import fs from "node:fs";
import path from "node:path";
import { assistantRoot } from "./profile.ts";
import { confined, raw, sha256, digest } from "../platforms/filesystem.ts";
/** Only completed lesson/artifact files are eligible. Memory, accounts, settings and recovery are excluded. */
export function retentionPlan(state: string, now = Date.now()) {
  const root = assistantRoot(state),
    records: { path: string; sha256: string; bytes: number }[] = [];
  for (const name of ["artifacts", "lessons"]) {
    const dir = confined(root, name);
    if (!fs.existsSync(dir)) continue;
    for (const filename of fs.readdirSync(dir)) {
      if (!/^[a-f0-9-]{36}\.(json|svg|png|mermaid)$/.test(filename)) continue;
      const relative = name + "/" + filename,
        file = confined(root, relative),
        s = fs.lstatSync(file);
      if (!s.isFile() || s.nlink !== 1 || s.mtimeMs > now - 30 * 86400000)
        continue;
      const data = raw(file, 4 * 1024 * 1024);
      records.push({
        path: relative,
        sha256: sha256(data),
        bytes: data.length,
      });
    }
  }
  const plan = {
    version: 1,
    records,
    totalBytes: records.reduce((n, r) => n + r.bytes, 0),
    excluded: [
      "memory",
      "sessions",
      "browser",
      "settings",
      "credentials",
      "recovery",
    ],
  };
  return { ...plan, digest: digest(plan) };
}
export function applyRetention(
  state: string,
  plan: ReturnType<typeof retentionPlan>,
  approved: string,
) {
  const { digest: identity, ...payload } = plan;
  if (identity !== approved || digest(payload) !== approved)
    throw Error("Retention review changed");
  for (const r of plan.records)
    if (
      sha256(raw(confined(assistantRoot(state), r.path), 4 * 1024 * 1024)) !==
      r.sha256
    )
      throw Error("Retention candidates changed; review again");
  for (const r of plan.records)
    fs.unlinkSync(confined(assistantRoot(state), r.path));
  return { deleted: plan.records.length, bytes: plan.totalBytes };
}
