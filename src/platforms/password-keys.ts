import fs from "node:fs";
import path from "node:path";
import { randomBytes, randomUUID } from "node:crypto";
import { ProtectedSecrets, protectedProcess } from "./secret-store.ts";
import { PACKAGE_ROOT, atomicJSON, exists, readJSON } from "./filesystem.ts";
import type { RuntimeContext } from "../contracts/types.ts";

export interface PasswordKeys {
  get(create: boolean): Promise<Buffer>;
}
/** Protect a random file-encryption key with the existing OS account; no plaintext-key fallback. */
export class OSAccountPasswordKeys implements PasswordKeys {
  private ctx: RuntimeContext;
  private root: string;
  constructor(ctx: RuntimeContext, root: string) {
    this.ctx = ctx;
    this.root = root;
  }
  async get(create: boolean): Promise<Buffer> {
    try {
      const metadata = path.join(this.root, "key.json");
      const wsl =
        process.platform === "linux" &&
        /microsoft|wsl/i.test(
          fs.readFileSync("/proc/sys/kernel/osrelease", "utf8"),
        );
      const backend =
        process.platform === "win32" || wsl
          ? "windows-dpapi"
          : "os-secret-store";
      const dpapi = async (operation: string, bytes: string) =>
        protectedProcess(
          wsl
            ? "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
            : "powershell.exe",
          [
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            fs.readFileSync(
              path.join(PACKAGE_ROOT, "src/platforms/protect.ps1"),
              "utf8",
            ),
          ],
          JSON.stringify({ operation, data: bytes }),
        );
      const store = new ProtectedSecrets(this.ctx);
      if (exists(metadata)) {
        const data = readJSON(metadata);
        if (data.version !== 1 || data.backend !== backend)
          throw Error("unavailable");
        if (
          backend === "os-secret-store" &&
          !/^password-key-[a-f0-9-]{36}$/.test(data.reference)
        )
          throw Error("unavailable");
        const value =
          backend === "windows-dpapi"
            ? await dpapi("unprotect", data.encrypted)
            : (await store.get(data.reference))?.api_key;
        if (typeof value !== "string") throw Error("unavailable");
        const key = Buffer.from(value, "base64");
        if (key.length !== 32) throw Error("unavailable");
        return key;
      }
      if (!create) throw Error("unavailable");
      const key = randomBytes(32),
        value = key.toString("base64");
      if (backend === "windows-dpapi")
        atomicJSON(metadata, {
          version: 1,
          backend,
          encrypted: await dpapi("protect", value),
        });
      else {
        const reference = "password-key-" + randomUUID();
        await store.put(reference, { api_key: value });
        atomicJSON(metadata, { version: 1, backend, reference });
      }
      return key;
    } catch {
      throw Error("password_protection_unavailable_no_plaintext_fallback");
    }
  }
}
