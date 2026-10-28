# Rights-review packet — `camreg_edmonton_ab` (City of Edmonton — Socrata 'Intersection Safety Device Locations')

> P36.2 (row 350) staging packet. Facts are separated from judgement; this packet
> asserts no legal conclusion (defining standard §3.1). It stages the operator's
> recorded E4-R4a answer — it does not flip anything (OP-26; HG-03 is the
> operator's gate).

- **Source id:** `camreg_edmonton_ab`
- **Homepage:** https://data.edmonton.ca/d/7fnd-72gr
- **Terms URL(s) fetched:** not fetched — the City of Edmonton terms page
  capture is QUEUED (see `p362/terms-manifest.toml`, leg `p362-camreg-edmonton-terms`)
- **robots.txt:** honor — probe + record (ADR-222); the `data.edmonton.ca`
  Socrata `/resource/*.json` API pattern is allowed on the sister portals
  probed (City of Chicago; inference for Edmonton — no Edmonton-specific
  robots read this pass)

## Terms (verbatim)

Dataset `7fnd-72gr` (67 rows, intersection safety devices): the licence field
reads **"See Terms of Use"** on 7 of the family datasets and is absent on two
(`vfki-xv3i`, `39my-9n5c` — I4-C066 catalog read 2026-09-30T18:06Z). The City
terms page is titled **"Open Government Licence - Edmonton"** (I7-F011); its
body is JS-rendered and was never captured verbatim — that capture is this
row's queued leg.

## SPDX candidate

`UNDETERMINED` — the staged basis is *conditional on the captured body*:
the operator's answer (below) decides R4a on the **OGL-Edmonton** basis once
the terms body is captured; if the captured text is NOT OGL-Edmonton, a new
HG-03 line rides the GATE-G6 packet (S6R-28; the line is staged in
`p362/batch.md`). Fallback precedent if OGL is not evidenced:
`LicenseRef-OperatorAccepted-DBRight` (`camreg_calgary_ab`/`camreg_york_on`:
Canadian, no grant → DBRight).

## redistributable analysis

Unreviewed — `redistributable = false` until the operator's flip lands.

## derivative_permitted analysis

Unreviewed — `derivative_permitted = false` until the operator's flip lands.

## ODbL compartment implications

Not OSM-derived. No ODbL implication. (OGL-family licences publish in the
`ogl_*` compartments; the exact expression is set at flip time.)

## Custody posture recommendation

MIRROR on flip (registry already declares MIRROR); `compact_status` becomes
`public_terms_only` per the E4 §2 flip recipe.

## Recorded operator answer — E4-R4a (GATE-P, 2026-10-01T04:49:27Z)

B-41 as presented (log round 26 record clarification, S6R-02): *"R4a Edmonton
on OGL-Edmonton"*. E4-R4a = **b, then decide on the OGL-Edmonton basis
(I7-C11 a): capture the City of Edmonton terms and flip if they permit
(non-US kept by S5-4)**.

This line records the operator's answer as DATA. The agent's half: the terms
capture is queued (`p362/terms-manifest.toml`) — `prepared_not_executed`
while `live:P35.38a` fails; the OGL-Edmonton decision line is staged verbatim
in `p362/batch.md` for the operator's confirmation or a GATE-G6 line.

## Decision

- [ ] permit ingestion — staged for the operator **after the terms body is
  captured**: OGL-Edmonton basis → flip; else a new HG-03 line at GATE-G6 —
  reviewer: operator · date: ____
- SPDX to record: OGL-Edmonton expression if confirmed verbatim /
  `LicenseRef-OperatorAccepted-DBRight` fallback   rights_reviewed_by (role,
  never a name): `maintainer (delegated)`   rights_reviewed_on: ____

## Counsel-needed flag

PENDING TERMS CAPTURE — the queued fetch must land before the basis resolves;
the source stays `ingestion_permitted=false` meanwhile.
