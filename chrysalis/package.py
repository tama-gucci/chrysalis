"""One allowlisted package lifecycle; personal overrides live outside defaults."""
from pathlib import Path
import json
import shutil
import uuid
import os
import re
from zoneinfo import ZoneInfo

from .runtime import atomic_json, digest, native_path
from helpers.records import compute_revision, serialize_record
from System.scripts.vault_paths import vault_path, reject_redirects, is_source_repository_checkout

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = ("chrysalis", "helpers", "System/scripts", "skills", "hosts/pi", "_types", "_templates", "docs",
               "System/_templates", "TaskNotes/Views", "Projects/_templates", "Slipbox/_templates", "Environments/_templates", "contracts", "tests/specs")
FILES = ("run.py", "requirements.txt", "package.json", "LICENSE", "README.md", "ARCHITECTURE.md", "STATUS.md", "System/Runtime-Constitution.md", "Dashboard.md", "TaskNotes/Workflows/README.md", "Projects/README.md", "Slipbox/README.md", "Environments/README.md")


def copy_atomic(source, destination):
    source, destination = native_path(source), native_path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pending = destination.with_name(".pending-" + str(uuid.uuid4()))
    try:
        shutil.copyfile(source, pending)
        os.replace(pending, destination)
    finally:
        pending.unlink(missing_ok=True)


def recover(target, state):
    journal = state / "pending.json"
    if not journal.is_file():
        return
    transaction = json.loads(journal.read_text())
    if not re.fullmatch(r"transaction-[a-f0-9-]{36}", str(transaction.get("snapshot", ""))):
        raise ValueError("Invalid package recovery snapshot")
    before, after = transaction["before"], transaction["after"]
    # A concurrent editor wins. Do not restore over an unrecognized post-image.
    for relative in set(before) | set(after):
        path = vault_path(target, relative)
        current = compute_revision(path) if path.is_file() else None
        if current not in {before.get(relative), after.get(relative)}:
            raise ValueError("Interrupted package update conflicts with local edits: " + relative)
    saved = state / transaction["snapshot"]
    for relative in set(before) | set(after):
        path = vault_path(target, relative)
        if relative in before:
            if compute_revision(saved / relative) != before[relative]:
                raise ValueError("Package recovery snapshot changed")
            copy_atomic(saved / relative, path)
        else:
            path.unlink(missing_ok=True)
    atomic_json(state / "current.json", transaction["owned_before"])
    journal.unlink()


def payload(root=ROOT):
    result = {}
    for directory in DIRECTORIES:
        for path in (root / directory).rglob("*"):
            if path.is_file() and not path.is_symlink() and "__pycache__" not in path.parts:
                if path.suffix in {".py", ".md", ".json", ".yaml", ".ts", ".base", ".css"}:
                    result[path.relative_to(root).as_posix()] = compute_revision(path)
    for filename in FILES:
        if (root / filename).is_file():
            result[filename] = compute_revision(root / filename)
    return result


def lifecycle(action, target, *, apply=False, fail_after=None):
    supplied = Path(target)
    if not supplied.is_absolute():
        raise ValueError("Select an absolute package target")
    reject_redirects(supplied)
    resolved = supplied.resolve()
    candidate, origin = native_path(resolved), native_path(ROOT)
    if candidate == origin or origin in candidate.parents or candidate in origin.parents or any((p / ".chrysalis-vault.json").exists() for p in (resolved, *resolved.parents)):
        raise ValueError("Package must remain outside source and personal vaults")
    lock = native_path(supplied.resolve().parent / ".chrysalis-packages" / digest(str(supplied.resolve())) / "lifecycle")
    reject_redirects(lock)
    from helpers.records import _advisory_file_lock
    with _advisory_file_lock(lock, lock_directory=lock.parent):
        return _lifecycle(action, target, apply=apply, fail_after=fail_after)


def _lifecycle(action, target, *, apply=False, fail_after=None):
    supplied = Path(target)
    if not supplied.is_absolute():
        raise ValueError("Select an absolute package target")
    reject_redirects(supplied)
    target = supplied.resolve()
    candidate, origin = native_path(target), native_path(ROOT)
    if candidate == origin or origin in candidate.parents or candidate in origin.parents or any((p / ".chrysalis-vault.json").exists() for p in (target, *target.parents)):
        raise ValueError("Package cannot replace source or a personal vault")
    if target.exists() and (target.is_symlink() or (hasattr(target, "is_junction") and target.is_junction())):
        raise ValueError("Package target cannot be redirected")
    state = native_path(target.parent / ".chrysalis-packages" / digest(str(target)))
    reject_redirects(state)
    target = native_path(target)
    if (state / "pending.json").is_file():
        if not apply:
            return {"status": "recovery_required"}
        recover(target, state)
    index = state / "current.json"
    previous = json.loads(index.read_text()) if index.is_file() else {}
    incoming = payload() if action == "install" else {}
    if action == "rollback":
        if not (state / "rollback.json").is_file():
            raise ValueError("No rollback snapshot")
        incoming = json.loads((state / "rollback.json").read_text())["manifest"]
    if action not in {"install", "remove", "rollback"}:
        raise ValueError("Unknown package action")
    for manifest in (previous, incoming):
        if not isinstance(manifest, dict):
            raise ValueError("Invalid package manifest")
        for relative, sha in manifest.items():
            if not isinstance(relative, str) or "\\" in relative or not isinstance(sha, str) or len(sha) != 64:
                raise ValueError("Invalid package manifest entry")
            vault_path(target, relative)
    conflicts = []
    for relative in set(previous) | set(incoming):
        path = target / relative
        current = compute_revision(path) if path.is_file() else None
        if current != previous.get(relative) and current != incoming.get(relative):
            conflicts.append(relative)
    # No force path: preserve learned edits and prevent a partially mixed executable release.
    result = {"status": "conflict" if conflicts else "preview", "conflicts": sorted(conflicts),
              "add_or_update": sorted(incoming), "remove": sorted(set(previous) - set(incoming))}
    if conflicts or not apply:
        return result
    state.mkdir(parents=True, exist_ok=True)
    backup = state / "before"
    restore = state / "rollback-payload"
    if action == "rollback":
        source = restore
    else:
        if backup.exists():
            shutil.rmtree(backup)
        for relative in previous:
            path = target / relative
            if path.is_file():
                (backup / relative).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, backup / relative)
        if restore.exists():
            shutil.rmtree(restore)
        if backup.exists():
            shutil.copytree(backup, restore)
        atomic_json(state / "rollback.json", {"manifest": previous})
        source = ROOT
    for relative in incoming:
        original = source / relative
        if not original.is_file() or compute_revision(original) != incoming[relative]:
            raise ValueError("Package input changed before application")
    snapshot_name = "transaction-" + str(uuid.uuid4())
    snapshot = state / snapshot_name
    before = {}
    for relative in set(previous) | set(incoming):
        path = vault_path(target, relative)
        if path.is_file():
            before[relative] = compute_revision(path)
            (snapshot / relative).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, snapshot / relative)
    atomic_json(state / "pending.json", {"before": before, "after": incoming, "owned_before": previous, "snapshot": snapshot_name})
    try:
        count = 0
        for relative in sorted(set(previous) | set(incoming)):
            destination = vault_path(target, relative)
            current = compute_revision(destination) if destination.is_file() else None
            if current != before.get(relative):
                raise ValueError("Package target changed during application: " + relative)
            if relative in incoming:
                if compute_revision(source / relative) != incoming[relative]:
                    raise ValueError("Package input changed during application")
                copy_atomic(source / relative, destination)
            else:
                destination.unlink(missing_ok=True)
            count += 1
            if fail_after == count:
                raise RuntimeError("Injected package interruption")
        if any(compute_revision(target / p) != sha for p, sha in incoming.items()):
            raise ValueError("Package postimage verification failed")
        atomic_json(index, incoming)
        (state / "pending.json").unlink()
    except Exception:
        recover(target, state)
        raise
    return {**result, "status": "verified", "manifest_digest": digest(incoming)}


def initialize(target, timezone):
    supplied = Path(target)
    if not supplied.is_absolute() or supplied.name != "chrysalis":
        raise ValueError("Select an absolute fresh directory named chrysalis")
    reject_redirects(supplied)
    supplied = supplied.resolve()
    if any(is_source_repository_checkout(p) for p in (supplied, *supplied.parents)):
        raise ValueError("Do not initialize a vault inside source or an installed package")
    ZoneInfo(timezone)
    if supplied.exists() and any(supplied.iterdir()):
        raise ValueError("Initialization requires an empty directory; no reset or migration")
    # A differently cased existing directory is not a fresh vault.
    if supplied.exists():
        actual = next(p.name for p in supplied.parent.iterdir() if p.resolve() == supplied.resolve())
        if actual != "chrysalis":
            raise ValueError("Existing directory entry is not lowercase chrysalis")
    if supplied == ROOT or ROOT in supplied.parents:
        raise ValueError("Do not initialize inside the package")
    supplied.mkdir(parents=True, exist_ok=True)
    for directory in ("System", "TaskNotes/Tasks", "TaskNotes/Archive", "TaskNotes/Workflows", "Daily", "Projects", "Slipbox", "Sources", "Environments", "Attachments/Originals"):
        (supplied / directory).mkdir(parents=True, exist_ok=True)
    for directory in ("_types", "_templates", "TaskNotes/Views", "Projects/_templates", "Slipbox/_templates"):
        shutil.copytree(ROOT / directory, supplied / directory, dirs_exist_ok=True)
    for relative in ("Dashboard.md", "TaskNotes/Workflows/README.md"):
        shutil.copyfile(ROOT / relative, supplied / relative)
    memory = {"type": "system_state", "schema_version": "1", "user_profile": {"timezone": timezone},
              "system_state": {"pause_state": {"is_paused": False}}, "active_horizons": {"active_projects": []},
              "cognitive_modality_defaults": {m: {"multiplier": 1.0} for m in ("analytical", "kinetic", "synthesis", "administrative")},
              "integrations": {"contract_version": "1.0.0", "instances": {}, "bindings": {}},
              "ingestion": {"contract_version": "1.0.0", "sources": {}, "preserve_originals_in_place": True}}
    (supplied / "System/Memory.md").write_text(serialize_record(memory, "# Memory\n\nPreferences and approved learning.\n"), encoding="utf-8")
    roadmap = {"type": "strategic_roadmap", "tag_registry": {}, "milestones": [], "onboarding_status": "awaiting_conversation"}
    (supplied / "System/Life-Roadmap.md").write_text(serialize_record(roadmap, "# Life roadmap\n\nChoose goals during onboarding.\n"), encoding="utf-8")
    atomic_json(supplied / ".chrysalis-vault.json", {"schema_version": "1", "vault_id": str(uuid.uuid4()), "package_version": "1.0.0"})
    return {"status": "initialized", "vault_root": str(supplied.resolve()), "schema_version": "1"}
