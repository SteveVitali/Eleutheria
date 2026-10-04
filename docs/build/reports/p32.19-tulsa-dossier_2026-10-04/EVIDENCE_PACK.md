<!-- SPDX-License-Identifier: Apache-2.0 -->
# P32.19 — Tulsa dossier evidence pack (offline)

Packet `sig.dossier-packet/1` / dossier `tulsa-tpd-alpr` — as-of 2026-09-27 (world) / 2026-09-27 (belief). Every row names the bytes the claims were read from and how those bytes were obtained. `live_verification=false`: nothing below is a live capture.

| document | bytes | capture digest (multihash) | how obtained | claims |
|---|---|---|---|---|
| `tulsa-mou-template` | 922 | `bcnagbpplwmrflkoxpxea4cnmecr6xm6…` | pdf_text / document / fixture_replay | 5 |
| `tulsa-policy-113c` | 937 | `bcnaig3acww6ixcoao5gwohjxj3vvzy2…` | pdf_text / document / fixture_replay | 7 |
| `tulsa-policy-113e` | 874 | `bcnaoe2ggfcixg77zar65yjqglpvarpu…` | pdf_text / document / fixture_replay | 4 |

## Document inventory and what each supports

| document | kind | what the packet takes from it |
|---|---|---|
| `tulsa-policy-113c` | TPD agency policy (PDF stand-in) | enacting body (Tulsa Police Department); the operator attribution authored from it; two distinct products — Flock Safety fixed ALPR and Axon Fleet 3 in-car; the 12-month period scoped verbatim to *manually entered* data; access restricted to authorized personnel; the stated 2023-07-07 effective date |
| `tulsa-policy-113e` | TPD agency policy (PDF stand-in) | sharing requires Chief of Police or designee approval; use limited to legitimate law enforcement purposes and official business; the uniform numeric retention period recorded reviewed-`absent` (a field-state, never a fabricated value); the stated 2023-10-04 effective date |
| `tulsa-mou-template` | blank MOU template (PDF stand-in, genre `template`) | offered structure/terms only — the purpose clause and the legitimate-law-enforcement-purposes use restriction as D6 claims; Licensor/Licensee/Date recorded `present_but_empty` — no executed contract, no named participants, no actual sharing edge |

## Template vs executed — recorded, not resolved

- The document marks itself 'TEMPLATE - not an executed instrument': the packet takes structure and offered terms only.
- The MOU's executed-instrument fields are `present_but_empty`: the packet asserts no execution, no parties and no signature date. The template proves terms *offered* — never adoption or an active partner relationship.
- No claim in the packet carries an executed-instrument predicate (`buyer`/`seller`/`signed_date`/`contract_value`/`amends_contract`) on the template — the emit-time guard and the release-side re-check both enforce it.
- The template's purpose clause ('the parties intend to share access to camera systems') lands as a D6 `written_policy_value` on q6 — offered terms — and never mints an access/partner edge on q4.

## Temporal distinctions (recorded, not resolved)

- Policy effective dates are STATED document dates — 113C 2023-07-07, 113E 2023-10-04 (`valid_from`, `effective_from`) — kept distinct from capture dates: replayed records carry each fixture's real authoring commit time, read from git (never a fetch); the evidence anchor is 2026-09-27T12:06:40+00:00.
- The captured 2023 policy files are NOT asserted to be the current enforceable versions: the published index's currency is a live-pass question (the packet declares the limitation, never a recency claim).
- The 12-month retention clause is scoped verbatim to manually entered LPR data; it is never generalized to every scan, and 113E's uniform period stays an honest `absent` field-state.

## Rights, review and acquisition posture

- `dossier_tulsa` stays `ingestion_permitted=false` (D-R10-SOURCES-1 OPEN): the three documents replayed committed stand-ins; the URLs are reviewed targets, not captured bytes.
- Independent semantic review: `not_run` — D-R10-HUMAN-1 OPEN. Mechanical completeness is reported separately from pilot completion (the honest `independent_semantic_review` checklist item fails rather than fabricating a reviewer).
- Unsupported counts, spend, partners and use are `unknown` with a documented search basis and a precise follow-up — never zero, never an inferred affirmative.

## Follow-up / RETURN PASS

Bounded live obligations are recorded in `LIVE_RETURN_PASS.json` (deferral `D-P32.19-1`): actual byte captures of the three reviewed URLs plus the TPD Flock page, the policies index and the Commercial Corridor Safety Guide lead — all behind HG-03, no rights flip, no gate completion. Gap follow-ups are drafted in `FOLLOW_UP_DRAFTS.json` through the real `tasks.detect` machinery — `status: drafted`, `records_requests_sent: 0`.
