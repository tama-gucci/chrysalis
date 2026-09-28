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


def is_source_repository_checkout(root: Path) -> bool:
    """Return True if root is the framework git source checkout without personal runtime state."""
    root = Path(root).resolve()
    has_git = (root / ".git").exists()
    has_personal_roadmap = (root / "System" / "Life-Roadmap.md").exists()
    return has_git and not has_personal_roadmap


def resolve_runtime_vault(explicit_path=None, *, script_path=__file__) -> Path:
    """Resolve the active personal runtime vault across Antigravity, Codex, and CLI sessions.

    Priority order:
    1. Explicit path argument or CHRYSALIS_VAULT_PATH / CHRYSALIS_VAULT_ROOT env var.
    2. Current workspace/script root if it contains personal runtime state (System/Life-Roadmap.md).
    3. Standard personal runtime vault (~/Documents/Chrysalis) when invoked from the source repo checkout.
    4. Fallback to resolve_vault_root().
    """
    selected = (
        explicit_path
        or os.environ.get("CHRYSALIS_VAULT_PATH")
        or os.environ.get("CHRYSALIS_VAULT_ROOT")
    )
    if selected:
        root = Path(selected).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Vault directory does not exist: {root}")
        return root

    candidate = resolve_vault_root(None, script_path=script_path)
    if not is_source_repository_checkout(candidate):
        return candidate

    default_personal_vault = Path.home() / "Documents" / "Chrysalis"
    if default_personal_vault.is_dir() and (
        (default_personal_vault / "mdbase.yaml").exists()
        or (default_personal_vault / "System" / "Memory.md").exists()
        or (default_personal_vault / "System" / "Life-Roadmap.md").exists()
    ):
        return default_personal_vault.resolve()

    return candidate


def memory_path(explicit_path=None, *, vault=None):
    selected = explicit_path or os.environ.get("CHRYSALIS_MEMORY_PATH")
    return (Path(selected).expanduser().resolve() if selected
            else runtime_memory_path(resolve_vault_root(vault)))


def main(argv=None) -> int:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Resolve Chrysalis vault paths for A2 local agent execution."
    )
    parser.add_argument("--vault", default=None, help="Explicit vault root path")
    parser.add_argument(
        "--runtime",
        action="store_true",
        help="Resolve the active personal runtime vault (e.g. ~/Documents/Chrysalis when run from source)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output resolved paths as JSON",
    )
    args = parser.parse_args(argv)
    root = resolve_runtime_vault(args.vault) if args.runtime else resolve_vault_root(args.vault)
    if args.json:
        payload = {
            "vault_root": str(root),
            "memory_path": str(runtime_memory_path(root)),
            "life_roadmap_path": str(vault_path(root, "System/Life-Roadmap.md")),
            "tasks_dir": str(vault_path(root, "TaskNotes/Tasks")),
            "is_source_checkout": is_source_repository_checkout(root),
        }
        print(json.dumps(payload, indent=2))
    else:
        print(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

