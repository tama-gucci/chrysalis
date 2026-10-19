import test from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import fs from "node:fs";
import { randomUUID } from "node:crypto";
import {
  DefaultResourceLoader,
  SettingsManager,
  SessionManager,
  createAgentSession,
} from "@earendil-works/pi-coding-agent";
import { prepareEngine } from "../extensions/specialists.ts";
import {
  defaults,
  saveProfile,
  registerWorkspace,
} from "../src/assistant/profile.ts";
import {
  atomicJSON,
  digest,
  sha256,
  raw,
  PACKAGE_ROOT,
} from "../src/platforms/filesystem.ts";
if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
test("actual child SDK loads external completion dependencies and enforces fixed role tools without model calls", async () => {
  const base = path.join(process.env.TEST_SCRATCH!, "child-" + randomUUID()),
    state = path.join(base, "state"),
    workspace = path.join(base, "workspace"),
    cwd = path.join(state, "assistant/tasks", randomUUID()),
    agentDir = path.join(base, "agent");
  for (const dir of [workspace, cwd, agentDir])
    fs.mkdirSync(dir, { recursive: true });
  const p = defaults();
  p.workspace = registerWorkspace(state, workspace);
  p.features.execution = true;
  p.routes.reviewer = {
    provider: "openai",
    model: "fixture",
    thinking: "off",
  };
  saveProfile(state, p);
  const prepared = prepareEngine(state),
    task = path.join(cwd, "task.json"),
    prior = {
      state: process.env.CHRYSALIS_STATE_ROOT,
      task: process.env.CHRYSALIS_CHILD_TASK,
    };
  atomicJSON(task, {
    version: 1,
    role: "reviewer",
    turns: 2,
    profileDigest: digest(p),
    route: p.routes.reviewer,
    doneExtension: prepared.done,
    doneSha256: sha256(raw(prepared.done)),
  });
  process.env.CHRYSALIS_STATE_ROOT = state;
  process.env.CHRYSALIS_CHILD_TASK = task;
  try {
    const settings = SettingsManager.inMemory({ packages: [] }),
      loader = new DefaultResourceLoader({
        cwd,
        agentDir,
        settingsManager: settings,
        noContextFiles: true,
        noSkills: true,
        noExtensions: true,
        additionalExtensionPaths: [
          path.join(PACKAGE_ROOT, "extensions/child.ts"),
          prepared.done,
        ],
      });
    await loader.reload();
    assert.deepEqual(loader.getExtensions().errors, []);
    const { session } = await createAgentSession({
      cwd,
      agentDir,
      resourceLoader: loader,
      settingsManager: settings,
      sessionManager: SessionManager.inMemory(cwd),
      tools: ["read", "bash", "subagent_done", "caller_ping"],
    });
    try {
      const errors: any[] = [];
      await session.bindExtensions({ onError: (e) => errors.push(e) });
      assert.deepEqual(errors, []);
      const tools = session.getActiveToolNames();
      assert(tools.includes("subagent_done"), JSON.stringify(tools));
      assert(tools.includes("read"));
      assert(!tools.includes("write"));
      assert(!tools.includes("chrysalis_operation"));
      assert(!tools.includes("chrysalis_specialist"));
    } finally {
      session.dispose();
    }
  } finally {
    for (const [key, value] of [
      ["CHRYSALIS_STATE_ROOT", prior.state],
      ["CHRYSALIS_CHILD_TASK", prior.task],
    ])
      if (value === undefined) delete process.env[key!];
      else process.env[key!] = value;
  }
});

test("programmatic child host refuses a broken required extension before any model session starts", async () => {
  const { spawnSync } = await import("node:child_process"),
    { createRequire } = await import("node:module"),
    require = createRequire(import.meta.url);
  const base = path.join(
      process.env.TEST_SCRATCH!,
      "child-fatal-" + randomUUID(),
    ),
    state = path.join(base, "state"),
    cwd = path.join(state, "assistant/tasks", randomUUID()),
    agentDir = path.join(base, "agent");
  fs.mkdirSync(cwd, { recursive: true });
  fs.mkdirSync(agentDir);
  const profile = defaults();
  saveProfile(state, profile);
  const done = path.join(base, "broken.ts");
  fs.writeFileSync(done, "export default function { invalid syntax");
  const task = path.join(cwd, "task.json");
  atomicJSON(task, {
    version: 1,
    role: "reviewer",
    turns: 1,
    brief: "This must never reach a model",
    profileDigest: digest(profile),
    route: { provider: "openai", model: "unavailable", thinking: "off" },
    doneExtension: done,
    doneSha256: sha256(raw(done)),
    childSha256: sha256(raw(path.join(PACKAGE_ROOT, "extensions/child.ts"))),
  });
  const r = spawnSync(
    process.execPath,
    [
      "--import",
      require.resolve("tsx/esm"),
      path.join(PACKAGE_ROOT, "extensions/child-host.mjs"),
    ],
    {
      env: {
        ...process.env,
        CHRYSALIS_STATE_ROOT: state,
        CHRYSALIS_CHILD_TASK: task,
        PI_CODING_AGENT_DIR: agentDir,
        PI_SUBAGENT_SESSION: path.join(base, "subagent-sessions/session.jsonl"),
      },
      encoding: "utf8",
      timeout: 15000,
    },
  );
  assert.notEqual(r.status, 0);
  assert.match(
    r.stderr,
    /Required child extensions failed to load; no model started/,
  );
  assert(!fs.existsSync(path.join(base, "subagent-sessions/session.jsonl")));
});
