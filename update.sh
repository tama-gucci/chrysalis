#!/usr/bin/env bash
# Chrysalis Framework Root Updater Launcher
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/update.py" --target "$SCRIPT_DIR" "$@"
