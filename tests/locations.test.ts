import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { visibleWidth } from "@earendil-works/pi-tui";
import {
  buildKnownFolders,
  mapNativeKnownFolders,
  readXdgDirectories,
  resolveDirectoryText,
  directorySuggestions,
  existingDirectory,
} from "../src/platforms/locations.ts";
import {
  createDirectoryInput,
  selectVaultParent,
} from "../extensions/directory-input.ts";
if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(process.env.TEST_SCRATCH, "locations-" + randomUUID());
fs.mkdirSync(base, { recursive: true });
const theme: any = { fg: (_color: string, text: string) => text };

test("folder phrases use Windows known folders and portable macOS/Linux locations", () => {
  const windows = buildKnownFolders("win32", "X:\\Profiles\\Example", {
    documents: "X:\\Redirected\\Documents",
  });
  assert.equal(
    resolveDirectoryText("My Documents Folder", windows),
    "X:\\Redirected\\Documents",
  );
  const posixHome = "/synthetic-profile";
  const mac = buildKnownFolders("darwin", posixHome);
  assert.equal(
    resolveDirectoryText("my documents folder", mac),
    path.posix.join(posixHome, "Documents"),
  );
  assert.equal(
    resolveDirectoryText("desktop", mac),
    path.posix.join(posixHome, "Desktop"),
  );
  const linux = buildKnownFolders(
    "linux",
    posixHome,
    {},
    'XDG_DOCUMENTS_DIR="$HOME/Local Documents"\nXDG_DOWNLOAD_DIR="$HOME/Downloads"\nXDG_DESKTOP_DIR="$(untrusted-command)"',
  );
  assert.equal(linux.documents, path.posix.join(posixHome, "Local Documents"));
  assert.equal(linux.desktop, path.posix.join(posixHome, "Desktop"));
  assert.throws(
    () => resolveDirectoryText("my project workspace", mac),
    /supported phrase/,
  );
  assert.throws(
    () => resolveDirectoryText("my documents folder", { home: base }),
    /unavailable/,
  );
});

test("directory completion is bounded, directory-only and never follows redirected entries", () => {
  const root = path.join(base, "completion");
  fs.mkdirSync(root);
  for (const name of ["Documents", "Downloads", "Other"])
    fs.mkdirSync(path.join(root, name));
  fs.writeFileSync(path.join(root, "private-file.txt"), "synthetic-canary");
  fs.symlinkSync(
    base,
    path.join(root, "Redirected"),
    process.platform === "win32" ? "junction" : "dir",
  );
  if (process.platform !== "win32") {
    fs.mkdirSync(path.join(root, "unsafe\x1bname"));
  }
  const locations = { home: root, documents: path.join(root, "Documents") };
  assert.deepEqual(
    directorySuggestions(root + path.sep + "Do", locations).map((x) => x.label),
    ["Documents" + path.sep, "Downloads" + path.sep],
  );
  const all = directorySuggestions(root + path.sep, locations);
  assert(!JSON.stringify(all).includes("private-file"));
  assert(!JSON.stringify(all).includes("Redirected"));
  assert(!JSON.stringify(all).includes("unsafe"));
  assert.equal(directorySuggestions(root + path.sep, locations, 1).length, 1);
  assert.equal(
    existingDirectory("my documents folder", locations),
    path.join(root, "Documents"),
  );
  assert.throws(
    () => existingDirectory(path.join(root, "private-file.txt"), locations),
    /existing folder/,
  );
});

test("native folder prompt advertises phrases and Tab completes before explicit Enter confirmation", () => {
  const root = path.join(base, "native");
  fs.mkdirSync(root);
  fs.mkdirSync(path.join(root, "Documents"));
  const values: Array<string | undefined> = [],
    tui = { terminal: { rows: 14 }, requestRender() {} };
  const component = createDirectoryInput(
    tui,
    theme,
    (value) => values.push(value),
    { home: root, documents: path.join(root, "Documents") },
  );
  component.focused = true;
  const first = component.render(58).join("\n");
  assert.match(first, /my documents folder/);
  assert.match(first, /Tab completes/);
  for (const key of "my doc") component.handleInput(key);
  component.handleInput("\t");
  assert(component.render(58).some((line) => line.includes("Documents")));
  assert.deepEqual(values, []);
  component.handleInput("\r");
  assert.deepEqual(values, [path.join(root, "Documents")]);
  assert(component.render(58).every((line) => visibleWidth(line) <= 58));
});

test("unrecognized/missing locations stay in the native dialog; cancellation and headless calls do not create folders", async () => {
  const values: Array<string | undefined> = [],
    component = createDirectoryInput(
      { terminal: { rows: 20 }, requestRender() {} },
      theme,
      (value) => values.push(value),
      { home: base, documents: path.join(base, "Missing") },
    );
  for (const key of "my documents folder") component.handleInput(key);
  component.handleInput("\r");
  assert.deepEqual(values, []);
  assert(!fs.existsSync(path.join(base, "Missing")));
  component.handleInput("\x1b");
  assert.deepEqual(values, [undefined]);
  await assert.rejects(
    selectVaultParent({ hasUI: false } as any),
    /native interactive/,
  );
});

test("Tab completion places the cursor at the end before entering a child folder", () => {
  const root = path.join(base, "cursor");
  fs.mkdirSync(path.join(root, "Documents", "Child"), { recursive: true });
  const values: Array<string | undefined> = [];
  const component = createDirectoryInput(
    { terminal: { rows: 20 }, requestRender() {} },
    theme,
    (value) => values.push(value),
    { documents: path.join(root, "Documents") },
  );
  for (const key of "my doc") component.handleInput(key);
  component.handleInput("\t");
  for (const key of "Child") component.handleInput(key);
  component.handleInput("\r");
  assert.deepEqual(values, [path.join(root, "Documents", "Child")]);
});

test("one unavailable native folder does not discard other valid known folders", () => {
  const result = mapNativeKnownFolders(
    {
      home: "C:\\Profile",
      documents: "C:\\Docs",
      desktop: "unavailable",
      downloads: "bad\x1bvalue",
    },
    (value) => {
      if (value === "unavailable") throw Error("unmounted");
      return value.replace("C:", "/mnt/c").replaceAll("\\", "/");
    },
  );
  assert.deepEqual(result, {
    home: "/mnt/c/Profile",
    documents: "/mnt/c/Docs",
  });
});

test("Linux folder discovery honors XDG_CONFIG_HOME and ignores oversized or nonregular configuration", () => {
  const config = path.join(base, "custom-config");
  fs.mkdirSync(config);
  const file = path.join(config, "user-dirs.dirs");
  fs.writeFileSync(file, 'XDG_DOCUMENTS_DIR="$HOME/Local Documents"');
  const previous = process.env.XDG_CONFIG_HOME;
  process.env.XDG_CONFIG_HOME = config;
  try {
    assert.equal(
      buildKnownFolders(
        "linux",
        "/synthetic-profile",
        {},
        readXdgDirectories(base),
      ).documents,
      "/synthetic-profile/Local Documents",
    );
  } finally {
    if (previous === undefined) delete process.env.XDG_CONFIG_HOME;
    else process.env.XDG_CONFIG_HOME = previous;
  }
  fs.writeFileSync(file, "x".repeat(64 * 1024 + 1));
  assert.equal(readXdgDirectories(base, config), "");
  fs.unlinkSync(file);
  fs.mkdirSync(file);
  assert.equal(readXdgDirectories(base, config), "");
});
