#!/usr/bin/env bash
# detect-secrets hook wrapper with clear DX messages.
# Hard-fails on new patterns so you can review; ignores cosmetic timestamp-only changes.
set -euo pipefail

BASELINE=".secrets.baseline"

# Save original baseline (if it exists).
ORIG=""
if [ -f "$BASELINE" ]; then
  ORIG=$(cat "$BASELINE")
fi

# Run scan (detect-secrets may update baseline in-place).
uv run -- detect-secrets scan --baseline "$BASELINE" || {
  echo ""
  echo "⚠ detect-secrets failed during scan."
  echo "Run:"
  echo "  git diff .secrets.baseline"
  echo "If changes are safe (test data, example keys), stage and commit them."
  echo "If a real secret was detected, remove it from code and use an env var instead."
  echo ""
  exit 1
}

# If baseline didn't exist before, nothing to compare.
if [ -z "$ORIG" ]; then
  exit 0
fi

CURRENT=$(cat "$BASELINE")

# Normalize by removing generated_at so we only care about real pattern changes.
normalize() {
  sed '/"generated_at"/d' | tr -d ' \t\n\r'
}

if [ "$(echo "$ORIG" | normalize)" = "$(echo "$CURRENT" | normalize)" ]; then
  # Only timestamp changed (or whitespace); restore original to avoid noisy baseline churn.
  echo "$ORIG" > "$BASELINE"
  exit 0
fi

# Actual patterns changed: hard-fail so you can review.
echo ""
echo "⚠ detect-secrets updated .secrets.baseline with new patterns."
echo "Run:"
echo "  git diff .secrets.baseline"
echo "If changes are safe (test data, example keys), stage and commit them."
echo "If a real secret was detected, remove it from code and use an env var instead."
echo ""
exit 1
