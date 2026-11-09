// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

/**
 * P37.19 (K1 MAP-04, OD-09 [B-23] = a "Natural Earth") — the populated-places
 * layer and the jurisdiction frames the map's place search resolves through.
 *
 * **OD-09 was answered `a` (Natural Earth), not K1's draft GeoNames:** the
 * non-US cities subset is the Natural Earth populated-places shape — public
 * domain, no attribution condition (SIG still credits "Made with Natural
 * Earth"). The real upstream capture stays HG-03-gated with the rest of the
 * boundary pack (`natural_earth_10m`, `docs/build/reports/rights/
 * natural_earth_10m.md`), so — the same `gate.mode = "fixture-bypass"`
 * posture the pack records — this committed fixture stands in: real,
 * public-domain place names and coordinates drawn at populated-place
 * resolution, bounded to a reviewable set.
 *
 * Every city here is a non-US populated place — the K4 registry already
 * covers the US gazetteer; this layer exists so "Canberra" never answers
 * zero (K1 §4.2 / C2 NEW-10). A city is NOT a SIG jurisdiction: it carries
 * coordinates, never a jkey, so a map selection frames it (`at=`) and the
 * place-filter offer honestly does not apply to it.
 */

/** One populated place in the cities layer. */
export interface PlaceCity {
  /** Display name (English exonym as NE records it). */
  name: string;
  /** Admin-1 name where NE records one (homonym disambiguation). */
  admin?: string;
  country: string;
  country_a2: string;
  lat: number;
  lon: number;
  /** NE SCALERANK bucket — a coarse size hint, never an exact population. */
  scalerank?: number;
}

/** The `sig.place-cities/1` document shape (web-side; the export emits this
 * path once the gated capture lands — `web/cities.json`). */
export interface PlaceCitiesDoc {
  schema: "sig.place-cities/1";
  source: string;
  license: string;
  attribution: string;
  cities: PlaceCity[];
}

/**
 * The committed Natural Earth populated-places fixture — real names and
 * coordinates (public-domain facts), spread across every non-US continent
 * so the homonym and framing paths both exercise. Canberra leads the set:
 * it is the acceptance case "Canberra → 0" fixes.
 */
export const MAP_CITIES_FIXTURE: PlaceCitiesDoc = {
  schema: "sig.place-cities/1",
  source: "natural_earth_10m — populated places (fixture-bypass posture; upstream capture HG-03 gated)",
  license: "CC0-1.0",
  attribution: "Made with Natural Earth.",
  cities: [
    { name: "Canberra", admin: "Australian Capital Territory", country: "Australia", country_a2: "AU", lat: -35.2835, lon: 149.1281, scalerank: 2 },
    { name: "Sydney", admin: "New South Wales", country: "Australia", country_a2: "AU", lat: -33.8688, lon: 151.2093, scalerank: 0 },
    { name: "Melbourne", admin: "Victoria", country: "Australia", country_a2: "AU", lat: -37.8136, lon: 144.9631, scalerank: 0 },
    { name: "London", admin: "England", country: "United Kingdom", country_a2: "GB", lat: 51.5072, lon: -0.1276, scalerank: 0 },
    { name: "Manchester", admin: "England", country: "United Kingdom", country_a2: "GB", lat: 53.4808, lon: -2.2426, scalerank: 3 },
    { name: "Paris", admin: "Île-de-France", country: "France", country_a2: "FR", lat: 48.8566, lon: 2.3522, scalerank: 0 },
    { name: "Lyon", admin: "Auvergne-Rhône-Alpes", country: "France", country_a2: "FR", lat: 45.7640, lon: 4.8357, scalerank: 3 },
    { name: "Berlin", admin: "Berlin", country: "Germany", country_a2: "DE", lat: 52.5200, lon: 13.4050, scalerank: 0 },
    { name: "Munich", admin: "Bavaria", country: "Germany", country_a2: "DE", lat: 48.1351, lon: 11.5820, scalerank: 2 },
    { name: "Toronto", admin: "Ontario", country: "Canada", country_a2: "CA", lat: 43.6532, lon: -79.3832, scalerank: 0 },
    { name: "Vancouver", admin: "British Columbia", country: "Canada", country_a2: "CA", lat: 49.2827, lon: -123.1207, scalerank: 2 },
    { name: "Ottawa", admin: "Ontario", country: "Canada", country_a2: "CA", lat: 45.4215, lon: -75.6972, scalerank: 2 },
    { name: "Mexico City", admin: "Ciudad de México", country: "Mexico", country_a2: "MX", lat: 19.4326, lon: -99.1332, scalerank: 0 },
    { name: "Guadalajara", admin: "Jalisco", country: "Mexico", country_a2: "MX", lat: 20.6597, lon: -103.3496, scalerank: 2 },
    { name: "Tokyo", admin: "Tokyo", country: "Japan", country_a2: "JP", lat: 35.6762, lon: 139.6503, scalerank: 0 },
    { name: "Osaka", admin: "Osaka", country: "Japan", country_a2: "JP", lat: 34.6937, lon: 135.5023, scalerank: 2 },
    { name: "São Paulo", admin: "São Paulo", country: "Brazil", country_a2: "BR", lat: -23.5505, lon: -46.6333, scalerank: 0 },
    { name: "Brasília", admin: "Distrito Federal", country: "Brazil", country_a2: "BR", lat: -15.7942, lon: -47.8822, scalerank: 2 },
    { name: "Buenos Aires", admin: "Ciudad Autónoma de Buenos Aires", country: "Argentina", country_a2: "AR", lat: -34.6037, lon: -58.3816, scalerank: 0 },
    { name: "Cape Town", admin: "Western Cape", country: "South Africa", country_a2: "ZA", lat: -33.9249, lon: 18.4241, scalerank: 2 },
    { name: "Johannesburg", admin: "Gauteng", country: "South Africa", country_a2: "ZA", lat: -26.2041, lon: 28.0473, scalerank: 1 },
    { name: "Nairobi", country: "Kenya", country_a2: "KE", lat: -1.2921, lon: 36.8219, scalerank: 1 },
    { name: "Cairo", admin: "Cairo", country: "Egypt", country_a2: "EG", lat: 30.0444, lon: 31.2357, scalerank: 0 },
    { name: "Lagos", admin: "Lagos", country: "Nigeria", country_a2: "NG", lat: 6.5244, lon: 3.3792, scalerank: 0 },
    { name: "Mumbai", admin: "Maharashtra", country: "India", country_a2: "IN", lat: 19.0760, lon: 72.8777, scalerank: 0 },
    { name: "New Delhi", admin: "Delhi", country: "India", country_a2: "IN", lat: 28.6139, lon: 77.2090, scalerank: 1 },
    { name: "Jakarta", country: "Indonesia", country_a2: "ID", lat: -6.2088, lon: 106.8456, scalerank: 0 },
    { name: "Auckland", country: "New Zealand", country_a2: "NZ", lat: -36.8509, lon: 174.7645, scalerank: 2 },
    { name: "Wellington", country: "New Zealand", country_a2: "NZ", lat: -41.2865, lon: 174.7762, scalerank: 3 },
    { name: "Madrid", country: "Spain", country_a2: "ES", lat: 40.4168, lon: -3.7038, scalerank: 0 },
    { name: "Barcelona", admin: "Catalonia", country: "Spain", country_a2: "ES", lat: 41.3874, lon: 2.1686, scalerank: 1 },
    { name: "Rome", admin: "Lazio", country: "Italy", country_a2: "IT", lat: 41.9028, lon: 12.4964, scalerank: 0 },
    { name: "Amsterdam", admin: "North Holland", country: "Netherlands", country_a2: "NL", lat: 52.3676, lon: 4.9041, scalerank: 2 },
    { name: "Brussels", country: "Belgium", country_a2: "BE", lat: 50.8503, lon: 4.3517, scalerank: 1 },
    { name: "Stockholm", country: "Sweden", country_a2: "SE", lat: 59.3293, lon: 18.0686, scalerank: 1 },
    { name: "Oslo", country: "Norway", country_a2: "NO", lat: 59.9139, lon: 10.7522, scalerank: 2 },
    { name: "Seoul", country: "South Korea", country_a2: "KR", lat: 37.5665, lon: 126.9780, scalerank: 0 },
    { name: "Taipei", country: "Taiwan", country_a2: "TW", lat: 25.0330, lon: 121.5654, scalerank: 1 },
    { name: "Istanbul", country: "Turkey", country_a2: "TR", lat: 41.0082, lon: 28.9784, scalerank: 0 },
    { name: "Dublin", admin: "Leinster", country: "Ireland", country_a2: "IE", lat: 53.3498, lon: -6.2603, scalerank: 2 },
  ],
};

/**
 * One place the map can frame — `bbox` ([w,s,e,n] degrees) when the
 * registry records one, else `center` (the internal point). `chain` is the
 * root-first jkey ancestry (self last) the descendants-inclusive
 * `jurisdiction=` facet matches through.
 */
export interface PlaceFrame {
  name?: string;
  bbox?: [number, number, number, number];
  center?: { lat: number; lon: number };
  chain?: string[];
}

/**
 * The fixtures-mode jurisdiction frames — the same `sig.map-dict/1`
 * `jurisdictions` fields an export's `web/map/dict.json` serves. Rough,
 * honest bounding boxes for the committed fixture registry (public facts at
 * coarse resolution; a frame is a starting view, never a claimed extent).
 */
export const MAP_PLACE_FRAMES_FIXTURE: Record<string, PlaceFrame> = {
  "iso3166-1:US": {
    name: "United States",
    bbox: [-125.0, 24.4, -66.9, 49.4],
    chain: ["iso3166-1:US"],
  },
  "iso3166-2:US-OK": {
    name: "Oklahoma",
    bbox: [-103.0, 33.6, -94.4, 37.0],
    chain: ["iso3166-1:US", "iso3166-2:US-OK"],
  },
  "us.census.geoid.county:40109": {
    name: "Oklahoma County",
    bbox: [-97.75, 35.35, -97.15, 35.75],
    chain: ["iso3166-1:US", "iso3166-2:US-OK", "us.census.geoid.county:40109"],
  },
  "us.census.geoid.place:4064000": {
    name: "Oklahoma City",
    bbox: [-97.65, 35.29, -97.30, 35.68],
    chain: ["iso3166-1:US", "iso3166-2:US-OK", "us.census.geoid.county:40109", "us.census.geoid.place:4064000"],
  },
  "us.census.geoid.county:40131": {
    name: "Cleveland County",
    bbox: [-97.55, 34.95, -97.0, 35.4],
    chain: ["iso3166-1:US", "iso3166-2:US-OK", "us.census.geoid.county:40131"],
  },
  "us.census.geoid.place:4055000": {
    name: "Norman",
    bbox: [-97.55, 35.12, -97.30, 35.35],
    chain: ["iso3166-1:US", "iso3166-2:US-OK", "us.census.geoid.county:40131", "us.census.geoid.place:4055000"],
  },
  "iso3166-2:US-TX": {
    name: "Texas",
    bbox: [-106.7, 25.8, -93.5, 36.5],
    chain: ["iso3166-1:US", "iso3166-2:US-TX"],
  },
  "us.census.geoid.county:48201": {
    name: "Harris County",
    bbox: [-95.95, 29.5, -94.9, 30.2],
    chain: ["iso3166-1:US", "iso3166-2:US-TX", "us.census.geoid.county:48201"],
  },
  "iso3166-2:US-VI": {
    name: "U.S. Virgin Islands",
    bbox: [-65.2, 17.6, -64.5, 18.5],
    chain: ["iso3166-1:US", "iso3166-2:US-VI"],
  },
  "iso3166-1:CA": {
    name: "Canada",
    bbox: [-141.0, 41.7, -52.6, 83.1],
    chain: ["iso3166-1:CA"],
  },
  "iso3166-2:CA-ON": {
    name: "Ontario",
    bbox: [-95.2, 41.9, -74.3, 56.9],
    chain: ["iso3166-1:CA", "iso3166-2:CA-ON"],
  },
  "iso3166-1:FR": {
    name: "France",
    bbox: [-5.2, 41.3, 9.7, 51.1],
    chain: ["iso3166-1:FR"],
  },
  "iso3166-1:DE": {
    name: "Germany",
    bbox: [5.8, 47.2, 15.1, 55.1],
    chain: ["iso3166-1:DE"],
  },
};
