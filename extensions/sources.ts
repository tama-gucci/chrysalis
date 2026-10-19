import path from "node:path";
import fs from "node:fs";
import { getAgentDir, CONFIG_DIR_NAME } from "@earendil-works/pi-coding-agent";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import type {
  ExtensionAPI,
  ExtensionCommandContext,
} from "@earendil-works/pi-coding-agent";
import { defaultStateRoot } from "../src/storage/context.ts";
import { PACKAGE_ROOT, digest, sha256 } from "../src/platforms/filesystem.ts";
import { SERVER_NAME, TOOL_SCHEMAS } from "../src/integrations/contracts.ts";

/** Public config-file contract supplements getMcpServers(), which lists extension registrations only. */
export function mcpConfiguration(
  pi: Pick<ExtensionAPI, "getMcpServers">,
  namespace: string,
  ctx?: any,
) {
  const files = [path.join(getAgentDir(), "mcp.json")];
  if (ctx?.isProjectTrusted?.())
    files.push(path.join(ctx.cwd, CONFIG_DIR_NAME, "mcp.json"));
  const identities: any[] = [],
    names: string[] = [];
  for (const file of files) {
    if (!fs.existsSync(file)) {
      identities.push({ file, hash: null });
      continue;
    }
    const stat = fs.lstatSync(file);
    if (!stat.isFile() || stat.size > 512 * 1024)
      throw Error(
        "MCP configuration is not a bounded regular file; inspect it natively",
      );
    const bytes = fs.readFileSync(file);
    let data: any;
    try {
      data = JSON.parse(bytes.toString("utf8"));
    } catch {
      throw Error("MCP configuration is invalid; inspect it natively");
    }
    if (
      !data ||
      typeof data !== "object" ||
      Array.isArray(data) ||
      (data.mcpServers !== undefined &&
        (!data.mcpServers ||
          typeof data.mcpServers !== "object" ||
          Array.isArray(data.mcpServers)))
    )
      throw Error("MCP configuration shape is invalid");
    identities.push({ file, hash: sha256(bytes) });
    names.push(...Object.keys(data.mcpServers ?? {}));
  }
  const matching = (name: string) =>
    !namespace || "mcp__" + name.replace(/-/g, "_") === namespace;
  const registered = pi.getMcpServers().filter((s) => matching(s.name));
  return {
    filesIdentity: digest(identities),
    identity: digest({ files: identities, registered }),
    configured: names.some(matching),
    registered: registered.length > 0,
  };
}

/** Pi owns orchestration and user MCP configuration; chrysalis owns only this server. */
export function installSources(pi: ExtensionAPI) {
  const config = {
    type: "stdio" as const,
    command: process.execPath,
    args: [
      "--import",
      pathToFileURL(createRequire(import.meta.url).resolve("tsx")).href,
      path.join(PACKAGE_ROOT, "src/mcp/server.ts"),
      "--state",
      defaultStateRoot(),
    ],
    env: {
      TSX_DISABLE_CACHE: "1",
      TSX_TSCONFIG_PATH: path.join(PACKAGE_ROOT, "tsconfig.json"),
    },
    exposure: "codemode" as const,
    timeout: 35,
    description:
      "Optional native-authorized read-only chrysalis sources; Health and Maps content require native review.",
  };
  pi.registerMcpServer(SERVER_NAME, config);
  let loadedConfiguration: string | undefined;
  pi.on("session_start", (_event, ctx) => {
    loadedConfiguration = mcpConfiguration(
      pi,
      "mcp__" + SERVER_NAME,
      ctx,
    ).filesIdentity;
  });
  pi.on("session_shutdown", () => {
    pi.unregisterMcpServer(SERVER_NAME);
  });
  return (name: string, ctx?: any) => {
    try {
      const configuration = mcpConfiguration(pi, "mcp__" + SERVER_NAME, ctx);
      if (
        configuration.configured ||
        (loadedConfiguration &&
          loadedConfiguration !== configuration.filesIdentity)
      )
        return false;
      const server = pi.getMcpServers().find((s) => s.name === SERVER_NAME);
      if (
        !server ||
        digest(server.config) !== digest(config) ||
        path.resolve(server.extensionPath) !==
          path.join(PACKAGE_ROOT, "extensions/chrysalis.ts")
      )
        return false;
      const tool = pi.getAllTools().find((t) => t.name === name);
      if (
        !tool ||
        tool.sourceInfo.path !== "builtin:mcp" ||
        tool.sourceInfo.source !== "builtin"
      )
        return false;
      const prefix = "mcp__" + SERVER_NAME + "__",
        short = name.startsWith(prefix) ? name.slice(prefix.length) : "";
      return (
        !!TOOL_SCHEMAS[short] &&
        ["codemode", "deferred"].includes(tool.exposure) &&
        tool.namespace?.name === "mcp__" + SERVER_NAME &&
        digest(tool.parameters) === digest(TOOL_SCHEMAS[short])
      );
    } catch {
      return false;
    }
  };
}
export async function maskedInput(
  ctx: ExtensionCommandContext,
  title: string,
): Promise<string | undefined> {
  if (!ctx.hasUI) return undefined;
  return ctx.ui.custom<string | undefined>((tui, _theme, _keys, done) => {
    let value = "";
    return {
      render(width: number) {
        return [
          title.slice(0, width),
          "*".repeat(Math.min(value.length, width)),
          "Enter confirms; Escape cancels".slice(0, width),
        ];
      },
      invalidate() {},
      handleInput(data: string) {
        if (data === "\u001b") {
          value = "";
          done(undefined);
          return;
        }
        if (data === "\r" || data === "\n") {
          const result = value.trim();
          value = "";
          done(result || undefined);
          return;
        }
        if (data === "\u007f" || data === "\b") value = value.slice(0, -1);
        else {
          const pasted = data.replace(/\u001b\[20[01]~/g, "");
          if (
            /^[\x20-\x7e]+$/.test(pasted) &&
            value.length + pasted.length <= 8192
          )
            value += pasted;
        }
        tui.requestRender();
      },
      dispose() {
        value = "";
      },
    };
  });
}

/** Read-only native evidence; no external-editor shortcut, file writes or session entry. */
export async function memoryOnlyView(
  ctx: ExtensionCommandContext,
  title: string,
  text: string,
): Promise<void> {
  if (!ctx.hasUI) throw Error("native_evidence_requires_interactive_ui");
  if (Buffer.byteLength(text) > 128 * 1024)
    throw Error("native_evidence_limit");
  await ctx.ui.custom<void>((tui, _theme, _keys, done) => {
    let lines = text.split("\n"),
      offset = 0,
      shown: string[] = [];
    text = "";
    return {
      render(width: number) {
        const columns = Math.max(1, width),
          height = Math.max(1, Math.min(20, tui.terminal.rows - 5));
        shown = lines.flatMap((line) =>
          line.length
            ? Array.from({ length: Math.ceil(line.length / columns) }, (_, i) =>
                line.slice(i * columns, (i + 1) * columns),
              )
            : [""],
        );
        offset = Math.min(offset, Math.max(0, shown.length - height));
        return [
          title.slice(0, columns),
          ...shown.slice(offset, offset + height),
          "Arrows/PageUp/PageDown scroll; Enter/Escape close".slice(0, columns),
        ];
      },
      invalidate() {},
      handleInput(data: string) {
        if (["\r", "\n", "\u001b"].includes(data)) {
          lines = [];
          shown = [];
          done();
          return;
        }
        if (data === "\u001b[A") offset = Math.max(0, offset - 1);
        if (data === "\u001b[B") offset++;
        if (data === "\u001b[5~") offset = Math.max(0, offset - 15);
        if (data === "\u001b[6~") offset += 15;
        tui.requestRender();
      },
      dispose() {
        lines = [];
        shown = [];
      },
    };
  });
}
