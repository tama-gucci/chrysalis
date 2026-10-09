import {
  confined,
  exists,
  readJSON,
  atomic,
  digest,
  raw,
  sha256,
  withLock,
} from "../platforms/filesystem.ts";
import { vaultState } from "../storage/context.ts";
import { readRecord } from "../storage/records.ts";
import type { RuntimeContext } from "../contracts/types.ts";
import { TASKS_SCOPE, SLEEP_SCOPE } from "./contracts.ts";
import type { Instance } from "./contracts.ts";
import { providerLock } from "./locks.ts";

function profilePath(ctx: RuntimeContext) {
  return confined(vaultState(ctx), "integrations.json");
}
export function authorizationDigest(instance: Instance) {
  return digest({ ...instance, verified_at: undefined });
}
export function instances(ctx: RuntimeContext): Instance[] {
  const f = profilePath(ctx);
  if (!exists(f)) return [];
  const data = readJSON(f);
  if (
    data.schema_version !== "1" ||
    !Array.isArray(data.instances) ||
    data.instances.length > 20
  )
    throw Error("invalid_integration_profile");
  for (const i of data.instances) {
    if (
      !/^[a-z0-9][a-z0-9-]{0,63}$/.test(i.id) ||
      !["google-tasks", "google-maps", "google-health"].includes(i.provider) ||
      !/^[a-z0-9-]{8,80}$/.test(i.secret_id) ||
      !Array.isArray(i.list_ids) ||
      i.list_ids.length > 20 ||
      i.list_ids.some((v) => typeof v !== "string" || v.length > 500) ||
      !Array.isArray(i.scopes) ||
      i.scopes.length > 4 ||
      typeof i.enabled !== "boolean" ||
      i.consent_version !== "1" ||
      typeof i.native_only !== "boolean"
    )
      throw Error("invalid_integration_profile");
    if (
      typeof i.account_alias !== "string" ||
      i.account_alias.length > 64 ||
      typeof i.project_id !== "string" ||
      !/^[a-z][a-z0-9-]{4,62}$/.test(i.project_id) ||
      typeof i.health_project_eligible !== "boolean" ||
      (i.provider !== "google-tasks" && i.native_only !== true) ||
      i.scopes.some((s) => typeof s !== "string") ||
      (i.provider === "google-tasks" &&
        (i.scopes.length !== 1 || i.scopes[0] !== TASKS_SCOPE)) ||
      (i.provider === "google-health" &&
        (i.scopes.length !== 1 || i.scopes[0] !== SLEEP_SCOPE)) ||
      (i.provider === "google-maps" && i.scopes.length)
    )
      throw Error("invalid_integration_profile");
  }
  if (new Set(data.instances.map((i) => i.id)).size !== data.instances.length)
    throw Error("invalid_integration_profile");
  return data.instances;
}
/** Native-only caller. Model-facing operations do not export this mutation. */
export async function saveInstance(ctx: RuntimeContext, instance: Instance) {
  return withLock(vaultState(ctx), "provider-profile", () => {
    const file = profilePath(ctx),
      revision = exists(file) ? sha256(raw(file)) : null;
    const rows = instances(ctx).filter((i) => i.id !== instance.id);
    rows.push(instance);
    if (rows.length > 20) throw Error("integration_limit");
    atomic(
      file,
      JSON.stringify({ schema_version: "1", instances: rows }),
      revision,
    );
  });
}
export function authorizedInstance(ctx: RuntimeContext, id: string) {
  const instance = instances(ctx).find((i) => i.id === id);
  if (!instance?.enabled) throw Error("integration_inactive");
  const binding = readRecord(ctx.vault, "System/Memory.md").frontmatter
    .integrations?.instances?.[id];
  if (
    !binding?.enabled ||
    binding.integration !== instance.provider ||
    binding.native_authorization !== authorizationDigest(instance)
  )
    throw Error("integration_binding_needs_review");
  return instance;
}
export async function requestBudget(ctx: RuntimeContext, instance: Instance) {
  await providerLock(ctx, vaultState(ctx), "provider-budget", () => {
    const file = confined(vaultState(ctx), "provider-budgets.json");
    const data = exists(file) ? readJSON(file) : {};
    const day = new Date().toISOString().slice(0, 10),
      prior = data[instance.id];
    const count = prior?.day === day ? prior.count : 0;
    if (!Number.isInteger(count) || count < 0 || count >= 100)
      throw Error("provider_daily_budget_exhausted");
    data[instance.id] = { day, count: count + 1 };
    atomic(file, JSON.stringify(data));
  });
}
