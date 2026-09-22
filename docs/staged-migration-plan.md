# Staged Vault Migration Plan: Legacy Chrysalis / TaskNotes to mdbase v0.3

This specification defines the non-destructive, staged migration process for transitioning existing Chrysalis and Obsidian TaskNotes runtime vaults to the **mdbase v0.3** AI Agent Framework database substrate.

---

## 1. Migration Architecture & Invariants

The migration engine is governed by four core safety invariants:

1. **Zero Data Loss Invariant**: No historical tasks, notes, deliverable records, or custom frontmatter properties are ever destructively removed.
2. **Superseded Context Preservation**: Unmapped or non-standard legacy properties (e.g. `subtasks`, `checklist`, `starred`, `obsidianUIMode`, `parent_task`, `diurnal_windows`) are removed from YAML frontmatter (to strictly satisfy `additionalProperties: false` under JSON Schema Draft 2020-12) and quarantined into a formatted Obsidian callout block at the top of the Markdown body:
   ```markdown
   > [!note] Superseded Legacy Context (Migrated from v0.2)
   > The following properties were migrated from legacy frontmatter to preserve historical context:
   > - **starred**: `true`
   > - **subtasks**:
   >   - Step 1: Initial research
   ```
3. **Atomic Rollback Guarantee**: An immutable, byte-for-byte snapshot of the entire vault is created prior to any file modification. A single-command rollback command restores the vault to its exact pre-migration state.
4. **Idempotence**: Running the migration procedure multiple times against the same vault produces identical, stable results without duplicating files, headers, or callout blocks.

---

## 2. Staged Migration Sequence

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 0: PRE-FLIGHT AUDIT & IMMUTABLE BACKUP                            │
│ - Validate vault path and write permissions                             │
│ - Scan for corrupt frontmatter, raw UTC "Z" strings, unmapped fields    │
│ - Create immutable snapshot: .chrysalis/migrations/{timestamp}_backup/   │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: COLLECTION ROOT & TYPE SCHEMA DEPLOYMENT                       │
│ - Deploy mdbase.yaml to vault root                                      │
│ - Deploy _types/ (task.md, project.md, zettel.md, source.md)            │
│ - Deploy _contracts/ and _templates/                                    │
│ - Create Sources/ directory for ingestion provenance                    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: PERSISTENT MEMORY & SYSTEM STATE CONVERSION                    │
│ - Ingest legacy System/Scheduling-Memory.md                             │
│ - Extract timezone, working hours, modality multipliers, active projects│
│ - Synthesize System/Memory.md conforming to Draft 2020-12 schema       │
│ - Supersede legacy file -> System/Scheduling-Memory.superseded.md       │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: TASK NOTES NORMALIZATION (chrysalis/TaskNotes/Tasks/**/*.md)   │
│ - Normalize filename: YYYYMMDD-{slug}.md                                │
│ - Map frontmatter properties (created -> dateCreated, local offset)     │
│ - Set date_uncertain: true if due is ambiguous                          │
│ - Quarantine unmapped legacy fields into Markdown body callout block    │
│ - Validate transformed note against _types/task.md via Draft202012      │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: PROJECT ROADMAPS SYNTHESIS (Projects/**/Roadmap.md)            │
│ - Synthesize frontmatter: project_id, title, status, pillar, deliverables│
│ - Extract deliverables from existing task references or markdown tables │
│ - Validate transformed roadmap against _types/project.md               │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 5: SLIPBOX ZETTEL HARMONIZATION (Slipbox/**/*.md)                 │
│ - Verify 14-digit local timestamp ID: YYYYMMDDHHmmss                    │
│ - Ensure dateCreated has explicit offset                                │
│ - Validate transformed zettel against _types/zettel.md                  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 6: OBSIDIAN & TASKNOTES CONFIGURATION HARMONIZATION               │
│ - Update TaskNotes data.json tasks folder to chrysalis/TaskNotes/Tasks  │
│ - Update Dashboard.md Dataview queries for "chrysalis/TaskNotes/Tasks"  │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ STAGE 7: POST-MIGRATION VERIFICATION GATE                               │
│ - Validate 100% of records against _types/*.md using ValidationHarness  │
│ - Verify link integrity (project_ref, linked_zettels)                   │
│ - Generate detailed migration report ledger                             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Comprehensive Schema Mapping Table

| Legacy Field (Chrysalis / TaskNotes) | Target Property (mdbase v0.3) | Type / Format | Transformation Rule & Fallback | Handling of Legacy Context |
| :--- | :--- | :--- | :--- | :--- |
| *(implicit)* | `type` | string (`"task"`) | Fixed constant: `"task"`. | Injected into frontmatter. |
| `title` | `title` | string | Verbatim. If missing, extracted from first H1 `# Title` or filename. | Preserved. |
| `status` | `status` | enum (`todo`, `in-progress`, `done`, `archived`) | Mapped directly. Legacy `completed` mapped to `done`; legacy `cancelled` mapped to `archived`. Default: `todo`. | Normalized. |
| `created` / `dateCreated` | `dateCreated` | string (RFC 3339 date-time with offset) | Prefer `dateCreated`, fallback `created`, fallback file ctime. If raw UTC `"Z"` present, converted to explicit local offset (e.g. `"-05:00"`). | Normalized to explicit offset. |
| `dateModified` | `dateModified` | string (RFC 3339 date-time with offset) | Verbatim with offset normalization, or omitted (optional). | Normalized. |
| `due` | `due` | string (`YYYY-MM-DD`) or `null` | Extracted as date string. If ambiguous or missing, set to `null` and set `date_uncertain: true`. | Clean date format. |
| `scheduled` | `scheduled` | string (RFC 3339 date-time with offset) or `null` | If legacy value was date-only (`YYYY-MM-DD`), expanded to default morning window `YYYY-MM-DDT09:00:00-05:00`. If inert, set to `null`. | Offset normalized. |
| `priority` | `priority` | enum (`urgent`, `high`, `normal`, `low`, `none`) | Verbatim. Default: `normal`. | Normalized. |
| `urgency_tier` | `urgency_tier` | integer ($1$ to $4$) | Verbatim integer. If missing, derived from `priority` (`urgent` $\to 4$, `high` $\to 3$, `normal` $\to 2$, `low`/`none` $\to 1$). | Derived. |
| `modality` | `modality` | enum (`analytical`, `kinetic`, `synthesis`, `administrative`) | Verbatim. Default: `analytical`. | Normalized. |
| `timeEstimate` | `timeEstimate` | integer (minutes) | Verbatim integer. Default: `45`. | Normalized. |
| `energy` | `energy` | enum (`high`, `medium`, `low`) | Verbatim. Default: `medium`. | Normalized. |
| `friction` | `friction` | enum (`high`, `medium`, `low`) | Verbatim. Default: `medium`. | Normalized. |
| `micro_chunked`| `micro_chunked`| boolean | Verbatim boolean. Default: `false`. | Normalized. |
| `tags` | `tags` | array of strings | Verbatim list. Ensure `"task"` is included. Default: `["task"]`. | Normalized. |
| `linked_zettels` | `linked_zettels` | array of strings | Verbatim list of wikilinks. Default: `[]`. | Normalized. |
| `project_ref` | `project_ref` | string (wikilink) or `null` | Ensure formatted as `[[Projects/<id>/Roadmap]]`. Default: `null`. | Normalized. |
| *(new)* | `deliverable_id` | string or `null` | Extracted from deliverable title match in parent roadmap, or `null`. | Injected. |
| `googleCalendarEventId` | `googleCalendarEventId` | string or `null` | Verbatim ID from TaskNotes sync, or `null`. | Preserved. |
| *(new)* | `date_uncertain`| boolean | Set to `true` if `due` is null or flagged TBD. Default: `false`. | Injected. |
| `startedAt` | `startedAt` | string (RFC 3339 date-time with offset) or `null` | Normalized with explicit offset, or `null`. | Preserved. |
| `completedAt` | `completedAt` | string (RFC 3339 date-time with offset) or `null` | Normalized with explicit offset, or `null`. | Preserved. |
| **Unmapped Legacy Fields** (`subtasks`, `checklist`, `starred`, `parent_task`, `obsidianUIMode`, etc.) | *(quarantined)* | Body Markdown Callout | **Removed from YAML frontmatter** (to pass `additionalProperties: false`) and appended to top of Markdown body as a formatted Obsidian Callout block (`> [!note] Superseded Legacy Context`). | **100% Preserved in Body**. |

---

## 4. Markdown Body Quarantining Example

### Before Migration (Legacy v0.2 Task Note):
```yaml
---
title: "Complete Literature Review on Consensus"
status: todo
created: 2026-09-01T10:00:00Z
starred: true
obsidianUIMode: preview
subtasks:
  - "Read Raft paper section 5"
  - "Summarize log matching proof"
---

# Complete Literature Review on Consensus

Initial notes on paper review...
```

### After Migration (mdbase v0.3 Task Note):
```yaml
---
type: task
title: "Complete Literature Review on Consensus"
status: todo
dateCreated: "2026-09-01T05:00:00-05:00"
due: null
scheduled: null
priority: normal
urgency_tier: 2
modality: analytical
timeEstimate: 45
energy: medium
friction: medium
micro_chunked: false
tags:
  - task
linked_zettels: []
project_ref: null
deliverable_id: null
googleCalendarEventId: null
date_uncertain: true
startedAt: null
completedAt: null
---

> [!note] Superseded Legacy Context (Migrated from v0.2)
> The following properties were migrated from legacy frontmatter to preserve historical context:
> - **starred**: `true`
> - **obsidianUIMode**: `"preview"`
> - **subtasks**:
>   - Read Raft paper section 5
>   - Summarize log matching proof

# Complete Literature Review on Consensus

Initial notes on paper review...
```

---

## 5. Automated Migration CLI Tool Specification

The migration is executed via the migration tool suite (specification implemented building upon `System/scripts/migrate_to_subfolder.py` and planned `System/scripts/migrate_v03.py`):

```bash
# Dry run: analyze vault, print proposed transformations, 0 disk mutations
python3 System/scripts/migrate_to_subfolder.py --vault-root /path/to/vault --dry-run

# Execute migration: snapshot backup + atomic transformations
python3 System/scripts/migrate_to_subfolder.py --vault-root /path/to/vault

# Verify post-migration vault integrity against mdbase v0.3 schemas
python3 tests/harness/validation_harness.py --collection /path/to/vault
```

---

## 6. Rollback Procedure & Disaster Recovery

1. **Pre-Migration Snapshot**: The tool creates an immutable snapshot directory at `<vault>/.chrysalis/migrations/<YYYYMMDDTHHMMSS>_pre_v03_backup/` containing byte-for-byte copies of all files.
2. **Manifest Verification**: An inventory manifest `snapshot_manifest.json` records relative paths, byte lengths, and SHA-256 digests of every file before transformation.
3. **Disaster Recovery Invocation**:
   ```bash
   python3 System/scripts/migrate_to_subfolder.py --vault-root /path/to/vault --rollback
   ```
4. **Rollback Actions**:
   - Newly introduced files (`mdbase.yaml`, `_types/`, `_contracts/`, `System/Memory.md`) are deleted.
   - Mutated files are replaced from the snapshot backup.
   - Cryptographic SHA-256 hashes are recalculated and verified to match the pre-migration baseline with 100% byte parity.
