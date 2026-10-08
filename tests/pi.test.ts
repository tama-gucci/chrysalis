import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import chrysalis from "../extensions/chrysalis.ts";
import { PACKAGE_ROOT, exists } from "../src/platforms/filesystem.ts";
import { externalState, selectedContext } from "../src/storage/context.ts";
import {
  DefaultResourceLoader,
  SettingsManager,
  SessionManager,
  createAgentSession,
} from "@earendil-works/pi-coding-agent";

if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
const base = path.join(
    externalState(process.env.TEST_SCRATCH),
    "pi-" + randomUUID(),
  ),
  state = path.join(base, "state"),
  vault = path.join(base, "Research Notes");
let registration: any, tool: any;
const handlers: Record<string, Function> = {},
  messages: string[] = [],
  notifications: string[] = [];
const pi: any = {
  registerTool: (value: any) => {
    tool = value;
  },
  registerCommand: (_name: string, value: any) => {
    registration = value;
  },
  on: (name: string, handler: Function) => {
    handlers[name] = handler;
  },
  setActiveTools: () => {},
  sendUserMessage: (text: string) => {
    messages.push(text);
  },
};
const ctx: any = {
  hasUI: true,
  cwd: base,
  ui: {
    input: async (title: string) =>
      title.includes("Name") ? "Research Notes" : base,
    editor: async (_title: string, prefill: string) => prefill,
    confirm: async () => false,
    notify: (text: string) => notifications.push(text),
  },
};

test("native operator onboarding reviews before writes, resumes and requires human-path confirmation", async () => {
  process.env.CHRYSALIS_STATE_ROOT = state;
  delete process.env.CHRYSALIS_VAULT_PATH;
  chrysalis(pi);
  assert(!exists(state));
  await registration.handler("onboard", ctx);
  assert(!exists(vault));
  assert.equal(messages.length, 0);
  ctx.ui.editor = async (_title: string, value: string) => value + "edited";
  ctx.ui.confirm = async () => true;
  await registration.handler("onboard", ctx);
  assert(!exists(vault));
  assert(notifications.some((n) => n.includes("edited")));
  ctx.ui.editor = async (_title: string, value: string) => value;
  await registration.handler("onboard", ctx);
  assert(exists(path.join(vault, ".chrysalis-vault.json")));
  assert.equal(selectedContext(state).vault, path.resolve(vault));
  await registration.handler("onboard", ctx);
  assert.equal(messages.length, 2);
  assert.match(messages[0], /conversational/);
  delete process.env.CHRYSALIS_STATE_ROOT;
});
test("bootstrap errors are useful; model cannot run approval or bypass life tools", async () => {
  process.env.CHRYSALIS_STATE_ROOT = path.join(base, "unconfigured-state");
  const error: any = await tool.execute("fixture", { operation: "doctor" });
  assert.equal(error.details.status, "error");
  assert.match(error.details.message, /onboard/);
  assert.equal(
    (
      await handlers.tool_call(
        { toolName: "bash", input: { command: "anything" } },
        ctx,
      )
    ).block,
    true,
  );
  assert.equal(
    (
      await handlers.tool_call(
        {
          toolName: "read",
          input: { path: path.join(PACKAGE_ROOT, "package.json") },
        },
        ctx,
      )
    ).block,
    true,
  );
  assert.equal(
    await handlers.tool_call(
      {
        toolName: "read",
        input: {
          path: path.join(PACKAGE_ROOT, "skills/chrysalis-daily/SKILL.md"),
        },
      },
      ctx,
    ),
    undefined,
  );
  assert.equal(
    (
      await tool.execute("fixture", {
        operation: "approve",
        arguments: { proposal_digest: "0".repeat(64) },
      })
    ).details.status,
    "error",
  );
  delete process.env.CHRYSALIS_STATE_ROOT;
});
test("actual Pi SDK discovers seven skills and invokes the new tool without Python", async () => {
  process.env.CHRYSALIS_STATE_ROOT = state;
  process.env.CHRYSALIS_VAULT_PATH = vault;
  delete process.env.CHRYSALIS_PYTHON;
  const cwd = path.join(base, "cwd"),
    agentDir = path.join(base, "profile");
  fs.mkdirSync(cwd, { recursive: true });
  fs.mkdirSync(agentDir, { recursive: true });
  const settings = SettingsManager.inMemory({ packages: [PACKAGE_ROOT] }),
    loader = new DefaultResourceLoader({
      cwd,
      agentDir,
      settingsManager: settings,
      noContextFiles: true,
      disabledBuiltinExtensions: ["mcp", "codemode"],
    });
  await loader.reload();
  assert.equal(loader.getSkills().skills.length, 7);
  assert.deepEqual(loader.getExtensions().errors, []);
  const { session } = await createAgentSession({
    cwd,
    agentDir,
    resourceLoader: loader,
    settingsManager: settings,
    sessionManager: SessionManager.inMemory(cwd),
    tools: ["read", "chrysalis_operation"],
  });
  try {
    const usage = {
      input: 0,
      output: 0,
      cacheRead: 0,
      cacheWrite: 0,
      totalTokens: 0,
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
    };
    session.agent.state.messages.push({
      role: "assistant",
      content: [
        {
          type: "toolCall",
          id: "synthetic-parent",
          name: "chrysalis_operation",
          arguments: { operation: "doctor" },
        },
      ],
      api: "openai-responses",
      provider: "synthetic",
      model: "fixture",
      usage,
      stopReason: "toolUse",
      timestamp: Date.now(),
    });
    const context = (session as any)._extensionRunner.createToolContext(
        "synthetic-parent",
        undefined,
      ),
      out = await context.executeTool("chrysalis_operation", {
        operation: "doctor",
        arguments: {},
      }),
      actual = out.result ?? out;
    assert.equal(actual.details.status, "ok", JSON.stringify(actual));
    const read = await context.executeTool("read", {
      path: path.join(PACKAGE_ROOT, "skills/chrysalis-daily/SKILL.md"),
    });
    assert(
      (read.result ?? read).content.some(
        (c) => c.type === "text" && c.text.includes("chrysalis_operation"),
      ),
    );
    const denied = await context.executeTool("read", {
      path: path.join(vault, "System/Memory.md"),
    });
    assert.match(JSON.stringify(denied), /reviewed operations|blocked/i);
  } finally {
    session.dispose();
    delete process.env.CHRYSALIS_STATE_ROOT;
    delete process.env.CHRYSALIS_VAULT_PATH;
  }
});

test("unapproved setup can restart with corrected folder and initial zone", async () => {
  const localState = path.join(base, "restart-state"),
    oldVault = path.join(base, "Declined vault"),
    newVault = path.join(base, "Corrected vault");
  process.env.CHRYSALIS_STATE_ROOT = localState;
  delete process.env.CHRYSALIS_VAULT_PATH;
  ctx.ui.input = async (title: string) =>
    title.includes("Name") ? "Declined vault" : base;
  ctx.ui.confirm = async () => false;
  ctx.ui.editor = async (_title: string, value: string) => value;
  await registration.handler("onboard", ctx);
  const pointer = JSON.parse(
    fs.readFileSync(path.join(localState, "pending-setup.json"), "utf8"),
  );
  assert(!exists(oldVault));
  ctx.ui.input = async (title: string) =>
    title.includes("Name") ? "Corrected vault" : base;
  ctx.ui.confirm = async () => true;
  await registration.handler("onboard --restart --zone Asia/Kathmandu", ctx);
  assert(!exists(oldVault));
  assert(exists(path.join(newVault, ".chrysalis-vault.json")));
  assert.equal(selectedContext(localState).vault, path.resolve(newVault));
  const memory = fs.readFileSync(
    path.join(newVault, "System/Memory.md"),
    "utf8",
  );
  assert.match(memory, /Asia\/Kat(?:h)?mandu/);
  await registration.handler("approve " + pointer.proposal_digest, ctx);
  assert(!exists(oldVault));
  assert(notifications.some((n) => n.includes("replaced")));
  delete process.env.CHRYSALIS_STATE_ROOT;
});
