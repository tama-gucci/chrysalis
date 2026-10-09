import fs from "node:fs";
import path from "node:path";
import { spawn } from "node:child_process";
import { PACKAGE_ROOT, confined, atomic, exists, raw } from "./filesystem.ts";
import { vaultState } from "../storage/context.ts";
import type { RuntimeContext } from "../contracts/types.ts";
import type { Credentials, SecretStore } from "../integrations/contracts.ts";

/** No secret appears in argv, shell text, diagnostics or model results. */
export function protectedProcess(
  command: string,
  args: string[],
  input = "",
): Promise<string> {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      windowsHide: true,
      shell: false,
      stdio: ["pipe", "pipe", "ignore"],
    });
    let output = "",
      settled = false;
    const finish = (error?: Error) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      error ? reject(error) : resolve(output.trim());
    };
    const timer = setTimeout(() => {
      child.kill();
      finish(Error("protected_store_unavailable"));
    }, 10000);
    child.on("error", () => finish(Error("protected_store_unavailable")));
    child.stdout.on("data", (chunk) => {
      output += chunk.toString();
      if (output.length > 131072) {
        child.kill();
        finish(Error("protected_store_unavailable"));
      }
    });
    child.stdin.on("error", () => finish(Error("protected_store_unavailable")));
    child.on("close", (code) =>
      finish(code ? Error("protected_store_unavailable") : undefined),
    );
    child.stdin.end(input);
  });
}
export class ProtectedSecrets implements SecretStore {
  private root: string;
  private label: string;
  constructor(ctx: RuntimeContext) {
    this.root = confined(vaultState(ctx), "protected-secrets");
    this.label = path.basename(vaultState(ctx));
  }
  private check(id: string) {
    if (!/^[a-z0-9-]{8,80}$/.test(id)) throw Error("invalid_secret_reference");
  }
  async put(id: string, value: Credentials) {
    this.check(id);
    const bytes = Buffer.from(JSON.stringify(value)).toString("base64");
    if (bytes.length > 65536) throw Error("credential_import_too_large");
    if (process.platform === "win32") {
      const encrypted = await protectedProcess(
        "powershell.exe",
        [
          "-NoProfile",
          "-NonInteractive",
          "-File",
          path.join(PACKAGE_ROOT, "src/platforms/protect.ps1"),
        ],
        JSON.stringify({ operation: "protect", data: bytes }),
      );
      atomic(confined(this.root, id + ".encrypted"), encrypted);
    } else if (process.platform === "darwin") {
      await protectedProcess(
        "security",
        ["-i"],
        `add-generic-password -U -a ${id} -s chrysalis.${this.label} -w ${bytes}\n`,
      );
    } else if (process.platform === "linux") {
      await protectedProcess(
        "secret-tool",
        ["store", "--label=chrysalis", "profile", this.label, "record", id],
        bytes,
      );
    } else throw Error("protected_store_unavailable");
  }
  async get(id: string): Promise<Credentials | undefined> {
    this.check(id);
    let value: string;
    if (process.platform === "win32") {
      const file = confined(this.root, id + ".encrypted");
      if (!exists(file)) return undefined;
      value = await protectedProcess(
        "powershell.exe",
        [
          "-NoProfile",
          "-NonInteractive",
          "-File",
          path.join(PACKAGE_ROOT, "src/platforms/protect.ps1"),
        ],
        JSON.stringify({
          operation: "unprotect",
          data: raw(file, 131072).toString("utf8"),
        }),
      );
    } else if (process.platform === "darwin")
      value = await protectedProcess("security", [
        "find-generic-password",
        "-a",
        id,
        "-s",
        "chrysalis." + this.label,
        "-w",
      ]);
    else if (process.platform === "linux")
      value = await protectedProcess("secret-tool", [
        "lookup",
        "profile",
        this.label,
        "record",
        id,
      ]);
    else throw Error("protected_store_unavailable");
    try {
      const parsed = JSON.parse(Buffer.from(value, "base64").toString("utf8"));
      if (
        !parsed ||
        typeof parsed !== "object" ||
        Array.isArray(parsed) ||
        Object.entries(parsed).some(([key, item]) =>
          key === "expiry_date"
            ? !Number.isFinite(item)
            : ![
                "google_subject",
                "client_id",
                "client_secret",
                "refresh_token",
                "access_token",
                "api_key",
              ].includes(key) ||
              typeof item !== "string" ||
              item.length > 16384,
        )
      )
        throw Error("invalid_protected_record");
      return parsed;
    } catch {
      throw Error("protected_store_unavailable");
    }
  }
  async remove(id: string) {
    this.check(id);
    if (process.platform === "win32") {
      const file = confined(this.root, id + ".encrypted");
      if (exists(file)) fs.unlinkSync(file);
    } else if (process.platform === "darwin")
      await protectedProcess("security", [
        "delete-generic-password",
        "-a",
        id,
        "-s",
        "chrysalis." + this.label,
      ]);
    else if (process.platform === "linux")
      await protectedProcess("secret-tool", [
        "clear",
        "profile",
        this.label,
        "record",
        id,
      ]);
    else throw Error("protected_store_unavailable");
  }
}
