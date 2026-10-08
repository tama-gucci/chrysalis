// A fixed text-only parser process. No paths, URLs or executable code come from the document.
import DOMMatrix from "@thednp/dommatrix";
import fs from "node:fs";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
globalThis.DOMMatrix = DOMMatrix;
// Fail closed on parser upgrades. The two guards bound encoded streams and every
// DecodeStream allocation before evaluation; a parser catch cannot hide a limit hit.
const worker = fs.readFileSync(
  fileURLToPath(import.meta.resolve("pdfjs-dist/legacy/build/pdf.worker.mjs")),
);
if (
  createHash("sha256").update(worker).digest("hex") !==
  "bb422f60804477de4a0b09091d8347a916a387755ed1cbad24ccaec1d09c78bf"
)
  throw Error("Unreviewed PDF parser build");
let limited = false;
globalThis.__chrysalisPdfBudget = (size) => {
  if (size > 8 * 1024 * 1024) {
    limited = true;
    throw Error("PDF stream budget exceeded");
  }
};
let guarded = worker.toString("utf8");
for (const [needle, replacement] of [
  [
    "  ensureBuffer(requested) {\n    const buffer = this.buffer;",
    "  ensureBuffer(requested) {\n    globalThis.__chrysalisPdfBudget(Math.max(requested, this.minBufferLength));\n    const buffer = this.buffer;",
  ],
  [
    "    this.dict = dict;\n  }\n  get length() {",
    "    this.dict = dict;\n    if (dict) globalThis.__chrysalisPdfBudget(this.end - this.start);\n  }\n  get length() {",
  ],
]) {
  if (guarded.split(needle).length !== 2)
    throw Error("PDF guard insertion changed");
  guarded = guarded.replace(needle, replacement);
}
globalThis.pdfjsWorker = await import(
  "data:text/javascript;base64," + Buffer.from(guarded).toString("base64")
);
const chunks = [];
let bytes = 0;
for await (const chunk of process.stdin) {
  bytes += chunk.length;
  if (bytes > 32 * 1024 * 1024) throw Error("PDF input limit exceeded");
  chunks.push(chunk);
}
const first = Number(process.argv[2]),
  count = Number(process.argv[3]);
if (
  !Number.isInteger(first) ||
  first < 1 ||
  !Number.isInteger(count) ||
  count < 1 ||
  count > 50
)
  throw Error("Invalid page selection");
const { getDocument } = await import("pdfjs-dist/legacy/build/pdf.mjs");
const task = getDocument({
  data: new Uint8Array(Buffer.concat(chunks)),
  verbosity: 0,
  isEvalSupported: false,
  useWasm: false,
  disableFontFace: true,
  useSystemFonts: false,
  isOffscreenCanvasSupported: false,
  isImageDecoderSupported: false,
  useWorkerFetch: false,
  disableAutoFetch: true,
  disableStream: true,
  disableRange: true,
  enableXfa: false,
  stopAtErrors: true,
});
const doc = await task.promise;
try {
  if (first > doc.numPages) throw Error("First page exceeds document");
  const end = Math.min(doc.numPages, first + count - 1),
    parts = [];
  let size = 0,
    hasText = false;
  for (let n = first; n <= end; n++) {
    const page = await doc.getPage(n),
      content = await page.getTextContent();
    if (limited) throw Error("PDF stream budget exceeded");
    const text = content.items.map((i) => i.str ?? "").join(" ");
    size += Buffer.byteLength(text);
    if (size > 1024 * 1024) throw Error("Extracted text limit exceeded");
    hasText ||= !!text.trim();
    parts.push("Page " + n + ":\n" + text);
    page.cleanup();
  }
  const output = {
    text: parts.join("\n\n"),
    has_text: hasText,
    coverage: {
      status: first === 1 && end === doc.numPages ? "complete" : "partial",
      pages_processed: end - first + 1,
      total_pages: doc.numPages,
    },
  };
  const json = JSON.stringify(output);
  if (Buffer.byteLength(json) > 2 * 1024 * 1024)
    throw Error("PDF output limit exceeded");
  process.stdout.write(json);
} finally {
  await task.destroy();
}
