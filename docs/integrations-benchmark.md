# Codemode measurement

The retained codemode test uses the actual Pi 1.0.4 sandbox and the shared Tasks provider service
with an in-process synthetic MCP-shaped wrapper. Production stdio reachability and nested gating
are tested separately by pi.test.ts. No account or model API is used.

The user-selected result is the subset whose synthetic title starts with Chosen. Direct calls
return the same bounded pages; the model would then perform that selection. Codemode selects in
the sandbox. Equal reduced items, provider coverage/cursors, provenance and explicit unavailable
results are asserted for small, large/paginated and partial-failure scenarios.

The comparison includes all six direct source declarations versus a codemode declaration, request
names/arguments, script text, model-visible result content and cold describeTool discovery. Warm
runs reuse a previously discovered schema, still counting declarations and the current script/
result. Common life-profile declarations are omitted on both sides. MCP content is counted once;
its duplicate structured representation is not another model-visible result. Pi estimateTokens
uses characters divided by four, so these figures are context estimates rather than tokenizer,
billing, latency or semantic-quality measurements. Cache/provider pricing is not modeled.

| Synthetic selection                               | Direct six-tool namespace | Cold codemode | Warm codemode |
| ------------------------------------------------- | ------------------------: | ------------: | ------------: |
| Two short summaries, select one                   |                       993 |           677 |           535 |
| Two pages of 100 long-title summaries, select two |                    29,134 |           956 |           814 |
| Same pages plus one unavailable inbox             |                    29,177 |           981 |           839 |

The large dataset intentionally stresses output size with roughly 384-character synthetic titles;
its approximately 97% reduction is not an expected saving for every inbox. Narrowing direct tool
declarations or provider requests can reduce the baseline substantially. The test also records a
single-tool direct baseline for comparison; a small already-narrow request may favor direct calls.
Backend summary-first/selected-details behavior is an independent optimization available to both
paths. Use codemode when joining/filtering materially large observations, rather than assuming
that JavaScript is cheaper for every one-step request. Health and Maps return non-content native
review status, so these measurements do not claim savings for model-visible Health/Maps metrics.

Raw measurement receipts and fixture paths remain outside source. Tests reproduce the method;
changes to schemas or host descriptions may change the estimates without changing correctness.
