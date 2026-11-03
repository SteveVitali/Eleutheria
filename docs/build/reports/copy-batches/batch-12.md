# Copy batch 12 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.52 (row 395, dossier sources explorer), the row needing new
     public sentences after batch-11 (B-2 "Batches + notice allowance",
     D-K5-2 = OD-07 a): the "Where this comes from" dossier block and the
     /dossier/<path>/sources/ explorer wording — the lede, the headline line,
     the previously-contributed intro, the over-time caption and the
     downloads absence — is agent-drafted, pending verbatim confirmation.
     Append-only: rows are never deleted or edited in place — a correction is
     a new row superseding the old id, and a status change is recorded in the
     confirmation log below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish
gate scans every `batch-*.md`, so a pending row refuses the republish
rather than reading as untracked. The `data-copy` attribute binds each
rendered element to its row ids. `{placeholder}` fields are injected
DATA (dates, counts, source names), not drafted copy.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| DS-01 | /dossier/&lt;path&gt;/ | The per-source contribution detail for this dossier is not published in this release — the sources table lists every source SIG tracks. | 05b838f1a9f7e92369f193a6730a3818cccf384dbded045756ab670e7fff212e | pending |
| DS-02 | /dossier/&lt;path&gt;/ | {records} records from {sources} sources · first seen by SIG {first} · last seen by SIG {last} | 62946d97cff69a1be35df4ae4f79b7244f890416008927701f36c8094e1cea4c | pending |
| DS-03 | /dossier/&lt;path&gt;/ | Explore all {sources} sources → | 98f9f60f4307f3f43f12b86919a9a966c3b517240b2219c1967e81c43248e505 | pending |
| DS-04 | /dossier/&lt;path&gt;/ | (downloads for this dossier are not yet available) | f72da752c7469474e9aecee73486674bff2553e406dffc928d4cd3459f47ea3a | pending |
| DS-05 | /dossier/&lt;path&gt;/ | The full "How we know this" provenance for this dossier (not site-wide) is at the foot of this page; the explorer reconciles every figure above to its sources. | ef38d51a41ddec4f584af050a4dc601cd3a9f7f350fb5c148c95c32af7a9eb8b | pending |
| DS-10 | /dossier/&lt;path&gt;/sources/ | Every source that contributed to {dossier} — what it added, when SIG saw it, and where sources disagree. | a2e6df368d0081583b149dbe4b46e81bcc357b76d336bbdd2f572b0bde22fd1a | pending |
| DS-11 | /dossier/&lt;path&gt;/sources/ | Sources that no longer contribute — with when SIG first and last saw them, and why they stopped. | 8accc38e03c488c11178fd76a57fa5d9c1dfbf047fea63acc144f35db647e446 | pending |
| DS-12 | /dossier/&lt;path&gt;/sources/ | Monthly records first seen by SIG, per source — a capture time, never an installation date. | 849f85f3668f6c49137516100b867b7b2445eb66a6835c88fe9647c25d591bc0 | pending |
| DS-13 | /dossier/&lt;path&gt;/sources/ | No recorded disagreement on this dossier — and where two sources may describe the same installation is not evaluable yet ({reason}). | b6056d7646b6f20008a4dd20fc9889951b5055242f34d13f8d58a9be86b7d368 | pending |
| DS-14 | /dossier/&lt;path&gt;/sources/ | Downloads for this dossier are not yet available — per-dossier, licence-compartmented files land with the downloads row (DSRC-03). The dossier-sources JSON above is the machine-readable view. | 3bd56b72d107f3d6b528c5891549e21907b5b344a91490cc4aa39319b1fe7a98 | pending |

## Confirmation log

<!-- one line per status change, `date -u` stamped; empty until the
     operator confirms a row verbatim. -->
