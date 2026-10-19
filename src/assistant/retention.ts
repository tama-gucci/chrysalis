import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { assistantRoot } from "./profile.ts";
import {
  confined,
  raw,
  sha256,
  digest,
  quarantineReviewedFile,
  withSyncLock,
} from "../platforms/filesystem.ts";
/** Only completed lesson/artifact files are eligible. */
export function retentionPlan(state: string, now = Date.now()) {
  return withSyncLock(assistantRoot(state), "private-output-retention", () => {
    const root = assistantRoot(state),
      records: {
        path: string;
        sha256: string;
        bytes: number;
        dev: number;
        ino: number;
        mtimeMs: number;
        ctimeMs: number;
      }[] = [];
    for (const name of ["artifacts", "lessons"]) {
      const dir = confined(root, name);
      if (!fs.existsSync(dir)) continue;
      for (const filename of fs.readdirSync(dir)) {
        if (!/^[a-f0-9-]{36}\.(json|svg|png|mermaid)$/.test(filename)) continue;
        const relative = name + "/" + filename,
          file = confined(root, relative),
          stat = fs.lstatSync(file);
        if (
          !stat.isFile() ||
          stat.nlink !== 1 ||
          stat.mtimeMs > now - 30 * 86400000
        )
          continue;
        const data = raw(file, 4 * 1024 * 1024);
        records.push({
          path: relative,
          sha256: sha256(data),
          bytes: data.length,
          dev: stat.dev,
          ino: stat.ino,
          mtimeMs: stat.mtimeMs,
          ctimeMs: stat.ctimeMs,
        });
      }
    }
    const plan = {
      version: 2,
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
  });
}
export function applyRetention(
  state: string,
  plan: ReturnType<typeof retentionPlan>,
  approved: string,
) {
  return withSyncLock(assistantRoot(state), "private-output-retention", () => {
    const { digest: identity, ...payload } = plan;
    if (identity !== approved || digest(payload) !== approved)
      throw Error("Retention review changed");
    const root = assistantRoot(state);
    for (const r of plan.records) {
      if (
        !/^(artifacts|lessons)\/[a-f0-9-]{36}\.(json|svg|png|mermaid)$/.test(
          r.path,
        )
      )
        throw Error("Invalid retention candidate");
      const file = confined(root, r.path),
        st = fs.lstatSync(file);
      if (
        !st.isFile() ||
        st.nlink !== 1 ||
        st.dev !== r.dev ||
        st.ino !== r.ino ||
        st.mtimeMs !== r.mtimeMs ||
        st.ctimeMs !== r.ctimeMs ||
        st.size !== r.bytes ||
        sha256(raw(file, 4 * 1024 * 1024)) !== r.sha256
      )
        throw Error("Retention candidates changed; review again");
    }
    const recovery = confined(root, "retention-recovery/" + randomUUID());
    for (const r of plan.records) {
      const moved = quarantineReviewedFile(
        confined(root, r.path),
        r.sha256,
        confined(recovery, r.path),
        r,
      );
      // Completed outputs share this transition lock with all native writers.
      fs.unlinkSync(moved);
    }
    return { deleted: plan.records.length, bytes: plan.totalBytes };
  });
}
