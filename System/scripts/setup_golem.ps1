<#
.SYNOPSIS
    Chrysalis mdbase v0.3 Setup & Validation Utility for Golem (Windows on Arm).

.DESCRIPTION
    Scaffolds the authoritative Chrysalis mdbase v0.3 vault layout on Golem,
    deploys core schemas, contracts, workflows, and life roadmap, executes
    the local validation harness, and optionally configures an unkillable 24/7
    Windows Scheduled Task for the mdbase connect daemon.

.PARAMETER VaultPath
    Target path for the Chrysalis vault. Defaults to $env:USERPROFILE\Documents\Chrysalis.

.PARAMETER RegisterDaemonTask
    Switch to register a continuous 24/7 Scheduled Task for mdbase connect.

.EXAMPLE
    .\setup_golem.ps1 -VaultPath "$env:USERPROFILE\Documents\Chrysalis" -RegisterDaemonTask
#>

[CmdletBinding()]
param(
    [string]$VaultPath = "$env:USERPROFILE\Documents\Chrysalis",
    [switch]$RegisterDaemonTask = $false
)

$ErrorActionPreference = "Stop"

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  Chrysalis mdbase v0.3 Setup & Validation Engine for Golem       " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan

# 1. Environment & Architecture Audit
Write-Host "`n[1/5] Auditing Host Environment..." -ForegroundColor Yellow
$arch = $env:PROCESSOR_ARCHITECTURE
Write-Host "  Processor Architecture : $arch" -ForegroundColor Gray
if ($arch -ne "ARM64") {
    Write-Host "  Note: Expected ARM64 on Golem (Surface Pro X), detected $arch. Continuing under Prism/WOW64..." -ForegroundColor DarkYellow
}

# Verify Python
try {
    $pythonVer = (python --version 2>&1)
    Write-Host "  Python Version         : $pythonVer" -ForegroundColor Green
} catch {
    Write-Error "Python 3.10+ is required but was not found in PATH. Please install Python and retry."
}

# Verify mdbase CLI
$mdbaseCmd = Get-Command "mdbase" -ErrorAction SilentlyContinue
if ($mdbaseCmd) {
    Write-Host "  mdbase CLI             : Found at $($mdbaseCmd.Source)" -ForegroundColor Green
} else {
    Write-Host "  mdbase CLI             : Not found in PATH. (Install via npm i -g @mdbase/cli or place mdbase.exe in PATH)" -ForegroundColor Yellow
}

# 2. Directory Scaffolding
Write-Host "`n[2/5] Scaffolding Authoritative Vault at: $VaultPath" -ForegroundColor Yellow

$requiredDirs = @(
    "$VaultPath\_types",
    "$VaultPath\_contracts",
    "$VaultPath\_templates",
    "$VaultPath\System",
    "$VaultPath\System\_templates",
    "$VaultPath\System\scripts",
    "$VaultPath\TaskNotes\Tasks",
    "$VaultPath\TaskNotes\Archive",
    "$VaultPath\TaskNotes\Workflows",
    "$VaultPath\TaskNotes\Views",
    "$VaultPath\TaskNotes\_templates",
    "$VaultPath\Projects\_templates",
    "$VaultPath\Slipbox\_templates",
    "$VaultPath\Sources"
)

foreach ($dir in $requiredDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}

# 3. Deploying Configuration & Schemas
Write-Host "`n[3/5] Deploying mdbase v0.3 Schemas, Workflows & Contracts..." -ForegroundColor Yellow
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = (Resolve-Path "$ScriptDir\..\..").Path

$isSelfVault = $false
try {
    $ResolvedVault = (Resolve-Path -Path $VaultPath -ErrorAction SilentlyContinue)
    if ($ResolvedVault -and ($ResolvedVault.Path -eq $RepoRoot)) {
        $isSelfVault = $true
    }
} catch {
    $isSelfVault = $false
}

if ($isSelfVault) {
    Write-Host "  Vault directory is the repository checkout ($VaultPath)." -ForegroundColor Green
    Write-Host "  Schemas, workflows, and contracts already in place; skipping copy." -ForegroundColor Gray
} else {
    # Copy mdbase.yaml
    if (Test-Path "$RepoRoot\mdbase.yaml") {
        Copy-Item "$RepoRoot\mdbase.yaml" "$VaultPath\mdbase.yaml" -Force
        Write-Host "  Copied: mdbase.yaml" -ForegroundColor Green
    }

    # Copy _types
    if (Test-Path "$RepoRoot\_types") {
        Copy-Item "$RepoRoot\_types\*.md" "$VaultPath\_types\" -Force
        Write-Host "  Copied: _types/*.md (task, project, zettel, source schemas)" -ForegroundColor Green
    }

    # Copy _contracts
    if (Test-Path "$RepoRoot\contracts\agent-runtime.contract.md") {
        Copy-Item "$RepoRoot\contracts\agent-runtime.contract.md" "$VaultPath\_contracts\" -Force
        Write-Host "  Copied: _contracts/agent-runtime.contract.md" -ForegroundColor Green
    }

    # Copy Workflows
    if (Test-Path "$RepoRoot\TaskNotes\Workflows") {
        Copy-Item "$RepoRoot\TaskNotes\Workflows\*.md" "$VaultPath\TaskNotes\Workflows\" -Force
        Write-Host "  Copied: TaskNotes/Workflows/*.md" -ForegroundColor Green
    }

    # Seed Life-Roadmap.md
    if (Test-Path "$RepoRoot\System\Life-Roadmap.md") {
        Copy-Item "$RepoRoot\System\Life-Roadmap.md" "$VaultPath\System\Life-Roadmap.md" -Force
        Write-Host "  Seeded: System/Life-Roadmap.md (Pre-configured for 2026-09-22)" -ForegroundColor Green
    } elseif (Test-Path "$RepoRoot\System\_templates\Life-Roadmap.template.md") {
        Copy-Item "$RepoRoot\System\_templates\Life-Roadmap.template.md" "$VaultPath\System\Life-Roadmap.md" -Force
        Write-Host "  Seeded: System/Life-Roadmap.md (from template)" -ForegroundColor Green
    }

    # Seed Memory.md
    if (-not (Test-Path "$VaultPath\System\Memory.md")) {
        if (Test-Path "$RepoRoot\System\_templates\Memory.template.md") {
            Copy-Item "$RepoRoot\System\_templates\Memory.template.md" "$VaultPath\System\Memory.md" -Force
            Write-Host "  Seeded: System/Memory.md (from template)" -ForegroundColor Green
        }
    }
}

# 4. Local Validation Harness Execution
Write-Host "`n[4/5] Executing Chrysalis Validation Harness..." -ForegroundColor Yellow
$harnessScript = "$RepoRoot\tests\harness\validation_harness.py"
if (Test-Path $harnessScript) {
    python $harnessScript -c $VaultPath
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  Harness Status: [PASS] 100% PASS (Zero errors, zero warnings)" -ForegroundColor Green
    } else {
        Write-Host "  Harness Status: [FAIL] Validation reported issues. Review output above." -ForegroundColor Red
    }
} else {
    Write-Host "  Harness script not found at: $harnessScript (Skipping validation check)" -ForegroundColor DarkYellow
}

# 5. Scheduled Task Configuration (Optional)
if ($RegisterDaemonTask) {
    Write-Host "`n[5/5] Registering 24/7 Persistent Windows Scheduled Task..." -ForegroundColor Yellow
    if (-not $mdbaseCmd) {
        Write-Host "  Skipping: mdbase.exe not found in PATH." -ForegroundColor Red
    } else {
        $TaskName = "ChrysalisMdbaseDaemon"
        $Action = New-ScheduledTaskAction -Execute $mdbaseCmd.Source -Argument "connect daemon run" -WorkingDirectory $VaultPath
        $Trigger = New-ScheduledTaskTrigger -AtLogOn
        $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
        
        try {
            Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -User $env:USERNAME -RunLevel Highest -Force | Out-Null
            Start-ScheduledTask -TaskName $TaskName
            Write-Host "  Registered and Started Scheduled Task: $TaskName" -ForegroundColor Green
            Write-Host "  Configured: Unlimited execution time (PT0S) and battery operation permitted." -ForegroundColor Gray
        } catch {
            Write-Host "  Failed to register scheduled task: $_. Please run PowerShell as Administrator." -ForegroundColor Red
        }
    }
} else {
    Write-Host "`n[5/5] Background Task Registration skipped (use -RegisterDaemonTask to configure)." -ForegroundColor Gray
}

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "  Chrysalis Vault Ready on Golem!                                 " -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "1. Pair your collection:  cd '$VaultPath'; mdbase connect init" -ForegroundColor Gray
Write-Host "2. Connect Gemini Spark:  Configure endpoint https://mcp.mdbase.dev/v1/mcp/<grant-id>" -ForegroundColor Gray
Write-Host "3. Follow the test guide: docs/golem-deployment-and-spark-test-guide.md" -ForegroundColor Gray
