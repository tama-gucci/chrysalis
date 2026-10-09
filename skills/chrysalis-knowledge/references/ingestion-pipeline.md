# Discover → extract → draft → validate → review → approve → apply → verify

Resolve enabled aliases from private Memory/Ingestion-Sources/Integrations. Call `ingest.discover`
with `source_alias`, bounded `page_size` and `page_token`. `all:true` returns one bounded page per
enabled alias, not a complete crawl. Continue returned pages deliberately. Missing mounts, partial
listings and unavailable exports stay explicit; an absent item never implies deletion. Discovery
and the current `ingestion.read` capability return metadata, not selected original extraction.

Put selected originals inside `Attachments/Originals` before file ingestion. Use `original.inspect`
for bounded text/PDF extraction; scanned PDFs/images report OCR-required and opaque formats remain
deferred. The life profile has no general extraction executor or browser. Preserve original bytes
and vault-relative links; never relocate or hydrate real media implicitly.

For optional life-document onboarding, the [document procedure](life-documents.md) provides native
folder selection and a separately reviewed selected-copy manifest. Its verified result supplies
an in-vault ingestion envelope. Copying originals is separate from creating Sources or synthesized
roadmap/project/atomic-note records; each resulting batch retains its own review boundary.

Call `ingest.draft` with `envelope`, local `date: "YYYY-MM-DD"` and optional local `now`.
The envelope has `contract_version: "2"`, read-only access and no write-back. Quarantine payloads.
Keep raw-byte SHA-256, normalized text and structured-payload fingerprints separate. Repeated raw
bytes retain source identity; a moved original proposes reviewed locator/history updates. Changed
bytes create distinct evidence: revision chains, incomplete-source recovery and semantic merges
require deliberate review rather than an automatic inference.

Structured tasks use integration/account/collection/item identity, never title. Initial completion
is imported honestly; done/archived local work is never reopened. Safe changed imports update only
untouched, unscheduled todo captures. Local edits, schedules, relationships and Calendar identifiers
produce review conflicts that preserve local work. Date-only deadlines remain date-only.

Separate evidence, extracted actions and inference, with citations, coverage and uncertainty. For
richer project/Zettel/task changes call `ingest.prevalidate` with complete `records`, or use ordinary
`propose`. Schema-only `validate` does not check the complete mutation policy. Reconciliation is
additive; failed/partial extraction cannot remove work. Only a reviewed complete same-scope
authoritative replacement may archive omissions. `horizon` drafts missing active-project overdue,
14-day and uncertain tasks; uncertain tasks remain excluded from scheduling until clarified.

For atomic knowledge read [zettelkasten-guide.md](zettelkasten-guide.md). Triage each claim as
new/update/disputed/no_material; do not turn every capture into a note. Use knowledge.search for
existing claims and inspect complete evidence before writing figures, dates or quotations. Prefer
knowledge.prepare for a combined source/note/link proposal with its reviewed index/log. Every new
atomic note is individually vetted and confirmed through Pi before the final batch approval.
Source capture does not imply approval to write synthesized notes. No candidates enter the vault.

Present the complete proposal and digest for native approval. Put foundational records before
dependants: application follows caller order and is not a multi-file transaction. Verify actual
bytes and links, report partial failure, and resume the exact remaining approved work. Never write
externally. Duplicate candidates require separate semantic judgment; no automatic merge occurs.
See the [operation API](../../operation-api.md) and [input contract](../../../contracts/ingestion-input.contract.md).
