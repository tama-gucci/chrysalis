# Implementation status

Version 2.0.0 contains one TypeScript/Node core, seven canonical skill families, a shared operation
API and a native Pi extension. Onboarding prepares an Obsidian folder with TaskNotes 4.13.8,
Dataview 0.5.68, nonsecret settings and detected named timezone. The user chooses the vault name.
Obsidian installation, account configuration and storage transport remain user responsibilities.

Verified in isolated Windows ARM64 fixtures with Pi SDK 1.0.4:

- All 37 maintained Node tests pass on minimum Node 22.18.0. Production TypeScript checks and the
  whole-source privacy/resource check pass. Node 24.20.0 has also exercised the implementation.
- Core cases cover approval/CAS conflicts and recovery, dependency validation, protected TaskNotes
  fields/history, timezone changes/DST, original hashes/PDF parsing and compressed-stream budgets,
  discovery/quarantine/provider identity, projects/knowledge, planning/staging/learning/pauses and receipts.
- The pinned TaskNotes model 0.3.0-rc.9 roundtrips supported native task fields/date forms against
  the generated schema. Native timeblock collision/midnight cases, moved originals, structured
  completion/updates/local conflicts and corrected setup have dedicated regression coverage.
- Native command tests cover declined/edited review, unapproved restart, explicit zone correction,
  Unicode names, approved-scope recovery and conversational handoff. Actual SDK loading discovers
  seven skills, calls the tool and denies arbitrary reads/executors.
- Pinned plugin bytes match locked hashes. Clean production-only npm archive and Pi-managed pinned
  Git installations load the package, generate a vault with networking forbidden during onboarding,
  and pass doctor. Installed-package onboarding also passes on minimum Node 22.18.0.
- Package removal in a disposable Pi profile preserves the generated vault and external chrysalis state.
- Three architecture flowcharts render without parser warnings. Maintained documentation links,
  frontmatter and shipped resource syntax pass the source checker.

The [behavior matrix](tests/specs/behaviors.md) separates deterministic, transport, conversation,
account and UI acceptance. Tests/dialogs/assistant calls use synthetic data. Detailed receipts,
frozen hash identities and independent read-only review evidence remain outside source.

Physical Obsidian rendering, community-plugin activation and task/timer interaction have not been
verified in this implementation run. Model conversation quality, research, authenticated integrations,
other operating systems/devices and OCR/vision require separate acceptance. The supported Pi range
is not a claim that every host version was tested. Health-data integration remains deferred.

Source publication and npm registry publication are distinct. No npm release or personal-vault
adoption is established by these checks. Local CAS coordinates cooperating writers; it cannot
provide a distributed transaction or prevent every noncooperating editor race.
