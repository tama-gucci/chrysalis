---
type: agent_workflow
id: workflow-08-continuation
version: "1.0.0"
stage: continuation
lifecycle_state_ref: CONTINUATION
requires_approval: false
inputs:
  - execution_metrics
  - diagnostics_list
outputs:
  - agent_action_output_json
---

# Workflow 08: Continuation & Envelope Serialization

## Objective
Format the standardized `AgentActionOutput` JSON envelope conforming to `contracts/agent-runtime.contract.md`, return execution status to caller, and close session cleanly.

## Envelope Structure:
```json
{
  "valid": true,
  "result": {
    "path": "chrysalis/Tasks/{YYYYMMDD}-{slug}.md",
    "revision": "a1b2c3d4...64hex",
    "mutations_executed": 3
  },
  "diagnostics": [],
  "revision": "a1b2c3d4...64hex"
}
```
