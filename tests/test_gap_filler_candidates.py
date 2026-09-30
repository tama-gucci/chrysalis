"""
tests/test_gap_filler_candidates.py
Unit tests verifying quick-capture gap-filler prioritization and inference fallback for /plan.
"""
from datetime import date
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from helpers.mdbase_helper import (
    format_gap_fillers_markdown,
    is_quick_capture_task,
    main as mdbase_cli_main,
    select_gap_filler_candidates,
)


class TestGapFillerCandidates(unittest.TestCase):
    def setUp(self):
        self.repo_root = Path(__file__).resolve().parent.parent
        self.temp_dir = Path(tempfile.mkdtemp(prefix="chrysalis_gap_filler_test_"))
        self.vault = self.temp_dir / "vault"
        self.vault.mkdir(parents=True, exist_ok=True)
        for sub in ("TaskNotes/Tasks", "Projects/compiler-pipeline", "System", "Sources"):
            (self.vault / sub).mkdir(parents=True, exist_ok=True)

        shutil.copy2(self.repo_root / "mdbase.yaml", self.vault / "mdbase.yaml")
        shutil.copy2(
            self.repo_root / "System/_templates/Life-Roadmap.template.md",
            self.vault / "System/Life-Roadmap.md",
        )
        shutil.copy2(
            self.repo_root / "System/_templates/Memory.template.md",
            self.vault / "System/Memory.md",
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _write_task(self, filename: str, fm: dict, body: str = "# Task Content\n"):
        task_file = self.vault / "TaskNotes" / "Tasks" / filename
        import yaml
        content = f"---\n{yaml.dump(fm, sort_keys=False)}---\n\n{body}"
        task_file.write_text(content, encoding="utf-8")
        return task_file

    def _write_roadmap(self, project_subpath: str, fm: dict, body: str = "# Roadmap\n"):
        rm_file = self.vault / "Projects" / project_subpath / "Roadmap.md"
        rm_file.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        content = f"---\n{yaml.dump(fm, sort_keys=False)}---\n\n{body}"
        rm_file.write_text(content, encoding="utf-8")
        return rm_file

    def test_01_is_quick_capture_task(self):
        """Validates detection of quick capture tasks across various signatures."""
        self.assertTrue(is_quick_capture_task({"external_item_id": "item-synthetic-12345"}))
        self.assertTrue(is_quick_capture_task({"external_source_alias": "quick-capture"}))
        self.assertTrue(is_quick_capture_task({"source_alias": "quick-capture"}))
        self.assertTrue(is_quick_capture_task({"external_integration": "google-tasks"}))
        self.assertTrue(is_quick_capture_task({"evidence_ref": "google-tasks:inbox:item-9"}))
        self.assertTrue(is_quick_capture_task({"source_ref": "[[Sources/capture-google-tasks-test]]"}))
        self.assertTrue(is_quick_capture_task({"tags": ["task", "quick-capture"]}))
        self.assertTrue(is_quick_capture_task({"capture_policy": "standalone"}))
        self.assertTrue(is_quick_capture_task({"capture_policy": "quick-capture"}))
        self.assertTrue(is_quick_capture_task({"external_source": "quick-capture"}))
        self.assertTrue(is_quick_capture_task({"external_id": "gt-12345"}))
        self.assertTrue(is_quick_capture_task({"source_ref": "[[Sources/capture_media_inbox]]"}))
        self.assertTrue(is_quick_capture_task({"source_alias": "quick_capture"}))
        self.assertTrue(is_quick_capture_task({"tags": ["task", "capture"]}))
        self.assertTrue(is_quick_capture_task({"evidence_ref": "quick_capture:note-1"}))
        self.assertTrue(is_quick_capture_task({"capture_source": "quick-capture"}))

        # Non-quick-capture tasks
        self.assertFalse(is_quick_capture_task({}))
        self.assertFalse(is_quick_capture_task({"tags": ["task", "pillar-1/admin"]}))
        self.assertFalse(is_quick_capture_task({"title": "Routine Deliverable", "project_ref": "[[Projects/X/Roadmap]]"}))
        self.assertFalse(is_quick_capture_task("not-a-dict"))

    def test_02_prioritizes_quick_capture_tasks_over_backlog(self):
        """When sufficient quick capture tasks exist, all selected candidates are quick-capture."""
        # 3 Quick-capture tasks
        self._write_task("syn-qc-item-1.md", {
            "title": "Quick Capture Item 1",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-1",
            "modality": "administrative",
            "timeEstimate": 15,
            "energy": "low",
            "friction": "low",
            "tags": ["task"],
            "urgency_tier": 2,
            "priority": "normal",
        })
        self._write_task("syn-qc-item-2.md", {
            "title": "Quick Capture Item 2",
            "status": "todo",
            "scheduled": None,
            "external_source_alias": "quick-capture",
            "modality": "kinetic",
            "timeEstimate": 30,
            "energy": "low",
            "friction": "low",
            "tags": ["task"],
            "urgency_tier": 3,
            "priority": "high",
        })
        self._write_task("syn-qc-item-3.md", {
            "title": "Quick Capture Item 3",
            "status": "todo",
            "scheduled": None,
            "source_alias": "quick-capture",
            "modality": "administrative",
            "timeEstimate": 20,
            "energy": "low",
            "friction": "low",
            "tags": ["task"],
            "urgency_tier": 2,
            "priority": "normal",
        })

        # 2 Backlog project tasks
        self._write_task("syn-project-task-1.md", {
            "title": "Compiler Benchmark Suite",
            "status": "todo",
            "scheduled": None,
            "project_ref": "[[Projects/compiler-pipeline/Roadmap]]",
            "modality": "analytical",
            "timeEstimate": 60,
            "energy": "high",
            "friction": "medium",
            "tags": ["task", "pillar-2/technical"],
        })
        self._write_task("syn-project-task-2.md", {
            "title": "Parser Syntax Generator",
            "status": "todo",
            "scheduled": None,
            "project_ref": "[[Projects/compiler-pipeline/Roadmap]]",
            "modality": "analytical",
            "timeEstimate": 75,
            "energy": "high",
            "friction": "high",
            "tags": ["task", "pillar-2/technical"],
        })

        result = select_gap_filler_candidates(
            self.vault,
            target_count=3,
            reference_date=date(2026, 10, 1),
        )

        self.assertEqual(result["quick_capture_count"], 3)
        self.assertEqual(result["inferred_count"], 0)
        self.assertFalse(result["inference_triggered"])
        self.assertEqual(len(result["candidates"]), 3)

        for c in result["candidates"]:
            self.assertEqual(c["candidate_type"], "quick_capture")
            self.assertIsNone(c["inference_source"])
            self.assertTrue(c["candidate_id"].startswith("qc-"))

    def test_03_infers_candidates_when_insufficient_quick_capture(self):
        """When fewer quick-capture tasks exist than target_count, remaining candidates are inferred."""
        # 1 Quick-capture task
        self._write_task("syn-qc-single.md", {
            "title": "Submit Synthetic Reimbursement",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-single",
            "modality": "administrative",
            "timeEstimate": 15,
            "energy": "low",
            "friction": "low",
            "tags": ["task"],
        })

        # 2 Backlog tasks
        self._write_task("syn-backlog-admin.md", {
            "title": "Clean Hardware Lab Benches",
            "status": "todo",
            "scheduled": None,
            "modality": "kinetic",
            "timeEstimate": 30,
            "energy": "low",
            "friction": "low",
            "tags": ["task"],
        })
        self._write_task("syn-backlog-synthesis.md", {
            "title": "Review Distributed System Zettels",
            "status": "todo",
            "scheduled": None,
            "modality": "synthesis",
            "timeEstimate": 45,
            "energy": "medium",
            "friction": "low",
            "tags": ["task", "chrysalis"],
        })

        result = select_gap_filler_candidates(
            self.vault,
            target_count=3,
            reference_date=date(2026, 10, 1),
        )

        self.assertEqual(result["quick_capture_count"], 1)
        self.assertEqual(result["inferred_count"], 2)
        self.assertTrue(result["inference_triggered"])
        self.assertEqual(len(result["candidates"]), 3)

        # Primary candidate is the quick-capture task
        self.assertEqual(result["candidates"][0]["candidate_id"], "qc-01")
        self.assertEqual(result["candidates"][0]["candidate_type"], "quick_capture")
        self.assertEqual(result["candidates"][0]["title"], "Submit Synthetic Reimbursement")

        # Inferred candidates follow
        self.assertEqual(result["candidates"][1]["candidate_id"], "inf-01")
        self.assertEqual(result["candidates"][1]["candidate_type"], "inferred")
        self.assertEqual(result["candidates"][2]["candidate_id"], "inf-02")
        self.assertEqual(result["candidates"][2]["candidate_type"], "inferred")

    def test_04_infers_from_roadmap_deliverables_when_no_backlog_tasks(self):
        """When no quick-capture tasks or task notes exist, infer candidates from Roadmap deliverables."""
        self._write_roadmap("compiler-pipeline", {
            "project_id": "compiler-pipeline",
            "title": "Compiler Optimization Pipeline",
            "deliverables": [
                {
                    "id": "deliv-ast-walker",
                    "title": "Implement AST Tree Walker",
                    "due": "2026-10-05",
                    "modality": "analytical",
                    "timeEstimate": 60,
                    "status": "todo",
                    "task_ref": None,
                },
                {
                    "id": "deliv-ir-emitter",
                    "title": "Synthesize LLVM IR Generator",
                    "due": "2026-10-08",
                    "modality": "analytical",
                    "timeEstimate": 75,
                    "status": "todo",
                    "task_ref": None,
                },
            ],
        })

        result = select_gap_filler_candidates(
            self.vault,
            target_count=2,
            reference_date=date(2026, 10, 1),
        )

        self.assertEqual(result["quick_capture_count"], 0)
        self.assertEqual(result["inferred_count"], 2)
        self.assertTrue(result["inference_triggered"])
        for c in result["candidates"]:
            self.assertEqual(c["candidate_type"], "inferred")
            self.assertEqual(c["inference_source"], "project_deliverable")
            self.assertTrue(c["deliverable_id"] in {"deliv-ast-walker", "deliv-ir-emitter"})

    def test_05_filters_scheduled_done_archived_and_excluded_tasks(self):
        """Tasks that are scheduled, done, archived, or in exclude_paths must not be selected."""
        # Scheduled task
        self._write_task("syn-sched.md", {
            "title": "Already Scheduled Task",
            "status": "todo",
            "scheduled": "2026-10-01T10:00:00-05:00",
            "external_item_id": "ext-sched",
        })
        # Done task
        self._write_task("syn-done.md", {
            "title": "Already Completed Task",
            "status": "done",
            "scheduled": None,
            "external_item_id": "ext-done",
        })
        # Archived task
        self._write_task("syn-archived.md", {
            "title": "Archived Task",
            "status": "archived",
            "scheduled": None,
            "external_item_id": "ext-arch",
        })
        # Active task to exclude
        self._write_task("syn-anchor-staged.md", {
            "title": "Staged Anchor Task",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-anchor",
        })
        # Eligible task
        self._write_task("syn-eligible.md", {
            "title": "Eligible Quick Capture",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-eligible",
        })

        result = select_gap_filler_candidates(
            self.vault,
            target_count=3,
            reference_date=date(2026, 10, 1),
            exclude_paths={"TaskNotes/Tasks/syn-anchor-staged.md"},
        )

        # Only ext-eligible is eligible as quick capture
        self.assertEqual(result["quick_capture_count"], 1)
        self.assertEqual(result["primary_candidates"][0]["title"], "Eligible Quick Capture")

    def test_06_sorts_quick_capture_by_deadline_and_urgency(self):
        """Quick capture candidates sort overdue > imminent > undated > future, then urgency tier."""
        self._write_task("syn-task-future.md", {
            "title": "Future Capture",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-fut",
            "due": "2026-10-25",  # > 14 days
            "urgency_tier": 4,
        })
        self._write_task("syn-task-overdue.md", {
            "title": "Overdue Capture",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-overdue",
            "due": "2026-09-28",  # overdue relative to 2026-10-01
            "urgency_tier": 2,
        })
        self._write_task("syn-task-imminent.md", {
            "title": "Imminent Capture",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-imminent",
            "due": "2026-10-03",  # imminent
            "urgency_tier": 3,
        })
        self._write_task("syn-task-undated.md", {
            "title": "Undated Capture",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-undated",
            "due": None,
            "urgency_tier": 2,
        })

        result = select_gap_filler_candidates(
            self.vault,
            target_count=4,
            reference_date=date(2026, 10, 1),
        )

        titles = [c["title"] for c in result["candidates"]]
        self.assertEqual(titles[0], "Overdue Capture")
        self.assertEqual(titles[1], "Imminent Capture")
        self.assertEqual(titles[2], "Undated Capture")
        self.assertEqual(titles[3], "Future Capture")

    def test_07_format_gap_fillers_markdown(self):
        """Verifies markdown formatting output."""
        mock_result = {
            "primary_candidates": [
                {
                    "candidate_id": "qc-01",
                    "candidate_type": "quick_capture",
                    "title": "Send invoice draft",
                    "tags": ["task"],
                    "modality": "administrative",
                    "timeEstimate": 15,
                    "energy": "low",
                    "due": "2026-10-02",
                }
            ],
            "inferred_candidates": [
                {
                    "candidate_id": "inf-01",
                    "candidate_type": "inferred",
                    "inference_source": "administrative_backlog",
                    "title": "Clean workbench",
                    "tags": ["task"],
                    "modality": "kinetic",
                    "timeEstimate": 30,
                    "energy": "low",
                    "due": None,
                }
            ],
            "candidates": [
                {
                    "candidate_id": "qc-01",
                    "candidate_type": "quick_capture",
                    "title": "Send invoice draft",
                    "tags": ["task"],
                    "modality": "administrative",
                    "timeEstimate": 15,
                    "energy": "low",
                    "due": "2026-10-02",
                },
                {
                    "candidate_id": "inf-01",
                    "candidate_type": "inferred",
                    "inference_source": "administrative_backlog",
                    "title": "Clean workbench",
                    "tags": ["task"],
                    "modality": "kinetic",
                    "timeEstimate": 30,
                    "energy": "low",
                    "due": None,
                }
            ]
        }
        md = format_gap_fillers_markdown(mock_result)
        self.assertIn("#### 🧩 Gap-Filler Candidates (Primary: Quick-Capture & Inferred Fallback):", md)
        self.assertIn("- [ ] **[qc-01] Send invoice draft** (`#task` • `administrative` • 15m • Low) *(Quick-Capture • Due: 2026-10-02)*", md)
        self.assertIn("- [ ] **[inf-01] Clean workbench** (`#task` • `kinetic` • 30m • Low) *(Inferred: Administrative Backlog)*", md)

    def test_08_cli_gap_fillers_subcommand(self):
        """Tests the CLI gap-fillers command and --include-gap-fillers on horizon-tasks."""
        self._write_task("syn-task-qc.md", {
            "title": "Quick Capture CLI Test",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-cli-1",
        })

        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = mdbase_cli_main(["--vault", str(self.vault), "gap-fillers", "--today", "2026-10-01"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertEqual(data["quick_capture_count"], 1)
        self.assertEqual(data["primary_candidates"][0]["title"], "Quick Capture CLI Test")

        # Markdown format via CLI
        buf_md = io.StringIO()
        with contextlib.redirect_stdout(buf_md):
            code_md = mdbase_cli_main(["--vault", str(self.vault), "gap-fillers", "--format", "markdown"])
        self.assertEqual(code_md, 0)
        self.assertIn("[qc-01]", buf_md.getvalue())

        # horizon-tasks with --include-gap-fillers
        buf_hor = io.StringIO()
        with contextlib.redirect_stdout(buf_hor):
            code_hor = mdbase_cli_main(["--vault", str(self.vault), "horizon-tasks", "--include-gap-fillers", "--today", "2026-10-01"])
        self.assertEqual(code_hor, 0)
        data_hor = json.loads(buf_hor.getvalue())
        self.assertIn("gap_fillers", data_hor)
        self.assertEqual(data_hor["gap_fillers"]["quick_capture_count"], 1)

    def test_09_wikilink_and_comma_separated_exclusions(self):
        """Validates that exclusion paths specified as short wikilinks, full wikilinks, or comma-separated strings work."""
        self._write_task("syn-task-exclude-me.md", {
            "title": "Exclude Me Task",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-ex-1",
        })
        self._write_task("syn-task-keep-me.md", {
            "title": "Keep Me Task",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-keep-1",
        })

        # Exclude via short wikilink [[syn-task-exclude-me]]
        res = select_gap_filler_candidates(
            self.vault,
            target_count=2,
            reference_date=date(2026, 10, 1),
            exclude_paths={"[[syn-task-exclude-me]]"},
        )
        titles = [c["title"] for c in res["candidates"]]
        self.assertNotIn("Exclude Me Task", titles)
        self.assertIn("Keep Me Task", titles)

        # Exclude via comma-separated string
        res2 = select_gap_filler_candidates(
            self.vault,
            target_count=2,
            reference_date=date(2026, 10, 1),
            exclude_paths="[[syn-task-exclude-me]],TaskNotes/Tasks/syn-task-keep-me.md",
        )
        titles2 = [c["title"] for c in res2["candidates"]]
        self.assertNotIn("Exclude Me Task", titles2)
        self.assertNotIn("Keep Me Task", titles2)

    def test_10_prevents_scheduled_deliverable_leakage_from_roadmap(self):
        """Deliverables already materialized and scheduled on the calendar must NOT leak as inferred gap-fillers."""
        self._write_roadmap("compiler-pipeline", {
            "project_id": "compiler-pipeline",
            "deliverables": [
                {
                    "id": "deliv-already-scheduled",
                    "title": "Already Scheduled AST Walker",
                    "due": "2026-10-02",
                    "status": "todo",
                }
            ],
        })
        self._write_task("syn-task-scheduled.md", {
            "title": "Already Scheduled AST Walker",
            "status": "todo",
            "scheduled": "2026-10-02T10:00:00-05:00",
            "deliverable_id": "deliv-already-scheduled",
            "project_ref": "[[Projects/compiler-pipeline/Roadmap]]",
        })

        res = select_gap_filler_candidates(
            self.vault,
            target_count=1,
            reference_date=date(2026, 10, 1),
        )
        self.assertEqual(len(res["candidates"]), 1)
        # Should fallback to standard administrative backlog instead of the scheduled deliverable
        self.assertNotEqual(res["candidates"][0].get("deliverable_id"), "deliv-already-scheduled")
        self.assertEqual(res["candidates"][0]["candidate_type"], "inferred")
        self.assertEqual(res["candidates"][0]["inference_source"], "administrative_backlog")

    def test_11_prevents_excluded_anchor_deliverable_leakage_from_roadmap(self):
        """When an anchor task is excluded, its roadmap deliverable must NOT leak as an inferred gap-filler."""
        self._write_roadmap("compiler-pipeline", {
            "project_id": "compiler-pipeline",
            "deliverables": [
                {
                    "id": "deliv-anchor",
                    "title": "Staged Anchor Deliverable",
                    "due": "2026-10-02",
                    "status": "todo",
                }
            ],
        })
        self._write_task("syn-anchor.md", {
            "title": "Staged Anchor Deliverable",
            "status": "todo",
            "scheduled": None,
            "deliverable_id": "deliv-anchor",
            "project_ref": "[[Projects/compiler-pipeline/Roadmap]]",
        })

        res = select_gap_filler_candidates(
            self.vault,
            target_count=1,
            reference_date=date(2026, 10, 1),
            exclude_paths={"TaskNotes/Tasks/syn-anchor.md"},
        )
        self.assertNotEqual(res["candidates"][0].get("deliverable_id"), "deliv-anchor")
        self.assertEqual(res["candidates"][0]["inference_source"], "administrative_backlog")

    def test_12_resilience_to_string_and_malformed_metadata(self):
        """Validates that string urgency tiers or time estimates do not crash candidate selection."""
        self._write_task("syn-task-string-fields.md", {
            "title": "Task with String Metadata",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-str-1",
            "urgency_tier": "high",
            "timeEstimate": "45m",
            "modality": "kinetic",
        })
        res = select_gap_filler_candidates(
            self.vault,
            target_count=1,
            reference_date=date(2026, 10, 1),
        )
        self.assertEqual(res["quick_capture_count"], 1)
        c0 = res["candidates"][0]
        self.assertEqual(c0["urgency_tier"], 3)
        self.assertEqual(c0["timeEstimate"], 45)

    def test_13_preferred_modality_sorting_and_comma_separated_modalities(self):
        """Validates that preferred modalities prioritize matching tasks and accept comma-separated strings."""
        self._write_task("syn-task-admin.md", {
            "title": "Admin Capture",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-admin",
            "modality": "administrative",
            "urgency_tier": 2,
        })
        self._write_task("syn-task-kinetic.md", {
            "title": "Kinetic Capture",
            "status": "todo",
            "scheduled": None,
            "external_item_id": "ext-kinetic",
            "modality": "kinetic",
            "urgency_tier": 2,
        })

        # When kinetic is preferred via string with comma
        res = select_gap_filler_candidates(
            self.vault,
            target_count=2,
            reference_date=date(2026, 10, 1),
            preferred_modalities="kinetic,administrative",
        )
        self.assertEqual(res["candidates"][0]["title"], "Kinetic Capture")
        self.assertEqual(res["candidates"][1]["title"], "Admin Capture")


if __name__ == "__main__":
    unittest.main()
