# chrysalis

A self-contained Pi package for goals, projects, knowledge and daily work in a private Markdown vault. TaskNotes supplies the Obsidian task interface; Dataview supplies declarative dashboards.

Follow [setup](docs/setup.md) to install a reviewed Git revision through Pi, then run `/chrysalis onboard`. Choose a vault name and parent folder, review the detected timezone and prepared settings, and approve creation. Open the completed folder as a vault in Obsidian and enable community plugins when prompted. No separate language runtime or user build is required.

The empty roadmap awaits a conversation about real goals. Original documents belong inside `Attachments/Originals`, where they can be opened and linked. Task and schedule changes require complete proposals and native operator approval through `/chrysalis approve <digest>`.

After changing the computer's timezone, run `/chrysalis timezone`. Use `--status` to inspect or `--zone Europe/Paris` to choose a named zone. Historical records and existing schedules are preserved.

Read [setup](docs/setup.md), [daily use](docs/user-guide.md), [operation API](docs/operations.md), [architecture](ARCHITECTURE.md), [verification status](STATUS.md) and [development checks](Development/TESTING.md). Pi is the maintained host; the domain core uses no Pi API.
