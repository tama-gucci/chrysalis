import test from "node:test";
import assert from "node:assert/strict";
import {
  visibleWidth,
  getKeybindings,
  setKeybindings,
  KeybindingsManager,
  TUI_KEYBINDINGS,
} from "@earendil-works/pi-tui";
import {
  createModelPicker,
  selectModel,
  firstModelMatch,
} from "../extensions/model-picker.ts";

const options = [
  ...Array.from({ length: 70 }, (_, i) => "synthetic/model-" + i),
  "synthetic-reviewed/small",
  "Skip",
];
const theme: any = { fg: (_color: string, text: string) => text };
function fixture(rows = 20) {
  const values: Array<string | undefined> = [];
  const tui = { terminal: { rows }, requestRender() {} };
  const picker = createModelPicker(
    "Background model",
    options,
    tui,
    theme,
    (value) => values.push(value),
  );
  return { values, tui, picker };
}

test("long model list follows every keyboard selection and reaches reviewed providers", () => {
  const { picker, values, tui } = fixture();
  for (let index = 0; index < options.length - 1; index++) {
    const lines = picker.render(80);
    assert(lines.length <= tui.terminal.rows - 2);
    assert(lines.some((line) => line.includes("→ " + options[index])));
    assert(lines.every((line) => visibleWidth(line) <= 80));
    if (index < options.length - 2) picker.handleInput("\x1b[B");
  }
  assert(
    picker
      .render(80)
      .some((line) => line.includes("→ synthetic-reviewed/small")),
  );
  picker.handleInput("\r");
  assert.deepEqual(values, ["synthetic-reviewed/small"]);
});

test("resize preserves the selected model and fits a small terminal", () => {
  const { picker, tui } = fixture(40);
  for (let i = 0; i < 35; i++) picker.handleInput("\x1b[B");
  for (const rows of [12, 9, 40]) {
    tui.terminal.rows = rows;
    const lines = picker.render(38);
    assert(lines.length <= Math.max(6, rows - 2));
    assert(lines.some((line) => line.includes("→ synthetic/model-35")));
    assert(lines.every((line) => visibleWidth(line) <= 38));
  }
});

test("paging and endpoint keys keep selection visible and return the exact native choice", () => {
  const { picker, values } = fixture(18);
  picker.handleInput("\x1b[6~");
  assert(
    picker.render(80).some((line) => line.includes("→ synthetic/model-9")),
  );
  picker.handleInput("\x1b[5~");
  assert(
    picker.render(80).some((line) => line.includes("→ synthetic/model-0")),
  );
  picker.handleInput("\x1b[F");
  assert(picker.render(80).some((line) => line.includes("→ Skip")));
  picker.handleInput("\x1b[H");
  assert(
    picker.render(80).some((line) => line.includes("→ synthetic/model-0")),
  );

  picker.handleInput("\r");
  assert.deepEqual(values, [options[0]]);
});

test("cancel never selects a model; headless calls cannot supply native choices", async () => {
  const { picker, values } = fixture();
  picker.handleInput("\x1b");
  picker.handleInput("\r");
  assert.deepEqual(values, [undefined]);
  await assert.rejects(
    selectModel({ hasUI: false } as any, "Models", options),
    /native interactive/,
  );
  let result: string | undefined;
  const native: any = {
    hasUI: true,
    ui: {
      custom: async (factory: any) => {
        const component = factory(
          { terminal: { rows: 16 }, requestRender() {} },
          theme,
          null,
          (value: string | undefined) => {
            result = value;
          },
        );
        component.handleInput("\x1b[F");
        component.handleInput("\x1b[A");
        component.handleInput("\r");
        return result;
      },
    },
  };
  assert.equal(
    await selectModel(native, "Models", options),
    "synthetic-reviewed/small",
  );
});

test("type-ahead jumps by provider/model prefixes, edits and clears without accepting a stale no-match", () => {
  const choices = [
    "openai/example-model",
    "antigravity/example-small",
    "antigravity/example-large",
    "Skip",
  ];
  const values: Array<string | undefined> = [];
  const picker = createModelPicker(
    "Models",
    choices,
    { terminal: { rows: 20 }, requestRender() {} },
    theme,
    (value) => values.push(value),
  );
  for (const key of "ant") picker.handleInput(key);
  assert(
    picker
      .render(80)
      .some((line) => line.includes("→ antigravity/example-small")),
  );
  picker.handleInput("\x7f");
  assert(
    picker
      .render(80)
      .some((line) => line.includes("→ antigravity/example-small")),
  );
  picker.handleInput("\x1b[D");
  picker.handleInput("\x15");
  for (const key of "example-l") picker.handleInput(key);
  assert(
    picker
      .render(80)
      .some((line) => line.includes("→ antigravity/example-large")),
  );
  picker.handleInput("\x15");
  for (const key of "missing") picker.handleInput(key);
  picker.handleInput("\r");
  assert.deepEqual(values, []);
  assert(picker.render(80).some((line) => line.includes("No matching model")));
  picker.handleInput("\x15");
  picker.handleInput("\r");
  assert.deepEqual(values, ["antigravity/example-large"]);
  assert.equal(firstModelMatch(choices, "ANT"), 1);
});

test("configured navigation still works while printable j/k belong to type-ahead", () => {
  const original = getKeybindings();
  try {
    setKeybindings(
      new KeybindingsManager(TUI_KEYBINDINGS, {
        "tui.select.up": "ctrl+p",
        "tui.select.down": "ctrl+n",
      }),
    );
    const { picker, values } = fixture();
    picker.handleInput("\x0e");
    assert(
      picker.render(80).some((line) => line.includes("→ synthetic/model-1")),
    );
    picker.handleInput("\x10");
    assert(
      picker.render(80).some((line) => line.includes("→ synthetic/model-0")),
    );
    picker.handleInput("k");
    assert(
      picker.render(80).some((line) => line.includes("No matching model")),
    );
    picker.handleInput("\x03");
    assert.deepEqual(values, [undefined]);
  } finally {
    setKeybindings(original);
  }
});
