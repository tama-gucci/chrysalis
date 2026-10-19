import { isIP } from "node:net";
import { randomUUID } from "node:crypto";
import { publicAddress, publicURL } from "../research/http.ts";

export const PASSWORD_INPUT_LIMIT = 2 * 1024 * 1024;
export const PASSWORD_RECORD_LIMIT = 5000;
export interface PasswordRecord {
  id: string;
  origins: string[];
  username: string;
  password: string;
  name: string;
  folder: string;
  source: { adapter: string; externalId?: string };
}
export interface PasswordSnapshot {
  records: PasswordRecord[];
  skipped: number;
  adapter: string;
}
/** Future manager adapters deliver private snapshots; credentials never become ingestion evidence. */
export interface PasswordSourceAdapter {
  id: string;
  readSnapshot(signal?: AbortSignal): Promise<PasswordSnapshot>;
}
function csv(text: string, firstRowOnly = false): string[][] {
  const rows: string[][] = [];
  let row: string[] = [],
    value = "",
    quoted = false,
    closed = false;
  const cell = () => {
    row.push(value);
    value = "";
    closed = false;
    if (row.length > 100) throw Error("password_import_invalid");
  };
  const end = () => {
    cell();
    if (row.some((v) => v !== "")) rows.push(row);
    row = [];
    if (rows.length > PASSWORD_RECORD_LIMIT + 1)
      throw Error("password_import_limit");
  };
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"') {
        if (text[i + 1] === '"') {
          value += '"';
          i++;
        } else {
          quoted = false;
          closed = true;
        }
      } else value += c;
    } else if (c === '"' && value === "" && !closed) quoted = true;
    else if (c === ",") cell();
    else if (c === "\r" || c === "\n") {
      if (c === "\r" && text[i + 1] === "\n") i++;
      end();
      if (firstRowOnly && rows.length) return rows;
    } else {
      if (closed || c === '"') throw Error("password_import_invalid");
      value += c;
    }
    if (value.length > 32768) throw Error("password_import_limit");
  }
  if (quoted) throw Error("password_import_invalid");
  if (value || row.length || closed) end();
  return rows;
}
const header = (v: string) =>
  v
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]/g, "");
const PASSWORD_COLUMNS = ["password", "loginpassword"];
const USER_COLUMNS = ["username", "loginusername", "user", "email"];
const URL_COLUMNS = ["url", "uri", "website", "loginuri", "loginurl"];

/** Strong export signatures, used only to refuse ordinary document copies/extraction. */
export function isPasswordExport(bytes: Buffer): boolean {
  try {
    const text = new TextDecoder("utf-8", { fatal: true })
      .decode(bytes)
      .replace(/^\uFEFF/, "");
    if (/^\s*[\[{]/.test(text)) {
      const data = JSON.parse(text);
      if (
        data?.encrypted === true &&
        (data?.data || data?.encKeyValidation_DO_NOT_EDIT)
      )
        return true;
      const list = Array.isArray(data) ? data : data?.items;
      return (
        Array.isArray(list) &&
        list.some(
          (v) =>
            v &&
            ((v.login && Object.hasOwn(v.login, "password")) ||
              (Object.hasOwn(v, "password") &&
                (Object.hasOwn(v, "username") ||
                  Object.hasOwn(v, "url") ||
                  Object.hasOwn(v, "urls")))),
        )
      );
    }
    // The importer and detector share quoting, blank-row and cell/column limits.
    const first = csv(text, true)[0]?.map(header) ?? [];
    if (
      PASSWORD_COLUMNS.some((k) => first.includes(k)) &&
      (USER_COLUMNS.some((k) => first.includes(k)) ||
        URL_COLUMNS.some((k) => first.includes(k)))
    )
      return true;
  } catch {
    /* Invalid formats are still rejected by the dedicated importer. */
  }
  return false;
}
export function assertNotPasswordExport(bytes: Buffer) {
  if (isPasswordExport(bytes))
    throw Error(
      "Password exports require /chrysalis passwords; never ordinary document ingestion",
    );
}
function item(raw: any, adapter: string): PasswordRecord | undefined {
  if (!raw || typeof raw !== "object") return;
  const username = raw.username ?? "",
    password = raw.password;
  if (password === null || password === undefined) return;
  if (
    typeof username !== "string" ||
    username.length > 1000 ||
    typeof password !== "string" ||
    password.length > 8192
  )
    throw Error("password_import_invalid");
  if (!password) return;
  const urls = Array.isArray(raw.urls) ? raw.urls : [raw.url];
  if (urls.length > 20) throw Error("password_import_limit");
  const origins: string[] = [];
  for (const url of urls) {
    if (typeof url !== "string" || url.length > 2000) continue;
    try {
      const destination = publicURL(url),
        host = destination.hostname.replace(/^\[|\]$/g, "");
      if (isIP(host) && !publicAddress(host)) continue;
      origins.push(destination.origin);
    } catch {
      /* Unsupported application/private/HTTP origins are not granted browser access. */
    }
  }
  if (!origins.length) return;
  return {
    id: randomUUID(),
    origins: [...new Set(origins)].sort(),
    username,
    password,
    name: typeof raw.name === "string" ? raw.name.slice(0, 256) : "Saved login",
    folder: typeof raw.folder === "string" ? raw.folder.slice(0, 256) : "",
    source: {
      adapter,
      ...(typeof raw.externalId === "string" &&
      /^[a-zA-Z0-9-]{1,100}$/.test(raw.externalId)
        ? { externalId: raw.externalId }
        : {}),
    },
  };
}
export function parsePasswordExport(bytes: Buffer): PasswordSnapshot {
  try {
    if (bytes.length > PASSWORD_INPUT_LIMIT) throw Error("limit");
    const text = new TextDecoder("utf-8", { fatal: true })
      .decode(bytes)
      .replace(/^\uFEFF/, "");
    let source: any[], adapter: string;
    if (/^\s*[\[{]/.test(text)) {
      const data = JSON.parse(text);
      if (data?.encrypted === true) throw Error("unsupported");
      if (Array.isArray(data)) {
        adapter = "generic-json";
        source = data;
      } else if (Array.isArray(data?.items)) {
        adapter = "bitwarden-export";
        const folders = new Map(
          (Array.isArray(data.folders) ? data.folders : []).map((f: any) => [
            f.id,
            f.name,
          ]),
        );
        source = data.items.map((v: any) =>
          v?.type === 1 && v.login
            ? {
                username: v.login.username,
                password: v.login.password,
                urls: (v.login.uris ?? []).map((u: any) => u.uri),
                name: v.name,
                folder: folders.get(v.folderId) ?? "",
                externalId: v.id,
              }
            : null,
        );
      } else throw Error("unsupported");
    } else {
      const rows = csv(text),
        names = rows.shift()?.map(header) ?? [];
      if (new Set(names).size !== names.length) throw Error("invalid");
      const find = (keys: string[]) => names.findIndex((v) => keys.includes(v));
      const p = find(PASSWORD_COLUMNS),
        u = find(USER_COLUMNS),
        l = find(URL_COLUMNS),
        n = find(["name", "title"]),
        f = find(["folder", "group"]),
        t = find(["type"]);
      if (p < 0 || l < 0 || u < 0) throw Error("unsupported");
      adapter = names.includes("loginpassword")
        ? "bitwarden-csv"
        : "generic-csv";
      source = rows.map((row) => {
        if (row.length !== names.length) throw Error("invalid");
        if (t >= 0 && !["1", "login"].includes(row[t].trim().toLowerCase()))
          return null;
        return {
          password: row[p],
          username: row[u],
          url: row[l],
          name: n >= 0 ? row[n] : undefined,
          folder: f >= 0 ? row[f] : undefined,
        };
      });
    }
    if (source.length > PASSWORD_RECORD_LIMIT) throw Error("limit");
    const records = source
      .map((v) => item(v, adapter))
      .filter(Boolean) as PasswordRecord[];
    return { records, skipped: source.length - records.length, adapter };
  } catch {
    throw Error("password_import_invalid_or_unsupported");
  }
}
const matches = (a: PasswordRecord, b: PasswordRecord) => {
  if (
    a.source.adapter === b.source.adapter &&
    a.source.externalId &&
    b.source.externalId
  )
    return a.source.externalId === b.source.externalId;
  return (
    a.username === b.username && a.origins.some((o) => b.origins.includes(o))
  );
};
export function mergePasswordSnapshot(
  existing: PasswordRecord[],
  snapshot: PasswordSnapshot,
) {
  if (existing.length + snapshot.records.length > PASSWORD_RECORD_LIMIT * 2)
    throw Error("password_import_limit");
  const records = existing.map((r) => ({ ...r, origins: [...r.origins] }));
  let added = 0,
    updated = 0,
    unchanged = 0;
  const seen: PasswordRecord[] = [];
  for (const incoming of snapshot.records) {
    const duplicate = seen.filter((r) => matches(r, incoming));
    if (
      duplicate.length &&
      duplicate.some(
        (r) =>
          r.password !== incoming.password || r.username !== incoming.username,
      )
    )
      throw Error("password_import_ambiguous_duplicates");
    if (duplicate.length) continue;
    seen.push(incoming);
    const indices = records
      .map((r, i) => (matches(r, incoming) ? i : -1))
      .filter((i) => i >= 0);
    if (indices.length > 1) throw Error("password_import_ambiguous_accounts");
    if (!indices.length) {
      records.push(incoming);
      added++;
      continue;
    }
    const i = indices[0],
      old = records[i],
      next = {
        ...incoming,
        id: old.id,
        source: incoming.source.externalId
          ? incoming.source
          : old.source.externalId
            ? old.source
            : incoming.source,
      };
    if (
      old.password === next.password &&
      old.username === next.username &&
      old.name === next.name &&
      old.folder === next.folder &&
      JSON.stringify(old.origins) === JSON.stringify(next.origins) &&
      JSON.stringify(old.source) === JSON.stringify(next.source)
    )
      unchanged++;
    else {
      records[i] = next;
      updated++;
    }
  }
  if (records.length > PASSWORD_RECORD_LIMIT)
    throw Error("password_import_limit");
  records.sort((a, b) =>
    (
      a.folder +
      "\0" +
      a.origins[0] +
      "\0" +
      a.username +
      "\0" +
      a.id
    ).localeCompare(
      b.folder + "\0" + b.origins[0] + "\0" + b.username + "\0" + b.id,
    ),
  );
  return {
    records,
    summary: {
      added,
      updated,
      unchanged,
      skipped: snapshot.skipped,
      total: records.length,
      deleted: 0,
    },
  };
}
