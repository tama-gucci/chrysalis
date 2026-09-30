---
name: plan
description: "Master two-stage focus scheduling engine: Protocol 1 (Staging Mode) queries for additions, applies cognitive modality pairing and ultradian sprint stacking; Protocol 2 (Calibration Mode) ingests wake telemetry, shifts sprint/defrost windows, and locks ISO scheduled timestamps."
trigger: "/plan"
domain: runtime
reads:
  - "Sources/*.md"
  - "System/Memory.md"
  - "System/Life-Roadmap.md"
  - "Projects/*/Roadmap.md"
  - "Slipbox/*.md"
  - "TaskNotes/Tasks/*.md"
  - ".agent/skills/audit/SKILL.md"
  - ".agent/skills/ingest/SKILL.md"
writes:
  - "System/Memory.md"
  - "System/Life-Roadmap.md"
  - "Projects/*/Roadmap.md"
  - "TaskNotes/Tasks/*.md"
---

> Paths below are relative to the resolved personal runtime vault (`<vault>`). The default layout keeps `System/`, `Projects/`, `Slipbox/`, and `Sources/` at the root and operational task folders under `TaskNotes/`. See `ARCHITECTURE.md`.


# /plan (Master Focus Scheduling & Bio-Cognitive Diurnal Engine)

## A2 Access Layer & Runtime Vault Resolution (Platform-Agnostic)
* **Resolve `<vault>`:** Run `python System/scripts/vault_paths.py --runtime --json` (or use `$CHRYSALIS_VAULT_PATH` / `$CHRYSALIS_VAULT_ROOT`). All reads and mutations must target `<vault>`, never the synthetic source checkout.
* **Provider-Independent A2 Operations:** Across Google Antigravity, OpenAI Codex, Claude Code, and local CLI agents, execute all queries (`mdbase -C "<vault>" query`, `python helpers/mdbase_helper.py --vault "<vault>" list/horizon-tasks`), schema validations (`python helpers/mdbase_helper.py --vault "<vault>" validate`), and file mutations (`replace_file_content` / `write_to_file` / `apply_patch` / `apply_cas_mutation`) directly on `<vault>`.

> **Stage 5 Lifecycle Alignment (`System/Workflows/05-plan.md`):** `/plan` executes immediately after `/ingest` (`System/Workflows/01-capture.md` through `04-organize.md`, aligned with `/project` and `/zettel`), taking newly materialized 14-day deliverable tasks (`TaskNotes/Tasks/YYYYMMDD-<slug>.md` with `project_ref` and `linked_zettels`) and stacking them into bio-cognitive ultradian focus sprints while keeping `date_uncertain: true, due: null` items unscheduled for deadline clarification.

## Protocol 1: Staging Mode (`/plan --stage` or `/stage`)
Triggered during the evening workflow (`/evening` after `/audit` and `/ingest --all`) or after interactive `/ingest` to construct tomorrow's prototype schedule.


### Step 1: Schedule Addition & Context Query
Initiate the conversation by prompting the user:
> *"Is there anything in particular you'd like included in tomorrow's schedule, or any new developments to note? (e.g., lab equipment setup, personal errand, or focus preference)"*

### Step 2: Intent Processing, Roadmap Sync & Modality Classification
Upon receiving the user's natural language response:
1. **Roadmap Context Ingestion:** If the user's response introduces new project developments, shifting priorities, or new constraints, update `Life-Roadmap.md` and relevant `Projects/*/Roadmap.md` (or delegate to `/audit --mutate`).
2. **Task Materialization & Cognitive Modality Classification:**
   * If the user requested a specific task that does not yet exist in `TaskNotes/Tasks/`:
     * Classify **Cognitive Modality**:
       - `analytical`: Deep mental load, convergent logic (systems architecture, technical writing, complex debugging).
       - `kinetic`: Physical/mechanical movement, low mental load (hardware assembly, workspace organization, physical filing).
       - `synthesis`: Creative/divergent pattern recognition (Zettelkasten notes, system architecture diagrams, design ideation).
       - `administrative`: Low-friction forms, documentation updates, emails.
     * Create the task note in `TaskNotes/Tasks/YYYYMMDD-<slug>.md` with complete YAML frontmatter (`dateCreated`, `created`, `priority`, `urgency_tier`, `modality`, `status: todo`, `scheduled: null`).
3. **Priority Arbitration Hierarchy (Life Roadmap Primary):**
   * **`Life-Roadmap.md` active milestone deliverables remain the primary source of daily priority.**
   * **Case A (Active Roadmap Milestone Present):** The analytical roadmap deliverable is assigned as the **Anchor Task (Peak Focus Sprints)**. The user's requested item is paired to its natural cognitive window: kinetic items into **Slump / Kinetic Defrost** ($+06:30 \to +08:15$), synthesis items into **Recovery Focus** ($+08:30 \to +10:30$).
   * **Case B (No Imminent Roadmap Deadlines):** If there are no urgent roadmap deadlines, the user's requested item *can* be elevated to the **Anchor Task**.
    * **Case C (No Additions Specified):** Assemble the prototype entirely from the active roadmap milestone tasks and eligible unscheduled task notes queried from the collection.
4. **Optional Read-Only Calendar Input (iCal Cache):**
   * Ingest external calendar commitments for tomorrow from the configured private iCal feed (`fetch_ical.py`) into `calendar_sync.cached_events` in `System/Memory.md`. Do not assume that the unfinished native mobile calendar bridge provides commitments.
   * Parse all external calendar commitments (e.g., team architecture syncs, lab sessions, recurring workshops).
   * For events or tasks with physical locations (`location` / `coordinates` and `travel_policy`), query the configured `routing.estimate` capability (`python helpers/mdbase_helper.py --vault "<vault>" route-estimate --origin "<origin>" --destination "<destination>" --mode "<mode>" --arrival-time "<arrival_at>" --buffer-minutes <buffer>`) when enabled, or apply a manual/default 30-minute transition buffer (`fallback_mode: "manual_only"`).
   * Compute deterministic departure windows: `departure_at = arrival_at - duration_minutes - buffer_minutes` (e.g., `10:00` arrival with `25m` commute and `10m` buffer yields `09:25` departure, `09:25–09:50` travel window, and `09:50–10:00` pre-arrival buffer). Invalidate any cached `route_estimate` whose `context_fingerprint` (`origin | destination | mode | departure_bucket`) no longer matches, and never persist `ephemeral_only` provider route metrics or polylines into Markdown files.
   * Save parsed events to `calendar_sync.staged_events_tomorrow` in `System/Memory.md`.
5. **Record Intent:** Save any user context or notes to `prototype_schedule.staged_user_intent` in `System/Memory.md`.

### Step 3: Bio-Cognitive Prototype Schedule Assembly & Collision Avoidance
1. **Diurnal Window Anchoring & Ultradian Sprint Stacking:**
   Anchor to baseline wake times (`09:00` weekday / `11:00` weekend) at baseline Energy 4:
   * **Morning Buffer:** $T_{\text{wake}} \to T_{\text{wake}} + 00:45$ *(Wake, hydrate, daylight, nutrition)*
   * **Peak Focus — Sprint 1 (75m):** $T_{\text{wake}} + 01:30 \to T_{\text{wake}} + 02:45$ *(Anchor Task — Deep Analytical Work)*
   * **Decompression Buffer (15m):** $T_{\text{wake}} + 02:45 \to T_{\text{wake}} + 03:00$ *(Screen-free biological reset, walk, stretch)*
   * **Peak Focus — Sprint 2 (75m):** $T_{\text{wake}} + 03:00 \to T_{\text{wake}} + 04:30$ *(Anchor Task completion or secondary analytical sprint)*
   * **Slump Window (75m):** $T_{\text{wake}} + 06:30 \to T_{\text{wake}} + 07:45$ *(Low-mental admin, passive learning, rest)*
   * **Kinetic Defrost Block (30m):** $T_{\text{wake}} + 07:45 \to T_{\text{wake}} + 08:15$ *(Physical movement / workspace reset to exit slump and elevate dopamine)*
   * **Recovery Focus Window (120m):** $T_{\text{wake}} + 08:30 \to T_{\text{wake}} + 10:30$ *(Synthesis, Zettelkasten notes, portfolio curation)*

2. **Calendar Conflict Resolution:**
   * Overlay any external calendar events staged for tomorrow.
   * If a calendar event intersects with an ultradian window, shift or wrap the focus blocks around the event (e.g. executing analytical sprints prior to an offsite event, or converting pre-event blocks into light kinetic preparation).
   * External calendar commitments take priority in physical space and time; Chrysalis tasks fill the remaining biological focus bandwidth.

3. **Capacity Guardrails:**
   * **Weekday (Mon–Fri):** 1 Anchor Task (Tier 3/4) + up to 2 Support Tasks (Max 3 total, $< 4\text{h}$ deep work + external calendar commitments).
   * **Weekend (Sat–Sun):** Max 1 Primary Anchor Task ($< 2.5\text{h}$, fabrication/creative/technical). Enforce strict `#pillar-1/admin` institutional lockout.

4. **Candidate Gap-Filler Selection (Quick-Capture Prioritization & Inference Rule):**
   * Query eligible unscheduled tasks via `python helpers/mdbase_helper.py --vault "<vault>" gap-fillers --target-count 3` (or direct A2 query).
   * **Primary Prioritization Rule:** Unscheduled quick capture tasks (tasks in `TaskNotes/Tasks/` captured with `external_item_id`, `source_alias: quick-capture`, external task capture adapters, or standalone capture policy with `status: todo` and `scheduled: null`) serve as the **primary gap-filler candidates** (`[qc-01]`, `[qc-02]`, etc.) presented to the user during the interactive feedback gate.
   * **Inference Fallback Rule:** If there are not enough preexisting quick-capture tasks to fill available downtime/recovery/slump gaps or present sufficient options (e.g. `< 3` candidates), gap-filler candidates are **inferred** (`[inf-01]`, `[inf-02]`, etc.) from:
     1. Roadmap backlog deliverables / active project deliverable candidates (`Projects/*/Roadmap.md` deliverables within the 14-day planning horizon),
     2. Routine low-energy administrative or kinetic task backlog in `TaskNotes/Tasks/`,
     3. Routine low-energy maintenance backlog fallbacks (slipbox hygiene, digital workspace triage, physical maintenance).
   * Candidates are labeled with their origin (`Quick-Capture • Due: YYYY-MM-DD` vs. `Inferred: Project Deliverable`, `Inferred: Administrative Backlog`) to provide immediate context during feedback evaluation.

### Step 4: Presentation & Interactive Feedback Gate
1. Render the prototype focus table followed by candidate gap-fillers:

```markdown
#### 📅 Prototype Focus Schedule: YYYY-MM-DD
*(Assumed Wake: 09:00 CDT • Roadmap Anchor: M1.x • Modality Pairing Active)*

| Window | Time (CDT) | Modality | Type | Task | Est | Energy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Peak Focus (Sprint 1)** | `10:30 – 11:45` | Analytical | **Anchor** | `[[roadmap-task]]` | 75m | High |
| *Decompression Buffer* | `11:45 – 12:00` | *Rest* | *Buffer* | *Screen-free biological reset* | 15m | Low |
| **Peak Focus (Sprint 2)** | `12:00 – 13:00` | Analytical | **Anchor** | `[[roadmap-task]]` | 60m | High |
| **Slump / Kinetic Defrost** | `15:30 – 16:45` | Kinetic | **Support 1** | `[[hardware-maintenance]]` | 60m | Low |
| **Recovery Focus** | `17:30 – 18:30` | Synthesis | **Support 2** | `[[zettel-slipbox]]` | 45m | Med |

---
#### 🧩 Gap-Filler Candidates:
- [ ] **[qc-01] Send invoice for consultation** (`#task` • `administrative` • 15m • Low) *(Quick-Capture • Due: 2026-10-02)*
- [ ] **[qc-02] Pick up lab supplies** (`#task` • `kinetic` • 30m • Low) *(Quick-Capture)*
- [ ] **[inf-01] Slipbox hygiene & literature review** (`#task #chrysalis` • `synthesis` • 45m • Medium) *(Inferred: Administrative Backlog)*
```

2. Set `prototype_schedule.feedback_status: "pending"` in `System/Memory.md`.
3. Prompt the user:
   > *"Here is your staged prototype schedule incorporating cognitive modality pairing and ultradian sprints. Reply to approve, swap tasks, or adjust windows before tomorrow's calibration."*
4. **Lifecycle Feedback Evaluation (3-Way Branch):**
   * **Branch 1 (Approval):**
     * Set `prototype_schedule.feedback_status: "approved"` in `System/Memory.md`.
     * Log entry to `schedule_refinement_memory.feedback_history`.
     * Prototype schedule is locked and ready for morning `/calibrate`.
   * **Branch 2 (Modification / Task Swapping):**
     * Ingest requested changes, re-run Step 2 priority arbitration, update schedule assembly, and re-present table.
   * **Branch 3 (No Response / Asynchronous Inaction):**
     * No artificial countdown timer is enforced; `prototype_schedule.feedback_status` remains `"pending"`.
     * When the next operational boundary occurs (e.g. morning check-in or nightly audit run without prior user response), the system detects unresolved pending feedback and automatically sets `system_state.pause_state.is_paused: true` (`reason: "unresponsive_nightly_audit"`), preserving learned multipliers and halting schedule serialization until unpaused.

---

## Protocol 2: Calibration & Timeblocking Mode (`/plan --calibrate` or `/calibrate`)
Triggered during the morning workflow (`/morning`) to calibrate the pre-approved schedule to actual wake telemetry and lock timeblock timestamps.

### Step 1: Telemetry Check-In & Calendar Refresh
1. Ingest actual $T_{\text{wake}}$ timestamp (e.g., `09:18:00-05:00`) and reported `energy_level` ($1–5$).
2. Unpause system if paused (`system_state.pause_state.is_paused: false`).
3. Update rolling baseline wake averages in `System/Memory.md`.
4. **Dynamic Calendar Refresh:** Ingest today's latest external calendar events from `calendar_sync.cached_events` in `System/Memory.md` (or configured read-only calendar feed), updating `calendar_sync.active_events_today`.

### Step 2: Diurnal Shift, Energy Gating & Calendar Collision Avoidance
1. **Dynamic Shift:** Shift all sprint and defrost timeblocks relative to actual $T_{\text{wake}}$ using `diurnal_baselines.relative_offsets`.
2. **Calendar & Travel Conflict Avoidance:** Adjust sprint boundaries so focus blocks do not overlap with scheduled calendar events or commute windows (`routing.estimate` / `travel_policy`). If an event or task has a physical location, reserve the calculated `departure_at` to `arrival_at` travel + buffer window (or a 30-minute manual transition buffer when `routing.estimate` is unconfigured).
3. **Energy Gating:**
   * **Energy 1–2 (Sleep Deprived / Low):** Complete lockout of Tier 3/4 tasks. Retain 1 low-friction kinetic/admin task in Slump window. Expand rest buffers by 50%.
   * **Energy 3–5 (Moderate to Optimal):** Execute full staged agenda.

### Step 3: Mandatory Frontmatter Timeblocking Lock & Serialization (A2 Local Writes Required)
> [!IMPORTANT]
> **Physical Disk Mutation Mandate (`A2`):** You MUST actively execute local file mutations (`replace_file_content` / `write_to_file` in Antigravity, `apply_patch` / file writes in Codex/Claude, or `helpers.mdbase_helper.apply_cas_mutation()`) to serialize the scheduled state to `<vault>` on disk. Never stop at printing text in chat.

1. **Mutate Task Frontmatter:** Update each scheduled task file in `<vault>/TaskNotes/Tasks/*.md` to write the resolved local ISO-8601 timestamp:
   ```yaml
   scheduled: "YYYY-MM-DDTHH:mm:ss-05:00"
   ```
   Validate with `python helpers/mdbase_helper.py --vault "<vault>" validate <task_path>` or `mdbase -C "<vault>" validate`.
2. **Update Memory:** Update `<vault>/System/Memory.md` to record `morning_checkin.active_today`, `morning_checkin.learned_rhythms`, and `morning_checkin.checkin_history`.
3. **Populate Daily Note:** Update or create `<vault>/Daily/YYYY-MM-DD.md` with the calibrated daily schedule table, biomarker telemetry, and task wikilinks.
4. **Calendar Export Status:** Native mobile calendar export is not implemented. Persist the approved schedule to task notes and daily memory; do not claim that an external calendar service, mobile device, or watch was directly updated. Keep reference links in task frontmatter.

### Step 4: Deliver Final Locked Agenda
Output the finalized daily schedule table in chat with exact sprint and defrost timeblocks and clickable markdown links to task notes.
