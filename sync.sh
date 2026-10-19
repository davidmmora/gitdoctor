#!/usr/bin/env bash
# ==============================================================================
# sync.sh -- Sincronizador inteligente de Repositorios (macOS / Linux)
# ==============================================================================

set -e

# Directorio del script y directorio padre de los repositorios
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

# Leer repos_dir personalizado si existe en config.local.json
LOCAL_CFG="$SCRIPT_DIR/config.local.json"
if [ -f "$LOCAL_CFG" ]; then
    CUSTOM_DIR=$(python3 -c "import json; print(json.load(open('$LOCAL_CFG')).get('repos_dir', ''))" 2>/dev/null || true)
    if [ -n "$CUSTOM_DIR" ] && [ -d "$CUSTOM_DIR" ]; then
        REPOS_DIR="$CUSTOM_DIR"
    fi
fi

# Resolver catalogo: repos.local.json o repos.json
CATALOG_FILE="$SCRIPT_DIR/repos.local.json"
if [ ! -f "$CATALOG_FILE" ]; then
    CATALOG_FILE="$SCRIPT_DIR/repos.json"
fi

AUTO_CLONE=true
AUTO_PULL=true
UPDATE_CATALOG=false

# Procesar argumentos
while [[ $# -gt 0 ]]; do
    case "$1" in
        --target-dir|-t)
            REPOS_DIR="$2"
            shift 2
            ;;
        --no-clone)
            AUTO_CLONE=false
            shift
            ;;
        --no-pull)
            AUTO_PULL=false
            shift
            ;;
        --update-catalog)
            UPDATE_CATALOG=true
            shift
            ;;
        -h|--help)
            echo "Uso: ./sync.sh [OPCIONES]"
            echo "  -t, --target-dir DIR Directorio donde residen los repositorios (por defecto ..)"
            echo "  --no-clone           No clonar repositorios faltantes"
            echo "  --no-pull            No hacer pull automatico de cambios remotos"
            echo "  --update-catalog     Escanear repositorios locales y actualizar repos.json"
            exit 0
            ;;
        *)
            shift
            ;;
    esac
done

# Colores ANSI
C_RESET="\033[0m"
C_CYAN="\033[36m"
C_GREEN="\033[32m"
C_YELLOW="\033[33m"
C_RED="\033[31m"
C_MAGENTA="\033[35m"
C_GRAY="\033[90m"
C_BOLD="\033[1m"

echo ""
echo -e "${C_CYAN}========================================================${C_RESET}"
echo -e "${C_CYAN}  GitDoctor -- Sincronizador Multihilo de Repositorios  ${C_RESET}"
echo -e "${C_GRAY}  Directorio de Repos: $REPOS_DIR${C_RESET}"
echo -e "${C_CYAN}========================================================${C_RESET}"
echo ""

# 0. Auto-actualizar GitDoctor si es repositorio Git
if [ -d "$SCRIPT_DIR/.git" ]; then
    if git -C "$SCRIPT_DIR" remote get-url origin &>/dev/null; then
        echo -e "${C_GRAY}[*] Comprobando actualizaciones de GitDoctor...${C_RESET}"
        PULL_OUT=$(git -C "$SCRIPT_DIR" pull -q --ff-only 2>&1 || true)
    fi
fi

# Auto-reajuste transparente (permisos, lanzadores y comandos globales)
if [ -f "$SCRIPT_DIR/setup-mac.sh" ]; then
    bash "$SCRIPT_DIR/setup-mac.sh" --reajuste &>/dev/null || true
fi

# Limpiar enlaces obsoletos o rotos en la raiz de repos
for legacy in "_sync" "repos-sync"; do
    if [ -L "$REPOS_DIR/$legacy" ]; then
        rm -f "$REPOS_DIR/$legacy" 2>/dev/null || true
    fi
done

# Verificar si python3 esta disponible
if ! command -v python3 &>/dev/null; then
    echo -e "${C_RED}[ERROR] python3 no esta disponible en tu sistema. Se requiere para parsear el catalogo.${C_RESET}"
    exit 1
fi

# 1. Actualizar catalogo si se solicita o no existe
if [ "$UPDATE_CATALOG" = true ] || [ ! -f "$CATALOG_FILE" ]; then
    echo -e "${C_YELLOW}[*] Escaneando repositorios con remoto para actualizar repos.json...${C_RESET}"
    python3 -c "
import os, subprocess, json

repos_dir = '$REPOS_DIR'
entries = []

for item in sorted(os.listdir(repos_dir)):
    if item in ['_gitdoctor', '_sync', 'gitdoctor', 'repos-sync'] or item.startswith('.'):
        continue
    full_path = os.path.join(repos_dir, item)
    if not os.path.isdir(full_path):
        continue

    if os.path.isdir(os.path.join(full_path, '.git')):
        try:
            remote = subprocess.check_output(['git', '-C', full_path, 'remote', 'get-url', 'origin'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
            if remote:
                branch = subprocess.check_output(['git', '-C', full_path, 'branch', '--show-current'], stderr=subprocess.DEVNULL).decode('utf-8').strip() or 'main'
                entries.append({
                    'name': item,
                    'group': 'General',
                    'path': item,
                    'url': remote,
                    'defaultBranch': branch
                })
        except Exception:
            pass
    else:
        for sub in sorted(os.listdir(full_path)):
            sub_path = os.path.join(full_path, sub)
            if os.path.isdir(os.path.join(sub_path, '.git')):
                try:
                    remote = subprocess.check_output(['git', '-C', sub_path, 'remote', 'get-url', 'origin'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
                    if remote:
                        branch = subprocess.check_output(['git', '-C', sub_path, 'branch', '--show-current'], stderr=subprocess.DEVNULL).decode('utf-8').strip() or 'main'
                        entries.append({
                            'name': sub,
                            'group': item,
                            'path': f'{item}/{sub}',
                            'url': remote,
                            'defaultBranch': branch
                        })
                except Exception:
                    pass

with open('$CATALOG_FILE', 'w', encoding='utf-8') as f:
    json.dump(entries, f, indent=4, ensure_ascii=False)

print(f'[OK] Catalogo repos.json actualizado ({len(entries)} repositorios).\n')
"
fi

if [ ! -f "$CATALOG_FILE" ]; then
    echo -e "${C_RED}[ERROR] No se encontro repos.json en $SCRIPT_DIR.${C_RESET}"
    exit 1
fi

# 2. Verificar y clonar repositorios faltantes
if [ "$AUTO_CLONE" = true ]; then
    python3 -c "
import os, json, subprocess, sys

catalog_file = '$CATALOG_FILE'
repos_dir = '$REPOS_DIR'
script_dir = os.path.dirname(catalog_file)

cfg_file = os.path.join(script_dir, 'config.local.json')
disabled_orgs = []
if os.path.isfile(cfg_file):
    try:
        with open(cfg_file, 'r', encoding='utf-8') as cf:
            cdata = json.load(cf)
            disabled_orgs = cdata.get('disabled_orgs', [])
    except Exception:
        pass

with open(catalog_file, 'r', encoding='utf-8-sig') as f:
    catalog = json.load(f)

if disabled_orgs:
    catalog = [c for c in catalog if c.get('group') not in disabled_orgs]

for item in catalog:
    if item.get('name') in ['gitdoctor', 'repos-sync'] or item.get('url', '').endswith('/gitdoctor.git') or item.get('url', '').endswith('/repos-sync.git'):
        continue

    rel_path = item.get('path', os.path.join(item.get('group', ''), item['name']))
    target = os.path.join(repos_dir, rel_path)
    parent_dir = os.path.dirname(target)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir, exist_ok=True)

    if not os.path.exists(target):
        grp = item.get('group', '')
        print(f'\033[35m[CLONE] Clonando en {grp}/{item[\"name\"]}...\033[0m')
        res = subprocess.run(['git', 'clone', item['url'], target])
        if res.returncode == 0:
            print(f'        \033[32m[OK] {item[\"name\"]} clonado con exito.\033[0m\n')
        else:
            print(f'        \033[31m[ERROR] No se pudo clonar {item[\"name\"]}.\033[0m\n')
"
fi

# 3. Comprobar estado de cada repositorio
echo -e "${C_YELLOW}[*] Verificando estado y sincronizacion con GitHub...${C_RESET}"

python3 -c "
import os, json, subprocess, sys
from collections import OrderedDict

catalog_file = '$CATALOG_FILE'
repos_dir = '$REPOS_DIR'
script_dir = os.path.dirname(catalog_file)
auto_pull = ('$AUTO_PULL' == 'true')

cfg_file = os.path.join(script_dir, 'config.local.json')
disabled_orgs = []
if os.path.isfile(cfg_file):
    try:
        with open(cfg_file, 'r', encoding='utf-8') as cf:
            cdata = json.load(cf)
            disabled_orgs = cdata.get('disabled_orgs', [])
    except Exception:
        pass

with open(catalog_file, 'r', encoding='utf-8-sig') as f:
    catalog = json.load(f)

if disabled_orgs:
    catalog = [c for c in catalog if c.get('group') not in disabled_orgs]
    print(f'\033[90m[INFO] Sincronizacion selectiva: Omitiendo {len(disabled_orgs)} organizaciones ({', '.join(disabled_orgs)})\033[0m')

rows = []
dirty_count = 0
push_count = 0
local_only_count = 0
up_to_date_count = 0

for item in catalog:
    if item.get('name') in ['gitdoctor', 'repos-sync'] or item.get('url', '').endswith('/gitdoctor.git') or item.get('url', '').endswith('/repos-sync.git'):
        continue

    r_name = item['name']
    r_group = item.get('group', 'General')
    rel_path = item.get('path', os.path.join(r_group, r_name))
    r_path = os.path.join(repos_dir, rel_path)

    if not os.path.exists(r_path):
        rows.append((r_group, r_name, '-', '[NO CLONADO]', 'Ejecuta ./sync.sh'))
        continue

    if not os.path.isdir(os.path.join(r_path, '.git')):
        rows.append((r_group, r_name, '-', '[NO ES GIT]', 'Carpeta sin .git'))
        continue

    try:
        branch = subprocess.check_output(['git', '-C', r_path, 'branch', '--show-current'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        if not branch:
            branch = '(detached)'
    except Exception:
        branch = '(unknown)'

    subprocess.run(['git', '-C', r_path, 'fetch', 'origin', '-q', '--prune'], stderr=subprocess.DEVNULL)

    try:
        status_out = subprocess.check_output(['git', '-C', r_path, 'status', '--porcelain'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        status_lines = [l for l in status_out.splitlines() if l.strip()]
    except Exception:
        status_lines = []
    has_dirty = len(status_lines) > 0

    ahead = 0
    behind = 0
    is_local_only = False
    try:
        upstream = subprocess.check_output(['git', '-C', r_path, 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
        if upstream:
            ahead_str = subprocess.check_output(['git', '-C', r_path, 'rev-list', '--count', '@{u}..HEAD'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
            behind_str = subprocess.check_output(['git', '-C', r_path, 'rev-list', '--count', 'HEAD..@{u}'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
            ahead = int(ahead_str) if ahead_str.isdigit() else 0
            behind = int(behind_str) if behind_str.isdigit() else 0
        else:
            try:
                remote_check = subprocess.check_output(['git', '-C', r_path, 'rev-parse', '--verify', f'origin/{branch}'], stderr=subprocess.DEVNULL).decode('utf-8').strip()
            except Exception:
                remote_check = ''
            if not remote_check and branch != '(detached)':
                is_local_only = True
                local_only_count += 1
    except Exception:
        upstream = ''

    pull_status = ''
    if behind > 0 and (not has_dirty) and auto_pull:
        res = subprocess.run(['git', '-C', r_path, 'pull', '-q', '--ff-only'], stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            pull_status = ' (pull OK)'
            behind = 0
        else:
            pull_status = ' (pull fallo)'

    if has_dirty and ahead > 0:
        estado = '[CAMBIOS LOCALES + PUSH]'
        detalle = f'{len(status_lines)} modif. y {ahead} commit(s) pendientes'
        dirty_count += 1
        push_count += 1
    elif has_dirty:
        estado = '[CAMBIOS LOCALES]'
        detalle = f'{len(status_lines)} archivo(s) sin commit'
        dirty_count += 1
    elif is_local_only:
        estado = '[RAMA SOLO LOCAL]'
        detalle = f'Rama no existe en GitHub (git push -u origin {branch})'
        push_count += 1
    elif ahead > 0 and behind > 0:
        estado = '[DESVIADO / MERGE]'
        detalle = f'{ahead} adelante, {behind} atras'
        push_count += 1
    elif ahead > 0:
        estado = '[PENDIENTE PUSH]'
        detalle = f'{ahead} commit(s) por subir a GitHub'
        push_count += 1
    elif behind > 0:
        estado = '[ACTUALIZACION DISP]'
        detalle = f'{behind} commit(s) en GitHub por bajar'
    else:
        estado = '[AL DIA]'
        detalle = 'Actualizado exitosamente' if pull_status else 'Limpio y sincronizado'
        up_to_date_count += 1

    rows.append((r_group, r_name, branch, estado, detalle))

# Mostrar agrupado por Organizacion
grouped = OrderedDict()
for grp, name, b, e, d in rows:
    if grp not in grouped:
        grouped[grp] = []
    grouped[grp].append((name, b, e, d))

col_w = [26, 38, 25, 30]

for grp_name, items in grouped.items():
    icon = '👤' if grp_name == 'Personal' else '📁'
    label = 'Personal' if grp_name == 'Personal' else 'Organizacion'
    print(f'\n  \033[1;37m{icon} [{label}: {grp_name}] -- {len(items)} repositorios\033[0m')
    print(f'  \033[90m{\"-\" * 70}\033[0m')
    head_line = f'  {\"Repositorio\":<{col_w[0]}} {\"Rama\":<{col_w[1]}} {\"Estado\":<{col_w[2]}} {\"Detalle\":<{col_w[3]}}'
    print(f'  \033[1m{head_line}\033[0m')

    for r, b, e, d in items:
        if '[AL DIA]' in e:
            color = '\033[32m'
        elif '[CAMBIOS LOCALES' in e:
            color = '\033[33m'
        elif '[RAMA SOLO LOCAL]' in e:
            color = '\033[35m'
        elif '[PENDIENTE PUSH]' in e:
            color = '\033[36m'
        elif '[ACTUALIZACION DISP]' in e:
            color = '\033[34m'
        else:
            color = '\033[31m'

        b_disp = (b[:35] + '..') if len(b) > 38 else b
        line = f'  {r:<{col_w[0]}} {b_disp:<{col_w[1]}} {color}{e:<{col_w[2]}}\033[0m {d:<{col_w[3]}}'
        print(line)

print('\n--------------------------------------------------------')
print(f'\033[36mResumen: {up_to_date_count} al dia | {dirty_count} con cambios locales | {push_count} pendientes de push | {local_only_count} ramas solo locales\033[0m')

if dirty_count > 0 or push_count > 0 or local_only_count > 0:
    print('\033[33m[!] ATENCION: Tienes cambios locales, ramas o commits por subir antes de cambiar de maquina.\033[0m')
else:
    print('\033[32m[OK] Todo en orden. Puedes cambiar de maquina con total tranquilidad.\033[0m')
print('========================================================\n')
"
