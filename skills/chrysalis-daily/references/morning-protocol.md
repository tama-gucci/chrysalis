# Morning calibration
Read Memory, the roadmap and active task records. Ask for actual wake time, energy 1–5 and changes
to commitments. Missing replies leave the system paused and learning unchanged. A previously
unreviewed prototype needs staging/review before application. Check pause state and resume intent.
Obtain a fresh observed calendar, including observed_at and events (an empty list is valid only when
actually observed). Unknown/stale/unavailable commitments block schedule application; invite the
user to provide a fresh explicit no-calendar observation when no calendar is used.
Call `plan` with wake, energy, configured timezone, calendar and optional selected task paths.
Review every proposed task timestamp, Memory change and Daily record before the operator approves.
The helper uses a .15 rolling wake baseline adjustment, 75-minute focus sprints, 15-minute breaks
(22.5 minutes at low energy), analytical peak +90m, administrative slump +390m, kinetic defrost
+465m and synthesis recovery +510m. It reserves observed commitments and physical transit windows,
shifts collisions forward within the local day, and does not invent routed durations.
Energy 1–2 excludes tiers 3/4 and analytical/synthesis tasks and retains one low-load support task.
That support must have explicitly low friction and must not require high energy; it receives at
most 75 minutes in the slump window. Weekday analytical/synthesis focus totals less than four hours.
Capacity is at most an anchor plus two supports on weekdays and one task on weekends, under 2.5h
weekend focus. Uncertain or blocked tasks need clarification. Calendar identifiers remain unchanged.
Apply the approved digest, read back task/Memory/Daily records, and report exact persisted blocks.
Use Daily/YYYY-MM-DD.md. For late-day entry pass `not_before` with the current local timestamp;
review only feasible remaining work. No block may precede that remaining-day boundary.
