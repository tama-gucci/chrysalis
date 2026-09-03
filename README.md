# chrysalis

> [!WARNING]
> **Project Status: Early Alpha**  
> Chrysalis is currently in active personal development and is not yet ready for general use. Formats and features may change frequently.

---

## 🏛️ System Architecture & Division of Labor

Chrysalis operates with a strict, principled division of labor between **Production Runtime** (running daily life operations) and the **Development Pipeline** (engineering and evolving the OS):

```mermaid
graph TD
    subgraph Production ["🏃 PRODUCTION RUNTIME (Running Chrysalis)"]
        GDrive["☁️ Google Drive<br/>(Central Cloud Host & Synced Substrate)"]
        GeminiSpark["♊ Google Gemini Spark<br/>(Autonomous Daily Orchestrator)<br/>• 08:30 Morning Calibration<br/>• 21:00 Evening Staging & Audit<br/>• Cloud Calendar Ingestion & Timeblocking"]
        Clients["📱💻 Concurrent Obsidian Clients<br/>(Mobile, Tablet, Desktop)"]
        
        GeminiSpark -->|Mutates State & Focus Blocks| GDrive
        Clients <-->|Direct Cloud Synchronization| GDrive
    end

    subgraph Development ["🛠️ DEVELOPMENT PIPELINE (Engineering Chrysalis)"]
        Workstation["🖥️ Local Development Workstation<br/>(System/Environment/ • Workstation Manifests)"]
        Antigravity["🛸 Google Antigravity<br/>(Development & Architecture IDE Agent)<br/>• Codebase Engineering & Pair-Programming<br/>• Skill & Protocol Authoring<br/>• /evolve RSI Synthesis & Code Refactoring"]
        
        Antigravity <-->|Engineers & Refactors Codebase| Workstation
        Workstation -->|Syncs Code Changes| GDrive
    end
```

### 1. 🏃 Production Runtime (Running Chrysalis)
* **Central Host Substrate:** **Google Drive** is the single central host substrate. No single personal machine is required to act as an active server—multiple client devices run Obsidian concurrently, syncing with Google Drive.
* **Autonomous Orchestrator:** **Google Gemini Spark** executes daily operational lifecycles:
  * **08:30 CDT Morning Calibration (`/morning`, `/calibrate`):** Prompts for wake telemetry ($T_{\text{wake}}$, energy $1–5$), calculates diurnal focus blocks, and writes locked ISO timestamps to task frontmatter on disk.
  * **21:00 CDT Evening Staging (`/evening`, `/audit`, `/plan`):** Reconciles completed tasks, updates bounded tag multipliers, ingests 14-day upcoming horizons, injects starter wedges, and stages tomorrow's focus agenda.
  * **Calendar Ingestion:** Automatically wraps focus sprints around external Google Calendar commitments with zero collisions.

### 2. 🛠️ Development Pipeline (Engineering Chrysalis)
* **Development Agent:** **Google Antigravity** is used strictly as the development and architecture IDE agent for pair-programming, codebase engineering, and skill refactoring. Antigravity has zero operational involvement in running daily Chrysalis routines.
* **Quarantined Environment:** The entire `System/Environment/` directory (workstation manifests, package telemetry, and local development scripts) belongs to the development pipeline and is kept out of the public repository.

---

## 📅 Daily Lifecycle

```
+-------------------------------------------------------------------------+
|                                                                         |
|   1. Evening Review (/evening)                                          |
|      • Checks completed tasks from today                                |
|      • Ingests tomorrow's calendar events                               |
|      • Selects 2–3 priority tasks from Life-Roadmap.md                  |
|      • Stages a draft schedule for tomorrow                             |
|                                                                         |
|                                 │                                       |
|                                 ▼                                       |
|                                                                         |
|   2. Morning Calibration (/morning)                                     |
|      • Logs wake time and energy score (1–5)                            |
|      • Shifts daily focus blocks relative to wake time                  |
|      • Writes scheduled start/end timestamps to task files on disk      |
|                                                                         |
|                                 │                                       |
|                                 ▼                                       |
|                                                                         |
|   3. Focus Execution (/plan)                                            |
|      • 75–90m focus sprint blocks with 15m decompression buffers        |
|      • Analytical work mapped to morning focus windows                  |
|      • Administrative tasks mapped to afternoon recovery windows        |
|                                                                         |
+-------------------------------------------------------------------------+
```

---

## 🚀 Setup Guide

---

### Step 1: Vault Setup

1. **Clone the repository into Google Drive:**
   ```bash
   git clone https://github.com/tama-gucci/chrysalis.git ~/GoogleDrive/chrysalis
   cd ~/GoogleDrive/chrysalis
   ```

2. **Run the bootstrap script:**
   ```bash
   bash bootstrap.sh
   ```
   * Automatically detects your local timezone offset, verifies directory substrates, and initializes memory and roadmaps from templates.

3. **Open in Obsidian:**
   * Open [Obsidian](https://obsidian.md) and select **Open folder as vault** pointing to `~/GoogleDrive/chrysalis`.
   * Enable community plugins when prompted (TaskNotes, Dataview, Nexus).

---

### Step 2: Google Gemini Spark Orchestrator Setup

1. Open **Google Gemini / Spark** and configure scheduled prompts for your vault located on Google Drive:
   * **Morning Prompt (Scheduled Daily: 08:30 Local Time):**
     ```text
     You are the Chrysalis Operating System orchestrator.
     Execute skill /morning:
     1. Read System/Scheduling-Memory.md to inspect current pause state and pre-approved prototype schedule.
     2. Prompt the user for morning wake telemetry (energy score 1-5 and wake notes).
     3. When telemetry is received, calculate rolling rhythms, shift diurnal focus blocks relative to Twake, execute tool calls to serialize scheduled timestamps to TaskNotes/Tasks/*.md, and write today's YYYY-MM-DD.md note.
     Follow all constitutional invariants in System/SYSTEM-PROMPT.md.
     ```
   * **Evening Prompt (Scheduled Daily: 21:00 Local Time):**
     ```text
     You are the Chrysalis Operating System orchestrator.
     Execute skill /evening:
     1. Run the unified nightly audit (/audit): reconcile completed tasks, update bounded tag multipliers in [0.20, 2.00], ingest upcoming 14-day roadmap horizons, inject starter wedges into stalled tasks, and maintain inferred task pool.
     2. Ingest external Google Calendar events for tomorrow via Google Workspace or cached events in Scheduling-Memory.md.
     3. Query the user for schedule additions, arbitrate priority with Life-Roadmap.md, assemble prototype focus schedule with ultradian sprints, and serialize to prototype_schedule in Scheduling-Memory.md.
     Follow all constitutional invariants in System/SYSTEM-PROMPT.md.
     ```
2. Runtime instructions and adapter specifications are defined in [GEMINI.md](file:///home/sin/GoogleDrive/chrysalis/GEMINI.md) and `System/Orchestrators/Gemini/Adapter-Spec.md`.

---

### Step 3: Initial Conversational Onboarding

Run the onboarding command with your AI orchestrator:

```text
/onboard
```

1. Select a starter archetype or reply with your personal goals.
2. The orchestrator compiles `System/Life-Roadmap.md` with structured pillars and tag registries.
3. The orchestrator initializes baseline multipliers in `System/Scheduling-Memory.md`.
4. The orchestrator executes `/doctor` to validate frontmatter and tag consistency.

---

### Step 4: External Google Calendar Sync (Optional)

1. Enable Google Calendar synchronization within the **TaskNotes** plugin settings in Obsidian.
2. Chrysalis will read cached events from `Scheduling-Memory.md` and wrap focus sprint blocks around external commitments with zero schedule collisions.

---

## 🛠️ Command Reference

| Command | Skill Runbook | Description |
| :--- | :--- | :--- |
| **`/onboard`** | `.agent/skills/onboard/SKILL.md` | Interactive intake interview: compiles strategic roadmap and seeds operational memory. |
| **`/morning`** | `.agent/skills/morning/SKILL.md` | Ingests wake time and energy score, shifting daily focus blocks and locking timestamps. |
| **`/evening`** | `.agent/skills/evening/SKILL.md` | Reconciles daily tasks, ingests calendar events, and stages tomorrow's prototype schedule. |
| **`/plan`** | `.agent/skills/plan/SKILL.md` | Master bio-cognitive focus scheduling engine with ultradian sprints. |
| **`/task`** | `.agent/skills/task/SKILL.md` | Creates a new task note with category tags, time estimates, and modality. |
| **`/doctor`** | `.agent/skills/doctor/SKILL.md` | 6-point integrity diagnostic suite: validates schemas, tags, timezones, and links. |
| **`/audit`** | `.agent/skills/audit/SKILL.md` | Unified nightly reconciliation: updates multipliers, chronotype learning, and horizons. |
| **`/zettel`** | `.agent/skills/zettel/SKILL.md` | Creates an atomic slipbox knowledge note with bidirectional links. |
| **`/pause`** | `.agent/skills/pause/SKILL.md` | Suspends active timeblocks and freezes multiplier decay across 4 semantic modes. |
| **`/resume`** | `.agent/skills/pause/SKILL.md` | Resumes daily planning cycles smoothly following a pause. |

---

## 📦 Acknowledgements & Core Dependencies

Chrysalis is built on top of [Obsidian](https://obsidian.md) and depends on community plugins that are integral to daily operation:

* **[TaskNotes](https://github.com/lucas-rego/obsidian-tasknotes):** Integral to Chrysalis. Provides task note rendering, frontmatter property management, time tracking, and external Google Calendar synchronization.
* **[Nexus](https://github.com/nexus-plugin/nexus):** In-vault AI model connectivity and local tool calling.
* **[Dataview](https://github.com/blacksmithgu/obsidian-dataview):** Dynamic task querying and dashboard aggregation across the vault substrate.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).

