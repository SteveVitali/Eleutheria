#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * gen-map-styles.mjs — P36.33 (K1 §2.5, SIG-UI-100): emit the basemap style
 * documents at build time, never as JS. Reads ops/basemap.lock.json
 * (sig.basemap-lock/1) — the single pin — and writes:
 *
 *   web/public/map/style-light.json    grayscale flavour, sig:* metadata
 *   web/public/map/style-dark.json     black flavour (K14: Protomaps' dark)
 *   web/public/map/style-context.json  the boundaries fallback (same-origin
 *                                      context.pmtiles + place labels)
 *
 * Content rules (K1 §2.5 verbatim): keep earth/water/muted landcover/roads
 * (casing z11)/admin boundaries/place labels (country, region, locality)/
 * road labels z13/water labels; drop POIs + transit + 3-D buildings (the v4
 * schema emits no POI/transit layers at all); buildings only from z15 at low
 * contrast; labels in English (`lang: "en"`). We additionally drop
 * `address_label` (POI-class) and `roads_shields` (it is the only layer that
 * needs the sprite sheet — the posture serves no sprite).
 *
 * The kill switch (lock `serving.active_source = "context"`): every emitted
 * document's `basemap` source then binds `pmtiles:///tiles/context.pmtiles`,
 * the same-origin fallback — one committed flip repoints the whole pipeline.
 *
 * Usage:
 *   node web/scripts/gen-map-styles.mjs            # emit
 *   node web/scripts/gen-map-styles.mjs --verify   # fail on drift (CI)
 */

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { layers, namedFlavor } from "@protomaps/basemaps";

const REPO = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const LOCK_PATH = join(REPO, "ops", "basemap.lock.json");
const OUT_DIR = join(REPO, "web", "public", "map");

const DROPPED = new Set(["address_label", "roads_shields", "roads_oneway"]);
const MINZOOM_ADJUST = { buildings: 15, roads_labels_major: 13 };

const lock = JSON.parse(readFileSync(LOCK_PATH, "utf-8"));
const active = lock.serving.active_source;
const servedKey =
  (lock.host.served && lock.host.served.key) ||
  lock.host.key_prefix + lock.upstream.reference_build.key;
const BASEMAP_URL =
  active === "basemap"
    ? `pmtiles://${lock.host.origin}/${servedKey}`
    : "pmtiles:///tiles/context.pmtiles";
const CONTEXT_URL = "pmtiles:///tiles/context.pmtiles";
const GLYPHS = lock.glyphs.url_template;

const BASEMAP_ATTRIBUTION =
  "Basemap © OpenStreetMap contributors (ODbL) · Protomaps";
const CONTEXT_ATTRIBUTION =
  "Boundaries: U.S. Census Bureau, Natural Earth (public domain)";

function sigMeta(theme) {
  return {
    "sig:contract": "sig.basemap-style/1",
    "sig:lock": "ops/basemap.lock.json",
    "sig:basemap": {
      active_source: active,
      served_key: active === "basemap" ? servedKey : null,
      reference_build: lock.upstream.reference_build.key,
      host_status: lock.host.create_status,
      theme,
    },
  };
}

function basemapLayers(flavor) {
  // `layers()` needs the flavor OBJECT (namedFlavor) — a bare string is
  // silently ignored and every colour slot serialises as `null` (P36.37 —
  // the emitted styles had never been rendered and carried nine nulls).
  return layers("protomaps", namedFlavor(flavor), { lang: lock.style.lang })
    .filter((l) => !DROPPED.has(l.id))
    .map((l) => {
      let out = l;
      if (MINZOOM_ADJUST[l.id] !== undefined) out = { ...out, minzoom: MINZOOM_ADJUST[l.id] };
      // The emitted layers name the upstream `protomaps` source — the style
      // declares it `basemap` (the lock's kill-switch URL), so repoint the
      // reference (P36.37 — the style had never been rendered before).
      if (out.source === "protomaps") out = { ...out, source: "basemap" };
      // place dots come from icon sprites — the posture serves none; strip the
      // icon-image reference so no sprite sheet is ever needed (K1 §2.1).
      if (out.layout && out.layout["icon-image"] !== undefined) {
        const { "icon-image": _drop, ...layout } = out.layout;
        out = { ...out, layout };
      }
      // Upstream emits `text-font` shapes the committed glyph set cannot
      // honour: non-string entries (a font helper serialises as `null`) and
      // `["case",…]` font-variant expressions. Both are style-validation
      // errors MapLibre refuses (P36.37 hit them on places_country and
      // places_locality), and the glyph manifest carries only Noto Sans
      // Regular + Italic — a non-plain stack pins the committed Regular one.
      if (out.layout && out.layout["text-font"] !== undefined) {
        const tf = out.layout["text-font"];
        if (!Array.isArray(tf) || !tf.every((f) => typeof f === "string" && f.length > 0)) {
          out = { ...out, layout: { ...out.layout, "text-font": ["Noto Sans Regular"] } };
        }
      }
      return out;
    });
}

function basemapStyle(theme, flavor) {
  return {
    version: 8,
    name: `SIG basemap — ${theme}`,
    metadata: sigMeta(theme),
    sources: {
      basemap: {
        type: "vector",
        url: BASEMAP_URL,
        attribution:
          active === "basemap" ? BASEMAP_ATTRIBUTION : CONTEXT_ATTRIBUTION,
      },
    },
    glyphs: GLYPHS,
    layers: basemapLayers(flavor),
  };
}

function contextStyle() {
  return {
    version: 8,
    name: "SIG context fallback — boundaries only",
    metadata: sigMeta("context"),
    sources: {
      context: {
        type: "vector",
        url: CONTEXT_URL,
        attribution: CONTEXT_ATTRIBUTION,
      },
    },
    glyphs: GLYPHS,
    layers: [
      { id: "background", type: "background", paint: { "background-color": "#f2f4f7" } },
      {
        id: "boundary-country",
        type: "line",
        source: "context",
        "source-layer": "boundary",
        filter: ["==", ["get", "level"], "country"],
        paint: { "line-color": "#7e8695", "line-width": 1.2 },
      },
      {
        id: "boundary-state",
        type: "line",
        source: "context",
        "source-layer": "boundary",
        filter: ["==", ["get", "level"], "state"],
        paint: { "line-color": "#9aa3b5", "line-width": 0.8 },
      },
      {
        id: "boundary-county",
        type: "line",
        source: "context",
        "source-layer": "boundary",
        filter: ["==", ["get", "level"], "county"],
        paint: { "line-color": "#c3c9d4", "line-width": 0.5 },
      },
      {
        id: "place-labels",
        type: "symbol",
        source: "context",
        "source-layer": "place",
        layout: {
          "text-field": ["get", "name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": 11,
        },
        paint: { "text-color": "#5a6272", "text-halo-color": "#ffffff", "text-halo-width": 1 },
      },
    ],
  };
}

const outputs = {
  "style-light.json": basemapStyle("light", lock.style.flavours.light),
  "style-dark.json": basemapStyle("dark", lock.style.flavours.dark),
  "style-context.json": contextStyle(),
};

let failed = false;
for (const [name, doc] of Object.entries(outputs)) {
  const text = JSON.stringify(doc, null, 2) + "\n";
  const dest = join(OUT_DIR, name);
  if (process.argv.includes("--verify")) {
    let current = null;
    try {
      current = readFileSync(dest, "utf-8");
    } catch {
      /* absent = drift */
    }
    if (current !== text) {
      console.error(`gen-map-styles --verify: ${name} drifted — re-run the generator`);
      failed = true;
    }
  } else {
    mkdirSync(dirname(dest), { recursive: true });
    writeFileSync(dest, text);
    console.log(`gen-map-styles: wrote ${name} (${doc.layers.length} layers)`);
  }
}
if (failed) process.exit(4);
