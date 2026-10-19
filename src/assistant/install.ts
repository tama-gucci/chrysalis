import { processStart } from "../execution/lease.ts";
import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import { assistantRoot } from "./profile.ts";
import {
  atomicJSON,
  readJSON,
  exists,
  rejectRedirects,
  PACKAGE_ROOT,
  sha256,
  confined,
  inside,
  digest,
  withLock,
  withSyncLock,
} from "../platforms/filesystem.ts";
const PACKS = {
  browser: { playwright: "1.64.0" },
  media: { "pi-web-access": "0.38.0" },
} as const;
export type Pack = keyof typeof PACKS;
export function packRoot(state: string, pack: Pack) {
  const file = path.join(assistantRoot(state), "packs", pack + ".json");
  if (!exists(file))
    throw Error(
      "Install the optional " + pack + " pack through native capabilities",
    );
  const entry = readJSON(file);
  if (
    entry.version !== 1 ||
    JSON.stringify(entry.dependencies) !== JSON.stringify(PACKS[pack]) ||
    typeof entry.root !== "string" ||
    !path.isAbsolute(entry.root) ||
    !inside(entry.root, path.join(assistantRoot(state), "packs")) ||
    !new RegExp("^" + pack + "-[a-f0-9-]{36}$").test(path.basename(entry.root))
  )
    throw Error("Optional pack identity changed");
  rejectRedirects(entry.root);
  const manifest = readJSON(path.join(entry.root, "package.json"));
  if (JSON.stringify(manifest.dependencies) !== JSON.stringify(PACKS[pack]))
    throw Error("Optional pack manifest drift");
  const expected = readJSON(
    path.join(
      PACKAGE_ROOT,
      "resources/optional-packs",
      pack,
      "package-lock.json",
    ),
  );
  if (
    digest(readJSON(path.join(entry.root, "package-lock.json"))) !==
      digest(expected) ||
    digest(entry.lock) !== digest(expected)
  )
    throw Error("Optional pack lock drift");
  if (pack === "browser") {
    if (
      typeof entry.browserExecutable !== "string" ||
      !inside(entry.browserExecutable, path.join(entry.root, "browsers"))
    )
      throw Error("Browser executable identity changed");
    rejectRedirects(entry.browserExecutable);
    fs.accessSync(entry.browserExecutable, fs.constants.X_OK);
  }
  return entry.root as string;
}
function cleanupManagedPacks(parent: string, pack: Pack, selected: string) {
  const uses = path.join(parent, "uses"),
    active = new Set<string>();
  if (exists(uses))
    for (const name of fs.readdirSync(uses)) {
      const file = confined(uses, name),
        lease = readJSON(file);
      if (
        !Number.isSafeInteger(lease.pid) ||
        typeof lease.start !== "string" ||
        typeof lease.root !== "string" ||
        !inside(lease.root, parent)
      )
        throw Error("Uncertain optional pack user; retain retired trees");
      if (processStart(lease.pid) === lease.start) active.add(lease.root);
      else fs.unlinkSync(file);
    }
  for (const name of fs.readdirSync(parent)) {
    if (!new RegExp("^" + pack + "-[a-f0-9-]{36}$").test(name)) continue;
    const root = confined(parent, name);
    if (root !== selected && !active.has(root))
      fs.rmSync(root, { recursive: true, force: true });
  }
}
/** Pin a managed pack until its browser closes or its media request finishes. */
export function acquirePack(state: string, pack: Pack) {
  const parent = path.join(assistantRoot(state), "packs");
  return withSyncLock(parent, "optional-pack-pointers", () => {
    const root = packRoot(state, pack);
    const start = processStart(process.pid);
    if (!start) throw Error("Cannot identify optional pack user");
    const file = confined(parent, "uses/" + randomUUID() + ".json");
    atomicJSON(file, { root, pid: process.pid, start });
    let released = false;
    return {
      root,
      browserExecutable:
        pack === "browser"
          ? (readJSON(path.join(parent, pack + ".json"))
              .browserExecutable as string)
          : undefined,
      release() {
        if (released) return;
        withSyncLock(parent, "optional-pack-pointers", () => {
          if (exists(file)) fs.unlinkSync(file);
          released = true;
          const pointer = path.join(parent, pack + ".json");
          if (exists(pointer))
            cleanupManagedPacks(parent, pack, readJSON(pointer).root);
        });
      },
    };
  });
}
async function command(
  program: string,
  args: string[],
  cwd: string,
  env: NodeJS.ProcessEnv,
  capture = false,
) {
  return await new Promise<string>((resolve, reject) => {
    let output = "",
      failure: Error | undefined;
    const child = spawn(program, args, {
      cwd,
      env,
      stdio: capture ? ["ignore", "pipe", "ignore"] : "ignore",
    });
    const stop = (error: Error) => {
      failure ??= error;
      child.kill("SIGKILL");
    };
    child.stdout?.on("data", (b) => {
      if (failure) return;
      output += b.toString();
      if (output.length > 8192) stop(Error("Installer output limit"));
    });
    const timer = setTimeout(
      () => stop(Error("Optional install timed out")),
      180000,
    );
    child.on("error", () => {
      failure ??= Error("Optional installer unavailable");
    });
    // Cleanup must wait until the installer and its output pipes have closed.
    child.on("close", (code) => {
      clearTimeout(timer);
      if (failure) reject(failure);
      else if (code === 0) resolve(output);
      else
        reject(
          Error("Optional install failed; previous pack remains selected"),
        );
    });
  });
}
/** Invoked only after native confirmation, never exposed through a model tool. */
export async function installPack(state: string, pack: Pack) {
  if (
    process.platform !== "linux" ||
    Number(process.versions.node.split(".")[0]) < 24
  )
    throw Error(
      "Optional packs currently require accepted Linux Node 24; base functions remain available",
    );
  const parent = path.join(assistantRoot(state), "packs");
  rejectRedirects(parent);
  fs.mkdirSync(parent, { recursive: true, mode: 0o700 });
  return withLock(parent, "install-" + pack, async () => {
    try {
      return {
        status: "installed",
        pack,
        account_connected: false,
        already_present: !!packRoot(state, pack),
      };
    } catch {}
    const pointer = path.join(parent, pack + ".json");
    const root = path.join(parent, pack + "-" + randomUUID());
    const installLease = confined(parent, "uses/" + randomUUID() + ".json");
    withSyncLock(parent, "optional-pack-pointers", () => {
      const start = processStart(process.pid);
      if (!start) throw Error("Cannot identify optional installer");
      fs.mkdirSync(root, { mode: 0o700 });
      atomicJSON(installLease, { root, pid: process.pid, start });
    });
    let committed = false;
    try {
      const lock = readJSON(
        path.join(
          PACKAGE_ROOT,
          "resources/optional-packs",
          pack,
          "package-lock.json",
        ),
      );
      atomicJSON(path.join(root, "package.json"), {
        name: "chrysalis-" + pack + "-pack",
        version: "1.0.0",
        private: true,
        type: "module",
        dependencies: PACKS[pack],
      });
      atomicJSON(path.join(root, "package-lock.json"), lock);
      const env = {
        PATH: path.dirname(process.execPath) + ":/usr/bin:/bin",
        HOME: root,
        npm_config_cache: path.join(parent, "npm-cache"),
        PLAYWRIGHT_BROWSERS_PATH: path.join(root, "browsers"),
        npm_config_ignore_scripts: "true",
        npm_config_audit: "false",
      };
      await command(
        "npm",
        ["ci", "--ignore-scripts", "--legacy-peer-deps", "--omit=dev"],
        root,
        env,
      );
      if (pack === "browser") {
        await command(
          process.execPath,
          [
            path.join(root, "node_modules/playwright/cli.js"),
            "install",
            "chromium",
            "--no-shell",
          ],
          root,
          env,
        );
        const lock = readJSON(
          path.join(PACKAGE_ROOT, "resources/browser.lock.json"),
        ).adblock;
        const response = await fetch(lock.url, {
          signal: AbortSignal.timeout(60000),
        });
        if (!response.ok || !response.body)
          throw Error("Pinned adblock download unavailable");
        const chunks: Uint8Array[] = [];
        let size = 0;
        const reader = response.body.getReader();
        try {
          for (;;) {
            const part = await reader.read();
            if (part.done) break;
            if ((size += part.value.length) > lock.bytes)
              throw Error("Adblock asset size changed");
            chunks.push(part.value);
          }
        } finally {
          await reader.cancel().catch(() => {});
        }
        const archive = Buffer.concat(chunks);
        if (archive.length !== lock.bytes || sha256(archive) !== lock.sha256)
          throw Error("Adblock asset integrity changed");
        const { unzipSync } = await import("fflate");
        const entries = unzipSync(archive);
        const extension = path.join(root, "adblock");
        fs.mkdirSync(extension, { mode: 0o700 });
        let expanded = 0;
        for (const [name, data] of Object.entries(entries)) {
          if (name.endsWith("/")) continue;
          if ((expanded += data.length) > 128 * 1024 * 1024)
            throw Error("Adblock extraction limit");
          const file = confined(extension, name);
          fs.mkdirSync(path.dirname(file), { recursive: true });
          fs.writeFileSync(file, data, { flag: "wx", mode: 0o600 });
        }
        const manifest = readJSON(path.join(extension, "manifest.json"));
        if (manifest.manifest_version !== 3)
          throw Error("Unsupported browser extension");
      }
      let browserExecutable: string | undefined;
      if (pack === "browser") {
        browserExecutable = (
          await command(
            process.execPath,
            [
              "-e",
              "process.stdout.write(require('playwright').chromium.executablePath())",
            ],
            root,
            env,
            true,
          )
        ).trim();
        if (
          !inside(
            rejectRedirects(browserExecutable),
            path.join(root, "browsers"),
          )
        )
          throw Error("Browser executable escaped its managed pack");
        fs.accessSync(browserExecutable, fs.constants.X_OK);
      }
      withSyncLock(parent, "optional-pack-pointers", () => {
        atomicJSON(pointer, {
          version: 1,
          root,
          dependencies: PACKS[pack],
          lock: readJSON(path.join(root, "package-lock.json")),
          ...(browserExecutable ? { browserExecutable } : {}),
        });
        committed = true;
      });
      try {
        withSyncLock(parent, "optional-pack-pointers", () =>
          cleanupManagedPacks(parent, pack, root),
        );
      } catch {
        /* Active/uncertain users retain their public runtime until close or later setup. */
      }
      return { status: "installed", pack, account_connected: false };
    } finally {
      withSyncLock(parent, "optional-pack-pointers", () => {
        if (!committed) {
          rejectRedirects(root);
          if (!inside(root, parent))
            throw Error("Invalid managed pack cleanup");
          fs.rmSync(root, { recursive: true, force: true });
        }
        if (exists(installLease)) fs.unlinkSync(installLease);
      });
    }
  });
}
