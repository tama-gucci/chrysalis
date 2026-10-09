import { accessToken } from "../auth/google.ts";
import { providerJSON } from "../http.ts";
import { requestBudget } from "../profile.ts";
import { observation, SLEEP_SCOPE } from "../contracts.ts";
import { serialize } from "../../time/timezone.ts";
import { configuredZone } from "../../core/runtime.ts";
import { Temporal } from "@js-temporal/polyfill";
import type { Instance, ProviderPorts } from "../contracts.ts";
import type { RuntimeContext, Metadata } from "../../contracts/types.ts";

export function normalizeSleep(
  ctx: RuntimeContext,
  rows: Metadata[],
  complete: boolean,
) {
  const zone = configuredZone(ctx),
    sleeps: Metadata[] = [];
  let omitted = 0;
  for (const point of rows) {
    const s = point.sleep;
    if (!s) {
      omitted++;
      continue;
    }
    const minutes = Number(s.summary?.minutesAsleep);
    if (
      !s.interval?.startTime ||
      !s.interval?.endTime ||
      !["number", "string"].includes(typeof s.summary?.minutesAsleep) ||
      !Number.isFinite(minutes) ||
      minutes < 0 ||
      minutes > 1440 ||
      s.metadata?.processed !== true
    ) {
      omitted++;
      continue;
    }
    let start: Temporal.Instant, end: Temporal.Instant;
    try {
      start = Temporal.Instant.from(s.interval.startTime);
      end = Temporal.Instant.from(s.interval.endTime);
    } catch {
      omitted++;
      continue;
    }
    if (
      end.epochMilliseconds <= start.epochMilliseconds ||
      minutes * 60000 > end.epochMilliseconds - start.epochMilliseconds + 60000
    )
      throw Error("provider_invalid_sleep");
    sleeps.push({
      minutes_asleep: minutes,
      start: serialize(start, zone),
      end: serialize(end, zone),
      main_sleep: s.metadata?.mainSleep === true,
      source_start_offset: s.interval.startUtcOffset ?? null,
      source_end_offset: s.interval.endUtcOffset ?? null,
    });
  }
  const unique = [
    ...new Map(sleeps.map((s) => [s.start + "/" + s.end, s])).values(),
  ].sort((a, b) => Temporal.Instant.compare(b.end, a.end));
  const main = unique.filter((s) => s.main_sleep);
  const age = main.length
    ? (Temporal.Instant.from(ctx.now ?? Temporal.Now.instant().toString())
        .epochMilliseconds -
        Temporal.Instant.from(main[0].end).epochMilliseconds) /
      3600000
    : null;
  return {
    status: age === null ? "empty" : age > 36 || age < 0 ? "stale" : "ok",
    timezone: zone,
    latest_sleep: main[0] ?? null,
    baseline_minutes:
      complete && !omitted && main.length >= 8
        ? main.slice(1).reduce((n, s) => n + s.minutes_asleep, 0) /
          (main.length - 1)
        : null,
    coverage: {
      complete: complete && !omitted,
      observed_sessions: unique.length,
      valid_main_sessions: main.length,
      omitted_sessions: omitted,
      latest_age_hours: age,
    },
    interpretation:
      "Device sleep evidence; confirm actual wake and energy with the user. No readiness score.",
    usage_policy: {
      audience: "native_operator_only",
      persistence: "memory_only",
      model_disclosure: false,
    },
  };
}
export async function morningEvidence(
  ctx: RuntimeContext,
  instance: Instance,
  ports: ProviderPorts,
) {
  if (
    instance.provider !== "google-health" ||
    !instance.health_project_eligible ||
    !instance.scopes.includes(SLEEP_SCOPE)
  )
    throw Error("health_access_unavailable");
  const token = await accessToken(ctx, instance, ports.secrets);
  await requestBudget(ctx, instance);
  const identity = await providerJSON(
    ctx,
    ports,
    "https://health.googleapis.com/v4/users/me/identity",
    { headers: { Authorization: "Bearer " + token } },
  );
  if (
    typeof identity.healthUserId !== "string" ||
    !/^[A-Za-z0-9-]{1,63}$/.test(identity.healthUserId)
  )
    throw Error("health_identity_unavailable");
  const end = Temporal.Instant.from(ctx.now ?? new Date().toISOString()),
    start = end.subtract({ hours: 35 * 24 });
  const url = new URL(
    "https://health.googleapis.com/v4/users/me/dataTypes/sleep/dataPoints:reconcile",
  );
  url.searchParams.set("pageSize", "25");
  url.searchParams.set(
    "filter",
    `sleep.interval.end_time >= "${start.toString()}" AND sleep.interval.end_time < "${end.toString()}"`,
  );
  let next: string | undefined,
    rows: Metadata[] = [];
  for (let page = 0; page < 4; page++) {
    if (next) url.searchParams.set("pageToken", next);
    await requestBudget(ctx, instance);
    const result = await providerJSON(ctx, ports, url.href, {
      headers: { Authorization: "Bearer " + token },
    });
    if (
      !Array.isArray(result.dataPoints ?? []) ||
      (result.dataPoints?.length ?? 0) > 25
    )
      throw Error("provider_invalid_response");
    rows.push(...(result.dataPoints ?? []));
    next = result.nextPageToken;
    if (next && (typeof next !== "string" || next.length > 500))
      throw Error("provider_invalid_response");
    if (!next) break;
  }
  return observation(
    ctx,
    instance,
    "health.morning_context",
    normalizeSleep(ctx, rows, !next),
  );
}
