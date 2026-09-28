"""Synthetic regressions for cleanup compatibility and data preservation."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import update
from Development.scripts.export_starter import export_starter
from System.scripts.bootstrap import ensure_directories, seed_system_memory
from System.scripts.doctor import ChrysalisDoctor
from System.scripts.migrate_to_subfolder import create_directory_structure, migrate_substrates
from System.scripts.vault_paths import memory_path, vault_path

ROOT = Path(__file__).resolve().parents[1]


class CleanupRegressions(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        env = patch.dict('os.environ', {}, clear=True)
        env.start()
        self.addCleanup(env.stop)

    def put(self, relative, content):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_bootstrap_preserves_legacy_memory_and_layout(self):
        for prefix in ('', 'chrysalis/', 'TaskNotes/'):
            with self.subTest(prefix=prefix), tempfile.TemporaryDirectory() as directory:
                vault = Path(directory)
                memory = vault / prefix / 'System/Scheduling-Memory.md'
                memory.parent.mkdir(parents=True)
                memory.write_text('---\ntimezone_offset: "+02:00"\ntag_multipliers: {analytical: 1.7}\n---\n')
                tasks = vault / (prefix or 'TaskNotes/') / 'Tasks'
                tasks.mkdir(parents=True)
                before = memory.read_bytes()
                ensure_directories(vault)
                seed_system_memory(vault, '-05:00', '2026-09-24T09:00:00-05:00')
                self.assertEqual(memory_path(vault=vault), memory)
                self.assertEqual(memory.read_bytes(), before)
                self.assertEqual(vault_path(vault, 'Tasks'), tasks)
                self.assertEqual(list(vault.rglob('Memory.md')), [])

    def test_ambiguous_memory_cannot_fall_back(self):
        self.put('System/Memory.md', 'first')
        self.put('TaskNotes/System/Memory.md', 'second')
        self.put('System/Scheduling-Memory.md', 'fallback')
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            memory_path(vault=self.root)
        doctor = ChrysalisDoctor(self.root)
        doctor.check_6_dynamic_state_multipliers()
        self.assertTrue(doctor.errors)
        self.assertIn('FAIL', doctor.check_results['6_multipliers']['status'])

    def test_doctor_validates_runtime_legacy_memory_before_template(self):
        self.put('System/Scheduling-Memory.md', '---\ntag_multipliers: {analytical: 9}\n---\n')
        doctor = ChrysalisDoctor(self.root)
        doctor.check_6_dynamic_state_multipliers()
        self.assertTrue(doctor.errors)
        self.assertIn('FAIL', doctor.check_results['6_multipliers']['status'])

    def test_doctor_multiplier_boundaries_and_malformed_memory(self):
        for value, valid in [('0.2', True), ('2', True), ('0.19', False), ('2.01', False),
                             ('.nan', False), ('.inf', False), ('false', False), ('null', False), ('bad', False)]:
            with self.subTest(value=value):
                self.put('System/Memory.md', '---\ncognitive_modality_defaults:\n  analytical:\n    multiplier: ' + value + '\n---\n')
                doctor = ChrysalisDoctor(self.root)
                doctor.check_6_dynamic_state_multipliers()
                self.assertEqual(not doctor.errors, valid)
        self.put('System/Memory.md', '---\ncognitive_modality_defaults: null\n---\n')
        doctor = ChrysalisDoctor(self.root)
        doctor.check_6_dynamic_state_multipliers()
        self.assertIn('FAIL', doctor.check_results['6_multipliers']['status'])

    def test_workflow_conflict_preserves_all_bytes_in_preview_and_execution(self):
        old = self.put('TaskNotes/Workflows/01-capture.md', '---\ntype: agent_workflow\n---\nlocal edits')
        current = self.put('System/Workflows/01-capture.md', '---\ntype: agent_workflow\n---\nnew version')
        before = {p: p.read_bytes() for p in (old, current)}
        for dry_run in (True, False):
            with self.subTest(dry_run=dry_run), self.assertRaisesRegex(FileExistsError, 'copies differ'):
                migrate_substrates(self.root, 'TaskNotes', dry_run=dry_run)
            self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_workflow_body_cannot_reclassify_plugin_data(self):
        note = self.put('TaskNotes/Workflows/custom.md', '---\ntype: runtime_workflow\n---\nExample: type: agent_workflow')
        before = note.read_bytes()
        migrate_substrates(self.root, 'TaskNotes')
        self.assertEqual(note.read_bytes(), before)
        self.assertFalse((self.root / 'TaskNotes/System/Workflows/custom.md').exists())

    def test_mdbase_encapsulation_is_rejected_before_writing(self):
        manifest = self.put('mdbase.yaml', 'spec_version: "0.3.0"\n')
        with self.assertRaisesRegex(ValueError, 'canonical split layout'):
            create_directory_structure(self.root, 'TaskNotes')
        self.assertEqual(list(self.root.iterdir()), [manifest])

    def test_legacy_update_mapping_and_private_protection(self):
        self.put('chrysalis/System/Memory.md', 'private state')
        self.assertEqual(update.destination_relative(self.root, 'System/scripts/doctor.py'),
                         'chrysalis/System/scripts/doctor.py')
        for path in ('chrysalis/System/Memory.md', 'chrysalis/Tasks/private.md',
                     'TaskNotes/System/Memory.md', 'TaskNotes/Workflows/private.md'):
            self.assertTrue(update.is_protected_target(path), path)
        with self.assertRaisesRegex(ValueError, 'canonical'):
            update.deployment_plan(ROOT, self.root)
        self.assertEqual(list(self.root.iterdir()), [self.root / 'chrysalis'])

    def test_canonical_deployment_contains_complete_framework_and_preserves_state(self):
        memory = self.put('System/Memory.md', 'private state')
        roadmap = self.put('System/Life-Roadmap.md', 'private roadmap')
        plugin = self.put('TaskNotes/Workflows/private.md', 'private workflow')
        update.sync_engine(ROOT, self.root)
        for relative in ('mdbase.yaml', '_types/task.md', '_contracts/task.contract.md',
                         'contracts/agent-runtime.contract.md', 'helpers/mdbase_helper.py',
                         'System/Workflows/01-capture.md', 'tests/harness/validation_harness.py'):
            self.assertTrue((self.root / relative).is_file(), relative)
        for path, expected in ((memory, 'private state'), (roadmap, 'private roadmap'), (plugin, 'private workflow')):
            self.assertEqual(path.read_text(), expected)
        self.assertFalse((self.root / 'Development/archive').exists())

    def test_bundle_uses_public_distribution_inventory(self):
        starter = self.root / 'starter'
        export_starter(str(starter))
        exported = {p.relative_to(starter).as_posix() for p in starter.rglob('*') if p.is_file()}
        dist = set(update.distribution_files(ROOT))
        self.assertTrue(dist.issubset(exported))
        self.assertNotIn('System/Life-Roadmap.md', dist)
        self.assertNotIn('System/Memory.md', dist)
        self.assertIn(
            'active_pillar: "Pillar 1:',
            (starter / 'System/Life-Roadmap.md').read_text(encoding='utf-8'),
        )
        for forbidden in (
            '.agent/skills/chrysalis-router/SKILL.md',
            'docs/spark-agent-system-prompt.md',
            'docs/golem-deployment-and-spark-test-guide.md',
            'Development/SPARK-INTEGRATION-ASSESSMENT.md',
            'System/scripts/package_golem_bundle.py',
            'System/scripts/setup_golem.ps1',
            'Skills/bundle/SKILL.md',
        ):
            self.assertNotIn(forbidden, dist)
            self.assertNotIn(forbidden, exported)
        self.assertFalse(any(name.startswith('Development/archive/') for name in dist))
        self.assertFalse(any(name.startswith('Skills/') for name in dist))
