# Engineering workflow

Read root instructions, architecture, status and handoff. Run the context script before edits.
Record branch/HEAD and dirty identities; preserve unrelated work. Keep one writer per checkout.
A concurrent reviewer works read-only against a frozen identity. Substantial changes require a
separate review invocation; the implementing invocation does not approve itself.

Keep fixtures, environments, logs, before-images and recovery outside source. Inspect hidden,
ignored and untracked files. Default-deny Git exclusions complement physical source privacy.
Use the complete retained suite and checker in `TESTING.md`; core contracts run without hosts,
then native adapters receive separate acceptance. Distinguish fixtures, real tool calls, model
conversations and authenticated account/UI checks.

Leave a concise sanitized handoff: date, role, branch/HEAD, changed scope, actual checks and
unresolved limits. Dirty files also need an external hash manifest; HEAD alone is insufficient.
Keep decisions in architecture and verification in status. Publish only within authorized scope.
