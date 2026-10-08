# Daily entry and optional fallback

Call `daily.begin` with `mode` and optional matching `timezone` before work. Supply the same
`invocation_id` UUID when recovering that entry; a new UUID starts a new entry. Entry alone never
suppresses fallback. `audit` and `stage` save actual hashed findings/proposals outside the vault
and return `result_digest`. `daily.gate` with `evening_start: "HH:mm"` checks their configured
zone/local date before returning `wake_agent`. Missing/corrupt results fail closed.

Morning calibration through `plan`, doctor and an interrupted audit do not qualify. A saved audit
or staging result can suppress fallback while its proposal still awaits approval; it proves a result
was drafted, not that its records were applied. Manual check-ins remain allowed.

The package registers no scheduler or background launcher. Any separately implemented fallback
must check pause state itself: `daily.gate` does not enforce semantic pauses. Recheck state at
conversation entry. A zero-write rehearsal creates neither entry nor suppression receipts.
