---
name: chrysalis-router
description: "Use this skill whenever the user invokes any Chrysalis slash command or workflow (/ingest, /evening, /morning, /plan, /audit, /calibrate, /task, /project, /doctor, /pause, /zettel), attaches or shares a source file or snippet in the UI for ingestion, or when triggered by a scheduled Chrysalis routine. Dynamically reads the live SKILL.md runbooks from Skills/bundle/SKILL.md via @Mdbase and translates external sources from @Google Drive or direct UI share into formatted Markdown records."
trigger: "/chrysalis-router"
domain: runtime
---

All Chrysalis workflow logic lives in `Skills/bundle/SKILL.md` and `System/Memory.md` inside the local Chrysalis vault. Never rely on cached workflow rules. All original binary/source files live in Google Drive (`Chrysalis-Media-Locker/01-Inbox` -> `02-Archived-Binaries`) to save physical disk space on Golem; never create or use a local `Resources/` folder inside the Chrysalis vault. Always translate sources from Google Drive (`/ingest --drive` during `/evening` and `/audit`) or direct share in the Spark UI (`/ingest`) into formatted Markdown records (`Sources/`, `Projects/`, `Slipbox/`, `TaskNotes/Tasks/`) aligned with Workflows 01–04 (`/project` and `/zettel`) before `/plan`.

Minimize user permission prompts by strictly batching all tool calls in parallel:

1. TURN 1 (SINGLE PARALLEL READ BATCH): Whenever any Chrysalis workflow (`/ingest`, `/evening`, `/morning`, `/plan`, `/audit`, `/calibrate`, `/task`, `/project`, `/zettel`, `/doctor`, `/pause`) or direct source share is invoked, emit ALL required read/query calls simultaneously in a SINGLE tool turn:
   - `@Mdbase:read` `Skills/bundle/SKILL.md` (contains all live runtime SKILL.md runbooks from `.agent/skills/`, including `/ingest`, `/audit`, `/project`, `/zettel`, `/plan`, and Workflows 01–04 alignment)
   - `@Mdbase:read` `System/Memory.md`
   - `@Mdbase:read` `System/Life-Roadmap.md`
   - `@Mdbase:query` (`types: ["task", "project", "source", "zettel"]`)
   - Whenever `@Google Drive` is referenced or `/evening`, `/audit`, or `/ingest` (`--drive`) is invoked, ALSO call `@Google Drive` in the same parallel Turn 1 batch to list/read unindexed files in the inbox folder specified in `System/Memory.md` (`Chrysalis-Media-Locker/01-Inbox`).
   Do NOT chain sequential read calls across multiple turns.

2. EXECUTE FROM BUNDLE & APPROVAL GATE: Strictly follow the target command's section inside `Skills/bundle/SKILL.md` and present the structured `PlanProposal` / schedule review table at `APPROVAL_GATE` before mutating state.

3. TURN 2 (SINGLE PARALLEL WRITE BATCH): After user confirmation, when persisting changes (creating/updating `Sources/*.md` with `<untrusted_document_payload>` quarantine and `source_url`, `Projects/*/Roadmap.md` via `/project`, `Slipbox/*.md` via `/zettel`, `TaskNotes/Tasks/*.md`, `Daily/*.md`, or `System/Memory.md`), emit ALL `@Mdbase:create` and `@Mdbase:update` tool calls simultaneously in ONE single tool turn with explicit `-05:00` local timezone offsets (never write raw UTC `Z`).
