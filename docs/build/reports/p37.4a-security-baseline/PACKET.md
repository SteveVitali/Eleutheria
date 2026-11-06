# P37.4a — Security baseline packet (`prepared_not_executed`)

**Authority (verbatim):** GATE-G6 §4 — "pre-authorise the 15 named 11D OM-20
rows: P37.3, P37.4a, P37.4b, P37.11, P37.12, P37.70, P37.15, P37.31, P37.32,
P37.33, P37.35, P37.46a, P37.46b, P37.56, P37.59" — operator selection
`"Approve all 15 (rec.)"` @ 2026-11-05T15:20Z; expires GATE-ACCEPT-R11.

**Named mutation (OM-14):** the security-baseline `production` writes —
scan/SBOM/cosign wiring into the deploy path — scripted end-to-end in
`ops/gcp/security-baseline.sh` (legs `prestate → apis → kms → sign → probe →
verify`; `--check` plans offline exit 0; window guard exit 42 inside
03:00–10:00Z; `SIG_SECB_AUTHOR` per apply).

**Status: QUEUED — `SIG_GCP_PROJECT` unset in the engineering dispatch**
(ADC present but `gcloud config project = rhema-507501`, not the SIG project;
cosign absent on PATH) — nothing ran against any API, keyring, image or
bucket: recorded `prepared_not_executed`, never fabricated (OM-19). Re-run:
`implement-spec spec=docs/tickets/422_P37.4a__security-baseline-scan-sbom-signing.md live_verification=true`
with `SIG_GCP_PROJECT` + ADC + `SIG_SECB_AUTHOR` exported and cosign on PATH,
outside 03:00–10:00Z.

**Legs and restore points (AR-2) — the scripted plan; none executed (queued):**
- `prestate` — planned captures: enabled-APIs list, KMS keyrings, deployed
  digests → sha256 sidecars + `restore-point.sh sqlpoint`, before any write.
- `apis` — `containeranalysis`, `containerscanning`, `ondemandscanning`,
  `cloudkms` enabled (additive; disable is never scripted).
- `kms` — `sig-release` keyring @ `global` + `sig-image-sign` EC P-256 HSM
  signing key; rollback = `versions disable 1` (never destroy).
- `sign` — planned `cosign sign --key gcpkms://… <digest>` per deployed digest +
  `cosign verify`; `sig.image-signature/1` records →
  `gs://<release-bucket>/ops/security/` (append-only).
- `probe` — queued acceptance: ≥1 signature per deployed digest MUST verify +
  scanning API live once the leg runs.
- Deploy-path wiring — `lib.sh security_sign_image` inside `web.sh`; armed
  `SIG_SECB_SIGNING=1` (config.sh default `0` until the leg exists).

**Acceptance shape (catalog):** SBOM and signature per release — landed
deterministically: `sbom.cdx.json` (CycloneDX 1.5 over `pylock.toml`) ships in
every export, is covered by `SHA256SUMS` + the pipeline minisign signature and
is bound into `releases/<pub>/data/`; the leg half adds per-digest cosign
signatures. A restricted read appearing in the audit log is the sibling row's
half (P37.4b owns the restricted-byte access + Data Access audit logs).
