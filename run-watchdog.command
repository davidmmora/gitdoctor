#!/usr/bin/env bash
# GitDoctor Vigilante - Launcher para macOS
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$DIR/agent.py" ]; then
    for cand in "$HOME/Repos/gitdoctor" "$HOME/repos/gitdoctor"; do
        if [ -f "$cand/agent.py" ]; then
            DIR="$cand"
            break
        fi
    done
fi
python3 "$DIR/agent.py" /vigilante
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
