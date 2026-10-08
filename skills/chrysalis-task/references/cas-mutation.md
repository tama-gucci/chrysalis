# Reviewed persistence

`read` returns the complete document and its raw-byte SHA-256 revision. Keep that revision while drafting.
Call `propose` with `records: [{path, document, if_revision}]` and optional `purpose`.
Each document is the complete post-image; use `if_revision: null` only for a new file.
The operation validates the whole set and saves an inert proposal outside the vault.

Present the complete changes and `proposal_digest`. The operator runs
`/chrysalis approve <digest>`; the native command collects review and confirmation, then applies.
If application was interrupted, `apply` with `{proposal_digest}` resumes the saved exact approval.
A chat statement, boolean, checkpoint flag or model call cannot approve anything.
Changed contents, roots or dependencies need a newly reviewed proposal.

Writes follow `records` order; put foundational records before their dependants. A partial batch
is not complete. Read back successful paths and resume remaining approved work. Local advisory
locks coordinate cooperating writers; they are not distributed or OS-level editor locks.
Quiesce concurrent editing during application and preserve local changes before reviewing a merge.
See the [operation API](../../operation-api.md).
