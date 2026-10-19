#!/usr/bin/env bash
# ==============================================================================
# reconcile-mac.sh -- Auditoria y Reconciliacion para macOS
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPOS_DIR="$(cd "$DIR/.." && pwd)"

if [ -n "$1" ]; then
    REPOS_DIR="$1"
fi

python3 "$DIR/reconcile.py" "$REPOS_DIR"
