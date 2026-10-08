# Development

Reusable code, schemas, procedures and synthetic tests belong here; personal vaults and host
state do not. Read [workflow](AGENT-WORKFLOW.md), [testing](TESTING.md) and [handoff](HANDOFF.md).
`agent_context.py show` reports bounded Git identities. `check.py` scans the full working tree
and checks maintained resources.

Put domain behavior in `chrysalis/` or `helpers/`; adapters only register/launch the shared
interface. Edit one canonical skill and verify Pi discovers and executes its route.
Future harnesses implement the versioned contract without changing domain behavior.
Keep optional transport tests independent of core correctness.
