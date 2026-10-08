import json
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
from chrysalis import runtime, daily, operations, receipts
from chrysalis.package import initialize, lifecycle
from helpers import records
from helpers.integration_registry import read_tasknotes_calendar_commitments
from System.scripts.vault_paths import resolve_runtime_vault

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def vault(tmp_path, monkeypatch):
    root = tmp_path / "chrysalis"
    initialize(root, "America/Chicago")
    monkeypatch.setenv("CHRYSALIS_STATE_ROOT", str(tmp_path / "execution"))
    return root


def task(vault, name="sample", **fields):
    fm = {"type": "task", "title": "Review a synthetic specification", "status": "todo",
          "dateCreated": "2026-10-05T09:00:00-05:00", "priority": "normal", "urgency_tier": 2,
          "timeEstimate": 45, "modality": "analytical", "tags": ["task"], "scheduled": None,
          "googleCalendarEventId": None, **fields}
    path = "TaskNotes/Tasks/" + name + ".md"
    (vault / path).write_text(records.serialize_record(fm, "# Synthetic specification\n"), encoding="utf-8")
    return path


def reviewed(vault, changes):
    key = runtime.propose(vault, changes)["proposal_digest"]
    runtime.approve(vault, key, evidence="Synthetic test operator approval")
    return key


def draft(vault, path, fm, body):
    return daily.change(vault, path, fm, body, revision=records.compute_revision(vault / path))


def calendar_observation(events=None):
    return {"status": "ok" if events else "empty", "freshness": "fresh", "observed_at": datetime.now(timezone.utc).isoformat(), "events": events or []}


def test_exact_approval_and_body_only_conflict(vault):
    path = task(vault)
    fm, body, _ = daily.read(vault, path)
    fm["priority"] = "high"
    change = draft(vault, path, fm, body)
    key = runtime.propose(vault, [change])["proposal_digest"]
    with pytest.raises(ValueError, match="approval_required"):
        runtime.apply(vault, key)
    runtime.approve(vault, key, evidence="Synthetic explicit approval")
    (vault / path).write_text((vault / path).read_text() + "A local body edit\n", encoding="utf-8")
    with pytest.raises(ValueError, match="stale_revision"):
        runtime.apply(vault, key)
    assert "A local body edit" in (vault / path).read_text()


def test_tampering_and_wrong_root(vault, tmp_path):
    path = task(vault)
    fm, body, _ = daily.read(vault, path)
    key = reviewed(vault, [draft(vault, path, {**fm, "priority": "high"}, body)])
    root2 = tmp_path / "other" / "chrysalis"
    shutil.copytree(vault, root2)
    with pytest.raises(ValueError, match="root or digest"):
        runtime.apply(root2, key)
    stored = runtime.state_root(vault) / "proposals" / (key + ".json")
    payload = json.loads(stored.read_text())
    payload["records"][0]["document"] += "Tampered"
    runtime.atomic_json(stored, payload)
    with pytest.raises(ValueError, match="digest"):
        runtime.apply(vault, key)


def test_partial_apply_retry_and_postimages(vault):
    paths = [task(vault, "one"), task(vault, "two")]
    changes = []
    for path in paths:
        fm, body, _ = daily.read(vault, path)
        changes.append(draft(vault, path, {**fm, "priority": "high"}, body))
    key = reviewed(vault, changes)
    assert runtime.apply(vault, key, fail_after=1)["status"] == "interrupted"
    assert runtime.apply(vault, key)["status"] == "verified"
    (vault / paths[0]).write_text((vault / paths[0]).read_text() + "local edit", encoding="utf-8")
    with pytest.raises(ValueError):
        runtime.apply(vault, key)


@pytest.mark.parametrize("field,value", [("googleCalendarEventId", "synthetic-calendar-event"), ("googleCalendarExceptionEventId", "synthetic-occurrence")])
def test_calendar_ownership(vault, field, value):
    path = task(vault, **{field: value})
    fm, body, _ = daily.read(vault, path)
    fm[field] = None
    with pytest.raises(ValueError, match="protected_calendar"):
        runtime.propose(vault, [draft(vault, path, fm, body)])


def test_tasknotes_roundtrip_and_unknown_properties(vault):
    fields = {"timeEntries": [{"startTime": "2026-10-07T14:00:00Z", "endTime": "2026-10-07T14:25:00Z"}],
              "contexts": ["synthetic-office"], "recurrence": "FREQ=WEEKLY", "complete_instances": ["2026-10-01"],
              "reminders": [{"id": "synthetic", "type": "relative", "relatedTo": "due", "offset": "-PT5M"}]}
    path = task(vault, **fields)
    fm, body, _ = daily.read(vault, path)
    key = reviewed(vault, [draft(vault, path, {**fm, "priority": "high"}, body)])
    assert runtime.apply(vault, key)["status"] == "verified"
    new = daily.read(vault, path)[0]
    assert all(new[k] == value for k, value in fields.items())
    with pytest.raises(ValueError, match="invalid_record"):
        runtime.propose(vault, [draft(vault, path, {**new, "execute_shell": "unsafe"}, body)])
    del new["timeEntries"]
    with pytest.raises(ValueError, match="plugin_field_removed"):
        runtime.propose(vault, [draft(vault, path, new, body)])


def test_validation_dependency_failure_after_cache(vault, monkeypatch):
    path = task(vault)
    fm, body, revision = daily.read(vault, path)
    assert records.validate_record(vault / path, collection_dir=vault).valid
    monkeypatch.setattr(records, "HAS_JSONSCHEMA", False)
    result = records.apply_cas_mutation(vault / path, records.serialize_record(fm, body), if_revision=revision, collection_dir=vault)
    assert not result.valid
    assert result.diagnostics[0].code == "validation_unavailable"


def test_noncooperating_editor_during_mutator(vault):
    path = task(vault)
    original = (vault / path).read_bytes()
    def mutate(content):
        (vault / path).write_bytes(original + b"Local editor\n")
        return content + "Agent edit\n"
    result = records.apply_cas_mutation(vault / path, mutate, if_revision=records.compute_revision(original), collection_dir=vault)
    assert not result.valid and result.diagnostics[0].code == "concurrent_modification"
    assert (vault / path).read_bytes() == original + b"Local editor\n"


def test_explicit_roots_case_and_confinement(vault, tmp_path, monkeypatch):
    monkeypatch.delenv("CHRYSALIS_VAULT_PATH", raising=False)
    with pytest.raises(ValueError):
        resolve_runtime_vault()
    with pytest.raises(ValueError):
        resolve_runtime_vault(ROOT)
    wrong = tmp_path / "other" / "Chrysalis"
    wrong.parent.mkdir()
    wrong.mkdir()
    with pytest.raises(ValueError, match="empty|lowercase"):
        initialize(wrong.parent / "chrysalis", "America/Chicago")
    for path in ("../escape.md", "/escape.md", "System/../escape.md", "C:/escape.md"):
        with pytest.raises(ValueError):
            runtime.propose(vault, [{"path": path, "document": "unsafe"}])
    with pytest.raises(ValueError):
        runtime.state_root(vault, vault / "state")


def test_calendar_empty_stale_and_never_observed():
    assert read_tasknotes_calendar_commitments()["status"] == "unavailable"
    assert read_tasknotes_calendar_commitments({"events": []})["freshness"] == "never_observed"
    now = datetime.now(timezone.utc)
    assert read_tasknotes_calendar_commitments({"events": [], "observed_at": now.isoformat()})["status"] == "empty"
    assert read_tasknotes_calendar_commitments({"events": [], "observed_at": (now - timedelta(days=1)).isoformat()})["status"] == "stale"


def test_plan_energy_calendar_and_consistent_records(vault):
    anchor = task(vault, "anchor", timeEstimate=120, urgency_tier=4)
    support = task(vault, "support", modality="kinetic", timeEstimate=30, friction="low", energy="low")
    calendar = calendar_observation([{"start": "2026-10-07T10:00:00-05:00", "end": "2026-10-07T12:00:00-05:00"}])
    changes, blocks = daily.plan(vault, wake="2026-10-07T09:00:00-05:00", energy=4, timezone="America/Chicago", calendar=calendar)
    assert all(not (b["start"] < "2026-10-07T12:00:00-05:00" and b["end"] > "2026-10-07T10:00:00-05:00") for b in blocks)
    key = reviewed(vault, changes)
    assert runtime.apply(vault, key)["status"] == "verified"
    daily_fm = daily.read(vault, "Daily/2026-10-07.md")[0]
    assert daily_fm["blocks"] == blocks
    changes, blocks = daily.plan(vault, wake="2026-10-07T09:00:00-05:00", energy=1, timezone="America/Chicago", calendar=calendar)
    assert all(b["task"] == support for b in blocks)
    with pytest.raises(ValueError, match="calendar_unknown"):
        daily.plan(vault, wake="2026-10-07T09:00:00-05:00", energy=4, timezone="America/Chicago", calendar={"status": "stale"})


def test_weekend_business_buffer_dst(vault):
    task(vault, "admin", modality="administrative", urgency_tier=4)
    _, blocks = daily.plan(vault, wake="2026-10-10T09:00:00-05:00", energy=5, timezone="America/Chicago", calendar=calendar_observation())
    assert not blocks
    assert daily.business_date("2026-10-09", 3) == "2026-10-14"
    assert daily.local_stamp("2026-11-02T09:00:00-06:00", "America/Chicago").utcoffset() == timedelta(hours=-6)
    with pytest.raises(ValueError):
        daily.local_stamp("2026-11-02T09:00:00-05:00", "America/Chicago")


def test_learning_once_and_pause_modes(vault):
    task(vault, "completed", status="done", timeEstimate=30, startedAt="2026-10-07T09:00:00-05:00", completedAt="2026-10-07T10:00:00-05:00")
    changes, result = daily.audit(vault, now="2026-10-07T18:00:00-05:00", timezone="America/Chicago")
    assert len(result["learned_sessions"]) == 1
    runtime.apply(vault, reviewed(vault, changes))
    changes, result = daily.audit(vault, now="2026-10-07T18:00:00-05:00", timezone="America/Chicago")
    assert not result["learned_sessions"]
    learned = daily.read(vault, "System/Memory.md")[0]["cognitive_modality_defaults"]
    for mode in ("maintenance", "rest", "flow", "vacation"):
        changes, _ = daily.pause(vault, mode=mode, now="2026-10-07T18:00:00-05:00", timezone="America/Chicago", until="2026-10-10" if mode == "vacation" else None)
        runtime.apply(vault, reviewed(vault, changes))
        assert daily.read(vault, "System/Memory.md")[0]["cognitive_modality_defaults"] == learned


def test_real_result_receipts_and_manual_retry(vault):
    receipts.begin(vault, "America/Chicago", "morning")
    now = datetime(2026, 10, 7, 22, tzinfo=timezone.utc)
    assert receipts.gate(vault, "America/Chicago", "16:00", now=now)["wake_agent"]
    key = receipts.save_result(vault, "America/Chicago", "audit", {"findings": [], "checked_records": 2}, now=now)
    assert not receipts.gate(vault, "America/Chicago", "16:00", now=now)["wake_agent"]
    assert receipts.begin(vault, "America/Chicago", "audit")["status"] == "entered"
    path = runtime.state_root(vault) / "results" / (key + ".json")
    path.write_text('{"stage":"audit"}', encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        receipts.gate(vault, "America/Chicago", "16:00", now=now)


def test_package_update_collision_remove_rollback(tmp_path):
    target = tmp_path / "package" / "chrysalis"
    assert lifecycle("install", target)["status"] == "preview"
    assert not target.exists()
    assert lifecycle("install", target, apply=True)["status"] == "verified"
    learned = target.parent / "learned" / "chrysalis-personal" / "SKILL.md"
    learned.parent.mkdir(parents=True)
    learned.write_text("Synthetic learned procedure", encoding="utf-8")
    (target / "skills/chrysalis-daily/SKILL.md").write_text("Synthetic local override", encoding="utf-8")
    assert lifecycle("install", target, apply=True)["status"] == "conflict"
    assert "Synthetic local override" in (target / "skills/chrysalis-daily/SKILL.md").read_text()
    shutil.copyfile(ROOT / "skills/chrysalis-daily/SKILL.md", target / "skills/chrysalis-daily/SKILL.md")
    assert lifecycle("remove", target, apply=True)["status"] == "verified"
    assert learned.read_text() == "Synthetic learned procedure"
    assert lifecycle("rollback", target, apply=True)["status"] == "verified"
    assert (target / "run.py").is_file()
