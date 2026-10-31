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
 * (minus SHARD_KEY_STOP_WORDS). A bucket whose serialized shard
 * would exceed SHARD_SPLIT_BYTES splits to three-character keys and its
 * two-character shard is re-emitted with `deeper: true` plus a bounded
 * representative set, so a two-character query still gets suggestions and a
 * longer query refetches the full three-character shard.
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

/** A shard over this serialized size splits to three-character keys (K3 §2.4's 24 KiB gzip posture). */
export const SHARD_SPLIT_BYTES = 24 * 1024;

/** The ratified per-shard bound (SIG-SRCH-010): no emitted shard may exceed it — a violation fails the build. */
export const SHARD_MAX_BYTES = 50 * 1024;

/** The entries a `deeper` two-char shard keeps for two-character queries (bounded representative set). */
export const DEEPER_SHARD_CAP = 40;

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

/**
 * The shard keys a label keys under: the first two alphanumeric characters
 * of every word, lowercased — minus the K3 stop words. Words shorter than
 * two characters pad with their last character (the element's `shardKey`
 * pads identically, so "3" reaches the `33` shard).
 */
export function shardKeysForLabel(label: string): Set<string> {
  const keys = new Set<string>();
  for (const word of label.toLowerCase().split(/[^a-z0-9]+/)) {
    if (word === "" || SHARD_KEY_STOP_WORDS.includes(word)) continue;
    keys.add((word + word.slice(-1)).slice(0, 2));
  }
  return keys;
}

const serialize = (key: string, entries: TypeaheadEntry[], deeper?: boolean): TypeaheadShard => ({
  schema: "sig.typeahead-shard/1",
  key,
  ...(deeper === true ? { deeper: true } : {}),
  entries,
});

const shardBytes = (shard: TypeaheadShard): number => JSON.stringify(shard).length;

/**
 * Build the full emitted shard set — deterministic (stable catalog order,
 * stable key iteration). Buckets past SHARD_SPLIT_BYTES split to
 * three-character keys; a three-character shard that would still exceed
 * SHARD_MAX_BYTES throws — SIG-ENG-042, the build fails before an
 * over-budget artifact ever ships.
 */
export function buildTypeaheadShards(
  catalog: TypeaheadCatalogEntry[] = typeaheadCatalog(),
): Map<string, TypeaheadShard> {
  const buckets = new Map<string, TypeaheadCatalogEntry[]>();
  for (const entry of catalog) {
    const keys = new Set<string>();
    for (const name of [entry.label, ...(entry.alt ?? [])]) {
      for (const k of shardKeysForLabel(name)) keys.add(k);
    }
    for (const key of keys) {
      const bucket = buckets.get(key) ?? [];
      bucket.push(entry);
      buckets.set(key, bucket);
    }
  }

  const shards = new Map<string, TypeaheadShard>();
  for (const key of [...buckets.keys()].sort()) {
    const bucket = buckets.get(key)!;
    if (shardBytes(serialize(key, bucket)) <= SHARD_SPLIT_BYTES) {
      shards.set(key, serialize(key, bucket));
      continue;
    }
    // Over the split threshold — three-character keys per word-start, and the
    // two-char shard keeps a bounded representative set marked `deeper`.
    const deep = new Map<string, TypeaheadCatalogEntry[]>();
    for (const entry of bucket) {
      const keys3 = new Set<string>();
      for (const name of [entry.label, ...(entry.alt ?? [])]) {
        for (const word of name.toLowerCase().split(/[^a-z0-9]+/)) {
          if (word === "" || SHARD_KEY_STOP_WORDS.includes(word)) continue;
          const k2 = (word + word.slice(-1)).slice(0, 2);
          if (k2 !== key) continue;
          keys3.add((word + word.slice(-1).repeat(2)).slice(0, 3));
        }
      }
      for (const k3 of keys3) {
        const b = deep.get(k3) ?? [];
        b.push(entry);
        deep.set(k3, b);
      }
    }
    for (const k3 of [...deep.keys()].sort()) {
      const shard = serialize(k3, deep.get(k3)!);
      if (shardBytes(shard) > SHARD_MAX_BYTES) {
        throw new Error(
          `typeahead shard "${k3}" would serialize to ${shardBytes(shard)} B — ` +
            `over the ratified ≤ ${SHARD_MAX_BYTES} B bound (SIG-SRCH-010); split the catalog, never the bound`,
        );
      }
      shards.set(k3, shard);
    }
    shards.set(key, serialize(key, bucket.slice(0, DEEPER_SHARD_CAP), true));
  }
  return shards;
}

/** The sorted emitted keys — `getStaticPaths` and the conformance test share it. */
export function typeaheadShardKeys(): string[] {
  return [...buildTypeaheadShards().keys()].sort();
}
