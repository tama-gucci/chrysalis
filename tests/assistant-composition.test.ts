import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { createAssistantMessageEventStream } from "@earendil-works/pi-ai";
import { memoryStream } from "../extensions/memory-stream.ts";
import { defaults, saveProfile } from "../src/assistant/profile.ts";
import { resetBudget } from "../src/assistant/budgets.ts";
import {
  reserveWriterLease,
  assertWriterLease,
} from "../src/execution/lease.ts";
import { sanitizeSVG, mermaidVisual } from "../src/learning/visuals.ts";
import {
  storeArtifact,
  inspectArtifact,
  prepareArtifactAdoption,
  adoptArtifact,
} from "../src/assistant/artifacts.ts";
import { installLearning } from "../extensions/learning.ts";
import { publicURL } from "../src/research/http.ts";
if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(process.env.TEST_SCRATCH, "composition-" + randomUUID());
fs.mkdirSync(base, { recursive: true });
test("memory reservation covers stream lifetime, caps tokens and reports actual usage", async () => {
  const state = path.join(base, "memory"),
    p = defaults();
  p.features.memory = true;
  p.features.observations = true;
  p.limits.calls = 2;
  p.limits.concurrency = 1;
  p.routes.observer = {
    provider: "openai",
    model: "small",
    thinking: "off",
  };
  saveProfile(state, p);
  const budget = resetBudget(state, 2, 1),
    upstream = createAssistantMessageEventStream();
  let options: any;
  const registry = {
    find: () => model,
    getAvailable: () => [model],
    streamSimple: (_m: any, _c: any, o: any) => {
      options = o;
      return upstream;
    },
  };
  const model = {
    provider: "openai",
    id: "small",
    api: "synthetic",
    maxTokens: 800,
  };
  const out = memoryStream(state, registry, model, {}, { maxTokens: 50000 });
  assert.equal(budget.status().active, 1);
  assert.equal(options.maxTokens, 800);
  assert.throws(() => budget.reserve("specialist"), /running/);
  const msg: any = {
    role: "assistant",
    content: [],
    provider: "openai",
    model: "small",
    api: "synthetic",
    usage: { input: 17, output: 4 },
    stopReason: "stop",
    timestamp: Date.now(),
  };
  upstream.push({ type: "done", reason: "stop", message: msg });
  upstream.end(msg);
  await out.result();
  await new Promise((r) => setImmediate(r));
  assert.equal(budget.status().active, 0);
  assert.deepEqual(budget.status().observations[0].usage, {
    input: 17,
    output: 4,
  });
  assert.throws(
    () => memoryStream(state, registry, { ...model, id: "other" }, {}, {}),
    /route/,
  );
  const abort = new AbortController(),
    stopped = memoryStream(
      state,
      {
        find: () => model,
        getAvailable: () => [model],
        streamSimple: () => createAssistantMessageEventStream(),
      },
      model,
      {},
      { signal: abort.signal },
    );
  abort.abort();
  assert.equal((await stopped.result()).stopReason, "error");
  assert.equal(budget.status().active, 0);
});
test("worker lease blocks parent writes and is released exactly once", () => {
  const state = path.join(base, "lease"),
    task = path.join(base, "task.json"),
    prior = process.env.CHRYSALIS_CHILD_TASK;
  const release = reserveWriterLease(state, task);
  assert.throws(() => assertWriterLease(state), /leased/);
  process.env.CHRYSALIS_CHILD_TASK = task;
  assertWriterLease(state);
  assert.throws(() => reserveWriterLease(state, task), /owns/);
  assert.equal(release(), false);
  assert.equal(release(), false);
  fs.unlinkSync(path.join(state, "assistant/workspace-writer.json"));
  assertWriterLease(state);
  if (prior === undefined) delete process.env.CHRYSALIS_CHILD_TASK;
  else process.env.CHRYSALIS_CHILD_TASK = prior;
});
test("diagrams reject encoded external resources; private artifacts require exact original adoption", async () => {
  for (const svg of [
    '<svg><image href="https://example.com/x"/></svg>',
    '<svg><rect fill="u&#x72;l(https://example.com/x)"/></svg>',
    "<svg><script>bad</script></svg>",
  ])
    assert.throws(() => sanitizeSVG(svg));
  const visual = await mermaidVisual(
    "flowchart LR\n A[Evidence] --> B[Review]\n B --> C[Vault]",
  );
  assert.match(visual.preview, /Evidence/);
  assert.equal(visual.visual_inspected, false);
  const state = path.join(base, "artifacts"),
    vault = path.join(base, "vault");
  fs.mkdirSync(vault);
  fs.writeFileSync(
    path.join(vault, ".chrysalis-vault.json"),
    JSON.stringify({ schema_version: "1", vault_id: "synthetic-vault" }),
  );
  const artifact = storeArtifact(state, "svg", Buffer.from(visual.svg), {
    source: "synthetic",
  });
  const ctx = { state, vault };
  const proposal = prepareArtifactAdoption(ctx, artifact.handle);
  assert.throws(
    () => adoptArtifact(ctx, artifact.handle, "0".repeat(64)),
    /changed/,
  );
  assert(!fs.existsSync(path.join(vault, "Attachments")));
  assert.equal(
    adoptArtifact(ctx, artifact.handle, proposal.digest).records_approved,
    false,
  );
  assert.equal(
    adoptArtifact(ctx, artifact.handle, proposal.digest).records_approved,
    false,
  );
  fs.appendFileSync(
    path.join(state, "assistant/artifacts", artifact.handle + ".svg"),
    "changed",
  );
  assert.throws(() => inspectArtifact(state, artifact.handle), /changed/);
});
test("question labels named Skip or Later are answers, while native controls retain skip/defer", async () => {
  const tools: any[] = [];
  installLearning({
    registerTool: (t: any) => tools.push(t),
    on: () => {},
  } as any);
  const tool = tools.find((t) => t.name === "chrysalis_question"),
    ctx = { hasUI: true, ui: { select: async () => "[1] Skip" } };
  const result = await tool.execute(
    "test",
    {
      questions: [{ question: "Synthetic choice", options: ["Skip", "Later"] }],
    },
    undefined,
    undefined,
    ctx,
  );
  assert.equal(JSON.parse(result.content[0].text)[0].status, "answered");
  ctx.ui.select = async () => "Later";
  const deferred = await tool.execute(
    "test",
    { questions: [{ question: "Synthetic choice", options: ["Skip"] }] },
    undefined,
    undefined,
    ctx,
  );
  assert.equal(JSON.parse(deferred.content[0].text)[0].status, "deferred");
});
test("ordinary browser transport cannot bypass native health/maps/tasks/calendar integrations", () => {
  for (const url of [
    "https://www.fitbit.com/data",
    "https://maps.googleapis.com/maps/api",
    "https://www.google.com/maps/dir",
    "https://www.googleapis.com/calendar/v3",
    "https://tasks.google.com/",
  ])
    assert.throws(() => publicURL(url), /native/);
  assert.equal(
    publicURL("https://developers.google.com/maps/documentation").hostname,
    "developers.google.com",
  );
});

test(
  "parent death never releases a live child lease; native reconciliation verifies child exit",
  { skip: process.platform !== "linux" },
  async () => {
    const { spawn } = await import("node:child_process");
    const { claimWorkerLease, writerLeaseStatus, reconcileWriterLease } =
      await import("../src/execution/lease.ts");
    const { digest } = await import("../src/platforms/filesystem.ts");
    const state = path.join(base, "surviving-child"),
      task = path.join(base, "surviving-task.json"),
      release = reserveWriterLease(state, task);
    const module = new URL("../src/execution/lease.ts", import.meta.url).href;
    const child = spawn(
      process.execPath,
      [
        "--input-type=module",
        "-e",
        `import {claimWorkerLease} from ${JSON.stringify(module)};claimWorkerLease(${JSON.stringify(state)},${JSON.stringify(task)});console.log("ready");setInterval(()=>{},1000);`,
      ],
      { stdio: ["ignore", "pipe", "pipe"] },
    );
    try {
      await new Promise<void>((resolve, reject) => {
        child.stdout.once("data", () => resolve());
        child.once("error", reject);
        child.once("exit", () => reject(Error("Child startup failed")));
      });
      const file = path.join(state, "assistant/workspace-writer.json"),
        record = writerLeaseStatus(state);
      record.pid = 99999999;
      fs.writeFileSync(file, JSON.stringify(record));
      assert.throws(() => assertWriterLease(state), /leased/);
      assert.throws(() => reserveWriterLease(state, task), /owns/);
      assert.throws(() => reconcileWriterLease(state, digest(record)), /alive/);
      const exited = new Promise((r) => child.once("exit", r));
      child.kill("SIGKILL");
      await exited;
      assert.equal(
        reconcileWriterLease(state, digest(record)).child_verified_exited,
        true,
      );
      assertWriterLease(state);
    } finally {
      child.kill("SIGKILL");
      release();
    }
  },
);
