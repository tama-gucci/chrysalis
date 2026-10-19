import test from "node:test";
import assert from "node:assert/strict";
import { ManagedBrowser } from "../src/research/playwright.ts";
import http from "node:http";
import { randomUUID } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { PACKAGE_ROOT } from "../src/platforms/filesystem.ts";
test(
  "managed Chromium retains a synthetic login and loads pinned adblock without host-network access",
  { skip: !process.env.CHRYSALIS_BROWSER_ACCEPTANCE_STATE },
  async () => {
    const browser = new ManagedBrowser(
        process.env.CHRYSALIS_BROWSER_ACCEPTANCE_STATE!,
        "acceptance-" + randomUUID(),
      ),
      internal = browser as any;
    let hits = 0;
    const canary = http.createServer((_req, res) => {
      hits++;
      res.setHeader("Access-Control-Allow-Origin", "*");
      res.end("host-canary");
    });
    await new Promise<void>((resolve) =>
      canary.listen(0, "127.0.0.1", resolve),
    );
    const port = (canary.address() as any).port;
    assert.equal(
      await (await fetch("http://127.0.0.1:" + port)).text(),
      "host-canary",
    );
    try {
      await browser.open();
      await internal.context.addCookies([
        {
          name: "synthetic_login",
          value: "synthetic-session-canary",
          domain: "example.com",
          path: "/",
          secure: true,
          expires: Math.floor(Date.now() / 1000) + 3600,
        },
      ]);
      await internal.page.route("https://example.com/synthetic", (route: any) =>
        route.fulfill({
          contentType: "text/html",
          body: '<title>Synthetic page</title><body><h1>Evidence</h1><input id="choice"><button id="apply" onclick="document.querySelector(\'h1\').textContent=\'Reviewed\'">Apply</button></body>',
        }),
      );
      const page = await browser.navigate("https://example.com/synthetic");
      assert.match(page.text, /Evidence/);
      assert(!JSON.stringify(page).includes("synthetic-session-canary"));
      await browser.interact("fill", "#choice", "Synthetic input");
      const clicked = await browser.interact("click", "#apply");
      assert.match(clicked.text, /Reviewed/);
      const extension =
        internal.context
          .serviceWorkers()
          .find((w: any) => w.url().startsWith("chrome-extension:")) ??
        (await internal.context.waitForEvent("serviceworker", {
          timeout: 10000,
        }));
      const manifest = await extension.evaluate(() =>
        chrome.runtime.getManifest(),
      );
      assert.match(manifest.name, /uBlock/i);
      assert.equal(
        manifest.version,
        JSON.parse(
          fs.readFileSync(
            path.join(PACKAGE_ROOT, "resources/browser.lock.json"),
            "utf8",
          ),
        ).adblock.version,
      );
      await browser.close();
      await browser.open();
      assert(
        (await internal.context.cookies("https://example.com")).some(
          (c: any) =>
            c.name === "synthetic_login" &&
            c.value === "synthetic-session-canary",
        ),
      );
      const baselineHits = hits;
      await internal.page.goto("http://127.0.0.1:" + port).catch(() => {});
      assert.equal(
        hits,
        baselineHits,
        "Managed Chromium must not reach the host canary",
      );
    } finally {
      await browser.close();
      await new Promise<void>((resolve) => canary.close(() => resolve()));
    }
  },
);
