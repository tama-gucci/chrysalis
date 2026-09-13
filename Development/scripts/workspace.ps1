param(
    [ValidateSet('preview', 'deploy', 'check', 'rollback-preview', 'rollback')]
    [string]$Action = 'preview',
    [string]$Vault,
    [switch]$Plugins
)

$ErrorActionPreference = 'Stop'
$repository = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
if (-not $Vault) {
    $Vault = Join-Path (Split-Path $repository -Parent) 'vault'
}
$target = [System.IO.Path]::GetFullPath($Vault)
if (-not (Test-Path -LiteralPath (Join-Path $target 'AGENTS.md'))) {
    throw 'Select an existing Chrysalis runtime vault with -Vault.'
}

if ($Action -eq 'check') {
    & python (Join-Path $repository 'System/scripts/doctor.py') --vault $target --read-only
} else {
    $updateArgs = @((Join-Path $repository 'update.py'), '--target', $target)
    if ($Action -like 'rollback*') {
        $updateArgs += '--rollback'
    } else {
        $updateArgs += @('--source', $repository)
        if ($Plugins) { $updateArgs += '--plugins' }
    }
    if ($Action -in @('preview', 'rollback-preview')) { $updateArgs += '--dry-run' }
    & python @updateArgs
}
if ($LASTEXITCODE -ne 0) { throw "Chrysalis $Action failed (exit $LASTEXITCODE)." }

if ($Action -eq 'deploy') {
    & python (Join-Path $repository 'System/scripts/doctor.py') --vault $target --read-only
    if ($LASTEXITCODE -ne 0) {
        throw 'Deployment finished but runtime validation failed. Review findings and use rollback if needed.'
    }
}
