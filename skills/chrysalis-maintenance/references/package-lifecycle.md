# Package and resources

Follow [setup](../../../docs/setup.md) for a reviewed Pi-managed Git installation. Pi installs
dependencies for Git/npm sources; a local directory must already have its dependencies in an
external copy. Keep package, vault and local state disjoint. Native `/chrysalis onboard` prepares
the folder and exact review; installation never launches Obsidian or connects accounts.

`/chrysalis repair` restores only missing eligible files whose current package bytes agree with
the original setup receipt. It preserves edits and excludes Memory, the roadmap and identity.
It is not a resource upgrade/reset. Changed releases may need separately reviewed resource
migration; no general vault-upgrade command is implemented.

Use `pi list`, `pi update --extensions` or `pi update <source>` to inspect/reconcile managed code.
A pinned Git revision remains pinned; select a newly reviewed source revision explicitly to change
it. Code rollback selects an earlier reviewed revision. `pi remove <source>` removes package code,
not the separate vault or chrysalis state. Reload/restart Pi after changing installed extensions.
Run doctor and representative workflows after code changes. Package updates do not silently
rewrite existing plugin settings/templates or migrate another package's memory.
