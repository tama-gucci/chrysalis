# Separate development workstation and runtime vault

Use a native local checkout on the development workstation, outside Google Drive, rclone/FUSE mounts, and personal vault synchronization. Keep the private runtime vault (`chrysalis/`) separate from the development source repository. Git transfers source changes; `update.py` promotes selected framework files into the personal runtime vault.

## Preserve the source before moving

Inspect `git status --short`, `git diff HEAD`, and `git ls-files --others --exclude-standard` on the old machine. A clone or Git bundle carries committed history only. Preserve uncommitted changes, deletions, and untracked source additions separately, or commit a reviewed checkpoint after the required privacy audit. Keep transfer snapshots private. Do not copy installed SDKs, virtual environments, build caches, credentials, runtime notes, or entire IDE profiles into source.

Verify the destination against the recorded commit and file checksums before retiring anything. Keep the old checkout until tests and the first controlled deployment pass.

## Toolchain & Environment Requirements

Chrysalis is an open, provider-independent AI agent framework operating on an **mdbase v0.3** Markdown database. Developing and validating the framework requires only standard Linux/Unix development tools:

- **Git** (version 2.40+)
- **Python 3.14** (tested 3.14.7) with `venv` support
- **Bash** and standard core utilities
- **ripgrep** (`rg`) for fast boundary and text scanning

### Note on Retired Historical Prototypes (`apps/gateway/` & `apps/mobile/`)
The bespoke Flutter mobile application (`apps/mobile/`) and FastAPI daemon (`apps/gateway/`) have been **formally retired**. The core framework operates directly on local Markdown files without daemon processes or custom mobile clients. You do NOT need Flutter SDK, Dart SDK, Android Studio, or C++ build tools for core Chrysalis development. Their code and tests are preserved in `apps/` solely for historical regression verification.

## Standard Verification Commands

From a fresh source checkout root, in Bash:

```bash
# 1. Prepare isolated virtual environment and dependencies
bash Development/scripts/setup-dev.sh

# 2. Run the authoritative framework pytest suite (259+ tests)
.venv/bin/pytest tests/

# 3. Run the standalone 3-layer mdbase v0.3 validation harness
python3 tests/harness/validation_harness.py -c .

# 4. Run candidate privacy audit and PII scanner (zero-leak invariant)
python3 Development/scripts/candidate_audit.py
bash Development/scripts/pii-scanner.sh
```

The bootstrap creates a per-checkout Python environment and installs declared dependencies. It does not install OS packages, create a runtime vault, deploy files, or configure credentials. Root `bootstrap.sh` initializes a runtime vault and is not the development setup command. Recreate environments in every worktree.

## Configure the Engineering Agents

Open the source repository root in Antigravity and Codex. Verify each agent can quote the shared workflow (`Development/AGENT-WORKFLOW.md`), current handoff (`Development/HANDOFF.md`), and report the actual Git commit. Keep personal vaults out of this development workspace.

Antigravity documents Linux x64 support and `AGENTS.md` discovery. Codex CLI provides a documented Linux path; sign in on the workstation rather than copying another machine's authentication files.

Both tools load repository instructions; our `AGENTS.md` points to [AGENT-WORKFLOW.md](AGENT-WORKFLOW.md) and [HANDOFF.md](HANDOFF.md). A new session should run `python3 Development/scripts/agent_context.py show` and inspect the files it identifies.

### Optional Lifecycle Hooks

After checking installed-client support, install the supplied templates as `.agents/hooks.json` (Antigravity) and `.codex/hooks.json` (Codex). Create the directories if missing. Merge with existing configuration; do not overwrite existing hooks. These local files are intentionally ignored by this repository's default-deny policy. Reinstall or merge them for each independent worktree; ordinary Git worktree creation will not carry ignored configuration.

The templates are [antigravity-hooks.template.json](_templates/antigravity-hooks.template.json) and [codex-hooks.template.json](_templates/codex-hooks.template.json). Commands target Linux Python 3. The hooks only emit a fixed read reminder; the helper's `show` command reads shared engineering context and current Git state. Raw histories are never injected as instructions.

## Runtime Vault Deployment

The personal runtime vault (`chrysalis/`) runs directly on local disk, visualized via Obsidian with the community TaskNotes plugin, and operated on by autonomous AI agents governed by `contracts/agent-runtime.contract.md`. There is no background gateway daemon.

After a source change has passed review, tests, and `/audit-dev`, preview and apply the deployment using explicit source and target paths:

```bash
# Preview changes non-destructively
python3 update.py --source release-source --target /path/to/chrysalis --dry-run

# Apply deployment to runtime vault
python3 update.py --source release-source --target /path/to/chrysalis
```

Do not run a blanket directory mirror or deploy directly from a moving development branch. Pause framework-editing agents during deployment. The updater preserves personal state and stores private rollback history in `<vault>/.chrysalis/`. Rollback instructions remain in [README.md](../README.md).
