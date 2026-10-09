# Operation API

Pi calls `chrysalis_operation` with `{operation, arguments}`. The adapter supplies initialized
vault/state roots and cancellation; model arguments cannot replace them. Read complete records
before editing. Paths are forward-slash vault-relative, except documents.prepare paths are relative
to the separately operator-selected external folder. Requests/results are capped
at 4 MiB; proposals contain 1–500 complete records. The [runtime contract](../contracts/agent-runtime.contract.md)
defines the approval and preservation rules.

Arguments marked optional may be omitted. Local `now`, `wake` and `not_before` values must carry
the configured IANA zone's date-correct offset, such as `2026-10-08T09:00:00+02:00` for Europe/Paris.
Use date-only `YYYY-MM-DD` for `date` and submission dates. Optional `timezone` must equal Memory.
Observation timestamps such as Calendar `observed_at` describe instants and may use another offset.

## Reads and validation

| Operation        | Arguments                                                                                                  | Result                                                                                   |
| ---------------- | ---------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| read             | path                                                                                                       | Complete document and raw-byte SHA-256 revision                                          |
| query            | collection; optional limit (default 50, 1–100), page (default 0), status                                   | Frontmatter/revision rows and next_page                                                  |
| schema           | type: task, project, zettel, source, system_state or daily_note                                            | Selected vault schema document/revision                                                  |
| template         | optional path                                                                                              | Maintained package template list, or unrendered document                                 |
| original.inspect | path inside Attachments/Originals; optional extract, first_page (default 1), page_count (default 10, 1–50) | Raw hash, link/preview and optional bounded extraction/coverage                          |
| validate         | path; optional document (otherwise read current file)                                                      | Schema diagnostics only                                                                  |
| doctor           | {}                                                                                                         | Read-only six-point integrity findings; no repair or health ledger                       |
| environment      | optional include_hardware                                                                                  | Platform, architecture, Node/process timezone; optional visible logical CPU count/memory |

Collections are `tasks`, `archive`, `projects`, `zettels`, `sources`, `daily` and `system`.
Scans read direct Markdown children, or `Projects/<id>/Roadmap.md`, with 2,000-record/16 MiB budgets;
they are not recursive searches. Some workflows use a smaller 500-record limit.
Environments can be read/proposed by exact path but are not a query collection.
Templates contain placeholders to fill before validation; they are not live configuration.
Schema defaults are annotations, not an automatic read-default engine. Domain schemas reject
unknown properties; system-state records allow extensible private preferences. Schema-only
`validate` does not establish revisions, links, timezone policy, original hashes or approval.

## Proposals and application

| Operation         | Arguments                                                                                                                | Result                                                                      |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| propose           | records: [{path, document, if_revision}]; optional purpose                                                               | Complete validated inert proposal and proposal_digest                       |
| apply             | proposal_digest                                                                                                          | Apply/resume only the saved exact operator approval; verified progress      |
| task.draft        | title, now; optional due, priority, modality, base_minutes, projects, tags, linked_zettels, body, fields, path, timezone | Unscheduled task proposal using native projects links and Memory multiplier |
| horizon           | now; optional horizon_days (must be 14)                                                                                  | Missing active-project task/ledger proposal, or no_changes                  |
| project.reconcile | path, deliverables; optional extraction_status, authoritative_replacement, source_ref, source_scope                      | Reviewed additive ledger proposal and diff                                  |
| project.status    | {}                                                                                                                       | All project statuses and done/total ratios                                  |
| graph             | {}                                                                                                                       | Exact reciprocal knowledge-link proposal, or no_changes                     |
| duplicates        | text (at most 64 KiB); optional sha256, limit (default 10, 1–20)                                                         | Hash/lexical candidates requiring semantic review                           |
| gap-fillers       | date; optional target_count (default 3, 1–20)                                                                            | Short unblocked candidates, possibly already scheduled                      |
| business-buffer   | submission_date; optional business_days (default 3, 3–5)                                                                 | Verification date after the business-day buffer                             |

Use `if_revision:null` for new files and the original `read.revision` for existing files.
`document` contains the entire YAML-frontmatter/body post-image. Order foundational records before
dependants: application follows the supplied order. Batches are resumable, not atomic across files.

`task.draft` defaults to analytical/normal and 45 base minutes; `due` is date-only. `fields` can
supply supported additional task fields, but cannot override capture identity, title/status/schedule,
dateCreated or any googleCalendar\* field. The exact prohibited keys in fields are type, id, title,
status, scheduled and dateCreated, plus all googleCalendar-prefixed keys; optional created is permitted. Unknown schema fields need separate reviewed
package/schema maintenance outside the life profile. No schema-edit operation is exposed.

Reconciliation accepts complete extraction by default. Partial/failed evidence cannot remove work;
archiving omissions additionally requires explicit complete authoritative replacement in the same
source scope. `horizon` examines all active projects; it is not an activation command.
Gap fillers are at most 45 minutes/tier 2 within the horizon, not necessarily unscheduled captures.

A complete task capture call has this shape; replace its timestamp with the actual configured local time:

```json
{
  "operation": "task.draft",
  "arguments": {
    "title": "Review the module interface",
    "now": "2026-10-08T09:00:00+02:00",
    "base_minutes": 30,
    "tags": []
  }
}
```

Present the returned post-images/digest. The operator runs `/chrysalis approve <digest>`, which
reviews and applies. Interrupted approved work can use `apply`; the model cannot issue approval.
Every changed post-image needs a new reviewed digest, including checkpoint updates.

Any proposal creating Slipbox notes returns required_note_reviews: [{path, revision}], where
revision hashes the entire proposed Markdown document. The native command first displays and
confirms each new note, then reviews the whole batch. Editing or declining stops before a new
receipt/write. The saved receipt includes these exact note_reviews; the backend rejects absent,
partial or mismatched reviews. This rule applies to generic propose and ingestion as well.

Mutation paths must use exact existing on-disk spelling. Reserved System names retain their
canonical spelling even on case-sensitive platforms; filename casing/short-name aliases cannot
bypass Memory or append-only journal guards.

## Knowledge compilation, answers and maintenance

| Operation         | Arguments                                                                                                       | Result                                                                                                                                    |
| ----------------- | --------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| knowledge.search  | query; optional aliases (at most 20 literal terms), include_sources, limit (default 10, 1–50), page (default 0) | Full-text matches with path, revision, summary, claim status, passive excerpt and next_page; no writes                                    |
| knowledge.lint    | optional paths (at most 500), records (complete proposed post-images), limit (default 100, 1–1,000)             | Read-only inventory/evidence/index/snapshot findings, total_findings, truncation and judgment limits                                      |
| knowledge.prepare | now, dispositions; optional records (at most 498), source_paths (at most 100 exact Sources paths)               | Validated inert compilation proposal, required_note_reviews and knowledge_review, including generated index/log and evidence dependencies |

Search uses literal phrases, query word tokens and explicit aliases, without stemming, embeddings
or semantic confidence. Default scope is atomic notes and answer snapshots; include_sources adds
captured sources. It scans full stored documents even if the index is absent. Fetch complete matched
records before answering. Plain answers are read-only; source acquisition is a separate workflow.

Lint overlays complete records, without validating/applying their mutation policy or writing a log.
Optional paths focus note/answer checks; inventory checks still inspect the complete bounded set.
It checks explicit WikiLinks, provenance, payload availability, partial extraction, index entries,
uncompiled Sources, knowledge inbound links and answer citation changes. Literal checking flags
high-signal numbers, ISO dates and quotations of at least 15 characters against captured payloads,
excluding metadata, code and link destinations. Findings need context; this is not a truth checker.
Captured text is normalized/cached once; empty captures are unavailable evidence. Fidelity checks
share a 64 MiB potential scan budget and at most 100,000 payload comparisons per invocation.
Exhaustion reports fidelity_budget_exceeded and scope.fidelity_incomplete, not a clean verdict.
Narrow paths for further inspection; inventory checks still continue.
Missing/contradictory concepts, atomicity, entailment and semantic links require agent/user judgment.

Dispositions are distinct values from new, update, disputed, no_material, archive and lint, at most
three per batch. no_material is exclusive, requires source_paths and cannot create/update atomic
notes. All source_paths must be present in stored/proposed Sources. The preparer owns
System/Knowledge-Index.md and System/Knowledge-Log.md; do not include those in input records.
It preserves prior journal entries/body as an exact prefix. Even a no-material or index-only
decision produces an index/log proposal requiring operator approval. Inspection alone does not.
Journal source_revisions binds source_paths to their exact post-image revisions; no-material
suppresses an uncompiled-source finding only while that approved source revision still matches.

Save an answer only when requested, using a new System/Knowledge-Answer-<timestamp>-<slug>.md,
record_kind: knowledge_answer, title, summary, body citations and cited_notes: [{path}]. Use archive
to fill archived_at, cited raw revisions and substantive-content fingerprints automatically.
Existing snapshots cannot be replaced through knowledge.prepare; changed source knowledge is
reported, not cascade-written into an old answer. Ordinary reviewed record editing remains possible.

Knowledge scans use the existing shallow collection budgets and additionally cap selected rows
at 5,000/32 MiB. Index/log each remain subject to the 1 MiB record budget. Scan failures are explicit,
not pagination of the underlying storage; search pages only the bounded result set. Preparation
binds every observed knowledge record revision, conservatively invalidating a batch if any of
those records changes before application. New files added by another editor are not a collection
snapshot lock. Sources and all affected notes/links still need complete reviewed post-images.
See the [knowledge procedure](chrysalis-knowledge/references/zettelkasten-guide.md).

## Ingestion and optional capabilities

### Optional onboarding documents

| Operation          | Arguments                                                                  | Result                                                                                                                          |
| ------------------ | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| documents.discover | optional page_size (default 50, 1–100), page_token (numeric-string offset) | Selected folder metadata, format/import outcomes, omissions and continuation; no content/hash reads or writes                   |
| documents.prepare  | paths: 1–100 distinct selected-folder-relative files                       | Inert external original-copy manifest, raw hashes, destinations and proposal_digest                                             |
| documents.apply    | proposal_digest                                                            | Copy/resume only an exact native approval; verified copied files and ingestion envelope; no source/roadmap/project/note records |

First the user runs `/chrysalis documents` to authorize an existing dedicated folder and bounded
metadata/selected-byte hashing. `/chrysalis documents --status` inspects the selection. The model
cannot select roots or issue approval. Discovery scans at most 10,000 entries/2,000 files, depth 8;
hidden/generated/redirected/unsupported entries and truncation are reported. Pages are fresh scans.
Preparation hashes selected originals up to 32 MiB/file and 64 MiB/batch. It does not extract their
contents or copy them before `/chrysalis approve <digest>`. Copies use link-safe relative names at
Attachments/Originals/Onboarding/<folder-id>. Different destination bytes are preserved.
Markdown imports additionally require TaskNotes to exclude original storage and both Dataview
JavaScript options to be disabled. Effective settings hashes are bound in the copy manifest;
unsafe or changed settings block copying and require a newly prepared/reviewed manifest. Fresh
vaults already have these defaults; existing user settings are never rewritten by document import.
Reselection invalidates pending manifests; changed pending source bytes require new review.
Matching already-copied files support recovery without rereading external sources. Source files
are never moved/edited. Copy verification is per-file/final-pass, without a distributed transaction.
Use the returned envelope with ingest.draft, then separate source/knowledge record review.
The [life-document procedure](chrysalis-knowledge/references/life-documents.md) connects supported
evidence to roadmap choices, possible projects and individually vetted atomic notes. Skip/defer
works without selecting a folder; opaque documents and OCR needs remain deferred.

### Private capability bindings

| Operation           | Arguments                                                                             | Result                                                                                                                                        |
| ------------------- | ------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| integrations.status | {}                                                                                    | Separate installation/configuration/credential/fixture/availability observations; authentication may be unknown, verification is not inferred |
| capability          | capability; optional request, binding_slot                                            | Result from the enabled private trusted binding                                                                                               |
| ingest.discover     | source_alias unless all:true; optional page_size (default 50, 1–100), page_token, all | Bounded metadata envelope(s), honest status and continuation                                                                                  |

| ingest.draft | envelope, date; optional now | Selected evidence/source/task proposal and outcomes, or unavailable/no_changes |
| ingest.prevalidate | envelope, date, optional now; alternatively records or proposal.records | Same envelope draft, or complete proposal validation |

Native-authorized live Tasks discovery returns a summary observation with `detail_selection_required`,
coverage and opaque provider cursors; it is not a detailed ingestion envelope. Select IDs through
`read_task_inbox` or `capability` (`ingestion.read`, request `source_alias`, `selected_ids`, optional
`page_size`, `page_token`, `include_completed`) to obtain its contract-version-2 envelope.
`selected_ids` cannot be combined with a cursor. `ingest.draft` uses that unchanged envelope.
Native Tasks capability requests must match the bound instance and its approved list IDs.
`health.morning_context`, `location.resolve` and `routing.estimate` return native-review readiness
for live providers. Maps routing uses `pairs` (at most 20); optional times are explicit-offset ISO
strings. No model argument activates a provider or authorizes sensitive disclosure.

Named capabilities are `ingestion.discover`, `ingestion.read`, `location.resolve`,
`routing.estimate`, `health.morning_context`, `visualization.map_projection` and `calendar.commitments_read`.
Requests cannot override private roots, credentials or activation. Capability-specific requests
follow the configured adapter; see [providers](../skills/chrysalis-integrations/references/providers.md).
Local/export `ingestion.read` returns discovery metadata; use selected original operations for bytes. Native Tasks selected-ID reads return structured detail envelopes.
`all:true` returns the first bounded page of each enabled source, at most 20 aliases.
`page_token` is a returned numeric-string offset for local/exports, or an opaque provider cursor for native Tasks. It is not a credential.

Envelope drafts require `contract_version:"2"`, `access_mode:"read-only"`,
`capabilities.write_back_supported:false`, a supported discovery status and at most 100 items.
Use returned discovery envelopes and the [input contract](../contracts/ingestion-input.contract.md);
do not fabricate availability or binary hashes. File items must point inside the vault's originals.
`now` defaults to the configured-zone clock when needed for structured task creation.

## Daily work

| Operation   | Arguments                                                                                      | Result                                                                             |
| ----------- | ---------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| plan        | wake, energy (integer 1–5), calendar; optional selected (task paths), not_before, timezone     | Task/Memory/Daily calibration proposal                                             |
| stage       | Same as plan                                                                                   | Memory-only pending prototype proposal and hashed result_digest                    |
| audit       | now; optional timezone                                                                         | Learning/rollover/wedge/feedback-pause proposal, findings and hashed result_digest |
| pause       | mode: maintenance, rest, flow or vacation; now; optional timezone; until required for vacation | Reviewed de-scheduling/pause proposal                                              |
| resume      | now; optional timezone                                                                         | Unpause proposal and contextual re-entry guidance                                  |
| daily.begin | mode; optional timezone, invocation_id (UUID)                                                  | External entry receipt; same UUID/mode resumes the receipt                         |
| daily.gate  | evening_start: HH:mm; optional timezone                                                        | Read-only wake_agent/reason from completed audit/staging result receipts           |

Calendar input is `{status:"ok"|"empty", freshness:"fresh", observed_at, events:[]}`.
Events need actual start/end instants or unambiguous local datetimes; optional `travel_minutes`
supplies transit context. A located event defaults to a 30-minute travel buffer; every event has a
15-minute post-buffer. Default observation age is one hour; optional `max_age_seconds` permits
60–86,400 seconds. A fresh explicitly observed empty calendar is valid; missing/stale is not.

Calibration reserves native user timeblocks, respects remaining-day limits and proposes only owned
focus blocks. Staging changes neither task scheduling nor wake learning. Audit learns valid completed
task sessions from the last 24 hours once, clears past/current todo schedules and drafts a single
three-step Starter Wedge for qualifying old tasks. Daily-only Pomodoro records do not independently
feed task-session learning. Review every proposal before applying.

Vacation `until` is on/after today's date. Resume does not run doctor or launch another agent.
Entry modes are morning, evening, audit, staging, calibration, check-in and resume.
The gate checks stored result receipts, not pause state; no scheduler/launcher is bundled.
