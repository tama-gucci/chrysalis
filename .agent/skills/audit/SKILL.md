---
name: audit
description: "Runtime Operational Audit: Unified nightly system reconciliation: executes pre-flight integrity pass via /doctor, updates telemetry multiplier learning bounded in [0.20, 2.00], chronotype delta learning, multi-project and roadmap horizon ingestion, starter wedge injection, candidate task pool maintenance, and auto-pause evaluation."
trigger: "/audit"
domain: runtime
reads:
  - "chrysalis/Tasks/*.md"
  - "chrysalis/Archive/*.md"
  - "Projects/*/Roadmap.md"
  - "System/Scheduling-Memory.md"
  - "System/Life-Roadmap.md"
  - "System/System-Health.md"
writes:
  - "System/Scheduling-Memory.md"
  - "System/Life-Roadmap.md"
  - "chrysalis/Tasks/*.md"
  - "Dashboard.md"
---

> Paths below are relative to the explicitly selected vault. The default layout keeps System, Projects, and Slipbox at the root and operational task folders under chrysalis/. For an existing encapsulated vault, resolve the corresponding resource under chrysalis/; never create a competing copy. See ARCHITECTURE.md.


# /audit (Runtime Operational Audit & Nightly Reconciliation Engine)

## Supported Commands & Triggers
* `/audit` (or `/audit --nightly`) — Executes the complete nightly operational reconciliation lifecycle.
* `/audit --integrity` (or `/audit --health`) — Executes the 6-point pre-flight integrity suite (delegated directly to [`doctor`](../doctor/SKILL.md)).
* `/audit --mutate` — On-demand roadmap milestone and candidate task pool mutation.

---

## Protocol 0: Full System Integrity & Diagnostic Suite (`/audit --integrity` or `/audit --health`)

> [!NOTE]
> Protocol 0 delegates directly to the canonical diagnostic skill [`doctor`](../doctor/SKILL.md). Calling `/audit --integrity` or `/audit --health` executes the 6-point integrity suite from `/doctor` without triggering the nightly learning lifecycle.

---

## Protocol 1: Unified Nightly Audit (`/audit` or `/audit --nightly`)

Execute the complete nightly audit and operational reconciliation sequence across the entire vault:

### Step 0: Mandatory Pre-Flight Health Pass (Delegated to `/doctor`)
Execute the full 6-point diagnostic pass defined in [`doctor`](../doctor/SKILL.md). If critical unrecoverable corruption is found, halt execution and alert user. Otherwise, apply auto-heals and proceed to Step 1.

### Step 1: Task Lifecycle, Multipliers & Chronotype Delta Learning
1. Scan `chrysalis/Tasks/*.md` (with `status: done`) and `chrysalis/Archive/*.md` for tasks completed in the preceding 24 hours.
2. Extract exact session durations: $T_{\text{actual}} = \text{completedAt} - \text{startedAt}$ (in minutes).
3. **Multiplier Resolution & Bounds Clamping:**
   * If a tag has no existing entry in `tag_multipliers`, initialize baseline multiplier at `1.00`.
   * Update tag multipliers using the learning formula:
     $$\text{New Multiplier} = \text{Current Multiplier} + 0.10 \times \left(\frac{T_{\text{actual}}}{T_{\text{estimated}}} - \text{Current Multiplier}\right)$$
   * **Invariant Bounds Clamping:** Clamp every updated multiplier strictly to $[0.20, 2.00]$.
4. Apply passive decay ($0.05$ toward $1.00$) for tags with zero sessions over 7 consecutive days.
5. **Chronotype Delta Learning:**
   * Record session start hour and efficiency ratio ($T_{\text{actual}} / T_{\text{estimated}}$) into `chronotype_telemetry.hourly_efficiency_history`.
   * If analytical tasks completed between $+02:30$ and $+05:30$ show $> 25\%$ higher efficiency than morning sprints, adjust `diurnal_baselines.relative_offsets.peak_sprint_1_start` by $0.10 \times \Delta$ toward the learned peak.
6. Persist updated multipliers, chronotype records, and `last_audit` timestamp to `System/Scheduling-Memory.md`.

### Step 2: Multi-Project & Roadmap Horizon Ingestion
1. **Project Roadmap Synchronization:** Crawl `Projects/*/Roadmap.md`. Sync completed deliverables and status back into `System/Life-Roadmap.md`.
2. **Milestone Progress Reconciliation:** Cross-reference completed tasks in `chrysalis/Archive/` with active milestones. Mark corresponding key results (`- [x]`) as complete.
3. **14-Day Horizon Ingestion:**
   * Scan `Life-Roadmap.md` and active project roadmaps for upcoming milestones occurring within the next 14 calendar days lacking active task notes.
   * Calculate each task's `timeEstimate` using the tag's active multiplier from `Scheduling-Memory.md` (applying the `1.00` fallback rule if unlisted).
   * Create structured `.md` files in `chrysalis/Tasks/` with complete YAML frontmatter (`dateCreated`, `created`, `priority`, `urgency_tier`, `modality`, `status: todo`, `scheduled: null`, `linked_zettels: []`, `project_ref: null`, `googleCalendarEventId: null`).

### Step 3: Friction Reduction & Starter Wedge Injection
Scan active tasks in `chrysalis/Tasks/` for stalled items ($\ge 48\text{h}$ in `status: todo` with `timeEstimate >= 45m` and `micro_chunked: false`). Inject a 3-step Starter Wedge checklist ($< 15\text{m}$ each) into the note body and set `micro_chunked: true`.

### Step 4: Inferred Task Pool Maintenance & Preference Tuning
1. Read `inferred_task_pool.interaction_history` from recent cycles in `Scheduling-Memory.md`:
   * Adjust `learning_weights` ($+0.10$ for staged/selected tags, $-0.15$ for dismissed tags, bounded in $[0.20, 2.00]$).
   * Incorporate qualitative `user_critique` notes to filter candidate archetypes.
2. Prune tasks marked `staged` or `dismissed`, as well as candidates presented $\ge 4$ times without user selection.
3. Synthesize 2–4 new candidates based on upcoming roadmap milestones, maintaining the active pool at 4–6 available items with explicit `modality` tags.

### Step 5: Auto-Pause Evaluation
If `prototype_schedule.feedback_status == "pending"` from the previous cycle without user response and system is not already under an active manual pause (`system_state.pause_state.is_paused == false`):
* Set `system_state.pause_state.is_paused: true`, `mode: "auto_unresponsive"`, and `reason: "unresponsive_nightly_audit"`.
* Set `freeze_multiplier_decay: true`.

---

## Protocol 2: Roadmap & Inferred Pool Mutation (`/audit --mutate`)
Triggered on-demand when `/plan` receives user feedback requiring structural system changes:
1. **Roadmap Mutations:** Append, modify, or re-scope milestones and horizons directly in `System/Life-Roadmap.md` and relevant `Projects/*/Roadmap.md`.
2. **Inferred Pool Overhauls:** Refresh, prune, or re-generate `inferred_task_pool` candidates matching specific user requests.
