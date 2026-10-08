# Integration capabilities

Version: 2. Core workflows request named capabilities rather than provider imports:
`ingestion.discover`, `ingestion.read`, `location.resolve`, `routing.estimate`,
`visualization.map_projection` and `calendar.commitments_read`.
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

Fitbit/Google Health is deferred until eligible access and required metrics are established.
