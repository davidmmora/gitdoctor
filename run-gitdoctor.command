#!/usr/bin/env bash
# GitDoctor AI - Suite Clinica de Salud de Repositorios (macOS Launcher)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ ! -f "$DIR/agent.py" ]; then
    for cand in "$HOME/Repos/_sync" "$HOME/repos/_sync" "$HOME/Repos/repos-sync"; do
        if [ -f "$cand/agent.py" ]; then
            DIR="$cand"
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
