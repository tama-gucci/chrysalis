import {
  Input,
  SelectList,
  getKeybindings,
  matchesKey,
  Key,
  truncateToWidth,
} from "@earendil-works/pi-tui";
import type {
  ExtensionCommandContext,
  Theme,
} from "@earendil-works/pi-coding-agent";
type PickerTerminal = { terminal: { rows: number }; requestRender: () => void };

export function firstModelMatch(options: readonly string[], prefix: string) {
  const query = prefix.trim().toLowerCase();
  if (!query) return -1;
  return options.findIndex((value) => {
    const name = value.toLowerCase();
    return (
      name.startsWith(query) ||
      name.slice(name.indexOf("/") + 1).startsWith(query)
    );
  });
}

/** Native type-ahead jumps without changing the authorized model inventory. */
export function createModelPicker(
  title: string,
  options: readonly string[],
  tui: PickerTerminal,
  theme: Pick<Theme, "fg">,
  done: (value: string | undefined) => void,
) {
  const input = new Input({
    prompt: "Jump to: ",
    placeholder: "provider or model prefix",
  });
  let selected = 0,
    visible = 0,
    list: SelectList,
    finished = false;
  const finish = (value: string | undefined) => {
    if (!finished) {
      finished = true;
      done(value);
    }
  };
  const current = () => {
    const height = Math.max(1, Math.min(12, tui.terminal.rows - 9));
    if (!list || height !== visible) {
      visible = height;
      list = new SelectList(
        options.map((label, index) => ({ value: String(index), label })),
        visible,
        {
          selectedPrefix: (text) => theme.fg("accent", text),
          selectedText: (text) => theme.fg("accent", text),
          description: (text) => theme.fg("dim", text),
          scrollInfo: (text) => theme.fg("dim", text),
          noMatch: (text) => theme.fg("dim", text),
        },
      );
      list.setSelectedIndex(selected);
      list.onSelectionChange = (item) => {
        selected = Number(item.value);
      };
      list.onSelect = (item) => finish(options[Number(item.value)]);
      list.onCancel = () => finish(undefined);
    }
    return list;
  };
  return {
    get focused() {
      return input.focused;
    },
    set focused(value: boolean) {
      input.focused = value;
    },
    render(width: number) {
      const noMatch =
        !!input.getValue().trim() &&
        firstModelMatch(options, input.getValue()) < 0;
      return [
        theme.fg("accent", truncateToWidth(title, width)),
        ...input.render(width),
        ...current().render(width),
        theme.fg(
          "dim",
          truncateToWidth(
            noMatch
              ? "No matching model; edit or clear the prefix."
              : "Type to jump · Backspace edits · Ctrl+U clears",
            width,
          ),
        ),
        theme.fg(
          "dim",
          truncateToWidth(
            "↑↓ navigate · PgUp/PgDn page · Enter select · Esc cancel",
            width,
          ),
        ),
      ];
    },
    handleInput(data: string) {
      if (finished) return;
      const picker = current(),
        keys = getKeybindings();
      if (matchesKey(data, Key.pageUp) || matchesKey(data, Key.pageDown)) {
        selected = Math.max(
          0,
          Math.min(
            options.length - 1,
            selected + (matchesKey(data, Key.pageUp) ? -visible : visible),
          ),
        );
        picker.setSelectedIndex(selected);
      } else if (matchesKey(data, Key.home) || matchesKey(data, Key.end)) {
        selected = matchesKey(data, Key.home) ? 0 : options.length - 1;
        picker.setSelectedIndex(selected);
      } else if (
        keys.matches(data, "tui.select.up") ||
        keys.matches(data, "tui.select.down") ||
        keys.matches(data, "tui.select.cancel")
      ) {
        picker.handleInput(data);
      } else if (keys.matches(data, "tui.select.confirm")) {
        if (
          !input.getValue().trim() ||
          firstModelMatch(options, input.getValue()) >= 0
        )
          picker.handleInput(data);
      } else {
        const before = input.getValue();
        if (matchesKey(data, Key.ctrl("u"))) input.setValue("");
        else input.handleInput(data);
        if (input.getValue() !== before) {
          const index = firstModelMatch(options, input.getValue());
          if (index >= 0) {
            selected = index;
            picker.setSelectedIndex(selected);
          }
        }
      }
      tui.requestRender();
    },
    invalidate() {
      current().invalidate();
      input.invalidate();
    },
  };
}

export async function selectModel(
  ctx: ExtensionCommandContext,
  title: string,
  options: readonly string[],
): Promise<string | undefined> {
  if (!ctx.hasUI)
    throw Error("Model selection requires native interactive controls");
  return ctx.ui.custom<string | undefined>(
    (tui, theme, _keys, done) =>
      createModelPicker(title, options, tui, theme, done),
    { overlay: true, overlayOptions: { width: "100%", margin: 1 } },
  );
}
