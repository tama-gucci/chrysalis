#!/bin/bash
set -euo pipefail
# Native operator installation only. Models cannot invoke this outside their sandbox.
if [ "$(id -u)" -ne 0 ] || [ -z "${SUDO_USER:-}" ] || [ -z "${SUDO_UID:-}" ]; then
  echo 'Run this reviewed installer with sudo from your normal account.' >&2
  exit 1
fi
command -v apt-get >/dev/null || { echo 'Automatic runner setup currently supports Debian/Ubuntu hosts.' >&2; exit 1; }
test -d /run/systemd/system || { echo 'Enable systemd in the Linux/WSL distribution first.' >&2; exit 1; }
apt-get update
apt-get install --no-install-recommends bubblewrap
loginctl enable-linger "$SUDO_USER"
systemctl start "user@${SUDO_UID}.service"
echo 'Runner prerequisites installed. Return to Pi and run /chrysalis assistant-status, then select a workspace.'
