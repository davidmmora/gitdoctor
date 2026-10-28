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
import tempfile
import platform
import webbrowser
import urllib.request

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
# GESTION Y VERIFICACION DE HERRAMIENTAS ESENCIALES (GIT, GH, CURL)
# ==============================================================================
def _refresh_path_and_find_tools():
    """Recarga el PATH en el proceso actual incluyendo rutas estandar donde residen herramientas"""
    cur_parts = os.environ.get("PATH", "").split(os.pathsep)
    extra_dirs = []

    if sys.platform == "win32":
        local_app = os.environ.get("LOCALAPPDATA", "")
        extra_dirs = [
            r"C:\Program Files\Git\cmd",
            r"C:\Program Files\Git\bin",
            r"C:\Program Files\GitHub CLI",
            os.path.join(local_app, "GitHub CLI") if local_app else "",
        ]
        # Leer tambien PATH del Registro de Windows
        try:
            import winreg
            for hkey, subkey in [(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                                 (winreg.HKEY_CURRENT_USER, r"Environment")]:
                try:
                    with winreg.OpenKey(hkey, subkey) as k:
                        val, _ = winreg.QueryValueEx(k, "Path")
                        extra_dirs.extend(val.split(";"))
                except Exception:
                    pass
        except Exception:
            pass
    else:
        home = os.path.expanduser("~")
        extra_dirs = [
            "/usr/local/bin",
            "/opt/homebrew/bin",
            os.path.join(home, ".local", "bin"),
            os.path.join(home, "bin")
        ]

    new_dirs = [d for d in extra_dirs if d and os.path.isdir(d) and d not in cur_parts]
    if new_dirs:
        os.environ["PATH"] = os.pathsep.join(new_dirs + cur_parts)

def install_git_cli():
    """Descarga e instala Git CLI si no esta presente en el sistema"""
    print(f"\n{C_CYAN}[*] Iniciando instalacion de Git CLI...{C_RESET}")
    system = sys.platform

    if system == "darwin":
        if shutil.which("brew"):
            print(f"  {C_GRAY}Homebrew detectado. Instalando Git: brew install git...{C_RESET}")
            subprocess.run(["brew", "install", "git"], check=False)
            _refresh_path_and_find_tools()
            return shutil.which("git") is not None
        else:
            print(f"  {C_YELLOW}Invocando instalador oficial de herramientas de desarrollador de Apple...{C_RESET}")
            subprocess.run(["xcode-select", "--install"], check=False)
            print(f"  {C_GRAY}Sigue las instrucciones del dialogo emergente para completar la instalacion de Git.{C_RESET}")
            return True

    elif system == "win32":
        if shutil.which("winget"):
            print(f"  {C_GRAY}Winget detectado. Instalando Git: winget install Git.Git...{C_RESET}")
            subprocess.run(["winget", "install", "--id", "Git.Git", "-e", "--source", "winget", "--accept-source-agreements", "--accept-package-agreements"], check=False)
            _refresh_path_and_find_tools()
            if shutil.which("git"):
                print(f"  {C_GREEN}[OK] Git CLI instalado con exito via winget.{C_RESET}")
                return True

        # Descarga con curl nativo
        print(f"  {C_GRAY}Descargando instalador de Git for Windows con curl nativo...{C_RESET}")
        git_installer = os.path.join(tempfile.gettempdir(), "Git-Installer.exe")
        git_url = "https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe"
        dl = subprocess.run(["curl.exe", "-fSL", "-o", git_installer, git_url], check=False)
        if dl.returncode == 0 and os.path.isfile(git_installer):
            print(f"  {C_GRAY}Ejecutando instalacion silenciosa de Git...{C_RESET}")
            subprocess.run([git_installer, "/VERYSILENT", "/NORESTART", "/NOCANCEL", "/SP-", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"], check=False)
            try:
                os.remove(git_installer)
            except Exception:
                pass
            _refresh_path_and_find_tools()
            if shutil.which("git"):
                print(f"  {C_GREEN}[OK] Git CLI instalado exitosamente.{C_RESET}")
                return True

    else:
        # Linux
        print(f"  {C_GRAY}Intentando instalar Git mediante el gestor del sistema...{C_RESET}")
        for mgr_cmd in [["sudo", "apt-get", "update"], ["sudo", "apt-get", "install", "-y", "git"]]:
            subprocess.run(mgr_cmd, check=False)
        _refresh_path_and_find_tools()
        return shutil.which("git") is not None

    return shutil.which("git") is not None

def install_github_cli():
    """Descarga e instala GitHub CLI ('gh') mediante curl nativo o gestor de paquetes"""
    print(f"\n{C_CYAN}[*] Iniciando instalacion de GitHub CLI ('gh')...{C_RESET}")
    system = sys.platform

    # 1. En macOS
    if system == "darwin":
        if shutil.which("brew"):
            print(f"  {C_GRAY}Homebrew detectado. Ejecutando: brew install gh...{C_RESET}")
            res = subprocess.run(["brew", "install", "gh"], check=False)
            _refresh_path_and_find_tools()
            if res.returncode == 0 and shutil.which("gh"):
                print(f"  {C_GREEN}[OK] GitHub CLI instalado con exito via Homebrew.{C_RESET}")
                return True

        # Instalacion directa con curl
        print(f"  {C_GRAY}Descargando GitHub CLI oficial con curl nativo...{C_RESET}")
        arch = platform.machine().lower()
        gh_arch = "macOS_arm64" if arch in ["arm64", "aarch64"] else "macOS_amd64"

        version = "2.67.0"
        try:
            res_v = subprocess.run(
                ["curl", "-sSL", "-o", "/dev/null", "-w", "%{url_effective}", "https://github.com/cli/cli/releases/latest"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=False
            )
            out_url = res_v.stdout.decode('utf-8').strip()
            if "/tag/v" in out_url:
                version = out_url.split("/tag/v")[-1].strip()
        except Exception:
            pass

        url = f"https://github.com/cli/cli/releases/download/v{version}/gh_{version}_{gh_arch}.zip"
        tmp_dir = tempfile.mkdtemp(prefix="gitdoctor_gh_")
        zip_path = os.path.join(tmp_dir, "gh.zip")

        try:
            print(f"  {C_GRAY}Descargando {url}...{C_RESET}")
            dl_res = subprocess.run(["curl", "-fsSL", "-o", zip_path, url], check=False)
            if dl_res.returncode == 0 and os.path.isfile(zip_path):
                import zipfile
                with zipfile.ZipFile(zip_path, 'r') as zf:
                    zf.extractall(tmp_dir)

                gh_bin = None
                for root, dirs, files in os.walk(tmp_dir):
                    if "gh" in files:
                        p = os.path.join(root, "gh")
                        if os.path.isfile(p):
                            gh_bin = p
                            break

                if gh_bin:
                    target_dir = "/usr/local/bin"
                    if not os.access(target_dir, os.W_OK):
                        target_dir = os.path.expanduser("~/.local/bin")
                        os.makedirs(target_dir, exist_ok=True)

                    dest_file = os.path.join(target_dir, "gh")
                    shutil.copy2(gh_bin, dest_file)
                    os.chmod(dest_file, 0o755)

                    _refresh_path_and_find_tools()
                    print(f"  {C_GREEN}[OK] GitHub CLI ('gh') instalado exitosamente en {dest_file}.{C_RESET}")
                    return True
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    # 2. En Windows
    elif system == "win32":
        if shutil.which("winget"):
            print(f"  {C_GRAY}Winget detectado. Ejecutando: winget install GitHub.cli...{C_RESET}")
            res = subprocess.run(["winget", "install", "--id", "GitHub.cli", "-e", "--accept-source-agreements", "--accept-package-agreements"], check=False)
            _refresh_path_and_find_tools()
            if shutil.which("gh"):
                print(f"  {C_GREEN}[OK] GitHub CLI instalado con exito via winget.{C_RESET}")
                return True

        print(f"  {C_GRAY}Descargando GitHub CLI con curl nativo...{C_RESET}")
        version = "2.67.0"
        try:
            res_v = subprocess.run(
                ["curl.exe", "-sSL", "-o", "NUL", "-w", "%{url_effective}", "https://github.com/cli/cli/releases/latest"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=10, check=False
            )
            out_url = res_v.stdout.decode('utf-8').strip()
            if "/tag/v" in out_url:
                version = out_url.split("/tag/v")[-1].strip()
        except Exception:
            pass

        msi_url = f"https://github.com/cli/cli/releases/download/v{version}/gh_{version}_windows_amd64.msi"
        tmp_msi = os.path.join(tempfile.gettempdir(), f"gh_{version}.msi")

        print(f"  {C_GRAY}Descargando {msi_url}...{C_RESET}")
        dl_res = subprocess.run(["curl.exe", "-fsSL", "-o", tmp_msi, msi_url], check=False)
        if dl_res.returncode == 0 and os.path.isfile(tmp_msi):
            print(f"  {C_GRAY}Instalando paquete MSI de GitHub CLI...{C_RESET}")
            subprocess.run(["msiexec.exe", "/i", tmp_msi, "/quiet", "/norestart"], check=False)
            try:
                os.remove(tmp_msi)
            except Exception:
                pass
            _refresh_path_and_find_tools()
            if shutil.which("gh"):
                print(f"  {C_GREEN}[OK] GitHub CLI instalado exitosamente.{C_RESET}")
                return True

        # Fallback ZIP en Windows si MSI no se instalo
        zip_url = f"https://github.com/cli/cli/releases/download/v{version}/gh_{version}_windows_amd64.zip"
        tmp_zip = os.path.join(tempfile.gettempdir(), "gh.zip")
        dl_zip = subprocess.run(["curl.exe", "-fsSL", "-o", tmp_zip, zip_url], check=False)
        if dl_zip.returncode == 0 and os.path.isfile(tmp_zip):
            import zipfile
            extract_to = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "GitHub CLI")
            os.makedirs(extract_to, exist_ok=True)
            with zipfile.ZipFile(tmp_zip, 'r') as zf:
                for member in zf.namelist():
                    if member.endswith("gh.exe"):
                        with zf.open(member) as src_file, open(os.path.join(extract_to, "gh.exe"), "wb") as dst_file:
                            dst_file.write(src_file.read())
                        break
            try:
                os.remove(tmp_zip)
            except Exception:
                pass
            _refresh_path_and_find_tools()
            if shutil.which("gh"):
                print(f"  {C_GREEN}[OK] GitHub CLI ('gh.exe') instalado exitosamente en {extract_to}.{C_RESET}")
                return True

    # 3. En Linux
    else:
        print(f"  {C_GRAY}Descargando GitHub CLI con curl nativo...{C_RESET}")
        tmp_script = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".sh") as tf:
                tmp_script = tf.name
            dl = subprocess.run(["curl", "-fsSL", "-o", tmp_script, "https://cli.github.com/packages/install.sh"], check=False)
            if dl.returncode == 0 and os.path.isfile(tmp_script):
                os.chmod(tmp_script, 0o700)
                subprocess.run(["sudo", "bash", tmp_script], check=False)
            _refresh_path_and_find_tools()
            if shutil.which("gh"):
                print(f"  {C_GREEN}[OK] GitHub CLI instalado exitosamente.{C_RESET}")
                return True
        except Exception:
            pass
        finally:
            if tmp_script and os.path.isfile(tmp_script):
                try:
                    os.remove(tmp_script)
                except Exception:
                    pass

    _refresh_path_and_find_tools()
    return shutil.which("gh") is not None

def ensure_essential_tools():
    """
    Verifica las herramientas esenciales (Git CLI y GitHub CLI).
    Si faltan, utiliza curl nativo y los instaladores oficiales para instalarlas automaticamente.
    """
    _refresh_path_and_find_tools()
    print(f"\n{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  GitDoctor -- Diagnostico de Herramientas Esenciales          {C_RESET}")
    print(f"{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_GRAY}Verificando requisitos indispensables para clonacion, sincronizacion y GitHub:{C_RESET}\n")

    # 1. Comprobar Git CLI
    has_git = shutil.which("git") is not None
    if has_git:
        git_ver = run_cmd(["git", "--version"])
        print(f"  * Git CLI:        {C_GREEN}[OK] Detectado ({git_ver}){C_RESET}")
    else:
        print(f"  * Git CLI:        {C_RED}[NO DETECTADO]{C_RESET} (Esencial para operar repositorios)")
        if ask_user_confirmation("  ¿Deseas que GitDoctor instale Git CLI ahora mismo usando curl?", default_yes=True):
            install_git_cli()
            has_git = shutil.which("git") is not None
            if has_git:
                print(f"    {C_GREEN}[OK] Git CLI disponible: {run_cmd(['git', '--version'])}{C_RESET}")
            else:
                print(f"    {C_YELLOW}[AVISO] Git se esta instalando o requiere reiniciar la terminal.{C_RESET}")

    # 2. Comprobar GitHub CLI ('gh')
    has_gh = shutil.which("gh") is not None
    if has_gh:
        gh_ver = run_cmd(["gh", "--version"]).splitlines()[0] if run_cmd(["gh", "--version"]) else ""
        print(f"  * GitHub CLI:     {C_GREEN}[OK] Detectado ({gh_ver}){C_RESET}")
    else:
        print(f"  * GitHub CLI:     {C_YELLOW}[NO DETECTADO]{C_RESET} (Esencial para descubrir organizaciones y clonar)")
        if ask_user_confirmation("  ¿Deseas que GitDoctor instale GitHub CLI ('gh') usando curl nativo?", default_yes=True):
            install_github_cli()
            has_gh = shutil.which("gh") is not None
            if has_gh:
                print(f"    {C_GREEN}[OK] GitHub CLI disponible: {run_cmd(['gh', '--version']).splitlines()[0]}{C_RESET}")
            else:
                print(f"    {C_YELLOW}[AVISO] GitHub CLI descargado. Si no responde inmediatamente, estara activo al reiniciar.{C_RESET}")

    # 3. Comprobar cURL
    has_curl = shutil.which("curl") is not None or shutil.which("curl.exe") is not None
    if has_curl:
        print(f"  * cURL Nativo:    {C_GREEN}[OK] Detectado{C_RESET}")
    else:
        print(f"  * cURL Nativo:    {C_GRAY}[INFO] Se utilizaran bibliotecas integradas de red{C_RESET}")

    print("")
    return {"git": has_git, "gh": has_gh}

# ==============================================================================
# GESTION SEGURA DE VARIABLES DE ENTORNO Y CLAVES PRIVADAS (.env)
# ==============================================================================
def ensure_env_in_gitignore(script_dir):
    """Garantiza que .env y archivos locales de configuracion esten en .gitignore"""
    gi_path = os.path.join(script_dir, ".gitignore")
    lines = []
    if os.path.isfile(gi_path):
        try:
            with open(gi_path, "r", encoding="utf-8") as f:
                lines = [l.strip() for l in f.readlines()]
        except Exception:
            pass

    needed = [".env", "*.env", "config.local.json", "*.local.json", "repos.local.json"]
    to_add = [n for n in needed if n not in lines]
    if to_add:
        try:
            with open(gi_path, "a", encoding="utf-8") as f:
                f.write("\n# Archivos locales de configuracion y claves privadas\n")
                for n in to_add:
                    f.write(f"{n}\n")
        except Exception:
            pass

def save_env_var(script_dir, var_name, value):
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
        print(f"  {C_RED}[ERROR] No se pudo guardar {var_name}: {e}{C_RESET}")
        return False

# ==============================================================================
# CONFIGURACION MULTI-PROVEEDOR DE INTELIGENCIA ARTIFICIAL (GITDOCTOR AI)
# ==============================================================================
def configure_ai_provider(script_dir, current_cfg=None):
    """
    Configurador interactivo de motor de IA.
    Pregunta que proveedor desea el usuario:
      - Google Gemini / Google Cloud
      - OpenAI (ChatGPT)
      - Anthropic (Claude)
      - AWS Bedrock / Amazon Web Services
      - Ollama (Local Offline)
      - Omitir
    Envia al usuario a la ubicacion exacta para obtener su API key (abriendo su navegador),
    explica los pasos detallados y almacena la clave en .env de forma segura.
    """
    if current_cfg is None:
        current_cfg = {}

    current_provider = current_cfg.get("ai_provider", "gemini")

    print(f"\n{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_WHITE}{C_BOLD}  GitDoctor AI -- Seleccion de Motor de Inteligencia Artificial  {C_RESET}")
    print(f"{C_CYAN}=================================================================={C_RESET}")
    print(f"{C_GRAY}GitDoctor incluye un copiloto clinico para diagnostico, salud de repositorios,{C_RESET}")
    print(f"{C_GRAY}resolucion de dudas y seguridad. Puedes usar la nube o un modelo local:{C_RESET}\n")

    options = [
        ("1", "gemini", "Google Gemini / Google Cloud", "Recomendado, cuota gratuita, alta velocidad", "https://aistudio.google.com/app/apikey"),
        ("2", "openai", "OpenAI / ChatGPT", "Modelos GPT-4o, GPT-4, o1", "https://platform.openai.com/api-keys"),
        ("3", "anthropic", "Anthropic Claude", "Claude 3.5 Sonnet, Claude 3.5 Haiku", "https://console.anthropic.com/settings/keys"),
        ("4", "aws", "AWS Bedrock / Amazon Web Services", "Modelos en tu infraestructura AWS (Claude, Titan)", "https://console.aws.amazon.com/iam/home#/security_credentials"),
        ("5", "ollama", "Ollama Local Offline", "100% privado en tu equipo, sin API key, gratuito", "https://ollama.com/download"),
        ("6", "none", "Omitir por ahora", "Modo clasico sin asistente de IA", None)
    ]

    for num, pid, name, note, _ in options:
        marker = f" {C_GREEN}(Activo){C_RESET}" if pid == current_provider else ""
        print(f"  {C_WHITE}[{num}]{C_RESET} {C_BOLD}{name}{C_RESET}{marker}")
        print(f"      {C_GRAY}{note}{C_RESET}")

    default_choice = "1"
    for num, pid, _, _, _ in options:
        if pid == current_provider:
            default_choice = num
            break

    try:
        choice = input(f"\n  {C_BOLD}Selecciona tu proveedor de IA [1-6] (Enter para [{default_choice}]): {C_RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        choice = default_choice

    if not choice:
        choice = default_choice

    selected_opt = next((opt for opt in options if opt[0] == choice), options[0])
    _, provider_id, provider_name, _, url = selected_opt

    env_file = os.path.join(script_dir, ".env")
    result_cfg = dict(current_cfg)
    result_cfg["ai_provider"] = provider_id

    # 1. Omitir por ahora
    if provider_id == "none":
        print(f"\n  {C_GRAY}[*] Modo clasico activado. GitDoctor operara con comandos tradicionales sin IA.{C_RESET}")
        return result_cfg

    # 2. Ollama Local Offline
    if provider_id == "ollama":
        print(f"\n  {C_GREEN}--- Ollama Local Offline Seleccionado ---{C_RESET}")
        print(f"  {C_GRAY}Ollama ejecuta modelos de lenguaje en tu propio procesador/GPU local.{C_RESET}")
        print(f"  {C_GRAY}100% privado: tus datos nunca salen de tu ordenador y no requiere API key.{C_RESET}")

        is_active = False
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                models = [m.get("name") for m in data.get("models", [])]
                is_active = True
                print(f"  {C_GREEN}[OK] Ollama esta activo en localhost:11434.{C_RESET}")
                if models:
                    print(f"  {C_CYAN}Modelos locales detectados:{C_RESET} {', '.join(models[:4])}")
                    result_cfg["ollama_model"] = models[0]
                else:
                    print(f"  {C_YELLOW}[INFO] Ollama esta corriendo pero aun no tiene modelos descargados.{C_RESET}")
                    print(f"  {C_GRAY}Puedes descargar uno con: ollama run llama3.1{C_RESET}")
                    result_cfg["ollama_model"] = "llama3.1"
        except Exception:
            pass

        if not is_active:
            if shutil.which("ollama"):
                print(f"  {C_GREEN}[OK] Comando 'ollama' detectado en tu PATH.{C_RESET}")
                print(f"  {C_GRAY}Recuerda iniciarlo con 'ollama serve' o 'ollama run llama3.1'.{C_RESET}")
            else:
                print(f"\n  {C_YELLOW}[!] Ollama no esta instalado o no se encuentra en ejecucion.{C_RESET}")
                print(f"  Ubicacion oficial de descarga: {C_WHITE}https://ollama.com/download{C_RESET}")
                if ask_user_confirmation("  ¿Deseas abrir la pagina de descarga de Ollama en tu navegador?", default_yes=True):
                    try:
                        webbrowser.open("https://ollama.com/download")
                        print(f"  {C_GREEN}[OK] Abriendo navegador...{C_RESET}")
                    except Exception:
                        pass
                print(f"  {C_GRAY}Despues de instalarlo, ejecuta 'ollama run llama3.1' para comenzar.{C_RESET}")
            result_cfg["ollama_model"] = result_cfg.get("ollama_model", "llama3.1")
        return result_cfg

    # 3. Proveedores Cloud que requieren credenciales / API Key
    print(f"\n  {C_CYAN}------------------------------------------------------------{C_RESET}")
    print(f"  {C_BOLD}Configuracion de {provider_name}{C_RESET}")
    print(f"  {C_CYAN}------------------------------------------------------------{C_RESET}")

    if provider_id == "gemini":
        var_name = "GEMINI_API_KEY"
        print(f"  {C_WHITE}Ubicacion exacta para obtener tu clave gratuita:{C_RESET}")
        print(f"  {C_CYAN}-> Google AI Studio:      {C_WHITE}https://aistudio.google.com/app/apikey{C_RESET}")
        print(f"  {C_GRAY}-> Google Cloud Console:  https://console.cloud.google.com/apis/credentials{C_RESET}")
        print(f"\n  {C_GRAY}Pasos:{C_RESET}")
        print(f"    1. Inicia sesion con tu cuenta de Google.")
        print(f"    2. Haz clic en 'Create API key' o 'Get API key'.")
        print(f"    3. Copia tu clave (comienza con 'AIzaSy...') y pegala abajo.")

    elif provider_id == "openai":
        var_name = "OPENAI_API_KEY"
        print(f"  {C_WHITE}Ubicacion exacta para obtener tu clave de OpenAI:{C_RESET}")
        print(f"  {C_CYAN}-> OpenAI Platform:       {C_WHITE}https://platform.openai.com/api-keys{C_RESET}")
        print(f"\n  {C_GRAY}Pasos:{C_RESET}")
        print(f"    1. Inicia sesion en OpenAI Platform.")
        print(f"    2. Haz clic en '+ Create new secret key'.")
        print(f"    3. Asigna un nombre (ej. 'GitDoctor') y copia tu clave (comienza con 'sk-...').")

    elif provider_id == "anthropic":
        var_name = "ANTHROPIC_API_KEY"
        print(f"  {C_WHITE}Ubicacion exacta para obtener tu clave de Anthropic:{C_RESET}")
        print(f"  {C_CYAN}-> Anthropic Console:     {C_WHITE}https://console.anthropic.com/settings/keys{C_RESET}")
        print(f"\n  {C_GRAY}Pasos:{C_RESET}")
        print(f"    1. Inicia sesion en Anthropic Console.")
        print(f"    2. Ve a Settings -> API Keys y haz clic en 'Create Key'.")
        print(f"    3. Copia tu clave (comienza con 'sk-ant-...') y pegala abajo.")

    elif provider_id == "aws":
        var_name = "AWS_ACCESS_KEY_ID"
        print(f"  {C_WHITE}Ubicaciones exactas en la consola de AWS:{C_RESET}")
        print(f"  {C_CYAN}-> AWS IAM Credenciales:  {C_WHITE}https://console.aws.amazon.com/iam/home#/security_credentials{C_RESET}")
        print(f"  {C_GRAY}-> Amazon Bedrock Access: https://console.aws.amazon.com/bedrock/home#/modelaccess{C_RESET}")
        print(f"\n  {C_GRAY}Pasos:{C_RESET}")
        print(f"    1. En AWS IAM crea un Access Key ID y Secret Access Key con permisos para Bedrock.")
        print(f"    2. En Amazon Bedrock -> Model access activa modelos (ej. Claude 3.5 Sonnet).")

    # Preguntar si desea abrir la pagina en su navegador
    if url:
        if ask_user_confirmation(f"\n  ¿Deseas abrir la ubicacion exacta en tu navegador ahora mismo?", default_yes=True):
            try:
                webbrowser.open(url)
                print(f"  {C_GREEN}[OK] Abriendo {url} en tu navegador web...{C_RESET}")
            except Exception as e:
                print(f"  {C_YELLOW}[!] Abre manualmente el enlace: {url}{C_RESET}")

    # Comprobar si ya existe una clave en .env o entorno
    existing_val = os.environ.get(var_name, "").strip()
    if not existing_val and os.path.isfile(env_file):
        try:
            with open(env_file, "r", encoding="utf-8") as ef:
                for line in ef:
                    if line.strip().startswith(f"{var_name}="):
                        existing_val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        except Exception:
            pass

    if existing_val:
        masked = existing_val[:4] + "..." + existing_val[-4:] if len(existing_val) > 8 else "***"
        print(f"\n  Clave actual detectada para {var_name}: {C_CYAN}{masked}{C_RESET}")
        if ask_user_confirmation("  ¿Deseas mantener esta clave?", default_yes=True):
            print(f"  {C_GREEN}[OK] Clave conservada.{C_RESET}")
            return result_cfg

    # Solicitar la clave al usuario
    print("")
    if provider_id == "aws":
        try:
            aws_id = input(f"  Ingresa tu AWS_ACCESS_KEY_ID (Enter para configurar luego): ").strip()
            aws_secret = input(f"  Ingresa tu AWS_SECRET_ACCESS_KEY (Enter para omitir): ").strip()
            aws_region = input(f"  Ingresa tu Region de AWS [us-east-1]: ").strip() or "us-east-1"
            if aws_id:
                save_env_var(script_dir, "AWS_ACCESS_KEY_ID", aws_id)
                if aws_secret:
                    save_env_var(script_dir, "AWS_SECRET_ACCESS_KEY", aws_secret)
                save_env_var(script_dir, "AWS_REGION", aws_region)
                result_cfg["aws_region"] = aws_region
                print(f"  {C_GREEN}[OK] Credenciales de AWS guardadas de forma segura en .env (ignorado por Git).{C_RESET}")
        except (EOFError, KeyboardInterrupt):
            pass
    else:
        try:
            k_input = input(f"  Ingresa tu {provider_name} API Key (Enter para configurar luego): ").strip()
            if k_input:
                save_env_var(script_dir, var_name, k_input)
                print(f"  {C_GREEN}[OK] Clave guardada de forma segura en .env (ignorado por Git con permisos 0600).{C_RESET}")
        except (EOFError, KeyboardInterrupt):
            pass

    return result_cfg

# ==============================================================================
# DESCUBRIMIENTO DE GITHUB Y ORGANIZACIONES REALES DEL USUARIO
# ==============================================================================
def get_github_auth_info():
    """Obtiene datos de la sesion autenticada de GitHub CLI y sus organizaciones reales"""
    _refresh_path_and_find_tools()
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
    # PASO 1: DIAGNOSTICO DE HERRAMIENTAS ESENCIALES (GIT CLI, GH CLI, CURL)
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 1/7] Herramientas Esenciales de Desarrollo{C_RESET}")
    tools_status = ensure_essential_tools()

    # --------------------------------------------------------------------------
    # PASO 2: CARPETA Y NOMBRE CANONICO DE GITDOCTOR
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 2/7] Carpeta y Ubicacion de GitDoctor{C_RESET}")
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
    # PASO 3: CONEXION CON GITHUB Y DETECCION DE CUENTA Y ORGANIZACIONES
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 3/7] Conexion con GitHub y Deteccion de Organizaciones{C_RESET}")
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
    # PASO 4: ALCANCE DE INSTALACION Y DESCARGA (TODO vs SELECTIVO)
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 4/7] Alcance de Descarga y Organizaciones{C_RESET}")
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
    # PASO 5: IDENTIDAD GIT PARA ESTE EQUIPO
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 5/7] Identidad de Git (Commits y Firma){C_RESET}")
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
    # PASO 6: MOTOR DE INTELIGENCIA ARTIFICIAL (GITDOCTOR AI)
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 6/7] Motor de Inteligencia Artificial (GitDoctor AI){C_RESET}")
    ai_cfg = configure_ai_provider(script_dir, {"ai_provider": "gemini"})
    ai_provider = ai_cfg.get("ai_provider", "gemini")

    print("")

    # --------------------------------------------------------------------------
    # PASO 7: MODO VIGILANTE EN SEGUNDO PLANO (WATCHDOG)
    # --------------------------------------------------------------------------
    print(f"{C_BOLD}[Paso 7/7] Servicio Vigilante (Monitoreo en Segundo Plano){C_RESET}")
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

    # Combinar parametros especificos del proveedor de IA
    for k in ["ollama_model", "openai_model", "anthropic_model", "aws_region", "aws_bedrock_model"]:
        if k in ai_cfg:
            cfg_data[k] = ai_cfg[k]

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

    # Modo verificacion de requisitos
    if any(arg in sys.argv for arg in ["--ensure-prereqs", "--prereqs"]):
        ensure_essential_tools()
        return

    # Modo configuracion directa de IA
    if any(arg in sys.argv for arg in ["--config-ai", "--ai"]):
        cfg_file = os.path.join(script_dir, "config.local.json")
        cfg = {}
        if os.path.isfile(cfg_file):
            try:
                cfg = json.load(open(cfg_file, "r", encoding="utf-8"))
            except Exception:
                pass
        updated = configure_ai_provider(script_dir, cfg)
        try:
            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(updated, f, indent=4, ensure_ascii=False)
            print(f"  {C_GREEN}[OK] Configuracion de IA actualizada en config.local.json.{C_RESET}\n")
        except Exception as e:
            print(f"  {C_RED}[ERROR] No se pudo guardar config.local.json: {e}{C_RESET}\n")
        return

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

