import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { rejectRedirects } from "./filesystem.ts";

export type KnownFolders = Partial<
  Record<"home" | "documents" | "desktop" | "downloads", string>
>;
export interface DirectorySuggestion {
  value: string;
  label: string;
}
const phrases = {
  "my documents folder": "documents",
  "my home folder": "home",
  desktop: "desktop",
  downloads: "downloads",
} as const;
const normalized = (value: string) =>
  value
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ")
    .replace(/^(my|the) /, "")
    .replace(/ folder$/, "");

/** Pure mapping keeps native OS discovery separate from portable alias resolution. */
export function buildKnownFolders(
  platform: NodeJS.Platform,
  home: string,
  native: KnownFolders = {},
  xdgText = "",
): KnownFolders {
  const paths = platform === "win32" ? path.win32 : path.posix;
  const result: KnownFolders = {
    home,
    documents: paths.join(home, "Documents"),
    desktop: paths.join(home, "Desktop"),
    downloads: paths.join(home, "Downloads"),
    ...native,
  };
  if (platform === "linux")
    for (const [key, variable] of [
      ["documents", "DOCUMENTS"],
      ["desktop", "DESKTOP"],
      ["downloads", "DOWNLOAD"],
    ] as const) {
      const match = new RegExp(
        "^XDG_" + variable + '_DIR="([^"\\n]*)"\\s*$',
        "m",
      ).exec(xdgText);
      if (!match) continue;
      const value = match[1].replace(/\$HOME/g, home);
      if (path.posix.isAbsolute(value) && !/[\x00-\x1f$`]/.test(value))
        result[key] = value;
    }
  return result;
}
export function isWSL() {
  if (process.platform !== "linux") return false;
  try {
    return /microsoft|wsl/i.test(
      fs.readFileSync("/proc/sys/kernel/osrelease", "utf8"),
    );
  } catch {
    return false;
  }
}
export function windowsPathInWSL(value: string) {
  if (!/^[a-z]:[\\/]/i.test(value))
    throw Error("Use a mounted absolute path for this Windows folder");
  return execFileSync("/usr/bin/wslpath", ["-u", value], {
    encoding: "utf8",
    timeout: 5000,
    maxBuffer: 8192,
  }).trim();
}
/** Retain valid native folders when one redirected location is unavailable. */
export function mapNativeKnownFolders(
  native: KnownFolders,
  convert: (value: string) => string = (value) => value,
): KnownFolders {
  const result: KnownFolders = {};
  for (const key of ["home", "documents", "desktop", "downloads"] as const) {
    const value = native[key];
    if (
      typeof value !== "string" ||
      !value ||
      value.length > 4096 ||
      /[\x00-\x1f\x7f-\x9f]/.test(value)
    )
      continue;
    try {
      result[key] = convert(value);
    } catch {}
  }
  return result;
}
/** XDG configuration is data: bounded regular files only, never shell evaluation. */
export function readXdgDirectories(
  home: string,
  configured = process.env.XDG_CONFIG_HOME,
): string {
  let fd: number | undefined;
  try {
    const root =
      configured &&
      path.isAbsolute(configured) &&
      !/[\x00-\x1f\x7f-\x9f]/.test(configured)
        ? configured
        : path.join(home, ".config");
    const file = rejectRedirects(path.join(root, "user-dirs.dirs"));
    if (!fs.lstatSync(file).isFile()) return "";
    fd = fs.openSync(
      file,
      fs.constants.O_RDONLY |
        fs.constants.O_NONBLOCK |
        (fs.constants.O_NOFOLLOW ?? 0),
    );
    const stat = fs.fstatSync(fd);
    if (!stat.isFile() || stat.size > 64 * 1024) return "";
    const buffer = Buffer.alloc(64 * 1024 + 1);
    let n = 0;
    while (n < buffer.length) {
      const count = fs.readSync(fd, buffer, n, buffer.length - n, n);
      if (!count) break;
      n += count;
    }
    return n <= 64 * 1024 ? buffer.subarray(0, n).toString("utf8") : "";
  } catch {
    return "";
  } finally {
    if (fd !== undefined) fs.closeSync(fd);
  }
}
export function knownFolders(): KnownFolders {
  const home = os.homedir(),
    wsl = isWSL();
  if (process.platform === "win32" || wsl) {
    const script = `[Console]::OutputEncoding=[Text.Encoding]::UTF8; $ErrorActionPreference='Stop'; $profileRoot=[Environment]::GetFolderPath('UserProfile'); $documents=[Environment]::GetFolderPath('MyDocuments'); if (!$documents) {$standardDocuments=Join-Path $profileRoot 'Documents'; if (Test-Path -LiteralPath $standardDocuments -PathType Container) {$documents=$standardDocuments}}; $downloads=Join-Path $profileRoot 'Downloads'; try {$downloads=[Environment]::ExpandEnvironmentVariables((Get-ItemPropertyValue -LiteralPath 'HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\User Shell Folders' -Name '{374DE290-123F-4565-9164-39C4925E467B}'))} catch {}; @{home=$profileRoot;documents=$documents;desktop=[Environment]::GetFolderPath('DesktopDirectory');downloads=$downloads}|ConvertTo-Json -Compress`;
    try {
      const output = execFileSync(
        wsl
          ? "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
          : "powershell.exe",
        ["-NoProfile", "-NonInteractive", "-Command", script],
        { encoding: "utf8", timeout: 5000, maxBuffer: 8192 },
      );
      const native = JSON.parse(output.replace(/^\uFEFF/, "")) as KnownFolders;
      return mapNativeKnownFolders(native, wsl ? windowsPathInWSL : undefined);
    } catch {
      return buildKnownFolders(process.platform, home);
    }
  }
  return buildKnownFolders(
    process.platform,
    home,
    {},
    process.platform === "linux" ? readXdgDirectories(home) : "",
  );
}
export function resolveDirectoryText(
  input: string,
  locations: KnownFolders,
): string {
  const value = input.trim();
  if (!value || value.length > 4096 || /[\x00-\x1f\x7f-\x9f]/.test(value))
    throw Error("Enter a folder phrase or an absolute path");
  const alias = normalized(value);
  if (["home", "documents", "desktop", "downloads"].includes(alias)) {
    const resolved = locations[alias as keyof KnownFolders];
    if (
      !resolved ||
      resolved.length > 4096 ||
      /[\x00-\x1f\x7f-\x9f]/.test(resolved)
    )
      throw Error("That known folder is unavailable; enter its absolute path");
    return resolved;
  }
  if (value === "~" || value.startsWith("~/") || value.startsWith("~\\")) {
    if (!locations.home) throw Error("The selected home folder is unavailable");
    return path.resolve(locations.home, value.slice(2));
  }
  if (isWSL() && /^[a-z]:[\\/]/i.test(value)) return windowsPathInWSL(value);
  if (!path.isAbsolute(value))
    throw Error(
      "Use a supported phrase such as my documents folder, or an absolute path",
    );
  return path.normalize(value);
}
/** One bounded, directory-only metadata listing; never opens a document or creates a folder. */
export function directorySuggestions(
  input: string,
  locations: KnownFolders,
  limit = 24,
): DirectorySuggestion[] {
  if (!Number.isInteger(limit) || limit < 1 || limit > 100)
    throw Error("Use a bounded suggestion count");
  const value = input.trim(),
    query = normalized(value);
  if (value.length > 4096 || /[\x00-\x1f\x7f-\x9f]/.test(value)) return [];
  if (
    !path.isAbsolute(value) &&
    !value.startsWith("~") &&
    !/^[a-z]:[\\/]/i.test(value)
  ) {
    return Object.entries(phrases)
      .filter(
        ([phrase, key]) =>
          normalized(phrase).startsWith(query) &&
          !!locations[key] &&
          (() => {
            try {
              return fs
                .statSync(rejectRedirects(locations[key]!))
                .isDirectory();
            } catch {
              return false;
            }
          })(),
      )
      .map(([label, key]) => ({ label, value: locations[key]! }))
      .slice(0, limit);
  }
  let resolved: string;
  try {
    resolved = resolveDirectoryText(value, locations);
  } catch {
    return [];
  }
  const trailing = /[\\/]$/.test(value),
    directory = trailing ? resolved : path.dirname(resolved),
    prefix = trailing ? "" : path.basename(resolved);
  const found: DirectorySuggestion[] = [];
  try {
    const handle = fs.opendirSync(rejectRedirects(directory));
    try {
      for (let visited = 0; visited < 512; visited++) {
        const entry = handle.readSync();
        if (!entry) break;
        if (
          /[\x00-\x1f\x7f-\x9f]/.test(entry.name) ||
          !entry.isDirectory() ||
          entry.isSymbolicLink() ||
          (!prefix.startsWith(".") && entry.name.startsWith(".")) ||
          !entry.name.toLowerCase().startsWith(prefix.toLowerCase())
        )
          continue;
        found.push({
          value: path.join(directory, entry.name),
          label: entry.name + path.sep,
        });
      }
    } finally {
      handle.closeSync();
    }
  } catch {
    return [];
  }
  return found.sort((a, b) => a.label.localeCompare(b.label)).slice(0, limit);
}
export function existingDirectory(input: string, locations: KnownFolders) {
  const resolved = rejectRedirects(resolveDirectoryText(input, locations));
  if (!fs.statSync(resolved).isDirectory())
    throw Error("Choose an existing folder");
  return resolved;
}
