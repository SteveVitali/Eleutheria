// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.29 (K6 VIZ-04, SIG-UI-127) — the build-side half of the dossier's
 * in-place map activation: the per-dossier props document
 * (`dossier/<slug>/map-embed.json`) that `<sig-activate>` fetches ONLY after
 * the reader's explicit click. It serialises the SAME island-prop contract
 * `/map/` hands `MapIsland` — one props shape, one resolution — plus the
 * embedded context (`embedded.jkey` seeds the jurisdiction facet so the
 * activated box draws the same records the static figure does, SIG-UI-132;
 * `embedded.placeLabel`; `embedded.publicationId` for "Cite this view").
 *
 * The fixtures-mode `records` payload is the dossier's OWN resolved sites
 * list — `buildSitesModel`'s one-resolution rows for this slug — projected
 * to `MapRecord` exactly as map.astro does; the tile path (export builds)
 * carries the compartment archives and the dict instead. The document holds
 * the dossier's restricted-visuals-derived facts only insofar as the
 * published surfaces already carry them — nothing per-area beyond the
 * published record points (SIG-UI-134).
 *
 * Build-time only — nothing here may reach a shipped JS chunk.
 */

import {
  dataSource,
  getDossierIndex,
  getDossiers,
  getJurisdictionFrames,
  getJurisdictionKeyMap,
  getJurisdictionSlugPaths,
  getLatestReleaseTarget,
  getMapSites,
  getSiteMetadata,
  getCompartmentTileSources,
} from "./data";
import { mapAttributionLine } from "./map-tiles";
import {
  assetJurisdictionKey,
  buildJurisdictionLookup,
  buildSitesModel,
  emittedSiteLists,
  dossierSitesHref,
  dossierSitesPath,
} from "./sites";
import { jkeyChain, jkeyParentMap } from "./scoped-search";
import { dossierPath } from "./dossier";
import { beliefPinnedPermalink } from "./citation";
import { withBase } from "./paths";
import { TYPEAHEAD_SHARD_ROOT } from "./typeahead-shards";
import { isDrawnMap, getDossierVisuals } from "./dossier-visuals";
import { boundsViewport, unionBounds } from "../islands/map/model";
import type { MapRecord } from "../islands/map/model";

/** The emitted document's own schema id. */
export const MAP_EMBED_SCHEMA = "sig.dossier-map-embed/1";

export interface DossierMapEmbedDoc {
  schema: string;
  tiles: ReturnType<typeof getCompartmentTileSources>;
  records: MapRecord[];
  pointCount: number;
  attribution: string;
  citationHref: string;
  release: string | null;
  compartments: { id: string; license: string; attribution?: string }[];
  styles: { light: string; dark: string; context: string };
  vendorBase: string;
  dictHref: string;
  asOf: string;
  unplotted: number;
  jurisdictionHrefs: Record<string, string>;
  jurisdictionFrames: Record<
    string,
    { name?: string; bbox?: [number, number, number, number]; chain?: string[] }
  >;
  shardRoot: string;
  embedded: {
    jkey: string | null;
    placeLabel: string;
    publicationId: string | null;
    /** Records-bounds viewport — the framing fallback for an unkeyed dossier
     *  (no registry bbox to `frame=`). Null when the payload is empty. */
    fallbackAt: { z: number; lat: number; lon: number } | null;
  };
}

/** The slugs that emit a props document — exactly the dossiers whose
 *  Figure-1 drew located records (the element's own render gate). */
export function embedDossierSlugs(): string[] {
  return getDossiers()
    .filter((d) => {
      const doc = getDossierVisuals(d.slug);
      return (
        doc !== null &&
        isDrawnMap(doc.map) &&
        doc.map.desc.records_drawn > 0
      );
    })
    .map((d) => d.slug);
}

/**
 * One dossier's embed-props document. Shared fixtures/tiles/context resolve
 * once per call — the endpoint emits every drawn-map dossier in one pass.
 */
export function buildMapEmbedDoc(slug: string): DossierMapEmbedDoc {
  const MAP_ASSETS = getMapSites();
  const DOSSIERS = getDossiers();
  const lookup = buildJurisdictionLookup(
    DOSSIERS,
    getDossierIndex(),
    getJurisdictionKeyMap(),
  );
  const sitesModel = buildSitesModel(MAP_ASSETS, lookup);
  const SLUG_BY_ASSET_ID = new Map(
    emittedSiteLists(sitesModel).flatMap((l) =>
      l.rows.map((r) => [r.id, l.slug] as const),
    ),
  );
  const ASSET_BY_ID = new Map(MAP_ASSETS.map((a) => [a.id, a]));
  const PLACE_PARENTS = jkeyParentMap(getDossierIndex());
  const siteRecordHref = (id: string): string | null => {
    const s = SLUG_BY_ASSET_ID.get(id);
    return s ? withBase(dossierSitesHref(s, id)) : null;
  };
  // The payload IS the static figure's scope: the records the one-resolution
  // sites model placed under this dossier's subtree (the deep-slug lists,
  // slug == slug or a descendant), PLUS the rows whose assets name this
  // dossier outright (an unkeyed flat dossier's records resolve to the keyed
  // descendant's list — the flat dossier still draws them, so the activated
  // box carries them too; SIG-UI-132's figure/map reconcile).
  const scopeRows = [...sitesModel.lists.entries()]
    .filter(
      ([s]) =>
        s === slug ||
        s.startsWith(`${slug}/`),
    )
    .flatMap(([, l]) => l.rows);
  const seen = new Set(scopeRows.map((r) => r.id));
  for (const l of sitesModel.lists.values()) {
    for (const r of l.rows) {
      if (seen.has(r.id)) continue;
      const asset = ASSET_BY_ID.get(r.id);
      if (asset && asset.dossierSlug === slug) {
        scopeRows.push(r);
        seen.add(r.id);
      }
    }
  }
  const TILE_SOURCES = getCompartmentTileSources();
  const records: MapRecord[] =
    TILE_SOURCES.length === 0
      ? scopeRows
          .filter((r) => r.lat !== null && r.lon !== null)
          .map((r) => ({
            id: r.id,
            label: r.label,
            technology: r.technology,
            operator: r.operator === "not stated" ? null : r.operator,
            sources: (r.sources ?? []).map((s) => ({
              label: s,
              href: withBase("sources/"),
            })),
            licence: r.licence,
            jurisdiction: {
              label: ASSET_BY_ID.get(r.id)?.jurisdiction ?? r.dossierSlug,
              href: withBase(dossierPath(r.dossierSlug).replace(/^\//, "")),
            },
            firstSeen: r.firstSeen,
            lastSeen: r.lastSeen,
            status: (r.status === "corroborated"
              ? "corroborated"
              : r.status === "contested" || r.contested
                ? "contested"
                : r.status === "candidate"
                  ? "candidate"
                  : r.status === "single source"
                    ? "single-source"
                    : null) as MapRecord["status"],
            precision: r.precision,
            tier: r.tier,
            lat: r.lat as number,
            lon: r.lon as number,
            compartment: r.compartment,
            recordHref: siteRecordHref(r.id),
            listHref: withBase(dossierSitesPath(r.dossierSlug)),
            jkey: (() => {
              const a = ASSET_BY_ID.get(r.id);
              return a ? assetJurisdictionKey(a) : null;
            })(),
            chain: (() => {
              const a = ASSET_BY_ID.get(r.id);
              const jk = a ? assetJurisdictionKey(a) : null;
              return jk ? jkeyChain(jk, PLACE_PARENTS) : undefined;
            })(),
          }))
      : [];

  const LATEST = getLatestReleaseTarget();
  const ISLAND_COMPARTMENTS = TILE_SOURCES.length > 0
    ? TILE_SOURCES.map((t) => ({
        id: t.compartment,
        license: t.license,
        attribution: t.attribution,
      }))
    : (LATEST?.compartments.map((c) => ({ id: c.compartment, license: c.license })) ?? []);
  const meta = getSiteMetadata();
  const SLUG_BY_JKEY = getJurisdictionSlugPaths();
  const JURISDICTION_HREFS: Record<string, string> = {};
  if (SLUG_BY_JKEY) {
    for (const [jkey, slugPath] of SLUG_BY_JKEY) {
      if (slugPath) {
        JURISDICTION_HREFS[jkey] = withBase(dossierPath(slugPath).replace(/^\//, ""));
      }
    }
  }
  // The frame table the app frames the seeded `jurisdiction=` through —
  // the dossier's own registry bbox + ancestor chain (P37.19's shape).
  const dossier = DOSSIERS.find((d) => d.slug === slug);
  const jkey = dossier?.jurisdiction_key ?? null;
  const frames = getJurisdictionFrames();
  const jurisdictionFrames: DossierMapEmbedDoc["jurisdictionFrames"] = {};
  if (jkey && frames[jkey]) {
    jurisdictionFrames[jkey] = {
      ...frames[jkey],
      chain: jkeyChain(jkey, PLACE_PARENTS),
    };
  }
  const citationHref = beliefPinnedPermalink({
    path: "/map/",
    title: "Infrastructure map",
    asOf: meta.asOf,
    rulesetVersion: meta.rulesetVersion,
  });
  const locatable = records;
  // The unkeyed-dossier framing fallback: the payload's own extent →
  // `at=<z>/<lat>/<lon>` (the fold's own rule — an unkeyed dossier has no
  // registry bbox to `frame=` through).
  const recBounds = unionBounds(
    records.map((r): [number, number, number, number] => [r.lon, r.lat, r.lon, r.lat]),
  );
  const fallbackAt = !jkey && recBounds ? boundsViewport(recBounds) : null;

  return {
    schema: MAP_EMBED_SCHEMA,
    tiles: TILE_SOURCES,
    records,
    pointCount: locatable.length,
    attribution: mapAttributionLine(TILE_SOURCES),
    citationHref,
    release: LATEST?.publicationId ?? null,
    compartments: ISLAND_COMPARTMENTS,
    styles: {
      light: withBase("map/style-light.json"),
      dark: withBase("map/style-dark.json"),
      context: withBase("map/style-context.json"),
    },
    vendorBase: withBase("map/vendor/"),
    dictHref: withBase("map/dict.json"),
    asOf: meta.asOf.as_of_world,
    unplotted: scopeRows.length - locatable.length,
    jurisdictionHrefs: JURISDICTION_HREFS,
    jurisdictionFrames,
    shardRoot: withBase(TYPEAHEAD_SHARD_ROOT),
    embedded: {
      jkey,
      placeLabel: dossier?.display_name ?? dossier?.name ?? dossier?.jurisdiction ?? slug,
      publicationId: LATEST?.publicationId ?? null,
      fallbackAt,
    },
  };
}

/** The emitted route one dossier's props document lives at. */
export function mapEmbedPropsHref(slug: string): string {
  return `dossier/${slug}/map-embed.json`;
}

/** dataSource passthrough for the endpoint's mode notes. */
export { dataSource };
