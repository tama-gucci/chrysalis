import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import {
  atomicJSON,
  rejectRedirects,
  PACKAGE_ROOT,
  digest,
} from "../src/platforms/filesystem.ts";
import { assistantRoot, loadProfile } from "../src/assistant/profile.ts";
import { defaultStateRoot } from "../src/storage/context.ts";
import { memoryStream } from "./memory-stream.ts";
import { assistantUI } from "../src/assistant/ui.ts";

export function memoryConfig(state: string) {
  const p = loadProfile(state),
    result: any = {
      compaction: "auto",
      compactionEngine: "blackhole",
      memory: p.features.observations,
      model: null,
      debug: false,
      debugLog: false,
      sessionFallback: false,
      observerFallbackModels: [],
      reflectorFallbackModels: [],
      dropperFallbackModels: [],
      skipForProviders: [],
      recallResponseMaxChars: p.limits.resultChars,
      retainedToolOutputMaxTokens: 4000,
      observerChunkMaxTokens: 8000,
      reflectorInputMaxTokens: 8000,
      dropperInputMaxTokens: 8000,
      agentMaxTurns: 4,
      workerAttemptTimeoutMs: 60000,
      observeAfterTokens: p.preset === "economical" ? 24000 : 16000,
      reflectAfterTokens: 32000,
      statusBar: false,
      showWorkerNotifications: false,
    };
  for (const role of ["observer", "reflector", "dropper"] as const) {
    const r = p.routes[role];
    if (r)
      result[role + "Model"] = {
        provider: r.provider,
        id: r.model,
        thinking: r.thinking,
        cooldownHours: 1,
      };
    else if (p.features.observations)
      throw Error("Choose all memory-worker routes first");
  }
  return result;
}
export async function installMemory(pi: ExtensionAPI) {
  const state = defaultStateRoot();
  if (!loadProfile(state).features.memory)
    return { active: () => [] as string[], allowed: (_: string) => false };
  for (const key of Object.keys(process.env))
    if (/^PI_(BLACKHOLE|VCC|VCC_OM|OBSERVATIONAL_MEMORY)_/.test(key))
      delete process.env[key];
  const root = path.join(assistantRoot(state), "memory-host");
  rejectRedirects(root);
  fs.mkdirSync(path.join(root, ".pi"), { recursive: true, mode: 0o700 });
  atomicJSON(
    path.join(root, ".pi/pi-blackhole-config.json"),
    memoryConfig(state),
  );
  let definition: string | undefined;
  const withCwd = (ctx: any) =>
    new Proxy(ctx, {
      get(t, k, r) {
        if (k === "cwd") return root;
        if (k === "modelRegistry")
          return new Proxy(t.modelRegistry, {
            get(reg, key) {
              if (key === "streamSimple")
                return (model: any, context: any, options: any) =>
                  memoryStream(state, reg, model, context, options);
              if (key === "find")
                return (...args: any[]) => {
                  const model = reg.find(...args);
                  return model
                    ? {
                        ...model,
                        maxTokens: Math.min(model.maxTokens ?? 1500, 1500),
                      }
                    : undefined;
                };
              if (key === "getApiKeyAndHeaders")
                return async (model: any, ...args: any[]) => {
                  const p = loadProfile(state);
                  const chosen = ["observer", "reflector", "dropper"].some(
                    (role) => {
                      const route = p.routes[role as "observer"];
                      return (
                        !!route &&
                        route.provider === model.provider &&
                        route.model === model.id
                      );
                    },
                  );
                  if (!p.features.memory || !p.features.observations || !chosen)
                    throw Error("Memory model route is not authorized");
                  return reg.getApiKeyAndHeaders(model, ...args);
                };
              const value = Reflect.get(reg, key, reg);
              return typeof value === "function" ? value.bind(reg) : value;
            },
          });
        return Reflect.get(t, k, r);
      },
    });
  const proxy = new Proxy(pi, {
    get(target, key, receiver) {
      if (key === "on")
        return (event: any, handler: any) =>
          target.on(event, ((e: any, ctx: any) =>
            handler(e, withCwd(ctx))) as any);
      if (key === "registerTool")
        return (t: any) => {
          if (t.name !== "recall") throw Error("Unexpected memory tool");
          definition = digest({
            name: t.name,
            description: t.description,
            parameters: t.parameters,
          });
          target.registerTool({
            ...t,
            execute: (id: any, p: any, signal: any, update: any, ctx: any) =>
              t.execute(id, p, signal, update, withCwd(ctx)),
          });
        };
      if (key === "registerCommand")
        return (name: string, c: any) => {
          if (
            ![
              "blackhole-memory",
              "blackhole-recall",
              "blackhole-export",
            ].includes(name)
          )
            return;
          target.registerCommand(name, {
            ...c,
            handler: async (args: string, ctx: any) =>
              assistantUI.run(async () => {
                if (name === "blackhole-export") {
                  const exports = path.join(
                    assistantRoot(state),
                    "memory-exports",
                  );
                  rejectRedirects(exports);
                  fs.mkdirSync(exports, { recursive: true, mode: 0o700 });
                  const requested = /\bout:(\S+)/.exec(args)?.[1],
                    filename = requested ?? randomUUID() + ".md";
                  if (
                    !/^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,100}\.md$/.test(filename) ||
                    fs.existsSync(path.join(exports, filename))
                  )
                    throw Error("Choose a new export filename only");
                  return c.handler(
                    args.replace(/\bout:\S+/g, "") +
                      " out:" +
                      path.join(exports, filename),
                    withCwd(ctx),
                  );
                }
                if (
                  name === "blackhole-memory" &&
                  args &&
                  !["status", "view", "full"].includes(args.trim())
                )
                  throw Error(
                    "Memory controls use /chrysalis models and capabilities",
                  );
                return c.handler(args, withCwd(ctx));
              }),
          });
        };
      return Reflect.get(target, key, receiver);
    },
  });
  const module = await import("pi-blackhole/dist/index.js");
  await module.default(proxy);
  return {
    active: () => (loadProfile(state).features.memory ? ["recall"] : []),
    allowed(name: string) {
      if (!loadProfile(state).features.memory) return false;
      const t = pi.getAllTools().find((t) => t.name === name);
      return (
        loadProfile(state).features.memory &&
        name === "recall" &&
        !!t &&
        path.resolve(t.sourceInfo.path) ===
          path.join(PACKAGE_ROOT, "extensions/chrysalis.ts") &&
        digest({
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        }) === definition
      );
    },
  };
}
