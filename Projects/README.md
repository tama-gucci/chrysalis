# Projects

Projects connect strategic priorities to tasks and reference notes. Create personal project folders in the runtime vault; only this guide and the templates belong in Git.

## Create a project

Use the `/project` or `/ingest` runbook or copy [Project-Template.md](_templates/Project-Template.md) to `Projects/<project-slug>/Roadmap.md`. Record outcomes, milestones, due dates, and reference notes. All original binary and source files live in Google Drive (`Chrysalis-Media-Locker/`); a local `Resources/` folder inside the vault is unnecessary as the agent translates external sources into formatted Markdown (`Sources/{source_id}.md`, `Projects/<project-slug>/Roadmap.md`, `Slipbox/*.md`, `TaskNotes/Tasks/*.md`).

Create actionable tasks under `TaskNotes/Tasks/` with a `project_ref` linking to the roadmap. Put reusable concepts in `Slipbox/` and reference them from the roadmap and task `linked_zettels` fields.

## Review, ingestion, and linking

The `/audit` runbook automatically invokes `/ingest --drive` to direct Gemini Spark (`@Google Drive` + `@Mdbase`) to translate new source files from the dedicated Google Drive inbox via `System/Workflows/01-capture.md` through `04-organize.md` (aligning `/project` and `/zettel`), then reviews upcoming 14-day milestones before `/plan` (`05-plan.md`). `/ingest` is also invoked on direct file share in the Spark UI.

`System/scripts/zettel_graph_linker.py --vault <runtime-vault>` matches tags and wikilinks. Review the resulting associations; the script does not infer meaning from arbitrary documents.

Document and audio ingestion are processed through `Sources/{source_id}.md` and governed by agent runtime contracts. Ingestion does not materialize tasks without human review and approval. See [capability status](../STATUS.md).
