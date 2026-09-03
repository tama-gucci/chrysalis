---
type: developer_guide
id: chrysalis-development-readme
status: active
version: 1.0.0
---

# 🛠️ Chrysalis Development & Engineering Hub

Welcome to the **Chrysalis Development Sphere**. This directory contains all architecture specifications, developer tooling, development-only agent skills, and environment manifests for engineering the Chrysalis framework.

All activities within this directory are strictly governed by the [`Development-Constitution.md`](Development-Constitution.md).

---

## 📁 Directory Structure

```
chrysalis/Development/
├── Development-Constitution.md   # The supreme engineering law, zero-leak PII rules & RSI invariants
├── README.md                     # This onboarding and developer orientation guide
├── scripts/                      # Developer utilities, PII scanner, and git boundary checkers
│   └── pii-scanner.sh            # Automated pre-commit and CI PII validation script
├── skills/                       # Modular development-only agent skills (registered in .agent/skills.json)
│   ├── audit-dev/                # /audit-dev: Git boundary, zero-leak PII scanner & evolve coordinator
│   └── evolve/                   # /evolve: Proactive capability expansion & recursive self-improvement
└── Environment/                  # Workstation profiles, hardware manifests & telemetry (quarantined)
    ├── Environment-Index.md      # Dataview index of registered developer machines
    ├── Active-Profile.md         # Active development node pointer
    ├── _templates/               # Clean public workstation manifest templates
    └── scripts/                  # Manifest generation and environment detection utilities
```

---

## 🔒 The Absolute Zero-Leak PII Law

Chrysalis is an open-source framework hosted on GitHub (`tama-gucci/chrysalis`). To guarantee that private user data never leaks to public version control, the repository enforces a strict **Zero-Leak Whitelist (Default-Deny)** architecture:

1. **Default-Deny `.gitignore`:** Everything is ignored by default (`/*`), and only explicitly whitelisted open-source framework assets and templates are tracked.
2. **1-to-1 Template Rule:** Every file containing personal user information (tasks, roadmaps, chronotype memory, health logs, daily notes) MUST have a corresponding sanitized `.template.md` tracked in git.
3. **Synthetic Placeholders Only:** Never commit real names, usernames, machine-bound paths (`/home/...`), personal emails, or credentials. Use `Jane Doe`, `user@example.com`, and relative paths (`chrysalis/...`).

---

## 🚀 Developer Workflows

### 1. Pre-Commit Verification Gate
Before staging or pushing any commits to GitHub, execute the Development Audit:
```bash
/audit-dev
```
Or run the standalone script:
```bash
bash Development/scripts/pii-scanner.sh
```

### 2. Recursive Self-Improvement (RSI) via `/evolve`
When developing new features, skills, or workflows:
* Use `/evolve` to scan unintegrated `#chrysalis` notes from `Slipbox/`.
* Synthesize 5-vector integration specs (Workflows, Skills, Dashboard UI, Operational Memory, Orchestrator Adapters).
* Always test optimizations with pre-commit snapshots in `.agent/skills/.backup/`.

### 3. Adding or Updating Agent Skills
* **Runtime Skills:** Placed in `.agent/skills/<skill-name>/SKILL.md` (e.g. `audit`, `plan`, `morning`, `evening`, `doctor`).
* **Development Skills:** Placed in `Development/skills/<skill-name>/SKILL.md` (registered via `.agent/skills.json`).
