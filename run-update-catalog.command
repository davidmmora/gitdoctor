#!/usr/bin/env bash
# GitDoctor - Actualizar Catalogo para macOS
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$DIR/sync.sh" ]; then
    for cand in "$HOME/Repos/gitdoctor" "$HOME/repos/gitdoctor"; do
        if [ -f "$cand/sync.sh" ]; then
            DIR="$cand"
            break
        fi
    done
fi
"$DIR/sync.sh" --update-catalog
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
