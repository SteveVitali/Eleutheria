// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.56 (K3 SRCH-06 / SIG-UI-128; cites SIG-SRCH-009, SIG-UI-059) — the
 * scoped-search helpers behind the dossier "Search within <place>" and the
 * source-page "Search this source" GET forms.
 *
 * The forms are plain zero-JS GETs onto the release-pinned federated search
 * route (`/v1/releases/<pub>/search?format=html`) — the same server-rendered
 * no-JS results page the `/search/` corpus form already targets (P36.38/39).
 * The scope is carried by the contract parameters:
 *
 * - `jurisdiction=<jkey>` — the dossier's canonical placement key. Per
 *   SIG-UI-059 the parameter is "a filter including descendants" — the
 *   record's `jurisdiction_chain` decides membership, so one key scopes to
 *   the place AND its descendants by contract. The v2 engine's current
 *   leaf-exact application (records where `place_key` equals the key) is the
 *   engine-side gap D-P36.56-1 records; the form emits the contract
 *   parameter, never a workaround that would silently mis-scope (a repeated
 *   `jurisdiction=` collapses to one value on the single-value route, and
 *   `within=` is dropped without a typed refusal today).
 * - `source=<id>` — the registry source id; exact by contract.
 *
 * When no release is activated the caller renders the named-empty state —
 * never a form without a real target.
 */

import { getDossierIndex } from "./data";

export interface ScopedSearchScope {
  /** The facet the GET form carries — `jurisdiction` or `source`. */
  param: "jurisdiction" | "source";
  /** The facet value — the canonical jkey or the registry source id. */
  value: string;
  /** The display name the button + label use (never a bare id). */
  label: string;
}

/**
 * The `scope` attribute value `<sig-typeahead>` reads on a scoped form —
 * `jurisdiction:<jkey>` or `source:<id>`. One grammar shared by the
 * component, the element and the tests.
 */
export function typeaheadScopeValue(scope: ScopedSearchScope): string {
  return `${scope.param}:${scope.value}`;
}

/**
 * The hidden-input pair a scoped form emits — one pair, the contract
 * parameter (see the module doc: multi-`jurisdiction` is never emitted).
 */
export function scopedSearchParam(scope: ScopedSearchScope): {
  name: string;
  value: string;
} {
  return { name: scope.param, value: scope.value };
}

/**
 * The root-first ancestor chain for `jkey` — self last — walked through the
 * dossier index's `parent_jkey` links (the same ancestry `jurisdiction_chain`
 * records per record). Unknown jkeys yield `[jkey]` (self-only); a cycle or a
 * missing parent stops at the last resolvable ancestor rather than looping —
 * the emitted chain only ever contains real index keys.
 */
export function jkeyChain(
  jkey: string,
  rows: ReturnType<typeof getDossierIndex> = getDossierIndex(),
): string[] {
  const byKey = new Map<string, (typeof rows)[number]>();
  for (const r of rows) {
    if (r.jkey) byKey.set(r.jkey, r);
  }
  const chain: string[] = [];
  const seen = new Set<string>();
  let cur: string | null | undefined = jkey;
  while (cur && !seen.has(cur)) {
    seen.add(cur);
    chain.unshift(cur);
    cur = byKey.get(cur)?.parent_jkey ?? null;
  }
  return chain;
}

/** Every jkey in `jkey`'s subtree — self + all descendants in the index. */
export function jkeySubtree(
  jkey: string,
  rows: ReturnType<typeof getDossierIndex> = getDossierIndex(),
): string[] {
  const out: string[] = [];
  for (const r of rows) {
    if (!r.jkey) continue;
    if (jkeyChain(r.jkey, rows).includes(jkey)) out.push(r.jkey);
  }
  return out;
}
