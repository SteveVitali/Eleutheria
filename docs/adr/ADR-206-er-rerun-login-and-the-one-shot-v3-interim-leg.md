# ADR-206 — The sig_materialize_login credential and the one-shot v3-interim ER re-run leg (P34.45)

- Date: 2026-10-09
- Status: accepted
- Ticket: P34.45 (Round 11 / P34, row 257 — the honest-evaluation posture;
  the OM-20 pre-authorised production mutation)
- Base: `r11/P34.44b-quality-baseline-run-and-nightly-probe`
- Related: ADR-153 (the "derivation, not identity" posture the re-run
  applies — inferential tiers review-only until an independent human B5
  evaluation exists), ADR-105 (the camera-site measured auto-write gate the
  ruleset amends), ADR-202 (the execution host and DB-login pattern this
  leg extends to its first write-capable credential), ADR-201 (the
  conditioned-grant pattern), ADR-111 (digest-pinned workload images),
  ADR-123 (one append-only execution record per run), HG-09 (secrets are
  environment/Secret Manager only), OM-20 (S5-3 "Both + list + P34.45" —
  the re-run is pre-authorised; expires GATE-G4, voided by a red probe, a
  failed restore point, or a contradicting production read), P34.46 (the
  API roll whose basis label must be live before the re-run mutates
  answers)

## Context

P34.45 makes every inferential camera-site tier review-only under ruleset
v3-interim (ADR-153). The engineering lands it; the hosted spine still
carries rows decided under v2 — auto-written inferential edges no
independent person has ever evaluated. Applying the new posture means ONE
append-only ER re-run on hosted (OM-20's named mutation): a fresh
`camera_site_run` whose ruleset_version is `3-interim`, new
`camera_site_match` decision rows demoting inferential dispositions to
`proposed` with the explicit `no_certifying_evaluation` reason, and the
review queue items they enqueue. No `UPDATE`, no `DELETE` — the prior
run's rows stay as history.

That run needs a database credential that can *write* — the first
write-capable login the P34.43 host has carried (`sig_audit` is read-only
by session default; `sig_recovery_login` is L2's and gated `live:P34.46`).
Three questions had non-obvious answers:

1. **How write-capable is "capable enough".** The materializer role
   `sig_materialize` (Round 6) already holds exactly the surface: INSERT on
   the materialized tables — `camera_site_run`, `camera_site_match`,
   `camera_site_execution`, `review_item` — with UPDATE/DELETE/TRUNCATE
   revoked group-wide and no claim-spine write. A login holding membership
   in that group needs zero new grants: the write surface is declared once,
   never duplicated credential by credential.
2. **How the once-ness is enforced.** "One permitted re-run" cannot be an
   honour-system promise in the runbook. The schema makes it checkable:
   `camera_site_run.ruleset_version` records the ruleset every run ran
   under, so a second attempt sees the `3-interim` run_key already present
   and queues (exit 42) — a further re-run needs a new operator decision,
   not a flag.
3. **What "after the API roll" means operationally.** A-20's disclosure
   promise is that a live-API answer changing under the new posture is
   disclosed by the basis label — so the re-run must not run while the API
   still serves the pre-roll image. The check is a *comparison*, not a
   document: the leg resolves `SIG_ER_RERUN_IMAGE` to a digest and refuses
   (exit 42) unless `sig-api`'s deployed image is that same digest — the
   ER run then rides the identical image the API serves, so the posture
   the run applies and the labels the API discloses are the same commit.

## Decision

**A distinct LOGIN member of the existing NOLOGIN group, never new
grants.** The `er_rerun_login` sqitch change creates
`sig_materialize_login LOGIN` (NOBYPASSRLS, NOSUPERUSER, NOCREATEDB,
NOCREATEROLE, CONNECTION LIMIT 2, a guarded CREATE so the deploy converges
a spine the leg ran early on) and grants it `sig_materialize` — nothing
else. Its DIRECT memberships are exactly `{sig_materialize}` (the verify
asserts it). It deliberately carries **no** `default_transaction_read_only`
session default — unlike `sig_audit`: it is the one write-capable login,
and honesty requires the grants, not a session flag, to bound it. INSERT is
append-only by grant; `db_logins.py`'s refused-write probes (UPDATE/DELETE/
TRUNCATE on the camera tables, a claim-spine write, an `ingest_run` insert)
are first-class assertions in `sig-ops db-login verify`.

**The credential lives like every other DB credential.** Password generated
→ `sig-er-rerun-password` in Secret Manager (only accessor: the exec host's
`sig-quality-probe-rt` runtime identity) → `ALTER ROLE … PASSWORD` with the
value in the environment only (HG-09, ADR-202). The exec host declaration
adds the `SIG_ER_RERUN_PASSWORD` → `sig-er-rerun-password` secret_env
binding; `ops/iam_identities.toml` adds the consumer row.

**One leg script, `ops/gcp/er-rerun.sh`, with the standard guard stack.**
`--check` is plan-only (no ADC, no network). Every mutating action —
`backup`, `login`, `run` — requires (a) the AR-3/AR-2 window (≥
`SIG_ER_RERUN_EARLIEST`, never 03:00–06:30Z, never inside the day-6→13
batch window), (b) `SIG_ER_RERUN_AUTHOR`, the recorded operator id for
*this* apply (OM-20's pre-authorisation is a scope, not a standing
credential), and (c) every live edge: the exec SA, the secret, the
v3-interim image digest actually deployed on `sig-api`, and — before the
first catalog statement — an on-demand Cloud SQL backup read back as
SUCCESSFUL (AR-2). Any missing edge exits **42** (queued), never a partial
apply. `run` additionally refuses (exit 42) when a
`ruleset_version='3-interim'` `camera_site_run` already exists — the
exactly-once bound the schema makes enforceable. The run itself is one
`sig-exec-er-rerun-<stamp>` one-off on the P34.43 host executing
`python -m resolution camera-sites --role sig_materialize_login` over the
Cloud SQL socket; pre/post state captures (`pre/er-state.json`,
`post/er-state.json`) give the before/after tier-disposition diff the
ticket requires as evidence. `rollback` is guidance only — append-only
means forward-only (re-run under the prior ruleset digest, or PITR to the
AR-2 backup); nothing is ever deleted.

## Consequences

- The hosted camera-site ER history becomes honestly layered: v2's
  auto-written inferential rows remain as the recorded decisions of that
  ruleset; v3-interim's run demotes the same pairs to `proposed` —
  supersession by newer rows, never mutation of old ones.
- A second v3-interim run is structurally a no-op *and* a leg refusal: the
  resolver's `ON CONFLICT` is +0 regardless, and the leg queues before it
  gets there.
- The leg cannot run while the API serves the pre-roll image — the
  disclosure promise (A-20) is enforced by comparison, not documented by
  hope.
- The write-capable login's blast radius is the group's: appending ER
  decision rows and review items. It cannot mutate, cannot touch the claim
  spine, cannot read outside the group's read surface, and its credential
  reaches only the exec host's runtime identity.

## Revisit trigger

Revisit when (a) an independent human B5 evaluation exists and a certified
inferential tier can legitimately auto-write again — the v3-interim posture
and this leg's demotion semantics were designed for its absence; (b) a
second ER re-run under v3-interim is ever wanted — that is a new operator
decision and a new leg, not a flag on this one; (c) `sig_materialize`'s
grant surface widens — this login inherits it immediately, so the group
stays the single place the write surface is declared; or (d) GATE-G4
passes without the re-run executing — OM-20's pre-authorisation expires
there and the leg reverts to engineering-only state.
