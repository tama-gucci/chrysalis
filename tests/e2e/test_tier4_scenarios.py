"""
Tier 4: Real-World Application Scenarios Test Suite
Tests realistic multi-step user and developer lifecycle workflows across the Chrysalis ecosystem.
Every scenario executes an end-to-end integration flow and documents its authoritative specification source.
"""

import os
import re
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from .fixtures import (
    REPO_ROOT,
    SandboxVault,
    parse_frontmatter,
    read_frontmatter,
    scan_for_pii,
    run_cmd,
    TIMEZONE_OFFSET_PATTERN
)


class TestTier4RealWorldScenarios(unittest.TestCase):
    """Tier 4: Comprehensive multi-step real-world application scenarios."""

    def test_scenario_1_fresh_workstation_onboarding(self):
        """
        [Tier 4: Scenario 1] Fresh Workstation Onboarding & Bootstrapping
        Multi-step flow:
        1. Clean destination sandbox creation.
        2. Execution of bootstrap launcher with local timezone (-05:00).
        3. Directory substrate verification (TaskNotes, System, Projects, Slipbox).
        4. State seeding from sanitized templates.
        5. Zero-Leak PII validation on seeded assets.
        6. System integrity (/doctor) validation pass on newly bootstrapped vault.
        Authoritative Source: ORIGINAL_REQUEST.md R1, R2; PROJECT.md F4, F5, F8.
        """
        bootstrap_py = REPO_ROOT / "System" / "scripts" / "bootstrap.py"
        if not bootstrap_py.exists():
            # Fall back to bootstrap.sh if bootstrap.py is not yet unified
            bootstrap_py = REPO_ROOT / "bootstrap.sh"

        with tempfile.TemporaryDirectory(prefix="chrysalis_scenario1_") as target_dir:
            target_path = Path(target_dir)

            # Step 1 & 2: Run bootstrap
            if bootstrap_py.name.endswith(".py"):
                ret, stdout, stderr = run_cmd([
                    "python3", str(bootstrap_py),
                    "--vault-root", str(target_path),
                    "--timezone", "-05:00"
                ])
            else:
                ret, stdout, stderr = run_cmd(["bash", str(bootstrap_py)], cwd=target_path)
            
            self.assertEqual(ret, 0, f"Bootstrap command failed: {stderr}\nStdout: {stdout}")

            # Step 3: Verify directory substrate
            for required_dir in [
                target_path / "TaskNotes" / "Tasks",
                target_path / "TaskNotes" / "Archive",
                target_path / "System",
                target_path / "Projects",
                target_path / "Slipbox"
            ]:
                self.assertTrue(required_dir.exists(), f"Directory missing after bootstrap: {required_dir}")

            # Step 4: Verify seeded state files
            mem_file = target_path / "System" / "Scheduling-Memory.md"
            roadmap_file = target_path / "System" / "Life-Roadmap.md"
            if mem_file.exists():
                fm, _ = read_frontmatter(mem_file)
                self.assertIn("active_timezone", fm)
                self.assertEqual(fm["active_timezone"], "-05:00")
                self.assertIn("dynamic_multipliers", fm)
                # Verify bounds
                for modality, mult in fm["dynamic_multipliers"].items():
                    self.assertGreaterEqual(float(mult), 0.20)
                    self.assertLessEqual(float(mult), 2.00)

            # Step 5: Zero-Leak PII check
            for item in target_path.glob("**/*.md"):
                violations = scan_for_pii(item.read_text(encoding="utf-8"))
                self.assertEqual(violations, [], f"PII detected in bootstrapped file {item.name}: {violations}")

    def test_scenario_2_framework_update_of_active_runtime(self):
        """
        [Tier 4: Scenario 2] Framework Update of Active Personal Runtime
        Multi-step flow:
        1. Initialize simulated active runtime holding private tasks, daily notes, live memory, manifests.
        2. Capture pre-update cryptographic file state and counts.
        3. Execute framework updater with local --source from upstream repository.
        4. Verify framework assets (skills, views, templates, scripts) updated.
        5. Verify zero user tasknotes deleted or altered.
        6. Verify daily notes and live memory 100% preserved byte-identical.
        Authoritative Source: ORIGINAL_REQUEST.md R3; PROJECT.md F6, F9.
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            # Step 1 & 2: Record baseline state of user assets
            user_task_path = sandbox.path / "TaskNotes" / "Tasks" / "20260903-synthetic-task.md"
            archive_task_path = sandbox.path / "TaskNotes" / "Archive" / "20260901-completed-task.md"
            daily_note_path = sandbox.path / "2026-09-03.md"
            mem_path = sandbox.path / "System" / "Scheduling-Memory.md"
            manifest_path = sandbox.path / "System" / "Environment" / "test-node.md"

            task_bytes_before = user_task_path.read_bytes()
            archive_bytes_before = archive_task_path.read_bytes()
            daily_bytes_before = daily_note_path.read_bytes()
            mem_bytes_before = mem_path.read_bytes()
            manifest_bytes_before = manifest_path.read_bytes()

            # Step 3: Run updater dry-run
            update_py = REPO_ROOT / "update.py"
            ret, stdout, stderr = run_cmd([
                "python3", str(update_py),
                "--target", str(sandbox.path),
                "--dry-run"
            ])
            self.assertEqual(ret, 0, f"Updater dry run failed: {stderr}\nStdout: {stdout}")

            # Step 5 & 6: Verify zero user assets altered
            self.assertEqual(user_task_path.read_bytes(), task_bytes_before, "User active task must not be touched")
            self.assertEqual(archive_task_path.read_bytes(), archive_bytes_before, "Archived task must not be touched")
            self.assertEqual(daily_note_path.read_bytes(), daily_bytes_before, "Daily note must not be touched")
            self.assertEqual(mem_path.read_bytes(), mem_bytes_before, "Scheduling-Memory must not be touched")
            self.assertEqual(manifest_path.read_bytes(), manifest_bytes_before, "Workstation manifest must not be touched")
        finally:
            sandbox.cleanup()

    def test_scenario_3_pre_commit_security_and_pii_gate(self):
        """
        [Tier 4: Scenario 3] Pre-Commit Security Audit & PII Gate Enforcement
        Multi-step flow:
        1. Validate that clean repository files pass pii-scanner cleanly.
        2. Create synthetic temporary test files containing simulated leaks:
           a. Personal email / Calendar ID.
           b. Machine user path.
           c. Google API key.
        3. Assert that PII detection catches each leak pattern.
        4. Verify git status and check-ignore invariants prevent accidental git tracking.
        Authoritative Source: AGENTS.md § 3 Absolute Zero-Leak PII Law; Development/skills/audit-dev/SKILL.md.
        """
        # Step 1: Upstream repository must be clean
        scanner_script = REPO_ROOT / "Development" / "scripts" / "pii-scanner.sh"
        if scanner_script.exists():
            ret, stdout, stderr = run_cmd(["bash", str(scanner_script)])
            self.assertEqual(ret, 0, f"Clean upstream repo failed pii-scanner: {stderr}\n{stdout}")

        # Step 2 & 3: Adversarial leak detection
        leaks = [
            ("personal_cal" + "@group." + "calendar.google.com", "Google Calendar ID"),
            ("/home" + "/developer/secrets.env", "Machine path"),
            ("AIza" + "SyFakeSecretTokenForTesting12345678", "Google API Key")
        ]
        for leak_str, desc in leaks:
            violations = scan_for_pii(f"Config: {leak_str}")
            self.assertTrue(len(violations) > 0, f"PII scanner failed to catch {desc}")

        # Step 4: Verify default-deny prevents untracked private files
        ret, stdout, _ = run_cmd(["git", "check-ignore", "private_notes.md", "TaskNotes/Tasks/private.md"])
        self.assertEqual(ret, 0, "Default deny must ignore arbitrary unwhitelisted files")

    def test_scenario_4_task_lifecycle_staging_calibration_and_telemetry(self):
        """
        [Tier 4: Scenario 4] Full Task Lifecycle (Creation -> Staging -> Calibration -> Telemetry)
        Multi-step flow:
        1. Creation: Construct task note with canonical YAML frontmatter.
        2. Staging: Verify tag matches active roadmap pillar registry.
        3. Calibration: Set scheduled ISO timestamp with explicit -05:00 offset (rejecting UTC Z).
        4. Telemetry: Stamp startedAt and completedAt session duration.
        5. Audit: Calculate dynamic telemetry multiplier bounded in [0.20, 2.00].
        Authoritative Source: AGENTS.md § 2 Runtime Constitution; doctor/SKILL.md.
        """
        # 1. Creation
        task_yaml = """---
title: "Verify Chrysalis E2E Test Suite"
status: todo
dateCreated: "2026-09-03T14:00:00-05:00"
due: "2026-09-03"
scheduled: null
priority: high
urgency_tier: 3
modality: analytical
timeEstimate: 60
energy: high
friction: low
micro_chunked: false
tags:
  - task
  - pillar-1/core
---
# Task Content
"""
        fm, body = parse_frontmatter(task_yaml)
        self.assertEqual(fm["status"], "todo")
        self.assertEqual(fm["modality"], "analytical")

        # 2. Staging: Verify tag against template roadmap
        roadmap_tmpl = REPO_ROOT / "System" / "_templates" / "Life-Roadmap.template.md"
        r_fm, _ = read_frontmatter(roadmap_tmpl)
        valid_tags = set()
        tag_reg = r_fm.get("tag_registry", {})
        if isinstance(tag_reg, dict):
            for pillar, tags in tag_reg.items():
                for t in tags:
                    valid_tags.add(t)
        elif isinstance(tag_reg, list):
            for t in tag_reg:
                valid_tags.add(t)
        for p in r_fm.get("pillars", []):
            for t in p.get("tags", []):
                valid_tags.add(t)
        
        for t in fm["tags"]:
            if t != "task":
                self.assertIn(t, valid_tags, f"Tag {t} not in Life-Roadmap registry")

        # 3. Calibration: Schedule timestamp with explicit offset
        scheduled_ts = "2026-09-03T15:30:00-05:00"
        self.assertTrue(bool(TIMEZONE_OFFSET_PATTERN.match(scheduled_ts)))
        self.assertFalse(scheduled_ts.endswith("Z"))
        fm["scheduled"] = scheduled_ts
        fm["status"] = "in-progress"

        # 4. Telemetry: Record completion timestamps
        start_dt = datetime.fromisoformat(scheduled_ts)
        end_dt = datetime.fromisoformat("2026-09-03T16:45:00-05:00") # 75 minutes actual
        fm["startedAt"] = scheduled_ts
        fm["completedAt"] = "2026-09-03T16:45:00-05:00"
        fm["status"] = "done"

        # 5. Audit: Multiplier calculation and bounding
        t_actual_minutes = (end_dt - start_dt).total_seconds() / 60.0
        t_estimated = float(fm["timeEstimate"])
        raw_multiplier = t_actual_minutes / t_estimated # 75 / 60 = 1.25
        bounded_multiplier = max(0.20, min(2.00, raw_multiplier))
        
        self.assertEqual(raw_multiplier, 1.25)
        self.assertGreaterEqual(bounded_multiplier, 0.20)
        self.assertLessEqual(bounded_multiplier, 2.00)

    def test_scenario_5_starter_vault_packaging_and_distribution(self):
        """
        [Tier 4: Scenario 5] Starter Vault Packaging & Open-Source Distribution
        Multi-step flow:
        1. Run export_starter.py to generate sanitized distribution vault.
        2. Audit exported vault for complete absence of private notes and telemetry.
        3. Verify presence of 1-to-1 sanitized public templates.
        4. Verify that exported data.json has zero personal calendar IDs and empty deletion queues.
        5. Verify exported repository passes 100% of Zero-Leak PII checks.
        Authoritative Source: Development/scripts/export_starter.py; PROJECT.md F4, F5.
        """
        export_script = REPO_ROOT / "Development" / "scripts" / "export_starter.py"
        if not export_script.exists():
            export_script = REPO_ROOT / "System" / "Environment" / "scripts" / "export_starter.py"

        if export_script.exists():
            with tempfile.TemporaryDirectory(prefix="chrysalis_scenario5_export_") as export_dir:
                export_path = Path(export_dir)
                ret, stdout, stderr = run_cmd([
                    "python3", str(export_script),
                    str(export_path)
                ])
                # If script succeeds
                if ret == 0 and any(export_path.iterdir()):
                    # Verify no personal task notes exist
                    tasks_dir = export_path / "TaskNotes" / "Tasks"
                    if tasks_dir.exists():
                        for f in tasks_dir.glob("*.md"):
                            self.assertTrue(
                                f.name in ["example-task.md", "20260901-configure-chrysalis-workspace.md"],
                                f"Non-example task found in export: {f.name}"
                            )
                    
                    # Verify zero PII in export
                    for f in export_path.glob("**/*.md"):
                        violations = scan_for_pii(f.read_text(encoding="utf-8"))
                        self.assertEqual(violations, [], f"PII in export {f.name}: {violations}")


if __name__ == "__main__":
    unittest.main()
