import test from "node:test";
import { runToolCall } from "@earendil-works/pi-agent-core";
import {
  installSources,
  maskedInput,
  memoryOnlyView,
} from "../extensions/sources.ts";
import { TOOL_SCHEMAS, SERVER_NAME } from "../src/integrations/contracts.ts";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import chrysalis from "../extensions/chrysalis.ts";
import { PACKAGE_ROOT, exists } from "../src/platforms/filesystem.ts";
import { externalState, selectedContext } from "../src/storage/context.ts";
import { dispatch } from "../src/app/operations.ts";
import { serializeRecord, readRecord } from "../src/storage/records.ts";
import { confined } from "../src/platforms/filesystem.ts";
import { vaultState } from "../src/storage/context.ts";
import { configuredZone } from "../src/core/runtime.ts";
import { nowStamp } from "../src/time/timezone.ts";
import { documentFolderStatus } from "../src/core/documents.ts";
import {
  DefaultResourceLoader,
  SettingsManager,
  SessionManager,
  createAgentSession,
  createCodemodeExtension,
  createMcpExtension,
} from "@earendil-works/pi-coding-agent";

if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(
    externalState(process.env.TEST_SCRATCH),
    "pi-" + randomUUID(),
  ),
  state = path.join(base, "state"),
  vault = path.join(base, "Research Notes");
fs.mkdirSync(base, { recursive: true });
let registration: any, tool: any;
const handlers: Record<string, Function> = {},
  messages: string[] = [],
  notifications: string[] = [];
const pi: any = {
  registerMcpServer: () => {},
  registerToolRenderer: () => {},
  getSettings: () => ({}),
  getMcpServers: () => [],
  unregisterMcpServer: () => {},
  getActiveTools: () => [],
  getAllTools: () => [],
  registerTool: (value: any) => {
    tool = value;
  },
  registerCommand: (_name: string, value: any) => {
    registration = value;
  },
  on: (name: string, handler: Function) => {
    handlers[name] = handler;
  },
  setActiveTools: () => {},
  sendUserMessage: (text: string) => {
    messages.push(text);
  },
};
const ctx: any = {
  hasUI: true,
  cwd: base,
  ui: {
    select: async () => "Later",
    input: async (title: string) =>
      title.includes("Name") ? "Research Notes" : base,
    custom: async (factory: any) => {
      let result: string | undefined;
      const component = factory(
        { terminal: { rows: 25 }, requestRender() {} },
        { fg: (_color: string, text: string) => text },
        null,
        (value: string | undefined) => {
          result = value;
        },
      );
      for (const key of base) component.handleInput(key);
      component.handleInput("\r");
      return result;
    },
    editor: async (_title: string, prefill: string) => prefill,
    confirm: async () => false,
    notify: (text: string) => notifications.push(text),
  },
};

test("source gate rejects effective registration overrides, wrong origins and drifted MCP schemas", () => {
  let registered: any, info: any;
  const api: any = {
    ...pi,
    registerMcpServer: (name: string, config: any) => {
      registered = {
        name,
        config,
        extensionPath: path.join(PACKAGE_ROOT, "extensions/chrysalis.ts"),
      };
    },
    getMcpServers: () => [registered],
    getAllTools: () => [info],
  };
  const gate = installSources(api);
  const name = "mcp__" + SERVER_NAME + "__integration_status";
  info = {
    name,
    parameters: TOOL_SCHEMAS.integration_status,
    namespace: { name: "mcp__" + SERVER_NAME },
    sourceInfo: { path: "builtin:mcp", source: "builtin" },
    exposure: "codemode",
  };
  assert(gate(name));
  info.exposure = "deferred";
  assert(gate(name), "Pi maps MCP codemode exposure to deferred");
  info.exposure = "hidden";
  assert(!gate(name));
  info.exposure = "codemode";
  info.parameters = { ...info.parameters, additionalProperties: true };
  assert(!gate(name));
  info.parameters = TOOL_SCHEMAS.integration_status;
  info.sourceInfo.path = "untrusted.ts";
  assert(!gate(name));
  info.sourceInfo.path = "builtin:mcp";
  registered.config = { ...registered.config, command: "untrusted" };
  assert(!gate(name));
  assert(!gate("mcp__other__integration_status"));
});

test("native secret input masks and clears; restricted evidence cannot invoke an external editor", async () => {
  let component: any;
  const native: any = {
    hasUI: true,
    ui: {
      editor: () => {
        throw Error("External editor forbidden");
      },
      custom: async (factory: any) => {
        let result: any;
        component = factory(
          { requestRender: () => {}, terminal: { rows: 25 } },
          null,
          null,
          (value: any) => {
            result = value;
          },
        );
        component.handleInput("synthetic-private-key");
        assert(
          !component.render(80).join("\n").includes("synthetic-private-key"),
        );
        component.handleInput("\r");
        return result;
      },
    },
  };
  assert.equal(await maskedInput(native, "API key"), "synthetic-private-key");
  assert(!component.render(80).join("\n").includes("*"));
  native.ui.custom = async (factory: any) => {
    component = factory(
      { requestRender: () => {}, terminal: { rows: 25 } },
      null,
      null,
      () => {},
    );
    assert(
      component.render(80).join("\n").includes("synthetic sleep evidence"),
    );
    component.handleInput("\u0007");
    component.handleInput("\u001b");
    assert(
      !component.render(80).join("\n").includes("synthetic sleep evidence"),
    );
  };
  await memoryOnlyView(
    native,
    "Health native review",
    "synthetic sleep evidence",
  );
});

test("native operator onboarding reviews before writes, resumes and requires human-path confirmation", async () => {
  process.env.CHRYSALIS_STATE_ROOT = state;
  delete process.env.CHRYSALIS_VAULT_PATH;
  await chrysalis(pi);
  assert(!exists(state));
  await registration.handler("onboard", ctx);
  assert(!exists(vault));
  assert.equal(messages.length, 0);
  ctx.ui.editor = async (_title: string, value: string) => value + "edited";
  ctx.ui.confirm = async () => true;
  await registration.handler("onboard", ctx);
  assert(!exists(vault));
  assert(notifications.some((n) => n.includes("edited")));
  ctx.ui.editor = async (_title: string, value: string) => value;
  await registration.handler("onboard", ctx);
  assert(exists(path.join(vault, ".chrysalis-vault.json")));
  assert.equal(selectedContext(state).vault, path.resolve(vault));
  await registration.handler("onboard", ctx);
  assert.equal(messages.length, 2);
  assert.match(messages[0], /conversational/);
  assert.match(messages[0], /optional folder/);
  assert.match(messages[0], /project/);
  assert.match(messages[0], /atomic.note/);
  delete process.env.CHRYSALIS_STATE_ROOT;
});
test("bootstrap errors are useful; model cannot run approval or bypass life tools", async () => {
  process.env.CHRYSALIS_STATE_ROOT = path.join(base, "unconfigured-state");
  const error: any = await tool.execute("fixture", { operation: "doctor" });
  assert.equal(error.details.status, "error");
  assert.match(error.details.message, /onboard/);
  assert.equal(
    (
      await handlers.tool_call(
        { toolName: "bash", input: { command: "anything" } },
        ctx,
      )
    ).block,
    true,
  );
  assert.equal(
    (
      await handlers.tool_call(
        {
          toolName: "read",
          input: { path: path.join(PACKAGE_ROOT, "package.json") },
        },
        ctx,
      )
    ).block,
    true,
  );
  assert.equal(
    (
      await handlers.tool_call(
        {
          toolName: "read",
          input: {
            path: path.join(PACKAGE_ROOT, "skills/chrysalis-daily/SKILL.md"),
          },
        },
        ctx,
      )
    ).block,
    true,
  );
  assert.equal(
    (
      await tool.execute("fixture", {
        operation: "approve",
        arguments: { proposal_digest: "0".repeat(64) },
      })
    ).details.status,
    "error",
  );
  delete process.env.CHRYSALIS_STATE_ROOT;
});

test("native per-note vetting rejects edits or any decline before the batch can write", async () => {
  process.env.CHRYSALIS_STATE_ROOT = state;
  const selected = selectedContext(state),
    now = nowStamp(configuredZone(selected), "2026-10-08T17:00:00+00:00");
  const records = ["lexer", "parser"].map((slug) => ({
    path: "Slipbox/20261008120000-" + slug + ".md",
    if_revision: null,
    document: serializeRecord(
      {
        type: "zettel",
        id: "20261008120000-" + slug,
        title: "One " + slug + " claim",
        dateCreated: now,
        tags: ["concept/compilers"],
        summary: "A single claim.",
        provenance_kind: "inference",
      },
      "# One claim\n\nEvidence and uncertainty for " + slug + ".\n",
    ),
  }));
  const draft: any = await dispatch(selected, "propose", { records });
  const untouched = () => {
    for (const record of records) assert(!exists(confined(vault, record.path)));
    assert(
      !exists(
        confined(
          vaultState(selected),
          "approvals/" + draft.proposal_digest + ".json",
        ),
      ),
    );
  };
  try {
    let decisions = [true, false];
    ctx.ui.editor = async (_title: string, text: string) => text;
    ctx.ui.confirm = async () => decisions.shift() ?? false;
    await registration.handler("approve " + draft.proposal_digest, ctx);
    untouched();
    decisions = [true, true, false];
    await registration.handler("approve " + draft.proposal_digest, ctx);
    untouched();
    ctx.ui.editor = async (_title: string, text: string) => text + "edited";
    ctx.ui.confirm = async () => {
      throw Error("Edited note must not reach confirmation");
    };
    await registration.handler("approve " + draft.proposal_digest, ctx);
    untouched();
    const shown: string[] = [],
      confirmations: string[] = [];
    ctx.ui.editor = async (title: string, text: string) => {
      if (title.startsWith("Vet atomic note:")) shown.push(text);
      return text;
    };
    ctx.ui.confirm = async (title: string) => {
      confirmations.push(title);
      return true;
    };
    await registration.handler("approve " + draft.proposal_digest, ctx);
    assert.deepEqual(
      shown,
      records.map((record) => record.document),
    );
    assert.deepEqual(confirmations, [
      "Approve this atomic note?",
      "Approve this atomic note?",
      "Approve this exact saved proposal?",
    ]);
    for (const record of records)
      assert.equal(readRecord(vault, record.path).document, record.document);
  } finally {
    ctx.ui.editor = async (_title: string, text: string) => text;
    ctx.ui.confirm = async () => true;
    delete process.env.CHRYSALIS_STATE_ROOT;
  }
});

test("malformed private credential files produce only sanitized native notifications", async () => {
  const file = path.join(base, "malformed-client.json");
  const canary = "synthetic-private-import-canary";
  fs.writeFileSync(file, '{"client_secret":"' + canary + '" broken');
  process.env.CHRYSALIS_STATE_ROOT = state;
  const notices: string[] = [];
  try {
    await registration.handler("integrations setup", {
      ...ctx,
      ui: {
        ...ctx.ui,
        select: async () => "google-tasks",
        confirm: async () => true,
        input: async (title: string) =>
          title.includes("Unique")
            ? "malformed-import"
            : title.includes("account alias")
              ? "primary"
              : title.includes("project ID")
                ? "fixture-project"
                : file,
        notify: (s: string) => notices.push(s),
      },
    });
    assert.deepEqual(notices, ["invalid_credential_file"]);
    assert(!JSON.stringify(notices).includes(canary));
  } finally {
    delete process.env.CHRYSALIS_STATE_ROOT;
  }
});
test("actual Pi SDK discovers nine skills and invokes the new tool without Python", async () => {
  process.env.CHRYSALIS_STATE_ROOT = state;
  process.env.CHRYSALIS_VAULT_PATH = vault;
  delete process.env.CHRYSALIS_PYTHON;
  const cwd = path.join(base, "cwd"),
    agentDir = path.join(base, "profile");
  fs.mkdirSync(cwd, { recursive: true });
  fs.mkdirSync(agentDir, { recursive: true });
  const lateAddon = path.join(base, "late-addon.ts");
  fs.writeFileSync(
    lateAddon,
    'export default function(pi) {\n pi.registerCommand("fixture_late", {handler:async()=>{\n  pi.registerTool({name:"late_friendly_read",label:"Unverified late tool",exposure:"codemode",\n   description:"Unverified read-only claim",annotations:{readOnlyHint:true,destructiveHint:false},\n   parameters:{type:"object",properties:{}},\n   execute:async()=>{throw Error("Ungranted tool must not execute");}\n  });\n }});\n}',
  );
  let debugPi: any;
  const settings = SettingsManager.inMemory({ packages: [PACKAGE_ROOT] }),
    loader = new DefaultResourceLoader({
      cwd,
      agentDir,
      settingsManager: settings,
      noContextFiles: true,
      additionalExtensionPaths: [lateAddon],
      extensionFactories: [
        (pi) => {
          debugPi = pi;
        },
        {
          name: "codemode",
          builtin: true,
          factory: createCodemodeExtension(),
          replaceable: true,
        },
        {
          name: "mcp",
          builtin: true,
          factory: createMcpExtension(),
          replaceable: true,
        },
      ],
    });
  await loader.reload();
  assert.equal(loader.getSkills().skills.length, 9);
  assert(
    loader.getSkills().skills.some((s) => s.name === "chrysalis-learning"),
  );
  assert.deepEqual(loader.getExtensions().errors, []);
  assert(
    loader.getExtensions().extensions.some((e) => e.tools.has("codemode")),
    JSON.stringify(
      loader
        .getExtensions()
        .extensions.map((e) => ({ path: e.path, tools: [...e.tools.keys()] })),
    ),
  );
  const { session } = await createAgentSession({
    cwd,
    agentDir,
    resourceLoader: loader,
    settingsManager: settings,
    sessionManager: SessionManager.inMemory(cwd),
  });
  try {
    const extensionErrors: any[] = [];
    await session.bindExtensions({
      onError: (error) => extensionErrors.push(error),
    });
    assert.deepEqual(extensionErrors, []);
    assert(
      session.getActiveToolNames().includes("codemode"),
      JSON.stringify(session.getActiveToolNames()),
    );
    const usage = {
      input: 0,
      output: 0,
      cacheRead: 0,
      cacheWrite: 0,
      totalTokens: 0,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
    };
    session.agent.state.messages.push({
      role: "assistant",
      content: [
        {
          type: "toolCall",
          id: "synthetic-parent",
          name: "chrysalis_operation",
          arguments: { operation: "doctor" },
        },
      ],
      api: "openai-responses",
      provider: "synthetic",
      model: "fixture",
      usage,
      stopReason: "toolUse",
      timestamp: Date.now(),
    });
    const context = (session as any)._extensionRunner.createToolContext(
        "synthetic-parent",
        undefined,
      ),
      out = await context.executeTool("chrysalis_operation", {
        operation: "doctor",
        arguments: {},
      }),
      actual = out.result ?? out;
    assert.equal(actual.details.status, "ok", JSON.stringify(actual));
    const read = await context.executeTool("read", {
      path: path.join(PACKAGE_ROOT, "skills/chrysalis-daily/SKILL.md"),
    });
    assert(
      (read.result ?? read).content.some(
        (c) => c.type === "text" && c.text.includes("chrysalis_operation"),
      ),
    );
    const denied = await context.executeTool("read", {
      path: path.join(vault, "System/Memory.md"),
    });
    assert.match(JSON.stringify(denied), /unavailable|outside|blocked/i);
    const executeCode = (args: any) =>
      runToolCall(
        {
          type: "toolCall",
          id: "synthetic-codemode",
          name: "codemode",
          arguments: args,
        },
        {
          tools: session.agent.state.tools,
          assistantMessage: session.agent.state.messages.at(-1) as any,
          context: session.agent.state,
          beforeToolCall: session.agent.beforeToolCall,
          afterToolCall: session.agent.afterToolCall,
        },
      );
    const code = await executeCode({
      code: 'const r = await tools.mcp__chrysalis_sources__integration_status({}); if (r.isError) throw Error("MCP error"); text({status:r.structuredContent.status, count:r.structuredContent.integrations.length, modelsAvailable:typeof models!=="undefined"});',
    });
    const output = JSON.stringify(code.result ?? code);
    assert.match(
      output,
      /Script completed/,
      JSON.stringify({
        output,
        servers: debugPi.getMcpServers(),
        tools: debugPi
          .getAllTools()
          .filter((t: any) => t.name.includes("mcp__chrysalis")),
      }),
    );
    assert.match(output, /modelsAvailable.*true/);
    assert.match(output, /status.*ok/);
    await session.prompt("/fixture_late");
    const late = await executeCode({
      code: "await tools.late_friendly_read({});",
    });
    assert.match(
      JSON.stringify(late),
      /No exact scoped grant/,
      JSON.stringify({
        late,
        registered: debugPi
          .getAllTools()
          .filter((t: any) => t.name.includes("late_")),
        active: debugPi.getActiveTools(),
      }),
    );
    const blocked = await executeCode({
      code:
        "await tools.read({path:" +
        JSON.stringify(path.join(vault, "System/Memory.md")) +
        "});",
    });
    assert.match(
      JSON.stringify(blocked),
      /Script failed|blocked|reviewed operations/i,
    );
    await session.reload();
    assert.deepEqual(extensionErrors, []);
    const reloaded = await executeCode({
      code: "text(await tools.mcp__chrysalis_sources__integration_status({}));",
    });
    assert.match(JSON.stringify(reloaded), /Script completed/);
    const stillDenied = await executeCode({
      code:
        "await tools.read({path:" +
        JSON.stringify(path.join(vault, "System/Memory.md")) +
        "});",
    });
    assert.match(JSON.stringify(stillDenied), /Script failed|blocked|outside/i);
  } finally {
    await (session as any)._extensionRunner.emit({
      type: "session_shutdown",
      reason: "exit",
    });
    session.dispose();
    delete process.env.CHRYSALIS_STATE_ROOT;
    delete process.env.CHRYSALIS_VAULT_PATH;
  }
});

test("unapproved setup can restart with corrected folder and initial zone", async () => {
  const localState = path.join(base, "restart-state"),
    oldVault = path.join(base, "Declined vault"),
    newVault = path.join(base, "Corrected vault");
  process.env.CHRYSALIS_STATE_ROOT = localState;
  delete process.env.CHRYSALIS_VAULT_PATH;
  ctx.ui.input = async (title: string) =>
    title.includes("Name") ? "Declined vault" : base;
  ctx.ui.confirm = async () => false;
  ctx.ui.editor = async (_title: string, value: string) => value;
  await registration.handler("onboard", ctx);
  const pointer = JSON.parse(
    fs.readFileSync(path.join(localState, "pending-setup.json"), "utf8"),
  );
  assert(!exists(oldVault));
  ctx.ui.input = async (title: string) =>
    title.includes("Name") ? "Corrected vault" : base;
  ctx.ui.confirm = async () => true;
  await registration.handler("onboard --restart --zone Asia/Kathmandu", ctx);
  assert(!exists(oldVault));
  assert(exists(path.join(newVault, ".chrysalis-vault.json")));
  assert.equal(selectedContext(localState).vault, path.resolve(newVault));
  const memory = fs.readFileSync(
    path.join(newVault, "System/Memory.md"),
    "utf8",
  );
  assert.match(memory, /Asia\/Kat(?:h)?mandu/);
  await registration.handler("approve " + pointer.proposal_digest, ctx);
  assert(!exists(oldVault));
  assert(notifications.some((n) => n.includes("replaced")));
  delete process.env.CHRYSALIS_STATE_ROOT;
});

test("native life-document selection and copies have separate cancel, edit and decline boundaries", async () => {
  process.env.CHRYSALIS_STATE_ROOT = state;
  delete process.env.CHRYSALIS_VAULT_PATH;
  const selected = selectedContext(state),
    source = path.join(base, "Life documents");
  fs.mkdirSync(source, { recursive: true });
  fs.writeFileSync(
    path.join(source, "portfolio.txt"),
    "A parser constructs a syntax tree.",
  );
  try {
    assert.equal(documentFolderStatus(selected).status, "not_selected");
    ctx.ui.input = async () => undefined;
    await registration.handler("documents", ctx);
    assert.equal(documentFolderStatus(selected).status, "not_selected");
    ctx.ui.input = async () => source;
    ctx.ui.editor = async (_title: string, value: string) => value;
    ctx.ui.confirm = async () => false;
    await registration.handler("documents", ctx);
    assert.equal(documentFolderStatus(selected).status, "not_selected");
    ctx.ui.editor = async (_title: string, value: string) => value + "edited";
    ctx.ui.confirm = async () => {
      throw Error("Edited scope must not reach confirmation");
    };
    await registration.handler("documents", ctx);
    assert.equal(documentFolderStatus(selected).status, "not_selected");
    const confirmationTitles: string[] = [];
    ctx.ui.editor = async (_title: string, value: string) => value;
    ctx.ui.confirm = async (title: string) => {
      confirmationTitles.push(title);
      return true;
    };
    await registration.handler("documents", ctx);
    assert.equal(documentFolderStatus(selected).status, "selected");
    assert.match(
      messages.at(-1)!,
      /roadmap context, candidate projects and individually vetted atomic notes/,
    );
    const plan: any = await dispatch(selected, "documents.prepare", {
      paths: ["portfolio.txt"],
    });
    const target = confined(vault, plan.manifest.entries[0].destination);
    assert(!exists(target));
    await assert.rejects(
      dispatch(selected, "documents.apply", {
        proposal_digest: plan.proposal_digest,
      }),
      /approval_required/,
    );
    ctx.ui.confirm = async () => false;
    await registration.handler("approve " + plan.proposal_digest, ctx);
    assert(!exists(target));
    ctx.ui.editor = async (_title: string, value: string) => value + "edited";
    await registration.handler("approve " + plan.proposal_digest, ctx);
    assert(!exists(target));
    ctx.ui.editor = async (_title: string, value: string) => value;
    ctx.ui.confirm = async (title: string) => {
      confirmationTitles.push(title);
      return true;
    };
    await registration.handler("approve " + plan.proposal_digest, ctx);
    assert.equal(
      fs.readFileSync(target, "utf8"),
      "A parser constructs a syntax tree.",
    );
    assert.equal(
      fs.readFileSync(path.join(source, "portfolio.txt"), "utf8"),
      "A parser constructs a syntax tree.",
    );
    assert.deepEqual(confirmationTitles, [
      "Use this life-documents folder?",
      "Copy these exact originals into the vault?",
    ]);
    assert(
      notifications.some((value) =>
        value.includes('"knowledge_records_created":false'),
      ),
    );
    const previous = documentFolderStatus(selected);
    ctx.ui.input = async () => {
      throw Error("Status must not prompt for a folder");
    };
    await registration.handler("documents --status", ctx);
    assert.deepEqual(documentFolderStatus(selected), previous);
  } finally {
    ctx.ui.editor = async (_title: string, value: string) => value;
    ctx.ui.confirm = async () => true;
    delete process.env.CHRYSALIS_STATE_ROOT;
  }
});

test("a configured same-schema MCP override cannot impersonate chrysalis's extension registration", async () => {
  const cwd = path.join(base, "override"),
    agentDir = path.join(cwd, "agent"),
    selectedState = path.join(cwd, "state"),
    previousAgent = process.env.PI_CODING_AGENT_DIR;
  fs.mkdirSync(agentDir, { recursive: true });
  process.env.PI_CODING_AGENT_DIR = agentDir;
  process.env.CHRYSALIS_STATE_ROOT = selectedState;
  const { createRequire } = await import("node:module"),
    require = createRequire(import.meta.url);
  const configuration = {
    command: process.execPath,
    args: [
      "--import",
      require.resolve("tsx"),
      path.join(PACKAGE_ROOT, "src/mcp/server.ts"),
      "--state",
      selectedState,
    ],
    env: {
      TSX_DISABLE_CACHE: "1",
      TSX_TSCONFIG_PATH: path.join(PACKAGE_ROOT, "tsconfig.json"),
    },
  };
  fs.writeFileSync(
    path.join(agentDir, "mcp.json"),
    JSON.stringify({
      mcpServers: {
        "chrysalis-sources": configuration,
      },
    }),
  );
  let api: any;
  const settings = SettingsManager.inMemory({ packages: [PACKAGE_ROOT] }),
    loader = new DefaultResourceLoader({
      cwd,
      agentDir,
      settingsManager: settings,
      noContextFiles: true,
      extensionFactories: [
        {
          name: "codemode",
          builtin: true,
          replaceable: true,
          factory: createCodemodeExtension(),
        },
        {
          name: "mcp",
          builtin: true,
          replaceable: true,
          factory: createMcpExtension(),
        },
        (pi) => {
          api = pi;
        },
      ],
    });
  let session: any;
  try {
    await loader.reload();
    assert.deepEqual(loader.getExtensions().errors, []);
    ({ session } = await createAgentSession({
      cwd,
      agentDir,
      settingsManager: settings,
      resourceLoader: loader,
      sessionManager: SessionManager.inMemory(cwd),
    }));
    await session.bindExtensions({});
    const message: any = {
      role: "assistant",
      content: [],
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
    };
    session.agent.state.messages.push(message);
    const out = await runToolCall(
      {
        type: "toolCall",
        id: "override",
        name: "codemode",
        arguments: {
          code: "await tools.mcp__chrysalis_sources__integration_status({});",
        },
      },
      {
        tools: session.agent.state.tools,
        assistantMessage: message,
        context: session.agent.state,
        beforeToolCall: session.agent.beforeToolCall,
        afterToolCall: session.agent.afterToolCall,
      },
    );
    assert.match(JSON.stringify(out), /Required package.*unavailable/);
    assert(
      api.getMcpServers().some((s: any) => s.name === SERVER_NAME),
      "the extension registration still exists, so checking it alone is insufficient",
    );
    assert(
      api
        .getAllTools()
        .some(
          (t: any) => t.name === "mcp__chrysalis_sources__integration_status",
        ),
      "the actual configured server has the identical schema and namespace",
    );
  } finally {
    if (session) {
      await session._extensionRunner.emit({
        type: "session_shutdown",
        reason: "exit",
      });
      session.dispose();
    }
    if (previousAgent === undefined) delete process.env.PI_CODING_AGENT_DIR;
    else process.env.PI_CODING_AGENT_DIR = previousAgent;
    delete process.env.CHRYSALIS_STATE_ROOT;
  }
});
