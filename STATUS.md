# Implementation status

The Pi package candidate implements one portable Python domain core, seven canonical skill families,
strict Markdown schemas and a thin Pi adapter. Pi is the sole maintained harness target.
It has not been adopted as a personal
runtime. The [behavior matrix](tests/specs/behaviors.md) identifies each procedure, deterministic
test and remaining conversation/provider/UI boundary.

Verified on Windows in external isolated fixtures:

- The complete retained suite passed 78 tests with ordinary deep Windows scratch paths,
  including independent-review regressions for
  read/revision races, provider configuration, quarantine, apply-time dependencies, package
  ancestry, native TaskNotes fields, planning limits, original extraction, Daily receipts,
  long-path I/O and lock isolation under conflicting explicit/environment state bindings.
- A separate read-only review accepted the implementation after all 13 findings were repaired.
  The final working-tree identity and detailed receipts are held outside source. The whole-source
  privacy/resource check passed 117 files; the exported npm package contains 98 verified files.
- Core validation, raw revisions, exact approval, resumable CAS writes, plugin preservation,
  daily planning/staging/learning, pauses, checkpoints, horizons, reciprocal links and ingestion.
- Metadata-only discovery, selected synthetic PDF parsing, image/opaque deferral, and vault
  relocation retaining original bytes, relative links and record identities.
- Owned package install/update/remove/rollback, collisions and injected-failure recovery.
- Real Pi package loading, seven skills, extension registration, nested tool
  pipeline and denied bypasses. Pi exercised 12 synthetic workflow/tool calls, including
  task, ingestion, links, planning, audit and approved application. These used synthetic assistant
  calls; no model conversation was asserted.
- Python x64 interpreter launch from Node ARM64 on the Windows host. Tested Pi 1.0.4 with Node
  24.20.0.
- Optional pi-hermes-memory 0.9.10 native SQLite on Node ARM64, durable-content JSON export/import
  across 40 synthetic rows (29,830 characters), and combined extension loading without loader
  errors. This does not verify model learning or permission coexistence; capped Markdown exports
  are not complete migration backups.

External acceptance remains required for real model conversations, onboarding research, semantic
judgment, OCR/vision, authenticated providers, TaskNotes/Maps UI and Calendar sync, live host launch,
job scheduling, streaming/offline conflicts and backups, and mobile. No credentials or real data
were used, no live profile/job was configured, and no storage was moved. Health-data integration
is deferred until its exact app/API, authorization and data scope are selected.

Installation/configuration/authentication/availability/verification are distinct capability states.
Normalized fixtures and unavailable-state tests do not prove authenticated operation. Local CAS
locks are cooperating-writer protection; distributed concurrent editing needs separate acceptance.
See [setup](docs/setup.md), [storage](docs/storage.md) and [test coverage](tests/specs/behaviors.md).
