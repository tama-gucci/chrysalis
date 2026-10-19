"""Boot the actual generic image. All writable disks live in --work.

This checks native installation primitives and a real nix-agent MCP backend.
Native fixture approvals replace human dialogs; it makes no model-quality claim.
"""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import uuid
import pexpect

parser = argparse.ArgumentParser()
parser.add_argument("--image", required=True, type=Path)
parser.add_argument("--work", required=True, type=Path)
args = parser.parse_args()
work = args.work.resolve()
work.mkdir(parents=True, exist_ok=True)
if any(work.iterdir()):
    raise SystemExit("Use a new empty external acceptance directory")
images = list(args.image.resolve().rglob("*.raw")) + list(args.image.resolve().rglob("*.img"))
if len(images) != 1:
    raise SystemExit("Expected exactly one native raw image")
usb, target, sentinel = [work / n for n in ("usb.qcow2", "target.qcow2", "sentinel.raw")]
subprocess.run(["qemu-img", "create", "-f", "qcow2", "-F", "raw", "-b", str(images[0]), str(usb), "20G"], check=True)
subprocess.run(["qemu-img", "create", "-f", "qcow2", str(target), "24G"], check=True)
with sentinel.open("wb") as f:
    f.write(b"CHRYSALIS-SENTINEL-DO-NOT-ALTER\n")
    f.truncate(32 * 1024 * 1024)
sentinel_hash = hashlib.sha256(sentinel.read_bytes()).hexdigest()
code = next((p for p in [Path("/usr/share/OVMF/OVMF_CODE_4M.fd"), Path("/usr/share/OVMF/OVMF_CODE.fd")] if p.exists()), None)
if code is None:
    raise SystemExit("OVMF firmware is required")
variables = code.with_name(code.name.replace("CODE", "VARS"))
shutil.copyfile(variables, work / "efi-vars.fd")
probe = Path(__file__).with_name("vm-probe.mjs").read_text()
results = []

class VM:
    def __init__(self, name, live):
        self.live = live
        shutil.copyfile(variables, work / "efi-vars.fd")
        command = [
            "qemu-system-x86_64", "-machine", "q35", "-m", "4096", "-smp", "2",
            "-accel", "kvm" if os.access("/dev/kvm", os.W_OK) else "tcg",
            "-drive", f"if=pflash,format=raw,readonly=on,file={code}",
            "-drive", f"if=pflash,format=raw,file={work / 'efi-vars.fd'}",
            "-vga", "none", "-device", "virtio-gpu-pci", "-display", "none",
            "-serial", "stdio", "-monitor", "none", "-no-reboot",
            "-netdev", "user,id=net", "-device", "virtio-net-pci,netdev=net",
        ]
        disks = [(usb, "chrysalis-usb", "qcow2")] if live else []
        disks += [(target, "chrysalis-target", "qcow2"), (sentinel, "chrysalis-sentinel", "raw")]
        for i, (file, serial, fmt) in enumerate(disks):
            command += ["-drive", f"file={file},if=none,id=d{i},format={fmt}",
                        "-device", f"virtio-blk-pci,drive=d{i},serial={serial},bootindex={i+1}"]
        self.log = (work / (name + ".log")).open("w", encoding="utf8")
        self.child = pexpect.spawn(command[0], command[1:], encoding="utf8", codec_errors="replace", timeout=600)
        self.child.logfile_read = self.log
        if not live:
            self.child.expect(r"(?i)(passphrase|password).*(chrysalis-root|crypt|disk)|(?i:Please enter passphrase)")
            self.child.sendline("fixture-encryption-2026")
        self.child.expect(r"login:\s*$")
        self.child.sendline("chrysalis")
        if not live:
            self.child.expect("Password:")
            self.child.sendline("fixture-account-2026")
        ready = uuid.uuid4().hex
        self.child.sendline("printf '\\nCHRYSALIS_SHELL_%s\\n' " + ready)
        self.child.expect("CHRYSALIS_SHELL_" + ready)
        self.run("stty -echo; export PS1='acceptance$ '")

    def run(self, command, timeout=2400, admin=False):
        token = "CHRYSALIS_RESULT_" + uuid.uuid4().hex
        encoded = base64.b64encode(command.encode()).decode()
        # Keep each terminal line below canonical input's line limit.
        self.child.sendline(": > /tmp/chrysalis-command")
        for i in range(0, len(encoded), 2000):
            self.child.sendline("printf %s " + shlex.quote(encoded[i:i+2000]) + " >> /tmp/chrysalis-command")
        shell = "base64 -d /tmp/chrysalis-command > /tmp/chrysalis-command.sh; "
        if admin and not self.live:
            shell += "printf '%s\\n' fixture-account-2026 | sudo -S -p '' bash /tmp/chrysalis-command.sh"
        else:
            shell += ("sudo -n " if admin else "") + "bash /tmp/chrysalis-command.sh"
        shell += "; printf '\\n" + token + ":%s\\n' \"$?\""
        self.child.sendline(shell)
        self.child.expect(token + r":(\d+)", timeout=timeout)
        status = int(self.child.match.group(1))
        if status:
            raise RuntimeError(f"Guest command failed ({status}); see {self.log.name}")
        return self.child.before

    def agent(self):
        self.run("""
agent_ready() {
  systemctl is-active --quiet cage-tty1 &&
  pgrep -x ghostty >/dev/null &&
  tmux has-session -t chrysalis &&
  tmux list-panes -t chrysalis -F '#{pane_current_command}' | grep -qxE 'pi|node|bun'
}
for attempt in $(seq 1 120); do
  if agent_ready; then
    restarts=$(systemctl show --value --property=NRestarts cage-tty1)
    sleep 5
    if agent_ready && test "$(systemctl show --value --property=NRestarts cage-tty1)" = "$restarts"; then exit 0; fi
  fi
  sleep 1
done
journalctl -u cage-tty1 -n 80 --no-pager
exit 1
""")

    def put(self, content, destination):
        encoded = base64.b64encode(content.encode()).decode()
        self.run("printf %s " + shlex.quote(encoded) + " | base64 -d > " + shlex.quote(destination))

    def probe(self, phase, admin=False):
        self.put(probe, "/tmp/chrysalis-vm-probe.mjs")
        self.run("export CHRYSALIS_SYSTEM_CONFIG=/etc/chrysalis/system.json; "
                 "export CHRYSALIS_STATE_ROOT=/var/lib/chrysalis/state; "
                 "export TSX_DISABLE_CACHE=1; "
                 "export TSX_TSCONFIG_PATH=/etc/chrysalis/package/tsconfig.json; "
                 "node --import /etc/chrysalis/package/node_modules/tsx/dist/loader.mjs "
                 "/tmp/chrysalis-vm-probe.mjs " + phase, admin=admin)

    def shutdown(self):
        self.child.sendline("sudo -n poweroff" if self.live else "printf '%s\\n' fixture-account-2026 | sudo -S -p '' poweroff")
        self.child.expect(pexpect.EOF, timeout=120)
        self.child.close()
        self.log.close()

    def abort(self):
        if self.child.isalive():
            self.child.terminate(force=True)
        self.log.close()

active = None
try:
    active = VM("01-live", True)
    active.agent()
    active.run("echo retained > /var/lib/chrysalis/state/acceptance-checkpoint; sync")
    active.shutdown()
    results.append("actual raw EFI boot and graphical terminal")
    active = VM("02-persistent-install", True)
    active.run("grep retained /var/lib/chrysalis/state/acceptance-checkpoint")
    active.agent()
    active.run("sudo -n systemctl stop cage-tty1")
    active.probe("install")
    active.abort()
    results.append("USB power-cycle persistence and dedicated-disk installation")
    active = VM("03-partial-handoff", True)
    active.run("sudo -n systemctl stop cage-tty1")
    active.probe("partial-handoff", admin=True)
    active.abort()
    results.append("handoff interrupted after a durable target copy")
    active = VM("04-handoff-after-restart", True)
    active.run("sudo -n systemctl stop cage-tty1")
    active.probe("handoff", admin=True)
    active.shutdown()
    results.append("restart between install and handoff without repeated formatting")
    active = VM("05-target", False)
    active.agent()
    active.run("systemctl stop cage-tty1", admin=True)
    active.probe("installed")
    active.probe("operations")
    active.shutdown()
    results.append("encrypted target boot, vault, real MCP activation, rollback and ledger")
    assert hashlib.sha256(sentinel.read_bytes()).hexdigest() == sentinel_hash, "Sentinel disk changed"
    results.append("unrelated sentinel disk unchanged")
    (work / "result.json").write_text(json.dumps({"status": "passed", "checks": results}, indent=2))
except BaseException as error:
    (work / "result.json").write_text(json.dumps({"status": "failed", "checks": results, "error": str(error)}, indent=2))
    raise
finally:
    if active:
        active.abort()
