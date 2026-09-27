#!/usr/bin/env bash
# Compatibility entry point: inspect staged blobs and the complete working candidate.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if command -v python3 >/dev/null 2>&1 && python3 -c "import sys" >/dev/null 2>&1; then
    exec python3 "$script_dir/candidate_audit.py" "$@"
else
    exec python "$script_dir/candidate_audit.py" "$@"
fi
