import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { preset, DIRECTORIES, pluginLock } from "../obsidian/preset.ts";
import {
  externalState,
  runtimeContext,
  vaultState,
} from "../storage/context.ts";
import { validate, readRecord } from "../storage/records.ts";
import { zoneName, nowStamp } from "../time/timezone.ts";
import {
  PACKAGE_ROOT,
  rejectPackageAncestry,
  confined,
  exists,
  raw,
  sha256,
  digest,
  canonical,
  atomic,
  atomicJSON,
  readJSON,
  files,
  withLock,
} from "../platforms/filesystem.ts";

export interface SetupPlan {
  contract_version: "2";
  kind: "create" | "repair";
  vault_root: string;
  state_root: string;
  vault_id: string;
  timezone: string;
  files: Record<string, { sha256: string; bytes: number }>;
  directories: string[];
  settings: Record<string, any>;
  plugins: any[];
  timezone_observation?: Record<string, any>;
}
function checkName(root: string) {
  if (
    /[<>:"|?*\x00-\x1f]/.test(path.basename(root)) ||
    /[. ]$/.test(path.basename(root)) ||
    /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\.|$)/i.test(path.basename(root))
  )
    throw new Error("Invalid vault name");
}
export function prepareOnboarding(input: {
  vault: string;
  state: string;
  timezone: string;
  observation?: Record<string, any>;
}) {
  const root = rejectPackageAncestry(input.vault);
  checkName(root);
  const state = externalState(input.state, root),
    timezone = zoneName(input.timezone);
  if (exists(root) && fs.readdirSync(root).length)
    throw new Error(
      "Initialization requires an empty directory; use the saved setup receipt to resume",
    );
  const id = randomUUID(),
    assets = preset(timezone, id),
    settings: Record<string, any> = {};
  for (const [relative, bytes] of assets)
    if (relative.endsWith(".json") && !relative.endsWith("manifest.json"))
      settings[relative] = JSON.parse(bytes.toString("utf8"));
  const plan: SetupPlan = {
    contract_version: "2",
    kind: "create",
    vault_root: root,
    state_root: state,
    vault_id: id,
    timezone,
    ...(input.observation ? { timezone_observation: input.observation } : {}),
    files: Object.fromEntries(
      [...assets].map(([relative, bytes]) => [
        relative,
        { sha256: sha256(bytes), bytes: bytes.length },
      ]),
    ),
    directories: DIRECTORIES,
    settings,
    plugins: pluginLock().plugins.map((p) => ({
      id: p.id,
      version: p.version,
      minAppVersion: p.minAppVersion,
      release: p.release,
    })),
  };
  return savePlan(plan, assets);
}
function savePlan(plan: SetupPlan, assets: Map<string, Buffer>) {
  const key = digest(plan),
    stage = confined(plan.state_root, "staging/" + key);
  for (const [relative, bytes] of assets)
    atomic(confined(stage, relative), bytes);
  for (const relative of ["System/Memory.md", "System/Life-Roadmap.md"]) {
    if (!assets.has(relative)) continue;
    const check = validate(
      stage,
      relative,
      assets.get(relative)!.toString("utf8"),
    );
    if (!check.valid)
      throw new Error(
        "Invalid setup records: " + JSON.stringify(check.diagnostics),
      );
  }
  atomicJSON(confined(plan.state_root, "setups/" + key + ".json"), plan);
  atomicJSON(confined(plan.state_root, "pending-setup.json"), {
    proposal_digest: key,
  });
  return { status: "review_required", proposal_digest: key, plan };
}
export function loadSetup(state: string, key: string): SetupPlan {
  state = externalState(state);
  if (!/^[a-f0-9]{64}$/.test(key)) throw new Error("Invalid setup digest");
  const plan = readJSON(confined(state, "setups/" + key + ".json"));
  if (
    digest(plan) !== key ||
    plan.contract_version !== "2" ||
    plan.state_root !== state
  )
    throw new Error("Setup identity changed");
  rejectPackageAncestry(plan.vault_root);
  externalState(state, plan.vault_root);
  checkName(plan.vault_root);
  for (const [relative, expected] of Object.entries(plan.files) as Array<
    [string, any]
  >) {
    const bytes = raw(
      confined(state, "staging/" + key + "/" + relative),
      16 * 1024 * 1024,
    );
    if (sha256(bytes) !== expected.sha256 || bytes.length !== expected.bytes)
      throw new Error("Setup staged resource changed");
  }
  return plan;
}
export function approveSetup(state: string, key: string, evidence: string) {
  const plan = loadSetup(state, key);
  if (exists(confined(state, "setup-cancellations/" + key + ".json")))
    throw new Error("Setup was replaced; review the current proposal");
  if (!evidence.trim() || evidence.length > 1000)
    throw new Error("Operator evidence required");
  atomicJSON(confined(state, "setup-approvals/" + key + ".json"), {
    proposal_digest: key,
    vault_root: plan.vault_root,
    vault_id: plan.vault_id,
    evidence,
    approved_at: nowStamp(plan.timezone),
  });
}
export async function applySetup(
  state: string,
  key: string,
  options: { failAfter?: number } = {},
) {
  const plan = loadSetup(state, key),
    approvalPath = confined(state, "setup-approvals/" + key + ".json");
  if (exists(confined(state, "setup-cancellations/" + key + ".json")))
    throw new Error("Setup was replaced; review the current proposal");
  if (!exists(approvalPath)) throw new Error("approval_required");
  const approval = readJSON(approvalPath);
  if (
    approval.proposal_digest !== key ||
    approval.vault_root !== plan.vault_root ||
    approval.vault_id !== plan.vault_id
  )
    throw new Error("Setup approval mismatch");
  return withLock(confined(state, "setup-locks"), plan.vault_root, () => {
    const root = plan.vault_root,
      ledgerPath = confined(state, "setup-applications/" + key + ".json"),
      ledger = exists(ledgerPath) ? readJSON(ledgerPath) : { applied: {} };
    if (plan.kind === "create" && exists(root))
      for (const file of files(root)) {
        const relative = path.relative(root, file).split(path.sep).join("/");
        if (!plan.files[relative])
          throw new Error(
            "Unexpected file in setup target; preserve user edits",
          );
      }
    if (
      plan.kind === "repair" &&
      readJSON(confined(root, ".chrysalis-vault.json")).vault_id !==
        plan.vault_id
    )
      throw new Error("Repair identity changed");
    for (const [relative, expected] of Object.entries(plan.files)) {
      const file = confined(root, relative);
      if (
        exists(file) &&
        sha256(raw(file, 16 * 1024 * 1024)) !== expected.sha256
      )
        throw new Error("Setup collision: " + relative);
    }
    fs.mkdirSync(root, { recursive: true });
    for (const directory of plan.directories)
      fs.mkdirSync(confined(root, directory), { recursive: true });
    const ordered = Object.keys(plan.files)
      .filter((f) => f !== ".chrysalis-vault.json")
      .sort();
    if (plan.files[".chrysalis-vault.json"])
      ordered.push(".chrysalis-vault.json");
    let count = 0;
    for (const relative of ordered) {
      const target = confined(root, relative),
        expected = plan.files[relative];
      if (exists(target)) {
        if (sha256(raw(target, 16 * 1024 * 1024)) !== expected.sha256)
          throw new Error("Setup postimage changed");
        ledger.applied[relative] = expected.sha256;
        atomicJSON(ledgerPath, ledger);
        continue;
      }
      if (options.failAfter !== undefined && count >= options.failAfter)
        return {
          status: "interrupted",
          proposal_digest: key,
          applied: ledger.applied,
        };
      const bytes = raw(
        confined(state, "staging/" + key + "/" + relative),
        16 * 1024 * 1024,
      );
      if (sha256(bytes) !== expected.sha256)
        throw new Error("Staged bytes changed");
      atomic(target, bytes, null);
      if (sha256(raw(target, 16 * 1024 * 1024)) !== expected.sha256)
        throw new Error("Setup verification failed");
      ledger.applied[relative] = expected.sha256;
      atomicJSON(ledgerPath, ledger);
      count++;
    }
    for (const [relative, expected] of Object.entries(plan.files))
      if (
        sha256(raw(confined(root, relative), 16 * 1024 * 1024)) !==
        expected.sha256
      )
        throw new Error("Setup final verification failed");
    const ctx = runtimeContext(root, state);
    if (plan.kind === "create" && plan.timezone_observation)
      atomicJSON(
        confined(vaultState(ctx), "timezone-observation.json"),
        plan.timezone_observation,
      );
    atomicJSON(confined(state, "profile.json"), {
      vault_root: root,
      vault_id: plan.vault_id,
    });
    const ownedPath = confined(vaultState(ctx), "owned-assets.json"),
      previous = exists(ownedPath) ? readJSON(ownedPath) : {};
    atomicJSON(ownedPath, { ...previous, ...plan.files });
    ledger.status = "verified";
    atomicJSON(ledgerPath, ledger);
    return {
      status: "ready_to_open",
      vault_root: root,
      vault_id: plan.vault_id,
      proposal_digest: key,
      ui_verified: false,
      minimum_obsidian_version: pluginLock()
        .plugins.map((p) => p.minAppVersion)
        .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }))
        .at(-1),
    };
  });
}
export function cancelPendingSetup(state: string) {
  state = externalState(state);
  const pending = pendingSetup(state);
  if (!pending) return;
  if (
    pending.approved ||
    exists(
      confined(
        state,
        "setup-applications/" + pending.proposal_digest + ".json",
      ),
    )
  )
    throw new Error(
      "Approved or interrupted setup must resume its exact scope; it cannot be replaced",
    );
  atomicJSON(
    confined(state, "setup-cancellations/" + pending.proposal_digest + ".json"),
    {
      proposal_digest: pending.proposal_digest,
      reason: "Operator restarted unapproved onboarding",
    },
  );
  fs.unlinkSync(confined(state, "pending-setup.json"));
}
export function pendingSetup(state: string) {
  const file = confined(externalState(state), "pending-setup.json");
  if (!exists(file)) return null;
  const key = readJSON(file).proposal_digest;
  const plan = loadSetup(state, key),
    ledger = confined(state, "setup-applications/" + key + ".json");
  return exists(ledger) && readJSON(ledger).status === "verified"
    ? null
    : {
        proposal_digest: key,
        plan,
        approved: exists(confined(state, "setup-approvals/" + key + ".json")),
      };
}
export function prepareRepair(ctx: { vault: string; state: string }) {
  const runtime = runtimeContext(ctx.vault, ctx.state),
    marker = readJSON(confined(runtime.vault, ".chrysalis-vault.json")),
    memoryPath = confined(runtime.vault, "System/Memory.md");
  const ownedPath = confined(vaultState(runtime), "owned-assets.json");
  if (!exists(ownedPath))
    throw new Error("Owned resource receipt missing; do not infer ownership");
  const timezone = zoneName(
    readRecord(runtime.vault, "System/Memory.md").frontmatter.user_profile
      .timezone,
  );
  const owned = readJSON(ownedPath),
    all = preset(timezone, marker.vault_id),
    assets = new Map<string, Buffer>(),
    modified: string[] = [];
  for (const [relative, expected] of Object.entries(owned) as Array<
    [string, any]
  >) {
    if (
      [
        "System/Memory.md",
        "System/Life-Roadmap.md",
        ".chrysalis-vault.json",
      ].includes(relative)
    )
      continue;
    const file = confined(runtime.vault, relative);
    if (exists(file)) {
      if (sha256(raw(file, 16 * 1024 * 1024)) !== expected.sha256)
        modified.push(relative);
      continue;
    }
    const bytes = all.get(relative);
    if (bytes && sha256(bytes) === expected.sha256) assets.set(relative, bytes);
  }
  if (!assets.size)
    return { status: "no_changes", modified_preserved: modified };
  const plan: SetupPlan = {
    contract_version: "2",
    kind: "repair",
    vault_root: runtime.vault,
    state_root: runtime.state,
    vault_id: marker.vault_id,
    timezone,
    files: Object.fromEntries(
      [...assets].map(([relative, bytes]) => [
        relative,
        { sha256: sha256(bytes), bytes: bytes.length },
      ]),
    ),
    directories: [],
    settings: Object.fromEntries(
      [...assets]
        .filter(([p]) => p.endsWith("data.json"))
        .map(([p, b]) => [p, JSON.parse(b.toString("utf8"))]),
    ),
    plugins: [],
  };
  return { ...savePlan(plan, assets), modified_preserved: modified };
}
