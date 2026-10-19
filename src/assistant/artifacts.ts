import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { assistantRoot } from "./profile.ts";
import {
  atomic,
  withSyncLock,
  atomicJSON,
  confined,
  readJSON,
  raw,
  sha256,
  digest,
} from "../platforms/filesystem.ts";
import type { RuntimeContext } from "../contracts/types.ts";
export function storeArtifact(
  state: string,
  kind: "svg" | "png" | "mermaid",
  data: Buffer,
  provenance: any = {},
) {
  return withSyncLock(assistantRoot(state), "private-output-retention", () => {
    if (data.length > 2 * 1024 * 1024) throw Error("Artifact limit");
    const root = path.join(assistantRoot(state), "artifacts");
    fs.mkdirSync(root, { recursive: true, mode: 0o700 });
    if (fs.readdirSync(root).length >= 200)
      throw Error("Artifact retention limit; review private outputs");
    const id = randomUUID();
    atomic(confined(root, id + "." + kind), data, null);
    atomicJSON(confined(root, id + ".json"), {
      version: 1,
      id,
      kind,
      sha256: sha256(data),
      bytes: data.length,
      provenance,
      authority: "private_unreviewed_artifact",
    });
    return {
      handle: id,
      kind,
      sha256: sha256(data),
      bytes: data.length,
      authority: "private_unreviewed_artifact",
    };
  });
}

export function inspectArtifact(state: string, id: string) {
  if (!/^[a-f0-9-]{36}$/.test(id)) throw Error("Invalid artifact handle");
  const root = path.join(assistantRoot(state), "artifacts"),
    metadata = readJSON(confined(root, id + ".json"));
  if (
    metadata.version !== 1 ||
    metadata.id !== id ||
    !["svg", "png", "mermaid"].includes(metadata.kind)
  )
    throw Error("Artifact metadata changed");
  const bytes = raw(confined(root, id + "." + metadata.kind), 2 * 1024 * 1024);
  if (sha256(bytes) !== metadata.sha256) throw Error("Artifact bytes changed");
  return { metadata, bytes };
}
export function prepareArtifactAdoption(ctx: RuntimeContext, id: string) {
  const { metadata } = inspectArtifact(ctx.state, id);
  if (!["png", "svg"].includes(metadata.kind))
    throw Error(
      "Keep Mermaid in a reviewed note code block; original adoption supports image artifacts",
    );
  const marker = readJSON(confined(ctx.vault, ".chrysalis-vault.json"));
  const plan = {
    version: 1,
    kind: "artifact_original",
    handle: id,
    vault: ctx.vault,
    vault_id: marker.vault_id,
    path: "Attachments/Originals/Generated/" + id + "." + metadata.kind,
    sha256: metadata.sha256,
    bytes: metadata.bytes,
    provenance: metadata.provenance,
  };
  return { ...plan, digest: digest(plan) };
}
/** Native-only copy; no roadmap, source record or atomic-note authority is implied. */
export function adoptArtifact(
  ctx: RuntimeContext,
  id: string,
  reviewedDigest: string,
) {
  const plan = prepareArtifactAdoption(ctx, id);
  if (plan.digest !== reviewedDigest) throw Error("Artifact adoption changed");
  const { bytes } = inspectArtifact(ctx.state, id);
  const target = confined(ctx.vault, plan.path);
  atomic(target, bytes, null);
  if (sha256(raw(target, 2 * 1024 * 1024)) !== plan.sha256)
    throw Error("Artifact verification failed");
  atomicJSON(
    confined(assistantRoot(ctx.state), "artifact-receipts/" + id + ".json"),
    plan,
  );
  return {
    status: "verified",
    original: plan.path,
    sha256: plan.sha256,
    records_approved: false,
  };
}
