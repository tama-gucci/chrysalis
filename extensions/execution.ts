import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { createJiti } from "jiti";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import {
  defaultStateRoot,
  optionalSelectedContext,
} from "../src/storage/context.ts";
import {
  PACKAGE_ROOT,
  inside,
  rejectRedirects,
  digest,
  raw,
} from "../src/platforms/filesystem.ts";
import { loadProfile } from "../src/assistant/profile.ts";
import { assistantUI } from "../src/assistant/ui.ts";
import { runIsolated } from "../src/execution/linux.ts";
import { excluded } from "../src/execution/workspace.ts";

const require = createRequire(import.meta.url);
const jiti = createJiti(import.meta.url, { fsCache: false, moduleCache: true });
let riskModules: Promise<any> | undefined;
async function risk(command: string) {
  riskModules ??= (async () => {
    const root = path.dirname(
      require.resolve("@aliou/pi-guardrails/package.json"),
    );
    const core: any = await jiti.import(path.join(root, "src/core/index.ts"));
    const rules: any = await jiti.import(
      path.join(root, "extensions/permission-gate/rules.ts"),
    );
    return { core, rules };
  })();
  const { core, rules } = await riskModules;
  return core.checkAction({ kind: "command", command, origin: "bash" }, [
    rules.createPermissionGateRule({ patterns: [], useBuiltinMatchers: true }),
  ]);
}
function vault(): string | undefined {
  return optionalSelectedContext()?.vault;
}
const quote = (s: string) => "'" + s.replace(/'/g, "'\\''") + "'";
/** Constant program executes inside the namespace. User paths/data are encoded, never shell code. */
const fileProgram = `const fs=require('fs'),path=require('path'); const a=JSON.parse(fs.readFileSync(0,'utf8'));
const root='/workspace'; if(typeof a.path!=='string'||a.path.includes('\\\\')||a.path.includes('\\0'))throw Error('Invalid path');
const f=path.resolve(root,a.path);if(f!==root&&!f.startsWith(root+'/'))throw Error('Path escapes workspace');
let p=f;while(p!==root){if(fs.existsSync(p)){const s=fs.lstatSync(p);if(s.isSymbolicLink()||(!s.isDirectory()&&!s.isFile())||s.isFile()&&s.nlink!==1)throw Error('Unsupported link or special file');}p=path.dirname(p);}
if(a.op==='read'){const fd=fs.openSync(f,fs.constants.O_RDONLY|fs.constants.O_NOFOLLOW|fs.constants.O_NONBLOCK);try{const s=fs.fstatSync(fd);if(!s.isFile()||s.size>1048576)throw Error('Read requires a bounded regular file');const t=fs.readFileSync(fd,'utf8');const lines=t.split('\\n');console.log(lines.slice(a.offset-1,a.offset-1+a.limit).join('\\n'));}finally{fs.closeSync(fd)}}
else {fs.mkdirSync(path.dirname(f),{recursive:true});let content=a.content;if(a.op==='edit'){const t=fs.readFileSync(f,'utf8');if(t.length>1048576||!a.oldText||t.split(a.oldText).length!==2)throw Error('Edit must match exactly once');content=t.replace(a.oldText,a.newText)}if(typeof content!=='string'||Buffer.byteLength(content)>1048576)throw Error('Write limit');const temp=f+'.pending-'+require('crypto').randomUUID();try{fs.writeFileSync(temp,content,{flag:'wx',mode:a.op==='edit'?fs.statSync(f).mode&0o777:0o600});fs.renameSync(temp,f);console.log('Workspace file written')}finally{if(fs.existsSync(temp))fs.unlinkSync(temp)}}`;
function relativeInput(input: string) {
  if (input.split(/[\\/]/).some(excluded))
    throw Error("Protected workspace file");
  const w = loadProfile(defaultStateRoot()).workspace;
  if (input.startsWith("/workspace/")) return input.slice(11);
  if (path.isAbsolute(input)) {
    if (!w || !inside(input, w.root))
      throw Error("Read/write blocked outside the selected workspace");
    return path.relative(w.root, input);
  }
  return input;
}
export function installExecution(
  pi: ExtensionAPI,
  readableSkill: (file: string) => boolean = () => false,
  readOnly = false,
  origin = path.join(PACKAGE_ROOT, "extensions/chrysalis.ts"),
) {
  const definitions = new Map<string, string>();
  function register(t: any) {
    definitions.set(
      t.name,
      digest({
        name: t.name,
        description: t.description,
        parameters: t.parameters,
      }),
    );
    pi.registerTool(t);
  }
  async function execute(
    command: string,
    ctx: any,
    signal?: AbortSignal,
    timeout?: number,
  ) {
    if (!loadProfile(defaultStateRoot()).features.execution)
      throw Error("Execution is disabled; use /chrysalis workspace");
    const decision = await risk(command);
    if (decision.kind !== "safe") {
      if (
        !ctx.hasUI ||
        !(await assistantUI.run(() =>
          ctx.ui.confirm(
            "Workspace command needs permission",
            decision.reason + "\n\n" + command,
          ),
        ))
      )
        throw Error("Command permission declined");
    }
    return runIsolated(defaultStateRoot(), command, {
      signal,
      timeout,
      vault: vault(),
      readOnly,
    });
  }
  register({
    name: "bash",
    label: "Isolated Bash",
    description:
      "Execute Linux Bash inside the selected chrysalis workspace. Network, vault, credentials and host directories are inaccessible. Native permission handles risky commands; no command can approve vault records.",
    parameters: Type.Object({
      command: Type.String(),
      timeout: Type.Optional(Type.Number({ minimum: 1, maximum: 900 })),
    }),
    async execute(
      _id: string,
      p: any,
      signal: AbortSignal,
      _update: any,
      ctx: any,
    ) {
      const r = await execute(p.command, ctx, signal, p.timeout);
      return {
        content: [{ type: "text", text: r.output }],
        details: r,
        isError: r.exitCode !== 0,
      };
    },
  });
  register({
    name: "read",
    label: "Read",
    description:
      "Read canonical chrysalis Markdown skills or a bounded text file inside the selected workspace. Vault reads use chrysalis_operation.",
    parameters: Type.Object({
      path: Type.String(),
      offset: Type.Optional(Type.Number({ minimum: 1 })),
      limit: Type.Optional(Type.Number({ minimum: 1, maximum: 1000 })),
    }),
    async execute(_id: string, p: any, signal: AbortSignal) {
      if (path.isAbsolute(p.path)) {
        const file = rejectRedirects(path.resolve(p.path));
        const relative = path
          .relative(PACKAGE_ROOT, file)
          .split(path.sep)
          .join("/");
        const publicSource =
          /^(src|extensions|skills|docs|contracts|Development|tests)\//.test(
            relative,
          ) ||
          /^(AGENTS|README|ARCHITECTURE|STATUS|CHANGELOG)\.md$/.test(
            relative,
          ) ||
          ["package.json", "tsconfig.json", "LICENSE"].includes(relative);
        if (
          (inside(file, PACKAGE_ROOT) &&
            publicSource &&
            /\.(md|ts|mjs|js|json)$/.test(file)) ||
          (readableSkill(file) && file.endsWith(".md"))
        ) {
          const lines = raw(file).toString("utf8").split("\n");
          return {
            content: [
              {
                type: "text",
                text: lines
                  .slice(
                    (p.offset ?? 1) - 1,
                    (p.offset ?? 1) - 1 + (p.limit ?? 1000),
                  )
                  .join("\n"),
              },
            ],
            details: {},
          };
        }
      }
      return fileCall(
        {
          ...p,
          path: relativeInput(p.path),
          op: "read",
          offset: p.offset ?? 1,
          limit: p.limit ?? 1000,
        },
        signal,
      );
    },
  });
  for (const op of ["write", "edit"])
    register({
      name: op,
      label: "Workspace " + op,
      description:
        op === "write"
          ? "Write a bounded UTF-8 file inside the selected workspace; never writes vault/source policy."
          : "Replace exactly one matching text fragment inside the selected workspace.",
      parameters:
        op === "write"
          ? Type.Object({ path: Type.String(), content: Type.String() })
          : Type.Object({
              path: Type.String(),
              oldText: Type.String(),
              newText: Type.String(),
            }),
      async execute(_id: string, p: any, signal: AbortSignal) {
        return fileCall({ ...p, path: relativeInput(p.path), op }, signal);
      },
    });
  async function fileCall(p: any, signal?: AbortSignal) {
    if (readOnly && p.op !== "read")
      throw Error("This role cannot write workspace files");
    const r = await runIsolated(
      defaultStateRoot(),
      "node -e " + quote(fileProgram),
      {
        signal,
        vault: vault(),
        input: JSON.stringify(p),
        readOnly: readOnly || p.op === "read",
      },
    );
    return {
      content: [{ type: "text", text: r.output }],
      details: r,
      isError: r.exitCode !== 0,
    };
  }
  pi.on("user_bash", async (event, ctx) => {
    const r = await execute(event.command, ctx);
    return {
      result: {
        output: r.output,
        exitCode: r.exitCode,
        cancelled: r.cancelled,
        truncated: r.truncated,
      },
    } as any;
  });
  return {
    active: () =>
      loadProfile(defaultStateRoot()).features.execution
        ? readOnly
          ? ["read", "bash"]
          : ["read", "bash", "write", "edit"]
        : ["read"],
    allowed(name: string) {
      if (
        !definitions.has(name) ||
        (name !== "read" && !loadProfile(defaultStateRoot()).features.execution)
      )
        return false;
      const t = pi.getAllTools().find((t) => t.name === name);
      return (
        !!t &&
        path.resolve(t.sourceInfo.path) === origin &&
        digest({
          name: t.name,
          description: t.description,
          parameters: t.parameters,
        }) === definitions.get(name)
      );
    },
  };
}
