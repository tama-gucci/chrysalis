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
    if (++files > 20000) throw Error("Workspace output limit");
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
      if (s.size > 16 * 1024 * 1024 || (bytes += s.size) > 64 * 1024 * 1024)
        throw Error("Workspace output limit");
      const fd = fs.openSync(
        file,
        fs.constants.O_RDONLY |
          fs.constants.O_NOFOLLOW |
          fs.constants.O_NONBLOCK,
      );
      try {
        const opened = fs.fstatSync(fd);
        if (
          !opened.isFile() ||
          opened.nlink !== 1 ||
          opened.dev !== s.dev ||
          opened.ino !== s.ino ||
          opened.size !== s.size
        )
          throw Error("Workspace output changed");
        const data = Buffer.alloc(s.size + 1);
        let length = 0;
        while (length < data.length) {
          const n = fs.readSync(fd, data, length, data.length - length, length);
          if (!n) break;
          length += n;
        }
        const after = fs.fstatSync(fd);
        if (
          length !== s.size ||
          after.size !== s.size ||
          after.mtimeMs !== opened.mtimeMs ||
          after.ctimeMs !== opened.ctimeMs
        )
          throw Error("Workspace output changed");
        process.stdout.write(
          JSON.stringify({
            path: name,
            data: data.subarray(0, length).toString("base64"),
            mode: opened.mode & 0o777,
          }) + "\n",
        );
      } finally {
        fs.closeSync(fd);
      }
    }
  }
}
walk("/workspace");
process.stdout.write(JSON.stringify({ end: true }) + "\n");
