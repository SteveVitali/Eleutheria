# ADR-018: MapLibre GL for the web map

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-GEO-012, SIG-UI-002
- **Spec:** docs/2_canonical_design_spec.md §19.5, §39

## Context

The public map must render static PMTiles without a mandatory dynamic tile server, and must not depend on a proprietary map SDK.

## Decision

Use MapLibre GL (open source) as the web map renderer, consuming static PMTiles v3.

## Consequences

Open, self-hostable, consumes static tiles; no proprietary SDK lock-in or usage-based billing. Requires PMTiles generation (tippecanoe).

## Alternatives considered

Mapbox GL JS (proprietary licence, usage billing); Leaflet (weaker vector-tile/GL story).

## Revisit trigger

MapLibre cannot render a required cartographic feature, or a superior open renderer is broadly adopted.
