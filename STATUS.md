# Capability status

Reviewed against source on 2026-09-12. This file is the implementation reference; design aspirations belong in Development/ROADMAP.md. Test counts are run results, not permanent completion percentages.

| Capability | State | Evidence / limitation |
| --- | --- | --- |
| Markdown task and project framework | Implemented | Schemas, templates, agent runbooks, runtime checks |
| Calendar feed import | Implemented | Python parser, recurrence regression tests; requires configured private feed |
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
| Offline mailbox | Local queue | No automatic consumer or cross-device delivery guarantee |
| Audio/PDF knowledge ingestion | Agent-assisted workflow / planned automation | No ingest_payload.py pipeline; capture does not imply transcription or synthesis |
| Wear OS, QR pairing, evening triage UI | Planned | Dedicated implementations absent |
| Gateway installer / standalone plugin distribution | Planned | No release packaging pipeline |

## Validation boundaries

Python framework tests cover scripts, file conventions, and synthetic scenarios. Gateway tests use explicit simulation and mocked failure cases. Flutter tests exercise application logic and widgets. Static analysis and an APK build do not replace a phone-to-vault-to-agent rehearsal.

Use the live diagnostic output to judge runtime state. Zero schema errors can coexist with overdue tasks, missing UI dependencies, stale calendars, and incomplete integrations.

## Verification on 2026-09-12

- Framework: 132 tests passed.
- Gateway: 11 tests passed using explicit simulation and controlled failure cases.
- Mobile: Dart analysis passed. Flutter tests could not start because the Windows ARM64 native C++ compiler toolchain is missing. No new APK was built or tested on a phone.
- Repository privacy scanner passed; this does not replace review before publishing.
