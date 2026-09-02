---
name: audit
description: "Unified nightly system reconciliation: executes pre-flight integrity pass via /doctor, updates telemetry multiplier learning bounded in [0.20, 2.00], chronotype delta learning, multi-project and roadmap horizon ingestion, starter wedge injection, candidate task pool maintenance, proactive capability expansion (#chrysalis idea synthesis), and closed-loop recursive self-improvement (RSI) friction analysis."
trigger: "/audit"
reads:
  - "chrysalis/TaskNotes/Tasks/*.md"
  - "chrysalis/TaskNotes/Archive/*.md"
  - "chrysalis/Projects/*/Roadmap.md"
  - "chrysalis/Slipbox/*.md"
  - "chrysalis/System/Scheduling-Memory.md"
  - "chrysalis/System/Life-Roadmap.md"
  - "chrysalis/System/System-Health.md"
  - "chrysalis/System/Changelog.md"
  - "chrysalis/.agent/skills/*/*.md"
writes:
  - "chrysalis/System/Scheduling-Memory.md"
  - "chrysalis/System/Life-Roadmap.md"
  - "chrysalis/System/System-Health.md"
  - "chrysalis/System/Changelog.md"
  - "chrysalis/TaskNotes/Tasks/*.md"
  - "chrysalis/TaskNotes/Workflows/*.md"
  - "chrysalis/Dashboard.md"
  - "chrysalis/.agent/skills/*/*.md"
  - "chrysalis/.agent/skills/.backup/*.md"
  - "chrysalis/Slipbox/*.md"
---

# /audit (Unified Nightly System Audit, Multiplier Learning & RSI Engine)

## Protocol 0: Full System Integrity & Diagnostic Suite (`/audit --integrity` or `/audit --health`)

> [!NOTE]
> Protocol 0 delegates directly to the canonical diagnostic skill [`doctor`](file:///home/sin/GoogleDrive/chrysalis/.agent/skills/doctor/SKILL.md). Calling `/audit --integrity` or `/audit --health` executes the 6-point integrity suite from `/doctor` without triggering the nightly learning lifecycle.

---

## Protocol 1: Unified Nightly Audit (`/audit` or `/audit --nightly`)

Execute the complete nightly audit and capability expansion sequence across the entire vault:

### Step 0: Mandatory Pre-Flight Health Pass (Delegated to `/doctor`)
Execute the full 6-point diagnostic pass defined in [`doctor`](file:///home/sin/GoogleDrive/chrysalis/.agent/skills/doctor/SKILL.md). If critical unrecoverable corruption is found, halt execution and alert user. Otherwise, apply auto-heals and proceed to Step 1.

### Step 1: Task Lifecycle, Multipliers & Chronotype Delta Learning
1. Scan `chrysalis/TaskNotes/Tasks/*.md` (with `status: done`) and `chrysalis/TaskNotes/Archive/*.md` for tasks completed in the preceding 24 hours.
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
6. Persist updated multipliers, chronotype records, and `last_audit` timestamp to `chrysalis/System/Scheduling-Memory.md`.

### Step 2: Multi-Project & Roadmap Horizon Ingestion
1. **Project Roadmap Synchronization:** Crawl `chrysalis/Projects/*/Roadmap.md`. Sync completed deliverables and status back into `chrysalis/System/Life-Roadmap.md`.
2. **Milestone Progress Reconciliation:** Cross-reference completed tasks in `TaskNotes/Archive/` with active milestones. Mark corresponding key results (`- [x]`) as complete.
3. **14-Day Horizon Ingestion:**
   * Scan `Life-Roadmap.md` and active project roadmaps for upcoming milestones occurring within the next 14 calendar days lacking active TaskNotes.
   * Calculate each task's `timeEstimate` using the tag's active multiplier from `Scheduling-Memory.md` (applying the `1.00` fallback rule if unlisted).
   * Create structured `.md` files in `chrysalis/TaskNotes/Tasks/` with complete YAML frontmatter (`dateCreated`, `created`, `priority`, `urgency_tier`, `modality`, `status: todo`, `scheduled: null`).

### Step 3: Friction Reduction & Starter Wedge Injection
Scan active tasks in `TaskNotes/Tasks/` for stalled items ($\ge 48\text{h}$ in `status: todo` with `timeEstimate >= 45m` and `micro_chunked: false`). Inject a 3-step Starter Wedge checklist ($< 15\text{m}$ each) into the note body and set `micro_chunked: true`.

### Step 4: Inferred Task Pool Maintenance & Preference Tuning
1. Read `inferred_task_pool.interaction_history` from recent cycles in `Scheduling-Memory.md`:
   * Adjust `learning_weights` ($+0.10$ for staged/selected tags, $-0.15$ for dismissed tags, bounded in $[0.20, 2.00]$).
   * Incorporate qualitative `user_critique` notes to filter candidate archetypes.
2. Prune tasks marked `staged` or `dismissed`, as well as candidates presented $\ge 4$ times without user selection.
3. Synthesize 2–4 new candidates based on upcoming roadmap milestones, maintaining the active pool at 4–6 available items with explicit `modality` tags.

### Step 5: Proactive Capability Expansion & Orchestrator Telemetry
1. **Scan for Feature Notes:** Query all vault files containing tag `chrysalis` where `integration_status == "unintegrated"` or missing.
2. **Multi-Vector Architectural Brainstorming:** For each unintegrated note, analyze the 5 Chrysalis integration pathways:
   - **Workflows:** New TaskNotes automated pipelines.
   - **Skills:** Modular skill additions or protocol mutations in `.agent/skills/`.
   - **Dashboard UI:** Obsidian Dataview blocks, callouts, or summaries.
   - **Operational Memory:** Schema expansions in `Scheduling-Memory.md`.
   - **Orchestrator Adapters:** Capability tier updates, floating alias mappings, or model release integrations in `System/Orchestrators/*`.
3. **Environment & Model Telemetry Audit:** Inspect `System/Environment/*.md` manifests and local plugin configurations. If new CLI tools or model releases are detected, formulate an `Adapter-Spec.md` capability tier update.
4. **Formulate Feature Integration Spec:**
   * Generate complete code/markdown specifications for the proposed feature or adapter update.
   * Log proposal in `chrysalis/System/Changelog.md` under `## 💡 Staged Feature Proposals`.
   * Queue proposal into `prototype_schedule.pending_feature_proposals` in `Scheduling-Memory.md` for evening staging review.
5. **Integration Finalization:** Upon user approval, deploy the artifacts, update note to `integration_status: integrated`, and record deployment in `System/Changelog.md`.

### Step 6: Closed-Loop RSI Friction Analysis & Slipbox Grounding
1. **Friction Diagnostic:** Identify task tags with multipliers $> 1.40$ or tasks stalled $> 72\text{h}$. Review `schedule_refinement_memory.feedback_history` for recurring user edits or prompt friction.
2. **Slipbox Knowledge Retrieval:** Query `chrysalis/Slipbox/*.md` for matching principles (`#concept/*`, `#principle/*`) to ground the optimization hypothesis in domain theory.
3. **Constitutional Pre-Commit Linter:** Verify all invariant laws (timezone, substrate, schema, feedback gate).
4. **Snapshot & Mutation:** Backup existing skill to `.agent/skills/.backup/<skill>_<timestamp>.md`, apply verified edits to `.agent/skills/<skill>/SKILL.md`, and log entry to `System/Changelog.md`.

### Step 7: Auto-Pause Evaluation
If `prototype_schedule.feedback_status == "pending"` from the previous cycle without user response and system is not already under an active manual pause (`system_state.pause_state.is_paused == false`):
* Set `system_state.pause_state.is_paused: true`, `mode: "auto_unresponsive"`, and `reason: "unresponsive_nightly_audit"`.
* Set `freeze_multiplier_decay: true`.

---

## Protocol 2: Skill Snapshot Rollback (`/audit --rollback [skill]`)
If a self-improved skill produces degraded behavior or user rejection:
1. Locate the most recent backup in `chrysalis/.agent/skills/.backup/<skill>_*.md`.
2. Restore the backup to `chrysalis/.agent/skills/<skill>/SKILL.md`.
3. Log the rollback event in `chrysalis/System/Changelog.md`.
4. Notify the user of successful restoration.

---

## Protocol 3: Roadmap & Inferred Pool Mutation (`/audit --mutate`)
Triggered on-demand when `/plan` receives user feedback requiring structural system changes:
1. **Roadmap Mutations:** Append, modify, or re-scope milestones and horizons directly in `chrysalis/System/Life-Roadmap.md` and relevant `Projects/*/Roadmap.md`.
2. **Inferred Pool Overhauls:** Refresh, prune, or re-generate `inferred_task_pool` candidates matching specific user requests.
