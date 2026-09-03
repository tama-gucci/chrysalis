#!/usr/bin/env python3
"""
Chrysalis Multi-System Manifest Generator
Captures package telemetry, OS info, and hardware profile into a Chrysalis-compliant System Manifest note.
Supports Linux (pacman, apt, dnf), macOS (brew), and Windows (winget, scoop, choco, Get-Package).

Usage:
    python generate_manifest.py [--system-name NAME] [--role ROLE] [--output PATH]
"""

import argparse
import datetime
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
from pathlib import Path


def get_local_iso_timestamp() -> str:
    """Returns local ISO 8601 timestamp with explicit timezone offset (e.g. -05:00)."""
    now = datetime.datetime.now().astimezone()
    return now.isoformat()


def detect_system_info(custom_name=None, custom_role=None):
    """Detects hostname, OS, kernel, arch, model, chassis, and role."""
    hostname = custom_name or socket.gethostname() or "unknown-host"
    os_name = "Unknown OS"
    model = ""

    # OS Detection
    try:
        if platform.system() == "Windows":
            win_ver = platform.win32_ver()
            os_name = f"Windows {win_ver[0]}"
            try:
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem).Caption"],
                    capture_output=True, text=True, timeout=5
                )
                caption = res.stdout.strip()
                if caption:
                    os_name = caption.replace("Microsoft ", "")
            except Exception:
                pass
        elif hasattr(platform, "freedesktop_os_release"):
            os_data = platform.freedesktop_os_release()
            os_name = os_data.get("PRETTY_NAME", os_data.get("NAME", platform.system()))
        elif os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        os_name = line.strip().split("=", 1)[1].strip('"\'')
                        break
                    elif line.startswith("NAME="):
                        os_name = line.strip().split("=", 1)[1].strip('"\'')
        elif platform.system() == "Darwin":
            os_name = f"macOS {platform.mac_ver()[0]}"
        else:
            os_name = platform.system()
    except Exception:
        os_name = platform.system()

    arch = platform.machine()
    kernel = f"{platform.system()} {platform.release()}"

    # Hardware Model Detection
    if platform.system() == "Windows":
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).Model"],
                capture_output=True, text=True, timeout=5
            )
            model = res.stdout.strip()
        except Exception:
            pass
    elif os.path.exists("/sys/devices/virtual/dmi/id/product_name"):
        try:
            with open("/sys/devices/virtual/dmi/id/product_name") as f:
                model = f.read().strip()
        except Exception:
            pass

    # Chassis Detection
    chassis = "desktop"
    if shutil.which("hostnamectl"):
        try:
            res = subprocess.run(["hostnamectl", "status"], capture_output=True, text=True)
            for line in res.stdout.splitlines():
                if "Chassis:" in line:
                    chassis = line.split("Chassis:", 1)[1].strip().split()[0].lower()
                    break
        except Exception:
            pass
    elif platform.system() == "Windows":
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_SystemEnclosure).ChassisTypes"],
                capture_output=True, text=True, timeout=5
            )
            raw_types = res.stdout.strip().split()
            for t in raw_types:
                try:
                    t_int = int(t)
                    if t_int in (30, 31, 32):
                        chassis = "tablet"
                        break
                    elif t_int in (8, 9, 10, 11, 14):
                        chassis = "laptop"
                        break
                    elif t_int in (17, 23, 28):
                        chassis = "server"
                        break
                    elif t_int in (3, 4, 5, 6, 7):
                        chassis = "desktop"
                        break
                except ValueError:
                    pass
        except Exception:
            if "surface" in hostname.lower() or (model and "surface" in model.lower()):
                chassis = "tablet"

    # Role inference
    role = custom_role
    if not role:
        if "server" in hostname.lower() or chassis in ("server", "vm", "container"):
            role = "Infrastructure Server"
        elif model and "surface" in model.lower():
            role = "At-Home Server (Surface Node)"
        elif chassis == "tablet":
            role = "Convertible Tablet"
        elif chassis == "laptop":
            role = "Mobile Laptop"
        else:
            role = "Primary Workstation"

    return {
        "system_name": hostname,
        "hostname": hostname,
        "model": model,
        "os": os_name,
        "arch": arch,
        "kernel": kernel,
        "chassis": chassis,
        "role": role,
    }


def query_pacman():
    """Queries pacman for native and foreign explicit packages."""
    native = {}
    foreign = {}
    try:
        res = subprocess.run(["pacman", "-Qne"], capture_output=True, text=True, check=True)
        for line in res.stdout.strip().splitlines():
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    native[parts[0]] = parts[1]
                elif len(parts) == 1:
                    native[parts[0]] = "unknown"
    except Exception as e:
        print(f"Notice: pacman -Qne failed: {e}", file=sys.stderr)

    try:
        res = subprocess.run(["pacman", "-Qme"], capture_output=True, text=True, check=True)
        for line in res.stdout.strip().splitlines():
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    foreign[parts[0]] = parts[1]
                elif len(parts) == 1:
                    foreign[parts[0]] = "unknown"
    except Exception as e:
        print(f"Notice: pacman -Qme failed: {e}", file=sys.stderr)

    return "pacman", native, foreign


def query_winget():
    """Queries winget for installed packages."""
    native = {}
    foreign = {}
    try:
        res = subprocess.run(["winget", "list", "--accept-source-agreements"], capture_output=True, text=True, timeout=30)
        lines = res.stdout.splitlines()
        start_idx = -1
        for i, line in enumerate(lines):
            if line.startswith("---") or "---" in line:
                start_idx = i + 1
                break
        if start_idx != -1 and start_idx < len(lines):
            for line in lines[start_idx:]:
                line_clean = line.strip()
                if not line_clean:
                    continue
                parts = [p for p in line_clean.split("  ") if p.strip()]
                if len(parts) >= 3:
                    pkg_id = parts[1].strip()
                    pkg_ver = parts[2].strip()
                    src = parts[3].strip() if len(parts) >= 4 else "winget"
                    if src.lower() == "winget":
                        native[pkg_id] = pkg_ver
                    else:
                        foreign[pkg_id] = f"{pkg_ver} ({src})"
                else:
                    parts = line_clean.split()
                    if len(parts) >= 2:
                        native[parts[0]] = parts[1]
    except Exception as e:
        print(f"Notice: winget query failed: {e}", file=sys.stderr)
    return "winget", native, foreign


def query_scoop():
    """Queries scoop for installed packages."""
    native = {}
    foreign = {}
    try:
        res = subprocess.run(["scoop", "list"], capture_output=True, text=True, timeout=15)
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0].lower() not in ("name", "----", "installed"):
                pkg_name = parts[0]
                pkg_ver = parts[1]
                source = parts[2] if len(parts) >= 3 else "main"
                if source.lower() == "main":
                    native[pkg_name] = pkg_ver
                else:
                    foreign[pkg_name] = f"{pkg_ver} ({source})"
    except Exception as e:
        print(f"Notice: scoop query failed: {e}", file=sys.stderr)
    return "scoop", native, foreign


def query_choco():
    """Queries chocolatey for installed packages."""
    native = {}
    foreign = {}
    try:
        res = subprocess.run(["choco", "list", "--local-only", "--limit-output"], capture_output=True, text=True, timeout=15)
        for line in res.stdout.strip().splitlines():
            if "|" in line:
                parts = line.split("|")
                native[parts[0]] = parts[1]
            elif line and not line.lower().startswith("chocolatey"):
                parts = line.split()
                if len(parts) >= 2:
                    native[parts[0]] = parts[1]
    except Exception as e:
        print(f"Notice: choco query failed: {e}", file=sys.stderr)
    return "choco", native, foreign


def query_windows_packages():
    """Fallback query via PowerShell Get-Package for Windows."""
    native = {}
    foreign = {}
    try:
        ps_cmd = "Get-Package | Select-Object -Property Name, Version, ProviderName | ConvertTo-Json"
        res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=30)
        data = json.loads(res.stdout)
        if isinstance(data, dict):
            data = [data]
        for item in data:
            name = item.get("Name", "")
            ver = str(item.get("Version", "installed"))
            provider = item.get("ProviderName", "Programs")
            if name:
                if str(provider).lower() in ("programs", "msi"):
                    native[name] = ver
                else:
                    foreign[name] = f"{ver} ({provider})"
    except Exception as e:
        print(f"Notice: Windows Get-Package query failed: {e}", file=sys.stderr)
    return "windows-pkg", native, foreign


def query_apt():
    """Queries apt / dpkg for manual packages."""
    native = {}
    foreign = {}
    try:
        res = subprocess.run(["apt-mark", "showmanual"], capture_output=True, text=True, check=True)
        for pkg in res.stdout.strip().splitlines():
            pkg = pkg.strip()
            if pkg:
                native[pkg] = "installed"
    except Exception:
        pass
    return "apt", native, foreign


def query_brew():
    """Queries homebrew for formulae and casks."""
    native = {}
    foreign = {}
    try:
        res = subprocess.run(["brew", "leaves"], capture_output=True, text=True, check=True)
        for pkg in res.stdout.strip().splitlines():
            pkg = pkg.strip()
            if pkg:
                native[pkg] = "formula"
    except Exception:
        pass
    try:
        res = subprocess.run(["brew", "list", "--cask"], capture_output=True, text=True, check=True)
        for pkg in res.stdout.strip().splitlines():
            pkg = pkg.strip()
            if pkg:
                foreign[pkg] = "cask"
    except Exception:
        pass
    return "brew", native, foreign


def query_dnf():
    """Queries dnf for user-installed packages."""
    native = {}
    foreign = {}
    try:
        res = subprocess.run(["dnf", "repoquery", "--userinstalled", "--qf", "%{NAME} %{VERSION}-%{RELEASE}"], capture_output=True, text=True, check=True)
        for line in res.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2:
                native[parts[0]] = parts[1]
            elif len(parts) == 1:
                native[parts[0]] = "installed"
    except Exception:
        pass
    return "dnf", native, foreign


def collect_packages():
    """Identifies package manager and collects packages."""
    if shutil.which("pacman"):
        return query_pacman()
    elif shutil.which("winget"):
        return query_winget()
    elif shutil.which("scoop"):
        return query_scoop()
    elif shutil.which("choco"):
        return query_choco()
    elif platform.system() == "Windows":
        return query_windows_packages()
    elif shutil.which("apt-mark") or shutil.which("dpkg"):
        return query_apt()
    elif shutil.which("brew"):
        return query_brew()
    elif shutil.which("dnf"):
        return query_dnf()
    else:
        return "manual", {}, {}


def build_manifest_content(sys_info, pkg_manager, native_pkgs, foreign_pkgs, timestamp=None, status="active"):
    """Formats markdown note with frontmatter and embedded JSON telemetry."""
    ts = timestamp or get_local_iso_timestamp()
    native_count = len(native_pkgs)
    foreign_count = len(foreign_pkgs)
    total_count = native_count + foreign_count
    
    json_data = {
        "timestamp": ts,
        "system_name": sys_info["system_name"],
        "hostname": sys_info["hostname"],
        "model": sys_info.get("model", ""),
        "host_os": sys_info["os"],
        "kernel": sys_info["kernel"],
        "arch": sys_info["arch"],
        "chassis": sys_info["chassis"],
        "role": sys_info["role"],
        "package_manager": pkg_manager,
        "package_counts": {
            "native_explicit": native_count,
            "foreign_explicit": foreign_count,
            "total_explicit": total_count
        },
        "native_packages": native_pkgs,
        "foreign_packages": foreign_pkgs
    }

    json_str = json.dumps(json_data, indent=2)

    model_line = f" • **Model:** {sys_info['model']}" if sys_info.get("model") else ""
    model_bullet = f"* **Hardware Model:** {sys_info['model']}\n" if sys_info.get("model") else ""

    content = f"""---
type: system_manifest
id: "system-manifest-{sys_info['system_name']}"
system_name: "{sys_info['system_name']}"
hostname: "{sys_info['hostname']}"
os: "{sys_info['os']}"
arch: "{sys_info['arch']}"
kernel: "{sys_info['kernel']}"
chassis: "{sys_info['chassis']}"
role: "{sys_info['role']}"
package_manager: "{pkg_manager}"
generated_at: "{ts}"
last_updated: "{ts}"
status: "{status}"
total_explicit_packages: {total_count}
native_count: {native_count}
foreign_count: {foreign_count}
tags:
  - system/manifest
  - system/{sys_info['system_name']}
---

# 🖥️ {sys_info['system_name']} System Package Manifest

> **Captured:** {ts}  
> **Host OS:** {sys_info['os']} ({sys_info['kernel']}) • **Arch:** {sys_info['arch']} • **Chassis:** {sys_info['chassis']}{model_line}  
> **Native Explicit Packages (`{pkg_manager}`):** {native_count}  
> **Foreign / User Packages:** {foreign_count}  
> **Total Explicit Packages:** {total_count}

---

## 📋 System Profile & Hardware Role

* **System Name / Hostname:** `{sys_info['hostname']}`
{model_bullet}* **Role:** {sys_info['role']}
* **Operating System:** {sys_info['os']}
* **Kernel & Architecture:** `{sys_info['kernel']}` (`{sys_info['arch']}`)
* **Chassis Type:** `{sys_info['chassis']}`
* **Package Manager Substrate:** `{pkg_manager}`
* **Operational Status:** `{status}`

---

## 📦 Package Inventory Telemetry

```json
{json_str}
```
"""
    return content


def main():
    parser = argparse.ArgumentParser(description="Chrysalis Multi-System Manifest Generator")
    parser.add_argument("--system-name", help="Override system name / hostname")
    parser.add_argument("--role", help="System role (e.g. Primary Workstation, Laptop, At-Home Server)")
    parser.add_argument("--status", default="active", help="System operational status (default: active)")
    parser.add_argument("--output", help="Output markdown filepath (default: System/Environment/<system_name>.md)")
    args = parser.parse_args()

    sys_info = detect_system_info(custom_name=args.system_name, custom_role=args.role)
    pkg_mgr, native, foreign = collect_packages()

    content = build_manifest_content(sys_info, pkg_mgr, native, foreign, status=args.status)

    if args.output:
        out_path = Path(args.output)
    else:
        # Default relative to chrysalis vault
        script_dir = Path(__file__).resolve().parent
        env_dir = script_dir.parent
        out_path = env_dir / f"{sys_info['system_name']}.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Successfully wrote manifest for '{sys_info['system_name']}' to: {out_path}")
    print(f"   Packages: {len(native)} native, {len(foreign)} foreign (Total: {len(native) + len(foreign)})")


if __name__ == "__main__":
    main()
