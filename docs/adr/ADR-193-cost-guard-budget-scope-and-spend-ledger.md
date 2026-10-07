# ADR-193 — Cost guard: project-scoped ceiling budget, test-threshold lifecycle, spend ledger conventions (P34.5)

- Date: 2026-10-02
- Status: accepted (the apply legs ran live 2026-10-02; the test-budget
  fire→delete, the OP-12 export link and the first monthly report are owed
  — D-P34.5-1/-2/-3)
- Ticket: P34.5 (Round 11 / P34, row 206; requirement SIG-OPS-009; answers
  S5-3 OM-20 + A-2)
- Base: `r11/P34.4-alerts-that-reach-a-human` (Round-11 chain)

## Context

P34.5 turns the operator's $300/month infrastructure ceiling into an alarmed,
measured control: a Cloud Billing budget, a temporary test-threshold budget
that proves the alert path end-to-end, a BigQuery billing-export dataset, and
a committed monthly spend ledger. Three design questions needed a recorded
answer:

1. **What does the budget sum?** The billing account serves projects beyond
   SIG (the account's other projects are not SIG infrastructure). A
   whole-account budget would fire on non-SIG spend and would contradict
   U-008's "spend above $300/mo" pause, which is defined on SIG
   infrastructure cost.
2. **How does the test threshold prove delivery without over-firing?** The
   contract wants a temporary threshold "set low enough to fire", the firing
   observed, and the test budget deleted — i.e. it proves the alert path the
   way P34.4's synthetic `SIG-ALERT` proved the notification path.
3. **What counts as a ledger row?** SIG-OPS-009 requires measured GCP lines
   beside non-GCP lines (Cloudflare/R2, registrar, domains) and the per-wave
   agent-usage report, each labelled. Before the export link lands there is
   *no* measured figure, and fabricating one is forbidden by the contract.

## Decision

**Budget scope**: the ceiling budget filters on `projects/$SIG_GCP_PROJECT`
(`--filter-projects`). The ceiling is SIG-infrastructure-only (U-008, A-2a);
spend on unrelated projects in the same billing account is out of scope for
the SIG pause rule and must not trigger it. Recipients: billing-account IAM
defaults stay enabled (never `--disable-default-iam-recipients`) plus the
committed operator e-mail channel resolved live by displayName — the address
is never committed (ADR-192's `<placeholder>` rule).

**Test threshold**: a second budget at `$0.01` with a single 100 %
(CURRENT_SPEND) threshold on the same project scope. Month-to-date spend is
already non-zero, so it fires at the next budget evaluation and exercises the
identical delivery path the 50/90/100 rules use. It is deleted only *after*
its firing is confirmed — `ops/gcp/cost-guard.sh`'s `testbudget-delete` leg
refuses (exit 42) without `--fired-confirmed "<evidence>"`, so the ordering
is enforced by the tool, not the doc.

**Ledger conventions** (`docs/build/reports/spend/`): `spend_ledger.csv`
rows are `(month, surface, provider, category, amount_usd, source_label,
evidence, note)`; `agent_usage.csv` holds per-wave usage (sessions / ACU /
tokens) separately because usage is reported, never dollar-capped
(OD-02/OD-03/OD-26), and never enters the infrastructure total. The label
vocabulary is `measured` (read from the export/invoice), `operator-reported`,
`estimate` (inference/list-price — superseded, never edited, when the
measured figure lands), and `pending` (the honest placeholder for a figure
that has not arrived — an empty `amount_usd`, never read as zero). Non-GCP
rows are marked `outside-cloud-account`: they join the monthly ledger for
completeness but are outside the ceiling's project-scoped sum.

**Billing export**: the dataset `sig_billing_export` is IaC-created; the
export *link* has no public API path and needs billing-admin, so it is an
operator console step (OP-12, D-P34.5-2). The verification query and the
standard-export table name (`gcp_billing_export_v1_<billing-account>`) are
documented so the first monthly report leg is mechanical once rows land.

## Consequences

- The project-scoped budget means *account-level* non-SIG spend can exceed
  $300 without firing SIG alerts — correct per U-008 but worth remembering
  when reading billing-account totals.
- The test budget's e-mail goes to billing IAM recipients (and the operator
  channel when resolvable); until D-P34.5-1's human leg runs, the alert path
  is engineering-verified, not human-confirmed.
- The ledger is honest by construction: before the export link lands, the
  month shows `pending`/`estimate` rows only — nothing claims a measured
  figure it does not have.
- P35.2+ inherits the alert plumbing; the billing export's first measured
  month closes the last "estimate" claim in the cost model.

## Revisit trigger

Revisit if a second project joins the SIG deployment (the filter must become
a list — the ceiling covers *SIG infrastructure*, however many projects that
is); if the account's currency or budget scope changes; if GCP adds a public
export-link API (the OP-12 console step then becomes scriptable); or if a
usage-limit event fires (the round pauses per the LEDGER pause list and the
agent-usage section of the ledger gains the event row).
