"""
Unit tests for Chrysalis Single-Folder Substrate Migration (migrate_to_subfolder.py)
==================================================================================
Validates:
1. Dry-run mode does not mutate any disk files.
2. Full execution moves all components into chrysalis/ subfolder:
   - Tasks, Archive, Views, Workflows, Templates
   - System, Projects, Slipbox, _types, Dashboard.md
   - Daily focus notes (YYYY-MM-DD*.md) -> chrysalis/Daily/
3. Establishes backward compatibility junction/symlink for TaskNotes.
4. Deploys root IDE trampolines (.agent/skills.json) and root AGENTS.md.
5. Updates Obsidian plugin data.json and daily-notes.json.
6. Updates Dashboard.md Dataview queries.
"""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from System.scripts.migrate_to_subfolder import (
    create_directory_structure,
    deploy_root_trampolines,
    migrate_substrates,
    setup_backward_compatibility,
    update_dashboard_queries,
    update_obsidian_configs,
)


class TestMigrateToSubfolder(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.vault_root = Path(self.temp_dir.name)

        # Build mock legacy vault layout
        (self.vault_root / "TaskNotes" / "Tasks").mkdir(parents=True, exist_ok=True)
        (self.vault_root / "TaskNotes" / "Archive").mkdir(parents=True, exist_ok=True)
        (self.vault_root / "TaskNotes" / "Views").mkdir(parents=True, exist_ok=True)
        (self.vault_root / "TaskNotes" / "Workflows").mkdir(parents=True, exist_ok=True)
        (self.vault_root / "TaskNotes" / "_templates").mkdir(parents=True, exist_ok=True)
        (self.vault_root / "System" / "_templates").mkdir(parents=True, exist_ok=True)
        (self.vault_root / "Projects" / "ProjA").mkdir(parents=True, exist_ok=True)
        (self.vault_root / "Slipbox").mkdir(parents=True, exist_ok=True)
        (self.vault_root / "_types").mkdir(parents=True, exist_ok=True)
        (self.vault_root / ".obsidian" / "plugins" / "tasknotes").mkdir(parents=True, exist_ok=True)
        (self.vault_root / ".obsidian" / "plugins" / "nexus").mkdir(parents=True, exist_ok=True)

        # Seed sample files
        (self.vault_root / "TaskNotes" / "Tasks" / "sample-task.md").write_text("---\ntitle: Sample Task\nstatus: todo\n---", encoding="utf-8")
        (self.vault_root / "TaskNotes" / "Views" / "tasks-default.base").write_text("view: tasks", encoding="utf-8")
        (self.vault_root / "TaskNotes" / "Workflows" / "test-wf.md").write_text("workflow: test", encoding="utf-8")
        (self.vault_root / "TaskNotes" / "_templates" / "Task-Template.md").write_text("template: task", encoding="utf-8")
        (self.vault_root / "System" / "Scheduling-Memory.md").write_text("timezone: -05:00", encoding="utf-8")
        (self.vault_root / "Projects" / "ProjA" / "Roadmap.md").write_text("# ProjA Roadmap", encoding="utf-8")
        (self.vault_root / "Slipbox" / "20260901-test.md").write_text("# Zettel Test", encoding="utf-8")
        (self.vault_root / "_types" / "task.md").write_text("# Type definition", encoding="utf-8")
        (self.vault_root / "Dashboard.md").write_text('FROM "TaskNotes/Tasks"\nFROM "Projects"', encoding="utf-8")
        (self.vault_root / "2026-09-02.md").write_text("# Daily Note", encoding="utf-8")

        # Seed plugin configs
        tasknotes_config = {
            "tasksFolder": "TaskNotes/Tasks",
            "archiveFolder": "TaskNotes/Archive",
            "inlineTaskConvertFolder": "TaskNotes/Tasks",
            "commandFileMapping": {
                "open-tasks-view": "TaskNotes/Views/tasks-default.base"
            }
        }
        (self.vault_root / ".obsidian" / "plugins" / "tasknotes" / "data.json").write_text(
            json.dumps(tasknotes_config), encoding="utf-8"
        )
        nexus_config = {
            "models": {
                "defaultModel": {"provider": "google", "model": "gemini-3.7-flash"},
                "agentModel": {"provider": "google", "model": "gemini-3.7-flash"}
            }
        }
        (self.vault_root / ".obsidian" / "plugins" / "nexus" / "data.json").write_text(
            json.dumps(nexus_config), encoding="utf-8"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_dry_run_leaves_files_untouched(self):
        folder_name = "chrysalis"
        create_directory_structure(self.vault_root, folder_name, dry_run=True)
        migrate_substrates(self.vault_root, folder_name, dry_run=True)
        update_obsidian_configs(self.vault_root, folder_name, dry_run=True)
        update_dashboard_queries(self.vault_root, folder_name, dry_run=True)

        # Verify nothing moved
        self.assertTrue((self.vault_root / "TaskNotes" / "Tasks" / "sample-task.md").exists())
        self.assertTrue((self.vault_root / "System" / "Scheduling-Memory.md").exists())
        self.assertTrue((self.vault_root / "Dashboard.md").exists())
        self.assertTrue((self.vault_root / "2026-09-02.md").exists())
        self.assertFalse((self.vault_root / "chrysalis" / "Tasks" / "sample-task.md").exists())

    def test_execute_migrates_all_components(self):
        folder_name = "chrysalis"
        create_directory_structure(self.vault_root, folder_name, dry_run=False)
        migrate_substrates(self.vault_root, folder_name, dry_run=False)
        setup_backward_compatibility(self.vault_root, folder_name, dry_run=False)
        deploy_root_trampolines(self.vault_root, folder_name, dry_run=False)
        update_obsidian_configs(self.vault_root, folder_name, dry_run=False)
        update_dashboard_queries(self.vault_root, folder_name, dry_run=False)

        # 1. Verify files moved into chrysalis/
        chrysalis_base = self.vault_root / "chrysalis"
        self.assertTrue((chrysalis_base / "Tasks" / "sample-task.md").exists())
        self.assertTrue((chrysalis_base / "Views" / "tasks-default.base").exists())
        self.assertTrue((chrysalis_base / "Workflows" / "test-wf.md").exists())
        self.assertTrue((chrysalis_base / "_templates" / "Task-Template.md").exists())
        self.assertTrue((chrysalis_base / "System" / "Scheduling-Memory.md").exists())
        self.assertTrue((chrysalis_base / "Projects" / "ProjA" / "Roadmap.md").exists())
        self.assertTrue((chrysalis_base / "Slipbox" / "20260901-test.md").exists())
        self.assertTrue((chrysalis_base / "_types" / "task.md").exists())
        self.assertTrue((chrysalis_base / "Dashboard.md").exists())
        self.assertTrue((chrysalis_base / "Daily" / "2026-09-02.md").exists())

        # 2. Verify root daily note was moved out of root
        self.assertFalse((self.vault_root / "2026-09-02.md").exists())

        # 3. Verify root IDE trampoline
        skills_json = self.vault_root / ".agent" / "skills.json"
        self.assertTrue(skills_json.exists())
        skills_data = json.loads(skills_json.read_text(encoding="utf-8"))
        self.assertEqual(skills_data["entries"][0]["path"], "chrysalis/.agent/skills")

        # 4. Verify root AGENTS.md trampoline
        root_agents = self.vault_root / "AGENTS.md"
        self.assertTrue(root_agents.exists())
        self.assertIn("chrysalis/AGENTS.md", root_agents.read_text(encoding="utf-8"))

        # 5. Verify Obsidian TaskNotes config
        tn_cfg = json.loads(
            (self.vault_root / ".obsidian" / "plugins" / "tasknotes" / "data.json").read_text(encoding="utf-8")
        )
        self.assertEqual(tn_cfg["rootFolder"], "chrysalis")
        self.assertEqual(tn_cfg["tasksFolder"], "chrysalis/Tasks")
        self.assertEqual(tn_cfg["archiveFolder"], "chrysalis/Archive")
        self.assertEqual(tn_cfg["commandFileMapping"]["open-tasks-view"], "chrysalis/Views/tasks-default.base")

        # 6. Verify Daily Notes config
        daily_cfg = json.loads((self.vault_root / ".obsidian" / "daily-notes.json").read_text(encoding="utf-8"))
        self.assertEqual(daily_cfg["folder"], "chrysalis/Daily")

        # 7. Folder migration must preserve the user-selected model
        nexus_cfg = json.loads(
            (self.vault_root / ".obsidian" / "plugins" / "nexus" / "data.json").read_text(encoding="utf-8")
        )
        self.assertEqual(nexus_cfg["models"]["defaultModel"]["model"], "gemini-3.7-flash")
        self.assertEqual(nexus_cfg["models"]["agentModel"]["model"], "gemini-3.7-flash")

        # 8. Verify Dashboard Dataview queries
        dash_content = (chrysalis_base / "Dashboard.md").read_text(encoding="utf-8")
        self.assertIn('FROM "chrysalis/Tasks"', dash_content)
        self.assertIn('FROM "chrysalis/Projects"', dash_content)


if __name__ == "__main__":
    unittest.main()
