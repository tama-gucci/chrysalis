"""
Google Tasks Optional Integration Helper (helpers/providers/google_tasks.py)

Owns Google Tasks one-way read-only capture discovery, pagination, field normalization,
and mapping into the Chrysalis Ingestion Input Contract v1.0.0 (`structured_task`).
Strictly read-only: importing never completes, deletes, moves, or reschedules
external Google Tasks.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Tuple, Union


GOOGLE_TASKS_INTEGRATION_ID = "google-tasks"
GOOGLE_TASKS_CONTRACT_VERSION = "1.0.0"

GOOGLE_TASKS_CAPABILITIES: Dict[str, Any] = {
    "supports_binary_bytes": False,
    "supports_revision_token": True,
    "supports_pagination": True,
    "supports_incremental_sync": True,
    "supports_subtasks": True,
    "supports_due_date_only": True,
    "supports_due_time_native": False,
    "write_back_supported": False,
    "supported_transports": [
        "mcp",
        "gtasks-mcp",
        "google_tasks_readonly_connector",
        "google_tasks_json_export",
    ],
}

GOOGLE_TASKS_MIDNIGHT_UTC_RE = re.compile(
    r"^([0-9]{4}-[0-9]{2}-[0-9]{2})T00:00:00(?:\.0+)?Z$"
)
DATE_ONLY_RE = re.compile(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})$")
GTASKS_MCP_META_LINE_RE = re.compile(
    r"^\s*\(Due:\s*(?P<due>[^)]*)\)\s*-\s*Notes:\s*(?P<notes>.*?)\s*-\s*ID:\s*(?P<id>\S+)\s*"
    r"-\s*Status:\s*(?P<status>\S+)\s*-\s*URI:\s*(?P<uri>\S+)\s*-\s*Hidden:\s*(?P<hidden>\S+)\s*"
    r"-\s*Parent:\s*(?P<parent>\S+)\s*-\s*Deleted\?:\s*(?P<deleted>\S+)\s*"
    r"-\s*Completed Date:\s*(?P<completed>\S+)\s*-\s*Position:\s*(?P<position>\S+)\s*"
    r"-\s*Updated Date:\s*(?P<updated>\S+)\s*-\s*ETag:\s*(?P<etag>.*?)\s*"
    r"-\s*Links:\s*(?P<links>.*?)\s*-\s*Kind:\s*tasks#task\}\s*$",
    re.DOTALL,
)
GTASKS_URI_LIST_RE = re.compile(r"/lists/([^/]+)/tasks/")


def parse_gtasks_mcp_list_output(
    raw_text: str,
    *,
    collection_id: Optional[str] = None,
    list_title: Optional[str] = None,
    include_completed: bool = False,
) -> Dict[str, Any]:
    """
    Parses the plain-text task list payload emitted by the `gtasks-mcp` MCP server
    (`list` tool) into a canonical Google Tasks items dictionary (`{"status": "ok", "items": [...]}`).
    Handles multi-line task `Notes:` blocks, extracts per-item `collection_id` from the task URI
    before falling back to `collection_id`, and filters out completed/deleted tasks unless
    `include_completed=True`.
    """
    def _opt_str(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        s = val.strip()
        if not s or s.lower() in {"undefined", "null", "not set", "none"}:
            return None
        return s

    raw_lines = str(raw_text or "").splitlines()
    coalesced_lines: List[str] = []
    idx = 0
    while idx < len(raw_lines):
        line = raw_lines[idx]
        if line.lstrip().startswith("(Due:") and not line.rstrip().endswith("Kind: tasks#task}"):
            buf = [line]
            idx += 1
            while idx < len(raw_lines):
                buf.append(raw_lines[idx])
                if raw_lines[idx].rstrip().endswith("Kind: tasks#task}"):
                    idx += 1
                    break
                idx += 1
            coalesced_lines.append("\n".join(buf))
        else:
            coalesced_lines.append(line)
            idx += 1

    items: List[Dict[str, Any]] = []
    pending_title_lines: List[str] = []
    for raw_line in coalesced_lines:
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith("Found ") and stripped.endswith("tasks:"):
            pending_title_lines.clear()
            continue
        m = GTASKS_MCP_META_LINE_RE.match(raw_line)
        if m:
            title = " ".join(pending_title_lines).strip() or "Untitled Task"
            pending_title_lines.clear()
            status_val = _opt_str(m.group("status")) or "needsAction"
            deleted_val = (_opt_str(m.group("deleted")) or "").lower()
            if deleted_val == "true":
                continue
            if not include_completed and status_val.lower() == "completed":
                continue
            uri = _opt_str(m.group("uri"))
            inferred_list_id = None
            if uri:
                m_list = GTASKS_URI_LIST_RE.search(uri)
                if m_list:
                    inferred_list_id = m_list.group(1)
            if not inferred_list_id:
                inferred_list_id = collection_id
            etag_raw = _opt_str(m.group("etag"))
            if etag_raw and len(etag_raw) >= 2 and etag_raw.startswith('"') and etag_raw.endswith('"'):
                etag_raw = etag_raw[1:-1]
            item_dict: Dict[str, Any] = {
                "id": _opt_str(m.group("id")),
                "title": title,
                "notes": _opt_str(m.group("notes")),
                "due": _opt_str(m.group("due")),
                "status": status_val,
                "selfLink": uri,
                "parent": _opt_str(m.group("parent")),
                "completed": _opt_str(m.group("completed")),
                "position": _opt_str(m.group("position")),
                "updated": _opt_str(m.group("updated")),
                "etag": etag_raw,
                "links": [],
            }
            if inferred_list_id:
                item_dict["collection_id"] = inferred_list_id
            if list_title:
                item_dict["collection_title"] = list_title
            items.append(item_dict)
        else:
            pending_title_lines.append(stripped)

    return {
        "status": "ok",
        "transport": "gtasks-mcp",
        "items": items,
    }


def parse_google_tasks_due(
    raw_due: Optional[str],
    *,
    explicit_due_time: Optional[str] = None,
    explicit_due_timezone: Optional[str] = None,
    default_local_offset: str = "-05:00",
) -> Dict[str, Any]:
    """
    Normalizes a Google Tasks `due` field without inventing times for date-only deadlines.
    Google Tasks API stores date-only values as 'YYYY-MM-DDT00:00:00.000Z'.
    Unless an explicit clock time is supplied, due_time and due_at remain None.
    """
    from helpers.mdbase_helper import normalize_deadline_evidence

    if raw_due is None or not str(raw_due).strip():
        return {
            "due": None,
            "due_time": None,
            "due_timezone": None,
            "due_at": None,
            "due_is_date_only": False,
            "date_uncertain": True,
        }

    s = str(raw_due).strip()
    m_mid = GOOGLE_TASKS_MIDNIGHT_UTC_RE.match(s)
    m_date = DATE_ONLY_RE.match(s)

    if (m_mid or m_date) and not explicit_due_time:
        iso_date = m_mid.group(1) if m_mid else m_date.group(1)  # type: ignore[union-attr]
        return {
            "due": iso_date,
            "due_time": None,
            "due_timezone": None,
            "due_at": None,
            "due_is_date_only": True,
            "date_uncertain": False,
        }

    if explicit_due_time:
        base_date = m_mid.group(1) if m_mid else (m_date.group(1) if m_date else s[:10])
        tz_label = explicit_due_timezone or default_local_offset
        norm = normalize_deadline_evidence(
            f"{base_date} {explicit_due_time} {tz_label}",
            default_local_offset=default_local_offset,
        )
        return {
            "due": norm.get("due"),
            "due_time": norm.get("due_time"),
            "due_timezone": norm.get("due_timezone"),
            "due_at": norm.get("due_at"),
            "due_is_date_only": norm.get("due_time") is None,
            "date_uncertain": bool(norm.get("date_uncertain")),
        }

    norm = normalize_deadline_evidence(s, default_local_offset=default_local_offset)
    return {
        "due": norm.get("due"),
        "due_time": norm.get("due_time"),
        "due_timezone": norm.get("due_timezone"),
        "due_at": norm.get("due_at"),
        "due_is_date_only": norm.get("due_time") is None and norm.get("due") is not None,
        "date_uncertain": bool(norm.get("date_uncertain")),
    }


def compute_structured_task_fingerprint(payload: Dict[str, Any]) -> str:
    """
    Computes a deterministic 64-char hex SHA-256 fingerprint over the normalized
    structured task payload fields. Stored strictly in `structured_payload_sha256`
    (never in `sha256`, which is reserved for original binary file bytes).
    """
    canonical = {
        "external_item_id": str(payload.get("external_item_id") or ""),
        "title": str(payload.get("title") or "").strip(),
        "notes": str(payload.get("notes") or "").strip(),
        "due": payload.get("due"),
        "due_time": payload.get("due_time"),
        "due_at": payload.get("due_at"),
        "external_status": str(payload.get("external_status") or "needsAction"),
        "parent_external_id": payload.get("parent_external_id"),
    }
    raw = json.dumps(canonical, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().lower()


def map_google_task_to_contract(
    raw_task: Dict[str, Any],
    *,
    source_alias: str = "quick-capture",
    account_scope: str = "default",
    collection_id: str = "<list-reference>",
    default_local_offset: str = "-05:00",
) -> Dict[str, Any]:
    """
    Normalizes a raw Google Tasks API item into a canonical v1.0.0
    IngestionInputItem (`content_kind: "structured_task"`).
    """
    external_id = str(raw_task.get("id") or raw_task.get("external_item_id") or "").strip()
    if not external_id:
        raise ValueError("Google Tasks item is missing required stable 'id' / 'external_item_id'")

    def _clean_evidence_val(val: str) -> str:
        s = re.sub(r"(?i)</untrusted_document_payload>", "&lt;/untrusted_document_payload&gt;", str(val))
        return s.replace("---", "&#45;&#45;&#45;")

    raw_title = str(raw_task.get("title") or "").strip()
    title = _clean_evidence_val(raw_title)
    notes = raw_task.get("notes")
    notes_str = _clean_evidence_val(str(notes).strip()) if notes is not None else None
    external_status = str(raw_task.get("status") or "needsAction").strip()

    due_info = parse_google_tasks_due(
        raw_task.get("due"),
        explicit_due_time=raw_task.get("due_time"),
        explicit_due_timezone=raw_task.get("due_timezone"),
        default_local_offset=default_local_offset,
    )

    payload_core = {
        "external_item_id": external_id,
        "title": title,
        "notes": notes_str,
        "due": due_info["due"],
        "due_time": due_info["due_time"],
        "due_timezone": due_info["due_timezone"],
        "due_at": due_info["due_at"],
        "due_is_date_only": due_info["due_is_date_only"],
        "date_uncertain": due_info["date_uncertain"],
        "external_status": external_status,
        "completed_at_raw": raw_task.get("completed"),
        "parent_external_id": raw_task.get("parent"),
        "position": raw_task.get("position"),
        "links": list(raw_task.get("links") or []),
        "source_evidence_fields": [
            k
            for k in ("title", "notes", "due", "status", "parent", "links")
            if raw_task.get(k) not in (None, "", [])
        ],
    }

    struct_fp = compute_structured_task_fingerprint(payload_core)
    raw_rev_token = str(
        raw_task.get("etag")
        or raw_task.get("updated")
        or raw_task.get("external_revision")
        or struct_fp
    ).strip()
    if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$", raw_rev_token):
        revision_token = f"rev-{hashlib.sha256(raw_rev_token.encode('utf-8')).hexdigest()[:16]}"
    else:
        revision_token = raw_rev_token

    evidence = [
        {
            "source_field": "title",
            "value": _clean_evidence_val(title),
            "external_item_id": external_id,
        }
    ]
    if due_info["due"] is not None:
        evidence.append({
            "source_field": "due",
            "value": _clean_evidence_val(str(raw_task.get("due"))),
            "normalized_due": due_info["due"],
            "due_is_date_only": due_info["due_is_date_only"],
        })
    if notes_str:
        evidence.append({
            "source_field": "notes",
            "value": _clean_evidence_val(notes_str[:200]),
        })

    effective_collection_id = str(raw_task.get("collection_id") or collection_id)

    return {
        "contract_version": GOOGLE_TASKS_CONTRACT_VERSION,
        "content_kind": "structured_task",
        "source_alias": source_alias,
        "integration": GOOGLE_TASKS_INTEGRATION_ID,
        "account_scope": account_scope,
        "collection_id": effective_collection_id,
        "external_item_id": external_id,
        "revision": {
            "external_revision": revision_token,
            "updated_at": raw_task.get("updated"),
            "etag": raw_task.get("etag"),
        },
        "locator": {
            "original_filename": None,
            "relative_path": None,
            "source_url": raw_task.get("selfLink") or raw_task.get("webViewLink"),
            "parent_external_id": raw_task.get("parent"),
        },
        "fingerprints": {
            "bytes_available": False,
            "sha256": None,
            "normalized_text_sha256": None,
            "structured_payload_sha256": struct_fp,
        },
        "extraction_coverage": {
            "status": "complete" if title else "failed",
            "pages_processed": None,
            "total_pages": None,
            "sections_indexed": [],
            "omissions": [],
            "limitations": ["google_tasks_api_due_is_date_only"],
            "uncertainty_flags": ["missing_due_date"] if due_info["date_uncertain"] else [],
        },
        "evidence": evidence,
        "payload": payload_core,
    }


normalize_google_task_item = map_google_task_to_contract
parse_google_task_due = parse_google_tasks_due



def discover_google_tasks_source(
    source_config: Dict[str, Any],
    *,
    source_alias: str = "quick-capture",
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    synthetic_response: Optional[Dict[str, Any]] = None,
    default_local_offset: str = "-05:00",
    vault_root: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """
    Executes bounded read-only discovery for a configured Google Tasks source alias.
    If no live connector or export/fixture payload is provided, returns explicit
    `operation_unavailable` with `missing_prerequisite: "google-tasks-read-connector"`
    and never fabricates tasks or reports an empty list.
    """
    collection_id = str(
        source_config.get("collection_id")
        or source_config.get("collection")
        or "<list-reference>"
    )
    account_scope = str(source_config.get("account_scope") or "default")
    access_mode = str(source_config.get("access") or "read-only")

    if access_mode != "read-only":
        return {
            "contract_version": GOOGLE_TASKS_CONTRACT_VERSION,
            "source_alias": source_alias,
            "integration": GOOGLE_TASKS_INTEGRATION_ID,
            "account_scope": account_scope,
            "collection_id": collection_id,
            "access_mode": access_mode,
            "discovery_status": "unsupported_operation",
            "capabilities": dict(GOOGLE_TASKS_CAPABILITIES),
            "pagination": {
                "bounded": True,
                "truncated": False,
                "page_size": page_size,
                "items_returned": 0,
                "total_known_items": 0,
                "next_page_token": None,
                "max_depth": 1,
            },
            "items": [],
            "diagnostics": [{
                "code": "write_access_forbidden",
                "severity": "error",
                "message": (
                    f"Google Tasks integration is strictly a one-way read-only capture source "
                    f"(requested access='{access_mode}'). External completion, deletion, or sync is prohibited."
                ),
            }],
        }

    # Check for export_path / fixture_path / mcp_snapshot_path when synthetic_response is not passed directly
    payload_data = synthetic_response
    if payload_data is None:
        export_path = (
            source_config.get("export_path")
            or source_config.get("fixture_path")
            or source_config.get("mcp_snapshot_path")
        )
        if export_path:
            p = Path(str(export_path)).expanduser()
            if not p.is_absolute() and not p.is_file() and vault_root is not None:
                p_vault = (Path(vault_root).resolve() / p).resolve()
                if p_vault.is_file():
                    p = p_vault
            if not p.is_file():
                return {
                    "contract_version": GOOGLE_TASKS_CONTRACT_VERSION,
                    "source_alias": source_alias,
                    "integration": GOOGLE_TASKS_INTEGRATION_ID,
                    "account_scope": account_scope,
                    "collection_id": collection_id,
                    "access_mode": "read-only",
                    "discovery_status": "mount_unavailable",
                    "capabilities": dict(GOOGLE_TASKS_CAPABILITIES),
                    "pagination": {
                        "bounded": True,
                        "truncated": False,
                        "page_size": page_size,
                        "items_returned": 0,
                        "total_known_items": None,
                        "next_page_token": None,
                        "max_depth": 1,
                    },
                    "items": [],
                    "diagnostics": [{
                        "code": "export_file_unavailable",
                        "severity": "error",
                        "message": f"Configured Google Tasks export path does not exist: {p}",
                        "path": str(p),
                    }],
                }
            try:
                raw_text = p.read_text(encoding="utf-8")
                if raw_text.lstrip().startswith("{"):
                    payload_data = json.loads(raw_text)
                else:
                    payload_data = parse_gtasks_mcp_list_output(
                        raw_text,
                        collection_id=collection_id if collection_id != "<list-reference>" else None,
                        include_completed=bool(source_config.get("include_completed", False)),
                    )
            except Exception as e:
                return {
                    "contract_version": GOOGLE_TASKS_CONTRACT_VERSION,
                    "source_alias": source_alias,
                    "integration": GOOGLE_TASKS_INTEGRATION_ID,
                    "account_scope": account_scope,
                    "collection_id": collection_id,
                    "access_mode": "read-only",
                    "discovery_status": "extraction_failed",
                    "capabilities": dict(GOOGLE_TASKS_CAPABILITIES),
                    "pagination": {
                        "bounded": True,
                        "truncated": False,
                        "page_size": page_size,
                        "items_returned": 0,
                        "total_known_items": None,
                        "next_page_token": None,
                        "max_depth": 1,
                    },
                    "items": [],
                    "diagnostics": [{
                        "code": "invalid_google_tasks_json",
                        "severity": "error",
                        "message": f"Failed to parse Google Tasks JSON export: {e}",
                        "path": str(p),
                    }],
                }

    if payload_data is None:
        return {
            "contract_version": GOOGLE_TASKS_CONTRACT_VERSION,
            "source_alias": source_alias,
            "integration": GOOGLE_TASKS_INTEGRATION_ID,
            "account_scope": account_scope,
            "collection_id": collection_id,
            "access_mode": "read-only",
            "discovery_status": "operation_unavailable",
            "missing_prerequisite": "google-tasks-read-connector",
            "capabilities": dict(GOOGLE_TASKS_CAPABILITIES),
            "pagination": {
                "bounded": True,
                "truncated": False,
                "page_size": page_size,
                "items_returned": 0,
                "total_known_items": None,
                "next_page_token": None,
                "max_depth": 1,
            },
            "items": [],
            "diagnostics": [{
                "code": "connector_unavailable",
                "severity": "info",
                "message": (
                    "No live Google Tasks read-only connector or export payload is connected in this environment "
                    "(missing prerequisite: 'google-tasks-read-connector')."
                ),
            }],
        }

    sim_status = str(payload_data.get("status") or "ok")
    if sim_status in {"auth_failure", "mount_unavailable", "operation_unavailable", "unsupported_operation", "permission_denied", "extraction_failed"}:
        return {
            "contract_version": GOOGLE_TASKS_CONTRACT_VERSION,
            "source_alias": source_alias,
            "integration": GOOGLE_TASKS_INTEGRATION_ID,
            "account_scope": account_scope,
            "collection_id": collection_id,
            "access_mode": "read-only",
            "discovery_status": sim_status,
            "capabilities": dict(GOOGLE_TASKS_CAPABILITIES),
            "pagination": {
                "bounded": True,
                "truncated": False,
                "page_size": page_size,
                "items_returned": 0,
                "total_known_items": None,
                "next_page_token": None,
                "max_depth": 1,
            },
            "items": [],
            "diagnostics": list(payload_data.get("diagnostics") or [{
                "code": sim_status,
                "severity": "error",
                "message": str(payload_data.get("message") or f"Google Tasks discovery failed with {sim_status}"),
            }]),
        }

    include_completed = bool(source_config.get("include_completed", False))
    raw_tasks = [
        rt for rt in list(payload_data.get("items") or [])
        if not (isinstance(rt, dict) and str(rt.get("deleted") or "").strip().lower() == "true")
        and (include_completed or not (isinstance(rt, dict) and str(rt.get("status") or "needsAction").strip().lower() == "completed"))
    ]
    total_tasks = len(raw_tasks)
    start_idx = int(page_token) if (page_token and str(page_token).isdigit()) else 0
    effective_page_size = page_size or payload_data.get("page_size")
    if effective_page_size is not None and int(effective_page_size) > 0:
        ps = int(effective_page_size)
        sliced = raw_tasks[start_idx : start_idx + ps]
        next_token = str(start_idx + ps) if (start_idx + ps) < total_tasks else payload_data.get("nextPageToken")
    else:
        sliced = raw_tasks[start_idx:]
        next_token = payload_data.get("nextPageToken") or payload_data.get("next_page_token")

    truncated = bool(next_token is not None or payload_data.get("truncated", False))
    mapped_items: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = list(payload_data.get("diagnostics") or [])

    for idx, rt in enumerate(sliced):
        try:
            mapped_items.append(
                map_google_task_to_contract(
                    rt,
                    source_alias=source_alias,
                    account_scope=account_scope,
                    collection_id=collection_id,
                    default_local_offset=default_local_offset,
                )
            )
        except Exception as e:
            diagnostics.append({
                "code": "task_item_mapping_failed",
                "severity": "error",
                "message": f"Failed to map Google Task at index {idx}: {e}",
            })

    if not mapped_items and diagnostics and any(d.get("severity") == "error" for d in diagnostics):
        d_status = "extraction_failed"
    elif not mapped_items and not truncated:
        d_status = "ok_empty"
    elif truncated:
        d_status = "partial_listing"
    else:
        d_status = "ok_items_available"

    return {
        "contract_version": GOOGLE_TASKS_CONTRACT_VERSION,
        "source_alias": source_alias,
        "integration": GOOGLE_TASKS_INTEGRATION_ID,
        "account_scope": account_scope,
        "collection_id": collection_id,
        "access_mode": "read-only",
        "discovery_status": d_status,
        "capabilities": dict(GOOGLE_TASKS_CAPABILITIES),
        "pagination": {
            "bounded": True,
            "truncated": truncated,
            "page_size": effective_page_size,
            "items_returned": len(mapped_items),
            "total_known_items": total_tasks,
            "next_page_token": next_token,
            "max_depth": 1,
        },
        "items": mapped_items,
        "diagnostics": diagnostics,
    }


parse_google_task_due = parse_google_tasks_due


def reconcile_structured_task_with_vault(vault_root: Union[Path, str], item: Dict[str, Any], **kwargs: Any) -> Dict[str, Any]:
    """Reconciles a v1.0.0 structured_task item against the local vault via draft_structured_task_capture."""
    from helpers.ingestion_contract import draft_structured_task_capture
    return draft_structured_task_capture(vault_root, item, **kwargs)
