<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# R2 mirror runbook — the zero-egress distribution host (P35.5, SIG-TRANSP-019)

The public release is served from a **Cloudflare R2 mirror** so download
egress cost cannot scale with traffic (D-J3-4/A-3: R2, $0 egress beyond the
free tier, $50/month hard ceiling). **GCS stays the origin of record** — the
mirror is a public copy, never the source of truth.

This runbook is the leg's operating document: prerequisites, the enable leg,
the egress ceiling + alerting, and the **kill switch**.

## 1. Prerequisites (all required before the live leg)

1. **OP-09 landed** — the operator's nameserver switch to Cloudflare
   (`docs/build/reports/DNS_CUTOVER_RUNBOOK.md`, obligation `D-P34.50-1`).

   ```bash
   dig +noall +answer surveillancegraph.org NS
   # expected: a Cloudflare pair (*.ns.cloudflare.com.), NOT *squarespacedns.com.
   ```

   While the answer names the Squarespace nameservers, OP-09 has NOT run and
   the leg MUST NOT execute.

2. **OM-20 authorisation** — the GATE-G4 operator-approved 11B list names
   P35.5 (it does — "Approve all 19", 2026-10-10); authorisation expires at
   the next GATE (GATE-G5).

3. **R2 credentials in the run shell, env only (HG-09)** — never written to a
   file: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` for the R2 S3 API (and
   `SIG_OBJECT_STORE_URL` = `https://<account>.r2.cloudflarestorage.com`).

4. **Pre-state capture** (`date -u`-stamped in the leg's run ledger): the
   committed `ops/mirrors.toml` state, the R2 bucket/CDN configuration export
   (empty before first enable), and the current egress/billing alert
   thresholds.

## 2. The enable leg (production write — AR-3/AR-2 weekday window)

1. Create the R2 bucket `sig-bulk` and bind the custom domain
   `files.surveillancegraph.org` (Cloudflare dashboard → R2 → bucket →
   Custom Domains). Keep **public listing OFF** — the origin must be
   **non-listable**: objects are reachable only by their content-hash keys.
2. Enable the committed-disabled registry row: set `enabled = true` on the
   `r2-public` entry in `ops/mirrors.toml` (the leg's branch
   `r11/P35.5-live-1`).
3. Dry-run, then apply:

   ```bash
   sig-ops mirror-push --name r2-public --export-dir <built release tree>
   sig-ops mirror-push --name r2-public --export-dir <built release tree> --apply
   # or inside a publish: sig-ops publish-web --public-tree <tree> --mirror r2-public --apply …
   ```

   The leg refuses (exit 3) when the row is disabled, the provider is
   metered-egress, a push cap is breached, the egress accounting is already in
   alarm, or the origin answers an anonymous listing.
4. Verify: `GET https://files.surveillancegraph.org/<release_id>/<path>.<sha12>`
   returns the bytes with `Cache-Control: public, max-age=31536000, immutable`;
   `GET https://files.surveillancegraph.org/?list-type=2` does NOT return a
   listing; `sig-ops egress-report` reports $0 egress beyond the free tier.

## 3. Egress ceiling and alerting (the $50/month kill-switch trigger)

- The committed ceiling is `ops/config.toml` `[egress] hard_ceiling_usd = 50.0`
  (SIG-TRANSP-019). `sig-ops egress-report --usage-usd <spent>` **warns at 80%
  ($40)** and **alarms at 100% ($50)** — an alarm exits 5 and, with `--alert`,
  fires a **recorded** alert through the P34.4 notifier seam
  (`ops/src/ops/alerts.py`, ADR-077).
- In the Cloudflare dashboard (operator step): set the billing/usage
  notification on the R2 account to the same $50 monthly ceiling so the
  provider-side signal arrives even between `egress-report` runs.
- A GB-side budget (`monthly_budget_gb`) runs beside the dollar ceiling; the
  report's level is the worse of the two bounds.

## 4. The kill switch (operator step — never an agent action)

When the ceiling alarms — or any time the mirror must stop serving — the
operator disables public serving **at the provider**:

1. Cloudflare dashboard → R2 → bucket `sig-bulk` → **remove/disable the
   `files.surveillancegraph.org` custom domain** (public reads stop within
   seconds; the objects stay private).
   _Alternative:_ keep the domain but **remove Public Access** so the bucket
   serves nothing anonymously.
2. Repoint public download links to the remaining mirrors
   (`ops/mirrors.toml`: the object-store row, BitTorrent magnets, Zenodo once
   deposited) — mirror-first degradation, per the mirrors registry.
3. Record the action in the spend ledger and the run ledger of the leg that
   fired it; the row in `ops/mirrors.toml` returns to `enabled = false` on the
   repair branch.
4. Re-enable only after the spend cause is understood and the ceiling is
   re-committed.

## 5. Rollback of the enable leg

- `ops/mirrors.toml` `r2-public` row back to `enabled = false` (its committed
  state).
- Pushed objects deleted from the R2 bucket (`<release_id>/**` keys).
- The CDN custom-domain route removed; egress/billing alert thresholds
  reverted to the pre-state capture (§1.4).
- GCS is untouched — it was never written by this leg.

## 6. What is NOT this row's

- The Zenodo production deposit — P37.55 (`D-R11-ARCHIVE-1`).
- OP-09 itself — the operator's step (`D-P34.50-1`); P35.67's leg probes the
  cutover read-only.
- The nameserver/CDN zone edit — `docs/build/reports/DNS_CUTOVER_RUNBOOK.md`.
