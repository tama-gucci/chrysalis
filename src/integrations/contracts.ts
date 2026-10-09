import { Ajv } from "ajv";
import type { RuntimeContext, Metadata } from "../contracts/types.ts";
import { configuredZone } from "../core/runtime.ts";
import { nowStamp, serialize } from "../time/timezone.ts";

export const SERVER_NAME = "chrysalis_sources";
export const TASKS_SCOPE = "https://www.googleapis.com/auth/tasks.readonly";
export const SLEEP_SCOPE =
  "https://www.googleapis.com/auth/googlehealth.sleep.readonly";
export type Provider = "google-tasks" | "google-maps" | "google-health";
export interface Instance {
  id: string;
  provider: Provider;
  enabled: boolean;
  account_alias: string;
  project_id: string;
  secret_id: string;
  scopes: string[];
  list_ids: string[];
  health_project_eligible: boolean;
  native_only: boolean;
  consent_version: "1";
  verified_at?: string;
}
export interface Credentials {
  google_subject?: string;
  client_id?: string;
  client_secret?: string;
  refresh_token?: string;
  access_token?: string;
  expiry_date?: number;
  api_key?: string;
}
export interface SecretStore {
  get(id: string): Promise<Credentials | undefined>;
  put(id: string, value: Credentials): Promise<void>;
  remove(id: string): Promise<void>;
}
export interface ProviderPorts {
  secrets: SecretStore;
  fetch: typeof fetch;
}
export const object = (properties: Metadata = {}, required: string[] = []) => ({
  type: "object",
  additionalProperties: false,
  properties,
  required,
});
const alias = { type: "string", pattern: "^[a-z0-9][a-z0-9-]{0,63}$" };
const short = { type: "string", minLength: 1, maxLength: 500 };
const timestamp = { type: "string", minLength: 10, maxLength: 64 };
const endpoint = object({ place_id: short }, ["place_id"]);
export const TOOL_SCHEMAS: Record<string, Metadata> = {
  integration_status: object(),
  list_task_lists: object({ instance: alias, cursor: short }, ["instance"]),
  read_task_inbox: object(
    {
      instance: alias,
      list_id: short,
      cursor: short,
      page_size: { type: "integer", minimum: 1, maximum: 100 },
      include_completed: { type: "boolean" },
      selected_ids: {
        type: "array",
        minItems: 1,
        maxItems: 20,
        uniqueItems: true,
        items: short,
      },
    },
    ["instance", "list_id"],
  ),
  get_morning_context: object({ instance: alias }, ["instance"]),
  resolve_location: object(
    {
      instance: alias,
      query: short,
      region_code: { type: "string", pattern: "^[A-Z]{2}$" },
    },
    ["instance", "query"],
  ),
  estimate_travel_times: object(
    {
      instance: alias,
      pairs: {
        type: "array",
        minItems: 1,
        maxItems: 20,
        items: object(
          {
            origin: endpoint,
            destination: endpoint,
            travel_mode: {
              enum: ["driving", "walking", "bicycling", "transit"],
            },
            departure_at: timestamp,
            arrival_by: timestamp,
          },
          ["origin", "destination", "travel_mode"],
        ),
      },
    },
    ["instance", "pairs"],
  ),
};
export const TOOL_DESCRIPTIONS: Record<string, string> = {
  integration_status:
    "Redacted readiness of native-authorized read-only source modules.",
  list_task_lists:
    "List a bounded page of authorized Google Tasks lists for operator selection.",
  read_task_inbox:
    "Read one authorized inbox page. Preserve coverage, cursor and stable capture identity; proposals still need native approval.",
  get_morning_context:
    "Report Health readiness only. Sleep evidence requires native review and never enters model results or session storage.",
  resolve_location:
    "Report Maps readiness only; restricted location content is displayed through the native operator command.",
  estimate_travel_times:
    "Report Maps readiness only; native attributed travel review preserves task work duration and record approvals.",
};
const ajv = new Ajv({ allErrors: true, strict: false });
const validators = Object.fromEntries(
  Object.entries(TOOL_SCHEMAS).map(([name, schema]) => [
    name,
    ajv.compile(schema),
  ]),
);
export function validateTool(name: string, args: Metadata) {
  if (!validators[name] || !validators[name](args))
    throw Error("invalid_source_request");
}
export function observation(
  ctx: RuntimeContext,
  instance: Instance,
  capability: string,
  fields: Metadata = {},
): Metadata {
  const zone = configuredZone(ctx);
  return {
    schema_version: "1",
    capability,
    provider: instance.provider,
    instance: instance.id,
    status: "ok",
    observed_at: ctx.now ? serialize(ctx.now, zone) : nowStamp(zone),
    coverage: { complete: true },
    provenance: "provider_observation",
    usage_policy: { read_only: true, write_back_supported: false },
    ...fields,
  };
}
