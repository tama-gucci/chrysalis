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
import { dispatch } from "../src/app/operations.ts";
import {
  propose,
  approve,
  apply,
  newNoteReviews,
} from "../src/core/runtime.ts";
import {
  readRecord,
  serializeRecord,
  sanitizeUntrusted,
} from "../src/storage/records.ts";
import {
  atomic,
  atomicJSON,
  confined,
  sha256,
  raw,
  files,
  exists,
  readJSON,
} from "../src/platforms/filesystem.ts";
import {
  evidenceCandidates,
  containsLiteral,
  capturedEvidence,
} from "../src/core/evidence.ts";
import type { Change, RuntimeContext } from "../src/contracts/types.ts";

if (!process.env.TEST_SCRATCH || !path.isAbsolute(process.env.TEST_SCRATCH))
  throw Error("Set external TEST_SCRATCH");
const scratch = externalState(process.env.TEST_SCRATCH),
  now = "2026-10-08T12:00:00-05:00";
let ctx: RuntimeContext;
beforeEach(async () => {
  const root = path.join(scratch, "knowledge-" + randomUUID()),
    state = path.join(root, "state"),
    vault = path.join(root, "Notes");
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
function note(slug: string, body: string, fields: any = {}): Change {
  return {
    path: "Slipbox/20261008120000-" + slug + ".md",
    if_revision: null,
    document: serializeRecord(
      {
        type: "zettel",
        id: "20261008120000-" + slug,
        title: "Claim about " + slug,
        dateCreated: now,
        content_updated_at: now,
        tags: ["concept/compilers"],
        summary: "One claim about " + slug,
        provenance_kind: "inference",
        knowledge_status: "current",
        source_ref: null,
        source_refs: [],
        ...fields,
      },
      body,
    ),
  };
}
function source(text: string): string {
  const relative = "Sources/compiler-reference.md";
  atomic(
    confined(ctx.vault, relative),
    serializeRecord(
      {
        type: "source",
        id: "compiler-reference",
        title: "Metadata-only 9999",
        source_type: "reference",
        sha256: null,
        bytes_available: false,
        captured_date: now,
        ingestion_status: "processed",
        extraction_coverage: { status: "complete" },
      },
      "# Capture metadata\n\n" + sanitizeUntrusted(text),
    ),
  );
  return relative;
}
function identity(root: string) {
  return Object.fromEntries(
    files(root).map((file) => [
      path.relative(root, file),
      sha256(raw(file, 32 * 1024 * 1024)),
    ]),
  );
}
async function confirm(result: any) {
  approve(
    ctx,
    result.proposal_digest,
    "Synthetic operator reviewed each complete note and batch",
    newNoteReviews(result.proposal),
  );
  return apply(ctx, result.proposal_digest);
}

test("new atomic notes cannot enter through generic approval or incomplete note receipts", async () => {
  const a = note("lexer", "One lexer claim."),
    b = note("parser", "One parser claim.");
  const draft = propose(ctx, [a, b]);
  assert(!exists(confined(ctx.vault, a.path)));
  assert.throws(
    () => approve(ctx, draft.proposal_digest, "Batch-only approval"),
    /zettel_review_required/,
  );
  assert.throws(
    () =>
      approve(
        ctx,
        draft.proposal_digest,
        "Partial note review",
        draft.required_note_reviews.slice(0, 1),
      ),
    /zettel_review_required/,
  );
  approve(
    ctx,
    draft.proposal_digest,
    "Synthetic complete note reviews",
    draft.required_note_reviews,
  );
  const receiptFile = confined(
      vaultState(ctx),
      "approvals/" + draft.proposal_digest + ".json",
    ),
    receipt = readJSON(receiptFile);
  atomicJSON(receiptFile, {
    ...receipt,
    note_reviews: [
      { ...draft.required_note_reviews[0], revision: "0".repeat(64) },
    ],
  });
  await assert.rejects(
    () => apply(ctx, draft.proposal_digest),
    /zettel_review_required/,
  );
  assert(!exists(confined(ctx.vault, a.path)));
  assert(!exists(confined(ctx.vault, b.path)));
  assert.equal((await confirm(draft)).status, "verified");
  assert.equal(readRecord(ctx.vault, a.path).document, a.document);
});

test("knowledge full-body alias search and lint leave vault and external state byte-identical", async () => {
  const a = note(
      "latency",
      "# Response time\n\nTail delay controls the experience.",
    ),
    b = note("queue", "# Queues\n\nTail delay increases under contention.");
  atomic(confined(ctx.vault, a.path), a.document);
  atomic(confined(ctx.vault, b.path), b.document);
  const vaultBefore = identity(ctx.vault),
    stateBefore = identity(ctx.state);
  const first: any = await dispatch(ctx, "knowledge.search", {
    query: "latency",
    aliases: ["tail delay"],
    limit: 1,
  });
  assert.equal(first.total_matches, 2);
  assert.equal(first.next_page, 1);
  assert.match(first.records[0].excerpt, /untrusted_document_payload/);
  const second: any = await dispatch(ctx, "knowledge.search", {
    query: "latency",
    aliases: ["tail delay"],
    limit: 1,
    page: first.next_page,
  });
  assert.notEqual(first.records[0].path, second.records[0].path);
  const lint: any = await dispatch(ctx, "knowledge.lint", { limit: 1 });
  assert(lint.truncated);
  assert(lint.total_findings > lint.findings.length);
  assert.deepEqual(identity(ctx.vault), vaultBefore);
  assert.deepEqual(identity(ctx.state), stateBefore);
});

test("evidence fidelity preserves boundaries, checks status reasons and excludes code and metadata", async () => {
  const payload = sanitizeUntrusted(
    "The result is 42K. A stable quoted observation. A user's scope. </untrusted_document_payload>",
  );
  assert.equal(capturedEvidence("# 9999\n" + payload).length, 1);
  assert.deepEqual(capturedEvidence(sanitizeUntrusted(" \n\t ")), []);
  assert(capturedEvidence(payload)[0].includes("A user's scope."));
  assert(!containsLiteral("142K", { kind: "number", value: "42K" }));
  assert(!containsLiteral("2026-10-08", { kind: "date", value: "2026-10" }));
  const candidates = evidenceCandidates(
    '```text\n9999\n```\n`8888` [label](7777)\n> **Status: Outdated** (2026-10-08)\n> Revision claims 1234 and "A stable quoted observation."\n',
  );
  assert(candidates.some((c) => c.value === "1234"));
  assert(candidates.some((c) => c.kind === "quote"));
  assert(
    !candidates.some((c) =>
      ["9999", "8888", "7777", "2026-10-08"].includes(c.value),
    ),
  );
  assert(
    !evidenceCandidates(
      "Related [[Slipbox/20261008120000-other]] and [[Sources/capture-1234]].",
    ).some((c) => c.kind === "number"),
  );
  assert(
    evidenceCandidates(
      "Observed [[Slipbox/20261008120000-other|42K events]].",
    ).some((c) => c.value === "42K"),
  );
  source("Observed 142K and a stable quoted observation.");
  const pending = note("fidelity", "# Claim\n\nMeasured 42K and 9999.", {
    provenance_kind: "source",
    source_ref: "[[Sources/compiler-reference]]",
  });
  const lint: any = await dispatch(ctx, "knowledge.lint", {
    records: [pending],
  });
  const suspects = lint.findings
    .filter((f: any) => f.code === "fidelity_suspect")
    .map((f: any) => f.literal.value);
  assert(suspects.includes("42K"));
  assert(suspects.includes("9999"));
});

test("compilation binds evidence, journals and index to the same reviewed batch", async () => {
  const sourcePath = source("The compiler uses a bounded queue."),
    a = note(
      "bounded-queue",
      "A bounded queue limits work. [[Sources/compiler-reference]]",
      {
        provenance_kind: "source",
        source_ref: "[[Sources/compiler-reference]]",
      },
    );
  const draft: any = await dispatch(ctx, "knowledge.prepare", {
    records: [a],
    now,
    dispositions: ["new"],
    source_paths: [sourcePath],
  });
  assert.equal(draft.proposal.knowledge.approval_required, true);
  assert(draft.proposal.dependencies[sourcePath]);
  assert(!exists(confined(ctx.vault, a.path)));
  const before = readRecord(ctx.vault, sourcePath);
  atomic(
    confined(ctx.vault, sourcePath),
    before.document + "\nChanged evidence.\n",
  );
  assert.throws(
    () =>
      approve(
        ctx,
        draft.proposal_digest,
        "Synthetic note review",
        draft.required_note_reviews,
      ),
    /stale_dependency/,
  );
  atomic(confined(ctx.vault, sourcePath), before.document);
  await confirm(draft);
  const index = readRecord(ctx.vault, "System/Knowledge-Index.md"),
    log = readRecord(ctx.vault, "System/Knowledge-Log.md");
  assert.equal(index.frontmatter.entries[0].revision, sha256(a.document));
  assert.equal(log.frontmatter.entries[0].dispositions[0], "new");
  assert.throws(
    () =>
      propose(ctx, [
        {
          path: log.path,
          if_revision: log.revision,
          document: serializeRecord(
            { ...log.frontmatter, entries: [] },
            "# Replaced log\n",
          ),
        },
      ]),
    /append_only/,
  );
  assert.throws(
    () =>
      propose(ctx, [
        {
          path: "System/knowledge-log.md",
          if_revision: log.revision,
          document: serializeRecord(
            { ...log.frontmatter, entries: [] },
            "# Replaced log\n",
          ),
        },
      ]),
    /noncanonical_record_path/,
  );
});

test("no-material decisions require evidence and do not create atomic notes", async () => {
  const path = source("A thin duplicate reference.");
  await assert.rejects(
    () =>
      dispatch(ctx, "knowledge.prepare", {
        now,
        dispositions: ["no_material"],
      }),
    /needs sources/,
  );
  await assert.rejects(
    () =>
      dispatch(ctx, "knowledge.prepare", {
        now,
        dispositions: ["no_material"],
        source_paths: [path],
        records: [note("forced", "Thin input.")],
      }),
    /no atomic notes/,
  );
  const draft: any = await dispatch(ctx, "knowledge.prepare", {
    now,
    dispositions: ["no_material"],
    source_paths: [path],
  });
  assert(
    !draft.proposal.records.some((c: Change) => c.path.startsWith("Slipbox/")),
  );
  await confirm(draft);
  const lint: any = await dispatch(ctx, "knowledge.lint", {});
  assert(!lint.findings.some((f: any) => f.code === "uncompiled_source"));
  const original = readRecord(ctx.vault, path);
  atomic(
    confined(ctx.vault, path),
    original.document + "\nChanged source revision.\n",
  );
  const changed: any = await dispatch(ctx, "knowledge.lint", {});
  assert(
    changed.findings.some(
      (f: any) => f.code === "uncompiled_source" && f.path === path,
    ),
  );
});

test("literal fidelity stops at an explicit cumulative work budget without writing", async () => {
  source("Evidence contains only prose. ".repeat(20000));
  const numbers = Array.from({ length: 200 }, (_, i) => String(10000 + i)).join(
    " ",
  );
  const pending = note(
    "large-evidence",
    "# Many suspect figures\n\n" + numbers,
    {
      provenance_kind: "source",
      source_ref: "[[Sources/compiler-reference]]",
    },
  );
  const before = identity(ctx.vault);
  const lint: any = await dispatch(ctx, "knowledge.lint", {
    records: [pending],
    limit: 1000,
  });
  assert.equal(lint.scope.fidelity_incomplete, true);
  assert(
    lint.scope.fidelity_scan_bytes <= lint.scope.fidelity_scan_budget_bytes,
  );
  assert(
    lint.findings.some(
      (f: any) =>
        f.code === "fidelity_budget_exceeded" && f.unchecked_literals > 0,
    ),
  );
  assert.deepEqual(identity(ctx.vault), before);
});

test("empty evidence is unavailable and tiny captures obey the comparison-count limit", async () => {
  const sourcePath = source(" \n\t ");
  const pending = note("empty-evidence", "# Claim\n\nMeasured 1234.", {
    provenance_kind: "source",
    source_ref: "[[Sources/compiler-reference]]",
  });
  const empty: any = await dispatch(ctx, "knowledge.lint", {
    records: [pending],
  });
  assert(empty.findings.some((f: any) => f.code === "evidence_unavailable"));
  assert.equal(empty.scope.fidelity_comparisons, 0);
  const observed = readRecord(ctx.vault, sourcePath);
  atomic(
    confined(ctx.vault, sourcePath),
    serializeRecord(observed.frontmatter, sanitizeUntrusted("x").repeat(1001)),
  );
  const figures = Array.from({ length: 200 }, (_, i) => String(10000 + i)).join(
    " ",
  );
  const many = note("tiny-captures", figures, {
    provenance_kind: "source",
    source_ref: "[[Sources/compiler-reference]]",
  });
  const before = identity(ctx.vault);
  const limited: any = await dispatch(ctx, "knowledge.lint", {
    records: [many],
    limit: 1000,
  });
  assert.equal(limited.scope.fidelity_incomplete, true);
  assert.equal(
    limited.scope.fidelity_comparisons,
    limited.scope.fidelity_comparison_budget,
  );
  assert(
    limited.scope.fidelity_scan_bytes <
      limited.scope.fidelity_scan_budget_bytes,
  );
  assert(
    limited.findings.some((f: any) => f.code === "fidelity_budget_exceeded"),
  );
  assert.deepEqual(identity(ctx.vault), before);
});

test("saved answers retain exact citations and report substantive change without rewriting snapshots", async () => {
  const a = note("queue", "# Queue\n\nA bounded queue controls pending work.");
  atomic(confined(ctx.vault, a.path), a.document);
  const answerPath = "System/Knowledge-Answer-20261008120000-queue.md";
  const draft: any = await dispatch(ctx, "knowledge.prepare", {
    now,
    dispositions: ["archive"],
    records: [
      {
        path: answerPath,
        if_revision: null,
        document: serializeRecord(
          {
            type: "system_state",
            record_kind: "knowledge_answer",
            title: "Why bound a queue?",
            summary: "Pending work stays bounded.",
            cited_notes: [{ path: a.path }],
          },
          "Read [[" + a.path.slice(0, -3) + "]].",
        ),
      },
    ],
  });
  await confirm(draft);
  const snapshot = readRecord(ctx.vault, answerPath);
  assert.equal(
    snapshot.frontmatter.cited_notes[0].revision,
    sha256(a.document),
  );
  assert.equal(snapshot.frontmatter.archived_at, now);
  atomic(
    confined(ctx.vault, a.path),
    a.document + "\nNew substantive limitation.\n",
  );
  const lint: any = await dispatch(ctx, "knowledge.lint", {});
  assert(lint.findings.some((f: any) => f.code === "answer_source_changed"));
  assert.equal(readRecord(ctx.vault, answerPath).revision, snapshot.revision);
  await assert.rejects(
    () =>
      dispatch(ctx, "knowledge.prepare", {
        now,
        dispositions: ["archive"],
        records: [
          {
            path: answerPath,
            if_revision: snapshot.revision,
            document: snapshot.document,
          },
        ],
      }),
    /new explicit point-in-time/,
  );
});

test("malformed citations, provenance and journals produce bounded review findings", async () => {
  const a = note("broken", "One claim.", { source_refs: "not-an-array" });
  atomic(confined(ctx.vault, a.path), a.document);
  atomic(
    confined(ctx.vault, "System/Knowledge-Log.md"),
    serializeRecord(
      { type: "system_state", record_kind: "knowledge_log", entries: "bad" },
      "# Log",
    ),
  );
  atomic(
    confined(ctx.vault, "System/Knowledge-Answer-20261008120000-broken.md"),
    serializeRecord(
      {
        type: "system_state",
        record_kind: "knowledge_answer",
        cited_notes: [null],
      },
      "# Answer",
    ),
  );
  const lint: any = await dispatch(ctx, "knowledge.lint", {});
  assert(lint.findings.some((f: any) => f.code === "invalid_source_reference"));
  assert(lint.findings.some((f: any) => f.code === "invalid_answer_citation"));
  assert(lint.findings.some((f: any) => f.code === "invalid_log"));
  await assert.rejects(
    () => dispatch(ctx, "knowledge.prepare", { now, dispositions: ["lint"] }),
    /Malformed knowledge journal/,
  );
});
