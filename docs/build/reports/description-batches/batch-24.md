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
| D24-01 | statrep_wa_ago_alpr_registry | Washington Attorney General's Office - Automated License Plate Reader (ALPR) System Registration: Registered ALPR System — a government mandated disclosure source published by Washington State Office of the Attorney General. | 6a699201481b417eaf2b368200613af21c6a435e7079831cca738276fb0a5a0b | pending |
| D24-02 | statrep_wa_watech_frt | Facial Recognition · WaTech (Technology Services Board posting of FR Notices of Intent and Accountability Reports, ch. 4 — a government mandated disclosure source published by Washington Technology Solutions (WaTech) / Technology Services Board, State of Washington. | 8f7b4141f29c2445899f8989a4517531e196aa81f15ef664496160e822706716 | pending |
| D24-03 | statrep_wa_wtsc_ate | Washington automated safety enforcement reports (RCW 46.63.220(6)) — WTSC statewide report + municipal annual reports — a government mandated disclosure source published by Washington Traffic Safety Commission (with University of Washington); municipal reports filed by the ~29 operating jurisdictions. | 597825a294fd4894ce6c196bbf3aa03b0e5e9e89ea7020f66b03877ecb2008d8 | pending |
| D24-04 | surveillance_under_surveillance | Surveillance under Surveillance — a community source. | 31da856defa175f66e3b761bfa41894fe34aa3d0b200cabd4218916624cd11f8 | pending |
| D24-05 | swagit | Swagit — municipal meeting video/agenda portals — a government portal source. | 4f08c1cffbbddbec59a47e832b8623865d42aebbcaa1b462a45522d6b936143d | pending |
| D24-06 | technocarte_update | Technocarte update — an upstream project source. | c65cb7b861cd81afd7f59ec47fcf717c1d2ae7c3d47dfd05830358fed843cf1a | pending |
| D24-07 | technopolice | Technopolice — an upstream project source. | f6f5fda936060dadef581caf3fbcb183cfab694bc67efbbaecdad448736fa204 | pending |
| D24-08 | technopolice_forum | Technopolice mapping discussion — an upstream project source. | 143b58ce638b07346d5c8238e4d2a386e0aec6264a9cc5d3ff5b2cb9c35f713e | pending |
| D24-09 | ted_eu | TED — Tenders Electronic Daily (EU OJ S procurement notices) — a government portal source. | 528f2e79cef2b10e88e98337c936864151b1da67eb1743d70c9f553a5cc63f4e | pending |
| D24-10 | tips_usa | TIPS — a government portal source. | b113ccaf9a93a2bcbeb1de4e15bde30396636253dbd381c0acc5e404094c546b | pending |
| D24-11 | uk_surveillance_camera_commissioner | UK Biometrics & Surveillance Camera Commissioner — Surveillance Camera Code of Practice compliance & oversight — a government portal source. | a6a0fd79f3c117c811587a76b5113cd65b1c649ea4ea3765e54edf06a71fd6b3 | pending |
| D24-12 | usaspending | USAspending — a government portal source. | db916c9f1bbf6f8ce24bbed07967deaf081b6cb48fe919c6d4dbe26e846476b4 | pending |
| D24-13 | wigle | WiGLE — a commercial source. | a23f58f866afe4cafaf886104dc88555a4e62408c2693a05624b1af92e917188 | pending |
| D24-14 | wikidata_sparql | Wikidata SPARQL — an upstream project source. | dfb2a190689237b619fc35d6ad4dbea72052b96f027b903da641e2a6454e51e5 | pending |
| D24-15 | wired_shotspotter_leak | WIRED ShotSpotter sensor leak — a news publisher source. | 7dd6e5cfddf09a704aa357e6e3892a6d75dca50261ca76e2af5e5c06624e321b | pending |

## Confirmation log

(none yet)
