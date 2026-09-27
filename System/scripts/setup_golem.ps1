<#
.SYNOPSIS
    Experimental Windows wrapper for the shared Chrysalis deployment tools.
.DESCRIPTION
    Deploys the canonical mdbase layout and seeds missing state from public
    templates. Windows/ARM execution and external agents require separate validation.
#>
[CmdletBinding()]
param(
    [string]$VaultPath = "$env:USERPROFILE\Documents\Chrysalis",
    [switch]$RegisterDaemonTask = $false
)
$ErrorActionPreference = "Stop"
if ($RegisterDaemonTask) {
    throw "Daemon setup is deferred. Validate the runtime integration separately before enabling a scheduled task."
}
$RepoRoot = (Resolve-Path "$PSScriptRoot\..\..").Path
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python with the dependencies in requirements.txt is required."
}
$Target = [System.IO.Path]::GetFullPath($VaultPath)
if ($Target.TrimEnd('\') -eq $RepoRoot.TrimEnd('\')) {
    throw "Select a separate runtime vault; source checkouts are not runtime targets."
}

# Shared Python tools own file selection, conflict checks, and state preservation.
python "$RepoRoot\update.py" --source $RepoRoot --target $Target
if ($LASTEXITCODE -ne 0) { throw "Framework deployment failed; inspect its report." }
python "$RepoRoot\System\scripts\bootstrap.py" --vault-root $Target
if ($LASTEXITCODE -ne 0) { throw "Bootstrap failed; inspect its report." }
python "$RepoRoot\tests\harness\validation_harness.py" -c $Target
if ($LASTEXITCODE -ne 0) { throw "Validation failed; the runtime is not verified." }

Write-Host "Local framework files deployed and checked."
Write-Host "Obsidian, Windows/ARM runtime behavior, and external-agent integrations require separate verification."
