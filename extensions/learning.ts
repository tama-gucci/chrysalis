import path from "node:path";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { PACKAGE_ROOT, digest } from "../src/platforms/filesystem.ts";
import { defaultStateRoot } from "../src/storage/context.ts";
import { loadProfile } from "../src/assistant/profile.ts";
import { assistantUI } from "../src/assistant/ui.ts";
import { validateQuiz, shuffled, gradeQuiz } from "../src/learning/quiz.ts";
import { captureLesson } from "../src/learning/capture.ts";
export function installLearning(pi: ExtensionAPI) {
  const defs = new Map<string, string>();
  let topic = "",
    entries: unknown[] = [];
  const append = (entry: unknown) => {
    entries.push(entry);
    while (
      entries.length > 100 ||
      Buffer.byteLength(JSON.stringify(entries)) > 220000
    )
      entries.shift();
  };
  function register(t: any) {
    defs.set(
      t.name,
      digest({
        name: t.name,
        description: t.description,
        parameters: t.parameters,
      }),
    );
    pi.registerTool(t);
  }
  register({
    name: "chrysalis_question",
    label: "Questions",
    description:
      "Ask one to three ready independent questions with optional choices, free text, skip and defer. Answers are conversation context only. Never request credentials or interpret a reply as vault approval.",
    parameters: Type.Object({
      questions: Type.Array(
        Type.Object({
          question: Type.String(),
          options: Type.Optional(Type.Array(Type.String())),
        }),
        { minItems: 1, maxItems: 3 },
      ),
    }),
    async execute(_id: string, p: any, _signal: any, _update: any, ctx: any) {
      if (!ctx.hasUI) throw Error("Questions require native user input");
      const replies = await assistantUI.run(async () => {
        const answers: any[] = [];
        for (const [index, q] of p.questions.entries()) {
          if (
            q.question.length > 3000 ||
            (q.options?.length ?? 0) > 5 ||
            q.options?.some(
              (o: any) => typeof o !== "string" || o.length > 1000,
            )
          )
            throw Error("Question limit");
          const label = "Q" + (index + 1) + ": " + q.question;
          let answer: string | undefined,
            status = "answered";
          if (q.options?.length) {
            const choices = q.options.map(
              (o: string, i: number) => "[" + (i + 1) + "] " + o,
            );
            answer = await ctx.ui.select(label, [
              ...choices,
              "Write my own answer",
              "Skip",
              "Later",
            ]);
            if (answer === "Write my own answer")
              answer = await ctx.ui.input(label);
            else {
              const found = choices.indexOf(answer ?? "");
              if (found >= 0) answer = q.options[found];
              else if (answer === "Skip") status = "skipped";
              else if (answer === "Later") status = "deferred";
            }
          } else answer = await ctx.ui.input(label + " (cancel to skip)");
          if (answer && answer.length > 4000) throw Error("Answer limit");
          answers.push({
            question: q.question,
            status: !answer ? "skipped" : status,
            answer: answer ?? null,
            authority: "conversation_only",
          });
        }
        return answers;
      });
      return {
        content: [{ type: "text", text: JSON.stringify(replies) }],
        details: { authority: "conversation_only" },
      };
    },
  });
  register({
    name: "chrysalis_quiz",
    label: "Learning check",
    description:
      "Offer an optional single/multiple-choice learning check, with skip and I-don't-know. Answers inform teaching only and cannot approve vault writes. The supplied key is an authored claim, not independently verified truth.",
    parameters: Type.Object({
      question: Type.String(),
      multiple: Type.Boolean(),
      options: Type.Array(
        Type.Object({
          id: Type.String(),
          label: Type.String(),
          correct: Type.Boolean(),
        }),
      ),
      explanation: Type.String(),
    }),
    async execute(_id: string, p: any, _signal: any, _update: any, ctx: any) {
      const q = validateQuiz(p);
      if (!ctx.hasUI) throw Error("Quiz requires interactive user input");
      const result = await assistantUI.run(async () => {
        const options = shuffled(q.options),
          selected: string[] = [];
        for (;;) {
          const labels = options
            .filter((o) => !selected.includes(o.id))
            .map((o) => "[" + o.id + "] " + o.label);
          const choices = [
            ...labels,
            ...(q.multiple && selected.length ? ["Finish selection"] : []),
            "I don't know",
            "Skip",
          ];
          const answer = await ctx.ui.select(
            q.question +
              (selected.length ? "\nSelected: " + selected.join(", ") : ""),
            choices,
          );
          if (!answer || answer === "Skip") return gradeQuiz(q, null);
          if (answer === "I don't know") return gradeQuiz(q, []);
          if (answer === "Finish selection") break;
          const i = choices.indexOf(answer);
          const option = options.filter((o) => !selected.includes(o.id))[i];
          if (!option) throw Error("Quiz response changed");
          selected.push(option.id);
          if (!q.multiple || selected.length === options.length) break;
        }
        const graded = gradeQuiz(q, selected);
        ctx.ui.notify(q.explanation, "info");
        return graded;
      });
      if (topic) {
        append({ quiz: q, response: result });
      }
      return {
        content: [{ type: "text", text: JSON.stringify(result) }],
        details: result,
      };
    },
  });
  register({
    name: "chrysalis_lesson",
    label: "Lesson",
    description:
      "Begin or finish a focused lesson. Private capture occurs only if enabled in native settings. Keeping durable lesson/project/atomic-note records requires separate native review.",
    parameters: Type.Object({
      action: Type.Union([Type.Literal("begin"), Type.Literal("finish")]),
      topic: Type.Optional(Type.String()),
    }),
    async execute(_id: string, p: any) {
      if (p.action === "begin") {
        if (!p.topic || p.topic.length > 500)
          throw Error("Choose a short lesson topic");
        topic = p.topic;
        entries = [];
        return {
          content: [
            {
              type: "text",
              text: "Lesson started; adapt depth, offer optional checks and cite evidence.",
            },
          ],
          details: {},
        };
      }
      const result = topic
        ? captureLesson(defaultStateRoot(), { topic, entries })
        : { status: "no_active_lesson" };
      topic = "";
      entries = [];
      return {
        content: [{ type: "text", text: JSON.stringify(result) }],
        details: result,
      };
    },
  });
  pi.on("message_end", async (e: any) => {
    if (!topic || !loadProfile(defaultStateRoot()).features.lessonCapture)
      return;
    if (!["user", "assistant"].includes(e.message.role)) return;
    const content = e.message.content;
    const text =
      typeof content === "string"
        ? content
        : Array.isArray(content)
          ? content
              .filter((c: any) => c.type === "text")
              .map((c: any) => c.text)
              .join("\n")
          : "";
    if (text) append({ role: e.message.role, text: text.slice(0, 12000) });
  });
  return {
    active: () => [...defs.keys()],
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
