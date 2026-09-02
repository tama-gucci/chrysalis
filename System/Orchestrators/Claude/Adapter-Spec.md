---
type: orchestrator_adapter_spec
id: chrysalis-orchestrator-claude
name: "Anthropic Claude Orchestrator Adapter"
orchestrator_platform: "anthropic_claude"
status: reference
version: 1.1.0
last_updated: "2026-09-02T13:42:00-05:00"

capability_tiers:
  operational_tier:
    alias: "claude-sonnet-latest"
    pinned_tested: "claude-3-7-sonnet"
    role: "Daily operational loops, fast frontmatter mutations, and scheduling"
  deep_reasoning_tier:
    alias: "claude-thought-latest"
    pinned_tested: "claude-3-7-sonnet-thought"
    role: "RSI audits, skill mutation verification, diagnostic auto-heals"
---

# 🎭 Anthropic Claude Orchestrator Adapter (Reference Spec)

This document specifies the integration configuration, capability tier routing, tool bindings, and prompt wrappers when using **Anthropic Claude** (e.g. Claude Code CLI or Claude Desktop with Model Context Protocol) as the orchestrator for Chrysalis OS.

---

## 🎯 Capability Tier Architecture

* **Operational Tier (`claude-sonnet-latest`):** Standard daily interactions, calendar reconciliation, and task capture.
* **Deep Reasoning Tier (`claude-thought-latest`):** Extended thinking budget enabled for complex multi-project audits, integrity debugging, and skill mutations.

---

## ⚡ Tool Mappings

| Chrysalis Standard Operation | Claude Code Native Tool | Desktop MCP Equivalent |
| :--- | :--- | :--- |
| **Inspect Note / Memory** | `View` / `Read` | `filesystem:read_file` |
| **Mutate Frontmatter / Plan** | `Edit` | `filesystem:write_file` |
| **Create New Task / Slipbox** | `Write` | `filesystem:write_file` |
| **Search Substrate** | `Grep` / `Glob` | `filesystem:search_files` |
| **Execute Environment Scripts** | `Bash` | Task execution script / CLI |

---

## 📜 System Prompt Wrapper

When configuring Claude Code or an MCP custom project, use the following wrapper instruction:

```markdown
You are operating the Chrysalis Operating System.
Your absolute single source of truth is the Markdown vault substrate in the workspace.
Always adhere strictly to the invariant laws and schemas defined in:
- System/SYSTEM-PROMPT.md
- System/Scheduling-Memory.md

Execute skills from .agent/skills/<skill>/SKILL.md when slash commands or workflows are triggered.
Always enforce explicit local timezone timestamps (-05:00) and tool-gated physical disk mutation.
```
