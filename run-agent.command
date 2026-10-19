#!/usr/bin/env bash
# GitDoctor AI - Suite Clinica de Repositorios (macOS Launcher)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$DIR/agent.py" ]; then
    for cand in "$HOME/Repos/_sync/agent.py" "$HOME/repos/_sync/agent.py" "$HOME/Repos/repos-sync/agent.py"; do
        if [ -f "$cand" ]; then
            DIR="$(dirname "$cand")"
            break
        fi
    done
fi

# Auto-actualizar silenciosamente si hay conexion con origin
if [ -d "$DIR/.git" ]; then
    git -C "$DIR" pull -q --ff-only 2>/dev/null || true
fi

python3 "$DIR/agent.py" "$@"
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
