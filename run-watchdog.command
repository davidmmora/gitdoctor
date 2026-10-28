#!/usr/bin/env bash
# GitDoctor Vigilante - Launcher para macOS
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$DIR/agent.py" ]; then
    for cand in "$HOME/Repos/gitdoctor" "$HOME/repos/gitdoctor" "$HOME/Documents/Repos/gitdoctor"; do
        if [ -f "$cand/agent.py" ]; then
            DIR="$cand"
            break
        fi
    done
fi

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] python3 no esta disponible en tu sistema."
    read -p "Presiona Enter para cerrar esta ventana..."
    exit 1
fi

if [ ! -f "$DIR/agent.py" ]; then
    echo "[ERROR] No se pudo encontrar agent.py en las rutas conocidas de GitDoctor."
    read -p "Presiona Enter para cerrar esta ventana..."
    exit 1
fi

python3 "$DIR/agent.py" /vigilante
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
