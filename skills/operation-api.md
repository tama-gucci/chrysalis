# Operation API

Pi calls `chrysalis_operation` with `{operation, arguments}`. The adapter supplies initialized
vault/state roots and cancellation; model arguments cannot replace them. Read complete records
before editing. All paths below are forward-slash vault-relative paths. Requests/results are capped
at 4 MiB; proposals contain 1–500 complete records. The [runtime contract](../contracts/agent-runtime.contract.md)
defines the approval and preservation rules.

Arguments marked optional may be omitted. Local `now`, `wake` and `not_before` values must carry
the configured IANA zone's date-correct offset, such as `2026-10-08T09:00:00+02:00` for Europe/Paris.
Use date-only `YYYY-MM-DD` for `date` and submission dates. Optional `timezone` must equal Memory.
Observation timestamps such as Calendar `observed_at` describe instants and may use another offset.

## Reads and validation

| Operation | Arguments | Result |
|---|---|---|
| read | path | Complete document and raw-byte SHA-256 revision |
| query | collection; optional limit (default 50, 1–100), page (default 0), status | Frontmatter/revision rows and next_page |
| schema | type: task, project, zettel, source, system_state or daily_note | Selected vault schema document/revision |
| template | optional path | Maintained package template list, or unrendered document |
| original.inspect | path inside Attachments/Originals; optional extract, first_page (default 1), page_count (default 10, 1–50) | Raw hash, link/preview and optional bounded extraction/coverage |
| validate | path; optional document (otherwise read current file) | Schema diagnostics only |
| doctor | {} | Read-only six-point integrity findings; no repair or health ledger |
| environment | optional include_hardware | Platform, architecture, Node/process timezone; optional visible logical CPU count/memory |

Collections are `tasks`, `archive`, `projects`, `zettels`, `sources`, `daily` and `system`.
Scans read direct Markdown children, or `Projects/<id>/Roadmap.md`, with 2,000-record/16 MiB budgets;
they are not recursive searches. Some workflows use a smaller 500-record limit.
Environments can be read/proposed by exact path but are not a query collection.
Templates contain placeholders to fill before validation; they are not live configuration.
Schema defaults are annotations, not an automatic read-default engine. Domain schemas reject
unknown properties; system-state records allow extensible private preferences. Schema-only
`validate` does not establish revisions, links, timezone policy, original hashes or approval.

## Proposals and application

| Operation | Arguments | Result |
|---|---|---|
| propose | records: [{path, document, if_revision}]; optional purpose | Complete validated inert proposal and proposal_digest |
| apply | proposal_digest | Apply/resume only the saved exact operator approval; verified progress |
| task.draft | title, now; optional due, priority, modality, base_minutes, projects, tags, linked_zettels, body, fields, path, timezone | Unscheduled task proposal using native projects links and Memory multiplier |
| horizon | now; optional horizon_days (must be 14) | Missing active-project task/ledger proposal, or no_changes |
| project.reconcile | path, deliverables; optional extraction_status, authoritative_replacement, source_ref, source_scope | Reviewed additive ledger proposal and diff |
| project.status | {} | All project statuses and done/total ratios |
| graph | {} | Exact reciprocal knowledge-link proposal, or no_changes |
| duplicates | text (at most 64 KiB); optional sha256, limit (default 10, 1–20) | Hash/lexical candidates requiring semantic review |
| gap-fillers | date; optional target_count (default 3, 1–20) | Short unblocked candidates, possibly already scheduled |
| business-buffer | submission_date; optional business_days (default 3, 3–5) | Verification date after the business-day buffer |

Use `if_revision:null` for new files and the original `read.revision` for existing files.
`document` contains the entire YAML-frontmatter/body post-image. Order foundational records before
dependants: application follows the supplied order. Batches are resumable, not atomic across files.

`task.draft` defaults to analytical/normal and 45 base minutes; `due` is date-only. `fields` can
supply supported additional task fields, but cannot override capture identity, title/status/schedule,
dateCreated or any googleCalendar* field. The exact prohibited keys in fields are type, id, title,
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

## Ingestion and optional capabilities

| Operation | Arguments | Result |
|---|---|---|
| integrations.status | {} | Separate installation/configuration/credential/fixture/availability observations; authentication may be unknown, verification is not inferred |
| capability | capability; optional request, binding_slot | Result from the enabled private trusted binding |
| ingest.discover | source_alias unless all:true; optional page_size (default 50, 1–100), page_token, all | Bounded metadata envelope(s), honest status and continuation |
| ingest.draft | envelope, date; optional now | Selected evidence/source/task proposal and outcomes, or unavailable/no_changes |
| ingest.prevalidate | envelope, date, optional now; alternatively records or proposal.records | Same envelope draft, or complete proposal validation |

Named capabilities are `ingestion.discover`, `ingestion.read`, `location.resolve`,
`routing.estimate`, `visualization.map_projection` and `calendar.commitments_read`.
Requests cannot override private roots, credentials or activation. Capability-specific requests
follow the configured adapter; see [providers](../skills/chrysalis-integrations/references/providers.md).
`ingestion.read` currently returns discovery metadata; use selected original operations for bytes.
`all:true` returns the first bounded page of each enabled source, at most 20 aliases.
`page_token` is a returned numeric-string offset, not a provider credential.

Envelope drafts require `contract_version:"2"`, `access_mode:"read-only"`,
`capabilities.write_back_supported:false`, a supported discovery status and at most 100 items.
Use returned discovery envelopes and the [input contract](../contracts/ingestion-input.contract.md);
do not fabricate availability or binary hashes. File items must point inside the vault's originals.
`now` defaults to the configured-zone clock when needed for structured task creation.

## Daily work

| Operation | Arguments | Result |
|---|---|---|
| plan | wake, energy (integer 1–5), calendar; optional selected (task paths), not_before, timezone | Task/Memory/Daily calibration proposal |
| stage | Same as plan | Memory-only pending prototype proposal and hashed result_digest |
| audit | now; optional timezone | Learning/rollover/wedge/feedback-pause proposal, findings and hashed result_digest |
| pause | mode: maintenance, rest, flow or vacation; now; optional timezone; until required for vacation | Reviewed de-scheduling/pause proposal |
| resume | now; optional timezone | Unpause proposal and contextual re-entry guidance |
| daily.begin | mode; optional timezone, invocation_id (UUID) | External entry receipt; same UUID/mode resumes the receipt |
| daily.gate | evening_start: HH:mm; optional timezone | Read-only wake_agent/reason from completed audit/staging result receipts |

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
