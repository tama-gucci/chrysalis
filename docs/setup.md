# Setup

Choose separate locations for the installed package, private vault, external execution state,
Python environment and host profile. Each selected vault and configurable life profile is named
`chrysalis`. On Windows a case-only spelling does not create a different directory.

Use Python 3.12 or later, including native Windows junction detection. Create a virtual environment outside source/vault and install
`requirements.txt`. Verify its real launch architecture before adding native dependencies.
Replace symbolic paths in these operator commands with explicitly selected absolute locations:

```text
python -I -B <source>/run.py package install --target <packages>/chrysalis
python -I -B <source>/run.py package install --target <packages>/chrysalis --apply
python -I -B <packages>/chrysalis/run.py init --vault <selected-parent>/chrysalis --timezone America/Chicago
```

Installation previews owned files and collisions. Initialization requires an empty directory.
It creates blank operational state, schemas, templates, originals storage and views; onboarding
supplies chosen goals. It does not adopt or reset an existing vault.

Set `CHRYSALIS_VAULT_PATH`, `CHRYSALIS_STATE_ROOT` and `CHRYSALIS_PYTHON` in the
private Pi profile environment. State must be absolute and external
to both vault and package.

## Pi

Use upstream `pi install <packages>/chrysalis`, or list that absolute local package in the
private profile's `settings.json` packages field. Choose an external `PI_CODING_AGENT_DIR`
whose final directory is `chrysalis`. The package manifest exposes canonical skills and the
typed extension. Invoke `/skill:chrysalis-daily` or another discovered family.
The life profile permits `read` for canonical skill Markdown and `chrysalis_operation`;
it denies arbitrary reads, writers and executors.

Pi's local install registers the selected package path; it does not copy that directory or
create the Python environment. Keep the installed release available and launch Pi with the
same private environment settings. A development session should not load this life package.
See the [upstream package contract](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md).

Memory packages are optional. Tested loader/native-store combinations are in `STATUS.md`;
full model learning and permission coexistence are unverified. The life policy does not grant
unknown memory or skill-management tools. Review additions narrowly and keep stores external.
A capped Markdown snapshot is not a complete database export.

## Obsidian and approval

Open the explicitly selected vault in Obsidian. Configure TaskNotes tasks at `TaskNotes/Tasks`,
archive at `TaskNotes/Archive`, daily notes at `Daily` and fields according to `_types/task.md`.
Install plugins and settings privately; source includes no personal `.obsidian` configuration
or vendored binaries. See [daily use](user-guide.md).

After reviewing the exact proposal, the operator records approval separately:

```text
python -I -B <packages>/chrysalis/run.py approve --vault <selected-parent>/chrysalis --state <execution-state> --digest <reviewed-sha256> --evidence <approval-reference>
```

The agent then calls `apply` with that digest. Never expose operator commands through an
executor in the life profile. Setup does not activate jobs or external providers.
