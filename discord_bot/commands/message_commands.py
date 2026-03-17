"""
Message-based user commands for Discord bot.
Users type plain text commands in allowed channels instead of slash commands.
"""

from datetime import datetime

import discord

from discord_bot.utils.permissions import in_allowed_channel_msg
from discord_bot.services.bot_service import BotService
from discord_bot.services.subscription_service import SubscriptionService
from shared.data_manager import DataManager
from shared.constants import ActionType, ActionResult


# Commands that the bot recognizes (no prefix)
COMMANDS = {'start', 'stop', 'status', 'expiry', 'link', 'help', 'queue', 'view'}


def setup_message_commands(
    bot: discord.Bot,
    bot_service: BotService,
    subscription_service: SubscriptionService,
    data_manager: DataManager
):
    """
    Setup message-based user commands.

    Args:
        bot: Discord bot instance
        bot_service: Bot service instance
        subscription_service: Subscription service instance
        data_manager: Data manager instance
    """

    @bot.listen("on_message")
    async def on_message(message: discord.Message):
        # Ignore messages from bots
        if message.author.bot:
            return

        # Parse command from message content
        content = message.content.strip()
        if not content:
            return

        parts = content.split(maxsplit=1)
        command = parts[0].lower()
        args = parts[1].strip() if len(parts) > 1 else ""

        # Ignore unknown commands silently
        if command not in COMMANDS:
            return

        # Check if in allowed channel (silently ignore if not)
        allowed, _ = in_allowed_channel_msg(message)
        if not allowed:
            return

        user_id = str(message.author.id)

        if command == "start":
            await handle_start(message, user_id, args, bot_service, data_manager)
        elif command == "stop":
            await handle_stop(message, user_id, args, bot_service, data_manager)
        elif command == "status":
            await handle_status(message, user_id, bot_service)
        elif command == "expiry":
            await handle_expiry(message, user_id, data_manager)
        elif command == "link":
            await handle_link(message, user_id, args, bot_service, data_manager)
        elif command == "help":
            await handle_help(message)
        elif command == "queue":
            await handle_queue(message, user_id, bot)
        elif command == "view":
            await handle_view(message, user_id, args, bot_service, data_manager)


async def handle_start(
    message: discord.Message,
    user_id: str,
    args: str,
    bot_service: BotService,
    data_manager: DataManager
):
    """Handle the start command."""
    emulator_name = args if args else None

    async with message.channel.typing():
        result = await bot_service.start_instance(user_id, emulator_name=emulator_name)

    data_manager.log_action(
        user_id=user_id,
        user_name=str(message.author),
        action=ActionType.START,
        details=f"Emulator start attempt{f' ({emulator_name})' if emulator_name else ''}",
        result=ActionResult.SUCCESS if result['success'] else ActionResult.FAILED
    )

    await message.reply(result['message'])


async def handle_stop(
    message: discord.Message,
    user_id: str,
    args: str,
    bot_service: BotService,
    data_manager: DataManager
):
    """Handle the stop command."""
    emulator_name = args if args else None

    async with message.channel.typing():
        result = await bot_service.stop_instance(user_id, emulator_name=emulator_name)

    data_manager.log_action(
        user_id=user_id,
        user_name=str(message.author),
        action=ActionType.STOP,
        details=f"Emulator stop attempt{f' ({emulator_name})' if emulator_name else ''}",
        result=ActionResult.SUCCESS if result['success'] else ActionResult.FAILED
    )

    await message.reply(result['message'])


async def handle_status(
    message: discord.Message,
    user_id: str,
    bot_service: BotService
):
    """Handle the status command."""
    status_info = bot_service.get_status(user_id)

    if not status_info['exists']:
        await message.reply(status_info['message'])
        return

    # Build plain text status
    lines = []
    lines.append(f"**Miner Status**")
    lines.append(f"Status: {status_info['status']}")
    lines.append(f"Emulator: #{status_info['emulator_index']}")

    if status_info['is_running'] and status_info['uptime_seconds']:
        hours = status_info['uptime_seconds'] // 3600
        minutes = (status_info['uptime_seconds'] % 3600) // 60
        lines.append(f"Uptime: {hours}h {minutes}m")

    if status_info['last_heartbeat']:
        try:
            hb_dt = datetime.fromisoformat(status_info['last_heartbeat'])
            lines.append(f"Last Update: <t:{int(hb_dt.timestamp())}:R>")
        except Exception:
            pass

    sub_status = "Active" if status_info['subscription_active'] else "Expired"
    lines.append(f"Subscription: {sub_status}")
    lines.append(f"Remaining: {status_info['days_left']} days")

    if status_info.get('state_synced', False):
        lines.append(f"\n⚠️ {status_info.get('sync_message', 'State was synchronized with GUI.')}")

    await message.reply("\n".join(lines))


async def handle_expiry(
    message: discord.Message,
    user_id: str,
    data_manager: DataManager
):
    """Handle the expiry command."""
    user = data_manager.get_user(user_id)

    if not user:
        await message.reply("You don't have access. Please contact admin.")
        return

    try:
        start_dt = user.subscription.start_datetime
        end_dt = user.subscription.end_datetime

        lines = []
        lines.append("**Subscription Information**")
        lines.append(f"Start: <t:{int(start_dt.timestamp())}:D>")
        lines.append(f"Expires: <t:{int(end_dt.timestamp())}:D>")
        lines.append(f"Remaining: {user.subscription.days_left} days")

        if user.subscription.is_active:
            lines.append("Status: Active")
        else:
            lines.append("Status: Expired - Please renew")

        await message.reply("\n".join(lines))
    except Exception:
        await message.reply("Error displaying subscription information.")


async def handle_link(
    message: discord.Message,
    user_id: str,
    args: str,
    bot_service: BotService,
    data_manager: DataManager
):
    """Handle the link command."""
    if not args:
        await message.reply("Usage: `link <emulator_name>`")
        return

    emulator_name = args

    result = bot_service.link_user_to_emulator(
        user_id,
        emulator_name,
        discord_name=str(message.author)
    )

    data_manager.log_action(
        user_id=user_id,
        user_name=str(message.author),
        action=ActionType.CONFIG_CHANGE,
        details=f"Link to emulator: {emulator_name}",
        result=ActionResult.SUCCESS if result['success'] else ActionResult.FAILED
    )

    await message.reply(result['message'])


async def handle_view(
    message: discord.Message,
    user_id: str,
    args: str,
    bot_service: BotService,
    data_manager: DataManager
):
    """Handle the view command - screenshot an emulator."""
    if not args:
        await message.reply("Usage: `view <emulator_name>`")
        return

    emulator_name = args

    # Check ownership or admin
    is_admin = bot_service._is_admin(user_id)
    if not is_admin:
        user = data_manager.get_user(user_id)
        if not user:
            await message.reply("You don't have access. Please contact admin.")
            return
        emu_entry = user.get_emulator_by_name(emulator_name)
        if not emu_entry:
            await message.reply(f'You are not linked to emulator "{emulator_name}".')
            return

    async with message.channel.typing():
        result = await bot_service.screenshot_emulator(emulator_name)

    if not result['success']:
        await message.reply(result['message'])
        return

    file = discord.File(result['image'], filename=f"{result['name']}.png")
    await message.reply(file=file)


async def handle_help(message: discord.Message):
    """Handle the help command."""
    help_text = (
        "**Miner Usage Guide**\n"
        "\n"
        "**Miner Control**\n"
        "`start` - Start your miner\n"
        "`start <name>` - Start a specific emulator\n"
        "`stop` - Stop your miner\n"
        "`stop <name>` - Stop a specific emulator\n"
        "`status` - Check miner status\n"
        "`view <name>` - Screenshot an emulator\n"
        "`expiry` - View subscription info\n"
        "\n"
        "**Emulator Management**\n"
        "`link <emulator_name>` - Link to an emulator\n"
        "\n"
        "**Other**\n"
        "`queue` - Show queue status\n"
        "`help` - Show this help message\n"
        "\n"
        "**Notes**\n"
        "• Cooldown between start/stop commands\n"
        "• Bot auto-stops when subscription expires\n"
        "• Contact admin for support"
    )

    await message.reply(help_text)


async def handle_queue(
    message: discord.Message,
    user_id: str,
    bot: discord.Bot
):
    """Handle the queue command."""
    if not hasattr(bot, 'operation_queue'):
        await message.reply("Queue system is not available.")
        return

    queue_info = bot.operation_queue.get_queue_info()
    pending_ops = bot.operation_queue.get_pending_operations(limit=10)

    user_pending_ops = [op for op in pending_ops if op['user_name'] == str(message.author)]

    lines = []
    lines.append("**Queue Status**")
    lines.append(f"Pending: {queue_info['pending_operations']}")
    lines.append(f"Processing: {queue_info['processing_operations']}")
    lines.append(f"Processor Active: {'Yes' if queue_info['is_processing'] else 'No'}")

    if user_pending_ops:
        op = user_pending_ops[0]
        lines.append(f"\n**Your Queue Position**")
        lines.append(f"Operation: {op['operation_type'].title()}")
        lines.append(f"Position: #{op['queue_position']}")
        lines.append(f"Emulator: #{op['emulator_index']}")
    else:
        lines.append("\nYou have no pending operations.")

    if pending_ops:
        lines.append(f"\n**Pending Operations**")
        for i, op in enumerate(pending_ops[:5], 1):
            lines.append(f"#{i}. {op['operation_type'].title()} - {op['user_name']} (Emulator #{op['emulator_index']})")
        if len(pending_ops) > 5:
            lines.append(f"... and {len(pending_ops) - 5} more")

    await message.reply("\n".join(lines))
