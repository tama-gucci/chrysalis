import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";
import {
  PACKAGE_ROOT,
  files,
  raw,
  readJSON,
  sha256,
} from "../platforms/filesystem.ts";
import { serializeRecord } from "../storage/records.ts";
import { zoneName } from "../time/timezone.ts";
import { MODALITIES } from "../contracts/types.ts";
import { registry } from "../contracts/fields.ts";
export { registry } from "../contracts/fields.ts";

export const DIRECTORIES = [
  "System",
  "TaskNotes/Tasks",
  "TaskNotes/Archive",
  "TaskNotes/Workflows",
  "Daily",
  "Projects",
  "Slipbox",
  "Sources",
  "Environments",
  "Attachments/Originals",
];
export function pluginLock() {
  return readJSON(path.join(PACKAGE_ROOT, "resources/plugins.lock.json"));
}
const json = (value: any) => Buffer.from(JSON.stringify(value, null, 2) + "\n");
export function preset(timezone: string, id: string) {
  timezone = zoneName(timezone);
  const fields = registry(),
    lock = pluginLock(),
    result = new Map<string, Buffer>();
  const base = path.join(PACKAGE_ROOT, "resources/vault");
  for (const file of files(base)) {
    const relative = path.relative(base, file).split(path.sep).join("/");
    result.set(relative, raw(file, 4 * 1024 * 1024));
  }
  // The registry is the source of truth for the task schema, UI defaults and views.
  result.set(
    "_types/task.md",
    Buffer.from(
      serializeRecord(
        { name: "task", version: 2, schema: { value: fields.task_schema } },
        "Task properties follow the chrysalis field registry.\n",
      ),
    ),
  );
  for (const plugin of lock.plugins) {
    const manifest = readJSON(
      path.join(PACKAGE_ROOT, "resources/plugins", plugin.id, "manifest.json"),
    );
    if (
      manifest.id !== plugin.id ||
      manifest.version !== plugin.version ||
      manifest.minAppVersion !== plugin.minAppVersion
    )
      throw new Error("Plugin manifest mismatch");
    for (const [file, expected] of Object.entries(plugin.assets) as Array<
      [string, any]
    >) {
      if (!["main.js", "manifest.json", "styles.css", "LICENSE"].includes(file))
        throw new Error("Untrusted plugin asset name");
      const bytes = raw(
        path.join(PACKAGE_ROOT, "resources/plugins", plugin.id, file),
        16 * 1024 * 1024,
      );
      if (bytes.length !== expected.bytes || sha256(bytes) !== expected.sha256)
        throw new Error("Plugin asset hash mismatch");
      result.set(".obsidian/plugins/" + plugin.id + "/" + file, bytes);
    }
  }
  const statuses = fields.task_schema.properties.status.enum.map(
    (value: string, order: number) => ({
      id: value,
      value,
      label:
        value === "todo"
          ? "To do"
          : value === "in-progress"
            ? "In progress"
            : value[0].toUpperCase() + value.slice(1),
      color: ["#808080", "#0066cc", "#008800", "#777777"][order],
      isCompleted: ["done", "archived"].includes(value),
      excludeFromCycle: value === "archived",
      order,
      autoArchive: false,
      autoArchiveDelay: 5,
    }),
  );
  const priorities = [...fields.task_schema.properties.priority.enum]
    .reverse()
    .map((value: string, weight: number) => ({
      id: value,
      value,
      label: value[0].toUpperCase() + value.slice(1),
      weight,
      color: ["#777777", "#008800", "#bb8800", "#cc5500", "#bb0000"][weight],
    }));
  const mapping = fields.field_mapping;
  const viewMap = {
    "open-calendar-view": "mini-calendar-default",
    "open-kanban-view": "kanban-default",
    "open-tasks-view": "tasks-default",
    "open-advanced-calendar-view": "calendar-default",
    "open-agenda-view": "agenda-default",
    "pomodoro-stats-base": "pomodoro-stats",
    relationships: "relationships",
  };
  result.set(
    ".obsidian/plugins/tasknotes/data.json",
    json({
      tasksFolder: fields.identification.folder,
      archiveFolder: fields.identification.archive,
      moveArchivedTasks: false,
      taskTag: fields.identification.tag,
      taskIdentificationMethod: "tag",
      excludedFolders:
        "TaskNotes/Archive, Attachments/Originals, _templates, _types, Projects/_templates, Slipbox/_templates, Environments/_templates",
      defaultTaskStatus: "todo",
      defaultTaskPriority: "normal",
      taskFilenameFormat: "zettel",
      storeTitleInFilename: false,
      fieldMapping: mapping,
      customStatuses: statuses,
      customPriorities: priorities,
      userFields: fields.custom_fields,
      taskCreationDefaults: {
        defaultContexts: "",
        defaultTags: "",
        defaultProjects: "",
        useParentNoteForTaskCreation: false,
        useParentNoteAsProject: false,
        useParentHeaderAsProject: false,
        inheritParentTaskProperties: false,
        defaultTimeEstimate: 45,
        defaultRecurrence: "none",
        defaultDueDate: "none",
        defaultDueTime: "none",
        defaultScheduledDate: "none",
        defaultScheduledTime: "none",
        useBodyTemplate: false,
        defaultReminders: [],
      },
      nlpDefaultToScheduled: false,
      inlineTaskConvertFolder: "TaskNotes/Tasks",
      pomodoroWorkDuration: 75,
      pomodoroShortBreakDuration: 15,
      pomodoroLongBreakDuration: 30,
      pomodoroLongBreakInterval: 3,
      pomodoroAutoStartBreaks: false,
      pomodoroAutoStartWork: false,
      pomodoroStorageLocation: "daily-notes",
      enableBases: true,
      enableMdbaseSpec: false,
      autoCreateDefaultBasesFiles: false,
      commandFileMapping: Object.fromEntries(
        Object.entries(viewMap).map(([k, v]) => [
          k,
          "TaskNotes/Views/" + v + ".base",
        ]),
      ),
      enableAPI: false,
      enableMCP: false,
      webhooks: [],
      enableDebugLogging: false,
      enableGoogleCalendar: false,
      enableMicrosoftCalendar: false,
      googleCalendarExport: { enabled: false },
      starterNoteCreated: true,
      showReleaseNotesOnUpdate: false,
      checkForUpdatesOnStartup: false,
    }),
  );
  result.set(
    ".obsidian/plugins/dataview/data.json",
    json({
      enableDataviewJs: false,
      enableInlineDataviewJs: false,
      enableInlineDataview: true,
    }),
  );
  result.set(
    ".obsidian/community-plugins.json",
    json(lock.plugins.map((p) => p.id)),
  );
  result.set(
    ".obsidian/core-plugins.json",
    json([
      "file-explorer",
      "global-search",
      "switcher",
      "graph",
      "backlink",
      "outgoing-link",
      "tag-pane",
      "properties",
      "page-preview",
      "daily-notes",
      "templates",
      "note-composer",
      "command-palette",
      "editor-status",
      "bookmarks",
      "outline",
      "word-count",
      "file-recovery",
      "bases",
    ]),
  );
  result.set(
    ".obsidian/app.json",
    json({
      attachmentFolderPath: "Attachments/Originals",
      alwaysUpdateLinks: true,
      newLinkFormat: "relative",
      useMarkdownLinks: false,
    }),
  );
  result.set(".obsidian/appearance.json", json({ baseFontSize: 16 }));
  result.set(
    ".obsidian/daily-notes.json",
    json({
      folder: "Daily",
      format: "YYYY-MM-DD",
      template: "_templates/Daily-Note",
    }),
  );
  result.set(
    ".obsidian/templates.json",
    json({
      folder: "_templates",
      dateFormat: "YYYY-MM-DD",
      timeFormat: "HH:mm",
    }),
  );
  const taskFilters = {
    and: [
      `file.inFolder("${fields.identification.folder}")`,
      `file.hasTag("${fields.identification.tag}")`,
      'status != "archived"',
      "archived != true",
    ],
  };
  for (const [command, name] of Object.entries(viewMap)) {
    const type = {
      "open-calendar-view": "tasknotesMiniCalendar",
      "open-kanban-view": "tasknotesKanban",
      "open-tasks-view": "tasknotesTaskList",
      "open-advanced-calendar-view": "tasknotesCalendar",
      "open-agenda-view": "tasknotesCalendar",
      "pomodoro-stats-base": "table",
      relationships: "tasknotesKanban",
    }[command];
    const view = {
      type,
      name: name.replace(/-/g, " "),
      order: [
        "status",
        "priority",
        "due",
        "scheduled",
        "projects",
        "timeEstimate",
      ],
      options: {
        showScheduled: true,
        showDue: true,
        showRecurring: true,
        showTimeEntries: true,
        showTimeblocks: true,
        showICSEvents: false,
        calendarView:
          command === "open-agenda-view" ? "listWeek" : "timeGridWeek",
      },
    };
    result.set(
      "TaskNotes/Views/" + name + ".base",
      Buffer.from(
        YAML.stringify(
          {
            filters:
              command === "pomodoro-stats-base"
                ? { and: ['file.inFolder("Daily")'] }
                : taskFilters,
            formulas:
              command === "pomodoro-stats-base"
                ? {
                    sessions:
                      "if(pomodoros, list(pomodoros).filter(value.completed).length, 0)",
                    workMinutes:
                      'if(pomodoros, list(pomodoros).filter(value.completed && value.type == "work").map(value.plannedDuration).reduce(acc + value, 0), 0)',
                  }
                : {},
            views: [
              command === "pomodoro-stats-base"
                ? {
                    type: "table",
                    name: "Sessions",
                    order: [
                      "file.name",
                      "formula.sessions",
                      "formula.workMinutes",
                    ],
                  }
                : view,
            ],
          },
          { lineWidth: 0 },
        ),
      ),
    );
  }
  result.set(
    "TaskNotes/Views/projects.base",
    Buffer.from(
      YAML.stringify({
        filters: { and: ['file.inFolder("Projects")', 'type == "project"'] },
        views: [
          {
            type: "table",
            name: "Projects",
            order: ["title", "status", "linked_zettels"],
          },
        ],
      }),
    ),
  );
  const memory = {
    type: "system_state",
    schema_version: "2",
    user_profile: { timezone },
    system_state: { pause_state: { is_paused: false } },
    active_horizons: { active_projects: [] },
    cognitive_modality_defaults: Object.fromEntries(
      MODALITIES.map((m) => [m, { multiplier: 1 }]),
    ),
    integrations: { contract_version: "2", instances: {}, bindings: {} },
    ingestion: {
      contract_version: "2",
      sources: {},
      preserve_originals_in_place: true,
    },
  };
  result.set(
    "System/Memory.md",
    Buffer.from(
      serializeRecord(
        memory,
        "# Memory\n\nPreferences and approved learning.\n",
      ),
    ),
  );
  result.set(
    "System/Life-Roadmap.md",
    Buffer.from(
      serializeRecord(
        {
          type: "strategic_roadmap",
          tag_registry: {},
          milestones: [],
          onboarding_status: "awaiting_conversation",
        },
        "# Life roadmap\n\nChoose goals during conversational onboarding.\n",
      ),
    ),
  );
  result.set(
    ".chrysalis-vault.json",
    json({
      schema_version: "1",
      vault_id: id,
      package_version: "2.0.0",
      preset_version: "2",
      setup_status: "ready",
    }),
  );
  result.set(
    "_templates/Daily-Note.md",
    Buffer.from(
      "---\ntype: daily_note\ndate: {{date:YYYY-MM-DD}}\ntags: [daily-note]\nblocks: []\npomodoros: []\n---\n\n# {{date:YYYY-MM-DD}}\n\n## Notes\n",
    ),
  );
  result.set(
    "Dashboard.md",
    Buffer.from(
      '# chrysalis\n\n[[Getting Started]] · [[TaskNotes/Views/tasks-default.base|Tasks]] · [[TaskNotes/Views/agenda-default.base|Agenda]] · [[TaskNotes/Views/calendar-default.base|Calendar]] · [[TaskNotes/Views/projects.base|Projects]] · [[TaskNotes/Views/pomodoro-stats.base|Sessions]]\n\n## Today\n\n```dataview\nTABLE priority, scheduled, timeEstimate, modality\nFROM "TaskNotes/Tasks"\nWHERE status != "done" AND status != "archived" AND !archived AND date(scheduled).day = date(today).day AND date(scheduled).month = date(today).month AND date(scheduled).year = date(today).year\nSORT scheduled ASC\n```\n\n## Backlog\n\n```dataview\nTABLE priority, due, projects, timeEstimate\nFROM "TaskNotes/Tasks"\nWHERE status != "done" AND status != "archived" AND !archived\nSORT priority ASC, due ASC\n```\n\n## Knowledge\n\n[[System/Knowledge-Index|Knowledge index]]\n\n```dataview\nLIST FROM "Slipbox"\nWHERE file.name != "README"\nSORT file.mtime DESC\nLIMIT 10\n```\n',
    ),
  );
  result.set(
    "Getting Started.md",
    Buffer.from(
      "# Getting started\n\nOpen this folder using **Open folder as vault** in Obsidian. Enable community plugins when prompted. TaskNotes and Dataview files are already provided. Open [[Dashboard]] to begin.\n\nUse Pi's `/chrysalis onboard` to discuss your goals, then the chrysalis skills to capture work and review plans. Changes are drafted for your review before operator approval.\n\nCreate tasks through TaskNotes or Pi. Tasks use todo, in-progress, done and archived; priorities run from none through urgent. Custom modality values are analytical, kinetic, synthesis and administrative. Energy/friction values are low, medium and high. Urgency runs from 1 to 4.\n\nDaily notes retain focus plans and TaskNotes session records. Originals belong in Attachments/Originals and can be opened and linked within this vault.\n\nOnboarding uses your computer's timezone. After a move, update the computer's timezone and run `/chrysalis timezone` in Pi. Review its proposed change. Existing records keep their times. `/chrysalis timezone --zone Europe/Paris` provides an explicit correction.\n",
    ),
  );
  return result;
}
