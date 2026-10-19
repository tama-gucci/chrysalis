import path from "node:path";
import { Type } from "typebox";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { defaultStateRoot } from "../src/storage/context.ts";
import { PACKAGE_ROOT, digest } from "../src/platforms/filesystem.ts";
import { storeArtifact } from "../src/assistant/artifacts.ts";
import { mermaidVisual, sanitizeSVG } from "../src/learning/visuals.ts";
export function installVisuals(
  pi: ExtensionAPI,
  origin = path.join(PACKAGE_ROOT, "extensions/chrysalis.ts"),
) {
  const t: any = {
    name: "chrysalis_visual",
    label: "Diagram",
    description:
      "Create a bounded private Mermaid/SVG teaching diagram. Mermaid receives a terminal preview and inert SVG; warnings/inspection limits stay visible. Vault adoption requires native artifact review and notes require separate approval.",
    parameters: Type.Object({
      kind: Type.Union([Type.Literal("mermaid"), Type.Literal("svg")]),
      code: Type.String(),
    }),
    async execute(_id: string, p: any) {
      const rendered =
        p.kind === "mermaid"
          ? await mermaidVisual(p.code)
          : {
              svg: sanitizeSVG(p.code),
              preview: null,
              warnings: [],
              visual_inspected: false,
            };
      const artifact = storeArtifact(
        defaultStateRoot(),
        "svg",
        Buffer.from(rendered.svg),
        {
          format: p.kind,
          source: p.kind === "mermaid" ? p.code : null,
          warnings: rendered.warnings,
        },
      );
      return {
        content: [
          {
            type: "text",
            text: JSON.stringify({
              ...artifact,
              preview: rendered.preview,
              warnings: rendered.warnings,
              visual_inspected: false,
            }),
          },
        ],
        details: { artifact },
      };
    },
  };
  const signature = digest({
    name: t.name,
    description: t.description,
    parameters: t.parameters,
  });
  pi.registerTool(t);
  return {
    active: () => [t.name],
    allowed(name: string) {
      const found = pi.getAllTools().find((t) => t.name === name);
      return (
        name === t.name &&
        !!found &&
        path.resolve(found.sourceInfo.path) === origin &&
        digest({
          name: found.name,
          description: found.description,
          parameters: found.parameters,
        }) === signature
      );
    },
  };
}
