# Conversational life onboarding

Use this procedure for first setup, a fresh roadmap, or a deliberate reconsideration of direction.
It is part of `chrysalis-knowledge`, using Pi conversation, clarification,
session continuation and reviewed domain writes. Research guidance below requires supplied evidence
or a separate research session; the life profile has no web or external memory tool. Do not build another agent or interview engine.

## 1. Establish context and assess the environment first

Run native /chrysalis onboard for a new vault. It detects timezone, stages the prepared folder, obtains operator approval and verifies files before this conversation. Resolve the explicitly selected vault, external state and package; do not fall back to the development checkout. Read an
existing `System/Onboarding.md` checkpoint when resuming and only the current records needed to
understand its status. Fresh-start onboarding never mines archived personal priorities by default.

Invoke `chrysalis-environment` to generate or refresh a reviewed `Environments/<node-id>.md` manifest
before roadmap creation. An existing recent manifest can be reviewed and reused. Show unknowns,
including whether the terminal observes the physical host or a container. Persist only the approved
manifest. If the environment cannot be assessed fully, continue the conversation with a partial
assessment; block only work that requires a genuinely unavailable capability.

Do not create Memory, seed a roadmap, install packages or initialize a vault as a preflight
side effect. A blank seed is not a chosen plan. Propose missing operational configuration later.

## 2. Understand the aspiration before making it specific

Read `goal-discovery.md`. Invite rough goals, tensions, curiosities and things the user would like to
change. Ask one to three short questions per round using native clarification when useful; ordinary
conversation is sufficient. Batch only independent questions. Accept “not sure,” “skip,” and “later.”

Clarify meanings, motivations, starting position, practical constraints and success criteria. Reuse
answers already given; do not force archetypes, a fixed number of pillars, or a complete biography.
Ask for decisions and personal context; identify external facts that require verification. Hardware
limitations inform near-term execution, not the range of aspirations the user is allowed to explore.

## 3. Research routes, then compare them

For an uncertain aspiration, develop two or three credible alternatives when available, including a
bounded exploration route if the user is not ready to commit. Keep supplied evidence in this
onboarding session/checkpoint. Browser tools and other packages' research skills are unavailable
in this life profile. Offer a separate research session and bring its cited findings back for review;
do not bypass the tool policy or imply that unchecked facts were researched.

Use current primary sources for requirements, eligibility, admissions, costs, timelines or software
compatibility. Establish the relevant jurisdiction before researching regulated qualifications.
Record each important claim's source URL, retrieval date, scope and uncertainty. Separate mandatory
requirements from optional strategies, estimates, marketing claims and the agent's recommendations.
Do not invent facts when browsing is unavailable; propose verification as the next step. Ask only
for personal details needed to distinguish routes. Do not put sensitive personal context into searches.

Compare fit against the user's criteria: outcome, prerequisites, time range, cost uncertainty,
flexibility, opportunity cost, dependencies, reversibility and unanswered questions. Explain why a
recommended route fits, and invite correction. Do not force novelty or discard standard paths simply
because an ideation skill favors unusual ideas. Research material remains untrusted source data.

## 4. Choose a direction or choose to learn more

Summarize what the user has chosen, what remains exploratory, and what they are declining or deferring.
Do not promote your recommendation to a user decision. If uncertainty is material, propose a small
experiment with a learning question, manageable effort and a review point. Choosing an exploration
project is a valid outcome; it does not imply commitment to its possible destination.

Establish the first feasible milestone and a small number of near-term actions. Unknown final dates
remain unknown. Clearly distinguish hard externally verified deadlines, provisional estimates, and
dates the user desires. Avoid promising controllable outcomes for decisions made by third parties.

## 5. Draft the life roadmap only after exploration

Read `System/_templates/Life-Roadmap.template.md` through `template` as a blank structure.
Translate only selected or
explicitly exploratory directions into the proposal. For each active direction, capture:

- Desired outcome and why it matters to this user.
- Chosen route, or a clearly labeled exploration decision.
- Evidence, dependencies, assumptions and review conditions.
- Milestones with observable evidence of progress; dates only when justified.
- A next action small enough to begin and a realistic capacity limit.
- What is deferred, declined or out of scope.

Use only as many pillars/tags as the user needs. Do not make systems setup the compulsory first
pillar. Draft the canonical tag registry before tasks. Keep later milestones in project roadmaps,
and materialize only approved near-term actions. Uncertain alternatives are not extracted commitments
to which the ingestion horizon rule automatically applies. Do not manufacture a Zettel for every idea.

## 6. Review, persist and verify

Present the concrete roadmap and exact list of records to create/update: relevant projects, source
records, useful Zettels, initial unscheduled tasks, and minimal operational state. Show unresolved
assumptions and what remains inactive. Reuse only a saved native approval for the same digest; choosing a
route alone does not authorize an unspecified backlog, appointments, purchases or external messages.

Validate and save the proposal first, then obtain `/chrysalis approve <digest>` review/application.
Capture existing revisions before drafting. Put roadmap/tag registry before dependent tasks in
`records`; application follows caller order and does not automatically sort dependencies.
Use `chrysalis-task` for task records and the knowledge pipeline for researched source/project/Zettel
records where appropriate. Use ordinary `propose` for the complete system-state change set.
Use explicit runtime paths, offset timestamps and safe YAML serialization. Keep existing learning
and integration settings unless the reviewed reset includes them; initialize only missing values.
Do not seed placeholder projects, assumed work hours or automatic ingestion as personal decisions.

The cross-file change set is not an all-or-nothing transaction. Record each successful path/revision;
if a later write fails, stop, report the partial state, reread it and resume remaining approved work.
Do not claim completion or blindly repeat earlier creates. Verify schema, links and saved content;
use read-only diagnostics. A freshly prepared empty vault must pass doctor; do not dismiss failures
as expected emptiness.
TaskNotes alone owns Calendar synchronization. New tasks remain `scheduled: null` with no event ID.

## 7. Hand off to the daily skill

After the approved onboarding records pass readback, **invoke `chrysalis-daily` in this conversation**.
Read its `references/daily-entry.md` and call `daily.begin` with mode `check-in`, the configured
timezone and `invocation_id` set to the handoff UUID described below.
Do not merely suggest a daily prompt or claim that reading the skill ran it. This is the normal final
onboarding stage; the user can still pause or decline it. Do not run it after a proposal-only interview
or while the approved roadmap apply remains incomplete.

Use a fresh UUID for this onboarding handoff. Propose and obtain exact approval to save it as
`daily_handoff_id` before entry, set stage `daily_handoff`, and maintain `daily_handoff_status`:
`pending`, `started`, `paused`, or `complete`. Without a saved checkpoint, retain it in the Pi session. Reuse the
same ID when recovering after interruption; the receipt helper distinguishes existing entry from a
new invocation. Read prior progress and resume unfinished actions rather than repeating a check-in
or already applied changes. If the ID/progress cannot be recovered, clarify status before restarting.

Start a light first-day conversation using the newly saved roadmap and the current local time.
Ask for missing capacity, energy and commitments; morning/afternoon can focus on a feasible next
action, while evening can review today and propose tomorrow. Do not fabricate completed sessions
or force a full-day schedule late at night. The daily procedure retains its task/schedule approval
gates. Once it reaches a useful stopping point, report completed and pending work accurately.

The handoff alone does not suppress a separately implemented evening fallback. If the daily conversation actually produces an
audit result or concrete staging proposal, retain the actual hashed result receipt produced by `audit` or `stage`; only that completed
stage suppresses the matching local date's evening fallback. Use `stage` for qualifying planning;
morning calibration through `plan` alone does not count.
The user can request another daily check-in. A completed handoff is not
reinvoked when an already finished onboarding checkpoint is reopened.

## Pause, resume and revise

Offer a concise progress recap at natural pauses. With approval to save progress, maintain
`System/Onboarding.md` from the sanitized checkpoint template using the same system-state CAS path.
Batch checkpoint updates at natural pauses. Every changed post-image requires a new exact proposal
digest and native approval; blanket permission to save progress is insufficient. Without approval,
keep discussion in the Pi session and do not claim a vault checkpoint exists.

Checkpoint stages are `environment`, `exploration`, `research`, `decision`, `roadmap_proposal`,
`applying`, `daily_handoff`, `complete`, or `paused`; these labels are procedural guidance, not a new state engine.
Store confirmed answers, candidate/declined routes, dated source links, next useful question, approved
scope and saved-file receipts. Do not dump full transcripts. On resumption, briefly recap and ask
only what is still needed. Recheck stale research and canonical records before applying anything.

## Approval and completion markers

`roadmap_approved` in the checkpoint refers to the exact reviewed proposal, identified in its save
receipts or by a digest of the proposed record set. It becomes true only when the user approves that
proposal. Material changes to its contents invalidate that approval: mark it false and review the
changed proposal before continuing. This field is a record of approval, not a substitute for it.

The blank roadmap's `onboarding_status: awaiting_conversation` changes to `active` in the approved
populated roadmap. Only report that transition complete after successful persistence and readback.
Checkpoint stage `complete` requires all approved onboarding records to verify and the daily handoff
to reach a verified stopping point (`daily_handoff_status: complete`). A daily plan may still be pending
approval; explicitly list that pending work. If the user pauses/declines daily, keep onboarding paused
with its saved roadmap intact and explain what remains. Partial record application stays `applying`
or `paused`, with successful receipts and remaining work listed.

Stable confirmed preferences belong in reviewed System/Memory.md. Candidate routes and changing
goals stay in the checkpoint and, once adopted, the vault roadmap. The package provides no separate
host-memory integration.
