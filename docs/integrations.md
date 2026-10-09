# Optional sources

Run `/chrysalis integrations setup` in interactive Pi. Onboarding offers this walkthrough;
skipping it leaves the vault fully usable. You can return later. Setup explains the selected
provider's outgoing data, read scope, model disclosure and costs before asking for credentials.
Credentials belong only in native controls or a downloaded credential file outside the package,
vault and execution profile. Never paste them into chat.

The walkthrough chooses a lowercase instance alias, account alias and Cloud project. Tasks and
Health import a downloaded OAuth client JSON and authorize in the system browser with PKCE and
a state-checked local callback. Tasks supports a Desktop client. Web clients require a registered
fixed `http://127.0.0.1:<port>/callback` URI in their downloaded JSON, with that port available.
Health requires a Web client, an already eligible enabled project and an account linked in the
Google Health mobile app. New-project Health onboarding is currently paused. Provider/client
eligibility and the live callback still need authenticated acceptance.

Google Maps uses a masked native API-key control. Enable Places API (New) and Routes API in your
own billable project; restrict the key to those APIs and appropriate application restrictions.
The walkthrough performs a small billable location query only after consent. A key cannot safely
be embedded in shared vault settings. Platform secret stores must be available: Windows uses
CurrentUser DPAPI, macOS uses Keychain, and Linux requires Secret Service's `secret-tool`.
There is no plaintext credential fallback. Only Windows synthetic protected-storage acceptance
has been exercised; other platforms remain unverified.

Setup tests access, lets you choose one Tasks inbox, and displays the complete nonsecret activation
and Memory post-image for approval. A matching external native authorization digest and approved
Memory binding are both required. Installation, a config edit or an old verification timestamp
does not establish current authentication. If activation application is interrupted, inspect its
saved proposal receipt and resume exact approval/application; reconnect if its binding changed.

```text
/chrysalis integrations status
/chrysalis integrations review <alias>
/chrysalis integrations reconnect <alias>
/chrysalis integrations disconnect <alias>
```

Reconnect performs the walkthrough again and requires fresh activation approval. Local disconnect
disables reads and disposes of an unshared protected credential. It leaves vault tasks and notes
alone and does not revoke Google access remotely. Use Google Account access controls for remote
revocation, after reviewing other clients sharing that account/Cloud project. Independent remote
revocation needs separate projects; separate client IDs in one project are insufficient.

Refresh and disposal share a credential lock. Reconnect acquires it before replacing the previous
profile. If disconnect reports `credential_cleanup_incomplete_reads_disabled_retry_disconnect`,
reads are already disabled but disposal is incomplete: wait for the protected backend or refresh
to finish, then repeat disconnect for the same alias. Success is reported only after cleanup.
Malformed credential files produce fixed errors without displaying their contents.

## Tasks capture

Only `tasks.readonly` plus standard account identity is requested. TaskNotes remains the sole
task manager and Calendar writer. The first page contains titles, status, date-only due dates
and revisions, without notes. Select at most 20 IDs to obtain detailed capture envelopes.
Account subject hashes, list IDs and item IDs define capture identity. Repeated accepted captures
use the existing reconciliation logic. Reads do not mark items imported or delete/complete them
in Google Tasks. Missing/deleted items, hierarchy and provider links are explicit omissions;
local completion, schedules, Calendar IDs, sessions and user edits survive reconciliation.
The final vault mutation still needs exact native approval and individual vetting of new notes.

## Health and travel evidence

Health reads only sleep and linked-account identity. Native review shows the latest processed
main sleep, date-correct vault timezone, source offsets, coverage and a baseline only when enough
valid observations exist. Missing, unprocessed, stale or incomplete observations remain explicit.
There is no readiness score or medical interpretation. Device evidence never overrides the user's
wake/energy replies or automatically adjusts learned scheduling multipliers.

Maps native review resolves a place or estimates selected route pairs, with Google Maps attribution,
mode, time context and partial failures. An ambiguous place needs user selection. Travel duration
remains separate from task `timeEstimate`; the user chooses a planning allowance independently.
Neither Health metrics nor Maps content enter model results, codemode store, proposals, vault
Markdown or Pi transcripts. Native evidence stays in memory. Their MCP tools return non-content
readiness and a native review command, so automatic Health/Maps enrichment through codemode is
deliberately unavailable. Broader disclosure/retention requires a separately verified policy and
storage design. Current native display/account behavior still needs live acceptance.

## Pi codemode

The package reuses Pi's MCP and codemode extensions with model helpers disabled. It registers a
package-owned stdio namespace `mcp__chrysalis_sources` with six strict read-only tools. The life
session ignores file-configured MCP servers and admits only the expected package registration,
origin and input schemas. Your global Pi settings are unchanged. General executors, arbitrary
reads and unrelated MCP tools remain blocked, including nested calls. Use a separate development
session for broader tools. This gate is not an OS sandbox.

Each provider response is bounded to 1 MiB; each provider request times out after 10 seconds.
The shared HTTP transport limits concurrency to four per process. Source tool calls have a
30-second deadline, pages are bounded to 100 Tasks items or 25 Health sessions, and the private
profile permits 100 provider requests per instance per UTC day. Failed/billable attempts count;
these limits are not a dollar-cost guarantee. Authentication requests are separately bounded.
No automatic retry loop runs. Budget state and protected credentials remain outside the vault.

Inspect `isError` before reducing MCP `structuredContent`. Preserve provider status, coverage,
pagination, omitted IDs and provenance; reduced output must not silently claim a complete inbox.
Use the [codemode recipes](../skills/chrysalis-integrations/references/codemode.md).
Token benefit depends on selected data and script/discovery overhead; measurements use estimated
context size, not a guarantee of provider-billed tokens.

Drive/local originals, supplied Tasks snapshots, map projections and normalized Calendar
observations remain optional core adapters. No Drive OAuth or Calendar connection is bundled.
See [provider guidance](../skills/chrysalis-integrations/references/providers.md),
[capability contract](../contracts/integration-capabilities.contract.md) and
[implementation status](../STATUS.md).
