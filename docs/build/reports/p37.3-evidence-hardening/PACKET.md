# P37.3 — Evidence-store hardening packet (`prepared_not_executed`)

**Authority (verbatim):** GATE-G6 §4 — "pre-authorise the 15 named 11D OM-20
rows: P37.3, P37.4a, P37.4b, P37.11, P37.12, P37.70, P37.15, P37.31, P37.32,
P37.33, P37.35, P37.46a, P37.46b, P37.56, P37.59" — operator selection
`"Approve all 15 (rec.)"` @ 2026-11-05T15:20Z; expires GATE-ACCEPT-R11.
**Carried decision:** `G1-RET [B-14] = a` — 365-day unlocked retention
(takedowns + the WV-06 deletion path stay possible).

**Named mutation (OM-14):** the evidence-bucket retention-policy write + the
off-instance replica/cross-project copy jobs — scripted end-to-end in
`ops/gcp/evidence-store.sh` (legs `prestate → bucket → captures → dr-bucket →
iam → jobs → repoint → probe → verify`; `--check` plans offline exit 0;
window guard exit 42 inside 03:00–10:00Z; `SIG_EVSTORE_AUTHOR` per apply).

**Status: QUEUED — `SIG_GCP_PROJECT` unset in the engineering dispatch**
(no hosted env); nothing ran against any bucket, job, or IAM policy —
recorded `prepared_not_executed`, never fabricated (OM-19). Re-run:
`implement-spec spec=docs/tickets/421_P37.3__evidence-store-hardening.md live_verification=true`
with `SIG_GCP_PROJECT` + ADC + `SIG_EVSTORE_AUTHOR` exported
(`SIG_BACKUP_PROJECT` optional — the export-copy leg queues without it).

**Restore points (AR-2):** IAM policies exported pre-grant; every object
write additive (source captures never deleted); per-job volume spec recorded
for repoint rollback; rollback removes only this leg's creations and never
deletes a bucket (WV-06 is the operator's act).

**Acceptance shape (the leg's `probe` step):** a delete attempt on a fresh
probe object under the 365-day unlocked retention MUST fail (unlocked
retention binds every principal — an ingest SA delete attempt on a capture
fails a fortiori); replica parity `dest == source − excluded` on
`sig-ops restricted-replica verify`.

**Pending declaration amendments that ride the leg's own commit**
(the reserved/absent-resource convention — a binding on a not-yet-created
resource is never declared ahead of the leg that creates it):
`iam_identities.toml` (sig-replica-rt bound + replica class + count 102 +
the new bucket_role rows) · `cadence.toml` (`state` paused→enabled +
`[[buckets]]` posture rows for the two new buckets) · `exec_host.toml`
(mount bucket→sig-evidence) · `config.sh` (`SIG_CAPTURE_BUCKET` default flip).
