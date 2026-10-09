// Evidence-candidate algorithm adapted from Astro-Han/karpathy-llm-wiki (MIT).
// See resources/notices/karpathy-llm-wiki.LICENSE.txt. Reports are not factual verdicts.
export interface Literal {
  kind: "number" | "date" | "quote";
  value: string;
}
export const normalizeEvidence = (value: string) =>
  value.replace(/\s+/g, " ").trim();
const numbers =
  /(?:\d{1,3}(?:,\d{3})+(?:\.\d+)*(?:\s*[KMB%](?![A-Za-z]))?|\d+(?:\.\d+)*(?:\s*[KMB%](?![A-Za-z]))?)(?![A-Za-z])/g;
const dates = /\d{4}-\d{2}(?:-\d{2})?/g;
const escapeRegex = (value: string) =>
  value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

/** Remove actual fences, not similarly shaped body text. Inputs are already parsed Markdown bodies. */
export function visibleLines(body: string): string[] {
  const result: string[] = [];
  let fence: { char: string; length: number } | undefined;
  for (const line of body.split(/\r?\n/)) {
    if (fence) {
      const end = /^ {0,3}(`{3,}|~{3,})[ \t]*$/.exec(line);
      if (end && end[1][0] === fence.char && end[1].length >= fence.length)
        fence = undefined;
      continue;
    }
    const start = /^ {0,3}(`{3,}|~{3,})(.*)$/.exec(line);
    if (start && !(start[1][0] === "`" && start[2].includes("`"))) {
      fence = { char: start[1][0], length: start[1].length };
      continue;
    }
    result.push(
      line
        .replace(/`[^`\n]*`/g, " ")
        .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
        .replace(
          /\[\[([^\]|]+)(?:\|([^\]]+))?\]\]/g,
          (_m, _target, label) => label ?? " ",
        ),
    );
  }
  return result;
}

/** High-signal closed candidate set: exact numeric spellings, ISO dates and long quotations. */
export function evidenceCandidates(body: string): Literal[] {
  const found: Literal[] = [];
  let paragraph: string[] = [],
    quotation: string[] = [],
    annotation = false;
  const flushParagraph = () => {
    const joined = normalizeEvidence(paragraph.join(" "));
    for (const expression of [/"([^"\n]*)"/g, /“([^”\n]*)”/g])
      for (const match of joined.matchAll(expression))
        if (match[1].trim().length >= 15)
          found.push({ kind: "quote", value: match[1].trim() });
    paragraph = [];
  };
  const flushQuote = () => {
    const joined = normalizeEvidence(quotation.join(" "));
    if (joined.length >= 15) found.push({ kind: "quote", value: joined });
    quotation = [];
  };
  for (const line of visibleLines(body)) {
    const stripped = line.trim();
    if (/^>\s*\*\*Status:/.test(stripped)) {
      flushParagraph();
      flushQuote();
      annotation = true;
      continue; // Annotation date is bookkeeping; explanations below still receive literal checks.
    }
    const quoted = stripped.startsWith(">");
    if (!quoted) annotation = false;
    let content = quoted ? stripped.replace(/^>\s*/, "") : line;
    for (const match of content.matchAll(dates))
      found.push({ kind: "date", value: match[0] });
    content = content.replace(dates, (match) => " ".repeat(match.length));
    for (const match of content.matchAll(numbers)) {
      const value = match[0].trim();
      if (/[KMB%]$|[,.]/.test(value) || value.length >= 4)
        found.push({ kind: "number", value });
    }
    if (quoted && !annotation) {
      flushParagraph();
      quotation.push(stripped.replace(/^>\s*/, ""));
    } else {
      flushQuote();
      if (!stripped) flushParagraph();
      else paragraph.push(quoted ? stripped.replace(/^>\s*/, "") : line);
    }
  }
  flushParagraph();
  flushQuote();
  const unique = new Map<string, Literal>();
  for (const item of found) unique.set(item.kind + "\0" + item.value, item);
  if (unique.size > 1000)
    throw new Error("Knowledge literal budget exceeded; narrow the note");
  return [...unique.values()];
}

export function containsLiteral(text: string, literal: Literal): boolean {
  return literalMatcher(literal)(normalizeEvidence(text));
}

/** Compile once and match already-normalized captured text without repeated whole-source copies. */
export function literalMatcher(
  literal: Literal,
): (normalized: string) => boolean {
  if (literal.kind === "quote") {
    const quotation = normalizeEvidence(literal.value);
    return (text) => text.includes(quotation);
  }
  const monthEnd =
    literal.kind === "date" && literal.value.length === 7 ? "(?!-\\d{2})" : "";
  const expression = new RegExp(
    "(?<![\\d.,])" +
      escapeRegex(normalizeEvidence(literal.value)) +
      monthEnd +
      "(?![A-Za-z0-9]|[.,]\\d|%)",
  );
  return (text) => expression.test(text);
}

/** Only captured payload text is evidence. A source record's title, timestamp and summaries are not. */
export function capturedEvidence(body: string): string[] {
  return [
    ...body.matchAll(
      /<untrusted_document_payload(?:\s[^>]*)?>([\s\S]*?)<\/untrusted_document_payload>/g,
    ),
  ]
    .map((match) =>
      normalizeEvidence(
        match[1]
          .replace(/&lt;/g, "<")
          .replace(/&gt;/g, ">")
          .replace(/&quot;/g, '"')
          .replace(/&#39;|&apos;/g, "'")
          .replace(/&amp;/g, "&"),
      ),
    )
    .filter((text) => text.length > 0);
}
