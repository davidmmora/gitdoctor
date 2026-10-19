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

$parentDir = Split-Path -Parent $scriptDir
$parentName = Split-Path -Leaf $parentDir

$knownOrgs = @("Personal", "th-mex", "w-amarillo", "w-azul", "w-naranja", "interpec", "w-pluma", "w-ic", "bf-agency", "WeHubs-io")

# REGLA ESTRICTA: GitDoctor reside UNICAMENTE en la raiz de repositorios
if ($knownOrgs -contains $parentName) {
    Write-Host "[ERROR] GitDoctor reside dentro de la organizacion '$parentName'." -ForegroundColor Red
    Write-Host "[REGLA ESTRICTA] GitDoctor debe estar UNICAMENTE en la raiz de tu carpeta de repositorios (ej: D:\Repos\gitdoctor, C:\Proyectos\gitdoctor o la unidad/carpeta que elijas)." -ForegroundColor Yellow
    Write-Host "Mueve la carpeta 'gitdoctor' a la raiz de tu directorio principal de proyectos para evitar conflictos." -ForegroundColor Yellow
    exit 1
}

$reposDir = $parentDir

# Registrar la carpeta raiz en config.local.json si no fue personalizada antes
$localCfgPath = Join-Path $scriptDir "config.local.json"
if (-not (Test-Path $localCfgPath)) {
    @{ repos_dir = $reposDir; sync_mode = "mirror"; enabled_orgs = @(); disabled_orgs = @() } | ConvertTo-Json -Depth 4 | Out-File -FilePath $localCfgPath -Encoding utf8
} else {
    try {
        $cfg = Get-Content $localCfgPath -Raw -Encoding utf8 | ConvertFrom-Json
        if (-not $cfg.repos_dir) {
            $cfg | Add-Member -MemberType NoteProperty -Name "repos_dir" -Value $reposDir -Force
            $cfg | ConvertTo-Json -Depth 4 | Out-File -FilePath $localCfgPath -Encoding utf8
        }
    } catch {}
}

if (-not $Reajuste) {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "  GitDoctor -- Suite de Salud y Git para Windows          " -ForegroundColor Cyan
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host "  Carpeta raiz de proyectos: $reposDir" -ForegroundColor DarkGray
    Write-Host "  Ubicacion de GitDoctor:    $scriptDir" -ForegroundColor DarkGray
    Write-Host ""

    # 1. Comprobar GitHub CLI
    Write-Host "[1/5] Verificando estado de GitHub CLI..." -ForegroundColor Yellow
    if (Get-Command gh -ErrorAction SilentlyContinue) {
        $ghUser = gh api user --jq .login 2>$null
        if ($ghUser) {
            Write-Host "      [OK] GitHub conectado como @$ghUser" -ForegroundColor Green
            Write-Host "           Boveda Privada disponible: Usa 'gitdoctor /catalogo' para sincronizar tu inventario." -ForegroundColor DarkGray
        } else {
            Write-Host "      [INFO] GitHub CLI detectado sin sesion. Usa 'reposync-ai' o 'gh auth login' para iniciar sesion." -ForegroundColor Yellow
        }
    } else {
        Write-Host "      [INFO] GitHub CLI ('gh') no detectado en PATH. Se recomienda instalarlo con 'winget install GitHub.cli'." -ForegroundColor DarkGray
    }

    # 2. Configurar reglas de Git para evitar conflictos de linea y permisos con Mac
    Write-Host "[2/5] Configurando parametros de Git y blindando el repo contra ruido..." -ForegroundColor Yellow
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

# Limpiar clones duplicados o mal ubicados de GitDoctor en organizaciones o carpetas legacy
foreach ($org in $knownOrgs) {
    $orgDup = Join-Path $reposDir "$org\gitdoctor"
    if ((Test-Path $orgDup) -and ($orgDup.ToLower() -ne $scriptDir.ToLower())) {
        Remove-Item -Path $orgDup -Recurse -Force -ErrorAction SilentlyContinue
    }
    $orgLegacy = Join-Path $reposDir "$org\repos-sync"
    if (Test-Path $orgLegacy) {
        Remove-Item -Path $orgLegacy -Recurse -Force -ErrorAction SilentlyContinue
    }
}

foreach ($legacy in @("_gitdoctor", "_sync", "repos-sync")) {
    $legPath = Join-Path $reposDir $legacy
    if ((Test-Path $legPath) -and ($legPath.ToLower() -ne $scriptDir.ToLower())) {
        Remove-Item -Path $legPath -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# 3. Configurar comandos globales 'gitdoctor' y 'gitdoc' en el perfil de PowerShell
if (-not $Reajuste) {
    Write-Host "[3/6] Configurando comandos globales 'gitdoctor' y 'gitdoc' en PowerShell..." -ForegroundColor Yellow
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
        Write-Error "No se encontro agent.py en las rutas conocidas de GitDoctor (D:\Repos\gitdoctor)."
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

# 4. Crear accesos directos en el Escritorio
if (-not $Reajuste) {
    Write-Host "[4/6] Creando accesos directos en el Escritorio..." -ForegroundColor Yellow
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

# 5. Diagnostico de onboarding y reorganizacion
Write-Host "[5/6] Verificando estructura de carpetas y diagnostico inicial..." -ForegroundColor Yellow
if (Get-Command python -ErrorAction SilentlyContinue) {
    python (Join-Path $scriptDir "onboarding.py")
}

# 6. Ejecutar primera sincronizacion de prueba
Write-Host "[6/6] Ejecutando sincronizacion inicial..." -ForegroundColor Yellow
powershell -ExecutionPolicy Bypass -File "$syncScript"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  ¡Instalacion de GitDoctor completada con exito!" -ForegroundColor Green
Write-Host "  A partir de ahora puedes escribir 'gitdoctor' o" -ForegroundColor White
Write-Host "  'gitdoc' en cualquier terminal de PowerShell." -ForegroundColor White
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
