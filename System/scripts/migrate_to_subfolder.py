#!/usr/bin/env python3
"""
Chrysalis AI Agent Framework - Single-Folder Substrate Migration Utility
Encapsulates Chrysalis into a dedicated subfolder (default: 'TaskNotes/')
inside any arbitrary user-named Obsidian vault.

Handles:
- Folder restructuring (Tasks, Archive, Daily, Views, Projects, Slipbox, System, System/Workflows, _types, _templates)
- Moving daily notes (YYYY-MM-DD*.md) from vault root into TaskNotes/Daily/
- Backward compatibility: Unprivileged Windows NTFS Directory Junction (mklink /J) or Unix symlink
- Antigravity IDE root trampolines (.agent/skills.json)
- Obsidian plugin configurations (.obsidian/plugins/tasknotes/data.json, daily-notes.json)
- Dashboard Dataview query updates
"""

import os
import sys
import json
import re
import shutil
import argparse
import subprocess
import yaml
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def print_header():
    print("=" * 65)
    print("  Chrysalis AI Agent Framework: Substrate Encapsulation Engine ")
    print("=" * 65)

def create_directory_structure(vault_root: Path, folder_name: str, dry_run: bool = False):
    """Creates the target encapsulated directory structure."""
    require_legacy_layout(vault_root, folder_name)
    target_base = vault_root / folder_name
    subdirs = [
        target_base / "Tasks",
        target_base / "Archive",
        target_base / "Daily",
        target_base / "Views",
        target_base / "Workflows",
        target_base / "Sources",
        target_base / "Projects" / "_templates",
        target_base / "Slipbox" / "_templates",
        target_base / "System" / "_templates",
        target_base / "System" / "scripts",
        target_base / "System" / "Environment" / "_templates",
        target_base / "System" / "Orchestrators",
        target_base / "System" / "Workflows",
        target_base / "_types",
        target_base / "_templates",
        target_base / ".agent" / "skills",
        vault_root / ".agent",
    ]
    print(f"\n[1/6] Creating Encapsulated Directory Structure at: {folder_name}/")
    for d in subdirs:
        if dry_run:
            print(f"  [dry-run] Would create: {d.relative_to(vault_root)}")
        else:
            d.mkdir(parents=True, exist_ok=True)
            print(f"  [OK] Verified directory: {d.relative_to(vault_root)}")

def move_path(src: Path, dst: Path, dry_run: bool = False):
    """Move file or directory from src to dst safely."""
    if not src.exists() or src.resolve() == dst.resolve():
        return False
    if dry_run:
        print(f"  [dry-run] Move: {src.name} -> {dst}")
        return True
    
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists():
        if src.is_dir():
            for item in src.iterdir():
                move_path(item, dst / item.name, dry_run=dry_run)
            try:
                src.rmdir()
            except OSError:
                pass
            return True
        else:
            raise FileExistsError(f"Migration conflict: {dst}; existing files are never overwritten")
    shutil.move(str(src), str(dst))
    print(f"  [OK] Moved: {src.name} -> {dst}")
    return True

def require_legacy_layout(vault_root: Path, folder_name: str):
    """This utility predates mdbase collection paths; never split a collection."""
    if any(path.exists() for path in (vault_root / "mdbase.yaml", vault_root / folder_name / "mdbase.yaml")):
        raise ValueError("mdbase collections use the canonical split layout; follow docs/staged-migration-plan.md instead of encapsulating them")


def validate_move(src: Path, dst: Path):
    """Check the entire move before changing any files in a subtree."""
    if not src.exists() or src.resolve() == dst.resolve() or not dst.exists():
        return
    if src.is_dir() and dst.is_dir():
        for item in src.iterdir():
            validate_move(item, dst / item.name)
    else:
        raise FileExistsError(f"Migration conflict: {dst}; existing files are never overwritten")


def migrate_substrates(vault_root: Path, folder_name: str, dry_run: bool = False):
    """Move a legacy layout after checking all conflicts; preserve user workflows."""
    require_legacy_layout(vault_root, folder_name)
    target = vault_root / folder_name
    tasknotes = vault_root / "TaskNotes"
    moves = []
    redundant = []
    if tasknotes.exists() and not tasknotes.is_symlink():
        if tasknotes != target:
            moves.extend((tasknotes / name, target / name)
                         for name in ("Tasks", "Archive", "Daily", "Inbox", "Views", "_templates"))
        for workflow in (tasknotes / "Workflows").glob("*.md"):
            text = workflow.read_text(encoding="utf-8")
            parts = text.split("---", 2)
            metadata = yaml.safe_load(parts[1]) if text.startswith("---\n") and len(parts) == 3 else {}
            is_agent = isinstance(metadata, dict) and metadata.get("type") == "agent_workflow"
            if is_agent:
                copies = [vault_root / "System/Workflows" / workflow.name,
                          target / "System/Workflows" / workflow.name]
                existing = [path for path in copies if path.exists()]
                if existing:
                    if any(path.read_bytes() != workflow.read_bytes() for path in existing):
                        raise FileExistsError(f"Migration conflict: {workflow.name}; workflow copies differ")
                    redundant.append(workflow)
                else:
                    moves.append((workflow, copies[1]))
            elif tasknotes != target:
                moves.append((workflow, target / "Workflows" / workflow.name))
    moves.extend((vault_root / name, target / name)
                 for name in ("System", "Projects", "Slipbox", "Sources", "_types", ".agent/skills", "Dashboard.md"))
    daily_pattern = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}.*\.md$")
    moves.extend((path, target / "Daily" / path.name) for path in vault_root.iterdir()
                 if path.is_file() and daily_pattern.match(path.name))
    for src, dst in moves:
        validate_move(src, dst)
    print(f"\n[2/6] Migrating Vault Substrates into {folder_name}/...")
    for src, dst in moves:
        move_path(src, dst, dry_run=dry_run)
    for path in redundant:
        if dry_run:
            print(f"  [dry-run] Remove byte-identical workflow copy: {path.name}")
        else:
            path.unlink()
    if not dry_run and tasknotes != target and tasknotes.is_dir() and not tasknotes.is_symlink():
        for path in (tasknotes / "Workflows", tasknotes):
            try:
                path.rmdir()
            except OSError:
                pass

def setup_backward_compatibility(vault_root: Path, folder_name: str, dry_run: bool = False):
    """Establishes an unprivileged junction (Windows) or symlink (Unix) for TaskNotes."""
    print(f"\n[3/6] Setting Up Backward Compatibility Alias...")
    legacy_tasknotes = vault_root / "TaskNotes"
    target_base = vault_root / folder_name

    if legacy_tasknotes.resolve() == target_base.resolve():
        print("  [OK] Target folder is TaskNotes; no compatibility alias needed.")
        return

    if legacy_tasknotes.exists():
        if legacy_tasknotes.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(legacy_tasknotes)):
            print("  [OK] TaskNotes directory alias already established.")
            return
        else:
            print("  ! Notice: TaskNotes directory still exists physically; skipping alias creation.")
            return

    if dry_run:
        print(f"  [dry-run] Would create TaskNotes alias pointing to {folder_name}")
        return

    if sys.platform == "win32":
        try:
            # mklink /J does NOT require administrator privileges on Windows
            cmd = f'cmd.exe /c mklink /J "{legacy_tasknotes}" "{target_base}"'
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                print(f"  [OK] Created unprivileged Windows NTFS Junction: TaskNotes -> {folder_name}")
            else:
                print(f"  ! Warning: mklink failed ({res.stderr.strip()}). Skipping junction.")
        except Exception as e:
            print(f"  ! Warning: Failed to create Windows junction: {e}")
    else:
        try:
            os.symlink(folder_name, legacy_tasknotes)
            print(f"  [OK] Created Unix symlink: TaskNotes -> {folder_name}")
        except Exception as e:
            print(f"  ! Warning: Failed to create symlink: {e}")

def deploy_root_trampolines(vault_root: Path, folder_name: str, dry_run: bool = False):
    """Deploys .agent/skills.json and root AGENTS.md trampoline."""
    print(f"\n[4/6] Deploying Root IDE & Orchestrator Trampolines...")
    
    # 1. .agent/skills.json
    skills_json_path = vault_root / ".agent" / "skills.json"
    trampoline_data = {
        "entries": [
            {"path": f"{folder_name}/.agent/skills"},
            {"path": f"{folder_name}/Development/skills"}
        ]
    }
    if dry_run:
        print(f"  [dry-run] Would write: .agent/skills.json pointing to {folder_name}/.agent/skills")
    else:
        skills_json_path.parent.mkdir(parents=True, exist_ok=True)
        skills_json_path.write_text(json.dumps(trampoline_data, indent=2) + "\n", encoding="utf-8")
        print(f"  [OK] Deployed: .agent/skills.json")

    # 2. Root AGENTS.md trampoline
    root_agents = vault_root / "AGENTS.md"
    trampoline_md = f"""---
type: system_specification
id: chrysalis-root-trampoline
status: active
---

# Chrysalis Vault Trampoline
This vault encapsulates the Chrysalis AI Agent Framework inside `{folder_name}/`.

The master constitution is located at:
- **Master Constitution:** [`{folder_name}/AGENTS.md`]({folder_name}/AGENTS.md)
- **Skills Registry:** [`.agent/skills.json`](.agent/skills.json) -> `{folder_name}/.agent/skills/`
"""
    if not root_agents.exists() or root_agents.is_symlink():
        if dry_run:
            print(f"  [dry-run] Would write root trampoline AGENTS.md")
        else:
            root_agents.write_text(trampoline_md, encoding="utf-8")
            print(f"  [OK] Deployed root trampoline AGENTS.md")

def update_obsidian_configs(vault_root: Path, folder_name: str, dry_run: bool = False):
    """Updates plugin configs and daily notes settings."""
    print(f"\n[5/6] Updating Obsidian Plugin Configurations...")

    # 1. TaskNotes / Chrysalis-Obsidian data.json
    candidates = [
        vault_root / ".obsidian" / "plugins" / "chrysalis-obsidian" / "data.json",
        vault_root / ".obsidian" / "plugins" / "tasknotes" / "data.json",
    ]
    for data_json in candidates:
        if data_json.exists():
            try:
                content = json.loads(data_json.read_text(encoding="utf-8"))
                content["rootFolder"] = folder_name
                content["tasksFolder"] = f"{folder_name}/Tasks"
                content["archiveFolder"] = f"{folder_name}/Archive"
                content["inlineTaskConvertFolder"] = f"{folder_name}/Tasks"
                
                # Excluded folders
                excluded = content.get("excludedFolders", "")
                additions = [f"{folder_name}/System", f"{folder_name}/_templates", f"{folder_name}/Projects/_templates"]
                for add in additions:
                    if add not in excluded:
                        excluded = f"{excluded}, {add}" if excluded else add
                content["excludedFolders"] = excluded

                # Update view base mappings
                cmd_map = content.get("commandFileMapping", {})
                for k, v in cmd_map.items():
                    if isinstance(v, str) and v.startswith("TaskNotes/Views/"):
                        base_name = v.split("/")[-1]
                        cmd_map[k] = f"{folder_name}/Views/{base_name}"
                content["commandFileMapping"] = cmd_map

                if dry_run:
                    print(f"  [dry-run] Would update {data_json.relative_to(vault_root)} to use {folder_name}/Tasks")
                else:
                    data_json.write_text(json.dumps(content, indent=2) + "\n", encoding="utf-8")
                    print(f"  [OK] Updated {data_json.relative_to(vault_root)}")
            except Exception as e:
                print(f"  ! Warning: Failed to update {data_json}: {e}")

    # 2. Daily Notes Core Plugin Setting
    daily_cfg = vault_root / ".obsidian" / "daily-notes.json"
    daily_data = {"folder": f"{folder_name}/Daily", "format": "YYYY-MM-DD"}
    if daily_cfg.exists():
        try:
            existing = json.loads(daily_cfg.read_text(encoding="utf-8"))
            existing["folder"] = f"{folder_name}/Daily"
            daily_data = existing
        except Exception:
            pass
    if dry_run:
        print(f"  [dry-run] Would set daily notes folder to {folder_name}/Daily")
    else:
        daily_cfg.parent.mkdir(parents=True, exist_ok=True)
        daily_cfg.write_text(json.dumps(daily_data, indent=2) + "\n", encoding="utf-8")
        print(f"  [OK] Set daily notes folder to: {folder_name}/Daily")

    # Model/provider settings are unrelated to folder migration and remain private.

def update_dashboard_queries(vault_root: Path, folder_name: str, dry_run: bool = False):
    """Updates Dataview queries inside Dashboard.md."""
    print(f"\n[6/6] Updating Dashboard Dataview Queries...")
    dash_path = vault_root / folder_name / "Dashboard.md"
    if not dash_path.exists():
        dash_path = vault_root / "Dashboard.md"
    if not dash_path.exists():
        print("  ! Dashboard.md not found, skipping.")
        return

    try:
        content = dash_path.read_text(encoding="utf-8")
        replacements = [
            ('FROM "TaskNotes/Tasks"', f'FROM "{folder_name}/Tasks"'),
            ('FROM "TaskNotes/Archive"', f'FROM "{folder_name}/Archive"'),
            ('FROM "Projects"', f'FROM "{folder_name}/Projects"'),
            ('FROM "Slipbox"', f'FROM "{folder_name}/Slipbox"'),
        ]
        modified = content
        for old, new in replacements:
            modified = modified.replace(old, new)

        if modified != content:
            if dry_run:
                print(f"  [dry-run] Would update Dataview queries in {dash_path.relative_to(vault_root)}")
            else:
                dash_path.write_text(modified, encoding="utf-8")
                print(f"  [OK] Updated Dataview queries in {dash_path.relative_to(vault_root)}")
        else:
            print(f"  [OK] Dashboard.md queries already aligned.")
    except Exception as e:
        print(f"  ! Warning: Failed to update Dashboard.md: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Chrysalis AI Agent Framework - Single-Folder Substrate Migration Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    default_vault = Path(__file__).resolve().parent.parent.parent
    parser.add_argument(
        "--vault-root",
        type=str,
        default=str(default_vault),
        help="Path to the Obsidian vault root (default: %(default)s)"
    )
    parser.add_argument(
        "--folder-name",
        type=str,
        default="TaskNotes",
        help="Target encapsulation subfolder name (default: %(default)s)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without modifying disk"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Perform actual disk migration"
    )

    args = parser.parse_args()
    vault_root = Path(args.vault_root).resolve()
    folder = Path(args.folder_name)
    if folder.is_absolute() or len(folder.parts) != 1 or args.folder_name in {".", ".."}:
        parser.error("folder-name must be a single relative directory name")
    if not (vault_root / folder).resolve().is_relative_to(vault_root):
        parser.error("migration target must remain inside the selected vault")

    if not args.execute and not args.dry_run:
        print("Notice: Running in preview/dry-run mode by default.")
        print("To perform actual migration, pass --execute.\n")
        args.dry_run = True

    print_header()
    print(f"  Vault Target:     {vault_root}")
    print(f"  Encapsulated Dir: {args.folder_name}/")
    print(f"  Execution Mode:   {'DRY-RUN (Simulated)' if args.dry_run else 'ACTIVE EXECUTION'}")

    create_directory_structure(vault_root, args.folder_name, dry_run=args.dry_run)
    migrate_substrates(vault_root, args.folder_name, dry_run=args.dry_run)
    setup_backward_compatibility(vault_root, args.folder_name, dry_run=args.dry_run)
    deploy_root_trampolines(vault_root, args.folder_name, dry_run=args.dry_run)
    update_obsidian_configs(vault_root, args.folder_name, dry_run=args.dry_run)
    update_dashboard_queries(vault_root, args.folder_name, dry_run=args.dry_run)

    print("\n" + "=" * 65)
    if args.dry_run:
        print("  Dry-run complete! Zero files modified.")
        print("  To execute: python migrate_to_subfolder.py --execute")
    else:
        print("  Migration completed successfully!")
        print("  Run '/doctor' or 'python -m unittest discover -t . -s tests/e2e'")
        print("  to verify complete system integrity.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
