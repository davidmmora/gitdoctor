#!/usr/bin/env python3
# ==============================================================================
# onboarding.py -- Asistente de Instalacion, Diagnostico y Reorganizacion
# ==============================================================================
# - Asistente interactivo de primera instalacion (Mac y Windows)
# - Deteccion dinamica de cuenta de GitHub y organizaciones reales del usuario
# - Seleccion de alcance de instalacion (Descargar todo vs Organizaciones selectivas)
# - Generacion de catalogo privado repos.local.json a partir de repos reales
# - Configuracion de identidad Git, Motor de IA y Servicio Vigilante
# - Diagnostico y clasificacion segura de proyectos locales existentes
# - Blindaje absoluto: GitDoctor NUNCA es eliminado ni alterado
# ==============================================================================

import os
import sys
import json
import shutil
import subprocess

# Configurar encoding UTF-8 seguro
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
if hasattr(sys.stdin, 'reconfigure'):
    try:
        sys.stdin.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Activar secuencias ANSI en Windows cmd.exe
if os.name == 'nt':
    os.system('')

C_RESET   = "\033[0m"
C_CYAN    = "\033[36m"
C_GREEN   = "\033[32m"
C_YELLOW  = "\033[33m"
C_RED     = "\033[31m"
C_MAGENTA = "\033[35m"
C_WHITE   = "\033[1;37m"
C_GRAY    = "\033[90m"
C_BOLD    = "\033[1m"

DEFAULT_FALLBACK_ORGS = [
    "Personal",
    "th-mex",
    "w-amarillo",
    "w-azul",
    "w-naranja",
    "interpec",
    "w-pluma",
    "w-ic",
    "bf-agency",
    "WeHubs-io"
]

def run_cmd(cmd, cwd=None, timeout=10):
    try:
        res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=timeout, check=False)
        return res.stdout.decode('utf-8', errors='replace').strip()
    except Exception:
        return ""

def is_gitdoctor_path(folder_path, script_dir):
    """Verifica de forma estricta y segura si una ruta es la propia instalacion de GitDoctor"""
    if not folder_path:
        return False
    try:
        if os.path.isdir(folder_path) and os.path.isdir(script_dir):
            if os.path.samefile(folder_path, script_dir):
                return True
    except Exception:
        pass

    try:
        p1 = os.path.normcase(os.path.realpath(folder_path))
        s1 = os.path.normcase(os.path.realpath(script_dir))
        if p1 == s1 or p1.startswith(s1 + os.sep):
            return True
        base = os.path.basename(p1).lower()
        if base in ["gitdoctor", "_gitdoctor", "repos-sync", "_sync"]:
            return True
    except Exception:
        pass
    return False

def get_repo_remote_url(folder_path):
    """Obtiene la URL remota de origin si es un repositorio Git"""
    git_dir = os.path.join(folder_path, ".git")
    if not os.path.isdir(git_dir):
        return ""
    return run_cmd(["git", "config", "--get", "remote.origin.url"], cwd=folder_path)

def extract_org_from_remote(url, known_orgs=None):
    """Extrae y clasifica la organizacion o usuario a partir de la URL remota de GitHub"""
    if not url:
        return None
    u = url.strip()
    if u.endswith('.git'):
        u = u[:-4]
    u = u.replace("git@github.com:", "").replace("https://github.com/", "").replace("ssh://git@github.com/", "")
    parts = [p for p in u.split('/') if p]
    if len(parts) >= 2:
        remote_org = parts[0].strip()
        org_pool = known_orgs if known_orgs else DEFAULT_FALLBACK_ORGS
        for org in org_pool:
            if remote_org.lower() == org.lower():
                return org
        if remote_org.lower() in ["davidmmora", "dmayomora", "personal"]:
            return "Personal"
        return remote_org
    return None

def ask_user_confirmation(prompt, default_yes=True):
    """Pregunta interactiva con valor por defecto seguro"""
    suffix = " [S/n]: " if default_yes else " [s/N]: "
    try:
        ans = input(f"{C_BOLD}{prompt}{C_RESET}{suffix}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("")
        return False
    if not ans:
        return default_yes
    return ans in ["s", "si", "y", "yes"]

# ==============================================================================
# DESCUBRIMIENTO DE GITHUB Y ORGANIZACIONES REALES DEL USUARIO
# ==============================================================================
def get_github_auth_info():
    """Obtiene datos de la sesion autenticada de GitHub CLI y sus organizaciones reales"""
    info = {
        "installed": False,
        "logged_in": False,
        "user": None,
        "name": None,
        "email": None,
        "orgs": []
    }

    if not shutil.which("gh"):
        return info

    info["installed"] = True
    try:
        res = subprocess.run(["gh", "api", "user"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if res.returncode == 0:
            data = json.loads(res.stdout.decode('utf-8'))
            info["logged_in"] = True
            info["user"] = data.get("login")
            info["name"] = data.get("name")
            info["email"] = data.get("email")
    except Exception:
        pass

    if info["logged_in"]:
        try:
            res_orgs = subprocess.run(["gh", "api", "user/orgs"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
            if res_orgs.returncode == 0:
                org_list = json.loads(res_orgs.stdout.decode('utf-8'))
                info["orgs"] = [o["login"] for o in org_list if "login" in o]
        except Exception:
            pass

    return info

def prompt_github_login():
    """Ofrece iniciar sesion interactiva con GitHub CLI si no hay sesion"""
    if not shutil.which("gh"):
        return False
    print(f"\n{C_YELLOW}[!] No se detecto sesion activa en GitHub CLI ('gh').{C_RESET}")
    print(f"{C_GRAY}Conectarte a GitHub permite detectar tus organizaciones y clonar tus repositorios privados de forma automatica y segura.{C_RESET}")
    if ask_user_confirmation("¿Deseas iniciar sesion en GitHub ahora mismo?", default_yes=True):
        try:
            subprocess.run(["gh", "auth", "login"], check=False)
            info = get_github_auth_info()
            return info.get("logged_in", False)
        except Exception:
            return False
    return False

def fetch_remote_repositories(gh_user, orgs_to_fetch, script_dir):
    """Consulta en GitHub los repositorios de las organizaciones seleccionadas y del usuario"""
    entries = []
    seen_names = set()

    # Repositorios personales
    if "Personal" in orgs_to_fetch and gh_user:
        print(f"  * Consultando repositorios personales de @{gh_user}...")
        try:
            cmd = ["gh", "repo", "list", "--limit", "150", "--json", "name,nameWithOwner,url,defaultBranchRef"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20)
            if res.returncode == 0:
                repos = json.loads(res.stdout.decode('utf-8'))
                for r in repos:
                    name = r.get("name", "")
                    if name.lower() in ["gitdoctor", "repos-sync"] or r.get("url", "").endswith("/gitdoctor.git"):
                        continue
                    branch = r.get("defaultBranchRef", {}).get("name") if r.get("defaultBranchRef") else "main"
                    entries.append({
                        "name": name,
                        "group": "Personal",
                        "path": f"Personal/{name}",
                        "url": r.get("url", ""),
                        "defaultBranch": branch or "main"
                    })
                    seen_names.add(name.lower())
        except Exception as e:
            print(f"    {C_RED}[!] Error consultando cuenta personal: {e}{C_RESET}")

    # Repositorios de cada organizacion seleccionada
    for org in orgs_to_fetch:
        if org == "Personal":
            continue
        print(f"  * Consultando organizacion '{org}'...")
        try:
            cmd = ["gh", "repo", "list", org, "--limit", "150", "--json", "name,nameWithOwner,url,defaultBranchRef"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=20)
            if res.returncode == 0:
                repos = json.loads(res.stdout.decode('utf-8'))
                for r in repos:
                    name = r.get("name", "")
                    if name.lower() in ["gitdoctor", "repos-sync"] or r.get("url", "").endswith("/gitdoctor.git"):
                        continue
                    branch = r.get("defaultBranchRef", {}).get("name") if r.get("defaultBranchRef") else "main"
                    entries.append({
                        "name": name,
                        "group": org,
                        "path": f"{org}/{name}",
                        "url": r.get("url", ""),
                        "defaultBranch": branch or "main"
                    })
                    seen_names.add(name.lower())
        except Exception as e:
            print(f"    {C_RED}[!] Error consultando {org}: {e}{C_RESET}")

    return entries

# ==============================================================================
# DIAGNOSTICO Y REORGANIZACION DE CARPETAS EXISTENTES
# ==============================================================================
def scan_existing_directory(repos_dir, known_orgs=None):
    """Analiza la estructura actual de la carpeta raiz de repositorios"""
    if not os.path.isdir(repos_dir):
        return {"exists": False, "items": []}

    entries = []
    active_org_pool = known_orgs if known_orgs else DEFAULT_FALLBACK_ORGS
    official_set = {o.lower(): o for o in active_org_pool}

    try:
        raw_items = sorted(os.listdir(repos_dir))
    except Exception:
        raw_items = []

    script_dir = os.path.dirname(os.path.abspath(__file__))

    for item in raw_items:
        item_p = os.path.join(repos_dir, item)
        if is_gitdoctor_path(item_p, script_dir) or item.startswith("."):
            continue

        if not os.path.isdir(item_p):
            continue

        # Caso A: Es una carpeta con nombre de organizacion conocida
        if item.lower() in official_set:
            official_name = official_set[item.lower()]
            try:
                sub_items = sorted(os.listdir(item_p))
            except Exception:
                sub_items = []
            sub_count = 0
            for sub in sub_items:
                if sub.startswith("."):
                    continue
                sub_p = os.path.join(item_p, sub)
                if is_gitdoctor_path(sub_p, script_dir):
                    continue
                if os.path.isdir(sub_p):
                    sub_count += 1
            entries.append({
                "name": item,
                "type": "official_org",
                "org": official_name,
                "path": item_p,
                "sub_count": sub_count
            })
            continue

        # Caso B: Carpeta suelta en la raiz
        has_git = os.path.isdir(os.path.join(item_p, ".git"))
        remote_url = get_repo_remote_url(item_p) if has_git else ""
        deduced_org = extract_org_from_remote(remote_url, known_orgs=active_org_pool) if remote_url else None

        entries.append({
            "name": item,
            "type": "loose_repo" if has_git else "loose_folder",
            "has_git": has_git,
            "remote": remote_url,
            "deduced_org": deduced_org,
            "path": item_p
        })

    return {"exists": True, "items": entries}

def run_onboarding_assistant(repos_dir, known_orgs=None, interactive=True):
    """Asistente que diagnostica y ofrece reorganizar proyectos sueltos"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    org_pool = known_orgs if known_orgs else DEFAULT_FALLBACK_ORGS

    scan = scan_existing_directory(repos_dir, known_orgs=org_pool)
    items = scan.get("items", [])

    if not items:
        return {"status": "clean"}

    official_dirs = [i for i in items if i["type"] == "official_org"]
    loose_repos   = [i for i in items if i["type"] == "loose_repo"]
    loose_folders = [i for i in items if i["type"] == "loose_folder"]

    if not loose_repos and not loose_folders:
        print(f"{C_GREEN}[OK] Estructura limpia.{C_RESET} Todos tus proyectos locales estan organizados por carpeta.")
        return {"status": "already_organized"}

    print(f"\n{C_CYAN}------------------------------------------------------------------{C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  Diagnostico de Carpetas Locales Existentes en {repos_dir}{C_RESET}")
    print(f"{C_CYAN}------------------------------------------------------------------{C_RESET}")
    if official_dirs:
        total_sub = sum(o["sub_count"] for o in official_dirs)
        print(f"  * {C_GREEN}{len(official_dirs)} carpetas de organizacion activas{C_RESET} ({total_sub} repositorios organizados)")
    if loose_repos:
        print(f"  * {C_YELLOW}{len(loose_repos)} repositorio(s) Git sueltos en la raiz{C_RESET} (deben pertenecer a una organizacion)")
    if loose_folders:
        print(f"  * {C_MAGENTA}{len(loose_folders)} carpeta(s) sin control de versiones en la raiz{C_RESET}")

    print(f"\n{C_YELLOW}[!] Regla de arquitectura: Todos tus proyectos deben residir en <organizacion>/<proyecto>.{C_RESET}")
    print(f"{C_GRAY}GitDoctor es el unico elemento que reside en la raiz.{C_RESET}\n")

    if not interactive:
        return {"status": "needs_reorganization", "loose_repos": len(loose_repos)}

    print(f"{C_BOLD}¿Que deseas hacer con las carpetas sueltas detectadas?{C_RESET}")
    print(f"  {C_WHITE}[1]{C_RESET} {C_GREEN}Clasificar inteligentemente{C_RESET} (Recomendado: deduce de Git y mueve a su organizacion)")
    print(f"  {C_WHITE}[2]{C_RESET} {C_CYAN}Mover todas a 'Personal'{C_RESET}")
    print(f"  {C_WHITE}[3]{C_RESET} {C_GRAY}Mantener tal cual por ahora{C_RESET} (Omitir reorganizacion)")

    try:
        choice = input(f"\n{C_BOLD}Selecciona una opcion [1/2/3] (Enter para 1): {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "3"

    if choice in ["3", "cancelar", "n"]:
        print(f"{C_GRAY}[*] Reorganizacion omitida.{C_RESET}\n")
        return {"status": "skipped"}

    plan = []
    candidates = loose_repos + loose_folders

    if choice == "2":
        for c in candidates:
            plan.append((c, "Personal"))
    else:
        for c in candidates:
            name = c["name"]
            suggested_org = c.get("deduced_org")
            if suggested_org and suggested_org in org_pool:
                plan.append((c, suggested_org))
            else:
                print(f"\n  Proyecto '{name}' (Remoto: {c.get('remote') or 'Sin Git'}):")
                for idx, o in enumerate(org_pool, 1):
                    print(f"    [{idx:2d}] {o}")
                print(f"    [ 0] Omitir")
                try:
                    ans_o = input(f"  Organizacion destino para '{name}' (Enter para Personal): ").strip()
                except (EOFError, KeyboardInterrupt):
                    ans_o = ""
                if ans_o == "0":
                    continue
                elif ans_o.isdigit() and 1 <= int(ans_o) <= len(org_pool):
                    plan.append((c, org_pool[int(ans_o) - 1]))
                else:
                    plan.append((c, "Personal"))

    if not plan:
        return {"status": "no_moves"}

    print(f"\n{C_BOLD}Plan de reorganizacion:{C_RESET}")
    for item, target_org in plan:
        print(f"  * {item['name']} -> {target_org}/{item['name']}")

    if not ask_user_confirmation("¿Deseas aplicar estos movimientos ahora?", default_yes=True):
        print(f"{C_GRAY}Operacion cancelada por el usuario.{C_RESET}\n")
        return {"status": "cancelled"}

    moved_count = 0
    for item, target_org in plan:
        src = item["path"]
        target_dir = os.path.join(repos_dir, target_org)
        dst = os.path.join(target_dir, item["name"])
        os.makedirs(target_dir, exist_ok=True)
        try:
            if not os.path.exists(dst):
                shutil.move(src, dst)
                moved_count += 1
                print(f"  {C_GREEN}[OK]{C_RESET} {item['name']} -> {target_org}/{item['name']}")
        except Exception as e:
            print(f"  {C_RED}[ERROR]{C_RESET} No se pudo mover {item['name']}: {e}")

    print(f"{C_GREEN}[OK] {moved_count} proyecto(s) organizados exitosamente.{C_RESET}\n")
    return {"status": "completed", "moved": moved_count}

# ==============================================================================
# ASISTENTE MAESTRO DE INSTALACION INTERACTIVA (SETUP WIZARD)
# ==============================================================================
def run_full_setup(script_dir):
    """
    Asistente interactivo maestro para la primera instalacion en Mac o Windows.
    Pregunta todo lo configurable: carpeta raiz, usuario y organizaciones de GitHub,
    alcance de descarga, Git identity, motor de IA, Vigilante y accesos.
    """
    print(f"\n{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  GitDoctor -- Asistente de Instalacion y Configuracion Inicial {C_RESET}")
    print(f"{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_GRAY}Bienvenido a GitDoctor. Este asistente configurara de forma personalizada{C_RESET}")
    print(f"{C_GRAY}tu entorno de trabajo, conectara con GitHub y definira que descargar.{C_RESET}\n")

    # --------------------------------------------------------------------------
    # PASO 1: CARPETA Y NOMBRE CANONICO DE GITDOCTOR
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 1/6] Carpeta y Ubicacion de GitDoctor{C_RESET}")
    current_folder_name = os.path.basename(script_dir)

    # Regla de nombre canonico: gitdoctor
    if current_folder_name.lower() != "gitdoctor":
        print(f"  {C_YELLOW}[AVISO] Tu carpeta actual se llama '{current_folder_name}'.{C_RESET}")
        print(f"  {C_GRAY}El nombre canonico y oficial en todo el ecosistema es 'gitdoctor'.{C_RESET}")
        print(f"  {C_GRAY}Se recomienda usar 'gitdoctor' para compatibilidad total con comandos globales.{C_RESET}")

    parent_dir = os.path.abspath(os.path.join(script_dir, ".."))
    parent_name = os.path.basename(parent_dir)

    # Detectar si GitDoctor reside dentro de una carpeta de organizacion (ej: Personal)
    inside_org = False
    if parent_name in DEFAULT_FALLBACK_ORGS or parent_name.lower() in ["personal", "repos-sync"]:
        inside_org = True
        suggested_repos_dir = os.path.abspath(os.path.join(parent_dir, ".."))
        print(f"  {C_YELLOW}[INFO] GitDoctor reside actualmente en: {script_dir}{C_RESET}")
        print(f"  {C_GRAY}Detectamos que esta dentro de '{parent_name}'. La suite opera sin problemas desde{C_RESET}")
        print(f"  {C_GRAY}aqui, o puedes usar la raiz superior como directorio principal de repositorios.{C_RESET}")
    else:
        suggested_repos_dir = parent_dir

    # Sugerencia segura si parent es la raiz del disco o home
    home_dir = os.path.expanduser("~")
    if suggested_repos_dir in [home_dir, "/", "C:\\", "D:\\"]:
        if os.name == 'nt' and os.path.exists("D:\\"):
            suggested_repos_dir = "D:\\Repos"
        else:
            suggested_repos_dir = os.path.join(home_dir, "Repos")

    # Si ya habia una configuracion previa en config.local.json, respetarla
    cfg_file = os.path.join(script_dir, "config.local.json")
    if os.path.isfile(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                cdata = json.load(f)
                if cdata.get("repos_dir") and os.path.isdir(cdata["repos_dir"]):
                    suggested_repos_dir = cdata["repos_dir"]
        except Exception:
            pass

    print(f"  * Directorio de GitDoctor:       {C_WHITE}{script_dir}{C_RESET}")
    print(f"  * Carpeta raiz de proyectos:     {C_GREEN}{suggested_repos_dir}{C_RESET}")

    try:
        user_repos_input = input(f"  {C_BOLD}Confirma la carpeta raiz de proyectos (Enter para usar la sugerida): {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        user_repos_input = ""

    if user_repos_input:
        repos_dir = os.path.abspath(os.path.expanduser(user_repos_input))
    else:
        repos_dir = suggested_repos_dir

    os.makedirs(repos_dir, exist_ok=True)
    print(f"  {C_GREEN}[OK] Carpeta de proyectos establecida en: {repos_dir}{C_RESET}\n")

    # --------------------------------------------------------------------------
    # PASO 2: CONEXION CON GITHUB Y DETECCION DE CUENTA Y ORGANIZACIONES
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 2/6] Conexion con GitHub y Deteccion de Organizaciones{C_RESET}")
    gh_info = get_github_auth_info()

    if not gh_info["installed"]:
        print(f"  {C_YELLOW}[INFO] GitHub CLI ('gh') no esta instalado en este equipo.{C_RESET}")
        print(f"  {C_GRAY}Recomendado: 'brew install gh' (Mac) o 'winget install GitHub.cli' (Windows).{C_RESET}")
    elif not gh_info["logged_in"]:
        prompt_github_login()
        gh_info = get_github_auth_info()

    gh_user = gh_info.get("user")
    user_orgs = gh_info.get("orgs", [])

    if gh_info.get("logged_in") and gh_user:
        u_name = f" ({gh_info.get('name')})" if gh_info.get("name") else ""
        print(f"  {C_GREEN}[OK] Conectado a GitHub como @{gh_user}{u_name}{C_RESET}")
        if user_orgs:
            print(f"  {C_CYAN}Organizaciones detectadas ({len(user_orgs)}):{C_RESET} {', '.join(user_orgs)}")
        else:
            print(f"  {C_GRAY}Organizaciones detectadas: Ninguna (solo tu cuenta personal).{C_RESET}")
    else:
        print(f"  {C_GRAY}Modo sin sesion remota de GitHub CLI.{C_RESET}")
        try:
            manual_user = input(f"  Ingresa tu usuario de GitHub si deseas consultar repos publicos (Enter para omitir): ").strip()
        except (EOFError, KeyboardInterrupt):
            manual_user = ""
        if manual_user:
            gh_user = manual_user

    # Lista total de organizaciones disponibles para este usuario
    available_orgs = ["Personal"]
    for o in user_orgs:
        if o not in available_orgs:
            available_orgs.append(o)

    # Si es David M Mora o no se encontraron orgs en GitHub, ofrecer las 10 oficiales como fallback
    if len(available_orgs) == 1 and (not gh_user or gh_user.lower() in ["davidmmora", "dmayomora"]):
        for o in DEFAULT_FALLBACK_ORGS:
            if o not in available_orgs:
                available_orgs.append(o)

    print("")

    # --------------------------------------------------------------------------
    # PASO 3: ALCANCE DE INSTALACION Y DESCARGA (TODO vs SELECTIVO)
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 3/6] Alcance de Descarga y Organizaciones{C_RESET}")
    print(f"  Define como deseas configurar la descarga de tus repositorios:")
    print(f"  {C_WHITE}[1]{C_RESET} {C_GREEN}Descargar TODO{C_RESET} (Todos los repos de tu cuenta personal y organizaciones)")
    print(f"  {C_WHITE}[2]{C_RESET} {C_CYAN}Seleccionar Organizaciones Especificas{C_RESET} (Elegir cuales activar en este equipo)")
    print(f"  {C_WHITE}[3]{C_RESET} {C_YELLOW}Solo Catalogar{C_RESET} (Crear catalogo privado, pero descargar bajo demanda con /clone)")
    print(f"  {C_WHITE}[4]{C_RESET} {C_GRAY}Solo Proyectos Locales Existentes{C_RESET} (No consultar GitHub ahora; usar lo que ya hay en disco)")

    try:
        scope_choice = input(f"\n  {C_BOLD}Selecciona una opcion [1/2/3/4] (Enter para 1): {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        scope_choice = "1"

    if not scope_choice:
        scope_choice = "1"

    enabled_orgs = list(available_orgs)
    disabled_orgs = []
    sync_mode = "mirror"
    download_on_setup = True

    if scope_choice == "2":
        sync_mode = "selective"
        print(f"\n  {C_BOLD}Organizaciones disponibles para sincronizar:{C_RESET}")
        for idx, o in enumerate(available_orgs, 1):
            label = "Cuenta Personal" if o == "Personal" else f"Organizacion {o}"
            print(f"    [{idx:2d}] {o:<20} ({label})")

        print(f"\n  {C_GRAY}Ingresa los numeros separados por coma (ej: 1, 2) o escribe 'todas':{C_RESET}")
        try:
            sel_input = input(f"  {C_BOLD}Organizaciones a activar en este equipo: {C_RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            sel_input = "todas"

        if sel_input.lower() not in ["todas", "all", "*", ""]:
            selected_indices = []
            for part in sel_input.replace(";", ",").split(","):
                part = part.strip()
                if part.isdigit():
                    val = int(part)
                    if 1 <= val <= len(available_orgs):
                        selected_indices.append(val - 1)
            if selected_indices:
                enabled_orgs = [available_orgs[i] for i in selected_indices]
                disabled_orgs = [o for o in available_orgs if o not in enabled_orgs]

        print(f"  {C_GREEN}[OK] Organizaciones activadas:{C_RESET} {', '.join(enabled_orgs)}")
        if disabled_orgs:
            print(f"  {C_GRAY}Organizaciones omitidas en este equipo:{C_RESET} {', '.join(disabled_orgs)}")

        download_on_setup = ask_user_confirmation("¿Deseas descargar los repositorios de estas organizaciones ahora mismo?", default_yes=True)

    elif scope_choice == "3":
        sync_mode = "catalog_only"
        download_on_setup = False
        print(f"  {C_GREEN}[OK] Modo Catalogo Privado.{C_RESET} Se construira el inventario sin clonar todo de inmediato.")

    elif scope_choice == "4":
        sync_mode = "local_only"
        download_on_setup = False
        print(f"  {C_GRAY}[*] Modo local: No se consultara GitHub en este paso.{C_RESET}")

    # Generar catalogo repos.local.json a partir de GitHub si se selecciono consultar
    cat_local = os.path.join(script_dir, "repos.local.json")
    if scope_choice in ["1", "2", "3"] and gh_info.get("logged_in") and gh_user:
        print(f"\n  {C_CYAN}[*] Consultando repositorios reales en GitHub...{C_RESET}")
        remote_repos = fetch_remote_repositories(gh_user, enabled_orgs, script_dir)
        if remote_repos:
            try:
                with open(cat_local, "w", encoding="utf-8") as f:
                    json.dump(remote_repos, f, indent=4, ensure_ascii=False)
                print(f"  {C_GREEN}[OK] Catalogo privado repos.local.json generado con {len(remote_repos)} repositorios.{C_RESET}")
            except Exception as e:
                print(f"  {C_RED}[ERROR] No se pudo guardar repos.local.json: {e}{C_RESET}")
        else:
            print(f"  {C_YELLOW}[INFO] No se encontraron repositorios remotos en las organizaciones seleccionadas.{C_RESET}")

    print("")

    # --------------------------------------------------------------------------
    # PASO 4: IDENTIDAD GIT PARA ESTE EQUIPO
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 4/6] Identidad de Git (Commits y Firma){C_RESET}")
    cur_git_name = run_cmd(["git", "config", "--global", "user.name"])
    cur_git_email = run_cmd(["git", "config", "--global", "user.email"])

    print(f"  * Nombre actual: {C_WHITE}{cur_git_name or 'No configurado'}{C_RESET}")
    print(f"  * Email actual:  {C_WHITE}{cur_git_email or 'No configurado'}{C_RESET}")

    if cur_git_name and cur_git_email:
        keep_git = ask_user_confirmation("¿Deseas mantener esta identidad de Git?", default_yes=True)
    else:
        keep_git = False

    if not keep_git:
        try:
            def_name = gh_info.get("name") or gh_user or cur_git_name or ""
            def_email = gh_info.get("email") or cur_git_email or ""
            new_name = input(f"  Nombre completo para tus commits [{def_name}]: ").strip() or def_name
            new_email = input(f"  Correo electronico para tus commits [{def_email}]: ").strip() or def_email

            if new_name:
                subprocess.run(["git", "config", "--global", "user.name", new_name], check=False)
            if new_email:
                subprocess.run(["git", "config", "--global", "user.email", new_email], check=False)
            print(f"  {C_GREEN}[OK] Identidad de Git configurada: {new_name} <{new_email}>{C_RESET}")
        except (EOFError, KeyboardInterrupt):
            pass

    print("")

    # --------------------------------------------------------------------------
    # PASO 5: MOTOR DE INTELIGENCIA ARTIFICIAL (GITDOCTOR AI)
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 5/6] Motor de Inteligencia Artificial (GitDoctor AI){C_RESET}")
    print(f"  GitDoctor incluye un asistente clinico inteligente para diagnostico y salud Git:")
    print(f"  {C_WHITE}[1]{C_RESET} {C_GREEN}Ollama Local Offline{C_RESET} (100% privado, sin API key, gratuito)")
    print(f"  {C_WHITE}[2]{C_RESET} {C_CYAN}Google Gemini API{C_RESET} (Nube, alta velocidad)")
    print(f"  {C_WHITE}[3]{C_RESET} {C_GRAY}Omitir por ahora{C_RESET} (Usar solo comandos tradicionales sin IA)")

    try:
        ai_choice = input(f"\n  {C_BOLD}Selecciona tu motor de IA [1/2/3] (Enter para 1): {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        ai_choice = "1"

    ai_provider = "ollama"
    if ai_choice == "2":
        ai_provider = "gemini"
        env_file = os.path.join(script_dir, ".env")
        has_key = False
        if os.path.isfile(env_file):
            try:
                with open(env_file, "r", encoding="utf-8") as ef:
                    if "GEMINI_API_KEY=" in ef.read():
                        has_key = True
            except Exception:
                pass

        if not has_key:
            try:
                g_key = input(f"  Ingresa tu Google Gemini API Key (Enter para configurar luego): ").strip()
                if g_key:
                    with open(env_file, "a", encoding="utf-8") as ef:
                        ef.write(f"\nGEMINI_API_KEY={g_key}\n")
                    print(f"  {C_GREEN}[OK] API Key guardada de forma segura en .env (ignorado por Git).{C_RESET}")
            except (EOFError, KeyboardInterrupt):
                pass
    elif ai_choice == "3":
        ai_provider = "none"
        print(f"  {C_GRAY}[*] Modo clinico clasico activado.{C_RESET}")
    else:
        ai_provider = "ollama"
        if shutil.which("ollama"):
            print(f"  {C_GREEN}[OK] Ollama detectado en tu sistema.{C_RESET}")
        else:
            print(f"  {C_YELLOW}[INFO] Ollama no detectado en PATH. Puedes instalarlo desde https://ollama.ai{C_RESET}")

    print("")

    # --------------------------------------------------------------------------
    # PASO 6: MODO VIGILANTE EN SEGUNDO PLANO (WATCHDOG)
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 6/6] Servicio Vigilante (Monitoreo en Segundo Plano){C_RESET}")
    print(f"  El Vigilante monitorea periodicamente tus ramas, commits pendientes y cambios")
    print(f"  locales para avisarte antes de apagar o cambiar de maquina.")
    watchdog_enabled = ask_user_confirmation("¿Deseas activar el modo Vigilante en este equipo?", default_yes=False)

    # --------------------------------------------------------------------------
    # GUARDAR CONFIGURACION EN config.local.json
    # --------------------------------------------------------------------------
    cfg_data = {
        "repos_dir": repos_dir,
        "gitdoctor_dir": script_dir,
        "sync_mode": sync_mode,
        "enabled_orgs": enabled_orgs,
        "disabled_orgs": disabled_orgs,
        "ai_provider": ai_provider,
        "watchdog_enabled": watchdog_enabled,
        "watchdog_interval_seconds": 300,
        "notifications_enabled": True,
        "download_on_setup": download_on_setup,
        "installed": True
    }

    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg_data, f, indent=4, ensure_ascii=False)
        print(f"\n{C_GREEN}[OK] Configuracion local guardada exitosamente en config.local.json.{C_RESET}")
    except Exception as e:
        print(f"\n{C_RED}[ERROR] No se pudo guardar config.local.json: {e}{C_RESET}")

    # --------------------------------------------------------------------------
    # REORGANIZACION DE PROYECTOS LOCALES PREEXISTENTES (SI EXISTEN)
    # --------------------------------------------------------------------------
    run_onboarding_assistant(repos_dir, known_orgs=enabled_orgs, interactive=True)

    print(f"\n{C_GREEN}=================================================================={C_RESET}")
    print(f"{C_GREEN}{C_BOLD}  ¡Configuracion inicial de GitDoctor completada con exito!      {C_RESET}")
    print(f"{C_GREEN}=================================================================={C_RESET}\n")

    return cfg_data

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Modo instalador interactivo completo
    if any(arg in sys.argv for arg in ["--interactive-setup", "--setup", "-i"]):
        run_full_setup(script_dir)
        return

    # Modo diagnostico simple de carpetas
    repos_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] and not sys.argv[1].startswith("-") else None
    if not repos_dir:
        cfg_file = os.path.join(script_dir, "config.local.json")
        if os.path.isfile(cfg_file):
            try:
                repos_dir = json.load(open(cfg_file)).get("repos_dir")
            except Exception:
                pass
        if not repos_dir:
            repos_dir = os.path.abspath(os.path.join(script_dir, ".."))

    run_onboarding_assistant(repos_dir, interactive=True)

if __name__ == "__main__":
    main()

