"""
Unit tests for Chrysalis Single-Folder Substrate Migration (migrate_to_subfolder.py)
==================================================================================
Validates:
1. Dry-run mode does not mutate any disk files.
2. Full execution moves all components into TaskNotes/ subfolder:
   - Tasks, Archive, Views, System/Workflows, Templates
   - System, Projects, Slipbox, _types, Dashboard.md
   - Daily focus notes (YYYY-MM-DD*.md) -> TaskNotes/Daily/
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
        (self.vault_root / "TaskNotes" / "Workflows" / "01-capture.md").write_text("---\ntype: agent_workflow\nid: workflow-01-capture\n---\n# Capture", encoding="utf-8")
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
        folder_name = "TaskNotes"
        create_directory_structure(self.vault_root, folder_name, dry_run=True)
        migrate_substrates(self.vault_root, folder_name, dry_run=True)
        update_obsidian_configs(self.vault_root, folder_name, dry_run=True)
        update_dashboard_queries(self.vault_root, folder_name, dry_run=True)

        # Verify nothing moved
        self.assertTrue((self.vault_root / "TaskNotes" / "Tasks" / "sample-task.md").exists())
        self.assertTrue((self.vault_root / "System" / "Scheduling-Memory.md").exists())
        self.assertTrue((self.vault_root / "Dashboard.md").exists())
        self.assertTrue((self.vault_root / "2026-09-02.md").exists())
        self.assertFalse((self.vault_root / "TaskNotes" / "System" / "Scheduling-Memory.md").exists())

    def test_execute_migrates_all_components(self):
        folder_name = "TaskNotes"
        create_directory_structure(self.vault_root, folder_name, dry_run=False)
        migrate_substrates(self.vault_root, folder_name, dry_run=False)
        setup_backward_compatibility(self.vault_root, folder_name, dry_run=False)
        deploy_root_trampolines(self.vault_root, folder_name, dry_run=False)
        update_obsidian_configs(self.vault_root, folder_name, dry_run=False)
        update_dashboard_queries(self.vault_root, folder_name, dry_run=False)

        # 1. Verify files moved into TaskNotes/
        tasknotes_base = self.vault_root / "TaskNotes"
        self.assertTrue((tasknotes_base / "Tasks" / "sample-task.md").exists())
        self.assertTrue((tasknotes_base / "Views" / "tasks-default.base").exists())
        self.assertTrue((tasknotes_base / "System" / "Workflows" / "01-capture.md").exists())
        self.assertTrue((tasknotes_base / "_templates" / "Task-Template.md").exists())
        self.assertTrue((tasknotes_base / "System" / "Scheduling-Memory.md").exists())
        self.assertTrue((tasknotes_base / "Projects" / "ProjA" / "Roadmap.md").exists())
        self.assertTrue((tasknotes_base / "Slipbox" / "20260901-test.md").exists())
        self.assertTrue((tasknotes_base / "_types" / "task.md").exists())
        self.assertTrue((tasknotes_base / "Dashboard.md").exists())
        self.assertTrue((tasknotes_base / "Daily" / "2026-09-02.md").exists())

        # 2. Verify root daily note was moved out of root
        self.assertFalse((self.vault_root / "2026-09-02.md").exists())

        # 3. Verify root IDE trampoline
        skills_json = self.vault_root / ".agent" / "skills.json"
        self.assertTrue(skills_json.exists())
        skills_data = json.loads(skills_json.read_text(encoding="utf-8"))
        self.assertEqual(skills_data["entries"][0]["path"], "TaskNotes/.agent/skills")

        # 4. Verify root AGENTS.md trampoline
        root_agents = self.vault_root / "AGENTS.md"
        self.assertTrue(root_agents.exists())
        self.assertIn("TaskNotes/AGENTS.md", root_agents.read_text(encoding="utf-8"))

        # 5. Verify Obsidian TaskNotes config
        tn_cfg = json.loads(
            (self.vault_root / ".obsidian" / "plugins" / "tasknotes" / "data.json").read_text(encoding="utf-8")
        )
        self.assertEqual(tn_cfg["rootFolder"], "TaskNotes")
        self.assertEqual(tn_cfg["tasksFolder"], "TaskNotes/Tasks")
        self.assertEqual(tn_cfg["archiveFolder"], "TaskNotes/Archive")
        self.assertEqual(tn_cfg["commandFileMapping"]["open-tasks-view"], "TaskNotes/Views/tasks-default.base")

        # 6. Verify Daily Notes config
        daily_cfg = json.loads((self.vault_root / ".obsidian" / "daily-notes.json").read_text(encoding="utf-8"))
        self.assertEqual(daily_cfg["folder"], "TaskNotes/Daily")

        # 7. Folder migration must preserve the user-selected model
        nexus_cfg = json.loads(
            (self.vault_root / ".obsidian" / "plugins" / "nexus" / "data.json").read_text(encoding="utf-8")
        )
        self.assertEqual(nexus_cfg["models"]["defaultModel"]["model"], "gemini-3.7-flash")
        self.assertEqual(nexus_cfg["models"]["agentModel"]["model"], "gemini-3.7-flash")

        # 8. Verify Dashboard Dataview queries
        dash_content = (tasknotes_base / "Dashboard.md").read_text(encoding="utf-8")
        self.assertIn('FROM "TaskNotes/Tasks"', dash_content)
        self.assertIn('FROM "TaskNotes/Projects"', dash_content)

    def test_duplicate_agent_workflow_in_tasknotes_and_system_does_not_conflict(self):
        """When both legacy TaskNotes/Workflows/01-capture.md and System/Workflows/01-capture.md exist, migration deduplicates cleanly and keeps TaskNotes/Workflows plugin notes in place."""
        (self.vault_root / "System" / "Workflows").mkdir(parents=True, exist_ok=True)
        (self.vault_root / "System/Workflows/01-capture.md").write_bytes(
            (self.vault_root / "TaskNotes/Workflows/01-capture.md").read_bytes()
        )
        (self.vault_root / "TaskNotes" / "Workflows" / "plugin-wf.md").write_text(
            "workflow: plugin",
            encoding="utf-8",
        )
        (self.vault_root / "TaskNotes" / "Archive" / "archived-task.md").write_text(
            "---\ntitle: Archived Task\nstatus: archived\n---",
            encoding="utf-8",
        )
        (self.vault_root / ".agent" / "skills" / "task").mkdir(parents=True, exist_ok=True)
        (self.vault_root / ".agent" / "skills" / "task" / "SKILL.md").write_text(
            "---\nname: task\ndescription: Task skill\n---",
            encoding="utf-8",
        )
        (self.vault_root / "TaskNotes" / "Views" / "workflows.base").write_text(
            'filters:\n  and:\n    - file.inFolder("TaskNotes/Workflows")\n',
            encoding="utf-8",
        )
        folder_name = "TaskNotes"
        create_directory_structure(self.vault_root, folder_name, dry_run=False)
        migrate_substrates(self.vault_root, folder_name, dry_run=False)
        update_dashboard_queries(self.vault_root, folder_name, dry_run=False)

        tasknotes_base = self.vault_root / "TaskNotes"
        self.assertTrue((tasknotes_base / "System" / "Workflows" / "01-capture.md").exists())
        self.assertIn("# Capture", (tasknotes_base / "System" / "Workflows" / "01-capture.md").read_text(encoding="utf-8"))
        self.assertTrue((self.vault_root / "TaskNotes" / "Workflows" / "plugin-wf.md").exists())
        self.assertTrue((tasknotes_base / "Archive" / "archived-task.md").exists())
        self.assertTrue((tasknotes_base / ".agent" / "skills" / "task" / "SKILL.md").exists())
        wf_base_text = (tasknotes_base / "Views" / "workflows.base").read_text(encoding="utf-8")
        self.assertIn('file.inFolder("TaskNotes/Workflows")', wf_base_text)

    def test_backward_compatibility_skips_self_alias_when_target_is_tasknotes(self):
        """When folder_name is TaskNotes, setup_backward_compatibility must never create a self-referential symlink TaskNotes -> TaskNotes even if TaskNotes does not exist yet."""
        shutil.rmtree(self.vault_root / "TaskNotes")
        setup_backward_compatibility(self.vault_root, "TaskNotes", dry_run=False)
        self.assertFalse((self.vault_root / "TaskNotes").is_symlink())


if __name__ == "__main__":
    unittest.main()
