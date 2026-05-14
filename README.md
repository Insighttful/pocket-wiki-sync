# pocket-wiki-sync

Sync [Pocket](https://heypocket.com/pages/home-v2c) AI voice meeting recordings and transcripts to a local [Obsidian](https://obsidian.md)-compatible wiki.

Pocket is an AI-powered voice meeting assistant — you trigger it by saying "Hey Pocket" — that records, transcribes, summarizes, and extracts action items from your conversations. This tool takes those recordings from the [Pocket API](https://docs.heypocketai.com/docs/api) and saves them as structured markdown files in your local wiki.

## How It Works

1. You record a meeting with Pocket (mobile app or web)
2. Pocket transcribes it, generates a summary, mind map, and action items
3. `pocket-wiki-sync` pulls that data from the Pocket API
4. Saves it as a clean markdown file in `~/wiki/raw/pocket/` with YAML frontmatter
5. Also generates an index (`concepts/pocket-sources.md`) and a daily sync log (`queries/pocket-sync-YYYY-MM-DD.md`)

All output is plain markdown — compatible with Obsidian, VS Code, or any text editor.

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/yourusername/pocket-wiki-sync.git
cd pocket-wiki-sync
uv tool install .

# 2. Add your Pocket API key
echo 'HEYPOCKET_API_KEY=pk_xxx' > .env

# 3. Run a sync
pocket-wiki sync

# 4. Check what you got
pocket-wiki list-synced
```

That's it. Your recordings are now in `~/wiki/raw/pocket/` as markdown files.

## Prerequisites

- **Python 3.12+** and **[uv](https://docs.astral.sh/uv/)** (package manager)
- **A Pocket account** with an API key — get one at [heypocketai.com](https://heypocketai.com)
- **A wiki directory** (defaults to `~/wiki`, any Obsidian vault works)

## Features

- Fetch recordings from the [Pocket API](https://docs.heypocketai.com/docs/api) with pagination
- Save recordings as structured markdown files (transcript, summary, mind map, action items)
- Idempotent sync — only saves new recordings, skips duplicates
- Incremental sync state tracked via `.last-sync` (single file, no backup copies)
- Concurrent transcript downloads with circuit breaker and retry
- Dry-run mode to preview what would be synced
- Auto-generated sources index and daily sync logs
- Tag filtering per-sync

## Configuration

### Credentials

Create a `.env` file in the project root or export the variable:

```bash
HEYPOCKET_API_KEY=pk_xxx
```

The API key starts with `pk_` and is obtained from the [Pocket dashboard](https://heypocketai.com). See the [API documentation](https://docs.heypocketai.com/docs/api) for details.

### Wiki Path

Set the wiki output directory (default: `~/wiki`):

```bash
export WIKI_PATH=~/wiki
```

Any directory works — point it at your Obsidian vault, a Foam workspace, or a plain folder.

### All Environment Variables

| Variable | Default | Description |
|---|---|---|
| `HEYPOCKET_API_KEY` | — | Pocket API key (required) |
| `HEYPOCKET_BASE_URL` | `https://public.heypocketai.com/api/v1` | Pocket API base URL |
| `WIKI_PATH` | `~/wiki` | Path to wiki/Obsidian vault |

## Usage

### Sync Recordings

By default, all available unsynced recordings are fetched and saved. Use `--max` only if you want to cap how many are synced in a single run.

```bash
# Sync new recordings (all by default)
pocket-wiki sync

# Limit to N recordings this run
pocket-wiki sync --max 10

# Force full sync (ignore last sync timestamp)
pocket-wiki sync --force

# Filter by tags
pocket-wiki sync --tags "meeting,work"

# Preview what would be synced without writing files
pocket-wiki sync --dry-run
```

### List and Inspect

```bash
# List recordings already in the wiki
pocket-wiki list-synced

# Show current configuration (check API key status)
pocket-wiki show-config
```

### Cleanup

```bash
# Clean up sync state files
pocket-wiki clean

# Also delete all synced recordings from the wiki
pocket-wiki clean --yes

# Preview what clean would remove
pocket-wiki clean --dry-run --all
```

## Output Structure

Recordings are saved following LLM Wiki conventions under your chosen wiki path:

```text
<WIKI_PATH>/
├── raw/
│   └── pocket/
│       ├── 2026-05-07-recording-title.md   (synced recordings)
│       └── ...
├── concepts/
│   └── pocket-sources.md                   (index of all sources)
└── queries/
    └── pocket-sync-2026-05-07.md           (sync log entry)
```

Each recording file contains YAML frontmatter (`id`, `title`, `created`, `duration`, `state`, `language`, `tags`) followed by sections for summary, mind map, action items, and transcript.

### File Format Example

```markdown
---
id: rec_abc123
title: "Sprint Planning - May 7"
created: 2026-05-07T14:30:00+00:00
duration_seconds: 1800
state: completed
language: en
tags:
  - meeting
  - sprint
---

# Sprint Planning - May 7

## Summary
We discussed sprint goals for the next two weeks...

## Mind Map

Type: tree

### Nodes
- **Sprint Goals**
  - id: node_1
  - parent_id:
  - color: blue

## Action Items

- [ ] **Update deployment pipeline**
  - id: ai_1
  - assignee: Alice
  - priority: high
  - status: TODO

## Transcript
Okay team, let's kick off sprint planning...
```

## Automated Syncing (Cron)

To sync every 15 minutes automatically, add this to your crontab (`crontab -e`):

```cron
*/15 * * * * cd ~/dev/pocket-wiki-sync && pocket-wiki sync --max 50 >> $HOME/wiki/pocket-sync.log 2>&1
```

See [docs/references/CRON_SETUP.md](docs/references/CRON_SETUP.md) for details on cron schedules, log management, and troubleshooting.

## Development

```bash
# Install in development mode
uv tool install -e .

# Run tests
just test

# Run full quality gate (lint + format + type check + tests + vulture + pymarkdown)
just check

# Quick fix (auto-fix lint + format)
just fix

# Show all available just commands
just
```

## Project Resources

- **Pocket product**: [heypocket.com](https://heypocket.com/pages/home-v2c)
- **Pocket API docs**: [docs.heypocketai.com/docs/api](https://docs.heypocketai.com/docs/api)
- **API base URL**: `https://public.heypocketai.com/api/v1`
