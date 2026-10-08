import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";
import { Ajv2020 } from "ajv/dist/2020.js";
import addFormats from "ajv-formats";
import { Temporal } from "@js-temporal/polyfill";
import {
  confined,
  raw,
  text,
  sha256,
  exists,
} from "../platforms/filesystem.ts";
import type {
  Metadata,
  Observation,
  Change,
  Diagnostic,
} from "../contracts/types.ts";

export function parse(document: string): {
  frontmatter: Metadata;
  body: string;
} {
  const match = /^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n|$)/.exec(document);
  if (!match) return { frontmatter: {}, body: document };
  const doc = YAML.parseDocument(match[1], {
    schema: "core",
    uniqueKeys: true,
  });
  if (doc.errors.length)
    throw new Error("Invalid YAML frontmatter: " + doc.errors[0].message);
  const fm = doc.toJS({ maxAliasCount: 50 });
  if (!fm || typeof fm !== "object" || Array.isArray(fm))
    throw new Error("Frontmatter must be an object");
  return { frontmatter: fm, body: document.slice(match[0].length) };
}
export const serializeRecord = (fm: Metadata, body = "") =>
  "---\n" +
  YAML.stringify(fm, { lineWidth: 0, aliasDuplicateObjects: false }) +
  "---\n" +
  body;
export function readRecord(vault: string, relative: string): Observation {
  const bytes = raw(confined(vault, relative));
  const document = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  return {
    path: relative,
    document,
    ...parse(document),
    revision: sha256(bytes),
  };
}
export const change = (
  record: Observation,
  fm: Metadata,
  body = record.body,
): Change => ({
  path: record.path,
  if_revision: record.revision,
  document: serializeRecord(fm, body),
});
export function schemaFor(relative: string): string {
  if (/^TaskNotes\/(Tasks|Archive)\/[^/]+\.md$/.test(relative)) return "task";
  if (/^Projects\/[^/]+\/Roadmap\.md$/.test(relative)) return "project";
  if (/^Slipbox\/[^/]+\.md$/.test(relative)) return "zettel";
  if (/^Sources\/[^/]+\.md$/.test(relative)) return "source";
  if (
    /^System\/[^/]+\.md$/.test(relative) ||
    /^Environments\/[a-z][a-z0-9-]{0,47}\.md$/.test(relative)
  )
    return "system_state";
  if (/^Daily\/\d{4}-\d\d-\d\d\.md$/.test(relative)) return "daily_note";
  throw new Error("Only authoritative Markdown collections can be changed");
}
const ajv = new Ajv2020({
  allErrors: true,
  strict: false,
  validateFormats: true,
  addUsedSchema: false,
});
(addFormats as unknown as (a: Ajv2020) => void)(ajv);
ajv.addFormat("tasknotes-date-time", {
  type: "string",
  validate: (value: string) => {
    try {
      if (/(?:Z|[+-]\d\d:\d\d)$/.test(value)) Temporal.Instant.from(value);
      else Temporal.PlainDateTime.from(value);
      return true;
    } catch {
      return false;
    }
  },
});
const validators = new Map<string, any>();
export function validate(
  vault: string,
  relative: string,
  document?: string,
): {
  valid: boolean;
  diagnostics: Diagnostic[];
  frontmatter: Metadata;
  body: string;
} {
  const diagnostics: Diagnostic[] = [];
  try {
    const { frontmatter, body } = parse(
      document ?? text(confined(vault, relative)),
    );
    const type = schemaFor(relative),
      schemaPath = confined(vault, "_types/" + type + ".md");
    if (!exists(schemaPath)) throw new Error("schema_missing: " + type);
    const bytes = raw(schemaPath);
    const key = schemaPath + sha256(bytes);
    let validator = validators.get(key);
    if (!validator) {
      const schema = parse(bytes.toString("utf8")).frontmatter.schema?.value;
      if (!schema) throw new Error("schema_invalid");
      validator = ajv.compile(schema);
      validators.set(key, validator);
    }
    if (!validator(frontmatter))
      for (const error of validator.errors ?? [])
        diagnostics.push({
          code:
            "schema_" +
            error.keyword.replace(
              /[A-Z]/g,
              (s: string) => "_" + s.toLowerCase(),
            ),
          field: error.instancePath,
          message: error.message,
          path: relative,
          severity: "error",
        });
    return { valid: diagnostics.length === 0, diagnostics, frontmatter, body };
  } catch (e: any) {
    return {
      valid: false,
      diagnostics: [
        {
          code: "validation_unavailable",
          message: e.message,
          path: relative,
          severity: "error",
        },
      ],
      frontmatter: {},
      body: "",
    };
  }
}
export function collection(
  vault: string,
  name: string,
  limit = 2000,
): Observation[] {
  const patterns: Record<string, string> = {
    tasks: "TaskNotes/Tasks",
    archive: "TaskNotes/Archive",
    projects: "Projects",
    zettels: "Slipbox",
    sources: "Sources",
    daily: "Daily",
    system: "System",
  };
  const base = patterns[name];
  if (!base) throw new Error("Unknown collection");
  const root = confined(vault, base);
  const result: Observation[] = [];
  let bytes = 0;
  if (!exists(root)) return result;
  for (const entry of fs
    .readdirSync(root, { withFileTypes: true })
    .sort((a, b) => a.name.localeCompare(b.name))) {
    if (
      ["README.md", "example-task.md", "_templates", "Views"].includes(
        entry.name,
      )
    )
      continue;
    const relative =
      name === "projects"
        ? base + "/" + entry.name + "/Roadmap.md"
        : base + "/" + entry.name;
    if (
      name === "projects" ? !entry.isDirectory() : !entry.name.endsWith(".md")
    )
      continue;
    const file = confined(vault, relative);
    if (!exists(file)) continue;
    if (!fs.statSync(file).isFile())
      throw new Error("Unexpected collection entry");
    const row = readRecord(vault, relative);
    bytes += Buffer.byteLength(row.document);
    if (bytes > 16 * 1024 * 1024)
      throw new Error("Collection byte budget exceeded; narrow the collection");
    result.push(row);
    if (result.length > limit) throw new Error("Collection limit exceeded");
  }
  return result;
}
export function registeredTags(vault: string, proposed?: Metadata) {
  const registry =
    (proposed ?? readRecord(vault, "System/Life-Roadmap.md").frontmatter)
      .tag_registry ?? {};
  return new Set<string>([
    ...Object.keys(registry),
    ...Object.values(registry).flatMap((v) => (Array.isArray(v) ? v : [])),
  ]);
}
export function sanitizeUntrusted(content: string, attributes: Metadata = {}) {
  const escape = (s: any) =>
    String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  const attrs = Object.entries(attributes)
    .map(([k, v]) => {
      if (!/^[a-z_][a-z0-9_]*$/.test(k))
        throw new Error("Invalid wrapper attribute");
      return k + '="' + escape(v) + '"';
    })
    .join(" ");
  return (
    "<untrusted_document_payload" +
    (attrs ? " " + attrs : "") +
    ">\n" +
    escape(content) +
    "\n</untrusted_document_payload>"
  );
}
