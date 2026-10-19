import fs from "node:fs";
import { spawn } from "node:child_process";
const job = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const ownerAlive = () => {
  try {
    const stat = fs.readFileSync("/proc/" + job.ownerPid + "/stat", "utf8");
    return (
      stat.slice(stat.lastIndexOf(")") + 2).split(" ")[19] === job.ownerStart
    );
  } catch {
    return false;
  }
};
if (
  !Number.isSafeInteger(job.ownerPid) ||
  job.ownerPid < 1 ||
  !/^[0-9]+$/.test(job.ownerStart) ||
  !ownerAlive()
)
  throw Error("Execution owner unavailable");
const filter = fs.openSync(job.filter, "r"),
  control = fs.openSync(job.control, "wx", 0o600);
const child = spawn(job.bwrap, job.args, {
  stdio: ["pipe", "inherit", "inherit", filter, control],
  env: { PATH: "/usr/bin:/bin" },
});
const ownerTimer = setInterval(() => {
  if (!ownerAlive()) {
    child.kill("SIGKILL");
    process.exit(125);
  }
}, 250);
child.stdin.on("error", () => {});
child.stdin.end(fs.readFileSync(job.input));
child.on("error", () => {
  clearInterval(ownerTimer);
  fs.closeSync(filter);
  fs.closeSync(control);
  process.exitCode = 125;
});
child.on("exit", (code) => {
  clearInterval(ownerTimer);
  fs.closeSync(filter);
  fs.closeSync(control);
  process.exitCode = code ?? 137;
});
