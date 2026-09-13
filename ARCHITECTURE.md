# Architecture and ownership

## Decision: retain separate runtime and development installations

Use Chrysalis in `vault/`; edit the reusable framework in `vault-git/`. This supports daily use while developing without exposing personal work to untested edits. The folder names are conventions, not hardcoded requirements.

| Location | Owner and purpose | Update policy |
| --- | --- | --- |
| `vault-git/` | Source code, schemas, templates, tests, runbooks | Edit and test here |
| `vault/` | Personal notes, state, Obsidian settings, installed framework | Deploy tested framework changes here |
| Temporary test vaults | Synthetic tasks and memory | Created and discarded by tests |
| `vault/.chrysalis/` | Private deployment history and backups | Managed by the updater; never commit |

Merging the two installations would make every source edit a live change and bring personal data next to routine Git operations. Symlinking runtime code to development has the same immediate-change problem. Controlled deployment provides a convenient local feedback loop without either tradeoff.

## Supported layout

```text
workspace/
  vault-git/                  source repository
    apps/mobile/             Flutter source and native Android bridges
    apps/gateway/            optional Python transport service
    System/scripts/          runtime utilities
    System/_templates/       sanitized memory templates
    .agent/skills/           runtime agent runbooks
    Development/             development rules and tooling
    tests/                   synthetic integration and unit tests
  vault/                     personal Obsidian vault
    AGENTS.md                installed operational rules
    Dashboard.md             Dataview command center
    System/                  private memory plus installed utilities/templates
    Projects/                personal roadmaps
    Slipbox/                 personal reference notes
    chrysalis/
      Tasks/ Archive/ Daily/ Inbox/ Views/ Workflows/ _templates/
    .obsidian/               installed plugins and personal settings
    .chrysalis/              deployment records and backups
```

The existing split layout is the default. Fully encapsulated installations place System, Projects, Slipbox, and the dashboard under `chrysalis/`. Runtime utilities support both. Do not retain independent duplicate copies of the same resource: ambiguous paths should be reconciled before mutation. Migration is a separate, explicit operation; normal deployment never relocates personal data.

## Selecting a vault

Python tools take an explicit vault option or `CHRYSALIS_VAULT_PATH`. Without one, they operate on their own installation. They must never infer that a similarly named sibling folder is the desired personal vault. `CHRYSALIS_MEMORY_PATH` can explicitly select a memory file for calendar imports.

Use `--vault` with doctor and calendar tools; bootstrap retains `--vault-root`. Run graph linking with its `--vault` option. Mobile accepts an explicit absolute `CHRYSALIS_VAULT_PATH` in desktop development; Android defaults to persistent app documents. That Android folder is local until a synchronization integration is configured and implemented.

## Deployment boundary

`update.py` owns the distribution allowlist, also consumed by starter export. It copies framework files, preserves private state, stages backups before replacement, detects changed managed files, and permits latest-snapshot rollback. It never mirrors arbitrary directories or deletes obsolete personal files.

Plugin binaries are optional. Plugin settings and secrets never cross between installations. The allowlisted legacy bundles are build artifacts, not a maintained plugin source project. Compiled mobile applications and the optional gateway process have their own build/run lifecycle; deploying vault files does not install a phone app or restart a service.

Deployment snapshots protect framework updates; they are not backups of all personal notes. Keep the usual independent vault backup. Pause framework-editing agents during deployment. Google Drive is a file transport, not a cross-device transaction lock.

## Execution boundary

A queued message is not execution, and an AI response is not proof of disk mutation. Missing backends return unavailable. Gateway simulation is explicitly enabled for tests and visibly labeled. Native cloud/edge AI, calendar export, and watch capabilities must not be advertised as working before they are connected and exercised.
