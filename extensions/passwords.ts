import path from "node:path";
import { PasswordStore } from "../src/passwords/store.ts";
import {
  defaultStateRoot,
  selectedContext,
  vaultState,
} from "../src/storage/context.ts";
import { atomicJSON, exists } from "../src/platforms/filesystem.ts";
import { assistantUI } from "../src/assistant/ui.ts";
import type { ManagedBrowser } from "../src/research/playwright.ts";

export function installPasswords() {
  const store = () => new PasswordStore(selectedContext(defaultStateRoot()));
  async function setup(ctx: any) {
    const s = store();
    if (
      !(await ctx.ui.confirm(
        "Create a private password-export inbox?",
        "Optional CSV/JSON exports are plaintext input. This dedicated inbox stays outside the vault/source. Native import creates or updates an encrypted password file protected by your OS account; passwords are never roadmap evidence or model-visible values.\n\n" +
          s.inbox,
      ))
    )
      return;
    ctx.ui.notify(
      "Password inbox: " +
        s.setupInbox() +
        "\nPlace an export here, then run /chrysalis passwords import. You can return later.",
      "info",
    );
  }
  return {
    configured() {
      try {
        return store().configured();
      } catch {
        return false;
      }
    },
    revision() {
      try {
        return store().revision();
      } catch {
        return null;
      }
    },
    async secrets() {
      return (await store().records()).map((r) => r.password);
    },
    async offer(ctx: any) {
      const file = path.join(
        vaultState(selectedContext()),
        "passwords-offer.json",
      );
      if (exists(file)) return;
      const choice = await ctx.ui.select(
        "Optional saved-password import for the browser",
        ["Set up private CSV/JSON inbox", "Later", "Skip"],
      );
      if (choice === "Set up private CSV/JSON inbox") await setup(ctx);
      atomicJSON(file, {
        version: 1,
        offered: true,
        choice:
          choice === "Set up private CSV/JSON inbox"
            ? "setup_offered"
            : "deferred",
      });
    },
    async native(tokens: string[], ctx: any) {
      if (!ctx.hasUI || tokens.length > 1)
        throw Error(
          "Use /chrysalis passwords [setup | import | status] in native controls",
        );
      const action = tokens[0] ?? "status",
        s = store();
      if (action === "setup") return setup(ctx);
      if (action === "status") {
        ctx.ui.notify(
          JSON.stringify({
            configured: s.configured(),
            inbox: s.inbox,
            stored_values: "encrypted",
            model_secret_access: false,
            sync: "future_adapter_not_connected",
          }),
          "info",
        );
        return;
      }
      if (action !== "import")
        throw Error("Use passwords setup, import or status");
      const names = s.inputFiles();
      if (!names.length) {
        ctx.ui.notify(
          "No CSV/JSON exports in the private inbox. Run passwords setup, then place an export there.",
          "info",
        );
        return;
      }
      const labels = names.map(
        (n, i) => i + 1 + ". " + n.replace(/[\x00-\x1f\x7f\x1b]/g, "_"),
      );
      const chosen = await ctx.ui.select(
          "Select a password export (contents stay private)",
          labels,
        ),
        index = labels.indexOf(chosen ?? "");
      if (index < 0) return;
      const plan = await s.prepare(names[index]);
      const result = await s.apply(plan, () =>
        ctx.ui.confirm(
          "Import these saved browser logins?",
          JSON.stringify(plan.summary, null, 2) +
            "\nNew accounts append; matching accounts update. Missing accounts are retained. Passwords/usernames are encrypted, not copied to the vault, chat, memory or workers. File and store revisions will be checked again.",
        ),
      );
      ctx.ui.notify(JSON.stringify(result), "info");
      if (
        result.status === "imported" &&
        (await ctx.ui.confirm(
          "Remove this plaintext export from the inbox?",
          "Only the exact imported file is removed after a fresh byte check. This is file deletion, not secure erasure of backups or storage.",
        ))
      )
        s.removeReviewedInput(plan);
    },
    async chooseLogin(
      browser: ManagedBrowser,
      ctx: any,
      selectors: { username?: string; password?: string },
    ) {
      const origin = browser.loginOrigin(),
        s = store(),
        revision = s.revision(),
        fields = { ...selectors },
        rows = (await s.records()).filter((r) => r.origins.includes(origin));
      if (!revision || revision !== s.revision())
        throw Error("Saved login changed; review again");
      if (!rows.length)
        throw Error("No saved login matches this exact HTTPS origin");
      const safe = (v: string) =>
        v.replace(/[\x00-\x1f\x7f\x1b]/g, "_").slice(0, 200);
      return assistantUI.run(async () => {
        const labels = rows.map(
          (r, i) => i + 1 + ". " + safe(r.name) + " — " + safe(r.username),
        );
        const chosen = await ctx.ui.select("Saved login for " + origin, labels),
          index = labels.indexOf(chosen ?? "");
        if (index < 0) return;
        if (
          !(await ctx.ui.confirm(
            "Fill this saved login?",
            origin +
              "\nFields: " +
              JSON.stringify(fields) +
              "\nOnly this exact HTTPS origin and these fields are authorized. This tool does not click submit; the trusted page may react to input. Password values stay internal; subsequent clicks/requests retain native approval. Cross-origin requests are blocked while these credentials are in use.",
          ))
        )
          return;
        if (browser.loginOrigin() !== origin || revision !== s.revision())
          throw Error("Saved login page or store changed; review again");
        return {
          record: rows[index],
          approvedOrigin: origin,
          selectors: fields,
          revision,
        };
      });
    },
  };
}
