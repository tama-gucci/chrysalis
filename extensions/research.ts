import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import {
  PACKAGE_ROOT,
  digest,
  atomicJSON,
} from "../src/platforms/filesystem.ts";
import { loadProfile, assistantRoot } from "../src/assistant/profile.ts";
import { defaultStateRoot } from "../src/storage/context.ts";
import { assistantUI } from "../src/assistant/ui.ts";
import { packRoot } from "../src/assistant/install.ts";
import { sharedBudget } from "../src/assistant/budgets.ts";
import { createJiti } from "jiti";
import { ManagedBrowser } from "../src/research/playwright.ts";
import { analyzeYouTube } from "../src/research/gemini-web.ts";
import type { installPasswords } from "./passwords.ts";
export function installResearch(
  pi: ExtensionAPI,
  origin = path.join(PACKAGE_ROOT, "extensions/chrysalis.ts"),
  readOnly = false,
  passwords?: ReturnType<typeof installPasswords>,
) {
  const state = defaultStateRoot(),
    browser = new ManagedBrowser(
      state,
      readOnly
        ? "researcher-" +
          path.basename(
            path.dirname(process.env.CHRYSALIS_CHILD_TASK ?? "child"),
          )
        : "profile",
    ),
    defs = new Map<string, string>();
  const publicBrowser = new ManagedBrowser(
    state,
    "public-research" +
      (readOnly
        ? "-" +
          path.basename(
            path.dirname(process.env.CHRYSALIS_CHILD_TASK ?? "child"),
          )
        : ""),
  );
  let manual = false;
  const budget = () => {
    const p = loadProfile(state);
    return sharedBudget(state, p.limits.calls, p.limits.concurrency);
  };
  function register(t: any) {
    defs.set(
      t.name,
      digest({
        name: t.name,
        description: t.description,
        parameters: t.parameters,
      }),
    );
    pi.registerTool(t);
  }
  async function open(ctx: any, selected: ManagedBrowser) {
    if (selected === browser && manual)
      throw Error("Close the native manual browser before model automation");
    if (selected === browser && passwords) {
      const secrets = passwords.configured() ? await passwords.secrets() : [];
      selected.configureSecrets(secrets);
    }
    await selected.open(false, (url, method) =>
      selected === browser && !readOnly && ctx.hasUI
        ? assistantUI.run(() =>
            ctx.ui.confirm(
              "Allow this browser request?",
              method +
                " " +
                new URL(url).origin +
                "\nMay change an account or send page input. No request headers or cookies will be shown.",
            ),
          )
        : Promise.resolve(false),
    );
  }
  async function run(
    ctx: any,
    action: () => Promise<any>,
    selected = browser,
    signal?: AbortSignal,
  ) {
    if (
      !loadProfile(state).features.research &&
      !loadProfile(state).features.browser
    )
      throw Error("Enable research/browser through native capabilities");
    const done = budget().reserve("browser_research");
    const abort = () => {
      void selected.close();
    };
    signal?.addEventListener("abort", abort, { once: true });
    try {
      if (signal?.aborted) throw Error("Research cancelled");
      await open(ctx, selected);
      const result = await selected.run(action, signal);
      if (typeof result.text === "string") {
        const length = result.text.length,
          cap = Math.floor(loadProfile(state).limits.resultChars / 2);
        result.text = result.text.slice(0, cap);
        result.omitted_text_chars = Math.max(0, length - cap);
      }
      if (Array.isArray(result.links)) {
        result.omitted_links = Math.max(0, result.links.length - 8);
        result.links = result.links.slice(0, 8).map((l: any) => ({
          text: l.text,
          url: String(l.url).slice(0, 500),
        }));
      }
      const cap = loadProfile(state).limits.resultChars;
      while (
        JSON.stringify(result).length > cap &&
        Array.isArray(result.links) &&
        result.links.length
      ) {
        result.links.pop();
        result.omitted_links++;
      }
      if (
        JSON.stringify(result).length > cap &&
        typeof result.text === "string"
      ) {
        const remove = JSON.stringify(result).length - cap + 200;
        result.text = result.text.slice(
          0,
          Math.max(0, result.text.length - remove),
        );
        result.omitted_text_chars += remove;
      }
      return {
        content: [{ type: "text", text: JSON.stringify(result) }],
        details: { status: "ok", usage: null },
      };
    } catch {
      throw Error(
        "Browser action failed or was blocked; no private page diagnostics returned",
      );
    } finally {
      signal?.removeEventListener("abort", abort);
      done();
    }
  }
  register({
    name: "chrysalis_research",
    label: "Research",
    description:
      "Search public web pages or read a selected HTTPS page with the managed browser. Returns bounded visible evidence and citations; no extra summary model. Private documents/identifiers must not be included in generic queries.",
    parameters: Type.Object({
      action: Type.Union([Type.Literal("search"), Type.Literal("read")]),
      query: Type.Optional(Type.String()),
      url: Type.Optional(Type.String()),
    }),
    async execute(_id: any, p: any, _signal: any, _update: any, ctx: any) {
      if (!loadProfile(state).features.research)
        throw Error("Public research is disabled");
      if (!loadProfile(state).features.research)
        throw Error("Public research is disabled");
      if (p.action === "search" && (!p.query || p.query.length > 500))
        throw Error("Use a short public query");
      return run(
        ctx,
        () =>
          publicBrowser.navigate(
            p.action === "search"
              ? "https://www.google.com/search?q=" + encodeURIComponent(p.query)
              : p.url,
          ),
        publicBrowser,
        _signal,
      );
    },
  });
  register({
    name: "chrysalis_browser",
    label: "Browser",
    description:
      "Bounded browser navigation/inspection/click/fill/screenshot in a private persistent Chromium profile. Account-changing requests require native permission. No Node evaluation, arbitrary profile paths, cookie export or vault writes.",
    parameters: Type.Object({
      action: Type.Union([
        Type.Literal("navigate"),
        Type.Literal("inspect"),
        Type.Literal("click"),
        Type.Literal("fill"),
        Type.Literal("screenshot"),
      ]),
      url: Type.Optional(Type.String()),
      selector: Type.Optional(Type.String()),
      value: Type.Optional(Type.String()),
    }),
    async execute(_id: any, p: any, _signal: any, _update: any, ctx: any) {
      if (readOnly || !loadProfile(state).features.browser)
        throw Error("Browser automation is disabled");
      if (_signal?.aborted) throw Error("Browser action cancelled");
      if (
        ["navigate", "click", "fill"].includes(p.action) &&
        (!ctx.hasUI ||
          !(await assistantUI.run(() =>
            ctx.ui.confirm(
              "Approve this browser action?",
              JSON.stringify({
                action: p.action,
                url: p.url,
                selector: p.selector,
                value: p.value,
              }) +
                "\nAn action can submit page contents or change an account regardless of HTTP method. Never enter credentials through model tools; use the visible managed browser yourself.",
            ),
          )))
      )
        throw Error("Browser action permission declined");
      if (_signal?.aborted) throw Error("Browser action cancelled");
      return run(
        ctx,
        () =>
          p.action === "navigate"
            ? browser.navigate(p.url)
            : p.action === "inspect"
              ? browser.inspect()
              : p.action === "screenshot"
                ? browser.screenshot()
                : browser.interact(p.action, p.selector ?? "", p.value),
        browser,
        _signal,
      );
    },
  });
  if (passwords && !readOnly)
    register({
      name: "chrysalis_browser_login",
      label: "Saved browser login",
      description:
        "Request native selection and consent to fill a saved login for the current exact HTTPS origin. Passwords stay internal. No credential values, inventory export, automatic submission or child access.",
      parameters: Type.Object({
        username_selector: Type.Optional(Type.String()),
        password_selector: Type.Optional(Type.String()),
      }),
      async execute(
        _id: any,
        p: any,
        signal: AbortSignal,
        _update: any,
        ctx: any,
      ) {
        if (
          !ctx.hasUI ||
          !loadProfile(state).features.browser ||
          !passwords.configured()
        )
          throw Error(
            "Saved login needs native UI, browser capability and an imported password store",
          );
        if (signal?.aborted) throw Error("Browser action cancelled");
        await open(ctx, browser);
        const choice = await passwords.chooseLogin(browser, ctx, {
          username: p.username_selector,
          password: p.password_selector,
        });
        if (!choice)
          return {
            content: [
              { type: "text", text: JSON.stringify({ status: "declined" }) },
            ],
            details: {},
          };
        return run(
          ctx,
          () => {
            if (passwords.revision() !== choice.revision)
              throw Error("Saved login changed; review again");
            return browser.fillCredentials(
              choice.record,
              choice.selectors,
              choice.approvedOrigin,
            );
          },
          browser,
          signal,
        );
      },
    });
  register({
    name: "chrysalis_youtube",
    label: "YouTube research",
    description:
      "Experimental Gemini Web-only video question capability. Native account acceptance is deferred; no paid API or provider fallback. Cookies are never returned.",
    parameters: Type.Object({ url: Type.String(), question: Type.String() }),
    async execute(_id: any, p: any, signal: any) {
      if (readOnly) throw Error("Child media access is disabled");
      const accepted = path.join(
        assistantRoot(state),
        "gemini-native-acceptance.json",
      );
      if (!fs.existsSync(accepted))
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                status: "deferred_verification",
                reason: "native_gemini_acceptance_pending",
                verified: false,
              }),
            },
          ],
          details: {},
        };
      const record = JSON.parse(fs.readFileSync(accepted, "utf8"));
      if (record.version !== 1 || record.enabled !== true)
        throw Error("Gemini access disabled");
      const root = packRoot(state, "media"),
        jiti = createJiti(import.meta.url, { fsCache: false }),
        module: any = await jiti.import(
          path.join(root, "node_modules/pi-web-access/gemini-web.ts"),
        );
      const done = budget().reserve("gemini_web");
      try {
        const result = await analyzeYouTube(
          p.url,
          p.question,
          {
            cookies: () => browser.googleCookies(),
            query: module.queryWithCookies,
          },
          signal,
        );
        return {
          content: [{ type: "text", text: JSON.stringify(result) }],
          details: { verified: false },
        };
      } finally {
        done();
      }
    },
  });
  pi.on("session_shutdown", async () => {
    await browser.close();
    await publicBrowser.close();
  });
  return {
    active: () => {
      const p = loadProfile(state);
      return [
        ...(p.features.research ? ["chrysalis_research"] : []),
        ...(p.features.browser
          ? [
              "chrysalis_browser",
              ...(passwords?.configured() ? ["chrysalis_browser_login"] : []),
            ]
          : []),
        ...(fs.existsSync(
          path.join(assistantRoot(state), "gemini-native-acceptance.json"),
        )
          ? ["chrysalis_youtube"]
          : []),
      ];
    },
    allowed(name: string) {
      const t = pi.getAllTools().find((t) => t.name === name);
      return (
        defs.has(name) &&
        !!t &&
        path.resolve(t.sourceInfo.path) === origin &&
        digest({
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        }) === defs.get(name)
      );
    },
    native: async (tokens: string[], ctx: any) => {
      if (!ctx.hasUI || tokens.length > 1)
        throw Error(
          "Use browser open, browser close or browser status in native controls",
        );
      const action = tokens[0] ?? "status";
      if (action === "status") {
        ctx.ui.notify(
          JSON.stringify({
            manual_open: manual,
            enabled: loadProfile(state).features.browser,
            account_verified: false,
          }),
          "info",
        );
        return;
      }
      if (action === "close") {
        await browser.close();
        manual = false;
        return;
      }
      if (action !== "open" || !loadProfile(state).features.browser)
        throw Error(
          "Enable the browser capability before opening the managed browser",
        );
      if (
        !(await ctx.ui.confirm(
          "Open your private managed browser?",
          "A visible Chromium window opens on this Linux host. You may sign in yourself; login cookies persist privately. Model automation is blocked while this manual window is open. Your manual page actions permit their own requests. Gemini/YouTube model access stays deferred.",
        ))
      )
        return;
      await browser.close();
      manual = true;
      try {
        await browser.open(true, async () => true);
        await browser.navigate("https://gemini.google.com/");
      } catch (e) {
        manual = false;
        await browser.close();
        throw e;
      }
    },
    status: () => ({
      budget: budget().status(),
      gemini: "deferred_verification",
    }),
  };
}
