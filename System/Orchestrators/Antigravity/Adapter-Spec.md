---
type: orchestrator_adapter_spec
id: chrysalis-orchestrator-antigravity
name: "Google Antigravity Orchestrator Adapter"
orchestrator_platform: "google_antigravity"
status: active
version: 1.1.0
last_updated: "2026-09-02T13:42:00-05:00"

capability_tiers:
  operational_tier:
    alias: "inherit"
    model_family: "flash"
    role: "Interactive chat, rapid task creation, and diurnal scheduling"
  deep_reasoning_tier:
    alias: "pro"
    model_family: "pro"
    role: "Multi-agent research, codebase refactors, and diagnostic integrity verification"
---

# 🛸 Google Antigravity Orchestrator Adapter

This document specifies the integration configuration, capability tier routing, tool mappings, and skill bindings when using **Google Antigravity (AGY)** as the primary desktop and IDE orchestrator for Chrysalis OS.

---

## 🎯 Capability Tier Architecture & Subagent Routing

Antigravity leverages native model parameter inheritance and subagent delegation:

* **Operational Tier (`Model: inherit` or `flash`):** Used for standard turn-by-turn interactions and quick slash command invocations (`/morning`, `/evening`, `/task`).
* **Deep Reasoning Tier (`Model: pro`):** Invoked when spawning specialized research or diagnostic subagents (`invoke_subagent` with `Model: pro`) during `/audit` and `/doctor`.

---

## ⚡ Native Tool Mappings

Antigravity executes Chrysalis file operations using its built-in native tools:

| Chrysalis Standard Operation | Antigravity Native Tool | Description |
| :--- | :--- | :--- |
| **Inspect Note / Memory** | `view_file` | Reads contents of Markdown task notes, roadmaps, and memory. |
| **Mutate Frontmatter / Plan** | `replace_file_content` | Makes precise, contiguous text replacements in `.md` files. |
| **Create New Task / Slipbox** | `write_to_file` | Writes new task notes or Zettelkasten slipbox notes. |
| **Search Substrate** | `grep_search` / `find_by_name` | Fast ripgrep searching across the vault. |
| **Execute Environment Scripts** | `run_command` | Runs `sync_calendar.py`, `generate_manifest.py`, or bash commands. |

---

## 🧭 Slash Command Bindings

All skills defined in `.agent/skills/` are exposed as interactive slash commands:
* `/doctor` — Run 6-point pre-flight system integrity diagnostics.
* `/audit` — Execute unified nightly reconciliation, multiplier bounds clamping, and RSI analysis.
* `/plan` — Master bio-cognitive focus scheduling (`--stage` / `--calibrate`).
* `/morning` — 08:30 morning telemetry check-in and calibration.
* `/evening` — 21:00 evening review and prototype schedule staging.
* `/pause` & `/resume` — Manual system suspension across 4 semantic archetypes.
* `/task` — Shorthand task ingestion and frontmatter generation.
* `/zettel` — Atomic slipbox and `#chrysalis` capability ideation capture.
