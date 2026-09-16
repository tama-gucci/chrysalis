"""Privacy regressions use disposable Git indexes and synthetic leak strings."""
import importlib.util
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('candidate_audit', ROOT / 'Development/scripts/candidate_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class CandidateAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.put('.gitignore', (ROOT / '.gitignore').read_text())
        self.put('README.md', 'Synthetic source\n')
        self.git('add', '.')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def test_clean_candidate_and_index_are_unchanged(self):
        before = (self.root / '.git/index').read_bytes()
        result = audit.audit(self.root)
        self.assertTrue(result['passed'], result)
        self.assertEqual(before, (self.root / '.git/index').read_bytes())

    def test_untracked_addition_and_staged_secret_hidden_by_clean_working_copy(self):
        secret = 'ghp_' + 'A' * 36
        self.put('README.md', secret)
        self.git('add', 'README.md')
        self.put('README.md', 'Clean working copy\n')
        self.put('tests/new.py', 'person' + '@' + 'private.test')
        findings = audit.audit(self.root)['findings']
        self.assertTrue(any('index:' in f and 'credential' in f for f in findings))
        self.assertTrue(any('working:' in f and 'non-placeholder email' in f for f in findings))
        self.assertFalse(any(secret in f for f in findings))

    def test_machine_paths_and_bearer_keys_are_rejected(self):
        examples = ['/' + 'home/' + 'synthetic/private', 'C:' + chr(92) + 'Users' + chr(92) + 'synthetic',
                    'bearer ' + 'x' * 24, 'AIza' + 'A' * 35,
                    '-----BEGIN ' + 'PRIVATE KEY-----']
        for content in examples:
            with self.subTest(content=content):
                self.put('tests/new.py', content)
                result = audit.audit(self.root)
                self.assertFalse(result['passed'])
                self.assertFalse(any(content in f for f in result['findings']))

    def test_forced_private_paths_are_rejected(self):
        for name in ['System/Life-Roadmap.md', 'chrysalis/Tasks/private.md',
                     'Projects/private/Roadmap.md', '.obsidian/plugins/demo/data.json',
                     'private.env', 'chrysalis/.chrysalis/private',
                     '.obsidian/plugins/obsidian-git/obsidian_askpass.sh']:
            with self.subTest(name=name):
                self.put(name, 'synthetic')
                self.git('add', '-f', name)
                self.assertTrue(any('quarantined path' in f for f in audit.audit(self.root)['findings']))
                self.git('rm', '--cached', name)

    def test_staged_ignore_hole_cannot_be_hidden_by_working_rules(self):
        good = (self.root / '.gitignore').read_text()
        self.put('.gitignore', good + '\n!/System/Life-Roadmap.md\n')
        self.git('add', '.gitignore')
        self.put('.gitignore', good)
        self.assertTrue(any('index: private path not ignored' in f for f in audit.audit(self.root)['findings']))

    def test_symlink_and_unmerged_index_fail_closed(self):
        target = self.put('README.md', 'Synthetic source')
        os.symlink(target, self.root / 'tests-link')
        self.git('add', '-f', 'tests-link')
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            audit.audit(self.root)

    def test_symlinked_parent_directory_is_rejected(self):
        self.put('tests/data.py', 'synthetic')
        self.git('add', 'tests/data.py')
        (self.root / 'tests').rename(self.root / 'other')
        os.symlink(self.root / 'other', self.root / 'tests')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            audit.audit(self.root)

    def test_new_javascript_and_unknown_binary_are_not_blanket_exempt(self):
        path = self.put('tests/new.js', 'user' + '@' + 'private.test')
        self.assertFalse(audit.audit(self.root)['passed'])
        path.write_bytes(b'\xff\x00private')
        self.assertTrue(any('unreviewed binary' in f for f in audit.audit(self.root)['findings']))

    def test_upstream_exemption_requires_exact_blob(self):
        name = '.obsidian/plugins/dataview/manifest.json'
        self.put(name, (ROOT / name).read_text())
        self.assertTrue(audit.audit(self.root)['passed'])
        with (self.root / name).open('a') as stream:
            stream.write('\n')
        self.assertTrue(any('provenance review required' in f for f in audit.audit(self.root)['findings']))

    def test_email_exceptions_are_narrow(self):
        self.assertTrue(audit.allowed_email('README.md', 'user@example.com'))
        self.assertTrue(audit.allowed_email('update.py', 'git' + '@github.com'))
        self.assertFalse(audit.allowed_email('README.md', 'git' + '@github.com'))
        self.assertTrue(audit.allowed_email('apps/mobile/ios/Runner/Assets.xcassets/AppIcon/Contents.json', 'Icon' + '@2x.png'))
        self.assertFalse(audit.allowed_email('README.md', 'Icon' + '@2x.png'))
