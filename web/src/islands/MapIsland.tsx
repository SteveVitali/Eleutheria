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
 * Honest coordinates (§19.4, SIG-GEO-008): the island draws ONLY the tier-reduced,
 * published `lat`/`lon` the data layer already carries — the same points the served
 * PMTiles are rendered from. It never has access to and never draws full-precision
 * geometry, and tier-3 / point-less assets are not in its payload at all (they stay as
 * the jurisdiction indicators the static page lists).
 *
 * National scale (P30.3, ADR-106): the points are FETCHED from the static
 * `/map/points.json` (built from the same data seam) on hydration rather than inlined as
 * props — ~225k located records would otherwise put tens of MB into the page HTML.
 *
 * Archivability (SIG-UI-038): the renderer is self-hosted maplibre-gl over a
 * background base style with NO third-party tile CDN. When the export bundle ships
 * the self-hosted basemap PMTiles (`/tiles/osm-basemap.pmtiles`, present in
 * `SIG_DATA_SOURCE=export` builds) the island layers it in via the `pmtiles://`
 * protocol; otherwise it renders the points over a plain background — either way the
 * ODbL / SIG attribution is shown (§42.3, a licence obligation).
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
import { decodeIslandPoints } from "../lib/map";
import type { IslandPoint, IslandPointsPayload } from "../lib/map";

/** The minimal, already-tier-reduced asset shape the island draws (a MapAsset with a point). */
export type MapIslandAsset = IslandPoint;

export interface MapIslandProps {
  /** The static points file (`/map/points.json`) — locatable, tier-reduced assets only. */
  pointsUrl: string;
  /** How many points the file carries (for the canvas label before the fetch resolves). */
  pointCount: number;
  /** The ODbL / SIG attribution line rendered in the map control (SIG-GEO-013, §42.3). */
  attribution: string;
  /** The belief-pinned citation permalink for the surface (SIG-UI-035). */
  citationHref: string;
  /** True when the self-hosted basemap PMTiles exists in the build (export mode). */
  hasBasemapTiles: boolean;
}

const SIG_SOURCE = "sig-infrastructure";

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** The popup carries the epistemic disclosure fields + the citation (SIG-UI-035, §19.4). */
function popupHtml(a: MapIslandAsset, citationHref: string): string {
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

export default function MapIsland({
  pointsUrl,
  pointCount,
  attribution,
  citationHref,
  hasBasemapTiles,
}: MapIslandProps): ReactElement {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [drawn, setDrawn] = useState(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // Register the self-hosted static PMTiles protocol (SIG-UI-038) so a basemap
    // archive can be layered in when the export ships one. No network by default.
    setWorkerUrl(maplibreWorkerUrl);
    const protocol = new Protocol();
    addProtocol("pmtiles", protocol.tile);

    const map = new MapLibreMap({
      container,
      style: backgroundStyle(),
      // A national view; the reader zooms in (the clusters show where the records are).
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

    const abort = new AbortController();
    const pointsReady: Promise<MapIslandAsset[]> = fetch(pointsUrl, { signal: abort.signal })
      .then((r) => {
        if (!r.ok) throw new Error(`${pointsUrl}: HTTP ${r.status}`);
        return r.json() as Promise<IslandPointsPayload>;
      })
      .then(decodeIslandPoints);
    // Handled here too, so a map that never fires `load` (e.g. no WebGL) or an unmount
    // mid-fetch leaves no unhandled rejection; the `load` handler still awaits the result.
    pointsReady.catch(() => setFailed(true));

    map.on("load", async () => {
      let assets: MapIslandAsset[];
      try {
        assets = await pointsReady;
      } catch {
        // The table below is the full, archivable surface; the island degrades honestly.
        setFailed(true);
        return;
      }
      if (hasBasemapTiles) {
        // Layer in the self-hosted OSM basemap when the export ships it. A missing
        // archive fires a non-fatal error event; the points still render.
        try {
          map.addSource("osm-basemap", {
            type: "vector",
            url: "pmtiles:///tiles/osm-basemap.pmtiles",
            attribution,
          });
          map.addLayer({
            id: "osm-basemap-roads",
            type: "line",
            source: "osm-basemap",
            "source-layer": "roads",
            paint: { "line-color": "hsl(210deg 12% 70%)", "line-width": 1 },
          });
        } catch {
          /* basemap is optional enhancement; points render regardless */
        }
      }

      map.addSource(SIG_SOURCE, {
        type: "geojson",
        data: {
          type: "FeatureCollection",
          features: assets.map((a) => ({
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
        source: SIG_SOURCE,
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
        source: SIG_SOURCE,
        filter: ["has", "point_count"],
        layout: { "text-field": ["get", "point_count_abbreviated"], "text-size": 12 },
      });
      map.addLayer({
        id: "sig-points",
        type: "circle",
        source: SIG_SOURCE,
        filter: ["!", ["has", "point_count"]],
        paint: {
          "circle-color": "hsl(28deg 80% 45%)",
          "circle-radius": 6,
          "circle-stroke-color": "#222",
          "circle-stroke-width": 1,
        },
      });

      const byId = new Map(assets.map((a) => [a.id, a]));
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

      // Name the canvas for assistive tech; the table remains the full SR path.
      const canvas = map.getCanvas();
      canvas.setAttribute("tabindex", "0");
      canvas.setAttribute(
        "aria-label",
        `Interactive map of ${assets.length} located surveillance records. ` +
          "The full list, including assets without a published point, is in the table below.",
      );
      setReady(true);
      // Evidence the points actually reached the renderer (the worker loaded + the source
      // tiled) — not merely that MapLibre initialised (P30.3: it once hydrated with 0 drawn).
      map.once("idle", () => setDrawn(map.querySourceFeatures(SIG_SOURCE).length > 0));
    });

    return () => {
      abort.abort();
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
