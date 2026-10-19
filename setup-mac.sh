#!/usr/bin/env bash
# ==============================================================================
# setup-mac.sh -- Instalador y Configurador para macOS
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PARENT_NAME="$(basename "$PARENT_DIR")"

# Modo reajuste rapido (silencioso, invocado por sync o launchers)
REAJUSTE_MODE=false
if [ "$1" = "--reajuste" ] || [ "$1" = "--quiet" ] || [ "$1" = "-q" ]; then
    REAJUSTE_MODE=true
fi

C_RESET="\033[0m"
C_CYAN="\033[36m"
C_GREEN="\033[32m"
C_YELLOW="\033[33m"
C_WHITE="\033[1;37m"
C_GRAY="\033[90m"

# Verificar que python3 este disponible
if ! command -v python3 &>/dev/null; then
    echo -e "\033[31m[ERROR] python3 no esta instalado en este equipo.\033[0m"
    echo -e "\033[33mInstalalo con: brew install python3 o descargalo de https://python.org\033[0m"
    exit 1
fi

LOCAL_CFG="$SCRIPT_DIR/config.local.json"

# En modo interactivo, ejecutar primero el asistente de configuracion completo
if [ "$REAJUSTE_MODE" = false ]; then
    python3 "$SCRIPT_DIR/onboarding.py" --interactive-setup
fi

# Leer configuracion establecida por el asistente
REPOS_DIR="$PARENT_DIR"
DOWNLOAD_ON_SETUP=true
if [ -f "$LOCAL_CFG" ]; then
    CFG_REPOS=$(python3 -c "import json; print(json.load(open('$LOCAL_CFG')).get('repos_dir', ''))" 2>/dev/null || true)
    if [ -n "$CFG_REPOS" ] && [ -d "$CFG_REPOS" ]; then
        REPOS_DIR="$CFG_REPOS"
    fi
    CFG_DL=$(python3 -c "import json; print(json.load(open('$LOCAL_CFG')).get('download_on_setup', True))" 2>/dev/null || true)
    if [ "$CFG_DL" = "False" ] || [ "$CFG_DL" = "false" ]; then
        DOWNLOAD_ON_SETUP=false
    fi
fi

if [ "$REAJUSTE_MODE" = false ]; then
    echo ""
    echo -e "${C_CYAN}==========================================================${C_RESET}"
    echo -e "${C_CYAN}  GitDoctor -- Integracion con el Sistema (macOS)         ${C_RESET}"
    echo -e "${C_CYAN}==========================================================${C_RESET}"
    echo -e "${C_GRAY}  Carpeta raiz de proyectos: ${C_WHITE}$REPOS_DIR${C_RESET}"
    echo -e "${C_GRAY}  Ubicacion de GitDoctor:    ${C_WHITE}$SCRIPT_DIR${C_RESET}"
    echo ""
fi

# 1. Asignar permisos de ejecucion a los scripts
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "${C_YELLOW}[1/4] Asignando permisos de ejecucion a scripts y launchers...${C_RESET}"
fi
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.command 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.py 2>/dev/null || true
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "      ${C_GREEN}[OK] Permisos asignados.${C_RESET}"
fi

# 2. Configurar Git global para macOS y blindar GitDoctor contra ruido de permisos
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "${C_YELLOW}[2/4] Configurando parametros de Git recomendados para Mac...${C_RESET}"
fi
git config --global core.autocrlf input 2>/dev/null || true
git -C "$SCRIPT_DIR" config core.filemode false 2>/dev/null || true
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "      ${C_GREEN}[OK] Git configurado (core.autocrlf=input, core.filemode=false).${C_RESET}"
fi

# 3. Configurar comandos globales 'gitdoctor' y 'gitdoc' en el shell (.zshrc / .bash_profile)
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "${C_YELLOW}[3/4] Configurando comandos globales 'gitdoctor' y 'gitdoc' en tu terminal...${C_RESET}"
fi

# Limpiar enlaces simbolicos viejos o rotos en la raiz de repos
for legacy in "_sync" "repos-sync"; do
    if [ -L "$REPOS_DIR/$legacy" ]; then
        rm -f "$REPOS_DIR/$legacy" 2>/dev/null || true
    fi
done

SHELL_BLOCK="# >>> GitDoctor Global Commands >>>
gitdoctor() {
    local target=\"\"
    for d in \"$SCRIPT_DIR\" \"\$HOME/Repos/gitdoctor\" \"\$HOME/repos/gitdoctor\"; do
        if [ -f \"\$d/agent.py\" ]; then target=\"\$d\"; break; fi
    done
    if [ -n \"\$target\" ]; then
        if [ \"\$1\" = \"--sync\" ] || [ \"\$1\" = \"sync\" ]; then
            shift
            \"\$target/sync.sh\" \"\$@\"
        else
            python3 \"\$target/agent.py\" \"\$@\"
        fi
    else
        echo \"[ERROR] No se encontro agent.py en las rutas conocidas de GitDoctor (~/Repos/gitdoctor).\"
        return 1
    fi
}

alias gitdoc=\"gitdoctor\"

# Alias de sincronizacion directa y compatibilidad
reposync() {
    gitdoctor --sync \"\$@\"
}
reposync-ai() {
    gitdoctor \"\$@\"
}
# <<< GitDoctor Global Commands <<<"

for TARGET_RC in "$HOME/.zshrc" "$HOME/.bash_profile"; do
    if [ -f "$TARGET_RC" ]; then
        python3 -c "
import re
path = '$TARGET_RC'
with open(path, 'r', encoding='utf-8', errors='replace') as f:
    c = f.read()
# Reemplazar bloques viejos de RepoSync o GitDoctor
pattern_old = r'# >>> (?:RepoSync|GitDoctor) Global (?:Alias|Commands) >>>[\s\S]*?# <<< (?:RepoSync|GitDoctor) Global (?:Alias|Commands) <<<'
new_block = '''$SHELL_BLOCK'''
if re.search(pattern_old, c):
    c = re.sub(pattern_old, new_block, c)
else:
    c = re.sub(r'alias reposync=.*?\n', '', c)
    c = re.sub(r'alias reposync-ai=.*?\n', '', c)
    c = re.sub(r'alias gitdoc=.*?\n', '', c)
    c = c.rstrip() + '\n\n' + new_block + '\n'
with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
"
    fi
done
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "      ${C_GREEN}[OK] Comandos globales 'gitdoctor' y 'gitdoc' configurados en tu terminal.${C_RESET}"
fi

# 4. Crear accesos directos de doble clic en el Escritorio de Mac
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "${C_YELLOW}[4/4] Creando accesos directos en el Escritorio de Mac...${C_RESET}"
fi
DESKTOP_DIR="$HOME/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
    rm -f "$DESKTOP_DIR"/RepoSync*.command 2>/dev/null || true

    cat << EOF > "$DESKTOP_DIR/GitDoctor - Consola & IA.command"
#!/usr/bin/env bash
python3 "$SCRIPT_DIR/agent.py"
EOF

    cat << EOF > "$DESKTOP_DIR/GitDoctor - Salud 360.command"
#!/usr/bin/env bash
python3 "$SCRIPT_DIR/agent.py" /seguridad
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
EOF

    cat << EOF > "$DESKTOP_DIR/GitDoctor - Sincronizar.command"
#!/usr/bin/env bash
"$SCRIPT_DIR/sync.sh"
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
EOF

    cat << EOF > "$DESKTOP_DIR/GitDoctor - Vigilante.command"
#!/usr/bin/env bash
python3 "$SCRIPT_DIR/agent.py" /vigilante
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
EOF

    cat << EOF > "$DESKTOP_DIR/GitDoctor - Salida Segura.command"
#!/usr/bin/env bash
python3 "$SCRIPT_DIR/agent.py" /apagar
echo ""
read -p "Presiona Enter para cerrar esta ventana..."
EOF

    chmod +x "$DESKTOP_DIR"/GitDoctor*.command 2>/dev/null || true
    if [ "$REAJUSTE_MODE" = false ]; then
        echo -e "      ${C_GREEN}[OK] 5 Accesos directos de GitDoctor creados en tu Escritorio de Mac.${C_RESET}"
    fi
else
    if [ "$REAJUSTE_MODE" = false ]; then
        echo -e "      [INFO] No se encontro ~/Desktop; los accesos directos quedan dentro de GitDoctor."
    fi
fi

# Si se invoco en modo reajuste silencioso, finalizamos aqui
if [ "$REAJUSTE_MODE" = true ]; then
    exit 0
fi

# 5. Auditoria de seguridad y reconciliacion
echo -e "\n${C_YELLOW}[*] Ejecutando reconciliacion de carpetas...${C_RESET}"
python3 "$SCRIPT_DIR/reconcile.py" "$REPOS_DIR"

# 6. Sincronizacion inicial si fue solicitada en la instalacion
if [ "$DOWNLOAD_ON_SETUP" = true ]; then
    echo -e "\n${C_YELLOW}[*] Procediendo con la sincronizacion y descarga de repositorios faltantes...${C_RESET}"
    "$SCRIPT_DIR/sync.sh"
else
    echo -e "\n${C_CYAN}[INFO] Modo bajo demanda activo. Tus proyectos estan catalogados en repos.local.json.${C_RESET}"
    echo -e "${C_GRAY}Para clonar cualquier repositorio cuando lo requieras usa: gitdoctor /clone <nombre>${C_RESET}"
    echo -e "${C_GRAY}O para sincronizar todo en cualquier momento usa:        gitdoctor --sync${C_RESET}"
fi

echo ""
echo -e "${C_GREEN}==========================================================${C_RESET}"
echo -e "${C_GREEN}  ¡Instalacion de GitDoctor completada con exito en tu Mac!${C_RESET}"
echo -e "${C_WHITE}  A partir de ahora usa 'gitdoctor' (o 'gitdoc') en tu${C_RESET}"
echo -e "${C_WHITE}  terminal para tener todo diagnosticado y al dia.${C_RESET}"
echo -e "${C_GREEN}==========================================================${C_RESET}"
echo ""
