# Modules

Strong models and services (modular, orthogonal modules).

## Structure

```text
modules/
├── wiki.py         # WikiOutput - saves recordings to markdown
└── tests/
    └── test_wiki.py
```

## Child Modules

- [wiki/](wiki/AGENTS.md) - if wiki becomes a package

## Key Knowledge for Agents

### CLI (project root `cli.py`)

- Entry point: `cli:app`
- Commands:
  - `sync` - Fetch new recordings and save to wiki
  - `list-synced` - List locally synced recordings
  - `show-config` - Show configuration and validate API key
  - `clean` - Clean up sync state files and recordings
- Uses `HeyPocketClient` from `shared` for API calls
- Uses `WikiOutput` for file output

### Wiki Output (modules/wiki.py)

- `WikiOutput` class saves recordings as markdown
- Output format: frontmatter + title + summary + transcript
- Creates index at `concepts/pocket-sources.md`
- Creates sync logs at `queries/pocket-sync-YYYY-MM-DD.md`
