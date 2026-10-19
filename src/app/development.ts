import fs from "node:fs";
import { optionalSelectedContext } from "../storage/context.ts";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { createJiti } from "jiti";
import {
  assistantRoot,
  loadProfile,
  saveProfile,
  registerWorkspace,
  protectedRoots,
} from "../assistant/profile.ts";
import {
  PACKAGE_ROOT,
  atomic,
  quarantineReviewedFile,
  atomicJSON,
  confined,
  files,
  raw,
  sha256,
  digest,
  readJSON,
  exists,
  inside,
  rejectRedirects,
  withLock,
} from "../platforms/filesystem.ts";
/** Source copies contain reusable bytes only; recovery and review identity stay external. */
export function prepareDevelopment(state: string) {
  const id = randomUUID(),
    root = path.join(
      os.homedir(),
      ".local/share/chrysalis-workspaces",
      "development-" + id,
    );
  const vault = optionalSelectedContext(state)?.vault;
  rejectRedirects(root);
  if (
    protectedRoots(state, vault).some((p) => inside(root, p) || inside(p, root))
  )
    throw Error("Development copy overlaps a protected root");
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  registerWorkspace(state, root, vault);
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
  profile.workspace = registerWorkspace(state, root, vault);
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
  let reviewBytes = 0,
    reviewFiles = 0;
  for (const file of files(record.root)) {
    const rel = path.relative(record.root, file).split(path.sep).join("/");
    const data = raw(file, 32 * 1024 * 1024);
    if (sha256(data) !== record.before[rel]) {
      if (++reviewFiles > 512 || (reviewBytes += data.length) > 3 * 1024 * 1024)
        throw Error("Split source changes into bounded native reviews");
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
  if (
    Buffer.byteLength(JSON.stringify(plan)) > 4 * 1024 * 1024 ||
    changes.length > 512
  )
    throw Error("Split source changes into bounded native reviews");
  return { ...plan, digest: digest(plan) };
}
export async function promoteDevelopment(
  state: string,
  id: string,
  approved: string,
) {
  return withLock(
    path.join(os.tmpdir(), "chrysalis-source-" + sha256(PACKAGE_ROOT)),
    "promotion",
    async () => {
      const plan = await developmentReview(state, id);
      if (plan.digest !== approved) throw Error("Source proposal changed");
      const recovery = confined(assistantRoot(state), "source-recovery/" + id);
      const receipt = confined(
        assistantRoot(state),
        "development-receipts/" + id + ".json",
      );
      const previous = exists(receipt) ? readJSON(receipt) : undefined;
      if (previous && previous.digest !== approved)
        throw Error(
          "Existing promotion identity differs; prepare a fresh development copy",
        );
      const observed = (file: string) =>
        exists(file) ? sha256(raw(file, 32 * 1024 * 1024)) : null;
      for (const c of plan.changes) {
        const hash = observed(confined(PACKAGE_ROOT, c.file));
        if (hash !== c.before && !(previous && hash === c.after))
          throw Error(
            "Live source changed; preserve concurrent edits. Recovery: " +
              recovery,
          );
      }
      const syncParents = (file: string) => {
        const stop = assistantRoot(state);
        for (
          let directory = path.dirname(file);
          ;
          directory = path.dirname(directory)
        ) {
          if (!inside(directory, stop))
            throw Error("Invalid source recovery directory");
          const fd = fs.openSync(rejectRedirects(directory), "r");
          try {
            fs.fsyncSync(fd);
          } finally {
            fs.closeSync(fd);
          }
          if (directory === stop) break;
        }
      };
      const save = (status: string, applied: string[]) => {
        atomicJSON(receipt, { ...plan, recovery, status, applied });
        syncParents(receipt);
      };
      const applied: string[] = previous?.applied ?? [];
      for (const c of plan.changes) {
        const target = confined(PACKAGE_ROOT, c.file),
          before = confined(recovery, c.file);
        if (
          observed(target) === c.before &&
          c.before !== null &&
          !exists(before)
        )
          atomic(before, raw(target, 32 * 1024 * 1024), null);
        if (c.before !== null) {
          if (!exists(before) || observed(before) !== c.before)
            throw Error(
              "Source recovery differs from reviewed before-image; preserve and inspect " +
                recovery,
            );
          syncParents(before);
        }
      }
      save("prepared", applied);
      const p = loadProfile(state);
      p.features.execution = false;
      saveProfile(state, p);
      try {
        for (const c of plan.changes) {
          const target = confined(PACKAGE_ROOT, c.file);
          if (previous && observed(target) === c.after) {
            if (!applied.includes(c.file)) applied.push(c.file);
            save("applying", applied);
            continue;
          }
          if (c.after === null)
            quarantineReviewedFile(
              target,
              c.before!,
              confined(recovery, "removed/" + c.file),
            );
          else atomic(target, c.text, c.before);
          if (!applied.includes(c.file)) applied.push(c.file);
          save("applying", applied);
        }
        save("promoted", applied);
      } catch (error) {
        save("partial-failure", applied);
        throw Error(
          "Source promotion incomplete; preserve and resume reviewed recovery " +
            recovery,
          { cause: error },
        );
      }
      return {
        status: "promoted",
        changed_files: plan.changes.length,
        recovery,
        reload_required: true,
        execution_disabled: true,
        committed: false,
      };
    },
  );
}
