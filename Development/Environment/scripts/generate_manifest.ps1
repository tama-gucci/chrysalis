<#
.SYNOPSIS
    Chrysalis Windows System Package Manifest Generator (Pure PowerShell)
.DESCRIPTION
    Captures package telemetry (winget, scoop, choco, or Get-Package), OS info, hardware profile,
    and hardware model into a Chrysalis-compliant System Manifest note.
.PARAMETER SystemName
    Override hostname/system name (default: $env:COMPUTERNAME).
.PARAMETER Role
    System operational role (default: "At-Home Server" or detected role).
.PARAMETER Status
    Operational status (default: "active").
.PARAMETER Output
    Custom output markdown file path.
.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\generate_manifest.ps1 -SystemName "surface-pro-x" -Role "At-Home Server"
#>
[CmdletBinding()]
param (
    [string]$SystemName = "",
    [string]$Role = "",
    [string]$Status = "active",
    [string]$Output = ""
)

$ErrorActionPreference = "SilentlyContinue"

# Timestamp with local timezone
$now = [DateTimeOffset]::Now
$timestamp = $now.ToString("yyyy-MM-ddTHH:mm:sszzz")

# Detect System Info
if (-not $SystemName) {
    $SystemName = $env:COMPUTERNAME.ToLower()
}
$hostname = $env:COMPUTERNAME

$osInfo = Get-CimInstance Win32_OperatingSystem
$osName = if ($osInfo.Caption) { $osInfo.Caption -replace "Microsoft ", "" } else { "Windows" }
$kernel = "Windows NT $($osInfo.Version)"
$arch = $env:PROCESSOR_ARCHITECTURE

# Detect hardware model
$compSys = Get-CimInstance Win32_ComputerSystem
$model = if ($compSys.Model) { $compSys.Model.Trim() } else { "" }

# Detect chassis
$enclosure = Get-CimInstance Win32_SystemEnclosure
$chassisTypes = $enclosure.ChassisTypes
$chassis = "desktop"
foreach ($t in $chassisTypes) {
    if ($t -in 30, 31, 32) { $chassis = "tablet"; break }
    elseif ($t -in 8, 9, 10, 11, 14) { $chassis = "laptop"; break }
    elseif ($t -in 17, 23, 28) { $chassis = "server"; break }
    elseif ($t -in 3, 4, 5, 6, 7) { $chassis = "desktop"; break }
}

# Role inference
if (-not $Role) {
    if ($SystemName -like "*server*" -or $chassis -eq "server") {
        $Role = "At-Home Server"
    } elseif ($model -like "*Surface*" -or $chassis -eq "tablet") {
        $Role = "At-Home Server (Surface Node)"
    } elseif ($chassis -eq "laptop") {
        $Role = "Mobile Laptop"
    } else {
        $Role = "Primary Workstation"
    }
}

# Collect Packages
$packageManager = "manual"
$nativePkgs = [ordered]@{}
$foreignPkgs = [ordered]@{}

if (Get-Command winget -ErrorAction SilentlyContinue) {
    $packageManager = "winget"
    try {
        $wingetOut = & winget list --accept-source-agreements | Out-String
        $lines = $wingetOut -split "`r?`n"
        $headerFound = $false
        foreach ($line in $lines) {
            if ($line -like "---*") {
                $headerFound = $true
                continue
            }
            if ($headerFound -and $line.Trim().Length -gt 0) {
                $parts = ($line.Trim() -split '\s{2,}')
                if ($parts.Count -ge 3) {
                    $id = $parts[1].Trim()
                    $ver = $parts[2].Trim()
                    $src = if ($parts.Count -ge 4) { $parts[3].Trim() } else { "winget" }
                    if ($src.ToLower() -eq "winget") {
                        $nativePkgs[$id] = $ver
                    } else {
                        $foreignPkgs[$id] = "$ver ($src)"
                    }
                }
            }
        }
    } catch {
        Write-Warning "winget parsing warning: $_"
    }
} elseif (Get-Command scoop -ErrorAction SilentlyContinue) {
    $packageManager = "scoop"
    try {
        $scoopList = & scoop list | Out-String
        $lines = $scoopList -split "`r?`n"
        foreach ($line in $lines) {
            $parts = $line.Trim() -split '\s+'
            if ($parts.Count -ge 2 -and $parts[0] -notin @("Name", "----", "Installed")) {
                $name = $parts[0]
                $ver = $parts[1]
                $src = if ($parts.Count -ge 3) { $parts[2] } else { "main" }
                if ($src.ToLower() -eq "main") { $nativePkgs[$name] = $ver }
                else { $foreignPkgs[$name] = "$ver ($src)" }
            }
        }
    } catch {}
} elseif (Get-Command choco -ErrorAction SilentlyContinue) {
    $packageManager = "choco"
    try {
        $chocoList = & choco list --local-only --limit-output
        foreach ($line in $chocoList) {
            if ($line -match '^([^|]+)\|([^|]+)') {
                $nativePkgs[$matches[1]] = $matches[2]
            }
        }
    } catch {}
} else {
    $packageManager = "windows-pkg"
    try {
        $pkgs = Get-Package -ErrorAction SilentlyContinue
        foreach ($p in $pkgs) {
            if ($p.ProviderName -in @("Programs", "msi")) {
                $nativePkgs[$p.Name] = $p.Version
            } else {
                $foreignPkgs[$p.Name] = "$($p.Version) ($($p.ProviderName))"
            }
        }
    } catch {}
}

$nativeCount = $nativePkgs.Count
$foreignCount = $foreignPkgs.Count
$totalCount = $nativeCount + $foreignCount

# Build JSON Telemetry
$jsonObj = [ordered]@{
    timestamp = $timestamp
    system_name = $SystemName
    hostname = $hostname
    model = $model
    host_os = $osName
    kernel = $kernel
    arch = $arch
    chassis = $chassis
    role = $Role
    package_manager = $packageManager
    package_counts = [ordered]@{
        native_explicit = $nativeCount
        foreign_explicit = $foreignCount
        total_explicit = $totalCount
    }
    native_packages = $nativePkgs
    foreign_packages = $foreignPkgs
}

$jsonStr = $jsonObj | ConvertTo-Json -Depth 5

$modelLine = if ($model) { " • **Model:** $model" } else { "" }
$modelBullet = if ($model) { "* **Hardware Model:** $model`n" } else { "" }

# Format Manifest Content
$content = @"
---
type: system_manifest
id: "system-manifest-$SystemName"
system_name: "$SystemName"
hostname: "$hostname"
os: "$osName"
arch: "$arch"
kernel: "$kernel"
chassis: "$chassis"
role: "$Role"
package_manager: "$packageManager"
generated_at: "$timestamp"
last_updated: "$timestamp"
status: "$Status"
total_explicit_packages: $totalCount
native_count: $nativeCount
foreign_count: $foreignCount
tags:
  - system/manifest
  - system/$SystemName
---

# 🖥️ $SystemName System Package Manifest

> **Captured:** $timestamp  
> **Host OS:** $osName ($kernel) • **Arch:** $arch • **Chassis:** $chassis$modelLine  
> **Native Explicit Packages (`$packageManager`):** $nativeCount  
> **Foreign / User Packages:** $foreignCount  
> **Total Explicit Packages:** $totalCount

---

## 📋 System Profile & Hardware Role

* **System Name / Hostname:** `$hostname`
$modelBullet* **Role:** $Role
* **Operating System:** $osName
* **Kernel & Architecture:** `$kernel` (`$arch`)
* **Chassis Type:** `$chassis`
* **Package Manager Substrate:** `$packageManager`
* **Operational Status:** `$Status`

---

## 📦 Package Inventory Telemetry

```json
$jsonStr
```
"@

# Write to file
if (-not $Output) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $envDir = Split-Path -Parent $scriptDir
    $Output = Join-Path $envDir "$SystemName.md"
}

$outputDir = Split-Path -Parent $Output
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir -Force | Out-Null
}

[System.IO.File]::WriteAllText($Output, $content, [System.Text.Encoding]::UTF8)

Write-Host "✅ Successfully wrote manifest for '$SystemName' to: $Output" -ForegroundColor Green
if ($model) {
    Write-Host "   Hardware Model: $model ($arch)"
}
Write-Host "   Packages: $nativeCount native, $foreignCount foreign (Total: $totalCount)"
