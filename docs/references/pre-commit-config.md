# Pre-commit Configuration

## Overview

Configure pre-commit to run linting, typing, and testing on `pre-push`.
No errors or warnings allowed (treat warnings like errors).

## Full Configuration

See `.pre-commit-config.yaml` in project root for complete setup.

### Key Dependencies

- `ruff` - Linting and formatting
- `ty` - Type checking
- `pytest` - Testing
- `vulture` - Dead code detection (optional)

### Pre-push Hook

```bash
pre-commit run --from-ref main --to-ref HEAD
```

Or configure in CI/CD pipeline before merge.
