// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P36.37 (K1 MAP-03a, R11-K13-MAP-03a) — the `/map/` T2 app shell in Preact.
 *
 * Owned requirements: SIG-UI-065 (one data hue), SIG-UI-095 (canvas
 * reachability), SIG-UI-097 (runtime dependency discipline), SIG-UI-101
 * (selection panel fields), SIG-UI-102 (synchronized map list), SIG-UI-103
 * (map state round-trip), SIG-UI-104 (filter counts and cannot-apply),
 * SIG-UI-106 (map budgets), SIG-UI-107 (symbol contrast and channels).
 * UXR-13/'records' wording; UXR-18/SIG-UI-068 link targets (never a 404).
 *
 * Enhancement-only: the app mounts over the preserved no-JS document
 * (P36.36); everything it shows is also in the tables below (SIG-UI-050).
 * SSR renders the shell skeleton into the reserved box; MapLibre mounts on
 * client:idle.
 */

/** @jsxImportSource preact */
import { useCallback, useEffect, useMemo, useRef, useState } from "preact/hooks";
import type { JSX } from "preact";
import type {
  Map as MapLibreMap,
  MapGeoJSONFeature,
  StyleSpecification,
} from "maplibre-gl";
import type { Feature as GeoJSONFeature } from "geojson";
import "maplibre-gl/dist/maplibre-gl.css";
import { loadMaplibre } from "./vendor";
import { Protocol } from "pmtiles";
import {
  compartmentAttribution,
  compartmentLayerId,
  compartmentSourceId,
  tileSourceAttribution,
  NATIONAL_CELLS_MAXZOOM,
  PMTILES_PROTOCOL,
} from "../../lib/map-tiles";
import type { CompartmentTileSource } from "../../lib/map-tiles";
import {
  SIG_DATA_HUE,
  SIG_DATA_SEQ_400,
  SIG_DATA_SEQ_700,
  SIG_INK,
  SIG_SURFACE_2,
} from "../../lib/design-tokens";
import {
  evidenceAnchorHref,
  facetNoticeText,
  ISLAND_VIEWS,
  recordRoutes,
  viewportDecimals,
  viewHref,
} from "../../lib/workspace-state/index";
import { withBase } from "../../lib/paths";
import { useMapWorkspace } from "./workspace";
import {
  activeFacetCount,
  buildFacetDict,
  cannotApplyNotes,
  cellSlice,
  cellSliceValue,
  dedupeTileSites,
  effectiveFacets,
  facetCannotApply,
  facetOptionCounts,
  facetOptions,
  geoFailureNote,
  inBounds,
  IN_VIEW_MAX,
  isMapDict,
  myLocationTarget,
  parseSeenRange,
  placeRowsInView,
  recordPasses,
  seenRangeWire,
  selectionFromRecord,
  selectionFromTileProps,
  sheetPeekText,
  siteRowsInView,
  sortInViewRows,
  statusCode,
  STATUS_BY_CODE,
  STATUS_CODE,
  STATUS_TEXT,
  tileFacetExpr,
  tilePlaceRowsInView,
  tileSiteRowsInView,
} from "./model";
import type {
  FacetDict,
  InViewRow,
  InViewSort,
  MapDict,
  MapFacets,
  MapFacetsV2,
  MapRecord,
  SelectionPanelModel,
  TileCellProps,
  TileSiteFeature,
  TileSiteProps,
} from "./model";
import { toCsv, type TableModel, type TableRowModel } from "../../elements/table-model";
import type { StatementRow } from "../../lib/provenance-panel";
import type { MaplibreModule } from "./vendor";

const isBrowser = typeof window !== "undefined";

// ------------------------------------------------------------------ props //

/** One switchable licence compartment (unchanged contract). */
export interface CompartmentOption {
  id: string;
  license: string;
  attribution?: string;
}

export interface MapAppProps {
  tiles: readonly CompartmentTileSource[];
  /** Fixtures-mode payload: the located records with their panel fields. */
  records: readonly MapRecord[];
  /** How many located records the surface holds (canvas label). */
  pointCount: number;
  attribution: string;
  citationHref: string;
  release: string | null;
  compartments: readonly CompartmentOption[];
  /** The emitted basemap style documents (P36.33). */
  styles: { light: string; dark: string; context: string };
  /** The vendored MapLibre ESM split directory (`…/map/vendor/`). */
  vendorBase: string;
  /** The release data dictionary (technology/source labels; optional). */
  dictHref: string;
  /** P37.18: the data as-of line the print view + legend carry. */
  asOf: string;
  /** P37.18: records with no published point in this build (legend line). */
  unplotted: number;
  /** P37.18: jkey → dossier href for tile-path place/jurisdiction links. */
  jurisdictionHrefs: Record<string, string>;
}

// ------------------------------------------------------------ small bits //

const GEOJSON_SOURCE = "sig-infrastructure";
const FOCUS_SOURCE = "sig-focus";
/** P37.18: the hover/keyboard-focus highlight ring (SIG-UI-095 parity for the
 * pointer's hover — a row hover or focus highlights the drawn feature). */
const HOVER_SOURCE = "sig-hover";
const SUMMED_CELLS_SOURCE = "sig-cells-summed";
const SUMMED_CELLS_LAYER = "sig-cells-summed-layer";
const SUMMED_CELLS_LABEL = "sig-cells-summed-label";
const EMPTY_FC: { type: "FeatureCollection"; features: never[] } = {
  type: "FeatureCollection",
  features: [],
};

const VIEW_LABELS: Record<string, string> = {
  list: "List",
  map: "Map",
  network: "Connections",
};

/** The basemap choices `basemap=` round-trips through (0=light, 1=dark). */
const BASEMAPS = [
  { key: "0" as const, label: "Light" },
  { key: "1" as const, label: "Dark" },
];

type BasemapState = "loading" | "ready" | "context" | "unavailable";

function backgroundStyle(): StyleSpecification {
  return {
    version: 8,
    sources: {},
    layers: [
      { id: "sig-bg", type: "background", paint: { "background-color": SIG_SURFACE_2 } },
    ],
  };
}

/** One data hue (SIG-UI-065): every record draws in SIG_DATA_HUE — the
 * technology channel is text/facet/legend, never a categorical colour. The
 * status channel is fill-vs-hollow + ring, not colour (SIG-UI-107). */
const STATUS_LAYERS = (layerId: string, sourceId: string) =>
  [
    // st=0 corroborated — solid disc
    {
      id: `${layerId}-c`,
      type: "circle" as const,
      source: sourceId,
      "source-layer": "sites",
      filter: ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 0]],
      paint: {
        "circle-color": SIG_DATA_HUE,
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3, 10, 6] as never,
        "circle-stroke-color": SIG_DATA_SEQ_700,
        "circle-stroke-width": 0.8,
        "circle-opacity": 0.85,
      },
    },
    // st=1 single source — hollow ring (second channel: no fill)
    {
      id: `${layerId}-1`,
      type: "circle" as const,
      source: sourceId,
      "source-layer": "sites",
      filter: ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 1]],
      paint: {
        "circle-color": "rgba(0,0,0,0)",
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3, 10, 6] as never,
        "circle-stroke-color": SIG_DATA_SEQ_700,
        "circle-stroke-width": 1.6,
      },
    },
    // st=2 contested — solid disc + outer ring (double ring, second channel)
    {
      id: `${layerId}-2`,
      type: "circle" as const,
      source: sourceId,
      "source-layer": "sites",
      filter: ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 2]],
      paint: {
        "circle-color": SIG_DATA_HUE,
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3, 10, 6] as never,
        "circle-stroke-color": SIG_DATA_SEQ_700,
        "circle-stroke-width": 0.8,
      },
    },
    {
      id: `${layerId}-2-ring`,
      type: "circle" as const,
      source: sourceId,
      "source-layer": "sites",
      filter: ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 2]],
      paint: {
        "circle-color": "rgba(0,0,0,0)",
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 6, 10, 9] as never,
        "circle-stroke-color": SIG_INK,
        "circle-stroke-width": 1.4,
      },
    },
    // st=3 candidate — hollow ring, dashed look via dasharray paint? MapLibre
    // circle-stroke has no dasharray → dashed look via thin dashed ring layer.
    {
      id: `${layerId}-3`,
      type: "circle" as const,
      source: sourceId,
      "source-layer": "sites",
      filter: ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 3]],
      paint: {
        "circle-color": "rgba(0,0,0,0)",
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 3, 3, 10, 6] as never,
        "circle-stroke-color": SIG_DATA_SEQ_400,
        "circle-stroke-width": 1.4,
        "circle-stroke-opacity": 0.7,
      },
    },
  ];

// The fixtures GeoJSON path (no tile archives) — same status channel mapping.
const FIXTURE_STATUS_LAYERS = [
  {
    id: "sig-pts-0",
    type: "circle" as const,
    filter: ["==", ["get", "st"], 0],
    paint: {
      "circle-color": SIG_DATA_HUE,
      "circle-radius": 6,
      "circle-stroke-color": SIG_DATA_SEQ_700,
      "circle-stroke-width": 0.8,
      "circle-opacity": 0.85,
    },
  },
  {
    id: "sig-pts-1",
    type: "circle" as const,
    filter: ["==", ["get", "st"], 1],
    paint: {
      "circle-color": "rgba(0,0,0,0)",
      "circle-radius": 6,
      "circle-stroke-color": SIG_DATA_SEQ_700,
      "circle-stroke-width": 1.6,
    },
  },
  {
    id: "sig-pts-2",
    type: "circle" as const,
    filter: ["==", ["get", "st"], 2],
    paint: {
      "circle-color": SIG_DATA_HUE,
      "circle-radius": 6,
      "circle-stroke-color": SIG_DATA_SEQ_700,
      "circle-stroke-width": 0.8,
    },
  },
  {
    id: "sig-pts-2-ring",
    type: "circle" as const,
    filter: ["==", ["get", "st"], 2],
    paint: {
      "circle-color": "rgba(0,0,0,0)",
      "circle-radius": 9,
      "circle-stroke-color": SIG_INK,
      "circle-stroke-width": 1.4,
    },
  },
  {
    id: "sig-pts-3",
    type: "circle" as const,
    filter: ["==", ["get", "st"], 3],
    paint: {
      "circle-color": "rgba(0,0,0,0)",
      "circle-radius": 6,
      "circle-stroke-color": SIG_DATA_SEQ_400,
      "circle-stroke-width": 1.4,
      "circle-stroke-opacity": 0.7,
    },
  },
];


interface OverlaySpec {
  sources: Record<string, import("maplibre-gl").SourceSpecification>;
  layers: import("maplibre-gl").LayerSpecification[];
  sourceIds: string[];
  compartments: string[];
}

/** The overlay sources+layers — merged into every basemap style document so
 * they survive `setStyle` swaps (K1 §2.6). */
function buildOverlay(props: MapAppProps): OverlaySpec {
  const sources: Record<string, import("maplibre-gl").SourceSpecification> = {};
  const layers: import("maplibre-gl").LayerSpecification[] = [];
  const sourceIds: string[] = [];
  const compartments: string[] = [];
  if (props.tiles.length > 0) {
    for (const t of props.tiles) {
      const sourceId = compartmentSourceId(t.compartment);
      const layerId = compartmentLayerId(t.compartment);
      sources[sourceId] = {
        type: "vector",
        url: `${PMTILES_PROTOCOL}${t.path}`,
        attribution: tileSourceAttribution(t),
      };
      layers.push(
        {
          id: `${layerId}-cells`,
          type: "fill",
          source: sourceId,
          "source-layer": "sites",
          filter: ["==", ["get", "tr"], 2],
          paint: { "fill-color": SIG_DATA_HUE, "fill-opacity": 0.18 },
        } as import("maplibre-gl").LayerSpecification,
        ...(STATUS_LAYERS(layerId, sourceId) as unknown as import("maplibre-gl").LayerSpecification[]),
      );
      compartments.push(t.compartment);
      sourceIds.push(sourceId);
    }
    // P37.18: the selection + hover rings draw on the tile path too — the
    // In-view list's select/hover needs a highlight target there as well.
    sources[FOCUS_SOURCE] = { type: "geojson", data: EMPTY_FC };
    sources[HOVER_SOURCE] = { type: "geojson", data: EMPTY_FC };
    layers.push(
      {
        id: "sig-focus-ring",
        type: "circle",
        source: FOCUS_SOURCE,
        paint: {
          "circle-color": "rgba(0,0,0,0)",
          "circle-radius": 12,
          "circle-stroke-color": SIG_INK,
          "circle-stroke-width": 3,
        },
      } as import("maplibre-gl").LayerSpecification,
      {
        id: "sig-hover-ring",
        type: "circle",
        source: HOVER_SOURCE,
        paint: {
          "circle-color": "rgba(0,0,0,0)",
          "circle-radius": 10,
          "circle-stroke-color": SIG_DATA_SEQ_700,
          "circle-stroke-width": 2,
          "circle-stroke-opacity": 0.85,
        },
      } as import("maplibre-gl").LayerSpecification,
    );
    sources[SUMMED_CELLS_SOURCE] = { type: "geojson", data: EMPTY_FC };
    layers.push(
      {
        id: SUMMED_CELLS_LAYER,
        type: "circle",
        source: SUMMED_CELLS_SOURCE,
        maxzoom: NATIONAL_CELLS_MAXZOOM + 1,
        paint: {
          "circle-color": SIG_DATA_HUE,
          "circle-opacity": 0.4,
          "circle-radius": [
            "interpolate", ["linear"], ["^", ["get", "n"], 0.5],
            1, 3, 32, 12, 256, 26,
          ],
          "circle-stroke-color": SIG_DATA_SEQ_700,
          "circle-stroke-width": 0.6,
        },
      } as import("maplibre-gl").LayerSpecification,
      {
        id: SUMMED_CELLS_LABEL,
        type: "symbol",
        source: SUMMED_CELLS_SOURCE,
        minzoom: 5,
        maxzoom: NATIONAL_CELLS_MAXZOOM + 1,
        layout: { "text-field": ["get", "n"], "text-size": 11, "text-allow-overlap": false },
        paint: { "text-color": SIG_INK },
      } as import("maplibre-gl").LayerSpecification,
    );
  } else if (props.records.length > 0) {
    // The fixtures path draws the located records directly — never a cluster
    // (the fixtures set is bounded; every record is selectable, SIG-UI-020).
    sources[GEOJSON_SOURCE] = {
      type: "geojson",
      data: {
        type: "FeatureCollection",
        features: props.records.map((r) => ({
          type: "Feature" as const,
          geometry: { type: "Point" as const, coordinates: [r.lon, r.lat] },
          properties: { id: r.id, st: r.status ? STATUS_CODE[r.status] : 1, tr: r.tier },
        })),
      },
    };
    for (const l of FIXTURE_STATUS_LAYERS) {
      layers.push({ ...l, source: GEOJSON_SOURCE } as import("maplibre-gl").LayerSpecification);
    }
    sources[FOCUS_SOURCE] = { type: "geojson", data: EMPTY_FC };
    sources[HOVER_SOURCE] = { type: "geojson", data: EMPTY_FC };
    layers.push(
      {
        id: "sig-focus-ring",
        type: "circle",
        source: FOCUS_SOURCE,
        paint: {
          "circle-color": "rgba(0,0,0,0)",
          "circle-radius": 12,
          "circle-stroke-color": SIG_INK,
          "circle-stroke-width": 3,
        },
      } as import("maplibre-gl").LayerSpecification,
      {
        id: "sig-hover-ring",
        type: "circle",
        source: HOVER_SOURCE,
        paint: {
          "circle-color": "rgba(0,0,0,0)",
          "circle-radius": 10,
          "circle-stroke-color": SIG_DATA_SEQ_700,
          "circle-stroke-width": 2,
          "circle-stroke-opacity": 0.85,
        },
      } as import("maplibre-gl").LayerSpecification,
    );
    sourceIds.push(GEOJSON_SOURCE);
  }
  return { sources, layers, sourceIds, compartments };
}

/** Merge the overlay spec into a basemap style document. */
function mergeStyleInto(base: StyleSpecification, overlay: OverlaySpec): StyleSpecification {
  return {
    ...base,
    sources: { ...base.sources, ...overlay.sources },
    layers: [...base.layers, ...overlay.layers],
  };
}

// ==================================================================== app //

export default function MapApp(props: MapAppProps): JSX.Element {
  const { state, issues, ignored, update } = useMapWorkspace("map", { release: props.release });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<MapLibreMap | null>(null);
  const mlRef = useRef<MaplibreModule | null>(null);
  const recordById = useMemo(() => new Map(props.records.map((r) => [r.id, r])), [props.records]);
  const overlay = useMemo(() => buildOverlay(props), [props.tiles, props.records]);
  const mergeStyle = useCallback(
    (base: StyleSpecification) => mergeStyleInto(base, overlay),
    [overlay],
  );
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const [drawn, setDrawn] = useState(false);
  const [basemapState, setBasemapState] = useState<BasemapState>("loading");
  const [basemapChoice, setBasemapChoice] = useState<"0" | "1">(state.basemap ?? "0");
  const [tab, setTab] = useState<"view" | "filters" | "selected">("view");
  const [zoom, setZoom] = useState(3);
  const [viewRows, setViewRows] = useState<InViewRow[]>([]);
  const [viewCount, setViewCount] = useState(0);
  const [statusLine, setStatusLine] = useState("");
  // P37.18 (MAP-03b): the list's table view (J5), the mobile bottom sheet
  // snap point (K1 §4.1), the release dictionary, and the drawn-set honesty
  // state (active facets that cannot apply at this zoom — C-03).
  const [viewMode, setViewMode] = useState<"list" | "table">("list");
  const [tableSort, setTableSort] = useState<InViewSort>("distance");
  const [tableDir, setTableDir] = useState<"asc" | "desc">("asc");
  const [snap, setSnap] = useState<"peek" | "half" | "full">("half");
  const [isNarrow, setIsNarrow] = useState(false);
  const [dict, setDict] = useState<MapDict | null>(null);
  const [greyed, setGreyed] = useState(false);
  const [ariaLine, setAriaLine] = useState("");
  const [geoPending, setGeoPending] = useState(false);
  const [geoNote, setGeoNote] = useState<string | null>(null);
  const [selection, setSelection] = useState<SelectionPanelModel | null>(null);
  const [statements, setStatements] = useState<StatementRow[]>([]);
  const popupRef = useRef<import("maplibre-gl").Popup | null>(null);
  const focusReturnRef = useRef<HTMLElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const canvasNoteRef = useRef<HTMLParagraphElement | null>(null);
  const drawnSourceIds = useRef<string[]>([]);
  const tileCompartments = useRef<string[]>([]);
  const moveTimer = useRef<number | null>(null);
  const ariaTimer = useRef<number | null>(null);
  const appliedUrl = useRef<string>("");
  // P37.18 tile-path working state: the deduped drawn sites + cells of the
  // current view, and rk → {props, lngLat} for list-driven selection.
  const tileByRk = useRef<Map<string, { props: TileSiteProps; lngLat: { lng: number; lat: number } }>>(
    new Map(),
  );
  const greyPaints = useRef<Map<string, Record<string, unknown>>>(new Map());

  // ------------------------------------------------------------ facets //
  // P37.18: the v2 facet set adds vendor/operator/source (wire = entity keys
  // / source ids) — applied over the sig.map-tiles/2 props on the tile path.
  const facets: MapFacetsV2 = useMemo(
    () => ({
      technology: state.technology,
      status: state.status,
      seen: parseSeenRange(state.seen),
      vendor: state.vendor,
      operator: state.operator,
      source: state.source,
    }),
    [
      state.technology,
      state.status,
      state.seen,
      state.vendor,
      state.operator,
      state.source,
    ],
  );

  const facetDict: FacetDict = useMemo(() => buildFacetDict(dict), [dict]);

  // Zoom honesty (SIG-UI-104, C-03): a facet that cannot apply at this zoom
  // never silently narrows — it is dropped from the effective set and the
  // drawn layers grey with a note (no hatch).
  const tileMode = props.tiles.length > 0;
  const cannot = useMemo(
    () => cannotApplyNotes(facets, zoom, tileMode),
    [facets, zoom, tileMode],
  );
  const appliedFacets = useMemo(
    () => effectiveFacets(facets, zoom, tileMode),
    [facets, zoom, tileMode],
  );

  const filteredRecords = useMemo(
    () => props.records.filter((r) => recordPasses(r, appliedFacets)),
    [props.records, appliedFacets],
  );

  const activeCompartments = useMemo(
    () =>
      state.collectionSpecified
        ? new Set(state.collection)
        : new Set(props.compartments.map((c) => c.id)),
    [state.collection, state.collectionSpecified, props.compartments],
  );

  // P37.18: the release dictionary (`sig.map-dict/1`) — tile path only; a
  // missing/stale dict degrades to the EMPTY lookups, never a crash.
  useEffect(() => {
    if (!isBrowser || props.tiles.length === 0) return;
    let live = true;
    fetch(props.dictHref)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((doc) => {
        if (live && isMapDict(doc)) setDict(doc);
      })
      .catch(() => {
        /* the dictionary is optional — the facets degrade honestly */
      });
    return () => {
      live = false;
    };
  }, [props.dictHref, props.tiles.length]);

  // P37.18 (K1 §4.1): the mobile bottom sheet — < 960 px the panel becomes a
  // sheet over the canvas; the map pads by the sheet's height so framing
  // never lands under it.
  useEffect(() => {
    if (!isBrowser) return;
    const mq = window.matchMedia("(max-width: 959px)");
    const apply = () => setIsNarrow(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !isNarrow) return;
    const bottom = snap === "peek" ? 88 : snap === "half" ? 260 : 420;
    map.setPadding({ bottom });
  }, [isNarrow, snap, ready]);

  // -------------------------------------------------------- layer style //
  const chooseStyle = useCallback(
    async (choice: "0" | "1"): Promise<{ style: StyleSpecification; state: BasemapState }> => {
      const wanted = choice === "1" ? props.styles.dark : props.styles.light;
      try {
        const r = await fetch(wanted);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const s = (await r.json()) as StyleSpecification;
        return { style: s, state: "ready" };
      } catch {
        // The named flavour is unreachable — the context fallback is the
        // boundaries base (K1 §2.6); never silently blank.
      }
      try {
        const r = await fetch(props.styles.context);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const s = (await r.json()) as StyleSpecification;
        return { style: s, state: "context" };
      } catch {
        return { style: backgroundStyle(), state: "unavailable" };
      }
    },
    [props.styles],
  );

  // -------------------------------------------------------- map create //
  useEffect(() => {
    if (!isBrowser) return;
    const container = containerRef.current;
    if (!container) return;
    let cancelled = false;
    let map: MapLibreMap | null = null;

    // The overlay spec is built ONCE (module-level `buildOverlay`) and merged
    // INTO every style document — style sources/layers survive `setStyle`
    // swaps (the basemap fallback chain), so nothing needs re-installing
    // (K1 §2.6). Sources carry the licence-compartment attribution.
    tileCompartments.current = overlay.compartments;
    drawnSourceIds.current = overlay.sourceIds;

    const selectFeature = (f: MapGeoJSONFeature | undefined) => {
      const id = String((f?.properties as { id?: string })?.id ?? "");
      if (!id || !recordById.has(id)) return;
      update({ focus: id });
    };

    void (async () => {
      try {
        const ml = await loadMaplibre(props.vendorBase);
        if (cancelled) return;
        mlRef.current = ml;
        const protocol = new Protocol();
        ml.addProtocol("pmtiles", protocol.tile);

        // K1 §2.6/§4.1: first paint is immediate — the map opens on the plain
        // background + the record overlays; the named basemap style swaps in
        // once its document arrives, and the error chain below degrades to the
        // boundaries fallback + honest notice when it cannot.
        map = new ml.Map({
          container,
          style: mergeStyle(backgroundStyle()),
          center: state.at ? [state.at.lon, state.at.lat] : [-97.5, 39],
          zoom: state.at?.z ?? 3,
          attributionControl: false,
          fadeDuration: 0,
        });
        mapRef.current = map;
        const markDrawn = (ev?: unknown) => {
          const e = ev as { sourceId?: string; isSourceLoaded?: boolean } | undefined;
          if (
            e &&
            e.isSourceLoaded === true &&
            drawnSourceIds.current.includes(e.sourceId ?? "")
          ) {
            setDrawn(true);
            return;
          }
          if (
            drawnSourceIds.current.some(
              (id) => map!.getSource(id) && map!.isSourceLoaded(id),
            )
          ) {
            setDrawn(true);
          }
        };
        const applyBasemap = (choice: "0" | "1") => {
          void chooseStyle(choice).then(({ style: next, state: bs }) => {
            const m = mapRef.current;
            if (!m) return;
            setBasemapState(bs);
            m.setStyle(mergeStyle(next), { diff: false });
            m.once("style.load", () => markDrawn());
          });
        };
        applyBasemap(state.basemap ?? "0");
        map.addControl(new ml.NavigationControl({ visualizePitch: false }), "top-right");
        map.addControl(
          new ml.AttributionControl({ compact: false, customAttribution: props.attribution }),
          "bottom-right",
        );

        // Basemap failure → the boundaries fallback, then an honest notice
        // (K1 §2.6). Errors attributed to the `basemap`/`context` sources.
        map.on("error", (e) => {
          const sid = (e as { sourceId?: string }).sourceId ?? "";
          if (sid === "basemap") {
            setBasemapState((cur) => {
              if (cur === "context" || cur === "unavailable") return cur;
              void fetch(props.styles.context)
                .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
                .then((style) => {
                  const m = mapRef.current;
                  if (!m) return;
                  m.setStyle(mergeStyle(style as StyleSpecification), { diff: false });
                  setBasemapState("context");
                })
                .catch(() => {
                  const m = mapRef.current;
                  if (!m) return;
                  m.setStyle(mergeStyle(backgroundStyle()), { diff: false });
                  setBasemapState("unavailable");
                });
              return cur;
            });
          } else if (sid === "context") {
            const m = mapRef.current;
            if (m) {
              m.setStyle(mergeStyle(backgroundStyle()), { diff: false });
            }
            setBasemapState("unavailable");
          }
        });

        map.on("load", () => {
          // Click-to-select wiring — registered once; the merged overlay
          // layers persist through every basemap swap (style sources).
          if (props.tiles.length === 0 && props.records.length > 0) {
            for (const layer of ["sig-pts-0", "sig-pts-1", "sig-pts-2", "sig-pts-3"]) {
              map!.on("click", layer, (e) => selectFeature(e.features?.[0]));
              map!.on("mouseenter", layer, () => (map!.getCanvas().style.cursor = "pointer"));
              map!.on("mouseleave", layer, () => (map!.getCanvas().style.cursor = ""));
            }
          }
          const canvas = map!.getCanvas();
          canvas.setAttribute("tabindex", "0");
          canvas.setAttribute(
            "aria-label",
            `Interactive map of ${props.pointCount} located surveillance records. ` +
              "The In view list and the tables below carry the same records.",
          );
          // SIG-UI-095 keyboard contract on the capture path — the renderer's
          // own canvas key handling stops propagation, so a container-level
          // capture listener carries Enter/Escape (Enter → the In-view list;
          // Escape → clear selection and return focus to the invoking row).
          container.addEventListener(
            "keydown",
            (e) => {
              if (e.key === "Enter") {
                // The In-view list is the keyboard equivalent — open its tab
                // first when the selection panel holds it (SIG-UI-095).
                setTab("view");
                requestAnimationFrame(() =>
                  listRef.current?.querySelector<HTMLElement>("[data-row]")?.focus(),
                );
                e.preventDefault();
              } else if (e.key === "Escape") {
                if (state.focus !== null) update({ focus: null });
                focusReturnRef.current?.focus();
              }
            },
            true,
          );
          setReady(true);
          // `data-drawn` latches when any overlay source reports loaded — the
          // basemap swap re-installs the sources, so `sourcedata` (not just
          // `idle`) must drive the check.
          map!.on("idle", markDrawn);
          map!.on("sourcedata", markDrawn);
          markDrawn();
          refreshList();
        });

        map.on("moveend", () => refreshList());
        map.on("zoom", () => setZoom(map!.getZoom()));
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();

    return () => {
      cancelled = true;
      if (moveTimer.current !== null) window.clearTimeout(moveTimer.current);
      map?.remove();
      mapRef.current = null;
      try {
        mlRef.current?.removeProtocol("pmtiles");
      } catch {
        /* already gone */
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --------------------------------------------------- in-view refresh //
  const refreshList = useCallback(() => {
    const map = mapRef.current;
    if (!map) return;
    if (moveTimer.current !== null) window.clearTimeout(moveTimer.current);
    moveTimer.current = window.setTimeout(() => {
      const b = map.getBounds();
      const bounds = { w: b.getWest(), s: b.getSouth(), e: b.getEast(), n: b.getNorth() };
      const c = map.getCenter();
      const z = map.getZoom();
      setZoom(z);
      let line = "";
      if (tileMode) {
        // Tile path (K1 §3.2/§4.6): the cells re-sum in the browser (dedupe
        // (compartment, h3)); the sites list reads the drawn v2 features.
        const hrefs = {
          jurisdictionHref: (jkey: string) =>
            props.jurisdictionHrefs[jkey] ?? null,
          recordPageHref: (rk: string) => {
            const rel = state.release ?? props.release;
            return rel ? (recordRoutes(rel, rk)?.pageHref ?? null) : null;
          },
        };
        if (z <= NATIONAL_CELLS_MAXZOOM) {
          const slice = cellSlice(appliedFacets, facetDict);
          const cells: { props: TileCellProps; compartment: string; lon: number; lat: number }[] =
            [];
          for (const comp of tileCompartments.current) {
            if (!activeCompartments.has(comp)) continue;
            const feats = map.querySourceFeatures(compartmentSourceId(comp), {
              sourceLayer: "cells",
            });
            for (const f of feats) {
              const g = f.geometry as { type?: string; coordinates?: unknown };
              if (g.type !== "Point" || !Array.isArray(g.coordinates)) continue;
              const [lon, lat] = g.coordinates as number[];
              if (!inBounds({ lat, lon }, bounds)) continue;
              cells.push({
                props: (f.properties ?? {}) as TileCellProps,
                compartment: comp,
                lon,
                lat,
              });
            }
          }
          // The drawn sum rides the same slice — the cells' `n` becomes the
          // facet's marginal count, never a joint guess (§3.2). Dedupe is by
          // h3 only: each archive carries its own compartment's cells, so a
          // shared h3 in two compartments sums honestly (never merged bytes).
          const src = map.getSource(SUMMED_CELLS_SOURCE) as
            | { setData?: (d: unknown) => void }
            | undefined;
          if (src?.setData) {
            const dedup = new Map<string, { n: number; lon: number; lat: number }>();
            for (const c of cells) {
              const h3 = String(c.props.h3 ?? "");
              if (h3 === "") continue;
              const d = dedup.get(h3) ?? { n: 0, lon: c.lon, lat: c.lat };
              d.n += cellSliceValue(c.props, slice);
              dedup.set(h3, d);
            }
            const summed = [...dedup.values()].map((d) => ({
              type: "Feature" as const,
              geometry: { type: "Point" as const, coordinates: [d.lon, d.lat] },
              properties: { n: d.n },
            }));
            src.setData({ type: "FeatureCollection", features: summed });
          }
          const { rows, matching } = tilePlaceRowsInView(cells, slice, facetDict, hrefs);
          setViewRows(rows);
          setViewCount(matching);
          line = `${matching} record${matching === 1 ? "" : "s"} in view — grouped by place`;
        } else {
          const centre = { lat: c.lat, lon: c.lng };
          const sites: TileSiteFeature[] = [];
          const byRk = tileByRk.current;
          byRk.clear();
          for (const comp of tileCompartments.current) {
            if (!activeCompartments.has(comp)) continue;
            for (const f of map.querySourceFeatures(compartmentSourceId(comp), {
              sourceLayer: "sites",
            })) {
              const g = f.geometry as { type?: string; coordinates?: unknown };
              let lon: number | null = null;
              let lat: number | null = null;
              if (g.type === "Point" && Array.isArray(g.coordinates)) {
                [lon, lat] = g.coordinates as number[];
              } else if (
                g.type === "Polygon" &&
                Array.isArray(g.coordinates) &&
                Array.isArray((g.coordinates as number[][][])[0])
              ) {
                const ring = (g.coordinates as number[][][])[0];
                const n = ring.length || 1;
                lon = ring.reduce((a, p) => a + p[0]!, 0) / n;
                lat = ring.reduce((a, p) => a + p[1]!, 0) / n;
              }
              if (lon === null || lat === null || !inBounds({ lat, lon }, bounds)) continue;
              const props = (f.properties ?? {}) as TileSiteProps;
              const rk = String(props.rk ?? "");
              if (rk) byRk.set(rk, { props, lngLat: { lng: lon, lat } });
              sites.push({ props, lat, lon, compartment: comp });
            }
          }
          const deduped = dedupeTileSites(sites);
          const { rows, matching } = tileSiteRowsInView(
            deduped,
            appliedFacets,
            facetDict,
            centre,
            hrefs,
          );
          setViewRows(rows);
          setViewCount(matching);
          line = `${matching} record${matching === 1 ? "" : "s"} in view`;
        }
      } else if (z <= NATIONAL_CELLS_MAXZOOM) {
        const { rows, matching } = placeRowsInView(filteredRecords, appliedFacets, bounds);
        setViewRows(rows);
        setViewCount(matching);
        line = `${matching} record${matching === 1 ? "" : "s"} in view — grouped by place`;
      } else {
        const centre = { lat: c.lat, lon: c.lng };
        const { rows, matching } = siteRowsInView(filteredRecords, appliedFacets, bounds, centre);
        setViewRows(rows);
        setViewCount(matching);
        line = `${matching} record${matching === 1 ? "" : "s"} in view`;
      }
      setStatusLine(line);
      // Live region, debounced 1 s (K1 §4.6): the announcements land after
      // the move settles, never mid-gesture.
      if (ariaTimer.current !== null) window.clearTimeout(ariaTimer.current);
      ariaTimer.current = window.setTimeout(() => setAriaLine(line), 1000);
      // SIG-UI-103: the viewport round-trips through `at=` (replaceState —
      // pan/zoom never grows history; precision follows §3.4).
      const d = viewportDecimals(z);
      const r = (v: number) => Math.round(v * 10 ** d) / 10 ** d;
      const at = { z: Math.round(z), lat: r(c.lat), lon: r(c.lng) };
      const href = `at=${at.z}/${at.lat}/${at.lon}`;
      if (href !== appliedUrl.current) {
        appliedUrl.current = href;
        update({ at }, "replace");
      }
    }, 300);
  }, [
    filteredRecords,
    appliedFacets,
    tileMode,
    facetDict,
    activeCompartments,
    state.release,
    props.release,
    props.jurisdictionHrefs,
    update,
  ]);

  // ------------------------------------------------- selection effects //
  useEffect(() => {
    const focus = state.focus;
    if (!isBrowser) return;
    if (focus === null) {
      setSelection(null);
      setStatements([]);
      popupRef.current?.remove();
      popupRef.current = null;
      return;
    }
    const rec = recordById.get(focus);
    const rel = state.release ?? props.release;
    const routes = rel ? recordRoutes(rel, focus) : null;
    if (rec) {
      const model = selectionFromRecord(rec, {
        recordPageHref: routes?.pageHref ?? null,
        disputeHref: withBase(`dispute/?subject=${encodeURIComponent(focus)}`),
      });
      setSelection(model);
      setTab("selected");
      mapRef.current?.jumpTo({
        center: [rec.lon, rec.lat],
        zoom: Math.max(mapRef.current.getZoom(), 9),
      });
      const src = mapRef.current?.getSource(FOCUS_SOURCE) as
        | { setData?: (d: unknown) => void }
        | undefined;
      src?.setData?.({
        type: "FeatureCollection",
        features: [
          {
            type: "Feature",
            geometry: { type: "Point", coordinates: [rec.lon, rec.lat] },
            properties: {},
          },
        ],
      });
      return;
    }
    if (routes) {
      setSelection({
        id: focus,
        label: focus,
        technology: "Loading…",
        operatorText: "",
        jurisdiction: { label: "", href: null },
        sources: [],
        licenceText: null,
        firstSeen: null,
        lastSeen: null,
        precision: "",
        statusText: "",
        recordHref: null,
        listHref: null,
        recordPageHref: routes.pageHref,
        disputeHref: null,
        located: false,
      });
      setTab("selected");
      fetch(routes.jsonHref)
        .then((r) => {
          if (!r.ok) throw new Error(`HTTP ${r.status}`);
          return r.json();
        })
        .then((record) => {
          const label =
            (record?.label?.text as string | null | undefined) ??
            (record?.entity_id as string | undefined) ??
            focus;
          const loc = record?.location as { lat?: number; lon?: number } | undefined;
          setSelection({
            id: focus,
            label,
            technology: String(record?.entity_type ?? "record"),
            operatorText: OPERATOR_FALLBACK,
            jurisdiction: {
              label: String(record?.jurisdiction?.id ?? ""),
              href: null,
            },
            sources: [],
            licenceText: null,
            firstSeen: null,
            lastSeen: null,
            precision: String(loc?.lat !== undefined ? "" : "no published point"),
            statusText: "",
            recordHref: null,
            listHref: null,
            recordPageHref: routes.pageHref,
            disputeHref: withBase(`dispute/?subject=${encodeURIComponent(focus)}`),
            located: typeof loc?.lat === "number",
          });
          setStatements(
            (Array.isArray(record?.claim_statements) ? record.claim_statements : []) as StatementRow[],
          );
          if (typeof loc?.lat === "number" && typeof loc?.lon === "number") {
            mapRef.current?.jumpTo({
              center: [loc.lon, loc.lat],
              zoom: Math.max(mapRef.current.getZoom(), 9),
            });
          }
        })
        .catch(() => {
          setSelection((cur) =>
            cur
              ? {
                  ...cur,
                  technology: "",
                  precision:
                    "The released record could not be loaded from this surface — the record page is the authoritative route.",
                }
              : cur,
          );
        });
      return;
    }
    setSelection({
      id: focus,
      label: focus,
      technology: "",
      operatorText: "",
      jurisdiction: { label: "", href: null },
      sources: [],
      licenceText: null,
      firstSeen: null,
      lastSeen: null,
      precision: "This record is not in the current map view.",
      statusText: "",
      recordHref: null,
      listHref: null,
      recordPageHref: null,
      disputeHref: null,
      located: false,
    });
  }, [state.focus, state.release, props.release, recordById]);

  // P37.18 (K1 §4.6): selecting a record scrolls its In-view row into view.
  useEffect(() => {
    if (!isBrowser || state.focus === null) return;
    listRef.current
      ?.querySelector<HTMLElement>(`[data-record-id="${CSS.escape(state.focus)}"]`)
      ?.scrollIntoView({ block: "nearest" });
  }, [state.focus, viewRows]);

  // ---------------------------------------------- tile-prop selection //
  const selectTileProps = useCallback(
    (p: Record<string, unknown>, lngLat: { lng: number; lat: number }) => {
      const rk = String(p.rk ?? "");
      const rel = state.release ?? props.release;
      const routes = rel && rk ? recordRoutes(rel, rk) : null;
      const model = selectionFromTileProps(
        p as Parameters<typeof selectionFromTileProps>[0],
        {
          recordPageHref: routes?.pageHref ?? null,
          disputeHref: rk ? withBase(`dispute/?subject=${encodeURIComponent(rk)}`) : null,
        },
      );
      setSelection(model);
      setTab("selected");
      // Small anchored popup: title + "Details →" (K1 §4.5). DOM-only, text.
      const ml = mlRef.current;
      const map = mapRef.current;
      if (ml && map) {
        const el = document.createElement("div");
        el.className = "sig-map-popup";
        const h = document.createElement("h3");
        h.textContent = model.label;
        el.appendChild(h);
        const a = document.createElement("a");
        a.href = "#";
        a.textContent = "Details →";
        a.addEventListener("click", (ev) => {
          ev.preventDefault();
          setTab("selected");
        });
        el.appendChild(a);
        popupRef.current?.remove();
        const popup = new ml.Popup({ closeButton: true })
          .setLngLat([lngLat.lng, lngLat.lat])
          .setDOMContent(el)
          .addTo(map);
        popupRef.current = popup;
      }
    },
    [state.release, props.release],
  );

  // Wire tile-layer clicks after the map loads (kept out of the effect's
  // dependency churn by a registration helper the loader also re-runs after
  // a basemap fallback swap).
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready || props.tiles.length === 0) return;
    const layerIds = tileCompartments.current.flatMap((c) => [
      compartmentLayerId(c),
      `${compartmentLayerId(c)}-cells`,
    ]);
    const open = (e: { features?: MapGeoJSONFeature[]; lngLat: { lng: number; lat: number } }) => {
      const f = e.features?.[0];
      if (!f) return;
      selectTileProps((f.properties ?? {}) as Record<string, unknown>, e.lngLat);
    };
    for (const id of layerIds) {
      map.on("click", id, open);
      map.on("mouseenter", id, () => (map.getCanvas().style.cursor = "pointer"));
      map.on("mouseleave", id, () => (map.getCanvas().style.cursor = ""));
    }
    return () => {
      for (const id of layerIds) map.off("click", id, open);
    };
  }, [ready, props.tiles.length, selectTileProps]);

  // ------------------------------------------- compartment + facet fx //
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const facetExpr = tileMode ? tileFacetExpr(appliedFacets, facetDict) : null;
    for (const comp of tileCompartments.current) {
      const layerId = compartmentLayerId(comp);
      for (const suffix of ["", "-c", "-1", "-2", "-2-ring", "-3", "-cells"]) {
        const id = `${layerId}${suffix}`;
        if (map.getLayer(id)) {
          map.setLayoutProperty(id, "visibility", activeCompartments.has(comp) ? "visible" : "none");
        }
      }
    }
    // Facet narrowing on the drawn site layers (sig.map-tiles/2 props).
    if (tileMode) {
      for (const comp of tileCompartments.current) {
        const layerId = compartmentLayerId(comp);
        const statusBases: Record<string, unknown[]> = {
          "": ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 0]],
          "-c": ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 0]],
          "-1": ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 1]],
          "-2": ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 2]],
          "-2-ring": ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 2]],
          "-3": ["all", ["!=", ["get", "tr"], 2], ["==", ["get", "st"], 3]],
          "-cells": ["==", ["get", "tr"], 2],
        };
        for (const [suffix, base] of Object.entries(statusBases)) {
          const id = `${layerId}${suffix}`;
          if (!map.getLayer(id)) continue;
          map.setFilter(id as never, facetExpr ? (["all", base, facetExpr] as never) : (base as never));
        }
      }
    }
    // Zoom honesty (C-03): active facets that cannot apply grey the drawn
    // layers — desaturated, never hatched; the note names them.
    const wantGrey = cannot.length > 0;
    if (wantGrey !== greyed || (wantGrey && greyPaints.current.size === 0)) {
      const GREY = "hsl(220deg 8% 55%)";
      const ids = tileMode
        ? [
            SUMMED_CELLS_LAYER,
            SUMMED_CELLS_LABEL,
            ...tileCompartments.current.flatMap((comp) =>
              ["", "-c", "-1", "-2", "-2-ring", "-3", "-cells"].map(
                (s) => `${compartmentLayerId(comp)}${s}`,
              ),
            ),
          ]
        : ["sig-pts-0", "sig-pts-1", "sig-pts-2", "sig-pts-2-ring", "sig-pts-3"];
      if (wantGrey) {
        for (const id of ids) {
          if (!map.getLayer(id)) continue;
          const l = map.getLayer(id) as { type?: string };
          const props =
            l.type === "circle"
              ? ["circle-color", "circle-stroke-color"]
              : l.type === "fill"
                ? ["fill-color"]
                : l.type === "symbol"
                  ? ["text-color"]
                  : [];
          const saved: Record<string, unknown> = {};
          for (const p of props) {
            saved[p] = map.getPaintProperty(id, p as never);
            map.setPaintProperty(id, p as never, GREY as never);
          }
          greyPaints.current.set(id, saved);
        }
      } else {
        for (const [id, saved] of greyPaints.current) {
          if (!map.getLayer(id)) continue;
          for (const [p, v] of Object.entries(saved)) {
            map.setPaintProperty(id, p as never, v as never);
          }
        }
        greyPaints.current.clear();
      }
      setGreyed(wantGrey);
    }
    // Fixtures path: the drawn point set re-filters client-side (few records).
    const src = map.getSource(GEOJSON_SOURCE) as { setData?: (d: unknown) => void } | undefined;
    if (src?.setData && props.tiles.length === 0) {
      src.setData({
        type: "FeatureCollection",
        features: filteredRecords.map((r) => ({
          type: "Feature" as const,
          geometry: { type: "Point" as const, coordinates: [r.lon, r.lat] },
          properties: { id: r.id, st: r.status ? STATUS_CODE[r.status] : 1, tr: r.tier },
        })),
      });
    }
    refreshList();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCompartments, filteredRecords, appliedFacets, facetDict, cannot.length, ready, tileMode]);

  // --------------------------------------------------------- keyboard //
  // SIG-UI-095: features reachable as focusable list items; Escape returns
  // focus; pan has a single-pointer alternative (the pan pad below + arrow
  // keys on the canvas — MapLibre's own keyboard handler).
  const onCanvasKeyDown = (e: JSX.TargetedKeyboardEvent<HTMLDivElement>) => {
    if (e.key === "Enter") {
      const first = listRef.current?.querySelector<HTMLElement>("[data-row]");
      first?.focus();
    } else if (e.key === "Escape") {
      if (state.focus !== null) update({ focus: null });
      focusReturnRef.current?.focus();
    }
  };
  // P37.18 (K1 §4.6/§4.7): roving arrow-key navigation inside the In-view
  // list; Escape clears the selection and returns focus to the invoking row
  // (J4); a row hover/focus draws the highlight ring where a point is known.
  const moveRowFocus = (from: HTMLElement, delta: number) => {
    const rows = [...(listRef.current?.querySelectorAll<HTMLElement>("[data-row]") ?? [])];
    const i = rows.indexOf(from);
    const next = rows[i + delta];
    next?.querySelector<HTMLElement>("button, a")?.focus();
  };
  const setHoverPoint = (row: InViewRow | null) => {
    const src = mapRef.current?.getSource(HOVER_SOURCE) as
      | { setData?: (d: unknown) => void }
      | undefined;
    src?.setData?.(
      row && typeof row.lat === "number" && typeof row.lon === "number"
        ? {
            type: "FeatureCollection",
            features: [
              {
                type: "Feature",
                geometry: { type: "Point", coordinates: [row.lon, row.lat] },
                properties: {},
              },
            ],
          }
        : EMPTY_FC,
    );
  };
  const onRowKeyDown = (e: JSX.TargetedKeyboardEvent<HTMLLIElement>) => {
    const li = e.currentTarget;
    if (e.key === "Escape") {
      focusReturnRef.current?.focus();
      if (state.focus !== null) update({ focus: null });
    } else if (e.key === "ArrowDown") {
      moveRowFocus(li, 1);
      e.preventDefault();
    } else if (e.key === "ArrowUp") {
      moveRowFocus(li, -1);
      e.preventDefault();
    } else if (e.key === "Home") {
      listRef.current
        ?.querySelector<HTMLElement>("[data-row] button, [data-row] a")
        ?.focus();
      e.preventDefault();
    } else if (e.key === "End") {
      const rows = [...(listRef.current?.querySelectorAll<HTMLElement>("[data-row]") ?? [])];
      rows[rows.length - 1]?.querySelector<HTMLElement>("button, a")?.focus();
      e.preventDefault();
    }
  };
  const selectRow = (row: InViewRow, el: HTMLElement | null) => {
    if (el) focusReturnRef.current = el;
    if (row.selectId) {
      const hit = tileByRk.current.get(row.selectId);
      if (tileMode && hit) {
        selectTileProps(hit.props as Record<string, unknown>, hit.lngLat);
        if (isNarrow) setSnap("half");
      } else {
        update({ focus: row.selectId });
        if (isNarrow) setSnap("half");
      }
    }
  };
  const panBy = (dx: number, dy: number) => mapRef.current?.panBy([dx, dy]);

  // P37.72 (D-K1-7, K1 §4.1/§4.2) — 'My location': a ONE-SHOT browser
  // geolocation read after this explicit click that only pans the map. The
  // position never leaves the browser — never sent to SIG, never stored,
  // never marked on the canvas — and no 'cameras near you' list/count/alert/
  // proximity notice is produced. The SIG-GOV-017 analysis this honours:
  // docs/build/reports/p37.72-gov017-analysis/PACKET.md.
  const locateMe = () => {
    if (geoPending) return;
    const geo = typeof navigator !== "undefined" ? navigator.geolocation : undefined;
    if (!geo) {
      setGeoNote(geoFailureNote("unsupported"));
      return;
    }
    setGeoPending(true);
    setGeoNote(null);
    geo.getCurrentPosition(
      (pos) => {
        setGeoPending(false);
        const map = mapRef.current;
        if (!map) return;
        map.easeTo(
          myLocationTarget(pos.coords.longitude, pos.coords.latitude, map.getZoom()),
        );
      },
      (err) => {
        setGeoPending(false);
        setGeoNote(
          geoFailureNote(
            err.code === err.PERMISSION_DENIED
              ? "denied"
              : err.code === err.TIMEOUT
                ? "timeout"
                : "unavailable",
          ),
        );
      },
      // No high-accuracy GPS fix is needed for a framing pan; a cached
      // position is fine and faster. One shot — never watchPosition.
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 300_000 },
    );
  };

  // P37.18 (K1 §4.6): "Download this view" — the in-view rows as CSV with
  // ADR-224's `#` licence provenance lines; the canvas is never downloaded.
  const downloadView = () => {
    const columns = [
      { index: 0, id: "record", label: "Record" },
      { index: 1, id: "technology", label: "Technology" },
      { index: 2, id: "operator", label: "Operator" },
      { index: 3, id: "status", label: "Status" },
      { index: 4, id: "distance_km", label: "Distance (km)" },
      { index: 5, id: "licence", label: "Licence" },
    ];
    const rows: TableRowModel[] = sortedRows.map((r) => {
      // The row's licence is its compartment's SPDX when the wire carries no
      // per-row line — the compartment licence IS what the row ships under.
      const licence =
        r.licence ?? props.compartments.find((c) => c.id === r.compartment)?.license ?? null;
      return {
        cells: [
          r.selectId ?? r.id,
          r.technology ?? r.meta,
          r.operator ?? "",
          r.statusText ?? "",
          r.selectId ? r.distanceKm.toFixed(2) : "",
          licence ?? "",
        ],
        facets: {},
        licences: licence ? [licence] : [],
        ...(r.compartment ? { compartment: r.compartment } : {}),
      };
    });
    const model: TableModel = { columns, rows };
    const label = rowsArePlaces
      ? "map places-in-view list"
      : "map records-in-view list";
    const csv = toCsv(model, rows.map((_, i) => i), columns.map((c) => c.id), label);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    a.download = "sig-map-in-view.csv";
    a.click();
    URL.revokeObjectURL(a.href);
  };
  const printView = () => window.print();

  // ------------------------------------------------------------- misc //
  const toggleCompartment = (id: string) => {
    const next = new Set(activeCompartments);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    const full = next.size === props.compartments.length;
    update({ collection: full ? [] : [...next], collectionSpecified: !full });
  };

  const toggleFacetValue = (
    facet: "technology" | "status" | "vendor" | "operator" | "source",
    value: string,
  ) => {
    const cur = facets[facet] as string[];
    const next = cur.includes(value) ? cur.filter((v) => v !== value) : [...cur, value];
    update({ [facet]: next });
  };

  const seenCannot = facetCannotApply("seen", zoom);
  const techOptions = facetOptions(filteredRecords, (r) => r.technology);
  const techCounts = facetOptionCounts(filteredRecords, (r) => r.technology);
  const statusCounts = facetOptionCounts(filteredRecords, (r) => r.status);
  // P37.18: tile-path facet options resolve through the dictionary — the
  // national totals are dict's measured counts, the in-view counts come from
  // the drawn features (tileByRk holds the current viewport set).
  const tileTechOptions = tileMode
    ? [...facetDict.techCodeBySlug.keys()].sort((a, b) => a.localeCompare(b))
    : [];
  const tileTechCounts = new Map<string, number>();
  const tileStatusCounts = new Map<string, number>();
  const tileVendorCounts = new Map<string, number>();
  const tileOperatorCounts = new Map<string, number>();
  const tileSourceCounts = new Map<string, number>();
  if (tileMode) {
    for (const { props: p } of tileByRk.current.values()) {
      if (typeof p.tc === "number" && p.tc > 0) {
        const slug = facetDict.techSlugByCode.get(p.tc) ?? `code ${p.tc}`;
        tileTechCounts.set(slug, (tileTechCounts.get(slug) ?? 0) + 1);
      }
      if (typeof p.st === "number") {
        const st = STATUS_BY_CODE[p.st];
        if (st) tileStatusCounts.set(st, (tileStatusCounts.get(st) ?? 0) + 1);
      }
      if (typeof p.vd === "number") {
        const v = facetDict.vendorBySlot.get(p.vd);
        if (v) tileVendorCounts.set(v.key, (tileVendorCounts.get(v.key) ?? 0) + 1);
      }
      if (typeof p.oe === "string" && p.oe !== "") {
        tileOperatorCounts.set(p.oe, (tileOperatorCounts.get(p.oe) ?? 0) + 1);
      }
      if (typeof p.sr === "number") {
        const s = facetDict.sourceByIndex.get(p.sr);
        if (s) tileSourceCounts.set(s.id, (tileSourceCounts.get(s.id) ?? 0) + 1);
      }
    }
  }
  const sortedRows = useMemo(
    () => sortInViewRows(viewRows, tableSort, tableDir),
    [viewRows, tableSort, tableDir],
  );
  const activeFilters = activeFacetCount(facets);

  // ----------------------------------------------------------- render //
  // SSR (client:idle): the shell skeleton — the reserved box the app mounts
  // into; the tables below remain the no-JS equivalent (P36.36).
  if (!isBrowser) {
    return (
      <div className="sig-map-app" data-testid="map-island-root">
        <div className="sig-map-app__shell">
          <p className="sig-island__note">
            The interactive map loads when JavaScript runs — the tables below
            carry the same records and are the complete equivalent.
          </p>
          <div className="sig-map-island__canvas sig-map-app__canvas-skeleton" aria-hidden="true" />
        </div>
      </div>
    );
  }

  const rowsArePlaces = zoom <= NATIONAL_CELLS_MAXZOOM;

  return (
    <div data-testid="map-island-root" className="sig-map-app">
      <nav className="sig-view-links" aria-label="Investigation views" data-testid="island-view-links">
        {ISLAND_VIEWS.map((v) =>
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

      {cannot.length > 0 && (
        <p className="sig-island__note" role="status" data-testid="filters-cannot-apply">
          {cannot.map((n) => n.note).join(" ")}
        </p>
      )}
      {basemapState === "context" && (
        <p className="sig-island__note" role="status" data-testid="basemap-fallback">
          The basemap is unavailable — the map shows the boundaries fallback.
        </p>
      )}
      {basemapState === "unavailable" && (
        <p className="sig-island__note" role="status" data-testid="basemap-unavailable">
          The basemap is unavailable — records draw over a plain background.
        </p>
      )}

      <div className="sig-map-app__shell">
        <div
          className={
            isNarrow ? "sig-map-app__panel sig-map-app__panel--sheet" : "sig-map-app__panel"
          }
          data-snap={isNarrow ? snap : undefined}
          data-testid="map-sheet"
        >
          {isNarrow && (
            <div className="sig-map-app__sheetbar" data-testid="sheet-bar">
              <button
                type="button"
                className="sig-map-app__grabber"
                aria-label={
                  snap === "full" ? "Collapse the panel sheet" : "Expand the panel sheet"
                }
                data-testid="sheet-grabber"
                onClick={() =>
                  setSnap(snap === "peek" ? "half" : snap === "half" ? "full" : "peek")
                }
              >
                <span className="sig-map-app__grabber-mark" aria-hidden="true" />
              </button>
              <span className="sig-map-app__peek" data-testid="sheet-peek" aria-live="off">
                {sheetPeekText(viewCount, activeFilters)}
              </span>
              <span className="sig-map-app__snaps" role="group" aria-label="Sheet position">
                {(["peek", "half", "full"] as const).map((s) => (
                  <button
                    key={s}
                    type="button"
                    className={snap === s ? "sig-map-app__tool is-active" : "sig-map-app__tool"}
                    aria-pressed={snap === s}
                    data-testid={`sheet-snap-${s}`}
                    onClick={() => setSnap(s)}
                  >
                    {s === "peek" ? "Peek" : s === "half" ? "Half" : "Full"}
                  </button>
                ))}
              </span>
            </div>
          )}
          <div className="sig-map-app__tabs" role="tablist" aria-label="Map panels">
            {(
              [
                ["view", rowsArePlaces ? "Places in view" : "In view"],
                ["filters", "Filters"],
                ["selected", "Selected"],
              ] as const
            ).map(([id, label]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={tab === id}
                className={tab === id ? "sig-map-app__tab is-active" : "sig-map-app__tab"}
                data-testid={`map-tab-${id}`}
                onClick={() => setTab(id)}
              >
                {label}
              </button>
            ))}
          </div>

          {tab === "view" && (
            <div className="sig-map-app__tabpanel" role="tabpanel" ref={listRef}>
              <p className="sig-map-app__status" role="status" data-testid="inview-status">
                {statusLine || `${viewCount} records in view`}
              </p>
              <p className="sig-map-app__viewtools">
                <button
                  type="button"
                  className={viewMode === "list" ? "sig-map-app__tool is-active" : "sig-map-app__tool"}
                  aria-pressed={viewMode === "list"}
                  data-testid="inview-list-toggle"
                  onClick={() => setViewMode("list")}
                >
                  List
                </button>{" "}
                <button
                  type="button"
                  className={viewMode === "table" ? "sig-map-app__tool is-active" : "sig-map-app__tool"}
                  aria-pressed={viewMode === "table"}
                  data-testid="inview-table-toggle"
                  onClick={() => setViewMode("table")}
                >
                  Table
                </button>{" "}
                <button
                  type="button"
                  className="sig-map-app__tool"
                  data-testid="download-view"
                  onClick={downloadView}
                >
                  Download this view (CSV)
                </button>{" "}
                <button
                  type="button"
                  className="sig-map-app__tool"
                  data-testid="print-view"
                  onClick={printView}
                >
                  Print this view
                </button>
              </p>
              {viewMode === "table" ? (
                <div className="sig-map-app__table-wrap">
                  <table className="sig-map-app__table" data-testid="inview-table">
                    <thead>
                      <tr>
                        {(
                          [
                            ["label", rowsArePlaces ? "Place" : "Record"],
                            ["technology", "Technology"],
                            ["status", "Status"],
                            ["distance", "Distance (km)"],
                          ] as const
                        ).map(([key, label]) => (
                          <th
                            key={key}
                            scope="col"
                            aria-sort={
                              tableSort === key
                                ? tableDir === "desc"
                                  ? "descending"
                                  : "ascending"
                                : "none"
                            }
                          >
                            <button
                              type="button"
                              className="sig-map-app__sort"
                              data-testid={`inview-sort-${key}`}
                              onClick={() => {
                                if (tableSort === key) {
                                  setTableDir(tableDir === "asc" ? "desc" : "asc");
                                } else {
                                  setTableSort(key);
                                  setTableDir("asc");
                                }
                              }}
                            >
                              {label}
                            </button>
                          </th>
                        ))}
                        <th scope="col">Open</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sortedRows.map((row) => (
                        <tr key={row.id}>
                          <th scope="row">
                            {row.selectId ? (
                              <button
                                type="button"
                                className="sig-map-app__row-main"
                                onClick={(e) => selectRow(row, e.currentTarget)}
                              >
                                {row.label}
                              </button>
                            ) : (
                              row.label
                            )}
                          </th>
                          <td>{row.technology ?? "—"}</td>
                          <td>{row.statusText ?? "—"}</td>
                          <td>{row.selectId ? row.distanceKm.toFixed(1) : "—"}</td>
                          <td>
                            {row.selectId && row.listHref ? (
                              <a href={row.listHref}>Open record</a>
                            ) : null}
                            {row.dossierHref ? <a href={row.dossierHref}>Dossier</a> : null}
                          </td>
                        </tr>
                      ))}
                      {sortedRows.length === 0 && (
                        <tr>
                          <td colspan={5}>No published records in this view.</td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              ) : (
                <ul className="sig-map-app__list" data-testid="inview-list" aria-label="Records in view">
                  {viewRows.map((row) => (
                    <li
                      key={row.id}
                      data-row
                      data-record-id={row.selectId ?? undefined}
                      className="sig-map-app__row"
                      tabIndex={0}
                      onKeyDown={onRowKeyDown}
                      onMouseEnter={() => setHoverPoint(row)}
                      onMouseLeave={() => setHoverPoint(null)}
                      onFocus={() => setHoverPoint(row)}
                      onBlur={() => setHoverPoint(null)}
                    >
                      {row.selectId ? (
                        <button
                          type="button"
                          className="sig-map-app__row-main"
                          data-testid={`inview-select-${row.id}`}
                          onClick={(e) => selectRow(row, e.currentTarget)}
                        >
                          {row.label}
                        </button>
                      ) : (
                        <button
                          type="button"
                          className="sig-map-app__row-main"
                          onClick={() => {
                            if (row.bbox) {
                              mapRef.current?.fitBounds(
                                [
                                  [row.bbox[0], row.bbox[1]],
                                  [row.bbox[2], row.bbox[3]],
                                ],
                                { padding: 40 },
                              );
                            } else if (row.frame) {
                              mapRef.current?.easeTo({
                                center: [row.frame.lon, row.frame.lat],
                                zoom: row.frame.zoom,
                              });
                            }
                          }}
                        >
                          {row.label}
                        </button>
                      )}
                      <span className="sig-map-app__row-meta">{row.meta}</span>
                      <span className="sig-map-app__row-links">
                        {row.selectId && row.listHref ? (
                          <a href={row.listHref} data-testid={`inview-record-${row.id}`}>
                            Open record
                          </a>
                        ) : null}
                        {row.dossierHref ? <a href={row.dossierHref}>Dossier</a> : null}
                      </span>
                    </li>
                  ))}
                  {viewRows.length === 0 && (
                    <li className="sig-map-app__row" data-testid="inview-empty">
                      No published records in this view — the places table below
                      lists every jurisdiction.
                    </li>
                  )}
                </ul>
              )}
              {viewCount > IN_VIEW_MAX && (
                <p className="sig-map-app__status">
                  Showing {IN_VIEW_MAX} of {viewCount} — zoom in or filter to
                  narrow the list; the{" "}
                  <a href="#places-heading">places table</a> lists every
                  jurisdiction.
                </p>
              )}
            </div>
          )}

          {tab === "filters" && (
            <div className="sig-map-app__tabpanel" role="tabpanel" data-testid="map-filters">
              {props.compartments.length > 0 && (
                <fieldset className="sig-island__compartments" data-testid="map-compartments">
                  <legend>Licence compartments</legend>
                  {props.compartments.map((c) => (
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

              <fieldset className="sig-map-app__facet">
                <legend>Technology — {techOptions.length} in view</legend>
                {techOptions.map((t) => (
                  <label key={t} className="sig-map-app__option">
                    <input
                      type="checkbox"
                      checked={facets.technology.includes(t)}
                      onChange={() => toggleFacetValue("technology", t)}
                      data-testid={`filter-tech-${t}`}
                    />{" "}
                    {t} <span className="sig-map-app__count">({techCounts.get(t) ?? 0})</span>
                  </label>
                ))}
              </fieldset>

              <fieldset className="sig-map-app__facet">
                <legend>Status</legend>
                {(Object.keys(STATUS_TEXT) as (keyof typeof STATUS_TEXT)[]).map((s) => (
                  <label key={s} className="sig-map-app__option">
                    <input
                      type="checkbox"
                      checked={facets.status.includes(s)}
                      onChange={() => toggleFacetValue("status", s)}
                      data-testid={`filter-status-${s}`}
                    />{" "}
                    {STATUS_TEXT[s]}{" "}
                    <span className="sig-map-app__count">({statusCounts.get(s) ?? 0})</span>
                  </label>
                ))}
              </fieldset>

              <fieldset className="sig-map-app__facet" data-testid="filter-seen-fieldset">
                <legend>Seen</legend>
                {seenCannot ? (
                  <p className="sig-map-app__cannot" data-testid="filter-seen-cannot">
                    {seenCannot} — matching records are listed in{" "}
                    <a href={viewHref(state, "list")}>Search</a>.
                  </p>
                ) : (
                  <SeenRangeEditor
                    value={facets.seen}
                    onApply={(seen) => update({ seen: seenRangeWire(seen) })}
                  />
                )}
              </fieldset>

              {tileMode && dict !== null && (
                <>
                  <fieldset className="sig-map-app__facet" data-testid="filter-vendor">
                    <legend>Vendor — {facetDict.vendorBySlot.size} named</legend>
                    {[...facetDict.vendorBySlot.values()].map((v) => (
                      <label key={v.key} className="sig-map-app__option">
                        <input
                          type="checkbox"
                          checked={facets.vendor.includes(v.key)}
                          onChange={() => toggleFacetValue("vendor", v.key)}
                          data-testid={`filter-vendor-${v.key}`}
                        />{" "}
                        {v.label}{" "}
                        <span className="sig-map-app__count">
                          ({tileVendorCounts.get(v.key) ?? 0} in view
                          {dict.totals.by_vendor_slot?.[String(v.slot)] !== undefined
                            ? ` · ${dict.totals.by_vendor_slot[String(v.slot)]} nationwide`
                            : ""}
                          )
                        </span>
                      </label>
                    ))}
                  </fieldset>
                  <fieldset className="sig-map-app__facet" data-testid="filter-operator">
                    <legend>Operator</legend>
                    {[...tileOperatorCounts.keys()].sort().map((k) => (
                      <label key={k} className="sig-map-app__option">
                        <input
                          type="checkbox"
                          checked={facets.operator.includes(k)}
                          onChange={() => toggleFacetValue("operator", k)}
                          data-testid={`filter-operator-${k}`}
                        />{" "}
                        {k} <span className="sig-map-app__count">({tileOperatorCounts.get(k)})</span>
                      </label>
                    ))}
                    {tileOperatorCounts.size === 0 && (
                      <p className="sig-map-app__cannot">
                        No resolved operator keys in view — operators resolve
                        through the entity build; text operators stay in the
                        list rows.
                      </p>
                    )}
                  </fieldset>
                  <fieldset className="sig-map-app__facet" data-testid="filter-source">
                    <legend>Source — {facetDict.sourceIndexById.size} in this release</legend>
                    {[...facetDict.sourceByIndex.values()].map((s) => (
                      <label key={s.id} className="sig-map-app__option">
                        <input
                          type="checkbox"
                          checked={facets.source.includes(s.id)}
                          onChange={() => toggleFacetValue("source", s.id)}
                          data-testid={`filter-source-${s.id}`}
                        />{" "}
                        {s.name}{" "}
                        <span className="sig-map-app__count">
                          ({tileSourceCounts.get(s.id) ?? 0} in view{s.licence ? ` · ${s.licence}` : ""})
                        </span>
                      </label>
                    ))}
                  </fieldset>
                </>
              )}
              {(!tileMode || dict === null) && (
                <fieldset className="sig-map-app__facet" data-testid="filter-future">
                  <legend>Vendor · operator · source</legend>
                  <p className="sig-map-app__cannot">
                    {tileMode
                      ? "These facets resolve through the release dictionary — it has not loaded yet, so they stay named here, never faked."
                      : "These facets apply over the typed tile properties (sig.map-tiles/2) — this build carries no tile archives, so they stay named here, never faked."}
                  </p>
                </fieldset>
              )}
            </div>
          )}

          {tab === "selected" && (
            <div className="sig-map-app__tabpanel" role="tabpanel" data-testid="map-selected-panel">
              {selection ? (
                <section className="sig-island__focus" aria-label="Selected record">
                  <h3 data-testid="selection-label">{selection.label}</h3>
                  <dl className="sig-map-app__fields">
                    <div className="pp-field"><dt>Technology</dt><dd data-testid="selection-technology">{selection.technology}</dd></div>
                    <div className="pp-field"><dt>Operator</dt><dd data-testid="selection-operator">{selection.operatorText}</dd></div>
                    <div className="pp-field">
                      <dt>Jurisdiction</dt>
                      <dd data-testid="selection-jurisdiction">
                        {selection.jurisdiction.href ? (
                          <a href={selection.jurisdiction.href}>{selection.jurisdiction.label}</a>
                        ) : (
                          selection.jurisdiction.label || "Not recorded"
                        )}
                      </dd>
                    </div>
                    <div className="pp-field">
                      <dt>Sources</dt>
                      <dd data-testid="selection-sources">
                        {selection.sources.length === 0
                          ? "Not recorded"
                          : selection.sources.map((s, i) => (
                              <span key={s.label}>
                                {i > 0 && ", "}
                                {s.href ? <a href={s.href}>{s.label}</a> : s.label}
                              </span>
                            ))}
                        {selection.licenceText ? ` (${selection.licenceText})` : null}
                      </dd>
                    </div>
                    <div className="pp-field"><dt>First seen</dt><dd data-testid="selection-first-seen">{selection.firstSeen ?? "Not recorded"}</dd></div>
                    <div className="pp-field"><dt>Last seen</dt><dd data-testid="selection-last-seen">{selection.lastSeen ?? "Not recorded"}</dd></div>
                    <div className="pp-field"><dt>Precision</dt><dd data-testid="selection-precision">{selection.precision}</dd></div>
                    <div className="pp-field"><dt>Status</dt><dd data-testid="selection-status">{selection.statusText}</dd></div>
                  </dl>
                  <p className="sig-map-app__actions">
                    {selection.recordHref && (
                      <>
                        <a href={selection.recordHref} data-testid="selection-record-link">
                          Open full record
                        </a>
                        {" · "}
                      </>
                    )}
                    {selection.recordPageHref && (
                      <>
                        <a href={selection.recordPageHref} data-testid="selection-page-link">
                          Released record
                        </a>
                        {" · "}
                      </>
                    )}
                    <a href={props.citationHref} data-testid="selection-cite">Cite this view</a>
                    {selection.disputeHref && (
                      <>
                        {" · "}
                        <a href={selection.disputeHref} data-testid="selection-dispute">
                          Report a problem
                        </a>
                      </>
                    )}
                    {" · "}
                    <button
                      type="button"
                      data-testid="selection-clear"
                      onClick={() => update({ focus: null })}
                    >
                      Clear selection
                    </button>
                  </p>
                  {statements.length > 0 && (
                    <LazyClaimPanels
                      statements={statements}
                      recordPageHref={selection.recordPageHref ?? undefined}
                    />
                  )}
                </section>
              ) : (
                <p className="sig-island__note" data-testid="selection-empty">
                  Select a record on the map or in the In view list — its panel
                  opens here. Escape returns focus.
                </p>
              )}
            </div>
          )}
        </div>

        <div
          className="sig-map-island__canvas sig-map-app__canvas"
          role="application"
          aria-roledescription="interactive map"
          aria-label="Interactive surveillance-infrastructure map (progressive enhancement; the In view list and the tables below carry the same records)"
          data-testid="map-island"
          data-ready={ready ? "true" : "false"}
          data-failed={failed ? "true" : "false"}
          data-drawn={drawn ? "true" : "false"}
          data-point-count={props.pointCount}
          data-greyed={greyed ? "true" : "false"}
          ref={containerRef}
          onKeyDown={onCanvasKeyDown}
        >
          {failed && (
            <p className="sig-island__note" ref={canvasNoteRef} data-testid="map-unavailable">
              The interactive map could not load — the tables below carry the
              same records.
            </p>
          )}
        </div>

        <div className="sig-map-app__controls">
          <div className="sig-map-app__panpad" role="group" aria-label="Pan the map" data-testid="pan-pad">
            <button type="button" aria-label="Pan north" onClick={() => panBy(0, -80)}>↑</button>
            <button type="button" aria-label="Pan west" onClick={() => panBy(-80, 0)}>←</button>
            <button type="button" aria-label="Pan east" onClick={() => panBy(80, 0)}>→</button>
            <button type="button" aria-label="Pan south" onClick={() => panBy(0, 80)}>↓</button>
          </div>
          <div className="sig-map-app__myloc">
            <button
              type="button"
              data-testid="my-location"
              aria-busy={geoPending || undefined}
              disabled={geoPending}
              onClick={locateMe}
            >
              {geoPending ? "Locating…" : "My location"}
            </button>
            <span className="sig-island__note">
              Pans the map only — the position stays in this browser.
            </span>
            {geoNote && (
              <p className="sig-island__note" role="status" data-testid="my-location-note">
                {geoNote}
              </p>
            )}
          </div>
          <label className="sig-map-app__basemap">
            Basemap{" "}
            <select
              value={basemapChoice}
              data-testid="basemap-toggle"
              onChange={(e) => {
                const v = (e.target as HTMLSelectElement).value as "0" | "1";
                setBasemapChoice(v);
                update({ basemap: v });
                void chooseStyle(v).then(({ style, state: bs }) => {
                  const map = mapRef.current;
                  if (!map) return;
                  setBasemapState(bs);
                  map.setStyle(mergeStyle(style), { diff: false });
                });
              }}
            >
              {BASEMAPS.map((b) => (
                <option key={b.key} value={b.key}>{b.label}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {/* P37.18: the debounced live region (K1 §4.6 — 1 s, never mid-gesture). */}
      <p className="sig-visually-hidden" role="status" aria-live="polite" data-testid="map-aria-live">
        {ariaLine}
      </p>

      {/* P37.18 (K1 §5): the print view — the In-view list, the legend, the
          attribution, the as-of line and the cite URL; the canvas never
          prints. */}
      <div className="sig-map-print" aria-hidden="false" data-testid="map-print">
        <h2>Map view — {rowsArePlaces ? "places" : "records"} in view</h2>
        <p className="sig-map-print__meta">
          {statusLine || `${viewCount} records in view`} · Data as of {props.asOf}
          {state.release ? (
            <>
              {" · release "}
              <code>{state.release}</code>
            </>
          ) : null}
          .
        </p>
        <p className="sig-map-print__meta">
          Cite this view: <a href={props.citationHref}>{props.citationHref}</a>
        </p>
        <table className="sig-map-print__table">
          <thead>
            <tr>
              <th scope="col">{rowsArePlaces ? "Place" : "Record"}</th>
              <th scope="col">Technology</th>
              <th scope="col">Operator</th>
              <th scope="col">Status</th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((r) => (
              <tr key={r.id}>
                <th scope="row">{r.label}</th>
                <td>{r.technology ?? "—"}</td>
                <td>{r.operator ?? "—"}</td>
                <td>{r.statusText ?? "—"}</td>
              </tr>
            ))}
            {sortedRows.length === 0 && (
              <tr>
                <td colSpan={4}>No published records in this view.</td>
              </tr>
            )}
          </tbody>
        </table>
        <p className="sig-map-print__meta">{ATTRIBUTION_PRINT(props.attribution)}</p>
      </div>

      <details className="sig-map-app__legend" data-testid="map-legend">
        <summary>Legend</summary>
        <ul>
          <li>
            <span className="sig-map-app__swatch sig-map-app__swatch--solid" aria-hidden="true" />{" "}
            Corroborated — two or more source records (the single data hue; never a colour key)
          </li>
          <li>
            <span className="sig-map-app__swatch sig-map-app__swatch--hollow" aria-hidden="true" />{" "}
            One source — a hollow ring (2+ source records; republications not yet collapsed)
          </li>
          <li>
            <span className="sig-map-app__swatch sig-map-app__swatch--ring" aria-hidden="true" />{" "}
            Contested — a second ring; the text says so too
          </li>
          <li>
            <span className="sig-map-app__swatch sig-map-app__swatch--dashed" aria-hidden="true" />{" "}
            Candidate — a thin open ring; the text says "Candidate"
          </li>
        </ul>
        <p className="sig-island__note">
          Records draw in one data hue (SIG-UI-065): technology is shown by the
          facet, the list and text, never a colour key. Not yet available:
          field of view (modelled), service areas, RTCCs and hubs.
        </p>
        <p className="sig-island__note" data-testid="legend-unplotted">
          Records with no published point:{" "}
          {dict?.totals.unplotted_rows ?? props.unplotted} (SIG-UI-020 — the
          jurisdiction indicators and the places table carry them).
        </p>
        <p className="sig-island__note" data-testid="legend-vintage">
          Data:{" "}
          {state.release ? (
            <>
              release <code>{state.release}</code>
            </>
          ) : (
            "this build"
          )}{" "}
          · as of {props.asOf}.
        </p>
      </details>

      <p className="sig-island__note" data-testid="map-compartment-attribution">
        {activeCompartments.size === props.compartments.length
          ? `All ${props.compartments.length} licence compartment${props.compartments.length === 1 ? "" : "s"}`
          : `${activeCompartments.size} of ${props.compartments.length} licence compartments`}
        {activeAttribution(props.compartments, activeCompartments)
          ? ` — ${activeAttribution(props.compartments, activeCompartments)}`
          : ""}
        .{state.release ? (
          <>
            {" "}
            Release <code>{state.release}</code>.
          </>
        ) : null}
      </p>
    </div>
  );
}

const OPERATOR_FALLBACK = "Operator not stated by any source";
const ATTRIBUTION_PRINT = (line: string) => `Attribution: ${line}`;

function activeAttribution(
  compartments: readonly CompartmentOption[],
  active: Set<string>,
): string {
  const lines = compartments
    .filter((c) => active.has(c.id))
    .map((c) =>
      c.license === "ODbL-1.0"
        ? compartmentAttribution(c.license)
        : (c.attribution?.trim() || compartmentAttribution(c.license)),
    );
  return [...new Set(lines)].join(" · ");
}

/** The seen-range editor (enabled only at the zoom the facet can apply). */
function SeenRangeEditor({
  value,
  onApply,
}: {
  value: { from: string; to: string } | null;
  onApply: (v: { from: string; to: string } | null) => void;
}): JSX.Element {
  const [from, setFrom] = useState(value?.from ?? "");
  const [to, setTo] = useState(value?.to ?? "");
  return (
    <span className="sig-map-app__seen">
      <label>
        From{" "}
        <input
          type="text"
          inputMode="numeric"
          placeholder="YYYY-MM"
          size={7}
          value={from}
          data-testid="filter-seen-from"
          onInput={(e) => setFrom((e.target as HTMLInputElement).value)}
        />
      </label>{" "}
      <label>
        To{" "}
        <input
          type="text"
          inputMode="numeric"
          placeholder="YYYY-MM"
          size={7}
          value={to}
          data-testid="filter-seen-to"
          onInput={(e) => setTo((e.target as HTMLInputElement).value)}
        />
      </label>{" "}
      <button
        type="button"
        data-testid="filter-seen-apply"
        onClick={() => {
          const ok = (v: string) => /^\d{4}-(0[1-9]|1[0-2])$/.test(v);
          if (ok(from) && ok(to)) onApply({ from, to });
        }}
      >
        Apply
      </button>{" "}
      <button type="button" data-testid="filter-seen-clear" onClick={() => onApply(null)}>
        Clear
      </button>
    </span>
  );
}

/** The claim panels load only when a selection carries statements (unchanged
 * lazy boundary from P36.21, now on Preact). */
function LazyClaimPanels({
  statements,
  recordPageHref,
}: {
  statements: StatementRow[];
  recordPageHref?: string;
}): JSX.Element | null {
  const [Panel, setPanel] = useState<
    | null
    | ((p: { statements: StatementRow[]; recordPageHref?: string }) => JSX.Element)
  >(null);
  useEffect(() => {
    let live = true;
    import("./claim-panels").then((m) => {
      if (live) setPanel(() => m.default);
    });
    return () => {
      live = false;
    };
  }, []);
  if (!Panel) return null;
  return <Panel statements={statements} recordPageHref={recordPageHref} />;
}
