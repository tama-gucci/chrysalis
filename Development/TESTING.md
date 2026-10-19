# Verification

Keep dependency installations, fixtures, logs and recovery outside source. Copy public source into an external workspace and run `npm ci --ignore-scripts --legacy-peer-deps` there. Set TEST_SCRATCH to an absolute external directory.

Run the following in the external workspace with its installed dependencies:

```text
npm run typecheck
npm test
node Development/scripts/check.mjs --root <absolute-source-checkout>
```

Replace the root placeholder with the source checkout. Run the retained suite on minimum Node 22.19.0
when verifying the supported runtime floor. Typecheck covers production src/extensions; tests execute
through Node. Run `node Development/scripts/agent_context.mjs show` from source.

Do not connect reusable dependency directories through junctions when running package managers. Tests use the pinned TaskNotes model and actual Pi SDK with synthetic assistant calls. They cover onboarding, protected fields, timezone/DST, originals/PDF limits, provider policies, knowledge workflows, planning/learning/pauses and approval/CAS recovery.

The checker scans all non-Git source, including ignored/untracked content; rejects runtime/generated locations, machine paths and credential patterns; validates structured data and links; and verifies pinned third-party bytes. Review prose/upstream code separately.

Freeze an external SHA-256 manifest and invoke a separate read-only reviewer for substantive changes. Also pack the source into an external archive and check actual installed-package loading, offline
onboarding and doctor through Pi. Git/npm transport acceptance does not publish an npm release.
Native loading/tool calls are separate from model conversations and desktop rendering. Physical Obsidian interaction, other platforms and authenticated integrations have explicit acceptance boundaries in STATUS.

The current candidate adds knowledge.test.ts, documents.test.ts and native review cases. They
exercise rejection/edit/tampered receipt boundaries, body/alias retrieval, unchanged read-only
state, captured-payload fidelity, index/journal, concurrent evidence, no-material and snapshots.
These cases now run in the complete suite after the guardrail/skill review phase. Do not skip existing cases or treat static checks as runtime proof.

Document cases cover operator-only root selection, metadata-only scans, excluded/depth-limited
files, separate copy approval, stale sources/authorization, raw provenance, recovery, collisions,
links/traversal and byte/cancellation limits. A combined source/note case retains per-note vetting.
Native tests exercise canceled/edited/declined scope and copy reviews. A narrow synthetic teaching/onboarding dialogue has model acceptance; broader early optional offers,
skip/defer, evidence quality and grounded roadmap/project/atomic-note scenarios remain separate checks.
Additional authored cases reject unsafe/drifted TaskNotes/Dataview settings for Markdown originals
and source/destination replacements by nonregular files. Plugin behavior and POSIX special-file
acceptance need platform/UI acceptance; source inspection is separate from physical Obsidian acceptance.

Decision-led onboarding changes are skill instructions, native handoff text and extensible
checkpoint fields, without a new operation or interview engine. The behavior matrix records
pending model scenarios for dependency order, partial replies, changed answers, shared constraints,
missing evidence, neutral recommendations and recap/approval separation. Static links, YAML and
TypeScript checks do not prove those conversational outcomes. Deterministic/native-control acceptance now runs; broader model conversation quality remains pending; STATUS records the narrow accepted dialogue.

Provider tests and codemode.test.ts exercise protected synthetic storage, native activation, OAuth loopback/refresh, scope/HTTP bounds, omission/freshness and shared-service result reduction. The actual Pi test reaches production stdio through codemode and enforces nested gates. The benchmark uses chars/4 estimates and preserves failure/coverage semantics; no live-account or billed-token claims follow. Native Health/Maps evidence uses a custom in-memory viewer without external-editor export.

Retain platform optional dependencies: the pinned tsx loader needs its esbuild platform package. The MCP launch uses an absolute package-resolved loader, package tsconfig and disabled transform cache; bare native type stripping cannot execute TypeScript inside an installed node_modules package. No user build or shell launch is needed.

Assistant acceptance adds namespace/Windows-interop/host-IPC denial, bounded stdin/output, cancellation,
aggregate resource prerequisites, worker leases, selected memory stream lifetime, encoded-SVG refusal,
artifact adoption and fixed child SDK roles. Optional browser acceptance uses
CHRYSALIS_BROWSER_ACCEPTANCE_STATE pointing to an external installed browser pack fixture. It checks
synthetic-cookie persistence, page interaction and pinned adblock loading; it never reads real cookies.
Use the package dependency resolver for actual live-checkout acceptance. Separate real model dialogue,
Gemini authentication/video work and physical visual inspection remain explicit boundaries.

Password acceptance adds bounded CSV/JSON normalization, append/update/no-deletion identities,
ambiguous matching refusal, encrypted stores, declined/stale/changed plans, corrupt ciphertext,
ordinary-ingestion/workspace exclusions and exact origin/held-field redaction guards. Set
CHRYSALIS_PASSWORD_DPAPI_ACCEPTANCE=1 only for explicit synthetic OS-account acceptance in an
external fixture. The optional browser fixture also exercises synthetic saved-login fields and
echoed values with no real accounts/cookies. Native installed-package checks separately exercise
setup/import, encrypted external state, origin/revision review and headless refusal. These controls
do not prove secrecy against arbitrary transformations by an approved trusted website.

## Modular Pi compatibility acceptance

Use Pi SDK/CLI 1.2.0 and Node >=22.19.0. The older SDK floor no longer describes the current
public model-runtime contract. Test direct calls, actual codemode descendants, native proposal
review, per-note/batch approval and stale revisions. The retained native cases include actual
reload, late tools, configured same-schema namespace overrides, MCP grant configuration drift,
legacy skill layouts and fixed child stream cancellation. Hints alone cannot authorize a call.

Pack/install production-only into an external prefix. Separately invoke the normal Pi CLI with
default built-ins and isolated home/auth/state. Native /mcp and SDK source calls must work without
built-in exclusions. Load the actual independently installed add-on package paths through their
ordinary manifests in both orders; do not create redundant local copies or patch their contents.
Offline registration/catalog acceptance is separate from real authentication/inference/quotas.
Private test probes, stream fixtures and recovery stay outside physical source. Complete latest
evidence and scope are recorded in STATUS.

## NixOS prototype

Use the locked flake. Local Nix evaluation is separate from a build or boot. The portable package
and module export both Linux architectures; the installer is x86_64 UEFI. The GitHub Actions
workflow runs the retained suite outside source, a NixOS graphical module/reboot test, builds the
native raw image, and boots that image with disposable target/sentinel disks. Test images, logs,
firmware state and provider-free fixture vaults remain in external runner temporary storage.

nix/tests/raw-boot.py is CI tooling only, not a runtime Python dependency. Its native fixture
approvals stand in for human dialogs. The real installer primitives, fact discovery, target boot,
vault setup and nix-agent MCP operations execute in the VM. Portable SDK tests separately exercise
Pi guards. This harness does not prove a real-model installation conversation, OAuth/browser
login, Obsidian GUI behavior, Secure Boot enrollment or physical hardware support.

The image job is manual-only and requires a registered default-branch workflow before feature-ref dispatch. See docs/nixos.md for the bootstrap prerequisite. The raw harness kills the actual handoff helper after a durable copy, power-cycles the USB and resumes with changed source state; target-only edits must remain protected. It also asserts actual Pi pane startup, mutable account state and exclusion of the USB transfer journal. These are authored acceptance cases until the x86 runner records a passing run.
