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

Syncs HeyPocket AI recordings/transcripts to a local Obsidian-compatible wiki.

## Setup (First Time)

If the project hasn't been set up yet:

1. **Ask user for HeyPocket API key** - The project requires `HEYPOCKET_API_KEY` in `.env`
2. **If user provides API key**, add it to `.env`:

   ```text
   HEYPOCKET_API_KEY=pk_xxx
   ```

3. **Create environment and install**:

   ```bash
   cd ~/dev/pocket-wiki-sync
   uv sync --all-extras
   ```

## Quick Commands

```bash
# Sync new recordings (incremental)
pocket-wiki sync

# Force full sync (ignore last sync timestamp)
pocket-wiki sync --force

# Preview without writing files
pocket-wiki sync --dry-run

# Filter by tags
pocket-wiki sync --tags work,meeting

# Limit results
pocket-wiki sync --max 10

# Verbose output
pocket-wiki sync --verbose

# Custom wiki path
pocket-wiki sync --wiki /path/to/wiki
```

## Finding Recordings

When the user asks about a recording:

1. Check index: `~/wiki/concepts/pocket-sources.md`
2. Search wiki: Use wiki search for keywords
3. Direct path: `~/wiki/raw/pocket/<date>-<slug>.md`

## Output Structure

```text
~/wiki/
├── raw/pocket/
│   └── YYYY-MM-DD-slug.md    # Individual recordings
├── concepts/
│   └── pocket-sources.md      # Index
└── queries/
    └── pocket-sync-YYYY-MM-DD.md  # Sync logs
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
```

If `.env` doesn't exist or doesn't have the key, **ask the user** for their HeyPocket API key before running any commands.

## Idempotency

- Uses `.last-sync` to track timestamp
- Uses `.sync-lock` to prevent concurrent syncs
- Same recording won't be saved twice
