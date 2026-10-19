#!/usr/bin/env bash
# ==============================================================================
# reconcile-mac.sh -- Auditoria y Reconciliacion para macOS
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ -n "$1" ]; then
    python3 "$DIR/reconcile.py" "$1"
else
    python3 "$DIR/reconcile.py"
fi
