---
name: onboard
description: "Interactive autonomous onboarding engine: detects environment telemetry and timezone, guides the user through a 4-step intake interview or archetype preset, compiles Life-Roadmap.md and tag_registry, seeds Scheduling-Memory.md multipliers and candidate pools, and runs pre-flight /doctor validation."
trigger: "/onboard"
reads:
  - "chrysalis/System/Life-Roadmap.md"
  - "chrysalis/System/Scheduling-Memory.md"
  - "chrysalis/System/_templates/Life-Roadmap.template.md"
  - "chrysalis/System/_templates/Scheduling-Memory.template.md"
writes:
  - "chrysalis/System/Life-Roadmap.md"
  - "chrysalis/System/Scheduling-Memory.md"
  - "chrysalis/TaskNotes/Tasks/*.md"
---

# /onboard (Autonomous Onboarding & Life-Roadmap Engine)

## Execution Protocol

### Step 1: Pre-Flight State & Environment Detection
1. **Timezone Offset Detection:**
   * Inspect current local timezone from runtime environment (e.g., `-05:00`, `-04:00`, `+01:00`).
   * Read `System/Scheduling-Memory.md`. If missing, copy from `System/_templates/Scheduling-Memory.template.md` and stamp the detected `timezone_offset`.
2. **Roadmap Existence Check:**
   * Read `System/Life-Roadmap.md`.
   * If `Life-Roadmap.md` already contains an active customized roadmap, prompt the user whether they wish to **(A) Refine current roadmap**, or **(B) Full Reset & Re-Onboard**.

---

### Step 2: Conversational Intake & Archetype Selection

Prompt the user with the interactive onboarding intake:

> *"👋 Welcome to Chrysalis OS! Let's configure your strategic roadmap and daily bio-cognitive focus rhythms.*
> 
> *Choose a starter archetype or reply with your personal goals:*
> 1. 🎓 **Student / Academic:** *Coursework, degree milestones, administrative appeals, exams.*
> 2. 💻 **Solo Founder / Developer:** *Product build, technical architecture, launch sprint, revenue.*
> 3. 🏛️ **Career Switcher / Licensure:** *Certifications, portfolio development, job outreach, credentials.*
> 4. 🎨 **Creator / Freelancer:** *Client deliverables, content pipeline, audience growth, business admin.*
> 5. ✍️ **Custom / Brainstorm:** *Paste a raw list of your current priorities, projects, and deadlines.*"

---

### Step 3: Taxonomy & Tag Registry Compilation

When the user selects an archetype or provides their priorities:

1. **Extract 3–5 Strategic Pillars:**
   * **Pillar 1:** Immediate operational reset & high-urgency deliverables (Active • Weeks 1–12).
   * **Pillar 2:** Medium-term core execution & milestone launch (Planned • Months 3–6).
   * **Pillar 3:** Long-term mastery, scaling, or credentialing (Horizon • Months 6–24).
2. **Generate Subtag Registry:**
   * Create standardized, lowercase hyphenated tags:
     `pillar-1/admin`, `pillar-1/setup`, `pillar-1/core`, `pillar-1/portfolio`, `pillar-2/growth`, etc.
3. **Chunk 14-Day Rolling Horizons:**
   * Structure Pillar 1 into actionable 14-day milestone blocks (`Milestone M1.1`, `M1.2`) with explicit dated horizon windows and key result checklists annotated with `#pillar-X/subtag`.

---

### Step 4: Dual-File System Synchronization (Physical Tool Calls)

> [!CAUTION]
> **Anti-Simulation Invariant:** The orchestrator MUST execute physical tool calls (`write_to_file` / `replace_file_content`) to persist changes to disk.

1. **Write `System/Life-Roadmap.md`:**
   * Serialize the compiled frontmatter with valid `tag_registry`, `active_pillar`, and formatted Markdown body.
2. **Update `System/Scheduling-Memory.md`:**
   * Update `system_state.active_pillar` to match Pillar 1.
   * Inject all compiled tags into `tag_multipliers` initialized to baseline `1.00`.
   * Inject matching tags into `inferred_task_pool.learning_weights` initialized to `1.00`.
   * Seed the `inferred_task_pool.tasks` with 2–4 starter candidate tasks extracted from Milestone M1.1.
3. **Generate Starter Task Notes:**
   * If requested, generate 1–2 initial starter task notes in `TaskNotes/Tasks/*.md` adhering strictly to the Universal TaskNotes Frontmatter Schema.

---

### Step 5: Diagnostic Verification Gate

1. Read and execute `.agent/skills/doctor/SKILL.md` (or run automated 6-point integrity pass).
2. Verify:
   * **Check #1:** Universal frontmatter schema valid.
   * **Check #2:** Explicit local timezone serialized.
   * **Check #3:** 100% tag alignment between `Life-Roadmap.md` and `Scheduling-Memory.md`.
3. Report final system health to the user and present tomorrow's initial focus schedule.
