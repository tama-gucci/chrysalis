---
name: zettel
description: "Captures atomic literature, technical insights, or Chrysalis system evolution ideas (#chrysalis), generates unique timestamp IDs, and links concepts bidirectionally."
trigger: "/zettel"
reads:
  - "chrysalis/Slipbox/*.md"
writes:
  - "chrysalis/Slipbox/*.md"
---

# /zettel (Atomic Knowledge & System Evolution Synthesis Engine)

## Syntax
* `/zettel [title] [tags...]`
* `/zettel [title] #chrysalis [subtags...]` *(for system feature ideas, habit trackers, and workflow concepts)*

## Processing Pipeline
1. **Timestamp Generation:** Create unique identifier `YYYYMMDDHHmmss`.
2. **Note Type Identification:**
   * **Branch A (Chrysalis System Evolution Idea):** If tags contain `chrysalis` or `chrysalis/*`:
     Construct note in `chrysalis/Slipbox/YYYYMMDDHHmmss-slug.md` with YAML frontmatter:
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
     [Initial ideas on how this could fit into TaskNotes workflows, agent skills, or Dashboard tables.]

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
     [How Chrysalis OS or human daily execution can leverage this principle.]

     ## References & Cross-Links
     - [[Related-Note]]
     ```
