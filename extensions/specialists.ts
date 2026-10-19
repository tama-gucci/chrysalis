import { openRuntimeRoute, selectedModel } from "./provider-runtime.ts";
import { specialistUsage } from "./specialist-usage.ts";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { reserveWriterLease } from "../src/execution/lease.ts";
import { createRequire } from "node:module";
import { createJiti } from "jiti";
import { randomUUID } from "node:crypto";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { defaultStateRoot } from "../src/storage/context.ts";
import {
  assistantRoot,
  loadProfile,
  type Role,
} from "../src/assistant/profile.ts";
import {
  atomicJSON,
  digest,
  PACKAGE_ROOT,
  sha256,
  raw,
} from "../src/platforms/filesystem.ts";
import { sharedBudget } from "../src/assistant/budgets.ts";
const require = createRequire(import.meta.url);
const quote = (s: string) => "'" + s.replace(/'/g, "'\\''") + "'";

/** A narrow maintained patch fixes child resources/CLI; every anchor must match the pinned engine. */
export function prepareEngine(state: string) {
  const upstream = path.dirname(
    require.resolve("@maplezzk/pi-interactive-subagents"),
  );
  const manifest = JSON.parse(
    fs.readFileSync(path.join(upstream, "package.json"), "utf8"),
  );
  if (manifest.version !== "3.16.4")
    throw Error("Unreviewed specialist engine version");
  const root = path.join(assistantRoot(state), "specialist-engine");
  fs.mkdirSync(root, { recursive: true, mode: 0o700 });
  for (const dir of ["pi-extension", "locales"])
    fs.cpSync(path.join(upstream, dir), path.join(root, dir), {
      recursive: true,
    });
  atomicJSON(path.join(root, "config.json"), { status: { enabled: false } });
  const file = path.join(root, "pi-extension/subagents/index.ts");
  let source = fs.readFileSync(file, "utf8");
  const sdk = path.resolve(
    path.dirname(
      fileURLToPath(import.meta.resolve("@earendil-works/pi-coding-agent")),
    ),
    "..",
  );
  const child = path.join(PACKAGE_ROOT, "extensions/child.ts");
  function replace(from: string, to: string) {
    if (source.split(from).length !== 2)
      throw Error("Specialist compatibility anchor changed");
    source = source.replace(from, to);
  }
  replace(
    'const parts: string[] = ["pi", ...buildChildExtensionArgs()];',
    "const parts: string[] = [" +
      JSON.stringify(quote(process.execPath)) +
      ', "--import", ' +
      JSON.stringify(quote(require.resolve("tsx/esm"))) +
      ', "--import", ' +
      JSON.stringify(
        quote(path.join(PACKAGE_ROOT, "src/platforms/dependencies.mjs")),
      ) +
      ", " +
      JSON.stringify(
        quote(path.join(PACKAGE_ROOT, "extensions/child-host.mjs")),
      ) +
      ', "--no-skills", "--no-context-files", ...buildChildExtensionArgs([' +
      JSON.stringify(child) +
      "])];",
  );
  replace(
    "envParts.push(`PI_SUBAGENT_NAME=${shellEscape(params.name)}`);",
    "envParts.push(`CHRYSALIS_STATE_ROOT=${shellEscape(" +
      JSON.stringify(state) +
      ')}`);\n  envParts.push(`CHRYSALIS_CHILD_TASK=${shellEscape(join(targetCwdForSession, "task.json"))}`);\n  envParts.push(`PI_SUBAGENT_NAME=${shellEscape(params.name)}`);',
  );
  const environment = [
    "CHRYSALIS_DEPENDENCIES_ROOT",
    "CHRYSALIS_PI_ROOT",
    "CHRYSALIS_EXECUTION_CONFIG",
    "PI_CODING_AGENT_DIR",
    "NODE_PATH",
  ]
    .filter((key) => process.env[key])
    .map(
      (key) =>
        "  envParts.push(" +
        JSON.stringify(key + "=" + quote(process.env[key]!)) +
        ");",
    )
    .join("\n");
  replace(
    "  const envParts: string[] = [renameEnvironment];",
    "  const envParts: string[] = [renameEnvironment];\n" + environment,
  );
  fs.writeFileSync(file, source, { mode: 0o600 });
  const completion = path.join(root, "pi-extension/subagents/subagent-done.ts"),
    upstreamRequire = createRequire(path.join(upstream, "package.json"));
  let doneSource = fs.readFileSync(completion, "utf8");
  for (const name of ["ajv", "pi-extensions-i18n"]) {
    const from = JSON.stringify(name);
    if (doneSource.split(from).length !== 2)
      throw Error("Completion dependency anchor changed");
    doneSource = doneSource.replace(
      from,
      JSON.stringify(upstreamRequire.resolve(name)),
    );
  }
  fs.writeFileSync(completion, doneSource, { mode: 0o600 });
  return {
    root,
    file,
    done: path.join(root, "pi-extension/subagents/subagent-done.ts"),
  };
}
export async function installSpecialists(pi: ExtensionAPI) {
  const state = defaultStateRoot(),
    defs = new Map<string, string>(),
    jobs = new Map<string, any>();
  let engine: any,
    shuttingDown = false;
  const startupAborters = new Set<() => void>();
  async function load() {
    if (engine) return engine;
    if (!process.env.TMUX)
      throw Error(
        "Specialists need the managed tmux session; main-agent work remains available",
      );
    const prepared = prepareEngine(state);
    const aliases: Record<string, string> = {};
    const upstream = path.dirname(
      require.resolve("@maplezzk/pi-interactive-subagents"),
    );
    const engineRequire = createRequire(path.join(upstream, "package.json"));
    for (const name of ["pi-terminal-mux", "pi-extensions-i18n", "ajv"])
      aliases[name] = engineRequire.resolve(name);
    for (const name of [
      "@earendil-works/pi-coding-agent",
      "@earendil-works/pi-tui",
    ])
      aliases[name] = fileURLToPath(import.meta.resolve(name));
    aliases["@sinclair/typebox"] = import.meta.resolve("typebox");
    const jiti = createJiti(import.meta.url, {
      fsCache: false,
      alias: aliases,
    });
    const module: any = await jiti.import(prepared.file);
    const proxy = new Proxy(pi, {
      get(t, k, r) {
        if (k === "registerTool" || k === "registerCommand") return () => {};
        if (k === "on")
          return (event: string, callback: any) =>
            ["session_start", "session_shutdown"].includes(event)
              ? t.on(event as any, callback)
              : () => {};
        return Reflect.get(t, k, r);
      },
    });
    await module.default(proxy);
    engine = { ...module, prepared };
    return engine;
  }
  const tool: any = {
    name: "chrysalis_specialist",
    label: "Specialist",
    description:
      "Launch a fixed researcher, reviewer, diagram-maker or worker with native-selected model and isolated workspace policy. One bounded brief, no CLI/tool/model/cwd overrides, no vault authority or nested agents. Status and interruption use returned task IDs.",
    parameters: Type.Object({
      action: Type.Union([
        Type.Literal("launch"),
        Type.Literal("status"),
        Type.Literal("interrupt"),
      ]),
      role: Type.Optional(
        Type.Union([
          Type.Literal("researcher"),
          Type.Literal("reviewer"),
          Type.Literal("diagram-maker"),
          Type.Literal("worker"),
        ]),
      ),
      task: Type.Optional(Type.String()),
      id: Type.Optional(Type.String()),
    }),
    async execute(
      _call: string,
      p: any,
      signal: AbortSignal,
      _update: any,
      ctx: any,
    ) {
      const profile = loadProfile(state);
      if (p.action !== "launch") {
        const job = jobs.get(p.id);
        if (!job) {
          if (p.action !== "status" || !/^[a-f0-9-]{36}$/.test(p.id ?? ""))
            throw Error("Unknown task in this parent session");
          const file = path.join(
            assistantRoot(state),
            "tasks",
            p.id,
            "status.json",
          );
          const saved = JSON.parse(fs.readFileSync(file, "utf8"));
          return {
            content: [
              {
                type: "text",
                text: JSON.stringify({
                  ...saved,
                  live_status_unknown: ["starting", "running"].includes(
                    saved.status,
                  ),
                  resume:
                    "Launch a new bounded brief; old policy is never resumed silently",
                }),
              },
            ],
            details: {},
          };
        }
        if (
          p.action === "interrupt" &&
          ["running", "awaiting_child_exit"].includes(job.status)
        )
          job.abort();
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id: p.id,
                status: job.status,
                summary: job.summary,
                usage: job.usage ?? null,
              }),
            },
          ],
          details: {},
        };
      }
      if (signal?.aborted || shuttingDown)
        throw Error("Specialist launch cancelled");
      if (!profile.features.specialists)
        throw Error(
          "Enable specialists and choose model routes through native settings",
        );
      if (!p.role || !p.task || p.task.length > profile.limits.inputChars)
        throw Error("Choose a role and bounded task brief");
      const route = profile.routes[p.role as Role];
      if (
        !route ||
        !ctx.modelRegistry
          .getAvailable()
          .some(
            (m: any) => m.provider === route.provider && m.id === route.model,
          )
      )
        throw Error("Selected specialist model is unavailable; no fallback");
      if (!profile.features.execution || !profile.workspace)
        throw Error("Select an isolated workspace first");
      selectedModel(ctx.modelRegistry, route);
      const done = sharedBudget(
        state,
        profile.limits.calls,
        profile.limits.concurrency,
      ).reserve("specialist", profile.limits.turns);
      let releaseWriter: (unclaimedExitProved?: boolean) => boolean = () =>
        true;
      let launchAttempted = false;
      let cancelRunning: (() => void) | undefined;
      let completion: Promise<void> | undefined;
      let runtime: Awaited<ReturnType<typeof openRuntimeRoute>> | undefined;
      let startupCancelled = false;
      const cancelStartup = () => {
        startupCancelled = true;
        runtime?.dispose();
        cancelRunning?.();
      };
      startupAborters.add(cancelStartup);
      signal?.addEventListener("abort", cancelStartup, { once: true });
      const checkStartup = () => {
        if (startupCancelled || signal?.aborted || shuttingDown)
          throw Error("Specialist launch cancelled");
      };
      try {
        checkStartup();
        const e = await load(),
          id = randomUUID(),
          cwd = path.join(assistantRoot(state), "tasks", id);
        checkStartup();
        fs.mkdirSync(cwd, { recursive: true, mode: 0o700 });
        runtime = await openRuntimeRoute(
          ctx.modelRegistry,
          route,
          profile.limits,
        );
        checkStartup();
        atomicJSON(path.join(cwd, "task.json"), {
          version: 1,
          role: p.role,
          brief: p.task,
          childSha256: sha256(
            raw(path.join(PACKAGE_ROOT, "extensions/child.ts")),
          ),
          turns: profile.limits.turns,
          profileDigest: digest(profile),
          route,
          runtimeRoute: runtime.endpoint,
          doneExtension: e.prepared.done,
          doneSha256: sha256(raw(e.prepared.done)),
        });
        if (p.role === "worker")
          releaseWriter = reserveWriterLease(
            state,
            path.join(cwd, "task.json"),
          );
        const persist = (status: string, summary: any = null) =>
          atomicJSON(path.join(cwd, "status.json"), {
            id,
            role: p.role,
            status,
            summary,
            profileDigest: digest(profile),
            route,
          });
        persist("starting");
        const manager = {
          getSessionFile: () => ctx.sessionManager.getSessionFile(),
          getSessionId: () => ctx.sessionManager.getSessionId(),
          getSessionDir: () =>
            path.join(assistantRoot(state), "task-artifacts"),
        };
        checkStartup();
        launchAttempted = true;
        const running = await e.launchSubagent(
          {
            name: "chrysalis-" + p.role,
            task: p.task,
            model: route.provider + "/" + route.model + ":" + route.thinking,
            tools:
              p.role === "worker"
                ? "read,bash,write,edit,subagent_done,caller_ping"
                : p.role === "diagram-maker"
                  ? "read,bash,chrysalis_visual,subagent_done,caller_ping"
                  : p.role === "researcher"
                    ? "read,bash,chrysalis_research,subagent_done,caller_ping"
                    : "read,bash,subagent_done,caller_ping",
            cwd,
            interactive: false,
            denyTools: "subagent,subagent-resume,chrysalis_operation,codemode",
          },
          { cwd, sessionManager: manager },
        );
        const job: any = { running, status: "running", summary: null };
        jobs.set(id, job);
        const controller = new AbortController();
        const saveStatus = () => {
          try {
            persist(job.status, job.summary);
          } catch {
            job.persistenceFailed = true;
          }
        };
        const abort = () => {
          runtime?.dispose();
          controller.abort();
          job.status = "interrupted";
          saveStatus();
        };
        cancelRunning = abort;
        job.abort = abort;
        signal?.addEventListener("abort", abort, { once: true });
        const timer = setTimeout(abort, profile.limits.timeoutSeconds * 1000);
        const release = (proof: boolean) => {
          try {
            return releaseWriter(proof);
          } catch {
            return false;
          }
        };
        const settle = (unclaimedExitProved: boolean) => {
          runtime?.dispose();
          const outcome = job.status;
          if (release(unclaimedExitProved)) {
            done(job.usage ?? undefined);
            return;
          }
          job.status = "awaiting_child_exit";
          saveStatus();
          const poll = setInterval(() => {
            if (release(unclaimedExitProved)) {
              clearInterval(poll);
              done(job.usage ?? undefined);
              job.status = outcome;
              saveStatus();
            }
          }, 1000);
          poll.unref();
        };
        // Watch/abort ownership is established before any fallible persistence.
        completion = Promise.resolve()
          .then(() => e.watchSubagent(running, controller.signal))
          .then(
            (result: any) => {
              if (job.status !== "interrupted")
                job.status = result.exitCode === 0 ? "finished" : "failed";
              job.summary = String(result.summary ?? "").slice(
                0,
                profile.limits.resultChars,
              );
              try {
                job.usage = specialistUsage(running.sessionFile);
              } catch {}
              saveStatus();
              settle(!result.error && Number.isInteger(result.exitCode));
            },
            () => {
              if (job.status !== "interrupted") job.status = "failed";
              saveStatus();
              settle(false);
            },
          )
          .finally(() => {
            clearTimeout(timer);
            signal?.removeEventListener("abort", abort);
          });
        if (startupCancelled || signal?.aborted || shuttingDown) {
          abort();
          throw Error("Specialist launch cancelled");
        }
        atomicJSON(path.join(cwd, "runtime.json"), {
          sessionFile: running.sessionFile,
          surface: running.surface,
        });
        persist("running");
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify({
                id,
                role: p.role,
                status: "running",
                model: route.provider + "/" + route.model,
              }),
            },
          ],
          details: {},
        };
      } catch (e) {
        if (cancelRunning) {
          cancelRunning();
          await completion;
        } else {
          runtime?.dispose();
          if (releaseWriter(!launchAttempted)) done();
        }
        throw e;
      } finally {
        startupAborters.delete(cancelStartup);
        signal?.removeEventListener("abort", cancelStartup);
      }
    },
  };
  pi.on("session_shutdown", async () => {
    shuttingDown = true;
    for (const abort of startupAborters) abort();
    for (const job of jobs.values())
      if (["running", "awaiting_child_exit"].includes(job.status)) job.abort();
  });
  defs.set(
    tool.name,
    digest({
      name: tool.name,
      description: tool.description,
      parameters: tool.parameters,
    }),
  );
  pi.registerTool(tool);
  return {
    active: () => (loadProfile(state).features.specialists ? [tool.name] : []),
    allowed(name: string) {
      const t = pi.getAllTools().find((t) => t.name === name);
      return (
        defs.has(name) &&
        !!t &&
        path.resolve(t.sourceInfo.path) ===
          path.join(PACKAGE_ROOT, "extensions/chrysalis.ts") &&
        digest({
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        }) === defs.get(name)
      );
    },
  };
}
