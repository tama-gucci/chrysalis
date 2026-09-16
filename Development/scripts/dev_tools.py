#!/usr/bin/env python3
"""Locate the installed Flutter SDK without recording machine paths in source."""
import os
from pathlib import Path
import shutil
import sys


def flutter(root):
    configured = os.environ.get('FLUTTER_ROOT')
    if configured:
        choices = [Path(configured) / 'bin/flutter']
    else:
        choices = [Path(shutil.which('flutter'))] if shutil.which('flutter') else []
        properties = root / 'apps/mobile/android/local.properties'
        if properties.is_file():
            for line in properties.read_text().splitlines():
                if line.startswith('flutter.sdk='):
                    choices.append(Path(line.split('=', 1)[1]) / 'bin/flutter')
    for choice in choices:
        if choice.is_file() and os.access(choice, os.X_OK):
            return choice.resolve()
    raise ValueError('Flutter unavailable. Set FLUTTER_ROOT to the installed SDK or add its bin directory to PATH.')


if __name__ == '__main__':
    try:
        print(flutter(Path(__file__).resolve().parents[2]))
    except ValueError as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
