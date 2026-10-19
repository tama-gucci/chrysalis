# Setup

Use Node 22.19.0 or later with ICU and Pi in the supported range >=1.2.0 <2.
Pi 1.2.0 is the tested SDK/host. Other versions in the declared range are untested.
TaskNotes requires Obsidian 1.12.2 or later. Independent add-ons may need a newer Node runtime;
Pi 1.2.0 itself requires Node >=22.19.0. pi-antigravity's resolved Undici 8.12.1 independently has that requirement.

Install chrysalis as an ordinary Pi package. Leave default MCP and codemode enabled. Pi owns these
built-ins and the user's MCP configuration; chrysalis registers only its source server/capabilities.
Use pi config for genuine resource conflicts and /chrysalis compatibility to inspect effective
origins and scoped permissions. Unrelated provider/UI resources remain independent. No custom
launcher or built-in exclusion is required. See the [compatibility rulebook](compatibility.md).

PI_CODING_AGENT_DIR may select an external Pi settings/auth/session directory. Keep existing login,
settings and conversations when updating a package. Authentication belongs in the native browser
or terminal; never paste tokens, password exports or OAuth callback URLs into chat.

For a reviewed private archive, install with ordinary Pi package management:

~~~text
pi install --local npm:chrysalis@file:/absolute/path/chrysalis-2.0.0.tgz
~~~

This uses the supplied archive and does not publish or fetch an unrelated registry release with
the same bare name. Preserve other package declarations and authentication. For a published
reviewed source revision, use Git transport:

Install a reviewed Git revision through Pi:

```text
pi install git:github.com/tama-gucci/chrysalis@<reviewed-commit-or-tag>
```

Replace the placeholder with a revision you reviewed. Pi installs production dependencies for managed
Git/npm packages; no user build or separate interpreter is required. A bare local source folder is
not dependency-ready: Pi references local directories without installing dependencies. For local
testing, first copy public source into an external workspace, install its production dependencies
there, then use `pi install <absolute-prepared-package-folder>`. Never put node_modules in the source
checkout. npm registry installation requires an actually published registry release; source on GitHub
does not establish that publication. See [Pi packages](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md).

Run `/chrysalis onboard` interactively. Choose a vault name (default `chrysalis`) and parent folder. The location prompt accepts
phrases such as `my documents folder`, `my home folder`, `desktop` and `downloads`, or an
absolute path. Matching existing folders appear as you type; use Up/Down to highlight a suggestion
and Tab to complete it. Enter confirms the resolved existing parent, and Escape cancels. The exact
vault path appears in the setup review before any creation. Windows uses known folders, WSL maps
Windows known folders, macOS uses standard user folders, and Linux honors XDG user-directory settings
and `XDG_CONFIG_HOME`. Valid redirected Windows folders are respected; if the native Documents
lookup is unavailable, an existing standard profile Documents folder is offered instead.
An unavailable known folder or an unrecognized phrase requires an explicit existing path. The command detects the computer timezone and prepares TaskNotes 4.13.8, Dataview 0.5.68,
schemas, views and empty state. Review the destination, minimum Obsidian version, settings and hashes
before approval. Declining leaves the target unchanged; interrupted approved setup resumes its exact scope.

Use `/chrysalis onboard --restart` to replace an unapproved setup. Add `--zone <IANA>` for an explicit
initial zone correction. An approved/interrupted setup retains its original scope; after creation use
`/chrysalis timezone --zone <IANA>` for a reviewed change. Creation/resumption hands the conversation
to goal discovery; on an existing selected vault, onboard starts that conversation without reinstalling.
Approving a previously saved setup directly applies it; run onboard afterward to begin goal discovery.

Goal onboarding follows a small decision map, asking one to three ready independent questions
per round and retaining partial answers or deferrals. You confirm a recap before adopted records
are drafted; file and per-note approval remain separate. Reviewed checkpoints let the conversation
resume without repeating settled questions. See the
[decision procedure](../skills/chrysalis-knowledge/references/onboarding-decisions.md).

The conversation first offers optional life documents. You may skip, defer or use
`/chrysalis documents` to choose a dedicated folder containing portfolios, resumes, academic
records, bills or other context. Review the inventory and exact selected copies separately.
Supported extracted evidence informs chosen roadmap goals, possible projects and atomic notes;
those records need their own approval. See the [document procedure](../skills/chrysalis-knowledge/references/life-documents.md)
for format limits and recovery. Existing selected vaults can use this command later too.

Open the folder through **Open folder as vault** in Obsidian, enable community plugins when prompted,
then open Dashboard. Generation works offline after package/dependency installation. Obsidian
installation and account configuration remain user choices.

The external chrysalis state defaults to `%LOCALAPPDATA%/chrysalis` on Windows (with a home-directory
fallback), or `$XDG_STATE_HOME/chrysalis` / `$HOME/.local/state/chrysalis` elsewhere.
`CHRYSALIS_STATE_ROOT` selects another absolute state directory. One state profile selects one vault;
`CHRYSALIS_VAULT_PATH` explicitly selects an existing initialized vault. Package, vault and state
must be disjoint. Vaults cannot sit inside a Git repository/package ancestry or use symlinks/junctions.
See [storage](storage.md). Profiles, credentials, locks, approvals and recovery stay outside source.

| Operator command                                 | Result                                                                             |
| ------------------------------------------------ | ---------------------------------------------------------------------------------- |
| /chrysalis onboard                               | Prepared folder creation/recovery or goal onboarding                               |
| /chrysalis onboard --restart                     | Replace unapproved setup and choose details again                                  |
| /chrysalis compatibility                        | Effective registrations and scoped external-tool authority                        |
| /chrysalis tools review &lt;name&gt;             | Native review of an external tool scope                                             |
| /chrysalis status                                | Selected root and pending setup; no integrity/UI check                             |
| /chrysalis documents                             | Select/review an optional external life-document folder                            |
| /chrysalis documents --status                    | Inspect current folder authorization without scanning                              |
| /chrysalis approve &lt;digest&gt;                | Review complete saved records/settings and approve/apply                           |
| /chrysalis repair                                | Restore eligible missing owned resources; preserve edits                           |
| /chrysalis timezone                              | Fresh computer observation and reviewed change if needed                           |
| /chrysalis timezone --status                     | Stored configured zone and last observation; no fresh detection                    |
| /chrysalis timezone --zone Europe/Paris          | Review an explicit named zone                                                      |
| /chrysalis integrations setup                    | Optional guided native provider authorization and binding approval                 |
| /chrysalis integrations status                   | Redacted configuration and last verification; fresh authentication remains unknown |
| /chrysalis integrations review &lt;alias&gt;     | Native evidence display without record writes                                      |
| /chrysalis integrations reconnect &lt;alias&gt;  | Fresh credentials, access test and activation review                               |
| /chrysalis integrations disconnect &lt;alias&gt; | Disable locally and dispose of unshared protected credentials                      |

Update the computer timezone after a move before rerunning detection. Existing records and schedules
are preserved. Repair uses original setup hashes; it is not an upgrade/reset and never resets Memory
or the roadmap. Noninteractive execution cannot supply approval; the life tool cannot approve itself.

Source setup can be skipped/deferred during onboarding or run later. No source connects simply
because its module is installed. Read [source setup](integrations.md) for scope, billing,
protected-storage requirements and Health/Maps native-only limitations.

## Optional assistant setup

First successful vault onboarding offers `/chrysalis assistant-setup`; Later preserves the basic
workflow. Choose authenticated background model routes and optional capabilities, then use `/reload`.
Use `/chrysalis runner-setup` inside Linux tmux for the reviewed minimal Debian/Ubuntu prerequisites,
then `/chrysalis workspace`. Planning and vault review do not require the execution runner.
Browser/media setup currently requires accepted Linux Node 24 and downloads only after native
permission. Gemini account/video verification remains deferred. See [commands and safeguards](assistant.md).

For a live source checkout, install exact production dependencies in a separate private prefix.
A managed launcher sets CHRYSALIS_DEPENDENCIES_ROOT and CHRYSALIS_PI_ROOT, supplies the package
`src/platforms/dependencies.mjs` through Node `--import`, and uses the corresponding NODE_PATH for
Pi's TypeScript extension loader. The Pi root is the installed coding-agent package, not its auth
directory. This does not copy personal files into source; ordinary Pi-managed npm/Git installation
uses normal dependency resolution. Keep the previous launcher/dependency identity for rollback.

## Optional saved-password import

Onboarding explicitly offers a private CSV/JSON password inbox, with Later/Skip. Use
`/chrysalis passwords setup`, then place an export in that folder and run
`/chrysalis passwords import`. Native import review precedes encrypted append/update; it does not
copy credentials into Obsidian or enable a password-manager sync. Read [formats and browser use](passwords.md).
