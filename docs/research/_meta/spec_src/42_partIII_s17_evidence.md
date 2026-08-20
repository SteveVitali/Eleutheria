## 17. The evidence store

The outline requires (OL-2B-IND-03) that raw source snapshots remain immutable, and (OL-13.4-01)
that SIG be able to hold a raw private archival copy alongside a redacted public derivative.
Q25 asks how snapshots should be content-addressed. This section answers all three.

### 17.1 Requirements

**SIG-EVID-001 (MUST).** The evidence store MUST satisfy, simultaneously:

| # | Requirement | Driven by |
|---|---|---|
| E1 | Bytes are write-once and verifiable by digest | OL-2B-IND-03, OL-8.15-02 |
| E2 | A capture remains **re-parseable**, not merely viewable, years later | OL-19.2, §21.7 backfill |
| E3 | Sensitive material can be sealed while its metadata stays public | OL-13.4-01, OL-Q31 |
| E4 | A takedown obligation is satisfiable through a permissioned, audited path | OL-Q32 |
| E5 | The store survives loss of the application entirely | §46.5 continuity |
| E6 | Storage cost is bounded and egress is not ruinous | §50 |

### 17.2 Content addressing

**SIG-EVID-002 (MUST).** Digests MUST be stored as **multihash** (base32-lowercase), not as bare
hex, so the algorithm is part of the value and can be migrated. *(REQ-R6-21; R6-F38.)*

**SIG-EVID-003 (MUST).** The interop digest MUST be **SHA-256 or SHA-512**; BLAKE3 MAY be stored
additionally in the fixity block for fast local verification. *(R6-F39.)* Rationale: BLAKE3 is
faster and actively maintained, but SHA-2 is what every archival and legal-verification
counterparty accepts. SIG carries both rather than choosing.

**SIG-EVID-004 (MUST).** Deduplication MUST be by digest. A portal page fetched daily that has
not changed produces one stored blob and N capture rows. `(content_digest, source_uri)` is
unique.

### 17.3 Layout: OCFL

**SIG-EVID-005 (MUST).** Evidence bytes MUST live in an **OCFL 1.1** storage root on
S3-compatible object storage: one OCFL object per source stream, one OCFL version per capture,
with `sha512` in the inventory manifest and BLAKE3 in the `fixity` block. *(REQ-R6-20; R6-F37.)*

Rationale for OCFL specifically, over a bespoke layout: it is designed for exactly this problem
(immutable, versioned, digest-verified objects with a human-readable on-disk structure), it is
**recoverable without SIG's software** — the inventory is JSON next to the files — and it is the
format digital-preservation institutions already accept. E5 is satisfied by construction.

```
evidence-root/
  0=ocfl_1.1
  ocfl_layout.json
  a1/b2/c3/  <urn:sig:source:flock-portal:hagerstown-md-pd>/
      inventory.json            # manifest: version → digest → path
      inventory.json.sha512
      v1/content/index.html
      v2/content/index.html     # only if bytes changed
      v3/content/capture.wacz
```

**SIG-EVID-006 (MUST).** Object storage holding evidence MUST have **versioning enabled** and
**Object Lock in *governance* mode** with a documented default retention. **Compliance mode MUST
NOT be used**, so that takedown obligations (§45) remain satisfiable through a permissioned,
audited path rather than being technically impossible. *(REQ-R6-23; R6-F41.)*

This is a genuine ethical trade-off recorded deliberately: compliance mode would make SIG's
archive unimpeachable against a hostile legal demand, and would also make SIG unable to honour a
legitimate privacy-harm removal. SIG chooses the latter capability, and compensates with
transparency reporting (§45.6).

### 17.4 Web captures

**SIG-EVID-007 (MUST).** Web captures MUST be stored as **WACZ 1.1.1** packages, not as
screenshots or rendered PDFs alone. *(REQ-R6-22; R6-F36.)*

Rationale: a Flock transparency portal is a JavaScript application. A screenshot proves what it
looked like; it does not let a future parser re-extract fields when SIG's extraction improves
(E2). A WACZ retains the network traffic — including the JSON the SPA fetched — so re-extraction
years later is possible. Screenshots and PDFs are ADDITIONALLY captured for human display and for
evidentiary presentation, as separate captures of the same artifact.

**SIG-EVID-008 (MUST).** For any artifact rendered by JavaScript, the capture set MUST include:
(a) the WACZ, (b) a full-page screenshot, (c) the extracted structured payload if one exists, and
(d) the raw HTML. Each is a separate `evidence_capture` row sharing one `evidence_artifact`.

### 17.5 Storage tiers

**SIG-EVID-009 (MUST).** Every capture MUST carry a `storage_tier`:

| Tier | Meaning | Bytes | Metadata | Excerpts |
|---|---|---|---|---|
| `public` | Freely redistributable, no sensitivity concern | Public URL | Public | Public |
| `restricted` | Lawfully held, redistribution limited by licence or sensitivity | Access-controlled | Public | Redacted |
| `sealed` | Contains material SIG must not expose (unredacted PII, sealed records, material under a takedown hold) | Access-controlled, audited | **Metadata-only public representation** | None |

**SIG-EVID-010 (MUST).** A `sealed` capture MUST still have a **public metadata representation**:
its existence, source, date, digest, and the claims it supports are public even when its bytes
are not. *(Discharges OL-13.4-01 and OL-Q31.)* This is what allows SIG to say "we hold the
contract, here is its hash, here is what it establishes" without publishing an unredacted PDF.

**SIG-EVID-011 (MUST).** Redaction MUST produce a **new capture** with `parent_capture_id` set,
never an edit of the original (SIG-EPIS-006). The redaction method and version MUST be recorded
so that a mis-redaction can be identified and re-done.

**SIG-EVID-012 (MUST).** Access to `restricted` and `sealed` bytes MUST be logged with
requester, purpose, and timestamp, and the access log MUST itself be subject to retention limits
so that it does not become a surveillance record of SIG's own researchers (§44.5).

### 17.6 Disappearance and link rot

**SIG-EVID-013 (MUST).** When an artifact ceases to be retrievable, SIG MUST record a
disappearance event on the artifact — `disappeared_observed_at` plus the failing status — and
MUST NOT delete the artifact, its captures, or its claims. *(Discharges OL-Q18.)*

**SIG-EVID-014 (MUST).** Disappearance MUST generate a research task (§33.2) and MUST be visible
in the UI as a distinct state: "this source no longer exists; SIG's capture of
YYYY-MM-DD is the record."

**SIG-EVID-015 (MUST).** A recurring link-rot sweep MUST re-check `capture_status` for all
artifacts on a cadence proportional to source volatility, and MUST attempt Wayback registration
for public artifacts SIG is permitted to submit.

**Rationale.** A vanished Flock portal is one of the most informationally valuable events SIG can
observe (OL-2B-FP-03, OL-3-04). Treating it as an error to be retried, rather than as a datum to
be recorded, would discard the single clearest signal that an agency changed its transparency
posture. *(R11 independently flags this as a top-5 operational risk the outline ignores.)*

### 17.7 Reproducibility and deposit

**SIG-EVID-016 (MUST).** Every claim MUST reference an `ingest_run` recording connector version,
code commit, ruleset version, vocabulary version, input evidence digests, parameters, and
environment. *(REQ-R6-25.)*

**SIG-EVID-017 (MUST).** Re-running a pinned connector over pinned evidence digests MUST produce
byte-identical claim tuples modulo `claim_id` and `sys_period`, enforced by a CI test.
*(REQ-R6-26.)*

**SIG-EVID-018 (MUST).** Ingestion MUST run with `LC_ALL=C` and `TZ=UTC`, and MUST NOT use
wall-clock time in any derived claim **value**. *(REQ-R6-27.)* Wall-clock time belongs in
`recorded_at`, nowhere else.

**SIG-EVID-019 (MUST).** Each quarterly release MUST be deposited to **Zenodo**, citing the
concept DOI for the dataset and the version DOI for the release. Evidence **bytes** MUST NOT be
deposited (size limits); the evidence **manifest of digests** MUST be. *(REQ-R6-30; R6-F42.)*
A Software Heritage deposit of the code MUST accompany it.

---
