---
name: evening
description: "Orchestrates the nightly workflow: executes the unified nightly /audit (task reconciliation, roadmap sync, starter wedges, candidate pool), checks for optional architectural evolution (/evolve), then hands off to /plan in Staging Mode to query for schedule additions, arbitrate priority with Life-Roadmap.md, and assemble tomorrow's prototype schedule."
trigger: "/evening"
reads:
  - "chrysalis/System/Scheduling-Memory.md"
  - "chrysalis/System/Life-Roadmap.md"
  - "chrysalis/.agent/skills/audit/SKILL.md"
  - "chrysalis/.agent/skills/evolve/SKILL.md"
  - "chrysalis/.agent/skills/plan/SKILL.md"
writes:
  - "chrysalis/System/Scheduling-Memory.md"
  - "chrysalis/System/Life-Roadmap.md"
  - "chrysalis/TaskNotes/Tasks/*.md"
---

# /evening (Evening & Midnight Operational Orchestrator)

## Execution Protocol

### 1. Execute Unified Nightly Audit
Read and execute `chrysalis/.agent/skills/audit/SKILL.md` under **Protocol 1: Unified Nightly Audit**:
* Reconcile completed tasks & update bounded telemetry multipliers ($[0.20, 2.00]$).
* Ingest 14-day upcoming project & roadmap milestones.
* Inject Starter Wedges into stalled tasks.
* Maintain candidate task pools and execute auto-pause evaluation.

### 1b. Proactive Capability & Architectural Evolution Pass (Personal Installation / Opt-In)
If `chrysalis/.agent/skills/evolve/SKILL.md` is present in the workspace:
* Read and execute `chrysalis/.agent/skills/evolve/SKILL.md` under **Protocol 1: Proactive Capability Expansion**:
  - Scan for unintegrated notes tagged `#chrysalis`.
  - Synthesize 5-vector integration specs (Workflows, Skills, Dashboard UI, Operational Memory, Adapters).
  - Queue pending proposals into `prototype_schedule.pending_feature_proposals` in `Scheduling-Memory.md` for evening staging presentation.

### 2. Pause & Unresponsive State Gate
Check `system_state.pause_state.is_paused`, `mode`, and `resume_target` in `chrysalis/System/Scheduling-Memory.md`:
* **Case A (Manual Pause with Evening Re-Entry — e.g. `mode == "maintenance"` or `resume_target == "evening"`):**
  * Execute `replace_file_content` on `Scheduling-Memory.md` to automatically unpause (`is_paused: false`, `mode: null`, `reason: null`, `paused_at: null`, `resume_policy: null`, `resume_target: null`, `freeze_multiplier_decay: false`).
  * Greet the user seamlessly with a fresh staging query and proceed directly to Step 3.
* **Case B (Multi-Day Horizon Pause — e.g. `mode == "vacation"` with future date):**
  * If today's date < `resume_target`, output status (*"🌴 Chrysalis is currently PAUSED on vacation until `<resume_target>`. Run `/resume` anytime to reactivate."*) and halt.
  * If today's date == `resume_target` (or the evening prior to resumption), auto-unpause and proceed to Step 3.
* **Case C (Auto-Unresponsive Gate — `mode == "auto_unresponsive"`):**
  * Output the pause notification:
    > *"⚠️ Chrysalis is currently PAUSED because the previous prototype schedule received no feedback. Would you like to unpause the system and stage tomorrow's focus? (Reply 'Unpause' to proceed)."*
  * Halt execution until the user confirms. Upon unpause confirmation, set `is_paused: false` and proceed to Step 3.
* **Case D (Active / Not Paused):** Proceed directly to Step 3.

### 3. Initiate Staging Mode (Schedule Addition Query, Tool-Gated Materialization & Priority Arbitration)
Read and execute `chrysalis/.agent/skills/plan/SKILL.md` under **Protocol 1: Staging Mode**:
1. Prompt the user for any schedule additions or new developments in natural language:
    > *"🌙 Evening Staging. Is there anything in particular you'd like included in tomorrow's schedule, or any new developments to note? (e.g., ebike maintenance, personal errand, or focus preference)"*
2. Upon receiving user input:
   * **Task Materialization (Tool Call):** If the user requests a new task, immediately execute file tool calls to create the task note in `chrysalis/TaskNotes/Tasks/YYYYMMDD-<slug>.md` with full schema frontmatter (`status: todo`, `scheduled: null`).
   * **Roadmap Updates (Tool Call):** If priorities shifted, execute tool calls on `chrysalis/System/Life-Roadmap.md` and `chrysalis/Projects/*/Roadmap.md`.
   * **Priority Arbitration:** Arbitrate priority against `Life-Roadmap.md` (active milestones remain primary anchor unless no urgent deadlines exist; user requests are integrated during downtime/slump/recovery windows).
   * **Prototype Serialization (Tool Call):** Execute `replace_file_content` on `chrysalis/System/Scheduling-Memory.md` to serialize `prototype_schedule` (`staged_user_intent`, `target_date`, `staged_anchor_task`, `staged_support_tasks`, `pending_feature_proposals`, `feedback_status: "pending"`).
   * **Present Prototype Table:** Present the prototype schedule table in chat with clickable task links, candidate gap-fillers, and any pending feature proposals.
3. Evaluate user feedback branch (lifecycle/cycle-boundary driven; no artificial countdown timer):
   * **Branch A (User Approves):** Execute `replace_file_content` on `Scheduling-Memory.md` to set `prototype_schedule.feedback_status: "approved"` and log to `feedback_history`. The schedule is ready for morning `/calibrate`.
   * **Branch B (User Modifies / Swaps Tasks):** Re-arbitrate priorities, execute tool calls to update `prototype_schedule` in `Scheduling-Memory.md`, and re-present the table.
   * **Branch C (User Does Not Respond / Ignored):** `prototype_schedule.feedback_status` remains `"pending"`. If the operational boundary transitions (e.g., morning check-in or next nightly audit runs without feedback), the system triggers constitutional auto-pause (`is_paused: true`, `reason: "unresponsive_nightly_audit"`) to prevent unapproved schedule drift and freezes multiplier decay curves.

---

### 4. Anti-Simulation Invariant
> [!CAUTION]
> **Physical Disk Mutation Mandate:** Outputting text or markdown tables in chat never mutates system state. The agent MUST actively execute file tool calls (`replace_file_content` / `write_to_file`) on disk files. Claiming in text that tasks or prototypes have been staged without executing the tool calls to update the task files and `Scheduling-Memory.md` is a fatal constitutional violation.
