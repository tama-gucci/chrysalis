# 📱 Chrysalis Mobile & Wearable Client (Flutter)

A cross-platform, local-first Flutter frontend engineered for **Chrysalis**, streamlining user interactions across Android smartphones and standalone circular Wear OS smartwatches with the home orchestrator, bio-cognitive diurnal scheduling, decentralized vault synchronization, and the **Chrysalis Knowledge Hypergraph**.

---

## 🏛️ Architecture & Core Principles

The application is structured into four decoupled layers following Clean Architecture principles:

```
apps/mobile/
├── lib/
│   ├── core/                  # Constants, timezones (-05:00), exceptions
│   │   ├── constants/timezones.dart
│   │   └── exceptions/app_exceptions.dart
│   │
│   ├── domain/                # Business logic, entities, parsers, scheduling
│   │   ├── models/            # TaskNote, Biometrics, UltradianSprint, Modalities
│   │   ├── parser/            # TaskNoteParser (14+ fields), TaskShorthandParser
│   │   └── services/          # BioCognitiveScheduler, BiometricService (Health Connect),
│   │                          # DeviceCalendarSyncCoordinator, IntelligenceEngine
│   │
│   ├── data/                  # Storage abstractions, offline-first SQLite cache
│   │   ├── database/          # Drift/SQLite tables, mutation journal, queries
│   │   ├── storage/           # VaultStorageProvider interface & implementations
│   │   └── sync/              # VaultSynchronizer (offline-first caching & drain loop)
│   │
│   ├── transport/             # Modular Intelligence Engine transport
│   │   ├── orchestrator_transport.dart
│   │   ├── ambient_gateway_client.dart    # Option A: WebSocket/REST gateway (port 8765)
│   │   ├── substrate_mailbox_client.dart  # Offline fallback via System/Inbox/events.json
│   │   └── hybrid_orchestrator_transport.dart
│   │
│   ├── presentation/          # Material 3 & Wear OS reactive UI
│   │   ├── screens/home_screen.dart
│   │   ├── theme/app_theme.dart
│   │   └── widgets/           # ActiveSprintCard, Timeline, RapidCaptureBar,
│   │                          # WearOSCockpitView, OrchestratorChatSheet, Sheets
│   │
│   └── main.dart              # Application entrypoint & dependency injection
└── test/                      # Comprehensive unit, integration, and widget tests
```

---

## 🔑 Key Architectural Systems

### 1. Modular Intelligence Engine Principle
The mobile client decouples UI presentation from backend intelligence via the `IntelligenceEngine` interface:
* **Option A (Ambient Gateway Mode — Primary):** Connects to the home server daemon ("Golem" — Surface Pro X, port `8765`) over secure WebSockets and HTTPS through a Cloudflare Zero-Trust Tunnel. Dispatches commands to Antigravity, OpenClaw, Hermes OS, or local LLMs.
* **Option B (Mobile-Native / Serverless — Edge Mode):** Bypasses the home server, running edge models on-device (e.g. Gemini Nano via AICore) or direct cloud model APIs.
* **Offline Mailbox Fallback:** When network connectivity is absent, intents are buffered to `System/Inbox/events.json` in the synced vault, executing automatically when connectivity resumes.

### 2. Standalone Wear OS Smartwatch Support (Circular OLED)
* **Tailored for Circular Displays (384×384 px):** Automatically adapts layout when `shortestSide < 320`.
* **Pure OLED Black (`#000000`):** Powers down OLED pixels to minimize battery drain.
* **Rotary Vertical Card Stack:**
  - Glanceable connection pill (`● Gateway Online`).
  - Active sprint cockpit hero card with remaining countdown timer.
  - Large circular microphone button (`#6366F1`) for instant voice dictation. Voice commands automatically classify into tasks or Zettel notes (`/zettel`).
  - Tactile action buttons: `Calibrate Today` and `Pause System`.

### 3. The Chrysalis Knowledge Hypergraph (Sprint Cockpit Knowledge Drawer)
* Tasks are not isolated items; they are rooted in research and strategy.
* Tasks in `TaskNotes/Tasks/*.md` support `linked_zettels: ["[[note-id]]"]` and `project_ref: "[[Projects/slug/Roadmap]]"`.
* The **Active Sprint Cockpit Card** on mobile features an expandable **Linked Knowledge Drawer** displaying connected research notes from `Slipbox/`, allowing the user to open read-only reference cards during deep focus sprints with a single tap.

### 4. Calendar Integration Architecture (Model C: Mobile OS Bridge)
* **Zero Google Cloud Console Setup:** Operates without OAuth client secrets, developer console configurations, or cloud API quotas.
* The Flutter app communicates through a native Android platform channel (`CalendarManager.kt` via `CalendarContract`) to write focus blocks directly into the phone's built-in calendar database.
* Android mirrors these events to Google Calendar and Wear OS watch complications automatically for free.
* Supports two-way synchronization: when tasks are calibrated, changed, or marked `done`, calendar events are created, updated, or removed accordingly.

### 5. Universal TaskNotes Frontmatter Compliance
* Strict parser and serializer for the universal TaskNotes frontmatter fields:
  - `title`, `status`, `dateCreated`, `created`, `due`, `scheduled`, `priority`, `urgency_tier`, `modality`, `timeEstimate`, `energy`, `friction`, `micro_chunked`, `tags`, `linked_zettels`, `project_ref`, `googleCalendarEventId`.
* **Constitutional Timezone Invariant:** Enforces explicit local timezone serialization (`-05:00`) and strictly prohibits unadorned UTC `"Z"` strings.
* 100% compatible with the Obsidian TaskNotes plugin on port `8080`.

### 6. Google Health Connect Biometric Telemetry
* Reads Sleep Sessions (deep, REM, light, awake stages, efficiency), Resting Heart Rate (RHR), and Heart Rate Variability (HRV RMSSD).
* Computes algorithmic morning readiness score ($1$ to $5$) for morning `/calibrate` and bio-cognitive timeblocking.

### 7. Bio-Cognitive Diurnal Scheduler & Ultradian Sprint Tracker
* Automatically calculates daily ultradian focus schedules:
  - 75-minute focus sprints separated by 15-minute decompression buffers.
  - Modality alignment: Peak Focus $\to$ Analytical tasks, Slump Defrost $\to$ Kinetic tasks, Recovery $\to$ Synthesis tasks.
  - Adaptive multiplier learning bounded strictly to $[0.20, 2.00]$.

---

## 🧪 Testing & Verification

Run the full test suite and static analysis:

```bash
# Navigate to mobile project
cd apps/mobile

# Run all tests
flutter test

# Run static analysis (0 errors, 0 warnings)
flutter analyze
```

---

## 🔒 Zero-Leak PII & Hygiene

Build directories and local files are strictly quarantined from git:
- `.dart_tool/`, `build/`, `.flutter-plugins*`, and local Gradle caches are gitignored via default-deny.
- All tests and sample files use synthetic placeholders (`Jane Doe`, `station-node`, `user@example.com`).
