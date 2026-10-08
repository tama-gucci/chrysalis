"""Inert task capture and complete project ledgers; no host services here."""
from datetime import date, timedelta
from copy import deepcopy
from pathlib import Path
import re
import uuid
import hashlib

from . import daily
from System.scripts.vault_paths import vault_path


def duplicate_candidates(vault, *, text, sha256=None, limit=10):
    """Rank evidence for host review; lexical similarity never authorizes a merge."""
    if not isinstance(text, str) or len(text.encode()) > 65536 or not isinstance(limit, int) or not 1 <= limit <= 20:
        raise ValueError("Use bounded duplicate evidence")
    from helpers.ingestion_contract import compute_normalized_text_sha256
    normalized = compute_normalized_text_sha256(text)
    words = set(re.findall(r"[a-z0-9]{3,}", text.lower()))
    candidates = []
    for index, path in enumerate(sorted(vault_path(vault, "Sources").glob("*.md"))):
        if path.name == "README.md":
            continue
        if index >= 500:
            raise ValueError("Narrow duplicate search")
        relative = path.relative_to(vault).as_posix()
        fm, body, revision = daily.read(vault, relative)
        other = set(re.findall(r"[a-z0-9]{3,}", body[:65536].lower()))
        overlap = len(words & other) / max(1, len(words | other))
        exact = bool(sha256 and fm.get("sha256") == sha256)
        normalized_match = fm.get("normalized_text_sha256") == normalized
        if exact or normalized_match or overlap > .1:
            candidates.append({"path": relative, "revision": revision, "raw_exact": exact, "normalized_exact": normalized_match,
                               "lexical_overlap": round(overlap, 4), "evidence": body[:2000]})
    candidates.sort(key=lambda item: (item["raw_exact"], item["normalized_exact"], item["lexical_overlap"]), reverse=True)
    return {"status": "candidates" if candidates else "empty", "candidates": candidates[:limit], "semantic_review_required": True}


def task_document(vault, *, title, now, timezone, modality="analytical", base_minutes=45,
                  tags=None, priority="normal", due=None, project_ref=None, linked_zettels=None,
                  body="", path=None, fields=None):
    stamp = daily.local_stamp(now, timezone)
    daily.configured_timezone(vault, timezone)
    if modality not in daily.MODALITIES:
        raise ValueError("Unknown modality")
    if not isinstance(base_minutes, (int, float)) or not 0 < base_minutes <= 1440:
        raise ValueError("Estimate must be 1–1440 minutes")
    memory, _, _ = daily.read(vault, "System/Memory.md")
    multiplier = memory.get("cognitive_modality_defaults", {}).get(modality, {}).get("multiplier", 1.0)
    if not .2 <= multiplier <= 2:
        raise ValueError("Invalid modality multiplier; review Memory")
    links = set(linked_zettels or [])
    if project_ref:
        if not re.fullmatch(r"\[\[Projects/[a-z0-9-]+/Roadmap\]\]", project_ref):
            raise ValueError("Use an explicit project WikiLink")
        project, _, _ = daily.read(vault, project_ref[2:-2] + ".md")
        links.update(project.get("linked_zettels", []))
    prefix = (due or stamp.date().isoformat()).replace("-", "")
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:60] or "task"
    path = path or f"TaskNotes/Tasks/{prefix}-{slug}.md"
    if not re.fullmatch(r"TaskNotes/Tasks/[a-z0-9-]+\.md", path) or vault_path(vault, path).exists():
        raise ValueError("Capture requires a new task path; review an explicit update separately")
    fm = {"type": "task", "id": str(uuid.uuid4()), "title": title, "status": "todo", "dateCreated": stamp.isoformat(),
          "due": due, "scheduled": None, "priority": priority, "urgency_tier": 2, "modality": modality,
          "timeEstimate": round(base_minutes * multiplier), "energy": "medium", "friction": "medium", "micro_chunked": False,
          "tags": sorted(set(tags or []) | {"task"}), "linked_zettels": sorted(links), "project_ref": project_ref,
          "googleCalendarEventId": None}
    if fields:
        forbidden = set(fields) & {"type", "id", "title", "status", "scheduled", "googleCalendarEventId", "dateCreated"}
        if forbidden:
            raise ValueError("Capture cannot override protected defaults")
        fm.update(fields)
    return path, fm, body or "# " + title + "\n"


def horizon(vault, *, now, timezone, horizon_days=14):
    current = daily.local_stamp(now, timezone).date()
    if horizon_days != 14:
        raise ValueError("The supported planning horizon is 14 days")
    changes = []
    for path in sorted(vault_path(vault, "Projects").glob("*/Roadmap.md")):
        relative = path.relative_to(vault).as_posix()
        fm, body, revision = daily.read(vault, relative)
        if fm.get("status") != "active":
            continue
        updated = deepcopy(fm)
        modified = False
        for deliverable in updated.get("deliverables", []):
            if deliverable.get("status") in {"done", "archived"} or deliverable.get("task_ref"):
                continue
            due = deliverable.get("due")
            if due and date.fromisoformat(due) > current + timedelta(days=14):
                continue
            project = "[[" + relative[:-3] + "]]"
            task_path = f"TaskNotes/Tasks/{(due or current.isoformat()).replace('-', '')}-{fm['project_id']}-{deliverable['id']}.md"
            if vault_path(vault, task_path).exists():
                raise ValueError("Existing horizon task without ledger reference needs review")
            fields = {"deliverable_id": deliverable["id"], "source_ref": deliverable.get("source_ref") or fm.get("source_ref"),
                      "horizon_bucket": "uncertain" if not due else "overdue" if date.fromisoformat(due) < current else "imminent",
                      "date_uncertain": not bool(due), "review_required": not bool(due) or date.fromisoformat(due) < current,
                      "urgency_tier": deliverable.get("tier", 2)}
            task_path, tfm, tbody = task_document(vault, title=deliverable["title"], now=now, timezone=timezone,
                due=due, project_ref=project, tags=fm.get("tags", []), modality=deliverable.get("modality", "analytical"),
                base_minutes=deliverable.get("base_minutes", 45), path=task_path, fields=fields)
            changes.append(daily.change(vault, task_path, tfm, tbody, revision=None))
            deliverable["task_ref"] = "[[" + task_path[:-3] + "]]"
            modified = True
        if modified:
            changes.append(daily.change(vault, relative, updated, body, revision=revision))
    return changes
