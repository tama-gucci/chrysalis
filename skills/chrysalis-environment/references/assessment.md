# Environment assessment
Ask only for missing node alias, intended use and IANA timezone. Use a neutral alias such as
station-node, never a hostname. Call `environment` with node, timezone, scope and optional storage_root.
The bounded collector observes OS, visible CPU/memory, selected hardware, interpreter pointer size,
PATH presence and storage capacity. It installs nothing and does not prove physical host identity,
emulation compatibility, GPU performance, model subscriptions or provider authentication. Report
unknown when running inside an uncertain shell/container. Do not dump config/env or token-bearing
plugin data. Inspect only plugin manifests and non-secret settings needed for the chosen workflow.
Save approved observations as a system_state environment_manifest under Environments/<node>.md
through propose/approval/apply. Preserve user annotations. Another device gets its own confirmed alias
and explicit roots; no synced active-device pointer. Reassess only relevant capability requirements.
