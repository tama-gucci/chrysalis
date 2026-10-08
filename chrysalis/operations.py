"""Host-independent dispatch surface. No shell or arbitrary writer."""
from datetime import date
from pathlib import Path
from copy import deepcopy
import re
import json

from helpers import records
from helpers import ingestion_contract as ingestion
from helpers import integration_registry as integrations
from System.scripts.vault_paths import resolve_runtime_vault, vault_path, native_path
from . import runtime, daily, receipts

OPERATIONS = tuple(json.loads((Path(__file__).resolve().parents[1] / "contracts/operations.json").read_text()))


def document_observation(path):
    with native_path(path).open("rb") as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError("record_too_large")
    return {"status": "ok", "document": raw.decode("utf-8"), "revision": records.compute_revision(raw)}


def redact(value):
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items() if not re.fullmatch(r"resolved_secret|credentials?|.*secret|.*password|(?:access_|refresh_|id_|auth_|bearer_)?token|api_?key|authorization", key, re.I)}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def graph(vault):
    """Draft exact project associations and reciprocal links, never fuzzy title matching."""
    projects, zettels, changes = {}, {}, []
    for path in sorted(vault_path(vault, "Projects").glob("*/Roadmap.md")):
        relative = path.relative_to(vault).as_posix()
        projects[f"[[{relative[:-3]}]]"] = (relative, *daily.read(vault, relative))
    for path in sorted(vault_path(vault, "Slipbox").glob("*.md")):
        relative = path.relative_to(vault).as_posix()
        if path.name == "README.md":
            continue
        fm, body, revision = daily.read(vault, relative)
        zettels[f"[[{relative[:-3]}]]"] = (relative, fm, body, revision)
    if len(projects) + len(zettels) > 500:
        raise ValueError("Narrow graph selection")
    related = {}
    reciprocal = {}
    for project_link, (relative, fm, body, revision) in projects.items():
        links = set(fm.get("linked_zettels", []))
        for zettel_link, (zrelative, zfm, zbody, zrevision) in zettels.items():
            if zfm.get("project_ref") == project_link:
                links.add(zettel_link)
        links &= set(zettels)
        related[project_link] = sorted(links)
        updated = deepcopy(fm)
        updated["linked_zettels"] = sorted(links)
        missing = [link for link in sorted(links) if link not in body]
        if missing:
            body += "\n\n## Knowledge references\n" + "\n".join("- " + link for link in missing) + "\n"
        if updated != fm or missing:
            changes.append(daily.change(vault, relative, updated, body, revision=revision))
        for link in links:
            zrelative, zfm, zbody, zrevision = zettels[link]
            if zfm.get("project_ref") is None:
                reciprocal.setdefault(link, []).append(project_link)
    for link, project_links in reciprocal.items():
        if len(project_links) == 1:
            zrelative, zfm, zbody, zrevision = zettels[link]
            changes.append(daily.change(vault, zrelative, {**zfm, "project_ref": project_links[0]}, zbody, revision=zrevision))
    for relative, fm, body, revision in daily.tasks(vault):
        if fm.get("project_ref") in related:
            new = deepcopy(fm)
            new["linked_zettels"] = sorted(set(fm.get("linked_zettels", [])) | set(related[fm["project_ref"]]))
            if new != fm:
                changes.append(daily.change(vault, relative, new, body, revision=revision))
    return changes


def doctor(vault):
    diagnostics = []
    checked = 0
    memory, _, _ = daily.read(vault, "System/Memory.md")
    timezone = memory.get("user_profile", {}).get("timezone")
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(timezone)
    except (ValueError, TypeError, KeyError):
        diagnostics.append({"code": "invalid_timezone", "path": "System/Memory.md"})
        timezone = None
    registered_tags = records._load_registered_pillars(vault)
    for modality in daily.MODALITIES:
        value = memory.get("cognitive_modality_defaults", {}).get(modality, {}).get("multiplier")
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not .2 <= value <= 2:
            diagnostics.append({"code": "invalid_multiplier", "modality": modality, "path": "System/Memory.md"})
    package = Path(__file__).resolve().parents[1]
    for name in ("daily", "task", "knowledge", "diagnostics", "environment", "integrations", "maintenance"):
        skill = package / "skills" / ("chrysalis-" + name) / "SKILL.md"
        if not skill.is_file():
            diagnostics.append({"code": "missing_skill_dependency", "skill": name})
            continue
        for relative in re.findall(r"references/[a-z0-9-]+\.md", skill.read_text(encoding="utf-8")):
            if not (skill.parent / relative).is_file():
                diagnostics.append({"code": "missing_skill_dependency", "skill": name, "reference": relative})
    for directory, pattern in (("TaskNotes/Tasks", "*.md"), ("TaskNotes/Archive", "*.md"), ("Projects", "*/Roadmap.md"), ("Slipbox", "*.md"), ("Sources", "*.md"), ("System", "*.md"), ("Daily", "*.md")):
        for path in sorted(vault_path(vault, directory).glob(pattern)):
            if path.name in {"example-task.md", "README.md"}:
                continue
            relative = path.relative_to(vault).as_posix()
            vault_path(vault, relative)
            validation = records.validate_record(path, type_name=runtime.schema_for(relative), collection_dir=vault)
            diagnostics.extend(d.to_dict() for d in validation.diagnostics)
            checked += 1
            if checked > 2000:
                raise ValueError("Diagnostic limit exceeded; select a smaller collection")
            fm, body, revision = daily.read(vault, relative)
            try:
                runtime.check_record(vault, {"path": relative, "if_revision": revision, "document": records.serialize_record(fm, body)})
                runtime.validate_relationships(vault, [{"path": relative, "document": records.serialize_record(fm, body)}])
            except (ValueError, KeyError, TypeError) as exc:
                diagnostics.append({"code": "record_policy", "path": relative, "reason": str(exc)})
            for tag in fm.get("tags", []):
                if tag.startswith("pillar-") and tag not in registered_tags:
                    diagnostics.append({"code": "unregistered_pillar", "path": relative, "tag": tag})
            for field in ("dateCreated", "created", "last_updated", "scheduled", "startedAt", "completedAt", "due_at", "wake_time"):
                value = fm.get(field)
                if timezone and isinstance(value, str) and "T" in value:
                    try:
                        daily.local_stamp(value, timezone)
                    except ValueError:
                        diagnostics.append({"code": "invalid_local_timestamp", "path": relative, "field": field})
            # Resolve explicitly rooted links and unique stems, excluding original embeds.
            for target in re.findall(r"\[\[([^\]|#]+)", body + str(fm)):
                if target.startswith("Attachments/"):
                    resolved = vault_path(vault, target).is_file()
                elif "/" in target:
                    resolved = vault_path(vault, target if Path(target).suffix else target + ".md").is_file()
                else:
                    found = [p for base in ("Slipbox", "Sources", "TaskNotes/Tasks") for p in vault_path(vault, base).glob(target + ".md")]
                    resolved = len(found) == 1
                if not resolved:
                    diagnostics.append({"code": "unresolved_link", "path": relative, "target": target})
    return {"status": "ok" if not diagnostics else "invalid", "checked": checked, "checks": ["schema", "timezone", "taxonomy", "links", "skill_dependencies", "multipliers"], "diagnostics": diagnostics}


def dispatch(request):
    operation = request.get("operation")
    if operation not in OPERATIONS:
        raise ValueError("unsupported_operation")
    vault = resolve_runtime_vault(request.get("vault_root"))
    args = request.get("arguments", {})
    if not isinstance(args, dict):
        raise ValueError("arguments must be an object")
    state = request.get("state_root")
    if operation == "schema":
        if args["type"] not in {"task", "project", "zettel", "source", "system_state", "daily_note"}:
            raise ValueError("Unknown record schema")
        path = vault_path(vault, "_types/" + args["type"] + ".md")
        return document_observation(path)
    if operation == "duplicates":
        from .knowledge import duplicate_candidates
        return duplicate_candidates(vault, **args)
    if operation == "original.inspect":
        from .originals import inspect
        return inspect(vault, **args)
    if operation == "template":
        package = Path(__file__).resolve().parents[1]
        available = {p.relative_to(package).as_posix(): p for base in ("_templates", "System/_templates", "Projects/_templates", "Slipbox/_templates", "Environments/_templates") for p in (package / base).glob("*.md")}
        if not args.get("path"):
            return {"status": "ok", "templates": sorted(available)}
        if args["path"] not in available:
            raise ValueError("Unknown maintained template")
        return {"status": "ok", "document": available[args["path"]].read_text(encoding="utf-8")}
    if operation == "query":
        patterns = {"tasks": ("TaskNotes/Tasks", "*.md"), "archive": ("TaskNotes/Archive", "*.md"), "projects": ("Projects", "*/Roadmap.md"), "zettels": ("Slipbox", "*.md"), "sources": ("Sources", "*.md"), "daily": ("Daily", "*.md")}
        directory, pattern = patterns[args["collection"]]
        limit, page = args.get("limit", 50), args.get("page", 0)
        if not isinstance(limit, int) or not 1 <= limit <= 100 or not isinstance(page, int) or page < 0:
            raise ValueError("Use a bounded query")
        found = []
        for path in sorted(vault_path(vault, directory).glob(pattern)):
            if path.name in {"README.md", "example-task.md"}:
                continue
            relative = path.relative_to(vault).as_posix()
            fm, _, revision = daily.read(vault, relative)
            if args.get("status") and fm.get("status") != args["status"]:
                continue
            found.append({"path": relative, "revision": revision, "frontmatter": fm})
            if len(found) > 2000:
                raise ValueError("Query collection limit exceeded")
        return {"status": "ok", "records": found[page * limit:(page + 1) * limit], "next_page": page + 1 if len(found) > (page + 1) * limit else None}
    if operation == "business-buffer":
        return {"status": "ok", "verification_date": daily.business_date(args["submission_date"], args.get("business_days", 3))}
    if operation == "gap-fillers":
        return {"status": "ok", "candidates": records.select_gap_filler_candidates(vault, target_count=min(20, args.get("target_count", 3)), reference_date=date.fromisoformat(args["date"]))}
    if operation == "project.status":
        projects = []
        for path in sorted(vault_path(vault, "Projects").glob("*/Roadmap.md")):
            fm, _, _ = daily.read(vault, path.relative_to(vault).as_posix())
            deliverables = fm.get("deliverables", [])
            projects.append({key: fm.get(key) for key in ("project_id", "title", "pillar", "status", "horizon_window")})
            projects[-1]["progress"] = {"done": sum(d.get("status") == "done" for d in deliverables), "total": len(deliverables)}
        return {"status": "ok", "projects": projects}
    if operation == "project.reconcile":
        path = vault_path(vault, args["path"])
        if runtime.schema_for(args["path"]) != "project":
            raise ValueError("Expected project roadmap")
        fm, body, revision = daily.read(vault, args["path"])
        result = records.reconcile_project_deliverables(path, args["deliverables"], authoritative_replacement=args.get("authoritative_replacement", False), source_scope=args.get("source_scope"), source_ref=args.get("source_ref"), extraction_status=args.get("extraction_status", "complete"))
        if records.compute_revision(path) != revision:
            raise ValueError("stale_revision: project changed during reconciliation")
        fm["deliverables"] = result.unchanged + result.modified + result.added + result.dropped
        return {**runtime.propose(vault, [daily.change(vault, args["path"], fm, body, revision=revision)], state=state, purpose="project_reconciliation"), "diff": result.to_dict()}
    if operation == "task.draft":
        from .knowledge import task_document
        relative, fm, body = task_document(vault, **args)
        return runtime.propose(vault, [daily.change(vault, relative, fm, body, revision=None)], state=state, purpose="task_capture")
    if operation == "horizon":
        from .knowledge import horizon
        changes = horizon(vault, **args)
        return runtime.propose(vault, changes, state=state, purpose="project_horizon") if changes else {"status": "no_changes"}
    if operation == "read":
        path = vault_path(vault, args["path"])
        runtime.schema_for(args["path"])
        return document_observation(path)
    if operation == "validate":
        path = vault_path(vault, args["path"])
        result = records.validate_record(path, args.get("document"), type_name=runtime.schema_for(args["path"]), collection_dir=vault)
        return {"status": "ok" if result.valid else "invalid", "diagnostics": [d.to_dict() for d in result.diagnostics]}
    if operation == "propose":
        return runtime.propose(vault, args["records"], state=state, purpose=args.get("purpose", "review"))
    if operation == "apply":
        return runtime.apply(vault, args["proposal_digest"], state=state)
    if operation == "ingest.discover":
        page_size = args.get("page_size", 50)
        if not isinstance(page_size, int) or isinstance(page_size, bool) or not 1 <= page_size <= 100:
            raise ValueError("Discovery page size must be 1–100")
        if args.get("page_token") is not None and not re.fullmatch(r"[0-9]{1,6}", str(args["page_token"])):
            raise ValueError("Invalid discovery page token")
        result = ingestion.discover_all_configured_sources(vault, page_size=args.get("page_size", 50)) if args.get("all") else ingestion.discover_configured_source(vault, args["source_alias"], page_size=args.get("page_size", 50), page_token=args.get("page_token"))
        return {"status": "observed", "discovery": redact(result)}
    if operation in {"ingest.draft", "ingest.prevalidate"}:
        proposal = args.get("proposal")
        if operation == "ingest.draft":
            proposal = ingestion.build_ingestion_proposal_from_envelope(vault, args["envelope"], reference_date=date.fromisoformat(args["date"]), default_local_offset=args["local_offset"])
        if proposal.get("valid_envelope") is False:
            return {"status": "invalid", "proposal": proposal, "prevalidation": {"valid": False, "diagnostics": proposal.get("diagnostics", [])}}
        prevalidation = records.prevalidate_ingestion_proposal(vault, proposal)
        if not prevalidation["valid"]:
            return {"status": "invalid", "prevalidation": prevalidation, "proposal": proposal}
        changes = [{"path": row["path"], "if_revision": row.get("if_revision"), "document": records._render_record_markdown(row)} for row in proposal["records"]]
        if not changes:
            return {"status": "no_changes", "proposal": proposal}
        return runtime.propose(vault, changes, state=state, purpose="ingestion", ingestion=proposal)
    if operation == "integrations.status":
        return {"status": "ok", "integrations": redact(integrations.evaluate_all_integrations(vault))}
    if operation == "capability":
        return {"status": "observed", "result": redact(integrations.invoke_capability(vault, args["capability"], request_payload=args.get("request", {}), workflow_binding=args.get("binding_slot")))}
    if operation in {"plan", "stage"}:
        changes, result = (daily.stage if operation == "stage" else daily.plan)(vault, **args)
        proposal = runtime.propose(vault, changes, state=state, purpose="staging" if operation == "stage" else "calibration")
        if operation == "stage":
            proposal["result_digest"] = receipts.save_result(vault, args["timezone"], "planning", {"blocks": result, "proposal_digest": proposal["proposal_digest"]}, state=state)
        return proposal
    if operation == "audit":
        health = doctor(vault)
        if health["status"] != "ok":
            return {"status": "blocked", "health": health}
        changes, result = daily.audit(vault, **args)
        proposal = runtime.propose(vault, changes, state=state, purpose="audit")
        proposal["audit"] = result
        proposal["result_digest"] = receipts.save_result(vault, args["timezone"], "audit", {**result, "proposal_digest": proposal["proposal_digest"]}, state=state)
        return proposal
    if operation in {"pause", "resume"}:
        changes, result = daily.pause(vault, **{**args, "mode": "resume" if operation == "resume" else args["mode"]})
        return {**runtime.propose(vault, changes, state=state, purpose=operation), **result}
    if operation == "graph":
        changes = graph(vault)
        return runtime.propose(vault, changes, state=state, purpose="knowledge_links") if changes else {"status": "no_changes"}
    if operation == "doctor":
        return doctor(vault)
    if operation == "daily.begin":
        return receipts.begin(vault, **args, state=state)
    if operation == "daily.gate":
        return receipts.gate(vault, **args, state=state)
    if operation == "environment":
        from System.scripts.environment_probe import collect
        return {"status": "observed", "environment": collect(**args)}
    raise ValueError("unsupported_operation")
