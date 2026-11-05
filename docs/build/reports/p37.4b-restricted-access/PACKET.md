# P37.4b — Restricted-byte access posture packet (`prepared_not_executed`)

**Authority (verbatim):** GATE-G6 §4 — "pre-authorise the 15 named 11D OM-20
rows: P37.3, P37.4a, P37.4b, P37.11, P37.12, P37.70, P37.15, P37.31, P37.32,
P37.33, P37.35, P37.46a, P37.46b, P37.56, P37.59" — operator selection
`"Approve all 15 (rec.)"` @ 2026-11-05T15:20Z; expires GATE-ACCEPT-R11.

**Named mutation (OM-14):** the restricted-byte access posture — audited
access, Data Access audit logs + exclusion filter, `ENCRYPTED_ONLY` —
scripted end-to-end in `ops/gcp/restricted-access.sh` (legs `prestate →
audit → sink → iam → ssl → job → cost → probe → verify`; `--check` plans
offline exit 0; window guard exit 42 inside 03:00–10:00Z; `SIG_RACC_AUTHOR`
per apply).

**Status: QUEUED — `SIG_GCP_PROJECT` unset in the engineering dispatch**
(ADC present but `gcloud config project = rhema-507501`, not the SIG
project) — nothing ran against any policy, sink, bucket, instance, job or
log: recorded `prepared_not_executed`, never fabricated (OM-19). Re-run:
`implement-spec spec=docs/tickets/423_P37.4b__security-baseline-restricted-access-audit-logs.md live_verification=true`
with `SIG_GCP_PROJECT` + ADC + `SIG_RACC_AUTHOR` exported, outside
03:00–10:00Z.

**Legs and restore points (AR-2) — the scripted plan; none executed (queued):**
- `prestate` — planned captures: project IAM policy (`auditConfigs`), the
  `sig-pg` describe (`sslMode`), logging sinks, the restricted-bucket
  describe, the log-volume cost read BEFORE → sha256 sidecars +
  `restore-point.sh sqlpoint`, before any write.
- `audit` — `storage.googleapis.com` `DATA_READ`+`DATA_WRITE` folded into
  the project `auditConfigs`, exempting `sig-ingest-rt`/`sig-export-rt`/
  `sig-replica-rt` (G1-13's volume control — the declared mechanical bulk
  readers; human and unexpected reads stay logged). Restore point: the
  captured `policy-pre.json` — rollback re-sets it verbatim.
- `sink` — PRIVATE `gs://<project>-sig-audit-logs` (UBLA, 90-day delete
  lifecycle = the retention sink) + `sig-data-access` log sink + writer
  grant + the log-volume alert policy (FEA-18, at the +$5/mo bound).
  Additive creates; rollback is name-checked deletes (the bucket is never
  the script's to delete).
- `iam` — `sig-quality-probe-rt` conditioned `objectUser` on
  `ops/access-log/` + `ops/access-log-purge/` only (the audited-read writer
  + the purge own their own namespace — the ADR-201 posture).
- `ssl` — `gcloud sql instances patch sig-pg --ssl-mode=ENCRYPTED_ONLY`
  (G1-14); restore = the captured `sql-pre.json` value
  (`ALLOW_UNENCRYPTED_AND_ENCRYPTED`).
- `job` — `sig-access-log-purge` (weekly Sun 10:00Z, outside the band) +
  `sig-sched-access-log-purge` — `restricted-access purge --apply` deletes
  exactly provably-expired `ops/access-log/` records (180 d, SIG-EVID-012),
  audited by its own `sig.access-log-purge/1` record.
- `cost` — the log-volume cost read AFTER (the gate cell's before/after —
  measured, never smoothed).
- `probe` — the queued acceptance: `sig-ops restricted-access read` fetches
  a probe object — a `sig.restricted-access/1` record MUST land under
  `ops/access-log/` (a restricted read appears in the audit log); the
  platform Data Access entry lands within propagation (`--verify`
  re-checks).

**Acceptance shape (catalog):** a restricted read appears in the audit log —
engineered + fixture-verified offline: `audited_read` logs the
`sig.restricted-access/1` record *before* returning bytes (a failed fetch
stays audited), an empty requester/purpose refuses (no unaudited read), and
the purge deletes only provably-expired rows while flagging what it cannot
parse. The platform-layer half rides the queued `probe`/`verify` legs.
