# Current engineering handoff

Date: 2026-10-19. Expanded review corrections cover all 227 GitHub candidate comments, including
duplicates. Separate frozen reviews accept the corrected implementation with no remaining confirmed
finding. Both complete Node 22.19.0/24.20.0 suites pass 175 cases: 169 passed, six optional/platform
skips and zero failures. TypeScript, source checks, both-architecture Nix evaluation, production
archive/Pi and synthetic Chromium acceptance pass. Fault injection verifies source-promotion
recovery; actual root/nonroot fixtures verify installation-proof permissions. Evidence stays external.

Ledger projection binds only the current authorized outcome. The installed-boot proof permits one
native-selected final-vault binding without granting system administration. Installer projection
waits for that boot. Source promotion keeps durable reviewed before-images and partial progress;
workspace deletion handles separate filesystems while preserving concurrent edits. The npm archive
contains runtime Nix rules/templates; use the reviewed Git flake for Nix builds.

Publish the reviewed source, require matching portable CI and pin the dotfiles consumer to that
public revision before merging. The synthetic-user VM prompt is the next acceptance handoff.
The native x86 image/VM/model-led loop remains unrun. Preserve the original dirty source baseline,
private vault, existing sessions and credentials. No npm release or live runtime promotion is included.

## Prior review handoff

Date: 2026-10-19. Review correction batch after published source 3db96019087bb1a635ef0c5d18a5cec006321119.
All 60 candidate findings were assessed; confirmed issues and independent review follow-ups are
corrected. Both complete suites on Node 22.19.0 and 24.20.0 pass 163 cases: 157 passed, six skips,
no failures each. Real
synthetic managed Chromium/password acceptance passes nine with one OS-account skip. Review
identities, full dispositions and logs remain external. The final source must receive matching
portable CI before merge and the dotfiles consumer must pin that published revision.

The Nix runner uses an immutable descriptor and pinned upstream FHS tree with the existing
sandbox and exact closure mounts. Native x86 VM execution is still pending. Earlier ARM package
acceptance predates this correction batch. Fresh production archive/Pi acceptance passes after
the corrections, with all nine skills, default built-ins, offline vault/doctor and MCP. Preserve the original live
checkout and all baseline file hashes; do not promote the trial/runtime or use personal accounts.

## Prior integration handoff

Date: 2026-10-18. NixOS integration implementation with separate frozen read-only reviews.
Branch chrysalis-nixos; base HEAD remains 3b6c579e5656bb5d491a7320d1b473286be742d0.
The original source checkout and all 210 baseline file hashes are preserved. Work is isolated.
Dependencies, synthetic fixtures, archives, logs, before-images and frozen manifests stay external.

The reusable package stays portable. The optional NixOS module owns integration, while native
NixOS images, upstream Pi/Home Manager, disko-install, Facter and pinned nix-agent do the work.
Read docs/nixos.md, nix/rules.md and chrysalis-system. Personal dotfiles consume the shared module;
publish their consumer lock only after pinning the actual published reviewed Git revision.

Node 22.19.0 and 24.20.0 complete suites each pass 146 cases: 140 passed, six optional/platform
skips, zero failures. All 23 system cases pass, including actual Pi direct/nested policy behavior.
Production TypeScript and whole-source checking are required. Locked root outputs, generated
target and both personal host toplevel derivations evaluate. Final package/archive identities and
independent review reports belong with the external candidate evidence, not private source files.

Recovery uses durable intent before privileged operations, exact stable device ancestry, bounded
mount-only recovery and a private copy-hash journal. Ambiguous privileged descendants block later
mutations until completion proof or reboot; close does not bypass that guard. A completed handoff
preserves later installed edits. Mutable Pi auth/settings remain outside Nix store ownership.
Do not broaden these controls into claims of whole-process isolation or complete machine auditing.

The x86 image/VM gate remains outstanding. The operator requested merging the implementation
as a prototype; merging its manual workflow registers the default-branch dispatch prerequisite.
Keep that remaining acceptance requirement explicit. Runtime/provider authentication, Obsidian
UI, physical hardware and firmware trust remain separate checks.

The user has authorized committing, pushing and merging the reviewed Pi baseline, NixOS
integration and realigned dotfiles as prototypes. Keep the baseline and NixOS implementation in
separate commits; the dotfiles consumer must pin the actual published Chrysalis revision. The ARM
package build and production archive/Pi acceptance passed after the final frozen read-only review.
External evidence retains their exact identities. The next handoff is a synthetic-user VM test.
No npm/distribution release or live runtime promotion is authorized here. Preserve the original
trial, active sessions, credentials and personal vault.

## Previous compatibility handoff

Date: 2026-10-15. Modular Pi compatibility implementation, with separate frozen read-only review.
Branch main; unchanged base HEAD 3b6c579e5656bb5d491a7320d1b473286be742d0. Prior dirty work is
preserved. External initial/final hash manifests and before-images identify the uncommitted build.
Run the context script for current source identities.

Pi >=1.2.0 <2 owns MCP/codemode and user server configuration; Node >=22.19.0 follows Pi's engine
floor. The package source gate checks exact identity/schema and rejects configured namespace
overrides. Direct/nested external tools use native scopes and configuration fingerprints; unrelated
resources remain available. Read docs/compatibility.md for grants and the trusted-host boundary.

Memory and fixed-role children use the parent's public model runtime. A bounded private stream
route avoids provider imports in children, scrubs ambient auth variables and uses task-local auth.
Explicit model choices, budgets, workspace isolation, writer leases and all vault approval/CAS
contracts remain. Private provider adapters and bespoke provider wrappers are not used.

Latest full suites on Node 24.20.0 and 22.19.0: 123 cases, 117 passed, six optional/platform skips.
Actual native approval/source/reload/late-registration and synthetic provider routing pass.
Normal Pi CLI/production archive startup retains default built-ins without duplicate warnings.
Both global add-ons load every original resource in either order; eight pi-antigravity chat models
register. Pi diagnosed a synthetic duplicate tool; removing only its colliding resource cleared the
error and preserved unrelated packages/built-ins. Google authentication/inference, live quotas and background service acceptance remain
unverified and user-controlled.

Deliver through the private archive and ordinary local Pi installation. Back up trial settings,
remove only its two known built-in exclusions and preserve auth, state and unrelated settings.
The user starts a fresh plain Pi session for native onboarding/login. Active sessions were not
driven or reloaded. Preserve working Pi authentication, global packages, personal files and conversations.
No commit, push or npm publication occurred.

## Historical handoff

Date: 2026-10-12. Role: assistant integration implementation with separate frozen read-only review.
Branch main; unchanged base HEAD 3b6c579e5656bb5d491a7320d1b473286be742d0. Changes remain
uncommitted. Run `node Development/scripts/agent_context.mjs show` for current dirty identities.
Earlier conversation-addon changes are preserved. No personal data or dependencies belong in source.

The package now integrates optional native model/capability setup, adaptive teaching/questions/
quizzes, private lesson/visual work, wrapped pinned Blackhole, fixed pinned interactive specialists,
controlled persistent Chromium research and isolated Linux workspace execution. Domain code remains
portable; Pi adapters live in extensions. Exact native vault review and individual atomic-note
vetting are unchanged. Native source-copy promotion and image-original adoption remain separate
from record adoption and Git publication. Read docs/assistant.md and STATUS.md for controls/limits.

Main dependency-free startup fencing and the minimal programmatic child host fail closed if
required policy does not load. Children have fixed roles/routes, bounded lifetime and no approvals.
Memory reservations cover actual streams with explicit routes and no fallback. Namespace snapshots,
aggregate resources, host IPC/network denial, bounded export and revision checks protect host/vault.
Live or uncertain worker leases persist until verified exit/reconciliation. Native workspace review
is required before execution. Optional features default off; the user selects models and scope.

Minimum Node 22.18.0 Linux ARM64 retained suite: 95 tests, 91 passed, four skipped, zero failures.
Subsequent five-case startup/child/research delta passed. Strict production TypeScript and complete
physical-source checking pass. Actual synthetic Chromium verified cookie persistence, page actions
and pinned adblock loading. Actual child SDK tests include required-extension failure before model.
Fresh production-only archive and managed live source each loaded eight skills, completed synthetic
offline onboarding/doctor and denied arbitrary vault reads without model calls. A narrow teacher
conversation left its synthetic vault unchanged; an isolated worker task physically succeeded with
four turns and 4,270 provider-reported tokens. Costs and measurement limits are documented.

Final separate frozen review found no remaining material issue in the examined delta within the
trusted host boundary. Earlier findings were corrected with targeted regressions. External recovery
retains the initial dirty snapshot/diff, final manifest, launcher before-images and evidence. The
managed source checkout is the runtime package, with exact dependencies in an external private
prefix; general Pi settings/authentication/sessions are preserved. No Git/npm publication occurred.

Gemini authentication and real YouTube ingestion are deliberately deferred. Browser uploads,
downloads/arbitrary JavaScript, unreviewed custom child providers and stale policy resume are excluded.
Physical Obsidian rendering, wider teaching scenarios, native memory-model quality, authenticated
Google integration and other OS execution runners require separate acceptance. Source promotion
checks privacy/CAS but not the full suite; publication still requires the documented full gate.

## Fresh installation trial and background provider follow-up

The user requested an interactive fresh package/onboarding trial and retained external provider
models for main, memory and specialists. Private trial configuration, copied login credentials,
installed production package, empty state and recovery remain external. Engineering created no
vault. The normal live source runtime, personal vault and existing session history are retained.
Named standalone research/memory/subagent add-ons were removed; package-owned engines remain.

Generic custom-provider adapters bind private entry/dependency-tree hashes, native model selection,
selected memory API/stream checks and child registration without additional tools, commands, hooks
or image models. Unreviewed routes, missing streams and drift fail closed. Child launch propagates
the Pi authentication/session directory. Provider code remains trusted host code. Separate frozen
review identified missing-stream fallback and incomplete-tree defects; corrections were accepted.
A nested provider Proxy compatibility issue was also corrected and regression-tested.

Minimum Node 22.18.0 complete suite: 98 tests, 94 passed, four skipped, zero failures. Three adapter
regressions and actual Pi 1.1.0 installed-provider/native-picker/child loading passed. The tested
provider exposed eight chat models; a native choice assigned one to all seven background routes.
Child read-only policy and absent extra provider tools passed without model requests. Fresh package
installation and actual terminal startup passed without saving a conversation or creating a vault.
Registration/metadata compatibility does not establish live custom-model quality or quotas. No
Git publication occurred. External manifests identify the current dirty implementation.

## Saved-password follow-up before the fresh trial

The optional onboarding password-export inbox and native setup/import/status routes are implemented.
Password records stay encrypted outside source/vault; append/update uses stable account identity,
raw source/store revisions and native confirmation. Saved-login selection binds exact HTTPS origin,
selectors and encrypted-store revision, then validates held primary-frame input handles. No model
password values, inventory export or child credential capability is added. Ordinary ingestion and
workspace snapshots refuse recognizable supported exports. Bitwarden sync remains a future native
read-only adapter; nothing was installed or connected. Docs/passwords.md describes limits.

Minimum Node complete suite: 107 cases, 102 passed, five skipped, none failed. Nine password cases
also passed separately with actual WSL DPAPI and actual pinned Chromium synthetic fields/echoes.
Strict TypeScript, whole-source checking and actual production-installed Pi native import/loading
passed without model requests. Separate frozen reviewer findings were corrected: exact approval
binding, JSON urls detection, bounded secret-free literal redaction and unique OS key references.
Native Linux/macOS protection, actual password exports and real-account login remain untested.

The fresh installed trial receives this candidate while preserving its separate copied auth,
provider declaration and empty onboarding state. Engineering does not create a trial vault or
import real passwords. The normal source runtime remains live; existing private state and sessions
remain outside source. External snapshots/manifests/logs identify the dirty implementation.
No Git or npm publication occurred.

## Onboarding control follow-up

Date: 2026-10-14. Role: native onboarding UI implementation with separate frozen read-only review.
Base branch/HEAD remain main / 3b6c579e5656bb5d491a7320d1b473286be742d0; no publication.
Prior assistant/provider/password changes are preserved. The scoped delta adds a windowed model
picker with provider/model type-ahead and a portable English-folder/directory-completion control.
Completion uses native input insertion so later typing appends at the end. Folder metadata discovery
is bounded, respects redirected Windows and Linux XDG settings, and omits links/control names.
Only new-vault parent selection changes; exact setup review, source/vault separation, credentials,
individual atomic-note vetting and all record approval/CAS gates remain in place.

Full suites on Node 22.18.0 and 24.20.0: 120 tests, 114 passed, six optional/platform skips, none failed.
SDK 1.0.4 TypeScript and actual Pi 1.2.0 offline tmux controls passed at 24 and 14 rows. WSL resolved
native Documents; other OS mappings use synthetic fixtures, not physical Mac acceptance. External
frozen manifests, before-images and native terminal evidence identify the dirty change. Promote only
the reviewed files with revision checks, preserve trial state/auth/provider declarations, then reload
after closing active dialogs. Do not reset onboarding or infer Git publication from these checks.
