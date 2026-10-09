# Implementation status

Version 2.0.0 is a self-contained Pi package with a portable TypeScript/Node core, seven canonical
skill families and 36 reviewed vault operations. Onboarding prepares a user-named Obsidian vault
with pinned TaskNotes 4.13.8, Dataview 0.5.68 and automatic named-timezone setup. Original files
belong inside Attachments/Originals. Optional life-document selection/copies, chosen roadmap
work, knowledge compilation/search/lint and individual approval of every new atomic note are
implemented. Conversation uses scoped decisions, partial replies, skip/defer and recap confirmation;
model conversation quality remains a separate acceptance boundary.

The source integration implementation adds a bundled six-tool stdio MCP server,
shared provider service, native credential onboarding and upstream Pi codemode/MCP adapters.
Google Tasks is one-way read-only capture: metadata first, selected detail envelopes, account/list
identity and existing safe local reconciliation. Native activation requires matching external
profile and approved Memory bindings. Reconnect and local disconnect are native-only. Credentials
are OS-protected outside vault/source; Windows uses CurrentUser DPAPI. macOS Keychain and Linux
Secret Service paths are implemented but have not received platform acceptance.

Google Health reads linked identity and processed sleep for eligible existing projects. Google
Maps reads minimal selected place/route context with native attribution. Both display evidence in
an in-memory read-only component without external-editor export; neither returns provider content
to model/session/vault records. MCP and ordinary operations return native-review readiness only.
Manual wake/energy replies and independently selected travel allowances remain authoritative.
Health project availability, live OAuth/account/scopes, Maps billing/display and provider-required
privacy disclosures need separate user-controlled acceptance. No account was connected in this run.
See [source setup](docs/integrations.md) and [design](docs/integrations-implementation-plan.md).

Current isolated Windows acceptance uses synthetic data and Pi SDK 1.0.4:

- The complete 74-case suite passed on minimum Node 22.18.0 with no skips. A subsequent
  13-case provider delta verifies sanitized cleanup-failure reporting and retry.
- A production-only npm archive installation loads all seven skills, prepares a vault with
  networking disabled, passes doctor and reaches bundled stdio through codemode with Pi's
  replaceable built-ins present. The pinned package-resolved tsx loader supports installed
  TypeScript without a build step; transform caching is disabled. All nine flowcharts render.
- Production TypeScript checks pass. Tests cover approvals, per-note review, CAS/recovery,
  document scope/copies, provenance/fidelity, plugin contracts, timezone/DST and daily planning.
- Actual Pi reaches the production bundled stdio server through upstream codemode. Its model
  helpers are disabled. Nested arbitrary reads are denied; effective registration/schema/origin
  overrides fail closed. Source activation, masking, native display and protected storage have
  synthetic native-control acceptance, not physical terminal rendering or live account proof.
- Provider cases cover strict input/scope bounds, partial Tasks details, stable identity,
  credential reflection, omission/freshness, HTTP destinations/limits, lossless concurrent daily
  budgets, in-flight local disconnect and protected refresh rotation. OAuth loopback tests use
  synthetic token exchanges and no browser/account, proving state, PKCE and granted-scope checks.
- Separate frozen read-only review identified refresh/disposal and malformed-import diagnostic
  defects; both were corrected and accepted. Regression cases cover disconnect during refresh,
  reconnect during a credential write and secret-free native import notifications.
- Codemode measurements use the shared Tasks service with synthetic MCP-shaped wrappers and
  actual Pi orchestration. Reduced results retain equal coverage/provenance/failures. Pi's
  chars/4 estimator includes schema, discovery, script, calls and model-visible results;
  it is not billed-token measurement. See [measurement method](docs/integrations-benchmark.md).

Physical source privacy/resource validation passes with no findings, including ignored/untracked
content, public syntax, links and pinned asset checks. The operator removed the previously empty
formatter cache after automated deletion was blocked; the checker was not weakened. No personal
data was created in source. Reviewed implementation identities and publication evidence have
external SHA-256 manifests. Git publication does not establish an npm release, live account
acceptance or personal-vault adoption.

Physical Obsidian/community-plugin rendering, terminal interaction, live model conversations,
authenticated Google accounts, other operating systems/devices and OCR/vision remain unverified.
The supported Pi range is not a claim that every version was tested. Local CAS coordinates
cooperating writers and cannot provide a distributed transaction or eliminate every editor race.
