// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.29 (K6 VIZ-04, SIG-UI-127) — the deferred embedded-map seam. This
 * module is a Vite lazy chunk: `MapIsland`'s `loadDossierEmbed` dynamic
 * import splits it out of the island entry, so the emitted
 * `/_astro/dossier-embed.*.js` shares every common chunk (Preact, MapApp,
 * the model, workspace-state) with `/map/` verbatim — the "same hashed
 * chunks" K6 §5.4 names, HTTP-cached across pages. The MapLibre renderer is
 * never bundled: `loadMaplibre(vendorBase)` fetches the self-hosted
 * `/map/vendor/` split at runtime, the same files the map surface reads.
 *
 * The `/_kit/sig-map-embed.js` shim the sigEnhancementKit build hook writes
 * re-exports this module under a stable name — `<sig-activate>` imports it
 * ONLY after an explicit reader click (SIG-UI-127: no T2 preload).
 *
 * This module must never import the build-time data layer (`lib/data.ts` —
 * fixture constants belong in the props document, not a shipped chunk).
 */

/** @jsxImportSource preact */
import { createElement } from "preact";
import { render } from "preact";
import MapApp from "./MapApp";
import type { MapAppProps } from "./MapApp";

/** The embedded-mode extras the element hands in beside MapAppProps. */
export interface EmbeddedHandlers {
  /** "Close interactive map" — restore the static figure + focus. */
  onClose: () => void;
  /** A mount/render failure the element turns into the honest notice. */
  onFailed: () => void;
}

export type EmbeddedMapProps = MapAppProps & { embedded: EmbeddedHandlers };

/**
 * Mount the K1 map app in `embedded` mode inside `host`. Returns the
 * unmount function (Preact detach — the host itself stays owned by the
 * caller, the static figure beneath it untouched).
 */
export function mountEmbeddedMap(
  host: HTMLElement,
  props: EmbeddedMapProps,
): () => void {
  render(createElement(MapApp, props), host);
  return () => render(null, host);
}
