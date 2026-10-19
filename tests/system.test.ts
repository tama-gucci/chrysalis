import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { installSystem } from "../extensions/system.ts";
import {
  PACKAGE_ROOT,
  atomicJSON,
  digest,
  raw,
  withLock,
} from "../src/platforms/filesystem.ts";
import {
  approveSystem,
  assertSystemIdle,
  assertSystemVault,
  beginPrivileged,
  completePrivileged,
  assertBackendTarget,
  assertSameDisk,
  configIdentity,
  configurationIdentity,
  confinedSystemFile,
  currentOperation,
  LEDGER_PATH,
  loadSystemConfig,
  projectSystemLedger,
  recordSystem,
  requireSystemScope,
  selectDisks,
  type SystemConfig,
} from "../src/system/state.ts";
import {
  command,
  assertInstalledLedgerProof,
  systemLedgerAuthorization,
  installedSystemProfile,
  copyHandoffFile,
  inspectTarget,
  unmountRecoveryTarget,
  installTarget,
  reconcileInstalled,
} from "../src/system/native.ts";

if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(process.env.TEST_SCRATCH, "system-" + randomUUID());
fs.mkdirSync(base, { recursive: true });
function fixture(mode: SystemConfig["mode"] = "installed") {
  const dir = path.join(base, randomUUID()),
    configuration = path.join(dir, "configuration"),
    state = path.join(dir, "state");
  fs.mkdirSync(configuration, { recursive: true });
  fs.mkdirSync(state);
  fs.writeFileSync(
    path.join(configuration, "flake.nix"),
    "{ outputs = _: {}; }\n",
  );
  const commands: any = Object.fromEntries(
    [
      "nix",
      "sudo",
      "disko",
      "lsblk",
      "findmnt",
      "facter",
      "mkpasswd",
      "nixAgent",
      "node",
    ].map((n) => [n, process.execPath]),
  );
  const c: SystemConfig = {
    version: 1,
    mode,
    configuration,
    host: "fixture",
    state,
    source: PACKAGE_ROOT,
    commands,
  };
  const file = path.join(dir, "native.json");
  atomicJSON(file, c);
  return { dir, c, file };
}
function vault() {
  const root = path.join(base, "vault-" + randomUUID());
  fs.mkdirSync(root);
  atomicJSON(path.join(root, ".chrysalis-vault.json"), {
    schema_version: "1",
    vault_id: randomUUID(),
  });
  return root;
}
test("system configuration is opt-in and rejects overlapping roots and invalid commands", () => {
  assert.equal(loadSystemConfig(""), undefined);
  const { c, file } = fixture();
  assert.equal(loadSystemConfig(file)?.host, "fixture");
  atomicJSON(file, { ...c, configuration: c.state });
  assert.throws(() => loadSystemConfig(file), /overlap/);
  atomicJSON(file, { ...c, commands: { ...c.commands, sudo: "sudo" } });
  assert.throws(() => loadSystemConfig(file), /pinned/);
});
test("native outcome binds exact configuration, machine and backend without granting other hosts", async () => {
  const { c } = fixture();
  assert.throws(() => requireSystemScope(c), /native/);
  const op = approveSystem(c, "Install a synthetic package", "backend-A");
  assert.equal(requireSystemScope(c, "backend-A").id, op.id);
  assert.throws(() => requireSystemScope(c, "backend-B"), /backend/);
  assert.throws(() => requireSystemScope({ ...c, host: "other" }), /scope/);
  assert.throws(
    () => assertBackendTarget(c, { flake_uri: c.configuration + "#other" }),
    /exact/,
  );
  assert.throws(
    () => assertBackendTarget(c, { mode: "home-manager" }),
    /NixOS/,
  );
  assertBackendTarget(c, {
    flake_uri: c.configuration + "#fixture",
    mode: "nixos",
  });
  await recordSystem(c, op.id, "closed");
  assert.throws(() => requireSystemScope(c), /native/);
});
test("disk selection excludes running media, all mounted disks, missing serials and changed identities", () => {
  const disk = (name: string, size: number, children: any[] = []) => ({
    type: "disk",
    path: "/dev/" + name,
    serial: name,
    model: "Fixture",
    "maj:min": "8:" + size,
    size,
    children,
  });
  const live = disk("live", 10, [{ "maj:min": "8:1", mountpoints: ["/"] }]);
  const mounted = disk("mounted", 20, [{ mountpoints: ["/media/data"] }]);
  const target = disk("target", 30);
  const report = {
    blockdevices: [
      live,
      mounted,
      target,
      { ...disk("unknown", 40), serial: null },
    ],
  };
  const aliases = Object.fromEntries(
    report.blockdevices.map((d) => [
      "/dev/disk/by-id/" + d.path.slice(5),
      d.path,
    ]),
  );
  const selected = selectDisks(report, "8:1", aliases);
  assert.equal(selected.length, 1);
  assert.equal(selected[0].kernel, "/dev/target");
  assertSameDisk(selected[0], selected);
  assert.throws(
    () => assertSameDisk({ ...selected[0], serial: "changed" }, selected),
    /identity/,
  );
});
test("system files stay in the selected checkout and source identity detects untracked changes", () => {
  const { c } = fixture(),
    before = configurationIdentity(c.configuration);
  fs.writeFileSync(path.join(c.configuration, "new.nix"), "{}");
  assert.notEqual(configurationIdentity(c.configuration), before);
  assert.throws(() => confinedSystemFile(c, "../escape"), /confined/);
  assert.throws(() => confinedSystemFile(c, "~/escape"), /home shorthand/);
  assert.throws(
    () => confinedSystemFile(c, path.join(c.state, "private")),
    /outside/,
  );
  fs.symlinkSync(c.state, path.join(c.configuration, "redirect"));
  assert.throws(() => confinedSystemFile(c, "redirect/secret"), /links/);
  assert.throws(() => configurationIdentity(c.configuration), /links/);
});
test("ledger uses observed receipt events, preserves edits, deduplicates restart and binds one vault", async () => {
  const { c } = fixture(),
    v = vault(),
    other = vault();
  const op = approveSystem(c, "Install <script> and [[untrusted]]", "backend");
  await recordSystem(c, op.id, "uncertain", {
    status: "connection-lost",
    running: null,
  });
  const first = await projectSystemLedger(c, v);
  assert.equal(first.appended, 2);
  const file = path.join(v, LEDGER_PATH),
    before = raw(file).toString();
  assert(before.includes("uncertain"));
  assert(!before.includes("<script>"));
  assert(!before.includes("[[untrusted]]"));
  assert.equal((await projectSystemLedger(c, v)).appended, 0);
  fs.appendFileSync(file, "\nOperator annotation.\n");
  await recordSystem(c, op.id, "verified", { bootVerified: true });
  assert.equal((await projectSystemLedger(c, v)).appended, 1);
  assert(raw(file).toString().includes("Operator annotation."));
  assert.equal((await projectSystemLedger(c, other)).appended, 0);
  assert(!fs.existsSync(path.join(other, LEDGER_PATH)));
  fs.writeFileSync(file, "# User-owned file\n");
  await assert.rejects(projectSystemLedger(c, v), /not machine-owned/);
});
function adapter() {
  const f = fixture(),
    prior = process.env.CHRYSALIS_SYSTEM_CONFIG,
    priorAgent = process.env.PI_CODING_AGENT_DIR;
  process.env.CHRYSALIS_SYSTEM_CONFIG = f.file;
  process.env.PI_CODING_AGENT_DIR = path.join(f.dir, "agent");
  fs.mkdirSync(process.env.PI_CODING_AGENT_DIR);
  const definitions: any[] = [],
    events: Record<string, Function[]> = {};
  let server: any;
  const pi: any = {
    registerMcpServer: (name: string, config: any) => {
      server = {
        name,
        config,
        extensionPath: path.join(PACKAGE_ROOT, "extensions/chrysalis.ts"),
      };
    },
    unregisterMcpServer() {},
    getMcpServers: () => [server],
    registerTool: (t: any) =>
      definitions.push({
        ...t,
        sourceInfo: {
          path: path.join(PACKAGE_ROOT, "extensions/chrysalis.ts"),
          source: "package",
        },
      }),
    getAllTools: () => definitions,
    getActiveTools: () => [],
    setActiveTools() {},
    sendUserMessage() {},
    on: (name: string, f: Function) => (events[name] ??= []).push(f),
  };
  const system = installSystem(pi);
  for (const name of [
    "build",
    "diff",
    "switch",
    "generations",
    "eval_config",
    "locate_option",
    "check",
  ])
    definitions.push({
      name: "mcp__chrysalis_system__" + name,
      description: "Fixture " + name,
      parameters: { type: "object", properties: {} },
      sourceInfo: { path: "builtin:mcp", source: "builtin" },
      namespace: { name: "mcp__chrysalis_system" },
      exposure: "codemode",
    });
  const ctx: any = {
    cwd: f.c.configuration,
    hasUI: true,
    ui: {
      input: async () => "Install a package",
      editor: async (_: any, v: string) => v,
      confirm: async () => true,
      notify() {},
    },
  };
  const restore = () => {
    if (prior === undefined) delete process.env.CHRYSALIS_SYSTEM_CONFIG;
    else process.env.CHRYSALIS_SYSTEM_CONFIG = prior;
    if (priorAgent === undefined) delete process.env.PI_CODING_AGENT_DIR;
    else process.env.PI_CODING_AGENT_DIR = priorAgent;
  };
  return {
    ...f,
    system,
    definitions,
    events,
    ctx,
    restore,
    server: () => server,
  };
}
test("system adapter refuses headless self-approval and gates direct/nested backend calls on actual build evidence", async () => {
  const a = adapter();
  try {
    const request = a.definitions.find((d) => d.name === "chrysalis_system");
    await assert.rejects(
      request.execute(
        "request",
        { action: "request", goal: "Change system" },
        undefined,
        undefined,
        { ...a.ctx, hasUI: false },
      ),
      /native interactive/,
    );
    assert.equal(currentOperation(a.c), undefined);
    await a.system.command([], a.ctx);
    const event = (name: string, input: any = {}, id = name) => ({
      toolName: "mcp__chrysalis_system__" + name,
      input,
      toolCallId: id,
    });
    assert.equal(
      (await a.system.authorize(event("switch"), a.ctx))?.block,
      true,
    );
    const build = event("build");
    assert.equal(await a.system.authorize(build, a.ctx), undefined);
    await a.events.tool_result[0]({
      ...build,
      content: [
        {
          type: "text",
          text: JSON.stringify({ status: "running", job_id: "fixture-job" }),
        },
      ],
    });
    assert.equal(currentOperation(a.c)?.phase, "building");
    assert.equal(
      (await a.system.authorize(event("switch"), a.ctx))?.block,
      true,
    );
    assert.equal(
      (await a.system.authorize(event("build", { job_id: "other-job" }), a.ctx))
        ?.block,
      true,
    );
    assert.equal(
      (await a.system.authorize(event("diff", {}, "too-soon"), a.ctx))?.block,
      true,
    );
    const poll = event("build", { job_id: "fixture-job" }, "completed-poll");
    assert.equal(await a.system.authorize(poll, a.ctx), undefined);
    await a.events.tool_result[0]({
      ...poll,
      content: [
        {
          type: "text",
          text: JSON.stringify({ status: "ok", job_id: "fixture-job" }),
        },
      ],
    });
    const diff = event("diff");
    assert.equal(await a.system.authorize(diff, a.ctx), undefined);
    const store = "/nix/store/" + "0".repeat(32) + "-fixture-system";
    await a.events.tool_result[0]({
      ...diff,
      content: [
        {
          type: "text",
          text: JSON.stringify({ status: "ok", store_path: store }),
        },
      ],
    });
    assert.equal(currentOperation(a.c)?.phase, "built");
    fs.appendFileSync(
      path.join(a.c.configuration, "flake.nix"),
      "\n# Changed after build\n",
    );
    assert.equal(
      (await a.system.authorize(event("switch"), a.ctx))?.block,
      true,
    );
    const next = event("diff", {}, "next");
    await a.system.authorize(next, a.ctx);
    await a.events.tool_result[0]({
      ...next,
      content: [
        {
          type: "text",
          text: JSON.stringify({ status: "ok", store_path: store }),
        },
      ],
    });
    const activation = event("switch");
    assert.equal(await a.system.authorize(activation, a.ctx), undefined);
    await a.events.tool_result[0]({
      ...activation,
      content: [{ type: "text", text: JSON.stringify({ status: "ok" }) }],
    });
    assert.equal(
      currentOperation(a.c)?.phase,
      "uncertain",
      "A transport success cannot fake the running closure",
    );
  } finally {
    a.restore();
  }
});
test("system backend registration, host and tool-definition drift revoke the native scope", async () => {
  const a = adapter();
  try {
    await a.system.command([], a.ctx);
    const event = {
      toolName: "mcp__chrysalis_system__eval_config",
      input: { flake_uri: a.c.configuration + "#other" },
      toolCallId: "drift",
    };
    assert.equal((await a.system.authorize(event, a.ctx))?.block, true);
    event.input.flake_uri = a.c.configuration + "#fixture";
    a.definitions.find((d) => d.name.endsWith("__eval_config")).description =
      "Changed";
    assert.equal((await a.system.authorize(event, a.ctx))?.block, true);
    a.server().config = { ...a.server().config, command: "substituted" };
    assert.equal((await a.system.authorize(event, a.ctx))?.block, true);
  } finally {
    a.restore();
  }
});
test("system process completion preserves nonzero exit and timeout uncertainty", async () => {
  const result = await command(process.execPath, [
    "-e",
    "process.stdout.write('fixture');process.exit(7)",
  ]);
  assert.equal(result.code, 7);
  assert.equal(result.output, "fixture");
  await assert.rejects(
    command(process.execPath, ["-e", "setInterval(()=>{},1000)"], {
      timeout: 20,
    }),
    /interrupted/,
  );
});

test("a persisted installation interruption never becomes an automatic formatting retry", async () => {
  const { c } = fixture("installer");
  const disk = {
    path: "/dev/disk/by-id/fixture",
    kernel: "/dev/fixture",
    majorMinor: "8:99",
    size: 123,
    serial: "fixture",
    model: "fixture",
  };
  const op = approveSystem(
    c,
    "Disposable interrupted installation",
    "fixture",
    disk,
  );
  await recordSystem(c, op.id, "installing", {
    source: configurationIdentity(c.configuration),
  });
  assert.equal((await reconcileInstalled(c)).status, "uncertain");
  await assert.rejects(installTarget(c), /interrupted/);
  assert.equal(currentOperation(c)?.phase, "uncertain");
  const v = vault();
  await assert.rejects(projectSystemLedger(c, v), /installed boot/);
  assert(!fs.existsSync(path.join(v, LEDGER_PATH)));
  assert(currentOperation(c)?.events.some((e) => e.phase === "installing"));
  assert(currentOperation(c)?.events.some((e) => e.phase === "uncertain"));
});
test("selecting a vault without an approved OS outcome creates no system ledger", async () => {
  const { c } = fixture(),
    v = vault();
  await assert.rejects(projectSystemLedger(c, v), /native/);
  assert(!fs.existsSync(path.join(v, LEDGER_PATH)));
});
test(
  "actual Pi native MCP/codemode preserves NixOS scope and observes a simulated activation mismatch",
  { timeout: 60000 },
  async () => {
    const { createRequire } = await import("node:module");
    const { pathToFileURL } = await import("node:url");
    const {
      DefaultResourceLoader,
      SettingsManager,
      SessionManager,
      createAgentSession,
      createCodemodeExtension,
      createMcpExtension,
    } = await import("@earendil-works/pi-coding-agent");
    const { runToolCall } = await import("@earendil-works/pi-agent-core");
    const f = fixture(),
      require = createRequire(import.meta.url);
    const fake = path.join(f.dir, "backend.mjs");
    const calls = path.join(f.dir, "backend-calls");
    const serverIndex = pathToFileURL(
      require.resolve("@modelcontextprotocol/sdk/server/index.js"),
    ).href;
    const serverStdio = pathToFileURL(
      require.resolve("@modelcontextprotocol/sdk/server/stdio.js"),
    ).href;
    const types = pathToFileURL(
      require.resolve("@modelcontextprotocol/sdk/types.js"),
    ).href;
    fs.writeFileSync(
      fake,
      "#!" +
        process.execPath +
        "\n" +
        'import fs from "node:fs";\n' +
        "import { Server } from " +
        JSON.stringify(serverIndex) +
        ";\n" +
        "import { StdioServerTransport } from " +
        JSON.stringify(serverStdio) +
        ";\n" +
        "import { ListToolsRequestSchema, CallToolRequestSchema } from " +
        JSON.stringify(types) +
        ";\n" +
        'const names=["build","diff","switch","generations","eval_config","locate_option","check"];\n' +
        'const s=new Server({name:"fixture-nix-agent",version:"1"},{capabilities:{tools:{}}});\n' +
        's.setRequestHandler(ListToolsRequestSchema,async()=>({tools:names.map(name=>({name,description:"Synthetic "+name,inputSchema:{type:"object",properties:{flake_uri:{type:"string"}},additionalProperties:true}}))}));\n' +
        "s.setRequestHandler(CallToolRequestSchema,async({params})=>{fs.appendFileSync(" +
        JSON.stringify(calls) +
        ',params.name+"\\n");const r=params.name==="diff"?{status:"ok",store_path:"/nix/store/' +
        "0".repeat(32) +
        '-fixture-system"}:{status:"ok"};return {content:[{type:"text",text:JSON.stringify(r)}],structuredContent:r};});\n' +
        "await s.connect(new StdioServerTransport());\n",
    );
    fs.chmodSync(fake, 0o700);
    f.c.commands.nixAgent = fake;
    atomicJSON(f.file, f.c);
    const agentDir = path.join(f.dir, "pi");
    fs.mkdirSync(agentDir);
    const before = Object.fromEntries(
      [
        "CHRYSALIS_SYSTEM_CONFIG",
        "CHRYSALIS_STATE_ROOT",
        "PI_CODING_AGENT_DIR",
      ].map((k) => [k, process.env[k]]),
    );
    process.env.CHRYSALIS_SYSTEM_CONFIG = f.file;
    process.env.CHRYSALIS_STATE_ROOT = f.c.state;
    process.env.PI_CODING_AGENT_DIR = agentDir;
    let api: any, session: any;
    try {
      const settings = SettingsManager.inMemory({ packages: [] });
      const loader = new DefaultResourceLoader({
        cwd: f.c.configuration,
        agentDir,
        settingsManager: settings,
        noContextFiles: true,
        additionalExtensionPaths: [PACKAGE_ROOT],
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
          (pi: any) => {
            api = pi;
          },
        ],
      });
      await loader.reload();
      assert.deepEqual(loader.getExtensions().errors, []);
      ({ session } = await createAgentSession({
        cwd: f.c.configuration,
        agentDir,
        resourceLoader: loader,
        settingsManager: settings,
        sessionManager: SessionManager.inMemory(f.c.configuration),
      }));
      session.agent.streamFunction = () => {
        throw Error("This fixture forbids model requests");
      };
      const errors: any[] = [];
      await session.bindExtensions({ onError: (e: any) => errors.push(e) });
      for (
        let n = 0;
        n < 100 &&
        api
          .getAllTools()
          .filter((t: any) => t.name.startsWith("mcp__chrysalis_system__"))
          .length !== 7;
        n++
      )
        await new Promise((r) => setTimeout(r, 50));
      assert.equal(
        api
          .getAllTools()
          .filter((t: any) => t.name.startsWith("mcp__chrysalis_system__"))
          .length,
        7,
        JSON.stringify(errors),
      );
      const command = loader
        .getExtensions()
        .extensions.flatMap((e: any) => [...e.commands.values()])
        .find((c: any) => c.name === "chrysalis");
      assert(command);
      const ctx: any = {
        ...(session as any)._extensionRunner.createContext(),
        cwd: f.c.configuration,
        hasUI: true,
        ui: {
          editor: async (_: any, v: string) => v,
          confirm: async () => true,
          notify(message: string) {
            console.error("Native fixture notice: " + message);
          },
        },
      };
      await command.handler("system Change the synthetic OS", ctx);
      assert.equal(currentOperation(f.c)?.phase, "approved");
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
      const invoke = (code: string) =>
        runToolCall(
          {
            type: "toolCall",
            id: randomUUID(),
            name: "codemode",
            arguments: { code },
          },
          {
            tools: session.agent.state.tools,
            assistantMessage: message,
            context: session.agent.state,
            beforeToolCall: session.agent.beforeToolCall,
            afterToolCall: session.agent.afterToolCall,
          },
        );
      const denied = await invoke(
        'await tools.mcp__chrysalis_system__eval_config({flake_uri:"elsewhere#other"});',
      );
      assert.match(JSON.stringify(denied), /exact approved/);
      const diff = await invoke(
        "text(await tools.mcp__chrysalis_system__diff({}));",
      );
      assert.equal(currentOperation(f.c)?.phase, "built", JSON.stringify(diff));
      const activation = await invoke(
        "text(await tools.mcp__chrysalis_system__switch({}));",
      );
      assert.equal(
        currentOperation(f.c)?.phase,
        "uncertain",
        JSON.stringify(activation),
      );
      const rollback = await invoke(
        'await tools.mcp__chrysalis_system__generations({action:"rollback",generation:999});',
      );
      assert.match(
        JSON.stringify(rollback),
        /exact native-approved generation/,
      );
      await (session as any)._extensionRunner.emit({
        type: "session_shutdown",
      });
      session.dispose();
      session = undefined;
      delete process.env.CHRYSALIS_SYSTEM_CONFIG;
      const disabledSettings = SettingsManager.inMemory({ packages: [] });
      const disabledLoader = new DefaultResourceLoader({
        cwd: f.c.configuration,
        agentDir,
        settingsManager: disabledSettings,
        noContextFiles: true,
        additionalExtensionPaths: [PACKAGE_ROOT],
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
          (pi: any) => {
            api = pi;
            pi.registerMcpServer("chrysalis_system", {
              type: "stdio",
              command: fake,
              cwd: f.c.configuration,
              exposure: "codemode",
            });
          },
        ],
      });
      await disabledLoader.reload();
      assert.deepEqual(disabledLoader.getExtensions().errors, []);
      ({ session } = await createAgentSession({
        cwd: f.c.configuration,
        agentDir,
        resourceLoader: disabledLoader,
        settingsManager: disabledSettings,
        sessionManager: SessionManager.inMemory(f.c.configuration),
      }));
      session.agent.streamFunction = () => {
        throw Error("This fixture forbids model requests");
      };
      await session.bindExtensions({ onError: (e: any) => errors.push(e) });
      for (
        let n = 0;
        n < 100 &&
        !api
          .getAllTools()
          .some((t: any) => t.name === "mcp__chrysalis_system__eval_config");
        n++
      )
        await new Promise((r) => setTimeout(r, 50));
      assert(
        api
          .getAllTools()
          .some((t: any) => t.name === "mcp__chrysalis_system__eval_config"),
      );
      const beforeDisabled = fs.readFileSync(calls, "utf8");
      const direct = await (session as any)._extensionRunner.emitToolCall({
        type: "tool_call",
        toolName: "mcp__chrysalis_system__eval_config",
        toolCallId: randomUUID(),
        input: {},
      });
      assert.equal(direct.block, true);
      assert.match(direct.reason, /not configured/);
      session.agent.state.messages.push(message);
      const nested = await invoke(
        "text(await tools.mcp__chrysalis_system__eval_config({}));",
      );
      assert.match(JSON.stringify(nested), /not configured/);
      assert.equal(
        fs.readFileSync(calls, "utf8"),
        beforeDisabled,
        "Inactive same-name backend was never invoked",
      );
    } finally {
      if (session) {
        await (session as any)._extensionRunner.emit({
          type: "session_shutdown",
        });
        session.dispose();
      }
      for (const [k, v] of Object.entries(before))
        if (v === undefined) delete process.env[k];
        else process.env[k] = v;
    }
  },
);

test("stable disk identity survives kernel renumbering and recovery touches only its mount subtree", async () => {
  const { c, dir } = fixture("installer");
  const metadata = path.join(dir, "devices.json"),
    journal = path.join(dir, "unmounts.json");
  const expected = {
    path: "/dev/disk/by-id/fixture",
    kernel: "/dev/old",
    majorMinor: "8:16",
    size: 12345,
    serial: "fixture-serial",
    model: "Fixture",
  };
  const current = { ...expected, kernel: "/dev/new", majorMinor: "8:32" };
  assert.equal(assertSameDisk(expected, [current]).kernel, "/dev/new");
  const data: any = {
    disk: {
      type: "disk",
      path: current.kernel,
      "maj:min": current.majorMinor,
      size: current.size,
      serial: current.serial,
      model: current.model,
      children: [
        { type: "part", path: "/dev/new1", "maj:min": "8:33" },
        {
          type: "part",
          path: "/dev/new2",
          "maj:min": "8:34",
          children: [
            { type: "crypt", path: "/dev/mapper/fixture", "maj:min": "253:0" },
          ],
        },
      ],
    },
    root: "8:1",
    mounts: [
      { target: "/", "maj:min": "8:1" },
      { target: "/mnt", "maj:min": "253:0" },
      { target: "/mnt/boot", "maj:min": "8:33" },
    ],
  };
  const write = () => fs.writeFileSync(metadata, JSON.stringify(data));
  const script = (name: string, body: string) => {
    const p = path.join(dir, name + ".mjs");
    fs.writeFileSync(
      p,
      "#!" +
        process.execPath +
        "\nimport fs from 'node:fs';\nconst file=" +
        JSON.stringify(metadata) +
        ";const data=JSON.parse(fs.readFileSync(file,'utf8'));\n" +
        body,
    );
    fs.chmodSync(p, 0o700);
    return p;
  };
  c.commands.lsblk = script(
    "lsblk",
    "console.log(JSON.stringify({blockdevices:[data.disk]}));",
  );
  c.commands.findmnt = script(
    "findmnt",
    "console.log(process.argv.includes('--json')?JSON.stringify({filesystems:data.mounts}):data.root);",
  );
  c.commands.sudo = script(
    "sudo",
    "const mount=process.argv.at(-1);const log=" +
      JSON.stringify(journal) +
      ";const seen=fs.existsSync(log)?JSON.parse(fs.readFileSync(log,'utf8')):[];seen.push(mount);fs.writeFileSync(log,JSON.stringify(seen));data.mounts=data.mounts.filter(m=>m.target!==mount);fs.writeFileSync(file,JSON.stringify(data));",
  );
  data.mounts.push({ target: "/mnt/sentinel", "maj:min": "8:99" });
  write();
  await assert.rejects(
    unmountRecoveryTarget(c, expected),
    /outside the approved/,
  );
  assert(!fs.existsSync(journal));
  data.mounts.pop();
  data.mounts.push({ target: "/media/data", "maj:min": "253:0" });
  write();
  await assert.rejects(
    unmountRecoveryTarget(c, expected),
    /outside the approved/,
  );
  assert(!fs.existsSync(journal));
  data.mounts.pop();
  data.root = "253:0";
  write();
  await assert.rejects(
    inspectTarget(c, expected),
    /running installation medium/,
  );
  data.root = "8:1";
  write();
  const final = await unmountRecoveryTarget(c, expected);
  assert.equal(final.mounts.length, 0);
  assert.deepEqual(JSON.parse(fs.readFileSync(journal, "utf8")), [
    "/mnt/boot",
    "/mnt",
  ]);
});
test("concurrent and late backend results cannot replace an activation receipt", async () => {
  const a = adapter();
  try {
    await a.system.command(["Change synthetic system"], a.ctx);
    const event = (tool: string, id: string, input: any = {}) => ({
      toolName: "mcp__chrysalis_system__" + tool,
      toolCallId: id,
      input,
    });
    const build = event("build", "build-first"),
      concurrent = event("diff", "diff-concurrent");
    const [started, denied] = await Promise.all([
      a.system.authorize(build, a.ctx),
      a.system.authorize(concurrent, a.ctx),
    ]);
    assert.equal(started, undefined);
    assert.equal(denied?.block, true);
    assert.equal(currentOperation(a.c)?.pending?.id, "build-first");
    assert.equal((await reconcileInstalled(a.c)).inflight, true);
    assert.equal(currentOperation(a.c)?.pending?.id, "build-first");
    const respond = (e: any, result: any) =>
      a.events.tool_result[0]({
        ...e,
        content: [{ type: "text", text: JSON.stringify(result) }],
      });
    await respond(build, { status: "running", job_id: "job-first" });
    assert.equal(
      (await a.system.authorize(event("diff", "premature"), a.ctx))?.block,
      true,
    );
    const poll = event("build", "poll-first", { job_id: "job-first" });
    await a.system.authorize(poll, a.ctx);
    await respond(poll, { status: "ok", job_id: "job-first" });
    const diff = event("diff", "fresh-diff");
    await a.system.authorize(diff, a.ctx);
    await respond(diff, {
      status: "ok",
      store_path: "/nix/store/" + "0".repeat(32) + "-fixture-system",
    });
    const activation = event("switch", "activation");
    await a.system.authorize(activation, a.ctx);
    assert.equal(currentOperation(a.c)?.phase, "activating");
    await respond(build, { status: "running", job_id: "job-first" });
    assert.equal(currentOperation(a.c)?.phase, "activating");
    assert.equal(currentOperation(a.c)?.pending?.id, "activation");
    const write = a.definitions.find(
      (d) => d.name === "chrysalis_system_write",
    );
    await assert.rejects(
      write.execute("blocked-write", { path: "new.nix", content: "{}" }),
      /in-flight/,
    );
    await a.events.tool_result[0]({
      ...activation,
      isError: true,
      content: [{ type: "text", text: "connection lost" }],
    });
    assert.equal(currentOperation(a.c)?.phase, "uncertain");
    assert.equal(currentOperation(a.c)?.pending, undefined);
    assert.throws(() => assertSystemIdle(a.c), /may still be running/);
    await a.system.command(["close"], a.ctx);
    await assert.rejects(
      a.system.command(["Recover without overlapping"], a.ctx),
      /restart/,
    );
    assert.equal(
      (await a.system.authorize(event("diff", "after-loss"), a.ctx))?.block,
      true,
    );
  } finally {
    a.restore();
  }
});
test("receipt directory durability failure blocks the upstream operation", async () => {
  const a = adapter(),
    original = fs.fsyncSync;
  try {
    await a.system.command(["Change synthetic system"], a.ctx);
    fs.fsyncSync = (fd: number) => {
      if (fs.fstatSync(fd).isDirectory())
        throw Error("Synthetic directory sync failure");
      return original(fd);
    };
    const result = await a.system.authorize(
      {
        toolName: "mcp__chrysalis_system__diff",
        toolCallId: "durability",
        input: {},
      },
      a.ctx,
    );
    assert.equal(result?.block, true);
    assert.match(result?.reason ?? "", /sync failure/);
  } finally {
    fs.fsyncSync = original;
    a.restore();
  }
});

test("the approved outcome permits post-activation verification and edits invalidate its earlier build proof", async () => {
  const a = adapter();
  try {
    await a.system.command(["Finish synthetic OS outcome"], a.ctx);
    const op = currentOperation(a.c)!;
    await recordSystem(a.c, op.id, "verified", {
      verification: ["synthetic observed closure"],
    });
    assert.equal(requireSystemScope(a.c).id, op.id);
    const write = a.definitions.find(
      (d) => d.name === "chrysalis_system_write",
    );
    await write.execute("post-activation-correction", {
      path: "feature.nix",
      content: "{}\n",
    });
    assert.equal(currentOperation(a.c)?.phase, "approved");
    assert.equal(
      fs.readFileSync(path.join(a.c.configuration, "feature.nix"), "utf8"),
      "{}\n",
    );
    assert.equal(
      (
        await a.system.authorize(
          {
            toolName: "mcp__chrysalis_system__switch",
            toolCallId: "stale-proof",
            input: {},
          },
          a.ctx,
        )
      )?.block,
      true,
    );
    await recordSystem(a.c, op.id, "closed");
    assert.throws(() => requireSystemScope(a.c), /native/);
  } finally {
    a.restore();
  }
});

test("handoff resolves the installed profile inside the target even without the live closure", () => {
  const { dir } = fixture(),
    target = path.join(dir, "target"),
    profiles = path.join(target, "nix/var/nix/profiles");
  const store = "/nix/store/" + "0".repeat(32) + "-synthetic-target";
  fs.mkdirSync(profiles, { recursive: true });
  fs.mkdirSync(target + store, { recursive: true });
  fs.symlinkSync("system-1-link", path.join(profiles, "system"));
  fs.symlinkSync(store, path.join(profiles, "system-1-link"));
  assert.equal(installedSystemProfile(target), store);
  fs.unlinkSync(path.join(profiles, "system-1-link"));
  fs.symlinkSync("/unapproved/path", path.join(profiles, "system-1-link"));
  assert.throws(() => installedSystemProfile(target), /closure is unavailable/);
});

test("interrupted handoff retries only its own durable copy intent and preserves target edits", async () => {
  const { c, dir } = fixture("installer");
  const disk = {
    path: "/dev/disk/by-id/fixture",
    kernel: "/dev/vda",
    majorMinor: "1:1",
    size: 100,
    serial: "fixture",
    model: "fixture",
  };
  const op = approveSystem(
    c,
    "Synthetic handoff recovery",
    "native-fixture",
    disk,
  );
  await recordSystem(c, op.id, "installed");
  const target = path.join(dir, "target"),
    file = path.join(target, "state/session.jsonl");
  fs.mkdirSync(target);
  copyHandoffFile(c, op.id, Buffer.from("before restart"), file, target);
  copyHandoffFile(
    c,
    op.id,
    Buffer.from("continued after restart"),
    file,
    target,
  );
  assert.equal(fs.readFileSync(file, "utf8"), "continued after restart");
  // A crash after durable intent but before the target write is equally recoverable.
  const journalFile = path.join(c.state, "system/handoff-" + op.id + ".json");
  const journal = JSON.parse(fs.readFileSync(journalFile, "utf8"));
  journal.files["state/not-yet-copied"] = {
    before: null,
    after: digest("old intent"),
  };
  atomicJSON(journalFile, journal);
  copyHandoffFile(
    c,
    op.id,
    Buffer.from("current checkpoint"),
    path.join(target, "state/not-yet-copied"),
    target,
  );
  fs.writeFileSync(file, "independent target edit");
  assert.throws(
    () => copyHandoffFile(c, op.id, Buffer.from("new USB state"), file, target),
    /target changed/,
  );
  assert.equal(fs.readFileSync(file, "utf8"), "independent target edit");
  assert.throws(
    () =>
      copyHandoffFile(
        c,
        op.id,
        Buffer.from("outside"),
        path.join(dir, "outside"),
        target,
      ),
    /confined/,
  );
});

test("ambiguous privileged activity survives outcome closure and requires completion or a new boot", async () => {
  const { c } = fixture();
  const op = approveSystem(c, "Synthetic privileged recovery", "native");
  const token = beginPrivileged(c, op.id, "switch");
  await recordSystem(c, op.id, "uncertain", {
    stage: "switch",
    status: "transport-error",
  });
  await recordSystem(c, op.id, "closed");
  assert.throws(() => assertSystemIdle(c), /may still be running/);
  assert.throws(
    () => approveSystem(c, "Do not overlap rollback", "native"),
    /restart/,
  );
  completePrivileged(c, token);
  const next = approveSystem(
    c,
    "Verified completion allows a new outcome",
    "native",
  );
  beginPrivileged(c, next.id, "switch");
  const file = path.join(c.state, "system/privileged.json");
  const activity = JSON.parse(fs.readFileSync(file, "utf8"));
  atomicJSON(file, { ...activity, boot: randomUUID() });
  assert.doesNotThrow(() => assertSystemIdle(c));
});

test("verbose installer output retains a bounded tail without terminating the process", async () => {
  const result = await command(
    process.execPath,
    [
      "-e",
      "process.stdout.write('x'.repeat(5*1024*1024), () => process.stdout.write('INSTALLER-COMPLETED'))",
    ],
    { tail: true },
  );
  assert.equal(result.code, 0);
  assert(result.output.length <= 4 * 1024 * 1024);
  assert(result.output.endsWith("INSTALLER-COMPLETED"));
});

test("a structured failed activation retains the privileged marker because timeout may leave a child", async () => {
  const a = adapter();
  try {
    await a.system.command(["Synthetic failed activation"], a.ctx);
    const event = (tool: string, id: string) => ({
      toolName: "mcp__chrysalis_system__" + tool,
      toolCallId: id,
      input: {},
    });
    const diff = event("diff", "prepare-failed-activation");
    assert.equal(await a.system.authorize(diff, a.ctx), undefined);
    await a.events.tool_result[0]({
      ...diff,
      content: [
        {
          type: "text",
          text: JSON.stringify({
            status: "ok",
            store_path: "/nix/store/" + "0".repeat(32) + "-fixture-system",
          }),
        },
      ],
    });
    const activation = event("switch", "failed-activation");
    assert.equal(await a.system.authorize(activation, a.ctx), undefined);
    await a.events.tool_result[0]({
      ...activation,
      content: [
        {
          type: "text",
          text: JSON.stringify({
            status: "failed",
            message: "timeout without exit proof",
          }),
        },
      ],
    });
    assert.equal(currentOperation(a.c)?.phase, "uncertain");
    assert.throws(() => assertSystemIdle(a.c), /may still be running/);
    await a.system.command(["close"], a.ctx);
    await assert.rejects(a.system.command(["Recover"], a.ctx), /restart/);
  } finally {
    a.restore();
  }
});

test("ledger binding uses the operation writer lock and preserves an in-flight receipt", async () => {
  const { c } = fixture(),
    selected = vault();
  const op = approveSystem(c, "Synthetic ledger concurrency", "native");
  let release!: () => void;
  const held = withLock(
    path.join(c.state, "system/locks"),
    op.id,
    () =>
      new Promise<void>((resolve) => {
        release = resolve;
      }),
  );
  try {
    await assert.rejects(projectSystemLedger(c, selected), /writer_busy/);
    assert.equal(currentOperation(c)?.vault, undefined);
  } finally {
    release();
    await held;
  }
  await recordSystem(c, op.id, "verified", { retained: "Latest completion" });
  await projectSystemLedger(c, selected);
  assert.equal(currentOperation(c)?.phase, "verified");
  assert(
    fs
      .readFileSync(path.join(selected, LEDGER_PATH), "utf8")
      .includes("Latest completion"),
  );
});

test("native close cannot revoke an in-flight context and its completion cannot reopen a closed outcome", async () => {
  const a = adapter(),
    ready = path.join(a.dir, "context-ready"),
    release = path.join(a.dir, "context-release");
  const quote = (value: string) => "'" + value.replaceAll("'", "'\\''") + "'";
  let execution: Promise<any> | undefined;
  try {
    await a.system.command(["Synthetic held system context"], a.ctx);
    const bash = a.definitions.find((d) => d.name === "chrysalis_system_bash");
    execution = bash.execute("held-context", {
      command:
        "touch " +
        quote(ready) +
        "; while [ ! -f " +
        quote(release) +
        " ]; do sleep 0.01; done",
      timeout: 10,
    });
    for (let n = 0; n < 200 && !fs.existsSync(ready); n++)
      await new Promise((r) => setTimeout(r, 10));
    assert(fs.existsSync(ready));
    assert.equal(currentOperation(a.c)?.pending?.id, "held-context");
    await assert.rejects(a.system.command(["close"], a.ctx), /in-flight/);
    assert.notEqual(currentOperation(a.c)?.phase, "closed");
    fs.writeFileSync(release, "release");
    await execution;
    execution = undefined;
    assert.equal(currentOperation(a.c)?.phase, "approved");
    await a.system.command(["close"], a.ctx);
    assert.equal(currentOperation(a.c)?.phase, "closed");
    assert.throws(() => requireSystemScope(a.c), /native/);
  } finally {
    fs.writeFileSync(release, "release");
    if (execution) await execution;
    a.restore();
  }
});

test("configuration/vault overlap is refused before approval, later use and native onboarding", async () => {
  const a = adapter();
  try {
    const selected = path.join(a.c.configuration, "Nested Vault"),
      id = randomUUID();
    fs.mkdirSync(selected);
    atomicJSON(path.join(selected, ".chrysalis-vault.json"), {
      schema_version: "1",
      vault_id: id,
    });
    assert.throws(
      () =>
        approveSystem(
          a.c,
          "Do not snapshot personal data",
          "native",
          undefined,
          selected,
        ),
      /configuration must be disjoint/,
    );
    assert.equal(currentOperation(a.c), undefined);
    assert.throws(
      () => a.system.validateVault(path.join(a.c.configuration, "New Vault")),
      /configuration must be disjoint/,
    );
    assert(!fs.existsSync(path.join(a.c.configuration, "New Vault")));
    approveSystem(a.c, "Previously approved without a vault", "native");
    atomicJSON(path.join(a.c.state, "profile.json"), {
      vault_root: selected,
      vault_id: id,
    });
    assert.throws(
      () => requireSystemScope(a.c),
      /configuration must be disjoint/,
    );
    assert.throws(
      () => assertSystemVault(a.c, path.dirname(a.c.configuration)),
      /disjoint/,
    );
  } finally {
    a.restore();
  }
});

test("ledger projection refuses closed, superseded and backend-drift outcomes", async () => {
  const { c } = fixture(),
    selected = vault();
  const op = approveSystem(c, "Ledger authority", "backend-A");
  await assert.rejects(
    systemLedgerAuthorization(c, "backend-B"),
    /authorization/,
  );
  assert.equal(currentOperation(c)?.vault, undefined);
  const guard = await systemLedgerAuthorization(c, "backend-A");
  await recordSystem(c, op.id, "closed");
  await assert.rejects(projectSystemLedger(c, selected, guard), /native/);
  assert(!fs.existsSync(path.join(selected, LEDGER_PATH)));
  approveSystem(c, "New outcome", "backend-A");
  await assert.rejects(projectSystemLedger(c, selected, guard), /changed/);
  let backend = "backend-A";
  const freshGuard = await systemLedgerAuthorization(c, () => backend);
  backend = "backend-B";
  await assert.rejects(projectSystemLedger(c, selected, freshGuard), /backend/);
  assert(!fs.existsSync(path.join(selected, LEDGER_PATH)));
});
test("first installed-boot ledger evidence is exact and grants no administrative scope", async () => {
  const { c } = fixture("installer"),
    disk = {
      path: "/dev/disk/by-id/synthetic",
      kernel: "/dev/sdz",
      majorMinor: "8:240",
      size: 1024,
      serial: "fixture",
      model: "fixture",
    };
  const liveVault = vault();
  const op = approveSystem(
    c,
    "Synthetic install",
    "installer-backend",
    disk,
    liveVault,
  );
  assert.equal(currentOperation(c)?.vault, undefined);
  const running = "/nix/store/" + "a".repeat(32) + "-system";
  const verified = await recordSystem(
    c,
    op.id,
    "verified",
    { bootVerified: true, running },
    (o) => {
      o.installationId = op.id;
    },
  );
  const installed = { ...c, mode: "installed" as const },
    proof = {
      handoffComplete: true,
      operation: op.id,
      host: c.host,
      running,
      rootUuid: "root-uuid",
    },
    observation: any = { running, profile: running };
  assertInstalledLedgerProof(
    installed,
    verified,
    proof,
    observation,
    "root-uuid",
  );
  assert.throws(() => requireSystemScope(installed), /scope/);
  for (const bad of [
    { ...proof, host: "other" },
    { ...proof, operation: randomUUID() },
    { ...proof, running: "different" },
    { ...proof, handoffComplete: false },
  ])
    assert.throws(
      () =>
        assertInstalledLedgerProof(
          installed,
          verified,
          bad,
          observation,
          "root-uuid",
        ),
      /proof/,
    );
  assert.throws(
    () =>
      assertInstalledLedgerProof(
        installed,
        verified,
        proof,
        observation,
        "wrong-root",
      ),
    /proof/,
  );
  const selected = vault();
  const authorize = () => {
    const current = currentOperation(c)!;
    assertInstalledLedgerProof(
      installed,
      current,
      proof,
      observation,
      "root-uuid",
    );
    return current;
  };
  assert(
    (await projectSystemLedger(installed, selected, authorize)).appended > 0,
  );
  assert.equal(
    (await projectSystemLedger(installed, selected, authorize)).appended,
    0,
  );
  await recordSystem(c, op.id, "closed");
  await assert.rejects(
    projectSystemLedger(installed, selected, authorize),
    /proof/,
  );
});
