#!/usr/bin/env bash
# Chrysalis OS Root Bootstrap Launcher
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/System/Environment/scripts/bootstrap.py"
