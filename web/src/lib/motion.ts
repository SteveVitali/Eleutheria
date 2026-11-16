// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.60 (SIG-UI-149, K14 §4.9 + NEW-10, DR-K14-15) — the reduced-motion
 * camera guard.
 *
 * With `prefers-reduced-motion: reduce` there MUST be no animated
 * transitions, map easing or animated layouts. The CSS side is the token pair
 * (`--sig-motion-*` zero under the media query); the MAP side is this module:
 * `easeOrJumpTo` / `fitBoundsOrJump` are the only sanctioned routes to the
 * animated camera methods — they substitute `jumpTo` (and `cameraForBounds` +
 * `jumpTo` for `fitBounds`) the moment the user asks for reduced motion.
 * `tests/unit/motion-guard.test.ts` bans bare `.easeTo(`, `.flyTo(` and
 * `.fitBounds(` call sites anywhere else under `src/`, so a future camera move
 * cannot bypass the guard silently.
 */

import type {
  CameraOptions,
  FitBoundsOptions,
  LngLatBoundsLike,
  Map as MapLibreMap,
} from "maplibre-gl";

/** The live `prefers-reduced-motion` read — evaluated per call, never cached. */
export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * `easeTo` when motion is allowed, `jumpTo` under `reduce`. Both take the same
 * camera options; the animation fields are simply inert on the jump.
 */
export function easeOrJumpTo(
  map: MapLibreMap,
  options: CameraOptions & { duration?: number; essential?: boolean },
): void {
  if (prefersReducedMotion()) map.jumpTo(options);
  else map.easeTo(options);
}

/**
 * `fitBounds` when motion is allowed; under `reduce` the same frame is
 * computed with `cameraForBounds` and applied with `jumpTo` — no easing, same
 * destination (NEW-10's fix shape: K14 §4.9 names `jumpTo` the substitute).
 */
export function fitBoundsOrJump(
  map: MapLibreMap,
  bounds: LngLatBoundsLike,
  options?: FitBoundsOptions,
): void {
  if (!prefersReducedMotion()) {
    map.fitBounds(bounds, options);
    return;
  }
  const camera = map.cameraForBounds(bounds, options);
  if (camera) map.jumpTo(camera);
}
