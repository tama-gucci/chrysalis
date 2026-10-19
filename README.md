# chrysalis

A modular Pi package for planning, learning, research, projects, knowledge and daily work in a private Markdown vault. TaskNotes supplies the Obsidian task interface; Dataview supplies declarative dashboards.

Follow [setup](docs/setup.md) to install a reviewed Git revision through Pi, then run `/chrysalis onboard`. Choose a vault name and parent folder, review the detected timezone and prepared settings, and approve creation. Open the completed folder as a vault in Obsidian and enable community plugins when prompted. No separate language runtime or user build is required.

The empty roadmap awaits a conversation about real goals. Original documents belong inside `Attachments/Originals`, where they can be opened and linked. Task and schedule changes require complete proposals and native operator approval through `/chrysalis approve <digest>`.

Onboarding offers an optional folder of life documents, such as portfolios, resumes, academic
records and bills. Use `/chrysalis documents` to select it. Review selected copies into the vault,
then use supported extracted evidence to discuss your roadmap, possible projects and atomic notes.
You can skip or return later. Copying documents does not approve the resulting records.

The onboarding conversation asks a few independent questions at a time, remembers partial answers
and deferrals, and confirms a recap before drafting adopted goals or projects. A reviewed decision
checkpoint supports resumption; deeper stress-testing is optional. Native assistant setup can enable
bounded web research during onboarding; see [assistant capabilities](docs/assistant.md). Research
informs recommendations; it does not approve adopted roadmap records or notes.

Every new atomic knowledge note is vetted and individually confirmed before entering the vault.
The knowledge skill compiles selected evidence into related single-thesis notes, maintains a
reviewed index/log and answers questions with citations. Search and lint stay read-only; saved
answer snapshots and repairs require review. Read the [knowledge design](docs/knowledge-design.md).

After changing the computer's timezone, run `/chrysalis timezone`. Use `--status` to inspect or `--zone Europe/Paris` to choose a named zone. Historical records and existing schedules are preserved.

Read [setup](docs/setup.md), [daily use](docs/user-guide.md), [operation API](docs/operations.md), [architecture](ARCHITECTURE.md), [verification status](STATUS.md) and [development checks](Development/TESTING.md). Pi is the maintained host; the domain core uses no Pi API.

Optional [source setup](docs/integrations.md) connects read-only Google Tasks capture through Pi
codemode. Eligible Google Health sleep and Google Maps travel evidence use native review only.
Run `/chrysalis integrations setup`; credentials stay in protected local storage outside the vault.

Optional assistant setup lets you choose inexpensive background models, session memory, fixed-role
specialists and an isolated execution workspace. Bash/file tools work in that workspace while vault
changes retain exact native approval. Browser and Gemini media packs are optional; real Gemini/YouTube
acceptance remains deferred. See [assistant controls and limits](docs/assistant.md).

Onboarding also offers optional [saved-password import](docs/passwords.md) into a dedicated private
inbox. CSV/JSON imports append/update an encrypted account file outside source/vault. Browser login
uses native account/origin selection; the model and child agents never receive credential values.

Pi owns its default MCP and codemode extensions; keep both enabled. Independent provider/UI packages
use ordinary Pi resources. See the [compatibility matrix and scoped tool policy](docs/compatibility.md).

## Optional NixOS system

The same Pi package now has an optional NixOS module and persistent x86_64 UEFI USB image.
Cage opens Ghostty, tmux and ordinary Pi; disko installs the dedicated encrypted Btrfs target.
After boot, existing native onboarding creates the Obsidian vault. One reviewed OS outcome
authorizes its system work and fixed machine ledger; personal records retain their exact reviews.
See [NixOS setup and acceptance](docs/nixos.md). The prototype requires the documented VM gate
before physical installation; package/evaluation checks alone do not establish boot acceptance.
