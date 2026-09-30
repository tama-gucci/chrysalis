# Chrysalis Architecture & System Boundaries

Chrysalis is an open, provider-independent AI agent framework operating on an **mdbase v0.3** Markdown database collection. It defines how an AI agent ingests unstructured information, organizes knowledge, manages projects and deliverables, plans focused actions, maintains durable memory, and records verified outcomes in a structured Markdown database.

---

## 1. System Architecture Diagram

```text
                     EXTERNAL INGESTION INPUTS
  [Course Syllabi]      [Lecture Transcripts]      [Web Clippings]
         │                       │                        │
         ▼                       ▼                        ▼
┌──────────────────────────────────────────────────────────────────┐
│             LAYER 3: PASSIVE UNTRUSTED TEXT SECURITY             │
│  - Quarantine Delimiters: <untrusted_document_payload>           │
│  - Delimiter Escape Neutralization (&lt;/...&gt;)                │
│  - Strict Frontmatter Schema Gate (additionalProperties: false)  │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                   INGESTION SOURCES COLLECTION                   │
│  - Path: Sources/{source_id}.md                                  │
│  - Metadata: sha256 digest, mime_type, captured_date             │
│  - Provenance: Content-addressed duplicate detection             │
└───────┬────────────────────────┬─────────────────────────┬───────┘
        │                        │                         │
        ▼                        ▼                         ▼
┌──────────────────────────────────────────────────────────────────┐
│               THE TRIPARTITE HYPERGRAPH CONTINUUM                │
│                                                                  │
│  ┌───────────────────┐    [[WikiLinks]]    ┌───────────────────┐ │
│  │ KNOWLEDGE ZETTELS │◄───────────────────►│ PROJECT ROADMAPS  │ │
│  │ Slipbox/*.md      │                     │ Projects/*/Roadmap│ │
│  │ - 14-digit IDs    │                     │ - Master Ledgers  │ │
│  │ - Atomic concepts │                     │ - Imminent/Future │ │
│  └─────────┬─────────┘                     └─────────┬─────────┘ │
│            │                                         │           │
│            │             [[WikiLinks]]               │           │
│            └───────────────────┬─────────────────────┘           │
│                                ▼                                 │
│                     ┌──────────────────────────────┐             │
│                     │       EXECUTION TASKS        │             │
│                     │  TaskNotes/Tasks/            │             │
│                     │  - 14-day horizon            │             │
│                     │  - Modality baselines        │             │
│                     └──────────────────────────────┘             │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│              LAYER 1 & 2: VALIDATION & ENGINE CONTRACTS          │
│  - Layer 1: JSON Schema 2020-12 ($schema, RFC 3339 offsets)      │
│  - Layer 2: mdbase v0.3 Engine (types, path_globs, links, CAS)   │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│             ADR 0006 CONCURRENCY & ATOMIC MUTATION               │
│  - Authoritative Bytes: sha256(UTF-8 document bytes)             │
│  - Compare-And-Swap (CAS): if_revision verification              │
│  - Advisory POSIX File Locks: fcntl.flock on sibling lockfiles   │
│  - Atomic Disk Replacement: os.replace via tempfiles             │
└────────────────────────────────┬─────────────────────────────────┘
                                 │
                                 ▼
┌──────────────────────────────────────────────────────────────────┐
│                    PLUGGABLE RUNTIME AGENTS                      │
│   [Google Antigravity]   [Claude]   [OpenAI Codex]   [Local LLM] │
│  - Governed by contracts/agent-runtime.contract.md               │
│  - 8-Stage Lifecycle & Mandatory Human Approval Gate             │
│  - Persistent Memory in System/Memory.md                         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 2. System Boundaries & Separation of Spheres

Chrysalis operates across three strictly segregated spheres:

1. **Framework Boundary (Source Repository)**:
   - Owns collection manifests (`mdbase.yaml`), JSON Schema Draft 2020-12 type definitions (`_types/*.md`), runtime contracts (`contracts/` including `contracts/ingestion-input.contract.md`), templates (`_templates/`, `System/_templates/`), operational workflows (`System/Workflows/`), provider-neutral ingestion skills (`.agent/skills/ingest/SKILL.md`), optional provider integration skills (`.agent/skills/google-drive/SKILL.md`, `.agent/skills/google-tasks/SKILL.md`), and deterministic Python helpers (`helpers/mdbase_helper.py`, `helpers/ingestion_contract.py`, `helpers/providers/`).
2. **Runtime Agent Boundary (AI Reasoning Engine)**:
   - An executing AI model (Google Antigravity, Claude, OpenAI Codex, local LLMs) supplying cognitive reasoning. The agent ingests context via the versioned (`1.0.0`) Ingestion Input Contract, formulates structured action proposals, waits for human approval, and invokes database operations strictly conforming to framework contracts.
3. **External Applications & Storage Boundary (UI, Media Storage & One-Way Capture Transports)**:
   - Optional interfaces (Obsidian desktop/mobile, TaskNotes community plugin, Google Calendar) providing visualization and calendar syncing, plus optional external media storage (`google-drive` or local filesystem mounts) and one-way quick-capture adapters (`google-tasks`). They are strictly decoupled from core framework execution and do not govern data contracts.

### Strict Personal Domain Boundary
Chrysalis is strictly scoped to personal knowledge, deliverable roadmaps, and cognitive execution. It prohibits:
- Building general-purpose multi-agent daemons or background supervisor processes.
- Building custom replacement database engines (it operates natively on plain Markdown files).
- Utilizing proprietary cloud task managers as an active task store, write-back target, or bidirectional sync engine (external task tools may serve strictly as one-way, read-only capture inputs into `/ingest`; `<vault>/TaskNotes/Tasks/*.md` remains the sole authoritative task store).

#### Separation of Source Repository and Personal Runtime Vault
Use Chrysalis in the personal runtime vault; edit the reusable framework in the source repository outside cloud synchronization. Tests use temporary synthetic sandboxes. Personal tasks, settings, and private notes stay in the runtime vault.

New mdbase deployments use the collection root for `System/`, `Projects/`, `Slipbox/`, schemas and contracts, with tasks in `TaskNotes/Tasks/`. `System/Workflows/` contains portable agent runbooks; `TaskNotes/Workflows/` is private plugin configuration. Runtime helpers can read existing encapsulated `TaskNotes/` and legacy `chrysalis/` layouts, rejecting ambiguous duplicate resources. This compatibility does not convert a legacy vault into an mdbase collection. The old encapsulation installer cannot preserve mdbase collection-relative paths and refuses mdbase restructuring; follow `docs/staged-migration-plan.md` instead.

---

## 3. The Tripartite Hypergraph Continuum

The core data substrate unifies four collections into an interconnected hypergraph linked bidirectionally via `[[WikiLinks]]`:

| Collection | Canonical Path Pattern | Type Schema | Purpose & Scope |
| :--- | :--- | :--- | :--- |
| **Ingestion Sources** | `Sources/{source_id}.md` | `_types/source.md` | Immutable raw document metadata, SHA-256 digests, provenance tracking, and content-addressed deduplication. |
| **Knowledge Zettels** | `Slipbox/{YYYYMMDDHHmmss}-{slug}.md` | `_types/zettel.md` | Atomic Zettelkasten claims and technical mental models with 14-digit local timestamp identifiers. |
| **Project Roadmaps** | `Projects/{project_id}/Roadmap.md` | `_types/project.md` | Strategic project initiatives containing master deliverable ledgers, milestone horizons, and course syllabi mappings. |
| **Execution Tasks** | `TaskNotes/Tasks/{YYYYMMDD}-{slug}.md` | `_types/task.md` | Concrete execution units categorized by cognitive modality and scheduled into ultradian focus blocks. |

### Hypergraph Linkage Invariants:
- **Tasks $\to$ Projects**: Every task generated from a project links to its parent roadmap via `project_ref: "[[Projects/<id>/Roadmap]]"` and specifies `deliverable_id`.
- **Tasks $\to$ Knowledge**: Tasks link to relevant background research or lecture notes via `linked_zettels: ["[[YYYYMMDDHHmmss-slug]]"]`.
- **Projects $\to$ Sources**: Roadmaps link to originating course syllabi or specifications via `source_ref: "[[Sources/<id>]]"` and `source_checksum: "<sha256>"`.
- **Knowledge $\to$ Sources**: Zettel notes link to originating lecture transcripts or papers via `source_ref: "[[Sources/<id>]]"` and `source_checksum: "<sha256>"`.

---

## 4. Three-Layer Validation Architecture

Chrysalis separates validation concerns into three distinct layers:

1. **Layer 1: Artifact Validation (Syntax & Schema)**
   - Validates Markdown YAML frontmatter syntax, required fields, and RFC 3339 date/time formats with explicit local timezone offsets (e.g. `"-05:00"`).
   - Enforces strict compliance with JSON Schema Draft 2020-12 dialect (`$schema: "https://json-schema.org/draft/2020-12/schema"`).
   - Enforces `additionalProperties: false` to reject unmapped or corrupted properties.
2. **Layer 2: Underlying mdbase Engine Capabilities**
   - Collection indexing, type resolution via `match.path_glob` and `match.where`.
   - Link existence and target type validation (`collection.links`).
   - CAS concurrency via `if_revision` matching `sha256(document bytes)`.
   - Read defaults (`collection.read_defaults`) and write-time lifecycle automation (`lifecycle.on_create`, `lifecycle.on_update`).
3. **Layer 3: Chrysalis Framework Behavior (Agent Workflows)**
   - Tripartite hypergraph referential integrity.
   - Provider-independent 8-stage agent lifecycle (`contracts/agent-runtime.contract.md`).
   - 14-day cognitive planning horizon boundary enforcement.
   - Out-of-horizon deliverable retention: master roadmaps retain 100% of deliverables, while tasks $>14$ days remain inert (`scheduled: null`).
   - Uncertain date modeling (`date_uncertain: true`, `due: null`).
   - Passive untrusted text defense and prompt injection quarantine.

---

## 5. Concurrency, Storage & CAS Architecture (ADR 0006)

Chrysalis implements the exact-document storage authority established in ADR 0006 (`mdbase` v0.1.0-beta.108, engine `0.4.0-rc.4`):

1. **Exact-Document Authority**: The UTF-8 document bytes on disk are the absolute source of truth. Document revision is strictly:
   $$\text{revision} = \text{sha256}(\text{document bytes}) \quad \text{(64 lowercase hex characters)}$$
2. **Compare-And-Swap (CAS)**: All update and delete operations must provide `if_revision`. If `if_revision` does not match the current disk revision, the mutation fails closed with `concurrent_modification` and modifies zero bytes on disk.
3. **Cross-Process Mutual Exclusion**: To eliminate Time-Of-Check to Time-Of-Use (TOCTOU) race conditions, `helpers/mdbase_helper.py` acquires an exclusive advisory lock (`fcntl.flock` on POSIX; `msvcrt.locking` + per-path `threading.Lock` on Windows) on a dedicated sibling lockfile (`<path>.lock`) before reading or writing. Lockfiles are never unlinked, preventing inode-reallocation races.
4. **Atomic Disk Replacement**: Files are written to temporary sibling files (`<path>.tmp.<uuid>`) and atomically replaced via `os.replace`, ensuring that crashes or power interruptions never corrupt existing files.

### 5.1 Agent Access Layer Decision: Direct Local Access vs. `mdbase` MCP

Evaluated against installed `mdbase` CLI (`0.1.0-beta.108`, engine `0.4.0-rc.4`, protocol `5`), `helpers/mdbase_helper.py`, and `tests/harness/validation_harness.py` (2026-09-27). Note that `mdbase` `0.1.0-beta.108` provides direct headless CLI execution (`mdbase -C <root>`), local Connect daemon IPC (`mdbase --collection <id>` over Unix socket / Windows named pipe `MDBASE_CONNECT_SOCKET`), and hosted WebSocket relay (`https://mcp.mdbase.dev/mcp` via `mdbase connect`), with no built-in stdio MCP server subcommand (`mdbase mcp` is not present in `0.1.0-beta.108`):

| Dimension | A1. Raw File Editing (`view_file`, `replace_file_content`, `write_to_file`) | A2. Direct Local Access + Validation Tools (`helpers/mdbase_helper.py` + `mdbase -C <root>` CLI) | B1. Local MCP / Local Connect IPC (`mdbase --collection` or custom stdio MCP wrapper) | B2. Hosted `mdbase` MCP Relay (`mcp.mdbase.dev` + `mdbase connect` Daemon) |
| :--- | :--- | :--- | :--- | :--- |
| **1. Read / Search / Query & Schema Enforcement** | Fast ripgrep/file reads (`<10ms`), but **zero automatic schema or non-`Z` offset enforcement** unless paired with a validator. | Full structured queries (`mdbase -C <root> query`) + strict Layer 1 (`Draft202012Validator` + explicit local offset), Layer 2 (`collection.links`), and Layer 3 (`validation_harness.py`, `doctor.py`). | Enforces Layer 1/2 `_types` & `_contracts`, but **lacks Layer 3 rules** (`<untrusted_document_payload>`, syllabus diffing, `[0.20, 2.00]` multiplier bounds) unless wrapped around Python helpers. | Enforces Layer 1/2 `_types` & `_contracts` remotely, but **lacks Layer 3 rules** and requires shipping query/record payloads over the relay. |
| **2. Preservation of Markdown, Frontmatter & Unknown Fields** | Exact byte preservation of Markdown body, comments, and Obsidian/TaskNotes fields during surgical edits; no automatic `additionalProperties: false` check. | `apply_cas_mutation` and surgical edits preserve full Markdown bodies, `[[WikiLinks]]`, and TaskNotes fields (`googleCalendarEventId`, `tn_role`) while rejecting unknown schema fields at Layer 1. | Field-level `mdbase update --fields` re-serializes YAML frontmatter (stripping YAML comments); strict schemas enforce `additionalProperties: false`. | Same as B1: field-level MCP mutations re-serialize YAML frontmatter without preserving comments. |
| **3. Atomic Writes, CAS, Concurrent Editors & Recovery** | No built-in `if_revision` check against concurrent Obsidian edits unless `compute_revision` is checked first. | `apply_cas_mutation` and `mdbase -C <root> update --if-revision` enforce exact SHA-256 CAS, sibling lockfiles (`fcntl.flock` / `msvcrt.locking`), and `os.replace`. | Enforces single-file SHA-256 `if_revision` CAS on the local authority. | Enforces single-file SHA-256 `if_revision` CAS on the local authority, mediated over WebSocket relay. |
| **4. Single-File vs. Multi-File Consistency** | Single-file atomic replacement only. | Single-file atomic replacement; multi-file workflows pre-validate all records in memory before writing in referential order (`Sources` $\to$ `Slipbox` $\to$ `Projects` $\to$ `Tasks`). | Single-file atomic replacement (`mdbase batch` executes sequentially without cross-file ACID rollback on partial failure). | Single-file atomic replacement (`mdbase batch` lacks cross-file ACID rollback). |
| **5. Offline Operation, Latency & Context Usage** | 100% offline; `<10ms` latency; minimal context overhead via targeted line/grep reads. | 100% offline; `15–45ms` local CLI/helper execution; zero MCP tool-schema envelope bloat. | Offline-capable locally (`30–80ms`), but adds JSON-RPC / MCP tool-schema overhead that duplicates native agent file/search tools. | **Requires internet + live relay + running local daemon**; high round-trip latency (`300–1200ms+`). |
| **6. Setup, Auth, Network Exposure & Privacy** | Zero daemon, zero auth, zero network exposure. | Zero daemon, zero auth, zero network exposure; vault bytes never leave local disk. | Local named pipe / socket only; requires local daemon (`mdbase connect`) or custom stdio server configuration per IDE. | Requires OAuth 2.1 grants (`dev.mdbase.mcp`), cloud account login, and plaintext termination in ephemeral RAM at `mcp.mdbase.dev`. |
| **7. Background-Process Requirements & Failure Modes** | Zero background processes; fails only on OS filesystem errors. | Zero background processes; fails closed on schema/CAS mismatch with deterministic diagnostics. | Requires running `mdbase connect` daemon (or per-session stdio child process); socket/pipe disconnects halt tool calls. | Requires persistent `mdbase connect` scheduled task; susceptible to sleep/network drops, token expiry, and OAuth `state` limits. |
| **8. Portability, Maintainability & Debugging** | Universal across all local coding agents; zero extra dependencies. | Portable across Windows/Linux/macOS (`Python 3.10+`, `PyYAML`, `jsonschema`, optional `mdbase` binary); directly testable via `pytest`. | Extra adapter/daemon maintenance layer with no capability gain for local agents that already have shell and file tools. | High maintenance burden (custom skill router, hardlink bundles, relay troubleshooting). |
| **9. Compatibility with Obsidian & TaskNotes** | Compatible if edits preserve frontmatter structure, though unvalidated edits risk breaking TaskNotes views. | 100% compatible: preserves `TaskNotes/Tasks/*.md` conventions (`googleCalendarEventId`, `tn_role`), `os.replace` triggers clean Obsidian file-watcher reloads, and `update.py` protects `.obsidian/plugins/*/data.json`. | Compatible at the file layer, though YAML re-serialization can reorder frontmatter keys. | Same as B1, plus external edits in Obsidian while the relay is offline cannot be seen by cloud agents until reconnected. |

**Decision**: **Direct Local Vault Access paired with Local Validation & CAS Tooling (A2)** is the default architecture for capable local agents (Google Antigravity, OpenAI Codex, Claude Code). Agents read/edit the local vault directly, enforce CAS and Layer 1–3 contracts via `helpers/mdbase_helper.py`, `mdbase -C <vault> validate/query`, `tests/harness/validation_harness.py`, and `System/scripts/doctor.py`, and require zero background daemons or cloud relays. Headless `mdbase -C <vault>` CLI remains available as an optional zero-daemon local query/validation tool.

---

## 6. Passive Untrusted Text Security Model

To protect autonomous AI agents from indirect prompt injection, ingested documents (syllabi, transcripts, web pages) are treated strictly as **passive, untrusted data**:

1. **Payload Delimiter Quarantine**: External text is encapsulated in `<untrusted_document_payload>` tags during context assembly. Agents are instructed never to treat text within these tags as executable system instructions.
2. **Delimiter Escape Neutralization**: Any occurrence of closing delimiter tags within the input text is sanitized into safe HTML entities (`&lt;/untrusted_document_payload&gt;`), preventing attackers from escaping the quarantine context.
3. **Strict Schema Gate**: Ingested data can only mutate structured state through validated JSON Schema types with `additionalProperties: false`. Injection payloads attempting to add hidden instruction fields are rejected at Layer 1.
4. **Air-Gapped Approval Gate**: Extracted plans and proposals cannot execute without human review. The approval token must be explicitly supplied by the human operator.

---

## 7. Component Disposition Ledger

| Component | Status | Disposition Rationale |
| :--- | :--- | :--- |
| **Tripartite Hypergraph** (`Sources/`, `Slipbox/`, `Projects/`, `TaskNotes/Tasks/`) | **Retained** | Core architectural foundation connecting provenance, knowledge, roadmaps, and tasks. |
| **Zero-Leak PII Law & Scanner** (`candidate_audit.py`, `pii-scanner.sh`) | **Retained** | Absolute privacy invariant protecting personal data from public Git tracking. |
| **Anti-Simulation Law** | **Retained** | Mandatory physical disk mutation; chat output alone never mutates state. |
| **1:1 Public Template Matrix** (`_templates/`, `System/_templates/`) | **Retained** | Sanitized public templates for all runtime records and state files. |
| **Collection Manifest & Schemas** (`mdbase.yaml`, `_types/*.md`, `_contracts/*.contract.md`) | **Simplified** | Retained mdbase v0.3 specification (`spec_version: "0.3.0"`) and Draft 2020-12 types (`task`, `project`, `zettel`, `source`, `system_state`); retired Spark-only `_types/skill.md`. |
| **Agent Runtime & Collection Contracts** (`contracts/*.contract.md`) | **Retained** | Provider-independent 8-stage lifecycle and collection path invariants. |
| **Runtime & Development Skills** (`.agent/skills/`, `Development/skills/`, `System/Workflows/01..08`) | **Simplified** | Removed Spark assumptions and `.agent/skills/chrysalis-router/`; retained 13 core runtime skills (`/audit`, `/calibrate`, `/doctor`, `/evening`, `/ingest`, `/morning`, `/onboard`, `/pause`, `/plan`, `/project`, `/task`, `/update`, `/zettel`), 2 optional integration skills (`google-drive`, `google-tasks`), and 2 development skills (`/audit-dev`, `/evolve`) (17 total). |

| **Validation & CAS Helpers** (`helpers/mdbase_helper.py`, `tests/harness/`) | **Retained** | Deterministic schema checks, SHA-256 CAS locking, untrusted payload quarantine, and 3-layer validation harness. |
| **Protected Updater & Bootstrap** (`update.py`, `bootstrap.py`, `export_starter.py`) | **Simplified** | Removed `Skills/` hardlink/bundle generation; added safe pruning of retired framework artifacts (`RETIRED_FRAMEWORK_ARTIFACTS` and `RETIRED_SKILL_REGISTRY_PATHS`) with backup/rollback support and non-destructive `.agent/skills.json` merging. |
| **Bespoke Gemini Spark Integration** (`chrysalis-router`, `_types/skill.md`, `spark-agent-system-prompt.md`, `golem-deployment-and-spark-test-guide.md`, `SPARK-INTEGRATION-ASSESSMENT.md`, `Skills/bundle/`) | **Retired** | Removed bespoke Spark routing, remote skill schema, prompts, hardlink bundles, and `mcp.mdbase.dev` cloud relay grants; replaced by direct local agent execution. |
| **Golem Packaging Wrappers** (`package_golem_bundle.py`, `setup_golem.ps1`) | **Retired** | Redundant with cross-platform `update.py`, `bootstrap.py`, and `export_starter.py`. |
| **`mdbase connect` Background Daemon & Cloud Relay** | **Retired** | Uninstalled background scheduled task and revoked `dev.mdbase.mcp` grants; headless `mdbase -C <vault>` CLI operates directly on local disk without a daemon. |
| **FastAPI Server Daemon** (`apps/gateway/`) | **Retired** | Port 8765 daemon retired; core framework operates directly on local Markdown files. |
| **Custom Mobile Client** (`apps/mobile/`) | **Retired** | Flutter app retired; mobile access provided by Obsidian Mobile / native recorders. |
| **Vendored Obsidian Binary Bundle** | **Retired** | 5.8 MB bundle in `.obsidian/plugins/chrysalis-obsidian/` removed; users install community TaskNotes directly. |
| **Autonomous 3 AM Background Cron** | **Retired** | Background night-time mutations retired; execution is interactive and human-gated. |
| **Static Candidate Task Pools** | **Retired** | Static YAML lists retired in favor of dynamic mdbase queries. |
| **TaskNotes Google Calendar Sync** | **Deferred** | Two-way OAuth 2.0 calendar sync handled by community TaskNotes plugin runtime. |
| **Wear OS Smartwatch Client** | **Deferred** | Standalone wearable client parked in backlog. |
