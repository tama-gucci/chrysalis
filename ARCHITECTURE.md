# Architecture

One Pi package contains a host-independent domain core. `skills/` holds canonical procedures; `chrysalis/`
dispatches operations; `helpers/` implements validation, ingestion and provider policy.
`hosts/pi/` registers the tool and launches isolated Python. The core imports no Pi API.
The operation allowlist is `contracts/operations.json`.
`run.py request` consumes one bounded versioned JSON request from stdin.

| Vault collection | Purpose |
|---|---|
| `System/Memory.md` | Preferences, IANA timezone, learning and private bindings |
| `System/Life-Roadmap.md` | Chosen goals, milestones and registered pillar tags |
| `Projects/<id>/Roadmap.md` | Complete deliverable ledger, including future work |
| `TaskNotes/Tasks`, `TaskNotes/Archive` | Authoritative tasks |
| `Slipbox`, `Sources` | Atomic knowledge and evidence/provenance notes |
| `Daily` | Approved focus projections and user notes |
| `Attachments/Originals` | Original bytes with relative links |
| `Environments` | Reviewed observations for explicit device aliases |
| `_types`, `_templates`, `TaskNotes/Views` | Schemas, templates and UI projections |

There is no inferred runtime. Setup selects an empty absolute directory whose actual entry is
lowercase `chrysalis`. Its marker binds identity and schema version. Source/package roots and
redirects are rejected. Profiles, Python, authentication, receipts, locks, host databases and
learned procedures stay outside synced vault content.

Writes carry a complete UTF-8 post-image and the SHA-256 of the bytes originally read. Strict
JSON Schema, timestamp, taxonomy, link and plugin policies run before proposal storage. Operator
approval is outside the life tool policy and binds the exact digest/root/identity/revisions.
Application validates remaining records, uses per-file atomic replacement, verifies actual bytes
and records external resumable receipts. A batch can partially apply. Local locks and final
rereads are cooperating-writer protection, not a distributed filesystem transaction.

The Pi life profile denies generic executors and arbitrary writers. Its read tool opens only
canonical Markdown skill resources. The operating-system
owner, another application and malicious extensions are outside this policy. Use a separate
development profile for general tools.

A future harness adapter needs only tool registration, bounded JSON transport, canonical skill
discovery and an equivalent life-profile tool policy. It must use the existing operation allowlist,
external state and operator approval boundary. Host auth, jobs and optional memory stay in the
adapter/profile; they do not become core dependencies. Pi is the only maintained adapter today.

Private capability bindings select statically registered providers. Installation, configuration,
credentials, observation and end-to-end verification are distinct. Host memory contains lessons
and references, never another backlog or schedule. Package defaults are owned and hashed;
external learned overrides remain separate. Collisions stop updates. A recovery journal and
rollback image protect interrupted package replacement.

Local `_types/*.md` documents contain JSON Schema definitions; no database daemon or collection
CLI is required. Normative boundaries: [runtime](contracts/agent-runtime.contract.md),
[ingestion](contracts/ingestion-input.contract.md), [integrations](contracts/integration-capabilities.contract.md).
