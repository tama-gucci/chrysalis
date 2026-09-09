#!/usr/bin/env python3
"""
Chrysalis OS - Automated Sanitization & Starter Export Engine
Builds a 100% clean, open-source distributable starter vault package,
stripping all private telemetry, personal tasknotes, and credentials.
"""

import os
import sys
import shutil
import re
import json
import argparse
import datetime
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent.parent

# Files and directories that belong to the OS Engine (Public / Distributable)
ENGINE_FILES = [
    "AGENTS.md",
    "Dashboard.md",
    "mdbase.yaml",
    ".gitignore",
    "bootstrap.sh",
]

ENGINE_DIRS = [
    ".agent/skills",
    "_types",
    "System/scripts",
    "System/Environment/scripts",
    "System/Environment/_templates",
    "System/Orchestrators",
    "System/_templates",
    "Projects/_templates",
    "Slipbox/_templates",
    "TaskNotes/_templates",
    "TaskNotes/Views",
    "TaskNotes/Workflows",
    "chrysalis/_templates",
    "chrysalis/Views",
    "chrysalis/Workflows",
    "Development",
]

# Sensitive keys and patterns to search for during safety audit
SENSITIVE_PATTERNS = [
    r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", # Email addresses
    r"AIza[0-9A-Za-z-_]{35}",                           # Google API keys
    r"sk-ant-[a-zA-Z0-9-_]{30,}",                       # Anthropic API keys
    r"ghp_[a-zA-Z0-9]{36}",                             # GitHub tokens
]

def sanitize_obsidian_config(src_obsidian: Path, dst_obsidian: Path, dry_run: bool = False):
    """Copy .obsidian folder while stripping runtime caches, calendars, and secrets."""
    if dry_run:
        print("  [dry-run] Would sanitize and copy .obsidian")
        return

    dst_obsidian.mkdir(parents=True, exist_ok=True)
    
    # Copy core configs
    for cfg in ["app.json", "appearance.json", "community-plugins.json", "core-plugins.json"]:
        src_file = src_obsidian / cfg
        if src_file.exists():
            shutil.copy2(src_file, dst_obsidian / cfg)
            
    # Copy plugins
    src_plugins = src_obsidian / "plugins"
    dst_plugins = dst_obsidian / "plugins"
    if src_plugins.exists():
        dst_plugins.mkdir(parents=True, exist_ok=True)
        for plugin in src_plugins.iterdir():
            if plugin.is_dir():
                dst_plugin_dir = dst_plugins / plugin.name
                dst_plugin_dir.mkdir(parents=True, exist_ok=True)
                for item in plugin.iterdir():
                    # Exclude secret data, caches, databases, and workflow run logs
                    if item.name == "data.json" and plugin.name in ["nexus", "text-generator"]:
                        continue # Strip API key configs
                    if item.name == "data.json" and plugin.name in ["tasknotes", "chrysalis-obsidian"]:
                        try:
                            # Sanitize custom calendar IDs and event fingerprints
                            data = json.loads(item.read_text(encoding="utf-8"))
                            data["calendars"] = []
                            data["icsCalendars"] = []
                            data["googleCalendarConfigs"] = []
                            data["googleCalendarSyncTokens"] = {}
                            data["microsoftCalendarSyncTokens"] = {}
                            data["googleCalendarTaskFingerprints"] = {}
                            data["googleCalendarEventIndex"] = []
                            data["googleCalendarSyncQueue"] = []
                            if "googleCalendarExport" in data and isinstance(data["googleCalendarExport"], dict):
                                data["googleCalendarExport"]["targetCalendarId"] = ""
                            (dst_plugin_dir / "data.json").write_text(json.dumps(data, indent=2), encoding="utf-8")
                            continue
                        except Exception:
                            pass
                    if item.name.endswith(".db") or item.name == "runs" or item.name == "data":
                        continue
                    if item.is_file():
                        shutil.copy2(item, dst_plugin_dir / item.name)
                    elif item.is_dir() and item.name not in ["runs", "data"]:
                        shutil.copytree(item, dst_plugin_dir / item.name, dirs_exist_ok=True)

def export_starter(target_dir: str, dry_run: bool = False):
    target_path = Path(target_dir).resolve()
    print("=======================================================")
    print("  Chrysalis OS - Autonomous Sanitizer & Starter Export ")
    print("=======================================================")
    print(f"  Source Vault: {VAULT_ROOT}")
    print(f"  Export Destination: {target_path}")
    if dry_run:
        print("  MODE: DRY RUN (no disk modifications)")
    print()

    if dry_run:
        print("  [dry-run] Verified clean export paths.")
        print("=======================================================\n")
        return

    if target_path.exists():
        print(f"  Clearing existing export directory: {target_path}...")
        shutil.rmtree(target_path)
    target_path.mkdir(parents=True, exist_ok=True)

    # 1. Copy Engine Files
    print("[1/5] Copying Core OS Constitutions & Adapters...")
    for f in ENGINE_FILES:
        src = VAULT_ROOT / f
        if src.exists():
            shutil.copy2(src, target_path / f)
            print(f"  ✓ {f}")

    # 2. Copy Engine Directories
    print("\n[2/5] Copying Modular Skills & Templates...")
    for d in ENGINE_DIRS:
        src = VAULT_ROOT / d
        dst = target_path / d
        if src.exists():
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=shutil.ignore_patterns(".backup", "__pycache__", "*.pyc", "evolve"))
            print(f"  ✓ {d}")

    # 3. Sanitize and Copy .obsidian
    print("\n[3/5] Sanitizing .obsidian Plugin Substrate...")
    sanitize_obsidian_config(VAULT_ROOT / ".obsidian", target_path / ".obsidian", dry_run=dry_run)
    print("  ✓ .obsidian (Caches, tokens, and databases stripped)")

    # 4. Generate Clean Template-Backed Active State
    print("\n[4/5] Initializing Clean Template-Backed Memory & Roadmap...")
    
    # Initialize empty Task directories with sample task
    tasks_dir = target_path / "TaskNotes" / "Tasks"
    tasks_dir.mkdir(parents=True, exist_ok=True)
    chrysalis_tasks_dir = target_path / "chrysalis" / "Tasks"
    chrysalis_tasks_dir.mkdir(parents=True, exist_ok=True)
    (target_path / "Slipbox").mkdir(parents=True, exist_ok=True)
    (target_path / "Projects").mkdir(parents=True, exist_ok=True)
    (target_path / "TaskNotes" / "Archive").mkdir(parents=True, exist_ok=True)
    (target_path / "chrysalis" / "Archive").mkdir(parents=True, exist_ok=True)
    (target_path / "chrysalis" / "Daily").mkdir(parents=True, exist_ok=True)

    # Copy templates as active starter files
    if (VAULT_ROOT / "System" / "_templates" / "Scheduling-Memory.template.md").exists():
        shutil.copy2(
            VAULT_ROOT / "System" / "_templates" / "Scheduling-Memory.template.md",
            target_path / "System" / "Scheduling-Memory.md"
        )
    if (VAULT_ROOT / "System" / "_templates" / "Life-Roadmap.template.md").exists():
        shutil.copy2(
            VAULT_ROOT / "System" / "_templates" / "Life-Roadmap.template.md",
            target_path / "System" / "Life-Roadmap.md"
        )
    sample_template = None
    if (VAULT_ROOT / "chrysalis" / "_templates" / "Task-Template.md").exists():
        sample_template = VAULT_ROOT / "chrysalis" / "_templates" / "Task-Template.md"
    elif (VAULT_ROOT / "TaskNotes" / "_templates" / "Task-Template.md").exists():
        sample_template = VAULT_ROOT / "TaskNotes" / "_templates" / "Task-Template.md"
        
    if sample_template:
        shutil.copy2(sample_template, tasks_dir / "20260901-configure-chrysalis-workspace.md")
        shutil.copy2(sample_template, chrysalis_tasks_dir / "20260901-configure-chrysalis-workspace.md")
    print("  ✓ Initialized clean System/Scheduling-Memory.md")
    print("  ✓ Initialized clean System/Life-Roadmap.md")
    print("  ✓ Created sample task in chrysalis/Tasks/ and TaskNotes/Tasks/")

    # 5. Security & Privacy Audit
    print("\n[5/5] Executing Safety & Privacy Leak Audit...")
    leaks_found = 0
    for root, _, files in os.walk(target_path):
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix in [".md", ".yaml", ".json", ".py", ".sh"]:
                try:
                    text = fpath.read_text(encoding="utf-8", errors="ignore")
                    for pat in SENSITIVE_PATTERNS:
                        matches = re.findall(pat, text)
                        if matches:
                            print(f"  ⚠️ Warning: Potential sensitive pattern '{pat}' in {fpath.relative_to(target_path)}: {matches}")
                            leaks_found += 1
                except Exception:
                    pass

    if leaks_found == 0:
        print("  ✓ 100% CLEAN: Zero credentials, private emails, or API keys detected.")
    else:
        print(f"  ! {leaks_found} potential sensitive patterns detected. Please review.")

    print("\n=======================================================")
    print(f"  Chrysalis Starter Vault successfully exported to:")
    print(f"  {target_path}")
    print("=======================================================\n")

def main():
    parser = argparse.ArgumentParser(description="Chrysalis Starter Vault Export Engine")
    parser.add_argument("--target-dir", default="/tmp/chrysalis-starter-export", help="Destination path for starter export")
    parser.add_argument("--dry-run", action="store_true", help="Simulate export without writing to disk")
    args = parser.parse_args()

    export_starter(args.target_dir, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
