# Description batch 25 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D25-01 | surveillance_under_surveillance | `Surveillance under Surveillance` — a community source. | b2f945ef71934ee1da08cb38765a9ff84d13f799443bbdce727b651233756b4e | pending |
| D25-02 | swagit | `Swagit — municipal meeting video/agenda portals` — a government portal source. | 8069b7eee3c48b412a7b91e64a80977d49c79ba0e076ad1dccd9d3d6765e8e4a | pending |
| D25-03 | technocarte_update | `Technocarte update` — an upstream project source. | 2d6e7193441ca385dc4b538d6b64c329ff715d04bdf9a444844f78a6b2ad58ad | pending |
| D25-04 | technopolice | `Technopolice` — an upstream project source. | 2e3f85b5fb7dad1f56594a6cc1930cfcab243d5cd84eda214b0f18c9f4d16e6a | pending |
| D25-05 | technopolice_forum | `Technopolice mapping discussion` — an upstream project source. | 73220f435b86717e0c160bab47897c739d734b31815afb249c8360c64a59d225 | pending |
| D25-06 | ted_eu | `TED — Tenders Electronic Daily (EU OJ S procurement notices)` — a government portal source. | 75935d6f13930e04a4ec05056f4126f7365a5a64c45d3d53a8bf6f4310e42c48 | pending |
| D25-07 | tips_usa | `TIPS` — a government portal source. | 811f1f59532e70975e351fb690e27de6a9d01afdf0556dcba332cb2e0b427523 | pending |
| D25-08 | uk_surveillance_camera_commissioner | `UK Biometrics & Surveillance Camera Commissioner — Surveillance Camera Code of Practice compliance & oversight` — a government portal source. | 8f5e39877fb41153f390eb0780a0a5021b9fa2cdd9b39630459fffc2adf65dd2 | pending |
| D25-09 | usaspending | `USAspending` — a government portal source. | cdadc87f686bbab30fcc64a5f945a26c1e863e99496e0119794aa8ccc321b148 | pending |
| D25-10 | wigle | `WiGLE` — a commercial source. | 340e94bb0c78b43ebb7e4fcfcb46eb71d3a2f26460532c4578bfe952d854b52d | pending |
| D25-11 | wikidata_sparql | `Wikidata SPARQL` — an upstream project source. | a71fa24b5fb56b95ee15d49f0df019dcb71ee0ae73e850787bfa2a2856cc2b72 | pending |
| D25-12 | wired_shotspotter_leak | `WIRED ShotSpotter sensor leak` — a news publisher source. | 9885eee4e10afb4992e55cccbe69b43a81a2230e77ba965d01fb850b6f74a96f | pending |

## Confirmation log

(none yet)
