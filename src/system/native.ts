import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { spawn } from "node:child_process";
import {
  PACKAGE_ROOT,
  atomic,
  atomicJSON,
  confined,
  digest,
  exists,
  raw,
  readJSON,
  rejectRedirects,
  sha256,
} from "../platforms/filesystem.ts";
import {
  assertSameDisk,
  assertSystemIdle,
  beginPrivileged,
  completePrivileged,
  configurationIdentity,
  currentOperation,
  recordSystem,
  persistSystemJSON,
  syncDirectoryTree,
  selectDisks,
  systemRoot,
  systemLease,
  systemLeaseActive,
  systemBootId,
  type DiskIdentity,
  type SystemConfig,
} from "./state.ts";

export async function command(
  executable: string,
  args: string[],
  options: {
    input?: string;
    signal?: AbortSignal;
    timeout?: number;
    cwd?: string;
    tail?: boolean;
  } = {},
) {
  return new Promise<{ code: number; output: string }>((resolve, reject) => {
    const child = spawn(executable, args, {
      cwd: options.cwd,
      env: { ...process.env, NIX_AGENT_USAGE_LOG: "0" },
      stdio: ["pipe", "pipe", "pipe"],
      detached: process.platform !== "win32",
    });
    let output = "",
      bytes = 0,
      settled = false;
    let interrupted = false,
      killTimer: ReturnType<typeof setTimeout> | undefined;
    const kill = (signal: NodeJS.Signals) => {
      try {
        if (process.platform !== "win32" && child.pid)
          process.kill(-child.pid, signal);
        else child.kill(signal);
      } catch {}
    };
    const stop = () => {
      if (interrupted) return;
      interrupted = true;
      kill("SIGTERM");
      killTimer = setTimeout(() => kill("SIGKILL"), 1500);
    };
    const timer = setTimeout(stop, options.timeout ?? 60_000);
    options.signal?.addEventListener("abort", stop, { once: true });
    if (options.signal?.aborted) stop();
    const cleanup = () => {
      clearTimeout(timer);
      clearTimeout(killTimer);
      options.signal?.removeEventListener("abort", stop);
    };
    const append = (chunk: Buffer) => {
      bytes += chunk.length;
      if (!options.tail && bytes > 4 * 1024 * 1024) {
        stop();
        return;
      }
      output += chunk.toString("utf8");
      if (options.tail) output = output.slice(-4 * 1024 * 1024);
    };
    child.stdout.on("data", append);
    child.stderr.on("data", append);
    child.on("error", (e) => {
      if (!settled) {
        settled = true;
        cleanup();
        reject(e);
      }
    });
    child.on("close", (code, signal) => {
      if (settled) return;
      settled = true;
      cleanup();
      if (signal || interrupted || (!options.tail && bytes > 4 * 1024 * 1024))
        return reject(
          Error(
            "System process interrupted or output limit exceeded; reconcile before retrying",
          ),
        );
      resolve({ code: code ?? 1, output });
    });
    child.stdin.on("error", () => {});
    child.stdin.end(options.input);
  });
}
export async function checked(
  executable: string,
  args: string[],
  options: Parameters<typeof command>[2] = {},
) {
  const r = await command(executable, args, options);
  if (r.code !== 0)
    throw Error(
      "Upstream command failed (" + r.code + "): " + r.output.slice(-3000),
    );
  return r.output.trim();
}
export async function diskInventory(c: SystemConfig): Promise<DiskIdentity[]> {
  const root = await checked(c.commands.findmnt, [
    "--noheadings",
    "--output",
    "MAJ:MIN",
    "/",
  ]);
  const report = JSON.parse(
    await checked(c.commands.lsblk, [
      "--json",
      "--bytes",
      "--output",
      "NAME,PATH,TYPE,SIZE,MODEL,SERIAL,MOUNTPOINTS,PKNAME,MAJ:MIN",
    ]),
  );
  const aliases: Record<string, string> = {};
  for (const e of fs.readdirSync("/dev/disk/by-id")) {
    const p = "/dev/disk/by-id/" + e;
    try {
      aliases[p] = fs.realpathSync(p);
    } catch {}
  }
  return selectDisks(report, root, aliases);
}
export async function inspectTarget(c: SystemConfig, expected: DiskIdentity) {
  const report = JSON.parse(
    await checked(c.commands.lsblk, [
      "--json",
      "--bytes",
      "--output",
      "NAME,PATH,TYPE,SIZE,MODEL,SERIAL,MOUNTPOINTS,MAJ:MIN",
      expected.path,
    ]),
  );
  const disk = report.blockdevices?.find((d: any) => d.type === "disk");
  if (!disk) throw Error("Approved disk is unavailable");
  const observed: DiskIdentity = {
    path: expected.path,
    kernel: disk.path,
    majorMinor: disk["maj:min"],
    size: Number(disk.size),
    serial: String(disk.serial ?? ""),
    model: String(disk.model ?? "").trim(),
  };
  assertSameDisk(expected, [observed]);
  const devices = new Set<string>(),
    crypt: string[] = [];
  const walk = (node: any) => {
    devices.add(node["maj:min"]);
    if (node.type === "crypt") crypt.push(node.path);
    for (const child of node.children ?? []) walk(child);
  };
  walk(disk);
  const root = await checked(c.commands.findmnt, [
    "--noheadings",
    "--output",
    "MAJ:MIN",
    "--mountpoint",
    "/",
  ]);
  if (devices.has(root))
    throw Error("The running installation medium cannot be a target");
  const mounts = JSON.parse(
    await checked(c.commands.findmnt, [
      "--json",
      "--list",
      "--output",
      "TARGET,MAJ:MIN",
    ]),
  ).filesystems as { target: string; "maj:min": string }[];
  return {
    disk: observed,
    devices: [...devices],
    crypt,
    mounts: mounts.filter((m) => devices.has(m["maj:min"])),
    foreignMounts: mounts.filter(
      (m) =>
        (m.target === "/mnt" || m.target.startsWith("/mnt/")) &&
        !devices.has(m["maj:min"]),
    ),
  };
}
export async function unmountRecoveryTarget(
  c: SystemConfig,
  expected: DiskIdentity,
  signal?: AbortSignal,
) {
  const observed = await inspectTarget(c, expected);
  if (
    observed.foreignMounts.length ||
    observed.mounts.some(
      (m) => m.target !== "/mnt" && !m.target.startsWith("/mnt/"),
    )
  )
    throw Error("Recovery refuses mounts outside the approved target subtree");
  for (const mount of observed.mounts
    .map((m) => m.target)
    .sort((a, b) => b.length - a.length))
    await checked(
      c.commands.sudo,
      ["-n", "--", "/run/current-system/sw/bin/umount", mount],
      { signal },
    );
  return inspectTarget(c, expected);
}
function assertExpectedMapper(
  observed: Awaited<ReturnType<typeof inspectTarget>>,
) {
  const mapper = "/dev/mapper/chrysalis-root";
  if (
    exists(mapper) &&
    !observed.crypt.some((p) => fs.realpathSync(p) === fs.realpathSync(mapper))
  )
    throw Error("Existing encryption mapping belongs to a different disk");
}
async function targetAccount(c: SystemConfig, user: string) {
  identifier(user, "account name");
  const apply =
    "cfg: let u = cfg.users.users." +
    user +
    "; s = cfg.programs.chrysalis-pi; l = cfg.disko.devices.disk.main.content.partitions.root.content; in { inherit (u) uid home isNormalUser; gid = (builtins.getAttr u.group cfg.users.groups).gid; inherit (s) user host mode configurationDirectory stateDirectory; luks = { inherit (l) type name passwordFile; contentType = l.content.type; }; }";
  const account = JSON.parse(
    await checked(
      c.commands.nix,
      [
        "eval",
        "--json",
        "--no-write-lock-file",
        c.configuration + "#nixosConfigurations." + c.host + ".config",
        "--apply",
        apply,
      ],
      { timeout: 300000 },
    ),
  );
  if (
    !account.isNormalUser ||
    !Number.isInteger(account.uid) ||
    account.uid < 1 ||
    !Number.isInteger(account.gid) ||
    account.gid < 1 ||
    account.home !== "/home/" + user ||
    account.user !== user ||
    account.host !== c.host ||
    account.mode !== "installed" ||
    account.configurationDirectory !== c.configuration ||
    account.stateDirectory !== c.state
  )
    throw Error(
      "Target account or handoff paths changed; preserve the native installation scope",
    );
  if (
    account.luks.type !== "luks" ||
    account.luks.name !== "chrysalis-root" ||
    account.luks.passwordFile !== "/run/chrysalis/luks.key" ||
    account.luks.contentType !== "btrfs"
  )
    throw Error(
      "The initial installer supports its seeded encrypted Btrfs layout",
    );
  return account as { uid: number; gid: number; home: string };
}
const identifier = (s: string, name: string) => {
  if (!/^[a-z][a-z0-9_-]{0,30}$/.test(s) || s === "root")
    throw Error("Use a normal " + name);
  return s;
};
const nixString = (s: string) =>
  JSON.stringify(s)
    .slice(1, -1)
    .replaceAll("$" + "{", "\\" + "$" + "{");
export interface InstallChoices {
  user: string;
  name: string;
  zone: string;
}
/** Native setup creates a minimal seed. The agent is free to refactor its real Nix files. */
export async function seedTarget(
  c: SystemConfig,
  choices: InstallChoices,
  disk: DiskIdentity,
) {
  identifier(choices.user, "account name");
  identifier(choices.name, "host name");
  new Intl.DateTimeFormat("en", { timeZone: choices.zone });
  if (c.mode !== "installer") throw Error("Target seeding is installer-only");
  const op = currentOperation(c);
  if (!op?.disk || op.phase !== "approved")
    throw Error("Native installation approval is required");
  assertSameDisk(op.disk, await diskInventory(c));
  fs.mkdirSync(rejectRedirects(c.configuration), {
    recursive: true,
    mode: 0o700,
  });
  const values: Record<string, string> = {
    SOURCE: "path:" + c.source,
    HOST: c.host,
    NAME: choices.name,
    USER: choices.user,
    ZONE: choices.zone,
    DISK: disk.path,
  };
  if (!op.installation || digest(op.installation) !== digest(choices))
    throw Error("Installation preferences do not match native approval");
  const progressFile = confined(systemRoot(c), "installation.json");
  const progress = exists(progressFile) ? readJSON(progressFile) : undefined;
  const seed =
    progress?.operation === op.id
      ? progress.seed === true
      : !exists(confined(c.configuration, "flake.nix"));
  persistSystemJSON(c, progressFile, {
    version: 1,
    operation: op.id,
    ...choices,
    seed,
    seeded: false,
  });
  const reuse = !seed;
  for (const name of reuse
    ? []
    : ["flake.nix", "host.nix", "disk.nix", "system.nix"]) {
    let template = fs.readFileSync(
      path.join(PACKAGE_ROOT, "nix/templates/target", name + ".in"),
      "utf8",
    );
    template = template.replace(/@([A-Z]+)@/g, (_all, key) => {
      if (!(key in values)) throw Error("Unknown seed placeholder");
      return nixString(values[key]);
    });
    const destination = confined(
      c.configuration,
      name === "system.nix" ? "modules/system.nix" : name,
    );
    if (!exists(destination)) atomic(destination, template, null);
  }
  if (!reuse && !exists(confined(c.configuration, "hardware.nix")))
    atomic(
      confined(c.configuration, "hardware.nix"),
      "{ hardware.facter.reportPath = ./facter.json; }\n",
      null,
    );
  const report = confined(c.configuration, "facter.json");
  if (exists(report))
    atomic(
      confined(systemRoot(c), "prior-facter.json"),
      raw(report, 8 * 1024 * 1024),
    );
  await checked(c.commands.sudo, ["-n", "--", c.commands.facter, "-o", report]);
  await checked(c.commands.sudo, [
    "-n",
    "--",
    "/run/current-system/sw/bin/chown",
    String(process.getuid!()),
    report,
  ]);
  persistSystemJSON(c, confined(systemRoot(c), "installation.json"), {
    version: 1,
    operation: op.id,
    ...choices,
    seed,
    seeded: true,
  });
}
/** Secrets arrive only from native masked input; never model arguments or subprocess argv. */
export async function saveInstallSecrets(
  c: SystemConfig,
  passphrase: string,
  accountPassword: string,
) {
  if (
    c.mode !== "installer" ||
    passphrase.length < 8 ||
    accountPassword.length < 8
  )
    throw Error("Use passwords of at least eight characters");
  const directory = rejectRedirects("/run/chrysalis");
  fs.mkdirSync(directory, { recursive: true, mode: 0o700 });
  fs.chmodSync(directory, 0o700);
  const hash = await checked(
    c.commands.mkpasswd,
    ["--method=yescrypt", "--stdin"],
    { input: accountPassword + "\n" },
  );
  atomic(confined(directory, "luks.key"), passphrase);
  atomic(confined(directory, "user-password"), hash + "\n");
}
export function runtimeObservation() {
  const link = (p: string) => {
    try {
      return fs.realpathSync(p);
    } catch {
      return null;
    }
  };
  return {
    running: link("/run/current-system"),
    profile: link("/nix/var/nix/profiles/system"),
    boot: exists("/proc/sys/kernel/random/boot_id") ? systemBootId() : null,
  };
}
export function observedGeneration(id?: number) {
  const directory = "/nix/var/nix/profiles";
  if (!exists(directory)) return;
  const current = runtimeObservation().profile;
  const names = fs
    .readdirSync(directory)
    .filter((n) => /^system-[0-9]+-link$/.test(n));
  for (const name of names.sort(
    (a, b) => Number(b.split("-")[1]) - Number(a.split("-")[1]),
  )) {
    const generation = Number(name.split("-")[1]);
    const target = fs.realpathSync(path.join(directory, name));
    if (!/^\/nix\/store\/[a-z0-9]{32}-[^/\n]+$/.test(target)) continue;
    if (id === undefined ? target === current : generation === id)
      return { generation, path: target };
  }
}
/** Reuses upstream installation and mount scripts. No partitioning implementation lives here. */
export async function installTarget(
  c: SystemConfig,
  signal?: AbortSignal,
  recovery = false,
) {
  if (c.mode !== "installer")
    throw Error("Installation is available only in the live profile");
  const op = currentOperation(c);
  if (
    !op?.disk ||
    !(recovery
      ? ["uncertain"].includes(op.phase)
      : ["approved", "built", "build-failed"].includes(op.phase))
  )
    throw Error(
      "An interrupted installation must be reconciled; formatting is not an automatic retry",
    );
  assertSystemIdle(c);
  if (!recovery) assertSameDisk(op.disk, await diskInventory(c));
  assertExpectedMapper(await inspectTarget(c, op.disk));
  if (
    !fs.lstatSync(op.disk.path).isSymbolicLink() ||
    !fs.statSync(op.disk.path).isBlockDevice()
  )
    throw Error("Target is not a stable block-device identity");
  const choices = readJSON(
    confined(systemRoot(c), "installation.json"),
  ) as InstallChoices & { operation: string };
  if (choices.operation !== op.id)
    throw Error("Installation choices belong to a different approval");
  for (const f of ["luks.key", "user-password"])
    if (!exists("/run/chrysalis/" + f))
      throw Error("Use native system setup to supply installation secrets");
  if (!exists(confined(c.configuration, "flake.lock")))
    throw Error("Lock the target before installation");
  const source = configurationIdentity(c.configuration);
  await targetAccount(c, choices.user);
  const lastAttempt = op.events.filter((e) => e.phase === "installing").at(-1);
  if (recovery && lastAttempt?.evidence.source !== source)
    throw Error("Recovery must retain the exact attempted disk configuration");
  if (
    recovery &&
    lastAttempt?.evidence.boot === systemBootId() &&
    typeof op.events.at(-1)?.evidence.exitCode !== "number"
  )
    throw Error(
      "Restart the persistent USB before recovering an interrupted process on this boot",
    );
  if (recovery) await unmountRecoveryTarget(c, op.disk, signal);
  const kinds = JSON.parse(
    await checked(
      c.commands.nix,
      [
        "eval",
        "--json",
        c.configuration +
          "#nixosConfigurations." +
          c.host +
          ".config.disko.devices",
        "--apply",
        "d: builtins.mapAttrs (_: builtins.attrNames) d",
      ],
      { timeout: 300_000 },
    ),
  );
  if (
    JSON.stringify(kinds.disk) !== JSON.stringify(["main"]) ||
    Object.entries(kinds).some(
      ([k, v]) => k !== "disk" && Array.isArray(v) && v.length,
    )
  )
    throw Error(
      "Installation scope allows exactly one disk and no additional storage pools",
    );
  const device = await checked(
    c.commands.nix,
    [
      "eval",
      "--raw",
      c.configuration +
        "#nixosConfigurations." +
        c.host +
        ".config.disko.devices.disk.main.device",
    ],
    { timeout: 300_000 },
  );
  if (device !== op.disk.path)
    throw Error("Evaluated disk does not match native approval");
  if (configurationIdentity(c.configuration) !== source)
    throw Error("Configuration changed during installation preflight");
  await checked("/run/current-system/sw/bin/sync", ["-f", c.configuration]);
  // disko-install itself builds its exact install closure before executing its disk script.
  const lease = systemLease("install-" + randomUUID(), "install", source);
  await recordSystem(
    c,
    op.id,
    "installing",
    {
      source,
      boot: systemBootId(),
      lock: exists(confined(c.configuration, "flake.lock"))
        ? configurationIdentity(c.configuration)
        : null,
    },
    (o) => {
      if (o.pending || o.phase !== op.phase)
        throw Error("Concurrent OS operation detected");
      o.pending = lease;
    },
  );
  const args = [
    "-n",
    "--",
    c.commands.disko,
    "--mode",
    recovery ? "mount" : "format",
    "--flake",
    c.configuration + "#" + c.host,
    "--disk",
    "main",
    op.disk.path,
    "--mount-point",
    "/mnt",
    "--write-efi-boot-entries",
    "--extra-files",
    "/run/chrysalis/user-password",
    "var/lib/chrysalis/user-password",
  ];
  const privileged = beginPrivileged(c, op.id, "install");
  let r: Awaited<ReturnType<typeof command>>;
  try {
    r = await command(c.commands.sudo, args, {
      timeout: 3_600_000,
      signal,
      tail: true,
    });
  } catch (e) {
    await recordSystem(
      c,
      op.id,
      "uncertain",
      {
        stage: "installation",
        reason:
          "Upstream process interrupted; inspect existing partitions before recovery",
      },
      (o) => {
        if (o.pending?.id === lease.id) delete o.pending;
      },
    );
    throw e;
  }
  completePrivileged(c, privileged);
  if (r.code !== 0) {
    await recordSystem(
      c,
      op.id,
      "uncertain",
      {
        stage: "installation",
        exitCode: r.code,
      },
      (o) => {
        if (o.pending?.id === lease.id) delete o.pending;
      },
    );
    throw Error(
      "disko-install failed; retain the private command output and reconcile before recovery: " +
        r.output.slice(-3000),
    );
  }
  await recordSystem(
    c,
    op.id,
    "installed",
    { source, bootVerified: false },
    (o) => {
      if (o.pending?.id !== lease.id)
        throw Error("Installation receipt changed during upstream execution");
      delete o.pending;
      o.installationId = op.id;
    },
  );
  return { status: "installed", operation: op.id, needsHandoff: true };
}
export async function reconcileInstalled(c: SystemConfig) {
  const op = currentOperation(c);
  if (!op) return { status: "unavailable" };
  const observation = runtimeObservation();
  if (op.pending && systemLeaseActive(op.pending))
    return { status: op.phase, inflight: true, ...observation };
  if (op.pending && ["system-write", "system-edit"].includes(op.pending.tool)) {
    let source: string;
    try {
      source = configurationIdentity(c.configuration);
    } catch {
      source = "unreadable";
    }
    await recordSystem(
      c,
      op.id,
      "approved",
      {
        stage: op.pending.tool,
        source,
        reason:
          "Configuration edit interrupted; inspect files and build a fresh diff",
      },
      (o) => {
        delete o.pending;
        delete o.build;
      },
    );
    return { status: "approved", ...observation };
  }
  const marker = "/var/lib/chrysalis/install.json";
  if (c.mode === "installed" && exists(marker)) {
    const proof = readJSON(marker);
    const rootUuid = await checked(c.commands.findmnt, [
      "--noheadings",
      "--output",
      "UUID",
      "/",
    ]);
    if (
      proof.operation === op.id &&
      proof.host === c.host &&
      proof.running === observation.running &&
      proof.rootUuid === rootUuid &&
      op.mode === "installer" &&
      op.phase === "installed"
    ) {
      await recordSystem(
        c,
        op.id,
        "verified",
        {
          ...observation,
          bootVerified: true,
          recovery: "Use the retained USB mount-only recovery flow",
        },
        (o) => {
          o.installationId = proof.operation;
        },
      );
      return { status: "verified", ...observation };
    }
  }
  if (op.phase === "activating" || op.phase === "installing" || op.pending) {
    const attempt = op.events.filter((e) => e.phase === "activating").at(-1);
    const expected = attempt?.evidence.expectedRunning;
    const matched =
      typeof expected === "string" &&
      observation.running === expected &&
      observation.profile === expected;
    await recordSystem(
      c,
      op.id,
      "uncertain",
      {
        ...observation,
        stage:
          op.pending?.tool ??
          (op.phase === "installing" ? "install" : "switch"),
        expectedClosureObserved: matched,
        reason: matched
          ? "Expected closure observed after interruption; service health still requires explicit verification"
          : "Previous process did not record completion; no automatic activation or formatting retry",
      },
      (o) => {
        delete o.pending;
      },
    );
  }
  return { status: currentOperation(c)!.phase, ...observation };
}
export function installedSystemProfile(root: string) {
  const directory = confined(rejectRedirects(root), "nix/var/nix/profiles");
  let target = fs.readlinkSync(path.join(directory, "system"));
  if (!target.startsWith("/nix/store/")) {
    if (!/^system-[0-9]+-link$/.test(target))
      throw Error("Invalid installed system profile");
    target = fs.readlinkSync(path.join(directory, target));
  }
  if (
    !/^\/nix\/store\/[a-z0-9]{32}-[^/\n]+$/.test(target) ||
    !fs.lstatSync(rejectRedirects(root + target)).isDirectory()
  )
    throw Error("Installed system closure is unavailable");
  return target;
}
/**
 * Durable copy intent contains only hashes. Retry may replace this installation's
 * partial copy, while any target bytes changed since that intent remain protected.
 */
export function copyHandoffFile(
  c: SystemConfig,
  operation: string,
  bytes: Buffer,
  destination: string,
  targetRoot: string,
) {
  const op = currentOperation(c);
  if (op?.id !== operation || op.phase !== "installed")
    throw Error("No matching installed handoff receipt");
  if (bytes.length > 32 * 1024 * 1024)
    throw Error("Handoff file exceeds its supported limit");
  const relative = path.relative(rejectRedirects(targetRoot), destination);
  if (confined(targetRoot, relative) !== destination)
    throw Error("Handoff target escaped its mounted root");
  const journalFile = confined(systemRoot(c), "handoff-" + operation + ".json");
  const journal = exists(journalFile)
    ? readJSON(journalFile)
    : { version: 1, operation, files: {} };
  if (
    journal.version !== 1 ||
    journal.operation !== operation ||
    !journal.files ||
    Object.keys(journal.files).length > 4096
  )
    throw Error("Invalid handoff copy journal");
  if (exists(destination)) {
    const stat = fs.lstatSync(destination);
    if (!stat.isFile() || stat.nlink !== 1)
      throw Error("Handoff refuses redirected or special target state");
  }
  const before = exists(destination)
    ? sha256(raw(destination, 32 * 1024 * 1024))
    : null;
  const after = sha256(bytes);
  const prior = journal.files[relative] as
    | { before: string | null; after: string }
    | undefined;
  if (
    prior
      ? before !== prior.before && before !== prior.after
      : before !== null && before !== after
  )
    throw Error(
      "Handoff target changed; preserve and inspect the installed checkpoint",
    );
  if (!prior || prior.after !== after) {
    if (!prior && Object.keys(journal.files).length >= 4096)
      throw Error("Handoff file count exceeds its supported limit");
    journal.files[relative] = { before, after };
    persistSystemJSON(c, journalFile, journal);
  }
  if (before !== after) atomic(destination, bytes, before);
  syncDirectoryTree(path.dirname(destination), targetRoot);
}
/** Called as root by the native adapter, never with model-selected destinations. */
export async function handoffTarget(c: SystemConfig, agentDirectory?: string) {
  if (process.getuid?.() !== 0 || c.mode !== "installer")
    throw Error("Handoff requires the native live installation helper");
  const op = currentOperation(c);
  if (op?.phase !== "installed" || !op.disk)
    throw Error("No completed installation to hand off");
  const operation = op.id;
  const choices = readJSON(
    confined(systemRoot(c), "installation.json"),
  ) as InstallChoices;
  const installedSource = op.events
    .filter((e) => e.phase === "installed")
    .at(-1)?.evidence.source;
  if (installedSource !== configurationIdentity(c.configuration))
    throw Error("Installed configuration changed before handoff");
  const account = await targetAccount(c, choices.user);
  assertExpectedMapper(await inspectTarget(c, op.disk));
  const script = await checked(
    c.commands.nix,
    [
      "build",
      "--no-link",
      "--print-out-paths",
      c.configuration +
        "#nixosConfigurations." +
        c.host +
        ".config.system.build.mountScript",
    ],
    { timeout: 3_600_000 },
  );
  if (!/^\/nix\/store\/[a-z0-9]{32}-[^\n]+$/.test(script))
    throw Error("Unexpected mount script output");
  await checked(script, [], { timeout: 60_000 });
  const mounted = await inspectTarget(c, op.disk);
  const mountedRoot = await checked(c.commands.findmnt, [
    "--noheadings",
    "--output",
    "MAJ:MIN",
    "--mountpoint",
    "/mnt",
  ]);
  if (!mounted.devices.includes(mountedRoot) || mounted.foreignMounts.length)
    throw Error("Mounted target ancestry does not match the approved disk");
  let copiedFiles = 0,
    copiedBytes = 0;
  function copyDirectory(source: string, target: string) {
    rejectRedirects(source);
    rejectRedirects(target);
    fs.mkdirSync(target, { recursive: true, mode: 0o700 });
    for (const item of fs.readdirSync(source, { withFileTypes: true })) {
      if (["locks", ".git", "result"].includes(item.name)) continue;
      if (
        source === systemRoot(c) &&
        /^handoff-[a-f0-9-]{36}\.json$/.test(item.name)
      )
        continue;
      const from = rejectRedirects(path.join(source, item.name)),
        to = rejectRedirects(path.join(target, item.name)),
        s = fs.lstatSync(from);
      if (s.isDirectory()) copyDirectory(from, to);
      else if (s.isFile() && s.nlink === 1) {
        if (++copiedFiles > 4096 || (copiedBytes += s.size) > 512 * 1024 * 1024)
          throw Error("Handoff checkpoint exceeds its supported limit");
        copyHandoffFile(c, operation, raw(from, 32 * 1024 * 1024), to, "/mnt");
      } else throw Error("Handoff refuses redirected or special state");
      fs.chownSync(to, account.uid, account.gid);
    }
    fs.chownSync(target, account.uid, account.gid);
  }
  try {
    const marker = "/mnt/var/lib/chrysalis/install.json";
    if (exists(marker)) {
      const previous = readJSON(marker);
      if (previous.operation !== op.id)
        throw Error(
          "Mounted system belongs to a different installation receipt",
        );
      if (previous.handoffComplete)
        return {
          status: "handoff-ready",
          operation: op.id,
          bootVerified: false,
          unchanged: true,
        };
    }
    copyDirectory(c.configuration, "/mnt" + c.configuration);
    copyDirectory(c.state, "/mnt" + c.state);
    const installedRunning = installedSystemProfile("/mnt");
    fs.chownSync("/mnt/var/lib/chrysalis/user-password", 0, 0);
    fs.chmodSync("/mnt/var/lib/chrysalis/user-password", 0o600);
    const rootUuid = await checked(c.commands.findmnt, [
      "--noheadings",
      "--output",
      "UUID",
      "/mnt",
    ]);

    if (agentDirectory) {
      const native = "/mnt" + "/home" + "/" + choices.user + "/.pi/agent";
      fs.mkdirSync(rejectRedirects(native), { recursive: true, mode: 0o700 });
      for (const name of ["auth.json", "settings.json"]) {
        const source = rejectRedirects(path.join(agentDirectory, name));
        if (!exists(source)) continue;
        const s = fs.lstatSync(source);
        if (!s.isFile() || s.size > 512 * 1024)
          throw Error("Invalid native Pi state");
        copyHandoffFile(
          c,
          op.id,
          raw(source, 512 * 1024),
          confined(native, name),
          "/mnt",
        );
        fs.chmodSync(confined(native, name), 0o600);
        fs.chownSync(confined(native, name), account.uid, account.gid);
      }
      fs.chownSync(native, account.uid, account.gid);
      fs.chownSync(path.dirname(native), account.uid, account.gid);
      fs.chownSync("/mnt" + account.home, account.uid, account.gid);
    }
    await checked("/run/current-system/sw/bin/sync", []);
    atomicJSON(marker, {
      operation: op.id,
      host: c.host,
      running: installedRunning,
      rootUuid,
      handoffComplete: true,
    });
    syncDirectoryTree(path.dirname(marker), path.dirname(marker));
    await checked("/run/current-system/sw/bin/sync", []);
    for (const name of ["luks.key", "user-password"])
      fs.rmSync(confined("/run/chrysalis", name), { force: true });
  } finally {
    await checked("/run/current-system/sw/bin/umount", ["-R", "/mnt"]);
  }
  return { status: "handoff-ready", operation: op.id, bootVerified: false };
}
