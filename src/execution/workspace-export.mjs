import fs from "node:fs";
import path from "node:path";
let bytes = 0,
  files = 0;
function walk(root, relative = "") {
  for (const entry of fs.readdirSync(path.join(root, relative), {
    withFileTypes: true,
  })) {
    const name = relative ? relative + "/" + entry.name : entry.name;
    if (
      [
        ".git",
        ".pi",
        ".ssh",
        ".gnupg",
        ".aws",
        ".azure",
        ".gcloud",
        ".kube",
        ".docker",
        ".npmrc",
        ".netrc",
        ".git-credentials",
        ".pypirc",
        ".yarnrc",
      ].includes(entry.name.toLowerCase()) ||
      /^\.env(?:\.|$)/.test(entry.name) ||
      /^(auth\.json|credentials.*|id_(rsa|dsa|ecdsa|ed25519)(?:_sk)?|.*\.(key|pem|p12))$/i.test(
        entry.name,
      )
    )
      continue;
    const file = path.join(root, name),
      s = fs.lstatSync(file);
    if (
      s.isSymbolicLink() ||
      (!s.isDirectory() && !s.isFile()) ||
      (s.isFile() && s.nlink !== 1)
    )
      throw Error("Unsupported output entry");
    if (s.isDirectory()) walk(root, name);
    else {
      if (
        ++files > 20000 ||
        s.size > 16 * 1024 * 1024 ||
        (bytes += s.size) > 64 * 1024 * 1024
      )
        throw Error("Workspace output limit");
      process.stdout.write(
        JSON.stringify({
          path: name,
          data: fs.readFileSync(file).toString("base64"),
          mode: s.mode & 0o777,
        }) + "\n",
      );
    }
  }
}
walk("/workspace");
process.stdout.write(JSON.stringify({ end: true }) + "\n");
