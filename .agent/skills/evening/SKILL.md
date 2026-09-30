---
name: evening
description: "Orchestrates the nightly workflow: executes the unified nightly /audit (task reconciliation, automated source ingestion across configured source aliases via /ingest --all, roadmap sync, starter wedges, candidate pool), then hands off to /plan in Staging Mode to query for schedule additions, arbitrate priority with Life-Roadmap.md, and assemble tomorrow's prototype schedule."
trigger: "/evening"
domain: runtime
reads:
  - "Sources/*.md"
  - "System/Memory.md"
  - "System/Life-Roadmap.md"
  - ".agent/skills/audit/SKILL.md"
  - ".agent/skills/ingest/SKILL.md"
  - ".agent/skills/plan/SKILL.md"
writes:
  - "Sources/*.md"
  - "Projects/*/Roadmap.md"
  - "Slipbox/*.md"
  - "System/Memory.md"
  - "System/Life-Roadmap.md"
  - "TaskNotes/Tasks/*.md"
---

> Paths below are relative to the resolved personal runtime vault (`<vault>`). The default layout keeps `System/`, `Projects/`, `Slipbox/`, and `Sources/` at the root and operational task folders under `TaskNotes/`. See `ARCHITECTURE.md`.


# /evening (Evening & Midnight Operational Orchestrator)

## A2 Access Layer & Runtime Vault Resolution (Platform-Agnostic)

This skill is strictly provider- and IDE-agnostic across capable local agents (**Google Antigravity**, **OpenAI Codex**, **Claude Code**, and local CLI runtimes) operating on the **A2 Access Layer** (*Direct Local Vault Access + Local Validation & CAS Tooling*):

1. **Resolve `<vault>` (Personal Runtime Vault):**
   * Run `python System/scripts/vault_paths.py --runtime --json` (or check `$CHRYSALIS_VAULT_PATH` / `$CHRYSALIS_VAULT_ROOT`).
   * When invoked from the framework git source checkout (where `System/Life-Roadmap.md` is absent), this automatically resolves to the personal runtime vault (`~/Documents/Chrysalis`, e.g. `C:\Users\...\Documents\Chrysalis`). Never mutate tracked synthetic files in the git source checkout during personal life operations.
2. **Local Vault Reads, Queries & CAS Writes (`A2`):**
   * Read and mutate `<vault>` directly using standard local file tools (`view_file` / `replace_file_content` / `write_to_file` in Antigravity; `apply_patch` / filesystem writes in Codex/Claude) paired with `helpers/mdbase_helper.py` (`horizon-tasks`, `validate`, `revision`, `apply_cas_mutation`), headless `mdbase -C "<vault>" query/validate`, and `python System/scripts/doctor.py --vault "<vault>"`. Zero background daemons (`mdbase connect`) or cloud mdbase MCP relays (`mcp.mdbase.dev`) are required.

---

## Execution Protocol

### 1. Execute Unified Nightly Audit (Including Automated `/ingest --all`)
Read and execute `.agent/skills/audit/SKILL.md` under **Protocol 1: Unified Nightly Audit** against `<vault>`:
* **Pre-Flight Integrity Pass (`/doctor`):** Run `python System/scripts/doctor.py --vault "<vault>"` (or `python System/scripts/doctor.py --runtime`) to verify task schemas, explicit local timezones, tag registries, graph wikilinks, and multiplier bounds.
* **Task Reconciliation & Multiplier Learning:** Reconcile completed tasks in `<vault>/TaskNotes/Tasks/*.md` and update bounded telemetry multipliers ($[0.20, 2.00]$) in `<vault>/System/Memory.md`.
* **Automated Configured Source Ingestion (`/ingest --all` / `/ingest --source <alias>`):**
   * Run `python helpers/mdbase_helper.py --runtime ingest-discover --all` across enabled sources configured in `<vault>/System/Memory.md` (`ingestion.sources`, such as `media` and `quick-capture`; legacy `/ingest --drive` maps to `--source media`).
   * Translate new or revised `file`, `text`, and `structured_task` inputs into formatted Markdown records (`<vault>/Sources/*.md`, `<vault>/TaskNotes/Tasks/*.md`) and execute Workflows `01-capture` through `04-organize` (aligning `/project` and `/zettel`) locally on `<vault>` via the A2 access layer.
   * *Graceful Continuation:* If a configured source has 0 unindexed items (`ok_empty` / `ok_fully_indexed`) or its external connector/mount is not currently connected (`operation_unavailable` / `mount_unavailable`), record the explicit status notice and proceed directly to 14-day horizon ingestion without halting `/evening`.
* **14-Day Horizon Ingestion:** Run `python helpers/mdbase_helper.py --vault "<vault>" horizon-tasks` (or `python helpers/mdbase_helper.py --runtime horizon-tasks`) to inspect upcoming 14-day project & roadmap milestones (plus `date_uncertain: true` items) and materialize any missing task notes in `<vault>/TaskNotes/Tasks/`.
* **Starter Wedges & Auto-Pause Check:** Inject Starter Wedges into stalled tasks and evaluate auto-pause status.

### 2. Pause & Unresponsive State Gate
Check `system_state.pause_state.is_paused`, `mode`, and `resume_target` in `<vault>/System/Memory.md`:
* **Case A (Manual Pause with Evening Re-Entry — e.g. `mode == "maintenance"` or `resume_target == "evening"`):**
  * Mutate `<vault>/System/Memory.md` on disk (via local file edit tool / `apply_cas_mutation`) to automatically unpause (`is_paused: false`, `mode: null`, `reason: null`, `paused_at: null`, `resume_policy: null`, `resume_target: null`).
  * Greet the user seamlessly with a fresh staging query and proceed directly to Step 3.
* **Case B (Multi-Day Horizon Pause — e.g. `mode == "vacation"` with future date):**
  * If today's date < `resume_target`, output status (*"🌴 Chrysalis is currently PAUSED on vacation until `<resume_target>`. Run `/resume` anytime to reactivate."*) and halt.
  * If today's date == `resume_target` (or the evening prior to resumption), auto-unpause and proceed to Step 3.
* **Case C (Auto-Unresponsive Gate — `mode == "auto_unresponsive"`):**
  * Output the pause notification:
    > *"⚠️ Chrysalis is currently PAUSED because the previous prototype schedule received no feedback. Would you like to unpause the system and stage tomorrow's focus? (Reply 'Unpause' to proceed)."*
  * Halt execution until the user confirms. Upon unpause confirmation, set `is_paused: false` in `<vault>/System/Memory.md` and proceed to Step 3.
* **Case D (Active / Not Paused):** Proceed directly to Step 3.

### 3. Initiate Staging Mode (Schedule Addition Query, Tool-Gated Materialization & Priority Arbitration)
Read and execute `.agent/skills/plan/SKILL.md` under **Protocol 1: Staging Mode** on `<vault>`:
1. Prompt the user for any schedule additions or new developments in natural language:
    > *"🌙 Evening Staging. Is there anything in particular you'd like included in tomorrow's schedule, or any new developments to note? (e.g., lab equipment setup, personal errand, or focus preference)"*
2. Upon receiving user input:
   * **Task Materialization (Local A2 Write):** If the user requests a new task, immediately create the task note in `<vault>/TaskNotes/Tasks/YYYYMMDD-<slug>.md` with full schema frontmatter (`status: todo`, `scheduled: null`) and validate via `python helpers/mdbase_helper.py --vault "<vault>" validate TaskNotes/Tasks/YYYYMMDD-<slug>.md`.
   * **Roadmap Updates (Local A2 Write):** If priorities shifted, update `<vault>/System/Life-Roadmap.md` and `<vault>/Projects/*/Roadmap.md`.
   * **Priority Arbitration:** Arbitrate priority against `<vault>/System/Life-Roadmap.md` (active milestones remain primary anchor unless no urgent deadlines exist; user requests are integrated during downtime/slump/recovery windows).
   * **Prototype Serialization (Local A2 Write):** Update `<vault>/System/Memory.md` on disk to serialize `prototype_schedule` (`staged_user_intent`, `target_date`, `staged_anchor_task`, `staged_support_tasks`, `feedback_status: "pending"`).
   * **Present Prototype Table:** Present the prototype schedule table in chat with clickable task links and candidate gap-fillers.
3. Evaluate user feedback branch (lifecycle/cycle-boundary driven; no artificial countdown timer):
   * **Branch A (User Approves):** Update `<vault>/System/Memory.md` on disk to set `prototype_schedule.feedback_status: "approved"` and log to `feedback_history`. Run `mdbase -C "<vault>" validate` (or `python helpers/mdbase_helper.py --vault "<vault>" validate System/Memory.md`) to confirm clean collection state. The schedule is ready for morning `/calibrate`.
   * **Branch B (User Modifies / Swaps Tasks):** Re-arbitrate priorities, update `prototype_schedule` in `<vault>/System/Memory.md`, and re-present the table.
   * **Branch C (User Does Not Respond / Ignored):** `prototype_schedule.feedback_status` remains `"pending"`. If the operational boundary transitions (e.g., morning check-in or next nightly audit runs without feedback), the system triggers constitutional auto-pause (`is_paused: true`, `reason: "unresponsive_nightly_audit"`) to prevent unapproved schedule drift and preserves learned multiplier curves.

---

### 4. Anti-Simulation Invariant
> [!CAUTION]
> **Physical Disk Mutation Mandate:** Outputting text or markdown tables in chat never mutates system state. The agent MUST actively execute physical local file mutations (`replace_file_content` / `write_to_file` in Antigravity, `apply_patch` / file writes in Codex/Claude, or `helpers/mdbase_helper.py`) on `<vault>` files. Claiming in text that tasks or prototypes have been staged without mutating `<vault>/TaskNotes/Tasks/*.md` and `<vault>/System/Memory.md` on disk is a fatal constitutional violation.
