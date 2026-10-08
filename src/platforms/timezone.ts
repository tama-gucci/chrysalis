import { spawn } from "node:child_process";
import { zoneName, nowStamp, stamp } from "../time/timezone.ts";

/** Fixed infrastructure code, never a model-supplied executable or argument. */
export async function detectTimezone(signal?: AbortSignal) {
  const env = { ...process.env };
  delete env.TZ;
  const observation = await new Promise<string>((resolve, reject) => {
    const child = spawn(
      process.execPath,
      [
        "--input-type=module",
        "-e",
        "console.log(JSON.stringify({zone:new Intl.DateTimeFormat().resolvedOptions().timeZone,icu:process.versions.icu}))",
      ],
      {
        env,
        shell: false,
        windowsHide: true,
        stdio: ["ignore", "pipe", "ignore"],
        signal,
      },
    );
    let output = "";
    const timeout = setTimeout(() => {
      child.kill();
      reject(new Error("Timezone detection timed out"));
    }, 5000);
    child.stdout.on("data", (b) => {
      output += b;
      if (output.length > 4096) {
        child.kill();
        reject(new Error("Invalid timezone observation"));
      }
    });
    child.on("error", reject);
    child.on("close", (code) => {
      clearTimeout(timeout);
      code === 0
        ? resolve(output)
        : reject(new Error("Timezone detection unavailable"));
    });
  });
  const result = JSON.parse(observation);
  if (!result.icu) throw new Error("Node ICU timezone support is required");
  const timezone = zoneName(result.zone),
    observed_at = nowStamp(timezone);
  return {
    timezone,
    offset: stamp(observed_at, timezone).offset,
    observed_at,
    source: "computer_setting",
    process_override_ignored: process.env.TZ !== undefined,
  };
}
