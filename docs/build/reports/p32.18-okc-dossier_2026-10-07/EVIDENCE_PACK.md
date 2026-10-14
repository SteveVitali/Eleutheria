<!-- SPDX-License-Identifier: Apache-2.0 -->
# P32.18 — Oklahoma City dossier evidence pack (offline)

Packet `sig.dossier-packet/1` / dossier `okc-flock-alpr` — as-of 2026-10-03 (world) / 2026-10-03 (belief). Every row names the bytes the claims were read from and how those bytes were obtained. `live_verification=false`: nothing below is a live capture.

| document | bytes | capture digest (multihash) | how obtained | claims |
|---|---|---|---|---|
| `okc-contract-c241032` | 1386 | `bcnadubksduuhzyywfancroisfb3wzu7…` | fixture_transcription / committed_fixture / stand-in | 5 |
| `okc-council-memo-2026-08` | 931 | `bcnaol6wye4ttw7lbce4hoqkkdaivd4t…` | pdf_text / document / fixture_replay | 4 |
| `okc-flock-amendment-2026` | 1068 | `bcnag5e56hd5r7dfvvlk357ctoff7dx6…` | pdf_text / document / fixture_replay | 7 |
| `okc-flock-usage-2026` | 444 | `bcnamnoklnmhz4rddujrv57uivhjcdyq…` | html_text / document / fixture_replay | 5 |
| `okc-ops-manual-5-118` | 1540 | `bcnapwpreim3d6ym7jc5723pj4tsbup6…` | fixture_transcription / committed_fixture / stand-in | 2 |
| `okc-p06-evidence-fixture` | 7441 | `bcnaa6v2z35pxf3vszq76ktb4gxdlj67…` | fixture_transcription / committed_fixture / stand-in | 12 |
| `okc-statute-47-7-606-1` | 1363 | `bcnahazrkd4qp7mfdjnuugfyb2xay5zv…` | fixture_transcription / committed_fixture / stand-in | 2 |

## Document inventory and what each supports

| document | kind | what the packet takes from it |
|---|---|---|
| `okc-flock-usage-2026` | official city page (HTML stand-in) | 90 city-owned readers; 109 partner agencies (aggregate degree); 7-day retention effective 2026-10-01; the ongoing-investigation exception |
| `okc-council-memo-2026-08` | council/governance document (PDF stand-in) | Amendment 1 / Renewal 3; $270,000 for Jul 2026–Jun 2027; posted 2026-08-18 — a governance record, NOT executed-contract evidence |
| `okc-flock-amendment-2026` | amendment text (PDF stand-in) | actor-scoped federal-disclosure restriction + compulsory-process exception; precedence over the Agreement; `signed_date`/`execution_state` recorded `present_but_empty` — execution is unverified, never inferred |
| `okc-statute-47-7-606-1` | committed transcription fixture (ok_statute) | 47 O.S. §7-606.1 — insurance-enforcement restriction scoped to the UVED program; NOT generalized to the OKCPD Flock program |
| `okc-ops-manual-5-118` | committed transcription fixture (okcpd_policy) | sharing restriction + the manual's own scope (vehicle-mounted readers) — policy evidence, applicability recorded |
| `okc-contract-c241032` | committed transcription fixture (okc_procurement) | vendor Flock Safety; contract C241032; $270,000/yr; 90 units |
| `okc-p06-evidence-fixture` | P06.1 committed evidence fixture | journalism/council statements (D6) + the corrected-seed scope partition — DeFlock 299 metro, the chief ~100 private city-limits, 90 active agency-operated, ~190 derived |

## Digest, signature and temporal uncertainty (recorded, not resolved)

- `signed_date` and `execution_state` on the amendment are `present_but_empty`: a partially-evidenced signature block means execution is unknown — the packet asserts neither signing nor execution.
- The council memo's original-approval references are internally inconsistent; the packet keeps the lifecycle label verbatim and asserts no reconciled original date.
- The 7-day retention rule is a STATED rule with a stated effective date (2026-10-01). On the scenario frame 2026-10-02 the change is announced; operational implementation is unverified (follow-up in the packet).
- Replay capture dates are each fixture's real authoring commit time, read from git (never a fetch); the evidence anchor is 2026-10-03T14:11:51+00:00. Stated document dates stay distinct from capture chronology on every claim.

## Rights, review and acquisition posture

- `dossier_okc` stays `ingestion_permitted=false` (D-R10-SOURCES-1 OPEN): the three documents replayed committed stand-ins; the URLs are reviewed targets, not captured bytes. The OKC shadow fixtures are reviewed transcriptions, not live captures.
- Journalism is `claim_directness=D6` — reported statements, never instruments; council materials are governance records, never executed-contract evidence.
- Independent semantic review: `not_run` — D-R10-HUMAN-1 OPEN. Mechanical completeness is reported separately from pilot completion.
- The ODbL OSM compartment stays separate; its seed row is scope-labelled by the correction packet and is not part of this CC-BY pack.

## Follow-up / RETURN PASS

Bounded live obligations are recorded in `LIVE_RETURN_PASS.json` (deferral `D-P32.18-1`): actual byte captures of the six reviewed URLs, the amendment signature pages, the post-effective retention page, the OSCN statutory version, the purchasing index (WAF-gated) — all behind HG-03, no rights flip, no gate completion.
