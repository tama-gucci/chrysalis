---
name: chrysalis-system
description: Use when the optional NixOS capability is configured and the user asks to install or change Linux, inspect system configuration, or recover an interrupted system operation. Ordinary vault work retains its existing procedures.
---

# NixOS system work

Use chrysalis_system action=status first. If the capability is unavailable, explain that normal Chrysalis still works; do not enable a host shell or install a new OS as a workaround.

Request one native outcome approval through chrysalis_system action=request. The native interface binds the target and backend. A typed request never lets the model approve itself. Use ordinary Nix files and the short system rules.

For initial installation, read references/installation.md. For an installed system, read references/operations.md. Read references/recovery.md after an interruption or uncertain outcome.

The implementation delegates to Pi, NixOS, Home Manager, disko and nix-agent. Tools with chrysalis_system prefixes use the explicit administration context; ordinary read/bash/write/edit remain governed by the existing workspace policy.

A system ledger is machine history, not a task, roadmap or atomic knowledge note. Do not use its projection mechanism to adopt personal records.
