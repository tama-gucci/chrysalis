#!/usr/bin/env python3
"""
Chrysalis OS - Autonomous Bootstrap & Onboarding Installer
Detects environment telemetry, initializes templates, seeds timezones,
and prepares the vault for Obsidian and AI Orchestrators.
"""

import os
import sys
import argparse
import datetime
import shutil
from pathlib import Path

def get_local_timezone_offset():
    """Detect local timezone offset in format '+HH:MM' or '-HH:MM'."""
    now = datetime.datetime.now().astimezone()
    offset = now.strftime("%z")
    if len(offset) == 5:
        return f"{offset[:3]}:{offset[3:]}"
    return "-05:00"

def get_iso_timestamp(offset):
    """Generate ISO timestamp with explicit local timezone."""
    now = datetime.datetime.now()
    return f"{now.strftime('%Y-%m-%dT%H:%M:%S')}{offset}"

def ensure_directories(vault_root: Path, folder_name: str = None, dry_run: bool = False):
    """Ensure standard Chrysalis folder substrate exists."""
    base = vault_root / folder_name if folder_name else vault_root
    if folder_name:
        dirs = [
            base / "Tasks",
            base / "Archive",
            base / "Daily",
            base / "Views",
            base / "Workflows",
            base / "_templates",
            base / "Slipbox" / "_templates",
            base / "Slipbox",
            base / "Projects" / "_templates",
            base / "Projects",
            base / "System" / "_templates",
            base / "System" / "scripts",
            base / "System" / "Orchestrators",
            base / "System" / "Environment" / "_templates",
            base / ".agent" / "skills",
            base / "_types",
            vault_root / ".agent",
        ]
    else:
        dirs = [
            vault_root / "TaskNotes" / "Tasks",
            vault_root / "TaskNotes" / "Archive",
            vault_root / "TaskNotes" / "Views",
            vault_root / "TaskNotes" / "Workflows",
            vault_root / "TaskNotes" / "_templates",
            vault_root / "Slipbox" / "_templates",
            vault_root / "Slipbox",
            vault_root / "Projects" / "_templates",
            vault_root / "System" / "_templates",
            vault_root / "System" / "scripts",
            vault_root / "System" / "Orchestrators",
            vault_root / "System" / "Environment" / "_templates",
            vault_root / ".agent" / "skills",
            vault_root / "_types"
        ]
    if dry_run:
        print(f"  [dry-run] Would verify directory substrate at {base}.")
        return
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ Directory substrate verified ({base.name}).")

def seed_system_memory(vault_root: Path, offset: str, timestamp: str, folder_name: str = None, force: bool = False, dry_run: bool = False):
    """Seed System/Scheduling-Memory.md from template if missing."""
    base = vault_root / folder_name if folder_name else vault_root
    mem_path = base / "System" / "Scheduling-Memory.md"
    template_path = base / "System" / "_templates" / "Scheduling-Memory.template.md"
    if not template_path.exists():
        template_path = Path(__file__).resolve().parent.parent / "_templates" / "Scheduling-Memory.template.md"

    if not mem_path.exists() or force:
        if dry_run:
            print(f"  [dry-run] Would create {mem_path.relative_to(vault_root)} from template.")
            return
        if template_path.exists():
            content = template_path.read_text(encoding="utf-8")
            content = content.replace("{{TIMEZONE_OFFSET}}", offset)
            content = content.replace("{{TIMESTAMP}}", timestamp)
            mem_path.parent.mkdir(parents=True, exist_ok=True)
            mem_path.write_text(content, encoding="utf-8")
            print(f"  ✓ Created {mem_path.relative_to(vault_root)} from template.")
        else:
            print("  ! Template not found, skipping Scheduling-Memory creation.")
    else:
        print(f"  ✓ {mem_path.relative_to(vault_root)} already exists.")

def seed_life_roadmap(vault_root: Path, offset: str, timestamp: str, folder_name: str = None, force: bool = False, dry_run: bool = False):
    """Seed System/Life-Roadmap.md from template if missing."""
    base = vault_root / folder_name if folder_name else vault_root
    roadmap_path = base / "System" / "Life-Roadmap.md"
    template_path = base / "System" / "_templates" / "Life-Roadmap.template.md"
    if not template_path.exists():
        template_path = Path(__file__).resolve().parent.parent / "_templates" / "Life-Roadmap.template.md"

    if not roadmap_path.exists() or force:
        if dry_run:
            print(f"  [dry-run] Would create {roadmap_path.relative_to(vault_root)} from template.")
            return
        if template_path.exists():
            today = datetime.date.today()
            d_end = today + datetime.timedelta(days=14)
            d_m2_start = d_end + datetime.timedelta(days=1)
            d_m2_end = d_m2_start + datetime.timedelta(days=28)
            
            content = template_path.read_text(encoding="utf-8")
            content = content.replace("{{TIMESTAMP}}", timestamp)
            content = content.replace("{{DATE_START}}", today.strftime("%Y-%m-%d"))
            content = content.replace("{{DATE_END}}", d_end.strftime("%Y-%m-%d"))
            content = content.replace("{{DATE_M2_START}}", d_m2_start.strftime("%Y-%m-%d"))
            content = content.replace("{{DATE_M2_END}}", d_m2_end.strftime("%Y-%m-%d"))
            roadmap_path.parent.mkdir(parents=True, exist_ok=True)
            roadmap_path.write_text(content, encoding="utf-8")
            print(f"  ✓ Created {roadmap_path.relative_to(vault_root)} from template.")
        else:
            print("  ! Template not found, skipping Life-Roadmap creation.")
    else:
        print(f"  ✓ {roadmap_path.relative_to(vault_root)} already exists.")

def ensure_root_trampolines(vault_root: Path, folder_name: str, dry_run: bool = False):
    """Create root IDE trampolines (.agent/skills.json) pointing into encapsulated subfolder."""
    if not folder_name:
        return
    skills_json = vault_root / ".agent" / "skills.json"
    content = f'''{{
  "entries": [
    {{ "path": "{folder_name}/.agent/skills" }},
    {{ "path": "{folder_name}/Development/skills" }}
  ]
}}
'''
    if dry_run:
        print(f"  [dry-run] Would create root trampoline at {skills_json.relative_to(vault_root)}.")
        return
    skills_json.parent.mkdir(parents=True, exist_ok=True)
    skills_json.write_text(content, encoding="utf-8")
    print(f"  ✓ Created IDE root trampoline at {skills_json.relative_to(vault_root)}.")

def main():
    parser = argparse.ArgumentParser(
        description="Chrysalis OS - Autonomous Bootstrap & Setup Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    default_vault = Path(__file__).resolve().parent.parent.parent
    parser.add_argument(
        "--vault-root",
        type=str,
        default=str(default_vault),
        help="Path to the Chrysalis vault root (default: %(default)s)"
    )
    parser.add_argument(
        "--encapsulated",
        action="store_true",
        help="Encapsulate all Chrysalis files into a single subfolder (default: 'chrysalis')"
    )
    parser.add_argument(
        "--folder-name",
        type=str,
        default=None,
        help="Explicit subfolder name for encapsulation (e.g. 'chrysalis')"
    )
    parser.add_argument(
        "--timezone",
        type=str,
        default=None,
        help="Explicit timezone offset (e.g. -05:00 or +02:00, default: auto-detect)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force overwrite of existing files"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate bootstrap process without writing any files or creating directories"
    )

    args = parser.parse_args()
    vault_root = Path(args.vault_root).resolve()
    offset = args.timezone or get_local_timezone_offset()
    timestamp = get_iso_timestamp(offset)

    folder_name = args.folder_name
    if args.encapsulated and not folder_name:
        folder_name = "chrysalis"

    print("=======================================================")
    print("  Chrysalis OS - Autonomous Bootstrap & Setup Engine  ")
    print("=======================================================")
    print(f"  Local Timezone Offset: {offset}")
    print(f"  Vault Substrate Path:  {vault_root}")
    if folder_name:
        print(f"  Encapsulated Subfolder: {folder_name}/")
    if args.dry_run:
        print("  MODE: DRY-RUN (no disk modifications)")
    print()

    print("[1/3] Verifying Substrate...")
    ensure_directories(vault_root, folder_name=folder_name, dry_run=args.dry_run)
    if folder_name:
        ensure_root_trampolines(vault_root, folder_name, dry_run=args.dry_run)

    print("\n[2/3] Seeding Operational Memory & Roadmaps...")
    seed_system_memory(vault_root, offset, timestamp, folder_name=folder_name, force=args.force, dry_run=args.dry_run)
    seed_life_roadmap(vault_root, offset, timestamp, folder_name=folder_name, force=args.force, dry_run=args.dry_run)

    print("\n[3/3] Orchestrator & Obsidian Instructions:")
    print("  -----------------------------------------------------")
    print("  1. Obsidian Setup:")
    print("     • Open Obsidian -> 'Open folder as vault' -> select this directory.")
    print("     • Click 'Enable community plugins' when prompted.")
    print("  2. Conversational Onboarding:")
    print("     • In your AI agent chat (Google Antigravity), run:")
    print("       /onboard")
    print("     • Answer 4 quick questions to customize your pillars and goals.")
    print("  3. Daily Operation:")
    print("     • Morning check-in: /morning")
    print("     • Evening staging:  /evening")
    print("     • Health Check:     /doctor")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
