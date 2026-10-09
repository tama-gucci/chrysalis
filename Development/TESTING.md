# Verification

Keep dependency installations, fixtures, logs and recovery outside source. Copy public source into an external workspace and run `npm ci --ignore-scripts --legacy-peer-deps` there. Set TEST_SCRATCH to an absolute external directory.

Run the following in the external workspace with its installed dependencies:

```text
npm run typecheck
npm test
node Development/scripts/check.mjs --root <absolute-source-checkout>
```

Replace the root placeholder with the source checkout. Run the retained suite on minimum Node 22.18.0
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
Native tests exercise canceled/edited/declined scope and copy reviews. Actual onboarding dialogue
still needs model acceptance for an early optional offer, skip/defer respect, evidence quality and
grounded roadmap/project/atomic-note suggestions.
Additional authored cases reject unsafe/drifted TaskNotes/Dataview settings for Markdown originals
and source/destination replacements by nonregular files. Plugin behavior and POSIX special-file
acceptance need platform/UI acceptance; source inspection is separate from physical Obsidian acceptance.

Decision-led onboarding changes are skill instructions, native handoff text and extensible
checkpoint fields, without a new operation or interview engine. The behavior matrix records
pending model scenarios for dependency order, partial replies, changed answers, shared constraints,
missing evidence, neutral recommendations and recap/approval separation. Static links, YAML and
TypeScript checks do not prove those conversational outcomes. Deterministic/native-control acceptance now runs; model conversation quality remains pending.

Provider tests and codemode.test.ts exercise protected synthetic storage, native activation, OAuth loopback/refresh, scope/HTTP bounds, omission/freshness and shared-service result reduction. The actual Pi test reaches production stdio through codemode and enforces nested gates. The benchmark uses chars/4 estimates and preserves failure/coverage semantics; no live-account or billed-token claims follow. Native Health/Maps evidence uses a custom in-memory viewer without external-editor export.

Retain platform optional dependencies: the pinned tsx loader needs its esbuild platform package. The MCP launch uses an absolute package-resolved loader, package tsconfig and disabled transform cache; bare native type stripping cannot execute TypeScript inside an installed node_modules package. No user build or shell launch is needed.
