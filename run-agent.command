#!/usr/bin/env bash
# GitDoctor AI - Suite Clinica de Repositorios (macOS Launcher)
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
    echo "[ERROR] python3 no esta instalado o no esta disponible en tu terminal."
    echo "Instalalo con: brew install python3 o desde https://python.org"
    read -p "Presiona Enter para cerrar esta ventana..."
    exit 1
fi

if [ ! -f "$DIR/agent.py" ]; then
    echo "[ERROR] No se pudo encontrar agent.py en las rutas conocidas de GitDoctor."
    echo "Ruta probada: $DIR"
    read -p "Presiona Enter para cerrar esta ventana..."
    exit 1
fi

# Auto-actualizar silenciosamente si hay conexion con origin
if [ -d "$DIR/.git" ]; then
    git -C "$DIR" pull -q --ff-only 2>/dev/null || true
fi

python3 "$DIR/agent.py" "$@"
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
