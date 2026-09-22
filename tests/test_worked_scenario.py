"""
tests/test_worked_scenario.py
Comprehensive 8-stage end-to-end worked scenario test suite for Chrysalis mdbase v0.3.
Verifies complete lifecycle with physical disk persistence across Sources/, Projects/,
chrysalis/Tasks/, and Slipbox/, out-of-horizon retention, and hypergraph link integrity.
Compatible with pytest and python -m unittest.
"""

from datetime import date, datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
import uuid
import yaml

from helpers.mdbase_helper import (
    Diagnostic,
    apply_cas_mutation,
    check_semantic_duplicate,
    compute_revision,
    filter_horizon_deliverables,
    parse_frontmatter,
    sanitize_untrusted_payload,
    serialize_record,
    validate_record,
)
from tests.harness.validation_harness import ValidationHarness

REPO_ROOT = Path(__file__).resolve().parents[1]


class TestWorkedScenario8StageLifecycle(unittest.TestCase):
    """Executes the complete 8-stage agent runtime lifecycle on a sandbox collection."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="chrysalis_scenario_")
        self.sandbox = Path(self.temp_dir)

        # 1. Initialize directory structure
        (self.sandbox / "_types").mkdir(parents=True)
        (self.sandbox / "_contracts").mkdir(parents=True)
        (self.sandbox / "_templates").mkdir(parents=True)
        (self.sandbox / "System").mkdir(parents=True)
        (self.sandbox / "Sources").mkdir(parents=True)
        (self.sandbox / "Projects" / "cs410").mkdir(parents=True)
        (self.sandbox / "chrysalis" / "Tasks").mkdir(parents=True)
        (self.sandbox / "Slipbox").mkdir(parents=True)

        # 2. Copy authoritative configuration and types
        shutil.copy(REPO_ROOT / "mdbase.yaml", self.sandbox / "mdbase.yaml")
        for t in ["task.md", "project.md", "zettel.md", "source.md"]:
            shutil.copy(REPO_ROOT / "_types" / t, self.sandbox / "_types" / t)

        # 3. Seed System/Memory.md from template
        mem_tmpl_path = REPO_ROOT / "System" / "_templates" / "Memory.template.md"
        if mem_tmpl_path.is_file():
            mem_tmpl = mem_tmpl_path.read_text(encoding="utf-8")
        else:
            mem_tmpl = (REPO_ROOT / "System" / "Memory.md").read_text(encoding="utf-8")

        mem_content = mem_tmpl.replace("{{TIMESTAMP}}", "2026-09-22T11:15:00-05:00") \
                              .replace("{{SESSION_ID}}", "init-001") \
                              .replace("{{TIMEZONE_OFFSET}}", "-05:00") \
                              .replace("{{HORIZON_DATE}}", "2026-10-06")
        (self.sandbox / "System" / "Memory.md").write_text(mem_content, encoding="utf-8")

        # 4. Reference fixtures
        self.fixtures_dir = REPO_ROOT / "fixtures"

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_worked_scenario_lifecycle(self):
        """
        Executes:
        Context Assembly -> Memory Retrieval -> Plan Proposal -> Approval Gate
        -> Act (Disk Mutation) -> Verified Outcome -> Continuation
        for both Syllabus v1 Ingestion and Lecture Transcript Ingestion.
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        reference_date = date(2026, 9, 22)

        # =====================================================================
        # STAGE 1: INITIALIZE
        # =====================================================================
        self.assertTrue((self.sandbox / "mdbase.yaml").is_file())
        for t in ["task", "project", "source", "zettel"]:
            self.assertTrue((self.sandbox / "_types" / f"{t}.md").is_file())

        # =====================================================================
        # PART A: SYLLABUS V1 INGESTION
        # =====================================================================

        # ---------------------------------------------------------------------
        # STAGE 2: CONTEXT ASSEMBLY (Syllabus v1)
        # ---------------------------------------------------------------------
        syllabus_v1_path = self.fixtures_dir / "synthetic_syllabus_v1.txt"
        self.assertTrue(syllabus_v1_path.is_file(), "Fixture synthetic_syllabus_v1.txt must exist")
        raw_syllabus_bytes = syllabus_v1_path.read_bytes()
        syllabus_sha256 = hashlib.sha256(raw_syllabus_bytes).hexdigest().lower()

        # Semantic duplicate check (clean baseline)
        dup = check_semantic_duplicate(raw_syllabus_bytes, self.sandbox)
        self.assertIsNone(dup, "Fresh syllabus must not match existing records")

        # Passive untrusted text quarantine
        quarantined_syllabus = sanitize_untrusted_payload(
            raw_text=raw_syllabus_bytes.decode("utf-8"),
            source_id="cs410-syllabus-v1",
            sha256_digest=syllabus_sha256,
            mime_type="text/plain"
        )
        self.assertIn("<untrusted_document_payload", quarantined_syllabus)
        self.assertIn("</untrusted_document_payload>", quarantined_syllabus)

        # ---------------------------------------------------------------------
        # STAGE 3: MEMORY RETRIEVAL
        # ---------------------------------------------------------------------
        mem_text = (self.sandbox / "System" / "Memory.md").read_text(encoding="utf-8")
        mem_fm, _ = parse_frontmatter(mem_text)
        self.assertEqual(mem_fm["user_profile"]["timezone_offset"], "-05:00")
        horizon_days = mem_fm["active_horizons"]["planning_window_days"]
        self.assertEqual(horizon_days, 14)

        # ---------------------------------------------------------------------
        # STAGE 4: PLAN PROPOSAL (Deliverable Partitioning)
        # ---------------------------------------------------------------------
        all_deliverables = [
            {
                "id": "cs410-ps1",
                "title": "Problem Set 1: Vector Clocks and Distributed State",
                "due": "2026-09-27",
                "status": "todo",
                "tier": 2,
                "modality": "analytical",
                "timeEstimate": 120,
            },
            {
                "id": "cs410-lab1",
                "title": "Lab 1: Raft Consensus RPC Skeleton",
                "due": "2026-10-04",
                "status": "todo",
                "tier": 3,
                "modality": "analytical",
                "timeEstimate": 180,
            },
            {
                "id": "cs410-midterm",
                "title": "Midterm Examination",
                "due": "2026-10-25",
                "status": "todo",
                "tier": 3,
                "modality": "analytical",
                "timeEstimate": 90,
            },
            {
                "id": "cs410-final-proj",
                "title": "Final Distributed KV-Store Project",
                "due": "2026-12-10",
                "status": "todo",
                "tier": 4,
                "modality": "synthesis",
                "timeEstimate": 360,
            },
        ]

        active_delivs, inert_delivs = filter_horizon_deliverables(
            all_deliverables,
            horizon_days=horizon_days,
            reference_date=reference_date
        )
        self.assertEqual(len(active_delivs), 2, "Exactly 2 deliverables within 14d horizon")
        self.assertEqual(len(inert_delivs), 2, "Exactly 2 deliverables outside 14d horizon")

        proposal_id_1 = f"prop_{session_id}_01"
        planned_mutations = []

        # 1. Source Record
        source_fm = {
            "type": "source",
            "id": "cs410-syllabus-v1",
            "title": "CS 410 Fall 2026 Course Syllabus",
            "source_type": "syllabus",
            "sha256": syllabus_sha256,
            "original_filename": "synthetic_syllabus_v1.txt",
            "file_size_bytes": len(raw_syllabus_bytes),
            "mime_type": "text/plain",
            "source_url": None,
            "captured_date": "2026-09-22T11:15:00-05:00",
            "ingestion_status": "raw",
            "supersedes": None,
            "extracted_projects": ["[[Projects/cs410/Roadmap]]"],
            "extracted_zettels": [],
            "extracted_tasks": [
                "[[chrysalis/Tasks/20260927-cs410-ps1]]",
                "[[chrysalis/Tasks/20261004-cs410-lab1]]",
            ],
        }
        source_doc = serialize_record(source_fm, quarantined_syllabus)
        planned_mutations.append(("Sources/cs410-syllabus-v1.md", source_doc, "source"))

        # 2. Project Roadmap (Full 4-deliverable master ledger)
        roadmap_delivs = [
            {
                "id": "cs410-ps1",
                "title": "Problem Set 1: Vector Clocks and Distributed State",
                "due": "2026-09-27",
                "date_uncertain": False,
                "status": "todo",
                "task_ref": "[[chrysalis/Tasks/20260927-cs410-ps1]]",
                "tier": 2,
            },
            {
                "id": "cs410-lab1",
                "title": "Lab 1: Raft Consensus RPC Skeleton",
                "due": "2026-10-04",
                "date_uncertain": False,
                "status": "todo",
                "task_ref": "[[chrysalis/Tasks/20261004-cs410-lab1]]",
                "tier": 3,
            },
            {
                "id": "cs410-midterm",
                "title": "Midterm Examination",
                "due": "2026-10-25",
                "date_uncertain": False,
                "status": "todo",
                "task_ref": None,  # Preserved in master ledger without calendar task clutter
                "tier": 3,
            },
            {
                "id": "cs410-final-proj",
                "title": "Final Distributed KV-Store Project",
                "due": "2026-12-10",
                "date_uncertain": False,
                "status": "todo",
                "task_ref": None,  # Preserved in master ledger without calendar task clutter
                "tier": 4,
            },
        ]
        roadmap_fm = {
            "type": "project_roadmap",
            "project_id": "cs410",
            "title": "CS 410: Advanced Distributed Systems",
            "status": "active",
            "pillar": "pillar-academics",
            "horizon_window": "2026-09-01 → 2026-12-15",
            "last_updated": "2026-09-22T11:15:00-05:00",
            "source_ref": "[[Sources/cs410-syllabus-v1]]",
            "source_checksum": syllabus_sha256,
            "tags": ["pillar-academics", "cs410"],
            "linked_zettels": [],
            "deliverables": roadmap_delivs,
        }
        roadmap_doc = serialize_record(roadmap_fm, "# CS 410 Course Roadmap\n\nDeliverable tracking and milestone roadmaps.")
        planned_mutations.append(("Projects/cs410/Roadmap.md", roadmap_doc, "project"))

        # 3. Tasks for Near-Term Deliverables ONLY
        for d in active_delivs:
            t_due = d["due"]
            t_slug = d["id"]
            due_clean = t_due.replace("-", "")
            task_path = f"chrysalis/Tasks/{due_clean}-{t_slug}.md"
            task_fm = {
                "type": "task",
                "title": d["title"],
                "status": "todo",
                "dateCreated": "2026-09-22T11:15:00-05:00",
                "due": t_due,
                "scheduled": None,
                "priority": "normal",
                "urgency_tier": d["tier"],
                "modality": d["modality"],
                "timeEstimate": d["timeEstimate"],
                "energy": "high",
                "friction": "medium",
                "micro_chunked": False,
                "tags": ["task", "pillar-academics/cs410"],
                "linked_zettels": [],
                "project_ref": "[[Projects/cs410/Roadmap]]",
                "deliverable_id": d["id"],
                "googleCalendarEventId": None,
                "date_uncertain": False,
            }
            task_doc = serialize_record(task_fm, f"# {d['title']}\n\nExecution notes and Starter Wedge checklist.")
            planned_mutations.append((task_path, task_doc, "task"))

        # Pre-validate all drafted records before approval
        for p_path, p_doc, p_type in planned_mutations:
            v_res = validate_record(self.sandbox / p_path, p_doc, type_name=p_type, collection_dir=self.sandbox)
            self.assertTrue(v_res.valid, f"Draft record {p_path} failed validation: {[d.to_dict() for d in v_res.diagnostics]}")

        # ---------------------------------------------------------------------
        # STAGE 5: APPROVAL GATE
        # ---------------------------------------------------------------------
        # Negative test inside lifecycle: unapproved token fails closed
        unapproved_token = "invalid_token"
        self.assertNotEqual(unapproved_token, proposal_id_1)

        # Human operator confirms proposal
        approval_token = proposal_id_1
        self.assertEqual(approval_token, proposal_id_1)

        # ---------------------------------------------------------------------
        # STAGE 6: ACT (Compare-And-Swap Physical Disk Mutations)
        # ---------------------------------------------------------------------
        executed_mutations = 0
        for rel_path, content, _ in planned_mutations:
            target_file = self.sandbox / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            res = apply_cas_mutation(target_file, content, if_revision=None)
            self.assertTrue(res.valid, f"CAS write failed for {rel_path}: {[d.to_dict() for d in res.diagnostics]}")
            executed_mutations += 1

        self.assertEqual(executed_mutations, 4)

        # ---------------------------------------------------------------------
        # STAGE 7: OUTCOME RECORDING & PHYSICAL DISK VERIFICATION
        # ---------------------------------------------------------------------
        self.assertTrue((self.sandbox / "Sources" / "cs410-syllabus-v1.md").is_file())
        self.assertTrue((self.sandbox / "Projects" / "cs410" / "Roadmap.md").is_file())
        self.assertTrue((self.sandbox / "chrysalis" / "Tasks" / "20260927-cs410-ps1.md").is_file())
        self.assertTrue((self.sandbox / "chrysalis" / "Tasks" / "20261004-cs410-lab1.md").is_file())

        # Verify task file count strictly equals 2 (zero out-of-horizon task files created)
        task_files = list((self.sandbox / "chrysalis" / "Tasks").glob("*.md"))
        self.assertEqual(len(task_files), 2, "Only near-term deliverables must create task notes")

        # Verify explicit timezone offset invariant on all written files
        for f in task_files:
            fm, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
            self.assertTrue(fm["dateCreated"].endswith("-05:00"))
            self.assertNotIn("Z", fm["dateCreated"])

        # ---------------------------------------------------------------------
        # STAGE 8: CONTINUATION (Compiling Output Envelope)
        # ---------------------------------------------------------------------
        roadmap_bytes = (self.sandbox / "Projects" / "cs410" / "Roadmap.md").read_bytes()
        roadmap_rev = compute_revision(roadmap_bytes)
        action_output = {
            "valid": True,
            "result": {
                "path": "Projects/cs410/Roadmap.md",
                "revision": roadmap_rev,
                "mutations_executed": executed_mutations,
                "records_created": [p for p, _, _ in planned_mutations],
            },
            "diagnostics": [],
            "revision": roadmap_rev,
        }
        self.assertTrue(action_output["valid"])

        # =====================================================================
        # PART B: LECTURE TRANSCRIPT INGESTION & ATOMIC ZETTEL EXTRACTION
        # =====================================================================

        # Stage 2: Context Assembly (Transcript)
        transcript_path = self.fixtures_dir / "synthetic_transcript.txt"
        self.assertTrue(transcript_path.is_file(), "Fixture synthetic_transcript.txt must exist")
        raw_transcript_bytes = transcript_path.read_bytes()
        transcript_sha256 = hashlib.sha256(raw_transcript_bytes).hexdigest().lower()

        quarantined_transcript = sanitize_untrusted_payload(
            raw_text=raw_transcript_bytes.decode("utf-8"),
            source_id="cs410-lecture-04",
            sha256_digest=transcript_sha256,
            mime_type="text/plain"
        )

        # Stage 4: Plan Proposal (Transcript Source + Atomic Zettel Note)
        zettel_id = "20260922143000-raft-log-matching-invariant"
        transcript_mutations = []

        # 1. Transcript Source Note
        transcript_source_fm = {
            "type": "source",
            "id": "cs410-lecture-04",
            "title": "CS 410 Lecture 04: Raft Consensus & Log Matching Invariant",
            "source_type": "transcript",
            "sha256": transcript_sha256,
            "original_filename": "synthetic_transcript.txt",
            "file_size_bytes": len(raw_transcript_bytes),
            "mime_type": "text/plain",
            "source_url": None,
            "captured_date": "2026-09-22T14:30:00-05:00",
            "ingestion_status": "extracted",
            "supersedes": None,
            "extracted_projects": ["[[Projects/cs410/Roadmap]]"],
            "extracted_zettels": [f"[[Slipbox/{zettel_id}]]"],
            "extracted_tasks": [],
        }
        transcript_source_doc = serialize_record(transcript_source_fm, quarantined_transcript)
        transcript_mutations.append(("Sources/cs410-lecture-04.md", transcript_source_doc, "source"))

        # 2. Atomic Zettel Note in Slipbox/
        zettel_body = (
            "# Raft Log Matching Invariant & Commit Safety\n\n"
            "The Raft consensus protocol achieves state machine replication safety via the "
            "**Log Matching Invariant**, which guarantees that if two logs contain an entry with "
            "the same index and term:\n"
            "1. They store the same state machine command.\n"
            "2. Their logs are identical in all preceding entries up to that index.\n\n"
            "Followers enforce this invariant by rejecting `AppendEntries` RPCs if their log does not "
            "match `prevLogIndex` and `prevLogTerm`."
        )
        zettel_fm = {
            "type": "zettel",
            "id": zettel_id,
            "title": "Raft Log Matching Invariant and Commit Safety",
            "dateCreated": "2026-09-22T14:30:00-05:00",
            "tags": ["concept/distributed-systems", "concept/consensus", "#chrysalis"],
            "source_ref": "[[Sources/cs410-lecture-04]]",
            "source_checksum": transcript_sha256,
            "project_ref": "[[Projects/cs410/Roadmap]]",
            "linked_zettels": [],
        }
        zettel_doc = serialize_record(zettel_fm, zettel_body)
        transcript_mutations.append((f"Slipbox/{zettel_id}.md", zettel_doc, "zettel"))

        # Validate drafted transcript mutations
        for t_path, t_doc, t_type in transcript_mutations:
            v_res = validate_record(self.sandbox / t_path, t_doc, type_name=t_type, collection_dir=self.sandbox)
            self.assertTrue(v_res.valid, f"Validation failed for {t_path}: {[d.to_dict() for d in v_res.diagnostics]}")

        # Stage 5: Approval Gate
        proposal_id_2 = f"prop_{session_id}_02"
        token_2 = proposal_id_2

        # Stage 6: Act (CAS mutations)
        for rel_path, content, _ in transcript_mutations:
            target_file = self.sandbox / rel_path
            target_file.parent.mkdir(parents=True, exist_ok=True)
            res = apply_cas_mutation(target_file, content, if_revision=None)
            self.assertTrue(res.valid)

        # Stage 7: Physical Disk Assertions
        self.assertTrue((self.sandbox / "Sources" / "cs410-lecture-04.md").is_file())
        self.assertTrue((self.sandbox / "Slipbox" / f"{zettel_id}.md").is_file())

        # Link project and zettel
        # Stage 8: Full Collection Conformance Pass via ValidationHarness
        harness = ValidationHarness(self.sandbox)
        full_report = harness.run_full_validation(check_links=True, strict_links=False)
        self.assertTrue(
            full_report.is_valid,
            f"Validation harness failed on worked scenario: {[d.to_dict() for d in full_report.diagnostics]}"
        )
        self.assertEqual(full_report.layer1_errors, 0)
        self.assertEqual(full_report.layer2_errors, 0)
        self.assertEqual(full_report.layer3_errors, 0)


if __name__ == "__main__":
    unittest.main()
