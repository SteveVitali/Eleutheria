// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.20 (UXK0-4, K3's SRCH-05 posture) — the pure matcher half of
 * `<sig-typeahead>`.
 *
 * Suggestions come only from committed static shards — one JSON file per
 * key prefix under the route's `shard-root` — never a live-spine read. The
 * shard contract (`sig.typeahead-shard/1`) is deliberately small: a label,
 * an optional kind tag, and the destination href. P36.40 owns producing the
 * real shards; this model is the shell they feed.
 */

export interface TypeaheadEntry {
  /** Display text — matched against the query. */
  label: string;
  /** Optional kind tag shown beside the label (source, place, term, …). */
  kind?: string;
  /** Optional context line — level, parent and count for a place; the
   *  suggestion never leads with a raw code (P34.14). */
  detail?: string;
  /** Alternate names the shard builder may key the entry under — matched
   *  like `label` but never rendered. */
  alt?: string[];
  /** The destination the option navigates to. */
  href: string;
  /**
   * P36.56 (SRCH-06 scope): a place entry's canonical jurisdiction key and
   * its root-first ancestor chain (self last — the same ancestry
   * `jurisdiction_chain` records). A `jurisdiction:<jkey>` scope matches an
   * entry when the scope key sits in this chain — the place itself and its
   * descendants, never a guessed ancestry.
   */
  jkey?: string;
  chain?: string[];
  /** P36.56: a source entry's registry id — `source:<id>` scope key. */
  source_id?: string;
}

export interface TypeaheadShard {
  schema: "sig.typeahead-shard/1";
  /** The prefix key this shard answers (lowercase alnum). */
  key: string;
  /**
   * P36.40: `true` on a shard whose bucket split one character deeper —
   * the shard carries a bounded representative set and a query whose
   * first run is longer than this key refetches the deeper shard for the
   * full set.
   */
  deeper?: boolean;
  /**
   * `true` on a terminal shard that could not be split any further and
   * keeps only the entries that fit — dropped multi-key entries stay
   * reachable through their other word-start shards.
   */
  truncated?: boolean;
  entries: TypeaheadEntry[];
}

/** Structural check — a malformed shard fails closed, never half-parses. */
export function isShard(doc: unknown): doc is TypeaheadShard {
  if (typeof doc !== "object" || doc === null) return false;
  const d = doc as Record<string, unknown>;
  if (d.schema !== "sig.typeahead-shard/1") return false;
  if (typeof d.key !== "string" || !/^[a-z0-9]+$/.test(d.key)) return false;
  if (!Array.isArray(d.entries)) return false;
  return d.entries.every(
    (e) =>
      typeof e === "object" &&
      e !== null &&
      typeof (e as Record<string, unknown>).label === "string" &&
      typeof (e as Record<string, unknown>).href === "string",
  );
}

/**
 * The shard a query resolves to: the first alphanumeric run, lowercased,
 * truncated to `keyLen`. "Austin" → "au"; "3rd" → "3r" (a one-char run pads
 * itself so a single character never scans the whole index).
 */
export function shardKey(query: string, keyLen = 2): string | null {
  const run = /^[a-z0-9]+/i.exec(query.trim());
  if (!run) return null;
  const key = run[0].toLowerCase();
  return (key + key.slice(-1).repeat(Math.max(0, keyLen - key.length))).slice(
    0,
    keyLen,
  );
}

/**
 * P36.56 (SRCH-06) — the `<sig-typeahead>` `scope` attribute:
 * `jurisdiction:<jkey>` keeps only the place whose chain holds the scope
 * key (the place itself and its descendants — `jurisdiction_chain`
 * semantics); `source:<id>` keeps the named source entry. Anything
 * unparseable scopes to nothing rather than widening — the element simply
 * falls back to the complete no-JS form submit.
 */
export function scopeMatches(
  entry: TypeaheadEntry,
  scope: string | null,
): boolean {
  const m = scope == null ? null : /^(\w+):(.+)$/.exec(scope);
  if (m === null) return true;
  return m[1] === "jurisdiction"
    ? (entry.chain ?? (entry.jkey ? [entry.jkey] : [])).includes(m[2]!)
    : m[1] === "source" && entry.source_id === m[2];
}

/**
 * Rank entries for a query: a label-word prefix beats a bare substring;
 * ties keep shard order (the shard's own ranking). Alternates (`alt`)
 * match like the label but never render — "OKC" still surfaces "Oklahoma
 * City". The caller slices to its cap — matching never reorders beyond
 * these classes.
 */
export function matchEntries(
  entries: TypeaheadEntry[],
  query: string,
): TypeaheadEntry[] {
  const q = query.trim().toLowerCase();
  if (q === "") return [];
  const score = (label: string): number => {
    const l = label.toLowerCase();
    if (l.split(/\s+/).some((w) => w.startsWith(q))) return 0;
    if (l.includes(q)) return 1;
    return -1;
  };
  const scoreEntry = (entry: TypeaheadEntry): number => {
    let s = score(entry.label);
    // An alternate only ever HELPS — a non-matching alt must never demote a
    // label that matched (P36.56 fix: `min(s, -1)` dropped every entry whose
    // code alt — "US", "OK" — missed the query).
    for (const alt of entry.alt ?? []) {
      const a = score(alt);
      if (a >= 0) s = Math.min(s === -1 ? 2 : s, a);
    }
    return s;
  };
  return entries
    .map((entry, i) => ({ entry, i, s: scoreEntry(entry) }))
    .filter((x) => x.s >= 0 && x.s < 2)
    .sort((a, b) => a.s - b.s || a.i - b.i)
    .map((x) => x.entry);
}
