#!/usr/bin/env python3
# ==============================================================================
# onboarding.py -- Asistente de Inicializacion, Diagnostico y Reorganizacion
# ==============================================================================
# - Escanea el directorio raiz de repositorios antes de la instalacion
# - Identifica repositorios existentes, proyectos sueltos y carpetas huerfanas
# - Clasifica proyectos por remoto de GitHub hacia las 10 organizaciones oficiales
# - Siempre consulta al usuario y solicita confirmacion antes de cualquier accion
# ==============================================================================

import os
import sys
import json
import shutil
import subprocess
import urllib.request
import urllib.error

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

OFFICIAL_ORGS = [
    "th-mex",
    "w-amarillo",
    "w-azul",
    "w-naranja",
    "interpec",
    "w-pluma",
    "w-ic",
    "bf-agency",
    "WeHubs-io",
    "Personal"
]

def run_cmd(cmd, cwd=None):
    try:
        res = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=False)
        return res.stdout.decode('utf-8', errors='replace').strip()
    except Exception:
        return ""

def get_repo_remote_url(folder_path):
    """Obtiene la URL remota de origin si es un repositorio Git"""
    git_dir = os.path.join(folder_path, ".git")
    if not os.path.isdir(git_dir):
        return ""
    return run_cmd(["git", "config", "--get", "remote.origin.url"], cwd=folder_path)

def extract_org_from_remote(url):
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
        # Verificar coincidencia exacta con organizaciones oficiales
        for org in OFFICIAL_ORGS:
            if remote_org.lower() == org.lower():
                return org
        # Si el usuario es davidmmora u otro usuario personal
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

def scan_existing_directory(repos_dir):
    """Analiza la estructura actual de la carpeta raiz de repositorios"""
    if not os.path.isdir(repos_dir):
        return {"exists": False, "items": []}

    entries = []
    official_set = {o.lower(): o for o in OFFICIAL_ORGS}

    try:
        raw_items = sorted(os.listdir(repos_dir))
    except Exception:
        raw_items = []

    script_dir = os.path.dirname(os.path.abspath(__file__))

    for item in raw_items:
        item_p = os.path.join(repos_dir, item)
        if os.path.abspath(item_p) == script_dir or item in ["_gitdoctor", "_sync", "gitdoctor", "repos-sync"] or item.startswith("."):
            continue

        if not os.path.isdir(item_p):
            continue

        # Caso A: Es una carpeta con nombre de organizacion oficial
        if item.lower() in official_set:
            official_name = official_set[item.lower()]
            # Revisar subcarpetas dentro de esta organizacion
            try:
                sub_items = sorted(os.listdir(item_p))
            except Exception:
                sub_items = []
            sub_count = 0
            for sub in sub_items:
                if sub.startswith("."):
                    continue
                sub_p = os.path.join(item_p, sub)
                if os.path.abspath(sub_p) == script_dir or sub in ["_gitdoctor", "_sync", "gitdoctor", "repos-sync"]:
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
        deduced_org = extract_org_from_remote(remote_url) if remote_url else None

        entries.append({
            "name": item,
            "type": "loose_repo" if has_git else "loose_folder",
            "has_git": has_git,
            "remote": remote_url,
            "deduced_org": deduced_org,
            "path": item_p
        })

    return {"exists": True, "items": entries}

def run_onboarding_assistant(repos_dir, interactive=True):
    """Asistente de onboarding que diagnostica y ofrece reorganizar el entorno de trabajo"""
    print(f"\n{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  GitDoctor -- Asistente Clinico de Onboarding y Reorganizacion {C_RESET}")
    print(f"{C_GRAY}  Directorio analizado: {repos_dir}{C_RESET}")
    print(f"{C_CYAN}=================================================================={C_RESET}\n")

    scan = scan_existing_directory(repos_dir)
    items = scan.get("items", [])

    if not items:
        print(f"{C_GREEN}[OK] Directorio limpio y listo.{C_RESET} No hay proyectos existentes en la raiz.")
        print(f"{C_GRAY}GitDoctor creara la arquitectura de organizaciones oficiales al sincronizar.{C_RESET}\n")
        return {"status": "clean"}

    official_dirs = [i for i in items if i["type"] == "official_org"]
    loose_repos   = [i for i in items if i["type"] == "loose_repo"]
    loose_folders = [i for i in items if i["type"] == "loose_folder"]

    print(f"{C_BOLD}Diagnostico del contenido actual:{C_RESET}")
    if official_dirs:
        total_sub = sum(o["sub_count"] for o in official_dirs)
        print(f"  * {C_GREEN}{len(official_dirs)} carpetas de organizacion oficial activas{C_RESET} ({total_sub} repositorios organizados)")
    if loose_repos:
        print(f"  * {C_YELLOW}{len(loose_repos)} repositorio(s) Git sueltos en la raiz{C_RESET} (deben pertenecer a una organizacion)")
    if loose_folders:
        print(f"  * {C_MAGENTA}{len(loose_folders)} carpeta(s) sin control de versiones Git en la raiz{C_RESET}")

    # Si todo ya esta organizado dentro de organizaciones oficiales
    if not loose_repos and not loose_folders:
        print(f"\n{C_GREEN}[OK] ¡Tu estructura ya respeta la arquitectura oficial de GitDoctor!{C_RESET}")
        print(f"{C_GRAY}Todos los repositorios estan agrupados por organizacion: <organizacion>/<repo>.{C_RESET}\n")
        return {"status": "already_organized"}

    print(f"\n{C_YELLOW}[!] Regla estricta: NUNCA tener proyectos de desarrollo sueltos en la raiz.{C_RESET}")
    print(f"{C_GRAY}GitDoctor es el UNICO repositorio que reside en la raiz; todos tus proyectos deben vivir dentro de una organizacion oficial.{C_RESET}\n")

    if not interactive:
        return {"status": "needs_reorganization", "loose_repos": len(loose_repos), "loose_folders": len(loose_folders)}

    print(f"{C_BOLD}¿Que deseas hacer con los proyectos detectados?{C_RESET}")
    print(f"  {C_WHITE}[1]{C_RESET} {C_GREEN}Reorganizar inteligentemente{C_RESET} (Recomendado: clasifica y mueve a su organizacion)")
    print(f"  {C_WHITE}[2]{C_RESET} {C_CYAN}Estructura limpia{C_RESET} (Mover todos los sueltos a 'Personal' y crear carpetas)")
    print(f"  {C_WHITE}[3]{C_RESET} {C_GRAY}Mantener tal cual por ahora{C_RESET} (Omitir reorganizacion y continuar instalacion)")

    try:
        choice = input(f"\n{C_BOLD}Selecciona una opcion [1/2/3] (Enter para 1): {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        choice = "3"

    if choice in ["3", "cancelar", "n"]:
        print(f"\n{C_GRAY}[*] Reorganizacion omitida. Conservando ubicaciones actuales.{C_RESET}\n")
        return {"status": "skipped"}

    # PLAN DE REORGANIZACION
    plan = []
    candidates = loose_repos + loose_folders

    if choice == "2":
        # Mover todo a Personal
        for c in candidates:
            plan.append((c, "Personal"))
    else:
        # Clasificacion inteligente
        print(f"\n{C_CYAN}Analizando destinos ideales para cada proyecto...{C_RESET}")
        for c in candidates:
            name = c["name"]
            suggested_org = c.get("deduced_org")

            if suggested_org and suggested_org in OFFICIAL_ORGS:
                print(f"  * {C_BOLD}{name}{C_RESET}: Detectado remoto -> {C_GREEN}{suggested_org}{C_RESET}")
                plan.append((c, suggested_org))
            else:
                # Preguntar al usuario a que organizacion mover
                print(f"\n  {C_YELLOW}[?] Proyecto '{name}' sin organizacion remota clara.{C_RESET}")
                print(f"  {C_GRAY}Remoto: {c.get('remote') or 'Sin Git'}{C_RESET}")
                print(f"  Organizaciones disponibles:")
                for idx, org in enumerate(OFFICIAL_ORGS, 1):
                    print(f"    [{idx:2d}] {org}")
                print(f"    [ 0] Omitir este proyecto")
                try:
                    ans_org = input(f"  {C_BOLD}Elige la organizacion destino para '{name}' [1-{len(OFFICIAL_ORGS)}] (Enter para Personal): {C_RESET}").strip()
                except (EOFError, KeyboardInterrupt):
                    ans_org = "10"

                if ans_org == "0":
                    print(f"    {C_GRAY}Omitiendo '{name}'.{C_RESET}")
                    continue
                elif ans_org.isdigit() and 1 <= int(ans_org) <= len(OFFICIAL_ORGS):
                    chosen_org = OFFICIAL_ORGS[int(ans_org) - 1]
                    plan.append((c, chosen_org))
                else:
                    plan.append((c, "Personal"))

    if not plan:
        print(f"\n{C_GRAY}[*] No se selecciono ningun proyecto para mover.{C_RESET}\n")
        return {"status": "no_moves"}

    # Resumen y confirmacion
    print(f"\n{C_CYAN}------------------------------------------------------------------{C_RESET}")
    print(f"{C_BOLD}Plan de Reorganizacion a aplicar:{C_RESET}")
    for item, target_org in plan:
        print(f"  * {item['name']} -> {C_BOLD}{target_org}/{item['name']}{C_RESET}")
    print(f"{C_CYAN}------------------------------------------------------------------{C_RESET}")

    if not ask_user_confirmation("¿Deseas aplicar estos movimientos de carpetas ahora mismo?", default_yes=True):
        print(f"\n{C_GRAY}[*] Operacion cancelada por el usuario. No se movio ningun archivo.{C_RESET}\n")
        return {"status": "cancelled"}

    # Aplicar movimientos
    moved_count = 0
    errors = []

    for item, target_org in plan:
        src = item["path"]
        target_dir = os.path.join(repos_dir, target_org)
        dst = os.path.join(target_dir, item["name"])

        os.makedirs(target_dir, exist_ok=True)
        try:
            if os.path.exists(dst):
                print(f"  {C_RED}[!] Ya existe una carpeta en {dst}. Omitiendo.{C_RESET}")
                continue
            shutil.move(src, dst)
            moved_count += 1
            print(f"  {C_GREEN}[OK] Movido exitosamente:{C_RESET} {item['name']} -> {target_org}/{item['name']}")
        except Exception as e:
            errors.append(f"{item['name']}: {e}")
            print(f"  {C_RED}[ERROR] No se pudo mover {item['name']}: {e}{C_RESET}")

    print(f"\n{C_GREEN}[OK] Reorganizacion finalizada:{C_RESET} {moved_count} proyectos organizados correctamente.")
    if errors:
        print(f"{C_RED}[!] Ocurrieron {len(errors)} errores al mover.{C_RESET}")

    # Regenerar catalogo repos.local.json si hubo cambios
    script_dir = os.path.dirname(os.path.abspath(__file__))
    cat_local = os.path.join(script_dir, "repos.local.json")
    cat_master = os.path.join(script_dir, "repos.json")
    catalog_file = cat_local if os.path.isfile(cat_local) else cat_master

    if os.path.isfile(catalog_file):
        try:
            with open(catalog_file, "r", encoding="utf-8-sig") as f:
                cat_data = json.load(f)
            updated = False
            for c_entry in cat_data:
                for item, target_org in plan:
                    if c_entry.get("name") == item["name"]:
                        c_entry["group"] = target_org
                        c_entry["path"] = f"{target_org}/{item['name']}"
                        updated = True
            if updated:
                with open(catalog_file, "w", encoding="utf-8") as f:
                    json.dump(cat_data, f, indent=4, ensure_ascii=False)
                print(f"{C_GREEN}[OK] Catalogo {os.path.basename(catalog_file)} actualizado con las nuevas rutas.{C_RESET}\n")
        except Exception:
            pass

    return {"status": "completed", "moved": moved_count}

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repos_dir = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else os.path.abspath(os.path.join(script_dir, ".."))
    run_onboarding_assistant(repos_dir, interactive=True)

if __name__ == "__main__":
    main()
