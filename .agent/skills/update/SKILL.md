---
name: update
description: "Upstream framework synchronization engine: inspects GitHub upstream releases, performs dry-run diff checks, safely updates core framework code, skills, views, and templates via update.py without touching personal data, and executes an automated post-update /doctor integrity pass."
trigger: "/update"
domain: runtime
reads:
  - "update.py"
  - "System/Runtime-Constitution.md"
  - "System/System-Health.md"
  - "System/Changelog.md"
writes:
  - "System/System-Health.md"
  - "System/Changelog.md"
---

> Paths below are relative to the explicitly selected vault. The default layout keeps System, Projects, and Slipbox at the root and operational task folders under chrysalis/. For an existing encapsulated vault, resolve the corresponding resource under chrysalis/; never create a competing copy. See ARCHITECTURE.md.


# /update

Use the selected runtime vault. Source changes belong in the development repository.

1. Preview the local source with `python update.py --source ../vault-git --target . --dry-run` from the runtime root. Resolve both paths explicitly; folder names are examples.
2. If updates are authorized, run the same command without `--dry-run`. Do not use force to bypass locally edited framework conflicts.
3. The updater backs up changed framework files and records their hashes in `.chrysalis/deployments/`. Personal state and plugin settings are excluded. `--plugins` explicitly includes approved plugin binaries.
4. Run `python System/scripts/doctor.py --vault . --read-only` and verify the affected workflow. On encapsulated installations use `chrysalis/System/scripts/doctor.py`.
5. Preview latest rollback with `python update.py --target . --rollback --dry-run`; remove `--dry-run` to restore it. Rollback stops when a deployed file was edited afterward.

`/update --check` is preview only. Never report update or rollback success without running the command and checking its result. Consult ARCHITECTURE.md and STATUS.md for ownership and current capabilities.
