#!/usr/bin/env bash
# ==============================================================================
# setup-mac.sh -- Instalador y Configurador para macOS
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
GRANDPARENT_DIR="$(cd "$PARENT_DIR/.." && pwd)"

PARENT_NAME="$(basename "$PARENT_DIR")"
GRANDPARENT_NAME="$(basename "$GRANDPARENT_DIR" | tr '[:upper:]' '[:lower:]')"

# Si GitDoctor reside en Personal/gitdoctor u otra organizacion oficial, REPOS_DIR es el abuelo
if [[ "$PARENT_NAME" =~ ^(Personal|th-mex|w-amarillo|w-azul|w-naranja|interpec|w-pluma|w-ic|bf-agency|WeHubs-io)$ ]] || [[ "$GRANDPARENT_NAME" =~ ^(repos|proyectos|developer)$ ]]; then
    REPOS_DIR="$GRANDPARENT_DIR"
else
    REPOS_DIR="$PARENT_DIR"
fi

REAJUSTE_MODE=false
if [ "$1" = "--reajuste" ] || [ "$1" = "--quiet" ] || [ "$1" = "-q" ]; then
    REAJUSTE_MODE=true
fi

C_RESET="\033[0m"
C_CYAN="\033[36m"
C_GREEN="\033[32m"
C_YELLOW="\033[33m"
C_WHITE="\033[1;37m"

if [ "$REAJUSTE_MODE" = false ]; then
    echo ""
    echo -e "${C_CYAN}==========================================================${C_RESET}"
    echo -e "${C_CYAN}  GitDoctor -- Instalador de Suite de Salud y Git (macOS)${C_RESET}"
    echo -e "${C_CYAN}==========================================================${C_RESET}"
    echo ""
fi

# 1. Asignar permisos de ejecucion a los scripts
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "${C_YELLOW}[1/6] Asignando permisos de ejecucion a los scripts...${C_RESET}"
fi
chmod +x "$SCRIPT_DIR"/*.sh 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.command 2>/dev/null || true
chmod +x "$SCRIPT_DIR"/*.py 2>/dev/null || true
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "      ${C_GREEN}[OK] Permisos asignados.${C_RESET}"
fi

# 2. Verificar GitHub CLI
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "${C_YELLOW}[2/6] Verificando estado de GitHub CLI...${C_RESET}"
    if command -v gh &>/dev/null; then
        GH_USER=$(gh api user --jq .login 2>/dev/null || true)
        if [ -n "$GH_USER" ]; then
            echo -e "      ${C_GREEN}[OK] GitHub CLI conectado como @$GH_USER${C_RESET}"
        else
            echo -e "      ${C_YELLOW}[INFO] GitHub CLI detectado sin sesion. Usa 'reposync-ai' o 'gh auth login' para iniciar sesion.${C_RESET}"
        fi
    else
        echo -e "      ${C_YELLOW}[INFO] GitHub CLI ('gh') no detectado. Se recomienda instalar con: brew install gh${C_RESET}"
    fi
fi

# 3. Configurar Git global para macOS y blindar GitDoctor contra ruido de permisos
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "${C_YELLOW}[3/6] Configurando parametros de Git recomendados para Mac...${C_RESET}"
fi
git config --global core.autocrlf input 2>/dev/null || true
git -C "$SCRIPT_DIR" config core.filemode false 2>/dev/null || true
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "      ${C_GREEN}[OK] Git configurado (core.autocrlf=input, core.filemode=false).${C_RESET}"
fi

# 4. Configurar comandos globales 'gitdoctor' y 'gitdoc' en el shell (.zshrc / .bashrc)
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "${C_YELLOW}[4/6] Configurando comandos globales 'gitdoctor' y 'gitdoc' en tu terminal...${C_RESET}"
fi

# Limpiar enlaces simbolicos viejos o rotos en la raiz de repos
for legacy in "_sync" "repos-sync"; do
    if [ -L "$REPOS_DIR/$legacy" ]; then
        rm -f "$REPOS_DIR/$legacy" 2>/dev/null || true
    fi
done

# Limpiar clones duplicados o redundantes de GitDoctor en otras carpetas
for dup in "$REPOS_DIR/_gitdoctor" "$REPOS_DIR/gitdoctor" "$REPOS_DIR/Personal/gitdoctor" "$REPOS_DIR/Personal/repos-sync"; do
    if [ -d "$dup" ]; then
        DUP_CANONICAL="$(cd "$dup" 2>/dev/null && pwd || true)"
        if [ -n "$DUP_CANONICAL" ] && [ "$DUP_CANONICAL" != "$SCRIPT_DIR" ]; then
            if [ -f "$dup/agent.py" ]; then
                rm -rf "$dup" 2>/dev/null || true
            fi
        fi
    fi
done

SHELL_BLOCK="# >>> GitDoctor Global Commands >>>
gitdoctor() {
    local target=\"\"
    for d in \"$SCRIPT_DIR\" \"\$HOME/Repos/Personal/gitdoctor\" \"\$HOME/repos/Personal/gitdoctor\" \"\$HOME/Repos/_gitdoctor\" \"\$HOME/repos/_gitdoctor\" \"\$HOME/Repos/gitdoctor\" \"\$HOME/repos/gitdoctor\" \"\$HOME/Repos/_sync\" \"\$HOME/repos/_sync\" \"\$HOME/Repos/repos-sync\" \"\$HOME/repos/repos-sync\"; do
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
        echo \"[ERROR] No se encontro agent.py en las rutas conocidas de GitDoctor.\"
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

# 5. Crear accesos directos de doble clic en el Escritorio de Mac
if [ "$REAJUSTE_MODE" = false ]; then
    echo -e "${C_YELLOW}[5/6] Creando accesos directos en el Escritorio de Mac...${C_RESET}"
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

# 6. Diagnostico de onboarding, auditoria de seguridad y reconciliacion
echo -e "${C_YELLOW}[6/6] Verificando estructura de carpetas y ejecutando auditoria...${C_RESET}"
python3 "$SCRIPT_DIR/onboarding.py" "$REPOS_DIR" || true
python3 "$SCRIPT_DIR/reconcile.py" "$REPOS_DIR"

echo -e "\n${C_YELLOW}[*] Procediendo con la sincronizacion y descarga de repositorios faltantes...${C_RESET}"
"$SCRIPT_DIR/sync.sh"

echo ""
echo -e "${C_GREEN}==========================================================${C_RESET}"
echo -e "${C_GREEN}  ¡Instalacion completada con exito en tu Mac!${C_RESET}"
echo -e "${C_WHITE}  A partir de ahora usa 'gitdoctor' (o 'gitdoc') en tu${C_RESET}"
echo -e "${C_WHITE}  terminal para tener todo diagnosticado y al dia.${C_RESET}"
echo -e "${C_GREEN}==========================================================${C_RESET}"
echo ""
