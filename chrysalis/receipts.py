"""Local-day eligibility based on saved, hashed results outside synced content."""
from datetime import datetime
import json
import re
import uuid
from zoneinfo import ZoneInfo

from .runtime import atomic_json, digest, state_root
from System.scripts.vault_paths import resolve_runtime_vault


def now_local(timezone, now=None):
    if now is not None and now.tzinfo is None:
        raise ValueError("Receipt timestamps must be timezone-aware")
    return datetime.now(ZoneInfo(timezone)) if now is None else now.astimezone(ZoneInfo(timezone))


def gate(vault, timezone, evening_start, *, state=None, now=None):
    vault = resolve_runtime_vault(vault)
    current = now_local(timezone, now)
    from .daily import configured_timezone
    configured_timezone(vault, timezone)
    if not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", evening_start):
        raise ValueError("Explicit evening start required")
    ledger = state_root(vault, state) / "daily.json"
    rows = json.loads(ledger.read_text()) if ledger.is_file() else []
    reviewed = False
    for row in rows:
        if row.get("stage") not in {"audit", "planning"} or not re.fullmatch(r"[a-f0-9]{64}", str(row.get("result_digest", ""))):
            raise ValueError("Invalid daily result reference")
        stamp = datetime.fromisoformat(row["completed_at"])
        if stamp.utcoffset() != stamp.astimezone(ZoneInfo(timezone)).utcoffset():
            raise ValueError("Invalid daily receipt offset")
        result = state_root(vault, state) / "results" / (row["result_digest"] + ".json")
        if not result.is_file():
            raise ValueError("Daily result missing; do not infer eligibility")
        payload = json.loads(result.read_text())
        if digest(payload) != row["result_digest"] or payload["stage"] != row["stage"] or payload["completed_at"] != row["completed_at"] or not payload.get("result"):
            raise ValueError("Daily result receipt changed")
        if stamp.astimezone(ZoneInfo(timezone)).date() == current.date():
            reviewed = True
    return {"status": "ok", "wake_agent": not reviewed and current.strftime("%H:%M") >= evening_start,
            "reason": "reviewed_today" if reviewed else "eligible" if current.strftime("%H:%M") >= evening_start else "outside_window"}


def begin(vault, timezone, mode, *, state=None, invocation_id=None):
    vault = resolve_runtime_vault(vault)
    from .daily import configured_timezone
    configured_timezone(vault, timezone)
    if mode not in {"morning", "evening", "audit", "staging", "calibration", "check-in", "resume"}:
        raise ValueError("Unknown daily entry mode")
    identity = str(uuid.UUID(invocation_id)) if invocation_id else str(uuid.uuid4())
    target = state_root(vault, state) / "entries" / (identity + ".json")
    if target.is_file():
        entry = json.loads(target.read_text())
        if entry["mode"] != mode:
            raise ValueError("Invocation belongs to another entry mode")
        return {"status": "existing", "invocation_id": identity, "entry": entry}
    atomic_json(target,
                {"mode": mode, "started_at": now_local(timezone).isoformat()})
    return {"status": "entered", "invocation_id": identity}


def save_result(vault, timezone, stage, result, *, state=None, now=None):
    if stage not in {"audit", "planning"} or not isinstance(result, dict) or not result:
        raise ValueError("A meaningful completed audit or planning result is required")
    vault = resolve_runtime_vault(vault)
    external = state_root(vault, state)
    stamp = now_local(timezone, now).isoformat()
    payload = {"stage": stage, "completed_at": stamp, "result": result}
    key = digest(payload)
    atomic_json(external / "results" / (key + ".json"), payload)
    from helpers.records import _advisory_file_lock
    with _advisory_file_lock(external / "daily.json", lock_directory=external):
        rows = json.loads((external / "daily.json").read_text()) if (external / "daily.json").is_file() else []
        rows.append({"stage": stage, "completed_at": stamp, "result_digest": key})
        atomic_json(external / "daily.json", rows)
    return key
