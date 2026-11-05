# ADR-231 — The security baseline: deterministic release SBOM, Artifact-Registry scanning, cosign-over-Cloud-KMS image signing, and the deploy-path hook (P37.4a)

- Date: 2026-11-05
- Status: accepted
- Ticket: P37.4a (Round 11 / P37, row 422 — R11-OPS-08; serves SIG-SEC-006;
  the OM-20 named mutation is GATE-G6 §4 pre-authorised, expires
  GATE-ACCEPT-R11)
- Base: `r11/P37.3-evidence-store-hardening`
- Related: ADR-111 (deploy by pinned digest — the thing signatures bind to),
  ADR-132 (immutable releases — the SBOM rides the same determinism),
  SIG-REL-015 (pipeline-key custody: minisign for manifests, KMS for images),
  SIG-SEC-010 (operator gate signatures — separate custody entirely),
  D-P37.4a-1 (the queued apply leg)

## Context

SIG-SEC-006 names the standard-practice baseline: dependency and container
scanning in CI, an SBOM per release, signed releases, least-privilege service
accounts, and a documented incident-response/disclosure posture. P34.42a/b and
P35.x covered identities, secrets and digest pinning; P36.50 signed export
`SHA256SUMS` with the pipeline minisign key. The remaining decisions for the
scan/SBOM/cosign half:

1. *What the release SBOM describes.* `make sbom` renders the ambient `.venv`
   via `cyclonedx-bom` — useful for ad-hoc audits but runner-dependent, so the
   same release could carry different SBOM bytes depending on who built it.
   That contradicts the immutable-release posture (SIG-EXPORT-003): the SBOM
   must be a pure function of the code the release was built from.
2. *How images get signed.* Cosign keyless (Fulcio/OIDC) needs a CI OIDC
   identity the project does not run; a cosign keypair file would put private
   key material in a manager secret that a runner must read — the exposure
   class HG-09 exists to prevent. The release pipeline already deploys by
   pinned digest (ADR-111), which is exactly what cosign signs.
3. *Where scanning happens.* A local scanner (trivy/grype) would add a tool
   pin + per-runner DB drift; Artifact Registry already hosts every image, and
   Container Analysis provides managed scanning plus on-demand scans over
   pinned digests.

## Decision

1. **The release SBOM is rendered from the committed `pylock.toml`.**
   `exports.sbom` emits `sbom.cdx.json` — deterministic CycloneDX 1.5 over the
   exact locked dependency closure (purl + SHA-256 per distribution, uv
   workspace members declared as unversioned workspace components, no
   timestamp/serial — byte-identical per lockfile). `SpineExport.write_to`
   emits it beside `manifest.json`; `SHA256SUMS` covers it as a declared
   sidecar member (`downloads.SIDECAR_SUMS_MEMBERS`), the pipeline minisign
   pair signs the sums, and `build_release` binds `sbom.cdx.json` (+ its
   `.minisig` when the OP-20 key is provisioned) into
   `releases/<pub>/data/` — *SBOM and signature per release*.
2. **Image signing is cosign over a Cloud KMS asymmetric key.**
   `sig-release` keyring (`global`) + `sig-image-sign` (EC P-256 SHA-256, HSM
   protection — key material never leaves GCP, so nothing rides an env var or
   a repo file). The leg signs every deployed digest
   (`sig-api`/`sig-web`/`sig-release` job) and records
   `sig.image-signature/1` under `ops/security/` on the release bucket —
   append-only attestation history. This is a *separate* custody domain from
   SIG-SEC-010's operator key and SIG-REL-015's minisign pipeline key: the KMS
   key signs image attestations, never manifests or gate records.
3. **Scanning is managed: Container Analysis + on-demand scanning APIs.** The
   leg enables `containeranalysis`, `containerscanning`,
   `ondemandscanning` and `cloudkms`; `sig-ops security-baseline scan-status`
   reads occurrences for a digest; no self-hosted scanner is introduced
   (dependency advisories still ride nightly `dep_audit`/`npm_audit_gate`).
4. **The deploy path carries the hook, armed by env.** `lib.sh` gains
   `security_sign_image <digest>` — in `--check` every deploy plan prints the
   pending cosign commands (the baseline is never silently absent); in
   `--apply` it signs + verifies when `SIG_SECB_SIGNING=1`. `web.sh` calls it
   for every digest-pinned deploy. The default stays `0` until the leg runs —
   arming a not-yet-created KMS key would refuse every deploy.
5. **Disclosure posture is `SECURITY.md`** at the repo root: reporting
   through the published `/dispute/` intake (the operator's e-mail is never
   committed — OP-10), the WV-05/WV-08 honest priority order without
   response-time promises, SIG-SEC-002's no-held-data scope note, and the
   release-integrity verification section.

## Consequences

- The named mutation (`ops/gcp/security-baseline.sh` — prestate → apis → kms →
  sign → probe → verify) runs under the GATE-G6 §4 pre-authorisation once the
  contract preconditions hold (`SIG_GCP_PROJECT` + ADC + `SIG_SECB_AUTHOR`,
  outside 03:00–10:00Z); until then it is `prepared_not_executed` —
  `D-P37.4a-1`.
- Every export (and therefore every release) carries a byte-deterministic SBOM
  covered by the signed checksum list; `verify_downloads` fails loud on a
  tampered `sbom.cdx.json`.
- Once the leg lands, `SIG_SECB_SIGNING=1` makes every `web.sh` deploy sign its
  digest and verify the signature lands — an unsigned deploy fails loud.

## Revisit trigger

- cosign/sigstore GA changes the signing CLI contract; a second maintainer
  needs their own signing identity (a dedicated deploy SA replaces the
  operator-ADC posture); the SBOM must describe the container image contents
  rather than the workspace lock (then `syft` over the built image replaces
  the pylock renderer); Fulcio keyless becomes viable (the CI gains a workload
  identity federation) making the KMS key redundant; the first security
  report actually arrives through `/dispute/` (the response posture gets its
  first real test).
