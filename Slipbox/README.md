# Slipbox

The slipbox stores reusable reference notes. Keep personal notes in the runtime vault; only this guide and the templates belong in Git.

## Write a note

Use `/zettel` or copy [Slipbox-Template.md](_templates/Slipbox-Template.md). Give each note one main idea, useful source context, and relevant tags. Use `YYYYMMDDHHmmss-<slug>.md` filenames with local time, checking for collisions before saving.

Link related notes with wikilinks. Project roadmaps can reference the notes, and task frontmatter can include them in `linked_zettels`.

## Connect knowledge to work

`System/scripts/zettel_graph_linker.py --vault <runtime-vault>` links using tags and existing wikilinks. Review its output for relevance. Notes tagged `#chrysalis` can be reviewed during a requested development evolution pass.

Audio transcription, lecture synthesis, and automated document ingestion remain agent-assisted workflows or planned automation. Sharing a recording into the mobile app does not prove that it has been transcribed, synthesized, or synchronized. Current limitations are recorded in [STATUS.md](../STATUS.md).
