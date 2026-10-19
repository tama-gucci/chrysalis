import { loadSystemConfig } from "./state.ts";
import { handoffTarget } from "./native.ts";
const c = loadSystemConfig();
if (!c || process.argv[2] !== "handoff")
  throw Error("Use the native Chrysalis handoff entrypoint");
const result = await handoffTarget(c, process.env.CHRYSALIS_HANDOFF_AGENT_DIR);
process.stdout.write(JSON.stringify(result) + "\n");
