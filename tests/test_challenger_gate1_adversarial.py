"""
Empirical Challenger Test Suite for Gate 1 Review:
1. Path escaping & traversal (link_target_escapes_collection)
2. Out-of-horizon deliverable retention (14-day window, scheduled: null, urgency_tier: 1)
3. Uncertain date representation (due: null, date_uncertain: true, RFC 3339)
4. Multiplier learning bounds & clamping strictly within [0.20, 2.00]
5. Cryptographic SHA-256 deduplication and collision resistance
6. Frontmatter schema validation & negative tests
"""

import hashlib
import json
import math
import os
import re
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath
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


def extract_yaml_blocks(markdown_text: str):
    """Extract all YAML/type blocks from a Markdown contract."""
    blocks = []
    # Match ```yaml ... ```
    pattern = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)
    for m in pattern.finditer(markdown_text):
        try:
            parsed = yaml.safe_load(m.group(1))
            if parsed:
                blocks.append(parsed)
        except Exception:
            pass
    return blocks


# ----------------------------------------------------------------------
# Helper functions modeling framework specifications
# ----------------------------------------------------------------------

def resolve_and_validate_path(target_path_str: str, collection_root: PurePosixPath = PurePosixPath(".")) -> str:
    """
    Normalizes and validates a link or file path against collection root escaping.
    Contract §3 Rule 5 & §5.2:
    - Rejects paths containing '..' that resolve outside collection root with 'link_target_escapes_collection'.
    - Rejects raw path traversal tokens '..' or absolute paths outside collection root.
    """
    # Check for null bytes
    if "\x00" in target_path_str:
        raise ValueError("link_target_escapes_collection: null byte detected in path")

    # Check for URL encoded traversal '%2e%2e'
    if "%2e%2e" in target_path_str.lower():
        raise ValueError("link_target_escapes_collection: URL-encoded traversal detected")

    # Normalize backslashes to slashes
    clean_str = target_path_str.replace("\\", "/")

    # Check for absolute root escaping (e.g. /etc/passwd or /root)
    if clean_str.startswith("/"):
        raise ValueError("link_target_escapes_collection: absolute path outside collection root")

    # Check for raw path traversal tokens '..' (Contract §3 Rule 5: No path may contain path traversal tokens)
    parts_raw = clean_str.split("/")
    if ".." in parts_raw:
        raise ValueError("link_target_escapes_collection: path traversal token '..' detected")

    # Resolve pure posix path parts
    parts = []
    for seg in clean_str.split("/"):
        if not seg or seg == ".":
            continue
        if seg == "..":
            if not parts:
                raise ValueError("link_target_escapes_collection: path resolves outside collection root")
            parts.pop()
        else:
            parts.append(seg)

    resolved = "/".join(parts)
    return resolved


def update_multiplier(
    current_multiplier: float,
    actual_minutes: float,
    estimated_minutes: float,
    learning_rate: float = 0.10,
    min_bound: float = 0.20,
    max_bound: float = 2.00,
    round_decimals: int = 2
) -> float:
    """
    Deterministic multiplier update formula from System/Memory.md:
    Multiplier_new = Multiplier_current + 0.10 * (T_actual / T_estimated - Multiplier_current)
    clamped strictly to [0.20, 2.00].
    """
    if estimated_minutes <= 0:
        # Avoid ZeroDivisionError; return clamped current multiplier
        return max(min_bound, min(max_bound, round(current_multiplier, round_decimals)))

    if actual_minutes < 0:
        actual_minutes = 0.0

    ratio = actual_minutes / estimated_minutes
    raw_new = current_multiplier + learning_rate * (ratio - current_multiplier)
    clamped = max(min_bound, min(max_bound, raw_new))
    return round(clamped, round_decimals)


class TestChallengerGate1Adversarial(unittest.TestCase):
    """Adversarial challenge test cases for Gate 1 collection contract & memory."""

    @classmethod
    def setUpClass(cls):
        cls.collection_contract_path = REPO_ROOT / "contracts" / "mdbase-collection.contract.md"
        cls.memory_path = REPO_ROOT / "System" / "Memory.md"
        cls.memory_template_path = REPO_ROOT / "System" / "_templates" / "Memory.template.md"

        cls.assertTrue(cls.collection_contract_path.exists(), "Collection contract must exist")
        cls.assertTrue(cls.memory_path.exists(), "System/Memory.md must exist")
        cls.assertTrue(cls.memory_template_path.exists(), "Memory template must exist")

        cls.collection_content = cls.collection_contract_path.read_text(encoding="utf-8")
        cls.memory_content = cls.memory_path.read_text(encoding="utf-8")
        cls.memory_fm, cls.memory_body = parse_frontmatter(cls.memory_content)

    # ==================================================================
    # 1. Path Escaping & Traversal Challenges
    # ==================================================================

    def test_path_escaping_adversarial_rejection(self):
        """Verify path normalizer rigorously rejects links escaping collection root."""
        adversarial_escape_payloads = [
            "../secret.md",
            "../../etc/passwd",
            "Projects/../../outside.md",
            "chrysalis/Tasks/../../../outside.md",
            "/etc/shadow",
            "/root/.ssh/id_rsa",
            "Projects/%2e%2e/secret.md",
            "chrysalis/Tasks/..\\..\\outside.md",
            "chrysalis/Tasks/task-1.md\x00.evil",
        ]

        for payload in adversarial_escape_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError, msg=f"Payload '{payload}' must be rejected with root escape error"):
                    resolve_and_validate_path(payload)

    def test_valid_collection_paths_accepted(self):
        """Verify legitimate relative collection paths are accepted and normalized."""
        valid_paths = [
            ("Projects/cs410/Roadmap.md", "Projects/cs410/Roadmap.md"),
            ("chrysalis/Tasks/hw1-task.md", "chrysalis/Tasks/hw1-task.md"),
            ("Slipbox/20260922100000-note.md", "Slipbox/20260922100000-note.md"),
            ("Sources/cs410-syllabus.md", "Sources/cs410-syllabus.md"),
            ("./chrysalis/Tasks/hw1-task.md", "chrysalis/Tasks/hw1-task.md"),
            ("chrysalis//Tasks///hw1-task.md", "chrysalis/Tasks/hw1-task.md"),
        ]

        for raw, expected in valid_paths:
            with self.subTest(raw=raw):
                resolved = resolve_and_validate_path(raw)
                self.assertEqual(resolved, expected)

    def test_canonical_path_regexes_from_contract(self):
        """Verify the exact regexes defined in Section 3 Table 1 of mdbase-collection contract."""
        # 1. Task regex: ^[0-9]{8}-[a-z0-9-]+(\.md)?$
        task_re = re.compile(r"^[0-9]{8}-[a-z0-9-]+(\.md)?$")
        self.assertTrue(task_re.match("20260922-cs410-hw1.md"))
        self.assertTrue(task_re.match("20260922-cs410-hw1"))
        self.assertFalse(task_re.match("2026092-bad.md"))  # 7 digits
        self.assertFalse(task_re.match("20260922_bad.md"))  # underscore
        self.assertFalse(task_re.match("20260922-Bad.md"))  # uppercase
        self.assertFalse(task_re.match("20260922-.md"))  # missing slug

        # 2. Project Roadmap regex: ^Projects/[a-z0-9-]+/Roadmap\.md$
        project_re = re.compile(r"^Projects/[a-z0-9-]+/Roadmap\.md$")
        self.assertTrue(project_re.match("Projects/chrysalis-architecture/Roadmap.md"))
        self.assertTrue(project_re.match("Projects/cs410/Roadmap.md"))
        self.assertFalse(project_re.match("Projects/Roadmap.md"))  # missing project folder
        self.assertFalse(project_re.match("Projects/CS410/Roadmap.md"))  # uppercase
        self.assertFalse(project_re.match("Projects/cs410/tasks.md"))  # not Roadmap.md

        # 3. Zettel regex: ^[0-9]{14}(-[a-z0-9-]+)?(\.md)?$
        zettel_re = re.compile(r"^[0-9]{14}(-[a-z0-9-]+)?(\.md)?$")
        self.assertTrue(zettel_re.match("20260922100000.md"))
        self.assertTrue(zettel_re.match("20260922100000-bayesian-inference.md"))
        self.assertTrue(zettel_re.match("20260922100000-bayesian-inference"))
        self.assertFalse(zettel_re.match("2026092210000-note.md"))  # 13 digits
        self.assertFalse(zettel_re.match("20260922100000_note.md"))  # underscore

        # 4. Source regex: ^[a-z0-9-]+(\.md)?$
        source_re = re.compile(r"^[a-z0-9-]+(\.md)?$")
        self.assertTrue(source_re.match("cs410-syllabus-f26.md"))
        self.assertTrue(source_re.match("lecture-01-transcript"))
        self.assertFalse(source_re.match("cs410_syllabus.md"))  # underscore
        self.assertFalse(source_re.match("Syllabus.md"))  # uppercase

    # ==================================================================
    # 2. Out-of-Horizon Deliverable Retention Challenges
    # ==================================================================

    def test_out_of_horizon_retention_rules(self):
        """
        Verify deliverables with due dates outside 14-day horizon:
        - Retained 100% in master project roadmap deliverable ledger
        - If materialized as tasks, remain inert: scheduled: null and urgency_tier: 1
        """
        today = date(2026, 9, 22)
        planning_window = 14  # days
        horizon_cutoff = today + timedelta(days=planning_window)  # 2026-10-06

        deliverables = [
            {"id": "d1-near", "title": "Homework 1", "due": "2026-09-29", "status": "todo"},
            {"id": "d2-boundary", "title": "Quiz 1", "due": "2026-10-06", "status": "todo"},
            {"id": "d3-out-15d", "title": "Midterm Exam", "due": "2026-10-07", "status": "todo"},
            {"id": "d4-out-84d", "title": "Final Project", "due": "2026-12-15", "status": "todo"},
        ]

        active_tasks = []
        inert_tasks = []

        for d in deliverables:
            due_date = date.fromisoformat(d["due"])
            if due_date <= horizon_cutoff:
                # In-horizon: active task
                task = {
                    "title": d["title"],
                    "status": d["status"],
                    "due": d["due"],
                    "scheduled": f"{d['due']}T10:00:00-05:00",
                    "urgency_tier": 2,
                    "dateCreated": "2026-09-22T10:00:00-05:00",
                }
                active_tasks.append(task)
            else:
                # Out-of-horizon: MUST remain inert
                task = {
                    "title": d["title"],
                    "status": d["status"],
                    "due": d["due"],
                    "scheduled": None,  # inert
                    "urgency_tier": 1,  # lowest urgency tier
                    "dateCreated": "2026-09-22T10:00:00-05:00",
                }
                inert_tasks.append(task)

        # Assert master ledger contains all 4 deliverables
        self.assertEqual(len(deliverables), 4)

        # Assert 2 near-term tasks and 2 inert out-of-horizon tasks
        self.assertEqual(len(active_tasks), 2)
        self.assertEqual(len(inert_tasks), 2)

        # Assert all inert tasks strictly satisfy scheduled: null and urgency_tier: 1
        for inert in inert_tasks:
            self.assertIsNone(inert["scheduled"], f"Inert task {inert['title']} must have scheduled: null")
            self.assertEqual(inert["urgency_tier"], 1, f"Inert task {inert['title']} must have urgency_tier: 1")

    # ==================================================================
    # 3. Uncertain Date Representation Challenges
    # ==================================================================

    def test_uncertain_date_representation_rfc3339(self):
        """
        Verify that uncertain dates use due: null and date_uncertain: true,
        satisfying RFC 3339 assertions and avoiding invalid date strings.
        """
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")

        # 1. Valid uncertain task
        valid_uncertain_task = {
            "title": "Final Exam (Date TBD by Registrar)",
            "status": "todo",
            "dateCreated": "2026-09-22T10:00:00-05:00",
            "due": None,
            "date_uncertain": True,
            "scheduled": None,
        }
        self.assertIsNone(valid_uncertain_task["due"])
        self.assertTrue(valid_uncertain_task["date_uncertain"])
        self.assertIsNone(valid_uncertain_task["scheduled"])

        # 2. Valid concrete task
        valid_concrete_task = {
            "title": "Homework 1",
            "status": "todo",
            "dateCreated": "2026-09-22T10:00:00-05:00",
            "due": "2026-09-30",
            "date_uncertain": False,
        }
        self.assertIsNotNone(date_pattern.match(valid_concrete_task["due"]))
        self.assertFalse(valid_concrete_task["date_uncertain"])

        # 3. Adversarial invalid date representations that violate RFC 3339
        invalid_due_values = [
            "TBD",
            "mid-November",
            "2026-??-??",
            "Fall 2026",
            "TBD by professor",
            "",
            "2026/09/30",
        ]
        for inv in invalid_due_values:
            with self.subTest(invalid_due=inv):
                self.assertIsNone(date_pattern.match(inv), f"Invalid due string '{inv}' must fail RFC 3339 date match")

        # 4. Invariant assertion: schedulers must never assign hard scheduled timestamp to uncertain task
        def attempt_schedule(task: dict, timestamp: str):
            if task.get("date_uncertain") and task.get("due") is None:
                raise ValueError("Invariant violation: cannot assign hard scheduled timestamp to task with date_uncertain: true and due: null")
            task["scheduled"] = timestamp

        with self.assertRaises(ValueError):
            attempt_schedule(valid_uncertain_task, "2026-09-25T10:00:00-05:00")

    # ==================================================================
    # 4. Multiplier Learning Bounds & Clamping Challenges
    # ==================================================================

    def test_multiplier_learning_extreme_bounds_clamping(self):
        """
        Verify multiplier update formula with extreme inputs:
        - Ratio T_actual / T_estimated = 0.01 (extreme under-run)
        - Ratio T_actual / T_estimated = 100.0 (extreme over-run)
        - Bounds strictly clamped within [0.20, 2.00] under all iterations.
        """
        # Baseline check from System/Memory.md session 20260920-02
        # T_actual = 105, T_estimated = 90, M_curr = 1.00 -> 1.02
        m_step = update_multiplier(current_multiplier=1.00, actual_minutes=105, estimated_minutes=90)
        self.assertEqual(m_step, 1.02, "Standard update must match System/Memory.md Session 20260920-02 (1.02)")

        # Case A: Extreme Over-run (Ratio = 100.0)
        # Single large jump
        m_over = update_multiplier(current_multiplier=1.00, actual_minutes=10000, estimated_minutes=100)
        self.assertEqual(m_over, 2.00, "Extreme over-run must be clamped strictly at 2.00")

        # Starting at upper bound 2.00
        m_over_max = update_multiplier(current_multiplier=2.00, actual_minutes=5000, estimated_minutes=50)
        self.assertEqual(m_over_max, 2.00, "Multiplier at 2.00 with over-run must stay at 2.00")

        # Case B: Extreme Under-run (Ratio = 0.01)
        # Single step from 1.00 -> 1.00 + 0.10 * (0.01 - 1.00) = 0.901 -> 0.90
        m_under = update_multiplier(current_multiplier=1.00, actual_minutes=1, estimated_minutes=100)
        self.assertEqual(m_under, 0.90)

        # Repeated 50 times with ratio 0.01 to test asymptotic lower clamp
        m_iter = 1.00
        for _ in range(50):
            m_iter = update_multiplier(current_multiplier=m_iter, actual_minutes=1, estimated_minutes=100)
            self.assertTrue(0.20 <= m_iter <= 2.00, f"Multiplier {m_iter} broke bounds during under-run")

        self.assertEqual(m_iter, 0.20, "Asymptotic under-run must be clamped strictly at 0.20")

        # Starting at lower bound 0.20
        m_under_min = update_multiplier(current_multiplier=0.20, actual_minutes=0.01, estimated_minutes=100)
        self.assertEqual(m_under_min, 0.20, "Multiplier at 0.20 with under-run must stay at 0.20")

        # Case C: Zero or negative inputs
        # Zero estimated minutes must not raise ZeroDivisionError
        m_zero_est = update_multiplier(current_multiplier=1.00, actual_minutes=60, estimated_minutes=0)
        self.assertEqual(m_zero_est, 1.00)

        # Zero actual minutes (task cancelled immediately)
        m_zero_act = update_multiplier(current_multiplier=1.00, actual_minutes=0, estimated_minutes=60)
        self.assertEqual(m_zero_act, 0.90)

    # ==================================================================
    # 5. Cryptographic Deduplication & SHA-256 Collision Challenges
    # ==================================================================

    def test_cryptographic_deduplication_and_provenance(self):
        """
        Verify SHA-256 hash collision resistance, 64-char lowercase hex formatting,
        and identical document duplicate detection.
        """
        sha256_re = re.compile(r"^[a-f0-9]{64}$")

        synthetic_syllabus_v1 = (
            b"# CS 410 Course Syllabus - Fall 2026\n"
            b"Instructor: Prof. Ada Lovelace\n"
            b"Deliverables:\n"
            b"- HW1: Due 2026-09-30\n"
            b"- Midterm: Due 2026-10-15\n"
        )

        # Duplicate payload (exact same bytes)
        synthetic_syllabus_duplicate = (
            b"# CS 410 Course Syllabus - Fall 2026\n"
            b"Instructor: Prof. Ada Lovelace\n"
            b"Deliverables:\n"
            b"- HW1: Due 2026-09-30\n"
            b"- Midterm: Due 2026-10-15\n"
        )

        # Subtle modification: 1 whitespace character difference
        synthetic_syllabus_modified = (
            b"# CS 410 Course Syllabus - Fall 2026\n"
            b"Instructor: Prof. Ada Lovelace\n"
            b"Deliverables:\n"
            b"- HW1: Due 2026-09-30\n"
            b"- Midterm: Due 2026-10-16\n"  # 15 -> 16
        )

        h1 = hashlib.sha256(synthetic_syllabus_v1).hexdigest()
        h_dup = hashlib.sha256(synthetic_syllabus_duplicate).hexdigest()
        h_mod = hashlib.sha256(synthetic_syllabus_modified).hexdigest()

        # Assert format matches regex ^[a-f0-9]{64}$
        self.assertTrue(sha256_re.match(h1))
        self.assertTrue(sha256_re.match(h_dup))
        self.assertTrue(sha256_re.match(h_mod))

        # Assert identical document matches hash (deduplication trigger)
        self.assertEqual(h1, h_dup, "Duplicate submission must yield exact identical SHA-256 digest")

        # Assert modification changes hash (avalanche effect)
        self.assertNotEqual(h1, h_mod, "Modified document must yield different SHA-256 digest")

        # Mock database of existing sources
        existing_sources = {
            h1: "Sources/cs410-syllabus-v1.md"
        }

        # Query simulation for ingestion
        def ingest_source_check(doc_bytes: bytes):
            digest = hashlib.sha256(doc_bytes).hexdigest()
            if digest in existing_sources:
                return {"status": "duplicate_source_detected", "source_ref": f"[[{existing_sources[digest]}]]"}
            return {"status": "accepted", "sha256": digest}

        res_dup = ingest_source_check(synthetic_syllabus_duplicate)
        self.assertEqual(res_dup["status"], "duplicate_source_detected")
        self.assertEqual(res_dup["source_ref"], "[[Sources/cs410-syllabus-v1.md]]")

        res_new = ingest_source_check(synthetic_syllabus_modified)
        self.assertEqual(res_new["status"], "accepted")
        self.assertEqual(res_new["sha256"], h_mod)

    # ==================================================================
    # 6. Frontmatter Schema Negative & Conformance Challenges
    # ==================================================================

    def test_schema_modality_and_energy_defaults(self):
        """Verify cognitive modality configurations in System/Memory.md adhere to specifications."""
        modalities = self.memory_fm.get("cognitive_modality_defaults", {})
        expected_modalities = {
            "analytical": {"baseline_minutes": 90, "energy_level": "high", "target_window": "peak_sprint_1"},
            "synthesis": {"baseline_minutes": 75, "energy_level": "medium", "target_window": "recovery"},
            "kinetic": {"baseline_minutes": 45, "energy_level": "medium", "target_window": "defrost"},
            "administrative": {"baseline_minutes": 30, "energy_level": "low", "target_window": "slump"},
        }

        for mod, expected in expected_modalities.items():
            self.assertIn(mod, modalities)
            cfg = modalities[mod]
            self.assertEqual(cfg.get("baseline_minutes"), expected["baseline_minutes"])
            self.assertEqual(cfg.get("energy_level"), expected["energy_level"])
            self.assertEqual(cfg.get("target_window"), expected["target_window"])
            self.assertTrue(0.20 <= cfg.get("multiplier", 1.0) <= 2.00)

    # ==================================================================
    # 7. Deep Schema Validation & Negative Property Rejection
    # ==================================================================

    def test_schema_conformance_and_negative_cases(self):
        """Extract all 4 type schemas from contract and test negative schema violations."""
        schemas = {}
        for match in re.finditer(r"```yaml\s*\n---\n(.*?)\n---", self.collection_content, re.DOTALL):
            d = yaml.safe_load(match.group(1))
            if d and d.get("kind") == "mdbase.type":
                schemas[d["name"]] = d["schema"]["value"]

        self.assertIn("task", schemas)
        self.assertIn("project", schemas)
        self.assertIn("zettel", schemas)
        self.assertIn("source", schemas)

        def validate_dict(data: dict, schema: dict, path: str = "root") -> list[str]:
            errors = []
            # Check required
            for req in schema.get("required", []):
                if req not in data:
                    errors.append(f"{path}: missing required property '{req}'")

            # Check additionalProperties
            if schema.get("additionalProperties") is False:
                allowed = set(schema.get("properties", {}).keys())
                for k in data.keys():
                    if k not in allowed:
                        errors.append(f"{path}: unexpected additional property '{k}'")

            props = schema.get("properties", {})
            for k, val in data.items():
                if k not in props:
                    continue
                p_schema = props[k]
                p_type = p_schema.get("type")

                # Handle type: [string, "null"]
                if isinstance(p_type, list):
                    if val is None:
                        if "null" not in p_type:
                            errors.append(f"{path}.{k}: null not allowed")
                        continue
                    if "string" in p_type and not isinstance(val, str):
                        errors.append(f"{path}.{k}: expected string, got {type(val).__name__}")
                        continue

                if isinstance(val, str):
                    if "minLength" in p_schema and len(val) < p_schema["minLength"]:
                        errors.append(f"{path}.{k}: string shorter than minLength {p_schema['minLength']}")
                    if "pattern" in p_schema and not re.search(p_schema["pattern"], val):
                        errors.append(f"{path}.{k}: string does not match pattern {p_schema['pattern']}")
                    if p_schema.get("format") == "date" and not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
                        errors.append(f"{path}.{k}: invalid date format")
                    if p_schema.get("format") == "date-time" and not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}([+-]\d{2}:\d{2}|Z)$", val):
                        errors.append(f"{path}.{k}: invalid date-time format")
                    if "enum" in p_schema and val not in p_schema["enum"]:
                        errors.append(f"{path}.{k}: value '{val}' not in enum {p_schema['enum']}")
                elif p_type == "integer":
                    if not isinstance(val, int) or isinstance(val, bool):
                        errors.append(f"{path}.{k}: expected integer, got {type(val).__name__}")
                        continue
                    if "minimum" in p_schema and val < p_schema["minimum"]:
                        errors.append(f"{path}.{k}: integer {val} below minimum {p_schema['minimum']}")
                    if "maximum" in p_schema and val > p_schema["maximum"]:
                        errors.append(f"{path}.{k}: integer {val} above maximum {p_schema['maximum']}")
                elif p_type == "boolean":
                    if not isinstance(val, bool):
                        errors.append(f"{path}.{k}: expected boolean, got {type(val).__name__}")
                elif p_type == "array":
                    if not isinstance(val, list):
                        errors.append(f"{path}.{k}: expected array, got {type(val).__name__}")
                        continue
                    if "minItems" in p_schema and len(val) < p_schema["minItems"]:
                        errors.append(f"{path}.{k}: array has {len(val)} items, minimum is {p_schema['minItems']}")
                    if "items" in p_schema and p_schema["items"].get("type") == "object":
                        item_schema = p_schema["items"]
                        for idx, item in enumerate(val):
                            errors.extend(validate_dict(item, item_schema, f"{path}.{k}[{idx}]"))

            return errors

        # 1. Task Model Validation
        # Valid task
        valid_task = {
            "title": "Complete Homework 1",
            "status": "todo",
            "dateCreated": "2026-09-22T10:00:00-05:00",
            "due": "2026-09-30",
            "urgency_tier": 2,
            "modality": "analytical",
            "timeEstimate": 90,
            "energy": "high",
            "friction": "medium",
            "tags": ["cs410", "homework"],
        }
        self.assertEqual(validate_dict(valid_task, schemas["task"]), [])

        # Negative Task A: additionalProperties injection
        bad_task_injection = dict(valid_task, malicious_override="rm -rf /")
        errs = validate_dict(bad_task_injection, schemas["task"])
        self.assertTrue(any("unexpected additional property 'malicious_override'" in e for e in errs))

        # Negative Task B: Invalid due format
        bad_task_due = dict(valid_task, due="TBD")
        errs = validate_dict(bad_task_due, schemas["task"])
        self.assertTrue(any("invalid date format" in e for e in errs))

        # Negative Task C: Out-of-bounds urgency_tier
        bad_task_tier = dict(valid_task, urgency_tier=5)
        errs = validate_dict(bad_task_tier, schemas["task"])
        self.assertTrue(any("above maximum 4" in e for e in errs))

        # Negative Task D: Missing required dateCreated
        bad_task_req = {k: v for k, v in valid_task.items() if k != "dateCreated"}
        errs = validate_dict(bad_task_req, schemas["task"])
        self.assertTrue(any("missing required property 'dateCreated'" in e for e in errs))

        # 2. Project Roadmap Validation
        valid_project = {
            "project_id": "cs410-fall2026",
            "title": "CS 410: Advanced Knowledge Systems",
            "status": "active",
            "pillar": "academics",
            "last_updated": "2026-09-22T10:00:00-05:00",
            "deliverables": [
                {"id": "hw1", "title": "Homework 1", "due": "2026-09-30", "status": "todo", "tier": 2},
                {"id": "final-exam", "title": "Final Exam", "due": None, "date_uncertain": True, "status": "todo", "tier": 1},
            ],
        }
        self.assertEqual(validate_dict(valid_project, schemas["project"]), [])

        # Negative Project A: invalid project_id pattern
        bad_proj_id = dict(valid_project, project_id="CS 410 Fall")
        errs = validate_dict(bad_proj_id, schemas["project"])
        self.assertTrue(any("project_id: string does not match pattern" in e for e in errs))

        # 3. Zettel Validation
        valid_zettel = {
            "id": "20260922100000-bayesian-inference",
            "title": "Bayesian Inference in Cognitive Architectures",
            "dateCreated": "2026-09-22T10:00:00-05:00",
            "tags": ["zettel", "bayesian", "ai"],
        }
        self.assertEqual(validate_dict(valid_zettel, schemas["zettel"]), [])

        # Negative Zettel A: empty tags (violating minItems: 1)
        bad_zettel_tags = dict(valid_zettel, tags=[])
        errs = validate_dict(bad_zettel_tags, schemas["zettel"])
        self.assertTrue(any("tags: array has 0 items, minimum is 1" in e for e in errs))

        # 4. Source Validation
        valid_source = {
            "id": "cs410-syllabus",
            "title": "CS 410 Syllabus",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "captured_date": "2026-09-22T10:00:00-05:00",
            "source_type": "syllabus",
            "ingestion_status": "raw",
        }
        self.assertEqual(validate_dict(valid_source, schemas["source"]), [])

        # Negative Source A: invalid sha256 pattern (63 characters)
        bad_source_sha = dict(valid_source, sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b85")
        errs = validate_dict(bad_source_sha, schemas["source"])
        self.assertTrue(any("sha256: string does not match pattern" in e for e in errs))

    # ==================================================================
    # 8. Wikilink Syntax and Relationship Traversal Matrix
    # ==================================================================

    def test_wikilink_relationship_matrix_integrity(self):
        """
        Verify all 12 wikilink relationships defined in Section 5.1 Table 5.1:
        - Target syntax format
        - Rejection of escaping wikilinks in Markdown content
        """
        wikilink_re = re.compile(r"\[\[([^\]]+)\]\]")

        sample_markdown = (
            "# Task Note\n"
            "Parent Project: [[Projects/cs410/Roadmap]]\n"
            "Linked Notes:\n"
            "- [[20260922100000-bayesian-inference]]\n"
            "- [[20260922100500-ultradian-sprints]]\n"
            "Source Reference: [[Sources/cs410-syllabus]]\n"
            "Attempted Root Escape: [[../outside_secret]]\n"
            "Attempted Root Escape 2: [[../../etc/passwd]]\n"
        )

        all_links = wikilink_re.findall(sample_markdown)
        self.assertEqual(len(all_links), 6)

        valid_targets = []
        rejected_targets = []

        for link in all_links:
            try:
                res = resolve_and_validate_path(link)
                valid_targets.append(res)
            except ValueError:
                rejected_targets.append(link)

        self.assertEqual(len(valid_targets), 4)
        self.assertEqual(len(rejected_targets), 2)
        self.assertIn("../outside_secret", rejected_targets)
        self.assertIn("../../etc/passwd", rejected_targets)


if __name__ == "__main__":
    unittest.main()

