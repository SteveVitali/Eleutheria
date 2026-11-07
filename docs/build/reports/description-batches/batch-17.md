# Description batch 17 — agent-drafted source descriptions awaiting operator verbatim confirmation

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
| D17-01 | eyes_on_flock | `Eyes on Flock` — an upstream project source. | 784ce233dc1bec655588a308e031fd234f319d1c2cfa358498c395edcc72ed41 | pending |
| D17-02 | eyes_on_flock_description | `Eyes on Flock description (Reddit)` — a news publisher source. | 6734a36e10db8bcee4a06ca341d853b28cfa1e6d8f764c30f6166c0178e71791 | pending |
| D17-03 | faa_drone_waivers | `FAA drone waivers` — a government portal source. | 476d930d4527820ecd86ce57259f450b243d04d05c998458768d0d05cad82a69 | pending |
| D17-04 | facial_recognition_world_map | `Facial Recognition World Map` — a community source. | b7aaf2d0d8aa765d78329506ac141ad3d6a53ea837ec3f7a834ece0dd82950cb | pending |
| D17-05 | fbi_cde_agency_registry | `FBI CDE agency registry` — a government portal source. | 8f4e2ae96e9c18b165de552b721ccd2d48312d39a9faf3520e2cbacf3e3b6368 | pending |
| D17-06 | fema_hsgp_allocations | `FEMA Homeland Security Grant Program (HSGP/UASI) allocations — federal grant funding to fusion centers and RTCCs` — a government portal source. | 9fa75f4f6dd20a9f42b02af901ad190be38740aaae8ecad85e90fe6fc40e4f25 | pending |
| D17-07 | flock_ajith_fyi | `flock.ajith.fyi` — a community source. | 8754a7d58516f5157708e70201fa7e9c7ec2262e6935697a0fcd5b02e13e489d | pending |
| D17-08 | flock_api_terms | `Flock API & Integration Terms` — a vendor site source. | 90e8d7d96703039820d3543f06613fef3190fdfc2114dca4d82a19f43ffdca44 | pending |
| D17-09 | flock_finder | `Flock Finder` — a community source. | 90afa64a5d5116270a82791adef7ea3af4389cb52894982b8f4c366cd743ff90 | pending |
| D17-10 | flock_transparency_portals | `Flock transparency portals` — a vendor site source. | 7d65ca80ee10c47f0935652700d18539d9013d1230caa3c3aaef8b04f63f8cde | pending |
| D17-11 | flock_you | `Flock-You` — a community source. | dedef1aa67d9342e0e05517056e8782bba0016b19342a7199ba16297aa547841 | pending |
| D17-12 | flockhopper3_deflock_data | `flockhopper3/deflock-data (NOT DeFlock)` — an upstream project source. | 4aaeb9e9af344f8ba430645196d808bf3001dbb4f3f0135f33909516224acb4d | pending |
| D17-13 | flockreporter | `FlockReporter` — a community source. | 8e1d7f5718ed0a9a80a057e45b9547436b7bb6f57fd0005f5a2fd7bfd7068dae | pending |
| D17-14 | foiaxpress | `FOIAXpress` — a records channel source. | b59891a6989959ee1fb9f694c41cd611e2bbc7547ccb5dfabc27214af0e04f62 | pending |
| D17-15 | footnote4a | `Footnote4a` — a community source. | 7fce7c9491eb7a5744e35cfb4848a271a4905b1ae2947ce53dbe3471fc2e4114 | pending |
| D17-16 | future_statutory_disclosure_2027 | `State statutory disclosure — first reports due 2027-04-01` — a government portal source. | 14c3c28dd9c88d6b3143b81916d2f72403a103f46e7e039e0bbbd48127bb481c | pending |
| D17-17 | future_statutory_disclosure_al | `Alabama LPR Registry duties — Ala. Admin. Code 265-X-6` — a government portal source. | a2ffea832da53b75b9ef21eeb87a32965ee83bd1bd4b70035ae4077a4f0e8e30 | pending |
| D17-18 | future_statutory_disclosure_ar | `Arkansas LPR statistics compilation — 12 CAR 150-103(f)` — a government portal source. | f48a35bda75065bdf6bed7a93f31006fb589689bd7eff7e63846e77ace57ac33 | pending |
| D17-19 | future_statutory_disclosure_mn | `Minnesota NW Metro RTCC report — HF 3198 (2025-26), contingent` — a government portal source. | 43a14c31a0bb23f9bb6994f5063471a162a6b9cd641bd6c54b14e240e5510214 | pending |
| D17-20 | future_statutory_disclosure_nm | `New Mexico ALPR agency reports to DPS — SB 40 (2026) §A` — a government portal source. | edb72d45e8b43c2dbab3967292b41d79481d62d1fe41370de52b8dd527568ae8 | pending |
| D17-21 | future_statutory_disclosure_ut | `Utah facial-recognition annual reports — Utah Code 77-23e-106` — a government portal source. | a751a56c9ee3ae59874f19de78ff6d07ca5b4e28c808c1deb6411d3c54b877e0 | pending |
| D17-22 | future_statutory_disclosure_va | `Virginia ALPR statutory disclosures — Va. Code § 2.2-5517(I/J/K)` — a government portal source. | ca8093b3574e9d5e4015cb98b60dcb3d6a844139907e9b0b3c2500952ddc25ba | pending |
| D17-23 | gao_surveillance_reports | `U.S. Government Accountability Office — surveillance-technology oversight reports (facial recognition, ALPR, DHS grant programs)` — a government portal source. | 912e4955fb8419d97ae763073a6256691f7f02b9d5c8b7aab3d1d11688390978 | pending |
| D17-24 | gleif | `GLEIF golden copy` — a government portal source. | bbe62ba191a573518e49366e64c03bee7a1fa893720363521f5d5c0376a6196a | pending |
| D17-25 | govqa | `GovQA` — a records channel source. | f19e05f691393481d5a4f933035f5b8278ce955ea6055600b08f4c46657af431 | pending |

## Confirmation log

(none yet)
