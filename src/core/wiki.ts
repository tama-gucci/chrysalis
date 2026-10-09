// Reviewed knowledge compilation follows the MIT-licensed karpathy-llm-wiki workflow.
// See resources/notices/karpathy-llm-wiki.LICENSE.txt. No operation here applies or approves records.
import { randomUUID } from "node:crypto";
import {
  collection,
  parse,
  schemaFor,
  serializeRecord,
  sanitizeUntrusted,
  recordPath,
} from "../storage/records.ts";
import {
  confined,
  exists,
  sha256,
  canonical,
} from "../platforms/filesystem.ts";
import { configuredZone } from "./runtime.ts";
import { stamp, serialize } from "../time/timezone.ts";
import {
  capturedEvidence,
  literalMatcher,
  evidenceCandidates,
  normalizeEvidence,
  visibleLines,
} from "./evidence.ts";
import type {
  Change,
  Metadata,
  Observation,
  RuntimeContext,
} from "../contracts/types.ts";

export const KNOWLEDGE_INDEX = "System/Knowledge-Index.md";
export const KNOWLEDGE_LOG = "System/Knowledge-Log.md";
const MAX_FIDELITY_SCAN_BYTES = 64 * 1024 * 1024;
const MAX_FIDELITY_COMPARISONS = 100000;
const isNote = (relative: string) => /^Slipbox\/[^/]+\.md$/.test(relative);
const isSource = (relative: string) => /^Sources\/[^/]+\.md$/.test(relative);
const isAnswer = (row: Observation) =>
  /^System\/Knowledge-Answer-[^/]+\.md$/.test(row.path) &&
  row.frontmatter.record_kind === "knowledge_answer";
const options = (args: Metadata, allowed: string[]) => {
  for (const key of Object.keys(args))
    if (!allowed.includes(key))
      throw new Error("Unsupported knowledge argument: " + key);
};
const bounded = (value: any, fallback: number, maximum: number) => {
  const n = value ?? fallback;
  if (!Number.isInteger(n) || n < 1 || n > maximum)
    throw new Error("Use a bounded knowledge limit");
  return n;
};
const link = (relative: string) => "[[" + relative.replace(/\.md$/, "") + "]]";
const label = (value: any, maximum = 300) =>
  String(value ?? "")
    .replace(/[\r\n|]/g, " ")
    .slice(0, maximum);
const contentHash = (row: Observation) =>
  sha256(
    canonical({
      body: normalizeEvidence(row.body),
      title: row.frontmatter.title ?? null,
      summary: row.frontmatter.summary ?? null,
      knowledge_status: row.frontmatter.knowledge_status ?? null,
      provenance_kind: row.frontmatter.provenance_kind ?? null,
      source_ref: row.frontmatter.source_ref ?? null,
      source_refs: row.frontmatter.source_refs ?? [],
    }),
  );

function rows(ctx: RuntimeContext, changes: Change[] = []): Observation[] {
  if (ctx.signal?.aborted) throw new Error("Cancelled");
  const found = ["zettels", "sources", "system"].flatMap((name) =>
    collection(ctx.vault, name),
  );
  const all = new Map(found.map((row) => [row.path, row]));
  const seen = new Set<string>();
  if (!Array.isArray(changes) || changes.length > 500)
    throw new Error("Use at most 500 complete knowledge changes");
  for (const change of changes) {
    if (!change || typeof change.path !== "string")
      throw new Error("Use complete knowledge records");
    schemaFor(change.path);
    recordPath(ctx.vault, change.path);
    if (
      typeof change.document !== "string" ||
      Buffer.byteLength(change.document) > 1024 * 1024 ||
      !(
        change.if_revision === null || /^[a-f0-9]{64}$/.test(change.if_revision)
      )
    )
      throw new Error("Use complete records and raw revisions");
    if (seen.has(change.path.toLowerCase()))
      throw new Error("Duplicate knowledge post-image");
    seen.add(change.path.toLowerCase());
    all.set(change.path, {
      ...parse(change.document),
      path: change.path,
      document: change.document,
      revision: sha256(change.document),
    });
  }
  const selected = [...all.values()].filter(
    (row) =>
      isNote(row.path) ||
      isSource(row.path) ||
      isAnswer(row) ||
      [KNOWLEDGE_INDEX, KNOWLEDGE_LOG].includes(row.path),
  );
  if (
    selected.length > 5000 ||
    selected.reduce((sum, row) => sum + Buffer.byteLength(row.document), 0) >
      32 * 1024 * 1024
  )
    throw new Error("Knowledge scan budget exceeded; narrow the collection");
  return selected.sort((a, b) => a.path.localeCompare(b.path));
}

function sourcePaths(row: Observation): string[] {
  const refs = new Set<string>();
  if (
    row.frontmatter.source_refs !== undefined &&
    !Array.isArray(row.frontmatter.source_refs)
  )
    throw new Error("source_refs must be an array");
  for (const value of [
    row.frontmatter.source_ref,
    ...(row.frontmatter.source_refs ?? []),
  ]) {
    if (value == null) continue;
    if (
      typeof value !== "string" ||
      !/^\[\[Sources\/[^/\]|#]+(?:\.md)?\]\]$/.test(value)
    )
      throw new Error("Use exact Sources WikiLinks for knowledge provenance");
    refs.add(value.slice(2, -2).replace(/\.md$/, "") + ".md");
  }
  return [...refs];
}

/** Full body search, bounded results and no state side effects. Aliases are explicit literal terms. */
export function searchKnowledge(ctx: RuntimeContext, args: Metadata) {
  options(args, ["query", "aliases", "include_sources", "limit", "page"]);
  if (
    typeof args.query !== "string" ||
    !args.query.trim() ||
    args.query.length > 2000
  )
    throw new Error("Use a bounded knowledge query");
  const aliases = args.aliases ?? [];
  if (
    !Array.isArray(aliases) ||
    aliases.length > 20 ||
    aliases.some(
      (item) => typeof item !== "string" || !item.trim() || item.length > 100,
    )
  )
    throw new Error("Use at most 20 literal aliases");
  if (
    args.include_sources !== undefined &&
    typeof args.include_sources !== "boolean"
  )
    throw new Error("include_sources must be boolean");
  const terms = [
    ...new Set(
      [
        args.query.trim(),
        ...(args.query.match(/[\p{L}\p{N}][\p{L}\p{N}-]*/gu) ?? []),
        ...aliases,
      ].map((term) => term.toLocaleLowerCase("en")),
    ),
  ];
  const size = bounded(args.limit, 10, 50),
    page = args.page ?? 0;
  if (!Number.isInteger(page) || page < 0)
    throw new Error("Use a nonnegative page");
  const candidates = rows(ctx).filter(
    (row) =>
      isNote(row.path) ||
      isAnswer(row) ||
      (args.include_sources && isSource(row.path)),
  );
  const matches = candidates
    .map((row) => {
      const text = row.document.toLocaleLowerCase("en"),
        matched = terms.filter((term) => text.includes(term));
      const first = matched.length
        ? Math.min(...matched.map((term) => text.indexOf(term)))
        : 0;
      return { row, matched, first };
    })
    .filter(({ matched }) => matched.length)
    .sort(
      (a, b) =>
        b.matched.length - a.matched.length ||
        a.row.path.localeCompare(b.row.path),
    );
  return {
    status: matches.length ? "matches" : "empty",
    total_matches: matches.length,
    records: matches
      .slice(page * size, (page + 1) * size)
      .map(({ row, matched, first }) => ({
        path: row.path,
        revision: row.revision,
        title: label(row.frontmatter.title ?? row.path),
        summary: label(row.frontmatter.summary ?? "", 500),
        knowledge_status: row.frontmatter.knowledge_status ?? "unclassified",
        kind: isAnswer(row)
          ? "answer_snapshot"
          : isSource(row.path)
            ? "source"
            : "atomic_note",
        matched_terms: matched,
        excerpt: sanitizeUntrusted(
          row.document.slice(Math.max(0, first - 80), first + 400),
        ),
      })),
    next_page: matches.length > (page + 1) * size ? page + 1 : null,
    scope: {
      full_text: true,
      records_scanned: candidates.length,
      include_sources: !!args.include_sources,
      semantic_search: false,
    },
  };
}

/** Lint stored knowledge or pending complete post-images. No repair, log or receipt is written. */
export function lintKnowledge(ctx: RuntimeContext, args: Metadata) {
  options(args, ["paths", "records", "limit"]);
  const all = rows(ctx, args.records ?? []),
    byPath = new Map(all.map((row) => [row.path, row]));
  const notes = all.filter((row) => isNote(row.path)),
    answers = all.filter(isAnswer);
  if (
    args.paths !== undefined &&
    (!Array.isArray(args.paths) ||
      args.paths.length > 500 ||
      args.paths.some((p) => !byPath.has(p)))
  )
    throw new Error("Use existing or proposed knowledge paths");
  const selected = new Set<string>(
    args.paths ?? notes.concat(answers).map((row) => row.path),
  );
  const issues: Metadata[] = [],
    maximum = bounded(args.limit, 100, 1000);
  let total = 0;
  let fidelityScanBytes = 0,
    fidelityComparisons = 0,
    fidelityIncomplete = false;
  const payloadCache = new Map<
    string,
    Array<{ text: string; bytes: number }>
  >();
  const issue = (code: string, relative: string, detail: Metadata = {}) => {
    total++;
    if (issues.length < maximum)
      issues.push({ code, path: relative, ...detail });
  };
  const usedSources = new Set<string>(),
    inbound = new Set<string>();
  const inspectLinks = (row: Observation) => {
    if (!selected.has(row.path)) return;
    for (const match of (row.body + JSON.stringify(row.frontmatter)).matchAll(
      /\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]/g,
    )) {
      const target = match[1],
        relative = /\.[^/]+$/.test(target) ? target : target + ".md";
      if (target.includes("/") && !byPath.has(relative)) {
        try {
          if (!exists(confined(ctx.vault, relative)))
            issue("broken_link", row.path, { target });
        } catch {
          issue("unsafe_link", row.path, { target });
        }
      }
    }
  };
  for (const row of notes.concat(answers)) {
    inspectLinks(row);
    for (const match of (row.body + JSON.stringify(row.frontmatter)).matchAll(
      /\[\[(Slipbox\/[^\]|#]+)(?:[|#][^\]]*)?\]\]/g,
    )) {
      const target = match[1].replace(/\.md$/, "") + ".md";
      if (target !== row.path) inbound.add(target);
    }
    if (isAnswer(row)) {
      if (!selected.has(row.path)) continue;
      if (
        !Array.isArray(row.frontmatter.cited_notes) ||
        !row.frontmatter.cited_notes.length
      )
        issue("answer_missing_citations", row.path);
      for (const citation of Array.isArray(row.frontmatter.cited_notes)
        ? row.frontmatter.cited_notes
        : []) {
        if (
          !citation ||
          typeof citation.path !== "string" ||
          !/^[a-f0-9]{64}$/.test(citation.revision ?? "") ||
          !/^[a-f0-9]{64}$/.test(citation.content_sha256 ?? "")
        ) {
          issue("invalid_answer_citation", row.path);
          continue;
        }
        const source = byPath.get(citation.path);
        if (!source || !isNote(source.path))
          issue("answer_missing_note", row.path, { target: citation.path });
        else if (
          citation.content_sha256
            ? contentHash(source) !== citation.content_sha256
            : source.revision !== citation.revision
        )
          issue("answer_source_changed", row.path, {
            target: citation.path,
            action: "Review the snapshot; do not rewrite it automatically",
          });
      }
      continue;
    }
    let refs: string[];
    try {
      refs = sourcePaths(row);
    } catch (e: any) {
      if (selected.has(row.path))
        issue("invalid_source_reference", row.path, { message: e.message });
      continue;
    }
    refs.forEach((relative) => usedSources.add(relative));
    if (!selected.has(row.path)) continue;
    if (!row.frontmatter.summary) issue("missing_summary", row.path);
    if (
      !visibleLines(row.body).some((line) => line.trim() && !/^#+\s/.test(line))
    )
      issue("empty_note", row.path);
    if (
      !refs.length &&
      !["personal", "inference"].includes(row.frontmatter.provenance_kind)
    )
      issue("missing_provenance", row.path);
    const evidence: Array<{ text: string; bytes: number }> = [];
    for (const relative of refs) {
      const source = byPath.get(relative);
      if (!source || !isSource(relative)) {
        issue("missing_evidence_source", row.path, { target: relative });
        continue;
      }
      let captured = payloadCache.get(relative);
      if (!captured) {
        captured = capturedEvidence(source.body).map((text) => ({
          text,
          bytes: Buffer.byteLength(text),
        }));
        payloadCache.set(relative, captured);
      }
      if (!captured.length)
        issue("evidence_unavailable", row.path, { target: relative });
      evidence.push(...captured);
      if (!source.frontmatter.extraction_coverage?.status)
        issue("unknown_evidence_coverage", row.path, { target: relative });
      if (
        source.frontmatter.extraction_coverage?.status &&
        !["complete", "not_applicable"].includes(
          source.frontmatter.extraction_coverage.status,
        )
      )
        issue("partial_evidence", row.path, {
          target: relative,
          coverage: source.frontmatter.extraction_coverage.status,
        });
    }
    if (refs.length && evidence.length) {
      const literals = evidenceCandidates(row.body);
      for (let i = 0; i < literals.length; i++) {
        const literal = literals[i],
          matches = literalMatcher(literal);
        let supported = false,
          incomplete = false;
        for (const payload of evidence) {
          if (
            fidelityScanBytes + payload.bytes > MAX_FIDELITY_SCAN_BYTES ||
            fidelityComparisons >= MAX_FIDELITY_COMPARISONS
          ) {
            incomplete = true;
            break;
          }
          fidelityScanBytes += payload.bytes;
          fidelityComparisons++;
          if (matches(payload.text)) {
            supported = true;
            break;
          }
        }
        if (incomplete) {
          fidelityIncomplete = true;
          issue("fidelity_budget_exceeded", row.path, {
            unchecked_literals: literals.length - i,
            action: "Narrow note paths/evidence; remaining claims need review",
          });
          break;
        }
        if (!supported)
          issue("fidelity_suspect", row.path, {
            literal,
            verdict: "needs_context_review",
          });
      }
    }
    if (
      ["disputed", "outdated"].includes(row.frontmatter.knowledge_status) &&
      !/>\s*\*\*Status: (Disputed|Outdated)\*\*/.test(row.body)
    )
      issue("missing_status_explanation", row.path);
    if (row.frontmatter.knowledge_status === "disputed" && refs.length < 2)
      issue("dispute_needs_both_sources", row.path);
    for (const match of row.body.matchAll(
      /^>\s*\*\*Status:\s*(Disputed|Outdated)\*\*([^\n]*)(?:\n([^\n]*))?/gm,
    )) {
      if (
        (match[1] === "Outdated" && !/\d{4}-\d\d-\d\d/.test(match[2])) ||
        !/^>\s*\S/.test(match[3] ?? "")
      )
        issue("malformed_status_block", row.path);
    }
  }
  for (const row of notes)
    if (selected.has(row.path) && !inbound.has(row.path))
      issue("orphan_note", row.path);
  const log = byPath.get(KNOWLEDGE_LOG);
  if (log && !Array.isArray(log.frontmatter.entries))
    issue("invalid_log", KNOWLEDGE_LOG);
  const noMaterial = new Set<string>(
    (Array.isArray(log?.frontmatter.entries) ? log.frontmatter.entries : [])
      .filter(
        (entry: Metadata) =>
          Array.isArray(entry?.dispositions) &&
          entry.dispositions.includes("no_material"),
      )
      .flatMap((entry: Metadata) =>
        Array.isArray(entry.source_paths)
          ? entry.source_paths.filter(
              (relative: string) =>
                entry.source_revisions?.[relative] ===
                byPath.get(relative)?.revision,
            )
          : [],
      ),
  );
  for (const row of all.filter((row) => isSource(row.path)))
    if (!usedSources.has(row.path) && !noMaterial.has(row.path))
      issue("uncompiled_source", row.path);
  const index = byPath.get(KNOWLEDGE_INDEX);
  if (!index) issue("missing_index", KNOWLEDGE_INDEX);
  else {
    const entries = index.frontmatter.entries;
    if (!Array.isArray(entries)) issue("invalid_index", KNOWLEDGE_INDEX);
    else {
      const indexed = new Map<string, Metadata>();
      for (const entry of entries) {
        if (!entry || typeof entry.path !== "string") {
          issue("invalid_index_entry", KNOWLEDGE_INDEX);
          continue;
        }
        if (indexed.has(entry.path))
          issue("duplicate_index_entry", KNOWLEDGE_INDEX, {
            target: entry.path,
          });
        indexed.set(entry.path, entry);
        const target = byPath.get(entry.path);
        if (!target || !(isNote(target.path) || isAnswer(target)))
          issue("missing_index_target", KNOWLEDGE_INDEX, {
            target: entry.path,
          });
        else if (
          entry.revision !== target.revision ||
          entry.title !== label(target.frontmatter.title ?? target.path) ||
          entry.summary !== label(target.frontmatter.summary ?? "", 500)
        )
          issue("stale_index_entry", KNOWLEDGE_INDEX, { target: entry.path });
      }
      for (const row of notes.concat(answers))
        if (!indexed.has(row.path)) issue("unindexed_note", row.path);
    }
  }
  return {
    status: total ? "review_required" : "ok",
    findings: issues,
    total_findings: total,
    truncated: total > issues.length,
    scope: {
      stored_or_proposed: true,
      notes_checked: selected.size,
      full_inventory: true,
      writes: false,
      fidelity_scan_bytes: fidelityScanBytes,
      fidelity_scan_budget_bytes: MAX_FIDELITY_SCAN_BYTES,
      fidelity_comparisons: fidelityComparisons,
      fidelity_comparison_budget: MAX_FIDELITY_COMPARISONS,
      fidelity_incomplete: fidelityIncomplete,
    },
    judgment_required: [
      "atomicity",
      "entailment",
      "contradictions",
      "missing_concepts",
      "link_relevance",
      "source_authority",
    ],
    coverage:
      "High-signal numeric spellings, ISO dates and quotes of at least 15 characters. Small integers, currency/sign forms, paraphrases and truth require semantic review. Status explanations are checked; annotation dates are bookkeeping.",
  };
}

/** Add a complete index and append-only log to the user's proposed change set, never to the vault. */
export function prepareKnowledge(ctx: RuntimeContext, args: Metadata) {
  options(args, ["records", "now", "dispositions", "source_paths"]);
  const now = serialize(
    stamp(args.now, configuredZone(ctx)),
    configuredZone(ctx),
  );
  const records: Change[] = args.records ?? [];
  if (
    !Array.isArray(records) ||
    records.length > 498 ||
    records.some((record) => !record || typeof record.path !== "string")
  )
    throw new Error(
      "Use at most 498 complete records; index and log need room",
    );
  const dispositions = args.dispositions;
  if (
    !Array.isArray(dispositions) ||
    !dispositions.length ||
    dispositions.length > 3 ||
    dispositions.some(
      (d) =>
        ![
          "new",
          "update",
          "disputed",
          "no_material",
          "archive",
          "lint",
        ].includes(d),
    ) ||
    new Set(dispositions).size !== dispositions.length ||
    (dispositions.includes("no_material") && dispositions.length !== 1)
  )
    throw new Error(
      "Declare explicit knowledge dispositions; no_material is exclusive",
    );
  const sources: string[] = args.source_paths ?? [];
  if (
    !Array.isArray(sources) ||
    sources.length > 100 ||
    sources.some((p) => !isSource(p))
  )
    throw new Error("Use bounded exact source paths");
  if (
    records.some((record) =>
      [KNOWLEDGE_INDEX, KNOWLEDGE_LOG].includes(record.path),
    )
  )
    throw new Error(
      "Knowledge index/log are generated from the reviewed post-images",
    );
  if (
    dispositions.includes("no_material") &&
    (records.some((record) => isNote(record.path)) || !sources.length)
  )
    throw new Error(
      "No-material compilation needs sources and creates/changes no atomic notes",
    );
  const observed = rows(ctx),
    dependencies = Object.fromEntries(
      observed.map((row) => [row.path, row.revision]),
    );
  let all = rows(ctx, records),
    byPath = new Map(all.map((row) => [row.path, row]));
  if (sources.some((relative) => !byPath.has(relative)))
    throw new Error("Knowledge source is absent from the stored/proposed set");
  const changes = records.map((record) => ({ ...record }));
  for (const record of changes) {
    const row = byPath.get(record.path);
    if (!row || !isAnswer(row)) continue;
    if (record.if_revision !== null || !dispositions.includes("archive"))
      throw new Error("Answers are new explicit point-in-time archives");
    const citations = row.frontmatter.cited_notes;
    if (
      !Array.isArray(citations) ||
      !citations.length ||
      citations.length > 100
    )
      throw new Error("Saved answers require cited atomic notes");
    record.document = serializeRecord(
      {
        ...row.frontmatter,
        archived_at: now,
        cited_notes: citations.map((citation) => {
          if (!citation || typeof citation.path !== "string")
            throw new Error("Use exact cited note paths");
          const note = byPath.get(citation.path);
          if (!note || !isNote(note.path))
            throw new Error("Answer citation requires an exact atomic note");
          return {
            path: note.path,
            revision: note.revision,
            content_sha256: contentHash(note),
          };
        }),
      },
      row.body,
    );
  }
  all = rows(ctx, changes);
  byPath = new Map(all.map((row) => [row.path, row]));
  const notes = all.filter((row) => isNote(row.path) || isAnswer(row));
  const entries = notes.map((row) => ({
    path: row.path,
    title: label(row.frontmatter.title ?? row.path),
    summary: label(row.frontmatter.summary ?? "", 500),
    revision: row.revision,
    updated:
      row.frontmatter.content_updated_at ??
      row.frontmatter.archived_at ??
      row.frontmatter.dateCreated ??
      null,
    kind: isAnswer(row) ? "answer_snapshot" : "atomic_note",
    knowledge_status: row.frontmatter.knowledge_status ?? "unclassified",
  }));
  const previousIndex = observed.find((row) => row.path === KNOWLEDGE_INDEX);
  const indexBody =
    "# Knowledge index\n\n| Note | Summary | Knowledge updated |\n|---|---|---|\n" +
    entries
      .map(
        (entry) =>
          "| " +
          link(entry.path) +
          " | " +
          (entry.kind === "answer_snapshot" ? "[Archived] " : "") +
          entry.summary.replace(/\[/g, "&#91;") +
          " | " +
          (entry.updated ?? "Unknown") +
          " |",
      )
      .join("\n") +
    "\n";
  const indexDocument = serializeRecord(
    { type: "system_state", record_kind: "knowledge_index", entries },
    indexBody,
  );
  if (!previousIndex || previousIndex.document !== indexDocument)
    changes.push({
      path: KNOWLEDGE_INDEX,
      if_revision: previousIndex?.revision ?? null,
      document: indexDocument,
    });
  const previousLog = observed.find((row) => row.path === KNOWLEDGE_LOG);
  const oldEntries = previousLog?.frontmatter.entries ?? [];
  if (!Array.isArray(oldEntries))
    throw new Error("Malformed knowledge journal; review before appending");
  const entry = {
    id: randomUUID(),
    at: now,
    dispositions,
    source_paths: sources,
    source_revisions: Object.fromEntries(
      sources.map((relative) => [relative, byPath.get(relative)!.revision]),
    ),
    paths: records.map((record) => record.path),
  };
  const oldBody = previousLog?.body ?? "# Knowledge log\n";
  const body =
    oldBody +
    (oldBody.endsWith("\n") ? "" : "\n") +
    "\n## " +
    now +
    " | " +
    dispositions.join(", ") +
    "\n" +
    "- Records: " +
    (entry.paths.map(link).join(", ") || "No note changes") +
    "\n- Sources: " +
    (sources.map(link).join(", ") || "None") +
    "\n";
  changes.push({
    path: KNOWLEDGE_LOG,
    if_revision: previousLog?.revision ?? null,
    document: serializeRecord(
      {
        ...previousLog?.frontmatter,
        type: "system_state",
        record_kind: "knowledge_log",
        entries: [...oldEntries, entry],
      },
      body,
    ),
  });
  if (changes.length > 500)
    throw new Error("Knowledge batch including index/log exceeds 500 records");
  const lint = lintKnowledge(ctx, { records: changes });
  return {
    changes,
    dependencies,
    review: {
      dispositions,
      lint,
      atomic_notes: changes
        .filter((record) => isNote(record.path))
        .map((record) => ({
          path: record.path,
          action: record.if_revision === null ? "create" : "update",
          revision: sha256(record.document),
        })),
      original_bytes_changed: false,
      approval_required: true,
    },
  };
}
