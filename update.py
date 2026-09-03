#!/usr/bin/env python3
"""
Chrysalis Framework: Upstream Updater Engine
Safely synchronizes the latest Chrysalis OS framework files, agent skills,
workflows, views, and templates from GitHub directly into an active vault.
Strictly safeguards all personal tasks, roadmaps, daily notes, and telemetry.
"""

import os
import sys
import shutil
import argparse
import tempfile
import subprocess
from pathlib import Path

# Upstream repositories to attempt (SSH first, then HTTPS fallback)
DEFAULT_UPSTREAM_SSH = "git@github.com:tama-gucci/chrysalis.git"
DEFAULT_UPSTREAM_HTTPS = "https://github.com/tama-gucci/chrysalis.git"

# Engine Whitelist (Files that belong to the core Chrysalis distribution)
ENGINE_FILES = [
    "AGENTS.md",
    "README.md",
    "LICENSE",
    "bootstrap.sh",
    "update.sh",
    "update.py",
    "Dashboard.md",
    "mdbase.yaml",
    ".gitignore",
    ".agent/skills.json",
    "Projects/README.md",
    "Slipbox/README.md",
    "System/Runtime-Constitution.md",
    "System/Environment/Environment-Index.md",
    "TaskNotes/Tasks/example-task.md",
]

ENGINE_DIRS = [
    "_types",
    "Development",
    "System/scripts",
    "System/Orchestrators",
    "System/Environment/scripts",
    "System/Environment/_templates",
    "System/_templates",
    "Projects/_templates",
    "Slipbox/_templates",
    "TaskNotes/_templates",
    "TaskNotes/Views",
    "TaskNotes/Workflows",
]

PROTECTED_PATHS = [
    "System/Life-Roadmap.md",
    "System/Scheduling-Memory.md",
    "System/System-Health.md",
    "System/Changelog.md",
    "System/Environment/Active-Profile.md",
    "Nexus",
    ".conversations",
    ".workspaces",
]

def is_protected_target(rel_path_str: str) -> bool:
    """Ensure a relative path in the target vault is never overwritten."""
    p = Path(rel_path_str)
    # Never touch personal tasks or archive
    if str(p).startswith("TaskNotes/Tasks") and p.name != "example-task.md":
        return True
    if str(p).startswith("TaskNotes/Archive"):
        return True
    # Never touch personal projects or slipbox
    if str(p).startswith("Projects/") and not str(p).startswith("Projects/_templates") and p.name != "README.md":
        return True
    if str(p).startswith("Slipbox/") and not str(p).startswith("Slipbox/_templates") and p.name != "README.md":
        return True
    # Never touch daily notes (format: YYYY-MM-DD*.md)
    if p.name.endswith(".md") and len(p.name) >= 10 and p.name[:4].isdigit() and p.name[4] == "-":
        return True
    # Protect personal environment node manifests (generic rule, no machine hostnames)
    if str(p).startswith("System/Environment") and p.suffix == ".md":
        if p.name not in ["Environment-Index.md", "README.md"] and "_templates" not in p.parts:
            return True
    # Check explicit protected list
    for protected in PROTECTED_PATHS:
        if str(p) == protected or str(p).startswith(f"{protected}/"):
            return True
    return False

# Backward-compatible alias
is_protected = is_protected_target

def clone_upstream(repo_url: str, dest_dir: str) -> bool:
    """Attempt shallow clone of upstream repository."""
    cmd = ["git", "clone", "--depth=1", repo_url, dest_dir]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def get_commit_info(repo_dir: Path) -> str:
    """Extract latest commit summary."""
    try:
        res = subprocess.run(
            ["git", "log", "-1", "--format=%h - %s (%ci)"],
            cwd=repo_dir, capture_output=True, text=True, check=True
        )
        return res.stdout.strip()
    except Exception:
        return "Unknown"

def sync_engine(src_dir: Path, target_dir: Path, dry_run: bool = False) -> tuple[int, list[str]]:
    """Copy whitelisted engine files from src_dir to target_dir."""
    updated_files = []
    
    # 1. Root and Individual Engine Files
    for rel_file in ENGINE_FILES:
        src_f = src_dir / rel_file
        dst_f = target_dir / rel_file
        if not src_f.exists():
            continue
        if is_protected_target(rel_file):
            continue
        
        # Check if identical
        if dst_f.exists() and src_f.read_bytes() == dst_f.read_bytes():
            continue
            
        if not dry_run:
            dst_f.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_f, dst_f)
        updated_files.append(rel_file)

    # 2. Engine Directories
    for rel_dir in ENGINE_DIRS:
        src_d = src_dir / rel_dir
        dst_d = target_dir / rel_dir
        if not src_d.exists():
            continue
        for root, dirs, files in os.walk(src_d):
            # Skip python caches and backup dirs
            if "__pycache__" in dirs:
                dirs.remove("__pycache__")
            if ".backup" in dirs:
                dirs.remove(".backup")
            for f in files:
                full_src = Path(root) / f
                rel_path = full_src.relative_to(src_dir)
                rel_str = str(rel_path)
                if is_protected_target(rel_str):
                    continue
                full_dst = target_dir / rel_path
                if full_dst.exists() and full_src.read_bytes() == full_dst.read_bytes():
                    continue
                if not dry_run:
                    full_dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(full_src, full_dst)
                updated_files.append(rel_str)

    # 3. Agent Skills (.agent/skills)
    src_skills = src_dir / ".agent" / "skills"
    dst_skills = target_dir / ".agent" / "skills"
    if src_skills.exists():
        for skill_entry in src_skills.iterdir():
            if skill_entry.is_dir() and skill_entry.name != ".backup":
                for root, dirs, files in os.walk(skill_entry):
                    for f in files:
                        full_src = Path(root) / f
                        rel_path = full_src.relative_to(src_dir)
                        rel_str = str(rel_path)
                        if is_protected_target(rel_str):
                            continue
                        full_dst = target_dir / rel_path
                        if full_dst.exists() and full_src.read_bytes() == full_dst.read_bytes():
                            continue
                        if not dry_run:
                            full_dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(full_src, full_dst)
                        updated_files.append(rel_str)

    # 4. Obsidian Plugins (Code/manifests/styles, preserving data.json and local databases)
    src_plugins = src_dir / ".obsidian" / "plugins"
    dst_plugins = target_dir / ".obsidian" / "plugins"
    if src_plugins.exists():
        for plugin_entry in src_plugins.iterdir():
            if plugin_entry.is_dir():
                for item in plugin_entry.iterdir():
                    # Preserve existing data.json, skip runs, caches
                    if item.name in ["runs", "data"] or "conflict" in item.name:
                        continue
                    rel_path = item.relative_to(src_dir)
                    full_dst = target_dir / rel_path
                    if item.name == "data.json" and full_dst.exists():
                        continue
                    if full_dst.exists() and item.is_file() and item.read_bytes() == full_dst.read_bytes():
                        continue
                    if not dry_run and item.is_file():
                        full_dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, full_dst)
                    updated_files.append(str(rel_path))

    return len(updated_files), updated_files

def main():
    parser = argparse.ArgumentParser(description="Chrysalis Framework Upstream Updater")
    parser.add_argument("--target", default=".", help="Target vault path (default: current directory)")
    parser.add_argument("--repo", default=None, help="Custom git repository URL")
    parser.add_argument("--source", default=None, help="Local repository path to sync from instead of git clone")
    parser.add_argument("--dry-run", action="store_true", help="Inspect updates without writing to disk")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()

    # Verify target directory accessibility and writability
    check_dir = target_path if target_path.exists() else target_path.parent
    if not check_dir.exists() or not os.access(check_dir, os.W_OK | os.R_OK):
        print(f"Error: Target path {target_path} is not accessible or writable.", file=sys.stderr)
        sys.exit(1)

    print("=======================================================")
    print("   🦋  Chrysalis OS: Framework Upstream Updater        ")
    print("=======================================================")
    print(f"Target Vault: {target_path}")
    if args.source:
        print(f"Source Vault: {Path(args.source).resolve()}")
    if args.dry_run:
        print("Mode:         DRY RUN (No files will be modified)")
    print()

    # Step 1: Source acquisition
    if args.source:
        src_path = Path(args.source).resolve()
        if not src_path.exists():
            print(f"\n❌ Error: Local source repository path not found: {src_path}", file=sys.stderr)
            sys.exit(1)
        print("[1/3] Using local source repository...")
        print(f"  ✓ Local source resolved: {src_path}")
        print()

        # Step 2: Compare and Sync
        action_verb = "Simulating sync of" if args.dry_run else "Synchronizing"
        print(f"[2/3] {action_verb} framework files...")
        count, updated_list = sync_engine(src_path, target_path, dry_run=args.dry_run)
    else:
        print("[1/3] Fetching upstream release from GitHub...")
        repos_to_try = [args.repo] if args.repo else [DEFAULT_UPSTREAM_SSH, DEFAULT_UPSTREAM_HTTPS]
        
        with tempfile.TemporaryDirectory() as tmp_dir:
            cloned = False
            active_repo = None
            for repo_url in repos_to_try:
                print(f"  Attempting clone from {repo_url}...")
                if clone_upstream(repo_url, tmp_dir):
                    cloned = True
                    active_repo = repo_url
                    break
            
            if not cloned:
                print("\n❌ Error: Failed to fetch from upstream repository.", file=sys.stderr)
                print("Please ensure your SSH key or internet connection is active, or pass --repo <url>.", file=sys.stderr)
                sys.exit(1)

            src_dir = Path(tmp_dir)
            commit_info = get_commit_info(src_dir)
            print(f"  ✓ Upstream fetched: {commit_info}")
            print()

            # Step 2: Compare and Sync
            action_verb = "Simulating sync of" if args.dry_run else "Synchronizing"
            print(f"[2/3] {action_verb} framework files...")
            count, updated_list = sync_engine(src_dir, target_path, dry_run=args.dry_run)

    # Step 3: Summary
    print(f"\n[3/3] Update Summary:")
    if count == 0:
        print("  ✓ Vault is already up-to-date with upstream!")
    else:
        print(f"  ✓ {count} framework file(s) {'would be ' if args.dry_run else ''}updated:")
        for item in updated_list[:25]:
            print(f"    • {item}")
        if len(updated_list) > 25:
            print(f"    ... and {len(updated_list) - 25} more.")

    print("\n=======================================================")
    if args.dry_run:
        print("✅ DRY RUN COMPLETE: Ready to apply updates.")
    else:
        print("✅ UPDATE COMPLETE: Framework files synchronized successfully.")
        print("   Personal tasks, roadmaps, and telemetry remained untouched.")
    print("=======================================================\n")

if __name__ == "__main__":
    main()
