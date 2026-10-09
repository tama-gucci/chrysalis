import type { RuntimeContext, Metadata } from "../contracts/types.ts";
import type { ProviderPorts } from "./contracts.ts";
const ENDPOINTS =
  /^(https:\/\/tasks\.googleapis\.com\/tasks\/v1\/|https:\/\/health\.googleapis\.com\/v4\/users\/me\/|https:\/\/places\.googleapis\.com\/v1\/places:searchText$|https:\/\/routes\.googleapis\.com\/directions\/v2:computeRoutes$)/;
let active = 0;
const pending: Array<() => void> = [];
async function acquire(signal: AbortSignal) {
  if (signal.aborted) throw Error("provider_canceled_or_timeout");
  if (active < 4) {
    active++;
    return;
  }
  await new Promise<void>((resolve, reject) => {
    const start = () => {
      signal.removeEventListener("abort", cancel);
      resolve();
    };
    const cancel = () => {
      const at = pending.indexOf(start);
      if (at >= 0) pending.splice(at, 1);
      reject(Error("provider_canceled_or_timeout"));
    };
    pending.push(start);
    signal.addEventListener("abort", cancel, { once: true });
  });
}
function release() {
  const next = pending.shift();
  if (next) next();
  else active--;
}
export async function providerJSON(
  ctx: RuntimeContext,
  ports: ProviderPorts,
  url: string,
  init: RequestInit = {},
): Promise<Metadata> {
  if (!ENDPOINTS.test(url) || !["GET", "POST"].includes(init.method ?? "GET"))
    throw Error("provider_endpoint_forbidden");
  if (
    (init.method ?? "GET") === "POST" &&
    !/^https:\/\/(places|routes)\.googleapis\.com\//.test(url)
  )
    throw Error("provider_write_forbidden");
  const signal = AbortSignal.any([
    AbortSignal.timeout(10000),
    ...(ctx.signal ? [ctx.signal] : []),
  ]);
  await acquire(signal);
  try {
    const response = await ports.fetch(url, {
      ...init,
      signal,
      redirect: "error",
    });
    if (!response.ok) throw Error("provider_http_" + response.status);
    if (!response.body) throw Error("provider_empty_response");
    const reader = response.body.getReader(),
      chunks: Uint8Array[] = [];
    let size = 0;
    try {
      for (;;) {
        const chunk = await reader.read();
        if (chunk.done) break;
        if ((size += chunk.value.length) > 1024 * 1024)
          throw Error("provider_response_limit");
        chunks.push(chunk.value);
      }
    } finally {
      await reader.cancel().catch(() => {});
    }
    const result = JSON.parse(
      new TextDecoder("utf-8", { fatal: true }).decode(Buffer.concat(chunks)),
    );
    if (!result || typeof result !== "object" || Array.isArray(result))
      throw Error("provider_invalid_response");
    return result;
  } catch (e: any) {
    const code = String(e?.message);
    throw Error(
      /^provider_(http_\d{3}|response_limit|empty_response|invalid_response)$/.test(
        code,
      )
        ? code
        : signal.aborted
          ? "provider_canceled_or_timeout"
          : "provider_unavailable",
    );
  } finally {
    release();
  }
}
