#!/usr/bin/env python3
"""
Chrysalis Framework: Upstream Updater Engine
Safely synchronizes the latest Chrysalis AI Agent Framework files, agent skills,
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

from System.scripts.vault_paths import framework_root, vault_path

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
    "TaskNotes/Tasks/example-task.md",
    "TaskNotes/Workflows/README.md",
]

ENGINE_DIRS = [
    "_types",
    "_contracts",
    "contracts",
    "_templates",
    "docs",
    "helpers",
    "tests/harness",
    "Development",
    "System/scripts",
    "System/Orchestrators",
    "System/Workflows",
    "System/Environment/scripts",
    "System/Environment/_templates",
    "System/_templates",
    "Projects/_templates",
    "Slipbox/_templates",
    "TaskNotes/_templates",
    "TaskNotes/Views",
]

PROTECTED_PATHS = [
    "System/Life-Roadmap.md",
    "System/Memory.md",
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
    # Normalize current and legacy layout prefixes for privacy checks
    parts = list(p.parts)
    while parts and parts[0] in {"TaskNotes", "chrysalis"}:
        parts.pop(0)
    norm_p = Path(*parts) if parts else p
    posix_p = norm_p.as_posix()
    orig_posix = p.as_posix()

    # Never touch personal tasks, archive, or Obsidian TaskNotes Workflows plugin definitions
    if (posix_p.startswith("TaskNotes/Tasks") or posix_p.startswith("Tasks")) and norm_p.name != "example-task.md":
        return True
    if (posix_p.startswith("TaskNotes/Workflows") or posix_p.startswith("Workflows")) and norm_p.name != "README.md":
        return True
    if posix_p.startswith("TaskNotes/Archive") or posix_p.startswith("Archive"):
        return True
    # Never touch personal projects, slipbox, or ingested sources
    if posix_p.startswith("Sources/"):
        return True
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
DEFAULT_PLUGINS = {"dataview", "various-complements"}
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


RETIRED_FRAMEWORK_ARTIFACTS = (
    ".agent/skills/chrysalis-router/SKILL.md",
    "_types/skill.md",
    "docs/spark-agent-system-prompt.md",
    "docs/golem-deployment-and-spark-test-guide.md",
    "Development/SPARK-INTEGRATION-ASSESSMENT.md",
    "System/scripts/package_golem_bundle.py",
    "System/scripts/setup_golem.ps1",
    "Skills/bundle/SKILL.md",
)

RETIRED_SKILL_REGISTRY_PATHS = {
    "Skills",
    "Skills/bundle",
    ".agent/skills/chrysalis-router",
}


def fingerprint(path: Path):
    if not path.is_file():
        return None
    raw = path.read_bytes()
    if path.name == "mdbase.yaml":
        try:
            import yaml
            loaded = yaml.safe_load(raw.decode("utf-8"))
            if isinstance(loaded, dict):
                normalized = {k: v for k, v in loaded.items() if k != "x-mdbase-connect"}
                if isinstance(normalized.get("settings"), dict) and isinstance(normalized["settings"].get("exclude"), list):
                    normalized["settings"] = dict(normalized["settings"])
                    normalized["settings"]["exclude"] = [x for x in normalized["settings"]["exclude"] if x != "System"]
                return hashlib.sha256(json.dumps(normalized, sort_keys=True).encode("utf-8")).hexdigest()
        except Exception:
            pass
    if path.name == "skills.json":
        try:
            loaded = json.loads(raw.decode("utf-8"))
            if isinstance(loaded, dict) and isinstance(loaded.get("entries"), list):
                tracked_paths = {".agent/skills", "Development/skills"} | RETIRED_SKILL_REGISTRY_PATHS
                paths = [
                    e.get("path").strip() for e in loaded["entries"]
                    if isinstance(e, dict) and isinstance(e.get("path"), str) and e.get("path").strip() in tracked_paths
                ]
                return hashlib.sha256(json.dumps(sorted(set(paths))).encode("utf-8")).hexdigest()
        except Exception:
            pass
    return hashlib.sha256(raw).hexdigest()


def merge_mdbase_connect_metadata(src_bytes: bytes, dst_path: Path) -> bytes:
    if dst_path.name == "skills.json":
        try:
            src_doc = json.loads(src_bytes.decode("utf-8"))
            dst_doc = json.loads(dst_path.read_text(encoding="utf-8")) if dst_path.is_file() else {}
            if isinstance(src_doc, dict) and isinstance(src_doc.get("entries"), list):
                merged_entries = []
                seen_paths = set()
                for entry in src_doc["entries"] + (dst_doc.get("entries", []) if isinstance(dst_doc, dict) else []):
                    if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                        continue
                    p = entry["path"].strip()
                    if p in RETIRED_SKILL_REGISTRY_PATHS or p in seen_paths:
                        continue
                    seen_paths.add(p)
                    merged_entries.append(entry)
                out_doc = dict(dst_doc) if isinstance(dst_doc, dict) else {}
                out_doc.update(src_doc)
                out_doc["entries"] = merged_entries
                return (json.dumps(out_doc, indent=2) + "\n").encode("utf-8")
        except Exception:
            pass
        return src_bytes
    if dst_path.name != "mdbase.yaml":
        return src_bytes
    try:
        import yaml
        src_doc = yaml.safe_load(src_bytes.decode("utf-8"))
        dst_doc = yaml.safe_load(dst_path.read_text(encoding="utf-8")) if dst_path.is_file() else {}
        if isinstance(src_doc, dict):
            if isinstance(dst_doc, dict) and "x-mdbase-connect" in dst_doc:
                src_doc["x-mdbase-connect"] = dst_doc["x-mdbase-connect"]
            if isinstance(src_doc.get("settings"), dict) and isinstance(src_doc["settings"].get("exclude"), list):
                src_doc["settings"]["exclude"] = [x for x in src_doc["settings"]["exclude"] if x != "System"]
            return yaml.safe_dump(src_doc, sort_keys=False).encode("utf-8")
    except Exception:
        pass
    return src_bytes


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
                       and (Path(current) / d).relative_to(source).as_posix() != "Development/archive"
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
    # Use the same resolver as runtime tools; new names must not create a
    # second copy of an existing installation's framework or task resources.
    first = relative.split("/", 1)[0]
    if first in {"System", "Projects", "Slipbox", "_types", "TaskNotes"} or relative.startswith(".agent/skills/"):
        return vault_path(target, relative).relative_to(target.resolve()).as_posix()
    if relative in {"Dashboard.md", "mdbase.yaml"}:
        return (framework_root(target) / relative).relative_to(target.resolve()).as_posix()
    return relative


def obsolete_framework_paths(target: Path, active_destinations: set[str], previous_files: dict) -> list[str]:
    """Identify previously deployed or generated framework files that are now retired."""
    candidates = set()
    for dest in previous_files:
        if dest not in active_destinations and dest != "TaskNotes/Tasks/example-task.md" and not is_protected_target(dest):
            candidates.add(dest)
    for rel in RETIRED_FRAMEWORK_ARTIFACTS:
        try:
            dest = destination_relative(target, rel)
        except Exception:
            dest = rel
        if dest not in active_destinations and not is_protected_target(dest):
            candidates.add(dest)
        if rel not in active_destinations and not is_protected_target(rel):
            candidates.add(rel)
    skills_mirror = target / "Skills"
    if skills_mirror.is_dir() and not skills_mirror.is_symlink():
        for skill_md in skills_mirror.rglob("SKILL.md"):
            rel = skill_md.relative_to(target).as_posix()
            if rel not in active_destinations and not is_protected_target(rel):
                candidates.add(rel)
    existing = []
    for rel in sorted(candidates):
        try:
            dst = safe_path(target, rel)
            if dst.is_file() and not dst.is_symlink():
                existing.append(rel)
        except Exception:
            continue
    return existing


def prune_empty_framework_dirs(target: Path, removed_paths: list[str]) -> None:
    """Remove empty directories left behind by pruned framework skills or mirrors."""
    for rel in sorted(removed_paths, reverse=True):
        try:
            parent = safe_path(target, rel).parent
            while parent != target.resolve() and parent.is_relative_to(target.resolve()):
                if parent.exists() and parent.is_dir() and not any(parent.iterdir()):
                    parent.rmdir()
                    parent = parent.parent
                else:
                    break
        except Exception:
            pass


def deployment_plan(source, target, *, plugins=False):
    if (source / "mdbase.yaml").is_file():
        if framework_root(target) != target.resolve() or vault_path(target, "Tasks") != target.resolve() / "TaskNotes/Tasks":
            raise ValueError("mdbase deployment requires the canonical System/ and TaskNotes/Tasks/ layout; follow docs/staged-migration-plan.md before updating a legacy vault")
    state_file = safe_path(target, STATE_DIRECTORY + "/deployment.json")
    previous = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {"files": {}}
    changes = []
    active_destinations = set()
    for relative in distribution_files(source, plugins=plugins):
        destination = destination_relative(target, relative)
        active_destinations.add(destination)
        dst = safe_path(target, destination)
        # Existing .gitignore belongs to this installation, even on first deploy.
        if relative == ".gitignore" and dst.exists():
            continue
        if relative == "TaskNotes/Tasks/example-task.md" and (dst.exists() or destination in previous.get("files", {})):
            continue
        before = fingerprint(dst)
        raw_before = hashlib.sha256(dst.read_bytes()).hexdigest() if dst.is_file() else None
        after = fingerprint(safe_path(source, relative))
        if before == after:
            continue
        if destination in previous.get("files", {}) and previous["files"][destination] not in {before, raw_before} and destination != ".agent/skills.json":
            raise ValueError(f"Runtime framework file changed locally: {destination}. Reconcile it in the source before deployment.")
        changes.append({"source": relative, "path": destination, "before": before, "after": after})

    for obsolete in obsolete_framework_paths(target, active_destinations, previous.get("files", {})):
        dst = safe_path(target, obsolete)
        before = fingerprint(dst)
        if obsolete in previous.get("files", {}) and not obsolete.startswith("Skills/") and before != previous["files"][obsolete]:
            raise ValueError(f"Runtime framework file changed locally: {obsolete}. Reconcile it in the source before deployment.")
        changes.append({"source": None, "path": obsolete, "before": before, "after": None})
    return changes, previous


def sync_engine(src_dir: Path, target_dir: Path, dry_run: bool = False, *, plugins: bool = False) -> tuple[int, list[str]]:
    """Deploy an allowlisted snapshot and prune retired framework artifacts, backing up every replaced or removed file first.

    A failed copy is rolled back automatically. Subsequent deployments refuse
    to overwrite local changes to managed files.
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
            dst = safe_path(target, rel)
            if change["after"] is not None:
                src = safe_path(source, change["source"])
                if fingerprint(src) != change["after"]:
                    raise ValueError(f"Source changed during deployment: {change['source']}")
                data = merge_mdbase_connect_metadata(src.read_bytes(), dst)
                atomic_write(safe_path(backup, "new/" + rel), data)
            if change["before"] is not None:
                if fingerprint(dst) != change["before"]:
                    raise ValueError(f"Target changed during deployment: {rel}")
                atomic_write(safe_path(backup, "old/" + rel), dst.read_bytes())
        write_json(backup / "manifest.json", manifest)
        applied = []
        removed_paths = []
        try:
            # Unlink pruned artifacts (such as hardlinked Skills/ mirrors) first so
            # subsequent updates to .agent/skills/ never share an inode with a legacy link.
            ordered_changes = [c for c in changes if c["after"] is None] + [c for c in changes if c["after"] is not None]
            for change in ordered_changes:
                dst = safe_path(target, change["path"])
                if fingerprint(dst) != change["before"]:
                    raise ValueError(f"Target changed during deployment: {change['path']}")
                if change["after"] is None:
                    dst.unlink(missing_ok=True)
                    removed_paths.append(change["path"])
                else:
                    atomic_write(dst, safe_path(backup, "new/" + change["path"]).read_bytes())
                applied.append(change)
            prune_empty_framework_dirs(target, removed_paths)
            files = dict(previous.get("files", {}))
            for c in changes:
                if c["after"] is None:
                    files.pop(c["path"], None)
                else:
                    files[c["path"]] = c["after"]
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
        removed_on_rollback = []
        try:
            for change in reversed(manifest["changes"]):
                dst = safe_path(target, change["path"])
                if change["before"] is None:
                    dst.unlink()
                    removed_on_rollback.append(change["path"])
                else:
                    atomic_write(dst, safe_path(backup, "old/" + change["path"]).read_bytes())
                restored.append(change)
            prune_empty_framework_dirs(target, removed_on_rollback)
            write_json(state_file, manifest["previous"])
        except Exception:
            for change in reversed(restored):
                if change["after"] is None:
                    safe_path(target, change["path"]).unlink(missing_ok=True)
                else:
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
    print("   🦋  Chrysalis AI Agent Framework: Upstream Updater  ")
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
