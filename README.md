# Chrysalis

> A transparent, Markdown-based task management and daily scheduling framework for Obsidian, designed to work alongside AI assistants.

> [!WARNING]
> **Project Status: Early Alpha**  
> Chrysalis is currently in active personal development and is not yet ready for general use. Formats and features may change frequently.

Chrysalis is an open-source task management and daily scheduling framework built with plain Markdown files in Obsidian. It was created out of frustration with subscription-based productivity apps that hide their mechanics behind closed software and lock your task history behind ongoing monthly payments.

With Chrysalis, your tasks, roadmaps, and scheduling logic exist as standard text files you control. It is designed to work with everyday tools like Google Calendar and Google Drive, while giving AI assistants (such as Gemini, Claude, or local models) structured instructions to help organize and calibrate your daily routine.

---

## Why Chrysalis

* **Transparent and Inspectable:** Every rule, schedule calculation, and task state is stored in readable Markdown files. You can see exactly how your schedule is built and modify the system rules at any time.
* **No Subscription Lock-In:** You own your data completely. You will never lose access to your tasks, historical logs, or roadmap if you stop paying for a service.
* **Practical Cloud and Calendar Integration:** Integrates with Google Calendar to prevent scheduling over existing events and syncs across devices using Google Drive or Git.
* **AI-Assisted Planning:** Provides AI assistants with clear instructions to draft realistic schedules based on your priorities and when you actually wake up.

---

## How It Works

Chrysalis is organized around a simple daily workflow:

1. **Evening Review (`/evening`):**
   * Review what you finished today.
   * Check tomorrow's calendar commitments to avoid conflicts.
   * Pick 2–3 priority items from your roadmap to stage a draft schedule for tomorrow.

2. **Morning Check-In (`/morning`):**
   * Log when you woke up and your energy level (1–5).
   * The system shifts your planned focus blocks to match your actual wake time.

3. **Daily Focus Blocks (`/plan`):**
   * Work is grouped into 75–90 minute blocks separated by short rest breaks.
   * Demanding analytical work is placed in morning focus windows, while administrative or lighter tasks are placed in afternoon recovery periods.

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
The assistant will guide you through setting up your initial roadmap, priority pillars, and first tasks.

---

## Available Commands

| Command | Purpose |
| :--- | :--- |
| **`/onboard`** | Walk through initial setup of your goals, roadmap, and daily routine. |
| **`/morning`** | Log morning wake time and energy to adjust today's schedule. |
| **`/evening`** | Review completed tasks and prepare tomorrow's schedule. |
| **`/plan`** | Generate or adjust focus blocks for the day. |
| **`/task`** | Add a new task with category tagging and time estimates. |
| **`/doctor`** | Run a health check to verify note formatting and tags. |
| **`/zettel`** | Capture a quick note or thought in your knowledge base. |
| **`/pause`** | Pause automatic daily scheduling while traveling or taking time off. |

---

## License
This project is open-source under the [MIT License](LICENSE).
