import path from "node:path";
import {
  Input,
  SelectList,
  Text,
  getKeybindings,
  matchesKey,
  Key,
  truncateToWidth,
} from "@earendil-works/pi-tui";
import type {
  ExtensionCommandContext,
  Theme,
} from "@earendil-works/pi-coding-agent";
import {
  knownFolders,
  directorySuggestions,
  existingDirectory,
  resolveDirectoryText,
  type KnownFolders,
  type DirectorySuggestion,
} from "../src/platforms/locations.ts";

const hint =
  'Try "my documents folder", "home", "desktop", "downloads", or an absolute path. Tab completes; Enter confirms.';
export function createDirectoryInput(
  tui: { terminal: { rows: number }; requestRender: () => void },
  theme: Pick<Theme, "fg">,
  done: (value: string | undefined) => void,
  locations: KnownFolders,
) {
  const input = new Input({
    prompt: "Location: ",
    placeholder: "my documents folder",
  });
  let suggestions: DirectorySuggestion[] = [],
    selected = 0,
    visible = 0,
    list: SelectList,
    finished = false,
    error = "",
    lastValue: string | undefined;
  const finish = (value: string | undefined) => {
    if (!finished) {
      finished = true;
      done(value);
    }
  };
  const update = () => {
    const value = input.getValue();
    if (value !== lastValue) {
      lastValue = value;
      suggestions = directorySuggestions(value, locations);
      selected = 0;
      list = undefined as any;
      error = "";
    }
  };
  const current = (height: number) => {
    update();
    if (!list || visible !== height) {
      visible = height;
      list = new SelectList(
        suggestions.map((item, index) => ({
          value: String(index),
          label: item.label,
        })),
        height,
        {
          selectedPrefix: (t) => theme.fg("accent", t),
          selectedText: (t) => theme.fg("accent", t),
          description: (t) => theme.fg("dim", t),
          scrollInfo: (t) => theme.fg("dim", t),
          noMatch: (t) => theme.fg("dim", t),
        },
      );
      list.setSelectedIndex(selected);
      list.onSelectionChange = (item) => {
        selected = Number(item.value);
      };
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
      const heading = [
        theme.fg(
          "accent",
          truncateToWidth("Where should the vault be created?", width),
        ),
        ...new Text(theme.fg("dim", hint), 0, 0).render(width),
      ];
      const height = Math.max(
        1,
        Math.min(6, tui.terminal.rows - heading.length - 6),
      );
      const picker = current(height);
      let target = "Type a supported phrase or path.";
      if (input.getValue())
        try {
          target =
            "Resolved: " + resolveDirectoryText(input.getValue(), locations);
        } catch {
          target = "Keep typing, or use a suggested location.";
        }
      return [
        ...heading,
        ...input.render(width),
        theme.fg("dim", truncateToWidth(error || target, width)),
        ...(suggestions.length
          ? picker.render(width)
          : [
              theme.fg(
                "dim",
                truncateToWidth("No matching directory suggestions.", width),
              ),
            ]),
        theme.fg(
          "dim",
          truncateToWidth(
            "↑↓ suggestions · Tab complete · Enter confirm · Esc cancel",
            width,
          ),
        ),
      ];
    },
    handleInput(data: string) {
      if (finished) return;
      update();
      const keys = getKeybindings();
      if (keys.matches(data, "tui.select.cancel")) {
        finish(undefined);
        return;
      }
      if (keys.matches(data, "tui.select.confirm")) {
        try {
          finish(existingDirectory(input.getValue(), locations));
        } catch (e: any) {
          error =
            e.code === "ENOENT"
              ? "Folder does not exist; choose an existing folder."
              : e.message;
        }
      } else if (matchesKey(data, Key.tab)) {
        const chosen = suggestions[selected];
        if (chosen) {
          input.setValue("");
          input.handleInput(
            "\x1b[200~" + chosen.value + path.sep + "\x1b[201~",
          );
          update();
        }
      } else if (
        keys.matches(data, "tui.select.up") ||
        keys.matches(data, "tui.select.down")
      ) {
        if (suggestions.length) current(visible || 6).handleInput(data);
      } else {
        if (matchesKey(data, Key.ctrl("u"))) input.setValue("");
        else input.handleInput(data);
        update();
      }
      tui.requestRender();
    },
    invalidate() {
      input.invalidate();
      list?.invalidate();
    },
  };
}
export async function selectVaultParent(
  ctx: ExtensionCommandContext,
): Promise<string | undefined> {
  if (!ctx.hasUI)
    throw Error("Folder selection requires native interactive controls");
  const locations = knownFolders();
  return ctx.ui.custom<string | undefined>(
    (tui, theme, _keys, done) =>
      createDirectoryInput(tui, theme, done, locations),
    { overlay: true, overlayOptions: { width: "100%", margin: 1 } },
  );
}
