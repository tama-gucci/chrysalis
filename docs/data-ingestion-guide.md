# Chrysalis Data Ingestion Architecture & `/ingest` Operational Guide

> **Architectural Decision & Storage Invariant (`STATUS.md` & `ARCHITECTURE.md`)**:
> 1. **Zero Local Binary Storage in the Vault:** All original binary and raw source files (PDF syllabi, textbooks, slide decks, audio recordings, lecture videos, whiteboard photos, datasets) are stored exclusively in **Google Drive** (`Chrysalis-Media-Locker/01-Inbox` $\to$ `Chrysalis-Media-Locker/02-Archived-Binaries`) so the vault remains pure UTF-8 Markdown.
> 2. **No Local `Resources/` Folder:** A `Resources/` folder inside `Projects/<id>/` or the Chrysalis vault is unnecessary and retired.
> 3. **Dedicated `/ingest` Markdown Translation Engine:** The runtime agent always translates external sources—either **automatically from the dedicated Google Drive folder during the nightly `/audit`** (`/ingest --drive`) or **interactively via direct attachment/share in the active agent session** (`/ingest` / `/ingest --share`)—into formatted, schema-validated UTF-8 Markdown records (`Sources/{source_id}.md`, `Projects/{project_id}/Roadmap.md`, `Slipbox/{YYYYMMDDHHmmss}-{slug}.md`, and `TaskNotes/Tasks/YYYYMMDD-<slug>.md`), aligning `/project` and `/zettel` with `System/Workflows/01-capture.md` through `04-organize.md` before handing off to `/plan` (`05-plan.md`).

---

## 1. Executive Architecture: The `/ingest` Pipeline (`Workflows 01–04` $\to$ `/plan`)

In **Chrysalis (`mdbase v0.3`)**, the **local Markdown vault (`mdbase.yaml`) is the single, authoritative source of truth for structured UTF-8 Markdown records**, while **Google Drive serves as the external binary locker**. Under **ADR 0006 (Exact-Document Storage Authority)**, every Markdown record's revision is defined by the cryptographic digest of its raw UTF-8 document bytes:

$$\text{revision} = \text{sha256}(\text{UTF-8 document bytes})$$

```mermaid
flowchart LR
    subgraph Channels["1. External Entry Channels (Zero Local Binaries)"]
        M1["Protocol 1: Nightly Google Drive Batch\n(/audit -> /ingest --drive)\nGoogle Drive: Chrysalis-Media-Locker/01-Inbox"]
        M2["Protocol 2: Interactive Direct Share\n(/ingest or /ingest --share)\nMultimodal Upload / Paste in Agent Session"]
    end

    subgraph Pipeline["2. /ingest Skill: Workflows 01–04 Alignment"]
        S1["Stage 1 (01-capture.md)\nSHA-256 Deduplication & <untrusted_document_payload>\n-> Draft Sources/{source_id}.md"]
        S2["Stage 2 (02-extract.md)\nPassive Extraction of 100% Deliverables,\nUncertain Dates & Atomic Concepts"]
        S3["Stage 3 (03-review.md)\nSyllabus Reconciliation (reconcile_syllabus)\n& Mandatory APPROVAL_GATE Table"]
        S4["Stage 4 (04-organize.md)\nAlign /project + Align /zettel\n+ 3-Way Horizon Partition (<=14d & Uncertain)"]
    end

    subgraph Hypergraph["3. Authoritative Local Vault Hypergraph (mdbase v0.3)"]
        R1["Sources/{source_id}.md\n(_types/source.md + Drive source_url)"]
        R2["Projects/{project_id}/Roadmap.md\n(/project - 100% Deliverables Ledger)"]
        R3["Slipbox/{YYYYMMDDHHmmss}-{slug}.md\n(/zettel - Atomic Knowledge Notes)"]
        R4["TaskNotes/Tasks/{YYYYMMDD}-{slug}.md\n(_types/task.md - <=14d & Uncertain Tasks)"]
    end

    subgraph Planning["4. Stage 5 Focus Scheduling"]
        P["/plan (05-plan.md)\nStack <=14d Tasks into Diurnal Ultradian Sprints"]
    end

    M1 --> S1
    M2 --> S1
    S1 --> S2 --> S3 --> S4
    S4 --> R1 & R2 & R3 & R4
    R2 -. "source_ref / source_checksum" .-> R1
    R3 -. "source_ref / project_ref" .-> R1
    R3 -. "project_ref" .-> R2
    R4 -. "project_ref / linked_zettels" .-> R2
    R2 & R4 --> P
```

### The Four Canonical Markdown Records Produced by `/ingest`
1. **Ingestion Provenance (`Sources/{source_id}.md` — `_types/source.md`)**:
   Content-addressed record (`id` and `sha256` unique across the collection) with `source_url` pointing to the original file in Google Drive (`Chrysalis-Media-Locker/02-Archived-Binaries/`), encapsulating the translated Markdown representation inside `<untrusted_document_payload source_id="..." sha256="..." mime_type="...">` with any nested `</untrusted_document_payload>` tags neutralized (`&lt;/untrusted_document_payload&gt;`).
2. **Master Project Roadmap (`Projects/{project_id}/Roadmap.md` — `/project` / `_types/project.md`)**:
   Aligned with `System/Workflows/01-capture.md` through `04-organize.md`. Links back to `source_ref: "[[Sources/{source_id}]]"` and `source_checksum: "<sha256>"`. Retains **100% of extracted project deliverables** across the entire timeline (`deliverables` YAML array) and reconciles syllabus revisions (`added`, `modified`, `dropped` $\to$ `status: archived`) via `reconcile_syllabus()`.
3. **Atomic Knowledge Zettels (`Slipbox/{YYYYMMDDHHmmss}-{slug}.md` — `/zettel` / `_types/zettel.md`)**:
   Aligned with `System/Workflows/01-capture.md` through `04-organize.md`. Synthesizes single-thesis mental models with 14-digit local timestamp IDs, linking back to `source_ref`, `source_checksum`, `source_url`, and `project_ref`, and weaving `linked_zettels` into `Roadmap.md` and active task notes before `/plan`.
4. **Actionable Execution Tasks (`TaskNotes/Tasks/{YYYYMMDD}-{slug}.md` — `_types/task.md`)**:
   Materialized via `filter_horizon_deliverables(horizon_days=14)` according to the **3-Way Horizon Partition Rule**:
   * **Imminent (`due <= today + 14d`)**: Recorded in `Roadmap.md` **and** materialized in `TaskNotes/Tasks/{YYYYMMDD}-{slug}.md` (`status: todo`, immediately scheduled by `/plan`).
   * **Uncertain (`due: null, date_uncertain: true`)**: Recorded in `Roadmap.md` **and** materialized in `TaskNotes/Tasks/{YYYYMMDD}-{slug}.md` (using `dateCreated`'s `YYYYMMDD` prefix, with `due: null, date_uncertain: true, scheduled: null`) so the task surfaces for deadline clarification without being auto-scheduled onto the calendar.
   * **Out-of-Horizon (`due > today + 14d`)**: Retained 100% in `Roadmap.md` (`deliverables` with `task_ref: null`); **not** materialized in `TaskNotes/Tasks/` until a future nightly `/audit` horizon sweep brings them within 14 days.

---

## 2. Two Operational Ingestion Modes (`.agent/skills/ingest/SKILL.md`)

### Mode 1: Automated Nightly Google Drive Folder Ingestion (`/audit` $\to$ `/ingest --drive`)
* **When it Runs:** Automatically called during Step 2 of the nightly operational audit (`/audit` / `/evening`), or on demand via `/ingest --drive`.
* **Dedicated Google Drive Folder Configuration (`System/Memory.md`):**
  ```yaml
  ingestion_config:
    drive_inbox_folder: "Chrysalis-Media-Locker/01-Inbox"
    drive_archive_folder: "Chrysalis-Media-Locker/02-Archived-Binaries"
    auto_ingest_on_nightly_audit: true
    local_resources_folder_enabled: false
  ```
* **Execution Sequence (A2 Access Layer + Google Drive MCP):**
  1. Resolve `<vault>` via `python System/scripts/vault_paths.py --runtime --json`.
  2. The agent inspects every file in `Chrysalis-Media-Locker/01-Inbox` via the connected **Google Drive MCP server** (in Google Antigravity, OpenAI Codex, or Claude Code) or a local Google Drive desktop mount. If `01-Inbox` is empty or the Google Drive MCP server is not currently connected, `/ingest --drive` logs `0 new files in Chrysalis-Media-Locker/01-Inbox` and proceeds cleanly without blocking `/audit` or `/evening`.
  3. Queries `<vault>/Sources/*.md` via `python helpers/mdbase_helper.py --vault "<vault>" check-duplicate <file>` (`helpers.mdbase_helper.check_semantic_duplicate()`) or `mdbase -C "<vault>" query --types source` to check `sha256` / `source_url` deduplication (`01-capture.md`).
  4. Translates each new or revised source file into formatted Markdown (`02-extract.md`), computes syllabus diffs (`03-review.md`), and presents the `PlanProposal` review table at `APPROVAL_GATE`.
  5. Upon confirmation (`04-organize.md`), serializes `<vault>/Sources/{source_id}.md`, `<vault>/Slipbox/YYYYMMDDHHmmss-<slug>.md` (`/zettel`), `<vault>/Projects/{project_id}/Roadmap.md` (`/project`), and `<=14d` / uncertain `<vault>/TaskNotes/Tasks/YYYYMMDD-<slug>.md`, validates each file via `python helpers/mdbase_helper.py --vault "<vault>" validate <path>`, archives the binary in `Chrysalis-Media-Locker/02-Archived-Binaries`, and hands off directly to `/plan` (`05-plan.md`).

### Mode 2: User-Directed Direct Share in Agent Session (`/ingest` or `/ingest --share`)
* **When it Runs:** Triggered whenever you attach a PDF syllabus, research paper, whiteboard photo, or voice memo (or paste raw text/links) directly in the active agent session.
* **Execution Sequence:**
  1. The agent performs multimodal extraction/OCR/transcription in-context—saving zero binary files in the vault.
  2. Executes Workflows `01-capture.md` through `04-organize.md`, aligning `/project` and `/zettel` and presenting the `PlanProposal` table at `APPROVAL_GATE`.
  3. Upon confirmation, writes the four formatted Markdown record types (`Sources/`, `Projects/`, `Slipbox/`, `TaskNotes/Tasks/`) and routes active 14-day tasks into `/plan`.

---

## 3. Strict Schema & Security Rules for `/ingest`

1. **Always Map `source_type` to One of the 6 Permitted Schema Enum Values (`_types/source.md`)**:

   | Input Source Material | Required `source_type` (`_types/source.md`) | Recommended `mime_type` |
   | :--- | :--- | :--- |
   | Course syllabus, project schedule, specification | `syllabus` | `text/markdown`, `text/plain`, or `application/pdf` |
   | Lecture notes, whiteboard photo (OCR), handwritten scan, meeting notes | `transcript` | `text/plain`, `image/jpeg`, or `image/png` |
   | Textbook chapter, research paper, assignment handout PDF | `pdf` | `application/pdf` |
   | Web article, documentation page, Google Doc URL | `web_page` | `text/html` or `text/markdown` |
   | Voice memo, spoken brainstorm | `audio` | `audio/mp4` or `audio/mpeg` |
   | Recorded lecture video or audio stream | `lecture_recording` | `video/mp4` or `audio/mpeg` |

2. **Never Store the Chrysalis Vault Folder Inside Google Drive**:
   Keep the Chrysalis vault (`Documents/Chrysalis`) on the local filesystem. Google Drive holds only the external `Chrysalis-Media-Locker/` folders (`01-Inbox/` and `02-Archived-Binaries/`).
3. **Quarantine All External Content (`<untrusted_document_payload>`)**:
   Every `Sources/{source_id}.md` record must wrap its translated Markdown content inside `<untrusted_document_payload source_id="..." sha256="..." mime_type="...">` with any nested `</untrusted_document_payload>` tags escaped to `&lt;/untrusted_document_payload&gt;`.

---

## 4. Ingestion Verification Commands

After executing `/ingest` or `/audit` (`/ingest --drive`) in your local agent session, verify collection and hypergraph integrity directly against the local vault:

```powershell
mdbase -C "$env:USERPROFILE\Documents\Chrysalis" validate
python tests/harness/validation_harness.py -c "$env:USERPROFILE\Documents\Chrysalis"
```
