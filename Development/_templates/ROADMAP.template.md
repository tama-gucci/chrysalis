# Development roadmap

Implementation status lives in [STATUS.md](../../STATUS.md). The engineering backlog is tracked in [BACKLOG.md](../BACKLOG.md). This roadmap describes framework capabilities in dependency order.

## 1. Near-term: Prove the personal daily-use workflow

- Complete mdbase v0.3 core foundation, type schemas, and portable workflows.
- Establish the zero-cloud local test harness and verify 8-stage lifecycle execution with real disk mutations.
- Validate non-destructive staged migration from legacy layouts to `chrysalis/TaskNotes/Tasks/` in the personal runtime vault (`chrysalis/`).
- Prove one complete input (syllabus/transcript ingestion) → extracted task/zettel → plan → completion cycle.
- Enforce passive untrusted text quarantine (`<untrusted_document_payload>`) and prompt injection neutralization.

## 2. Mid-term: Finish integrations

- Harmonize TaskNotes community plugin as the designated sole writer for Google Calendar synchronization via `googleCalendarEventId`.
- Evaluate candidate runtime agent bridges (Gemini Spark Streamable HTTP MCP adapter and Claude Desktop stdio bridge).
- Reconcile cross-agent telemetry and chronotype calibration within deterministic session memory (`System/Memory.md`).
- Multi-workstation synchronization over local network or encrypted relay listeners.
- Strengthen runtime diagnostics (`/doctor`) and automated self-healing.

## 3. Package the usable core

- Maintain 1:1 public sanitized template matrix for all personal runtime state files.
- Package deterministic Python helpers (`helpers/mdbase_helper.py`) with zero external cloud dependencies.
- Standardize 8-stage state machine in `contracts/agent-runtime.contract.md` with 22 diagnostic codes.
- Ensure 100% test coverage across schemas, CAS concurrency, and adversarial failure modes.

## 4. Long-term: Expand only after the core workflow is proven

- Direct local LLM provider bridges (Ollama, local runners).
- Extended multimodal audio ingestion pipeline.
- Standalone Wear OS smartwatch interface (deferred).
- Advanced semantic Zettelkasten linking and reviewed self-improvement.

## Capability horizons

| Horizon | Planned capability | Dependency |
| :--- | :--- | :--- |
| Near-term | Task micro-chunking / Starter Wedge refinement | Real daily-use feedback |
| Mid-term | Cross-agent telemetry and chronotype calibration | Verified execution and permission-based telemetry |
| Mid-term | Multi-workstation synchronization | Authenticated storage and conflict handling |
| Long-term | Semantic synthesis and self-improvement | Stable data and reviewable proposals |
