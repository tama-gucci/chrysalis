# Developing while using Chrysalis (mdbase v0.3)

Edit the framework in the selected local source repository, use the personal runtime vault (`chrysalis/`) for daily operations, and promote changes through the updater. [ARCHITECTURE.md](../ARCHITECTURE.md) defines ownership and [STATUS.md](../STATUS.md) records capability maturity.

New to the project? Start with the [beginner architecture and development guide](BEGINNERS-GUIDE.md), which explains the source/runtime boundary, agent handoffs, Git, testing, and controlled deployment.

Run `python3 Development/scripts/check.py` for local checks. See [Testing](TESTING.md) for setup, failure reports, candidate privacy checks, and the local validation harness.

For a separate Linux development workstation, follow [Workstation setup](WORKSTATION-SETUP.md). Antigravity and Codex share the [agent workflow](AGENT-WORKFLOW.md) and [current handoff](HANDOFF.md).

To set up automation with limited development experience, follow the [step-by-step background development guide](BACKGROUND-DEVELOPMENT.md). Technical details remain in the [engineering reference](BACKGROUND-DEVELOPMENT-REFERENCE.md), [prioritized backlog](BACKLOG.md), and [2026-09-15 source review](REVIEW-2026-09-15.md).

## Daily workflow

Use Antigravity for interactive engineering, including debugging, refactoring, and architecture. Codex is available for selected reviews or second opinions. Both agents follow the same ownership, independent-review, validation, and handoff rules in [AGENT-WORKFLOW.md](AGENT-WORKFLOW.md).

To report friction or suggest an architectural change, use the [plain-language feedback process](FEEDBACK.md).

1. Open the personal runtime vault (`chrysalis/`) in Obsidian and select it explicitly for life operations.
2. Make framework changes in the source repository. Tests use synthetic data in temporary sandboxes.
3. Run the validation checks relevant to the changed subsystem.
4. Prepare a vetted release package, then preview and deploy it with explicit package and personal vault paths. No GitHub push is needed to try a change locally.
5. Run the runtime diagnostic check (`/doctor`) and verify the affected workflow. Roll back the deployment if necessary.

```bash
# Run the complete test suite (contracts, schemas, CAS concurrency, workflows)
python3 -m pytest tests/

# Run the standalone validation test harness
python3 tests/harness/validation_harness.py --collection .

# Verify Zero-Leak PII privacy invariant
bash Development/scripts/pii-scanner.sh
python3 Development/scripts/candidate_audit.py

# Optional: Deploy to personal runtime vault
python3 update.py --source "<reviewed-release-package>" --target "<personal-vault>" --dry-run
python3 update.py --source "<reviewed-release-package>" --target "<personal-vault>"
python3 System/scripts/doctor.py --vault "<personal-vault>" --read-only
```

Note: Legacy prototype daemons (`apps/gateway/`) and mobile client (`apps/mobile/`) have been retired. The Chrysalis framework operates directly on local Markdown files conforming to mdbase v0.3 specifications. Users interact with the vault via Obsidian with the community TaskNotes plugin and candidate AI runtime agents.

## Runtime edits and rollback

Personal notes remain editable during development. Framework changes belong in source. If a managed runtime file has changed, deployment stops: compare it, incorporate the intended change in source, and retry. Do not bypass conflicts by deleting deployment history.

```bash
python3 update.py --target "<personal-vault>" --rollback --dry-run
python3 update.py --target "<personal-vault>" --rollback
```

Rollback restores only the most recent deployment and refuses to overwrite files edited afterward. It does not undo personal task activity. Repeated rollback follows the saved deployment chain. Backups remain in the private vault (`<vault>/.chrysalis/`).

## Templates and exports

`python3 Development/scripts/export_starter.py <empty-directory>` creates a starter from the deployment allowlist and synthetic templates. It refuses a nonempty destination and excludes all personal settings.

## Skills and privacy

Runtime skills are in `.agent/skills/`; development skills are in `Development/skills/`. Back up each modified runbook to `.agent/skills/.backup/` before editing it. Installed copies are updated by deployment.

Before committing or pushing, run `/audit-dev` or `bash Development/scripts/pii-scanner.sh`. Review untracked additions as well. Follow [Development-Constitution.md](Development-Constitution.md): private state stays out of Git, and source examples use synthetic values.
