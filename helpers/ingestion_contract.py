"""
Chrysalis Provider-Neutral Ingestion Contract & Orchestration Helper (helpers/ingestion_contract.py)

Implements:
1. Versioned Ingestion Input Contract (v1.0.0) with shared envelope and explicit variants
   (`file`, `text`, `structured_task`).
2. Private runtime source configuration resolution (`ingestion.sources`) with a narrow,
   non-destructive compatibility layer for legacy `ingestion_config` and `--drive`.
3. Untrusted payload quarantine, delimiter neutralization, and anti-control validation.
4. Provider-aware file identity (preserving originals in place and preventing silent
   cross-provider provenance migration assumptions).
5. One-way structured task capture identity (`(integration, account_scope, collection_id, external_item_id)`),
   repeat-import deduplication, local edit & completed-work preservation, conflict proposal
   generation, date-only deadline fidelity, and standalone future-dated inert task policy.
"""

from __future__ import annotations

from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from helpers.mdbase_helper import (
    EMPTY_BYTES_SHA256,
    SHA256_HEX_PATTERN,
    UNTRUSTED_CLOSING_TAG_PATTERN,
    compute_revision,
    evaluate_source_identity,
    normalize_deadline_evidence,
    normalize_extracted_text,
    parse_frontmatter,
    sanitize_untrusted_payload,
    serialize_record,
)
from helpers.providers.google_drive import (
    GOOGLE_DRIVE_CAPABILITIES,
    GOOGLE_DRIVE_INTEGRATION_ID,
    discover_google_drive_source,
)

from helpers.providers.google_tasks import (
    GOOGLE_TASKS_CAPABILITIES,
    GOOGLE_TASKS_INTEGRATION_ID,
    compute_structured_task_fingerprint,
    discover_google_tasks_source,
    map_google_task_to_contract,
    parse_google_tasks_due,
    parse_gtasks_mcp_list_output,
)


def compute_normalized_text_sha256(text: str) -> str:
    """Computes a canonical 64-char hex SHA-256 over normalized UTF-8 text."""
    return hashlib.sha256(normalize_extracted_text(text).encode("utf-8")).hexdigest().lower()


compute_structured_payload_sha256 = compute_structured_task_fingerprint
discover_google_tasks = discover_google_tasks_source
parse_google_task_due = parse_google_tasks_due


INGESTION_CONTRACT_VERSION = "1.0.0"
CONTRACT_VERSION = INGESTION_CONTRACT_VERSION

ALLOWED_CONTENT_KINDS: Set[str] = {"file", "text", "structured_task"}

ALLOWED_DISCOVERY_STATUSES: Set[str] = {
    "ok_empty",
    "ok_fully_indexed",
    "ok_items_available",
    "partial_listing",
    "auth_failure",
    "mount_unavailable",
    "operation_unavailable",
    "unsupported_operation",
    "permission_denied",
    "extraction_failed",
}

ALLOWED_ACCESS_MODES: Set[str] = {"read-only"}

FORBIDDEN_PAYLOAD_CONTROL_KEYS: Set[str] = {
    "integration",
    "source_alias",
    "access_mode",
    "execute_command",
    "override_skill",
    "approve_automatically",
    "bypass_approval_gate",
    "write_back",
}


# =========================================================================
# 1. Private Source Configuration & Compatibility Layer
# =========================================================================

def translate_legacy_ingestion_config(legacy_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    Narrow, non-destructive compatibility translator mapping legacy `ingestion_config`
    fields into the provider-neutral `ingestion` configuration structure.
    Preserves all existing runtime values without mutating or deleting user config.
    """
    if not isinstance(legacy_cfg, dict) or not legacy_cfg:
        return {}

    locker_root = str(legacy_cfg.get("locker_root") or "Chrysalis-Media-Locker")
    local_mount = legacy_cfg.get("local_locker_path")
    discovery_roots = list(legacy_cfg.get("discovery_roots") or ["01-Inbox", "02-Projects"])
    preserve_in_place = bool(legacy_cfg.get("preserve_originals_in_place", True))
    max_depth = int(legacy_cfg.get("max_discovery_depth", 6))
    auto_ingest = bool(legacy_cfg.get("auto_ingest_on_nightly_audit", True))
    local_res = bool(legacy_cfg.get("local_resources_folder_enabled", False))

    return {
        "contract_version": INGESTION_CONTRACT_VERSION,
        "auto_ingest_on_nightly_audit": auto_ingest,
        "local_resources_folder_enabled": local_res,
        "preserve_originals_in_place": preserve_in_place,
        "standalone_future_task_policy": "create_inert_task",
        "default_sources": ["media"],
        "legacy_compatibility_applied": True,
        "sources": {
            "media": {
                "alias": "media",
                "integration": GOOGLE_DRIVE_INTEGRATION_ID,
                "enabled": True,
                "collection": locker_root,
                "local_mount_path": local_mount,
                "drive_inbox_folder": legacy_cfg.get("drive_inbox_folder", f"{locker_root}/01-Inbox"),
                "drive_projects_folder": legacy_cfg.get("drive_projects_folder", f"{locker_root}/02-Projects"),
                "discovery_roots": discovery_roots,
                "access": "read-only",
                "preserve_originals_in_place": preserve_in_place,
                "max_discovery_depth": max_depth,
            }
        },
    }


def resolve_ingestion_config(vault_root: Union[Path, str]) -> Dict[str, Any]:
    """
    Resolves the private runtime ingestion configuration from `<vault>/System/Memory.md`
    (or optional `<vault>/System/Ingestion-Sources.md`).
    - Prefers `ingestion.sources`.
    - Falls back cleanly to `translate_legacy_ingestion_config(ingestion_config)` when only
      legacy configuration is present.
    - Never auto-activates installed integration skills that are not explicitly enabled
      in the user's configuration.
    """
    v_root = Path(vault_root).resolve()
    mem_path = v_root / "System" / "Memory.md"
    opt_sources_path = v_root / "System" / "Ingestion-Sources.md"

    fm: Dict[str, Any] = {}
    if mem_path.is_file():
        try:
            fm, _ = parse_frontmatter(mem_path.read_text(encoding="utf-8"))
        except Exception:
            fm = {}

    if opt_sources_path.is_file():
        try:
            opt_fm, _ = parse_frontmatter(opt_sources_path.read_text(encoding="utf-8"))
            if isinstance(opt_fm.get("ingestion"), dict):
                fm = dict(fm)
                base_ing = dict(fm.get("ingestion")) if isinstance(fm.get("ingestion"), dict) else {}
                base_sources = dict(base_ing.get("sources")) if isinstance(base_ing.get("sources"), dict) else {}
                opt_ing = dict(opt_fm["ingestion"])
                if isinstance(opt_ing.get("sources"), dict):
                    merged_sources = dict(base_sources)
                    for k_alias, v_scfg in opt_ing["sources"].items():
                        if isinstance(v_scfg, dict) and isinstance(merged_sources.get(k_alias), dict):
                            combined_s = dict(merged_sources[k_alias])
                            combined_s.update(v_scfg)
                            merged_sources[k_alias] = combined_s
                        else:
                            merged_sources[k_alias] = v_scfg
                    opt_ing["sources"] = merged_sources
                base_ing.update(opt_ing)
                fm["ingestion"] = base_ing
        except Exception:
            pass

    has_modern_blocks = (
        isinstance(fm.get("ingestion"), dict)
        or isinstance(fm.get("integrations"), dict)
        or (v_root / "System" / "Integrations.md").is_file()
    )
    if has_modern_blocks:
        try:
            from helpers.integration_registry import resolve_integration_config

            int_cfg = resolve_integration_config(v_root)
            bridged_sources = int_cfg.get("bridged_ingestion_sources")
            if isinstance(bridged_sources, dict) and bridged_sources:
                fm = dict(fm)
                base_ing = dict(fm.get("ingestion")) if isinstance(fm.get("ingestion"), dict) else {}
                base_sources = dict(base_ing.get("sources")) if isinstance(base_ing.get("sources"), dict) else {}
                for alias_name, bridged_s in bridged_sources.items():
                    if not isinstance(bridged_s, dict):
                        continue
                    existing_s = dict(base_sources.get(alias_name)) if isinstance(base_sources.get(alias_name), dict) else {}
                    existing_s.update(bridged_s)
                    base_sources[alias_name] = existing_s
                base_ing["sources"] = base_sources
                fm["ingestion"] = base_ing
        except Exception:
            pass

    raw_ingestion = fm.get("ingestion")
    legacy_cfg = fm.get("ingestion_config")

    if isinstance(raw_ingestion, dict) and isinstance(raw_ingestion.get("sources"), dict):
        sources_out: Dict[str, Dict[str, Any]] = {}
        for alias, scfg in raw_ingestion["sources"].items():
            if not isinstance(scfg, dict):
                continue
            norm_s = dict(scfg)
            norm_s["alias"] = str(alias)
            norm_s["integration"] = str(scfg.get("integration") or "").strip()
            raw_access = scfg.get("access") or scfg.get("mode") or "read-only"
            norm_s["access"] = str(raw_access).strip().replace("_", "-")
            col_val = scfg.get("collection")
            if not col_val and isinstance(scfg.get("collection_roots"), list) and scfg["collection_roots"]:
                col_val = scfg["collection_roots"][0]
            if col_val is not None:
                norm_s["collection"] = col_val
            # Sources in ingestion.sources default to enabled: False unless explicitly enabled: true
            norm_s["enabled"] = bool(scfg.get("enabled") is True)
            sources_out[str(alias)] = norm_s

        # Preserve optional legacy path hints onto 'media' without overwriting collection or auto-enabling
        if isinstance(legacy_cfg, dict) and "media" in sources_out:
            m_src = sources_out["media"]
            if not m_src.get("collection") and legacy_cfg.get("locker_root"):
                m_src["collection"] = str(legacy_cfg["locker_root"])
            if m_src.get("local_mount_path") is None and legacy_cfg.get("local_locker_path"):
                m_src["local_mount_path"] = legacy_cfg.get("local_locker_path")
            if "discovery_roots" not in m_src and legacy_cfg.get("discovery_roots"):
                m_src["discovery_roots"] = list(legacy_cfg["discovery_roots"])

        default_sources = list(
            raw_ingestion.get("default_sources")
            or [alias for alias, s in sources_out.items() if s.get("enabled")]
        )

        return {
            "contract_version": str(raw_ingestion.get("contract_version") or INGESTION_CONTRACT_VERSION),
            "auto_ingest_on_nightly_audit": bool(
                raw_ingestion.get(
                    "auto_ingest_on_nightly_audit",
                    legacy_cfg.get("auto_ingest_on_nightly_audit", True) if isinstance(legacy_cfg, dict) else True,
                )
            ),
            "local_resources_folder_enabled": bool(
                raw_ingestion.get(
                    "local_resources_folder_enabled",
                    legacy_cfg.get("local_resources_folder_enabled", False) if isinstance(legacy_cfg, dict) else False,
                )
            ),
            "preserve_originals_in_place": bool(
                raw_ingestion.get(
                    "preserve_originals_in_place",
                    legacy_cfg.get("preserve_originals_in_place", True) if isinstance(legacy_cfg, dict) else True,
                )
            ),
            "standalone_future_task_policy": str(
                raw_ingestion.get("standalone_future_task_policy") or "create_inert_task"
            ),
            "default_sources": default_sources,
            "legacy_compatibility_applied": False,
            "sources": sources_out,
        }

    if isinstance(legacy_cfg, dict) and legacy_cfg:
        return translate_legacy_ingestion_config(legacy_cfg)

    return {
        "contract_version": INGESTION_CONTRACT_VERSION,
        "auto_ingest_on_nightly_audit": True,
        "local_resources_folder_enabled": False,
        "preserve_originals_in_place": True,
        "standalone_future_task_policy": "create_inert_task",
        "default_sources": [],
        "legacy_compatibility_applied": False,
        "sources": {},
    }


def resolve_legacy_command_alias(
    source_alias: Optional[str] = None,
    *,
    legacy_drive_flag: bool = False,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Maps deprecated `--drive` flag to `--source media` outside the core `/ingest` runbook.
    """
    if legacy_drive_flag and not source_alias:
        return "media", {
            "code": "legacy_command_alias_used",
            "severity": "info",
            "message": "Compatibility layer mapped legacy '--drive' command to '--source media'.",
        }
    return source_alias, None


# =========================================================================
# 2. Versioned Contract Validation & Untrusted Payload Security
# =========================================================================

def sanitize_ingestion_item(item: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Quarantines external text fields, neutralizes closing `</untrusted_document_payload>`
    delimiters, and rejects/strips any external payload keys attempting to control
    integration selection or executable behavior.
    """
    diagnostics: List[Dict[str, Any]] = []
    cleaned = json.loads(json.dumps(item, default=str))
    payload = dict(cleaned.get("payload") or {})

    for forbidden_key in sorted(FORBIDDEN_PAYLOAD_CONTROL_KEYS):
        if forbidden_key in payload:
            payload.pop(forbidden_key, None)
            diagnostics.append({
                "code": "untrusted_payload_control_attempt",
                "severity": "warning",
                "field": f"payload.{forbidden_key}",
                "message": (
                    f"External payload attempted to specify control field '{forbidden_key}'; "
                    "neutralized by untrusted payload boundary."
                ),
            })

    for text_field in ("title", "notes", "text_content", "extracted_text"):
        val = payload.get(text_field)
        if isinstance(val, str):
            new_val = val
            if UNTRUSTED_CLOSING_TAG_PATTERN.search(new_val):
                new_val = UNTRUSTED_CLOSING_TAG_PATTERN.sub(
                    "&lt;/untrusted_document_payload&gt;",
                    new_val,
                )
                diagnostics.append({
                    "code": "delimiter_escape_neutralized",
                    "severity": "info",
                    "field": f"payload.{text_field}",
                    "message": f"Neutralized closing quarantine delimiter in payload.{text_field}.",
                })
            if "---" in new_val:
                new_val = new_val.replace("---", "&#45;&#45;&#45;")
                diagnostics.append({
                    "code": "yaml_fence_escape_neutralized",
                    "severity": "info",
                    "field": f"payload.{text_field}",
                    "message": f"Neutralized YAML frontmatter fence sequence in payload.{text_field}.",
                })
            payload[text_field] = new_val

    if isinstance(cleaned.get("evidence"), list):
        for ev in cleaned["evidence"]:
            if isinstance(ev, dict) and isinstance(ev.get("value"), str):
                ev["value"] = UNTRUSTED_CLOSING_TAG_PATTERN.sub(
                    "&lt;/untrusted_document_payload&gt;",
                    ev["value"],
                ).replace("---", "&#45;&#45;&#45;")

    cleaned["payload"] = payload
    if (
        str(cleaned.get("content_kind") or "") == "structured_task"
        and isinstance(cleaned.get("fingerprints"), dict)
        and cleaned["fingerprints"].get("structured_payload_sha256")
    ):
        cleaned["fingerprints"]["structured_payload_sha256"] = compute_structured_task_fingerprint(payload)
    return cleaned, diagnostics


def validate_ingestion_item(item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a single IngestionInputItem against the v1.0.0 contract and enforces
    strict binary `sha256` vs text/structured fingerprint separation.
    """
    diagnostics: List[Dict[str, Any]] = []

    if str(item.get("contract_version") or "") != INGESTION_CONTRACT_VERSION:
        diagnostics.append({
            "code": "unsupported_contract_version",
            "severity": "error",
            "field": "contract_version",
            "message": f"Expected contract_version '{INGESTION_CONTRACT_VERSION}', got '{item.get('contract_version')}'.",
        })

    content_kind = str(item.get("content_kind") or "")
    if content_kind not in ALLOWED_CONTENT_KINDS:
        diagnostics.append({
            "code": "invalid_content_kind",
            "severity": "error",
            "field": "content_kind",
            "message": f"content_kind must be one of {sorted(ALLOWED_CONTENT_KINDS)}, got '{content_kind}'.",
        })

    for req_field in ("source_alias", "integration", "collection_id"):
        if not str(item.get(req_field) or "").strip():
            diagnostics.append({
                "code": "missing_contract_field",
                "severity": "error",
                "field": req_field,
                "message": f"Required contract envelope field '{req_field}' is missing or empty.",
            })

    fps = item.get("fingerprints")
    if not isinstance(fps, dict):
        diagnostics.append({
            "code": "missing_fingerprints",
            "severity": "error",
            "field": "fingerprints",
            "message": "Item must include a 'fingerprints' object.",
        })
        fps = {}

    bytes_available = bool(fps.get("bytes_available", False))
    sha256_val = fps.get("sha256")
    norm_text_sha = fps.get("normalized_text_sha256")
    struct_sha = fps.get("structured_payload_sha256")
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}

    # Enforce the binary hashing law: sha256 means ONLY exact original binary file bytes!
    if sha256_val is not None:
        if content_kind != "file" or not bytes_available:
            diagnostics.append({
                "code": "invalid_fingerprint_masquerade",
                "severity": "error",
                "field": "fingerprints.sha256",
                "message": (
                    "Text or structured-payload fingerprints must not masquerade as original-file "
                    "checksums: 'sha256' must be null when content_kind != 'file' or bytes_available is false."
                ),
            })
        elif not SHA256_HEX_PATTERN.match(str(sha256_val).lower()):
            diagnostics.append({
                "code": "invalid_sha256_format",
                "severity": "error",
                "field": "fingerprints.sha256",
                "message": f"Invalid SHA-256 hex digest: '{sha256_val}'.",
            })
        elif str(sha256_val).lower() == EMPTY_BYTES_SHA256 and int(payload.get("file_size_bytes") or 0) > 0:
            diagnostics.append({
                "code": "empty_bytes_sha256_forbidden",
                "severity": "error",
                "field": "fingerprints.sha256",
                "message": "Empty-bytes SHA-256 placeholder is forbidden when file_size_bytes > 0.",
            })

    if content_kind == "file":
        if bytes_available and not sha256_val:
            diagnostics.append({
                "code": "missing_binary_sha256",
                "severity": "error",
                "field": "fingerprints.sha256",
                "message": "File item with bytes_available=true must provide exact binary 'sha256'.",
            })
        if (
            bytes_available
            and sha256_val
            and norm_text_sha
            and str(sha256_val).lower() == str(norm_text_sha).lower()
            and int(payload.get("file_size_bytes") or 0) > 0
        ):
            diagnostics.append({
                "code": "invalid_fingerprint_masquerade",
                "severity": "error",
                "field": "fingerprints.sha256",
                "message": "File binary 'sha256' must not reuse normalized_text_sha256 when bytes_available=true.",
            })
        if not bytes_available and not norm_text_sha:
            diagnostics.append({
                "code": "missing_text_fingerprint",
                "severity": "error",
                "field": "fingerprints.normalized_text_sha256",
                "message": "File item with bytes_available=false must provide 'normalized_text_sha256'.",
            })
    elif content_kind == "text":
        if not norm_text_sha or not SHA256_HEX_PATTERN.match(str(norm_text_sha).lower()):
            diagnostics.append({
                "code": "missing_text_fingerprint",
                "severity": "error",
                "field": "fingerprints.normalized_text_sha256",
                "message": "Text input item must provide a valid 64-char hex 'normalized_text_sha256'.",
            })
    elif content_kind == "structured_task":
        ext_id = str(item.get("external_item_id") or payload.get("external_item_id") or "").strip()
        if not ext_id:
            diagnostics.append({
                "code": "missing_external_item_id",
                "severity": "error",
                "field": "external_item_id",
                "message": "structured_task input item must provide a stable non-empty 'external_item_id'.",
            })
        if not str(payload.get("title") or "").strip():
            diagnostics.append({
                "code": "missing_task_title",
                "severity": "error",
                "field": "payload.title",
                "message": "structured_task input item must provide a non-empty 'payload.title'.",
            })
        if not struct_sha or not SHA256_HEX_PATTERN.match(str(struct_sha).lower()):
            diagnostics.append({
                "code": "missing_structured_payload_fingerprint",
                "severity": "error",
                "field": "fingerprints.structured_payload_sha256",
                "message": "structured_task input item must provide a valid 64-char hex 'structured_payload_sha256'.",
            })

    errors = [d for d in diagnostics if d.get("severity") == "error"]
    return {
        "valid": len(errors) == 0,
        "diagnostics": diagnostics,
    }


def validate_discovery_envelope(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates a provider's IngestionDiscoveryEnvelope (v1.0.0), including access mode,
    write-back prohibition, discovery status, pagination metadata, and every item.
    """
    diagnostics: List[Dict[str, Any]] = list(envelope.get("diagnostics") or [])

    if str(envelope.get("contract_version") or "") != INGESTION_CONTRACT_VERSION:
        diagnostics.append({
            "code": "unsupported_contract_version",
            "severity": "error",
            "field": "contract_version",
            "message": f"Expected contract_version '{INGESTION_CONTRACT_VERSION}', got '{envelope.get('contract_version')}'.",
        })

    access_mode = str(envelope.get("access_mode") or "")
    if access_mode not in ALLOWED_ACCESS_MODES:
        diagnostics.append({
            "code": "write_access_forbidden",
            "severity": "error",
            "field": "access_mode",
            "message": f"Ingestion access_mode must be 'read-only', got '{access_mode}'.",
        })

    caps = envelope.get("capabilities") or {}
    if caps.get("write_back_supported") is True:
        diagnostics.append({
            "code": "external_write_back_forbidden",
            "severity": "error",
            "field": "capabilities.write_back_supported",
            "message": "External write-back is prohibited in Chrysalis ingestion.",
        })

    d_status = str(envelope.get("discovery_status") or "")
    if d_status not in ALLOWED_DISCOVERY_STATUSES:
        diagnostics.append({
            "code": "invalid_discovery_status",
            "severity": "error",
            "field": "discovery_status",
            "message": f"Invalid discovery_status '{d_status}'. Must be one of {sorted(ALLOWED_DISCOVERY_STATUSES)}.",
        })

    for idx, item in enumerate(envelope.get("items") or []):
        item_val = validate_ingestion_item(item)
        for d in item_val["diagnostics"]:
            d_copy = dict(d)
            d_copy["item_index"] = idx
            diagnostics.append(d_copy)

    errors = [d for d in diagnostics if d.get("severity") == "error"]
    return {
        "valid": len(errors) == 0,
        "discovery_status": d_status,
        "diagnostics": diagnostics,
    }


# =========================================================================
# 3. Provider-Neutral Discovery Dispatch (`--source <alias>` & `--all`)
# =========================================================================

def map_filesystem_item_to_contract(
    raw_item: Dict[str, Any],
    *,
    source_alias: str = "media",
    integration: str = "local-filesystem",
    account_scope: Optional[str] = None,
    collection_id: str = "<folder-reference>",
) -> Dict[str, Any]:
    """
    Provider-neutral mapper converting a discovered filesystem or export descriptor
    into a versioned 1.0.0 IngestionInputItem (content_kind='file' or 'text').
    Preserves strict binary sha256 vs normalized_text_sha256 separation.
    """
    filename = str(raw_item.get("filename") or raw_item.get("name") or "untitled")
    rel_path = raw_item.get("relative_path") or filename
    source_url = raw_item.get("source_url") or raw_item.get("webViewLink")
    external_id = str(
        raw_item.get("external_item_id")
        or raw_item.get("file_id")
        or raw_item.get("id")
        or rel_path
    )
    mime_type = str(raw_item.get("mime_type") or raw_item.get("mimeType") or "application/octet-stream")
    size_bytes = int(raw_item.get("size_bytes") or raw_item.get("file_size_bytes") or 0)

    raw_bytes: Optional[bytes] = raw_item.get("raw_bytes")
    sha256_val: Optional[str] = raw_item.get("sha256")
    bytes_available = bool(raw_item.get("bytes_available", sha256_val is not None or raw_bytes is not None))
    if raw_bytes is not None and not sha256_val:
        sha256_val = hashlib.sha256(raw_bytes).hexdigest().lower()
        bytes_available = True
        size_bytes = len(raw_bytes)

    if not bytes_available:
        sha256_val = None

    extracted_text = raw_item.get("extracted_text") or raw_item.get("text_content")
    norm_text_sha: Optional[str] = raw_item.get("normalized_text_sha256")
    if extracted_text is not None and not norm_text_sha:
        norm_text_sha = hashlib.sha256(
            normalize_extracted_text(str(extracted_text)).encode("utf-8")
        ).hexdigest().lower()

    content_kind = "file" if (bytes_available or raw_item.get("content_kind") == "file" or raw_item.get("path")) else "text"
    if content_kind == "text":
        bytes_available = False
        sha256_val = None

    ext_cov = dict(raw_item.get("extraction_coverage") or {})
    if not ext_cov:
        if not raw_item.get("readable", True):
            cov_status = "failed"
        elif not raw_item.get("supported", True):
            cov_status = "unsupported"
        else:
            cov_status = "complete"
        ext_cov = {
            "status": cov_status,
            "pages_processed": raw_item.get("estimated_pages"),
            "total_pages": raw_item.get("estimated_pages"),
            "sections_indexed": [],
            "omissions": [],
            "limitations": [] if raw_item.get("supported", True) else ["unsupported_binary_format"],
            "uncertainty_flags": [],
        }
    elif "status" not in ext_cov:
        ext_cov["status"] = "partial" if ext_cov.get("omissions") else "complete"

    return {
        "contract_version": INGESTION_CONTRACT_VERSION,
        "content_kind": content_kind,
        "source_alias": source_alias,
        "integration": integration,
        "account_scope": account_scope,
        "collection_id": collection_id,
        "external_item_id": external_id,
        "revision": {
            "external_revision": str(
                raw_item.get("external_revision")
                or raw_item.get("headRevisionId")
                or raw_item.get("md5Checksum")
                or sha256_val
                or norm_text_sha
                or ""
            )
            or None,
            "updated_at": raw_item.get("modifiedTime") or raw_item.get("updated_at"),
            "etag": raw_item.get("etag"),
        },
        "locator": {
            "original_filename": filename,
            "relative_path": str(rel_path).replace("\\", "/") if rel_path else None,
            "source_url": source_url,
            "local_path": raw_item.get("path"),
            "parent_external_id": raw_item.get("parent_id"),
        },
        "fingerprints": {
            "bytes_available": bytes_available,
            "sha256": sha256_val,
            "normalized_text_sha256": norm_text_sha,
            "structured_payload_sha256": None,
        },
        "extraction_coverage": ext_cov,
        "evidence": list(raw_item.get("evidence_anchors") or raw_item.get("evidence") or []),
        "payload": {
            "mime_type": mime_type,
            "file_size_bytes": size_bytes,
            "format_kind": raw_item.get("format_kind", "file"),
            "location_category": raw_item.get("location_category", "unclassified_inbox"),
            "material_role": raw_item.get("material_role", "deliverable_instruction"),
            "ingestion_outcome": raw_item.get("ingestion_outcome", "extracted"),
            "extracted_text": extracted_text,
            "auto_create_project": raw_item.get("auto_create_project", True),
            "auto_materialize_tasks": raw_item.get("auto_materialize_tasks", True),
            "folder_context": raw_item.get("folder_context"),
            "identity": raw_item.get("identity"),
            "index_state": raw_item.get("index_state"),
        },
    }


def discover_mounted_filesystem_source(
    vault_root: Union[Path, str],
    source_config: Dict[str, Any],
    *,
    source_alias: str,
    integration: str = "local-filesystem",
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generic provider-neutral filesystem collection reader that can serve mounted
    folders from any provider (Nextcloud, Syncthing, SMB, local folders, etc.)
    without Google Drive assumptions.
    """
    from helpers.mdbase_helper import discover_media_locker

    collection_id = str(source_config.get("collection") or source_config.get("local_mount_path") or "")
    access_mode = str(source_config.get("access") or "read-only")
    if access_mode != "read-only":
        return {
            "contract_version": INGESTION_CONTRACT_VERSION,
            "source_alias": source_alias,
            "integration": integration,
            "account_scope": source_config.get("account_scope"),
            "collection_id": collection_id,
            "access_mode": access_mode,
            "discovery_status": "unsupported_operation",
            "capabilities": {
                "supports_binary_bytes": True,
                "supports_revision_token": True,
                "supports_pagination": True,
                "supports_incremental_sync": True,
                "write_back_supported": False,
            },
            "pagination": {
                "bounded": True,
                "truncated": False,
                "page_size": page_size,
                "items_returned": 0,
                "total_known_items": 0,
                "next_page_token": None,
                "max_depth": int(source_config.get("max_discovery_depth", 6)),
            },
            "items": [],
            "diagnostics": [{
                "code": "write_access_forbidden",
                "severity": "error",
                "message": f"Integration '{integration}' requires read-only access.",
            }],
        }

    raw_mount = source_config.get("local_mount_path") or collection_id
    mount_path = (
        None
        if (not raw_mount or (str(raw_mount).startswith("<") and str(raw_mount).endswith(">")))
        else raw_mount
    )
    locker_res = discover_media_locker(
        vault_root,
        locker_root=mount_path,
        discovery_roots=source_config.get("discovery_roots"),
        max_depth=int(source_config.get("max_discovery_depth", 6)),
        allow_host_fallback=False,
        integration=integration,
    )
    status_map = {
        "unavailable": "mount_unavailable",
        "unreadable": "permission_denied",
        "empty": "ok_empty",
        "fully_indexed": "ok_fully_indexed",
        "partially_processed": "ok_items_available",
        "unindexed_inputs_present": "ok_items_available",
        "unsupported": "ok_items_available",
    }
    d_status = status_map.get(str(locker_res.get("collection_status")), "operation_unavailable")
    raw_files = list(locker_res.get("files") or [])
    has_provider_transition = False
    for f in raw_files:
        ident = evaluate_provider_file_identity(
            vault_root,
            source_alias=source_alias,
            integration=integration,
            collection_id=collection_id,
            external_item_id=f.get("external_item_id") or f.get("relative_path") or f.get("filename"),
            precomputed_sha256=f.get("sha256"),
            source_url=f.get("source_url"),
            original_filename=f.get("filename"),
            relative_path=f.get("relative_path"),
        )
        if ident.get("provider_scope_changed"):
            has_provider_transition = True
            f["identity"] = ident
            f["index_state"] = "provider_transition_pending"
            f["ingestion_outcome"] = "updated_existing"

    if has_provider_transition and d_status == "ok_fully_indexed":
        d_status = "ok_items_available"

    total_files = len(raw_files)
    start_idx = int(page_token) if (page_token and str(page_token).isdigit()) else 0
    if page_size is not None and page_size > 0:
        page_files = raw_files[start_idx : start_idx + page_size]
        next_token = str(start_idx + page_size) if (start_idx + page_size) < total_files else None
    else:
        page_files = raw_files[start_idx:]
        next_token = None
    truncated = next_token is not None
    if truncated and d_status in {"ok_items_available", "ok_fully_indexed"}:
        d_status = "partial_listing"

    items: List[Dict[str, Any]] = []
    for f in page_files:
        mapped = map_filesystem_item_to_contract(
            f,
            source_alias=source_alias,
            integration=integration,
            account_scope=source_config.get("account_scope"),
            collection_id=collection_id,
        )
        items.append(mapped)


    return {
        "contract_version": INGESTION_CONTRACT_VERSION,
        "source_alias": source_alias,
        "integration": integration,
        "account_scope": source_config.get("account_scope"),
        "collection_id": collection_id,
        "access_mode": "read-only",
        "discovery_status": d_status,
        "capabilities": {
            "supports_binary_bytes": True,
            "supports_revision_token": True,
            "supports_pagination": True,
            "supports_incremental_sync": True,
            "write_back_supported": False,
        },
        "pagination": {
            "bounded": True,
            "truncated": truncated,
            "page_size": page_size,
            "items_returned": len(items),
            "total_known_items": total_files,
            "next_page_token": next_token,
            "max_depth": int(source_config.get("max_discovery_depth", 6)),
        },
        "items": items,
        "diagnostics": list(locker_res.get("diagnostics") or []),
    }


def discover_configured_source(
    vault_root: Union[Path, str],
    source_alias: str,
    *,
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    synthetic_responses: Optional[Dict[str, Dict[str, Any]]] = None,
    allow_host_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Resolves `<source_alias>` in `<vault>/System/Memory.md` and dispatches to the
    configured integration adapter (`google-drive`, `google-tasks`, `local-filesystem`, etc.).
    Fails closed if `<source_alias>` is unknown or disabled.
    """
    v_root = Path(vault_root).resolve()
    cfg = resolve_ingestion_config(v_root)
    sources = cfg.get("sources") or {}

    if source_alias not in sources:
        return {
            "contract_version": INGESTION_CONTRACT_VERSION,
            "source_alias": source_alias,
            "integration": "unconfigured",
            "account_scope": None,
            "collection_id": "",
            "access_mode": "read-only",
            "discovery_status": "operation_unavailable",
            "error_code": "source_alias_not_configured",
            "capabilities": {"write_back_supported": False},
            "pagination": {
                "bounded": True,
                "truncated": False,
                "page_size": page_size,
                "items_returned": 0,
                "total_known_items": None,
                "next_page_token": None,
                "max_depth": 0,
            },
            "items": [],
            "diagnostics": [{
                "code": "source_alias_not_configured",
                "severity": "error",
                "message": (
                    f"Source alias '{source_alias}' is not configured in System/Memory.md "
                    f"(configured aliases: {sorted(sources.keys())})."
                ),
            }],
        }

    source_cfg = sources[source_alias]
    integration = str(source_cfg.get("integration") or "").strip()
    if not source_cfg.get("enabled", True):
        return {
            "contract_version": INGESTION_CONTRACT_VERSION,
            "source_alias": source_alias,
            "integration": integration or "unknown",
            "account_scope": source_cfg.get("account_scope"),
            "collection_id": str(source_cfg.get("collection") or ""),
            "access_mode": str(source_cfg.get("access") or "read-only"),
            "discovery_status": "operation_unavailable",
            "error_code": "source_disabled",
            "capabilities": {"write_back_supported": False},
            "pagination": {
                "bounded": True,
                "truncated": False,
                "page_size": page_size,
                "items_returned": 0,
                "total_known_items": None,
                "next_page_token": None,
                "max_depth": 0,
            },
            "items": [],
            "diagnostics": [{
                "code": "source_disabled",
                "severity": "error",
                "message": f"Source alias '{source_alias}' (integration '{integration}') is disabled in configuration.",
            }],
        }

    syn_resp = (synthetic_responses or {}).get(source_alias)

    if integration == GOOGLE_DRIVE_INTEGRATION_ID:
        return discover_google_drive_source(
            v_root,
            source_cfg,
            source_alias=source_alias,
            page_size=page_size,
            page_token=page_token,
            synthetic_response=syn_resp,
            allow_host_fallback=allow_host_fallback,
        )

    if integration == GOOGLE_TASKS_INTEGRATION_ID:
        return discover_google_tasks_source(
            source_cfg,
            source_alias=source_alias,
            page_size=page_size,
            page_token=page_token,
            synthetic_response=syn_resp,
            vault_root=v_root,
        )

    if integration in {"local-filesystem", "mounted-folder", "filesystem"} or (
        source_cfg.get("local_mount_path") and syn_resp is None
    ):
        return discover_mounted_filesystem_source(
            v_root,
            source_cfg,
            source_alias=source_alias,
            integration=integration or "local-filesystem",
            page_size=page_size,
            page_token=page_token,
        )

    if syn_resp is not None and isinstance(syn_resp.get("envelope"), dict):
        env = dict(syn_resp["envelope"])
        env["source_alias"] = source_alias
        env["integration"] = integration
        return env

    return {
        "contract_version": INGESTION_CONTRACT_VERSION,
        "source_alias": source_alias,
        "integration": integration,
        "account_scope": source_cfg.get("account_scope"),
        "collection_id": str(source_cfg.get("collection") or ""),
        "access_mode": str(source_cfg.get("access") or "read-only"),
        "discovery_status": "unsupported_operation",
        "error_code": "unsupported_integration",
        "capabilities": {"write_back_supported": False},
        "pagination": {
            "bounded": True,
            "truncated": False,
            "page_size": page_size,
            "items_returned": 0,
            "total_known_items": None,
            "next_page_token": None,
            "max_depth": 0,
        },
        "items": [],
        "diagnostics": [{
            "code": "unsupported_integration",
            "severity": "error",
            "message": f"Integration '{integration}' for source alias '{source_alias}' has no registered adapter.",
        }],
    }


def discover_all_configured_sources(
    vault_root: Union[Path, str],
    *,
    page_size: Optional[int] = None,
    synthetic_responses: Optional[Dict[str, Dict[str, Any]]] = None,
    allow_host_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Executes discovery across all enabled sources in `ingestion.sources` in deterministic order.
    Never automatically activates installed integration skills that are disabled or unconfigured.
    """
    v_root = Path(vault_root).resolve()
    cfg = resolve_ingestion_config(v_root)
    sources = cfg.get("sources") or {}
    enabled_aliases = [alias for alias, scfg in sources.items() if scfg.get("enabled", False)]

    envelopes: Dict[str, Dict[str, Any]] = {}
    for alias in enabled_aliases:
        envelopes[alias] = discover_configured_source(
            v_root,
            alias,
            page_size=page_size,
            synthetic_responses=synthetic_responses,
            allow_host_fallback=allow_host_fallback,
        )

    return {
        "contract_version": INGESTION_CONTRACT_VERSION,
        "vault": str(v_root),
        "enabled_sources": enabled_aliases,
        "skipped_disabled_sources": [alias for alias, scfg in sources.items() if not scfg.get("enabled", False)],
        "envelopes": envelopes,
    }


# =========================================================================
# 4. Provider-Aware File Identity & Provenance
# =========================================================================

def evaluate_provider_file_identity(
    vault_root: Union[Path, str],
    *,
    source_alias: str,
    integration: str,
    collection_id: str,
    external_item_id: Optional[str] = None,
    raw_bytes: Optional[bytes] = None,
    precomputed_sha256: Optional[str] = None,
    extracted_text: Optional[str] = None,
    source_url: Optional[str] = None,
    original_filename: Optional[str] = None,
    relative_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates file identity across sessions and providers.
    - Preserves `exact_duplicate`, `changed_version`, `renamed_or_moved`, and `incomplete_prior_ingestion`.
    - Enforces the provider-transition invariant: if a file with identical binary `sha256` was
      previously ingested under a different `integration` or `source_alias`, Chrysalis does NOT
      silently imply that remote provenance or URLs have migrated; it flags `provider_scope_changed: True`
      and preserves historical source provenance in `previous_sources`.
    """
    v_root = Path(vault_root).resolve()
    base_ident = evaluate_source_identity(
        v_root,
        raw_bytes=raw_bytes,
        precomputed_sha256=precomputed_sha256,
        extracted_text=extracted_text,
        source_url=source_url,
        original_filename=original_filename,
        relative_path=relative_path,
    )
    base_ident["source_alias"] = source_alias
    base_ident["integration"] = integration
    base_ident["collection_id"] = collection_id
    base_ident["external_item_id"] = external_item_id
    base_ident["provider_scope_changed"] = False

    existing_rel = base_ident.get("existing_path")
    if existing_rel:
        existing_file = v_root / str(existing_rel)
        if existing_file.is_file():
            try:
                efm, _ = parse_frontmatter(existing_file.read_text(encoding="utf-8"))
                prev_integration = efm.get("integration")
                prev_alias = efm.get("source_alias")
                if not prev_integration and efm.get("source_url") and "drive.google.com" in str(efm.get("source_url")):
                    prev_integration = GOOGLE_DRIVE_INTEGRATION_ID
                if prev_integration and prev_integration != integration:
                    base_ident["provider_scope_changed"] = True
                    base_ident["previous_integration"] = prev_integration
                    base_ident["previous_source_alias"] = prev_alias
                    # Never silently carry over a provider-specific URL to a new provider unless explicitly supplied
                    if source_url is None:
                        base_ident["source_url"] = None
                        base_ident["preserved_prior_source_url"] = efm.get("source_url")
                    base_ident["provenance_action"] = "record_provider_transition_preserve_prior_provenance"
            except Exception:
                pass

    return base_ident


# =========================================================================
# 5. Structured Task Capture Identity, Deduplication & Conflict Proposals
# =========================================================================

def _slugify(text: str, max_len: int = 48) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].strip("-") or "captured-task"


def evaluate_task_capture_identity(
    vault_root: Union[Path, str],
    *,
    integration: str,
    account_scope: Optional[str],
    collection_id: str,
    external_item_id: str,
    external_revision: Optional[str],
    structured_payload_sha256: str,
    incoming_title: str,
    incoming_due: Optional[str],
    incoming_notes: Optional[str],
) -> Dict[str, Any]:
    """
    Evaluates a structured task capture item against `TaskNotes/Tasks/*.md` and `TaskNotes/Archive/*.md`.
    - Matches strictly by `(external_integration, external_account_scope, external_collection_id, external_item_id)`.
    - Never collapses distinct tasks because `title` or `notes` match.
    - Detects repeated imports (`exact_duplicate`) via `external_revision` / `external_payload_sha256`.
    - Preserves `done` and `archived` local states (`completed_locally_preserved`).
    - Detects local edits (`user_modified` or diverged local fields) and surfaces conflicting external
      changes as review proposals (`conflict_with_local_edits`).
    """
    v_root = Path(vault_root).resolve()
    norm_acct = str(account_scope or "default").strip()
    norm_col = str(collection_id or "default").strip()
    norm_ext_id = str(external_item_id).strip()

    search_dirs = [
        (v_root / "TaskNotes" / "Tasks", False),
        (v_root / "TaskNotes" / "Archive", True),
    ]

    for tdir, is_archive_dir in search_dirs:
        if not tdir.is_dir():
            continue
        for tf in sorted(tdir.glob("*.md")):
            if tf.name == "example-task.md" or tf.name.startswith("."):
                continue
            try:
                raw_doc = tf.read_text(encoding="utf-8")
                fm, body = parse_frontmatter(raw_doc)
            except Exception:
                continue

            tf_int = str(fm.get("external_integration") or "").strip()
            tf_acct = str(fm.get("external_account_scope") or "default").strip()
            tf_col = str(fm.get("external_collection_id") or "default").strip()
            tf_ext_id = str(fm.get("external_item_id") or "").strip()

            if not tf_ext_id:
                continue

            if (tf_int, tf_acct, tf_col, tf_ext_id) != (integration, norm_acct, norm_col, norm_ext_id):
                continue

            rel_path = tf.relative_to(v_root).as_posix()
            disk_rev = compute_revision(tf)
            local_status = str(fm.get("status") or "todo")
            stored_ext_rev = str(fm.get("external_revision") or "").strip() or None
            stored_payload_sha = str(fm.get("external_payload_sha256") or "").strip().lower() or None

            local_title = str(fm.get("title") or "").strip()
            local_due = str(fm.get("due")) if fm.get("due") is not None else None
            has_local_edits = bool(
                fm.get("user_modified") is True
                or local_status == "in-progress"
                or fm.get("scheduled") is not None
                or fm.get("googleCalendarEventId") is not None
                or bool(fm.get("linked_zettels"))
                or fm.get("project_ref") is not None
                or fm.get("location") is not None
                or fm.get("coordinates") is not None
                or fm.get("route_estimate") is not None
                or fm.get("travel_policy") is not None
                or bool(fm.get("external_conflict_flag"))
                or _has_local_body_or_frontmatter_edits(fm, body)
            )

            # Check if title or due was locally edited relative to what we have on disk
            if not has_local_edits and stored_payload_sha is not None:
                src_ev_meta = _extract_source_evidence_from_body(body)
                current_local_fp = compute_structured_task_fingerprint({
                    "external_item_id": norm_ext_id,
                    "title": local_title,
                    "notes": _extract_captured_notes_from_body(body),
                    "due": local_due,
                    "due_time": fm.get("due_time"),
                    "due_at": fm.get("due_at"),
                    "external_status": str(src_ev_meta.get("external_status") or "needsAction"),
                    "parent_external_id": src_ev_meta.get("parent_external_id"),
                })
                if current_local_fp != stored_payload_sha:
                    has_local_edits = True

            # 1. Completed or archived local tasks are NEVER reopened or overwritten
            if is_archive_dir or local_status in {"done", "archived"}:
                return {
                    "match_status": "completed_locally_preserved",
                    "is_duplicate": True,
                    "existing_task_path": rel_path,
                    "existing_revision": disk_rev,
                    "local_status": local_status,
                    "has_local_edits": has_local_edits,
                    "preserve_completed": True,
                    "action": "preserve_completed_do_not_reopen",
                }

            # 2. Exact repeat import (unchanged revision, payload fingerprint, or already-recorded conflict proposal)
            existing_conflict = fm.get("external_conflict_proposal")
            conflict_payload_sha = (
                str(existing_conflict.get("external_payload_sha256") or "").strip().lower()
                if isinstance(existing_conflict, dict)
                else None
            )
            if (
                (stored_payload_sha and stored_payload_sha == structured_payload_sha256.lower())
                or (conflict_payload_sha and conflict_payload_sha == structured_payload_sha256.lower())
                or (
                    stored_ext_rev
                    and external_revision
                    and stored_ext_rev == str(external_revision).strip()
                    and stored_payload_sha == structured_payload_sha256.lower()
                )
            ):
                return {
                    "match_status": "exact_duplicate",
                    "is_duplicate": True,
                    "existing_task_path": rel_path,
                    "existing_revision": disk_rev,
                    "local_status": local_status,
                    "has_local_edits": has_local_edits,
                    "already_recorded_conflict": bool(
                        conflict_payload_sha and conflict_payload_sha == structured_payload_sha256.lower()
                    ),
                    "action": "skip_duplicate_task",
                }

            # 3. External task changed: surface conflict if local task was edited by user/runtime
            if has_local_edits:
                return {
                    "match_status": "conflict_with_local_edits",
                    "is_duplicate": False,
                    "existing_task_path": rel_path,
                    "existing_revision": disk_rev,
                    "existing_frontmatter": fm,
                    "existing_body": body,
                    "local_status": local_status,
                    "has_local_edits": True,
                    "action": "propose_conflict_review_preserve_local",
                }

            return {
                "match_status": "changed_external_task",
                "is_duplicate": False,
                "existing_task_path": rel_path,
                "existing_revision": disk_rev,
                "existing_frontmatter": fm,
                "existing_body": body,
                "local_status": local_status,
                "has_local_edits": False,
                "action": "propose_external_update",
            }

    return {
        "match_status": "new_task",
        "is_duplicate": False,
        "existing_task_path": None,
        "existing_revision": None,
        "action": "create_new_captured_task",
    }


def _extract_source_evidence_from_body(body: str) -> Dict[str, Any]:
    m = re.search(r"\*\*Source Evidence\*\*:\s*`(\{.*?\})`", body)
    if not m:
        return {}
    try:
        loaded = json.loads(m.group(1))
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _extract_framework_defaults_from_body(body: str) -> Dict[str, Any]:
    m = re.search(r"\*\*Framework Defaults\*\*:\s*`(\{.*?\})`", body)
    if not m:
        return {}
    try:
        loaded = json.loads(m.group(1))
        return loaded if isinstance(loaded, dict) else {}
    except Exception:
        return {}


def _has_local_body_or_frontmatter_edits(fm: Dict[str, Any], body: str) -> bool:
    """
    Detects whether local Chrysalis frontmatter fields (`title`, `due`, `priority`,
    `urgency_tier`, `modality`, `timeEstimate`, `energy`, `friction`, `micro_chunked`,
    `tags`) or Markdown body text outside `<untrusted_document_payload>` / `Source Evidence`
    differ from baseline capture template defaults.
    """
    src_ev = _extract_source_evidence_from_body(body)
    defaults = _extract_framework_defaults_from_body(body)

    if src_ev:
        if "title" in src_ev and str(fm.get("title") or "").strip() != str(src_ev.get("title") or "").strip():
            return True
        if "due" in src_ev:
            ev_due = str(src_ev["due"]) if src_ev.get("due") is not None else None
            loc_due = str(fm["due"]) if fm.get("due") is not None else None
            if loc_due != ev_due:
                return True

    expected_priority = str(defaults.get("priority") or "normal")
    expected_urgency = int(defaults.get("urgency_tier") if defaults.get("urgency_tier") is not None else 2)
    expected_modality = str(defaults.get("modality") or "administrative")
    expected_est = int(defaults.get("timeEstimate") if defaults.get("timeEstimate") is not None else 45)
    expected_energy = str(defaults.get("energy") or "medium")
    expected_friction = str(defaults.get("friction") or "low")
    expected_chunked = bool(defaults.get("micro_chunked") if "micro_chunked" in defaults else False)

    if str(fm.get("priority") or "normal") != expected_priority:
        return True
    try:
        if int(fm.get("urgency_tier", 2)) != expected_urgency:
            return True
    except (TypeError, ValueError):
        return True
    if str(fm.get("modality") or "administrative") != expected_modality:
        return True
    try:
        if int(fm.get("timeEstimate", 45)) != expected_est:
            return True
    except (TypeError, ValueError):
        return True
    if str(fm.get("energy") or "medium") != expected_energy:
        return True
    if str(fm.get("friction") or "low") != expected_friction:
        return True
    if bool(fm.get("micro_chunked", False)) != expected_chunked:
        return True

    local_tags = list(fm.get("tags") or ["task"])
    if "tags" in defaults and isinstance(defaults["tags"], list):
        if local_tags != list(defaults["tags"]):
            return True
    else:
        if set(local_tags) - {"task"}:
            return True

    expected_h1_title = str(src_ev.get("title") or fm.get("title") or "").strip()
    expected_h1_line = f"# {expected_h1_title}"
    seen_primary_h1 = False

    # Inspect Markdown body outside the quarantine block and standard template headings
    stripped_body = re.sub(
        r"<untrusted_document_payload[^>]*>.*?</untrusted_document_payload>",
        "",
        body,
        flags=re.DOTALL,
    )
    for raw_line in stripped_body.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if not seen_primary_h1 and line == expected_h1_line:
            seen_primary_h1 = True
            continue
        if line in {
            "## Captured Source Evidence vs. Framework Defaults",
            "## Quarantined Capture Payload",
        }:
            continue
        if re.match(r"^-\s+\*\*(?:Source Evidence|Framework Defaults)\*\*:\s*`.*`$", line):
            continue
        return True

    return False


def _extract_captured_notes_from_body(body: str) -> str:
    m = re.search(
        r"<untrusted_document_payload[^>]*>\s*(.*?)\s*</untrusted_document_payload>",
        body,
        re.DOTALL,
    )
    if not m:
        return ""
    raw_inner = m.group(1).strip()
    # Strip leading 'Title: ...\nNotes:' wrapper without splitting on 'Notes:' inside Title
    m_notes = re.search(r"(?:^|\n)Notes:[ \t]*(.*)\Z", raw_inner, re.DOTALL)
    if m_notes:
        return m_notes.group(1).strip()
    return raw_inner


def classify_standalone_task_horizon(
    due_date_str: Optional[str],
    *,
    date_uncertain: bool = False,
    reference_date: Optional[date] = None,
    horizon_days: int = 14,
) -> str:
    """
    Classifies a standalone captured task's horizon bucket (`overdue`, `imminent`,
    `uncertain`, `future`).
    Standalone future-dated tasks (`due > today + 14d`) are classified as `future`
    and materialized as inert tasks (`scheduled: null`) rather than silently dropped.
    """
    if date_uncertain or not due_date_str:
        return "uncertain"
    ref = reference_date or date.today()
    try:
        d = date.fromisoformat(str(due_date_str)[:10])
    except ValueError:
        return "uncertain"
    delta = (d - ref).days
    if delta < 0:
        return "overdue"
    if delta <= horizon_days:
        return "imminent"
    return "future"


def draft_structured_task_capture(
    vault_root: Union[Path, str],
    item: Dict[str, Any],
    *,
    reference_date: Optional[date] = None,
    horizon_days: int = 14,
    default_local_offset: str = "-05:00",
    default_pillar_tag: Optional[str] = None,
    allocated_paths: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Drafts Chrysalis records (`Sources/<id>.md` provenance + `TaskNotes/Tasks/<slug>.md`)
    from a validated `structured_task` IngestionInputItem.
    - Distinguishes source evidence from framework defaults.
    - Preserves date-only deadlines (`due_time: null`, `due_at: null`).
    - Never collapses distinct external IDs with identical titles.
    - Preserves completed work and local edits, surfacing conflicts as review proposals.
    """
    v_root = Path(vault_root).resolve()
    ref_date = reference_date or date.today()
    now_iso = f"{ref_date.isoformat()}T09:00:00{default_local_offset}"

    sanitized_item, san_diags = sanitize_ingestion_item(item)
    val = validate_ingestion_item(sanitized_item)
    if not val["valid"]:
        return {
            "valid": False,
            "outcome": "failed",
            "diagnostics": san_diags + val["diagnostics"],
            "records": [],
        }

    source_alias = str(sanitized_item["source_alias"])
    integration = str(sanitized_item["integration"])
    account_scope = str(sanitized_item.get("account_scope") or "default")
    collection_id = str(sanitized_item["collection_id"])
    external_id = str(sanitized_item["external_item_id"])
    rev_obj = sanitized_item.get("revision") or {}
    external_rev = rev_obj.get("external_revision")
    fps = sanitized_item["fingerprints"]
    struct_sha = str(fps["structured_payload_sha256"])
    payload = sanitized_item["payload"]

    title = str(payload.get("title") or "").strip()
    notes = payload.get("notes")
    due_str = payload.get("due")
    due_time = payload.get("due_time")
    due_tz = payload.get("due_timezone")
    due_at = payload.get("due_at")
    date_uncertain = bool(payload.get("date_uncertain", due_str is None))
    external_status = str(payload.get("external_status") or "needsAction")

    ident = evaluate_task_capture_identity(
        v_root,
        integration=integration,
        account_scope=account_scope,
        collection_id=collection_id,
        external_item_id=external_id,
        external_revision=external_rev,
        structured_payload_sha256=struct_sha,
        incoming_title=title,
        incoming_due=due_str,
        incoming_notes=notes,
    )

    if ident["match_status"] == "exact_duplicate":
        return {
            "valid": True,
            "outcome": "skipped_duplicate",
            "match_status": "exact_duplicate",
            "already_recorded_conflict": bool(ident.get("already_recorded_conflict")),
            "has_local_edits": bool(ident.get("has_local_edits")),
            "existing_task_path": ident["existing_task_path"],
            "records": [],
            "diagnostics": san_diags,
        }

    if ident["match_status"] == "completed_locally_preserved":
        return {
            "valid": True,
            "outcome": "skipped_duplicate",
            "match_status": "completed_locally_preserved",
            "existing_task_path": ident["existing_task_path"],
            "records": [],
            "diagnostics": san_diags + [{
                "code": "completed_task_preserved",
                "severity": "info",
                "path": ident["existing_task_path"],
                "message": (
                    f"Local task '{ident['existing_task_path']}' is already {ident['local_status']}; "
                    "preserved local state without reopening."
                ),
            }],
        }

    # Build deterministic source provenance ID keyed by (integration, account_scope, collection_id, external_id)
    id_seed = f"{integration}:{account_scope}:{collection_id}:{external_id}"
    short_id_hash = hashlib.sha256(id_seed.encode("utf-8")).hexdigest()[:8]
    source_slug = f"capture-{_slugify(integration, 16)}-{_slugify(external_id, 20)}-{short_id_hash}"
    source_rel_path = f"Sources/{source_slug}.md"
    source_abs_path = v_root / source_rel_path
    source_if_rev = compute_revision(source_abs_path) if source_abs_path.is_file() else None

    horizon_bucket = classify_standalone_task_horizon(
        due_str,
        date_uncertain=date_uncertain,
        reference_date=ref_date,
        horizon_days=horizon_days,
    )

    # Determine task file path
    if ident.get("existing_task_path"):
        task_rel_path = str(ident["existing_task_path"])
        task_if_rev = ident.get("existing_revision")
    else:
        date_prefix = (due_str or ref_date.isoformat()).replace("-", "")[:8]
        base_slug = _slugify(title, 36)
        cand_rel = f"TaskNotes/Tasks/{date_prefix}-{base_slug}.md"
        used = allocated_paths if allocated_paths is not None else set()
        if (v_root / cand_rel).exists() or cand_rel in used:
            cand_rel = f"TaskNotes/Tasks/{date_prefix}-{base_slug}-{short_id_hash[:6]}.md"
            collision_idx = 2
            while (v_root / cand_rel).exists() or cand_rel in used:
                cand_rel = f"TaskNotes/Tasks/{date_prefix}-{base_slug}-{short_id_hash[:6]}-{collision_idx}.md"
                collision_idx += 1
        if allocated_paths is not None:
            allocated_paths.add(cand_rel)
        task_rel_path = cand_rel
        task_if_rev = None

    task_wikilink = f"[[{task_rel_path[:-3]}]]"
    source_wikilink = f"[[Sources/{source_slug}]]"

    tags = ["task"]
    if default_pillar_tag:
        tags.append(default_pillar_tag)

    # Separate source evidence from Chrysalis framework defaults
    source_evidence_summary = {
        "external_item_id": external_id,
        "external_revision": external_rev,
        "title": title,
        "due": due_str,
        "due_time": due_time,
        "notes_present": bool(notes),
        "external_status": external_status,
        "parent_external_id": payload.get("parent_external_id"),
    }
    framework_defaults_applied = {
        "priority": "normal",
        "urgency_tier": 2,
        "modality": "administrative",
        "timeEstimate": 45,
        "energy": "medium",
        "friction": "low",
        "micro_chunked": False,
        "tags": tags,
        "scheduled": None,
        "project_ref": None,
        "linked_zettels": [],
    }

    quarantined_payload_body = sanitize_untrusted_payload(
        f"Title: {title}\nNotes: {notes or ''}",
        source_id=source_slug,
        sha256_digest=None,
        mime_type="application/json",
    )

    if ident["match_status"] == "conflict_with_local_edits":
        existing_fm = dict(ident["existing_frontmatter"])
        existing_body = str(ident["existing_body"])
        conflict_proposal = {
            "detected_at": now_iso,
            "source_alias": source_alias,
            "integration": integration,
            "external_item_id": external_id,
            "external_revision": external_rev,
            "external_payload_sha256": struct_sha,
            "proposed_changes": {
                "title": title,
                "due": due_str,
                "due_time": due_time,
                "due_at": due_at,
                "notes": notes,
            },
            "preserved_local_values": {
                "title": existing_fm.get("title"),
                "due": existing_fm.get("due"),
                "scheduled": existing_fm.get("scheduled"),
                "status": existing_fm.get("status"),
                "priority": existing_fm.get("priority"),
                "urgency_tier": existing_fm.get("urgency_tier"),
                "modality": existing_fm.get("modality"),
                "timeEstimate": existing_fm.get("timeEstimate"),
                "energy": existing_fm.get("energy"),
                "friction": existing_fm.get("friction"),
                "micro_chunked": existing_fm.get("micro_chunked"),
                "tags": existing_fm.get("tags"),
                "googleCalendarEventId": existing_fm.get("googleCalendarEventId"),
                "project_ref": existing_fm.get("project_ref"),
                "linked_zettels": existing_fm.get("linked_zettels"),
                "location": existing_fm.get("location"),
                "coordinates": existing_fm.get("coordinates"),
                "route_estimate": existing_fm.get("route_estimate"),
                "travel_policy": existing_fm.get("travel_policy"),
            },
        }
        existing_fm["review_required"] = True
        existing_fm["external_conflict_flag"] = True
        existing_fm["external_conflict_proposal"] = conflict_proposal
        existing_fm["review_notes"] = (
            f"External task '{external_id}' changed in '{source_alias}' (rev={external_rev}), "
            "but local edits exist; local values preserved pending human review."
        )
        if not existing_fm.get("source_ref"):
            existing_fm["source_ref"] = source_wikilink
        task_fm = existing_fm
        task_body = existing_body
        outcome_label = "updated_existing"
    elif ident["match_status"] == "changed_external_task":
        existing_fm = dict(ident["existing_frontmatter"])
        existing_fm["title"] = title
        existing_fm["due"] = due_str
        existing_fm["due_time"] = due_time
        existing_fm["due_timezone"] = due_tz
        existing_fm["due_at"] = due_at
        existing_fm["date_uncertain"] = date_uncertain
        existing_fm["horizon_bucket"] = horizon_bucket
        existing_fm["external_revision"] = str(external_rev) if external_rev else None
        existing_fm["external_payload_sha256"] = struct_sha
        existing_fm["external_conflict_flag"] = False
        existing_fm["external_conflict_proposal"] = None
        existing_fm["source_ref"] = source_wikilink
        # Strictly preserve scheduled=None during ingest (or existing null), calendar ID, and links
        existing_fm["scheduled"] = None
        task_fm = existing_fm
        task_body = (
            f"# {title}\n\n"
            f"## Captured Source Evidence vs. Framework Defaults\n"
            f"- **Source Evidence**: `{json.dumps(source_evidence_summary, sort_keys=True)}`\n"
            f"- **Framework Defaults**: `{json.dumps(framework_defaults_applied, sort_keys=True)}`\n\n"
            f"## Quarantined Capture Payload\n"
            f"{quarantined_payload_body}\n"
        )
        outcome_label = "updated_existing"
    else:
        task_status = "done" if external_status == "completed" else "todo"

        task_fm = {
            "type": "task",
            "title": title,
            "status": task_status,
            "dateCreated": now_iso,
            "created": now_iso,
            "due": due_str,
            "due_time": due_time,
            "due_timezone": due_tz,
            "due_at": due_at,
            "scheduled": None,
            "priority": "normal",
            "urgency_tier": 2,
            "modality": "administrative",
            "timeEstimate": 45,
            "energy": "medium",
            "friction": "low",
            "micro_chunked": False,
            "tags": tags,
            "linked_zettels": [],
            "project_ref": None,
            "deliverable_id": None,
            "source_ref": source_wikilink,
            "evidence_ref": f"{integration}:{collection_id}:{external_id}",
            "horizon_bucket": horizon_bucket,
            "review_required": bool(date_uncertain or horizon_bucket == "overdue"),
            "review_notes": (
                "Standalone future-dated capture retained as inert task (scheduled: null)."
                if horizon_bucket == "future"
                else ("No due date supplied by capture source." if date_uncertain else None)
            ),
            "googleCalendarEventId": None,
            "date_uncertain": date_uncertain,
            "external_source_alias": source_alias,
            "external_integration": integration,
            "external_account_scope": account_scope,
            "external_collection_id": collection_id,
            "external_item_id": external_id,
            "external_revision": str(external_rev) if external_rev else None,
            "external_payload_sha256": struct_sha,
            "external_conflict_flag": False,
            "external_conflict_proposal": None,
            "user_modified": False,
        }
        task_body = (
            f"# {title}\n\n"
            f"## Captured Source Evidence vs. Framework Defaults\n"
            f"- **Source Evidence**: `{json.dumps(source_evidence_summary, sort_keys=True)}`\n"
            f"- **Framework Defaults**: `{json.dumps(framework_defaults_applied, sort_keys=True)}`\n\n"
            f"## Quarantined Capture Payload\n"
            f"{quarantined_payload_body}\n"
        )
        outcome_label = "extracted"

    source_fm = {
        "type": "source",
        "id": source_slug,
        "title": f"Task Capture: {title}",
        "source_type": "other",
        "sha256": None,
        "bytes_available": False,
        "normalized_text_sha256": None,
        "structured_payload_sha256": struct_sha,
        "source_alias": source_alias,
        "integration": integration,
        "collection_id": collection_id,
        "external_item_id": external_id,
        "external_revision": str(external_rev) if external_rev else None,
        "original_filename": f"{integration}-{external_id}.json",
        "relative_path": None,
        "previous_paths": [],
        "location_category": "unclassified_inbox",
        "material_role": "deliverable_instruction",
        "ingestion_outcome": outcome_label,
        "extraction_coverage": sanitized_item.get("extraction_coverage"),
        "evidence_anchors": sanitized_item.get("evidence") or [],
        "file_size_bytes": 0,
        "mime_type": "application/json",
        "source_url": (sanitized_item.get("locator") or {}).get("source_url"),
        "captured_date": now_iso,
        "ingestion_status": "processed",
        "supersedes": None,
        "linked_projects": [],
        "extracted_projects": [],
        "linked_zettels": [],
        "extracted_zettels": [],
        "extracted_tasks": [task_wikilink],
    }
    source_body = (
        f"# Task Capture: {title}\n\n"
        f"## Provenance Metadata\n"
        f"- **Source Alias**: `{source_alias}`\n"
        f"- **Integration**: `{integration}`\n"
        f"- **Collection ID**: `{collection_id}`\n"
        f"- **External Item ID**: `{external_id}`\n"
        f"- **Structured Payload SHA-256**: `{struct_sha}` (`bytes_available: false`, `sha256: null`)\n\n"
        f"## Quarantined Content\n"
        f"{quarantined_payload_body}\n"
    )

    records = [
        {
            "path": task_rel_path,
            "type": "task",
            "if_revision": task_if_rev,
            "frontmatter": task_fm,
            "body": task_body,
        },
        {
            "path": source_rel_path,
            "type": "source",
            "if_revision": source_if_rev,
            "frontmatter": source_fm,
            "body": source_body,
        },
    ]

    return {
        "valid": True,
        "outcome": outcome_label,
        "match_status": ident["match_status"],
        "has_local_edits": bool(ident.get("has_local_edits")),
        "task_path": task_rel_path,
        "source_path": source_rel_path,
        "horizon_bucket": horizon_bucket,
        "source_evidence": source_evidence_summary,
        "framework_defaults": framework_defaults_applied,
        "records": records,
        "diagnostics": san_diags,
    }



def build_ingestion_proposal_from_envelope(
    vault_root: Union[Path, str],
    envelope: Dict[str, Any],
    *,
    proposal_id: Optional[str] = None,
    reference_date: Optional[date] = None,
    horizon_days: int = 14,
    default_local_offset: str = "-05:00",
    default_pillar_tag: Optional[str] = None,
    allocated_paths: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Converts a provider's v1.0.0 IngestionDiscoveryEnvelope (containing `file`, `text`,
    and/or `structured_task` items) into a unified Chrysalis ingestion proposal ready
    for `prevalidate_ingestion_proposal` -> human approval -> `apply_ingestion_proposal`.
    """
    v_root = Path(vault_root).resolve()
    ref_date = reference_date or date.today()
    now_iso = f"{ref_date.isoformat()}T09:00:00{default_local_offset}"
    env_val = validate_discovery_envelope(envelope)
    diagnostics: List[Dict[str, Any]] = list(env_val["diagnostics"])

    if not env_val["valid"]:
        return {
            "proposal_id": proposal_id or f"ingest-{envelope.get('source_alias', 'batch')}",
            "valid_envelope": False,
            "discovery_status": envelope.get("discovery_status"),
            "records": [],
            "outcomes": [],
            "diagnostics": diagnostics,
        }

    records: List[Dict[str, Any]] = []
    outcomes: List[Dict[str, Any]] = []
    shared_allocated_paths: Set[str] = allocated_paths if allocated_paths is not None else set()
    source_alias = str(envelope.get("source_alias") or "direct-share")
    integration = str(envelope.get("integration") or "session-share")
    collection_id = str(envelope.get("collection_id") or "default")

    for item in envelope.get("items") or []:
        ckind = str(item.get("content_kind"))
        if ckind == "structured_task":
            draft = draft_structured_task_capture(
                v_root,
                item,
                reference_date=ref_date,
                horizon_days=horizon_days,
                default_local_offset=default_local_offset,
                default_pillar_tag=default_pillar_tag,
                allocated_paths=shared_allocated_paths,
            )
            diagnostics.extend(draft.get("diagnostics") or [])
            records.extend(draft.get("records") or [])
            item_col_id = str(item.get("collection_id") or collection_id)
            outcomes.append({
                "input_path": f"{integration}:{item_col_id}:{item.get('external_item_id')}",
                "external_item_id": item.get("external_item_id"),
                "content_kind": "structured_task",
                "outcome": draft.get("outcome", "extracted"),
                "match_status": draft.get("match_status"),
                "already_recorded_conflict": bool(draft.get("already_recorded_conflict")),
                "has_local_edits": bool(draft.get("has_local_edits")),
                "task_path": draft.get("task_path"),
            })
        elif ckind in {"file", "text"}:
            san_item, san_diags = sanitize_ingestion_item(item)
            diagnostics.extend(san_diags)
            loc = san_item.get("locator") or {}
            fps = san_item.get("fingerprints") or {}
            payload = san_item.get("payload") or {}
            fname = str(loc.get("original_filename") or san_item.get("external_item_id") or "document.md")
            rel_p = loc.get("relative_path")
            src_url = loc.get("source_url")
            sha_val = fps.get("sha256")
            bytes_avail = bool(fps.get("bytes_available", False))
            norm_text_sha = fps.get("normalized_text_sha256")
            extracted_text = str(payload.get("extracted_text") or payload.get("text_content") or "")

            ident = evaluate_provider_file_identity(
                v_root,
                source_alias=source_alias,
                integration=integration,
                collection_id=collection_id,
                external_item_id=san_item.get("external_item_id"),
                precomputed_sha256=sha_val,
                extracted_text=extracted_text if extracted_text else None,
                source_url=src_url,
                original_filename=fname,
                relative_path=rel_p,
            )

            m_status = ident["match_status"]
            if m_status == "exact_duplicate" and not ident.get("provider_scope_changed"):
                outcomes.append({
                    "input_path": rel_p or fname,
                    "content_kind": ckind,
                    "outcome": "skipped_duplicate",
                    "match_status": m_status,
                })
                continue

            short_h = (sha_val or norm_text_sha or hashlib.sha256(fname.encode("utf-8")).hexdigest())[:8]
            existing_id_cand = str(ident["existing_source_id"]) if ident.get("existing_source_id") else None
            if (
                existing_id_cand
                and f"Sources/{existing_id_cand}.md" not in shared_allocated_paths
                and (
                    m_status in {"renamed_or_moved", "incomplete_prior_ingestion"}
                    or ident.get("provider_scope_changed")
                )
            ):
                source_slug = existing_id_cand
            else:
                source_slug = f"src-{_slugify(Path(fname).stem, 28)}-{short_h}"
                if existing_id_cand and not ident.get("supersedes"):
                    ident["supersedes"] = f"[[Sources/{existing_id_cand}]]"

            source_rel_path = f"Sources/{source_slug}.md"
            shared_allocated_paths.add(source_rel_path)
            source_abs_path = v_root / source_rel_path
            source_if_rev = compute_revision(source_abs_path) if source_abs_path.is_file() else None
            existing_src_fm: Dict[str, Any] = {}
            if source_abs_path.is_file():
                try:
                    existing_src_fm, _ = parse_frontmatter(source_abs_path.read_text(encoding="utf-8"))
                except Exception:
                    existing_src_fm = {}

            is_update_existing = bool(m_status == "renamed_or_moved" or ident.get("provider_scope_changed"))
            outcome_val = str(
                payload.get("ingestion_outcome")
                or ("updated_existing" if is_update_existing else "extracted")
            )
            if is_update_existing and outcome_val == "extracted":
                outcome_val = "updated_existing"

            quarantined_body = sanitize_untrusted_payload(
                extracted_text or f"Metadata record for {fname}",
                source_id=source_slug,
                sha256_digest=sha_val,
                mime_type=str(payload.get("mime_type") or "text/markdown"),
            )
            prev_paths = list(ident.get("previous_paths") or existing_src_fm.get("previous_paths") or [])
            old_rel_p = existing_src_fm.get("relative_path")
            if old_rel_p and old_rel_p != rel_p and old_rel_p not in prev_paths:
                prev_paths.append(str(old_rel_p))
            source_fm = {
                "type": "source",
                "id": source_slug,
                "title": str(payload.get("title") or existing_src_fm.get("title") or Path(fname).stem),
                "source_type": str(payload.get("source_type") or existing_src_fm.get("source_type") or "pdf"),
                "sha256": sha_val if bytes_avail else None,
                "bytes_available": bytes_avail,
                "normalized_text_sha256": norm_text_sha,
                "structured_payload_sha256": None,
                "source_alias": source_alias,
                "integration": integration,
                "collection_id": collection_id,
                "external_item_id": str(san_item.get("external_item_id") or fname),
                "external_revision": (san_item.get("revision") or {}).get("external_revision"),
                "original_filename": fname,
                "relative_path": rel_p,
                "previous_paths": prev_paths,
                "location_category": payload.get("location_category", "unclassified_inbox"),
                "material_role": payload.get("material_role", "deliverable_instruction"),
                "ingestion_outcome": outcome_val,
                "extraction_coverage": san_item.get("extraction_coverage"),
                "evidence_anchors": san_item.get("evidence") or [],
                "file_size_bytes": int(payload.get("file_size_bytes") or existing_src_fm.get("file_size_bytes") or 0),
                "mime_type": str(payload.get("mime_type") or existing_src_fm.get("mime_type") or "text/markdown"),
                "source_url": ident.get("source_url"),
                "captured_date": now_iso,
                "ingestion_status": "processed" if outcome_val == "extracted" else "extracted",
                "supersedes": ident.get("supersedes") or existing_src_fm.get("supersedes"),
                "linked_projects": list(existing_src_fm.get("linked_projects") or []),
                "extracted_projects": list(existing_src_fm.get("extracted_projects") or []),
                "linked_zettels": list(existing_src_fm.get("linked_zettels") or []),
                "extracted_zettels": list(existing_src_fm.get("extracted_zettels") or []),
                "extracted_tasks": list(existing_src_fm.get("extracted_tasks") or []),
            }
            if ident.get("provider_scope_changed"):
                prior_list = list(existing_src_fm.get("previous_sources") or [])
                prior_entry = {
                    "integration": ident.get("previous_integration"),
                    "source_alias": ident.get("previous_source_alias"),
                    "source_url": ident.get("preserved_prior_source_url"),
                }
                if prior_entry not in prior_list:
                    prior_list.append(prior_entry)
                source_fm["previous_sources"] = prior_list

            records.append({
                "path": source_rel_path,
                "type": "source",
                "if_revision": source_if_rev,
                "frontmatter": source_fm,
                "body": f"# {source_fm['title']}\n\n{quarantined_body}\n",
            })
            outcomes.append({
                "input_path": rel_p or fname,
                "content_kind": ckind,
                "outcome": outcome_val,
                "match_status": m_status,
                "provider_scope_changed": ident.get("provider_scope_changed", False),
                "source_path": source_rel_path,
            })

    return {
        "proposal_id": proposal_id or f"ingest-{source_alias}-{ref_date.strftime('%Y%m%d')}",
        "valid_envelope": True,
        "source_alias": source_alias,
        "integration": integration,
        "discovery_status": envelope.get("discovery_status"),
        "records": records,
        "outcomes": outcomes,
        "diagnostics": diagnostics,
    }


def compute_file_sha256(data_or_path: Union[bytes, str, Path]) -> str:
    """Computes exact 64-char lowercase hex SHA-256 of original binary file bytes."""
    raw = data_or_path if isinstance(data_or_path, bytes) else Path(data_or_path).read_bytes()
    return hashlib.sha256(raw).hexdigest().lower()


validate_ingestion_batch = validate_discovery_envelope
resolve_ingestion_sources = resolve_ingestion_config
