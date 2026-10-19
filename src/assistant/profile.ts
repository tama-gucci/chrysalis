import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  atomicJSON,
  exists,
  readJSON,
  rejectRedirects,
  inside,
  PACKAGE_ROOT,
} from "../platforms/filesystem.ts";
import { externalState } from "../storage/context.ts";

export const ROLES = [
  "researcher",
  "reviewer",
  "diagram-maker",
  "worker",
  "observer",
  "reflector",
  "dropper",
] as const;
export type Role = (typeof ROLES)[number];
export interface Route {
  provider: string;
  model: string;
  thinking: "off" | "minimal" | "low" | "medium" | "high" | "xhigh";
}
export interface Workspace {
  id: string;
  root: string;
  dev: number;
  ino: number;
  network?: "off" | "loopback";
}
export interface AssistantProfile {
  version: 1;
  features: {
    execution: boolean;
    memory: boolean;
    observations: boolean;
    specialists: boolean;
    research: boolean;
    browser: boolean;
    lessonCapture: boolean;
  };
  routes: Partial<Record<Role, Route>>;
  preset: "economical" | "balanced" | "thorough";
  workspace?: Workspace;
  limits: {
    concurrency: number;
    turns: number;
    inputChars: number;
    resultChars: number;
    calls: number;
    timeoutSeconds: number;
  };
}
export function defaults(): AssistantProfile {
  return {
    version: 1,
    features: {
      execution: false,
      memory: false,
      observations: false,
      specialists: false,
      research: false,
      browser: false,
      lessonCapture: false,
    },
    routes: {},
    preset: "economical",
    limits: {
      concurrency: 1,
      turns: 8,
      inputChars: 48000,
      resultChars: 6000,
      calls: 24,
      timeoutSeconds: 300,
    },
  };
}
export function assistantRoot(state: string): string {
  return path.join(externalState(state), "assistant");
}
function bounded(n: unknown, min: number, max: number): number {
  if (!Number.isSafeInteger(n) || Number(n) < min || Number(n) > max)
    throw Error("Invalid assistant limit");
  return Number(n);
}
export function validateProfile(p: any): AssistantProfile {
  if (
    !p ||
    p.version !== 1 ||
    !["economical", "balanced", "thorough"].includes(p.preset)
  )
    throw Error("Unsupported assistant settings");
  const d = defaults();
  if (
    !p.features ||
    Object.keys(p.features).some((k) => !(k in d.features)) ||
    Object.values(p.features).some((v) => typeof v !== "boolean")
  )
    throw Error("Invalid assistant capabilities");
  if (
    !p.routes ||
    Object.keys(p.routes).some((k) => !ROLES.includes(k as Role))
  )
    throw Error("Invalid model roles");
  for (const r of Object.values(p.routes) as any[]) {
    if (
      !r ||
      Object.keys(r).some(
        (k) => !["provider", "model", "thinking"].includes(k),
      ) ||
      typeof r.provider !== "string" ||
      !/^[a-zA-Z0-9_.-]{1,100}$/.test(r.provider) ||
      typeof r.model !== "string" ||
      !/^[a-zA-Z0-9_.:/-]{1,160}$/.test(r.model) ||
      !["off", "minimal", "low", "medium", "high", "xhigh"].includes(r.thinking)
    )
      throw Error("Invalid model route");
  }
  if (!p.limits || Object.keys(p.limits).some((k) => !(k in d.limits)))
    throw Error("Invalid usage limits");
  const l = p.limits;
  bounded(l.concurrency, 1, 4);
  bounded(l.turns, 1, 24);
  bounded(l.inputChars, 1000, 96000);
  bounded(l.resultChars, 1000, 16000);
  bounded(l.calls, 1, 100);
  bounded(l.timeoutSeconds, 5, 900);
  if (
    p.workspace &&
    (typeof p.workspace.id !== "string" ||
      !/^[a-z0-9-]{8,80}$/.test(p.workspace.id) ||
      !path.isAbsolute(p.workspace.root) ||
      !Number.isSafeInteger(p.workspace.dev) ||
      !Number.isSafeInteger(p.workspace.ino))
  )
    throw Error("Invalid workspace identity");
  if (
    p.workspace?.network !== undefined &&
    !["off", "loopback"].includes(p.workspace.network)
  )
    throw Error("Invalid workspace network scope");
  if (
    Object.keys(p).some(
      (k) =>
        ![
          "version",
          "features",
          "routes",
          "preset",
          "workspace",
          "limits",
        ].includes(k),
    )
  )
    throw Error("Unknown assistant setting");
  return { ...d, ...p, features: { ...d.features, ...p.features } };
}
export function loadProfile(state: string): AssistantProfile {
  const file = path.join(assistantRoot(state), "profile.json");
  return exists(file) ? validateProfile(readJSON(file)) : defaults();
}
/** Native-only: never export a settings mutation as a model tool. */
export function saveProfile(state: string, p: AssistantProfile) {
  const root = assistantRoot(state);
  rejectRedirects(root);
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  atomicJSON(path.join(root, "profile.json"), validateProfile(p));
}
export function protectedRoots(state: string, vault?: string): string[] {
  const home = os.homedir();
  return [
    PACKAGE_ROOT,
    externalState(state),
    ...[
      ".pi",
      ".ssh",
      ".config",
      ".codex",
      ".gemini",
      ".antigravity",
      ".aws",
      ".gnupg",
      ".local/share/pi",
      ".local/share/chrysalis-browser",
    ].map((p) => path.join(home, p)),
    ...(vault ? [vault] : []),
  ].map((p) => rejectRedirects(path.resolve(p)));
}
export function registerWorkspace(
  state: string,
  root: string,
  vault?: string,
): Workspace {
  root = rejectRedirects(path.resolve(root));
  if (
    protectedRoots(state, vault).some((p) => inside(root, p) || inside(p, root))
  )
    throw Error("Workspace overlaps a protected root");
  const stat = fs.statSync(root);
  if (!stat.isDirectory())
    throw Error("Select an existing workspace directory");
  let count = 0;
  function inspect(dir: string) {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (++count > 20000)
        throw Error("Workspace scan limit; select a smaller directory");
      const file = path.join(dir, entry.name),
        s = fs.lstatSync(file);
      if (
        s.isSymbolicLink() ||
        (!s.isFile() && !s.isDirectory()) ||
        (s.isFile() && s.nlink !== 1) ||
        [".chrysalis-vault.json", ".obsidian", ".pi"].includes(entry.name) ||
        ["System/Memory.md", "System/Life-Roadmap.md"].some((p) =>
          fs.existsSync(path.join(root, p)),
        )
      )
        throw Error(
          "Workspace contains links, special files, vault or host configuration",
        );
      if (entry.name === ".git" && s.isFile())
        throw Error(
          "Linked worktree metadata requires a sanitized development copy",
        );
      if (s.isDirectory()) inspect(file);
    }
  }
  inspect(root);
  return { id: randomUUID(), root, dev: stat.dev, ino: stat.ino };
}
export function currentWorkspace(state: string, vault?: string): Workspace {
  const p = loadProfile(state),
    w = p.workspace;
  if (!p.features.execution || !w)
    throw Error("Choose a workspace through /chrysalis workspace");
  rejectRedirects(w.root);
  const s = fs.statSync(w.root);
  if (
    !s.isDirectory() ||
    s.dev !== w.dev ||
    s.ino !== w.ino ||
    protectedRoots(state, vault).some(
      (r) => inside(w.root, r) || inside(r, w.root),
    )
  )
    throw Error("Workspace identity changed or overlaps a protected root");
  return w;
}
