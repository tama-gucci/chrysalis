#!/usr/bin/env python3
"""
Chrysalis Framework: Upstream Updater Engine
Safely synchronizes the latest Chrysalis OS framework files, agent skills,
workflows, views, and templates from GitHub directly into an active vault.
Strictly safeguards all personal tasks, roadmaps, daily notes, and telemetry.
"""

import os
import json
import hashlib
import uuid
from datetime import datetime
from contextlib import contextmanager
import sys
import shutil
import argparse
import tempfile
import subprocess
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Upstream repositories to attempt (SSH first, then HTTPS fallback)
DEFAULT_UPSTREAM_SSH = "git@github.com:tama-gucci/chrysalis.git"
DEFAULT_UPSTREAM_HTTPS = "https://github.com/tama-gucci/chrysalis.git"

# Engine Whitelist (Files that belong to the core Chrysalis distribution)
ENGINE_FILES = [
    "AGENTS.md",
    "README.md",
    "ARCHITECTURE.md",
    "STATUS.md",
    "requirements.txt",
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
    "chrysalis/Tasks/example-task.md",
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
    "chrysalis/_templates",
    "chrysalis/Views",
    "chrysalis/Workflows",
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
    p = Path(rel_path_str.replace("\\", "/"))
    if any(part in {".chrysalis", ".venv", "venv", "node_modules", ".dart_tool"} for part in p.parts):
        return True
    if p.suffix.lower() in {".env", ".db", ".sqlite", ".sqlite3", ".pem", ".key"} or p.name.lower().endswith(".token.json"):
        return True
    if "credentials" in p.name.lower():
        return True
    if p.name == "data.json" and ".obsidian" in p.parts:
        return True
    # Strip optional leading 'chrysalis/' for unified check
    parts = list(p.parts)
    if parts and parts[0] == "chrysalis":
        parts.pop(0)
    norm_p = Path(*parts) if parts else p
    posix_p = norm_p.as_posix()
    orig_posix = p.as_posix()

    # Never touch personal tasks or archive
    if (posix_p.startswith("TaskNotes/Tasks") or posix_p.startswith("Tasks") or orig_posix.startswith("chrysalis/Tasks")) and norm_p.name != "example-task.md":
        return True
    if posix_p.startswith("TaskNotes/Archive") or posix_p.startswith("Archive") or orig_posix.startswith("chrysalis/Archive"):
        return True
    # Never touch personal projects or slipbox
    if posix_p.startswith("Projects/") and not posix_p.startswith("Projects/_templates") and norm_p.name != "README.md":
        return True
    if posix_p.startswith("Slipbox/") and not posix_p.startswith("Slipbox/_templates") and norm_p.name != "README.md":
        return True
    # Never touch daily notes (format: YYYY-MM-DD*.md or Daily/YYYY-MM-DD*.md)
    if norm_p.name.endswith(".md") and len(norm_p.name) >= 10 and norm_p.name[:4].isdigit() and norm_p.name[4] == "-":
        return True
    # Protect personal environment node manifests (generic rule, no machine hostnames)
    if (posix_p.startswith("System/Environment") or orig_posix.startswith("System/Environment")) and norm_p.suffix == ".md":
        if norm_p.name not in ["Environment-Index.md", "README.md"] and "_templates" not in norm_p.parts:
            return True
    # Check explicit protected list
    for protected in PROTECTED_PATHS:
        if posix_p == protected or posix_p.startswith(f"{protected}/") or orig_posix == protected or orig_posix.startswith(f"{protected}/"):
            return True
    return False

# Backward-compatible alias
is_protected = is_protected_target

def clone_upstream(repo_url: str, dest_dir: str) -> bool:
    """Attempt shallow clone of upstream repository."""
    cmd = ["git", "-c", "credential.helper=", "clone", "--depth=1", repo_url, dest_dir]
    clone_env = os.environ.copy()
    clone_env["GIT_TERMINAL_PROMPT"] = "0"
    clone_env["GCM_INTERACTIVE"] = "never"
    clone_env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes -o StrictHostKeyChecking=accept-new"
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=5, env=clone_env, stdin=subprocess.DEVNULL)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
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

PLUGIN_ASSETS = {"main.js", "manifest.json", "styles.css", "connector.js", "sqlite3.wasm"}
DEFAULT_PLUGINS = {"chrysalis-obsidian", "dataview", "various-complements"}
STATE_DIRECTORY = ".chrysalis"


def safe_path(root: Path, relative: str) -> Path:
    """Reject paths that escape the target, including through junctions."""
    relative = relative.replace("\\", "/")
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or ":" in relative:
        raise ValueError(f"Unsafe relative path: {relative}")
    path = root / rel
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"Path leaves selected directory: {relative}")
    return path


def fingerprint(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def atomic_write(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path, value):
    atomic_write(path, (json.dumps(value, indent=2) + "\n").encode("utf-8"))


@contextmanager
def deployment_lock(target):
    state = safe_path(target, STATE_DIRECTORY)
    state.mkdir(parents=True, exist_ok=True)
    lock = safe_path(target, STATE_DIRECTORY + "/deployment.lock")
    try:
        handle = lock.open("x")
    except FileExistsError:
        raise ValueError("A deployment lock exists; finish or inspect that operation before retrying")
    try:
        handle.write(str(os.getpid()))
        handle.close()
        yield
    finally:
        lock.unlink(missing_ok=True)


def distribution_files(source: Path, *, plugins=False):
    """One allowlist for deployment and clean export; no plugin settings or caches."""
    selected = set(ENGINE_FILES)
    for directory in ENGINE_DIRS + [".agent/skills"]:
        base = safe_path(source, directory)
        if not base.is_dir():
            continue
        for current, dirs, files in os.walk(base, followlinks=False):
            dirs[:] = [d for d in dirs if d not in {"__pycache__", ".backup", ".git", ".pytest_cache"}
                       and not (Path(current) / d).is_symlink()]
            for name in files:
                if not name.endswith((".pyc", ".bak", ".tmp", ".log")):
                    selected.add((Path(current) / name).relative_to(source).as_posix())
    if plugins:
        for plugin in sorted(DEFAULT_PLUGINS):
            for name in sorted(PLUGIN_ASSETS):
                selected.add(f".obsidian/plugins/{plugin}/{name}")
    for relative in sorted(selected):
        path = safe_path(source, relative)
        if path.is_file() and not path.is_symlink() and not is_protected_target(relative):
            yield relative


def destination_relative(target, relative):
    # Preserve existing layouts. Merely having chrysalis/Tasks does not mean
    # that System, Projects, and Slipbox have been migrated.
    if (target / "chrysalis/System").is_dir() and not (target / "System").is_dir():
        first = relative.split("/", 1)[0]
        if first in {"System", "Projects", "Slipbox", "_types"} or relative in {"Dashboard.md", "mdbase.yaml"}:
            return "chrysalis/" + relative
    return relative


def deployment_plan(source, target, *, plugins=False):
    state_file = safe_path(target, STATE_DIRECTORY + "/deployment.json")
    previous = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {"files": {}}
    changes = []
    for relative in distribution_files(source, plugins=plugins):
        destination = destination_relative(target, relative)
        dst = safe_path(target, destination)
        # Existing settings belong to this installation, even on first deploy.
        if relative in {".gitignore", ".agent/skills.json", "chrysalis/Tasks/example-task.md"} and dst.exists():
            continue
        before = fingerprint(dst)
        after = fingerprint(safe_path(source, relative))
        if before == after:
            continue
        if destination in previous.get("files", {}) and before != previous["files"][destination]:
            raise ValueError(f"Runtime framework file changed locally: {destination}. Reconcile it in the source before deployment.")
        changes.append({"source": relative, "path": destination, "before": before, "after": after})
    return changes, previous


def sync_engine(src_dir: Path, target_dir: Path, dry_run: bool = False, *, plugins: bool = False) -> tuple[int, list[str]]:
    """Deploy an allowlisted snapshot, backing up every replaced file first.

    A failed copy is rolled back automatically. Subsequent deployments refuse
    to overwrite local changes to managed files. Old files are never pruned.
    """
    source, target = Path(src_dir).resolve(), Path(target_dir).resolve()
    if source == target or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError("Source and target must be separate, non-nested directories")
    if not source.is_dir():
        raise ValueError("Source directory does not exist")
    changes, previous = deployment_plan(source, target, plugins=plugins)
    if dry_run or not changes:
        return len(changes), [c["path"] for c in changes]
    target.mkdir(parents=True, exist_ok=True)
    with deployment_lock(target):
        changes, previous = deployment_plan(source, target, plugins=plugins)
        release = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S") + "-" + uuid.uuid4().hex[:8]
        backup = safe_path(target, f"{STATE_DIRECTORY}/deployments/{release}")
        manifest = {"id": release, "created": datetime.now().astimezone().isoformat(),
                    "status": "prepared", "previous": previous, "changes": changes}
        # Stage source bytes and original files before touching the installation.
        for change in changes:
            rel = change["path"]
            src = safe_path(source, change["source"])
            data = src.read_bytes()
            if hashlib.sha256(data).hexdigest() != change["after"]:
                raise ValueError(f"Source changed during deployment: {change['source']}")
            atomic_write(safe_path(backup, "new/" + rel), data)
            dst = safe_path(target, rel)
            if change["before"] is not None:
                original = dst.read_bytes()
                if hashlib.sha256(original).hexdigest() != change["before"]:
                    raise ValueError(f"Target changed during deployment: {rel}")
                atomic_write(safe_path(backup, "old/" + rel), original)
        write_json(backup / "manifest.json", manifest)
        applied = []
        try:
            for change in changes:
                dst = safe_path(target, change["path"])
                if fingerprint(dst) != change["before"]:
                    raise ValueError(f"Target changed during deployment: {change['path']}")
                atomic_write(dst, safe_path(backup, "new/" + change["path"]).read_bytes())
                applied.append(change)
            files = dict(previous.get("files", {}))
            files.update({c["path"]: c["after"] for c in changes})
            manifest["status"] = "complete"
            write_json(backup / "manifest.json", manifest)
            write_json(safe_path(target, STATE_DIRECTORY + "/deployment.json"), {"id": release, "files": files})
        except Exception:
            for change in reversed(applied):
                dst = safe_path(target, change["path"])
                if change["before"] is None:
                    dst.unlink(missing_ok=True)
                else:
                    atomic_write(dst, safe_path(backup, "old/" + change["path"]).read_bytes())
            manifest["status"] = "failed"
            write_json(backup / "manifest.json", manifest)
            raise
    print(f"Deployment snapshot: {release}")
    return len(changes), [c["path"] for c in changes]


def _rollback(target_dir: Path, *, dry_run=False):
    """Restore the latest deployment only if its files are still unchanged."""
    target = Path(target_dir).resolve()
    state_file = safe_path(target, STATE_DIRECTORY + "/deployment.json")
    state = json.loads(state_file.read_text(encoding="utf-8"))
    if not state.get("id"):
        raise ValueError("No deployment to roll back")
    backup = safe_path(target, f"{STATE_DIRECTORY}/deployments/{state['id']}")
    manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
    # Validate every file and backup before restoring anything.
    for change in manifest["changes"]:
        if fingerprint(safe_path(target, change["path"])) != change["after"]:
            raise ValueError(f"File changed since deployment: {change['path']}; rollback stopped")
        if change["before"] is not None and fingerprint(safe_path(backup, "old/" + change["path"])) != change["before"]:
            raise ValueError(f"Backup is missing or damaged: {change['path']}")
    if not dry_run:
        restored = []
        try:
            for change in reversed(manifest["changes"]):
                dst = safe_path(target, change["path"])
                if change["before"] is None:
                    dst.unlink()
                else:
                    atomic_write(dst, safe_path(backup, "old/" + change["path"]).read_bytes())
                restored.append(change)
            write_json(state_file, manifest["previous"])
        except Exception:
            for change in reversed(restored):
                atomic_write(safe_path(target, change["path"]), safe_path(backup, "new/" + change["path"]).read_bytes())
            raise
        manifest["status"] = "rolled-back"
        write_json(backup / "manifest.json", manifest)
    return [c["path"] for c in manifest["changes"]]


def rollback(target_dir: Path, *, dry_run=False):
    target = Path(target_dir).resolve()
    if dry_run:
        return _rollback(target, dry_run=True)
    with deployment_lock(target):
        return _rollback(target)


def main():
    parser = argparse.ArgumentParser(description="Chrysalis Framework Upstream Updater")
    parser.add_argument("--target", default=".", help="Target vault path (default: current directory)")
    parser.add_argument("--repo", default=None, help="Custom git repository URL")
    parser.add_argument("--source", default=None, help="Local repository path to sync from instead of git clone")
    parser.add_argument("--dry-run", action="store_true", help="Inspect updates without writing to disk")
    parser.add_argument("--plugins", action="store_true", help="Include approved plugin binaries; preserve all settings")
    parser.add_argument("--rollback", action="store_true", help="Restore the latest deployment snapshot")
    args = parser.parse_args()

    target_path = Path(args.target).resolve()

    if args.rollback:
        changed = rollback(target_path, dry_run=args.dry_run)
        print(f"{len(changed)} files {'would be restored' if args.dry_run else 'restored'}")
        return

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
        count, updated_list = sync_engine(src_path, target_path, dry_run=args.dry_run, plugins=args.plugins)
    else:
        print("[1/3] Fetching upstream release from GitHub...")
        if os.environ.get("CHRYSALIS_OFFLINE_SYNC") == "1":
            repos_to_try = []
        else:
            repos_to_try = [args.repo] if args.repo else [DEFAULT_UPSTREAM_HTTPS, DEFAULT_UPSTREAM_SSH]
        
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
                local_repo = Path(__file__).resolve().parent
                if (local_repo / "AGENTS.md").exists():
                    print(f"  ✓ Upstream unreachable; using local repository fallback: {local_repo}")
                    src_dir = local_repo
                    commit_info = get_commit_info(src_dir)
                else:
                    print("\n❌ Error: Failed to fetch from upstream repository.", file=sys.stderr)
                    print("Please ensure your SSH key or internet connection is active, or pass --repo <url>.", file=sys.stderr)
                    sys.exit(1)
            else:
                src_dir = Path(tmp_dir)
                commit_info = get_commit_info(src_dir)
            print(f"  ✓ Upstream fetched: {commit_info}")
            print()

            # Step 2: Compare and Sync
            action_verb = "Simulating sync of" if args.dry_run else "Synchronizing"
            print(f"[2/3] {action_verb} framework files...")
            count, updated_list = sync_engine(src_dir, target_path, dry_run=args.dry_run, plugins=args.plugins)

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
