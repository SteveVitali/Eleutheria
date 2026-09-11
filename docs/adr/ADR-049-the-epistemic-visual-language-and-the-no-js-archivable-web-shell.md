# ADR-049: The epistemic visual language and the no-JS, archivable web shell

- **Status:** Accepted
- **Date:** 2026-09-01
- **Phase:** P15.1
- **Requirement ids:** SIG-UI-003, SIG-UI-004, SIG-UI-005, SIG-UI-006, SIG-UI-007, SIG-UI-008, SIG-UI-009, SIG-UI-035, SIG-UI-036, SIG-UI-037, SIG-UI-039, SIG-UI-041
- **Spec:** docs/2_canonical_design_spec.md §§39.0 (personas / design center), 39.1 (epistemic visual language), 39.9 (citation and permanence), 40 (implementation stack and design system)

## Context

P15.1 builds the Astro web shell (the framework choice itself is ADR-014) and — the
load-bearing part — **owns the epistemic visual language and the a11y / no-JS /
archivability baseline that every later Phase-15 surface (P15.2–P15.5) consumes**.
Those surfaces reference these components; they do not redefine them. The design
center is the local advocate (SIG-UI-002): plain-language, paper-friendly, honest
about gaps. Several concrete decisions were needed that the spec constrains but does
not fully specify, and each shapes every downstream surface — hence this record.

## Decision

1. **The visual language is pure data + logic in `web/src/lib/epistemic.ts`, colour-free.**
   The four §10.7 fields (`resolution_status`, `support`, `agreement`, `currency`) are
   rendered as four INDEPENDENT chips — never a fused badge (SIG-UI-004). Support is a
   four-step glyph that always travels with a text equivalent, a machine-readable
   evidence count, and a stable downgrade reason code (SIG-UI-003). Absence has exactly
   ONE hatch texture (`.sig-absence-hatch`); the four §9.5 kinds are distinguished
   *within* it by a distinct symbol + text (SIG-UI-007). A contested value carries a
   persistent `≠` marker at every appearance (SIG-UI-008). A contradiction renders as a
   value range with each competing claim plotted (source/tier/date/link + a
   different-quantity note, SIG-UI-009).

2. **"Green never for epistemic state" is enforced mechanically (SIG-UI-006).** Every
   `--sig-epi-*` colour token in `web/src/styles/epistemic.css` is written as an `hsl()`
   whose hue lies OUTSIDE the green band [75°, 165°]; a unit test parses the stylesheet
   and fails on any green token, and an e2e test re-checks the *rendered* hues. Colour is
   always a redundant channel (SIG-UI-005): meaning is carried by glyph/symbol/text.

3. **Static-first, zero-JS-by-default, archivable by construction (SIG-UI-036/037).**
   `output: "static"` and no `client:*` directive anywhere ⇒ the build ships **zero client
   JavaScript** (asserted: `dist` has 0 `.js` files; the Lighthouse `script:size` budget is
   0 bytes). Breaking archivability requires an explicit, greppable `client:` directive.
   Every map has a `<table>` tabular equivalent and every graph a `<ul>` list equivalent,
   verified by a Playwright project that runs with **JavaScript disabled**.

4. **The shell reads committed TS fixtures, not a live API, at build time.** Static-first
   means no build-time API dependency. `web/src/lib/fixtures.ts` mirrors the read-API wire
   contract: its `ResolutionEnvelope` is a faithful *subset* of
   `api/src/api/models.py::ResolutionEnvelope`, so the shell wires to the live `/v1` API
   unchanged. Presentation data the envelope does not carry (the glyph's evidence count,
   the plotted competing claims) lives on an outer `FactView` view-model, never on the
   wire-envelope type.

5. **A clicked absence gap generates a research task with no JavaScript (SIG-UI-007).** The
   hatch is a plain GET link to a **pre-generated** intake page (`getStaticPaths` over the
   `TASKABLE_ABSENCES` registry). The task parameters are carried in a **base64url** path
   slug — URL- and filesystem-safe on any OS — and decoded to a `GENERATED` research-task
   descriptor mirroring the engine's `research_task` row (status, `(task_type, subject)`
   dedup key, absence kind, rationale).

6. **Belief-pinned permalinks + citation on every page (SIG-UI-035).** `Citation` renders on
   every page through `BaseLayout`; the permalink pins both as-of axes and the ruleset
   version (canonical origin from Astro's `site` config), so a citation captured today
   re-resolves to the same belief after a later correction — proven by a `resolveAsOfBelief`
   test that appends a correction and shows the pinned answer is unchanged.

7. **The three mandated gates run in CI, not by memory.** A `web` job in
   `.github/workflows/ci.yml` runs: axe WCAG 2.0/2.1/2.2 A+AA on every page (SIG-UI-037), the
   dependency-licence gate (SIG-UI-039), and Lighthouse performance budgets that fail the
   build on regression (SIG-UI-041).

## Deviation: the licence gate is "OSI **or** a short documented waiver," not literal OSI-only

SIG-UI-039 says every dependency must be OSI-licensed. The Astro build toolchain tree
resolves two dependencies to licences that are permissive/public-domain but **not on the
OSI-approved list**: `CC0-1.0` and `BlueOak-1.0.0`. Neither is any of the categories the
requirement exists to exclude (non-commercial CC-BY-NC, source-available, or dual-BUSL).
`web/scripts/check-licenses.mjs` therefore keeps a strict `OSI_ALLOW` set and a separate,
explicitly-enumerated `WAIVED` set (currently exactly those two), plus a `DENY` tripwire for
the excluded categories. The split means the gate never silently mislabels a waived licence
as OSI, and adding any *other* non-OSI licence still fails the build until a human reviews it.

## Consequences

- P15.2–P15.5 import these components and inherit the a11y/no-JS/archivability baseline; the
  visual language is defined once. Any change to it is a new ADR, not an ad-hoc edit (§0.7).
- The shell is decoupled from API availability in CI, at the cost of keeping the fixtures'
  envelope subset in sync with `models.py` (a faithful subset, guarded by review).
- The self-hosted-tiles map renderer (SIG-UI-038) and the Postgres FTS search (SIG-UI-040)
  are **not** decided here: the reference map is a static, tile-CDN-free SVG + table, and the
  real map/search land with P15.3 / on demonstrated need.

## Alternatives considered

- **Build-time fetch from a running `sig-api`** (rejected): most faithful, but couples the
  static build and CI to a live API and undercuts the "reads from a plain fixture" simplicity.
- **Client-hydrated task intake reading a query string** (rejected): would put the SIG-UI-007
  flow behind JavaScript, violating the no-JS baseline; the pre-generated static route keeps it
  archivable.
- **A single fused epistemic badge with a colour scale** (rejected by the spec, SIG-UI-004/006):
  cannot express "strongly supported but contested," and colour scales lean on green.

## Revisit trigger

Revisit when the shell is wired to the live `/v1` read API (if the envelope subset in
`fixtures.ts` diverges from `api/src/api/models.py`), when the self-hosted-tiles map renderer
lands (P15.3, SIG-UI-038) and the reference SVG must be reconciled with it, or when a new
dependency requires a licence that is neither OSI-approved nor in the current `WAIVED` set —
at which point the waiver must be re-justified or the dependency dropped.
