import { digest } from "../../platforms/filesystem.ts";
import { dateOnly } from "../../time/timezone.ts";
import { accessToken } from "../auth/google.ts";
import { providerJSON } from "../http.ts";
import { requestBudget } from "../profile.ts";
import { observation, TASKS_SCOPE } from "../contracts.ts";
import type { Instance, ProviderPorts } from "../contracts.ts";
import type { RuntimeContext, Metadata } from "../../contracts/types.ts";

export async function readTasks(
  ctx: RuntimeContext,
  instance: Instance,
  ports: ProviderPorts,
  args: Metadata,
  lists = false,
) {
  if (
    instance.provider !== "google-tasks" ||
    !instance.scopes.includes(TASKS_SCOPE)
  )
    throw Error("provider_scope_missing");
  if (!lists && !instance.list_ids.includes(args.list_id))
    throw Error("inbox_not_authorized");
  const token = await accessToken(ctx, instance, ports.secrets);
  const credentials = await ports.secrets.get(instance.secret_id);
  if (!credentials?.google_subject) throw Error("provider_reconnect_required");
  const url = new URL(
    lists
      ? "https://tasks.googleapis.com/tasks/v1/users/@me/lists"
      : "https://tasks.googleapis.com/tasks/v1/lists/" +
        encodeURIComponent(args.list_id) +
        "/tasks",
  );
  url.searchParams.set("maxResults", String(args.page_size ?? 100));
  url.searchParams.set(
    "fields",
    lists
      ? "nextPageToken,items(id,title)"
      : "nextPageToken,items(id,title,due,status,updated,etag,parent,links,deleted,hidden)",
  );
  if (args.cursor) url.searchParams.set("pageToken", args.cursor);
  if (!lists) {
    url.searchParams.set("showCompleted", String(!!args.include_completed));
    url.searchParams.set("showHidden", String(!!args.include_completed));
    url.searchParams.set("showDeleted", "true");
  }
  let result: Metadata;
  if (args.selected_ids) {
    if (lists || args.cursor) throw Error("selected_details_cannot_page");
    const items: Metadata[] = [],
      failed: Metadata[] = [];
    for (let offset = 0; offset < args.selected_ids.length; offset += 4) {
      const group = await Promise.allSettled(
        args.selected_ids.slice(offset, offset + 4).map(async (id: string) => {
          const one = new URL(
            url.origin + url.pathname + "/" + encodeURIComponent(id),
          );
          one.search = "";
          one.pathname = url.pathname + "/" + encodeURIComponent(id);
          one.searchParams.set(
            "fields",
            "id,title,notes,due,status,updated,etag,parent,links,deleted,hidden",
          );
          await requestBudget(ctx, instance);
          return providerJSON(ctx, ports, one.href, {
            headers: { Authorization: "Bearer " + token },
          });
        }),
      );
      group.forEach((r, index) =>
        r.status === "fulfilled"
          ? items.push(r.value)
          : failed.push({
              id: args.selected_ids[offset + index],
              reason: "item_unavailable",
            }),
      );
    }
    result = { items, failed };
  } else {
    await requestBudget(ctx, instance);
    result = await providerJSON(ctx, ports, url.href, {
      headers: { Authorization: "Bearer " + token },
    });
  }
  const rows = result.items ?? [];
  if (
    !Array.isArray(rows) ||
    rows.length > 100 ||
    (result.nextPageToken &&
      (typeof result.nextPageToken !== "string" ||
        result.nextPageToken.length > 500))
  )
    throw Error("provider_invalid_response");
  const items: Metadata[] = [],
    omitted: Metadata[] = result.failed ?? [];
  for (const row of rows) {
    if (
      typeof row.id !== "string" ||
      row.id.length > 500 ||
      (!row.deleted &&
        (typeof row.title !== "string" || row.title.length > 500))
    )
      throw Error("provider_invalid_response");
    if (lists) {
      items.push({ id: row.id, title: row.title });
      continue;
    }
    if (row.deleted || row.parent || row.links?.length) {
      omitted.push({
        id: row.id,
        reason: row.deleted
          ? "deleted_preserve_local"
          : "unsupported_relationship_review",
      });
      continue;
    }
    if (
      row.notes &&
      (typeof row.notes !== "string" || Buffer.byteLength(row.notes) > 16384)
    )
      throw Error("provider_invalid_response");
    const due = row.due
      ? dateOnly(String(row.due).slice(0, 10)).toString()
      : null;
    if (!["needsAction", "completed"].includes(row.status))
      throw Error("provider_invalid_response");
    items.push({
      content_kind: "structured_task",
      integration: "google-tasks",
      account_scope: digest(credentials.google_subject),
      collection_id: args.list_id,
      external_item_id: row.id,
      external_revision: row.updated ?? row.etag ?? null,
      observation_digest: digest(row),
      payload: {
        title: row.title,
        notes: row.notes ?? "",
        due,
        external_status: row.status,
      },
    });
  }
  const next = result.nextPageToken ?? null;
  return observation(
    ctx,
    instance,
    lists ? "ingestion.discover" : "ingestion.read",
    {
      status: items.length ? "ok" : "empty",
      coverage: {
        complete: !next && !omitted.length,
        next_cursor: next,
        omitted,
      },
      ...(lists
        ? { items }
        : !args.selected_ids
          ? {
              items: items.map((i) => ({
                content_kind: "structured_task_summary",
                external_item_id: i.external_item_id,
                external_revision: i.external_revision,
                title: i.payload.title,
                due: i.payload.due,
                status: i.payload.external_status,
              })),
              detail_selection_required: true,
            }
          : {
              envelope: {
                contract_version: "2",
                source_alias: instance.id,
                integration: instance.provider,
                access_mode: "read-only",
                discovery_status:
                  next || omitted.length
                    ? "partial_listing"
                    : items.length
                      ? "ok_items_available"
                      : "ok_empty",
                capabilities: { write_back_supported: false },
                pagination: {
                  bounded: true,
                  next_page_token: next,
                  truncated: !!next || !!omitted.length,
                },
                items,
              },
            }),
    },
  );
}
