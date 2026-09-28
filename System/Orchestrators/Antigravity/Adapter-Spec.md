# Antigravity & Local Agent Adapter Contract (`A2` Access Layer)

Interactive operation on the **A2 Default Access Layer** is the supported baseline across **Google Antigravity**, **OpenAI Codex**, and **Claude Code**: resolve the personal runtime vault via `python System/scripts/vault_paths.py --runtime --json`, read `AGENTS.md`, execute the relevant `.agent/skills/<skill>/SKILL.md` runbook, and verify physical changes via `python helpers/mdbase_helper.py --runtime validate`, `mdbase -C "<vault>" validate`, and `python System/scripts/doctor.py --runtime`. Runtime activity belongs in the personal runtime vault (`~/Documents/Chrysalis`); reusable code changes belong in the development repository.

Local coding agents execute directly within the active agent environment without requiring an external mdbase gateway daemon (`mcp.mdbase.dev`). External binary sources in `Chrysalis-Media-Locker/01-Inbox` are read via a connected **Google Drive MCP server** or local Google Drive desktop mount during `/ingest`, while all translated Markdown records (`Sources/`, `Projects/`, `Slipbox/`, `TaskNotes/Tasks/`) are written and validated locally on `<vault>`. A process exit code alone does not prove the requested task mutation occurred; physical disk modifications must be verified.

No timer, background process, tunnel, or always-on host is created by these instructions. Such deployment is separate work. Emulation must be explicitly enabled and visibly labeled, and must not claim actual calendar or file changes.

Use the real tool interfaces available in the active agent environment. Do not assume tools named in old planning artifacts are callable. See the installation's `STATUS.md` for completed and planned capabilities.
