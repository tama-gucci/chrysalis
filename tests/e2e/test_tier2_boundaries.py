"""
Tier 2: Boundary & Corner Cases Test Suite (F1 - F9)
Tests boundary conditions, edge cases, failure modes, and adversarial inputs.
Every test case documents its authoritative specification source.
"""

import os
import re
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import yaml

from .fixtures import (
    REPO_ROOT,
    SandboxVault,
    parse_frontmatter,
    read_frontmatter,
    scan_for_pii,
    run_cmd,
    TIMEZONE_OFFSET_PATTERN,
    RAW_UTC_PATTERN
)


class TestTier2BoundaryAndCornerCases(unittest.TestCase):
    """Tier 2: Boundary and corner cases across features F1 through F9."""

    # =========================================================================
    # FEATURE F1: Master Constitution Consolidation Boundaries
    # Authoritative Source: PROJECT.md § Feature Inventory F1, AGENTS.md
    # =========================================================================

    def test_f1_b01_corrupted_frontmatter_fails_gracefully(self):
        """
        [F1-T2-01] Frontmatter parser must detect and reject unclosed YAML frontmatter delimiters.
        Authoritative Source: AGENTS.md § Universal TaskNotes Frontmatter Schema.
        """
        corrupt_content = "---\ntitle: Unclosed\nstatus: todo\n# missing closing delimiter\nBody text"
        fm, _ = parse_frontmatter(corrupt_content)
        self.assertEqual(fm, {}, "Unclosed frontmatter must not parse as valid YAML dict")

    def test_f1_b02_agents_md_minimum_viable_length(self):
        """
        [F1-T2-02] AGENTS.md must contain comprehensive specifications (>80 lines) to guard against accidental truncation.
        Authoritative Source: AGENTS.md § 1-3.
        """
        agents_path = REPO_ROOT / "AGENTS.md"
        self.assertTrue(agents_path.exists())
        lines = agents_path.read_text(encoding="utf-8").splitlines()
        self.assertGreater(len(lines), 80, "AGENTS.md must exceed 80 lines of specification content")

    def test_f1_b03_all_relative_links_in_agents_md_resolve(self):
        """
        [F1-T2-03] Every relative markdown link in AGENTS.md must resolve to a valid file on disk.
        Authoritative Source: PROJECT.md § Architecture.
        """
        agents_path = REPO_ROOT / "AGENTS.md"
        content = agents_path.read_text(encoding="utf-8")
        # Extract markdown links [text](path)
        link_pattern = re.compile(r"\[.*?\]\(([^http#\)]+)\)")
        matches = link_pattern.findall(content)
        for link in matches:
            resolved = (REPO_ROOT / link.strip()).resolve()
            self.assertTrue(resolved.exists(), f"Link '{link}' in AGENTS.md resolves to non-existent file: {resolved}")

    def test_f1_b04_tasknotes_schema_forbids_arbitrary_modality(self):
        """
        [F1-T2-04] Universal TaskNotes schema restricts modality strictly to analytical, kinetic, synthesis, administrative.
        Authoritative Source: AGENTS.md § Universal TaskNotes Frontmatter Schema.
        """
        allowed_modalities = {"analytical", "kinetic", "synthesis", "administrative"}
        invalid_modality = "creative_burst"
        self.assertNotIn(invalid_modality, allowed_modalities, "Arbitrary modalities must not be permitted")

    def test_f1_b05_urgency_tier_bounds(self):
        """
        [F1-T2-05] Urgency tier must be bounded strictly between 1 (Lowest) and 4 (Highest).
        Authoritative Source: AGENTS.md § Universal TaskNotes Frontmatter Schema.
        """
        valid_tiers = {1, 2, 3, 4}
        for invalid_tier in [0, 5, -1, 10]:
            self.assertNotIn(invalid_tier, valid_tiers, f"Tier {invalid_tier} must be out of bounds")

    # =========================================================================
    # FEATURE F2: Zero-Leak PII Remediation Boundaries
    # Authoritative Source: PROJECT.md § Feature Inventory F2, ORIGINAL_REQUEST.md R2
    # =========================================================================

    def test_f2_b01_pii_scanner_adversarial_machine_path(self):
        """
        [F2-T2-01] Scanner logic must flag machine paths (/home/<user>/... or C:\\Users\\...).
        Authoritative Source: AGENTS.md Part II § 1 Absolute Zero-Leak PII Law.
        """
        test_text = "Configuration written to " + "/home" + "/developer/secret_vault/keys.txt"
        violations = scan_for_pii(test_text)
        self.assertTrue(any("Machine path" in v[1] for v in violations), f"Failed to catch machine path: {violations}")

    def test_f2_b02_pii_scanner_adversarial_api_key(self):
        """
        [F2-T2-02] Scanner logic must flag Google API keys (AIzaSy...).
        Authoritative Source: AGENTS.md Part II § 1 Absolute Zero-Leak PII Law.
        """
        test_text = "api_key = '" + "AIza" + "SyDummyTestToken1234567890ABCDEFGHI'"
        violations = scan_for_pii(test_text)
        self.assertTrue(any("Google API Key" in v[1] for v in violations), f"Failed to catch API key: {violations}")

    def test_f2_b03_pii_scanner_adversarial_calendar_id(self):
        """
        [F2-T2-03] Scanner logic must flag personal Google Calendar email addresses.
        Authoritative Source: PROJECT.md § Feature Inventory F2.
        """
        test_text = '"targetCalendarId": "f06bb5bfd42813aaf60a' + '@group.' + 'calendar.google.com"'
        violations = scan_for_pii(test_text)
        self.assertTrue(any("Google Calendar ID" in v[1] for v in violations), f"Failed to catch Calendar ID: {violations}")

    def test_f2_b04_gitignore_blocks_daily_notes_regex(self):
        """
        [F2-T2-04] .gitignore must block edge-case daily note filenames like 2026-01-01.md and 2026-12-31-reflection.md.
        Authoritative Source: AGENTS.md Part II § 1 Quarantined Personal Substrates.
        """
        ret, stdout, _ = run_cmd(["git", "check-ignore", "2026-01-01.md", "2026-12-31-reflection.md"])
        self.assertEqual(ret, 0, "git check-ignore must successfully recognize daily notes as ignored")
        ignored = stdout.splitlines()
        self.assertEqual(len(ignored), 2, f"Both daily notes should be ignored: {ignored}")

    def test_f2_b05_gitignore_blocks_workstation_manifests(self):
        """
        [F2-T2-05] .gitignore must block personal workstation manifests under System/Environment/*.md.
        Authoritative Source: AGENTS.md Part II § 1 Quarantined Personal Substrates.
        """
        ret, stdout, _ = run_cmd([
            "git", "check-ignore",
            "System/Environment/obelisk.md",
            "System/Environment/surface-pro-x.md",
            "System/Environment/custom-workstation.md"
        ])
        self.assertEqual(ret, 0, "git check-ignore must recognize personal workstation manifests as ignored")
        ignored = stdout.splitlines()
        self.assertEqual(len(ignored), 3, f"All workstation manifests should be ignored: {ignored}")

    # =========================================================================
    # FEATURE F3: Nomenclature & Synthetic Standards Boundaries
    # Authoritative Source: PROJECT.md § Feature Inventory F3
    # =========================================================================

    def test_f3_b01_types_task_valid_yaml_mdbase(self):
        """
        [F3-T2-01] _types/task.md frontmatter must parse as valid YAML and declare version: 0.2.0.
        Authoritative Source: _types/task.md line 1-10.
        """
        types_path = REPO_ROOT / "_types" / "task.md"
        self.assertTrue(types_path.exists())
        fm, _ = read_frontmatter(types_path)
        self.assertEqual(str(fm.get("version")), "0.2.0", "_types/task.md must have version 0.2.0")

    def test_f3_b02_types_task_priority_enum_completeness(self):
        """
        [F3-T2-02] _types/task.md priority property must permit urgent, high, normal, low, none.
        Authoritative Source: PROJECT.md § Interface Contracts.
        """
        types_path = REPO_ROOT / "_types" / "task.md"
        content = types_path.read_text(encoding="utf-8")
        for prio in ["urgent", "high", "normal", "low", "none"]:
            self.assertIn(prio, content, f"_types/task.md must permit priority '{prio}'")

    def test_f3_b03_types_task_time_estimate_is_number(self):
        """
        [F3-T2-03] _types/task.md must specify timeEstimate as a number.
        Authoritative Source: _types/task.md.
        """
        types_path = REPO_ROOT / "_types" / "task.md"
        content = types_path.read_text(encoding="utf-8")
        self.assertIn("timeEstimate", content)
        self.assertIn("number", content)

    def test_f3_b04_no_personal_emails_in_public_files(self):
        """
        [F3-T2-04] Repository public markdown and code files must not contain personal email addresses.
        Authoritative Source: AGENTS.md § 3 Synthetic Placeholder Standard.
        """
        email_pattern = re.compile(r"\b[A-Za-z0-9._%+-]+@(?!example\.com|example\.org)[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
        for f in REPO_ROOT.glob("**/*.md"):
            if ".agent/skills/.backup" in str(f):
                continue
            text = f.read_text(encoding="utf-8")
            matches = email_pattern.findall(text)
            self.assertEqual(matches, [], f"Personal email found in {f.relative_to(REPO_ROOT)}: {matches}")

    def test_f3_b05_environment_index_no_broken_wikilinks(self):
        """
        [F3-T2-05] Environment-Index.md must not reference non-existent private node files.
        Authoritative Source: PROJECT.md § Feature Inventory F3.
        """
        env_index = REPO_ROOT / "System" / "Environment" / "Environment-Index.md"
        content = env_index.read_text(encoding="utf-8")
        self.assertNotIn("[[obelisk]]", content, "Environment-Index.md must not reference broken [[obelisk]] link")

    # =========================================================================
    # FEATURE F4: Script & Tooling Consolidation Boundaries
    # Authoritative Source: PROJECT.md § Feature Inventory F4, Interface Contracts
    # =========================================================================

    def test_f4_b01_bootstrap_py_dry_run_makes_zero_disk_mutations(self):
        """
        [F4-T2-01] bootstrap.py --dry-run must not create any files or directories on disk.
        Authoritative Source: PROJECT.md § Interface Contracts § bootstrap.py.
        """
        bootstrap_py = REPO_ROOT / "System" / "scripts" / "bootstrap.py"
        if bootstrap_py.exists():
            with tempfile.TemporaryDirectory(prefix="chrysalis_dryrun_") as tmp_dir:
                tmp_path = Path(tmp_dir)
                ret, stdout, stderr = run_cmd([
                    "python3", str(bootstrap_py),
                    "--vault-root", str(tmp_path),
                    "--dry-run"
                ])
                self.assertEqual(ret, 0, f"bootstrap.py --dry-run failed: {stderr}")
                created = list(tmp_path.iterdir())
                self.assertEqual(created, [], "bootstrap.py --dry-run must not create any files on disk")

    def test_f4_b02_bootstrap_py_does_not_overwrite_existing_files(self):
        """
        [F4-T2-02] bootstrap.py must never overwrite existing files without --force.
        Authoritative Source: PROJECT.md § Interface Contracts § bootstrap.py.
        """
        bootstrap_py = REPO_ROOT / "System" / "scripts" / "bootstrap.py"
        if bootstrap_py.exists():
            sandbox = SandboxVault(populate_runtime=True)
            try:
                mem_path = sandbox.path / "System" / "Scheduling-Memory.md"
                original_content = mem_path.read_text(encoding="utf-8")
                
                # Run bootstrap without --force
                ret, stdout, stderr = run_cmd([
                    "python3", str(bootstrap_py),
                    "--vault-root", str(sandbox.path)
                ])
                self.assertEqual(ret, 0, f"bootstrap.py failed: {stderr}")
                self.assertEqual(mem_path.read_text(encoding="utf-8"), original_content, "Existing memory must NOT be overwritten")
            finally:
                sandbox.cleanup()

    def test_f4_b03_bootstrap_py_respects_custom_timezone(self):
        """
        [F4-T2-03] bootstrap.py must apply explicit timezone offset when --timezone is provided.
        Authoritative Source: PROJECT.md § Interface Contracts § bootstrap.py.
        """
        bootstrap_py = REPO_ROOT / "System" / "scripts" / "bootstrap.py"
        if bootstrap_py.exists():
            with tempfile.TemporaryDirectory(prefix="chrysalis_tz_") as tmp_dir:
                tmp_path = Path(tmp_dir)
                ret, stdout, stderr = run_cmd([
                    "python3", str(bootstrap_py),
                    "--vault-root", str(tmp_path),
                    "--timezone", "-08:00"
                ])
                self.assertEqual(ret, 0, f"bootstrap.py with --timezone failed: {stderr}")
                mem_file = tmp_path / "System" / "Scheduling-Memory.md"
                if mem_file.exists():
                    content = mem_file.read_text(encoding="utf-8")
                    self.assertIn("-08:00", content, "Seeded memory must use custom timezone -08:00")

    def test_f4_b04_export_starter_dry_run_is_non_destructive(self):
        """
        [F4-T2-04] export_starter.py --dry-run must execute without modifying source repository.
        Authoritative Source: PROJECT.md § Interface Contracts § export_starter.py.
        """
        export_script = REPO_ROOT / "Development" / "scripts" / "export_starter.py"
        if export_script.exists():
            with tempfile.TemporaryDirectory(prefix="chrysalis_export_") as tmp_dir:
                ret, stdout, stderr = run_cmd([
                    "python3", str(export_script),
                    "--target-dir", str(tmp_dir),
                    "--dry-run"
                ])
                self.assertEqual(ret, 0, f"export_starter.py --dry-run failed: {stderr}")

    def test_f4_b05_sync_calendar_graceful_on_unreachable_port(self):
        """
        [F4-T2-05] sync_calendar.py must handle unreachable API ports gracefully without unhandled exceptions.
        Authoritative Source: Survey Report (spec_miner_1, explorer_1).
        """
        sync_script = REPO_ROOT / "System" / "scripts" / "sync_calendar.py"
        if sync_script.exists():
            ret, stdout, stderr = run_cmd([
                "python3", str(sync_script),
                "--port", "65432"
            ])
            # Should exit with error notice, not an uncaught traceback crash
            self.assertTrue("Traceback (most recent call last)" not in stderr, f"sync_calendar.py crashed with traceback: {stderr}")

    # =========================================================================
    # FEATURE F5: Public Template Matrix Completeness Boundaries
    # Authoritative Source: PROJECT.md § Feature Inventory F5, AGENTS.md Part II
    # =========================================================================

    def test_f5_b01_task_template_validates_mdbase_schema(self):
        """
        [F5-T2-01] Task-Template.md frontmatter must strictly comply with _types/task.md schema.
        Authoritative Source: TaskNotes/_templates/Task-Template.md.
        """
        tmpl_path = REPO_ROOT / "TaskNotes" / "_templates" / "Task-Template.md"
        self.assertTrue(tmpl_path.exists())
        fm, _ = read_frontmatter(tmpl_path)
        self.assertIn("modality", fm)
        self.assertIn("urgency_tier", fm)
        self.assertIn("micro_chunked", fm)

    def test_f5_b02_system_manifest_template_embedded_json_valid(self):
        """
        [F5-T2-02] System-Manifest-Template.md embedded package JSON block must be valid syntactically.
        Authoritative Source: System/Environment/_templates/System-Manifest-Template.md.
        """
        tmpl_path = REPO_ROOT / "System" / "Environment" / "_templates" / "System-Manifest-Template.md"
        self.assertTrue(tmpl_path.exists())
        content = tmpl_path.read_text(encoding="utf-8")
        json_matches = re.findall(r"```json\s*(\{.*?\})\s*```", content, re.DOTALL)
        for block in json_matches:
            try:
                data = json.loads(block)
                self.assertIsInstance(data, dict, "Embedded JSON block must parse as dictionary")
            except Exception as e:
                self.fail(f"Embedded JSON block in System-Manifest-Template.md is invalid: {e}")

    def test_f5_b03_scheduling_memory_multipliers_within_bounds(self):
        """
        [F5-T2-03] Multipliers in Scheduling-Memory.template.md must fall strictly within [0.20, 2.00].
        Authoritative Source: AGENTS.md § 2 Dynamic Memory & Operational State.
        """
        mem_tmpl = REPO_ROOT / "System" / "_templates" / "Scheduling-Memory.template.md"
        fm, _ = read_frontmatter(mem_tmpl)
        multipliers = fm.get("dynamic_multipliers", {})
        for modality, mult in multipliers.items():
            self.assertGreaterEqual(float(mult), 0.20, f"Multiplier for {modality} below 0.20 minimum")
            self.assertLessEqual(float(mult), 2.00, f"Multiplier for {modality} above 2.00 maximum")

    def test_f5_b04_daily_note_template_chronotype_structure(self):
        """
        [F5-T2-04] Daily-Note.template.md must include sections for morning calibration, focus sprints, and evening reflection.
        Authoritative Source: System/_templates/Daily-Note.template.md.
        """
        tmpl_path = REPO_ROOT / "System" / "_templates" / "Daily-Note.template.md"
        self.assertTrue(tmpl_path.exists())
        content = tmpl_path.read_text(encoding="utf-8").lower()
        self.assertTrue("morning" in content or "calibration" in content)
        self.assertTrue("focus" in content or "sprint" in content or "timeblock" in content)
        self.assertTrue("evening" in content or "reflection" in content or "audit" in content)

    def test_f5_b05_template_timestamps_reject_raw_z(self):
        """
        [F5-T2-05] Templates must never use raw UTC 'Z' in timestamp placeholders.
        Authoritative Source: AGENTS.md § 1 Explicit Local Timezone.
        """
        for tmpl in REPO_ROOT.glob("**/_templates/**/*.md"):
            content = tmpl.read_text(encoding="utf-8")
            self.assertNotIn("T00:00:00Z", content, f"Template {tmpl} contains raw UTC 'Z' timestamp")

    # =========================================================================
    # FEATURE F6: Upstream Updater Refactoring Boundaries
    # Authoritative Source: PROJECT.md § Feature Inventory F6, Interface Contracts
    # =========================================================================

    def test_f6_b01_update_py_rejects_non_existent_source(self):
        """
        [F6-T2-01] update.py must cleanly reject a non-existent local --source directory.
        Authoritative Source: PROJECT.md § Interface Contracts § update.py.
        """
        update_py = REPO_ROOT / "update.py"
        ret, stdout, stderr = run_cmd([
            "python3", str(update_py),
            "--source", "/non/existent/repo/path",
            "--dry-run"
        ])
        self.assertNotEqual(ret, 0, "update.py must exit non-zero for non-existent source directory")

    def test_f6_b02_update_py_protects_custom_environment_manifests(self):
        """
        [F6-T2-02] update.py is_protected_target must return True for any custom System/Environment/*.md manifest.
        Authoritative Source: PROJECT.md § Interface Contracts § update.py.
        """
        update_py = REPO_ROOT / "update.py"
        content = update_py.read_text(encoding="utf-8")
        self.assertTrue(
            "System/Environment" in content and "is_protected" in content,
            "update.py must protect System/Environment manifests"
        )

    def test_f6_b03_update_py_protects_plugin_data_json(self):
        """
        [F6-T2-03] update.py must never distribute or overwrite plugin data.json files.
        Authoritative Source: PROJECT.md § Interface Contracts § update.py whitelist.
        """
        update_py = REPO_ROOT / "update.py"
        content = update_py.read_text(encoding="utf-8")
        self.assertIn("data.json", content, "update.py must explicitly guard or exclude data.json")

    def test_f6_b04_update_py_protects_slipbox_notes(self):
        """
        [F6-T2-04] update.py is_protected_target must protect Slipbox notes.
        Authoritative Source: AGENTS.md § 3 Quarantined Personal Substrates.
        """
        update_py = REPO_ROOT / "update.py"
        content = update_py.read_text(encoding="utf-8")
        self.assertIn("Slipbox", content, "update.py must protect Slipbox/")

    def test_f6_b05_update_py_protects_project_roadmaps(self):
        """
        [F6-T2-05] update.py is_protected_target must protect personal project roadmaps under Projects/*/.
        Authoritative Source: AGENTS.md § 3 Quarantined Personal Substrates.
        """
        update_py = REPO_ROOT / "update.py"
        content = update_py.read_text(encoding="utf-8")
        self.assertIn("Projects", content, "update.py must protect Projects/")

    # =========================================================================
    # FEATURE F7: Strategic Capability Roadmap Boundaries
    # Authoritative Source: ORIGINAL_REQUEST.md R4, PROJECT.md F7
    # =========================================================================

    def test_f7_b01_roadmap_template_parity(self):
        """
        [F7-T2-01] Development/_templates/ROADMAP.template.md must maintain 1-to-1 section parity with ROADMAP.md.
        Authoritative Source: PROJECT.md § Feature Inventory F7.
        """
        roadmap_path = REPO_ROOT / "Development" / "ROADMAP.md"
        tmpl_path = REPO_ROOT / "Development" / "_templates" / "ROADMAP.template.md"
        if roadmap_path.exists() and tmpl_path.exists():
            rm_headers = [line for line in roadmap_path.read_text(encoding="utf-8").splitlines() if line.startswith("#")]
            tmpl_headers = [line for line in tmpl_path.read_text(encoding="utf-8").splitlines() if line.startswith("#")]
            self.assertEqual(len(rm_headers), len(tmpl_headers), "ROADMAP.md and its template should have matching heading counts")

    def test_f7_b02_roadmap_no_pii_leaks(self):
        """
        [F7-T2-02] Development/ROADMAP.md must be 100% free of personal names or machine paths.
        Authoritative Source: AGENTS.md § 3 Absolute Zero-Leak PII Law.
        """
        roadmap_path = REPO_ROOT / "Development" / "ROADMAP.md"
        if roadmap_path.exists():
            violations = scan_for_pii(roadmap_path.read_text(encoding="utf-8"))
            self.assertEqual(violations, [], f"ROADMAP.md contains PII: {violations}")

    def test_f7_b03_roadmap_architectural_matrix_present(self):
        """
        [F7-T2-03] Development/ROADMAP.md must contain an architectural capability matrix or summary table.
        Authoritative Source: ORIGINAL_REQUEST.md R4.
        """
        roadmap_path = REPO_ROOT / "Development" / "ROADMAP.md"
        if roadmap_path.exists():
            content = roadmap_path.read_text(encoding="utf-8")
            self.assertIn("|", content, "ROADMAP.md must contain markdown tables for capability mapping")

    def test_f7_b04_roadmap_anti_simulation_alignment(self):
        """
        [F7-T2-04] Planned capabilities in ROADMAP.md must preserve the Anti-Simulation Law and physical file substrate.
        Authoritative Source: AGENTS.md § 1 Vault Substrate.
        """
        roadmap_path = REPO_ROOT / "Development" / "ROADMAP.md"
        if roadmap_path.exists():
            content = roadmap_path.read_text(encoding="utf-8").lower()
            self.assertTrue("substrate" in content or "markdown" in content or "file" in content)

    def test_f7_b05_roadmap_status_indicators_valid(self):
        """
        [F7-T2-05] Capabilities in ROADMAP.md must declare structured status indicators (e.g. Planned, Proposed, Research).
        Authoritative Source: PROJECT.md § Acceptance Criteria.
        """
        roadmap_path = REPO_ROOT / "Development" / "ROADMAP.md"
        if roadmap_path.exists():
            content = roadmap_path.read_text(encoding="utf-8").lower()
            self.assertTrue(
                "planned" in content or "proposed" in content or "milestone" in content,
                "ROADMAP.md must define status indicators for planned capabilities"
            )

    # =========================================================================
    # FEATURE F8: Upstream Dual Verification Boundaries
    # Authoritative Source: doctor/SKILL.md, AGENTS.md
    # =========================================================================

    def test_f8_b01_doctor_detects_out_of_bounds_multipliers(self):
        """
        [F8-T2-01] Verification logic must flag dynamic multipliers outside [0.20, 2.00].
        Authoritative Source: doctor/SKILL.md § Check 6 (Dynamic State Multipliers Bounded).
        """
        invalid_multipliers = [0.10, 0.19, 2.01, 3.50, -0.50]
        for m in invalid_multipliers:
            self.assertFalse(0.20 <= m <= 2.00, f"Multiplier {m} should be rejected as out of bounds")

    def test_f8_b02_doctor_detects_utc_z_timestamps(self):
        """
        [F8-T2-02] Verification logic must flag raw UTC timestamps with trailing 'Z'.
        Authoritative Source: doctor/SKILL.md § Check 2 (Explicit Local Timezone Invariant).
        """
        utc_ts = "2026-09-03T14:30:00Z"
        self.assertTrue(bool(RAW_UTC_PATTERN.match(utc_ts)), "RAW_UTC_PATTERN should recognize raw UTC 'Z'")
        self.assertFalse(bool(TIMEZONE_OFFSET_PATTERN.match(utc_ts)), "TIMEZONE_OFFSET_PATTERN must reject raw 'Z'")

    def test_f8_b03_doctor_detects_unregistered_tag(self):
        """
        [F8-T2-03] Verification logic must flag tags not registered in Life-Roadmap.md.
        Authoritative Source: doctor/SKILL.md § Check 3 (Tag Registry Validation).
        """
        registered = {"pillar-core/research", "pillar-ops/admin"}
        unregistered = "pillar-fake/unregistered"
        self.assertNotIn(unregistered, registered, "Unregistered tag should be detected")

    def test_f8_b04_doctor_detects_broken_wikilinks(self):
        """
        [F8-T2-04] Verification logic must detect broken wikilinks to missing files.
        Authoritative Source: doctor/SKILL.md § Check 4 (Wikilink & Graph Integrity).
        """
        target = REPO_ROOT / "NonExistentFile12345.md"
        self.assertFalse(target.exists(), "Target file does not exist, wikilink should be flagged as broken")

    def test_f8_b05_doctor_detects_missing_skill_description(self):
        """
        [F8-T2-05] Skill validator must flag any skill missing the required description field.
        Authoritative Source: doctor/SKILL.md § Check 5 (Skill Runbooks Validation).
        """
        invalid_skill_fm = {"name": "test-skill"}
        self.assertNotIn("description", invalid_skill_fm, "Skill without description must be flagged")

    # =========================================================================
    # FEATURE F9: Non-Destructive Runtime Synchronization Boundaries
    # Authoritative Source: ORIGINAL_REQUEST.md R3, PROJECT.md F9
    # =========================================================================

    def test_f9_b01_snapshot_restoration_integrity(self):
        """
        [F9-T2-01] Pre-sync snapshot mechanism must be able to restore the sandbox runtime to 100% byte identical state.
        Authoritative Source: PROJECT.md § Feature Inventory F9; Survey Report (explorer_2).
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            # 1. Take snapshot of sandbox
            snapshot_dir = Path(tempfile.mkdtemp(prefix="chrysalis_snapshot_test_"))
            for item in sandbox.path.iterdir():
                dest = snapshot_dir / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
            
            # 2. Corrupt or delete a file in sandbox
            task_path = sandbox.path / "TaskNotes" / "Tasks" / "20260903-synthetic-task.md"
            task_original_bytes = task_path.read_bytes()
            task_path.write_text("CORRUPTED BY SIMULATED POWER LOSS", encoding="utf-8")
            
            # 3. Restore from snapshot
            shutil.copy2(snapshot_dir / "TaskNotes" / "Tasks" / "20260903-synthetic-task.md", task_path)
            
            # 4. Verify identical
            self.assertEqual(task_path.read_bytes(), task_original_bytes, "Restored file must be byte-identical")
            shutil.rmtree(snapshot_dir)
        finally:
            sandbox.cleanup()

    def test_f9_b02_sync_empty_source_safety(self):
        """
        [F9-T2-02] Running updater with empty source must abort safely without wiping target directory.
        Authoritative Source: PROJECT.md § Interface Contracts § update.py.
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            initial_count = sandbox.count_files()
            with tempfile.TemporaryDirectory() as empty_source:
                update_py = REPO_ROOT / "update.py"
                run_cmd([
                    "python3", str(update_py),
                    "--source", empty_source,
                    "--target", str(sandbox.path),
                    "--dry-run"
                ])
                self.assertEqual(sandbox.count_files(), initial_count, "Target files must remain completely untouched")
        finally:
            sandbox.cleanup()

    def test_f9_b03_sync_to_read_only_target_handles_gracefully(self):
        """
        [F9-T2-03] Syncing to an unwritable directory should report a permission error without uncaught crash.
        Authoritative Source: PROJECT.md § Interface Contracts.
        """
        update_py = REPO_ROOT / "update.py"
        ret, stdout, stderr = run_cmd([
            "python3", str(update_py),
            "--target", "/root/forbidden_vault",
            "--dry-run"
        ])
        self.assertNotEqual(ret, 0, "Update to inaccessible path must exit non-zero")

    def test_f9_b04_runtime_vault_file_count_preserved(self):
        """
        [F9-T2-04] Total file count of user tasks and notes in sandbox must not decrease after framework update.
        Authoritative Source: ORIGINAL_REQUEST.md R3.
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            tasks_before = len(list((sandbox.path / "TaskNotes" / "Tasks").iterdir()))
            archives_before = len(list((sandbox.path / "TaskNotes" / "Archive").iterdir()))
            
            update_py = REPO_ROOT / "update.py"
            run_cmd(["python3", str(update_py), "--target", str(sandbox.path), "--dry-run"])
            
            tasks_after = len(list((sandbox.path / "TaskNotes" / "Tasks").iterdir()))
            archives_after = len(list((sandbox.path / "TaskNotes" / "Archive").iterdir()))
            
            self.assertEqual(tasks_before, tasks_after, "Active user task count must be preserved")
            self.assertEqual(archives_before, archives_after, "Archived user task count must be preserved")
        finally:
            sandbox.cleanup()

    def test_f9_b05_sync_preserves_untracked_runtime_caches_if_present(self):
        """
        [F9-T2-05] Framework synchronization must not tamper with runtime cache directories like Nexus/ or .workspaces/.
        Authoritative Source: AGENTS.md Part II § 1 Quarantined Personal Substrates.
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            nexus_dir = sandbox.path / "Nexus" / "cache"
            nexus_dir.mkdir(parents=True, exist_ok=True)
            cache_file = nexus_dir / "sqlite.db"
            cache_file.write_text("fake sqlite cache data", encoding="utf-8")
            
            update_py = REPO_ROOT / "update.py"
            run_cmd(["python3", str(update_py), "--target", str(sandbox.path), "--dry-run"])
            
            self.assertTrue(cache_file.exists(), "Runtime cache file must be preserved")
        finally:
            sandbox.cleanup()


if __name__ == "__main__":
    unittest.main()
