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

> **A2 Access Layer & Runtime Vault Resolution:**
> Resolve `<personal-vault>` via `python System/scripts/vault_paths.py --runtime --json` (or `$CHRYSALIS_VAULT_PATH` / `$CHRYSALIS_VAULT_ROOT`, defaulting to `~/Documents/Chrysalis` when invoked from the source repository). Paths below are relative to the selected vault (`System/`, `Projects/`, `Slipbox/`, and `Sources/` at the root and operational task folders under `TaskNotes/`). See `ARCHITECTURE.md`.


# /update

Use the selected runtime vault. Source changes belong in the development repository.

1. Select the local development repository, the runtime vault (`python System/scripts/vault_paths.py --runtime --json`), and an explicitly vetted release package. The updater's recursive Development selection does not consult Git ignore rules; exclude private feedback, transcripts and unrelated files from the package. From the source repository root, preview with `python update.py --source "<reviewed-release-package>" --target "<personal-vault>" --dry-run`, replacing both placeholders with explicit paths. Do not infer a source from a sibling folder.
2. If updates are authorized, run the same command without `--dry-run`. Do not use force to bypass locally edited framework conflicts.
3. The updater backs up changed framework files and records their hashes in `.chrysalis/deployments/`. Personal state and plugin settings are excluded. `--plugins` explicitly includes approved plugin binaries.
4. From the same source repository, run `python System/scripts/doctor.py --vault "<personal-vault>" --read-only` (or `python System/scripts/doctor.py --runtime --read-only`) and `python tests/harness/validation_harness.py --vault "<personal-vault>"` with the selected runtime path and verify the affected workflow. A source diagnostic does not install programs or prove every runtime integration is ready.
5. From that source repository, preview latest rollback with `python update.py --target "<personal-vault>" --rollback --dry-run`; remove `--dry-run` to restore it. Rollback stops when a deployed file was edited afterward.

`/update --check` is preview only. Never report update or rollback success without running the command and checking its result. Consult `ARCHITECTURE.md` and `STATUS.md` for ownership and current capabilities.
