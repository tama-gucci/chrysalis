import fs from "node:fs";
import path from "node:path";
import {
  canonical,
  digest,
  sha256,
  atomic,
  atomicJSON,
  confined,
  exists,
  raw,
  readJSON,
  withLock,
} from "../platforms/filesystem.ts";
import { vaultState, runtimeContext } from "../storage/context.ts";
import {
  readRecord,
  parse,
  validate,
  schemaFor,
  registeredTags,
  collection,
  recordPath,
} from "../storage/records.ts";
import { stamp, zoneName, nowStamp, dateOnly } from "../time/timezone.ts";
import {
  MODALITIES,
  MAX_RECORDS,
  MAX_REQUEST_BYTES,
} from "../contracts/types.ts";
import type {
  RuntimeContext,
  Change,
  Proposal,
  Metadata,
} from "../contracts/types.ts";
import { locationPolicy } from "./location.ts";

export const PLUGIN_FIELDS = new Set([
  "timeEntries",
  "pomodoros",
  "recurrence",
  "recurrenceAnchor",
  "complete_instances",
  "skipped_instances",
  "reminders",
  "blockedBy",
  "blocking",
  "contexts",
  "projects",
  "tn_role",
  "googleCalendarEventId",
  "googleCalendarId",
  "recurrence_anchor",
  "recurrence_parent",
  "occurrence_date",
  "materialization",
  "next_trigger",
  "template",
  "horizons",
  "attachments",
  "totalTrackedTime",
  "completedDate",
  "icsEventId",
  "customProperties",
  "isBlocked",
  "isBlocking",
  "hasSubtasks",
  "sortOrder",
  "archived",
  "occurrence_materialization",
  "occurrence_next_trigger",
  "occurrence_template",
  "occurrence_past_horizon",
  "occurrence_future_horizon",
  "tasknotes_manual_order",
  "dateModified",
]);
const equal = (a: any, b: any) => canonical(a ?? null) === canonical(b ?? null);
export function configuredZone(ctx: RuntimeContext) {
  return zoneName(
    readRecord(ctx.vault, "System/Memory.md").frontmatter.user_profile
      ?.timezone,
  );
}
export function checkRecord(
  ctx: RuntimeContext,
  item: Change,
  resume = false,
  all: Change[] = [],
) {
  const target = recordPath(ctx.vault, item.path),
    kind = schemaFor(item.path);
  if (
    typeof item.document !== "string" ||
    Buffer.byteLength(item.document) > 1024 * 1024
  )
    throw new Error("A bounded complete proposed document is required");
  if (item.if_revision !== null && !/^[a-f0-9]{64}$/.test(item.if_revision))
    throw new Error("Original raw-byte revision is required");
  const expected = sha256(item.document),
    current = exists(target) ? sha256(raw(target)) : null;
  if (current !== item.if_revision && !(resume && current === expected))
    throw new Error("stale_revision: refresh the entire document");
  const result = validate(ctx.vault, item.path, item.document);
  if (!result.valid)
    throw new Error("invalid_record: " + JSON.stringify(result.diagnostics));
  const old: Metadata = exists(target)
      ? readRecord(ctx.vault, item.path).frontmatter
      : {},
    next = result.frontmatter;
  const memory = all.find((c) => c.path === "System/Memory.md");
  const zone = zoneName(
    (item.path === "System/Memory.md"
      ? next
      : memory
        ? parse(memory.document).frontmatter
        : readRecord(ctx.vault, "System/Memory.md").frontmatter
    ).user_profile?.timezone,
  );
  if (item.path === "System/Memory.md")
    for (const modality of MODALITIES) {
      const m = next.cognitive_modality_defaults?.[modality]?.multiplier;
      if (typeof m !== "number" || !Number.isFinite(m) || m < 0.2 || m > 2)
        throw new Error("invalid_modality_multiplier");
    }
  for (const field of [
    "dateCreated",
    "created",
    "dateModified",
    "due",
    "due_at",
    "last_updated",
    "captured_date",
    "scheduled",
    "startedAt",
    "completedAt",
    "wake_time",
    "content_updated_at",
    "archived_at",
  ]) {
    const value = next[field];
    if (
      typeof value !== "string" ||
      !value.includes("T") ||
      equal(value, old[field])
    )
      continue;
    if (kind === "task" && field === "dateModified") continue;
    stamp(value, zone, true);
  }
  if (item.path === "System/Knowledge-Log.md" && exists(target)) {
    const prior = readRecord(ctx.vault, item.path);
    if (
      next.record_kind !== "knowledge_log" ||
      !Array.isArray(next.entries) ||
      !Array.isArray(prior.frontmatter.entries) ||
      !equal(
        next.entries.slice(0, prior.frontmatter.entries.length),
        prior.frontmatter.entries,
      ) ||
      !result.body.startsWith(prior.body)
    )
      throw new Error("knowledge_log_is_append_only");
  }
  if (kind === "task") {
    locationPolicy(next);
    for (const field of PLUGIN_FIELDS)
      if (field in old && !(field in next))
        throw new Error("plugin_field_removed: " + field);
    for (const field of [
      "timeEntries",
      "pomodoros",
      "complete_instances",
      "skipped_instances",
      "completedDate",
    ])
      if (field in old && !equal(old[field], next[field]))
        throw new Error("protected_plugin_history: " + field);
    for (const field of new Set([...Object.keys(old), ...Object.keys(next)]))
      if (
        (field.startsWith("googleCalendar") ||
          (field === "dateModified" && field in old)) &&
        !equal(old[field], next[field])
      )
        throw new Error("protected_plugin_field: " + field);
  }
  if (kind === "daily_note") {
    if (next.date && next.date !== path.basename(item.path, ".md"))
      throw new Error("daily_date_mismatch");
    const planningZone = zoneName(next.planning_timezone ?? zone);
    const intervals: Array<[number, number]> = [];
    for (const block of next.blocks ?? []) {
      const preserved = (old.blocks ?? []).some((b) => equal(b, block));
      const start = stamp(block.start, planningZone, !preserved),
        end = stamp(block.end, planningZone, !preserved);
      if (
        start.epochMilliseconds >= end.epochMilliseconds ||
        start.toPlainDate().toString() !== next.date ||
        end.toPlainDate().toString() !== next.date
      )
        throw new Error("invalid_daily_interval");
      if (
        intervals.some(
          ([a, b]) => start.epochMilliseconds < b && end.epochMilliseconds > a,
        )
      )
        throw new Error("overlapping_daily_intervals");
      intervals.push([start.epochMilliseconds, end.epochMilliseconds]);
    }
    for (const field of ["pomodoros", "timeEntries", "customProperties"])
      if (field in old && !(field in next))
        throw new Error("plugin_field_removed: " + field);
    for (const field of ["pomodoros", "timeEntries"])
      if (field in old && !equal(old[field], next[field]))
        throw new Error("protected_plugin_history: " + field);
  }
  if (
    kind === "source" &&
    next.sha256 &&
    (next.bytes_available !== true ||
      next.original_locator?.kind !== "vault_relative")
  )
    throw new Error(
      "Raw identity requires observed in-vault bytes; text fingerprints are separate",
    );
  if (kind === "source" && next.original_locator?.kind === "vault_relative") {
    const relative = next.original_locator.path;
    if (
      typeof relative !== "string" ||
      !relative.startsWith("Attachments/Originals/")
    )
      throw new Error("invalid_original_locator");
    const original = confined(ctx.vault, relative);
    if (!exists(original)) throw new Error("missing_original");
    if (next.sha256 && sha256(raw(original, 32 * 1024 * 1024)) !== next.sha256)
      throw new Error("original_hash_mismatch");
  }
  return { target, expected, kind, next };
}
export function validateRelationships(ctx: RuntimeContext, changes: Change[]) {
  const proposed = new Map(changes.map((c) => [c.path, parse(c.document)]));
  const tags = registeredTags(
    ctx.vault,
    proposed.get("System/Life-Roadmap.md")?.frontmatter,
  );
  const stems = new Map<string, Set<string>>();
  for (const name of [
    "tasks",
    "archive",
    "projects",
    "zettels",
    "sources",
    "daily",
  ]) {
    for (const row of collection(ctx.vault, name)) {
      const stem = path.basename(row.path, ".md");
      if (!stems.has(stem)) stems.set(stem, new Set());
      stems.get(stem)!.add(row.path);
    }
  }
  for (const relative of proposed.keys()) {
    const stem = path.basename(relative, ".md");
    if (!stems.has(stem)) stems.set(stem, new Set());
    stems.get(stem)!.add(relative);
  }
  for (const [relative, { frontmatter: fm, body }] of proposed) {
    for (const tag of fm.tags ?? [])
      if (
        typeof tag === "string" &&
        tag.startsWith("pillar-") &&
        !tags.has(tag)
      )
        throw new Error("unregistered_pillar: " + tag);
    for (const block of fm.blocks ?? [])
      if (
        !/^TaskNotes\/Tasks\/[^/]+\.md$/.test(block.task) ||
        !(proposed.has(block.task) || exists(confined(ctx.vault, block.task)))
      )
        throw new Error("unresolved_daily_task");
    for (const match of (body + JSON.stringify(fm)).matchAll(
      /\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]/g,
    )) {
      const target = match[1];
      let resolved = false;
      if (target.includes("/")) {
        const candidate = path.posix.extname(target) ? target : target + ".md";
        resolved =
          proposed.has(candidate) || exists(confined(ctx.vault, candidate));
      } else resolved = stems.get(target)?.size === 1;
      if (!resolved) throw new Error("unresolved_link: " + target);
    }
  }
}
export function propose(
  ctx: RuntimeContext,
  changes: Change[],
  purpose = "review",
  ingestion?: Metadata,
  observedDependencies: Record<string, string> = {},
  knowledgeReview?: Metadata,
) {
  runtimeContext(ctx.vault, ctx.state);
  if (
    !Array.isArray(changes) ||
    !changes.length ||
    changes.length > MAX_RECORDS
  )
    throw new Error("Proposals require 1–500 records");
  const names = changes.map((c) => c.path.toLowerCase());
  if (new Set(names).size !== names.length)
    throw new Error("Duplicate or case-colliding paths");
  for (const change of changes) checkRecord(ctx, change, false, changes);
  validateRelationships(ctx, changes);
  const dependencies: Record<string, string | null> = {};
  for (const relative of new Set([
    "System/Memory.md",
    "System/Life-Roadmap.md",
    ...changes.map((c) => "_types/" + schemaFor(c.path) + ".md"),
  ]))
    dependencies[relative] = sha256(raw(confined(ctx.vault, relative)));
  for (const [relative, expected] of Object.entries(observedDependencies)) {
    schemaFor(relative);
    if (
      !/^[a-f0-9]{64}$/.test(expected) ||
      sha256(raw(confined(ctx.vault, relative))) !== expected
    )
      throw new Error("stale_knowledge_evidence: " + relative);
    dependencies[relative] = expected;
  }
  const proposal: Proposal = {
    contract_version: "2",
    vault_root: ctx.vault,
    vault_id: readJSON(confined(ctx.vault, ".chrysalis-vault.json")).vault_id,
    purpose,
    records: changes,
    dependencies,
    ...(ingestion ? { ingestion } : {}),
    ...(knowledgeReview ? { knowledge: knowledgeReview } : {}),
  };
  if (Buffer.byteLength(canonical(proposal)) > MAX_REQUEST_BYTES)
    throw new Error("Proposal exceeds 4 MiB");
  const key = digest(proposal);
  atomicJSON(confined(vaultState(ctx), "proposals/" + key + ".json"), proposal);
  return {
    status: "review_required",
    proposal_digest: key,
    proposal,
    required_note_reviews: newNoteReviews(proposal),
  };
}
export function newNoteReviews(proposal: Proposal) {
  return proposal.records
    .filter(
      (item) =>
        /^Slipbox\/[^/]+\.md$/.test(item.path) && item.if_revision === null,
    )
    .map((item) => ({ path: item.path, revision: sha256(item.document) }));
}
export function loadProposal(ctx: RuntimeContext, key: string): Proposal {
  if (!/^[a-f0-9]{64}$/.test(key)) throw new Error("Invalid proposal digest");
  const proposal = readJSON(
    confined(vaultState(ctx), "proposals/" + key + ".json"),
  );
  if (
    digest(proposal) !== key ||
    proposal.contract_version !== "2" ||
    proposal.vault_root !== ctx.vault ||
    proposal.vault_id !==
      readJSON(confined(ctx.vault, ".chrysalis-vault.json")).vault_id
  )
    throw new Error("Proposal identity or digest changed; review again");
  return proposal;
}
function dependencies(ctx: RuntimeContext, p: Proposal, resume = false) {
  for (const [relative, expected] of Object.entries(p.dependencies)) {
    const current = exists(confined(ctx.vault, relative))
      ? sha256(raw(confined(ctx.vault, relative)))
      : null;
    const own = p.records.find((c) => c.path === relative);
    if (
      current !== expected &&
      !(resume && own && current === sha256(own.document))
    )
      throw new Error("stale_dependency: " + relative + "; review again");
  }
}
/** Operator boundary: this function is never dispatched as a model operation. */
export function approve(
  ctx: RuntimeContext,
  key: string,
  evidence: string,
  noteReviews: Array<{ path: string; revision: string }> = [],
) {
  if (
    typeof evidence !== "string" ||
    !evidence.trim() ||
    evidence.length > 1000
  )
    throw new Error("Explicit operator approval evidence required");
  const proposal = loadProposal(ctx, key);
  if (
    !Array.isArray(noteReviews) ||
    !equal(noteReviews, newNoteReviews(proposal))
  )
    throw new Error(
      "zettel_review_required: review and confirm each new atomic note",
    );
  dependencies(ctx, proposal);
  for (const item of proposal.records)
    checkRecord(ctx, item, false, proposal.records);
  validateRelationships(ctx, proposal.records);
  atomicJSON(confined(vaultState(ctx), "approvals/" + key + ".json"), {
    proposal_digest: key,
    vault_root: ctx.vault,
    vault_id: proposal.vault_id,
    approved_at: nowStamp(configuredZone(ctx), ctx.now),
    evidence,
    note_reviews: noteReviews,
  });
  return { status: "approved", proposal_digest: key };
}
export async function apply(
  ctx: RuntimeContext,
  key: string,
  options: { failAfter?: number; beforeCommit?: () => void } = {},
) {
  const proposal = loadProposal(ctx, key),
    external = vaultState(ctx),
    approvalPath = confined(external, "approvals/" + key + ".json");
  if (!exists(approvalPath))
    throw new Error("approval_required: operator receipt is absent");
  const receipt = readJSON(approvalPath);
  if (
    receipt.proposal_digest !== key ||
    receipt.vault_root !== ctx.vault ||
    receipt.vault_id !== proposal.vault_id
  )
    throw new Error("approval_mismatch");
  if (!equal(receipt.note_reviews ?? [], newNoteReviews(proposal)))
    throw new Error(
      "zettel_review_required: exact per-note approval evidence is absent",
    );
  return withLock(confined(external, "locks"), "vault-writer", () => {
    dependencies(ctx, proposal, true);
    validateRelationships(ctx, proposal.records);
    const ledgerPath = confined(external, "applications/" + key + ".json"),
      ledger = exists(ledgerPath) ? readJSON(ledgerPath) : { applied: {} };
    const pending: Array<ReturnType<typeof checkRecord> & { item: Change }> =
      [];
    for (const item of proposal.records) {
      const row = checkRecord(ctx, item, true, proposal.records);
      if (item.path in ledger.applied) {
        if (!exists(row.target) || sha256(raw(row.target)) !== row.expected)
          throw new Error("applied_record_changed");
      } else if (
        exists(row.target) &&
        sha256(raw(row.target)) === row.expected
      ) {
        ledger.applied[item.path] = row.expected;
        atomicJSON(ledgerPath, ledger);
      } else pending.push({ ...row, item });
    }
    let count = 0;
    for (const row of pending) {
      if (options.failAfter !== undefined && count >= options.failAfter)
        return {
          status: "interrupted",
          proposal_digest: key,
          applied: ledger.applied,
        };
      dependencies(ctx, proposal, true);
      validateRelationships(ctx, proposal.records);
      checkRecord(ctx, row.item, false, proposal.records);
      atomic(
        row.target,
        row.item.document,
        row.item.if_revision,
        options.beforeCommit,
      );
      if (sha256(raw(row.target)) !== row.expected)
        throw new Error("postimage_mismatch");
      ledger.applied[row.item.path] = row.expected;
      atomicJSON(ledgerPath, ledger);
      count++;
    }
    for (const item of proposal.records) {
      checkRecord(ctx, item, true, proposal.records);
      if (sha256(raw(confined(ctx.vault, item.path))) !== sha256(item.document))
        throw new Error("postimage_mismatch");
    }
    validateRelationships(ctx, proposal.records);
    ledger.status = "verified";
    atomicJSON(ledgerPath, ledger);
    return {
      status: "verified",
      proposal_digest: key,
      applied: ledger.applied,
    };
  });
}
