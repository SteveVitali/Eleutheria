<!-- SPDX-License-Identifier: Apache-2.0 -->
# P32.20 — San Diego dossier evidence pack (offline)

Packet `sig.dossier-packet/1` / dossier `san-diego-sdpd-alpr` — as-of 2026-09-27 (world) / 2026-09-27 (belief). Every row names the bytes the claims were read from and how those bytes were obtained. `live_verification=false`: nothing below is a live capture.

| document | bytes | capture digest (multihash) | how obtained | claims |
|---|---|---|---|---|
| `sd-asr-2025-vigilant` | 1002 | `bcnahgc5tkk62ylpau3asf4liv3iimsw…` | pdf_text / subscription / fixture_replay | 11 |
| `sd-pab-index` | 371 | `bcnais6jwoqh5qhgonafhpwkyc4uhmyi…` | html_text / document / fixture_replay | 5 |
| `sd-technology-index` | 460 | `bcnam7m3jdbew42nnr7wgn4zti7hy3nq…` | html_text / document / fixture_replay | 8 |
| `sd-ubicquia-agreement-2023` | 965 | `bcnap7tmundad3eb75ztrshepb3ign44…` | pdf_text / document / fixture_replay | 13 |

## Document inventory and what each supports

| document | kind | what the packet takes from it |
|---|---|---|
| `sd-asr-2025-vigilant` | SDPD Annual Surveillance Report 2025 (Vigilant section; `official_statement`, access_mode `subscription`) | configured subscription access + pooled lookup participation + vendor-cloud-shared data scope (q4); vendor Vigilant Solutions and product Vigilant LEARN (q1/q2); the 2025 report period (q9); the 60-day period scoped to the subscription's ALPR data (q7); the agency's bounded no-hardware statement (q3, authored) — **never a device count, deployment existence, location or implementation claim** |
| `sd-ubicquia-agreement-2023` | City–Ubicquia public-safety agreement (genre `contract`) | buyer City of San Diego, prime contractor `seller` Ubicquia, Inc. and component `vendor` Flock Safety, Inc. as distinct roles; value $11,662,500 and five-year term; 500 streetlight units scoped `contracted_units` — contracted ≠ installed; vendor-side `signed_date` 2023-12-15 verbatim and `City Date:` recorded `present_but_empty` — execution unverified |
| `sd-technology-index` | SDPD surveillance-technology index (`portal_document`) | the index listings — ALPR Program, 2025 ASR, ALPR Use Policy — existence + verbatim titles + the 2026-02-15 posted date; the authored technology claim for the physical program cites the ALPR Program anchor span |
| `sd-pab-index` | Privacy Advisory Board reports index (`portal_document`) | the PAB recommendation's existence + verbatim title and the Annual Reports listing; the authored `authorization_state` keeps the recommendation **proposed** — cited to the index anchor span |

## Subscription vs hardware — enforced, not resolved

- The ASR's `access_mode` is `subscription`: the connector's hardware guard barred every device/location predicate at emit time, and the packet asserts no local SDPD camera, device count, deployment existence or fixed asset from the subscription.
- The only q3 subscription statement is the agency's own bounded sentence — 'owns no ALPR cameras or hardware **under this arrangement**' — scoped verbatim; it is never a universal absence claim and never evidence about the streetlight program.
- The physical program's only count is 500 units scoped `contracted_units` — contracted is not installed; no installed/active/current count is asserted anywhere.

## Prime contractor vs component vendor

- `seller = Ubicquia, Inc.` is the named contracting party; `vendor = Flock Safety, Inc.` is the component supplier whose terms are incorporated by reference — separate predicates, an authored claim records the split, and a vendor mention never mints an operational relationship.

## Recommendation vs adoption — and self-report vs oversight

- The PAB recommendation is evidenced by its index listing (existence + verbatim title + original span locator) and stays `proposed` — no claim asserts adoption, enactment or policy force.
- The 2025 ASR is the agency's own self-report (`official_statement`) — distinct in genre and in what it can support from the oversight body's instrument.

## Signature vs execution — recorded, not resolved

- `signed_date` carries 'Vendor Date: 12/15/2023' verbatim — a vendor-side date; `City Date:` is a `present_but_empty` field-state. The genre stays `contract`; nothing calls the agreement executed.

## Part VIII preflight — metadata only

- The ALPR index's 2024–2026 network-audit spreadsheet links (SRC-027) were reviewed by link/label metadata only. No workbook byte, XLSX container, ZIP member or `sharedStrings` stream was fetched, staged or transported; per-query audit workbooks may carry plates, person-level queries and officer identities — the workbook acquisition path is `rejected` permanently (E4-B3 = a).
- A safe agency-level aggregate could later support q8 through an approved workflow; it is optional and the dossier does not depend on it (PART_VIII_PREFLIGHT.json).

## Temporal distinctions (recorded, not resolved)

- Stated dates are document dates — the 2023-12-15 vendor-signed date, the 2025 report period and the 2026-02-15 posted date are never promoted to capture dates: replayed records carry each fixture's real authoring commit time, read from git (never a fetch); the evidence anchor is 2026-09-27T12:06:40+00:00.
- Captured index listings are not asserted to be the current versions: index currency is a live-pass question.

## Rights, review and acquisition posture

- `dossier_san_diego` stays `ingestion_permitted=false` (D-R10-SOURCES-1 OPEN): the four documents replayed committed stand-ins; the URLs are reviewed targets, not captured bytes.
- Independent semantic review: `not_run` — D-R10-HUMAN-1 OPEN. Mechanical completeness is reported separately from pilot completion (the honest `independent_semantic_review` checklist item fails rather than fabricating a reviewer).
- Unsupported facts are `unknown` or declared `partial` with a documented search basis and a precise follow-up — never zero, never an inferred affirmative.

## Follow-up / RETURN PASS

Bounded live obligations are recorded in `LIVE_RETURN_PASS.json` (deferral `D-P32.20-1`): actual byte captures of the four reviewed URLs plus the ALPR detail page, the ALPR Use Policy, the PAB recommendation PDF, the council/budget leads and the preflight-only network-audit links — all behind HG-03, no rights flip, no gate completion. Gap follow-ups are drafted in `FOLLOW_UP_DRAFTS.json` through the real `tasks.detect` machinery — `status: drafted`, `records_requests_sent: 0`.
