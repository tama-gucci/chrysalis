import os from "node:os";
/** Read-only, opt-in observations; no hostname, username, process list or serial numbers. */
export function environment(args: Record<string, any> = {}) {
  for (const key of Object.keys(args))
    if (!["include_hardware"].includes(key))
      throw new Error("Unknown environment option");
  const result: Record<string, any> = {
    platform: process.platform,
    architecture: process.arch,
    node_version: process.version,
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  };
  if (args.include_hardware)
    Object.assign(result, {
      logical_processors: os.availableParallelism(),
      memory_bytes: os.totalmem(),
    });
  return { status: "observed", environment: result, read_only: true };
}
