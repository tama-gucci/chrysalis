import fs from "node:fs";
import path from "node:path";
import { spawn, spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { currentWorkspace, assistantRoot } from "../assistant/profile.ts";
import { snapshotWorkspace, mergeWorkspace } from "./workspace.ts";
import {
  withLock,
  confined,
  PACKAGE_ROOT,
  atomicJSON,
  raw,
  sha256,
  atomic,
} from "../platforms/filesystem.ts";
import { excluded } from "./workspace.ts";
import { assertWriterLease } from "./lease.ts";
import { delegationReady, serviceEnvironment } from "./cgroup.ts";

const trustedHelpers = ["job.mjs", "workspace-export.mjs"].map((name) => {
  const file = path.join(PACKAGE_ROOT, "src/execution", name);
  const bytes = raw(file);
  return { name, file, bytes, hash: sha256(bytes) };
});
export interface RunResult {
  output: string;
  exitCode: number;
  truncated: boolean;
  cancelled: boolean;
  wallSeconds: number;
}
/** Architecture-checked seccomp: no network/host IPC or namespace/process escape. */
export function syscallPolicy(arch = process.arch, loopback = false): Buffer {
  const tables: Record<string, { arch: number; denied: number[] }> = {
    arm64: {
      arch: 0xc00000b7,
      denied: [198, 199, 203, 40, 39, 117, 270, 271, 265, 268, 97, 438],
    },
    x64: {
      arch: 0xc000003e,
      denied: [41, 42, 53, 165, 166, 101, 310, 311, 304, 308, 272, 438],
    },
  };
  const t = tables[arch];
  if (!t) throw Error("Execution is unsupported on this architecture");
  const ins: number[][] = [
    [0x20, 0, 0, 4],
    [0x15, 1, 0, t.arch],
    [0x06, 0, 0, 0x00050001],
    [0x20, 0, 0, 0],
  ];
  if (arch === "x64")
    ins.push([0x35, 0, 1, 0x40000000], [0x06, 0, 0, 0x00050001]);
  const socket = arch === "arm64" ? 198 : 41,
    connect = arch === "arm64" ? 203 : 42;
  if (loopback)
    ins.push(
      [0x15, 0, 5, socket],
      [0x20, 0, 0, 16],
      [0x15, 2, 0, 2],
      [0x15, 1, 0, 10],
      [0x06, 0, 0, 0x00050001],
      [0x06, 0, 0, 0x7fff0000],
    );
  for (const nr of t.denied.filter(
    (n) => !loopback || (n !== socket && n !== connect),
  ))
    ins.push([0x15, 0, 1, nr], [0x06, 0, 0, 0x00050001]);
  ins.push([0x06, 0, 0, 0x7fff0000]);
  const b = Buffer.alloc(ins.length * 8);
  ins.forEach(([code, jt, jf, k], i) => {
    b.writeUInt16LE(code, i * 8);
    b[i * 8 + 2] = jt;
    b[i * 8 + 3] = jf;
    b.writeUInt32LE(k, i * 8 + 4);
  });
  return b;
}
export function runnerStatus() {
  if (process.platform !== "linux" || !["arm64", "x64"].includes(process.arch))
    return { available: false, reason: "unsupported_host" };
  const r = spawnSync(
    "/usr/bin/bwrap",
    [
      "--unshare-all",
      "--new-session",
      "--die-with-parent",
      "--ro-bind",
      "/usr",
      "/usr",
      "--symlink",
      "usr/bin",
      "/bin",
      "--symlink",
      "usr/lib",
      "/lib",
      "--proc",
      "/proc",
      "--dev",
      "/dev",
      "/bin/true",
    ],
    { timeout: 5000, stdio: "ignore", env: { PATH: "/usr/bin:/bin" } },
  );
  return {
    available: r.status === 0 && delegationReady(),
    reason:
      r.status !== 0
        ? "bubblewrap_or_namespaces_unavailable"
        : !delegationReady()
          ? "native_cgroup_setup_required"
          : "namespace_and_resource_controls_available",
  };
}
export async function runIsolated(
  state: string,
  command: string,
  options: {
    signal?: AbortSignal;
    timeout?: number;
    vault?: string;
    readOnly?: boolean;
    input?: string;
  } = {},
): Promise<RunResult> {
  if (process.platform !== "linux" || !["arm64", "x64"].includes(process.arch))
    throw Error("No accepted runner for this host");
  if (
    typeof command !== "string" ||
    !command ||
    Buffer.byteLength(command) > 65536
  )
    throw Error("Command limit exceeded");
  if (!delegationReady())
    throw Error("Native runner resource setup required; no host fallback");
  assertWriterLease(state);
  const w = currentWorkspace(state, options.vault);
  if (options.signal?.aborted) throw Error("Execution cancelled");
  const privateRoot = path.join(assistantRoot(state), "runner");
  fs.mkdirSync(privateRoot, { recursive: true, mode: 0o700 });
  if (options.input && Buffer.byteLength(options.input) > 8 * 1024 * 1024)
    throw Error("Runner input limit");
  return withLock(path.join(privateRoot, "locks"), w.id, async () => {
    assertWriterLease(state);
    for (const helper of trustedHelpers)
      if (sha256(raw(helper.file)) !== helper.hash)
        throw Error(
          "Runner source changed; reload and review the new execution policy first",
        );
    const sealed = path.join(privateRoot, "helpers-" + randomUUID());
    fs.mkdirSync(sealed, { mode: 0o700 });
    for (const helper of trustedHelpers)
      atomic(path.join(sealed, helper.name), helper.bytes, null);
    const image = snapshotWorkspace(w.root, privateRoot);
    const received = path.join(privateRoot, randomUUID());
    fs.mkdirSync(received, { mode: 0o700 });
    const filter = path.join(privateRoot, randomUUID() + ".bpf");
    fs.writeFileSync(
      filter,
      syscallPolicy(process.arch, w.network === "loopback"),
      { mode: 0o600, flag: "wx" },
    );
    const jobFile = received + ".job.json",
      inputFile = received + ".input",
      controlFile = received + ".control";
    const node = fs.realpathSync(process.execPath);
    const binds = [
      "--ro-bind",
      "/usr",
      "/usr",
      "--symlink",
      "usr/bin",
      "/bin",
      "--symlink",
      "usr/lib",
      "/lib",
      "--symlink",
      "usr/lib",
      "/lib64",
    ];
    binds.push("--ro-bind", node, "/runner/node");
    const workspaceArgs = options.readOnly
      ? ["--ro-bind", image.directory, "/workspace"]
      : [
          "--ro-bind",
          image.directory,
          "/input",
          "--size",
          "67108864",
          "--tmpfs",
          "/workspace",
          "--ro-bind",
          path.join(sealed, "workspace-export.mjs"),
          "/runner/export.mjs",
        ];
    const script = options.readOnly
      ? command
      : 'cp -a /input/. /workspace/ || exit 125; /bin/bash --noprofile --norc -c "$1"; result=$?; node /runner/export.mjs > /runner/results || exit 125; exit "$result"';
    const args = [
      "--unshare-all",
      "--unshare-user",
      "--disable-userns",
      "--new-session",
      "--die-with-parent",
      ...binds,
      "--proc",
      "/proc",
      "--dev",
      "/dev",
      "--size",
      "33554432",
      "--tmpfs",
      "/tmp",
      "--dir",
      "/tmp/home",
      ...workspaceArgs,
      "--bind-fd",
      "4",
      "/runner/results",
      "--chdir",
      "/workspace",
      "--clearenv",
      "--setenv",
      "PATH",
      "/runner:/usr/bin:/bin",
      "--setenv",
      "HOME",
      "/tmp/home",
      "--setenv",
      "TMPDIR",
      "/tmp",
      "--setenv",
      "LANG",
      "C.UTF-8",
      "--seccomp",
      "3",
      "/usr/bin/prlimit",
      "--nofile=128",
      "--fsize=134217728",
      "--cpu=300",
      "--as=2147483648",
      "/bin/bash",
      "--noprofile",
      "--norc",
      "-c",
      script,
      "chrysalis-task",
      ...(options.readOnly ? [] : [command]),
    ];
    const started = Date.now(),
      limit = 65536;
    let retain = false;
    const unit = "chrysalis-job-" + randomUUID();
    fs.writeFileSync(inputFile, options.input ?? "", {
      mode: 0o600,
      flag: "wx",
    });
    atomicJSON(jobFile, {
      args,
      filter,
      input: inputFile,
      control: controlFile,
    });
    try {
      const result: RunResult = await new Promise((resolve, reject) => {
        const child = spawn(
          "/usr/bin/systemd-run",
          [
            "--user",
            "--wait",
            "--pipe",
            "--quiet",
            "--collect",
            "--unit",
            unit,
            "-p",
            "MemoryMax=536870912",
            "-p",
            "MemorySwapMax=0",
            "-p",
            "TasksMax=64",
            "-p",
            "CPUQuota=100%",
            "-p",
            "RuntimeMaxSec=" +
              Math.min(900, Math.max(1, options.timeout ?? 300)),
            process.execPath,
            path.join(sealed, "job.mjs"),
            jobFile,
          ],
          {
            stdio: ["ignore", "pipe", "pipe"],
            env: serviceEnvironment(),
            detached: true,
          },
        );
        let output = Buffer.alloc(0),
          truncated = false,
          cancelled = false;
        const stop = () => {
          cancelled = true;
          spawnSync(
            "/usr/bin/systemctl",
            ["--user", "kill", "--signal=KILL", "--kill-whom=all", unit],
            { env: serviceEnvironment(), timeout: 3000, stdio: "ignore" },
          );
        };
        const timer = setTimeout(
          stop,
          Math.min(900, Math.max(1, options.timeout ?? 300)) * 1000,
        );
        options.signal?.addEventListener("abort", stop, { once: true });
        const collect = (b: Buffer) => {
          if (output.length + b.length > limit) truncated = true;
          if (output.length < limit)
            output = Buffer.concat([
              output,
              b.subarray(0, limit - output.length),
            ]);
        };
        child.stdout!.on("data", collect);
        child.stderr!.on("data", collect);
        let encoded = "",
          controlBytes = 0,
          final = false,
          invalid = false,
          fileCount = 0,
          decodedBytes = 0;
        const paths = new Set<string>();
        const receive = (data: Buffer) => {
          if (invalid || options.readOnly) return;
          try {
            if ((controlBytes += data.length) > 128 * 1024 * 1024)
              throw Error("Control output limit");
            encoded += data.toString("utf8");
            let at: number;
            while ((at = encoded.indexOf("\n")) >= 0) {
              const line = encoded.slice(0, at);
              encoded = encoded.slice(at + 1);
              const record = JSON.parse(line);
              if (final) throw Error("Trailing output");
              if (record.end === true && Object.keys(record).length === 1) {
                final = true;
                continue;
              }
              if (
                typeof record.path !== "string" ||
                record.path.split("/").some(excluded) ||
                paths.has(record.path) ||
                typeof record.data !== "string" ||
                !/^[a-zA-Z0-9+/]*={0,2}$/.test(record.data) ||
                !Number.isInteger(record.mode) ||
                record.mode < 0 ||
                record.mode > 0o777
              )
                throw Error("Invalid output entry");
              const target = confined(received, record.path),
                bytes = Buffer.from(record.data, "base64");
              if (
                bytes.toString("base64") !== record.data ||
                ++fileCount > 20000 ||
                bytes.length > 16 * 1024 * 1024 ||
                (decodedBytes += bytes.length) > 64 * 1024 * 1024
              )
                throw Error("Output limit");
              paths.add(record.path);
              fs.mkdirSync(path.dirname(target), { recursive: true });
              fs.writeFileSync(target, bytes, {
                flag: "wx",
                mode: record.mode,
              });
            }
            if (encoded.length > 24 * 1024 * 1024)
              throw Error("Output entry limit");
          } catch {
            invalid = true;
            stop();
          }
        };
        const clean = () => {
          clearTimeout(timer);
          options.signal?.removeEventListener("abort", stop);
        };
        child.on("error", () => {
          clean();
          reject(Error("Isolated runner could not start; no host fallback"));
        });
        child.on("close", (code) => {
          clean();
          if (!options.readOnly && !cancelled && fs.existsSync(controlFile)) {
            const size = fs.statSync(controlFile).size;
            if (size > 128 * 1024 * 1024) invalid = true;
            else receive(fs.readFileSync(controlFile));
          }
          if (
            !options.readOnly &&
            !cancelled &&
            (!final || invalid || encoded.length)
          )
            reject(
              Error(
                "Workspace results incomplete; no changes applied\n" +
                  output.toString("utf8").slice(0, 1000),
              ),
            );
          else
            resolve({
              output: output.toString("utf8"),
              exitCode: code ?? 137,
              truncated,
              cancelled,
              wallSeconds: (Date.now() - started) / 1000,
            });
        });
        if (options.signal?.aborted) stop();
      });
      if (!options.readOnly && !result.cancelled) {
        try {
          assertWriterLease(state);
          currentWorkspace(state, options.vault);
          mergeWorkspace(w.root, { ...image, directory: received });
        } catch {
          retain = true;
          const handle = path.basename(received);
          atomicJSON(received + ".conflict.json", {
            workspace: w,
            revisions: image.revisions,
            candidate: received,
          });
          throw Error(
            "Workspace conflict; changes retained privately with recovery handle " +
              handle,
          );
        }
      }
      return result;
    } finally {
      fs.rmSync(sealed, { recursive: true, force: true });
      fs.unlinkSync(filter);
      for (const p of [jobFile, inputFile, controlFile])
        if (fs.existsSync(p)) fs.unlinkSync(p);
      fs.rmSync(image.directory, { recursive: true, force: true });
      if (!retain) fs.rmSync(received, { recursive: true, force: true });
    }
  });
}
