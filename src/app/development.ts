import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { createJiti } from "jiti";
import {
  assistantRoot,
  loadProfile,
  saveProfile,
  registerWorkspace,
} from "../assistant/profile.ts";
import {
  PACKAGE_ROOT,
  atomic,
  atomicJSON,
  confined,
  files,
  raw,
  sha256,
  digest,
  readJSON,
  exists,
} from "../platforms/filesystem.ts";
/** Source copies contain reusable bytes only; recovery and review identity stay external. */
export function prepareDevelopment(state: string) {
  const id = randomUUID(),
    root = path.join(
      os.homedir(),
      ".local/share/chrysalis-workspaces",
      "development-" + id,
    );
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  const before: Record<string, string> = Object.create(null);
  for (const file of files(PACKAGE_ROOT)) {
    const rel = path.relative(PACKAGE_ROOT, file).split(path.sep).join("/");
    const data = raw(file, 32 * 1024 * 1024);
    before[rel] = sha256(data);
    atomic(confined(root, rel), data, null);
  }
  atomicJSON(confined(assistantRoot(state), "development/" + id + ".json"), {
    version: 1,
    id,
    root,
    before,
  });
  const profile = loadProfile(state);
  profile.workspace = registerWorkspace(state, root);
  profile.features.execution = true;
  saveProfile(state, profile);
  return {
    id,
    workspace: root,
    source: PACKAGE_ROOT,
    status: "prepared",
    source_unchanged: true,
  };
}
export async function developmentReview(state: string, id: string) {
  if (!/^[a-f0-9-]{36}$/.test(id)) throw Error("Invalid development ID");
  const record = readJSON(
    confined(assistantRoot(state), "development/" + id + ".json"),
  );
  if (record.version !== 1 || record.id !== id)
    throw Error("Invalid development identity");
  const jiti = createJiti(import.meta.url, { fsCache: false });
  const checker: any = await jiti.import(
    path.join(PACKAGE_ROOT, "Development/scripts/check.mjs"),
  );
  const check = checker.check(record.root);
  if (check.status !== "passed")
    throw Error(
      "Source privacy/resource checks failed; correct the development copy first",
    );
  const after: Record<string, { hash: string; text: string }> =
    Object.create(null);
  for (const file of files(record.root)) {
    const rel = path.relative(record.root, file).split(path.sep).join("/");
    const data = raw(file, 32 * 1024 * 1024);
    if (sha256(data) !== record.before[rel]) {
      const text = new TextDecoder("utf-8", { fatal: true }).decode(data);
      if (data.length > 1024 * 1024)
        throw Error("Split large source changes for review");
      after[rel] = { hash: sha256(data), text };
    }
  }
  const changes = Object.entries(after).map(([file, v]) => ({
    file,
    before: record.before[file] ?? null,
    after: v.hash,
    text: v.text,
  }));
  for (const file of Object.keys(record.before))
    if (!exists(confined(record.root, file)))
      changes.push({
        file,
        before: record.before[file],
        after: null as any,
        text: null as any,
      });
  const plan = {
    version: 1,
    id,
    root: record.root,
    changes,
    checks: {
      privacy: check.status,
      full_suite: "required_before_publication; not run by this review command",
    },
  };
  return { ...plan, digest: digest(plan) };
}
export async function promoteDevelopment(
  state: string,
  id: string,
  approved: string,
) {
  const plan = await developmentReview(state, id);
  if (plan.digest !== approved) throw Error("Source proposal changed");
  for (const c of plan.changes) {
    const target = confined(PACKAGE_ROOT, c.file);
    if (
      (exists(target) ? sha256(raw(target, 32 * 1024 * 1024)) : null) !==
      c.before
    )
      throw Error("Live source changed; preserve concurrent edits");
  }
  const recovery = confined(
    assistantRoot(state),
    "source-recovery/" + randomUUID(),
  );
  for (const c of plan.changes) {
    const target = confined(PACKAGE_ROOT, c.file);
    if (exists(target))
      atomic(confined(recovery, c.file), raw(target, 32 * 1024 * 1024), null);
  }
  const p = loadProfile(state);
  p.features.execution = false;
  saveProfile(state, p);
  for (const c of plan.changes) {
    const target = confined(PACKAGE_ROOT, c.file);
    if (c.after === null) {
      if (sha256(raw(target, 32 * 1024 * 1024)) !== c.before)
        throw Error("Live source changed");
      fs.unlinkSync(target);
    } else atomic(target, c.text, c.before);
  }
  atomicJSON(
    confined(assistantRoot(state), "development-receipts/" + id + ".json"),
    plan,
  );
  return {
    status: "promoted",
    changed_files: plan.changes.length,
    reload_required: true,
    execution_disabled: true,
    committed: false,
  };
}
