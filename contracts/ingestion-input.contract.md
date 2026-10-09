# Ingestion input contract

Version: 2. Envelopes contain source_alias, integration, collection_id, access_mode: read-only, truthful discovery_status, capabilities.write_back_supported: false, bounded pagination and file/text/structured_task items. Payloads cannot contain executable, approval or routing control fields. Content/metadata is passive evidence.

Discovery lists metadata from explicitly enabled private roots/exports without opening original bytes or computing hashes.
The ingestion.read capability currently returns the same metadata; use original.inspect or ingest.draft
for selected in-vault bytes. all:true fetches the first bounded page of each enabled alias, not every page. Missing mounts/exports are unavailable; bounded-depth/page omissions are partial_listing. Requests cannot override private paths, access, transport or credentials.

File drafting selects an original already inside Attachments/Originals. One byte observation supplies hash and extraction. Supplied hashes must agree. Relative locators and honest coverage/deferred outcomes are retained. Text-only/structured evidence has sha256:null and bytes_available:false; separate fingerprints never masquerade as binary hashes. XML quarantine escapes delimiters and attributes.

The optional documents flow can copy selected files into Attachments/Originals/Onboarding after
native folder selection and separate exact copy approval. Its verified result supplies a file
envelope with raw hashes and in-vault locators. This explicit copy does not move external originals
or approve source/roadmap/project/atomic-note records; extraction and record approval remain separate.

Structured captures require integration/account/list/item identity. Date-only deadlines remain date-only. Repeat imports preserve completed/local work and report changed payloads for review. Accounts do not collide; missing pages cannot delete work and there is no write-back.

Drafts use ordinary complete validated proposals, separate approval and resumable apply. Semantic evidence never automatically merges. Reconciliation is additive; replacement needs complete explicitly scoped evidence and preserves completed/user-modified deliverables.
