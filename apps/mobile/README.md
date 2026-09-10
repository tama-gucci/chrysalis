# 📱 Chrysalis Mobile & Wearable Client (Flutter)

A cross-platform, local-first Flutter application engineered for **Chrysalis**, serving as both a primary **Ingestion Surface (Pillar I)** and **Interface Translation Cockpit (Pillar III)** across Android smartphones and standalone circular Wear OS smartwatches.

---

## 🌊 Role in the Three Core Pillars

1. **Pillar I: Data Ingestion Surface 🐛🍃 (The Hungry Caterpillar)**
   - **Native Android Sharesheet Receiver:** Hooks directly into Android's system sharesheet (`ACTION_SEND` / `ACTION_SEND_MULTIPLE`) to receive text clippings, web URLs, PDFs (course syllabi, assignments), and audio recordings (lectures, voice memos).
   - **Binary-Safe Stream Cache & Auto-Staging:** Safely caches `content://` byte streams to disk and drops files into `chrysalis/Inbox/` with zero user friction or popup dialogs.
   - **Rapid Shorthand Capture:** Single-line capture bar with autocomplete for tags, modalities, and time estimates.
   - **Wear OS Voice Dictation:** One-tap circular microphone button on smartwatch capturing audio and classifying into tasks or Zettels.

2. **Pillar III: Interface Translation Cockpit 🦋✨ (The Emergent Butterfly)**
   - **Active Sprint Cockpit Hero Card:** Renders the active 75-minute ultradian focus sprint with real-time countdown timer and modality accent colors.
   - **Expandable Linked Knowledge Drawer:** Directly inspects connected atomic research notes (`linked_zettels`) from `Slipbox/` inside the active sprint card without switching apps.
   - **Diurnal Timeline Widget:** Visual day block representation showing wake time, morning analytical peak, slump defrost, and evening recovery windows.
   - **Model C Calendar Synchronization:** Direct Android `CalendarContract` integration writing focus blocks to the phone's built-in calendar database, mirroring to Google Calendar and Wear OS watch complications with zero cloud setup.

---

## 🏛️ Clean Architecture & Directory Structure

The mobile application is structured into four decoupled layers:

```
apps/mobile/
├── android/                   # Native Android integration
│   └── app/src/main/
│       ├── AndroidManifest.xml# ACTION_SEND / SEND_MULTIPLE intent filters
│       ├── kotlin/.../MainActivity.kt # MethodChannels (Sharesheet, Calendar, Health Connect)
│       └── res/xml/file_paths.xml    # FileProvider configuration
│
├── lib/
│   ├── core/                  # System constants, explicit timezones (-05:00), exceptions
│   │   ├── constants/timezones.dart
│   │   └── exceptions/app_exceptions.dart
│   │
│   ├── domain/                # Business logic, entities, parsers, scheduling
│   │   ├── models/            # TaskNote, Biometrics, UltradianSprint, Modalities
│   │   ├── parser/            # TaskNoteParser (Universal Schema), TaskShorthandParser
│   │   └── services/          # BioCognitiveScheduler, BiometricService (Health Connect),
│   │                          # DeviceCalendarSyncCoordinator, ShareReceiverService,
│   │                          # ShareAutoStagingController, IntelligenceEngine
│   │
│   ├── data/                  # Storage abstractions, offline-first Drift/SQLite cache
│   │   ├── database/          # Tables, mutation journal (SHA-256), queries
│   │   ├── storage/           # VaultStorageProvider (Local, Google Drive, In-Memory)
│   │   └── sync/              # VaultSynchronizer (offline-first caching & drain loop)
│   │
│   ├── transport/             # Modular Intelligence Engine transport
│   │   ├── orchestrator_transport.dart
│   │   ├── ambient_gateway_client.dart    # Option A: WebSocket/REST gateway (port 8765)
│   │   ├── substrate_mailbox_client.dart  # Offline fallback via System/Inbox/events.json
│   │   └── hybrid_orchestrator_transport.dart
│   │
│   ├── presentation/          # Material 3 Dark & Wear OS circular reactive UI
│   │   ├── screens/home_screen.dart
│   │   ├── theme/app_theme.dart
│   │   └── widgets/           # ActiveSprintCard, LinkedKnowledgeDrawer,
│   │                          # RapidCaptureBar, UltradianTimelineWidget,
│   │                          # MorningCalibrationSheet, OrchestratorStatusChip
│   │
│   └── main.dart              # Application entrypoint & dependency injection
└── test/                      # Comprehensive unit, widget, and domain tests
```

---

## 🔑 Key Subsystems & Features

### 1. Universal Android Native Sharesheet Ingestion
* **No Custom Web Dialog Friction:** External apps (Chrome, PDF viewers, Audio Recorders) share directly to Chrysalis via Android's native sharesheet.
* **Persistent Byte Stream Caching:** Android content URIs expire quickly. `MainActivity.kt` streams bytes into `context.cacheDir/shared_staging/<filename>` before permission expires.
* **Auto-Staging to `chrysalis/Inbox/`:** `ShareAutoStagingController` moves cached payloads directly into `<vault>/chrysalis/Inbox/` on physical disk, resolves filename collisions (`<filename>_1.<ext>`), shows a brief confirmation Toast, and auto-dismisses when opened as a share target.

### 2. Standalone Wear OS Smartwatch Companion
* **Circular OLED Display (384×384 px):** Automatically adapts layout when `shortestSide < 320`.
* **Pure OLED Black (`#000000`):** Powers off pixels to maximize battery life.
* **Rotary Card Stack:**
  - Active sprint countdown timer and modality pill.
  - Large circular microphone button (`#6366F1`) for instant voice capture.
  - One-tap quick actions: `Calibrate Today` and `Pause System`.

### 3. Active Sprint Knowledge Drawer (Hypergraph Integration)
* Chrysalis tasks in `chrysalis/Tasks/*.md` declare `linked_zettels: ["[[20260912100000-concept]]"]`.
* During deep focus sprints, users tap the **Linked Knowledge Drawer** at the bottom of the active sprint card to inspect read-only atomic notes from `Slipbox/` without navigating away.

### 4. Model C Calendar Synchronization (Zero Cloud Setup)
* Communicates through native Android `CalendarContract` platform channel (`CalendarManager.kt`).
* Focus sprints are written directly to the smartphone's built-in calendar database, automatically mirroring to Google Calendar and Wear OS watch complications for free with zero Google Cloud console setup or OAuth tokens.

### 5. Universal Chrysalis Frontmatter Compliance
* Strict serialization and deserialization conforming to the Universal Chrysalis Task Schema (`AGENTS.md`).
* Enforces explicit local timezone offsets (e.g. `"-05:00"`).
* Full 1:1 interoperability with the desktop `chrysalis-obsidian` plugin on port `8080`.

### 6. Google Health Connect Biometric Telemetry
* Interfaces with `androidx.health.connect.client` to ingest Sleep Sessions (deep, REM, light), Resting Heart Rate (RHR), and Heart Rate Variability (HRV RMSSD).
* Algorithmic calculation of morning readiness score ($1$ to $5$) for morning `/calibrate` and adaptive diurnal sprint shifting.

---

## 🧪 Testing & Verification

Run the full Dart test suite and static analysis:

```bash
cd apps/mobile

# Run static analysis
dart analyze

# Run unit and widget tests
flutter test
```
