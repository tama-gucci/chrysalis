# 📁 Projects Directory (Strategic Roadmaps & Dossiers)

The **Projects Directory** forms the strategic layer of the Chrysalis Hypergraph (Pillar II), bridging atomic knowledge notes in `Slipbox/` with granular, timeblocked execution in `chrysalis/Tasks/`.

---

## 🏛️ Project Dossier Structure

Each active initiative maintains an encapsulated project folder tracking strategic intent, deliverables, timeline horizons, and reference literature:

```
Projects/
├── README.md                          # This directory index & architectural overview
├── _templates/
│   └── Project-Template.md            # Standardized 1:1 public project roadmap template
└── <Project_Slug>/                    # Encapsulated project dossier (e.g. CAD_Certification_2026)
    ├── Roadmap.md                     # Master strategic roadmap & milestone matrix
    ├── Lectures/                      # Processed lecture master notes from audio ingestion
    └── Resources/                     # Local project assets, diagrams, and reference materials
```

---

## 🌊 The 3-Tier Cascade (Syllabus & Dossier Ingestion)

When complex real-world documents (such as academic course syllabi, RFP briefs, or technical roadmaps) are ingested via the Android Sharesheet or Chat:

1. **Tier 1: Strategic Project Dossier (`Roadmap.md`)**  
   The orchestrator compiles the core project roadmap defining:
   - Target outcomes, horizons (`horizon_window: YYYY-MM-DD → YYYY-MM-DD`), and pillar alignment.
   - Deliverable milestone matrix with strict verification dates.
2. **Tier 2: Actionable Task Decomposition (`chrysalis/Tasks/*.md`)**  
   Milestones are broken down into bite-sized task notes with cognitive modality tags, time estimates, Starter Wedges, and `project_ref: "[[Projects/<Project_Slug>/Roadmap]]"`.
3. **Tier 3: Reference Knowledge Linking (`Slipbox/*.md`)**  
   Reference concepts, technical standards, and textbook notes are captured in `Slipbox/` and declared under `## 3. Reference Notes & Zettels`. The automated linker (`zettel_graph_linker.py`) establishes bidirectional `[[WikiLinks]]` across both layers.

---

## 🔄 Lifecycle Integration

* **Nightly Operational Audit (`/audit`):** Scans all project roadmaps for milestones due within the next 14 days, dynamically replenishing the candidate task pool in `System/Scheduling-Memory.md`.
* **Standardized Schema:** For new projects, use the `/project` skill or duplicate `Projects/_templates/Project-Template.md`.
