# Chrysalis

> [!WARNING]
> **Project Status: Early Alpha**  
> Chrysalis is currently in active personal development and is not yet ready for general use. Formats and features may change frequently.

---

## How Chrysalis Works

Chrysalis is designed to bridge your long-term goals, your daily energy, and your AI assistant using standard Markdown files stored on your computer.

Instead of hiding scheduling algorithms inside a black box, every calculation, task state, and schedule rule lives in open text files that you can inspect and modify.

---

### The Three Layers of the System

Chrysalis divides your productivity into three distinct layers:

1. **The Strategic Roadmap (`System/Life-Roadmap.md`):**
   * This file holds your big-picture priorities, organized into 3–5 strategic pillars (e.g., career, academics, personal projects, finances).
   * Active milestones are broken down into **14-day rolling windows** with concrete checklists. This tells you and your AI assistant what is urgent right now versus what belongs in future horizons.

2. **The Task Backlog (`TaskNotes/Tasks/*.md`):**
   * Every task is an individual Markdown file containing details like priority, category tag, and estimated time.
   * Tasks are tagged to match your roadmap pillars (for example, `#pillar-1/admin` or `#pillar-2/deliverables`).

3. **Operational Memory & Multipliers (`System/Scheduling-Memory.md`):**
   * This is the memory engine. It records your typical wake habits, stores a cache of upcoming calendar events, and tracks **learned time multipliers** for each task category.
   * If you estimate tasks in a certain category at 30 minutes, but you consistently take 45 minutes, the system gradually adjusts a multiplier so your future schedules remain realistic and do not overload your day.

---

### The Daily Three-Phase Workflow

```
+-------------------------------------------------------------------------+
|                                                                         |
|   1. Evening Review (/evening)                                          |
|      • Checks completed tasks from today                                |
|      • Ingests tomorrow's Google Calendar events to prevent overlap     |
|      • Selects 2–3 priority tasks from Life-Roadmap.md                  |
|      • Stages a draft schedule for tomorrow                             |
|                                                                         |
|                                 │                                       |
|                                 ▼                                       |
|                                                                         |
|   2. Morning Calibration (/morning)                                     |
|      • User logs wake time (Twake) and energy level (1–5)               |
|      • Focus blocks shift dynamically based on when you actually woke up|
|      • Lock scheduled timestamps to task files on disk                  |
|                                                                         |
|                                 │                                       |
|                                 ▼                                       |
|                                                                         |
|   3. Focused Execution (/plan)                                          |
|      • 75–90m focus sprint blocks with 15m decompression buffers        |
|      • Analytical work scheduled during peak morning energy             |
|      • Administrative/light tasks placed during afternoon recovery      |
|                                                                         |
+-------------------------------------------------------------------------+
```

#### Phase 1: Evening Staging (`/evening`)
At the end of the day, you run the evening routine:
* The AI reviews what you accomplished today and marks completed items.
* It checks tomorrow's calendar commitments so focus blocks will not conflict with meetings, appointments, or classes.
* It looks at your active 14-day roadmap milestones and selects the most important anchor task and support tasks.
* It stages a draft schedule for tomorrow and presents it for your review.

#### Phase 2: Morning Calibration (`/morning`)
When you wake up, you provide two quick data points: the time you woke up and your energy level from 1 (exhausted) to 5 (fully rested).
* Rather than enforcing a rigid schedule that breaks if you sleep in or wake up early, Chrysalis recalculates your daily blocks relative to your actual wake time.
* If your energy is low, it scales back task duration and prioritizes high-friction items into manageable starter steps.
* Once calculated, the exact start and end times are written directly into your task notes.

#### Phase 3: Focused Sprint Execution (`/plan`)
Your workday is structured into focused sprint blocks:
* **Peak Sprints (75–90 minutes):** Reserved for demanding, deep-focus work (coding, writing, technical analysis).
* **Decompression Buffers (15 minutes):** Built-in breaks between sprints to prevent cognitive fatigue.
* **Slump & Recovery Windows:** Lighter administrative tasks, errands, or inbox processing are scheduled during natural afternoon energy dips.

#### Taking Time Off (`/pause` and `/resume`)
If you are traveling, sick, or taking a vacation, running `/pause` freezes schedule tracking. It clears active time blocks so you do not return to a wall of overdue alerts or broken schedule calculations. When you are ready to return, `/resume` smoothly restarts the daily cycle.

---

## Setup Guide

Follow this guide to set up Chrysalis on your computer, configure Obsidian, and connect your preferred AI assistant.

---

### Step 1: Base Vault Setup (All Users)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/tama-gucci/chrysalis.git ~/Chrysalis
   cd ~/Chrysalis
   ```

2. **Run the bootstrap installer:**
   ```bash
   ./bootstrap.sh
   ```
   * This script auto-detects your local computer's timezone (e.g., `-05:00`), verifies the directory structure, and initializes clean starter templates for your roadmap and scheduling memory.

3. **Open the vault in Obsidian:**
   * Download and install [Obsidian](https://obsidian.md).
   * On the startup screen, select **Open folder as vault** and choose the `~/Chrysalis` folder.
   * When prompted, click **Turn on community plugins** (TaskNotes, Dataview, Obsidian Git).

---

### Step 2: Configure Your Orchestrator (AI Assistant)

Chrysalis is designed to work with whichever AI assistant you prefer. Choose your orchestrator below:

#### Option A: Google Gemini (Cloud Cron & Google Workspace)
* **Best for:** Automated morning and evening schedule prompts delivered on a schedule.
* **How to configure:**
  1. Store your `Chrysalis` vault inside **Google Drive** (e.g., `~/GoogleDrive/Chrysalis`) so Google Gemini can access your notes via the Google Workspace extension.
  2. Set up two scheduled prompts in Google Spark / Gemini:
     * **Morning Prompt (08:30):**
       ```text
       You are the Chrysalis orchestrator. Execute skill /morning:
       Read System/Scheduling-Memory.md, prompt for wake telemetry, and calibrate today's schedule.
       Follow all rules in System/SYSTEM-PROMPT.md.
       ```
     * **Evening Prompt (21:00):**
       ```text
       You are the Chrysalis orchestrator. Execute skill /evening:
       Run the nightly audit, ingest tomorrow's Google Calendar events, and stage tomorrow's schedule.
       Follow all rules in System/SYSTEM-PROMPT.md.
       ```
  3. The root [GEMINI.md](file:///home/sin/GoogleDrive/chrysalis/GEMINI.md) file is already pre-configured to instruct Gemini on the system rules.

---

#### Option B: Google Antigravity (IDE & Desktop Agent)
* **Best for:** Interactive pairing, code refactoring, and multi-agent task execution.
* **How to configure:**
  1. Open the `Chrysalis` folder inside the **Antigravity IDE**.
  2. All skills inside `.agent/skills/` are loaded automatically as native slash commands (`/onboard`, `/morning`, `/evening`, `/doctor`, etc.).
  3. The root [AGENTS.md](file:///home/sin/GoogleDrive/chrysalis/AGENTS.md) file provides the agent with system rules and schemas.
  4. You can chat directly with the agent in the side panel to plan your day, add tasks, or run diagnostics.

---

#### Option C: Anthropic Claude (Claude Code CLI & Desktop MCP)
* **Best for:** Terminal-first workflows using Claude Code or Claude Desktop.
* **How to configure:**
  1. The root [CLAUDE.md](file:///home/sin/GoogleDrive/chrysalis/CLAUDE.md) file automatically instructs Claude on all system rules and file formats.
  2. **Using Claude Code (CLI):**
     * Open your terminal in the vault folder:
       ```bash
       cd ~/Chrysalis
       claude
       ```
     * Type `/onboard` or `/evening` directly in the prompt.
  3. **Using Claude Desktop (MCP):**
     * Add the local filesystem tool or TaskNotes MCP server to your `claude_desktop_config.json` pointing to your Chrysalis vault directory.

---

#### Option D: Local LLMs (Ollama, LM Studio & Obsidian Nexus)
* **Best for:** Complete offline execution with no external API dependencies.
* **How to configure:**
  1. Ensure you have [Ollama](https://ollama.ai) or LM Studio running locally with a tool-calling model (such as `qwen2.5-coder` or `llama3.3`).
  2. Inside Obsidian, go to **Settings** $\to$ **Nexus**.
  3. Set your local provider endpoint (for example, `http://localhost:11434/v1`).
  4. Open the Nexus chat panel in Obsidian to run `/morning`, `/evening`, or `/plan` locally on your machine.

---

### Step 3: Run the Initial Onboarding Interview

Once your AI assistant is connected, open chat in the vault folder and run:

```text
/onboard
```

The assistant will guide you through a quick intake:
1. You can choose a starter archetype (*Student/Academic*, *Solo Founder/Developer*, *Career Switcher/Licensure*, *Creator/Freelancer*) or paste in your existing goals.
2. The assistant generates your initial [Life-Roadmap.md](file:///home/sin/GoogleDrive/chrysalis/System/Life-Roadmap.md) with 3–5 strategic pillars and 14-day milestone blocks.
3. It seeds your baseline multipliers in [Scheduling-Memory.md](file:///home/sin/GoogleDrive/chrysalis/System/Scheduling-Memory.md) and creates your first sample task.
4. It finishes by running `/doctor` to verify that all tags and file links are clean and ready for daily use.

---

### Step 4: Connecting Google Calendar (Optional)

To enable external calendar awareness:
1. Ensure the **TaskNotes** plugin is enabled in Obsidian.
2. In TaskNotes settings, turn on Google Calendar sync and authorize your account.
3. Chrysalis will automatically pull your scheduled events so that morning and evening focus blocks wrap around your meetings without double-booking.

---

## Command Reference

| Command | Skill File | Description |
| :--- | :--- | :--- |
| **`/onboard`** | `.agent/skills/onboard/SKILL.md` | Initial intake interview: builds your strategic roadmap and seeds system memory. |
| **`/morning`** | `.agent/skills/morning/SKILL.md` | Ingests wake time and energy score, then shifts today's focus blocks accordingly. |
| **`/evening`** | `.agent/skills/evening/SKILL.md` | Reviews completed tasks, pulls calendar events, and stages tomorrow's schedule. |
| **`/plan`** | `.agent/skills/plan/SKILL.md` | Generates focus sprint blocks aligned with your energy and external meetings. |
| **`/task`** | `.agent/skills/task/SKILL.md` | Quickly adds a new task with category tagging and learned time estimates. |
| **`/doctor`** | `.agent/skills/doctor/SKILL.md` | Runs a 6-point integrity check on schemas, tags, timezones, and file links. |
| **`/audit`** | `.agent/skills/audit/SKILL.md` | Nightly background reconciliation: updates category multipliers and rolls forward horizons. |
| **`/zettel`** | `.agent/skills/zettel/SKILL.md` | Creates a quick atomic note in your Slipbox with automatic wikilinks. |
| **`/pause`** | `.agent/skills/pause/SKILL.md` | Pauses daily scheduling routines during travel, illness, or time off. |
| **`/resume`** | `.agent/skills/pause/SKILL.md` | Resumes normal daily scheduling cycles after a pause. |

---

## License
This project is open-source under the [MIT License](LICENSE).
