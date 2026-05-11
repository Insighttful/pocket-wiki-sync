# pocket-wiki-sync development tasks
#
# Common commands:
#   just                - List available commands
#   just install        - Install package in dev mode
#   just test           - Run tests
#   just check          - Full quality gate (pre-commit --all-files)
#   just fix            - Auto-fix lint + format
#   just clean-pyc      - Remove __pycache__ directories

default:
    @just --list

# Install the package in development mode
install:
    uv tool install -e .

# Install with dev dependencies
install-dev:
    uv sync --dev

# Run tests (pass extra args after --, e.g. just test -- -k "test_sync")
test *args="":
    uv run pytest --strict-markers -q {{args}}

# Run tests with coverage
test-cov *args="":
    uv run pytest --strict-markers -q --cov=modules --cov=shared --cov=cli.py {{args}}

# Run ruff linter
lint:
    uv run ruff check .

# Auto-fix lint issues
lint-fix:
    uv run ruff check --fix .

# Format code with ruff
format:
    uv run ruff format .

# Check formatting without changing files
format-check:
    uv run ruff format --check .

# Full quality gate (pre-commit on all files)
check: quality-gate

quality-gate:
    uv run pre-commit run --all-files

# Auto-fix lint issues and format
fix: lint-fix format

# Remove Python bytecode / __pycache__ directories
clean-pyc:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; true
    find . -type f -name '*.pyc' -delete

# Remove all build/development caches
clean-cache: clean-pyc
    rm -rf .ruff_cache .pytest_cache .mypy_cache
    rm -rf *.egg-info
    rm -rf .coverage coverage.xml htmlcov

# Full clean including sync state files
clean-all: clean-cache
    rm -f .last-sync .sync-lock

# Alias: full clean
clean: clean-all

# Run vulture dead code detection
vulture:
    uv run vulture . --min-confidence=90 --exclude=.venv

# Run ty type checker
ty:
    uv run ty check --error-on-warning

# Run deptry dependency checker
deptry:
    uv run deptry .
