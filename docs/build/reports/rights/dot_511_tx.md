# Rights-review packet — `dot_511_tx` (TxDOT CCTV locations, ArcGIS republish)

> P36.2 (row 350) staging packet. Facts are separated from judgement; this packet
> asserts no legal conclusion (defining standard §3.1). It stages the operator's
> recorded E4-R3 answer — it does not flip anything (OP-26; HG-03 is the
> operator's gate).

- **Source id:** `dot_511_tx`
- **Homepage:** https://services1.arcgis.com/7DRakJXKPEhwv0fM/arcgis/rest/services/TxDOT_CCTV_Locations/FeatureServer/0
- **Terms URL(s) fetched:** none — the item carries NO licence text (verified
  metadata, below)
- **robots.txt:** honor — probe + record (ADR-222); ArcGIS REST item not
  reviewed this pass

## Terms (verbatim)

ArcGIS item `adb3663e850e4f76be44596dbe696a93` ("TxDOT CCTV Locations"):
`licenseInfo` is **EMPTY** — there is no verbatim licence text to quote, and the
item is published under a *personal* account (`dkarctur`), not a TxDOT-owned org
(sources.toml notes, P26.7). `drivetexas.org`'s own camera API was unreachable on
probe (recorded). The target has 2,798 observed rows
(`dot_511_targets.toml`).

## SPDX candidate

`UNDETERMINED` — staged basis per the operator's E4-R3 answer:
`LicenseRef-PublicRecord-FactualCompilation` (GL-GATE-07 US rule;
`policy/data/licenses.toml` row exists — the same basis P26.16 applied to the
`dot_511_la`/`_ga`/`_al`/`_md` siblings).

## redistributable analysis

Unreviewed — `redistributable = false` until the operator's flip lands.

## derivative_permitted analysis

Unreviewed — `derivative_permitted = false` until the operator's flip lands.

## ODbL compartment implications

Not OSM-derived. No ODbL implication.

## Custody posture recommendation

MIRROR on flip (registry already declares MIRROR); `compact_status` becomes
`public_terms_only` per the E4 §2 flip recipe (currently `not_contacted` —
compact=False is a second gate failure beyond `ingestion_permitted`).

## Recorded operator answer — E4-R3 (GATE-P, 2026-10-01T04:49:27Z)

B-41 (ADR-169 §12, recorded verbatim): *"As listed, R3 flip"* — option label
selected by the operator **against the presented recommendation** (*"I recommend
finding a TxDOT-owned layer first rather than a second republish"*).
E4-R3 = **a — flip `dot_511_tx` under GL-GATE-07 (US)**.

This line records the operator's answer as DATA. The agent's half: the flip
patch is prepared on `r11/sources-flips` (staging only, unsigned); the operator
applies it in one signed commit or a GATE DECISIONS row (OP-26 / ADR-169 §14).
Nearest flipped precedent: `camreg_txdot_rep_tx` ("Texas Traffic Cameras",
personal account `JustinZero`, licence "none" → GL-GATE-07, live 2026-09-18);
the two layers likely overlap (same TxDOT population — inference, not a
conclusion).

## Decision

- [ ] permit ingestion — staged for the operator: `FLIPPED under GL-GATE-07 — "As listed, R3 flip" (B-41, 2026-10-01T04:49:27Z)` — reviewer: operator · date: ____
- SPDX to record: `LicenseRef-PublicRecord-FactualCompilation`   rights_reviewed_by (role, never a name): `maintainer (delegated)`   rights_reviewed_on: ____

## Counsel-needed flag

NO — decided class under GL-GATE-07 (US public-record factual compilation);
the row stays `ingestion_permitted=false` until the operator's act.
