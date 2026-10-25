$ErrorActionPreference = "Stop"

. (Join-Path $PSScriptRoot "scripts\common.ps1")

$python = Initialize-Venv -Requirements "requirements.txt"
& $python (Join-Path (Get-ProjectRoot) "main.py")
exit $LASTEXITCODE
