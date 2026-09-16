# Set up background development: a beginner's guide

This guide shows you how to have Codex improve Chrysalis while you spend your time using your personal vault.

**You will mostly copy messages into a chat. Codex will do the coding, testing, and setup work.** Follow the steps in order and check the result at the end of each one. You can pause between steps and return later.

The first setup requires some development: Chrysalis has a backlog and instructions, but the complete automatic workflow still needs to be built. Creating a scheduled chat alone would not finish that work.

## What you are setting up

Once setup is complete, one daily job will:

1. Pick one small improvement.
2. Make the change in a separate development folder.
3. Test it and get a separate code review.
4. Save accepted work and report the result.

You will review a short summary. Installing those improvements into your personal vault is a separate weekly step, covered below.

Three terms used in the app:

| Term | Plain meaning |
| --- | --- |
| Project | The Chrysalis source folder containing the code |
| Worktree | A separate working folder where the agent can make changes |
| Commit | A saved checkpoint in the project's Git history |

The initial setup keeps development on your computer. Connecting automatic checks to GitHub can come later.

## Step 1 — Open the Chrysalis development project

**You do this:**

1. Open the desktop app you use for Codex.
2. Select Codex and open your existing Chrysalis development project.
3. Start a chat in that project. Keep it open for Steps 1–4.
4. Let any other agent currently editing that same project finish first.

The correct folder contains **AGENTS.md**, **Development**, and **apps**. The personal vault containing your daily notes is a different folder.

**Copy this into the chat:**

```text
Help me set up background development for Chrysalis. I have limited development experience, so explain results simply and handle the technical work yourself.

First, read this checkout's shared engineering instructions and check the actual Git state. Confirm that this is the source repository. Tell me whether there are changes that need preserving and whether the required development tools are available.

For this first step, inspect and report only. Use the source repository and synthetic test data for the setup.
```

**This step is done when:** Codex confirms the correct project and explains any missing tools. If tools are missing, say, “Please set up the missing development tools and verify them.” Follow any specific installation or sign-in instructions it provides.

Look for **Scheduled** in the desktop app's sidebar. That is where you will check the daily job later. If you use Codex only in a terminal or editor extension, see [If Scheduled is missing](#if-scheduled-is-missing) below.

## Step 2 — Ask Codex to repair the starting version

The source review found five failing tests. Have Codex recheck and fix those before giving it recurring work.

**Copy this into the same chat:**

```text
Complete the starting-version repair described as B00 in Development/BACKLOG.md.

Preserve existing work. Recheck and fix the task-schema and mailbox-contract failures from Development/REVIEW-2026-09-15.md. Run the required tests and privacy checks.

Use a separate review agent or review invocation to check the exact changes. Address its findings. After review and /audit-dev pass, save the intended source changes as a local Git commit and update Development/HANDOFF.md.

Keep this work local to development. Finish by telling me whether the tests pass, whether review passed, and the saved commit ID. If anything prevents completion, explain the specific problem.
```

**This step is done when:** Codex reports passing required checks, a completed separate review, and a commit ID. A commit ID looks like a short string of letters and numbers.

If it reports a failure, reply:

```text
Please resolve that failure and repeat the affected checks. Tell me when this step is actually complete.
```

A report that the agent “finished” is not enough if its checks still fail.

## Step 3 — Ask Codex to make the checks automatic

You should not have to remember a list of test commands.

**Copy this into the same chat:**

```text
Complete the local-check milestone of B01 in Development/BACKLOG.md.

Create and verify one command that runs the required development checks and reports failures clearly. Include the candidate privacy checks. Use the existing setup tools where appropriate.

Test it in a fresh development working folder. Verify that a failing required check produces a failed overall result. Arrange a separate review and save the reviewed result after /audit-dev.

Keep hosted GitHub checks recorded as pending if they have not actually run. Give me the exact local check command and a plain-language summary of its result.
```

**This step is done when:** There is one working check command, it passes on the repaired source, and the agent has demonstrated that it also detects failure.

You do not need to type that command each day. The next step connects it to the background job.

## Step 4 — Ask Codex to build the daily routine

This is the largest setup step. The agent needs to build the missing connection between choosing work, making changes, checking them, and saving the result.

**Copy this into the same chat:**

```text
Build the development routine described in B02 in Development/BACKLOG.md, using its verified local-check prerequisite.

Start with one worker and one small ready item at a time. Use isolated worktrees, durable task ownership, and saved progress so repeated or interrupted runs cannot duplicate work.

Connect implementation, actual validation, a separate review invocation, and at most two repair attempts. Accepted changes may be integrated into a dedicated local development branch after review and /audit-dev. Record the exact integrated revision. Keep publication and personal-vault installation outside this daily routine.

Implement a 45-minute maximum per run. Explain how usage is measured and ask for any spending limit that is genuinely needed before enabling paid execution. Preserve unfinished work when a limit is reached.

Test startup, repeat invocation, interruption recovery, and the handoff to review. Configure and verify worktree setup and the specific tool permissions the routine needs.

Save the exact operating instructions in Development/AUTOMATION-RUN.md, adding its explicit public allowlist entry. Keep machine-specific configuration private. Include how to run once, schedule the tested entry point, pause, resume, and find results.

Leave recurring execution off. Report which parts you actually built and verified, and what remains incomplete.
```

**This step is done when:** Codex has built and tested the routine and created **Development/AUTOMATION-RUN.md** with real operating instructions.

That file does **not** exist just because this guide names it. Codex creates it during this step. The existing builder/reviewer prompt templates alone are not the complete routine.

If Codex gives you another design document instead of doing the work, reply:

```text
Please implement and test the routine you described. I need a working one-run operation and its operating instructions. Identify any part that you cannot implement with the available tools.
```

## Step 5 — Try one complete run while you are present

**You do this:**

1. Keep the development computer awake.
2. Start a new Codex chat in the same project.
3. Paste the message below. Let the tested operating instructions choose the working folder.

```text
Read Development/AUTOMATION-RUN.md and execute one complete development run now, using the configured routine.

Choose one ready bounded repair from the backlog. Carry it through implementation, checks, separate review, and the configured local integration step.

Do not enable recurrence during this trial. Show me what changed, whether checks and review passed, where the result was saved, and whether any part still needs my attention.
```

**This step is done when:** One actual item completes the full process and its saved code can be identified. A list of suggestions, an unreviewed patch, or a run that required repeated manual command forwarding does not complete the trial.

If the routine fails, ask Codex to repair the setup and repeat the trial. This is the time to resolve tool permissions and missing authentication.

## Step 6 — Put the tested routine on a daily schedule

Choose a time when your development computer is usually awake. **9:00 AM local time** is an example; replace it below if needed.

**Copy this into the desktop project chat:**

```text
The manual Chrysalis development trial has passed. Create one daily scheduled task named "Chrysalis development" at 9:00 AM in my local timezone.

Use the exact tested entry point and operating instructions in Development/AUTOMATION-RUN.md. Use this source project and the worktree arrangement verified during setup.

Run at most one development item at a time, using the existing checks, separate review, limits, and local integration policy. Finish with a short result summary.

Verify that the task was actually created. Tell me its project, next run time, and how to pause it. If your current tools cannot create it, say so and give me the exact prompt and settings to enter in Scheduled.
```

If the agent cannot create the task directly, open **Scheduled**, use its task-creation control, and enter the settings and exact prompt it supplies. The scheduling choice should match the arrangement tested in Step 5; changing it to a different folder or mode can break the routine.

**This step is done when:** The task appears in Scheduled with the correct project and a next run time.

Desktop schedules can work in local projects/worktrees. Keep the computer on and the desktop app running. Web chats cannot directly operate on your local folder; the CLI and editor extension do not provide the Scheduled screen. [Official scheduling documentation](https://learn.chatgpt.com/docs/automations).

## Step 7 — Check the first automatic run

After the scheduled time, open the task in Scheduled and inspect its latest result.

A useful result might say:

> **Improved:** Pending offline commands are preserved when a queue file is damaged.\
> **Checks:** Passed.\
> **Review:** Passed.\
> **Saved:** A named development commit.\
> **Decision needed:** None.

This is an example, not a report of completed work.

**Setup is working when:** A run started at its scheduled time, completed useful work, and saved a verified result without you directing its individual actions.

A blocked result is still useful if it clearly identifies a real missing dependency. Repeated empty runs or the same unexplained failure mean the setup needs attention.

## Step 8 — Bring completed improvements into your personal installation

The daily job prepares and saves development changes. A release installs selected changes into the copy of Chrysalis you use for your life goals.

Start with a weekly release review. In the development chat, paste:

```text
Prepare this week's Chrysalis release from the reviewed development changes.

Explain the practical improvements simply. Build the needed artifacts, run the required checks, and rehearse the update and rollback with synthetic data.

Identify the personal installation from an already verified configuration, or ask me for its location if it is unknown. Preview the update against that exact target and explain any conflicts or additional app/service steps.

Present the concrete release and preview for approval before changing the personal installation.
```

When the preview is satisfactory, you can reply:

```text
Apply the exact release you just previewed to that confirmed installation. Verify the affected workflow and report the result.
```

**This step is done when:** Codex identifies the installed version and reports the result of checking the affected workflow in that installation.

Initially, that keeps release decisions in one short weekly conversation. After several reliable releases, you can ask Codex to automate compatible updates under a defined release policy.

## If something goes wrong

| What you see | What to do |
| --- | --- |
| A step ends with failed checks | Paste the failure back and ask the agent to resolve that step |
| A permission or sign-in request | Ask what specific operation needs it; complete the relevant setup |
| The job keeps selecting the same item | Pause it and ask Codex to repair task ownership/progress tracking |
| It says work is saved, but gives no result location | Ask for the actual saved commit and verification record |
| The scheduled time passes without a run | Check the app, computer, next-run timezone, and task status |
| You want development to stop temporarily | Use the pause instructions from Step 6; ask how to stop an active run separately |

### If Scheduled is missing

Steps 1–5 can still be completed in your existing coding tool. Before Step 6, paste:

```text
My coding interface does not have a Scheduled screen. Help me schedule the tested routine from Development/AUTOMATION-RUN.md on this development computer.

Inspect what is actually available and choose one supported local scheduling method. Prepare and test it before enabling recurrence. Give me simple start, pause, resume, and status instructions. Explain whether the app must remain open and how the computer's sleep behavior affects it.
```

That alternative needs its own verified setup; this guide does not claim it is already installed.

## Your first action

Open the Chrysalis source project and paste the message in **Step 1**. Complete one step at a time.

The detailed design is retained in [the engineering reference](BACKGROUND-DEVELOPMENT-REFERENCE.md). The agent can use [the backlog](BACKLOG.md) and [source review](REVIEW-2026-09-15.md) for technical details while you follow this guide.
