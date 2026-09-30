import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update
from System.scripts.vault_paths import resolve_vault_root, vault_path


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.source = self.root / 'source'
        self.target = self.root / 'runtime'
        self.source.mkdir()
        self.target.mkdir()
        (self.source / 'README.md').write_text('new')
        (self.target / 'README.md').write_text('old')

    def tearDown(self):
        self.temporary.cleanup()

    def test_preview_does_not_write(self):
        count, files = update.sync_engine(self.source, self.target, dry_run=True)
        self.assertEqual(files, ['README.md'])
        self.assertEqual(count, 1)
        self.assertEqual(list(self.target.iterdir()), [self.target / 'README.md'])
        self.assertEqual((self.target / 'README.md').read_text(), 'old')

    def test_deploy_rollback_preserves_personal_data_and_settings(self):
        for base in [self.source, self.target]:
            (base / 'TaskNotes/Tasks').mkdir(parents=True)
            (base / '.obsidian/plugins/chrysalis-obsidian').mkdir(parents=True)
        personal = self.target / 'TaskNotes/Tasks/private.md'
        personal.write_text('my task')
        (self.source / 'TaskNotes/Tasks/private.md').write_text('do not deploy')
        settings = self.target / '.obsidian/plugins/chrysalis-obsidian/data.json'
        settings.write_text('{"private": true}')
        (self.source / '.obsidian/plugins/chrysalis-obsidian/data.json').write_text('{}')
        (self.source / 'LICENSE').write_text('license')
        update.sync_engine(self.source, self.target, plugins=True)
        self.assertEqual(personal.read_text(), 'my task')
        self.assertEqual(settings.read_text(), '{"private": true}')
        update.rollback(self.target)
        self.assertEqual((self.target / 'README.md').read_text(), 'old')
        self.assertFalse((self.target / 'LICENSE').exists())
        self.assertEqual(personal.read_text(), 'my task')

    def test_repeated_deploy_and_local_edit_conflict(self):
        update.sync_engine(self.source, self.target)
        self.assertEqual(update.sync_engine(self.source, self.target), (0, []))
        (self.target / 'README.md').write_text('local edit')
        (self.source / 'README.md').write_text('next release')
        with self.assertRaisesRegex(ValueError, 'changed locally'):
            update.sync_engine(self.source, self.target)
        with self.assertRaisesRegex(ValueError, 'changed since'):
            update.rollback(self.target)
        self.assertEqual((self.target / 'README.md').read_text(), 'local edit')

    def test_failed_deploy_restores_previous_files(self):
        (self.source / 'LICENSE').write_text('license')
        original_write = update.atomic_write

        def fail_on_readme(path, data):
            if path == self.target / 'README.md' and data == b'new':
                raise OSError('simulated disk error')
            return original_write(path, data)

        with patch.object(update, 'atomic_write', side_effect=fail_on_readme):
            with self.assertRaises(OSError):
                update.sync_engine(self.source, self.target)
        self.assertEqual((self.target / 'README.md').read_text(), 'old')
        self.assertFalse((self.target / 'LICENSE').exists())

    def test_rejects_nested_destination_and_traversal(self):
        with self.assertRaises(ValueError):
            update.sync_engine(self.source, self.source / 'runtime')
        with self.assertRaises(ValueError):
            update.safe_path(self.target, '../source/README.md')

    def test_maps_framework_to_existing_encapsulated_layout(self):
        (self.source / 'System/scripts').mkdir(parents=True)
        (self.source / 'System/scripts/example.py').write_text('pass')
        (self.source / 'System/Workflows').mkdir(parents=True)
        (self.source / 'System/Workflows/01-capture.md').write_text('---\ntype: agent_workflow\n---')
        (self.source / '.agent/skills/task').mkdir(parents=True)
        (self.source / '.agent/skills/task/SKILL.md').write_text('---\nname: task\ndescription: Task skill\n---')
        (self.source / 'TaskNotes/Workflows').mkdir(parents=True)
        (self.source / 'TaskNotes/Workflows/README.md').write_text('# Obsidian Plugin Workflows')
        (self.source / 'TaskNotes/Views').mkdir(parents=True)
        (self.source / 'TaskNotes/Views/workflows.base').write_text('view: workflows')
        (self.target / 'TaskNotes/System').mkdir(parents=True)
        (self.target / 'TaskNotes/.agent/skills').mkdir(parents=True)
        (self.target / 'TaskNotes/Workflows').mkdir(parents=True)
        (self.target / 'TaskNotes/Workflows/private-wf.md').write_text('my plugin workflow')
        update.sync_engine(self.source, self.target)
        self.assertTrue((self.target / 'TaskNotes/System/scripts/example.py').exists())
        self.assertTrue((self.target / 'TaskNotes/System/Workflows/01-capture.md').exists())
        self.assertTrue((self.target / 'TaskNotes/.agent/skills/task/SKILL.md').exists())
        self.assertTrue((self.target / 'TaskNotes/Workflows/README.md').exists())
        self.assertTrue((self.target / 'TaskNotes/Views/workflows.base').exists())
        self.assertEqual((self.target / 'TaskNotes/Workflows/private-wf.md').read_text(), 'my plugin workflow')
        self.assertFalse((self.target / 'System').exists())
        self.assertFalse((self.target / '.agent/skills').exists())

    def test_vault_path_resolves_workflows_and_system_workflows(self):
        (self.target / 'TaskNotes/Workflows').mkdir(parents=True)
        (self.target / 'System/Workflows').mkdir(parents=True)
        (self.target / '_templates').mkdir(parents=True)
        (self.target / 'TaskNotes/_templates').mkdir(parents=True)
        (self.target / '_templates/Task-Template.md').write_text('root template')
        (self.target / 'TaskNotes/_templates/Task-Template.md').write_text('tasknotes template')
        self.assertEqual(vault_path(self.target, 'Workflows'), self.target.resolve() / 'TaskNotes/Workflows')
        self.assertEqual(vault_path(self.target, 'TaskNotes/Workflows'), self.target.resolve() / 'TaskNotes/Workflows')
        self.assertEqual(vault_path(self.target, 'System/Workflows'), self.target.resolve() / 'System/Workflows')
        self.assertEqual(vault_path(self.target, 'TaskNotes'), self.target.resolve() / 'TaskNotes')
        self.assertEqual(vault_path(self.target, '_templates'), self.target.resolve() / '_templates')
        self.assertEqual(vault_path(self.target, 'TaskNotes/_templates'), self.target.resolve() / 'TaskNotes/_templates')
        self.assertEqual(vault_path(self.target, '_templates/Task-Template.md'), self.target.resolve() / '_templates/Task-Template.md')
        self.assertEqual(vault_path(self.target, 'TaskNotes/_templates/Task-Template.md'), self.target.resolve() / 'TaskNotes/_templates/Task-Template.md')
        (self.target / 'Workflows').mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            vault_path(self.target, 'Workflows')

    def test_encapsulated_layout_with_migrated_views_does_not_create_duplicate_tasknotes_views(self):
        (self.source / 'TaskNotes/Workflows').mkdir(parents=True)
        (self.source / 'TaskNotes/Workflows/README.md').write_text('# Obsidian Plugin Workflows')
        (self.source / 'TaskNotes/Views').mkdir(parents=True)
        (self.source / 'TaskNotes/Views/workflows.base').write_text('view: workflows')
        (self.target / 'TaskNotes/System').mkdir(parents=True)
        (self.target / 'TaskNotes/Views').mkdir(parents=True)
        (self.target / 'TaskNotes/Workflows').mkdir(parents=True)
        update.sync_engine(self.source, self.target)
        self.assertTrue((self.target / 'TaskNotes/Views/workflows.base').exists())
        self.assertTrue((self.target / 'TaskNotes/Workflows/README.md').exists())
        self.assertEqual(vault_path(self.target, 'Views'), self.target.resolve() / 'TaskNotes/Views')

    def test_path_resolution_never_selects_sibling_runtime(self):
        with patch.dict('os.environ', {}, clear=True):
            root = resolve_vault_root(script_path=self.source / 'System/scripts/doctor.py')
            self.assertEqual(root, self.source)
        with self.assertRaises(ValueError):
            resolve_vault_root(self.root / 'missing')

    def test_ambiguous_resource_is_rejected(self):
        for rel in ['System', 'TaskNotes/System']:
            directory = self.target / rel
            directory.mkdir(parents=True)
            (directory / 'Scheduling-Memory.md').write_text('state')
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            vault_path(self.target, 'System/Scheduling-Memory.md')

    def test_ingest_skill_and_workflow_01_to_04_alignment(self):
        import yaml
        repo_root = Path(__file__).resolve().parent.parent
        ingest_skill = repo_root / '.agent/skills/ingest/SKILL.md'
        self.assertTrue(ingest_skill.exists())
        raw = ingest_skill.read_text(encoding='utf-8')
        fm = yaml.safe_load(raw.split('---', 2)[1])
        self.assertEqual(fm.get('name'), 'ingest')
        self.assertEqual(fm.get('trigger'), '/ingest')
        self.assertIn('Sources/*.md', fm.get('reads', []))
        self.assertIn('Sources/*.md', fm.get('writes', []))
        for wf in ('01-capture.md', '02-extract.md', '03-review.md', '04-organize.md'):
            self.assertIn(f'System/Workflows/{wf}', fm.get('reads', []))
        self.assertIn('/ingest --drive', (repo_root / '.agent/skills/audit/SKILL.md').read_text(encoding='utf-8'))
        self.assertIn('/ingest --drive', (repo_root / '.agent/skills/evening/SKILL.md').read_text(encoding='utf-8'))
        self.assertIn('.agent/skills/ingest/SKILL.md', (repo_root / '.agent/skills/project/SKILL.md').read_text(encoding='utf-8'))
        self.assertIn('.agent/skills/ingest/SKILL.md', (repo_root / '.agent/skills/zettel/SKILL.md').read_text(encoding='utf-8'))
        self.assertIn('.agent/skills/ingest/SKILL.md', (repo_root / '.agent/skills/plan/SKILL.md').read_text(encoding='utf-8'))

        mem_tmpl_fm = yaml.safe_load((repo_root / 'System/_templates/Memory.template.md').read_text(encoding='utf-8').split('---', 2)[1])
        self.assertEqual(mem_tmpl_fm.get('ingestion_config', {}).get('drive_inbox_folder'), 'Chrysalis-Media-Locker/01-Inbox')
        self.assertTrue(mem_tmpl_fm.get('ingestion_config', {}).get('auto_ingest_on_nightly_audit'))
        self.assertFalse(mem_tmpl_fm.get('ingestion_config', {}).get('local_resources_folder_enabled'))

    def test_sync_deploys_native_skills_protects_sources_and_prunes_spark_artifacts(self):
        import json
        import os

        self.assertTrue(update.is_protected_target('Sources/cs341-syllabus.md'))
        for name in ('ingest', 'zettel', 'audit', 'plan'):
            sdir = self.source / f'.agent/skills/{name}'
            sdir.mkdir(parents=True, exist_ok=True)
            (sdir / 'SKILL.md').write_text(f'---\nname: {name}\ndescription: {name} skill\n---\n# /{name}\nBody for {name}')
        (self.source / '.agent/skills.json').write_text(
            json.dumps({'version': 1, 'entries': [{'path': '.agent/skills'}, {'path': 'Development/skills'}]}) + '\n'
        )
        (self.source / 'TaskNotes/Tasks').mkdir(parents=True, exist_ok=True)
        (self.source / 'TaskNotes/Tasks/example-task.md').write_text('example')
        (self.source / '_types').mkdir(parents=True, exist_ok=True)
        (self.source / '_types/task.md').write_text('---\nkind: mdbase.type\n---')

        # Seed legacy Spark/Golem artifacts and hardlinked Skills/ mirror in target runtime
        legacy_ingest = self.target / '.agent/skills/ingest/SKILL.md'
        legacy_ingest.parent.mkdir(parents=True, exist_ok=True)
        legacy_ingest.write_text('---\nname: ingest\n---\nold ingest body')
        legacy_hardlink = self.target / 'Skills/ingest/SKILL.md'
        legacy_hardlink.parent.mkdir(parents=True, exist_ok=True)
        os.link(legacy_ingest, legacy_hardlink)

        for rel in (
            'Skills/bundle/SKILL.md',
            '_types/skill.md',
            '.agent/skills/chrysalis-router/SKILL.md',
            'docs/spark-agent-system-prompt.md',
            'docs/golem-deployment-and-spark-test-guide.md',
            'Development/SPARK-INTEGRATION-ASSESSMENT.md',
            'System/scripts/package_golem_bundle.py',
            'System/scripts/setup_golem.ps1',
        ):
            p = self.target / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text('legacy spark artifact')

        (self.target / '.agent/skills.json').write_text(
            json.dumps({
                'version': 1,
                'entries': [
                    {'path': '.agent/skills'},
                    {'path': 'Development/skills'},
                    {'path': 'Skills/bundle'},
                    {'path': '.agent/skills/chrysalis-router'},
                    {'path': 'Custom/skills'},
                ],
            }) + '\n'
        )

        update.sync_engine(self.source, self.target)

        # Verify retired artifacts and Skills/ mirror are pruned without breaking .agent/skills/ingest/SKILL.md
        self.assertFalse((self.target / 'Skills').exists())
        self.assertFalse((self.target / '_types/skill.md').exists())
        self.assertFalse((self.target / '.agent/skills/chrysalis-router').exists())
        self.assertFalse((self.target / 'docs/spark-agent-system-prompt.md').exists())
        self.assertFalse((self.target / 'docs/golem-deployment-and-spark-test-guide.md').exists())
        self.assertFalse((self.target / 'Development/SPARK-INTEGRATION-ASSESSMENT.md').exists())
        self.assertFalse((self.target / 'System/scripts/package_golem_bundle.py').exists())
        self.assertFalse((self.target / 'System/scripts/setup_golem.ps1').exists())
        self.assertIn('Body for ingest', (self.target / '.agent/skills/ingest/SKILL.md').read_text(encoding='utf-8'))

        # Verify .agent/skills.json merged non-destructively AND stripped retired Spark paths even when .agent/skills & Development/skills were already present
        merged_cfg = json.loads((self.target / '.agent/skills.json').read_text(encoding='utf-8'))
        entry_paths = [e['path'] for e in merged_cfg['entries']]
        self.assertIn('.agent/skills', entry_paths)
        self.assertIn('Development/skills', entry_paths)
        self.assertIn('Custom/skills', entry_paths)
        self.assertNotIn('Skills/bundle', entry_paths)
        self.assertNotIn('.agent/skills/chrysalis-router', entry_paths)

        # Verify rollback restores pruned Skills/ and retired artifacts cleanly, and re-sync re-prunes them
        update._rollback(self.target)
        self.assertTrue((self.target / 'Skills/ingest/SKILL.md').exists())
        self.assertTrue((self.target / '_types/skill.md').exists())
        self.assertTrue((self.target / '.agent/skills/chrysalis-router/SKILL.md').exists())
        update.sync_engine(self.source, self.target)
        self.assertFalse((self.target / 'Skills').exists())
        self.assertFalse((self.target / '_types/skill.md').exists())

        # Repeated update is a clean no-op
        self.assertEqual(update.sync_engine(self.source, self.target), (0, []))

        # Deleting example-task.md in runtime must not fail subsequent updates
        (self.target / 'TaskNotes/Tasks/example-task.md').unlink()
        (self.source / 'README.md').write_text('v2')
        count, updated = update.sync_engine(self.source, self.target)
        self.assertIn('README.md', updated)
        self.assertFalse((self.target / 'TaskNotes/Tasks/example-task.md').exists())

    def test_workflows_types_and_unquoted_utc_detection(self):
        import yaml
        from helpers.mdbase_helper import check_semantic_duplicate
        from tests.harness.syntax_validator import SyntaxValidator
        from System.scripts.doctor import ChrysalisDoctor

        repo_root = Path(__file__).resolve().parent.parent
        # 1. Workflows 01-05 must explicitly reference /ingest and source_url
        wf01 = (repo_root / 'System/Workflows/01-capture.md').read_text(encoding='utf-8')
        wf02 = (repo_root / 'System/Workflows/02-extract.md').read_text(encoding='utf-8')
        wf03 = (repo_root / 'System/Workflows/03-review.md').read_text(encoding='utf-8')
        wf04 = (repo_root / 'System/Workflows/04-organize.md').read_text(encoding='utf-8')
        wf05 = (repo_root / 'System/Workflows/05-plan.md').read_text(encoding='utf-8')
        self.assertIn('source_url', wf01)
        self.assertIn('/ingest', wf01)
        self.assertIn('Chrysalis-Media-Locker/01-Inbox', wf01)
        self.assertIn('/ingest', wf02)
        self.assertIn('/ingest', wf03)
        self.assertIn('/project', wf04)
        self.assertIn('/zettel', wf04)
        self.assertIn('/plan', wf05)

        # 2. _types/*.md must not have `now: true` in lifecycle (prevents mdbase UTC .sssZ overwrite)
        for tfile in ('task.md', 'project.md', 'zettel.md', 'source.md'):
            tfm = yaml.safe_load((repo_root / '_types' / tfile).read_text(encoding='utf-8').split('---', 2)[1])
            lifecycle = tfm.get('lifecycle', {})
            self.assertNotIn('now', str(lifecycle), f'{tfile} must not set lifecycle now: true')

        # 3. Unquoted UTC .sssZ timestamps must be caught by both SyntaxValidator and ChrysalisDoctor
        bad_task = self.target / 'TaskNotes/Tasks/bad-utc.md'
        bad_task.parent.mkdir(parents=True, exist_ok=True)
        bad_task.write_text(
            '---\n'
            'type: task\n'
            'title: "Bad UTC Timestamp"\n'
            'status: todo\n'
            'dateCreated: "2026-09-25T09:00:00-05:00"\n'
            'created: "2026-09-25T09:00:00-05:00"\n'
            'dateModified: 2026-09-25T04:08:03.274Z\n'
            'due: "2026-09-30"\n'
            'scheduled: null\n'
            'priority: normal\n'
            'urgency_tier: 2\n'
            'modality: analytical\n'
            'timeEstimate: 45\n'
            'energy: medium\n'
            'friction: medium\n'
            'micro_chunked: false\n'
            'tags:\n'
            '  - task\n'
            'linked_zettels: []\n'
            'project_ref: null\n'
            'googleCalendarEventId: null\n'
            '---\n\n# Bad UTC Timestamp\n',
            encoding='utf-8',
        )
        sv = SyntaxValidator()
        _, _, _, issues = sv.validate_syntax_and_schema(bad_task.read_text(encoding='utf-8'), str(bad_task), None)
        self.assertTrue(any(i.code == 'format_invalid' and "raw UTC 'Z'" in i.message for i in issues), issues)

        doc = ChrysalisDoctor(self.target)
        doc.check_2_timezone_compliance()
        self.assertTrue(any("raw UTC 'Z'" in e for e in doc.errors), doc.errors)

        # 4. check_semantic_duplicate must skip Sources/README.md and handle sha256=None safely
        (self.target / 'Sources').mkdir(parents=True, exist_ok=True)
        (self.target / 'Sources/README.md').write_text('# Sources\n', encoding='utf-8')
        (self.target / 'Sources/s1.md').write_text(
            '---\ntype: source\nid: "s1"\nsha256: null\nsource_url: "https://drive.google.com/file/d/abc/view"\n---\n',
            encoding='utf-8',
        )
        self.assertIsNone(check_semantic_duplicate(None, self.target))
        dup = check_semantic_duplicate(None, self.target, source_url='https://drive.google.com/file/d/abc/view')
        self.assertIsNotNone(dup)
        self.assertEqual(dup[0], 's1')

    def test_a2_access_layer_cli_and_skill_compliance(self) -> None:
        import json
        import os
        import shutil
        from unittest import mock
        from System.scripts import vault_paths
        from helpers import mdbase_helper

        repo_root = Path(__file__).resolve().parents[1]
        update.sync_engine(self.source, self.target)
        shutil.copytree(repo_root / "_types", self.target / "_types", dirs_exist_ok=True)
        (self.target / "System").mkdir(parents=True, exist_ok=True)

        # Seed valid runtime state in self.target
        (self.target / "System/Life-Roadmap.md").write_text(
            '---\n'
            'type: strategic_roadmap\n'
            'id: "life-roadmap-test"\n'
            'version: "5.0.0"\n'
            'status: "active"\n'
            'timezone_offset: "-05:00"\n'
            'tag_registry:\n'
            '  - "pillar-1/setup"\n'
            '---\n\n# Life Roadmap\n',
            encoding="utf-8",
        )
        (self.target / "System/Memory.md").write_text(
            '---\n'
            'type: system_state\n'
            'schema_version: "1.0.0"\n'
            'last_updated: "2026-09-27T21:00:00-05:00"\n'
            'updated_by: "test-agent"\n'
            'user_profile:\n'
            '  timezone_offset: "-05:00"\n'
            'cognitive_modality_defaults:\n'
            '  analytical:\n'
            '    baseline_minutes: 90\n'
            '    energy_level: "high"\n'
            '    target_window: "peak_sprint_1"\n'
            '    multiplier: 1.0\n'
            '---\n\n# Memory\n',
            encoding="utf-8",
        )

        # 1. resolve_runtime_vault resolves CHRYSALIS_VAULT_PATH or explicit_path
        self.assertEqual(vault_paths.resolve_runtime_vault(str(self.target)), self.target.resolve())
        with mock.patch.dict(os.environ, {"CHRYSALIS_VAULT_PATH": str(self.target)}):
            self.assertEqual(vault_paths.resolve_runtime_vault(), self.target.resolve())

        # 2. validate_record supports system_state and strategic_roadmap records
        mem_res = mdbase_helper.validate_record(self.target / "System/Memory.md", self.target)
        self.assertTrue(mem_res.valid, mem_res.diagnostics)
        roadmap_res = mdbase_helper.validate_record(self.target / "System/Life-Roadmap.md", self.target)
        self.assertTrue(roadmap_res.valid, roadmap_res.diagnostics)

        # 3. mdbase_helper CLI subcommands work end-to-end (including drive-inbox, check-duplicate --text, apply-cas-mutation, reconcile-syllabus)
        self.assertEqual(
            mdbase_helper.main(["--vault", str(self.target), "validate", str(self.target / "System/Memory.md")]),
            0,
        )
        self.assertEqual(
            mdbase_helper.main(["--vault", str(self.target), "list", "--type", "system_state"]),
            0,
        )
        self.assertEqual(
            mdbase_helper.main(["--vault", str(self.target), "horizon-tasks", "--today", "2026-09-27"]),
            0,
        )
        self.assertEqual(
            mdbase_helper.main(["--vault", str(self.target), "drive-inbox"]),
            0,
        )
        self.assertEqual(
            mdbase_helper.main(
                [
                    "--vault",
                    str(self.target),
                    "check-duplicate",
                    "--text",
                    "Synthetic lecture notes content",
                    "--source-url",
                    "https://drive.google.com/file/d/new-file/view",
                ]
            ),
            0,
        )
        # Verify apply-cas-mutation CLI mutates frontmatter and validates schema
        mem_text = (self.target / "System/Memory.md").read_text(encoding="utf-8")
        mem_fm_raw = mem_text.split("---", 2)[1]
        expected_hash = mdbase_helper.compute_frontmatter_hash(mem_fm_raw)
        self.assertEqual(
            mdbase_helper.main(
                [
                    "--vault",
                    str(self.target),
                    "apply-cas-mutation",
                    str(self.target / "System/Memory.md"),
                    "--expected-hash",
                    expected_hash,
                    "--updates-json",
                    json.dumps({"updated_by": "codex-or-antigravity-agent"}),
                ]
            ),
            0,
        )
        self.assertIn(
            "codex-or-antigravity-agent",
            (self.target / "System/Memory.md").read_text(encoding="utf-8"),
        )

        # Verify zettel_graph_linker CLI accepts --vault and --runtime
        from System.scripts import zettel_graph_linker
        with mock.patch("sys.argv", ["zettel_graph_linker.py", "--vault", str(self.target), "--dry-run"]):
            self.assertEqual(zettel_graph_linker.main(), 0)

        # 4. Verify all 17 runtime, integration, and development skills and workflows have A2 Access Layer and zero Antigravity-only tool lock-in
        all_skills = list(sorted((repo_root / ".agent/skills").glob("*/SKILL.md"))) + list(
            sorted((repo_root / "Development/skills").glob("*/SKILL.md"))
        )
        self.assertEqual(len(all_skills), 17)
        self.assertTrue(update.is_protected_target("System/Ingestion-Sources.md"))
        for skill_md in all_skills:
            text = skill_md.read_text(encoding="utf-8")
            self.assertNotIn("Gemini Spark", text, str(skill_md))
            self.assertNotIn("mdbase_create_record", text, str(skill_md))
            self.assertNotIn("mdbase_update_record", text, str(skill_md))
            self.assertNotIn("mdbase_query_records", text, str(skill_md))
            self.assertIn("A2", text, str(skill_md))
            self.assertNotIn("Antigravity developer chat", text, str(skill_md))

        for wf_md in sorted((repo_root / "System/Workflows").glob("*.md")):
            text = wf_md.read_text(encoding="utf-8")
            self.assertNotIn("Gemini Spark", text, str(wf_md))
            self.assertNotIn("mdbase_query_records", text, str(wf_md))
            self.assertIn("A2", text, str(wf_md))


