# Description batch 24 — agent-drafted source descriptions awaiting operator verbatim confirmation

<!-- P36.45 (R11-K13-UX10-1; D-J3-12 / OD-07 a — 'batches of ~25 confirmed verbatim; description pending review until then'). Append-only: a status change is recorded in the confirmation log below with a `date -u` stamp; rows are never deleted. -->

## Convention

One row per agent-drafted per-source description — the **source** id,
the exact **text** as it will render, its **sha256** (UTF-8, no trailing
newline), and a **status** (`pending` · `confirmed`). Only `confirmed`
descriptions may land on the registry `description` field — the
publish-matrix lint fails a declared description whose sha256 matches
no confirmed row here. An unconfirmed source publishes
`description_pending_review`.

## Rows

| id | source | text | sha256 | status |
|---|---|---|---|---|
| D24-01 | statrep_wa_ago_alpr_registry | `Washington Attorney General's Office - Automated License Plate Reader (ALPR) System Registration: Registered ALPR System` — a government mandated disclosure source published by `Washington State Office of the Attorney General`. | b6bad2e7fc52da82a242a83b02627afd8b27ad0d876f4e19289f9fe24b6eaaf0 | pending |
| D24-02 | statrep_wa_watech_frt | `Facial Recognition · WaTech (Technology Services Board posting of FR Notices of Intent and Accountability Reports, ch. 4` — a government mandated disclosure source published by `Washington Technology Solutions (WaTech) / Technology Services Board, State of Washington`. | 54e067d283b1a2b5a4be90b4e6ab985e8c347e4590f09068b4bfd3f651078681 | pending |
| D24-03 | statrep_wa_wtsc_ate | `Washington automated safety enforcement reports (RCW 46.63.220(6)) — WTSC statewide report + municipal annual reports` — a government mandated disclosure source published by `Washington Traffic Safety Commission (with University of Washington), municipal reports filed by the ~29 operating jurisdictions`. | f0fbf90cc1c2e7f8c37789c11b82a27225873f1e9fe7edddf177a953418f0aed | pending |
| D24-04 | surveillance_under_surveillance | `Surveillance under Surveillance` — a community source. | b2f945ef71934ee1da08cb38765a9ff84d13f799443bbdce727b651233756b4e | pending |
| D24-05 | swagit | `Swagit — municipal meeting video/agenda portals` — a government portal source. | 8069b7eee3c48b412a7b91e64a80977d49c79ba0e076ad1dccd9d3d6765e8e4a | pending |
| D24-06 | technocarte_update | `Technocarte update` — an upstream project source. | 2d6e7193441ca385dc4b538d6b64c329ff715d04bdf9a444844f78a6b2ad58ad | pending |
| D24-07 | technopolice | `Technopolice` — an upstream project source. | 2e3f85b5fb7dad1f56594a6cc1930cfcab243d5cd84eda214b0f18c9f4d16e6a | pending |
| D24-08 | technopolice_forum | `Technopolice mapping discussion` — an upstream project source. | 73220f435b86717e0c160bab47897c739d734b31815afb249c8360c64a59d225 | pending |
| D24-09 | ted_eu | `TED — Tenders Electronic Daily (EU OJ S procurement notices)` — a government portal source. | 75935d6f13930e04a4ec05056f4126f7365a5a64c45d3d53a8bf6f4310e42c48 | pending |
| D24-10 | tips_usa | `TIPS` — a government portal source. | 811f1f59532e70975e351fb690e27de6a9d01afdf0556dcba332cb2e0b427523 | pending |
| D24-11 | uk_surveillance_camera_commissioner | `UK Biometrics & Surveillance Camera Commissioner — Surveillance Camera Code of Practice compliance & oversight` — a government portal source. | 8f5e39877fb41153f390eb0780a0a5021b9fa2cdd9b39630459fffc2adf65dd2 | pending |
| D24-12 | usaspending | `USAspending` — a government portal source. | cdadc87f686bbab30fcc64a5f945a26c1e863e99496e0119794aa8ccc321b148 | pending |
| D24-13 | wigle | `WiGLE` — a commercial source. | 340e94bb0c78b43ebb7e4fcfcb46eb71d3a2f26460532c4578bfe952d854b52d | pending |
| D24-14 | wikidata_sparql | `Wikidata SPARQL` — an upstream project source. | a71fa24b5fb56b95ee15d49f0df019dcb71ee0ae73e850787bfa2a2856cc2b72 | pending |
| D24-15 | wired_shotspotter_leak | `WIRED ShotSpotter sensor leak` — a news publisher source. | 9885eee4e10afb4992e55cccbe69b43a81a2230e77ba965d01fb850b6f74a96f | pending |

## Confirmation log

(none yet)
