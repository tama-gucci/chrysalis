# Maintained behavior coverage

Canonical families are daily, task, knowledge, diagnostics, environment, integrations and maintenance. All use chrysalis_operation. Tests are in core.test.ts and pi.test.ts; their names below are literal test descriptions or named scenario groups.

| Behavior | Operations / family | Deterministic evidence |
|---|---|---|
| Complete read observations and bounded queries | read, query, schema, template / all | Raw revisions, read-only query/template/schema cases |
| Schema and plugin contracts | validate, propose / task | Missing validator/unknown fields; TaskNotes model roundtrip; protected Calendar/history |
| Exact approval and CAS recovery | propose, apply / all | Complete approval/body conflicts; dependency revalidation; interrupted-batch resume |
| Onboarding and checkpoint procedure | native onboard; knowledge | Operator decline/edited review/recovery and handoff; unapproved restart/zone correction, Unicode names and approved-scope preservation; checkpoint writing uses ordinary system-state CAS |
| Goal research and chosen roadmap | knowledge references | Canonical procedure retained; real conversation/research quality needs separate acceptance |
| Automatic reusable timezone setup | native timezone | OS detection ignoring TZ; move preserves schedules/history and invalidates pending approval; DST gaps/folds |
| Task capture and velocity | task.draft / task | Unscheduled defaults, actual multipliers and no fabricated parent |
| Complete project ledger / 14-day horizon | horizon, project.status / knowledge | Future stays ledger-only, unknown-date review, native projects links |
| Additive / scoped reconciliation | project.reconcile / knowledge | Partial inputs cannot remove; completed/user-edited/other-source work preserved |
| Atomic knowledge and reciprocal linking | graph / knowledge | Exact project-Zettel links and task propagation; no fuzzy associations |
| Duplicate distinction | duplicates / knowledge | Read-only fingerprint/lexical evidence; semantic decision remains host judgment |
| Metadata-only bounded discovery | ingest.discover / knowledge/integrations | Depth/page truncation, no bytes/hash until selection; caller overrides reject |
| Selected originals, extraction and coverage | original.inspect / knowledge | Raw bytes and actual synthetic PDF text; compressed stream budget; OCR/deferred outcomes |
| File/text/structured identity and quarantine | ingest.draft, ingest.prevalidate / knowledge | Raw identity vs text; escaped delimiters/attributes; provider/account/list/item identity; renamed originals keep identity and repair the locator through review |
| Read-only external capture | integrations / knowledge | Initial completed status, reviewed safe updates, persisted local-edit conflicts, date-only deadline and account separation; no write-back |
| Readiness and capability routing | integrations.status, capability / integrations | Disabled/unavailable and recursive secret policy; private bindings and fixed adapters |
| Location/route privacy and provenance | capability / integrations | Context fingerprint/TTL, transit vs work estimate, persistent provider data forbidden |
| Calendar/map projections | capability / integrations | Read-only observed commitments and permitted coordinates; desktop/account acceptance separate |
| Morning calibration and roadmap priority | plan / daily | Fresh commitments, late-day boundary, native user timeblock collision avoidance and consistent records |
| Inert evening prototype | stage / daily | Task bytes unchanged until approved calibration; separate staging receipt |
| Learning, rollover and Starter Wedge | audit / daily | Completed session learned once; old task wedge not duplicated |
| Ultradian/low-energy/weekend planning | plan, gap-fillers, business-buffer / daily | Bounded duration, low-friction slump support, collision avoidance and business-day buffer |
| Four pauses and re-entry | pause, resume / daily | Preserved notes, plugin sessions, learning and user timeblocks; flow blocks planning |
| Entry and fallback receipts | daily.begin, daily.gate / daily | Entry alone does not suppress; real audit/staging result required |
| Six-point integrity gate | doctor / diagnostics | Fresh prepared vault; invalid schema/timezone/links/skills/multipliers block |
| Environment assessment | environment / environment | Bounded read-only observations; neutral alias in reviewed record |
| Resource ownership and recovery | native onboard/repair / maintenance | Exact staged hashes, collisions, final marker and missing-resource repair preserving edits |
| Code lifecycle | Pi package manager / maintenance | Local/npm/Git package acceptance; no custom installer or vault deletion |
| Native host policy | Pi extension / all | Actual seven-skill loading and tool calls without separate interpreter; bypass denied |

Tests prove deterministic boundaries and native transport. They do not prove semantic judgment, model conversation, real account authentication or desktop rendering. No UI/account success is inferred from a clean package or a successful schema test.
