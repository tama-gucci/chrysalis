---
name: calibrate
description: "Handles morning check-in telemetry: unpauses system if paused, captures exact wake timestamp from user response, parses energy score (1-5), updates rolling baseline rhythms, and routes to plan under Calibration & Timeblocking Mode."
trigger: "/calibrate"
domain: runtime
reads:
  - "System/Memory.md"
  - ".agent/skills/plan/SKILL.md"
writes:
  - "System/Memory.md"
  - "chrysalis/TaskNotes/Tasks/*.md"
---

> Paths below are relative to the explicitly selected vault. The default layout keeps System, Projects, and Slipbox at the root and operational task folders under chrysalis/. For an existing encapsulated vault, resolve the corresponding resource under chrysalis/; never create a competing copy. See ARCHITECTURE.md.


# /calibrate (Morning Telemetry & Calibration Ingestion Engine)

## Execution Protocol

### 1. Morning Dispatch & Pause Check
1. Read `system_state.pause_state.is_paused` and `prototype_schedule.feedback_status` in `System/Memory.md`.
2. Dispatch prompt based on state:
   * **If Paused or Missed/Pending Evening Staging (`is_paused == true` or `feedback_status == "pending"`):**
     > *"🌅 Morning Check-In. Chrysalis is currently PAUSED (or awaiting schedule staging). Reply with your energy level (1–5) and top focus (or schedule additions) to unpause the system and stage today's agenda."*
   * **If Active with Pre-Approved Staged Prototype (`feedback_status == "approved"`):**
     > *"🌅 Morning Calibration Check-In. Reply with your current energy level (1–5) and any immediate notes when up."*

### 2. Telemetry Ingestion, System Unpause & State Serialization
* **Case A (User Replies):**
  1. **Unpause System & Log Telemetry:**
     * Capture reply timestamp as exact $T_{\text{wake}}$ (e.g., `09:18:00-05:00`).
     * Parse numerical energy score (1–5) or ingest self-reported sleep/recovery telemetry.
     * Calculate updated rolling average wake time:
       $$\text{New Rolling Wake} = \text{Current Baseline} + 0.15 \times (T_{\text{wake}} - \text{Current Baseline})$$
     * Set `applied_energy_mode: "sleep_deprived"` for 1–2, or `"optimal"` for 3–5.
     * **MANDATORY TOOL CALL:** Execute `replace_file_content` on `System/Memory.md` to:
       - Set `system_state.pause_state`: `{ is_paused: false, mode: null, reason: null, paused_at: null, resume_policy: null, resume_target: null, freeze_multiplier_decay: false }`.
       - Update session metrics and active day check-in with today's date, timestamp, energy level, and energy mode.
  2. **Route to Execution:**
     * If `prototype_schedule.feedback_status` was `"approved"`: Read and execute `.agent/skills/plan/SKILL.md` under **Protocol 2: Calibration & Timeblocking Mode**, passing $T_{\text{wake}}$ and `energy_level`.
     * If `prototype_schedule.feedback_status` was `"pending"` or system was paused: Read and execute `.agent/skills/plan/SKILL.md` under **Protocol 1: Staging Mode**, passing $T_{\text{wake}}$ and `energy_level` to stage today's focus and obtain feedback before locking timestamps.
* **Case B (User Still Does Not Respond / Inaction):**
  * Retain `system_state.pause_state.is_paused: true`.
  * Multiplier decay curves remain frozen, and no unapproved timestamps are written to disk.

---

### 3. Anti-Simulation Invariant (Tool Call Gate)
> [!CAUTION]
> **Physical Disk Mutation Mandate:** Outputting text or markdown tables in the chat response does NOT mutate vault state. The agent MUST actively invoke tool calls (`replace_file_content` / `write_to_file`) on disk files. Claiming in text that a timestamp has been locked without executing the tool call to update the task note is a fatal constitutional violation.
