import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { assistantRoot } from "../assistant/profile.ts";
import {
  atomic,
  confined,
  readJSON,
  raw,
  sha256,
  digest,
} from "../platforms/filesystem.ts";
const leasePath = (state: string) =>
  confined(assistantRoot(state), "workspace-writer.json");
function processStart(pid: number) {
  if (process.platform !== "linux")
    throw Error("Worker process identity requires Linux");
  try {
    const stat = fs.readFileSync("/proc/" + pid + "/stat", "utf8");
    return stat.slice(stat.lastIndexOf(")") + 2).split(" ")[19];
  } catch (e: any) {
    if (e.code === "ENOENT") return null;
    throw e;
  }
}
export function writerLeaseStatus(state: string) {
  const file = leasePath(state);
  if (!fs.existsSync(file)) return null;
  const record = readJSON(file);
  if (
    !Number.isSafeInteger(record.pid) ||
    typeof record.task !== "string" ||
    typeof record.token !== "string"
  )
    throw Error("Invalid workspace writer lease");
  // A tmux child can outlive its parent. Uncertain ownership is never automatically discarded.
  return record;
}
export function assertWriterLease(state: string) {
  const owner = writerLeaseStatus(state);
  if (
    owner &&
    (path.resolve(process.env.CHRYSALIS_CHILD_TASK ?? "") !==
      path.resolve(owner.task) ||
      (owner.childPid && owner.childPid !== process.pid))
  )
    throw Error(
      "Workspace is leased to a worker; wait, interrupt or use native reconciliation",
    );
}
export function claimWorkerLease(state: string, task: string) {
  const file = leasePath(state),
    bytes = raw(file),
    record = JSON.parse(bytes.toString("utf8"));
  if (record.task !== task || record.childPid)
    throw Error("Worker lease cannot be inherited or resumed silently");
  atomic(
    file,
    JSON.stringify({
      ...record,
      childPid: process.pid,
      childStart: processStart(process.pid),
    }),
    sha256(bytes),
  );
}
export function reserveWriterLease(state: string, task: string) {
  if (writerLeaseStatus(state))
    throw Error("Another worker owns this workspace");
  const file = leasePath(state),
    record = { pid: process.pid, task, token: randomUUID() };
  atomic(file, JSON.stringify(record), null);
  let released = false;
  return () => {
    if (!released) {
      if (fs.existsSync(file)) {
        const owner = readJSON(file);
        if (owner.token !== record.token) return true;
        if (
          !Number.isSafeInteger(owner.childPid) ||
          typeof owner.childStart !== "string" ||
          processStart(owner.childPid) === owner.childStart
        )
          return false;
        fs.unlinkSync(file);
      }
      released = true;
      return true;
    }
    return true;
  };
}
export function reconcileWriterLease(state: string, approved: string) {
  const record = writerLeaseStatus(state);
  if (!record || digest(record) !== approved)
    throw Error("Worker lease review changed");
  if (
    !Number.isSafeInteger(record.childPid) ||
    typeof record.childStart !== "string"
  )
    throw Error(
      "Worker startup identity is uncertain; retain the lease and inspect/terminate its tmux window before operator recovery",
    );
  if (processStart(record.childPid) === record.childStart)
    throw Error("Worker is still alive; interrupt it before reconciliation");
  if (digest(writerLeaseStatus(state)) !== approved)
    throw Error("Worker lease changed");
  fs.unlinkSync(leasePath(state));
  return { status: "released", child_verified_exited: true };
}
