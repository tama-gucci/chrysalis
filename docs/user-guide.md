# Daily use

Pi discovers seven families through `/skill:chrysalis-<family>`: daily, task, knowledge, diagnostics,
environment, integrations and maintenance. Read the canonical skill and necessary references,
including the shared [operation API](operations.md). The life profile supplies no browser,
general executor or external memory tool; use supplied evidence or a separate research session.

Use bounded query/read operations and draft complete records. `task.draft` needs a title and actual
local `now`; it creates an unscheduled task with native projects links. Show complete post-images
and digest; the operator runs `/chrysalis approve <digest>`. Verified completion means actual bytes
matched. Every changed record set, including an onboarding checkpoint, needs its own reviewed digest.

Goal discovery populates the empty roadmap. Projects keep complete ledgers; the 14-day horizon
drafts missing active-project near-term, overdue and uncertain tasks. Uncertain work needs
clarification before scheduling. Completed/local work survives supplementary reconciliation.
Knowledge links use exact reciprocal associations.

Onboarding uses a small decision ledger to ask one to three independent questions at a time,
after their prerequisites are settled. Partial answers and skipped/deferred choices are retained;
missing evidence delays only dependent questions. The agent recaps your choices and unresolved
matters for confirmation before drafting adopted records. Recommendations include reasons and
alternatives; personal goals and tradeoffs remain yours. A deeper stress-test is optional.
Progress can be saved in the reviewed checkpoint at natural pauses. Read the
[decision procedure](../skills/chrysalis-knowledge/references/onboarding-decisions.md).

Onboarding optionally uses life documents to understand your circumstances, suggest projects and
identify useful atomic knowledge. Select a dedicated external folder with `/chrysalis documents`,
review the inventory and approve selected original copies into the vault. You can skip or return
later. Copy approval does not activate projects or approve notes; discuss the evidence and review
complete record proposals separately. See the [life-document procedure](../skills/chrysalis-knowledge/references/life-documents.md).

For atomic notes use chrysalis-knowledge's Zettelkasten procedure. Review each complete proposed
note, its evidence, uncertainty and links; nothing enters Slipbox as an unapproved candidate.
The native approval command confirms each new note as Markdown before reviewing the complete
batch. Declining one stops the batch. Revisions need a new proposal, including dependent links.

knowledge.search reads full note text and explicit synonyms; knowledge.lint reports evidence,
link/index and source-inventory issues without repairs. knowledge.prepare proposes compiled notes
with an index and append-only knowledge log. Questions return cited answers without saving them.
An explicit saved-answer request produces a separately reviewed dated System snapshot; later
knowledge changes are reported without automatically rewriting it. See [knowledge design](knowledge-design.md)
for limitations. Existing vault schemas are not upgraded by a package install.

Planning requires actual wake/energy and fresh observed commitments. Explicitly observed empty is
valid; absent/stale cannot establish free time. Staging creates an inert Memory prototype. Calibration
proposes task, Memory and Daily changes, including owned native timeblocks. Low energy, weekends,
ultradian rests, native user timeblocks and remaining-day boundaries constrain the plan. Calendar
travel buffers are supplied context, separate from task work estimates.

Evening audit learns valid completed task sessions from the last 24 hours once, clears past/current
todo schedules and drafts one Starter Wedge per qualifying old task. Pauses preserve learning.
TaskNotes manages native completion/session history and Calendar identifiers; chrysalis preserves
them. The package has no background scheduler.

Ingestion follows discovery, selected extraction, draft, validation, review, approval, apply and
verification. Discovery is paged metadata; `all:true` does not crawl every page. Put selected originals
inside the vault first, manually or through the reviewed documents copy flow. PDF parsing is bounded by pages, 32 MiB input, 8 MiB decompressed streams,
1 MiB text, time and memory. Scanned PDFs/images report OCR-required; opaque formats remain deferred.
Duplicate candidates never automatically merge records.

## Prepared Obsidian settings

The preset supplies task list, Kanban, mini-calendar, calendar/agenda, projects, relationships and
session views. The relationships view is a Kanban projection. Dataview dashboards use declarative
queries; DataviewJS and inline JavaScript are disabled.

TaskNotes uses `TaskNotes/Tasks`, the `task` tag, frontmatter titles, todo/in-progress/done/archived
statuses and none/low/normal/high/urgent priorities. The shared registry maps modality, urgency,
energy, friction and knowledge links to native custom fields. Automatic archive movement is off.
Google/Microsoft Calendar connections, API/MCP, webhooks and debug logging start disabled.
Original storage is excluded from TaskNotes, so task-tagged Markdown evidence remains outside
active tasks. Markdown imports verify this exclusion and disabled Dataview code settings, binding
their hashes to copy approval. Existing vaults with unsafe settings require user correction in
Obsidian and a new copy review; import does not change plugin configuration.

Daily notes retain focus plans and native Pomodoro history. Timer defaults are 75-minute focus,
15-minute short rest and 30-minute long rest every three cycles, with automatic starts off. Timers
do not automatically complete tasks. The sessions view summarizes completed Daily Pomodoros;
audit learning uses task timeEntries or explicit task timing. User timeblocks/prose survive owned
focus replacement. The Obsidian Daily template uses native date placeholders; agent draft templates
have explicit placeholders to fill before validation.

Run `/chrysalis timezone` after changing the computer setting. Existing records/schedules retain
their meaning. Review a new plan if the prototype needs recalibration. Physical Obsidian behavior
still needs the acceptance checks in [status](../STATUS.md).

Optional sources use [native setup](integrations.md) through `/chrysalis integrations setup`. Read-only Tasks inboxes can supply selected captures through codemode. Health sleep and Maps travel use native review only; neither automatically changes a schedule or task duration.
