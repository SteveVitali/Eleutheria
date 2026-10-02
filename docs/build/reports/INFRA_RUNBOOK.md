<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# INFRA_RUNBOOK — running the P21.5 infrastructure (deposits, store, tiles, mirrors, degraded mode)

*P21.5, ADR-067. How to run each of deliverables 1–6 with the exact env names. Every
credentialed integration is **dry-run / sandbox by default** and reports
`gate pending: HG-07` when its credential is absent — it never fabricates success (§3.1).*

Prerequisite for the export-based commands: a built release, e.g.
`uv run sig-exports build --jurisdiction okc --out exports/out/okc`.

## 1. Zenodo deposit (SIG-EXPORT-002)

| goal | command | env |
|---|---|---|
| offline dry-run (default) | `uv run sig-exports deposit --in exports/out/okc` | — |
| sandbox dry-run (10.5072 prefix, offline) | `uv run sig-exports deposit --in exports/out/okc --sandbox --dry-run` | — |
| **real sandbox deposit** | `uv run sig-exports deposit --in exports/out/okc --sandbox` | `SIG_ZENODO_SANDBOX_TOKEN` |
| production deposit (operator only) | `uv run sig-exports deposit --in exports/out/okc` *(swap in a production token)* | production Zenodo token |

- Without `SIG_ZENODO_SANDBOX_TOKEN`, `--sandbox` exits **4** (`gate pending: HG-07`) and
  writes nothing. Every deposit appends a row to `docs/build/reports/DEPOSITS.md` with its
  `environment` (RISK-P21-08). The deposit uploads the release bundle + `manifest.json` +
  `digests.json` + `CITATION.cff` + `sbom.cdx.json` and carries the per-compartment licence.

## 2. Object store + CDN + egress alarm + torrent (SIG-EXPORT-008/009)

| goal | command | env |
|---|---|---|
| push a release to the store | `uv run sig-exports push --in exports/out/okc --store cloudflare-r2:sig-bulk` | `SIG_OBJECT_STORE_URL`, `SIG_OBJECT_STORE_KEY`, `SIG_OBJECT_STORE_SECRET` (boto3-standard) |
| egress budget report | `uv run sig-ops egress-report` (add `--usage-gb N` when a usage figure is known) | — (usage API when available) |
| produce a `.torrent` | `uv run sig-exports torrent --in exports/out/okc/sig_graph/claims.parquet` | — |

- Objects are uploaded under **content-hash keys** with an immutable `Cache-Control`
  (append-only; never overwritten). A **metered-egress** provider fails the build
  (SIG-EXPORT-008). Store/CDN config template: `ops/config.toml` (ADR-067 picks Cloudflare
  R2; AWS S3 + CloudFront per ADR-015 is the documented alternative). `egress-report`
  reports `gate pending: HG-07` with the documented threshold when no live usage is
  available, and exits **5** on a real breach (RISK-P21-09).

## 3. Tile generation (LD-F07/LD-H08, §40)

| goal | command |
|---|---|
| render GeoJSON → PMTiles | `uv run sig-exports tiles --in exports/out/okc/osm_physical/devices.geojson --out /tmp/sig.pmtiles` |

- Uses **tippecanoe** if on `PATH`, else the pure-Python fallback (small extents). The
  ODbL licence + OSM attribution are preserved in the archive metadata (ADR-048, §42). The
  jurisdiction build renders `web/tiles/sig-infrastructure.pmtiles`; the web build in
  `export` mode copies it into `/tiles/` (consumed by the map's `/map/style.json` source).
  **A1 is ticked — the served map is zero-JS; no MapLibre island.**

## 4. Mirrors + Software Heritage (SIG-GOV-022/023/024)

| goal | command | env |
|---|---|---|
| build a SWH save request (print only) | `uv run sig-ops swh-save --repo-url https://github.com/SteveVitali/Eleutheria` | — |
| actually submit to SWH | `uv run sig-ops swh-save --repo-url <url> --now` | `SIG_SWH_TOKEN` (optional; not needed for public repos) |

- Mirror manifest: `ops/mirrors.toml`. Succession/rebuild guide: `docs/build/SUCCESSION.md`.
  This run leaves SWH **untriggered** (`gate pending`: no public repo URL saved).

## 5. Degraded-but-alive mode + keepalive (SIG-GOV-021, RISK-P0-12)

| goal | command | env |
|---|---|---|
| build the fully static site (no API) | `uv run sig-ops degraded --data-source fixtures` | — |
| build from an export snapshot | `uv run sig-ops degraded --data-source export --export-dir exports/out/okc` | — |
| the monthly keepalive | `.github/workflows/keepalive.yml` (cron `0 7 1 * *` + manual) | — |

- `sig-ops degraded` **fails loudly** if it cannot rebuild. The keepalive runs exactly this
  command monthly so a dormant scheduler is caught by a red build. Cost: **$0 beyond the
  static host**.

## Gate status (this run)

- **HG-07 (accounts): NO.** Real sandbox deposit, live object-store push, and triggered
  SWH save are `gate pending: HG-07`. Dry-run/sandbox-stub, tiles, `.torrent`, degraded
  mode, and keepalive are done for real.
- **HG-12 (budget): zero-cost.** CDN/object-store config are templates only.
- **A1: ticked.** The zero-JS static map stays; no MapLibre island; `/map/` script budget
  unchanged.

## 6. Production data protection (P34.3; SIG-OPS-002, SIG-STORE-048)

`ops/gcp/protect.sh` owns the five pre-authorised mutations (S5-3 11A list,
expires GATE-G4). It is dry-run by default; every `--apply` leg is idempotent
(live-read → `SKIP`) and window-gated (never 03:00–10:00Z; `sig-pg` legs also
never inside an AR-3 window or while `sig-materialize` runs). The AR-2 restore
point — an on-demand `sig-pg` backup verified `SUCCESSFUL` — runs before any
instance patch.

| goal | command |
|---|---|
| print the plan (no ADC, no network) | `ops/gcp/protect.sh --check` (bare, or per leg: `prestate\|backup\|instance\|buckets\|iam`) |
| capture pre-state JSON + sha256 (read-only, any time) | `ops/gcp/protect.sh --apply prestate` |
| run the live leg (order: prestate → AR-2 backup → three `sig-pg` patches → bucket versioning+lifecycle → `sig-web` IAM → post-state + `--verify` + site checks) | `ops/gcp/protect.sh --apply` |
| verify the outcome (live reads) | `ops/gcp/protect.sh --verify` |
| verify offline against recorded JSON | `ops/gcp/protect.sh --verify --from-state <state-dir>` |

Stop rules (automatic): a non-`UPDATE` operation, a restart, an `api /health`
failure, or a site route failing after QA-7 rolls that action back inline and
exits non-zero — the leg never continues past a red step.

Rollback per mutation (the script prints and runs these on a stop-rule trip;
run manually if an interruption left a mid-apply state):

| mutation | rollback |
|---|---|
| deletion protection + retain-backups | `gcloud sql instances patch sig-pg --no-deletion-protection --no-retain-backups-on-delete` |
| maintenance window SUN 09:00Z | `gcloud sql instances patch sig-pg --maintenance-window-any` |
| autoresize cap 40 GB | `gcloud sql instances patch sig-pg --storage-auto-increase-limit=0` |
| bucket versioning + lifecycle (`sig-restricted`, `sig-public`, `sig-web`) | `gcloud storage buckets update gs://<bucket> --no-versioning` + re-apply the captured prior lifecycle file (pre-state: none — `--lifecycle-file` of an empty rule set clears it; noncurrent versions already written are kept) |
| `allUsers` on `sig-web` | `gcloud storage buckets add-iam-policy-binding gs://<project>-sig-web --member=allUsers --role=roles/storage.objectViewer` |

QA-7 verification after the IAM change: `GET /` and `/map/` → 200 and
`GET /tiles/sig_graph-sites.pmtiles` (Range) → 206 on both
`https://surveillancegraph.org` and the `sig-web` `*.run.app` URL, and the
direct bucket URL `https://storage.googleapis.com/<project>-sig-web/index.html`
→ 403/404. Captured states land in the gitignored `docs/build/logs/protect/`.

## 7. Alerts that reach a human (P34.4; SIG-OPS-006 partial, QA-3/4/5, QA-8 disable)

`ops/gcp/alerts.sh` owns the five pre-authorised mutations (S5-3 11A list,
expires GATE-G4) over the committed alert set (`ops/monitoring/*.json`,
ADR-192). Same contract as `protect.sh`: dry-run by default, idempotent,
window-gated (never 03:00–10:00Z; the `sig-probe` image roll additionally
never inside an AR-3 window).

| goal | command |
|---|---|
| print the plan (no ADC, no network) | `ops/gcp/alerts.sh --check` (bare, or per leg: `prestate\|monitoring\|reingest\|proberoll\|delivery\|jobfail`) |
| capture pre-state JSON + sha256 (read-only, any time) | `ops/gcp/alerts.sh --apply prestate` |
| leg A — create the TLS-expiry + SIG-ALERT policies, disable `reingest.yml`, build+roll `sig-probe` at HEAD, run the delivery test, post-state `--verify` | `ops/gcp/alerts.sh --apply all` |
| leg B — extend the failed-job policy to `sig-probe` (self-gates: exit 42 while the re-roll's latest sweep is not green) | `ops/gcp/alerts.sh --apply jobfail` |
| verify the outcome (live reads) | `ops/gcp/alerts.sh --verify` |
| verify offline against recorded JSON | `ops/gcp/alerts.sh --verify --from-state <state-dir>` |
| diff the committed defs alone | `uv run sig-ops monitoring-defs verify --live` (or `--from-state <dir>`) |

Rollback per mutation (printed by the script; run manually if an interruption
left a mid-apply state):

| mutation | rollback |
|---|---|
| create a new alert policy (TLS-expiry / SIG-ALERT log) | `gcloud alpha monitoring policies delete <new id> --project <p>` |
| extend the failed-job policy to `sig-probe` + rate limit | `gcloud alpha monitoring policies update 7285515107319155929 --policy-from-file=<apply-dir>/policy.7285515107319155929.prior.rendered.json` (the captured prior definition) |
| `sig-probe` image roll | `uv run sig-ops roll-jobs --job sig-probe --image <before-digest> --apply` (the digest is in `<dir>/proberoll.record.json`) |
| `reingest.yml` disabled | `gh workflow enable reingest.yml` (+ restore the `schedule:` block from git history if ever wanted — it stayed `workflow_dispatch`-only) |

Evidence lands in the gitignored `docs/build/logs/alerts/` (pre/post captures
with sha256s). The delivery test POSTs a synthetic `SIG-ALERT` to the
`sig-alerts` webhook — its token is read from Secret Manager into memory only,
never printed or persisted — and reads `SIG-ALERT-RECEIVED` back from Cloud
Logging; the e-mail receipt itself is the operator's human check (`D-P34.4-2`).

## 8. Cost guard (P34.5; SIG-OPS-009)

The $300/month infrastructure ceiling is policed by a Cloud Billing **budget**
with e-mail alerts at 50/90/100 % of CURRENT_SPEND, scoped to the SIG project
(the billing account serves other projects — the ceiling covers SIG
infrastructure only). Measured costs land in BigQuery dataset
`sig_billing_export`; `docs/build/reports/spend/` is the committed monthly
ledger (measured / operator-reported / estimate / pending labels; agent usage
in `agent_usage.csv`, reported-never-capped).

| goal | command |
|---|---|
| print the plan (no ADC, no network) | `ops/gcp/cost-guard.sh --check` (bare, or per leg: `prestate\|budget\|testbudget\|testbudget-delete\|dataset\|exportcheck`) |
| capture pre-state JSON + sha256 (read-only, any time) | `ops/gcp/cost-guard.sh --apply prestate` |
| create the ceiling budget + the test budget + the export dataset, post-state + verify | `ops/gcp/cost-guard.sh --apply all` |
| delete the fired test budget (name-checked; refuses without `--fired-confirmed "<evidence>"`) | `ops/gcp/cost-guard.sh --apply testbudget-delete --fired-confirmed "<where the firing is recorded>"` |
| verify the outcome (live reads; read-only) | `ops/gcp/cost-guard.sh --verify` |
| verify offline against recorded JSON | `ops/gcp/cost-guard.sh --verify --from-state <state-dir>` |
| is the export delivering rows yet? | `ops/gcp/cost-guard.sh --apply exportcheck` |

The billing account is discovered live from the project's billing link (never
committed); `SIG_BILLING_ACCOUNT` overrides. The **billing-export link itself
is an operator console step (OP-12)** — Cloud Billing export has no public API
path: Billing → Billing export → BigQuery export → dataset `sig_billing_export`
on the SIG project. Rows land as `gcp_billing_export_v1_<billing-account-id>`
within ~a day; the first monthly report leg waits for them (`D-P34.5-3`).

Rollback per mutation (printed by the script):

| mutation | rollback |
|---|---|
| `billingbudgets.googleapis.com` enabled (prerequisite) | `gcloud services disable billingbudgets.googleapis.com --project <p> --force` |
| ceiling budget | `gcloud billing budgets delete <id> --billing-account <acct> --billing-project <p>` |
| test budget | same delete (the scripted leg is name-checked and requires the fired confirmation) |
| export dataset | `bq rm -r -d <p>:sig_billing_export` (disable the console export link first) |

Evidence lands in the gitignored `docs/build/logs/cost-guard/` (pre/post
captures with sha256s). The test budget's alert e-mail receipt is the
operator's human check (`D-P34.5-1`) — an agent never asserts receipt.

## 9. Restore drill at scale + restore point + logical export (P34.6; SIG-OPS-001, ADR-175)

Three scripts own the durable-restore half of the protection story.
`ops/gcp/restore-drill.sh` runs the at-scale drill: a point-in-time
`gcloud sql instances clone sig-pg → sig-pg-drill-<STAMP>` at `T = now−10 min`,
then append-only row-count parity at T on BOTH instances through the Cloud SQL
Auth Proxy (`sig-ops cloudsql-drill` — the `ops/src/ops/cloudsql_drill.py`
engine), a local `sig-api serve` smoke (`/health` + one `/v1/coverage` call),
measured RTO (clone submit → verified) and RPO (T − `max(lower(claim.sys_period))`),
and finally a **name-checked delete** that can only ever name
`sig-pg-drill(-b)?-<YYYYmmddtHHMMz>` — `sig-pg` is refused outright, as is any
hand-typed name outside that shape. The record lands as `record.json`
(`sig.restore-drill/1`) under the gitignored `docs/build/logs/restore-drill/`.

`ops/gcp/restore-point.sh` is the scripted AR-2: `sqlpoint` proves an on-demand
`sig-pg` backup `SUCCESSFUL` (the caller stops on a non-zero exit — the same
stop rule `protect.sh` enforces), and `bucketpoint gs://<src>…` mirrors named
objects into `gs://<project>-sig-restricted/restore-point/<STAMP>/` with a
written manifest (refuses any source outside this project's `sig-*` buckets).

`ops/gcp/logical-export.sh` owns the monthly `gcloud sql export sql` into
`gs://<project>-sig-backups/pg/monthly/<YYYY-MM>/` — the logical export that
survives the instance's lifecycle — plus the bucket lifecycle (Delete
`pg/monthly/*` at 100 d so the three newest monthly exports are always kept;
Delete `pg/adhoc/*` at 30 d) and the seed-dump relabel-by-copy into
`pg/seed-2026-09-15/` (originals never deleted). None of those three legs is on
the S5-3 list: every apply action other than `prestate` requires
`--go "<verbatim in-ticket go>"` and the queued rows live in
`docs/tickets/DEFERRALS.md` (`D-P34.6-2/3/4`).

| goal | command |
|---|---|
| print the drill plan (no ADC, no network) | `ops/gcp/restore-drill.sh --check` (bare, or per leg: `prestate\|clone\|counts\|smoke\|deleteclone\|fullrestore`) |
| capture pre-state JSON + sha256 (read-only, any time) | `ops/gcp/restore-drill.sh --apply prestate` |
| leg 1 — the whole PITR drill (prestate → clone → counts → smoke → deleteclone → poststate → verify) | `ops/gcp/restore-drill.sh --apply all` |
| run just the delete on a known drill instance (name-checked) | `ops/gcp/restore-drill.sh --apply deleteclone sig-pg-drill-<STAMP>` |
| leg 3 — the full-backup variant (QUEUED; needs `--go`) | `ops/gcp/restore-drill.sh --apply fullrestore --go "<verbatim go>"` |
| verify the drill outcome (live reads) | `ops/gcp/restore-drill.sh --verify` |
| verify offline against recorded JSON | `ops/gcp/restore-drill.sh --verify --from-state <dir>` |
| the AR-2 restore point on sig-pg alone | `ops/gcp/restore-point.sh --apply sqlpoint` |
| bucket mirror into sig-restricted | `ops/gcp/restore-point.sh --apply bucketpoint gs://<project>-sig-backups/pg/monthly/` |
| export/lifecycle/relabel plans + the queued applies | `ops/gcp/logical-export.sh --check` / `--apply <leg> --go "<verbatim go>"` |
| verify the export/lifecycle/relabel outcome | `ops/gcp/logical-export.sh --verify [--from-state <dir>]` |

Stop rules (automatic — the contract's voided-by): a non-SUCCESSFUL newest
backup voids the authorisation (exit 5); a red `sig-probe` sweep voids it
unless `--probe-note` records the judgment that the red is the known class; a
running `sig-materialize` refuses the clone (fail-closed on an unreadable
check); and inside 03:00–10:00Z every mutation refuses (exit 42). The clone leg
is NOT bound by AR-3 (it is a separate instance); the export leg IS (it loads
sig-pg's single vCPU). The `counts` leg needs `cloud-sql-proxy` on PATH and the
PG password in `SIG_PG_PASSWORD` (or Secret Manager `sig-pg-password`, read
into memory only — never a file, never argv).

The monthly cadence is declared as the `[[maintenance]]` row in
`ops/cadence.toml` (`pg-logical-export`, day 1 at 12:00 UTC — outside the band;
GCP cron's dom+dow OR semantics rule out "first Sunday"). P35.1a's scheduler of
record deploys the trigger; until then the row is the queue entry.
