import { raw } from "../src/platforms/filesystem.ts";
/** Provider-reported session usage, not a billing or retry guarantee. */
export function specialistUsage(file: string) {
  try {
    const usage = {
        input: 0,
        output: 0,
        cacheRead: 0,
        cacheWrite: 0,
        totalTokens: 0,
      },
      entries = raw(file, 4 * 1024 * 1024)
        .toString("utf8")
        .split("\n");
    let turns = 0;
    for (const line of entries) {
      if (!line.trim()) continue;
      const entry = JSON.parse(line),
        message = entry.type === "message" ? entry.message : null;
      if (message?.role !== "assistant" || !message.usage) continue;
      for (const key of Object.keys(usage) as (keyof typeof usage)[]) {
        const value = message.usage[key];
        if (!Number.isFinite(value) || value < 0) return null;
        usage[key] += value;
      }
      if (message.usage.totalTokens > 0) turns++;
    }
    return turns
      ? { turns, ...usage, source: "provider_reported_session_usage" }
      : null;
  } catch {
    return null;
  }
}
