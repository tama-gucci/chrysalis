import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import {
  exists,
  readJSON,
  confined,
  rejectRedirects,
  rejectPackageAncestry,
  inside,
  PACKAGE_ROOT,
} from "../platforms/filesystem.ts";
import type { RuntimeContext } from "../contracts/types.ts";

export function vaultRoot(selected: string): string {
  const root = rejectPackageAncestry(selected);
  if (!exists(root) || !fs.statSync(root).isDirectory())
    throw new Error("Select an existing initialized vault");
  const marker = readJSON(confined(root, ".chrysalis-vault.json"));
  if (
    marker.schema_version !== "1" ||
    !/^[a-z0-9-]{8,80}$/.test(marker.vault_id)
  )
    throw new Error("Unsupported or missing vault identity");
  return root;
}
export function externalState(selected: string, vault?: string): string {
  const root = rejectPackageAncestry(selected);
  for (const boundary of [PACKAGE_ROOT, ...(vault ? [vault] : [])])
    if (inside(root, boundary) || inside(boundary, root))
      throw new Error(
        "Execution state must be disjoint from vault and package",
      );
  return root;
}
export function runtimeContext(
  vault: string,
  state: string,
  now?: string,
): RuntimeContext {
  vault = vaultRoot(vault);
  state = externalState(state, vault);
  return { vault, state, now };
}
export function vaultState(ctx: RuntimeContext): string {
  const id = readJSON(confined(ctx.vault, ".chrysalis-vault.json")).vault_id;
  return confined(externalState(ctx.state, ctx.vault), id);
}
export function defaultStateRoot(): string {
  const override = process.env.CHRYSALIS_STATE_ROOT;
  if (override) return externalState(override);
  const parent =
    process.platform === "win32"
      ? (process.env.LOCALAPPDATA ?? os.homedir())
      : (process.env.XDG_STATE_HOME ??
        path.join(os.homedir(), ".local", "state"));
  return externalState(path.join(parent, "chrysalis"));
}
export function selectedContext(state = defaultStateRoot()): RuntimeContext {
  state = externalState(state);
  const selected =
    process.env.CHRYSALIS_VAULT_PATH ??
    (exists(confined(state, "profile.json"))
      ? readJSON(confined(state, "profile.json")).vault_root
      : undefined);
  if (!selected)
    throw new Error(
      "Run /chrysalis onboard or explicitly select an initialized vault",
    );
  const ctx = runtimeContext(selected, state);
  const binding = confined(state, "profile.json");
  if (
    exists(binding) &&
    readJSON(binding).vault_root === ctx.vault &&
    readJSON(binding).vault_id !==
      readJSON(confined(ctx.vault, ".chrysalis-vault.json")).vault_id
  )
    throw new Error("Vault identity changed; review a new binding");
  return ctx;
}

/** Unconfigured differs from a broken or changed authoritative binding. */
export function optionalSelectedContext(
  state = defaultStateRoot(),
): RuntimeContext | undefined {
  if (
    !process.env.CHRYSALIS_VAULT_PATH &&
    !exists(confined(state, "profile.json"))
  )
    return;
  return selectedContext(state);
}
