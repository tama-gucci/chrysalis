# Capability status

Reviewed against source on 2026-09-16 (B00 and B01 local checks; broader review remains dated below). This file is the implementation reference; design aspirations belong in Development/ROADMAP.md. Test counts are run results, not permanent completion percentages.

| Capability | State | Evidence / limitation |
| --- | --- | --- |
| Markdown task and project framework | Implemented | Schemas, templates, agent runbooks, runtime checks |
| Calendar feed import | Implemented with correctness gaps | Timezone/recurrence and invalid-refresh preservation defects reproduced; see the 2026-09-15 review |
| Note/project/task linking | Implemented | Tag and wikilink matching; not a semantic inference engine |
| Runtime deployment | Implemented | Allowlist, preview, snapshots, local-edit detection, rollback |
| Obsidian task plugin | Vendored prototype | Compiled bundle; full plugin source and release pipeline absent |
| Dataview dashboard | Implemented, dependency required | Install/enable Dataview in each vault |
| Android share intake | Implemented prototype | Kotlin receiver and Dart staging; physical-device rehearsal required |
| Local mobile task persistence | Implemented | SQLite cache and local Markdown provider |
| Mobile schedule view | Implemented preview | Does not establish persisted calendar reservations or conflict-free external scheduling |
| Google Drive mobile provider | Library only | Authentication and startup wiring unfinished |
| Android Health Connect | Native bridge present | Reads only when available and permission is already granted; no fabricated startup telemetry |
| Native calendar export | Interface/coordinator only | Android calendar handler and application integration unfinished |
| Gateway Antigravity adapter | Prototype | Real process launch path; deployment-specific CLI compatibility still needs verification |
| OpenClaw / Hermes adapters | Unimplemented | Return unavailable |
| Direct cloud/on-device AI | Unimplemented | Returns unavailable |
| Offline mailbox | Local queue with preservation defect | Malformed contents can be overwritten; no automatic consumer or cross-device delivery guarantee |
| Audio/PDF knowledge ingestion | Agent-assisted workflow / planned automation | No ingest_payload.py pipeline; capture does not imply transcription or synthesis |
| Wear OS, QR pairing, evening triage UI | Planned | Dedicated implementations absent |
| Gateway installer / standalone plugin distribution | Planned | No release packaging pipeline |
| Background framework development | Local validation implemented; runner planned | One-command local checks and candidate privacy audit verified in a fresh worktree; scheduler, dispatcher and hosted CI remain pending |

## Validation boundaries

Python framework tests cover scripts, file conventions, and synthetic scenarios. Gateway tests use explicit simulation and mocked failure cases. Flutter tests exercise application logic and widgets. Static analysis and an APK build do not replace a phone-to-vault-to-agent rehearsal.

Use the live diagnostic output to judge runtime state. Zero schema errors can coexist with overdue tasks, missing UI dependencies, stale calendars, and incomplete integrations.

## Verification on 2026-09-12

- Framework: 132 tests passed.
- Gateway: 11 tests passed using explicit simulation and controlled failure cases.
- Mobile: Dart analysis passed. Flutter tests could not start because the Windows ARM64 native C++ compiler toolchain is missing. No new APK was built or tested on a phone.
- Repository privacy scanner passed; this does not replace review before publishing.

## Android device verification on 2026-09-13

- Built and installed the current debug APK on a physical Android device.
- Fixed duplicate local storage initialization that caused an Android file watcher assertion during startup. Added and ran a standalone regression check for repeated initialization and file persistence.
- Captured a synthetic task through the app UI; verified its Markdown file and its reappearance after a full app restart.
- Delivered synthetic text through Android ACTION_SEND; verified inbox contents persisted after restart. Image, audio, PDF, and multi-file shares remain untested on-device.
- Fixed the timeline heading overflow and visually checked the corrected layout on-device. Changed Dart files passed analysis.
- Verified phone-to-gateway WebSocket connection and HTTP command/response through ADB USB forwarding. The actual gateway used an intentionally unavailable backend and returned its expected error on the phone; no agent action or simulation was executed.
- Remaining: Obsidian/task synchronization, production connection setup and authentication, connection-state updates after disconnect, real agent execution, and Health Connect/calendar permission workflows. The earlier desktop Flutter test toolchain limitation remains.

## Engineering review on 2026-09-15

Reviewed `main` at `cfa92e8` plus the preserved uncommitted changes; this is not a released snapshot. See [the complete review](Development/REVIEW-2026-09-15.md) for evidence, source references and priorities.

- Framework: 133 passed, 3 failed out of 136. Failures concern the current task schema.
- Gateway: 11 passed with 2 dependency deprecation warnings after an approved run outside the restricted sandbox; fixtures use explicit emulation and controlled failures.
- Flutter analysis: no issues. Flutter tests: 101 passed, 2 failed because hybrid transport expectations still use the legacy mailbox path.
- Standalone local-storage initialization regression: passed.
- Synthetic probes reproduced calendar YAML corruption, loss of cached commitments on invalid HTTP 200 input, timezone/recurrence errors, doctor false-success results, malformed mailbox overwrite, archived-task scheduling, and missing start time on direct completion.
- Doctor success alone is not a runtime-readiness gate. Calendar import is implemented with known correctness gaps; mobile calibration remains a preview without verified persisted planning.
- No new APK build, physical-device test, real backend execution or personal-vault inspection occurred in this review. No application repair, persistent automation, commit, push or deployment was performed.

## B00 baseline verification on 2026-09-16

The local checkpoint containing this entry restores the task schema's framework fields and corrects mailbox destination notices and tests while preserving the earlier working state. New regression coverage protects framework metadata, plugin annotations, configured destinations and legacy-event preservation.

- Framework: 138 passed; gateway: 11 passed with two dependency deprecation warnings.
- Flutter analysis: no issues; Flutter tests: 108 passed; affected calendar fixture tests passed again after synthetic-address normalization.
- Standalone storage initialization regression: passed.
- Independent staged-candidate review: no actionable introduced B00 findings. Complete candidate privacy audit and staged whitespace checks passed; details in [the handoff](Development/HANDOFF.md#b00-starting-version-repair--2026-09-16).
- This establishes a local source test baseline. The earlier calendar, diagnostic, malformed-mailbox, scheduling and synchronization findings remain open. No new device rehearsal, real backend execution, hosted CI, background routine or runtime deployment was performed.

## B01 local checks verification on 2026-09-16

`python3 Development/scripts/check.py` now runs all required local checks with individual logs and a nonzero overall result on any failure. Setup installs the tested Python pins and enforces the mobile dependency lock. Candidate privacy scans both staged blobs and tracked/eligible-untracked working files. A separate trusted-controller invocation rejects candidate replacements of its required policy.

- Fresh worktree setup and full checker passed: framework 152, gateway 11 (two dependency deprecation warnings), Flutter 108, clean Flutter analysis, standalone storage regression and candidate privacy/stability checks.
- An intentionally failing framework test produced overall exit 1 while remaining suites ran. A replacement candidate checker was rejected before test execution. Synthetic failures were removed and the final fresh run passed.
- Separate review identified and verified the repair of a credential-helper quarantine omission; final staged review and `/audit-dev` passed before the local checkpoint.
- B01's local milestone is complete. Hosted GitHub checks are unimplemented/unverified and remain pending; no background execution, integration service, publishing or runtime deployment was enabled.
