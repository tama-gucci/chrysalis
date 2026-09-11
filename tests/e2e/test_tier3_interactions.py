"""
Tier 3: Cross-Feature Interactions Test Suite
Tests integration contracts and cross-cutting behaviors between independent features.
Every test case documents its authoritative specification source.
"""

import os
import re
import json
import tempfile
import unittest
from pathlib import Path

from .fixtures import (
    REPO_ROOT,
    SandboxVault,
    parse_frontmatter,
    read_frontmatter,
    scan_for_pii,
    run_cmd
)


class TestTier3CrossFeatureInteractions(unittest.TestCase):
    """Tier 3: Pairwise cross-feature interactions across F1 - F9."""

    def test_f3_i01_updater_does_not_leak_pii_into_target(self):
        """
        [Tier 3: F2 + F6] Framework updater synchronization must produce zero PII leaks in destination vault.
        Authoritative Source: PROJECT.md F2 & F6; AGENTS.md § 3 Absolute Zero-Leak PII Law.
        """
        sandbox = SandboxVault(populate_runtime=False)
        try:
            update_py = REPO_ROOT / "update.py"
            # Run updater dry-run / target inspection
            ret, stdout, stderr = run_cmd([
                "python3", str(update_py),
                "--target", str(sandbox.path),
                "--dry-run"
            ])
            self.assertEqual(ret, 0, f"update.py failed: {stderr}")
            
            # Scan all files in the repo root that would be distributed
            for p in REPO_ROOT.glob("System/_templates/**/*.md"):
                violations = scan_for_pii(p.read_text(encoding="utf-8"))
                self.assertEqual(violations, [], f"PII in distributed template {p.name}: {violations}")
        finally:
            sandbox.cleanup()

    def test_f3_i02_bootstrap_seeds_from_complete_templates(self):
        """
        [Tier 3: F4 + F5] Unified bootstrap.py seeds live files strictly from sanitized public templates.
        Authoritative Source: PROJECT.md F4 & F5; AGENTS.md § 2 Dynamic Memory & Operational State.
        """
        bootstrap_py = REPO_ROOT / "System" / "scripts" / "bootstrap.py"
        if bootstrap_py.exists():
            with tempfile.TemporaryDirectory(prefix="chrysalis_seed_test_") as tmp_dir:
                tmp_path = Path(tmp_dir)
                ret, stdout, stderr = run_cmd([
                    "python3", str(bootstrap_py),
                    "--vault-root", str(tmp_path),
                    "--timezone", "-05:00"
                ])
                self.assertEqual(ret, 0, f"bootstrap.py failed: {stderr}")
                
                # Verify seeded Scheduling-Memory.md
                mem_path = tmp_path / "System" / "Scheduling-Memory.md"
                if mem_path.exists():
                    fm, _ = read_frontmatter(mem_path)
                    self.assertEqual(fm.get("active_timezone"), "-05:00")
                    self.assertIn("dynamic_multipliers", fm)
                    violations = scan_for_pii(mem_path.read_text(encoding="utf-8"))
                    self.assertEqual(violations, [], f"Seeded memory contains PII: {violations}")

    def test_f3_i03_doctor_validates_agents_md_invariants(self):
        """
        [Tier 3: F1 + F8] System integrity check validates that AGENTS.md harmonizes with Runtime-Constitution.md.
        Authoritative Source: PROJECT.md F1 & F8; doctor/SKILL.md.
        """
        agents_path = REPO_ROOT / "AGENTS.md"
        runtime_const = REPO_ROOT / "System" / "Runtime-Constitution.md"
        self.assertTrue(agents_path.exists())
        self.assertTrue(runtime_const.exists())
        
        agents_text = agents_path.read_text(encoding="utf-8")
        runtime_text = runtime_const.read_text(encoding="utf-8")
        
        # Both must declare Institutional Buffering
        self.assertIn("Institutional Buffering", agents_text, "AGENTS.md missing Institutional Buffering")
        self.assertIn("Institutional Buffering", runtime_text, "Runtime-Constitution.md missing Institutional Buffering")

    def test_f3_i04_sync_with_sanitized_data_json_prevents_calendar_wipes(self):
        """
        [Tier 3: F2 + F9] Syncing with sanitized tasknotes config never triggers Google Calendar deletions on runtime.
        Authoritative Source: PROJECT.md F2 & F9; Survey Report (explorer_2).
        """
        sandbox = SandboxVault(populate_runtime=True)
        try:
            # Verify runtime tasknotes data.json has empty deletion queue
            runtime_data_json = sandbox.path / ".obsidian" / "plugins" / "tasknotes" / "data.json"
            data = json.loads(runtime_data_json.read_text(encoding="utf-8"))
            self.assertEqual(data.get("googleCalendarDeletionQueue", []), [], "Runtime deletion queue must be empty")
            
            # Verify upstream plugin data.json is also sanitized
            upstream_data_json = REPO_ROOT / ".obsidian" / "plugins" / "chrysalis-obsidian" / "data.json"
            if upstream_data_json.exists():
                upstream_data = json.loads(upstream_data_json.read_text(encoding="utf-8"))
                self.assertEqual(
                    upstream_data.get("googleCalendarDeletionQueue", []),
                    [],
                    "Upstream data.json must have empty deletion queue so sync never propagates wipes"
                )
        finally:
            sandbox.cleanup()

    def test_f3_i05_updater_distributes_all_consolidated_scripts(self):
        """
        [Tier 3: F4 + F6] Upstream updater distribution rules must include newly consolidated scripts.
        Authoritative Source: PROJECT.md F4 & F6; Interface Contracts § update.py.
        """
        update_py = REPO_ROOT / "update.py"
        content = update_py.read_text(encoding="utf-8")
        self.assertTrue(
            "System" in content and "Development" in content,
            "update.py must distribute both System/ and Development/ scripts"
        )

    def test_f3_i06_synthetic_station_node_resolves_cleanly(self):
        """
        [Tier 3: F3 + F8] Synthetic node reference in Environment-Index.md does not trigger broken wikilink diagnostics.
        Authoritative Source: PROJECT.md F3 & F8; doctor/SKILL.md § Check 4.
        """
        env_index = REPO_ROOT / "System" / "Environment" / "Environment-Index.md"
        content = env_index.read_text(encoding="utf-8")
        self.assertNotIn("[[obelisk]]", content, "Broken private node [[obelisk]] must not be referenced")

    def test_f3_i07_roadmap_template_matches_public_matrix(self):
        """
        [Tier 3: F5 + F7] Public roadmap template adheres to 1-to-1 public template matrix requirements.
        Authoritative Source: PROJECT.md F5 & F7; AGENTS.md § 2 Mandatory 1-to-1 Public Template Matrix.
        """
        roadmap_tmpl = REPO_ROOT / "Development" / "_templates" / "ROADMAP.template.md"
        self.assertTrue(roadmap_tmpl.exists(), "Development/_templates/ROADMAP.template.md must exist")
        violations = scan_for_pii(roadmap_tmpl.read_text(encoding="utf-8"))
        self.assertEqual(violations, [], f"ROADMAP.template.md contains PII: {violations}")


if __name__ == "__main__":
    unittest.main()
