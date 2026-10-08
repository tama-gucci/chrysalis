"""Deterministic draft operations. These functions never persist vault changes."""
from copy import deepcopy
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo
import hashlib
import math
from pathlib import Path

from helpers import records
from System.scripts.vault_paths import vault_path, native_path

MODALITIES = ("analytical", "kinetic", "synthesis", "administrative")


def read(vault, relative):
    path = native_path(vault_path(vault, relative))
    raw = path.read_bytes()
    fm, body = records.parse_frontmatter(raw.decode("utf-8"))
    return fm, body, records.compute_revision(raw)


def change(vault, relative, frontmatter, body, *, revision):
    """Bind a draft to the bytes read, never to a later re-read of its path."""
    vault_path(vault, relative)
    return {"path": relative, "if_revision": revision,
            "document": records.serialize_record(frontmatter, body)}


def configured_timezone(vault, timezone):
    memory, _, _ = read(vault, "System/Memory.md")
    if memory.get("user_profile", {}).get("timezone") != timezone:
        raise ValueError("Timezone must match the selected vault Memory")
    return timezone


def pause_gate(memory, current, cycle):
    pause = memory.get("system_state", {}).get("pause_state", {})
    if not pause.get("is_paused"):
        return
    mode = pause.get("mode")
    paused_at = datetime.fromisoformat(pause["paused_at"]) if pause.get("paused_at") else current
    ready = (mode == "maintenance" and cycle == "evening") or (
        mode == "rest" and cycle == "morning" and current.date() > paused_at.date()) or (
        mode == "vacation" and current.date().isoformat() >= (pause.get("resume_target") or "9999-12-31"))
    if not ready:
        raise ValueError("paused: review an explicit resume before this cycle")


def tasks(vault, archived=False):
    result = []
    for base in ("TaskNotes/Tasks", "TaskNotes/Archive") if archived else ("TaskNotes/Tasks",):
        directory = vault_path(vault, base)
        for path in sorted(directory.glob("*.md")):
            if path.name == "example-task.md":
                continue
            relative = path.relative_to(vault).as_posix()
            fm, body, revision = read(vault, relative)
            result.append((relative, fm, body, revision))
            if len(result) > 500:
                raise ValueError("Narrow the task selection; more than 500 records")
    return result


def local_stamp(value, timezone):
    if not isinstance(value, str) or value.endswith("Z"):
        raise ValueError("Use an explicit local timestamp")
    stamp = datetime.fromisoformat(value)
    zone = ZoneInfo(timezone)
    if stamp.tzinfo is None or stamp.astimezone(zone).utcoffset() != stamp.utcoffset():
        raise ValueError("Timestamp offset does not match the configured timezone")
    # Roundtrip rejects imaginary DST wall times.
    if stamp.astimezone(zone).replace(tzinfo=None) != stamp.replace(tzinfo=None):
        raise ValueError("Nonexistent local wall time")
    return stamp.astimezone(zone)


def business_date(start, days):
    if not 3 <= days <= 5:
        raise ValueError("Institutional verification requires 3–5 business days")
    current = date.fromisoformat(start)
    for _ in range(days):
        current += timedelta(days=1)
        while current.weekday() >= 5:
            current += timedelta(days=1)
    return current.isoformat()


def plan(vault, *, wake, energy, timezone, calendar, selected=None, not_before=None):
    if not isinstance(energy, int) or isinstance(energy, bool) or not 1 <= energy <= 5:
        raise ValueError("Energy must be an integer from 1 to 5")
    wake = local_stamp(wake, timezone)
    earliest = local_stamp(not_before, timezone) if not_before else wake
    if earliest.date() != wake.date() or earliest < wake:
        raise ValueError("Remaining-day boundary must be on the wake date and after waking")
    configured_timezone(vault, timezone)
    if calendar.get("status") not in {"ok", "empty"} or calendar.get("freshness") != "fresh":
        raise ValueError("calendar_unknown: obtain a fresh observation or explicit no-calendar observation")
    observed = calendar.get("observed_at")
    if not observed:
        raise ValueError("calendar_unknown: observation timestamp required")
    observed = datetime.fromisoformat(observed.replace("Z", "+00:00"))
    age = datetime.now(wake.tzinfo) - observed if observed.tzinfo else timedelta(days=1)
    max_age = calendar.get("max_age_seconds", 3600)
    if not isinstance(max_age, (int, float)) or not 60 <= max_age <= 86400:
        raise ValueError("calendar_unknown: invalid observation age limit")
    if age < timedelta(seconds=-60) or age > timedelta(seconds=max_age):
        raise ValueError("calendar_unknown: stale observation")
    memory, body, memory_revision = read(vault, "System/Memory.md")
    pause_gate(memory, wake, "morning")
    memory = deepcopy(memory)
    roadmap, _, _ = read(vault, "System/Life-Roadmap.md")
    active_projects = set(memory.get("active_horizons", {}).get("active_projects", []))
    roadmap_tasks = {m.get("task_ref") for m in roadmap.get("milestones", []) if isinstance(m, dict) and m.get("status") not in {"done", "archived"}}
    all_tasks = candidates = tasks(vault)
    if selected is not None:
        unknown = set(selected) - {row[0] for row in candidates}
        if unknown:
            raise ValueError("Unknown selected task")
        candidates = [row for row in candidates if row[0] in selected]
    weekend = wake.weekday() >= 5
    eligible = []
    for row in candidates:
        fm = row[1]
        if fm.get("status") not in {"todo", "in-progress"} or fm.get("review_required") or fm.get("date_uncertain"):
            continue
        if fm.get("isBlocked") or fm.get("blockedBy"):
            continue
        due = str(fm.get("due") or "")[:10]
        if selected is None and (fm.get("horizon_bucket") == "future" or (due and date.fromisoformat(due) > wake.date() + timedelta(days=14))):
            continue
        if weekend and (fm.get("institutional") or fm.get("modality") == "administrative"):
            continue
        if energy <= 2 and (fm.get("urgency_tier", 2) >= 3 or fm.get("modality") not in {"kinetic", "administrative"} or fm.get("friction") != "low" or fm.get("energy") == "high"):
            continue
        eligible.append(row)
    priorities = {"urgent": 0, "high": 1, "normal": 2, "low": 3, "none": 4}
    def rank(row):
        fm = row[1]
        rooted_task = "[[" + row[0][:-3] + "]]"
        due = str(fm.get("due") or "9999-12-31")[:10]
        strategic = rooted_task in roadmap_tasks or (fm.get("project_ref") in active_projects and due <= (wake.date() + timedelta(days=14)).isoformat())
        return (0 if strategic else 1, priorities.get(fm.get("priority", "normal"), 2), due,
                {"low": 0, "medium": 1, "high": 2}.get(fm.get("friction", "medium"), 1), row[0])
    eligible.sort(key=rank)
    if eligible:
        anchor = eligible[0]
        supports = [row for row in eligible[1:] if row[1].get("urgency_tier", 2) <= 2]
        eligible = [anchor] if weekend or energy <= 2 else [anchor, *supports[:2]]
    events = []
    for event in calendar.get("events", []):
        start = local_stamp(event["start"], timezone)
        end = local_stamp(event["end"], timezone)
        if end <= start:
            raise ValueError("Invalid calendar interval")
        buffer = event.get("travel_minutes", 30 if event.get("location") else 0)
        if not isinstance(buffer, (int, float)) or buffer < 0:
            raise ValueError("Invalid travel buffer")
        events.append((start - timedelta(minutes=buffer), end + timedelta(minutes=15)))
    blocks, changes = [], []
    occupied = list(events)
    buffer_minutes = 22.5 if energy <= 2 else 15
    deep_remaining = 239.0
    for relative, fm, task_body, revision in eligible:
        modality = fm.get("modality", "administrative")
        offset = {"analytical": 90, "administrative": 390, "kinetic": 465, "synthesis": 510}[modality]
        if energy <= 2:
            offset = 390
        start = max(wake + timedelta(minutes=offset), earliest)
        remaining = min(float(fm.get("timeEstimate", 45)), 75 if energy <= 2 else 149 if weekend else 150)
        if modality in {"analytical", "synthesis"}:
            remaining = min(remaining, deep_remaining)
        if not math.isfinite(remaining) or remaining <= 0:
            continue
        first = None
        while remaining > 0:
            duration = min(75, remaining)
            end = start + timedelta(minutes=duration)
            # Only shift forward inside this day; commitments and prior focus win.
            while True:
                collision = next(((a, b) for a, b in occupied if start < b and end > a), None)
                if not collision:
                    break
                start = collision[1]
                end = start + timedelta(minutes=duration)
            cutoff = min(wake + timedelta(hours=12), wake.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
            if end > cutoff:
                duration = min(duration, (cutoff - start).total_seconds() / 60)
                if duration <= 0:
                    break
                end = start + timedelta(minutes=duration)
            first = first or start
            blocks.append({"task": relative, "start": start.isoformat(), "end": end.isoformat()})
            occupied.append((start, end + timedelta(minutes=buffer_minutes)))
            remaining -= duration
            if modality in {"analytical", "synthesis"}:
                deep_remaining -= duration
            start = end + timedelta(minutes=buffer_minutes)
        if first:
            updated = deepcopy(fm)
            updated["scheduled"] = first.isoformat()
            changes.append(change(vault, relative, updated, task_body, revision=revision))
    scheduled_paths = {b["task"] for b in blocks}
    for relative, fm, task_body, revision in all_tasks:
        if relative not in scheduled_paths and fm.get("scheduled") and str(fm["scheduled"])[:10] == wake.date().isoformat():
            changes.append(change(vault, relative, {**fm, "scheduled": None}, task_body, revision=revision))
    baseline = memory.setdefault("morning_checkin", {}).setdefault("learned_rhythms", {}).get("wake_minutes", 540)
    actual = wake.hour * 60 + wake.minute
    memory["morning_checkin"]["learned_rhythms"]["wake_minutes"] = round(baseline + .15 * (actual - baseline), 2)
    memory["morning_checkin"]["active_today"] = {"date": wake.date().isoformat(), "wake": wake.isoformat(), "energy": energy}
    memory.setdefault("system_state", {})["pause_state"] = {"is_paused": False, "mode": None}
    memory["prototype_schedule"] = {"target_date": wake.date().isoformat(), "feedback_status": "approved", "blocks": blocks}
    changes.append(change(vault, "System/Memory.md", memory, body, revision=memory_revision))
    daily = {"type": "daily_note", "date": wake.date().isoformat(), "wake_time": wake.isoformat(),
             "energy_level": energy, "energy_mode": "sleep_deprived" if energy <= 2 else "optimal", "tags": ["daily-note"], "blocks": blocks}
    daily_path = f"Daily/{wake.date().isoformat()}.md"
    old_fm, old_body, daily_revision = read(vault, daily_path) if vault_path(vault, daily_path).is_file() else ({}, "", None)
    daily = {**old_fm, **daily}
    start_marker, end_marker = "<!-- chrysalis:focus:start -->", "<!-- chrysalis:focus:end -->"
    lines = [start_marker, "# Daily focus", "", "| Start | End | Task |", "|---|---|---|"]
    lines.extend(f"| {b['start']} | {b['end']} | [[{b['task'][:-3]}]] |" for b in blocks)
    lines.extend([end_marker, ""])
    projection = "\n".join(lines)
    if start_marker in old_body and end_marker in old_body:
        before, remainder = old_body.split(start_marker, 1)
        _, after = remainder.split(end_marker, 1)
        new_body = before + projection + after.lstrip("\n")
    else:
        new_body = projection + "\n" + old_body
    changes.append(change(vault, daily_path, daily, new_body, revision=daily_revision))
    return changes, blocks


def audit(vault, *, now, timezone):
    current = local_stamp(now, timezone)
    configured_timezone(vault, timezone)
    memory, body, memory_revision = read(vault, "System/Memory.md")
    pause_gate(memory, current, "evening")
    memory = deepcopy(memory)
    if memory.get("system_state", {}).get("pause_state", {}).get("mode") in {"maintenance", "vacation"}:
        memory["system_state"]["pause_state"] = {"is_paused": False, "mode": None}
    outcomes = memory.setdefault("learned_sessions", {})
    defaults = memory.setdefault("cognitive_modality_defaults", {})
    changes, learned, warnings = [], [], []
    for relative, fm, task_body, revision in tasks(vault, archived=True):
        updated = deepcopy(fm)
        sessions = list(fm.get("timeEntries", []))
        if not sessions and fm.get("startedAt") and fm.get("completedAt"):
            sessions = [{"startTime": fm["startedAt"], "endTime": fm["completedAt"]}]
        for session in sessions:
            if not session.get("endTime") or fm.get("status") != "done":
                continue
            try:
                start = datetime.fromisoformat(session["startTime"].replace("Z", "+00:00"))
                end = datetime.fromisoformat(session["endTime"].replace("Z", "+00:00"))
                estimate = float(fm.get("timeEstimate", 0))
                if start.tzinfo is None or end.tzinfo is None or end <= start or end > current or estimate <= 0:
                    raise ValueError("Invalid session")
                if current - end > timedelta(hours=24):
                    continue
                stable_task = str(fm.get("id") or (Path(relative).stem + "|" + str(fm.get("dateCreated"))))
                identity = hashlib.sha256((stable_task + "|" + start.isoformat() + "|" + end.isoformat()).encode()).hexdigest()
                if identity in outcomes:
                    continue
                modality = fm.get("modality", "administrative")
                default = defaults.setdefault(modality, {"multiplier": 1.0})
                duration = (end - start).total_seconds() / 60
                default["multiplier"] = records.calculate_dynamic_multiplier(default.get("multiplier", 1.0), duration, estimate)
                outcomes[identity] = {"task": relative, "start": start.isoformat(), "end": end.isoformat(), "duration": duration}
                learned.append(identity)
            except (ValueError, TypeError):
                warnings.append({"path": relative, "code": "invalid_session_review_required"})
        if fm.get("status") == "todo":
            scheduled = fm.get("scheduled")
            if scheduled and str(scheduled)[:10] <= current.date().isoformat():
                updated["scheduled"] = None
            try:
                age = current - datetime.fromisoformat(fm["dateCreated"])
                if age >= timedelta(hours=48) and fm.get("timeEstimate", 0) >= 45 and not fm.get("micro_chunked"):
                    updated["micro_chunked"] = True
                    task_body += "\n\n## Starter Wedge\n- [ ] Open the materials (under 15 minutes)\n- [ ] Do the smallest concrete sub-action (under 15 minutes)\n- [ ] Continue or record the next obstacle\n"
            except (ValueError, KeyError):
                warnings.append({"path": relative, "code": "invalid_task_age"})
        if updated != fm:
            changes.append(change(vault, relative, updated, task_body, revision=revision))
    pause = memory.setdefault("system_state", {}).setdefault("pause_state", {})
    prototype = memory.get("prototype_schedule", {})
    if prototype.get("feedback_status") == "pending" and prototype.get("target_date", "9999-12-31") <= current.date().isoformat() and not pause.get("is_paused"):
        pause.update({"is_paused": True, "mode": "auto_unresponsive", "reason": "unreviewed_previous_cycle", "paused_at": current.isoformat()})
    changes.append(change(vault, "System/Memory.md", memory, body, revision=memory_revision))
    return changes, {"learned_sessions": learned, "warnings": warnings}


def stage(vault, **arguments):
    """Compile a reviewable agenda without scheduling tasks or learning telemetry."""
    memory, body, revision = read(vault, "System/Memory.md")
    changes, blocks = plan(vault, **arguments)
    planned = next(item for item in changes if item["path"] == "System/Memory.md")
    prototype = records.parse_frontmatter(planned["document"])[0]["prototype_schedule"]
    prototype["feedback_status"] = "pending"
    memory["prototype_schedule"] = prototype
    return [change(vault, "System/Memory.md", memory, body, revision=revision)], blocks


def pause(vault, *, mode, now, timezone, until=None):
    current = local_stamp(now, timezone)
    configured_timezone(vault, timezone)
    if mode not in {"maintenance", "rest", "flow", "vacation", "resume"}:
        raise ValueError("Unknown pause mode")
    if mode == "vacation" and (not until or date.fromisoformat(until) < current.date()):
        raise ValueError("Vacation requires a future resume date")
    memory, body, memory_revision = read(vault, "System/Memory.md")
    memory = deepcopy(memory)
    target = {"maintenance": "evening", "rest": "morning", "flow": None, "vacation": until, "resume": None}[mode]
    memory.setdefault("system_state", {})["pause_state"] = {"is_paused": mode != "resume", "mode": None if mode == "resume" else mode,
                                                           "paused_at": current.isoformat(), "resume_target": target}
    if mode == "maintenance":
        memory["prototype_schedule"] = {"feedback_status": "pending", "blocks": []}
    if mode == "rest":
        memory["rest_day"] = current.date().isoformat()
    changes = [change(vault, "System/Memory.md", memory, body, revision=memory_revision)]
    if mode != "resume":
        for relative, fm, task_body, revision in tasks(vault):
            if fm.get("scheduled") and str(fm["scheduled"])[:10] == current.date().isoformat():
                fm["scheduled"] = None
                changes.append(change(vault, relative, fm, task_body, revision=revision))
        relative = f"Daily/{current.date().isoformat()}.md"
        if vault_path(vault, relative).is_file():
            fm, daily_body, revision = read(vault, relative)
            fm["blocks"] = []
            start_marker, end_marker = "<!-- chrysalis:focus:start -->", "<!-- chrysalis:focus:end -->"
            if start_marker in daily_body and end_marker in daily_body:
                before, remainder = daily_body.split(start_marker, 1)
                _, after = remainder.split(end_marker, 1)
                daily_body = before + start_marker + "\n# Daily focus\n\nNo active focus blocks.\n" + end_marker + after
            daily_body += f"\n\n> [!WARNING]\n> Paused: {mode}; re-entry: {target or 'manual'}.\n"
            changes.append(change(vault, relative, fm, daily_body, revision=revision))
    routing = "morning" if current.hour < 12 else "flex" if current.hour < 18 else "evening"
    return changes, {"resume_target": target, "reentry": routing}
