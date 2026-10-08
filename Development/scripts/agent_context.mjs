import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
const root = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const git = (...args) =>
  execFileSync("git", ["-C", root, ...args], {
    encoding: "utf8",
    windowsHide: true,
  }).trim();
const status = {
  branch: git("branch", "--show-current"),
  head: git("rev-parse", "HEAD"),
  working_tree: git("status", "--short"),
};
const index = process.argv.indexOf("--manifest");
if (index >= 0) {
  const target = path.resolve(process.argv[index + 1]);
  const relative = path.relative(root, target);
  if (
    relative === "" ||
    (!path.isAbsolute(relative) &&
      relative !== ".." &&
      !relative.startsWith(".." + path.sep))
  )
    throw Error("Hash manifest belongs outside source");
  const names = git(
      "ls-files",
      "--cached",
      "--others",
      "--exclude-standard",
      "-z",
    )
      .split("\0")
      .filter(Boolean),
    hashes = {};
  for (const name of names) {
    const f = path.join(root, name);
    if (fs.existsSync(f) && fs.statSync(f).isFile())
      hashes[name] = createHash("sha256")
        .update(fs.readFileSync(f))
        .digest("hex");
  }
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(
    target,
    JSON.stringify({ ...status, files: hashes }, null, 2) + "\n",
  );
}
console.log(JSON.stringify(status, null, 2));
