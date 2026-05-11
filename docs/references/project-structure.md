# Project Structure Conventions

## Directory Layout

All development projects should live under `~/dev/*`.

## Standard Structure

```text
project-name/
├── .git/
├── AGENTS.md          # Project conventions (this file)
├── pyproject.toml     # Python project config
├── uv.lock            # Dependency lockfile
├── references/        # External documentation
│   └── *.md
├── src/               # Source code
│   └── package_name/
├── tests/             # Test files
└── scripts/           # Automation scripts
```

## Key Files

- `AGENTS.md` - Conventions and structure reference
- `pyproject.toml` - Project metadata and dependencies
- `uv.lock` - Locked dependency versions
