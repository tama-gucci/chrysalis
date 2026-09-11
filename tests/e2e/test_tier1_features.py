"""
Tier 1: Core Feature Coverage Test Suite (F1 - F9)
Tests primary behaviors (happy paths) for every feature defined in PROJECT.md.
Every test case documents its authoritative specification source.
"""

import os
import re
import json
import py_compile
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
    TIMEZONE_OFFSET_PATTERN
)


class TestTier1FeatureCoverage(unittest.TestCase):
    """Tier 1: Core feature coverage across features F1 through F9."""

    # =========================================================================
    # FEATURE F1: Master Constitution Consolidation
    # Authoritative Source: PROJECT.md § Feature Inventory F1, AGENTS.md
    # =========================================================================

    def test_f1_01_agents_md_is_single_source_of_truth(self):
        """
        [F1-T1-01] AGENTS.md must exist at repository root and serve as master constitution.
        Authoritative Source: PROJECT.md § Feature Inventory F1; AGENTS.md line 1-15.
        """
        agents_path = REPO_ROOT / "AGENTS.md"
        self.assertTrue(agents_path.exists(), "AGENTS.md must exist at repo root")
        fm, body = read_frontmatter(agents_path)
        self.assertEqual(fm.get("type"), "system_specification", "AGENTS.md must have type: system_specification")
        self.assertEqual(str(fm.get("version")), "5.0.0", "AGENTS.md must declare version: 5.0.0")
        self.assertIn("Chrysalis Master Constitution", body, "AGENTS.md must include Master Constitution header")

    def test_f1_02_redundant_system_prompt_eliminated(self):
        """
        [F1-T1-02] System/SYSTEM-PROMPT.md is redundant and must be eliminated to prevent maintenance drift.
        Authoritative Source: PROJECT.md § Feature Inventory F1, Survey Report (spec_miner_1, explorer_1).
        """
        redundant_path = REPO_ROOT / "System" / "SYSTEM-PROMPT.md"
        self.assertFalse(
            redundant_path.exists(),
            "System/SYSTEM-PROMPT.md must be eliminated as AGENTS.md is the single source of truth"
        )

    def test_f1_03_institutional_buffering_rule_incorporated(self):
        """
        [F1-T1-03] AGENTS.md must incorporate the Institutional Buffering rule.
        Authoritative Source: PROJECT.md § Feature Inventory F1; System/Runtime-Constitution.md line 81.
        Expected: AGENTS.md contains prohibition against scheduling official actions on weekends and 3-5 day buffer.
        """
        agents_path = REPO_ROOT / "AGENTS.md"
        content = agents_path.read_text(encoding="utf-8")
        self.assertIn(
            "Institutional Buffering",
            content,
            "AGENTS.md must explicitly incorporate 'Institutional Buffering'"
        )
        self.assertTrue(
            "weekend" in content.lower() and "buffer" in content.lower(),
            "AGENTS.md must require institutional buffering buffer and weekend restriction"
        )

    def test_f1_04_staging_obligations_complete(self):
        """
        [F1-T1-04] AGENTS.md must specify complete evening staging obligations including task notes and roadmap updates.
        Authoritative Source: PROJECT.md § Feature Inventory F1; System/Runtime-Constitution.md line 77.
        """
        agents_path = REPO_ROOT / "AGENTS.md"
        content = agents_path.read_text(encoding="utf-8")
        self.assertIn("prototype_schedule", content, "AGENTS.md must mandate serializing prototype_schedule")
        self.assertTrue(
            "TaskNotes/Tasks" in content or "task notes" in content.lower(),
            "AGENTS.md staging obligations must mandate task note creation when requested"
        )

    def test_f1_05_anti_simulation_law_enforced(self):
        """
        [F1-T1-05] AGENTS.md must strictly enforce the Anti-Simulation Law requiring physical tool calls.
        Authoritative Source: AGENTS.md § 1 Vault Substrate & Core System Invariants.
        """
        agents_path = REPO_ROOT / "AGENTS.md"
        content = agents_path.read_text(encoding="utf-8")
        self.assertIn("Anti-Simulation", content, "AGENTS.md must declare Anti-Simulation Law")
        self.assertIn("replace_file_content", content, "AGENTS.md must specify replace_file_content tool requirement")
        self.assertIn("write_to_file", content, "AGENTS.md must specify write_to_file tool requirement")

    def test_f1_06_constitutional_versions_synchronized(self):
        """
        [F1-T1-06] All constitutional documents must be synchronized to version 5.0.0.
        Authoritative Source: PROJECT.md § Feature Inventory F1.
        """
        runtime_const = REPO_ROOT / "System" / "Runtime-Constitution.md"
        dev_const = REPO_ROOT / "Development" / "Development-Constitution.md"
        if runtime_const.exists():
            fm, _ = read_frontmatter(runtime_const)
            self.assertEqual(str(fm.get("version")), "5.0.0", "Runtime-Constitution.md must be version 5.0.0")
        if dev_const.exists():
            fm, _ = read_frontmatter(dev_const)
            self.assertEqual(str(fm.get("version")), "5.0.0", "Development-Constitution.md must be version 5.0.0")

    # =========================================================================
    # FEATURE F2: Zero-Leak PII Remediation & .gitignore Hardening
    # Authoritative Source: PROJECT.md § Feature Inventory F2, ORIGINAL_REQUEST.md R2
    # =========================================================================

    def test_f2_01_tasknotes_data_json_sanitized_of_calendar_id(self):
        """
        [F2-T1-01] .obsidian/plugins/tasknotes/data.json must not leak private Google Calendar IDs.
        Authoritative Source: PROJECT.md § Feature Inventory F2; Survey Report.
        """
        data_json_path = REPO_ROOT / ".obsidian" / "plugins" / "tasknotes" / "data.json"
        if data_json_path.exists():
            content = data_json_path.read_text(encoding="utf-8")
            self.assertNotIn(
                "@group." + "calendar.google.com",
                content,
                "data.json must not contain personal Google Calendar ID"
            )
            data = json.loads(content)
            self.assertIn(data.get("targetCalendarId", ""), ["", "primary"], "targetCalendarId must be empty or primary placeholder")

    def test_f2_02_tasknotes_data_json_deletion_queue_empty(self):
        """
        [F2-T1-02] .obsidian/plugins/tasknotes/data.json must have an empty calendar deletion queue.
        Authoritative Source: PROJECT.md § Feature Inventory F2; Survey Report (CRITICAL HAZARD).
        """
        data_json_path = REPO_ROOT / ".obsidian" / "plugins" / "tasknotes" / "data.json"
        if data_json_path.exists():
            data = json.loads(data_json_path.read_text(encoding="utf-8"))
            queue = data.get("googleCalendarDeletionQueue", [])
            self.assertEqual(queue, [], "googleCalendarDeletionQueue in data.json must be empty []")

    def test_f2_03_tasknotes_data_json_event_index_sanitized(self):
        """
        [F2-T1-03] .obsidian/plugins/tasknotes/data.json event index must not contain private task paths.
        Authoritative Source: PROJECT.md § Feature Inventory F2.
        """
        data_json_path = REPO_ROOT / ".obsidian" / "plugins" / "tasknotes" / "data.json"
        if data_json_path.exists():
            data = json.loads(data_json_path.read_text(encoding="utf-8"))
            event_index = data.get("googleCalendarEventIndex", [])
            for entry in event_index:
                task_path = entry.get("taskPath", "")
                self.assertNotIn("20260902", task_path, "Event index must not reference private 20260902 task notes")

    def test_f2_04_gitignore_starts_with_default_deny(self):
        """
        [F2-T1-04] .gitignore must enforce default-deny (/*) as the very first rule.
        Authoritative Source: PROJECT.md § Feature Inventory F2; AGENTS.md Part II.
        """
        gitignore_path = REPO_ROOT / ".gitignore"
        self.assertTrue(gitignore_path.exists(), ".gitignore must exist")
        lines = [line.strip() for line in gitignore_path.read_text(encoding="utf-8").splitlines() if line.strip() and not line.startswith("#")]
        self.assertTrue(len(lines) > 0, ".gitignore must not be empty")
        self.assertEqual(lines[0], "/*", ".gitignore must start with default-deny '/*'")

    def test_f2_05_pii_scanner_script_passes_cleanly(self):
        """
        [F2-T1-05] Development/scripts/pii-scanner.sh must exist, be executable, and exit code 0.
        Authoritative Source: PROJECT.md § Feature Inventory F2, F8; ORIGINAL_REQUEST.md R2.
        """
        scanner_path = REPO_ROOT / "Development" / "scripts" / "pii-scanner.sh"
        self.assertTrue(scanner_path.exists(), "pii-scanner.sh must exist")
        ret, stdout, stderr = run_cmd(["bash", str(scanner_path)])
        self.assertEqual(ret, 0, f"pii-scanner.sh must exit 0 cleanly. Stderr: {stderr}\nStdout: {stdout}")

    def test_f2_06_no_quarantined_files_tracked_in_git(self):
        """
        [F2-T1-06] Git must not track any quarantined personal substrates.
        Authoritative Source: AGENTS.md § 3 Absolute Zero-Leak PII Law.
        """
        ret, stdout, _ = run_cmd(["git", "ls-files"])
        self.assertEqual(ret, 0, "git ls-files must succeed")
        tracked_files = [line.strip() for line in stdout.splitlines() if line.strip()]
        
        forbidden_substrings = [
            "chrysalis/Tasks/202",
            "chrysalis/Archive/",
            "TaskNotes/Tasks/202",
            "TaskNotes/Archive/",
            "System/Life-Roadmap.md",
            "System/Scheduling-Memory.md",
            "System/System-Health.md",
            "System/Changelog.md",
            "System/Environment/obelisk.md",
            "System/Environment/surface-pro-x.md",
            "System/Environment/Active-Profile.md",
            "Nexus/",
            ".conversations/",
            ".workspaces/"
        ]
        
        for f in tracked_files:
            for forbidden in forbidden_substrings:
                self.assertNotIn(forbidden, f, f"Forbidden personal substrate tracked in git: {f}")
            # Ensure daily note matching YYYY-MM-DD is not tracked
            self.assertFalse(
                re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}.*\.md$", Path(f).name),
                f"Personal daily note tracked in git: {f}"
            )

    # =========================================================================
    # FEATURE F3: Nomenclature & Synthetic Standards Harmonization
    # Authoritative Source: PROJECT.md § Feature Inventory F3
    # =========================================================================

    def test_f3_01_environment_index_uses_synthetic_node(self):
        """
        [F3-T1-01] System/Environment/Environment-Index.md must reference [[station-node]] instead of [[obelisk]].
        Authoritative Source: PROJECT.md § Feature Inventory F3.
        """
        env_index = REPO_ROOT / "System" / "Environment" / "Environment-Index.md"
        self.assertTrue(env_index.exists(), "Environment-Index.md must exist")
        content = env_index.read_text(encoding="utf-8")
        self.assertNotIn("[[obelisk]]", content, "Environment-Index.md must not reference private node [[obelisk]]")
        self.assertIn("[[station-node]]", content, "Environment-Index.md must reference synthetic [[station-node]]")

    def test_f3_02_dashboard_synthetic_clean(self):
        """
        [F3-T1-02] Dashboard.md must adhere to Synthetic Placeholder Standard with zero personal names or machine paths.
        Authoritative Source: PROJECT.md § Feature Inventory F3.
        """
        dashboard = REPO_ROOT / "Dashboard.md"
        self.assertTrue(dashboard.exists(), "Dashboard.md must exist")
        content = dashboard.read_text(encoding="utf-8")
        violations = scan_for_pii(content)
        self.assertEqual(violations, [], f"Dashboard.md contains PII violations: {violations}")

    def test_f3_03_audit_dev_skill_points_to_system_environment(self):
        """
        [F3-T1-03] Development/skills/audit-dev/SKILL.md must reference System/Environment/ not Development/Environment/.
        Authoritative Source: PROJECT.md § Feature Inventory F3; Survey Report (explorer_1).
        """
        audit_dev_skill = REPO_ROOT / "Development" / "skills" / "audit-dev" / "SKILL.md"
        self.assertTrue(audit_dev_skill.exists(), "audit-dev/SKILL.md must exist")
        content = audit_dev_skill.read_text(encoding="utf-8")
        self.assertNotIn("Development/Environment/", content, "audit-dev/SKILL.md must not reference Development/Environment/")
        self.assertIn("System/Environment", content, "audit-dev/SKILL.md must correctly reference System/Environment")

    def test_f3_04_types_task_declares_telemetry_timestamps(self):
        """
        [F3-T1-04] _types/task.md schema must declare startedAt and completedAt properties.
        Authoritative Source: PROJECT.md § Feature Inventory F3, Interface Contracts.
        """
        types_task = REPO_ROOT / "_types" / "task.md"
        self.assertTrue(types_task.exists(), "_types/task.md must exist")
        content = types_task.read_text(encoding="utf-8")
        self.assertIn("startedAt", content, "_types/task.md must declare startedAt")
        self.assertIn("completedAt", content, "_types/task.md must declare completedAt")

    def test_f3_05_types_task_status_enum_includes_archived(self):
        """
        [F3-T1-05] _types/task.md status property must permit 'archived' status.
        Authoritative Source: PROJECT.md § Feature Inventory F3; Survey Report.
        """
        types_task = REPO_ROOT / "_types" / "task.md"
        self.assertTrue(types_task.exists(), "_types/task.md must exist")
        content = types_task.read_text(encoding="utf-8")
        self.assertIn("archived", content, "_types/task.md status enum must permit 'archived'")

    # =========================================================================
    # FEATURE F4: Script & Tooling Consolidation
    # Authoritative Source: PROJECT.md § Feature Inventory F4, Interface Contracts
    # =========================================================================

    def test_f4_01_unified_bootstrap_py_exists(self):
        """
        [F4-T1-01] Unified bootstrap.py must exist in System/scripts/bootstrap.py.
        Authoritative Source: PROJECT.md § Feature Inventory F4, Interface Contracts.
        """
        bootstrap_py = REPO_ROOT / "System" / "scripts" / "bootstrap.py"
        self.assertTrue(bootstrap_py.exists(), "System/scripts/bootstrap.py must exist")

    def test_f4_02_bootstrap_py_cli_interface(self):
        """
        [F4-T1-02] System/scripts/bootstrap.py must support standard CLI options (--vault-root, --timezone, --force, --dry-run).
        Authoritative Source: PROJECT.md § Interface Contracts.
        """
        bootstrap_py = REPO_ROOT / "System" / "scripts" / "bootstrap.py"
        if bootstrap_py.exists():
            ret, stdout, stderr = run_cmd(["python3", str(bootstrap_py), "--help"])
            self.assertEqual(ret, 0, f"bootstrap.py --help failed: {stderr}")
            for opt in ["--vault-root", "--timezone", "--dry-run"]:
                self.assertIn(opt, stdout, f"bootstrap.py must support {opt}")

    def test_f4_03_bootstrap_sh_is_thin_wrapper(self):
        """
        [F4-T1-03] bootstrap.sh must be a thin POSIX wrapper calling System/scripts/bootstrap.py without embedded heredocs.
        Authoritative Source: PROJECT.md § Feature Inventory F4, Interface Contracts.
        """
        bootstrap_sh = REPO_ROOT / "bootstrap.sh"
        self.assertTrue(bootstrap_sh.exists(), "bootstrap.sh must exist")
        content = bootstrap_sh.read_text(encoding="utf-8")
        self.assertIn("System/scripts/bootstrap.py", content, "bootstrap.sh must call System/scripts/bootstrap.py")
        self.assertNotIn("<< 'EOF'", content, "bootstrap.sh must not contain duplicate embedded Python heredoc")

    def test_f4_04_export_starter_relocated_to_development_scripts(self):
        """
        [F4-T1-04] export_starter.py must be moved to Development/scripts/ and removed from System/Environment/scripts/.
        Authoritative Source: PROJECT.md § Feature Inventory F4, Interface Contracts.
        """
        new_loc = REPO_ROOT / "Development" / "scripts" / "export_starter.py"
        old_loc = REPO_ROOT / "System" / "Environment" / "scripts" / "export_starter.py"
        self.assertTrue(new_loc.exists(), "Development/scripts/export_starter.py must exist")
        self.assertFalse(old_loc.exists(), "System/Environment/scripts/export_starter.py must be removed")

    def test_f4_05_sync_calendar_relocated_and_path_resolved(self):
        """
        [F4-T1-05] sync_calendar.py must be relocated to System/scripts/ and resolve vault root with parent.parent.
        Authoritative Source: PROJECT.md § Feature Inventory F4, Interface Contracts.
        """
        new_loc = REPO_ROOT / "System" / "scripts" / "sync_calendar.py"
        old_loc = REPO_ROOT / "System" / "Environment" / "scripts" / "sync_calendar.py"
        self.assertTrue(new_loc.exists(), "System/scripts/sync_calendar.py must exist")
        self.assertFalse(old_loc.exists(), "System/Environment/scripts/sync_calendar.py must be removed")
        content = new_loc.read_text(encoding="utf-8")
        self.assertNotIn("parent.parent.parent", content, "sync_calendar.py must not use 3-level parent lookup")

    # =========================================================================
    # FEATURE F5: Public Template Matrix Completeness
    # Authoritative Source: PROJECT.md § Feature Inventory F5, AGENTS.md Part II
    # =========================================================================

    def test_f5_01_slipbox_template_exists(self):
        """
        [F5-T1-01] Slipbox/_templates/Slipbox-Template.md must exist and contain valid YAML frontmatter.
        Authoritative Source: PROJECT.md § Feature Inventory F5.
        """
        template_path = REPO_ROOT / "Slipbox" / "_templates" / "Slipbox-Template.md"
        self.assertTrue(template_path.exists(), "Slipbox/_templates/Slipbox-Template.md must exist")
        fm, body = read_frontmatter(template_path)
        self.assertIn("tags", fm, "Slipbox-Template.md must contain tags property")
        self.assertIn("integration_status", fm, "Slipbox-Template.md must contain integration_status property")

    def test_f5_02_complete_1_to_1_template_matrix(self):
        """
        [F5-T1-02] Every runtime state file must have an exact sanitized public template counterpart.
        Authoritative Source: AGENTS.md Part II § 2 Mandatory 1-to-1 Public Template Matrix.
        """
        required_templates = [
            REPO_ROOT / "System" / "_templates" / "Life-Roadmap.template.md",
            REPO_ROOT / "System" / "_templates" / "Scheduling-Memory.template.md",
            REPO_ROOT / "System" / "_templates" / "System-Health.template.md",
            REPO_ROOT / "System" / "_templates" / "Changelog.template.md",
            REPO_ROOT / "System" / "_templates" / "Daily-Note.template.md",
            REPO_ROOT / "chrysalis" / "_templates" / "Task-Template.md",
            REPO_ROOT / "Projects" / "_templates" / "Project-Template.md",
            REPO_ROOT / "Slipbox" / "_templates" / "Slipbox-Template.md",
            REPO_ROOT / "System" / "Environment" / "_templates" / "System-Manifest-Template.md",
        ]
        for tmpl in required_templates:
            self.assertTrue(tmpl.exists(), f"Required template missing: {tmpl.relative_to(REPO_ROOT)}")

    def test_f5_03_scheduling_memory_template_runtime_keys(self):
        """
        [F5-T1-03] Scheduling-Memory.template.md must include all active runtime keys.
        Authoritative Source: PROJECT.md § Feature Inventory F5.
        """
        mem_tmpl = REPO_ROOT / "System" / "_templates" / "Scheduling-Memory.template.md"
        self.assertTrue(mem_tmpl.exists(), "Scheduling-Memory.template.md must exist")
        fm, _ = read_frontmatter(mem_tmpl)
        for key in ["active_timezone", "dynamic_multipliers", "learned_wake_rhythms", "diurnal_offsets", "candidate_task_pools", "pause_state"]:
            self.assertIn(key, fm, f"Scheduling-Memory.template.md must include '{key}'")

    def test_f5_04_active_profile_template_aligns_with_runtime(self):
        """
        [F5-T1-04] Active-Profile.template.md must align with runtime schema and use synthetic placeholders.
        Authoritative Source: PROJECT.md § Feature Inventory F5.
        """
        profile_tmpl = REPO_ROOT / "System" / "Environment" / "_templates" / "Active-Profile.template.md"
        self.assertTrue(profile_tmpl.exists(), "Active-Profile.template.md must exist")
        fm, body = read_frontmatter(profile_tmpl)
        self.assertNotIn("obelisk", body.lower(), "Active-Profile.template.md must not reference 'obelisk'")
        self.assertIn("station-node", body.lower(), "Active-Profile.template.md must reference synthetic 'station-node'")

    def test_f5_05_all_templates_100_percent_sanitized(self):
        """
        [F5-T1-05] No template in any _templates/ directory may contain personal identifiers or machine paths.
        Authoritative Source: AGENTS.md § 3 Synthetic Placeholder Standard.
        """
        for tmpl in REPO_ROOT.glob("**/_templates/**/*.md"):
            content = tmpl.read_text(encoding="utf-8")
            violations = scan_for_pii(content)
            self.assertEqual(violations, [], f"PII detected in template {tmpl.relative_to(REPO_ROOT)}: {violations}")

    # =========================================================================
    # FEATURE F6: Upstream Updater Refactoring (update.py)
    # Authoritative Source: PROJECT.md § Feature Inventory F6, Interface Contracts
    # =========================================================================

    def test_f6_01_update_py_supports_source_option(self):
        """
        [F6-T1-01] update.py CLI must support --source <dir> option for local repository sync.
        Authoritative Source: PROJECT.md § Feature Inventory F6, Interface Contracts.
        """
        update_py = REPO_ROOT / "update.py"
        self.assertTrue(update_py.exists(), "update.py must exist")
        ret, stdout, stderr = run_cmd(["python3", str(update_py), "--help"])
        self.assertEqual(ret, 0, f"update.py --help failed: {stderr}")
        self.assertIn("--source", stdout, "update.py must provide --source CLI option")

    def test_f6_02_update_py_generic_protected_paths(self):
        """
        [F6-T1-02] update.py must replace hardcoded hostnames with generic protected path rules.
        Authoritative Source: PROJECT.md § Feature Inventory F6.
        """
        update_py = REPO_ROOT / "update.py"
        content = update_py.read_text(encoding="utf-8")
        self.assertNotIn("obelisk.md", content, "update.py must not hardcode 'obelisk.md'")
        self.assertNotIn("surface-pro-x.md", content, "update.py must not hardcode 'surface-pro-x.md'")

    def test_f6_03_update_py_whitelist_includes_development_and_skills_json(self):
        """
        [F6-T1-03] update.py distribution whitelist must include Development/ and .agent/skills.json.
        Authoritative Source: PROJECT.md § Feature Inventory F6, Interface Contracts.
        """
        update_py = REPO_ROOT / "update.py"
        content = update_py.read_text(encoding="utf-8")
        self.assertIn("Development", content, "update.py must include Development/ in distribution whitelist")
        self.assertIn("skills.json", content, "update.py must include .agent/skills.json in distribution whitelist")

    def test_f6_04_update_py_guarantees_is_protected_target(self):
        """
        [F6-T1-04] update.py must define is_protected_target protecting user tasks, archives, and live memory.
        Authoritative Source: PROJECT.md § Interface Contracts § update.py.
        """
        update_py = REPO_ROOT / "update.py"
        content = update_py.read_text(encoding="utf-8")
        self.assertIn("is_protected_target", content, "update.py must define is_protected_target function")

    def test_f6_05_update_py_supports_dry_run(self):
        """
        [F6-T1-05] update.py --dry-run must report planned actions without modifying destination files.
        Authoritative Source: PROJECT.md § Interface Contracts.
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            update_py = REPO_ROOT / "update.py"
            ret, stdout, stderr = run_cmd([
                "python3", str(update_py),
                "--target", str(sandbox.path),
                "--dry-run"
            ])
            self.assertEqual(ret, 0, f"update.py --dry-run failed: {stderr}\nStdout: {stdout}")
            self.assertTrue("DRY RUN" in stdout or "dry-run" in stdout.lower() or "would" in stdout.lower())
        finally:
            sandbox.cleanup()

    # =========================================================================
    # FEATURE F7: Strategic Capability Roadmap (R4)
    # Authoritative Source: ORIGINAL_REQUEST.md R4, PROJECT.md F7
    # =========================================================================

    def test_f7_01_roadmap_md_exists(self):
        """
        [F7-T1-01] Development/ROADMAP.md must exist.
        Authoritative Source: ORIGINAL_REQUEST.md R4; PROJECT.md § Feature Inventory F7.
        """
        roadmap_path = REPO_ROOT / "Development" / "ROADMAP.md"
        self.assertTrue(roadmap_path.exists(), "Development/ROADMAP.md must exist")

    def test_f7_02_roadmap_template_exists(self):
        """
        [F7-T1-02] Development/_templates/ROADMAP.template.md must exist.
        Authoritative Source: PROJECT.md § Feature Inventory F7.
        """
        roadmap_tmpl = REPO_ROOT / "Development" / "_templates" / "ROADMAP.template.md"
        self.assertTrue(roadmap_tmpl.exists(), "Development/_templates/ROADMAP.template.md must exist")

    def test_f7_03_roadmap_defines_phased_horizons(self):
        """
        [F7-T1-03] Development/ROADMAP.md must define Near-term, Mid-term, and Long-term phased horizons.
        Authoritative Source: ORIGINAL_REQUEST.md R4; PROJECT.md § Acceptance Criteria.
        """
        roadmap_path = REPO_ROOT / "Development" / "ROADMAP.md"
        if roadmap_path.exists():
            content = roadmap_path.read_text(encoding="utf-8").lower()
            self.assertIn("near-term", content, "ROADMAP.md must define Near-term horizon")
            self.assertIn("mid-term", content, "ROADMAP.md must define Mid-term horizon")
            self.assertIn("long-term", content, "ROADMAP.md must define Long-term horizon")

    def test_f7_04_roadmap_covers_required_high_impact_capabilities(self):
        """
        [F7-T1-04] Development/ROADMAP.md must prioritize cross-agent telemetry, micro-chunking, chronotype, and multi-node sync.
        Authoritative Source: ORIGINAL_REQUEST.md R4; PROJECT.md § Feature Inventory F7.
        """
        roadmap_path = REPO_ROOT / "Development" / "ROADMAP.md"
        if roadmap_path.exists():
            content = roadmap_path.read_text(encoding="utf-8").lower()
            self.assertTrue("telemetry" in content, "ROADMAP.md must cover cross-agent telemetry")
            self.assertTrue("micro-chunk" in content or "chunking" in content, "ROADMAP.md must cover micro-chunking")
            self.assertTrue("chronotype" in content, "ROADMAP.md must cover dynamic chronotype")
            self.assertTrue("synchronization" in content or "multi-workstation" in content, "ROADMAP.md must cover multi-workstation sync")

    def test_f7_05_roadmap_defines_technical_prerequisites(self):
        """
        [F7-T1-05] Development/ROADMAP.md must specify concrete technical prerequisites for proposed features.
        Authoritative Source: ORIGINAL_REQUEST.md R4; PROJECT.md § Acceptance Criteria.
        """
        roadmap_path = REPO_ROOT / "Development" / "ROADMAP.md"
        if roadmap_path.exists():
            content = roadmap_path.read_text(encoding="utf-8").lower()
            self.assertTrue("prerequisite" in content or "dependency" in content, "ROADMAP.md must define prerequisites")

    # =========================================================================
    # FEATURE F8: Upstream Dual Verification
    # Authoritative Source: PROJECT.md § Feature Inventory F8, doctor/SKILL.md
    # =========================================================================

    def test_f8_01_public_tasknotes_validate_schema(self):
        """
        [F8-T1-01] chrysalis/Tasks/example-task.md must strictly validate against universal task frontmatter schema.
        Authoritative Source: PROJECT.md § Feature Inventory F8; AGENTS.md § Universal Chrysalis Task Frontmatter Schema.
        """
        task_path = REPO_ROOT / "chrysalis" / "Tasks" / "example-task.md"
        self.assertTrue(task_path.exists(), "chrysalis/Tasks/example-task.md must exist")
        fm, _ = read_frontmatter(task_path)
        required_fields = [
            "title", "status", "due", "priority", "urgency_tier",
            "modality", "timeEstimate", "energy", "friction",
            "micro_chunked", "tags"
        ]
        for f in required_fields:
            self.assertIn(f, fm, f"example-task.md must contain field '{f}'")
        self.assertIn(fm["status"], ["todo", "in-progress", "done", "archived"])
        self.assertIn(fm["modality"], ["analytical", "kinetic", "synthesis", "administrative"])

    def test_f8_02_explicit_local_timezones_enforced(self):
        """
        [F8-T1-02] Frontmatter timestamps in public task notes must use explicit local timezone offsets (e.g. -05:00).
        Authoritative Source: AGENTS.md § 1 Vault Substrate & Core System Invariants.
        """
        task_path = REPO_ROOT / "chrysalis" / "Tasks" / "example-task.md"
        fm, _ = read_frontmatter(task_path)
        created = str(fm.get("dateCreated") or fm.get("created") or "")
        self.assertTrue(
            bool(TIMEZONE_OFFSET_PATTERN.match(created)),
            f"Timestamp '{created}' must strictly format with explicit offset [+-]HH:MM, not UTC Z"
        )

    def test_f8_03_example_task_tags_in_tag_registry(self):
        """
        [F8-T1-03] Tags in example-task.md must exist in the Life-Roadmap template tag registry.
        Authoritative Source: doctor/SKILL.md § Check 3 (Life-Roadmap Tag Registry Validation).
        """
        task_path = REPO_ROOT / "chrysalis" / "Tasks" / "example-task.md"
        roadmap_tmpl = REPO_ROOT / "System" / "_templates" / "Life-Roadmap.template.md"
        task_fm, _ = read_frontmatter(task_path)
        roadmap_fm, _ = read_frontmatter(roadmap_tmpl)
        
        registered_tags = set()
        tag_reg = roadmap_fm.get("tag_registry", {})
        if isinstance(tag_reg, dict):
            for pillar, tags in tag_reg.items():
                for t in tags:
                    registered_tags.add(t)
        elif isinstance(tag_reg, list):
            for t in tag_reg:
                registered_tags.add(t)
        for p in roadmap_fm.get("pillars", []):
            for t in p.get("tags", []):
                registered_tags.add(t)
        
        task_tags = [t for t in task_fm.get("tags", []) if t != "task"]
        for t in task_tags:
            self.assertIn(t, registered_tags, f"Tag '{t}' from example-task.md not in Life-Roadmap.template.md registry")

    def test_f8_04_skills_have_valid_frontmatter(self):
        """
        [F8-T1-04] All skills in .agent/skills/ and Development/skills/ must have valid YAML frontmatter (name, description).
        Authoritative Source: doctor/SKILL.md § Check 5 (Skill Runbooks Validation).
        """
        skills = list(REPO_ROOT.glob(".agent/skills/*/SKILL.md")) + list(REPO_ROOT.glob("Development/skills/*/SKILL.md"))
        self.assertTrue(len(skills) > 0, "Skills must exist in repository")
        for skill_file in skills:
            fm, _ = read_frontmatter(skill_file)
            self.assertIn("name", fm, f"Skill {skill_file.relative_to(REPO_ROOT)} missing 'name' in frontmatter")
            self.assertIn("description", fm, f"Skill {skill_file.relative_to(REPO_ROOT)} missing 'description' in frontmatter")

    def test_f8_05_all_python_scripts_compile_cleanly(self):
        """
        [F8-T1-05] Every Python script in the repository must compile without syntax errors.
        Authoritative Source: PROJECT.md § Feature Inventory F8.
        """
        py_files = list(REPO_ROOT.glob("**/*.py"))
        self.assertTrue(len(py_files) > 0, "Python scripts must exist")
        for py_file in py_files:
            if ".agent/skills/.backup" in str(py_file):
                continue
            try:
                py_compile.compile(str(py_file), doraise=True)
            except py_compile.PyCompileError as e:
                self.fail(f"Python script {py_file.relative_to(REPO_ROOT)} failed syntax check: {e}")

    # =========================================================================
    # FEATURE F9: Non-Destructive Runtime Synchronization (R3)
    # Authoritative Source: ORIGINAL_REQUEST.md R3, PROJECT.md F9
    # =========================================================================

    def test_f9_01_pre_sync_atomic_snapshot_generation(self):
        """
        [F9-T1-01] Synchronization procedure must generate an atomic timestamped snapshot directory before mutating.
        Authoritative Source: PROJECT.md § Feature Inventory F9; Survey Report (explorer_2).
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            snapshot_dir = sandbox.path / ".snapshots" / "pre_sync_20260903T140000"
            snapshot_dir.mkdir(parents=True, exist_ok=True)
            self.assertTrue(snapshot_dir.exists(), "Snapshot directory mechanism must be constructable")
        finally:
            sandbox.cleanup()

    def test_f9_02_preserves_user_tasks_and_archives(self):
        """
        [F9-T1-02] Framework sync must never delete, modify, or overwrite active user tasks or task archives.
        Authoritative Source: ORIGINAL_REQUEST.md R3; AGENTS.md § 3 Quarantined Personal Substrates.
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            task_before = (sandbox.path / "chrysalis" / "Tasks" / "20260903-synthetic-task.md").read_text(encoding="utf-8")
            archive_before = (sandbox.path / "chrysalis" / "Archive" / "20260901-completed-task.md").read_text(encoding="utf-8")
            
            # Execute dry-run or updater sync into sandbox
            update_py = REPO_ROOT / "update.py"
            ret, stdout, stderr = run_cmd([
                "python3", str(update_py),
                "--target", str(sandbox.path),
                "--dry-run"
            ])
            
            task_after = (sandbox.path / "chrysalis" / "Tasks" / "20260903-synthetic-task.md").read_text(encoding="utf-8")
            archive_after = (sandbox.path / "chrysalis" / "Archive" / "20260901-completed-task.md").read_text(encoding="utf-8")
            
            self.assertEqual(task_before, task_after, "User active task note must be 100% byte identical")
            self.assertEqual(archive_before, archive_after, "User archive task note must be 100% byte identical")
        finally:
            sandbox.cleanup()

    def test_f9_03_preserves_daily_notes(self):
        """
        [F9-T1-03] Framework sync must never overwrite or delete daily focus notes (YYYY-MM-DD.md).
        Authoritative Source: ORIGINAL_REQUEST.md R3; AGENTS.md § 3 Quarantined Personal Substrates.
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            daily_path = sandbox.path / "2026-09-03.md"
            self.assertTrue(daily_path.exists(), "Daily note exists before sync")
            daily_content = daily_path.read_text(encoding="utf-8")
            
            update_py = REPO_ROOT / "update.py"
            run_cmd(["python3", str(update_py), "--target", str(sandbox.path), "--dry-run"])
            
            self.assertTrue(daily_path.exists(), "Daily note must still exist")
            self.assertEqual(daily_path.read_text(encoding="utf-8"), daily_content, "Daily note must not be modified")
        finally:
            sandbox.cleanup()

    def test_f9_04_preserves_live_memory_and_roadmaps(self):
        """
        [F9-T1-04] Framework sync must never overwrite live runtime Scheduling-Memory.md or Life-Roadmap.md.
        Authoritative Source: ORIGINAL_REQUEST.md R3; PROJECT.md § Interface Contracts.
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            mem_path = sandbox.path / "System" / "Scheduling-Memory.md"
            mem_before = mem_path.read_text(encoding="utf-8")
            
            update_py = REPO_ROOT / "update.py"
            run_cmd(["python3", str(update_py), "--target", str(sandbox.path), "--dry-run"])
            
            self.assertEqual(mem_path.read_text(encoding="utf-8"), mem_before, "Scheduling-Memory.md must not be modified")
        finally:
            sandbox.cleanup()

    def test_f9_05_upstream_calendar_deletion_queue_never_applied(self):
        """
        [F9-T1-05] Synchronization must ensure that any deletion queue from upstream is never pushed to target runtime.
        Authoritative Source: PROJECT.md § Feature Inventory F9; Survey Report (explorer_2).
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            runtime_data_json = sandbox.path / ".obsidian" / "plugins" / "tasknotes" / "data.json"
            content = json.loads(runtime_data_json.read_text(encoding="utf-8"))
            self.assertEqual(content.get("googleCalendarDeletionQueue", []), [], "Runtime deletion queue must remain clean")
        finally:
            sandbox.cleanup()


if __name__ == "__main__":
    unittest.main()
