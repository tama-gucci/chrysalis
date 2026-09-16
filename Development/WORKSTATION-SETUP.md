# Separate development workstation and runtime server

Use a native local checkout on the development workstation, outside Google Drive, rclone/FUSE mounts, and personal vault synchronization. Keep the private runtime installation on the server. Git transfers source changes; the existing updater promotes selected framework files into the runtime.

## Preserve the source before moving

Inspect `git status --short`, `git diff HEAD`, and `git ls-files --others --exclude-standard` on the old machine. A clone or Git bundle carries committed history only. Preserve uncommitted changes, deletions, and untracked source additions separately, or commit a reviewed checkpoint after the required privacy audit. Keep transfer snapshots private. Do not copy installed SDKs, virtual environments, build caches, credentials, runtime notes, or entire IDE profiles into source.

Verify the destination against the recorded commit and file checksums before retiring anything. Keep the old checkout until tests and the first controlled deployment pass. Inspect gateway/service launch configuration before deleting any development directory; a running runtime service may still depend on it.

## Linux toolchain

Install Git, Python with venv support, Bash, ripgrep, and a Linux x64 Flutter SDK that satisfies `apps/mobile/pubspec.yaml` (currently Dart `^3.13.2`). Keep `pubspec.lock`; do not upgrade dependencies as part of relocation. Check the selected Flutter release's bundled Dart version rather than installing unrelated standalone Dart.

For Flutter Linux desktop and native test assets, provide Clang, CMake, Ninja, pkg-config, GTK 3 development libraries, and the C++ toolchain. On Arch the corresponding packages include `base-devel`, `clang`, `cmake`, `ninja`, `pkgconf`, and `gtk3`. Review package changes before installation. [Flutter's Linux setup guide](https://docs.flutter.dev/platform-integration/linux/setup) describes the required toolchain and doctor checks.

For Android, install Android Studio or the SDK command-line tools, SDK platforms/build-tools, and the NDK/CMake selected by Flutter and Gradle. Platform-tools alone are insufficient. Use the repository Gradle wrapper; inspect `android/settings.gradle.kts` and `android/gradle/wrapper/gradle-wrapper.properties`. Java source compatibility is 17; the Gradle runtime JDK must also satisfy the selected Android plugin. Review Android SDK licenses interactively. Follow [Flutter's Android setup guide](https://docs.flutter.dev/platform-integration/android/setup).

From a fresh source checkout, in Bash:

```bash
bash Development/scripts/setup-dev.sh --mobile
.venv/bin/python -m unittest discover -t . -s tests
.venv/bin/python -m pytest apps/gateway/tests -q
bash Development/scripts/pii-scanner.sh
cd apps/mobile
flutter --version
flutter doctor -v
flutter analyze
flutter test
dart --packages=.dart_tool/package_config.json test/data/local_vault_initialization_check.dart
flutter build apk --debug
```

The bootstrap creates a per-checkout Python environment and installs declared dependencies. Without `--mobile`, it only prepares Python. It does not install OS packages, create a runtime vault, deploy files, or configure credentials. Root `bootstrap.sh` initializes a runtime and is not the development setup command. Python requirements currently specify ranges rather than a complete lockfile; record resolved versions after a successful destination run.

Recreate environments in every worktree. Run Android device tests on an explicitly selected test device with synthetic data. Linux builds cannot validate Windows-specific behavior or iOS builds. [TESTING.md](TESTING.md) and [STATUS.md](../STATUS.md) define remaining integration limits.

## Configure the two agents

Open the source repository root in Antigravity and Codex. Verify each agent can quote the shared workflow and current handoff and report the actual Git commit. Keep personal vaults out of this development workspace.

Antigravity documents Linux x64 support and AGENTS.md discovery. Confirm the installed executable/version; package inventories can be stale and multiple launchers can coexist. See its [downloads](https://antigravity.google/download), [changelog](https://antigravity.google/changelog), and [hooks](https://antigravity.google/docs/hooks).

The official [Codex Linux desktop guide](https://learn.chatgpt.com/docs/linux/linux-app) currently describes Debian/Ubuntu and Fedora packages. It does not establish a supported Arch package. Verify desktop compatibility before adopting any community packaging. The [Codex CLI](https://learn.chatgpt.com/docs/codex/cli) provides a documented Linux path; sign in on the workstation rather than copying another machine's authentication files.

Both tools load [repository instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md); our AGENTS.md points to [AGENT-WORKFLOW.md](AGENT-WORKFLOW.md) and [HANDOFF.md](HANDOFF.md). A new session should run `python3 Development/scripts/agent_context.py show` and inspect the files it identifies.

### Optional lifecycle hooks

After checking installed-client support, install the supplied templates as `.agents/hooks.json` (Antigravity) and `.codex/hooks.json` (Codex). Create the directories if missing. Merge with existing configuration; do not overwrite existing hooks. These local files are intentionally ignored by this repository's default-deny policy. Reinstall or merge them for each independent worktree; ordinary Git worktree creation will not carry ignored configuration.

The templates are [antigravity-hooks.template.json](_templates/antigravity-hooks.template.json) and [codex-hooks.template.json](_templates/codex-hooks.template.json). Commands target Linux Python 3. They resolve the helper from the Git root, including when a session starts in `apps/mobile`. The hooks only emit a fixed read reminder; the helper's `show` command reads shared engineering context and current Git state. Raw histories are never injected as instructions.

Codex requires both project trust and separate trust for each hook definition. Open `/hooks` in its interactive CLI, inspect the exact command, and trust that definition. A new or changed hook is skipped until reviewed, even if the project itself is trusted. Repeat this review when a definition changes or a different worktree introduces a new hook location. See [hook review and trust](https://learn.chatgpt.com/docs/hooks#review-and-trust-hooks). Do not disable hook trust checks.

Antigravity uses its first `PreInvocation`; Codex uses `SessionStart` for startup, resume, clear, and compaction. Current [Codex hook documentation](https://learn.chatgpt.com/docs/hooks) describes repository hooks, merging, and event output. Feature availability must be tested in the installed clients. AGENTS.md remains the fallback if hooks are unsupported.

Smoke-test each client: start a fresh session in the root and then a source subdirectory, ask it to report the handoff's next step and current commit, and inspect the hook/context-read output. Record whether hooks actually ran. Finish a small synthetic engineering task with one agent, update the handoff, and have the other review its exact changes. Do not describe cross-agent handoff as validated until that round trip succeeds.

Antigravity has a separate interactive [SSH OAuth flow](https://antigravity.google/docs/cli/install/#remote-ssh-oauth-flow). A timed-out headless SSH login does not establish that its desktop client is unusable. Validate the intended desktop project directly, or complete the documented remote login before testing its CLI over SSH.

For Codex desktop worktrees, configure a local-environment setup action through the app using `bash Development/scripts/setup-dev.sh --mobile`. Review its generated `.codex` configuration before sharing it. Git-created worktrees need setup explicitly. See [local environments](https://learn.chatgpt.com/docs/environments/local-environment) and [worktrees](https://learn.chatgpt.com/docs/environments/git-worktrees).

## Runtime server after cutover

The server continues running the existing private vault, its Obsidian settings/plugins, and any configured gateway/orchestrator. Development migration does not prove gateway health or remove its agent-runtime dependencies. Retain the required runtime launcher and credentials. The plugin API and optional gateway use distinct ports, 8080 and 8765.

After a source change has passed review and tests, transfer its committed revision to a dedicated release checkout on the server. Keep this checkout separate from both the personal vault and any old dirty development checkout. Verify its commit, then preview using explicit source and target paths:

```powershell
# From the server workspace; release-source is the reviewed source checkout.
python release-source/update.py --source release-source --target vault --dry-run
# Inspect the preview, then apply that same revision:
python release-source/update.py --source release-source --target vault
python release-source/System/scripts/doctor.py --vault vault --read-only
```

Do not run a blanket directory mirror or deploy directly from a moving development branch. Pause framework-editing agents during deployment. The updater preserves personal state and stores private rollback history. Apps and gateway services have separate release lifecycles; updating vault files does not restart or package them. Rollback commands remain in [README.md](README.md).

The transition is complete only after source recovery, workstation toolchain checks, an actual two-agent handoff, and a reviewed deployment rehearsal succeed. Remote login alone is the first access check.
