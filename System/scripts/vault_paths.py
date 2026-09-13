"""Explicit vault selection shared by runtime tools.

A repository never silently selects a sibling personal vault. Pass --vault or
CHRYSALIS_VAULT_PATH to operate on another installation. Both the existing
split layout and the optional fully encapsulated layout are supported.
"""

import os
from pathlib import Path


def resolve_vault_root(explicit_path=None, *, script_path=__file__):
    selected = explicit_path or os.environ.get("CHRYSALIS_VAULT_PATH")
    if selected:
        root = Path(selected).expanduser().resolve()
        if not root.is_dir():
            raise ValueError(f"Vault directory does not exist: {root}")
        return root
    root = Path(script_path).resolve().parent.parent.parent
    if root.name == "chrysalis" and (root.parent / "AGENTS.md").exists():
        return root.parent
    return root


def vault_path(root, relative):
    """Resolve an existing resource without guessing another vault.

    Reject ambiguous duplicate resources instead of updating an arbitrary copy.
    Missing operational folders use the existing installation's layout.
    """
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError("Expected a vault-relative path")
    if rel.parts and rel.parts[0] == "chrysalis":
        rel = Path(*rel.parts[1:])
    candidates = [root / rel, root / "chrysalis" / rel]
    if rel.parts and rel.parts[0] in {"Tasks", "Archive"}:
        candidates.append(root / "TaskNotes" / rel)
    present = [p for p in candidates if p.exists()]
    if len({p.resolve() for p in present}) > 1:
        raise ValueError(f"Ambiguous vault resource: {relative}; reconcile the two copies first")
    if present:
        return present[0]
    if rel.parts and rel.parts[0] in {"Tasks", "Archive", "Daily", "Inbox", "Views", "Workflows", "_templates"}:
        return candidates[1]
    encapsulated = (root / "chrysalis" / "System").is_dir() and not (root / "System").is_dir()
    return candidates[1] if encapsulated else candidates[0]


def memory_path(explicit_path=None, *, vault=None):
    selected = explicit_path or os.environ.get("CHRYSALIS_MEMORY_PATH")
    return Path(selected).expanduser().resolve() if selected else vault_path(resolve_vault_root(vault), "System/Scheduling-Memory.md")
