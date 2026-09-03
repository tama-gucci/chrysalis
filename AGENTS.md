---
type: system_specification
id: chrysalis-core-system-prompt
status: evergreen_constitution
version: 5.0.0
---

# Chrysalis Master Constitution (Dual-Mode: Runtime & Development)

## Preamble: Separation of Spheres (Runtime vs. Development)
Chrysalis operates across two strictly segregated functional domains:
1. **The Runtime Sphere (`System/`, `TaskNotes/`):** The private execution substrate governing daily focus, chronotype rhythms, task execution, and personal memory. Governed by the **Runtime Constitution** ([`System/Runtime-Constitution.md`](System/Runtime-Constitution.md)).
2. **The Development Sphere (`Development/`):** The engineering substrate governing open-source framework design, modular skill authoring, recursive self-improvement (`/evolve`), and codebase maintenance. Governed by the **Development Constitution** ([`Development/Development-Constitution.md`](Development/Development-Constitution.md)).

---

## 1. Vault Substrate & Core System Invariants
* **Markdown File Substrate:** The vault filesystem and synced cloud storage substrate (`Google Drive`) is the absolute single source of truth (`chrysalis/`). All state, roadmaps, task lifecycles, and agent skills exist as plain Markdown files with YAML frontmatter.
* **Autonomous AI Orchestration:** Google Antigravity executes daily focus operations (Runtime) and system refactoring (Development) over the Markdown substrate.
* **No External Task Managers:** Never use proprietary cloud task managers, external databases, or third-party APIs for task management. All task mutations must occur directly on TaskNotes files in `chrysalis/TaskNotes/`.
* **Explicit Local Timezone:** All frontmatter ISO timestamps must strictly serialize with the explicit local timezone offset defined in `Scheduling-Memory.md` (e.g., `"-05:00"`). Never write raw UTC `"Z"` strings.
* **Mandatory Physical Disk Mutation (Anti-Simulation Law):** Chat text output alone NEVER mutates system state. The agent must NEVER merely output text claiming tasks are scheduled, staged, calibrated, or code is refactored without calling file modification tools (`replace_file_content` / `write_to_file`) to persist changes to physical disk. Presenting simulated execution in chat without executing physical tool calls is a fatal constitutional breach.
* **Dual Modular Skill Engine:** Autonomous AI agents discover and execute native modular skills defined in `chrysalis/.agent/skills/<skill>/SKILL.md` (Runtime) and `chrysalis/Development/skills/<skill>/SKILL.md` (Development, registered via `.agent/skills.json`).

---

## 2. PART I: Runtime Constitution (Life Operations)

### Dynamic Memory & Operational State
* **`Scheduling-Memory.md`:** Mutable operational state, dynamic tag multipliers bounded to $[0.20, 2.00]$, learned wake rhythms, chronotype telemetry, active diurnal offsets, energy baseline logic, pause flags, and candidate task pools.
* **`Life-Roadmap.md`:** Mutable strategic taxonomy, active/inactive Pillar definitions, milestone horizons, and primary priority arbiter.
* **`Projects/*/Roadmap.md`:** Project-level roadmaps and deliverable tracking.
* **`System-Health.md`:** Persistent diagnostic health ledger tracking integrity passes, schema validations, and auto-heal events.
* **`Changelog.md`:** Persistent historical ledger tracking autonomous system evolution and skill mutations.
* **`System/_templates/`:** Public 1:1 sanitized templates for all runtime state files.

### Universal TaskNotes Frontmatter Schema
Every task note generated or updated within `chrysalis/TaskNotes/Tasks/` must strictly adhere to the following schema:

```yaml
---
title: "Imperative Task Title"
status: todo # Allowed values: todo, in-progress, done, archived
dateCreated: "YYYY-MM-DDTHH:mm:ss-05:00"
created: "YYYY-MM-DDTHH:mm:ss-05:00" # Backward-compatible alias
due: "YYYY-MM-DD"
scheduled: null # Format: "YYYY-MM-DDTHH:mm:ss-05:00" or null
priority: normal # Allowed values: urgent, high, normal, low
urgency_tier: 2 # Scale: 1 (Lowest) to 4 (Highest)
modality: analytical # Allowed values: analytical, kinetic, synthesis, administrative
timeEstimate: 45 # In minutes (baseline duration * active tag multiplier)
energy: medium # Allowed values: high, medium, low
friction: medium # Allowed values: high, medium, low
micro_chunked: false # Boolean: true if a 3-step Starter Wedge has been injected
tags:
  - task
  - pillar-X/subtag # Must reference a tag defined in Life-Roadmap.md
---
```

### Runtime Behavioral Invariants
* **System Integrity Diagnostic Gate (`/doctor`):** Nightly audits and maintenance passes execute the 6-point integrity suite before scheduling or mutating skills. Critical corruption halts operations and records findings in `System/System-Health.md`.
* **Two-Stage Planning Lifecycle (`/plan`):**
  1. *Staging Mode (`/plan --stage`):* Queries the user in natural language. `Life-Roadmap.md` remains primary priority arbiter (active deliverables take Peak Focus anchor slots).
  2. *Calibration Mode (`/plan --calibrate`):* Ingests morning wake and energy telemetry, shifts diurnal windows, and serializes ISO timestamps.
* **Active Tool-Gated Serialization:** During morning calibration, the agent MUST execute tool calls to serialize `scheduled` timestamps into `TaskNotes/Tasks/*.md`, update `morning_checkin` in `Scheduling-Memory.md`, and write `YYYY-MM-DD.md`. During evening staging, the agent MUST execute tool calls to serialize `prototype_schedule`.
* **Bio-Cognitive Modality & Ultradian Alignment:** Work is stacked into 75–90m ultradian sprints separated by a 15m decompression buffer (Analytical $\to$ Peak Sprints, Kinetic $\to$ Slump/Defrost, Synthesis $\to$ Recovery).
* **Feedback-Gated Execution:** Prototype schedules require user review. If omitted, the system auto-pauses to prevent schedule drift.
* **Semantic Pause Lifecycle (`/pause [mode]`):** Supports 4 semantic pause modes (`maintenance`, `rest`, `flow`, `vacation`), freezing multiplier decay and de-scheduling active blocks (`scheduled: null`).
* **Cloud-Native Calendar Ingestion:** Ingests calendar commitments before scheduling; focus sprints wrap around commitments with zero collisions.
* **Telemetry Multipliers & Chronotype Learning:** Session durations ($T_{\text{actual}} = \text{completedAt} - \text{startedAt}$) adjust multipliers bounded in $[0.20, 2.00]$.
* **Unified Nightly Life Audit (`/audit`):** Reconciles task lifecycles, learns multipliers, ingests 14-day roadmap milestones, injects starter wedges, and tunes candidate task pools.

---

## 3. PART II: Development Constitution (Engineering & GitHub Hygiene)

### Absolute Zero-Leak PII Law (GitHub Privacy Invariant)
Chrysalis is distributed publicly on GitHub (`tama-gucci/chrysalis`). Under NO circumstances may any Personal Identifiable Information (PII), personal data, or private device secrets ever be tracked, committed, or pushed to GitHub.

1. **Quarantined Personal Substrates (Strictly Ignored by Git):**
   * Personal task notes (`TaskNotes/Tasks/*.md` except `example-task.md`) and task archive (`TaskNotes/Archive/*.md`).
   * Live runtime state: `System/Life-Roadmap.md`, `System/Scheduling-Memory.md`, `System/System-Health.md`, `System/Changelog.md`.
   * Daily focus notes matching `YYYY-MM-DD*.md`.
   * Personal projects (`Projects/*` except `README.md` and `_templates/`) and personal slipbox notes (`Slipbox/*` except `README.md`).
   * Workstation manifests: `Development/Environment/*.md` (e.g. `obelisk.md`, `surface-pro-x.md`, `Active-Profile.md`).
   * Databases & caches: `Nexus/`, `.conversations/`, `.workspaces/`, `.obsidian/plugins/*/data/`, `*.token.json`, `*.env`.

2. **Mandatory 1-to-1 Public Template Matrix:**
   Every personal runtime file has an exact, sanitized public `.template.md` tracked in git:
   * `System/Life-Roadmap.md` $\to$ `System/_templates/Life-Roadmap.template.md`
   * `System/Scheduling-Memory.md` $\to$ `System/_templates/Scheduling-Memory.template.md`
   * `System/System-Health.md` $\to$ `System/_templates/System-Health.template.md`
   * `System/Changelog.md` $\to$ `System/_templates/Changelog.template.md`
   * `Daily Notes (YYYY-MM-DD.md)` $\to$ `System/_templates/Daily-Note.template.md`
   * `TaskNotes/Tasks/*.md` $\to$ `TaskNotes/_templates/Task-Template.md` & `TaskNotes/Tasks/example-task.md`
   * `Projects/*/Roadmap.md` $\to$ `Projects/_templates/Project-Template.md`
   * `Development/Environment/*.md` $\to$ `Development/Environment/_templates/System-Manifest-Template.md`

3. **Synthetic Placeholder Standard:**
   All public code, documentation, examples, and skill runbooks must strictly use synthetic values:
   * `Jane Doe`, `user@example.com`, relative paths (`chrysalis/...`), generic node names (`station-node`).
   * Machine-bound user paths (`/home/...`, `C:\Users\...`) are strictly prohibited in public files.

4. **Recursive Self-Improvement (RSI) Protocol (`/evolve`):**
   * Development-only execution in Google Antigravity.
   * Mandatory pre-mutation backup snapshot to `.agent/skills/.backup/<skill>_<timestamp>.md`.
   * Pre-commit constitutional verification against all system invariants.
   * Instant rollback via `/evolve --rollback <skill>`.
   * Formal proposal tracking in `System/Changelog.md`.

5. **Mandatory Pre-Commit & Pre-Push Security Gate (`/audit-dev`):**
   Before committing or pushing changes to GitHub, the agent or developer MUST execute:
   ```bash
   /audit-dev
   ```
   Ensures zero quarantined files are tracked, zero machine paths or PII exist in text files, staged diff is clean, and `.gitignore` default-deny (`/*`) is intact.
