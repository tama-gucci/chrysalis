import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  conversationToolDigest,
  installCompanions,
} from "../extensions/companions.ts";
import { PACKAGE_ROOT } from "../src/platforms/filesystem.ts";
import { externalState } from "../src/storage/context.ts";
import {
  DefaultResourceLoader,
  SettingsManager,
  SessionManager,
  createAgentSession,
} from "@earendil-works/pi-coding-agent";

if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(
  externalState(process.env.TEST_SCRATCH),
  "companions-" + randomUUID(),
);
fs.mkdirSync(base, { recursive: true });
const definition = {
  name: "recall",
  description: "Synthetic current-session recall",
  parameters: { type: "object", properties: {}, additionalProperties: false },
};
function policy(state: string, origin: string, tools: any[] = [definition]) {
  fs.mkdirSync(state, { recursive: true });
  fs.writeFileSync(
    path.join(state, "host-addons.json"),
    JSON.stringify({
      version: 2,
      skill_roots: [],
      tools: tools.map((t) => ({
        name: t.name,
        extension_path: origin,
        mode: "read-only",
        definition_sha256: conversationToolDigest({
          ...t,
          exposure: "direct",
          sourceInfo: { path: origin },
        }),
      })),
    }),
  );
}

test("companion permission is absent by default and checks exact tool definitions and origins", () => {
  const state = path.join(base, "policy"),
    origin = path.join(base, "addon.ts");
  process.env.CHRYSALIS_STATE_ROOT = state;
  let info: any = {
    ...definition,
    exposure: "direct",
    sourceInfo: { path: origin },
  };
  const api: any = { getAllTools: () => [info] };
  assert(!installCompanions(api).allowed("recall"));
  policy(state, origin);
  const gate = installCompanions(api);
  assert(gate.allowed("recall"));
  info = { ...info, description: "Changed semantics" };
  assert(!gate.allowed("recall"));
  info = { ...definition, sourceInfo: { path: path.join(base, "other.ts") } };
  assert(!gate.allowed("recall"));
  info = {
    ...definition,
    parameters: { type: "object" },
    sourceInfo: { path: origin },
  };
  assert(!gate.allowed("recall"));
  assert(!gate.allowed("bash"));
  assert(!gate.allowed("subagent"));
  policy(state, origin, [{ ...definition, name: "write" }]);
  assert.throws(() => installCompanions(api), /Invalid host/);
  policy(state, origin, [definition, definition]);
  assert.throws(() => installCompanions(api), /Invalid host/);
  delete process.env.CHRYSALIS_STATE_ROOT;
});

test("actual host admits research, recall and questions without allowing direct writes or approval", async () => {
  const cwd = path.join(base, "cwd"),
    agentDir = path.join(base, "agent"),
    state = path.join(base, "native-state"),
    addon = path.join(base, "reviewed-addon.ts");
  fs.mkdirSync(cwd, { recursive: true });
  fs.mkdirSync(agentDir, { recursive: true });
  const defs = [
    definition,
    {
      ...definition,
      name: "ask_user_question",
      description: "Synthetic question",
    },
    {
      ...definition,
      name: "ketch_search",
      description: "Synthetic read-only public research",
    },
  ];
  fs.writeFileSync(
    addon,
    "export default pi => { for (const t of " +
      JSON.stringify(defs) +
      ") pi.registerTool({...t, label:t.name, execute:async()=>({content:[{type:'text',text:'Synthetic passive evidence: yes'}],details:{}})}); }",
  );
  process.env.CHRYSALIS_STATE_ROOT = state;
  const onboarding = await import("../src/app/onboarding.ts");
  const setup = onboarding.prepareOnboarding({
    vault: path.join(cwd, "Synthetic Vault"),
    state,
    timezone: "Etc/UTC",
  });
  onboarding.approveSetup(
    state,
    setup.proposal_digest,
    "synthetic native fixture",
  );
  await onboarding.applySetup(state, setup.proposal_digest);
  policy(state, addon, defs);
  const settings = SettingsManager.inMemory({});
  const loader = new DefaultResourceLoader({
    cwd,
    agentDir,
    settingsManager: settings,
    noContextFiles: true,
    noExtensions: true,
    noSkills: true,
    additionalExtensionPaths: [
      addon,
      path.join(PACKAGE_ROOT, "extensions/chrysalis.ts"),
    ],
  });
  await loader.reload();
  assert.deepEqual(loader.getExtensions().errors, []);
  const effective = loader
    .getExtensions()
    .extensions.find((e) => e.path === addon)!;
  const effectivePolicy = JSON.parse(
    fs.readFileSync(path.join(state, "host-addons.json"), "utf8"),
  );
  for (const b of effectivePolicy.tools) {
    const t = effective.tools.get(b.name)!;
    b.definition_sha256 = conversationToolDigest({
      ...t.definition,
      exposure: t.definition.exposure ?? "direct",
      sourceInfo: t.sourceInfo,
    });
  }
  fs.writeFileSync(
    path.join(state, "host-addons.json"),
    JSON.stringify(effectivePolicy),
  );
  const { session } = await createAgentSession({
    cwd,
    agentDir,
    resourceLoader: loader,
    settingsManager: settings,
    sessionManager: SessionManager.inMemory(cwd),
  });
  try {
    await session.bindExtensions({});
    for (const t of defs) assert(session.getActiveToolNames().includes(t.name));
    const runner: any = (session as any)._extensionRunner;
    session.agent.state.messages.push({
      role: "assistant",
      content: [
        { type: "toolCall", id: "synthetic", name: "codemode", arguments: {} },
      ],
      api: "openai-responses",
      provider: "synthetic",
      model: "fixture",
      stopReason: "toolUse",
      timestamp: Date.now(),
      usage: {
        input: 0,
        output: 0,
        cacheRead: 0,
        cacheWrite: 0,
        totalTokens: 0,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
      },
    });
    const context = runner.createToolContext("synthetic", undefined);
    for (const t of defs)
      assert.match(
        JSON.stringify(await context.executeTool(t.name, {})),
        /Synthetic passive/,
      );
    session.setActiveToolsByName([
      ...session.getActiveToolNames(),
      "write",
      "bash",
    ]);
    const target = path.join(cwd, "not-approved.md");
    assert.match(
      JSON.stringify(
        await context.executeTool("write", {
          path: target,
          content: "unapproved",
        }),
      ),
      /unavailable|blocked|reviewed operations/i,
    );
    assert(!fs.existsSync(target));
    assert.match(
      JSON.stringify(
        await context.executeTool("bash", { command: "echo unapproved" }),
      ),
      /unavailable|blocked|reviewed operations/i,
    );
    assert.match(
      JSON.stringify(
        await context.executeTool("chrysalis_operation", {
          operation: "approve",
          arguments: {},
        }),
      ),
      /Validation failed for tool.*chrysalis_operation/,
    );
    assert(!session.getActiveToolNames().includes("subagent"));
  } finally {
    await (session as any)._extensionRunner.emit({
      type: "session_shutdown",
      reason: "exit",
    });
    session.dispose();
    delete process.env.CHRYSALIS_STATE_ROOT;
  }
});

test("scoped grants distrust hints, recheck metadata, and apply the same native review to nested calls", async () => {
  const state = path.join(base, "generic-policy"),
    origin = path.join(base, "generic.ts");
  process.env.CHRYSALIS_STATE_ROOT = state;
  fs.mkdirSync(state, { recursive: true });
  let info: any = {
    ...definition,
    name: "friendly_read",
    exposure: "deferred",
    namespace: { name: "independent" },
    annotations: { readOnlyHint: true, destructiveHint: false },
    sourceInfo: {
      path: origin,
      source: "package",
      scope: "user",
      origin: "package",
    },
  };
  const api: any = { getAllTools: () => [info] },
    gate = installCompanions(api),
    event = { toolName: info.name, input: { query: "public topic" } };
  try {
    assert(
      (await gate.authorize(event, { hasUI: false }))?.block,
      "hints grant no authority",
    );
    fs.writeFileSync(
      path.join(state, "host-addons.json"),
      JSON.stringify({
        version: 2,
        skill_roots: [],
        tools: [
          {
            name: info.name,
            mode: "review",
            extension_path: origin,
            definition_sha256: conversationToolDigest(info),
          },
        ],
      }),
    );
    assert((await gate.authorize(event, { hasUI: false }))?.block);
    let reviews = 0;
    const ctx = {
      hasUI: true,
      ui: {
        confirm: async () => {
          reviews++;
          return true;
        },
      },
    };
    assert.equal(await gate.authorize(event, ctx), undefined);
    assert.equal(
      await gate.authorize({ ...event, parentToolCallId: "orchestrator" }, ctx),
      undefined,
    );
    assert.equal(
      reviews,
      2,
      "nested and direct calls each require their own review",
    );
    assert(
      (
        await gate.authorize(
          { ...event, input: { path: path.join(state, "approvals.json") } },
          ctx,
        )
      )?.block,
    );
    const original = info;
    info = { ...info, annotations: undefined };
    assert((await gate.authorize(event, ctx))?.block);
    info = { ...original, namespace: { name: "changed" } };
    assert((await gate.authorize(event, ctx))?.block);
    info = original;
    const changedDuringReview = {
      hasUI: true,
      ui: {
        confirm: async () => {
          info = { ...info, exposure: "hidden" };
          return true;
        },
      },
    };
    assert((await gate.authorize(event, changedDuringReview))?.block);
    assert(!gate.allowed(info.name));
  } finally {
    delete process.env.CHRYSALIS_STATE_ROOT;
  }
});

test("MCP grants bind configuration and legacy package skill roots keep their accepted layout", async () => {
  const state = path.join(base, "mcp-grant"),
    agent = path.join(base, "mcp-agent"),
    oldAgent = process.env.PI_CODING_AGENT_DIR;
  fs.mkdirSync(state, { recursive: true });
  fs.mkdirSync(agent, { recursive: true });
  process.env.CHRYSALIS_STATE_ROOT = state;
  process.env.PI_CODING_AGENT_DIR = agent;
  const info: any = {
    ...definition,
    name: "mcp__independent__read",
    exposure: "deferred",
    namespace: { name: "mcp__independent" },
    sourceInfo: {
      path: "builtin:mcp",
      source: "builtin",
      scope: "temporary",
      origin: "top-level",
    },
  };
  const api: any = { getAllTools: () => [info], getMcpServers: () => [] };
  try {
    const { mcpConfiguration } = await import("../extensions/sources.ts");
    const file = path.join(agent, "mcp.json");
    fs.writeFileSync(
      file,
      JSON.stringify({
        mcpServers: { independent: { command: "reviewed-server" } },
      }),
    );
    fs.writeFileSync(
      path.join(state, "host-addons.json"),
      JSON.stringify({
        version: 2,
        skill_roots: [],
        tools: [
          {
            name: info.name,
            mode: "read-only",
            extension_path: "builtin:mcp",
            definition_sha256: conversationToolDigest(info),
            mcp_configuration: mcpConfiguration(api, "mcp__independent")
              .identity,
          },
        ],
      }),
    );
    const gate = installCompanions(api);
    assert(gate.allowed(info.name));
    fs.writeFileSync(
      file,
      JSON.stringify({
        mcpServers: { independent: { command: "different-server" } },
      }),
    );
    assert(
      !gate.allowed(info.name),
      "same schema and tool origin cannot preserve a changed server grant",
    );
    const pkg = path.join(base, "legacy-package"),
      entry = path.join(pkg, "extensions/addon.ts"),
      skill = path.join(pkg, "skills/research");
    fs.mkdirSync(path.dirname(entry), { recursive: true });
    fs.mkdirSync(skill, { recursive: true });
    fs.writeFileSync(path.join(skill, "SKILL.md"), "Synthetic research");
    const legacy: any = { ...definition, name: "ketch_search" };
    const { digest } = await import("../src/platforms/filesystem.ts");
    fs.writeFileSync(
      path.join(state, "host-addons.json"),
      JSON.stringify({
        version: 1,
        skill_roots: [skill],
        tools: [
          {
            name: legacy.name,
            extension_path: entry,
            definition_sha256: digest({
              name: legacy.name,
              description: legacy.description,
              parameters: legacy.parameters,
              promptGuidelines: legacy.promptGuidelines,
            }),
          },
        ],
      }),
    );
    assert(installCompanions(api).readableSkill(path.join(skill, "SKILL.md")));
  } finally {
    delete process.env.CHRYSALIS_STATE_ROOT;
    if (oldAgent === undefined) delete process.env.PI_CODING_AGENT_DIR;
    else process.env.PI_CODING_AGENT_DIR = oldAgent;
  }
});
