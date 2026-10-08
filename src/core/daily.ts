import { Temporal } from "@js-temporal/polyfill";
import { configuredZone } from "./runtime.ts";
import {
  collection,
  readRecord,
  change,
  parse,
  serializeRecord,
} from "../storage/records.ts";
import { confined, exists, sha256 } from "../platforms/filesystem.ts";
import {
  stamp,
  serialize,
  dateOnly,
  instant,
  zoneName,
  nativeTimeblockInterval,
} from "../time/timezone.ts";
import type {
  RuntimeContext,
  Metadata,
  Change,
  Observation,
} from "../contracts/types.ts";

const clone = <T>(value: T): T => structuredClone(value);
const minute = 60000;
const startMarker = "<!-- chrysalis:focus:start -->",
  endMarker = "<!-- chrysalis:focus:end -->";
function zone(ctx: RuntimeContext, value: string) {
  if (zoneName(value) !== configuredZone(ctx))
    throw new Error("Timezone must match the selected vault Memory");
  return configuredZone(ctx);
}
export function pauseGate(
  memory: Metadata,
  current: Temporal.ZonedDateTime,
  cycle: string,
) {
  const pause = memory.system_state?.pause_state;
  if (!pause?.is_paused) return;
  const pausedDate = pause.paused_at
    ? stamp(pause.paused_at, current.timeZoneId, false).toPlainDate().toString()
    : current.toPlainDate().toString();
  const ready =
    (pause.mode === "maintenance" && cycle === "evening") ||
    (pause.mode === "rest" && current.toPlainDate().toString() > pausedDate) ||
    (pause.mode === "vacation" &&
      current.toPlainDate().toString() >=
        (pause.resume_target ?? "9999-12-31"));
  if (!ready)
    throw new Error("paused: review an explicit resume before this cycle");
}
export function tasks(ctx: RuntimeContext, archived = false) {
  const rows = collection(ctx.vault, "tasks", 500);
  if (archived) rows.push(...collection(ctx.vault, "archive", 500));
  if (rows.length > 500) throw new Error("Narrow task selection");
  return rows;
}
function replaceFocus(body: string, projection: string) {
  const a = body.indexOf(startMarker),
    b = body.indexOf(endMarker);
  if (a >= 0 && b > a)
    return (
      body.slice(0, a) +
      projection +
      body.slice(b + endMarker.length).replace(/^\n+/, "")
    );
  if (a >= 0 || b >= 0)
    throw new Error("Malformed focus markers; review the daily note");
  return projection + "\n" + body;
}
export function plan(
  ctx: RuntimeContext,
  args: Metadata,
): { changes: Change[]; blocks: Metadata[] } {
  const { wake, energy, calendar, selected, not_before } = args;
  const timezone = zone(ctx, args.timezone ?? configuredZone(ctx));
  if (!Number.isInteger(energy) || energy < 1 || energy > 5)
    throw new Error("Energy must be an integer from 1 to 5");
  const w = stamp(wake, timezone),
    date = w.toPlainDate().toString(),
    current = instant(
      ctx.now ?? Temporal.Now.instant().toString(),
    ).toZonedDateTimeISO(timezone);
  const earliest = not_before
    ? stamp(not_before, timezone)
    : current.toPlainDate().toString() === date &&
        current.epochMilliseconds > w.epochMilliseconds
      ? current
      : w;
  if (
    earliest.toPlainDate().toString() !== date ||
    earliest.epochMilliseconds < w.epochMilliseconds
  )
    throw new Error(
      "Remaining-day boundary must follow waking on the same day",
    );
  if (
    !calendar ||
    !["ok", "empty"].includes(calendar.status) ||
    calendar.freshness !== "fresh" ||
    !calendar.observed_at
  )
    throw new Error(
      "calendar_unknown: fresh observation timestamp required, including an explicit empty calendar",
    );
  const observed = instant(calendar.observed_at).epochMilliseconds,
    now = instant(
      ctx.now ?? Temporal.Now.instant().toString(),
    ).epochMilliseconds;
  const age = (now - observed) / 1000,
    maxAge = calendar.max_age_seconds ?? 3600;
  if (
    typeof maxAge !== "number" ||
    maxAge < 60 ||
    maxAge > 86400 ||
    age < -60 ||
    age > maxAge
  )
    throw new Error("calendar_unknown: stale observation");
  const memoryRecord = readRecord(ctx.vault, "System/Memory.md"),
    memory = clone(memoryRecord.frontmatter);
  pauseGate(memory, w, "morning");
  const roadmap = readRecord(ctx.vault, "System/Life-Roadmap.md").frontmatter;
  const active = new Set(memory.active_horizons?.active_projects ?? []),
    roadmapTasks = new Set(
      (roadmap.milestones ?? [])
        .filter((m) => !["done", "archived"].includes(m.status))
        .map((m) => m.task_ref),
    );
  const all = tasks(ctx);
  let candidates = all;
  if (selected !== undefined) {
    if (
      !Array.isArray(selected) ||
      selected.some((p) => !all.some((r) => r.path === p))
    )
      throw new Error("Unknown selected task");
    candidates = all.filter((r) => selected.includes(r.path));
  }
  const weekend = w.dayOfWeek >= 6,
    horizon = w.toPlainDate().add({ days: 14 }).toString();
  let eligible = candidates.filter(({ frontmatter: fm }) => {
    if (
      !["todo", "in-progress"].includes(fm.status) ||
      fm.archived ||
      fm.review_required ||
      fm.date_uncertain ||
      fm.isBlocked ||
      (fm.blockedBy?.length ?? 0) > 0
    )
      return false;
    const due = String(fm.due ?? "").slice(0, 10);
    if (
      selected === undefined &&
      (fm.horizon_bucket === "future" || (due && due > horizon))
    )
      return false;
    if (weekend && (fm.institutional || fm.modality === "administrative"))
      return false;
    if (
      energy <= 2 &&
      ((fm.urgency_tier ?? 2) >= 3 ||
        !["kinetic", "administrative"].includes(fm.modality) ||
        fm.friction !== "low" ||
        fm.energy === "high")
    )
      return false;
    return true;
  });
  const priorities = { urgent: 0, high: 1, normal: 2, low: 3, none: 4 },
    friction = { low: 0, medium: 1, high: 2 };
  const rank = (row: Observation) => {
    const fm = row.frontmatter,
      due = String(fm.due ?? "9999-12-31").slice(0, 10);
    const strategic =
      roadmapTasks.has("[[" + row.path.slice(0, -3) + "]]") ||
      ((fm.projects ?? []).some((p) => active.has(p)) && due <= horizon);
    return [
      strategic ? 0 : 1,
      priorities[fm.priority] ?? 2,
      due,
      friction[fm.friction] ?? 1,
      row.path,
    ];
  };
  eligible.sort((a, b) => {
    const x = rank(a),
      y = rank(b);
    for (let i = 0; i < x.length; i++) {
      if (x[i] === y[i]) continue;
      return x[i] < y[i] ? -1 : 1;
    }
    return 0;
  });
  if (eligible.length)
    eligible =
      weekend || energy <= 2
        ? [eligible[0]]
        : [
            eligible[0],
            ...eligible
              .slice(1)
              .filter((r) => (r.frontmatter.urgency_tier ?? 2) <= 2)
              .slice(0, 2),
          ];
  const relative = "Daily/" + date + ".md",
    old = exists(confined(ctx.vault, relative))
      ? readRecord(ctx.vault, relative)
      : null;
  const occupied: Array<[number, number]> = [];
  for (const block of old?.frontmatter.timeblocks ?? []) {
    if (String(block.id).startsWith("chrysalis-")) continue;
    const blockZone = old?.frontmatter.planning_timezone ?? timezone;
    const [a, b] = nativeTimeblockInterval(
      date,
      block.startTime,
      block.endTime,
      blockZone,
    );
    occupied.push([a, b + 15 * minute]);
  }
  for (const event of calendar.events ?? []) {
    const a = stamp(event.start, timezone, false).epochMilliseconds,
      b = stamp(event.end, timezone, false).epochMilliseconds;
    const buffer = event.travel_minutes ?? (event.location ? 30 : 0);
    if (
      b <= a ||
      typeof buffer !== "number" ||
      !Number.isFinite(buffer) ||
      buffer < 0
    )
      throw new Error("Invalid calendar interval or travel buffer");
    occupied.push([a - buffer * minute, b + 15 * minute]);
  }
  const blocks: Metadata[] = [],
    changes: Change[] = [];
  let deepRemaining = 239;
  const midnight = w.toPlainDate().add({ days: 1 }).toZonedDateTime({
    timeZone: timezone,
    plainTime: "00:00",
  }).epochMilliseconds;
  const cutoff = Math.min(w.epochMilliseconds + 12 * 60 * minute, midnight);
  const format = (ms: number) =>
    serialize(Temporal.Instant.fromEpochMilliseconds(ms), timezone);
  for (const row of eligible) {
    const fm = row.frontmatter,
      modality = fm.modality ?? "administrative",
      offset =
        energy <= 2
          ? 390
          : ({
              analytical: 90,
              administrative: 390,
              kinetic: 465,
              synthesis: 510,
            }[modality] ?? 390);
    let start = Math.max(
        w.epochMilliseconds + offset * minute,
        earliest.epochMilliseconds,
      ),
      remaining = Math.min(
        fm.timeEstimate ?? 45,
        energy <= 2 ? 75 : weekend ? 149 : 150,
      );
    if (["analytical", "synthesis"].includes(modality))
      remaining = Math.min(remaining, deepRemaining);
    if (!Number.isFinite(remaining) || remaining <= 0) continue;
    let first: number | undefined;
    while (remaining > 0) {
      let duration = Math.min(75, remaining),
        end = start + duration * minute;
      for (;;) {
        const collision = occupied.find(([a, b]) => start < b && end > a);
        if (!collision) break;
        start = collision[1];
        end = start + duration * minute;
      }
      if (end > cutoff) {
        duration = Math.min(duration, (cutoff - start) / minute);
        if (duration <= 0) break;
        end = start + duration * minute;
      }
      first ??= start;
      blocks.push({ task: row.path, start: format(start), end: format(end) });
      occupied.push([start, end + (energy <= 2 ? 22.5 : 15) * minute]);
      remaining -= duration;
      if (["analytical", "synthesis"].includes(modality))
        deepRemaining -= duration;
      start = end + (energy <= 2 ? 22.5 : 15) * minute;
    }
    if (first !== undefined)
      changes.push(change(row, { ...fm, scheduled: format(first) }));
  }
  const scheduled = new Set(blocks.map((b) => b.task));
  for (const row of all)
    if (
      !scheduled.has(row.path) &&
      row.frontmatter.scheduled &&
      String(row.frontmatter.scheduled).slice(0, 10) === date
    )
      changes.push(change(row, { ...row.frontmatter, scheduled: null }));
  memory.morning_checkin ??= {};
  memory.morning_checkin.learned_rhythms ??= {};
  const baseline = memory.morning_checkin.learned_rhythms.wake_minutes ?? 540;
  memory.morning_checkin.learned_rhythms.wake_minutes =
    Math.round((baseline + 0.15 * (w.hour * 60 + w.minute - baseline)) * 100) /
    100;
  memory.morning_checkin.active_today = {
    date,
    wake: serialize(w, timezone),
    energy,
  };
  memory.system_state ??= {};
  memory.system_state.pause_state = { is_paused: false, mode: null };
  memory.prototype_schedule = {
    target_date: date,
    planning_timezone: timezone,
    feedback_status: "approved",
    blocks,
  };
  changes.push(change(memoryRecord, memory));
  const timeblocks = [
    ...(old?.frontmatter.timeblocks ?? []).filter(
      (b) => !String(b.id).startsWith("chrysalis-"),
    ),
    ...blocks.map((b, index) => ({
      id: "chrysalis-" + date + "-" + index,
      title: all.find((t) => t.path === b.task)!.frontmatter.title,
      startTime: b.start.slice(11, 16),
      endTime: b.end.slice(11, 16),
      attachments: ["[[" + b.task.slice(0, -3) + "]]"],
    })),
  ];
  const fm = {
    ...(old?.frontmatter ?? {}),
    type: "daily_note",
    date,
    planning_timezone: timezone,
    wake_time: serialize(w, timezone),
    energy_level: energy,
    energy_mode: energy <= 2 ? "sleep_deprived" : "optimal",
    tags: old?.frontmatter.tags ?? ["daily-note"],
    blocks,
    timeblocks,
  };
  const projection = [
    startMarker,
    "# Daily focus",
    "",
    "| Start | End | Task |",
    "|---|---|---|",
    ...blocks.map(
      (b) =>
        "| " + b.start + " | " + b.end + " | [[" + b.task.slice(0, -3) + "]] |",
    ),
    endMarker,
    "",
  ].join("\n");
  changes.push({
    path: relative,
    if_revision: old?.revision ?? null,
    document: serializeRecord(fm, replaceFocus(old?.body ?? "", projection)),
  });
  return { changes, blocks };
}
export function stage(ctx: RuntimeContext, args: Metadata) {
  const memory = readRecord(ctx.vault, "System/Memory.md"),
    result = plan(ctx, args),
    planned = result.changes.find((c) => c.path === memory.path)!;
  const prototype = parse(planned.document).frontmatter.prototype_schedule;
  prototype.feedback_status = "pending";
  return {
    changes: [
      change(memory, { ...memory.frontmatter, prototype_schedule: prototype }),
    ],
    blocks: result.blocks,
  };
}
export function audit(ctx: RuntimeContext, args: Metadata) {
  const timezone = zone(ctx, args.timezone ?? configuredZone(ctx)),
    current = stamp(args.now, timezone),
    record = readRecord(ctx.vault, "System/Memory.md"),
    memory = clone(record.frontmatter);
  pauseGate(memory, current, "evening");
  if (
    ["maintenance", "vacation"].includes(memory.system_state?.pause_state?.mode)
  )
    memory.system_state.pause_state = { is_paused: false, mode: null };
  memory.learned_sessions ??= {};
  memory.cognitive_modality_defaults ??= {};
  const changes: Change[] = [],
    learned: string[] = [],
    warnings: Metadata[] = [];
  for (const row of tasks(ctx, true)) {
    const fm = row.frontmatter,
      updated = clone(fm);
    let body = row.body;
    let sessions = fm.timeEntries ?? [];
    if (!sessions.length && fm.startedAt && fm.completedAt)
      sessions = [{ startTime: fm.startedAt, endTime: fm.completedAt }];
    for (const session of sessions) {
      if (!session.endTime || fm.status !== "done") continue;
      try {
        const start = instant(session.startTime).epochMilliseconds,
          end = instant(session.endTime).epochMilliseconds,
          estimate = fm.timeEstimate ?? 0;
        if (end <= start || end > current.epochMilliseconds || estimate <= 0)
          throw new Error("Invalid session");
        if (current.epochMilliseconds - end > 24 * 60 * minute) continue;
        const id = sha256(
          String(fm.id ?? row.path + "|" + fm.dateCreated) +
            "|" +
            session.startTime +
            "|" +
            session.endTime,
        );
        if (memory.learned_sessions[id]) continue;
        const modality = fm.modality ?? "administrative",
          duration = (end - start) / minute,
          m = memory.cognitive_modality_defaults[modality]?.multiplier ?? 1;
        memory.cognitive_modality_defaults[modality] = {
          ...(memory.cognitive_modality_defaults[modality] ?? {}),
          multiplier:
            Math.round(
              Math.max(0.2, Math.min(2, m + 0.1 * (duration / estimate - m))) *
                100,
            ) / 100,
        };
        memory.learned_sessions[id] = {
          task: row.path,
          start: session.startTime,
          end: session.endTime,
          duration,
        };
        learned.push(id);
      } catch {
        warnings.push({
          path: row.path,
          code: "invalid_session_review_required",
        });
      }
    }
    if (fm.status === "todo" && !fm.archived) {
      if (
        fm.scheduled &&
        String(fm.scheduled).slice(0, 10) <= current.toPlainDate().toString()
      )
        updated.scheduled = null;
      try {
        const age =
          current.epochMilliseconds -
          stamp(fm.dateCreated, timezone, false).epochMilliseconds;
        if (
          age >= 48 * 60 * minute &&
          (fm.timeEstimate ?? 0) >= 45 &&
          !fm.micro_chunked
        ) {
          updated.micro_chunked = true;
          body +=
            "\n\n## Starter Wedge\n- [ ] Open the materials (under 15 minutes)\n- [ ] Do the smallest concrete sub-action (under 15 minutes)\n- [ ] Continue or record the next obstacle\n";
        }
      } catch {
        warnings.push({ path: row.path, code: "invalid_task_age" });
      }
    }
    if (JSON.stringify(updated) !== JSON.stringify(fm))
      changes.push(change(row, updated, body));
  }
  memory.system_state ??= {};
  memory.system_state.pause_state ??= {};
  const pause = memory.system_state.pause_state,
    prototype = memory.prototype_schedule ?? {};
  if (
    prototype.feedback_status === "pending" &&
    (prototype.target_date ?? "9999-12-31") <=
      current.toPlainDate().toString() &&
    !pause.is_paused
  )
    Object.assign(pause, {
      is_paused: true,
      mode: "auto_unresponsive",
      reason: "unreviewed_previous_cycle",
      paused_at: serialize(current, timezone),
    });
  changes.push(change(record, memory));
  return { changes, result: { learned_sessions: learned, warnings } };
}
export function pause(ctx: RuntimeContext, args: Metadata) {
  const timezone = zone(ctx, args.timezone ?? configuredZone(ctx)),
    current = stamp(args.now, timezone),
    mode = args.mode;
  if (!["maintenance", "rest", "flow", "vacation", "resume"].includes(mode))
    throw new Error("Unknown pause mode");
  const date = current.toPlainDate().toString();
  if (
    mode === "vacation" &&
    (!args.until || dateOnly(args.until).toString() < date)
  )
    throw new Error("Vacation requires a future resume date");
  const record = readRecord(ctx.vault, "System/Memory.md"),
    memory = clone(record.frontmatter);
  const target = {
    maintenance: "evening",
    rest: "morning",
    flow: null,
    vacation: args.until,
    resume: null,
  }[mode];
  memory.system_state ??= {};
  memory.system_state.pause_state = {
    is_paused: mode !== "resume",
    mode: mode === "resume" ? null : mode,
    paused_at: serialize(current, timezone),
    resume_target: target,
  };
  if (mode === "maintenance")
    memory.prototype_schedule = { feedback_status: "pending", blocks: [] };
  if (mode === "rest") memory.rest_day = date;
  const changes = [change(record, memory)];
  if (mode !== "resume") {
    for (const row of tasks(ctx))
      if (
        row.frontmatter.scheduled &&
        String(row.frontmatter.scheduled).slice(0, 10) === date
      )
        changes.push(change(row, { ...row.frontmatter, scheduled: null }));
    const relative = "Daily/" + date + ".md";
    if (exists(confined(ctx.vault, relative))) {
      const daily = readRecord(ctx.vault, relative);
      let body = replaceFocus(
        daily.body,
        startMarker +
          "\n# Daily focus\n\nNo active focus blocks.\n" +
          endMarker +
          "\n",
      );
      body +=
        "\n\n> [!WARNING]\n> Paused: " +
        mode +
        "; re-entry: " +
        (target ?? "manual") +
        ".\n";
      changes.push(
        change(
          daily,
          {
            ...daily.frontmatter,
            blocks: [],
            timeblocks: (daily.frontmatter.timeblocks ?? []).filter(
              (b) => !String(b.id).startsWith("chrysalis-"),
            ),
          },
          body,
        ),
      );
    }
  }
  return {
    changes,
    result: {
      resume_target: target,
      reentry:
        current.hour < 12 ? "morning" : current.hour < 18 ? "flex" : "evening",
    },
  };
}
