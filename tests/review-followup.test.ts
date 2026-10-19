import test from "node:test";
import { installAssistantControls } from "../extensions/controls.ts";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { spawnSync } from "node:child_process";
import { BrowserSecretGuard } from "../src/research/secret-guard.ts";
import { analyzeYouTube } from "../src/research/gemini-web.ts";
import { UsageBudget } from "../src/assistant/budgets.ts";
import { defaults, validateProfile } from "../src/assistant/profile.ts";
import { sanitizeSVG } from "../src/learning/visuals.ts";
import { specialistUsage } from "../extensions/specialist-usage.ts";
import {
  snapshotWorkspace,
  mergeWorkspace,
} from "../src/execution/workspace.ts";
import { PACKAGE_ROOT } from "../src/platforms/filesystem.ts";

test("URL redaction decodes fully escaped and lowercase hex path secrets", () => {
  const guard = new BrowserSecretGuard(),
    secret = "cookie/Secret+42";
  guard.configure([secret]);
  const escaped = [...Buffer.from(secret)]
    .map((b) => "%" + b.toString(16).padStart(2, "0"))
    .join("");
  for (const input of [
    "https://example.com/" + escaped,
    "https://example.com/" + encodeURIComponent(secret),
  ])
    assert(!guard.url(input).includes("Secret"));
  assert.equal(guard.url("https://example.com/" + escaped), "");
  assert.equal(
    guard.url("https://example.com/a%3Fb%23c%2Fd"),
    "https://example.com/a%3Fb%23c%2Fd",
  );
  assert.equal(guard.url("https://example.com/%xx"), "");
  assert.throws(
    () => guard.configure(["a".repeat(65537)]),
    /redaction unavailable/,
  );
  assert.throws(() => guard.text("unrelated"), /automation refused/);
});
test("pre-cancelled YouTube analysis touches neither cookies nor transport", async () => {
  let cookies = 0,
    requests = 0;
  const controller = new AbortController();
  controller.abort();
  const result = await analyzeYouTube(
    "https://youtu.be/abcdefghijk",
    "Synthetic question",
    {
      cookies: async () => {
        cookies++;
        return {};
      },
      query: async () => {
        requests++;
        return "";
      },
    },
    controller.signal,
  );
  assert.equal(result.status, "unavailable");
  assert.equal(result.reason, "cancelled");
  assert.equal(cookies, 0);
  assert.equal(requests, 0);
});
test("usage budgets reject nonfinite limits and snapshots cannot mutate accounting", () => {
  for (const invalid of [NaN, Infinity, -1, 0, 1.5])
    assert.throws(() => new UsageBudget(invalid, 1), /Invalid/);
  const budget = new UsageBudget(4, 1);
  budget.reserve("fixture")({ input: 1 });
  (budget.status().observations[0].usage as any).input = 999;
  assert.equal(budget.status().observations[0].usage.input, 1);
  for (const field of ["features", "routes"])
    for (const invalid of [[], "invalid", null]) {
      const profile: any = defaults();
      profile[field] = invalid;
      assert.throws(() => validateProfile(profile));
    }
});
test("inert SVG labels accept code-like text while executable attributes remain refused", () => {
  const safe = "<svg><text>style=literal url(example) C:\\folder</text></svg>";
  assert.equal(sanitizeSVG(safe), safe);
  for (const svg of [
    '<svg style="x"></svg>',
    '<svg><text onclick="x">x</text></svg>',
    '<svg><image href="https://example.com"/></svg>',
    "<svg><text><broken</text></svg>",
  ])
    assert.throws(() => sanitizeSVG(svg));
});
test("usage accounting streams valid sessions beyond the former four MiB cap", () => {
  assert(process.env.TEST_SCRATCH);
  const file = path.join(
    process.env.TEST_SCRATCH,
    "usage-" + randomUUID() + ".jsonl",
  );
  const entry = JSON.stringify({
    type: "message",
    message: { role: "user", content: "x".repeat(1024) },
  });
  fs.writeFileSync(file, (entry + "\n").repeat(5000));
  fs.appendFileSync(
    file,
    JSON.stringify({
      type: "message",
      message: {
        role: "assistant",
        usage: {
          input: 3,
          output: 2,
          cacheRead: 0,
          cacheWrite: 0,
          totalTokens: 5,
        },
      },
    }) + "\n",
  );
  assert(fs.statSync(file).size > 4 * 1024 * 1024);
  assert.equal(specialistUsage(file)?.totalTokens, 5);
});
test("managed dependency preload resolves a real CommonJS require from an external root", () => {
  assert(process.env.TEST_SCRATCH);
  const root = path.join(process.env.TEST_SCRATCH, "cjs-" + randomUUID()),
    deps = path.join(root, "dependencies"),
    module = path.join(deps, "node_modules/synthetic-only-cjs");
  fs.mkdirSync(module, { recursive: true });
  fs.writeFileSync(path.join(deps, "package.json"), "{}");
  fs.writeFileSync(
    path.join(module, "package.json"),
    JSON.stringify({ name: "synthetic-only-cjs", main: "index.cjs" }),
  );
  fs.writeFileSync(
    path.join(module, "index.cjs"),
    "module.exports = 'external-cjs-ok';",
  );
  const caller = path.join(root, "caller.cjs");
  fs.writeFileSync(
    caller,
    "process.stdout.write(require('synthetic-only-cjs'));",
  );
  const result = spawnSync(
    process.execPath,
    [
      "--import",
      path.join(PACKAGE_ROOT, "src/platforms/dependencies.mjs"),
      caller,
    ],
    {
      encoding: "utf8",
      env: {
        ...process.env,
        CHRYSALIS_DEPENDENCIES_ROOT: deps,
        CHRYSALIS_PI_ROOT: "",
      },
    },
  );
  assert.equal(result.status, 0, result.stderr);
  assert.equal(result.stdout, "external-cjs-ok");
});

test(
  "workspace deletion safely merges across filesystem boundaries",
  {
    skip: process.platform !== "linux" || !fs.existsSync("/dev/shm"),
  },
  () => {
    assert(process.env.TEST_SCRATCH);
    const root = fs.mkdtempSync("/dev/shm/chrysalis-delete-");
    const privateRoot = path.join(
      process.env.TEST_SCRATCH,
      "cross-device-" + randomUUID(),
    );
    try {
      fs.mkdirSync(privateRoot);
      if (fs.statSync(root).dev === fs.statSync(privateRoot).dev) return;
      fs.writeFileSync(path.join(root, "remove.txt"), "Reviewed original");
      const image = snapshotWorkspace(root, privateRoot);
      fs.unlinkSync(path.join(image.directory, "remove.txt"));
      mergeWorkspace(root, image);
      assert(!fs.existsSync(path.join(root, "remove.txt")));
      assert(
        !fs.readdirSync(root).some((n) => n.startsWith(".chrysalis-removed-")),
      );
    } finally {
      fs.rmSync(root, { recursive: true, force: true });
    }
  },
);

test("recovery listing keeps valid workspace details and unreadable receipt handles", async () => {
  assert(process.env.TEST_SCRATCH);
  const previous = process.env.CHRYSALIS_STATE_ROOT,
    state = path.join(
      process.env.TEST_SCRATCH,
      "recovery-list-" + randomUUID(),
    ),
    root = path.join(state, "assistant/runner");
  fs.mkdirSync(root, { recursive: true });
  process.env.CHRYSALIS_STATE_ROOT = state;
  const ids = [
    "00000000-0000-4000-8000-000000000001",
    "00000000-0000-4000-8000-000000000002",
    "00000000-0000-4000-8000-000000000003",
  ];
  fs.writeFileSync(path.join(root, ids[0] + ".conflict.json"), "invalid");
  fs.writeFileSync(
    path.join(root, ids[1] + ".conflict.json"),
    "x".repeat(5 * 1024 * 1024),
  );
  fs.writeFileSync(
    path.join(root, ids[2] + ".conflict.json"),
    JSON.stringify({
      workspace: { root: "/synthetic/workspace", id: "synthetic" },
      candidate: "/synthetic/candidate",
      revisions: { "changed.txt": "a".repeat(64) },
    }),
  );
  let shown: any;
  try {
    await installAssistantControls({} as any)("recovery", [], {
      hasUI: true,
      ui: {
        notify(value: string) {
          shown = JSON.parse(value);
        },
      },
    } as any);
    assert.equal(shown.total, 3);
    assert.equal(shown.conflicts.length, 3);
    assert.equal(shown.conflicts[2].workspace, "/synthetic/workspace");
    assert.equal(shown.conflicts[2].revision_count, 1);
    assert(shown.conflicts[0].metadata.includes("unavailable"));
    assert(shown.conflicts[1].metadata.includes("unavailable"));
    assert.equal(shown.next_offset, null);
  } finally {
    if (previous === undefined) delete process.env.CHRYSALIS_STATE_ROOT;
    else process.env.CHRYSALIS_STATE_ROOT = previous;
  }
});
