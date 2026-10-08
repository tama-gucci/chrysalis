# Optional named capabilities
Inspect integrations.status and the trusted registry. Installation, private configuration,
credentials, transport availability and end-to-end verification are different states. Only enabled
bindings run. Model auth is separate. Keep credential references in private config and actual secrets
outside vault/package; never include resolved secrets in tool results or diagnostics.

Drive supplies ingestion.discover/read through a bounded configured local mount or supplied read-only
connector responses. Use explicit collection roots, depth/page limits and raw-byte SHA-256 only when
actual bytes are available. Text-only exports have sha256:null. Folder URLs are not file URLs.
Unavailable/auth/permission/partial states remain visible. Never upload, move, rename, delete or hydrate
cloud originals automatically. Configure vault Attachments/Originals as the ordinary local source.

Google Tasks consumes a user-configured read-only connector snapshot/export/API response. It has no
bundled OAuth daemon. Map id/title/notes/date-only due/update/etag/parent/links and pagination into
structured_task envelopes. Distinct IDs with equal titles remain distinct; missing pages never delete
local tasks. Local completed work, schedules, links and edits remain authoritative. Zero write-back.

Google Maps supplies separate location.resolve and routing.estimate bindings. Query only minimal
location endpoints, never transmit task bodies, tags or unrelated context. Ask on ambiguous results.
Manual coordinates work without providers. Respect current provider storage/display/attribution terms:
place IDs may persist; restricted coordinates/route metrics stay ephemeral and cannot appear in a
non-compatible map projection. Route context invalidation uses origin/destination/mode/time fingerprint;
travel durations/buffers never overwrite timeEstimate. Unknown travel uses a declared manual buffer.

Obsidian Maps (official maps Bases plugin) supplies visualization.map_projection only. location owns
coordinates; the top-level coordinates property is a synchronized permitted projection. Virtual,
cleared or disallowed locations clear stale pins. Google-derived/disallowed data is excluded from
non-Google tiles. Map pins do not compute commutes. Disabling Maps never breaks tasks or planning.

Calendar commitments are read-only observations with observed_at, freshness and actual events. A fresh
empty list differs from stale, absent and unavailable. TaskNotes alone writes Calendar. Authenticated
provider operation and real UI rendering require separate acceptance; fixture normalization is scoped
evidence. Fitbit/Google Health is deferred pending eligible access and defined metrics.
