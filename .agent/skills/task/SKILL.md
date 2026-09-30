---
name: task
description: "Parses shorthand task input, extracts project tags and cognitive modalities, applies adaptive multipliers with a 1.00 fallback rule to baseline estimates, and creates Chrysalis task markdown files."
trigger: "/task"
domain: runtime
reads:
  - "System/Memory.md"
writes:
  - "TaskNotes/Tasks/*.md"
---

> **A2 Access Layer & Runtime Vault Resolution:**
> All paths below (`System/...`, `TaskNotes/...`, `Projects/...`, `Slipbox/...`) are relative to the resolved **personal runtime vault** (`<vault>`), resolved via `python System/scripts/vault_paths.py --runtime --json` (defaulting to `~/Documents/Chrysalis` when invoked from the source checkout). Write task files directly to `<vault>/TaskNotes/Tasks/` and validate with `python helpers/mdbase_helper.py --vault "<vault>" validate "<vault>/TaskNotes/Tasks/YYYYMMDD-slug.md"`.

# /task (Shorthand Task Capture Engine)

## Syntax
`/task [title] [tag] [priority] [est:Xm] [due:YYYY-MM-DD] [modality:analytical|kinetic|synthesis|administrative] [project:slug] [[[linked-zettel]]]`

## Processing Pipeline
1. **Title, Tag & Project Extraction:** Parse task description and assign the corresponding `#pillar-X/*` tag from `System/Life-Roadmap.md`. If a project is specified (or inferred from matching deliverables in `Projects/*/Roadmap.md`), set `project_ref: "[[Projects/<slug>/Roadmap]]"`.
2. **Cognitive Modality Inference:**
   * If explicit modality is provided (e.g. `modality:kinetic`), assign it directly.
   * If omitted, infer from nature of task:
     - `analytical`: Deep mental load, code architecture, systems engineering, technical writing.
     - `kinetic`: Hardware builds, physical assembly, maintenance, workspace organization.
     - `synthesis`: Zettelkasten notes, research synthesis, system design ideation.
     - `administrative`: Documentation updates, portal checks, emails, forms.
3. **Multiplier Resolution & Fallback Rule:**
   * Read `cognitive_modality_defaults.<modality>.multiplier` from `System/Memory.md`.
   * Look up the active multiplier matching the assigned modality (baseline `1.00` fallback).
   * Compute effective duration:
     $$\text{timeEstimate} = \text{round}(\text{base\_estimate} \times \text{multiplier})$$
4. **Zettelkasten Hypergraph Association:**
   * If `project_ref` is present, read that project's `linked_zettels` array and Section 3 reference links to `Slipbox/`; do not depend on an exact heading label.
   * Inject matching Zettel references into `linked_zettels` frontmatter array.
5. **Optional Location & Map Enrichment (`location.resolve` & `visualization.map_projection`):**
   * If the task includes a physical venue, address, or coordinates:
     * When a `location.resolve` capability provider is enabled in `System/Memory.md` or `System/Integrations.md`, resolve the location via `python helpers/mdbase_helper.py --vault "<vault>" location-resolve --query "<query>"`.
     * If `location.resolve` returns `status: "ambiguous"`, present the returned `candidates` to the user rather than silently guessing.
     * When no `location.resolve` provider is enabled (`fallback_mode: "manual_only"`), store user-entered `location` (`provenance: "user_supplied"`) and/or top-level `coordinates: "lat, lng"` directly.
     * Respect provider storage and display policies (`contracts/integration-capabilities.contract.md`): when `persistence_policy: "place_id_only"`, persist `place_id` and label/address in `location`, omit provider-derived `lat`/`lng` from persistent Markdown (`coordinates: null`), and exclude the record from non-compatible map views (`map_display_permitted: false`).
6. **File Generation:** Create a new file in `TaskNotes/Tasks/YYYYMMDD-slug.md` with complete YAML frontmatter:

```yaml
---
title: "Task Title"
status: todo
dateCreated: "YYYY-MM-DDTHH:mm:ss-05:00"
created: "YYYY-MM-DDTHH:mm:ss-05:00"
due: "YYYY-MM-DD"
scheduled: null
priority: normal # urgent, high, normal, low
urgency_tier: 2 # 1-4
modality: analytical # analytical, kinetic, synthesis, administrative
timeEstimate: 45
energy: medium # high, medium, low
friction: medium # high, medium, low
micro_chunked: false
tags:
  - task
  - pillar-1/setup
linked_zettels: []
project_ref: null
googleCalendarEventId: null
location: null
coordinates: null
route_estimate: null
travel_policy: null
---
```
