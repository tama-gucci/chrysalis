# Pi package compatibility

chrysalis uses Pi 1.2.0 or later in major version 1 and Node 22.19.0 or later.
The tested host is Pi 1.2.0 on Linux ARM64 in Windows WSL. Other versions and native
Windows/macOS remain untested. Add-ons can require a newer Node version.

## Ownership and permission boundary

Pi owns its default MCP, codemode and tool-search extensions, their commands and configuration.
chrysalis registers only its source server and capabilities. Keep the built-ins enabled.
No exclusions, custom launcher or duplicate initialization is required for an installed package.
Existing user MCP configuration is loaded by Pi. A same-name user override of chrysalis_sources
is visible in /mcp and fails chrysalis's exact server/configuration gate.

Model calls use one policy, whether direct or nested through ctx.executeTool:

| Operation                                                 | Authority                                                                                     |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Provider registration, native quota/UI commands and hooks | Ordinary trusted Pi extension features; no model-tool grant                                   |
| Pi-owned orchestration with public reachesTools metadata  | May discover/orchestrate; every reached tool is checked again                                 |
| chrysalis source tools                                    | Exact server name, owner, launch configuration, namespace, callable exposure and input schema |
| chrysalis capabilities                                    | Exact package registration and enabled native capability                                      |
| External read-only tool                                   | Explicit native grant for the exact effective definition and origin                           |
| Other external action                                     | Exact native scope grant, then native confirmation of each call and its complete input        |
| Unknown or changed tool                                   | Scoped denial with a native review remedy                                                     |
| Hidden tool                                               | Native Pi exposure/resource configuration first, then exact scope review                      |
| Selected workspace work                                   | Existing isolated executor and native-selected workspace                                      |
| Authoritative vault changes                               | Saved proposal, per-note vetting, final native approval, raw revisions and apply              |

Visibility is not permission. MCP codemode tools may be reported as deferred by Pi.
Annotations are unverified hints; a friendly name, readOnlyHint or absent metadata grants nothing.
Native questionnaire answers, provider results, recalled text and external documents cannot approve.
Reserved package tools cannot be replaced by an external grant. Grants are checked on every call,
including after late registration, reload, changed load order, revocation or definition changes.

Use /chrysalis tools review <exact-tool-name> for a new external tool. Review the entire extension
and its effects before attesting that it is read-only. The other grant mode requires native review
for each external action. Neither mode permits direct authoritative vault mutation. Literal references
to the selected vault, package or private state are refused. These input checks do not certify arbitrary
code or interpret encoded commands: the native grant trusts the reviewed implementation's external scope.
Configured MCP files are fingerprinted through the documented agent/trusted-project locations because
Pi 1.2.0 exposes extension registrations, not the complete effective-server catalog. Any file change
requires /reload and re-review of external MCP grants. A configured chrysalis namespace collision
is denied even when its tool schema matches. This conservative check does not prove resolved
environment/command substitutions, executable bytes or native in-memory transport state.
User-configured MCP tools remain available; they need their own grant and are never trusted merely
because builtin:mcp registered them. Re-review a server/configuration change.

Grants live in the existing private host-addons.json policy (version 2). MCP grants additionally bind configuration-file identities and namespace-matching extension registrations.
Shared Pi-owned MCP resource tools have no namespace; their grants conservatively bind all server
registrations/configuration and retain native review for external actions.
The digest includes name,
description, schema, prompt guidance, exposure, namespace, annotations, registration source and
reachesTools implementation. Version 1 grants remain readable with their historical identity checks;
adding grants requires a separately reviewed version 2 policy. No migration silently widens authority.
Use pi config and package resource filters to resolve conflicts; do not reset every active tool.

Native Pi extensions, hooks, commands and provider code share the host process's OS permissions.
A tool hook cannot prevent their direct filesystem access or malicious behavior. The execution runner
isolates its own model-directed workspace tools only. Stronger whole-process containment needs a
separate platform boundary; this refactor adds no container or separate-account prerequisite.
Pi codemode's non-chat model helpers follow Pi's provider runtime. There is no per-helper tool_call
event, so chrysalis does not claim its tool grants govern those calls or all provider billing.

## Generic provider propagation

Install a provider as an ordinary independent Pi package. Use Pi's native login and main-model
selection; use /chrysalis models to choose authenticated chat models separately for memory and
specialist roles. The picker uses the public model registry without package-name filters.

All background streams use the parent's public modelRegistry.streamSimple runtime. Memory calls it
directly. A specialist process receives one fixed, bounded local stream route to that same runtime,
not provider source, credentials or a reconstructed provider catalog. Public registerProvider in
the child exposes only that selected chat model. The endpoint is private, ephemeral, turn-limited,
cancellable and removed on completion, timeout, interruption or parent shutdown. Child tool/role,
workspace, lease and approval restrictions remain. Provider tools and hooks are never imported into
children. This small transport exists because Pi's public SDK does not serialize a parent provider
runtime across process boundaries. It contains no provider-specific account/failover implementation.

Missing authentication, unavailable/changed routes and stream failures stop that work. No model or
billing route is silently substituted. The provider package itself is trusted host code; its internal
retry/account behavior belongs to that package. Do not switch credentials concurrently with workers.
Registration and an offline synthetic stream establish routing, not authenticated service access,
provider quality, live quota accuracy or permission to send personal data.

## Compatibility matrix

| Component / feature                                         | Classification                                   | Acceptance boundary                                                                                                                           |
| ----------------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Pi 1.2.0 built-in MCP/codemode with chrysalis               | Verified compatible                              | Synthetic SDK/installed-archive startup and calls; no built-in exclusions                                                                     |
| Existing user MCP servers                                   | Supported with documented configuration          | Pi loads configuration; each external tool requires its own scoped native grant                                                               |
| Exact chrysalis server override or duplicate resource names | Incompatible feature                             | Fail closed; resolve the conflict with pi config or manifest/settings filters                                                                 |
| pi-quotas 0.5.0                                             | Verified installation/registration compatibility | All six original resources load; native quota/token commands retained. Live authenticated quotas remain untested                              |
| pi-antigravity 0.10.0                                       | Verified installation/registration compatibility | All three original resources and eight chat catalog entries load. Google sign-in/live inference/background service acceptance remain untested |
| Public provider runtime for main/memory/specialists         | Verified offline routing                         | Synthetic registered provider and child stream; no live service claim                                                                         |
| Competing observational-memory engines                      | Incompatible feature together                    | Choose one memory engine through ordinary resource selection                                                                                  |
| Direct authoritative-vault writer                           | Incompatible feature                             | Use proposal/native approval/CAS instead                                                                                                      |
| Other Pi versions, native Windows/macOS                     | Untested                                         | Declared ranges are not platform/version acceptance                                                                                           |

pi-antigravity 0.10.0 resolves Undici 8.12.1, which requires Node >=22.19. Pi 1.2.0 also declares that floor, so chrysalis now requires Node >=22.19.0 for its supported Pi adapter. This minimum is not attributed solely to the add-on. Use a runtime satisfying the entire selected loadout.
Do not install local duplicate copies of globally installed packages. Apply filters to the existing
package declaration, preserving unrelated resources/settings. Resource filters select extension files;
they cannot split a provider registration from commands/hooks in the same file. Native commands in
pi-antigravity's provider entry therefore remain trusted host commands; chrysalis does not claim a
provider-only resource filter can remove them.

## Diagnostics and author rulebook

Run /chrysalis compatibility to inspect effective tool origins, namespaces, exposure, definition
digests, scoped authority and registered source ownership. Use /mcp for effective user/server
overrides and Pi's startup diagnostics for duplicate tools/commands; pi config shows effective
package resources. Do not copy a credential-bearing configuration into chat. Remedies should change
only the conflicting resource. Installation never activates a source, reads personal files or
creates/rewrites a vault.

Authors should use namespaced names, activation that preserves unrelated tools, public model/provider APIs and declared
runtime requirements. Avoid replacing shared built-ins, colliding commands, broad active-tool resets,
competing memory engines, direct vault writes, credential races, hidden state in package/source and
private imports or account adapters. Keep extension resources separable in manifests where practical.
Avoid assuming an SDK metadata object is an isolation proof.

See official [extensions](https://pi.dev/docs/latest/extensions),
[packages](https://pi.dev/docs/latest/packages), [MCP](https://pi.dev/docs/latest/mcp),
[codemode](https://pi.dev/docs/latest/codemode) and [host trust](https://pi.dev/docs/latest/security).
