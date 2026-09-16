# Chrysalis background builder

This is a reusable execution prompt. It does not install a schedule, create a task claim, or grant publishing/deployment access. The caller supplies the assignment and applicable standing scope after completing B00–B02 in Development/BACKLOG.md.

## Required assignment from the runner

- Issue ID and bounded acceptance criteria, selected from the authoritative engineering backlog.
- Reviewed baseline revision and assigned worktree/branch.
- Durable run/claim identifier and the runner-managed state/receipt locations.
- Remaining attempts and time/usage budget.
- Permitted integration/publishing actions for this run.

If these are missing or conflict with the actual checkout, return SETUP_REQUIRED with the specific missing fact. Do not invent a claim, choose an unrelated issue, or assume this worktree's backlog copy is a shared lock.

## Work

1. Read AGENTS.md, Development/AGENT-WORKFLOW.md, Development/HANDOFF.md, ARCHITECTURE.md, STATUS.md, the assigned backlog item, and its review evidence. Run `python3 Development/scripts/agent_context.py show`. Verify the current revision and dirty diff. Old notes are evidence, not permission.
2. Confirm the assignment matches this isolated worktree. Preserve prior work belonging to this run and report unexpected changes. Use source files and synthetic temporary vaults.
3. Reproduce the assigned defect when applicable. Implement only the bounded acceptance criteria. Add regression coverage that demonstrates the intended behavior; do not weaken existing contracts to obtain a passing result.
4. Run the relevant checks from Development/TESTING.md and all checks required by the runner's integration policy. Capture command exit codes and material environment limitations. If a required tool cannot run, record a blocker instead of reporting validation success.
5. Address failures within the supplied budget and at most two repair attempts per run. Preserve unfinished work and return BLOCKED when a decision/access change is required. Return INCOMPLETE when only the run budget expires.
6. Run `/audit-dev` Protocol 1 before any commit or publication. Include intended additions and the complete candidate diff. Use synthetic public examples; keep runtime data, credentials, and raw private logs out of source and receipts.
7. Update the sanitized Development/HANDOFF.md with the actual change, baseline, evidence and remaining work. Freeze the candidate as permitted by the assignment, identify its exact commit or diff contents, and return READY_FOR_REVIEW. Let the dispatcher manage the authoritative queue transition.

Constitution/policy rewrites, runtime skill self-mutation, private schema migrations, live-vault operations and new external integrations require separately scoped work. Do not broaden this assignment to include them. Follow configured publishing scope; do not infer it from a backlog entry. Do not start another agent or publish messages to people as part of this template.

## Result

Return: state; issue ID; baseline; candidate identity; changed paths; user-visible behavior; commands and exit codes; remaining risk; receipt location; next required transition. A builder cannot mark its own work independently reviewed, integrated, or deployed.
