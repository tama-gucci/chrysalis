import test, { beforeEach } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  prepareOnboarding,
  approveSetup,
  applySetup,
} from "../src/app/onboarding.ts";
import {
  externalState,
  runtimeContext,
  vaultState,
} from "../src/storage/context.ts";
import {
  prepareDocumentFolder,
  selectDocumentFolder,
  documentFolderStatus,
  approveDocumentImport,
} from "../src/core/documents.ts";
import { dispatch } from "../src/app/operations.ts";
import { approve, newNoteReviews } from "../src/core/runtime.ts";
import { serializeRecord } from "../src/storage/records.ts";
import {
  PACKAGE_ROOT,
  files,
  confined,
  exists,
  raw,
  sha256,
} from "../src/platforms/filesystem.ts";
import type { RuntimeContext } from "../src/contracts/types.ts";

if (!process.env.TEST_SCRATCH || !path.isAbsolute(process.env.TEST_SCRATCH))
  throw Error("Set external TEST_SCRATCH");
const scratch = externalState(process.env.TEST_SCRATCH),
  now = "2026-10-08T12:00:00-05:00";
let ctx: RuntimeContext, root: string, source: string;
beforeEach(async () => {
  root = path.join(scratch, "documents-" + randomUUID());
  const state = path.join(root, "state"),
    vault = path.join(root, "Notes");
  source = path.join(root, "Life documents");
  fs.mkdirSync(source, { recursive: true });
  const setup = prepareOnboarding({
    vault,
    state,
    timezone: "America/Chicago",
  });
  approveSetup(
    state,
    setup.proposal_digest,
    "Synthetic operator setup confirmation",
  );
  await applySetup(state, setup.proposal_digest);
  ctx = runtimeContext(vault, state, now);
});
function put(
  relative: string,
  value: string | Buffer = "A parser turns a token stream into a syntax tree.",
) {
  const target = confined(source, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, value);
  return target;
}
function select() {
  const folder = prepareDocumentFolder(ctx, source);
  selectDocumentFolder(
    ctx,
    folder,
    "Synthetic operator selected exact folder scope",
  );
  return folder;
}
function snapshot(directory: string) {
  return files(directory).map((f) => [
    path.relative(directory, f),
    sha256(fs.readFileSync(f)),
  ]);
}

test("life documents require native selection and cannot override package, state or vault roots", async () => {
  assert.equal(documentFolderStatus(ctx).status, "not_selected");
  await assert.rejects(
    dispatch(ctx, "documents.discover", {}),
    /select.*folder/i,
  );
  await assert.rejects(
    dispatch(ctx, "documents.select", { root: source }),
    /operation/i,
  );
  for (const boundary of [ctx.vault, ctx.state, PACKAGE_ROOT, root])
    assert.throws(() => prepareDocumentFolder(ctx, boundary), /separate/);
  assert.throws(
    () => prepareDocumentFolder(ctx, "relative-folder"),
    /absolute/,
  );
  const before = snapshot(ctx.vault);
  const folder = prepareDocumentFolder(ctx, source);
  assert.throws(() => selectDocumentFolder(ctx, folder, ""), /approval/);
  assert.equal(documentFolderStatus(ctx).status, "not_selected");
  select();
  await assert.rejects(
    dispatch(ctx, "documents.discover", { root: source }),
    /Unsupported/,
  );
  assert.deepEqual(snapshot(ctx.vault), before);
});

test("life-document inventory is paged metadata only and reports excluded or depth-limited files", async () => {
  put("resume.txt");
  put("portfolio.docx");
  put("scan.png");
  put(".hidden-secret.txt", "Excluded synthetic token");
  put("deep/".repeat(9) + "bill.txt");
  select();
  const beforeVault = snapshot(ctx.vault),
    beforeState = snapshot(ctx.state);
  const first: any = await dispatch(ctx, "documents.discover", {
    page_size: 1,
  });
  assert.equal(first.items.length, 1);
  assert.equal(first.next_page_token, "1");
  assert.equal(first.discovery_complete, false);
  assert.equal(first.scan_truncated, true);
  assert(
    first.omitted.some((item: any) => item.reason === "hidden_or_generated"),
  );
  assert(first.omitted.some((item: any) => item.reason === "depth_limit"));
  const all: any = await dispatch(ctx, "documents.discover", {
    page_size: 100,
  });
  assert.deepEqual(
    all.items.map((item: any) => item.extraction).sort(),
    ["ocr_required", "supported_bounded", "unsupported_deferred"].sort(),
  );
  for (const item of all.items) {
    assert.equal(item.sha256, null);
    assert.equal(item.bytes_read, false);
    assert(!("content" in item));
  }
  assert.deepEqual(snapshot(ctx.vault), beforeVault);
  assert.deepEqual(snapshot(ctx.state), beforeState);
});

test("document originals have a separate exact copy approval and retain source bytes and provenance", async () => {
  const original = put("portfolio [draft].txt"),
    hash = sha256(raw(original));
  select();
  const before = snapshot(ctx.vault),
    plan: any = await dispatch(ctx, "documents.prepare", {
      paths: ["portfolio [draft].txt"],
    });
  const entry = plan.manifest.entries[0];
  assert.match(
    entry.destination,
    /Attachments\/Originals\/Onboarding\/.+\/portfolio _draft_\.txt$/,
  );
  assert.equal(entry.sha256, hash);
  assert.deepEqual(snapshot(ctx.vault), before);
  await assert.rejects(
    dispatch(ctx, "documents.apply", { proposal_digest: plan.proposal_digest }),
    /approval_required/,
  );
  assert.throws(
    () => approveDocumentImport(ctx, plan.proposal_digest, ""),
    /approval/,
  );
  approveDocumentImport(
    ctx,
    plan.proposal_digest,
    "Synthetic operator confirmed exact copies",
  );
  const result: any = await dispatch(ctx, "documents.apply", {
    proposal_digest: plan.proposal_digest,
  });
  assert.equal(result.status, "verified");
  assert.equal(result.knowledge_records_created, false);
  assert.equal(sha256(raw(original)), hash);
  assert.equal(sha256(raw(confined(ctx.vault, entry.destination))), hash);
  const ingest: any = await dispatch(ctx, "ingest.draft", {
    envelope: result.envelope,
    date: "2026-10-08",
    now,
  });
  assert.equal(ingest.status, "review_required");
  assert.equal(ingest.proposal.records.length, 1);
  assert.match(ingest.proposal.records[0].path, /^Sources\//);
  assert(!exists(confined(ctx.vault, ingest.proposal.records[0].path)));
  assert.equal(
    ingest.proposal.records[0].document.includes(entry.destination),
    true,
  );
  // A derived note still cannot use a batch-only receipt after copy authorization.
  const sourceRecord = ingest.proposal.records[0],
    notePath = "Slipbox/20261008120000-token-stream.md";
  const compiled: any = await dispatch(ctx, "knowledge.prepare", {
    now,
    dispositions: ["new"],
    source_paths: [sourceRecord.path],
    records: [
      sourceRecord,
      {
        path: notePath,
        if_revision: null,
        document: serializeRecord(
          {
            type: "zettel",
            id: "20261008120000-token-stream",
            title: "Parsing constructs a syntax tree",
            dateCreated: now,
            tags: ["concept/compilers"],
            summary: "Parsing structures tokens.",
            provenance_kind: "source",
            source_ref: "[[" + sourceRecord.path.slice(0, -3) + "]]",
            source_refs: [],
          },
          "# Parsing constructs a syntax tree\n\nA parser turns a token stream into a syntax tree.\n\n[[" +
            sourceRecord.path.slice(0, -3) +
            "]]\n",
        ),
      },
    ],
  });
  assert.throws(
    () => approve(ctx, compiled.proposal_digest, "Synthetic batch only"),
    /individually|note/i,
  );
  assert.equal(newNoteReviews(compiled.proposal).length, 1);
  assert(!exists(confined(ctx.vault, notePath)));
});

test("changed pending source or selected-folder authorization blocks all copies before mutation", async () => {
  const first = put("resume.txt"),
    second = put("portfolio.txt");
  select();
  const plan: any = await dispatch(ctx, "documents.prepare", {
    paths: ["resume.txt", "portfolio.txt"],
  });
  approveDocumentImport(
    ctx,
    plan.proposal_digest,
    "Synthetic exact copy approval",
  );
  fs.writeFileSync(second, "Changed synthetic portfolio");
  await assert.rejects(
    dispatch(ctx, "documents.apply", { proposal_digest: plan.proposal_digest }),
    /source changed/,
  );
  for (const entry of plan.manifest.entries)
    assert(!exists(confined(ctx.vault, entry.destination)));
  assert.equal(sha256(raw(first)), plan.manifest.entries[0].sha256);
  select();
  await assert.rejects(
    dispatch(ctx, "documents.apply", { proposal_digest: plan.proposal_digest }),
    /authorization.*changed/,
  );
  for (const entry of plan.manifest.entries)
    assert(!exists(confined(ctx.vault, entry.destination)));
});

test("partial copy recovery verifies existing originals and never overwrites edited destinations", async () => {
  put("resume.txt");
  put("portfolio.txt");
  select();
  const plan: any = await dispatch(ctx, "documents.prepare", {
    paths: ["resume.txt", "portfolio.txt"],
  });
  approveDocumentImport(
    ctx,
    plan.proposal_digest,
    "Synthetic exact copy approval",
  );
  const first = plan.manifest.entries[0],
    target = confined(ctx.vault, first.destination);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.copyFileSync(confined(source, first.source_path), target);
  put(
    first.source_path,
    "Changed after a matching original had already been copied",
  );
  const resumed: any = await dispatch(ctx, "documents.apply", {
    proposal_digest: plan.proposal_digest,
  });
  assert.equal(resumed.status, "verified");
  assert.equal(sha256(raw(target)), first.sha256);
  fs.writeFileSync(target, "User edited the in-vault original");
  await assert.rejects(
    dispatch(ctx, "documents.apply", { proposal_digest: plan.proposal_digest }),
    /destination changed/,
  );
  assert.equal(raw(target).toString(), "User edited the in-vault original");
});

test("copy paths reject traversal, links, sanitized-name collisions and oversize selections", async () => {
  put("resume.txt");
  put("note[1].txt");
  put("note_1_.txt");
  select();
  for (const relative of [
    "../outside.txt",
    "folder/../resume.txt",
    "folder\\resume.txt",
    ".hidden.txt",
    "NODE_MODULES/dependency.txt",
  ])
    await assert.rejects(
      dispatch(ctx, "documents.prepare", { paths: [relative] }),
      /path|Hidden/,
    );
  await assert.rejects(
    dispatch(ctx, "documents.prepare", {
      paths: ["note[1].txt", "note_1_.txt"],
    }),
    /collide/,
  );
  const big = put("too-large.pdf", "");
  fs.truncateSync(big, 32 * 1024 * 1024 + 1);
  await assert.rejects(
    dispatch(ctx, "documents.prepare", { paths: ["too-large.pdf"] }),
    /budget/,
  );
  const link = path.join(source, "redirect");
  fs.symlinkSync(root, link, process.platform === "win32" ? "junction" : "dir");
  assert.throws(() => prepareDocumentFolder(ctx, link), /links or junctions/);
  await assert.rejects(
    dispatch(ctx, "documents.prepare", {
      paths: ["redirect/Life documents/resume.txt"],
    }),
    /links or junctions/,
  );
  const scan: any = await dispatch(ctx, "documents.discover", {});
  assert(
    scan.omitted.some(
      (item: any) =>
        item.path === "redirect" && item.reason === "redirected_path",
    ),
  );
  assert.equal(
    scan.items.find((item: any) => item.path === "too-large.pdf").import_status,
    "over_file_budget",
  );
  assert(!exists(confined(vaultState(ctx), "document-imports")));
});

test("copy batches reject cumulative oversize and canceled work while retaining exact approval", async () => {
  for (const name of ["one.pdf", "two.pdf", "three.pdf"]) {
    const full = put(name, "");
    fs.truncateSync(full, 24 * 1024 * 1024);
  }
  select();
  await assert.rejects(
    dispatch(ctx, "documents.prepare", {
      paths: ["one.pdf", "two.pdf", "three.pdf"],
    }),
    /budget/,
  );
  const plan: any = await dispatch(ctx, "documents.prepare", {
    paths: ["one.pdf"],
  });
  approveDocumentImport(
    ctx,
    plan.proposal_digest,
    "Synthetic exact copy approval",
  );
  const abort = new AbortController();
  abort.abort();
  await assert.rejects(
    dispatch({ ...ctx, signal: abort.signal }, "documents.apply", {
      proposal_digest: plan.proposal_digest,
    }),
    /Cancelled/,
  );
  assert(!exists(confined(ctx.vault, plan.manifest.entries[0].destination)));
  assert(
    exists(
      confined(
        vaultState(ctx),
        "document-approvals/" + plan.proposal_digest + ".json",
      ),
    ),
  );
});

test("Markdown copies require passive TaskNotes and Dataview settings bound to exact approval", async () => {
  const body =
    "---\ntags: [task]\nstatus: todo\n---\n\n# Original export\n\n```dataviewjs\nthrow Error('Passive fixture');\n```\n";
  put("task-export.md", body);
  select();
  const taskPath = confined(ctx.vault, ".obsidian/plugins/tasknotes/data.json"),
    viewPath = confined(ctx.vault, ".obsidian/plugins/dataview/data.json"),
    taskBytes = fs.readFileSync(taskPath),
    viewBytes = fs.readFileSync(viewPath),
    settings = JSON.parse(taskBytes.toString());
  assert(
    settings.excludedFolders
      .split(",")
      .map((entry: string) => entry.trim())
      .includes("Attachments/Originals"),
  );
  const plan: any = await dispatch(ctx, "documents.prepare", {
    paths: ["task-export.md"],
  });
  assert.equal(plan.manifest.markdown_safety.originals_excluded, true);
  assert.equal(
    plan.manifest.markdown_safety.tasknotes_settings_sha256,
    sha256(taskBytes),
  );
  approveDocumentImport(
    ctx,
    plan.proposal_digest,
    "Synthetic passive Markdown copy approval",
  );
  const target = confined(ctx.vault, plan.manifest.entries[0].destination);
  fs.writeFileSync(
    taskPath,
    JSON.stringify({ ...settings, excludedFolders: "TaskNotes/Archive" }),
  );
  await assert.rejects(
    dispatch(ctx, "documents.prepare", { paths: ["task-export.md"] }),
    /Markdown import blocked/,
  );
  await assert.rejects(
    dispatch(ctx, "documents.apply", { proposal_digest: plan.proposal_digest }),
    /Markdown import blocked/,
  );
  assert(!exists(target));
  fs.writeFileSync(taskPath, taskBytes);
  for (const flag of ["enableDataviewJs", "enableInlineDataviewJs"]) {
    fs.writeFileSync(
      viewPath,
      JSON.stringify({ ...JSON.parse(viewBytes.toString()), [flag]: true }),
    );
    await assert.rejects(
      dispatch(ctx, "documents.apply", {
        proposal_digest: plan.proposal_digest,
      }),
      /Markdown import blocked/,
    );
    assert(!exists(target));
  }
  fs.writeFileSync(viewPath, viewBytes);
  fs.writeFileSync(
    taskPath,
    JSON.stringify({ ...settings, defaultTaskPriority: "low" }),
  );
  await assert.rejects(
    dispatch(ctx, "documents.apply", { proposal_digest: plan.proposal_digest }),
    /settings changed/,
  );
  assert(!exists(target));
  const replacement: any = await dispatch(ctx, "documents.prepare", {
    paths: ["task-export.md"],
  });
  approveDocumentImport(
    ctx,
    replacement.proposal_digest,
    "Synthetic newly reviewed passive settings",
  );
  await dispatch(ctx, "documents.apply", {
    proposal_digest: replacement.proposal_digest,
  });
  assert.equal(fs.readFileSync(target, "utf8"), body);
  assert.equal(
    fs.readFileSync(confined(source, "task-export.md"), "utf8"),
    body,
  );
  assert.deepEqual(fs.readdirSync(confined(ctx.vault, "TaskNotes/Tasks")), []);
});

test("reopened source and destination paths must remain regular files", async () => {
  const original = put("resume.txt");
  put("portfolio.txt");
  select();
  const plan: any = await dispatch(ctx, "documents.prepare", {
    paths: ["resume.txt"],
  });
  approveDocumentImport(ctx, plan.proposal_digest, "Synthetic exact copies");
  fs.renameSync(original, original + ".preserved");
  fs.mkdirSync(original);
  await assert.rejects(
    dispatch(ctx, "documents.apply", { proposal_digest: plan.proposal_digest }),
    /regular/,
  );
  assert(!exists(confined(ctx.vault, plan.manifest.entries[0].destination)));
  const other: any = await dispatch(ctx, "documents.prepare", {
    paths: ["portfolio.txt"],
  });
  approveDocumentImport(ctx, other.proposal_digest, "Synthetic exact copies");
  const target = confined(ctx.vault, other.manifest.entries[0].destination);
  fs.mkdirSync(target, { recursive: true });
  await assert.rejects(
    dispatch(ctx, "documents.apply", {
      proposal_digest: other.proposal_digest,
    }),
    /regular/,
  );
  assert(fs.statSync(target).isDirectory());
});
