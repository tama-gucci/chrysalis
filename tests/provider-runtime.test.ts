import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  DefaultResourceLoader,
  SettingsManager,
  SessionManager,
  createAgentSession,
} from "@earendil-works/pi-coding-agent";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai";
import {
  openRuntimeRoute,
  selectedModel,
  registerRuntimeRoute,
  runtimeStream,
} from "../extensions/provider-runtime.ts";
import { defaults, saveProfile } from "../src/assistant/profile.ts";
import { memoryStream } from "../extensions/memory-stream.ts";
if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");

test("public Pi provider runtime serves main, memory and fixed child routes without importing provider tools or credentials", async () => {
  const base = path.join(process.env.TEST_SCRATCH!, "runtime-" + randomUUID());
  fs.mkdirSync(base, { recursive: true });
  const route = {
      provider: "synthetic-independent",
      model: "small",
      thinking: "off",
    },
    model = {
      id: "small",
      name: "Synthetic chat",
      api: "openai-completions" as const,
      reasoning: false,
      input: ["text" as const],
      contextWindow: 8192,
      maxTokens: 1024,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    };
  let calls = 0,
    parent: any,
    child: any;
  const result = (m: any) => {
    calls++;
    const out = createAssistantMessageEventStream(),
      message: any = {
        role: "assistant",
        api: m.api,
        provider: m.provider,
        model: m.id,
        content: [{ type: "text", text: "synthetic offline response" }],
        usage: {
          input: 2,
          output: 3,
          cacheRead: 0,
          cacheWrite: 0,
          totalTokens: 5,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
        },
        stopReason: "stop",
        timestamp: Date.now(),
      };
    out.push({ type: "done", reason: "stop", message });
    out.end(message);
    return out;
  };
  const sessions: any[] = [];
  async function host(factory: any, set: any) {
    const cwd = path.join(base, randomUUID());
    fs.mkdirSync(cwd);
    const settings = SettingsManager.inMemory({ packages: [] }),
      loader = new DefaultResourceLoader({
        cwd,
        agentDir: cwd,
        settingsManager: settings,
        noContextFiles: true,
        noSkills: true,
        noExtensions: true,
        extensionFactories: [
          factory,
          (pi: any) =>
            pi.on("session_start", (_e: any, ctx: any) =>
              set(ctx.modelRegistry),
            ),
        ],
      });
    await loader.reload();
    assert.deepEqual(loader.getExtensions().errors, []);
    const { session } = await createAgentSession({
      cwd,
      agentDir: cwd,
      settingsManager: settings,
      resourceLoader: loader,
      sessionManager: SessionManager.inMemory(cwd),
    });
    sessions.push(session);
    await session.bindExtensions({});
    return session;
  }
  let runtime: any;
  try {
    await host(
      (pi: any) => {
        pi.registerProvider(route.provider, {
          api: model.api,
          apiKey: "synthetic-offline",
          baseUrl: "http://invalid.local",
          models: [model],
          streamSimple: result,
        });
        pi.registerTool({
          name: "independent_ui",
          label: "UI",
          description: "Ordinary provider UI",
          parameters: { type: "object", properties: {} },
          execute: async () => ({ content: [], details: {} }),
        });
      },
      (r: any) => (parent = r),
    );
    const main = selectedModel(parent, route);
    assert.equal(
      (await parent.streamSimple(main, { messages: [] }).result()).stopReason,
      "stop",
    );
    const profile = defaults();
    profile.features.memory = profile.features.observations = true;
    profile.routes.observer = route as any;
    saveProfile(base, profile);
    assert.equal(
      (await memoryStream(base, parent, main, { messages: [] }).result())
        .stopReason,
      "stop",
    );
    assert.throws(
      () => selectedModel(parent, { ...route, model: "missing" }),
      /no fallback/,
    );
    assert.throws(() => memoryStream(base, {}, main, {}), /no fallback/);
    runtime = await openRuntimeRoute(parent, route, {
      turns: 1,
      timeoutSeconds: 15,
    });
    assert(!JSON.stringify(runtime.endpoint).includes("synthetic-offline"));
    const childSession = await host(
      (pi: any) => registerRuntimeRoute(pi, runtime.endpoint, route),
      (r: any) => (child = r),
    );
    assert(
      !childSession.getAllTools().some((t: any) => t.name === "independent_ui"),
    );
    const childModel = selectedModel(child, route);
    assert.equal(
      (await child.streamSimple(childModel, { messages: [] }).result())
        .stopReason,
      "stop",
    );
    assert.equal(calls, 3);
    assert.equal(
      (await runtimeStream(runtime.endpoint, main, { messages: [] }).result())
        .stopReason,
      "error",
    );
    assert.equal(calls, 3, "turn limit cannot invoke a different model");
    assert.throws(
      () =>
        registerRuntimeRoute(
          { registerProvider() {} },
          { ...runtime.endpoint, identity: "changed" },
          route,
        ),
      /Invalid/,
    );
    runtime.dispose();
    runtime.dispose();
    assert.equal(
      (await runtimeStream(runtime.endpoint, main, { messages: [] }).result())
        .stopReason,
      "error",
    );
  } finally {
    runtime?.dispose();
    for (const session of sessions) session.dispose();
  }
});

test("fixed runtime route rejects forged tokens, changed models and cancelled streams without fallback", async () => {
  const model: any = {
    provider: "independent",
    id: "small",
    api: "openai-completions",
    name: "Offline",
    input: ["text"],
    reasoning: false,
    contextWindow: 4096,
    maxTokens: 512,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
  };
  let calls = 0;
  const registry: any = {
    find: () => model,
    getAvailable: () => [model],
    streamSimple: () => {
      calls++;
      return createAssistantMessageEventStream();
    },
  };
  const runtime = await openRuntimeRoute(
    registry,
    { provider: model.provider, model: model.id, thinking: "off" },
    { turns: 2, timeoutSeconds: 5 },
  );
  try {
    assert.equal(
      (
        await runtimeStream({ ...runtime.endpoint, token: "wrong" }, model, {
          messages: [],
        }).result()
      ).stopReason,
      "error",
    );
    assert.equal(calls, 0);
    model.api = "other";
    assert.equal(
      (await runtimeStream(runtime.endpoint, model, { messages: [] }).result())
        .stopReason,
      "error",
    );
    assert.equal(calls, 0);
  } finally {
    runtime.dispose();
  }
});

test("runtime cancellation reaches the parent stream and cleanup prevents another request", async () => {
  const model: any = {
    provider: "independent",
    id: "small",
    api: "openai-completions",
    name: "Offline",
    input: ["text"],
    reasoning: false,
    contextWindow: 4096,
    maxTokens: 512,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
  };
  let started = false,
    aborted = false;
  const registry: any = {
    find: () => model,
    getAvailable: () => [model],
    streamSimple: (_m: any, _c: any, options: any) => {
      started = true;
      const out = createAssistantMessageEventStream();
      options.signal.addEventListener(
        "abort",
        () => {
          aborted = true;
          out.end();
        },
        { once: true },
      );
      return out;
    },
  };
  const runtime = await openRuntimeRoute(
    registry,
    { provider: model.provider, model: model.id, thinking: "off" },
    { turns: 2, timeoutSeconds: 5 },
  );
  try {
    const controller = new AbortController(),
      out = runtimeStream(
        runtime.endpoint,
        model,
        { messages: [] },
        { signal: controller.signal },
      );
    for (let i = 0; i < 100 && !started; i++)
      await new Promise((r) => setTimeout(r, 5));
    assert(started);
    controller.abort();
    assert.equal((await out.result()).stopReason, "error");
    for (let i = 0; i < 100 && !aborted; i++)
      await new Promise((r) => setTimeout(r, 5));
    assert(aborted);
    runtime.dispose();
    assert.equal(
      (await runtimeStream(runtime.endpoint, model, { messages: [] }).result())
        .stopReason,
      "error",
    );
  } finally {
    runtime.dispose();
  }
});
