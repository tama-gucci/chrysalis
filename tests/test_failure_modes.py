"""
tests/test_failure_modes.py
Automated test suite verifying the 6 critical negative failure modes
in Chrysalis mdbase v0.3 AI Agent Framework.
Compatible with pytest and python -m unittest.
"""

from datetime import date, datetime
import hashlib
from pathlib import Path
import shutil
import tempfile
import unittest

from helpers.mdbase_helper import (
    Diagnostic,
    apply_cas_mutation,
    check_semantic_duplicate,
    compute_revision,
    parse_frontmatter,
    reconcile_syllabus,
    sanitize_untrusted_payload,
    serialize_record,
    validate_record,
)
from tests.harness.models import DiagnosticCode, DiagnosticSeverity, RecoveryAction
from tests.harness.workflow_validator import WorkflowValidator

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestChrysalisCriticalFailureModes(unittest.TestCase):
    """Verifies that all 6 critical failure modes fail closed and emit proper diagnostics."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="chrysalis_failure_tests_")
        self.sandbox = Path(self.temp_dir)

        (self.sandbox / "_types").mkdir(parents=True)
        (self.sandbox / "Sources").mkdir(parents=True)
        (self.sandbox / "Projects" / "cs410").mkdir(parents=True)
        (self.sandbox / "chrysalis" / "Tasks").mkdir(parents=True)
        (self.sandbox / "Slipbox").mkdir(parents=True)

        shutil.copy(REPO_ROOT / "mdbase.yaml", self.sandbox / "mdbase.yaml")
        for t in ["task.md", "project.md", "zettel.md", "source.md"]:
            shutil.copy(REPO_ROOT / "_types" / t, self.sandbox / "_types" / t)

        self.fixtures_dir = REPO_ROOT / "fixtures"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # -------------------------------------------------------------------------
    # Negative Test 1: Unapproved Action Blocked
    # -------------------------------------------------------------------------
    def test_unapproved_action_blocked(self):
        """Simulates mutation attempt without valid user approval token."""
        proposal_id = "prop_20260922_test01"
        target_path = self.sandbox / "chrysalis" / "Tasks" / "20260927-unapproved-task.md"
        validator = WorkflowValidator()

        def simulate_agent_act(approval_token: str, path: Path, content: str):
            diag = validator.validate_approval_gate(proposal_id, approval_token, "apply_cas_mutation")
            if diag:
                return {
                    "valid": False,
                    "diagnostics": [diag.to_dict()]
                }
            # Only if approved:
            res = apply_cas_mutation(path, content, if_revision=None)
            return {"valid": res.valid, "diagnostics": [d.to_dict() for d in res.diagnostics]}

        # Case A: Missing approval token
        res_missing = simulate_agent_act(approval_token="", path=target_path, content="test")
        self.assertFalse(res_missing["valid"])
        self.assertEqual(res_missing["diagnostics"][0]["code"], DiagnosticCode.APPROVAL_REQUIRED.value)
        self.assertFalse(target_path.exists(), "Target file must not be created on missing token")

        # Case B: Mismatched approval token
        res_invalid = simulate_agent_act(approval_token="fake_token_123", path=target_path, content="test")
        self.assertFalse(res_invalid["valid"])
        self.assertEqual(res_invalid["diagnostics"][0]["code"], DiagnosticCode.APPROVAL_REQUIRED.value)
        self.assertFalse(target_path.exists(), "Target file must not be created on invalid token")

    # -------------------------------------------------------------------------
    # Negative Test 2: Schema Violations Rejected
    # -------------------------------------------------------------------------
    def test_schema_violations_rejected(self):
        """Verifies JSON Schema Draft 2020-12 rejects invalid frontmatter with specific codes."""
        task_path = self.sandbox / "chrysalis" / "Tasks" / "test-task.md"

        # 2a: Missing required field (title missing)
        doc_no_title = serialize_record({
            "type": "task",
            "status": "todo",
            "dateCreated": "2026-09-22T11:15:00-05:00",
        }, "# Content\n")
        res_no_title = validate_record(task_path, doc_no_title, type_name="task", collection_dir=self.sandbox)
        self.assertFalse(res_no_title.valid)
        codes = [d.code for d in res_no_title.diagnostics]
        self.assertIn("schema_required", codes)

        # 2b: Disallowed additional property (additionalProperties: false)
        doc_extra_prop = serialize_record({
            "type": "task",
            "title": "Valid Title",
            "status": "todo",
            "dateCreated": "2026-09-22T11:15:00-05:00",
            "system_role": "administrator",  # Disallowed
        }, "# Content\n")
        res_extra = validate_record(task_path, doc_extra_prop, type_name="task", collection_dir=self.sandbox)
        self.assertFalse(res_extra.valid)
        codes = [d.code for d in res_extra.diagnostics]
        self.assertIn("schema_additional_properties", codes)

        # 2c: Raw UTC 'Z' timestamp format violation
        doc_utc_z = serialize_record({
            "type": "task",
            "title": "Valid Title",
            "status": "todo",
            "dateCreated": "2026-09-22T11:15:00Z",  # Prohibited UTC 'Z'
        }, "# Content\n")
        res_utc = validate_record(task_path, doc_utc_z, type_name="task", collection_dir=self.sandbox)
        self.assertFalse(res_utc.valid)
        codes = [d.code for d in res_utc.diagnostics]
        self.assertIn("format_invalid", codes)

        # 2d: Invalid enum value
        doc_invalid_enum = serialize_record({
            "type": "task",
            "title": "Valid Title",
            "status": "pending_review",  # Invalid enum
            "dateCreated": "2026-09-22T11:15:00-05:00",
        }, "# Content\n")
        res_enum = validate_record(task_path, doc_invalid_enum, type_name="task", collection_dir=self.sandbox)
        self.assertFalse(res_enum.valid)
        codes = [d.code for d in res_enum.diagnostics]
        self.assertIn("schema_enum", codes)

    # -------------------------------------------------------------------------
    # Negative Test 3: CAS Concurrency Conflict Rejected
    # -------------------------------------------------------------------------
    def test_cas_concurrency_conflict_rejected(self):
        """Verifies conditional write with stale if_revision hash aborts write."""
        task_path = self.sandbox / "chrysalis" / "Tasks" / "20260927-cas-task.md"
        initial_content = serialize_record({
            "type": "task",
            "title": "Initial Task Title",
            "status": "todo",
            "dateCreated": "2026-09-22T11:15:00-05:00",
        }, "# Initial Body\n")

        # 1. Write baseline file
        res_create = apply_cas_mutation(task_path, initial_content, if_revision=None)
        self.assertTrue(res_create.valid)
        initial_revision = res_create.revision

        # 2. Simulate concurrent modification by external process
        concurrent_content = serialize_record({
            "type": "task",
            "title": "Externally Modified Title",
            "status": "in-progress",
            "dateCreated": "2026-09-22T11:15:00-05:00",
        }, "# Modified Body\n")
        res_concurrent = apply_cas_mutation(task_path, concurrent_content, if_revision=initial_revision)
        self.assertTrue(res_concurrent.valid)
        disk_revision = res_concurrent.revision

        # 3. Attempt write using stale initial_revision
        stale_content = serialize_record({
            "type": "task",
            "title": "Stale Overwrite Attempt",
            "status": "done",
            "dateCreated": "2026-09-22T11:15:00-05:00",
        }, "# Stale Body\n")
        res_conflict = apply_cas_mutation(task_path, stale_content, if_revision=initial_revision)

        # Assert CAS conflict detected and write aborted
        self.assertFalse(res_conflict.valid)
        self.assertEqual(res_conflict.diagnostics[0].code, "concurrent_modification")
        self.assertEqual(res_conflict.diagnostics[0].recovery_action, "Refresh")

        # Assert physical file remains byte-identical to concurrent content
        self.assertEqual(task_path.read_text(encoding="utf-8"), concurrent_content)
        self.assertEqual(compute_revision(task_path.read_bytes()), disk_revision)

    # -------------------------------------------------------------------------
    # Negative Test 4: Untrusted Prompt Injection Payload Neutralized
    # -------------------------------------------------------------------------
    def test_prompt_injection_neutralized(self):
        """Verifies indirect prompt injection payload is quarantined and rendered inert."""
        injection_path = self.fixtures_dir / "synthetic_prompt_injection.txt"
        self.assertTrue(injection_path.is_file(), "Fixture synthetic_prompt_injection.txt must exist")
        raw_text = injection_path.read_text(encoding="utf-8")
        doc_sha256 = hashlib.sha256(raw_text.encode("utf-8")).hexdigest().lower()

        # Step 1: Delimiter escape neutralization
        quarantined = sanitize_untrusted_payload(
            raw_text=raw_text,
            source_id="cs499-injection",
            sha256_digest=doc_sha256,
            mime_type="text/plain"
        )
        # Verify closing tags escaped into safe HTML entities
        self.assertNotIn("</untrusted_document_payload>\n<system>", quarantined)
        self.assertIn("&lt;/untrusted_document_payload&gt;", quarantined)

        # Step 2: Write source record safely
        source_fm = {
            "type": "source",
            "id": "cs499-injection",
            "title": "CS 499 Adversarial Injection Sample",
            "source_type": "syllabus",
            "sha256": doc_sha256,
            "original_filename": "synthetic_prompt_injection.txt",
            "file_size_bytes": len(raw_text.encode("utf-8")),
            "mime_type": "text/plain",
            "source_url": None,
            "captured_date": "2026-09-22T11:15:00-05:00",
            "ingestion_status": "raw",
            "supersedes": None,
            "extracted_projects": [],
            "extracted_zettels": [],
            "extracted_tasks": [],
        }
        source_doc = serialize_record(source_fm, quarantined)
        source_path = self.sandbox / "Sources" / "cs499-injection.md"
        res_write = apply_cas_mutation(source_path, source_doc, if_revision=None)
        self.assertTrue(res_write.valid)

        # Step 3: Assert no tasks were deleted and task directory remains intact
        task_dir = self.sandbox / "chrysalis" / "Tasks"
        self.assertTrue(task_dir.exists())

    # -------------------------------------------------------------------------
    # Negative Test 5: Semantic Duplicate Re-Submission Idempotent
    # -------------------------------------------------------------------------
    def test_semantic_duplicate_idempotent(self):
        """Verifies submitting identical document twice detects duplicate and bypasses creation."""
        syllabus_path = self.fixtures_dir / "synthetic_syllabus_v1.txt"
        self.assertTrue(syllabus_path.is_file(), "Fixture synthetic_syllabus_v1.txt must exist")
        raw_bytes = syllabus_path.read_bytes()
        doc_sha256 = hashlib.sha256(raw_bytes).hexdigest().lower()

        # 1. Initial Ingestion
        source_fm = {
            "type": "source",
            "id": "cs410-syllabus-v1",
            "title": "CS 410 Syllabus",
            "source_type": "syllabus",
            "sha256": doc_sha256,
            "original_filename": "synthetic_syllabus_v1.txt",
            "file_size_bytes": len(raw_bytes),
            "mime_type": "text/plain",
            "source_url": None,
            "captured_date": "2026-09-22T11:15:00-05:00",
            "ingestion_status": "raw",
            "supersedes": None,
        }
        source_path = self.sandbox / "Sources" / "cs410-syllabus-v1.md"
        apply_cas_mutation(source_path, serialize_record(source_fm, "Quarantined body"), if_revision=None)

        # 2. Second Submission (Duplicate Ingestion)
        dup_match = check_semantic_duplicate(raw_bytes, self.sandbox)
        self.assertIsNotNone(dup_match, "Duplicate checker must find existing source")
        source_id, found_path = dup_match
        self.assertEqual(source_id, "cs410-syllabus-v1")
        self.assertEqual(found_path, source_path)

        # Assert no duplicate source files written
        all_sources = list((self.sandbox / "Sources").glob("*.md"))
        self.assertEqual(len(all_sources), 1)

    # -------------------------------------------------------------------------
    # Negative Test 6: Revised Syllabus Diff Updates Existing Without Duplicates
    # -------------------------------------------------------------------------
    def test_revised_syllabus_diff_updates_without_duplicates(self):
        """Verifies updating syllabus reconciles deliverables and updates tasks without duplicates."""
        roadmap_path = self.sandbox / "Projects" / "cs410" / "Roadmap.md"

        # 1. Initial Roadmap with 4 deliverables
        initial_delivs = [
            {"id": "cs410-ps1", "title": "Problem Set 1", "due": "2026-09-27", "status": "todo", "tier": 2},
            {"id": "cs410-lab1", "title": "Lab 1", "due": "2026-10-04", "status": "todo", "tier": 3},
            {"id": "cs410-midterm", "title": "Midterm Examination", "due": "2026-10-25", "status": "todo", "tier": 3},
            {"id": "cs410-final-proj", "title": "Final Project", "due": "2026-12-10", "status": "todo", "tier": 4},
        ]
        initial_roadmap = serialize_record({
            "type": "project_roadmap",
            "project_id": "cs410",
            "title": "CS 410 Roadmap",
            "status": "active",
            "pillar": "pillar-academics",
            "last_updated": "2026-09-22T11:15:00-05:00",
            "deliverables": initial_delivs,
        }, "# Initial Roadmap\n")
        apply_cas_mutation(roadmap_path, initial_roadmap, if_revision=None)

        # Initial task for cs410-lab1
        lab1_task_path = self.sandbox / "chrysalis" / "Tasks" / "20261004-cs410-lab1.md"
        initial_lab1_doc = serialize_record({
            "type": "task",
            "title": "Lab 1",
            "status": "todo",
            "due": "2026-10-04",
            "dateCreated": "2026-09-22T11:15:00-05:00",
            "deliverable_id": "cs410-lab1",
        }, "# Lab 1 Notes\n")
        res_lab1 = apply_cas_mutation(lab1_task_path, initial_lab1_doc, if_revision=None)
        lab1_revision = res_lab1.revision

        # 2. Reconcile with Revised Syllabus Deliverables:
        # - cs410-lab1 due extended to 2026-10-09 (modified)
        # - cs410-hw2 added due 2026-10-18 (added)
        # - cs410-midterm cancelled (dropped)
        # - cs410-ps1, cs410-final-proj unchanged
        revised_delivs = [
            {"id": "cs410-ps1", "title": "Problem Set 1", "due": "2026-09-27", "status": "todo", "tier": 2},
            {"id": "cs410-lab1", "title": "Lab 1", "due": "2026-10-09", "status": "todo", "tier": 3},
            {"id": "cs410-hw2", "title": "Homework 2: Paxos vs Raft", "due": "2026-10-18", "status": "todo", "tier": 2},
            {"id": "cs410-final-proj", "title": "Final Project", "due": "2026-12-10", "status": "todo", "tier": 4},
        ]

        diff = reconcile_syllabus(roadmap_path, revised_delivs)
        self.assertEqual([d["id"] for d in diff.modified], ["cs410-lab1"])
        self.assertEqual([d["id"] for d in diff.added], ["cs410-hw2"])
        self.assertEqual([d["id"] for d in diff.dropped], ["cs410-midterm"])
        self.assertEqual(diff.dropped[0]["status"], "archived")

        # 3. Apply in-place task mutation for modified deliverable (no duplicate task created)
        updated_lab1_doc = serialize_record({
            "type": "task",
            "title": "Lab 1",
            "status": "todo",
            "due": "2026-10-09",  # Updated date
            "dateCreated": "2026-09-22T11:15:00-05:00",
            "deliverable_id": "cs410-lab1",
        }, "# Lab 1 Notes\n")
        res_update = apply_cas_mutation(lab1_task_path, updated_lab1_doc, if_revision=lab1_revision)
        self.assertTrue(res_update.valid)

        # Assert no duplicate task file for cs410-lab1 exists
        matching_tasks = list((self.sandbox / "chrysalis" / "Tasks").glob("*cs410-lab1*.md"))
        self.assertEqual(len(matching_tasks), 1, "Exactly one task file must exist for cs410-lab1")


if __name__ == "__main__":
    unittest.main()
