# Optional named capabilities

Inspect `integrations.status`. Installed, configured, credentials-present, transport-available,
authenticated and verified are separate states. Authentication may be unknown; fixtures never
authenticate an account. Only enabled private bindings run. Keep secret references in private
configuration and actual secrets outside vault/package; resolved secrets never belong in results.

Drive discovery uses bounded explicit local roots or supplied normalized exports. The current
`ingestion.read` capability also returns metadata. Selected in-vault bytes use `original.inspect`
or `ingest.draft`; only actual byte observations supply raw SHA-256. Text exports have `sha256:null`.
No Drive cloud upload, rename, deletion, hydration or OAuth service is bundled. Configure the vault's
`Attachments/Originals` as the ordinary local original collection.

Google Tasks reads a native-authorized inbox through the shared provider service, or an explicitly supplied snapshot/export. Live metadata pages omit notes; selected IDs yield detail envelopes through codemode. Read [source setup](../../../docs/integrations.md) and [recipes](codemode.md). Supported fields are id, title, notes, date-only
due, status and updated. Configured account/list scope supplies identity. Other provider fields
such as parent relationships and links are not mapped automatically. Missing pages never delete
local work; completion, schedules and local edits survive reconciliation. There is no write-back.

Google Maps exposes `location.resolve` and `routing.estimate`. Live reads require native activation and protected external credentials; fixtures are separate evidence. Live content is shown only in attributed native review; ordinary operations and MCP return non-content readiness. Queries exclude task bodies,
tags and unrelated context. Ask on ambiguous results. Manual coordinates need no provider.
Route context/freshness remain separate from `timeEstimate`; planning uses explicitly supplied
Calendar travel buffers, without automatically calling a routing provider. Restricted provider
coordinates/route metrics cannot persist in records. Current terms/account behavior need separate
verification before deployment; the package's provenance rules are not a legal terms audit.

`visualization.map_projection` returns permitted projection data; it installs or opens no Maps UI.
An optional compatible Obsidian Maps plugin is not bundled. Location owns coordinates; any proposed
top-level coordinates must agree with it and obey provenance rules. Propose both fields together,
including clearing a stale projection: the core does not automatically update or remove pins.

Calendar commitments are read-only normalized observations with `observed_at` and actual events.
Fresh empty differs from stale, absent and unavailable. The package connects no Calendar account.
TaskNotes alone owns Calendar writes if the user independently enables its synchronization.
Authenticated integrations and physical UI rendering require separate acceptance. Eligible Google Health sleep is available only in native memory-only review; new-project onboarding is paused. Model disclosure and automatic calibration enrichment remain unavailable. Confirm manual wake and energy replies independently.
