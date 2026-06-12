#!/usr/bin/env bash
# Install Baysix tracked git hooks into .git/hooks. Idempotent. Re-run after pulling.
set -euo pipefail
REPO="$(git rev-parse --show-toplevel)"
SRC="$REPO/.claude/hooks/git"
DST="$REPO/.git/hooks"
for hook in pre-commit; do
  cp "$SRC/$hook" "$DST/$hook"
  chmod +x "$DST/$hook"
  echo "installed: $DST/$hook"
done
