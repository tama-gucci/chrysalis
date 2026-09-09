---
type: strategic_roadmap
id: chrysalis-architecture-roadmap
status: active
version: 2.0.0
last_updated: "{{TIMESTAMP}}"
---

# Chrysalis Strategic Functionality & Evolution Roadmap

## 1. Vision & Architectural Philosophy
Chrysalis operates as an autonomous, localized personal operating system, Zettelkasten knowledge engine, and bio-cognitive life cockpit. By maintaining an uncompromised Markdown substrate with explicit separation between Runtime (life operations) and Development (framework engineering), the system preserves user sovereignty, zero-leak privacy, and verifiable cognitive rhythm alignment.

Chrysalis bridges atomic knowledge, project strategy, and daily execution across the **Tripartite Knowledge-Execution Continuum (The Chrysalis Hypergraph)**:
1. **Knowledge Layer:** Atomic permanent notes and mental models in `Slipbox/*.md`.
2. **Strategic Layer:** Milestone deliverables and project roadmaps in `Projects/*/Roadmap.md`.
3. **Execution Layer:** Universal TaskNotes schemas (`TaskNotes/Tasks/*.md`) with deep Obsidian interoperability.
4. **Temporal Layer:** 75-minute ultradian focus sprints timeblocked onto mobile and wearable calendars.

Architectural delivery follows a dual topology via the **Modular Intelligence Engine**:
- **Option A (Dedicated Home Hub - Golem):** Surface Pro X (16GB RAM total: 4GB Hyper-V Home Assistant, 12GB operational memory for Chrysalis and background agents) hosting the Ambient Gateway daemon (`apps/gateway/`) on port **8765** behind a Cloudflare Zero-Trust Tunnel, coexisting with Obsidian TaskNotes on port **8080**.
- **Option B (Mobile-Native / Serverless):** On-device inference (e.g. Gemini Nano) or direct cloud model APIs without a home server requirement.

This roadmap outlines high-impact architectural expansions across three structured horizons: Near-term, Mid-term, and Long-term, aligned directly with the project completion blueprint sprints.

---

## 2. Phased Horizons

### Horizon 1: Near-Term (Foundations & Core Automation)
*Focus: Establishing the Model C calendar bridge, modular intelligence engine, task-sprint micro-chunking, and cross-agent telemetry.*

#### N1. Automated Task-Sprint Micro-Chunking & Model C Calendar Bridge (`/task --chunk`)
- **Status**: Active (Sprint 1 / Milestone 1)
- **Capability**: 
  - When high-friction or high-energy tasks are staged or scheduled, autonomous agents automatically inject a 3-step Starter Wedge (`micro_chunked: true`) with low-friction micro-actions.
  - Implement **Model C (Mobile OS Bridge)** calendar synchronization: an Android Kotlin platform channel (`CalendarContract`) writing focus sprints directly to the local calendar provider with zero Google Cloud Console setup, zero OAuth secrets, and zero API quota limits. Includes private iCal feed fallback (`fetch_ical.py`).
- **Prerequisites & Technical Dependencies**:
  - `TaskNotes/_templates/Task-Template.md` schema compliance (`micro_chunked`, `googleCalendarEventId`).
  - Native Kotlin `CalendarManager.kt` using Android `ContentResolver` and `device_calendar_platform_channel.dart`.
  - Offline fallback verification via `System/scripts/fetch_ical.py`.

#### N2. Cross-Agent Telemetry Ingestion, Modular Intelligence Engine & Ambient Gateway
- **Status**: Active (Sprint 1 & Sprint 2 / Milestone 2)
- **Capability**: 
  - Formalize the `IntelligenceEngine` abstract Dart interface in `apps/mobile/lib/domain/services/intelligence_engine.dart` to decouple mobile UI from backend transports.
  - Ingest cross-agent telemetry across multiple AI agent orchestrators (Google Antigravity language server reference, OpenClaw, Hermes OS) into a unified session ledger in `System/Scheduling-Memory.md` with multiplier learning rates bounded in $[0.20, 2.00]$.
  - Configure the 24/7 Ambient Gateway daemon on Golem on port **8765** (reserving port **8080** for Obsidian TaskNotes) exposed securely via Cloudflare Zero-Trust Tunnel.
  - Autonomous Zettelkasten Hypergraph Linker: automatically scan `Slipbox/*.md` for tags matching active projects, append bidirectional `[[WikiLinks]]` to `Projects/*/Roadmap.md` Section 3, and inject `linked_zettels: []` into task frontmatter.
- **Prerequisites & Technical Dependencies**:
  - `BaseOrchestratorBridge` adapter pattern in `apps/gateway/orchestrator_bridge.py`.
  - Non-blocking lock handling in `System/scripts/` to prevent concurrent write collisions.
  - Script `System/scripts/zettel_graph_linker.py` and streaming conversational bottom sheet (`orchestrator_chat_sheet.dart`).

---

### Horizon 2: Mid-Term (Adaptive Intelligence & Biosynchronous Flow)
*Focus: Standalone Wear OS smartwatch experience, dynamic chronotype calibration, evening card triage deck, and multi-workstation synchronization.*

#### M1. Dynamic Chronotype Calibration, Standalone Wear OS Cockpit & Evening Triage
- **Status**: Planned (Sprint 3 / Milestone 3)
- **Capability**: 
  - **Standalone Wear OS Smartwatch Client:** Circular OLED responsive layout (384×384, pure black `#000000`), glanceable active sprint cockpit card, large tap targets, and prominent circular voice dictation mic button routing thoughts automatically to tasks or Zettel notes.
  - Expand morning calibration (`/calibrate`) beyond wake timestamps to include rolling sleep debt calculations and HRV ingestion via Health Connect Android platform channel.
  - **Evening Reconciliation Triage Deck (`/evening`):** Mobile gesture card deck for rapid swipe triage (Swipe Right = Done, Swipe Left = Tomorrow, Swipe Down = Backlog), with next-day prototype preview and approval.
- **Prerequisites & Technical Dependencies**:
  - Historical wake telemetry ledger in `Scheduling-Memory.md` (`learned_wake_rhythms`).
  - Flutter circular layout adaptation (`MediaQuery.shortestSide < 320`) and `wear_os_cockpit_view.dart`.
  - Health Connect platform channel data source in `apps/mobile`.

#### M2. Secure Multi-Workstation Manifest Synchronization & Obsidian Vault Coexistence
- **Status**: Proposed (Milestone 4)
- **Capability**: 
  - Provide cryptographic peer-to-peer or authenticated synchronization of hardware manifests (`System/Environment/*.md`) across multi-node workstations (`station-node`, mobile devices, server blades) while preserving zero-leak Git boundary quarantines.
  - Verify complete coexistence and synchronization between Obsidian TaskNotes local server on port **8080** and Chrysalis Ambient Gateway on port **8765**.
- **Prerequisites & Technical Dependencies**:
  - Standardized host profiling via `System/Environment/scripts/generate_manifest.py`.
  - `update.py` generic exclusion rule ensuring workstation manifests are never overwritten or leaked.
  - Safe Git staging pre-commit hook via `Development/scripts/pii-scanner.sh`.

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

| Horizon / Sprint | Capability Key | Status | Milestone | Target Substrate | Technical Prerequisites | Security & Privacy Impact |
| :--- | :--- | :---: | :---: | :--- | :--- | :--- |
| **Near-term (Sprint 1)** | Model C Calendar Bridge | Active | M1 | Android / Dart | `CalendarContract` platform channel, `fetch_ical.py` | Zero Google Cloud PII |
| **Near-term (Sprint 1)** | Task Micro-chunking | Active | M1 | `TaskNotes/` | Schema validation, Starter Wedge templates | Zero PII risk |
| **Near-term (Sprint 1)** | Modular IntelligenceEngine | Active | M2 | `apps/mobile/` | Abstract contract & gateway client | Local / Tunnel auth |
| **Near-term (Sprint 1)** | Golem Gateway Daemon (p8765) | Active | M2 | `apps/gateway/` | FastAPI, Windows venv, Cloudflare | Outbound tunnel only |
| **Near-term (Sprint 1)** | Cross-agent telemetry | Active | M2 | `System/Scheduling-Memory.md` | Non-blocking write locks, telemetry parser | Local storage only |
| **Near-term (Sprint 2)** | Zettel Hypergraph Linker | Planned | M2 | `Slipbox/`, `Projects/` | Wikilink graph parser, skill update | Local vault only |
| **Mid-term (Sprint 3)** | Dynamic chronotype | Planned | M3 | `System/`, `.agent/skills/calibrate/` | EMA calculation, Health Connect sync | Quarantined to local vault |
| **Mid-term (Sprint 3)** | Standalone Wear OS OLED | Planned | M3 | Wear OS / Flutter | Responsive circular 384x384 layout | Local device |
| **Mid-term (Sprint 3)** | Evening Triage Deck | Planned | M3 | `apps/mobile/` | Gesture physics, task mutator | Local vault only |
| **Mid-term** | Multi-workstation sync | Proposed | M4 | `System/Environment/` | Generic exclusion rules in `update.py` | Strict zero-leak enforcement |
| **Mid-term** | Obsidian Port 8080 Coexistence | Active | M4 | Obsidian / TaskNotes | Port separation verification | Localhost only |
| **Long-term** | Recursive evolution | Proposed | M5 | `Development/`, `.agent/skills/` | E2E test harness, snapshot rollbacks | Code review audit gate |
| **Long-term** | Slipbox synthesis | Proposed | M6 | `Slipbox/`, `Projects/` | Wikilink graph audit, `mdbase.yaml` index | Zero external APIs |
