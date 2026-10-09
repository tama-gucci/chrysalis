import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListToolsRequestSchema,
  CallToolRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import { sourceTool } from "../integrations/service.ts";
import { TOOL_SCHEMAS, TOOL_DESCRIPTIONS } from "../integrations/contracts.ts";
import { selectedContext } from "../storage/context.ts";

const index = process.argv.indexOf("--state");
if (index < 0 || !process.argv[index + 1])
  throw Error("explicit_external_state_required");
const state = process.argv[index + 1];
const server = new Server(
  { name: "chrysalis", version: "2.0.0" },
  { capabilities: { tools: {} } },
);
server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: Object.entries(TOOL_SCHEMAS).map(([name, inputSchema]) => ({
    name,
    description: TOOL_DESCRIPTIONS[name],
    inputSchema: inputSchema as any,
    outputSchema: {
      type: "object",
      properties: {
        status: { type: "string" },
        schema_version: { type: "string" },
      },
      required: ["status", "schema_version"],
      additionalProperties: true,
    },
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
      openWorldHint: true,
    },
  })),
}));
server.setRequestHandler(CallToolRequestSchema, async (request, extra) => {
  try {
    const ctx = { ...selectedContext(state), signal: extra.signal };
    const result = await sourceTool(
      ctx,
      request.params.name,
      request.params.arguments ?? {},
    );
    return {
      content: [{ type: "text", text: JSON.stringify(result) }],
      structuredContent: result,
    };
  } catch {
    return {
      isError: true,
      content: [
        {
          type: "text",
          text: "Source request unavailable; inspect native integrations status.",
        },
      ],
      structuredContent: {
        schema_version: "1",
        status: "unavailable",
        reason: "native_status_required",
      },
    };
  }
});
await server.connect(new StdioServerTransport());
