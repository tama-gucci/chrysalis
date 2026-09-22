"""
Chrysalis mdbase v0.3 Helper Module (helpers/mdbase_helper.py)
Deterministic validation, ADR 0006 CAS operations, deduplication, and syllabus diffing.
Conforms strictly to Python 3.10+ standard library and PyYAML.
"""

import contextlib
from dataclasses import dataclass, field
from datetime import date, datetime
import fcntl
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

def compute_revision(document_bytes: bytes) -> str:
    """Computes exact-document revision hash: sha256(document_bytes) as 64 lowercase hex."""
    return hashlib.sha256(document_bytes).hexdigest().lower()


@contextlib.contextmanager
def _advisory_file_lock(path: Path):
    """
    Acquires an exclusive POSIX advisory lock via fcntl.flock on a dedicated
    sibling lockfile (path.with_suffix(path.suffix + ".lock")).
    
    Guarantees cross-thread and cross-process mutual exclusion.
    Lockfile is never unlinked to prevent inode-reallocation race conditions.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o666)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
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
# 3. Cryptographic Provenance & Deduplication
# =========================================================================

def check_semantic_duplicate(
    source_bytes: bytes,
    collection_dir: Union[Path, str]
) -> Optional[Tuple[str, Path]]:
    """
    Calculates SHA-256 digest of source_bytes and scans Sources/**/*.md
    to detect existing duplicate records across sessions.
    Returns (source_id, file_path) if match found, else None.
    """
    digest = compute_revision(source_bytes)
    sources_dir = Path(collection_dir) / "Sources"
    if not sources_dir.exists():
        return None

    for p in sources_dir.rglob("*.md"):
        try:
            fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
            if fm.get("sha256", "").lower() == digest:
                sid = str(fm.get("id", p.stem))
                return (sid, p)
        except Exception:
            continue
    return None


# =========================================================================
# 4. Passive Text Quarantine Formatting
# =========================================================================

def sanitize_untrusted_payload(
    raw_text: str,
    source_id: str,
    sha256_digest: str,
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
    return (
        f'<untrusted_document_payload source_id="{source_id}" '
        f'sha256="{sha256_digest}" mime_type="{mime_type}">\n'
        f'{escaped_text}\n'
        f'</untrusted_document_payload>'
    )


# =========================================================================
# 5. Uncertain Date & Horizon Boundary Handling
# =========================================================================

def process_uncertain_dates(deliverables: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            if not DATE_ONLY_PATTERN.match(stripped):
                item["due"] = None
                item["date_uncertain"] = True
            else:
                item["due"] = stripped
                if "date_uncertain" not in item:
                    item["date_uncertain"] = False
        else:
            if "date_uncertain" not in item:
                item["date_uncertain"] = False
        processed.append(item)
    return processed


def filter_horizon_deliverables(
    deliverables: List[Dict[str, Any]],
    horizon_days: int = 14,
    reference_date: Optional[date] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Partitions deliverables into (active_deliverables, inert_deliverables).
    Active deliverables are due within reference_date + horizon_days or have uncertain dates.
    Inert deliverables are due > horizon_days in the future.
    """
    ref = reference_date or date.today()
    active: List[Dict[str, Any]] = []
    inert: List[Dict[str, Any]] = []

    for d in deliverables:
        due_val = d.get("due")
        is_uncertain = d.get("date_uncertain", False)

        if not due_val or is_uncertain:
            active.append(d)
            continue

        try:
            if isinstance(due_val, date) and not isinstance(due_val, datetime):
                due_date = due_val
            elif isinstance(due_val, str):
                due_date = date.fromisoformat(due_val.strip())
            else:
                active.append(d)
                continue

            days_until = (due_date - ref).days
            if days_until <= horizon_days:
                active.append(d)
            else:
                inert.append(d)
        except Exception:
            active.append(d)

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
# 7. Syllabus Revision Reconciliation Diffing
# =========================================================================

def reconcile_syllabus(
    existing_roadmap_path: Union[Path, str],
    new_deliverables: Union[List[Dict[str, Any]], str]
) -> SyllabusDiff:
    """
    Diffs extracted deliverables from an updated syllabus against the existing roadmap.
    Categorizes deliverables into added, modified, dropped (marked status: archived), and unchanged.
    Accepts new_deliverables either as a structured list of dicts or as raw text.
    """
    roadmap_path = Path(existing_roadmap_path)
    existing_fm: Dict[str, Any] = {}
    if roadmap_path.exists():
        try:
            existing_fm, _ = parse_frontmatter(roadmap_path.read_text(encoding="utf-8"))
        except Exception:
            existing_fm = {}

    project_id = str(existing_fm.get("project_id", roadmap_path.parent.name if roadmap_path.name == "Roadmap.md" else "project"))
    old_items: List[Dict[str, Any]] = existing_fm.get("deliverables", [])
    old_by_id = {str(item["id"]): dict(item) for item in old_items if isinstance(item, dict) and "id" in item}

    # Normalize new deliverables if input is text or raw yaml
    items_to_compare: List[Dict[str, Any]] = []
    if isinstance(new_deliverables, list):
        items_to_compare = [dict(d) for d in new_deliverables if isinstance(d, dict)]
    elif isinstance(new_deliverables, str):
        try:
            loaded = yaml.safe_load(new_deliverables)
            if isinstance(loaded, list):
                items_to_compare = [dict(d) for d in loaded if isinstance(d, dict)]
            elif isinstance(loaded, dict) and "deliverables" in loaded:
                items_to_compare = [dict(d) for d in loaded["deliverables"] if isinstance(d, dict)]
        except Exception:
            items_to_compare = []

    added: List[Dict[str, Any]] = []
    modified: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []
    unchanged: List[Dict[str, Any]] = []

    new_ids: Set[str] = set()
    for new_item in items_to_compare:
        nid = str(new_item.get("id", ""))
        if not nid:
            continue
        new_ids.add(nid)
        if nid not in old_by_id:
            added.append(new_item)
        else:
            old_item = old_by_id[nid]
            due_changed = "due" in new_item and str(new_item["due"]) != str(old_item.get("due"))
            title_changed = "title" in new_item and str(new_item["title"]) != str(old_item.get("title"))
            uncertain_changed = "date_uncertain" in new_item and bool(new_item["date_uncertain"]) != bool(old_item.get("date_uncertain"))
            status_changed = (
                "status" in new_item
                and new_item["status"] != old_item.get("status")
            )
            tier_changed = (
                "tier" in new_item
                and new_item["tier"] != old_item.get("tier")
            )

            if due_changed or title_changed or uncertain_changed or status_changed or tier_changed:
                merged = dict(old_item)
                merged.update(new_item)
                modified.append(merged)
            else:
                unchanged.append(old_item)

    for oid, old_item in old_by_id.items():
        if oid not in new_ids:
            dropped_item = dict(old_item)
            dropped_item["status"] = "archived"
            dropped.append(dropped_item)

    return SyllabusDiff(
        project_id=project_id,
        added=added,
        modified=modified,
        dropped=dropped,
        unchanged=unchanged
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
    record_text: str,
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

    if not resolved_type:
        p_str = str(path_obj).replace("\\", "/")
        if "chrysalis/Tasks" in p_str or "Tasks/" in p_str:
            resolved_type = "task"
        elif "Projects" in p_str and path_obj.name == "Roadmap.md":
            resolved_type = "project"
        elif "Slipbox" in p_str:
            resolved_type = "zettel"
        elif "Sources" in p_str:
            resolved_type = "source"

    valid_types = {"task", "project", "zettel", "source"}
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
