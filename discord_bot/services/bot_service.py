"""
Bot service for managing WhaleBots instances.
"""

import os
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
import pytz

from whalebots_automation import WhaleBots
from whalebots_automation.exceptions import (
    WhaleBotsError, EmulatorNotFoundError, EmulatorAlreadyRunningError,
    EmulatorNotRunningError, WindowError
)
from shared.models import User, Subscription
from shared.constants import InstanceStatus
from shared.data_manager import DataManager
from .ui_operation_queue import UIOperationQueue, OperationType, Priority, OperationStatus


class BotService:
    """Service for managing bot instances via WhaleBots automation."""
    
    def __init__(self, whalebots_path: str, data_manager: DataManager, operation_queue: Optional[UIOperationQueue] = None):
        """
        Initialize bot service.

        Args:
            whalebots_path: Path to WhaleBots installation
            data_manager: Data manager instance
            operation_queue: Optional UI operation queue instance
        """
        self.whalebots_path = whalebots_path
        self.data_manager = data_manager
        self._whalesbot: Optional[WhaleBots] = None
        self.operation_queue = operation_queue
        self.use_queue = operation_queue is not None
    
    @property
    def whalesbot(self) -> WhaleBots:
        """Get or create WhaleBots instance."""
        if self._whalesbot is None:
            self._whalesbot = WhaleBots(self.whalebots_path)
        return self._whalesbot

    def _get_actual_emulator_state(self, emulator_index: int) -> bool:
        """
        Get the actual running state of an emulator.

        Args:
            emulator_index: Index of the emulator to check

        Returns:
            True if emulator is actually running, False otherwise
        """
        try:
            emulator_states = self.whalesbot.get_emulator_states()
            for state in emulator_states:
                if state.index == emulator_index:
                    # Use the is_active property from EmulatorState class
                    return state.is_active
            return False
        except Exception as e:
            print(f"[ERROR] Failed to get actual emulator state for index {emulator_index}: {e}")
            # Return False on error to be safe - we don't want to start a bot that might already be running
            return False
    
    def _is_admin(self, user_id: str) -> bool:
        """Check if a user ID is an admin."""
        config = self.data_manager.get_config()
        return user_id in config.admin_users

    def _resolve_emulator_index(self, user, emulator_name: str, is_admin: bool = False) -> Dict[str, Any]:
        """
        Resolve an emulator name to an index, verifying the user is linked to it.

        Args:
            user: User object
            emulator_name: Name of the emulator to resolve
            is_admin: If True, skip ownership check (admins can control any emulator)

        Returns:
            Dict with 'success', 'index', and optionally 'message'
        """
        try:
            # Check user's own emulators list first
            emu_entry = user.get_emulator_by_name(emulator_name)
            if emu_entry:
                return {
                    'success': True,
                    'index': emu_entry['index']
                }

            # Not in user's list — check if the emulator exists
            emulator_state = self.whalesbot.get_emulator_state_by_name(emulator_name)
            if not emulator_state:
                return {
                    'success': False,
                    'message': f'Emulator "{emulator_name}" not found.'
                }

            # Admins can control any emulator
            if is_admin:
                return {
                    'success': True,
                    'index': emulator_state.index
                }

            return {
                'success': False,
                'message': f'You are not linked to emulator "{emulator_name}". Use `link {emulator_name}` first.'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error resolving emulator: {str(e)}'
            }

    async def start_instance(self, user_id: str, emulator_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Start bot instance for user.

        Args:
            user_id: Discord user ID
            emulator_name: Optional emulator name to start (uses user's linked emulator if None)

        Returns:
            Result dictionary with success status and message
        """
        is_admin = self._is_admin(user_id)

        user = self.data_manager.get_user(user_id)
        if not user and not is_admin:
            return {
                'success': False,
                'message': "You don't have access. Please contact admin."
            }

        # Resolve emulator index
        if emulator_name:
            if not user:
                # Admin without a user record — resolve directly
                try:
                    emulator_state = self.whalesbot.get_emulator_state_by_name(emulator_name)
                    if not emulator_state:
                        return {'success': False, 'message': f'Emulator "{emulator_name}" not found.'}
                    emulator_index = emulator_state.index
                except Exception as e:
                    return {'success': False, 'message': f'Error resolving emulator: {str(e)}'}
            else:
                resolve_result = self._resolve_emulator_index(user, emulator_name, is_admin=is_admin)
                if not resolve_result['success']:
                    return resolve_result
                emulator_index = resolve_result['index']
        else:
            if not user or user.emulator_index == -1:
                return {
                    'success': False,
                    'message': 'You are not linked to any emulator. Use `link <emulator_name>` to link first.'
                }
            emulator_index = user.emulator_index

        # Attempt to backfill emulator name if missing (non-blocking)
        if user and not user.emulator_name:
            try:
                for state in self.whalesbot.get_emulator_states():
                    if state.index == user.emulator_index:
                        user.emulator_name = state.emulator_info.name
                        self.data_manager.save_user(user)
                        break
            except Exception:
                pass

        # Check subscription (admins bypass)
        if not is_admin and user and user.subscription.is_expired:
            return {
                'success': False,
                'message': f'Your subscription expired on {user.subscription.end_at}. Please renew.'
            }

        # If queue is available, use queued execution
        if self.use_queue and self.operation_queue:
            return await self._queued_start_instance(user, emulator_index)

        emu_label = emulator_name or (user.emulator_name if user else None) or f"#{emulator_index}"

        try:
            actual_emulator_state = await asyncio.wait_for(
                asyncio.to_thread(self._get_actual_emulator_state, emulator_index),
                timeout=10.0
            )

            if user:
                if user.is_running and not actual_emulator_state:
                    print(f"[SYNC] User {user.discord_name} database says RUNNING but emulator is STOPPED. Syncing state...")
                    user.status = InstanceStatus.STOPPED.value
                    user.last_stop = datetime.now(pytz.UTC).isoformat()
                    self.data_manager.save_user(user)
                    return {
                        'success': False,
                        'message': 'Detected state inconsistency. Your miner was stopped outside Discord. Status has been synchronized. Please try starting again.'
                    }

                if user.is_running and actual_emulator_state:
                    return {
                        'success': False,
                        'message': 'Your miner is already running.'
                    }

                if not user.is_running and actual_emulator_state:
                    print(f"[SYNC] User {user.discord_name} database says STOPPED but emulator is RUNNING. Syncing state...")
                    user.status = InstanceStatus.RUNNING.value
                    user.last_start = datetime.now(pytz.UTC).isoformat()
                    user.last_heartbeat = datetime.now(pytz.UTC).isoformat()
                    self.data_manager.save_user(user)
                    return {
                        'success': False,
                        'message': 'Detected state inconsistency. Your miner was started outside Discord. Status has been synchronized.'
                    }
            else:
                # Admin with no user record — just check actual state
                if actual_emulator_state:
                    return {
                        'success': False,
                        'message': 'Emulator is already running.'
                    }
        except asyncio.TimeoutError:
            user_label = user.discord_name if user else user_id
            print(f"[ERROR] Timeout checking emulator state for user {user_label}")
            return {
                'success': False,
                'message': 'Timeout checking emulator state. WhaleBots may not be responding. Please try again.'
            }
        except Exception as e:
            user_label = user.discord_name if user else user_id
            print(f"[ERROR] Failed to check emulator state for user {user_label}: {e}")
            return {
                'success': False,
                'message': f'Unable to verify emulator state. Please try again. Error: {str(e)}'
            }

        try:
            await asyncio.wait_for(
                asyncio.to_thread(self.whalesbot.start, emulator_index),
                timeout=30.0
            )

            if user:
                user.status = InstanceStatus.RUNNING.value
                user.last_start = datetime.now(pytz.UTC).isoformat()
                user.last_heartbeat = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)

            return {
                'success': True,
                'message': f'Bot started for {emu_label}'
            }

        except asyncio.TimeoutError:
            user_label = user.discord_name if user else user_id
            print(f"[ERROR] Timeout starting emulator for user {user_label}")
            if user:
                user.status = InstanceStatus.ERROR.value
                self.data_manager.save_user(user)
            return {
                'success': False,
                'message': 'Timeout starting miner. WhaleBots window may not be responding. Please check manually.'
            }

        except EmulatorAlreadyRunningError:
            if user:
                user.status = InstanceStatus.RUNNING.value
                self.data_manager.save_user(user)
            return {
                'success': False,
                'message': 'Emulator is already running.'
            }

        except (EmulatorNotFoundError, WindowError) as e:
            if user:
                user.status = InstanceStatus.ERROR.value
                self.data_manager.save_user(user)
            return {
                'success': False,
                'message': f'Error starting: {str(e)}'
            }

        except Exception as e:
            if user:
                user.status = InstanceStatus.ERROR.value
                self.data_manager.save_user(user)
            return {
                'success': False,
                'message': f'Unknown error: {str(e)}'
            }
    
    async def stop_instance(self, user_id: str, emulator_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Stop bot instance for user.

        Args:
            user_id: Discord user ID
            emulator_name: Optional emulator name to stop (uses user's linked emulator if None)

        Returns:
            Result dictionary with success status and message
        """
        is_admin = self._is_admin(user_id)

        user = self.data_manager.get_user(user_id)
        if not user and not is_admin:
            return {
                'success': False,
                'message': "You don't have access."
            }

        # Resolve emulator index
        if emulator_name:
            if not user:
                # Admin without a user record — resolve directly
                try:
                    emulator_state = self.whalesbot.get_emulator_state_by_name(emulator_name)
                    if not emulator_state:
                        return {'success': False, 'message': f'Emulator "{emulator_name}" not found.'}
                    emulator_index = emulator_state.index
                except Exception as e:
                    return {'success': False, 'message': f'Error resolving emulator: {str(e)}'}
            else:
                resolve_result = self._resolve_emulator_index(user, emulator_name, is_admin=is_admin)
                if not resolve_result['success']:
                    return resolve_result
                emulator_index = resolve_result['index']
        else:
            if not user or user.emulator_index == -1:
                return {
                    'success': False,
                    'message': 'No emulator specified. Use `stop <emulator_name>`.'
                }
            emulator_index = user.emulator_index

        # If queue is available, use queued execution
        if self.use_queue and self.operation_queue:
            return await self._queued_stop_instance(user, emulator_index)

        emu_label = emulator_name or (user.emulator_name if user else None) or f"#{emulator_index}"

        # Check actual emulator state before proceeding (run in thread to avoid blocking)
        try:
            actual_emulator_state = await asyncio.wait_for(
                asyncio.to_thread(self._get_actual_emulator_state, emulator_index),
                timeout=10.0
            )

            if user:
                # Check if database says running but emulator is actually stopped (GUI stop scenario)
                if user.is_running and not actual_emulator_state:
                    print(f"[SYNC] User {user.discord_name} database says RUNNING but emulator is STOPPED during stop command. Syncing state...")
                    user.status = InstanceStatus.STOPPED.value
                    user.last_stop = datetime.now(pytz.UTC).isoformat()
                    self.data_manager.save_user(user)
                    return {
                        'success': False,
                        'message': 'Your miner is already stopped (state synchronized). No action needed.'
                    }

                # Check if database says stopped but emulator is actually running (GUI start scenario)
                if not user.is_running and actual_emulator_state:
                    print(f"[SYNC] User {user.discord_name} database says STOPPED but emulator is RUNNING during stop command. Syncing state...")
                    user.status = InstanceStatus.RUNNING.value
                    user.last_start = datetime.now(pytz.UTC).isoformat()
                    user.last_heartbeat = datetime.now(pytz.UTC).isoformat()
                    self.data_manager.save_user(user)
                    # Fall through to the stop logic below after sync

                # Check if not running (both database and actual state agree after potential sync)
                if not user.is_running and not actual_emulator_state:
                    return {
                        'success': False,
                        'message': 'Your miner is not running.'
                    }
            else:
                # Admin with no user record — just check actual state
                if not actual_emulator_state:
                    return {
                        'success': False,
                        'message': 'Emulator is not running.'
                    }
        except asyncio.TimeoutError:
            user_label = user.discord_name if user else user_id
            print(f"[ERROR] Timeout checking emulator state for user {user_label}")
            return {
                'success': False,
                'message': 'Timeout checking emulator state. WhaleBots may not be responding. Please try again.'
            }
        except Exception as e:
            user_label = user.discord_name if user else user_id
            print(f"[ERROR] Failed to check emulator state for user {user_label} during stop: {e}")
            return {
                'success': False,
                'message': f'Unable to verify emulator state. Please try again. Error: {str(e)}'
            }

        # Try to stop (run in thread to avoid blocking Discord event loop)
        try:
            await asyncio.wait_for(
                asyncio.to_thread(self.whalesbot.stop, emulator_index),
                timeout=30.0
            )

            # Update user status if user record exists
            if user:
                user.status = InstanceStatus.STOPPED.value
                user.last_stop = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)

            return {
                'success': True,
                'message': f'Bot stopped for {emu_label}'
            }

        except asyncio.TimeoutError:
            user_label = user.discord_name if user else user_id
            print(f"[ERROR] Timeout stopping emulator for user {user_label}")
            if user:
                user.status = InstanceStatus.ERROR.value
                self.data_manager.save_user(user)
            return {
                'success': False,
                'message': 'Timeout stopping miner. WhaleBots window may not be responding. Please check manually.'
            }

        except EmulatorNotRunningError:
            if user:
                user.status = InstanceStatus.STOPPED.value
                self.data_manager.save_user(user)
            return {
                'success': False,
                'message': 'Emulator is not running.'
            }

        except (EmulatorNotFoundError, WindowError) as e:
            if user:
                user.status = InstanceStatus.ERROR.value
                self.data_manager.save_user(user)
            return {
                'success': False,
                'message': f'Error stopping: {str(e)}'
            }

        except Exception as e:
            if user:
                user.status = InstanceStatus.ERROR.value
                self.data_manager.save_user(user)
            return {
                'success': False,
                'message': f'Unknown error: {str(e)}'
            }
    
    def get_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get bot status for user.

        Args:
            user_id: Discord user ID

        Returns:
            Status dictionary
        """
        user = self.data_manager.get_user(user_id)
        if not user:
            return {
                'exists': False,
                'message': "You don't have access."
            }

        # Check actual emulator state and sync if needed
        if user.emulator_index != -1:
            actual_emulator_state = self._get_actual_emulator_state(user.emulator_index)

            # Auto-sync state if inconsistency detected
            state_synced = False
            sync_message = ""

            if user.is_running and not actual_emulator_state:
                print(f"[SYNC] Status check: User {user.discord_name} database says RUNNING but emulator is STOPPED. Auto-syncing...")
                user.status = InstanceStatus.STOPPED.value
                user.last_stop = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)
                state_synced = True
                sync_message = " (State auto-synchronized: was stopped outside Discord)"

            elif not user.is_running and actual_emulator_state:
                print(f"[SYNC] Status check: User {user.discord_name} database says STOPPED but emulator is RUNNING. Auto-syncing...")
                user.status = InstanceStatus.RUNNING.value
                user.last_start = datetime.now(pytz.UTC).isoformat()
                user.last_heartbeat = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)
                state_synced = True
                sync_message = " (State auto-synchronized: was started outside Discord)"

        # Build status message - convert to running/stopped text
        status = user.status
        if user.subscription.is_expired:
            status = InstanceStatus.EXPIRED.value

        # Map status to running/stopped text
        if status == InstanceStatus.RUNNING.value:
            status_text = 'Miner is running'
        elif status == InstanceStatus.STOPPED.value:
            status_text = 'Miner is stopped'
        elif status == InstanceStatus.EXPIRED.value:
            status_text = 'Miner is stopped'
        elif status == InstanceStatus.ERROR.value:
            status_text = 'Miner is stopped'
        else:
            status_text = 'Miner is stopped'

        info = {
            'exists': True,
            'status': status_text,
            'symbol': '',
            'emulator_index': user.emulator_index,
            'is_running': user.is_running,
            'uptime_seconds': user.uptime_seconds,
            'last_heartbeat': user.last_heartbeat,
            'subscription_active': user.subscription.is_active,
            'days_left': user.subscription.days_left,
            'state_synced': state_synced if 'state_synced' in locals() else False,
            'sync_message': sync_message if 'sync_message' in locals() else ""
        }

        return info
    
    def update_heartbeat(self, user_id: str) -> None:
        """
        Update heartbeat timestamp for user.
        
        Args:
            user_id: Discord user ID
        """
        user = self.data_manager.get_user(user_id)
        if user and user.is_running:
            user.last_heartbeat = datetime.now(pytz.UTC).isoformat()
            self.data_manager.save_user(user)
    
    async def force_stop_instance(self, user_id: str) -> Dict[str, Any]:
        user = self.data_manager.get_user(user_id)
        if not user:
            return {
                'success': False,
                'message': 'User does not exist.'
            }
        
        try:
            if user.is_running:
                await asyncio.wait_for(
                    asyncio.to_thread(self.whalesbot.stop, user.emulator_index),
                    timeout=30.0
                )
            
            user.status = InstanceStatus.STOPPED.value
            user.last_stop = datetime.now(pytz.UTC).isoformat()
            self.data_manager.save_user(user)
            
            return {
                'success': True,
                'message': f'Force stopped bot for {user.discord_name}'
            }
        
        except asyncio.TimeoutError:
            user.status = InstanceStatus.ERROR.value
            self.data_manager.save_user(user)
            return {
                'success': False,
                'message': 'Timeout stopping miner. WhaleBots may not be responding.'
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
    
    def get_available_emulators(self) -> Dict[str, Any]:
        """
        Get list of all available emulators.
        
        Returns:
            Dict with emulator list and count
        """
        try:
            emulator_states = self.whalesbot.get_emulator_states()
            emulators = []
            for state in emulator_states:
                emulators.append({
                    'index': state.index,
                    'name': state.emulator_info.name,
                    'is_active': state.is_active,
                    'linked_user': None  # Will be filled later
                })
            
            # Find linked users (multiple users can share an emulator)
            all_users = self.data_manager.get_all_users()
            for emu in emulators:
                linked_users = []
                for user in all_users:
                    if user.emulator_index == emu['index']:
                        linked_users.append(user.discord_name)
                emu['linked_user'] = ", ".join(linked_users) if linked_users else None
            
            return {
                'success': True,
                'emulators': emulators,
                'count': len(emulators)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error getting emulators: {str(e)}'
            }
    
    def link_user_to_emulator(
        self,
        user_id: str,
        emulator_name: str,
        discord_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Link user to an emulator by name.
        Multiple users can share the same emulator.

        Args:
            user_id: Discord user ID
            emulator_name: Name of the emulator to link
            discord_name: Discord username (used when auto-creating a user record)

        Returns:
            Result dictionary
        """
        user = self.data_manager.get_user(user_id)
        if not user:
            # Auto-create user record with expired subscription placeholder
            now = datetime.now(pytz.UTC)
            subscription = Subscription(
                start_at=now.isoformat(),
                end_at=now.isoformat()
            )
            user = User(
                discord_id=user_id,
                discord_name=discord_name or user_id,
                emulator_index=-1,
                subscription=subscription,
                status=InstanceStatus.STOPPED.value
            )
            self.data_manager.save_user(user)

        # Check if user's bot is running
        if user.is_running:
            return {
                'success': False,
                'message': 'Please stop your miner before changing emulator link.'
            }

        # Find emulator by name
        try:
            emulator_state = self.whalesbot.get_emulator_state_by_name(emulator_name)
            if not emulator_state:
                return {
                    'success': False,
                    'message': f'Emulator "{emulator_name}" not found.'
                }

            # Link emulator
            old_emulator = user.emulator_name or f"Unlinked (Index {user.emulator_index})"
            user.emulator_index = emulator_state.index
            user.emulator_name = emulator_state.emulator_info.name
            self.data_manager.save_user(user)

            return {
                'success': True,
                'message': f'Successfully linked to emulator "{emulator_name}"!\nOld: {old_emulator}\nNew: {user.emulator_name} (Index {user.emulator_index})'
            }

        except Exception as e:
            return {
                'success': False,
                'message': f'Error linking emulator: {str(e)}'
            }
    
    def unlink_user_from_emulator(self, user_id: str) -> Dict[str, Any]:
        """
        Unlink user from emulator (set emulator_name to None).
        User account remains but cannot start bot until linked again.
        
        Args:
            user_id: Discord user ID
            
        Returns:
            Result dictionary
        """
        user = self.data_manager.get_user(user_id)
        if not user:
            return {
                'success': False,
                'message': "User not found."
            }
        
        # Check if user's bot is running
        if user.is_running:
            return {
                'success': False,
                'message': 'Please stop your miner before unlinking emulator.'
            }
        
        old_emulator = user.emulator_name or f"Index {user.emulator_index}"
        user.emulator_name = None
        user.emulator_index = -1  # -1 means unlinked
        self.data_manager.save_user(user)
        
        return {
            'success': True,
            'message': f'Successfully unlinked from emulator "{old_emulator}".\nYou can link to another emulator using /link command.'
        }
    
    def validate_user_emulators(self) -> Dict[str, Any]:
        """
        Validate all users' emulator links.
        Unlink users if their emulator no longer exists.
        
        Returns:
            Dict with validation results
        """
        try:
            # Get all available emulators
            emulator_states = self.whalesbot.get_emulator_states()
            available_names = {state.emulator_info.name for state in emulator_states}
            available_indices = {state.index for state in emulator_states}
            
            # Check all users
            all_users = self.data_manager.get_all_users()
            unlinked_users = []
            
            for user in all_users:
                # Skip users with no active subscription
                if user.subscription.is_expired:
                    continue
                
                # Check if user's emulator still exists
                needs_unlink = False
                
                if user.emulator_name and user.emulator_name not in available_names:
                    needs_unlink = True
                elif user.emulator_index not in available_indices and user.emulator_index != -1:
                    needs_unlink = True
                
                if needs_unlink:
                    # Force stop if running
                    if user.is_running:
                        try:
                            self.whalesbot.stop(user.emulator_index)
                        except:
                            pass
                        user.status = InstanceStatus.STOPPED.value
                    
                    # Unlink
                    old_name = user.emulator_name or f"Index {user.emulator_index}"
                    user.emulator_name = None
                    user.emulator_index = -1
                    self.data_manager.save_user(user)
                    
                    unlinked_users.append({
                        'user_id': user.discord_id,
                        'user_name': user.discord_name,
                        'old_emulator': old_name
                    })
            
            return {
                'success': True,
                'unlinked_count': len(unlinked_users),
                'unlinked_users': unlinked_users
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error validating emulators: {str(e)}'
            }
    
    def get_whalebots_instance(self):
        """
        Get the WhaleBots instance.

        Returns:
            WhaleBots instance or None if not available
        """
        try:
            return self.whalesbot
        except Exception:
            return None

    def cleanup(self) -> None:
        """Cleanup WhaleBots instance."""
        if self._whalesbot:
            self._whalesbot.cleanup()
            self._whalesbot = None

    async def _queued_start_instance(self, user: User, emulator_index: int = None) -> Dict[str, Any]:
        """
        Start instance using queue system.

        Args:
            user: User object
            emulator_index: Emulator index to start (defaults to user.emulator_index)

        Returns:
            Result dictionary with success status and message
        """
        if emulator_index is None:
            emulator_index = user.emulator_index
        # Check if user already has pending operations
        pending_ops = self.operation_queue.get_pending_operations()
        user_pending = [op for op in pending_ops if op['user_name'] == user.discord_name]

        if user_pending:
            return {
                'success': False,
                'message': f'You already have a pending operation in the queue (position #{user_pending[0]["queue_position"]}).'
            }

        emu_label = (user.emulator_name if user else None) or f"#{emulator_index}"

        # Create start operation callback
        async def start_operation():
            # Check actual emulator state before proceeding
            actual_emulator_state = self._get_actual_emulator_state(emulator_index)

            # Check for state inconsistency
            if user.is_running and not actual_emulator_state:
                print(f"[SYNC] User {user.discord_name} database says RUNNING but emulator is STOPPED. Syncing...")
                user.status = InstanceStatus.STOPPED.value
                user.last_stop = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)
                return {
                    'success': False,
                    'message': 'State inconsistency detected. Status synchronized. Please try again.'
                }

            # Check if already running
            if user.is_running and actual_emulator_state:
                return {
                    'success': False,
                    'message': 'Your miner is already running.'
                }

            # Check if emulator was started outside Discord
            if not user.is_running and actual_emulator_state:
                print(f"[SYNC] User {user.discord_name} database says STOPPED but emulator is RUNNING. Syncing...")
                user.status = InstanceStatus.RUNNING.value
                user.last_start = datetime.now(pytz.UTC).isoformat()
                user.last_heartbeat = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)
                return {
                    'success': False,
                    'message': 'State inconsistency detected. Your miner was started outside Discord. Status synchronized.'
                }

            # Execute start operation
            try:
                self.whalesbot.start(emulator_index)

                # Update user status
                user.status = InstanceStatus.RUNNING.value
                user.last_start = datetime.now(pytz.UTC).isoformat()
                user.last_heartbeat = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)

                return {
                    'success': True,
                    'message': f'Bot started for {emu_label}'
                }

            except EmulatorAlreadyRunningError:
                # Update status to running anyway
                user.status = InstanceStatus.RUNNING.value
                self.data_manager.save_user(user)
                return {
                    'success': False,
                    'message': 'Emulator is already running.'
                }

            except (EmulatorNotFoundError, WindowError) as e:
                user.status = InstanceStatus.ERROR.value
                self.data_manager.save_user(user)
                return {
                    'success': False,
                    'message': f'Error starting: {str(e)}'
                }

        # Add operation to queue
        operation_id = await self.operation_queue.add_operation(
            operation_type=OperationType.START,
            user_id=user.discord_id,
            user_name=user.discord_name,
            emulator_index=emulator_index,
            priority=Priority.NORMAL,
            timeout=60,
            callback=start_operation,
            metadata={'emulator_name': user.emulator_name}
        )

        # Wait for operation to complete
        result = await self.operation_queue.wait_for_operation(operation_id, timeout=120)

        if result is None:
            return {
                'success': False,
                'message': 'Operation timed out. Please try again or contact admin.'
            }

        if result.status == OperationStatus.COMPLETED:
            return result.result or {'success': False, 'message': 'Unknown error'}
        else:
            return {
                'success': False,
                'message': f'Operation failed: {result.error or "Unknown error"}'
            }

    async def _queued_stop_instance(self, user: User, emulator_index: int = None) -> Dict[str, Any]:
        """
        Stop instance using queue system.

        Args:
            user: User object
            emulator_index: Emulator index to stop (defaults to user.emulator_index)

        Returns:
            Result dictionary with success status and message
        """
        if emulator_index is None:
            emulator_index = user.emulator_index
        # Check if user already has pending operations
        pending_ops = self.operation_queue.get_pending_operations()
        user_pending = [op for op in pending_ops if op['user_name'] == user.discord_name]

        if user_pending:
            return {
                'success': False,
                'message': f'You already have a pending operation in the queue (position #{user_pending[0]["queue_position"]}).'
            }

        emu_label = (user.emulator_name if user else None) or f"#{emulator_index}"

        # Create stop operation callback
        async def stop_operation():
            # Check actual emulator state before proceeding
            actual_emulator_state = self._get_actual_emulator_state(emulator_index)

            # Check for state inconsistency
            if user.is_running and not actual_emulator_state:
                print(f"[SYNC] User {user.discord_name} database says RUNNING but emulator is STOPPED during stop. Syncing...")
                user.status = InstanceStatus.STOPPED.value
                user.last_stop = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)
                return {
                    'success': False,
                    'message': 'Your miner is already stopped (state synchronized).'
                }

            # Check if database says stopped but emulator is actually running
            if not user.is_running and actual_emulator_state:
                print(f"[SYNC] User {user.discord_name} database says STOPPED but emulator is RUNNING during stop. Syncing...")
                user.status = InstanceStatus.RUNNING.value
                user.last_start = datetime.now(pytz.UTC).isoformat()
                user.last_heartbeat = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)

            # Check if not running after potential sync
            if not user.is_running and not actual_emulator_state:
                return {
                    'success': False,
                    'message': 'Your miner is not running.'
                }

            # Execute stop operation
            try:
                self.whalesbot.stop(emulator_index)

                # Update user status
                user.status = InstanceStatus.STOPPED.value
                user.last_stop = datetime.now(pytz.UTC).isoformat()
                self.data_manager.save_user(user)

                uptime_text = ""
                if user.uptime_seconds:
                    hours = user.uptime_seconds // 3600
                    minutes = (user.uptime_seconds % 3600) // 60
                    uptime_text = f"\nUptime: {hours}h {minutes}m"

                return {
                    'success': True,
                    'message': f'Bot stopped for {emu_label}'
                }

            except EmulatorNotRunningError:
                # Update status to stopped anyway
                user.status = InstanceStatus.STOPPED.value
                self.data_manager.save_user(user)
                return {
                    'success': False,
                    'message': 'Emulator is not running.'
                }

            except (EmulatorNotFoundError, WindowError) as e:
                user.status = InstanceStatus.ERROR.value
                self.data_manager.save_user(user)
                return {
                    'success': False,
                    'message': f'Error stopping: {str(e)}'
                }

        # Add operation to queue (higher priority for stop)
        operation_id = await self.operation_queue.add_operation(
            operation_type=OperationType.STOP,
            user_id=user.discord_id,
            user_name=user.discord_name,
            emulator_index=emulator_index,
            priority=Priority.HIGH,  # Stop operations have higher priority
            timeout=45,
            callback=stop_operation,
            metadata={'emulator_name': user.emulator_name}
        )

        # Wait for operation to complete
        result = await self.operation_queue.wait_for_operation(operation_id, timeout=90)

        if result is None:
            return {
                'success': False,
                'message': 'Operation timed out. Please try again or contact admin.'
            }

        if result.status == OperationStatus.COMPLETED:
            return result.result or {'success': False, 'message': 'Unknown error'}
        else:
            return {
                'success': False,
                'message': f'Operation failed: {result.error or "Unknown error"}'
            }
