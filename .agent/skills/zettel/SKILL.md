---
name: zettel
description: "Captures atomic literature, technical insights, or Chrysalis system evolution ideas (#chrysalis), generates unique timestamp IDs, and links concepts bidirectionally."
trigger: "/zettel"
domain: runtime
reads:
  - "Slipbox/*.md"
writes:
  - "Slipbox/*.md"
---

> Paths below are relative to the explicitly selected vault. The default layout keeps System, Projects, and Slipbox at the root and operational task folders under chrysalis/. For an existing encapsulated vault, resolve the corresponding resource under chrysalis/; never create a competing copy. See ARCHITECTURE.md.


# /zettel (Atomic Knowledge & System Evolution Synthesis Engine)

## Syntax
* `/zettel [title] [tags...]`
* `/zettel [title] #chrysalis [subtags...]` *(for system feature ideas, habit trackers, and workflow concepts)*

## Processing Pipeline
1. **Timestamp Generation:** Create unique identifier `YYYYMMDDHHmmss`.
2. **Note Type Identification:**
   * **Branch A (Chrysalis System Evolution Idea):** If tags contain `chrysalis` or `chrysalis/*`:
     Construct note in `Slipbox/YYYYMMDDHHmmss-slug.md` with YAML frontmatter:
     ```yaml
     ---
     id: "YYYYMMDDHHmmss"
     title: "Feature / System Idea Title"
     dateCreated: "YYYY-MM-DDTHH:mm:ss-05:00"
     tags:
       - zettel
       - chrysalis
       - chrysalis/feature # or habit, workflow, ui
     integration_status: unintegrated # unintegrated, staged, integrated
     ---
     # Feature / System Idea Title

     ## Concept & Desired Outcome
     [Detailed description of the tool, habit tracker, or workflow concept and why it helps.]

     ## Proposed Mechanics & Vault Integration
     [Initial ideas on how this could fit into Chrysalis workflows, agent skills, or Dashboard tables.]

     ## References & Source Inspiration
     - [[Source-or-Link]]
     ```
   * **Branch B (Standard Domain Knowledge / Principle):**
     Construct atomic single-thesis note:
     ```yaml
     ---
     id: "YYYYMMDDHHmmss"
     title: "Atomic Principle Title"
     dateCreated: "YYYY-MM-DDTHH:mm:ss-05:00"
     tags:
       - zettel
       - concept/domain
       - principle/domain
     ---
     # Atomic Principle Title

     ## Core Thesis
     [Concise single-thesis claim or mental model.]

     ## Technical Elaboration & Context
     [Structured explanation, math, or implementation.]

     ## Empirical Operational Application
     [How Chrysalis or human daily execution can leverage this principle.]

     ## References & Cross-Links
     - [[Related-Note]]
     ```

3. **Autonomous Hypergraph Linking (Knowledge-to-Execution Pipeline):**
   * After writing the Zettel note to `Slipbox/`:
     1. **Project Roadmap Linking:** Inspect all active project roadmaps in `Projects/*/Roadmap.md`. If the Zettel note's tags or core thesis intersect with an active project's tags or domain, append a `[[WikiLink]]` to that project roadmap under `## 3. Reference Files & Contacts`.
     2. **Task Frontmatter Injection:** For tasks in `chrysalis/TaskNotes/Tasks/*.md` (or `TaskNotes/Tasks/*.md`) that belong to that project or share its tags, inject the Zettel note reference into the task's frontmatter:
        ```yaml
        linked_zettels:
          - "[[YYYYMMDDHHmmss-slug]]"
        ```
     3. **Task & Knowledge Interoperability:** During active focus sprints, external interfaces (Obsidian with TaskNotes community plugin) and AI runtime agents read `linked_zettels` to surface the underlying research directly within task context.
     4. **Calendar Event Annotation (Planned):** Keep linked Zettels in task notes. Calendar event annotation requires the future native calendar integration.
