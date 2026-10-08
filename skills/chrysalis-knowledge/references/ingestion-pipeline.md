# Discover → extract → draft → prevalidate → approve → apply → verify
Resolve enabled aliases and named capabilities from private Memory/Ingestion-Sources/Integrations.
Use `ingest.discover` with a bounded page_size and page_token or all:true. Do not follow links outside
configured collection roots. Distinguish empty, fully indexed, partial, auth failure, missing mount
and unavailable transport. A partial listing never implies deletion.
Validate the 1.0.0 file/text/structured_task envelope. Quarantine untrusted payloads; separate raw-byte
sha256, normalized text and structured payload fingerprints. File identity distinguishes exact
duplicates, renamed/moved originals, changed versions and incomplete prior targets. Changed provider
scope needs reviewed provenance; a new cloud ID is not inferred from a path and old URLs stay scoped.
Extract evidence, background knowledge, next actions and agent inference separately, with page/
section/figure citations, coverage, omissions and uncertainty. PDF/image preview may require host
read-only extraction tools; unsupported opaque formats remain explicitly deferred, never completed.
Originals live at Attachments/Originals with vault-relative locators and links/embeds. Ingestion
preserves bytes in place and never relocates or hydrates real media implicitly.
Use `ingest.draft` for normalized structured captures and metadata drafts. For richer extracted
projects/Zettels/tasks, prepare the complete proposal and call `ingest.prevalidate`. Reconciliation
is additive, preserves done/archived/user-edited records, and never drops items from failed/partial
extractions. Only an explicitly reviewed complete authoritative replacement in the same source scope
can archive omitted deliverables. Date-only due dates stay date-only; no screenshot timestamp deadline.
Project horizons: overdue, imminent within 14 days and uncertain create inert tasks; future items
remain in project deliverables with task_ref:null. Standalone future captures create inert tasks.
Structured task identity is integration/account/collection/item ID, never title. Completed local
work remains completed; external conflicts preserve local fields and draft a review proposal.
Prevalidation checks schemas, tags, revisions and cross-links before presenting the exact digest.
Operator approval binds that digest/root/revisions. Apply in dependency order, verify actual bytes
and links, and resume exact remaining approved changes after partial failure. Never write externally.
Hand off only eligible reviewed tasks to planning. Exact and semantic duplicates require distinct
evidence; a semantic match can suggest reuse but must not silently merge unrelated records.
