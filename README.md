# Chrysalis: AI Agent Framework on mdbase v0.3

Chrysalis is an open, provider-independent AI Agent Framework operating on an **mdbase v0.3** Markdown database substrate. It defines the formal contracts, schemas, lifecycle rules, and deterministic helpers for how an autonomous AI agent ingests unstructured information, organizes knowledge, manages projects and deliverables, plans focused actions, maintains durable memory, and records verified outcomes in plain Markdown files.

Markdown notes with YAML frontmatter are the authoritative database records. AI agents (Google Antigravity, Claude, OpenAI Codex, Gemini Spark, or local LLMs) supply reasoning and execute operations strictly through standardized runtime contracts. External tools (Obsidian, TaskNotes, Google Calendar) provide optional visualization and interface layers.

---

## Core Capabilities

- **mdbase v0.3 Markdown Database Substrate**: Authoritative collection configuration (`mdbase.yaml`), JSON Schema Draft 2020-12 type definitions (`_types/*.md`), and data contracts (`_contracts/`).
- **Tripartite Knowledge-Execution Continuum**: Living bidirectional hypergraph linking atomic research notes (`Slipbox/`), strategic course and project roadmaps (`Projects/`), and granular execution tasks (`TaskNotes/Tasks/`) via `[[WikiLinks]]`.
- **Exact-Document Authority & CAS Concurrency**: Document bytes on disk are authoritative; document revisions are strictly `sha256(bytes)`. Mutations enforce Compare-And-Swap (`if_revision`), failing closed against concurrent modifications.
- **Provider-Independent Agent Runtime Contract**: Standardized 8-stage state machine (`contracts/agent-runtime.contract.md`) with explicit preconditions, structured input/output envelopes, and error handling.
- **Mandatory Human Approval Gate**: Air-gapped confirmation requirement before any physical disk mutation or scheduling action is executed.
- **Passive Untrusted Text Security**: Multimodal ingestion (syllabi, transcripts, web clippings) isolates external inputs in strict `<untrusted_document_payload>` quarantine delimiters, neutralizing prompt injection attacks.
- **Out-of-Horizon Deliverable Retention & Uncertain Dates**: Master roadmaps preserve 100% of long-term deliverables, while near-term tasks are scheduled within a 14-day cognitive horizon. Ambiguous dates are modeled cleanly via `date_uncertain: true` and `due: null`.
- **Deterministic Persistent Memory**: Session-grounded memory (`System/Memory.md`) tracking user preferences, explicit `-05:00` timezone offsets, modality baselines, and bounded multiplier learning without background cron daemons.

---

## 8-Stage Agent Workflow Lifecycle

Autonomous agents execute the standardized Chrysalis lifecycle:

$$\text{Capture} \longrightarrow \text{Extract} \longrightarrow \text{Review} \longrightarrow \text{Organize} \longrightarrow \text{Plan} \longrightarrow \text{Act} \longrightarrow \text{Record Outcomes} \longrightarrow \text{Continuation}$$

1. **Capture**: Raw document ingestion into `Sources/` with cryptographic SHA-256 provenance and duplicate detection.
2. **Extract**: Passive text analysis isolating deliverables, milestones, concepts, and relationships.
3. **Review**: Human-in-the-loop review of extracted deliverables, uncertain dates, and proposed structure.
4. **Organize**: Structuring into the Tripartite Continuum: `Projects/**/Roadmap.md`, `Slipbox/**/*.md`, and `TaskNotes/Tasks/**/*.md`.
5. **Plan**: Two-stage focus scheduling (Staging and Calibration) pairing cognitive modalities with 75–90m ultradian focus sprints.
6. **Act**: Atomic filesystem mutation with CAS `if_revision` validation and exclusive file locking.
7. **Record Outcomes**: Verification of disk persistence and deterministic memory updates in `System/Memory.md`.
8. **Continuation**: Clean transition to idle or queueing the next prioritized sprint.

---

## Zero-Cloud Local Quickstart

Chrysalis requires **zero external cloud services** to run its validation harness, execute synthetic scenarios, and verify collection integrity. Everything runs locally using Python 3.10+ and standard virtual environment dependencies.

### 1. Prerequisites
- Python 3.10 or higher.
- Git.

### 2. Setup
```bash
# Clone the repository
git clone https://github.com/tama-gucci/chrysalis.git
cd chrysalis

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies (pure validation tooling: PyYAML and jsonschema)
pip install -r requirements.txt
```

### 3. Run Validation Tests
```bash
# Run the complete test suite (contracts, schemas, CAS concurrency, workflows)
python3 -m pytest tests/

# Run the mdbase v0.3 milestone tests
python3 -m pytest tests/test_mdbase_v03_milestone2.py tests/test_contracts_and_memory.py tests/test_gate1_adversarial.py tests/test_validation_harness.py tests/test_worked_scenario.py tests/test_failure_modes.py
```

### 4. Run the Standalone Validation Harness
```bash
# Validate collection configuration, types, and hypergraph links
python3 tests/harness/validation_harness.py --collection .
```

---

## Repository Structure

```text
chrysalis/
├── mdbase.yaml               # Authoritative mdbase v0.3 collection manifest
├── _types/                   # JSON Schema 2020-12 type definitions
│   ├── task.md               # Execution tasks schema & TaskNotes interop
│   ├── project.md            # Project roadmaps & deliverable master ledgers
│   ├── zettel.md             # Atomic Slipbox research notes schema
│   └── source.md             # Ingestion document provenance & digests
├── _contracts/               # Versioned mdbase collection contracts
├── _templates/               # 1:1 public sanitized record templates
├── contracts/                # Runtime contracts
│   ├── agent-runtime.contract.md     # 8-stage state machine & approval gate
│   └── mdbase-collection.contract.md # Collection model, paths & wikilinks
├── helpers/                  # Deterministic validation & CAS helpers
│   └── mdbase_helper.py      # Schema validation, CAS mutations, syllabus diffing
├── fixtures/                 # Realistic synthetic test fixtures
│   ├── synthetic_syllabus_v1.txt
│   ├── synthetic_syllabus_v2_revised.txt
│   ├── synthetic_transcript.txt
│   └── synthetic_prompt_injection.txt
├── TaskNotes/
│   ├── Tasks/                # Active execution task notes
│   ├── Views/                # TaskNotes Obsidian database views (.base)
│   └── Workflows/            # Operational workflow definitions (01-capture to 08-continuation)
├── Projects/                 # Project roadmaps and deliverable master ledgers
├── Slipbox/                  # Atomic Zettelkasten research notes
├── Sources/                  # Ingested raw documents & provenance records
├── System/
│   ├── Memory.md             # Persistent agent memory & active horizons
│   └── _templates/           # System state templates
├── Development/              # Engineering protocols, backlog, and handoffs
└── tests/                    # Local validation harness, scenarios, and test suites
    ├── harness/              # Validation harness package (CLI & engine)
    ├── test_validation_harness.py
    ├── test_worked_scenario.py
    └── test_failure_modes.py
```

---

## Pluggable Runtime Architecture

Chrysalis separates the **database and workflow framework** from the **reasoning agent**:
- The framework owns schemas, validation rules, state machine transitions, and disk CAS operations.
- Any AI runtime can interact with Chrysalis by consuming `contracts/agent-runtime.contract.md` and invoking helper tools or filesystem operations.
- Optional client integrations (Obsidian community plugins, TaskNotes Google Calendar sync, and cloud MCP relays) are cleanly decoupled from core framework execution. See [STATUS.md](STATUS.md) for current implementation status and deferred integrations.

---

## License

See [LICENSE](LICENSE).
