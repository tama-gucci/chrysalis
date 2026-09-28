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
   - Owns collection manifests (`mdbase.yaml`), JSON Schema Draft 2020-12 type definitions (`_types/*.md`), runtime contracts (`contracts/`), templates (`_templates/`, `System/_templates/`), operational workflows (`System/Workflows/`), and deterministic Python helpers (`helpers/mdbase_helper.py`).
2. **Runtime Agent Boundary (AI Reasoning Engine)**:
   - An executing AI model (Google Antigravity, Claude, OpenAI Codex, local LLMs) supplying cognitive reasoning. The agent ingests context, formulates structured action proposals, waits for human approval, and invokes database operations strictly conforming to framework contracts.
3. **External Applications Boundary (UI & Transports)**:
   - Optional interfaces (Obsidian desktop/mobile, TaskNotes community plugin, Google Calendar) providing visualization and calendar syncing. They are strictly decoupled from framework execution and do not govern data contracts.

### Strict Personal Domain Boundary
Chrysalis is strictly scoped to personal knowledge, deliverable roadmaps, and cognitive execution. It prohibits:
- Building general-purpose multi-agent daemons or background supervisor processes.
- Building custom replacement database engines (it operates natively on plain Markdown files).
- Utilizing proprietary cloud task managers or external closed databases.

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

Evaluated against installed `mdbase` CLI (`0.1.0-beta.108`, engine `0.4.0-rc.4`, protocol `5`), `helpers/mdbase_helper.py`, and `tests/harness/validation_harness.py` (2026-09-27):

| Dimension | A1. Raw File Editing (`view_file`, `replace_file_content`, `write_to_file`) | A2. Direct Local Access + Validation Tools (`helpers/mdbase_helper.py` + `mdbase -C <root>` CLI) | B. `mdbase` MCP (`mcp.mdbase.dev` Hosted Relay + `mdbase connect` Daemon) |
| :--- | :--- | :--- | :--- |
| **Read / Search / Query & Schema Enforcement** | Fast ripgrep/file reads (`<10ms`), but **zero automatic schema or non-`Z` offset enforcement** unless paired with a validator. | Full structured queries (`mdbase -C <root> query`) + strict Layer 1 (`Draft202012Validator` + explicit local offset), Layer 2 (`collection.links`), and Layer 3 (`validation_harness.py`, `doctor.py`). | Structured MCP queries and Layer 1/2 `_contracts/*.contract.md` checks, but **lacks Layer 3 rules** (`<untrusted_document_payload>`, syllabus diffing, `[0.20, 2.00]` multiplier bounds). |
| **Preservation of Markdown, Frontmatter & Links** | Exact byte preservation of Markdown body, comments, and Obsidian/TaskNotes fields during surgical edits. | `apply_cas_mutation` and surgical edits preserve full Markdown bodies, `[[WikiLinks]]`, and TaskNotes fields (`googleCalendarEventId`, `tn_role`). | Field-level MCP updates (`mdbase update --fields`) re-serialize YAML frontmatter without preserving comments. |
| **Atomic Writes, CAS & Concurrent Editors** | No built-in `if_revision` check against concurrent Obsidian edits unless `compute_revision` is checked first. | `apply_cas_mutation` and `mdbase -C <root> update --if-revision` enforce exact SHA-256 CAS, sibling lockfiles, and `os.replace`. | Enforces single-file `if_revision` CAS on the local connector, mediated over WebSocket relay. |
| **Single-File vs. Multi-File Consistency** | Single-file atomic replacement only. | Single-file atomic replacement; multi-file workflows pre-validate all records before writing in referential order (`Sources` $\to$ `Slipbox` $\to$ `Projects` $\to$ `Tasks`). | Single-file atomic replacement (`mdbase batch` executes sequentially without cross-file ACID rollback on partial failure). |
| **Offline Operation, Latency & Context Usage** | 100% offline; `<10ms` latency; minimal context overhead via targeted line/grep reads. | 100% offline; `15–45ms` local CLI/helper execution; zero MCP schema/envelope bloat. | **Requires internet + live relay + running local daemon** (`mdbase connect`); high tool-call round-trip latency (`300–1200ms+`). |
| **Setup, Auth, Privacy & Background Daemons** | Zero daemon, zero auth, zero network exposure. | Zero daemon, zero auth, zero network exposure; vault bytes never leave local disk. | Requires persistent background daemon (`mdbase connect`), OAuth 2.1 grants, and plaintext termination in ephemeral RAM at `mcp.mdbase.dev`. |

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
| **Collection Manifest & Schemas** (`mdbase.yaml`, `_types/*.md`, `_contracts/*.contract.md`) | **Retained** | mdbase v0.3 specification (`spec_version: "0.3.0"`) and JSON Schema Draft 2020-12 types. |
| **Agent Runtime & Collection Contracts** (`contracts/*.contract.md`) | **Retained** | Provider-independent 8-stage lifecycle and collection path invariants. |
| **Runtime Skills & Portable Workflows** (`.agent/skills/`, `System/Workflows/01..08`) | **Simplified** | Removed Spark assumptions and `.agent/skills/chrysalis-router/`; retained 11 core runtime skills (`/audit`, `/calibrate`, `/doctor`, `/evening`, `/ingest`, `/morning`, `/onboard`, `/pause`, `/plan`, `/project`, `/task`, `/update`, `/zettel`). |
| **Validation & CAS Helpers** (`helpers/mdbase_helper.py`, `tests/harness/`) | **Retained** | Deterministic schema checks, SHA-256 CAS locking, untrusted payload quarantine, and 3-layer validation harness. |
| **Protected Updater & Bootstrap** (`update.py`, `bootstrap.py`, `export_starter.py`) | **Simplified** | Removed `Skills/` hardlink/bundle generation; added safe pruning of retired framework artifacts with backup/rollback support and non-destructive `.agent/skills.json` merging. |
| **Bespoke Gemini Spark Integration** (`chrysalis-router`, `spark-agent-system-prompt.md`, `golem-deployment-and-spark-test-guide.md`, `SPARK-INTEGRATION-ASSESSMENT.md`, `Skills/bundle/`) | **Retired** | Removed bespoke Spark routing, prompts, hardlink bundles, and `mcp.mdbase.dev` cloud relay grants; replaced by direct local agent execution. |
| **Golem Packaging Wrappers** (`package_golem_bundle.py`, `setup_golem.ps1`) | **Retired** | Redundant with cross-platform `update.py`, `bootstrap.py`, and `export_starter.py`. |
| **`mdbase connect` Background Daemon & Cloud Relay** | **Retired** | Uninstalled background scheduled task and revoked `dev.mdbase.mcp` grants; headless `mdbase -C <vault>` CLI operates directly on local disk without a daemon. |
| **FastAPI Server Daemon** (`apps/gateway/`) | **Retired** | Port 8765 daemon retired; core framework operates directly on local Markdown files. |
| **Custom Mobile Client** (`apps/mobile/`) | **Retired** | Flutter app retired; mobile access provided by Obsidian Mobile / native recorders. |
| **Vendored Obsidian Binary Bundle** | **Retired** | 5.8 MB bundle in `.obsidian/plugins/chrysalis-obsidian/` removed; users install community TaskNotes directly. |
| **Autonomous 3 AM Background Cron** | **Retired** | Background night-time mutations retired; execution is interactive and human-gated. |
| **Static Candidate Task Pools** | **Retired** | Static YAML lists retired in favor of dynamic mdbase queries. |
| **TaskNotes Google Calendar Sync** | **Deferred** | Two-way OAuth 2.0 calendar sync handled by community TaskNotes plugin runtime. |
| **Wear OS Smartwatch Client** | **Deferred** | Standalone wearable client parked in backlog. |
