$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "scripts\common.ps1")

$root = Get-ProjectRoot
$python = Initialize-Venv -Requirements "requirements-dev.txt"

$pyinstallerArgs = @(
    "-m", "PyInstaller",
    "--noconfirm", "--clean", "--windowed", "--onefile",
    "--name", "Pokedex-Kanto",
    "--add-data", "assets;assets"
)

$pyinstallerArgs += "main.py"

Push-Location $root
try {
    & $python @pyinstallerArgs
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o executável." }
} finally {
    Pop-Location
}

Write-Host "Executável criado em: dist\Pokedex-Kanto.exe"
