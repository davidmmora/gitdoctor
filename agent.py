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
import shutil
import tempfile
import difflib
import getpass
import subprocess
import urllib.request
import urllib.error
import urllib.parse
import webbrowser
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    from onboarding import run_onboarding_assistant, configure_ai_provider, save_env_var
except ImportError:
    run_onboarding_assistant = None
    configure_ai_provider = None
    save_env_var = None

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

def save_env_var_local(script_dir, var_name, value):
    """Guarda o actualiza una variable en .env de forma segura y restringe permisos a 0600"""
    ensure_env_in_gitignore(script_dir)
    env_path = os.path.join(script_dir, ".env")
    existing_lines = []
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip().startswith(f"{var_name}="):
                        existing_lines.append(line)
        except Exception:
            pass

    existing_lines.append(f"{var_name}={value.strip()}\n")
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
        print(f"{C_RED}[ERROR] No se pudo guardar {var_name}: {sanitize_error(e)}{C_RESET}")
        return False

def save_gemini_api_key(script_dir, key):
    """Guarda la API key de Gemini en .env con permisos restringidos"""
    if save_env_var:
        return save_env_var(script_dir, "GEMINI_API_KEY", key)
    return save_env_var_local(script_dir, "GEMINI_API_KEY", key)

def load_ai_api_key(script_dir, provider=None, interactive=False):
    """Carga la API key para el proveedor de IA configurado desde variables de entorno o .env"""
    if not provider:
        cfg = load_local_config(script_dir)
        provider = cfg.get("ai_provider", "gemini")

    if provider in ["ollama", "none"]:
        return None

    var_name = {
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "aws": "AWS_ACCESS_KEY_ID"
    }.get(provider, "GEMINI_API_KEY")

    # 1. Variable en proceso / entorno
    val = os.environ.get(var_name, "").strip()
    if val:
        return val

    # 2. Archivo .env
    env_path = os.path.join(script_dir, ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith(f"{var_name}="):
                        k = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if k:
                            return k
        except Exception:
            pass

    if not interactive:
        return None

    # Configuracion interactiva multi-proveedor
    if configure_ai_provider:
        cfg = load_local_config(script_dir)
        updated_cfg = configure_ai_provider(script_dir, cfg)
        save_local_config(script_dir, updated_cfg)
        chosen_p = updated_cfg.get("ai_provider", "gemini")
        return load_ai_api_key(script_dir, chosen_p, interactive=False)

    # Fallback si configure_ai_provider no esta disponible
    print(f"\n{C_YELLOW}+--------------------------------------------------------+{C_RESET}")
    print(f"{C_YELLOW}|  Configuracion de Clave para {var_name:<26}|{C_RESET}")
    print(f"{C_YELLOW}+--------------------------------------------------------+{C_RESET}")
    user_key = ""
    try:
        user_key = getpass.getpass(f"{C_BOLD}Introduce tu clave ({var_name}): {C_RESET}").strip()
    except Exception:
        try:
            user_key = input(f"{C_BOLD}Introduce tu clave ({var_name}): {C_RESET}").strip()
        except EOFError:
            user_key = ""

    if user_key:
        save_fn = save_env_var if save_env_var else save_env_var_local
        if save_fn(script_dir, var_name, user_key):
            print(f"{C_GREEN}[OK] Clave guardada exitosamente y protegida localmente.{C_RESET}\n")
            return user_key

    return None

def load_gemini_api_key(script_dir, interactive=False):
    """Carga la API key de Gemini (compatibilidad hacia atras)"""
    return load_ai_api_key(script_dir, provider="gemini", interactive=interactive)

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
# MOTOR DE BUSQUEDA INTELIGENTE, COINCIDENCIA DIFUSA Y CATALOGO DE REPOSITORIOS
# ==============================================================================
def split_words(s):
    """Divide cadenas en palabras considerando snake_case, kebab-case y CamelCase"""
    if not s:
        return []
    s = s.replace('-', ' ').replace('_', ' ')
    words = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|\d+', s)
    return [w.lower() for w in words] if words else [s.lower()]

def find_matching_repos(query, catalog, repos_dir=None, cutoff=0.50):
    """
    Motor de Busqueda Inteligente y Coincidencia Difusa (Fuzzy Search) para Repositorios.
    Tolera:
    - Faltas de ortografia y typos (ej: 'peluza' -> 'pelusa', 'trascript' -> 'TranscriptAudio')
    - Diferencias de mayusculas/minusculas, guiones y espacios (ej: 'web-api-net' -> 'WebApiNet')
    - Nombres parciales o palabras clave (ej: 'audio' -> 'TranscriptAudio', 'moodboard' -> 'moodboard-homesweethome')
    - Busqueda en catalogo y en carpetas locales en disco

    Devuelve lista de dicts ordenados por relevancia:
    [{'entry': {...}, 'score': float, 'match_type': str, 'is_cloned': bool}, ...]
    """
    if not query:
        return []

    q_clean = query.strip().lower().rstrip('/').replace('.git', '')
    if q_clean.startswith("./"):
        q_clean = q_clean[2:]
    if q_clean.startswith("repo:"):
        q_clean = q_clean[5:].strip()

    q_alnum = re.sub(r'[^a-z0-9]', '', q_clean)
    q_words = split_words(query)

    # Construir conjunto de repositorios (catalogo + carpetas fisicas no catalogadas)
    pool = []
    seen_names = set()

    for item in catalog:
        name = item.get("name", "")
        if name:
            seen_names.add(name.lower())
            pool.append(dict(item))

    script_dir = os.path.dirname(os.path.abspath(__file__))
    if repos_dir and os.path.isdir(repos_dir):
        try:
            for item in sorted(os.listdir(repos_dir)):
                p1 = os.path.join(repos_dir, item)
                if is_gitdoctor_path(p1, script_dir) or item.startswith('.'):
                    continue
                if not os.path.isdir(p1):
                    continue
                if os.path.isdir(os.path.join(p1, ".git")):
                    if item.lower() not in seen_names:
                        seen_names.add(item.lower())
                        pool.append({
                            "name": item,
                            "group": "Personal",
                            "path": f"Personal/{item}",
                            "url": run_cmd(['git', 'remote', 'get-url', 'origin'], cwd=p1) or "",
                            "defaultBranch": "main"
                        })
                else:
                    for sub in sorted(os.listdir(p1)):
                        if sub.startswith('.'):
                            continue
                        p2 = os.path.join(p1, sub)
                        if os.path.isdir(p2) and os.path.isdir(os.path.join(p2, ".git")):
                            if sub.lower() not in seen_names:
                                seen_names.add(sub.lower())
                                pool.append({
                                    "name": sub,
                                    "group": item,
                                    "path": f"{item}/{sub}",
                                    "url": run_cmd(['git', 'remote', 'get-url', 'origin'], cwd=p2) or "",
                                    "defaultBranch": "main"
                                })
        except Exception:
            pass

    results = []
    for entry in pool:
        name = entry.get('name', '')
        group = entry.get('group', '')
        path = entry.get('path', f"{group}/{name}")
        n_lower = name.lower()
        n_alnum = re.sub(r'[^a-z0-9]', '', n_lower)
        p_lower = path.lower()
        p_alnum = re.sub(r'[^a-z0-9]', '', p_lower)
        n_words = split_words(name)

        score = 0.0
        match_type = 'none'

        # 1. Coincidencia exacta de nombre o ruta
        if q_clean == n_lower or q_clean == p_lower:
            score = 1.0
            match_type = 'exact'
        # 2. Coincidencia alfanumerica exacta (ignora guiones, mayusculas, espacios)
        elif q_alnum and (q_alnum == n_alnum or q_alnum == p_alnum):
            score = 0.98
            match_type = 'alnum'
        # 3. Prefijo alfanumerico (ej: "webapi" en "WebApiNet")
        elif q_alnum and n_alnum.startswith(q_alnum) and len(q_alnum) >= 3:
            score = 0.94
            match_type = 'prefix'
        # 4. Subcadena alfanumerica directa
        elif q_alnum and q_alnum in n_alnum and len(q_alnum) >= 3:
            score = 0.90
            match_type = 'substring'
        # 5. Coincidencia de palabras (tokens)
        elif any(qw in nw for qw in q_words for nw in n_words if len(qw) >= 3):
            score = 0.88
            match_type = 'word_match'
        # 6. Subcadena en ruta completa
        elif q_clean in p_lower and len(q_clean) >= 3:
            score = 0.85
            match_type = 'substring_path'
        else:
            # 7. Coincidencia difusa (fuzzy ratio) con difflib
            r_name = difflib.SequenceMatcher(None, q_clean, n_lower).ratio()
            r_alnum = difflib.SequenceMatcher(None, q_alnum, n_alnum).ratio() if (q_alnum and n_alnum) else 0.0
            r_parts = max([difflib.SequenceMatcher(None, q_clean, part).ratio() for part in n_words]) if n_words else 0.0
            best_r = max(r_name, r_alnum, r_parts)
            if best_r >= cutoff:
                score = round(best_r, 3)
                match_type = 'fuzzy'

        if score >= cutoff:
            is_cloned = False
            if repos_dir:
                rel = path.replace('/', os.sep)
                full = os.path.join(repos_dir, rel)
                is_cloned = os.path.isdir(os.path.join(full, ".git"))
            results.append({
                "entry": entry,
                "score": score,
                "match_type": match_type,
                "is_cloned": is_cloned
            })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results

def find_matching_org(query, known_orgs, cutoff=0.85):
    """Busca una organizacion con tolerancia a mayusculas, guiones y faltas de ortografia"""
    if not query:
        return None
    q = query.strip().lower()
    q_alnum = re.sub(r'[^a-z0-9]', '', q)

    for o in known_orgs:
        if o.lower() == q or re.sub(r'[^a-z0-9]', '', o.lower()) == q_alnum:
            return o

    # Fuzzy match con umbral alto para no confundir nombres de repos con organizaciones
    if len(q) >= 4:
        close = difflib.get_close_matches(q, [o.lower() for o in known_orgs], n=1, cutoff=cutoff)
        if close:
            for o in known_orgs:
                if o.lower() == close[0]:
                    return o
    return None

def print_repos_catalog_table(repo_items, filter_desc=""):
    """Imprime una tabla clinica y visual del catalogo de repositorios"""
    print(f"\n{C_CYAN}=================================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  📁 Catálogo de Repositorios de Desarrollo ({len(repo_items)} encontrados)           {C_RESET}")
    if filter_desc:
        print(f"  {C_GRAY}Filtro aplicado: '{filter_desc}'{C_RESET}")
    print(f"{C_CYAN}=================================================================================={C_RESET}")

    if not repo_items:
        print(f"\n  {C_YELLOW}[!] No se encontraron repositorios con el criterio especificado.{C_RESET}")
        print(f"  {C_GRAY}Tip: Escribe {C_WHITE}/repos{C_GRAY} para ver todos o {C_WHITE}/buscar <termino>{C_GRAY} para buscar con tolerancia a faltas.{C_RESET}\n")
        return

    by_org = {}
    for r in repo_items:
        by_org.setdefault(r["group"], []).append(r)

    total_cloned = sum(1 for r in repo_items if r["is_cloned"])
    total_uncloned = len(repo_items) - total_cloned

    for org, r_list in sorted(by_org.items()):
        cloned_in_org = sum(1 for r in r_list if r["is_cloned"])
        uncloned_in_org = len(r_list) - cloned_in_org
        stats_str = f"{cloned_in_org} clonados" if uncloned_in_org == 0 else f"{cloned_in_org} clonados, {uncloned_in_org} en nube"
        print(f"\n{C_BOLD}{C_CYAN}🏢 [{org}]{C_RESET} {C_GRAY}({len(r_list)} repos: {stats_str}){C_RESET}")

        for idx, r in enumerate(sorted(r_list, key=lambda x: x["name"].lower()), 1):
            if r["is_cloned"]:
                status_str = f"{C_GREEN}[✓ Clonado]{C_RESET}"
                dirty_str = f" {C_YELLOW}(cambios locales){C_RESET}" if r["is_dirty"] else ""
                branch_str = f" {C_CYAN}(rama: {r['branch']}){C_RESET}"
            else:
                status_str = f"{C_YELLOW}[☁ En nube]{C_RESET}"
                dirty_str = ""
                branch_str = f" {C_GRAY}(default: {r['defaultBranch']}){C_RESET}"

            print(f"  {idx:2d}. {C_WHITE}{r['name']:<28}{C_RESET} {status_str}{branch_str}{dirty_str}")

    print(f"\n{C_CYAN}----------------------------------------------------------------------------------{C_RESET}")
    print(f"  * Total: {C_BOLD}{len(repo_items)} repositorios{C_RESET} ({C_GREEN}{total_cloned} clonados en este equipo{C_RESET}, {C_YELLOW}{total_uncloned} disponibles en GitHub{C_RESET})")
    print(f"  * {C_GRAY}Comandos directos:{C_RESET} {C_WHITE}/code <nombre>{C_RESET} para abrir en VS Code | {C_WHITE}/clone <nombre>{C_RESET} para descargar | {C_WHITE}/buscar <texto>{C_RESET} para buscar difuso")
    print("")

def list_repositories(repos_dir, catalog, query="", org_name="", status_filter="all", interactive=True):
    """
    Lista y filtra los repositorios del catalogo y disco con estado detallado.
    - Soporta filtro por termino/query (con tolerancia a faltas de ortografia).
    - Soporta filtro por organizacion y por estado (cloned / uncloned / all).
    - Devuelve dict estructurado y muestra en pantalla de forma atractiva.
    """
    q = (query or "").strip()
    org = (org_name or "").strip()

    # Si query contiene modificadores de estado
    if "--nube" in q.lower() or "--cloud" in q.lower() or "--faltantes" in q.lower() or "--disponibles" in q.lower():
        status_filter = "uncloned"
        q = re.sub(r'--(nube|cloud|faltantes|disponibles)', '', q, flags=re.I).strip()
    elif "--clonados" in q.lower() or "--local" in q.lower():
        status_filter = "cloned"
        q = re.sub(r'--(clonados|local)', '', q, flags=re.I).strip()

    # Si se paso un query pero no org, verificar si el query es una organizacion
    if q and not org:
        all_orgs = get_active_orgs(repos_dir)
        repo_names = {c['name'].lower() for c in catalog}
        q_alnum = re.sub(r'[^a-z0-9]', '', q.lower())
        matched_o = None
        for o in all_orgs:
            if o.lower() == q.lower() or re.sub(r'[^a-z0-9]', '', o.lower()) == q_alnum:
                matched_o = o
                break
        # Solo considerarlo filtro de org si coincide con una org y no es el nombre exacto de un repo
        if matched_o and q.lower() not in repo_names:
            org = matched_o
            q = ""

    # Obtener candidatos
    candidates = []
    if q:
        matches = find_matching_repos(q, catalog, repos_dir=repos_dir, cutoff=0.45)
        candidates = [m["entry"] for m in matches]
    else:
        candidates = list(catalog)
        # Agregar repos descubiertos fisicamente en disco que no esten en catalog
        known_names = {c["name"].lower() for c in catalog}
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if repos_dir and os.path.isdir(repos_dir):
            try:
                for item in sorted(os.listdir(repos_dir)):
                    p1 = os.path.join(repos_dir, item)
                    if is_gitdoctor_path(p1, script_dir) or item.startswith('.'):
                        continue
                    if not os.path.isdir(p1):
                        continue
                    if os.path.isdir(os.path.join(p1, ".git")):
                        if item.lower() not in known_names:
                            known_names.add(item.lower())
                            candidates.append({
                                "name": item, "group": "Personal", "path": f"Personal/{item}",
                                "url": run_cmd(['git', 'remote', 'get-url', 'origin'], cwd=p1) or "",
                                "defaultBranch": "main"
                            })
                    else:
                        for sub in sorted(os.listdir(p1)):
                            if sub.startswith('.'):
                                continue
                            p2 = os.path.join(p1, sub)
                            if os.path.isdir(p2) and os.path.isdir(os.path.join(p2, ".git")):
                                if sub.lower() not in known_names:
                                    known_names.add(sub.lower())
                                    candidates.append({
                                        "name": sub, "group": item, "path": f"{item}/{sub}",
                                        "url": run_cmd(['git', 'remote', 'get-url', 'origin'], cwd=p2) or "",
                                        "defaultBranch": "main"
                                    })
            except Exception:
                pass

    if org:
        candidates = [
            c for c in candidates
            if c.get("group", "").lower() == org.lower()
            or re.sub(r'[^a-z0-9]', '', c.get("group", "").lower()) == re.sub(r'[^a-z0-9]', '', org.lower())
        ]

    repo_items = []
    for entry in candidates:
        name = entry["name"]
        grp = entry.get("group", "Otros")
        rel_path = entry.get("path", f"{grp}/{name}").replace("/", os.sep)
        full_path = os.path.join(repos_dir, rel_path)
        git_dir = os.path.join(full_path, ".git")
        is_cloned = os.path.isdir(git_dir)
        branch = "-"
        is_dirty = False

        if is_cloned:
            b = run_cmd(["git", "branch", "--show-current"], cwd=full_path)
            branch = b if b else run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=full_path) or entry.get("defaultBranch", "main")
            st = run_cmd(["git", "status", "--porcelain"], cwd=full_path)
            is_dirty = bool(st)

        if status_filter == "cloned" and not is_cloned:
            continue
        if status_filter in ["uncloned", "nube"] and is_cloned:
            continue

        repo_items.append({
            "name": name,
            "group": grp,
            "path": rel_path,
            "full_path": full_path,
            "is_cloned": is_cloned,
            "branch": branch,
            "is_dirty": is_dirty,
            "url": entry.get("url", ""),
            "defaultBranch": entry.get("defaultBranch", "main")
        })

    filter_desc = q if q else (f"Organizacion: {org}" if org else "")
    if status_filter != "all":
        filter_desc = f"{filter_desc} (solo {status_filter})".strip()

    if interactive:
        print_repos_catalog_table(repo_items, filter_desc=filter_desc)

    return {
        "total": len(repo_items),
        "cloned_count": len([r for r in repo_items if r["is_cloned"]]),
        "uncloned_count": len([r for r in repo_items if not r["is_cloned"]]),
        "repositories": repo_items
    }

def search_repositories_cli(repos_dir, catalog, query):
    """Buscador interactivo de repositorios con tolerancia a errores tipograficos (fuzzy search)"""
    if not query:
        print(f"\n{C_YELLOW}[?] No indicaste el termino a buscar.{C_RESET}")
        try:
            query = input(f"{C_BOLD}Nombre o termino a buscar: {C_RESET}").strip()
        except EOFError:
            query = ""
        if not query:
            return {"matches": []}

    matches = find_matching_repos(query, catalog, repos_dir=repos_dir, cutoff=0.45)
    print(f"\n{C_CYAN}=================================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  🔍 Resultados de búsqueda difusa para: '{query}' ({len(matches)} encontrados)     {C_RESET}")
    print(f"{C_CYAN}=================================================================================={C_RESET}")

    if not matches:
        print(f"\n  {C_RED}[!] No se encontraron repositorios similares a '{query}'.{C_RESET}")
        print(f"  {C_GRAY}Tip: Escribe {C_WHITE}/repos{C_GRAY} para ver el catalogo completo.{C_RESET}\n")
        return {"matches": []}

    display_candidates = matches[:10]
    for idx, m in enumerate(display_candidates, 1):
        e = m["entry"]
        pct = int(m["score"] * 100)
        status_tag = f"{C_GREEN}[✓ Clonado]{C_RESET}" if m.get("is_cloned") else f"{C_YELLOW}[☁ En nube]{C_RESET}"
        match_label = f"{C_GREEN}Exacta (100%){C_RESET}" if m["match_type"] == "exact" else f"{C_CYAN}{m['match_type']} ({pct}%){C_RESET}"
        print(f"  [{idx:2d}] {C_BOLD}{e.get('group', 'Personal')}/{e['name']:<26}{C_RESET} {status_tag} {match_label}")

    print(f"\n{C_GRAY}Opciones: Escribe el numero [1-{len(display_candidates)}] para abrir en VS Code, o presiona Enter para salir.{C_RESET}")
    try:
        ans = input(f"{C_BOLD}Abrir en VS Code > {C_RESET}").strip()
    except EOFError:
        ans = ""

    if ans.isdigit() and 1 <= int(ans) <= len(display_candidates):
        chosen = display_candidates[int(ans) - 1]["entry"]
        open_repo_in_vscode(repos_dir, catalog, chosen["name"])
    print("")
    return {"matches": [m["entry"] for m in matches]}

# ==============================================================================
# INTEGRACION CON VISUAL STUDIO CODE (/code <repo>)
# ==============================================================================
def open_repo_in_vscode(repos_dir, catalog, query):
    """Busca un repositorio por nombre o coincidencia difusa (fuzzy search) y lo abre en VS Code"""
    if not query:
        print(f"\n{C_YELLOW}[?] No indicaste el repositorio a abrir.{C_RESET}")
        try:
            query = input(f"{C_BOLD}Nombre o termino del proyecto a abrir en VS Code: {C_RESET}").strip()
        except EOFError:
            query = ""
        if not query:
            print(f"{C_GRAY}Operacion cancelada.{C_RESET}\n")
            return {"success": False, "error": "No query provided"}

    matches = find_matching_repos(query, catalog, repos_dir=repos_dir, cutoff=0.50)

    if not matches:
        print(f"\n{C_RED}[!] No se encontro ningun repositorio que coincida con '{query}'.{C_RESET}")
        print(f"{C_GRAY}Tip: Escribe {C_WHITE}/repos{C_GRAY} para ver el catalogo completo o {C_WHITE}/buscar <termino>{C_GRAY} para buscar.{C_RESET}\n")
        return {"success": False, "error": "Repo not found"}

    target = None
    top = matches[0]

    # 1. Coincidencia exacta o perfecta (score >= 0.95)
    if top["score"] >= 0.95:
        target = top["entry"]
    # 2. Solo 1 coincidencia cercana o ventaja clara respecto a la segunda
    elif len(matches) == 1 or (len(matches) > 1 and top["score"] >= 0.75 and (top["score"] - matches[1]["score"]) >= 0.15):
        best_name = top["entry"]["name"]
        best_grp = top["entry"].get("group", "")
        sim_pct = int(top["score"] * 100)
        print(f"\n{C_CYAN}[i] No se encontro exactamente '{query}'. Coincidencia mas cercana:{C_RESET}")
        print(f"    -> {C_BOLD}{best_grp}/{best_name}{C_RESET} ({sim_pct}% de similitud)")
        try:
            ans = input(f"{C_BOLD}¿Deseas abrir '{best_name}' en Visual Studio Code? [S/n]: {C_RESET}").strip().lower()
        except EOFError:
            ans = "s"
        if ans in ["", "s", "si", "y", "yes"]:
            target = top["entry"]
        else:
            print(f"{C_GRAY}Operacion cancelada.{C_RESET}\n")
            return {"success": False, "error": "Cancelled by user"}
    # 3. Multiples coincidencias difusas
    else:
        print(f"\n{C_BOLD}Se encontraron multiples repositorios similares a '{query}':{C_RESET}")
        display_candidates = matches[:8]
        for idx, m in enumerate(display_candidates, 1):
            e = m["entry"]
            sim_pct = int(m["score"] * 100)
            status_tag = f"{C_GREEN}[Clonado]{C_RESET}" if m.get("is_cloned") else f"{C_YELLOW}[En nube]{C_RESET}"
            print(f"  [{idx}] {C_BOLD}{e.get('group', '')}/{e['name']}{C_RESET} ({sim_pct}% coincidencia) {status_tag}")
        try:
            ans = input(f"\n{C_BOLD}Selecciona el numero a abrir (o Enter para cancelar): {C_RESET}").strip()
            if ans.isdigit() and 1 <= int(ans) <= len(display_candidates):
                target = display_candidates[int(ans) - 1]["entry"]
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
    opened = False
    try:
        subprocess.Popen(['code', full_path], shell=(os.name == 'nt'))
        opened = True
    except Exception:
        pass

    if not opened and sys.platform == 'darwin':
        for cand in [
            '/opt/homebrew/bin/code',
            '/usr/local/bin/code',
            '/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code'
        ]:
            if os.path.isfile(cand):
                try:
                    subprocess.Popen([cand, full_path])
                    opened = True
                    break
                except Exception:
                    pass
        if not opened:
            try:
                res = subprocess.run(['open', '-a', 'Visual Studio Code', full_path])
                if res.returncode == 0:
                    opened = True
            except Exception:
                pass

    elif not opened and sys.platform == 'win32':
        localapp = os.environ.get('LOCALAPPDATA', '')
        if localapp:
            win_code = os.path.join(localapp, 'Programs', 'Microsoft VS Code', 'bin', 'code.cmd')
            if os.path.isfile(win_code):
                try:
                    comspec = os.environ.get('COMSPEC', 'cmd.exe')
                    subprocess.Popen([comspec, '/c', win_code, full_path], shell=False)
                    opened = True
                except Exception:
                    pass

    if opened:
        print("")
        return {"success": True, "path": full_path, "name": target['name']}
    else:
        print(f"{C_RED}[ERROR] No se pudo iniciar Visual Studio Code (comando 'code'). Verifica que este instalado y en tu PATH.{C_RESET}\n")
        return {"success": False, "error": "Could not launch VS Code"}

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
    is_empty_repo = False
    stub_branch = False
    stub_remote = ""
    stub_commits = 0
    dirty_lines = []

    head_rev = run_cmd(["git", "rev-parse", "--verify", "HEAD"], cwd=full_path)

    if not head_rev:
        # Repositorio sin commits locales (unborn branch)
        if lines and lines[0].startswith("## No commits yet on "):
            branch_part = lines[0][21:].strip()
            branch = branch_part.split("...")[0].strip()
        else:
            branch = run_cmd(["git", "branch", "--show-current"], cwd=full_path) or entry.get("defaultBranch", "main")

        # Verificar si origin tiene commits para esta rama o la rama por defecto
        remote_sha = run_cmd(["git", "rev-parse", "--verify", f"origin/{branch}"], cwd=full_path)
        if not remote_sha:
            def_b = entry.get("defaultBranch", "main")
            remote_sha = run_cmd(["git", "rev-parse", "--verify", f"origin/{def_b}"], cwd=full_path)

        if remote_sha:
            c_cnt = run_cmd(["git", "rev-list", "--count", remote_sha], cwd=full_path)
            behind = int(c_cnt) if c_cnt.isdigit() else 1
        else:
            is_empty_repo = True
    else:
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

        # Detectar si la rama actual es un cascaron inicial (<= 2 commits)
        # mientras que el desarrollo activo esta en origin/develop u otra rama
        dirty_count_tmp = len(dirty_lines)
        if dirty_count_tmp == 0:
            c_cnt = run_cmd(["git", "rev-list", "--count", "HEAD"], cwd=full_path)
            if c_cnt in ("1", "2"):
                dev_rev = run_cmd(["git", "rev-parse", "--verify", "origin/develop"], cwd=full_path)
                if dev_rev:
                    dev_cnt = run_cmd(["git", "rev-list", "--count", "origin/develop"], cwd=full_path)
                    if dev_cnt and dev_cnt.isdigit() and int(dev_cnt) > int(c_cnt):
                        stub_branch = True
                        stub_remote = "develop"
                        stub_commits = int(dev_cnt)

    dirty_count = len(dirty_lines)

    # Clasificar estado
    if is_empty_repo:
        status = "EMPTY_REPO"
    elif dirty_count > 0 and ahead > 0:
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
        "is_empty_repo": is_empty_repo,
        "stub_branch": stub_branch,
        "stub_remote": stub_remote,
        "stub_commits": stub_commits,
        "url": entry.get("url", "")
    }

def audit_all_repos(repos_dir, catalog, with_fetch=False, max_workers=16, org_filter=None, auto_reindex=True):
    """Audita los repositorios en paralelo ultra-rapido respetando filtros de organizacion"""
    t0 = time.time()

    # Auto-escaneo preventivo si se detectan rutas invalidas en entradas previamente clonadas
    if auto_reindex and catalog and repos_dir and os.path.isdir(repos_dir):
        has_invalid_paths = False
        for c in catalog:
            rel_p = c.get("path", f"{c.get('group', 'Personal')}/{c.get('name', '')}").replace("/", os.sep)
            full_p = os.path.join(repos_dir, rel_p)
            if c.get("is_cloned", True) and not os.path.exists(full_p):
                has_invalid_paths = True
                break
        if has_invalid_paths:
            try:
                reindex_and_sync_catalog(
                    repos_dir=repos_dir,
                    catalog=catalog,
                    sync_remote_transfers=with_fetch,
                    auto_move_physical=True,
                    quiet=True
                )
            except Exception:
                pass

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
    empty_list       = [r for r in results if r["status"] == "EMPTY_REPO"]
    stub_list        = [r for r in results if r.get("stub_branch")]

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
        "empty": empty_list,
        "stub": stub_list,
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

    if audit.get('empty'):
        print(f"  * {C_GRAY}Repositorios vacios en GitHub ({len(audit['empty'])}):{C_RESET}")
        for r in audit['empty']:
            print(f"      - {C_BOLD}{r['group']}/{r['name']}{C_RESET}: {C_GRAY}Sin commits aun en GitHub (creado vacio){C_RESET}")

    if audit.get('stub'):
        print(f"  * {C_CYAN}En rama inicial (codigo en develop) ({len(audit['stub'])}):{C_RESET}")
        for r in audit['stub']:
            print(f"      - {C_BOLD}{r['group']}/{r['name']}{C_RESET} [{r['branch']}]: {C_CYAN}Codigo activo en 'origin/{r['stub_remote']}' ({r['stub_commits']} commits). Usa /gitflow para activar.{C_RESET}")

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
        matched = [r for r in dirty_repos if r["name"].lower() == target_repo.lower()]
        if not matched:
            matches = find_matching_repos(target_repo, [r for r in catalog if r["name"] in [d["name"] for d in dirty_repos]], repos_dir=repos_dir, cutoff=0.55)
            if matches:
                best_name = matches[0]["entry"]["name"]
                matched = [r for r in dirty_repos if r["name"].lower() == best_name.lower()]
        dirty_repos = matched

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
    gitflow_pending = []
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
        if gf_info["has_local_develop"]:
            gitflow_ok.append(entry_data)
        elif gf_info["has_remote_develop"]:
            gitflow_pending.append(entry_data)
        else:
            gitflow_missing.append(entry_data)

    print(f"{C_BOLD}Estado de Gitflow en tus repositorios clonados:{C_RESET}")
    print(f"  * {C_GREEN}Con Gitflow activo (rama 'develop' local):{C_RESET} {len(gitflow_ok)}")
    if gitflow_pending:
        print(f"  * {C_CYAN}Con 'develop' en GitHub (pendiente de checkout local):{C_RESET} {len(gitflow_pending)}")
    print(f"  * {C_YELLOW}Sin Gitflow (solo rama '{gitflow_missing[0]['info']['base_branch'] if gitflow_missing else 'main'}'):{C_RESET} {len(gitflow_missing)}\n")

    # Si hay repositorios con develop en GitHub pero no en local, permitir activarlos directamente
    if gitflow_pending:
        print(f"{C_CYAN}[i] Repositorios con rama 'develop' existente en GitHub no activa en este equipo:{C_RESET}")
        for idx, p in enumerate(gitflow_pending[:8], 1):
            print(f"  [{idx:2d}] {p['entry'].get('group')}/{p['entry']['name']} (rama actual: {p['info']['current_branch']})")
        if len(gitflow_pending) > 8:
            print(f"  ... y {len(gitflow_pending)-8} mas")
        try:
            ans_p = input(f"\n{C_BOLD}¿Deseas activar/hacer checkout de 'develop' en estos {len(gitflow_pending)} repositorios? [S/n]: {C_RESET}").strip().lower()
        except (EOFError, KeyboardInterrupt):
            ans_p = "n"
        if ans_p in ["", "s", "si", "y", "yes"]:
            for p in gitflow_pending:
                res = implement_gitflow_on_repo(p["full_path"], p["entry"]["name"])
                if res.get("success"):
                    print(f"  {C_GREEN}[OK] {p['entry']['name']}: Cambiado a 'develop' desde origin/develop.{C_RESET}")
                else:
                    print(f"  {C_RED}[!] {p['entry']['name']}: {res.get('error')}{C_RESET}")
            print("")

    if not gitflow_missing:
        print(f"{C_GREEN}[OK] ¡Excelente! Todos tus repositorios tienen implementada la rama 'develop'.{C_RESET}\n")
        return {"configured": 0}

    # Si se especifico un repositorio puntual
    if target_repo and target_repo.lower() != "all":
        candidates = [m for m in gitflow_missing if m["entry"]["name"].lower() == target_repo.lower()]
        if not candidates:
            gf_matches = find_matching_repos(target_repo, [m["entry"] for m in gitflow_missing], repos_dir=repos_dir, cutoff=0.55)
            if gf_matches:
                best_name = gf_matches[0]["entry"]["name"]
                candidates = [m for m in gitflow_missing if m["entry"]["name"].lower() == best_name.lower()]
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
    """Crea un commit con los cambios pendientes en un repositorio especifico (con soporte fuzzy)"""
    match = None
    for entry in catalog:
        if entry["name"].lower() == repo_name.lower():
            match = entry
            break

    if not match:
        matches = find_matching_repos(repo_name, catalog, repos_dir=repos_dir, cutoff=0.55)
        if matches:
            top = matches[0]
            sim_pct = int(top["score"] * 100)
            print(f"{C_CYAN}[i] Repositorio detectado por coincidencia aproximada: {top['entry'].get('group')}/{top['entry']['name']} ({sim_pct}% de similitud){C_RESET}")
            match = top["entry"]

    if not match:
        print(f"{C_RED}[ERROR] Repositorio '{repo_name}' no encontrado en repos.json ni en disco.{C_RESET}")
        print(f"{C_GRAY}Tip: Usa /repos para ver el listado de proyectos disponibles o /buscar <termino>.{C_RESET}\n")
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
    # Auto-reindexar antes de clonar/pull para detectar repos movidos en disco o transferidos en GitHub
    try:
        reindex_res = reindex_and_sync_catalog(
            repos_dir=repos_dir,
            catalog=catalog,
            sync_remote_transfers=True,
            auto_move_physical=True,
            quiet=True
        )
        if reindex_res.get("physical_moves") or reindex_res.get("relocated_repos"):
            moved_total = len(reindex_res.get("physical_moves", [])) + len(reindex_res.get("relocated_repos", []))
            print(f"  {C_GREEN}[AUTO-REINDEX] Se detectaron y actualizaron {moved_total} repositorio(s) reubicado(s) antes de sincronizar.{C_RESET}")
    except Exception:
        pass
    audit = audit_all_repos(repos_dir, catalog, with_fetch=True, org_filter=org_filter, auto_reindex=False)

    cloned = []
    if auto_clone and audit["not_cloned"]:
        for item in audit["not_cloned"]:
            target = item["full_path"]
            os.makedirs(os.path.dirname(target), exist_ok=True)
            print(f"  {C_MAGENTA}[CLONE] Descargando {item['group']}/{item['name']}...{C_RESET}")
            res = subprocess.run(["git", "clone", item["url"], target])
            if res.returncode == 0:
                cloned.append(item["name"])
                # Si origin/develop tiene mas commits que la rama por defecto, activar develop
                try:
                    c_main = run_cmd(["git", "rev-list", "--count", "HEAD"], cwd=target)
                    c_dev = run_cmd(["git", "rev-list", "--count", "origin/develop"], cwd=target)
                    if c_dev and c_dev.isdigit() and int(c_dev) > int(c_main or '0'):
                        run_cmd(["git", "checkout", "-b", "develop", "origin/develop"], cwd=target)
                        print(f"    {C_CYAN}-> Detectado Gitflow activo: Cambiado automaticamente a rama 'develop' ({c_dev} commits).{C_RESET}")
                except Exception:
                    pass

    pulled = []
    failed_pull = []

    def pull_one(r):
        if r["status"] == "BEHIND" and r["dirty_count"] == 0 and not r.get("is_empty_repo"):
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
    """Clona un repositorio puntual o una organizacion entera bajo demanda con busqueda inteligente"""
    if not target_query:
        print(f"\n{C_YELLOW}[?] No indicaste que repositorio u organizacion clonar.{C_RESET}")
        print(f"{C_GRAY}Tip: Escribe /repos para ver todos tus proyectos o /disponibles para ver los que faltan en este equipo.{C_RESET}")
        try:
            target_query = input(f"{C_BOLD}Nombre a descargar: {C_RESET}").strip()
        except EOFError:
            target_query = ""
        if not target_query:
            print(f"{C_GRAY}Operacion cancelada.{C_RESET}\n")
            return {"success": False, "error": "No target provided"}

    q = target_query.strip().lower()

    # 1. Comprobar si coincide con una organizacion entera (exacta o difusa)
    all_orgs = get_active_orgs(repos_dir)
    matched_org = find_matching_org(q, all_orgs)

    if matched_org:
        org_matches = [c for c in catalog if c.get("group", "").lower() == matched_org.lower()]
        missing_in_org = []
        for item in org_matches:
            target_p = os.path.join(repos_dir, item.get('path', f"{item['group']}/{item['name']}").replace('/', os.sep))
            if not os.path.isdir(target_p):
                missing_in_org.append((item, target_p))

        if not missing_in_org:
            print(f"\n{C_GREEN}[OK] Todos los repositorios de la organizacion '{matched_org}' ya estan clonados localmente.{C_RESET}\n")
            return {"success": True, "already_cloned": True}

        print(f"\n{C_MAGENTA}Descargando {len(missing_in_org)} repositorios de '{matched_org}'...{C_RESET}")
        cloned_count = 0
        for item, tp in missing_in_org:
            os.makedirs(os.path.dirname(tp), exist_ok=True)
            print(f"  * Clonando {item['name']}...")
            res = subprocess.run(["git", "clone", item['url'], tp])
            if res.returncode == 0:
                cloned_count += 1
                try:
                    c_main = run_cmd(["git", "rev-list", "--count", "HEAD"], cwd=tp)
                    c_dev = run_cmd(["git", "rev-list", "--count", "origin/develop"], cwd=tp)
                    if c_dev and c_dev.isdigit() and int(c_dev) > int(c_main or '0'):
                        run_cmd(["git", "checkout", "-b", "develop", "origin/develop"], cwd=tp)
                except Exception:
                    pass
        print(f"\n{C_GREEN}[OK] Descargados {cloned_count} repositorios de '{matched_org}'.{C_RESET}\n")
        return {"success": True, "cloned": cloned_count}

    # 2. Comprobar si coincide con un repositorio puntual con busqueda difusa
    matches = find_matching_repos(target_query, catalog, repos_dir=repos_dir, cutoff=0.50)
    if not matches:
        print(f"\n{C_RED}[!] No se encontro ningun repositorio en el catalogo que coincida con '{target_query}'.{C_RESET}")
        print(f"{C_GRAY}Tip: Escribe /repos para ver el catalogo completo o /disponibles para los que faltan.{C_RESET}\n")
        return {"success": False, "error": "Not found in catalog"}

    chosen = None
    top = matches[0]
    if top["score"] >= 0.95:
        chosen = top["entry"]
    elif len(matches) == 1 or (len(matches) > 1 and top["score"] >= 0.75 and (top["score"] - matches[1]["score"]) >= 0.15):
        best_name = top["entry"]["name"]
        best_grp = top["entry"].get("group", "")
        sim_pct = int(top["score"] * 100)
        print(f"\n{C_CYAN}[i] No se encontro exactamente '{target_query}'. Coincidencia mas cercana:{C_RESET}")
        print(f"    -> {C_BOLD}{best_grp}/{best_name}{C_RESET} ({sim_pct}% de similitud)")
        try:
            ans = input(f"{C_BOLD}¿Deseas descargar '{best_name}'? [S/n]: {C_RESET}").strip().lower()
        except EOFError:
            ans = "s"
        if ans in ["", "s", "si", "y", "yes"]:
            chosen = top["entry"]
        else:
            print(f"{C_GRAY}Operacion cancelada.{C_RESET}\n")
            return {"success": False, "error": "Cancelled"}
    else:
        print(f"\n{C_BOLD}Se encontraron multiples repositorios similares a '{target_query}':{C_RESET}")
        for idx, m in enumerate(matches[:8], 1):
            e = m["entry"]
            sim_pct = int(m["score"] * 100)
            status_tag = f"{C_GREEN}[Ya clonado]{C_RESET}" if m.get("is_cloned") else f"{C_YELLOW}[Disponible para clonar]{C_RESET}"
            print(f"  [{idx}] {C_BOLD}{e.get('group', '')}/{e['name']}{C_RESET} ({sim_pct}% coincidencia) {status_tag}")
        try:
            ans = input(f"\n{C_BOLD}Selecciona el numero a descargar: {C_RESET}").strip()
            if ans.isdigit() and 1 <= int(ans) <= min(len(matches), 8):
                chosen = matches[int(ans) - 1]["entry"]
        except EOFError:
            return {"success": False}

    if not chosen:
        print(f"{C_YELLOW}[!] Operacion cancelada.{C_RESET}\n")
        return {"success": False, "error": "Cancelled"}

    target_p = os.path.join(repos_dir, chosen.get('path', f"{chosen.get('group')}/{chosen['name']}").replace('/', os.sep))

    if os.path.isdir(target_p):
        print(f"\n{C_GREEN}[OK] El repositorio {chosen.get('group')}/{chosen['name']} ya existe en este equipo.{C_RESET}\n")
        return {"success": True, "already_exists": True}

    os.makedirs(os.path.dirname(target_p), exist_ok=True)
    print(f"\n{C_MAGENTA}[CLONE] Descargando {chosen.get('group')}/{chosen['name']} ({chosen['url']})...{C_RESET}")
    res = subprocess.run(["git", "clone", chosen['url'], target_p])
    if res.returncode == 0:
        print(f"{C_GREEN}[OK] Repositorio clonado exitosamente en: {target_p}{C_RESET}")
        try:
            c_main = run_cmd(["git", "rev-list", "--count", "HEAD"], cwd=target_p)
            c_dev = run_cmd(["git", "rev-list", "--count", "origin/develop"], cwd=target_p)
            if c_dev and c_dev.isdigit() and int(c_dev) > int(c_main or '0'):
                run_cmd(["git", "checkout", "-b", "develop", "origin/develop"], cwd=target_p)
                print(f"  {C_CYAN}[GITFLOW] Cambiado automaticamente a la rama activa 'develop' ({c_dev} commits).{C_RESET}")
        except Exception:
            pass
        print("")
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
# AUTO-DESCUBRIMIENTO, REINDEXACION Y RECONCILIACION FISICA/REMOTA DEL CATALOGO
# ==============================================================================
IGNORED_SCAN_DIRS = {
    "node_modules", ".cache", ".sync", "_sync", "_gitdoctor", "gitdoctor",
    "repos-sync", ".venv", "venv", "env", "virtualenv", "dist", "build",
    ".next", ".turbo", "__pycache__", ".firebase", ".vscode", ".idea",
    "target", "out", "coverage", ".gradle", ".pytest_cache", ".mypy_cache"
}

def _read_git_config_remote(repo_path):
    """Lee la URL remota origin desde git o directamente desde .git/config como fallback rapido."""
    remote = run_cmd(["git", "remote", "get-url", "origin"], cwd=repo_path, timeout=5)
    if remote:
        return remote
    cfg_path = os.path.join(repo_path, ".git", "config")
    if os.path.isfile(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8", errors="ignore") as f:
                in_origin = False
                for line in f:
                    s = line.strip()
                    if s.startswith("[") and s.endswith("]"):
                        in_origin = (s.lower() == '[remote "origin"]')
                    elif in_origin and s.lower().startswith("url"):
                        parts = s.split("=", 1)
                        if len(parts) == 2:
                            return parts[1].strip()
        except Exception:
            pass
    return ""

def _extract_repo_slug_and_owner(url):
    """Extrae (owner, repo_name) normalizados desde una URL Git (HTTPS o SSH)."""
    if not url:
        return "", ""
    u = normalize_url(url)
    for prefix in ("https://github.com/", "https://gitlab.com/", "https://bitbucket.org/"):
        if u.startswith(prefix):
            rest = u[len(prefix):].strip("/")
            parts = [p for p in rest.split("/") if p]
            if len(parts) >= 2:
                return parts[0], parts[-1]
    parts = [p for p in re.split(r"[:/]", u) if p]
    if len(parts) >= 2:
        return parts[-2], parts[-1]
    return "", ""

def scan_local_disk_repos(repos_dir, script_dir=None, max_depth=3):
    """
    Escanea recursivamente el directorio raiz de repositorios (hasta max_depth niveles)
    buscando carpetas que contengan un directorio o archivo `.git`.
    Ignora carpetas del sistema, temporales, caches y la propia instalacion de GitDoctor.
    """
    if script_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))

    discovered = []
    if not repos_dir or not os.path.isdir(repos_dir):
        return discovered

    repos_dir_abs = os.path.abspath(repos_dir)

    def _walk(current_dir, depth):
        if depth > max_depth:
            return
        try:
            entries = sorted(os.scandir(current_dir), key=lambda e: e.name.lower())
        except Exception:
            return

        for entry in entries:
            try:
                if not entry.is_dir(follow_symlinks=False):
                    continue
            except Exception:
                continue

            name = entry.name
            if name.startswith(".") or name.lower() in IGNORED_SCAN_DIRS:
                continue

            full_path = os.path.abspath(entry.path)
            if is_gitdoctor_path(full_path, script_dir):
                continue

            git_marker = os.path.join(full_path, ".git")
            if os.path.isdir(git_marker) or os.path.isfile(git_marker):
                rel_path = os.path.relpath(full_path, repos_dir_abs).replace("\\", "/")
                rel_parts = [p for p in rel_path.split("/") if p]
                repo_name = rel_parts[-1] if rel_parts else name
                group = rel_parts[0] if len(rel_parts) >= 2 else "Personal"

                remote_url = _read_git_config_remote(full_path)
                norm_remote = normalize_url(remote_url)
                if norm_remote.endswith("/gitdoctor") or norm_remote.endswith("/repos-sync"):
                    continue

                branch = run_cmd(["git", "branch", "--show-current"], cwd=full_path, timeout=5)
                if not branch:
                    branch = run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=full_path, timeout=5) or "main"
                head_commit = run_cmd(["git", "rev-parse", "--short", "HEAD"], cwd=full_path, timeout=5) or ""

                discovered.append({
                    "name": repo_name,
                    "group": group,
                    "is_loose_root": (len(rel_parts) == 1),
                    "path": rel_path,
                    "full_path": full_path,
                    "url": remote_url,
                    "norm_url": norm_remote,
                    "branch": branch,
                    "head_commit": head_commit
                })
                # No descender dentro de un repositorio Git ya encontrado
                continue

            if depth < max_depth:
                _walk(full_path, depth + 1)

    _walk(repos_dir_abs, 1)
    return discovered

def _fetch_github_remote_org_map(gh_info=None, active_orgs=None):
    """
    Construye un mapa {repo_name_lower: [{group, url, name, owner, defaultBranch}, ...]} consultando
    las organizaciones de GitHub para detectar si un repositorio fue transferido de organizacion en GitHub,
    diferenciando repositorios homonimos legitimos en distintas organizaciones.
    """
    remote_map = {}
    if not shutil.which("gh"):
        return remote_map

    if gh_info is None:
        gh_info = get_github_status()
    if not gh_info.get("logged_in"):
        return remote_map

    user_login = (gh_info.get("user") or "").lower()
    orgs_to_query = ["Personal"]
    for o in (active_orgs or gh_info.get("orgs") or []):
        if o not in orgs_to_query:
            orgs_to_query.append(o)

    def _query_org(org_name):
        try:
            if org_name == "Personal":
                cmd = ["gh", "repo", "list", "--limit", "300", "--json", "name,nameWithOwner,url,defaultBranchRef,owner"]
            else:
                cmd = ["gh", "repo", "list", org_name, "--limit", "300", "--json", "name,nameWithOwner,url,defaultBranchRef,owner"]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=15)
            if res.returncode == 0:
                return org_name, json.loads(res.stdout.decode("utf-8", errors="replace"))
        except Exception:
            pass
        return org_name, []

    with ThreadPoolExecutor(max_workers=min(8, max(1, len(orgs_to_query)))) as ex:
        results = list(ex.map(_query_org, orgs_to_query))

    for org_name, repo_list in results:
        for r in repo_list:
            r_name = r.get("name", "")
            if not r_name or r_name.lower() in ("gitdoctor", "repos-sync", "_sync"):
                continue
            owner_login = (r.get("owner", {}) or {}).get("login", "") or org_name
            resolved_group = "Personal" if owner_login.lower() in (user_login, "davidmmora", "personal") else owner_login
            def_branch = (r.get("defaultBranchRef") or {}).get("name") or "main"
            remote_Url = r.get("url", "")
            if remote_Url and not remote_Url.endswith(".git"):
                remote_Url = remote_Url + ".git"
            item_meta = {
                "name": r_name,
                "group": resolved_group,
                "owner": owner_login,
                "url": remote_Url,
                "norm_url": normalize_url(remote_Url),
                "defaultBranch": def_branch
            }
            remote_map.setdefault(r_name.lower(), []).append(item_meta)
    return remote_map

def _atomic_write_json(target_path, data):
    """Escribe un archivo JSON de forma atomica con sangria limpia de 4 espacios y UTF-8."""
    parent_dir = os.path.dirname(os.path.abspath(target_path))
    os.makedirs(parent_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".gitdoc_cat_", suffix=".json.tmp", dir=parent_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            json.dump(data, tmp_file, indent=4, ensure_ascii=False)
            tmp_file.write("\n")
        os.replace(tmp_path, target_path)
    except Exception:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise

def reindex_and_sync_catalog(
    repos_dir,
    catalog=None,
    catalog_file=None,
    script_dir=None,
    sync_remote_transfers=True,
    auto_move_physical=True,
    prune_deleted_remotes=False,
    gh_info=None,
    active_orgs=None,
    interactive=True,
    quiet=False
):
    """
    Escanea recursivamente el disco (`D:\\Repos` o `~/Repos`), detecta repositorios que fueron:
      1) Transferidos de organizacion en GitHub (moviendo fisicamente su carpeta local y actualizando `git remote`),
      2) Movidos manualmente de carpeta o renombrados en el disco local,
      3) Agregados manualmente en disco sin estar en el catalogo,
      4) Eliminados del disco (marcando `is_cloned: False` o limpiando huerfanos),
    y sincroniza de forma atomica el catalogo (`repos.local.json` / `_sync/repos.json`).

    Retorna un diccionario diagnostico con:
      - relocated_repos: lista de repositorios reubicados (origen -> destino)
      - physical_moves: lista de carpetas movidas fisicamente en disco tras cambio en GitHub
      - newly_discovered: lista de nuevos repositorios descubiertos e indexados
      - orphaned_cleaned: lista de rutas huerfanas actualizadas/limpiadas
      - active_total: total de repositorios activos en el catalogo
      - cloned_total: total de repositorios clonados fisicamente en disco
      - catalog: lista actualizada en memoria
    """
    if script_dir is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))

    if catalog_file is None:
        cat_local = os.path.join(script_dir, "repos.local.json")
        cat_master = os.path.join(script_dir, "repos.json")
        catalog_file = cat_local if os.path.isfile(cat_local) else cat_master

    if catalog is None:
        catalog = []
        if os.path.isfile(catalog_file):
            try:
                with open(catalog_file, "r", encoding="utf-8-sig") as f:
                    catalog = json.load(f)
            except Exception:
                catalog = []

    if not quiet:
        print(f"\n{C_CYAN}================================================================{C_RESET}")
        print(f"{C_WHITE}{C_BOLD}  🔍 GitDoctor -- Auto-Descubrimiento y Reindexacion Clinica   {C_RESET}")
        print(f"{C_GRAY}  Escaneando disco (max 3 niveles): {repos_dir}{C_RESET}")
        print(f"{C_CYAN}================================================================{C_RESET}")

    # 1. Escaneo recursivo en disco (hasta 3 niveles)
    disk_repos = scan_local_disk_repos(repos_dir, script_dir=script_dir, max_depth=3)

    # 2. Deteccion de transferencias de organizacion en GitHub -> Movimiento fisico en disco
    physical_moves = []
    remote_org_map = {}
    if sync_remote_transfers:
        if not quiet:
            print(f"{C_CYAN}[*] Verificando posibles transferencias de organizacion en GitHub...{C_RESET}")
        remote_org_map = _fetch_github_remote_org_map(gh_info=gh_info, active_orgs=active_orgs)

        if remote_org_map:
            for d_repo in disk_repos:
                r_key = d_repo["name"].lower()
                candidates = remote_org_map.get(r_key, [])
                if not candidates:
                    continue

                current_group = d_repo["group"]
                # Si el repositorio NO esta suelto en la raiz y sigue existiendo en su organizacion actual en GitHub, no fue transferido
                if (not d_repo.get("is_loose_root")) and any(c["group"].lower() == current_group.lower() for c in candidates):
                    continue

                # Si ya existe otra carpeta en disco con el mismo nombre dentro de target_group (y no es esta misma), no mover encima
                if any(
                    other["full_path"] != d_repo["full_path"]
                    and other["name"].lower() == r_key
                    and other["group"].lower() == candidates[0]["group"].lower()
                    for other in disk_repos
                ):
                    continue

                # Cuando existe en exactamente una organizacion en GitHub (o estaba suelto en la raiz), moverlo automaticamente
                if len(candidates) == 1:
                    gh_meta = candidates[0]
                    target_group = gh_meta["group"]

                    if target_group.lower() != current_group.lower() or d_repo.get("is_loose_root"):
                        new_rel_path = f"{target_group}/{d_repo['name']}"
                        new_full_path = os.path.abspath(os.path.join(repos_dir, target_group, d_repo["name"]))
                        old_full_path = d_repo["full_path"]
                        old_rel_path = d_repo["path"]

                        if auto_move_physical and os.path.abspath(old_full_path) != new_full_path:
                            if not os.path.exists(new_full_path):
                                try:
                                    os.makedirs(os.path.dirname(new_full_path), exist_ok=True)
                                    shutil.move(old_full_path, new_full_path)
                                    # Actualizar el remote origin local para apuntar a la nueva organizacion
                                    if gh_meta.get("url"):
                                        run_cmd(["git", "remote", "set-url", "origin", gh_meta["url"]], cwd=new_full_path, timeout=5)
                                    d_repo["group"] = target_group
                                    d_repo["is_loose_root"] = False
                                    d_repo["path"] = new_rel_path
                                    d_repo["full_path"] = new_full_path
                                    if gh_meta.get("url"):
                                        d_repo["url"] = gh_meta["url"]
                                        d_repo["norm_url"] = gh_meta["norm_url"]
                                    physical_moves.append({
                                        "name": d_repo["name"],
                                        "from_path": old_rel_path,
                                        "to_path": new_rel_path,
                                        "new_url": gh_meta.get("url", d_repo["url"])
                                    })
                                    # Limpiar carpeta de organizacion anterior si quedo vacia
                                    old_parent = os.path.dirname(old_full_path)
                                    if os.path.abspath(old_parent) != os.path.abspath(repos_dir) and os.path.isdir(old_parent) and not os.listdir(old_parent):
                                        try:
                                            os.rmdir(old_parent)
                                        except Exception:
                                            pass
                                except Exception as e:
                                    if not quiet:
                                        print(f"  {C_RED}[!] No se pudo mover fisicamente {old_rel_path} -> {new_rel_path}: {e}{C_RESET}")
                            else:
                                if not quiet:
                                    print(f"  {C_YELLOW}[!] Destino ya existe en disco ({new_rel_path}), se conserva ubicacion actual.{C_RESET}")

    # 2.5. Si hay un repositorio local que NO existe en ninguna organizacion de GitHub (sin remote o no subido aun)
    #      o esta suelto en la raiz sin organizacion, preguntar interactivamente a que org moverlo y si subirlo a GitHub.
    published_to_github = []
    if interactive and not quiet:
        org_choices = list(active_orgs) if active_orgs else list(DEFAULT_ORGS)
        if "Personal" not in org_choices:
            org_choices.append("Personal")

        for d_repo in disk_repos:
            r_key = d_repo["name"].lower()
            in_github = bool(remote_org_map.get(r_key)) if remote_org_map else bool(d_repo.get("url"))
            is_loose = d_repo.get("is_loose_root", False)
            has_remote = bool(d_repo.get("url"))

            # Caso A: Esta suelto en la raiz (ej. D:\Repos\mi-proyecto) y no estaba en GitHub
            was_loose = is_loose
            if is_loose:
                print(f"\n{C_YELLOW}[!] El repositorio '{d_repo['name']}' esta suelto en la raiz ({d_repo['path']}) y no pertenece a ninguna organizacion.{C_RESET}")
                for idx, o_name in enumerate(org_choices, 1):
                    print(f"    [{idx:2d}] {o_name}")
                print(f"    [ 0] Omitir movimiento")
                try:
                    ans_org = input(f"  {C_BOLD}¿A que organizacion deseas mover '{d_repo['name']}'? (Enter para Personal): {C_RESET}").strip()
                except (EOFError, KeyboardInterrupt):
                    ans_org = "0"

                chosen_org = None
                if ans_org == "":
                    chosen_org = "Personal"
                elif ans_org.isdigit() and 1 <= int(ans_org) <= len(org_choices):
                    chosen_org = org_choices[int(ans_org) - 1]

                if chosen_org:
                    new_rel = f"{chosen_org}/{d_repo['name']}"
                    new_full = os.path.abspath(os.path.join(repos_dir, chosen_org, d_repo["name"]))
                    if not os.path.exists(new_full):
                        try:
                            os.makedirs(os.path.dirname(new_full), exist_ok=True)
                            shutil.move(d_repo["full_path"], new_full)
                            physical_moves.append({
                                "name": d_repo["name"],
                                "from_path": d_repo["path"],
                                "to_path": new_rel,
                                "new_url": d_repo.get("url", "")
                            })
                            d_repo["group"] = chosen_org
                            d_repo["path"] = new_rel
                            d_repo["full_path"] = new_full
                            d_repo["is_loose_root"] = False
                            print(f"  {C_GREEN}[OK] Movido fisicamente a: {new_rel}{C_RESET}")
                        except Exception as e:
                            print(f"  {C_RED}[!] Error al mover carpeta: {e}{C_RESET}")

            # Caso B: No tiene remote configurado (o estaba suelto sin existir en GitHub) -> preguntar si lo sube a GitHub
            if (not has_remote) or (was_loose and remote_org_map and not in_github):
                target_org = d_repo["group"]
                print(f"\n{C_YELLOW}[?] El repositorio local '{target_org}/{d_repo['name']}' no existe aun en GitHub en ninguna organizacion.{C_RESET}")
                try:
                    ans_pub = input(f"  {C_BOLD}¿Deseas crearlo y subirlo a GitHub (privado) bajo '{target_org}/{d_repo['name']}' ahora? [S/n]: {C_RESET}").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    ans_pub = "n"

                if ans_pub in ("", "s", "si", "y", "yes"):
                    # Asegurar que tenga al menos un commit antes de hacer push
                    if not d_repo.get("head_commit"):
                        subprocess.run(["git", "add", "-A"], cwd=d_repo["full_path"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        commit_msg = f"chore: initial commit\n\n{COPILOT_TRAILER}"
                        subprocess.run(["git", "commit", "-m", commit_msg], cwd=d_repo["full_path"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        d_repo["head_commit"] = run_cmd(["git", "rev-parse", "--short", "HEAD"], cwd=d_repo["full_path"], timeout=5) or ""

                    gh_target = d_repo["name"] if target_org.lower() == "personal" else f"{target_org}/{d_repo['name']}"
                    # Si ya tenia un remote origin huerfano, removerlo antes de --remote=origin
                    if has_remote:
                        subprocess.run(["git", "remote", "remove", "origin"], cwd=d_repo["full_path"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                    print(f"  {C_CYAN}[*] Creando y subiendo repositorio privado '{gh_target}' en GitHub...{C_RESET}")
                    create_cmd = [
                        "gh", "repo", "create", gh_target,
                        "--private",
                        f"--source={d_repo['full_path']}",
                        "--remote=origin",
                        "--push"
                    ]
                    res_pub = subprocess.run(create_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    if res_pub.returncode == 0:
                        created_url = _read_git_config_remote(d_repo["full_path"])
                        if created_url and not created_url.endswith(".git"):
                            created_url = created_url + ".git"
                        d_repo["url"] = created_url
                        d_repo["norm_url"] = normalize_url(created_url)
                        published_to_github.append(f"{target_org}/{d_repo['name']}")
                        print(f"  {C_GREEN}[OK] ¡Subido exitosamente a GitHub!: {created_url}{C_RESET}")
                    else:
                        err_msg = res_pub.stderr.decode("utf-8", errors="ignore").strip()
                        print(f"  {C_RED}[ERROR] No se pudo subir a GitHub: {err_msg}{C_RESET}")

    # 3. Indexar repositorios encontrados en disco por URL normalizada, por (org, nombre) y por nombre
    disk_by_url = {}
    disk_by_org_name = {}
    disk_by_name = {}
    for d in disk_repos:
        if d["norm_url"]:
            disk_by_url[d["norm_url"]] = d
        disk_by_org_name[(d["group"].lower(), d["name"].lower())] = d
        disk_by_name.setdefault(d["name"].lower(), []).append(d)

    relocated_repos = []
    newly_discovered = []
    orphaned_cleaned = []
    matched_disk_paths = set()
    updated_catalog = []

    # Filtrar entradas de plantilla dummy si ya hay repos reales en disco
    dummy_names = {"mi-proyecto-backend", "mi-proyecto-frontend", "mi-libreria-utilidades"}
    has_real_repos = any(d["name"] not in dummy_names for d in disk_repos)

    for entry in catalog:
        e_name = entry.get("name", "")
        if not e_name or e_name.lower() in ("gitdoctor", "repos-sync", "_sync"):
            continue
        if has_real_repos and e_name in dummy_names and os.path.basename(catalog_file) == "repos.local.json":
            continue

        e_url = entry.get("url", "")
        e_norm_url = normalize_url(e_url)
        old_group = entry.get("group", "Personal")
        old_path = entry.get("path", f"{old_group}/{e_name}").replace("\\", "/")

        # Buscar coincidencia en disco: 1° por (org, nombre) exacto en disco, 2° por URL remota, 3° por nombre unico no asignado
        matched_disk = None
        if (old_group.lower(), e_name.lower()) in disk_by_org_name:
            cand = disk_by_org_name[(old_group.lower(), e_name.lower())]
            if cand["full_path"] not in matched_disk_paths:
                matched_disk = cand
        if not matched_disk and e_norm_url and e_norm_url in disk_by_url and disk_by_url[e_norm_url]["full_path"] not in matched_disk_paths:
            matched_disk = disk_by_url[e_norm_url]
        if not matched_disk and e_name.lower() in disk_by_name:
            unmatched_cands = [c for c in disk_by_name[e_name.lower()] if c["full_path"] not in matched_disk_paths]
            if len(unmatched_cands) == 1:
                matched_disk = unmatched_cands[0]

        if matched_disk:
            matched_disk_paths.add(matched_disk["full_path"])
            new_path = matched_disk["path"]
            new_group = matched_disk["group"]
            new_url = matched_disk["url"] or e_url

            # Si el usuario movio la carpeta manualmente en el disco (ej. Personal/x -> th-mex/x)
            # y la URL remota en GitHub confirma que pertenece a new_group, actualizar git remote
            gh_cands = remote_org_map.get(e_name.lower(), [])
            gh_match = next((c for c in gh_cands if c["group"].lower() == new_group.lower()), None)
            if gh_match and gh_match.get("url") and normalize_url(gh_match["url"]) != normalize_url(new_url):
                new_url = gh_match["url"]
                run_cmd(["git", "remote", "set-url", "origin", new_url], cwd=matched_disk["full_path"], timeout=5)

            if old_path != new_path or old_group != new_group:
                relocated_repos.append({
                    "name": matched_disk["name"],
                    "from_group": old_group,
                    "to_group": new_group,
                    "from_path": old_path,
                    "to_path": new_path,
                    "url": new_url
                })

            new_entry = dict(entry)
            new_entry["name"] = matched_disk["name"]
            new_entry["group"] = new_group
            new_entry["path"] = new_path
            new_entry["url"] = new_url
            new_entry["defaultBranch"] = entry.get("defaultBranch") or matched_disk["branch"] or "main"
            new_entry["activeBranch"] = matched_disk["branch"]
            if matched_disk["head_commit"]:
                new_entry["headCommit"] = matched_disk["head_commit"]
            new_entry["is_cloned"] = True
            updated_catalog.append(new_entry)
        else:
            # Ruta no encontrada en disco (Huerfana / No clonada)
            gh_cands = remote_org_map.get(e_name.lower(), [])
            gh_meta = next((c for c in gh_cands if c["group"].lower() == old_group.lower()), None)
            if not gh_meta and len(gh_cands) == 1:
                gh_meta = gh_cands[0]

            if prune_deleted_remotes and remote_org_map and not gh_cands:
                orphaned_cleaned.append({
                    "name": e_name,
                    "old_path": old_path,
                    "action": "removed_missing_remote"
                })
                continue

            new_entry = dict(entry)
            was_marked_cloned = entry.get("is_cloned", True)
            if gh_meta and gh_meta["group"].lower() != old_group.lower():
                new_rel = f"{gh_meta['group']}/{gh_meta['name']}"
                relocated_repos.append({
                    "name": gh_meta["name"],
                    "from_group": old_group,
                    "to_group": gh_meta["group"],
                    "from_path": old_path,
                    "to_path": new_rel,
                    "url": gh_meta["url"]
                })
                new_entry["group"] = gh_meta["group"]
                new_entry["path"] = new_rel
                new_entry["url"] = gh_meta["url"]

            new_entry["is_cloned"] = False
            if was_marked_cloned:
                orphaned_cleaned.append({
                    "name": e_name,
                    "old_path": old_path,
                    "action": "marked_uncloned"
                })
            updated_catalog.append(new_entry)

    # 4. Agregar nuevos repositorios descubiertos en disco que no estaban en el catalogo
    for d in disk_repos:
        if d["full_path"] not in matched_disk_paths:
            default_b = d["branch"] if d["branch"] and d["branch"] != "(detached)" else "main"
            new_item = {
                "name": d["name"],
                "group": d["group"],
                "path": d["path"],
                "url": d["url"] or f"https://github.com/{d['group']}/{d['name']}.git",
                "defaultBranch": default_b,
                "activeBranch": d["branch"],
                "is_cloned": True
            }
            if d["head_commit"]:
                new_item["headCommit"] = d["head_commit"]
            updated_catalog.append(new_item)
            newly_discovered.append({
                "name": d["name"],
                "group": d["group"],
                "path": d["path"],
                "url": new_item["url"],
                "branch": d["branch"]
            })

        # deduplicar entradas del catalogo que apunten a la misma ruta relativa final
    deduped_catalog = []
    seen_rel_paths = set()
    for item in updated_catalog:
        rp = item.get("path", "").lower()
        if rp in seen_rel_paths:
            continue
        seen_rel_paths.add(rp)
        deduped_catalog.append(item)
    updated_catalog = deduped_catalog

    # Ordenar catalogo limpiamente por organizacion y nombre
    updated_catalog.sort(key=lambda x: (x.get("group", "").lower(), x.get("name", "").lower()))

    # 5. Persistencia atomica en disco
    # Si el archivo objetivo era repos.json (plantilla publica) y descubrimos repos reales del usuario,
    # guardamos en repos.local.json para respetar la privacidad de GitDoctor.
    target_save_file = catalog_file
    if os.path.basename(catalog_file) == "repos.json" and has_real_repos:
        target_save_file = os.path.join(script_dir, "repos.local.json")

    _atomic_write_json(target_save_file, updated_catalog)

    # Si existe un subdirectorio _sync/repos.json legacy, sincronizarlo atomicamente tambien
    legacy_sync_cat = os.path.join(repos_dir, "_sync", "repos.json")
    if os.path.isfile(legacy_sync_cat) and os.path.abspath(legacy_sync_cat) != os.path.abspath(os.path.join(script_dir, "repos.json")):
        try:
            _atomic_write_json(legacy_sync_cat, updated_catalog)
        except Exception:
            pass

    # Actualizar la lista `catalog` in-place para que la sesion activa del CLI/Agente vea los cambios de inmediato
    catalog.clear()
    catalog.extend(updated_catalog)

    cloned_total = sum(1 for c in updated_catalog if c.get("is_cloned", False))
    active_total = len(updated_catalog)

    # 6. Imprimir resumen diagnostico clinico
    if not quiet:
        print(f"\n{C_BOLD}📋 RESUMEN DIAGNOSTICO DE REINDEXACION:{C_RESET}")
        if physical_moves:
            print(f"\n  {C_MAGENTA}🚚 Carpetas Movidas Fisicamente (Transferencia detectada en GitHub): ({len(physical_moves)}){C_RESET}")
            for pm in physical_moves:
                print(f"    * {C_BOLD}{pm['name']}{C_RESET}: {C_YELLOW}{pm['from_path']}{C_RESET} --> {C_GREEN}{pm['to_path']}{C_RESET}")
        if relocated_repos:
            print(f"\n  {C_CYAN}🔄 Repositorios Reubicados en Catalogo: ({len(relocated_repos)}){C_RESET}")
            for rr in relocated_repos:
                print(f"    * {C_BOLD}{rr['name']}{C_RESET}: {C_YELLOW}{rr['from_path']}{C_RESET} --> {C_GREEN}{rr['to_path']}{C_RESET}")
        if newly_discovered:
            print(f"\n  {C_GREEN}✨ Nuevos Repositorios Descubiertos e Indexados: ({len(newly_discovered)}){C_RESET}")
            for nd in newly_discovered:
                print(f"    * {C_BOLD}{nd['path']}{C_RESET} [{nd['branch']}] ({nd['url']})")
        if orphaned_cleaned:
            print(f"\n  {C_YELLOW}🧹 Rutas Huerfanas / No Clonadas Actualizadas: ({len(orphaned_cleaned)}){C_RESET}")
            for oc in orphaned_cleaned[:15]:
                print(f"    * {oc['old_path']} -> {oc['action']}")
            if len(orphaned_cleaned) > 15:
                print(f"    * ... y {len(orphaned_cleaned) - 15} mas.")

        if not (physical_moves or relocated_repos or newly_discovered):
            print(f"  {C_GREEN}[OK] El catalogo y las carpetas en disco estan 100% sincronizados.{C_RESET}")

        print(f"\n  * {C_BOLD}Catalogo actualizado:{C_RESET} {os.path.basename(target_save_file)}")
        print(f"  * {C_BOLD}Repositorios clonados en disco:{C_RESET} {C_GREEN}{cloned_total}{C_RESET}")
        print(f"  * {C_BOLD}Total de repositorios activos en catalogo:{C_RESET} {C_CYAN}{active_total}{C_RESET}\n")

    return {
        "success": True,
        "catalog_file": target_save_file,
        "physical_moves": physical_moves,
        "relocated_repos": relocated_repos,
        "newly_discovered": newly_discovered,
        "published_to_github": published_to_github,
        "orphaned_cleaned": orphaned_cleaned,
        "cloned_total": cloned_total,
        "active_total": active_total
    }

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
19. `list_repositories`: Lista y filtra los repositorios del catalogo y del equipo (clonados vs en la nube). Usalo SIEMPRE que el usuario pida un listado, ver repositorios, o consultar que proyectos existen.
20. `search_repositories`: Busca repositorios con tolerancia a errores tipograficos, faltas de ortografia y nombres aproximados (fuzzy matching).
21. `reindex_catalog`: Escanea recursivamente el disco (`D:\\Repos` o `~/Repos`), detecta repositorios movidos de carpeta, transferidos de organizacion en GitHub (moviendo fisicamente sus archivos locales y actualizando su remote), agregados manualmente o eliminados, y sincroniza el catalogo maestro (`repos.local.json` / `repos.json`).

REGLAS DE INTERACCION:
- Responde siempre de forma concisa, profesional, clara, cercana y en espanol con tono de Medico DevOps de cabecera.
- Si el usuario pide un listado o ver qué repositorios tiene ('dame un listado', 'que repos tengo', 'mostrar repos', 'listar proyectos'), ejecuta INMEDIATAMENTE `list_repositories`.
- Si el usuario menciona un nombre aproximado o mal escrito de un repositorio (ej. 'peluza' por 'pelusa', 'audio' por 'TranscriptAudio'), las herramientas cuentan con busqueda difusa (fuzzy search) integrada y encontraran el proyecto adecuado automaticamente.
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
            },
            {
                "name": "list_repositories",
                "description": "Lista y muestra los repositorios del catalogo y del equipo, con estado de clonacion y rama activa. Usala SIEMPRE que el usuario pida un listado, ver que proyectos tiene, o filtrar por organizacion.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "Filtro opcional por nombre o termino de busqueda"
                        },
                        "org_name": {
                            "type": "STRING",
                            "description": "Filtro opcional por organizacion (ej: 'Personal', 'th-mex', etc.)"
                        },
                        "status_filter": {
                            "type": "STRING",
                            "enum": ["all", "cloned", "uncloned"],
                            "description": "Filtrar por estado: 'cloned' (clonados en este equipo), 'uncloned' (solo en la nube) o 'all' (todos)"
                        }
                    }
                }
            },
            {
                "name": "search_repositories",
                "description": "Busca repositorios por nombre, termino o coincidencia difusa con tolerancia a faltas de ortografia (fuzzy search).",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {
                            "type": "STRING",
                            "description": "Nombre o termino del repositorio a buscar (incluso con faltas de ortografia o nombres parciales)"
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "reindex_catalog",
                "description": "Auto-descubre y reindexa el catalogo de repositorios: escanea el disco recursivamente, detecta repositorios movidos en disco o transferidos de organizacion en GitHub (moviendo sus archivos fisicos y actualizando su remote origin), registra nuevos repos locales y limpia rutas huerfanas.",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "sync_remote_transfers": {
                            "type": "BOOLEAN",
                            "description": "Si es True (por defecto), consulta GitHub para detectar si algun repositorio cambio de organizacion y mueve fisicamente su carpeta local."
                        },
                        "auto_move_physical": {
                            "type": "BOOLEAN",
                            "description": "Si es True (por defecto), mueve automaticamente la carpeta fisica del repositorio en disco hacia la nueva organizacion detectada."
                        }
                    }
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

def call_openai_api(api_key, model, conversation_history, system_instruction):
    """Llama a la API de OpenAI (ChatGPT) para modelos GPT-4o, GPT-4, etc."""
    global _LAST_GEMINI_ERROR
    _LAST_GEMINI_ERROR = ""

    if not api_key:
        _LAST_GEMINI_ERROR = "Falta OPENAI_API_KEY. Configurala con /set-key."
        return None

    url = "https://api.openai.com/v1/chat/completions"
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
        "model": model or "gpt-4o",
        "messages": messages,
        "temperature": 0.3
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            msg = resp_data.get("choices", [{}])[0].get("message", {}).get("content", "")
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
    except urllib.error.HTTPError as e:
        err_msg = ""
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            err_msg = err_data.get("error", {}).get("message", "")
        except Exception:
            pass
        _LAST_GEMINI_ERROR = f"OpenAI HTTP {e.code}: {err_msg or e.reason}"
        return None
    except Exception as e:
        _LAST_GEMINI_ERROR = f"Error en OpenAI: {sanitize_error(e)}"
        return None

def call_anthropic_api(api_key, model, conversation_history, system_instruction):
    """Llama a la API de Anthropic para modelos Claude 3.5 Sonnet / Haiku"""
    global _LAST_GEMINI_ERROR
    _LAST_GEMINI_ERROR = ""

    if not api_key:
        _LAST_GEMINI_ERROR = "Falta ANTHROPIC_API_KEY. Configurala con /set-key."
        return None

    url = "https://api.anthropic.com/v1/messages"
    messages = []
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

    if not messages:
        messages = [{"role": "user", "content": "Hola"}]

    payload = {
        "model": model or "claude-3-5-sonnet-20241022",
        "max_tokens": 4096,
        "system": system_instruction,
        "messages": messages,
        "temperature": 0.3
    }
    data_bytes = json.dumps(payload).encode("utf-8")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json"
    }
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            text_parts = [c.get("text", "") for c in resp_data.get("content", []) if c.get("type") == "text"]
            return {
                "candidates": [
                    {
                        "content": {
                            "role": "model",
                            "parts": [{"text": "\n".join(text_parts)}]
                        }
                    }
                ]
            }
    except urllib.error.HTTPError as e:
        err_msg = ""
        try:
            err_data = json.loads(e.read().decode("utf-8"))
            err_msg = err_data.get("error", {}).get("message", "")
        except Exception:
            pass
        _LAST_GEMINI_ERROR = f"Anthropic HTTP {e.code}: {err_msg or e.reason}"
        return None
    except Exception as e:
        _LAST_GEMINI_ERROR = f"Error en Anthropic: {sanitize_error(e)}"
        return None

def call_aws_bedrock_api(conversation_history, system_instruction, local_cfg):
    """Invoca modelos en Amazon Bedrock mediante boto3"""
    global _LAST_GEMINI_ERROR
    _LAST_GEMINI_ERROR = ""
    try:
        import boto3
    except ImportError:
        _LAST_GEMINI_ERROR = "Para usar AWS Bedrock se requiere 'boto3'. Instalalo con: pip install boto3"
        return None

    region = local_cfg.get("aws_region") or os.environ.get("AWS_REGION", "us-east-1")
    model = local_cfg.get("aws_bedrock_model", "anthropic.claude-3-5-sonnet-20241022-v2:0")
    try:
        client = boto3.client("bedrock-runtime", region_name=region)
        messages = []
        for turn in conversation_history:
            role = turn.get("role", "user")
            if role == "model":
                role = "assistant"
            parts = turn.get("parts", [])
            text = "".join([p["text"] for p in parts if "text" in p])
            if text:
                messages.append({"role": role, "content": text})
        if not messages:
            messages = [{"role": "user", "content": "Hola"}]

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": system_instruction,
            "messages": messages,
            "temperature": 0.3
        })
        resp = client.invoke_model(body=body, modelId=model)
        resp_data = json.loads(resp.get("body").read().decode("utf-8"))
        text_parts = [c.get("text", "") for c in resp_data.get("content", []) if c.get("type") == "text"]
        return {
            "candidates": [
                {
                    "content": {
                        "role": "model",
                        "parts": [{"text": "\n".join(text_parts)}]
                    }
                }
            ]
        }
    except Exception as e:
        _LAST_GEMINI_ERROR = f"Error en AWS Bedrock ({region}): {sanitize_error(e)}"
        return None

def call_ai_engine(api_key, conversation_history, system_instruction, local_cfg):
    """Enrutador de IA inteligente: despacha al motor activo segun configuracion"""
    provider = local_cfg.get("ai_provider", "gemini")
    if provider == "ollama":
        host = local_cfg.get("ollama_host", "http://localhost:11434")
        model = local_cfg.get("ollama_model", "llama3.1")
        return call_ollama_api(host, model, conversation_history, system_instruction)
    elif provider == "openai":
        model = local_cfg.get("openai_model", "gpt-4o")
        return call_openai_api(api_key, model, conversation_history, system_instruction)
    elif provider == "anthropic":
        model = local_cfg.get("anthropic_model", "claude-3-5-sonnet-20241022")
        return call_anthropic_api(api_key, model, conversation_history, system_instruction)
    elif provider in ["aws", "bedrock"]:
        return call_aws_bedrock_api(conversation_history, system_instruction, local_cfg)
    else:
        return call_gemini_api(api_key, conversation_history, system_instruction)

def interactive_switch_ai(local_cfg, script_dir, target=None):
    """Permite consultar o cambiar el motor de IA entre Google Gemini, OpenAI, Anthropic, AWS y Ollama"""
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
        elif "gemini" in t or "google" in t:
            local_cfg["ai_provider"] = "gemini"
            save_local_config(script_dir, local_cfg)
            print(f"\n{C_GREEN}[OK] Motor de IA cambiado a: Google Gemini Cloud.{C_RESET}\n")
            return local_cfg
        elif "openai" in t or "chatgpt" in t or "gpt" in t:
            local_cfg["ai_provider"] = "openai"
            save_local_config(script_dir, local_cfg)
            print(f"\n{C_GREEN}[OK] Motor de IA cambiado a: OpenAI (ChatGPT).{C_RESET}\n")
            return local_cfg
        elif "anthropic" in t or "claude" in t:
            local_cfg["ai_provider"] = "anthropic"
            save_local_config(script_dir, local_cfg)
            print(f"\n{C_GREEN}[OK] Motor de IA cambiado a: Anthropic Claude.{C_RESET}\n")
            return local_cfg
        elif "aws" in t or "bedrock" in t:
            local_cfg["ai_provider"] = "aws"
            save_local_config(script_dir, local_cfg)
            print(f"\n{C_GREEN}[OK] Motor de IA cambiado a: AWS Bedrock.{C_RESET}\n")
            return local_cfg

    print(f"\n{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  GitDoctor -- Configuracion de Motor de Inteligencia Artificial {C_RESET}")
    print(f"{C_CYAN}=================================================================={C_RESET}\n")
    print(f"Motor actualmente activo: {C_BOLD}{C_GREEN}{current.upper()}{C_RESET}\n")

    status_ollama = f"{C_GREEN}[Activo en localhost:11434]{C_RESET}" if ollama_info["available"] else f"{C_GRAY}[No detectado]{C_RESET}"
    models_str = f" ({', '.join(ollama_info['models'][:3])})" if ollama_info["models"] else ""

    providers = [
        ("1", "gemini", "Google Gemini / Google Cloud (Cuota gratuita en la nube)"),
        ("2", "openai", "OpenAI / ChatGPT (GPT-4o, o1)"),
        ("3", "anthropic", "Anthropic Claude (Claude 3.5 Sonnet / Haiku)"),
        ("4", "aws", "AWS Bedrock / Amazon Web Services"),
        ("5", "ollama", f"Ollama Local Offline {status_ollama}{models_str} (100% privado)")
    ]

    for num, pid, desc in providers:
        marker = f" {C_GREEN}<- Activo{C_RESET}" if pid == current else ""
        print(f"  [{num}] {desc}{marker}")

    try:
        ans = input(f"\n{C_BOLD}Selecciona motor [1-5] (Enter para mantener {current}): {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        ans = ""

    mapping = {"1": "gemini", "2": "openai", "3": "anthropic", "4": "aws", "5": "ollama"}
    if ans in mapping:
        chosen = mapping[ans]
        local_cfg["ai_provider"] = chosen
        if chosen == "ollama":
            if ollama_info["models"]:
                local_cfg["ollama_model"] = ollama_info["models"][0]
            else:
                local_cfg["ollama_model"] = "llama3.1"
        save_local_config(script_dir, local_cfg)

        key = load_ai_api_key(script_dir, chosen, interactive=False)
        if chosen != "ollama" and not key:
            print(f"\n{C_YELLOW}[!] Has seleccionado {chosen.upper()} pero aun no tienes su clave configurada.{C_RESET}")
            if configure_ai_provider:
                local_cfg = configure_ai_provider(script_dir, local_cfg)
                save_local_config(script_dir, local_cfg)
        else:
            print(f"\n{C_GREEN}[OK] Motor configurado: {chosen.upper()}.{C_RESET}\n")

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

    elif tool_name == "list_repositories":
        query = args.get("query", "")
        org_name = args.get("org_name", "")
        status_filter = args.get("status_filter", "all")
        return list_repositories(repos_dir, catalog, query=query, org_name=org_name, status_filter=status_filter, interactive=True)

    elif tool_name == "search_repositories":
        query = args.get("query", "")
        matches = find_matching_repos(query, catalog, repos_dir=repos_dir, cutoff=0.45)
        return {
            "query": query,
            "total_matches": len(matches),
            "matches": [
                {
                    "name": m["entry"]["name"],
                    "group": m["entry"].get("group", ""),
                    "path": m["entry"].get("path", ""),
                    "score": m["score"],
                    "similarity_percent": int(m["score"] * 100),
                    "match_type": m["match_type"],
                    "is_cloned": m.get("is_cloned", False),
                    "url": m["entry"].get("url", "")
                }
                for m in matches[:10]
            ]
        }

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

    elif tool_name == "reindex_catalog":
        sync_remote = args.get("sync_remote_transfers", True)
        auto_move = args.get("auto_move_physical", True)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        gh_info = get_github_status() if sync_remote else None
        return reindex_and_sync_catalog(
            repos_dir=repos_dir,
            catalog=catalog,
            catalog_file=catalog_file,
            script_dir=script_dir,
            sync_remote_transfers=sync_remote,
            auto_move_physical=auto_move,
            gh_info=gh_info,
            active_orgs=active_orgs,
            quiet=False
        )

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
    print(f"  * {C_WHITE}/repos{C_RESET} [filtro|org]         : Listado completo de proyectos con estado (clonados en disco vs en la nube).")
    print(f"  * {C_WHITE}/buscar <termino>{C_RESET}         : Busqueda difusa e inteligente con tolerancia a faltas de ortografia.")
    print(f"  * {C_WHITE}/reindex{C_RESET} (o {C_WHITE}reindex{C_RESET})       : Auto-escanea el disco y GitHub; mueve carpetas si cambiaron de org y sincroniza el catalogo.")
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
    print(f"  * {C_WHITE}/ia{C_RESET} [motor]              : Alterna motor de IA (Gemini, OpenAI, Anthropic, AWS, Ollama).")
    print(f"  * {C_WHITE}/vigilante{C_RESET} [segundos]     : Monitoreo continuo en segundo plano con notificaciones nativas de SO.")
    print(f"  * {C_WHITE}/set-key{C_RESET}                  : Configura API Key de tu proveedor de IA con enlace directo en el navegador.")
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
    "repos": "/repos",
    "repo": "/repos",
    "list": "/repos",
    "lista": "/repos",
    "listar": "/repos",
    "listado": "/repos",
    "proyectos": "/repos",
    "catalogo-repos": "/repos",
    "buscar": "/buscar",
    "search": "/buscar",
    "find": "/buscar",
    "reindex": "/reindex",
    "reindexar": "/reindex",
    "reconciliar": "/reindex",
    "escanear": "/reindex",
    "autodescubrir": "/reindex",
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
    "/importar-github", "/publico", "/ia", "/set-key", "/ayuda", "/helpme", "/salir",
    "/repos", "/buscar", "/reindex"
]

def resolve_user_command(user_input):
    """
    Motor Antierrores:
    1. Reconoce comandos tanto con '/' como sin '/' (ej. 'salud', 'code amps', 'sync', 'repos', 'buscar').
    2. Detecta expresiones naturales de listado y busqueda ('dame un listado', 'cuales repos tengo', 'abrir repo x').
    3. Si hay un error tipografico en un comando (ej. '/saldu', '/synk', '/clonn', '/apago', '/reposs'),
       sugiere interactivamente la correccion adecuada.
    4. Si no es comando, devuelve None para que Gemini AI lo atienda como lenguaje natural.
    """
    raw = user_input.strip()
    if not raw:
        return None, ""

    # Normalizar para detectar frases naturales
    clean_lower = re.sub(r'[¿?¡!.,;:]', '', raw.lower()).strip()

    # Deteccion de frases naturales de LISTADO
    # Ejemplos: "dame un listado", "dame una lista", "ver repos", "que repos tengo", "cuales son mis repos", "listado de repos"
    LIST_PHRASES = [
        "dame un listado", "dame una lista", "dame el listado", "dame la lista",
        "ver listado", "ver lista", "ver repos", "ver repositorios", "ver proyectos",
        "mostrar listado", "mostrar lista", "mostrar repos", "mostrar repositorios", "mostrar proyectos",
        "listar repos", "listar repositorios", "listar proyectos", "listar", "listado", "lista",
        "listado de repos", "listado de repositorios", "listado de proyectos",
        "lista de repos", "lista de repositorios", "lista de proyectos",
        "que repos tengo", "que repositorios tengo", "que proyectos tengo",
        "cuales repos tengo", "cuales repositorios tengo", "cuales proyectos tengo",
        "cuales son mis repos", "cuales son mis repositorios", "cuales son mis proyectos",
        "mis repos", "mis repositorios", "mis proyectos"
    ]

    for phrase in sorted(LIST_PHRASES, key=len, reverse=True):
        if clean_lower == phrase:
            return "/repos", ""
        if clean_lower.startswith(phrase + " "):
            remainder = clean_lower[len(phrase):].strip()
            remainder = re.sub(r'^(de\s+|en\s+|del\s+|los\s+|las\s+|de\s+los\s+|de\s+las\s+)', '', remainder).strip()
            if remainder in ["repos", "los repos", "mis repos", "repositorios", "los repositorios", "mis repositorios", "proyectos", "los proyectos", "mis proyectos"]:
                remainder = ""
            return "/repos", remainder

    # Deteccion de frases naturales de BUSQUEDA
    # Ejemplos: "busca el repo pelusa", "buscar repositorio transcript", "donde esta pelusa"
    SEARCH_PREFIXES = [
        "busca el repo ", "busca el repositorio ", "busca el proyecto ", "busca repo ",
        "buscar el repo ", "buscar el repositorio ", "buscar el proyecto ", "buscar repo ",
        "donde esta el repo ", "donde esta el repositorio ", "donde esta el proyecto ", "donde esta ",
        "encuentra el repo ", "encuentra el repositorio ", "encuentra "
    ]
    for prefix in SEARCH_PREFIXES:
        if clean_lower.startswith(prefix):
            remainder = clean_lower[len(prefix):].strip()
            return "/buscar", remainder

    # Deteccion de frases naturales de ABRIR EN VS CODE
    OPEN_PREFIXES = [
        "abre el repo ", "abre el repositorio ", "abre el proyecto ",
        "abrir el repo ", "abrir el repositorio ", "abrir el proyecto ",
        "abreme el repo ", "abreme el repositorio ", "abreme el proyecto ",
        "abre ", "abrir ", "abreme "
    ]
    for prefix in OPEN_PREFIXES:
        if clean_lower.startswith(prefix):
            remainder = clean_lower[len(prefix):].strip()
            if remainder not in ["code", "vscode", "visual"]:
                return "/code", remainder

    # Deteccion de frases naturales de CLONAR
    CLONE_PREFIXES = [
        "clona el repo ", "clona el repositorio ", "clona la organizacion ", "clona la org ",
        "clonar el repo ", "clonar el repositorio ", "clonar la organizacion ",
        "descarga el repo ", "descarga el repositorio ", "descargar el repo ",
        "clona ", "clonar ", "descarga ", "descargar "
    ]
    for prefix in CLONE_PREFIXES:
        if clean_lower.startswith(prefix):
            remainder = clean_lower[len(prefix):].strip()
            return "/clone", remainder

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
# DESPACHADOR DE COMANDOS CANONICOS (CLI DIRECTO + REPL INTERACTIVO)
# ==============================================================================
def dispatch_single_command(canon_cmd, rest, repos_dir, catalog, catalog_file, gh_info, enabled_orgs, disabled_orgs, local_cfg, script_dir, all_known_orgs):
    """Ejecuta un comando canonico reconocido por GitDoctor tanto en modo CLI directo como en REPL interactivo"""
    if canon_cmd in ["/ayuda", "/helpme"]:
        print_helpme_commands()

    elif canon_cmd == "/repos":
        list_repositories(repos_dir, catalog, query=rest if rest else "", interactive=True)

    elif canon_cmd == "/buscar":
        if not rest:
            try:
                rest = input(f"{C_BOLD}Nombre o termino del proyecto a buscar: {C_RESET}").strip()
            except EOFError:
                rest = ""
        if rest:
            search_repositories_cli(repos_dir, catalog, rest)

    elif canon_cmd == "/code":
        if not rest:
            print(f"\n{C_YELLOW}[?] No indicaste el repositorio a abrir.{C_RESET}")
            try:
                rest = input(f"{C_BOLD}Nombre o termino del proyecto a abrir en VS Code: {C_RESET}").strip()
            except EOFError:
                rest = ""
        if rest:
            open_repo_in_vscode(repos_dir, catalog, rest)

    elif canon_cmd == "/orgs":
        interactive_manage_orgs(repos_dir, catalog, local_cfg, script_dir, all_known_orgs)

    elif canon_cmd == "/modo":
        interactive_toggle_sync_mode(script_dir, local_cfg)

    elif canon_cmd == "/clone":
        if not rest:
            print(f"\n{C_YELLOW}[?] No indicaste qué repositorio u organizacion clonar.{C_RESET}")
            print(f"{C_GRAY}Tip: Escribe /disponibles para ver la lista de repos que faltan en este equipo o /repos para ver todos.{C_RESET}")
            try:
                rest = input(f"{C_BOLD}Nombre a descargar: {C_RESET}").strip()
            except EOFError:
                rest = ""
        if rest:
            clone_specific_repo_or_org(repos_dir, catalog, rest)

    elif canon_cmd == "/disponibles":
        list_available_uncloned_repos(repos_dir, catalog)

    elif canon_cmd == "/nuevos":
        check_for_new_remote_repos(repos_dir, catalog, catalog_file, gh_info, enabled_orgs, interactive=True)

    elif canon_cmd == "/disco":
        check_and_prune_disk(repos_dir, catalog, auto_prune=False)

    elif canon_cmd == "/apagar":
        safe_preflight_checkout(repos_dir, catalog)

    elif canon_cmd == "/salud":
        if "360" in rest.lower():
            with_fetch = "fetch" in rest.lower() or "-f" in rest.lower()
            see_all = "-all" in rest.lower() or "all" in rest.lower()
            org_filter = None if see_all or not disabled_orgs else enabled_orgs
            audit_health_360(repos_dir, catalog, with_fetch=with_fetch, org_filter=org_filter)
        else:
            with_fetch = "fetch" in rest.lower() or "-f" in rest.lower()
            see_all = "-all" in rest.lower() or "all" in rest.lower()
            org_filter = None if see_all or not disabled_orgs else enabled_orgs
            scope_str = "todos los repositorios" if see_all or not disabled_orgs else f"{len(enabled_orgs)} organizaciones activas"
            print(f"\n{C_CYAN}[*] Evaluando salud ({scope_str}, {'con fetch remoto' if with_fetch else 'local'})...{C_RESET}")
            audit = audit_all_repos(repos_dir, catalog, with_fetch=with_fetch, org_filter=org_filter)
            print_health_report(audit)

    elif canon_cmd == "/seguridad":
        with_fetch = "fetch" in rest.lower() or "-f" in rest.lower()
        see_all = "-all" in rest.lower() or "all" in rest.lower()
        org_filter = None if see_all or not disabled_orgs else enabled_orgs
        audit_health_360(repos_dir, catalog, with_fetch=with_fetch, org_filter=org_filter)

    elif canon_cmd == "/gitflow":
        target = rest.strip() if rest else None
        org_filter = None if not disabled_orgs else enabled_orgs
        interactive_manage_gitflow(repos_dir, catalog, target_repo=target, org_filter=org_filter)

    elif canon_cmd == "/onboarding":
        if run_onboarding_assistant:
            run_onboarding_assistant(repos_dir, interactive=True)
        else:
            print(f"{C_RED}[!] Modulo onboarding.py no disponible.{C_RESET}\n")

    elif canon_cmd == "/limpiar":
        target = rest.strip() if rest else "all"
        clean_repo_hygiene(repos_dir, catalog, target_repo=target)

    elif canon_cmd == "/sync":
        target_org = rest.strip() if rest else None
        org_filter = [target_org] if target_org else (enabled_orgs if disabled_orgs else None)
        sync_all_repos(repos_dir, catalog, auto_pull=True, auto_clone=True, org_filter=org_filter)
        if gh_info.get('logged_in'):
            check_for_new_remote_repos(repos_dir, catalog, catalog_file, gh_info, org_filter or enabled_orgs, interactive=True)

    elif canon_cmd == "/push":
        target = rest.strip() if rest else "all"
        push_ahead_repos(repos_dir, catalog, target_repo=target)

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

    elif canon_cmd == "/github":
        gh_info_fresh = get_github_status()
        print_github_profile(gh_info_fresh)

    elif canon_cmd == "/login":
        interactive_github_login()

    elif canon_cmd == "/switch":
        target = rest.strip() if rest else None
        interactive_github_switch(target_user=target)

    elif canon_cmd == "/logout":
        target = rest.strip() if rest else None
        interactive_github_logout(target_user=target)

    elif canon_cmd == "/git-id":
        parts = rest.split(None, 1) if rest else []
        if len(parts) == 2:
            interactive_git_identity(name=parts[0], email=parts[1])
        else:
            interactive_git_identity()

    elif canon_cmd == "/dir":
        set_custom_repos_dir(script_dir, local_cfg, new_dir=rest if rest else None)

    elif canon_cmd == "/catalogo":
        parts = rest.split(None, 1) if rest else []
        act = parts[0] if len(parts) >= 1 else None
        p_arg = parts[1] if len(parts) >= 2 else None
        interactive_manage_catalog_vault(script_dir, local_cfg, gh_info, action=act, param=p_arg, repos_dir=repos_dir)

    elif canon_cmd == "/importar-github":
        import_repos_from_github(script_dir, gh_info)

    elif canon_cmd == "/reindex":
        no_remote = "--local" in rest.lower() or "local" in rest.lower()
        no_move = "--no-move" in rest.lower()
        reindex_and_sync_catalog(
            repos_dir=repos_dir,
            catalog=catalog,
            catalog_file=catalog_file,
            script_dir=script_dir,
            sync_remote_transfers=(not no_remote),
            auto_move_physical=(not no_move),
            gh_info=gh_info,
            active_orgs=all_known_orgs,
            quiet=False
        )

    elif canon_cmd == "/publico":
        prepare_for_public_repo(script_dir)

    elif canon_cmd == "/vigilante":
        sec = 300
        if rest and rest.isdigit():
            sec = int(rest)
        notif_flag = local_cfg.get("notifications_enabled", True)
        start_watchdog_loop(repos_dir, catalog, interval_seconds=sec, send_notifications=notif_flag,
                            catalog_file=catalog_file, gh_info=gh_info, active_orgs=enabled_orgs)

    elif canon_cmd == "/set-key":
        load_ai_api_key(script_dir, interactive=True)

    elif canon_cmd == "/ia":
        interactive_switch_ai(local_cfg, script_dir, target=rest if rest else None)

    elif canon_cmd == "/perfiles":
        interactive_manage_profiles(repos_dir, catalog, local_cfg, script_dir)

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

    # Auto-actualizacion de GitDoctor al iniciar si hay cambios nuevos en origin
    if os.path.isdir(os.path.join(script_dir, ".git")):
        try:
            old_head = run_cmd(["git", "rev-parse", "--short", "HEAD"], cwd=script_dir, timeout=4)
            subprocess.run(["git", "pull", "-q", "--ff-only"], cwd=script_dir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8)
            new_head = run_cmd(["git", "rev-parse", "--short", "HEAD"], cwd=script_dir, timeout=4)
            if old_head and new_head and old_head != new_head:
                print(f"{C_GREEN}✨ [AUTO-UPDATE] GitDoctor se actualizo automaticamente ({old_head} -> {new_head}).{C_RESET}")
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

    ai_provider = local_cfg.get("ai_provider", "gemini")
    api_key = load_ai_api_key(script_dir, ai_provider, interactive=False)

    # Modo CLI Directo: Si se ejecuto 'gitdoctor <comando>' o 'python3 agent.py <comando>'
    if len(sys.argv) > 1:
        cli_raw = " ".join(sys.argv[1:]).strip()
        if cli_raw in ["-h", "--help", "help", "/help", "ayuda", "/ayuda"]:
            print_helpme_commands()
            return

        canon_cmd, rest = resolve_user_command(cli_raw)
        if canon_cmd and canon_cmd != "CANCELLED":
            dispatch_single_command(canon_cmd, rest, repos_dir, catalog, catalog_file, gh_info, enabled_orgs, disabled_orgs, local_cfg, script_dir, all_known_orgs)
            return

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

    # Notificacion de Motor de IA (Multi-IA: Ollama Local + Proveedores Cloud)
    ai_provider = local_cfg.get("ai_provider", "gemini")
    ollama_info = probe_ollama_status()
    if ai_provider == "ollama":
        o_model = local_cfg.get("ollama_model", "llama3.1")
        print(f"{C_GREEN}[OK] IA Activa:{C_RESET} Ollama Local Offline {C_GRAY}(Modelo: {o_model} @ localhost:11434 - 100% privado){C_RESET}")
    elif ai_provider == "openai" and api_key:
        print(f"{C_GREEN}[OK] IA Activa:{C_RESET} OpenAI (ChatGPT) {C_GRAY}(Key: {get_masked_key(api_key)}){C_RESET}")
    elif ai_provider == "anthropic" and api_key:
        print(f"{C_GREEN}[OK] IA Activa:{C_RESET} Anthropic Claude {C_GRAY}(Key: {get_masked_key(api_key)}){C_RESET}")
    elif ai_provider == "aws":
        print(f"{C_GREEN}[OK] IA Activa:{C_RESET} AWS Bedrock {C_GRAY}(Key ID: {get_masked_key(api_key)}){C_RESET}")
    elif ai_provider == "gemini" and api_key:
        print(f"{C_GREEN}[OK] IA Activa:{C_RESET} Google Gemini Cloud {C_GRAY}(Key: {get_masked_key(api_key)}){C_RESET}")
        if ollama_info["available"]:
            print(f"      {C_CYAN}[Tip Local]: Ollama detectado en tu maquina. Puedes alternar a IA local con /ia ollama.{C_RESET}")
    elif ai_provider == "none":
        print(f"{C_GRAY}[INFO] IA:{C_RESET} Modo clasico sin IA activo. Escribe {C_WHITE}/ia{C_RESET} o {C_WHITE}/set-key{C_RESET} para activar un motor.")
    else:
        if ollama_info["available"]:
            print(f"{C_GREEN}[OK] IA Activa:{C_RESET} Ollama Local detectado {C_GRAY}(localhost:11434). Escribe /ia ollama para activarlo.{C_RESET}")
        else:
            p_name = {"gemini": "Gemini", "openai": "OpenAI", "anthropic": "Anthropic", "aws": "AWS"}.get(ai_provider, ai_provider.upper())
            print(f"{C_YELLOW}[!] IA:{C_RESET} Modo Offline {C_GRAY}(Usa /set-key para configurar clave de {p_name} o abre Ollama para IA local){C_RESET}")

    # Revision y descarga automatica de cambios remotos al iniciar GitDoctor
    org_filter = enabled_orgs if disabled_orgs else None
    print(f"\n{C_CYAN}[*] Revisando cambios remotos en tus repositorios y sincronizando al iniciar...{C_RESET}")
    try:
        startup_reindex = reindex_and_sync_catalog(
            repos_dir=repos_dir,
            catalog=catalog,
            catalog_file=catalog_file,
            script_dir=script_dir,
            sync_remote_transfers=bool(gh_info.get("logged_in")),
            auto_move_physical=True,
            gh_info=gh_info,
            active_orgs=all_known_orgs,
            interactive=True,
            quiet=True
        )
        if startup_reindex.get("physical_moves"):
            for pm in startup_reindex["physical_moves"]:
                print(f"  {C_MAGENTA}🚚 [AUTO-MOVE] '{pm['name']}' movido fisicamente: {pm['from_path']} -> {pm['to_path']}{C_RESET}")
        if startup_reindex.get("newly_discovered"):
            print(f"  {C_GREEN}✨ [AUTO-INDEX] {len(startup_reindex['newly_discovered'])} nuevo(s) repositorio(s) local(es) agregado(s) al catalogo.{C_RESET}")
    except Exception:
        pass

    init_audit = audit_all_repos(repos_dir, catalog, with_fetch=True, org_filter=org_filter, auto_reindex=False)

    # Si hay repositorios limpios con cambios pendientes en el remoto (BEHIND), descargarlos automaticamente
    startup_behind = [r for r in init_audit.get("behind", []) if r.get("dirty_count", 0) == 0]
    if startup_behind:
        print(f"  {C_CYAN}⬇ Descargando actualizaciones de {len(startup_behind)} repositorio(s) con cambios nuevos...{C_RESET}")

        def _startup_pull(repo_info):
            res = subprocess.run(["git", "pull", "-q", "--ff-only"], cwd=repo_info["full_path"], stderr=subprocess.DEVNULL)
            return repo_info, (res.returncode == 0)

        pulled_names = []
        with ThreadPoolExecutor(max_workers=16) as executor:
            for r_info, ok in executor.map(_startup_pull, startup_behind):
                if ok:
                    pulled_names.append(f"{r_info['group']}/{r_info['name']}")

        if pulled_names:
            print(f"  {C_GREEN}[OK] Descargados automaticamente ({len(pulled_names)}): {', '.join(pulled_names)}{C_RESET}")
            # Actualizar el estado en memoria de init_audit tras el pull exitoso
            init_audit = audit_all_repos(repos_dir, catalog, with_fetch=False, org_filter=org_filter, auto_reindex=False)

    print_health_report(init_audit)

    print(f"{C_WHITE}Comandos principales de GitDoctor:{C_RESET}")
    print(f"  {C_BOLD}/repos{C_RESET} [filtro|org]        {C_GRAY}Listado completo de proyectos (clonados en disco vs en la nube){C_RESET}")
    print(f"  {C_BOLD}/buscar <termino>{C_RESET}         {C_GRAY}Busqueda inteligente con tolerancia a faltas de ortografia{C_RESET}")
    print(f"  {C_BOLD}/reindex{C_RESET}                   {C_GRAY}Auto-escanea disco y GitHub; mueve carpetas si cambiaron de org y sincroniza catalogo{C_RESET}")
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

        if canon_cmd:
            dispatch_single_command(canon_cmd, rest, repos_dir, catalog, catalog_file, gh_info, enabled_orgs, disabled_orgs, local_cfg, script_dir, all_known_orgs)
            if canon_cmd in ["/orgs", "/modo", "/login", "/switch", "/logout", "/catalogo", "/importar-github", "/reindex", "/publico", "/dir", "/set-key", "/ia"]:
                gh_info = get_github_status()
                all_known_orgs = get_active_orgs(repos_dir, gh_info)
                disabled_orgs = set(local_cfg.get("disabled_orgs", [])) if local_cfg.get("sync_mode") == "selective" else set()
                enabled_orgs = [o for o in all_known_orgs if o not in disabled_orgs]
                system_instruction = build_system_instruction(enabled_orgs, user_name=gh_info.get('name') or gh_info.get('user'))
                cat_local = os.path.join(script_dir, "repos.local.json")
                if os.path.isfile(cat_local):
                    try:
                        with open(cat_local, "r", encoding="utf-8-sig") as f:
                            catalog = json.load(f)
                        catalog = [c for c in catalog if c.get("name") not in ["gitdoctor", "repos-sync"] and not c.get("url", "").endswith("/gitdoctor.git") and not c.get("url", "").endswith("/repos-sync.git")]
                    except Exception:
                        pass
                if canon_cmd in ["/set-key", "/ia"]:
                    ai_provider = local_cfg.get("ai_provider", "gemini")
                    new_key = load_ai_api_key(script_dir, ai_provider, interactive=False)
                    if new_key:
                        api_key = new_key
                        _CACHED_GEMINI_MODELS = []
            continue

        # Turno conversacional con IA
        ai_provider = local_cfg.get("ai_provider", "gemini")
        if ai_provider not in ["ollama", "none"] and not api_key:
            ollama_info = probe_ollama_status()
            if ollama_info["available"]:
                print(f"\n{C_CYAN}[*] {ai_provider.capitalize()} no tiene clave configurada, pero Ollama esta activo localmente.{C_RESET}")
                print(f"{C_GRAY}Cambiando automaticamente a Ollama Local Offline...{C_RESET}\n")
                local_cfg["ai_provider"] = "ollama"
                ai_provider = "ollama"
            else:
                p_label = {"gemini": "Gemini", "openai": "OpenAI", "anthropic": "Anthropic", "aws": "AWS"}.get(ai_provider, "tu IA")
                print(f"\n{C_YELLOW}[!] Para conversar en lenguaje natural con IA necesitas tu clave de {p_label} o abrir Ollama.{C_RESET}")
                print(f"{C_GRAY}Escribe {C_WHITE}/set-key{C_GRAY} para configurar tu clave segura o {C_WHITE}/ia{C_GRAY} para IA local.{C_RESET}\n")
                continue

        ai_names = {
            "ollama": "Ollama Local",
            "gemini": "Google Gemini",
            "openai": "OpenAI ChatGPT",
            "anthropic": "Anthropic Claude",
            "aws": "AWS Bedrock"
        }
        ai_engine_name = ai_names.get(ai_provider, "GitDoctor AI")
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
