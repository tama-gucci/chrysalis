---
type: system_specification
id: chrysalis-development-constitution
status: evergreen_constitution
version: 5.0.0
domain: development
---

# Chrysalis Development Constitution

> Architecture decision (2026-09-12): keep the personal runtime vault separate from the development repository. Runtime framework files are deployed snapshots; edit reusable code and runbooks in source. ARCHITECTURE.md defines supported layouts, and STATUS.md is the implementation reference. Future capabilities below must not be assumed operational.


## Preamble: Separation of Spheres (Runtime vs. Development)
Chrysalis operates across two strictly segregated functional domains:
1. **The Runtime Sphere (`chrysalis/System/`, `chrysalis/TaskNotes/Tasks/` or `System/`, `TaskNotes/Tasks/`):** The private, local execution substrate of daily life focus, chronotype rhythms, task execution, and personal memory. All runtime state files containing personal data are strictly quarantined from public version control. Governed by the **Runtime Constitution** ([`System/Runtime-Constitution.md`](../System/Runtime-Constitution.md)).
2. **The Development Sphere (`Development/` in the source repository):** The engineering and architecture substrate governing open-source framework design, skill authoring, recursive self-improvement (`/evolve`), and codebase maintenance. Governed by this Development Constitution.

The root **Master Constitution** ([`AGENTS.md`](../AGENTS.md)) serves as the unified single source of truth across both spheres for autonomous AI agent platforms.

The fundamental law of the Development Sphere is the preservation of privacy, architectural purity, and safe system evolution.

---

## Article I: Absolute Zero-Leak PII Law (GitHub Privacy Invariant)
The Chrysalis codebase is hosted on a public GitHub repository (`tama-gucci/chrysalis`). Under NO circumstances may any Personal Identifiable Information (PII), personal data, or private device secrets ever be tracked, committed, or pushed to GitHub.

### 1. Quarantined Personal Substrates
The following paths are designated as strictly private and MUST NEVER be tracked by git or pushed to GitHub:
* **Personal Tasks & Archives:** `chrysalis/TaskNotes/Tasks/*.md`, `TaskNotes/Tasks/*.md`, and `chrysalis/Tasks/*.md` (except `example-task.md`), and task archive (`chrysalis/TaskNotes/Archive/*.md`, `TaskNotes/Archive/*.md`, `chrysalis/Archive/*.md`).
* **Live System Memory & Roadmaps:** `System/Life-Roadmap.md`, `System/Memory.md`, `System/System-Health.md`, `System/Changelog.md`.
* **Daily Focus & Journal Notes:** All daily notes matching `YYYY-MM-DD*.md` and `chrysalis/Daily/*.md` / `TaskNotes/Daily/*.md`.
* **Personal Projects & Slipbox Thoughts:** `Projects/*` (except `Projects/README.md` and `Projects/_templates/**`) and `Slipbox/*` (except `Slipbox/README.md` and `Slipbox/_templates/**`).
* **Personal Workstation Telemetry:** `System/Environment/*.md` manifests (e.g. `obelisk.md`, `surface-pro-x.md`, `Active-Profile.md`) and private workstation configurations.
* **Local Databases, Virtual Environments & Build Artifacts:** `Nexus/` SQLite databases, `.conversations/`, `.workspaces/`, `.obsidian/plugins/*/data/`, `*.token.json`, `*credentials*.json`, `*.env`, `*.db`, `*.sqlite*`, and private keys.

### 2. Mandatory 1-to-1 Public Template Matrix
Every file type that contains personal runtime information MUST provide an exact, sanitized template in public version control:
* `System/Life-Roadmap.md` $\to$ `System/_templates/Life-Roadmap.template.md`
* `System/Memory.md` $\to$ `System/_templates/Memory.template.md`
* `System/System-Health.md` $\to$ `System/_templates/System-Health.template.md`
* `System/Changelog.md` $\to$ `System/_templates/Changelog.template.md`
* `Daily Notes (YYYY-MM-DD.md)` $\to$ `System/_templates/Daily-Note.template.md`
* `chrysalis/TaskNotes/Tasks/*.md` $\to$ `_templates/Task-Template.md` & `example-task.md`
* `Projects/*/Roadmap.md` $\to$ `Projects/_templates/Project-Template.md`
* `Slipbox/*.md` $\to$ `Slipbox/_templates/Slipbox-Template.md`
* `System/Environment/*.md` $\to$ `System/Environment/_templates/System-Manifest-Template.md`

### 3. Synthetic Placeholder Standard
All public code, documentation, examples, and skill runbooks must strictly use synthetic/mock values:
* Names: `Jane Doe`, `Alex Developer` (never real names).
* Emails: `user@example.com` (never personal email addresses).
* Filesystem Paths: Relative paths (`chrysalis/...`, `source/...`) or home-relative (`~/chrysalis`). Never machine-specific absolute user paths like `/home/<username>/...` or `C:\Users\<username>\...`.
* Hostnames: `station-node`, `dev-laptop` (never personal machine hostnames).

### 4. Default-Deny Git Architecture
`.gitignore` must strictly maintain a default-deny (`/*`) posture. No whole-directory whitelisting is permitted without rigorous constitutional review.

---

## Article II: Development Organization & Directory Structure
All development-specific assets reside exclusively within `Development/` in the source repository:

* **`AGENTS.md`:** Root Master Constitution unifying Runtime and Development Spheres for autonomous AI agents.
* **`Development/Development-Constitution.md` (This File):** Constitutional laws of engineering, PII hygiene, and RSI.
* **`Development/README.md`:** Developer guide, architecture orientation, and git workflow.
* **`Development/scripts/`:** Developer utility scripts, PII linters, git boundary verifiers, and setup helpers.
* **`Development/skills/`:** Modular development-only agent skills (`audit-dev`, `evolve`), registered into Antigravity via `.agent/skills.json`.
* **`contracts/`:** Formal runtime and collection contracts (`agent-runtime.contract.md`, `mdbase-collection.contract.md`).
* **`_types/`:** Authoritative JSON Schema Draft 2020-12 data schemas (`task.md`, `project.md`, `source.md`, `zettel.md`).
* **`helpers/`:** Deterministic helper utilities (`mdbase_helper.py`) providing CAS concurrency, validation, and provenance tracking.

### Architectural Invariants in Development
1. **Pure AI Agent Framework:** Chrysalis operates directly on an mdbase v0.3 Markdown database collection. All operations are mediated by formal runtime contracts.
2. **Decoupled User Interfaces:** User interfaces (Obsidian with TaskNotes plugin, Google Calendar) and candidate AI integrations (Gemini Spark, Claude Desktop) are decoupled client applications, not internal framework daemons.
3. **Hardware Portability & Local Authority:** The local Markdown files are the authoritative truth. Operations do not depend on cloud daemons or persistent background services.

---

## Article III: Recursive Self-Improvement (RSI) Protocol
System growth and autonomous capability expansion occur exclusively via the `/evolve` engine in development environments:

1. **Development-Only Execution:** `/evolve` is an engineering tool executed interactively in the selected coding agent, including Antigravity or Codex. It is never invoked during automated daily runtime routines. Shared engineering context follows [AGENT-WORKFLOW.md](AGENT-WORKFLOW.md).
2. **Mandatory Snapshot Rollback Anchor:** Prior to modifying any existing skill file in `.agent/skills/` or `Development/skills/`, the agent MUST write a timestamped backup copy to `.agent/skills/.backup/<skill>_<timestamp>.md`.
3. **Constitutional Pre-Commit Linter:** Every proposed modification to skills, workflows, or schemas must be verified against:
   * Explicit local timezone offset compliance (`"-05:00"`).
   * File substrate single source of truth (`chrysalis/`).
   * Mandatory physical disk mutation (Anti-Simulation Law).
   * Zero-Leak PII compliance (no personal paths or strings).
   * Dynamic state multiplier bounds clamped strictly to $[0.20, 2.00]$.
4. **Rollback Guarantee:** If a modified skill produces degraded behavior, the agent must immediately restore the previous snapshot via `/evolve --rollback <skill>`.
5. **Formal Changelog Auditing:** All mutations and architectural proposals must be recorded in `System/Changelog.md`.

---

## Article IV: Pre-Commit & Pre-Push Security Gate
Before creating any git commit or pushing to GitHub, the developer or agent MUST execute the development audit skill:

```bash
/audit-dev
```

The pre-flight gate strictly enforces:
1. **Quarantined Path Check:** Zero tracked files in `git ls-files` matching private task notes, personal roadmaps, daily notes, or private manifests.
2. **Deep Content Scanner:** Zero occurrences of `/home/<username>`, personal emails, auth tokens (`ghp_`, `AIza`), or private keys across all git-tracked files.
3. **Staged Diff Review:** Zero PII or secrets present in `git diff --cached`.
4. **Default-Deny Whitelist Check:** Verification that `.gitignore` maintains root `/*` denial.

A failure of ANY point in the pre-commit gate immediately blocks commit creation.

---

## Article V: Substrate Portability & Anti-Simulation Laws
* **Cross-Platform Compatibility:** Development scripts and tools must remain POSIX-compliant and account for cloud sync filesystems (e.g., avoiding hard filesystem symlinks on FUSE mounts such as Google Drive).
* **Anti-Simulation Law:** Chat text alone NEVER modifies code, skills, or documentation. All development modifications must be physically persisted to physical disk via tool calls (`replace_file_content` / `write_to_file`).
