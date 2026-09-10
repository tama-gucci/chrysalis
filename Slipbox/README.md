# 🗃️ Slipbox (Atomic Zettelkasten Knowledge Base)

The **Slipbox** is the permanent atomic knowledge repository of the Chrysalis Hypergraph (Pillar II). It preserves mental models, literature insights, technical drafting conventions, and autonomous system evolution hypotheses.

---

## 🏛️ Core Principles of Chrysalis Zettels

1. **Atomicity:** Each note focuses on a single conceptual claim, definition, or mental model.
2. **Standardized Identification:** Note filenames and titles use high-precision local timestamps (`YYYYMMDDHHmmss-<slug>.md`) guaranteeing permanent uniqueness and immutable linking.
3. **Bidirectional Linking:** Notes connect to peer Zettels, parent project roadmaps (`Projects/*/Roadmap.md`), and active execution tasks (`chrysalis/Tasks/*.md`) via semantic `[[WikiLinks]]`.

---

## 🌊 Audio Ingestion & Lecture Synthesis Pipeline

When audio recordings (such as college lectures, design studio briefings, or technical podcasts) are ingested via the Android Sharesheet (`chrysalis/Inbox/`):

1. **Map Phase (Transcription & Chunking):** Long-form audio (45–90m) is transcribed and segmented into timestamped windows.
2. **Reduce Phase (Atomic Synthesis):** The orchestrator extracts fundamental ideas, producing:
   - **Lecture Master Note:** Archived in `Projects/<Course>/Lectures/YYYY-MM-DD-<Topic>.md`.
   - **Atomic Zettel Notes:** 2–4 permanent concept notes synthesized directly into `Slipbox/`, formatted with definitions, mental models, and tags.

---

## 🔍 The Knowledge-Execution Continuum

Knowledge in Chrysalis is never passive:
* **Active Sprint Cockpit Knowledge Drawer:** Tasks in `chrysalis/Tasks/*.md` specify `linked_zettels: ["[[20260912100000-aia-cad-layer-guidelines]]"]`. When executing an active 75-minute sprint on the mobile app, users expand the **Linked Knowledge Drawer** to read these atomic reference notes with one tap.
* **Automated Graph Linker (`zettel_graph_linker.py`):** Traverses project roadmaps and automatically injects relevant Zettel references into task frontmatter.
* **Recursive Self-Improvement (`#chrysalis`):** Notes tagged with `#chrysalis` capture architecture evolution ideas and are automatically ingested by the developer agent via `/evolve`.
