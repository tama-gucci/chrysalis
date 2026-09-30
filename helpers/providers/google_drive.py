"""
Google Drive Optional Integration Helper (helpers/providers/google_drive.py)

Owns Google Drive-specific mount resolution, MCP/export payload mapping, bounded
pagination, and translation into the Chrysalis Ingestion Input Contract v1.0.0.
Strictly read-only; never moves, modifies, or deletes remote Google Drive files.
"""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


GOOGLE_DRIVE_INTEGRATION_ID = "google-drive"
GOOGLE_DRIVE_CONTRACT_VERSION = "1.0.0"

GOOGLE_DRIVE_CAPABILITIES: Dict[str, Any] = {
    "supports_binary_bytes": True,
    "supports_exported_text": True,
    "supports_revision_token": True,
    "supports_pagination": True,
    "supports_incremental_sync": True,
    "write_back_supported": False,
    "supported_transports": ["local_mount", "google_drive_mcp_readonly"],
}


def is_google_drive_folder_url(url: Optional[str]) -> bool:
    """Returns True if the URL points to a Google Drive folder container rather than an individual file."""
    if not url:
        return False
    return "/drive/folders/" in str(url).strip()


def resolve_google_drive_host_mount(
    collection_name: str = "Chrysalis-Media-Locker",
    *,
    allow_host_fallback: bool = False,
) -> Tuple[Optional[Path], Optional[Dict[str, Any]]]:
    """
    Resolves a host-mounted Google Drive collection folder when permitted.
    Strictly disabled under pytest or when CHRYSALIS_DISABLE_HOST_FALLBACK=1.
    """
    host_fallback_allowed = (
        allow_host_fallback
        and os.environ.get("CHRYSALIS_DISABLE_HOST_FALLBACK") != "1"
        and "PYTEST_CURRENT_TEST" not in os.environ
    )
    if not host_fallback_allowed:
        return None, None

    env_locker = os.environ.get("CHRYSALIS_MEDIA_LOCKER_PATH")
    if env_locker:
        env_cand = Path(env_locker).expanduser()
        if not env_cand.is_dir():
            return None, {
                "code": "locker_unavailable",
                "severity": "error",
                "message": f"CHRYSALIS_MEDIA_LOCKER_PATH does not exist: {env_cand}",
                "path": str(env_cand),
            }
        return env_cand.resolve(), None

    home = Path.home()
    locker_candidates = [
        Path("G:/My Drive") / collection_name,
        home / "Google Drive" / "My Drive" / collection_name,
        home / "My Drive" / collection_name,
        home / collection_name,
    ]
    for lc in locker_candidates:
        try:
            if lc.is_dir():
                return lc.resolve(), None
        except Exception:
            continue
    return None, None


def map_google_drive_item_to_contract(
    raw_item: Dict[str, Any],
    *,
    source_alias: str = "media",
    account_scope: Optional[str] = None,
    collection_id: str = "<folder-reference>",
) -> Dict[str, Any]:
    """
    Maps a discovered local-mount file descriptor or Google Drive MCP item into
    a versioned 1.0.0 IngestionInputItem (content_kind='file' or 'text').
    Delegates to the provider-neutral `map_filesystem_item_to_contract` helper
    with `integration=GOOGLE_DRIVE_INTEGRATION_ID`.
    """
    from helpers.ingestion_contract import map_filesystem_item_to_contract

    return map_filesystem_item_to_contract(
        raw_item,
        source_alias=source_alias,
        integration=GOOGLE_DRIVE_INTEGRATION_ID,
        account_scope=account_scope,
        collection_id=collection_id,
    )



def discover_google_drive_source(
    vault_root: Union[Path, str],
    source_config: Dict[str, Any],
    *,
    source_alias: str = "media",
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    synthetic_response: Optional[Dict[str, Any]] = None,
    allow_host_fallback: bool = False,
) -> Dict[str, Any]:
    """
    Executes bounded read-only discovery for a configured Google Drive source alias
    and returns a canonical v1.0.0 IngestionDiscoveryEnvelope.
    """
    from helpers.mdbase_helper import discover_media_locker

    collection_id = str(source_config.get("collection") or source_config.get("locker_root") or "<folder-reference>")
    account_scope = source_config.get("account_scope")
    access_mode = str(source_config.get("access") or "read-only")

    if access_mode != "read-only":
        return {
            "contract_version": GOOGLE_DRIVE_CONTRACT_VERSION,
            "source_alias": source_alias,
            "integration": GOOGLE_DRIVE_INTEGRATION_ID,
            "account_scope": account_scope,
            "collection_id": collection_id,
            "access_mode": access_mode,
            "discovery_status": "unsupported_operation",
            "capabilities": dict(GOOGLE_DRIVE_CAPABILITIES),
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
                "message": f"Google Drive integration supports only read-only access (got '{access_mode}').",
            }],
        }

    # Handle explicit synthetic/connector response when supplied
    if synthetic_response is not None:
        sim_status = str(synthetic_response.get("status") or "ok")
        if sim_status in {"auth_failure", "mount_unavailable", "operation_unavailable", "unsupported_operation", "permission_denied", "extraction_failed"}:
            return {
                "contract_version": GOOGLE_DRIVE_CONTRACT_VERSION,
                "source_alias": source_alias,
                "integration": GOOGLE_DRIVE_INTEGRATION_ID,
                "account_scope": account_scope,
                "collection_id": collection_id,
                "access_mode": "read-only",
                "discovery_status": sim_status,
                "capabilities": dict(GOOGLE_DRIVE_CAPABILITIES),
                "pagination": {
                    "bounded": True,
                    "truncated": False,
                    "page_size": page_size,
                    "items_returned": 0,
                    "total_known_items": None,
                    "next_page_token": None,
                    "max_depth": int(source_config.get("max_discovery_depth", 6)),
                },
                "items": [],
                "diagnostics": list(synthetic_response.get("diagnostics") or [{
                    "code": sim_status,
                    "severity": "error",
                    "message": str(synthetic_response.get("message") or f"Google Drive discovery returned {sim_status}"),
                }]),
            }

        raw_items = list(synthetic_response.get("items") or [])
        total_items = len(raw_items)
        start_idx = int(page_token) if (page_token and str(page_token).isdigit()) else 0
        if page_size is not None and page_size > 0:
            sliced = raw_items[start_idx : start_idx + page_size]
            next_token = str(start_idx + page_size) if (start_idx + page_size) < total_items else None
        else:
            sliced = raw_items[start_idx:]
            next_token = synthetic_response.get("next_page_token")
        truncated = bool(next_token is not None or synthetic_response.get("truncated", False))
        mapped_items = [
            map_google_drive_item_to_contract(
                it,
                source_alias=source_alias,
                account_scope=account_scope,
                collection_id=collection_id,
            )
            for it in sliced
        ]
        if not mapped_items and not truncated:
            d_status = "ok_empty"
        elif truncated:
            d_status = "partial_listing"
        else:
            d_status = "ok_items_available"
        return {
            "contract_version": GOOGLE_DRIVE_CONTRACT_VERSION,
            "source_alias": source_alias,
            "integration": GOOGLE_DRIVE_INTEGRATION_ID,
            "account_scope": account_scope,
            "collection_id": collection_id,
            "access_mode": "read-only",
            "discovery_status": d_status,
            "capabilities": dict(GOOGLE_DRIVE_CAPABILITIES),
            "pagination": {
                "bounded": True,
                "truncated": truncated,
                "page_size": page_size,
                "items_returned": len(mapped_items),
                "total_known_items": total_items,
                "next_page_token": next_token,
                "max_depth": int(source_config.get("max_discovery_depth", 6)),
            },
            "items": mapped_items,
            "diagnostics": list(synthetic_response.get("diagnostics") or []),
        }

    # Resolve local mount path or explicit locker root
    mount_path = source_config.get("local_mount_path") or source_config.get("locker_root_path")
    if mount_path is None and collection_id and not collection_id.startswith("<"):
        cand = Path(collection_id).expanduser()
        if cand.is_absolute() or cand.exists():
            mount_path = str(cand)

    discovery_roots = source_config.get("discovery_roots")
    max_depth = int(source_config.get("max_discovery_depth", 6))

    locker_res = discover_media_locker(
        vault_root,
        locker_root=mount_path,
        discovery_roots=discovery_roots,
        max_depth=max_depth,
        allow_host_fallback=allow_host_fallback,
    )

    col_status = locker_res.get("collection_status")
    status_map = {
        "unavailable": "mount_unavailable",
        "unreadable": "permission_denied",
        "empty": "ok_empty",
        "fully_indexed": "ok_fully_indexed",
        "partially_processed": "ok_items_available",
        "unindexed_inputs_present": "ok_items_available",
        "unsupported": "ok_items_available",
    }
    discovery_status = status_map.get(str(col_status), "operation_unavailable")

    raw_files = list(locker_res.get("files") or [])
    from helpers.ingestion_contract import evaluate_provider_file_identity

    has_provider_transition = False
    for f in raw_files:
        ident = evaluate_provider_file_identity(
            vault_root,
            source_alias=source_alias,
            integration=GOOGLE_DRIVE_INTEGRATION_ID,
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

    if has_provider_transition and discovery_status == "ok_fully_indexed":
        discovery_status = "ok_items_available"

    total_files = len(raw_files)
    start_idx = int(page_token) if (page_token and str(page_token).isdigit()) else 0
    if page_size is not None and page_size > 0:
        page_files = raw_files[start_idx : start_idx + page_size]
        next_token = str(start_idx + page_size) if (start_idx + page_size) < total_files else None
    else:
        page_files = raw_files[start_idx:]
        next_token = None

    truncated = next_token is not None
    if truncated and discovery_status in {"ok_items_available", "ok_fully_indexed"}:
        discovery_status = "partial_listing"

    items = [
        map_google_drive_item_to_contract(
            f,
            source_alias=source_alias,
            account_scope=account_scope,
            collection_id=collection_id,
        )
        for f in page_files
    ]

    return {
        "contract_version": GOOGLE_DRIVE_CONTRACT_VERSION,
        "source_alias": source_alias,
        "integration": GOOGLE_DRIVE_INTEGRATION_ID,
        "account_scope": account_scope,
        "collection_id": collection_id,
        "access_mode": "read-only",
        "discovery_status": discovery_status,
        "capabilities": dict(GOOGLE_DRIVE_CAPABILITIES),
        "pagination": {
            "bounded": True,
            "truncated": truncated,
            "page_size": page_size,
            "items_returned": len(items),
            "total_known_items": total_files,
            "next_page_token": next_token,
            "max_depth": max_depth,
        },
        "items": items,
        "raw_discovery": locker_res,
        "diagnostics": list(locker_res.get("diagnostics") or []),
    }


map_drive_item_to_contract = map_google_drive_item_to_contract
