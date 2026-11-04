$ErrorActionPreference = "Stop"

function Get-ProjectRoot {
    return (Split-Path -Parent $PSScriptRoot)
}

function Find-Python {
    if ($env:POKEDEX_PYTHON) {
        if (-not (Test-Path $env:POKEDEX_PYTHON)) {
            throw "POKEDEX_PYTHON aponta para um caminho inexistente: $env:POKEDEX_PYTHON"
        }
        return $env:POKEDEX_PYTHON
    }

    foreach ($command in @("py", "python", "python3")) {
        $found = Get-Command $command -ErrorAction SilentlyContinue
        if (-not $found) { continue }

        $version = & $found.Source -c "import sys; print(sys.version_info[0], sys.version_info[1])" 2>$null
        if ($LASTEXITCODE -ne 0 -or -not $version) { continue }

        $parts = ($version -join " ").Trim().Split(" ")
        if ($parts.Count -ge 2 -and [int]$parts[0] -eq 3 -and [int]$parts[1] -ge 10) {
            return $found.Source
        }
    }

    throw "Python 3.10+ não encontrado. Instale em https://python.org/downloads/ ou defina a variável POKEDEX_PYTHON."
}

function Initialize-Venv {
    param([Parameter(Mandatory = $true)][string] $Requirements)

    $root = Get-ProjectRoot
    $venvPython = Join-Path $root ".venv\Scripts\python.exe"

    if (-not (Test-Path $venvPython)) {
        $python = Find-Python
        Write-Host "Criando o ambiente virtual em .venv ..."
        & $python -m venv (Join-Path $root ".venv")
        if ($LASTEXITCODE -ne 0) { throw "Falha ao criar o ambiente virtual." }
    }

    # Reinstala apenas quando algum requirements*.txt muda.
    $snapshot = (Get-ChildItem -Path $root -Filter "requirements*.txt" | Sort-Object Name | ForEach-Object {
        "$($_.Name):$((Get-Content $_.FullName -Raw))"
    }) -join "`n"
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = [System.Text.Encoding]::UTF8.GetBytes($snapshot)
        $hash = ([System.BitConverter]::ToString($sha.ComputeHash($bytes))).Replace("-", "")
    } finally {
        $sha.Dispose()
    }

    # Cada conjunto tem seu próprio marcador: instalar apenas os requisitos
    # do aplicativo não significa que as ferramentas de desenvolvimento existem.
    $marker = Join-Path $root ".venv\.$Requirements.sha256"
    $current = if (Test-Path $marker) { (Get-Content $marker -Raw).Trim() } else { "" }

    if ($current -ne $hash) {
        Write-Host "Instalando as dependências de $Requirements ..."
        & $venvPython -m pip install --disable-pip-version-check --quiet -r (Join-Path $root $Requirements)
        if ($LASTEXITCODE -ne 0) { throw "Falha ao instalar as dependências." }
        Set-Content -Path $marker -Value $hash -Encoding ascii
    }

    return $venvPython
}
