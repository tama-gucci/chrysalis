#!/usr/bin/env bash
# Prepare a source checkout; never initialize or deploy a personal vault.
set -euo pipefail

if (( $# > 0 )); then
  printf 'Usage: bash Development/scripts/setup-dev.sh\n' >&2
  exit 2
fi
if [[ -n "${CHRYSALIS_VAULT_PATH:-}" || -n "${CHRYSALIS_MEMORY_PATH:-}" ]]; then
  printf 'Unset personal CHRYSALIS_VAULT_PATH and CHRYSALIS_MEMORY_PATH before development setup.\n' >&2
  exit 1
fi
repository="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository"
for tool in python3 git; do
  command -v "$tool" >/dev/null || { printf 'Missing tool: %s\n' "$tool" >&2; exit 1; }
done
if [[ "$(git rev-parse --show-toplevel)" != "$repository" ]]; then
  printf 'Run this from a Chrysalis source checkout.\n' >&2
  exit 1
fi
python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3, 14) else "Use Python 3.14 for the pinned local environment")'
if [[ -L .venv || ( -e .venv && ! -f .venv/pyvenv.cfg ) ]]; then
  printf 'Refusing an unexpected or linked .venv directory.\n' >&2
  exit 1
fi
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
if [[ ! -x .venv/bin/python ]]; then
  printf 'The existing .venv is not a usable Linux environment. Recreate it locally.\n' >&2
  exit 1
fi
.venv/bin/python -m pip install -r requirements.txt -r Development/requirements.lock
printf '%s\n' 'Ready. Validate with:' 'python3 Development/scripts/check.py'
