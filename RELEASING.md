# Releasing WhalesBot

This project ships as a single PyInstaller-built `WhalesBot.exe`. End users
download a release zip from GitHub, extract, and run the exe. Subsequent
updates are handled automatically: on startup the exe asks GitHub if a
newer release exists, and (with the user's explicit `y`) downloads and
swaps in the new version.

## How auto-update works

1. `VERSION` (a one-line file at the repo root) is bundled into the exe at build time.
2. On startup, `shared/updater.py` calls
   `https://api.github.com/repos/Minnyat/rok-whalesbot-discord-bot/releases/latest`
   and compares `tag_name` to the bundled `VERSION` (semver-style: `1.2.3`).
3. If newer, the user is prompted `[y/N]`. Default is **N** — only an explicit `y` updates.
4. On `y`: the first `.zip` asset on the release is downloaded to `%TEMP%`,
   extracted to a staging dir (skipping `data/` and `.env` so user state survives),
   and `updater.bat` is spawned. The exe exits, the bat waits for the file
   to release, robocopies the staged files into the install dir, and relaunches.

Users can disable the check entirely with `AUTO_UPDATE=off` in their `.env`.

## Cutting a release

### 1. Bump `VERSION`
Edit the `VERSION` file at the repo root, e.g. `1.0.0` -> `1.0.1`.
This must be done **before** building — PyInstaller bakes it into the exe.

Use semver-style numeric segments only (`1.0.1`, `2.3.10`). Pre-release
tags like `1.0.1-beta` will not compare correctly with the current code.

### 2. Build
```
build.bat
```
Output lands at `dist\WhalesBot.exe`. The build script handles installing
dependencies and PyInstaller automatically.

If `build.bat` errors with "Access is denied" on `dist\WhalesBot.exe`,
something has the file open — close any running `WhalesBot.exe`, any
Explorer window previewing `dist\`, or wait for AV to finish scanning.

### 3. Package the release zip
Create a zip containing **just** the new exe:

```
WhalesBot.exe
```

That's the minimum. `updater.bat` is bundled inside the exe and gets
written out on first run, and `data/` + `.env` are intentionally skipped
during update extraction so user state is never overwritten.

For a zip that also works as a **first-time install** (not just an
update), add a `.env` template and an empty `data/` folder:

```
WhalesBot.exe
updater.bat        (optional convenience for new users)
.env               (template with placeholder DISCORD_BOT_TOKEN)
data/              (empty folder)
```

### 4. Create the GitHub release
1. https://github.com/Minnyat/rok-whalesbot-discord-bot/releases/new
2. **Tag**: matches `VERSION` exactly (e.g. `1.0.1`). A leading `v` like `v1.0.1` is fine — the updater strips it.
3. **Title**: anything human-readable.
4. **Body**: the **first line** is shown to users in the update prompt — make it informative.
5. **Attach** the zip as a release asset. Upload only one `.zip` — the updater picks the first one alphabetically.
6. Publish (not draft, not pre-release).

### 5. Verify
On a machine with the previous version, launch `WhalesBot.exe`. You should see:

```
Update available: v1.0.0 -> 1.0.1
Notes: <first line of release body>
Update now? [y/N]: _
```

Press `y`. The exe should download, swap, and relaunch with the new version.

## Files involved

| File | Purpose |
|---|---|
| `VERSION` | Source of truth for the current version. Bump before each release. |
| `shared/updater.py` | Check + prompt + download + spawn updater logic. |
| `updater.bat` | Out-of-process file swap + relaunch. Bundled into the exe. |
| `build.bat` | Builds `dist\WhalesBot.exe` with the right `--add-data` flags. |
| `run_bot.py` | Entrypoint — calls `check_and_prompt()` right after `.env` loads. |

## Testing locally without a real release

To test the prompt flow without cutting a real release: temporarily set
`VERSION` to something lower than the current GitHub release (e.g.
`0.0.1`), rebuild, and run. The prompt will appear. Remember to restore
`VERSION` before your real next release.
