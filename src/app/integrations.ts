import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  PACKAGE_ROOT,
  rejectRedirects,
  inside,
} from "../platforms/filesystem.ts";
import { readRecord, change } from "../storage/records.ts";
import { propose, approve, apply } from "../core/runtime.ts";
import { ProtectedSecrets } from "../platforms/secret-store.ts";
import { authorize, credentialLock } from "../integrations/auth/google.ts";
import {
  instances,
  saveInstance,
  authorizationDigest,
} from "../integrations/profile.ts";
import { sourceTool, defaultPorts } from "../integrations/service.ts";
import { readTasks } from "../integrations/providers/google-tasks.ts";
import {
  TASKS_SCOPE,
  SLEEP_SCOPE,
  validateTool,
} from "../integrations/contracts.ts";
import type { Instance, Credentials } from "../integrations/contracts.ts";
import type { RuntimeContext, Metadata } from "../contracts/types.ts";
import { configuredZone } from "../core/runtime.ts";
import { nowStamp } from "../time/timezone.ts";

export interface OperatorUI {
  input(title: string, placeholder?: string): Promise<string | undefined>;
  select(title: string, options: string[]): Promise<string | undefined>;
  confirm(title: string, message: string): Promise<boolean>;
  notify(message: string, level?: "info" | "warning" | "error"): void;
  editor(title: string, text: string): Promise<string | undefined>;
  display(title: string, text: string): Promise<void>;
}
export function importCredentials(
  ctx: RuntimeContext,
  selected: string,
): Metadata {
  if (!path.isAbsolute(selected))
    throw Error("absolute_credential_file_required");
  const file = rejectRedirects(path.resolve(selected));
  if (
    inside(file, PACKAGE_ROOT) ||
    inside(file, ctx.vault) ||
    inside(file, ctx.state)
  )
    throw Error("credential_import_requires_external_file");
  const before = fs.lstatSync(file);
  if (!before.isFile() || before.size > 65536)
    throw Error("invalid_credential_file");
  const fd = fs.openSync(
    file,
    fs.constants.O_RDONLY |
      (process.platform !== "win32"
        ? fs.constants.O_NONBLOCK | fs.constants.O_NOFOLLOW
        : 0),
  );
  try {
    const stat = fs.fstatSync(fd);
    if (
      !stat.isFile() ||
      stat.dev !== before.dev ||
      stat.ino !== before.ino ||
      stat.size !== before.size
    )
      throw Error("invalid_credential_file");
    const bytes = Buffer.alloc(stat.size);
    let size = 0;
    while (size < bytes.length) {
      const n = fs.readSync(fd, bytes, size, bytes.length - size, size);
      if (!n) break;
      size += n;
    }
    if (size !== stat.size || fs.fstatSync(fd).size !== stat.size)
      throw Error("credential_file_changed");
    try {
      const parsed = JSON.parse(
        new TextDecoder("utf-8", { fatal: true }).decode(bytes),
      );
      if (!parsed || typeof parsed !== "object" || Array.isArray(parsed))
        throw Error("invalid_credential_file");
      return parsed;
    } catch {
      // Parser diagnostics can contain credential-bearing input excerpts.
      throw Error("invalid_credential_file");
    }
  } finally {
    fs.closeSync(fd);
  }
}
export async function configureIntegration(
  ctx: RuntimeContext,
  ui: OperatorUI,
  masked: (title: string) => Promise<string | undefined>,
  reconnect?: string,
) {
  const prior = reconnect
    ? instances(ctx).find((i) => i.id === reconnect)
    : undefined;
  if (reconnect && !prior) throw Error("unknown_integration");
  const provider =
    prior?.provider ??
    (await ui.select("Optional source: connect now, or skip", [
      "google-tasks",
      "google-maps",
      "google-health",
      "Skip or later",
    ]));
  if (!provider || provider === "Skip or later") return;
  const native_only = provider !== "google-tasks";
  if (
    !(await ui.confirm(
      "Review source access",
      provider === "google-tasks"
        ? "Read selected Google Tasks inboxes; send selected capture text to your Pi model for review. No write-back. Credentials stay in protected external storage. Standard Google identity access binds captures to the account."
        : provider === "google-health"
          ? "Requires an already eligible Google Health project. Sleep evidence is shown only in native controls and held in memory. No health metrics enter model/session/vault records. This wellbeing feature informs a manual morning check-in. Credentials use protected storage."
          : "Maps queries send only selected locations/mode/time, incur your Google Maps billing, and display attributed content only in native controls. Restricted results never enter Pi model/session/vault records. Limits: 20 pairs per request and 100 provider requests/day.",
    ))
  )
    return;
  if (
    provider === "google-health" &&
    !(await ui.confirm(
      "Health project access",
      "Do you already have an eligible enabled Google Health API project? New-project onboarding is currently paused. No existing access: choose No and continue manually.",
    ))
  )
    return;
  const id =
    prior?.id ?? (await ui.input("Unique integration alias", provider));
  if (!id) return;
  if (
    !/^[a-z0-9][a-z0-9-]{0,63}$/.test(id) ||
    (!prior && instances(ctx).some((i) => i.id === id))
  )
    throw Error("choose_unused_lowercase_alias");
  const account_alias = await ui.input(
    "Private account alias (no email needed)",
    "primary",
  );
  const project_id = await ui.input(
    "Google Cloud project ID",
    "example-project",
  );
  if (!account_alias || !project_id) return;
  if (account_alias.length > 64 || !/^[a-z][a-z0-9-]{4,62}$/.test(project_id))
    throw Error("invalid_account_or_project_alias");
  let credentials: Credentials;
  if (provider === "google-maps") {
    const api_key = await masked(
      "Restricted Google Maps API key; Escape cancels",
    );
    if (!api_key) return;
    if (!/^[A-Za-z0-9_-]{20,500}$/.test(api_key))
      throw Error("invalid_maps_key");
    credentials = { api_key };
  } else {
    const file = await ui.input(
      "Absolute downloaded OAuth client JSON path (outside source/vault/state)",
    );
    if (
      !file ||
      !(await ui.confirm(
        "Import credentials privately",
        "Read this credential file locally and store only an encrypted/protected copy? Never paste its content into chat. " +
          file,
      ))
    )
      return;
    const data = importCredentials(ctx, file),
      client = data.installed ?? data.web;
    if (data.installed && data.web) throw Error("ambiguous_oauth_client");
    if (client?.project_id && client.project_id !== project_id)
      throw Error("oauth_project_id_mismatch");
    if (
      !client ||
      typeof client.client_id !== "string" ||
      typeof client.client_secret !== "string" ||
      client.client_id.length > 500 ||
      client.client_secret.length > 500
    )
      throw Error("invalid_oauth_client");
    let redirect: string | undefined;
    if (!data.installed) {
      const choices = (client.redirect_uris ?? []).filter(
        (v: unknown) =>
          typeof v === "string" &&
          /^http:\/\/127\.0\.0\.1:\d+\/callback$/.test(v),
      );
      if (!choices.length)
        throw Error("web_client_requires_registered_fixed_loopback_callback");
      redirect = await ui.select(
        "Choose a registered local Web OAuth callback",
        choices,
      );
      if (!redirect) return;
    }
    if (provider === "google-health" && !data.web)
      throw Error("health_requires_web_oauth_client");
    if (
      !(await ui.confirm(
        "Authorize Google access",
        "A system browser opens using the selected client and loopback callback. Health accounts must already be linked in the Google Health mobile app. Scope: " +
          (provider === "google-tasks" ? TASKS_SCOPE : SLEEP_SCOPE) +
          " plus standard account identity. Sharing a Cloud project couples remote revocation across clients. Separate projects are needed for independent remote revocation.",
      ))
    )
      return;
    credentials = await authorize(
      { client_id: client.client_id, client_secret: client.client_secret },
      [provider === "google-tasks" ? TASKS_SCOPE : SLEEP_SCOPE],
      (url) =>
        ui.notify(
          "Authorize in the system browser. If it did not open, visit: " + url,
          "info",
        ),
      ctx.signal,
      redirect,
    );
  }
  const instance: Instance = {
    id,
    provider: provider as Instance["provider"],
    enabled: false,
    account_alias,
    project_id,
    secret_id: randomUUID(),
    scopes:
      provider === "google-tasks"
        ? [TASKS_SCOPE]
        : provider === "google-health"
          ? [SLEEP_SCOPE]
          : [],
    list_ids: [],
    native_only,
    health_project_eligible: provider === "google-health",
    consent_version: "1",
  };
  const secrets = new ProtectedSecrets(ctx);
  await secrets.put(instance.secret_id, credentials);
  let retained = false;
  try {
    if (provider === "google-tasks") {
      let cursor: string | undefined;
      const lists: Metadata[] = [];
      for (let page = 0; page < 5; page++) {
        const result = await readTasks(
          ctx,
          instance,
          { ...defaultPorts(ctx), secrets },
          { cursor },
          true,
        );
        lists.push(...result.items);
        cursor = result.coverage.next_cursor ?? undefined;
        if (!cursor) break;
      }
      if (cursor) throw Error("narrow_task_list_inventory_before_setup");
      if (!lists.length)
        throw Error("create_inbox_in_google_tasks_then_reconnect");
      const choices = lists.map(
          (r, i) => `${i + 1}. ${JSON.stringify(r.title)}`,
        ),
        choice = await ui.select("Choose one read-only inbox", choices);
      if (!choice) return;
      const selected = lists[choices.indexOf(choice)];
      if (!selected) throw Error("inbox_selection_required");
      instance.list_ids = [selected.id];
      await readTasks(
        ctx,
        instance,
        { ...defaultPorts(ctx), secrets },
        { list_id: selected.id, page_size: 1 },
      );
    } else if (provider === "google-health") {
      const { morningEvidence } = await import(
        "../integrations/providers/google-health.ts"
      );
      const evidence = await morningEvidence(ctx, instance, {
        ...defaultPorts(ctx),
        secrets,
      });
      await ui.display(
        "Health access test: native evidence only",
        JSON.stringify(evidence, null, 2),
      );
    } else {
      const query = await ui.input(
        "Location for a small billable Maps access test",
      );
      if (!query) return;
      validateTool("resolve_location", { instance: id, query });
      const { mapsEvidence } = await import(
        "../integrations/providers/google-maps.ts"
      );
      const evidence = await mapsEvidence(
        ctx,
        instance,
        { ...defaultPorts(ctx), secrets },
        { query },
        true,
      );
      await ui.display(
        "Google Maps access test: native display only",
        JSON.stringify(evidence, null, 2),
      );
    }
    instance.enabled = true;
    instance.verified_at = nowStamp(configuredZone(ctx));
    const memory = readRecord(ctx.vault, "System/Memory.md"),
      fm = structuredClone(memory.frontmatter);
    fm.integrations ??= { instances: {}, bindings: {} };
    fm.integrations.instances ??= {};
    fm.integrations.bindings ??= {};
    fm.integrations.instances[id] = {
      integration: provider,
      enabled: true,
      access: "read-only",
      native_authorization: authorizationDigest(instance),
    };
    const capability =
      provider === "google-tasks"
        ? "ingestion.read"
        : provider === "google-health"
          ? "health.morning_context"
          : "routing.estimate";
    if (!fm.integrations.bindings[capability])
      fm.integrations.bindings[capability] = { instance: id, capability };
    const secondary =
      provider === "google-tasks"
        ? "ingestion.discover"
        : provider === "google-maps"
          ? "location.resolve"
          : undefined;
    if (secondary && !fm.integrations.bindings[secondary])
      fm.integrations.bindings[secondary] = {
        instance: id,
        capability: secondary,
      };
    if (provider === "google-tasks") {
      fm.ingestion ??= { sources: {} };
      fm.ingestion.sources ??= {};
      fm.ingestion.sources[id] = {
        instance: id,
        integration: provider,
        enabled: true,
        mode: "read-only",
        collection_id: instance.list_ids[0],
      };
    }
    const proposal = propose(
      ctx,
      [change(memory, fm)],
      "integration_activation",
    );
    const displayed = JSON.stringify(
        { activation: instance, proposal },
        null,
        2,
      ),
      seen = await ui.editor(
        "Review exact nonsecret activation and Memory record",
        displayed,
      );
    if (
      seen !== displayed ||
      !(await ui.confirm(
        "Activate this source?",
        "Approve this exact nonsecret binding and external profile. New task/knowledge records still require their own approvals. Digest: " +
          proposal.proposal_digest,
      ))
    )
      return;
    const activate = async () => {
      // Until Memory application succeeds the saved profile is unusable by tools.
      await saveInstance(ctx, instance);
      retained = true;
      approve(
        ctx,
        proposal.proposal_digest,
        "Native operator reviewed source activation",
      );
      const result = await apply(ctx, proposal.proposal_digest);
      if (result.status !== "verified") {
        ui.notify(
          "Activation record application needs recovery; inspect the exact proposal receipt.",
          "warning",
        );
      }
      if (
        result.status === "verified" &&
        prior &&
        !instances(ctx).some((i) => i.secret_id === prior.secret_id)
      )
        await secrets.remove(prior.secret_id);
      ui.notify(
        "Source configuration saved. Inspect integrations status before workflow use.",
        "info",
      );
    };
    // Acquire before replacing the old profile so a lock timeout preserves its credential identity.
    if (prior) await credentialLock(ctx, prior.secret_id, activate);
    else await activate();
  } finally {
    if (!retained) await secrets.remove(instance.secret_id);
  }
}
export async function disconnectIntegration(
  ctx: RuntimeContext,
  ui: OperatorUI,
  id: string,
) {
  const instance = instances(ctx).find((i) => i.id === id);
  if (!instance) throw Error("unknown_integration");
  if (
    !(await ui.confirm(
      "Disconnect locally?",
      "Stop this source and dispose of its unshared protected credentials? Vault records remain authoritative. This does not revoke Google project-wide access. Use Google Account access controls for remote revocation; all project clients for that account can be affected.",
    ))
  )
    return;
  await saveInstance(ctx, { ...instance, enabled: false });
  if (
    !instances(ctx).some(
      (i) => i.id !== id && i.secret_id === instance.secret_id,
    )
  ) {
    try {
      await credentialLock(ctx, instance.secret_id, async () => {
        if (
          !instances(ctx).some(
            (i) => i.id !== id && i.secret_id === instance.secret_id,
          )
        )
          await new ProtectedSecrets(ctx).remove(instance.secret_id);
      });
    } catch {
      throw Error(
        "credential_cleanup_incomplete_reads_disabled_retry_disconnect",
      );
    }
  }
  ui.notify(
    "Locally disconnected. For remote revocation review every client in this Google Cloud project/account, including clients outside chrysalis.",
    "info",
  );
}
export async function reviewIntegration(
  ctx: RuntimeContext,
  ui: OperatorUI,
  id: string,
) {
  const i = instances(ctx).find((i) => i.id === id);
  if (!i) throw Error("unknown_integration");
  let name: string,
    args: Metadata = { instance: id };
  if (i.provider === "google-health") name = "get_morning_context";
  else if (i.provider === "google-tasks") {
    name = "read_task_inbox";
    args.list_id = i.list_ids[0];
  } else {
    const choice = await ui.select("Native Google Maps review", [
      "Resolve a place",
      "Estimate travel",
    ]);
    if (!choice) return;
    if (choice === "Resolve a place") {
      name = "resolve_location";
      const query = await ui.input("Place/address to send to Google Maps");
      if (!query) return;
      args.query = query;
    } else {
      name = "estimate_travel_times";
      const origin = await ui.input("Origin Google place ID"),
        destination = await ui.input("Destination Google place ID"),
        mode = await ui.select("Travel mode", [
          "driving",
          "walking",
          "bicycling",
          "transit",
        ]);
      if (!origin || !destination || !mode) return;
      const departure = await ui.input(
        "Departure ISO time with offset (leave empty for provider's current context)",
      );
      args.pairs = [
        {
          origin: { place_id: origin },
          destination: { place_id: destination },
          travel_mode: mode,
          ...(departure ? { departure_at: departure } : {}),
        },
      ];
    }
  }
  validateTool(name, args);
  if (
    !(await ui.confirm(
      "Read selected provider data?",
      i.provider === "google-maps"
        ? "This billable query sends only the selected route/place fields. Results stay in attributed native display; choose planning allowances independently."
        : "Read the selected scope for native display only? Device data does not override your morning replies.",
    ))
  )
    return;
  const result = await sourceTool(
    ctx,
    name,
    args,
    defaultPorts(ctx),
    "operator",
  );
  await ui.display(
    i.provider === "google-maps"
      ? "Google Maps: native evidence, no record write"
      : "Native source evidence: no record write",
    JSON.stringify(result, null, 2),
  );
}
