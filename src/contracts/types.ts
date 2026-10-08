/** JSON metadata remains extensible at the type boundary; schemas validate it on disk. */
export type Metadata = Record<string, any>;
export interface Change {
  path: string;
  if_revision: string | null;
  document: string;
}
export interface Proposal {
  contract_version: "2";
  vault_root: string;
  vault_id: string;
  purpose: string;
  records: Change[];
  dependencies: Record<string, string | null>;
  ingestion?: Metadata;
}
export interface RuntimeContext {
  vault: string;
  state: string;
  now?: string;
  signal?: AbortSignal;
}
export interface Observation {
  path: string;
  document: string;
  frontmatter: Metadata;
  body: string;
  revision: string;
}
export interface Diagnostic {
  code: string;
  path?: string;
  field?: string;
  message?: string;
  severity?: string;
}
export const MODALITIES = [
  "analytical",
  "kinetic",
  "synthesis",
  "administrative",
] as const;
export const MAX_REQUEST_BYTES = 4 * 1024 * 1024;
export const MAX_RECORDS = 500;
