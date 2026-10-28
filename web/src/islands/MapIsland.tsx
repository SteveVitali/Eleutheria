// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The interactive infrastructure-map island (P27.9, DECISION-SPA = B, ADR-097 —
 * exercising SIG-UI-047, the MAY-level MapLibre progressive-enhancement island;
 * P32.15 shared workspace state, SIG-FIND-004, ADR-134).
 *
 * PROGRESSIVE ENHANCEMENT, NOT REPLACEMENT (SIG-UI-050): this island hydrates ONLY
 * on `/map/`; the tabular equivalent below it in the page is the source of truth and
 * the no-JS / screen-reader path (SIG-UI-037) and is never removed. With JavaScript
 * disabled the reader still gets the full located-assets table.
 *
 * Real vector tiles (P31.15, ADR-R9-TILES; P35.52, sig.map-tiles/2, ADR-156): the
 * island layers the per-licence-compartment PMTiles archives the export ships
 * (`/tiles/<compartment>-sites.<sha8>.pmtiles`, z0–z14 — the `cells` layer at z0–9
 * and the tier-banded `sites` layer above) — one attributed source per
 * compartment, composited on one map as an ODbL 4.4(b) produced work but never
 * merged (ADR-106). **No basemap** (Q8): the points
 * draw over a plain background. The combined `/map/points.json` is retired (Q9 —
 * R8-1 ending); the island never fetches it. Builds that ship no archives (the
 * committed fixtures) fall back to the small inline `points` prop — still only
 * tier-reduced, publishable points (§19.4, SIG-GEO-008): the island never has access
 * to and never draws full-precision geometry, and tier-3 / point-less assets are not
 * in its payload at all (they stay the jurisdiction indicators the static page
 * lists).
 *
 * Shared URL state (`sig.workspace-state/1`): `release`, `collection` (the
 * compartment switch — toggling updates BOTH the drawn sources and the licence
 * attribution line), `focus` (the selected record — a self-describing record_key
 * resolves its released `/r/<pub>/c/<comp>/entity/<type>/<id>.json`, a bare
 * island id resolves the inline points), and the List/Connections view links.
 * The viewport (`z`/`lat`/`lon`) is transient (S4 §8) — never written to the URL.
 * Centering uses `jumpTo` (no auto-pan animation; reduced-motion safe).
 *
 * Archivability (SIG-UI-038): the renderer is self-hosted maplibre-gl with NO
 * third-party tile CDN; the ODbL / SIG attribution is shown per source (§42.3, a
 * licence obligation).
 */

import { useEffect, useMemo, useRef, useState } from "react";
import type { ReactElement } from "react";
import {
  Map as MapLibreMap,
  Popup,
  NavigationControl,
  AttributionControl,
  addProtocol,
  removeProtocol,
  setWorkerUrl,
} from "maplibre-gl";
import type { StyleSpecification, MapGeoJSONFeature } from "maplibre-gl";
import type { Feature as GeoJSONFeature } from "geojson";
import { Protocol } from "pmtiles";
import "maplibre-gl/dist/maplibre-gl.css";
// P30.3: maplibre-gl v6 resolves its worker as `./maplibre-gl-worker.mjs` next to its own
// module — a file the Astro/Vite bundle never emits, so the GeoJSON worker 404'd and NO point
// was ever drawn (the map showed an empty background). Bundle the worker (with the shared
// chunk it imports) as one self-contained file and point maplibre at it explicitly.
import maplibreWorkerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import {
  compartmentAttribution,
  compartmentLayerId,
  compartmentSourceId,
  tileSourceAttribution,
  NATIONAL_CELLS_MAXZOOM,
  PMTILES_PROTOCOL,
} from "../lib/map-tiles";
import type { CompartmentTileSource } from "../lib/map-tiles";
import type { IslandPoint } from "../lib/map";
import {
  SIG_DATA_HUE,
  SIG_DATA_SEQ_400,
  SIG_DATA_SEQ_700,
  SIG_INK,
  SIG_SURFACE_2,
} from "../lib/design-tokens";
import {
  evidenceAnchorHref,
  facetNoticeText,
  recordRoutes,
  splitRecordKey,
  viewHref,
  WORKSPACE_VIEWS,
} from "../lib/workspace-state";
import { useWorkspaceState } from "./workspace";
import { panelFromStatement } from "../lib/provenance-panel";
import type { StatementRow } from "../lib/provenance-panel";
import ProvenancePanel from "../components/ProvenancePanel";

/** One switchable licence compartment (tile archive or release compartment). */
export interface CompartmentOption {
  id: string;
  license: string;
  /** The drawn sources' own credit from ATTRIBUTION.json (P34.21a / E2-12). */
  attribution?: string;
}

export interface MapIslandProps {
  /** The per-licence-compartment PMTiles archives the export ships (empty in fixtures). */
  tiles: readonly CompartmentTileSource[];
  /**
   * The fixtures-mode fallback: the small inline point set drawn as GeoJSON when the
   * build ships no tile archives. Only tier-reduced, publishable points (§19.4).
   */
  points: readonly IslandPoint[];
  /** How many located records the surface holds (for the canvas label). */
  pointCount: number;
  /** The ODbL / SIG attribution line rendered in the map control (SIG-GEO-013, §42.3). */
  attribution: string;
  /** The belief-pinned citation permalink for the surface (SIG-UI-035). */
  citationHref: string;
  /** The latest activated publication id for this build, or null (none). */
  release: string | null;
  /** The licence compartments the workspace switch governs. */
  compartments: readonly CompartmentOption[];
}

const GEOJSON_SOURCE = "sig-infrastructure";
const FOCUS_SOURCE = "sig-focus";
/** The browser-summed cells layer (K1 §3.2) — never a licence-mixed archive. */
const SUMMED_CELLS_SOURCE = "sig-cells-summed";
const SUMMED_CELLS_LAYER = "sig-cells-summed-layer";
const SUMMED_CELLS_LABEL = "sig-cells-summed-label";
const EMPTY_FC: { type: "FeatureCollection"; features: never[] } = {
  type: "FeatureCollection",
  features: [],
};

/** The `sig.map-tiles/2` §3.3 keys a `sites` feature carries. */
interface TileFeatureProps {
  rk?: string;
  lb?: string;
  j?: string;
  tr?: number;
  pm?: number;
  op?: string;
}

// P36.19 (UXK0-3, K0 §4.8): the popup is built from DOM nodes + textContent —
// client code renders text only: no innerHTML, no dangerouslySetInnerHTML,
// no MapLibre setHTML (check-unsafe-dom.mjs fails the gate on a re-introduce).
// Every label still comes from third-party data and is never markup.
function popupElement(a: IslandPoint, citationHref: string): HTMLElement {
  const root = document.createElement("div");
  root.className = "sig-map-popup";
  const heading = document.createElement("h3");
  heading.textContent = a.label;
  root.appendChild(heading);
  const fields = document.createElement("dl");
  const rows: Array<[string, string]> = [
    ["Jurisdiction", a.jurisdiction],
    ["Sensitivity tier", String(a.tier)],
    ["Published precision", a.precision],
  ];
  for (const [term, value] of rows) {
    const dt = document.createElement("dt");
    dt.textContent = term;
    const dd = document.createElement("dd");
    dd.textContent = value;
    fields.appendChild(dt);
    fields.appendChild(dd);
  }
  root.appendChild(fields);
  const cite = document.createElement("a");
  cite.href = citationHref;
  cite.textContent = "Cite this view (belief-pinned)";
  root.appendChild(cite);
  return root;
}

function backgroundStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {},
    layers: [
      {
        id: "sig-bg",
        type: "background",
        paint: { "background-color": SIG_SURFACE_2 },
      },
    ],
  };
}

const SITE_PAINT = {
  "circle-color": SIG_DATA_HUE,
  "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3, 10, 6] as never,
  "circle-stroke-color": SIG_DATA_SEQ_700,
  "circle-stroke-width": 1,
};

const VIEW_LABELS: Record<string, string> = {
  list: "List",
  map: "Map",
  network: "Connections",
};

interface FocusPane {
  id: string;
  label: string;
  detail: string;
  /** Released-record routes when `focus` is a record_key under a pinned release. */
  recordPageHref?: string;
  /** The record's JSON twin (`…/<id>.json`) — the panel's "Equivalent requests". */
  recordJsonHref?: string;
  evidenceHref?: string;
  compartmentHref?: string;
  /**
   * P35.36 (UXR-33): the record's embedded `sig.statement/1` rows (the
   * `claim_statements` the P35.36 record JSON carries) — rendered through the
   * shared panel contract, bounded to FOCUS_PANEL_LIMIT with the remainder
   * linked on the record page. Absent on a pre-P35.36 record (empty).
   */
  claimStatements?: StatementRow[];
  /** Where the focus resolves in the current view ("not in this view" is honest). */
  located: boolean;
}

/** The selection pane bounds its panels; the record page carries them all. */
const FOCUS_PANEL_LIMIT = 8;

export default function MapIsland({
  tiles,
  points,
  pointCount,
  attribution,
  citationHref,
  release,
  compartments,
}: MapIslandProps): ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const tileLayerCompartments = useRef<string[]>([]);
  /** The compartment switch as the sourcedata/moveend listeners see it. */
  const activeCompartmentsRef = useRef<Set<string>>(new Set());
  /** The cells re-sum closure the tile path registers (K1 §3.2 browser sum). */
  const resumCellsRef = useRef<(() => void) | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [drawn, setDrawn] = useState(false);
  const [focusPane, setFocusPane] = useState<FocusPane | null>(null);
  const { state, issues, ignored, update } = useWorkspaceState("map", { release });

  // The effective compartment selection: an ABSENT `collection` means all;
  // an explicit `collection=` means none — "0 of N compartments" is a real
  // state, not a silent default (sig.workspace-state/1, ADR-134).
  const allCompartmentIds = useMemo(() => compartments.map((c) => c.id), [compartments]);
  const activeCompartments = useMemo(
    () =>
      state.collectionSpecified ? new Set(state.collection) : new Set(allCompartmentIds),
    [state.collection, state.collectionSpecified, allCompartmentIds],
  );
  const activeAttribution = useMemo(() => {
    const lines = compartments
      .filter((c) => activeCompartments.has(c.id))
      .map((c) =>
        c.license === "ODbL-1.0"
          ? compartmentAttribution(c.license)
          : (c.attribution?.trim() || compartmentAttribution(c.license)),
      );
    return [...new Set(lines)].join(" · ");
  }, [compartments, activeCompartments]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Register the self-hosted static PMTiles protocol (SIG-UI-038): the per-
    // compartment archives are `pmtiles://` sources. No network by default.
    setWorkerUrl(maplibreWorkerUrl);
    const protocol = new Protocol();
    addProtocol("pmtiles", protocol.tile);

    const map = new MapLibreMap({
      container,
      style: backgroundStyle(),
      // A national view; the reader zooms in.
      center: [-97.5, 39],
      zoom: 3,
      attributionControl: false,
      // Tile fade-in re-renders the whole viewport every frame — at national
      // scale (~10⁵ circles per draw) that animation saturates the main thread
      // for tens of seconds under load. Instant appearance trades a cosmetic
      // fade for a responsive map.
      fadeDuration: 0,
      // Keyboard operability (WCAG 2.2 AA): arrow-pan / +- zoom are on by default;
      // the container is focusable and named below so a keyboard user can drive it.
    });
    mapRef.current = map;
    map.addControl(new NavigationControl({ visualizePitch: false }), "top-right");
    map.addControl(
      new AttributionControl({ compact: false, customAttribution: attribution }),
      "bottom-right",
    );

    map.on("load", () => {
      const tileLayerIds: string[] = [];
      let drawnSourceIds: string[] = [];

      if (tiles.length > 0) {
        // The real path: one attributed vector source per licence compartment —
        // composited on one map, never merged (ADR-106). A missing archive fires a
        // non-fatal error event; the other compartments still render.
        for (const t of tiles) {
          const sourceId = compartmentSourceId(t.compartment);
          const layerId = compartmentLayerId(t.compartment);
          try {
            map.addSource(sourceId, {
              type: "vector",
              url: `${PMTILES_PROTOCOL}${t.path}`,
              attribution: tileSourceAttribution(t),
            });
            // sig.map-tiles/2: tier-2 sites are H3 polygons (never the true
            // point) — they draw under their own fill layer; tr≤1 stay circles.
            map.addLayer({
              id: `${layerId}-cells`,
              type: "fill",
              source: sourceId,
              "source-layer": "sites",
              filter: ["==", ["get", "tr"], 2],
              paint: { "fill-color": SIG_DATA_HUE, "fill-opacity": 0.18 },
            });
            map.addLayer({
              id: layerId,
              type: "circle",
              source: sourceId,
              "source-layer": "sites",
              filter: ["!=", ["get", "tr"], 2],
              paint: SITE_PAINT,
            });
            tileLayerIds.push(layerId, `${layerId}-cells`);
            tileLayerCompartments.current.push(t.compartment);
            drawnSourceIds.push(sourceId);
          } catch {
            /* a failing archive degrades honestly; other compartments still draw */
          }
        }

        // K1 §3.2: cell counts are summed in the BROWSER. A cross-compartment
        // count file would be a licence-mixed derived database (ADR-106 §4
        // files those only as restricted build inputs), so each archive keeps
        // its own compartment's `cells` and the client re-sums visible cells
        // per h3 over the ACTIVE compartments on every sourcedata/moveend —
        // toggling a compartment re-sums instantly. The summed source is an
        // in-memory GeoJSON layer (a produced work; every active
        // compartment's attribution rides the map control).
        map.addSource(SUMMED_CELLS_SOURCE, { type: "geojson", data: EMPTY_FC });
        map.addLayer({
          id: SUMMED_CELLS_LAYER,
          type: "circle",
          source: SUMMED_CELLS_SOURCE,
          maxzoom: NATIONAL_CELLS_MAXZOOM + 1,
          paint: {
            "circle-color": SIG_DATA_HUE,
            "circle-opacity": 0.4,
            // √(summed n)-scaled radius — legible from 1 record to a metro cell
            "circle-radius": [
              "interpolate",
              ["linear"],
              ["^", ["get", "n"], 0.5],
              1,
              3,
              32,
              12,
              256,
              26,
            ],
            "circle-stroke-color": SIG_DATA_SEQ_700,
            "circle-stroke-width": 0.6,
          },
        });
        map.addLayer({
          id: SUMMED_CELLS_LABEL,
          type: "symbol",
          source: SUMMED_CELLS_SOURCE,
          minzoom: 5,
          maxzoom: NATIONAL_CELLS_MAXZOOM + 1,
          layout: {
            "text-field": ["get", "n"],
            "text-size": 11,
            "text-allow-overlap": false,
          },
          paint: { "text-color": SIG_INK },
        });
        // The setData below re-fires `sourcedata` for SUMMED_CELLS_SOURCE;
        // re-entering on our own write is an infinite async loop that keeps the
        // map permanently busy so `idle` never fires and `data-drawn` never
        // latches (the P35.52 export leg red). Skip our own source's events and
        // skip the write entirely when the re-summed collection is unchanged —
        // a tile storm's sourcedata churn then costs one query pass, not a
        // worker round-trip per tile.
        let lastCellsSignature = "";
        const resumCells = (event?: object) => {
          if (
            event !== undefined &&
            "sourceId" in event &&
            event.sourceId === SUMMED_CELLS_SOURCE
          ) {
            return;
          }
          // dedupe by (compartment, h3): the same cell can arrive twice from
          // adjacent tile interiors; then sum across compartments by h3.
          const seen = new Set<string>();
          const byCell = new Map<string, { n: number; coordinates: [number, number] }>();
          for (const comp of activeCompartmentsRef.current) {
            const sourceId = compartmentSourceId(comp);
            if (!map.getSource(sourceId)) continue;
            let feats: GeoJSONFeature[] = [];
            try {
              feats = map.querySourceFeatures(sourceId, { sourceLayer: "cells" });
            } catch {
              continue;
            }
            for (const f of feats) {
              const h3 = String((f.properties as Record<string, unknown>)?.["h3"] ?? "");
              if (!h3 || f.geometry?.type !== "Point") continue;
              const dedupeKey = `${comp}:${h3}`;
              if (seen.has(dedupeKey)) continue;
              seen.add(dedupeKey);
              const n = Number((f.properties as Record<string, unknown>)?.["n"] ?? 0);
              const cur = byCell.get(h3);
              if (cur) cur.n += n;
              else {
                const [cx = 0, cy = 0] = (f.geometry as { coordinates: number[] })
                  .coordinates;
                byCell.set(h3, { n, coordinates: [cx, cy] });
              }
            }
          }
          const features = [...byCell].map(([h3, c]) => ({
            type: "Feature" as const,
            geometry: { type: "Point" as const, coordinates: c.coordinates },
            properties: { h3, n: c.n },
          }));
          const signature = features
            .map((f) => `${f.properties.h3}=${f.properties.n}`)
            .sort()
            .join("|");
          if (signature === lastCellsSignature) return;
          lastCellsSignature = signature;
          const setData = (map.getSource(SUMMED_CELLS_SOURCE) as
            | { setData?: (d: unknown) => void }
            | undefined)?.setData;
          setData?.call(map.getSource(SUMMED_CELLS_SOURCE), {
            type: "FeatureCollection",
            features,
          });
        };
        resumCellsRef.current = resumCells;
        map.on("sourcedata", resumCells);
        map.on("moveend", resumCells);
        resumCells();

        // Popups read the tile feature's own §3.3 render properties — the only
        // data the archive carries (rk / lb / j / tr / pm / op — the record
        // key, label, K4 jurisdiction key, tier and uncertainty radius).
        const openTilePopup = (e: {
          features?: MapGeoJSONFeature[];
          lngLat: { lng: number; lat: number };
        }) => {
          const f = e.features?.[0];
          const p = (f?.properties ?? {}) as TileFeatureProps;
          if (!f) return;
          const tier = Number(p.tr ?? 0);
          const asset: IslandPoint = {
            id: String(p.rk ?? ""),
            label: String(p.lb ?? p.rk ?? ""),
            jurisdiction: String(p.j ?? ""),
            tier,
            lat: e.lngLat.lat,
            lon: e.lngLat.lng,
            precision:
              typeof p.pm === "number"
                ? `±${p.pm} m`
                : tier === 2
                  ? "binned (H3 cell)"
                  : "",
          };
          new Popup({ closeButton: true })
            .setLngLat([e.lngLat.lng, e.lngLat.lat])
            .setDOMContent(popupElement(asset, citationHref))
            .addTo(map);
        };
        for (const layerId of tileLayerIds) {
          map.on("click", layerId, openTilePopup);
          map.on("mouseenter", layerId, () => {
            map.getCanvas().style.cursor = "pointer";
          });
          map.on("mouseleave", layerId, () => {
            map.getCanvas().style.cursor = "";
          });
        }
      } else if (points.length > 0) {
        // Fixtures fallback: no archives shipped → the small inline point set as a
        // clustered GeoJSON source (same disclosure + popup contract).
        map.addSource(GEOJSON_SOURCE, {
          type: "geojson",
          data: {
            type: "FeatureCollection",
            features: points.map((a) => ({
              type: "Feature",
              geometry: { type: "Point", coordinates: [a.lon, a.lat] },
              properties: { id: a.id },
            })),
          },
          cluster: true,
          clusterRadius: 48,
          clusterMaxZoom: 13,
        });

        map.addLayer({
          id: "sig-clusters",
          type: "circle",
          source: GEOJSON_SOURCE,
          filter: ["has", "point_count"],
          paint: {
            "circle-color": SIG_DATA_SEQ_400,
            "circle-radius": ["step", ["get", "point_count"], 14, 10, 20, 50, 28],
            "circle-stroke-color": SIG_DATA_SEQ_700,
            "circle-stroke-width": 1,
          },
        });
        map.addLayer({
          id: "sig-cluster-count",
          type: "symbol",
          source: GEOJSON_SOURCE,
          filter: ["has", "point_count"],
          layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12 },
        });
        map.addLayer({
          id: "sig-points",
          type: "circle",
          source: GEOJSON_SOURCE,
          filter: ["!", ["has", "point_count"]],
          paint: {
            "circle-color": SIG_DATA_HUE,
            "circle-radius": 6,
            "circle-stroke-color": SIG_DATA_SEQ_700,
            "circle-stroke-width": 1,
          },
        });
        // The focus marker: a distinct ring, fed by the workspace `focus` state.
        map.addSource(FOCUS_SOURCE, {
          type: "geojson",
          data: { type: "FeatureCollection", features: [] },
        });
        map.addLayer({
          id: "sig-focus-ring",
          type: "circle",
          source: FOCUS_SOURCE,
          paint: {
            "circle-color": "rgba(0,0,0,0)",
            "circle-radius": 12,
            "circle-stroke-color": SIG_INK,
            "circle-stroke-width": 3,
          },
        });

        drawnSourceIds = [GEOJSON_SOURCE];
        const byId = new Map(points.map((a) => [a.id, a]));
        map.on("click", "sig-points", (e) => {
          const f = e.features?.[0] as MapGeoJSONFeature | undefined;
          const id = f?.properties?.["id"] as string | undefined;
          const asset = id ? byId.get(id) : undefined;
          if (!asset) return;
          new Popup({ closeButton: true })
            .setLngLat([asset.lon, asset.lat])
            .setDOMContent(popupElement(asset, citationHref))
            .addTo(map);
        });
        map.on("click", "sig-clusters", (e) => {
          const f = e.features?.[0];
          if (!f) return;
          const g = f.geometry;
          if (g.type !== "Point") return;
          const [lng = 0, lat = 0] = g.coordinates;
          map.easeTo({ center: [lng, lat], zoom: Math.min(map.getZoom() + 2, 15) });
        });
        for (const layer of ["sig-points", "sig-clusters"]) {
          map.on("mouseenter", layer, () => {
            map.getCanvas().style.cursor = "pointer";
          });
          map.on("mouseleave", layer, () => {
            map.getCanvas().style.cursor = "";
          });
        }
      } else {
        setFailed(true);
        return;
      }

      // Name the canvas for assistive tech; the table remains the full SR path.
      const canvas = map.getCanvas();
      canvas.setAttribute("tabindex", "0");
      canvas.setAttribute(
        "aria-label",
        `Interactive map of ${pointCount} located surveillance records. ` +
          "The full list, including records without a published point, is in the table below.",
      );
      setReady(true);
      // Evidence the points actually reached the renderer (the worker loaded + a source
      // tiled) — not merely that MapLibre initialised (P30.3: it once hydrated with 0
      // drawn). A compartment archive that 404s leaves its source featureless, which
      // reads here as an honest data-drawn="false".
      //
      // The check is `isSourceLoaded`, not a `querySourceFeatures` feature scan: a
      // feature query materialises every feature in every loaded tile — O(10⁵) at
      // national scale per call, on a listener that refires each idle — which
      // saturates the main thread for minutes under CPU throttle. Source-loaded is
      // the O(1) honest signal: the archive's TileJSON parsed and its tiles are
      // streaming (a 404/malformed archive never reports loaded); whether any
      // compartment carries features is the export gate's job, not a per-idle
      // renderer audit. The check is RECURRING — the first idle can precede a
      // just-added source's tiles — but unregisters on the first positive latch.
      const checkDrawn = () =>
        drawnSourceIds.some((id) => map.getSource(id) && map.isSourceLoaded(id));
      const onIdle = () => {
        if (!checkDrawn()) return;
        map.off("idle", onIdle);
        setDrawn(true);
      };
      map.on("idle", onIdle);
    });

    return () => {
      map.remove();
      mapRef.current = null;
      tileLayerCompartments.current = [];
      resumCellsRef.current = null;
      try {
        removeProtocol("pmtiles");
      } catch {
        /* protocol may already be gone on a fast re-mount */
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Compartment switch → data AND attribution (SIG-FIND-004): each mounted tile
  // layer toggles with the selection; the browser-summed `cells` layer re-sums
  // over the active compartments (K1 §3.2); the attribution line recomputes.
  useEffect(() => {
    activeCompartmentsRef.current = activeCompartments;
    const map = mapRef.current;
    if (!map || !ready) return;
    for (const compartment of tileLayerCompartments.current) {
      const layerId = compartmentLayerId(compartment);
      for (const id of [layerId, `${layerId}-cells`]) {
        if (map.getLayer(id)) {
          map.setLayoutProperty(
            id,
            "visibility",
            activeCompartments.has(compartment) ? "visible" : "none",
          );
        }
      }
    }
    resumCellsRef.current?.();
  }, [activeCompartments, ready]);

  // Focus resolution (SIG-FIND-004): a `focus` record_key is self-describing —
  // its released-record JSON is fetched and the pane links the record/evidence
  // anchors; a bare island id resolves the inline points. An unresolvable focus
  // stays navigable — the pane says so honestly and still links what it can.
  useEffect(() => {
    const focus = state.focus;
    const map = mapRef.current;
    if (!ready) return;
    const setMarker = (lat: number | null, lon: number | null) => {
      const src = map?.getSource(FOCUS_SOURCE) as { setData?: (d: unknown) => void } | undefined;
      if (!src?.setData) return;
      src.setData(
        lat !== null && lon !== null
          ? {
              type: "FeatureCollection",
              features: [
                {
                  type: "Feature",
                  geometry: { type: "Point", coordinates: [lon, lat] },
                  properties: {},
                },
              ],
            }
          : { type: "FeatureCollection", features: [] },
      );
    };
    if (focus === null) {
      setFocusPane(null);
      setMarker(null, null);
      return;
    }
    let cancelled = false;
    const rel = state.release ?? release;
    const routes = rel ? recordRoutes(rel, focus) : null;

    // Bare island id first — cheap and works with no release pinned.
    const point = points.find((p) => p.id === focus);
    if (point) {
      map?.jumpTo({ center: [point.lon, point.lat], zoom: Math.max(map.getZoom(), 9) });
      setMarker(point.lat, point.lon);
      setFocusPane({
        id: focus,
        label: point.label,
        detail: `${point.jurisdiction} · ${point.precision}`,
        recordPageHref: routes?.pageHref,
        compartmentHref: routes?.compartmentHref,
        located: true,
      });
      return () => {
        cancelled = true;
      };
    }

    if (routes) {
      setFocusPane({
        id: focus,
        label: focus,
        detail: "Loading the released record…",
        recordPageHref: routes.pageHref,
        compartmentHref: routes.compartmentHref,
        located: false,
      });
      fetch(routes.jsonHref)
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((record) => {
          if (cancelled) return;
          const label =
            (record?.label?.text as string | null | undefined) ??
            (record?.entity_id as string | undefined) ??
            focus;
          const jurisdiction = (record?.jurisdiction?.id as string | undefined) ?? "";
          const loc = record?.location as
            | { kind?: string; lat?: number; lon?: number; precision?: string }
            | undefined;
          const lat = typeof loc?.lat === "number" ? loc.lat : null;
          const lon = typeof loc?.lon === "number" ? loc.lon : null;
          if (lat !== null && lon !== null) {
            map?.jumpTo({ center: [lon, lat], zoom: Math.max(map.getZoom(), 9) });
            setMarker(lat, lon);
          } else {
            setMarker(null, null);
          }
          const artifact = (record?.evidence_refs as { artifact_id?: string | null }[] | undefined)
            ?.map((e) => e.artifact_id)
            .find((a): a is string => typeof a === "string");
          const parts = splitRecordKey(focus);
          // P35.36 (UXR-33): the record JSON embeds its `sig.statement/1`
          // claim rows — the selection pane renders them through the one
          // panel contract (a pre-P35.36 record carries none — honest absence).
          const claimStatements = (
            Array.isArray(record?.claim_statements) ? record.claim_statements : []
          ) as StatementRow[];
          setFocusPane({
            id: focus,
            label,
            detail:
              `${jurisdiction ? `${jurisdiction} · ` : ""}${String(record?.entity_type ?? "record")}` +
              (loc?.precision ? ` · ${loc.precision}` : "") +
              (lat === null ? " · no published point" : ""),
            recordPageHref: routes.pageHref,
            recordJsonHref: routes.jsonHref,
            evidenceHref:
              artifact && parts ? evidenceAnchorHref(rel!, parts.compartment, artifact) : undefined,
            compartmentHref: routes.compartmentHref,
            claimStatements,
            located: lat !== null && lon !== null,
          });
        })
        .catch(() => {
          if (cancelled) return;
          // The record could not be loaded from this surface (fixtures mode has no
          // /r/ tree, or the release is not staged here) — the pane stays honest
          // and still links the canonical routes.
          setFocusPane({
            id: focus,
            label: focus,
            detail:
              "The released record could not be loaded from this surface — the record page is the authoritative route.",
            recordPageHref: routes.pageHref,
            compartmentHref: routes.compartmentHref,
            located: false,
          });
        });
      return () => {
        cancelled = true;
      };
    }

    // Not a record key, not an island point — say so, never fabricate.
    setFocusPane({
      id: focus,
      label: focus,
      detail: "This record is not in the current map view.",
      located: false,
    });
    setMarker(null, null);
    return () => {
      cancelled = true;
    };
  }, [state.focus, state.release, release, ready, points]);

  const toggleCompartment = (id: string) => {
    const next = new Set(activeCompartments);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    // Full selection canonicalises back to the absent (all-compartments)
    // default; every other selection — including the EMPTY one — is explicit.
    const full = next.size === allCompartmentIds.length;
    update({ collection: full ? [] : [...next], collectionSpecified: !full });
  };

  return (
    <div data-testid="map-island-root">
      <nav className="sig-view-links" aria-label="Investigation views" data-testid="island-view-links">
        {WORKSPACE_VIEWS.map((v) =>
          v === state.view ? (
            <strong key={v} aria-current="page">{VIEW_LABELS[v]}</strong>
          ) : (
            <a key={v} href={viewHref(state, v)} data-testid={`view-link-${v}`}>
              {VIEW_LABELS[v]}
            </a>
          ),
        )}
      </nav>
      {issues.length > 0 && (
        <p className="sig-island__note" role="status" data-testid="workspace-issues">
          {issues.join(" ")}
        </p>
      )}
      {ignored.length > 0 && (
        <p className="sig-island__note" role="status" data-testid="facet-not-applied">
          {facetNoticeText(ignored)}
        </p>
      )}

      {compartments.length > 0 && (
        <fieldset className="sig-island__compartments" data-testid="map-compartments">
          <legend>Licence compartments</legend>
          {compartments.map((c) => (
            <label key={c.id}>
              <input
                type="checkbox"
                data-testid={`map-compartment-${c.id}`}
                checked={activeCompartments.has(c.id)}
                onChange={() => toggleCompartment(c.id)}
              />{" "}
              <code>{c.id}</code> <span className="sig-island__note">({c.license})</span>
            </label>
          ))}
        </fieldset>
      )}
      <p className="sig-island__note" data-testid="map-compartment-attribution">
        {activeCompartments.size === allCompartmentIds.length
          ? `All ${allCompartmentIds.length} licence compartment${allCompartmentIds.length === 1 ? "" : "s"}`
          : `${activeCompartments.size} of ${allCompartmentIds.length} licence compartments`}
        {activeAttribution ? ` — ${activeAttribution}` : ""}.
        {state.release ? (
          <>
            {" "}Release <code data-testid="workspace-release">{state.release}</code>.
          </>
        ) : null}
      </p>

      <div
        className="sig-map-island__canvas"
        role="application"
        aria-roledescription="interactive map"
        aria-label="Interactive surveillance-infrastructure map (progressive enhancement; the full data is in the table below)"
        data-testid="map-island"
        data-ready={ready ? "true" : "false"}
        data-failed={failed ? "true" : "false"}
        data-drawn={drawn ? "true" : "false"}
        data-point-count={pointCount}
        ref={containerRef}
      />

      {focusPane && (
        <section className="sig-island__focus" data-testid="map-focus-pane" aria-label="Selected record">
          <h3>Selected record</h3>
          <p>
            <strong>{focusPane.label}</strong>
            {focusPane.detail ? <span className="sig-island__note"> — {focusPane.detail}</span> : null}
          </p>
          <p>
            {focusPane.recordPageHref && (
              <>
                <a href={focusPane.recordPageHref} data-testid="focus-record-link">
                  Open the released record
                </a>
                {" · "}
              </>
            )}
            {focusPane.evidenceHref && (
              <>
                <a href={focusPane.evidenceHref} data-testid="focus-evidence-link">
                  Open evidence page
                </a>
                {" · "}
              </>
            )}
            {focusPane.compartmentHref && (
              <>
                <a href={focusPane.compartmentHref}>Compartment browse</a>
                {" · "}
              </>
            )}
            <a href={viewHref(state, "list")} data-testid="focus-list-link">List</a>
            {" · "}
            <a href={viewHref(state, "network")} data-testid="focus-network-link">Connections</a>
            {" · "}
            <button type="button" onClick={() => update({ focus: null })}>
              Clear selection
            </button>
          </p>
          {/* P35.36 (UXR-33): one shared provenance panel per claim the record
              publishes — the same contract the record page renders, bounded
              here with the remainder on the record page. */}
          {focusPane.claimStatements && focusPane.claimStatements.length > 0 && (
            <div className="sig-island__focus-panels" data-testid="focus-claim-panels">
              {focusPane.claimStatements.slice(0, FOCUS_PANEL_LIMIT).map((stmt) => (
                <ProvenancePanel
                  key={stmt.claim_id}
                  panel={panelFromStatement(stmt, stmt.claim_id, {
                    jsonHref: focusPane.recordJsonHref,
                  })}
                  anchor={false}
                />
              ))}
              {focusPane.claimStatements.length > FOCUS_PANEL_LIMIT && focusPane.recordPageHref && (
                <p className="sig-island__note">
                  {focusPane.claimStatements.length - FOCUS_PANEL_LIMIT} more claim
                  {focusPane.claimStatements.length - FOCUS_PANEL_LIMIT === 1 ? "" : "s"} on{" "}
                  <a href={focusPane.recordPageHref}>the released record</a>.
                </p>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
