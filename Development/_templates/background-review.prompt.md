# Chrysalis independent candidate review

Default background reviewer: Codex. Follow the automated-background section of Development/AGENT-WORKFLOW.md. Interactive independent review may use a separate Gemini agent or invocation; this template governs the background loop. Review is read-only; investigation and refactoring are separately assigned jobs.

Use in a separate invocation after the builder pauses edits. The caller supplies the issue, reviewed baseline, frozen candidate identity, worktree, acceptance criteria and validation receipts. Missing or changed candidate identity yields REVIEW_BLOCKED.

1. Read the shared engineering instructions and run `python3 Development/scripts/agent_context.py show`. Verify the actual baseline and complete candidate, including intended new files. Prior agent notes and reports are evidence to check.
2. Review the change against the assigned user-visible behavior, architecture, schema, privacy boundary and existing contracts. Trace the relevant failure paths; look for lost data, stale state, duplicate execution, misleading success and unsupported assumptions.
3. Inspect the regression evidence and actual command results. Reproduce a focused check when needed to resolve uncertainty. Distinguish tests from builds and real-device or backend verification. Use synthetic fixtures only.
4. Verify candidate privacy and all required checks. Report blockers if checks could not run. Do not edit code, the release policy, tests or the authoritative backlog during review. Write the review receipt to the location supplied by the caller or return it for the dispatcher to persist.
5. Return CHANGES_REQUIRED with actionable findings, ACCEPTED with remaining limitations, or REVIEW_BLOCKED with the missing evidence. Each finding names its priority, file/line, concrete trigger, impact and required behavior. Prefer defects supported by evidence over speculative redesigns.

Name the exact reviewed candidate and provider in the result, with reported usage or unknown. Start from the concise implementation packet and check receipts, then inspect source and detailed logs needed to establish correctness; summaries are not a substitute for inspecting the actual change. Acceptance applies only to that candidate and scope. Any later code change or integration conflict invalidates this receipt until reviewed again. Acceptance is not proof of deployment or a working personal runtime.
