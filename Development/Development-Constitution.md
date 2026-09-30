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
1. **The Runtime Sphere (`System/`, `TaskNotes/Tasks/`):** The private, local execution substrate of daily life focus, chronotype rhythms, task execution, and personal memory. All runtime state files containing personal data are strictly quarantined from public version control. Governed by the **Runtime Constitution** ([`System/Runtime-Constitution.md`](../System/Runtime-Constitution.md)).
2. **The Development Sphere (`Development/` in the source repository):** The engineering and architecture substrate governing open-source framework design, skill authoring, recursive self-improvement (`/evolve`), and codebase maintenance. Governed by this Development Constitution.

The root **Master Constitution** ([`AGENTS.md`](../AGENTS.md)) serves as the unified single source of truth across both spheres for autonomous AI agent platforms.

The fundamental law of the Development Sphere is the preservation of privacy, architectural purity, and safe system evolution.

---

## Article I: Absolute Zero-Leak PII Law (GitHub Privacy Invariant)
The Chrysalis codebase is hosted on a public GitHub repository (`tama-gucci/chrysalis`). Under NO circumstances may any Personal Identifiable Information (PII), personal data, or private device secrets ever be tracked, committed, or pushed to GitHub.

### 1. Quarantined Personal Substrates
The following paths are designated as strictly private and MUST NEVER be tracked by git or pushed to GitHub:
* **Personal Tasks, Archives & Obsidian Plugin Workflows:** `TaskNotes/Tasks/*.md` (except `example-task.md`), task archive (`TaskNotes/Archive/*.md`), and personal Obsidian TaskNotes Workflows plugin files (`TaskNotes/Workflows/*` except `README.md`).
* **Live System Memory & Roadmaps:** `System/Life-Roadmap.md`, `System/Memory.md`, `System/Ingestion-Sources.md`, `System/System-Health.md`, `System/Changelog.md`.
* **Daily Focus & Journal Notes:** All daily notes matching `YYYY-MM-DD*.md` and `Daily/*.md` / `TaskNotes/Daily/*.md`.
* **Personal Projects, Slipbox Thoughts & Translated Sources:** `Projects/*` (except `Projects/README.md` and `Projects/_templates/**`), `Slipbox/*` (except `Slipbox/README.md` and `Slipbox/_templates/**`), and `Sources/*` (except `Sources/README.md`).
* **Personal Workstation Telemetry:** `System/Environment/*.md` manifests (e.g. `obelisk.md`, `surface-pro-x.md`, `Active-Profile.md`) and private workstation configurations.
* **Local Databases, Virtual Environments & Build Artifacts:** `Nexus/` SQLite databases, `.conversations/`, `.workspaces/`, `.obsidian/plugins/*/data/`, `*.token.json`, `*credentials*.json`, `*.env`, `*.db`, `*.sqlite*`, and private keys.

### 2. Mandatory 1-to-1 Public Template Matrix
Every file type that contains personal runtime information MUST provide an exact, sanitized template in public version control:
* `System/Life-Roadmap.md` $\to$ `System/_templates/Life-Roadmap.template.md`
* `System/Memory.md` $\to$ `System/_templates/Memory.template.md`
* `System/Ingestion-Sources.md` $\to$ `System/_templates/Ingestion-Sources.template.md`
* `System/System-Health.md` $\to$ `System/_templates/System-Health.template.md`
* `System/Changelog.md` $\to$ `System/_templates/Changelog.template.md`
* `Daily Notes (YYYY-MM-DD.md)` $\to$ `System/_templates/Daily-Note.template.md`
* `TaskNotes/Tasks/*.md` $\to$ `_templates/Task-Template.md` & `example-task.md`
* `Projects/*/Roadmap.md` $\to$ `Projects/_templates/Project-Template.md`
* `Slipbox/*.md` $\to$ `Slipbox/_templates/Slipbox-Template.md`
* `Sources/*.md` $\to$ `_templates/Source-Template.md`
* `System/Environment/*.md` $\to$ `System/Environment/_templates/System-Manifest-Template.md`

### 3. Synthetic Placeholder Standard
All public code, documentation, examples, and skill runbooks must strictly use synthetic/mock values:
* Names: `Jane Doe`, `Alex Developer` (never real names).
* Emails: `user@example.com` (never personal email addresses).
* Filesystem Paths: Relative paths (`TaskNotes/...`, `source/...`) or home-relative (`~/vault`). Never machine-specific absolute user paths like `/home/<username>/...` or `C:\Users\<username>\...`.
* Hostnames: `station-node`, `dev-laptop` (never personal machine hostnames).
* **Life Roadmap & Milestone Anonymization Invariant:** All placeholder examples, documentation tables, skill runbooks, and test cases must ALWAYS be synthetic and anonymized, and must NEVER be derived from or mirror the user's actual personal Life Roadmap, private milestones, institutions, educational/vocational entities, employer names, or personal projects. Examples must use purely generic or technical concepts (e.g., "Compiler Engineering", "Distributed Key-Value Store", "Algorithmic Trading Engine", "Library Modernization").

### 4. Default-Deny Git Architecture
`.gitignore` must strictly maintain a default-deny (`/*`) posture. No whole-directory whitelisting is permitted without rigorous constitutional review.

---

## Article II: Development Organization & Directory Structure
All development-specific assets reside exclusively within `Development/` in the source repository:

* **`AGENTS.md`:** Root Master Constitution unifying Runtime and Development Spheres for autonomous AI agents.
* **`Development/Development-Constitution.md` (This File):** Constitutional laws of engineering, PII hygiene, and RSI.
* **`Development/README.md`:** Developer guide, architecture orientation, and git workflow.
* **`Development/scripts/`:** Developer utility scripts, PII linters, git boundary verifiers, and setup helpers.
* **`Development/skills/`:** Modular development-only agent skills (`audit-dev`, `evolve`), registered for Google Antigravity, OpenAI Codex, and local coding agents via `.agent/skills.json` and `AGENTS.md`.
* **`contracts/`:** Formal runtime and collection contracts (`agent-runtime.contract.md`, `mdbase-collection.contract.md`, `ingestion-input.contract.md`).
* **`System/Workflows/`:** Portable 8-stage AI agent lifecycle workflow runbooks (`01-capture.md` through `08-continuation.md`).
* **`_types/`:** Authoritative JSON Schema Draft 2020-12 data schemas (`task.md`, `project.md`, `source.md`, `zettel.md`, `system_state.md`).
* **`helpers/`:** Deterministic A2 helper utilities (`mdbase_helper.py`, `ingestion_contract.py`, `helpers/providers/`) providing CAS concurrency, validation, duplicate detection, provider-neutral ingestion normalization, and provenance tracking.

### Architectural Invariants in Development
1. **Pure AI Agent Framework & A2 Access Layer:** Chrysalis operates directly on an mdbase v0.3 Markdown database collection via the A2 local access layer (`vault_paths.py --runtime`, `helpers/mdbase_helper.py`, `mdbase -C <vault>`, `doctor.py`, `tests/harness/validation_harness.py`). All operations are mediated by formal runtime contracts, and core `/ingest` (`discover → extract → draft → prevalidate → approve → apply → verify`) remains strictly decoupled from optional provider integration skills (`google-drive`, `google-tasks`).
2. **Decoupled User Interfaces:** User interfaces (Obsidian with TaskNotes plugin, Google Calendar) and AI coding/desktop clients (Google Antigravity, OpenAI Codex, Claude Code/Desktop) are decoupled client applications, not internal framework daemons.
3. **Hardware Portability & Local Authority:** The local Markdown files are the authoritative truth. Operations do not depend on cloud daemons or persistent background services.

---

## Article III: Recursive Self-Improvement (RSI) Protocol
System growth and autonomous capability expansion occur exclusively via the `/evolve` engine in development environments:

1. **Development-Only Execution:** `/evolve` is an engineering tool executed interactively in the selected coding agent, including Antigravity or Codex. It is never invoked during automated daily runtime routines. Shared engineering context follows [AGENT-WORKFLOW.md](AGENT-WORKFLOW.md).
2. **Mandatory Snapshot Rollback Anchor:** Prior to modifying any existing skill file in `.agent/skills/` or `Development/skills/`, the agent MUST write a timestamped backup copy to `.agent/skills/.backup/<skill>_<timestamp>.md`.
3. **Constitutional Pre-Commit Linter:** Every proposed modification to skills, workflows, or schemas must be verified against:
   * Explicit local timezone offset compliance (`"-05:00"`).
   * File substrate single source of truth (vault filesystem).
   * Mandatory physical disk mutation (Anti-Simulation Law).
   * Zero-Leak PII compliance (no personal paths or strings).
   * Dynamic state multiplier bounds clamped strictly to $[0.20, 2.00]$.
   * Synthetic placeholder & roadmap anonymization compliance (no real user milestones, institutions, or personal projects).
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
* **Anti-Simulation Law:** Chat text alone NEVER modifies code, skills, or documentation. All development modifications must be physically persisted to physical disk via local file mutation tools (`replace_file_content` / `write_to_file` / `apply_patch` / `apply_cas_mutation`).
