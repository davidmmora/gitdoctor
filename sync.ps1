# ==============================================================================
# sync.ps1 -- Sincronizador inteligente de Repositorios (Windows)
# ==============================================================================
param(
    [string]$TargetDir = "",
    [switch]$NoClone,
    [switch]$NoPull,
    [switch]$UpdateCatalog,
    [switch]$Vault
)

$AutoClone = -not $NoClone
$AutoPull  = -not $NoPull

$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition }
if (-not $scriptDir) { $scriptDir = (Get-Location).Path }

# Resolver Boveda Privada si repos.local.json no existe o si se solicita con -Vault
$localCat = Join-Path $scriptDir "repos.local.json"
if ($Vault -or (-not (Test-Path $localCat))) {
    $localCfgFile = Join-Path $scriptDir "config.local.json"
    if (Test-Path $localCfgFile) {
        try {
            $localCfg = Get-Content $localCfgFile -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($localCfg.catalog_gist_id -and (Get-Command gh -ErrorAction SilentlyContinue)) {
                Write-Host "[*] Sincronizando catalogo privado desde la Boveda Secreta ($($localCfg.catalog_gist_id))..." -ForegroundColor Cyan
                $vaultJson = gh api "/gists/$($localCfg.catalog_gist_id)" --jq '.files[] | .content' 2>$null
                if (-not $vaultJson) {
                    $vaultJson = gh gist view $localCfg.catalog_gist_id -f repos.local.json 2>$null
                }
                if ($vaultJson -and $vaultJson.Trim().StartsWith("[")) {
                    $vaultJson | Out-File -FilePath $localCat -Encoding utf8
                    Write-Host "    [OK] Catalogo privado actualizado desde la Boveda." -ForegroundColor Green
                }
            }
        } catch {}
    }
}

# Resolver catalogo: repos.local.json (si existe) o repos.json
$catalogFile = Join-Path $scriptDir "repos.local.json"
if (-not (Test-Path $catalogFile)) {
    $catalogFile = Join-Path $scriptDir "repos.json"
}

# Resolver directorio de repositorios (respeta config.local.json si se personalizo)
if (-not $TargetDir) {
    $localCfgFile = Join-Path $scriptDir "config.local.json"
    if (Test-Path $localCfgFile) {
        try {
            $localCfg = Get-Content $localCfgFile -Raw -Encoding UTF8 | ConvertFrom-Json
            if ($localCfg.repos_dir -and (Test-Path $localCfg.repos_dir)) {
                $reposDir = $localCfg.repos_dir
            }
        } catch {}
    }
    if (-not $reposDir) {
        $parentDir = Split-Path -Parent $scriptDir
        $parentName = Split-Path -Leaf $parentDir
        $knownOrgs = @("Personal", "th-mex", "w-amarillo", "w-azul", "w-naranja", "interpec", "w-pluma", "w-ic", "bf-agency", "WeHubs-io")

        # Si GitDoctor reside dentro de una organizacion, la raiz de repos es el padre superior
        if ($knownOrgs -contains $parentName -or $parentName -eq "Personal") {
            $reposDir = Split-Path -Parent $parentDir
        } else {
            $reposDir = $parentDir
        }
    }
} else {
    $reposDir = $TargetDir
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  GitDoctor -- Sincronizador Multihilo de Repositorios  " -ForegroundColor Cyan
Write-Host "  Directorio de Repos: $reposDir" -ForegroundColor DarkGray
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 0. Auto-actualizar GitDoctor si es repositorio Git
if (Test-Path (Join-Path $scriptDir ".git")) {
    $syncRemote = git -C $scriptDir remote get-url origin 2>$null
    if ($syncRemote) {
        Write-Host "[*] Comprobando actualizaciones de GitDoctor..." -ForegroundColor DarkGray
        git -C $scriptDir pull -q --ff-only 2>$null
    }
}

# Auto-reajuste silencioso (permisos, lanzadores y comandos globales)
$setupWin = Join-Path $scriptDir "setup-windows.ps1"
if (Test-Path $setupWin) {
    try {
        powershell -ExecutionPolicy Bypass -File $setupWin -Reajuste | Out-Null
    } catch {}
}

# Limpiar junctions y symlinks viejos o rotos en la raiz de repos
foreach ($legacy in @("_sync", "repos-sync")) {
    $legacyPath = Join-Path $reposDir $legacy
    if (Test-Path $legacyPath) {
        $item = Get-Item $legacyPath -Force -ErrorAction SilentlyContinue
        if ($item -and $item.LinkType) {
            Remove-Item -Path $legacyPath -Force -Recurse -ErrorAction SilentlyContinue
        }
    }
}

# 1. Actualizar catalogo si se solicita o no existe
if ($UpdateCatalog -or (-not (Test-Path $catalogFile))) {
    Write-Host "[*] Escaneando repositorios con remoto para actualizar repos.json..." -ForegroundColor Yellow
    $entries = @()
    Get-ChildItem -Path $reposDir -Directory | ForEach-Object {
        $gName = $_.Name
        if ($gName -in @("_gitdoctor", "_sync", "gitdoctor", "repos-sync")) { return }

        if (Test-Path (Join-Path $_.FullName ".git")) {
            $remote = git -C $_.FullName remote get-url origin 2>$null
            if ($remote) {
                $branch = git -C $_.FullName branch --show-current 2>$null
                $entries += [PSCustomObject]@{
                    name = $_.Name
                    group = "General"
                    path = $_.Name
                    url = $remote.Trim()
                    defaultBranch = if ($branch) { $branch.Trim() } else { "main" }
                }
            }
        } else {
            $subFolders = Get-ChildItem -Path $_.FullName -Directory
            foreach ($s in $subFolders) {
                if (Test-Path (Join-Path $s.FullName ".git")) {
                    $remote = git -C $s.FullName remote get-url origin 2>$null
                    if ($remote) {
                        $branch = git -C $s.FullName branch --show-current 2>$null
                        $entries += [PSCustomObject]@{
                            name = $s.Name
                            group = $gName
                            path = "$gName/$($s.Name)"
                            url = $remote.Trim()
                            defaultBranch = if ($branch) { $branch.Trim() } else { "main" }
                        }
                    }
                }
            }
        }
    }
    $json = $entries | ConvertTo-Json -Depth 3
    [System.IO.File]::WriteAllText($catalogFile, $json, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "[OK] Catalogo repos.json actualizado ($($entries.Count) repositorios).`n" -ForegroundColor Green
}

if (-not (Test-Path $catalogFile)) {
    Write-Host "[ERROR] No se encontro repos.json en $scriptDir." -ForegroundColor Red
    exit 1
}

$catalog = Get-Content $catalogFile -Raw -Encoding UTF8 | ConvertFrom-Json

# Si el catalogo actual es la plantilla publica de ejemplo, no intentar clonar repos falsos
$isDummy = ($catalog | Where-Object { $_.name -like "*mi-proyecto*" -or $_.url -like "*mi-organizacion*" })
if ($isDummy -and (-not (Test-Path (Join-Path $scriptDir "repos.local.json")))) {
    Write-Host "[INFO] Se detecto la plantilla repos.json de ejemplo. Ejecuta el instalador o 'gitdoctor /catalogo' para escanear tus proyectos reales.`n" -ForegroundColor Yellow
    exit 0
}

# Leer configuracion local de maquina (organizaciones habilitadas/deshabilitadas)
$localCfgFile = Join-Path $scriptDir "config.local.json"
$disabledOrgs = @()
if (Test-Path $localCfgFile) {
    try {
        $localCfg = Get-Content $localCfgFile -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($localCfg.disabled_orgs) { $disabledOrgs = @($localCfg.disabled_orgs) }
    } catch {}
}
if ($disabledOrgs.Count -gt 0) {
    $catalog = @($catalog | Where-Object { $_.group -notin $disabledOrgs })
    Write-Host "[INFO] Sincronizacion selectiva activa: Omitiendo $($disabledOrgs.Count) organizaciones ($($disabledOrgs -join ', '))" -ForegroundColor DarkGray
}

# 2. Verificar y clonar repositorios faltantes
if ($AutoClone) {
    foreach ($item in $catalog) {
        if ($item.name -in @("gitdoctor", "repos-sync") -or ($item.url -and ($item.url.ToLower().EndsWith("/gitdoctor.git") -or $item.url.ToLower().EndsWith("/repos-sync.git")))) {
            continue
        }

        $relPath = if ($item.path) { $item.path -replace '/', '\' } elseif ($item.group) { "$($item.group)\$($item.name)" } else { $item.name }
        $targetPath = Join-Path $reposDir $relPath
        $targetParent = Split-Path -Parent $targetPath
        if (-not (Test-Path $targetParent)) {
            New-Item -ItemType Directory -Path $targetParent -Force | Out-Null
        }

        if (-not (Test-Path $targetPath)) {
            Write-Host "[CLONE] Clonando repositorio faltante: $($item.group)/$($item.name)..." -ForegroundColor Magenta
            git clone $item.url $targetPath
            if ($LASTEXITCODE -eq 0) {
                Write-Host "        [OK] $($item.name) clonado con exito.`n" -ForegroundColor Green
            } else {
                Write-Host "        [ERROR] No se pudo clonar $($item.name).`n" -ForegroundColor Red
            }
        }
    }
}

# 3. Comprobar estado de cada repositorio
Write-Host "[*] Verificando estado y sincronizacion con GitHub..." -ForegroundColor Yellow

$report = @()

foreach ($item in $catalog) {
    if ($item.name -in @("gitdoctor", "repos-sync") -or ($item.url -and ($item.url.ToLower().EndsWith("/gitdoctor.git") -or $item.url.ToLower().EndsWith("/repos-sync.git")))) {
        continue
    }

    $rName = $item.name
    $rGroup = if ($item.group) { $item.group } else { "General" }
    $relPath = if ($item.path) { $item.path -replace '/', '\' } elseif ($item.group) { "$($item.group)\$($item.name)" } else { $item.name }
    $rPath = Join-Path $reposDir $relPath

    if (-not (Test-Path $rPath)) {
        $report += [PSCustomObject]@{
            Grupo = $rGroup
            Repositorio = $rName
            Rama = "-"
            Estado = "[NO CLONADO]"
            Detalle = "Ejecuta .\sync.ps1"
        }
        continue
    }

    $isGit = Test-Path (Join-Path $rPath ".git")
    if (-not $isGit) {
        $report += [PSCustomObject]@{
            Grupo = $rGroup
            Repositorio = $rName
            Rama = "-"
            Estado = "[NO ES GIT]"
            Detalle = "Carpeta sin .git"
        }
        continue
    }

    $branch = git -C $rPath branch --show-current 2>$null
    if (-not $branch) { $branch = "(detached)" }

    # Fetch silencioso de origin
    git -C $rPath fetch origin -q --prune 2>$null

    # Cambios locales no commiteados
    $statusLines = @(git -C $rPath status --porcelain 2>$null)
    $hasDirty = ($statusLines.Count -gt 0)

    # Verificar tracking upstream
    $upstream = git -C $rPath rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null

    $ahead = 0
    $behind = 0
    $isLocalOnly = $false

    if ($upstream) {
        $aheadCount = git -C $rPath rev-list --count '@{u}..HEAD' 2>$null
        $behindCount = git -C $rPath rev-list --count 'HEAD..@{u}' 2>$null
        if ($aheadCount) { $ahead = [int]$aheadCount }
        if ($behindCount) { $behind = [int]$behindCount }
    } else {
        $hasRemoteBranch = git -C $rPath rev-parse --verify "origin/$branch" 2>$null
        if ((-not $hasRemoteBranch) -and ($branch -ne "(detached)")) {
            $isLocalOnly = $true
        }
    }

    # Auto-Pull si esta detras y limpio
    $pullStatus = ""
    if (($behind -gt 0) -and (-not $hasDirty) -and $AutoPull) {
        git -C $rPath pull -q --ff-only 2>$null
        if ($LASTEXITCODE -eq 0) {
            $pullStatus = " (pull OK)"
            $behind = 0
        } else {
            $pullStatus = " (pull fallo)"
        }
    }

    # Determinar estado
    $estadoStr = ""
    $detalleStr = ""

    if ($hasDirty -and ($ahead -gt 0)) {
        $estadoStr = "[CAMBIOS LOCALES + PUSH]"
        $detalleStr = "$($statusLines.Count) modif. y $ahead commit(s) pendientes de subir"
    } elseif ($hasDirty) {
        $estadoStr = "[CAMBIOS LOCALES]"
        $detalleStr = "$($statusLines.Count) archivo(s) sin commit"
    } elseif ($isLocalOnly) {
        $estadoStr = "[RAMA SOLO LOCAL]"
        $detalleStr = "Rama no existe en GitHub (corre git push -u origin $branch)"
    } elseif (($ahead -gt 0) -and ($behind -gt 0)) {
        $estadoStr = "[DESVIADO / MERGE]"
        $detalleStr = "$ahead adelante, $behind atras"
    } elseif ($ahead -gt 0) {
        $estadoStr = "[PENDIENTE PUSH]"
        $detalleStr = "$ahead commit(s) por subir a GitHub"
    } elseif ($behind -gt 0) {
        $estadoStr = "[ACTUALIZACION DISP]"
        $detalleStr = "$behind commit(s) en GitHub por bajar"
    } else {
        $estadoStr = "[AL DIA]"
        if ($pullStatus) {
            $detalleStr = "Actualizado exitosamente"
        } else {
            $detalleStr = "Limpio y sincronizado"
        }
    }

    $report += [PSCustomObject]@{
        Grupo = $rGroup
        Repositorio = $rName
        Rama = $branch
        Estado = $estadoStr
        Detalle = $detalleStr
    }
}

# Mostrar agrupado por Organizacion
$groupedReport = $report | Group-Object Grupo
$sep = "-" * 70
foreach ($grp in $groupedReport) {
    $header = if ($grp.Name -eq "Personal") { "[Personal: $($grp.Name)]" } else { "[Organizacion: $($grp.Name)]" }
    Write-Host ""
    Write-Host "  $header -- $($grp.Count) repositorios" -ForegroundColor White
    Write-Host "  $sep" -ForegroundColor DarkGray
    $grp.Group | Select-Object Repositorio, Rama, Estado, Detalle | Format-Table -AutoSize
}

# 4. Resumen
$dirtyCount = @($report | Where-Object { $_.Estado -like "*CAMBIOS LOCALES*" }).Count
$pushCount  = @($report | Where-Object { $_.Estado -like "*PENDIENTE PUSH*" }).Count
$localOnly  = @($report | Where-Object { $_.Estado -like "*RAMA SOLO LOCAL*" }).Count
$upToDate   = @($report | Where-Object { $_.Estado -like "*AL DIA*" }).Count

Write-Host "--------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "Resumen: $upToDate al dia | $dirtyCount con cambios locales | $pushCount pendientes de push | $localOnly ramas solo locales" -ForegroundColor Cyan
if (($dirtyCount -gt 0) -or ($pushCount -gt 0) -or ($localOnly -gt 0)) {
    Write-Host "[!] ATENCION: Tienes cambios locales, ramas o commits por subir antes de cambiar de maquina." -ForegroundColor Yellow
} else {
    Write-Host "[OK] Todo en orden. Puedes cambiar a la Mac con total tranquilidad." -ForegroundColor Green
}
Write-Host "========================================================`n" -ForegroundColor Cyan
