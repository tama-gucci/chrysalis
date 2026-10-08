"""Explicit vault selection and confined paths for the supported layout."""
import json
import os
from pathlib import Path


def native_path(path):
    """Preserve logical identities while using extended Windows paths for disk I/O."""
    path = Path(path).absolute()
    value = str(path)
    if os.name == "nt" and not value.startswith("\\\\?\\"):
        return Path("\\\\?\\UNC\\" + value[2:] if value.startswith("\\\\") else "\\\\?\\" + value)
    return path


def resolve_vault_root(explicit_path=None, *, script_path=__file__):
    selected = explicit_path or os.environ.get("CHRYSALIS_VAULT_PATH")
    if not selected:
        raise ValueError("Select an explicit vault; there is no automatic runtime fallback")
    path = Path(selected).expanduser()
    if not path.is_absolute() or not path.is_dir():
        raise ValueError("Vault must be an existing absolute directory")
    reject_redirects(path)
    return path.resolve()


def reject_redirects(path):
    for item in (Path(path), *Path(path).parents):
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise ValueError("Authoritative paths cannot traverse links or junctions")


def is_source_repository_checkout(root):
    root = Path(root).resolve()
    return (root / ".git").exists() or (root / "package.json").is_file()


def resolve_runtime_vault(explicit_path=None, *, script_path=__file__):
    root = resolve_vault_root(explicit_path)
    actual = next((p.name for p in root.parent.iterdir() if p.resolve() == root), None)
    if actual != "chrysalis":
        raise ValueError("The actual vault directory entry must be named chrysalis")
    if any(is_source_repository_checkout(p) or p.name in {".git", ".agents", "node_modules"} for p in (root, *root.parents)):
        raise ValueError("Source and package directories are not personal runtimes")
    marker = root / ".chrysalis-vault.json"
    if marker.is_symlink() or not marker.is_file():
        raise ValueError("Vault has not been initialized through reviewed setup")
    info = json.loads(marker.read_text(encoding="utf-8"))
    if info.get("schema_version") != "1" or not info.get("vault_id"):
        raise ValueError("Unsupported vault schema or missing identity")
    return root


def vault_path(root, relative):
    root = Path(root).resolve()
    rel = Path(relative)
    if rel.is_absolute() or not rel.parts or ".." in rel.parts or ":" in str(relative):
        raise ValueError("Expected a confined vault-relative path")
    target = root / rel
    for item in (target, *target.parents):
        if item == root:
            break
        if item.is_symlink() or (hasattr(item, "is_junction") and item.is_junction()):
            raise ValueError("Links and junctions are not supported inside authoritative paths")
    target.resolve().relative_to(root)
    return target


def framework_root(root):
    return Path(root).resolve()


def runtime_memory_path(root):
    return vault_path(root, "System/Memory.md")


def memory_path(explicit_path=None, *, vault=None, runtime=False):
    root = resolve_runtime_vault(vault) if runtime else resolve_vault_root(vault)
    if explicit_path:
        return vault_path(root, Path(explicit_path).relative_to(root))
    return runtime_memory_path(root)


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vault", required=True)
    parser.add_argument("--runtime", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    root = resolve_runtime_vault(args.vault) if args.runtime else resolve_vault_root(args.vault)
    print(json.dumps({"vault_root": str(root), "memory_path": str(runtime_memory_path(root))}) if args.json else root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
