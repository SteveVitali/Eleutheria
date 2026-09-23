## Summary
Lands the three actionable-timing / evidence-inspection public surfaces on P15.1's epistemic visual language + no-JS/a11y baseline and P15.2's `next_decision_date` wire contract. Implements the spec at `docs/tickets/P15.4__watch-evidence.md` (canonical §§39.5, 39.5a, 39.6; §29.7, §17.5). All work is confined to `web/` (SIG-ENG-010) and is additive.

- **Renewal watch** (§39.5): per-contract expiry, renewal window, notice deadline, approving body, next scheduled meeting, and replacement procurement (SIG-UI-026); per-jurisdiction **iCal** (RFC 5545, octet-folded) + **RSS** subscriptions emitted as **static files**, every alert **keyed on `next_decision_date`** reused verbatim from P15.2 — not the expiry (SIG-UI-027, SIG-UI-014b).
- **Evidence recommender** (§39.5a): a six-axis ordinal ranking — directness `D`, currency `C`, open contradiction, open task, artifact-type-vs-decision, `capture_status` (SIG-UI-027a) — with a **structural neutrality guarantee**: the input type carries no persuasiveness/sentiment/vote signal and a denylist rejects any smuggled in at runtime (SIG-UI-027b); output is an exportable citation list with belief-pinned permalinks + as-of dates (SIG-UI-027c).
- **Evidence viewer** (§39.6): document with the supporting span highlighted at its locator plus the full provenance chain enforced at build (SIG-UI-028), field-by-field capture diffing (SIG-UI-029, §29.7), and sealed captures rendered metadata-only with an explanation (SIG-UI-030, §17.5).
- **Contested values** carry the persistent marker at every appearance — watch list, feed text, recommender entry, citation export, and the conflicting-claims view (SIG-UI-008).

## What changed
- New libs: `web/src/lib/watch.ts`, `recommender.ts`, `evidence-viewer.ts`, `watch-evidence-fixture.ts`.
- New pages/endpoints: `pages/watch.astro`, `pages/watch/[jurisdiction].ics.ts`, `pages/watch/[jurisdiction].xml.ts`, `pages/watch/citations.txt.ts`, `pages/evidence/[id].astro`, `pages/evidence/index.astro`; nav + CSS additions.
- Tests: `tests/unit/{watch,recommender,evidence-viewer}.test.ts`, `tests/e2e/watch-evidence.spec.ts` + `.nojs.spec.ts`, `tests/e2e/pages.ts`.
- Docs: `ADR-052`, `docs/adr/README.md`, `docs/traceability.md`, `docs/risk_register.md`.

## Design decisions (ADR-052)
- Subscriptions are static build-time files (no feed server) to preserve the zero-JS/perf gates; the iCal/RSS serializers are single-sourced and tested.
- The watch **reuses** `resolveTermination`/`nextDecisionDate` from P15.2 rather than recomputing/forking, so the watch and the dossier can never disagree on the decision date.
- The recommender's neutrality is enforced structurally (closed type + denylist + pure per-axis score), not by convention — the property that keeps SIG a record, not an advocacy instrument.

## Verification
- `astro check`: 0 errors (58 files).
- Unit: **112 passed** (38 new).
- Build: 23 pages incl. `/watch/`, `/evidence/*`, the `.ics`/`.xml` feeds, and `citations.txt`.
- Licences: 197 deps OSI-only.
- E2E: **87 passed** (chromium + no-js), incl. axe **WCAG 2.2 AA** on every new page.
- Perf (lhci): green incl. the evidence pages (0 script bytes, ≤150 KB).

## Acceptance criteria → evidence
| AC | Status | Evidence |
|---|---|---|
| Surfaces exist + function | met | `/watch/`, `/evidence/` build + e2e |
| iCal + RSS by jurisdiction, keyed on `next_decision_date` | met | `watch.ts::toICal`/`toRss`; `watch.test.ts`; e2e feeds DTSTART/pubDate = 2027-01-02 (not 2027-04-02) |
| Recommender ranks only by directness/currency/dispute; persuasiveness/sentiment/vote absent | met | `recommender.ts` closed type + `FORBIDDEN_RANKING_INPUTS`/`assertNeutralInputs`; `recommender.test.ts` |
| Recommender output exportable as citation list w/ permalinks + as-of | met | `citationListText`; `watch/citations.txt`; tests |
| Viewer: span highlight at locator; field-by-field diff; sealed = metadata-only + explanation | met (agentic) | `evidence-viewer.ts`; `evidence/[id].astro`; unit + e2e (chromium + no-js) |
| Contested marked at every appearance | met | markers on watch/feed/recommender/export/viewer; tests |
| Phase-gate (§51.3) | met | CI-equivalent gates green; ADR-052; traceability + risk register updated |

Spec: `docs/tickets/P15.4__watch-evidence.md`. Requirement ids stamped: SIG-UI-026, -027, -027a, -027b, -027c, -028, -029, -030 (+ SIG-UI-008/014b, SIG-EVID-009/010, SIG-RECON-045).

Generated with [Devin](https://devin.ai)
