import fs from "node:fs";
import path from "node:path";
import { MAX_REQUEST_BYTES } from "../contracts/types.ts";
import type { RuntimeContext, Metadata } from "../contracts/types.ts";
import {
  PACKAGE_ROOT,
  readJSON,
  confined,
  text,
  files,
} from "../platforms/filesystem.ts";
import { runtimeContext } from "../storage/context.ts";
import {
  readRecord,
  collection,
  schemaFor,
  validate,
} from "../storage/records.ts";
import { propose, apply, configuredZone } from "../core/runtime.ts";
import * as daily from "../core/daily.ts";
import * as knowledge from "../core/knowledge.ts";
import * as receipts from "../storage/receipts.ts";
import { doctor } from "../core/diagnostics.ts";
import { discover, draftIngestion } from "../core/ingestion.ts";
import { capability, integrationStatus, redact } from "../core/integrations.ts";
import { inspectOriginal } from "../core/originals.ts";
import { businessDate } from "../time/timezone.ts";
import { environment } from "../platforms/environment.ts";
import {
  searchKnowledge,
  lintKnowledge,
  prepareKnowledge,
} from "../core/wiki.ts";
import {
  discoverDocuments,
  prepareDocumentImport,
  applyDocumentImport,
} from "../core/documents.ts";

export const OPERATIONS: string[] = readJSON(
  path.join(PACKAGE_ROOT, "contracts/operations.json"),
);
/** The host supplies roots and cancellation; model arguments cannot replace either. */
export async function dispatch(
  ctx: RuntimeContext,
  operation: string,
  args: Metadata = {},
) {
  runtimeContext(ctx.vault, ctx.state);
  if (!OPERATIONS.includes(operation)) throw new Error("unsupported_operation");
  if (
    !args ||
    typeof args !== "object" ||
    Array.isArray(args) ||
    Buffer.byteLength(JSON.stringify(args)) > MAX_REQUEST_BYTES
  )
    throw new Error("Use a bounded argument object");
  if (ctx.signal?.aborted) throw new Error("Cancelled");
  switch (operation) {
    case "read": {
      schemaFor(args.path);
      const row = readRecord(ctx.vault, args.path);
      return { status: "ok", document: row.document, revision: row.revision };
    }
    case "query": {
      const size = args.limit ?? 50,
        page = args.page ?? 0;
      if (
        !Number.isInteger(size) ||
        size < 1 ||
        size > 100 ||
        !Number.isInteger(page) ||
        page < 0
      )
        throw new Error("Use a bounded query");
      const rows = collection(ctx.vault, args.collection).filter(
        (r) => !args.status || r.frontmatter.status === args.status,
      );
      return {
        status: "ok",
        records: rows
          .slice(page * size, (page + 1) * size)
          .map(({ path, revision, frontmatter }) => ({
            path,
            revision,
            frontmatter,
          })),
        next_page: rows.length > (page + 1) * size ? page + 1 : null,
      };
    }
    case "schema": {
      if (
        ![
          "task",
          "project",
          "zettel",
          "source",
          "system_state",
          "daily_note",
        ].includes(args.type)
      )
        throw new Error("Unknown schema");
      const row = readRecord(ctx.vault, "_types/" + args.type + ".md");
      return { status: "ok", document: row.document, revision: row.revision };
    }
    case "template": {
      const root = path.join(PACKAGE_ROOT, "resources/vault"),
        available = files(root)
          .map((f) => path.relative(root, f).split(path.sep).join("/"))
          .filter((f) => f.includes("_templates/") && f.endsWith(".md"));
      if (!args.path) return { status: "ok", templates: available };
      if (!available.includes(args.path))
        throw new Error("Unknown maintained template");
      return { status: "ok", document: text(confined(root, args.path)) };
    }
    case "validate": {
      const result = validate(ctx.vault, args.path, args.document);
      return {
        status: result.valid ? "ok" : "invalid",
        diagnostics: result.diagnostics,
      };
    }
    case "propose":
      return propose(ctx, args.records, args.purpose ?? "review");
    case "apply":
      return apply(ctx, args.proposal_digest);
    case "original.inspect":
      return inspectOriginal(ctx, args);
    case "documents.discover":
      return discoverDocuments(ctx, args);
    case "documents.prepare":
      return prepareDocumentImport(ctx, args);
    case "documents.apply":
      if (Object.keys(args).some((key) => key !== "proposal_digest"))
        throw Error("Use only the saved document-import digest");
      return applyDocumentImport(ctx, args.proposal_digest);
    case "duplicates":
      return knowledge.duplicateCandidates(ctx, args);
    case "knowledge.search":
      return searchKnowledge(ctx, args);
    case "knowledge.lint":
      return lintKnowledge(ctx, args);
    case "knowledge.prepare": {
      const candidate = prepareKnowledge(ctx, args);
      return {
        ...propose(
          ctx,
          candidate.changes,
          "knowledge_compilation",
          undefined,
          candidate.dependencies,
          candidate.review,
        ),
        knowledge_review: candidate.review,
      };
    }
    case "task.draft":
      return propose(ctx, [knowledge.taskDocument(ctx, args)], "task_capture");
    case "horizon": {
      const changes = knowledge.horizon(ctx, args);
      return changes.length
        ? propose(ctx, changes, "project_horizon")
        : { status: "no_changes" };
    }
    case "project.reconcile": {
      const result = knowledge.reconcile(ctx, args);
      return {
        ...propose(ctx, result.changes, "project_reconciliation"),
        diff: result.diff,
      };
    }
    case "project.status":
      return {
        status: "ok",
        projects: collection(ctx.vault, "projects").map(
          ({ frontmatter: fm }) => ({
            ...Object.fromEntries(
              ["project_id", "title", "pillar", "status", "horizon_window"].map(
                (k) => [k, fm[k]],
              ),
            ),
            progress: {
              done: (fm.deliverables ?? []).filter((d) => d.status === "done")
                .length,
              total: (fm.deliverables ?? []).length,
            },
          }),
        ),
      };
    case "graph": {
      const changes = knowledge.graph(ctx);
      return changes.length
        ? propose(ctx, changes, "knowledge_links")
        : { status: "no_changes" };
    }
    case "gap-fillers":
      return { status: "ok", candidates: knowledge.gapFillers(ctx, args) };
    case "business-buffer":
      return {
        status: "ok",
        verification_date: businessDate(
          args.submission_date,
          args.business_days ?? 3,
        ),
      };
    case "doctor":
      return doctor(ctx);
    case "environment":
      return environment(args);
    case "integrations.status": {
      const status = redact(integrationStatus(ctx)),
        native = await (
          await import("../integrations/service.ts")
        ).sourceTool(ctx, "integration_status");
      for (const item of native.integrations)
        status.integrations[item.instance] = {
          integration: item.provider,
          ...item,
        };
      return status;
    }
    case "capability":
      return {
        status: "observed",
        result: redact(
          await capability(
            ctx,
            args.capability,
            args.request ?? {},
            args.binding_slot,
          ),
        ),
      };
    case "ingest.discover":
      return {
        status: "observed",
        discovery: redact(await discover(ctx, args)),
      };
    case "ingest.draft":
      return draftIngestion(ctx, args);
    case "ingest.prevalidate":
      return args.envelope
        ? draftIngestion(ctx, args)
        : propose(
            ctx,
            args.records ?? args.proposal?.records,
            "ingestion_prevalidated",
          );
    case "plan":
    case "stage":
    case "audit": {
      const health = doctor(ctx);
      if (health.status !== "ok") return { status: "blocked", health };
      if (operation === "audit") {
        const r = daily.audit(ctx, args),
          p = propose(ctx, r.changes, "audit");
        return {
          ...p,
          audit: r.result,
          result_digest: await receipts.saveResult(ctx, "audit", {
            ...r.result,
            proposal_digest: p.proposal_digest,
          }),
        };
      }
      const r = (operation === "stage" ? daily.stage : daily.plan)(ctx, args),
        p = propose(
          ctx,
          r.changes,
          operation === "stage" ? "staging" : "calibration",
        );
      return operation === "stage"
        ? {
            ...p,
            result_digest: await receipts.saveResult(ctx, "planning", {
              blocks: r.blocks,
              proposal_digest: p.proposal_digest,
            }),
          }
        : p;
    }
    case "pause":
    case "resume": {
      const r = daily.pause(ctx, {
        ...args,
        mode: operation === "resume" ? "resume" : args.mode,
      });
      return { ...propose(ctx, r.changes, operation), ...r.result };
    }
    case "daily.begin":
      return receipts.begin(ctx, args);
    case "daily.gate":
      return receipts.gate(ctx, args);
    default:
      throw new Error("unsupported_operation");
  }
}
