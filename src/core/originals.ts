import { assertNotPasswordExport } from "../passwords/import.ts";
import path from "node:path";
import { spawn } from "node:child_process";
import {
  confined,
  raw,
  sha256,
  PACKAGE_ROOT,
} from "../platforms/filesystem.ts";
import { sanitizeUntrusted } from "../storage/records.ts";
import type { RuntimeContext, Metadata } from "../contracts/types.ts";

export async function inspectOriginal(
  ctx: RuntimeContext,
  args: Metadata,
): Promise<Metadata> {
  if (
    typeof args.path !== "string" ||
    !args.path.startsWith("Attachments/Originals/")
  )
    throw new Error("Select an in-vault original");
  const bytes = raw(confined(ctx.vault, args.path), 32 * 1024 * 1024),
    suffix = path.extname(args.path).toLowerCase();
  assertNotPasswordExport(bytes);
  const result = {
    status: "observed",
    path: args.path,
    sha256: sha256(bytes),
    bytes: bytes.length,
    link: "[[" + args.path + "]]",
    embed: "![[" + args.path + "]]",
    preview: [
      ".pdf",
      ".png",
      ".jpg",
      ".jpeg",
      ".gif",
      ".webp",
      ".txt",
      ".md",
    ].includes(suffix)
      ? "obsidian"
      : "external_app",
    extraction_status: "not_requested",
  };
  if (!args.extract) return result;
  let extracted: string, coverage: Metadata;
  if ([".txt", ".md", ".csv"].includes(suffix)) {
    if (bytes.length > 1024 * 1024)
      throw new Error("Text extraction limit is 1 MiB");
    extracted = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    coverage = { status: "complete", pages_processed: null, total_pages: null };
  } else if (suffix === ".pdf") {
    const first = args.first_page ?? 1,
      count = args.page_count ?? 10;
    if (
      !Number.isInteger(first) ||
      first < 1 ||
      !Number.isInteger(count) ||
      count < 1 ||
      count > 50
    )
      throw new Error("Select 1–50 PDF pages");
    const parsed = await new Promise<Metadata>((resolve, reject) => {
      const child = spawn(
        process.execPath,
        [
          "--max-old-space-size=128",
          path.join(PACKAGE_ROOT, "src/platforms/pdf-worker.mjs"),
          String(first),
          String(count),
        ],
        {
          shell: false,
          windowsHide: true,
          stdio: ["pipe", "pipe", "ignore"],
          signal: ctx.signal,
        },
      );
      let output = "",
        size = 0;
      const timer = setTimeout(() => {
        child.kill();
        reject(new Error("PDF extraction timed out"));
      }, 15000);
      child.stdout.on("data", (b) => {
        size += b.length;
        if (size > 2 * 1024 * 1024) {
          child.kill();
          reject(new Error("PDF output limit exceeded"));
        } else output += b;
      });
      child.on("error", reject);
      child.stdin.on("error", reject);
      child.on("close", (code) => {
        clearTimeout(timer);
        if (code !== 0)
          return reject(
            new Error("PDF extraction failed or exceeded its resource budget"),
          );
        try {
          resolve(JSON.parse(output));
        } catch (e) {
          reject(e);
        }
      });
      child.stdin.end(bytes);
    });
    if (!parsed.has_text)
      return {
        ...result,
        extraction_status: "ocr_required",
        coverage: parsed.coverage,
      };
    extracted = parsed.text;
    coverage = parsed.coverage;
  } else
    return {
      ...result,
      extraction_status:
        result.preview === "obsidian" ? "ocr_required" : "unsupported_deferred",
    };
  if (Buffer.byteLength(extracted) > 1024 * 1024)
    throw new Error("Extracted text exceeds 1 MiB");
  return {
    ...result,
    extraction_status: "extracted",
    coverage,
    normalized_text_sha256: sha256(
      extracted.replace(/\r\n/g, "\n").replace(/\s+/g, " ").trim(),
    ),
    untrusted_text: sanitizeUntrusted(extracted, {
      source_id: path.basename(args.path, suffix),
      sha256: result.sha256,
    }),
  };
}
