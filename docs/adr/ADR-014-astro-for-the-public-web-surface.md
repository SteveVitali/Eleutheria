# ADR-014: Astro for the public web surface

- **Status:** Accepted
- **Date:** 2026-08-26
- **Phase:** P00.2
- **Requirement ids:** SIG-ENG-010, SIG-UI-002
- **Spec:** docs/2_canonical_design_spec.md §47, §39

## Context

The design centre is a local advocate who needs a fast, printable, static-first site; TypeScript is confined to `web/`.

## Decision

Build the public site with Astro, producing static HTML by default with islands only where interactivity is needed.

## Consequences

Static-first output is cheap to host, mirrorable, and survives the app being offline (§46.5); good print path. Ties the web layer to Astro's conventions.

## Alternatives considered

Next.js (heavier, SSR-first); a SPA framework (poor no-JS and print story, fails SIG-UI accessibility goals).

## Revisit trigger

Astro cannot meet the accessibility/no-JS or print requirements, or its maintenance/licence posture changes.
