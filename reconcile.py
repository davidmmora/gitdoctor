#!/usr/bin/env python3
# ==============================================================================
# reconcile.py -- Auditoria de Seguridad y Reconciliacion Inteligente
# ==============================================================================

import os
import sys
import json
import subprocess

try:
    from agent import reindex_and_sync_catalog
except ImportError:
    reindex_and_sync_catalog = None

C_RESET = "\033[0m"
C_CYAN = "\033[36m"
C_GREEN = "\033[32m"
C_YELLOW = "\033[33m"
C_RED = "\033[31m"
C_MAGENTA = "\033[35m"
C_GRAY = "\033[90m"
C_BOLD = "\033[1m"

def normalize_url(url):
    if not url:
        return ""
    u = url.strip()
    if u.endswith('.git'):
        u = u[:-4]
    u = u.replace("git@github.com:", "https://github.com/")
    u = u.replace("ssh://git@github.com/", "https://github.com/")
    return u.lower().rstrip('/')

def run_cmd(cmd, cwd):
    try:
        return subprocess.check_output(cmd, cwd=cwd, stderr=subprocess.DEVNULL).decode('utf-8', errors='replace').strip()
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

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Resolver catalogo: repos.local.json (si existe) o repos.json
    cat_local = os.path.join(script_dir, "repos.local.json")
    cat_master = os.path.join(script_dir, "repos.json")
    catalog_file = cat_local if os.path.isfile(cat_local) else cat_master

    # Cargar configuracion local si existe
    cfg_path = os.path.join(script_dir, "config.local.json")
    local_cfg = {}
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as cf:
                local_cfg = json.load(cf)
        except Exception:
            pass

    # Resolver organizaciones conocidas dinamicamente
    known_orgs = {"Personal"}
    if local_cfg.get("enabled_orgs"):
        known_orgs.update(local_cfg["enabled_orgs"])
    if local_cfg.get("disabled_orgs"):
        known_orgs.update(local_cfg["disabled_orgs"])

    # Resolver directorio de repositorios (respeta config.local.json si se personalizo)
    repos_dir = None
    cli_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if cli_arg and cli_arg.lower() in ("reindex", "--reindex", "-r", "--auto"):
        if local_cfg.get("repos_dir") and os.path.isdir(local_cfg["repos_dir"]):
            repos_dir = os.path.abspath(local_cfg["repos_dir"])
        else:
            parent = os.path.abspath(os.path.join(script_dir, ".."))
            if os.path.basename(parent) in known_orgs or os.path.basename(parent).lower() in ["personal", "repos-sync"]:
                repos_dir = os.path.abspath(os.path.join(parent, ".."))
            else:
                repos_dir = parent
        if reindex_and_sync_catalog:
            reindex_and_sync_catalog(
                repos_dir=repos_dir,
                catalog_file=catalog_file,
                script_dir=script_dir,
                sync_remote_transfers=("--local" not in sys.argv),
                auto_move_physical=("--no-move" not in sys.argv),
                quiet=False
            )
            return

    if len(sys.argv) > 1 and sys.argv[1]:
        repos_dir = os.path.abspath(sys.argv[1])
    elif local_cfg.get("repos_dir") and os.path.isdir(local_cfg["repos_dir"]):
        repos_dir = os.path.abspath(local_cfg["repos_dir"])
    else:
        parent = os.path.abspath(os.path.join(script_dir, ".."))
        if os.path.basename(parent) in known_orgs or os.path.basename(parent).lower() in ["personal", "repos-sync"]:
            repos_dir = os.path.abspath(os.path.join(parent, ".."))
        else:
            repos_dir = parent

    print(f"\n{C_CYAN}=========================================================={C_RESET}")
    print(f"{C_CYAN}  GitDoctor -- Auditoria y Reconciliacion Clinica         {C_RESET}")
    print(f"{C_GRAY}  Analizando directorio: {repos_dir}{C_RESET}")
    print(f"{C_CYAN}=========================================================={C_RESET}\n")

    if not os.path.isfile(catalog_file):
        print(f"{C_RED}[ERROR] No se encontro {catalog_file}{C_RESET}")
        sys.exit(1)

    with open(catalog_file, 'r', encoding='utf-8-sig') as f:
        catalog = json.load(f)

    catalog_by_url = {}
    catalog_by_name = {}
    for entry in catalog:
        norm = normalize_url(entry['url'])
        catalog_by_url[norm] = entry
        catalog_by_name[entry['name']] = entry

    # 1. Escanear repositorios locales (nivel 1 y nivel 2)
    local_repo_paths = []
    for item in sorted(os.listdir(repos_dir)):
        p1 = os.path.join(repos_dir, item)
        if is_gitdoctor_path(p1, script_dir) or item.startswith('.'):
            continue
        if not os.path.isdir(p1):
            continue

        if os.path.isdir(os.path.join(p1, ".git")):
            local_repo_paths.append(p1)
        else:
            try:
                for sub in sorted(os.listdir(p1)):
                    p2 = os.path.join(p1, sub)
                    if is_gitdoctor_path(p2, script_dir) or sub.startswith('.'):
                        continue
                    if os.path.isdir(p2) and os.path.isdir(os.path.join(p2, ".git")):
                        local_repo_paths.append(p2)
            except Exception:
                pass

    inspected_repos = []
    dirty_repos = []
    unpushed_repos = []

    for r_path in local_repo_paths:
        remote = run_cmd(['git', 'remote', 'get-url', 'origin'], cwd=r_path)
        norm_remote = normalize_url(remote)
        branch = run_cmd(['git', 'branch', '--show-current'], cwd=r_path) or "(detached)"
        folder_display = os.path.relpath(r_path, repos_dir)

        status_out = run_cmd(['git', 'status', '--porcelain'], cwd=r_path)
        status_lines = [l for l in status_out.splitlines() if l.strip()]
        has_dirty = len(status_lines) > 0

        upstream = run_cmd(['git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}'], cwd=r_path)
        ahead = 0
        if upstream:
            ahead_str = run_cmd(['git', 'rev-list', '--count', '@{u}..HEAD'], cwd=r_path)
            ahead = int(ahead_str) if ahead_str.isdigit() else 0
        else:
            head_count = run_cmd(['git', 'rev-list', '--count', 'HEAD'], cwd=r_path)
            ahead = int(head_count) if head_count.isdigit() else 0

        info = {
            'folder': folder_display,
            'path': r_path,
            'remote': remote,
            'norm_remote': norm_remote,
            'branch': branch,
            'dirty_lines': len(status_lines),
            'ahead': ahead
        }
        inspected_repos.append(info)

        if has_dirty:
            dirty_repos.append(info)
        if ahead > 0:
            unpushed_repos.append(info)

    # -------------------------------------------------------------
    # FASE 1: AUDITORIA DE SEGURIDAD (Cambios locales o pendientes)
    # -------------------------------------------------------------
    print(f"{C_BOLD}--- [1/3] Auditoria de Seguridad: Cambios Pendientes ---{C_RESET}")

    if dirty_repos or unpushed_repos:
        print(f"\n{C_YELLOW}[!] ATENCION: Se detectaron repositorios con trabajo local pendiente:{C_RESET}")
        for r in inspected_repos:
            if r['dirty_lines'] > 0 or r['ahead'] > 0:
                msgs = []
                if r['dirty_lines'] > 0:
                    msgs.append(f"{r['dirty_lines']} archivo(s) sin commit")
                if r['ahead'] > 0:
                    msgs.append(f"{r['ahead']} commit(s) pendientes de push")
                print(f"  * {C_BOLD}{r['folder']}{C_RESET} (rama: {r['branch']}): {C_RED}{', '.join(msgs)}{C_RESET}")
        print(f"\n{C_GRAY}Consejo: Si reconoces estos cambios, haz commit y git push antes de mover o sincronizar.{C_RESET}\n")
    else:
        print(f"{C_GREEN}[OK] Todos los repositorios locales estan limpios y respaldados.{C_RESET}\n")

    # -------------------------------------------------------------
    # FASE 2: DETECCION DE DISCREPANCIAS DE NOMBRES Y UBICACION
    # -------------------------------------------------------------
    print(f"{C_BOLD}--- [2/3] Deteccion de Discrepancias y Reorganizacion ---{C_RESET}")

    renames_needed = []
    already_matched = set()

    for r in inspected_repos:
        # Excepcion absoluta: GitDoctor es la suite orquestadora y nunca se modifica
        if is_gitdoctor_path(r['path'], script_dir) or r['norm_remote'].endswith('/gitdoctor') or r['norm_remote'].endswith('/repos-sync'):
            continue

        if r['norm_remote'] in catalog_by_url:
            canonical_entry = catalog_by_url[r['norm_remote']]
            canonical_name = canonical_entry['name']
            already_matched.add(canonical_name)

            target_rel = canonical_entry.get('path', os.path.join(canonical_entry.get('group', ''), canonical_name))
            target_full = os.path.abspath(os.path.join(repos_dir, target_rel))

            if os.path.abspath(r['path']) != target_full:
                renames_needed.append({
                    'current_display': r['folder'],
                    'target_rel': target_rel,
                    'current_path': r['path'],
                    'target_path': target_full,
                    'has_dirty': (r['dirty_lines'] > 0 or r['ahead'] > 0)
                })

    if renames_needed:
        print(f"\n{C_YELLOW}Se encontraron repositorios que requieren reorganizarse segun el catalogo oficial:{C_RESET}\n")
        for item in renames_needed:
            warn = f" {C_YELLOW}(Tiene cambios pendientes){C_RESET}" if item['has_dirty'] else ""
            print(f"  * Ubicacion actual: {C_RED}{item['current_display']}{C_RESET}  -->  Ubicacion oficial: {C_GREEN}{item['target_rel']}{C_RESET}{warn}")

        print(f"\n{C_BOLD}¿Deseas mover estas carpetas a su ubicacion organizada automaticamente?{C_RESET}")
        print(f"{C_GRAY}(Esto NO altera tu codigo ni tus ramas, solo acomoda las carpetas y evita clonar de nuevo){C_RESET}")
        try:
            ans = input(f"{C_BOLD}Organizar carpetas ahora? [S/n]: {C_RESET}").strip().lower()
        except EOFError:
            ans = 's'

        if ans in ['', 's', 'si', 'y', 'yes']:
            for item in renames_needed:
                t_path = item['target_path']
                t_parent = os.path.dirname(t_path)
                if not os.path.exists(t_parent):
                    os.makedirs(t_parent, exist_ok=True)

                if os.path.exists(t_path):
                    print(f"  {C_RED}[!] No se puede mover '{item['current_display']}' porque ya existe '{item['target_rel']}'.{C_RESET}")
                else:
                    try:
                        os.rename(item['current_path'], t_path)
                        print(f"  {C_GREEN}[OK] Movido: '{item['current_display']}' -> '{item['target_rel']}'{C_RESET}")
                    except Exception as e:
                        print(f"  {C_RED}[ERROR] No se pudo mover: {e}{C_RESET}")
    else:
        print(f"{C_GREEN}[OK] Todas las carpetas locales coinciden con la estructura organizada del catalogo.{C_RESET}\n")

    # -------------------------------------------------------------
    # FASE 3: REPOSITORIOS EXTRAS / FALTANTES
    # -------------------------------------------------------------
    print(f"{C_BOLD}--- [3/3] Resumen de Repositorios Extras y Faltantes ---{C_RESET}")

    def is_gitdoctor_repo(r_dict):
        p = os.path.abspath(r_dict.get('path', ''))
        nr = r_dict.get('norm_remote', '')
        return is_gitdoctor_path(p, script_dir) or nr.endswith('/gitdoctor') or nr.endswith('/repos-sync')

    extras = [r for r in inspected_repos if r['norm_remote'] and (r['norm_remote'] not in catalog_by_url) and not is_gitdoctor_repo(r)]
    if extras:
        print(f"\n{C_YELLOW}[INFO] Se encontraron repositorios en este equipo que NO estan en repos.json:{C_RESET}")
        for ex in extras:
            print(f"  * {ex['folder']} ({ex['remote']})")
        try:
            ans_add = input(f"\n{C_BOLD}¿Deseas agregarlos al catalogo repos.json para sincronizarlos con Windows? [S/n]: {C_RESET}").strip().lower()
        except EOFError:
            ans_add = 's'

        if ans_add in ['', 's', 'si', 'y', 'yes']:
            for ex in extras:
                catalog.append({
                    'name': os.path.basename(ex['folder']),
                    'group': 'Personal',
                    'path': f"Personal/{os.path.basename(ex['folder'])}",
                    'url': ex['remote'],
                    'defaultBranch': ex['branch']
                })
            with open(catalog_file, 'w', encoding='utf-8') as f:
                json.dump(catalog, f, indent=4, ensure_ascii=False)
            print(f"{C_GREEN}[OK] Catalogo repos.json actualizado con los repositorios nuevos.{C_RESET}")

    missing = []
    for c in catalog:
        if c.get('name') in ['gitdoctor', 'repos-sync'] or c.get('url', '').endswith('/gitdoctor.git') or c.get('url', '').endswith('/repos-sync.git'):
            continue
        c_rel = c.get('path', os.path.join(c.get('group', ''), c['name']))
        if not os.path.exists(os.path.join(repos_dir, c_rel)):
            missing.append(c)

    if missing:
        print(f"\n{C_CYAN}📥 Repositorios del catalogo que aun no tienes en este equipo ({len(missing)}):{C_RESET}")
        for m in missing:
            print(f"  * {m.get('group', '')}/{m['name']} ({m['url']})")
        print(f"{C_GRAY}Estos se clonaran automaticamente cuando ejecutes sync.sh.{C_RESET}")

    print(f"\n{C_GREEN}=========================================================={C_RESET}")
    print(f"{C_GREEN}  Auditoria y Reconciliacion completada.                  {C_RESET}")
    print(f"{C_GREEN}==========================================================\n{C_RESET}")

if __name__ == '__main__':
    main()
