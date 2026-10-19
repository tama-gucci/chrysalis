import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
const root = fs.realpathSync("/etc/chrysalis/package");
const { defaults, registerWorkspace, saveProfile } = await import(
  pathToFileURL(path.join(root, "src/assistant/profile.ts")).href
);
const { runnerStatus, runIsolated } = await import(
  pathToFileURL(path.join(root, "src/execution/linux.ts")).href
);
assert(!fs.existsSync("/usr/bin/bwrap"));
assert(process.env.CHRYSALIS_EXECUTION_CONFIG?.startsWith("/nix/store/"));
assert(runnerStatus().available, JSON.stringify(runnerStatus()));
const base = fs.mkdtempSync("/var/tmp/chrysalis-runner-");
fs.chmodSync(base, 0o700);
const state = path.join(base, "state"),
  workspace = path.join(base, "workspace");
fs.mkdirSync(workspace);
const profile = defaults();
profile.workspace = registerWorkspace(state, workspace);
profile.features.execution = true;
saveProfile(state, profile);
fs.writeFileSync(path.join(state, "canary"), "private-fixture");
const command =
  "printf synthetic-nixos > result.txt; cat result.txt; " +
  "test ! -e " +
  state +
  "/canary || exit 7; " +
  "test ! -e /run/user/" +
  process.getuid!() +
  "/bus || exit 8; " +
  'node -e \'require("net").createConnection({host:"127.0.0.1",port:80})' +
  '.on("error",e=>{console.log(e.code);process.exit(e.code==="EPERM"?0:9)})\'';
const result = await runIsolated(state, command, { timeout: 10 });
assert.equal(result.exitCode, 0, result.output);
assert.match(result.output, /synthetic-nixos.*EPERM/s);
assert.equal(
  fs.readFileSync(path.join(workspace, "result.txt"), "utf8"),
  "synthetic-nixos",
);
const readonly = await runIsolated(state, "printf blocked > forbidden.txt", {
  readOnly: true,
  timeout: 5,
});
assert.notEqual(readonly.exitCode, 0);
assert(!fs.existsSync(path.join(workspace, "forbidden.txt")));
const controller = new AbortController();
setTimeout(() => controller.abort(), 200);
const stopped = await runIsolated(state, "sleep 20 & wait", {
  signal: controller.signal,
  timeout: 3,
});
assert(stopped.cancelled);
assert(stopped.wallSeconds < 3);
console.log("NixOS native workspace execution passed");
