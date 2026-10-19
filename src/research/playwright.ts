import { BrowserSecretGuard } from "./secret-guard.ts";
import type { PasswordRecord } from "../passwords/import.ts";
import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { randomUUID } from "node:crypto";
import { assistantRoot } from "../assistant/profile.ts";
import { acquirePack } from "../assistant/install.ts";
import { confined } from "../platforms/filesystem.ts";
import { publicRequest, publicURL } from "./http.ts";
import { storeArtifact } from "../assistant/artifacts.ts";
export class ManagedBrowser {
  private context: any;
  private releasePack: (() => void) | undefined;
  private opening: Promise<void> | undefined;
  private closing: Promise<void> | undefined;
  private secrets = new BrowserSecretGuard();
  private credentialOrigins: Set<string> | undefined;
  configureSecrets(values: string[]) {
    this.secrets.configure(values);
  }
  loginOrigin() {
    return publicURL(this.page.url()).origin;
  }
  private page: any;
  private actionSignal: AbortSignal | undefined;
  private queue: Promise<unknown> = Promise.resolve();
  readonly state: string;
  private readonly profileName: string;
  constructor(state: string, profileName = "profile") {
    if (!/^[a-zA-Z0-9-]{1,80}$/.test(profileName))
      throw Error("Invalid managed profile identity");
    this.state = state;
    this.profileName = profileName;
  }
  async open(
    headed = false,
    permitWrite?: (url: string, method: string) => Promise<boolean>,
  ) {
    if (this.closing) await this.closing;
    if (this.opening) return this.opening;
    if (this.context) return;
    const pending = this.startOpen(headed, permitWrite);
    this.opening = pending;
    try {
      await pending;
    } finally {
      if (this.opening === pending) this.opening = undefined;
    }
  }
  private async startOpen(
    headed: boolean,
    permitWrite?: (url: string, method: string) => Promise<boolean>,
  ) {
    const profile = confined(
      assistantRoot(this.state),
      "browser/" + this.profileName,
    );
    fs.mkdirSync(profile, { recursive: true, mode: 0o700 });
    fs.chmodSync(profile, 0o700);
    const lease = acquirePack(this.state, "browser"),
      root = lease.root;
    this.releasePack = lease.release;
    const adblock = path.join(root, "adblock");
    try {
      const library: any = await import(
        pathToFileURL(path.join(root, "node_modules/playwright/index.mjs")).href
      );
      this.context = await library.chromium.launchPersistentContext(profile, {
        channel: "chromium",
        executablePath: lease.browserExecutable,
        headless: !headed,
        serviceWorkers: "block",
        acceptDownloads: false,
        chromiumSandbox: true,
        args: [
          // CPU rendering avoids stalled animation frames on headless hosts without a GPU.
          ...(!headed
            ? ["--disable-gpu", "--disable-software-rasterizer"]
            : []),
          "--disable-extensions-except=" + adblock,
          "--load-extension=" + adblock,
          "--proxy-server=http://127.0.0.1:9",
          "--proxy-bypass-list=<-loopback>",
          "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
        ],
      });
    } catch (error) {
      if (!this.context) {
        this.releasePack?.();
        this.releasePack = undefined;
      }
      throw error;
    }
    await this.context.routeWebSocket("**/*", (socket: any) => socket.close());
    await this.context.route("**/*", async (route: any) => {
      try {
        const request = route.request(),
          method = request.method();
        if (this.actionSignal?.aborted) throw Error("Cancelled");
        const destination = publicURL(request.url());
        if (
          this.credentialOrigins &&
          !this.credentialOrigins.has(destination.origin)
        )
          throw Error("Credential origin boundary");
        if (
          !["GET", "HEAD"].includes(method) &&
          !(permitWrite && (await permitWrite(request.url(), method)))
        )
          throw Error("External write needs native permission");
        if (this.actionSignal?.aborted) throw Error("Cancelled");
        const response = await publicRequest(request.url(), {
          signal: this.actionSignal,
          method,
          headers: await request.allHeaders(),
          body: request.postDataBuffer() ?? undefined,
        });
        const headers = { ...response.headers };
        for (const name of [
          "content-length",
          "transfer-encoding",
          "connection",
          "keep-alive",
          "proxy-authenticate",
          "proxy-authorization",
          "te",
          "trailer",
          "upgrade",
        ])
          delete headers[name];
        await route.fulfill({
          status: response.status,
          headers,
          body: response.body,
        });
      } catch {
        await route.abort("blockedbyclient");
      }
    });
    this.page =
      this.context
        .pages()
        .find((p: any) => !p.url().startsWith("chrome-extension:")) ??
      (await this.context.newPage());
  }
  run<T>(action: () => Promise<T>, signal?: AbortSignal) {
    const wrapped = async () => {
      if (signal?.aborted) throw Error("Browser action cancelled");
      this.actionSignal = signal;
      try {
        return await action();
      } finally {
        this.actionSignal = undefined;
      }
    };
    const next = this.queue.then(wrapped, wrapped);
    this.queue = next.catch(() => {});
    return next;
  }
  async navigate(url: string) {
    const destination = publicURL(url);
    if (
      this.credentialOrigins &&
      !this.credentialOrigins.has(destination.origin)
    )
      throw Error("Close the browser before changing credential origins");
    await this.page.goto(url, {
      waitUntil: "domcontentloaded",
      timeout: 25000,
    });
    return this.inspect();
  }
  async inspect() {
    return {
      url: this.secrets.url(this.page.url()),
      title: this.secrets.text(await this.page.title()).slice(0, 500),
      text: this.secrets
        .text(await this.page.locator("body").innerText({ timeout: 5000 }))
        .slice(0, 12000),
      links: await this.page
        .locator("a[href]")
        .evaluateAll((nodes: any[]) =>
          nodes.slice(0, 30).map((n) => ({
            text: n.textContent ?? "",
            url: n.href,
          })),
        )
        .then((links: any[]) =>
          links.map((l) => ({
            text: this.secrets.text(l.text).slice(0, 100),
            url: this.secrets.url(l.url),
          })),
        ),
    };
  }
  async interact(action: "click" | "fill", selector: string, value?: string) {
    if (selector.length > 500 || (value && value.length > 4000))
      throw Error("Browser interaction limit");
    const target = this.page.locator(selector);
    if (
      action === "fill" &&
      ((await target.getAttribute("type"))?.toLowerCase() === "password" ||
        /(?:current-password|new-password|one-time-code)/i.test(
          (await target.getAttribute("autocomplete")) ?? "",
        ) ||
        /(?:password|passwd|passcode|secret|otp)/i.test(
          ((await target.getAttribute("name")) ?? "") +
            " " +
            ((await target.getAttribute("id")) ?? ""),
        ))
    )
      throw Error("Enter credentials yourself in the managed browser");
    if (action === "click") await target.click({ timeout: 5000 });
    else await target.fill(value ?? "", { timeout: 5000 });
    return this.inspect();
  }
  async fillCredentials(
    record: PasswordRecord,
    selectors: { username?: string; password?: string },
    approvedOrigin: string,
  ) {
    const handles: any[] = [];
    try {
      this.secrets.configure([record.password]);
      if (
        this.loginOrigin() !== approvedOrigin ||
        !record.origins.includes(approvedOrigin) ||
        (!selectors.username && !selectors.password)
      )
        throw Error("invalid");
      const validate = async (handle: any, password: boolean) => {
        if (!handle || (await handle.ownerFrame()) !== this.page.mainFrame())
          throw Error("foreign frame");
        const safe = await handle.evaluate(
          (e: any, password: boolean) =>
            e.isConnected &&
            e.tagName.toLowerCase() === "input" &&
            (password
              ? e.type.toLowerCase() === "password"
              : ["text", "email", "tel"].includes(e.type.toLowerCase())),
          password,
        );
        if (!safe || this.loginOrigin() !== approvedOrigin)
          throw Error("changed");
      };
      const check = async (selector: string, password: boolean) => {
        if (
          selector.length > 500 ||
          selector.includes(">>") ||
          /^(xpath|text|internal):?=/.test(selector)
        )
          throw Error("invalid");
        const input = this.page.locator(selector);
        if ((await input.count()) !== 1) throw Error("invalid");
        const handle = await input.elementHandle();
        if (handle) handles.push(handle);
        await validate(handle, password);
        return handle;
      };
      const username = selectors.username
        ? await check(selectors.username, false)
        : undefined;
      const password = selectors.password
        ? await check(selectors.password, true)
        : undefined;
      this.credentialOrigins = new Set([approvedOrigin]);
      if (username) {
        await validate(username, false);
        await username.fill(record.username, { timeout: 5000 });
      }
      if (password) {
        await validate(password, true);
        await password.fill(record.password, { timeout: 5000 });
      }
      if (this.loginOrigin() !== approvedOrigin) throw Error("changed");
      return {
        status: "credentials_filled",
        origin: approvedOrigin,
        submitted: false,
      };
    } catch {
      throw Error("Saved credential fill failed or origin/field was unsafe");
    } finally {
      for (const h of handles) await h.dispose?.().catch(() => {});
    }
  }
  async screenshot() {
    if (this.secrets.enabled)
      throw Error(
        "Screenshots disabled when saved passwords are available in this private profile",
      );
    return storeArtifact(
      this.state,
      "png",
      await this.page.screenshot({ fullPage: false }),
      { source: this.page.url(), kind: "browser_screenshot" },
    );
  }
  async googleCookies() {
    if (!this.context) throw Error("Managed browser is not open");
    const cookies = await this.context.cookies([
      "https://gemini.google.com",
      "https://accounts.google.com",
    ]);
    const allowed = new Set([
      "__Secure-1PSID",
      "__Secure-1PSIDTS",
      "__Secure-3PSID",
      "__Secure-3PSIDTS",
      "SID",
      "HSID",
      "SSID",
      "APISID",
      "SAPISID",
    ]);
    return Object.fromEntries(
      cookies
        .filter(
          (c: any) =>
            allowed.has(c.name) &&
            /(^|\.)google\.com$/.test(c.domain.replace(/^\./, "")),
        )
        .map((c: any) => [c.name, c.value]),
    );
  }
  async close() {
    if (this.closing) return this.closing;
    const pending = (async () => {
      // An abort during launch must retain the pack until the returned context closes.
      try {
        await this.opening;
      } catch {}
      await this.context?.close();
      this.context = undefined;
      this.releasePack?.();
      this.releasePack = undefined;
      this.credentialOrigins = undefined;
      this.page = undefined;
    })();
    this.closing = pending;
    try {
      await pending;
    } finally {
      if (this.closing === pending) this.closing = undefined;
    }
  }
}
