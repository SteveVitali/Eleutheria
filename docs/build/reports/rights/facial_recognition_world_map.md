# Rights-review packet — `facial_recognition_world_map` (Facial Recognition World Map)

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `facial_recognition_world_map`
- **Homepage:** https://www.surfshark.com/facial-recognition-map
- **Terms URL(s):** homepage terms — **not fetched this pass** (reviewer to record)
- **robots.txt:** honor — not fetched this pass.

## Terms (verbatim)

> **Not fetched this pass.** A global, **country-level** map of facial-recognition
> deployment/regulation status. Publisher terms are not recorded; the reviewer must
> fetch the terms page and record the verbatim licence/attribution requirement, and
> confirm whether the underlying data (as opposed to the map graphic) is licensed for
> reuse.

## SPDX candidate

`UNDETERMINED` (accepted expressions per `policy/data/licenses.toml`).

## redistributable analysis

Separately reviewed (SIG-LIC-003). Coarse **country-level** aggregates only; ingested at
explicit coarse granularity and **never disaggregated to agency level** (§22.7,
SIG-INGEST-042, RISK-P0-08 / P4). redistributable=UNDETERMINED pending review.

## derivative_permitted analysis

Country-level claims labelled with the source's granularity; no finer inference.
derivative_permitted=UNDETERMINED pending review.

## ODbL compartment implications

Not OSM-derived.

## Custody posture recommendation

**LINK** — keep link-only until a rights review + operator flip. The REFERENCE-capture
path (`connectors.coarse_international`, P21.8) runs on a flip; the loader gate refuses a
live fetch (exit 3) until then.

## Decision

- [x] permit ingestion — reviewer: counsel (HG-02), operator-reported counsel approval 2026-09-15
- SPDX to record: `LicenseRef-DerivedFacts-Citations`   rights_reviewed_by (role, never a name): counsel (HG-02)   rights_reviewed_on: 2026-09-15
- **Status:** FLIPPED 2026-09-15 on counsel's approval — DERIVE custody, derived-facts only (metadata/facts, never the upstream expressive content), `redistributable=false`.

## Counsel-needed flag

**YES — SIG-LIC-009:** confirm the publisher's licence/terms and whether the underlying
data is reusable before any flip; a recorded reviewer role is not a legal opinion.

**HG-02 resolved 2026-09-16 (counsel, operator-reported):** derived facts/citations publishable — dedicated `derived_facts` compartment (ADR-086); `redistributable` flipped to true on the registry record (it gates SIG's emitted claims; upstream bytes are still never re-hosted — architectural, not flag-borne).
