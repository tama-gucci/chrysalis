"""
Unit tests for Milestone 1 contracts and persistent agent memory.
Validates contracts/agent-runtime.contract.md, contracts/mdbase-collection.contract.md,
System/Memory.md, and System/_templates/Memory.template.md.
"""

import json
import re
import unittest
from pathlib import Path
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent


def parse_frontmatter(content: str):
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except Exception:
        fm = {}
    return fm, parts[2]


class TestContractsAndMemory(unittest.TestCase):
    """Test suite validating Milestone 1 shared contracts and persistent memory."""

    def test_agent_runtime_contract_structure(self):
        contract_path = REPO_ROOT / "contracts" / "agent-runtime.contract.md"
        self.assertTrue(contract_path.exists(), "agent-runtime.contract.md must exist")

        content = contract_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)

        # Frontmatter validation
        self.assertEqual(fm.get("kind"), "mdbase.contract")
        self.assertEqual(fm.get("id"), "agent-runtime")
        self.assertEqual(fm.get("contract_type"), "agent_runtime")
        self.assertEqual(fm.get("spec_version"), "0.3.0")

        # 8 lifecycle states
        expected_states = [
            "INITIALIZE",
            "CONTEXT_ASSEMBLY",
            "MEMORY_RETRIEVAL",
            "PLAN_PROPOSAL",
            "APPROVAL_GATE",
            "ACT",
            "OUTCOME_RECORDING",
            "CONTINUATION",
        ]
        for state in expected_states:
            self.assertIn(state, body, f"Agent runtime contract must define state {state}")

        # 9 permitted actions
        expected_actions = [
            "create_record",
            "read_record",
            "update_record",
            "delete_record",
            "query_records",
            "ingest_source",
            "reconcile_roadmap",
            "propose_plan",
            "execute_plan",
        ]
        for action in expected_actions:
            self.assertIn(action, body, f"Contract must specify action {action}")

        # Exact JSON Schema 2020-12 envelope mentions
        self.assertIn("AgentActionInput", body)
        self.assertIn("AgentActionOutput", body)
        self.assertIn("https://json-schema.org/draft/2020-12/schema", body)

        # Concurrency & Security invariants
        self.assertIn("concurrent_modification", body)
        self.assertIn("if_revision", body)
        self.assertIn("sha256", body)
        self.assertIn("approval_required", body)
        self.assertIn("simulation_prohibited", body)
        self.assertIn("<untrusted_document_payload>", body)

    def test_mdbase_collection_contract_structure(self):
        contract_path = REPO_ROOT / "contracts" / "mdbase-collection.contract.md"
        self.assertTrue(contract_path.exists(), "mdbase-collection.contract.md must exist")

        content = contract_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)

        # Frontmatter validation
        self.assertEqual(fm.get("kind"), "mdbase.contract")
        self.assertEqual(fm.get("id"), "chrysalis-mdbase-collection")
        self.assertEqual(fm.get("version"), "0.3.0")

        # 4 collection types
        expected_types = ["task", "project", "zettel", "source"]
        for t in expected_types:
            self.assertIn(f"name: {t}", body, f"Collection contract must define type {t}")

        # Tripartite and source path globs
        self.assertTrue("TaskNotes/Tasks/**/*.md" in body or "chrysalis/Tasks/**/*.md" in body)
        self.assertIn("Projects/**/Roadmap.md", body)
        self.assertIn("Slipbox/**/*.md", body)
        self.assertIn("Sources/**/*.md", body)

        # Cognitive and temporal invariants
        self.assertIn("date_uncertain", body)
        self.assertIn("read_defaults", body)
        self.assertIn("lifecycle", body)
        self.assertIn("duplicate_source_detected", body)

    def test_system_memory_document(self):
        memory_path = REPO_ROOT / "System" / "Memory.md"
        self.assertTrue(memory_path.exists(), "System/Memory.md must exist")

        content = memory_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(content)

        # Frontmatter checks
        self.assertEqual(fm.get("schema_version"), "1.0.0")
        self.assertIn("last_updated", fm)
        self.assertRegex(fm["last_updated"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[+-]\d{2}:\d{2}$")

        user_profile = fm.get("user_profile", {})
        self.assertEqual(user_profile.get("timezone_offset"), "-05:00")
        self.assertTrue(user_profile.get("focus_preferences", {}).get("weekend_admin_lockout"))

        modalities = fm.get("cognitive_modality_defaults", {})
        self.assertIn("analytical", modalities)
        self.assertIn("synthesis", modalities)
        self.assertIn("kinetic", modalities)
        self.assertIn("administrative", modalities)

        for mod, cfg in modalities.items():
            mult = cfg.get("multiplier", 1.0)
            self.assertTrue(0.20 <= mult <= 2.00, f"Multiplier for {mod} must be in [0.20, 2.00]")

        horizons = fm.get("active_horizons", {})
        self.assertEqual(horizons.get("planning_window_days"), 14)
        self.assertIsInstance(horizons.get("active_projects"), list)

        # Body checks
        self.assertIn("Strategic Directives", body)
        self.assertIn("Past Session Outcomes Ledger", body)

    def test_system_memory_template_1to1_matrix(self):
        template_path = REPO_ROOT / "System" / "_templates" / "Memory.template.md"
        self.assertTrue(template_path.exists(), "System/_templates/Memory.template.md must exist")

        content = template_path.read_text(encoding="utf-8")
        self.assertIn("schema_version: \"1.0.0\"", content)
        self.assertIn("{{TIMESTAMP}}", content)
        self.assertIn("{{TIMEZONE_OFFSET}}", content)
        self.assertIn("planning_window_days: 14", content)
        self.assertIn("cognitive_modality_defaults:", content)


if __name__ == "__main__":
    unittest.main()
