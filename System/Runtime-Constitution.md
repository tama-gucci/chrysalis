---
type: system_specification
id: chrysalis-runtime-constitution
status: evergreen_constitution
version: 5.0.0
domain: runtime
---

# Chrysalis Runtime Constitution

## Preamble: Separation of Spheres (Runtime vs. Development)
Chrysalis operates across two strictly segregated functional domains:
1. **The Runtime Sphere (`chrysalis/System/`, `chrysalis/TaskNotes/`):** The private, local execution substrate of daily life focus, chronotype rhythms, task execution, and personal memory. Governed by this Runtime Constitution.
2. **The Development Sphere (`chrysalis/Development/`):** The engineering and architecture substrate governing open-source framework design, skill authoring, recursive self-improvement (`/evolve`), and codebase maintenance. Governed by [`Development/Development-Constitution.md`](../Development/Development-Constitution.md).

---

## 1. Vault Substrate & Core Architecture
* **Markdown File Substrate:** The vault filesystem and synced cloud storage substrate (`Google Drive`) is the absolute single source of truth (`chrysalis/`). All state, roadmaps, task lifecycles, and agent skills exist as plain Markdown files with YAML frontmatter.
* **Tripartite Knowledge-Execution Continuum (The Chrysalis Hypergraph):** Unifies atomic Zettelkasten knowledge (`Slipbox/*.md`), strategic roadmaps (`Projects/*/Roadmap.md`), granular TaskNotes execution (`TaskNotes/Tasks/*.md`), and temporal calendar focus blocks into a living, bidirectional hypergraph linked via `[[WikiLinks]]`.
* **Modular Intelligence Engine Principle:** Dual topology supporting:
  - **Option A (Dedicated Home Hub - Golem):** Ambient Gateway daemon (`apps/gateway/`, FastAPI on port `8765`) running on the home server, connecting via a pluggable orchestrator bridge (`BaseOrchestratorBridge`) to Google Antigravity language server (reference), OpenClaw, Hermes OS, or local LLMs over a secure Cloudflare Zero-Trust Tunnel.
  - **Option B (Mobile-Native / Serverless):** Direct edge AI transport executing on-device (e.g. Gemini Nano) or direct cloud model APIs without a home server requirement.
* **Dedicated "Golem" Hardware Topology:** Surface Pro X with 16GB total RAM running Windows 11 on ARM64 24/7 plugged in: 4GB is dedicated to Home Assistant in Hyper-V, leaving 12GB of operational RAM dedicated to Chrysalis, the Ambient Gateway daemon, and autonomous background agents.
* **Deep Obsidian & TaskNotes Interoperability:** Chrysalis operates natively as an Obsidian vault. All tasks use standard TaskNotes frontmatter schema for 1:1 compatibility with the Obsidian TaskNotes plugin on port `8080`, running concurrently and without port collision with the Chrysalis Gateway on port `8765`.
* **Standalone Wear OS Smartwatch Support:** Native circular wearable client (384×384 OLED, pure black `#000000` to preserve battery), featuring rotary card stack, glanceable active sprint cockpit, and prominent voice dictation routing to tasks or Zettels.
* **Model C (Mobile OS Bridge) Calendar Synchronization:** Direct Android `CalendarContract` platform channel that writes focus sprints directly to the device's built-in calendar database, mirroring to Google Calendar and Wear OS watch complications automatically for free with zero Google Cloud Console setup, paired with an iCal feed fallback (`fetch_ical.py`).
* **Autonomous AI Orchestration:** An autonomous AI orchestrator executes daily life focus operations over the Markdown substrate with connected client apps (e.g., Obsidian, Chrysalis Mobile).
* **Quarantined Personal State:** All live personal operational files (`Scheduling-Memory.md`, `Life-Roadmap.md`, `System-Health.md`, `Changelog.md`, and `TaskNotes/Tasks/*.md`) are strictly quarantined from public version control.
* **No External Task Managers:** Never use proprietary cloud task managers, external databases, or third-party APIs for task management. All task mutations must occur directly on TaskNotes files in `chrysalis/TaskNotes/`.
* **Native Modular Skill Engine:** Autonomous AI agents discover and execute native modular skills defined in `chrysalis/.agent/skills/<skill-name>/SKILL.md` (and development skills in `chrysalis/Development/skills/` via `chrysalis/.agent/skills.json`).
* **Explicit Local Timezone:** All frontmatter ISO timestamps must strictly serialize with the explicit local timezone offset defined in `Scheduling-Memory.md` (e.g., `"-05:00"`). Never write raw UTC `"Z"` strings.
* **Mandatory Physical Disk Mutation (Anti-Simulation Law):** Chat text output alone NEVER mutates system state. The agent must NEVER merely output text claiming tasks are scheduled, staged, or calibrated without calling file modification tools (`replace_file_content` / `write_to_file`) to persist changes to the Markdown files on disk. Presenting simulated execution in chat without executing physical tool calls is a fatal constitutional breach.

---

## 2. Dynamic Memory & System Architecture Roles
System rules and operational state are partitioned into dedicated files:

* **`AGENTS.md`:** Root Master Constitution unifying Runtime and Development Spheres as the single source of truth for autonomous AI orchestrators.
* **`Runtime-Constitution.md` (This File):** Dedicated Runtime Sphere constitution governing invariant architectural laws, schema typing, and runtime behavioral invariants.
* **`Development/Development-Constitution.md`:** Invariant laws of open-source engineering, zero-leak GitHub PII protection, and safe recursive self-improvement.
* **`Scheduling-Memory.md`:** Mutable operational state, dynamic tag multipliers (bounded to $[0.20, 2.00]$), learned wake rhythms, chronotype telemetry, active diurnal offsets, energy baseline logic, pause flags, and candidate task pools.
* **`Life-Roadmap.md`:** Mutable strategic taxonomy, active/inactive Pillar definitions, milestone horizons, and primary priority arbiter.
* **`Projects/*/Roadmap.md`:** Project-level roadmaps and deliverable tracking with bidirectional links to reference Zettels.
* **`Slipbox/*.md`:** Atomic Zettelkasten knowledge notes, technical mental models, and system evolution hypotheses (`#chrysalis`) forming the knowledge substrate of the Chrysalis Hypergraph.
* **`System/Orchestrators/*`:** Modular orchestrator adapter registry, pluggable bridge contracts (Antigravity reference, OpenClaw, Hermes OS), and production runtime specifications.
* **`System/System-Health.md`:** Persistent diagnostic health ledger tracking integrity passes, schema validations, and auto-heal events.
* **`System/Changelog.md`:** Persistent historical ledger tracking autonomous system evolution, capability expansions, and skill mutations.
* **`System/Environment/*`:** Multi-node workstation telemetry manifests, hardware profiling, and manifest generation utilities assisting users across their personal projects (manifests quarantined from git, templates & scripts public).
* **`System/_templates/`:** Public, sanitized 1:1 templates for every runtime memory and state file.
* **`.agent/skills/`:** Modular, self-contained executable protocols: unified nightly operational audits (`/audit`), system integrity diagnostics (`/doctor`), system suspension/resumption (`/pause` & `/resume`), project staging and cross-roadmap promotion (`/project`), two-stage focus planning (`/plan --stage` & `/plan --calibrate`), and knowledge synthesis (`/zettel`).

---

## 3. Universal TaskNotes Frontmatter Schema
Every task note generated or updated within `chrysalis/TaskNotes/Tasks/` must strictly adhere to the following schema:

```yaml
---
title: "Imperative Task Title"
status: todo # Allowed values: todo, in-progress, done, archived
dateCreated: "YYYY-MM-DDTHH:mm:ss-05:00"
created: "YYYY-MM-DDTHH:mm:ss-05:00" # Backward-compatible alias
due: "YYYY-MM-DD"
scheduled: null # Format: "YYYY-MM-DDTHH:mm:ss-05:00" or null
priority: normal # Allowed values: urgent, high, normal, low, none
urgency_tier: 2 # Scale: 1 (Lowest) to 4 (Highest)
modality: analytical # Allowed values: analytical, kinetic, synthesis, administrative
timeEstimate: 45 # In minutes (baseline duration * active tag multiplier)
energy: medium # Allowed values: high, medium, low
friction: medium # Allowed values: high, medium, low
micro_chunked: false # Boolean: true if a 3-step Starter Wedge has been injected
tags:
  - task
  - pillar-X/subtag # Must reference a tag defined in Life-Roadmap.md
linked_zettels: [] # Array of wikilinks to relevant Slipbox notes, e.g. ["[[20260901-modular-engine]]"]
project_ref: null # Wikilink to parent project roadmap, e.g. "[[Projects/chrysalis-architecture/Roadmap]]"
googleCalendarEventId: null # Android CalendarContract event ID for Model C calendar sync
---
```

---

## 4. Universal Behavioral Invariants
* **System Integrity & Pre-Flight Diagnostic Gate:** Every nightly audit must execute the 6-point integrity suite (via `/doctor`) before scheduling or mutating skills. Critical schema corruption or broken dependencies halt mutations immediately and record findings in `System/System-Health.md`. `/doctor` may also be executed manually anytime (e.g. during `/pause maintenance`).
* **Autonomous Zettelkasten Hypergraph Linking:** Autonomous agents connect knowledge to action: scanning `Slipbox/*.md` to associate relevant research notes with active project roadmaps (`Projects/*/Roadmap.md` Section 3) and injecting them as `linked_zettels` in `TaskNotes/Tasks/*.md` frontmatter so the active sprint cockpit and Android calendar events display direct reference links.
* **Two-Stage Planning Lifecycle & Priority Arbitration:** 
  1. *Staging Mode (`/plan --stage`):* The agent queries the user for schedule additions or context in natural language. `Life-Roadmap.md` remains the primary arbiter of daily priority: active roadmap deliverables take Peak Focus anchor slots unless no imminent deadlines exist. User additions are integrated into downtime, slump, or recovery windows.
  2. *Calibration Mode (`/plan --calibrate`):* Ingests actual morning wake and energy telemetry, shifts diurnal windows, and serializes ISO timestamps.
* **Active Tool-Gated Serialization:** During morning calibration, the agent MUST execute tool calls to serialize `scheduled: "YYYY-MM-DDTHH:mm:ss-05:00"` into `chrysalis/TaskNotes/Tasks/*.md`, update `morning_checkin` in `chrysalis/System/Scheduling-Memory.md`, and write `chrysalis/YYYY-MM-DD.md`. During evening staging, the agent MUST execute tool calls to create new task notes in `chrysalis/TaskNotes/Tasks/` if requested, update `chrysalis/System/Life-Roadmap.md` if roadmap priorities changed, and serialize `prototype_schedule` in `chrysalis/System/Scheduling-Memory.md`.
* **Bio-Cognitive Modality & Ultradian Alignment:** Focus schedules must stack work into 75–90m ultradian sprints separated by a 15m decompression buffer. Work is paired by cognitive modality (Analytical $\to$ Peak Sprints, Kinetic $\to$ Slump/Defrost, Synthesis $\to$ Recovery).
* **Feedback-Gated Execution:** Autonomous prototype schedules require user approval or feedback before timestamps are locked to disk. If feedback is omitted, the system auto-pauses to prevent schedule drift.
* **Semantic Pause Lifecycle & Manual Suspension:** The system supports intentional manual pausing (`/pause [mode]`) across 4 semantic archetypes (`maintenance`, `rest`, `flow`, `vacation`). Manual pauses freeze multiplier decay, de-schedule active daily task blocks (`scheduled: null`), and orchestrate frictionless lifecycle re-entry without unresponsiveness warning gates.
* **Institutional Buffering:** Never schedule official administrative or institutional actions on weekends. Multi-day institutional workflows require a mandatory buffer of 3–5 business days between submission and verification.
* **Model C Mobile OS Bridge & Calendar Ingestion:** Calendar commitments are ingested via Model C (`CalendarContract` platform channel) or private iCal feed (`fetch_ical.py`) before scheduling; focus sprints wrap around commitments with zero collisions and mirror out to Google Calendar and Wear OS watch complications with zero cloud setup.
* **Telemetry-Driven Multipliers & Chronotype Learning:** Task durations must always be calculated from actual session deltas ($T_{\text{actual}} = \text{completedAt} - \text{startedAt}$) and adjusted via experiential learning rates bounded in $[0.20, 2.00]$ rather than static estimates.
* **Nightly Operational Audit:** Operational state reconciliation is handled by `/audit`, updating multipliers, ingesting upcoming 14-day roadmap milestones, injecting starter wedges, and maintaining candidate task pools.
