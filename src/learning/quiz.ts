import { randomInt } from "node:crypto";
export interface Quiz {
  question: string;
  multiple: boolean;
  options: { id: string; label: string; correct: boolean }[];
  explanation: string;
}
export function validateQuiz(q: Quiz): Quiz {
  if (
    typeof q.question !== "string" ||
    q.question.length > 3000 ||
    typeof q.explanation !== "string" ||
    q.explanation.length > 6000 ||
    typeof q.multiple !== "boolean" ||
    !Array.isArray(q.options) ||
    q.options.length < 2 ||
    q.options.length > 8
  )
    throw Error("Invalid quiz");
  const ids = new Set<string>();
  for (const o of q.options) {
    if (
      !/^[a-z0-9-]{1,40}$/.test(o.id) ||
      ids.has(o.id) ||
      typeof o.label !== "string" ||
      o.label.length > 1000 ||
      typeof o.correct !== "boolean"
    )
      throw Error("Invalid quiz options");
    ids.add(o.id);
  }
  const n = q.options.filter((o) => o.correct).length;
  if (!n || (!q.multiple && n !== 1))
    throw Error("Quiz needs a valid answer key");
  return q;
}
export function shuffled<T>(values: T[], choose = randomInt): T[] {
  const result = [...values];
  for (let i = result.length - 1; i > 0; i--) {
    const j = choose(i + 1);
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}
export function gradeQuiz(q: Quiz, selected: string[] | null) {
  validateQuiz(q);
  if (selected === null)
    return {
      status: "skipped",
      correct: null,
      selected: [],
      explanation: null,
      authority: "conversation_only",
    };
  if (
    new Set(selected).size !== selected.length ||
    selected.some((id) => !q.options.some((o) => o.id === id))
  )
    throw Error("Unknown quiz response");
  const key = q.options
    .filter((o) => o.correct)
    .map((o) => o.id)
    .sort();
  return {
    status: selected.length ? "answered" : "unknown",
    correct: key.join(",") === [...selected].sort().join(","),
    selected,
    answerKey: key,
    explanation: q.explanation,
    authority: "conversation_only",
  };
}
