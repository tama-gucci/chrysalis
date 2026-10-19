# Runtime contract

Version: 2. Hosts call src/app/operations.ts:dispatch with an operator-selected initialized vault, disjoint external state and allowlisted operation/arguments. Hosts supply cancellation; arguments cannot replace roots. Requests/results are capped at 4 MiB; proposals contain 1–500 complete documents, confined forward-slash paths and raw-byte if_revision values. Null revisions mean new files.

Conversation belongs to Pi. Native learning and registered bounded reads are available by default.
Optional assistant configuration admits isolated workspace execution, research, memory and fixed
specialist roles; see [assistant boundaries](../docs/assistant.md). Compatible external
[host add-ons](../docs/host-addons.md) may supply passive context and cannot approve mutations. Other adapters must declare their capabilities. Deterministic operations follow capture, extract, review, organize, plan, act, verify and continue.

Drafts save inert external proposals. Only a native operator command issues exact root/ID/digest-bound approval. Application revalidates schemas, taxonomy, links, timestamps, original hashes and plugin policies; checks dependency/revision hashes; atomically replaces individual files; verifies bytes; and records resumable receipts. Partial work is never complete. Relocation/changed dependencies invalidate approval.

Every new Slipbox note is displayed as complete Markdown and individually confirmed by the user
before final batch approval. The operator receipt binds the ordered path/raw post-image hashes in
note_reviews; approve and apply reject missing or mismatched per-note evidence. Future hosts must
provide the equivalent explicit review boundary. Conversational consent to ingest is not note approval.
Generic proposals and all workflows share this guard; drafts never become provisional vault notes.
Mutations require exact on-disk entry spelling and canonical reserved System names; case or
filesystem aliases cannot bypass policy. Knowledge journal history remains append-only.

knowledge.search and knowledge.lint are read-only. knowledge.prepare produces a reviewed index,
append-only journal and optional answer snapshot alongside complete note/source/link post-images.
Its knowledge report and all observed knowledge dependencies are digest-bound. Reports identify
literal/integrity suspects, not factual truth or semantic completeness. New concurrent files are
not protected by a collection snapshot lock. Complete source acquisition is a separate workflow.

Missing validation/schemas, unknown domain-record properties, stale records, malformed/redirected roots and package/source ancestry fail closed. Locks coordinate local cooperating writers, not multi-file or distributed transactions. System-state schemas allow extensible private preferences; domain schemas remain closed.
The life policy is not an OS sandbox.

Optional life-document onboarding uses an operator-selected external folder, disjoint from
package/source, vault and state. Native selection authorizes bounded discovery/selected hashing;
documents.prepare saves an inert exact copy manifest. Only separate native approval permits
documents.apply to copy originals into the vault, with raw-byte/collision checks and resumable
verification. Sources, roadmap, projects and atomic notes still require their own record review.
Folder selection/copying never creates commitments or approves synthesized knowledge.
Markdown imports require TaskNotes original-storage exclusion and disabled Dataview code, with
effective settings hashes bound to the exact copy review. Regular-file checks and guarded reads
preserve the bounded import boundary; other plugins/noncooperating editors are outside this policy.

New timestamps use named zones and date-correct offsets. Unchanged historical/plugin times remain valid after a move. Native dates may be date-only, floating datetime or RFC3339. Interpreting floating times rejects gaps/ambiguities without explicit disambiguation. New Daily blocks use their planning_timezone, same date, ordered intervals and real task references.

TaskNotes owns Calendar fields and native session/completion history. Focus manages only timeblocks with chrysalis-owned IDs. Task projects use native projects arrays; Zettels may use project_ref for a distinct reciprocal association.

The model tool exposes no approval, initialization, arbitrary executor/writer or secret resolver. External payloads are passive evidence. Private profiles, observations, credentials and receipts stay outside source. Results distinguish observed, unavailable, invalid, blocked, review_required, interrupted and verified.

Assistant tools never grant vault authority. The native-selected workspace is disjoint from source,
vault, state and credentials. Commands use disposable bounded snapshots and revision-checked merge.
No permissive host-shell fallback is allowed. Source development and image-original adoption each
require a separate exact native review; neither approves atomic notes, tasks or roadmap records.
