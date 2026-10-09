# Current engineering handoff

Date: 2026-10-09. Role: modular read-only Pi source integrations and publication. Branch: main.
Implementation base: bb846fc60adae6f35cdbdf7baf5ed60695f0d901.
Run node Development/scripts/agent_context.mjs show for current dirty identity. All earlier
knowledge, document onboarding and decision-guidance changes were preserved. Source, user vault
and execution state remain separate; no personal runtime or account was accessed.

The package has one portable TypeScript core, seven skills and 36 reviewed vault operations.
New src/integrations modules own provider contracts, private profiles, bounded HTTP, OAuth and
Tasks/Health/Maps normalization. src/mcp/server.ts exposes six read-only tools. extensions/sources.ts
reuses upstream codemode/MCP with model helpers disabled, sparse on-demand declarations and exact
registration/origin/schema checks. File-configured servers are ignored only in this life session;
global settings are unchanged. The native integrations command coordinates consent, masked key/
external client import, access tests, exact Memory approval, reconnect/disconnect and native review.

Live Tasks captures pass metadata first and selected details to the existing ingestion proposal/
reconciliation implementation. Native authorization and approved Memory must match. General tools,
arbitrary reads, resources, model helpers and unrelated MCP calls stay outside the life profile.
Health/Maps provider content is native-only with no external-editor export or persisted observations.
New-project Health onboarding is paused; eligible access and Web client callbacks still need live
acceptance. Manual morning input and independent travel allowances remain the supported planning
path. Local disconnect does not invoke account/project-wide remote revocation.

A complete 74-case suite and subsequent 13-case provider delta passed on minimum Node 22.18.0;
the delta verifies sanitized cleanup-failure reporting and retry. Production TypeScript passes.
Actual SDK/stdio/codemode reachability and nested denial are proved with synthetic calls. Windows
DPAPI, native activation/cancel, credential reflection, PKCE/state/scope checks, provider bounds,
concurrent counters and protected refresh rotation have isolated fixture acceptance. The token
benchmark uses Pi's chars/4 estimator, equal selected results and in-process MCP-shaped wrappers;
its production stdio proof is separate. A production-only installed archive loads seven skills,
prepares a vault with networking disabled, passes doctor and reaches bundled stdio/codemode with
replaceable upstream built-ins present and model helpers disabled. The pinned tsx launch handles
installed TypeScript with package tsconfig and no transform cache. All nine flowcharts render.

Separate frozen read-only review found two credential lifecycle/diagnostic defects, corrected and
accepted in a focused second pass. Shared refresh/disposal locking prevents credential recreation;
reconnect locks before profile replacement. Invalid imports use fixed errors. Race/canary tests
cover refresh/disconnect, writer/reconnect and native notifications. Failed local disposal leaves
reads disabled and the credential identity retriable, with a fixed incomplete-cleanup message.

Dependencies, fixtures, logs, before-images, measurement and frozen manifests remain external.
The operator removed the previously empty formatter cache after automated removal was blocked.
The complete physical source checker now passes without exclusions or findings. Git publication
is recorded separately from actual Obsidian/terminal behavior, model conversations, other platforms,
authenticated accounts and personal adoption. Keep one source writer; future substantive changes
need separate frozen review. Machine-specific Pi packages, credentials and remote-access guides
belong outside reusable source.
