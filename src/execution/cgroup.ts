import fs from "node:fs";
import { spawnSync } from "node:child_process";
import { randomUUID } from "node:crypto";
import { executionRuntime, type ExecutionRuntime } from "./runtime.ts";
export function serviceEnvironment() {
  if (!process.getuid) throw Error("Linux user service manager required");
  const runtime = "/run/user/" + process.getuid();
  return {
    PATH: "/usr/bin:/bin",
    XDG_RUNTIME_DIR: runtime,
    DBUS_SESSION_BUS_ADDRESS: "unix:path=" + runtime + "/bus",
  };
}
export function delegationReady(runtime?: ExecutionRuntime) {
  try {
    if (!fs.statSync("/run/user/" + process.getuid!() + "/bus").isSocket())
      return false;
    const host = runtime ?? executionRuntime();
    const code =
      "const fs=require('node:fs');const p=fs.readFileSync('/proc/self/cgroup','utf8').trim().split('\\n').find(s=>s.startsWith('0::')).slice(3);const read=f=>fs.readFileSync('/sys/fs/cgroup'+p+'/'+f,'utf8').trim();const cpu=read('cpu.max').split(' ');process.exit(read('memory.max')==='536870912'&&read('memory.swap.max')==='0'&&read('pids.max')==='64'&&cpu[0]!=='max'&&Number(cpu[0])<=Number(cpu[1])?0:1)";
    const result = spawnSync(
      host.systemdRun,
      [
        "--user",
        "--wait",
        "--pipe",
        "--quiet",
        "--collect",
        "--unit",
        "chrysalis-prereq-" + randomUUID(),
        "-p",
        "MemoryMax=536870912",
        "-p",
        "MemorySwapMax=0",
        "-p",
        "TasksMax=64",
        "-p",
        "CPUQuota=100%",
        "-p",
        "RuntimeMaxSec=5",
        host.node,
        "-e",
        code,
      ],
      { env: serviceEnvironment(), stdio: "ignore", timeout: 10000 },
    );
    return result.status === 0;
  } catch {
    return false;
  }
}
