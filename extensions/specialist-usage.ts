import fs from "node:fs";
import { rejectRedirects } from "../src/platforms/filesystem.ts";
/** Provider-reported session usage, not a billing or retry guarantee. */
export function specialistUsage(file: string) {
  let fd: number | undefined;
  try {
    fd = fs.openSync(
      rejectRedirects(file),
      fs.constants.O_RDONLY |
        (fs.constants.O_NOFOLLOW ?? 0) |
        (fs.constants.O_NONBLOCK ?? 0),
    );
    if (!fs.fstatSync(fd).isFile()) return null;
    const usage = {
      input: 0,
      output: 0,
      cacheRead: 0,
      cacheWrite: 0,
      totalTokens: 0,
    };
    let turns = 0,
      line = "",
      offset = 0,
      total = 0;
    const buffer = Buffer.alloc(64 * 1024);
    const consume = (text: string) => {
      if (!text.trim()) return;
      const entry = JSON.parse(text),
        m = entry.type === "message" ? entry.message : null;
      if (m?.role !== "assistant" || !m.usage) return;
      for (const key of Object.keys(usage) as (keyof typeof usage)[]) {
        const value = m.usage[key];
        if (!Number.isFinite(value) || value < 0)
          throw Error("Invalid session usage");
        usage[key] += value;
      }
      if (m.usage.totalTokens > 0) turns++;
    };
    for (;;) {
      const n = fs.readSync(fd, buffer, 0, buffer.length, offset);
      if (!n) break;
      offset += n;
      if ((total += n) > 512 * 1024 * 1024) return null;
      line += buffer.subarray(0, n).toString("utf8");
      let at: number;
      while ((at = line.indexOf("\n")) >= 0) {
        consume(line.slice(0, at));
        line = line.slice(at + 1);
      }
      if (line.length > 32 * 1024 * 1024) return null;
    }
    consume(line);
    return turns
      ? { turns, ...usage, source: "provider_reported_session_usage" }
      : null;
  } catch {
    return null;
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
  }
}
