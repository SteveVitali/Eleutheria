# ADR-162: Transparency and distribution: export-time static artifacts, source-keyed rights lanes, a fail-closed scrub, a status lane and a zero-egress host

- **Status:** Accepted
- **Date:** 2026-10-01
- **Ticket:** SEED-11 (Round 11 Stage B, T1; unit SEED-11b)
- **Decided:** at GATE-P. A-3 was answered at 2026-10-01T03:53:59Z (round 2) and B-19 at 2026-10-01T04:39:45Z
  (round 13). The operator's words are recorded verbatim below.
- **Requirement ids:** SIG-EXPORT-002, SIG-EXPORT-008, SIG-EXPORT-009, SIG-METRIC-007, SIG-EVID-009, SIG-UI-035,
  SIG-PUB-015, SIG-TRUST-006, SIG-LIC-004a, SIG-LIC-010. The draft family SIG-TRANSP-D01…D25 (J3 §11) and D26…D43
  (K9/K10, via UXR-A10) is appended as SIG-TRANSP-001…043 by PLAN-11B (PLAN §6.2). SIG-REL-008 and SIG-REL-009 come
  from G3 (drafts D08/D09; §56.6; final ids per `PD/stageB/T1_id_map.csv`).
- **Spec:** `docs/2_canonical_design_spec.md` §17.5, §32.4, §38.1, §38.5, §39.9, §42, §43, §55.2
- **Implemented by:** P35.5 (zero-egress host, ceilings, kill switch); P35.31 (scrub, publish secret gate, capture-tier
  derivation); P35.32 (`ingest_run_report`); P35.33, P35.35, P35.36, P35.37, P35.39–P35.42; P36.43 (status lane);
  P36.45–P36.51, P36.66a/b (site snapshots), P36.67, P36.68, P36.69; P37.36 (raw archive); P37.41, P37.42, P37.55–P37.56;
  acceptance P37.65a/b (`PD/data/round11_plan.csv`; PLAN §5.6)
- **Sources:**
  - `PD` = `docs/build/planning/2026-09-30-next-phase/`.
  - `PD/feedback/RATIFICATION_LOG.md`, rounds 2 and 13.
  - `PD/data/decision_catalog.csv` rows Q-31, D-J3-4, OD-04, D-J3-1, D-J3-2, D-J3-3, D-J3-6, D-J3-7, D-J3-10,
    D-J3-11, D-J3-13 and Q-J4-7.
  - `PD/design/J3-transparency-design.md` §0–§3, §6.8–§6.9, §7.1, §8.1, §8.5, §9, §11, §13.
  - `PD/research/J4-redistribution-matrix.md` §0, §2, §8, §10.
  - `PD/reviews/S4-feasibility.md` FEA-18.
  - `PD/NEXT_PHASE_PLAN.md` §5.6, §7, §10.4.
- **Relationship to landed ADRs:** none superseded, amended, qualified or extended. PLAN §7 lists no status line for
  ADR-162.
  - J3 §8.1 and D-J3-6 describe the `/s/<pub>/` snapshots as "a new ADR extending ADR-132". PLAN §7 assigns ADR-132's
    `Extended by` line to ADR-161 (release model v2, P35.12), which owns descriptor v2 and namespace staging.
  - Related: ADR-048 (bulk exports and egress-friendly distribution), ADR-124 (the withdrawal and eligibility barrier),
    ADR-132 (immutable release namespaces), ADR-155 (page types), ADR-161 (release model v2), ADR-168 (collection
    conduct, robots disclosure), ADR-183 (express-terms acceptance), ADR-185 (Part VIII screened lanes).
- **Recorded:** 2026-10-01T07:44:31Z (`date -u` at writing; SEED-11b, Claude Code / Opus 5.5 sub-agent). This file records
  operator decisions taken at GATE-P; the record text is agent-drafted.

## Context

The operator asked to be able to *"explore each third party source, link to the ground truth, download the raw data,
and see ingestion logs/metrics/timestamps"* (Wave 2, PLAN §1.1). U-003.9 asked for sortable sources with downloads and
versions, and U-003.10 for per-source detail pages.

J1 and J4 found the following at planning time (PLAN §5.6; J3 §0–§1; cited, not re-measured here):

- **Release.** A checksummed 1.05 GB licence-separated release exists that nothing links to.
- **Evidence and run data.** None of the 255 public evidence items carries an upstream URL. The 342-row registry, 350
  real captures and 387 run rows are internal only.
- **Downloads.** They are served straight from GCS at internet egress rates, from an anonymously listable bucket. That
  is about $0.13 per full-release download and about $2,800/month for one looping scraper (J4 §7).
- **Raw bytes.** They keep data that ingest discards: OSM `user`/`uid`, Eyes on Flock search reasons, ArcGIS editor
  names (J4 NEW-4).
- **Rights.** Most sources are `derived-only`: 147 of the 237 in-scope sources rest on SIG-made factual-compilation
  or DB-right bases. Bytes are publishable only for `raw-ok` sources.
- **Permalinks.** Site pages do not pin to a release (J3 NEW-1).

SIG-EXPORT-008 makes egress "the existential cost". J3 drafted one design that keeps transparency inside the release
model, and J4 drafted the per-source rights lanes and the log scrub. The open choices went to the operator as A-3 (the
host) and B-19 (what is published).

## Decision

### The operator's words (verbatim, from `PD/feedback/RATIFICATION_LOG.md`)

| line | round time (UTC) | question as presented (summary, log) | operator answer, verbatim | sha256 of the answer text |
|---|---|---|---|---|
| A-3 | 2026-10-01T03:53:59Z (round 2) | DNS to Cloudflare + R2 $0-egress origin + $50/mo egress kill switch + contact@ alias. Options: *Yes, all three (Recommended) · No DNS move · Alias + ceiling only* | **Yes, all three (Recommended)** | `23fdd5a6edd22288021feb5e812691a8650a2f94b90af47c4cbef5f4d20d4361` |
| B-19 | 2026-10-01T04:39:45Z (round 13) | transparency package (raw-ok bytes after Part VIII screen; scrubbed run logs; snapshots; JSON-LD; prior releases as manifests; 6-h status lane; review packets). Options: *Yes, as stated (Recommended) · Also keep prior release bytes · Nothing new published* | **Yes, as stated (Recommended)** | `4c9ce7ecc8cf59eb515dff039921d76dcc1119aba1124a15b75b053b3c590e44` |

Each answer is an option label the operator selected. Labels: **agent-drafted, adopted by the operator at
2026-10-01T03:53:59Z** (A-3) and **at 2026-10-01T04:39:45Z** (B-19). The sha256 is
`printf '%s' "<answer>" | shasum -a 256`, computed at writing.

The B-19 line as presented in the packet (`PD/feedback/RATIFICATION_ANSWERS.md`):

> *"Transparency (Q-22): raw bytes for **raw-ok sources only**, after the Part VIII byte screen; J4's derived-only
> default; scrubbed run logs disclosing robots as host + count; commit hashes shown (repo is public); `/s/<pub>/`
> snapshots; JSON-LD as linked files; prior releases as manifests + disclosure, not bytes; status lane every 6 h, refused
> sources as counts; review packets linked after a per-packet check"*

The decision rows, quoted from `operator_answer`:

| row | answer (verbatim) |
|---|---|
| **Q-31** | *"a — move DNS to Cloudflare: P34.50 writes the runbook, then the operator switches nameservers (OP-09); R2 serves basemap, tiles, downloads and snapshots"* |
| **D-J3-4** | *"a — R2 mirror + custom domain, $50/mo egress ceiling with automatic kill switch (P35.5)"* |
| **OD-04** | *"a — create contact@surveillancegraph.org (OP-10, via Cloudflare Email Routing after OP-09) and use it as the project contact string"* |
| **D-J3-1**, **D-J3-3**, **D-J3-6**, **D-J3-7**, **D-J3-10**, **D-J3-11**, **D-J3-13**, **Q-J4-7** | *"yes"* |
| **D-J3-2** | *"yes — robots disclosed as host + count"* |

### What is decided

1. **Every transparency surface is a static artifact made at export time** (J3 T-1, T-2).
   - **Inputs.** Each artifact is built from the export's one read-only spine snapshot plus scrubbed run records. New
     reads are `EXPORT_QUERIES` keys over explicit-column views granted to `sig_export` only.
   - **Binding.** Each artifact is bound into the immutable release (ADR-132; descriptor v2 under ADR-161) and rendered
     by the site.
   - **The artifacts.** The source index and source pages; run, capture and issue records; the counting funnel;
     per-compartment statements files; per-source slices; the data dictionary; DCAT/PROV metadata; changes and id
     diffs; and the downloads center.
   - **No live reads.** Nothing is computed per request from the live spine, and the API serves the same files.
   - **New moving parts.** There are only three:
     - an append-only `ingest_run_report` table (P35.32);
     - the status lane (item 5);
     - the distribution host (item 6).
2. **Rights are keyed on the source, never on the compartment** (J3 T-3, T-4; J4 §2).
   - **Lanes.** Each source carries a reviewed raw-bytes lane: `raw-ok · derived-only · link-only · restricted ·
     unknown`.
   - **Default.** J4's lane table is accepted as the registry `[redistribution]` default (D-J3-1). That includes the
     `derived-only` default for the 13 SIG-labelled CC0 rows and the 147 factual-compilation / DB-right rows, reviewed
     to lift a source only on request (Q-J4-7).
   - **Attribution.** Every attribution string comes from the per-source registry text, and the publish fails on any
     required-but-empty attribution.
   - **Express-terms rows.** These stay published (A-8; ADR-183). Each file's ATTRIBUTION states the captured terms and
     the operator-accepted basis (PLAN §5.6).
3. **The scrub fails closed** (J3 T-6, §9.1; J4 S-1…S-14).
   - **One module.** Every log field, URL and header passes one policy module (P35.31).
   - **Abort rule.** A secret-shaped value anywhere in the publish set aborts the publish.
   - **What never appears.** Reviewers appear by role only. No person is named in logs, URLs, filenames or samples (J3
     T-11).
   - **Never exported.** The fields J3 §3.5 lists stay out of the public tree.
4. **What B-19 publishes:**
   - **Raw captured bytes, `raw-ok` sources only** (D-J3-1).
     - They are published only after the Part VIII byte screen. Re-serialisations for P8-5/6/8 are redacted, and
       redactions are new captures (SIG-PUB-015).
     - The first batch is the clear `raw-ok` sources with stored bytes, about 35 MB.
     - P8-1/P8-2/P8-4 and `restricted` sources never get raw bytes.
     - Withdrawal deletes the bytes, purges caches and leaves a tombstone.
     - Every archive write touching a Part VIII-screened family is an in-ticket go, never pre-authorised (OM-20;
       P37.36).
   - **Scrubbed run logs** (D-J3-2), robots outcomes included. A disregarded robots verdict is disclosed as **host +
     count** with a reference to GL-GATE-08 as re-confirmed (ADR-168).
   - **Connector version and commit hash** in public logs (D-J3-3). The repository is public (C-6).
   - **Per-release site snapshots `/s/<pub>/`** (D-J3-6).
     - The same export-mode site build runs a second time under base `/s/<pub>/`.
     - The result is staged into the release namespace and covered by its integrity manifest and withdrawal barrier
       (J3 §8.1). It makes every page citable (SIG-UI-035).
   - **Machine-readable metadata (JSON-LD, DCAT, PROV-O) as linked files only**, never inline `<script>` elements
     (D-J3-7).
   - **Prior releases as history** (D-J3-10). The restricted 2026-09-24 and 2026-09-27 trees are published as their
     manifests plus a disclosure, not their bytes, because they carry the attribution and terms defects.
   - **Rights review packets** (D-J3-13). The basis, gate reference, reviewer role and date are shown. Each packet is
     linked only after a per-packet Part VIII / personal-identifier check.
5. **The status lane** (D-J3-11; J3 §7.1).
   - **What it is.** A 6-hourly batch job, not a service. It runs read-only over the transparency views and scrubs
     through the same module.
   - **What it publishes.** Only `status/**`, through the single allow-listed publish path. It never touches records,
     claims or release trees.
   - **What it shows.** Gated and refused sources appear as counts only.
   - **Labels.** Status pages say they are newer than the release and are not a citation (J3 T-7).
6. **Distribution goes through a zero-egress host** (A-3; D-J3-4; J3 §6.8).
   - **Host.** An R2 origin under a SIG-controlled custom domain, after the DNS move to Cloudflare. P34.50 writes the
     runbook, the operator switches nameservers (OP-09), and P35.5 builds the host.
   - **Origin of record.** `sig-public` (GCS) stays the origin of record. Anonymous listing is removed; the signed
     `SHA256SUMS` and the catalog replace listing.
   - **Ceilings and kill switch.**
     - Egress has a **$50/month ceiling** with an **automatic kill switch**: downloads switch off, with a notice, if
       the ceiling is hit.
     - An **R2 Class-B operations ceiling with an alert** sits next to it (FEA-18; P35.5). The egress ceiling does not
       cover operations.
   - **Paths and limits.**
     - Paths are immutable, versioned and content-addressed, with `latest` only as a JSON pointer.
     - Per-file caps apply.
     - Rate limits are published on `/data/`.
   - **Launch order.** **No download link goes live before this host and its guard exist** (J3 R-3).
   - **Shared use.** The same host serves the basemap and tiles (ADR-156) and the snapshots.
7. **The `contact@` alias** (OD-04, the third member of A-3) is created by the operator (OP-10) through Cloudflare Email
   Routing after OP-09, and becomes the project contact string. Its use in the crawler user-agent and in sign-ups is
   ADR-168's (C-8: no request that needs a contact string is sent before the alias exists).
8. **Not decided here.** These belong to other ADRs:
   - release identity, descriptor v2, signing (B-20) and cadence: ADR-161;
   - Zenodo deposits (B-21): P37.55, an operator-run, in-ticket go;
   - the map basemap: ADR-156;
   - page-type budgets: ADR-155;
   - the Part VIII screened lanes: ADR-185.

## Consequences

- **U-003.9 and U-003.10, and the Wave-2 ask, get one coherent design.** Sources, runs, captures, downloads, the
  status lane and citable snapshots all come from release files, so site, JSON twins and API cannot disagree.
- **Spend is bounded by construction** (estimates from Q-31's consequences and the `PD/data/round11_plan.csv` row notes,
  which are inference; P34.5's spend ledger measures them):
  - R2 serving: about $2–13/month.
  - Status lane: about $0.2/month.
  - Raw archive: about $0.1/month.
  - Worst-case download egress: capped at $50/month by the kill switch.
- **Exposure grows with transparency.** Publishing robots disregard per host may prompt vendor blocking (J3 R-6;
  accepted by D-J3-2). Raw bytes and logs are the main Part VIII leak surface, which is why the scrub fails closed and
  raw bytes are `raw-ok`-only and phased (J3 R-2).
- **Irreversibility.** Downloaded bytes cannot be recalled (J3 §9.3). So nothing enters a release until the
  publication, attribution and scrub gates pass. The `/data/` withdrawal disclosure says plainly that earlier
  downloads may still circulate.
- **Ordering constraints follow.**
  - The attribution fix and its publish-time gate (P34.21a/b, 11A) precede the transparency surfaces (J3 R-1).
  - The capture-tier derivation (P35.31; J3 NEW-2) precedes any surface that advertises capture bytes. The dossier
    live captures depend on it (PLAN §5.9, TS-07).
  - Real per-claim provenance waits for actual capture bindings. Until then the panel says "run-level only" (J3
    G-6).
- **Snapshots multiply objects.** They add about 60–150 MB and 3–5k objects per release (J3 §8.1, inference), served
  from R2.

## Alternatives considered

- **No DNS move; GCS behind the load balancer** (A-3 options "No DNS move" and "Alias + ceiling only"; Q-31 b/c). Not
  chosen. Map serving costs about $6–43/month plus unbounded download egress, unless downloads stay unlinked, which
  leaves U-003.9/U-003.10 only partly met.
- **Also keep the bytes of prior releases** (B-19 option 2). Not chosen. They carry misattribution and terms-forbidden
  rows (J4 Q-J4-8).
- **Nothing new published** (B-19 option 3). Not chosen.
- **Rights keyed on the compartment licence.** Rejected (J4 §4.2). A compartment's licence says nothing about whether a
  source's bytes may be redistributed.
- **Reading run rows from GCS at export time instead of a spine table.** J3 §3.3 kept it open for T1. `ingest_run_report`
  was chosen in the plan (P35.32): the export stays one snapshot, the export job needs no restricted-bucket read, and
  append-only is trigger-enforced.
- **JSON-LD inline under an exemption.** Not chosen (D-J3-7). Revisit if Dataset Search indexing matters.
- **Pinning only the data, not the pages** (J3 §8.1 fallback). Not chosen. Snapshots make every page citable.

## Revisit trigger

- **Cost or abuse.** The egress kill switch fires, or the R2 operations ceiling alert fires, or measured spend for this
  ADR's parts exceeds its estimate by more than 2× in a P34.5 spend-ledger month.
- **Leak.** A Part VIII or personal-data leak is found in a published raw byte, log, URL, filename or sample, or a
  planted-secret test fails open. Stop the affected lane and re-decide by a new ADR.
- **Rights.** A rights holder objects to published raw bytes or derived rows (withdrawal per ADR-124/ADR-132), or a
  source's lane changes.
- **Conduct.** A vendor blocks SIG, or demands that it stop, after the robots disclosure (D-J3-2; also ADR-168's
  triggers).
- **Release model.** Descriptor v2 changes again, or ADR-161 is superseded. The snapshot and transparency-root inputs
  are then re-derived.
- **Requests.** The operator asks to publish prior-release bytes or inline JSON-LD (Dataset Search), or asks to retire
  the zero-egress host.
- **Status lane.** It becomes a second publish path: a non-`status/**` write gets through its allow-list (J3 R-12).
