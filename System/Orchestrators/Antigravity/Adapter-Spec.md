---
type: orchestrator_adapter_spec
id: chrysalis-orchestrator-antigravity
name: "Google Antigravity Orchestrator Adapter"
orchestrator_platform: "google_antigravity"
status: active
version: 1.0.0
last_updated: "2026-09-03T12:05:00-05:00"
---

# 🛸 Google Antigravity Orchestrator Adapter

This specification defines the runtime contracts, execution topologies, scheduled automation hooks, and tool bindings when operating **Google Antigravity** as the **Autonomous Production Orchestrator** for Chrysalis over the Markdown filesystem substrate.

---

## 🌐 Architectural Overview

Chrysalis is built on an open Markdown substrate hosted on synced cloud storage (e.g., Google Drive) or local disk. Google Antigravity acts as the unified, autonomous orchestrator across both daily life operations and system development:

```mermaid
graph TD
    User["User Interaction / On-Demand"] --> AGY["🛸 Google Antigravity (Autonomous Orchestrator)"]
    CronOptional["Optional Scheduled Timers (08:30 / 21:30)"] --> AGY
    
    AGY --> DailyOps["Daily Focus Operations:<br/>• /morning (Wake Telemetry & Diurnal Shift)<br/>• /evening (Task Reconciliation & Focus Staging)<br/>• /calibrate • /plan • /task • /audit • /doctor"]
    
    AGY <-->|Physical Tool Calls (Anti-Simulation Compliant)| Substrate["☁️ Chrysalis Filesystem Substrate<br/>(Markdown Files & YAML Frontmatter)"]
```

---

## ⚙️ Supported Execution Topologies

Antigravity accommodates flexible deployment models depending on user preferences and hardware availability:

### 1. Mode 1: Interactive / On-Demand (Default)
* **Runtime:** Standard Antigravity IDE, Antigravity 2.0 desktop application, or `agy` CLI on the user's active workstation or laptop.
* **Workflow:** The user opens the Chrysalis workspace and triggers operational runbooks on-demand via slash commands:
  * Morning wake calibration: `/morning` or `/plan --calibrate`
  * Evening task audit and focus staging: `/evening` or `/plan --stage`
  * Dynamic task ingestion: `/task <shorthand>`
  * System integrity checks: `/doctor`
* **Characteristics:** Zero background resource overhead when the application is closed.

### 2. Mode 2: Automated / Scheduled (Optional Always-On)
* **Runtime:** A continuous instance of Antigravity running on a dedicated host (e.g., a low-power home server, always-on PC, or VM) syncing with the vault substrate.
* **Workflow:** Leverages Antigravity's native `schedule` tool (one-shot timers or recurring 5-field cron jobs) to trigger automated notifications:
  * **Morning Trigger (`08:30` local time):** Evaluates pause state, requests wake time and energy score ($1-5$), and locks calibrated focus timestamps.
  * **Evening Trigger (`21:30` local time):** Executes `/audit` to reconcile completed session deltas, checks 14-day roadmap horizons, and stages tomorrow's prototype schedule.
* **Characteristics:** Proactive, hands-free life rhythm synchronization without manual trigger requirements.

### 3. Mode 3: Ambient Gateway Service on "Golem" (Surface Pro X Production Topology)
* **Runtime:** Ambient Chrysalis Gateway (`apps/gateway/`, FastAPI on port `8765`) running 24/7 on Golem (Surface Pro X on Windows 11 on ARM64, 16GB total RAM: 4GB Hyper-V Home Assistant, 12GB operational memory).
* **Workflow:** The gateway wraps Antigravity's headless language server (`language_server.exe agentapi` / `agentapi.bat` on Windows, or POSIX equivalent) via `AntigravityBridge`. Mobile and Wear OS clients connect over a secure Cloudflare Zero-Trust Tunnel.
* **Port Separation:** Operates strictly on port `8765`, coexisting peacefully with the Obsidian TaskNotes plugin on port `8080`.

---

## 🛠️ Tool Bindings & Anti-Simulation Law

Unlike consumer web LLM interfaces that lack filesystem mutation tools, Antigravity possesses native tool-calling capabilities that strictly satisfy the **Chrysalis Anti-Simulation Law**:

| Operation | Native Antigravity Tool | Target Files |
| :--- | :--- | :--- |
| **Inspect State** | `view_file` | `System/Scheduling-Memory.md`, `TaskNotes/Tasks/*.md`, `System/Life-Roadmap.md`, `Slipbox/*.md` |
| **Lock Timestamps** | `replace_file_content` | `TaskNotes/Tasks/*.md` (`scheduled: "YYYY-MM-DDTHH:mm:ss-05:00"`) |
| **Create Notes** | `write_to_file` | `TaskNotes/Tasks/*.md`, `YYYY-MM-DD.md` (Daily Note), `Slipbox/*.md` (/zettel) |
| **Update Memory** | `replace_file_content` | `System/Scheduling-Memory.md` (`morning_checkin`, `prototype_schedule`) |
| **Hypergraph Linking** | `replace_file_content` | `Projects/*/Roadmap.md` (Ref Files), `TaskNotes/Tasks/*.md` (`linked_zettels`) |
| **Run Diagnostics** | `run_command`, `write_to_file` | `System/System-Health.md` (via `/doctor`) |
| **Scheduled Automation** | `schedule`, `manage_task` | Background cron triggers (`08:30` and `21:30`) |

> [!IMPORTANT]
> **Anti-Simulation Invariant:** Chat text output alone NEVER mutates system state. Antigravity must always execute physical tool calls (`replace_file_content` / `write_to_file`) to commit schedule blocks, hypergraph links, and state transitions to disk.

---

## 📅 Calendar Ingestion & Collision Avoidance

Antigravity ensures zero collisions with external commitments using a multi-layer strategy:

1. **Model C (Mobile OS Bridge) & Client-Synchronized Cache (Primary):**
   * Reads `calendar_sync.cached_events` from `System/Scheduling-Memory.md` (populated and kept current by client-side calendar synchronization via Android `CalendarContract`, requiring zero Google Cloud Console setup).
2. **Decoupled iCal Ingestion Fallback:**
   * Standalone/headless environments ingest calendar feeds via `fetch_ical.py` using Google Calendar's private `.ics` URL.
3. **TaskNotes MCP Integration (Direct Query):**
   * If the TaskNotes MCP server is registered in `mcp_config.json`, Antigravity calls `tasknotes_get_calendar_events` directly to ingest real-time calendar commitments from port `8080`.
4. **Bio-Cognitive Wrapping:** Focus sprint blocks (75–90m) automatically wrap around external meetings, appointments, and travel buffers without overlap.

---

## ⏰ Scheduled Automation Prompt Payloads (Optional Mode 2)

When running in automated scheduled mode, Antigravity executes the following standardized prompts:

### 1. Morning Calibration Trigger
```text
Execute skill /morning:
1. Read "System/Scheduling-Memory.md" and check pause_state. If paused, respect the pause policy.
2. Ingest external calendar commitments from "calendar_sync.cached_events" or TaskNotes MCP.
3. Prompt the user for morning wake telemetry (actual wake time and energy score 1-5).
4. Shift diurnal focus sprint windows anchored to Twake.
5. Execute replace_file_content tool calls to write locked ISO timestamps (scheduled: YYYY-MM-DDTHH:mm:ss-05:00) to TaskNotes/Tasks/*.md.
6. Create today's daily note at YYYY-MM-DD.md and update morning_checkin in System/Scheduling-Memory.md.
```

### 2. Evening Staging & Nightly Audit Trigger
```text
Execute skill /evening:
1. Run Unified Nightly Audit (/audit):
   - Reconcile completed tasks in TaskNotes/Tasks/*.md against session deltas; update bounded multipliers within [0.20, 2.00] in System/Scheduling-Memory.md.
   - Evaluate upcoming 14-day roadmap milestones in System/Life-Roadmap.md and instantiate required TaskNotes.
   - Inject Starter Wedges (micro_chunked: true) into stalled tasks (>72h).
2. Ingest external calendar commitments for tomorrow.
3. Query the user for any schedule additions, errands, or contextual constraints.
4. Arbitrate priority against Life-Roadmap.md (active roadmap deliverables receive Peak Focus slots).
5. Assemble tomorrow's prototype focus schedule and execute tool calls to serialize prototype_schedule in System/Scheduling-Memory.md.
```

---

## 🔒 Security & Local Environment Boundary

* **Universal Operating Contract:** The Antigravity adapter operates identically across Linux, macOS, and Windows.
* **Environment Quarantine:** All host-specific hardware manifests, local paths, package telemetry, and developer profiles reside exclusively within `System/Environment/` and are strictly excluded from public version control.
