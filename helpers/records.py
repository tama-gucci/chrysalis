"""
chrysalis record validation and ingestion helpers
Strict validation, raw-byte CAS operations, deduplication and additive reconciliation.
Requires the separately installed validation dependencies.
"""

import contextlib
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
import difflib
import sys
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None  # type: ignore
try:
    import fcntl
except ImportError:
    fcntl = None  # type: ignore
    import msvcrt
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union
import uuid
import yaml
from System.scripts.vault_paths import native_path, reject_redirects

try:
    from jsonschema import Draft202012Validator, FormatChecker
    from jsonschema.exceptions import ValidationError
    HAS_JSONSCHEMA = True
except ImportError:
    Draft202012Validator = None
    FormatChecker = None
    ValidationError = Exception
    HAS_JSONSCHEMA = False

# RFC 3339 date-time with explicit timezone offset (e.g. -05:00, +01:00)
TIMEZONE_OFFSET_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?[+\-][0-9]{2}:[0-9]{2}$"
)

# Raw UTC format with 'Z' suffix (prohibited by Chrysalis Local Timezone Invariant)
RAW_UTC_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?Z$"
)

# ISO date format (YYYY-MM-DD)
DATE_ONLY_PATTERN = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

# Cryptographic SHA-256 digest (64 lowercase hex characters)
SHA256_HEX_PATTERN = re.compile(r"^[a-f0-9]{64}$")

# Slug pattern (lowercase alphanumeric and hyphens)
SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")

# Zettel 14-digit local timestamp ID pattern (YYYYMMDDHHmmss with optional kebab-case slug)
ZETTEL_ID_PATTERN = re.compile(r"^[0-9]{14}(-[a-z0-9-]+)?$")

# XML end-tag delimiter escape pattern (case-insensitive with flexible whitespace)
UNTRUSTED_CLOSING_TAG_PATTERN = re.compile(
    r"<\s*/\s*untrusted_document_payload\s*>",
    re.IGNORECASE
)


@dataclass
class Diagnostic:
    code: str
    severity: str  # "error", "warning", "info"
    message: str
    field: Optional[str] = None
    path: Optional[str] = None
    recovery_action: Optional[str] = None  # "FixRequest", "Refresh", "ResolveConflict", "RepairCollection", "Retry"

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }
        if self.field is not None:
            d["field"] = self.field
        if self.path is not None:
            d["path"] = self.path
        if self.recovery_action is not None:
            d["recovery_action"] = self.recovery_action
        return d


@dataclass
class ValidationResult:
    valid: bool
    diagnostics: List[Diagnostic] = field(default_factory=list)
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    body: str = ""

    @property
    def success(self) -> bool:
        return self.valid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "frontmatter": self.frontmatter,
            "body": self.body,
        }


@dataclass
class CASResult:
    valid: bool
    revision: Optional[str] = None
    diagnostics: List[Diagnostic] = field(default_factory=list)
    diff: Optional[str] = None
    dry_run: bool = False
    proposed_content: Optional[str] = None

    @property
    def success(self) -> bool:
        """Alias for valid to satisfy callers checking res.success."""
        return self.valid

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "valid": self.valid,
            "revision": self.revision,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }
        if self.diff is not None:
            d["diff"] = self.diff
        if self.dry_run:
            d["dry_run"] = self.dry_run
        if self.proposed_content is not None:
            d["proposed_content"] = self.proposed_content
        return d


@dataclass
class SyllabusDiff:
    project_id: str
    added: List[Dict[str, Any]] = field(default_factory=list)
    modified: List[Dict[str, Any]] = field(default_factory=list)
    dropped: List[Dict[str, Any]] = field(default_factory=list)
    unchanged: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "added": self.added,
            "modified": self.modified,
            "dropped": self.dropped,
            "unchanged": self.unchanged,
        }


# =========================================================================
# 1. Frontmatter Parsing & Serialization
# =========================================================================

def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Extracts YAML frontmatter dict and markdown body from document string."""
    if not content.startswith("---"):
        return {}, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        data = yaml.safe_load(parts[1])
        fm = data if isinstance(data, dict) else {}
        body = parts[2]
        return fm, body
    except Exception as e:
        raise ValueError(f"YAML frontmatter parsing error: {e}")


def serialize_record(frontmatter: Dict[str, Any], body: str = "") -> str:
    """Serializes frontmatter dict and body into clean markdown string."""
    clean_body = body.lstrip("\r\n")
    fm_yaml = yaml.dump(frontmatter, sort_keys=False, allow_unicode=True)
    if clean_body:
        return f"---\n{fm_yaml}---\n\n{clean_body}\n"
    return f"---\n{fm_yaml}---\n"


# =========================================================================
# 2. ADR 0006 Exact-Document CAS Revision
# =========================================================================

def compute_revision(document_bytes: Union[bytes, str, Path]) -> str:
    """Computes exact-document revision hash: sha256(document_bytes) as 64 lowercase hex."""
    if isinstance(document_bytes, Path):
        raw = native_path(document_bytes).read_bytes()
    elif isinstance(document_bytes, str):
        p = Path(document_bytes)
        try:
            raw = p.read_bytes() if p.is_file() else document_bytes.encode("utf-8")
        except OSError:
            raw = document_bytes.encode("utf-8")
    else:
        raw = document_bytes
    return hashlib.sha256(raw).hexdigest().lower()


def compute_frontmatter_hash(document_or_fm: Union[bytes, str, Path]) -> str:
    """Computes SHA-256 hash for CAS frontmatter/document revision checks."""
    return compute_revision(document_or_fm)



import threading
import time

_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: Dict[str, threading.Lock] = {}


@contextlib.contextmanager
def _advisory_file_lock(path: Path, timeout: float = 30.0, *, lock_directory=None):
    """
    Acquires an exclusive advisory lock via in-process threading.Lock plus
    fcntl.flock (POSIX) or msvcrt.locking (Windows) in the selected external
    lock directory. Standalone helper calls default to the OS temporary directory.
    
    Guarantees cross-thread and cross-process mutual exclusion with timeout protection.
    Lockfile is never unlinked to prevent inode-reallocation race conditions.
    """
    # Locks are local execution state, never synced content.
    import tempfile
    selected = Path(lock_directory) if lock_directory is not None else Path(tempfile.gettempdir())
    if not selected.is_absolute():
        raise ValueError("Lock storage must be an absolute external directory")
    reject_redirects(selected)
    lock_root = native_path(selected / "chrysalis-locks")
    lock_root.mkdir(parents=True, exist_ok=True)
    lock_path = lock_root / (hashlib.sha256(str(native_path(path.resolve())).encode()).hexdigest() + ".lock")
    lock_key = str(lock_path.resolve())
    with _LOCKS_GUARD:
        thread_lock = _PATH_LOCKS.setdefault(lock_key, threading.Lock())

    acquired_thread = thread_lock.acquire(timeout=timeout)
    if not acquired_thread:
        raise TimeoutError(f"Timed out after {timeout}s waiting for in-process lock on {lock_path}")

    try:
        lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o666)
        try:
            start_time = time.monotonic()
            if fcntl is not None:
                while True:
                    try:
                        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except (BlockingIOError, OSError):
                        if time.monotonic() - start_time > timeout:
                            raise TimeoutError(f"Timed out after {timeout}s acquiring lock on {lock_path}")
                        time.sleep(0.005)
            else:
                os.lseek(lock_fd, 0, os.SEEK_SET)
                if os.fstat(lock_fd).st_size == 0:
                    os.write(lock_fd, b"\0")
                while True:
                    try:
                        os.lseek(lock_fd, 0, os.SEEK_SET)
                        msvcrt.locking(lock_fd, msvcrt.LK_NBLCK, 1)
                        break
                    except OSError:
                        if time.monotonic() - start_time > timeout:
                            raise TimeoutError(f"Timed out after {timeout}s acquiring lock on {lock_path}")
                        time.sleep(0.005)
            yield
        finally:
            try:
                if fcntl is not None:
                    fcntl.flock(lock_fd, fcntl.LOCK_UN)
                else:
                    os.lseek(lock_fd, 0, os.SEEK_SET)
                    msvcrt.locking(lock_fd, msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
            os.close(lock_fd)
    finally:
        thread_lock.release()


def apply_cas_mutation(
    file_path: Union[Path, str],
    mutator_fn: Optional[Union[str, Callable[[str], str]]] = None,
    if_revision: Optional[str] = None,
    schema_name: Optional[str] = None,
    dry_run: bool = False,
    collection_dir: Optional[Union[Path, str]] = None,
    timeout: float = 30.0,
    new_document: Optional[Union[str, Callable[[str], str]]] = None,
    lock_directory: Optional[Union[Path, str]] = None,
) -> CASResult:
    """
    Applies conditional atomic mutation using raw-byte compare-and-swap.
    Enforces fail-closed JSON Schema Draft 2020-12 validation on vault records.
    Rejects stale record revisions; bookkeeping locks are not record writes.
    Advisory locks coordinate cooperating helpers. A final revision check narrows
    editor races but does not lock noncooperating editors or cloud replicas.
    Supports callable mutators and proposal-only dry runs (dry_run=True).
    """
    path = native_path(file_path)
    target_mutator = mutator_fn if mutator_fn is not None else new_document
    if target_mutator is None:
        return CASResult(
            valid=False,
            diagnostics=[Diagnostic(
                code="invalid_request",
                severity="error",
                message=f"apply_cas_mutation on {path} requires mutator_fn or new_document content.",
                field="mutator_fn",
                path=str(path),
                recovery_action="FixRequest"
            )]
        )

    try:
        import tempfile
        selected_locks = Path(lock_directory) if lock_directory is not None else Path(tempfile.gettempdir())
        logical_locks = native_path(selected_locks.resolve())
        for boundary in (Path(__file__).resolve().parents[1], Path(collection_dir).resolve() if collection_dir else path.parent.resolve()):
            boundary = native_path(boundary)
            if logical_locks == boundary or boundary in logical_locks.parents:
                raise ValueError("Lock storage must remain outside source and vault")
        with _advisory_file_lock(path, timeout=timeout, lock_directory=selected_locks):
            existed = path.exists()
            if existed:
                if if_revision is None:
                    return CASResult(
                        valid=False,
                        diagnostics=[Diagnostic(
                            code="schema_required",
                            severity="error",
                            message=f"Updating existing file {path} requires an explicit 'if_revision' parameter.",
                            field="if_revision",
                            path=str(path),
                            recovery_action="FixRequest"
                        )]
                    )

                current_bytes = path.read_bytes()
                actual_revision = compute_revision(current_bytes)

                if if_revision.lower() != actual_revision.lower():
                    return CASResult(
                        valid=False,
                        diagnostics=[Diagnostic(
                            code="concurrent_modification",
                            severity="error",
                            message=f"CAS conflict on {path}. Expected revision {if_revision}, but current disk revision is {actual_revision}.",
                            path=str(path),
                            recovery_action="Refresh"
                        )]
                    )
                current_text = current_bytes.decode("utf-8", errors="replace")
            else:
                if if_revision is not None:
                    return CASResult(
                        valid=False,
                        diagnostics=[Diagnostic(
                            code="record_not_found",
                            severity="error",
                            message=f"Target file {path} does not exist on disk, but 'if_revision' was provided.",
                            path=str(path),
                            recovery_action="FixRequest"
                        )]
                    )
                current_text = ""
                current_bytes = b""

            # Resolve new content using callable mutator or string
            if callable(target_mutator):
                try:
                    resolved_doc = target_mutator(current_text)
                except Exception as e:
                    return CASResult(
                        valid=False,
                        diagnostics=[Diagnostic(
                            code="mutator_error",
                            severity="error",
                            message=f"Error executing mutator function on {path}: {e}",
                            path=str(path),
                            recovery_action="FixRequest"
                        )]
                    )
            else:
                resolved_doc = str(target_mutator)

            # Determine target schema for validation
            target_type = schema_name
            if target_type is None:
                p_str = str(path).replace("\\", "/")
                if "TaskNotes/Tasks" in p_str or "Tasks/" in p_str:
                    target_type = "task"
                elif "Projects" in p_str and path.name == "Roadmap.md":
                    target_type = "project"
                elif "Slipbox" in p_str:
                    target_type = "zettel"
                elif "Sources" in p_str:
                    target_type = "source"
                elif "System" in p_str and "Workflows" not in p_str and "Environment" not in p_str and path.suffix == ".md":
                    target_type = "system_state"
                elif resolved_doc.strip().startswith("---"):
                    try:
                        fm_peek, _ = parse_frontmatter(resolved_doc)
                        if fm_peek and fm_peek.get("type"):
                            raw_t = fm_peek.get("type")
                            if raw_t in {"task", "project", "zettel", "source", "system_state"}:
                                target_type = raw_t
                            elif raw_t == "project_roadmap":
                                target_type = "project"
                    except Exception:
                        pass

            if target_type is None:
                return CASResult(valid=False, diagnostics=[Diagnostic(
                    code="type_unknown", severity="error",
                    message="A registered record schema is required for authoritative writes.",
                    path=str(path), recovery_action="FixRequest",
                )])
            if target_type == "task" and current_bytes:
                previous_fm, _ = parse_frontmatter(current_text)
                proposed_fm, _ = parse_frontmatter(resolved_doc)
                if previous_fm.get("googleCalendarEventId") != proposed_fm.get("googleCalendarEventId"):
                    return CASResult(valid=False, diagnostics=[Diagnostic(
                        code="protected_calendar_field", severity="error",
                        message="TaskNotes owns Calendar event identifiers; preserve their value.",
                        path=str(path), field="googleCalendarEventId", recovery_action="FixRequest",
                    )])
            # Schema validation (fails closed)
            if target_type is not None:
                val_res = validate_record(path, resolved_doc, type_name=target_type, collection_dir=collection_dir)
                if not val_res.valid:
                    return CASResult(
                        valid=False,
                        diagnostics=val_res.diagnostics
                    )

            new_bytes = resolved_doc.encode("utf-8")
            projected_revision = compute_revision(new_bytes)

            # Proposal-only dry run mode
            if dry_run:
                diff_lines = list(difflib.unified_diff(
                    current_text.splitlines(keepends=True),
                    resolved_doc.splitlines(keepends=True),
                    fromfile=f"a/{path.name}",
                    tofile=f"b/{path.name}",
                ))
                diff_str = "".join(diff_lines)
                return CASResult(
                    valid=True,
                    revision=projected_revision,
                    diff=diff_str,
                    dry_run=True,
                    proposed_content=resolved_doc
                )

            # Atomic write guarantee via sibling temp file
            path.parent.mkdir(parents=True, exist_ok=True)
            temp_path = path.with_suffix(f".tmp.{uuid.uuid4().hex}")
            try:
                with open(temp_path, "wb") as f:
                    f.write(new_bytes)
                    f.flush()
                    os.fsync(f.fileno())
                if (existed and (not path.exists() or path.read_bytes() != current_bytes)) or (
                    not existed and path.exists()
                ):
                    return CASResult(valid=False, diagnostics=[Diagnostic(
                        code="concurrent_modification", severity="error",
                        message="The record changed while preparing its replacement.",
                        path=str(path), recovery_action="Refresh",
                    )])
                os.replace(temp_path, path)
            finally:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

            return CASResult(valid=True, revision=projected_revision)
    except (OSError, TimeoutError) as e:
        return CASResult(
            valid=False,
            diagnostics=[Diagnostic(
                code="io_error",
                severity="error",
                message=f"Filesystem error during atomic CAS mutation on {path}: {e}",
                path=str(path),
                recovery_action="Retry"
            )]
        )


# =========================================================================
# 3. Cryptographic Provenance, Identity & Deduplication
# =========================================================================

EMPTY_BYTES_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
SCREENSHOT_FILENAME_PATTERN = re.compile(
    r"^(?:screenshot|screen\s*shot|img|dsc|pxl|photo|scan|clip)[_\-\s]*20[0-9]{2}",
    re.IGNORECASE,
)


def normalize_extracted_text(text: str) -> str:
    """Normalizes extracted text for separate text-digest comparison (never used as binary sha256)."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def _resolve_wikilink_target(wikilink: str, vault_root: Path) -> Optional[Path]:
    """Resolves a [[WikiLink]] to its expected file path inside vault_root."""
    if not isinstance(wikilink, str):
        return None
    cleaned = wikilink.strip()
    if cleaned.startswith("[[") and cleaned.endswith("]]"):
        cleaned = cleaned[2:-2].strip()
    if "|" in cleaned:
        cleaned = cleaned.split("|", 1)[0].strip()
    if not cleaned:
        return None
    if not cleaned.endswith(".md"):
        cleaned_md = f"{cleaned}.md"
    else:
        cleaned_md = cleaned
    candidates = [
        vault_root / cleaned_md,
        vault_root / "Slipbox" / Path(cleaned_md).name,
        vault_root / "TaskNotes" / "Tasks" / Path(cleaned_md).name,
        vault_root / "Sources" / Path(cleaned_md).name,
    ]
    for cand in candidates:
        if cand.is_file():
            return cand
    return None


def _check_source_completeness(fm: Dict[str, Any], vault_root: Path) -> Tuple[bool, List[str]]:
    """Checks whether an existing Sources/*.md record was completely ingested and its linked records exist."""
    missing: List[str] = []
    status = str(fm.get("ingestion_status") or "raw")
    if status == "incomplete" or str(fm.get("ingestion_outcome") or "") == "failed":
        missing.append(f"ingestion_status:{status}")
    sha_val = str(fm.get("sha256") or "").lower()
    size_val = int(fm.get("file_size_bytes") or 0)
    if sha_val == EMPTY_BYTES_SHA256 and size_val > 0:
        missing.append("sha256:empty_bytes_placeholder")
    if fm.get("bytes_available") is False and sha_val:
        missing.append("sha256:labeled_when_bytes_unavailable")
    orig_fn = str(fm.get("original_filename") or "")
    if "," in orig_fn and len([p.strip() for p in orig_fn.split(",") if p.strip()]) >= 2:
        missing.append("original_filename:bundled_multi_file_placeholder")
    for list_field in ("linked_projects", "extracted_projects", "extracted_tasks", "linked_zettels", "extracted_zettels"):
        links = fm.get(list_field)
        if isinstance(links, list):
            for link in links:
                if isinstance(link, str) and link.strip():
                    if _resolve_wikilink_target(link, vault_root) is None:
                        missing.append(f"{list_field}:{link}")
    return (len(missing) == 0), missing


def evaluate_source_identity(
    collection_dir: Union[Path, str],
    *,
    source_bytes: Optional[bytes] = None,
    raw_bytes: Optional[bytes] = None,
    extracted_text: Optional[str] = None,
    precomputed_sha256: Optional[str] = None,
    source_url: Optional[str] = None,
    original_filename: Optional[str] = None,
    relative_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Unified source identity and deduplication engine returning one stable JSON-serializable dict
    across file, text, stdin, and sha256 modes.
    - Defines sha256 strictly as original binary bytes (None when bytes_available is False).
    - Keeps normalized_text_sha256 separate.
    - Distinguishes exact_duplicate, changed_version, incomplete_prior_ingestion, renamed_or_moved, and new_source.
    - Treats same source_url with changed bytes as a revision candidate (changed_version), not an exact duplicate.
    - Preserves provenance across renames/moves without inventing Google Drive URLs.
    """
    vault_root = Path(collection_dir).resolve()
    bytes_available = False
    binary_sha256: Optional[str] = None
    norm_text_sha256: Optional[str] = None
    effective_bytes = source_bytes if source_bytes is not None else raw_bytes

    if precomputed_sha256:
        binary_sha256 = precomputed_sha256.strip().lower()
        bytes_available = True
    elif effective_bytes is not None:
        binary_sha256 = compute_revision(effective_bytes)
        bytes_available = True

    if extracted_text is not None:
        norm_text = normalize_extracted_text(extracted_text)
        norm_text_sha256 = hashlib.sha256(norm_text.encode("utf-8")).hexdigest().lower()

    result: Dict[str, Any] = {
        "match_status": "new_source",
        "is_duplicate": False,
        "is_revision_candidate": False,
        "is_incomplete_prior": False,
        "is_renamed_or_moved": False,
        "existing_source_id": None,
        "existing_path": None,
        "sha256": binary_sha256,
        "bytes_available": bytes_available,
        "normalized_text_sha256": norm_text_sha256,
        "source_url": source_url,
        "supersedes": None,
        "provenance_action": "create_new_source",
        "missing_targets": [],
    }

    sources_dir = vault_root / "Sources"
    if not sources_dir.is_dir():
        return result

    norm_rel = relative_path.replace("\\", "/") if relative_path else None
    norm_fname = Path(original_filename).name if original_filename else (Path(norm_rel).name if norm_rel else None)

    for sf in sorted(sources_dir.rglob("*.md")):
        if sf.name == "README.md":
            continue
        try:
            raw_doc = sf.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(raw_doc)
        except Exception:
            continue

        existing_id = str(fm.get("id") or sf.stem)
        existing_rel_doc_path = sf.relative_to(vault_root).as_posix()
        existing_sha = str(fm.get("sha256") or "").strip().lower() or None
        existing_text_sha = str(fm.get("normalized_text_sha256") or "").strip().lower() or None
        if not existing_text_sha and "<untrusted_document_payload" in body:
            m = re.search(r"<untrusted_document_payload[^>]*>(.*?)</untrusted_document_payload>", body, re.DOTALL)
            if m:
                existing_text_sha = hashlib.sha256(normalize_extracted_text(m.group(1)).encode("utf-8")).hexdigest().lower()
        if not existing_text_sha and body.strip():
            existing_text_sha = hashlib.sha256(normalize_extracted_text(body).encode("utf-8")).hexdigest().lower()

        existing_url = fm.get("source_url")
        existing_url_str = str(existing_url).strip() if existing_url else None
        existing_fname = str(fm.get("original_filename") or "").strip() or None
        existing_locker_rel = str(fm.get("relative_path") or "").replace("\\", "/").strip() or None
        is_complete, missing_targets = _check_source_completeness(fm, vault_root)
        if bytes_available and binary_sha256 and existing_sha is None and fm.get("bytes_available") is False:
            is_complete = False
            missing_targets.append("sha256:binary_bytes_now_available")

        is_bundled_or_folder_url = bool(
            "original_filename:bundled_multi_file_placeholder" in missing_targets
            or (existing_url_str and "/drive/folders/" in existing_url_str)
        )
        effective_existing_url = None if is_bundled_or_folder_url else existing_url_str

        # 1. Exact binary SHA-256 match
        if bytes_available and binary_sha256 and existing_sha == binary_sha256:
            if not is_complete:
                result.update({
                    "match_status": "incomplete_prior_ingestion",
                    "is_duplicate": False,
                    "is_incomplete_prior": True,
                    "existing_source_id": existing_id,
                    "existing_path": existing_rel_doc_path,
                    "source_url": source_url if source_url is not None else effective_existing_url,
                    "provenance_action": "repair_incomplete_ingestion",
                    "missing_targets": missing_targets,
                })
                return result

            path_changed = (
                (norm_rel and existing_locker_rel and norm_rel != existing_locker_rel)
                or (norm_fname and existing_fname and norm_fname != existing_fname)
            )
            if path_changed:
                result.update({
                    "match_status": "renamed_or_moved",
                    "is_duplicate": True,
                    "is_renamed_or_moved": True,
                    "existing_source_id": existing_id,
                    "existing_path": existing_rel_doc_path,
                    "source_url": source_url if source_url is not None else effective_existing_url,
                    "provenance_action": "update_provenance_path",
                })
                return result

            result.update({
                "match_status": "exact_duplicate",
                "is_duplicate": True,
                "existing_source_id": existing_id,
                "existing_path": existing_rel_doc_path,
                "source_url": source_url if source_url is not None else effective_existing_url,
                "provenance_action": "skip_exact_duplicate",
            })
            return result

        # 2. Text-only match when original binary bytes are unavailable
        if not bytes_available and norm_text_sha256 and existing_text_sha == norm_text_sha256:
            if not is_complete:
                result.update({
                    "match_status": "incomplete_prior_ingestion",
                    "is_duplicate": False,
                    "is_incomplete_prior": True,
                    "existing_source_id": existing_id,
                    "existing_path": existing_rel_doc_path,
                    "source_url": source_url if source_url is not None else effective_existing_url,
                    "provenance_action": "repair_incomplete_ingestion",
                    "missing_targets": missing_targets,
                })
                return result
            result.update({
                "match_status": "exact_duplicate",
                "is_duplicate": True,
                "existing_source_id": existing_id,
                "existing_path": existing_rel_doc_path,
                "source_url": source_url if source_url is not None else effective_existing_url,
                "provenance_action": "skip_exact_duplicate",
            })
            return result

        # 3. Same URL or same filename/relative_path with different bytes -> revision candidate or incomplete prior
        url_matches = bool(source_url and existing_url_str and source_url.strip() == existing_url_str)
        fname_in_multi = bool(
            norm_fname
            and existing_fname
            and (norm_fname == existing_fname or norm_fname in [x.strip() for x in existing_fname.split(",")])
        )
        rel_matches = bool(norm_rel and existing_locker_rel and norm_rel == existing_locker_rel)

        if url_matches or rel_matches or fname_in_multi:
            if not is_complete:
                if (
                    bytes_available
                    and binary_sha256
                    and existing_sha
                    and existing_sha != binary_sha256
                    and existing_sha != EMPTY_BYTES_SHA256
                    and "sha256:mismatch_with_binary_bytes" not in missing_targets
                ):
                    missing_targets = list(missing_targets) + ["sha256:mismatch_with_binary_bytes"]
                result.update({
                    "match_status": "incomplete_prior_ingestion",
                    "is_duplicate": False,
                    "is_incomplete_prior": True,
                    "existing_source_id": existing_id,
                    "existing_path": existing_rel_doc_path,
                    "source_url": source_url if source_url is not None else effective_existing_url,
                    "provenance_action": "repair_incomplete_ingestion",
                    "missing_targets": missing_targets,
                })
                return result

            # If neither bytes nor text was provided (only URL lookup), and URL matched a complete record
            if not bytes_available and norm_text_sha256 is None and url_matches:
                result.update({
                    "match_status": "exact_duplicate",
                    "is_duplicate": True,
                    "existing_source_id": existing_id,
                    "existing_path": existing_rel_doc_path,
                    "source_url": effective_existing_url,
                    "provenance_action": "skip_exact_duplicate",
                })
                return result

            # Bytes or text were provided and differ from existing record -> changed_version!
            result.update({
                "match_status": "changed_version",
                "is_duplicate": False,
                "is_revision_candidate": True,
                "existing_source_id": existing_id,
                "existing_path": existing_rel_doc_path,
                "source_url": source_url if source_url is not None else effective_existing_url,
                "supersedes": f"[[Sources/{existing_id}]]",
                "provenance_action": "create_revision_superseding_prior",
            })
            return result

    return result




def find_exact_source_duplicate(
    source_bytes: bytes,
    collection_dir: Union[Path, str],
    source_url: Optional[str] = None
) -> Optional[Tuple[str, Path]]:
    """
    Calculates SHA-256 digest of source_bytes and scans Sources/**/*.md
    to detect existing exact duplicate records across sessions.
    Same URL with changed bytes is treated as a revision candidate (returns None), not an exact duplicate.
    Returns (source_id, file_path) if exact duplicate found, else None.
    """
    ident = evaluate_source_identity(
        collection_dir,
        source_bytes=source_bytes if source_bytes else None,
        source_url=source_url,
    )
    if ident.get("is_duplicate") and ident.get("existing_source_id") and ident.get("existing_path"):
        return (str(ident["existing_source_id"]), Path(collection_dir) / str(ident["existing_path"]))
    return None


# =========================================================================
# 3.1 Media Locker Discovery & Format Inspection
# =========================================================================

import zlib








# =========================================================================
# 4. Passive Text Quarantine Formatting
# =========================================================================

def sanitize_untrusted_payload(
    raw_text: str,
    source_id: str,
    sha256_digest: Optional[str],
    mime_type: str = "text/markdown"
) -> str:
    """
    Neutralizes closing delimiter escape sequences and encapsulates untrusted
    external text in protective XML boundary tags.
    """
    escaped_text = UNTRUSTED_CLOSING_TAG_PATTERN.sub(
        "&lt;/untrusted_document_payload&gt;",
        raw_text
    )
    from html import escape
    source_attr = escape(str(source_id), quote=True)
    sha_attr = escape(str(sha256_digest or "unavailable"), quote=True)
    mime_attr = escape(str(mime_type), quote=True)
    return (
        f'<untrusted_document_payload source_id="{source_attr}" '
        f'sha256="{sha_attr}" mime_type="{mime_attr}">\n'
        f'{escaped_text}\n'
        f'</untrusted_document_payload>'
    )


# =========================================================================
# 5. Deadline Evidence Normalization & Horizon Eligibility
# =========================================================================

TZ_ABBREV_OFFSETS: Dict[str, str] = {
    "CDT": "-05:00",
    "CST": "-06:00",
    "EDT": "-04:00",
    "EST": "-05:00",
    "MDT": "-06:00",
    "MST": "-07:00",
    "PDT": "-07:00",
    "PST": "-08:00",
}


def resolve_chicago_tz() -> Any:
    """Resolve the named zone through installed IANA data; no inferred host environment."""
    if ZoneInfo is None:
        raise RuntimeError("IANA timezone support is required")
    return ZoneInfo("America/Chicago")


def get_chicago_offset_str(target_date: Optional[Union[date, datetime]] = None) -> str:
    """
    Returns explicit offset '+HH:MM' or '-HH:MM' for America/Chicago on target_date.
    Defaults to current date if target_date is omitted.
    """
    if target_date is None:
        target_date = date.today()
    tz = resolve_chicago_tz()
    if isinstance(target_date, datetime):
        dt = target_date if target_date.tzinfo is not None else target_date.replace(tzinfo=tz)
    else:
        dt = datetime(target_date.year, target_date.month, target_date.day, 12, 0, 0, tzinfo=tz)
    offset = dt.utcoffset()
    if offset is None:
        return "-06:00"
    total_seconds = int(offset.total_seconds())
    sign = "+" if total_seconds >= 0 else "-"
    total_seconds = abs(total_seconds)
    hours, remainder = divmod(total_seconds, 3600)
    minutes = remainder // 60
    return f"{sign}{hours:02d}:{minutes:02d}"


def normalize_deadline_evidence(
    raw_deadline: Optional[str],
    *,
    filename: Optional[str] = None,
    source_of_deadline: str = "content",
    default_local_offset: str = "-05:00",
) -> Dict[str, Any]:
    """
    Parses and normalizes deadline strings into schema-compatible fields without inventing times
    for date-only deadlines and never treating a screenshot filename timestamp as a deadline.
    """
    if source_of_deadline == "filename" or (
        filename and raw_deadline and raw_deadline.strip() in filename and SCREENSHOT_FILENAME_PATTERN.match(Path(filename).stem)
    ):
        return {
            "due": None,
            "due_time": None,
            "due_timezone": None,
            "due_at": None,
            "date_uncertain": True,
            "review_required": True,
            "review_notes": "Rejected filename timestamp as deadline; screenshot filename indicates capture time only.",
        }

    if raw_deadline is None:
        return {
            "due": None,
            "due_time": None,
            "due_timezone": None,
            "due_at": None,
            "date_uncertain": True,
            "review_required": False,
            "review_notes": None,
        }

    s = str(raw_deadline).strip()
    if not s or s.upper() in {"TBD", "TBA", "NULL", "NONE", "UNANNOUNCED", "UNKNOWN"}:
        return {
            "due": None,
            "due_time": None,
            "due_timezone": None,
            "due_at": None,
            "date_uncertain": True,
            "review_required": False,
            "review_notes": None,
        }

    # 1. Exact ISO date-only (YYYY-MM-DD) -> do NOT invent due_time or due_at
    if DATE_ONLY_PATTERN.match(s):
        return {
            "due": s,
            "due_time": None,
            "due_timezone": None,
            "due_at": None,
            "date_uncertain": False,
            "review_required": False,
            "review_notes": None,
        }

    # 2. US short date only (M/D/YY or M/D/YYYY) -> do NOT invent due_time or due_at
    m_short = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s)
    if m_short:
        month, day, year_raw = int(m_short.group(1)), int(m_short.group(2)), int(m_short.group(3))
        year = 2000 + year_raw if year_raw < 100 else year_raw
        iso_d = date(year, month, day).isoformat()
        return {
            "due": iso_d,
            "due_time": None,
            "due_timezone": None,
            "due_at": None,
            "date_uncertain": False,
            "review_required": False,
            "review_notes": None,
        }

    # 3. Timed deadline (e.g. "9/29/26, 11:59 PM (CDT)" or "2026-09-29 23:59 CDT")
    m_timed = re.match(
        r"^(?:Past\s+due\s*\|\s*)?(\d{1,2}/\d{1,2}/\d{2,4}|\d{4}-\d{2}-\d{2})[\s,]+(\d{1,2}):(\d{2})(?::(\d{2}))?\s*(AM|PM)?\s*(?:\(?([A-Z]{3,4}|[+\-]\d{2}:\d{2})\)?)?",
        s,
        re.IGNORECASE,
    )
    if m_timed:
        date_part, hh_raw, mm_raw, ss_raw, ampm, tz_token = m_timed.groups()
        if "/" in date_part:
            mm_d, dd_d, yy_d = [int(x) for x in date_part.split("/")]
            yy_d = 2000 + yy_d if yy_d < 100 else yy_d
            iso_date = date(yy_d, mm_d, dd_d).isoformat()
        else:
            iso_date = date_part
        hh = int(hh_raw)
        mm = int(mm_raw)
        ss = int(ss_raw) if ss_raw else 0
        if ampm:
            ampm_u = ampm.upper()
            if ampm_u == "PM" and hh < 12:
                hh += 12
            elif ampm_u == "AM" and hh == 12:
                hh = 0
        time_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
        tz_label = tz_token.upper() if tz_token else None
        tz_offset = TZ_ABBREV_OFFSETS.get(tz_label, tz_label if (tz_label and re.match(r"^[+\-]\d{2}:\d{2}$", tz_label)) else default_local_offset)
        due_at = f"{iso_date}T{time_str}{tz_offset}"
        return {
            "due": iso_date,
            "due_time": time_str,
            "due_timezone": tz_label or default_local_offset,
            "due_at": due_at,
            "date_uncertain": False,
            "review_required": False,
            "review_notes": None,
        }

    # 4. Full RFC 3339 timestamp with explicit offset
    if TIMEZONE_OFFSET_PATTERN.match(s):
        iso_date = s[:10]
        time_part = s[11:19]
        tz_part = s[-6:]
        return {
            "due": iso_date,
            "due_time": time_part,
            "due_timezone": tz_part,
            "due_at": s,
            "date_uncertain": False,
            "review_required": False,
            "review_notes": None,
        }

    # Unrecognized/ambiguous string (e.g. "Mid-October", "Week 5") -> uncertain
    return {
        "due": None,
        "due_time": None,
        "due_timezone": None,
        "due_at": None,
        "date_uncertain": True,
        "review_required": True,
        "review_notes": f"Ambiguous deadline expression preserved as uncertain: '{s}'",
    }


def process_uncertain_dates(
    deliverables: List[Dict[str, Any]],
    *,
    normalize_raw: bool = False,
) -> List[Dict[str, Any]]:
    """Identifies ambiguous/TBD deadlines and normalizes due: null with date_uncertain: true."""
    processed = []
    for d in deliverables:
        item = dict(d)
        due_val = item.get("due")
        if due_val in (None, "", "TBD", "tbd", "null", "None"):
            item["due"] = None
            item["date_uncertain"] = True
        elif isinstance(due_val, str):
            stripped = due_val.strip()
            if DATE_ONLY_PATTERN.match(stripped):
                item["due"] = stripped
                if "date_uncertain" not in item:
                    item["date_uncertain"] = False
            elif normalize_raw:
                norm = normalize_deadline_evidence(stripped, filename=item.get("source_filename"))
                item["due"] = norm["due"]
                item["date_uncertain"] = norm["date_uncertain"]
                if norm["due_time"] and "due_time" not in item:
                    item["due_time"] = norm["due_time"]
                if norm["due_timezone"] and "due_timezone" not in item:
                    item["due_timezone"] = norm["due_timezone"]
                if norm["due_at"] and "due_at" not in item:
                    item["due_at"] = norm["due_at"]
            else:
                item["due"] = None
                item["date_uncertain"] = True
        else:
            item["due"] = None
            item["date_uncertain"] = True
        processed.append(item)
    return processed


def classify_deliverable_horizons(
    deliverables: List[Dict[str, Any]],
    *,
    horizon_days: int = 14,
    reference_date: Optional[date] = None,
    existing_tasks: Optional[Dict[str, Dict[str, Any]]] = None,
    vault_root: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """
    Separates deliverables into:
    - overdue: due < reference_date and status not in {done, archived}
    - imminent: reference_date <= due <= reference_date + horizon_days and status not in {done, archived}
    - uncertain: due is None or date_uncertain is True and status not in {done, archived}
    - future: due > reference_date + horizon_days and status not in {done, archived}
    - excluded_done_or_archived: status in {done, archived} (excluded from new task materialization)
    Also flags contradictory or stale deadline evidence against existing tasks and prepares scheduling_handoff
    with scheduled: None (never auto-scheduling during ingestion).
    """
    ref = reference_date or date.today()
    overdue: List[Dict[str, Any]] = []
    imminent: List[Dict[str, Any]] = []
    uncertain: List[Dict[str, Any]] = []
    future: List[Dict[str, Any]] = []
    excluded: List[Dict[str, Any]] = []
    conflicts: List[Dict[str, Any]] = []

    task_lookup: Dict[str, Dict[str, Any]] = {}
    if vault_root is not None:
        v_path = Path(vault_root).resolve()
        tasks_dir = v_path / "TaskNotes" / "Tasks"
        if tasks_dir.is_dir():
            for tf in sorted(tasks_dir.glob("*.md")):
                if tf.name in {"README.md", "example-task.md"} or tf.name.startswith("."):
                    continue
                try:
                    tfm, _ = parse_frontmatter(tf.read_text(encoding="utf-8"))
                    t_entry = {
                        "path": tf.relative_to(v_path).as_posix(),
                        "due": str(tfm["due"]) if tfm.get("due") is not None else None,
                        "status": str(tfm.get("status") or "todo").lower(),
                        "googleCalendarEventId": tfm.get("googleCalendarEventId"),
                    }
                    if tfm.get("deliverable_id"):
                        task_lookup[str(tfm["deliverable_id"])] = t_entry
                    task_lookup[tf.stem] = t_entry
                    task_lookup[f"[[TaskNotes/Tasks/{tf.stem}]]"] = t_entry
                except Exception:
                    continue
    if existing_tasks:
        task_lookup.update(existing_tasks)

    for raw_d in deliverables:
        d = dict(raw_d)
        did = str(d.get("id") or "")
        status = str(d.get("status") or "todo").lower()
        t_ref = str(d.get("task_ref") or "").strip()
        linked_task = task_lookup.get(did) or (task_lookup.get(t_ref) if t_ref else None)
        if linked_task and str(linked_task.get("status") or "").lower() in {"done", "archived"}:
            status = str(linked_task.get("status")).lower()
            d["status"] = status

        if status in {"done", "archived"}:
            d["horizon_bucket"] = "completed" if status == "done" else "archived"
            excluded.append(d)
            continue

        # Check for contradictory or stale deadline evidence against existing task or conflicting sources
        if linked_task and d.get("due") and linked_task.get("due") and str(d.get("due")) != str(linked_task.get("due")):
            d["conflict_flag"] = True
            note = (
                f"Contradictory deadline between source ({d.get('due')}) and existing task "
                f"{linked_task.get('path', did)} ({linked_task.get('due')}). Requires human review."
            )
            d["conflict_notes"] = f"{d.get('conflict_notes')}; {note}" if d.get("conflict_notes") else note
            conflicts.append({"deliverable_id": did, "reason": note})
        elif d.get("conflict_flag"):
            conflicts.append({"deliverable_id": did, "reason": d.get("conflict_notes") or "Flagged conflict"})

        due_val = d.get("due")
        is_uncertain = bool(d.get("date_uncertain", False)) or not due_val

        if is_uncertain:
            d["horizon_bucket"] = "uncertain"
            uncertain.append(d)
            continue

        try:
            if isinstance(due_val, date) and not isinstance(due_val, datetime):
                due_date = due_val
            elif isinstance(due_val, str) and DATE_ONLY_PATTERN.match(due_val.strip()[:10]):
                due_date = date.fromisoformat(due_val.strip()[:10])
            else:
                raise ValueError(f"Non-ISO date value: {due_val!r}")
            days_until = (due_date - ref).days
            if days_until < 0:
                d["horizon_bucket"] = "overdue"
                overdue.append(d)
            elif days_until <= horizon_days:
                d["horizon_bucket"] = "imminent"
                imminent.append(d)
            else:
                d["horizon_bucket"] = "future"
                future.append(d)
        except Exception:
            d["horizon_bucket"] = "uncertain"
            d["date_uncertain"] = True
            uncertain.append(d)

    eligible_for_tasks = overdue + imminent + uncertain
    scheduling_handoff = [
        {
            "deliverable_id": item.get("id"),
            "title": item.get("title"),
            "due": item.get("due"),
            "due_time": item.get("due_time"),
            "due_timezone": item.get("due_timezone"),
            "due_at": item.get("due_at"),
            "horizon_bucket": item.get("horizon_bucket"),
            "scheduled": None,  # Never auto-scheduled during ingestion
            "review_required": bool(item.get("conflict_flag") or item.get("horizon_bucket") in {"overdue", "uncertain"}),
        }
        for item in eligible_for_tasks
    ]

    return {
        "reference_date": ref.isoformat(),
        "horizon_days": horizon_days,
        "overdue": overdue,
        "imminent": imminent,
        "uncertain": uncertain,
        "future": future,
        "excluded_done_or_archived": excluded,
        "eligible_for_task_materialization": eligible_for_tasks,
        "conflicts_requiring_review": conflicts,
        "scheduling_handoff": scheduling_handoff,
    }


def filter_horizon_deliverables(
    deliverables: List[Dict[str, Any]],
    horizon_days: int = 14,
    reference_date: Optional[date] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Partitions deliverables into (active_deliverables, inert_deliverables).
    Excludes done and archived items from active task materialization.
    Active deliverables are overdue, due within reference_date + horizon_days, or have uncertain dates.
    Inert deliverables are due > horizon_days in the future.
    """
    classified = classify_deliverable_horizons(
        deliverables, horizon_days=horizon_days, reference_date=reference_date
    )
    active = classified["overdue"] + classified["imminent"] + classified["uncertain"]
    inert = classified["future"]
    return active, inert


# =========================================================================
# 5.1 Gap-Filler Candidate Selection & Prioritization Engine (/plan)
# =========================================================================

def is_quick_capture_task(frontmatter: Dict[str, Any]) -> bool:
    """
    Determines whether a task note represents a quick-capture task (e.g. from Google Tasks,
    inbox capture, or standalone external capture policy).
    """
    if not isinstance(frontmatter, dict):
        return False
    # Direct external IDs
    if frontmatter.get("external_item_id") or frontmatter.get("external_id"):
        return True

    # Source aliases (normalize hyphens / underscores)
    for alias_key in ("external_source_alias", "source_alias", "source", "capture_source"):
        val = str(frontmatter.get(alias_key) or "").strip().lower().replace("_", "-")
        if val in {"quick-capture", "inbox", "capture", "google-tasks"}:
            return True

    # Integrations
    for integ_key in ("external_integration", "integration", "external_source"):
        val = str(frontmatter.get(integ_key) or "").strip().lower().replace("_", "-")
        if val in {"google-tasks", "quick-capture", "inbox"}:
            return True

    # Standalone capture policy
    for pol_key in ("capture_policy", "standalone_future_task_policy", "capture_type", "source_type"):
        val = str(frontmatter.get(pol_key) or "").strip().lower().replace("_", "-")
        if val in {"standalone", "quick-capture", "inbox", "create-inert-task"}:
            return True

    # Evidence reference (e.g. google-tasks:..., quick-capture:..., capture:...)
    evidence = str(frontmatter.get("evidence_ref") or "").strip().lower().replace("_", "-")
    if evidence.startswith("google-tasks:") or "quick-capture" in evidence or evidence.startswith("capture:"):
        return True

    # Source reference (e.g. [[Sources/capture-google-tasks...]], [[Sources/capture_...]], [[Sources/quick-capture...]])
    src_ref = str(frontmatter.get("source_ref") or "").strip().lower().replace("_", "-")
    if "capture-google-tasks" in src_ref or "capture-" in src_ref or "quick-capture" in src_ref:
        return True

    # Tags
    tags = frontmatter.get("tags") or []
    if isinstance(tags, list):
        for t in tags:
            t_str = str(t).strip().lower().replace("_", "-")
            if t_str in {"quick-capture", "inbox-capture", "quick_capture", "capture"}:
                return True

    return False


def select_gap_filler_candidates(
    vault_root: Union[Path, str],
    *,
    target_count: int = 3,
    reference_date: Optional[date] = None,
    horizon_days: int = 14,
    preferred_modalities: Optional[Sequence[str]] = None,
    exclude_paths: Optional[Union[Set[str], Sequence[str]]] = None,
) -> Dict[str, Any]:
    """
    Selects gap-filler candidates for the /plan interactive feedback gate.

    Prioritization Rule:
    1. Unscheduled quick capture tasks (tasks in TaskNotes/Tasks/ with external_item_id,
       source_alias: quick-capture, or standalone capture with status: todo and scheduled: null)
       serve as the PRIMARY gap-filler candidates.
    2. If there are not enough preexisting quick capture tasks to fill available gaps or
       reach target_count, gap-filler candidates are INFERRED from:
       - Roadmap backlog deliverables / active project deliverable candidates (within the 14-day horizon),
       - Routine low-energy administrative/kinetic/synthesis backlog tasks,
       - Routine system maintenance templates.
    """
    v_path = Path(vault_root).resolve()
    ref = reference_date or date.today()
    target = max(1, target_count)

    def _parse_urgency(val: Any) -> int:
        try:
            if val is not None:
                return int(val)
        except (ValueError, TypeError):
            m = {"urgent": 4, "high": 3, "medium": 2, "normal": 2, "low": 1}
            return m.get(str(val).strip().lower(), 2)
        return 2

    def _parse_time_estimate(val: Any, default: int = 45) -> int:
        try:
            if isinstance(val, str) and val.endswith("m"):
                return int(val[:-1])
            if val is not None:
                return int(val)
        except (ValueError, TypeError):
            return default
        return default

    exclude_set: Set[str] = set()
    if exclude_paths:
        raw_list: List[str] = []
        if isinstance(exclude_paths, str):
            raw_list = [exclude_paths]
        else:
            raw_list = list(exclude_paths)
        for ep in raw_list:
            for sub in str(ep).split(","):
                sub_clean = sub.strip()
                if not sub_clean:
                    continue
                exclude_set.add(sub_clean)
                unbracketed = sub_clean.strip("[]").strip()
                exclude_set.add(unbracketed)
                stem = Path(unbracketed).stem
                name = Path(unbracketed).name
                exclude_set.add(stem)
                exclude_set.add(name)
                exclude_set.add(f"[[{stem}]]")
                exclude_set.add(f"[[TaskNotes/Tasks/{stem}]]")
                exclude_set.add(f"TaskNotes/Tasks/{name}")
                exclude_set.add(f"TaskNotes/Tasks/{stem}.md")

    pref_modalities_list: List[str] = []
    if preferred_modalities:
        raw_mods: List[str] = []
        if isinstance(preferred_modalities, str):
            raw_mods = [preferred_modalities]
        else:
            raw_mods = list(preferred_modalities)
        for m in raw_mods:
            for sub in str(m).split(","):
                sub_clean = sub.strip().lower()
                if sub_clean and sub_clean not in pref_modalities_list:
                    pref_modalities_list.append(sub_clean)

    quick_capture_tasks: List[Dict[str, Any]] = []
    backlog_tasks: List[Dict[str, Any]] = []
    ineligible_deliv_ids: Set[str] = set()
    ineligible_task_refs: Set[str] = set()

    tasks_dir = v_path / "TaskNotes" / "Tasks"
    if tasks_dir.is_dir():
        for tf in sorted(tasks_dir.glob("*.md")):
            if tf.name in {"README.md", "example-task.md"} or tf.name.startswith("."):
                continue
            rel_path = tf.relative_to(v_path).as_posix()
            try:
                fm, _ = parse_frontmatter(tf.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(fm, dict):
                continue

            did = str(fm.get("deliverable_id") or "").strip()
            task_ref_forms = {
                rel_path,
                tf.name,
                tf.stem,
                f"[[{tf.stem}]]",
                f"[[{rel_path[:-3]}]]",
                f"[[TaskNotes/Tasks/{tf.stem}]]",
            }

            # Check if explicitly excluded
            if any(ref_form in exclude_set for ref_form in task_ref_forms):
                if did:
                    exclude_set.add(did)
                    ineligible_deliv_ids.add(did)
                ineligible_task_refs.update(task_ref_forms)
                continue

            # Check status: done/archived/completed/cancelled tasks are ineligible
            status = str(fm.get("status") or "todo").strip().lower()
            if status in {"done", "archived", "completed", "cancelled"}:
                if did:
                    ineligible_deliv_ids.add(did)
                ineligible_task_refs.update(task_ref_forms)
                continue

            # Check scheduled: tasks already scheduled on calendar are ineligible
            sched = fm.get("scheduled")
            if sched is not None and str(sched).strip() != "" and str(sched).strip().lower() != "null":
                if did:
                    ineligible_deliv_ids.add(did)
                ineligible_task_refs.update(task_ref_forms)
                continue

            due_val = fm.get("due")
            due_str = str(due_val) if due_val is not None else None
            due_bucket = 2
            days_until = 9999
            if due_str and DATE_ONLY_PATTERN.match(due_str[:10]):
                try:
                    d_obj = date.fromisoformat(due_str[:10])
                    days_until = (d_obj - ref).days
                    if days_until < 0:
                        due_bucket = 0  # overdue
                    elif days_until <= horizon_days:
                        due_bucket = 1  # imminent
                    else:
                        due_bucket = 3  # future
                except ValueError:
                    due_bucket = 2
            elif bool(fm.get("date_uncertain")):
                due_bucket = 2
            else:
                hb = str(fm.get("horizon_bucket") or "").strip().lower()
                if hb == "overdue":
                    due_bucket = 0
                elif hb == "imminent":
                    due_bucket = 1
                elif hb == "future":
                    due_bucket = 3
                elif hb == "uncertain":
                    due_bucket = 2

            urgency = _parse_urgency(fm.get("urgency_tier"))
            prio_rank = {"urgent": 0, "high": 1, "normal": 2, "low": 3, "none": 4}.get(
                str(fm.get("priority") or "normal").strip().lower(), 2
            )
            time_est = _parse_time_estimate(fm.get("timeEstimate"), 45)

            task_entry = {
                "title": str(fm.get("title") or tf.stem),
                "path": rel_path,
                "wikilink": f"[[{rel_path[:-3]}]]",
                "tags": [str(t) for t in (fm.get("tags") or [])],
                "modality": str(fm.get("modality") or "administrative"),
                "timeEstimate": time_est,
                "energy": str(fm.get("energy") or "medium"),
                "friction": str(fm.get("friction") or "low"),
                "priority": str(fm.get("priority") or "normal"),
                "urgency_tier": urgency,
                "due": due_str,
                "external_item_id": fm.get("external_item_id") or fm.get("external_id"),
                "external_source_alias": fm.get("external_source_alias") or fm.get("source_alias") or fm.get("external_source"),
                "external_integration": fm.get("external_integration") or fm.get("integration"),
                "project_ref": fm.get("project_ref"),
                "deliverable_id": did or None,
                "_due_bucket": due_bucket,
                "_days_until": days_until,
                "_urgency": urgency,
                "_prio_rank": prio_rank,
            }

            if is_quick_capture_task(fm):
                quick_capture_tasks.append(task_entry)
            else:
                backlog_tasks.append(task_entry)

    # Sort quick_capture_tasks: overdue -> imminent -> undated -> future
    # When preferred modalities specified, rank matching modalities first within each due bucket
    qc_mod_weights: Dict[str, int] = {}
    if pref_modalities_list:
        qc_mod_weights = {m: idx for idx, m in enumerate(pref_modalities_list)}

    quick_capture_tasks.sort(
        key=lambda x: (
            x["_due_bucket"],
            qc_mod_weights.get(x["modality"].lower(), 99),
            -x["_urgency"],
            x["_prio_rank"],
            x["_days_until"],
            x["title"],
        )
    )

    primary_candidates: List[Dict[str, Any]] = []
    for idx, item in enumerate(quick_capture_tasks[:target], start=1):
        clean_item = dict(item)
        for k in ("_due_bucket", "_days_until", "_urgency", "_prio_rank"):
            clean_item.pop(k, None)
        clean_item["candidate_id"] = f"qc-{idx:02d}"
        clean_item["candidate_type"] = "quick_capture"
        clean_item["inference_source"] = None
        primary_candidates.append(clean_item)

    needed_inferred = target - len(primary_candidates)
    inferred_candidates: List[Dict[str, Any]] = []
    inference_triggered = needed_inferred > 0

    if needed_inferred > 0:
        # Preferred order for gap-filling: administrative & kinetic (ideal for slump/defrost), synthesis (recovery), analytical (deep)
        modality_weights = {"administrative": 0, "kinetic": 1, "synthesis": 2, "analytical": 3}
        if pref_modalities_list:
            modality_weights = {m: idx for idx, m in enumerate(pref_modalities_list)}
            modality_weights.setdefault("administrative", 90)
            modality_weights.setdefault("kinetic", 91)
            modality_weights.setdefault("synthesis", 92)
            modality_weights.setdefault("analytical", 93)

        backlog_tasks.sort(
            key=lambda x: (
                modality_weights.get(x["modality"].lower(), 99),
                x["_due_bucket"],
                -x["_urgency"],
                x["_prio_rank"],
                x["_days_until"],
            )
        )

        for item in backlog_tasks:
            if len(inferred_candidates) >= needed_inferred:
                break
            clean_item = dict(item)
            for k in ("_due_bucket", "_days_until", "_urgency", "_prio_rank"):
                clean_item.pop(k, None)
            idx = len(inferred_candidates) + 1
            clean_item["candidate_id"] = f"inf-{idx:02d}"
            clean_item["candidate_type"] = "inferred"
            mod = clean_item.get("modality", "").lower()
            if clean_item.get("project_ref"):
                clean_item["inference_source"] = "project_deliverable" if clean_item.get("deliverable_id") else "roadmap_backlog"
            elif mod in {"administrative", "kinetic"}:
                clean_item["inference_source"] = "administrative_backlog"
            elif mod == "synthesis":
                clean_item["inference_source"] = "synthesis_backlog"
            else:
                clean_item["inference_source"] = "task_backlog"
            inferred_candidates.append(clean_item)

    # If still needed, infer from Projects/*/Roadmap.md deliverables
    if len(inferred_candidates) < needed_inferred:
        existing_deliv_ids = set()
        for t in quick_capture_tasks + backlog_tasks:
            if t.get("deliverable_id"):
                existing_deliv_ids.add(str(t["deliverable_id"]))

        for rm in sorted(v_path.glob("Projects/*/Roadmap.md")):
            if len(inferred_candidates) >= needed_inferred:
                break
            try:
                fm, _ = parse_frontmatter(rm.read_text(encoding="utf-8"))
                delivs = fm.get("deliverables", [])
                if not isinstance(delivs, list):
                    continue
                proj_id = fm.get("project_id") or rm.parent.name
                classified = classify_deliverable_horizons(
                    delivs,
                    reference_date=ref,
                    horizon_days=horizon_days,
                    vault_root=v_path,
                )
                pool = classified["imminent"] + classified["overdue"] + classified["uncertain"]
                for d in pool:
                    if len(inferred_candidates) >= needed_inferred:
                        break
                    did = str(d.get("id") or "").strip()
                    t_ref = str(d.get("task_ref") or "").strip()
                    if not did and not t_ref:
                        continue
                    if did in existing_deliv_ids or did in ineligible_deliv_ids or did in exclude_set:
                        continue
                    if t_ref:
                        t_clean = t_ref.strip("[]").strip()
                        if (
                            t_ref in exclude_set
                            or t_clean in exclude_set
                            or Path(t_clean).stem in exclude_set
                            or t_ref in ineligible_task_refs
                            or f"[[{t_clean}]]" in ineligible_task_refs
                            or f"[[TaskNotes/Tasks/{Path(t_clean).stem}]]" in ineligible_task_refs
                        ):
                            continue
                    existing_deliv_ids.add(did)
                    idx = len(inferred_candidates) + 1
                    inferred_candidates.append({
                        "candidate_id": f"inf-{idx:02d}",
                        "candidate_type": "inferred",
                        "inference_source": "project_deliverable",
                        "title": str(d.get("title") or did),
                        "path": None,
                        "wikilink": None,
                        "tags": ["task", f"project-{proj_id}"],
                        "modality": str(d.get("modality") or "analytical"),
                        "timeEstimate": _parse_time_estimate(d.get("timeEstimate"), 45),
                        "energy": str(d.get("energy") or "medium"),
                        "friction": str(d.get("friction") or "medium"),
                        "priority": str(d.get("priority") or "normal"),
                        "urgency_tier": _parse_urgency(d.get("urgency_tier")),
                        "due": str(d.get("due")) if d.get("due") is not None else None,
                        "external_item_id": None,
                        "external_source_alias": None,
                        "external_integration": None,
                        "project_ref": f"[[Projects/{proj_id}/Roadmap]]",
                        "deliverable_id": did or None,
                    })
            except Exception:
                continue

    # If STILL needed (e.g. completely empty vault or everything scheduled), provide routine low-energy administrative backlog
    if len(inferred_candidates) < needed_inferred:
        standard_fallbacks = [
            {
                "title": "Slipbox hygiene & literature note review",
                "tags": ["task", "chrysalis"],
                "modality": "synthesis",
                "timeEstimate": 45,
                "energy": "medium",
                "friction": "low",
                "inference_source": "administrative_backlog",
            },
            {
                "title": "Digital workspace & backlog triage",
                "tags": ["task"],
                "modality": "administrative",
                "timeEstimate": 20,
                "energy": "low",
                "friction": "low",
                "inference_source": "administrative_backlog",
            },
            {
                "title": "Physical workspace & hardware maintenance",
                "tags": ["task"],
                "modality": "kinetic",
                "timeEstimate": 30,
                "energy": "low",
                "friction": "low",
                "inference_source": "administrative_backlog",
            },
        ]
        for fb in standard_fallbacks:
            if len(inferred_candidates) >= needed_inferred:
                break
            idx = len(inferred_candidates) + 1
            inferred_candidates.append({
                "candidate_id": f"inf-{idx:02d}",
                "candidate_type": "inferred",
                "inference_source": fb["inference_source"],
                "title": fb["title"],
                "path": None,
                "wikilink": None,
                "tags": fb["tags"],
                "modality": fb["modality"],
                "timeEstimate": fb["timeEstimate"],
                "energy": fb["energy"],
                "friction": fb["friction"],
                "priority": "normal",
                "urgency_tier": 2,
                "due": None,
                "external_item_id": None,
                "external_source_alias": None,
                "external_integration": None,
                "project_ref": None,
                "deliverable_id": None,
            })

    all_candidates = primary_candidates + inferred_candidates
    return {
        "reference_date": ref.isoformat(),
        "target_count": target,
        "quick_capture_count": len(quick_capture_tasks),
        "inferred_count": len(inferred_candidates),
        "inference_triggered": inference_triggered,
        "primary_candidates": primary_candidates,
        "inferred_candidates": inferred_candidates,
        "candidates": all_candidates,
    }


def format_gap_fillers_markdown(gap_result: Dict[str, Any]) -> str:
    """
    Renders gap-filler candidates into standard Markdown matching the /plan presentation format.
    """
    primary = gap_result.get("primary_candidates") or []
    inferred = gap_result.get("inferred_candidates") or []
    all_cands = gap_result.get("candidates") or (primary + inferred)
    if not all_cands:
        return "#### Gap-Filler Candidates:\n*(No eligible gap-filler candidates available)*"

    if primary and not inferred:
        header = "#### Gap-Filler Candidates (Primary: Quick-Capture):"
    elif inferred and not primary:
        header = "#### Inferred Gap-Filler Candidates:"
    else:
        header = "#### Gap-Filler Candidates (Primary: Quick-Capture & Inferred Fallback):"

    lines = [header]
    for c in all_cands:
        cid = c.get("candidate_id") or "cand"
        title = c.get("title") or "Untitled Task"
        tags = c.get("tags") or []
        tag_str = " ".join(f"#{t}" for t in tags) if tags else "#task"
        mod = c.get("modality") or "administrative"
        est = f"{c.get('timeEstimate', 45)}m"
        energy = str(c.get("energy") or "medium").capitalize()
        ctype = c.get("candidate_type")
        due = c.get("due")
        due_suffix = f" | Due: {due}" if due else ""

        if ctype == "quick_capture":
            src_note = f"Quick-Capture{due_suffix}"
        else:
            inf_src = str(c.get("inference_source") or "backlog").replace("_", " ").title()
            src_note = f"Inferred: {inf_src}{due_suffix}"

        lines.append(f"- [ ] **[{cid}] {title}** (`{tag_str}` | `{mod}` | {est} | {energy}) *({src_note})*")

    return "\n".join(lines)


# =========================================================================
# 6. Dynamic Cognitive Multiplier Learning
# =========================================================================

def calculate_dynamic_multiplier(
    current_multiplier: float,
    actual_duration_minutes: float,
    estimated_duration_minutes: float,
    learning_rate: float = 0.10
) -> float:
    """
    Calculates updated cognitive modality multiplier bounded strictly in [0.20, 2.00].
    Multiplier_new = Multiplier_current + alpha * (T_actual / T_estimated - Multiplier_current)
    """
    if estimated_duration_minutes <= 0:
        ratio = 1.0
    else:
        ratio = actual_duration_minutes / estimated_duration_minutes

    updated = current_multiplier + learning_rate * (ratio - current_multiplier)
    clamped = max(0.20, min(2.00, updated))
    return round(clamped, 2)


# =========================================================================
# 7. Project & Syllabus Reconciliation Engine
# =========================================================================

def _slugify_deliverable_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.strip().lower()).strip("-")
    return slug or "deliverable"


def reconcile_syllabus(
    existing_roadmap_path: Union[Path, str],
    new_deliverables: Union[List[Dict[str, Any]], str],
    *,
    mode: Optional[str] = None,
    authoritative_replacement: Optional[bool] = None,
    source_scope: Optional[str] = None,
    source_ref: Optional[str] = None,
    extraction_status: str = "complete",
) -> SyllabusDiff:
    """
    Reconciles extracted deliverables against an existing project Roadmap.md.
    - Supplementary ingestion is additive by default (mode='supplementary' or authoritative_replacement=False).
    - Missing deliverables are marked dropped (status: archived) ONLY for an explicitly identified
      authoritative replacement of the same source_scope/source_ref.
    - Empty, failed, malformed, or partial extraction NEVER implies deletion (dropped = []).
    - Preserves completed (done) and archived status, user_modified edits, existing task_ref links,
      calendar identifiers (googleCalendarEventId), and unrelated deliverables from other sources.
    - Flags conflicting dates across supplementary sources (conflict_flag: True, conflict_notes).
    - Keyed by deliverable identity (id / explicit title), never collapsing distinct assignments
      that share identical or similar rubric instructions.
    """
    roadmap_path = Path(existing_roadmap_path)
    existing_fm: Dict[str, Any] = {}
    if roadmap_path.exists():
        try:
            existing_fm, _ = parse_frontmatter(roadmap_path.read_text(encoding="utf-8"))
        except Exception:
            existing_fm = {}

    project_id = str(existing_fm.get("project_id", roadmap_path.parent.name if roadmap_path.name == "Roadmap.md" else "project"))
    old_items: List[Dict[str, Any]] = [
        dict(item) for item in (existing_fm.get("deliverables") or []) if isinstance(item, dict) and ("id" in item or "title" in item)
    ]
    for item in old_items:
        if "id" not in item or not item["id"]:
            item["id"] = _slugify_deliverable_id(str(item.get("title", "deliverable")))
    old_by_id = {str(item["id"]): dict(item) for item in old_items}

    # Parse new_deliverables and detect empty/failed/malformed input
    items_to_compare: List[Dict[str, Any]] = []
    parse_failed = False
    if isinstance(new_deliverables, list):
        items_to_compare = [dict(d) for d in new_deliverables if isinstance(d, dict)]
    elif isinstance(new_deliverables, str):
        stripped_input = new_deliverables.strip()
        if not stripped_input:
            items_to_compare = []
        else:
            try:
                loaded = yaml.safe_load(stripped_input)
                if isinstance(loaded, list):
                    items_to_compare = [dict(d) for d in loaded if isinstance(d, dict)]
                elif isinstance(loaded, dict) and "deliverables" in loaded and isinstance(loaded["deliverables"], list):
                    items_to_compare = [dict(d) for d in loaded["deliverables"] if isinstance(d, dict)]
                else:
                    parse_failed = True
            except Exception:
                parse_failed = True

    # Empty, failed, or partial extraction must NEVER imply deletion!
    if parse_failed or not items_to_compare or extraction_status in {"empty", "failed", "partial"}:
        return SyllabusDiff(
            project_id=project_id,
            added=[],
            modified=[],
            dropped=[],
            unchanged=list(old_by_id.values()),
        )

    # Determine whether missing items in the same scope can be marked dropped
    has_scoped_items = any(item.get("source_scope") or item.get("source_ref") for item in old_items)
    has_multi_source_context = bool(
        has_scoped_items
        or existing_fm.get("contributing_sources")
        or source_scope is not None
        or source_ref is not None
        or any(isinstance(d, dict) and (d.get("source_scope") or d.get("source_ref")) for d in items_to_compare)
    )
    if authoritative_replacement is not None:
        is_authoritative = bool(authoritative_replacement)
    elif mode is not None:
        is_authoritative = (mode == "authoritative_replacement")
    else:
        is_authoritative = not has_multi_source_context

    added: List[Dict[str, Any]] = []
    modified: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    unchanged: List[Dict[str, Any]] = []

    new_ids: Set[str] = set()
    for raw_new in items_to_compare:
        new_item = dict(raw_new)
        nid = str(new_item.get("id") or "").strip()
        if not nid and new_item.get("title"):
            nid = _slugify_deliverable_id(str(new_item["title"]))
            new_item["id"] = nid
        if not nid:
            continue
        if nid in new_ids:
            # Ensure distinct assignments with different titles aren't collided
            alt_id = _slugify_deliverable_id(f"{nid}-{new_item.get('title', '')}-{new_item.get('due', '')}")
            if alt_id not in new_ids:
                nid = alt_id
                new_item["id"] = nid
        new_ids.add(nid)
        if source_ref and "source_ref" not in new_item:
            new_item["source_ref"] = source_ref
        if source_scope and "source_scope" not in new_item:
            new_item["source_scope"] = source_scope

        if nid not in old_by_id:
            if "status" not in new_item:
                new_item["status"] = "todo"
            added.append(new_item)
        else:
            old_item = old_by_id[nid]
            old_status = str(old_item.get("status") or "todo")
            due_changed = "due" in new_item and str(new_item["due"]) != str(old_item.get("due"))
            both_have_due = bool(new_item.get("due") and old_item.get("due") and str(new_item["due"]) != str(old_item["due"]))

            # Preserve done/archived status and user_modified items, flagging any contradictory dates
            if old_status in {"done", "archived"} or old_item.get("user_modified") is True:
                preserved = dict(old_item)
                if both_have_due:
                    preserved["conflict_flag"] = True
                    src_label = new_item.get("source_ref") or new_item.get("source_scope") or source_ref or source_scope or "incoming source"
                    note = f"Conflicting deadline '{new_item.get('due')}' from {src_label} vs preserved '{old_item.get('due')}'"
                    preserved["conflict_notes"] = f"{preserved.get('conflict_notes')}; {note}" if preserved.get("conflict_notes") else note
                unchanged.append(preserved)
                continue

            title_changed = "title" in new_item and str(new_item["title"]) != str(old_item.get("title"))
            uncertain_changed = "date_uncertain" in new_item and bool(new_item["date_uncertain"]) != bool(old_item.get("date_uncertain"))
            tier_changed = "tier" in new_item and new_item["tier"] != old_item.get("tier")
            due_time_changed = "due_time" in new_item and new_item.get("due_time") != old_item.get("due_time")
            new_status_raw = str(new_item.get("status") or "").strip() if "status" in new_item else ""
            status_changed = bool(
                new_status_raw
                and new_status_raw != old_status
                and not (old_status == "in-progress" and new_status_raw == "todo")
            )

            if due_changed or title_changed or uncertain_changed or tier_changed or due_time_changed or status_changed:
                merged = dict(old_item)
                saved_task_ref = old_item.get("task_ref")
                saved_cal_id = old_item.get("googleCalendarEventId")
                if old_status in {"done", "archived"} or (old_status == "in-progress" and new_status_raw in {"", "todo"}):
                    saved_status = old_status
                else:
                    saved_status = new_item.get("status", old_status)
                different_source = bool(
                    (old_item.get("source_ref") and new_item.get("source_ref") and old_item.get("source_ref") != new_item.get("source_ref"))
                    or (old_item.get("source_scope") and new_item.get("source_scope") and old_item.get("source_scope") != new_item.get("source_scope"))
                )
                merged.update(new_item)
                if saved_task_ref and not new_item.get("task_ref"):
                    merged["task_ref"] = saved_task_ref
                if saved_cal_id and not new_item.get("googleCalendarEventId"):
                    merged["googleCalendarEventId"] = saved_cal_id
                merged["status"] = saved_status
                if both_have_due and (not is_authoritative or different_source):
                    merged["conflict_flag"] = True
                    src_old = old_item.get("source_ref") or old_item.get("source_scope") or "existing roadmap"
                    src_new = new_item.get("source_ref") or new_item.get("source_scope") or "supplementary source"
                    note = f"Contradictory deadline between {src_old} ({old_item.get('due')}) and {src_new} ({new_item.get('due')})"
                    merged["conflict_notes"] = f"{merged.get('conflict_notes')}; {note}" if merged.get("conflict_notes") else note
                modified.append(merged)
            else:
                unchanged.append(old_item)

    for oid, old_item in old_by_id.items():
        if oid not in new_ids:
            old_status = str(old_item.get("status") or "todo")
            old_scope = old_item.get("source_scope")
            old_src_ref = old_item.get("source_ref")
            if source_scope is not None:
                same_scope = (old_scope == source_scope)
            elif source_ref is not None:
                same_scope = (old_src_ref == source_ref)
            elif has_scoped_items:
                same_scope = False
            else:
                same_scope = True

            if is_authoritative and same_scope and old_status not in {"done", "archived"} and not old_item.get("user_modified"):
                dropped_item = dict(old_item)
                dropped_item["status"] = "archived"
                dropped.append(dropped_item)
            else:
                unchanged.append(old_item)

    return SyllabusDiff(
        project_id=project_id,
        added=added,
        modified=modified,
        dropped=dropped,
        unchanged=unchanged
    )


def reconcile_project_deliverables(
    existing_roadmap_path: Union[Path, str],
    new_deliverables: List[Dict[str, Any]],
    *,
    authoritative_replacement: bool = False,
    source_scope: Optional[str] = None,
    source_ref: Optional[str] = None,
    extraction_status: str = "complete",
) -> SyllabusDiff:
    """
    Explicitly additive-by-default multi-source project reconciliation helper.
    Only marks missing deliverables as dropped when authoritative_replacement=True AND source_scope matches.
    """
    return reconcile_syllabus(
        existing_roadmap_path,
        new_deliverables,
        mode="authoritative_replacement" if authoritative_replacement else "supplementary",
        authoritative_replacement=authoritative_replacement,
        source_scope=source_scope,
        source_ref=source_ref,
        extraction_status=extraction_status,
    )


# =========================================================================
# 8. JSON Schema Draft 2020-12 Validation Engine
# =========================================================================

_VALIDATOR_CACHE: Dict[Tuple[str, str], Any] = {}
_FORMAT_CHECKER = FormatChecker() if FormatChecker else None


if _FORMAT_CHECKER:
    @_FORMAT_CHECKER.checks("tasknotes-date-time")
    def _check_tasknotes_stamp(val):
        if not isinstance(val, str):
            return False
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).tzinfo is not None
        except ValueError:
            return False

    @_FORMAT_CHECKER.checks("date")
    def _check_date_format(val: Any) -> bool:
        """Validates strict YYYY-MM-DD calendar dates."""
        if not isinstance(val, str):
            return True
        if not DATE_ONLY_PATTERN.match(val):
            return False
        try:
            datetime.strptime(val, "%Y-%m-%d")
            return True
        except ValueError:
            return False


    @_FORMAT_CHECKER.checks("date-time")
    def _check_date_time_format(val: Any) -> bool:
        """
        Validates RFC 3339 timestamps with explicit local timezone offsets.
        Enforces Chrysalis Local Timezone Invariant: rejects raw UTC 'Z' and naive timestamps.
        """
        if not isinstance(val, str):
            return True
        if RAW_UTC_PATTERN.match(val):
            return False
        if not TIMEZONE_OFFSET_PATTERN.match(val):
            return False
        try:
            datetime.fromisoformat(val)
            return True
        except ValueError:
            return False


def _find_type_schema_file(type_name: str, collection_dir: Optional[Union[Path, str]] = None, record_path: Optional[Path] = None) -> Optional[Path]:
    """Resolves physical path to _types/{type_name}.md across repository configurations."""
    candidates: List[Path] = []
    if collection_dir:
        selected = Path(collection_dir) / "_types" / f"{type_name}.md"
        return selected if selected.is_file() else None

    # Relative to this helper module
    repo_root = Path(__file__).resolve().parents[1]
    candidates.append(repo_root / "_types" / f"{type_name}.md")

    # Relative to current working directory
    candidates.append(Path.cwd() / "_types" / f"{type_name}.md")

    # Walk up from target record path
    if record_path:
        curr = record_path.resolve().parent
        for _ in range(5):
            candidate = curr / "_types" / f"{type_name}.md"
            candidates.append(candidate)
            if curr.parent == curr:
                break
            curr = curr.parent

    for c in candidates:
        if c.is_file():
            return c
    return None


def _get_validator_for_type(type_name: str, collection_dir: Optional[Union[Path, str]] = None, record_path: Optional[Path] = None) -> Optional[Draft202012Validator]:
    """Retrieves or compiles a Draft202012Validator instance with FormatChecker for the given type."""
    if not HAS_JSONSCHEMA or Draft202012Validator is None:
        return None
    schema_path = _find_type_schema_file(type_name, collection_dir=collection_dir, record_path=record_path)
    if not schema_path:
        return None

    try:
        schema_bytes = schema_path.read_bytes()
    except OSError:
        return None

    cache_key = (str(schema_path.resolve()), compute_revision(schema_bytes))
    if cache_key in _VALIDATOR_CACHE:
        return _VALIDATOR_CACHE[cache_key]

    try:
        content = schema_bytes.decode("utf-8")
        fm, _ = parse_frontmatter(content)
        schema_val = fm.get("schema", {}).get("value")
        if not isinstance(schema_val, dict):
            return None
        Draft202012Validator.check_schema(schema_val)
        validator = Draft202012Validator(schema_val, format_checker=_FORMAT_CHECKER)
        _VALIDATOR_CACHE[cache_key] = validator
        return validator
    except Exception:
        return None


def format_field_path(path_tokens: Sequence[Union[str, int]], leaf: Optional[str] = None) -> Optional[str]:
    """Formats path deque/list into dot and bracket string notation (e.g. deliverables[0].id)."""
    full = list(path_tokens)
    if leaf is not None:
        full.append(leaf)
    if not full:
        return None
    res = ""
    for item in full:
        if isinstance(item, int):
            res += f"[{item}]"
        else:
            if res:
                res += f".{item}"
            else:
                res = str(item)
    return res


def validator_to_diagnostic_code(validator_name: str) -> str:
    """Translates camelCase JSON Schema validator keyword to canonical snake_case schema_<keyword>."""
    if not validator_name:
        return "schema_violation"
    snake = re.sub(r"(?<!^)(?=[A-Z])", "_", validator_name).lower()
    return f"schema_{snake}"


def _normalize_frontmatter_dates(val: Any) -> Any:
    """Recursively converts datetime and date instances to ISO 8601 string representations."""
    if isinstance(val, dict):
        return {k: _normalize_frontmatter_dates(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [_normalize_frontmatter_dates(v) for v in val]
    elif isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def validate_record(
    path: Union[Path, str],
    record_text: Optional[Union[str, Path]] = None,
    type_name: Optional[str] = None,
    collection_dir: Optional[Union[Path, str]] = None
) -> ValidationResult:
    """
    Validates a markdown record's frontmatter against its local record type definition.
    Enforces authoritative JSON Schema Draft 2020-12 validation via jsonschema.Draft202012Validator,
    mapping validation errors to canonical schema_<keyword> diagnostic codes.
    Preserves Chrysalis Local Timezone format checks (rejecting UTC 'Z' strings).
    """
    path_obj = Path(path)
    if not HAS_JSONSCHEMA or Draft202012Validator is None:
        return ValidationResult(valid=False, diagnostics=[Diagnostic(
            code="validation_unavailable", severity="error",
            message="Strict schema validation requires jsonschema; writes are disabled.",
            path=str(path_obj), recovery_action="InstallDependency",
        )])
    if record_text is None:
        record_text = native_path(path_obj).read_text(encoding="utf-8")
    elif isinstance(record_text, Path) or (isinstance(record_text, str) and not record_text.startswith("---") and Path(record_text).is_dir()):
        if collection_dir is None:
            collection_dir = Path(record_text)
        record_text = native_path(path_obj).read_text(encoding="utf-8")
    diagnostics: List[Diagnostic] = []

    try:
        fm, body = parse_frontmatter(record_text)
    except Exception as e:
        return ValidationResult(
            valid=False,
            diagnostics=[Diagnostic(
                code="schema_syntax_error",
                severity="error",
                message=f"Syntax error parsing YAML frontmatter: {e}",
                path=str(path_obj),
                recovery_action="FixRequest"
            )]
        )

    # Infer type if not explicitly provided
    resolved_type = type_name or fm.get("type")
    if resolved_type == "project_roadmap":
        resolved_type = "project"
    elif resolved_type in {"strategic_roadmap", "system_health", "system_health_report", "system_specification", "system_memory_extension"}:
        resolved_type = "system_state"

    if not resolved_type:
        p_str = str(path_obj).replace("\\", "/")
        if "TaskNotes/Tasks" in p_str or "Tasks/" in p_str:
            resolved_type = "task"
        elif "Projects" in p_str and path_obj.name == "Roadmap.md":
            resolved_type = "project"
        elif "Slipbox/" in p_str or p_str.startswith("Slipbox/"):
            resolved_type = "zettel"
        elif "Sources/" in p_str or p_str.startswith("Sources/"):
            resolved_type = "source"
        elif ("System/" in p_str or p_str.startswith("System/")) and "System/Workflows" not in p_str and "System/Environment" not in p_str:
            resolved_type = "system_state"

    valid_types = {"task", "project", "zettel", "source", "system_state", "daily_note"}
    if not resolved_type or resolved_type not in valid_types:
        diagnostics.append(Diagnostic(
            code="type_unknown",
            severity="error",
            message=f"Unable to determine valid local record type for {path_obj}",
            path=str(path_obj),
            recovery_action="FixRequest"
        ))
        return ValidationResult(valid=False, diagnostics=diagnostics, frontmatter=fm, body=body)

    # Pre-check: Chrysalis Local Timezone Invariant (reject raw UTC 'Z' timestamps)
    for k, v in fm.items():
        if k in {"dateCreated", "created", "scheduled", "due", "last_updated", "captured_date", "startedAt", "completedAt"} and isinstance(v, str) and RAW_UTC_PATTERN.match(v):
            diagnostics.append(Diagnostic(
                code="format_invalid",
                severity="error",
                message=f"Field '{k}' contains raw UTC 'Z' string '{v}'. Explicit local offset required (e.g. -05:00).",
                field=k,
                path=str(path_obj),
                recovery_action="FixRequest"
            ))

    # Semantic validation for task location, coordinates, route_estimate, and travel_policy
    if resolved_type == "task":
        try:
            from helpers.location_routing import validate_task_location_and_travel_fields
            loc_val = validate_task_location_and_travel_fields(fm)
            loc_diags = loc_val if isinstance(loc_val, list) else loc_val.get("diagnostics", [])
            for d_item in loc_diags:
                diagnostics.append(Diagnostic(
                    code=str(d_item.get("code") or "schema_semantic_violation"),
                    severity=str(d_item.get("severity") or "error"),
                    message=str(d_item.get("message") or "Invalid task location or travel field."),
                    field=d_item.get("field"),
                    path=str(path_obj),
                    recovery_action="FixRequest",
                ))
        except Exception as e:
            diagnostics.append(Diagnostic(
                code="schema_semantic_violation",
                severity="error",
                message=f"Error validating task location/travel fields: {e}",
                path=str(path_obj),
                recovery_action="FixRequest",
            ))

    # Semantic validation for source records: forbid synthetic or empty-string sha256
    if resolved_type == "source":
        bytes_avail = fm.get("bytes_available")
        sha_val = fm.get("sha256")
        fsize = fm.get("file_size_bytes")
        if bytes_avail is False and sha_val is not None:
            diagnostics.append(Diagnostic(
                code="schema_semantic_violation",
                severity="error",
                message="Field 'sha256' must be null when 'bytes_available' is false (synthetic or metadata-derived sha256 is forbidden).",
                field="sha256",
                path=str(path_obj),
                recovery_action="FixRequest"
            ))
        if sha_val is not None and str(sha_val).strip().lower() == EMPTY_BYTES_SHA256 and isinstance(fsize, int) and fsize > 0:
            diagnostics.append(Diagnostic(
                code="schema_semantic_violation",
                severity="error",
                message="Field 'sha256' cannot be the empty-bytes SHA-256 digest when 'file_size_bytes' > 0.",
                field="sha256",
                path=str(path_obj),
                recovery_action="FixRequest"
            ))

    # Retrieve compiled JSON Schema Draft 2020-12 validator
    validator = _get_validator_for_type(resolved_type, collection_dir=collection_dir, record_path=path_obj)
    if validator is None:
        diagnostics.append(Diagnostic(
            code="schema_not_found",
            severity="error",
            message=f"Authoritative schema for type '{resolved_type}' could not be located or loaded.",
            path=str(path_obj),
            recovery_action="RepairCollection"
        ))
        return ValidationResult(valid=False, diagnostics=diagnostics, frontmatter=fm, body=body)

    # Normalize unquoted YAML dates to ISO strings for schema evaluation
    normalized_fm = _normalize_frontmatter_dates(fm)

    # Execute full JSON Schema Draft 2020-12 validation
    for err in validator.iter_errors(normalized_fm):
        code = validator_to_diagnostic_code(err.validator)
        leaf: Optional[str] = None

        if err.validator == "required":
            m = re.search(r"'([^']+)' is a required property", err.message)
            if m:
                leaf = m.group(1)
        elif err.validator == "additionalProperties":
            extra_props = re.findall(r"'([^']+)'", err.message)
            leaf = extra_props[0] if extra_props else None

        field_path = format_field_path(err.path, leaf=leaf)
        diagnostics.append(Diagnostic(
            code=code,
            severity="error",
            message=err.message,
            field=field_path,
            path=str(path_obj),
            recovery_action="FixRequest"
        ))

    is_valid = len([d for d in diagnostics if d.severity == "error"]) == 0
    return ValidationResult(
        valid=is_valid,
        diagnostics=diagnostics,
        frontmatter=fm,
        body=body
    )


# =========================================================================
# 9. Ingestion Lifecycle Pipeline: Prevalidate -> Approve -> Apply -> Verify
# =========================================================================

VALID_INGESTION_OUTCOMES = {
    "extracted",
    "metadata_only",
    "reference_indexed",
    "supporting_asset_deferred",
    "unsupported_deferred",
    "skipped_duplicate",
    "duplicate_skipped",
    "duplicate_unchanged",
    "revised_source",
    "updated_existing",
    "incomplete",
    "unreadable",
    "extraction_failed",
    "failed",
}


def _render_record_markdown(record_spec: Dict[str, Any]) -> str:
    """Renders a drafted record specification (either raw 'content' or 'frontmatter' + 'body') to UTF-8 Markdown."""
    if "content" in record_spec and isinstance(record_spec["content"], str):
        return record_spec["content"]
    fm = record_spec.get("frontmatter") or {}
    body = record_spec.get("body") or ""
    serialized_fm = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
    return f"---\n{serialized_fm}\n---\n\n{body.strip()}\n"


def _load_registered_pillars(vault_root: Path) -> Set[str]:
    """Loads registered pillar tags from System/Life-Roadmap.md if present."""
    roadmap_file = vault_root / "System" / "Life-Roadmap.md"
    registered: Set[str] = set()
    if not roadmap_file.is_file():
        return registered
    try:
        fm, _ = parse_frontmatter(roadmap_file.read_text(encoding="utf-8"))
        tag_reg = fm.get("tag_registry")
        if isinstance(tag_reg, dict):
            for p_key, subtags in tag_reg.items():
                if isinstance(p_key, str) and p_key.strip():
                    registered.add(p_key.strip())
                if isinstance(subtags, list):
                    for st in subtags:
                        if isinstance(st, str) and st.strip():
                            registered.add(st.strip())
                elif isinstance(subtags, str) and subtags.strip():
                    registered.add(subtags.strip())
        elif isinstance(tag_reg, list):
            for entry in tag_reg:
                if isinstance(entry, dict) and entry.get("tag"):
                    registered.add(str(entry["tag"]).strip())
                elif isinstance(entry, str) and entry.strip():
                    registered.add(entry.strip())
        for p in fm.get("pillars") or []:
            if isinstance(p, dict):
                if p.get("id"):
                    registered.add(str(p["id"]).strip())
                for st in p.get("subtags") or []:
                    if isinstance(st, str) and st.strip():
                        registered.add(st.strip())
    except Exception:
        pass
    return registered


def prevalidate_ingestion_proposal(
    vault_root: Union[Path, str],
    proposal: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Prevalidates an ingestion batch proposal before human approval is requested.
    Checks:
    1. Target paths are inside vault_root and conform to collection directories.
    2. Every drafted record passes JSON Schema Draft 2020-12 & semantic validation.
    3. CAS revision integrity: new records (if_revision=None) cannot overwrite differing existing files
       (record_collision), and updated records with stale if_revision fail (concurrent_modification).
    4. Ingestion tasks never auto-schedule onto the calendar (scheduled must be None).
    5. Pillar tags on projects and tasks exist in Life-Roadmap.md (or proposed_pillar_tags in proposal).
    6. All cross-references ([[Sources/...]], [[Projects/.../Roadmap]], [[Slipbox/...]], [[TaskNotes/Tasks/...]])
       resolve either to existing vault files or to records in this proposal.
    """
    v_root = Path(vault_root).resolve()
    proposal_id = str(proposal.get("proposal_id") or f"ingest-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    records: List[Dict[str, Any]] = list(proposal.get("records") or [])
    outcomes: List[Dict[str, Any]] = list(proposal.get("outcomes") or [])
    diagnostics: List[Dict[str, Any]] = []

    registered_pillars = _load_registered_pillars(v_root)
    for extra_tag in proposal.get("proposed_pillar_tags") or []:
        registered_pillars.add(str(extra_tag).strip())

    # Collect all planned relative paths and stems for cross-reference resolution
    planned_paths: Set[str] = set()
    planned_stems: Set[str] = set()
    for r in records:
        rel_p = str(r.get("path") or "").replace("\\", "/").lstrip("/")
        if rel_p:
            planned_paths.add(rel_p)
            if Path(rel_p).stem.lower() not in {"roadmap", "readme", "index"}:
                planned_stems.add(Path(rel_p).stem)

    def _ref_resolves(wikilink: str) -> bool:
        cleaned = str(wikilink).strip()
        if cleaned.startswith("[[") and cleaned.endswith("]]"):
            cleaned = cleaned[2:-2].strip()
        if "|" in cleaned:
            cleaned = cleaned.split("|", 1)[0].strip()
        if not cleaned:
            return True
        norm = cleaned if cleaned.endswith(".md") else f"{cleaned}.md"
        if norm in planned_paths:
            return True
        if "/" not in cleaned and Path(norm).stem in planned_stems:
            return True
        for prefix in ("", "Sources/", "Slipbox/", "TaskNotes/Tasks/", "Projects/"):
            cand_rel = f"{prefix}{norm}".replace("//", "/")
            if cand_rel in planned_paths:
                return True
        resolved_disk = _resolve_wikilink_target(wikilink, v_root)
        return resolved_disk is not None and resolved_disk.is_file()

    for idx, rec in enumerate(records):
        rel_path = str(rec.get("path") or "").replace("\\", "/").lstrip("/")
        if not rel_path or ".." in Path(rel_path).parts:
            diagnostics.append({
                "code": "invalid_target_path",
                "severity": "error",
                "path": rel_path,
                "message": f"Record [{idx}] has invalid or escaping vault-relative path: '{rel_path}'",
            })
            continue

        abs_target = (v_root / rel_path).resolve()
        if not abs_target.is_relative_to(v_root):
            diagnostics.append({
                "code": "path_traversal_forbidden",
                "severity": "error",
                "path": rel_path,
                "message": f"Record [{idx}] escapes vault root: '{rel_path}'",
            })
            continue

        md_text = _render_record_markdown(rec)
        expected_new_rev = compute_revision(md_text)
        if_rev = rec.get("if_revision")

        if abs_target.is_file():
            actual_rev = compute_revision(abs_target)
            raw_disk_text = abs_target.read_text(encoding="utf-8", errors="replace")
            fm_raw = (
                raw_disk_text.split("---", 2)[1]
                if raw_disk_text.startswith("---") and raw_disk_text.count("---") >= 2
                else ""
            )
            fm_rev = compute_revision(fm_raw) if fm_raw else ""
            if actual_rev.lower() != expected_new_rev.lower():
                if if_rev is None:
                    diagnostics.append({
                        "code": "record_collision",
                        "severity": "error",
                        "path": rel_path,
                        "field": "if_revision",
                        "message": (
                            f"New record collision at '{rel_path}': target file already exists on disk "
                            f"(revision {actual_rev[:12]}...) and no 'if_revision' was provided."
                        ),
                    })
                else:
                    if str(if_rev).strip().lower() != actual_rev.lower():
                        diagnostics.append({
                            "code": "concurrent_modification",
                            "severity": "error",
                            "path": rel_path,
                            "field": "if_revision",
                            "message": (
                                f"Stale revision for '{rel_path}': expected '{if_rev}', "
                                f"found '{actual_rev}' on disk."
                            ),
                        })
        else:
            if if_rev is not None:
                diagnostics.append({
                    "code": "concurrent_modification",
                    "severity": "error",
                    "path": rel_path,
                    "field": "if_revision",
                    "message": (
                        f"Expected existing revision '{if_rev}' for '{rel_path}', "
                        f"but target file does not exist on disk."
                    ),
                })

        rtype = rec.get("type")
        val_res = validate_record(abs_target, md_text, type_name=rtype, collection_dir=v_root)
        for d in val_res.diagnostics:
            diagnostics.append(d.to_dict())

        fm = val_res.frontmatter or {}
        inferred_type = rtype or fm.get("type")
        if inferred_type == "project_roadmap":
            inferred_type = "project"

        # Task-specific prevalidation: never auto-schedule during /ingest, check pillar tags & refs
        if inferred_type == "task" or rel_path.startswith("TaskNotes/Tasks/"):
            existing_disk_scheduled = None
            if abs_target.is_file() and if_rev is not None:
                try:
                    existing_disk_fm, _ = parse_frontmatter(abs_target.read_text(encoding="utf-8"))
                    existing_disk_scheduled = existing_disk_fm.get("scheduled")
                except Exception:
                    existing_disk_scheduled = None
            if fm.get("scheduled") is not None and fm.get("scheduled") != existing_disk_scheduled:
                diagnostics.append({
                    "code": "ingestion_auto_schedule_forbidden",
                    "severity": "error",
                    "path": rel_path,
                    "field": "scheduled",
                    "message": "Ingestion must never auto-schedule tasks; 'scheduled' must be null until /plan.",
                })
            if registered_pillars:
                tags = [str(t) for t in (fm.get("tags") or []) if str(t) != "task"]
                is_standalone_external_capture = bool(
                    fm.get("external_item_id") and not any(t.startswith("pillar-") for t in tags)
                )
                if not is_standalone_external_capture and not any(t in registered_pillars for t in tags):
                    diagnostics.append({
                        "code": "unregistered_pillar_tag",
                        "severity": "error",
                        "path": rel_path,
                        "field": "tags",
                        "message": f"Task tags {tags} do not match any registered pillar tag in Life-Roadmap.md.",
                    })
            if fm.get("project_ref") and not _ref_resolves(str(fm["project_ref"])):
                diagnostics.append({
                    "code": "broken_cross_reference",
                    "severity": "error",
                    "path": rel_path,
                    "field": "project_ref",
                    "message": f"Task project_ref '{fm['project_ref']}' does not resolve to an existing or proposed Roadmap.md.",
                })
            if fm.get("source_ref") and not _ref_resolves(str(fm["source_ref"])):
                diagnostics.append({
                    "code": "broken_cross_reference",
                    "severity": "error",
                    "path": rel_path,
                    "field": "source_ref",
                    "message": f"Task source_ref '{fm['source_ref']}' does not resolve to an existing or proposed source.",
                })
            for lz in fm.get("linked_zettels") or []:
                if not _ref_resolves(str(lz)):
                    diagnostics.append({
                        "code": "broken_cross_reference",
                        "severity": "error",
                        "path": rel_path,
                        "field": "linked_zettels",
                        "message": f"Task linked_zettel '{lz}' does not resolve.",
                    })

        # Project-specific prevalidation
        elif inferred_type == "project" or (rel_path.startswith("Projects/") and rel_path.endswith("/Roadmap.md")):
            if registered_pillars and fm.get("pillar") and str(fm["pillar"]) not in registered_pillars:
                diagnostics.append({
                    "code": "unregistered_pillar_tag",
                    "severity": "error",
                    "path": rel_path,
                    "field": "pillar",
                    "message": f"Project pillar '{fm.get('pillar')}' is not registered in Life-Roadmap.md.",
                })
            if fm.get("source_ref") and not _ref_resolves(str(fm["source_ref"])):
                diagnostics.append({
                    "code": "broken_cross_reference",
                    "severity": "error",
                    "path": rel_path,
                    "field": "source_ref",
                    "message": f"Project source_ref '{fm['source_ref']}' does not resolve.",
                })
            for field_name in ("contributing_sources", "reference_sources", "linked_zettels"):
                for ref in fm.get(field_name) or []:
                    ref_str = ref.get("source_ref") if isinstance(ref, dict) else str(ref)
                    if ref_str and not _ref_resolves(str(ref_str)):
                        diagnostics.append({
                            "code": "broken_cross_reference",
                            "severity": "error",
                            "path": rel_path,
                            "field": field_name,
                            "message": f"Project {field_name} reference '{ref_str}' does not resolve.",
                        })
            for d_item in fm.get("deliverables") or []:
                if isinstance(d_item, dict):
                    if d_item.get("task_ref") and not _ref_resolves(str(d_item["task_ref"])):
                        diagnostics.append({
                            "code": "broken_cross_reference",
                            "severity": "error",
                            "path": rel_path,
                            "field": "deliverables.task_ref",
                            "message": f"Deliverable '{d_item.get('id')}' task_ref '{d_item.get('task_ref')}' does not resolve.",
                        })
                    if d_item.get("source_ref") and not _ref_resolves(str(d_item["source_ref"])):
                        diagnostics.append({
                            "code": "broken_cross_reference",
                            "severity": "error",
                            "path": rel_path,
                            "field": "deliverables.source_ref",
                            "message": f"Deliverable '{d_item.get('id')}' source_ref '{d_item.get('source_ref')}' does not resolve.",
                        })

        # Source-specific prevalidation
        elif inferred_type == "source" or rel_path.startswith("Sources/"):
            for field_name in ("linked_projects", "extracted_projects", "extracted_tasks", "linked_zettels", "extracted_zettels"):
                for ref in fm.get(field_name) or []:
                    if not _ref_resolves(str(ref)):
                        diagnostics.append({
                            "code": "broken_cross_reference",
                            "severity": "error",
                            "path": rel_path,
                            "field": field_name,
                            "message": f"Source {field_name} reference '{ref}' does not resolve to an existing or proposed record.",
                        })

        # Zettel-specific prevalidation
        elif inferred_type == "zettel" or rel_path.startswith("Slipbox/"):
            if fm.get("source_ref") and not _ref_resolves(str(fm["source_ref"])):
                diagnostics.append({
                    "code": "broken_cross_reference",
                    "severity": "error",
                    "path": rel_path,
                    "field": "source_ref",
                    "message": f"Zettel source_ref '{fm['source_ref']}' does not resolve.",
                })
            if fm.get("project_ref") and not _ref_resolves(str(fm["project_ref"])):
                diagnostics.append({
                    "code": "broken_cross_reference",
                    "severity": "error",
                    "path": rel_path,
                    "field": "project_ref",
                    "message": f"Zettel project_ref '{fm['project_ref']}' does not resolve.",
                })
            for field_name in ("linked_zettels", "related_zettels"):
                for ref in fm.get(field_name) or []:
                    if not _ref_resolves(str(ref)):
                        diagnostics.append({
                            "code": "broken_cross_reference",
                            "severity": "error",
                            "path": rel_path,
                            "field": field_name,
                            "message": f"Zettel {field_name} reference '{ref}' does not resolve.",
                        })

    outcome_counts: Dict[str, int] = {k: 0 for k in sorted(VALID_INGESTION_OUTCOMES)}
    for o in outcomes:
        oc = str(o.get("outcome") or "extracted")
        if oc not in VALID_INGESTION_OUTCOMES:
            diagnostics.append({
                "code": "invalid_ingestion_outcome",
                "severity": "error",
                "message": f"Invalid ingestion outcome '{oc}' for item '{o.get('input_path')}'.",
            })
        else:
            outcome_counts[oc] = outcome_counts.get(oc, 0) + 1

    error_diags = [d for d in diagnostics if d.get("severity") == "error"]
    return {
        "valid": len(error_diags) == 0,
        "proposal_id": proposal_id,
        "vault": str(v_root),
        "records_count": len(records),
        "outcome_counts": outcome_counts,
        "diagnostics": diagnostics,
    }
