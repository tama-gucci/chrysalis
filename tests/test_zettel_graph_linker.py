"""
Unit tests for Chrysalis Autonomous Zettelkasten Hypergraph Linker (zettel_graph_linker.py)
========================================================================================
Validates bidirectional graph linking:
1. Slipbox Zettels -> Projects Section 3
2. Slipbox Zettels -> TaskNotes linked_zettels frontmatter
3. Idempotency across repeated executions
"""

import tempfile
import unittest
from pathlib import Path

from System.scripts.zettel_graph_linker import (
    ZettelGraphLinker,
    extract_wikilinks,
    normalize_tag,
    parse_frontmatter,
)


class TestZettelGraphLinker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_root = Path(self.temp_dir.name)

        # Create vault directories
        self.slipbox_dir = self.vault_root / "Slipbox"
        self.projects_dir = self.vault_root / "Projects" / "Project_Omega"
        self.tasks_dir = self.vault_root / "chrysalis" / "Tasks"

        self.slipbox_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_parse_frontmatter_and_wikilinks(self):
        content = """---
id: "20260901120000"
title: "Ultradian Rhythm Dynamics"
tags:
  - zettel
  - neuroscience/biology
---
# Ultradian Rhythm Dynamics
Body mentions [[20260815100000-deep-work]] and [[Projects/Project_Omega/Roadmap]].
"""
        fm, body = parse_frontmatter(content)
        self.assertEqual(fm.get("id"), "20260901120000")
        self.assertEqual(fm.get("title"), "Ultradian Rhythm Dynamics")
        self.assertIn("neuroscience/biology", fm.get("tags", []))

        links = extract_wikilinks(body)
        self.assertEqual(len(links), 2)
        self.assertIn("20260815100000-deep-work", links)
        self.assertIn("Projects/Project_Omega/Roadmap", links)

    def test_normalize_tag(self):
        self.assertEqual(normalize_tag("#Pillar-1/Mobile"), "pillar-1/mobile")
        self.assertEqual(normalize_tag("  #Chrysalis  "), "chrysalis")
        self.assertEqual(normalize_tag("architecture"), "architecture")

    def test_hypergraph_linking_dry_run_and_sync(self):
        # 1. Create a Slipbox Zettel note
        zettel_file = self.slipbox_dir / "20260901120000-ultradian-rhythms.md"
        zettel_file.write_text(
            """---
id: "20260901120000"
title: "Ultradian Rhythm Biology"
tags:
  - zettel
  - pillar-1/mobile
  - architecture
---
# Ultradian Rhythm Biology
Reference to [[Projects/Project_Omega/Roadmap]].
""",
            encoding="utf-8",
        )

        # 2. Create a Project Roadmap
        roadmap_file = self.projects_dir / "Roadmap.md"
        roadmap_file.write_text(
            """---
type: project_roadmap
project_id: "project-omega"
title: "Project Omega Architecture"
pillar: "pillar-1"
status: "active"
tags:
  - pillar-1/mobile
---
# Project Omega Architecture

## 1. Project Objective & Scope
Build core system features.

---

## 2. Deliverables & Milestone Breakdown
- [ ] Implement engine (#pillar-1/mobile)

---

## 3. Reference Files & Contacts
- [[Existing-Doc]]
""",
            encoding="utf-8",
        )

        # 3. Create a Task Note
        task_file = self.tasks_dir / "task-implement-engine.md"
        task_file.write_text(
            """---
title: "Implement Engine Core"
status: todo
dateCreated: "2026-09-01T10:00:00-05:00"
created: "2026-09-01T10:00:00-05:00"
due: "2026-09-07"
scheduled: null
priority: high
urgency_tier: 3
modality: analytical
timeEstimate: 75
energy: high
friction: medium
micro_chunked: false
tags:
  - task
  - pillar-1/mobile
linked_zettels: []
project_ref: "[[Projects/Project_Omega/Roadmap]]"
googleCalendarEventId: null
---
# Implement Engine Core
""",
            encoding="utf-8",
        )

        linker = ZettelGraphLinker(vault_root=self.vault_root)

        # Test Dry Run: should detect updates but not modify files
        dry_result = linker.link_hypergraph(dry_run=True)
        self.assertEqual(dry_result["zettels_scanned"], 1)
        self.assertEqual(dry_result["projects_scanned"], 1)
        self.assertEqual(dry_result["tasks_scanned"], 1)
        self.assertEqual(dry_result["projects_updated"], 1)
        self.assertEqual(dry_result["tasks_updated"], 1)

        # Confirm file unchanged in dry run
        roadmap_content_dry = roadmap_file.read_text(encoding="utf-8")
        self.assertNotIn("20260901120000-ultradian-rhythms", roadmap_content_dry)

        # Test Sync: should execute physical mutations
        sync_result = linker.link_hypergraph(dry_run=False)
        self.assertEqual(sync_result["projects_updated"], 1)
        self.assertEqual(sync_result["tasks_updated"], 1)

        # Confirm Project Section 3 has new wikilink
        roadmap_content = roadmap_file.read_text(encoding="utf-8")
        self.assertIn("[[20260901120000-ultradian-rhythms]]", roadmap_content)

        # Confirm Task has linked_zettels populated in frontmatter
        task_content = task_file.read_text(encoding="utf-8")
        self.assertIn('[[20260901120000-ultradian-rhythms]]', task_content)

        # Test Idempotency: running a second time should detect 0 new updates
        second_result = linker.link_hypergraph(dry_run=False)
        self.assertEqual(second_result["projects_updated"], 0)
        self.assertEqual(second_result["tasks_updated"], 0)

    def test_legacy_tasknotes_fallback(self):
        # Remove chrysalis/Tasks and create TaskNotes/Tasks
        import shutil
        shutil.rmtree(self.tasks_dir)
        legacy_dir = self.vault_root / "TaskNotes" / "Tasks"
        legacy_dir.mkdir(parents=True, exist_ok=True)

        task_file = legacy_dir / "legacy-task.md"
        task_file.write_text(
            """---
title: "Legacy Task"
status: todo
tags:
  - task
  - pillar-1/mobile
linked_zettels: []
---
# Legacy Task
""",
            encoding="utf-8",
        )

        zettel_file = self.slipbox_dir / "20260901120000-ultradian-rhythms.md"
        zettel_file.write_text(
            """---
id: "20260901120000"
title: "Ultradian Rhythm Dynamics"
tags:
  - zettel
  - pillar-1/mobile
---
# Ultradian Rhythm Dynamics
""",
            encoding="utf-8",
        )

        linker = ZettelGraphLinker(vault_root=self.vault_root)
        sync_result = linker.link_hypergraph(dry_run=False)
        self.assertEqual(sync_result["tasks_updated"], 1)

        task_content = task_file.read_text(encoding="utf-8")
        self.assertIn("[[20260901120000-ultradian-rhythms]]", task_content)


if __name__ == "__main__":
    unittest.main()
