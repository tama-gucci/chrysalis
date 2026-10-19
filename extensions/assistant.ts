import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";
import type {
  ExtensionAPI,
  ExtensionCommandContext,
} from "@earendil-works/pi-coding-agent";
import {
  loadProfile,
  saveProfile,
  defaults,
  ROLES,
  registerWorkspace,
  type AssistantProfile,
  type Role,
} from "../src/assistant/profile.ts";
import { defaultStateRoot } from "../src/storage/context.ts";
import { runnerStatus } from "../src/execution/linux.ts";
import { assistantUI } from "../src/assistant/ui.ts";
import { installPack, packRoot } from "../src/assistant/install.ts";
import { selectModel } from "./model-picker.ts";

export function installAssistantSettings(pi: ExtensionAPI) {
  async function models(ctx: ExtensionCommandContext) {
    const state = defaultStateRoot(),
      p = loadProfile(state),
      available = ctx.modelRegistry
        .getAvailable()
        .filter((m: any) => !m.type || m.type === "chat");
    const mode = await ctx.ui.select("Background model settings", [
      "Shared model",
      "Advanced: choose one role",
      "Disable background workers",
      "Keep current settings",
    ]);
    if (!mode || mode === "Keep current settings") return;
    if (mode === "Disable background workers") {
      p.features.observations = false;
      p.features.specialists = false;
      saveProfile(state, p);
      return;
    }
    const selectedRole = mode.startsWith("Advanced")
      ? ((await ctx.ui.select("Role", [...ROLES])) as Role | undefined)
      : undefined;
    if (mode.startsWith("Advanced") && !selectedRole) return;
    const names = available.map((m) => m.provider + "/" + m.id);
    const chosen = await selectModel(
      ctx,
      "Choose an authenticated chat model from Pi",
      [...names, "Skip"],
    );
    const index = names.indexOf(chosen ?? "");
    if (index < 0) return;
    const model = available[index];
    const thinking = model.reasoning
      ? await ctx.ui.select(
          "Thinking level (less thinking can reduce overhead)",
          ["off", "minimal", "low", "medium", "high", "xhigh"],
        )
      : "off";
    if (!thinking) return;
    const route: any = { provider: model.provider, model: model.id, thinking };
    for (const role of selectedRole ? [selectedRole] : ROLES)
      p.routes[role] = route;
    const preset = await ctx.ui.select("Usage preset", [
      "economical",
      "balanced",
      "thorough",
    ]);
    if (!preset) return;
    p.preset = preset as AssistantProfile["preset"];
    p.limits =
      preset === "economical"
        ? defaults().limits
        : {
            concurrency: preset === "balanced" ? 2 : 3,
            turns: preset === "balanced" ? 12 : 16,
            inputChars: preset === "balanced" ? 64000 : 96000,
            resultChars: preset === "balanced" ? 8000 : 12000,
            calls: preset === "balanced" ? 36 : 48,
            timeoutSeconds: 600,
          };
    if (
      await ctx.ui.confirm(
        "Save these private model routes?",
        "Specialists receive selected task briefs; enabled memory workers receive conversation context. This may send that context to the chosen providers. Native-only evidence and credentials are excluded.\n\n" +
          JSON.stringify(
            {
              routes: p.routes,
              limits: p.limits,
              fallback: "pause; never use the main model silently",
            },
            null,
            2,
          ),
      )
    )
      saveProfile(state, p);
  }
  async function capabilities(ctx: ExtensionCommandContext) {
    const state = defaultStateRoot(),
      p = loadProfile(state);
    const feature = await ctx.ui.select("Choose a capability to configure", [
      "memory",
      "observations",
      "specialists",
      "research",
      "browser",
      "lessonCapture",
      "execution",
      "Gemini Web (deferred)",
      "Keep current settings",
    ]);
    if (!feature || feature === "Keep current settings") return;
    if (feature === "execution") {
      await workspace(ctx);
      return;
    }
    if (feature === "Gemini Web (deferred)") {
      if (
        await ctx.ui.confirm(
          "Prepare optional media client?",
          "Install pinned web-access privately. No sign-in, cookie reads, video requests or paid API fallback. Gemini acceptance remains deferred.",
        )
      )
        ctx.ui.notify(
          JSON.stringify(await installPack(state, "media")),
          "info",
        );
      return;
    }
    const key = feature as keyof AssistantProfile["features"];
    const enable = await ctx.ui.select("Capability: " + feature, [
      "Enable",
      "Disable",
      "Later",
    ]);
    if (!enable || enable === "Later") return;
    if (
      enable === "Enable" &&
      feature === "observations" &&
      !["observer", "reflector", "dropper"].every((r) => p.routes[r as Role])
    ) {
      ctx.ui.notify(
        "Choose memory-worker models with /chrysalis models first",
        "warning",
      );
      return;
    }
    if (enable === "Enable" && feature === "specialists" && !p.routes.worker) {
      ctx.ui.notify(
        "Choose specialist models with /chrysalis models first",
        "warning",
      );
      return;
    }
    if (enable === "Enable" && ["browser", "research"].includes(feature)) {
      try {
        packRoot(state, "browser");
      } catch {
        if (
          !(await ctx.ui.confirm(
            "Install managed Chromium support?",
            "Install pinned Playwright and Chromium resources privately, with lifecycle scripts disabled. A browser download can use several hundred MB. No account sign-in occurs.",
          ))
        )
          return;
        await installPack(state, "browser");
      }
    }
    p.features[key] = enable === "Enable";
    if (key === "memory" && !p.features.memory) p.features.observations = false;
    if (key === "observations" && p.features[key]) p.features.memory = true;
    if (
      await ctx.ui.confirm(
        "Save capability choice?",
        feature +
          ": " +
          enable +
          ". Account sign-in and vault record adoption require their own controls.",
      )
    )
      saveProfile(state, p);
    ctx.ui.notify(
      "Settings saved. Use /reload before starting new optional work.",
      "info",
    );
  }
  async function workspace(ctx: ExtensionCommandContext) {
    const choice = await ctx.ui.select("Execution workspace", [
      "Create a private workspace",
      "Use an existing project directory",
      "Disable execution",
      "Later",
    ]);
    if (!choice || choice === "Later") return;
    const state = defaultStateRoot(),
      p = loadProfile(state);
    if (choice === "Disable execution") {
      p.features.execution = false;
      saveProfile(state, p);
      return;
    }
    if (!runnerStatus().available) {
      ctx.ui.notify(
        "The accepted Linux runner is unavailable. Install Bubblewrap through the capability setup; planning remains available.",
        "warning",
      );
      return;
    }
    let root: string | undefined;
    if (choice === "Create a private workspace") {
      root = path.join(
        os.homedir(),
        ".local",
        "share",
        "chrysalis-workspaces",
        randomUUID(),
      );
      fs.mkdirSync(root, { recursive: true, mode: 0o700 });
    } else root = await ctx.ui.input("Absolute path to the project workspace");
    if (!root) return;
    const vaultProfile = path.join(state, "profile.json");
    const vault = fs.existsSync(vaultProfile)
      ? JSON.parse(fs.readFileSync(vaultProfile, "utf8")).vault_root
      : undefined;
    const selected = registerWorkspace(state, root, vault);
    const network = await ctx.ui.select("Workspace networking", [
      "No sockets",
      "Isolated loopback for local tests",
      "Later",
    ]);
    if (!network || network === "Later") return;
    selected.network = network === "No sockets" ? "off" : "loopback";
    if (
      !(await ctx.ui.confirm(
        "Allow execution in this workspace?",
        selected.root +
          "\n\nCommands use a disposable copy and checked merge. External networking is disabled; " +
          (selected.network === "loopback"
            ? "isolated loopback is allowed"
            : "all sockets are blocked") +
          ". Vault, credentials, approvals and the live package remain inaccessible. Git/configuration secrets are excluded. Limits: 64 MiB workspace, 32 MiB scratch, 512 MiB aggregate RAM, 64 processes.",
      ))
    )
      return;
    p.workspace = selected;
    p.features.execution = true;
    saveProfile(state, p);
    pi.setActiveTools([
      ...new Set([...pi.getActiveTools(), "read", "bash", "write", "edit"]),
    ]);
    ctx.ui.notify(
      "Workspace selected. Bash and file tools now use isolated execution.",
      "info",
    );
  }
  return async (command: string, ctx: ExtensionCommandContext) => {
    if (
      !["models", "capabilities", "workspace", "assistant-setup"].includes(
        command,
      )
    )
      return false;
    if (!ctx.hasUI)
      throw Error("Assistant setup requires native interactive controls");
    {
      if (command === "models") await models(ctx);
      else if (command === "workspace") await workspace(ctx);
      else if (command === "capabilities") await capabilities(ctx);
      else {
        const choice = await ctx.ui.select(
          "Optional chrysalis assistant setup",
          [
            "Recommended: models then capabilities",
            "Set up an execution workspace",
            "Later",
          ],
        );
        if (choice === "Recommended: models then capabilities") {
          await models(ctx);
          await capabilities(ctx);
        } else if (choice === "Set up an execution workspace")
          await workspace(ctx);
      }
    }
    return true;
  };
}
