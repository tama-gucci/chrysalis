# Chrysalis

> A structured, Markdown-based task management and daily focus framework for Obsidian, designed to work seamlessly with AI assistants.

> [!WARNING]
> **Project Status: Early Alpha**  
> Chrysalis is currently in active personal development and is not yet ready for general use. Formats and features may change frequently.

Chrysalis is a personal productivity setup built entirely with plain Markdown files in Obsidian. It helps you manage long-term goals, schedule daily focus blocks around your natural energy levels, and collaborate with AI assistants (like Gemini, Claude, or local LLMs) to keep your schedule organized without proprietary task apps or cloud databases.

---

## How It Works

Chrysalis is organized around a simple daily workflow:

1. **Evening Review (`/evening`):**
   * Review what you finished today.
   * Check tomorrow's calendar events.
   * Pick 2–3 priority tasks from your roadmap to build a realistic draft schedule for tomorrow.

2. **Morning Check-In (`/morning`):**
   * Log when you woke up and your current energy level (1–5).
   * The system automatically shifts your focus blocks to match your actual wake time.

3. **Daily Focus Blocks (`/plan`):**
   * Tasks are grouped into 75–90 minute sprint blocks separated by short breaks.
   * Demanding analytical work is placed in morning focus windows, while administrative or lighter tasks are placed in afternoon recovery periods.

---

## Key Features

* **Plain Markdown Substrate:** All tasks, roadmaps, and settings live as standard Markdown files in your vault. Your data stays yours, with no third-party task apps or lock-in.
* **AI Assistant Ready:** Includes pre-written prompt guides and slash commands so assistants (Gemini, Claude, Antigravity, or local LLMs) can read your tasks and update your daily schedule directly on disk.
* **Realistic Time Estimates:** Tracks how long tasks actually take versus your estimates, gradually learning personal time multipliers so you don't overschedule your day.
* **Calendar Integration:** Pulls in external Google Calendar events to ensure focus blocks are never scheduled over meetings or classes.
* **System Health Check (`/doctor`):** Built-in diagnostic check to verify that tags, dates, and file formats are valid and consistent.

---

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/tama-gucci/chrysalis.git ~/Chrysalis
cd ~/Chrysalis

# Run the setup script to detect your local timezone and initialize templates
./bootstrap.sh
```

### 2. Open in Obsidian
1. Install [Obsidian](https://obsidian.md).
2. Choose **Open folder as vault** and select the `~/Chrysalis` directory.
3. Turn on community plugins when prompted (TaskNotes, Dataview, Obsidian Git).

### 3. Set Up Your Goals
Open your AI assistant in the vault folder and run:
```text
/onboard
```
The assistant will guide you through setting up your initial life roadmap, priority pillars, and first tasks.

---

## Available Commands

| Command | Purpose |
| :--- | :--- |
| **`/onboard`** | Walk through initial setup of your goals, roadmap, and daily routine. |
| **`/morning`** | Log morning wake time and energy to adjust today's schedule. |
| **`/evening`** | Review completed tasks and prepare tomorrow's schedule. |
| **`/plan`** | Generate or adjust focus sprint blocks for the day. |
| **`/task`** | Add a new task with automatic category tagging and time estimates. |
| **`/doctor`** | Run a quick health check to verify note formatting and tags. |
| **`/zettel`** | Capture a quick note or thought in your knowledge base. |
| **`/pause`** | Pause automatic daily scheduling while traveling or taking time off. |

---

## License
This project is open-source under the [MIT License](LICENSE).
