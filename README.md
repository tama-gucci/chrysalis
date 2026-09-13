# Chrysalis

Chrysalis is a local-first framework for connecting reference knowledge, project priorities, and daily work. Markdown notes with YAML frontmatter are the source of truth. AI agents execute the operational runbooks; Obsidian and the Android prototype provide interfaces to those files.

The workflow has three stages: capture material, organize it into notes and tasks, and plan or complete the work. Planning uses cognitive modality, energy, focus blocks, and decompression buffers. These are configurable workflow rules, not guarantees about human performance.

## Start here

- [Architecture and folder ownership](ARCHITECTURE.md)
- [Implemented capabilities and remaining work](STATUS.md)
- [Develop while using Chrysalis](Development/README.md)
- [Runtime rules](System/Runtime-Constitution.md)
- [Master constitution](AGENTS.md)

## Two installations, one framework source

Keep `vault-git/` as the editable source repository and `vault/` as the personal daily-use installation. Tests use temporary synthetic vaults. Runtime framework files are deployed snapshots, not a second source tree to maintain manually. Personal notes and settings stay in the runtime vault.

The existing layout is supported: `System/`, `Projects/`, and `Slipbox/` are at the vault root; tasks, archives, daily notes, views, and incoming files live under `chrysalis/`. A fully encapsulated layout is optional, not a prerequisite. Do not move personal folders merely to match a diagram.

## Local development and deployment

From `vault-git/`:

```powershell
python -m unittest discover -t . -s tests
python update.py --source . --target ../vault --dry-run
python update.py --source . --target ../vault
python System/scripts/doctor.py --vault ../vault --read-only
```

Deployment previews files, backs up replaced files under the runtime's `.chrysalis/deployments/`, and records content hashes. Subsequent deployments stop if managed runtime files have been edited locally. Personal tasks, archives, project content, notes, memory, and plugin settings are excluded.

```powershell
python update.py --target ../vault --rollback --dry-run
python update.py --target ../vault --rollback
```

Optional `--plugins` includes approved plugin binaries, never `data.json`. Restart Obsidian after a plugin binary update. Enable Dataview in the selected vault to render [Dashboard.md](Dashboard.md).

## Applications

- [Android prototype](apps/mobile/README.md): local capture, task persistence, and schedule preview.
- [Ambient gateway](apps/gateway/README.md): optional transport to an external Antigravity installation.
- Obsidian plugin bundles are vendored build artifacts. Their complete source is not present here; do not treat editing a minified bundle as plugin development.

Calendar ingestion is provided by `System/scripts/fetch_ical.py`. Native calendar export, authenticated mobile Drive sync, direct AI inference, and the dedicated watch interface are unfinished; see [STATUS.md](STATUS.md).

## Privacy

The repository uses a default-deny `.gitignore` and a pre-commit PII scanner. Keep live state and deployment backups outside Git. Passing the scanner is a useful check, not a blanket certification of all possible personal data.

## License

See [LICENSE](LICENSE).
