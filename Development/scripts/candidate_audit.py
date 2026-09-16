#!/usr/bin/env python3
"""Audit staged blobs AND tracked/eligible-untracked working files without staging."""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import tempfile


# Exact preserved upstream artifacts; updates require explicit provenance review.
VENDOR_BLOBS = {
    ".obsidian/plugins/chrysalis-obsidian/main.js": "d97b3462d5b049fd955a47bcfd4dcfcbcd1fb4e786162bf42fa6c21fd742df8b",
    ".obsidian/plugins/chrysalis-obsidian/styles.css": "20b739b66bf4559621049d1d4b8068bed816270a127731e46bb620ff314d58d8",
    ".obsidian/plugins/dataview/main.js": "bcdb7a7882051a30427a3fa370533c1052019591e7551bcc12611bb9a726bbb3",
    ".obsidian/plugins/dataview/manifest.json": "9235db47112da81b85591c79ecb9ae2574e5e72207056e976472f90616286185",
    ".obsidian/plugins/dataview/styles.css": "3306dd9032e00f989ba7233a37fd255bc4d3f4340cee661762e952f3f6aa1de9",
    ".obsidian/plugins/various-complements/main.js": "f58b3b54af0573f3c0d08b161f6571f3d130b6a23295ba131d651ab28753dfbe",
    ".obsidian/plugins/various-complements/styles.css": "b79acfb2babedd0329b569febb7d509e5b131be06c583526326275a2fe9cfc54"
}
PATTERNS = {
    'machine path': re.compile(r'(?:/home/|/Users/)[a-zA-Z0-9_-]+|[A-Za-z]:\\+Users\\+[a-zA-Z0-9_-]+'),
    'credential': re.compile(r'ghp_[a-zA-Z0-9]{36}|AIza[0-9A-Za-z_-]{35}|-----BEGIN [A-Z ]*PRIVATE KEY-----|bearer\s+[a-zA-Z0-9_.-]{20,}', re.I),
    'calendar identifier': re.compile(r'[\w.+-]+@group\.calendar\.google\.com'),
    'private task reference': re.compile(r'(?:TaskNotes|chrysalis)/Tasks/202[0-9]{5}-[\w-]+\.md'),
}
EMAIL = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
PRIVATE_PROBES = (
    'System/Life-Roadmap.md', 'System/Scheduling-Memory.md', 'System/System-Health.md',
    'System/Changelog.md', 'chrysalis/System/Scheduling-Memory.md',
    'chrysalis/Tasks/private.md', 'TaskNotes/Tasks/private.md',
    'chrysalis/Archive/private.md', 'TaskNotes/Archive/private.md',
    'chrysalis/Daily/2026-09-16.md', '2026-09-16.md',
    'Projects/private/Roadmap.md', 'Slipbox/private.md',
    'System/Environment/station-node.md', '.obsidian/plugins/example/data.json',
    '.obsidian/plugins/obsidian-git/obsidian_askpass.sh',
    '.obsidian/plugins/example/data/cache.json', '.obsidian/plugins/example/runs/run.json',
    '.venv/config', 'apps/gateway/.venv/config', 'apps/mobile/.dart_tool/package_config.json',
    'apps/mobile/build/output', 'private.env', 'private.token.json', 'credentials.json',
    'Nexus/cache', '.conversations/private', '.workspaces/private', 'note (conflict).md',
)


def git(root, *args):
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE, env=env)


def repository(path):
    return Path(os.fsdecode(git(path, 'rev-parse', '--show-toplevel')).strip()).resolve()


def quarantined(path):
    if path == '.obsidian/plugins/obsidian-git/obsidian_askpass.sh':
        return True
    p = PurePosixPath(path)
    parts = p.parts
    if any(x in parts for x in ('Nexus', '.conversations', '.workspaces', '.venv', 'venv', '__pycache__', '.dart_tool', '.chrysalis', '.backup')):
        return True
    if re.search(r'(^|/)(chrysalis|TaskNotes)/(Tasks|Archive|Daily)/', path):
        return path not in ('chrysalis/Tasks/example-task.md', 'TaskNotes/Tasks/example-task.md')
    if re.search(r'(^|/)System/(Life-Roadmap|Scheduling-Memory|System-Health|Changelog)\.md$', path):
        return True
    if re.match(r'\d{4}-\d{2}-\d{2}.*\.md$', p.name):
        return True
    local = path.removeprefix('chrysalis/')
    if local.startswith(('Projects/', 'Slipbox/')):
        area = local.split('/')[0]
        return local != area + '/README.md' and not local.startswith(area + '/_templates/')
    if local.startswith('System/Environment/'):
        return local != 'System/Environment/Environment-Index.md' and not local.startswith(('System/Environment/_templates/', 'System/Environment/scripts/'))
    if re.search(r'^\.obsidian/(workspace.*\.json|plugins/[^/]+/(data\.json|data/|runs/|storage/|cache\.db))', path):
        return True
    if path.startswith(('apps/mobile/build/', 'apps/mobile/android/.gradle/')) or path.endswith('/local.properties'):
        return True
    return bool(re.search(r'(\.env|token.*\.json|credentials.*\.json|\.db|\.sqlite3?|\.pyc)$', p.name, re.I) or '(conflict' in p.name)


def candidates(root):
    """Reject symlinks/gitlinks instead of reading targets outside the candidate."""
    index = {}
    for row in git(root, 'ls-files', '--stage', '-z').split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t', 1)
        mode, oid, stage = meta.split()
        path = os.fsdecode(name)
        if stage != b'0' or mode not in (b'100644', b'100755'):
            raise ValueError(f'Unsupported or unresolved index entry: {path!r}')
        index[path] = git(root, 'cat-file', 'blob', oid.decode())
    names = set(index)
    names.update(os.fsdecode(n) for n in git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0') if n)
    working = {}
    for name in sorted(names):
        path = root / name
        components = PurePosixPath(name).parts
        linked = any(root.joinpath(*components[:n]).is_symlink() for n in range(1, len(components) + 1))
        if linked or not path.resolve().is_relative_to(root):
            raise ValueError(f'Candidate symlink is not allowed: {name!r}')
        if path.is_file():
            working[name] = path.read_bytes()
        elif path.exists():
            raise ValueError(f'Unsupported candidate entry: {name!r}')
    return {'index': index, 'working': working}


def fingerprint(files):
    return hashlib.sha256(json.dumps(
        [(name, hashlib.sha256(data).hexdigest()) for name, data in sorted(files.items())],
        ensure_ascii=True, separators=(',', ':'),
    ).encode()).hexdigest()


def identities(root, views):
    result = {key: fingerprint(value) for key, value in views.items()}
    result['index_entries'] = hashlib.sha256(git(root, 'ls-files', '--stage', '-z')).hexdigest()
    modes = [(name, bool((root / name).stat().st_mode & 0o111)) for name in sorted(views['working'])]
    result['working_modes'] = hashlib.sha256(json.dumps(modes).encode()).hexdigest()
    return result


def allowed_email(path, value):
    if value.rsplit('@', 1)[1].lower() in ('example.com', 'example.org', 'example.net'):
        return True
    if path == 'update.py' and value == 'git' + '@github.com':
        return True  # SSH transport syntax.
    return bool('/Assets.xcassets/' in path and re.fullmatch(r'[\w.-]+@[123]x\.png', value))


def ignore_issues(files):
    """Evaluate candidate ignore rules in isolation from local/global Git excludes."""
    raw = files.get('.gitignore', b'')
    rules = raw.decode('utf-8').splitlines()
    if len(rules) < 6 or rules[5] != '/*':
        return ['root default-deny must be /* on line 6']
    with tempfile.TemporaryDirectory(prefix='chrysalis-ignore-') as tmp:
        root = Path(tmp)
        clean_env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
        subprocess.run(['git', 'init', '-q', '--template=', str(root)], check=True, capture_output=True, env=clean_env)
        for name, data in files.items():
            if PurePosixPath(name).name == '.gitignore':
                dest = root / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
        env = os.environ.copy()
        for key in list(env):
            if key.startswith('GIT_'):
                env.pop(key)
        result = subprocess.run(
            ['git', '-C', str(root), '-c', 'core.excludesFile=/dev/null',
             'check-ignore', '--no-index', '-z', '--stdin'],
            input=b'\0'.join(p.encode() for p in PRIVATE_PROBES) + b'\0',
            capture_output=True, env=env,
        )
        if result.returncode not in (0, 1):
            raise ValueError('Could not evaluate candidate ignore rules')
        ignored = set(result.stdout.decode().strip('\0').split('\0'))
        return ['private path not ignored: ' + p for p in PRIVATE_PROBES if p not in ignored]


def audit(root):
    views = candidates(root)
    findings = []
    counts = {}
    for view, files in views.items():
        counts[view] = len(files)
        for detail in ignore_issues(files):
            findings.append(f'{view}: {detail}')
        for path, raw in sorted(files.items()):
            if quarantined(path):
                findings.append(f'{view}: {path!r}: quarantined path')
            digest = hashlib.sha256(raw).hexdigest()
            if path in VENDOR_BLOBS:
                if digest != VENDOR_BLOBS[path]:
                    findings.append(f'{view}: {path!r}: upstream artifact changed; provenance review required')
                continue
            if raw.startswith(b'\x89PNG\r\n\x1a\n') and path.endswith('.png'):
                continue
            if raw.startswith(b'\x00\x00\x01\x00') and path.endswith('.ico'):
                continue
            try:
                content = raw.decode('utf-8')
                if '\0' in content:
                    raise UnicodeError()
            except UnicodeError:
                findings.append(f'{view}: {path!r}: unreviewed binary content')
                continue
            for label, pattern in PATTERNS.items():
                for match in pattern.finditer(content):
                    line = content[:match.start()].count('\n') + 1
                    findings.append(f'{view}: {path!r}:{line}: {label}')
            for match in EMAIL.finditer(content):
                if not allowed_email(path, match.group()):
                    line = content[:match.start()].count('\n') + 1
                    findings.append(f'{view}: {path!r}:{line}: non-placeholder email')
    return {'passed': not findings, 'counts': counts,
            'fingerprints': identities(root, views),
            'findings': findings}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        result = audit(repository(args.candidate))
        print(json.dumps(result, indent=2))
        return 0 if result['passed'] else 1
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Privacy audit FAILED: {error}')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
