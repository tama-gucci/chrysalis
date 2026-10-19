import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import {
  PACKAGE_ROOT,
  atomic,
  atomicJSON,
  canonical,
  confined,
  digest,
  exists,
  inside,
  raw,
  readJSON,
  rejectRedirects,
  sha256,
  withLock,
} from "../platforms/filesystem.ts";
import { nowStamp, zoneName } from "../time/timezone.ts";
import {
  externalState,
  vaultRoot,
  selectedContext,
} from "../storage/context.ts";

export const LEDGER_PATH = "System/System-Ledger.md";
export const LEDGER_HEADER =
  "# System ledger\n\n<!-- chrysalis-system-ledger:v1 -->\n";
export type Phase =
  | "approved"
  | "building"
  | "build-failed"
  | "built"
  | "installing"
  | "installed"
  | "activating"
  | "uncertain"
  | "degraded"
  | "verified"
  | "failed"
  | "closed";
export interface SystemConfig {
  version: 1;
  mode: "installer" | "installed";
  timeZone?: string;
  configuration: string;
  host: string;
  state: string;
  source: string;
  commands: {
    nix: string;
    sudo: string;
    disko: string;
    lsblk: string;
    findmnt: string;
    facter: string;
    mkpasswd: string;
    nixAgent: string;
    node: string;
  };
}
export interface DiskIdentity {
  path: string;
  kernel: string;
  majorMinor: string;
  size: number;
  serial: string;
  model: string;
}
export interface SystemEvent {
  id: string;
  at: string;
  phase: Phase;
  evidence: Record<string, unknown>;
}
export interface SystemOperation {
  version: 1;
  id: string;
  goal: string;
  approvedAt: string;
  configIdentity: string;
  machine: string;
  configuration: string;
  host: string;
  mode: SystemConfig["mode"];
  disk?: DiskIdentity;
  phase: Phase;
  events: SystemEvent[];
  backendIdentity: string;
  build?: { job: string; source: string; storePath?: string };
  installationId?: string;
  vault?: { root: string; id: string };
  recovery?: { path: string; generation: number };
  installation?: { user: string; name: string; zone: string };
  pending?: {
    id: string;
    tool: string;
    source: string;
    owner?: { pid: number; boot: string; start: string };
  };
}
const phases: Phase[] = [
  "approved",
  "building",
  "build-failed",
  "built",
  "installing",
  "installed",
  "activating",
  "uncertain",
  "degraded",
  "verified",
  "failed",
  "closed",
];
export function boundedText(value: unknown, max: number, name: string): string {
  if (
    typeof value !== "string" ||
    !value.trim() ||
    value.length > max ||
    /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(value)
  )
    throw Error("Invalid " + name);
  return value.trim();
}
export function loadSystemConfig(
  file = process.env.CHRYSALIS_SYSTEM_CONFIG,
): SystemConfig | undefined {
  if (!file) return;
  if (!path.isAbsolute(file))
    throw Error("System configuration must be an absolute native path");
  // NixOS /etc entries intentionally resolve to immutable store files.
  const resolved = fs.realpathSync(file),
    stat = fs.statSync(resolved);
  if (!stat.isFile() || stat.size > 65536)
    throw Error("Invalid native system configuration");
  const c = JSON.parse(fs.readFileSync(resolved, "utf8"));
  if (
    c.version !== 1 ||
    !["installer", "installed"].includes(c.mode) ||
    !/^[a-zA-Z0-9_-]{1,63}$/.test(c.host)
  )
    throw Error("Unsupported native system configuration");
  for (const key of ["configuration", "state", "source"])
    if (
      typeof c[key] !== "string" ||
      !path.isAbsolute(c[key]) ||
      /[\x00-\x1f]/.test(c[key])
    )
      throw Error("Invalid system path");
  for (const key of [
    "nix",
    "sudo",
    "disko",
    "lsblk",
    "findmnt",
    "facter",
    "mkpasswd",
    "nixAgent",
    "node",
  ])
    if (
      typeof c.commands?.[key] !== "string" ||
      !path.isAbsolute(c.commands[key]) ||
      /[\x00-\x1f]/.test(c.commands[key])
    )
      throw Error("Missing pinned system command");
  const root = rejectRedirects(c.configuration),
    state = externalState(c.state);
  if ([PACKAGE_ROOT, state].some((p) => inside(root, p) || inside(p, root)))
    throw Error("System configuration overlaps package or private state");
  if (c.timeZone !== undefined) zoneName(c.timeZone);
  return c as SystemConfig;
}
export function assertSystemVault(c: SystemConfig, selectedVault: string) {
  const root = rejectRedirects(selectedVault);
  externalState(c.state, root);
  if (inside(c.configuration, root) || inside(root, c.configuration))
    throw Error("Vault and system configuration must be disjoint");
}
export const configIdentity = (c: SystemConfig) => digest(c);
export function machineIdentity(): string {
  for (const f of ["/etc/machine-id", "/proc/sys/kernel/random/boot_id"]) {
    try {
      const id = (
        f.startsWith("/proc/")
          ? fs.readFileSync(f, "utf8")
          : raw(f, 256).toString()
      ).trim();
      if (/^[a-f0-9-]{32,36}$/.test(id)) return sha256(id);
    } catch {}
  }
  throw Error("Machine identity unavailable");
}
export function systemRoot(c: SystemConfig) {
  return confined(externalState(c.state), "system");
}
export function configurationIdentity(root: string): string {
  rejectRedirects(root);
  const entries: [string, string][] = [];
  let count = 0,
    total = 0;
  function walk(dir: string) {
    for (const e of fs
      .readdirSync(dir, { withFileTypes: true })
      .sort((a, b) => a.name.localeCompare(b.name))) {
      if (e.name === ".git" || e.name === "result" || e.name === "node_modules")
        continue;
      if (++count > 10000) throw Error("Configuration inventory exceeds limit");
      const p = rejectRedirects(path.join(dir, e.name)),
        s = fs.lstatSync(p);
      if (s.isDirectory()) walk(p);
      else if (s.isFile() && s.nlink === 1) {
        if ((total += s.size) > 32 * 1024 * 1024)
          throw Error("Configuration inventory exceeds byte limit");
        entries.push([path.relative(root, p), sha256(raw(p, 8 * 1024 * 1024))]);
      } else throw Error("Configuration contains a redirect or special file");
    }
  }
  walk(root);
  return digest(entries);
}
export function systemBootId() {
  const boot = fs
    .readFileSync("/proc/sys/kernel/random/boot_id", "utf8")
    .trim();
  if (!/^[a-f0-9-]{36}$/.test(boot))
    throw Error("Kernel boot identity unavailable");
  return boot;
}
function processStart(pid: number) {
  if (!Number.isSafeInteger(pid) || pid < 1)
    throw Error("Invalid process identity");
  const stat = fs.readFileSync("/proc/" + pid + "/stat", "utf8");
  const start = stat
    .slice(stat.lastIndexOf(")") + 2)
    .trim()
    .split(/\s+/)[19];
  if (!/^[0-9]+$/.test(start))
    throw Error("Kernel process identity unavailable");
  return start;
}
export function systemLease(
  id: string,
  tool: string,
  source: string,
): NonNullable<SystemOperation["pending"]> {
  return {
    id,
    tool,
    source,
    owner: {
      pid: process.pid,
      boot: systemBootId(),
      start: processStart(process.pid),
    },
  };
}
export function systemLeaseActive(
  lease: NonNullable<SystemOperation["pending"]>,
) {
  if (!lease.owner) return false;
  try {
    return (
      lease.owner.boot === systemBootId() &&
      lease.owner.start === processStart(lease.owner.pid)
    );
  } catch {
    try {
      process.kill(lease.owner.pid, 0);
      return true;
    } catch (e: any) {
      return e.code !== "ESRCH";
    }
  }
}
/** A transport disconnect cannot prove a privileged descendant has exited. */
export function assertSystemIdle(c: SystemConfig) {
  const file = confined(systemRoot(c), "privileged.json");
  if (!exists(file)) return;
  const activity = readJSON(file);
  if (
    activity.version !== 1 ||
    typeof activity.boot !== "string" ||
    typeof activity.busy !== "boolean"
  )
    throw Error("Invalid privileged activity checkpoint");
  if (activity.busy && activity.boot === systemBootId())
    throw Error(
      "A privileged system process may still be running; restart this system before another mutation",
    );
}
export function beginPrivileged(
  c: SystemConfig,
  operation: string,
  tool: string,
) {
  assertSystemIdle(c);
  const token = randomUUID();
  persistSystemJSON(c, confined(systemRoot(c), "privileged.json"), {
    version: 1,
    token,
    operation,
    tool,
    boot: systemBootId(),
    busy: true,
  });
  return token;
}
export function completePrivileged(c: SystemConfig, token: string) {
  const file = confined(systemRoot(c), "privileged.json");
  const activity = readJSON(file);
  if (activity.token !== token)
    throw Error("Privileged activity checkpoint changed");
  persistSystemJSON(c, file, { ...activity, busy: false });
}
export function syncDirectoryTree(directory: string, stop: string) {
  if (!inside(directory, stop))
    throw Error("Durability path escaped its state root");
  for (let current = directory; ; current = path.dirname(current)) {
    const fd = fs.openSync(rejectRedirects(current), fs.constants.O_RDONLY);
    try {
      fs.fsyncSync(fd);
    } finally {
      fs.closeSync(fd);
    }
    if (path.dirname(current) === current) break;
  }
}
export function persistSystemJSON(
  c: SystemConfig,
  file: string,
  value: unknown,
) {
  if (!inside(file, c.state)) throw Error("Private system state path required");
  atomicJSON(file, value);
  syncDirectoryTree(path.dirname(file), externalState(c.state));
}
function operationFile(c: SystemConfig, id: string) {
  if (!/^[a-f0-9-]{36}$/.test(id)) throw Error("Invalid operation identity");
  return confined(systemRoot(c), "operations/" + id + ".json");
}
export function currentOperation(c: SystemConfig): SystemOperation | undefined {
  const pointer = confined(systemRoot(c), "current.json");
  if (!exists(pointer)) return;
  const p = readJSON(pointer),
    op = readJSON(operationFile(c, p.id));
  if (
    op.version !== 1 ||
    op.id !== p.id ||
    !phases.includes(op.phase) ||
    !Array.isArray(op.events) ||
    op.events.length > 1024
  )
    throw Error("Invalid system receipt");
  return op;
}
/** Native-only. No model tool exposes this authorization function. */
export function approveSystem(
  c: SystemConfig,
  goal: string,
  backendIdentity: string,
  disk?: DiskIdentity,
  selectedVault?: string,
  recovery?: SystemOperation["recovery"],
  installation?: SystemOperation["installation"],
): SystemOperation {
  assertSystemIdle(c);
  goal = boundedText(goal, 4000, "system outcome");
  const old = currentOperation(c);
  if (
    old &&
    (old.pending || !["verified", "failed", "closed"].includes(old.phase))
  )
    throw Error("Resume or close the pending system outcome first");
  if (c.mode === "installer" && !disk)
    throw Error("Installation approval requires an observed exact target disk");
  const now = nowStamp(
    c.timeZone ?? Intl.DateTimeFormat().resolvedOptions().timeZone,
  );
  const op: SystemOperation = {
    version: 1,
    id: randomUUID(),
    goal,
    approvedAt: now,
    configIdentity: configIdentity(c),
    machine: machineIdentity(),
    configuration: c.configuration,
    host: c.host,
    mode: c.mode,
    disk,
    phase: "approved",
    events: [],
    backendIdentity,
    recovery,
    installation,
  };
  if (selectedVault) {
    const root = vaultRoot(selectedVault);
    assertSystemVault(c, root);
    op.vault = {
      root,
      id: readJSON(confined(root, ".chrysalis-vault.json")).vault_id,
    };
  }
  op.events.push({
    id: randomUUID(),
    at: now,
    phase: "approved",
    evidence: {
      configuration: c.configuration,
      host: c.host,
      recovery: recovery ?? null,
      installation: installation ?? null,
      disk: disk
        ? { model: disk.model, size: disk.size, identity: digest(disk) }
        : null,
    },
  });
  fs.mkdirSync(path.dirname(operationFile(c, op.id)), {
    recursive: true,
    mode: 0o700,
  });
  persistSystemJSON(c, operationFile(c, op.id), op);
  persistSystemJSON(c, confined(systemRoot(c), "current.json"), { id: op.id });
  return op;
}
export function requireSystemScope(
  c: SystemConfig,
  backendIdentity?: string,
): SystemOperation {
  const op = currentOperation(c);
  if (!op || ["closed", "failed"].includes(op.phase))
    throw Error("Use native /chrysalis system to authorize an OS outcome");
  if (
    op.configIdentity !== configIdentity(c) ||
    op.configuration !== c.configuration ||
    op.host !== c.host ||
    op.machine !== machineIdentity() ||
    op.mode !== c.mode
  )
    throw Error("System scope changed; native review is required");
  if (op.vault) assertSystemVault(c, op.vault.root);
  let selected: { vault: string } | undefined;
  try {
    selected = selectedContext(c.state);
  } catch {}
  if (selected) assertSystemVault(c, selected.vault);
  if (backendIdentity && op.backendIdentity !== backendIdentity)
    throw Error(
      "System backend registration changed; native review is required",
    );
  return op;
}
export async function recordSystem(
  c: SystemConfig,
  id: string,
  phase: Phase,
  evidence: Record<string, unknown> = {},
  update?: (o: SystemOperation) => void,
) {
  if (!phases.includes(phase) || Buffer.byteLength(canonical(evidence)) > 16384)
    throw Error("Invalid system evidence");
  return withLock(confined(systemRoot(c), "locks"), id, () => {
    const file = operationFile(c, id),
      before = raw(file, 1024 * 1024),
      op = JSON.parse(before.toString()) as SystemOperation;
    if (op.events.length >= 1024)
      throw Error("System receipt event limit reached");
    update?.(op);
    op.phase = phase;
    op.events.push({
      id: randomUUID(),
      at: nowStamp(
        c.timeZone ?? Intl.DateTimeFormat().resolvedOptions().timeZone,
      ),
      phase,
      evidence,
    });
    atomic(file, canonical(op) + "\n", sha256(before));
    syncDirectoryTree(path.dirname(file), externalState(c.state));
    return op;
  });
}
export function assertBackendTarget(c: SystemConfig, input: any) {
  if (input.mode && input.mode !== "nixos")
    throw Error("This outcome authorizes NixOS operations only");
  if (
    input.flake_uri !== undefined &&
    input.flake_uri !== c.configuration + "#" + c.host &&
    input.flake_uri !== "path:" + c.configuration + "#" + c.host
  )
    throw Error("The exact approved flake and host are required");
  if (
    input.attr !== undefined &&
    (typeof input.attr !== "string" || input.attr.length > 1024)
  )
    throw Error("Invalid Nix attribute");
}
export function confinedSystemFile(c: SystemConfig, name: string) {
  if (typeof name !== "string" || name.startsWith("~"))
    throw Error("Use a configuration path without home shorthand");
  if (path.isAbsolute(name)) {
    if (!inside(name, c.configuration))
      throw Error("System file is outside the selected configuration");
    name = path.relative(c.configuration, name);
  }
  if (
    name
      .split(/[\\/]/)
      .some((p) => [".git", ".pi", ".env", "node_modules"].includes(p))
  )
    throw Error("Protected system configuration file");
  return confined(c.configuration, name);
}
export function selectDisks(
  report: any,
  rootDevice: string,
  aliases: Record<string, string>,
): DiskIdentity[] {
  if (!Array.isArray(report?.blockdevices))
    throw Error("Invalid block inventory");
  const selected: DiskIdentity[] = [];
  function containsRoot(d: any): boolean {
    return (
      d["maj:min"] === rootDevice ||
      (d.mountpoints ?? []).some(
        (p: any) => typeof p === "string" && p.length > 0,
      ) ||
      (d.children ?? []).some(containsRoot)
    );
  }
  for (const d of report.blockdevices) {
    if (
      d.type !== "disk" ||
      containsRoot(d) ||
      !Number.isSafeInteger(Number(d.size)) ||
      Number(d.size) <= 0
    )
      continue;
    const id = Object.keys(aliases)
      .sort()
      .find((id) => aliases[id] === d.path && !/-part\d+$/.test(id));
    if (!id || !id.startsWith("/dev/disk/by-id/") || !d.serial) continue;
    selected.push({
      path: id,
      kernel: d.path,
      majorMinor: d["maj:min"],
      size: Number(d.size),
      serial: String(d.serial),
      model: String(d.model ?? "").trim(),
    });
  }
  return selected;
}
export function assertSameDisk(
  expected: DiskIdentity,
  candidates: DiskIdentity[],
) {
  const stable = (d: DiskIdentity) => ({
    path: d.path,
    serial: d.serial,
    size: d.size,
    model: d.model,
  });
  const d = candidates.find((d) => d.path === expected.path);
  if (!d || digest(stable(d)) !== digest(stable(expected)))
    throw Error("Approved disk identity changed or is the running medium");
  return d;
}

const prose = (s: string) =>
  s
    .replace(/[&<>\[\]\x60*_\\#]/g, (c) => "&#" + c.charCodeAt(0) + ";")
    .replace(/\r?\n/g, " ");
/** Fixed machine-owned destination. The model cannot supply Markdown or choose the output path. */
export async function projectSystemLedger(
  c: SystemConfig,
  selectedVault: string,
) {
  const vault = vaultRoot(selectedVault);
  assertSystemVault(c, vault);
  const marker = readJSON(confined(vault, ".chrysalis-vault.json"));
  return withLock(
    confined(systemRoot(c), "locks"),
    "ledger-" + marker.vault_id,
    async () => {
      const directory = confined(systemRoot(c), "operations");
      const operations = exists(directory)
        ? fs
            .readdirSync(directory)
            .filter((p) => /^[a-f0-9-]{36}\.json$/.test(p))
            .sort()
        : [];
      const file = confined(vault, LEDGER_PATH),
        before = exists(file) ? raw(file, 8 * 1024 * 1024) : null;
      let output = before?.toString("utf8") ?? LEDGER_HEADER;
      if (!output.startsWith(LEDGER_HEADER))
        throw Error(
          "Existing system ledger is not machine-owned; preserve and review it",
        );
      let appended = 0;
      for (const name of operations) {
        const id = name.slice(0, -5);
        const op = await withLock(confined(systemRoot(c), "locks"), id, () => {
          const receipt = operationFile(c, id),
            bytes = raw(receipt, 1024 * 1024);
          const current = JSON.parse(bytes.toString()) as SystemOperation;
          if (
            current.id !== id ||
            current.version !== 1 ||
            !current.approvedAt ||
            !Array.isArray(current.events)
          )
            throw Error("Invalid ledger receipt");
          if (
            current.vault &&
            (current.vault.root !== vault ||
              current.vault.id !== marker.vault_id)
          )
            return undefined;
          if (!current.vault) {
            current.vault = { root: vault, id: marker.vault_id };
            atomic(receipt, canonical(current) + "\n", sha256(bytes));
            syncDirectoryTree(path.dirname(receipt), externalState(c.state));
          }
          return current;
        });
        if (!op) continue;
        for (const event of op.events) {
          const token = "<!-- chrysalis-system-event:" + event.id + " -->";
          if (output.includes(token)) continue;
          output +=
            "\n" +
            token +
            "\n## " +
            prose(event.at) +
            " - " +
            prose(event.phase) +
            "\n\n";
          output +=
            "Request: " +
            prose(op.goal) +
            "\n\nOperation: " +
            prose(op.id) +
            "; host: " +
            prose(op.host) +
            ".\n\n";
          output +=
            "Observed evidence: " + prose(canonical(event.evidence)) + "\n";
          appended++;
        }
      }
      if (appended) {
        atomic(file, output, before === null ? null : sha256(before));
        syncDirectoryTree(path.dirname(file), vault);
      }
      return { status: "verified", appended, path: LEDGER_PATH };
    },
  );
}
