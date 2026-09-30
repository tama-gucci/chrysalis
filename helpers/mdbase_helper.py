"""
Chrysalis mdbase v0.3 Helper Module (helpers/mdbase_helper.py)
Deterministic validation, ADR 0006 CAS operations, deduplication, and syllabus diffing.
Conforms strictly to Python 3.10+ standard library and PyYAML.
"""

import contextlib
from dataclasses import dataclass, field
from datetime import date, datetime
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
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union
import uuid
import yaml

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

    @property
    def success(self) -> bool:
        """Alias for valid to satisfy callers checking res.success."""
        return self.valid

    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "revision": self.revision,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


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
        raw = document_bytes.read_bytes()
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
def _advisory_file_lock(path: Path):
    """
    Acquires an exclusive advisory lock via in-process threading.Lock plus
    fcntl.flock (POSIX) or msvcrt.locking (Windows) on a dedicated sibling
    lockfile (path.with_suffix(path.suffix + ".lock")).
    
    Guarantees cross-thread and cross-process mutual exclusion.
    Lockfile is never unlinked to prevent inode-reallocation race conditions.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_key = str(lock_path.resolve())
    with _LOCKS_GUARD:
        thread_lock = _PATH_LOCKS.setdefault(lock_key, threading.Lock())

    with thread_lock:
        lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o666)
        try:
            if fcntl is not None:
                fcntl.flock(lock_fd, fcntl.LOCK_EX)
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


def apply_cas_mutation(
    file_path: Union[Path, str],
    new_document: str,
    if_revision: Optional[str] = None
) -> CASResult:
    """
    Applies conditional atomic mutation using Compare-And-Swap (ADR 0006).
    Ensures zero disk bytes are modified if if_revision does not match.
    Guarantees mutual exclusion against TOCTOU race conditions via advisory
    file locking (fcntl.flock). Writes atomically via sibling temp file and os.replace.
    """
    path = Path(file_path)
    new_bytes = new_document.encode("utf-8")

    try:
        with _advisory_file_lock(path):
            if path.exists():
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

            # Atomic write guarantee via sibling temp file
            temp_path = path.with_suffix(f".tmp.{uuid.uuid4().hex}")
            try:
                with open(temp_path, "wb") as f:
                    f.write(new_bytes)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(temp_path, path)
            finally:
                if temp_path.exists():
                    temp_path.unlink(missing_ok=True)

            new_revision = compute_revision(new_bytes)
            return CASResult(valid=True, revision=new_revision)
    except OSError as e:
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


def update_source_provenance_on_move(
    source_record_path: Union[Path, str],
    new_filename: str,
    new_relative_path: Optional[str] = None,
) -> CASResult:
    """
    Updates original_filename and relative_path on an existing Sources/*.md record when a file
    is renamed or moved in the locker (matched by exact binary sha256), preserving prior paths
    in previous_paths and never inventing a Google Drive URL.
    """
    p = Path(source_record_path)
    raw = p.read_text(encoding="utf-8")
    current_rev = compute_revision(p)
    fm, body = parse_frontmatter(raw)
    prev_paths = list(fm.get("previous_paths") or [])
    old_rel = fm.get("relative_path") or fm.get("original_filename")
    if old_rel and str(old_rel) not in prev_paths and str(old_rel) != (new_relative_path or new_filename):
        prev_paths.append(str(old_rel))
    fm["original_filename"] = new_filename
    if new_relative_path is not None:
        fm["relative_path"] = new_relative_path.replace("\\", "/")
    fm["previous_paths"] = prev_paths
    # Strictly preserve existing source_url without inventing a fake Drive URL
    if "source_url" not in fm:
        fm["source_url"] = None
    return apply_cas_mutation(p, serialize_record(fm, body), if_revision=current_rev)


def check_semantic_duplicate(
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


def extract_pdf_bounded(
    file_path: Union[Path, str],
    *,
    max_pages: int = 15,
) -> Dict[str, Any]:
    """
    Extracts bounded page-level text, accurate total page count, and section headings from a PDF
    using stdlib zlib FlateDecode stream decompression (and pypdf/fitz when available).
    """
    p = Path(file_path)
    raw_bytes = p.read_bytes()
    if not raw_bytes.startswith(b"%PDF-"):
        return {
            "valid_pdf": False,
            "total_pages": 0,
            "pages_processed": 0,
            "has_searchable_text": False,
            "has_embedded_images": False,
            "sections_indexed": [],
            "page_excerpts": [],
            "omissions": ["Invalid PDF header"],
            "uncertainty_flags": ["corrupt_or_non_pdf"],
        }

    # Decompress FlateDecode streams to inspect object streams (/ObjStm) and page content streams
    decompressed_streams: List[bytes] = []
    for m in re.finditer(rb"stream\r?\n(.*?)\r?\nendstream", raw_bytes, re.DOTALL):
        try:
            decompressed_streams.append(zlib.decompress(m.group(1)))
        except Exception:
            continue

    combined = raw_bytes + b"\n" + b"\n".join(decompressed_streams)
    counts: List[int] = []
    for d in re.findall(rb"<<(.*?)>>", combined, re.DOTALL):
        if re.search(rb"/Type\s*/Pages\b", d):
            cm = re.search(rb"/Count\s+(\d+)", d)
            if cm:
                counts.append(int(cm.group(1)))
    if counts:
        total_pages = max(counts)
    else:
        page_objs = re.findall(rb"/Type\s*/Page\b(?!s)", combined)
        total_pages = max(1, len(page_objs))

    has_image_xobjects = bool(re.search(rb"/Subtype\s*/Image\b", combined))

    # Extract readable text spans from decompressed streams
    text_fragments: List[str] = []
    for chunk in decompressed_streams or [raw_bytes]:
        if b"BT" in chunk and b"ET" in chunk:
            for literal in re.findall(rb"\(([^()\\]{2,200})\)", chunk):
                try:
                    decoded = literal.decode("latin-1", errors="ignore").strip()
                    if sum(c.isalnum() for c in decoded) >= 2:
                        text_fragments.append(decoded)
                except Exception:
                    continue

    has_searchable_text = len(text_fragments) >= 3 or bool(
        re.search(rb"/Font\b|BT\s", raw_bytes) and not decompressed_streams
    )
    pages_processed = min(total_pages, max_pages)
    sections_indexed: List[str] = []
    for frag in text_fragments[:200]:
        if re.match(r"^(?:Chapter|Section|Part|Project|Module|Unit)\s+\d+", frag, re.IGNORECASE):
            if frag not in sections_indexed:
                sections_indexed.append(frag)

    omissions: List[str] = []
    if total_pages > pages_processed:
        omissions.append(f"Pages {pages_processed + 1}..{total_pages} omitted by bounded reference window (max_pages={max_pages})")
    uncertainty_flags: List[str] = []
    if not has_searchable_text and has_image_xobjects:
        uncertainty_flags.append("scanned_or_image_only_pdf_requires_visual_ocr")

    return {
        "valid_pdf": True,
        "total_pages": total_pages,
        "pages_processed": pages_processed,
        "has_searchable_text": has_searchable_text,
        "has_embedded_images": has_image_xobjects,
        "sections_indexed": sections_indexed[:20],
        "page_excerpts": text_fragments[:25],
        "omissions": omissions,
        "uncertainty_flags": uncertainty_flags,
    }


def inspect_media_file(file_path: Union[Path, str], locker_root: Optional[Union[Path, str]] = None) -> Dict[str, Any]:
    """
    Inspects a media file's headers, extension, size, and folder context before claiming format support.
    Distinguishes searchable PDFs, scan/PNG visual OCR inputs, long reference PDFs, and unsupported
    binary supporting assets (such as AutoCAD .dwt files).
    """
    p = Path(file_path)
    rel_posix = p.name
    if locker_root:
        try:
            rel_posix = p.resolve().relative_to(Path(locker_root).resolve()).as_posix()
        except Exception:
            rel_posix = p.name

    parts = Path(rel_posix).parts
    # Contextual classification from folder hierarchy (contextual evidence, never unquestionable identity)
    location_category = "unclassified_inbox"
    material_role = "deliverable_instruction"
    course_hint: Optional[str] = None
    project_hint: Optional[str] = None
    auto_materialize_tasks = True
    auto_create_project = True

    lower_rel = rel_posix.lower()
    stem_lower = p.stem.lower()
    has_deliverable_tokens = any(
        tok in stem_lower for tok in ("project", "part ", "part-", "start the", "assignment", "lab", "rubric", "spec")
    )
    in_reference_subfolder = any(tok in lower_rel for tok in ("textbook", "reference", "chapters", "readings"))

    if parts and parts[0].lower().startswith("01-inbox"):
        location_category = "unclassified_inbox"
    elif parts and (parts[0].lower().startswith("02-projects") or parts[0].lower() == "projects"):
        if len(parts) >= 3:
            course_hint = parts[1]
        if len(parts) >= 4:
            project_hint = parts[2]
        elif len(parts) == 3:
            project_hint = parts[1]
        if in_reference_subfolder or (
            bool(re.match(r"^chapter\s+\d+(?:[\s\(\-]|$|\.)", p.stem, re.IGNORECASE))
            and not has_deliverable_tokens
        ):
            location_category = "shared_reference"
            material_role = "shared_reference"
            auto_materialize_tasks = False
            auto_create_project = False
        else:
            location_category = "project_library"
            material_role = "deliverable_instruction"

    folder_context = {
        "relative_path": rel_posix,
        "course_hint": course_hint,
        "project_hint": project_hint if location_category != "shared_reference" else None,
        "evidence_type": "contextual_folder_hierarchy",
        "proves_ingested": False,
    }

    try:
        raw_bytes = p.read_bytes()
    except OSError as e:
        return {
            "filename": p.name,
            "relative_path": rel_posix,
            "path": str(p),
            "readable": False,
            "supported": False,
            "format_kind": "unreadable",
            "location_category": location_category,
            "material_role": material_role,
            "ingestion_outcome": "unreadable",
            "error": str(e),
            "sha256": None,
            "size_bytes": 0,
            "folder_context": folder_context,
            "auto_materialize_tasks": False,
            "auto_create_project": False,
        }

    size_bytes = len(raw_bytes)
    sha256 = compute_revision(raw_bytes)
    ext = p.suffix.lower()
    is_generic_screenshot_name = bool(SCREENSHOT_FILENAME_PATTERN.match(p.stem))

    if ext == ".pdf":
        pdf_meta = extract_pdf_bounded(p)
        is_valid_pdf = pdf_meta["valid_pdf"]
        estimated_pages = pdf_meta["total_pages"]
        has_text_markers = pdf_meta["has_searchable_text"]
        has_image_xobjects = pdf_meta["has_embedded_images"]
        is_long_ref = (
            location_category == "shared_reference"
            or size_bytes >= 2_000_000
            or estimated_pages > 15
        )
        if not is_valid_pdf:
            format_kind = "corrupt_or_invalid_pdf"
            supported = False
            strategy = "unreadable_or_invalid"
            outcome = "unreadable"
        elif is_long_ref:
            format_kind = "pdf_long_reference"
            supported = True
            strategy = "section_indexed_bounded_pdf"
            outcome = "reference_indexed"
            material_role = "shared_reference"
            auto_materialize_tasks = False
            auto_create_project = False
        elif has_text_markers:
            format_kind = "pdf_searchable"
            supported = True
            strategy = "page_bounded_pdf_and_visual"
            outcome = "extracted"
        else:
            format_kind = "pdf_scanned_or_visual"
            supported = True
            strategy = "visual_ocr_with_uncertainty"
            outcome = "extracted"
        return {
            "filename": p.name,
            "relative_path": rel_posix,
            "path": str(p),
            "readable": is_valid_pdf,
            "supported": supported,
            "format_kind": format_kind,
            "extraction_strategy": strategy,
            "estimated_pages": estimated_pages,
            "extraction_coverage": {
                "pages_processed": pdf_meta["pages_processed"],
                "total_pages": estimated_pages,
                "sections_indexed": pdf_meta["sections_indexed"],
                "omissions": pdf_meta["omissions"],
                "uncertainty_flags": pdf_meta["uncertainty_flags"],
            },
            "has_searchable_text": has_text_markers,
            "has_embedded_images": has_image_xobjects,
            "is_long_reference": is_long_ref,
            "location_category": location_category,
            "material_role": material_role,
            "ingestion_outcome": outcome,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "folder_context": folder_context,
            "filename_is_generic_timestamp": is_generic_screenshot_name,
            "association_requires_review": bool(location_category == "unclassified_inbox" and is_generic_screenshot_name),
            "auto_materialize_tasks": auto_materialize_tasks,
            "auto_create_project": auto_create_project,
        }

    if ext in {".png", ".jpg", ".jpeg", ".webp"}:
        if is_generic_screenshot_name and location_category == "unclassified_inbox":
            location_category = "announcements_deadlines_rubrics"
            material_role = "announcement_deadline"
        width = height = None
        if ext == ".png" and len(raw_bytes) >= 24 and raw_bytes[:8] == b"\x89PNG\r\n\x1a\n":
            width = int.from_bytes(raw_bytes[16:20], "big")
            height = int.from_bytes(raw_bytes[20:24], "big")
        return {
            "filename": p.name,
            "relative_path": rel_posix,
            "path": str(p),
            "readable": True,
            "supported": True,
            "format_kind": "image_visual_ocr",
            "extraction_strategy": "visual_ocr_with_uncertainty",
            "dimensions": {"width": width, "height": height} if width and height else None,
            "location_category": location_category,
            "material_role": material_role,
            "ingestion_outcome": "extracted",
            "sha256": sha256,
            "size_bytes": size_bytes,
            "folder_context": folder_context,
            "filename_is_generic_timestamp": is_generic_screenshot_name,
            "association_requires_review": bool(project_hint is None and is_generic_screenshot_name),
            "auto_materialize_tasks": auto_materialize_tasks,
            "auto_create_project": False,
        }

    if ext in {".md", ".txt", ".csv", ".json", ".html"}:
        return {
            "filename": p.name,
            "relative_path": rel_posix,
            "path": str(p),
            "readable": True,
            "supported": True,
            "format_kind": "text_searchable",
            "extraction_strategy": "direct_text_parse",
            "location_category": location_category,
            "material_role": material_role,
            "ingestion_outcome": "extracted",
            "sha256": sha256,
            "size_bytes": size_bytes,
            "folder_context": folder_context,
            "filename_is_generic_timestamp": False,
            "association_requires_review": False,
            "auto_materialize_tasks": auto_materialize_tasks,
            "auto_create_project": auto_create_project,
        }

    # Unsupported binaries (.dwt, .dwg, .dwf, .rvt, .zip, etc.): preserve & identify as supporting assets
    header_sig = raw_bytes[:6].decode("ascii", errors="ignore") if len(raw_bytes) >= 6 else ""
    return {
        "filename": p.name,
        "relative_path": rel_posix,
        "path": str(p),
        "readable": True,
        "supported": False,
        "format_kind": "unsupported_binary_asset",
        "binary_signature": header_sig if header_sig.isprintable() else None,
        "extraction_strategy": "preserve_metadata_only_no_fabrication",
        "location_category": "supporting_asset" if location_category != "project_library" else "project_library",
        "material_role": "supporting_asset",
        "ingestion_outcome": "unsupported_deferred",
        "sha256": sha256,
        "size_bytes": size_bytes,
        "folder_context": folder_context,
        "filename_is_generic_timestamp": False,
        "association_requires_review": False,
        "auto_materialize_tasks": False,
        "auto_create_project": False,
    }


def discover_media_locker(
    vault_root: Union[Path, str],
    *,
    locker_root: Optional[Union[Path, str]] = None,
    inbox_path: Optional[Union[Path, str]] = None,
    discovery_roots: Optional[Sequence[str]] = None,
    max_depth: int = 6,
    allow_host_fallback: bool = False,
    integration: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Bounded, configurable recursive discovery of configured media locker roots.
    - Authoritative explicit configuration: invalid explicit path never falls back to host mounts.
    - Distinguishes empty, fully_indexed, unavailable, unreadable, unsupported, and partially_processed.
    - Never reports access failure as '0 unindexed files'.
    - Preserves originals in their existing locations by default.
    """
    v_root = Path(vault_root).resolve()
    mem_file = v_root / "System" / "Memory.md"
    ing_cfg: Dict[str, Any] = {}
    if mem_file.is_file():
        try:
            fm, _ = parse_frontmatter(mem_file.read_text(encoding="utf-8"))
            ing_cfg = dict(fm.get("ingestion_config") or {})
            if not ing_cfg and isinstance(fm.get("ingestion"), dict):
                sources_map = fm["ingestion"].get("sources") or {}
                media_src = sources_map.get("media") or {}
                if isinstance(media_src, dict):
                    col = str(media_src.get("collection") or "Chrysalis-Media-Locker")
                    if not col.startswith("<"):
                        ing_cfg["locker_root"] = col
                    if media_src.get("local_mount_path"):
                        ing_cfg["local_locker_path"] = media_src["local_mount_path"]
                    if media_src.get("discovery_roots"):
                        ing_cfg["discovery_roots"] = media_src["discovery_roots"]
        except Exception:
            ing_cfg = {}

    cfg_locker_name = str(ing_cfg.get("locker_root") or "Chrysalis-Media-Locker")
    inbox_rel = str(ing_cfg.get("drive_inbox_folder") or f"{cfg_locker_name}/01-Inbox")
    projects_rel = str(ing_cfg.get("drive_projects_folder") or f"{cfg_locker_name}/02-Projects")
    preserve_in_place = bool(ing_cfg.get("preserve_originals_in_place", True))
    effective_max_depth = int(ing_cfg.get("max_discovery_depth", max_depth))
    configured_subroots = list(discovery_roots or ing_cfg.get("discovery_roots") or ["01-Inbox", "02-Projects"])

    # Collect existing Sources/*.md records in the vault
    indexed_sources: List[Dict[str, Any]] = []
    sources_dir = v_root / "Sources"
    if sources_dir.is_dir():
        for sf in sorted(sources_dir.rglob("*.md")):
            if sf.name == "README.md":
                continue
            try:
                sfm, _ = parse_frontmatter(sf.read_text(encoding="utf-8"))
                complete, missing = _check_source_completeness(sfm, v_root)
                indexed_sources.append({
                    "id": sfm.get("id") or sf.stem,
                    "path": sf.relative_to(v_root).as_posix(),
                    "title": sfm.get("title"),
                    "original_filename": sfm.get("original_filename"),
                    "relative_path": sfm.get("relative_path"),
                    "sha256": str(sfm.get("sha256") or "").lower() or None,
                    "source_url": sfm.get("source_url"),
                    "ingestion_status": sfm.get("ingestion_status"),
                    "complete": complete,
                    "missing_targets": missing,
                })
            except Exception:
                continue

    # Resolve target locker root or inbox path
    explicit_target = locker_root or inbox_path or ing_cfg.get("local_locker_path")
    resolved_base: Optional[Path] = None
    diagnostics: List[Dict[str, Any]] = []

    if explicit_target is not None:
        cand = Path(str(explicit_target)).expanduser()
        if not cand.exists():
            return {
                "vault": str(v_root),
                "collection_status": "unavailable",
                "error_code": "locker_unavailable",
                "message": f"Explicit media path is unavailable or does not exist: {cand}",
                "locker_root": str(cand),
                "drive_inbox_folder": inbox_rel,
                "drive_projects_folder": projects_rel,
                "preserve_originals_in_place": preserve_in_place,
                "indexed_sources_count": len(indexed_sources),
                "indexed_sources": indexed_sources,
                "local_mount_path": None,
                "files": [],
                "local_unindexed_files": [],
                "diagnostics": [{
                    "code": "locker_unavailable",
                    "severity": "error",
                    "message": f"Explicitly configured media path does not exist: {cand}",
                    "path": str(cand),
                }],
            }
        try:
            resolved_base = cand.resolve()
            if not resolved_base.is_dir():
                raise PermissionError(f"Not a directory: {resolved_base}")
            list(resolved_base.iterdir())
        except OSError as e:
            return {
                "vault": str(v_root),
                "collection_status": "unreadable",
                "error_code": "locker_unreadable",
                "message": f"Explicit media path is unreadable: {e}",
                "locker_root": str(cand),
                "drive_inbox_folder": inbox_rel,
                "drive_projects_folder": projects_rel,
                "preserve_originals_in_place": preserve_in_place,
                "indexed_sources_count": len(indexed_sources),
                "indexed_sources": indexed_sources,
                "local_mount_path": str(cand),
                "files": [],
                "local_unindexed_files": [],
                "diagnostics": [{
                    "code": "locker_unreadable",
                    "severity": "error",
                    "message": str(e),
                    "path": str(cand),
                }],
            }
    else:
        host_path: Optional[Path] = None
        host_err: Optional[Dict[str, Any]] = None
        if integration in (None, "google-drive"):
            from helpers.providers.google_drive import resolve_google_drive_host_mount

            host_path, host_err = resolve_google_drive_host_mount(
                cfg_locker_name,
                allow_host_fallback=allow_host_fallback,
            )
        if host_err is not None:
            return {
                "vault": str(v_root),
                "collection_status": "unavailable",
                "error_code": "locker_unavailable",
                "message": host_err["message"],
                "locker_root": host_err.get("path") or cfg_locker_name,
                "drive_inbox_folder": inbox_rel,
                "drive_projects_folder": projects_rel,
                "preserve_originals_in_place": preserve_in_place,
                "indexed_sources_count": len(indexed_sources),
                "indexed_sources": indexed_sources,
                "local_mount_path": None,
                "files": [],
                "local_unindexed_files": [],
                "diagnostics": [host_err],
            }
        resolved_base = host_path

        if resolved_base is None:
            unavail_msg = (
                "Media Locker mount is unavailable (no explicit locker root or connected Drive mount)."
                if integration in (None, "google-drive")
                else f"Mounted filesystem path is unavailable for integration '{integration}'."
            )
            diag_msg = (
                "Media Locker mount unavailable; connect Google Drive or pass --locker-root."
                if integration == "google-drive"
                else "Media storage mount unavailable; configure local_mount_path or pass --locker-root."
            )
            return {
                "vault": str(v_root),
                "collection_status": "unavailable",
                "error_code": "locker_unavailable",
                "message": unavail_msg,
                "locker_root": cfg_locker_name,
                "drive_inbox_folder": inbox_rel,
                "drive_projects_folder": projects_rel,
                "preserve_originals_in_place": preserve_in_place,
                "indexed_sources_count": len(indexed_sources),
                "indexed_sources": indexed_sources,
                "local_mount_path": None,
                "files": [],
                "local_unindexed_files": [],
                "diagnostics": [{
                    "code": "locker_unavailable",
                    "severity": "info",
                    "message": diag_msg,
                }],
            }


    # Determine roots to walk within resolved_base while preserving locker-relative paths
    walk_roots: List[Path] = []
    if inbox_path is not None:
        raw_inbox = Path(str(inbox_path)).expanduser()
        if locker_root is not None:
            cand_inbox = raw_inbox if raw_inbox.is_absolute() else (resolved_base / raw_inbox)
            if not cand_inbox.exists():
                return {
                    "vault": str(v_root),
                    "collection_status": "unavailable",
                    "error_code": "locker_unavailable",
                    "message": f"Explicit inbox_path does not exist: {cand_inbox}",
                    "locker_root": str(resolved_base),
                    "drive_inbox_folder": inbox_rel,
                    "drive_projects_folder": projects_rel,
                    "preserve_originals_in_place": preserve_in_place,
                    "indexed_sources_count": len(indexed_sources),
                    "indexed_sources": indexed_sources,
                    "local_mount_path": None,
                    "files": [],
                    "local_unindexed_files": [],
                    "diagnostics": [{
                        "code": "locker_unavailable",
                        "severity": "error",
                        "message": f"Explicit inbox_path does not exist: {cand_inbox}",
                        "path": str(cand_inbox),
                    }],
                }
            resolved_inbox = cand_inbox.resolve()
            if not resolved_inbox.is_relative_to(resolved_base):
                return {
                    "vault": str(v_root),
                    "collection_status": "unreadable",
                    "error_code": "path_traversal_forbidden",
                    "message": f"inbox_path escapes locker_root: {resolved_inbox}",
                    "locker_root": str(resolved_base),
                    "drive_inbox_folder": inbox_rel,
                    "drive_projects_folder": projects_rel,
                    "preserve_originals_in_place": preserve_in_place,
                    "indexed_sources_count": len(indexed_sources),
                    "indexed_sources": indexed_sources,
                    "local_mount_path": str(resolved_base),
                    "files": [],
                    "local_unindexed_files": [],
                    "diagnostics": [{
                        "code": "path_traversal_forbidden",
                        "severity": "error",
                        "message": f"inbox_path escapes locker_root: {resolved_inbox}",
                        "path": str(resolved_inbox),
                    }],
                }
            walk_roots = [resolved_inbox]
        else:
            # Only inbox_path was passed: preserve relative paths such as '01-Inbox/file.pdf'
            # or '02-Projects/<course>/<project>/file.pdf' by resolving the locker root ancestor.
            walk_roots = [resolved_base]
            curr_anc = resolved_base
            while curr_anc != curr_anc.parent:
                if curr_anc.name.lower() == cfg_locker_name.lower():
                    resolved_base = curr_anc
                    break
                if curr_anc.name.lower().startswith(("01-inbox", "02-projects")):
                    resolved_base = curr_anc.parent
                    break
                curr_anc = curr_anc.parent
    else:
        for sub in configured_subroots:
            clean_sub = str(sub).replace("\\", "/").strip("/")
            if clean_sub.startswith(f"{cfg_locker_name}/"):
                clean_sub = clean_sub[len(cfg_locker_name) + 1:]
            if ".." in Path(clean_sub).parts:
                diagnostics.append({
                    "code": "path_traversal_forbidden",
                    "severity": "error",
                    "message": f"Rejected unsafe discovery root escaping locker: {sub}",
                })
                continue
            cand_sub = resolved_base / clean_sub
            if cand_sub.exists():
                try:
                    if cand_sub.resolve().is_relative_to(resolved_base):
                        walk_roots.append(cand_sub.resolve())
                    else:
                        diagnostics.append({
                            "code": "path_traversal_forbidden",
                            "severity": "error",
                            "message": f"Rejected symlink/path escaping locker root: {sub}",
                        })
                except Exception:
                    continue
        if not walk_roots:
            walk_roots = [resolved_base]

    discovered_files: List[Dict[str, Any]] = []
    seen_resolved: Set[str] = set()

    def _walk_bounded(current_dir: Path, depth: int) -> None:
        if depth > effective_max_depth:
            return
        try:
            entries = sorted(current_dir.iterdir(), key=lambda e: e.name.lower())
        except OSError as e:
            diagnostics.append({
                "code": "directory_unreadable",
                "severity": "error",
                "message": f"Unable to read directory {current_dir}: {e}",
                "path": str(current_dir),
            })
            return

        for entry in entries:
            if entry.name.startswith(".") or entry.name.lower() in {"desktop.ini", "thumbs.db"}:
                continue
            try:
                resolved_entry = entry.resolve()
                if not resolved_entry.is_relative_to(resolved_base):
                    diagnostics.append({
                        "code": "path_traversal_forbidden",
                        "severity": "error",
                        "message": f"Path escapes selected locker root: {entry}",
                        "path": str(entry),
                    })
                    continue
            except OSError as e:
                discovered_files.append({
                    "filename": entry.name,
                    "relative_path": entry.name,
                    "path": str(entry),
                    "readable": False,
                    "supported": False,
                    "index_state": "unreadable",
                    "error": str(e),
                })
                continue

            if entry.is_dir():
                _walk_bounded(entry, depth + 1)
            elif entry.is_file():
                key = str(resolved_entry)
                if key in seen_resolved:
                    continue
                seen_resolved.add(key)
                info = inspect_media_file(entry, locker_root=resolved_base)
                if not info.get("readable"):
                    info["index_state"] = "unreadable"
                    discovered_files.append(info)
                    continue

                ident = evaluate_source_identity(
                    v_root,
                    precomputed_sha256=info.get("sha256"),
                    original_filename=info.get("filename"),
                    relative_path=info.get("relative_path"),
                )
                info["identity"] = ident
                if not info.get("supported"):
                    # Keep index_state='unsupported' while unindexed; once recorded in Sources/*.md,
                    # reflect its indexed identity state (e.g. exact_duplicate) so reruns reach fully_indexed.
                    info["index_state"] = "unsupported" if ident["match_status"] == "new_source" else ident["match_status"]
                    discovered_files.append(info)
                    continue

                info["index_state"] = ident["match_status"]
                discovered_files.append(info)

    for wr in walk_roots:
        _walk_bounded(wr, 1)

    counts = {
        "total_files": len(discovered_files),
        "new_source": sum(1 for f in discovered_files if f.get("index_state") == "new_source"),
        "exact_duplicate": sum(1 for f in discovered_files if f.get("index_state") == "exact_duplicate"),
        "changed_version": sum(1 for f in discovered_files if f.get("index_state") == "changed_version"),
        "incomplete_prior_ingestion": sum(1 for f in discovered_files if f.get("index_state") == "incomplete_prior_ingestion"),
        "renamed_or_moved": sum(1 for f in discovered_files if f.get("index_state") == "renamed_or_moved"),
        "unsupported": sum(1 for f in discovered_files if f.get("index_state") == "unsupported"),
        "unreadable": sum(1 for f in discovered_files if f.get("index_state") == "unreadable"),
        "shared_reference": sum(1 for f in discovered_files if f.get("material_role") == "shared_reference"),
    }

    if counts["total_files"] == 0:
        if any(d.get("code") == "directory_unreadable" for d in diagnostics):
            collection_status = "unreadable"
        else:
            collection_status = "empty"
    elif counts["unreadable"] == counts["total_files"]:
        collection_status = "unreadable"
    elif counts["supported" if "supported" in counts else "total_files"] and (
        counts["new_source"] == 0
        and counts["changed_version"] == 0
        and counts["incomplete_prior_ingestion"] == 0
        and counts["unreadable"] == 0
        and counts["unsupported"] == 0
    ):
        collection_status = "fully_indexed"
    elif (
        counts["exact_duplicate"] > 0
        or counts["incomplete_prior_ingestion"] > 0
        or counts["renamed_or_moved"] > 0
        or counts["unsupported"] > 0
    ) and (
        counts["new_source"] > 0
        or counts["changed_version"] > 0
        or counts["incomplete_prior_ingestion"] > 0
        or counts["unsupported"] > 0
    ):
        collection_status = "partially_processed"
    elif counts["exact_duplicate"] > 0 and counts["unsupported"] > 0 and counts["new_source"] == 0:
        collection_status = "partially_processed"
    elif counts["unsupported"] == counts["total_files"]:
        collection_status = "unsupported"
    else:
        collection_status = "unindexed_inputs_present"

    local_unindexed = [
        f for f in discovered_files
        if f.get("index_state") in {"new_source", "changed_version", "incomplete_prior_ingestion", "unsupported"}
    ]

    return {
        "vault": str(v_root),
        "collection_status": collection_status,
        "locker_root": str(resolved_base),
        "drive_inbox_folder": inbox_rel,
        "drive_projects_folder": projects_rel,
        "preserve_originals_in_place": preserve_in_place,
        "indexed_sources_count": len(indexed_sources),
        "indexed_sources": indexed_sources,
        "local_mount_path": str(resolved_base),
        "counts": counts,
        "files": discovered_files,
        "local_unindexed_files": local_unindexed,
        "diagnostics": diagnostics,
    }


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
    sha_attr = sha256_digest if sha256_digest else "unavailable"
    return (
        f'<untrusted_document_payload source_id="{source_id}" '
        f'sha256="{sha_attr}" mime_type="{mime_type}">\n'
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

_VALIDATOR_CACHE: Dict[Tuple[str, float], Any] = {}
_FORMAT_CHECKER = FormatChecker() if FormatChecker else None


if _FORMAT_CHECKER:
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


class _MockValidationError:
    def __init__(self, validator: str, message: str, path: Sequence[Union[str, int]] = ()):
        self.validator = validator
        self.message = message
        self.path = list(path)


class _FallbackValidator:
    """Pure-Python standard library fallback when jsonschema is not installed."""
    def __init__(self, schema_dict: Dict[str, Any]):
        self.schema = schema_dict

    def iter_errors(self, instance: Any):
        if not isinstance(instance, dict):
            return
        req = self.schema.get("required", [])
        for r in req:
            if r not in instance:
                yield _MockValidationError("required", f"'{r}' is a required property", [r])
        if self.schema.get("additionalProperties") is False:
            allowed = set(self.schema.get("properties", {}).keys())
            for k in instance.keys():
                if k not in allowed:
                    yield _MockValidationError("additionalProperties", f"Additional properties are not allowed ('{k}' was unexpected)", ())
        props = self.schema.get("properties", {})
        for k, v in instance.items():
            if k in props:
                pdef = props[k]
                if "enum" in pdef and v is not None and v not in pdef["enum"]:
                    yield _MockValidationError("enum", f"'{v}' is not one of {pdef['enum']}", [k])
                if "type" in pdef and v is not None:
                    ptypes = pdef["type"] if isinstance(pdef["type"], list) else [pdef["type"]]
                    if isinstance(v, bool) and "boolean" not in ptypes:
                        yield _MockValidationError("type", f"{v} is not of type boolean", [k])
                    elif isinstance(v, int) and not isinstance(v, bool) and "integer" not in ptypes and "number" not in ptypes:
                        yield _MockValidationError("type", f"{v} is not of type {ptypes}", [k])
                    elif isinstance(v, str) and "string" not in ptypes:
                        yield _MockValidationError("type", f"{v} is not of type {ptypes}", [k])
                    elif isinstance(v, list) and "array" not in ptypes:
                        yield _MockValidationError("type", f"{v} is not of type array", [k])
                    elif isinstance(v, dict) and "object" not in ptypes:
                        yield _MockValidationError("type", f"{v} is not of type object", [k])
                if isinstance(v, str):
                    if "minLength" in pdef and len(v) < pdef["minLength"]:
                        yield _MockValidationError("minLength", f"'{v}' is shorter than {pdef['minLength']}", [k])
                    if "pattern" in pdef and not re.search(pdef["pattern"], v):
                        yield _MockValidationError("pattern", f"'{v}' does not match pattern {pdef['pattern']}", [k])
                    if pdef.get("format") == "date" and not DATE_ONLY_PATTERN.match(v):
                        yield _MockValidationError("format", f"'{v}' is not a valid date", [k])
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    if "minimum" in pdef and v < pdef["minimum"]:
                        yield _MockValidationError("minimum", f"{v} is less than minimum {pdef['minimum']}", [k])
                    if "maximum" in pdef and v > pdef["maximum"]:
                        yield _MockValidationError("maximum", f"{v} is greater than maximum {pdef['maximum']}", [k])
                if isinstance(v, dict) and "properties" in pdef:
                    nested_validator = _FallbackValidator(pdef)
                    for err in nested_validator.iter_errors(v):
                        yield _MockValidationError(err.validator, err.message, [k] + err.path)
                if isinstance(v, list) and "items" in pdef and isinstance(pdef["items"], dict):
                    item_validator = _FallbackValidator(pdef["items"])
                    for idx, item in enumerate(v):
                        for err in item_validator.iter_errors(item):
                            yield _MockValidationError(err.validator, err.message, [k, idx] + err.path)


def _find_type_schema_file(type_name: str, collection_dir: Optional[Union[Path, str]] = None, record_path: Optional[Path] = None) -> Optional[Path]:
    """Resolves physical path to _types/{type_name}.md across repository configurations."""
    candidates: List[Path] = []
    if collection_dir:
        candidates.append(Path(collection_dir) / "_types" / f"{type_name}.md")

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
    schema_path = _find_type_schema_file(type_name, collection_dir=collection_dir, record_path=record_path)
    if not schema_path:
        return None

    try:
        mtime = schema_path.stat().st_mtime
    except OSError:
        mtime = 0.0

    cache_key = (str(schema_path.resolve()), mtime)
    if cache_key in _VALIDATOR_CACHE:
        return _VALIDATOR_CACHE[cache_key]

    try:
        content = schema_path.read_text(encoding="utf-8")
        fm, _ = parse_frontmatter(content)
        schema_val = fm.get("schema", {}).get("value")
        if not isinstance(schema_val, dict):
            return None
        if Draft202012Validator is not None:
            validator = Draft202012Validator(schema_val, format_checker=_FORMAT_CHECKER)
        else:
            validator = _FallbackValidator(schema_val)
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
    Validates a markdown record's frontmatter against its mdbase type definition.
    Enforces authoritative JSON Schema Draft 2020-12 validation via jsonschema.Draft202012Validator,
    mapping validation errors to canonical schema_<keyword> diagnostic codes.
    Preserves Chrysalis Local Timezone format checks (rejecting UTC 'Z' strings).
    """
    path_obj = Path(path)
    if record_text is None:
        record_text = path_obj.read_text(encoding="utf-8")
    elif isinstance(record_text, Path) or (isinstance(record_text, str) and not record_text.startswith("---") and Path(record_text).is_dir()):
        if collection_dir is None:
            collection_dir = Path(record_text)
        record_text = path_obj.read_text(encoding="utf-8")
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

    valid_types = {"task", "project", "zettel", "source", "system_state"}
    if not resolved_type or resolved_type not in valid_types:
        diagnostics.append(Diagnostic(
            code="type_unknown",
            severity="error",
            message=f"Unable to determine valid mdbase type for {path_obj}",
            path=str(path_obj),
            recovery_action="FixRequest"
        ))
        return ValidationResult(valid=False, diagnostics=diagnostics, frontmatter=fm, body=body)

    # Pre-check: Chrysalis Local Timezone Invariant (reject raw UTC 'Z' timestamps)
    for k, v in fm.items():
        if isinstance(v, str) and RAW_UTC_PATTERN.match(v):
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
                    valid_revs = {actual_rev.lower()}
                    if fm_rev:
                        valid_revs.add(fm_rev.lower())
                    if str(if_rev).strip().lower() not in valid_revs:
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


def verify_ingestion_batch(
    vault_root: Union[Path, str],
    proposal: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Post-apply verification pass for an ingestion batch.
    Confirms every record in proposal exists on disk, validates against its schema,
    and has zero broken cross-references.
    """
    v_root = Path(vault_root).resolve()
    records: List[Dict[str, Any]] = list(proposal.get("records") or [])
    diagnostics: List[Dict[str, Any]] = []
    verified_paths: List[str] = []

    for rec in records:
        rel_path = str(rec.get("path") or "").replace("\\", "/").lstrip("/")
        abs_target = v_root / rel_path
        if not abs_target.is_file():
            diagnostics.append({
                "code": "missing_applied_record",
                "severity": "error",
                "path": rel_path,
                "message": f"Expected applied record does not exist on disk: {rel_path}",
            })
            continue
        val_res = validate_record(abs_target, abs_target.read_text(encoding="utf-8"), collection_dir=v_root)
        if not val_res.valid:
            for d in val_res.diagnostics:
                diagnostics.append(d.to_dict())
            continue
        fm = val_res.frontmatter or {}
        if rel_path.startswith("Sources/"):
            complete, missing = _check_source_completeness(fm, v_root)
            if not complete:
                diagnostics.append({
                    "code": "incomplete_source_links",
                    "severity": "error",
                    "path": rel_path,
                    "message": f"Source record has unresolved targets after batch apply: {missing}",
                })
                continue
        verified_paths.append(rel_path)

    return {
        "valid": len(diagnostics) == 0,
        "verified_count": len(verified_paths),
        "verified_paths": verified_paths,
        "diagnostics": diagnostics,
    }


def apply_ingestion_proposal(
    vault_root: Union[Path, str],
    proposal: Dict[str, Any],
    *,
    approved: bool = False,
    state_file: Optional[Union[Path, str]] = None,
    fail_after_n: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Executes approved batch persistence with coherent cross-reference ordering and resumable retry ledger.
    - Enforces Mandatory Human Approval Gate (approved=True required).
    - Acquires advisory batch lock and prevalidates entire proposal (including CAS revisions & new-record collision checks).
    - Orders writes so referenced targets (Projects, Slipbox, Tasks) are written before Sources.
    - Records per-file completion in <vault>/.chrysalis/ingestion_batches/<proposal_id>.json so retry
      after mid-batch failure resumes cleanly without duplicating or failing on already-applied outputs.
    """
    v_root = Path(vault_root).resolve()
    proposal_id = str(proposal.get("proposal_id") or "ingest-batch")

    if not approved:
        return {
            "valid": False,
            "applied": False,
            "error_code": "approval_required",
            "message": "Mandatory Human Approval Gate: proposal cannot be applied without explicit approval (approved=True).",
            "proposal_id": proposal_id,
            "applied_records": [],
        }

    batch_ledger_path = (
        Path(state_file).resolve()
        if state_file
        else (v_root / ".chrysalis" / "ingestion_batches" / f"{proposal_id}.json")
    )
    batch_ledger_path.parent.mkdir(parents=True, exist_ok=True)

    with _advisory_file_lock(batch_ledger_path):
        preval = prevalidate_ingestion_proposal(v_root, proposal)
        if not preval["valid"]:
            return {
                "valid": False,
                "applied": False,
                "error_code": "prevalidation_failed",
                "message": "Proposal failed prevalidation; zero files were written.",
                "proposal_id": proposal_id,
                "prevalidation": preval,
                "applied_records": [],
            }

        ledger: Dict[str, Any] = {
            "proposal_id": proposal_id,
            "status": "in_progress",
            "applied_records": {},
            "outcomes": list(proposal.get("outcomes") or []),
        }
        if batch_ledger_path.is_file():
            try:
                loaded = json.loads(batch_ledger_path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    ledger.update(loaded)
            except Exception:
                pass

        def _save_ledger() -> None:
            batch_ledger_path.write_text(json.dumps(ledger, indent=2, default=str), encoding="utf-8")

        # Sort records so targets (Projects, Slipbox, Tasks) are persisted before Sources
        def _order_key(rec: Dict[str, Any]) -> int:
            p = str(rec.get("path") or "").replace("\\", "/").lstrip("/")
            if p.startswith("Projects/"):
                return 0
            if p.startswith("Slipbox/"):
                return 1
            if p.startswith("TaskNotes/Tasks/"):
                return 2
            if p.startswith("Sources/"):
                return 3
            return 4

        ordered_records = sorted(list(proposal.get("records") or []), key=_order_key)
        applied_this_run: List[str] = []
        skipped_already_applied: List[str] = []
        writes_performed = 0

        for rec in ordered_records:
            rel_path = str(rec.get("path") or "").replace("\\", "/").lstrip("/")
            abs_target = v_root / rel_path
            md_text = _render_record_markdown(rec)
            expected_new_rev = compute_revision(md_text)

            # Check if already applied in a previous attempt of this batch
            prev_entry = (ledger.get("applied_records") or {}).get(rel_path)
            if abs_target.is_file():
                current_disk_rev = compute_revision(abs_target)
                if current_disk_rev == expected_new_rev or (
                    isinstance(prev_entry, dict) and prev_entry.get("revision") == current_disk_rev
                ):
                    skipped_already_applied.append(rel_path)
                    ledger["applied_records"][rel_path] = {
                        "revision": current_disk_rev,
                        "status": "applied",
                    }
                    _save_ledger()
                    continue

            if fail_after_n is not None and writes_performed >= fail_after_n:
                ledger["status"] = "interrupted"
                _save_ledger()
                return {
                    "valid": False,
                    "applied": False,
                    "error_code": "batch_interrupted",
                    "message": f"Batch interrupted after {writes_performed} writes; state saved for idempotent retry.",
                    "proposal_id": proposal_id,
                    "state_file": str(batch_ledger_path),
                    "applied_this_run": applied_this_run,
                    "skipped_already_applied": skipped_already_applied,
                }

            if_rev = rec.get("if_revision")
            if if_rev is not None and abs_target.is_file():
                doc_rev = compute_revision(abs_target)
                raw_text = abs_target.read_text(encoding="utf-8", errors="replace")
                fm_raw = (
                    raw_text.split("---", 2)[1]
                    if raw_text.startswith("---") and raw_text.count("---") >= 2
                    else ""
                )
                fm_rev = compute_revision(fm_raw) if fm_raw else ""
                if fm_rev and str(if_rev).strip().lower() == fm_rev.lower():
                    if_rev = doc_rev

            cas_res = apply_cas_mutation(abs_target, md_text, if_revision=if_rev)
            if not cas_res.valid:
                ledger["status"] = "failed"
                _save_ledger()
                return {
                    "valid": False,
                    "applied": False,
                    "error_code": "cas_apply_failed",
                    "message": f"Failed to persist {rel_path}",
                    "diagnostics": [d.to_dict() for d in cas_res.diagnostics],
                    "proposal_id": proposal_id,
                    "state_file": str(batch_ledger_path),
                    "applied_this_run": applied_this_run,
                    "skipped_already_applied": skipped_already_applied,
                }

            writes_performed += 1
            applied_this_run.append(rel_path)
            ledger["applied_records"][rel_path] = {
                "revision": cas_res.revision,
                "status": "applied",
            }
            _save_ledger()

        verification = verify_ingestion_batch(v_root, proposal)
        ledger["status"] = "completed" if verification["valid"] else "verification_failed"
        _save_ledger()

        return {
            "valid": verification["valid"],
            "applied": True,
            "proposal_id": proposal_id,
            "state_file": str(batch_ledger_path),
            "applied_this_run": applied_this_run,
            "skipped_already_applied": skipped_already_applied,
            "total_applied_records": len(ledger["applied_records"]),
            "outcome_counts": preval["outcome_counts"],
            "verification": verification,
        }


def _resolve_cli_vault(explicit_vault: Optional[str] = None, use_runtime: bool = False) -> Path:
    import sys
    repo_root = str(Path(__file__).resolve().parents[1])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
    try:
        from System.scripts.vault_paths import resolve_runtime_vault, resolve_vault_root
        return resolve_runtime_vault(explicit_vault) if use_runtime else resolve_vault_root(explicit_vault)
    except Exception:
        if explicit_vault:
            return Path(explicit_vault).expanduser().resolve()
        env_v = os.environ.get("CHRYSALIS_VAULT_PATH") or os.environ.get("CHRYSALIS_VAULT_ROOT")
        if env_v:
            return Path(env_v).expanduser().resolve()
        return Path.cwd().resolve()


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Chrysalis A2 Access Layer Helper CLI (schema validation, CAS revision, duplicate check, horizon query)"
    )
    parser.add_argument("--vault", default=None, help="Collection/vault root directory")
    parser.add_argument("--runtime", action="store_true", help="Automatically resolve active personal runtime vault")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("resolve-vault", help="Print resolved vault root path")

    p_list = subparsers.add_parser("list", help="List collection records in the vault")
    p_list.add_argument("--type", dest="record_type", choices=["task", "project", "zettel", "source", "system_state"], default=None)

    p_val = subparsers.add_parser("validate", help="Validate a record file against its JSON Schema 2020-12 type")
    p_val.add_argument("path", help="Vault-relative or absolute path to record")
    p_val.add_argument("--type", dest="record_type", default=None)

    p_rev = subparsers.add_parser("revision", help="Compute exact ADR 0006 SHA-256 revision of a file")
    p_rev.add_argument("path", help="Vault-relative or absolute path to file")

    p_dup = subparsers.add_parser("check-duplicate", help="Evaluate multi-level source identity and deduplication against Sources/")
    p_dup.add_argument("source_file", nargs="?", default=None, help="Optional path to local source file to hash and check")
    p_dup.add_argument("--text", default=None, help="Raw text payload fetched via Google Drive MCP server or session")
    p_dup.add_argument("--sha256", default=None, help="Precomputed 64-char SHA-256 digest of source file bytes")
    p_dup.add_argument("--stdin", action="store_true", help="Read payload bytes from stdin")
    p_dup.add_argument("--source-url", default=None, help="Optional Google Drive or web source URL")
    p_dup.add_argument("--filename", default=None, help="Original filename of the source")
    p_dup.add_argument("--relative-path", default=None, help="Locker-relative path of the source")

    p_drive = subparsers.add_parser("drive-inbox", aliases=["discover", "discover-locker"], help="Discover files across Chrysalis-Media-Locker roots with explicit status codes")
    p_drive.add_argument("--locker-root", default=None, help="Explicit path to Media Locker root")
    p_drive.add_argument("--inbox-path", "--subpath", dest="inbox_path", default=None, help="Explicit path or relative subpath to a specific inbox/subfolder")
    p_drive.add_argument("--discovery-root", dest="discovery_roots", action="append", default=None, help="Specific discovery root(s) within locker_root")
    p_drive.add_argument("--allow-host-fallback", action="store_true", help="Allow searching host Google Drive mount locations when no explicit path is given")

    p_cas = subparsers.add_parser("apply-cas-mutation", aliases=["cas-write"], help="Execute atomic Compare-And-Swap (CAS) mutation with JSON Schema 2020-12 validation")
    p_cas.add_argument("path", help="Vault-relative or absolute target file path")
    p_cas.add_argument("--if-revision", "--expected-hash", dest="if_revision", default=None, help="Expected 64-char SHA-256 revision or frontmatter hash on disk")
    p_cas.add_argument("--updates-json", default=None, help="JSON object of frontmatter fields to update while preserving the Markdown body")
    p_cas.add_argument("--create", action="store_true", help="Create a new record (fails if file already exists)")
    p_cas.add_argument("--content-file", default=None, help="File containing new UTF-8 Markdown content")
    p_cas.add_argument("--stdin", action="store_true", help="Read new UTF-8 Markdown content from stdin")

    p_rec = subparsers.add_parser("reconcile-syllabus", help="Diff extracted deliverables against an existing Projects/<id>/Roadmap.md")
    p_rec.add_argument("roadmap_path", help="Vault-relative or absolute path to Roadmap.md")
    p_rec.add_argument("deliverables_file", help="Path to YAML/JSON file containing extracted deliverables")
    p_rec.add_argument("--mode", choices=["supplementary", "authoritative_replacement"], default=None)
    p_rec.add_argument("--authoritative-replacement", action="store_true", default=False)
    p_rec.add_argument("--source-scope", default=None)
    p_rec.add_argument("--source-ref", default=None)
    p_rec.add_argument("--extraction-status", choices=["complete", "partial", "empty", "failed"], default="complete")

    p_hor = subparsers.add_parser("horizon-tasks", help="Partition project roadmap deliverables across the 14-day planning horizon")
    p_hor.add_argument("--horizon-days", type=int, default=14)
    p_hor.add_argument("--reference-date", "--today", dest="reference_date", default=None, help="Reference date YYYY-MM-DD (defaults to today)")

    p_preval = subparsers.add_parser("prevalidate-proposal", help="Prevalidate an ingestion batch proposal JSON before human approval")
    p_preval.add_argument("proposal_file", help="Path to JSON file containing the ingestion proposal")

    p_apply = subparsers.add_parser("apply-proposal", help="Apply an approved ingestion batch proposal with resumable batch ledger")
    p_apply.add_argument("proposal_file", help="Path to JSON file containing the ingestion proposal")
    p_apply.add_argument("--approved", action="store_true", help="Confirm explicit human approval for this batch")
    p_apply.add_argument("--state-file", default=None, help="Optional path to batch state ledger JSON")

    subparsers.add_parser("ingest-sources", aliases=["resolve-sources"], help="Resolve configured provider-neutral ingestion sources from System/Memory.md")

    p_idisc = subparsers.add_parser("ingest-discover", help="Execute provider-neutral discovery for a configured source alias or all enabled sources")
    p_idisc.add_argument("--source", dest="source_alias", default=None, help="Configured source alias (e.g. 'media', 'quick-capture')")
    p_idisc.add_argument("--all", action="store_true", dest="discover_all", help="Discover across all enabled configured sources")
    p_idisc.add_argument("--drive", action="store_true", dest="legacy_drive", help="Legacy compatibility alias for --source media")
    p_idisc.add_argument("--page-size", type=int, default=None, help="Bounded page size for discovery")
    p_idisc.add_argument("--page-token", default=None, help="Pagination continuation token")
    p_idisc.add_argument("--synthetic-response", default=None, help="Optional path to JSON file containing synthetic provider response")
    p_idisc.add_argument("--allow-host-fallback", action="store_true", help="Allow host mount fallback when permitted")

    p_idraft = subparsers.add_parser("ingest-draft", aliases=["ingest-register"], help="Build a prevalidated ingestion proposal from a discovery envelope or configured source")
    p_idraft.add_argument("--source", dest="source_alias", default=None, help="Configured source alias")
    p_idraft.add_argument("--all", action="store_true", dest="draft_all", help="Draft proposal across all enabled sources")
    p_idraft.add_argument("--envelope-file", default=None, help="Path to v1.0.0 IngestionDiscoveryEnvelope JSON file")
    p_idraft.add_argument("--today", dest="reference_date", default=None, help="Reference date YYYY-MM-DD")

    p_inorm = subparsers.add_parser("ingest-normalize-task", help="Normalize a Google Tasks or external task JSON payload into a v1.0.0 structured_task contract item")
    p_inorm.add_argument("task_json", nargs="?", default=None, help="Path to JSON file or inline JSON string of external task")
    p_inorm.add_argument("--source", dest="source_alias", default="quick-capture", help="Configured source alias")
    p_inorm.add_argument("--account-scope", default="user@example.com", help="Account scope")
    p_inorm.add_argument("--collection-id", default="tasklist-inbox-01", help="Task list / collection ID")

    p_icheck = subparsers.add_parser("ingest-check", help="Evaluate provider file or task capture identity against existing vault records")
    p_icheck.add_argument("item_json", help="Path to JSON file or inline JSON string of v1.0.0 IngestionItem")

    subparsers.add_parser("integration-status", aliases=["integrations-status"], help="Evaluate configured integrations, readiness states, and capability bindings")

    p_capres = subparsers.add_parser("capability-resolve", help="Resolve a named capability against configured integration bindings and readiness states")
    p_capres.add_argument("capability", help="Capability identifier (e.g. location.resolve, routing.estimate, visualization.map_projection)")
    p_capres.add_argument("--alias", default=None, help="Optional binding alias (e.g. media, quick-capture)")
    p_capres.add_argument("--instance", default=None, help="Optional explicit integration instance ID")
    p_capres.add_argument("--fallback", default="manual_only", help="Fallback mode (manual_only, skip_with_warning, require_user_input, fail)")

    p_locres = subparsers.add_parser("location-resolve", help="Resolve a location query via the configured location.resolve capability provider")
    p_locres.add_argument("--query", required=True, help="Location query string")
    p_locres.add_argument("--region-code", default=None, help="Optional ISO region code (e.g. US)")
    p_locres.add_argument("--language-code", default=None, help="Optional language code (defaults to instance config or en)")
    p_locres.add_argument("--instance", default=None, help="Optional explicit integration instance ID")
    p_locres.add_argument("--synthetic-response", default=None, help="Optional path to synthetic provider response JSON")

    p_route = subparsers.add_parser("route-estimate", help="Estimate route duration and distance via the configured routing.estimate capability provider")
    p_route.add_argument("--origin", required=True, help="Origin Place ID, coordinates, or address")
    p_route.add_argument("--destination", default=None, help="Destination Place ID, coordinates, or address")
    p_route.add_argument("--task", default=None, help="Optional vault-relative or absolute path to a task note")
    p_route.add_argument("--scheduled", default=None, help="Optional scheduled ISO timestamp for the task")
    p_route.add_argument(
        "--mode",
        default="driving",
        choices=["driving", "transit", "walking", "bicycling", "drive", "walk", "bicycle", "bike"],
        help="Travel mode",
    )
    p_route.add_argument("--departure-time", default=None, help="ISO 8601 departure timestamp with explicit local offset")
    p_route.add_argument("--arrival-time", default=None, help="ISO 8601 arrival timestamp with explicit local offset")
    p_route.add_argument("--buffer-minutes", type=int, default=None, help="Buffer minutes before arrival")
    p_route.add_argument("--instance", default=None, help="Optional explicit integration instance ID")
    p_route.add_argument("--synthetic-response", default=None, help="Optional path to synthetic provider response JSON")

    p_mapproj = subparsers.add_parser("map-project", help="Project eligible task coordinates to the configured visualization.map_projection provider")
    p_mapproj.add_argument("--view-path", default="TaskNotes/Views/maps-default.base", help="Vault-relative path to the Obsidian Bases map view")
    p_mapproj.add_argument("--instance", default=None, help="Optional explicit integration instance ID")

    args = parser.parse_args(argv)
    vault_root = _resolve_cli_vault(args.vault, use_runtime=args.runtime or (args.command == "resolve-vault" and not args.vault))

    if args.command == "resolve-vault":
        print(vault_root)
        return 0

    if args.command in {"ingest-sources", "resolve-sources"}:
        from helpers.ingestion_contract import resolve_ingestion_config
        print(json.dumps(resolve_ingestion_config(vault_root), indent=2, default=str))
        return 0

    if args.command in {"integration-status", "integrations-status"}:
        from helpers.integration_registry import evaluate_all_integrations
        print(json.dumps(evaluate_all_integrations(vault_root), indent=2, default=str))
        return 0

    if args.command == "capability-resolve":
        from helpers.integration_registry import resolve_capability_binding
        res = resolve_capability_binding(
            vault_root,
            args.capability,
            workflow_binding=args.alias,
            instance_id=args.instance,
        )
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("status") == "ok" else 1

    if args.command == "location-resolve":
        from helpers.location_routing import enrich_task_location
        syn_resp = None
        if args.synthetic_response:
            syn_resp = json.loads(Path(args.synthetic_response).read_text(encoding="utf-8"))
        res = enrich_task_location(
            vault_root,
            {"title": args.query or "Location Lookup"},
            query=args.query,
            region_code=args.region_code,
            language_code=args.language_code,
            workflow_binding="task.location_lookup",
            instance_id=args.instance,
            transport=syn_resp,
        )
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("status") in {"resolved", "ambiguous", "resolved_user_supplied", "virtual"} else 1

    if args.command == "route-estimate":
        from helpers.location_routing import (
            _parse_cli_endpoint,
            estimate_task_commute,
            normalize_travel_mode,
            propose_travel_schedule_window,
        )
        syn_resp = None
        if args.synthetic_response:
            syn_resp = json.loads(Path(args.synthetic_response).read_text(encoding="utf-8"))

        task_stub: Dict[str, Any] = {
            "title": "Route Estimate Lookup",
            "timeEstimate": 45,
            "travel_policy": {},
        }
        if args.task:
            task_path = (vault_root / args.task) if not Path(args.task).is_absolute() else Path(args.task)
            if not task_path.is_file():
                print(json.dumps({
                    "valid": False,
                    "error_code": "task_file_not_found",
                    "message": f"Specified task file does not exist: {task_path}",
                }, indent=2))
                return 1
            try:
                task_fm, _ = parse_frontmatter(task_path.read_text(encoding="utf-8"))
                if isinstance(task_fm, dict):
                    task_stub.update(task_fm)
            except Exception as e:
                print(json.dumps({
                    "valid": False,
                    "error_code": "task_parse_error",
                    "message": str(e),
                }, indent=2))
                return 1

        if args.destination:
            dest_stub = _parse_cli_endpoint(args.destination) or {
                "label": args.destination,
                "address": args.destination,
                "resolution_status": "unresolved",
            }
            task_stub["location"] = dest_stub
        elif not task_stub.get("location"):
            print(json.dumps({
                "valid": False,
                "error_code": "missing_destination",
                "message": "Destination is required (provide --destination or a --task note with resolved location).",
            }, indent=2))
            return 1

        if args.scheduled:
            task_stub["scheduled"] = args.scheduled

        origin_stub = _parse_cli_endpoint(args.origin)

        # Detect whether --mode was explicitly passed on the CLI vs defaulted
        raw_cli_args = argv if argv is not None else sys.argv[1:]
        explicit_mode_given = any(a == "--mode" or a.startswith("--mode=") for a in raw_cli_args)
        if explicit_mode_given:
            norm_mode = normalize_travel_mode(args.mode) or args.mode or "driving"
        else:
            norm_mode = None

        t_policy = task_stub.setdefault("travel_policy", {})
        if not isinstance(t_policy, dict):
            t_policy = {}
            task_stub["travel_policy"] = t_policy
        if norm_mode:
            t_policy["preferred_mode"] = norm_mode
        if args.arrival_time:
            t_policy["arrival_at"] = args.arrival_time
        if args.buffer_minutes is not None:
            t_policy["buffer_minutes"] = args.buffer_minutes

        eff_buf = args.buffer_minutes if args.buffer_minutes is not None else int(t_policy.get("buffer_minutes", 0) or 0)

        res = estimate_task_commute(
            vault_root,
            task_stub,
            origin=origin_stub,
            travel_mode=norm_mode,
            departure_at=args.departure_time,
            arrival_by=args.arrival_time or t_policy.get("arrival_at"),
            workflow_binding="plan.route_estimate",
            instance_id=args.instance,
            transport=syn_resp,
        )
        effective_arrival = args.arrival_time or task_stub.get("scheduled") or t_policy.get("arrival_at")
        if effective_arrival or args.departure_time:
            res["schedule_window"] = propose_travel_schedule_window(
                res.get("proposed_frontmatter") or task_stub,
                route_estimate=res.get("ephemeral_route_estimate"),
                arrival_at=effective_arrival,
                departure_at=args.departure_time,
                buffer_minutes=eff_buf,
            )
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("status") in {"ok", "manual_override"} else 1

    if args.command == "map-project":
        from helpers.integration_registry import invoke_capability
        req_records = []
        for tpath in sorted((vault_root / "TaskNotes" / "Tasks").glob("*.md")):
            try:
                tfm, _ = parse_frontmatter(tpath.read_text(encoding="utf-8"))
                req_records.append({"path": tpath.relative_to(vault_root).as_posix(), "frontmatter": tfm})
            except Exception:
                pass
        res = invoke_capability(
            vault_root,
            "visualization.map_projection",
            {"records": req_records, "base_view_path": args.view_path},
            workflow_binding="views.map_projection",
            instance_id=args.instance,
        )
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("status") in {"ok", "empty", "policy_filtered"} else 1

    if args.command == "ingest-normalize-task":
        from helpers.providers.google_tasks import normalize_google_task_item
        raw_input = (args.task_json or sys.stdin.read() or "").strip()
        try:
            if raw_input.startswith(("{", "[")):
                raw_dict = json.loads(raw_input)
            else:
                p_obj = Path(raw_input) if raw_input and len(raw_input) < 260 else None
                if p_obj and p_obj.is_file():
                    raw_dict = json.loads(p_obj.read_text(encoding="utf-8"))
                else:
                    raw_dict = json.loads(raw_input)
            if not isinstance(raw_dict, dict):
                raise ValueError("Task input payload must be a JSON object.")
            item = normalize_google_task_item(
                raw_dict,
                source_alias=args.source_alias,
                account_scope=args.account_scope,
                collection_id=args.collection_id,
            )
        except Exception as e:
            print(json.dumps({
                "valid": False,
                "error_code": "invalid_task_payload",
                "message": str(e),
            }, indent=2))
            return 1
        print(json.dumps(item, indent=2, default=str))
        return 0

    if args.command == "ingest-check":
        from helpers.ingestion_contract import (
            evaluate_provider_file_identity,
            evaluate_task_capture_identity,
            sanitize_ingestion_item,
            validate_ingestion_item,
        )
        raw_item_arg = (args.item_json or "").strip()
        try:
            if raw_item_arg.startswith(("{", "[")):
                item_dict = json.loads(raw_item_arg)
            else:
                p_obj = Path(raw_item_arg) if raw_item_arg and len(raw_item_arg) < 260 else None
                if p_obj and p_obj.is_file():
                    item_dict = json.loads(p_obj.read_text(encoding="utf-8"))
                else:
                    item_dict = json.loads(raw_item_arg)
            if not isinstance(item_dict, dict):
                raise ValueError("Ingestion item input must be a JSON object.")
        except Exception as e:
            print(json.dumps({
                "valid": False,
                "error_code": "invalid_item_json",
                "message": str(e),
            }, indent=2))
            return 1

        kind = item_dict.get("content_kind") or item_dict.get("item_kind")
        if kind not in {"file", "text", "structured_task"}:
            print(json.dumps({
                "valid": False,
                "error_code": "invalid_ingestion_item",
                "message": f"Missing or unsupported content_kind: '{kind}'.",
            }, indent=2))
            return 1

        if "contract_version" in item_dict:
            item_dict, _ = sanitize_ingestion_item(item_dict)
            val_res = validate_ingestion_item(item_dict)
            if not val_res.get("valid"):
                print(json.dumps({
                    "valid": False,
                    "error_code": "invalid_ingestion_item",
                    "diagnostics": val_res.get("diagnostics", []),
                }, indent=2))
                return 1

        if kind == "structured_task":
            payload = item_dict.get("payload") if isinstance(item_dict.get("payload"), dict) else item_dict
            fingerprints = item_dict.get("fingerprints") if isinstance(item_dict.get("fingerprints"), dict) else {}
            revision = item_dict.get("revision") if isinstance(item_dict.get("revision"), dict) else {}
            ext_id = str(item_dict.get("external_item_id") or payload.get("external_item_id") or "").strip()
            if not ext_id:
                print(json.dumps({
                    "valid": False,
                    "error_code": "missing_external_item_id",
                    "message": "structured_task item requires non-empty external_item_id.",
                }, indent=2))
                return 1
            res = evaluate_task_capture_identity(
                vault_root,
                integration=str(item_dict.get("integration") or "google-tasks"),
                account_scope=item_dict.get("account_scope"),
                collection_id=str(item_dict.get("collection_id") or "default"),
                external_item_id=ext_id,
                external_revision=revision.get("external_revision") or item_dict.get("external_revision"),
                structured_payload_sha256=str(
                    fingerprints.get("structured_payload_sha256")
                    or item_dict.get("structured_payload_sha256")
                    or ""
                ),
                incoming_title=str(payload.get("title") or item_dict.get("title") or ""),
                incoming_due=payload.get("due") if "due" in payload else item_dict.get("due"),
                incoming_notes=payload.get("notes") if "notes" in payload else item_dict.get("notes"),
            )
        else:
            locator = item_dict.get("locator") if isinstance(item_dict.get("locator"), dict) else {}
            fingerprints = item_dict.get("fingerprints") if isinstance(item_dict.get("fingerprints"), dict) else {}
            payload = item_dict.get("payload") if isinstance(item_dict.get("payload"), dict) else {}
            res = evaluate_provider_file_identity(
                vault_root,
                source_alias=str(item_dict.get("source_alias") or "media"),
                integration=str(item_dict.get("integration") or "google-drive"),
                collection_id=str(item_dict.get("collection_id") or ""),
                external_item_id=item_dict.get("external_item_id"),
                precomputed_sha256=fingerprints.get("sha256") or item_dict.get("sha256"),
                extracted_text=payload.get("extracted_text") or item_dict.get("extracted_text"),
                source_url=locator.get("source_url") or item_dict.get("source_url"),
                original_filename=locator.get("original_filename") or item_dict.get("original_filename"),
                relative_path=locator.get("relative_path") or item_dict.get("relative_path"),
            )
        print(json.dumps(res, indent=2, default=str))
        return 0


    if args.command == "ingest-discover":
        from helpers.ingestion_contract import (
            discover_all_configured_sources,
            discover_configured_source,
            resolve_legacy_command_alias,
        )
        syn_map = None
        if args.synthetic_response:
            loaded_syn = json.loads(Path(args.synthetic_response).read_text(encoding="utf-8"))
            target_alias = args.source_alias or "media"
            syn_map = loaded_syn if isinstance(loaded_syn, dict) and target_alias in loaded_syn else {target_alias: loaded_syn}

        if args.discover_all:
            res = discover_all_configured_sources(
                vault_root,
                page_size=args.page_size,
                synthetic_responses=syn_map,
                allow_host_fallback=args.allow_host_fallback,
            )
            print(json.dumps(res, indent=2, default=str))
            return 0

        eff_alias, compat_diag = resolve_legacy_command_alias(args.source_alias, legacy_drive_flag=args.legacy_drive)
        if not eff_alias:
            print(json.dumps({"valid": False, "error_code": "missing_source_selector", "message": "Provide --source <alias> or --all"}))
            return 1
        res = discover_configured_source(
            vault_root,
            eff_alias,
            page_size=args.page_size,
            page_token=args.page_token,
            synthetic_responses=syn_map,
            allow_host_fallback=args.allow_host_fallback,
        )
        if compat_diag:
            res.setdefault("diagnostics", []).append(compat_diag)
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("error_code") not in {"source_alias_not_configured", "source_disabled", "unsupported_integration"} else 1

    if args.command in {"ingest-draft", "ingest-register"}:
        from helpers.ingestion_contract import (
            build_ingestion_proposal_from_envelope,
            discover_all_configured_sources,
            discover_configured_source,
        )
        ref_d = date.fromisoformat(args.reference_date) if args.reference_date else date.today()
        if args.envelope_file:
            env = json.loads(Path(args.envelope_file).read_text(encoding="utf-8"))
            prop = build_ingestion_proposal_from_envelope(vault_root, env, reference_date=ref_d)
            print(json.dumps(prop, indent=2, default=str))
            return 0 if prop.get("valid_envelope") else 1
        if args.draft_all:
            all_disc = discover_all_configured_sources(vault_root)
            combined_records = []
            combined_outcomes = []
            combined_diags = []
            shared_allocated_paths: set = set()
            for alias, env in (all_disc.get("envelopes") or {}).items():
                p = build_ingestion_proposal_from_envelope(
                    vault_root,
                    env,
                    reference_date=ref_d,
                    allocated_paths=shared_allocated_paths,
                )
                combined_records.extend(p.get("records") or [])
                combined_outcomes.extend(p.get("outcomes") or [])
                combined_diags.extend(p.get("diagnostics") or [])
            prop = {
                "proposal_id": f"ingest-all-{ref_d.strftime('%Y%m%d')}",
                "records": combined_records,
                "outcomes": combined_outcomes,
                "diagnostics": combined_diags,
            }
            print(json.dumps(prop, indent=2, default=str))
            return 0
        if args.source_alias:
            env = discover_configured_source(vault_root, args.source_alias)
            prop = build_ingestion_proposal_from_envelope(vault_root, env, reference_date=ref_d)
            print(json.dumps(prop, indent=2, default=str))
            return 0 if prop.get("valid_envelope") else 1
        print(json.dumps({"valid": False, "error": "Provide --source <alias>, --all, or --envelope-file"}))
        return 1

    if args.command == "list":
        patterns = {
            "task": "TaskNotes/Tasks/*.md",
            "project": "Projects/*/Roadmap.md",
            "zettel": "Slipbox/*.md",
            "source": "Sources/*.md",
            "system_state": "System/*.md",
        }
        selected_types = [args.record_type] if args.record_type else ["task", "project", "zettel", "source"]
        records = []
        for rtype in selected_types:
            for p in sorted(vault_root.glob(patterns[rtype])):
                if p.name == "README.md" or p.name.startswith("."):
                    continue
                try:
                    fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
                except Exception:
                    fm = {}
                records.append({
                    "type": rtype,
                    "path": p.relative_to(vault_root).as_posix(),
                    "title": fm.get("title") or fm.get("id") or p.stem,
                    "status": fm.get("status") or fm.get("ingestion_status"),
                    "due": str(fm.get("due")) if fm.get("due") is not None else None,
                    "revision": compute_revision(p),
                })
        print(json.dumps({"vault": str(vault_root), "count": len(records), "records": records}, indent=2))
        return 0

    if args.command == "validate":
        target = Path(args.path)
        if not target.is_absolute():
            target = vault_root / target
        if not target.exists():
            print(json.dumps({"valid": False, "error": f"File not found: {target}"}))
            return 1
        res = validate_record(target, target.read_text(encoding="utf-8"), type_name=args.record_type, collection_dir=vault_root)
        print(json.dumps(res.to_dict(), indent=2, default=str))
        return 0 if res.valid else 1

    if args.command == "revision":
        target = Path(args.path)
        if not target.is_absolute():
            target = vault_root / target
        rev = compute_revision(target)
        print(json.dumps({"path": str(target), "revision": rev}))
        return 0 if rev else 1

    if args.command == "check-duplicate":
        raw_bytes: Optional[bytes] = None
        orig_name = args.filename
        if args.source_file:
            src_path = Path(args.source_file)
            if not src_path.is_absolute() and not src_path.exists():
                src_path = vault_root / src_path
            raw_bytes = src_path.read_bytes()
            if not orig_name:
                orig_name = src_path.name
        elif args.stdin:
            raw_bytes = sys.stdin.buffer.read()

        res = evaluate_source_identity(
            vault_root,
            raw_bytes=raw_bytes,
            precomputed_sha256=args.sha256,
            extracted_text=args.text,
            source_url=args.source_url,
            original_filename=orig_name,
            relative_path=args.relative_path,
        )
        print(json.dumps(res, indent=2))
        return 0

    if args.command in {"drive-inbox", "discover", "discover-locker"}:
        allow_fallback = bool(args.allow_host_fallback or (args.locker_root is None and args.inbox_path is None))
        res = discover_media_locker(
            vault_root,
            locker_root=args.locker_root,
            inbox_path=args.inbox_path,
            discovery_roots=args.discovery_roots,
            allow_host_fallback=allow_fallback,
        )
        print(json.dumps(res, indent=2, default=str))
        return 0

    if args.command in {"apply-cas-mutation", "cas-write"}:
        target = Path(args.path)
        if not target.is_absolute():
            target = vault_root / target
        effective_rev = args.if_revision
        if target.exists() and effective_rev:
            doc_rev = compute_revision(target)
            raw_text = target.read_text(encoding="utf-8")
            fm_raw = raw_text.split("---", 2)[1] if raw_text.startswith("---") and raw_text.count("---") >= 2 else ""
            fm_rev = compute_revision(fm_raw)
            if effective_rev.lower() == fm_rev.lower():
                effective_rev = doc_rev

        if args.updates_json:
            if not target.exists():
                print(json.dumps({"valid": False, "error": f"Target file not found for --updates-json: {target}"}))
                return 1
            raw_text = target.read_text(encoding="utf-8")
            fm, body = parse_frontmatter(raw_text)
            updates = json.loads(args.updates_json)
            if isinstance(updates, dict):
                fm.update(updates)
            serialized_fm = yaml.safe_dump(fm, sort_keys=False, allow_unicode=True).strip()
            new_content = f"---\n{serialized_fm}\n---\n{body}"
            if effective_rev is None:
                effective_rev = compute_revision(target)
        elif args.content_file:
            new_content = Path(args.content_file).read_text(encoding="utf-8")
        elif args.stdin:
            new_content = sys.stdin.read()
        else:
            print(json.dumps({"valid": False, "error": "Provide --updates-json, --content-file, or --stdin"}))
            return 1

        val_res = validate_record(target, new_content, collection_dir=vault_root)
        if not val_res.valid:
            print(json.dumps(val_res.to_dict(), indent=2, default=str))
            return 1

        res = apply_cas_mutation(
            target,
            new_content,
            if_revision=None if args.create else effective_rev,
        )
        print(json.dumps(res.to_dict(), indent=2, default=str))
        return 0 if res.valid else 1

    if args.command == "reconcile-syllabus":
        rm_path = Path(args.roadmap_path)
        if not rm_path.is_absolute():
            rm_path = vault_root / rm_path
        deliv_text = Path(args.deliverables_file).read_text(encoding="utf-8")
        diff = reconcile_syllabus(
            rm_path,
            deliv_text,
            mode=args.mode,
            authoritative_replacement=True if args.authoritative_replacement else None,
            source_scope=args.source_scope,
            source_ref=args.source_ref,
            extraction_status=args.extraction_status,
        )
        print(json.dumps(diff.to_dict(), indent=2, default=str))
        return 0

    if args.command == "horizon-tasks":
        ref_date = date.fromisoformat(args.reference_date) if args.reference_date else date.today()
        summary = []
        for rm in sorted(vault_root.glob("Projects/*/Roadmap.md")):
            try:
                fm, _ = parse_frontmatter(rm.read_text(encoding="utf-8"))
                deliverables = fm.get("deliverables", [])
                if isinstance(deliverables, list):
                    classified = classify_deliverable_horizons(
                        deliverables,
                        reference_date=ref_date,
                        horizon_days=args.horizon_days,
                        vault_root=vault_root,
                    )
                    summary.append({
                        "project_id": fm.get("project_id") or rm.parent.name,
                        "roadmap": rm.relative_to(vault_root).as_posix(),
                        "overdue": classified["overdue"],
                        "imminent": classified["imminent"],
                        "uncertain": classified["uncertain"],
                        "future": classified["future"],
                        "excluded_done_or_archived": classified["excluded_done_or_archived"],
                        "conflicts_requiring_review": classified["conflicts_requiring_review"],
                        "eligible_for_task_materialization": classified["eligible_for_task_materialization"],
                        "scheduling_handoff": classified["scheduling_handoff"],
                        "out_of_horizon_count": len(classified["future"]),
                    })
            except Exception as e:
                summary.append({"roadmap": rm.relative_to(vault_root).as_posix(), "error": str(e)})
        print(json.dumps({"vault": str(vault_root), "reference_date": ref_date.isoformat(), "projects": summary}, indent=2, default=str))
        return 0

    if args.command == "prevalidate-proposal":
        prop = json.loads(Path(args.proposal_file).read_text(encoding="utf-8"))
        res = prevalidate_ingestion_proposal(vault_root, prop)
        print(json.dumps(res, indent=2, default=str))
        return 0 if res["valid"] else 1

    if args.command == "apply-proposal":
        prop = json.loads(Path(args.proposal_file).read_text(encoding="utf-8"))
        res = apply_ingestion_proposal(
            vault_root,
            prop,
            approved=args.approved,
            state_file=args.state_file,
        )
        print(json.dumps(res, indent=2, default=str))
        return 0 if res.get("valid") else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
