import test from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import bootstrap from "../extensions/bootstrap-guard.mjs";
import { digest, PACKAGE_ROOT } from "../src/platforms/filesystem.ts";
import path from "node:path";
test("startup fence rejects absent/drifted policy and requires the loaded operation origin", () => {
  const handlers: any = {},
    events: any = {};
  let tools: any[] = [];
  bootstrap({
    events: { on: (name: string, f: any) => (events[name] = f) },
    on: (name: string, f: any) => (handlers[name] = f),
    getAllTools: () => tools,
  });
  assert.equal(handlers.tool_call().block, true);
  const definition = {
    name: "chrysalis_operation",
    description: "Synthetic operation",
    parameters: { type: "object" },
  };
  events["chrysalis:policy-loaded"]({
    root: PACKAGE_ROOT,
    operationIdentity: digest(definition),
  });
  tools = [
    {
      ...definition,
      sourceInfo: { path: path.join(PACKAGE_ROOT, "extensions/chrysalis.ts") },
    },
  ];
  assert.equal(handlers.tool_call(), undefined);
  tools[0].sourceInfo.path = path.join(PACKAGE_ROOT, "extensions/other.ts");
  assert.equal(handlers.tool_call().block, true);
  tools[0].sourceInfo.path = path.join(PACKAGE_ROOT, "extensions/chrysalis.ts");
  tools[0].description = "Overridden";
  assert.equal(handlers.tool_call().block, true);
  const url = new URL("../extensions/bootstrap-guard.mjs", import.meta.url)
    .href;
  const r = spawnSync(
    process.execPath,
    [
      "--input-type=module",
      "-e",
      `import guard from ${JSON.stringify(url)};const h={};guard({events:{on:()=>{}},getAllTools:()=>[],on:(n,f)=>h[n]=f});h.session_start();console.log("unsafe-continued");`,
    ],
    { encoding: "utf8", timeout: 5000 },
  );
  assert.equal(r.status, 1);
  assert.match(r.stderr, /refusing an unguarded session/);
  assert(!r.stdout.includes("unsafe-continued"));
});
