import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { randomUUID } from "node:crypto";
import { validateQuiz, gradeQuiz, shuffled } from "../src/learning/quiz.ts";
import { captureLesson } from "../src/learning/capture.ts";
import { defaults, saveProfile } from "../src/assistant/profile.ts";
test("quiz IDs survive shuffle and grading cannot approve records", () => {
  const q = {
    question: "Which types are immutable?",
    multiple: true,
    options: [
      { id: "a", label: "String", correct: true },
      { id: "b", label: "List", correct: false },
      { id: "c", label: "Tuple", correct: true },
    ],
    explanation: "Synthetic quiz explanation",
  };
  assert.equal(gradeQuiz(q, ["c", "a"]).correct, true);
  assert.equal(gradeQuiz(q, []).status, "unknown");
  assert.equal(gradeQuiz(q, null).status, "skipped");
  assert.equal(gradeQuiz(q, ["a"]).authority, "conversation_only");
  assert.throws(() => gradeQuiz(q, ["injected"]));
  assert.throws(() =>
    validateQuiz({ ...q, options: [q.options[0], q.options[0]] }),
  );
  assert.deepEqual(
    shuffled(q.options, () => 0)
      .map((x) => x.id)
      .sort(),
    ["a", "b", "c"],
  );
});
test("lesson capture is opt-in, bounded and outside vault/source", () => {
  if (!process.env.TEST_SCRATCH) throw Error("Set external TEST_SCRATCH");
  const state = path.join(process.env.TEST_SCRATCH, "lesson-" + randomUUID());
  assert.equal(
    captureLesson(state, { topic: "Synthetic", entries: [] }).status,
    "disabled",
  );
  const p = defaults();
  p.features.lessonCapture = true;
  saveProfile(state, p);
  const r = captureLesson(state, {
    topic: "Synthetic",
    entries: [{ text: "Example" }],
  });
  assert.equal(r.status, "captured");
  assert.equal(r.authority, "unreviewed_private_lesson");
  assert(
    fs.existsSync(path.join(state, "assistant/lessons", r.handle + ".json")),
  );
  assert.throws(
    () =>
      captureLesson(state, {
        topic: "Synthetic",
        entries: [{ text: "x".repeat(300000) }],
      }),
    /limit/,
  );
});
