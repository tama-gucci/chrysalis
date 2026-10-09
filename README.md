# chrysalis

A self-contained Pi package for goals, projects, knowledge and daily work in a private Markdown vault. TaskNotes supplies the Obsidian task interface; Dataview supplies declarative dashboards.

Follow [setup](docs/setup.md) to install a reviewed Git revision through Pi, then run `/chrysalis onboard`. Choose a vault name and parent folder, review the detected timezone and prepared settings, and approve creation. Open the completed folder as a vault in Obsidian and enable community plugins when prompted. No separate language runtime or user build is required.

The empty roadmap awaits a conversation about real goals. Original documents belong inside `Attachments/Originals`, where they can be opened and linked. Task and schedule changes require complete proposals and native operator approval through `/chrysalis approve <digest>`.

Onboarding offers an optional folder of life documents, such as portfolios, resumes, academic
records and bills. Use `/chrysalis documents` to select it. Review selected copies into the vault,
then use supported extracted evidence to discuss your roadmap, possible projects and atomic notes.
You can skip or return later. Copying documents does not approve the resulting records.

The onboarding conversation asks a few independent questions at a time, remembers partial answers
and deferrals, and confirms a recap before drafting adopted goals or projects. A reviewed decision
checkpoint supports resumption; deeper stress-testing is optional.

Every new atomic knowledge note is vetted and individually confirmed before entering the vault.
The knowledge skill compiles selected evidence into related single-thesis notes, maintains a
reviewed index/log and answers questions with citations. Search and lint stay read-only; saved
answer snapshots and repairs require review. Read the [knowledge design](docs/knowledge-design.md).

After changing the computer's timezone, run `/chrysalis timezone`. Use `--status` to inspect or `--zone Europe/Paris` to choose a named zone. Historical records and existing schedules are preserved.

Read [setup](docs/setup.md), [daily use](docs/user-guide.md), [operation API](docs/operations.md), [architecture](ARCHITECTURE.md), [verification status](STATUS.md) and [development checks](Development/TESTING.md). Pi is the maintained host; the domain core uses no Pi API.

Optional [source setup](docs/integrations.md) connects read-only Google Tasks capture through Pi
codemode. Eligible Google Health sleep and Google Maps travel evidence use native review only.
Run `/chrysalis integrations setup`; credentials stay in protected local storage outside the vault.
