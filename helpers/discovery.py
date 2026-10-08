"""Confined, metadata-only discovery; never opens original content."""
from pathlib import Path
import mimetypes
from itertools import islice
from System.scripts.vault_paths import vault_path, reject_redirects


def discover_originals(vault_root, *, locker_root=None, discovery_roots=None, max_depth=6, integration=None):
    diagnostics, files = [], []
    if not isinstance(max_depth, int) or not 0 <= max_depth <= 12:
        raise ValueError("Discovery depth must be 0–12")
    base = Path(locker_root) if locker_root else None
    if base is None or not base.is_absolute() or not base.is_dir():
        return {"collection_status": "unavailable", "files": [], "diagnostics": [{"code": "mount_unavailable", "severity": "error"}]}
    reject_redirects(base)
    base = base.resolve()
    subroots = discovery_roots or ["."]
    if not isinstance(subroots, list) or not 1 <= len(subroots) <= 20:
        raise ValueError("Select 1–20 discovery roots")
    roots = []
    for relative in subroots:
        root = base if relative == "." else vault_path(base, relative)
        if not root.is_dir():
            diagnostics.append({"code": "discovery_root_unavailable", "severity": "warning", "root": relative})
        else:
            roots.append(root)
    seen, truncated = set(), False
    def walk(directory, depth):
        nonlocal truncated
        try:
            entries = sorted(islice(directory.iterdir(), 10001), key=lambda p: p.name.casefold())
            if len(entries) > 10000:
                diagnostics.append({"code": "directory_limit", "severity": "warning"})
                entries = entries[:10000]
                truncated = True
            for path in entries:
                if len(files) >= 1000:
                    truncated = True
                    break
                if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
                    diagnostics.append({"code": "redirect_skipped", "severity": "warning"})
                    continue
                if path.is_dir():
                    if depth < max_depth:
                        walk(path, depth + 1)
                    else:
                        truncated = True
                    continue
                if not path.is_file() or path in seen:
                    continue
                seen.add(path)
                stat = path.stat()
                relative = path.relative_to(base).as_posix()
                suffix = path.suffix.lower()
                files.append({"filename": path.name, "path": str(path), "relative_path": relative,
                              "size_bytes": stat.st_size, "external_revision": str(stat.st_mtime_ns),
                              "sha256": None, "bytes_available": False, "content_kind": "file",
                              "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                              "supported": suffix in {".pdf", ".txt", ".md", ".csv", ".png", ".jpg", ".jpeg", ".webp"},
                              "ingestion_outcome": "metadata_only", "index_state": "requires_selected_read",
                              "extraction_coverage": {"status": "partial", "limitations": ["metadata_only; original content has not been read"]}})
        except OSError:
            diagnostics.append({"code": "directory_unreadable", "severity": "warning"})
            truncated = True
    for root in roots:
        walk(root, 0)
    return {"collection_status": "unindexed_inputs_present" if files or truncated else "empty" if roots and not diagnostics else "unreadable",
            "files": files, "diagnostics": diagnostics, "listing_truncated": truncated,
            "local_mount_path": str(base), "preserve_originals_in_place": True}
