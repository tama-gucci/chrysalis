#!/usr/bin/env python3
"""Create a clean starter using the same allowlist as runtime deployment."""
import argparse
import json
import sys
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(VAULT_ROOT))
from update import distribution_files, safe_path, atomic_write, DEFAULT_PLUGINS
from System.scripts.bootstrap import ensure_directories, seed_system_memory, seed_life_roadmap, get_local_timezone_offset, get_iso_timestamp


def export_starter(target_dir: str, dry_run: bool = False):
    target = Path(target_dir).resolve()
    if target == VAULT_ROOT or target.is_relative_to(VAULT_ROOT) or VAULT_ROOT.is_relative_to(target):
        raise ValueError("Export must be outside the source repository")
    if target.exists() and any(target.iterdir()):
        raise ValueError("Export destination must be empty; existing files are never removed")
    files = list(distribution_files(VAULT_ROOT, plugins=True))
    if dry_run:
        print(f"DRY RUN: {len(files)} framework files would be exported")
        return
    for relative in files:
        atomic_write(safe_path(target, relative), safe_path(VAULT_ROOT, relative).read_bytes())
    # Settings are synthesized, never copied from a personal installation.
    enabled = [p for p in sorted(DEFAULT_PLUGINS) if (target / '.obsidian/plugins' / p / 'main.js').exists()]
    atomic_write(target / '.obsidian/community-plugins.json', json.dumps(enabled).encode())
    ensure_directories(target)
    offset = get_local_timezone_offset()
    timestamp = get_iso_timestamp(offset)
    seed_system_memory(target, offset, timestamp)
    seed_life_roadmap(target, offset, timestamp)
    print(f"Exported {len(files)} framework files. Personal data and plugin settings were excluded.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', nargs='?')
    parser.add_argument('--target-dir', dest='target_dir')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    target = args.target_dir or args.target
    if not target:
        parser.error('a destination is required')
    export_starter(target, args.dry_run)


if __name__ == '__main__':
    main()
