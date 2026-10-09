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
 * Real vector tiles (P31.15, ADR-R9-TILES): the island layers the per-licence-
 * compartment PMTiles archives the export ships (`/tiles/<compartment>-sites.pmtiles`,
 * z0–z14) — one attributed source per compartment, composited on one map as an ODbL
 * 4.4(b) produced work but never merged (ADR-106). **No basemap** (Q8): the points
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
  PMTILES_PROTOCOL,
} from "../lib/map-tiles";
import type { CompartmentTileSource } from "../lib/map-tiles";
import type { IslandPoint } from "../lib/map";
import {
  evidenceAnchorHref,
  facetNoticeText,
  recordRoutes,
  splitRecordKey,
  viewHref,
  WORKSPACE_VIEWS,
} from "../lib/workspace-state";
import { useWorkspaceState } from "./workspace";

/** One switchable licence compartment (tile archive or release compartment). */
export interface CompartmentOption {
  id: string;
  license: string;
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

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

interface TileFeatureProps {
  entity_id?: string;
  label?: string;
  jurisdiction?: string;
  sensitivity_tier?: number;
  precision?: string;
}

/** The popup carries the epistemic disclosure fields + the citation (SIG-UI-035). */
function popupHtml(a: IslandPoint, citationHref: string): string {
  return (
    `<div class="sig-map-popup">` +
    `<h3>${escapeHtml(a.label)}</h3>` +
    `<dl>` +
    `<dt>Jurisdiction</dt><dd>${escapeHtml(a.jurisdiction)}</dd>` +
    `<dt>Sensitivity tier</dt><dd>${a.tier}</dd>` +
    `<dt>Published precision</dt><dd>${escapeHtml(a.precision)}</dd>` +
    `</dl>` +
    `<a href="${escapeHtml(citationHref)}">Cite this view (belief-pinned)</a>` +
    `</div>`
  );
}

function backgroundStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {},
    layers: [
      {
        id: "sig-bg",
        type: "background",
        paint: { "background-color": "hsl(210deg 20% 96%)" },
      },
    ],
  };
}

const SITE_PAINT = {
  "circle-color": "hsl(28deg 80% 45%)",
  "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3, 10, 6] as never,
  "circle-stroke-color": "#222",
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
  evidenceHref?: string;
  compartmentHref?: string;
  /** Where the focus resolves in the current view ("not in this view" is honest). */
  located: boolean;
}

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
      .map((c) => compartmentAttribution(c.license));
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
              attribution: compartmentAttribution(t.license),
            });
            map.addLayer({
              id: layerId,
              type: "circle",
              source: sourceId,
              "source-layer": "sites",
              paint: SITE_PAINT,
            });
            tileLayerIds.push(layerId);
            tileLayerCompartments.current.push(t.compartment);
            drawnSourceIds.push(sourceId);
          } catch {
            /* a failing archive degrades honestly; other compartments still draw */
          }
        }

        // Popups read the tile feature's own (slimmed) render properties — the only
        // data the archive carries (entity_id / label / jurisdiction /
        // sensitivity_tier / precision, §19.4).
        const openTilePopup = (e: {
          features?: MapGeoJSONFeature[];
          lngLat: { lng: number; lat: number };
        }) => {
          const f = e.features?.[0];
          const p = (f?.properties ?? {}) as TileFeatureProps;
          if (!f) return;
          const asset: IslandPoint = {
            id: String(p.entity_id ?? ""),
            label: String(p.label ?? p.entity_id ?? ""),
            jurisdiction: String(p.jurisdiction ?? ""),
            tier: Number(p.sensitivity_tier ?? 0),
            lat: e.lngLat.lat,
            lon: e.lngLat.lng,
            precision: String(p.precision ?? ""),
          };
          new Popup({ closeButton: true })
            .setLngLat([e.lngLat.lng, e.lngLat.lat])
            .setHTML(popupHtml(asset, citationHref))
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
            "circle-color": "hsl(28deg 80% 55%)",
            "circle-radius": ["step", ["get", "point_count"], 14, 10, 20, 50, 28],
            "circle-stroke-color": "#333",
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
            "circle-color": "hsl(28deg 80% 45%)",
            "circle-radius": 6,
            "circle-stroke-color": "#222",
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
            "circle-stroke-color": "hsl(28deg 80% 40%)",
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
            .setHTML(popupHtml(asset, citationHref))
            .addTo(map);
        });
        map.on("click", "sig-clusters", (e) => {
          const f = e.features?.[0];
          if (!f) return;
          const [lng, lat] = (f.geometry as { coordinates: [number, number] }).coordinates;
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
      // reads here as an honest data-drawn="false". This is a RECURRING idle check,
      // not a one-shot: the first idle can precede a just-added source's tiles being
      // queryable under load, so the flag only ever latches true when features are
      // really there.
      const checkDrawn = () =>
        drawnSourceIds.some(
          (id) => map.getSource(id) && map.querySourceFeatures(id).length > 0,
        );
      map.on("idle", () => {
        if (checkDrawn()) setDrawn(true);
      });
    });

    return () => {
      map.remove();
      mapRef.current = null;
      tileLayerCompartments.current = [];
      try {
        removeProtocol("pmtiles");
      } catch {
        /* protocol may already be gone on a fast re-mount */
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Compartment switch → data AND attribution (SIG-FIND-004): each mounted tile
  // layer toggles with the selection; the attribution line below recomputes.
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    for (const compartment of tileLayerCompartments.current) {
      const layerId = compartmentLayerId(compartment);
      if (map.getLayer(layerId)) {
        map.setLayoutProperty(
          layerId,
          "visibility",
          activeCompartments.has(compartment) ? "visible" : "none",
        );
      }
    }
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
          setFocusPane({
            id: focus,
            label,
            detail:
              `${jurisdiction ? `${jurisdiction} · ` : ""}${String(record?.entity_type ?? "record")}` +
              (loc?.precision ? ` · ${loc.precision}` : "") +
              (lat === null ? " · no published point" : ""),
            recordPageHref: routes.pageHref,
            evidenceHref:
              artifact && parts ? evidenceAnchorHref(rel!, parts.compartment, artifact) : undefined,
            compartmentHref: routes.compartmentHref,
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
        </section>
      )}
    </div>
  );
}
