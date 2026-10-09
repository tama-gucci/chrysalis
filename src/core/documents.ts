import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { vaultState } from "../storage/context.ts";
import { configuredZone } from "./runtime.ts";
import { nowStamp } from "../time/timezone.ts";
import {
  PACKAGE_ROOT,
  confined,
  rejectRedirects,
  inside,
  exists,
  sha256,
  digest,
  canonical,
  readJSON,
  atomicJSON,
  atomic,
  withLock,
} from "../platforms/filesystem.ts";
import type { RuntimeContext, Metadata } from "../contracts/types.ts";

const MAX_FILE_BYTES = 32 * 1024 * 1024,
  MAX_BATCH_BYTES = 64 * 1024 * 1024;
/** Fail on special files before reading; nonblocking/no-follow flags close POSIX leaf races. */
function regularBytes(target: string, limit: number) {
  rejectRedirects(target);
  const before = fs.lstatSync(target);
  if (!before.isFile()) throw Error("Select regular document files");
  if (before.size > limit)
    throw Error("Document file exceeds its reviewed byte limit");
  const flags =
    fs.constants.O_RDONLY |
    (fs.constants.O_NONBLOCK ?? 0) |
    (fs.constants.O_NOFOLLOW ?? 0);
  const fd = fs.openSync(target, flags);
  try {
    const opened = fs.fstatSync(fd);
    if (
      !opened.isFile() ||
      opened.dev !== before.dev ||
      opened.ino !== before.ino ||
      opened.size !== before.size
    )
      throw Error("Document path changed or is not a regular file");
    const buffer = Buffer.alloc(opened.size + 1);
    let length = 0;
    while (length < buffer.length) {
      const count = fs.readSync(
        fd,
        buffer,
        length,
        buffer.length - length,
        length,
      );
      if (!count) break;
      length += count;
    }
    if (length !== opened.size || fs.fstatSync(fd).size !== opened.size)
      throw Error("Document file changed during read");
    rejectRedirects(target);
    return buffer.subarray(0, length);
  } finally {
    fs.closeSync(fd);
  }
}
function markdownSafety(ctx: RuntimeContext, entries: Metadata[]) {
  if (!entries.some((entry) => /\.md$/i.test(entry.source_path))) return null;
  // TaskNotes exclusions are case-sensitive; original-storage ancestors retain canonical spelling.
  let parent = ctx.vault;
  for (const name of ["Attachments", "Originals"]) {
    const next = confined(parent, name);
    if (exists(next) && !fs.readdirSync(parent).includes(name))
      throw Error(
        "Use canonical Attachments/Originals folder spelling for passive Markdown storage",
      );
    parent = next;
  }
  const taskBytes = regularBytes(
      confined(ctx.vault, ".obsidian/plugins/tasknotes/data.json"),
      4 * 1024 * 1024,
    ),
    viewBytes = regularBytes(
      confined(ctx.vault, ".obsidian/plugins/dataview/data.json"),
      4 * 1024 * 1024,
    ),
    task = JSON.parse(taskBytes.toString("utf8")),
    view = JSON.parse(viewBytes.toString("utf8")),
    exclusions =
      typeof task.excludedFolders === "string"
        ? task.excludedFolders.split(",")
        : task.excludedFolders;
  if (
    !Array.isArray(exclusions) ||
    exclusions.some((value) => typeof value !== "string") ||
    !exclusions.some((value: string) => {
      const folder = value
        .trim()
        .replace(/\\/g, "/")
        .replace(/^\/+|\/+$/g, "");
      return folder === "Attachments/Originals" || folder === "Attachments";
    }) ||
    view.enableDataviewJs !== false ||
    view.enableInlineDataviewJs !== false
  )
    throw Error(
      "Markdown import blocked: exclude Attachments/Originals in TaskNotes and disable DataviewJS and inline DataviewJS in Obsidian, then prepare and review again",
    );
  return {
    originals_excluded: true,
    dataview_code_enabled: false,
    tasknotes_settings_sha256: sha256(taskBytes),
    dataview_settings_sha256: sha256(viewBytes),
  };
}
const folderFile = (ctx: RuntimeContext) =>
  confined(vaultState(ctx), "document-folder.json");
const planFile = (ctx: RuntimeContext, key: string) => {
  if (!/^[a-f0-9]{64}$/.test(key))
    throw Error("Use a saved document-import digest");
  return confined(vaultState(ctx), "document-imports/" + key + ".json");
};
function argsOnly(args: Metadata, allowed: string[]) {
  for (const key of Object.keys(args))
    if (!allowed.includes(key))
      throw Error("Unsupported document argument: " + key);
}
function sourceRoot(ctx: RuntimeContext, input: string) {
  const root = rejectRedirects(input);
  if (!exists(root) || !fs.statSync(root).isDirectory())
    throw Error("Choose an existing document folder");
  for (const boundary of [ctx.vault, ctx.state, PACKAGE_ROOT])
    if (inside(root, boundary) || inside(boundary, root))
      throw Error(
        "Document folder must be separate from vault, execution state and package/source",
      );
  return root;
}
export function prepareDocumentFolder(ctx: RuntimeContext, root: string) {
  return {
    version: "1",
    folder_id: randomUUID(),
    source_root: sourceRoot(ctx, root),
    vault_root: ctx.vault,
    vault_id: readJSON(confined(ctx.vault, ".chrysalis-vault.json")).vault_id,
    permissions: {
      metadata_discovery: true,
      selected_byte_hashing: true,
      copy_requires_separate_approval: true,
      source_writes: false,
    },
  };
}
function verifyFolder(ctx: RuntimeContext, folder: Metadata) {
  if (
    folder.version !== "1" ||
    !/^[a-f0-9-]{36}$/.test(folder.folder_id ?? "") ||
    folder.vault_root !== ctx.vault ||
    folder.vault_id !==
      readJSON(confined(ctx.vault, ".chrysalis-vault.json")).vault_id ||
    folder.permissions?.metadata_discovery !== true ||
    folder.permissions?.selected_byte_hashing !== true ||
    folder.permissions?.copy_requires_separate_approval !== true ||
    folder.permissions?.source_writes !== false
  )
    throw Error("Document-folder authorization is invalid for this vault");
  sourceRoot(ctx, folder.source_root);
  return folder;
}
/** Operator boundary; never dispatched as a model operation. No vault files are written. */
export function selectDocumentFolder(
  ctx: RuntimeContext,
  folder: Metadata,
  evidence: string,
) {
  if (!evidence?.trim() || evidence.length > 1000)
    throw Error("Explicit folder-selection approval required");
  verifyFolder(ctx, folder);
  atomicJSON(folderFile(ctx), {
    ...folder,
    approved_at: nowStamp(configuredZone(ctx), ctx.now),
    evidence,
  });
  return { status: "selected", folder_id: folder.folder_id };
}
export function documentFolderStatus(ctx: RuntimeContext) {
  return exists(folderFile(ctx))
    ? {
        status: "selected",
        folder: verifyFolder(ctx, readJSON(folderFile(ctx))),
      }
    : { status: "not_selected" };
}
function selectedFolder(ctx: RuntimeContext) {
  const status = documentFolderStatus(ctx);
  if (!status.folder)
    throw Error(
      "Ask the user to select an optional folder with /chrysalis documents",
    );
  return status.folder;
}
const extraction = (relative: string) =>
  /\.(txt|md|csv|pdf)$/i.test(relative)
    ? "supported_bounded"
    : /\.(png|jpe?g|gif|webp)$/i.test(relative)
      ? "ocr_required"
      : "unsupported_deferred";
const excluded = (part: string) =>
  part.startsWith(".") ||
  ["node_modules", "nexus"].includes(part.toLowerCase());
const destination = (folder: Metadata, relative: string) =>
  "Attachments/Originals/Onboarding/" +
  folder.folder_id +
  "/" +
  relative
    .split("/")
    .map((part) => part.replace(/[\x00-\x1f\x7f\[\]#|^<>"?*]/g, "_"))
    .join("/");

/** Paged metadata only; neither file content nor durable checkpoints are created. */
export function discoverDocuments(ctx: RuntimeContext, args: Metadata) {
  argsOnly(args, ["page_size", "page_token"]);
  const folder = selectedFolder(ctx),
    size = args.page_size ?? 50,
    token = args.page_token ?? "0";
  if (
    !Number.isInteger(size) ||
    size < 1 ||
    size > 100 ||
    typeof token !== "string" ||
    !/^\d{1,6}$/.test(token)
  )
    throw Error("Use a bounded document page");
  const items: Metadata[] = [],
    omitted: Metadata[] = [];
  let visited = 0,
    truncated = false,
    omittedCount = 0;
  const omit = (relative: string, reason: string) => {
    omittedCount++;
    if (omitted.length < 100) omitted.push({ path: relative, reason });
  };
  function walk(directory: string, depth: number) {
    if (ctx.signal?.aborted) throw Error("Cancelled");
    const handle = fs.opendirSync(rejectRedirects(directory)),
      entries: fs.Dirent[] = [];
    try {
      let entry: fs.Dirent | null;
      while ((entry = handle.readSync())) {
        if (visited + entries.length >= 10000) {
          truncated = true;
          break;
        }
        entries.push(entry);
      }
    } finally {
      handle.closeSync();
    }
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      if (ctx.signal?.aborted) throw Error("Cancelled");
      if (visited >= 10000 || items.length >= 2000) {
        truncated = true;
        break;
      }
      visited++;
      const full = path.join(directory, entry.name),
        relative = path
          .relative(folder.source_root, full)
          .split(path.sep)
          .join("/");
      if (excluded(entry.name)) {
        omit(relative, "hidden_or_generated");
        continue;
      }
      if (entry.isSymbolicLink()) {
        omit(relative, "redirected_path");
        continue;
      }
      try {
        confined(folder.source_root, relative);
      } catch {
        omit(relative, "unsupported_or_redirected_path");
        continue;
      }
      if (entry.isDirectory()) {
        if (depth >= 8) {
          truncated = true;
          omit(relative, "depth_limit");
        } else walk(full, depth + 1);
      } else if (entry.isFile()) {
        const stat = fs.statSync(full);
        if (!stat.isFile()) {
          omit(relative, "not_regular_file");
          continue;
        }
        items.push({
          path: relative,
          bytes: stat.size,
          import_status:
            stat.size > MAX_FILE_BYTES ? "over_file_budget" : "selectable",
          extraction: extraction(relative),
          sha256: null,
          bytes_read: false,
        });
      } else omit(relative, "not_regular_file");
    }
  }
  walk(folder.source_root, 0);
  const offset = Number(token),
    next = items.length > offset + size ? String(offset + size) : null;
  return {
    status: "observed",
    folder_id: folder.folder_id,
    items: items.slice(offset, offset + size),
    next_page_token: next,
    discovery_complete: !truncated && !omittedCount && !next,
    scan_truncated: truncated,
    observed_files: items.length,
    entries_visited: visited,
    omitted,
    omitted_count: omittedCount,
    scope:
      "Metadata only; hidden/generated/redirected entries excluded; pages are a fresh bounded scan, not a collection snapshot",
  };
}

/** Selected raw bytes are hashed; only an external manifest is saved pending native review. */
export function prepareDocumentImport(ctx: RuntimeContext, args: Metadata) {
  argsOnly(args, ["paths"]);
  const folder = selectedFolder(ctx),
    paths: string[] = args.paths;
  if (
    !Array.isArray(paths) ||
    !paths.length ||
    paths.length > 100 ||
    paths.some((p) => typeof p !== "string" || p.length > 2000) ||
    new Set(paths.map((p) => p.toLowerCase())).size !== paths.length
  )
    throw Error("Select 1–100 distinct document paths");
  let total = 0;
  const entries = paths.map((relative) => {
    if (ctx.signal?.aborted) throw Error("Cancelled");
    if (relative.split("/").some(excluded))
      throw Error("Hidden/generated document paths are excluded");
    const source = confined(folder.source_root, relative),
      target = destination(folder, relative);
    if (!fs.statSync(source).isFile())
      throw Error("Select regular document files");
    const size = fs.statSync(source).size;
    if (size > MAX_FILE_BYTES || total + size > MAX_BATCH_BYTES)
      throw Error(
        "Document copy budget: 32 MiB/file, 64 MiB/batch; select a smaller batch",
      );
    const bytes = regularBytes(source, MAX_FILE_BYTES);
    total += bytes.length;
    if (total > MAX_BATCH_BYTES)
      throw Error("Document batch changed beyond its byte budget");
    const hash = sha256(bytes),
      existing = confined(ctx.vault, target);
    if (
      exists(existing) &&
      sha256(regularBytes(existing, MAX_FILE_BYTES)) !== hash
    )
      throw Error(
        "Document destination collision; preserve the existing original",
      );
    return {
      source_path: relative,
      destination: target,
      sha256: hash,
      bytes: bytes.length,
      extraction: extraction(relative),
    };
  });
  if (
    new Set(entries.map((e) => e.destination.toLowerCase())).size !==
    entries.length
  )
    throw Error("Document filenames collide after safe link naming");
  const manifest = {
    version: "1",
    kind: "document_import",
    folder,
    folder_digest: digest(folder),
    vault_root: ctx.vault,
    vault_id: folder.vault_id,
    entries,
    total_bytes: total,
    source_writes: false,
    markdown_safety: markdownSafety(ctx, entries),
    proposed_at: nowStamp(configuredZone(ctx), ctx.now),
  };
  const key = digest(manifest);
  if (Buffer.byteLength(canonical(manifest)) > 4 * 1024 * 1024)
    throw Error("Document manifest exceeds 4 MiB");
  atomicJSON(planFile(ctx, key), manifest);
  return { status: "review_required", proposal_digest: key, manifest };
}
export function loadDocumentImport(ctx: RuntimeContext, key: string) {
  const manifest = readJSON(planFile(ctx, key)),
    folder = selectedFolder(ctx);
  if (
    digest(manifest) !== key ||
    manifest.kind !== "document_import" ||
    manifest.version !== "1" ||
    manifest.source_writes !== false ||
    manifest.vault_root !== ctx.vault ||
    manifest.vault_id !== folder.vault_id ||
    manifest.folder_digest !== digest(folder) ||
    digest(manifest.folder) !== digest(folder) ||
    !Array.isArray(manifest.entries) ||
    !manifest.entries.length ||
    manifest.entries.length > 100 ||
    !Number.isInteger(manifest.total_bytes) ||
    manifest.total_bytes < 0 ||
    manifest.total_bytes > MAX_BATCH_BYTES
  )
    throw Error(
      "Document import identity, folder authorization or digest changed; review again",
    );
  let total = 0;
  for (const entry of manifest.entries) {
    if (
      typeof entry.source_path !== "string" ||
      entry.source_path.length > 2000 ||
      entry.source_path.split("/").some(excluded) ||
      entry.destination !== destination(folder, entry.source_path) ||
      !/^[a-f0-9]{64}$/.test(entry.sha256) ||
      !Number.isInteger(entry.bytes) ||
      entry.bytes < 0 ||
      entry.bytes > MAX_FILE_BYTES ||
      entry.extraction !== extraction(entry.source_path)
    )
      throw Error("Invalid document-import entry");
    confined(folder.source_root, entry.source_path);
    confined(ctx.vault, entry.destination);
    total += entry.bytes;
  }
  if (
    total !== manifest.total_bytes ||
    new Set(manifest.entries.map((e: Metadata) => e.destination.toLowerCase()))
      .size !== manifest.entries.length
  )
    throw Error("Invalid document-import totals or duplicate destinations");
  if (
    digest(manifest.markdown_safety) !==
    digest(markdownSafety(ctx, manifest.entries))
  )
    throw Error(
      "Passive Markdown settings changed; prepare and review the import again",
    );
  return manifest;
}
function inspectPending(
  ctx: RuntimeContext,
  manifest: Metadata,
  entry: Metadata,
) {
  if (
    entry.destination !== destination(manifest.folder, entry.source_path) ||
    !/^[a-f0-9]{64}$/.test(entry.sha256) ||
    !Number.isInteger(entry.bytes) ||
    entry.bytes < 0 ||
    entry.bytes > MAX_FILE_BYTES
  )
    throw Error("Invalid document-import entry");
  const target = confined(ctx.vault, entry.destination);
  if (exists(target)) {
    if (sha256(regularBytes(target, entry.bytes)) !== entry.sha256)
      throw Error("Document destination changed; preserve local bytes");
    return { target, bytes: null };
  }
  const bytes = regularBytes(
    confined(manifest.folder.source_root, entry.source_path),
    entry.bytes,
  );
  if (bytes.length !== entry.bytes || sha256(bytes) !== entry.sha256)
    throw Error("Document source changed; prepare and review a new batch");
  return { target, bytes };
}
/** Native operator approval only; root/path/raw-byte hashes are exact and cannot be model-issued. */
export function approveDocumentImport(
  ctx: RuntimeContext,
  key: string,
  evidence: string,
) {
  if (!evidence?.trim() || evidence.length > 1000)
    throw Error("Explicit document-copy approval required");
  const manifest = loadDocumentImport(ctx, key);
  for (const entry of manifest.entries) inspectPending(ctx, manifest, entry);
  atomicJSON(confined(vaultState(ctx), "document-approvals/" + key + ".json"), {
    proposal_digest: key,
    vault_root: ctx.vault,
    vault_id: manifest.vault_id,
    folder_digest: manifest.folder_digest,
    approved_at: nowStamp(configuredZone(ctx), ctx.now),
    evidence,
  });
}
export async function applyDocumentImport(ctx: RuntimeContext, key: string) {
  const manifest = loadDocumentImport(ctx, key),
    approval = confined(vaultState(ctx), "document-approvals/" + key + ".json");
  if (!exists(approval))
    throw Error("approval_required: document-copy approval is absent");
  const receipt = readJSON(approval);
  if (
    receipt.proposal_digest !== key ||
    receipt.vault_root !== ctx.vault ||
    receipt.vault_id !== manifest.vault_id ||
    receipt.folder_digest !== manifest.folder_digest
  )
    throw Error("Document-copy approval mismatch");
  return withLock(confined(vaultState(ctx), "locks"), "vault-writer", () => {
    const ledgerPath = confined(
        vaultState(ctx),
        "document-applications/" + key + ".json",
      ),
      copied: Metadata[] = [];
    for (const entry of manifest.entries) inspectPending(ctx, manifest, entry);
    for (const entry of manifest.entries) {
      if (ctx.signal?.aborted)
        throw Error("Cancelled; resume the unchanged approved import");
      loadDocumentImport(ctx, key);
      const { target, bytes } = inspectPending(ctx, manifest, entry);
      if (bytes !== null)
        atomic(target, bytes, null, () => {
          loadDocumentImport(ctx, key);
        });
      if (sha256(regularBytes(target, entry.bytes)) !== entry.sha256)
        throw Error("Document-copy post-image mismatch");
      copied.push({
        path: entry.destination,
        sha256: entry.sha256,
        bytes: entry.bytes,
      });
      atomicJSON(ledgerPath, {
        proposal_digest: key,
        copied,
        status: "applying",
      });
    }
    loadDocumentImport(ctx, key);
    for (const entry of manifest.entries) {
      if (ctx.signal?.aborted)
        throw Error("Cancelled; resume the unchanged approved import");
      if (
        sha256(
          regularBytes(confined(ctx.vault, entry.destination), entry.bytes),
        ) !== entry.sha256
      )
        throw Error(
          "Document-copy final verification failed; preserve local bytes",
        );
    }
    atomicJSON(ledgerPath, {
      proposal_digest: key,
      copied,
      status: "verified",
    });
    return {
      status: "verified",
      proposal_digest: key,
      copied,
      knowledge_records_created: false,
      envelope: {
        contract_version: "2",
        source_alias: "onboarding-documents",
        integration: "local-filesystem",
        collection_id: manifest.folder.folder_id,
        access_mode: "read-only",
        discovery_status: "ok_items_available",
        capabilities: { write_back_supported: false },
        items: manifest.entries.map((entry: Metadata) => ({
          content_kind: "file",
          payload: {
            relative_path: entry.destination,
            original_filename: path.basename(entry.source_path),
            file_size_bytes: entry.bytes,
            sha256: entry.sha256,
            bytes_available: true,
          },
        })),
      },
    };
  });
}
