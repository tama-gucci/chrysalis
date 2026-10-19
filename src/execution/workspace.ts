import { isPasswordExport } from "../passwords/import.ts";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  atomic,
  confined,
  rejectRedirects,
  sha256,
  raw,
  exists,
} from "../platforms/filesystem.ts";
export interface WorkspaceImage {
  directory: string;
  revisions: Record<string, string>;
  files: number;
  bytes: number;
}
export function excluded(name: string) {
  return (
    [
      ".git",
      ".pi",
      ".ssh",
      ".gnupg",
      ".aws",
      ".azure",
      ".gcloud",
      ".kube",
      ".docker",
      ".npmrc",
      ".netrc",
      ".git-credentials",
      ".pypirc",
      ".yarnrc",
    ].includes(name.toLowerCase()) ||
    /^\.env(?:\.|$)/.test(name) ||
    /^(auth\.json|credentials.*|id_(rsa|dsa|ecdsa|ed25519)(?:_sk)?|.*\.(key|pem|p12))$/i.test(
      name,
    )
  );
}
/** Never mount original host inodes. Bounded copies reject hardlinks and special files. */
export function snapshotWorkspace(
  root: string,
  privateRoot: string,
): WorkspaceImage {
  const directory = path.join(privateRoot, randomUUID());
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  const revisions: Record<string, string> = Object.create(null);
  let bytes = 0,
    count = 0;
  function walk(dir: string, rel = "") {
    rejectRedirects(dir);
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if ([".chrysalis-vault.json", ".obsidian"].includes(e.name))
        throw Error(
          "Workspace became a vault; no execution or merge is permitted",
        );
      if (excluded(e.name)) continue;
      const relative = rel ? rel + "/" + e.name : e.name,
        source = confined(root, relative),
        s = fs.lstatSync(source);
      if (
        ++count > 20000 ||
        s.isSymbolicLink() ||
        (!s.isDirectory() && !s.isFile())
      )
        throw Error("Workspace contains unsupported entries or exceeds limits");
      if (s.isDirectory()) {
        fs.mkdirSync(confined(directory, relative), { mode: 0o700 });
        walk(source, relative);
        continue;
      }
      if (
        s.nlink !== 1 ||
        s.size > 16 * 1024 * 1024 ||
        (bytes += s.size) > 64 * 1024 * 1024
      )
        throw Error("Workspace links or copy limit exceeded");
      const fd = fs.openSync(
        source,
        fs.constants.O_RDONLY |
          fs.constants.O_NOFOLLOW |
          fs.constants.O_NONBLOCK,
      );
      try {
        const actual = fs.fstatSync(fd);
        if (
          !actual.isFile() ||
          actual.nlink !== 1 ||
          actual.dev !== s.dev ||
          actual.ino !== s.ino ||
          actual.size !== s.size
        )
          throw Error("Workspace file changed during capture");
        const buffer = Buffer.alloc(s.size + 1);
        let read = 0;
        while (read < buffer.length) {
          const n = fs.readSync(fd, buffer, read, buffer.length - read, read);
          if (!n) break;
          read += n;
        }
        const data = buffer.subarray(0, read),
          final = fs.fstatSync(fd);
        if (
          data.length !== s.size ||
          final.size !== s.size ||
          final.mtimeMs !== actual.mtimeMs ||
          final.ctimeMs !== actual.ctimeMs
        )
          throw Error("Workspace file changed during capture");
        if (isPasswordExport(data))
          throw Error("Password exports cannot enter execution workspaces");
        revisions[relative] = sha256(data);
        fs.writeFileSync(confined(directory, relative), data, {
          flag: "wx",
          mode: s.mode & 0o777,
        });
      } finally {
        fs.closeSync(fd);
      }
    }
  }
  try {
    walk(root);
    return { directory, revisions, files: count, bytes };
  } catch (e) {
    fs.rmSync(directory, { recursive: true, force: true });
    throw e;
  }
}
export function mergeWorkspace(root: string, image: WorkspaceImage) {
  const after = snapshotWorkspace(
    image.directory,
    path.dirname(image.directory),
  );
  try {
    const changed = [
      ...new Set([
        ...Object.keys(image.revisions),
        ...Object.keys(after.revisions),
      ]),
    ].filter((r) => image.revisions[r] !== after.revisions[r]);
    for (const rel of changed) {
      const target = confined(root, rel);
      if (exists(target)) {
        const s = fs.lstatSync(target);
        if (
          !s.isFile() ||
          s.nlink !== 1 ||
          sha256(raw(target, 32 * 1024 * 1024)) !== image.revisions[rel]
        )
          throw Error("Workspace conflict; results retained for review");
      } else if (image.revisions[rel] !== undefined)
        throw Error("Workspace conflict; results retained for review");
    }
    for (const rel of changed) {
      const target = confined(root, rel);
      if (after.revisions[rel] === undefined) {
        if (sha256(raw(target, 32 * 1024 * 1024)) !== image.revisions[rel])
          throw Error("Workspace conflict");
        fs.unlinkSync(target);
      } else {
        atomic(
          target,
          raw(confined(after.directory, rel), 32 * 1024 * 1024),
          image.revisions[rel] ?? null,
        );
        const descriptor = fs.openSync(
          target,
          fs.constants.O_RDONLY | fs.constants.O_NOFOLLOW,
        );
        try {
          const actual = fs.fstatSync(descriptor);
          if (
            !actual.isFile() ||
            actual.nlink !== 1 ||
            sha256(raw(target, 32 * 1024 * 1024)) !== after.revisions[rel]
          )
            throw Error("Workspace changed before mode update");
          fs.fchmodSync(
            descriptor,
            fs.statSync(confined(after.directory, rel)).mode & 0o777,
          );
        } finally {
          fs.closeSync(descriptor);
        }
      }
    }
    return { changedFiles: changed.length };
  } finally {
    fs.rmSync(after.directory, { recursive: true, force: true });
  }
}
