// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The interactive infrastructure-map island — the `/map/` T2 app shell
 * (P36.37, K1 MAP-03a; ADR-155's named T2 surface over the P36.36 no-JS
 * baseline).
 *
 * P36.37 migrated this surface to **Preact** (SIG-UI-097 — the only island
 * runtime after migration; React must never reach the /map/ bundle) and the
 * MapLibre ESM split (K1 §6.1: the renderer is served from `/map/vendor/` as
 * static self-hosted modules — `scripts/prepare-map-vendor.mjs` emits them;
 * `loadMaplibre` in `./map/vendor` imports them and pins the worker).
 *
 * The props contract is unchanged where the page consumed it; the selection
 * panel's richer fields (SIG-UI-101) ride the bounded `records` payload in
 * fixtures mode — the tile path projects the same model from `sig.map-tiles/2`
 * properties at runtime.
 */

/** @jsxImportSource preact */
import type { JSX } from "preact";
import MapApp from "./map/MapApp";
import type { MapAppProps, CompartmentOption } from "./map/MapApp";

export type { CompartmentOption };

export type MapIslandProps = MapAppProps;

export default function MapIsland(props: MapIslandProps): JSX.Element {
  return <MapApp {...props} />;
}
