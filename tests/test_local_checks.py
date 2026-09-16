"""Check controller failures and trusted-policy boundaries with synthetic inputs."""
import importlib.util
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Development/scripts'))
try:
    spec = importlib.util.spec_from_file_location('local_checks', ROOT / 'Development/scripts/check.py')
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)
finally:
    sys.path.pop(0)


class LocalCheckTests(unittest.TestCase):
    def test_nonzero_missing_command_and_timeout_are_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cases = [([sys.executable, '-c', 'raise SystemExit(7)'], 5, 7),
                     ([str(root / 'missing')], 5, 1),
                     ([sys.executable, '-c', 'import time; time.sleep(5)'], .05, 124)]
            for command, timeout, expected in cases:
                result = checks.run_check('synthetic', command, root, root, timeout, os.environ.copy())
                self.assertFalse(result['passed'])
                self.assertEqual(result['exit_code'], expected)

    def test_empty_framework_discovery_cannot_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = checks.run_check('framework', [sys.executable, '-c', 'print("Ran 0 tests in 0s")'], root, root, 5, os.environ.copy())
            self.assertFalse(result['passed'])

    def test_dependency_gate_fails_even_with_python_optimization(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock = Path(tmp) / 'requirements.lock'
            lock.write_text('chrysalis-synthetic-missing-dependency==1.0.0\n')
            result = subprocess.run([sys.executable, '-O', '-c', checks.ENVIRONMENT_CHECK, str(lock)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)

    def test_external_candidate_cannot_replace_required_policy(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in checks.POLICY_FILES:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            (root / 'Development/scripts/check.py').write_text('print("PASS")')
            issues = checks.policy_issues(root)
            self.assertTrue(any('Protected check policy differs: Development/scripts/check.py' in issue for issue in issues))
            self.assertTrue(any('Required baseline test file removed' in issue for issue in issues))
