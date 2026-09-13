---
name: plan
description: "Master two-stage focus scheduling engine: Protocol 1 (Staging Mode) queries for additions, applies cognitive modality pairing and ultradian sprint stacking; Protocol 2 (Calibration Mode) ingests wake telemetry, shifts sprint/defrost windows, and locks ISO scheduled timestamps."
trigger: "/plan"
domain: runtime
reads:
  - "System/Scheduling-Memory.md"
  - "System/Life-Roadmap.md"
  - "Projects/*/Roadmap.md"
  - "chrysalis/Tasks/*.md"
  - ".agent/skills/audit/SKILL.md"
writes:
  - "System/Scheduling-Memory.md"
  - "System/Life-Roadmap.md"
  - "Projects/*/Roadmap.md"
  - "chrysalis/Tasks/*.md"
---

> Paths below are relative to the explicitly selected vault. The default layout keeps System, Projects, and Slipbox at the root and operational task folders under chrysalis/. For an existing encapsulated vault, resolve the corresponding resource under chrysalis/; never create a competing copy. See ARCHITECTURE.md.


# /plan (Master Focus Scheduling & Bio-Cognitive Diurnal Engine)

## Protocol 1: Staging Mode (`/plan --stage` or `/stage`)
Triggered during the evening workflow (`/evening`) to construct tomorrow's prototype schedule.

### Step 1: Schedule Addition & Context Query
Initiate the conversation by prompting the user:
> *"Is there anything in particular you'd like included in tomorrow's schedule, or any new developments to note? (e.g., ebike maintenance, personal errand, or focus preference)"*

### Step 2: Intent Processing, Roadmap Sync & Modality Classification
Upon receiving the user's natural language response:
1. **Roadmap Context Ingestion:** If the user's response introduces new project developments, shifting priorities, or new constraints, update `Life-Roadmap.md` and relevant `Projects/*/Roadmap.md` (or delegate to `/audit --mutate`).
2. **Task Materialization & Cognitive Modality Classification:**
   * If the user requested a specific task that does not yet exist in `chrysalis/Tasks/`:
     * Classify **Cognitive Modality**:
       - `analytical`: Deep mental load, convergent logic (CAD drafting, legal/academic writing, problem sets).
       - `kinetic`: Physical/mechanical movement, low mental load (ebike repairs, physical builds, errands, cleaning).
       - `synthesis`: Creative/divergent pattern recognition (Zettelkasten notes, portfolio layouts, design ideation).
       - `administrative`: Low-friction forms, portal checks, emails.
     * Create the task note in `chrysalis/Tasks/YYYYMMDD-<slug>.md` with complete YAML frontmatter (`dateCreated`, `created`, `priority`, `urgency_tier`, `modality`, `status: todo`, `scheduled: null`).
3. **Priority Arbitration Hierarchy (Life Roadmap Primary):**
   * **`Life-Roadmap.md` active milestone deliverables remain the primary source of daily priority.**
   * **Case A (Active Roadmap Milestone Present):** The analytical roadmap deliverable is assigned as the **Anchor Task (Peak Focus Sprints)**. The user's requested item is paired to its natural cognitive window: kinetic items into **Slump / Kinetic Defrost** ($+06:30 \to +08:15$), synthesis items into **Recovery Focus** ($+08:30 \to +10:30$).
   * **Case B (No Imminent Roadmap Deadlines):** If there are no urgent roadmap deadlines, the user's requested item *can* be elevated to the **Anchor Task**.
    * **Case C (No Additions Specified):** Assemble the prototype entirely from the active roadmap milestone tasks and `inferred_task_pool`.
4. **Dynamic Calendar Synchronization (Model C OS Bridge & Cache Ingestion):**
   * Ingest external calendar commitments for tomorrow from the configured private iCal feed (`fetch_ical.py`) into `calendar_sync.cached_events` in `System/Scheduling-Memory.md`. Do not assume that the unfinished native mobile calendar bridge provides commitments.
   * Parse all external calendar commitments (e.g., CAD certification studio/online classes).
   * For events with physical locations (e.g., studio classrooms), allocate an automatic 30-minute transition/travel buffer before and after.
   * Save parsed events to `calendar_sync.staged_events_tomorrow` in `System/Scheduling-Memory.md`.
5. **Record Intent:** Save any user context or notes to `prototype_schedule.staged_user_intent` in `System/Scheduling-Memory.md`.

### Step 3: Bio-Cognitive Prototype Schedule Assembly & Collision Avoidance
1. **Diurnal Window Anchoring & Ultradian Sprint Stacking:**
   Anchor to baseline wake times (`09:00` weekday / `11:00` weekend) at baseline Energy 4:
   * **Morning Buffer:** $T_{\text{wake}} \to T_{\text{wake}} + 00:45$ *(Wake, hydrate, daylight, nutrition)*
   * **Peak Focus — Sprint 1 (75m):** $T_{\text{wake}} + 01:30 \to T_{\text{wake}} + 02:45$ *(Anchor Task — Deep Analytical Work)*
   * **Decompression Buffer (15m):** $T_{\text{wake}} + 02:45 \to T_{\text{wake}} + 03:00$ *(Screen-free biological reset, walk, stretch)*
   * **Peak Focus — Sprint 2 (75m):** $T_{\text{wake}} + 03:00 \to T_{\text{wake}} + 04:30$ *(Anchor Task completion or secondary analytical sprint)*
   * **Slump Window (75m):** $T_{\text{wake}} + 06:30 \to T_{\text{wake}} + 07:45$ *(Low-mental admin, passive learning, rest)*
   * **Kinetic Defrost Block (30m):** $T_{\text{wake}} + 07:45 \to T_{\text{wake}} + 08:15$ *(Physical movement / ebike tuning to exit slump and elevate dopamine)*
   * **Recovery Focus Window (120m):** $T_{\text{wake}} + 08:30 \to T_{\text{wake}} + 10:30$ *(Synthesis, Zettelkasten notes, portfolio curation)*

2. **Calendar Conflict Resolution:**
   * Overlay any external calendar events staged for tomorrow.
   * If a calendar event intersects with an ultradian window, shift or wrap the focus blocks around the event (e.g. executing analytical sprints prior to evening class, or converting pre-class blocks into light kinetic preparation).
   * External calendar commitments take priority in physical space and time; Chrysalis tasks fill the remaining biological focus bandwidth.

3. **Capacity Guardrails:**
   * **Weekday (Mon–Fri):** 1 Anchor Task (Tier 3/4) + up to 2 Support Tasks (Max 3 total, $< 4\text{h}$ deep work + external calendar commitments).
   * **Weekend (Sat–Sun):** Max 1 Primary Anchor Task ($< 2.5\text{h}$, fabrication/creative/technical). Enforce strict `#pillar-1/admin` institutional lockout.

### Step 4: Presentation & Interactive Feedback Gate
1. Render the prototype focus table followed by candidate gap-fillers:

```markdown
#### 📅 Prototype Focus Schedule: YYYY-MM-DD
*(Assumed Wake: 09:00 CDT • Roadmap Anchor: M1.x • Modality Pairing Active)*

| Window | Time (CDT) | Modality | Type | Task | Est | Energy |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Peak Focus (Sprint 1)** | `10:30 – 11:45` | Analytical | **Anchor** | [roadmap-task.md](file:///...) | 75m | High |
| *Decompression Buffer* | `11:45 – 12:00` | *Rest* | *Buffer* | *Screen-free biological reset* | 15m | Low |
| **Peak Focus (Sprint 2)** | `12:00 – 13:00` | Analytical | **Anchor** | [roadmap-task.md](file:///...) | 60m | High |
| **Slump / Kinetic Defrost** | `15:30 – 16:45` | Kinetic | **Support 1** | [ebike-maintenance.md](file:///...) | 60m | Low |
| **Recovery Focus** | `17:30 – 18:30` | Synthesis | **Support 2** | [zettel-slipbox.md](file:///...) | 45m | Med |

---
#### 🧩 Inferred Gap-Filler Candidates:
- [ ] **[inf-01] Task Title** (`#tag` • `modality` • Est • Energy)
```

2. Set `prototype_schedule.feedback_status: "pending"` in `Scheduling-Memory.md`.
3. Prompt the user:
   > *"Here is your staged prototype schedule incorporating cognitive modality pairing and ultradian sprints. Reply to approve, swap tasks, or adjust windows before tomorrow's calibration."*
4. **Lifecycle Feedback Evaluation (3-Way Branch):**
   * **Branch 1 (Approval):**
     * Set `prototype_schedule.feedback_status: "approved"` in `Scheduling-Memory.md`.
     * Log entry to `schedule_refinement_memory.feedback_history`.
     * Prototype schedule is locked and ready for morning `/calibrate`.
   * **Branch 2 (Modification / Task Swapping):**
     * Ingest requested changes, re-run Step 2 priority arbitration, update schedule assembly, and re-present table.
   * **Branch 3 (No Response / Asynchronous Inaction):**
     * No artificial countdown timer is enforced; `prototype_schedule.feedback_status` remains `"pending"`.
     * When the next operational boundary occurs (e.g. morning check-in or nightly audit run without prior user response), the system detects unresolved pending feedback and automatically sets `system_state.pause_state.is_paused: true` (`reason: "unresponsive_nightly_audit"`), freezing tag multiplier decay curves and halting schedule serialization until unpaused.

---

## Protocol 2: Calibration & Timeblocking Mode (`/plan --calibrate` or `/calibrate`)
Triggered during the morning workflow (`/morning`) to calibrate the pre-approved schedule to actual wake telemetry and lock timeblock timestamps.

### Step 1: Telemetry Check-In & Calendar Refresh
1. Ingest actual $T_{\text{wake}}$ timestamp (e.g., `09:18:00-05:00`) and reported `energy_level` ($1–5$).
2. Unpause system if paused (`system_state.pause_state.is_paused: false`).
3. Update rolling baseline wake averages in `Scheduling-Memory.md`.
4. **Dynamic Calendar Refresh:** Ingest today's latest Google Calendar events via Google Workspace tool integrations or read from `calendar_sync.cached_events` in `Scheduling-Memory.md`, updating `calendar_sync.active_events_today`.

### Step 2: Diurnal Shift, Energy Gating & Calendar Collision Avoidance
1. **Dynamic Shift:** Shift all sprint and defrost timeblocks relative to actual $T_{\text{wake}}$ using `diurnal_baselines.relative_offsets`.
2. **Calendar Conflict Avoidance:** Adjust sprint boundaries so focus blocks do not overlap with scheduled calendar events. If an event has a physical location, ensure a 30-minute transition buffer before and after.
3. **Energy Gating:**
   * **Energy 1–2 (Sleep Deprived / Low):** Complete lockout of Tier 3/4 tasks. Retain 1 low-friction kinetic/admin task in Slump window. Expand rest buffers by 50%.
   * **Energy 3–5 (Moderate to Optimal):** Execute full staged agenda.

### Step 3: Mandatory Frontmatter Timeblocking Lock & Serialization (Tool Calls Required)
> [!IMPORTANT]
> **Tool Execution Mandate:** You MUST actively execute file tool calls (`replace_file_content`) to serialize the scheduled state to disk. Never stop at printing text in chat.

1. **Mutate Task Frontmatter:** Call `replace_file_content` on each scheduled task file in `chrysalis/Tasks/*.md` to write the resolved local ISO-8601 timestamp:
   ```yaml
   scheduled: "YYYY-MM-DDTHH:mm:ss-05:00"
   ```
2. **Update Scheduling Memory:** Call `replace_file_content` on `System/Scheduling-Memory.md` to update `morning_checkin.active_today`, `morning_checkin.learned_rhythms`, and `morning_checkin.checkin_history`.
3. **Populate Daily Note:** Call `replace_file_content` (or create) `chrysalis/Daily/YYYY-MM-DD.md` (or `YYYY-MM-DD.md`) with the calibrated daily schedule table, biomarker telemetry, and task wikilinks.
4. **Calendar Export Status:** Native mobile calendar export is not implemented. Persist the approved schedule to task notes and daily memory; do not claim that Android, Google Calendar, or a watch was updated. Keep reference links in task frontmatter.

### Step 4: Deliver Final Locked Agenda
Output the finalized daily schedule table in chat with exact sprint and defrost timeblocks and clickable markdown links to task notes.
