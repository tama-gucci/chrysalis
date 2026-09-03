#!/usr/bin/env bash
# Chrysalis Root Bootstrap & Setup Launcher
# Thin wrapper executing System/scripts/bootstrap.py

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${SCRIPT_DIR}/System/scripts/bootstrap.py" "$@"
