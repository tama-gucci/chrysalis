# Reviewed persistence
`read` returns the complete record and raw-byte revision. Keep that original revision while drafting.
`propose` accepts path, complete document and if_revision (null only for new files), validates the
entire set, and saves it outside the vault. Present its digest and exact changes. The operator runs
the approval command with the digest and human evidence. `apply` uses that receipt and verifies
post-images and resumable progress. A boolean or host chat string is not approval evidence.
Whole-body edits invalidate stale proposals. Local advisory locks coordinate cooperating writers;
the final reread narrows editor races, but neither mechanism is a distributed or OS-level lock.
Quiesce concurrent editing during application. Preserve locally changed records and re-review a merge.
