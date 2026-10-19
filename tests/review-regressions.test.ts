import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { spawnSync } from "node:child_process";
import { pathToFileURL } from "node:url";
import path from "node:path";
import { randomUUID, createHash } from "node:crypto";
import { ManagedBrowser } from "../src/research/playwright.ts";
import { BrowserSecretGuard } from "../src/research/secret-guard.ts";
import { publicURL, publicRequest } from "../src/research/http.ts";
import { analyzeYouTube } from "../src/research/gemini-web.ts";
import {
  isPasswordExport,
  parsePasswordExport,
} from "../src/passwords/import.ts";
import {
  defaults,
  saveProfile,
  registerWorkspace,
  validateProfile,
} from "../src/assistant/profile.ts";
import { sharedBudget } from "../src/assistant/budgets.ts";
import { snapshotWorkspace } from "../src/execution/workspace.ts";
import {
  reserveWriterLease,
  writerLeaseStatus,
} from "../src/execution/lease.ts";
import {
  prepareOnboarding,
  approveSetup,
  applySetup,
  loadSetup,
} from "../src/app/onboarding.ts";
import {
  quarantineReviewedFile,
  withSyncLock,
  PACKAGE_ROOT,
} from "../src/platforms/filesystem.ts";
import { storeArtifact } from "../src/assistant/artifacts.ts";
import { retentionPlan, applyRetention } from "../src/assistant/retention.ts";
import { packRoot, acquirePack } from "../src/assistant/install.ts";
import { installLearning } from "../extensions/learning.ts";
import { installResearch } from "../extensions/research.ts";
import {
  approveSystem,
  requireSystemScope,
  currentOperation,
  recordSystem,
  beginPrivileged,
  systemRoot,
} from "../src/system/state.ts";
if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(process.env.TEST_SCRATCH, "review-" + randomUUID());
fs.mkdirSync(base, { recursive: true });
const directory = (name: string) => {
  const p = path.join(base, name);
  fs.mkdirSync(p, { recursive: true });
  return p;
};
test("redaction cannot emit a password inside its replacement marker", () => {
  for (const password of ["private", "[", "pri", "ate"]) {
    const guard = new BrowserSecretGuard();
    guard.configure([password]);
    assert(!guard.text(password + " outside").includes(password));
  }
});
test("trailing-dot protected hosts stay protected and IPv6 literals reach address validation", async () => {
  for (const host of [
    "maps.google.com.",
    "calendar.google.com.",
    "localhost.",
    "a.local.",
  ])
    assert.throws(() => publicURL("https://" + host + "/"));
  assert.equal(publicURL("https://example.com./").hostname, "example.com");
  await assert.rejects(publicRequest("https://[::1]/"), /Private destination/);
});
test("Gemini redacts short and encoded cookies and cookie failures remain structured", async () => {
  const value = "x y";
  const result = await analyzeYouTube(
    "https://youtu.be/abcdefghijk",
    "Synthetic",
    {
      cookies: async () => ({ "__Secure-1PSID": value }),
      query: async () =>
        [
          value,
          encodeURIComponent(value),
          Buffer.from(value).toString("base64"),
        ].join(" | "),
    },
  );
  assert.equal(result.status, "ok");
  for (const v of [
    value,
    encodeURIComponent(value),
    Buffer.from(value).toString("base64"),
  ])
    assert(!result.answer?.includes(v));
  const failed = await analyzeYouTube(
    "https://youtu.be/abcdefghijk",
    "Synthetic",
    {
      cookies: async () => {
        throw Error("fixture cookie failure");
      },
      query: async () => {
        throw Error("must not query");
      },
    },
  );
  assert.equal(failed.status, "unavailable");
});
test("truncated credential exports stay excluded and opaque source IDs stay distinct", () => {
  assert(
    isPasswordExport(
      Buffer.from('[{"username":"fixture","password":"fixture"'),
    ),
  );
  assert(!isPasswordExport(Buffer.from('{"ordinary":')));
  const records = parsePasswordExport(
    Buffer.from(
      JSON.stringify([
        {
          externalId: "item_1",
          username: "same",
          password: "fixture",
          url: "https://example.com",
        },
        {
          externalId: "item_2",
          username: "same",
          password: "fixture",
          url: "https://example.com",
        },
      ]),
    ),
  ).records;
  assert.deepEqual(
    records.map((r) => r.source.externalId),
    ["item_1", "item_2"],
  );
});
test("workspace copies exclude credential filenames and SSH variants", () => {
  const root = directory("filtered-project"),
    scratch = directory("filtered-private");
  for (const name of [
    ".npmrc",
    ".netrc",
    ".git-credentials",
    "id_ecdsa",
    "id_dsa",
    "id_ed25519_sk",
  ])
    fs.writeFileSync(path.join(root, name), "synthetic-only");
  fs.mkdirSync(path.join(root, ".docker"));
  fs.writeFileSync(path.join(root, ".docker/config.json"), "{}");
  fs.writeFileSync(path.join(root, "allowed.txt"), "public");
  const image = snapshotWorkspace(root, scratch);
  assert.deepEqual(Object.keys(image.revisions), ["allowed.txt"]);
});
test("resumed approved setup rechecks the current execution workspace", async () => {
  const state = path.join(base, "setup-state"),
    vault = directory("setup-vault");
  const plan = prepareOnboarding({ vault, state, timezone: "Etc/UTC" });
  approveSetup(state, plan.proposal_digest, "synthetic native approval");
  const profile = defaults();
  profile.workspace = registerWorkspace(state, vault);
  saveProfile(state, profile);
  assert.throws(() => loadSetup(state, plan.proposal_digest), /disjoint/);
  await assert.rejects(applySetup(state, plan.proposal_digest), /disjoint/);
  assert.equal(fs.readdirSync(vault).length, 0);
});
test("budget changes wait for active work; profile identities require strings", () => {
  const state = path.join(base, "budgets"),
    first = sharedBudget(state, 5, 1),
    done = first.reserve("fixture");
  assert.throws(() => sharedBudget(state, 10, 2), /Wait/);
  done();
  assert.equal(sharedBudget(state, 10, 2).status().callLimit, 10);
  const p: any = defaults();
  p.routes.worker = { provider: 123, model: "fixture", thinking: "off" };
  assert.throws(() => validateProfile(p), /route/);
  delete p.routes.worker;
  p.workspace = { id: 123456789, root: base, dev: 1, ino: 1 };
  assert.throws(() => validateProfile(p), /identity/);
});
test("lease transitions are serialized and a stale release cannot delete a later reservation", () => {
  const state = directory("lease"),
    task = path.join(base, "task.json");
  const old = reserveWriterLease(state, task);
  assert.equal(old(), false);
  assert.equal(old(true), true);
  const current = reserveWriterLease(state, task);
  assert.equal(old(true), true);
  assert(writerLeaseStatus(state));
  withSyncLock(
    path.join(state, "assistant"),
    "workspace-writer-transition",
    () => {
      assert.throws(() => current(true), /writer_busy/);
    },
  );
  assert.equal(current(true), true);
  assert.equal(writerLeaseStatus(state), null);
});
test("removal races preserve the changed inode rather than unlinking new bytes", () => {
  const file = path.join(directory("removal"), "source.txt"),
    recovery = path.join(base, "removed.txt");
  fs.writeFileSync(file, "before");
  const expected = createHash("sha256").update("before").digest("hex");
  const rename = fs.renameSync;
  fs.renameSync = ((from: any, to: any) => {
    if (from === file) fs.writeFileSync(file, "concurrent");
    return rename(from, to);
  }) as any;
  try {
    assert.throws(
      () => quarantineReviewedFile(file, expected, recovery),
      /changed/,
    );
  } finally {
    fs.renameSync = rename;
  }
  assert.equal(fs.readFileSync(file, "utf8"), "concurrent");
});
test("retention refuses touched identical bytes before deleting any reviewed files", () => {
  const state = directory("retention"),
    artifact = storeArtifact(state, "mermaid", Buffer.from("graph TD; A-->B"));
  const root = path.join(state, "assistant/artifacts"),
    old = new Date(Date.now() - 40 * 86400000);
  for (const name of fs.readdirSync(root))
    fs.utimesSync(path.join(root, name), old, old);
  const plan = retentionPlan(state);
  assert(plan.records.length >= 2);
  const file = path.join(root, artifact.handle + ".mermaid");
  fs.utimesSync(file, new Date(), new Date());
  assert.throws(() => applyRetention(state, plan, plan.digest), /changed/);
  assert(fs.existsSync(file));
  assert.equal(fs.readdirSync(root).length, 2);
});
test("optional pack pointers cannot select arbitrary host code", () => {
  const state = directory("pack"),
    root = directory("outside-pack");
  fs.mkdirSync(path.join(state, "assistant/packs"), { recursive: true });
  fs.writeFileSync(
    path.join(state, "assistant/packs/browser.json"),
    JSON.stringify({
      version: 1,
      root,
      dependencies: { playwright: "1.64.0" },
    }),
  );
  assert.throws(() => packRoot(state, "browser"), /identity/);
});
test("lesson capture stores selected native-approved text, without ambient conversation", async () => {
  const state = path.join(base, "lesson-native"),
    prior = process.env.CHRYSALIS_STATE_ROOT;
  process.env.CHRYSALIS_STATE_ROOT = state;
  try {
    const p = defaults();
    p.features.lessonCapture = true;
    saveProfile(state, p);
    const tools = new Map<string, any>(),
      events = new Map<string, any>();
    installLearning({
      registerTool: (t: any) => tools.set(t.name, t),
      on: (n: string, f: any) => events.set(n, f),
    } as any);
    assert(!events.has("message_end"));
    const lesson = tools.get("chrysalis_lesson");
    const ctx = { hasUI: true, ui: { confirm: async () => true } };
    await lesson.execute(
      "start",
      { action: "begin", topic: "Synthetic" },
      undefined,
      undefined,
      ctx,
    );
    await assert.rejects(
      lesson.execute(
        "decline",
        { action: "capture", text: "declined" },
        undefined,
        undefined,
        { hasUI: true, ui: { confirm: async () => false } },
      ),
      /declined/,
    );
    await lesson.execute(
      "capture",
      { action: "capture", text: "selected recap" },
      undefined,
      undefined,
      ctx,
    );
    await lesson.execute(
      "finish",
      { action: "finish" },
      undefined,
      undefined,
      ctx,
    );
    const files = fs.readdirSync(path.join(state, "assistant/lessons"));
    const text = fs.readFileSync(
      path.join(state, "assistant/lessons", files[0]),
      "utf8",
    );
    assert(text.includes("selected recap"));
    assert(!text.includes("declined"));
  } finally {
    if (prior === undefined) delete process.env.CHRYSALIS_STATE_ROOT;
    else process.env.CHRYSALIS_STATE_ROOT = prior;
  }
});
test("screenshots require native consent before opening a managed profile", async () => {
  const state = path.join(base, "screenshot"),
    prior = process.env.CHRYSALIS_STATE_ROOT;
  process.env.CHRYSALIS_STATE_ROOT = state;
  try {
    const p = defaults();
    p.features.browser = true;
    saveProfile(state, p);
    const tools = new Map<string, any>();
    installResearch({
      registerTool: (t: any) => tools.set(t.name, t),
      on: () => {},
      registerCommand: () => {},
    } as any);
    await assert.rejects(
      tools
        .get("chrysalis_browser")
        .execute("fixture", { action: "screenshot" }, undefined, undefined, {
          hasUI: false,
        }),
      /permission declined/,
    );
  } finally {
    if (prior === undefined) delete process.env.CHRYSALIS_STATE_ROOT;
    else process.env.CHRYSALIS_STATE_ROOT = prior;
  }
});
test("system approvals keep one pending outcome and reject a replaced vault marker", async () => {
  const state = path.join(base, "system-state"),
    vault = directory("system-vault");
  const setup = prepareOnboarding({ vault, state, timezone: "Etc/UTC" });
  approveSetup(state, setup.proposal_digest, "synthetic");
  await applySetup(state, setup.proposal_digest);
  const c: any = {
    version: 1,
    mode: "installed",
    host: "fixture",
    configuration: directory("configuration"),
    state,
    source: PACKAGE_ROOT,
    timeZone: "Etc/UTC",
    commands: Object.fromEntries(
      [
        "nix",
        "sudo",
        "disko",
        "lsblk",
        "findmnt",
        "facter",
        "mkpasswd",
        "nixAgent",
        "node",
      ].map((n) => [n, "/bin/true"]),
    ),
  };
  const op = approveSystem(c, "Synthetic outcome", "fixture", undefined, vault);
  assert.throws(
    () => approveSystem(c, "Another outcome", "fixture"),
    /pending/,
  );
  assert.equal(currentOperation(c)?.id, op.id);
  const marker = path.join(vault, ".chrysalis-vault.json"),
    data = JSON.parse(fs.readFileSync(marker, "utf8"));
  fs.writeFileSync(marker, JSON.stringify({ ...data, vault_id: randomUUID() }));
  assert.throws(() => requireSystemScope(c), /identity changed/);
});

test("retired optional packs remain until their final active user releases them", () => {
  const state = directory("pack-users"),
    parent = path.join(state, "assistant/packs");
  fs.mkdirSync(parent, { recursive: true });
  const lock = JSON.parse(
    fs.readFileSync(
      path.join(
        PACKAGE_ROOT,
        "resources/optional-packs/media/package-lock.json",
      ),
      "utf8",
    ),
  );
  const make = () => {
    const root = path.join(parent, "media-" + randomUUID());
    fs.mkdirSync(root);
    fs.writeFileSync(
      path.join(root, "package.json"),
      JSON.stringify({ dependencies: { "pi-web-access": "0.38.0" } }),
    );
    fs.writeFileSync(
      path.join(root, "package-lock.json"),
      JSON.stringify(lock),
    );
    fs.writeFileSync(
      path.join(parent, "media.json"),
      JSON.stringify({
        version: 1,
        root,
        dependencies: { "pi-web-access": "0.38.0" },
        lock,
      }),
    );
    return root;
  };
  const old = make(),
    a = acquirePack(state, "media"),
    b = acquirePack(state, "media");
  const next = make();
  a.release();
  assert(fs.existsSync(old));
  b.release();
  assert(!fs.existsSync(old));
  assert(fs.existsSync(next));
});
test("another process cannot start an old system receipt during replacement approval", async () => {
  const c: any = {
    version: 1,
    mode: "installed",
    host: "fixture",
    configuration: directory("race-config"),
    state: directory("race-state"),
    source: PACKAGE_ROOT,
    timeZone: "Etc/UTC",
    commands: Object.fromEntries(
      [
        "nix",
        "sudo",
        "disko",
        "lsblk",
        "findmnt",
        "facter",
        "mkpasswd",
        "nixAgent",
        "node",
      ].map((n) => [n, "/bin/true"]),
    ),
  };
  const old = approveSystem(c, "First synthetic outcome", "fixture");
  await recordSystem(c, old.id, "verified");
  withSyncLock(systemRoot(c), "outcome-approval", () => {
    const probe =
      "import {recordSystem} from " +
      JSON.stringify(
        pathToFileURL(path.join(PACKAGE_ROOT, "src/system/state.ts")).href,
      ) +
      "; await recordSystem(" +
      JSON.stringify(c) +
      "," +
      JSON.stringify(old.id) +
      ',"verified",{},o=>{o.pending={id:"synthetic",source:"synthetic",tool:"write"};});';
    const result = spawnSync(
      process.execPath,
      ["--input-type=module", "--eval", probe],
      { encoding: "utf8", timeout: 20000 },
    );
    assert.notEqual(result.status, 0);
    assert.match(result.stderr, /writer_busy/);
  });
  const next = approveSystem(c, "Replacement synthetic outcome", "fixture");
  await assert.rejects(recordSystem(c, old.id, "verified"), /outcome changed/);
  assert.throws(() => beginPrivileged(c, old.id, "write"), /outcome changed/);
  assert.equal(currentOperation(c)?.id, next.id);
});

test("browser close waits for an in-flight launch before releasing its managed pack", async () => {
  const state = directory("browser-launch"),
    parent = path.join(state, "assistant/packs");
  const root = path.join(parent, "browser-" + randomUUID());
  fs.mkdirSync(path.join(root, "node_modules/playwright"), { recursive: true });
  fs.mkdirSync(path.join(root, "browsers"));
  const executable = path.join(root, "browsers/chromium");
  fs.writeFileSync(executable, "fixture", { mode: 0o700 });
  const lock = JSON.parse(
    fs.readFileSync(
      path.join(
        PACKAGE_ROOT,
        "resources/optional-packs/browser/package-lock.json",
      ),
      "utf8",
    ),
  );
  fs.writeFileSync(
    path.join(root, "package.json"),
    JSON.stringify({ dependencies: { playwright: "1.64.0" } }),
  );
  fs.writeFileSync(path.join(root, "package-lock.json"), JSON.stringify(lock));
  fs.writeFileSync(
    path.join(parent, "browser.json"),
    JSON.stringify({
      version: 1,
      root,
      dependencies: { playwright: "1.64.0" },
      lock,
      browserExecutable: executable,
    }),
  );
  const gate = path.join(base, "launch-ready"),
    finish = path.join(base, "launch-finish"),
    closed = path.join(base, "launch-closed");
  const module =
    'import fs from "node:fs"; export const chromium={async launchPersistentContext(){fs.writeFileSync(' +
    JSON.stringify(gate) +
    ',"ready"); while(!fs.existsSync(' +
    JSON.stringify(finish) +
    ')) await new Promise(r=>setTimeout(r,5)); return {routeWebSocket:async()=>{},route:async()=>{},pages:()=>[{url:()=>"about:blank"}],close:async()=>fs.writeFileSync(' +
    JSON.stringify(closed) +
    ',"closed")};}};';
  fs.writeFileSync(
    path.join(root, "node_modules/playwright/index.mjs"),
    module,
  );
  const browser = new ManagedBrowser(state);
  const opening = browser.open();
  for (let i = 0; i < 200 && !fs.existsSync(gate); i++)
    await new Promise((r) => setTimeout(r, 5));
  assert(fs.existsSync(gate), "delayed fixture launch started");
  let completed = false;
  const closing = browser.close().then(() => {
    completed = true;
  });
  await new Promise((r) => setTimeout(r, 20));
  assert.equal(completed, false);
  assert.equal(fs.readdirSync(path.join(parent, "uses")).length, 1);
  fs.writeFileSync(finish, "finish");
  await Promise.all([opening, closing]);
  assert(fs.existsSync(closed));
  assert.equal(fs.readdirSync(path.join(parent, "uses")).length, 0);
});
