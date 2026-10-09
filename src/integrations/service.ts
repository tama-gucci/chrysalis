import type { RuntimeContext, Metadata } from "../contracts/types.ts";
import { ProtectedSecrets } from "../platforms/secret-store.ts";
import {
  authorizedInstance,
  instances,
  authorizationDigest,
} from "./profile.ts";
import { validateTool, observation } from "./contracts.ts";
import type { ProviderPorts } from "./contracts.ts";
import { readTasks } from "./providers/google-tasks.ts";
import { morningEvidence } from "./providers/google-health.ts";
import { mapsEvidence } from "./providers/google-maps.ts";

export const PROVIDER_REGISTRY = Object.freeze({
  "google-tasks": readTasks,
  "google-health": morningEvidence,
  "google-maps": mapsEvidence,
});
export function defaultPorts(ctx: RuntimeContext): ProviderPorts {
  return { secrets: new ProtectedSecrets(ctx), fetch };
}
async function observed<T>(work: () => Promise<T>): Promise<T> {
  try {
    return await work();
  } catch (e: any) {
    const code = String(e?.message);
    if (
      /^(provider_[a-z_]+|provider_http_\d{3}|protected_store_unavailable|health_[a-z_]+|integration_[a-z_]+|inbox_not_authorized|selected_details_cannot_page|choose_arrival_or_departure|arrival_time_requires_transit)$/.test(
        code,
      )
    )
      throw Error(code);
    throw Error("provider_invalid_response");
  }
}
/** Host-neutral service; model calls cannot set roots, transport, credentials or audience. */
export async function sourceTool(
  ctx: RuntimeContext,
  name: string,
  args: Metadata = {},
  ports = defaultPorts(ctx),
  audience: "model" | "operator" = "model",
) {
  validateTool(name, args);
  if (name === "integration_status")
    return {
      schema_version: "1",
      status: "ok",
      integrations: instances(ctx).map((i) => {
        let active = false;
        try {
          authorizedInstance(ctx, i.id);
          active = true;
        } catch {}
        return {
          instance: i.id,
          provider: i.provider,
          installed: true,
          configured: active,
          authenticated: null,
          available: null,
          last_verified_at: i.verified_at ?? null,
          audience: i.native_only ? "native_operator_only" : "model",
          reason: !active
            ? "inactive_or_binding_changed"
            : i.native_only
              ? "native_review_required"
              : "account_read_requires_fresh_probe",
        };
      }),
    };
  const instance = authorizedInstance(ctx, args.instance);
  if (
    (name === "list_task_lists" || name === "read_task_inbox") &&
    instance.provider !== "google-tasks"
  )
    throw Error("provider_mismatch");
  if (name === "get_morning_context" && instance.provider !== "google-health")
    throw Error("provider_mismatch");
  if (
    ["resolve_location", "estimate_travel_times"].includes(name) &&
    instance.provider !== "google-maps"
  )
    throw Error("provider_mismatch");
  if (instance.provider !== "google-tasks" && audience !== "operator")
    return observation(
      ctx,
      instance,
      name === "get_morning_context"
        ? "health.morning_context"
        : name === "resolve_location"
          ? "location.resolve"
          : "routing.estimate",
      {
        status: "native_review_required",
        reason:
          instance.provider === "google-health"
            ? "health_summary_not_authorized_for_model_or_plaintext_session"
            : "maps_content_not_authorized_for_saved_session",
        usage_policy: {
          audience: "native_operator_only",
          model_disclosure: false,
        },
        operator_command: "/chrysalis integrations review " + instance.id,
      },
    );
  const scoped = {
    ...ctx,
    signal: AbortSignal.any([
      AbortSignal.timeout(30000),
      ...(ctx.signal ? [ctx.signal] : []),
    ]),
  };
  if (name === "list_task_lists" || name === "read_task_inbox") {
    const result = await observed(() =>
      readTasks(scoped, instance, ports, args, name === "list_task_lists"),
    );
    if (name === "list_task_lists")
      result.items = result.items.filter((i) =>
        instance.list_ids.includes(i.id),
      );
    if (
      authorizationDigest(authorizedInstance(ctx, instance.id)) !==
      authorizationDigest(instance)
    )
      throw Error("integration_changed_during_read");
    const credentials = await ports.secrets.get(instance.secret_id),
      serialized = JSON.stringify(result);
    if (
      credentials &&
      Object.entries(credentials).some(
        ([key, value]) =>
          key !== "expiry_date" &&
          typeof value === "string" &&
          value.length >= 8 &&
          serialized.includes(value),
      )
    )
      throw Error("provider_credential_reflection_blocked");
    return result;
  }
  const result =
    name === "get_morning_context"
      ? await observed(() => morningEvidence(scoped, instance, ports))
      : await observed(() =>
          mapsEvidence(
            scoped,
            instance,
            ports,
            args,
            name === "resolve_location",
          ),
        );
  if (
    authorizationDigest(authorizedInstance(ctx, instance.id)) !==
    authorizationDigest(instance)
  )
    throw Error("integration_changed_during_read");
  return result;
}
