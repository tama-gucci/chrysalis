---
type: orchestrator_adapter_spec
id: chrysalis-orchestrator-local-llm
name: "Local LLM / Ollama Orchestrator Adapter"
orchestrator_platform: "local_llm"
status: reference
version: 1.1.0
last_updated: "2026-09-02T13:42:00-05:00"

capability_tiers:
  operational_tier:
    alias: "qwen2.5-coder:latest"
    pinned_tested: "qwen2.5-coder:32b"
    role: "Local daily operational loops, frontmatter mutations, and scheduling"
  deep_reasoning_tier:
    alias: "deepseek-r1:latest"
    pinned_tested: "deepseek-r1:70b"
    role: "Local deep reasoning, RSI friction analysis, and diagnostic validation"
---

# 🦙 Local LLM / Ollama Orchestrator Adapter (Reference Spec)

This document specifies the integration configuration, capability tier routing, tool calling patterns, and Nexus settings when using **Local Open-Weight Models** (via Ollama, LM Studio, or vLLM) as the orchestrator for Chrysalis OS.

---

## 🎯 Capability Tier Architecture

* **Operational Tier (`qwen2.5-coder:latest` / `32b`):** Fast, accurate tool calling, robust JSON/YAML schema handling, and reliable text replacement generation.
* **Deep Reasoning Tier (`deepseek-r1:latest` / `70b`):** Extended chain-of-thought for deep RSI audits and multi-file code refactors.

---

## 🔌 Obsidian Nexus Configuration (Ollama)

To run a local model within Obsidian via the Nexus plugin:

```json
{
  "llmProviders": {
    "ollama": {
      "apiKey": "http://127.0.0.1:11434",
      "enabled": true,
      "ollamaModel": "qwen2.5-coder:32b"
    }
  },
  "defaultModel": {
    "provider": "ollama",
    "model": "qwen2.5-coder:32b"
  }
}
```

---

## ⚙️ Execution Requirements

* **Context Window:** Minimum 32k tokens recommended (64k+ preferred) to ingest `Life-Roadmap.md`, `Scheduling-Memory.md`, and relevant `TaskNotes/Tasks/*.md` without truncation.
* **Structured Output / Tool Calling Support:** Model must support native function calling or robust JSON schema compliance to execute disk mutations reliably.
