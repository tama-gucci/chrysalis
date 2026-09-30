---
name: zettel
description: "Captures atomic literature, technical insights, or Chrysalis system evolution ideas (#chrysalis), aligns with /ingest and Workflows 01–04 to ground notes in Sources/{source_id}.md and external source URLs, generates 14-digit timestamp IDs, and weaves bidirectional wikilinks into Projects/*/Roadmap.md and TaskNotes/Tasks/*.md before /plan."
trigger: "/zettel"
domain: runtime
reads:
  - "Sources/*.md"
  - "Slipbox/*.md"
  - "Slipbox/_templates/Slipbox-Template.md"
  - "Projects/*/Roadmap.md"
  - "TaskNotes/Tasks/*.md"
  - "System/Workflows/01-capture.md"
  - "System/Workflows/02-extract.md"
  - "System/Workflows/03-review.md"
  - "System/Workflows/04-organize.md"
  - ".agent/skills/ingest/SKILL.md"
writes:
  - "Slipbox/*.md"
  - "Projects/*/Roadmap.md"
  - "TaskNotes/Tasks/*.md"
---

> Paths below are relative to the resolved personal runtime vault (`<vault>`). The default layout keeps `System/`, `Projects/`, `Slipbox/`, and `Sources/` at the root and operational task folders under `TaskNotes/`. See `ARCHITECTURE.md`.


# /zettel (Atomic Knowledge & System Evolution Synthesis Engine)

## A2 Access Layer & Runtime Vault Resolution (Platform-Agnostic)
* **Resolve `<vault>`:** Run `python System/scripts/vault_paths.py --runtime --json` (or use `$CHRYSALIS_VAULT_PATH` / `$CHRYSALIS_VAULT_ROOT`). All runtime knowledge notes and hypergraph links must be written to `<vault>`, never the synthetic source checkout.
* **Provider-Independent A2 Execution:** Create and link `<vault>/Slipbox/YYYYMMDDHHmmss-<slug>.md` using standard local file tools (`write_to_file` / `replace_file_content` / `apply_patch`), validate with `python helpers/mdbase_helper.py --vault "<vault>" validate <path>` / `mdbase -C "<vault>" validate`, and weave bidirectional wikilinks via `python System/scripts/zettel_graph_linker.py --vault "<vault>"`.

## Syntax & Triggers
* `/zettel [title] [tags...]` — Synthesizes an atomic single-thesis knowledge note in `Slipbox/YYYYMMDDHHmmss-<slug>.md`.
* `/zettel [title] #chrysalis [subtags...]` — Captures system feature ideas, habit trackers, and workflow concepts for `/evolve`.
* **Automatic Invocation via `/ingest` (`Workflows 01–04`):** Invoked automatically during configured source batch ingestion (`/audit` $\to$ `/ingest --all` or `/ingest --source <alias>` via optional integration skills supplying `ingestion.discover` / `ingestion.read` or local filesystem mounts) and interactive direct share (`/ingest`) to synthesize atomic notes from translated `Sources/{source_id}.md` records before `/plan` (`05-plan.md`).

## Alignment with `System/Workflows/01-capture.md` – `04-organize.md` & `/ingest`
1. **Zero Local Binary Storage (Configured External Media Provenance):** Raw source files (lecture recordings, PDF papers, slide decks, whiteboard photos) remain outside the vault in the configured external media storage boundary (`preserve_originals_in_place: true`, configured under `ingestion.sources`, e.g., `media` via an optional `ingestion.read` integration skill or a local filesystem mount). `/ingest` first translates the source into `<vault>/Sources/{source_id}.md` (`01-capture.md`).
2. **Cryptographic & Provenance Grounding (`02-extract.md` – `04-organize.md`):** Every Zettel extracted from an ingested source embeds `source_ref: "[[Sources/<source_id>]]"`, `source_checksum: "<64-char-sha256>"`, `source_url` (pointing to the original external file or web URL when known), and `project_ref: "[[Projects/<project_id>/Roadmap]]"`.
3. **Pre-`/plan` Hypergraph Weaving (`04-organize.md` $\to$ `05-plan.md`):** Before `/plan` schedules active focus sprints, `/zettel` links each new `<vault>/Slipbox/YYYYMMDDHHmmss-<slug>.md` note into `<vault>/Projects/<project_id>/Roadmap.md` (`linked_zettels`) and active 14-day `<vault>/TaskNotes/Tasks/YYYYMMDD-<slug>.md` frontmatter (`linked_zettels`) so the research notes surface inside scheduled focus blocks.

## Processing Pipeline
1. **Timestamp Identity Generation:** Create a 14-digit local timestamp identifier `YYYYMMDDHHmmss` with kebab-case slug (`YYYYMMDDHHmmss-slug`, matching `^[0-9]{14}(-[a-z0-9-]+)?$`).
2. **Note Type Identification & `_types/zettel.md` Serialization:**
   * **Branch A (Chrysalis System Evolution Idea):** If tags contain `chrysalis` or `chrysalis/*`, construct note in `Slipbox/YYYYMMDDHHmmss-slug.md`:
     ```yaml
     ---
     type: zettel
     id: "YYYYMMDDHHmmss-slug"
     title: "Feature / System Idea Title"
     dateCreated: "YYYY-MM-DDTHH:mm:ss-05:00"
     tags:
       - zettel
       - chrysalis
       - chrysalis/feature # or habit, workflow, ui
     source_ref: "[[Sources/source-id]]" # or null if conversational
     source_checksum: null # 64-char lowercase hex sha256 if extracted from source
     source_url: null # External media or web URL if applicable
     project_ref: null
     linked_zettels: []
     integration_status: unintegrated # unintegrated, staged, integrated
     ---
     # Feature / System Idea Title

     ## Concept & Desired Outcome
     [Detailed description of the tool, habit tracker, or workflow concept and why it helps.]

     ## Proposed Mechanics & Vault Integration
     [Initial ideas on how this could fit into Chrysalis workflows, agent skills, or Dashboard tables.]

     ## References & Source Inspiration
     - [[Sources/source-id]]
     ```
   * **Branch B (Standard Domain Knowledge / Principle — `_types/zettel.md`):**
     Construct atomic single-thesis note in `Slipbox/YYYYMMDDHHmmss-slug.md`:
     ```yaml
     ---
     type: zettel
     id: "YYYYMMDDHHmmss-slug"
     title: "Atomic Principle Title"
     dateCreated: "YYYY-MM-DDTHH:mm:ss-05:00"
     tags:
       - zettel
       - concept/domain
       - principle/domain
     source_ref: "[[Sources/source-id]]" # or null if conversational
     source_checksum: "{{64_char_sha256_or_null}}"
     source_url: "{{external_source_or_web_url_or_null}}"
     project_ref: "[[Projects/project-slug/Roadmap]]" # or null
     linked_zettels: []
     integration_status: integrated # integrated when linked into Roadmap & Tasks during Stage 4
     ---
     # Atomic Principle Title

     ## Core Thesis
     [Concise single-thesis claim or mental model.]

     ## Technical Elaboration & Context
     [Structured explanation, math, or implementation.]

     ## Empirical Operational Application
     [How Chrysalis or human daily execution can leverage this principle.]

     ## References & Cross-Links
     - Provenance: [[Sources/source-id]]
     - Related: [[Related-Note]]
     ```

3. **Autonomous Hypergraph Linking (`04-organize.md` $\to$ `05-plan.md`):**
   * After writing the Zettel note to `Slipbox/`:
     1. **Project Roadmap Linking:** Inspect active project roadmaps in `Projects/*/Roadmap.md` (or the target `project_ref` from `/ingest`). Append `"[[YYYYMMDDHHmmss-slug]]"` to the roadmap's `linked_zettels` frontmatter array and Section 3 references (`System/scripts/zettel_graph_linker.py`).
     2. **Task Frontmatter Injection:** For tasks in `TaskNotes/Tasks/*.md` that belong to that project (`project_ref`) or share its tags, inject the Zettel reference into the task's frontmatter before `/plan` runs:
        ```yaml
        linked_zettels:
          - "[[YYYYMMDDHHmmss-slug]]"
        ```
     3. **Task & Knowledge Interoperability:** During active focus sprints planned by `/plan`, Obsidian (with TaskNotes) and AI runtime agents read `linked_zettels` to surface the underlying knowledge note and its external `source_url` directly within task execution context.
