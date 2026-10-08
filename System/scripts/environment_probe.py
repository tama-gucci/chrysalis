#!/usr/bin/env python3
"""Bounded local environment observations; JSON to stdout, no manifest writes.

Does not install software, call providers, enumerate packages, or accept agreements.
The caller labels the execution scope; detection cannot prove the physical host.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def node_id(value):
    reserved = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(1, 10)),
                *(f"lpt{i}" for i in range(1, 10)), "readme", "active-profile"}
    if not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", value) or value in reserved:
        raise ValueError("Use a non-reserved lowercase node alias of 1-48 letters/digits/hyphens")
    return value


def command_result(args):
    """Only called with fixed, noninteractive read commands; never return stderr."""
    try:
        result = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=12,
                                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode:
            return {"status": "unavailable", "reason": "command_failed"}
        if len(result.stdout) > 65536:
            return {"status": "unavailable", "reason": "unexpected_output_size"}
        return {"status": "observed", "text": result.stdout.strip()}
    except subprocess.TimeoutExpired:
        return {"status": "unavailable", "reason": "timeout"}
    except OSError:
        return {"status": "unavailable", "reason": "command_unavailable"}


def hardware_observations(system):
    values = {"logical_cpus_visible": os.cpu_count(), "native_cpu_architecture": None,
              "cpu_model": None, "machine_model": None, "memory_total_bytes": None,
              "gpu_names": None}
    result = {"values": values, "status": "partial", "source": "runtime observations"}
    if system == "Windows":
        shell = shutil.which("powershell") or shutil.which("pwsh")
        if not shell:
            result["reason"] = "powershell_unavailable"
            return result
        script = (
            "$ErrorActionPreference='Stop'; "
            "[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
            "$nodeComputer=Get-CimInstance Win32_ComputerSystem; "
            "$nodeCpus=@(Get-CimInstance Win32_Processor); "
            "$nodeGpus=@(Get-CimInstance Win32_VideoController -ErrorAction SilentlyContinue); "
            "@{machine_model=$nodeComputer.Model;memory_total_bytes=$nodeComputer.TotalPhysicalMemory;"
            "cpu_model=@($nodeCpus | ForEach-Object {$_.Name});"
            "cpu_arch_codes=@($nodeCpus | ForEach-Object {$_.Architecture});"
            "gpu_names=@($nodeGpus | ForEach-Object {$_.Name})} | ConvertTo-Json -Compress"
        )
        observed = command_result([shell, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", script])
        result["source"] = "selected Win32 CIM properties"
        if observed["status"] != "observed":
            result["reason"] = observed["reason"]
            return result
        try:
            data = json.loads(observed["text"])
            for key in ("machine_model", "cpu_model", "gpu_names"):
                values[key] = data.get(key) or None
            memory = data.get("memory_total_bytes")
            values["memory_total_bytes"] = int(memory) if memory else None
            architectures = {0: "x86", 5: "arm", 9: "x86_64", 12: "arm64"}
            values["native_cpu_architecture"] = sorted({architectures.get(code, "unknown")
                                                       for code in data.get("cpu_arch_codes", [])}) or None
        except (ValueError, TypeError, AttributeError):
            result["reason"] = "unparseable_probe_output"
    elif system == "Linux":
        result["source"] = "visible procfs memory and Python runtime"
        try:
            with open("/proc/meminfo", encoding="utf-8") as stream:
                meminfo = stream.read(65536)
            match = re.search(r"^MemTotal:\s+(\d+)\s+kB", meminfo, re.M)
            if match:
                values["memory_total_bytes"] = int(match[1]) * 1024
        except OSError:
            result["reason"] = "procfs_unavailable"
    elif system == "Darwin":
        result["source"] = "selected sysctl properties"
        for key, prop in (("memory_total_bytes", "hw.memsize"), ("machine_model", "hw.model")):
            observed = command_result(["sysctl", "-n", prop])
            if observed["status"] == "observed":
                try:
                    values[key] = int(observed["text"]) if key == "memory_total_bytes" else observed["text"]
                except ValueError:
                    pass
    return result


def collect(node, timezone, scope="unknown", storage_root=None):
    node = node_id(node)
    stamp = datetime.now(ZoneInfo(timezone)).isoformat(timespec="seconds")
    system = platform.system()
    storage = {"status": "not_checked", "total_bytes": None, "free_bytes": None}
    if storage_root is not None:
        root = Path(storage_root)
        if not root.is_absolute() or not root.is_dir():
            raise ValueError("storage-root must be an existing absolute directory")
        try:
            usage = shutil.disk_usage(root)
            storage = {"status": "observed", "total_bytes": usage.total, "free_bytes": usage.free}
        except OSError:
            storage["status"] = "unavailable"
    return {
        "format_version": 1, "node_id": node, "observed_at": stamp, "timezone": timezone,
        "execution_scope": scope, "scope_evidence": "caller label; verify terminal backend separately",
        "os": {"system": system, "release": platform.release(), "version": platform.version(),
               "reported_machine": platform.machine()},
        "python": {"version": platform.python_version(), "implementation": platform.python_implementation(),
                   "pointer_bits": struct.calcsize("P") * 8,
                   "architecture_note": "pointer size and reported machine do not prove native hardware architecture"},
        "hardware": hardware_observations(system), "storage": storage,
        "tools_on_path": {tool: bool(shutil.which(tool))
                          for tool in ("pi", "python", "python3", "git", "node", "pwsh", "powershell", "obsidian")},
        "tool_evidence": "PATH presence only; no launch, authentication, compatibility, or provider check",
        "limits": ["Only the current execution environment was observed.",
                   "Container/VM visible memory and storage can differ from quotas or physical host resources.",
                   "No package inventory, hostname, serial number, network identifier, credential, or user-file scan.",
                   "Missing tool on PATH does not establish it is not installed.",
                   "Role, vault access, plugins, sync and integrations require separate selected checks."],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node", required=True, help="User-chosen stable alias, not an inferred hostname")
    parser.add_argument("--timezone", required=True, help="Confirmed IANA timezone")
    parser.add_argument("--scope", choices=("host", "wsl", "container", "remote", "unknown"), default="unknown")
    parser.add_argument("--storage-root", help="Optional existing absolute directory; inspect capacity only")
    args = parser.parse_args(argv)
    try:
        result = collect(args.node, args.timezone, args.scope, args.storage_root)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
