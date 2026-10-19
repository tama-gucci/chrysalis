# Initial installation

Start with native system setup. It discovers candidate disks and collects account, host and timezone choices, then displays the exact destructive target. Passwords use masked native input, not chat, tools, source or Nix values.

The native seed uses a dedicated GPT disk, a 1 GiB EFI partition, LUKS and Btrfs subvolumes. Facter supplies machine facts. Inspect the seed and improve its real modules as required; use upstream hardware modules for evidenced quirks.

Use the system-context tools for configuration work. Refresh and inspect the target lockfile. Build the selected host with the pinned backend, poll it, and use diff for fresh completed-build evidence. Include new files in Git when working in a Git-backed configuration.

Run chrysalis_system action=install only for the approved live target. Its native adapter invokes disko-install, transfers the editable configuration and selected private Pi state, and leaves boot verification pending.

After handoff, reboot into the installed system. Continue existing native vault onboarding at its final path, then use action=reconcile. Keep the USB until successful boot and ledger projection are observed.
