<#
.SYNOPSIS
    Ambient Chrysalis Gateway Daemon Launcher for Windows ARM64 (golem).
.DESCRIPTION
    Launches the FastAPI gateway daemon using the isolated Python virtual environment at C:\venvs\chrysalis-gateway.
#>

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$LocalVenv = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$GlobalVenv = "C:\venvs\chrysalis-gateway\Scripts\python.exe"

if (Test-Path $LocalVenv) {
    $PythonExe = $LocalVenv
} elseif (Test-Path $GlobalVenv) {
    $PythonExe = $GlobalVenv
} else {
    $PythonExe = (Get-Command python -ErrorAction SilentlyContinue).Source
    if (-not $PythonExe) {
        Write-Error "Python not found. Please create a virtual environment with 'python -m venv .venv' and install requirements."
        exit 1
    }
}

$Port = if ($env:CHRYSALIS_GATEWAY_PORT) { $env:CHRYSALIS_GATEWAY_PORT } elseif ($env:CHRYALIS_GATEWAY_PORT) { $env:CHRYALIS_GATEWAY_PORT } else { "8765" }
Write-Host "Starting Ambient Chrysalis Gateway on port $Port..." -ForegroundColor Cyan
Set-Location $ScriptDir
& $PythonExe -m uvicorn main:app --host 0.0.0.0 --port $Port
