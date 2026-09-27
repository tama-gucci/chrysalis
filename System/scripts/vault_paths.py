"""Resolve resources inside an explicitly selected vault.

New vaults use System/ and TaskNotes/. Existing encapsulated TaskNotes/ or
legacy chrysalis/ layouts remain readable; duplicate resources fail closed.
"""

import os
from pathlib import Path

TASK_DIRECTORIES = {"Tasks", "Archive", "Daily", "Inbox", "Views", "Workflows"}
LAYOUT_PREFIXES = ("TaskNotes", "chrysalis")


def resolve_vault_root(explicit_path=None, *, script_path=__file__):
    selected = explicit_path or os.environ.get("CHRYSALIS_VAULT_PATH")
    if selected:
        root = Path(selected).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Vault directory does not exist: {root}")
        return root
    root = Path(script_path).resolve().parent.parent.parent
    if root.name in LAYOUT_PREFIXES and (root.parent / "AGENTS.md").exists():
        return root.parent
    return root


def _existing_resource(candidates, relative):
    present = [path for path in candidates if path.exists()]
    if len({path.resolve() for path in present}) > 1:
        raise ValueError(f"Ambiguous vault resource: {relative}; reconcile the copies first")
    return present[0] if present else None


def framework_root(root):
    """Locate the framework without mistaking a task-only folder for a vault."""
    root = Path(root).resolve()
    system = _existing_resource(
        [root / "System", *(root / prefix / "System" for prefix in LAYOUT_PREFIXES)],
        "System",
    )
    return system.parent if system else root


def vault_path(root, relative):
    """Resolve a resource, preserving its existing layout and rejecting duplicates."""
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("Expected a vault-relative path")
    if not rel.parts or str(rel) in LAYOUT_PREFIXES:
        return root / rel
    # Collection templates and TaskNotes templates are distinct resources.
    if rel.parts[:2] == ("TaskNotes", "_templates"):
        return root / rel
    if rel.parts[0] == "_templates" and (root / rel).exists():
        return root / rel
    if rel.parts[0] in LAYOUT_PREFIXES:
        rel = Path(*rel.parts[1:])
    candidates = [root / rel, *(root / prefix / rel for prefix in LAYOUT_PREFIXES)]
    present = _existing_resource(candidates, relative)
    if present:
        return present
    # Choose a missing file's location from its existing top-level directory.
    parents = [root / rel.parts[0], *(root / prefix / rel.parts[0] for prefix in LAYOUT_PREFIXES)]
    parent = _existing_resource(parents, rel.parts[0])
    if parent:
        return parent.joinpath(*rel.parts[1:])
    if rel.parts[0] in TASK_DIRECTORIES:
        task_base = _existing_resource(
            [root / "Tasks", *(root / prefix / "Tasks" for prefix in LAYOUT_PREFIXES)],
            "Tasks",
        )
        return (task_base.parent if task_base else root / "TaskNotes") / rel
    return framework_root(root) / rel


def runtime_memory_path(root):
    """Prefer current memory, falling back to existing legacy state, never a template."""
    current = vault_path(root, "System/Memory.md")
    if current.exists():
        return current
    legacy = vault_path(root, "System/Scheduling-Memory.md")
    return legacy if legacy.exists() else current


def memory_path(explicit_path=None, *, vault=None):
    selected = explicit_path or os.environ.get("CHRYSALIS_MEMORY_PATH")
    return (Path(selected).expanduser().resolve() if selected
            else runtime_memory_path(resolve_vault_root(vault)))
