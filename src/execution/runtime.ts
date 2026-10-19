import fs from "node:fs";
import { readJSON } from "../platforms/filesystem.ts";
export interface ExecutionRuntime {
  bwrap: string;
  systemdRun: string;
  systemctl: string;
  node: string;
  usr: string;
  storePaths: string[];
}
function immutableStorePath(value: unknown, directory = false): string {
  if (
    typeof value !== "string" ||
    value.length > 4096 ||
    !/^\/nix\/store\/[a-z0-9]{32}-[^/\x00-\x20]+(?:\/[^\x00-\x20]*)?$/.test(
      value,
    )
  )
    throw Error("Execution runtime requires immutable Nix store paths");
  const resolved = fs.realpathSync(value);
  if (!resolved.startsWith("/nix/store/"))
    throw Error("Runtime path escaped the Nix store");
  const stat = fs.statSync(resolved);
  if (
    stat.uid !== 0 ||
    stat.mode & 0o022 ||
    (directory ? !stat.isDirectory() : !stat.isFile())
  )
    throw Error("Execution runtime path is not managed by root");
  return resolved;
}
export function executionRuntime(): ExecutionRuntime {
  const file = process.env.CHRYSALIS_EXECUTION_CONFIG;
  if (!file)
    return {
      bwrap: "/usr/bin/bwrap",
      systemdRun: "/usr/bin/systemd-run",
      systemctl: "/usr/bin/systemctl",
      node: fs.realpathSync(process.execPath),
      usr: "/usr",
      storePaths: [],
    };
  const config = readJSON(immutableStorePath(file));
  if (config.version !== 1 || config.arch !== process.arch)
    throw Error("Execution runtime architecture or version changed");
  const list = immutableStorePath(config.storePaths);
  if (fs.statSync(list).size > 2 * 1024 * 1024)
    throw Error("Runtime closure limit");
  const storePaths = fs.readFileSync(list, "utf8").trim().split("\n");
  if (
    storePaths.length > 8192 ||
    storePaths.some(
      (p) => !/^\/nix\/store\/[a-z0-9]{32}-[^/\x00-\x20]+$/.test(p),
    )
  )
    throw Error("Invalid immutable runtime closure");
  for (const p of storePaths) {
    const stat = fs.statSync(p);
    if (stat.uid !== 0 || stat.mode & 0o022)
      throw Error("Runtime closure is writable");
  }
  return {
    bwrap: immutableStorePath(config.bwrap),
    systemdRun: immutableStorePath(config.systemdRun),
    systemctl: immutableStorePath(config.systemctl),
    node: immutableStorePath(config.node),
    usr: immutableStorePath(config.usr, true),
    storePaths,
  };
}
export function runtimeBindings(runtime: ExecutionRuntime): string[] {
  return [
    "--ro-bind",
    runtime.usr,
    "/usr",
    "--symlink",
    "usr/bin",
    "/bin",
    "--symlink",
    "usr/lib",
    "/lib",
    "--symlink",
    "usr/lib64",
    "/lib64",
    ...runtime.storePaths.flatMap((p) => ["--ro-bind", p, p]),
  ];
}
