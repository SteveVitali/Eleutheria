<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# P36.70 — second-release acceptance packet (`prepared_not_executed`)

`sig.second-release-acceptance/1` — see `packet.json` for the machine row.

Ticket `417_P36.70__second-release-acceptance.md` / **R11-REL-11** — the
rollback + withdrawal rehearsal machinery and the staged leg on the second
activated release (P36.72b's). **Status: `prepared_not_executed`** — nothing
was promoted, rolled back, withdrawn, signed, or rolled; no production
mutation ran and no gate row was added. The leg stays QUEUED for the OM-19
re-run below.

## Authority — the plan cells, verbatim

- **Gate status (contract cell, verbatim):**
  `D-G3-3 [B-9] = a: the first Class R promotion runs under the standing go if it is still valid (renewed at GATE-G5); otherwise as Class S (IN-TICKET PAUSE)`
- **OM-20 status (contract, verbatim):** `conditional — the first Class R
  promotion runs under the standing go only if it is still valid (renewed
  at GATE-G5); otherwise the leg pauses in-ticket and runs as Class S`.
- **The standing go (adopted verbatim, 2026-10-01T04:35:53Z):**
  "Agents may promote a Class R release built from the same signed code
  whose diff stays within bounds (records −2%…+15%, no compartment <−5% or
  >+50%, no source loses >20%), with all checks green and no waivers; this
  go expires at the next sub-round gate or after 30 days, and is void on
  any ratchet regression, Part VIII screen change or new source."
- **Validity — quoted from the record, never presumed:** GATE DECISIONS
  records the GATE-G5 sitting (2026-10-25T18:40Z) renewing the go verbatim —
  `expires GATE-G6 or 2026-11-24, whichever first`. The go is valid now,
  but the rehearsal leg's precondition — P36.72b promoted — is the
  operator's HG-11 act at the GATE-G6 sitting, exactly when the go
  expires → the contract's own fallback applies: the legs run **Class S**
  under operator `sig.operator-authority/1` records
  (`registry/authorities/<name>.json` — the verbs verify them, never
  create them, SIG-SEC-010).
- **Live window (contract cell, verbatim — the leg stays queued, never
  executed here):** `after P36.72b promotes (>= 2026-11-13T12:00Z); weekday
  14:00-20:00Z`.
- **Live leg (contract cell, verbatim — queued, never run here):**
  `1: rollback + withdrawal rehearsal after P36.72b promotes` (0.5 leg run).
- **Mutation (OM-14, none executed this run):** `the Class R promotion
  rehearsal (conditional on the standing go's validity) + the
  rollback/withdrawal rehearsal on a low-stakes record — bounded,
  reversible`. Restore points are the rehearsal's own machinery.

## The machinery landed (engineered + fixture-verified)

- **`ops/src/ops/release_rehearsal.py`** — the rehearsal runner:
  `rehearsal_orders` emits the deterministic `sig.withdrawal-order/1`
  deny+reinstate pair; `assert_bounded_orders` holds the bound (entity-kind
  low-stakes targets only, ≤4, the `allow` twin exactly covering the deny's
  targets); `plan`/`blockers` resolve the pointers and every QUEUED reason
  read-only; `run` executes the four timed legs over the landed
  `verb_rollback`/`verb_withdraw` machinery and emits
  `sig.release-rehearsal/1` (per-leg `seconds`/`budget_s`/`within_budget`,
  pre/post pointer state, receipts) — to `--out` and appended under
  `registry/rehearsals/` on apply.
- **`sig-ops release-rehearsal {plan,orders,run}`** — the CLI surface;
  `--apply` exits 42 (`rehearsal-blocked`) on any unmet precondition so a
  queued leg can never be forced.
- **`ops/gcp/release-rehearsal.sh`** — the wrapper: `--check` prints the
  plan offline (no ADC, no network — verified this run); `--apply` carries
  the contract window guard (≥ 2026-11-13T12:00Z, weekday 14:00-20:00Z),
  `SIG_REHEARSAL_AUTHOR` + the two `SIG_REHEARSAL_GO`/`_AUTHORITY` record
  names + `SIG_REHEARSAL_ENTITY`, exiting 42 QUEUED before the ADC gate.
- **`tests/ops/test_release_rehearsal.py`** — 10 fixture tests: the
  deterministic bounded order pair, the plan's QUEUED blockers, the four
  timed legs over a two-release fixture registry (latest restored, `allow`
  lifts the deny append-only, `sig.release-rehearsal/1` + journal events),
  the honest partial record on a planted leg failure, CLI exit codes.

## The queued leg (0.5 run) — QUEUED under `D-P36.70-1`

Preconditions (none met here — recorded, never fabricated): P36.72b's
promote landed (`D-P36.72b-1`, the operator's HG-11 act at the GATE-G6
sitting) so a promoted release + rollback target exist; the operator's
`sig.operator-authority/1` go + takedown-authority records named for the
two verb slots; `SIG_RELEASE_REGISTRY` + ADC/`SIG_GCP_PROJECT` present;
inside the window (≥ 2026-11-13T12:00Z, weekday 14:00-20:00Z); the
low-stakes entity id(s) (≤4) chosen at the sitting — a non-Part-VIII
entity route on the promoted release.

```
ops/gcp/release-rehearsal.sh --apply
# → sig-ops release-rehearsal orders --entity <id> --out <state>/orders
# → sig-ops release-rehearsal run --registry $SIG_RELEASE_REGISTRY \
#     --deny-order …/rehearsal-deny.json --allow-order …/rehearsal-allow.json \
#     --go <name> --authority <name> --apply --out <record>
# legs: rollback-to-prior → rollback-restore → withdraw-deny → withdraw-reinstate
```

Restore point: `rollback-restore` re-points `latest` at the promoted
release (the prior release stays published); the withdrawal's reinstate is
a NEW `allow` disposition — the byte-level restore is the next release's
staging (the append-only contract, §8.3). The measured timings replace G3
§5.2's `[est]` figures (§8.1 ≤10 min rollback; SIG-REL-D13 ≤15 min
every-alias withdrawal).

## The conditional Class R promotion — recorded, never re-decided

The go is valid now but expires at the GATE-G6 sitting — the same sitting
that lands the rehearsal precondition — so the contract's own fallback
(Class S) is the recorded posture. Were an unexpected still-valid go plus
a Class-R-eligible candidate to exist at the re-run, the promotion runs
through the landed P35.60 classifier (`release classify` →
`release promote --class class_r --approval <standing-go-name>`) — the
record would quote GATE-G5's renewal verbatim, never presume it. No such
candidate or validity exists in this run; nothing is claimed.

## Re-run prompt (verbatim — OM-19)

```
implement-spec spec=docs/tickets/417_P36.70__second-release-acceptance.md live_verification=true
```

## Named limits (recorded, never silently skipped)

- **No promoted release, no staged candidate, no authority records, no
  hosted env** in this run — the fixture registry stands in; nothing is
  fabricated.
- **The low-stakes record is chosen at the sitting** — the packet stages
  the machinery + bound, never a fabricated target.
- **P-mode verify + origin probes** ride the promoted release's own verify
  leg; `--origin` is plumbed for the sitting.
- **Rolls land `prepared_not_executed`** unless the sitting passes
  `--execute-rolls` with digest-pinned images.
