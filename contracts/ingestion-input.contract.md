# Ingestion contract

Provider envelopes use version 1.0.0. An item declares `content_kind` (file, text or
structured_task), source alias, integration, account/collection/item identity, revision, locator,
fingerprints, extraction coverage, evidence and payload. Discovery is read-only, bounded and
explicit about pagination, partial listings, missing mounts, permissions, auth and empty results.

Binary `sha256` means exact original bytes. It is null if bytes are unavailable.
`normalized_text_sha256` and `structured_payload_sha256` are distinct fields.
Provider composite identity never comes from a title; a path is not a stable cloud identifier.
Changed provider scope retains prior provenance without transferring unrelated URLs.

Originals belong at vault-relative `Attachments/Originals`; Sources notes retain locators and
relative links. External references can remain explicit pending a separately approved import.
Ordinary ingestion does not relocate/hydrate a collection. Metadata-only, OCR-required,
unsupported, partial and failed extraction must not be reported as complete interpretation.

The pipeline is discover -> extract -> draft -> prevalidate -> review -> operator approval -> apply ->
verify. `original.inspect` offers bounded text/PDF extraction with page/coverage labels.
Hashing and extraction use one selected raw byte observation. Originals are capped at 32 MiB,
text output at 1 MiB, selected PDF pages at 50 and decoded PDF streams at 8 MiB.
Untrusted text is delimiter-neutralized and wrapped; wrapper attributes are escaped and MIME
metadata must be a type/subtype token. Evidence, inference and unknown dates remain
separate. Raw/normalized deduplication is deterministic; semantic reuse needs review of candidate
evidence and never silently merges notes.

`ingest.draft` handles normalized captures/metadata; richer source-to-project/Zettel/task proposals
use `ingest.prevalidate`. Prevalidation checks schemas, links, tags and whole-body revisions.
Complete project ledgers keep future work; the 14-day horizon materializes overdue/imminent/uncertain
work as inert tasks. Standalone captures need no fabricated project or knowledge note.

Reconciliation preserves completed/archived work and local edits. Partial/failed extraction
cannot delete omitted items. Authoritative replacement requires complete extraction and matching
source scope. Google Tasks is a one-way input with no completion/write-back synchronization.
Application uses the common exact approval boundary and verifies bytes and resumable receipts.
