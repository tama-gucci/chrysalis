#!/usr/bin/env python3
"""Run every required local check; optionally control a separate candidate checkout."""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import tempfile
import time

from candidate_audit import audit, candidates, identities, repository
from dev_tools import flutter

ENVIRONMENT_CHECK = """import importlib.metadata as metadata
from pathlib import Path
import sys

if sys.version_info[:2] != (3, 14):
    raise SystemExit("Python 3.14 required")
pins = [line.split("==") for line in Path(sys.argv[1]).read_text().splitlines()
        if line and not line.startswith("#")]
bad = [name for name, version in pins if metadata.version(name) != version]
if bad:
    raise SystemExit("Pinned dependencies differ: " + str(bad))
print("Python and dependency pins match")
"""

TRUSTED_ROOT = Path(__file__).resolve().parents[2]
POLICY_FILES = (
    'Development/scripts/check.py', 'Development/scripts/candidate_audit.py',
    'Development/scripts/dev_tools.py', 'Development/scripts/pii-scanner.sh',
    'Development/scripts/setup-dev.sh', 'Development/requirements.lock',
    'Development/skills/audit-dev/SKILL.md',
)


def policy_issues(root):
    issues = []
    if root != TRUSTED_ROOT:
        for name in POLICY_FILES:
            path = root / name
            if path.is_symlink() or not path.is_file() or path.read_bytes() != (TRUSTED_ROOT / name).read_bytes():
                issues.append(f'Protected check policy differs: {name}; review and update the trusted controller separately.')
        for pattern in ('tests/**/test_*.py', 'apps/gateway/tests/test_*.py', 'apps/mobile/test/**/*test.dart'):
            for source in TRUSTED_ROOT.glob(pattern):
                relative = source.relative_to(TRUSTED_ROOT)
                if not (root / relative).is_file():
                    issues.append(f'Required baseline test file removed: {relative}')
    return issues


def run_check(name, command, cwd, directory, timeout, env):
    log = directory / (name + '.log')
    start = time.monotonic()
    print(f'RUN  {name}', flush=True)
    code = 1
    try:
        with log.open('w') as output:
            process = subprocess.Popen(command, cwd=cwd, env=env, stdout=output,
                                       stderr=subprocess.STDOUT, start_new_session=True)
            try:
                code = process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                output.write('\nCheck interrupted or exceeded its time limit.\n')
                code = 124
    except OSError as error:
        log.write_text(str(error) + '\n')
    if name == 'framework' and code == 0:
        if not re.search(r'Ran [1-9][0-9]* tests? in ', log.read_text()):
            with log.open('a') as output:
                output.write('\nNo executed framework tests were reported.\n')
            code = 1
    passed = code == 0
    print(f'{"PASS" if passed else "FAIL"} {name} (exit {code}) — {log}', flush=True)
    return {'name': name, 'passed': passed, 'exit_code': code,
            'seconds': round(time.monotonic() - start, 2), 'log': str(log)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=TRUSTED_ROOT,
                        help='Source checkout to test using this controller’s required checks.')
    args = parser.parse_args()
    directory = Path(tempfile.mkdtemp(prefix='chrysalis-check-'))
    results = []
    report = {'started': datetime.now().astimezone().isoformat(), 'checks': results,
              'mode': 'local development check', 'passed': False}
    try:
        root = repository(args.candidate)
        if platform.system() != 'Linux':
            raise ValueError('The verified local runner supports Linux; use the documented toolchain.')
        if any(os.environ.get(k) for k in ('CHRYSALIS_VAULT_PATH', 'CHRYSALIS_MEMORY_PATH')):
            raise ValueError('Unset personal runtime overrides before development checks.')
        problems = policy_issues(root)
        if problems:
            raise ValueError('\n'.join(problems))
        report['mode'] = 'external trusted controller' if root != TRUSTED_ROOT else 'local development check'
        initial = audit(root)
        report['candidate'] = initial['fingerprints']
        report['head'] = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True).strip()
        (directory / 'privacy.log').write_text(json.dumps(initial, indent=2) + '\n')
        results.append({'name': 'candidate-privacy', 'passed': initial['passed'], 'log': str(directory / 'privacy.log')})
        print(f'{"PASS" if initial["passed"] else "FAIL"} candidate-privacy — {directory / "privacy.log"}', flush=True)
        if not initial['passed']:
            raise ValueError('Candidate privacy failed; inspect the report before executing candidate tests.')
        python = root / '.venv/bin/python'
        if (root / '.venv').is_symlink() or not python.is_file():
            raise ValueError('Run bash Development/scripts/setup-dev.sh --mobile in this checkout first.')
        flutter_bin = flutter(root)
        dart = flutter_bin.parent / 'cache/dart-sdk/bin/dart'
        env = os.environ.copy()
        env['PYTHONNOUSERSITE'] = '1'
        for key in ('PYTHONPATH', 'PYTHONHOME', 'PYTHONOPTIMIZE', 'PYTEST_ADDOPTS', 'PYTEST_PLUGINS'):
            env.pop(key, None)
        env['PATH'] = str(flutter_bin.parent) + os.pathsep + env.get('PATH', '')
        checks = [
            ('dependencies', [str(python), '-c', ENVIRONMENT_CHECK, str(TRUSTED_ROOT / 'Development/requirements.lock')], root, 60),
            ('pip-consistency', [str(python), '-m', 'pip', 'check'], root, 60),
            ('flutter-version', [str(flutter_bin), '--version', '--machine'], root, 120),
            ('framework', [str(python), '-m', 'unittest', 'discover', '-t', '.', '-s', 'tests'], root, 300),
            ('gateway', [str(python), '-m', 'pytest', 'apps/gateway/tests', '-q'], root, 60),
            ('flutter-analysis', [str(flutter_bin), 'analyze', '--no-pub'], root / 'apps/mobile', 300),
            ('flutter-tests', [str(flutter_bin), 'test', '--no-pub', '--reporter', 'expanded'], root / 'apps/mobile', 600),
            ('storage-regression', [str(dart), '--packages=.dart_tool/package_config.json', 'test/data/local_vault_initialization_check.dart'], root / 'apps/mobile', 60),
        ]
        for name, command, cwd, timeout in checks:
            result = run_check(name, command, cwd, directory, timeout, env)
            if name == 'flutter-version' and result['passed']:
                try:
                    version = json.loads(Path(result['log']).read_text())
                    if version.get('flutterVersion') != '3.47.2' or not version.get('dartSdkVersion', '').startswith('3.13.2'):
                        raise ValueError('Expected Flutter 3.47.2 with Dart 3.13.2')
                except ValueError as error:
                    result.update(passed=False, exit_code=1, detail=str(error))
                    print(f'FAIL flutter-version: {error}', flush=True)
            results.append(result)
        final = identities(root, candidates(root))
        unchanged = final == initial['fingerprints']
        results.append({'name': 'candidate-unchanged', 'passed': unchanged})
        print(f'{"PASS" if unchanged else "FAIL"} candidate-unchanged', flush=True)
        report['passed'] = all(result['passed'] for result in results)
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report['error'] = str(error)
        print(f'FAIL preflight: {error}', flush=True)
    finally:
        report['finished'] = datetime.now().astimezone().isoformat()
        (directory / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
        print(f'\nOverall: {"PASS" if report["passed"] else "FAIL"}. Report: {directory / "report.json"}', flush=True)
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
