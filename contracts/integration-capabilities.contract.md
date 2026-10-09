# Integration capabilities

Version: 3. Core workflows request named capabilities rather than provider imports:
`ingestion.discover`, `ingestion.read`, `location.resolve`, `routing.estimate`,
`visualization.map_projection`, `health.morning_context` and `calendar.commitments_read`.
Static registry entries bind trusted functions; arbitrary module/path imports are rejected.

Private `integrations.instances` select an adapter and explicit activation/configuration;
`integrations.bindings` select capability instances. `ingestion.sources` selects read-only
capture collections. Optional Integrations/Ingestion-Sources documents refine Memory settings.
Installed code does not activate a provider.

Readiness distinguishes installed, configured, authenticated, available and verified. Credentials
and PATH/plugin presence are preliminary evidence; configuration assertions never establish
end-to-end verification. A normalized successful observation does not certify an account workflow.
Missing, disabled, stale, ambiguous and unavailable providers return honest states.

`credentials_present` and `fixture_available` describe preliminary evidence separately.
Synthetic fixtures never authenticate an account; missing credentials report false and
unchecked account authentication remains unknown. A nonexistent fixture is unavailable.
Ingestion requests may select a configured source and bounded page only; they cannot override
paths, credentials, access, transport or private collection configuration.

Secret references use explicit environment variables or absolute external private files.
Inline credentials and secret files inside the package/vault are rejected. Provider auth is
separate from model auth. Results omit resolved credential values.

Drive discovery reads an explicit bounded mount or normalized export. Selected file drafting requires originals inside the vault.
Google Tasks imports structured captures without write-back. Calendar observations include
`observed_at` and events: fresh empty differs from stale, unavailable and never-observed.
TaskNotes is the only Calendar synchronization writer; agents preserve every Calendar identifier.

Maps queries minimize outgoing location/route fields and exclude task titles, notes, tags and vault
paths. Routing remains separate from task work estimates. Context fingerprints and freshness
invalidate stale routes; ephemeral provider data cannot enter persistent records. Obsidian Maps
projection respects display/provenance policy and filters prohibited cross-map coordinates.
Authenticated operation and current provider terms need separate acceptance before deployment.

Native source activation requires matching external profile and approved Memory native_authorization digests. Secret references for bundled live providers identify OS-protected external records; environment/file references remain only for legacy adapters. Model requests cannot activate/reconnect/disconnect, choose transport/roots, or grant disclosure. Health/Maps native-only policy is enforced from provider identity, regardless of flags.

The bundled MCP transport publishes six strict tools through the same service as ordinary capabilities. Tasks metadata does not include notes; selected detail IDs produce contract-version-2 capture envelopes with account-subject hashes, coverage and omissions. The ingestion backend remains the sole reconciliation/proposal implementation. Provider deletes and omissions never delete local records. External completion cannot override authoritative local lifecycle.

Google Health reads only sleep and linked identity for eligible existing projects. Native evidence is memory-only, with freshness, processed/session coverage and bounded baseline uncertainty. Maps content uses attributed native display, independent travel allowances and no model/session/proposal persistence. Both providers return non-content native-review readiness to the model without secret reads or network calls. No broadened model-disclosure path is implemented.

HTTP reads are endpoint-allowlisted, redirect-denied, deadline/cancellation/size/concurrency bounded and charged to external daily request counters. OAuth exchanges use the maintained Google library with PKCE, verified identity, exact loopback callback state and protected refresh rotation. Local disconnect never invokes project-wide remote revocation. Account/live/UI acceptance remains separate from fixtures.
