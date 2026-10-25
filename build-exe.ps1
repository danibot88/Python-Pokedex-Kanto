$ErrorActionPreference = "Stop"

function Find-Python {
    $bundled = "C:\Users\Pichau\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
    if (Test-Path $bundled) { return $bundled }

    foreach ($command in @("py", "python", "python3")) {
        $found = Get-Command $command -ErrorAction SilentlyContinue
        if ($found) { return $found.Source }
    }

    throw "Python não foi encontrado. Instale o Python 3.11+ em https://python.org/downloads/ e tente novamente."
}

$python = Find-Python
if (-not (Test-Path ".venv")) {
    & $python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean --windowed --onefile `
    --name "Pokedex-Kanto" `
    --add-data "assets;assets" `
    main.py
Write-Host "Executável criado em: dist\Pokedex-Kanto.exe"
