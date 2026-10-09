import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  prepareOnboarding,
  approveSetup,
  applySetup,
} from "../src/app/onboarding.ts";
import {
  runtimeContext,
  vaultState,
  externalState,
} from "../src/storage/context.ts";
import { readRecord, serializeRecord } from "../src/storage/records.ts";
import { atomic, confined, digest } from "../src/platforms/filesystem.ts";
import { ProtectedSecrets } from "../src/platforms/secret-store.ts";
import {
  saveInstance,
  authorizedInstance,
  authorizationDigest,
  requestBudget,
} from "../src/integrations/profile.ts";
import { sourceTool } from "../src/integrations/service.ts";
import {
  TASKS_SCOPE,
  SLEEP_SCOPE,
  validateTool,
} from "../src/integrations/contracts.ts";
import type {
  Credentials,
  Instance,
  ProviderPorts,
} from "../src/integrations/contracts.ts";
import { providerJSON } from "../src/integrations/http.ts";
import { normalizeSleep } from "../src/integrations/providers/google-health.ts";
import { dispatch } from "../src/app/operations.ts";
import {
  importCredentials,
  disconnectIntegration,
  configureIntegration,
} from "../src/app/integrations.ts";
import {
  authorize,
  accessToken,
  credentialLock,
} from "../src/integrations/auth/google.ts";
import { OAuth2Client } from "google-auth-library";

if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(
  externalState(process.env.TEST_SCRATCH),
  "integrations-" + randomUUID(),
);
const vault = path.join(base, "vault"),
  state = path.join(base, "state");
const plan = prepareOnboarding({
  vault,
  state,
  timezone: "America/Chicago",
  observation: { timezone: "America/Chicago", source: "fixture" },
});
approveSetup(state, plan.proposal_digest, "Synthetic setup acceptance");
await applySetup(state, plan.proposal_digest);
const ctx = runtimeContext(vault, state, "2026-10-08T12:00:00-05:00");
const credentials: Credentials = {
  client_id: "synthetic-client-identity",
  client_secret: "synthetic-private-client",
  refresh_token: "synthetic-refresh-value",
  access_token: "synthetic-access-value",
  expiry_date: Date.now() + 3600000,
  google_subject: "synthetic-subject-identity",
};
const records = new Map<string, Credentials>();
const secrets = {
  get: async (id: string) => records.get(id),
  put: async (id: string, value: Credentials) => {
    records.set(id, value);
  },
  remove: async (id: string) => {
    records.delete(id);
  },
};
async function activate(provider: Instance["provider"], id: string) {
  const i: Instance = {
    id,
    provider,
    enabled: true,
    account_alias: "primary",
    project_id: "fixture-project",
    secret_id: randomUUID(),
    scopes:
      provider === "google-tasks"
        ? [TASKS_SCOPE]
        : provider === "google-health"
          ? [SLEEP_SCOPE]
          : [],
    list_ids: provider === "google-tasks" ? ["inbox"] : [],
    health_project_eligible: provider === "google-health",
    native_only: provider !== "google-tasks",
    consent_version: "1",
  };
  records.set(i.secret_id, {
    ...credentials,
    api_key: "synthetic-maps-key-value",
  });
  await saveInstance(ctx, i);
  const memory = readRecord(vault, "System/Memory.md"),
    fm = memory.frontmatter;
  fm.integrations ??= { instances: {}, bindings: {} };
  fm.integrations.instances[id] = {
    integration: provider,
    enabled: true,
    access: "read-only",
    native_authorization: authorizationDigest(i),
  };
  fm.integrations.bindings["ingestion.read"] = {
    instance: id,
    capability: "ingestion.read",
  };
  fm.ingestion ??= { sources: {} };
  fm.ingestion.sources[id] = {
    instance: id,
    integration: provider,
    enabled: true,
    mode: "read-only",
    collection_id: "inbox",
  };
  atomic(confined(vault, "System/Memory.md"), serializeRecord(fm, memory.body));
  return i;
}
const tasks = await activate("google-tasks", "task-inbox");
const health = await activate("google-health", "sleep-evidence");
const maps = await activate("google-maps", "travel-evidence");
const json = (value: any, status = 200) =>
  new Response(JSON.stringify(value), {
    status,
    headers: { "Content-Type": "application/json" },
  });

test("native receipt and enabled binding are required; model schema cannot supply privilege or secrets", async () => {
  for (const args of [
    { instance: tasks.id, list_id: "inbox", audience: "operator" },
    { instance: tasks.id, list_id: "inbox", api_key: "fake" },
    {
      instance: tasks.id,
      list_id: "inbox",
      selected_ids: Array(21).fill("item"),
    },
  ])
    assert.throws(
      () => validateTool("read_task_inbox", args),
      /invalid_source_request/,
    );
  const old = readRecord(vault, "System/Memory.md");
  const fm = structuredClone(old.frontmatter);
  fm.integrations.instances[tasks.id].native_authorization = "changed";
  atomic(confined(vault, old.path), serializeRecord(fm, old.body));
  assert.throws(
    () => authorizedInstance(ctx, tasks.id),
    /binding_needs_review/,
  );
  atomic(confined(vault, old.path), old.document);
  let requests = 0;
  const ports: ProviderPorts = {
    secrets,
    fetch: async () => {
      requests++;
      return json({});
    },
  };
  await assert.rejects(
    sourceTool(
      ctx,
      "read_task_inbox",
      { instance: tasks.id, list_id: "other" },
      ports,
    ),
    /not_authorized/,
  );
  assert.equal(requests, 0);
});

test("Tasks summarizes first, fetches selected details with partial failures and stable protected account identity", async () => {
  const urls: string[] = [];
  const ports: ProviderPorts = {
    secrets,
    fetch: async (url, init) => {
      urls.push(String(url));
      assert.equal(init?.method ?? "GET", "GET");
      assert.equal(init?.redirect, "error");
      if (String(url).includes("/missing")) return json({}, 404);
      if (new URL(String(url)).pathname.endsWith("/chosen"))
        return json({
          id: "chosen",
          title: "Review compiler design",
          notes: "Evidence and a plan",
          status: "needsAction",
          due: "2026-10-12T00:00:00.000Z",
          updated: "revision-one",
        });
      return json({
        items: [
          {
            id: "chosen",
            title: "Review compiler design",
            status: "needsAction",
          },
          { id: "gone", deleted: true },
          {
            id: "child",
            title: "Child",
            status: "needsAction",
            parent: "parent",
          },
        ],
        nextPageToken: "next-provider-page",
      });
    },
  };
  const before = readRecord(vault, "System/Memory.md").revision;
  const summary = await sourceTool(
    ctx,
    "read_task_inbox",
    { instance: tasks.id, list_id: "inbox", page_size: 10 },
    ports,
  );
  assert(summary.detail_selection_required);
  assert.equal(summary.items.length, 1);
  assert.equal(summary.coverage.complete, false);
  assert.equal(summary.coverage.next_cursor, "next-provider-page");
  assert.equal(summary.coverage.omitted.length, 2);
  assert(!JSON.stringify(summary).includes("Evidence and a plan"));
  assert(!new URL(urls[0]).searchParams.get("fields")?.includes("notes"));
  const detail = await sourceTool(
    ctx,
    "read_task_inbox",
    {
      instance: tasks.id,
      list_id: "inbox",
      selected_ids: ["chosen", "missing"],
    },
    ports,
  );
  assert.equal(detail.envelope.items.length, 1);
  assert.equal(detail.envelope.discovery_status, "partial_listing");
  assert.equal(detail.envelope.items[0].payload.due, "2026-10-12");
  assert.equal(
    detail.envelope.items[0].account_scope,
    digest(credentials.google_subject),
  );
  assert.equal(detail.envelope.items[0].payload.notes, "Evidence and a plan");
  assert.equal(detail.coverage.omitted[0].id, "missing");
  assert.equal(readRecord(vault, "System/Memory.md").revision, before);
  const proposal: any = await dispatch(ctx, "ingest.draft", {
    envelope: detail.envelope,
    date: "2026-10-08",
    now: ctx.now,
  });
  assert.equal(proposal.status, "review_required");
  assert.equal(
    fs
      .readdirSync(path.join(vault, "TaskNotes/Tasks"))
      .filter((f) => f.endsWith(".md")).length,
    0,
  );
});

test("Health and Maps model paths return non-content readiness without loading secrets or making requests", async () => {
  const ports: ProviderPorts = {
    secrets: {
      ...secrets,
      get: async () => {
        throw Error("Secret read forbidden");
      },
    },
    fetch: async () => {
      throw Error("Request forbidden");
    },
  };
  const before = readRecord(vault, "System/Memory.md").revision;
  for (const [name, args] of [
    ["get_morning_context", { instance: health.id }],
    ["resolve_location", { instance: maps.id, query: "Example library" }],
    [
      "estimate_travel_times",
      {
        instance: maps.id,
        pairs: [
          {
            origin: { place_id: "example-a" },
            destination: { place_id: "example-b" },
            travel_mode: "walking",
          },
        ],
      },
    ],
  ] as const) {
    const result = await sourceTool(ctx, name, args, ports);
    assert.equal(result.status, "native_review_required");
    assert.equal(result.usage_policy.model_disclosure, false);
    assert(!JSON.stringify(result).includes("minutes_asleep"));
    assert(!String(result.observed_at).endsWith("Z"));
  }
  assert.equal(readRecord(vault, "System/Memory.md").revision, before);
  const status = await sourceTool(ctx, "integration_status", {}, ports);
  assert(
    status.integrations.every(
      (i) => i.authenticated === null && i.available === null,
    ),
  );
});

test("native Health normalization retains timezone, freshness, omission and baseline uncertainty", () => {
  const sleep = {
    sleep: {
      interval: {
        startTime: "2026-10-08T02:00:00Z",
        endTime: "2026-10-08T10:00:00Z",
        startUtcOffset: "-18000s",
        endUtcOffset: "-18000s",
      },
      summary: { minutesAsleep: "420" },
      metadata: { processed: true, mainSleep: true },
    },
  };
  const result = normalizeSleep(
    ctx,
    [sleep, sleep, { sleep: { metadata: { processed: false } } }],
    true,
  );
  assert.equal(result.latest_sleep.minutes_asleep, 420);
  assert.match(result.latest_sleep.end, /-05:00$/);
  assert.equal(result.coverage.observed_sessions, 1);
  assert.equal(result.coverage.omitted_sessions, 1);
  assert.equal(result.coverage.complete, false);
  assert.equal(result.baseline_minutes, null);
  assert.equal(
    normalizeSleep({ ...ctx, now: "2026-10-11T12:00:00-05:00" }, [sleep], true)
      .status,
    "stale",
  );
  assert.equal(normalizeSleep(ctx, [], true).status, "empty");
});

test("native Health reads linked identity and bounded reconciled sleep; native Maps uses attributed minimal route context", async () => {
  const urls: string[] = [];
  const ports: ProviderPorts = {
    secrets,
    fetch: async (input, init) => {
      const url = new URL(String(input));
      urls.push(url.href);
      if (url.pathname.endsWith("/identity"))
        return json({
          healthUserId: "synthetic-health-user",
          name: "users/me/identity",
        });
      if (url.host === "health.googleapis.com") {
        assert.equal(url.searchParams.get("pageSize"), "25");
        assert(
          url.searchParams.get("filter")?.includes("sleep.interval.end_time"),
        );
        return json({
          dataPoints: [
            {
              sleep: {
                interval: {
                  startTime: "2026-10-08T02:00:00Z",
                  endTime: "2026-10-08T10:00:00Z",
                },
                summary: { minutesAsleep: "420" },
                metadata: { processed: true, mainSleep: true },
              },
            },
          ],
        });
      }
      assert.equal(url.host, "routes.googleapis.com");
      assert.equal(init?.method, "POST");
      assert.equal(
        (init?.headers as any)["X-Goog-FieldMask"],
        "routes.duration",
      );
      assert(!String(init?.body).includes("timeEstimate"));
      return json({ routes: [{ duration: "1200s" }] });
    },
  };
  const morning = await sourceTool(
    ctx,
    "get_morning_context",
    { instance: health.id },
    ports,
    "operator",
  );
  assert.equal(morning.latest_sleep.minutes_asleep, 420);
  assert.equal(morning.baseline_minutes, null);
  assert.equal(urls.length, 2);
  const routeInstance = await activate("google-maps", "native-route");
  const revision = readRecord(vault, "System/Memory.md").revision;
  const route = await sourceTool(
    ctx,
    "estimate_travel_times",
    {
      instance: routeInstance.id,
      pairs: [
        {
          origin: { place_id: "synthetic-origin" },
          destination: { place_id: "synthetic-destination" },
          travel_mode: "driving",
          departure_at: ctx.now,
        },
      ],
    },
    ports,
    "operator",
  );
  assert.equal(route.attribution, "Google Maps");
  assert.equal(route.estimates[0].duration_minutes, 20);
  assert(!String(route.estimates[0].observed_at).endsWith("Z"));
  assert.equal(readRecord(vault, "System/Memory.md").revision, revision);
  const pair = {
    origin: { place_id: "synthetic-origin" },
    destination: { place_id: "synthetic-destination" },
    travel_mode: "driving",
    departure_at: ctx.now,
  };
  const callsBefore = urls.length;
  await assert.rejects(
    sourceTool(
      ctx,
      "estimate_travel_times",
      {
        instance: routeInstance.id,
        pairs: [pair, { ...pair, arrival_by: ctx.now }],
      },
      ports,
      "operator",
    ),
    /choose_arrival_or_departure/,
  );
  assert.equal(urls.length, callsBefore);
  const budgetFile = confined(vaultState(ctx), "provider-budgets.json");
  const budgets = JSON.parse(fs.readFileSync(budgetFile, "utf8"));
  budgets[routeInstance.id] = {
    day: new Date().toISOString().slice(0, 10),
    count: 99,
  };
  atomic(budgetFile, JSON.stringify(budgets));
  const partial = await sourceTool(
    ctx,
    "estimate_travel_times",
    {
      instance: routeInstance.id,
      pairs: [pair, pair],
    },
    ports,
    "operator",
  );
  assert.equal(partial.status, "partial");
  assert.equal(partial.estimates[0].duration_minutes, 20);
  assert.equal(partial.estimates[1].reason, "provider_daily_budget_exhausted");
  assert.equal(urls.length, callsBefore + 1);
});

test("HTTP forbids arbitrary destinations, redirects, writes and oversized/error payload disclosure", async () => {
  let calls = 0;
  const ports: ProviderPorts = {
    secrets,
    fetch: async () => {
      calls++;
      return json({});
    },
  };
  await assert.rejects(
    providerJSON(ctx, ports, "https://example.com/"),
    /endpoint_forbidden/,
  );
  await assert.rejects(
    providerJSON(
      ctx,
      ports,
      "https://tasks.googleapis.com/tasks/v1/lists/inbox/tasks",
      { method: "POST" },
    ),
    /write_forbidden/,
  );
  assert.equal(calls, 0);
  await assert.rejects(
    providerJSON(
      ctx,
      { ...ports, fetch: async () => json({ secret: "must not escape" }, 403) },
      "https://tasks.googleapis.com/tasks/v1/lists/inbox/tasks",
    ),
    /^Error: provider_http_403$/,
  );
  await assert.rejects(
    providerJSON(
      ctx,
      { ...ports, fetch: async () => json({ text: "x".repeat(1024 * 1024) }) },
      "https://tasks.googleapis.com/tasks/v1/lists/inbox/tasks",
    ),
    /response_limit/,
  );
  let concurrent = 0,
    peak = 0;
  const throttled: ProviderPorts = {
    secrets,
    fetch: async () => {
      concurrent++;
      peak = Math.max(peak, concurrent);
      await new Promise((r) => setTimeout(r, 5));
      concurrent--;
      return json({});
    },
  };
  await Promise.all(
    Array.from({ length: 12 }, () =>
      providerJSON(
        ctx,
        throttled,
        "https://tasks.googleapis.com/tasks/v1/lists/inbox/tasks",
      ),
    ),
  );
  assert(peak <= 4);
});

test("credential reflection is blocked and external credential imports cannot read vault files", async () => {
  const ports: ProviderPorts = {
    secrets,
    fetch: async () =>
      json({
        id: "reflect",
        title: credentials.access_token,
        notes: "",
        status: "needsAction",
      }),
  };
  await assert.rejects(
    sourceTool(
      ctx,
      "read_task_inbox",
      { instance: tasks.id, list_id: "inbox", selected_ids: ["reflect"] },
      ports,
    ),
    /credential_reflection_blocked/,
  );
  assert.throws(
    () => importCredentials(ctx, "relative-client.json"),
    /absolute/,
  );
  assert.throws(
    () => importCredentials(ctx, path.join(vault, "System/Memory.md")),
    /external_file/,
  );
  const file = path.join(base, "synthetic-client.json");
  fs.writeFileSync(
    file,
    JSON.stringify({
      installed: { client_id: "example", client_secret: "example" },
    }),
  );
  assert.equal(importCredentials(ctx, file).installed.client_id, "example");
  fs.writeFileSync(file, '{"client_secret":"synthetic-secret-canary" broken');
  assert.throws(
    () => importCredentials(ctx, file),
    (e: any) =>
      e.message === "invalid_credential_file" &&
      !String(e).includes("synthetic-secret-canary"),
  );
  fs.writeFileSync(file, "null");
  assert.throws(() => importCredentials(ctx, file), /invalid_credential_file/);
});

test(
  "Windows DPAPI protects synthetic secrets outside vault and local disconnect cannot revoke project access",
  { skip: process.platform !== "win32" },
  async () => {
    const store = new ProtectedSecrets(ctx),
      id = randomUUID();
    await store.put(id, credentials);
    const encrypted = fs.readFileSync(
      confined(vaultState(ctx), "protected-secrets/" + id + ".encrypted"),
      "utf8",
    );
    assert(!encrypted.includes(credentials.access_token!));
    assert.deepEqual(await store.get(id), credentials);
    await store.remove(id);
    assert.equal(await store.get(id), undefined);
    const notifications: string[] = [];
    const ui: any = {
      confirm: async () => false,
      notify: (message: string) => notifications.push(message),
    };
    await disconnectIntegration(ctx, ui, maps.id);
    assert(authorizedInstance(ctx, maps.id));
    // Use an absent protected record to prove the disable boundary without live account material.
    ui.confirm = async () => true;
    const remove = ProtectedSecrets.prototype.remove;
    ProtectedSecrets.prototype.remove = async () => {
      throw Error("synthetic-secret-cleanup-canary");
    };
    try {
      await assert.rejects(
        disconnectIntegration(ctx, ui, maps.id),
        /^Error: credential_cleanup_incomplete_reads_disabled_retry_disconnect$/,
      );
      assert.throws(() => authorizedInstance(ctx, maps.id), /inactive/);
      assert.equal(notifications.length, 0);
    } finally {
      ProtectedSecrets.prototype.remove = remove;
    }
    await disconnectIntegration(ctx, ui, maps.id);
    assert.throws(() => authorizedInstance(ctx, maps.id), /inactive/);
    assert(notifications[0].includes("project/account"));
  },
);

test("OAuth loopback enforces callback state, PKCE and granted scopes without browser or account access", async () => {
  const getToken = OAuth2Client.prototype.getToken,
    verify = OAuth2Client.prototype.verifyIdToken;
  let scope = TASKS_SCOPE,
    called: any;
  OAuth2Client.prototype.getToken = async function (args: any) {
    called = args;
    return {
      tokens: {
        refresh_token: "synthetic-refresh-value",
        access_token: "synthetic-access-value",
        id_token: "synthetic-id-value",
        scope,
      },
      res: null,
    } as any;
  };
  OAuth2Client.prototype.verifyIdToken = async () =>
    ({ getPayload: () => ({ sub: "synthetic-subject-identity" }) }) as any;
  const callback = (url: string) => {
    const auth = new URL(url);
    assert.equal(auth.searchParams.get("code_challenge_method"), "S256");
    assert(auth.searchParams.get("code_challenge"));
    assert(auth.searchParams.get("scope")?.includes("openid"));
    const target = new URL(auth.searchParams.get("redirect_uri")!);
    target.searchParams.set("state", "wrong");
    target.searchParams.set("code", "synthetic-code");
    void fetch(target).then(async (r) => {
      assert.equal(r.status, 400);
      target.searchParams.set("state", auth.searchParams.get("state")!);
      const correct = await fetch(target);
      assert.equal(correct.status, 200);
    });
  };
  try {
    const result = await authorize(
      credentials,
      [TASKS_SCOPE],
      callback,
      undefined,
      undefined,
      () => {},
    );
    assert.equal(result.google_subject, "synthetic-subject-identity");
    assert.equal(called.code, "synthetic-code");
    assert(called.codeVerifier);
    scope = "ungranted";
    await assert.rejects(
      authorize(
        credentials,
        [TASKS_SCOPE],
        callback,
        undefined,
        undefined,
        () => {},
      ),
      /^Error: oauth_authorization_incomplete$/,
    );
    const controller = new AbortController();
    controller.abort();
    await assert.rejects(
      authorize(
        credentials,
        [TASKS_SCOPE],
        () => {},
        controller.signal,
        undefined,
        () => {},
      ),
      /authorization_incomplete/,
    );
    await assert.rejects(
      authorize(
        credentials,
        [TASKS_SCOPE],
        () => {},
        undefined,
        "https://example.com/callback",
        () => {},
      ),
      /invalid_registered_callback/,
    );
  } finally {
    OAuth2Client.prototype.getToken = getToken;
    OAuth2Client.prototype.verifyIdToken = verify;
  }
});

test("parallel budget reservations are lossless, exhaust at 100, and an in-flight disconnect suppresses returned data", async () => {
  const isolated = { ...tasks, id: "budget-fixture" };
  for (let round = 0; round < 10; round++)
    await Promise.all(
      Array.from({ length: 10 }, () => requestBudget(ctx, isolated)),
    );
  await assert.rejects(requestBudget(ctx, isolated), /daily_budget_exhausted/);
  const canceled = await activate("google-tasks", "cancel-inflight");
  const ports: ProviderPorts = {
    secrets,
    fetch: async () => {
      await saveInstance(ctx, { ...canceled, enabled: false });
      return json({
        items: [
          { id: "item", title: "Must not be delivered", status: "needsAction" },
        ],
      });
    },
  };
  await assert.rejects(
    sourceTool(
      ctx,
      "read_task_inbox",
      { instance: canceled.id, list_id: "inbox" },
      ports,
    ),
    /inactive/,
  );
});

test("expired tokens refresh once across parallel reads and rotate only in protected storage", async () => {
  const i = { ...tasks, secret_id: randomUUID() };
  records.set(i.secret_id, { ...credentials, expiry_date: 0 });
  const prior = OAuth2Client.prototype.refreshAccessToken;
  let calls = 0;
  OAuth2Client.prototype.refreshAccessToken = async () => {
    calls++;
    await new Promise((r) => setTimeout(r, 10));
    return {
      credentials: {
        access_token: "synthetic-rotated-value",
        refresh_token: "synthetic-rotated-refresh",
        expiry_date: Date.now() + 3600000,
      },
    } as any;
  };
  try {
    const values = await Promise.all(
      Array.from({ length: 8 }, () => accessToken(ctx, i, secrets)),
    );
    assert.equal(calls, 1);
    assert(values.every((v) => v === "synthetic-rotated-value"));
    assert.equal(
      records.get(i.secret_id)?.refresh_token,
      "synthetic-rotated-refresh",
    );
  } finally {
    OAuth2Client.prototype.refreshAccessToken = prior;
  }
});

test(
  "local disconnect waits for an in-flight refresh before disposing credentials",
  {
    skip: process.platform !== "win32",
  },
  async () => {
    const instance = await activate("google-tasks", "disconnect-refresh-race");
    const store = new ProtectedSecrets(ctx);
    await store.put(instance.secret_id, { ...credentials, expiry_date: 0 });
    const prior = OAuth2Client.prototype.refreshAccessToken;
    let start!: () => void, release!: () => void;
    const started = new Promise<void>((r) => {
      start = r;
    });
    const resume = new Promise<void>((r) => {
      release = r;
    });
    OAuth2Client.prototype.refreshAccessToken = async () => {
      start();
      await resume;
      return {
        credentials: {
          access_token: "synthetic-after-disconnect",
          refresh_token: "synthetic-after-disconnect-refresh",
          expiry_date: Date.now() + 3600000,
        },
      } as any;
    };
    try {
      const read = sourceTool(
        ctx,
        "read_task_inbox",
        {
          instance: instance.id,
          list_id: "inbox",
        },
        { secrets: store, fetch: async () => json({ items: [] }) },
      );
      // Attach the rejection assertion before releasing either asynchronous path.
      const denied = assert.rejects(read, /integration_inactive/);
      await started;
      const notices: string[] = [];
      const disconnect = disconnectIntegration(
        ctx,
        {
          confirm: async () => true,
          notify: (s: string) => notices.push(s),
        } as any,
        instance.id,
      );
      const deadline = Date.now() + 3000;
      while (Date.now() < deadline) {
        try {
          authorizedInstance(ctx, instance.id);
        } catch {
          break;
        }
        await new Promise((r) => setTimeout(r, 5));
      }
      assert.throws(
        () => authorizedInstance(ctx, instance.id),
        /integration_inactive/,
      );
      assert.equal(notices.length, 0);
      release();
      await Promise.all([disconnect, denied]);
      assert.equal(await store.get(instance.secret_id), undefined);
      assert(notices.some((s) => s.includes("Locally disconnected")));
    } finally {
      release();
      OAuth2Client.prototype.refreshAccessToken = prior;
    }
  },
);

test(
  "native Maps setup cancels without activation, then applies only exact approved bindings",
  { skip: process.platform !== "win32" },
  async () => {
    const before = readRecord(vault, "System/Memory.md").revision,
      fetchPrior = globalThis.fetch;
    let accept = false,
      views = 0,
      requests = 0;
    const ui: any = {
      select: async () => "google-maps",
      input: async (title: string) =>
        title.includes("Unique")
          ? "maps-setup"
          : title.includes("account alias")
            ? "primary"
            : title.includes("project ID")
              ? "fixture-project"
              : "Example library",
      confirm: async (title: string) =>
        title !== "Activate this source?" || accept,
      notify: () => {},
      editor: async (_title: string, value: string) => value,
      display: async () => {
        views++;
      },
    };
    globalThis.fetch = async (input, init) => {
      requests++;
      assert(String(input).startsWith("https://places.googleapis.com/"));
      assert.equal(init?.method, "POST");
      return json({
        places: [
          {
            id: "synthetic-place",
            displayName: { text: "Example library" },
            formattedAddress: "Example Street",
          },
        ],
      });
    };
    try {
      await configureIntegration(ctx, ui, async () => "synthetic_maps_api_key");
      assert.equal(readRecord(vault, "System/Memory.md").revision, before);
      assert.throws(() => authorizedInstance(ctx, "maps-setup"), /inactive/);
      assert.equal(views, 1);
      accept = true;
      await configureIntegration(ctx, ui, async () => "synthetic_maps_api_key");
      assert.equal(
        authorizedInstance(ctx, "maps-setup").provider,
        "google-maps",
      );
      const memory = readRecord(vault, "System/Memory.md");
      assert(!memory.document.includes("synthetic_maps_api_key"));
      assert(memory.frontmatter.integrations.bindings["location.resolve"]);
      assert.equal(requests, 2);
      assert.equal(views, 2);
      await assert.rejects(
        dispatch(ctx, "capability", {
          capability: "location.resolve",
          request: { query: "Example library", instance: "travel-evidence" },
        }),
        /cannot override/,
      );
      const oldSecret = authorizedInstance(ctx, "maps-setup").secret_id;
      const store = new ProtectedSecrets(ctx);
      let start!: () => void, release!: () => void, approved!: () => void;
      const started = new Promise<void>((r) => {
        start = r;
      });
      const resume = new Promise<void>((r) => {
        release = r;
      });
      const approval = new Promise<void>((r) => {
        approved = r;
      });
      const writer = credentialLock(ctx, oldSecret, async () => {
        start();
        await resume;
        await store.put(oldSecret, { api_key: "synthetic_old_key_rewrite" });
      });
      try {
        await started;
        const reconnect = configureIntegration(
          ctx,
          {
            ...ui,
            confirm: async (title: string) => {
              if (title === "Activate this source?") approved();
              return true;
            },
          },
          async () => "synthetic_reconnected_maps_key",
          "maps-setup",
        );
        await approval;
        await new Promise((r) => setTimeout(r, 25));
        assert.equal(
          authorizedInstance(ctx, "maps-setup").secret_id,
          oldSecret,
        );
        release();
        await Promise.all([writer, reconnect]);
        assert.notEqual(
          authorizedInstance(ctx, "maps-setup").secret_id,
          oldSecret,
        );
        assert.equal(await store.get(oldSecret), undefined);
      } finally {
        release();
      }
      await disconnectIntegration(
        ctx,
        { ...ui, confirm: async () => true },
        "maps-setup",
      );
      assert.throws(() => authorizedInstance(ctx, "maps-setup"), /inactive/);
    } finally {
      globalThis.fetch = fetchPrior;
    }
  },
);
