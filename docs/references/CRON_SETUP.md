# Pocket Wiki Sync — Automated Syncing via Cron

## Overview

You can set up `pocket-wiki-sync` to run automatically on a schedule using your system's cron daemon. The CLI handles its own locking, error reporting, and incremental sync state — no wrapper script needed.

## Prerequisites

- `pocket-wiki-sync` installed (`uv tool install pocket-wiki-sync`)
- `HEYPOCKET_API_KEY` configured — either in a `.env` file in the project directory or exported as an environment variable
- Cron daemon running on your system

## Basic Setup

Open your crontab:

```bash
crontab -e
```

Add a line to run every 15 minutes:

```cron
*/15 * * * * cd ~/dev/pocket-wiki-sync && pocket-wiki sync --max 50 >> $HOME/wiki/pocket-sync.log 2>&1
```

This will:

- Change to the project directory (so `.env` is picked up)
- Run the sync command with a max of 50 recordings
- Append all output (stdout + stderr) to a log file

## Cron Schedule Reference

| Schedule | Cron Expression |
|---|---|
| Every 15 minutes | `*/15 * * * *` |
| Every 30 minutes | `*/30 * * * *` |
| Every hour | `0 * * * *` |
| Daily at 2 AM | `0 2 * * *` |

## Log Management

The log file will grow over time. Add a log rotation line to your crontab:

```cron
# Rotate logs monthly, keep 12 months
0 0 1 * * find $HOME/wiki -name "pocket-sync.log*" -mtime +365 -delete
```

Or use `logrotate` if available on your system.

## Multiple Syncs

If a sync is already running when cron triggers another, the CLI's built-in lock mechanism (`--force` to override) will cause the second instance to exit immediately with a message. This prevents overlapping syncs — no action needed on your part.

## Testing

Run the command manually first to verify everything works:

```bash
cd ~/dev/pocket-wiki-sync && pocket-wiki sync --max 5
```

Check the output directory:

```bash
ls -la ~/wiki/raw/pocket/
```

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Sync not running | Cron daemon not active | Check `sudo systemctl status cron` |
| "API key not set" error | `.env` not found or env var missing | Use absolute path: `cd /home/user/dev/pocket-wiki-sync && ...` |
| Nothing appears in log | Log directory doesn't exist | Ensure parent directory exists or use `$HOME/` path |
| Slow performance | Too many recordings in one sync | Lower `--max 50` to `--max 10` |
