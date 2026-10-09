import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  createAgentSession,
  DefaultResourceLoader,
  SettingsManager,
  SessionManager,
  createCodemodeExtension,
  estimateTokens,
} from "@earendil-works/pi-coding-agent";
import { runToolCall } from "@earendil-works/pi-agent-core";
import { sourceTool } from "../src/integrations/service.ts";
import {
  TASKS_SCOPE,
  TOOL_SCHEMAS,
  TOOL_DESCRIPTIONS,
} from "../src/integrations/contracts.ts";
import {
  saveInstance,
  authorizationDigest,
} from "../src/integrations/profile.ts";
import {
  prepareOnboarding,
  approveSetup,
  applySetup,
} from "../src/app/onboarding.ts";
import { externalState, runtimeContext } from "../src/storage/context.ts";
import { readRecord, serializeRecord } from "../src/storage/records.ts";
import { atomic, confined } from "../src/platforms/filesystem.ts";

test("actual codemode reduces bounded Tasks fixture results with equal coverage; context estimates include schemas and discovery", async () => {
  if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
  const base = path.join(
      externalState(process.env.TEST_SCRATCH),
      "codemode-" + randomUUID(),
    ),
    vault = path.join(base, "vault"),
    state = path.join(base, "state"),
    cwd = path.join(base, "cwd"),
    agentDir = path.join(base, "profile");
  const p = prepareOnboarding({
    vault,
    state,
    timezone: "Europe/Paris",
    observation: { timezone: "Europe/Paris", source: "fixture" },
  });
  approveSetup(state, p.proposal_digest, "Synthetic setup");
  await applySetup(state, p.proposal_digest);
  const ctx = runtimeContext(vault, state, "2026-10-08T12:00:00+02:00");
  const instance: any = {
    id: "fixture-inbox",
    provider: "google-tasks",
    enabled: true,
    account_alias: "primary",
    project_id: "fixture-project",
    secret_id: randomUUID(),
    scopes: [TASKS_SCOPE],
    list_ids: ["small", "large", "failure"],
    health_project_eligible: false,
    native_only: false,
    consent_version: "1",
  };
  await saveInstance(ctx, instance);
  const m = readRecord(vault, "System/Memory.md"),
    fm = m.frontmatter;
  fm.integrations.instances[instance.id] = {
    integration: instance.provider,
    enabled: true,
    native_authorization: authorizationDigest(instance),
  };
  atomic(confined(vault, m.path), serializeRecord(fm, m.body));
  const credential = {
    client_id: "synthetic-client-identity",
    client_secret: "synthetic-client-secret",
    refresh_token: "synthetic-refresh",
    access_token: "synthetic-access",
    expiry_date: Date.now() + 3600000,
    google_subject: "synthetic-identity",
  };
  const ports: any = {
    secrets: {
      get: async () => credential,
      put: async () => {},
      remove: async () => {},
    },
    fetch: async (input: any) => {
      const u = new URL(String(input));
      if (u.pathname.includes("/failure/"))
        return new Response("{}", { status: 503 });
      const large = u.pathname.includes("/large/"),
        page = Number(u.searchParams.get("pageToken") ?? 0),
        n = large ? 100 : 2;
      return new Response(
        JSON.stringify({
          items: Array.from({ length: n }, (_, index) => ({
            id: `item-${page}-${index}`,
            title:
              (index === 0 ? "Chosen " : "Other ") +
              "synthetic compiler evidence ".repeat(large ? 14 : 1),
            status: "needsAction",
          })),
          ...(large && page === 0 ? { nextPageToken: "1" } : {}),
        }),
      );
    },
  };
  const wrap = (r: any) => ({
    content: [{ type: "text", text: JSON.stringify(r) }],
    structuredContent: r,
  });
  const fixtureName = "mcp__fixture_sources__read_task_inbox";
  const settings = SettingsManager.inMemory({}),
    loader = new DefaultResourceLoader({
      cwd,
      agentDir,
      settingsManager: settings,
      noContextFiles: true,
      noSkills: true,
      disabledBuiltinExtensions: ["mcp", "codemode"],
      extensionFactories: [
        (pi) => {
          createCodemodeExtension({ models: false, inlineBudget: 0 })(pi);
          pi.registerTool({
            name: fixtureName,
            label: "Fixture inbox",
            description: TOOL_DESCRIPTIONS.read_task_inbox,
            parameters: TOOL_SCHEMAS.read_task_inbox as any,
            outputSchema: { type: "object" },
            exposure: "codemode",
            namespace: {
              name: "mcp__fixture_sources",
              description: "Synthetic Tasks service acceptance",
            },
            async execute(_id, args, signal) {
              try {
                const r = wrap(
                  await sourceTool(
                    { ...ctx, signal },
                    "read_task_inbox",
                    args,
                    ports,
                  ),
                );
                return {
                  content: r.content as any,
                  structuredContent: r,
                  details: {},
                };
              } catch {
                return {
                  content: [{ type: "text", text: "Fixture unavailable" }],
                  structuredContent: {
                    isError: true,
                    content: [],
                    structuredContent: { status: "unavailable" },
                  },
                  details: {},
                  isError: true,
                };
              }
            },
          });
        },
      ],
    });
  fs.mkdirSync(cwd, { recursive: true });
  fs.mkdirSync(agentDir, { recursive: true });
  await loader.reload();
  const { session } = await createAgentSession({
    cwd,
    agentDir,
    settingsManager: settings,
    resourceLoader: loader,
    sessionManager: SessionManager.inMemory(cwd),
    tools: ["codemode"],
  });
  await session.bindExtensions({});
  const usage: any = {
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0,
    totalTokens: 0,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
  };
  session.agent.state.messages.push({
    role: "assistant",
    content: [],
    api: "openai-responses",
    provider: "synthetic",
    model: "fixture",
    usage,
    stopReason: "toolUse",
    timestamp: Date.now(),
  });
  const estimate = (value: any) =>
    estimateTokens({
      role: "user",
      content: typeof value === "string" ? value : JSON.stringify(value),
      timestamp: Date.now(),
    } as any);
  const declared = estimate(
    session.agent.state.tools.map((t) => ({
      name: t.name,
      description: t.description,
      parameters: t.parameters,
    })),
  );
  const directSchemas = estimate(
    Object.entries(TOOL_SCHEMAS).map(([name, parameters]) => ({
      name,
      description: TOOL_DESCRIPTIONS[name],
      parameters,
    })),
  );
  const measurements: any[] = [];
  try {
    for (const scenario of ["small", "large", "partial"]) {
      const requests =
        scenario === "small"
          ? [{ instance: instance.id, list_id: "small", page_size: 100 }]
          : [
              { instance: instance.id, list_id: "large", page_size: 100 },
              {
                instance: instance.id,
                list_id: "large",
                page_size: 100,
                cursor: "1",
              },
              ...(scenario === "partial"
                ? [
                    {
                      instance: instance.id,
                      list_id: "failure",
                      page_size: 100,
                    },
                  ]
                : []),
            ];
      const direct = await Promise.all(
        requests.map(async (args) => {
          try {
            return wrap(await sourceTool(ctx, "read_task_inbox", args, ports));
          } catch {
            return {
              isError: true,
              content: [],
              structuredContent: { status: "unavailable" },
            };
          }
        }),
      );
      const reduce = (r: any) =>
        r.isError
          ? { status: "unavailable" }
          : {
              status: r.structuredContent.status,
              coverage: r.structuredContent.coverage,
              provenance: r.structuredContent.provenance,
              items: r.structuredContent.items.filter((i: any) =>
                i.title.startsWith("Chosen "),
              ),
            };
      const expected = direct.map(reduce),
        code = `const requests=${JSON.stringify(requests)}; const results=await Promise.allSettled(requests.map(args=>tools.${fixtureName}(args))); text(results.map(r=>r.status!=="fulfilled"||r.value.isError?{status:"unavailable"}:{status:r.value.structuredContent.status,coverage:r.value.structuredContent.coverage,provenance:r.value.structuredContent.provenance,items:r.value.structuredContent.items.filter(i=>i.title.startsWith("Chosen "))}));`;
      const discovery = `text(await describeTool("${fixtureName}"));`;
      const run = async (code: string) => {
        const out = await runToolCall(
          {
            type: "toolCall",
            id: "fixture-codemode",
            name: "codemode",
            arguments: { code },
          },
          {
            tools: session.agent.state.tools,
            assistantMessage: session.agent.state.messages.at(-1) as any,
            context: session.agent.state,
            beforeToolCall: session.agent.beforeToolCall,
            afterToolCall: session.agent.afterToolCall,
          },
        );
        assert(!out.isError, JSON.stringify(out));
        return out.result.content
          .filter((c) => c.type === "text")
          .map((c: any) => c.text)
          .join("\n");
      };
      const schemaOutput = await run(discovery),
        cold = await run(code),
        warm = await run(code);
      assert.match(schemaOutput, /selected_ids/);
      assert.match(cold, /Script completed/);
      const value = (output: string) =>
        JSON.parse(output.slice(output.indexOf("Output:\n") + 8).trim());
      assert.deepEqual(value(cold), expected);
      assert.deepEqual(value(warm), expected);
      const directUnits =
          directSchemas +
          estimate(
            requests.map((args) => ({ name: fixtureName, arguments: args })),
          ) +
          direct.reduce(
            (n, r) =>
              n +
              estimate(
                r.content.length
                  ? r.content
                  : [{ type: "text", text: "Fixture unavailable" }],
              ),
            0,
          ),
        warmUnits =
          declared +
          estimate({ name: "codemode", arguments: { code } }) +
          estimate(warm),
        coldUnits =
          warmUnits +
          estimate({ name: "codemode", arguments: { code: discovery } }) +
          estimate(schemaOutput);
      measurements.push({
        scenario,
        direct_estimated_tokens: directUnits,
        cold_codemode_estimated_tokens: coldUnits,
        warm_codemode_estimated_tokens: warmUnits,
        direct_schema_units: directSchemas,
        single_tool_direct_estimated_tokens:
          directUnits -
          directSchemas +
          estimate({
            name: fixtureName,
            description: TOOL_DESCRIPTIONS.read_task_inbox,
            parameters: TOOL_SCHEMAS.read_task_inbox,
          }),
        codemode_schema_units: declared,
        discovery_units: estimate(schemaOutput),
        cold_change_percent: Math.round((coldUnits / directUnits - 1) * 100),
        warm_change_percent: Math.round((warmUnits / directUnits - 1) * 100),
        equal_reduced_results: true,
      });
    }
    fs.writeFileSync(
      path.join(base, "measurements.json"),
      JSON.stringify(
        {
          estimator: "Pi estimateTokens chars/4, not billed tokens",
          transport:
            "shared provider service with in-process synthetic MCP-shaped wrappers; separate production stdio acceptance in pi.test.ts",
          measurements,
        },
        null,
        2,
      ),
    );
    assert(
      measurements.find((r) => r.scenario === "large")
        .warm_codemode_estimated_tokens <
        measurements.find((r) => r.scenario === "large")
          .direct_estimated_tokens,
    );
  } finally {
    session.dispose();
  }
});
