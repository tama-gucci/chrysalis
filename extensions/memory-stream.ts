import { selectedModel } from "./provider-runtime.ts";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai";
import { loadProfile } from "../src/assistant/profile.ts";
import { sharedBudget } from "../src/assistant/budgets.ts";
/** Hold the reservation for the actual provider stream, including cancellation/timeout. */
export function memoryStream(
  state: string,
  registry: any,
  model: any,
  context: any,
  options: any = {},
) {
  const p = loadProfile(state);
  if (
    !p.features.memory ||
    !p.features.observations ||
    !["observer", "reflector", "dropper"].some((r) => {
      const route = p.routes[r as "observer"];
      return (
        route && route.provider === model.provider && route.model === model.id
      );
    })
  )
    throw Error("Memory route is not authorized");
  const selected = selectedModel(registry, {
    provider: model.provider,
    model: model.id,
  });
  if (selected.api !== model.api)
    throw Error("Selected memory API changed; no fallback");
  const done = sharedBudget(
    state,
    p.limits.calls,
    p.limits.concurrency,
  ).reserve("memory_provider_turn");
  const output = createAssistantMessageEventStream(),
    controller = new AbortController();
  const signal = options.signal
    ? AbortSignal.any([options.signal, controller.signal])
    : controller.signal;
  let completed = false,
    usage: any;
  const finish = () => {
    if (!completed) {
      completed = true;
      clearTimeout(timer);
      signal.removeEventListener("abort", onAbort);
      done(usage);
    }
  };
  const fail = () => {
    if (completed) return;
    const message: any = {
      role: "assistant",
      content: [],
      api: model.api,
      provider: model.provider,
      model: model.id,
      usage: {
        input: 0,
        output: 0,
        cacheRead: 0,
        cacheWrite: 0,
        totalTokens: 0,
        cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
      },
      stopReason: "error",
      errorMessage: "Memory work stopped or unavailable; no fallback",
      timestamp: Date.now(),
    };
    output.push({ type: "error", reason: "error", error: message });
    output.end(message);
    finish();
  };
  const timer = setTimeout(() => {
    controller.abort();
    fail();
  }, 60000);
  const onAbort = () => fail();
  signal.addEventListener("abort", onAbort, { once: true });
  void (async () => {
    try {
      if (signal.aborted) throw Error("Cancelled");
      const upstream = await registry.streamSimple(selected, context, {
        ...options,
        signal,
        maxTokens: Math.min(
          options.maxTokens ?? 1500,
          1500,
          selected.maxTokens ?? 1500,
        ),
      });
      for await (const event of upstream) {
        if (completed) break;
        output.push(event);
        if (event.type === "done" || event.type === "error") {
          usage = (event.message ?? event.error)?.usage;
          output.end(event.message ?? event.error);
          finish();
        }
      }
      if (!completed) fail();
    } catch {
      if (!completed) fail();
    }
  })();
  return output;
}
