import { randomUUID } from "node:crypto";
import { configuredZone } from "./runtime.ts";
import {
  collection,
  readRecord,
  change,
  serializeRecord,
  sanitizeUntrusted,
} from "../storage/records.ts";
import { confined, exists, sha256 } from "../platforms/filesystem.ts";
import { stamp, serialize, dateOnly } from "../time/timezone.ts";
import { MODALITIES } from "../contracts/types.ts";
import { taskDefaults } from "../contracts/fields.ts";
import type { RuntimeContext, Metadata, Change } from "../contracts/types.ts";

export function taskDocument(ctx: RuntimeContext, args: Metadata): Change {
  const timezone = configuredZone(ctx);
  if (args.timezone && args.timezone !== timezone)
    throw new Error("Timezone must match Memory");
  const now = stamp(args.now, timezone);
  const modality = args.modality ?? "analytical",
    base = args.base_minutes ?? 45;
  if (
    !MODALITIES.includes(modality) ||
    typeof base !== "number" ||
    !Number.isFinite(base) ||
    base <= 0 ||
    base > 1440
  )
    throw new Error("Invalid task modality or estimate");
  if (
    typeof args.title !== "string" ||
    !args.title.trim() ||
    args.title.length > 500
  )
    throw new Error("Use a bounded task title");
  const multiplier =
    readRecord(ctx.vault, "System/Memory.md").frontmatter
      .cognitive_modality_defaults?.[modality]?.multiplier ?? 1;
  if (multiplier < 0.2 || multiplier > 2)
    throw new Error("Invalid modality multiplier");
  const projects = args.projects ?? [],
    links = new Set<string>(args.linked_zettels ?? []);
  if (!Array.isArray(projects)) throw new Error("Use native projects links");
  for (const project of projects) {
    if (!/^\[\[Projects\/[a-z0-9-]+\/Roadmap\]\]$/.test(project))
      throw new Error("Use explicit project WikiLinks");
    const fm = readRecord(ctx.vault, project.slice(2, -2) + ".md").frontmatter;
    for (const link of fm.linked_zettels ?? []) links.add(link);
  }
  const due = args.due ?? null;
  if (due) dateOnly(due);
  const prefix = String(due ?? now.toPlainDate().toString()).replace(/-/g, "");
  const slug =
    args.title
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "")
      .slice(0, 60) || "task";
  const relative =
    args.path ?? "TaskNotes/Tasks/" + prefix + "-" + slug + ".md";
  if (
    !/^TaskNotes\/Tasks\/[a-z0-9-]+\.md$/.test(relative) ||
    exists(confined(ctx.vault, relative))
  )
    throw new Error("Capture requires a fresh task path");
  const fields = args.fields ?? {};
  for (const key of Object.keys(fields))
    if (
      ["type", "id", "title", "status", "scheduled", "dateCreated"].includes(
        key,
      ) ||
      key.startsWith("googleCalendar")
    )
      throw new Error("Capture cannot override protected defaults");
  const fm = {
    ...taskDefaults(),
    type: "task",
    id: randomUUID(),
    title: args.title,
    dateCreated: serialize(now, timezone),
    due,
    priority: args.priority ?? "normal",
    modality,
    timeEstimate: Math.round(base * multiplier),
    tags: [...new Set([...(args.tags ?? []), "task"])].sort(),
    linked_zettels: [...links].sort(),
    projects,
    googleCalendarEventId: null,
    ...fields,
  };
  return {
    path: relative,
    if_revision: null,
    document: serializeRecord(fm, args.body ?? "# " + args.title + "\n"),
  };
}
export function horizon(ctx: RuntimeContext, args: Metadata) {
  if ((args.horizon_days ?? 14) !== 14)
    throw new Error("The supported horizon is 14 days");
  const current = stamp(args.now, configuredZone(ctx)).toPlainDate(),
    changes: Change[] = [];
  for (const row of collection(ctx.vault, "projects")) {
    if (row.frontmatter.status !== "active") continue;
    const fm = structuredClone(row.frontmatter);
    let modified = false;
    for (const item of fm.deliverables ?? []) {
      if (["done", "archived"].includes(item.status) || item.task_ref) continue;
      if (
        item.due &&
        dateOnly(item.due).toString() > current.add({ days: 14 }).toString()
      )
        continue;
      const due = item.due ?? null,
        relative =
          "TaskNotes/Tasks/" +
          (due ?? current.toString()).replace(/-/g, "") +
          "-" +
          fm.project_id +
          "-" +
          item.id +
          ".md";
      const fields = {
        deliverable_id: item.id,
        source_ref: item.source_ref ?? fm.source_ref ?? null,
        horizon_bucket: !due
          ? "uncertain"
          : due < current.toString()
            ? "overdue"
            : "imminent",
        date_uncertain: !due,
        review_required: !due || due < current.toString(),
        urgency_tier: item.tier ?? 2,
      };
      changes.push(
        taskDocument(ctx, {
          title: item.title,
          now: args.now,
          timezone: configuredZone(ctx),
          due,
          projects: ["[[" + row.path.slice(0, -3) + "]]"],
          tags: fm.tags ?? [],
          modality: item.modality ?? "analytical",
          base_minutes: item.base_minutes ?? 45,
          path: relative,
          fields,
        }),
      );
      item.task_ref = "[[" + relative.slice(0, -3) + "]]";
      modified = true;
    }
    if (modified) changes.push(change(row, fm));
  }
  return changes;
}
export function reconcile(ctx: RuntimeContext, args: Metadata) {
  const row = readRecord(ctx.vault, args.path);
  if (!/^Projects\/[a-z0-9-]+\/Roadmap.md$/.test(row.path))
    throw new Error("Expected project roadmap");
  if (!Array.isArray(args.deliverables) || args.deliverables.length > 500)
    throw new Error("Use bounded deliverables");
  const fm = structuredClone(row.frontmatter),
    original = fm.deliverables ?? [],
    incoming = args.deliverables;
  const ids = incoming.map((d) => d.id);
  if (
    ids.some((id) => typeof id !== "string" || !id) ||
    new Set(ids).size !== ids.length
  )
    throw new Error("Unique deliverable IDs required");
  const diff = {
    added: [] as Metadata[],
    modified: [] as Metadata[],
    unchanged: [] as Metadata[],
    dropped: [] as Metadata[],
    diagnostics: [] as Metadata[],
  };
  const complete = (args.extraction_status ?? "complete") === "complete";
  const authoritative =
    args.authoritative_replacement === true &&
    complete &&
    !!(args.source_scope || args.source_ref);
  for (const prior of original) {
    const next = incoming.find((d) => d.id === prior.id);
    const sameSource = args.source_scope
      ? prior.source_scope === args.source_scope
      : args.source_ref
        ? prior.source_ref === args.source_ref
        : false;
    if (
      !complete ||
      ["done", "archived"].includes(prior.status) ||
      prior.user_modified ||
      !next
    ) {
      if (
        !next &&
        authoritative &&
        sameSource &&
        !prior.user_modified &&
        !["done", "archived"].includes(prior.status)
      )
        diff.dropped.push({ ...prior, status: "archived" });
      else diff.unchanged.push(prior);
    } else {
      const merged = {
        ...prior,
        ...next,
        ...(prior.task_ref ? { task_ref: prior.task_ref } : {}),
        ...(prior.status === "in-progress" && next.status === "todo"
          ? { status: "in-progress" }
          : {}),
      };
      if (
        prior.due &&
        next.due &&
        prior.due !== next.due &&
        (!authoritative || !sameSource)
      ) {
        merged.conflict_flag = true;
        merged.conflict_notes =
          "Contradictory deadline evidence requires review: " +
          prior.due +
          " / " +
          next.due;
      }
      if (JSON.stringify(merged) === JSON.stringify(prior))
        diff.unchanged.push(prior);
      else diff.modified.push(merged);
    }
  }
  if (complete)
    for (const next of incoming)
      if (!original.some((d) => d.id === next.id))
        diff.added.push({
          status: "todo",
          ...next,
          ...(args.source_ref ? { source_ref: args.source_ref } : {}),
          ...(args.source_scope ? { source_scope: args.source_scope } : {}),
        });
  fm.deliverables = [
    ...diff.unchanged,
    ...diff.modified,
    ...diff.added,
    ...diff.dropped,
  ];
  return { changes: [change(row, fm)], diff };
}
export function graph(ctx: RuntimeContext) {
  const projects = collection(ctx.vault, "projects", 500),
    zettels = collection(ctx.vault, "zettels", 500);
  if (projects.length + zettels.length > 500)
    throw new Error("Narrow graph selection");
  const zlinks = new Map(
      zettels.map((z) => ["[[" + z.path.slice(0, -3) + "]]", z]),
    ),
    related = new Map<string, string[]>(),
    changes: Change[] = [];
  const reciprocal = new Map<string, string[]>();
  for (const row of projects) {
    const link = "[[" + row.path.slice(0, -3) + "]]",
      links = new Set<string>(row.frontmatter.linked_zettels ?? []);
    for (const z of zettels)
      if (z.frontmatter.project_ref === link)
        links.add("[[" + z.path.slice(0, -3) + "]]");
    const selected = [...links].filter((l) => zlinks.has(l)).sort();
    related.set(link, selected);
    const missing = selected.filter((l) => !row.body.includes(l));
    const fm = { ...row.frontmatter, linked_zettels: selected };
    if (
      JSON.stringify(fm) !== JSON.stringify(row.frontmatter) ||
      missing.length
    )
      changes.push(
        change(
          row,
          fm,
          row.body +
            (missing.length
              ? "\n\n## Knowledge references\n" +
                missing.map((l) => "- " + l).join("\n") +
                "\n"
              : ""),
        ),
      );
    for (const zlink of selected)
      if (!zlinks.get(zlink)!.frontmatter.project_ref) {
        if (!reciprocal.has(zlink)) reciprocal.set(zlink, []);
        reciprocal.get(zlink)!.push(link);
      }
  }
  for (const [zlink, links] of reciprocal)
    if (links.length === 1) {
      const z = zlinks.get(zlink)!;
      changes.push(change(z, { ...z.frontmatter, project_ref: links[0] }));
    }
  for (const row of collection(ctx.vault, "tasks")) {
    const links = new Set<string>(row.frontmatter.linked_zettels ?? []);
    for (const project of row.frontmatter.projects ?? [])
      for (const link of related.get(project) ?? []) links.add(link);
    const selected = [...links].sort();
    if (
      JSON.stringify(selected) !==
      JSON.stringify(row.frontmatter.linked_zettels ?? [])
    )
      changes.push(
        change(row, { ...row.frontmatter, linked_zettels: selected }),
      );
  }
  return changes;
}
export function duplicateCandidates(ctx: RuntimeContext, args: Metadata) {
  if (
    typeof args.text !== "string" ||
    Buffer.byteLength(args.text) > 65536 ||
    !Number.isInteger(args.limit ?? 10) ||
    (args.limit ?? 10) < 1 ||
    (args.limit ?? 10) > 20
  )
    throw new Error("Use bounded duplicate evidence");
  const normalized = sha256(
    args.text.replace(/\r\n/g, "\n").replace(/\s+/g, " ").trim(),
  );
  const words = new Set<string>(
    args.text.toLowerCase().match(/[a-z0-9]{3,}/g) ?? [],
  );
  const candidates: Metadata[] = [];
  for (const row of collection(ctx.vault, "sources", 500)) {
    const other = new Set<string>(
      row.body
        .slice(0, 65536)
        .toLowerCase()
        .match(/[a-z0-9]{3,}/g) ?? [],
    );
    const union = new Set([...words, ...other]),
      overlap =
        [...words].filter((w) => other.has(w)).length / Math.max(1, union.size),
      rawExact = !!args.sha256 && row.frontmatter.sha256 === args.sha256,
      normalizedExact = row.frontmatter.normalized_text_sha256 === normalized;
    if (rawExact || normalizedExact || overlap > 0.1)
      candidates.push({
        path: row.path,
        revision: row.revision,
        raw_exact: rawExact,
        normalized_exact: normalizedExact,
        lexical_overlap: Math.round(overlap * 10000) / 10000,
        evidence: sanitizeUntrusted(row.body.slice(0, 2000)),
      });
  }
  candidates.sort(
    (a, b) =>
      Number(b.raw_exact) - Number(a.raw_exact) ||
      Number(b.normalized_exact) - Number(a.normalized_exact) ||
      b.lexical_overlap - a.lexical_overlap,
  );
  return {
    status: candidates.length ? "candidates" : "empty",
    candidates: candidates.slice(0, args.limit ?? 10),
    semantic_review_required: true,
  };
}
export function gapFillers(ctx: RuntimeContext, args: Metadata) {
  if (
    !Number.isInteger(args.target_count ?? 3) ||
    (args.target_count ?? 3) < 1 ||
    (args.target_count ?? 3) > 20
  )
    throw new Error("Use 1–20 gap fillers");
  const date = dateOnly(args.date).toString(),
    horizon = dateOnly(date).add({ days: 14 }).toString();
  return collection(ctx.vault, "tasks", 500)
    .filter(
      ({ frontmatter: fm }) =>
        ["todo", "in-progress"].includes(fm.status) &&
        !fm.archived &&
        !fm.review_required &&
        !fm.date_uncertain &&
        !fm.isBlocked &&
        !fm.blockedBy?.length &&
        (fm.urgency_tier ?? 2) <= 2 &&
        (fm.timeEstimate ?? 45) <= 45 &&
        (fm.due ?? horizon) <= horizon &&
        fm.horizon_bucket !== "future",
    )
    .sort(
      (a, b) =>
        (a.frontmatter.timeEstimate ?? 45) - (b.frontmatter.timeEstimate ?? 45),
    )
    .slice(0, Math.min(20, args.target_count ?? 3))
    .map((r) => ({
      path: r.path,
      revision: r.revision,
      title: r.frontmatter.title,
      timeEstimate: r.frontmatter.timeEstimate ?? 45,
    }));
}
