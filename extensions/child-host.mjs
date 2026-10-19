import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
// The child uses the fixed parent stream, so provider keys and ambient auth variables are unnecessary.
const inherited = new Set([
  "PATH",
  "HOME",
  "USER",
  "LOGNAME",
  "SHELL",
  "LANG",
  "LC_ALL",
  "TERM",
  "TZ",
  "TMPDIR",
  "TMP",
  "TEMP",
  "TMUX",
  "TMUX_PANE",
  "NODE_PATH",
  "CHRYSALIS_STATE_ROOT",
  "CHRYSALIS_CHILD_TASK",
  "CHRYSALIS_DEPENDENCIES_ROOT",
  "CHRYSALIS_PI_ROOT",
  "CHRYSALIS_EXECUTION_CONFIG",
  "PI_CODING_AGENT_DIR",
]);
for (const key of Object.keys(process.env))
  if (!inherited.has(key) && !key.startsWith("PI_SUBAGENT_"))
    delete process.env[key];
const {
  DefaultResourceLoader,
  SettingsManager,
  SessionManager,
  createAgentSession,
  getAgentDir,
} = await import("@earendil-works/pi-coding-agent");
import { defaultStateRoot, externalState } from "../src/storage/context.ts";
import { assistantRoot, loadProfile } from "../src/assistant/profile.ts";
import {
  PACKAGE_ROOT,
  rejectRedirects,
  inside,
  digest,
  raw,
  sha256,
} from "../src/platforms/filesystem.ts";

/** Minimal programmatic host: extension errors are fatal before any model request. */
const state = defaultStateRoot(),
  file = process.env.CHRYSALIS_CHILD_TASK;
if (
  !file ||
  !path.isAbsolute(file) ||
  !inside(rejectRedirects(file), path.join(assistantRoot(state), "tasks"))
)
  throw Error("Missing bounded child envelope");
const task = JSON.parse(raw(file).toString("utf8")),
  profile = loadProfile(state);
if (
  task.version !== 1 ||
  digest(profile) !== task.profileDigest ||
  typeof task.brief !== "string" ||
  task.brief.length > profile.limits.inputChars
)
  throw Error("Child policy changed or brief invalid");
if (
  sha256(raw(path.join(PACKAGE_ROOT, "extensions/child.ts"))) !==
    task.childSha256 ||
  sha256(raw(task.doneExtension)) !== task.doneSha256
)
  throw Error("Child extension bytes changed");

const sessionFile = process.env.PI_SUBAGENT_SESSION;
const sessionsRoot = path.join(
  path.dirname(getAgentDir()),
  "subagent-sessions",
);
if (
  !sessionFile ||
  !path.isAbsolute(sessionFile) ||
  !inside(rejectRedirects(sessionFile), sessionsRoot)
)
  throw Error("Child session path is not managed");
externalState(path.dirname(sessionFile));
const cwd = path.dirname(file),
  agentDir = path.join(cwd, "host"),
  settings = SettingsManager.inMemory({ packages: [] });
let registry;
const loader = new DefaultResourceLoader({
  extensionFactories: [
    {
      name: "chrysalis-child-route",
      factory: (pi) =>
        pi.on("session_start", (_event, ctx) => {
          registry = ctx.modelRegistry;
        }),
    },
  ],
  cwd,
  agentDir,
  settingsManager: settings,
  noContextFiles: true,
  noSkills: true,
  noExtensions: true,
  additionalExtensionPaths: [
    ...(task.runtimeRoute
      ? [path.join(PACKAGE_ROOT, "extensions/provider-child.ts")]
      : []),
    path.join(PACKAGE_ROOT, "extensions/child.ts"),
    task.doneExtension,
  ],
});
fs.mkdirSync(agentDir, { recursive: true, mode: 0o700 });
await loader.reload();
if (loader.getExtensions().errors.length)
  throw Error("Required child extensions failed to load; no model started");
if (!task.runtimeRoute)
  throw Error("Child has no fixed parent model runtime; no fallback");
const { session } = await createAgentSession({
  cwd,
  agentDir,
  settingsManager: settings,
  resourceLoader: loader,
  sessionManager: SessionManager.open(sessionFile),
});
let finished = false,
  policyFailure = false;
const started = Date.now();
const hardStop = setTimeout(() => {
  void session.abort();
  setTimeout(() => process.exit(1), 1000).unref();
}, profile.limits.timeoutSeconds * 1000);
try {
  const errors = [];
  await session.bindExtensions({
    onError: (e) => {
      errors.push(e);
      policyFailure = true;
      void session.abort();
    },
    shutdownHandler: () => {
      finished = true;
      void session.abort();
    },
  });
  if (
    errors.length ||
    !session.getActiveToolNames().includes("subagent_done") ||
    !session.getActiveToolNames().includes("read")
  )
    throw Error("Child policy did not bind; no model started");
  const model = registry.find(task.route.provider, task.route.model);
  if (!model) throw Error("Selected child model unavailable; no fallback");
  await session.setModel(model);
  session.setThinkingLevel(task.route.thinking);
  if (digest(loadProfile(state)) !== task.profileDigest)
    throw Error("Child policy changed before prompt");
  await session.prompt(task.brief);
  // The pinned completion extension may send a bounded follow-up after agent_end.
  while (
    !finished &&
    !policyFailure &&
    Date.now() - started < profile.limits.timeoutSeconds * 1000
  )
    await new Promise((r) => setTimeout(r, 100));
  if (!finished) process.exitCode = 1;
} finally {
  clearTimeout(hardStop);
  session.dispose();
}
