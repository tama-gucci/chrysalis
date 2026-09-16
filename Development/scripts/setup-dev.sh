#!/usr/bin/env bash
# Prepare a source checkout; never initialize or deploy a personal vault.
set -euo pipefail

mobile=false
case "${1:-}" in
  '') ;;
  --mobile) mobile=true ;;
  *) printf 'Usage: bash Development/scripts/setup-dev.sh [--mobile]\n' >&2; exit 2 ;;
esac
if (( $# > 1 )); then
  printf 'Only --mobile is supported.\n' >&2
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
if $mobile; then
  command -v flutter >/dev/null || { printf 'Add the Flutter SDK bin directory to PATH.\n' >&2; exit 1; }
fi
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
.venv/bin/python -m pip install -r requirements.txt -r apps/gateway/requirements.txt
if $mobile; then
  (cd apps/mobile && flutter pub get)
fi
printf '%s\n' 'Ready. Validate with:' \
  '.venv/bin/python -m unittest discover -t . -s tests' \
  '.venv/bin/python -m pytest apps/gateway/tests -q' \
  'bash Development/scripts/pii-scanner.sh' \
  'In apps/mobile: flutter analyze; flutter test'
