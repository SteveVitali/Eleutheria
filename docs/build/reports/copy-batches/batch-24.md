# Copy batch 24 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P37.38 (row 462, R11-K13-CX-01 — the disagreements browser:
     /disagreements/ + /disagreements/place/<slug>/ copy). Append-only, same
     convention as batch-01: rows are never deleted or edited in place; a
     status change is recorded in the confirmation log with a `date -u` stamp.
     Id prefix: CX-* = the disagreements surface's drafted copy. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. Furniture — headings, link labels, table captions — is
navigational chrome, never a row (the batch-16/23 precedent).

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| CX-01 | /disagreements/ | Where the record disagrees with itself, SIG keeps every side visible — this browser lists each disagreement the release records, labelled by kind, never silently reconciled. | 3776f908b7e195e232df772cfa3b69bb9b76bcc673a45b52d74b906394b168ee | pending |
| CX-02 | /disagreements/ | Two claims that disagree about the same subject, each with its source and dates. The record keeps both sides; it does not pick a winner. | 4a7c85cbf8ddaf249d62db4b8b6d88e3474164dcc72c33360b3286556f888527 | pending |
| CX-03 | /disagreements/ | Records one source locates at conflicting coordinates — identity defects SIG keeps labelled until the subject re-keying lands, never treated as a contradiction between sources. | d74cfa47af1bef8994f214a8e147d610235efb60912d910449b887d94af0ca20 | pending |
| CX-04 | /disagreements/ | Records a source declares to one jurisdiction but locates in another — shown on both sides: the declaring dossier and the locating dossier. | 8630a406808023e343beb4784d5e40ccd09b1636b5423799a8c9429f532205f6 | pending |
| CX-05 | /disagreements/place/*/ | Every disagreement the release records for this place, labelled by kind — contradictions keep both sides; placement disagreements show here and on the counterpart dossier. | 0bc10352412c342c3844da03af3e290d49598fe48df88bef9d21f933a6590a0e | pending |
| CX-06 | /disagreements/place/*/ | No recorded contradiction is placed here in this release — none exists to show, not a hidden one. | b25ef3f47ac92b1dea0164cd1c3fa0351d8a7c36c7ad8a773f87bb5671a80aa5 | pending |
| CX-07 | /disagreements/place/*/ | Records the same source locates at conflicting coordinates — labelled identity defects, not a disagreement between sources. | 4566e4bf7cb98c4d8c699d3a607d6c055bd07af6dc865ed848e4173803c3c190 | pending |
| CX-08 | /disagreements/place/*/ | No within-source coordinate conflicts are recorded for this place. | dd65b1af70a88b43b83fbfa8767f0180b937af7d76ab2311b64e67445e37c1f3 | pending |
| CX-09 | /disagreements/place/*/ | No declared-vs-located disagreement is recorded for this place. | 6eb1bbf36e9ae147fcaa4d1321e04b89d3c660d4da65a8d992c31ae2182a4f7a | pending |
| CX-10 | /disagreements/ | No recorded contradictions in this release | 699f7610dc65abedfb28a0e8137dee4ef6f94fe843eb888d3b91a5f71bdd1ef8 | pending |
| CX-11 | /disagreements/ | No materialized contradiction record is published in this release — none exists to show, not a hidden one. | 9aa8438cac9b833e285d94f20711940505bdef8f1396bcb5f7e2c6f5799b5390 | pending |
| CX-12 | /disagreements/ | The declared-vs-located and coordinate-conflict sections below still list the disagreements placement records. | 2ead06e958e2a0a5c15bff456c18ddf28deb969d648f5ab425939d328e472702 | pending |
| CX-13 | /disagreements/ | Browse the evidence | addfdc03f1922778bed7445dc7919da922810771dcd4a52b3ded63cb70c03ab0 | pending |
| CX-14 | /disagreements/ | A contradiction appears here once a release materializes one. | 7876369c9d84fa6d26a1714d70dddc6f6690618111e2a780e71680f169dfb27a | pending |
| CX-15 | /disagreements/place/*/ | Every count on this page cites the dossier's own contribution artifact — the same numbers the sources explorer shows. A kind with nothing recorded says so; it is never smoothed into a zero it does not mean. | 2b030cc20c5981d42aa7558b061fc76c4b3434213d8f5f3162e996a2d584e9a1 | pending |

## Confirmation log

<!-- Operator confirmations append here, one line per row or batch-wide,
     dated with `date -u`. -->
