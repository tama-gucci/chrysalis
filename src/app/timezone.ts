import { detectTimezone } from "../platforms/timezone.ts";
import { zoneName, nowStamp } from "../time/timezone.ts";
import { readRecord, change } from "../storage/records.ts";
import { propose, configuredZone } from "../core/runtime.ts";
import { vaultState } from "../storage/context.ts";
import {
  confined,
  atomicJSON,
  exists,
  readJSON,
} from "../platforms/filesystem.ts";
import type { RuntimeContext } from "../contracts/types.ts";

export async function timezoneStatus(ctx: RuntimeContext) {
  const file = confined(vaultState(ctx), "timezone-observation.json");
  return {
    status: "ok",
    configured_timezone: configuredZone(ctx),
    last_observation: exists(file) ? readJSON(file) : null,
  };
}
export async function proposeTimezone(ctx: RuntimeContext, manual?: string) {
  const observation = manual
    ? {
        timezone: zoneName(manual),
        observed_at: nowStamp(zoneName(manual), ctx.now),
        source: "operator_selection",
      }
    : await detectTimezone(ctx.signal);
  atomicJSON(
    confined(vaultState(ctx), "timezone-observation.json"),
    observation,
  );
  const current = configuredZone(ctx);
  if (current === observation.timezone)
    return { status: "no_changes", configured_timezone: current, observation };
  const record = readRecord(ctx.vault, "System/Memory.md"),
    memory = structuredClone(record.frontmatter);
  memory.user_profile.timezone = observation.timezone;
  if (memory.prototype_schedule) {
    memory.prototype_schedule.feedback_status = "needs_recalibration";
    memory.prototype_schedule.previous_timezone = current;
  }
  return {
    ...propose(ctx, [change(record, memory)], "timezone_setup"),
    old_timezone: current,
    new_timezone: observation.timezone,
    observation,
    schedules_preserved: true,
  };
}
