# Developing while using Chrysalis

Edit the framework in `vault-git/`, use `vault/` for daily operations, and promote changes through the updater. [ARCHITECTURE.md](../ARCHITECTURE.md) defines ownership and [STATUS.md](../STATUS.md) records capability maturity.

New to the project? Start with the [beginner architecture and development guide](BEGINNERS-GUIDE.md), which explains the source/runtime boundary, agent handoffs, Git, testing, and controlled deployment.

See [Testing](TESTING.md) for test setup and validation boundaries.

For a separate Linux development workstation and runtime server, follow [Workstation setup](WORKSTATION-SETUP.md). Antigravity and Codex share the [agent workflow](AGENT-WORKFLOW.md) and [current handoff](HANDOFF.md).

To set up automation with limited development experience, follow the [step-by-step background development guide](BACKGROUND-DEVELOPMENT.md). Each step includes a message to paste into Codex and a result to check. Technical details remain in the [engineering reference](BACKGROUND-DEVELOPMENT-REFERENCE.md), [prioritized backlog](BACKLOG.md), and [2026-09-15 source review](REVIEW-2026-09-15.md). These documents do not themselves configure a recurring developer or release job.

## Daily workflow

1. Open the personal vault in Obsidian and select it explicitly for life operations.
2. Make framework changes in the repository. Tests use synthetic data in temporary vaults.
3. Run the checks relevant to the changed subsystem.
4. Preview and deploy from the local source. No GitHub push is needed to try a change locally.
5. Run the runtime diagnostic check and verify the affected workflow. Roll back the deployment if necessary.

```powershell
python -m unittest discover -t . -s tests
python -m pytest apps/gateway/tests -q
# In apps/mobile:
flutter test
flutter analyze
# Back in the repository root:
python update.py --source . --target ../vault --dry-run
python update.py --source . --target ../vault
python System/scripts/doctor.py --vault ../vault --read-only
```

Install the gateway test dependencies in an isolated environment using `apps/gateway/requirements.txt`. Use the same environment when running its tests. The framework scripts require PyYAML.

## Runtime edits and rollback

Personal notes remain editable during development. Framework changes belong in source. If a managed runtime file has changed, deployment stops: compare it, incorporate the intended change in source, and retry. Do not bypass conflicts by deleting deployment history.

```powershell
python update.py --target ../vault --rollback --dry-run
python update.py --target ../vault --rollback
```

Rollback restores only the most recent deployment and refuses to overwrite files edited afterward. It does not undo personal task activity. Repeated rollback follows the saved deployment chain. Backups remain in the private vault.

## Plugins and exports

`--plugins` deploys approved binary assets, preserving settings. Restart Obsidian afterward. The current plugin is vendored; develop a future standalone plugin in its own source project rather than hand-editing minified JavaScript.

`python Development/scripts/export_starter.py <empty-directory>` creates a starter from the deployment allowlist and synthetic templates. It refuses a nonempty destination and excludes all plugin settings.

## Skills and privacy

Runtime skills are in `.agent/skills/`; development skills are in `Development/skills/`. Back up each modified runbook to `.agent/skills/.backup/` before editing it. Installed copies are updated by deployment.

Before committing or pushing, run `/audit-dev` or `bash Development/scripts/pii-scanner.sh`. Review untracked additions as well. Follow [Development-Constitution.md](Development-Constitution.md): private state stays out of Git, and source examples use synthetic values.
