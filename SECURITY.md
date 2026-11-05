<!-- SPDX-License-Identifier: CC-BY-4.0 -->
<!-- Copyright (C) 2026 The SIG project. Documentation is CC-BY-4.0; see LICENSE and §42. -->

# Security policy (SIG-SEC-006; P37.4a, ADR-231)

## Reporting a vulnerability

Report security issues through the same public intake channel the project uses
for corrections, disputes and legal demands — the e-mail named on the
**/dispute/** page of the published site (`/dispute/`, category *security
concern*). The address is deliberately not committed to this repository; the
page always shows the current one.

Please include: the affected surface (public site, read API, export bundles,
connector pipeline), a description and reproduction, and whether the report
involves personal data (see *Scope*). **Do not open a public issue for an
unresolved vulnerability.**

## Response posture

- **Priority order** (SIG-GOV-003): privacy-harm and safety reports first —
  including anything touching plate, trip or per-person data — then factual
  security issues, then everything else. This is a *priority order*, not a
  response-time commitment: the project is maintained by a single operator and
  publishes no SLA (Round-11 waiver WV-08, ADR-186).
- **Acknowledgement:** the operator reads the intake channel and triages in the
  published order. A refused report is answered with reasoning (SIG-GOV-004).
- **Disclosure:** coordinated disclosure is the commitment (SIG-SEC-006): fixes
  land in the next publication release; the reporter is credited in the release
  changelog only if they ask to be. Legal demands are counted in the published
  transparency report (SIG-SEC-003, ADR-166).

## Scope

**In scope:** the public web surface (`/`, `/r/**`, `/s/**`, transparency
pages), the unauthenticated read API (`/v1/**`), the export and release
bundles, the ingestion/connector pipeline, and the operations machinery under
`ops/` — including anything that could expose claim data beyond the published
compartment, break the append-only guarantee, or bypass the ingestion gate.

**Out of scope:** issues in third-party dependencies without a SIG-specific
impact path (report upstream; the dependency audit + container scanning catch
known advisories), self-XSS, and theoretical attacks requiring a compromised
operator key (SIG-SEC-010's custody split is documented in the design spec).

## What this project does not hold

SIG's strongest protection is *not holding* the data (SIG-SEC-002): no plate
readings, trip histories, per-person records, user accounts or passwords exist
to leak. Reports that assume such data will be closed as out-of-scope with the
reference to Part VIII of the design spec.

## Supported versions

The public surface serves **release-bound, immutable publications**
(`releases/<pub>/`). Only the latest promoted release and the repository HEAD
receive security fixes; older releases stay readable verbatim (they are the
historical record) and carry their own integrity manifests.

## Verification of release integrity

Each release ships `SHA256SUMS` + `SHA256SUMS.minisig` (the pipeline's minisign
signature, public key `sig-release.minisign.pub` bound in the release) and
`sbom.cdx.json` — a deterministic CycloneDX SBOM rendered from the committed
`pylock.toml` — under `releases/<pub>/data/`. Deployed container images are
signed with cosign under a Cloud KMS asymmetric key and scanned by Artifact
Registry's Container Analysis (the P37.4a baseline leg; verify commands are in
`ops/gcp/security-baseline.sh`).

## Key handling

No secret may ever live in this repository (HG-09). Gate decisions and
production mutations are signed with an operator-only key (SIG-SEC-010); the
release-pipeline key signs manifests, never gate records, and vice versa.
