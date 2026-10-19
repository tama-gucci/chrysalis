import fs from "node:fs";
import { mcpConfiguration } from "./sources.ts";
import path from "node:path";
import type { ExtensionAPI, ToolInfo } from "@earendil-works/pi-coding-agent";
import { defaultStateRoot } from "../src/storage/context.ts";
import { selectedContext } from "../src/storage/context.ts";
import {
  PACKAGE_ROOT,
  confined,
  digest,
  exists,
  inside,
  raw,
  rejectRedirects,
  atomicJSON,
  atomic,
  sha256,
  canonical,
  withSyncLock,
} from "../src/platforms/filesystem.ts";
import { assistantUI } from "../src/assistant/ui.ts";

/** An annotation is a claim. Only an exact native grant supplies authority. */
export function conversationToolDigest(tool: any) {
  return digest({
    name: tool.name,
    description: tool.description,
    parameters: tool.parameters,
    promptGuidelines: tool.promptGuidelines,
    exposure: tool.exposure,
    namespace: tool.namespace,
    annotations: tool.annotations,
    sourceInfo: tool.sourceInfo,
    reachesTools: tool.reachesTools ? String(tool.reachesTools) : undefined,
  });
}
const legacyDigest = (tool: any) =>
  digest({
    name: tool.name,
    description: tool.description,
    parameters: tool.parameters,
    promptGuidelines: tool.promptGuidelines,
  });
const mcpOrigin = (t: any) =>
  t?.sourceInfo?.path === "builtin:mcp" &&
  t.sourceInfo.source === "builtin" &&
  (!t.namespace || /^mcp__/.test(t.namespace.name));
const reserved = (name: string) =>
  /^(chrysalis_|mcp__chrysalis_sources__)/.test(name) ||
  ["read", "bash", "write", "edit", "codemode", "tool_search"].includes(name);

export function builtinOrchestration(tool: ToolInfo | undefined) {
  return (
    !!tool &&
    ["builtin:codemode", "builtin:tool-search"].includes(
      tool.sourceInfo?.path,
    ) &&
    tool.sourceInfo.source === "builtin" &&
    typeof tool.reachesTools === "function" &&
    tool.exposure !== "hidden"
  );
}

/** Public metadata plus operator grants; never loads or rewrites another package. */
export function installCompanions(pi: ExtensionAPI) {
  const file = confined(defaultStateRoot(), "host-addons.json");
  const policy = () => {
    if (exists(file) && !fs.lstatSync(file).isFile())
      throw Error("Host policy must be a regular file");
    const p = exists(file)
      ? JSON.parse(raw(file, 128 * 1024).toString("utf8"))
      : { version: 2, tools: [], skill_roots: [] };
    if (
      ![1, 2].includes(p.version) ||
      !Array.isArray(p.tools) ||
      !Array.isArray(p.skill_roots) ||
      p.tools.length > 128 ||
      p.skill_roots.length > 16
    )
      throw Error("Invalid host add-on policy");
    const names = new Set();
    for (const t of p.tools) {
      if (
        !t ||
        typeof t.name !== "string" ||
        reserved(t.name) ||
        names.has(t.name) ||
        typeof t.extension_path !== "string" ||
        !(
          path.isAbsolute(t.extension_path) ||
          (p.version === 2 && t.extension_path === "builtin:mcp")
        ) ||
        !/^[a-f0-9]{64}$/.test(t.definition_sha256) ||
        (p.version === 2 && !["read-only", "review"].includes(t.mode))
      )
        throw Error("Invalid host conversation tool binding");
      names.add(t.name);
    }
    for (const r of p.skill_roots) {
      if (typeof r !== "string" || !path.isAbsolute(r))
        throw Error("Invalid host skill root");
      const resolved = rejectRedirects(r),
        protectedRoots = [PACKAGE_ROOT, defaultStateRoot()];
      try {
        protectedRoots.push(selectedContext().vault);
      } catch {}
      if (
        !p.tools.some(
          (t: any) =>
            path.isAbsolute(t.extension_path) &&
            inside(
              resolved,
              p.version === 1
                ? path.resolve(path.dirname(t.extension_path), "..")
                : path.dirname(t.extension_path),
            ),
        ) ||
        protectedRoots.some(
          (target) => inside(resolved, target) || inside(target, resolved),
        )
      )
        throw Error(
          "Host skill root must be confined to a reviewed external package and disjoint from protected roots",
        );
    }
    return p;
  };
  // Validate at startup; reread on calls so revocation and reload have the same meaning.
  policy();
  let context: any, loadedConfiguration: string | undefined;
  pi.on?.("session_start", (_event, ctx) => {
    context = ctx;
    loadedConfiguration = mcpConfiguration(pi, "", ctx).filesIdentity;
  });
  const binding = (name: string, ctx: any = context) => {
    try {
      const p = policy(),
        b = p.tools.find((t: any) => t.name === name),
        t = pi.getAllTools().find((t) => t.name === name);
      if (
        !b ||
        !t ||
        t.exposure === "hidden" ||
        (mcpOrigin(t)
          ? b.extension_path !== "builtin:mcp"
          : rejectRedirects(path.resolve(t.sourceInfo.path)) !==
            rejectRedirects(b.extension_path)) ||
        (p.version === 1 ? legacyDigest(t) : conversationToolDigest(t)) !==
          b.definition_sha256
      )
        return;
      if (mcpOrigin(t)) {
        const config = mcpConfiguration(pi, t.namespace?.name ?? "", ctx);
        if (
          (!config.configured && !config.registered) ||
          (loadedConfiguration &&
            loadedConfiguration !== config.filesIdentity) ||
          b.mcp_configuration !== config.identity
        )
          return;
      }
      return { ...b, mode: p.version === 1 ? "read-only" : b.mode, tool: t };
    } catch {
      return;
    }
  };
  const protectedInput = (input: unknown, ctx: any) => {
    const roots = [PACKAGE_ROOT, defaultStateRoot()];
    try {
      roots.push(selectedContext().vault);
    } catch {}
    const normalize = (value: string) =>
      path
        .normalize(value.split(String.fromCharCode(92)).join(path.sep))
        .toLowerCase();
    const normalizedRoots = roots.map(normalize);
    const inspect = (value: unknown, key = ""): boolean => {
      if (typeof value === "string") {
        if (normalizedRoots.some((root) => normalize(value).includes(root)))
          return true;
        if (
          path.isAbsolute(value) ||
          /^(?:\.{1,2}[\\/]|[a-z]:[\\/])/i.test(value) ||
          /(?:path|file|directory|root|cwd)$/i.test(key)
        ) {
          const resolved = normalize(
            path.resolve(ctx?.cwd ?? process.cwd(), value),
          );
          return normalizedRoots.some(
            (root) => inside(resolved, root) || inside(root, resolved),
          );
        }
        return false;
      }
      if (Array.isArray(value)) return value.some((v) => inspect(v, key));
      if (value && typeof value === "object")
        return Object.entries(value).some(([k, v]) => inspect(v, k));
      return false;
    };
    return inspect(input);
  };
  return {
    allowed: (name: string) => binding(name)?.mode === "read-only",
    active: () =>
      policy()
        .tools.filter((t: any) => binding(t.name))
        .map((t: any) => t.name),
    readableSkill: (file: string) =>
      file.endsWith(".md") &&
      policy().skill_roots.some((r: string) =>
        inside(file, rejectRedirects(r)),
      ),
    async authorize(event: any, ctx: any) {
      const b = binding(event.toolName, ctx);
      if (!b)
        return {
          block: true,
          reason:
            "No exact scoped grant for this tool. Use /chrysalis tools review " +
            event.toolName +
            " to review its origin and scope. Vault mutations require chrysalis proposals and native approval.",
        };
      if (protectedInput(event.input, ctx))
        return {
          block: true,
          reason:
            "External tools cannot target the vault, package or private chrysalis state. Use reviewed vault operations or an explicitly selected execution workspace.",
        };
      if (b.mode === "read-only") return;
      if (!ctx.hasUI)
        return {
          block: true,
          reason:
            "This external operation requires native review; headless calls are denied.",
        };
      const identity = conversationToolDigest(b.tool),
        input = digest(event.input);
      const approved = await assistantUI.run(() =>
        ctx.ui.confirm(
          "Allow this external operation once?",
          JSON.stringify(
            {
              tool: event.toolName,
              origin: b.tool.sourceInfo,
              namespace: b.tool.namespace,
              annotations: b.tool.annotations ?? "unverified / absent",
              input: event.input,
            },
            null,
            2,
          ) + "\nNo authoritative vault writes or approvals are granted.",
        ),
      );
      const current = binding(event.toolName, ctx);
      if (
        !approved ||
        !current ||
        current.mode !== b.mode ||
        conversationToolDigest(current.tool) !== identity ||
        digest(event.input) !== input
      )
        return {
          block: true,
          reason:
            "External operation was declined or its registration changed during review.",
        };
    },
    async native(tokens: string[], ctx: any) {
      if (tokens[0] !== "review" || tokens.length !== 2 || !ctx.hasUI)
        throw Error(
          "Use /chrysalis tools review <exact-tool-name> in an interactive session",
        );
      const name = tokens[1],
        t = pi.getAllTools().find((t) => t.name === name);
      if (
        !t ||
        reserved(name) ||
        !(path.isAbsolute(t.sourceInfo?.path ?? "") || mcpOrigin(t)) ||
        t.exposure === "hidden"
      )
        throw Error(
          "Tool has no reviewable external registration; reserved tools retain their own policy",
        );
      const policyRevision = exists(file)
        ? sha256(raw(file, 128 * 1024))
        : null;
      const identity = conversationToolDigest(t);
      const mcp = mcpOrigin(t)
        ? mcpConfiguration(pi, t.namespace?.name ?? "", ctx)
        : undefined;
      if (
        mcp &&
        loadedConfiguration &&
        loadedConfiguration !== mcp.filesIdentity
      )
        throw Error(
          "MCP configuration changed; /reload before reviewing its new scope",
        );
      const mode = await ctx.ui.select("External tool authority", [
        "Review each external operation",
        "Trust this exact read-only implementation",
        "Cancel",
      ]);
      if (!mode || mode === "Cancel") return;
      const exact = JSON.stringify(
        {
          tool: t.name,
          source: t.sourceInfo,
          namespace: t.namespace,
          exposure: t.exposure,
          annotations: t.annotations ?? "absent",
          parameters: t.parameters,
          description: t.description,
          promptGuidelines: t.promptGuidelines,
          reachesTools: t.reachesTools ? String(t.reachesTools) : null,
          definition_sha256: identity,
        },
        null,
        2,
      );
      if (
        (await ctx.ui.editor("Review exact tool and scope", exact)) !== exact ||
        !(await ctx.ui.confirm(
          "Grant this external tool scope?",
          "Extension code is trusted host code. Hints do not prove safety. This grant permits no authoritative vault writes, credential access, account switching or memory-engine replacement.\n" +
            exact,
        ))
      )
        return;
      const current = pi.getAllTools().find((v) => v.name === name);
      if (
        !current ||
        conversationToolDigest(current) !== identity ||
        (mcp &&
          mcpConfiguration(pi, t.namespace?.name ?? "", ctx).identity !==
            mcp.identity)
      )
        throw Error("Tool or MCP configuration changed during review");
      const p = policy();
      // Legacy grants remain readable, but do not silently convert their weaker identities.
      if (p.version === 1 && p.tools.length)
        throw Error(
          "Legacy host policy: review a version 2 file separately before adding grants; existing grants are preserved",
        );
      p.version = 2;
      p.tools = p.tools.filter((b: any) => b.name !== name);
      p.tools.push({
        name,
        extension_path: mcpOrigin(t)
          ? "builtin:mcp"
          : rejectRedirects(t.sourceInfo.path),
        definition_sha256: identity,
        ...(mcp ? { mcp_configuration: mcp.identity } : {}),
        mode: mode.startsWith("Trust") ? "read-only" : "review",
      });
      withSyncLock(defaultStateRoot(), "host-addons-policy", () =>
        atomic(file, canonical(p) + "\n", policyRevision),
      );
      pi.setActiveTools([...new Set([...pi.getActiveTools(), name])]);
      ctx.ui.notify(
        "Scoped grant saved. Each call rechecks the effective registration.",
        "info",
      );
    },
    diagnostic: () =>
      pi.getAllTools().map((t) => ({
        name: t.name,
        origin: t.sourceInfo,
        namespace: t.namespace?.name,
        exposure: t.exposure,
        authority: builtinOrchestration(t)
          ? "Pi orchestration; descendants checked"
          : (binding(t.name)?.mode ?? "package policy or ungranted"),
        definition_sha256: conversationToolDigest(t),
      })),
  };
}
