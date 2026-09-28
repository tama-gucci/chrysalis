---
name: pause
description: "Handles manual system suspension and resumption: de-schedules active timeblocks, preserves learned multipliers, sets semantic pause mode (maintenance, rest, flow, vacation), and orchestrates frictionless lifecycle re-entry."
trigger: "/pause"
domain: runtime
reads:
  - "System/Memory.md"
  - "TaskNotes/Tasks/*.md"
  - "Daily/YYYY-MM-DD.md"
writes:
  - "System/Memory.md"
  - "TaskNotes/Tasks/*.md"
  - "Daily/YYYY-MM-DD.md"
---

> **A2 Access Layer & Runtime Vault Resolution:**
> All paths below (`System/...`, `TaskNotes/...`, `Daily/...`) are relative to the resolved **personal runtime vault** (`<vault>`), resolved via `python System/scripts/vault_paths.py --runtime --json` (defaulting to `~/Documents/Chrysalis` when invoked from the source checkout). Apply all state mutations on `<vault>` using native file editing tools and validate via `python helpers/mdbase_helper.py --vault "<vault>" validate <file>`.

# /pause & /resume (System Suspension & Re-Entry Orchestrator)

## Supported Commands & Triggers
* `/pause` — Interactive pause: prompts for mode or pauses for the remainder of today.
* `/pause maintenance` (or `/pause --maintenance`) — Pauses for vault refactoring / system debugging; de-schedules today's focus, wipes prototype schedule, and auto-resumes at tonight's `/evening`. Run `/doctor` anytime during maintenance to verify system integrity.
* `/pause rest` (or `/pause sick` / `/pause --rest`) — Pauses for biological rest/illness; de-schedules focus, preserves learned multipliers, suppresses check-ins, and auto-resumes at next morning `/morning`.
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

### Step 2: Operational State Mutation (Local A2 Write)
Update `<vault>/System/Memory.md` on disk (via `replace_file_content` / `write_to_file` in Antigravity, `apply_patch` / file writes in OpenAI Codex / Claude Code, or `python helpers/mdbase_helper.py --runtime apply-cas-mutation`) to update `system_state.pause_state`:
```yaml
system_state:
  pause_state:
    is_paused: true
    mode: "maintenance" # maintenance | rest | flow | vacation | auto_unresponsive
    reason: "<User-provided or inferred reason>"
    paused_at: "YYYY-MM-DDTHH:mm:ss-05:00"
    resume_policy: "auto_at_cycle" # auto_at_cycle | manual_only | scheduled_date
    resume_target: "evening" # evening | morning | "YYYY-MM-DD"
```

* **If `mode == "maintenance"`:** Wipe `prototype_schedule` (`staged_user_intent: null`, `target_date: null`, `feedback_status: "pending"`, `staged_anchor_task: null`, `staged_support_tasks: []`).
* **If `mode == "rest"`:** Preserve rolling wake rhythms; mark `rest_day: true` in context notes to prevent negative efficiency scoring.

### Step 3: Task Frontmatter Sanitation (Local A2 Writes)
For modes requiring focus de-scheduling (`maintenance`, `rest`, `vacation`):
1. Scan `<vault>/TaskNotes/Tasks/*.md` for tasks with `scheduled != null` on today's date.
2. **MANDATORY TOOL CALL (Local A2 Write):** Update each scheduled task file on disk (`replace_file_content` / `write_to_file` / `apply_patch` / `apply_cas_mutation`) to set:
   ```yaml
   scheduled: null
   ```
   *(Tasks remain safely in `status: todo` in the daily backlog without phantom timeblock locks).*

### Step 4: Daily Note Status Annotation (Local A2 Write)
If `<vault>/Daily/YYYY-MM-DD.md` exists for today:
1. **MANDATORY TOOL CALL (Local A2 Write):** Update the Daily Focus Note on disk (`replace_file_content` / `write_to_file` / `apply_patch`) to inject a status callout:
   ```markdown
   > [!WARNING]
   > **Chrysalis System Status: PAUSED (<Mode>)**
   > Operational schedule paused at `HH:mm CDT`. Scheduled timeblocks cleared.
   > System re-entry target: `<resume_target>`.
   ```

### Step 5: User Confirmation Output
Output a concise confirmation message in chat:
> *"⏸️ Chrysalis is now PAUSED (`<mode>`). Active task blocks have been de-scheduled (`scheduled: null`). Learned multipliers are preserved. System will resume automatically at `<resume_target>` (or run `/resume` anytime)."*

---

## Protocol 2: System Resume (`/resume` or `/unpause`)

### Step 1: State Restoration (Local A2 Write)
1. Update `<vault>/System/Memory.md` on disk (`replace_file_content` / `write_to_file` in Antigravity, `apply_patch` / file writes in OpenAI Codex / Claude Code, or `python helpers/mdbase_helper.py --runtime apply-cas-mutation`) to restore active state:
   ```yaml
   system_state:
     pause_state:
       is_paused: false
       mode: null
       reason: null
       paused_at: null
       resume_policy: null
       resume_target: null
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
> **Mandatory Tool Call Execution (`A2`):** Merely claiming that the system is paused or resumed in chat text without executing physical file mutation tool calls (`replace_file_content` / `write_to_file` in Antigravity, `apply_patch` / file writes in OpenAI Codex / Claude Code, or `helpers/mdbase_helper.py`) to update `<vault>/System/Memory.md` and task notes is a fatal constitutional violation.
