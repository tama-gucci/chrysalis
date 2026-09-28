# Orchestrator registry

An orchestrator resolves the active personal runtime vault (`python System/scripts/vault_paths.py --runtime --json`), follows `AGENTS.md` and `.agent/skills/*/SKILL.md` operational runbooks, and persists approved actions as local Markdown mutations via the **A2 Default Access Layer** (`python helpers/mdbase_helper.py --runtime`, headless `mdbase -C "<vault>"`, `python System/scripts/doctor.py --runtime`, and `python tests/harness/validation_harness.py --runtime`). External binary sources in `Chrysalis-Media-Locker/` are read via a connected **Google Drive MCP server** or local Google Drive desktop mount during `/ingest`. Model selection belongs to the configured agent provider; no particular cloud model is a framework prerequisite.

| Adapter | Implementation |
| --- | --- |
| Interactive file-capable agent | Operational runbooks (`.agent/skills/*/SKILL.md`) and A2 local file contracts (`contracts/agent-runtime.contract.md`) |
| Antigravity (Google Antigravity) | First-class A2 agent runtime; executes modular skills over `<vault>` with local validation and Google Drive MCP support |
| Codex (OpenAI Codex) | First-class A2 agent runtime; executes modular skills over `<vault>` with local validation and Google Drive MCP support |
| Claude Code | Compatible A2 local coding agent runtime over `<vault>` |
| OpenClaw / Hermes | Reserved adapters returning unavailable |

Calendar ingestion uses the configured iCal feed (`python System/scripts/fetch_ical.py --runtime`). Native calendar export and automatic mailbox consumption remain unfinished. See `STATUS.md` and `ARCHITECTURE.md` at the installation root.

Queued intent, transport health, and simulated output are not proof of execution. The agent must verify resulting files and describe errors accurately.
