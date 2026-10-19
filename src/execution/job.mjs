import fs from "node:fs";
import { spawn } from "node:child_process";
const job = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const filter = fs.openSync(job.filter, "r"),
  control = fs.openSync(job.control, "wx", 0o600);
const child = spawn(job.bwrap, job.args, {
  stdio: ["pipe", "inherit", "inherit", filter, control],
  env: { PATH: "/usr/bin:/bin" },
});
child.stdin.on("error", () => {});
child.stdin.end(fs.readFileSync(job.input));
child.on("error", () => {
  fs.closeSync(filter);
  fs.closeSync(control);
  process.exitCode = 125;
});
child.on("exit", (code) => {
  fs.closeSync(filter);
  fs.closeSync(control);
  process.exitCode = code ?? 137;
});
