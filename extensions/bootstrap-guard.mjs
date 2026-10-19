import path from "node:path";
import { createHash } from "node:crypto";
const canonical = (v) =>
  v === null || typeof v !== "object"
    ? (JSON.stringify(v) ?? "null")
    : Array.isArray(v)
      ? "[" + v.map(canonical).join(",") + "]"
      : "{" +
        Object.keys(v)
          .filter((k) => v[k] !== undefined)
          .sort()
          .map((k) => JSON.stringify(k) + ":" + canonical(v[k]))
          .join(",") +
        "}";
const digest = (v) => createHash("sha256").update(canonical(v)).digest("hex");
/** Dependency-free startup fence; a failed main extension must not leave host tools active. */
export default function bootstrapGuard(pi) {
  let marker;
  pi.events.on("chrysalis:policy-loaded", (value) => {
    marker = value;
  });
  const ready = () => {
    const t = pi.getAllTools().find((t) => t.name === "chrysalis_operation");
    return (
      marker &&
      t &&
      path.resolve(t.sourceInfo.path) ===
        path.join(marker.root, "extensions/chrysalis.ts") &&
      digest({
        name: t.name,
        description: t.description,
        parameters: t.parameters,
      }) === marker.operationIdentity
    );
  };
  const fatal = () => {
    if (!ready()) {
      process.stderr.write(
        "chrysalis required policy failed to load; refusing an unguarded session. Inspect the package/dependency configuration from your normal terminal.\n",
      );
      process.exit(1);
    }
  };
  pi.on("session_start", fatal);
  pi.on("before_agent_start", fatal);
  pi.on("tool_call", () =>
    ready()
      ? undefined
      : { block: true, reason: "Required chrysalis policy is unavailable" },
  );
}
