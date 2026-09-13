---
type: system_environment_index
id: chrysalis-environment-index
title: Environment & System Manifests Index
last_updated: "2026-09-01T23:11:15-05:00"
---

# 🌐 Chrysalis Environment & Multi-System Manifests

The **Environment Substrate** tracks host machines, hardware roles, operating systems, and explicit package telemetry across all computational environments used within the Chrysalis ecosystem.

## 🎯 Active Deployment Profile

* **[[Active-Profile|Active-Profile.md]]**
  * Create this private file from [_templates/Active-Profile.template.md](_templates/Active-Profile.template.md).
  * Record the selected storage, orchestrator, and devices there. No dedicated server is required.

---

## 🖥️ Registered Systems Registry

```dataview
TABLE
    hostname as "Hostname",
    os as "Operating System",
    role as "Role",
    chassis as "Chassis",
    package_manager as "Pkg Mgr",
    total_explicit_packages as "Explicit Pkgs",
    last_updated as "Last Updated",
    status as "Status"
FROM "System/Environment"
WHERE type = "system_manifest"
SORT system_name ASC
```

### Example system node
* `[[station-node]]` is a synthetic name, not an installed machine. Actual nodes appear in the private manifests listed above.

---

## 🛠️ Onboarding a New System

To add a new system node (laptop, secondary workstation, home server, edge device, VPS, or VM):

### Method 1: Automated Manifest Generator (Recommended)

#### On Linux / macOS (Python):
```bash
# Auto-detects OS, chassis, package manager, and packages:
python3 System/Environment/scripts/generate_manifest.py

# Or specify custom name and role:
python3 System/Environment/scripts/generate_manifest.py --system-name "laptop-node" --role "Mobile Laptop"
```

#### On Windows PCs (PowerShell - Zero Dependencies):
```powershell
# Run directly from PowerShell (auto-detects Windows edition, Surface hardware model, winget/scoop/choco):
powershell -ExecutionPolicy Bypass -File .\System\Environment\scripts\generate_manifest.ps1

# Or specify custom name and role (e.g. for Surface Pro X home server):
powershell -ExecutionPolicy Bypass -File .\System\Environment\scripts\generate_manifest.ps1 -SystemName "server-node" -Role "At-Home Server"
```

#### On Windows PCs (Python):
```cmd
python System\Environment\scripts\generate_manifest.py --system-name "server-node" --role "At-Home Server"
```

### Method 2: Manual Template Instantiation
1. Copy the template from `[[_templates/System-Manifest-Template|System-Manifest-Template.md]]` to `System/Environment/<system_name>.md`.
2. Extract explicit packages using the appropriate native command:
   * **Windows (winget):** `winget list --source winget` (native) and `winget list` (all)
   * **Windows (scoop):** `scoop list`
   * **Windows (choco):** `choco list --local-only`
   * **Windows (PowerShell):** `Get-Package`
   * **Arch Linux:** `pacman -Qne` (native) and `pacman -Qme` (AUR/foreign)
   * **Debian / Ubuntu:** `apt-mark showmanual`
   * **Fedora / RHEL:** `dnf repoquery --userinstalled`
   * **macOS:** `brew leaves` (formulae) and `brew list --cask` (casks)
   * **Alpine Linux:** `apk info -e`
   * **Nix / NixOS:** `nix-env -q`
3. Populate the frontmatter and embedded JSON telemetry.

---

## 📋 Manifest Frontmatter Schema Reference

```yaml
---
type: system_manifest
id: "system-manifest-<system_name>"
system_name: "<system_name>"
hostname: "<hostname>"
os: "<Operating System>"
arch: "<Architecture, e.g., x86_64, aarch64>"
kernel: "<Kernel release>"
chassis: "<desktop | laptop | server | vm | sbc>"
role: "<Primary Workstation | Mobile Laptop | Home Server | etc.>"
package_manager: "<pacman | apt | dnf | brew | nix | apk>"
generated_at: "YYYY-MM-DDTHH:mm:ss-05:00"
last_updated: "YYYY-MM-DDTHH:mm:ss-05:00"
status: "active" # active, maintenance, decommissioned
total_explicit_packages: <integer>
native_count: <integer>
foreign_count: <integer>
tags:
  - system/manifest
  - system/<system_name>
---
```
