#!/usr/bin/env bash
# GitDoctor - Actualizar Catalogo para macOS
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$DIR/sync.sh" ]; then
    for cand in "$HOME/Repos/gitdoctor" "$HOME/repos/gitdoctor" "$HOME/Documents/Repos/gitdoctor"; do
        if [ -f "$cand/sync.sh" ]; then
            DIR="$cand"
            break
        fi
    done
fi

if [ ! -f "$DIR/sync.sh" ]; then
    echo "[ERROR] No se pudo encontrar sync.sh en las rutas conocidas de GitDoctor."
    read -p "Presiona Enter para cerrar esta ventana..."
    exit 1
fi

"$DIR/sync.sh" --update-catalog
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
