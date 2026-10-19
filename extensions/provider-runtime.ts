import net from "node:net";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { randomBytes } from "node:crypto";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai";
import { digest } from "../src/platforms/filesystem.ts";

export function selectedModel(registry: any, route: any) {
  if (!route || typeof registry?.streamSimple !== "function")
    throw Error("Selected provider runtime unavailable; no fallback");
  const model = registry.find(route.provider, route.model);
  if (
    !model ||
    (model.type && model.type !== "chat") ||
    !registry
      .getAvailable()
      .some((m: any) => m.provider === route.provider && m.id === route.model)
  )
    throw Error("Selected model unavailable; no fallback");
  return model;
}
function catalog(model: any) {
  // Public model fields only. Headers, URLs, credentials and provider internals never cross.
  const { id, name, api, reasoning, input, cost, contextWindow, maxTokens } =
    model;
  return { id, name, api, reasoning, input, cost, contextWindow, maxTokens };
}
export interface RuntimeRoute {
  address: string;
  token: string;
  model: any;
  identity: string;
  timeoutSeconds?: number;
}
/** One parent-owned model route, limited to one child and its turn/lifetime budget. */
export async function openRuntimeRoute(registry: any, route: any, limits: any) {
  const timeoutSeconds = Math.min(900, Math.max(5, limits.timeoutSeconds));
  const model = selectedModel(registry, route),
    metadata = catalog(model),
    identity = digest(metadata),
    token = randomBytes(32).toString("hex"),
    directory = fs.mkdtempSync(path.join(os.tmpdir(), "chrysalis-runtime-"));
  fs.chmodSync(directory, 0o700);
  const address =
    process.platform === "win32"
      ? "\\\\.\\pipe\\chrysalis-" + token
      : path.join(directory, "stream");
  const sockets = new Set<net.Socket>();
  let disposed = false,
    active = false,
    calls = 0;
  const server = net.createServer((socket) => {
    sockets.add(socket);
    socket.setEncoding("utf8");
    const controller = new AbortController();
    socket.on("error", () => {});
    socket.on("close", () => {
      sockets.delete(socket);
      controller.abort();
    });
    socket.setTimeout(timeoutSeconds * 1000, () => socket.destroy());
    let request = "",
      accepted = false;
    socket.on("data", async (chunk) => {
      if (accepted) {
        socket.destroy();
        return;
      }
      request += chunk.toString("utf8");
      if (Buffer.byteLength(request) > 4 * 1024 * 1024) {
        socket.destroy();
        return;
      }
      if (!request.includes("\n")) return;
      accepted = true;
      let owns = false;
      try {
        const value = JSON.parse(request.trim());
        request = "";
        if (
          disposed ||
          value.token !== token ||
          active ||
          calls >= limits.turns ||
          !value.context ||
          !Array.isArray(value.context.messages)
        )
          throw Error("Bounded runtime request refused");
        if (digest(catalog(selectedModel(registry, route))) !== identity)
          throw Error("Selected model changed; no fallback");
        active = true;
        owns = true;
        calls++;
        const maxTokens = Math.min(metadata.maxTokens, 4096);
        let bytes = 0,
          ended = false;
        for await (const event of registry.streamSimple(model, value.context, {
          signal: controller.signal,
          reasoning: route.thinking,
          maxTokens,
        })) {
          if (controller.signal.aborted || disposed) break;
          const line = JSON.stringify(event) + "\n";
          bytes += Buffer.byteLength(line);
          if (bytes > 32 * 1024 * 1024)
            throw Error("Child stream output limit");
          if (!socket.write(line))
            await new Promise<void>((resolve) => {
              socket.once("drain", resolve);
              socket.once("close", resolve);
            });
          if (event.type === "done" || event.type === "error") {
            ended = true;
            break;
          }
        }
        if (!ended)
          throw Error("Selected provider stream ended without a result");
        socket.end();
      } catch {
        socket.destroy();
      } finally {
        if (owns) active = false;
      }
    });
  });
  server.on("error", () => {});
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    clearTimeout(timer);
    for (const socket of sockets) socket.destroy();
    server.close();
    fs.rmSync(directory, { recursive: true, force: true });
  };
  const timer = setTimeout(dispose, limits.timeoutSeconds * 1000);
  timer.unref();
  try {
    await new Promise<void>((resolve, reject) => {
      server.once("error", reject);
      server.listen(address, () => {
        server.off("error", reject);
        resolve();
      });
    });
    if (process.platform !== "win32") fs.chmodSync(address, 0o600);
  } catch (error) {
    dispose();
    throw error;
  }
  return {
    endpoint: {
      address,
      token,
      model: metadata,
      identity,
      timeoutSeconds,
    } as RuntimeRoute,
    dispose,
  };
}

/** A child sees only its fixed chat stream; it receives no provider code or credentials. */
export function runtimeStream(
  endpoint: RuntimeRoute,
  model: any,
  context: any,
  options: any = {},
) {
  const output = createAssistantMessageEventStream();
  let finished = false,
    buffer = "",
    bytes = 0;
  const socket = net.createConnection(endpoint.address);
  socket.setEncoding("utf8");
  const finish = (event?: any) => {
    if (finished) return;
    finished = true;
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", abort);
    if (event) {
      output.push(event);
      output.end(event.message ?? event.error);
    } else {
      const error: any = {
        role: "assistant",
        content: [],
        api: model.api,
        provider: model.provider,
        model: model.id,
        timestamp: Date.now(),
        usage: {
          input: 0,
          output: 0,
          cacheRead: 0,
          cacheWrite: 0,
          totalTokens: 0,
          cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
        },
        stopReason: "error",
        errorMessage: "Selected parent runtime unavailable; no fallback",
      };
      output.push({ type: "error", reason: "error", error });
      output.end(error);
    }
    socket.destroy();
  };
  const abort = () => finish();
  const timer = setTimeout(
    abort,
    Math.min(900, Math.max(5, endpoint.timeoutSeconds ?? 120)) * 1000,
  );
  options.signal?.addEventListener("abort", abort, { once: true });
  socket.on("error", abort);
  socket.on("close", () => {
    if (!finished) finish();
  });
  socket.on("connect", () => {
    if (options.signal?.aborted) {
      finish();
      return;
    }
    try {
      const request = JSON.stringify({ token: endpoint.token, context }) + "\n";
      if (Buffer.byteLength(request) > 4 * 1024 * 1024)
        throw Error("Request limit");
      socket.write(request);
    } catch {
      finish();
    }
  });
  socket.on("data", (chunk) => {
    bytes += Buffer.byteLength(chunk);
    if (bytes > 32 * 1024 * 1024) {
      finish();
      return;
    }
    buffer += chunk.toString("utf8");
    let split;
    while (!finished && (split = buffer.indexOf("\n")) >= 0) {
      const line = buffer.slice(0, split);
      buffer = buffer.slice(split + 1);
      try {
        const event = JSON.parse(line);
        if (event.type === "done" || event.type === "error") finish(event);
        else output.push(event);
      } catch {
        finish();
      }
    }
  });
  return output;
}
export function registerRuntimeRoute(
  pi: any,
  endpoint: RuntimeRoute,
  route: any,
) {
  if (
    !endpoint ||
    digest(endpoint.model) !== endpoint.identity ||
    endpoint.model.id !== route.model ||
    !/^[a-f0-9]{64}$/.test(endpoint.token)
  )
    throw Error("Invalid fixed provider route");
  pi.registerProvider(route.provider, {
    api: endpoint.model.api,
    apiKey: "chrysalis-parent-runtime",
    baseUrl: "http://invalid.local",
    models: [endpoint.model],
    streamSimple: (model: any, context: any, options: any) =>
      runtimeStream(endpoint, model, context, options),
  });
}
