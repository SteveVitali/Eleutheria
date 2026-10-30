# Copy batch 03 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.23 (row 363), the next row needing new public sentences
     after batch-02 (B-2 "Batches + notice allowance", round 11,
     UXK14-3b). Append-only: rows are never deleted or edited in place — a
     correction is a new row superseding the old id, and a status change is
     recorded in the confirmation log below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`/`batch-02.md`: one row per drafted public
sentence — **page**, exact **text** as it renders, **sha256** (UTF-8, no
trailing newline, `printf '%s' '<text>' | shasum -a 256`), **status**
(`pending` · `confirmed`). Only `confirmed` sentences may ship (B-2); the
publish gate scans every `batch-*.md`, so a pending row refuses the
republish rather than reading as untracked. The component-kit-B copy here
is shared-contract copy: the "Help find it" affordance renders wherever
the absence chip mounts (`/map/` today; the record surfaces as CX-01/GX
rows adopt it), and the callout kind labels render wherever `Callout`
mounts (the internal harness today — the rows are bound from day one so a
later public mount is already tracked).

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| CK-61 | lib/epistemic.ts | Help find it › | 747d1831ed389ecd9ba4b8467825e29d48987ddf97b54a924b791e3d1a7ee411 | pending |
| CK-62 | lib/callouts.ts | Note | d8da2c49df39d91df7ecd199b92da7bf264f026242ccc69b08daeadfe587c45b | pending |
| CK-63 | lib/callouts.ts | Caution | 2e178e6c65f95e64f44ab34d7cb1f8661f991b98392c4501061774d820f39f7e | pending |
| CK-64 | lib/callouts.ts | Known issue | 0743cfc411155f86d187922b3c5a91191b6c73c82b4ab4dfca98f3323b39dd88 | pending |
| PV-01 | /dossier/[...path]/print/ | Council brief | 17226999075fc9b74d604bb6b7657ce5931e12ba313ed742374755c5b4f357dd | pending |
| PV-02 | /dossier/[...path]/print/ | Fields recorded | 9ed975abc8d367baf0d15b75c1b1ecaf9014bf2c134b69d35f493854a5a757f9 | pending |
| PV-03 | /dossier/[...path]/print/ | Fields with no recorded value | 7ad73268a17663919cc83f808e0b9738b5150665e14cc55844efd9e2b9d284b0 | pending |
| PV-04 | /dossier/[...path]/print/ | Next decision | 9948287605a481d8713f9e3142e8eadf972d95f59f0a33833ed39d09861b87c7 | pending |
| PV-05 | /dossier/[...path]/print/ | (renewal or expiry) | ac9c748c73f5588df497430bf35a433a2525c46ec0bd4eb57f973b1761b1ec3f | pending |
| PV-06 | /dossier/[...path]/print/ | Documents to bring | 33aac1679d07b28eda441a25e7da1eb92eb00b713c224fd4769463192a8a98b8 | pending |
| PV-07 | /dossier/[...path]/print/ | No source documents recorded. | 18afea0c259871cafabc9278d686c1165c18b017d9f497435a6a39cfc7c554e5 | pending |
| PV-08 | /dossier/[...path]/print/ | Scan for the pinned page — | 7e94862e2952d7a081b181522b0fca2cebe9c3c60096902214d574c75fe3c0d3 | pending |
| PV-09 | /dossier/[...path]/print/ | Map — the recorded sites' geography. | e8e5b8571ebd769a20bdeb7efe1714b7ab1ae412a78b030b735d1f81ae3560a1 | pending |
| PV-10 | /dossier/[...path]/print/ | Extent — the recorded deployment's geographic coverage. | fe55809be91951102bb6dd89acb8650bb2dc5cbab0d401fd2083671aa54372a1 | pending |
| PV-11 | /dossier/[...path]/print/ | Trend — the recorded count over time. | 30a6eb08f3a9e5fec5608faba4a4d9ff56a586aa2871c056d09aa540ba980038 | pending |
| PV-12 | /dossier/[...path]/print/ | Axis — the recorded deployment axis. | 5b007e03234492c659491a2e48c4cbb7fcfbc570b23375d59fe577ca82d110bd | pending |
| PV-13 | /dossier/[...path]/print/ | Terms used on this page | 18fd4ef8ab76864b3c750a8e6e559478309004400d9c38a4764c7fdec3c70078 | pending |
| PV-14 | /dossier/[...path]/print/ | SIG dossier — print | 2d857645d1da24cbff34a4fba328f63d4d56a06906899861a19abd730ae2c0f0 | pending |
| PV-15 | /dossier/[...path]/print/ | Page {n}/{total} | 231b42c1e40729d468a66d87840ae2f0007ba0d0c3ea048c7a9a2fed12e68ceb | pending |
| PV-16 | /dossier/[...path]/print/ | Licence: {DOSSIER_LICENCE_ID}. | 96d64afb2017a52e817665199d1bb5048c39d55fd19d0f641c45b64c48ff2a42 | pending |

## Confirmation log

<!-- The operator's verbatim confirmation lands here at the copy-batch sitting:
     one line per sitting naming the rows confirmed, the operator's words
     verbatim, and a `date -u` stamp. Nothing is written until that sitting. -->
