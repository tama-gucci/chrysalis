import fs from "node:fs";
import path from "node:path";
import { randomUUID, createHash } from "node:crypto";
import { fileURLToPath } from "node:url";

export const PACKAGE_ROOT = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
export const sha256 = (data: string | Buffer) =>
  createHash("sha256").update(data).digest("hex");
export function canonical(value: any): string {
  if (value === null || typeof value !== "object")
    return JSON.stringify(value) ?? "null";
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  return (
    "{" +
    Object.keys(value)
      .filter((k) => value[k] !== undefined)
      .sort()
      .map((k) => JSON.stringify(k) + ":" + canonical(value[k]))
      .join(",") +
    "}"
  );
}
export const digest = (value: any) => sha256(canonical(value));
export function exists(target: string): boolean {
  try {
    fs.lstatSync(target);
    return true;
  } catch (e: any) {
    if (e.code === "ENOENT") return false;
    throw e;
  }
}
export function inside(target: string, root: string): boolean {
  const relative = path.relative(root, target);
  return (
    relative === "" ||
    (!relative.startsWith(".." + path.sep) &&
      relative !== ".." &&
      !path.isAbsolute(relative))
  );
}
export function rejectRedirects(target: string): string {
  if (!path.isAbsolute(target)) throw new Error("Select an absolute path");
  let current = path.resolve(target);
  for (;;) {
    if (exists(current) && fs.lstatSync(current).isSymbolicLink())
      throw new Error("Authoritative paths cannot traverse links or junctions");
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return path.resolve(target);
}
export function confined(root: string, relative: string): string {
  if (
    typeof relative !== "string" ||
    !relative ||
    /[\\:\x00]/.test(relative) ||
    path.isAbsolute(relative) ||
    relative.split("/").some((p) => !p || p === "." || p === "..")
  )
    throw new Error("Expected a confined forward-slash relative path");
  if (
    relative
      .split("/")
      .some(
        (p) =>
          /[. ]$/.test(p) ||
          /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(p),
      )
  )
    throw new Error("Unsupported path entry");
  const target = path.resolve(root, relative);
  if (!inside(target, root)) throw new Error("Path escapes root");
  return rejectRedirects(target);
}
export function rejectPackageAncestry(target: string) {
  const absolute = rejectRedirects(target);
  if (inside(absolute, PACKAGE_ROOT) || inside(PACKAGE_ROOT, absolute))
    throw new Error("Source/package ancestry is forbidden");
  for (let p = absolute; ; p = path.dirname(p)) {
    if (
      exists(path.join(p, ".git")) ||
      exists(path.join(p, "package.json")) ||
      ["node_modules", ".git", ".agents"].includes(path.basename(p))
    )
      throw new Error("Source/package directories are not vaults");
    if (path.dirname(p) === p) break;
  }
  return absolute;
}
export function raw(target: string, limit = 1024 * 1024): Buffer {
  rejectRedirects(target);
  const fd = fs.openSync(target, "r");
  try {
    const buffer = Buffer.alloc(limit + 1);
    let n = 0;
    while (n < buffer.length) {
      const count = fs.readSync(fd, buffer, n, buffer.length - n, n);
      if (!count) break;
      n += count;
    }
    if (n > limit) throw new Error("record_too_large");
    return buffer.subarray(0, n);
  } finally {
    fs.closeSync(fd);
  }
}
export function text(target: string, limit?: number) {
  return new TextDecoder("utf-8", { fatal: true }).decode(raw(target, limit));
}
export function readJSON(target: string) {
  return JSON.parse(text(target, 4 * 1024 * 1024));
}
export function atomic(
  target: string,
  data: string | Buffer,
  expected?: string | null,
  beforeCommit?: () => void,
) {
  rejectRedirects(target);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  const pending = path.join(path.dirname(target), ".pending-" + randomUUID());
  try {
    const fd = fs.openSync(pending, "wx", 0o600);
    try {
      fs.writeFileSync(fd, data);
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
    beforeCommit?.();
    rejectRedirects(target);
    if (
      expected !== undefined &&
      (exists(target) ? sha256(raw(target, 32 * 1024 * 1024)) : null) !==
        expected
    )
      throw new Error("stale_revision: preserve concurrent edits");
    // Exclusive creation avoids overwriting a file that appeared after the final check.
    if (expected === null) {
      fs.linkSync(pending, target);
      fs.unlinkSync(pending);
    } else fs.renameSync(pending, target);
  } finally {
    if (exists(pending)) fs.unlinkSync(pending);
  }
}
export const atomicJSON = (target: string, value: any) =>
  atomic(target, canonical(value) + "\n");
export async function withLock<T>(
  directory: string,
  identity: string,
  action: () => Promise<T> | T,
): Promise<T> {
  rejectRedirects(directory);
  fs.mkdirSync(directory, { recursive: true });
  const lock = path.join(directory, sha256(identity) + ".lock");
  const owner = { pid: process.pid, token: randomUUID() };
  try {
    const fd = fs.openSync(lock, "wx", 0o600);
    try {
      fs.writeFileSync(fd, canonical(owner));
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
  } catch (e: any) {
    if (e.code !== "EEXIST") throw e;
    const previous = readJSON(lock);
    if (!Number.isInteger(previous.pid)) throw new Error("Invalid lock owner");
    try {
      process.kill(previous.pid, 0);
    } catch (probe: any) {
      if (probe.code === "ESRCH") {
        if (canonical(readJSON(lock)) === canonical(previous))
          fs.unlinkSync(lock);
        return withLock(directory, identity, action);
      }
    }
    throw new Error("writer_busy: another cooperating writer owns this scope");
  }
  try {
    return await action();
  } finally {
    if (exists(lock) && readJSON(lock).token === owner.token)
      fs.unlinkSync(lock);
  }
}
/** Short synchronous transitions; an abandoned lock requires native inspection. */
export function withSyncLock<T>(
  directory: string,
  identity: string,
  action: () => T,
): T {
  rejectRedirects(directory);
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const file = path.join(directory, sha256(identity) + ".sync.lock");
  const owner = { pid: process.pid, token: randomUUID() };
  let fd: number;
  try {
    fd = fs.openSync(file, "wx", 0o600);
  } catch {
    throw Error(
      "writer_busy: inspect an active or abandoned transition before retrying",
    );
  }
  try {
    fs.writeFileSync(fd, canonical(owner));
    fs.fsyncSync(fd);
    return action();
  } finally {
    fs.closeSync(fd);
    if (exists(file) && readJSON(file).token === owner.token)
      fs.unlinkSync(file);
  }
}
/** Move first, then verify; conflicting bytes are restored or kept in recovery. */
export function quarantineReviewedFile(
  target: string,
  expected: string,
  recovery: string,
  identity?: {
    dev: number;
    ino: number;
    mtimeMs: number;
    ctimeMs: number;
    bytes: number;
  },
) {
  rejectRedirects(target);
  rejectRedirects(recovery);
  const before = fs.lstatSync(target);
  if (
    !before.isFile() ||
    before.nlink !== 1 ||
    (identity &&
      (before.dev !== identity.dev ||
        before.ino !== identity.ino ||
        before.mtimeMs !== identity.mtimeMs ||
        before.ctimeMs !== identity.ctimeMs ||
        before.size !== identity.bytes))
  )
    throw Error("Removal candidate changed; review again");
  fs.mkdirSync(path.dirname(recovery), { recursive: true, mode: 0o700 });
  if (exists(recovery)) throw Error("Recovery target already exists");
  fs.renameSync(target, recovery);
  try {
    const moved = fs.lstatSync(recovery);
    if (
      !moved.isFile() ||
      moved.nlink !== 1 ||
      moved.dev !== before.dev ||
      moved.ino !== before.ino ||
      moved.mtimeMs !== before.mtimeMs ||
      sha256(raw(recovery, 32 * 1024 * 1024)) !== expected
    )
      throw Error("Removal candidate changed; private recovery preserved");
    return recovery;
  } catch (error) {
    try {
      fs.linkSync(recovery, target);
      fs.unlinkSync(recovery);
    } catch {}
    throw error;
  }
}
export function files(root: string, limit = 10000): string[] {
  const found: string[] = [];
  function walk(dir: string) {
    rejectRedirects(dir);
    for (const entry of fs
      .readdirSync(dir, { withFileTypes: true })
      .sort((a, b) => a.name.localeCompare(b.name))) {
      if (entry.name === ".git" || entry.name === "node_modules") continue;
      const full = path.join(dir, entry.name);
      rejectRedirects(full);
      if (entry.isDirectory()) walk(full);
      else if (entry.isFile()) {
        found.push(full);
        if (found.length > limit) throw new Error("Collection limit exceeded");
      }
    }
  }
  if (exists(root)) walk(root);
  return found;
}
