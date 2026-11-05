# ADR-232 — The restricted-byte access posture: one audited access function, GCS Data Access audit logs with a retention sink + exclusion filter, and Cloud SQL ENCRYPTED_ONLY (P37.4b)

- Date: 2026-11-05
- Status: accepted
- Ticket: P37.4b (Round 11 / P37, row 423 — R11-OPS-08; serves SIG-SEC-005 +
  SIG-EVID-012; the OM-20 named mutation is GATE-G6 §4 pre-authorised, expires
  GATE-ACCEPT-R11)
- Base: `r11/P37.4a-security-baseline-scan-sbom-signing`
- Related: ADR-231 (the a-half's scan/SBOM/cosign baseline), ADR-177
  (evidence-store retention posture), ADR-201 (the conditioned-grant pattern
  the access-log IAM leg follows), SIG-SEC-007 (least privilege),
  D-P37.4b-1 (the queued apply leg)

## Context

SIG-SEC-005 names the requirement: access to `restricted`/`sealed` bytes MUST
be logged with requester, purpose, and time — and that log MUST itself carry
a retention limit so it does not become a surveillance record of SIG's own
researchers (SIG-EVID-012, §44.5). Three findings converged:

1. *G1-13's forensics gap.* No Data Access audit logs, so direct reads of
   restricted bytes in GCS were unlogged; the app-level
   `evidence_access_log` table covers API paths only; `_Default` logs keep
   30 days.
2. *G1-14.* Cloud SQL `sig-pg` ran `sslMode ALLOW_UNENCRYPTED_AND_ENCRYPTED`
   — reachable only through connectors, but `ENCRYPTED_ONLY` is cheap
   hygiene.
3. *F2a group 9's scope.* "A single audited access function; scheduled purge
   of expired log rows" — the contract's verbatim deliverable.

Open questions the decision had to answer:

1. *Where the direct-access log lives.* `evidence_access_log` keys rows on a
   `capture_id` foreign key and needs a write principal against Cloud SQL —
   right for API-served access, wrong shape for a byte-store read where the
   object name is the locator and the operator's ADC is the writer.
2. *Which principals are exempted.* Exempting every workload would make the
   turn-on decorative; exempting nobody makes the ingest/export/replica bulk
   readers drown the signal in volume and cost. G1-13's recommendation
   exempts the ingest and export SAs specifically.
3. *Where the entries retire.* Raising `_Default` retention keeps the entries
   in the same operational stream; a dedicated sink with a lifecycle is a
   declared, bounded home. SIG-SEC-005's own clause — the log is itself
   retention-limited — argues for a lifecycle that *deletes*, not a bigger
   window.
4. *Who runs the purge.* The access log's own writer must also be its
   sweeper, and neither may hold wider delete rights — the same
   conditioned-grant posture ADR-201 set for captures.

## Decision

1. **One audited access function, log-first.**
   `ops.restricted_access.audited_read` is the only sanctioned direct read of
   restricted/sealed bytes: it writes a `sig.restricted-access/1` record
   (requester, purpose, time, bucket, object) under `ops/access-log/` on the
   byte bucket **before** fetching, so a failed fetch is still an audited
   attempt; an empty requester or purpose refuses — no unaudited path exists.
   The API-path log `evidence_access_log` stays the table for API-served
   access; the object log is the byte-store counterpart under the same
   retention class.
2. **The access log is retained 180 days, then purged on a schedule.** The
   retention is `evidence.access_log.ACCESS_LOG_RETENTION_DAYS` (the
   SIG-EVID-012 bound) applied to the object log. `sig-access-log-purge`
   (weekly, Sun 10:00Z — outside the 03:00–10:00Z band) runs
   `sig-ops restricted-access purge --apply` over `ops/access-log/`: it
   deletes exactly the records provably expired, keeps **and flags**
   anything it cannot parse (never delete what you cannot explain,
   SIG-ENG-042), and lands a `sig.access-log-purge/1` record under
   `ops/access-log-purge/` — the sweep is itself audited.
3. **Data Access audit logs carry an exclusion filter.** The `audit` leg
   folds `storage.googleapis.com` `DATA_READ` + `DATA_WRITE` into the project
   `auditConfigs`, exempting `sig-ingest-rt`, `sig-export-rt` and
   `sig-replica-rt` — the declared mechanical bulk readers (G1-13's volume
   control: human and unexpected reads stay the signal). The merge is pure
   and idempotent: it adds exempted members, never removes.
4. **A retention sink, not a growing log.** The `sig-data-access` log sink
   routes the entries to PRIVATE `gs://<project>-sig-audit-logs` under a
   90-day delete lifecycle — the platform audit trail never becomes a
   permanent surveillance record either. The `SIG — Data Access audit-log
   daily volume` alert (FEA-18) fires at the recorded +$5/mo S1a bound
   (~350 MB/day ingested), and the leg records the log-volume cost read
   before and after — measured, never smoothed.
5. **Cloud SQL `ENCRYPTED_ONLY`.** `sig-pg` moves to
   `sslMode=ENCRYPTED_ONLY` (G1-14's cheap hygiene — connector-only access
   already carried TLS in practice); the restore point is the captured
   pre-state describe, rollback patches the pre-state value back.
6. **The named mutation rides one script under one recorded author.**
   `ops/gcp/restricted-access.sh` sequences `prestate → audit → sink → iam →
   ssl → job → cost → probe → verify`, windowed never 03:00–10:00Z with
   `SIG_RACC_AUTHOR` required on every mutating leg (OM-20 scope
   discipline). Every leg's restore point is the captured prestate (the IAM
   policy JSON, the sql describe) or a name-checked delete of an additive
   create; buckets and log objects are never deleted by the script. The leg
   is QUEUED `prepared_not_executed` under `D-P37.4b-1` —
   `SIG_GCP_PROJECT` unset at the engineering dispatch (OM-19).

## Consequences

- **A restricted read appears in the audit log** — the catalog acceptance
  shape — holds at two layers: the synchronous `ops/access-log/` record
  (the probe's MUST-hold check) and the platform Data Access entry
  (eventual; the probe records propagation honestly and `--verify`
  re-checks).
- The alerting roll's committed def set (`ops/monitoring/`) stays the
  P34.4/P35.2-owned surface: the log-volume alert policy def co-locates with
  the leg (`ops/gcp/data-access-alert-policy.json`) so the named mutation is
  the sole writer; a later alerting `verify` reports the policy EXTRA until
  a follow-up homes it — recorded, never smoothed.
- The auditConfig merge only ever *adds* exempted members — a smaller
  exclusion is a deliberate re-decision, never this script's silent act.
- The conditioned `ops/access-log/` + `ops/access-log-purge/` grant keeps
  the audit machinery's delete reach inside its own namespace — a purge bug
  cannot touch captures.
- Cost posture: the sink keeps ≤ 90 days of entries and the alert makes the
  +$5/mo bound loud rather than smoothed.

## Revisit trigger

The 90-day sink lifecycle proves too short for a real audit question
(lengthen before the first lifecycle delete would land); a second mechanical
bulk-reader class emerges (extend `SIG_RACC_EXEMPT_SAS` and the merge call);
the object-form access log proves insufficient for a takedown review that
needs to join `evidence_access_log` (the object log then mirrors into the
table); or the first real read shows the exempted set hiding a human access
pattern (the exclusion list is re-decided).
