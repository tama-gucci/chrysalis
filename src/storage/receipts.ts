import { randomUUID } from "node:crypto";
import { vaultState } from "./context.ts";
import {
  confined,
  exists,
  readJSON,
  atomicJSON,
  digest,
  withLock,
} from "../platforms/filesystem.ts";
import { configuredZone } from "../core/runtime.ts";
import { stamp, nowStamp, instant } from "../time/timezone.ts";
import type { RuntimeContext, Metadata } from "../contracts/types.ts";

export function begin(ctx: RuntimeContext, args: Metadata) {
  if (
    ![
      "morning",
      "evening",
      "audit",
      "staging",
      "calibration",
      "check-in",
      "resume",
    ].includes(args.mode)
  )
    throw new Error("Unknown daily entry mode");
  if (args.timezone && args.timezone !== configuredZone(ctx))
    throw new Error("Timezone must match Memory");
  const id = args.invocation_id ?? randomUUID();
  if (!/^[a-f0-9-]{36}$/i.test(id))
    throw new Error("Invalid invocation identity");
  const target = confined(vaultState(ctx), "entries/" + id + ".json");
  if (exists(target)) {
    const entry = readJSON(target);
    if (entry.mode !== args.mode)
      throw new Error("Invocation belongs to another mode");
    return { status: "existing", invocation_id: id, entry };
  }
  atomicJSON(target, {
    mode: args.mode,
    started_at: nowStamp(configuredZone(ctx), ctx.now),
  });
  return { status: "entered", invocation_id: id };
}
export async function saveResult(
  ctx: RuntimeContext,
  stage: string,
  result: Metadata,
) {
  if (
    !["audit", "planning"].includes(stage) ||
    !result ||
    !Object.keys(result).length
  )
    throw new Error("A meaningful result is required");
  const timezone = configuredZone(ctx),
    payload = {
      stage,
      timezone,
      completed_at: nowStamp(timezone, ctx.now),
      result,
    },
    key = digest(payload),
    external = vaultState(ctx);
  atomicJSON(confined(external, "results/" + key + ".json"), payload);
  await withLock(confined(external, "locks"), "daily-ledger", () => {
    const file = confined(external, "daily.json"),
      rows = exists(file) ? readJSON(file) : [];
    rows.push({
      stage,
      timezone,
      completed_at: payload.completed_at,
      result_digest: key,
    });
    atomicJSON(file, rows);
  });
  return key;
}
export function gate(ctx: RuntimeContext, args: Metadata) {
  const timezone = configuredZone(ctx);
  if (args.timezone && args.timezone !== timezone)
    throw new Error("Timezone must match Memory");
  if (!/^(?:[01][0-9]|2[0-3]):[0-5][0-9]$/.test(args.evening_start))
    throw new Error("Explicit evening start required");
  const current = stamp(nowStamp(timezone, ctx.now), timezone),
    file = confined(vaultState(ctx), "daily.json"),
    rows = exists(file) ? readJSON(file) : [];
  let reviewed = false;
  for (const row of rows) {
    if (
      !["audit", "planning"].includes(row.stage) ||
      !/^[a-f0-9]{64}$/.test(row.result_digest)
    )
      throw new Error("Invalid daily result reference");
    const payload = readJSON(
      confined(vaultState(ctx), "results/" + row.result_digest + ".json"),
    );
    if (
      digest(payload) !== row.result_digest ||
      payload.stage !== row.stage ||
      payload.completed_at !== row.completed_at ||
      !payload.result
    )
      throw new Error("Daily result receipt changed");
    const recorded = stamp(row.completed_at, row.timezone ?? timezone, true);
    if (
      recorded.toPlainDate().toString() === current.toPlainDate().toString() &&
      (row.timezone ?? timezone) === timezone
    )
      reviewed = true;
  }
  const eligible =
    String(current.hour).padStart(2, "0") +
      ":" +
      String(current.minute).padStart(2, "0") >=
    args.evening_start;
  return {
    status: "ok",
    wake_agent: !reviewed && eligible,
    reason: reviewed
      ? "reviewed_today"
      : eligible
        ? "eligible"
        : "outside_window",
  };
}
