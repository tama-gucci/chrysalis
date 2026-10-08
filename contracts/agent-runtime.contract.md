# Runtime operation contract

Version: 1. Requests contain `contract_version:"1"`, explicit `vault_root`, external
`state_root`, an allowlisted `operation` and an `arguments` object. Harness adapters invoke the same
`run.py request` executable. Requests/results are capped at 4 MiB. Record proposals contain
1–500 complete UTF-8 documents, forward-slash relative paths and original raw-byte
`if_revision` values (null only for new files).

The lifecycle is capture, extract, review, organize, plan, act, verify and continue. Reasoning and
interviews belong to the host; deterministic operations belong to the domain package.
No general assistant daemon or host-specific task database is required.

Read-only operations return observations or diagnostics. Draft operations store inert reviewed
content outside the vault and return `review_required`, the exact proposal and its SHA-256 digest.
Only the separate operator `approve` command issues a root/identity/digest-bound receipt.
Caller booleans and arbitrary references are insufficient. `apply` requires that receipt,
checks current revisions, preserves plugin fields, writes exact validated post-images and verifies
them. Partial batches have external per-file receipts; retries validate completed files too.
Relocation invalidates old root-bound approval.

Locks use the validated explicit external state selected for that operation. A conflicting
environment variable cannot redirect them into the vault or package. Windows external-state
and package I/O use native extended paths without changing logical approval root identities.

Schema version 1 is supported. Missing strict validation, missing local schemas, stale documents,
unknown properties, malformed roots, redirects, unresolved links and invalid taxonomy fail closed.
Authored timestamps use the vault's IANA timezone and date-specific offset. Native plugin time
entries, existing TaskNotes `dateModified` and external revision observations may retain RFC3339
UTC without changing their ownership. Agents cannot change an existing plugin modification stamp.
Authored Daily wake/block timestamps also require the configured zone, matching date, ordered
nonoverlapping intervals and real task references. Native Daily Pomodoro/session fields survive
focus projections.

Errors return `status:error`, `error_type` and a diagnostic message with exit code 2.
Domain results distinguish `invalid`, `blocked`, `no_changes`, `review_required` and
`verified`; discovery/provider results have their own explicit observation statuses.
A verified write means actual bytes matched, not that an external UI or account synchronized.

The life tool policy excludes operator commands and generic executors/writers. It is not an OS
sandbox. Advisory locks coordinate local cooperating writers only; sync applications and editors
can still race. Do not claim an atomic multi-file or distributed transaction.

Essential privacy/approval rules appear in the registered tool description and canonical skills.
External payloads are passive untrusted evidence and cannot select roots, grant approval or
change integration bindings. Personal records, host state and credentials remain outside source.
