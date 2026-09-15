# Proposed rights dispositions — the B pass (2026-09-15)

> Drafted by the maintainer as the RIGHTS-review pass for the connector-backed
> UNDETERMINED sources (P25.x). Each row states the **evidence fetched** (terms pages
> / dataset APIs — permitted research, not ingestion) and a **proposed disposition**.
> Nothing here flips `ingestion_permitted`: the flip is the operator's call (HG-03).
> Sources whose packet does not exist yet are marked **NEW PACKET DRAFTED**.

## Flippable-now proposals (resolved licence basis, defensible at maintainer level)

| source | evidence | proposed disposition |
|---|---|---|
| `usaspending` | Packet quotes the API terms (DATA Act, Pub. L. 113-101); U.S. federal works are public domain (17 U.S.C. §105). Counsel flag LOW. | **FLIP** — SPDX `CC0-1.0`, redistributable+derivative, REFERENCE custody. Code gap: POST-with-JSON-body (P25.2). |
| `fbi_cde_agency_registry` | FBI Crime Data Explorer / data.gov — U.S. federal government data (public domain, same §105 basis as usaspending). data.gov key staged. | **FLIP** — SPDX `CC0-1.0`, REFERENCE. NEW PACKET DRAFTED. Code gap: data.gov-key auth wiring (P25.4). |
| `eff_data_driven` | eff.org/copyright fetched 2026-09-15: *"Any and all original material on the EFF website may be freely distributed at will under CC-BY-4.0, unless otherwise noted."* The release is a joint EFF/MuckRock compilation of agency public-records responses; the underlying records are U.S. government records. Ingest is **aggregate-only** by design (§23.9: scan/hit/degree/retention figures, never per-search/per-plate rows). | **FLIP** — SPDX `CC-BY-4.0` (EFF compilation layer), redistributable+derivative at aggregate granularity only, MIRROR custody. Counsel flag PARTIAL retained (underlying-records nuance) — revisit if counsel disagrees. |
| `muckrock` | muckrock.com/api fetched 2026-09-15: documented public API; token auth via `accounts.muckrock.com/api/token/` + `/api/refresh/` (matches the staged refresh token); 15 req/min + identifiable-UA ToS; content = FOIA request metadata + released government records. | **FLIP** — SPDX per-document (records metadata listing; released-document contents carry the issuing agency's posture, recorded per document), REFERENCE custody, API-mode fetch under ToS. NEW PACKET DRAFTED. Code gap: JWT refresh flow (P25.2). Counsel flag PARTIAL. |

## Rights resolved, flip deliberately held

| source | evidence | proposed disposition |
|---|---|---|
| `raa_prefectures` | data.gouv.fr dataset API 2026-09-15: `license = odc-odbl` → **ODbL-1.0 confirmed** (the registry's SPDX was right). | Rights RESOLVED (ODbL-1.0); **stay unflipped** — the France-cohort invariant (P24.6/D-JURIS.2-1, `test_no_france_source_is_flipped`) holds the flip for the P25.5 France review, which must also resolve the *underlying arrêté PDFs'* posture (the index's ODbL doesn't carry into the gazettes). |

## Escalate / hold (genuine open questions — do NOT flip)

| source | evidence | proposed disposition |
|---|---|---|
| `decp_fr` | data.gouv.fr dataset API 2026-09-15: `license = fr-lo` → **Licence Ouverte confirmed**, and `fr-lo`/`lov2` is **not** in `policy/data/licenses.toml`'s accepted SPDX set. | **HOLD — needs an operator/counsel decision:** (a) amend the accepted set to add `LicenceOuverte-2.0` (licenses.toml + ADR + counsel), (b) map LO→CC-BY-4.0 per Etalab's own compatibility guidance (counsel question), or (c) leave UNDETERMINED until HG-02. |
| `madada` | madada.fr/help/api fetched 2026-09-15: no full API; Atom/JSON feeds + an authorities CSV. Content is **user-authored request text**; `compact_status = not_contacted`. | **LINK-only.** HG-04 outreach owed before any flip; user-authored republication is a real rights risk (SIG-LIC-003). Counsel YES. |
| `declarationcamera_be` | No packet existed (NEW PACKET DRAFTED). declarationcamera.be is a JS-only citizen site; no terms found. | **LINK-only** pending a real terms page / outreach. Counsel YES. |
| `aspi_mapping_chinas_tech_giants` | aspi.org.au/copyright → HTTP 403 (terms unfetchable programmatically). | **LINK-only**; coarse vendor-level aggregates only even if flipped later (SIG-INGEST-042). Counsel YES. |
| `carnegie_ai_gsi` | carnegieendowment.org terms page returned no content to the fetcher. | **LINK-only**; country-level only (SIG-INGEST-042). Counsel YES. |
| `facial_recognition_world_map` | surfshark.com/facial-recognition-map fetched 2026-09-15: editorial/marketing page, **no data licence stated**; commercial publisher. | **LINK-only**; country-level citation only, no re-host. Counsel YES. |
| `ccops_seattle`, `ccops_nyc_post`, `ccops_sf` | Packets: ordinance-mandated municipal disclosures (SMC 14.18 / POST Act / SF AC 19B). Municipal-record copyright posture is genuinely uncertain (17 U.S.C. §105 covers federal works only). | **HOLD at REFERENCE-pending-counsel:** the connector emits derived identifiers + citations and never re-hosts documents; flipping on that basis is defensible but the municipal-copyright question is HG-02's. Proposed: defer the flip to counsel; keep fixture-only runs. |
| `pathways_rtcc_federation`, `pathways_fr_css_forensics`, `pathways_acoustic_drone_location` | Packets: per-document mixed terms (government records + vendor press + advocacy). | **HOLD at current posture:** per-document rights review deferred to P25.5; fixtures remain short paraphrased fact carriers, never verbatim re-hosts. |

## Outcome — operator determinations recorded 2026-09-15

- **FLIPPED (4):** `usaspending` (CC0-1.0), `fbi_cde_agency_registry` (CC0-1.0),
  `eff_data_driven` (CC-BY-4.0), `muckrock` (`LicenseRef-MuckRock-API-ToS`,
  REFERENCE, `redistributable=false` — ingestion for evidence/citation only; the
  export gate fails closed on the non-registered expression until HG-02 resolves
  the per-document records posture). `rights_reviewed_by = "maintainer
  (delegated)"`, `rights_reviewed_on = 2026-09-15`; packet Decision lines marked.
- **`decp_fr` — DECIDED: add `LicenceOuverte-2.0` to the accepted SPDX set**
  (ADR-084; `relicensable_to` self-only until counsel confirms LO↔CC-BY). Rights
  RESOLVED on the row; **not flipped** — France-cohort gate (P24.6/D-JURIS.2-1)
  holds it for P25.5, same as `raa_prefectures` (ODbL confirmed).
- **Held (9):** madada, declarationcamera_be, aspi, carnegie_ai_gsi,
  facial_recognition_world_map, ccops×3, pathways×3 — LINK/REFERENCE-pending,
  counsel or HG-04 outreach owed.
- **Live-ops state after the pass:** 12 sources flipped/loadable; the four new
  ones still need their P25.2/P25.4 connector code (POST body, JWT refresh,
  data.gov-key auth, bulk-file fetch) before a live run emits anything.
