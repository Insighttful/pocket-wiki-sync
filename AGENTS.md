# Development Conventions

**Always ask for permission prior to committing.**

## Child AGENTS.md (Recurse for module-specific knowledge)

- [modules/AGENTS.md](modules/AGENTS.md) - Strong models/services
- [shared/AGENTS.md](shared/AGENTS.md) - Weak models, clients, cross-cutting concerns
- [docs/AGENTS.md](docs/AGENTS.md) - Documentation structure

## Project Structure

- Projects: `~/dev/*`
- **Root files**: `cli.py`, `README.md`, `pyproject.toml` stay in project root (GitHub convention)
- **scripts/**: Executable scripts stay in project root
- **modules/**: Strong models/services (modular, orthogonal)
- **shared/**: Weak models, clients, cross-cutting concerns (e.g., `environment.py` with pydantic-settings)

## Import Conventions

This project is an application, not a library. Follow these rules:

1. **No `__all__`.** Never define `__all__` in any module.
2. **No import switchboards.** Never re-export symbols in `__init__.py`. The `__init__.py` files should only contain a docstring (or be empty).
3. **Full explicit import paths.** Every import must reference the defining module directly:

   ```python
   # Good
   from shared.pocket.models import HeyPocketRecording
   from shared.pocket.client import HeyPocketClient
   from shared.pocket.config import HeyPocketConfig
   from shared.environment import get_wiki_env, get_heypocket_env, get_sync_env
   from shared.sync_state import SyncLock, SyncState

   # Bad — import switchboard (don't do this)
   from shared import HeyPocketRecording
   from shared import HeyPocketClient, HeyPocketConfig
   ```

## Dependency Management

Use global `uv`. Dev deps: `ruff`, `ty`, `pytest`, `vulture`, `pre-commit`.

## Tool Configuration

Prefer `pyproject.toml` as the configuration surface for all tools. If a tool supports reading from `pyproject.toml` (e.g., `ruff`, `pytest`, `pymarkdownlnt`), add its config under a `[tool.<name>]` section rather than creating a standalone config file. This keeps the project root tidy and all configuration in one place.

## pre-commit

Run on every commit. Order: ruff-fix → ruff-format → ruff-check → ty → detect-secrets → pytest → vulture (min-confidence=65) → pymarkdown. No errors/warnings.

## Test Structure

- **Single file module** (`cli.py`): `tests/test_cli.py`
- **Package module** (`client/`): `client/tests/test_client.py`

Example:

```text
cli.py
tests/test_cli.py
modules/
├── wiki.py
└── tests/test_wiki.py
shared/
├── pocket/
│   ├── __init__.py
│   ├── models.py
│   ├── config.py
│   ├── client.py
│   └── tests/test_client.py
```

## Documentation

All docs in `docs/`. Reference docs in `docs/references/`. Plans in `docs/plans/`.

## Module AGENTS.md Hierarchy

Every module under `modules/`, `shared/`, and `docs/` must have its own `AGENTS.md` scoped to that module. Parent modules reference child `AGENTS.md` files via relative paths.

**Always recurse the AGENTS.md hierarchy and keep relationships/paths up to date.**

---

## Pocket Wiki Sync

Syncs HeyPocket AI recordings/transcripts to a local wiki (Obsidian-compatible) via CLI or CRON.
Single responsibility: fetch from HeyPocket API → save transcripts as markdown to WIKI_RAW_PATH.

### Core Principles

- KISS, ergonomic, 12-factor-aligned:
  - Config + secrets in `.env` via pydantic-settings (source of truth; .env values win over os.environ).
  - No in-memory env pollution across runs/commands.
  - Runtime/temporal state (last sync) in a single file (`/project-root/.last-sync`), not in `.env`.
- WIKI_RAW_PATH is exactly where transcripts are saved; no magic subdirectories.

### API

- Base URL: `https://public.heypocketai.com/api/v1`
- Auth: Bearer token (`pk_xxx`) in Authorization header
- API key loaded from `.env` via pydantic-settings

### Setup

```bash
cd ~/dev/pocket-wiki-sync
uv pip install -e .
```

Config in `.env`:

```bash
HEYPOCKET_API_KEY=pk_xxx
WIKI_RAW_PATH=~/wiki/raw   # or any path where you want transcripts saved
```

On first run, if WIKI_RAW_PATH is not set, the CLI prompts once and writes it to .env.

### Usage

Default behavior: fetch and sync all unsynced recordings. Use `--max N` only if you want to limit a single run.

```bash
pocket-wiki sync               # Fetch all unsynced recordings
pocket-wiki sync --max 10      # Limit this run to 10
pocket-wiki sync --dry-run     # Preview what would be synced
pocket-wiki sync --verbose     # Detailed logs for debugging
pocket-wiki list-synced        # List synced recordings (local files only)
pocket-wiki show-config        # Show config + validate API key
pocket-wiki clean              # Clean up state files (--all to delete recordings)
```

### Sync State

- Last sync timestamp stored in `.last-sync` at project root (gitignored). This is the single source of truth; no backup copies.
- On each run:
  - Fetches recordings from last sync date.
  - Filters out any not newer than the exact last_sync_dt.
  - Optionally ignores “personal”/“private” tags (default: enabled via IGNORE_PRIVATE_TAGS).

### Output

Transcripts are saved directly under WIKI_RAW_PATH as:
`<YYYY-MM-DD>-<slug>.md`

No extra directories are created by this tool.
