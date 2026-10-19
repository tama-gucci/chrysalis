import { Worker } from "node:worker_threads";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import path from "node:path";
import { PACKAGE_ROOT } from "../platforms/filesystem.ts";
const require = createRequire(import.meta.url);
export function sanitizeSVG(code: string) {
  if (typeof code !== "string" || code.length > 64000)
    throw Error("SVG source limit");
  const parts: string[] = [];
  let start = -1,
    quote = "";
  for (let i = 0; i < code.length; i++) {
    const char = code[i];
    if (start < 0) {
      if (char === "<") start = i;
      continue;
    }
    if (char === "<") throw Error("Malformed SVG markup");
    if (quote) {
      if (char === quote) quote = "";
    } else if (char === '"' || char === "'") quote = char;
    else if (char === ">") {
      parts.push(code.slice(start, i + 1));
      start = -1;
    }
  }
  if (start >= 0) throw Error("Malformed SVG markup");
  const markup = parts.join("");
  if (
    code.length > 64000 ||
    !/^\s*<svg\b/i.test(code) ||
    /&(?!(?:amp|lt|gt|quot|apos);)|<!|<\?/i.test(code) ||
    /\\|\bon[a-z]+\s*=|\b(href|src|style|base)\s*=|url\s*\(|expression\s*\(|javascript:/i.test(
      markup,
    )
  )
    throw Error("SVG must contain inert geometry/text only");
  const allowed = new Set([
    "svg",
    "g",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "path",
    "text",
    "tspan",
    "defs",
    "marker",
    "title",
    "desc",
    "lineargradient",
    "radialgradient",
    "stop",
  ]);
  for (const match of code.matchAll(/<\/?\s*([a-zA-Z0-9:_-]+)/g))
    if (!allowed.has(match[1].toLowerCase()))
      throw Error("Unsupported SVG element");
  return code;
}
const escape = (s: string) =>
  s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
let rendering = 0;
export async function mermaidVisual(code: string) {
  if (rendering >= 2)
    throw Error("Diagram rendering busy; retry after the current preview");
  rendering++;
  try {
    if (code.length > 16000 || code.split("\n").length > 200)
      throw Error("Diagram source limit");
    const art: any = await new Promise((resolve, reject) => {
      const worker = new Worker(
        pathToFileURL(
          path.join(PACKAGE_ROOT, "src/learning/visual-worker.mjs"),
        ),
        {
          workerData: {
            code,
            module: pathToFileURL(require.resolve("grok-mermaid")).href,
          },
          resourceLimits: {
            maxOldGenerationSizeMb: 64,
            maxYoungGenerationSizeMb: 16,
          },
        },
      );
      const timer = setTimeout(() => {
        void worker.terminate();
        reject(Error("Diagram rendering timed out"));
      }, 3000);
      worker.once("message", (v) => {
        clearTimeout(timer);
        resolve(v);
        void worker.terminate();
      });
      worker.once("error", () => {
        clearTimeout(timer);
        reject(Error("Diagram renderer unavailable"));
      });
    });
    if (!art || art.plain.length > 300 || art.width > 300)
      throw Error("Diagram cannot be rendered within bounds");
    const svg =
      '<svg xmlns="http://www.w3.org/2000/svg" width="' +
      Math.max(200, art.width * 10 + 32) +
      '" height="' +
      (art.plain.length * 20 + 32) +
      '"><rect width="100%" height="100%" fill="#ffffff"/><g fill="#172033" font-family="monospace" font-size="16">' +
      art.plain
        .map(
          (line: string, i: number) =>
            '<text x="16" y="' +
            (30 + i * 20) +
            '" xml:space="preserve">' +
            escape(line) +
            "</text>",
        )
        .join("") +
      "</g></svg>";
    return {
      svg: sanitizeSVG(svg),
      preview: art.plain.join("\n").slice(0, 6000),
      warnings: art.warnings ?? [],
      visual_inspected: false,
    };
  } finally {
    rendering--;
  }
}
