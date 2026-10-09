import fs from "node:fs";
import path from "node:path";
import {
  confined,
  exists,
  rejectRedirects,
  raw,
  sha256,
  digest,
} from "../platforms/filesystem.ts";
import {
  collection,
  readRecord,
  change,
  serializeRecord,
  sanitizeUntrusted,
  parse,
} from "../storage/records.ts";
import { configuredZone, propose } from "./runtime.ts";
import { sourceConfiguration, configuration } from "./integrations.ts";
import { taskDocument } from "./knowledge.ts";
import { inspectOriginal } from "./originals.ts";
import { nowStamp, dateOnly } from "../time/timezone.ts";
import type { RuntimeContext, Metadata, Change } from "../contracts/types.ts";

function options(args: Metadata, keys: string[]) {
  for (const k of Object.keys(args))
    if (!keys.includes(k))
      throw new Error(
        "Request cannot override trusted ingestion configuration: " + k,
      );
}
export async function discover(ctx: RuntimeContext, args: Metadata) {
  options(args, ["source_alias", "page_size", "page_token", "all"]);
  const size = args.page_size ?? 50,
    token = args.page_token ?? "0";
  if (
    !Number.isInteger(size) ||
    size < 1 ||
    size > 100 ||
    typeof token !== "string" ||
    token.length > 500
  )
    throw new Error("Use a bounded discovery page");
  if (args.all) {
    const aliases = Object.keys(
      configuration(ctx).ingestion.sources ?? {},
    ).filter((a) => configuration(ctx).ingestion.sources[a].enabled === true);
    if (aliases.length > 20) throw new Error("Too many configured sources");
    return Promise.all(
      aliases.map((source_alias) =>
        discover(ctx, { source_alias, page_size: size }),
      ),
    );
  }
  const c = sourceConfiguration(ctx, args.source_alias),
    items: Metadata[] = [];
  if (c.native_authorization && c.integration === "google-tasks") {
    const { sourceTool } = await import("../integrations/service.ts");
    return sourceTool(ctx, "read_task_inbox", {
      instance: c.instance,
      list_id: c.collection_id,
      page_size: size,
      ...(args.page_token ? { cursor: args.page_token } : {}),
    });
  }
  if (!/^\d{1,6}$/.test(token)) throw Error("Use a bounded discovery page");
  const offset = Number(token);
  let truncated = false;
  if (c.integration === "google-tasks" || c.export_path) {
    if (!c.export_path || !exists(rejectRedirects(c.export_path)))
      return {
        status: "unavailable",
        discovery_status: "operation_unavailable",
        reason: "configured_export_missing",
      };
    const data = JSON.parse(
      raw(rejectRedirects(c.export_path), 4 * 1024 * 1024).toString("utf8"),
    );
    const rows = data.items ?? data.tasks;
    if (!Array.isArray(rows) || rows.length > 2000)
      throw new Error("Invalid bounded export");
    for (const row of rows) {
      if (c.integration === "google-tasks")
        items.push({
          content_kind: "structured_task",
          integration: c.integration,
          account_scope: c.account_scope,
          collection_id: c.collection_id,
          external_item_id: row.id ?? row.external_item_id,
          external_revision: row.updated ?? null,
          payload: {
            title: row.title,
            notes: row.notes ?? "",
            due: row.due?.slice(0, 10) ?? null,
            external_status: row.status ?? "needsAction",
          },
        });
      else items.push(row);
    }
  } else {
    const root = c.local_mount_path
        ? rejectRedirects(c.local_mount_path)
        : confined(ctx.vault, "Attachments/Originals"),
      depth = c.max_discovery_depth ?? 8,
      roots = c.discovery_roots ?? ["."];
    if (
      !Number.isInteger(depth) ||
      depth < 0 ||
      depth > 32 ||
      !Array.isArray(roots) ||
      roots.length > 20
    )
      throw new Error("Use bounded private discovery roots");
    if (!exists(root))
      return { status: "unavailable", discovery_status: "mount_unavailable" };
    function walk(dir: string, level: number) {
      rejectRedirects(dir);
      for (const e of fs
        .readdirSync(dir, { withFileTypes: true })
        .sort((a, b) => a.name.localeCompare(b.name))) {
        const full = rejectRedirects(path.join(dir, e.name));
        if (e.isDirectory()) {
          if (level >= depth) truncated = true;
          else walk(full, level + 1);
        } else if (e.isFile()) {
          if (items.length >= 2000) {
            truncated = true;
            continue;
          }
          const relative = path
            .relative(ctx.vault, full)
            .split(path.sep)
            .join("/");
          items.push({
            content_kind: "file",
            external_item_id:
              c.integration === "local-filesystem" ? null : e.name,
            payload: {
              original_filename: e.name,
              relative_path: relative,
              file_size_bytes: fs.statSync(full).size,
              sha256: null,
              bytes_available: false,
            },
          });
        }
      }
    }
    for (const selected of roots)
      walk(selected === "." ? root : confined(root, selected), 0);
  }
  const next = items.length > offset + size ? String(offset + size) : null;
  return {
    contract_version: "2",
    source_alias: args.source_alias,
    integration: c.integration,
    collection_id: c.collection_id ?? args.source_alias,
    access_mode: "read-only",
    discovery_status:
      truncated || next
        ? "partial_listing"
        : items.length
          ? "ok_items_available"
          : "ok_empty",
    capabilities: { write_back_supported: false },
    pagination: { bounded: true, next_page_token: next, truncated },
    items: items.slice(offset, offset + size),
  };
}
export async function draftIngestion(ctx: RuntimeContext, args: Metadata) {
  options(args, ["envelope", "date", "now"]);
  const e = args.envelope;
  if (
    !e ||
    e.contract_version !== "2" ||
    e.access_mode !== "read-only" ||
    e.capabilities?.write_back_supported !== false ||
    !Array.isArray(e.items) ||
    e.items.length > 100
  )
    throw new Error("Invalid read-only bounded ingestion envelope");
  if (
    ![
      "ok_items_available",
      "partial_listing",
      "ok_empty",
      "ok_fully_indexed",
    ].includes(e.discovery_status)
  )
    return { status: "unavailable", reason: e.discovery_status };
  const date = dateOnly(args.date).toString(),
    zone = configuredZone(ctx),
    changes: Change[] = [],
    outcomes: Metadata[] = [],
    existing = collection(ctx.vault, "sources", 500),
    tasks = collection(ctx.vault, "tasks", 500).concat(
      collection(ctx.vault, "archive", 500),
    );
  for (const item of e.items) {
    const p = item.payload;
    if (
      !p ||
      typeof p !== "object" ||
      !["file", "text", "structured_task"].includes(item.content_kind)
    )
      throw new Error("Invalid ingestion item");
    for (const key of [
      "execute_command",
      "override_skill",
      "approve_automatically",
      "bypass_approval_gate",
      "write_back",
      "integration",
      "source_alias",
      "access_mode",
    ])
      if (key in p) throw new Error("Payload contains control field");
    for (const value of [p.mime_type, p.source_type])
      if (value && !/^[a-z0-9.+_/-]{1,100}$/i.test(value))
        throw new Error("Invalid ingestion metadata");
    let key: string, body: string, metadata: Metadata;
    if (item.content_kind === "structured_task") {
      const identity = {
        integration: item.integration ?? e.integration,
        account_scope: item.account_scope,
        collection_id: item.collection_id ?? e.collection_id,
        external_item_id: item.external_item_id,
      };
      if (
        Object.values(identity).some(
          (v) => typeof v !== "string" || !v || v.length > 500,
        )
      )
        throw new Error("Stable provider/account/list/item identity required");
      key = digest(identity);
      if (
        typeof p.title !== "string" ||
        !p.title.trim() ||
        p.title.length > 500 ||
        (p.notes !== undefined &&
          (typeof p.notes !== "string" ||
            Buffer.byteLength(p.notes) > 1024 * 1024)) ||
        (p.due != null &&
          (typeof p.due !== "string" ||
            !/^\d{4}-\d{2}-\d{2}(?:T.*)?$/.test(p.due))) ||
        ![undefined, "needsAction", "completed"].includes(p.external_status)
      )
        throw new Error("Invalid bounded structured task payload");
      const sourcePath = "Sources/capture-" + key.slice(0, 24) + ".md",
        due = p.due ? dateOnly(p.due.slice(0, 10)).toString() : null,
        importedBody = sanitizeUntrusted(p.notes ?? "", { source_id: key }),
        importedStatus = p.external_status === "completed" ? "done" : "todo",
        snapshot = {
          title: p.title,
          due,
          body: importedBody,
          status: importedStatus,
        },
        horizon = !due
          ? "uncertain"
          : due > dateOnly(date).add({ days: 14 }).toString()
            ? "future"
            : due < date
              ? "overdue"
              : "imminent";
      const fingerprint = digest(p),
        prior = tasks.find(
          (t) =>
            t.frontmatter.external_integration === identity.integration &&
            t.frontmatter.external_account_scope === identity.account_scope &&
            t.frontmatter.external_collection_id === identity.collection_id &&
            t.frontmatter.external_item_id === identity.external_item_id,
        );
      if (prior) {
        if (
          prior.frontmatter.external_payload_sha256 === fingerprint ||
          ["done", "archived"].includes(prior.frontmatter.status)
        ) {
          outcomes.push({
            identity: key,
            status:
              prior.frontmatter.external_payload_sha256 === fingerprint
                ? "duplicate_unchanged"
                : "completed_preserved",
          });
          continue;
        }
        const source = existing.find((s) => s.path === sourcePath),
          accepted = source?.frontmatter.structured_task_snapshot,
          untouched =
            accepted &&
            !prior.frontmatter.user_modified &&
            !prior.frontmatter.external_conflict_flag &&
            prior.frontmatter.scheduled == null &&
            prior.frontmatter.googleCalendarEventId == null &&
            !(
              prior.frontmatter.projects?.length ||
              prior.frontmatter.linked_zettels?.length
            ) &&
            [
              "location",
              "coordinates",
              "route_estimate",
              "travel_policy",
              "due_time",
              "due_at",
              "due_timezone",
            ].every((field) => prior.frontmatter[field] == null) &&
            prior.frontmatter.status === "todo" &&
            prior.frontmatter.title === accepted.title &&
            (prior.frontmatter.due ?? null) === accepted.due &&
            prior.body === accepted.body;
        if (untouched) {
          changes.push(
            change(
              prior,
              {
                ...prior.frontmatter,
                title: p.title,
                due,
                status: importedStatus,
                scheduled: null,
                due_time: null,
                due_at: null,
                due_timezone: null,
                date_uncertain: !due,
                review_required: !due || horizon === "overdue",
                horizon_bucket: horizon,
                external_revision: item.external_revision ?? null,
                external_payload_sha256: fingerprint,
                external_conflict_flag: false,
                external_conflict_proposal: null,
              },
              importedBody,
            ),
          );
          changes.push(
            change(
              source!,
              {
                ...source!.frontmatter,
                title: p.title,
                structured_payload_sha256: fingerprint,
                structured_task_snapshot: snapshot,
                external_revision: item.external_revision ?? null,
                ingestion_outcome: "updated_existing",
              },
              sanitizeUntrusted(JSON.stringify(p), { source_id: key }),
            ),
          );
          outcomes.push({ identity: key, status: "updated_existing" });
        } else {
          // Preserve local work and the last accepted import snapshot. Only the conflict evidence changes.
          const conflict = {
            external_revision: item.external_revision ?? null,
            external_payload_sha256: fingerprint,
            source_alias: e.source_alias,
            proposed_changes: { ...snapshot, body: importedBody },
          };
          if (
            digest(prior.frontmatter.external_conflict_proposal ?? {}) ===
            digest(conflict)
          ) {
            outcomes.push({ identity: key, status: "conflict_already_staged" });
            continue;
          }
          changes.push(
            change(prior, {
              ...prior.frontmatter,
              review_required: true,
              external_conflict_flag: true,
              external_conflict_proposal: conflict,
            }),
          );
          outcomes.push({ identity: key, status: "external_conflict_review" });
        }
        continue;
      }
      const task = taskDocument(ctx, {
        title: p.title,
        now: args.now ?? nowStamp(zone, ctx.now),
        path: "TaskNotes/Tasks/capture-" + key.slice(0, 24) + ".md",
        due,
        body: importedBody,
        modality: "administrative",
        fields: {
          source_ref: "[[" + sourcePath.slice(0, -3) + "]]",
          due_time: null,
          due_at: null,
          due_timezone: null,
          date_uncertain: !due,
          review_required: !due || horizon === "overdue",
          external_source_alias: e.source_alias,
          external_integration: identity.integration,
          external_account_scope: identity.account_scope,
          external_collection_id: identity.collection_id,
          external_item_id: identity.external_item_id,
          external_revision: item.external_revision ?? null,
          external_payload_sha256: fingerprint,
          horizon_bucket: horizon,
        },
      });
      const initialTask = parse(task.document);
      task.document = serializeRecord(
        { ...initialTask.frontmatter, status: importedStatus },
        initialTask.body,
      );
      changes.push(task);
      metadata = {
        type: "source",
        id: "capture-" + key.slice(0, 24),
        title: p.title,
        source_type: "other",
        sha256: null,
        bytes_available: false,
        structured_payload_sha256: fingerprint,
        structured_task_snapshot: snapshot,
        captured_date: nowStamp(zone, ctx.now),
        ingestion_status: "processed",
        source_alias: e.source_alias,
        integration: identity.integration,
        collection_id: identity.collection_id,
        external_item_id: identity.external_item_id,
        external_revision: item.external_revision ?? null,
        extracted_tasks: ["[[" + task.path.slice(0, -3) + "]]"],
      };
      body = sanitizeUntrusted(JSON.stringify(p), { source_id: key });
      changes.push({
        path: sourcePath,
        if_revision: null,
        document: serializeRecord(metadata, body),
      });
      continue;
    }
    let rawHash: string | null = null,
      normalizedHash: string | null = null,
      original: string | undefined,
      coverage: Metadata | undefined,
      content: string | undefined;
    if (item.content_kind === "file") {
      original = p.relative_path ?? p.original_locator?.path;
      if (
        typeof original !== "string" ||
        !original.startsWith("Attachments/Originals/")
      )
        throw new Error(
          "Import originals into the vault before drafting; external references cannot masquerade as local bytes",
        );
      const observed = await inspectOriginal(ctx, {
        path: original,
        extract: true,
        first_page: p.first_page,
        page_count: p.page_count,
      });
      rawHash = observed.sha256;
      if (p.sha256 && p.sha256 !== rawHash)
        throw new Error("Original raw-byte hash mismatch");
      coverage = observed.coverage ?? { status: observed.extraction_status };
      content = observed.untrusted_text;
      normalizedHash = observed.normalized_text_sha256 ?? null;
    } else {
      if (
        p.sha256 ||
        p.bytes_available ||
        (p.mime_type && !/^text\//.test(p.mime_type)) ||
        p.source_type === "pdf"
      )
        throw new Error("Extracted text cannot masquerade as original bytes");
      const value = p.text ?? p.extracted_text ?? "";
      if (typeof value !== "string" || Buffer.byteLength(value) > 1024 * 1024)
        throw new Error("Use bounded text evidence");
      normalizedHash = sha256(
        value.replace(/\r\n/g, "\n").replace(/\s+/g, " ").trim(),
      );
      content = sanitizeUntrusted(value, {
        source_id: item.external_item_id ?? "text",
      });
    }
    key =
      rawHash ??
      digest({
        integration: e.integration,
        collection_id: e.collection_id,
        external_item_id: item.external_item_id,
        text: content,
      });
    const id = "source-" + key.slice(0, 24),
      relative = "Sources/" + id + ".md";
    const prior = existing.find((s) =>
      rawHash ? s.frontmatter.sha256 === rawHash : s.frontmatter.id === id,
    );
    if (prior) {
      if (
        rawHash &&
        original &&
        prior.frontmatter.original_locator?.path !== original
      ) {
        const previous =
            prior.frontmatter.original_locator?.path ??
            prior.frontmatter.relative_path,
          previousPaths = [
            ...new Set([
              ...(prior.frontmatter.previous_paths ?? []),
              ...(previous ? [previous] : []),
            ]),
          ],
          sourceFm = {
            ...prior.frontmatter,
            original_filename: path.basename(original),
            relative_path: original,
            original_locator: { kind: "vault_relative", path: original },
            previous_paths: previousPaths,
            ingestion_outcome: "updated_existing",
          };
        if (previousPaths.length > 100)
          throw new Error("Original provenance history exceeds its bound");
        // Preserve extracted evidence and stable source identity while changing only its original link.
        const oldLink = previous ? "Original: [[" + previous + "]]" : "",
          newLink = "Original: [[" + original + "]]",
          updatedBody =
            oldLink && prior.body.includes(oldLink)
              ? prior.body.replace(oldLink, newLink)
              : newLink + "\n\n" + prior.body;
        changes.push(change(prior, sourceFm, updatedBody));
        outcomes.push({
          path: prior.path,
          status: "original_locator_updated",
          raw_exact: true,
          observed_original: original,
        });
        continue;
      }
      outcomes.push({
        path: prior.path,
        status: "duplicate_unchanged",
        raw_exact: !!rawHash,
        observed_original: original,
      });
      continue;
    }
    if (changes.some((c) => c.path === relative)) continue;
    metadata = {
      type: "source",
      id,
      title:
        p.title ??
        p.original_filename ??
        item.external_item_id ??
        "Captured reference",
      source_type:
        item.content_kind === "file" &&
        path.extname(original!).toLowerCase() === ".pdf"
          ? "pdf"
          : "reference",
      sha256: rawHash,
      bytes_available: !!rawHash,
      normalized_text_sha256: normalizedHash,
      captured_date: nowStamp(zone, ctx.now),
      ingestion_status: content ? "processed" : "raw",
      ingestion_outcome: content ? "extracted" : "unsupported_deferred",
      extraction_coverage: coverage ?? null,
      source_alias: e.source_alias ?? null,
      integration: e.integration ?? null,
      collection_id: e.collection_id ?? null,
      external_item_id: item.external_item_id ?? null,
      external_revision: item.external_revision ?? null,
      ...(original
        ? {
            original_filename: path.basename(original),
            relative_path: original,
            original_locator: { kind: "vault_relative", path: original },
          }
        : {}),
    };
    body =
      "# " +
      String(metadata.title).replace(/[\r\n]/g, " ") +
      "\n\n" +
      (original ? "Original: [[" + original + "]]\n\n" : "") +
      (content ?? "Extraction deferred; no content inferred.\n");
    changes.push({
      path: relative,
      if_revision: null,
      document: serializeRecord(metadata, body),
    });
  }
  if (!changes.length) return { status: "no_changes", outcomes };
  return {
    ...propose(ctx, changes, "ingestion", { contract_version: "2", outcomes }),
    outcomes,
  };
}
