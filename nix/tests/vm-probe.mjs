// Disposable VM harness. Native approvals here authorize synthetic fixture state only.
// No provider credentials, personal vaults or real disks are accepted.
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import os from "node:os";
import { spawnSync } from "node:child_process";
import { createRequire } from "node:module";
const root = fs.realpathSync("/etc/chrysalis/package");
const require = createRequire(path.join(root, "package.json"));
const state = await import(path.join(root, "src/system/state.ts"));
const native = await import(path.join(root, "src/system/native.ts"));
const c = state.loadSystemConfig("/etc/chrysalis/system.json");
assert(c);
const phase = process.argv[2];
const key = "fixture-encryption-2026",
  password = "fixture-account-2026";

if (phase === "install") {
  assert.equal(c.mode, "installer");
  const disks = await native.diskInventory(c);
  const disk = disks.find((d) => d.serial === "chrysalis-target");
  assert(disk, "Only the explicitly named disposable target is permitted");
  // A persisted pre-format interruption may never trigger an implicit reformat.
  const interrupted = state.approveSystem(
    c,
    "Disposable interruption test",
    "vm-native",
    disk,
  );
  await state.recordSystem(c, interrupted.id, "installing", {
    source: state.configurationIdentity(c.configuration),
  });
  await native.reconcileInstalled(c);
  await assert.rejects(native.installTarget(c), /interrupted/);
  await state.recordSystem(c, interrupted.id, "closed", {
    test: "no automatic retry",
  });
  state.approveSystem(
    c,
    "Install the named disposable acceptance disk",
    "vm-native",
    disk,
    undefined,
    undefined,
    { user: "chrysalis", name: "acceptance", zone: "Etc/UTC" },
  );
  await native.saveInstallSecrets(c, key, password);
  await native.seedTarget(
    c,
    { user: "chrysalis", name: "acceptance", zone: "Etc/UTC" },
    disk,
  );
  fs.appendFileSync(path.join(c.configuration, "host.nix"), "\n");
  const host = path.join(c.configuration, "host.nix");
  fs.writeFileSync(
    host,
    fs
      .readFileSync(host, "utf8")
      .replace(
        "  system.stateVersion",
        '  boot.kernelParams = [ "console=tty0" "console=ttyS0,115200" ];\n  system.stateVersion',
      ),
  );
  await native.checked(c.commands.nix, ["flake", "lock", c.configuration], {
    timeout: 600000,
  });
  await native.installTarget(c);
  assert.equal(state.currentOperation(c).phase, "installed");
  console.log(JSON.stringify({ stage: "installed-pending-handoff" }));
} else if (phase === "partial-handoff") {
  assert.equal(c.mode, "installer");
  assert.equal(state.currentOperation(c).phase, "installed");
  await native.saveInstallSecrets(c, key, password);
  const fixture = path.join(c.state, "handoff-acceptance-checkpoint");
  fs.writeFileSync(fixture, "before restart");
  const script = "/run/chrysalis/interrupt-handoff.mjs";
  // Kill the actual helper after a durable target copy and before its final marker.
  // This hook exists only in this disposable acceptance process.
  fs.writeFileSync(
    script,
    [
      'import fs from "node:fs";',
      "const state = await import(" +
        JSON.stringify(path.join(root, "src/system/state.ts")) +
        ");",
      "const native = await import(" +
        JSON.stringify(path.join(root, "src/system/native.ts")) +
        ");",
      "const original = fs.chownSync;",
      "fs.chownSync = (file, ...args) => { original(file, ...args); if (file === " +
        JSON.stringify("/mnt" + fixture) +
        ') process.kill(process.pid, "SIGKILL"); };',
      'await native.handoffTarget(state.loadSystemConfig("/etc/chrysalis/system.json"));',
      'throw Error("Handoff interruption did not fire");',
    ].join("\n"),
  );
  const interrupted = spawnSync(
    process.execPath,
    [...process.execArgv, script],
    { stdio: "inherit" },
  );
  assert.equal(interrupted.signal, "SIGKILL");
  assert.equal(fs.readFileSync("/mnt" + fixture, "utf8"), "before restart");
  assert(!fs.existsSync("/mnt/var/lib/chrysalis/install.json"));
  console.log(
    JSON.stringify({ stage: "handoff-interrupted-after-durable-copy" }),
  );
} else if (phase === "handoff") {
  assert.equal(c.mode, "installer");
  assert.equal(state.currentOperation(c).phase, "installed");
  await native.saveInstallSecrets(c, key, password);
  fs.writeFileSync(
    path.join(c.state, "handoff-acceptance-checkpoint"),
    "continued after restart",
  );
  const agent = "/run/chrysalis/acceptance-agent";
  fs.mkdirSync(agent, { recursive: true, mode: 0o700 });
  fs.writeFileSync(
    path.join(agent, "auth.json"),
    JSON.stringify({
      "acceptance-fixture": {
        type: "api_key",
        key: "vm-only-nonworking-canary",
      },
    }),
    { mode: 0o600 },
  );
  fs.writeFileSync(
    path.join(agent, "settings.json"),
    JSON.stringify({ quietStartup: true }),
    { mode: 0o600 },
  );
  console.log(JSON.stringify(await native.handoffTarget(c, agent)));
  fs.writeFileSync(
    path.join(agent, "settings.json"),
    JSON.stringify({ quietStartup: false }),
  );
  assert.equal((await native.handoffTarget(c, agent)).unchanged, true);
} else if (phase === "installed") {
  assert.equal(c.mode, "installed");
  const profile = path.join(os.homedir(), ".pi/agent");
  for (const file of ["auth.json", "settings.json"]) {
    const stat = fs.lstatSync(path.join(profile, file));
    assert(!stat.isSymbolicLink());
    assert.equal(stat.uid, process.getuid());
    assert.equal(stat.mode & 0o777, 0o600);
  }
  assert.equal(fs.statSync(os.homedir()).uid, process.getuid());
  assert.equal(
    JSON.parse(fs.readFileSync(path.join(profile, "settings.json"), "utf8"))
      .quietStartup,
    true,
  );
  assert.equal(
    JSON.parse(fs.readFileSync(path.join(profile, "auth.json"), "utf8"))[
      "acceptance-fixture"
    ].key,
    "vm-only-nonworking-canary",
  );
  assert.equal(
    fs.readFileSync(
      path.join(c.state, "handoff-acceptance-checkpoint"),
      "utf8",
    ),
    "continued after restart",
  );
  assert.equal(
    fs
      .readdirSync(state.systemRoot(c))
      .filter((name) => /^handoff-[a-f0-9-]{36}\.json$/.test(name)).length,
    0,
    "USB transfer journals must stay out of installed runtime state",
  );
  const reconciled = await native.reconcileInstalled(c);
  assert.equal(reconciled.status, "verified", JSON.stringify(reconciled));
  const onboarding = await import(path.join(root, "src/app/onboarding.ts"));
  const vault = path.join(os.homedir(), "Acceptance Vault");
  const plan = onboarding.prepareOnboarding({
    vault,
    state: c.state,
    timezone: "Etc/UTC",
  });
  onboarding.approveSetup(
    c.state,
    plan.proposal_digest,
    "Native disposable VM harness approval",
  );
  assert.equal(
    (await onboarding.applySetup(c.state, plan.proposal_digest)).status,
    "ready_to_open",
  );
  const first = await state.projectSystemLedger(c, vault);
  assert(first.appended > 0);
  assert.equal((await state.projectSystemLedger(c, vault)).appended, 0);
  fs.writeFileSync(path.join(c.state, "acceptance-vault"), vault);
  console.log(JSON.stringify({ stage: "boot-verified-vault-ready", vault }));
} else if (phase === "operations") {
  assert.equal(c.mode, "installed");
  const { Client } = await import(
    require.resolve("@modelcontextprotocol/sdk/client/index.js")
  );
  const { StdioClientTransport } = await import(
    require.resolve("@modelcontextprotocol/sdk/client/stdio.js")
  );
  const client = new Client({
    name: "chrysalis-disposable-acceptance",
    version: "1",
  });
  const transport = new StdioClientTransport({
    command: c.commands.nixAgent,
    cwd: c.configuration,
    env: {
      ...process.env,
      NIX_AGENT_FLAKE: c.configuration + "#" + c.host,
      XDG_STATE_HOME: path.join(c.state, "backend"),
    },
  });
  await client.connect(transport);
  try {
    const call = async (name, args) => {
      const result = await client.callTool({ name, arguments: args });
      assert(!result.isError, JSON.stringify(result));
      if (result.structuredContent?.status) return result.structuredContent;
      for (const part of result.content ?? [])
        if (part.type === "text") {
          try {
            const parsed = JSON.parse(part.text);
            if (parsed.status) return parsed;
          } catch {}
        }
      throw Error("Missing structured backend evidence");
    };
    const vault = fs.readFileSync(
      path.join(c.state, "acceptance-vault"),
      "utf8",
    );
    const host = path.join(c.configuration, "host.nix"),
      before = fs.readFileSync(host, "utf8");
    const recovery = native.observedGeneration();
    assert(recovery);
    let op = state.approveSystem(
      c,
      "Create a disposable system marker",
      "vm-native",
      undefined,
      vault,
      recovery,
    );
    fs.writeFileSync(
      host,
      before.replace(
        "  system.stateVersion",
        '  environment.etc."chrysalis-acceptance".text = "verified";\n  system.stateVersion',
      ),
    );
    const source = state.configurationIdentity(c.configuration);
    await state.recordSystem(c, op.id, "building", { source });
    const diff = await call("diff", {
      flake_uri: c.configuration + "#" + c.host,
      mode: "nixos",
    });
    assert.equal(diff.status, "ok", JSON.stringify(diff));
    assert(diff.store_path?.startsWith("/nix/store/"));
    await state.recordSystem(c, op.id, "built", {
      source,
      storePath: diff.store_path,
    });
    await state.recordSystem(c, op.id, "activating", {
      source,
      expectedRunning: diff.store_path,
      before: native.runtimeObservation(),
    });
    const activated = await call("switch", {
      flake_uri: c.configuration + "#" + c.host,
      mode: "nixos",
    });
    assert(
      ["ok", "degraded"].includes(activated.status),
      JSON.stringify(activated),
    );
    assert.equal(native.runtimeObservation().running, diff.store_path);
    assert.equal(
      fs.readFileSync("/etc/chrysalis-acceptance", "utf8"),
      "verified",
    );
    await state.recordSystem(
      c,
      op.id,
      activated.status === "ok" ? "verified" : "degraded",
      {
        source,
        ...native.runtimeObservation(),
        health: activated.summary?.health ?? null,
      },
    );
    await state.projectSystemLedger(c, vault);
    if (state.currentOperation(c).phase === "degraded")
      await state.recordSystem(c, op.id, "closed", {
        test: "explicit recovery follows",
      });
    op = state.approveSystem(
      c,
      "Recover the exact pre-change generation",
      "vm-native",
      undefined,
      vault,
      recovery,
    );
    await state.recordSystem(c, op.id, "activating", {
      expectedRunning: recovery.path,
    });
    const rolled = await call("generations", {
      action: "rollback",
      mode: "nixos",
      generation: recovery.generation,
    });
    assert.equal(rolled.status, "ok", JSON.stringify(rolled));
    assert.equal(native.runtimeObservation().running, recovery.path);
    assert(!fs.existsSync("/etc/chrysalis-acceptance"));
    await state.recordSystem(c, op.id, "verified", {
      ...native.runtimeObservation(),
      generation: recovery.generation,
    });
    await state.projectSystemLedger(c, vault);
    op = state.approveSystem(
      c,
      "Exercise a failed disposable build",
      "vm-native",
      undefined,
      vault,
      recovery,
    );
    fs.writeFileSync(host, 'throw "intentional disposable build failure"\n');
    const failed = await call("diff", {
      flake_uri: c.configuration + "#" + c.host,
      mode: "nixos",
    });
    assert.equal(failed.status, "failed", JSON.stringify(failed));
    await state.recordSystem(c, op.id, "build-failed", {
      status: failed.status,
    });
    fs.writeFileSync(host, before);
    assert.equal(native.runtimeObservation().running, recovery.path);
    await state.recordSystem(c, op.id, "closed", {
      test: "failed build preserved running generation",
    });
    await state.projectSystemLedger(c, vault);
    assert.equal((await state.projectSystemLedger(c, vault)).appended, 0);
    console.log(
      JSON.stringify({ stage: "activation-recovery-failure-ledger-verified" }),
    );
  } finally {
    await client.close();
  }
} else throw Error("Unknown disposable VM phase");
