# Daily entry and fallback
Call `daily.begin` with timezone and mode before work. Invocation alone never suppresses fallback.
`audit` and `stage` save actual hashed findings/proposals outside the vault and return their result
digest. `daily.gate` verifies these results, their local dates and offsets before suppressing the
evening fallback. Missing/corrupt results fail closed. Morning entry, doctor alone and an interrupted
audit do not qualify. Morning calibration through `plan` alone does not suppress evening fallback.
Manual reruns remain allowed. Job registration and host launch are separate:
preview a disabled host job that calls the read-only gate at a configured local evening time,
then invokes this skill only when eligible. Recheck at entry. No live job is activated by setup.
A zero-write rehearsal creates neither entry nor suppression receipts; label it clearly.
