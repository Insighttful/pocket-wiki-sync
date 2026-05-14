---
name: pocket-wiki-sync
description: "Sync HeyPocket AI recordings to a local Obsidian-compatible wiki raw directory. Use when the user wants to sync, manage, or search their voice recordings and transcripts. Commands: pocket-wiki sync, pocket-wiki list-synced, pocket-wiki show-config, pocket-wiki clean."
license: MIT
compatibility: Requires Python 3.12+, HeyPocket API key, uv package manager, and local wiki directory
metadata:
  author: dgxspark
  version: 0.0.1
---

# Pocket Wiki Sync

Syncs HeyPocket AI recordings/transcripts to a local Obsidian-compatible wiki (raw markdown files).

## Setup (First Time)

If the project hasn't been set up yet:

1. **Ask user for HeyPocket API key** - The project requires `HEYPOCKET_API_KEY` in `.env`.
2. **If user provides API key**, add it to `.env`:

   ```text
   HEYPOCKET_API_KEY=pk_xxx
   ```

3. **Create environment and install**:

   ```bash
   cd ~/dev/pocket-wiki-sync
   uv sync --all-extras
   ```

4. On first run, if `WIKI_RAW_PATH` is not set in `.env`, the CLI will prompt once for a transcripts directory (e.g., `~/wiki/raw`) and write it to `.env`.

## Core Principles

- `.env` is the source of truth:
  - Config + secrets are read from `.env` via pydantic-settings.
  - No in-memory environment pollution across runs/commands.
- Sync state:
  - Single file at project root: `.last-sync`.
  - No backup copies; deleting this file means “full sync” next run.

## Quick Commands

Default behavior: fetch and sync all unsynced recordings (no artificial limit). Use `--max` only to cap a single run.

```bash
# Sync new recordings (all by default)
pocket-wiki sync

# Force full sync (ignore last sync timestamp)
pocket-wiki sync --force

# Limit this run to N recordings
pocket-wiki sync --max 10

# Preview without writing files
pocket-wiki sync --dry-run

# Verbose output (useful for debugging)
pocket-wiki sync --verbose

# Filter by tags
pocket-wiki sync --tags work,meeting

# Custom wiki path for this run
pocket-wiki sync --wiki /path/to/wiki
```

Other commands:

```bash
# List synced recordings (local files only)
pocket-wiki list-synced

# Show current configuration and validate API key
pocket-wiki show-config

# Clean up state files (--all to also delete recordings)
pocket-wiki clean
```

## Finding Recordings

When the user asks about a recording:

1. List synced: `pocket-wiki list-synced`
2. Direct path: `<WIKI_RAW_PATH>/YYYY-MM-DD-slug.md`

There are no extra subdirectories (no concepts/ or queries/) created by this tool.

## Output Structure

Transcripts are saved directly under `WIKI_RAW_PATH` as:

- `YYYY-MM-DD-slug.md`

No additional directories are created by pocket-wiki-sync.

Example (if WIKI_RAW_PATH=~/wiki/raw):

```text
~/wiki/raw/
├── 2026-05-14-conversation-on-may-14th-at-11-54.md
└── 2026-05-13-sprint-planning.md
```

## File Format

Each recording file contains:

- YAML frontmatter (id, title, created, tags)
- **Summary** (AI-generated)
- **Mind Map** (structured nodes)
- **Action Items** (actionable tasks)
- **Transcript** (plain text)

## Environment

Required in `.env`:

```text
HEYPOCKET_API_KEY=pk_xxx
WIKI_RAW_PATH=~/wiki/raw   # or any directory where you want transcripts saved
```

If `.env` doesn't exist or doesn't have the key, **ask the user** for their HeyPocket API key before running any commands.

## Idempotency

- Uses `.last-sync` (project root) to track last sync timestamp.
- Uses `.sync-lock` to prevent concurrent syncs.
- The same recording won’t be saved twice.
