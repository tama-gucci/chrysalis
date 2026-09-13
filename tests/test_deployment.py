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
            (base / 'chrysalis/Tasks').mkdir(parents=True)
            (base / '.obsidian/plugins/chrysalis-obsidian').mkdir(parents=True)
        personal = self.target / 'chrysalis/Tasks/private.md'
        personal.write_text('my task')
        (self.source / 'chrysalis/Tasks/private.md').write_text('do not deploy')
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
        (self.target / 'chrysalis/System').mkdir(parents=True)
        update.sync_engine(self.source, self.target)
        self.assertTrue((self.target / 'chrysalis/System/scripts/example.py').exists())
        self.assertFalse((self.target / 'System').exists())

    def test_path_resolution_never_selects_sibling_runtime(self):
        with patch.dict('os.environ', {}, clear=True):
            root = resolve_vault_root(script_path=self.source / 'System/scripts/doctor.py')
            self.assertEqual(root, self.source)
        with self.assertRaises(ValueError):
            resolve_vault_root(self.root / 'missing')

    def test_ambiguous_resource_is_rejected(self):
        for rel in ['System', 'chrysalis/System']:
            directory = self.target / rel
            directory.mkdir(parents=True)
            (directory / 'Scheduling-Memory.md').write_text('state')
        with self.assertRaisesRegex(ValueError, 'Ambiguous'):
            vault_path(self.target, 'System/Scheduling-Memory.md')
