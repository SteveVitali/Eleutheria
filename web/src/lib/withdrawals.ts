// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
/**
 * Publication withdrawals — the committed, engineered suppression list
 * (P34.19, F-337, SIG-GOV-007).
 *
 * The single source of truth is the policy data table
 * `policy/src/policy/data/publication_withdrawals.json`
 * (`sig.publication-withdrawals/1`): the claims/entities that leave every
 * public artifact — leak-provenance refusals like the nine F-337 Atlas
 * face-recognition rows (the BuzzFeed Clearview article whose agency data
 * came from unnamed-source internal documents, the same class
 * `wired_shotspotter_leak` is refused under).
 *
 * The export writer, the API read surface and these export-mode web readers
 * all match this ONE list so every public layer suppresses identically.
 * Matching is fail-closed: `candidate_claim_ids` suppress alongside
 * `claim_ids` until a host-side rerun narrows them (see `D-P34.19-1` in
 * `docs/tickets/DEFERRALS.md`).
 */
// The committed table is bundled at build time: a static JSON import is
// resolved by the bundler against the SOURCE tree (`web/src/lib/` → repo
// root), so it survives the prerender chunking that relocates runtime
// `import.meta.url` into `dist/.prerender/chunks/` (a `readFileSync`
// resolved there misses — the composed export-mode build fails closed).
// The bytes still come from the ONE shared committed file, never a copy.
import withdrawalsTableJson from "../../../policy/src/policy/data/publication_withdrawals.json";

const WITHDRAWALS_SCHEMA = "sig.publication-withdrawals/1";

export interface WithdrawalEntry {
  upstream_id: string;
  source_id: string;
  agency?: string;
  agency_jurisdiction?: string;
  predicate?: string;
  raw_value?: string;
  entity_id: string;
  claim_ids: string[];
  candidate_claim_ids?: string[];
  tainted_locator?: string;
  reason: string;
  authority?: string;
  disposition?: string;
  kind?: string;
  note?: string;
}

interface WithdrawalsTable {
  schema: string;
  withdrawals: WithdrawalEntry[];
}

let cached: WithdrawalsTable | null = null;

function loadTable(): WithdrawalsTable {
  if (cached) return cached;
  const parsed = withdrawalsTableJson as WithdrawalsTable;
  if (parsed?.schema !== WITHDRAWALS_SCHEMA || !Array.isArray(parsed.withdrawals)) {
    throw new Error(
      `policy/src/policy/data/publication_withdrawals.json: not a valid ${WITHDRAWALS_SCHEMA} table`,
    );
  }
  cached = parsed;
  return parsed;
}

/** Every withdrawal entry, in table order (append-only). */
export function withdrawalEntries(): WithdrawalEntry[] {
  return [...loadTable().withdrawals];
}

/** The suppressed claim ids (`claim_ids` + `candidate_claim_ids`, fail-closed). */
export function withdrawnClaimIds(): Set<string> {
  const out = new Set<string>();
  for (const e of loadTable().withdrawals) {
    for (const id of e.claim_ids ?? []) out.add(id);
    for (const id of e.candidate_claim_ids ?? []) out.add(id);
  }
  return out;
}

/** The suppressed subject-entity ids. */
export function withdrawnEntityIds(): Set<string> {
  return new Set(loadTable().withdrawals.map((e) => e.entity_id));
}

/** The suppressed upstream record ids (e.g. Atlas `AOS*`). */
export function withdrawnUpstreamIds(): Set<string> {
  return new Set(loadTable().withdrawals.map((e) => e.upstream_id));
}

/** Every suppressed id, whatever its kind. */
export function withdrawnIds(): Set<string> {
  return new Set([...withdrawnClaimIds(), ...withdrawnEntityIds(), ...withdrawnUpstreamIds()]);
}

export function isWithdrawn(id: string | undefined | null): boolean {
  return !!id && withdrawnIds().has(id);
}

/** The entry suppressing `id` (any id kind), or undefined. */
export function withdrawalFor(id: string | undefined | null): WithdrawalEntry | undefined {
  if (!id) return undefined;
  return loadTable().withdrawals.find(
    (e) =>
      id === e.entity_id ||
      id === e.upstream_id ||
      (e.claim_ids ?? []).includes(id) ||
      (e.candidate_claim_ids ?? []).includes(id),
  );
}

/** The record fields an export-mode payload may be keyed on. A row whose value
 *  under any of these names equals a suppressed id is dropped — `id` covers
 *  the map surface's `MapAsset.id` (an entity id); `previous_claim_id` covers
 *  the corrections log's revision pointer. */
const WITHDRAWN_KEY_NAMES = [
  "id",
  "claim_id",
  "claimId",
  "previous_claim_id",
  "entity_id",
  "entityId",
  "subject_id",
  "subjectId",
  "upstream_id",
  "upstreamId",
] as const;

/**
 * Drop every row carrying a suppressed id under a recognised key name
 * (`claim_id`, `entity_id`, `subject_id`, `upstream_id`, `id`, …). Rows
 * without a matching key pass through — the withdrawal is the *claim*, never
 * the agency's whole record.
 */
export function dropWithdrawn<T>(rows: readonly T[]): T[] {
  const ids = withdrawnIds();
  if (ids.size === 0) return [...rows];
  return rows.filter((row) => {
    if (row === null || typeof row !== "object") return true;
    const rec = row as Record<string, unknown>;
    for (const key of WITHDRAWN_KEY_NAMES) {
      const value = rec[key];
      if (typeof value === "string" && ids.has(value)) return false;
    }
    return true;
  });
}
