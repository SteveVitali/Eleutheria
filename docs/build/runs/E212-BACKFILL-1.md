<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Run ledger — E2-12-BACKFILL-1 — the second hosted attribution-corrections backfill (D-E2-12-BACKFILL), all 34 source/record pairs — **DONE**

- **Obligation:** `D-E2-12-BACKFILL` (`docs/tickets/DEFERRALS.md`, kind V,
  registered by this leg for the ad-hoc go) —
  `sig-db attribution-corrections --dsn <sig-pg>
  --corrections docs/build/reports/rights/e212_attribution_corrections.json
  --apply` on the production claim spine (INSERT-only `rights_record` +
  `rights_decision` rows; never UPDATE/DELETE).
- **Authorization — the operator-signed go** on
  `r11/P38.3c-round11-integration-plan-2`: LEDGER GATE DECISIONS row
  `2026-11-25T03:30Z | E2-12-BACKFILL` (commit `c3cec493`, `git
  verify-commit` → `Good "git" signature … ED25519`,
  `go-verify-c3cec493.txt`; "All 34 pairs" verbatim selection,
  AskUserQuestion 2026-11-25). The go authorises a D-P34.21a-class leg
  under the same preconditions (`live:P34.3`, AR-2 backup + pre-state,
  probe ≤ 24 h, outside the never-band) applying a NEW corrections
  artifact covering all 34 source/record pairs — INSERT-only
  `rights_record` rows carrying the declared `sources.toml`
  attribution_text/terms_url + per-source `rights_decision` redirects;
  the 3 `D-P34.21a-2` under-review sources included at their DECLARED
  attribution under the prior's unchanged licence; read-back =
  `assert_attribution_rows` green on a pre-flight probe + 0
  attribution-required claims with empty effective attribution among
  corrected pairs.
- **Harness:** devin-desktop/swe-2-high/subagent (OM-19 leg-runner)
- **Branch / worktree:** `r11/ops-e212-backfill` in dedicated worktree
  `/tmp/sig-e212-backfill`; code+artifact commit `393c2c12`; register +
  e0 anchor commit `2028d82c`.
- **Environment:** `SIG_GCP_PROJECT=zeta-medley-508121-u7`
  (`SIG_GCP_REGION=us-central1`); ADC `14stevevitali@gmail.com`;
  `cloud-sql-proxy zeta-medley-508121-u7:us-central1:sig-pg --address
  127.0.0.1 --port 5433` (up for the whole leg); `sig-pg-password`
  pulled from Secret Manager into env only — never argv, never a file.
- **Evidence:** `docs/build/logs/e212-backfill-1/` (the gitignored
  subtree): `date-u-start.txt`, `date-u-window.txt`, `proxy.log`,
  `db-connect.txt`, `derive-map.txt`, `pairs.json`,
  `dry-run-rehearsal.json`, `prestate_capture.py`, `readback.py`,
  `attribution-probe3.py`, `probe3-pre.txt`, `probe3-post.txt`,
  `go-verify-c3cec493.txt`, `protect-verify.txt`, `backups-list.txt`,
  `backups-list-post.txt`, `probe-run.json`, `prestate.json`,
  `prestate-err.txt`, `dry-run.json`, `dry-run-err.txt`, `apply.json`,
  `apply-exit.txt`, `apply-err.txt`, `readback.json`, `readback-err.txt`,
  `apply2.json`, `apply2-err.txt`, `poststate.json`.

## The artifact — what was applied and why this leg needed a writer extension

`docs/build/reports/rights/e212_attribution_corrections.json` —
`sig.attribution-corrections/1`, 34 correction rows, sha256
`33031308f5f010f999876cc1d57ccfd5fc3fdcef37ac00d6df930b6a89dc7a0b`.
Licence counter: 29 `LicenseRef-OperatorAccepted-DBRight` (the
`camreg_und_*`), 4 `LicenseRef-PublicRecord-FactualCompilation`
(`camreg_us_ny_001/002`, `dot_511_ky`, `dot_511_ut`), 1
`LicenseRef-StAlbert-ODL-1.0` (`camreg_stalbert_ab`). Each row carries
`prior_rights_ids` naming the defective records
(`01a0b868-dca5-7e8b`, `01a0b868-776e-72ca`, `01a0b98a-c001-7a19`) —
attribution-fill on the same resolved licence, never a licence change.

**The suppressed-source mechanism (why `rights_corrections.py` was
extended, commit `393c2c12`).** `rights_decision` redirects join on the
*recorded* `ea.source_id`/`claim_source.source_id`; the 31
`camreg_und_*`/`camreg_us_ny_*` sources in scope are ADR-178 public
re-keys whose recorded handles are retired in the spine. A decision
keyed on the public alias joins nothing — the reason live-3's artifact
never touched the suppressed sources. The extension adds an optional
`source_id_digests` field (`sha256:<64 hex>` of the retired id); the
writer resolves the recorded spine ids by digest over
`evidence_artifact`/`source_registry`/`rights_decision`
(`_spine_source_ids`) and keys each decision on the resolved recorded
id. Priors are classified per pair — an `out_of_scope` kind reports
priors reachable from a source but not listed for correction instead of
correcting them. Reports emit digests, never handles. Tests:
`tests/db/test_attribution_corrections.py` (suppressed-source keying,
digest validation); `tests/exports/test_p34_21b_attribution_corrections.py`
14 passed; `ruff`/`mypy` clean.

## Preconditions (all recorded at leg time)

| # | precondition | result | evidence |
|---|---|---|---|
| 1 | `date -u` outside 03:00–06:30Z never-band + no AR-3 freeze | **met** — apply ran 06:36–06:37Z | `date-u-window.txt` (06:31:08Z) |
| 2 | `live:P34.3` data protection live — `protect.sh --verify` | **met** — 11 OK, 0 DRIFT at 06:31:11Z | `protect-verify.txt` |
| 3 | AR-2 on-demand backup SUCCESSFUL + pre-state captured | **met** — ON_DEMAND `1795588277489` SUCCESSFUL 06:31:17Z; prestate 06:33:05Z | `backups-list.txt`, `prestate.json` |
| 4 | `sig.probe-run/1` record ≤ 24 h | **met** — `generated_at=2026-11-25T06:32:57Z`, `overall=partial` (absence leg 8/8 404s, `failed: 0`) | `probe-run.json` |

## Execution

- **Dry run (rehearsal, ~03:40Z):** `sources: 34,
  decisions_would_write: 34, claims_affected: 104,807, refused: []`;
  prior kinds `{correct: 34, out_of_scope: 3}` (`dry-run-rehearsal.json`).
- **Official dry run (06:34Z):** identical — 34 sources, 34 decisions,
  104,807 claims, 0 refused; out-of-scope = `dot_511_ky`'s two `CC0-1.0`
  priors (6,351 + 2,959 claims) and `dot_511_ut`'s one (1,184 claims) —
  CC0 carries no attribution requirement, correctly untouched
  (`dry-run.json`).
- **`--apply` (06:36–06:37Z, exit 0):** `decisions_inserted: 34`,
  `claims_affected: 104,807`, 0 refused; 34 unique `rights_record`s
  referenced (`apply.json`). Table deltas vs prestate:
  `rights_decision` +34, `rights_record` +3 — the other 31 corrected
  records already existed (minted 2026-11-24 ~23:11Z by the earlier
  attempt whose decisions keyed on public ids and joined nothing —
  exactly the defect this leg's digest resolution fixes); only the 3
  under-review sources needed new records (their declared-attribution
  variants). `n_tup_upd`/`n_tup_del` **+0 on all 8 spine tables**;
  sqitch 81→81 (`poststate.json`).
- **Second `--apply` (06:39Z):** `decisions_inserted: 0` — idempotent
  (`apply2.json`).

## Read-back (post-apply) — the go's verify contract

- **`assert_attribution_rows` replica (attribution-probe3.py):** E2-12
  gate verdict **0 violations** — every `(source, rights_record)`
  effective pair with `attribution_required` now carries non-empty
  attribution (was 34 violations pre-apply; `probe3-pre.txt` →
  `probe3-post.txt`).
- **0 empty effective attribution among corrected pairs:**
  `empty_effective_on_corrected_pairs = {}`; licence-blind
  `empty_attribution` over the corrected spine ids dropped 115,301 →
  10,494. The residual is exactly the recorded out-of-scope CC0
  priors — `dot_511_ky` 9,310 + `dot_511_ut` 1,184 — which require no
  attribution (`readback.json`).
- **0 wrong-upstream rows:** every corrected claim resolves to a record
  carrying its own source's declared attribution (`readback.json`,
  `wrong_attribution_after.total_on_corrected_set = 0`); per-source
  spot-checks resolve to the corrected spdx/attribution/terms_url for
  all 34 sources.
- **INSERT-only held:** `n_tup_upd`/`n_tup_del` +0 everywhere; no
  UPDATE/DELETE issued; sqitch head unchanged.

## Obligation closeout

- `D-E2-12-BACKFILL:e0` anchor appended in `2028d82c` (row registered
  OPEN by this leg — the go was ad-hoc with no register row).
- `D-E2-12-BACKFILL:e1` OPEN→DONE + DEFERRALS cell flip + this ledger +
  LEDGER PHASE LOG row in the closeout commit.
- **Follow-on:** the E2-12 blocker on OPS-EXPORT-GCE-3 is cleared —
  `assert_attribution_rows` will now pass; the GCE export leg can be
  re-dispatched (`D-P37.65a-1` chain).
