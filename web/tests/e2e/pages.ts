// SPDX-License-Identifier: Apache-2.0
// Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
// carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

// The shell's pages. Kept in one place so
// the a11y sweep and the no-JS checks cover the same surface.

// The standard shell-layout pages: each carries the primary nav and the citation
// affordance (SIG-UI-035). The dossier page is one of these; its PRINT export is a
// standalone paginated document (no nav/citation by design) and is covered by the
// a11y sweep below, not here.
export const SHELL_PAGES = [
  "/",
  "/dossier/",
  "/dossier/oklahoma-city/",
  "/visual-language/",
  "/map/",
  "/network/",
  "/search/",
  "/watch/",
  "/evidence/",
  "/evidence/active-device-count/",
  "/evidence/operator-roster-size/",
  "/research-queue/",
  "/corrections/",
  "/contribution-back/",
  "/dispute/",
  "/methodology/",
  "/data-freshness/",
  "/coverage-metrics/",
  "/editorial-standards/",
  "/style-guide/",
  // P35.38a: the crawler contact/explanation page the User-Agent names
  // (SIG-INGEST-036 rule 1). T0 — ships zero <script> like every other
  // non-island public page.
  "/data-collection/",
] as const;

// The seven outline surfaces + the required eighth (the corrections log), asserted to
// exist across the built Phase-15 site (P15.5 deliverable 6 / AC1). Each maps to a
// representative page (the recommender lives on /watch/; the viewer at /evidence/*).
export const PHASE15_SURFACES = {
  dossier: "/dossier/oklahoma-city/",
  map: "/map/",
  network: "/network/",
  watch: "/watch/",
  evidence_recommender: "/watch/",
  evidence_viewer: "/evidence/active-device-count/",
  research_queue: "/research-queue/",
  corrections_log: "/corrections/",
} as const;

// The worked dossier's canonical slug + its derived surfaces (SIG-UI-010..015).
export const DOSSIER_SLUG = "oklahoma-city";
export const DOSSIER_PAGE = `/dossier/${DOSSIER_SLUG}/`;
export const DOSSIER_PRINT = `/dossier/${DOSSIER_SLUG}/print/`;
export const DOSSIER_JSON = `/dossier/${DOSSIER_SLUG}.json`;

// The reviewed research-dossier portfolio (P32.17, SIG-DOS-001/002) — the
// fixture dossier exercising all six answer states.
export const RESEARCH_INDEX = "/research-dossier/";
export const RESEARCH_SLUG = "okc-alpr";
export const RESEARCH_PAGE = `/research-dossier/${RESEARCH_SLUG}/`;
export const RESEARCH_JSON = `/research-dossier/${RESEARCH_SLUG}.json`;

// P34.12 (K11 §5.5 / RQ-00, F-113/F-274): the fixture `/task/new/<slug>/`
// intake pages are RETIRED — they claimed a research task "has been generated"
// from a gap when nothing had been, and `getStaticPaths` shipped demo fixture
// pages. There is deliberately no TASK_PAGE in the sweep any more; the real
// `/task/<handle>/` surface arrives with RQ-03 (K13 §7.1 W2).

export const ALL_PAGES = [...SHELL_PAGES] as const;

// The jurisdiction-conditional dossiers (FR-GDPR / BE-GDPR), localised and with the
// public-employee name withheld at build time (SIG-PUB-017, §44). Included in the a11y
// sweep so the localised pages meet WCAG 2.2 AA like every other shell page.
export const JURISDICTION_DOSSIER_PAGES = [
  "/dossier/paris-alpr/",
  "/dossier/brussels-alpr/",
] as const;

// The authenticated curation surface (P21.6, §34, ADR-068). NOT part of the public
// zero-JS shell — behind auth and under WCAG 2.2 AA (not the public zero-JS/perf
// budget). Kept here so the axe sweep covers them like every other page. The compare
// page id is URL-encoded (the item_id carries ':' and '~').
export const CURATE_COMPARE_PAGE = "/curate/er_match%3Aagency%3Aokcpd~agency%3Aokc-pd/";
export const CURATE_PAGES = [
  "/curate/",
  CURATE_COMPARE_PAGE,
  "/curate/contradictions/",
  "/curate/tasks/",
  "/curate/submit/",
  "/curate/revert/",
] as const;

// The data-freshness table's pre-rendered static sort routes (P27.7): sorting is a
// plain GET to a distinct page (no client JS), so each sort order must meet WCAG 2.2 AA
// like the base page. The base `/data-freshness/` is already in SHELL_PAGES.
// P34.13 (K12b NEW-11, F-17): the "stale" and "volatility" sort routes returned the
// identical alphabetical table — affordances that do nothing — and are REMOVED until
// UX9-2 makes a real ordering. Only the working status sort remains pre-rendered.
export const FRESHNESS_SORT_PAGES = [
  "/data-freshness/status/",
] as const;

// The no-op sort routes that must NOT exist in the build (K12b NEW-11) — asserted
// 404 in the freshness spec.
export const REMOVED_FRESHNESS_SORT_PAGES = [
  "/data-freshness/stale/",
  "/data-freshness/volatility/",
] as const;

// The P34.13 chrome pages (QW-11): branded error pages and the /terms forwarder.
// They render the shell header/nav but a minimal chrome (no provenance/citation
// module) and are noindex — in the axe + zero-JS sweeps like every public page.
export const CHROME_PAGES = [
  "/404.html",
  "/403/",
  "/410/",
  "/terms/",
] as const;

// The full a11y surface for the axe sweep: the shell-layout pages,
// the jurisdiction-conditional dossiers, the standalone dossier print export,
// the freshness sort routes, and the curation pages (WCAG 2.2 AA everywhere,
// SIG-UI-037 + P21.6).
export const A11Y_PAGES = [
  ...ALL_PAGES,
  ...JURISDICTION_DOSSIER_PAGES,
  ...FRESHNESS_SORT_PAGES,
  ...CHROME_PAGES,
  DOSSIER_PRINT,
  ...CURATE_PAGES,
] as const;

// The three OPT-IN public interactive islands (P27.9, ADR-097). These are the ONLY
// public pages that ship a hydration `<script>`; every other public page stays
// zero-JS (SIG-UI-036/037). Each preserves its no-JS fallback (SIG-UI-050).
export const ISLAND_PAGES = ["/map/", "/network/", "/search/"] as const;

// Every OTHER public page that MUST still ship zero `<script>` (AC2). The `/curate/**`
// island allowance (ADR-068) is proven separately in curate.nojs.spec.ts; the dossier
// print export is a standalone document. This is the shell surface minus the islands.
export const ZERO_JS_PUBLIC_PAGES = [
  ...ALL_PAGES,
  ...JURISDICTION_DOSSIER_PAGES,
  ...FRESHNESS_SORT_PAGES,
  ...CHROME_PAGES,
  DOSSIER_PRINT,
].filter((p) => !(ISLAND_PAGES as readonly string[]).includes(p)) as readonly string[];
