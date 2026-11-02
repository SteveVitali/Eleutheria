// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.40 (K3 SRCH-05 / SIG-SRCH-010, UXR-23 shared shards; cites SIG-UI-073)
 * — the ONE typeahead shard catalog and builder. Every `<sig-typeahead>`
 * mount point — the site header, the home hero, the `/search/` corpus form,
 * the dossier-index place form, and (when their rows land) the map place
 * search and the explorer's search-to-node — names the SAME shard root below
 * and reads the same emitted `sig.typeahead-shard/1` documents. The shared-
 * shards conformance test (`tests/unit/typeahead-shards.test.ts`) fails on
 * any mount point that names a different root.
 *
 * The catalog is NAMED THINGS only (K3 §2.4 sets A/C — records never enter
 * the typeahead): places from the grouped dossier index, source registry
 * rows, and the technology labels the site corpus declares. Organisations
 * join when the `/entity/` surfaces ship (GX-06a — an entry must link an
 * existing page, R-6). The data layer is release-pinned in export mode, so
 * the emitted set is per-release by construction (SIG-UI-076).
 *
 * Sharding is word-start (K3 §2.4): an entry lands under the first two
 * alphanumeric characters of EVERY word of its label and alternates —
 * "Austin Police Department" reaches the `au`, `po` and `de…` shards
 * (minus SHARD_KEY_STOP_WORDS). A bucket whose serialized shard would
 * exceed SHARD_SPLIT_BYTES splits to one character deeper, recursively; a
 * bucket that cannot be reduced any further (every remaining entry shares
 * the whole key prefix — splitting changes nothing) emits a `truncated`
 * shard instead: entries whose only key path runs through this prefix are
 * kept first, and multi-key entries are dropped because they stay
 * reachable through their OTHER word-start shards. A post-build coverage
 * check proves every catalog entry survives in at least one shard — a
 * loss fails the build, it is never emitted silently.
 */

import { getDossierIndex, getMapSites, getSourceRows } from "./data";
import { dossierDisplayTitle } from "./jurisdictions";
import { dossierPath } from "./dossier";
import { withBase } from "./paths";
import type { TypeaheadEntry, TypeaheadShard } from "../elements/typeahead-model";

/**
 * The one shard root every consumer names (route-relative — callers apply
 * `withBase`). Change it in ONE place: the conformance test scans every
 * `shard-root=` mount point and fails on divergence (UXR-23).
 */
export const TYPEAHEAD_SHARD_ROOT = "search/shards/";

/**
 * The function words K3 §2.4 excludes from shard keys (the draft's own
 * enumeration — its largest measured shards were `de` and `at_`; a query is
 * keyed on its first alphanumeric run, so a word a reader types first is
 * never a shard key either way).
 */
export const SHARD_KEY_STOP_WORDS: readonly string[] = ["at", "de", "&"];

/** A shard over this serialized size splits one character deeper (K3 §2.4's ~24 KiB posture). */
export const SHARD_SPLIT_BYTES = 24 * 1024;

/** The ratified per-shard bound (SIG-SRCH-010): no emitted shard may exceed it. */
export const SHARD_MAX_BYTES = 50 * 1024;

/** The entries a `deeper` shard keeps for queries shorter than its children. */
export const DEEPER_SHARD_CAP = 40;

/** Deepest key length the splitter explores — past this a bucket goes terminal. */
const MAX_KEY_LEN = 8;

export interface TypeaheadCatalogEntry extends TypeaheadEntry {
  /** Alternate names the entry also keys under (never rendered). */
  alt?: string[];
}

/**
 * The typeahead catalog — the named things of the release-pinned corpus.
 * Every entry links an existing page of its kind in this release (R-6):
 * places → dossiers, sources → the registry surface, technologies → the
 * scoped corpus search (the `technology` workspace parameter).
 */
export function typeaheadCatalog(): TypeaheadCatalogEntry[] {
  const entries: TypeaheadCatalogEntry[] = [];
  for (const d of getDossierIndex()) {
    const label = d.display_name ?? d.name ?? dossierDisplayTitle(d.subject_label, d.jurisdiction);
    const detail = [
      d.level ? d.level.replace(/_/g, " ") : "place",
      typeof d.records === "number" ? `${d.records} record${d.records === 1 ? "" : "s"}` : null,
      d.parent_name ? `in ${d.parent_name}` : null,
    ]
      .filter((s): s is string => s !== null)
      .join(" · ");
    entries.push({
      label,
      kind: "place",
      href: withBase(dossierPath(d.slug_path ?? d.slug)),
      detail,
      alt: [d.subject_label, d.jurisdictionCode ?? ""].filter(
        (s): s is string => typeof s === "string" && s !== "" && s !== label,
      ),
    });
  }
  for (const s of getSourceRows().sources) {
    const label = s.name ?? s.source_id;
    entries.push({
      label,
      kind: "source",
      href: withBase("sources/"),
      detail:
        s.lifecycle_state === "published"
          ? "registry source"
          : `registry source (${s.lifecycle_state.replace(/_/g, " ")})`,
      alt: s.source_id !== label ? [s.source_id] : [],
    });
  }
  const tech = new Set<string>();
  for (const site of getMapSites()) {
    if (site.technology && site.technology !== "unreported") tech.add(site.technology);
  }
  for (const slug of [...tech].sort()) {
    entries.push({
      label: slug,
      kind: "technology",
      href: withBase(`search/?technology=${encodeURIComponent(slug)}`),
      detail: "technology — records classified under it",
    });
  }
  return entries;
}

/** The `len`-character word-start keys one name keys under (stop words excluded). */
function wordKeys(name: string, len: number): Set<string> {
  const keys = new Set<string>();
  for (const word of name.toLowerCase().split(/[^a-z0-9]+/)) {
    if (word === "" || SHARD_KEY_STOP_WORDS.includes(word)) continue;
    keys.add((word + word.slice(-1).repeat(len)).slice(0, len));
  }
  return keys;
}

/** Every `len`-char key an entry lands under across label + alternates. */
function entryKeys(entry: TypeaheadCatalogEntry, len: number): Set<string> {
  const keys = new Set<string>();
  for (const name of [entry.label, ...(entry.alt ?? [])]) {
    for (const k of wordKeys(name, len)) keys.add(k);
  }
  return keys;
}

/**
 * The shard keys a label keys under at the base two-character depth —
 * exported for the conformance test and shared with the element's own
 * `shardKey` padding rule.
 */
export function shardKeysForLabel(label: string): Set<string> {
  return wordKeys(label, 2);
}

const serialize = (key: string, entries: TypeaheadEntry[], extra?: { deeper?: boolean; truncated?: boolean }): TypeaheadShard => ({
  schema: "sig.typeahead-shard/1",
  key,
  ...(extra?.deeper === true ? { deeper: true } : {}),
  ...(extra?.truncated === true ? { truncated: true } : {}),
  entries,
});

const shardBytes = (shard: TypeaheadShard): number => JSON.stringify(shard).length;

/** Number of distinct two-char homes an entry has — 1 means this prefix path is its only way to be found. */
function homeCount(entry: TypeaheadCatalogEntry): number {
  return entryKeys(entry, 2).size;
}

/**
 * Emit shard(s) for `bucket`, the entries keyed under `key` (length `len`).
 * Over SHARD_SPLIT_BYTES the bucket splits one character deeper and the
 * parent shard keeps DEEPER_SHARD_CAP representatives marked `deeper`.
 * When splitting can no longer reduce the bucket (every entry shares the
 * same next-level key, or the depth cap is hit) the shard goes terminal:
 * entries whose ONLY two-char home is this prefix are kept first, then the
 * rest fills what fits — dropped multi-key entries stay reachable through
 * their other word-start shards, which the post-build coverage check
 * verifies over the whole emitted set.
 */
function emitBucket(
  shards: Map<string, TypeaheadShard>,
  bucket: TypeaheadCatalogEntry[],
  key: string,
  len: number,
): void {
  if (shardBytes(serialize(key, bucket)) <= SHARD_SPLIT_BYTES) {
    shards.set(key, serialize(key, bucket));
    return;
  }
  const sub = new Map<string, TypeaheadCatalogEntry[]>();
  if (len < MAX_KEY_LEN) {
    for (const entry of bucket) {
      for (const k of entryKeys(entry, len + 1)) {
        if (!k.startsWith(key)) continue;
        const b = sub.get(k) ?? [];
        b.push(entry);
        sub.set(k, b);
      }
    }
  }
  const monolithic = sub.size === 1 && sub.values().next().value!.length === bucket.length;
  if (sub.size > 1 || (sub.size === 1 && !monolithic)) {
    shards.set(key, serialize(key, bucket.slice(0, DEEPER_SHARD_CAP), { deeper: true }));
    for (const k of [...sub.keys()].sort()) {
      emitBucket(shards, sub.get(k)!, k, len + 1);
    }
    return;
  }
  // Terminal bucket: deeper keys cannot divide it. Keep single-home entries
  // first (they are reachable ONLY through this prefix), then fill what fits;
  // dropped multi-key entries stay reachable through their other shards.
  const order = new Map<TypeaheadCatalogEntry, number>(bucket.map((e, i) => [e, i]));
  const ordered = [...bucket].sort(
    (a, b) => homeCount(a) - homeCount(b) || order.get(a)! - order.get(b)!,
  );
  const kept: TypeaheadCatalogEntry[] = [];
  let bytes = shardBytes(serialize(key, []));
  for (const entry of ordered) {
    const add = JSON.stringify(entry).length + 1;
    if (bytes + add > SHARD_MAX_BYTES) break;
    bytes += add;
    kept.push(entry);
  }
  const mustKeep = ordered.filter((e) => homeCount(e) === 1);
  if (mustKeep.some((e) => !kept.includes(e))) {
    throw new Error(
      `typeahead shard "${key}" cannot fit its single-home entries inside the ratified ` +
        `${SHARD_MAX_BYTES} B bound (SIG-SRCH-010) — the catalog needs a different sharding rule, not a bigger bound`,
    );
  }
  shards.set(key, serialize(key, kept, { truncated: kept.length < bucket.length }));
}

/**
 * Build the full emitted shard set — deterministic (stable catalog order,
 * stable key iteration). Throws when any catalog entry would be left
 * unreachable in every shard: an emitted set that loses named things is a
 * build failure, not a quiet degradation (SIG-ENG-042).
 */
export function buildTypeaheadShards(
  catalog: TypeaheadCatalogEntry[] = typeaheadCatalog(),
): Map<string, TypeaheadShard> {
  const buckets = new Map<string, TypeaheadCatalogEntry[]>();
  for (const entry of catalog) {
    for (const key of entryKeys(entry, 2)) {
      const bucket = buckets.get(key) ?? [];
      bucket.push(entry);
      buckets.set(key, bucket);
    }
  }
  const shards = new Map<string, TypeaheadShard>();
  for (const key of [...buckets.keys()].sort()) {
    emitBucket(shards, buckets.get(key)!, key, 2);
  }
  const covered = new Set<TypeaheadCatalogEntry>();
  for (const shard of shards.values()) {
    for (const e of shard.entries) covered.add(e as TypeaheadCatalogEntry);
  }
  const lost = catalog.filter((e) => !covered.has(e));
  if (lost.length > 0) {
    throw new Error(
      `typeahead shards lost ${lost.length} catalog entr${lost.length === 1 ? "y" : "ies"} ` +
        `(first: "${lost[0].label}") — splitting must keep every named thing reachable`,
    );
  }
  return shards;
}

/** The sorted emitted keys — `getStaticPaths` and the conformance test share it. */
export function typeaheadShardKeys(): string[] {
  return [...buildTypeaheadShards().keys()].sort();
}
