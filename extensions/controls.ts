import {
  writerLeaseStatus,
  reconcileWriterLease,
} from "../src/execution/lease.ts";
import { spawnSync } from "node:child_process";
import { retentionPlan, applyRetention } from "../src/assistant/retention.ts";
import fs from "node:fs";
import path from "node:path";
import type {
  ExtensionAPI,
  ExtensionCommandContext,
} from "@earendil-works/pi-coding-agent";
import { defaultStateRoot, selectedContext } from "../src/storage/context.ts";
import { capabilityStatus } from "../src/assistant/catalog.ts";
import { loadProfile, assistantRoot } from "../src/assistant/profile.ts";
import { sharedBudget } from "../src/assistant/budgets.ts";
import {
  prepareDevelopment,
  developmentReview,
  promoteDevelopment,
} from "../src/app/development.ts";
import {
  inspectArtifact,
  prepareArtifactAdoption,
  adoptArtifact,
} from "../src/assistant/artifacts.ts";
import {
  confined,
  readJSON,
  PACKAGE_ROOT,
  digest,
} from "../src/platforms/filesystem.ts";
import { runnerStatus } from "../src/execution/linux.ts";

/** This dispatcher is called only from a native command, under the shared UI queue. */
export function installAssistantControls(pi: ExtensionAPI) {
  return async (
    command: string,
    tokens: string[],
    ctx: ExtensionCommandContext,
  ) => {
    if (
      ![
        "assistant-status",
        "usage",
        "develop",
        "artifact",
        "recovery",
        "retention",
        "runner-setup",
        "worker-reconcile",
      ].includes(command)
    )
      return false;
    const state = defaultStateRoot(),
      p = loadProfile(state);
    if (command === "assistant-status")
      ctx.ui.notify(JSON.stringify(capabilityStatus(state), null, 2), "info");
    else if (command === "usage")
      ctx.ui.notify(
        JSON.stringify(
          {
            ...sharedBudget(
              state,
              p.limits.calls,
              p.limits.concurrency,
            ).status(),
            accounting:
              "work reservations; unknown provider tokens are not estimated",
            main_model_included: false,
          },
          null,
          2,
        ),
        "info",
      );
    else if (command === "runner-setup") {
      if (
        !ctx.hasUI ||
        process.platform !== "linux" ||
        !process.env.TMUX ||
        tokens.length
      )
        throw Error("Runner setup requires an interactive Linux tmux session");
      if (
        !(await ctx.ui.confirm(
          "Install isolated execution prerequisites?",
          "Open a tmux setup window. The reviewed sudo installer installs Bubblewrap on Debian/Ubuntu and enables your standard systemd user manager with lingering. Enter any password only in that terminal. No vault or account data is changed.",
        ))
      )
        return true;
      const quote = (s: string) => "\'" + s.replace(/\'/g, "\'\\\'\'") + "\'";
      const installer = path.join(
        PACKAGE_ROOT,
        "Development/scripts/runner-setup.sh",
      );
      const result = spawnSync(
        "tmux",
        [
          "new-window",
          "-n",
          "chrysalis-setup",
          "sudo -- /bin/bash " +
            quote(installer) +
            '; read -r -p "Press Enter to close setup"',
        ],
        { encoding: "utf8", timeout: 5000 },
      );
      if (result.status !== 0)
        throw Error(
          "Could not open setup window; inspect the reviewed runner installer from your normal terminal",
        );
      ctx.ui.notify(
        "Finish setup in the new tmux window, return here and run /chrysalis assistant-status. Installation is not claimed complete yet.",
        "info",
      );
    } else if (command === "worker-reconcile") {
      if (!ctx.hasUI || tokens.length)
        throw Error("Worker reconciliation requires native controls");
      const lease = writerLeaseStatus(state);
      if (!lease) {
        ctx.ui.notify("No worker lease exists", "info");
        return true;
      }
      const exact = JSON.stringify(lease, null, 2);
      if ((await ctx.ui.editor("Worker lease review", exact)) !== exact)
        return true;
      if (
        await ctx.ui.confirm(
          "Reconcile this worker lease?",
          "Release only if the recorded child process has verifiably exited. Unknown startup identity remains blocked; no living worker is bypassed.",
        )
      )
        ctx.ui.notify(
          JSON.stringify(reconcileWriterLease(state, digest(lease))),
          "info",
        );
    } else if (command === "retention") {
      if (!ctx.hasUI || tokens.length)
        throw Error("Retention requires native controls without arguments");
      const plan = retentionPlan(state),
        exact = JSON.stringify(plan, null, 2);
      if (
        (await ctx.ui.editor(
          "Private retention review " + plan.digest,
          exact,
        )) !== exact
      )
        return true;
      if (
        plan.records.length &&
        (await ctx.ui.confirm(
          "Delete these exact old private artifacts and lessons?",
          "Only the listed files older than 30 days will be removed. Memory, sessions, browser accounts, settings and recovery are excluded.",
        ))
      )
        ctx.ui.notify(
          JSON.stringify(applyRetention(state, plan, plan.digest)),
          "info",
        );
    } else if (command === "develop") {
      if (!ctx.hasUI)
        throw Error("Source development requires native controls");
      const action = tokens.shift() ?? "prepare";
      if (action === "prepare") {
        if (tokens.length || !runnerStatus().available)
          throw Error(
            "Accepted Linux runner required; use develop prepare without arguments",
          );
        if (
          !(await ctx.ui.confirm(
            "Prepare a source development copy?",
            "Create a private copy of the reusable package outside the live source. Select it as the isolated workspace. Vault and credential data are excluded. Promotion later requires complete source review; no commit or push occurs.",
          ))
        )
          return true;
        const result = prepareDevelopment(state);
        pi.setActiveTools([
          ...new Set([...pi.getActiveTools(), "read", "bash", "write", "edit"]),
        ]);
        ctx.ui.notify(JSON.stringify(result), "info");
      } else if (action === "review" && tokens.length === 1) {
        const plan = await developmentReview(state, tokens[0]);
        const exact = JSON.stringify(plan, null, 2),
          viewed = await ctx.ui.editor("Source changes: " + plan.digest, exact);
        if (viewed === undefined) return true;
        if (viewed !== exact)
          throw Error("Edited review; revise the workspace and review again");
        if (
          await ctx.ui.confirm(
            "Promote these exact source changes?",
            "Replace only the displayed reusable files after checking their original revisions. Recovery bytes are retained privately. Execution is disabled until reload and a new workspace choice. Full verification is still required before publication. No Git operation occurs.",
          )
        )
          ctx.ui.notify(
            JSON.stringify(
              await promoteDevelopment(state, tokens[0], plan.digest),
            ),
            "info",
          );
      } else throw Error("Use develop prepare or develop review <id>");
    } else if (command === "artifact") {
      if (
        !ctx.hasUI ||
        tokens.length !== 2 ||
        !["inspect", "adopt"].includes(tokens[0])
      )
        throw Error(
          "Use artifact inspect <handle> or artifact adopt <handle> in native controls",
        );
      const [action, id] = tokens;
      const item = inspectArtifact(state, id);
      const text =
        JSON.stringify(item.metadata, null, 2) +
        (item.metadata.kind === "svg" || item.metadata.kind === "mermaid"
          ? "\n\n" + item.bytes.toString("utf8")
          : "\n\nPNG preview is not available in this text dialog; inspect the private artifact file before adoption.");
      const seen = await ctx.ui.editor("Private artifact " + id, text);
      if (seen === undefined) return true;
      if (seen !== text)
        throw Error("Artifact review was edited; create a new artifact");
      if (action === "adopt") {
        const runtime = selectedContext(state),
          plan = prepareArtifactAdoption(runtime, id);
        const exact = JSON.stringify(plan, null, 2);
        if (
          (await ctx.ui.editor("Original adoption " + plan.digest, exact)) !==
          exact
        )
          return true;
        if (
          await ctx.ui.confirm(
            "Copy this exact original into the vault?",
            "Copy only this image to the displayed new attachment path. This does not approve any roadmap, source record or atomic note.",
          )
        )
          ctx.ui.notify(
            JSON.stringify(adoptArtifact(runtime, id, plan.digest)),
            "info",
          );
      }
    } else {
      const root = path.join(assistantRoot(state), "runner");
      if (tokens.length)
        throw Error(
          "Recovery lists retained conflict handles; no automatic overwrite is permitted",
        );
      const records = fs.existsSync(root)
        ? fs
            .readdirSync(root)
            .filter((n) => /^[a-f0-9-]{36}\.conflict\.json$/.test(n))
            .slice(0, 100)
            .map((n) => ({
              handle: n.replace(/\.conflict\.json$/, ""),
              ...readJSON(confined(root, n)),
            }))
        : [];
      ctx.ui.notify(
        JSON.stringify(
          {
            conflicts: records,
            worker_lease: writerLeaseStatus(state),
            action:
              "Inspect the candidate and reconcile it in the selected workspace. Retry work after resolving concurrent edits; retained results never overwrite automatically.",
          },
          null,
          2,
        ),
        "info",
      );
    }
    return true;
  };
}
