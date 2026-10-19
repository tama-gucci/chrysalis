import { loadProfile } from "./profile.ts";
import { runnerStatus } from "../execution/linux.ts";
import { packRoot } from "./install.ts";
export function capabilityStatus(state: string) {
  const p = loadProfile(state);
  const installed = (pack: "browser" | "media") => {
    try {
      packRoot(state, pack);
      return true;
    } catch {
      return false;
    }
  };
  return {
    version: 1,
    capabilities: {
      execution: {
        enabled: p.features.execution,
        state: !p.features.execution
          ? "disabled"
          : runnerStatus().available && p.workspace
            ? "configured"
            : "needs_setup",
        network: p.workspace?.network ?? "off",
      },
      learning: {
        enabled: true,
        state: "ready",
        capture: p.features.lessonCapture,
      },
      memory: {
        enabled: p.features.memory,
        state: p.features.memory ? "configured" : "disabled",
        observations: p.features.observations,
      },
      specialists: {
        enabled: p.features.specialists,
        state: !p.features.specialists
          ? "disabled"
          : process.env.TMUX && p.workspace
            ? "configured"
            : "needs_setup",
      },
      research: {
        enabled: p.features.research,
        state: !p.features.research
          ? "disabled"
          : installed("browser")
            ? "configured"
            : "needs_setup",
      },
      browser: {
        enabled: p.features.browser,
        state: !p.features.browser
          ? "disabled"
          : installed("browser")
            ? "configured"
            : "needs_setup",
      },
      gemini_web: {
        enabled: false,
        installed: installed("media"),
        state: "deferred_verification",
        verified: false,
      },
    },
    routes: p.routes,
    limits: p.limits,
    fallback: "pause",
    status_semantics:
      "configured describes prerequisites, not verified provider access or successful live work",
  };
}
