---
name: morning
description: "Orchestrates the morning workflow: executes /calibrate to unpause system, capture exact wake time and energy telemetry (1-5), then delegates to /plan under Calibration Mode to shift timeblocks and lock scheduled timestamps."
trigger: "/morning"
domain: runtime
reads:
  - "System/Scheduling-Memory.md"
  - ".agent/skills/calibrate/SKILL.md"
  - ".agent/skills/plan/SKILL.md"
writes:
  - "System/Scheduling-Memory.md"
  - "chrysalis/Tasks/*.md"
  - "chrysalis/Daily/YYYY-MM-DD.md"
---

> Paths below are relative to the explicitly selected vault. The default layout keeps System, Projects, and Slipbox at the root and operational task folders under chrysalis/. For an existing encapsulated vault, resolve the corresponding resource under chrysalis/; never create a competing copy. See ARCHITECTURE.md.


# /morning (Morning Operational Orchestrator)

## Execution Protocol

### 1. Execute Morning Calibration Check-In & State Gate
Read and execute `.agent/skills/calibrate/SKILL.md`:
1. Check `system_state.pause_state.is_paused` and `prototype_schedule.feedback_status` in `Scheduling-Memory.md`.
2. Dispatch proactive check-in prompt:
   * **If Active with Pre-Approved Prototype (`feedback_status == "approved"`):**
     > *"🌅 Morning Calibration Check-In. Reply with your current energy level (1–5) and any immediate notes when up."*
   * **If Paused or Missed/Pending Staging (`is_paused == true` or `feedback_status == "pending"`):**
     > *"🌅 Morning Check-In. Chrysalis is currently PAUSED (or awaiting schedule staging). Reply with your energy level (1–5) and top focus (or schedule additions) to unpause the system and stage today's agenda."*

### 2. Response Ingestion & Tool-Gated Execution Routing
* **Case A (User Responds):**
  1. **Unpause System & Log Telemetry:** Call `replace_file_content` on `Scheduling-Memory.md` to unpause (`is_paused: false`, `mode: null`, `reason: null`, `paused_at: null`, `resume_policy: null`, `resume_target: null`, `freeze_multiplier_decay: false`), update `morning_checkin.active_today`, compute rolling wake baseline, and log to `checkin_history`.
  2. **Route Scheduling Mode:**
     * **If Pre-Approved (`feedback_status == "approved"`):** Execute `.agent/skills/plan/SKILL.md` under **Protocol 2: Calibration & Timeblocking Mode** to shift diurnal timeblocks, execute tool calls to serialize `scheduled: "YYYY-MM-DDTHH:mm:ss-05:00"` into all scheduled `chrysalis/Tasks/*.md` notes, and write the calibrated daily focus note `chrysalis/Daily/YYYY-MM-DD.md`.
     * **If Previously Paused / Pending:** Execute `.agent/skills/plan/SKILL.md` under **Protocol 1: Staging Mode** using $T_{\text{wake}}$ and energy level to stage today's focus, present the prototype table, and obtain approval before locking timestamps.
* **Case B (User Still Does Not Respond / Inaction):**
  * Retain `system_state.pause_state.is_paused: true`.
  * Multiplier decay curves remain frozen, and no unapproved timestamps are written to disk.

---

### 3. Anti-Simulation Invariant
> [!CAUTION]
> **Physical Disk Mutation Mandate:** Outputting text or markdown tables in the chat response does NOT mutate vault state. The agent MUST actively invoke tool calls (`replace_file_content` / `write_to_file`) on disk files. Claiming in text that a timestamp has been locked without executing the tool call to update the task note is a fatal constitutional violation.
