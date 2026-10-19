import fs from "node:fs";
import path from "node:path";
import {
  randomBytes,
  randomUUID,
  createCipheriv,
  createDecipheriv,
} from "node:crypto";
import { vaultState } from "../storage/context.ts";
import {
  atomic,
  canonical,
  confined,
  exists,
  raw,
  rejectRedirects,
  sha256,
  withLock,
  quarantineReviewedFile,
  inside,
} from "../platforms/filesystem.ts";
import {
  OSAccountPasswordKeys,
  type PasswordKeys,
} from "../platforms/password-keys.ts";
import {
  parsePasswordExport,
  mergePasswordSnapshot,
  PASSWORD_INPUT_LIMIT,
  PASSWORD_RECORD_LIMIT,
  type PasswordRecord,
} from "./import.ts";
import type { RuntimeContext } from "../contracts/types.ts";

const MAX_STORE = 8 * 1024 * 1024;
function regularInput(file: string, limit = PASSWORD_INPUT_LIMIT): Buffer {
  rejectRedirects(file);
  const before = fs.lstatSync(file);
  if (!before.isFile() || before.nlink !== 1 || before.size > limit)
    throw Error("password_input_not_regular_or_too_large");
  const fd = fs.openSync(
    file,
    fs.constants.O_RDONLY |
      (fs.constants.O_NOFOLLOW ?? 0) |
      (fs.constants.O_NONBLOCK ?? 0),
  );
  try {
    const opened = fs.fstatSync(fd);
    if (
      !opened.isFile() ||
      opened.nlink !== 1 ||
      opened.ino !== before.ino ||
      opened.dev !== before.dev ||
      opened.size !== before.size
    )
      throw Error("password_input_changed");
    const bytes = Buffer.alloc(opened.size + 1);
    let length = 0;
    while (length < bytes.length) {
      const n = fs.readSync(fd, bytes, length, bytes.length - length, length);
      if (!n) break;
      length += n;
    }
    const after = fs.fstatSync(fd);
    rejectRedirects(file);
    if (
      length !== opened.size ||
      after.size !== opened.size ||
      after.mtimeMs !== opened.mtimeMs ||
      after.ctimeMs !== opened.ctimeMs
    )
      throw Error("password_input_changed");
    return bytes.subarray(0, length);
  } finally {
    fs.closeSync(fd);
  }
}
export interface PasswordImportPlan {
  file: string;
  sourceHash: string;
  before: string | null;
  records: PasswordRecord[];
  summary: {
    added: number;
    updated: number;
    unchanged: number;
    skipped: number;
    total: number;
    deleted: number;
  };
}
export class PasswordStore {
  readonly ctx: RuntimeContext;
  readonly root: string;
  readonly inbox: string;
  private file: string;
  private keys: PasswordKeys;
  constructor(ctx: RuntimeContext, keys?: PasswordKeys) {
    this.ctx = ctx;
    this.root = confined(vaultState(ctx), "passwords");
    this.inbox = confined(this.root, "inbox");
    this.file = confined(this.root, "passwords.encrypted.json");
    this.keys = keys ?? new OSAccountPasswordKeys(ctx, this.root);
  }
  setupInbox() {
    rejectRedirects(this.inbox);
    fs.mkdirSync(this.inbox, { recursive: true, mode: 0o700 });
    fs.chmodSync(this.root, 0o700);
    fs.chmodSync(this.inbox, 0o700);
    return this.inbox;
  }
  configured() {
    return exists(this.file);
  }
  revision() {
    return exists(this.file)
      ? sha256(regularInput(this.file, MAX_STORE))
      : null;
  }
  inputFiles() {
    if (!exists(this.inbox)) return [];
    const names = fs.readdirSync(this.inbox, { withFileTypes: true });
    if (names.length > 100) throw Error("password_inbox_limit");
    return names
      .filter((e) => e.isFile() && /\.(csv|json)$/i.test(e.name))
      .map((e) => e.name)
      .sort();
  }
  async records(): Promise<PasswordRecord[]> {
    if (!exists(this.file)) return [];
    try {
      const envelope = JSON.parse(
        regularInput(this.file, MAX_STORE).toString("utf8"),
      );
      if (envelope.version !== 1 || envelope.algorithm !== "aes-256-gcm")
        throw Error("invalid");
      const decipher = createDecipheriv(
        "aes-256-gcm",
        await this.keys.get(false),
        Buffer.from(envelope.nonce, "base64"),
      );
      decipher.setAAD(Buffer.from("chrysalis-password-store-v1"));
      decipher.setAuthTag(Buffer.from(envelope.tag, "base64"));
      const bytes = Buffer.concat([
        decipher.update(Buffer.from(envelope.ciphertext, "base64")),
        decipher.final(),
      ]);
      const data = JSON.parse(bytes.toString("utf8"));
      bytes.fill(0);
      if (
        data.version !== 1 ||
        !Array.isArray(data.records) ||
        data.records.length > PASSWORD_RECORD_LIMIT
      )
        throw Error("invalid");
      for (const r of data.records)
        if (
          !/^[a-f0-9-]{36}$/.test(r.id) ||
          !Array.isArray(r.origins) ||
          !r.origins.length ||
          typeof r.password !== "string" ||
          typeof r.username !== "string"
        )
          throw Error("invalid");
      return data.records;
    } catch {
      throw Error("password_store_unavailable_or_corrupt");
    }
  }
  async prepare(name: string): Promise<PasswordImportPlan> {
    if (!/\.(csv|json)$/i.test(name))
      throw Error("password_export_format_unsupported");
    const file = confined(this.inbox, name),
      source = regularInput(file),
      before = this.revision();
    const merged = mergePasswordSnapshot(
      await this.records(),
      parsePasswordExport(source),
    );
    if (
      !merged.summary.added &&
      !merged.summary.updated &&
      !merged.summary.unchanged
    )
      throw Error("password_import_has_no_supported_browser_logins");
    return { file, sourceHash: sha256(source), before, ...merged };
  }
  async apply(plan: PasswordImportPlan, confirm: () => Promise<boolean>) {
    const reviewedIdentity = sha256(canonical(plan));
    if (!(await confirm())) return { status: "declined" };
    return withLock(this.root, "password-store", async () => {
      if (sha256(canonical(plan)) !== reviewedIdentity)
        throw Error("password_import_plan_changed");
      if (
        this.revision() !== plan.before ||
        sha256(regularInput(plan.file)) !== plan.sourceHash
      )
        throw Error("password_import_stale_review_again");
      if (sha256(canonical(plan)) !== reviewedIdentity)
        throw Error("password_import_plan_changed");
      const bytes = Buffer.from(
        canonical({
          version: 1,
          revision: randomUUID(),
          records: plan.records,
        }),
      );
      if (bytes.length > MAX_STORE / 2) throw Error("password_store_limit");
      const nonce = randomBytes(12),
        cipher = createCipheriv(
          "aes-256-gcm",
          await this.keys.get(true),
          nonce,
        );
      cipher.setAAD(Buffer.from("chrysalis-password-store-v1"));
      const ciphertext = Buffer.concat([cipher.update(bytes), cipher.final()]);
      bytes.fill(0);
      if (
        this.revision() !== plan.before ||
        sha256(regularInput(plan.file)) !== plan.sourceHash
      )
        throw Error("password_import_stale_review_again");
      if (sha256(canonical(plan)) !== reviewedIdentity)
        throw Error("password_import_plan_changed");
      atomic(
        this.file,
        canonical({
          version: 1,
          algorithm: "aes-256-gcm",
          nonce: nonce.toString("base64"),
          tag: cipher.getAuthTag().toString("base64"),
          ciphertext: ciphertext.toString("base64"),
        }),
        plan.before,
      );
      return { status: "imported", ...plan.summary };
    });
  }
  async withRevision<T>(
    revision: string,
    action: () => Promise<T>,
  ): Promise<T> {
    return withLock(this.root, "password-store", async () => {
      if (this.revision() !== revision)
        throw Error("Saved login changed; review again");
      return action();
    });
  }
  removeReviewedInput(plan: PasswordImportPlan) {
    const file = rejectRedirects(path.resolve(plan.file));
    if (!inside(file, this.inbox) || file === this.inbox)
      throw Error("password_input_outside_inbox");
    const recovery = confined(this.root, "removed/" + randomUUID());
    quarantineReviewedFile(file, plan.sourceHash, recovery);
    fs.unlinkSync(recovery);
  }
}
