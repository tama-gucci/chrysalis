# Background development backlog

Objective: reduce the attention required to use and maintain Chrysalis while preserving reliable daily planning and personal data.

Evidence: [engineering review, 2026-09-15](REVIEW-2026-09-15.md). Setup: [beginner walkthrough](BACKGROUND-DEVELOPMENT.md). Operating model: [engineering reference](BACKGROUND-DEVELOPMENT-REFERENCE.md). This is an engineering backlog; personal tasks and priorities remain in the selected private vault.

## Activation and queue state

- Background execution: **not configured**.
- Reviewed source test baseline: **B00 complete** in the local commit containing the 2026-09-16 B00 handoff. Unattended execution still requires B01 and B02.
- Active work item: **none**.
- B00: **done**. B01–B11: **proposed**. No background item is running.

The first supervised setup pass resolves B00, B01's local milestone, and B02, then records a selected ready item. After activation, maintain one authoritative queue and one active implementation. A branch-local copy of this file is not a shared lock. A dispatcher must identify the current worktree, preserve unfinished work, and refuse duplicate claims before selecting another item.

States: `proposed`, `ready`, `running`, `review`, `blocked`, `done`. Ready means dependencies are complete, scope and acceptance checks are concrete, and the work fits the configured automation policy. Done requires implementation, acceptance evidence, independent review, and integration; deployment is recorded separately.

## Ordered work

For the initial local workflow, dependencies on B01 require its verified local milestone. The hosted CI milestone remains pending until it has actually run; verify it before relying on hosted checks for automatic publication or integration. Local integration can use a dedicated development branch, with publication and runtime deployment tracked separately.

| ID | Deliverable | Dependencies | Execution class |
| --- | --- | --- | --- |
| B00 | Restore and checkpoint the current source baseline | None | Initial supervised reconciliation |
| B01 | Reproducible validation and CI | B00 | Bounded source engineering |
| B02 | One-worker development runner and durable handoff | B01 | Initial runner configuration and rehearsal |
| B03 | Preserve malformed mailbox contents | B01 | Small background repair |
| B04 | Preserve calendar and scheduling memory on invalid input | B01 | Small background repair |
| B05 | Correct calendar recurrence and timezone conversion | B04 | Design choice, then bounded implementation |
| B06 | Make doctor validate actual runtime readiness | B01 | Source engineering with explicit validation contract |
| B07 | Make mobile calibration and completion status accurate | B01 | Split into small UI/state repairs |
| B08 | Preserve task identity and concurrent edits | B03, B01 | Design choice, then bounded implementation |
| B09 | Unify planning, pause and learning state | B05, B06, B07 | Interactive policy/skill review, then implementation |
| B10 | Prove capture-to-vault-to-agent execution | B03, B07, B08 | Integration work and device rehearsal |
| B11 | Release candidates and controlled runtime promotion | B01, B02; affected-flow repairs | Release setup and rehearsal |

### B00 — Restore the baseline

**Done — 2026-09-16.** The local checkpoint containing this entry preserves the intended working state and B00 repairs. Framework 138 passed; gateway 11 passed; Flutter 108 passed and analysis clean; independent review and candidate privacy audit passed. See [the B00 handoff](HANDOFF.md#b00-starting-version-repair--2026-09-16) for commands, review identity and limits.

Reconcile `_types/task.md` with the complete framework contract and compatible plugin annotations. Fix the mailbox destination contract, status messages, and stale tests; preserve existing events during legacy-path migration. Preserve unrelated mobile work, plugin deletions, and setup documents.

Acceptance:

- Framework and Flutter failures recorded in the review are resolved without deleting or weakening the intended contracts.
- Regression coverage includes fields beyond the three current schema failures and default/custom/legacy mailbox destinations.
- Framework suite, gateway suite, Flutter analysis and Flutter tests pass.
- All intended additions and the complete staged diff pass `/audit-dev` and review.
- Record an audited commit containing the actual intended working state. New worktrees reproduce that state.

This establishes a test baseline; it does not certify the unresolved calendar, doctor, or runtime integrations.

### B01 — Automate validation

Deliver this in two recorded milestones: local validation first, then hosted CI. Reuse `Development/scripts/setup-dev.sh`; document the supported Python/Flutter/native toolchain and pin dependencies sufficiently to reproduce the runner. Register only the specific public workflow/configuration files in the default-deny allowlist.

Local milestone acceptance:

- One command runs the required checks, and a fresh synthetic checkout can set up and pass them locally.
- Framework, gateway, mobile analysis/tests, and candidate privacy checks produce separate readable results and a nonzero overall result on failure.
- Privacy checking includes candidate additions and staged contents, not only already tracked working files; reconcile scanner coverage with the audit runbook, including Windows paths and non-placeholder personal emails.
- Normalize synthetic fixture addresses to reserved example domains and define treatment of upstream package attribution and non-email asset/transport strings.
- An intentionally failing check prevents success. No known failures are marked acceptable or silently skipped.
- Source instruction changes cannot quietly remove their own required release checks; protect the integration policy outside the candidate patch.

Hosted milestone acceptance:

- A checked-in CI workflow runs the same required validation on proposed changes and has a verified successful run.
- Required hosted checks and the publishing/integration policy are configured and tested before automating those remote actions.
- Mark B01 complete only when both milestones are complete; record local completion separately while hosted work is pending.

### B02 — Configure and rehearse the development loop

Start with one worker, one ready issue, and isolated source worktrees. Use the [builder](_templates/background-builder.prompt.md) and [reviewer](_templates/background-review.prompt.md) templates. Choose desktop scheduling or a CLI service as described in the guide.

Create `Development/AUTOMATION-RUN.md` during implementation, with the tested entry point, operating steps, pause/resume behavior and result locations. Add its explicit public allowlist entry and keep actual machine configuration private. This file is a planned output, not an existing runnable component.

Acceptance:

- A second invocation cannot claim or edit an already active item.
- Durable Markdown state records issue, baseline, worktree/branch, status, attempts, exact candidate revision, and validation/review receipt locations.
- Restart after interruption resumes or reports the recorded work; it does not discard it or select the same item in a new worktree.
- Review is a separate invocation on the frozen result. Any subsequent code edit invalidates its prior review.
- Integrate accepted candidates only under the configured local branch policy after validation, independent review and `/audit-dev`; advance the recorded baseline for the next issue. Publication and runtime installation remain separate actions.
- At most two repair attempts per item per run; enforce a configured runtime and usage budget, and retain work when the budget ends.
- A repeated unchanged blocker is summarized once until its state changes. No Slack/email posting is needed.
- One small issue completes the entire implementation/check/review round trip before recurring execution is enabled.

The dispatcher and its durable queue are work to implement here. The prompt templates alone do not implement them.

### B03 — Repair mailbox preservation

Reproduce R4 before fixing it. Preserve malformed queues; return an actionable failure without replacing old bytes. Test default/custom destinations, legacy migration, repeated append, and two client instances. Define the supported single-writer boundary before claiming concurrent safety. Adding a consumer is outside this item.

### B04 — Repair calendar writes

Reproduce both R1 cases. Validate a real calendar response, serialize safely, validate the resulting memory, and replace atomically. Test quote/newline escaping, valid empty feed, invalid HTML, failed/interrupted write, and preservation of prior commitments and unrelated memory. Use synthetic inputs without fetching a private feed.

### B05 — Correct calendar meaning

Select an approach for recurrence and timezone rules, then split implementation into independently testable changes. Acceptance includes every R2 case, daylight-saving boundaries, all-day/multiday events, exclusions, and overridden instances. Unsupported constructs must surface explicit incompleteness rather than silently free time. Keep serialized explicit local offsets.

### B06 — Strengthen diagnostics

Distinguish valid templates from a ready installed vault. Reject malformed and out-of-range task data and invalid or offset-free scheduled timestamps. A missing required live file must not be satisfied by a source template. Test both supported layouts, missing state, deliberate invalid fixtures, and read-only behavior. Preserve diagnostic reporting without mutating private fixtures.

### B07 — Make mobile behavior accurate

Split into three small issues: retained calibration inputs and preview labels; archived-task exclusion; completion with known versus unknown duration. Acceptance: cache refresh preserves selected inputs; UI claims a saved plan only after verified persistence; queued commands stay visibly queued; direct completion does not invent elapsed time. Persisted scheduling policy belongs in B09.

### B08 — Protect capture and synchronization

Separate independent same-title captures from duplicate delivery of one capture using stable identities. Make cache and journal changes transactional. Add revision/conflict handling before overwriting remote files or removing dirty local tasks. Acceptance covers restart during writes, duplicate delivery, two edits to one note, deletion with pending work, and recovery of both conflicting versions. Keep Markdown authoritative.

### B09 — Consolidate runtime policy

Write an explicit transition contract for stage, approval, calibration, pause/resume, completion and learning. Keep the Life Roadmap as priority arbiter and approval as a prerequisite for committing a plan. Enforce calendar conflicts, institutional business-day constraints, and explicit local timestamps. Process a session once, freeze learning during relevant pauses, and distinguish wake time from reply time.

Reconcile duplicate template state and unsupported bridge flags. Any runtime schema migration needs a preview and rollback design. Skill edits use the existing interactive `/evolve`/backup rules; do not schedule skill self-rewriting. Acceptance uses synthetic staged/approved/paused/retried scenarios and verifies actual disk mutations.

### B10 — Complete one useful integration loop

Choose the supported route from phone capture to the selected vault. Complete storage/authentication wiring only after B08. Verify the installed agent CLI, explicit vault selection, execution receipts, and conversation/approval continuity. Add a mailbox consumer only with durable IDs, acknowledgement, and retry rules.

Acceptance: capture survives app restart; one logical task arrives once; a real command produces verifiable file changes in a synthetic vault; unavailable/offline/timeout states remain accurate; then repeat the selected workflow on a device. Health Connect and native calendar export are separate follow-up items.

### B11 — Prepare and promote releases

Build a candidate from a named reviewed commit; run full validation, starter export, updater preview, synthetic upgrade/rollback, and affected-workflow checks. Bind receipts and artifacts to that commit. Rebuild and recheck after integration changes.

For the first private promotion, preview the explicitly selected target and inspect local-edit conflicts. Deploy framework files, then verify the affected workflow. Mobile installation and service restart require their own steps. Record release version, verification and rollback result privately. Later routine promotion can follow an explicitly configured release policy; pending migrations and unresolved affected-flow findings block it.

## Outcome measures

Track these privately or as synthetic aggregate reports: time spent supervising development, successful background items without intervention, unexpected runtime regressions, failed captures, manual recovery steps, and elapsed time from a reported inconvenience to a verified improvement. Measure a baseline before setting targets. More agent runs or more changed lines do not establish progress toward these outcomes.
