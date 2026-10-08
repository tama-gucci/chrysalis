# Verification

Keep dependency installations, fixtures, logs and recovery outside source. Copy public source into an external workspace and run `npm ci --ignore-scripts --omit=optional --legacy-peer-deps` there. Set TEST_SCRATCH to an absolute external directory.

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
