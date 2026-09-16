# Current engineering handoff

Date: 2026-09-16
Prepared by: Codex, B00 implementation with independent review
Branch: `main`
Code baseline: `cfa92e845773c501b4bdf3c62bda6a1570e86307`
Checkpoint: the local commit containing this B00 entry; identify it with `git log -1 --format=%H -- Development/HANDOFF.md`. The parent baseline above does not identify the repaired source.

Current activity: B00 repairs and acceptance checks are complete, with independent review of the source candidate. This checkpoint includes the preserved development working state. Background execution, publication and runtime installation remain off. Earlier notes below are historical evidence, not current instructions or authorization.

## B00 starting-version repair — 2026-09-16

Reproduced all five prior failures: framework 133 passed/3 failed; Flutter 101 passed/2 failed. Reconciled `_types/task.md` with the complete baseline framework fields (version, archived state, telemetry timestamps, knowledge links and NLP metadata), retained compatible TaskNotes annotations, and replaced the generated-file notice with explicit framework ownership. Added parsed-YAML schema regression coverage in `tests/test_task_schema.py`.

Hybrid command/message notices now identify `mailboxClient.mailboxPath` and state that local buffering is not execution. Updated mailbox/interface comments and transport tests. Tests cover default, custom and explicitly selected legacy destinations; preservation of a legacy event during repeated default appends; unchanged legacy bytes; and precedence of an existing selected mailbox. Mailbox read/write behavior itself is unchanged. Malformed queues and multi-client coordination remain B03/B08 work.

Preserved all prior mobile persistence/UI/debug changes, plugin deletions and community configuration, generated CMake changes, setup/context tools, guides and tests. Normalized synthetic calendar fixture addresses to reserved example domains for the privacy audit. Converted Markdown trailing-space line breaks in the two background guides and this handoff to explicit line breaks where needed so the complete newly staged diff passes whitespace checks. A pre-edit content hash inventory verified that unrelated source contents were preserved.

Validation executed from the source root unless marked mobile:

| Command | Result |
| --- | --- |
| `python3 Development/scripts/agent_context.py show` | Actual baseline, branch and dirty state inspected |
| `.venv/bin/python -m unittest discover -t . -s tests` | 138 passed, including new schema regressions; repeated after fixture normalization |
| `timeout 60s .venv/bin/python -m pytest apps/gateway/tests -q` | 11 passed; two dependency deprecation warnings |
| `flutter analyze --no-pub` (mobile) | No issues |
| `flutter test --no-pub --reporter expanded` (mobile) | 108 passed |
| `flutter test --no-pub test/domain/device_calendar_sync_test.dart --reporter expanded` (mobile) | Affected suite passed after fixture-only address normalization |
| `dart --packages=.dart_tool/package_config.json test/data/local_vault_initialization_check.dart` (mobile) | Repeated initialization and file persistence passed |
| `bash Development/scripts/pii-scanner.sh` and complete `/audit-dev` Protocol 1 review | Candidate scanner, quarantine checks, supplemental staged-content scan and ignore-boundary checks passed |
| `git diff --cached --check` | Passed, including all new files |

Flutter commands used the installed SDK explicitly and approved SDK-cache access; the restricted attempt failed before tests began. Gateway tests used approved execution outside the restrictive sandbox. This is local test evidence; no new APK build, physical-device test, hosted CI run or real backend execution was performed.

Independent review: a separate read-only review agent inspected the complete staged candidate against `cfa92e8`, including new files and preserved changes. It found no actionable introduced B00 issues and independently passed six schema/context tests, the scanner and staged whitespace checks. The reviewed source candidate's staged manifest (`git ls-files --stage | sha256sum`) was `ea0e03b3ae74ce5ba64b937f1346aa214a8e3293c6944349c43c990858a6c8c6`; only this handoff, STATUS and backlog completion records changed afterward, with final staged review before committing.

Privacy scope: all 332 candidate files were included, with 290 non-vendor text files scanned from staged blobs for machine paths, Windows user paths, secret patterns and email-like strings. Fifteen representative private-path ignore probes passed. Reserved synthetic addresses were accepted; image filenames and SSH transport strings are not email addresses. The unchanged upstream Dataview manifest author attribution was reviewed as public package provenance and retained. No private runtime files or credentials were found in the candidate. The existing scanner alone does not cover the whole audit contract; durable automation of these supplemental checks remains B01.

Next: B01's local validation milestone, then B02. A passing source baseline is not approval to deploy or evidence that deferred calendar, doctor, mailbox corruption, synchronization or runtime integrations are ready. All work remains local; this checkpoint does not enable a scheduler or publish changes.

## Background development Step 1 — 2026-09-16

Verified the source checkout on a local filesystem, branch `main`, at `cfa92e845773c501b4bdf3c62bda6a1570e86307`. Read the shared instructions, architecture, status, handoff, setup/testing guides and Step 1. Ran `python3 Development/scripts/agent_context.py show`, Git root/branch/HEAD/worktree/status checks, `git diff --stat`, `git diff --numstat`, inspected the maintained-code/configuration diff, and checked the staging index (empty). Before this note, 15 tracked files were modified, 11 tracked plugin files deleted, and 17 untracked entries present. Preserve the existing mobile, schema, plugin, documentation, setup/helper and test changes; the commit alone does not include them.

Read-only tool checks found Git, Python, Bash, ripgrep, Clang, CMake, Ninja, pkg-config, GTK 3, C++, Java, Android platform-tools, the configured Android SDK and a runnable Flutter installation. Flutter's installed metadata reports 3.47.2; its bundled Dart executable reports 3.13.2, matching the mobile constraint. Flutter is absent from this session's PATH: use the configured SDK executable or set a process-local PATH before mobile checks. The shell's default Java is 26; JDK 17 is also installed. Select and verify the intended JDK when running Android checks. No persistent tool configuration was changed.

The existing source `.venv` successfully imports the declared framework/gateway packages, and `.venv/bin/python -m pip check` reports no broken requirements. `pkg-config --modversion gtk+-3.0` and executable version checks passed. No personal runtime environment override was set. `git diff --check` passed. No application suites, build, device rehearsal or publication audit were run for this inspection; the five earlier test failures remain historical results requiring fresh verification in Step 2.

Step 1 is complete: the correct source project and installed tools are identified, with the command-path/JDK caveats above. No dependencies were installed, application files repaired, commits created, schedule enabled or personal vault accessed. Scheduling UI availability was not inspected. Next action is the separately requested Step 2/B00 repair and review, preserving the complete dirty source state. `Development/AUTOMATION-RUN.md` is still absent, as expected before Step 4.

## Beginner guide revision — 2026-09-15

Verified `main` at `cfa92e845773c501b4bdf3c62bda6a1570e86307`, ran the context helper, and inspected the dirty state before editing. This revision changes documentation only: the beginner walkthrough, its preserved technical reference, the developer index, backlog milestone wording, `.gitignore`'s explicit reference-document entry, and this handoff.

The guide now follows one local setup path: verify the source/tools; repair and review a checkpoint; automate local checks; implement the development routine; rehearse one complete run; schedule it; verify its first automatic run; review/install completed improvements weekly. It includes a fallback request when the client lacks Scheduled. Product instructions were checked against current official OpenAI documentation. Actual account/client scheduling access was not tested.

B01 now distinguishes local validation from hosted CI. B02 and the initial local workflow depend on the verified local milestone; hosted CI remains pending until exercised. This avoids requiring a beginner to configure GitHub before a local trial. The planned `Development/AUTOMATION-RUN.md` must be created and tested during B02; it does not exist yet. The daily routine's local integration policy must be configured and verified separately from publication and runtime installation.

No setup prompts in the guide were executed, and no agent worker or schedule was activated. Application tests were not rerun for this documentation-only revision; the earlier dated results below remain historical evidence. Next implementation remains B00, followed by B01's local milestone and B02. Preserve existing unrelated work and use the current user's task to establish scope.

Revision validation: eight ordered steps, 32 local document links/anchors, three Bash examples in the technical reference, and `git diff --check` passed. The privacy scanner passed against a temporary source-only Git snapshot of all 331 existing eligible files. A pre-edit content-hash manifest confirmed that only the five intended existing documentation/allowlist files changed, plus the new technical reference. The real Git staging index remained empty. No application or private runtime file changed.

## Current review and next action — 2026-09-15

The latest objective is background framework development with minimal supervision. It supersedes the earlier emphasis on automating daily runtime scheduling. Keep the existing source/runtime separation. This review did not inspect the personal Life Roadmap or mutate personal state.

Verified `main` at `cfa92e845773c501b4bdf3c62bda6a1570e86307` and inspected the existing dirty diff. Preserved prior application changes, schema changes, plugin removals, toolchain files, context tools and beginner guide. Current additions are `Development/REVIEW-2026-09-15.md`, `Development/BACKGROUND-DEVELOPMENT.md`, `Development/BACKLOG.md`, and `Development/_templates/background-{builder,review}.prompt.md`; current edits add links/allowlist entries in `.gitignore` and `Development/README.md`, dated findings in `STATUS.md`, and this handoff. All are uncommitted.

Fresh validation: framework 133 passed/3 failed; gateway 11 passed with 2 deprecation warnings; Flutter analysis clean; Flutter tests 101 passed/2 failed; standalone storage regression passed. The review records exact commands and sandbox limitations. Additional temporary synthetic probes reproduced calendar memory corruption/data loss, recurrence/timezone errors, doctor false-success, malformed mailbox overwrite, archived-task scheduling, and missing duration telemetry. No new device/backend test was run.

Documentation verification passed for local links, Bash example syntax and diff whitespace. A content-hash comparison with the pre-edit source manifest found changes only in the four intended existing documentation/allowlist files; unrelated source contents were preserved. The privacy scanner passed on a temporary source-only Git snapshot containing all 330 existing eligible files, including additions. The real staging index remained empty. Additional pattern review identified existing vendor/asset/fixture/transport matches and incomplete scanner coverage; see R11 and B01. This is a scoped audit result, not a privacy certification of arbitrary content.

Next implementation sequence: B00 repairs the source baseline and prepares it for separate review; B01 establishes reproducible validation/CI; B02 rehearses a single-worker development loop before recurrence. Prioritize B03/B04/B06 preservation and diagnostic repairs, then controlled release preparation. The candidate must include the intended dirty work; creating a plain worktree at the old HEAD would omit it. A reviewed source checkpoint is needed before that workflow starts.

No scheduler, dispatcher, CI workflow, automatic publication or runtime promotion was enabled. The templates are execution instructions requiring a concrete runner assignment and configured scope. Do not infer publishing or live deployment permission from this handoff or its earlier plans.

## Goal and decisions

Move primary development to a Linux x86_64 workstation. Keep the personal installation on its existing server. Use a native local Git checkout for development, synthetic test vaults, and explicit reviewed framework deployments. Follow [WORKSTATION-SETUP.md](WORKSTATION-SETUP.md) and [AGENT-WORKFLOW.md](AGENT-WORKFLOW.md).

Antigravity implements features; Codex reviews, refactors, and handles architecture. Both read this handoff and the shared instructions. Concurrent writers use separate worktrees. Optional hook templates load a fixed context reminder; Codex hook execution is verified. The user supplied a successful Antigravity desktop handoff read; Antigravity hook execution remains unverified.

## Work already present before transition preparation

- Mobile persistence initialization and timeline UI changes; Android debug network configuration; a new standalone storage regression check. Inspect `apps/mobile/` and the dated device section in STATUS.md. Those device results were recorded by a prior session, not independently repeated during migration preparation.
- Obsidian plugin removals and community-plugin configuration edits, plus task schema and testing documentation changes. Preserve and review these changes; cloning the baseline commit alone loses them.
- The complete maintained Obsidian plugin source and release pipeline are absent. Existing bundles do not establish a rebuildable plugin project.

## Transition additions

- Shared agent workflow and workstation setup guide; root instructions point both agents here.
- A development-only bootstrap and context helper, plus optional hook templates and synthetic helper tests.
- Development instructions allow either selected coding agent to perform interactive engineering. Existing privacy, backup, and deployment rules still apply.

## Validation and next action

The source has been recovered on the destination workstation. The transfer verified 324 source files by Git content hashes, preserved 11 deletions and all 10 Git-eligible untracked additions, and retained the baseline history. Subsequent Flutter dependency resolution regenerated the Linux and Windows plugin CMake lists to include `jni`; review these generated changes with the rest of the working diff.

Verified destination toolchain: Linux x86_64, Python 3.14.7, Flutter 3.47.2 with Dart 3.13.2, Clang 22.1.8, JDK 17.0.20.1, Android SDK platform 36 and build-tools 36.0.0. Flutter doctor reports healthy Android and Linux toolchains. Web Chrome configuration remains absent and was not needed for the Android build.

- Framework: 133 of 136 passed, including all four new shared-context helper tests. Three failures concern the already-dirty task schema: missing `startedAt`/`completedAt`, missing `archived` status, and missing schema version. The old machine has the same three failures.
- Gateway: 11 passed, with two dependency deprecation warnings.
- Flutter analysis: no issues.
- Flutter tests: 101 passed, two failed in `test/transport/hybrid_orchestrator_transport_test.dart`. These expect `System/Inbox/events.json` while the current default mailbox uses `chrysalis/System/Inbox/events.json`. The transport's status text also still names the old path; reconcile the contract before changing tests.
- Standalone local-storage regression: passed.
- Android debug APK: built successfully on the destination. No new physical-device installation or rehearsal was performed during this transition.
- Privacy audit: passed on the destination using a temporary Git index containing all current additions, modifications, and deletions. The real staging index was left unchanged.
- Codex CLI 0.154.0: authenticated and successfully read the shared documents and context helper. Its exact startup hook was reviewed and trusted through `/hooks` after discovering that hook trust is separate from project trust. A minimal read-only turn then emitted `hook/started` and `hook/completed` for `SessionStart`, completing successfully in 42 ms. The hook runs with the first turn, not bare session initialization.
- Antigravity desktop 2.12.2 / CLI 1.2.1: present. On 2026-09-14 the user supplied its desktop report: it read this handoff and correctly reported main at cfa92e8 with the preserved dirty working tree. Codex independently rechecked that state over SSH. This proves desktop context reading; it does not prove the Antigravity startup hook ran. The earlier SSH CLI test timed out awaiting authentication.

Continue development on the new workstation. Keep the old source checkout and private transfer packet as recovery copies. Do not edit both checkouts independently. The personal runtime was not modified, and no source changes were committed or pushed by the migration.

Next: Antigravity implements the reviewed schema and mailbox repairs below, updates this handoff with actual validation, and yields to Codex for review. Then create an audited source checkpoint before parallel worktrees or deployment. Avoid opening the source as a daily-use Obsidian vault: its task schema is marked as generated from plugin settings and the current dirty diff removed framework fields. Preserve the complete maintained schema when resolving that change.

Before retiring any old directory, verify service launch configuration no longer depends on it. No process was listening on the server's standard plugin/gateway ports when checked during preparation; this transition does not establish that those services are continuously running. Use a separate reviewed release checkout and updater preview for the first runtime promotion, after the code review and validation issues are resolved.

## First implementation and review round trip

Codex reviewed these contracts on 2026-09-14 against baseline `cfa92e8` plus the current dirty files. Application/schema code was not changed during this review. Content SHA-256 values identify the reviewed files; compare them before applying findings if another session has edited them:

- `_types/task.md`: `eeb52e17fa6b16fe48ad48de5e3c31b904ddc06d060a095d71afbc5b7a1f4379`
- `apps/mobile/lib/transport/substrate_mailbox_client.dart`: `9710ddbf544e97fa8d27753451b1f903160e72f59f6f8d9d1948f4bef0d1b2f3`
- `apps/mobile/lib/transport/hybrid_orchestrator_transport.dart`: `35498a98bf521041ad75d2958b84a1e42f821b802293d9597b1fbd7b07de17d8`
- `apps/mobile/test/transport/hybrid_orchestrator_transport_test.dart`: `8a30dc6f0d2a9135903f1e737a510a34c2d2ed6370ff3e41f02558d46aff354b`

### Findings and implementation scope

1. `_types/task.md`: the working diff drops `version: 0.2.0`, `archived`, `startedAt`, and `completedAt`. It also drops `linked_zettels`, `project_ref`, and `x-chrysalis` NLP metadata, which the three reported failures do not cover. Compare the complete schema with `git show HEAD:_types/task.md`; preserve the maintained Chrysalis fields and compatible TaskNotes annotations. Do not weaken the tests or blindly discard the entire working diff. Clarify source ownership in the file's generated-file notice so it does not invite accidental regeneration of framework-owned fields.
2. Mailbox: `SubstrateMailboxClient.defaultMailboxPath` is `chrysalis/System/Inbox/events.json`; `legacyMailboxPath` is `System/Inbox/events.json`. Existing reads fall back to the legacy file when the selected file is absent, while writes use the configured `mailboxPath`. Keep the default and documented compatibility behavior for this bounded repair. The two hybrid tests still look for writes at the legacy path. Status messages in `hybrid_orchestrator_transport.dart` also hardcode that legacy path, so merely changing the tests leaves misleading user feedback. Report the configured write destination, update stale comments, and retain the distinction between a queued message and an executed action.
3. Add focused regression coverage for the complete framework schema fields, actual default and custom mailbox write destinations, and preservation of existing legacy events when writing to the default mailbox. Use synthetic in-memory or temporary storage. Do not add a live consumer, change runtime layout, or treat buffering as cross-device delivery.

### Handoff back to Codex

Run the framework suite, gateway suite, Flutter analysis, and Flutter tests on the workstation using its configured development environment. Run the development privacy audit against all intended additions and changes. Record exact commands/results and the affected paths here. Preserve unrelated mobile work, plugin deletions, and generated CMake changes. Leave this implementation uncommitted for Codex review of the complete working diff; a source checkpoint follows successful review and the required pre-commit audit. Do not push or deploy as part of this first round trip.

The desktop context-read check is complete. A full implementation-to-review round trip, Antigravity hook execution, and a reviewed runtime deployment rehearsal remain pending.

## Beginner guide added on 2026-09-14

Added a reusable beginner architectural guide covering source/runtime ownership, application layers, local persistence, gateway limits, agent context hooks and handoffs, toolchains, Git, worktrees, validation, privacy, deployment, recovery, and a glossary. The developer index links to it and .gitignore allows this one new public document. Private workstation details and the browsable reading edition remain outside the repository. Checked repository links and Bash example syntax; the application suites were not rerun for this documentation-only addition. No application/schema changes, commit, push, or runtime deployment were performed.
