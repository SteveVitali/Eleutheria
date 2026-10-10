# Spend ledger — SIG-OPS-009 (P34.5)

Cost truth for the hosted SIG deployment, in one committed place. The ledger
answers the question the $300/month infrastructure ceiling polices: *what does
the deployment actually cost, measured, next to what it is estimated to cost?*

- **Ledger rows:** [`spend_ledger.csv`](spend_ledger.csv) — one row per
  (month, surface, provider, category).
- **Agent usage:** [`agent_usage.csv`](agent_usage.csv) — one row per wave /
  reporting event. Usage is **reported, never dollar-capped** (OD-02/OD-03/
  OD-26); it is kept in its own file so it can never be summed into the
  infrastructure total the ceiling watches.
- **Production control:** `ops/gcp/cost-guard.sh` (budget + billing export
  dataset + test-threshold lifecycle), deferred rows `D-P34.5-*` in
  `docs/tickets/DEFERRALS.md`.

## Labels

Every row carries exactly one `source_label`:

| label | meaning |
|---|---|
| `measured` | read from the BigQuery billing export / a provider invoice — an observed figure with an `evidence` pointer |
| `operator-reported` | reported by the operator from a provider console/receipt — trusted, not independently re-derived |
| `estimate` | inference or list-price projection — *never* a measured amount; the row's note names what supersedes it |
| `pending` | a placeholder row for a measured/operator-reported figure that has not arrived yet (e.g. the export's first month) — `amount_usd` is empty |

A `pending` row is removed (replaced by its real row) when the figure lands;
it is never read as zero. An `estimate` row is superseded, not edited, when the
measured figure lands — the estimate stays visible so the projection's accuracy
is auditable.

## Rules

1. **Never fabricate an amount.** If a figure is not yet read or reported, the
   row is `pending` with an empty `amount_usd`.
2. **Infrastructure only under the ceiling.** The $300/month budget
   (`ops/gcp/cost-guard.sh`, display name `SIG infra ceiling — 300 USD per
   month (U-008)`) sums GCP lines only. Cloudflare/R2, registrar and domain
   rows are *billed outside the cloud account*: they appear in the same
   monthly ledger for completeness but are marked `outside-cloud-account` in
   `note` and are not part of the ceiling comparison.
3. **Agent usage is separate.** ACU/session/token figures live in
   `agent_usage.csv` and are never currency. A usage-limit event pauses the
   round (digest + stop, per the LEDGER pause list) — that is an operational
   pause, not a spend line.
4. **Monthly cadence.** Once the billing export holds rows, each month gets
   its measured GCP rows (per service) beside the non-GCP rows. The first
   monthly report is a queued live leg (`D-P34.5-3`) until the export link
   lands.

## Monthly report procedure (when the export has rows)

```bash
# rows in the export for the month (the leg's verification query):
bq query --nouse_legacy_sql \
 'SELECT service.description AS service,
         ROUND(SUM(cost), 2) AS usd,
         currency
    FROM `<project>.sig_billing_export.gcp_billing_export_v1_<billing-acct>`
   WHERE invoice.month = "<YYYYMM>"
   GROUP BY service, currency
   ORDER BY usd DESC'
```

Then append the month's `measured` rows to `spend_ledger.csv`, add the
operator-reported non-GCP rows for that month, and append the wave's usage
row to `agent_usage.csv` if one was reported. If `invoice.month` has no rows
for the current month yet (the export lags), the month stays `pending` — the
report is not owed until data exists.

## Ceiling status

| item | state |
|---|---|
| ceiling | USD 300/month infrastructure (U-008, A-2a) |
| R2 mirror ceiling | USD 50/month hard cap (P35.5 / SIG-TRANSP-019, D-J3-4/A-3) — `ops/config.toml` `[egress] hard_ceiling_usd`; warns at 80%, alarms at 100% via `sig-ops egress-report --usage-usd --alert`; the kill switch is the operator's documented step ([R2_MIRROR_RUNBOOK.md](../R2_MIRROR_RUNBOOK.md)) |
| alert thresholds | 50 / 90 / 100 % of CURRENT_SPEND → billing IAM recipients + operator e-mail channel |
| budget | live 2026-10-02 — see `ops/gcp/cost-guard.sh --verify` output |
| test threshold | `D-P34.5-1` (fires → operator confirms → `testbudget-delete --fired-confirmed …`) |
| billing export | dataset `sig_billing_export` live; the console link is OP-12 (`D-P34.5-2`) |
| first monthly report | `D-P34.5-3` — queued until the export holds rows |
