---
type: strategic_roadmap
id: chrysalis-architecture-roadmap
status: active
version: 1.0.0
last_updated: "2026-09-03"
---

# Chrysalis Strategic Functionality & Evolution Roadmap

## 1. Vision & Architectural Philosophy
Chrysalis operates as an autonomous, localized personal operating system and agentic pairing framework. By maintaining an uncompromised Markdown substrate with explicit separation between Runtime (life operations) and Development (framework engineering), the system preserves user sovereignty, zero-leak privacy, and verifiable cognitive rhythm alignment.

This roadmap outlines high-impact architectural expansions across three structured horizons: Near-term, Mid-term, and Long-term.

---

## 2. Phased Horizons

### Horizon 1: Near-Term (Foundations & Core Automation)
*Focus: Stabilizing operational feedback loops, friction reduction, and granular task execution.*

#### N1. Automated Task-Sprint Micro-Chunking (`/task --chunk`)
- **Status**: Planned (Milestone 1)
- **Capability**: When high-friction or high-energy tasks are created or scheduled, autonomous agents automatically inject a 3-step Starter Wedge (`micro_chunked: true`) with low-friction micro-actions (e.g. 5-minute exploratory anchors).
- **Prerequisites & Technical Dependencies**:
  - `TaskNotes/_templates/Task-Template.md` schema compliance (`micro_chunked` boolean).
  - Agent skill `.agent/skills/task/SKILL.md` parser integration.
  - Frontmatter schema validation via `/doctor`.

#### N2. Cross-Agent Telemetry Ingestion & Aggregation
- **Status**: Planned (Milestone 2)
- **Capability**: Ingest execution telemetry across multiple AI agent orchestrators (Google Antigravity, local CLI tools, background workers) into a unified session ledger in `System/Scheduling-Memory.md`.
- **Prerequisites & Technical Dependencies**:
  - Standardized JSON session log schemas in `.agent/`.
  - Non-blocking lock handling in `System/scripts/` to prevent concurrent write collisions.
  - Multiplier learning algorithm bounds check in $[0.20, 2.00]$.

---

### Horizon 2: Mid-Term (Adaptive Intelligence & Biosynchronous Flow)
*Focus: Deepening biometrical chronotype alignment, predictive scheduling, and multi-node orchestration.*

#### M1. Dynamic Chronotype Calibration & Energy Wave Modeling
- **Status**: Proposed (Milestone 3)
- **Capability**: Expand morning calibration (`/calibrate`) beyond wake timestamps to include rolling sleep debt calculations, circadian dip predictions, and dynamic ultradian sprint shifting based on weekly diurnal drift.
- **Prerequisites & Technical Dependencies**:
  - Historical wake telemetry ledger in `Scheduling-Memory.md` (`learned_wake_rhythms`).
  - Rolling exponential moving average (EMA) computation in `.agent/skills/calibrate/SKILL.md`.
  - Calendar collision detection from `System/scripts/sync_calendar.py`.

#### M2. Secure Multi-Workstation Manifest Synchronization
- **Status**: Proposed (Milestone 4)
- **Capability**: Provide cryptographic peer-to-peer or authenticated synchronization of hardware manifests (`System/Environment/*.md`) across multi-node workstations (`station-node`, mobile devices, server blades) while preserving zero-leak Git boundary quarantines.
- **Prerequisites & Technical Dependencies**:
  - Standardized host profiling via `System/Environment/scripts/generate_manifest.py`.
  - `update.py` generic exclusion rule ensuring workstation manifests are never overwritten or leaked.
  - Safe Git staging pre-commit hook via `pii-scanner.sh`.

---

### Horizon 3: Long-Term (Autonomous Ecosystem & Recursive Synthesis)
*Focus: Full-lifecycle agent autonomy, emergent project distillation, and resilient offline execution.*

#### L1. Continuous Recursive Self-Improvement Engine (`/evolve 2.0`)
- **Status**: Research / Proposed (Milestone 5)
- **Capability**: Automated identification of workflow bottlenecks from daily notes (`YYYY-MM-DD.md`) and task drift telemetry, automatically synthesizing and testing candidate skill revisions in isolated sandboxes before proposing changelog promotions.
- **Prerequisites & Technical Dependencies**:
  - Snapshot rollback infrastructure in `.agent/skills/.backup/`.
  - Comprehensive automated E2E test harness (`tests/e2e/`).
  - Strict human-in-the-loop review gating before disk mutation.

#### L2. Semantic Knowledge Weaver & Slipbox Synthesis (`/zettel --synthesize`)
- **Status**: Research / Proposed (Milestone 6)
- **Capability**: Automated bidirectional semantic linking between active project roadmaps (`Projects/*/Roadmap.md`), permanent slipbox literature notes (`Slipbox/`), and universal task notes (`TaskNotes/Tasks/`), revealing hidden dependencies and knowledge clusters.
- **Prerequisites & Technical Dependencies**:
  - Wikilink and graph integrity validation via `/doctor`.
  - Standardized slipbox frontmatter schema (`Slipbox/_templates/Slipbox-Template.md`).
  - Metadata indexing via `mdbase.yaml`.

---

## 3. Capability Matrix & Dependencies

| Horizon | Capability Key | Status | Milestone | Target Substrate | Technical Prerequisites | Security & Privacy Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Near-term** | Micro-chunking | Planned | M1 | `TaskNotes/` | Schema validation, Starter Wedge templates | Zero PII risk |
| **Near-term** | Cross-agent telemetry | Planned | M2 | `System/Scheduling-Memory.md` | Non-blocking write locks, telemetry parser | Local storage only |
| **Mid-term** | Dynamic chronotype | Proposed | M3 | `System/`, `.agent/skills/calibrate/` | EMA calculation, calendar sync bridge | Quarantined to local vault |
| **Mid-term** | Multi-workstation sync | Proposed | M4 | `System/Environment/` | Generic exclusion rules in `update.py` | Strict zero-leak enforcement |
| **Long-term** | Recursive evolution | Proposed | M5 | `Development/`, `.agent/skills/` | E2E test harness, snapshot rollbacks | Code review audit gate |
| **Long-term** | Slipbox synthesis | Proposed | M6 | `Slipbox/`, `Projects/` | Wikilink graph audit, `mdbase.yaml` index | Zero external APIs |
