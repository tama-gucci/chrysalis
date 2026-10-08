import path from "node:path";
import { PACKAGE_ROOT, readJSON } from "../platforms/filesystem.ts";

export function registry() {
  return readJSON(path.join(PACKAGE_ROOT, "resources/field-registry.json"));
}
export function taskDefaults() {
  const fields = registry();
  return {
    status: "todo",
    priority: "normal",
    scheduled: null,
    projects: [],
    ...Object.fromEntries(
      fields.custom_fields
        .filter((f) => f.defaultValue !== undefined)
        .map((f) => [f.key, structuredClone(f.defaultValue)]),
    ),
  };
}
