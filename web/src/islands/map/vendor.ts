// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.37 (K1 §6.1, SIG-UI-097) — the MapLibre ESM split. The renderer is
 * served as three static, self-hosted module files under `/map/vendor/` —
 * `maplibre-gl.mjs`, `maplibre-gl-shared.mjs`, `maplibre-gl-worker.mjs` —
 * emitted by `scripts/prepare-map-vendor.mjs` from the pinned package. The
 * main thread imports the entry module over HTTP; the worker file resolves
 * its own `./maplibre-gl-shared.mjs` import next to itself, so the shared
 * chunk is fetched once and HTTP-cached for the worker realm — never bundled
 * twice into the island (the ≈ 143 KB duplicated-worker defect the K1 split
 * removes, the T2-map `jsInitialBytes` budget).
 *
 * Nothing here imports `maplibre-gl` statically — a static import would drag
 * the whole renderer back into the island chunk. Types are imported
 * type-only.
 */

import type { Map as MapLibreMap } from "maplibre-gl";

/** The runtime module shape the app uses (a subset of the maplibre-gl API). */
export interface MaplibreModule {
  Map: typeof MapLibreMap;
  Popup: typeof import("maplibre-gl").Popup;
  NavigationControl: typeof import("maplibre-gl").NavigationControl;
  AttributionControl: typeof import("maplibre-gl").AttributionControl;
  addProtocol: typeof import("maplibre-gl").addProtocol;
  removeProtocol: typeof import("maplibre-gl").removeProtocol;
  setWorkerUrl: typeof import("maplibre-gl").setWorkerUrl;
}

let cached: Promise<MaplibreModule> | null = null;

/**
 * Load the self-hosted MapLibre ESM entry and pin its worker to the sibling
 * file. Rejects when the vendor assets were not emitted (a dev server before
 * `prepare-map-vendor.mjs` ran, or a build that skipped the step) — the app
 * turns that into the honest "interactive map unavailable" state.
 */
export function loadMaplibre(vendorBase: string): Promise<MaplibreModule> {
  if (!cached) {
    cached = Promise.all([
      import(/* @vite-ignore */ `${vendorBase}maplibre-gl.mjs`),
    ]).then(([mod]) => {
      const m = mod as MaplibreModule;
      m.setWorkerUrl(`${vendorBase}maplibre-gl-worker.mjs`);
      return m;
    });
    // A failed fetch poisons the shared promise; reset so a retry can win.
    cached.catch(() => {
      cached = null;
    });
  }
  return cached;
}
