---
name: pause
description: "Handles manual system suspension and resumption: de-schedules active timeblocks, freezes multiplier decay, sets semantic pause mode (maintenance, rest, flow, vacation), and orchestrates frictionless lifecycle re-entry."
trigger: "/pause"
reads:
  - "chrysalis/System/Scheduling-Memory.md"
  - "chrysalis/TaskNotes/Tasks/*.md"
  - "chrysalis/YYYY-MM-DD.md"
writes:
  - "chrysalis/System/Scheduling-Memory.md"
  - "chrysalis/TaskNotes/Tasks/*.md"
  - "chrysalis/YYYY-MM-DD.md"
---

# /pause & /resume (System Suspension & Re-Entry Orchestrator)

## Supported Commands & Triggers
* `/pause` — Interactive pause: prompts for mode or pauses for the remainder of today.
* `/pause maintenance` (or `/pause --maintenance`) — Pauses for vault refactoring / system debugging; de-schedules today's focus, wipes prototype schedule, and auto-resumes at tonight's `/evening`. Run `/doctor` anytime during maintenance to verify system integrity.
* `/pause rest` (or `/pause sick` / `/pause --rest`) — Pauses for biological rest/illness; de-schedules focus, freezes multiplier decay, suppresses check-ins, and auto-resumes at next morning `/morning`.
* `/pause flow` (or `/pause --flow`) — Unstructured flow mode; removes rigid sprint window locks, switches daily note to unscripted flow log mode.
* `/pause vacation until YYYY-MM-DD` (or `/pause away until YYYY-MM-DD`) — Multi-day horizon pause; suspends daily prompts until target date.
* `/resume` (or `/unpause` / `/pause --resume`) — Immediately unpauses system and provides contextual re-entry options.

---

## Protocol 1: System Pause (`/pause [mode] [args]`)

### Step 1: Mode Resolution & Parameter Parsing
1. Identify the requested pause mode:
   * **`maintenance`:** User is actively working on Chrysalis configs, skills, or vault organization.
   * **`rest` / `sick`:** User needs biological rest, sick time, or burnout recovery.
   * **`flow`:** User wants unscripted spontaneous deep work without rigid timeblocks.
   * **`vacation`:** User is traveling or taking a multi-day break (`until YYYY-MM-DD`).
   * **Unspecified (`/pause`):** If no mode is specified in command arguments, prompt the user or default to `maintenance` for today if immediate pause is requested.

### Step 2: Operational State Mutation (Tool Call)
Execute `replace_file_content` on `chrysalis/System/Scheduling-Memory.md` to update `system_state.pause_state`:
```yaml
system_state:
  pause_state:
    is_paused: true
    mode: "maintenance" # maintenance | rest | flow | vacation | auto_unresponsive
    reason: "<User-provided or inferred reason>"
    paused_at: "YYYY-MM-DDTHH:mm:ss-05:00"
    resume_policy: "auto_at_cycle" # auto_at_cycle | manual_only | scheduled_date
    resume_target: "evening" # evening | morning | "YYYY-MM-DD"
    freeze_multiplier_decay: true
```

* **If `mode == "maintenance"`:** Wipe `prototype_schedule` (`staged_user_intent: null`, `target_date: null`, `feedback_status: "pending"`, `staged_anchor_task: null`, `staged_support_tasks: []`).
* **If `mode == "rest"`:** Preserve rolling wake rhythms; mark `rest_day: true` in context notes to prevent negative efficiency scoring.

### Step 3: Task Frontmatter Sanitation (Tool Calls)
For modes requiring focus de-scheduling (`maintenance`, `rest`, `vacation`):
1. Scan `chrysalis/TaskNotes/Tasks/*.md` for tasks with `scheduled != null` on today's date.
2. **MANDATORY TOOL CALL:** Execute `replace_file_content` on each scheduled task file to set:
   ```yaml
   scheduled: null
   ```
   *(Tasks remain safely in `status: todo` in the daily backlog without phantom timeblock locks).*

### Step 4: Daily Note Status Annotation (Tool Call)
If `chrysalis/YYYY-MM-DD.md` exists for today:
1. **MANDATORY TOOL CALL:** Execute `replace_file_content` to inject a status callout into the Daily Focus Note:
   ```markdown
   > [!WARNING]
   > **Chrysalis System Status: PAUSED (<Mode>)**
   > Operational schedule paused at `HH:mm CDT`. Scheduled timeblocks cleared.
   > System re-entry target: `<resume_target>`.
   ```

### Step 5: User Confirmation Output
Output a concise confirmation message in chat:
> *"⏸️ Chrysalis is now PAUSED (`<mode>`). Active task blocks have been de-scheduled (`scheduled: null`). Multiplier decay is frozen. System will resume automatically at `<resume_target>` (or run `/resume` anytime)."*

---

## Protocol 2: System Resume (`/resume` or `/unpause`)

### Step 1: State Restoration (Tool Call)
1. Execute `replace_file_content` on `chrysalis/System/Scheduling-Memory.md` to restore active state:
   ```yaml
   system_state:
     pause_state:
       is_paused: false
       mode: null
       reason: null
       paused_at: null
       resume_policy: null
       resume_target: null
       freeze_multiplier_decay: false
   ```

### Step 2: Contextual Re-Entry Routing
Determine appropriate next steps based on local time ($T_{\text{now}}$):
* **Morning Window ($< 12:00\text{ CDT}$):**
  > *"▶️ Chrysalis has been RESUMED. Would you like to run `/calibrate` to ingest morning telemetry and schedule today's focus sprints?"*
* **Afternoon Window ($12:00 – 18:00\text{ CDT}$):**
  > *"▶️ Chrysalis has been RESUMED. System is active in flex mode. Remaining backlog items are available in `TaskNotes/Tasks/`. Evening staging will run at your configured evening time."*
* **Evening Window ($> 18:00\text{ CDT}$):**
  > *"▶️ Chrysalis has been RESUMED. System is ready for tonight's `/evening` staging pass."*

> [!TIP]
> **Maintenance Verification:** If resuming from `mode: "maintenance"`, run [`/doctor`](../doctor/SKILL.md) to ensure all vault schemas, timezones, and skill dependencies remain in strict constitutional compliance.

---

## Anti-Simulation Invariant
> [!CAUTION]
> **Mandatory Tool Call Execution:** Merely claiming that the system is paused or resumed in chat text without executing tool calls (`replace_file_content`) to update `Scheduling-Memory.md` and task notes is a fatal constitutional violation.
