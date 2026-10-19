#!/usr/bin/env bash
# GitDoctor - Sincronizacion para macOS
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$DIR/sync.sh" ]; then
    for cand in "$HOME/Repos/_sync/sync.sh" "$HOME/repos/_sync/sync.sh" "$HOME/Repos/repos-sync/sync.sh"; do
        if [ -f "$cand" ]; then
            DIR="$(dirname "$cand")"
            break
        fi
    done
fi
"$DIR/sync.sh"
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
