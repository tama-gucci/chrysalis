import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomBytes, randomUUID } from "node:crypto";
import {
  parsePasswordExport,
  mergePasswordSnapshot,
  isPasswordExport,
} from "../src/passwords/import.ts";
import { PasswordStore } from "../src/passwords/store.ts";
import { BrowserSecretGuard } from "../src/research/secret-guard.ts";
import { ManagedBrowser } from "../src/research/playwright.ts";
import {
  prepareOnboarding,
  approveSetup,
  applySetup,
} from "../src/app/onboarding.ts";
import { runtimeContext } from "../src/storage/context.ts";
import { dispatch } from "../src/app/operations.ts";
import {
  prepareDocumentFolder,
  selectDocumentFolder,
} from "../src/core/documents.ts";
import { snapshotWorkspace } from "../src/execution/workspace.ts";
if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(process.env.TEST_SCRATCH, "passwords-" + randomUUID());
fs.mkdirSync(base, { recursive: true });
const secret = ["synthetic", "password", "canary"].join("-");
const csv = (pw = secret, user = "user@example.com") =>
  Buffer.from(
    'name,url,username,password\r\n"Sample, account",https://example.com/login,' +
      user +
      "," +
      pw +
      "\r\n",
  );
async function context() {
  const root = path.join(base, randomUUID()),
    vault = path.join(root, "Notes"),
    state = path.join(root, "state");
  const setup = prepareOnboarding({
    vault,
    state,
    timezone: "America/Chicago",
  });
  approveSetup(state, setup.proposal_digest, "Synthetic operator approval");
  await applySetup(state, setup.proposal_digest);
  return runtimeContext(vault, state);
}
function fixtureStore(ctx: any) {
  const key = randomBytes(32);
  return new PasswordStore(ctx, { get: async () => key });
}

test("CSV/Bitwarden snapshots normalize browser origins, reject malformed data, skip non-login fields and merge without deletion", () => {
  assert(isPasswordExport(csv()));
  const initial = parsePasswordExport(csv());
  assert.equal(initial.records[0].name, "Sample, account");
  assert.deepEqual(initial.records[0].origins, ["https://example.com"]);
  const merged = mergePasswordSnapshot([], initial),
    id = merged.records[0].id;
  const again = mergePasswordSnapshot(
    merged.records,
    parsePasswordExport(csv()),
  );
  assert.equal(again.summary.unchanged, 1);
  assert.equal(again.records[0].id, id);
  const changed = mergePasswordSnapshot(
    again.records,
    parsePasswordExport(csv(secret + "-rotated")),
  );
  assert.equal(changed.summary.updated, 1);
  assert.equal(changed.records[0].id, id);
  const appended = mergePasswordSnapshot(
    changed.records,
    parsePasswordExport(csv(secret, "second@example.com")),
  );
  assert.equal(appended.summary.added, 1);
  assert.equal(appended.summary.total, 2);
  assert.equal(appended.summary.deleted, 0);
  assert.throws(
    () =>
      parsePasswordExport(
        Buffer.from(
          'username,url,password\nu,https://example.com,"unterminated',
        ),
      ),
    /invalid_or_unsupported/,
  );
  const duplicate = Buffer.from(
    "name,url,username,password\na,https://example.com,u,a\nb,https://example.com,u,b\n",
  );
  assert.throws(
    () => mergePasswordSnapshot([], parsePasswordExport(duplicate)),
    /ambiguous/,
  );
  const json = Buffer.from(
    JSON.stringify({
      items: [
        {
          id: "synthetic-id",
          type: 1,
          name: "Sample",
          login: {
            username: "u",
            password: secret,
            uris: [
              { uri: "https://example.com/one" },
              { uri: "https://example.com/two" },
            ],
          },
        },
        { type: 2, notes: secret },
      ],
    }),
  );
  assert(isPasswordExport(json));
  assert.equal(parsePasswordExport(json).records.length, 1);
  for (const url of [
    "https://192.168.1.1",
    "https://[::1]",
    "https://127.0.0.1",
  ]) {
    assert.equal(
      parsePasswordExport(
        Buffer.from(JSON.stringify([{ password: secret, urls: [url] }])),
      ).records.length,
      0,
    );
  }
  assert.equal(parsePasswordExport(json).skipped, 1);
  assert.equal(
    parsePasswordExport(
      Buffer.from("name,url,username,password\nLocal,http://localhost,u,x\n"),
    ).records.length,
    0,
  );
});
test("password store is encrypted, rejected imports write nothing, stale input/store and mutated native plans cannot overwrite", async () => {
  const ctx = await context(),
    s = fixtureStore(ctx);
  s.setupInbox();
  const input = path.join(s.inbox, "export.csv");
  fs.writeFileSync(input, csv());
  const plan = await s.prepare("export.csv");
  assert.equal((await s.apply(plan, async () => false)).status, "declined");
  assert(!s.configured());
  assert.equal((await s.apply(plan, async () => true)).status, "imported");
  const bytes = fs.readFileSync(
    path.join(s.root, "passwords.encrypted.json"),
    "utf8",
  );
  assert(!bytes.includes(secret));
  assert(!bytes.includes("user@example.com"));
  assert.equal((await s.records())[0].password, secret);
  fs.writeFileSync(input, csv(secret + "-new"));
  const stale = await s.prepare("export.csv");
  fs.writeFileSync(input, csv(secret + "-changed"));
  await assert.rejects(
    s.apply(stale, async () => true),
    /stale/,
  );
  assert.equal((await s.records())[0].password, secret);
  const tampered = await s.prepare("export.csv");
  await assert.rejects(
    s.apply(tampered, async () => {
      tampered.records[0].password = "changed-after-review";
      return true;
    }),
    /plan_changed/,
  );
  const p1 = await s.prepare("export.csv"),
    p2 = await s.prepare("export.csv");
  await s.apply(p1, async () => true);
  await assert.rejects(
    s.apply(p2, async () => true),
    /stale/,
  );
  fs.writeFileSync(input, csv(secret + "-other"));
  assert.throws(
    () => s.removeReviewedInput(p1),
    /Removal candidate changed; private recovery preserved/,
  );
  const file = path.join(s.root, "passwords.encrypted.json"),
    data = JSON.parse(fs.readFileSync(file, "utf8"));
  data.tag = Buffer.alloc(16).toString("base64");
  fs.writeFileSync(file, JSON.stringify(data));
  await assert.rejects(s.records(), /corrupt/);
});
test("known password exports cannot become vault originals, model-readable evidence or workspace snapshots", async () => {
  const ctx = await context(),
    folder = path.join(base, "documents-" + randomUUID());
  fs.mkdirSync(folder);
  fs.writeFileSync(path.join(folder, "notes.csv"), csv());
  selectDocumentFolder(
    ctx,
    prepareDocumentFolder(ctx, folder),
    "Synthetic selected document folder",
  );
  await assert.rejects(
    dispatch(ctx, "documents.prepare", { paths: ["notes.csv"] }),
    /Password exports/,
  );
  const original = path.join(ctx.vault, "Attachments/Originals/export.csv");
  fs.writeFileSync(original, csv());
  await assert.rejects(
    dispatch(ctx, "original.inspect", {
      path: "Attachments/Originals/export.csv",
      extract: true,
    }),
    /Password exports/,
  );
  const snapshots = path.join(base, "snapshots-" + randomUUID());
  fs.mkdirSync(snapshots);
  assert.throws(() => snapshotWorkspace(folder, snapshots), /Password exports/);
  assert.equal(fs.readdirSync(snapshots).length, 0);
});
test("browser autofill binds exact origins, validates fields, never returns values and blocks screenshots; known secret encodings are redacted", async () => {
  const guard = new BrowserSecretGuard();
  guard.configure([secret]);
  for (const v of [
    secret,
    encodeURIComponent(secret),
    Buffer.from(secret).toString("base64"),
  ])
    assert(!guard.text(v).includes(v));
  assert.equal(
    guard.url("https://example.com/p?token=" + secret + "#private"),
    "https://example.com/p",
  );
  const b: any = new ManagedBrowser(path.join(base, "browser"));
  let filled = "";
  const fields: any = {
    "#username": { type: "text" },
    "#password": { type: "password" },
    "#unsafe": { type: "text" },
  };
  const frame = {};
  b.page = {
    mainFrame: () => frame,
    url: () => "https://example.com/login",
    locator: (s: string) => ({
      count: async () => 1,
      elementHandle: async () => ({
        ownerFrame: async () => frame,
        evaluate: async (_f: any, password: boolean) =>
          password
            ? fields[s]?.type === "password"
            : fields[s]?.type === "text",
        fill: async (v: string) => {
          filled = v;
        },
        dispose: async () => {},
      }),
      fill: async () => {
        throw Error("Locator must not re-resolve for fill");
      },
    }),
  };
  b.configureSecrets([secret]);
  const record = parsePasswordExport(csv()).records[0];
  const result = await b.fillCredentials(
    record,
    {
      username: "#username",
      password: "#password",
    },
    "https://example.com",
  );
  assert.equal(filled, secret);
  assert.equal(result.submitted, false);
  assert(!JSON.stringify(result).includes(secret));
  assert(b.credentialOrigins.has("https://example.com"));
  await assert.rejects(
    b.fillCredentials(record, { password: "#unsafe" }, "https://example.com"),
    /unsafe/,
  );
  record.origins.push("https://other.example");
  b.page.url = () => "https://other.example/login";
  await assert.rejects(
    b.fillCredentials(record, { password: "#password" }, "https://example.com"),
    /unsafe/,
  );
  await assert.rejects(b.screenshot(), /Screenshots disabled/);
});
test(
  "actual OS-account protection encrypts and reloads synthetic credentials without a plaintext key",
  { skip: !process.env.CHRYSALIS_PASSWORD_DPAPI_ACCEPTANCE },
  async () => {
    const ctx = await context(),
      s = new PasswordStore(ctx);
    s.setupInbox();
    fs.writeFileSync(path.join(s.inbox, "export.csv"), csv());
    await s.apply(await s.prepare("export.csv"), async () => true);
    const reloaded = new PasswordStore(ctx);
    assert.equal((await reloaded.records())[0].password, secret);
    const key = JSON.parse(
      fs.readFileSync(path.join(s.root, "key.json"), "utf8"),
    );
    assert.equal(key.version, 1);
    if (key.backend === "windows-dpapi") {
      assert.deepEqual(Object.keys(key).sort(), [
        "backend",
        "encrypted",
        "version",
      ]);
      assert.equal(typeof key.encrypted, "string");
      assert(key.encrypted.length > 40);
    } else {
      assert.equal(key.backend, "os-secret-store");
      assert.deepEqual(Object.keys(key).sort(), [
        "backend",
        "reference",
        "version",
      ]);
      assert.match(key.reference, /^password-key-[a-f0-9-]{36}$/);
    }
    for (const name of ["key.json", "passwords.encrypted.json"]) {
      const text = fs.readFileSync(path.join(s.root, name), "utf8");
      assert(!text.includes(secret));
      assert(!text.includes("user@example.com"));
    }
  },
);

test("supported password export shapes are excluded and distinct manager IDs remain distinct", () => {
  const json = Buffer.from(
    JSON.stringify([{ password: secret, urls: ["https://example.com"] }]),
  );
  assert.equal(parsePasswordExport(json).records.length, 1);
  assert(isPasswordExport(json));
  const multilineHeader = Buffer.from(
    '"pass\nword",url,username\n' + secret + ",https://example.com,user\n",
  );
  assert.equal(parsePasswordExport(multilineHeader).records.length, 1);
  assert(isPasswordExport(multilineHeader));
  const leadingBlanks = Buffer.concat([Buffer.from("\n\r\n"), csv()]);
  assert.equal(parsePasswordExport(leadingBlanks).records.length, 1);
  assert(isPasswordExport(leadingBlanks));
  const longHeader = Buffer.from(
    "name," +
      "x".repeat(32768) +
      ",url,username,password\nName,unused,https://example.com,u," +
      secret +
      "\n",
  );
  assert.equal(parsePasswordExport(longHeader).records.length, 1);
  assert(isPasswordExport(longHeader));
  const records = parsePasswordExport(
    Buffer.from(
      JSON.stringify({
        items: [
          {
            id: "a",
            type: 1,
            name: "one",
            login: {
              username: "same",
              password: "first",
              uris: [{ uri: "https://example.com" }],
            },
          },
          {
            id: "b",
            type: 1,
            name: "two",
            login: {
              username: "same",
              password: "second",
              uris: [{ uri: "https://example.com" }],
            },
          },
        ],
      }),
    ),
  ).records;
  const merged = mergePasswordSnapshot([], { records, skipped: 0 });
  assert.equal(merged.records.length, 2);
  assert.equal(
    mergePasswordSnapshot(merged.records, { records, skipped: 0 }).summary
      .unchanged,
    2,
  );
});
test("literal redaction covers overlaps and short secrets; resource errors never contain secret patterns", () => {
  const guard = new BrowserSecretGuard();
  guard.configure(["abc", "bcde", "x"]);
  assert.equal(guard.text("abcde and x"), "[private] and [private]");
  assert.equal(guard.text("nothing"), "nothing");
  const oversized = secret.repeat(40000),
    limited = new BrowserSecretGuard();
  assert.throws(
    () => limited.configure([oversized]),
    (e) =>
      String(e) ===
      "Error: Private browser redaction unavailable; automation refused",
  );
  assert.throws(() => limited.text(secret), /automation refused/);
  assert.throws(
    () => guard.text("a".repeat(1024 * 1024 + 1)),
    /automation refused/,
  );
});
test("held credential inputs are revalidated after username events rather than resolved a second time", async () => {
  const b: any = new ManagedBrowser(path.join(base, "changing-fields")),
    frame = {};
  let safe = true,
    wrote = false,
    resolved = 0;
  const password = {
    ownerFrame: async () => frame,
    evaluate: async () => safe,
    fill: async () => {
      wrote = true;
    },
    dispose: async () => {},
  };
  const username = {
    ownerFrame: async () => frame,
    evaluate: async () => true,
    fill: async () => {
      safe = false;
    },
    dispose: async () => {},
  };
  b.page = {
    url: () => "https://example.com/login",
    mainFrame: () => frame,
    locator: (s: string) => ({
      count: async () => 1,
      elementHandle: async () => {
        resolved++;
        return s === "#u" ? username : password;
      },
    }),
  };
  const record = parsePasswordExport(csv()).records[0];
  await assert.rejects(
    b.fillCredentials(
      record,
      { username: "#u", password: "#p" },
      "https://example.com",
    ),
    /unsafe/,
  );
  assert.equal(resolved, 2);
  assert.equal(wrote, false);
});
test(
  "actual managed Chromium only fills exact approved primary-frame fields and redacts echoed credentials",
  { skip: !process.env.CHRYSALIS_BROWSER_ACCEPTANCE_STATE },
  async () => {
    const b: any = new ManagedBrowser(
      process.env.CHRYSALIS_BROWSER_ACCEPTANCE_STATE!,
      "password-test-" + randomUUID(),
    );
    try {
      await b.open(false, async () => false);
      await b.page.route("https://example.com/login", async (route: any) =>
        route.fulfill({
          status: 200,
          contentType: "text/html",
          body: `<title>Login</title><input id="u"><input type="password" id="p"><div id="echo"></div><a id="link" href="https://example.com/ok">Continue</a><script>document.querySelector('#p').addEventListener('input',e=>{document.title=e.target.value;document.querySelector('#echo').textContent=e.target.value;document.querySelector('#link').textContent=e.target.value;document.querySelector('#link').href='https://example.com/ok?token='+encodeURIComponent(e.target.value);});</script>`,
        }),
      );
      await b.navigate("https://example.com/login");
      const record = parsePasswordExport(csv()).records[0];
      const result = await b.fillCredentials(
        record,
        { username: "#u", password: "#p" },
        "https://example.com",
      );
      assert.equal(result.submitted, false);
      assert.equal(await b.page.locator("#p").inputValue(), secret);
      const evidence = JSON.stringify(await b.inspect());
      assert(!evidence.includes(secret));
      assert(!evidence.includes(encodeURIComponent(secret)));
      assert(!evidence.includes("?token"));
      await assert.rejects(b.screenshot(), /Screenshots disabled/);
      await assert.rejects(
        b.navigate("https://example.org"),
        /credential origins/,
      );
      assert.equal(
        await b.page.evaluate(async () => {
          try {
            await fetch("https://example.org/credential-boundary");
            return "unexpected";
          } catch {
            return "blocked";
          }
        }),
        "blocked",
      );
      await assert.rejects(
        b.fillCredentials(record, { password: "#u" }, "https://example.com"),
        /unsafe/,
      );
      record.origins.push("https://example.org");
      await assert.rejects(
        b.fillCredentials(record, { password: "#p" }, "https://example.org"),
        /unsafe/,
      );
    } finally {
      await b.close();
    }
  },
);
