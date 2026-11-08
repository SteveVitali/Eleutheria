// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.19 (K1 MAP-04 §4.2) — the local coordinates parser the map's place
 * search runs BEFORE any shard lookup: "41.4959, -94.5205" (or the same
 * pair with hemisphere letters — "41.4959N, 94.5205W", "N41.5 W94.5")
 * parses in the browser and jumps the map. No request is ever made; an
 * unparseable string is an honest null, never a guess.
 *
 * Deliberately narrow: two signed-or-hemisphere-marked decimal numbers,
 * comma-separated, or hemisphere-letter pairs. Bare words ("Austin") and
 * ambiguous pairs (two hemisphere letters of the same axis, a sign and a
 * contradictory letter) return null — the typeahead still answers them.
 */

export interface ParsedCoordinates {
  lat: number;
  lon: number;
}

const NUM = /[+-]?\d+(?:\.\d+)?/;

/** One coordinate token: an optional hemisphere letter on either side of a decimal number. */
const TOKEN = new RegExp(
  `^\\s*([NSEW]?)\\s*(${NUM.source})\\s*([NSEW]?)\\s*$`,
  "i",
);

interface Token {
  value: number;
  hemi: "N" | "S" | "E" | "W" | null;
}

function parseToken(raw: string): Token | null {
  const m = TOKEN.exec(raw);
  if (!m) return null;
  const pre = (m[1] ?? "").toUpperCase();
  const post = (m[3] ?? "").toUpperCase();
  // A letter on both sides ("N41.5N") is malformed, never a guess.
  if (pre !== "" && post !== "") return null;
  const hemi = (pre || post || null) as Token["hemi"];
  const value = Number(m[2]);
  if (!Number.isFinite(value)) return null;
  return { value, hemi };
}

/** Apply the hemisphere letter to the axis value; a contradictory sign is a refusal. */
function applyHemisphere(t: Token, positive: "N" | "E", negative: "S" | "W"): number | null {
  if (t.hemi === null) return t.value;
  if (t.hemi !== positive && t.hemi !== negative) return null;
  const sign = t.hemi === positive ? 1 : -1;
  // "−41.5S" names south twice — consistent; "+41.5S" contradicts itself.
  if (t.value < 0 && sign > 0) return null;
  return Math.abs(t.value) * sign;
}

/**
 * Parse a typed coordinate pair — returns `{lat, lon}` or null. Accepted
 * shapes:
 *   "41.4959, -94.5205"          — comma-separated signed decimals
 *   "41.4959N, 94.5205W"         — hemisphere suffixes
 *   "N41.4959, W94.5205"         — hemisphere prefixes
 *   "41.4959N 94.5205W"          — hemisphere letters, space-separated
 * Order is always latitude then longitude; a pair that only makes sense
 * swapped ("94.5, 41.5" where the first exceeds 90°) is rejected, never
 * silently reordered — the typing reader sees the honest no-match.
 */
export function parseCoordinates(raw: string): ParsedCoordinates | null {
  const text = raw.trim();
  if (text === "" || text.length > 80) return null;

  const tryPair = (a: Token | null, b: Token | null): ParsedCoordinates | null => {
    if (a === null || b === null) return null;
    // Axis assignment: a letter fixes the axis (N/S = lat, E/W = lon);
    // without letters the first number is the latitude.
    const latTok = a.hemi === "E" || a.hemi === "W" ? b : a;
    const lonTok = a.hemi === "E" || a.hemi === "W" ? a : b;
    if (latTok.hemi === "E" || latTok.hemi === "W") return null;
    if (lonTok.hemi === "N" || lonTok.hemi === "S") return null;
    const lat = applyHemisphere(latTok, "N", "S");
    const lon = applyHemisphere(lonTok, "E", "W");
    if (lat === null || lon === null) return null;
    if (lat < -90 || lat > 90 || lon < -180 || lon > 180) return null;
    return { lat, lon };
  };

  // Shape 1: comma-separated pair ("41.4959, -94.5205", "N41.5, W94.5").
  if (text.includes(",")) {
    const parts = text.split(",");
    if (parts.length !== 2) return null;
    return tryPair(parseToken(parts[0] ?? ""), parseToken(parts[1] ?? ""));
  }

  // Shape 2: hemisphere-marked pair, whitespace-separated ("41.5N 94.5W",
  // "N41.5 W94.5") — letters are required so a bare "41.5 94.5" never reads
  // as coordinates by accident.
  const words = text.split(/\s+/).filter((w) => w !== "");
  if (words.length === 2) {
    const a = parseToken(words[0]!);
    const b = parseToken(words[1]!);
    if (a?.hemi && b?.hemi) return tryPair(a, b);
  }
  return null;
}
