import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { raw } from "../src/platforms/filesystem.ts";
import { registerRuntimeRoute } from "./provider-runtime.ts";
export default function providerChild(pi: ExtensionAPI) {
  const file = process.env.CHRYSALIS_CHILD_TASK;
  if (!file) throw Error("Missing child provider envelope");
  const task = JSON.parse(raw(file).toString("utf8"));
  registerRuntimeRoute(pi, task.runtimeRoute, task.route);
}
