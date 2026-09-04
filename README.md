# Chrysalis

A calm, flexible daily planner and notebook that adapts when life happens.

> **Project status:** Chrysalis is an early-stage personal project in active development. Things are still evolving as it's tested and refined in daily use.

---

## What is Chrysalis?

Most calendar apps and to-do lists treat you like a machine. They assume you'll wake up at the exact same minute every day, work through tasks in neat little boxes, and never get tired, distracted, or interrupted.

When real life gets in the way—you wake up late, a meeting runs long, or you're just having a slow day—rigid schedules fall apart. You end up with a wall of red overdue badges, a sense of guilt, and a plan you don't even want to look at anymore.

**Chrysalis is designed to be forgiving.** It's a personal planning notebook that lives on your computer, paired with an AI assistant that helps you organize your days. Instead of forcing you to stick to an unrealistic schedule, it reshapes your day around what actually happens, helping you focus on what matters most without the stress.

Best of all, your notes and to-do lists are saved as simple, readable text files right on your own machine. There's no vendor lock-in, no hidden database, and no paid monthly subscription required.

---

## How It Helps: Real-World Examples

The easiest way to understand Chrysalis is to look at how it handles common everyday situations:

### 1. Waking up late without wrecking your day
> **The scenario:** You planned to start work at 8:00 AM. Instead, you overslept, woke up groggy at 9:15 AM, and by the time you made coffee it was 9:45 AM.

With a standard calendar, half your morning is already "lost" and you're playing catch-up before you even begin. 

With Chrysalis, you just do a quick morning check-in: *"I woke up at 9:15 and I'm moving a little slowly today."*

Chrysalis takes that in stride. It slides your schedule forward to start when your day actually began, trims off low-priority clutter, and makes sure your top 1–2 important items still have room to breathe. No frantic dragging of calendar blocks, and no guilt.

---

### 2. Protecting time for big goals before chores take over
> **The scenario:** You want to write a book, learn a new language, or fix up the back patio. But every day, answering messages, running errands, and doing laundry end up swallowing all your free hours.

When you're juggling a dozen small chores, the big personal projects always get pushed to "someday."

Chrysalis helps you keep your long-term goals in sight. When it plans your day, it prioritizes carving out a dedicated window of high-energy focus for your main project first thing, before routine chores and administrative tasks fill up the afternoon.

---

### 3. Learning how long things actually take
> **The scenario:** You tell yourself that cleaning the kitchen will take "just twenty minutes," but whenever you actually do it, an hour has gone by.

Most of us consistently underestimate how long everyday tasks take. Over time, that optimism leads to cramming seven hours of work into a four-hour afternoon, leaving us feeling exhausted and unproductive.

Whenever you finish a task in Chrysalis, it takes note of how long it actually took compared to what you estimated. Over time, it gently adjusts future estimates so your schedules become realistic and sustainable.

---

### 4. Winding down at night with a clear head
> **The scenario:** It's 10:30 PM. You're trying to relax, but your mind is racing with everything you didn't finish today and wondering what you have to do tomorrow morning.

Before you log off for the evening, Chrysalis invites you to do a two-minute evening check-in. It reviews what you got done, checks your calendar for tomorrow's commitments (like a doctor's appointment or a parent-teacher conference), and drafts a clean, realistic plan for the next morning. 

You can close your laptop knowing that tomorrow is already organized, giving you a chance to actually relax and get a good night's sleep.

---

### 5. Taking time off without returning to a mess
> **The scenario:** You caught a bad cold, or you're heading out for a long weekend trip.

On traditional task apps, taking three days off means coming back to thirty overdue notifications in bright red. 

With Chrysalis, you can simply say you're taking a break. Chrysalis pauses your planning cycle and clears your active schedule. When you return, you simply check in, and it helps you start fresh without a mountain of backlog guilt.

---

## How the Pieces Fit Together

You don't need any technical background to understand how Chrysalis works. It brings together three simple tools:

```
+-------------------------------------------------------------+
|                                                             |
|   1. Obsidian (Your Notebook)                               |
|      A clean, distraction-free app where you write notes,   |
|      keep checklists, and view your schedule.               |
|                                                             |
|                              ▲                              |
|                              │                              |
|                              ▼                              |
|                                                             |
|   2. Plain Text Files (Your Data)                           |
|      All your notes and tasks are saved as simple text      |
|      files on your computer. You own your data forever.     |
|                                                             |
|                              ▲                              |
|                              │                              |
|                              ▼                              |
|                                                             |
|   3. An AI Assistant (Your Planning Partner)                |
|      A friendly helper you can chat with to organize tasks, |
|      draft schedules, and adjust plans when things change.  |
|                                                             |
+-------------------------------------------------------------+
```

### What About Syncing to Your Phone?
**Cloud storage is completely optional, but very helpful.**

Chrysalis works 100% locally on a single laptop or desktop computer with zero cloud setup needed. 

However, if you put your Chrysalis folder inside a cloud storage provider of your choice (such as iCloud, Dropbox, OneDrive, Syncthing, or Google Drive), your notes will sync automatically between your devices. That means you can:
* Check off tasks from your phone while running errands.
* View your daily schedule on a tablet while working at your desk.
* Add a quick thought or to-do item on the go, knowing it will be waiting on your computer when you sit down.

---

## Everyday Commands

When you want to plan your day or update your tasks, you can talk to the assistant naturally or use simple shortcuts:

| Command | What it does in plain English |
| :--- | :--- |
| **`/morning`** | **Morning Check-In:** Tell the assistant what time you woke up and how energetic you feel. It adjusts your schedule for the day accordingly. |
| **`/evening`** | **Evening Review:** Look over what you finished today, see what's on your calendar tomorrow, and draft tomorrow's plan so you can rest easy. |
| **`/plan`** | **Daily Planner:** Organize your to-do list into realistic focus blocks that fit comfortably around your meetings and personal appointments. |
| **`/task`** | **Quick Add:** Add a new task with an estimated time and category (e.g. *Finish quarterly invoice, 45m, work*). |
| **`/pause`** | **Take a Break:** Pause your daily schedules for vacations, sick days, or weekends so tasks don't pile up while you're away. |
| **`/doctor`** | **Quick Checkup:** Runs a quick health check on your notes to make sure files and links are tidy and working properly. |

---

## Getting Started

Setting up Chrysalis takes just a few steps:

### 1. Download Obsidian
Install [Obsidian](https://obsidian.md) (it's free for personal use on macOS, Windows, and Linux). Obsidian is the notebook app where your tasks and daily pages will be displayed.

### 2. Get Your Chrysalis Folder
Download or clone this repository to a convenient location on your computer (such as your documents folder, or inside a synced cloud folder if you want cross-device access):

```bash
git clone https://github.com/tama-gucci/chrysalis.git ~/chrysalis
```

### 3. Open the Folder in Obsidian
* Open Obsidian and choose **"Open folder as vault"**.
* Select the `chrysalis` folder you just downloaded.
* When prompted, enable the community plugins included with the setup (these help render task lists, calendar views, and dashboards).

### 4. Say Hello to Your Assistant
Open the folder in your AI assistant workspace (like Google Antigravity) and run the intake check-in:

```text
/onboard
```

The assistant will ask a few friendly questions about what your days look like, what major projects you're working on, and how you prefer to structure your time. From there, it sets up your starter templates and you're ready to plan your first day.

---

## Your Data Belongs to You

Most modern productivity tools lock your life behind proprietary web apps. If the service shuts down, raises its prices, or loses your data, you're stuck.

With Chrysalis:
* **No vendor lock-in:** Every task, plan, and note is a standard Markdown text file. You can open and read them with any text editor on any computer, now or twenty years from now.
* **No required accounts:** You don't need to create a third-party account just to track your daily chores.
* **Zero tracking:** Your personal tasks and thoughts stay on your own hardware.

---

## Community & Contributing

Chrysalis was born out of a desire for a calmer, more humane approach to personal organization. If you have ideas, feedback, or want to contribute improvements, feel free to open an issue or pull request on GitHub.

### License
This project is open source and available under the [MIT License](LICENSE).
