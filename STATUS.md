# Implementation status

## Current modular Pi compatibility (2026-10-15)

Current requirements: Pi >=1.2.0 <2 and Node >=22.19.0, following Pi's public runtime API and
declared engine floor. Pi owns default MCP/codemode and user server configuration. chrysalis
registers only its source server. Direct and nested calls share exact package identity or native
scoped grants; configured same-schema overrides and MCP configuration drift fail closed.
Private provider adapters were replaced by a bounded route through the parent Pi model runtime.

The latest complete suites passed on Node 24.20.0 and 22.19.0: 123 cases, 117 passed, six
optional/platform skips, zero failures each. Native setup, individual note vetting, final approval,
stale revisions, actual source calls, late registration, actual reload, misleading/missing metadata,
configured namespace overrides, legacy skill roots and child stream cancellation are covered.
A 22.18.0 run also passed, but that version is below the supported host engine floor.

A fresh production archive loaded eight skills. Normal installed Pi CLI startup/exit retained
builtin:mcp and builtin:codemode with empty stderr and no duplicate/conflict warnings.
Native /mcp, direct/nested source calls and denial of arbitrary vault writes/model approvals passed.
Both actual global add-ons loaded all original resources in either package order: six quota
extensions, three pi-antigravity extensions and eight pi-antigravity chat catalog entries. No redundant
local add-on copies, provider-specific wrappers or paid model calls were used. A genuine duplicate
tool was diagnosed by Pi; removing only that resource cleared the error and preserved the loadout.
Authenticated Google
inference, live quotas and real background service acceptance remain user-controlled and untested.

Separate frozen read-only review accepted fixes to effective MCP identity, grant drift, legacy
skills, namespace-free resource grants, child auth-environment inheritance and documentation.
No remaining material implementation finding was reported. External before-images/manifests identify
the initial dirty tree and final candidate; branch main/HEAD remain unchanged and uncommitted.

See [compatibility](docs/compatibility.md) for the matrix, resource selection, generic provider
strategy and precise limits. Config-file fingerprints do not prove resolved substitutions,
executable bytes or all in-memory transport behavior. Model hooks cannot sandbox native extensions.
Physical native Windows/macOS, other Pi versions, live accounts and broader onboarding remain
untested. Existing per-note/batch review, CAS, native-only Health/Maps and read-only capture remain.
No personal-vault writes or Git/npm publication occurred.

Historical verification below records its original build.


Version 2.0.0 is a self-contained Pi package with a portable TypeScript/Node core, eight canonical
skill families and 36 reviewed vault operations. Onboarding prepares a user-named Obsidian vault
with pinned TaskNotes 4.13.8, Dataview 0.5.68 and automatic named-timezone setup. Original files
belong inside Attachments/Originals. Optional life-document selection/copies, chosen roadmap
work, knowledge compilation/search/lint and individual approval of every new atomic note are
implemented. Conversation uses scoped decisions, partial replies, skip/defer and recap confirmation;
model conversation quality remains a separate acceptance boundary.

The source integration implementation adds a bundled six-tool stdio MCP server,
shared provider service, native credential onboarding and Pi-owned built-in codemode/MCP.
Google Tasks is one-way read-only capture: metadata first, selected detail envelopes, account/list
identity and existing safe local reconciliation. Native activation requires matching external
profile and approved Memory bindings. Reconnect and local disconnect are native-only. Credentials
are OS-protected outside vault/source; Windows uses CurrentUser DPAPI. macOS Keychain and Linux
Secret Service paths are implemented but have not received platform acceptance.

Google Health reads linked identity and processed sleep for eligible existing projects. Google
Maps reads minimal selected place/route context with native attribution. Both display evidence in
an in-memory read-only component without external-editor export; neither returns provider content
to model/session/vault records. MCP and ordinary operations return native-review readiness only.
Manual wake/energy replies and independently selected travel allowances remain authoritative.
Health project availability, live OAuth/account/scopes, Maps billing/display and provider-required
privacy disclosures need separate user-controlled acceptance. No account was connected in this run.
See [source setup](docs/integrations.md) and [design](docs/integrations-implementation-plan.md).

Prior isolated Windows baseline acceptance used synthetic data and Pi SDK 1.0.4:

- The complete 74-case suite passed on minimum Node 22.18.0 with no skips. A subsequent
  13-case provider delta verifies sanitized cleanup-failure reporting and retry.
- A production-only npm archive installation loads all seven baseline skills, prepares a vault with
  networking disabled, passes doctor and reaches bundled stdio through codemode with Pi's
  replaceable built-ins present. The pinned package-resolved tsx loader supports installed
  TypeScript without a build step; transform caching is disabled. All nine flowcharts render.
- Production TypeScript checks pass. Tests cover approvals, per-note review, CAS/recovery,
  document scope/copies, provenance/fidelity, plugin contracts, timezone/DST and daily planning.
- Actual Pi reaches the production bundled stdio server through upstream codemode. Its model
  helpers are disabled. Nested arbitrary reads are denied; effective registration/schema/origin
  overrides fail closed. Source activation, masking, native display and protected storage have
  synthetic native-control acceptance, not physical terminal rendering or live account proof.
- Provider cases cover strict input/scope bounds, partial Tasks details, stable identity,
  credential reflection, omission/freshness, HTTP destinations/limits, lossless concurrent daily
  budgets, in-flight local disconnect and protected refresh rotation. OAuth loopback tests use
  synthetic token exchanges and no browser/account, proving state, PKCE and granted-scope checks.
- Separate frozen read-only review identified refresh/disposal and malformed-import diagnostic
  defects; both were corrected and accepted. Regression cases cover disconnect during refresh,
  reconnect during a credential write and secret-free native import notifications.
- Codemode measurements use the shared Tasks service with synthetic MCP-shaped wrappers and
  actual Pi orchestration. Reduced results retain equal coverage/provenance/failures. Pi's
  chars/4 estimator includes schema, discovery, script, calls and model-visible results;
  it is not billed-token measurement. See [measurement method](docs/integrations-benchmark.md).

Physical source privacy/resource validation passes with no findings, including ignored/untracked
content, public syntax, links and pinned asset checks. The operator removed the previously empty
formatter cache after automated deletion was blocked; the checker was not weakened. No personal
data was created in source. Reviewed implementation identities and publication evidence have
external SHA-256 manifests. Git publication does not establish an npm release, live account
acceptance or personal-vault adoption.

Physical Obsidian/community-plugin rendering, terminal interaction, authenticated Google accounts, other operating systems/devices and OCR/vision remain unverified.
The supported Pi range is not a claim that every version was tested. Local CAS coordinates
cooperating writers and cannot provide a distributed transaction or eliminate every editor race.

## Reviewed conversation add-ons (2026-10-11)

An optional external host policy admits exactly five bounded Ketch research tools, current-session
recall and structured questions. Exact origin and definition checks reject overrides/drift. No
companion can approve records; general executors and child agents remain excluded. Onboarding
uses generic, bounded queries, primary citations and user choices before native record review.

Typecheck passed. The complete 76-test suite ran on Linux ARM64 with the pinned Pi SDK: 73 passed,
3 platform-specific cases skipped and none failed. New tests cover absent policy, definition/origin
drift, duplicate/forbidden tools and actual host calls with reactivated write/shell tools still
blocked. Existing per-note approval and native onboarding cases passed. Whole-source checking
passed with no findings. Separate installed Pi 1.1.0 acceptance loaded the eight-skill life
loadout and seven companions, checked exact registrations, called actual session recall and
returned two results from a generic live Ketch search. Final-path loading, general-profile
add-ons and refusal to export memory into source also passed. These checks made no model calls.
The frozen source review found no material approval bypass. No new billed model-conversation,
interactive questionnaire rendering or authenticated-browser acceptance is claimed.

## Assistant integrations (2026-10-12)

Native optional setup/model routes, teaching/questions/quizzes/capture/diagrams, exact image-original
adoption, wrapped memory streams, fixed specialist roles, controlled browser/search and Linux execution
are implemented. Source development uses a private copy and native revision-checked promotion.
Runner prerequisites have a native tmux setup path. Private retention excludes memory, account
profiles, credentials and recovery. No optional worker/model route is enabled implicitly.

The complete retained suite ran on Linux ARM64 at minimum Node 22.18.0: 95 tests, 91 passed,
four skipped and none failed. Skips distinguish optional browser acceptance and platform-specific
cases. Actual Chromium separately retained synthetic cookies across restart, interacted with a
synthetic page and loaded pinned uBlock Origin Lite; no real account was used. Actual SDK child
loading and broken-required-extension refusal passed without model calls. Main and child startup
fences prevent the host from recovering a required-policy load failure into unrestricted built-ins.
Strict production TypeScript and physical-source checks passed during integration.

A synthetic teaching/onboarding conversation used the configured main model, explained finite
automata, offered two unadopted project directions and left decisions/record review open. Its
synthetic vault remained unchanged. A fixed worker completed a synthetic file task through isolated
write/Bash and the required completion extension; physical workspace verification passed. The
worker provider reported four turns and 4,270 tokens. These narrow cases do not establish teaching
quality across every scenario or a general token-saving claim. See the measured dependency and
tool-schema costs in [assistant measurements](docs/assistant-benchmark.md).

Independent read-only review identified memory-stream lifetime, external child imports, browser
action approvals/cancellation, entity-encoded SVG resources, host-copy growth and worker-lease
release defects. Corrections include lifetime reservations, pinned completion imports, anonymous
research, native interaction review, cancellation, encoded-resource rejection, bounded descriptor
reads and retention of uncertain/live worker leases. Earlier read-registration and hardlink
findings are corrected. A fresh production-only npm archive and the managed live-checkout loadout each loaded all eight
skills, completed synthetic offline onboarding/doctor, loaded memory with observations off and
blocked arbitrary vault reads, with no model calls. The managed launcher uses external exact
dependencies and the live source; general Pi settings, authentication and sessions are preserved.
Separate final frozen read-only review found no remaining material issue within the documented
trusted-host-extension boundary. The final five-case startup/child/research delta and whole-source
checker also passed after the complete suite. Public third-party notices are included in the archive.

Gemini Web sign-in and real YouTube requests remain deliberately deferred. Browser uploads/downloads
and arbitrary JavaScript are not exposed. The former private background-provider adapters were replaced by the public-runtime strategy described in the current compatibility section; stale child-policy resume remains unsupported. Source promotion runs public-source checks, not the full test suite;
publication still requires that suite. No Git or npm publication follows from this implementation.

## Historical private background provider adapters (superseded)

Native model setup admits authenticated custom chat providers only when an operator-maintained
private declaration verifies the adapter and complete dependency-tree identities. Child startup
loads only the declared provider registration; extra tools, commands, hooks and image models are
suppressed. Memory validates the selected provider/API before streaming. Code or declaration drift
pauses work without a fallback. Provider code remains trusted host code, outside execution isolation.
The complete suite passed at minimum Node 22.18.0: 98 tests, 94 passed, four skipped, zero failures.
Three adapter cases and actual Pi 1.1.0 registration/native-picker/child loading passed. The tested
external provider exposed eight chat models and native setup assigned one to all seven routes.
The child retained read-only controls with no extra provider tools. Fresh production installation
and actual terminal startup also passed. No model requests were made; these establish registration
and control compatibility rather than live provider quality, quotas or model outcomes. Separate
frozen review confirmed missing-stream and incomplete-tree fixes. Source privacy checking passes.

## Saved-password import

Onboarding offers a separate optional private CSV/JSON inbox with Later/Skip. Native setup/import
creates an organized AES-256-GCM password file in external per-vault state. New accounts append,
matching accounts update with retained local IDs, and missing entries remain. Ambiguous accounts,
changed source/store revisions and changed review plans stop use. Supported password exports are
refused by ordinary document extraction/copy, workspace snapshots and public-source checks.

Native saved-login selection binds the exact reviewed HTTPS origin, fields and store revision.
Held primary-frame inputs are revalidated before filling. Values remain inside the parent broker;
no inventory/export/child tool exists. Known representations are redacted with bounded literal
matching, protected page URLs omit queries/fragments, screenshots are refused and cross-origin
requests are blocked while credentials are in use. Trusted pages may react or transmit on input.
The OS protects a random key without a plaintext fallback; WSL uses Windows CurrentUser DPAPI.
Native Linux/macOS storage references are unique per private store but platform acceptance remains
separate. See [password formats and future adapters](docs/passwords.md). Bitwarden sync is a future
read-only snapshot boundary; no manager was installed, connected or synchronized.

The complete minimum-Node Linux ARM64 suite passed: 107 tests, 102 passed, five skipped, zero
failures. Skips cover two optional browser cases and three platform-specific cases. All nine
password cases separately passed with actual WSL DPAPI and pinned Chromium enabled, using synthetic
credentials. Chromium checks include held fields, echoed-secret redaction, screenshot refusal and
cross-origin refusal. Strict TypeScript and the complete physical-source checker passed. Actual
production-package Pi loading retained eight skills, synthetic offline onboarding/doctor and
blocked arbitrary vault reads; native password import, stale-origin review and headless refusal
passed with zero model calls. Separate frozen read-only review identified and accepted corrections
for exact origin/field approval, JSON export detection, secret-bearing regex diagnostics and
OS-secret key collisions across state roots. No real password export, browser account or personal
vault was used. Real login behavior and broader site transformations require user-controlled
acceptance; these checks are not a universal secret-exfiltration proof.

## Native onboarding controls

The background-model chooser now uses a terminal-sized scrolling window, paging and provider/model
prefix type-ahead. Resize preserves selection; unmatched text cannot confirm a stale selection.
New-vault parent selection advertises supported English folder phrases and directory-only Tab
completion, shows the resolved path, and accepts an existing parent before the separate setup review.
Windows known folders, WSL translation, macOS home folders and Linux XDG configuration are supported.
The chooser never creates a vault or approves records. Existing selected vaults bypass parent selection.

Both Node 22.18.0 and Node 24.20.0 Linux ARM64 complete retained suites passed: 120 cases, 114 passed,
six optional/platform skips, zero failures. Strict production TypeScript passed against SDK 1.0.4.
Actual offline Pi 1.2.0/tmux acceptance passed at 24 and 14 terminal rows: selection follow, paging,
provider/model prefix jumps, resize, native Windows Documents resolution through WSL, and Tab followed
by child-folder typing/completion. There were no model requests or personal vault writes. Windows,
macOS and Linux mapping/configuration cases passed synthetic checks; physical macOS and native Windows
terminal acceptance remain separate. The user's active trial session was not driven by these checks.
