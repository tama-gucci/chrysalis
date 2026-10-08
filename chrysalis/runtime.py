"""Reviewed changes, external receipts, and strict record persistence.

This is a cooperating local writer, not a filesystem or distributed sandbox.
The operator approval command must not be exposed as an agent tool.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone

from helpers import records
from System.scripts.vault_paths import resolve_runtime_vault, vault_path, native_path

VERSION = "1"
MAX_REQUEST_BYTES = 4 * 1024 * 1024
MAX_RECORDS = 500
PLUGIN_FIELDS = {
    "timeEntries", "pomodoros", "recurrence", "recurrenceAnchor", "complete_instances",
    "skipped_instances", "reminders", "blockedBy", "blocking", "contexts", "projects",
    "tn_role", "googleCalendarEventId", "googleCalendarId",
    "recurrence_anchor", "recurrence_parent", "occurrence_date", "materialization",
    "next_trigger", "template", "horizons", "attachments", "totalTrackedTime",
    "completedDate", "icsEventId", "customProperties", "isBlocked", "isBlocking", "hasSubtasks", "sortOrder",
    "archived", "occurrence_materialization", "occurrence_next_trigger", "occurrence_template",
    "occurrence_past_horizon", "occurrence_future_horizon",
    "tasknotes_manual_order",
    "dateModified",
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def state_root(vault, explicit=None):
    selected = explicit or os.environ.get("CHRYSALIS_STATE_ROOT")
    if not selected or not Path(selected).is_absolute():
        raise ValueError("Select an absolute external CHRYSALIS_STATE_ROOT")
    path = Path(selected).resolve()
    package = Path(__file__).resolve().parents[1]
    for forbidden in (Path(vault).resolve(), package):
        candidate, boundary = native_path(path), native_path(forbidden)
        if candidate == boundary or boundary in candidate.parents:
            raise ValueError("Execution state must remain outside vault and package")
    for parent in (Path(selected), *Path(selected).parents):
        if parent.is_symlink() or (hasattr(parent, "is_junction") and parent.is_junction()):
            raise ValueError("Execution state cannot traverse links or junctions")
    identity = json.loads((Path(vault) / ".chrysalis-vault.json").read_text(encoding="utf-8"))["vault_id"]
    if not re.fullmatch(r"[a-z0-9-]{8,80}", identity):
        raise ValueError("Invalid vault identity")
    return native_path(path / identity)


def schema_for(relative):
    if relative.startswith("TaskNotes/Tasks/") or relative.startswith("TaskNotes/Archive/"):
        return "task"
    if relative.startswith("Projects/") and relative.endswith("/Roadmap.md"):
        return "project"
    if relative.startswith("Slipbox/"):
        return "zettel"
    if relative.startswith("Sources/"):
        return "source"
    if relative.startswith("System/") and len(Path(relative).parts) == 2:
        return "system_state"
    if relative.startswith("Daily/"):
        return "daily_note"
    if re.fullmatch(r"Environments/[a-z][a-z0-9-]{0,47}\.md", relative):
        return "system_state"
    raise ValueError("Only authoritative Markdown collections can be changed")


def check_record(vault, item, *, resume=False):
    relative = item.get("path", "")
    if not isinstance(relative, str) or "\\" in relative or not relative.endswith(".md"):
        raise ValueError("Use a relative Markdown path with forward slashes")
    path = native_path(vault_path(vault, relative))
    kind = schema_for(relative)
    document = item.get("document")
    if not isinstance(document, str):
        raise ValueError("A complete proposed document is required")
    # Hash the exact UTF-8 post-image. Never normalize a reviewed document on apply.
    expected = records.compute_revision(document.encode("utf-8"))
    current = records.compute_revision(path) if path.is_file() else None
    if current != item.get("if_revision") and not (resume and current == expected):
        raise ValueError("stale_revision: refresh the entire document")
    validation = records.validate_record(path, document, type_name=kind, collection_dir=vault)
    if not validation.valid:
        raise ValueError("invalid_record: " + ", ".join(d.code for d in validation.diagnostics))
    old = records.parse_frontmatter(path.read_text(encoding="utf-8"))[0] if path.is_file() else {}
    new = validation.frontmatter
    from .daily import read, local_stamp
    timezone_name = read(vault, "System/Memory.md")[0].get("user_profile", {}).get("timezone")
    if relative == "System/Memory.md":
        timezone_name = new.get("user_profile", {}).get("timezone")
        from zoneinfo import ZoneInfo
        ZoneInfo(timezone_name)
        for modality in ("analytical", "kinetic", "synthesis", "administrative"):
            multiplier = new.get("cognitive_modality_defaults", {}).get(modality, {}).get("multiplier")
            if not isinstance(multiplier, (int, float)) or isinstance(multiplier, bool) or not .2 <= multiplier <= 2:
                raise ValueError("invalid_modality_multiplier")
    for field in ("dateCreated", "created", "dateModified", "due_at", "last_updated", "captured_date", "scheduled", "startedAt", "completedAt", "wake_time"):
        value = new.get(field)
        if kind == "task" and field == "dateModified" and field in old:
            if value != old[field]:
                raise ValueError("protected_plugin_timestamp: dateModified")
            continue
        if isinstance(value, str) and "T" in value:
            local_stamp(value, timezone_name)
    if kind == "daily_note":
        date_name = Path(relative).stem
        if new.get("date") and new["date"] != date_name:
            raise ValueError("daily_date_mismatch")
        if new.get("wake_time") and local_stamp(new["wake_time"], timezone_name).date().isoformat() != date_name:
            raise ValueError("daily_wake_date_mismatch")
        intervals = []
        for block in new.get("blocks", []):
            start, end = local_stamp(block["start"], timezone_name), local_stamp(block["end"], timezone_name)
            if end <= start or start.date().isoformat() != date_name or end.date().isoformat() != date_name:
                raise ValueError("invalid_daily_interval")
            if any(start < b and end > a for a, b in intervals):
                raise ValueError("overlapping_daily_intervals")
            intervals.append((start, end))
        for field in ("pomodoros", "timeEntries", "customProperties"):
            if field in old and field not in new:
                raise ValueError("plugin_field_removed: " + field)
    if kind == "task":
        for field in PLUGIN_FIELDS:
            if field in old and field not in new:
                raise ValueError("plugin_field_removed: " + field)
        for field in set(old) | set(new):
            if not field.startswith("googleCalendar"):
                continue
            if new.get(field) != old.get(field):
                raise ValueError("protected_calendar_field: " + field)
    if kind == "source":
        locator = new.get("original_locator")
        if locator and locator.get("kind") == "vault_relative":
            original = vault_path(vault, locator["path"])
            if not locator["path"].startswith("Attachments/Originals/") or not original.is_file():
                raise ValueError("missing_original: vault-relative original is unavailable")
            if new.get("sha256") and records.compute_revision(original) != new["sha256"]:
                raise ValueError("original_hash_mismatch")
    return path, kind, expected


def propose(vault, changes, *, state=None, purpose="review", ingestion=None):
    vault = resolve_runtime_vault(vault)
    if not isinstance(changes, list) or not 0 < len(changes) <= MAX_RECORDS:
        raise ValueError("Proposals require 1–500 explicit records")
    if len({c.get("path") for c in changes}) != len(changes):
        raise ValueError("Duplicate paths in proposal")
    folded = [c.get("path", "").casefold() for c in changes]
    if len(set(folded)) != len(folded):
        raise ValueError("Case-colliding paths in proposal")
    for item in changes:
        check_record(vault, item)
    validate_relationships(vault, changes)
    if ingestion is not None:
        check = records.prevalidate_ingestion_proposal(vault, ingestion)
        if not check["valid"]:
            raise ValueError("Ingestion cross-reference prevalidation failed")
    proposal = {"contract_version": VERSION, "vault_root": str(vault),
                "vault_id": json.loads((vault / ".chrysalis-vault.json").read_text())["vault_id"],
                "purpose": purpose, "records": changes}
    if ingestion is not None:
        proposal["ingestion"] = ingestion
    if len(json.dumps(proposal).encode()) > MAX_REQUEST_BYTES:
        raise ValueError("Proposal exceeds 4 MiB")
    key = digest(proposal)
    atomic_json(state_root(vault, state) / "proposals" / (key + ".json"), proposal)
    return {"status": "review_required", "proposal_digest": key, "proposal": proposal}


def validate_relationships(vault, changes):
    proposed = {item["path"]: records.parse_frontmatter(item["document"]) for item in changes}
    tags = records._load_registered_pillars(vault)
    if "System/Life-Roadmap.md" in proposed:
        registry = proposed["System/Life-Roadmap.md"][0].get("tag_registry", {})
        if isinstance(registry, dict):
            tags = set(registry)
            tags.update(tag for entries in registry.values() if isinstance(entries, list) for tag in entries)
    for relative, (fm, body) in proposed.items():
        if schema_for(relative) == "daily_note":
            for block in fm.get("blocks", []):
                task = block["task"]
                if not task.startswith("TaskNotes/Tasks/") or not task.endswith(".md") or not (task in proposed or vault_path(vault, task).is_file()):
                    raise ValueError("unresolved_daily_task: " + task)
        for tag in fm.get("tags", []):
            if tag.startswith("pillar-") and tag not in tags:
                raise ValueError("unregistered_pillar: " + tag)
        for target in re.findall(r"\[\[([^\]|#]+)", body + str(fm)):
            if target.startswith("Attachments/"):
                exists = vault_path(vault, target).is_file()
            elif "/" in target:
                candidate = target if Path(target).suffix else target + ".md"
                exists = candidate in proposed or vault_path(vault, candidate).is_file()
            else:
                matches = {p for p in proposed if Path(p).stem == target}
                matches.update(p.relative_to(vault).as_posix() for base in ("Slipbox", "Sources", "TaskNotes/Tasks", "Daily") for p in vault_path(vault, base).glob("*.md") if p.stem == target)
                exists = len(matches) == 1
            if not exists:
                raise ValueError("unresolved_link: " + target)


def load_proposal(vault, key, state=None):
    vault = resolve_runtime_vault(vault)
    if not re.fullmatch(r"[a-f0-9]{64}", key):
        raise ValueError("Invalid proposal digest")
    path = state_root(vault, state) / "proposals" / (key + ".json")
    proposal = json.loads(path.read_text(encoding="utf-8"))
    if digest(proposal) != key or proposal["vault_root"] != str(vault):
        raise ValueError("Proposal root or digest changed; review again")
    if proposal["vault_id"] != json.loads((vault / ".chrysalis-vault.json").read_text())["vault_id"]:
        raise ValueError("Proposal belongs to another vault")
    return vault, proposal


def approve(vault, key, *, state=None, evidence):
    """Operator-only action. Host tools deliberately do not expose this function."""
    vault, proposal = load_proposal(vault, key, state)
    if not isinstance(evidence, str) or not evidence.strip() or len(evidence) > 1000:
        raise ValueError("Record the explicit human approval evidence")
    for item in proposal["records"]:
        check_record(vault, item)
    validate_relationships(vault, proposal["records"])
    receipt = {"proposal_digest": key, "vault_root": str(vault), "vault_id": proposal["vault_id"],
               "approved_at": datetime.now(timezone.utc).isoformat(), "evidence": evidence}
    atomic_json(state_root(vault, state) / "approvals" / (key + ".json"), receipt)
    return {"status": "approved", "proposal_digest": key}


def apply(vault, key, *, state=None, fail_after=None):
    vault, proposal = load_proposal(vault, key, state)
    external = state_root(vault, state)
    approval_path = external / "approvals" / (key + ".json")
    if not approval_path.is_file():
        raise ValueError("approval_required: operator receipt is absent")
    receipt = json.loads(approval_path.read_text(encoding="utf-8"))
    if any(receipt.get(k) != proposal.get(k) for k in ("vault_root", "vault_id")) or receipt.get("proposal_digest") != key:
        raise ValueError("approval_mismatch")
    ledger_path = external / "applications" / (key + ".json")
    with records._advisory_file_lock(ledger_path, lock_directory=external):
        validate_relationships(vault, proposal["records"])
        ledger = json.loads(ledger_path.read_text()) if ledger_path.is_file() else {"applied": {}}
        pending = []
        # Validate the entire remaining batch before the first record write.
        for item in proposal["records"]:
            already = item["path"] in ledger["applied"]
            path, kind, expected = check_record(vault, item, resume=True)
            if already:
                if not path.is_file() or records.compute_revision(path) != expected:
                    raise ValueError("applied_record_changed: preserve local edits and review again")
            elif path.is_file() and records.compute_revision(path) == expected:
                # Recover the crash between record replacement and ledger persistence.
                ledger["applied"][item["path"]] = expected
                atomic_json(ledger_path, ledger)
            else:
                pending.append((item, path, kind, expected))
        for index, (item, path, kind, expected) in enumerate(pending):
            if fail_after is not None and index >= fail_after:
                return {"status": "interrupted", "proposal_digest": key, "applied": ledger["applied"]}
            result = records.apply_cas_mutation(path, item["document"], if_revision=item.get("if_revision"),
                                               schema_name=kind, collection_dir=vault, lock_directory=external)
            if not result.valid:
                return {"status": "conflict", "diagnostics": [d.to_dict() for d in result.diagnostics]}
            if records.compute_revision(path) != expected:
                raise ValueError("postimage_mismatch")
            check_record(vault, item, resume=True)
            ledger["applied"][item["path"]] = expected
            atomic_json(ledger_path, ledger)
        for item in proposal["records"]:
            if records.compute_revision(vault_path(vault, item["path"])) != records.compute_revision(item["document"].encode()):
                raise ValueError("postimage_mismatch")
            check_record(vault, item, resume=True)
        validate_relationships(vault, proposal["records"])
        ledger["status"] = "verified"
        atomic_json(ledger_path, ledger)
    return {"status": "verified", "proposal_digest": key, "applied": ledger["applied"]}
