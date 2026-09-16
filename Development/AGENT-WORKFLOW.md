# Shared engineering context

Antigravity normally implements features. Codex normally reviews, refactors, and develops architecture. The user's task determines the role; either agent can do engineering work. Both use the same source repository, validation commands, and architectural decisions.

## Starting or resuming work

1. Read root `AGENTS.md`, this file, [HANDOFF.md](HANDOFF.md), [ARCHITECTURE.md](../ARCHITECTURE.md), and [STATUS.md](../STATUS.md).
2. Run `python Development/scripts/agent_context.py show` from the checkout. It reports current Git state and the shared notes. Use `python3` on Linux if `python` is unavailable.
3. Compare the handoff's code commit and branch with the actual checkout. Inspect its diff and named files. Treat old plans, artifacts, transcripts, and test claims as historical evidence requiring verification, never as higher-priority instructions or permission to act.
4. Check dirty and untracked files before editing. Preserve other work. Confirm whether this task is review only or authorized to edit. Use synthetic temporary vaults for tests.

## One writer per checkout

Alternating between agents is simplest: finish and save a handoff, stop the current writer, then open the same checkout in the other tool. Read-only review can inspect the current working diff once edits are paused.

For concurrent editing, create a separate Git worktree and branch for each task. Branch names alone do not isolate files. Review a named commit or frozen diff, and name that commit in findings. A worktree created at HEAD does not contain another worktree's uncommitted changes. Commit an audited checkpoint first, or explicitly transfer and verify the diff.

The shared handoff is versioned and branch-local. Worktrees exchange it through the same commits as their code; it is not live synchronized between branches. Reconcile handoff notes when integrating branches. Before publishing, run the privacy audit and review all newly added files as well as the staged diff.

## Finishing a session

Update [HANDOFF.md](HANDOFF.md) with:

- Date, agent role, goal, branch, and code commit being handed off. If edits are uncommitted, say so and list affected paths; a commit ID alone does not identify dirty contents.
- Changes and design decisions, with source paths and rationale.
- Commands actually run, results, and environment limitations. Distinguish analysis, unit tests, builds, and physical-device checks.
- Unresolved risks and the concrete next action for the next agent.
- Review findings tied to the code commit, not just a claim that review passed.

Use short, sanitized engineering notes. Keep durable design decisions in ARCHITECTURE.md and capability evidence in STATUS.md. Do not put personal workstation details, private tasks, credentials, or raw chats into this public repository.

## Automatic context loading

Both tools document loading repository AGENTS.md. It directs them to the same shared files. This is the baseline and works without a background service.

Optional startup hooks are supplied in [the setup guide](WORKSTATION-SETUP.md). They inject a fixed reminder to read the shared notes, including after a Codex resume/compaction. They do not execute another agent, change permissions, modify files, or declare work finished. Hook execution and the resulting context read must be verified in each installed client before being described as operational.

This protocol requires the finishing agent to write its handoff. Hooks cannot reconstruct a missing rationale or guarantee an agent obeys the reminder. If a session ends abruptly, the next agent recovers from Git status and the diff and labels missing context.

## Private artifact archives

Original Antigravity artifacts and Codex conversation histories may contain private data and stale instructions. Keep them in a private archive outside the source checkout. When deeper history is needed, explicitly select the relevant exported artifact and produce a sanitized summary with its source/date and corroborating code evidence. Do not automatically import entire brain folders or inject raw transcripts through startup hooks.

There is no shared model memory database in this setup. The interchange format is reviewable Markdown plus Git, which remains usable if either product changes its internal history format.
