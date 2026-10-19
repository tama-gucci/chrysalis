import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { spawnSync } from "node:child_process";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  defaults,
  saveProfile,
  loadProfile,
  registerWorkspace,
  currentWorkspace,
} from "../src/assistant/profile.ts";
import { UsageBudget } from "../src/assistant/budgets.ts";
import { UIQueue } from "../src/assistant/ui.ts";
import {
  runIsolated,
  runnerStatus,
  syscallPolicy,
} from "../src/execution/linux.ts";

if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(process.env.TEST_SCRATCH, "assistant-" + randomUUID());
fs.mkdirSync(base, { recursive: true });
const state = path.join(base, "state"),
  workspace = path.join(base, "workspace");
fs.mkdirSync(workspace);
test("private settings default disabled, reject injected routes and protected/redirected roots", () => {
  assert.deepEqual(loadProfile(state).features, defaults().features);
  const p = defaults();
  p.routes.worker = { provider: "synthetic", model: "small", thinking: "off" };
  p.workspace = registerWorkspace(state, workspace);
  p.features.execution = true;
  saveProfile(state, p);
  assert.equal(currentWorkspace(state).root, workspace);
  assert.throws(
    () =>
      saveProfile(state, {
        ...p,
        routes: { worker: { ...p.routes.worker, provider: "../secret" } },
      } as any),
    /Invalid/,
  );
  assert.throws(() => registerWorkspace(state, state), /protected/);
  fs.symlinkSync(state, path.join(workspace, "redirect"), "dir");
  assert.throws(() => registerWorkspace(state, workspace), /links/);
  fs.unlinkSync(path.join(workspace, "redirect"));
});
test("call reservation is atomic, bounded and released once; UI cancellation releases the queue", async () => {
  const budget = new UsageBudget(2, 1),
    done = budget.reserve("worker");
  assert.throws(() => budget.reserve("research"), /running/);
  done();
  done();
  assert.equal(budget.status().active, 0);
  const end = budget.reserve("reviewer");
  end({ input: 4, output: 2 });
  assert.throws(() => budget.reserve("worker"), /limit/);
  const q = new UIQueue(),
    results: number[] = [];
  await assert.rejects(
    q.run(async () => {
      throw Error("cancelled");
    }),
  );
  await Promise.all([
    q.run(async () => {
      results.push(1);
    }),
    q.run(async () => {
      results.push(2);
    }),
  ]);
  assert.deepEqual(results, [1, 2]);
});
test(
  "Linux runner writes only workspace, hides state and blocks network/host IPC",
  { skip: process.platform !== "linux" },
  async () => {
    assert(
      runnerStatus().available,
      "Bubblewrap required for execution acceptance",
    );
    assert(syscallPolicy().length > 32);
    fs.writeFileSync(path.join(state, "canary-secret"), "private-canary");
    const r = await runIsolated(
      state,
      "printf synthetic > result.txt; cat result.txt; test ! -e " +
        state +
        '; node -e \'require("net").connect(80,"127.0.0.1").on("error",e=>{console.log(e.code);process.exit(e.code==="EPERM"?0:1)})\'',
      { timeout: 10 },
    );
    assert.equal(r.exitCode, 0, r.output);
    assert.match(r.output, /synthetic.*EPERM/s);
    assert.equal(
      fs.readFileSync(path.join(workspace, "result.txt"), "utf8"),
      "synthetic",
    );
    const win = "/mnt/c/Windows/System32/cmd.exe";
    if (fs.existsSync(win)) {
      fs.copyFileSync(win, path.join(workspace, "cmd.exe"));
      const interop = await runIsolated(
        state,
        "./cmd.exe /c echo interop-escaped",
        { timeout: 5 },
      );
      assert(!interop.output.includes("interop-escaped"));
      assert.notEqual(interop.exitCode, 0);
    }
    const readonly = await runIsolated(state, "printf bad > denied.txt", {
      readOnly: true,
      timeout: 5,
    });
    assert.notEqual(readonly.exitCode, 0);
    assert(!fs.existsSync(path.join(workspace, "denied.txt")));
  },
);
test(
  "runner cancellation kills descendants and bounded output reports truncation",
  { skip: process.platform !== "linux" },
  async () => {
    const c = new AbortController(),
      marker = "chrysalis-desc-" + randomUUID();
    const pending = runIsolated(
      state,
      "node -e '" +
        'process.title="' +
        marker +
        '";setInterval(()=>{},1000)' +
        "' & wait",
      { signal: c.signal, timeout: 10 },
    );
    const alive = () =>
      spawnSync("pgrep", ["-f", "^" + marker + "$"], { encoding: "utf8" })
        .status === 0;
    for (let i = 0; i < 300 && !alive(); i++)
      await new Promise((r) => setTimeout(r, 10));
    assert(alive(), "the sandbox descendant actually started");
    const cancelledAt = Date.now();
    c.abort();
    const stopped = await pending;
    assert(stopped.cancelled);
    assert(Date.now() - cancelledAt < 3000);
    for (let i = 0; i < 100 && alive(); i++)
      await new Promise((r) => setTimeout(r, 10));
    assert(!alive(), "no descendant survives cancellation");
    const r = await runIsolated(state, "head -c 90000 /dev/zero", {
      timeout: 3,
    });
    assert(r.truncated);
    assert.equal(Buffer.byteLength(r.output), 65536);
  },
);
test(
  "pre-existing and post-snapshot hardlinks preserve protected inodes; command input bypasses no shell quoting",
  { skip: process.platform !== "linux" },
  async () => {
    const secret = path.join(state, "protected-inode");
    fs.writeFileSync(secret, "original");
    fs.linkSync(secret, path.join(workspace, "late-link"));
    await assert.rejects(
      runIsolated(state, "printf changed > late-link"),
      /links/,
    );
    assert.equal(fs.readFileSync(secret, "utf8"), "original");
    fs.unlinkSync(path.join(workspace, "late-link"));
    const late = runIsolated(state, "sleep 0.3; printf changed > late-link");
    fs.linkSync(secret, path.join(workspace, "late-link"));
    await assert.rejects(late, /conflict/);
    assert.equal(fs.readFileSync(secret, "utf8"), "original");
    fs.unlinkSync(path.join(workspace, "late-link"));
    const content = "literal-$(false)-`false`-" + "x".repeat(200000);
    const r = await runIsolated(
      state,
      'node -e \'require("fs").writeFileSync("stdin.txt",require("fs").readFileSync(0))\'',
      { input: content },
    );
    assert.equal(r.exitCode, 0, r.output);
    assert.equal(
      fs.readFileSync(path.join(workspace, "stdin.txt"), "utf8"),
      content,
    );
  },
);
