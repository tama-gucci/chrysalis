#!/usr/bin/env bash
# Compatibility entry point: inspect staged blobs and the complete working candidate.
set -euo pipefail
script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$script_dir/candidate_audit.py" "$@"
