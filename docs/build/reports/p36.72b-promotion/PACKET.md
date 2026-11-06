<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# P36.72b — core-surfaces Class S promotion packet (`prepared_not_executed`)

`sig.core-surfaces-promotion/1` — see `packet.json` for the machine row.

Ticket `416_P36.72b__core-surfaces-walkthroughs-and-promotion.md` /
**R11-K13-ACC-PLACES b-half** — the walkthrough record + the Class S readout
staging + the promote leg. The promote is **the operator's HG-11 act at the
GATE-G6 sitting** — this packet stages the evidence and the verb; it never
promotes, never signs, never ticks HG-11.

**Status: `prepared_not_executed`** — nothing was promoted, signed, staged
to a bucket, or rolled. The promote leg is QUEUED for the OM-19 re-run below.

## Authority — the plan cells, verbatim

- **Gate status (contract cell, verbatim):**
  `IN-TICKET PAUSE: HG-11 Class S readout for the core-surfaces release (same sitting as GATE-G6)`
- **OM-20 status:** `never pre-authorised` — HG-11's Class S promotion is
  the operator's act at the GATE-G6 sitting; the leg pauses in-ticket for it.
- **Live window (contract cell, verbatim — the leg stays queued, never executed here):**
  `release cut never inside AR-3 windows (expected >= 2026-11-13T12:00Z)`
- **Live leg (contract cell, verbatim — queued, never run here):** `1: promote after HG-11`
  (0.5 leg run).
- **Production mutation (OM-14, none executed this run):** the Class S promotion itself —
  metadata-only (`registry/conf/<gen+1>` + the api→web digest rolls; zero
  release bytes copied). Restore point: the prior release stays published;
  `sig-ops release rollback` re-points `latest` at it.

## The evidence the operator reads

1. **P36.72a's acceptance readout** —
   `docs/build/reports/p36.72a-acceptance/READOUT.md` +
   `readout.json` (`sig.core-surfaces-acceptance/1`): **PASS
   (fixture-verified)** — 506/506 across the crawl (477 discovered routes,
   0 unexplained 404s), historical-URL end-states (all 38 redirect rules),
   bare-id sweeps, HTML = JSON twin parity, number truth over 5,150 figure
   regions, bijective ROUTES.csv dispositions (48 rows), axe WCAG 2.2 AA in
   both JS states, per-type budgets, and these walkthroughs. Its named
   limits (fixture-scope redirect targets, unserved artifacts, external
   rows, `/s/<pub>/` + `/v1/releases/…` parity legs) are recorded there —
   the promoted-release legs own them (`D-P36.71-1`, `D-P36.35-1`,
   `D-R10-PUBLISH-1`).
2. **The walkthrough record** — `WALKTHROUGHS.md` beside this packet:
   A1 A2 A3 A4 O1 O3 O4 J1 re-run 9/9 green on 2026-11-05 over the fixture
   build, recorded **`agent-verified`** — never user research.
3. **The classifier's own readout draft** — at the sitting,
   `sig-ops release classify --apply` writes the `sig.release-readout/1`
   pair under `registry/readouts/<pub>.{json,md}` (agent-drafted, signature
   slot empty by construction, the required wording verbatim) and fires the
   `release.readout-pending` notice on the landed alerts seam. That draft —
   not this packet — is the document the operator signs.

## The queued leg — promote after HG-11 (0.5 run)

Runs only after the operator's signed readout exists under
`registry/approvals/` (`sig.promotion-approval/1`, `kind: signed_readout`,
`class: class_s`, `publication_id` = the candidate's `p-<sha256>`,
`signature` + `basis` present — the verb checks the record, it never
creates one). Sequence the leg-runner executes:

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
then `sig-web` by digest (`min-instances=1` through the flip) → post-promote
checks → journals `promoted`. An absent/refused approval fails closed; a
red P-mode check stays recorded — the restore point is the prior release.

## Environment the leg needs (absent here — never fabricated)

- `SIG_RELEASE_REGISTRY` (the private release bucket) + ADC /
  `SIG_GCP_PROJECT` — none present in this run shell.
- The staged candidate `p-<sha256>` (the release cut/build/stage/verify-S
  legs the sitting's runner performs — the cadence machinery
  `D-P36.44-1` or a manual `release cut → build → sites → stage → verify
  --mode S` sequence).
- The operator's signed-readout object name under `registry/approvals/`
  (written at the sitting, never by this row).
- Digest-pinned `sig-api`/`sig-web` images + `--project`/`--region` for the
  roll legs (the operator's `--execute-rolls` posture).
- Window: the promote runs **at/after the GATE-G6 sitting**, never inside
  AR-3 windows (contract cell, verbatim).

## Re-run prompt (verbatim — OM-19)

```
implement-spec spec=docs/tickets/416_P36.72b__core-surfaces-walkthroughs-and-promotion.md live_verification=true
```

Obligation: `D-P36.72b-1` (OPEN) — closed by the journaled `promoted`
event + a green P-mode verify on the promoted core-surfaces release.

## Named limits (recorded, never silently skipped)

- **No candidate exists yet in this environment** — the pub id is resolved
  at the sitting; the packet names the verb, never a fabricated id.
- **The readout draft is the classifier's** — this packet packages the
  acceptance evidence; `release classify` produces the signable
  `sig.release-readout/1` pair at the sitting.
- **Verify legs downstream:** the post-promotion search-acceptance legs
  ride `D-P36.71-1`; the redirects.conf include carry rides `D-P36.35-1`;
  external/public-exposure rows ride `D-R10-PUBLISH-1`.

*This packet records the pause; it never implies the operator signed, the
release promoted, or HG-11 ticked.*
