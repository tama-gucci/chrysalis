import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash } from "node:crypto";
import YAML from "yaml";

export function check(root) {
  root = path.resolve(root);
  const findings = [],
    all = [];
  const issue = (code, file) => findings.push({ code, path: file });
  function walk(directory) {
    for (const e of fs.readdirSync(directory, { withFileTypes: true })) {
      if (directory === root && e.name === ".git") continue;
      const full = path.join(directory, e.name),
        relative = path.relative(root, full).split(path.sep).join("/");
      if (fs.lstatSync(full).isSymbolicLink()) {
        issue("redirected_source", relative);
        continue;
      }
      if (e.isDirectory()) {
        if (
          [
            ".obsidian",
            ".agent",
            ".agents",
            "node_modules",
            ".venv",
            ".pytest_cache",
            "__pycache__",
            ".trash",
            "backups",
            "Nexus",
            ".conversations",
            ".workspaces",
          ].includes(e.name)
        )
          issue("private_or_generated_directory", relative);
        walk(full);
      } else if (e.isFile()) all.push({ full, relative });
    }
  }
  walk(root);
  const lock = JSON.parse(
      fs.readFileSync(path.join(root, "resources/plugins.lock.json"), "utf8"),
    ),
    vendor = new Map(
      lock.plugins.flatMap((p) =>
        Object.entries(p.assets).map(([name, value]) => [
          "resources/plugins/" + p.id + "/" + name,
          value,
        ]),
      ),
    );
  for (const { full, relative } of all) {
    if (
      /^(System|Daily|Attachments|TaskNotes|Projects|Slipbox|Sources|Environments)(\/|$)/.test(
        relative,
      )
    )
      issue("runtime_collection_in_source", relative);
    if (/\.(pyc|py|sqlite|db|zip|tgz|env|log|tmp|bak)$/.test(relative))
      issue("obsolete_or_generated_file", relative);
    const bytes = fs.readFileSync(full),
      asset = vendor.get(relative);
    if (asset) {
      if (
        bytes.length !== asset.bytes ||
        createHash("sha256").update(bytes).digest("hex") !== asset.sha256
      )
        issue("third_party_asset_changed", relative);
      continue;
    }
    if (!/\.(md|json|yaml|yml|base|ts|mjs|js|txt)$/.test(relative)) continue;
    let text;
    try {
      text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    } catch {
      issue("non_utf8_source", relative);
      continue;
    }
    if (/[a-z]:[\\/]+users[\\/]|\/home\/[a-z0-9_-]+\//i.test(text))
      issue("machine_bound_path", relative);
    if (
      /-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{25,}|AIza[A-Za-z0-9_-]{30,}|sk-(?:proj-)?[A-Za-z0-9_-]{30,}/.test(
        text,
      )
    )
      issue("credential_pattern", relative);
    if (
      relative.endsWith(".md") &&
      /antigravity|codex|claude\s+code|hermes|syncthing/i.test(text)
    )
      issue("outdated_documentation", relative);
    try {
      if (relative.endsWith(".json")) JSON.parse(text);
      if (/\.(base|ya?ml)$/.test(relative)) YAML.parse(text);
      if (relative.endsWith(".md") && text.startsWith("---")) {
        const m = /^---\r?\n([\s\S]*?)\r?\n---/.exec(text);
        if (!m) throw Error("frontmatter");
        YAML.parse(m[1]);
      }
    } catch {
      issue("structured_source_syntax", relative);
    }
    if (relative.endsWith(".md"))
      for (const m of text.matchAll(/(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)/g)) {
        const target = m[1].replace(/^<|>$/g, "").split("#")[0];
        if (
          target &&
          !target.includes("://") &&
          !target.startsWith("mailto:") &&
          !fs.existsSync(path.resolve(path.dirname(full), target))
        )
          issue("broken_document_link", relative);
      }
    if (relative.endsWith("SKILL.md"))
      for (const m of text.matchAll(/references\/[a-z0-9-]+\.md/g))
        if (!fs.existsSync(path.join(path.dirname(full), m[0])))
          issue("missing_skill_reference", relative);
  }
  const manifest = JSON.parse(
    fs.readFileSync(path.join(root, "package.json"), "utf8"),
  );
  for (const file of manifest.files)
    if (!fs.existsSync(path.join(root, file)))
      issue("missing_package_resource", file);
  if (
    !fs
      .readFileSync(path.join(root, ".gitignore"), "utf8")
      .split(/\r?\n/)
      .includes("/*")
  )
    issue("missing_default_deny", ".gitignore");
  return {
    status: findings.length ? "failed" : "passed",
    files_checked: all.length,
    findings,
    scope:
      "All non-Git files, including ignored/untracked content. Pinned third-party bytes checked against the asset lock; prose privacy and upstream code review remain separate.",
  };
}
if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const index = process.argv.indexOf("--root"),
    root =
      index >= 0
        ? process.argv[index + 1]
        : path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
  const result = check(root);
  console.log(JSON.stringify(result, null, 2));
  process.exitCode = result.status === "passed" ? 0 : 1;
}
