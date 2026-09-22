# Projects

Projects connect strategic priorities to tasks and reference notes. Create personal project folders in the runtime vault; only this guide and the templates belong in Git.

## Create a project

Use the `/project` runbook or copy [Project-Template.md](_templates/Project-Template.md) to `Projects/<project-slug>/Roadmap.md`. Record outcomes, milestones, due dates, and reference notes. Optional `Resources/` and `Lectures/` folders hold supporting material when needed.

Create actionable tasks under `chrysalis/TaskNotes/Tasks/` (or `TaskNotes/Tasks/`) with a `project_ref` linking to the roadmap. Put reusable concepts in `Slipbox/` and reference them from the roadmap and task `linked_zettels` fields.

## Review and linking

The `/audit` runbook directs an agent to review upcoming milestones and update the candidate task pool. It runs when invoked through an agent; the folder itself does not schedule background work.

`System/scripts/zettel_graph_linker.py --vault <runtime-vault>` matches tags and wikilinks. Review the resulting associations; the script does not infer meaning from arbitrary documents.

Document and audio ingestion are processed through `Sources/{source_id}.md` and governed by agent runtime contracts. Ingestion does not materialize tasks without human review and approval. See [capability status](../STATUS.md).
