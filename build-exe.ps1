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

# Alguns Pythons embarcados (ex.: runtimes com patch de CA) carregam um PEM
# extra ao criar o contexto SSL. Empacotamos o arquivo quando ele existir para
# que as requisições HTTPS funcionem também no executável.
$sslDir = (& $python -c "import ssl, os; print(os.path.dirname(ssl.__file__))").Trim()
$sslPatch = Join-Path $sslDir "codex-rejected-cas.pem"
if (Test-Path $sslPatch) {
    Write-Host "Incluindo o pacote de CA do Python local: $sslPatch"
    $pyinstallerArgs += @("--add-data", "$sslPatch;.")
}

$pyinstallerArgs += "main.py"

Push-Location $root
try {
    & $python @pyinstallerArgs
    if ($LASTEXITCODE -ne 0) { throw "Falha ao gerar o executável." }
} finally {
    Pop-Location
}

Write-Host "Executável criado em: dist\Pokedex-Kanto.exe"
