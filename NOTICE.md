# Dependency and integration notices

chrysalis's own code is MIT licensed. Third-party code retains its original license. npm includes
the upstream license files in installed dependencies; optional downloads remain external.

| Component | Pinned version | Integration |
| --- | --- | --- |
| [pi-guardrails](https://github.com/aliou/pi-guardrails) | 0.19.0 | Reuses risk/permission rules behind immutable execution isolation |
| [pi-blackhole](https://github.com/k0valik/pi-blackhole) | 0.5.12 | Wrapped recall/compaction and explicit-model memory workers |
| [interactive subagents](https://github.com/maplezzk/pi-extensions/tree/main/packages/pi-interactive-subagents) | 3.16.4 | Fixed-role wrapper and version-checked child-launch/completion patches |
| [grok-mermaid](https://www.npmjs.com/package/grok-mermaid) | 0.2.3 | Bounded local Unicode diagram renderer |
| [Playwright](https://github.com/microsoft/playwright) | 1.64.0 | Optional managed persistent Chromium automation |
| [uBlock Origin Lite](https://github.com/uBlockOrigin/uBOL-home) | 2026.1006.1931 | Optional GPL-3.0 Chromium extension; official archive hash in browser.lock.json |
| [pi-web-access](https://github.com/nicobailon/pi-web-access) | 0.38.0 | Optional Gemini Web client only; account/video acceptance deferred |

The teaching workflow is independently implemented; no learn configuration is copied. Browser
search uses controlled Playwright visible evidence rather than loading the full web-access tool
suite. Package dependency pinning does not by itself establish compatibility or live acceptance.
