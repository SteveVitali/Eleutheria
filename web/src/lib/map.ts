// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * The infrastructure map's honest-rendering rules as pure data + logic (§39.3, §19.5).
 *
 * P15.3 owns the two spatial/graph surfaces and the rules that keep them honest.
 * This module carries the *map* half — no rendering, no colour, no DOM — so every
 * rule below is unit-testable in isolation from the Astro page and re-usable by the
 * static SVG render, the tabular equivalent, and (were it ever wired) an interactive
 * renderer. The rules encoded here:
 *
 *   - the §39.3 layer catalog, with derived layers (FOV, coverage) flagged so they
 *     are separately toggled and visually distinct (SIG-UI-016, SIG-GEO-006);
 *   - the coverage underlay BOUND to the point layer by a single control, so a user
 *     can never see points without seeing where SIG has not looked (SIG-UI-017);
 *   - the encoding that stops low coverage reading as low density (SIG-UI-018);
 *   - national-zoom density binning + the per-tier zoom at which an individual point
 *     is honestly renderable (SIG-UI-019, SIG-GEO-011, §19.4);
 *   - no-coordinate assets surfaced as jurisdiction indicators, never dropped
 *     (SIG-UI-020);
 *   - the sharing-edge default view (ego, never a national hairball) (SIG-UI-021).
 *
 * The static-PMTiles serving contract (SIG-UI-038, SIG-GEO-012/013) lives in its
 * sibling `map-tiles.ts`.
 */

import type { AbsenceKind } from "./epistemic";

// --- Sensitivity tiers (§19.4, SIG-GEO-008) --------------------------------

/**
 * The public coordinate-precision tier applied at the view layer (§19.4). Full
 * precision retained in canonical storage under RLS; the tier governs what may be
 * published — and therefore whether, and at what zoom, an individual point is an
 * honest thing to draw (SIG-UI-019).
 */
export type SensitivityTier = 0 | 1 | 2 | 3;

export const SENSITIVITY_TIERS: readonly SensitivityTier[] = [0, 1, 2, 3] as const;

// --- The §39.3 layer catalog (SIG-UI-016) ----------------------------------

/**
 * Observed geometry is a *record*; derived geometry (FOV cones, coverage estimates)
 * is a *model*. SIG-GEO-006 requires the two be visually and structurally
 * distinguishable in every surface, and SIG-UI-016 requires the derived layers be
 * separately toggled — so `kind` is a first-class property of every layer, never an
 * afterthought of styling.
 */
export type LayerKind = "observed" | "derived";

export interface MapLayer {
  id: string;
  label: string;
  kind: LayerKind;
  /** One-line plain-language description (the local advocate is the design center). */
  description: string;
}

/** The seven observed layers of §39.3, in display order. */
export const OBSERVED_LAYERS: readonly MapLayer[] = [
  {
    id: "physical_devices",
    label: "Physical devices",
    kind: "observed",
    description: "Cameras, ALPRs, and other hardware SIG has a location claim for.",
  },
  {
    id: "deployments",
    label: "Deployments",
    kind: "observed",
    description: "Where a capability is operated, whether or not a device point is published.",
  },
  {
    id: "rtccs_integration_hubs",
    label: "RTCCs & integration hubs",
    kind: "observed",
    description: "Real-time crime centres and the hubs that fuse feeds.",
  },
  {
    id: "sharing_edges",
    label: "Sharing edges",
    kind: "observed",
    description: "Declared data-sharing relationships, drawn as an ego network (SIG-UI-021).",
  },
  {
    id: "private_public_networks",
    label: "Private–public networks",
    kind: "observed",
    description: "Registries enrolling private cameras into public access.",
  },
  {
    id: "service_areas",
    label: "Service areas",
    kind: "observed",
    description: "Operating-area polygons for mobile or point-less assets (SIG-GEO-004).",
  },
  {
    id: "lifecycle_status",
    label: "Lifecycle status",
    kind: "observed",
    description: "Candidate / active / decommissioned state of each asset.",
  },
] as const;

/**
 * The derived layers (§39.3): field-of-view cones and coverage estimates. Each is a
 * model, not an observation — it MUST be separately toggled and drawn distinctly
 * from observed geometry (SIG-UI-016, SIG-GEO-006/007). `coverage` is additionally
 * bound to the point layer by a single control (SIG-UI-017); see `LAYER_CONTROLS`.
 */
export const DERIVED_LAYERS: readonly MapLayer[] = [
  {
    id: "field_of_view",
    label: "Field of view (modelled)",
    kind: "derived",
    description: "Modelled sight-lines from asset direction + assumed optics. Assumptions published.",
  },
  {
    id: "coverage",
    label: "Coverage (modelled)",
    kind: "derived",
    description: "Where SIG has and has not looked. Bound to the device layer (SIG-UI-017).",
  },
] as const;

/** Every layer, observed then derived. */
export const MAP_LAYERS: readonly MapLayer[] = [...OBSERVED_LAYERS, ...DERIVED_LAYERS];

export const POINT_LAYER_ID = "physical_devices";
export const COVERAGE_LAYER_ID = "coverage";

// --- Layer controls + the bound coverage control (SIG-UI-016/017) ----------

/**
 * A user-facing toggle. Most layers get their own independent control; the point
 * layer and the coverage underlay share ONE control so they can never be toggled
 * apart (SIG-UI-017). Two independent toggles would let the map lie by default —
 * points with the coverage turned off read as "this is everything there is".
 */
export interface LayerControl {
  id: string;
  label: string;
  /** The layer ids this single control shows/hides together. */
  governs: readonly string[];
}

/** The single control that binds the point layer to its coverage underlay (SIG-UI-017). */
export const POINT_COVERAGE_CONTROL: LayerControl = {
  id: "devices_and_coverage",
  label: "Devices + where SIG has looked",
  governs: [POINT_LAYER_ID, COVERAGE_LAYER_ID],
};

/**
 * The map's control set: the bound devices+coverage control, plus one independent
 * control per remaining layer. Derived layers other than coverage (i.e. FOV) get
 * their own toggle so they are separately switchable and distinct (SIG-UI-016).
 */
export const LAYER_CONTROLS: readonly LayerControl[] = [
  POINT_COVERAGE_CONTROL,
  ...MAP_LAYERS.filter((l) => l.id !== POINT_LAYER_ID && l.id !== COVERAGE_LAYER_ID).map((l) => ({
    id: `toggle_${l.id}`,
    label: l.label,
    governs: [l.id] as const,
  })),
];

/**
 * Whether the coverage underlay is bound to the point layer such that points can
 * never be shown without coverage (SIG-UI-017). True iff exactly one control
 * governs the point layer and that same control also governs coverage, and no
 * OTHER control governs the point layer independently.
 */
export function coverageBoundToPoints(controls: readonly LayerControl[] = LAYER_CONTROLS): boolean {
  const governingPoints = controls.filter((c) => c.governs.includes(POINT_LAYER_ID));
  if (governingPoints.length !== 1) return false;
  const control = governingPoints[0]!;
  return control.governs.includes(COVERAGE_LAYER_ID);
}

/** Throw unless the coverage↔point binding holds (SIG-UI-017); used as a build-time guard. */
export function assertCoverageBinding(controls: readonly LayerControl[] = LAYER_CONTROLS): void {
  if (!coverageBoundToPoints(controls)) {
    throw new Error(
      "SIG-UI-017: the coverage underlay MUST be bound to the point layer by a single control — " +
        "points cannot be shown without coverage.",
    );
  }
}

// --- Low coverage MUST NOT read as low density (SIG-UI-018) ----------------

/**
 * How much of a bin cell SIG has actually looked at. Distinct from how many devices
 * are *in* it — that distinction is the whole point of SIG-UI-018.
 */
export type CoverageLevel = "none" | "low" | "partial" | "high";

export const COVERAGE_LEVELS: readonly CoverageLevel[] = ["none", "low", "partial", "high"] as const;

/**
 * The non-colour encoding for a coverage level. Low/absent coverage is DESATURATED
 * and value-suppressed and carries the absence hatch, so "we don't know" is visually
 * distinct from "there is little here" (SIG-UI-018) — and the distinction survives
 * greyscale/colour-blindness (SIG-UI-005). Colour, where the CSS adds any, is a
 * redundant channel only.
 */
export interface CoverageEncoding {
  level: CoverageLevel;
  /** Desaturate the cell — coverage uncertainty drains colour, it does not add it. */
  desaturated: boolean;
  /** Suppress the density value's visual weight where SIG has not looked. */
  valueSuppressed: boolean;
  /** Carry the single absence texture where coverage is absent/low (§9.5, SIG-UI-007). */
  hatched: boolean;
  /** Plain-language label announced to a screen reader. */
  label: string;
}

const COVERAGE_ENCODINGS: Record<CoverageLevel, CoverageEncoding> = {
  none: {
    level: "none",
    desaturated: true,
    valueSuppressed: true,
    hatched: true,
    label: "No coverage — SIG has not looked here; this is not evidence of little activity.",
  },
  low: {
    level: "low",
    desaturated: true,
    valueSuppressed: true,
    hatched: true,
    label: "Low coverage — SIG has barely looked here; density below is unreliable.",
  },
  partial: {
    level: "partial",
    desaturated: true,
    valueSuppressed: false,
    hatched: false,
    label: "Partial coverage — some of this area has been searched.",
  },
  high: {
    level: "high",
    desaturated: false,
    valueSuppressed: false,
    hatched: false,
    label: "High coverage — SIG has searched this area thoroughly.",
  },
};

/** The non-colour encoding for a coverage level (SIG-UI-018). */
export function coverageEncoding(level: CoverageLevel): CoverageEncoding {
  return COVERAGE_ENCODINGS[level];
}

/** A national-zoom density bin: how many devices, and how well the cell is covered. */
export interface DensityBin {
  /** The H3 cell id (§19.5, SIG-GEO-011); opaque here. */
  h3: string;
  jurisdiction: string;
  deviceCount: number;
  coverage: CoverageLevel;
}

/** The number of density buckets an honestly-covered cell is quantised into. */
export const DENSITY_BUCKETS = 4;

/**
 * The render descriptor for a density bin. `densityBucket` is only meaningful where
 * coverage is adequate; where it is not, the coverage encoding suppresses the value
 * so a low, unreliable count never renders like a confidently-low count (SIG-UI-018).
 */
export interface BinRender {
  h3: string;
  deviceCount: number;
  densityBucket: number;
  coverage: CoverageEncoding;
}

/**
 * Whether this cell's *count* should be read as a confident density signal. False
 * whenever coverage is absent/low — the count is then "we don't know", not "little
 * here". This is the predicate SIG-UI-018 turns on: the two must never be conflated.
 */
export function readsAsDensity(bin: DensityBin): boolean {
  return !coverageEncoding(bin.coverage).valueSuppressed;
}

export function renderBin(bin: DensityBin, maxCount: number): BinRender {
  const cov = coverageEncoding(bin.coverage);
  // Quantise the count into buckets 0..DENSITY_BUCKETS-1 only where it is a real
  // signal; a suppressed (low-coverage) cell reads as bucket 0 regardless of count.
  const bucket =
    cov.valueSuppressed || maxCount <= 0
      ? 0
      : Math.min(DENSITY_BUCKETS - 1, Math.floor((bin.deviceCount / maxCount) * DENSITY_BUCKETS));
  return { h3: bin.h3, deviceCount: bin.deviceCount, densityBucket: bucket, coverage: cov };
}

// --- National-zoom binning + per-tier point honesty (SIG-UI-019) -----------

/**
 * At or below this zoom the map renders density bins, not individual points — the
 * national view (SIG-UI-019). Above it, points may appear where the tier allows.
 */
export const NATIONAL_ZOOM_MAX = 6;

export type RenderMode = "bins" | "points";

/** Density bins at national zoom, individual points once zoomed in (SIG-UI-019). */
export function renderModeForZoom(zoom: number): RenderMode {
  return zoom <= NATIONAL_ZOOM_MAX ? "bins" : "points";
}

/**
 * The minimum zoom at which an individual point is an HONEST thing to draw for each
 * sensitivity tier (§19.4). A tier-0 asset (public right-of-way hardware) can be
 * shown once past the national view; a tier-2 asset (H3-binned) needs a close zoom
 * so the drawn point never implies more precision than SIG published; a tier-3
 * asset (jurisdiction-only) is NEVER drawn as a point — `null` (SIG-UI-019/020).
 */
export const MIN_POINT_ZOOM_BY_TIER: Record<SensitivityTier, number | null> = {
  0: NATIONAL_ZOOM_MAX + 1,
  1: NATIONAL_ZOOM_MAX + 3,
  2: NATIONAL_ZOOM_MAX + 6,
  3: null,
};

/**
 * Whether an individual point for an asset of this tier may be drawn at this zoom —
 * i.e. the zoom supports honest rendering of the asset's published precision
 * (SIG-UI-019). Tier 3 is never a point (it has no published geometry).
 */
export function pointVisibleAtZoom(tier: SensitivityTier, zoom: number): boolean {
  const min = MIN_POINT_ZOOM_BY_TIER[tier];
  return min !== null && zoom >= min;
}

// --- No-coordinate assets as jurisdiction indicators (SIG-UI-020) ----------

export interface MapAsset {
  id: string;
  label: string;
  jurisdiction: string;
  tier: SensitivityTier;
  /** null when SIG publishes no point for this asset (tier 3, mobile, or unknown). */
  lat: number | null;
  lon: number | null;
  /** The published-precision description shown in the tabular equivalent. */
  precision: string;
  /** Set when the location itself is a gap (§9.5) — rendered as the hatch. */
  locationAbsence?: AbsenceKind;
}

/** A jurisdiction-level roll-up of the assets that cannot be drawn as points. */
export interface JurisdictionIndicator {
  jurisdiction: string;
  count: number;
  assetIds: string[];
}

/**
 * Whether an asset has a publishable point. False when it has no coordinates OR its
 * tier forbids publishing geometry (tier 3, §19.4) — either way it becomes a
 * jurisdiction indicator, never a dropped row (SIG-UI-020).
 */
export function isLocatable(asset: MapAsset): boolean {
  return asset.lat !== null && asset.lon !== null && asset.tier !== 3;
}

/**
 * Split assets into those drawn as points and those rolled up to jurisdiction
 * indicators. Nothing is dropped: `locatable.length + Σ indicator.count === total`
 * (SIG-UI-020) — a map that shows only locatable assets systematically understates
 * capability, which is the outline's core critique of camera maps.
 */
export function partitionByLocatability(assets: readonly MapAsset[]): {
  locatable: MapAsset[];
  jurisdictionIndicators: JurisdictionIndicator[];
} {
  const locatable: MapAsset[] = [];
  const byJurisdiction = new Map<string, JurisdictionIndicator>();
  for (const asset of assets) {
    if (isLocatable(asset)) {
      locatable.push(asset);
      continue;
    }
    const existing = byJurisdiction.get(asset.jurisdiction);
    if (existing) {
      existing.count += 1;
      existing.assetIds.push(asset.id);
    } else {
      byJurisdiction.set(asset.jurisdiction, {
        jurisdiction: asset.jurisdiction,
        count: 1,
        assetIds: [asset.id],
      });
    }
  }
  const jurisdictionIndicators = [...byJurisdiction.values()].sort((a, b) =>
    a.jurisdiction.localeCompare(b.jurisdiction),
  );
  return { locatable, jurisdictionIndicators };
}

// --- Sharing edges: ego by default, never a hairball (SIG-UI-021) ----------

/** The sharing-edge view modes; the default is the ego network, never a global one. */
export const SHARING_EDGE_VIEWS = ["ego", "matrix", "arc"] as const;
export type SharingEdgeView = (typeof SHARING_EDGE_VIEWS)[number];

/** Default to an ego network from a selected entity — never a national hairball. */
export const DEFAULT_SHARING_EDGE_VIEW: SharingEdgeView = "ego";
