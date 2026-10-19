#!/usr/bin/env python3
# ==============================================================================
# agent.py -- GitDoctor AI: Suite Clinica de Salud, Seguridad y DevOps
# ==============================================================================
# - Gestion de Salud 360°, Gitflow, Secretos y Sincronizacion Multi-Equipo (Windows & macOS)
# - Soporte Multi-IA (Ollama Local Offline + Google Gemini Cloud)
# - Gestion Multi-Trabajo y Multi-Proveedor (GitHub, GitLab, Bitbucket, Azure DevOps)
# - Sincronizacion Selectiva por Maquina (Filtro de Organizaciones y Ahorro de Disco)
# - Descarga Bajo Demanda y Apertura Directa en Visual Studio Code
# - Modo Vigilante con Notificaciones Nativas del Sistema Operativo
# ==============================================================================

import os
import sys
import json
import time
import re
import difflib
import getpass
import subprocess
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    from onboarding import run_onboarding_assistant
except ImportError:
    run_onboarding_assistant = None

# Configurar encoding UTF-8 seguro para consolas Windows y Mac
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

# ==============================================================================
# CONSTANTES Y CONFIGURACION VISUAL
# ==============================================================================
C_RESET   = "\033[0m"
C_CYAN    = "\033[36m"
C_GREEN   = "\033[32m"
C_YELLOW  = "\033[33m"
C_RED     = "\033[31m"
C_MAGENTA = "\033[35m"
C_WHITE   = "\033[1;37m"
C_GRAY    = "\033[90m"
C_BOLD    = "\033[1m"

DEFAULT_ORGS = [
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

GITIGNORE_TEMPLATES = {
    "node": "node_modules/\ndist/\nbuild/\n.env\n.env.local\n.next/\n*.log\n.DS_Store\nThumbs.db\n.firebase/\n.vscode/\n",
    "python": "__pycache__/\n*.py[cod]\n*$py.class\n.venv/\nenv/\nvirtualenv/\n.env\n*.tmp\n.DS_Store\nThumbs.db\n.vscode/\n",
    "standard": "node_modules/\n__pycache__/\n.env\n*.tmp\n.DS_Store\nThumbs.db\n.firebase/\n.vscode/\n"
}

JUNK_PATTERNS = [
    ".firebase",
    ".DS_Store",
    "Thumbs.db",
    "vsce-debug.log",
    "npm-debug.log",
    ".vscode"
]

PRUNABLE_FOLDERS = [
    "node_modules",
    ".next",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".firebase",
    ".turbo"
]

COPILOT_TRAILER = "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"

# ==============================================================================
# UTILIDADES GIT Y RUTAS
# ==============================================================================
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

def normalize_url(url):
    if not url:
        return ""
    u = url.strip()
    if u.endswith('.git'):
        u = u[:-4]
    u = u.replace("git@github.com:", "https://github.com/")
    u = u.replace("ssh://git@github.com/", "https://github.com/")
    return u.lower().rstrip('/')

def run_cmd(cmd, cwd=None, timeout=30):
    try:
        res = subprocess.run(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=timeout,
            check=False
        )
        return res.stdout.decode('utf-8', errors='replace').strip()
    except Exception:
        return ""

# ==============================================================================
# NOTIFICACIONES NATIVAS DEL SISTEMA OPERATIVO (WINDOWS, MACOS, LINUX)
# ==============================================================================
def send_os_notification(title, message):
    """
    Envia una notificacion nativa del sistema operativo con CERO dependencias pip:
    - En Windows: Notificacion Toast de Windows Runtime via PowerShell.
    - En macOS: Notificacion en el Centro de Notificaciones via AppleScript / osascript.
    - En Linux: Notificacion de escritorio via notify-send.
    """
    clean_title = title.replace("'", "").replace('"', "")
    clean_msg = message.replace("'", "").replace('"', "")

    try:
        if sys.platform == 'win32':
            ps_script = f"""
[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
$template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
$strings = $template.GetElementsByTagName('text')
$strings[0].AppendChild($template.CreateTextNode('{clean_title}')) | Out-Null
$strings[1].AppendChild($template.CreateTextNode('{clean_msg}')) | Out-Null
$toast = [Windows.UI.Notifications.ToastNotification]::new($template)
[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier('GitDoctor').Show($toast)
"""
            subprocess.run(['powershell', '-WindowStyle', 'Hidden', '-Command', ps_script],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            return True

        elif sys.platform == 'darwin':
            osa_cmd = f'display notification "{clean_msg}" with title "{clean_title}"'
            subprocess.run(['osascript', '-e', osa_cmd],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            return True

        else:
            subprocess.run(['notify-send', clean_title, clean_msg],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
            return True
    except Exception:
        return False

# ==============================================================================
# CONFIGURACION LOCAL POR MAQUINA (_sync/config.local.json)
# ==============================================================================
def load_local_config(script_dir):
    """Carga la configuracion especifica de esta maquina"""
    cfg_file = os.path.join(script_dir, "config.local.json")
    default_cfg = {
        "sync_mode": "mirror",       # "mirror" (identico en todas partes) o "selective" (personalizado por maquina)
        "enabled_orgs": [],          # Vacio = Todas las detectadas estan activadas
        "disabled_orgs": [],         # Organizaciones omitidas en este equipo (solo en modo selective)
        "notifications_enabled": True,
        "watchdog_interval_seconds": 300
    }
    if os.path.isfile(cfg_file):
        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                default_cfg.update(data)
        except Exception:
            pass
    return default_cfg

def save_local_config(script_dir, cfg):
    """Guarda la configuracion local de la maquina"""
    cfg_file = os.path.join(script_dir, "config.local.json")
    try:
        with open(cfg_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"{C_RED}[ERROR] No se pudo guardar config.local.json: {e}{C_RESET}")
        return False

def interactive_toggle_sync_mode(script_dir, local_cfg):
    """Permite alternar entre Modo Espejo (Identico) y Modo Personalizado (Selectivo)"""
    cur_mode = local_cfg.get("sync_mode", "mirror")
    print(f"\n{C_CYAN}================================================================{C_RESET}")
    print(f"{C_CYAN}  Modo de Sincronizacion de Organizaciones en este Equipo       {C_RESET}")
    print(f"{C_CYAN}================================================================{C_RESET}")
    mode_str = "MODO ESPEJO (IDENTICO)" if cur_mode == "mirror" else "MODO PERSONALIZADO (SELECTIVO)"
    print(f"Modo actual: {C_GREEN if cur_mode == 'mirror' else C_YELLOW}[{mode_str}]{C_RESET}\n")

    print(f"  {C_BOLD}[1] Modo Espejo (Identico):{C_RESET}")
    print(f"      Mantiene exactamente las mismas organizaciones y repositorios en todos tus equipos.")
    print(f"      Cualquier organizacion nueva creada en GitHub o en otro equipo se clonara aqui.\n")

    print(f"  {C_BOLD}[2] Modo Personalizado (Selectivo):{C_RESET}")
    print(f"      Tu decides que organizaciones mantener en este equipo y cuales omitir.")
    print(f"      Ideal para laptops con poco disco para que las organizaciones pesadas solo vivan en GitHub.\n")

    try:
        ans = input(f"{C_BOLD}Selecciona el modo [1=Espejo, 2=Personalizado, Enter=Mantener]: {C_RESET}").strip()
    except EOFError:
        ans = ""

    if ans == "1":
        local_cfg["sync_mode"] = "mirror"
        local_cfg["disabled_orgs"] = []
        save_local_config(script_dir, local_cfg)
        print(f"\n{C_GREEN}[OK] Modo cambiado a: ESPEJO (IDENTICO). Todas las organizaciones se mantendran sincronizadas.{C_RESET}\n")
    elif ans == "2":
        local_cfg["sync_mode"] = "selective"
        save_local_config(script_dir, local_cfg)
        print(f"\n{C_YELLOW}[OK] Modo cambiado a: PERSONALIZADO (SELECTIVO). Usa /orgs para elegir que organizaciones mantener.{C_RESET}\n")

    return local_cfg.get("sync_mode", "mirror")

def interactive_manage_orgs(repos_dir, catalog, local_cfg, script_dir, all_known_orgs):
    """Interfaz interactiva para activar o desactivar organizaciones en este equipo"""
    sync_mode = local_cfg.get("sync_mode", "mirror")
    mode_label = f"{C_GREEN}[ESPEJO / IDENTICO]{C_RESET}" if sync_mode == "mirror" else f"{C_YELLOW}[PERSONALIZADO / SELECTIVO]{C_RESET}"

    print(f"\n{C_CYAN}================================================================{C_RESET}")
    print(f"{C_CYAN}  Configuracion de Organizaciones en este Equipo                {C_RESET}")
    print(f"{C_CYAN}================================================================{C_RESET}")
    print(f"Modo de sincronizacion actual: {mode_label}")
    if sync_mode == "mirror":
        print(f"{C_GRAY}En Modo Espejo todas las organizaciones se mantienen sincronizadas de forma identica.{C_RESET}")
        print(f"{C_GRAY}Para desactivar organizaciones individuales en esta maquina, escribe 'm' para pasar a Modo Personalizado.{C_RESET}\n")
    else:
        print(f"{C_GRAY}Puedes desactivar organizaciones pesadas en laptops con poco disco.{C_RESET}")
        print(f"{C_GRAY}Las desactivadas no se clonaran automaticamente ni ensuciaran tu auditoria.{C_RESET}\n")

    disabled_set = set(local_cfg.get("disabled_orgs", [])) if sync_mode == "selective" else set()

    while True:
        print(f"{C_BOLD}Organizaciones disponibles:{C_RESET}")
        for idx, org in enumerate(all_known_orgs, 1):
            repos_in_org = len([c for c in catalog if c.get("group") == org])
            is_active = (org not in disabled_set)
            status_tag = f"{C_GREEN}[X] Activa{C_RESET}     " if is_active else f"{C_RED}[ ] Omitida{C_RESET}    "
            print(f"  [{idx}] {status_tag} {C_BOLD}{org:<15}{C_RESET} ({repos_in_org} repositorios en catalogo)")

        print(f"\n{C_GRAY}Comandos: Escribe el numero (1-{len(all_known_orgs)}) para alternar, 'm' para cambiar Modo (Espejo/Personalizado), 'todas' para activar todas, o Enter para guardar y salir.{C_RESET}")
        try:
            choice = input(f"{C_CYAN}Alternar organizacion > {C_RESET}").strip().lower()
        except EOFError:
            break

        if not choice:
            break

        if choice in ["m", "modo"]:
            new_mode = interactive_toggle_sync_mode(script_dir, local_cfg)
            sync_mode = new_mode
            disabled_set = set(local_cfg.get("disabled_orgs", [])) if sync_mode == "selective" else set()
            continue

        if choice in ["todas", "all", "t"]:
            disabled_set.clear()
            local_cfg["sync_mode"] = "mirror"
            print(f"\n{C_GREEN}[OK] Todas las organizaciones han sido activadas (Modo Espejo).{C_RESET}\n")
            continue

        if choice.isdigit():
            i = int(choice)
            if 1 <= i <= len(all_known_orgs):
                chosen_org = all_known_orgs[i - 1]
                if sync_mode == "mirror":
                    # Cambiar a modo selectivo automaticamente al desactivar una org
                    local_cfg["sync_mode"] = "selective"
                    sync_mode = "selective"
                    print(f"{C_GRAY}(Cambiando a Modo Personalizado/Selectivo para esta maquina){C_RESET}")

                if chosen_org in disabled_set:
                    disabled_set.remove(chosen_org)
                    print(f"\n{C_GREEN}[+] '{chosen_org}' ahora esta ACTIVADA en este equipo.{C_RESET}")
                    org_folder = os.path.join(repos_dir, chosen_org)
                    if not os.path.isdir(org_folder):
                        try:
                            dl_ans = input(f"{C_BOLD}¿Deseas descargar los repositorios de '{chosen_org}' desde GitHub ahora? [S/n]: {C_RESET}").strip().lower()
                        except EOFError:
                            dl_ans = "s"
                        if dl_ans in ["", "s", "si", "y", "yes"]:
                            clone_specific_repo_or_org(repos_dir, catalog, chosen_org)
                    print("")
                else:
                    disabled_set.add(chosen_org)
                    print(f"\n{C_YELLOW}[-] '{chosen_org}' ahora esta DESACTIVADA en este equipo (solo vivira en GitHub).{C_RESET}")
                    org_folder = os.path.join(repos_dir, chosen_org)
                    if os.path.isdir(org_folder):
                        has_dirty = False
                        has_ahead = False
                        for sub in os.listdir(org_folder):
                            sub_p = os.path.join(org_folder, sub)
                            if os.path.isdir(os.path.join(sub_p, ".git")):
                                st = run_cmd(["git", "status", "--porcelain"], cwd=sub_p)
                                if st: has_dirty = True
                                ah = run_cmd(["git", "rev-list", "--count", "@{u}..HEAD"], cwd=sub_p)
                                if ah and ah.isdigit() and int(ah) > 0: has_ahead = True

                        if has_dirty or has_ahead:
                            print(f"  {C_RED}[!] ATENCION: Hay cambios locales sin guardar o sin subir en '{chosen_org}'. Se conserva la carpeta en disco para proteger tu codigo.{C_RESET}\n")
                        else:
                            try:
                                rm_ans = input(f"{C_BOLD}¿Deseas eliminar la copia local de '{chosen_org}' para liberar espacio (esta 100% segura en GitHub)? [s/N]: {C_RESET}").strip().lower()
                            except EOFError:
                                rm_ans = "n"
                            if rm_ans in ["s", "si", "y", "yes"]:
                                import shutil
                                shutil.rmtree(org_folder, ignore_errors=True)
                                print(f"  {C_GREEN}[OK] Copia local eliminada. La organizacion '{chosen_org}' ahora solo vive en la nube (GitHub).{C_RESET}\n")
            else:
                print(f"{C_RED}[!] Opcion invalida.{C_RESET}\n")
        else:
            print(f"{C_RED}[!] Escribe un numero o presiona Enter para guardar.{C_RESET}\n")

    local_cfg["disabled_orgs"] = sorted(list(disabled_set))
    local_cfg["enabled_orgs"] = [o for o in all_known_orgs if o not in disabled_set]
    save_local_config(script_dir, local_cfg)
    print(f"{C_GREEN}[OK] Configuracion guardada en _sync/config.local.json.{C_RESET}\n")
    return local_cfg

def api_manage_organizations(repos_dir, catalog, local_cfg, script_dir, all_known_orgs, action, org_name=None, remove_local_folder=False):
    """API para consultar, activar o desactivar organizaciones (llamable por Gemini AI)"""
    disabled_set = set(local_cfg.get("disabled_orgs", []))
    if action == "list":
        return {
            "all_orgs": all_known_orgs,
            "active_orgs": [o for o in all_known_orgs if o not in disabled_set],
            "disabled_orgs": list(disabled_set)
        }
    elif action == "disable":
        if not org_name:
            return {"error": "org_name es requerido para desactivar"}
        match = None
        for o in all_known_orgs:
            if o.lower() == org_name.lower():
                match = o
                break
        if not match:
            return {"error": f"Organizacion '{org_name}' no encontrada"}
        disabled_set.add(match)
        local_cfg["disabled_orgs"] = sorted(list(disabled_set))
        local_cfg["enabled_orgs"] = [o for o in all_known_orgs if o not in disabled_set]
        save_local_config(script_dir, local_cfg)

        removed_folder = False
        if remove_local_folder:
            org_folder = os.path.join(repos_dir, match)
            if os.path.isdir(org_folder):
                import shutil
                shutil.rmtree(org_folder, ignore_errors=True)
                removed_folder = True

        return {
            "success": True,
            "disabled_org": match,
            "removed_local_folder": removed_folder,
            "message": f"Organizacion '{match}' desactivada en este equipo. Ahora solo vive en GitHub."
        }
    elif action == "enable":
        if not org_name:
            return {"error": "org_name es requerido para activar"}
        match = None
        for o in all_known_orgs:
            if o.lower() == org_name.lower():
                match = o
                break
        if not match:
            return {"error": f"Organizacion '{org_name}' no encontrada"}
        if match in disabled_set:
            disabled_set.remove(match)
        local_cfg["disabled_orgs"] = sorted(list(disabled_set))
        local_cfg["enabled_orgs"] = [o for o in all_known_orgs if o not in disabled_set]
        save_local_config(script_dir, local_cfg)
        return {
            "success": True,
            "enabled_org": match,
            "message": f"Organizacion '{match}' activada en este equipo."
        }
    return {"error": "Accion no valida"}

# ==============================================================================
# SEGURIDAD Y GESTION DE API KEY (GEMINI)
# ==============================================================================
def sanitize_error(text):
    """Elimina cualquier clave o token de mensajes de error o URLs"""
    if not text:
        return ""
    text = re.sub(r'key=[A-Za-z0-9_\-]+', 'key=[PROTEGIDO]', str(text))
    text = re.sub(r'AIza[0-9A-Za-z\-_]{35}', '[API_KEY_PROTEGIDA]', str(text))
    return text

def get_masked_key(key):
    """Devuelve version ofuscada de la API key para visualizacion segura"""
    if not key:
        return "No configurada"
    if len(key) <= 8:
        return "***"
    return f"{key[:4]}...{key[-4:]}"

def ensure_env_in_gitignore(script_dir):
    """Garantiza que .env y archivos locales esten en .gitignore"""
    gi_path = os.path.join(script_dir, ".gitignore")
    lines = []
    if os.path.isfile(gi_path):
        try:
            with open(gi_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines()]
        except Exception:
            pass

    needed = [".env", "*.env", "config.local.json", "*.local.json"]
    to_add = [n for n in needed if n not in lines]
    if to_add:
        try:
            with open(gi_path, "a", encoding="utf-8") as f:
                f.write("\n# Archivos locales de configuracion y claves privadas\n")
                for n in to_add:
                    f.write(f"{n}\n")
        except Exception:
            pass

def save_gemini_api_key(script_dir, key):
    """Guarda la API key en _sync/.env con permisos restringidos"""
    key = key.strip()
    if not key:
        return False

    ensure_env_in_gitignore(script_dir)
    env_path = os.path.join(script_dir, ".env")

    existing_lines = []
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip().startswith("GEMINI_API_KEY="):
                        existing_lines.append(line)
        except Exception:
            pass

    existing_lines.append(f"GEMINI_API_KEY={key}\n")

    try:
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(existing_lines)

        if hasattr(os, 'chmod') and os.name != 'nt':
            try:
                os.chmod(env_path, 0o600)
            except Exception:
                pass
        return True
    except Exception as e:
        print(f"{C_RED}[ERROR] No se pudo guardar la clave: {sanitize_error(e)}{C_RESET}")
        return False

def load_gemini_api_key(script_dir, interactive=False):
    """Carga la API key desde variable de entorno o archivo .env"""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key

    env_path = os.path.join(script_dir, ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("GEMINI_API_KEY="):
                        k = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if k:
                            return k
        except Exception:
            pass

    if not interactive:
        return None

    print(f"\n{C_YELLOW}+--------------------------------------------------------+{C_RESET}")
    print(f"{C_YELLOW}|  Configuracion de Seguridad para Gemini AI             |{C_RESET}")
    print(f"{C_YELLOW}+--------------------------------------------------------+{C_RESET}")
    print(f"{C_GRAY}Tu API Key se guardara en {C_WHITE}_sync/.env{C_GRAY} (ignorado por Git con .gitignore).{C_RESET}")
    print(f"{C_GRAY}Si no tienes una o prefieres omitir, presiona Enter para usar comandos locales.{C_RESET}\n")

    user_key = ""
    try:
        user_key = getpass.getpass(f"{C_BOLD}Introduce tu Gemini API Key: {C_RESET}").strip()
    except Exception:
        try:
            user_key = input(f"{C_BOLD}Introduce tu Gemini API Key: {C_RESET}").strip()
        except EOFError:
            user_key = ""

    if user_key:
        if save_gemini_api_key(script_dir, user_key):
            print(f"{C_GREEN}[OK] API Key guardada exitosamente y protegida localmente.{C_RESET}\n")
            return user_key

    return None

# ==============================================================================
# GESTION DE SESION Y PERFIL DE GITHUB (gh CLI)
# ==============================================================================
def get_github_status():
    """Obtiene el estado completo de la sesion de GitHub mediante gh CLI"""
    info = {
        'installed': False,
        'logged_in': False,
        'user': None,
        'name': None,
        'email': None,
        'accounts': [],
        'orgs': [],
        'git_name': run_cmd(['git', 'config', '--global', 'user.name']),
        'git_email': run_cmd(['git', 'config', '--global', 'user.email']),
        'raw_status': ''
    }

    gh_version = run_cmd(['gh', '--version'])
    if not gh_version:
        return info
    info['installed'] = True

    try:
        res = subprocess.run(['gh', 'api', 'user'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if res.returncode == 0:
            data = json.loads(res.stdout.decode('utf-8'))
            info['logged_in'] = True
            info['user'] = data.get('login')
            info['name'] = data.get('name')
            info['email'] = data.get('email')
    except Exception:
        pass

    try:
        res = subprocess.run(['gh', 'api', 'user/orgs'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if res.returncode == 0:
            orgs = json.loads(res.stdout.decode('utf-8'))
            info['orgs'] = [o['login'] for o in orgs if 'login' in o]
    except Exception:
        pass

    try:
        res = subprocess.run(['gh', 'auth', 'status'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
        out = res.stdout.decode('utf-8', errors='ignore')
        info['raw_status'] = out
        accs = re.findall(r'account\s+([A-Za-z0-9_\-]+)', out)
        info['accounts'] = list(dict.fromkeys(accs))
        if not info['user'] and accs:
            info['user'] = accs[0]
            info['logged_in'] = True
    except Exception:
        pass

    return info

def print_github_profile(gh_info):
    """Muestra una tarjeta visual con el perfil de GitHub y Git actual"""
    print(f"\n{C_BOLD}+--------------------------------------------------------+{C_RESET}")
    print(f"{C_BOLD}|  Perfil y Sesion de GitHub                             |{C_RESET}")
    print(f"{C_BOLD}+--------------------------------------------------------+{C_RESET}")

    if not gh_info['installed']:
        print(f"  {C_RED}[!] GitHub CLI ('gh') no esta instalado en este sistema.{C_RESET}")
        print(f"      Instalalo con: winget install GitHub.cli (Windows) o brew install gh (Mac)")
        print("")
        return

    if not gh_info['logged_in']:
        print(f"  {C_YELLOW}[!] No hay una sesion activa de GitHub.{C_RESET}")
        print(f"      Usa {C_WHITE}/login{C_RESET} para iniciar sesion con tu cuenta.")
        print("")
        return

    user_disp = f"@{gh_info['user']}"
    name_disp = f"({gh_info['name']})" if gh_info.get('name') else ""
    print(f"  * {C_BOLD}Usuario Activo:{C_RESET} {C_GREEN}{user_disp}{C_RESET} {name_disp}")
    if gh_info.get('email'):
        print(f"  * {C_BOLD}Email GitHub:{C_RESET}   {gh_info['email']}")

    accs = gh_info.get('accounts', [])
    if len(accs) > 1:
        print(f"  * {C_BOLD}Cuentas en este equipo ({len(accs)}):{C_RESET} {', '.join(accs)}")
        print(f"    {C_GRAY}(Puedes cambiar entre ellas con /switch){C_RESET}")

    orgs = gh_info.get('orgs', [])
    if orgs:
        print(f"  * {C_BOLD}Organizaciones ({len(orgs)}):{C_RESET} {', '.join(orgs)}")
    else:
        print(f"  * {C_BOLD}Organizaciones:{C_RESET} Ninguna organizacion detectada (solo repos personales)")

    git_id = []
    if gh_info.get('git_name'): git_id.append(gh_info['git_name'])
    if gh_info.get('git_email'): git_id.append(f"<{gh_info['git_email']}>")
    git_str = " ".join(git_id) if git_id else "No configurado"
    print(f"  * {C_BOLD}Identidad Git Local:{C_RESET} {git_str}")
    print("")

def interactive_github_login():
    """Inicia el proceso interactivo de login con gh CLI"""
    print(f"\n{C_CYAN}=========================================================={C_RESET}")
    print(f"{C_CYAN}  Iniciar Sesion en GitHub (GitHub CLI)                   {C_RESET}")
    print(f"{C_CYAN}=========================================================={C_RESET}")
    print(f"{C_GRAY}Se abrira el asistente oficial de GitHub CLI para autenticarte.{C_RESET}\n")

    res = subprocess.call(["gh", "auth", "login"])
    if res == 0:
        subprocess.run(["gh", "auth", "setup-git"], stderr=subprocess.DEVNULL)
        new_info = get_github_status()
        print(f"\n{C_GREEN}[OK] Sesion iniciada exitosamente como @{new_info.get('user', 'usuario')}!{C_RESET}")

        if new_info.get('name') or new_info.get('user') or new_info.get('email'):
            sug_name = new_info.get('name') or new_info.get('user')
            sug_email = new_info.get('email')
            print(f"\n{C_BOLD}Deseas configurar la identidad de Git para tus commits con esta cuenta?{C_RESET}")
            if sug_name: print(f"  - user.name:  {sug_name}")
            if sug_email: print(f"  - user.email: {sug_email}")
            try:
                ans = input(f"{C_BOLD}Actualizar git config global? [S/n]: {C_RESET}").strip().lower()
            except EOFError:
                ans = 's'
            if ans in ['', 's', 'si', 'y', 'yes']:
                if sug_name: run_cmd(['git', 'config', '--global', 'user.name', sug_name])
                if sug_email: run_cmd(['git', 'config', '--global', 'user.email', sug_email])
                print(f"{C_GREEN}[OK] Identidad de Git actualizada.{C_RESET}")
        print_github_profile(new_info)
        return {"success": True, "user": new_info.get('user')}
    else:
        print(f"\n{C_YELLOW}[!] Inicio de sesion cancelado o no completado.{C_RESET}\n")
        return {"success": False, "error": "Login cancelled"}

def interactive_github_switch(target_user=None):
    """Permite cambiar la cuenta activa de GitHub"""
    gh_info = get_github_status()
    accs = gh_info.get('accounts', [])

    if target_user:
        print(f"\n{C_CYAN}[*] Cambiando cuenta activa a @{target_user}...{C_RESET}")
        res = subprocess.call(["gh", "auth", "switch", "-u", target_user])
        if res == 0:
            new_info = get_github_status()
            print(f"{C_GREEN}[OK] Cuenta activa cambiada a @{new_info.get('user')}.{C_RESET}\n")
            return {"success": True, "active_user": new_info.get('user')}
        else:
            print(f"{C_RED}[ERROR] No se pudo cambiar a la cuenta @{target_user}.{C_RESET}\n")
            return {"success": False, "error": f"Failed to switch to {target_user}"}

    if len(accs) <= 1:
        print(f"\n{C_YELLOW}[INFO] Solo tienes 1 cuenta registrada (@{gh_info.get('user')}).{C_RESET}")
        print(f"{C_GRAY}Para agregar otra cuenta de GitHub (ej. de tu colega o personal), escribe {C_WHITE}/login{C_GRAY}.{C_RESET}\n")
        return {"success": False, "message": "Only one account registered. Use /login to add another."}

    print(f"\n{C_BOLD}Cuentas de GitHub autenticadas en este equipo:{C_RESET}")
    for idx, acc in enumerate(accs, 1):
        active_tag = f" {C_GREEN}(Activa actual){C_RESET}" if acc == gh_info.get('user') else ""
        print(f"  [{idx}] @{acc}{active_tag}")

    try:
        sel = input(f"\n{C_BOLD}Selecciona el numero de la cuenta a la que deseas cambiar: {C_RESET}").strip()
    except EOFError:
        sel = ""

    if sel.isdigit() and 1 <= int(sel) <= len(accs):
        chosen = accs[int(sel) - 1]
        res = subprocess.call(["gh", "auth", "switch", "-u", chosen])
        if res == 0:
            new_info = get_github_status()
            print(f"\n{C_GREEN}[OK] Cuenta activa cambiada a @{new_info.get('user')}!{C_RESET}")
            if new_info.get('name') or new_info.get('email'):
                try:
                    ans = input(f"{C_BOLD}Actualizar git user.name y user.email para esta cuenta? [S/n]: {C_RESET}").strip().lower()
                except EOFError:
                    ans = 's'
                if ans in ['', 's', 'si', 'y', 'yes']:
                    if new_info.get('name') or new_info.get('user'):
                        run_cmd(['git', 'config', '--global', 'user.name', new_info.get('name') or new_info.get('user')])
                    if new_info.get('email'):
                        run_cmd(['git', 'config', '--global', 'user.email', new_info.get('email')])
                    print(f"{C_GREEN}[OK] Identidad de Git actualizada.{C_RESET}")
            print("")
            return {"success": True, "active_user": new_info.get('user')}

    print(f"{C_YELLOW}[!] Operacion cancelada.{C_RESET}\n")
    return {"success": False, "message": "Cancelled"}

def interactive_github_logout(target_user=None):
    """Cierra la sesion de una cuenta de GitHub"""
    print(f"\n{C_YELLOW}[!] Cerrar sesion de GitHub:{C_RESET}")
    cmd = ["gh", "auth", "logout"]
    if target_user:
        cmd.extend(["-u", target_user])
    res = subprocess.call(cmd)
    new_info = get_github_status()
    print_github_profile(new_info)
    return {"success": (res == 0), "active_user": new_info.get('user')}

def interactive_git_identity(name=None, email=None):
    """Configura user.name y user.email de Git"""
    cur_name = run_cmd(['git', 'config', '--global', 'user.name'])
    cur_email = run_cmd(['git', 'config', '--global', 'user.email'])

    if name and email:
        run_cmd(['git', 'config', '--global', 'user.name', name])
        run_cmd(['git', 'config', '--global', 'user.email', email])
        print(f"{C_GREEN}[OK] Identidad Git actualizada: {name} <{email}>{C_RESET}\n")
        return {"success": True, "name": name, "email": email}

    print(f"\n{C_BOLD}Configuracion actual de Git (global):{C_RESET}")
    print(f"  * user.name:  {cur_name or '(no configurado)'}")
    print(f"  * user.email: {cur_email or '(no configurado)'}\n")

    try:
        new_name = input(f"Nuevo user.name [{cur_name}]: ").strip()
        new_email = input(f"Nuevo user.email [{cur_email}]: ").strip()
    except EOFError:
        return {"success": False}

    if new_name:
        run_cmd(['git', 'config', '--global', 'user.name', new_name])
    if new_email:
        run_cmd(['git', 'config', '--global', 'user.email', new_email])

    print(f"{C_GREEN}[OK] Identidad de Git actualizada con exito.{C_RESET}\n")
    return {"success": True}

def get_active_orgs(repos_dir, gh_info=None):
    """
    Determina dinamicamente las organizaciones activas combinando:
    1. Organizaciones de GitHub del usuario actual
    2. Organizaciones configuradas en config.local.json
    3. Carpetas locales en repos_dir (que no sean gitdoctor ni ocultas)
    4. 'Personal' y fallbacks conocidos
    """
    orgs = set()
    if gh_info and gh_info.get('orgs'):
        orgs.update(gh_info['orgs'])

    # Leer organizaciones desde config.local.json si existen
    script_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        cfg = load_local_config(script_dir)
        if cfg.get("enabled_orgs"):
            orgs.update(cfg["enabled_orgs"])
        if cfg.get("disabled_orgs"):
            orgs.update(cfg["disabled_orgs"])
    except Exception:
        pass

    try:
        if os.path.isdir(repos_dir):
            for item in os.listdir(repos_dir):
                p = os.path.join(repos_dir, item)
                if is_gitdoctor_path(p, script_dir) or item.startswith('.'):
                    continue
                if os.path.isdir(p):
                    orgs.add(item)
    except Exception:
        pass

    orgs.add("Personal")

    # Si la lista esta vacia (sin gh ni carpetas), sugerir las oficiales de fallback
    if len(orgs) <= 1:
        orgs.update(DEFAULT_ORGS)

    return sorted(list(orgs))

# ==============================================================================
# INTEGRACION CON VISUAL STUDIO CODE (/code <repo>)
# ==============================================================================
def open_repo_in_vscode(repos_dir, catalog, query):
    """Busca un repositorio por nombre o coincidencia difusa y lo abre en VS Code"""
    if not query:
        print(f"\n{C_YELLOW}[?] No indicaste el repositorio a abrir.{C_RESET}")
        try:
            query = input(f"{C_BOLD}Nombre o termino del proyecto a abrir en VS Code: {C_RESET}").strip()
        except EOFError:
            query = ""
        if not query:
            print(f"{C_GRAY}Operacion cancelada.{C_RESET}\n")
            return {"success": False, "error": "No query provided"}

    q = query.strip().lower()
    matches = []

    for entry in catalog:
        name = entry['name'].lower()
        grp = entry.get('group', '').lower()
        path = entry.get('path', '').lower()
        if q == name or q == path or q in name or q in grp:
            matches.append(entry)

    if not matches:
        # Buscar en carpetas fisicas si no esta en catalog
        try:
            for root, dirs, files in os.walk(repos_dir):
                if ".git" in dirs:
                    dirs.clear()
                    bname = os.path.basename(root).lower()
                    if q in bname:
                        rel = os.path.relpath(root, repos_dir)
                        matches.append({"name": os.path.basename(root), "path": rel, "group": os.path.dirname(rel)})
        except Exception:
            pass

    if not matches:
        print(f"\n{C_RED}[!] No se encontro ningun repositorio que coincida con '{query}'.{C_RESET}\n")
        return {"success": False, "error": "Repo not found"}

    target = None
    if len(matches) == 1:
        target = matches[0]
    else:
        # Coincidencia exacta de nombre
        exact = [m for m in matches if m['name'].lower() == q]
        if len(exact) == 1:
            target = exact[0]
        else:
            print(f"\n{C_BOLD}Se encontraron multiples repositorios que coinciden con '{query}':{C_RESET}")
            for idx, m in enumerate(matches[:8], 1):
                print(f"  [{idx}] {m.get('group', '')}/{m['name']}")
            try:
                ans = input(f"{C_BOLD}Selecciona el numero a abrir: {C_RESET}").strip()
                if ans.isdigit() and 1 <= int(ans) <= min(len(matches), 8):
                    target = matches[int(ans) - 1]
            except EOFError:
                return {"success": False}

    if not target:
        print(f"{C_YELLOW}[!] Operacion cancelada.{C_RESET}\n")
        return {"success": False, "error": "Cancelled"}

    rel_path = target.get('path', f"{target.get('group', '')}/{target['name']}").replace('/', os.sep)
    full_path = os.path.join(repos_dir, rel_path)

    # Si no esta clonado fisicamente, ofrecer clonarlo primero
    if not os.path.isdir(full_path):
        print(f"\n{C_YELLOW}[!] El repositorio {target.get('group')}/{target['name']} no esta clonado en este equipo.{C_RESET}")
        url = target.get('url')
        if not url:
            print(f"{C_RED}[ERROR] No hay URL registrada en el catalogo para clonarlo.{C_RESET}\n")
            return {"success": False, "error": "No url"}
        try:
            ans = input(f"{C_BOLD}¿Deseas descargarlo y abrirlo en VS Code ahora? [S/n]: {C_RESET}").strip().lower()
        except EOFError:
            ans = 's'
        if ans in ['', 's', 'si', 'y', 'yes']:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            print(f"{C_MAGENTA}[CLONE] Clonando {target['name']}...{C_RESET}")
            res = subprocess.run(["git", "clone", url, full_path])
            if res.returncode != 0:
                print(f"{C_RED}[ERROR] No se pudo clonar el repositorio.{C_RESET}\n")
                return {"success": False, "error": "Clone failed"}
        else:
            return {"success": False, "error": "User skipped clone"}

    print(f"\n{C_GREEN}[OK] Abriendo en Visual Studio Code:{C_RESET} {target.get('group')}/{target['name']}")
    try:
        subprocess.Popen(['code', full_path], shell=(os.name == 'nt'))
        print("")
        return {"success": True, "path": full_path, "name": target['name']}
    except Exception as e:
        print(f"{C_RED}[ERROR] No se pudo iniciar 'code': {e}{C_RESET}\n")
        return {"success": False, "error": str(e)}

# ==============================================================================
# AUDITORIA Y DIAGNOSTICO PARALELO (MULTIHILO)
# ==============================================================================
def inspect_single_repo(entry, repos_dir, with_fetch=False):
    """Inspecciona el estado Git de un unico repositorio con una sola llamada optimizada"""
    name = entry['name']
    group = entry.get('group', 'General')
    rel_path = entry.get('path', f"{group}/{name}").replace('/', os.sep)
    full_path = os.path.join(repos_dir, rel_path)

    if not os.path.exists(full_path):
        return {
            "name": name, "group": group, "path": rel_path, "full_path": full_path,
            "status": "NOT_CLONED", "branch": "-", "dirty_count": 0, "ahead": 0,
            "behind": 0, "dirty_files": [], "url": entry.get("url", "")
        }

    git_dir = os.path.join(full_path, ".git")
    if not os.path.isdir(git_dir):
        return {
            "name": name, "group": group, "path": rel_path, "full_path": full_path,
            "status": "NO_GIT", "branch": "-", "dirty_count": 0, "ahead": 0,
            "behind": 0, "dirty_files": [], "url": entry.get("url", "")
        }

    if with_fetch:
        subprocess.run(["git", "fetch", "origin", "-q", "--prune"], cwd=full_path, stderr=subprocess.DEVNULL)

    status_out = run_cmd(["git", "status", "-b", "--porcelain"], cwd=full_path)
    lines = [l for l in status_out.splitlines() if l.strip()]

    branch = "(detached)"
    ahead = 0
    behind = 0
    is_local_only = False
    dirty_lines = []

    if lines and lines[0].startswith("## "):
        header = lines[0][3:].strip()
        dirty_lines = lines[1:]

        if "..." in header:
            parts = header.split("...", 1)
            branch = parts[0].strip()
            rest = parts[1].strip()
            if "[" in rest and "]" in rest:
                info_b = rest.split("[", 1)[1].split("]", 1)[0]
                m_ahead = re.search(r'ahead (\d+)', info_b)
                m_behind = re.search(r'behind (\d+)', info_b)
                if m_ahead:
                    ahead = int(m_ahead.group(1))
                if m_behind:
                    behind = int(m_behind.group(1))
        elif "HEAD" in header:
            branch = "(detached)"
        else:
            branch = header.split()[0]
            is_local_only = True
    else:
        dirty_lines = lines

    dirty_count = len(dirty_lines)

    # Clasificar estado
    if dirty_count > 0 and ahead > 0:
        status = "DIRTY_AND_AHEAD"
    elif dirty_count > 0:
        status = "DIRTY"
    elif is_local_only:
        status = "LOCAL_ONLY_BRANCH"
    elif ahead > 0 and behind > 0:
        status = "DIVERGED"
    elif ahead > 0:
        status = "AHEAD"
    elif behind > 0:
        status = "BEHIND"
    else:
        status = "CLEAN"

    return {
        "name": name,
        "group": group,
        "path": rel_path,
        "full_path": full_path,
        "status": status,
        "branch": branch,
        "dirty_count": dirty_count,
        "dirty_files": dirty_lines,
        "ahead": ahead,
        "behind": behind,
        "is_local_only": is_local_only,
        "url": entry.get("url", "")
    }

def audit_all_repos(repos_dir, catalog, with_fetch=False, max_workers=16, org_filter=None):
    """Audita los repositorios en paralelo ultra-rapido respetando filtros de organizacion"""
    t0 = time.time()
    scoped_catalog = catalog
    if org_filter:
        scoped_catalog = [c for c in catalog if c.get("group") in org_filter]

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(inspect_single_repo, entry, repos_dir, with_fetch) for entry in scoped_catalog]
        results = [f.result() for f in futures]
    duration = time.time() - t0

    clean_list       = [r for r in results if r["status"] == "CLEAN"]
    dirty_list       = [r for r in results if r["status"] in ["DIRTY", "DIRTY_AND_AHEAD"]]
    ahead_list       = [r for r in results if r["status"] in ["AHEAD", "DIRTY_AND_AHEAD"]]
    behind_list      = [r for r in results if r["status"] == "BEHIND"]
    local_only_list  = [r for r in results if r["status"] == "LOCAL_ONLY_BRANCH"]
    diverged_list    = [r for r in results if r["status"] == "DIVERGED"]
    not_cloned_list  = [r for r in results if r["status"] == "NOT_CLONED"]

    total = len(results)
    health_score = max(0.0, min(100.0, ((total - len(dirty_list) - len(ahead_list) - len(behind_list) - len(local_only_list)) / max(1, total)) * 100))

    return {
        "total": total,
        "health_score": round(health_score, 1),
        "duration": round(duration, 2),
        "with_fetch": with_fetch,
        "clean": clean_list,
        "dirty": dirty_list,
        "ahead": ahead_list,
        "behind": behind_list,
        "local_only": local_only_list,
        "diverged": diverged_list,
        "not_cloned": not_cloned_list,
        "all_results": results
    }

def print_health_report(audit, verbose=False):
    """Imprime un reporte visual y conciso del estado de salud"""
    score = audit["health_score"]
    color = C_GREEN if score >= 95 else (C_YELLOW if score >= 75 else C_RED)

    print(f"\n{C_BOLD}+--------------------------------------------------------+{C_RESET}")
    print(f"{C_BOLD}|  Indice de Salud del Ecosistema: {color}{score}%{C_RESET} ({audit['duration']}s){C_BOLD}        |{C_RESET}")
    print(f"{C_BOLD}+--------------------------------------------------------+{C_RESET}")
    print(f"  * {C_GREEN}Al dia y limpios:{C_RESET} {len(audit['clean'])} / {audit['total']}")

    if audit['dirty']:
        print(f"  * {C_YELLOW}Con cambios locales ({len(audit['dirty'])}):{C_RESET}")
        for r in audit['dirty']:
            f_preview = r['dirty_files'][:2]
            f_str = ", ".join([f.split()[-1] for f in f_preview])
            extra = f" (+{len(r['dirty_files'])-2} mas)" if len(r['dirty_files']) > 2 else ""
            print(f"      - {C_BOLD}{r['group']}/{r['name']}{C_RESET}: {C_YELLOW}{len(r['dirty_files'])} modif.{C_RESET} ({f_str}{extra})")

    if audit['ahead']:
        print(f"  * {C_CYAN}Commits pendientes de push ({len(audit['ahead'])}):{C_RESET}")
        for r in audit['ahead']:
            print(f"      - {C_BOLD}{r['group']}/{r['name']}{C_RESET} [{r['branch']}]: {C_CYAN}{r['ahead']} commit(s) adelante{C_RESET}")

    if audit['behind']:
        print(f"  * {C_MAGENTA}Actualizaciones en GitHub disponibles ({len(audit['behind'])}):{C_RESET}")
        for r in audit['behind']:
            print(f"      - {C_BOLD}{r['group']}/{r['name']}{C_RESET}: {C_MAGENTA}{r['behind']} commit(s) atras{C_RESET}")

    if audit['local_only']:
        print(f"  * {C_RED}Ramas solo locales sin upstream ({len(audit['local_only'])}):{C_RESET}")
        for r in audit['local_only']:
            print(f"      - {C_BOLD}{r['group']}/{r['name']}{C_RESET} (rama: {r['branch']})")

    if audit['not_cloned']:
        print(f"  * {C_RED}No clonados ({len(audit['not_cloned'])}):{C_RESET}")
        for r in audit['not_cloned']:
            print(f"      - {r['group']}/{r['name']}")

    if not audit['dirty'] and not audit['ahead'] and not audit['behind'] and not audit['local_only'] and not audit['not_cloned']:
        print(f"\n  {C_GREEN}[OK] Ecosistema impecable! Puedes cambiar de equipo con 100% de confianza.{C_RESET}")
    print("")

# ==============================================================================
# HIGIENE Y LIMPIEZA DE ARCHIVOS BASURA (.firebase, logs, .DS_Store, etc.)
# ==============================================================================
def clean_repo_hygiene(repos_dir, catalog, target_repo="all"):
    """
    Detecta archivos de cache/logs (.firebase, logs, etc.) en repositorios,
    los elimina del seguimiento de Git y agrega las reglas a su .gitignore.
    """
    print(f"\n{C_CYAN}[*] Iniciando escaneo de higiene y archivos no deseados...{C_RESET}")
    audit = audit_all_repos(repos_dir, catalog, with_fetch=False)

    dirty_repos = audit["dirty"]
    if target_repo != "all":
        dirty_repos = [r for r in dirty_repos if r["name"].lower() == target_repo.lower()]

    if not dirty_repos:
        print(f"{C_GREEN}[OK] No hay repositorios con archivos que requieran limpieza.{C_RESET}\n")
        return {"cleaned": []}

    cleaned_actions = []

    for r in dirty_repos:
        repo_path = r["full_path"]
        dirty_files = r["dirty_files"]

        junk_found = []
        for line in dirty_files:
            file_name = line.strip().split()[-1]
            for pat in JUNK_PATTERNS:
                if pat in file_name:
                    junk_found.append((pat, file_name))
                    break

        if not junk_found:
            continue

        print(f"\n  {C_BOLD}Reparando higiene en:{C_RESET} {C_YELLOW}{r['group']}/{r['name']}{C_RESET}")
        patterns_to_ignore = set()

        for pat, fname in junk_found:
            if pat == ".firebase":
                patterns_to_ignore.add(".firebase/")
                run_cmd(["git", "rm", "-r", "--cached", ".firebase"], cwd=repo_path)
            elif pat in [".DS_Store", "Thumbs.db"]:
                patterns_to_ignore.add(pat)
                run_cmd(["git", "rm", "--cached", fname], cwd=repo_path)
            elif "log" in pat:
                patterns_to_ignore.add("*.log")
                run_cmd(["git", "rm", "--cached", fname], cwd=repo_path)
            elif pat == ".vscode":
                patterns_to_ignore.add(".vscode/")

        gi_file = os.path.join(repo_path, ".gitignore")
        existing_gi = []
        if os.path.isfile(gi_file):
            try:
                with open(gi_file, "r", encoding="utf-8") as gf:
                    existing_gi = [l.strip() for l in gf.readlines()]
            except Exception:
                pass

        added_to_gi = []
        for pat in patterns_to_ignore:
            if pat not in existing_gi and pat.rstrip('/') not in existing_gi:
                added_to_gi.append(pat)

        if added_to_gi:
            try:
                with open(gi_file, "a", encoding="utf-8") as gf:
                    gf.write("\n# Reglas agregadas automaticamente por GitDoctor\n")
                    for p in added_to_gi:
                        gf.write(f"{p}\n")
                print(f"    {C_GREEN}[+] Agregado a .gitignore:{C_RESET} {', '.join(added_to_gi)}")
            except Exception as e:
                print(f"    {C_RED}[!] Error actualizando .gitignore:{C_RESET} {e}")

        status_after = run_cmd(["git", "status", "--porcelain"], cwd=repo_path)
        has_staged = False
        for line in status_after.splitlines():
            if line.startswith("D ") or line.startswith("M ") or line.startswith("A "):
                has_staged = True
                break

        if has_staged or added_to_gi:
            run_cmd(["git", "add", ".gitignore"], cwd=repo_path)
            commit_msg = f"chore: ignore build/cache files ({', '.join(patterns_to_ignore)})\n\n{COPILOT_TRAILER}"
            res = run_cmd(["git", "commit", "-m", commit_msg], cwd=repo_path)
            if res:
                print(f"    {C_GREEN}[OK] Commit de limpieza registrado.{C_RESET}")

        cleaned_actions.append({
            "repo": f"{r['group']}/{r['name']}",
            "patterns": list(patterns_to_ignore),
            "added_to_gitignore": added_to_gi
        })

    print(f"\n{C_GREEN}[OK] Limpieza de higiene completada en {len(cleaned_actions)} repositorio(s).{C_RESET}\n")
    return {"cleaned": cleaned_actions}

# ==============================================================================
# GESTOR DE ESPACIO EN DISCO Y PRUNE (/disco /prune)
# ==============================================================================
def check_and_prune_disk(repos_dir, catalog, auto_prune=False):
    """Calcula el uso de disco de dependencias/builds y permite liberarlo"""
    print(f"\n{C_CYAN}[*] Analizando uso de espacio en disco en {repos_dir}...{C_RESET}")

    total_bytes = 0
    prunable_items = []

    for root, dirs, files in os.walk(repos_dir):
        if any(root.startswith(os.path.join(repos_dir, d)) for d in ["_gitdoctor", "_sync", "gitdoctor", "repos-sync"]):
            continue

        for d in list(dirs):
            if d in PRUNABLE_FOLDERS:
                full_d = os.path.join(root, d)
                d_size = 0
                try:
                    for sroot, sdirs, sfiles in os.walk(full_d):
                        for f in sfiles:
                            try:
                                d_size += os.path.getsize(os.path.join(sroot, f))
                            except Exception:
                                pass
                except Exception:
                    pass

                rel = os.path.relpath(full_d, repos_dir)
                prunable_items.append((rel, full_d, d_size, d))
                dirs.remove(d)

    total_prunable = sum([p[2] for p in prunable_items])
    mb_prunable = total_prunable / (1024 * 1024)
    gb_prunable = mb_prunable / 1024

    print(f"\n{C_BOLD}+--------------------------------------------------------+{C_RESET}")
    print(f"{C_BOLD}|  Analisis de Espacio en Disco (Carpetas Regenerables)  |{C_RESET}")
    print(f"{C_BOLD}+--------------------------------------------------------+{C_RESET}")
    print(f"  * Carpetas detectadas: {len(prunable_items)}")
    print(f"  * Espacio recuperable: {C_YELLOW}{gb_prunable:.2f} GB ({mb_prunable:.1f} MB){C_RESET}")

    if prunable_items:
        # Agrupar por tipo
        by_type = {}
        for rel, fd, sz, tp in prunable_items:
            by_type[tp] = by_type.get(tp, 0) + sz

        print(f"\n  {C_BOLD}Desglose por tipo de carpeta:{C_RESET}")
        for tp, sz in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            print(f"    - {tp:<15}: {sz / (1024*1024):.1f} MB")

        print(f"\n{C_GRAY}(Estas carpetas son recreadas al correr npm install / pip install / build){C_RESET}")

        ans = "s" if auto_prune else ""
        if not auto_prune:
            try:
                ans = input(f"\n{C_BOLD}¿Deseas purgar estas carpetas para liberar {gb_prunable:.2f} GB? [s/N]: {C_RESET}").strip().lower()
            except EOFError:
                ans = "n"

        if ans in ["s", "si", "y", "yes"]:
            import shutil
            freed = 0
            for rel, fd, sz, tp in prunable_items:
                try:
                    shutil.rmtree(fd, ignore_errors=True)
                    freed += sz
                except Exception:
                    pass
            print(f"\n{C_GREEN}[OK] ¡Limpieza completada! Se liberaron {freed / (1024*1024*1024):.2f} GB de disco.{C_RESET}\n")
            return {"freed_bytes": freed, "freed_gb": round(freed / (1024*1024*1024), 2)}
        else:
            print(f"{C_GRAY}No se realizaron cambios en el disco.{C_RESET}\n")
            return {"freed_bytes": 0}
    else:
        print(f"\n{C_GREEN}[OK] Tu disco esta totalmente optimizado. No hay carpetas pesadas para purgar.{C_RESET}\n")
        return {"freed_bytes": 0}

# ==============================================================================
# AUDITORIA DE SEGURIDAD Y FUGA DE SECRETOS (API KEYS, .ENV, CERTIFICADOS)
# ==============================================================================
SECRET_PATTERNS = [
    (r'AIzaSy[0-9A-Za-z\-_]{33}', "Google / Gemini API Key"),
    (r'sk-[a-zA-Z0-9_-]{20,}', "OpenAI API Key"),
    (r'sk-proj-[a-zA-Z0-9_-]{20,}', "OpenAI Project Key"),
    (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
    (r'ghp_[0-9a-zA-Z]{36}', "GitHub Personal Access Token"),
    (r'github_pat_[0-9a-zA-Z_]{82}', "GitHub Fine-Grained Token")
]

DANGEROUS_EXTENSIONS = [".pem", ".key", ".pfx", ".pkcs12", ".cer"]

def scan_repo_secrets(repo_path, repo_name):
    """Escanea un repositorio en busca de claves de API, secretos y archivos .env expuestos"""
    findings = []

    # 1. Verificar si .env o archivos de entorno estan siendo rastreados por Git
    tracked_env = run_cmd(["git", "ls-files", ".env", ".env.local", ".env.production", ".env.staging"], cwd=repo_path)
    if tracked_env:
        for f in tracked_env.splitlines():
            findings.append({
                "repo": repo_name,
                "file": f.strip(),
                "type": "ENV_TRACKED_IN_GIT",
                "risk": "CRITICAL",
                "detail": f"Archivo '{f.strip()}' rastreado en Git. ¡Riesgo alto de filtracion a GitHub!"
            })

    # 2. Verificar si existe .env en disco que NO este en .gitignore
    gi_path = os.path.join(repo_path, ".gitignore")
    gi_content = ""
    if os.path.isfile(gi_path):
        try:
            with open(gi_path, "r", encoding="utf-8", errors="replace") as gf:
                gi_content = gf.read()
        except Exception:
            pass

    for env_name in [".env", ".env.local", ".env.production"]:
        env_full = os.path.join(repo_path, env_name)
        if os.path.isfile(env_full) and ".env" not in gi_content:
            findings.append({
                "repo": repo_name,
                "file": env_name,
                "type": "ENV_NOT_IN_GITIGNORE",
                "risk": "HIGH",
                "detail": f"Existe '{env_name}' en disco pero .gitignore no tiene regla para ignorarlo."
            })

    # 3. Verificar archivos de certificados o llaves privadas
    for root, dirs, files in os.walk(repo_path):
        if ".git" in dirs:
            dirs.remove(".git")
        if "node_modules" in dirs:
            dirs.remove("node_modules")
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in DANGEROUS_EXTENSIONS or f == "id_rsa" or (f.startswith("service-account") and f.endswith(".json")):
                rel_f = os.path.relpath(os.path.join(root, f), repo_path)
                is_in_git = run_cmd(["git", "ls-files", rel_f], cwd=repo_path)
                if is_in_git:
                    findings.append({
                        "repo": repo_name,
                        "file": rel_f,
                        "type": "CERT_KEY_TRACKED",
                        "risk": "CRITICAL",
                        "detail": f"Certificado/Llave privada '{rel_f}' rastreada por Git."
                    })

    # 4. Escanear cambios locales pendientes (staged o modified) por patrones de API Keys
    try:
        diff_text = run_cmd(["git", "diff", "HEAD"], cwd=repo_path)
        if not diff_text:
            diff_text = run_cmd(["git", "diff", "--cached"], cwd=repo_path)
        if diff_text:
            for pat, pat_name in SECRET_PATTERNS:
                matches = re.findall(pat, diff_text)
                if matches:
                    findings.append({
                        "repo": repo_name,
                        "file": "diff local",
                        "type": "API_KEY_IN_DIFF",
                        "risk": "CRITICAL",
                        "detail": f"Posible {pat_name} detectada en cambios locales pendientes."
                    })
    except Exception:
        pass

    return findings

# ==============================================================================
# AUDITORIA Y ESTRATEGIA DE RAMAS GITFLOW (/gitflow)
# ==============================================================================
def inspect_repo_gitflow(repo_path, repo_name):
    """Inspecciona si el repositorio tiene implementada la estrategia de ramas Gitflow (develop)"""
    git_dir = os.path.join(repo_path, ".git")
    if not os.path.isdir(git_dir):
        return None

    raw_branches = run_cmd(["git", "branch", "-a"], cwd=repo_path)
    branches = [b.strip().replace("* ", "") for b in raw_branches.splitlines() if b.strip()]

    has_local_develop = any(b == "develop" for b in branches)
    has_remote_develop = any("origin/develop" in b for b in branches)
    has_develop = has_local_develop or has_remote_develop

    # Identificar rama principal base
    base_branch = "main"
    if any(b == "main" or "origin/main" in b for b in branches):
        base_branch = "main"
    elif any(b == "master" or "origin/master" in b for b in branches):
        base_branch = "master"

    # Rama actual
    current_branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=repo_path)

    return {
        "repo": repo_name,
        "has_gitflow": has_develop,
        "has_local_develop": has_local_develop,
        "has_remote_develop": has_remote_develop,
        "base_branch": base_branch,
        "current_branch": current_branch,
        "is_on_main": current_branch in ["main", "master"]
    }

def implement_gitflow_on_repo(repo_path, repo_name, push_remote=False):
    """Crea la rama develop a partir de la rama principal e implementa Gitflow"""
    info = inspect_repo_gitflow(repo_path, repo_name)
    if not info:
        return {"success": False, "error": "No es un repositorio Git"}

    base_b = info["base_branch"]

    # Verificar si hay cambios sin guardar
    status = run_cmd(["git", "status", "--porcelain"], cwd=repo_path)
    if status:
        return {"success": False, "error": "El repositorio tiene cambios sin commit. Haz commit primero."}

    # Si no existe develop localmente, crearla desde base_b
    if not info["has_local_develop"]:
        if info["has_remote_develop"]:
            run_cmd(["git", "checkout", "-b", "develop", "origin/develop"], cwd=repo_path)
        else:
            run_cmd(["git", "checkout", base_b], cwd=repo_path)
            run_cmd(["git", "checkout", "-b", "develop"], cwd=repo_path)
    else:
        run_cmd(["git", "checkout", "develop"], cwd=repo_path)

    pushed = False
    if push_remote:
        res = subprocess.run(["git", "push", "-u", "origin", "develop"], cwd=repo_path, stderr=subprocess.DEVNULL)
        pushed = (res.returncode == 0)

    return {"success": True, "branch": "develop", "pushed": pushed}

def interactive_manage_gitflow(repos_dir, catalog, target_repo=None, org_filter=None):
    """Muestra y permite implementar la estrategia Gitflow en repositorios del ecosistema"""
    print(f"\n{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  GitDoctor -- Auditoria y Configuracion de Gitflow             {C_RESET}")
    print(f"{C_CYAN}=================================================================={C_RESET}\n")

    scoped_catalog = catalog
    if org_filter:
        scoped_catalog = [c for c in catalog if c.get("group") in org_filter]

    gitflow_ok = []
    gitflow_missing = []

    for entry in scoped_catalog:
        rel_p = entry.get('path', f"{entry.get('group', 'General')}/{entry['name']}").replace('/', os.sep)
        full_p = os.path.join(repos_dir, rel_p)
        if not os.path.isdir(full_p):
            continue

        gf_info = inspect_repo_gitflow(full_p, entry['name'])
        if not gf_info:
            continue

        entry_data = {"entry": entry, "full_path": full_p, "info": gf_info}
        if gf_info["has_gitflow"]:
            gitflow_ok.append(entry_data)
        else:
            gitflow_missing.append(entry_data)

    print(f"{C_BOLD}Estado de Gitflow en tus repositorios clonados:{C_RESET}")
    print(f"  * {C_GREEN}Con Gitflow activo (rama 'develop'):{C_RESET} {len(gitflow_ok)}")
    print(f"  * {C_YELLOW}Sin Gitflow (solo rama '{gitflow_missing[0]['info']['base_branch'] if gitflow_missing else 'main'}'):{C_RESET} {len(gitflow_missing)}\n")

    if not gitflow_missing:
        print(f"{C_GREEN}[OK] ¡Excelente! Todos tus repositorios tienen implementada la rama 'develop'.{C_RESET}\n")
        return {"configured": 0}

    # Si se especifico un repositorio puntual
    if target_repo and target_repo.lower() != "all":
        candidates = [m for m in gitflow_missing if m["entry"]["name"].lower() == target_repo.lower()]
        if not candidates:
            print(f"{C_GRAY}El repositorio '{target_repo}' ya tiene Gitflow o no fue encontrado.{C_RESET}\n")
            return {"configured": 0}
        gitflow_missing = candidates

    print(f"{C_YELLOW}[!] Repositorios con flujo plano (sin rama develop):{C_RESET}")
    for idx, m in enumerate(gitflow_missing[:12], 1):
        print(f"  [{idx:2d}] {m['entry'].get('group')}/{m['entry']['name']} (rama base: {m['info']['base_branch']})")
    if len(gitflow_missing) > 12:
        print(f"  ... y {len(gitflow_missing)-12} mas")

    print(f"\n{C_GRAY}Tip de Buenas Practicas: Gitflow te permite desarrollar en 'develop' y reservar 'main' para produccion.{C_RESET}")
    try:
        ans = input(f"\n{C_BOLD}¿Deseas implementar Gitflow (crear rama 'develop') en estos repositorios? [S/n]: {C_RESET}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"

    if ans not in ["", "s", "si", "y", "yes"]:
        print(f"\n{C_GRAY}[*] Operacion omitida por el usuario.{C_RESET}\n")
        return {"configured": 0}

    try:
        push_ans = input(f"{C_BOLD}¿Deseas subir la rama 'develop' a GitHub (origin) al crearla? [s/N]: {C_RESET}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        push_ans = "n"
    do_push = push_ans in ["s", "si", "y", "yes"]

    configured_count = 0
    for m in gitflow_missing:
        name = m["entry"]["name"]
        print(f"  {C_CYAN}Configurando Gitflow en {m['entry'].get('group')}/{name}...{C_RESET}")
        res = implement_gitflow_on_repo(m["full_path"], name, push_remote=do_push)
        if res.get("success"):
            push_msg = " y subida a origin" if res.get("pushed") else " (local)"
            print(f"    {C_GREEN}[OK] Rama 'develop' creada{push_msg}.{C_RESET}")
            configured_count += 1
        else:
            print(f"    {C_RED}[!] No se pudo aplicar: {res.get('error')}{C_RESET}")

    print(f"\n{C_GREEN}[OK] Gitflow implementado en {configured_count} repositorio(s).{C_RESET}\n")
    return {"configured": configured_count}

# ==============================================================================
# AUDITORIA DE SALUD 360° (SECRETOS, GITFLOW, HIGIENE Y SINCRONIZACION)
# ==============================================================================
def audit_health_360(repos_dir, catalog, with_fetch=False, org_filter=None):
    """Ejecuta una auditoria completa y holistica de salud 360 grados del ecosistema"""
    print(f"\n{C_CYAN}=================================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  🛡️  GitDoctor: Auditoria Integral de Salud 360° (Seguridad, Gitflow e Higiene) {C_RESET}")
    print(f"{C_CYAN}=================================================================================={C_RESET}\n")

    # 1. Auditoria basica de sincronizacion Git
    audit = audit_all_repos(repos_dir, catalog, with_fetch=with_fetch, org_filter=org_filter)

    scoped_catalog = catalog
    if org_filter:
        scoped_catalog = [c for c in catalog if c.get("group") in org_filter]

    # 2. Escaneo de Secretos y Gitflow en repositorios clonados
    all_secrets = []
    gitflow_stats = {"with_develop": 0, "without_develop": 0, "on_main": 0}
    repos_without_gitflow = []

    for entry in scoped_catalog:
        rel_p = entry.get('path', f"{entry.get('group', 'General')}/{entry['name']}").replace('/', os.sep)
        full_p = os.path.join(repos_dir, rel_p)
        if not os.path.isdir(full_p):
            continue

        # Secretos
        sec_findings = scan_repo_secrets(full_p, entry['name'])
        if sec_findings:
            all_secrets.extend(sec_findings)

        # Gitflow
        gf = inspect_repo_gitflow(full_p, entry['name'])
        if gf:
            if gf["has_gitflow"]:
                gitflow_stats["with_develop"] += 1
                if gf["is_on_main"]:
                    gitflow_stats["on_main"] += 1
            else:
                gitflow_stats["without_develop"] += 1
                repos_without_gitflow.append(entry)

    # 3. Calculo de Score 360
    base_score = audit["health_score"]
    secret_penalty = min(30, len(all_secrets) * 10)
    gitflow_penalty = 10 if gitflow_stats["without_develop"] > 0 else 0
    score_360 = max(0.0, round(base_score - secret_penalty - gitflow_penalty, 1))

    color_score = C_GREEN if score_360 >= 90 else (C_YELLOW if score_360 >= 70 else C_RED)

    print(f"{C_BOLD}Indice Global de Salud 360°:{C_RESET} {color_score}{score_360}%{C_RESET}\n")

    # A) SEGURIDAD Y SECRETOS
    print(f"{C_BOLD}1. 🛡️  Seguridad y Fuga de Secretos:{C_RESET}")
    if all_secrets:
        print(f"  {C_RED}[!] Se detectaron {len(all_secrets)} posibles riesgos o secretos expuestos:{C_RESET}")
        for s in all_secrets:
            print(f"    * {C_BOLD}{s['repo']}{C_RESET}: {C_YELLOW}{s['detail']}{C_RESET}")
    else:
        print(f"  {C_GREEN}[OK] 0 secretos detectados.{C_RESET} Ningun archivo .env o llave privada filtrada en Git.")

    # B) GITFLOW
    print(f"\n{C_BOLD}2. 🌿 Estrategia de Ramas (Gitflow):{C_RESET}")
    print(f"  * Con rama 'develop' (Gitflow): {C_GREEN}{gitflow_stats['with_develop']}{C_RESET}")
    if gitflow_stats["without_develop"] > 0:
        print(f"  * {C_YELLOW}Con flujo plano (solo 'main'): {gitflow_stats['without_develop']} repositorios{C_RESET}")
    else:
        print(f"  * {C_GREEN}[OK] 100% de repositorios utilizan Gitflow.{C_RESET}")

    # C) HIGIENE Y BASURA
    print(f"\n{C_BOLD}3. 🧹 Higiene y Archivos de Compilacion:{C_RESET}")
    junk_count = len(audit["dirty"])
    if junk_count > 0:
        print(f"  * {C_YELLOW}{junk_count} repositorio(s) con cambios sin commit o archivos temporales.{C_RESET}")
    else:
        print(f"  * {C_GREEN}[OK] Limpieza total.{C_RESET} Sin archivos de compilacion o cache rastreados.")

    # D) SINCRONIZACION
    print(f"\n{C_BOLD}4. 🔄 Estado de Sincronizacion:{C_RESET}")
    print(f"  * Limpios y al dia: {C_GREEN}{len(audit['clean'])}{C_RESET} / {audit['total']}")
    if audit['ahead']:
        print(f"  * {C_CYAN}{len(audit['ahead'])} repositorio(s) con commits pendientes de subir a GitHub.{C_RESET}")
    if audit['behind']:
        print(f"  * {C_MAGENTA}{len(audit['behind'])} repositorio(s) con cambios por descargar de GitHub.{C_RESET}")

    print(f"\n{C_CYAN}=================================================================================={C_RESET}\n")

    # Oferta interactiva de correccion (siempre con decision del usuario)
    has_issues = bool(all_secrets or repos_without_gitflow or audit['dirty'] or audit['ahead'])
    if not has_issues:
        print(f"{C_GREEN}[OK] ¡Tu ecosistema tiene una salud de 10 estrellas! Todo en orden.{C_RESET}\n")
        return {"score": score_360, "all_secrets": all_secrets, "gitflow": gitflow_stats}

    try:
        opt_ans = input(f"{C_BOLD}¿Deseas que GitDoctor te ayude a optimizar las observaciones encontradas? [S/n]: {C_RESET}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        opt_ans = "n"

    if opt_ans in ["", "s", "si", "y", "yes"]:
        # Sub-paso 1: Corregir .env si no estan en .gitignore
        unignored_envs = [s for s in all_secrets if s["type"] == "ENV_NOT_IN_GITIGNORE"]
        if unignored_envs:
            try:
                env_ans = input(f"\n{C_BOLD}¿Deseas agregar '.env' a los .gitignore de los {len(unignored_envs)} proyectos afectados? [S/n]: {C_RESET}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                env_ans = "n"
            if env_ans in ["", "s", "si", "y", "yes"]:
                for s in unignored_envs:
                    for entry in scoped_catalog:
                        if entry['name'] == s['repo']:
                            rel_p = entry.get('path', f"{entry.get('group', 'General')}/{entry['name']}").replace('/', os.sep)
                            gi_file = os.path.join(repos_dir, rel_p, ".gitignore")
                            try:
                                with open(gi_file, "a", encoding="utf-8") as gf:
                                    gf.write("\n.env\n.env.*\n")
                                print(f"  {C_GREEN}[OK] .env agregado a .gitignore en {s['repo']}{C_RESET}")
                            except Exception:
                                pass

        # Sub-paso 2: Gitflow
        if repos_without_gitflow:
            interactive_manage_gitflow(repos_dir, catalog, org_filter=org_filter)

        # Sub-paso 3: Higiene
        if audit['dirty']:
            clean_repo_hygiene(repos_dir, catalog, target_repo="all")

        # Sub-paso 4: Push si hay commits pendientes
        if audit['ahead']:
            try:
                push_ans = input(f"\n{C_BOLD}¿Deseas subir los commits pendientes ({len(audit['ahead'])} repos) a GitHub ahora? [S/n]: {C_RESET}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                push_ans = "n"
            if push_ans in ["", "s", "si", "y", "yes"]:
                push_ahead_repos(repos_dir, catalog, target_repo="all")

    print("")
    return {"score": score_360, "all_secrets": all_secrets, "gitflow": gitflow_stats}

# ==============================================================================
# COMMIT Y PUSH DIRECTO
# ==============================================================================
def commit_single_repo(repos_dir, catalog, repo_name, message):
    """Crea un commit con los cambios pendientes en un repositorio especifico"""
    match = None
    for entry in catalog:
        if entry["name"].lower() == repo_name.lower():
            match = entry
            break

    if not match:
        print(f"{C_RED}[ERROR] Repositorio '{repo_name}' no encontrado en repos.json.{C_RESET}\n")
        return {"success": False, "error": "Repo not found"}

    rel_path = match.get('path', f"{match.get('group', 'General')}/{match['name']}").replace('/', os.sep)
    full_path = os.path.join(repos_dir, rel_path)

    run_cmd(["git", "add", "."], cwd=full_path)
    full_msg = f"{message}\n\n{COPILOT_TRAILER}"
    res = run_cmd(["git", "commit", "-m", full_msg], cwd=full_path)

    if res:
        print(f"{C_GREEN}[OK] Commit creado en {match['name']}:{C_RESET} {message}")
        push_res = subprocess.run(["git", "push"], cwd=full_path, stderr=subprocess.DEVNULL)
        if push_res.returncode == 0:
            print(f"      {C_GREEN}[OK] Cambios subidos a GitHub.{C_RESET}\n")
            return {"success": True, "pushed": True}
        else:
            print(f"      {C_YELLOW}[!] Commit listo en local; push pendiente.{C_RESET}\n")
            return {"success": True, "pushed": False}
    else:
        print(f"{C_YELLOW}[INFO] No habia cambios pendientes para commitear en {match['name']}.{C_RESET}\n")
        return {"success": False, "error": "Nothing to commit"}

# ==============================================================================
# PULL Y CLONACION PARALELA / BAJO DEMANDA
# ==============================================================================
def sync_all_repos(repos_dir, catalog, auto_pull=True, auto_clone=True, org_filter=None):
    """Sincroniza y descarga actualizaciones en paralelo de forma segura"""
    print(f"\n{C_CYAN}[*] Iniciando sincronizacion paralela de repositorios...{C_RESET}")
    audit = audit_all_repos(repos_dir, catalog, with_fetch=True, org_filter=org_filter)

    cloned = []
    if auto_clone and audit["not_cloned"]:
        for item in audit["not_cloned"]:
            target = item["full_path"]
            os.makedirs(os.path.dirname(target), exist_ok=True)
            print(f"  {C_MAGENTA}[CLONE] Descargando {item['group']}/{item['name']}...{C_RESET}")
            res = subprocess.run(["git", "clone", item["url"], target])
            if res.returncode == 0:
                cloned.append(item["name"])

    pulled = []
    failed_pull = []

    def pull_one(r):
        if r["status"] == "BEHIND" and r["dirty_count"] == 0:
            res = subprocess.run(["git", "pull", "-q", "--ff-only"], cwd=r["full_path"], stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return (r["name"], True)
            return (r["name"], False)
        return None

    if auto_pull:
        candidates = [r for r in audit["behind"] if r["dirty_count"] == 0]
        with ThreadPoolExecutor(max_workers=16) as executor:
            res_list = list(executor.map(pull_one, candidates))
            for res in res_list:
                if res:
                    if res[1]:
                        pulled.append(res[0])
                    else:
                        failed_pull.append(res[0])

    print(f"\n{C_GREEN}[OK] Sincronizacion finalizada:{C_RESET}")
    print(f"  * Actualizados con pull: {len(pulled)}")
    if pulled:
        print(f"    ({', '.join(pulled[:6])}{'...' if len(pulled)>6 else ''})")
    if cloned:
        print(f"  * Nuevos clonados: {len(cloned)} ({', '.join(cloned)})")
    if failed_pull:
        print(f"  * {C_RED}Pull no pudo aplicarse (--ff-only no lineal) en:{C_RESET} {', '.join(failed_pull)}")
    print("")

    return {"pulled": pulled, "cloned": cloned, "failed": failed_pull}

def clone_specific_repo_or_org(repos_dir, catalog, target_query):
    """Clona un repositorio puntual o una organizacion entera bajo demanda"""
    if not target_query:
        print(f"\n{C_YELLOW}[?] No indicaste que repositorio u organizacion clonar.{C_RESET}")
        print(f"{C_GRAY}Tip: Escribe /disponibles para ver la lista de proyectos que faltan en este equipo.{C_RESET}")
        try:
            target_query = input(f"{C_BOLD}Nombre a descargar: {C_RESET}").strip()
        except EOFError:
            target_query = ""
        if not target_query:
            print(f"{C_GRAY}Operacion cancelada.{C_RESET}\n")
            return {"success": False, "error": "No target provided"}

    q = target_query.strip().lower()

    # 1. Comprobar si coincide con una organizacion entera
    org_matches = [c for c in catalog if c.get("group", "").lower() == q]
    if org_matches:
        missing_in_org = []
        for item in org_matches:
            target_p = os.path.join(repos_dir, item.get('path', f"{item['group']}/{item['name']}").replace('/', os.sep))
            if not os.path.isdir(target_p):
                missing_in_org.append((item, target_p))

        if not missing_in_org:
            print(f"\n{C_GREEN}[OK] Todos los repositorios de la organizacion '{target_query}' ya estan clonados localmente.{C_RESET}\n")
            return {"success": True, "already_cloned": True}

        print(f"\n{C_MAGENTA}Descargando {len(missing_in_org)} repositorios de '{target_query}'...{C_RESET}")
        cloned_count = 0
        for item, tp in missing_in_org:
            os.makedirs(os.path.dirname(tp), exist_ok=True)
            print(f"  * Clonando {item['name']}...")
            res = subprocess.run(["git", "clone", item['url'], tp])
            if res.returncode == 0:
                cloned_count += 1
        print(f"\n{C_GREEN}[OK] Descargados {cloned_count} repositorios de '{target_query}'.{C_RESET}\n")
        return {"success": True, "cloned": cloned_count}

    # 2. Comprobar si coincide con un repositorio puntual
    repo_matches = [c for c in catalog if q == c['name'].lower() or q in c['name'].lower()]
    if not repo_matches:
        print(f"\n{C_RED}[!] No se encontro ningun repositorio en repos.json que coincida con '{target_query}'.{C_RESET}\n")
        return {"success": False, "error": "Not found in catalog"}

    chosen = repo_matches[0]
    target_p = os.path.join(repos_dir, chosen.get('path', f"{chosen.get('group')}/{chosen['name']}").replace('/', os.sep))

    if os.path.isdir(target_p):
        print(f"\n{C_GREEN}[OK] El repositorio {chosen.get('group')}/{chosen['name']} ya existe en este equipo.{C_RESET}\n")
        return {"success": True, "already_exists": True}

    os.makedirs(os.path.dirname(target_p), exist_ok=True)
    print(f"\n{C_MAGENTA}[CLONE] Descargando {chosen.get('group')}/{chosen['name']} ({chosen['url']})...{C_RESET}")
    res = subprocess.run(["git", "clone", chosen['url'], target_p])
    if res.returncode == 0:
        print(f"{C_GREEN}[OK] Repositorio clonado exitosamente en: {target_p}{C_RESET}\n")
        return {"success": True, "path": target_p}
    else:
        print(f"{C_RED}[ERROR] No se pudo clonar el repositorio.{C_RESET}\n")
        return {"success": False, "error": "git clone failed"}

def list_available_uncloned_repos(repos_dir, catalog):
    """Muestra lista de repositorios disponibles que aun no se han clonado en esta maquina"""
    uncloned = []
    for item in catalog:
        rel = item.get('path', f"{item.get('group', 'General')}/{item['name']}").replace('/', os.sep)
        full = os.path.join(repos_dir, rel)
        if not os.path.isdir(full):
            uncloned.append(item)

    if not uncloned:
        print(f"\n{C_GREEN}[OK] Tienes todos los repositorios del catalogo ({len(catalog)}) descargados en este equipo.{C_RESET}\n")
        return []

    print(f"\n{C_BOLD}Repositorios disponibles en GitHub que aun no tienes en este equipo ({len(uncloned)}):{C_RESET}")
    by_grp = {}
    for item in uncloned:
        grp = item.get("group", "General")
        by_grp.setdefault(grp, []).append(item)

    for grp, items in sorted(by_grp.items()):
        print(f"  {C_CYAN}[{grp}]{C_RESET} ({len(items)} disponibles):")
        names = [i['name'] for i in items]
        print(f"    {', '.join(names[:10])}{'...' if len(names)>10 else ''}")

    print(f"\n{C_GRAY}Puedes clonar cualquiera con: {C_WHITE}/clone <nombre_repo_o_org>{C_RESET}\n")
    return uncloned

# ==============================================================================
# DETECCION DE REPOSITORIOS NUEVOS CREADOS POR COLEGAS EN GITHUB
# ==============================================================================
def check_for_new_remote_repos(repos_dir, catalog, catalog_file, gh_info, active_orgs, interactive=True):
    """
    Escanea las organizaciones compartidas en GitHub para detectar si un colega
    o el usuario creo un nuevo repositorio que aun no este en el catalogo ni en disco.
    Envia una notificacion nativa y ofrece clonarlo de inmediato.
    """
    if not gh_info or not gh_info.get('logged_in'):
        if interactive:
            print(f"\n{C_YELLOW}[!] Inicia sesion en GitHub con /login para escanear repositorios remotos.{C_RESET}\n")
        return {"new_repos": []}

    known_names = {c['name'].lower() for c in catalog}
    for o in active_orgs:
        o_path = os.path.join(repos_dir, o)
        if os.path.isdir(o_path):
            try:
                for sub in os.listdir(o_path):
                    known_names.add(sub.lower())
            except Exception:
                pass

    if interactive:
        print(f"\n{C_CYAN}[*] Consultando GitHub para detectar repositorios nuevos en {len(active_orgs)} organizaciones...{C_RESET}")

    new_found = []
    for org in active_orgs:
        try:
            if org == "Personal":
                cmd = ["gh", "repo", "list", "--limit", "100", "--json", "name,nameWithOwner,url,defaultBranchRef"]
            else:
                cmd = ["gh", "repo", "list", org, "--limit", "100", "--json", "name,nameWithOwner,url,defaultBranchRef"]

            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=12)
            if res.returncode == 0:
                repos = json.loads(res.stdout.decode('utf-8'))
                for r in repos:
                    r_name = r["name"]
                    if r_name.lower() not in known_names and r_name.lower() not in ["_sync", "repos-sync"]:
                        author_name = org
                        try:
                            c_cmd = ["gh", "api", f"repos/{r['nameWithOwner']}/commits?per_page=1", "--jq", ".[0].commit.author.name"]
                            c_res = subprocess.run(c_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
                            if c_res.returncode == 0:
                                parsed = c_res.stdout.decode('utf-8').strip()
                                if parsed:
                                    author_name = parsed
                        except Exception:
                            pass

                        new_found.append({
                            "name": r_name,
                            "group": org,
                            "url": r["url"],
                            "full_name": r.get("nameWithOwner", f"{org}/{r_name}"),
                            "defaultBranch": r.get("defaultBranchRef", {}).get("name") if r.get("defaultBranchRef") else "main",
                            "author": author_name
                        })
        except Exception:
            pass

    if not new_found:
        if interactive:
            print(f"{C_GREEN}[OK] No hay repositorios nuevos sin clonar en tus organizaciones compartidas.{C_RESET}\n")
        return {"new_repos": []}

    for item in new_found:
        author = item['author']
        r_name = item['name']
        org = item['group']
        msg_text = f"Oye, {author} agrego el repositorio '{r_name}' en '{org}'."

        send_os_notification("GitDoctor: Nuevo Repositorio", f"{msg_text} Deseas clonarlo?")

        print(f"\n{C_MAGENTA}+--------------------------------------------------------+{C_RESET}")
        print(f"{C_MAGENTA}|  NUEVO REPOSITORIO DETECTADO EN GITHUB                 |{C_RESET}")
        print(f"{C_MAGENTA}+--------------------------------------------------------+{C_RESET}")
        print(f"  * {C_BOLD}Repositorio:{C_RESET} {C_GREEN}{org}/{r_name}{C_RESET}")
        print(f"  * {C_BOLD}Agregado por:{C_RESET} {C_CYAN}{author}{C_RESET}")
        print(f"  * {C_BOLD}URL:{C_RESET}          {item['url']}\n")

        if interactive:
            try:
                ans = input(f"{C_BOLD}Oye, {author} agrego esto en '{org}'. Deseas clonarlo en tu equipo ahora? [S/n]: {C_RESET}").strip().lower()
            except EOFError:
                ans = "n"

            if ans in ["", "s", "si", "y", "yes"]:
                target_path = os.path.join(repos_dir, org, r_name)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                print(f"  {C_CYAN}Clonando en {org}/{r_name}...{C_RESET}")
                res = subprocess.run(["git", "clone", item["url"], target_path])
                if res.returncode == 0:
                    print(f"  {C_GREEN}[OK] Clonado exitosamente en: {target_path}{C_RESET}")
                    catalog.append({
                        "name": r_name,
                        "group": org,
                        "path": f"{org}/{r_name}",
                        "url": item["url"],
                        "defaultBranch": item["defaultBranch"] or "main"
                    })
                    with open(catalog_file, "w", encoding="utf-8") as f:
                        json.dump(catalog, f, indent=4, ensure_ascii=False)
                    print(f"  {C_GREEN}[OK] Registrado en el catalogo ({os.path.basename(catalog_file)}).{C_RESET}\n")
            else:
                print(f"  {C_GRAY}Omitido por ahora. Puedes clonarlo despues con /clone {r_name}.{C_RESET}\n")

    return {"new_repos": new_found}

# ==============================================================================
# PUSH ASISTIDO
# ==============================================================================
def push_ahead_repos(repos_dir, catalog, target_repo="all"):
    """Sube los commits locales pendientes en repositorios que van adelante"""
    audit = audit_all_repos(repos_dir, catalog, with_fetch=False)
    candidates = audit["ahead"]
    if target_repo != "all":
        candidates = [r for r in candidates if r["name"].lower() == target_repo.lower()]

    if not candidates:
        print(f"\n{C_GREEN}[OK] No hay commits pendientes de push hacia GitHub.{C_RESET}\n")
        return {"pushed": []}

    print(f"\n{C_YELLOW}[!] Repositorios con commits locales listos para subir a GitHub:{C_RESET}")
    for r in candidates:
        print(f"  * {C_BOLD}{r['group']}/{r['name']}{C_RESET} [{r['branch']}]: {r['ahead']} commit(s)")

    pushed = []
    for r in candidates:
        print(f"  {C_CYAN}Subiendo {r['group']}/{r['name']}...{C_RESET}")
        res = subprocess.run(["git", "push"], cwd=r["full_path"], stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if res.returncode == 0:
            print(f"    {C_GREEN}[OK] Subido exitosamente.{C_RESET}")
            pushed.append(r["name"])
        else:
            err = res.stderr.decode('utf-8', errors='ignore').strip()
            print(f"    {C_RED}[ERROR] No se pudo subir: {err}{C_RESET}")

    print("")
    return {"pushed": pushed}

# ==============================================================================
# PRE-FLIGHT CHECK / SALIDA SEGURA (/apagar /checkout)
# ==============================================================================
def safe_preflight_checkout(repos_dir, catalog):
    """Auditoria rapida antes de apagar el equipo o cambiar a Mac"""
    print(f"\n{C_CYAN}================================================================{C_RESET}")
    print(f"{C_CYAN}  Pre-Flight Check: Auditoria de Salida Segura                 {C_RESET}")
    print(f"{C_CYAN}================================================================{C_RESET}")
    print(f"{C_GRAY}Verificando que todo quede limpio y respaldado antes de cambiar de equipo...{C_RESET}")

    audit = audit_all_repos(repos_dir, catalog, with_fetch=False)
    dirty = audit["dirty"]
    ahead = audit["ahead"]

    if ahead:
        print(f"\n{C_YELLOW}[!] Tienes commits pendientes de subir en {len(ahead)} repositorio(s):{C_RESET}")
        for r in ahead:
            print(f"  * {r['group']}/{r['name']} ({r['ahead']} commits)")
        try:
            ans = input(f"\n{C_BOLD}¿Deseas subirlos todos a GitHub ahora mismo? [S/n]: {C_RESET}").strip().lower()
        except EOFError:
            ans = 's'
        if ans in ['', 's', 'si', 'y', 'yes']:
            push_ahead_repos(repos_dir, catalog, target_repo="all")

    if dirty:
        print(f"\n{C_YELLOW}[!] ATENCION: Dejaste cambios locales sin commit en {len(dirty)} repositorio(s):{C_RESET}")
        for r in dirty:
            print(f"  * {r['group']}/{r['name']} [{r['branch']}]: {len(r['dirty_files'])} archivos modificados")
        print(f"{C_GRAY}Consejo: Si son entregables importantes, haz commit antes de apagar.{C_RESET}\n")
    else:
        print(f"\n{C_GREEN}[OK] ¡Todo en orden y limpio! Puedes cambiar de equipo con 100% de confianza.{C_RESET}\n")

    return {"clean": (len(dirty) == 0 and len(ahead) == 0)}

# ==============================================================================
# MODO VIGILANTE (WATCHDOG CONTINUO CON NOTIFICACIONES NATIVAS)
# ==============================================================================
def start_watchdog_loop(repos_dir, catalog, interval_seconds=300, send_notifications=True, catalog_file=None, gh_info=None, active_orgs=None):
    """Monitorea continuamente el estado, detecta nuevos repos creados por colegas y envia notificaciones nativas de SO"""
    print(f"\n{C_MAGENTA}================================================================{C_RESET}")
    print(f"{C_MAGENTA}  GitDoctor Vigilante -- Monitoreo Activo (Notificaciones Nativas) {C_RESET}")
    print(f"{C_GRAY}  Intervalo de chequeo: cada {interval_seconds} segundos. Presiona Ctrl+C para pausar.{C_RESET}")
    print(f"{C_MAGENTA}================================================================{C_RESET}\n")

    # Notificacion inicial de arranque
    if send_notifications:
        send_os_notification("GitDoctor Vigilante", f"Monitoreo activado en {os.path.basename(repos_dir)} (cada {interval_seconds}s)")

    last_dirty_set = set()
    last_ahead_set = set()
    cycle_count = 0

    try:
        while True:
            now_str = datetime.now().strftime("%H:%M:%S")
            audit = audit_all_repos(repos_dir, catalog, with_fetch=False)

            current_dirty = {r["name"] for r in audit["dirty"]}
            current_ahead = {r["name"] for r in audit["ahead"]}

            if current_dirty != last_dirty_set or current_ahead != last_ahead_set:
                print(f"[{now_str}] {C_YELLOW}[!] Cambio de estado detectado:{C_RESET}")
                notif_parts = []

                if current_dirty:
                    d_list = ', '.join(sorted(current_dirty)[:3])
                    extra_d = f" (+{len(current_dirty)-3} mas)" if len(current_dirty) > 3 else ""
                    print(f"  * {C_YELLOW}Cambios sin commit ({len(current_dirty)}):{C_RESET} {d_list}{extra_d}")
                    notif_parts.append(f"{len(current_dirty)} repos con cambios sin commit ({d_list}{extra_d})")

                if current_ahead:
                    a_list = ', '.join(sorted(current_ahead)[:3])
                    extra_a = f" (+{len(current_ahead)-3} mas)" if len(current_ahead) > 3 else ""
                    print(f"  * {C_CYAN}Commits sin subir ({len(current_ahead)}):{C_RESET} {a_list}{extra_a}")
                    notif_parts.append(f"{len(current_ahead)} repos con commits por subir")

                if not current_dirty and not current_ahead:
                    print(f"  * {C_GREEN}Todos los repositorios estan limpios y respaldados.{C_RESET}")
                    if last_dirty_set or last_ahead_set:
                        notif_parts.append("Ecosistema 100% limpio y respaldado")

                # Enviar notificacion nativa del sistema operativo
                if send_notifications and notif_parts:
                    send_os_notification("GitDoctor Vigilante", " | ".join(notif_parts))

                last_dirty_set = current_dirty
                last_ahead_set = current_ahead
            else:
                print(f"[{now_str}] {C_GRAY}Monitoreo OK: Salud {audit['health_score']}% ({audit['total']} repos){C_RESET}")

            # Cada 3 ciclos (~15 min por defecto), chequear si algun colega creo un repo nuevo en GitHub
            cycle_count += 1
            if cycle_count % 3 == 0 and gh_info and gh_info.get('logged_in') and active_orgs and catalog_file:
                check_for_new_remote_repos(repos_dir, catalog, catalog_file, gh_info, active_orgs, interactive=False)

            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print(f"\n{C_YELLOW}[*] Modo Vigilante pausado. Volviendo al asistente.{C_RESET}\n")

# ==============================================================================
# TRIAGE CON GEMINI AI (CARPETAS NUEVAS O HUERFANAS)
# ==============================================================================
def triage_unclassified_folders(repos_dir, catalog, catalog_file, api_key, active_orgs):
    """Detecta carpetas sin clasificar y las asigna a una organizacion"""
    catalog_names = {c["name"] for c in catalog}
    unclassified = []

    for item in sorted(os.listdir(repos_dir)):
        if item in ["_gitdoctor", "_sync", "gitdoctor", "repos-sync"] or item.startswith("."):
            continue
        p = os.path.join(repos_dir, item)
        if not os.path.isdir(p):
            continue

        if item not in active_orgs:
            unclassified.append({
                "path": p, "current_location": "raiz", "folder_name": item
            })
        else:
            try:
                for sub in sorted(os.listdir(p)):
                    if sub.startswith("."):
                        continue
                    sub_p = os.path.join(p, sub)
                    if not os.path.isdir(sub_p):
                        continue
                    has_git = os.path.isdir(os.path.join(sub_p, ".git"))
                    remote = run_cmd(["git", "remote", "get-url", "origin"], cwd=sub_p) if has_git else ""

                    if (not has_git) or (not remote) or (sub not in catalog_names):
                        unclassified.append({
                            "path": sub_p, "current_location": f"{item}/{sub}",
                            "folder_name": sub, "parent_org": item, "has_git": has_git, "remote": remote
                        })
            except Exception:
                pass

    if not unclassified:
        print(f"{C_GREEN}[OK] Todo en orden: No se detectaron carpetas huerfanas ni proyectos sin respaldar.{C_RESET}\n")
        return {"unclassified": 0}

    print(f"\n{C_YELLOW}[!] Se detectaron {len(unclassified)} proyectos que requieren clasificacion:{C_RESET}")
    for item in unclassified:
        print(f"  * {item['current_location']}")
    print("")

    return {"unclassified": len(unclassified), "items": [i['current_location'] for i in unclassified]}

# ==============================================================================
# MOTOR CONVERSACIONAL CON GEMINI AI (FUNCTION CALLING REST API)
# ==============================================================================
def build_system_instruction(active_orgs, user_name=None):
    display_user = user_name or "tu equipo"
    return f"""
Eres GitDoctor AI, el Medico DevOps y Especialista Clinico Integral de repositorios de desarrollo de {display_user}.

MISION PRIMORDIAL CLINICA Y ANTIERRORES:
- Tu objetivo primordial es DIAGNOSTICAR Y CURAR el entorno Git: prevenir errores, blindar contra fuga de secretos y mantener las mejores practicas de la industria.
- Sé extremadamente comprensivo y tolerante con cualquier falta de ortografia, abreviatura, lenguaje coloquial o error tipografico.
- Si el usuario dice 'asme un comit', 'checame la salu', 'sube lo q falta', 'abreme el visual', 'sincronisame', 'purgame el disco', 'descarga el repo x', comprende de inmediato su intencion clinica y ejecuta la herramienta adecuada.
- Antes de acciones destructivas o cambios masivos, advierte claramente lo que hara para que el usuario no pierda trabajo.
- Si un repositorio esta en estado 'DIVERGED' o con conflictos, explicale con calma y en espanol sencillo como resolverlo sin perder codigo.

ARQUITECTURA DEL ENTORNO:
- Directorio de repositorios: D:\\Repos (Windows) y ~/Repos (macOS).
- Organizaciones Activas / Detectadas en este equipo: {json.dumps(active_orgs)}
- Soporte Multi-Usuario, Multi-Trabajo y Multi-Proveedor (GitHub, GitLab, Bitbucket, Azure DevOps).
- Catalogo maestro: _sync/repos.json.

TUS CAPACIDADES MEDIANTE HERRAMIENTAS:
1. `check_health`: Evalua la salud de todos los repositorios en paralelo.
2. `audit_360`: Realiza auditoria profunda de salud 360: seguridad (deteccion de API keys/secretos expuestos), Gitflow e higiene.
3. `manage_gitflow`: Audita o implementa la estrategia de ramas Gitflow (creando la rama develop) en repositorios.
4. `clean_hygiene`: Limpia archivos de cache y temporales no deseados (.firebase, logs, .DS_Store, .vscode).
5. `open_in_vscode`: Abre directamente cualquier repositorio en Visual Studio Code por nombre o palabra clave.
6. `clone_repo_or_org`: Descarga bajo demanda un repositorio especifico o una organizacion entera.
7. `check_disk_usage`: Analiza y purga carpetas pesadas regenerables (node_modules, .next, dist, etc.) para ahorrar disco.
8. `safe_checkout`: Auditoria pre-flight antes de apagar la maquina o cambiar a otro equipo.
9. `sync_all`: Descarga cambios pendientes de GitHub en paralelo con pull seguro (--ff-only).
10. `push_unpushed`: Sube a GitHub los commits locales pendientes.
11. `commit_repo`: Realiza commit y push de cambios en un repositorio especifico.
12. `get_github_status`: Consulta el usuario activo, cuentas conectadas y organizaciones de GitHub.
13. `github_login`: Inicia sesion en GitHub con GitHub CLI (gh auth login).
14. `github_switch_user`: Cambia entre cuentas de GitHub guardadas.
15. `set_git_identity`: Configura el nombre y correo de Git global (user.name y user.email).
16. `check_new_remote_repos`: Escanea GitHub para detectar si colegas agregaron repositorios nuevos y ofrece clonarlos.
17. `start_watchdog`: Activa el modo vigilante con notificaciones nativas del sistema operativo.
18. `run_onboarding`: Diagnostica y reorganiza carpetas existentes en la raiz hacia las 10 organizaciones oficiales.

REGLAS DE INTERACCION:
- Responde siempre de forma concisa, profesional, clara, cercana y en espanol con tono de Medico DevOps de cabecera.
- Apoya tanto al usuario principal como a cualquier colega que use la herramienta.
- Explica los resultados de manera sencilla y siempre sugiere el comando rapido para que el usuario aprenda.
- Nunca expongas tokens, claves ni URLs con datos sensibles.
"""

GEMINI_TOOLS = [
    {
        "functionDeclarations": [
            {
                "name": "check_health",
                "description": "Verifica el estado de salud y sincronizacion de los repositorios del ecosistema en paralelo.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "with_fetch": {
                            "type": "BOOLEAN",
                            "description": "Si es True, ejecuta git fetch antes de evaluar para detectar cambios remotos en GitHub."
                        }
                    }
                }
            },
            {
                "name": "open_in_vscode",
                "description": "Abre un repositorio de desarrollo directamente en Visual Studio Code.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "repo_name": {
                            "type": "STRING",
                            "description": "Nombre o termino de busqueda del repositorio a abrir"
                        }
                    },
                    "required": ["repo_name"]
                }
            },
            {
                "name": "clone_repo_or_org",
                "description": "Descarga bajo demanda un repositorio puntual o una organizacion entera que no este clonada en este equipo.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "target_name": {
                            "type": "STRING",
                            "description": "Nombre del repositorio o de la organizacion a clonar"
                        }
                    },
                    "required": ["target_name"]
                }
            },
            {
                "name": "manage_organizations",
                "description": "Permite ver, activar o desactivar organizaciones en este equipo para que solo vivan en GitHub y opcionalmente liberar espacio en disco.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {
                            "type": "STRING",
                            "enum": ["list", "enable", "disable"],
                            "description": "Accion a realizar: 'list' para ver estado, 'enable' para activar, 'disable' para desactivar en este equipo"
                        },
                        "org_name": {
                            "type": "STRING",
                            "description": "Nombre de la organizacion a activar o desactivar"
                        },
                        "remove_local_folder": {
                            "type": "BOOLEAN",
                            "description": "Si es True al desactivar, elimina la carpeta local del disco para liberar espacio (solo si esta 100% limpia y respaldada en GitHub)"
                        }
                    },
                    "required": ["action"]
                }
            },
            {
                "name": "check_disk_usage",
                "description": "Analiza carpetas pesadas regenerables (node_modules, .next, dist) y ofrece purgarlas para liberar espacio en disco.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "auto_prune": {
                            "type": "BOOLEAN",
                            "description": "Si es True, purga las carpetas pesadas encontradas"
                        }
                    }
                }
            },
            {
                "name": "safe_checkout",
                "description": "Ejecuta una revision rapida de seguridad antes de apagar el equipo o cambiar de maquina.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "clean_hygiene",
                "description": "Limpia archivos basura de cache o logs (como .firebase, logs, .DS_Store, .vscode) y actualiza .gitignore.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "target_repo": {
                            "type": "STRING",
                            "description": "Nombre especifico del repositorio a limpiar o 'all' para todos."
                        }
                    }
                }
            },
            {
                "name": "sync_all",
                "description": "Ejecuta sincronizacion de repositorios con pull seguro (--ff-only) y clonacion de faltantes en paralelo.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "auto_pull": {
                            "type": "BOOLEAN",
                            "description": "Descargar cambios remotos automaticamente"
                        }
                    }
                }
            },
            {
                "name": "push_unpushed",
                "description": "Sube a GitHub los commits locales pendientes en los repositorios que van adelante.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "target_repo": {
                            "type": "STRING",
                            "description": "Nombre del repositorio a subir o 'all' para todos."
                        }
                    }
                }
            },
            {
                "name": "commit_repo",
                "description": "Hace commit y push de cambios pendientes en un repositorio especifico.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "repo_name": {
                            "type": "STRING",
                            "description": "Nombre del repositorio a commitear"
                        },
                        "message": {
                            "type": "STRING",
                            "description": "Mensaje descriptivo del commit"
                        }
                    },
                    "required": ["repo_name", "message"]
                }
            },
            {
                "name": "get_github_status",
                "description": "Consulta el usuario activo, cuentas de GitHub conectadas, organizaciones disponibles y configuracion de Git.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "github_login",
                "description": "Inicia el flujo interactivo de inicio de sesion con GitHub CLI (gh auth login).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "github_switch_user",
                "description": "Cambia la cuenta activa de GitHub a otro usuario autenticado en la maquina.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "target_user": {
                            "type": "STRING",
                            "description": "Nombre del usuario de GitHub al que cambiar (opcional)"
                        }
                    }
                }
            },
            {
                "name": "set_git_identity",
                "description": "Configura el nombre y correo electronico global para los commits de Git.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "name": {
                            "type": "STRING",
                            "description": "Nombre completo para Git (user.name)"
                        },
                        "email": {
                            "type": "STRING",
                            "description": "Correo electronico para Git (user.email)"
                        }
                    },
                    "required": ["name", "email"]
                }
            },
            {
                "name": "check_new_remote_repos",
                "description": "Escanea las organizaciones de GitHub para detectar si colegas agregaron repositorios nuevos y ofrece clonarlos con notificacion.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "start_watchdog",
                "description": "Inicia el modo vigilante de monitoreo continuo con notificaciones nativas del sistema.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "interval_seconds": {
                            "type": "INTEGER",
                            "description": "Segundos entre chequeos (por defecto 300)"
                        }
                    }
                }
            },
            {
                "name": "audit_360",
                "description": "Auditoria de salud 360 grados: analiza estado Git, detecta fuga de API keys o secretos, valida Gitflow e higiene.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "with_fetch": {
                            "type": "BOOLEAN",
                            "description": "Si es True, consulta GitHub en tiempo real para cambios remotos"
                        }
                    }
                }
            },
            {
                "name": "manage_gitflow",
                "description": "Audita o implementa la estrategia de ramas Gitflow (creando la rama develop) en repositorios.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "target_repo": {
                            "type": "STRING",
                            "description": "Nombre de un repositorio especifico o 'all' para todos"
                        }
                    }
                }
            },
            {
                "name": "run_onboarding",
                "description": "Ejecuta el asistente interactivo de diagnostico y reorganizacion de proyectos sueltos hacia las organizaciones oficiales.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {}
                }
            },
            {
                "name": "manage_catalog_vault",
                "description": "Gestiona la Boveda Privada multi-equipo en GitHub Gist Secreto para sincronizar repos.local.json entre Windows y Mac de forma 100% privada y confidencial.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {
                            "type": "STRING",
                            "description": "Accion: 'push' (subir catalogo), 'pull' (descargar catalogo), 'status' (ver estado de la boveda)",
                            "enum": ["push", "pull", "status"]
                        },
                        "gist_id": {
                            "type": "STRING",
                            "description": "Opcional: ID del Gist secreto al hacer pull"
                        }
                    },
                    "required": ["action"]
                }
            }
        ]
    }
]

_CACHED_GEMINI_MODELS = []
_LAST_GEMINI_ERROR = ""

def discover_available_gemini_models(api_key):
    """Descubre dinamicamente los modelos soportados por la API key activa"""
    global _CACHED_GEMINI_MODELS, _LAST_GEMINI_ERROR
    if _CACHED_GEMINI_MODELS:
        return _CACHED_GEMINI_MODELS

    default_fallbacks = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite",
        "gemini-pro-latest"
    ]

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = []
            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    models.append(name)

            EXCLUDED_KEYWORDS = [
                "omni", "tts", "image", "transcribe", "embedding", "robotics",
                "banana", "lyria", "deep-research", "antigravity", "computer-use",
                "2.5", "aqa"
            ]
            valid_models = []
            for m in models:
                if any(bad in m.lower() for bad in EXCLUDED_KEYWORDS):
                    continue
                valid_models.append(m)

            flash_models = [m for m in valid_models if "flash" in m]
            pro_models = [m for m in valid_models if "pro" in m]

            prioritized = []
            for pref in ["gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]:
                if pref in flash_models and pref not in prioritized:
                    prioritized.append(pref)
            for m in flash_models:
                if m not in prioritized:
                    prioritized.append(m)
            for m in pro_models:
                if m not in prioritized:
                    prioritized.append(m)

            if prioritized:
                _CACHED_GEMINI_MODELS = prioritized
                return _CACHED_GEMINI_MODELS
    except urllib.error.HTTPError as e:
        _LAST_GEMINI_ERROR = f"HTTP {e.code}: {e.reason}"
    except Exception as e:
        _LAST_GEMINI_ERROR = str(e)

    _CACHED_GEMINI_MODELS = default_fallbacks
    return _CACHED_GEMINI_MODELS

def get_last_gemini_error():
    global _LAST_GEMINI_ERROR
    return _LAST_GEMINI_ERROR or "Verifica tu conexion o clave."

def call_gemini_api(api_key, conversation_history, system_instruction):
    """Llama a la API de Gemini de forma segura, dinamica y resiliente"""
    global _LAST_GEMINI_ERROR
    _LAST_GEMINI_ERROR = ""

    models = discover_available_gemini_models(api_key)
    payload = {
        "contents": conversation_history,
        "systemInstruction": {
            "parts": [{"text": system_instruction}]
        },
        "tools": GEMINI_TOOLS,
        "generationConfig": {
            "temperature": 0.3
        }
    }
    data_bytes = json.dumps(payload).encode("utf-8")

    last_err = ""
    for model in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                resp_json = json.loads(resp.read().decode("utf-8"))
                return resp_json
        except urllib.error.HTTPError as e:
            err_msg = ""
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                err_msg = err_data.get("error", {}).get("message", "")
            except Exception:
                pass
            last_err = f"HTTP {e.code} ({e.reason}): {err_msg}" if err_msg else f"HTTP {e.code} ({e.reason})"
            if e.code in (400, 401, 403) and ("API_KEY_INVALID" in err_msg or "API key not valid" in err_msg):
                _LAST_GEMINI_ERROR = "Tu API Key de Gemini es invalida o expiro. Configura una nueva con /set-key."
                return None
            if e.code == 429 or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                _LAST_GEMINI_ERROR = "RATE_LIMIT: Limite de peticiones por minuto alcanzado en Gemini AI (cuota temporal agotada)."
                return None
            continue
        except Exception as e:
            last_err = sanitize_error(str(e))
            continue

    _LAST_GEMINI_ERROR = last_err or "No se pudo comunicar con ningun modelo disponible de Gemini."
    return None

# ==============================================================================
# MOTOR MULTI-IA (OLLAMA LOCAL OFFLINE + GOOGLE GEMINI CLOUD)
# ==============================================================================
def probe_ollama_status(host="http://localhost:11434"):
    """Detecta en milisegundos si Ollama esta activo localmente y lista sus modelos"""
    try:
        req = urllib.request.Request(f"{host}/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            models = [m.get("name") for m in data.get("models", [])]
            return {"available": True, "models": models, "host": host}
    except Exception:
        return {"available": False, "models": [], "host": host}

def call_ollama_api(host, model, conversation_history, system_instruction):
    """Ejecuta inferencia con IA local y privada mediante Ollama (100% offline)"""
    url = f"{host}/api/chat"
    messages = [{"role": "system", "content": system_instruction}]

    for turn in conversation_history:
        role = turn.get("role", "user")
        if role == "model":
            role = "assistant"
        parts = turn.get("parts", [])
        text = ""
        for p in parts:
            if "text" in p:
                text += p["text"]
            elif "functionCall" in p:
                text += f"\n[Accion solicitada: {p['functionCall']['name']}({json.dumps(p['functionCall'].get('args', {}))})]\n"
            elif "functionResponse" in p:
                text += f"\n[Resultado de accion: {json.dumps(p['functionResponse'].get('response', {}))}]\n"
        if text:
            messages.append({"role": role, "content": text})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3}
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            msg = resp_data.get("message", {}).get("content", "")
            return {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": msg}]
                        }
                    }
                ]
            }
    except Exception as e:
        global _LAST_GEMINI_ERROR
        _LAST_GEMINI_ERROR = f"Error en Ollama ({host}, modelo '{model}'): {sanitize_error(e)}"
        return None

def call_ai_engine(api_key, conversation_history, system_instruction, local_cfg):
    """Enrutador de IA inteligente: despacha a Ollama Local o Gemini Cloud segun configuracion"""
    provider = local_cfg.get("ai_provider", "gemini")
    if provider == "ollama":
        host = local_cfg.get("ollama_host", "http://localhost:11434")
        model = local_cfg.get("ollama_model", "llama3.1")
        return call_ollama_api(host, model, conversation_history, system_instruction)
    else:
        return call_gemini_api(api_key, conversation_history, system_instruction)

def interactive_switch_ai(local_cfg, script_dir, target=None):
    """Permite consultar o cambiar el motor de IA entre Google Gemini y Ollama Local"""
    ollama_info = probe_ollama_status()
    current = local_cfg.get("ai_provider", "gemini")

    if target:
        t = target.lower().strip()
        if "ollama" in t or "local" in t:
            local_cfg["ai_provider"] = "ollama"
            parts = t.split(None, 1)
            if len(parts) > 1:
                local_cfg["ollama_model"] = parts[1]
            elif ollama_info["models"]:
                local_cfg["ollama_model"] = ollama_info["models"][0]
            else:
                local_cfg["ollama_model"] = "llama3.1"
            save_local_config(script_dir, local_cfg)
            print(f"\n{C_GREEN}[OK] Motor de IA cambiado a: Ollama Local (Modelo: {local_cfg['ollama_model']}){C_RESET}\n")
            return local_cfg
        elif "gemini" in t or "cloud" in t:
            local_cfg["ai_provider"] = "gemini"
            save_local_config(script_dir, local_cfg)
            print(f"\n{C_GREEN}[OK] Motor de IA cambiado a: Google Gemini Cloud.{C_RESET}\n")
            return local_cfg

    print(f"\n{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  GitDoctor -- Configuracion de Motor de Inteligencia Artificial {C_RESET}")
    print(f"{C_CYAN}=================================================================={C_RESET}\n")
    print(f"Motor actualmente activo: {C_BOLD}{C_GREEN}{current.upper()}{C_RESET}\n")

    print(f"Opciones disponibles:")
    print(f"  [1] Google Gemini Cloud (Gratuito con API Key en la nube)")
    status_ollama = f"{C_GREEN}[En ejecucion en localhost:11434]{C_RESET}" if ollama_info["available"] else f"{C_GRAY}[No detectado]{C_RESET}"
    models_str = f" - Modelos: {', '.join(ollama_info['models'][:3])}" if ollama_info["models"] else ""
    print(f"  [2] Ollama Local Offline {status_ollama}{models_str} (100% privado, sin limites)")

    try:
        ans = input(f"\n{C_BOLD}Selecciona motor [1/2] (Enter para mantener {current}): {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        ans = ""

    if ans == "1":
        local_cfg["ai_provider"] = "gemini"
        save_local_config(script_dir, local_cfg)
        print(f"\n{C_GREEN}[OK] Motor configurado: Google Gemini Cloud.{C_RESET}\n")
    elif ans == "2":
        local_cfg["ai_provider"] = "ollama"
        if ollama_info["models"]:
            print(f"\nModelos disponibles en tu Ollama:")
            for idx, m in enumerate(ollama_info["models"], 1):
                print(f"  [{idx}] {m}")
            try:
                m_ans = input(f"{C_BOLD}Elige modelo [1-{len(ollama_info['models'])}] (Enter para {ollama_info['models'][0]}): {C_RESET}").strip()
                if m_ans.isdigit() and 1 <= int(m_ans) <= len(ollama_info["models"]):
                    local_cfg["ollama_model"] = ollama_info["models"][int(m_ans)-1]
                else:
                    local_cfg["ollama_model"] = ollama_info["models"][0]
            except Exception:
                local_cfg["ollama_model"] = ollama_info["models"][0]
        else:
            local_cfg["ollama_model"] = "llama3.1"
            print(f"\n{C_YELLOW}[INFO] No se detectaron modelos descargados en Ollama. Puedes descargar uno con: ollama run llama3.1{C_RESET}")

        save_local_config(script_dir, local_cfg)
        print(f"\n{C_GREEN}[OK] Motor configurado: Ollama Local (Modelo: {local_cfg['ollama_model']}).{C_RESET}\n")

    return local_cfg

# ==============================================================================
# GESTION MULTI-TRABAJO Y MULTI-PROVEEDOR (GITHUB, GITLAB, AZURE, BITBUCKET)
# ==============================================================================
def detect_repo_provider(url):
    """Detecta el proveedor de alojamiento Git a partir de la URL remota"""
    if not url:
        return "Local"
    u = url.lower()
    if "github.com" in u:
        return "GitHub"
    elif "gitlab.com" in u or "gitlab" in u:
        return "GitLab"
    elif "bitbucket.org" in u:
        return "Bitbucket"
    elif "dev.azure.com" in u or "visualstudio.com" in u:
        return "Azure DevOps"
    return "Git Remoto"

def get_org_git_identities(repos_dir, catalog):
    """Obtiene el nombre y correo de Git configurado en cada organizacion"""
    org_identities = {}
    for entry in catalog:
        grp = entry.get('group', 'Personal')
        rel_p = entry.get('path', f"{grp}/{entry['name']}").replace('/', os.sep)
        full_p = os.path.join(repos_dir, rel_p)
        if grp not in org_identities and os.path.isdir(full_p):
            name = run_cmd(["git", "config", "--local", "user.name"], cwd=full_p)
            email = run_cmd(["git", "config", "--local", "user.email"], cwd=full_p)
            provider = detect_repo_provider(entry.get("url", ""))
            org_identities[grp] = {
                "user.name": name or "(heredado global)",
                "user.email": email or "(heredado global)",
                "provider": provider,
                "is_local": bool(name or email)
            }
    return org_identities

def set_org_git_identity(repos_dir, catalog, target_org, user_name, user_email):
    """Aplica una identidad de Git (nombre y correo) a todos los repos de una organizacion"""
    updated_count = 0
    for entry in catalog:
        if entry.get("group", "").lower() == target_org.lower():
            rel_p = entry.get('path', f"{entry.get('group')}/{entry['name']}").replace('/', os.sep)
            full_p = os.path.join(repos_dir, rel_p)
            if os.path.isdir(full_p):
                run_cmd(["git", "config", "--local", "user.name", user_name], cwd=full_p)
                run_cmd(["git", "config", "--local", "user.email", user_email], cwd=full_p)
                updated_count += 1
    return updated_count

def interactive_manage_profiles(repos_dir, catalog, local_cfg, script_dir):
    """Permite ver y configurar identidades de Git (user.name y user.email) por organizacion para multi-trabajo"""
    print(f"\n{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  GitDoctor -- Gestion Multi-Trabajo e Identidades Git          {C_RESET}")
    print(f"{C_CYAN}=================================================================={C_RESET}\n")

    identities = get_org_git_identities(repos_dir, catalog)
    if not identities:
        print(f"{C_YELLOW}[!] No se encontraron repositorios clonados para inspeccionar identidades.{C_RESET}\n")
        return

    print(f"{C_BOLD}Identidades de commit configuradas por organizacion:{C_RESET}")
    org_list = sorted(identities.keys())
    for idx, org in enumerate(org_list, 1):
        info = identities[org]
        status_tag = f"{C_GREEN}[Propia de org]{C_RESET}" if info["is_local"] else f"{C_GRAY}[Heredada global]{C_RESET}"
        print(f"  [{idx:2d}] {C_BOLD}{org:<14}{C_RESET} [{info['provider']}]: {info['user.name']} <{info['user.email']}> {status_tag}")

    print(f"\n{C_GRAY}Tip: Puedes asignar un correo corporativo para organizaciones de trabajo y tu correo personal para el resto.{C_RESET}")
    try:
        ans = input(f"\n{C_BOLD}¿Deseas configurar una identidad de trabajo para alguna organizacion? [s/N]: {C_RESET}").strip().lower()
    except (EOFError, KeyboardInterrupt):
        ans = "n"

    if ans not in ["s", "si", "y", "yes"]:
        print(f"{C_GRAY}Sin cambios en identidades.{C_RESET}\n")
        return

    try:
        chosen_idx = input(f"{C_BOLD}Numero de organizacion a configurar (1-{len(org_list)}): {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        chosen_idx = ""

    if not chosen_idx.isdigit() or not (1 <= int(chosen_idx) <= len(org_list)):
        print(f"{C_RED}[!] Opcion invalida.{C_RESET}\n")
        return

    chosen_org = org_list[int(chosen_idx) - 1]
    print(f"\n{C_CYAN}Configurando identidad para '{chosen_org}':{C_RESET}")
    try:
        new_name = input(f"{C_BOLD}Nombre completo para '{chosen_org}': {C_RESET}").strip()
        new_email = input(f"{C_BOLD}Correo electronico para '{chosen_org}': {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        new_name, new_email = "", ""

    if new_name and new_email:
        count = set_org_git_identity(repos_dir, catalog, chosen_org, new_name, new_email)
        print(f"\n{C_GREEN}[OK] Identidad aplicada a {count} repositorio(s) en '{chosen_org}':{C_RESET} {new_name} <{new_email}>\n")
    else:
        print(f"{C_YELLOW}[!] Datos incompletos. No se realizaron cambios.{C_RESET}\n")

def execute_tool_call(tool_name, args, repos_dir, catalog, catalog_file, api_key, active_orgs, local_cfg):
    """Ejecuta una herramienta solicitada por Gemini y devuelve el resultado"""
    print(f"\n{C_MAGENTA}⚙ [Accion de Agente]: {C_BOLD}{tool_name}{C_RESET} {json.dumps(args)}{C_RESET}")

    if tool_name == "check_health":
        with_fetch = args.get("with_fetch", False)
        org_filter = local_cfg.get("enabled_orgs") if local_cfg.get("disabled_orgs") else None
        audit = audit_all_repos(repos_dir, catalog, with_fetch=with_fetch, org_filter=org_filter)
        print_health_report(audit)
        return {
            "health_score": audit["health_score"],
            "total_repos": audit["total"],
            "dirty_repos": [r["name"] for r in audit["dirty"]],
            "ahead_repos": [r["name"] for r in audit["ahead"]],
            "behind_repos": [r["name"] for r in audit["behind"]],
            "duration": audit["duration"]
        }

    elif tool_name == "open_in_vscode":
        repo_name = args.get("repo_name", "")
        return open_repo_in_vscode(repos_dir, catalog, repo_name)

    elif tool_name == "manage_organizations":
        action = args.get("action", "list")
        org_name = args.get("org_name")
        rm_folder = args.get("remove_local_folder", False)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        all_orgs = get_active_orgs(repos_dir, get_github_status())
        return api_manage_organizations(repos_dir, catalog, local_cfg, script_dir, all_orgs, action, org_name, rm_folder)

    elif tool_name == "clone_repo_or_org":
        target = args.get("target_name", "")
        return clone_specific_repo_or_org(repos_dir, catalog, target)

    elif tool_name == "check_disk_usage":
        auto_prune = args.get("auto_prune", False)
        return check_and_prune_disk(repos_dir, catalog, auto_prune=auto_prune)

    elif tool_name == "safe_checkout":
        return safe_preflight_checkout(repos_dir, catalog)

    elif tool_name == "clean_hygiene":
        target = args.get("target_repo", "all")
        return clean_repo_hygiene(repos_dir, catalog, target_repo=target)

    elif tool_name == "sync_all":
        auto_pull = args.get("auto_pull", True)
        org_filter = local_cfg.get("enabled_orgs") if local_cfg.get("disabled_orgs") else None
        return sync_all_repos(repos_dir, catalog, auto_pull=auto_pull, auto_clone=True, org_filter=org_filter)

    elif tool_name == "push_unpushed":
        target = args.get("target_repo", "all")
        return push_ahead_repos(repos_dir, catalog, target_repo=target)

    elif tool_name == "commit_repo":
        repo_name = args.get("repo_name", "")
        msg = args.get("message", "chore: update repository files")
        return commit_single_repo(repos_dir, catalog, repo_name, msg)

    elif tool_name == "get_github_status":
        gh_info = get_github_status()
        print_github_profile(gh_info)
        return {
            "logged_in": gh_info["logged_in"],
            "user": gh_info["user"],
            "name": gh_info["name"],
            "accounts": gh_info["accounts"],
            "orgs": gh_info["orgs"]
        }

    elif tool_name == "github_login":
        return interactive_github_login()

    elif tool_name == "github_switch_user":
        target = args.get("target_user")
        return interactive_github_switch(target_user=target)

    elif tool_name == "set_git_identity":
        name = args.get("name")
        email = args.get("email")
        return interactive_git_identity(name=name, email=email)

    elif tool_name == "check_new_remote_repos":
        gh_info = get_github_status()
        return check_for_new_remote_repos(repos_dir, catalog, catalog_file, gh_info, active_orgs, interactive=True)

    elif tool_name == "prepare_public_repo":
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return prepare_for_public_repo(script_dir)

    elif tool_name == "toggle_sync_mode":
        mode = args.get("mode", "mirror")
        local_cfg["sync_mode"] = mode
        if mode == "mirror":
            local_cfg["disabled_orgs"] = []
        script_dir = os.path.dirname(os.path.abspath(__file__))
        save_local_config(script_dir, local_cfg)
        return {"success": True, "sync_mode": mode}

    elif tool_name == "start_watchdog":
        interval = args.get("interval_seconds", 300)
        start_watchdog_loop(repos_dir, catalog, interval_seconds=interval)
        return {"status": "watchdog_completed"}

    elif tool_name == "audit_360":
        with_fetch = args.get("with_fetch", False)
        org_filter = local_cfg.get("enabled_orgs") if local_cfg.get("disabled_orgs") else None
        return audit_health_360(repos_dir, catalog, with_fetch=with_fetch, org_filter=org_filter)

    elif tool_name == "manage_gitflow":
        target = args.get("target_repo")
        org_filter = local_cfg.get("enabled_orgs") if local_cfg.get("disabled_orgs") else None
        return interactive_manage_gitflow(repos_dir, catalog, target_repo=target, org_filter=org_filter)

    elif tool_name == "run_onboarding":
        if run_onboarding_assistant:
            return run_onboarding_assistant(repos_dir, interactive=True)
        return {"error": "Modulo onboarding no disponible"}

    elif tool_name == "manage_catalog_vault":
        act = args.get("action", "status")
        g_id = args.get("gist_id")
        gh_info = get_github_status()
        script_dir = os.path.dirname(os.path.abspath(__file__))
        return interactive_manage_catalog_vault(script_dir, local_cfg, gh_info, action=act, param=g_id, repos_dir=repos_dir)

    return {"error": f"Herramienta desconocida: {tool_name}"}

# ==============================================================================
# DESCUBRIMIENTO DE REPOSITORIOS Y CONFIGURACION DE CARPETA PERSONALIZADA
# ==============================================================================
def import_repos_from_github(script_dir, gh_info):
    """
    Importa automaticamente todos los repositorios a los que el usuario tiene acceso en GitHub
    y los guarda en repos.local.json (sin tocar ni alterar el repos.json principal).
    Ideal para que colegas configuren su propio catalogo en segundos.
    """
    if not gh_info['logged_in']:
        print(f"\n{C_YELLOW}[!] Debes iniciar sesion primero en GitHub con /login.{C_RESET}\n")
        return {"success": False, "error": "Not logged in"}

    user = gh_info['user']
    print(f"\n{C_CYAN}[*] Descubriendo repositorios accesibles en GitHub para @{user}...{C_RESET}")

    entries = []
    # 1. Repositorios personales
    try:
        cmd = ["gh", "repo", "list", "--limit", "300", "--json", "name,nameWithOwner,url,defaultBranchRef"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            user_repos = json.loads(res.stdout.decode('utf-8'))
            for r in user_repos:
                if r["name"].lower() in ["gitdoctor", "repos-sync"] or r.get("url", "").endswith("/gitdoctor.git"):
                    continue
                b = r.get("defaultBranchRef", {}).get("name") if r.get("defaultBranchRef") else "main"
                entries.append({
                    "name": r["name"],
                    "group": "Personal",
                    "path": f"Personal/{r['name']}",
                    "url": r["url"],
                    "defaultBranch": b or "main"
                })
    except Exception:
        pass

    # 2. Repositorios de cada organizacion
    for org in gh_info.get('orgs', []):
        print(f"  * Explorando organizacion: {org}...")
        try:
            cmd = ["gh", "repo", "list", org, "--limit", "300", "--json", "name,nameWithOwner,url,defaultBranchRef"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                org_repos = json.loads(res.stdout.decode('utf-8'))
                for r in org_repos:
                    if r["name"].lower() in ["gitdoctor", "repos-sync"] or r.get("url", "").endswith("/gitdoctor.git"):
                        continue
                    b = r.get("defaultBranchRef", {}).get("name") if r.get("defaultBranchRef") else "main"
                    entries.append({
                        "name": r["name"],
                        "group": org,
                        "path": f"{org}/{r['name']}",
                        "url": r["url"],
                        "defaultBranch": b or "main"
                    })
        except Exception:
            pass

    if not entries:
        print(f"\n{C_YELLOW}[!] No se encontraron repositorios o no se pudo consultar la API.{C_RESET}\n")
        return {"success": False, "count": 0}

    # Guardar en repos.local.json
    local_cat_path = os.path.join(script_dir, "repos.local.json")
    with open(local_cat_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=4, ensure_ascii=False)

    print(f"\n{C_GREEN}[OK] ¡Descubrimiento completado! Se registraron {len(entries)} repositorios en repos.local.json.{C_RESET}")
    print(f"{C_GRAY}Este archivo es local y privado (ignorado por Git) para que cada colega tenga su propio catalogo.{C_RESET}\n")
    return {"success": True, "count": len(entries)}

def resolve_repos_dir(script_dir, local_cfg=None):
    """Resuelve la carpeta raiz de repositorios con resiliencia y compatibilidad"""
    if local_cfg and local_cfg.get("repos_dir"):
        c_dir = local_cfg["repos_dir"].strip()
        if c_dir and os.path.isdir(c_dir):
            return os.path.abspath(c_dir)

    parent = os.path.abspath(os.path.join(script_dir, ".."))
    parent_name = os.path.basename(parent)
    known_orgs = set(DEFAULT_ORGS)
    if local_cfg:
        if local_cfg.get("enabled_orgs"):
            known_orgs.update(local_cfg["enabled_orgs"])
        if local_cfg.get("disabled_orgs"):
            known_orgs.update(local_cfg["disabled_orgs"])

    # Si GitDoctor fue clonado dentro de una organizacion (ej: Personal/gitdoctor), la raiz es el directorio superior
    if parent_name in known_orgs or parent_name.lower() in ["personal", "repos-sync"]:
        return os.path.abspath(os.path.join(parent, ".."))
    return parent

def set_custom_repos_dir(script_dir, local_cfg, new_dir=None):
    """Permite ver o cambiar la carpeta raiz de repositorios para este equipo"""
    cur_dir = resolve_repos_dir(script_dir, local_cfg)
    if not new_dir:
        print(f"\n{C_BOLD}Carpeta raiz de repositorios en este equipo:{C_RESET}")
        print(f"  * Ruta actual: {C_CYAN}{cur_dir}{C_RESET}\n")
        try:
            new_dir = input(f"{C_BOLD}Ingresa nueva ruta absoluta (o Enter para mantener la actual): {C_RESET}").strip()
        except EOFError:
            new_dir = ""

    if new_dir:
        abs_p = os.path.abspath(new_dir)
        os.makedirs(abs_p, exist_ok=True)
        local_cfg["repos_dir"] = abs_p
        save_local_config(script_dir, local_cfg)
        print(f"\n{C_GREEN}[OK] Carpeta raiz de repositorios actualizada a: {abs_p}{C_RESET}\n")
        return abs_p
    return cur_dir

def prepare_for_public_repo(script_dir):
    """
    Prepara el repositorio para hacerse publico en GitHub de forma 100% segura:
    1. Si repos.json tiene repos reales, los respalda en repos.local.json (ignorado por Git).
    2. Coloca repos.example.json como el nuevo repos.json publico.
    3. Verifica que .env, config.local.json y repos.local.json esten en .gitignore.
    4. Tus maquinas siguen funcionando exactamente igual con repos.local.json sin exponer nada en GitHub.
    """
    cat_master = os.path.join(script_dir, "repos.json")
    cat_local = os.path.join(script_dir, "repos.local.json")
    cat_example = os.path.join(script_dir, "repos.example.json")

    print(f"\n{C_CYAN}================================================================{C_RESET}")
    print(f"{C_CYAN}  Preparacion de Privacidad para Repositorio Publico            {C_RESET}")
    print(f"{C_CYAN}================================================================{C_RESET}")
    print(f"{C_GRAY}Esta accion protege tus repositorios privados para que puedas hacer publico{C_RESET}")
    print(f"{C_GRAY}el proyecto en GitHub sin exponer clientes, nombres de repos ni URLs privadas.{C_RESET}\n")

    ensure_env_in_gitignore(script_dir)

    import shutil
    if os.path.isfile(cat_master):
        if not os.path.isfile(cat_local):
            shutil.copyfile(cat_master, cat_local)
            print(f"  {C_GREEN}[OK] Tus repositorios privados se respaldaron en repos.local.json (ignorado por Git).{C_RESET}")
        else:
            print(f"  {C_GRAY}[INFO] Ya existe repos.local.json con tu catalogo privado.{C_RESET}")

    if os.path.isfile(cat_example):
        shutil.copyfile(cat_example, cat_master)
        print(f"  {C_GREEN}[OK] repos.json fue reemplazado con la plantilla generica (repos.example.json).{C_RESET}")
    else:
        sample = [
            {"name": "mi-proyecto-backend", "group": "mi-organizacion", "path": "mi-organizacion/mi-proyecto-backend", "url": "https://github.com/mi-organizacion/mi-proyecto-backend.git", "defaultBranch": "main"},
            {"name": "mi-libreria-personal", "group": "Personal", "path": "Personal/mi-libreria-personal", "url": "https://github.com/mi-usuario/mi-libreria-personal.git", "defaultBranch": "main"}
        ]
        with open(cat_master, "w", encoding="utf-8") as f:
            json.dump(sample, f, indent=4)
        print(f"  {C_GREEN}[OK] repos.json fue reemplazado con un catalogo generico de ejemplo.{C_RESET}")

    print(f"\n{C_BOLD}Estado de proteccion:{C_RESET}")
    print(f"  * {C_GREEN}Tus maquinas seguiran sincronizando tus repos reales{C_RESET} usando repos.local.json.")
    print(f"  * {C_GREEN}En GitHub solo se vera el archivo de ejemplo{C_RESET} repos.json.")
    print(f"  * {C_GREEN}Tus claves de API (.env) estan protegidas.{C_RESET}")
    print(f"\n{C_GREEN}[OK] ¡Listo! Ahora puedes cambiar la visibilidad de tu repositorio a PUBLICO con total seguridad.{C_RESET}\n")
    return {"success": True, "message": "Repositorio preparado y protegido para visibilidad publica."}

# ==============================================================================
# BOVEDA PRIVADA DE CATALOGO MULTI-EQUIPO (GITHUB GIST SECRETO)
# ==============================================================================
VAULT_GIST_DESC = "GitDoctor Private Catalog Vault"
VAULT_FILENAME = "repos.vault.json"

def find_existing_vault_gist():
    """Busca un Gist Secreto existente en la cuenta del usuario para el catalogo privado"""
    try:
        res = subprocess.run(["gh", "api", "/gists", "--paginate"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=12)
        if res.returncode == 0:
            gists = json.loads(res.stdout.decode('utf-8'))
            for g in gists:
                files = g.get("files", {})
                desc = g.get("description", "")
                if VAULT_FILENAME in files or desc == VAULT_GIST_DESC:
                    return g.get("id")
    except Exception:
        pass
    return None

def vault_get_configured_id(script_dir, local_cfg):
    """Obtiene el ID del Gist configurado en config.local.json o intenta autodescubrirlo"""
    gid = local_cfg.get("catalog_gist_id")
    if gid:
        return gid
    found = find_existing_vault_gist()
    if found:
        local_cfg["catalog_gist_id"] = found
        save_local_config(script_dir, local_cfg)
        return found
    return None

def build_catalog_from_local_folders(repos_dir):
    """Genera una lista de catalogo a partir de las carpetas locales de repositorios"""
    entries = []
    if not os.path.isdir(repos_dir):
        return entries
    try:
        raw_items = sorted(os.listdir(repos_dir))
    except Exception:
        raw_items = []

    for item in raw_items:
        if item in ["_gitdoctor", "_sync", "gitdoctor", "repos-sync"] or item.startswith('.'):
            continue
        p1 = os.path.join(repos_dir, item)
        if not os.path.isdir(p1):
            continue

        if os.path.isdir(os.path.join(p1, ".git")):
            remote = run_cmd(['git', 'remote', 'get-url', 'origin'], cwd=p1)
            b = run_cmd(['git', 'branch', '--show-current'], cwd=p1) or "main"
            entries.append({
                "name": item,
                "group": "Personal",
                "path": f"Personal/{item}",
                "url": remote or f"https://github.com/davidmmora/{item}.git",
                "defaultBranch": b
            })
        else:
            try:
                for sub in sorted(os.listdir(p1)):
                    if sub.startswith('.'):
                        continue
                    p2 = os.path.join(p1, sub)
                    if os.path.isdir(p2) and os.path.isdir(os.path.join(p2, ".git")):
                        remote = run_cmd(['git', 'remote', 'get-url', 'origin'], cwd=p2)
                        b = run_cmd(['git', 'branch', '--show-current'], cwd=p2) or "main"
                        entries.append({
                            "name": sub,
                            "group": item,
                            "path": f"{item}/{sub}",
                            "url": remote or f"https://github.com/{item}/{sub}.git",
                            "defaultBranch": b
                        })
            except Exception:
                pass
    return entries

def vault_push_catalog(script_dir, local_cfg, gh_info, repos_dir=None):
    """Sube el catalogo privado local (repos.local.json) a un GitHub Gist Secreto"""
    if not gh_info.get('logged_in'):
        print(f"\n{C_YELLOW}[!] Debes iniciar sesion primero en GitHub con /login.{C_RESET}\n")
        return {"success": False, "error": "Not logged in"}

    cat_local = os.path.join(script_dir, "repos.local.json")
    cat_master = os.path.join(script_dir, "repos.json")

    # Si repos.local.json no existe, intentar poblarlo desde los repos locales en disco
    if not os.path.isfile(cat_local):
        if repos_dir and os.path.isdir(repos_dir):
            local_scanned = build_catalog_from_local_folders(repos_dir)
            if local_scanned:
                print(f"\n{C_CYAN}[*] No existia repos.local.json, pero se detectaron {len(local_scanned)} repos locales en tu disco.{C_RESET}")
                try:
                    ans = input(f"{C_BOLD}¿Deseas generar repos.local.json con estos repositorios para la Boveda? [S/n]: {C_RESET}").strip().lower()
                except EOFError:
                    ans = "s"
                if ans in ["", "s", "si", "y", "yes"]:
                    with open(cat_local, "w", encoding="utf-8") as f:
                        json.dump(local_scanned, f, indent=4, ensure_ascii=False)
                    print(f"  {C_GREEN}[OK] repos.local.json generado con {len(local_scanned)} repos.{C_RESET}")

    target_file = cat_local if os.path.isfile(cat_local) else cat_master
    if not os.path.isfile(target_file):
        print(f"\n{C_RED}[ERROR] No se encontro ni repos.local.json ni repos.json para respaldar.{C_RESET}\n")
        return {"success": False, "error": "No catalog file"}

    try:
        with open(target_file, "r", encoding="utf-8-sig") as f:
            cat_data = json.load(f)
    except Exception as e:
        print(f"\n{C_RED}[ERROR] El archivo de catalogo esta dañado o no es JSON valido: {e}{C_RESET}\n")
        return {"success": False, "error": str(e)}

    # Validar que no sea solo el dummy de ejemplo
    dummy_names = {"mi-proyecto-backend", "mi-proyecto-frontend", "mi-libreria-utilidades"}
    real_repos = [r for r in cat_data if r.get("name") not in dummy_names]
    if not real_repos and len(cat_data) <= 3:
        print(f"\n{C_YELLOW}[!] Tu catalogo actual solo contiene la plantilla publica de ejemplo de GitDoctor.{C_RESET}")
        print(f"{C_GRAY}Tip: Puedes usar /importar-github para escanear tus organizaciones reales en GitHub.{C_RESET}\n")
        try:
            proceed = input(f"{C_BOLD}¿Deseas subir la plantilla de todos modos a la Boveda? [s/N]: {C_RESET}").strip().lower()
        except EOFError:
            proceed = "n"
        if proceed not in ["s", "si", "y", "yes"]:
            return {"success": False, "error": "Cancelled by user"}

    print(f"\n{C_CYAN}[*] Sincronizando catalogo con la Boveda Privada en GitHub Gist Secreto...{C_RESET}")
    gist_id = vault_get_configured_id(script_dir, local_cfg)

    if gist_id:
        print(f"  * Actualizando Boveda existente (Gist ID: {gist_id})...")
        cmd = ["gh", "gist", "edit", gist_id, "--filename", VAULT_FILENAME, target_file]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0:
            print(f"\n{C_GREEN}[OK] ¡Boveda Privada actualizada exitosamente!{C_RESET}")
            print(f"  * Repositorios respaldados: {C_BOLD}{len(cat_data)}{C_RESET}")
            print(f"  * ID de tu Boveda: {C_CYAN}{gist_id}{C_RESET}")
            print(f"  * Visibilidad: {C_GREEN}100% SECRETA / PRIVADA{C_RESET} (Inaccesible para terceros en GitHub)")
            print(f"{C_GRAY}Ahora puedes descargar este catalogo en tus otros equipos ejecutando '/catalogo pull'.{C_RESET}\n")
            return {"success": True, "gist_id": gist_id, "count": len(cat_data)}
        else:
            err = res.stderr.decode('utf-8', errors='ignore')
            print(f"  {C_YELLOW}[!] No se pudo editar el Gist {gist_id} ({err.strip()}). Creando nueva Boveda...{C_RESET}")

    # Si no existia o fallo la edicion, crear nuevo Gist Secreto
    cmd = ["gh", "gist", "create", "--desc", VAULT_GIST_DESC, "--filename", VAULT_FILENAME, target_file]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0:
        out = res.stdout.decode('utf-8', errors='ignore').strip()
        new_id = out.rstrip('/').split('/')[-1]
        local_cfg["catalog_gist_id"] = new_id
        save_local_config(script_dir, local_cfg)
        print(f"\n{C_GREEN}[OK] ¡Boveda Privada creada exitosamente en tu cuenta @{gh_info.get('user')}!{C_RESET}")
        print(f"  * Repositorios respaldados: {C_BOLD}{len(cat_data)}{C_RESET}")
        print(f"  * ID de tu Boveda: {C_CYAN}{new_id}{C_RESET}")
        print(f"  * Visibilidad: {C_GREEN}100% SECRETA / PRIVADA{C_RESET} (Solo tu cuenta @{gh_info.get('user')} tiene acceso)")
        print(f"{C_GRAY}Tu ID quedo guardado en config.local.json. En tu otro equipo solo escribe '/catalogo pull'.{C_RESET}\n")
        return {"success": True, "gist_id": new_id, "count": len(cat_data)}
    else:
        err = res.stderr.decode('utf-8', errors='ignore')
        print(f"\n{C_RED}[ERROR] No se pudo crear el Gist Secreto en GitHub: {err.strip()}{C_RESET}\n")
        return {"success": False, "error": err}

def fetch_vault_raw_json(gist_id):
    """Obtiene el JSON puro de la Boveda sin importar el nombre interno del archivo"""
    # 1. Probar via gh api
    try:
        cmd = ["gh", "api", f"/gists/{gist_id}"]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=12)
        if res.returncode == 0:
            gdata = json.loads(res.stdout.decode('utf-8'))
            files = gdata.get("files", {})
            for fname in ["repos.vault.json", "repos.local.json"]:
                if fname in files and files[fname].get("content"):
                    return files[fname]["content"]
            # Tomar el primer archivo que comience como lista JSON
            for fname, finfo in files.items():
                content = finfo.get("content", "")
                if content and content.strip().startswith("["):
                    return content
    except Exception:
        pass

    # 2. Probar con gh gist view especificando nombres comunes
    for fn in ["repos.local.json", "repos.vault.json"]:
        cmd = ["gh", "gist", "view", gist_id, "-f", fn]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10)
        if res.returncode == 0 and res.stdout:
            txt = res.stdout.decode('utf-8', errors='ignore').strip()
            if txt.startswith("["):
                return txt

    return None

def vault_pull_catalog(script_dir, local_cfg, gh_info, target_gist_id=None):
    """Descarga el catalogo privado desde el GitHub Gist Secreto y lo guarda en repos.local.json"""
    if not gh_info.get('logged_in'):
        print(f"\n{C_YELLOW}[!] Debes iniciar sesion primero en GitHub con /login.{C_RESET}\n")
        return {"success": False, "error": "Not logged in"}

    gist_id = target_gist_id or vault_get_configured_id(script_dir, local_cfg)

    if not gist_id:
        print(f"\n{C_YELLOW}[?] No se encontro ninguna Boveda vinculada en esta maquina.{C_RESET}")
        try:
            ans = input(f"{C_BOLD}Ingresa el ID o URL del Gist Secreto (o Enter para cancelar): {C_RESET}").strip()
        except EOFError:
            ans = ""
        if not ans:
            print(f"{C_GRAY}Tip: Ejecuta '/catalogo push' en tu equipo principal para subir el catalogo primero.{C_RESET}\n")
            return {"success": False, "error": "No gist id"}
        gist_id = ans.rstrip('/').split('/')[-1]

    print(f"\n{C_CYAN}[*] Descargando catalogo privado desde la Boveda Secreta ({gist_id})...{C_RESET}")

    raw_json = fetch_vault_raw_json(gist_id)
    if not raw_json:
        print(f"\n{C_RED}[ERROR] No se pudo leer el contenido de la Boveda {gist_id} desde GitHub.{C_RESET}\n")
        return {"success": False, "error": "Could not fetch vault content"}
    try:
        cat_data = json.loads(raw_json)
        if not isinstance(cat_data, list):
            raise ValueError("El formato del catalogo debe ser una lista JSON de repositorios.")
    except Exception as e:
        print(f"\n{C_RED}[ERROR] El contenido descargado no es un catalogo valido: {e}{C_RESET}\n")
        return {"success": False, "error": str(e)}

    cat_local = os.path.join(script_dir, "repos.local.json")
    if os.path.isfile(cat_local):
        import shutil
        shutil.copyfile(cat_local, cat_local + ".bak")

    with open(cat_local, "w", encoding="utf-8") as f:
        json.dump(cat_data, f, indent=4, ensure_ascii=False)

    local_cfg["catalog_gist_id"] = gist_id
    save_local_config(script_dir, local_cfg)

    orgs_found = set(r.get("group", "Otros") for r in cat_data)

    print(f"\n{C_GREEN}[OK] ¡Catalogo privado descargado y activado exitosamente!{C_RESET}")
    print(f"  * Archivo local: {C_BOLD}repos.local.json{C_RESET} (ignorado por Git, 100% confidencial)")
    print(f"  * Total repositorios: {C_BOLD}{len(cat_data)}{C_RESET}")
    print(f"  * Organizaciones: {C_CYAN}{', '.join(sorted(orgs_found))}{C_RESET}")
    print(f"{C_GRAY}Ahora puedes ejecutar '/sync' para clonar o poner al dia todos tus proyectos en este equipo.{C_RESET}\n")
    return {"success": True, "count": len(cat_data), "gist_id": gist_id}

def vault_show_status(script_dir, local_cfg, gh_info):
    """Muestra el estado de la Boveda Privada y del catalogo local"""
    cat_local = os.path.join(script_dir, "repos.local.json")
    cat_master = os.path.join(script_dir, "repos.json")

    has_local = os.path.isfile(cat_local)
    active_cat = cat_local if has_local else cat_master

    count = 0
    orgs = set()
    if os.path.isfile(active_cat):
        try:
            with open(active_cat, "r", encoding="utf-8-sig") as f:
                d = json.load(f)
                count = len(d)
                orgs = set(r.get("group", "Otros") for r in d)
        except Exception:
            pass

    gist_id = vault_get_configured_id(script_dir, local_cfg)

    print(f"\n{C_CYAN}================================================================{C_RESET}")
    print(f"{C_CYAN}  Boveda Privada de Catalogo Multi-Equipo (GitHub Gist Secreto) {C_RESET}")
    print(f"{C_CYAN}================================================================{C_RESET}")
    print(f"{C_BOLD}Catalogo Local en este equipo:{C_RESET}")
    if has_local:
        print(f"  * Archivo activo: {C_GREEN}repos.local.json{C_RESET} (Privado, protegido por .gitignore)")
    else:
        print(f"  * Archivo activo: {C_YELLOW}repos.json{C_RESET} (Plantilla publica de ejemplo)")
    print(f"  * Total repositorios: {C_BOLD}{count}{C_RESET}")
    print(f"  * Organizaciones: {C_GRAY}{', '.join(sorted(orgs)) or 'Ninguna'}{C_RESET}\n")

    print(f"{C_BOLD}Boveda Remota en GitHub (Gist Secreto):{C_RESET}")
    if gist_id:
        print(f"  * ID Boveda: {C_CYAN}{gist_id}{C_RESET} (Vinculada)")
        print(f"  * Cuenta: {C_GREEN}@{gh_info.get('user', 'desconocido')}{C_RESET}")
        print(f"  * Visibilidad: {C_GREEN}100% SECRETA / PRIVADA{C_RESET} (Solo tu sesion de GitHub CLI)")
    else:
        print(f"  * Estado: {C_YELLOW}[!] Ninguna Boveda vinculada aun en este equipo.{C_RESET}")
        print(f"  * Usa {C_WHITE}/catalogo push{C_RESET} para respaldar o {C_WHITE}/catalogo pull{C_RESET} para descargar.")

    print(f"\n{C_GRAY}Comandos directos:{C_RESET}")
    print(f"  * {C_WHITE}/catalogo push{C_RESET} : Sube tu repos.local.json a la Boveda Secreta")
    print(f"  * {C_WHITE}/catalogo pull{C_RESET} : Descarga el catalogo privado de la Boveda a esta maquina")
    print(f"  * {C_WHITE}/catalogo status{C_RESET} : Muestra este panel de estado\n")

def interactive_manage_catalog_vault(script_dir, local_cfg, gh_info, action=None, param=None, repos_dir=None):
    """Manejador interactivo o directo del comando /catalogo"""
    act = (action or "").strip().lower()
    if act in ["push", "subir", "guardar", "respaldar"]:
        return vault_push_catalog(script_dir, local_cfg, gh_info, repos_dir=repos_dir)
    elif act in ["pull", "bajar", "descargar", "sync", "sincronizar"]:
        return vault_pull_catalog(script_dir, local_cfg, gh_info, target_gist_id=param)
    elif act in ["status", "estado", "info"]:
        vault_show_status(script_dir, local_cfg, gh_info)
        return {"status": "shown"}
    else:
        vault_show_status(script_dir, local_cfg, gh_info)
        print(f"{C_BOLD}¿Que deseas hacer?{C_RESET}")
        print(f"  {C_WHITE}[1]{C_RESET} {C_GREEN}Subir catalogo local a la Boveda Privada (/catalogo push){C_RESET}")
        print(f"  {C_WHITE}[2]{C_RESET} {C_CYAN}Descargar catalogo de la Boveda Privada (/catalogo pull){C_RESET}")
        print(f"  {C_WHITE}[3]{C_RESET} {C_YELLOW}Auto-descubrir repositorios desde GitHub CLI (/importar-github){C_RESET}")
        print(f"  {C_WHITE}[Enter]{C_RESET} Salir")
        try:
            choice = input(f"\n{C_BOLD}Selecciona una opcion [1/2/3]: {C_RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            choice = ""
        if choice == "1":
            return vault_push_catalog(script_dir, local_cfg, gh_info, repos_dir=repos_dir)
        elif choice == "2":
            return vault_pull_catalog(script_dir, local_cfg, gh_info)
        elif choice == "3":
            return import_repos_from_github(script_dir, gh_info)
        return {"status": "cancelled"}

# ==============================================================================
# CATALOGO DE COMANDOS MANUALES (HELPME) Y REPOSO DE IA
# ==============================================================================
def print_helpme_commands():
    """Muestra el catalogo completo de comandos disponibles en GitDoctor"""
    print(f"\n{C_CYAN}=================================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  🛠️  HELPME: Catalogo Completo de Comandos Disponibles en GitDoctor            {C_RESET}")
    print(f"{C_GRAY}  Puedes usarlos con o sin barra '/' (ej: 'salud' o '/salud') si la IA no responde.{C_RESET}")
    print(f"{C_CYAN}=================================================================================={C_RESET}\n")

    print(f"{C_BOLD}{C_GREEN}🩺 DIAGNOSTICO Y SALUD DEL ECOSISTEMA:{C_RESET}")
    print(f"  * {C_WHITE}/salud{C_RESET} (o {C_WHITE}salud{C_RESET})          : Diagnostico ultrarrapido (~1s) del estado de todos los repos.")
    print(f"  * {C_WHITE}/salud fetch{C_RESET}              : Diagnostico completo consultando GitHub en tiempo real.")
    print(f"  * {C_WHITE}/salud 360{C_RESET} (o {C_WHITE}/seguridad{C_RESET})  : Auditoria integral de Salud 360° (Secretos, API keys, Gitflow e higiene).")
    print(f"  * {C_WHITE}/gitflow{C_RESET} [repo|all]       : Audita e implementa la estrategia Gitflow (creando rama develop).")
    print(f"  * {C_WHITE}/onboarding{C_RESET} (o {C_WHITE}organizar{C_RESET})  : Diagnostica y reorganiza carpetas existentes hacia las organizaciones oficiales.")
    print(f"  * {C_WHITE}/disco{C_RESET} (o {C_WHITE}disco{C_RESET})          : Analiza y purga node_modules/.next/dist para liberar GBs de disco.")
    print(f"  * {C_WHITE}/limpiar{C_RESET} [repo|all]       : Limpia basura (.firebase, logs, .DS_Store) y actualiza .gitignore.")
    print(f"  * {C_WHITE}/apagar{C_RESET} (o {C_WHITE}checkout{C_RESET})       : Auditoria pre-flight de salida segura antes de apagar o cambiar a Mac.\n")

    print(f"{C_BOLD}{C_CYAN}🔄 SINCRONIZACION Y GESTION DE CODIGO:{C_RESET}")
    print(f"  * {C_WHITE}/catalogo{C_RESET} [push|pull|status]: Gestiona tu Boveda Privada (Gist Secreto) para compartir repos entre Windows y Mac.")
    print(f"  * {C_WHITE}/sync{C_RESET} [org]               : Descarga cambios remotos en paralelo con pull lineal (--ff-only).")
    print(f"  * {C_WHITE}/push{C_RESET} [repo|all]          : Sube a GitHub los commits locales que van adelante.")
    print(f"  * {C_WHITE}/commit <repo> <msg>{C_RESET}       : Hace stage, commit y push de cambios pendientes con trailer oficial.")
    print(f"  * {C_WHITE}/clone <repo|org>{C_RESET}         : Descarga bajo demanda un repo o una organizacion entera a tu disco.")
    print(f"  * {C_WHITE}/disponibles{C_RESET}              : Muestra los repositorios del catalogo que no estan clonados aqui.")
    print(f"  * {C_WHITE}/nuevos{C_RESET}                   : Detecta repos nuevos creados en GitHub por colegas y ofrece clonarlos.\n")

    print(f"{C_BOLD}{C_MAGENTA}💻 DESARROLLO Y ORGANIZACIONES:{C_RESET}")
    print(f"  * {C_WHITE}/code <repo>{C_RESET}              : Abre cualquier proyecto al instante en Visual Studio Code.")
    print(f"  * {C_WHITE}/orgs{C_RESET}                     : Activa o desactiva organizaciones en esta maquina para ahorrar disco.")
    print(f"  * {C_WHITE}/modo{C_RESET}                     : Alterna entre Modo Espejo (100% repos) y Modo Selectivo.")
    print(f"  * {C_WHITE}/dir{C_RESET} [nueva_ruta]         : Consulta o cambia la carpeta raiz de repositorios (D:\\Repos o ~/Repos).\n")

    print(f"{C_BOLD}{C_YELLOW}👤 CUENTAS DE GITHUB, MULTI-TRABAJO Y SEGURIDAD:{C_RESET}")
    print(f"  * {C_WHITE}/github{C_RESET}                   : Muestra usuario activo, cuentas conectadas y organizaciones.")
    print(f"  * {C_WHITE}/perfiles{C_RESET}                 : Gestiona identidades de commit (nombre/correo) por organizacion (Multi-Trabajo).")
    print(f"  * {C_WHITE}/login{C_RESET}                    : Inicia sesion con GitHub CLI (gh auth login) con tu cuenta o la de un colega.")
    print(f"  * {C_WHITE}/switch{C_RESET} [usuario]         : Cambia entre multiples cuentas de GitHub guardadas.")
    print(f"  * {C_WHITE}/logout{C_RESET}                   : Cierra sesion de una cuenta en GitHub CLI.")
    print(f"  * {C_WHITE}/git-id{C_RESET} [nombre email]    : Configura nombre y correo global para los commits de Git.")
    print(f"  * {C_WHITE}/importar-github{C_RESET}          : Escanea tus organizaciones en GitHub y genera tu catalogo local privado.")
    print(f"  * {C_WHITE}/publico{C_RESET}                  : Protege tus repos privados para poder publicar GitDoctor en GitHub.\n")

    print(f"{C_BOLD}{C_WHITE}🛡️ INTELIGENCIA ARTIFICIAL Y SISTEMA:{C_RESET}")
    print(f"  * {C_WHITE}/ia{C_RESET} [ollama|gemini]       : Alterna entre IA Local Offline (Ollama) y Nube (Gemini Cloud).")
    print(f"  * {C_WHITE}/vigilante{C_RESET} [segundos]     : Monitoreo continuo en segundo plano con notificaciones nativas de SO.")
    print(f"  * {C_WHITE}/set-key{C_RESET}                  : Configura o actualiza tu Gemini API Key de forma segura.")
    print(f"  * {C_WHITE}/helpme{C_RESET} (o {C_WHITE}/ayuda{C_RESET})       : Muestra este catalogo completo de comandos.")
    print(f"  * {C_WHITE}/salir{C_RESET} (o {C_WHITE}exit{C_RESET})           : Cierra la consola de GitDoctor.\n")
    print(f"{C_GRAY}💡 Tip: Recuerda que el Motor Antierrores te permite escribir los comandos tal cual sin la barra '/' (ej: 'salud', 'sync', 'disco').{C_RESET}\n")

def run_cooldown_countdown(seconds=25):
    """Muestra un contador regresivo amigable y visual que se puede interrumpir con Ctrl+C o Enter"""
    print(f"\n{C_CYAN}================================================================{C_RESET}")
    print(f"{C_CYAN}  ⏳ Modo Espera / Reposo de IA                                  {C_RESET}")
    print(f"{C_CYAN}================================================================{C_RESET}")
    print(f"{C_GRAY}Tip: Puedes cerrar la terminal un rato con {C_WHITE}/salir{C_GRAY} y volver mas tarde,{C_RESET}")
    print(f"{C_GRAY}o esperar aqui mientras se restablece la cuota de la IA.{C_RESET}\n")
    print(f"{C_YELLOW}Iniciando cuenta regresiva ({seconds}s)... (Presiona Ctrl+C para omitir y escribir un comando){C_RESET}")
    try:
        for remaining in range(seconds, 0, -1):
            sys.stdout.write(f"\r{C_YELLOW}  ⏳ Reanudando en {remaining:2d}s...{C_RESET} {C_GRAY}(Ctrl+C para omitir y escribir un comando){C_RESET} ")
            sys.stdout.flush()
            time.sleep(1)
        print(f"\r{C_GREEN}  [OK] ¡Tiempo de espera completado! La IA deberia estar lista para reintentar.{C_RESET}      \n")
    except KeyboardInterrupt:
        print(f"\r{C_GRAY}  [*] Espera omitida por el usuario. Listo para ingresar comandos.{C_RESET}               \n")

# ==============================================================================
# MOTOR ANTIERRORES: RESOLUCION INTELIGENTE Y AUTOCORRECCION DIFUSA
# ==============================================================================
COMMAND_MAP = {
    "salud": "/salud",
    "status": "/salud",
    "estado": "/salud",
    "limpiar": "/limpiar",
    "clean": "/limpiar",
    "higiene": "/limpiar",
    "sync": "/sync",
    "sincronizar": "/sync",
    "pull": "/sync",
    "actualizar": "/sync",
    "push": "/push",
    "subir": "/push",
    "commit": "/commit",
    "guardar": "/commit",
    "code": "/code",
    "abrir": "/code",
    "vs": "/code",
    "vscode": "/code",
    "orgs": "/orgs",
    "organizaciones": "/orgs",
    "config-orgs": "/orgs",
    "clone": "/clone",
    "clonar": "/clone",
    "bajar": "/clone",
    "descargar": "/clone",
    "catalogo": "/catalogo",
    "boveda": "/catalogo",
    "vault": "/catalogo",
    "disponibles": "/disponibles",
    "faltantes": "/disponibles",
    "disco": "/disco",
    "prune": "/disco",
    "espacio": "/disco",
    "apagar": "/apagar",
    "checkout": "/apagar",
    "salida": "/apagar",
    "vigilante": "/vigilante",
    "watchdog": "/vigilante",
    "monitor": "/vigilante",
    "github": "/github",
    "gh": "/github",
    "perfil": "/github",
    "whoami": "/github",
    "login": "/login",
    "auth": "/login",
    "switch": "/switch",
    "cambiar-cuenta": "/switch",
    "logout": "/logout",
    "desconectar": "/logout",
    "git-id": "/git-id",
    "identidad": "/git-id",
    "dir": "/dir",
    "carpeta": "/dir",
    "directorio": "/dir",
    "importar-github": "/importar-github",
    "mis-repos": "/importar-github",
    "descubrir": "/importar-github",
    "nuevos": "/nuevos",
    "check-github": "/nuevos",
    "novedades": "/nuevos",
    "modo": "/modo",
    "modo-sync": "/modo",
    "espejo": "/modo",
    "mirror": "/modo",
    "publico": "/publico",
    "preparar-publico": "/publico",
    "proteger-publico": "/publico",
    "set-key": "/set-key",
    "key": "/set-key",
    "gitflow": "/gitflow",
    "develop": "/gitflow",
    "ramas": "/gitflow",
    "seguridad": "/seguridad",
    "360": "/seguridad",
    "salud-360": "/seguridad",
    "secretos": "/seguridad",
    "onboarding": "/onboarding",
    "organizar": "/onboarding",
    "reorganizar": "/onboarding",
    "ia": "/ia",
    "ai": "/ia",
    "modelo": "/ia",
    "ollama": "/ia",
    "perfiles": "/perfiles",
    "identidades": "/perfiles",
    "trabajos": "/perfiles",
    "ayuda": "/ayuda",
    "help": "/ayuda",
    "helpme": "/ayuda",
    "help-me": "/ayuda",
    "comandos": "/ayuda",
    "menu": "/ayuda",
    "salir": "/salir",
    "exit": "/salir",
    "quit": "/salir"
}

CANONICAL_SLASH_COMMANDS = [
    "/code", "/orgs", "/modo", "/clone", "/disponibles", "/nuevos", "/salud", "/seguridad",
    "/gitflow", "/onboarding", "/limpiar", "/disco", "/sync", "/push", "/commit", "/apagar",
    "/vigilante", "/github", "/perfiles", "/catalogo", "/login", "/switch", "/logout", "/git-id", "/dir",
    "/importar-github", "/publico", "/ia", "/set-key", "/ayuda", "/helpme", "/salir"
]

def resolve_user_command(user_input):
    """
    Motor Antierrores:
    1. Reconoce comandos tanto con '/' como sin '/' (ej. 'salud', 'code amps', 'sync').
    2. Si hay un error tipografico en un comando (ej. '/saldu', '/synk', '/clonn', '/apago'),
       sugiere interactivamente la correccion adecuada.
    3. Si no es comando, devuelve None para que Gemini AI lo atienda como lenguaje natural.
    """
    raw = user_input.strip()
    if not raw:
        return None, ""

    parts = raw.split(None, 1)
    tok = parts[0]
    rest = parts[1].strip() if len(parts) > 1 else ""

    norm_tok = tok.lower().lstrip("/")

    # A) Coincidencia directa o alias conocido
    if norm_tok in COMMAND_MAP:
        return COMMAND_MAP[norm_tok], rest

    # B) Si el usuario uso barra '/' pero con error tipografico (ej: /saldu, /puxh)
    if tok.startswith("/"):
        matches = difflib.get_close_matches(tok.lower(), CANONICAL_SLASH_COMMANDS, n=1, cutoff=0.55)
        if matches:
            sug = matches[0]
            print(f"\n{C_YELLOW}[!] Comando '{tok}' no reconocido. Quisiste decir '{sug}'?{C_RESET}")
            full_sug = f"{sug} {rest}".strip()
            try:
                ans = input(f"{C_BOLD}Deseas ejecutar '{full_sug}'? [S/n]: {C_RESET}").strip().lower()
            except EOFError:
                ans = "n"
            if ans in ["", "s", "si", "y", "yes"]:
                return sug, rest
            else:
                return "CANCELLED", ""
        else:
            print(f"\n{C_RED}[!] Comando '{tok}' no reconocido. Escribe /ayuda para ver los comandos disponibles.{C_RESET}\n")
            return "CANCELLED", ""

    # C) Si no parece comando, es conversacion para Gemini
    return None, raw

# ==============================================================================
# BUCLE PRINCIPAL CONVERSACIONAL (REPL)
# ==============================================================================
def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Auto-actualizacion silenciosa de _sync si hay conexion con origin
    if os.path.isdir(os.path.join(script_dir, ".git")):
        try:
            subprocess.run(["git", "pull", "-q", "--ff-only"], cwd=script_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        except Exception:
            pass

    local_cfg = load_local_config(script_dir)

    # Directorio raiz de repositorios (personalizable por maquina en config.local.json)
    repos_dir = resolve_repos_dir(script_dir, local_cfg)

    # Cargar catalogo: repos.local.json privado (si existe) o repos.json maestro
    cat_local = os.path.join(script_dir, "repos.local.json")
    cat_master = os.path.join(script_dir, "repos.json")
    catalog_file = cat_local if os.path.isfile(cat_local) else cat_master

    catalog = []
    if os.path.isfile(catalog_file):
        try:
            with open(catalog_file, "r", encoding="utf-8-sig") as f:
                catalog = json.load(f)
        except Exception:
            pass

    # Excepcion absoluta: GitDoctor es la suite orquestadora, nunca un proyecto regular a clonar o mover
    catalog = [c for c in catalog if c.get("name") not in ["gitdoctor", "repos-sync"] and not c.get("url", "").endswith("/gitdoctor.git") and not c.get("url", "").endswith("/repos-sync.git")]

    # Estado de GitHub CLI y Organizaciones
    gh_info = get_github_status()

    # Boveda Privada: Si no existe repos.local.json pero existe una Boveda en GitHub Gist Secreto
    if not os.path.isfile(cat_local) and gh_info.get("logged_in"):
        existing_vault = vault_get_configured_id(script_dir, local_cfg)
        if existing_vault:
            print(f"\n{C_CYAN}🔐 [Boveda Privada Detectada]: Se encontro tu catalogo privado en GitHub Gist Secreto ({existing_vault}).{C_RESET}")
            try:
                ans = input(f"{C_BOLD}¿Deseas descargar tu catalogo privado a esta maquina ahora? [S/n]: {C_RESET}").strip().lower()
            except EOFError:
                ans = "s"
            if ans in ["", "s", "si", "y", "yes"]:
                res = vault_pull_catalog(script_dir, local_cfg, gh_info, target_gist_id=existing_vault)
                if res.get("success"):
                    catalog_file = cat_local
                    try:
                        with open(catalog_file, "r", encoding="utf-8-sig") as f:
                            catalog = json.load(f)
                        catalog = [c for c in catalog if c.get("name") not in ["gitdoctor", "repos-sync"] and not c.get("url", "").endswith("/gitdoctor.git") and not c.get("url", "").endswith("/repos-sync.git")]
                    except Exception:
                        pass

    all_known_orgs = get_active_orgs(repos_dir, gh_info)

    disabled_orgs = set(local_cfg.get("disabled_orgs", []))
    enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]

    api_key = load_gemini_api_key(script_dir, interactive=False)

    print(f"\n{C_CYAN}================================================================{C_RESET}")
    print(f"{C_WHITE}{C_BOLD}     🩺 GitDoctor AI -- Suite Clinica y DevOps de Repositorios  {C_RESET}")
    print(f"{C_CYAN}================================================================{C_RESET}")
    
    cat_type = "catalogo personal (repos.local.json)" if catalog_file == cat_local else "catalogo maestro (repos.json)"
    orgs_info_str = f"{len(enabled_orgs)}/{len(all_known_orgs)} activas" if disabled_orgs else f"{len(all_known_orgs)} organizaciones"
    print(f"{C_GRAY}Espacio: {repos_dir} | {orgs_info_str} | {len(catalog)} repos ({cat_type}){C_RESET}")

    # Notificacion de GitHub
    if gh_info['logged_in']:
        user_str = f"@{gh_info['user']}"
        name_str = f" ({gh_info['name']})" if gh_info.get('name') else ""
        print(f"{C_GREEN}[OK] GitHub:{C_RESET} {C_BOLD}{user_str}{C_RESET}{name_str} | {len(gh_info['orgs'])} orgs detectadas")
    else:
        print(f"{C_YELLOW}[!] GitHub:{C_RESET} No has iniciado sesion. Escribe {C_WHITE}/login{C_RESET} para autenticarte con tu cuenta.")

    # Notificacion de Motor de IA (Multi-IA: Ollama Local + Gemini Cloud)
    ai_provider = local_cfg.get("ai_provider", "gemini")
    ollama_info = probe_ollama_status()
    if ai_provider == "ollama":
        o_model = local_cfg.get("ollama_model", "llama3.1")
        print(f"{C_GREEN}[OK] IA Activa:{C_RESET} Ollama Local Offline {C_GRAY}(Modelo: {o_model} @ localhost:11434 - 100% privado){C_RESET}")
    elif api_key:
        print(f"{C_GREEN}[OK] IA Activa:{C_RESET} Google Gemini Cloud {C_GRAY}(Key: {get_masked_key(api_key)}){C_RESET}")
        if ollama_info["available"]:
            print(f"      {C_CYAN}[Tip Local]: Ollama detectado en tu maquina. Puedes alternar a IA local con /ia ollama.{C_RESET}")
    else:
        if ollama_info["available"]:
            print(f"{C_GREEN}[OK] IA Activa:{C_RESET} Ollama Local detectado {C_GRAY}(localhost:11434). Escribe /ia ollama para activarlo.{C_RESET}")
        else:
            print(f"{C_YELLOW}[!] IA:{C_RESET} Modo Offline {C_GRAY}(Usa /set-key para Gemini o abre Ollama para IA local offline){C_RESET}")

    # Auditoria inicial rapida (filtrada si hay orgs desactivadas)
    org_filter = enabled_orgs if disabled_orgs else None
    init_audit = audit_all_repos(repos_dir, catalog, with_fetch=False, org_filter=org_filter)
    print_health_report(init_audit)

    print(f"{C_WHITE}Comandos principales de GitDoctor:{C_RESET}")
    print(f"  {C_BOLD}/salud 360{C_RESET} (o /seguridad)  {C_GRAY}Auditoria profunda: Secretos, API keys, Gitflow e higiene{C_RESET}")
    print(f"  {C_BOLD}/gitflow{C_RESET} [repo|all]        {C_GRAY}Auditar e implementar estrategia Gitflow (crea rama develop){C_RESET}")
    print(f"  {C_BOLD}/perfiles{C_RESET}                  {C_GRAY}Gestionar identidades de commit por organizacion (Multi-Trabajo){C_RESET}")
    print(f"  {C_BOLD}/ia{C_RESET}                        {C_GRAY}Alternar motor de IA (Ollama Local Offline vs Gemini Cloud){C_RESET}")
    print(f"  {C_BOLD}/onboarding{C_RESET}                {C_GRAY}Diagnosticar y reorganizar proyectos sueltos en organizaciones{C_RESET}")
    print(f"  {C_BOLD}/code <repo>{C_RESET}              {C_GRAY}Abrir proyecto en Visual Studio Code{C_RESET}")
    print(f"  {C_BOLD}/catalogo{C_RESET} [push|pull]       {C_GRAY}Boveda Privada en Gist Secreto para compartir repos entre Mac y PC{C_RESET}")
    print(f"  {C_BOLD}/sync{C_RESET}                     {C_GRAY}Sincronizar y descargar cambios remotos en paralelo{C_RESET}")
    print(f"  {C_BOLD}/push{C_RESET}                     {C_GRAY}Subir commits locales pendientes a GitHub{C_RESET}")
    print(f"  {C_BOLD}/disco{C_RESET} (o /prune)         {C_GRAY}Analizar y purgar carpetas pesadas (node_modules, etc.){C_RESET}")
    print(f"  {C_BOLD}/apagar{C_RESET} (o /checkout)     {C_GRAY}Revision de seguridad antes de salir o cambiar de equipo{C_RESET}")
    print(f"  {C_BOLD}/helpme{C_RESET} (o /ayuda)        {C_GRAY}Ver catalogo clinico completo de comandos{C_RESET}")
    print(f"  {C_BOLD}/salir{C_RESET}                    {C_GRAY}Cerrar la consola de GitDoctor{C_RESET}")
    print(f"{C_GRAY}O escribe directamente en lenguaje natural lo que necesitas.{C_RESET}\n")

    conversation_history = []
    system_instruction = build_system_instruction(enabled_orgs, user_name=gh_info.get('name') or gh_info.get('user'))

    while True:
        try:
            user_input = input(f"{C_CYAN}GitDoctor > {C_RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C_GRAY}Cerrando GitDoctor. Hasta pronto!{C_RESET}\n")
            break

        if not user_input:
            continue

        canon_cmd, rest = resolve_user_command(user_input)

        if canon_cmd == "CANCELLED":
            continue

        if canon_cmd in ["/salir", "exit", "quit"]:
            print(f"\n{C_GRAY}Cerrando GitDoctor. Hasta pronto!{C_RESET}\n")
            break

        elif canon_cmd in ["/ayuda", "/helpme"]:
            print_helpme_commands()
            continue

        elif canon_cmd == "/code":
            if not rest:
                print(f"\n{C_YELLOW}[?] No indicaste el repositorio a abrir.{C_RESET}")
                try:
                    rest = input(f"{C_BOLD}Nombre o termino del proyecto a abrir en VS Code: {C_RESET}").strip()
                except EOFError:
                    rest = ""
            if rest:
                open_repo_in_vscode(repos_dir, catalog, rest)
            continue

        elif canon_cmd == "/orgs":
            local_cfg = interactive_manage_orgs(repos_dir, catalog, local_cfg, script_dir, all_known_orgs)
            disabled_orgs = set(local_cfg.get("disabled_orgs", [])) if local_cfg.get("sync_mode") == "selective" else set()
            enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
            system_instruction = build_system_instruction(enabled_orgs, user_name=gh_info.get('name') or gh_info.get('user'))
            continue

        elif canon_cmd == "/modo":
            interactive_toggle_sync_mode(script_dir, local_cfg)
            disabled_orgs = set(local_cfg.get("disabled_orgs", [])) if local_cfg.get("sync_mode") == "selective" else set()
            enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
            system_instruction = build_system_instruction(enabled_orgs, user_name=gh_info.get('name') or gh_info.get('user'))
            continue

        elif canon_cmd == "/clone":
            if not rest:
                print(f"\n{C_YELLOW}[?] No indicaste qué repositorio u organizacion clonar.{C_RESET}")
                print(f"{C_GRAY}Tip: Escribe /disponibles para ver la lista de repos que faltan en este equipo.{C_RESET}")
                try:
                    rest = input(f"{C_BOLD}Nombre a descargar: {C_RESET}").strip()
                except EOFError:
                    rest = ""
            if rest:
                clone_specific_repo_or_org(repos_dir, catalog, rest)
            continue

        elif canon_cmd == "/disponibles":
            list_available_uncloned_repos(repos_dir, catalog)
            continue

        elif canon_cmd == "/nuevos":
            check_for_new_remote_repos(repos_dir, catalog, catalog_file, gh_info, enabled_orgs, interactive=True)
            continue

        elif canon_cmd == "/disco":
            check_and_prune_disk(repos_dir, catalog, auto_prune=False)
            continue

        elif canon_cmd == "/apagar":
            safe_preflight_checkout(repos_dir, catalog)
            continue

        elif canon_cmd == "/salud":
            if "360" in rest.lower():
                with_fetch = "fetch" in rest.lower() or "-f" in rest.lower()
                see_all = "-all" in rest.lower() or "all" in rest.lower()
                org_filter = None if see_all or not disabled_orgs else enabled_orgs
                audit_health_360(repos_dir, catalog, with_fetch=with_fetch, org_filter=org_filter)
                continue
            with_fetch = "fetch" in rest.lower() or "-f" in rest.lower()
            see_all = "-all" in rest.lower() or "all" in rest.lower()
            org_filter = None if see_all or not disabled_orgs else enabled_orgs
            scope_str = "todos los repositorios" if see_all or not disabled_orgs else f"{len(enabled_orgs)} organizaciones activas"
            print(f"\n{C_CYAN}[*] Evaluando salud ({scope_str}, {'con fetch remoto' if with_fetch else 'local'})...{C_RESET}")
            audit = audit_all_repos(repos_dir, catalog, with_fetch=with_fetch, org_filter=org_filter)
            print_health_report(audit)
            continue

        elif canon_cmd == "/seguridad":
            with_fetch = "fetch" in rest.lower() or "-f" in rest.lower()
            see_all = "-all" in rest.lower() or "all" in rest.lower()
            org_filter = None if see_all or not disabled_orgs else enabled_orgs
            audit_health_360(repos_dir, catalog, with_fetch=with_fetch, org_filter=org_filter)
            continue

        elif canon_cmd == "/gitflow":
            target = rest.strip() if rest else None
            org_filter = None if not disabled_orgs else enabled_orgs
            interactive_manage_gitflow(repos_dir, catalog, target_repo=target, org_filter=org_filter)
            continue

        elif canon_cmd == "/onboarding":
            if run_onboarding_assistant:
                run_onboarding_assistant(repos_dir, interactive=True)
            else:
                print(f"{C_RED}[!] Modulo onboarding.py no disponible.{C_RESET}\n")
            continue

        elif canon_cmd == "/limpiar":
            target = rest.strip() if rest else "all"
            clean_repo_hygiene(repos_dir, catalog, target_repo=target)
            continue

        elif canon_cmd == "/sync":
            target_org = rest.strip() if rest else None
            org_filter = [target_org] if target_org else (enabled_orgs if disabled_orgs else None)
            sync_all_repos(repos_dir, catalog, auto_pull=True, auto_clone=True, org_filter=org_filter)
            if gh_info.get('logged_in'):
                check_for_new_remote_repos(repos_dir, catalog, catalog_file, gh_info, org_filter or enabled_orgs, interactive=True)
            continue

        elif canon_cmd == "/push":
            target = rest.strip() if rest else "all"
            push_ahead_repos(repos_dir, catalog, target_repo=target)
            continue

        elif canon_cmd == "/commit":
            parts = rest.split(None, 1) if rest else []
            if len(parts) >= 2:
                r_target, c_msg = parts[0], parts[1]
            else:
                r_target = parts[0] if len(parts) == 1 else ""
                if not r_target:
                    try:
                        r_target = input(f"{C_BOLD}Repositorio a commitear: {C_RESET}").strip()
                    except EOFError:
                        r_target = ""
                try:
                    c_msg = input(f"{C_BOLD}Mensaje descriptivo del commit: {C_RESET}").strip()
                except EOFError:
                    c_msg = ""
            if r_target and c_msg:
                commit_single_repo(repos_dir, catalog, r_target, c_msg)
            else:
                print(f"{C_YELLOW}[!] Operacion de commit cancelada.{C_RESET}\n")
            continue

        elif canon_cmd == "/github":
            gh_info = get_github_status()
            print_github_profile(gh_info)
            continue

        elif canon_cmd == "/login":
            interactive_github_login()
            gh_info = get_github_status()
            all_known_orgs = get_active_orgs(repos_dir, gh_info)
            disabled_orgs = set(local_cfg.get("disabled_orgs", []))
            enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
            system_instruction = build_system_instruction(enabled_orgs)
            continue

        elif canon_cmd == "/switch":
            target = rest.strip() if rest else None
            interactive_github_switch(target_user=target)
            gh_info = get_github_status()
            all_known_orgs = get_active_orgs(repos_dir, gh_info)
            disabled_orgs = set(local_cfg.get("disabled_orgs", []))
            enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
            system_instruction = build_system_instruction(enabled_orgs)
            continue

        elif canon_cmd == "/logout":
            target = rest.strip() if rest else None
            interactive_github_logout(target_user=target)
            gh_info = get_github_status()
            all_known_orgs = get_active_orgs(repos_dir, gh_info)
            disabled_orgs = set(local_cfg.get("disabled_orgs", []))
            enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
            system_instruction = build_system_instruction(enabled_orgs)
            continue

        elif canon_cmd == "/git-id":
            parts = rest.split(None, 1) if rest else []
            if len(parts) == 2:
                interactive_git_identity(name=parts[0], email=parts[1])
            else:
                interactive_git_identity()
            continue

        elif canon_cmd == "/dir":
            repos_dir = set_custom_repos_dir(script_dir, local_cfg, new_dir=rest if rest else None)
            all_known_orgs = get_active_orgs(repos_dir, gh_info)
            disabled_orgs = set(local_cfg.get("disabled_orgs", []))
            enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
            system_instruction = build_system_instruction(enabled_orgs)
            continue

        elif canon_cmd == "/catalogo":
            parts = rest.split(None, 1) if rest else []
            act = parts[0] if len(parts) >= 1 else None
            p_arg = parts[1] if len(parts) >= 2 else None
            interactive_manage_catalog_vault(script_dir, local_cfg, gh_info, action=act, param=p_arg, repos_dir=repos_dir)
            cat_local = os.path.join(script_dir, "repos.local.json")
            if os.path.isfile(cat_local):
                catalog_file = cat_local
                try:
                    with open(catalog_file, "r", encoding="utf-8-sig") as f:
                        catalog = json.load(f)
                    catalog = [c for c in catalog if c.get("name") not in ["gitdoctor", "repos-sync"] and not c.get("url", "").endswith("/gitdoctor.git") and not c.get("url", "").endswith("/repos-sync.git")]
                except Exception:
                    pass
                all_known_orgs = get_active_orgs(repos_dir, gh_info)
                disabled_orgs = set(local_cfg.get("disabled_orgs", [])) if local_cfg.get("sync_mode") == "selective" else set()
                enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
                system_instruction = build_system_instruction(enabled_orgs, user_name=gh_info.get('name') or gh_info.get('user'))
            continue

        elif canon_cmd == "/importar-github":
            res = import_repos_from_github(script_dir, gh_info)
            if res.get("success"):
                cat_local = os.path.join(script_dir, "repos.local.json")
                if os.path.isfile(cat_local):
                    catalog_file = cat_local
                    with open(catalog_file, "r", encoding="utf-8-sig") as f:
                        catalog = json.load(f)
                    all_known_orgs = get_active_orgs(repos_dir, gh_info)
                    disabled_orgs = set(local_cfg.get("disabled_orgs", []))
                    enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
                    system_instruction = build_system_instruction(enabled_orgs, user_name=gh_info.get('name') or gh_info.get('user'))
            continue

        elif canon_cmd == "/publico":
            prepare_for_public_repo(script_dir)
            cat_local = os.path.join(script_dir, "repos.local.json")
            if os.path.isfile(cat_local):
                catalog_file = cat_local
                with open(catalog_file, "r", encoding="utf-8-sig") as f:
                    catalog = json.load(f)
            continue

        elif canon_cmd == "/vigilante":
            sec = 300
            if rest and rest.isdigit():
                sec = int(rest)
            notif_flag = local_cfg.get("notifications_enabled", True)
            start_watchdog_loop(repos_dir, catalog, interval_seconds=sec, send_notifications=notif_flag,
                                catalog_file=catalog_file, gh_info=gh_info, active_orgs=enabled_orgs)
            continue

        elif canon_cmd == "/set-key":
            new_key = load_gemini_api_key(script_dir, interactive=True)
            if new_key:
                api_key = new_key
                _CACHED_GEMINI_MODELS = []
                print(f"{C_GREEN}[OK] Gemini AI listo con clave actualizada.{C_RESET}\n")
            continue

        elif canon_cmd == "/ia":
            local_cfg = interactive_switch_ai(local_cfg, script_dir, target=rest if rest else None)
            continue

        elif canon_cmd == "/perfiles":
            interactive_manage_profiles(repos_dir, catalog, local_cfg, script_dir)
            continue

        # Turno conversacional con IA
        ai_provider = local_cfg.get("ai_provider", "gemini")
        if ai_provider == "gemini" and not api_key:
            ollama_info = probe_ollama_status()
            if ollama_info["available"]:
                print(f"\n{C_CYAN}[*] Gemini no tiene clave configurada, pero Ollama esta activo localmente.{C_RESET}")
                print(f"{C_GRAY}Cambiando automaticamente a Ollama Local Offline...{C_RESET}\n")
                local_cfg["ai_provider"] = "ollama"
                ai_provider = "ollama"
            else:
                print(f"\n{C_YELLOW}[!] Para conversar en lenguaje natural con IA necesitas tu Gemini API Key o abrir Ollama.{C_RESET}")
                print(f"{C_GRAY}Escribe {C_WHITE}/set-key{C_GRAY} para configurar tu clave segura o {C_WHITE}/ia{C_GRAY} para IA local.{C_RESET}\n")
                continue

        ai_engine_name = "Ollama Local" if ai_provider == "ollama" else "Gemini"
        print(f"{C_GRAY}Consultando con {ai_engine_name}...{C_RESET}")
        conversation_history.append({
            "role": "user",
            "parts": [{"text": user_input}]
        })

        if len(conversation_history) > 12:
            conversation_history = conversation_history[-10:]
            while conversation_history and conversation_history[0].get("role") != "user":
                conversation_history.pop(0)

        resp = call_ai_engine(api_key, conversation_history, system_instruction, local_cfg)
        if not resp:
            if conversation_history and conversation_history[-1].get("role") == "user":
                conversation_history.pop()

            err_detail = get_last_gemini_error()
            is_rate_limit = "RATE_LIMIT" in err_detail or "429" in err_detail

            if is_rate_limit:
                clean_err = err_detail.replace("RATE_LIMIT: ", "")
                print(f"\n{C_YELLOW}[!] {clean_err}{C_RESET}")
                print(f"{C_GRAY}La cuota gratuita de Gemini suele restablecerse automaticamente en 30-60 segundos.{C_RESET}")
                ollama_probe = probe_ollama_status()
                if ollama_probe["available"]:
                    print(f"      {C_CYAN}[Tip Local]: Tienes Ollama activo en localhost:11434. Escribe '/ia ollama' para usar IA local sin limites.{C_RESET}")
            else:
                print(f"\n{C_RED}[!] No se pudo conectar con la IA temporalmente.{C_RESET} {C_YELLOW}({err_detail}){C_RESET}")

            try:
                ans = input(f"\n{C_BOLD}¿Quieres ver el listado de comandos disponibles para continuar? [S/n]: {C_RESET}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                ans = "n"

            if ans in ["", "s", "si", "y", "yes"]:
                print_helpme_commands()
            else:
                run_cooldown_countdown(seconds=25)
            continue

        try:
            candidate = resp["candidates"][0]
            parts = candidate["content"].get("parts", [])

            function_calls = [p["functionCall"] for p in parts if "functionCall" in p]
            text_parts = [p["text"] for p in parts if "text" in p]

            if text_parts:
                ai_text = "\n".join(text_parts).strip()
                print(f"\n{C_BOLD}GitDoctor AI:{C_RESET}\n{ai_text}\n")

            if function_calls:
                conversation_history.append(candidate["content"])

                for fc in function_calls:
                    fn_name = fc["name"]
                    fn_args = fc.get("args", {})
                    tool_result = execute_tool_call(fn_name, fn_args, repos_dir, catalog, catalog_file, api_key, enabled_orgs, local_cfg)

                    if fn_name in ["github_login", "github_switch_user", "github_logout"]:
                        gh_info = get_github_status()
                        all_known_orgs = get_active_orgs(repos_dir, gh_info)
                        disabled_orgs = set(local_cfg.get("disabled_orgs", []))
                        enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
                        system_instruction = build_system_instruction(enabled_orgs)

                    conversation_history.append({
                        "role": "user",
                        "parts": [{
                            "functionResponse": {
                                "name": fn_name,
                                "response": tool_result
                            }
                        }]
                    })

                follow_up = call_ai_engine(api_key, conversation_history, system_instruction, local_cfg)
                if follow_up:
                    follow_cand = follow_up["candidates"][0]
                    follow_texts = [p["text"] for p in follow_cand["content"].get("parts", []) if "text" in p]
                    if follow_texts:
                        print(f"\n{C_BOLD}GitDoctor AI:{C_RESET}\n{'\n'.join(follow_texts).strip()}\n")
                    conversation_history.append(follow_cand["content"])
                else:
                    err_detail = get_last_gemini_error()
                    print(f"{C_YELLOW}[!] La accion se ejecuto, pero no se pudo obtener el mensaje final de la IA ({err_detail}).{C_RESET}\n")
            else:
                conversation_history.append(candidate["content"])

        except Exception as e:
            print(f"{C_RED}[!] Error procesando respuesta de IA: {sanitize_error(e)}{C_RESET}\n")

if __name__ == "__main__":
    main()
