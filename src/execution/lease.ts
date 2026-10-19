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
  withSyncLock,
} from "../platforms/filesystem.ts";
const leasePath = (state: string) =>
  confined(assistantRoot(state), "workspace-writer.json");
export function processStart(pid: number) {
  if (!Number.isSafeInteger(pid) || pid < 1)
    throw Error("Invalid worker process identity");
  if (process.platform !== "linux")
    throw Error("Worker process identity requires Linux");
  try {
    const stat = fs.readFileSync("/proc/" + pid + "/stat", "utf8");
    const start = stat.slice(stat.lastIndexOf(")") + 2).split(" ")[19];
    if (!/^[0-9]+$/.test(start ?? "") || BigInt(start) <= 0n)
      throw Error("Invalid worker kernel identity");
    return start;
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
    record.pid < 1 ||
    ((record.childPid !== undefined || record.childStart !== undefined) &&
      (!Number.isSafeInteger(record.childPid) ||
        record.childPid < 1 ||
        typeof record.childStart !== "string" ||
        !/^[0-9]+$/.test(record.childStart) ||
        BigInt(record.childStart) <= 0n)) ||
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
      (owner.childPid &&
        (owner.childPid !== process.pid ||
          processStart(process.pid) !== owner.childStart)))
  )
    throw Error(
      "Workspace is leased to a worker; wait, interrupt or use native reconciliation",
    );
}
const transition = <T>(state: string, action: () => T) =>
  withSyncLock(assistantRoot(state), "workspace-writer-transition", action);
export function claimWorkerLease(state: string, task: string) {
  return transition(state, () => {
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
  });
}
export function reserveWriterLease(state: string, task: string) {
  const record = { pid: process.pid, task, token: randomUUID() };
  transition(state, () => {
    if (writerLeaseStatus(state))
      throw Error("Another worker owns this workspace");
    atomic(leasePath(state), JSON.stringify(record), null);
  });
  let released = false;
  return (unclaimedExitProved = false) =>
    transition(state, () => {
      if (released) return true;
      const file = leasePath(state);
      if (fs.existsSync(file)) {
        const owner = writerLeaseStatus(state);
        if (owner.token !== record.token) {
          released = true;
          return true;
        }
        if (
          Number.isSafeInteger(owner.childPid) &&
          typeof owner.childStart === "string"
        ) {
          if (processStart(owner.childPid) === owner.childStart) return false;
        } else if (!unclaimedExitProved) return false;
        fs.unlinkSync(file);
      }
      released = true;
      return true;
    });
}
export function reconcileWriterLease(state: string, approved: string) {
  return transition(state, () => {
    const record = writerLeaseStatus(state);
    if (!record || digest(record) !== approved)
      throw Error("Worker lease review changed");
    if (
      !Number.isSafeInteger(record.childPid) ||
      record.childPid < 1 ||
      typeof record.childStart !== "string" ||
      !/^[0-9]+$/.test(record.childStart) ||
      BigInt(record.childStart) <= 0n
    )
      throw Error(
        "Worker startup identity is uncertain; inspect/terminate its tmux window before operator recovery",
      );
    if (processStart(record.childPid) === record.childStart)
      throw Error("Worker is still alive; interrupt it before reconciliation");
    fs.unlinkSync(leasePath(state));
    return { status: "released", child_verified_exited: true };
  });
}
