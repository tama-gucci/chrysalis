import fs from "node:fs";
import path from "node:path";
import { collection, readRecord, validate } from "../storage/records.ts";
import {
  configuredZone,
  checkRecord,
  validateRelationships,
} from "./runtime.ts";
import { PACKAGE_ROOT, text, exists } from "../platforms/filesystem.ts";
import type { RuntimeContext, Metadata } from "../contracts/types.ts";

export function doctor(ctx: RuntimeContext) {
  const diagnostics: Metadata[] = [];
  let checked = 0;
  try {
    configuredZone(ctx);
  } catch (e: any) {
    diagnostics.push({ code: "invalid_timezone", message: e.message });
  }
  for (const name of [
    "daily",
    "task",
    "knowledge",
    "diagnostics",
    "environment",
    "integrations",
    "maintenance",
  ]) {
    const file = path.join(
      PACKAGE_ROOT,
      "skills/chrysalis-" + name,
      "SKILL.md",
    );
    if (!exists(file)) {
      diagnostics.push({ code: "missing_skill_dependency", skill: name });
      continue;
    }
    for (const match of text(file).matchAll(/references\/[a-z0-9-]+\.md/g))
      if (!exists(path.join(path.dirname(file), match[0])))
        diagnostics.push({
          code: "missing_skill_dependency",
          skill: name,
          reference: match[0],
        });
  }
  for (const name of [
    "tasks",
    "archive",
    "projects",
    "zettels",
    "sources",
    "daily",
    "system",
  ]) {
    for (const row of collection(ctx.vault, name)) {
      if (++checked > 2000) throw new Error("Diagnostic limit exceeded");
      const result = validate(ctx.vault, row.path, row.document);
      diagnostics.push(...result.diagnostics);
      if (result.valid)
        try {
          const item = {
            path: row.path,
            if_revision: row.revision,
            document: row.document,
          };
          checkRecord(ctx, item);
          validateRelationships(ctx, [item]);
        } catch (e: any) {
          diagnostics.push({
            code: "record_policy",
            path: row.path,
            message: e.message,
          });
        }
    }
  }
  return {
    status: diagnostics.length ? "invalid" : "ok",
    checked,
    checks: [
      "schema",
      "timezone",
      "taxonomy",
      "links",
      "skill_dependencies",
      "multipliers",
    ],
    diagnostics,
  };
}
