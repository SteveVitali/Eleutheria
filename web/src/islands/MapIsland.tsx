// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The interactive infrastructure-map island (P27.9, DECISION-SPA = B, ADR-097 —
 * exercising SIG-UI-047, the MAY-level MapLibre progressive-enhancement island).
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
 * Archivability (SIG-UI-038): the renderer is self-hosted maplibre-gl with NO
 * third-party tile CDN; the ODbL / SIG attribution is shown per source (§42.3, a
 * licence obligation).
 */

import { useEffect, useRef, useState } from "react";
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
}

const GEOJSON_SOURCE = "sig-infrastructure";

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

/** The popup carries the epistemic disclosure fields + the citation (SIG-UI-035, §19.4). */
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

export default function MapIsland({
  tiles,
  points,
  pointCount,
  attribution,
  citationHref,
}: MapIslandProps): ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [drawn, setDrawn] = useState(false);

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
          "The full list, including assets without a published point, is in the table below.",
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
      try {
        removeProtocol("pmtiles");
      } catch {
        /* protocol may already be gone on a fast re-mount */
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
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
  );
}
