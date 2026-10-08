# chrysalis

chrysalis connects knowledge, projects and daily work in an Obsidian vault. Markdown notes are
authoritative. TaskNotes supplies task lists, calendars and timers; Pi reads the packaged
procedures and invokes one small Python domain core.

The Pi package exposes seven skill families and one `chrysalis_operation` tool. The tool reads,
drafts and applies separately approved proposals. Keep the private vault, installed package,
host profiles and execution state in separate explicitly selected locations.

Pi is the supported harness. The core, schemas and procedures remain independent of it;
future adapters can use the same versioned JSON operation contract.

- [Setup](docs/setup.md)
- [Daily use](docs/user-guide.md)
- [Architecture](ARCHITECTURE.md)
- [Verified capabilities and limits](STATUS.md)
- [Storage](docs/storage.md)

Capture, ingestion, project horizons, knowledge links, morning calibration, evening review,
four pause modes, diagnostics and onboarding use the same core. Providers are optional and
disabled until configured. Google Tasks is a read-only capture input; TaskNotes owns Calendar sync.

Originals live at `Attachments/Originals`, separate from evidence notes in `Sources`. Relative
links survive relocation. Bounded text/PDF extraction is available; image OCR and physical preview
require a suitable external reader.

Source contains synthetic examples and sanitized templates only. Keep private records,
credentials, caches, environments, learned skills and recovery assets outside it. Git exclusion
alone does not remove a file from disk.
