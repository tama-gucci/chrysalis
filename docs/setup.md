# Setup

Use Node 22.18 or later with ICU and Pi in the supported range `>=1.0.4 <2`.
SDK 1.0.4 is the tested host version; the whole supported range has not been individually tested.
The pinned TaskNotes release requires Obsidian 1.12.2 or later.

Use a dedicated Pi life profile. Set `PI_CODING_AGENT_DIR` to an absolute external profile directory
before installation and whenever launching this profile. This is Pi's supported configuration-directory
override, not a chrysalis command. Keep general development/research sessions separate: the extension
restricts life tools to chrysalis operations, canonical skill reads and gated source codemode.

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

Run `/chrysalis onboard` interactively. Choose a vault name (default `chrysalis`) and absolute parent
folder. The command detects the computer timezone and prepares TaskNotes 4.13.8, Dataview 0.5.68,
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
