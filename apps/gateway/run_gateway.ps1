param([string]$Python)

$ErrorActionPreference = 'Stop'
if (-not $Python) {
    $Python = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
}
if (-not (Test-Path -LiteralPath $Python)) {
    throw 'Create a local .venv and install requirements.txt, or pass -Python with the configured interpreter.'
}
Push-Location $PSScriptRoot
try {
    # main.py owns host, port, and backend configuration.
    & $Python (Join-Path $PSScriptRoot 'main.py')
    if ($LASTEXITCODE -ne 0) { throw "Gateway exited with code $LASTEXITCODE" }
} finally {
    Pop-Location
}
