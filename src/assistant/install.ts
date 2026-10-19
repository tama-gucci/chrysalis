import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { randomUUID } from "node:crypto";
import os from "node:os";
import { assistantRoot } from "./profile.ts";
import {
  atomicJSON,
  readJSON,
  exists,
  rejectRedirects,
  PACKAGE_ROOT,
  sha256,
  confined,
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
    !path.isAbsolute(entry.root)
  )
    throw Error("Optional pack identity changed");
  rejectRedirects(entry.root);
  const manifest = readJSON(path.join(entry.root, "package.json"));
  if (JSON.stringify(manifest.dependencies) !== JSON.stringify(PACKS[pack]))
    throw Error("Optional pack manifest drift");
  return entry.root as string;
}
async function command(
  program: string,
  args: string[],
  cwd: string,
  env: NodeJS.ProcessEnv,
) {
  await new Promise<void>((resolve, reject) => {
    const child = spawn(program, args, { cwd, env, stdio: "ignore" });
    const timer = setTimeout(() => {
      child.kill("SIGKILL");
      reject(Error("Optional install timed out"));
    }, 180000);
    child.on("error", () => {
      clearTimeout(timer);
      reject(Error("Optional installer unavailable"));
    });
    child.on("exit", (code) => {
      clearTimeout(timer);
      code === 0
        ? resolve()
        : reject(
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
  const root = path.join(parent, pack + "-" + randomUUID());
  fs.mkdirSync(root, { mode: 0o700 });
  atomicJSON(path.join(root, "package.json"), {
    private: true,
    type: "module",
    dependencies: PACKS[pack],
  });
  const env = {
    PATH: path.dirname(process.execPath) + ":/usr/bin:/bin",
    HOME: root,
    npm_config_cache: path.join(parent, "npm-cache"),
    PLAYWRIGHT_BROWSERS_PATH: path.join(os.homedir(), ".cache/ms-playwright"),
    npm_config_ignore_scripts: "true",
    npm_config_audit: "false",
  };
  await command(
    "npm",
    ["install", "--ignore-scripts", "--legacy-peer-deps", "--omit=dev"],
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
  atomicJSON(path.join(parent, pack + ".json"), {
    version: 1,
    root,
    dependencies: PACKS[pack],
    lock: readJSON(path.join(root, "package-lock.json")),
  });
  return { status: "installed", pack, account_connected: false };
}
