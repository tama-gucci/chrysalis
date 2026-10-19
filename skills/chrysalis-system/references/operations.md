# Installed-system operations

The native outcome scope includes the selected configuration, exact NixOS host and backend identity. Work within it. Do not widen the target or substitute another tool with a matching name.

Use the pinned nix-agent MCP tools:
- build starts or polls jobs. Save the job identity and poll until terminal status.
- diff builds synchronously and compares against the running closure. A successful fresh result with a store path supplies activation evidence.
- switch activates. A degraded result means new services failed; an interrupted call needs observation before retry.
- generations lists recovery choices. Generation changes require a separately bound native recovery target.
- eval_config and locate_option inspect the actual configuration.
- check lint may return findings despite status ok; check dry-build is only a plan.

Do not change source during an in-flight build. If another editor changes it, finish the old job and build the new source. Complete a fresh diff before switch. Keep an available recovery generation.

Use chrysalis_system action=reconcile to observe actual state and project receipts to the selected vault. Do not treat a successful transport or profile update as proof of healthy activation.

A verified outcome remains available for verification until native close or a new outcome. Any edit invalidates prior build proof. Do not close or replace an outcome while its context tool has an active lease. A lost privileged response or ambiguous failure requires confirmed completion or a new boot before another mutation; closing the outcome does not clear that guard.
