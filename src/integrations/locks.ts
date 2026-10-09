import { withLock } from "../platforms/filesystem.ts";
import type { RuntimeContext } from "../contracts/types.ts";

/** Cooperating provider processes wait briefly; mutation/approval locks retain their policy. */
export async function providerLock<T>(
  ctx: RuntimeContext,
  root: string,
  id: string,
  action: () => T | Promise<T>,
): Promise<T> {
  const started = Date.now();
  for (;;) {
    if (ctx.signal?.aborted) throw Error("provider_canceled_or_timeout");
    try {
      return await withLock(root, id, action);
    } catch (e: any) {
      if (!String(e.message).startsWith("writer_busy:")) throw e;
      if (Date.now() - started >= 5000)
        throw Error("provider_lock_unavailable");
      await new Promise<void>((resolve, reject) => {
        const cancel = () => {
          clearTimeout(timer);
          reject(Error("provider_canceled_or_timeout"));
        };
        const timer = setTimeout(() => {
          ctx.signal?.removeEventListener("abort", cancel);
          resolve();
        }, 25);
        ctx.signal?.addEventListener("abort", cancel, { once: true });
      });
    }
  }
}
