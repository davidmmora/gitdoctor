# ==============================================================================
# setup-windows.ps1 -- Instalador y Configurador para Windows
# ==============================================================================

param(
    [switch]$Reajuste
)

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }
$syncScript = Join-Path $scriptDir "sync.ps1"
$localCfgPath = Join-Path $scriptDir "config.local.json"

# Verificar que Python este disponible
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python no esta disponible en el PATH del sistema." -ForegroundColor Red
    Write-Host "Instalalo con 'winget install Python.Python.3.11' o desde https://python.org (asegurate de marcar 'Add Python to PATH')." -ForegroundColor Yellow
    exit 1
}

# ------------------------------------------------------------------------------
# Deteccion e instalacion de herramientas esenciales (Git CLI y GitHub CLI)
# ------------------------------------------------------------------------------
if (-not $Reajuste) {
    # 1. Comprobar Git CLI
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
        Write-Host "[!] Git CLI no esta disponible en el sistema." -ForegroundColor Yellow
        Write-Host "Intentando instalar Git con winget o curl nativo..." -ForegroundColor Cyan
        $installedGit = $false
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            try {
                Write-Host "Instalando Git mediante winget..." -ForegroundColor Cyan
                winget install --id Git.Git -e --source winget --accept-source-agreements --accept-package-agreements
                $installedGit = $true
            } catch {}
        }
        if (-not $installedGit -or (-not (Get-Command git -ErrorAction SilentlyContinue))) {
            Write-Host "Descargando instalador de Git for Windows con curl nativo..." -ForegroundColor Cyan
            $gitInstaller = Join-Path $env:TEMP "Git-Installer.exe"
            try {
                curl.exe -fSL -o $gitInstaller "https://github.com/git-for-windows/git/releases/latest/download/Git-64-bit.exe"
                if (Test-Path $gitInstaller) {
                    Write-Host "Ejecutando instalacion silenciosa de Git..." -ForegroundColor Cyan
                    Start-Process -FilePath $gitInstaller -ArgumentList "/VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS /RESTARTAPPLICATIONS" -Wait
                    Remove-Item $gitInstaller -Force -ErrorAction SilentlyContinue
                }
            } catch {
                Write-Host "[ADVERTENCIA] No se pudo descargar Git automaticamente: $_" -ForegroundColor Red
            }
        }
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }

    # 2. Comprobar GitHub CLI (gh)
    if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
        Write-Host "[!] GitHub CLI ('gh') no esta disponible en el sistema." -ForegroundColor Yellow
        Write-Host "GitHub CLI es esencial para detectar tus organizaciones y clonar tus repositorios." -ForegroundColor Gray
        Write-Host "Descargando e instalando GitHub CLI mediante winget o curl nativo..." -ForegroundColor Cyan
        $installedGh = $false
        if (Get-Command winget -ErrorAction SilentlyContinue) {
            try {
                Write-Host "Instalando GitHub CLI mediante winget..." -ForegroundColor Cyan
                winget install --id GitHub.cli -e --source winget --accept-source-agreements --accept-package-agreements
                $installedGh = $true
            } catch {}
        }
        if (-not $installedGh -or (-not (Get-Command gh -ErrorAction SilentlyContinue))) {
            Write-Host "Descargando GitHub CLI con curl nativo..." -ForegroundColor Cyan
            $ghMsi = Join-Path $env:TEMP "gh_installer.msi"
            try {
                curl.exe -fSL -o $ghMsi "https://github.com/cli/cli/releases/latest/download/gh_windows_amd64.msi"
                if (Test-Path $ghMsi) {
                    Write-Host "Instalando paquete MSI de GitHub CLI..." -ForegroundColor Cyan
                    Start-Process msiexec.exe -ArgumentList "/i `"$ghMsi`" /quiet /norestart" -Wait
                    Remove-Item $ghMsi -Force -ErrorAction SilentlyContinue
                }
            } catch {
                Write-Host "[ADVERTENCIA] No se pudo instalar GitHub CLI automaticamente: $_" -ForegroundColor Red
            }
        }
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    }
}

# En modo interactivo, ejecutar primero el asistente de configuracion completo
if (-not $Reajuste) {
    python (Join-Path $scriptDir "onboarding.py") --interactive-setup
}

# Leer configuracion establecida por el asistente
$parentDir = Split-Path -Parent $scriptDir
$reposDir = $parentDir
$downloadOnSetup = $true

if (Test-Path $localCfgPath) {
    try {
        $cfg = Get-Content $localCfgPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($cfg.repos_dir -and (Test-Path $cfg.repos_dir)) {
            $reposDir = $cfg.repos_dir
        }
        if ($cfg.download_on_setup -ne $null) {
            $downloadOnSetup = [bool]$cfg.download_on_setup
        }
    } catch {}
}

if (-not $Reajuste) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "  GitDoctor -- Integracion con el Sistema (Windows)       " -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "  Carpeta raiz de proyectos: $reposDir" -ForegroundColor DarkGray
    Write-Host "  Ubicacion de GitDoctor:    $scriptDir" -ForegroundColor DarkGray
    Write-Host ""

    # 1. Configurar reglas de Git para evitar conflictos de linea y permisos
    Write-Host "[1/4] Configurando parametros de Git recomendados para Windows..." -ForegroundColor Yellow
}

git config --global core.autocrlf true 2>$null
git config --global core.filemode false 2>$null
git -C "$scriptDir" config core.filemode false 2>$null
if (-not $Reajuste) {
    Write-Host "      [OK] Git configurado (core.autocrlf=true, core.filemode=false)" -ForegroundColor Green
}

# Limpiar symlinks y junctions viejos o rotos en la raiz de repos
foreach ($legacy in @("_sync", "repos-sync")) {
    $legPath = Join-Path $reposDir $legacy
    if (Test-Path $legPath) {
        $item = Get-Item $legPath -Force -ErrorAction SilentlyContinue
        if ($item -and $item.LinkType) {
            Remove-Item -Path $legPath -Force -Recurse -ErrorAction SilentlyContinue
        }
    }
}

# 2. Configurar comandos globales 'gitdoctor' y 'gitdoc' en el perfil de PowerShell
if (-not $Reajuste) {
    Write-Host "[2/4] Configurando comandos globales 'gitdoctor' y 'gitdoc' en PowerShell..." -ForegroundColor Yellow
}

$profilePath = $PROFILE
if (-not (Test-Path $profilePath)) {
    $profileDir = Split-Path -Parent $profilePath
    if (-not (Test-Path $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    New-Item -ItemType File -Path $profilePath -Force | Out-Null
}

$profileContent = Get-Content $profilePath -Raw -ErrorAction SilentlyContinue
if (-not $profileContent) { $profileContent = "" }

$functionCode = @"

# >>> GitDoctor Global Commands >>>
function gitdoctor {
    param(
        [Parameter(ValueFromRemainingArguments = `$true)]
        `$ArgsList
    )
    `$candidates = @(
        "$scriptDir",
        "D:\Repos\gitdoctor",
        "`$HOME\Repos\gitdoctor",
        "`$HOME\repos\gitdoctor",
        "C:\Repos\gitdoctor"
    )
    `$foundDir = `$null
    foreach (`$d in `$candidates) {
        if (Test-Path (Join-Path `$d "agent.py")) { `$foundDir = `$d; break }
    }
    if (`$foundDir) {
        if (`$ArgsList -contains "--sync" -or `$ArgsList -contains "sync") {
            powershell -ExecutionPolicy Bypass -File (Join-Path `$foundDir "sync.ps1") `$ArgsList
        } else {
            python (Join-Path `$foundDir "agent.py") `$ArgsList
        }
    } else {
        Write-Error "No se encontro agent.py en las rutas conocidas de GitDoctor ($scriptDir)."
    }
}

Set-Alias -Name gitdoc -Value gitdoctor -Scope Global -ErrorAction SilentlyContinue

function reposync {
    gitdoctor --sync `$args
}
# <<< GitDoctor Global Commands <<<
"@

if ($profileContent -match "# >>> (?:RepoSync|GitDoctor) Global (?:Command|Commands) >>>[\s\S]*?# <<< (?:RepoSync|GitDoctor) Global (?:Command|Commands) <<<") {
    $profileContent = $profileContent -replace "# >>> (?:RepoSync|GitDoctor) Global (?:Command|Commands) >>>[\s\S]*?# <<< (?:RepoSync|GitDoctor) Global (?:Command|Commands) <<<", $functionCode.Trim()
    Set-Content -Path $profilePath -Value $profileContent -Encoding UTF8
    if (-not $Reajuste) {
        Write-Host "      [OK] Comandos 'gitdoctor' y 'gitdoc' actualizados en tu perfil: $profilePath" -ForegroundColor Green
    }
} else {
    Add-Content -Path $profilePath -Value $functionCode -Encoding UTF8
    if (-not $Reajuste) {
        Write-Host "      [OK] Comandos 'gitdoctor' y 'gitdoc' agregados a tu perfil: $profilePath" -ForegroundColor Green
    }
}

# 3. Crear accesos directos en el Escritorio
if (-not $Reajuste) {
    Write-Host "[3/4] Creando accesos directos en el Escritorio..." -ForegroundColor Yellow
}
try {
    $desktopPath = [Environment]::GetFolderPath("Desktop")
    if (Test-Path $desktopPath) {
        $wsh = New-Object -ComObject WScript.Shell
        
        # Acceso 1: Consola & Asistente IA
        $shortcutAI = $wsh.CreateShortcut((Join-Path $desktopPath "GitDoctor - Consola & IA.lnk"))
        $shortcutAI.TargetPath = Join-Path $scriptDir "run-agent.bat"
        $shortcutAI.WorkingDirectory = $scriptDir
        $shortcutAI.Description = "GitDoctor: Consola de Diagnostico, Salud 360 y Asistente IA"
        $shortcutAI.IconLocation = "$env:SystemRoot\System32\shell32.dll,264"
        $shortcutAI.Save()

        # Acceso 2: Salud 360
        $shortcutDoc = $wsh.CreateShortcut((Join-Path $desktopPath "GitDoctor - Salud 360.lnk"))
        $shortcutDoc.TargetPath = Join-Path $scriptDir "run-gitdoctor.bat"
        $shortcutDoc.WorkingDirectory = $scriptDir
        $shortcutDoc.Description = "Auditoria completa de seguridad, secretos y Gitflow"
        $shortcutDoc.IconLocation = "$env:SystemRoot\System32\shell32.dll,264"
        $shortcutDoc.Save()

        # Acceso 3: Sincronizar
        $shortcutSync = $wsh.CreateShortcut((Join-Path $desktopPath "GitDoctor - Sincronizar.lnk"))
        $shortcutSync.TargetPath = Join-Path $scriptDir "run-sync.bat"
        $shortcutSync.WorkingDirectory = $scriptDir
        $shortcutSync.Description = "Sincronizar todos los repositorios con GitHub"
        $shortcutSync.IconLocation = "$env:SystemRoot\System32\shell32.dll,238"
        $shortcutSync.Save()

        # Acceso 4: Vigilante (Segundo Plano)
        $shortcutVig = $wsh.CreateShortcut((Join-Path $desktopPath "GitDoctor - Vigilante.lnk"))
        $shortcutVig.TargetPath = Join-Path $scriptDir "run-watchdog.bat"
        $shortcutVig.WorkingDirectory = $scriptDir
        $shortcutVig.Description = "Modo Vigilante continuo con notificaciones nativas"
        $shortcutVig.IconLocation = "$env:SystemRoot\System32\shell32.dll,246"
        $shortcutVig.Save()

        # Acceso 5: Salida Segura (Pre-Flight)
        $shortcutOut = $wsh.CreateShortcut((Join-Path $desktopPath "GitDoctor - Salida Segura.lnk"))
        $shortcutOut.TargetPath = Join-Path $scriptDir "run-checkout.bat"
        $shortcutOut.WorkingDirectory = $scriptDir
        $shortcutOut.Description = "Auditoria pre-flight antes de apagar o cambiar de maquina"
        $shortcutOut.IconLocation = "$env:SystemRoot\System32\shell32.dll,27"
        $shortcutOut.Save()

        if (-not $Reajuste) {
            Write-Host "      [OK] 5 Accesos directos de GitDoctor creados en tu Escritorio de Windows." -ForegroundColor Green
        }
    }
} catch {
    if (-not $Reajuste) {
        Write-Host "      [WARN] No se pudieron crear los accesos directos en el escritorio: $_" -ForegroundColor DarkGray
    }
}

if ($Reajuste) {
    exit 0
}

# 4. Sincronizacion inicial si fue solicitada
if ($downloadOnSetup) {
    Write-Host "`n[*] Procediendo con la sincronizacion y descarga de repositorios faltantes..." -ForegroundColor Yellow
    powershell -ExecutionPolicy Bypass -File "$syncScript"
} else {
    Write-Host "`n[INFO] Modo bajo demanda activo. Tus proyectos estan catalogados en repos.local.json." -ForegroundColor Cyan
    Write-Host "Para clonar cualquier repositorio cuando lo requieras usa: gitdoctor /clone <nombre>" -ForegroundColor DarkGray
    Write-Host "O para sincronizar todo en cualquier momento usa:        gitdoctor --sync" -ForegroundColor DarkGray
}

# 5. Certificacion final con /doctor
Write-Host "`n[*] Certificando entorno del sistema con /doctor..." -ForegroundColor Yellow
python (Join-Path $scriptDir "agent.py") /doctor --quiet 2>$null

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  ¡Instalacion de GitDoctor completada con exito!" -ForegroundColor Green
Write-Host "  A partir de ahora puedes escribir 'gitdoctor' o" -ForegroundColor White
Write-Host "  'gitdoc' en cualquier terminal de PowerShell." -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
