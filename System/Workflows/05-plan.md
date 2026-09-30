---
type: agent_workflow
id: workflow-05-plan
version: "1.0.0"
stage: plan
lifecycle_state_ref: PLAN_PROPOSAL
requires_approval: false
inputs:
  - roadmap_deliverables
  - memory_horizons
outputs:
  - active_tasks_to_create
  - inert_deliverables
  - staged_sprint_blocks
---

# Workflow 05: Horizon Evaluation & Staging (`/plan` Downstream of `/ingest`)

## Objective
Executed by `/plan` via the **A2 Access Layer** immediately following `/ingest` (`01-capture.md` through `04-organize.md`, aligned with `/project` and `/zettel`). Enforces the cognitive 14-day horizon boundary, pairs materialized deliverable tasks with bio-cognitive modalities, and stages ultradian focus sprints in `System/Memory.md` (`prototype_schedule`).

## Protocol Steps
1. **Horizon Partitioning (`python helpers/mdbase_helper.py --vault "<vault>" horizon-tasks` / `filter_horizon_deliverables(horizon_days=14)`)**:
   - **Near-term (`due <= today + 14d`)**: Materialized task notes in `<vault>/TaskNotes/Tasks/YYYYMMDD-<slug>.md` with `status: todo`, `project_ref`, `deliverable_id`, and `linked_zettels` are eligible for diurnal sprint stacking in `/plan`.
   - **Uncertain (`due: null, date_uncertain: true`)**: Materialized in `<vault>/TaskNotes/Tasks/` with `scheduled: null` so they surface for deadline clarification without being auto-scheduled onto the calendar.
   - **Out-of-horizon (`due > today + 14d`)**: Retained in `<vault>/Projects/{project_id}/Roadmap.md` (`deliverables` ledger with `task_ref: null`); not scheduled until a subsequent nightly `/audit` brings them within the 14-day window.
2. **Cognitive Modality Pairing (`/plan` Protocol 1)**:
   - Pair tasks to diurnal windows: `analytical` $\to$ Peak Focus Sprints (`+01:30` to `+04:30`), `kinetic` $\to$ Slump / Kinetic Defrost (`+06:30` to `+08:15`), `synthesis` $\to$ Recovery Focus (`+08:30` to `+10:30`), `administrative` $\to$ Weekday Slump window (with weekend lockout).
3. **Contextual Location, Travel & Map Projection (`location.resolve`, `routing.estimate`, `visualization.map_projection`)**:
   - When a task carries a physical destination (`location`, `coordinates`, or `travel_policy`), `/plan` invokes `routing.estimate` (`python helpers/mdbase_helper.py --vault "<vault>" route-estimate`) if bound and enabled, or falls back to manual/default transition buffers (`fallback_mode: "manual_only"`).
   - Computes departure windows via `departure_at = arrival_at - duration_minutes - buffer_minutes`, invalidates stale `route_estimate` records when `context_fingerprint` changes, strips `ephemeral_only` provider route metrics/polylines from persistent Markdown, and enforces `map_display_permitted` rules on `visualization.map_projection` views (`TaskNotes/Views/maps-default.base`).
4. **Compile Proposal**: Serialize `prototype_schedule` in `<vault>/System/Memory.md`, mint `proposal_id`, and transition to `06-act.md` (Approval Gate).
