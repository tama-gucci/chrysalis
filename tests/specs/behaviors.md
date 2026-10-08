# Behavior coverage

The Pi package exposes the canonical families. In the table, `daily`,
`knowledge`, `task`, `diagnostics`, `integrations`, `environment` and `maintenance` mean
`skills/chrysalis-<family>/SKILL.md` and its named references. Pi invokes
`/skill:chrysalis-<family>`. Both call the same `chrysalis_operation` operation.
Legacy section labels below identify the reviewed source behavior; they are not retained runbooks.

Tests named below are in `test_portable_core.py` (C), `test_workflows.py` (W),
`test_discovery.py` (D), `test_providers.py` (P), or `test_review_boundaries.py` (R).
Fixture verification proves the deterministic
boundary. Native acceptance separately exercises actual loaders, tool dispatch and policy in
Pi. Conversation, authenticated provider operation and UI behavior need the acceptance stated
in [status](../../STATUS.md); their unverified state is not a parity claim.

| Legacy entry / source section | Canonical procedure / Pi family | Operation and dependency | Positive and negative evidence / state |
|---|---|---|---|
| audit / pre-flight health; doctor / six-point suite | diagnostics / doctor-checks | doctor; six local schemas | W doctor_read_only_six_checks_and_reviewed_repairs; missing schema/broken links block; fixture verified |
| doctor / diagnostic ledger and repairs | diagnostics / doctor-checks | propose/apply; external approval | W doctor_read_only_six_checks_and_reviewed_repairs; inspection does not write, repair needs receipt; fixture verified |
| audit / lifecycle and modality learning | daily / evening-audit-protocol | audit; observed timeEntries | C learning_once_and_pause_modes; invalid timing adds no learning; fixture verified |
| audit / chronotype learning; calibrate / telemetry | daily / morning-protocol | plan; wake/energy and fresh calendar | C plan_energy_calendar_and_consistent_records; W timezone_and_calendar_observation_not_caller_booleans; fixture verified |
| audit / Starter Wedge and rollover | daily / evening-audit-protocol | audit; task age and estimate | W starter_wedge_rollover_and_wake_learning_have_observed_boundaries; recent/invalid sessions excluded, repeated wedge not duplicated; fixture verified |
| audit / all configured sources; evening / audit then staging | daily / evening-audit-protocol plus knowledge / ingestion-pipeline | ingest.discover, horizon, graph, stage | D metadata_discovery_does_not_read_original_bytes; W staging_is_inert_until_feedback_and_cycle_boundary; conversation sequence unverified |
| audit / roadmap updates | daily / evening-audit-protocol | read/propose/apply; confirmed outcomes | W project_integration_and_checkpoint_use_one_reviewed_set; arbitrary mutation denied; deterministic write boundary verified, outcome interpretation needs conversation |
| morning / check-in and missing response; calibrate / pause check | daily / morning-protocol, daily-entry | daily.begin, plan; explicit input | W pause_reentry_and_onboarding_receipt_resume; no response invokes no writer; pause transitions fixture verified, natural-language check-in unverified |
| plan / roadmap-first anchor and gap-fillers | daily / staging-protocol | gap-fillers, stage, plan; roadmap + active horizons | C plan_energy_calendar_and_consistent_records; blocked/uncertain/future exclusions; fixture verified |
| plan / modality windows, ultradian breaks, low energy and weekends | daily / morning-protocol | plan; local timezone | C plan_energy_calendar_and_consistent_records, weekend_business_buffer_dst; W late_day_boundary_never_schedules_past_blocks; R aggregate_deep_work_and_low_energy_limits: weekday deep work below 4h, one low-friction low-energy slump support, single rest buffers; fixture verified |
| plan / Calendar and transit collisions | daily / morning-protocol | plan; fresh observed commitments | W timezone_and_calendar_observation_not_caller_booleans; P DST/travel/TTL cases; stale/unknown blocks; fixture verified, live calendar unverified |
| plan / prototype feedback and no response | daily / staging-protocol | stage then audit; exact proposal | W staging_is_inert_until_feedback_and_cycle_boundary; staged blocks remain inert, next-cycle pause; fixture verified, conversation approval unverified |
| evening / pause gate; pause / four modes and re-entry | daily / pause-resume-protocol | pause/resume/audit/plan | C learning_once_and_pause_modes; W pause_reentry_and_onboarding_receipt_resume; multipliers preserved and blocked mode cannot plan; fixture verified |
| pause / task sanitation and Daily annotation | daily / pause-resume-protocol | pause; approved CAS batch | W pause_clears_rendered_focus_but_preserves_user_daily_notes; timestamps and rendered blocks cleared, personal note body preserved; fixture verified |
| evening / eligibility and manual retry | daily / daily-entry | daily.begin/gate, audit/stage result receipts | C real_result_receipts_and_manual_retry; W pause_reentry_and_onboarding_receipt_resume; R morning_calibration_does_not_suppress_evening_but_stage_does; entry/calibration alone never suppress fallback, tampering fails; fixture verified, no live job installed |
| task / shorthand metadata and classification | task / task-schema, velocity-multiplier | task.draft; confirmed fields | W task_capture_and_horizon_preserve_full_ledger; standalone task has no fabricated parent; fixture/native calls verified, language interpretation unverified |
| task / plugin conventions | task / task-schema, cas-mutation | schema/validate/propose/apply | C tasknotes_roundtrip_and_unknown_properties, calendar_ownership; R native_manual_order_daily_pomodoros_and_utc_timestamp_survive; unknown fields reject, native fields/Calendar ownership preserved; fixture verified, UI rendering/sync unverified |
| project / intake, scaffolding and staging | knowledge / project-roadmap-spec | template/propose/apply; synthetic project schema | W project_integration_and_checkpoint_use_one_reviewed_set; staged project requires reviewed activation; fixture verified, scoping conversation unverified |
| project / Life-Roadmap integration and 14-day tasks | knowledge / project-roadmap-spec | horizon/propose; registered pillar | W task_capture_and_horizon_preserve_full_ledger, project_integration_and_checkpoint_use_one_reviewed_set; future deliverables stay ledger-only; fixture verified |
| project / catalog and status | knowledge / project-roadmap-spec | project.status, query | W project_integration_and_checkpoint_use_one_reviewed_set; explicit status/progress from records; fixture verified |
| zettel / atomic synthesis, grounding and reciprocal links | knowledge / zettelkasten-guide | schema/template/propose, graph | W graph_routes_approved_reciprocal_links; missing target rejects; fixture/native graph calls verified, synthesis quality unverified |
| ingest / bounded multi-source discovery | knowledge / ingestion-pipeline | ingest.discover; explicit private bindings | D both tests; zero content reads and partial depth listing not empty success; fixture verified, real streamed mount unverified |
| ingest / extraction, format coverage and quarantine | knowledge / ingestion-pipeline, quarantine-security | original.inspect, ingest.draft | W ingestion_raw_identity_links_quarantine_and_relocation, original_preview_limits_and_fingerprint_masquerade; real synthetic PDF parsed, complete PNG classified OCR-required, opaque asset deferred; OCR/vision unverified |
| ingest / raw, normalized and structured identity | knowledge / ingestion-pipeline | ingest.draft, ingest.prevalidate | W ingestion_raw_identity_links_quarantine_and_relocation; binary/text masquerade rejects, repeat import inert; fixture/native ingest calls verified |
| ingest / semantic duplicate distinction | knowledge / ingestion-pipeline | duplicates; host semantic judgment | W semantic_candidate_evidence_never_merges_or_writes; candidates do not merge; deterministic evidence verified, semantic judgment unverified |
| ingest / additive deadlines and reconciliation | knowledge / ingestion-pipeline | project.reconcile, horizon | W additive_project_reconciliation_preserves_done_and_omissions, task_capture_and_horizon_preserve_full_ledger; partial inputs cannot erase records; fixture verified |
| ingest / prevalidate, approval, resumable apply and verify | knowledge / ingestion-pipeline | validate/propose/apply; strict validator | C exact_approval_and_body_only_conflict, partial_apply_retry_and_postimages; W fresh_process_missing_validator_cannot_write; fixture/native apply calls verified |
| onboard / conversational onboarding | knowledge / onboarding, goal-discovery | environment, template, read, propose, daily.begin | W project_integration_and_checkpoint_use_one_reviewed_set, pause_reentry_and_onboarding_receipt_resume; exact checkpoint and resumable invocation; deterministic persistence verified, interview/research/handoff conversation unverified |
| google-drive / activation and read-only transports | integrations / providers; knowledge / ingestion-pipeline | integrations.status, ingest.discover | D metadata_discovery_does_not_read_original_bytes; W templates_queries_and_unavailable_capability; unavailable is explicit; normalization/mount fixtures verified, authenticated API unverified |
| google-drive / provider IDs, revisions and pagination | integrations / providers | ingest.discover/draft; normalized provider response | W ingestion_raw_identity_links_quarantine_and_relocation; D partial page/depth cases; no invented cloud ID; fixture verified, live revision changes unverified |
| google-tasks / one-way identity and deadlines | integrations / providers; knowledge / ingestion-pipeline | capability/ingest.draft; structured_task | W structured_task_repeat_import_preserves_completed_local_work; read-only contract and local edit conflict; fixture verified, authenticated capture unverified |
| google-maps / ambiguity, privacy and policy | integrations / providers | location.resolve, routing.estimate; private binding | P ambiguity, outbound privacy, policy filter, malformed response tests; normalization/policy fixture verified, authenticated lookup unverified |
| google-maps / contextual routing and stale data | integrations / providers | routing.estimate; freshness/permissions | P route arithmetic, stale multi-hop, DST and TTL tests; travel separate from work estimate; fixture verified, actual routes unverified |
| obsidian-maps / ownership and permitted projection | integrations / providers | visualization.map_projection | P coordinate ownership and Google policy filtering; forbidden provider coordinates do not project; fixture verified, plugin UI unverified |
| update / package lifecycle | maintenance / package-lifecycle | operator package install/remove/rollback | C package_update_collision_remove_rollback; W package_failure_restores_owned_files_and_rejects_manifest_escape; learned/unowned edits preserved, recovery verified |
| shared anti-simulation, explicit vault, timezone and approval invariants | every family | versioned shared core; external operator approval | C tampering_and_wrong_root, explicit_roots_case_and_confinement, noncooperating_editor_during_mutator; fixture and native policy calls verified |

Environment observations support onboarding without installing dependencies. Optional host memory
remains external and provider-neutral; native-store/export and combined-loader checks are reported
separately in status. Repository privacy/testing are ordinary engineering gates in
`Development/TESTING.md`, rather than runtime skills.

Independent-review regressions also cover one-buffer document/revision observations, apply-time
link/taxonomy checks, zero-write rejection of forbidden package ancestry, escaped quarantine
metadata, selected-original hash/extraction consistency, compressed PDF stream limits, structured
Daily time/task references, trusted provider configuration and honest fixture/authentication states
in R. These are deterministic boundary checks; future harness adapters must reuse them.
R also checks ordinary deep Windows state/package paths, prefixed-path containment and
conflicting environment/explicit state bindings without leaking locks into vault or package.
