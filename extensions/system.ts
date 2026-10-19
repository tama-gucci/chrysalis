import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import { Type } from "typebox";
import {
  createBashTool,
  createReadTool,
  createWriteTool,
  createEditTool,
  getAgentDir,
  type ExtensionAPI,
  type ExtensionCommandContext,
} from "@earendil-works/pi-coding-agent";
import {
  PACKAGE_ROOT,
  confined,
  digest,
  exists,
  raw,
  withLock,
} from "../src/platforms/filesystem.ts";
import { selectedContext } from "../src/storage/context.ts";
import { assistantUI } from "../src/assistant/ui.ts";
import { conversationToolDigest } from "./companions.ts";
import { maskedInput, mcpConfiguration } from "./sources.ts";
import {
  approveSystem,
  assertSystemIdle,
  assertSystemVault,
  beginPrivileged,
  completePrivileged,
  assertBackendTarget,
  configIdentity,
  configurationIdentity,
  confinedSystemFile,
  currentOperation,
  loadSystemConfig,
  projectSystemLedger,
  recordSystem,
  requireSystemScope,
  systemRoot,
  systemLease,
} from "../src/system/state.ts";
import {
  checked,
  command,
  diskInventory,
  installTarget,
  inspectTarget,
  reconcileInstalled,
  runtimeObservation,
  observedGeneration,
  saveInstallSecrets,
  seedTarget,
} from "../src/system/native.ts";

const SERVER = "chrysalis_system";
const PREFIX = "mcp__" + SERVER + "__";
const BACKEND_TOOLS = new Set([
  "build",
  "diff",
  "switch",
  "generations",
  "eval_config",
  "locate_option",
  "check",
]);
const origin = path.join(PACKAGE_ROOT, "extensions/chrysalis.ts");
function backendResult(event: any): any {
  if (event.details?.status) return event.details;
  if (event.details?.structuredContent?.status)
    return event.details.structuredContent;
  for (const p of event.content ?? [])
    if (p.type === "text") {
      try {
        const r = JSON.parse(p.text);
        if (r && typeof r.status === "string") return r;
      } catch {}
    }
  return { status: "unknown" };
}
export function installSystem(pi: ExtensionAPI) {
  const optional = loadSystemConfig();
  if (!optional)
    return {
      active: () => [] as string[],
      allowed: (_name: string) => false,
      validateVault: (_vault: string) => {},
      authorize: async (event: any, _ctx: any) =>
        event.toolName.startsWith(PREFIX)
          ? {
              block: true,
              reason: "The optional NixOS system capability is not configured",
            }
          : undefined,
      command: async (_args: string[], ctx: any) =>
        ctx.ui.notify(
          "The optional NixOS system capability is not configured",
          "info",
        ),
    };
  const c = optional;
  const registration = {
    type: "stdio" as const,
    command: c.commands.nixAgent,
    cwd: c.configuration,
    env: {
      NIX_AGENT_FLAKE: c.configuration + "#" + c.host,
      XDG_STATE_HOME: path.join(c.state, "backend"),
    },
    exposure: "codemode" as const,
    timeout: 1900,
    description:
      "Pinned NixOS operations for the native-authorized Chrysalis outcome. Build jobs must be polled; dry-build is planning only.",
  };
  pi.registerMcpServer(SERVER, registration);
  let loadedFiles: string | undefined;
  let sessionContext: any;
  function backendIdentity(ctx: any = sessionContext) {
    const fresh = loadSystemConfig();
    if (!fresh || configIdentity(fresh) !== configIdentity(c))
      throw Error(
        "Native NixOS configuration changed; reload Pi before another outcome",
      );
    const config = mcpConfiguration(pi, "mcp__" + SERVER, ctx);
    const registered = pi.getMcpServers().find((s) => s.name === SERVER);
    if (
      config.configured ||
      (loadedFiles && config.filesIdentity !== loadedFiles) ||
      !registered ||
      digest(registered.config) !== digest(registration) ||
      path.resolve(registered.extensionPath) !== origin
    )
      throw Error(
        "System MCP registration changed; reload and review natively",
      );
    const tools = pi.getAllTools().filter((t) => t.name.startsWith(PREFIX));
    if (
      tools.length !== BACKEND_TOOLS.size ||
      tools.some(
        (t) =>
          !BACKEND_TOOLS.has(t.name.slice(PREFIX.length)) ||
          t.sourceInfo.path !== "builtin:mcp" ||
          t.sourceInfo.source !== "builtin" ||
          t.namespace?.name !== "mcp__" + SERVER ||
          !["deferred", "codemode"].includes(t.exposure),
      )
    )
      throw Error(
        "Pinned system backend tools are not ready or their identity changed",
      );
    return digest({
      registration: config.identity,
      tools: tools
        .sort((a, b) => a.name.localeCompare(b.name))
        .map(conversationToolDigest),
    });
  }
  const identities = new Map<string, string>();
  const register = (tool: any) => {
    identities.set(
      tool.name,
      digest({
        name: tool.name,
        description: tool.description,
        parameters: tool.parameters,
      }),
    );
    pi.registerTool(tool);
  };
  const owned = (name: string) => {
    const tool = pi.getAllTools().find((t) => t.name === name);
    return (
      !!tool &&
      path.resolve(tool.sourceInfo.path) === origin &&
      identities.get(name) ===
        digest({
          name: tool.name,
          description: tool.description,
          parameters: tool.parameters,
        })
    );
  };
  const scope = (ctx?: any) => requireSystemScope(c, backendIdentity(ctx));
  async function ledger() {
    let selected;
    try {
      selected = selectedContext(c.state);
    } catch {
      return {
        status: "pending-vault",
        message:
          "Complete the existing native vault onboarding after the installed system boots",
      };
    }
    try {
      return await projectSystemLedger(c, selected.vault);
    } catch {
      return {
        status: "pending-projection",
        message:
          "Private receipts are retained; resolve the ledger collision and reconcile",
      };
    }
  }
  async function begin(
    goal: string | undefined,
    ctx: any,
    rollback?: number,
    queued = false,
  ) {
    if (!ctx.hasUI)
      throw Error(
        "System authorization requires a native interactive Pi session",
      );
    const reviewOutcome = async () => {
      assertSystemIdle(c);
      const pending = currentOperation(c);
      if (pending?.pending)
        throw Error(
          "Observe the in-flight operation before changing its native scope",
        );
      if (
        pending &&
        !["verified", "closed", "failed"].includes(pending.phase) &&
        rollback === undefined
      ) {
        scope(ctx);
        if (c.mode === "installer") {
          const key = await maskedInput(
            ctx,
            "Resume: disk encryption passphrase",
          );
          const password = await maskedInput(
            ctx,
            "Resume: normal account password",
          );
          if (!key || !password) return { status: "cancelled" };
          await saveInstallSecrets(c, key, password);
          const progressFile = confined(systemRoot(c), "installation.json");
          const progress = exists(progressFile)
            ? JSON.parse(raw(progressFile, 65536).toString())
            : undefined;
          if (
            pending.phase === "approved" &&
            pending.disk &&
            pending.installation &&
            (!progress || progress.operation !== pending.id || !progress.seeded)
          )
            await seedTarget(c, pending.installation, pending.disk);
        }
        return {
          status: "resumed",
          operation: pending.id,
          phase: pending.phase,
        };
      }
      const request =
        goal ??
        (await ctx.ui.input(
          "Requested OS outcome",
          c.mode === "installer"
            ? "Install NixOS and complete Chrysalis onboarding"
            : "",
        ));
      if (!request) return { status: "cancelled" };
      let disk, choices;
      if (c.mode === "installer") {
        const disks = await diskInventory(c);
        const labels = disks.map(
          (d) =>
            d.model +
            " | " +
            (d.size / 2 ** 30).toFixed(1) +
            " GiB | " +
            d.path,
        );
        const picked = await ctx.ui.select(
          "Dedicated target disk: all data on this disk will be erased",
          labels,
        );
        if (!picked) return { status: "cancelled" };
        disk = disks[labels.indexOf(picked)];
        if (!disk) throw Error("The selected disk is no longer available");
        const user = await ctx.ui.input("Normal account name", "user");
        const name = await ctx.ui.input("Computer name", "chrysalis");
        const zone = await ctx.ui.input(
          "Named timezone",
          Intl.DateTimeFormat().resolvedOptions().timeZone,
        );
        if (!user || !name || !zone) return { status: "cancelled" };
        choices = { user, name, zone };
        if (
          !/^[a-z][a-z0-9_-]{0,30}$/.test(user) ||
          user === "root" ||
          !/^[a-z][a-z0-9_-]{0,30}$/.test(name)
        )
          throw Error("Use normal lowercase account and computer names");
        new Intl.DateTimeFormat("en", { timeZone: zone });
      }
      let selectedVault: string | undefined;
      try {
        selectedVault = selectedContext(c.state).vault;
      } catch {}
      if (rollback !== undefined && c.mode !== "installed")
        throw Error("Generation recovery is available on the installed system");
      if (
        rollback !== undefined &&
        pending &&
        ["building", "activating", "installing"].includes(pending.phase)
      )
        throw Error(
          "Observe the in-flight operation before authorizing recovery",
        );
      const recovery =
        c.mode === "installed" ? observedGeneration(rollback) : undefined;
      if (rollback !== undefined && !recovery)
        throw Error(
          "Requested generation does not exist in the actual system profile",
        );
      const identity = backendIdentity(ctx);
      const summary = {
        ledgerDestination:
          selectedVault ?? "The vault selected through native onboarding",
        outcome: request,
        recovery: recovery ?? null,
        mode: c.mode,
        configuration: c.configuration,
        host: c.host,
        disk: disk ?? null,
        storage: disk
          ? "Erase this dedicated disk; GPT, 1 GiB EFI, LUKS and Btrfs"
          : null,
        choices: choices ?? null,
        ledger:
          "Authorize machine-generated system history in the selected Chrysalis vault; personal records keep existing review rules",
      };
      const exact = JSON.stringify(summary, null, 2);
      if ((await ctx.ui.editor("Review OS outcome and scope", exact)) !== exact)
        return { status: "cancelled" };
      if (!(await ctx.ui.confirm("Authorize this OS outcome?", exact)))
        return { status: "cancelled" };
      let passphrase: string | undefined, password: string | undefined;
      if (disk) {
        passphrase = await maskedInput(
          ctx,
          "Disk encryption passphrase (at least eight characters)",
        );
        const repeat = await maskedInput(
          ctx,
          "Repeat disk encryption passphrase",
        );
        password = await maskedInput(
          ctx,
          "Normal account password (at least eight characters)",
        );
        if (
          !passphrase ||
          !password ||
          passphrase !== repeat ||
          passphrase.length < 8 ||
          password.length < 8
        )
          throw Error("Passwords cancelled, too short, or passphrases differ");
      }
      if (
        rollback !== undefined &&
        pending &&
        !["verified", "closed", "failed"].includes(pending.phase)
      )
        await recordSystem(
          c,
          pending.id,
          "closed",
          {
            reason: "Superseded by native approved generation recovery",
            ...runtimeObservation(),
          },
          (o) => {
            if (o.pending)
              throw Error("Observe the in-flight operation before recovery");
          },
        );
      const op = approveSystem(
        c,
        request,
        identity,
        disk,
        selectedVault,
        recovery,
        choices,
      );
      if (disk && choices) {
        await saveInstallSecrets(c, passphrase!, password!);
        await seedTarget(c, choices, disk);
        passphrase = password = undefined;
      }
      pi.setActiveTools([
        ...new Set([...pi.getActiveTools(), ...identities.keys()]),
      ]);
      pi.sendUserMessage(
        "The operator authorized this OS outcome: " +
          request +
          ". Host: " +
          c.host +
          ". Read chrysalis-system. Discover facts and edit ordinary Nix files in the selected configuration. Use the pinned backend, verify actual results, and preserve the system receipt. " +
          (disk
            ? "The native seed and secrets are ready. Review and build the target, then use chrysalis_system action=install. No other disk is authorized."
            : "A fresh completed diff and unchanged source are required before activation."),
      );
      return {
        status: "approved",
        operation: op.id,
        host: c.host,
        choices,
        targetDisk: disk?.path,
      };
    };
    return queued ? reviewOutcome() : assistantUI.run(reviewOutcome);
  }
  const pendingCalls = new Map<
    string,
    {
      operation: string;
      tool: string;
      source: string;
      input: any;
      privileged?: string;
    }
  >();
  register({
    name: "chrysalis_system",
    label: "System",
    description:
      "Request native approval for an OS outcome, inspect status, install the approved live target, or reconcile observed results and its fixed machine ledger. Cannot approve itself or write arbitrary vault records.",
    parameters: Type.Object({
      action: Type.Union(
        ["request", "status", "inspect", "install", "recover", "reconcile"].map(
          (a) => Type.Literal(a),
        ),
      ),
      goal: Type.Optional(Type.String({ maxLength: 4000 })),
    }),
    async execute(
      _id: string,
      args: any,
      signal: AbortSignal,
      _update: any,
      ctx: any,
    ) {
      let result;
      if (args.action === "request") result = await begin(args.goal, ctx);
      else if (args.action === "status") {
        const op = currentOperation(c);
        result = {
          mode: c.mode,
          host: c.host,
          operation: op
            ? {
                id: op.id,
                phase: op.phase,
                goal: op.goal,
                recovery: op.recovery,
              }
            : null,
          ...runtimeObservation(),
        };
      } else if (args.action === "inspect") {
        const op = scope(ctx);
        if (!op.disk) throw Error("No approved installation disk");
        result = await inspectTarget(c, op.disk);
      } else if (args.action === "reconcile")
        result = { ...(await reconcileInstalled(c)), ledger: await ledger() };
      else {
        scope(ctx);
        result = await withLock(
          confined(systemRoot(c), "locks"),
          "installation",
          async () => {
            const installed =
              currentOperation(c)?.phase === "installed"
                ? { status: "installed", operation: currentOperation(c)!.id }
                : await installTarget(c, signal, args.action === "recover");
            const envBefore = process.env.CHRYSALIS_HANDOFF_AGENT_DIR;
            process.env.CHRYSALIS_HANDOFF_AGENT_DIR = getAgentDir();
            try {
              const loader = pathToFileURL(
                createRequire(import.meta.url).resolve("tsx"),
              ).href;
              const privileged = beginPrivileged(
                c,
                currentOperation(c)!.id,
                "handoff",
              );
              const handoff = await command(
                c.commands.sudo,
                [
                  "-n",
                  "--preserve-env=CHRYSALIS_SYSTEM_CONFIG,CHRYSALIS_HANDOFF_AGENT_DIR",
                  "--",
                  c.commands.node,
                  "--import",
                  loader,
                  path.join(PACKAGE_ROOT, "src/system/cli.ts"),
                  "handoff",
                ],
                { timeout: 3_600_000, signal },
              );
              completePrivileged(c, privileged);
              if (handoff.code !== 0)
                throw Error(
                  "Handoff exited (" +
                    handoff.code +
                    "); inspect the target and resume its copy journal",
                );
              result = {
                ...installed,
                handoff: JSON.parse(handoff.output.trim()),
                next: "Reboot into the installed system; preserve the USB until boot verification",
              };
            } finally {
              if (envBefore === undefined)
                delete process.env.CHRYSALIS_HANDOFF_AGENT_DIR;
              else process.env.CHRYSALIS_HANDOFF_AGENT_DIR = envBefore;
            }
            return result;
          },
        );
      }
      return {
        content: [{ type: "text", text: JSON.stringify(result) }],
        details: result,
      };
    },
  });
  for (const [kind, factory] of [
    ["read", createReadTool],
    ["write", createWriteTool],
    ["edit", createEditTool],
    ["bash", createBashTool],
  ] as const) {
    const original: any = factory(c.configuration);
    register({
      ...original,
      name: "chrysalis_system_" + kind,
      label: "System " + kind,
      description:
        "Native-authorized NixOS context: " +
        original.description +
        (kind === "bash"
          ? " Trusted host administration; the ordinary chrysalis Bash tool remains isolated. Shell calls invalidate earlier build proof. Do not use shell activation or formatting: use the pinned backend or installation entrypoint so receipts can verify outcomes."
          : ""),
      async execute(id: string, input: any, signal: AbortSignal, update: any) {
        const op = scope();
        if (kind === "read") {
          const path = confinedSystemFile(c, input.path);
          return original.execute(id, { ...input, path }, signal, update);
        }
        if (
          op.pending ||
          [
            "building",
            "activating",
            "installing",
            "installed",
            "uncertain",
          ].includes(op.phase)
        )
          throw Error(
            "Reconcile or complete the in-flight operation before changing configuration",
          );
        assertSystemIdle(c);
        const boundedInput =
          kind === "bash"
            ? input
            : { ...input, path: confinedSystemFile(c, input.path) };
        const beforeSource = configurationIdentity(c.configuration);
        await recordSystem(
          c,
          op.id,
          op.phase,
          { stage: "system-" + kind, source: beforeSource, started: true },
          (o) => {
            if (o.pending || o.phase !== op.phase)
              throw Error("Concurrent OS operation detected");
            o.pending = systemLease(
              id,
              "system-" + kind,
              configurationIdentity(c.configuration),
            );
          },
        );
        let privileged: string | undefined;
        try {
          if (kind === "bash")
            privileged = beginPrivileged(c, op.id, "system-bash");
          const result = await original.execute(
            id,
            boundedInput,
            signal,
            update,
          );
          if (privileged) completePrivileged(c, privileged);
          const afterSource = configurationIdentity(c.configuration);
          const phase =
            op.phase === "verified" && beforeSource === afterSource
              ? "verified"
              : "approved";
          await recordSystem(
            c,
            op.id,
            phase,
            {
              stage: "system-" + kind,
              source: afterSource,
              commandCompleted: !result.isError,
              note: "Configuration context finished; a fresh diff is required before activation",
            },
            (o) => {
              if (o.pending?.id !== id || o.phase !== op.phase)
                throw Error("System context receipt changed");
              delete o.pending;
              delete o.build;
            },
          );
          return result;
        } catch (error) {
          await recordSystem(
            c,
            op.id,
            "uncertain",
            {
              stage: "system-" + kind,
              reason:
                "Interrupted system context; inspect state before continuing",
            },
            (o) => {
              if (
                o.pending?.id !== id ||
                ["closed", "failed"].includes(o.phase)
              )
                throw Error("System context receipt changed");
              delete o.pending;
            },
          );
          throw error;
        }
      },
    });
  }
  async function authorize(event: any, ctx: any) {
    if (!event.toolName.startsWith(PREFIX)) return;
    try {
      const short = event.toolName.slice(PREFIX.length);
      if (!BACKEND_TOOLS.has(short))
        throw Error("Unrecognized system backend tool");
      const op = scope(ctx),
        input = event.input ?? {};
      assertBackendTarget(c, input);
      const source = configurationIdentity(c.configuration);
      const poll = short === "build" && !!input.job_id;
      const rollback =
        short === "generations" && (input.action ?? "list") !== "list";
      if (short !== "generations" && !poll)
        input.flake_uri = c.configuration + "#" + c.host;
      if (c.mode === "installer" && (short === "switch" || rollback))
        throw Error(
          "The live system cannot be activated as the target; use the native installation entrypoint",
        );
      const mutating = ["build", "diff", "switch"].includes(short) || rollback;
      if (poll && op.build?.job !== input.job_id)
        throw Error("Build job is outside this outcome");
      let phase: "building" | "activating" = "building";
      const evidence: Record<string, unknown> = { source, tool: short };
      if (mutating) {
        assertSystemIdle(c);
        if (op.pending)
          throw Error(
            "Wait for the current backend call before another operation",
          );
        if (rollback) {
          if (
            input.action !== "rollback" ||
            !op.recovery ||
            ![op.recovery.path, op.recovery.generation].includes(
              input.generation,
            ) ||
            observedGeneration(op.recovery.generation)?.path !==
              op.recovery.path
          )
            throw Error(
              "Recovery requires the exact native-approved generation",
            );
          if (
            ["building", "activating", "installing", "installed"].includes(
              op.phase,
            )
          )
            throw Error("Observe the in-flight result before recovery");
          phase = "activating";
          Object.assign(evidence, {
            expectedRunning: op.recovery.path,
            recoveryGeneration: op.recovery.generation,
            before: runtimeObservation(),
          });
        } else if (short === "switch") {
          if (
            op.phase !== "built" ||
            op.build?.source !== source ||
            !op.build.storePath
          )
            throw Error(
              "Run a fresh completed diff for the unchanged source before activation",
            );
          phase = "activating";
          Object.assign(evidence, {
            expectedRunning: op.build.storePath,
            before: runtimeObservation(),
          });
        } else {
          const interruptedPoll =
            poll &&
            op.phase === "uncertain" &&
            op.events.at(-1)?.evidence.stage === "build";
          if (
            ["activating", "installing", "installed", "uncertain"].includes(
              op.phase,
            ) &&
            !interruptedPoll
          )
            throw Error("Reconcile the in-flight operation first");
          if (op.phase === "building" && !poll)
            throw Error(
              "Poll the tracked build to completion before another build or diff",
            );
          if (poll && op.phase !== "building" && !interruptedPoll)
            throw Error("The tracked build is no longer running");
        }
        await recordSystem(c, op.id, phase, evidence, (o) => {
          if (o.pending || o.phase !== op.phase)
            throw Error("Concurrent backend operation detected");
          o.pending = systemLease(event.toolCallId, short, source);
        });
        pendingCalls.set(event.toolCallId, {
          operation: op.id,
          tool: short,
          source: poll && op.build ? op.build.source : source,
          input: { ...input },
          privileged:
            short === "switch" || rollback
              ? beginPrivileged(c, op.id, short)
              : undefined,
        });
      }
      event.input = input;
    } catch (e: any) {
      return { block: true, reason: e.message };
    }
  }
  pi.on("tool_result", async (event: any) => {
    const call = pendingCalls.get(event.toolCallId);
    if (!call) return;
    pendingCalls.delete(event.toolCallId);
    const result = backendResult(event),
      current = currentOperation(c);
    // A late or duplicate result cannot replace a newer write-ahead transition.
    if (
      current?.id !== call.operation ||
      current.pending?.id !== event.toolCallId
    )
      return;
    let source: string;
    try {
      source = configurationIdentity(c.configuration);
    } catch {
      source = "unreadable";
    }
    const release = (o: import("../src/system/state.ts").SystemOperation) => {
      if (o.pending?.id !== event.toolCallId)
        throw Error("Stale backend result");
      delete o.pending;
      if (
        call.privileged &&
        !event.isError &&
        ["ok", "degraded"].includes(result.status)
      )
        completePrivileged(c, call.privileged);
    };
    const storePath =
      typeof result.store_path === "string" &&
      /^\/nix\/store\/[a-z0-9]{32}-[^/\n]+$/.test(result.store_path)
        ? result.store_path
        : undefined;
    const evidence = {
      source: call.source,
      stage: call.tool,
      status: event.isError ? "transport-error" : String(result.status),
      storePath: storePath ?? null,
      note: "Upstream diagnostics remain private; dry-build and transport success are not build proof",
    };
    if (
      event.isError ||
      ![
        "ok",
        "failed",
        "running",
        "started",
        "interrupted",
        "degraded",
      ].includes(result.status)
    ) {
      await recordSystem(c, call.operation, "uncertain", evidence, release);
    } else if (call.tool === "diff") {
      await recordSystem(
        c,
        call.operation,
        result.status === "ok" && storePath && source === call.source
          ? "built"
          : "build-failed",
        evidence,
        (o) => {
          release(o);
          o.build = {
            job: "completed-diff",
            source: call.source,
            storePath:
              result.status === "ok" && source === call.source
                ? storePath
                : undefined,
          };
        },
      );
    } else if (call.tool === "build") {
      const job =
        typeof result.job_id === "string" && result.job_id.length <= 256
          ? result.job_id
          : call.input.job_id
            ? current.build?.job
            : undefined;
      const running = ["running", "started"].includes(result.status);
      const phase = running
        ? job
          ? "building"
          : "uncertain"
        : result.status === "ok" && source === call.source
          ? "approved"
          : "build-failed";
      await recordSystem(c, call.operation, phase, evidence, (o) => {
        release(o);
        if (job)
          o.build = {
            job,
            source:
              o.build && o.build.job === job ? o.build.source : call.source,
          };
      });
    } else {
      const observation = runtimeObservation();
      const expected =
        call.tool === "generations"
          ? current.recovery?.path
          : current.build?.storePath;
      const actual =
        observation.running === expected &&
        observation.profile === expected &&
        source === call.source;
      const phase =
        actual && result.status === "degraded"
          ? "degraded"
          : actual && result.status === "ok"
            ? "verified"
            : "uncertain";
      await recordSystem(
        c,
        call.operation,
        phase,
        {
          ...evidence,
          ...observation,
          recovery: current.recovery ?? null,
          verification: [
            "running closure",
            "system profile",
            "source identity",
          ],
          health: result.summary?.health ?? null,
          healthNote:
            result.health_note ??
            (result.summary?.health
              ? null
              : "Service health was not established by this response"),
        },
        release,
      );
      await ledger();
    }
  });
  pi.on("before_agent_start", async (event: any) => ({
    systemPrompt:
      event.systemPrompt +
      "\n" +
      fs.readFileSync(path.join(PACKAGE_ROOT, "nix/rules.md"), "utf8"),
  }));
  const activeSystemTools = () => {
    try {
      requireSystemScope(c);
      return [...identities.keys()];
    } catch {
      return ["chrysalis_system"];
    }
  };
  pi.on("session_start", async (_event, ctx) => {
    sessionContext = ctx;
    loadedFiles = mcpConfiguration(pi, "mcp__" + SERVER, ctx).filesIdentity;
    if (currentOperation(c)) await reconcileInstalled(c);
    pi.setActiveTools([
      ...new Set([...pi.getActiveTools(), ...activeSystemTools()]),
    ]);
    if (c.mode === "installer" && ctx.hasUI && !currentOperation(c)) {
      pi.sendUserMessage(
        "Begin Chrysalis NixOS onboarding. Help the user sign in through Pi if necessary, then request native system setup with chrysalis_system action=request. Discover technical facts yourself; do not ask the user for installation commands.",
      );
    }
    if (
      c.mode === "installed" &&
      ctx.hasUI &&
      exists("/var/lib/chrysalis/install.json")
    ) {
      let selected = false;
      try {
        selectedContext(c.state);
        selected = true;
      } catch {}
      if (!selected)
        pi.sendUserMessage(
          "The installed Chrysalis system has booted. Continue the existing native vault onboarding with /chrysalis onboard. Do not reuse approvals from temporary mount paths. Then reconcile the machine ledger.",
        );
      else await ledger();
    }
  });
  pi.on("session_shutdown", () => pi.unregisterMcpServer(SERVER));
  return {
    active: activeSystemTools,
    allowed: owned,
    validateVault: (vault: string) => assertSystemVault(c, vault),
    authorize,
    async command(args: string[], ctx: ExtensionCommandContext) {
      if (!ctx.hasUI) throw Error("System controls require native UI");
      if (args[0] === "status") {
        ctx.ui.notify(
          JSON.stringify({
            mode: c.mode,
            phase: currentOperation(c)?.phase ?? "not-approved",
            ...runtimeObservation(),
          }),
          "info",
        );
        return;
      }
      if (args[0] === "reconcile") {
        ctx.ui.notify(
          JSON.stringify({
            ...(await reconcileInstalled(c)),
            ledger: await ledger(),
          }),
          "info",
        );
        return;
      }
      if (args[0] === "close") {
        const op = currentOperation(c);
        if (!op) return;
        if (
          op.pending ||
          ["building", "activating", "installing"].includes(op.phase)
        )
          throw Error(
            "Observe the in-flight result before ending this outcome",
          );
        if (
          await ctx.ui.confirm(
            "End this OS outcome?",
            "This revokes further system-tool authority. It does not undo changes or imply success.",
          )
        )
          await recordSystem(c, op.id, "closed", runtimeObservation(), (o) => {
            if (
              o.pending ||
              ["building", "activating", "installing"].includes(o.phase)
            )
              throw Error(
                "Observe the in-flight result before ending this outcome",
              );
          });
        return;
      }
      if (args[0] === "rollback") {
        const id = Number(args[1]);
        if (args.length !== 2 || !Number.isSafeInteger(id) || id < 1)
          throw Error(
            "Use /chrysalis system rollback <observed generation number>",
          );
        await begin("Recover system generation " + id, ctx, id, true);
      } else await begin(args.join(" ") || undefined, ctx, undefined, true);
    },
  };
}
