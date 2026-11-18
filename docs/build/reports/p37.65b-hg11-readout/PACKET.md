<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# P37.65b — the HG-11 final Class S readout + promotion packet (`prepared_not_executed`)

`sig.hg11-readout/1` — see `packet.json` for the machine row.

Ticket `494_P37.65b__final-readout-and-promotion.md` /
**R11-K13-TX-16 b-half** — the journalist/researcher/skeptic journey
re-runs + the final HG-11 Class S readout + the promote leg. The promote
is **the operator's act at the readout** — this packet stages the evidence
and the verb; it never promotes, never signs, never ticks HG-11.

**Status: `prepared_not_executed`** — nothing was promoted, signed, rolled
or cut. The promote leg is QUEUED for the OM-19 re-run below.

## Authority — the plan cells, verbatim

- **Gate status (contract cell, verbatim):**
  `IN-TICKET PAUSE: HG-11 final Class S readout (covers MAP-07, ACC-EXPLORE, TX-12 exposure, Wave C/D sources, CONF-12)`
- **OM-20 status:** `never pre-authorised` — the promote leg runs only on
  the operator's verbatim go at the readout; it is never pre-authorised.
- **Live window (contract cell, verbatim — the leg stays queued, never
  executed here):**
  `final release cut never inside AR-3 windows (12-06 -> 12-13T12:00Z)`
- **Live leg (contract cell, verbatim — queued, never run here):**
  `1: promote after HG-11` (0.5 leg run).
- **Production mutation (OM-14, none executed this run):** the promote leg
  itself — metadata-only (`registry/conf/<gen+1>` + the api→web digest
  rolls; zero release bytes copied). Restore point: the prior release
  stays published; `sig-ops release rollback` re-points `latest`.

## The readout — what the operator is asked to decide

Sign (or decline) the final Class S readout for the transparency
republish: the release whose acceptance evidence is folded in below. The
decision the readout asks is whether the candidate — once P37.65a's
deferred `release-cut` + `live-crawl` legs stage and verify it — may be
promoted `class_s` (the `1: promote after HG-11` leg). The signable
`sig.release-readout/1` pair is drafted at the sitting by
`sig-ops release classify --apply` under `registry/readouts/<pub>.{json,md}`
— agent-drafted, signature slot empty by construction. This packet is the
evidence set the decision reads; it is not the document signed.

## The coverage the readout folds in (the plan cell's five areas)

| area | evidence | layer reached |
|---|---|---|
| **MAP-07** (P37.63 map acceptance) | `docs/build/reports/p37.63-map-acceptance/PACKET.md` — J1–J10 10/10 fixtures + 10/10 at real size (232,500-site national build); tile verify PASS; budgets 523/523; LHCI `/map/` green | fixture-verified; the candidate/live legs (`live-journeys`, `live-lhci`, `live-tiles`, `cost-7d`) ride `D-P37.63-1` — `prepared_not_executed` |
| **ACC-EXPLORE** (P37.64 entity/graph/dossier-figure acceptance) | `docs/build/reports/p37.64-explore-acceptance/PACKET.md` — 15/15 dist sweep over 515 emitted routes (D20 + DV01…DV12 incl. the records-side parity chain + print composition) + 15/15 journey battery (K2 J-1…J-6, K6 VJ-1…VJ-6, K13 §8 capstone legs, axe in interaction states) | fixture-verified; `live-verify` rides `D-P37.64-1` — `prepared_not_executed` |
| **TX-12 exposure** (P37.36 raw archive) | `docs/build/reports/p37.36-raw-archive/PACKET.md` — the raw-ok lane (`D-J3-1 [B-19] = yes` verbatim): `raw-archive build` over the hosted evidence store after the Part VIII byte screen, P8-5/6/8 as new-capture reserialisations, push by content-hash key, the withdrawal rehearsal receipt | the archive-write legs are `prepared_not_executed` (never pre-authorised — verbatim go + hosted env absent); the exposure this readout covers is recorded as riding HG-11 — nothing links the raw bytes publicly before it |
| **Wave C/D sources** | Wave C: `docs/build/reports/p37.2-wave-c/WAVE_C_PACKET.md` (`prepared_not_executed` — L1–L5 queued inside `2026-11-16→20`, verbatim ING-GO-C recorded at GATE-G5) · Wave D: `docs/build/reports/WAVE_D_RUNBOOK.md` + `WAVE_D_FLIP_LIST.md` (146 flag rows, all `ingestion_permitted=false`; legs gated `2026-11-23→12-04` / `2026-12-14→12-18` under verbatim ING-GO-D + OP-26 flips) | both waves' hosted legs are queued `prepared_not_executed` — the readout records the wave posture; it neither flips a source nor claims a wave ran |
| **CONF-12** (P37.45 public `/quality/` page) | `web/quality.json` (`sig.quality-page/1`) + `web/src/pages/quality/index.astro` — every registered check rendered with its state (failing + ratchet shown), "no human check performed" verbatim, the basis table's independent-review row `none`; coverage `SIG-CONF-011 → MET-ENGINEERED(D-R10-PUBLISH-1)` | engineered + fixture-verified (`quality.spec.ts` re-ran green in this row's journey set); the served-layer half rides the publish path |
| **TX-16** (P37.65a transparency acceptance) | `docs/build/reports/p37.65a-transparency-acceptance/PACKET.md` + `scrub-audit.json` (`sig.scrub-audit/1`) — the publish-set scrub audit over 273 published-transparency files, **0 secret-shaped hits**; J1/J4 deterministic legs 4/4; budgets 523/523 | fixture-verified; `release-cut` + `live-crawl` ride `D-P37.65a-1` — `prepared_not_executed` (the hosted registry 404s under `D-P35.53-1`, OPEN, owner: the operator OP-24) |

## This row's own evidence — the journey re-runs

`WALKTHROUGHS.md` beside this packet: the journalist / researcher /
skeptic re-runs — **599/599 agent-verified legs green** on 2026-11-18 over
the emitted fixture build (528 pages / 530 classified routes), never user
research. J1, J2, J-2, VJ-3, VJ-5, J5 (journalist); J4's deterministic
half, J-5 (researcher); J3, `/quality/`, methodology, corrections log,
dispute path, open questions (skeptic). J4's durable-pin half rides
`D-P37.65a-1`'s live crawl — recorded, never claimed.

## The queued leg — promote after HG-11 (0.5 run)

Runs only after **both** hold: (a) the operator's verbatim go at this
readout — recorded as a `sig.promotion-approval/1`
`kind=signed_readout` record under `registry/approvals/` naming the
candidate `p-<sha256>` (`class_s`, `signature` + `basis` present — the
verb checks the record, it never creates one); and (b) a staged
candidate exists — `D-P37.65a-1`'s `release-cut` + `live-crawl` legs must
land first (blocked on `D-P35.53-1`, the release-infra apply leg, owner:
the operator OP-24). Sequence the leg-runner executes:

```
# 0. resolve the candidate — the staged pub id (journal / staged/ tree)
PUB=<p-<sha256>>

# 1. the promote (metadata-only; --apply performs the writes)
sig-ops release promote --registry "$SIG_RELEASE_REGISTRY" \
  --publication "$PUB" --approval <readout-name> --class class_s \
  --api-image <repo>/sig-api@sha256:<64> --web-image <repo>/sig-web@sha256:<64> \
  --project <gcp-project> --region <gcp-region> --min-instances 1 \
  --apply --execute-rolls

# 2. the post-promote P-mode verify on every public origin
sig-ops release verify --registry "$SIG_RELEASE_REGISTRY" \
  --work-dir <tree> --publication "$PUB" --mode P \
  --origin <each public origin> --api-origin <api origin> --apply
```

`promote` checks the approval → writes `registry/conf/<gen+1>` (latest
pointer, `promoted.map += pub`, carried barrier files) → rolls `sig-api`
then `sig-web` by digest (`min-instances=1` through the flip) → post-
promote checks → journals `promoted`. An absent/refused approval fails
closed; a red P-mode check stays recorded — the restore point is the prior
release. The promote unlocks the downstream verify legs: `D-P37.63-1`
(map live legs + cost-7d), `D-P37.64-1` (explore live-verify), and the
P37.66 coverage-outcome closeout.

## Environment the leg needs (absent here — never fabricated)

- `SIG_RELEASE_REGISTRY` (the private release bucket) + ADC /
  `SIG_GCP_PROJECT` — none present in this run shell;
  `gs://eleutheria-sig-release` 404s under `D-P35.53-1` (OPEN, owner: the
  operator OP-24 — recorded verbatim, never papered over).
- The staged candidate `p-<sha256>` — `D-P37.65a-1`'s cut/build/stage +
  `verify --mode S` legs, themselves queued on the registry.
- The operator's verbatim go at this readout + the signed-readout object
  name under `registry/approvals/` (written at the sitting, never by this
  row).
- Digest-pinned `sig-api`/`sig-web` images + `--project`/`--region` for
  the roll legs (the operator's `--execute-rolls` posture).
- Window: the promote runs **after the operator's verbatim go**, never
  inside the AR-3 windows the plan cell names
  (`12-06 -> 12-13T12:00Z`, verbatim).

## Re-run prompt (verbatim — OM-19)

```
implement-spec spec=docs/tickets/494_P37.65b__final-readout-and-promotion.md live_verification=true
```

Obligation: `D-P37.65b-1` (OPEN) — closed by the journaled `promoted`
event + a green P-mode verify on the promoted release.

## Named limits (recorded, never silently skipped)

- **No candidate exists yet in this environment** — the pub id is resolved
  at the sitting; the packet names the verb, never a fabricated id. Even
  the operator's "go" cannot promote a release whose cut has not run —
  `D-P37.65a-1` is the recorded prerequisite.
- **The signable readout is the classifier's** — this packet packages the
  acceptance evidence; `release classify` produces the
  `sig.release-readout/1` pair at the sitting.
- **No live or public claim** — every verdict recorded here is engineered
  or fixture-verified; nothing asserts a staging, live or public state
  (SIG-ENG-042).

*This packet records the pause; it never implies the operator signed, the
release promoted, or HG-11 ticked.*
