# chrysalis

> [!WARNING]
> **Project Status: Early Alpha**  
> chrysalis is currently in active personal development and is not yet ready for general use. Formats and features may change frequently.

---

## How chrysalis Works

chrysalis coordinates daily task scheduling, milestone tracking, and AI assistant interactions using Markdown files stored locally in an Obsidian vault.

---

### System Structure

The system is structured across three primary file layers:

1. **Strategic Roadmap (`System/Life-Roadmap.md`):**
   * Contains long-term objectives grouped into strategic pillars.
   * Milestones are organized into 14-day rolling windows containing key result checklists and associated category tags.

2. **Task Backlog (`TaskNotes/Tasks/*.md`):**
   * Individual Markdown files for each task containing frontmatter metadata (status, priority, urgency tier, time estimate, modality, and roadmap tags).

3. **Operational Memory (`System/Scheduling-Memory.md`):**
   * Stores system state, wake baselines, cached external calendar events, and category-specific time multipliers derived from task completion history.

---

### Daily Workflow

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

#### 1. Evening Staging (`/evening`)
* Reconciles completed tasks from the current day.
* Ingests external calendar commitments for the following day.
* Selects active milestone deliverables from `Life-Roadmap.md`.
* Writes a staged schedule to `prototype_schedule` in `Scheduling-Memory.md`.

#### 2. Morning Calibration (`/morning`)
* Ingests actual wake timestamp ($T_{\text{wake}}$) and reported energy score ($1–5$).
* Calculates diurnal focus windows relative to $T_{\text{wake}}$.
* Serializes explicit ISO timestamps (`scheduled: "YYYY-MM-DDTHH:mm:ss-05:00"`) directly into the frontmatter of scheduled task files.

#### 3. Focus Blocks (`/plan`)
* Groups tasks into 75–90 minute sprint blocks separated by 15-minute buffers.
* Analytical tasks are scheduled during morning peak windows; administrative and routine tasks are scheduled during afternoon recovery windows.

#### 4. Pausing and Resuming (`/pause` and `/resume`)
* Running `/pause` clears scheduled task timestamps and suspends daily cycle processing.
* Running `/resume` reactivates normal morning and evening scheduling cycles.

---

## Setup Guide

---

### Step 1: Base Vault Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tama-gucci/chrysalis.git ~/chrysalis
   cd ~/chrysalis
   ```

2. **Run the bootstrap script:**
   ```bash
   ./bootstrap.sh
   ```
   * Detects the host system's timezone offset, verifies required directories, and copies initial template files if active files are not present.

3. **Open in Obsidian:**
   * Open [Obsidian](https://obsidian.md) and select **Open folder as vault** pointing to `~/chrysalis`.
   * Enable community plugins when prompted (TaskNotes, Dataview, Nexus).

---

### Step 2: Orchestrator Configuration

chrysalis can be orchestrated using several AI runtime environments:

#### Option A: Google Gemini (Google Spark & Google Workspace)
1. Place the vault directory inside **Google Drive** (e.g. `~/GoogleDrive/chrysalis`) so files are accessible to Google Workspace extensions.
2. Configure scheduled prompts in Google Spark / Gemini:
   * **Morning Prompt (08:30):**
     ```text
     You are the chrysalis orchestrator. Execute skill /morning:
     Read System/Scheduling-Memory.md, prompt for wake telemetry, and calibrate today's schedule.
     Follow all rules in System/SYSTEM-PROMPT.md.
     ```
   * **Evening Prompt (21:00):**
     ```text
     You are the chrysalis orchestrator. Execute skill /evening:
     Run the nightly audit, ingest tomorrow's Google Calendar events, and stage tomorrow's schedule.
     Follow all rules in System/SYSTEM-PROMPT.md.
     ```
3. Runtime instructions are defined in [GEMINI.md](file:///home/sin/GoogleDrive/chrysalis/GEMINI.md).

---

#### Option B: Google Antigravity (IDE Agent)
1. Open the vault directory in **Antigravity IDE**.
2. Skills in `.agent/skills/` are loaded as native slash commands (`/onboard`, `/morning`, `/evening`, `/doctor`, etc.).
3. Operating rules are defined in [AGENTS.md](file:///home/sin/GoogleDrive/chrysalis/AGENTS.md).

---

#### Option C: Anthropic Claude (Claude Code CLI & Desktop MCP)
1. Operating rules are defined in [CLAUDE.md](file:///home/sin/GoogleDrive/chrysalis/CLAUDE.md).
2. **Claude Code CLI:** Run `claude` inside the vault directory and invoke commands directly.
3. **Claude Desktop MCP:** Configure local filesystem access or TaskNotes API tools in `claude_desktop_config.json`.

---

#### Option D: Local LLMs (Ollama, LM Studio & Obsidian Nexus)
1. Run a local tool-calling model (e.g. `qwen2.5-coder`) via Ollama or LM Studio.
2. In Obsidian **Settings $\to$ Nexus**, configure the local API endpoint (e.g. `http://localhost:11434/v1`).
3. Invoke slash commands within the Nexus panel.

---

### Step 3: Initial Onboarding

Run the onboarding command with your AI assistant:

```text
/onboard
```

1. Select an archetype or provide an outline of current priorities and projects.
2. The assistant generates `System/Life-Roadmap.md` with structured pillars and tag registries.
3. The assistant initializes baseline multipliers in `System/Scheduling-Memory.md`.
4. The assistant executes `/doctor` to validate frontmatter and tag consistency.

---

### Step 4: External Calendar Sync (Optional)

1. Enable Google Calendar synchronization within the **TaskNotes** plugin settings.
2. chrysalis will read cached events from `Scheduling-Memory.md` and avoid scheduling focus blocks during external commitments.

---

## Command Reference

| Command | Skill File | Description |
| :--- | :--- | :--- |
| **`/onboard`** | `.agent/skills/onboard/SKILL.md` | Initial intake: builds strategic roadmap and seeds operational memory. |
| **`/morning`** | `.agent/skills/morning/SKILL.md` | Ingests wake time and energy score, shifting daily focus blocks. |
| **`/evening`** | `.agent/skills/evening/SKILL.md` | Reconciles daily tasks, ingests calendar events, and stages tomorrow's schedule. |
| **`/plan`** | `.agent/skills/plan/SKILL.md` | Generates focus sprint blocks aligned with calendar commitments. |
| **`/task`** | `.agent/skills/task/SKILL.md` | Creates a new task file with category tags and time estimates. |
| **`/doctor`** | `.agent/skills/doctor/SKILL.md` | Validates frontmatter schemas, tags, timezones, and link integrity. |
| **`/audit`** | `.agent/skills/audit/SKILL.md` | Reconciles task durations, updates multipliers, and crawls upcoming milestones. |
| **`/zettel`** | `.agent/skills/zettel/SKILL.md` | Creates an atomic slipbox note with bidirectional links. |
| **`/pause`** | `.agent/skills/pause/SKILL.md` | De-schedules active blocks and halts daily planning routines. |
| **`/resume`** | `.agent/skills/pause/SKILL.md` | Resumes daily planning cycles following a pause. |

---

## Acknowledgements & Core Dependencies

chrysalis is built on top of [Obsidian](https://obsidian.md) and depends on community plugins that are integral to the system's daily operation:

* **[TaskNotes](https://github.com/lucas-rego/obsidian-tasknotes):** Integral to chrysalis. Provides task note rendering, frontmatter property management, time tracking, the local REST API bridge, and external Google Calendar synchronization.
* **[Nexus](https://github.com/nexus-plugin/nexus):** Integral to chrysalis. Provides in-vault AI model connectivity, local tool calling, and embedded workspace context.
* **[Dataview](https://github.com/blacksmithgu/obsidian-dataview):** Provides dynamic task querying and dashboard aggregation across the vault substrate.

---

## License
This project is open-source under the [MIT License](LICENSE).
