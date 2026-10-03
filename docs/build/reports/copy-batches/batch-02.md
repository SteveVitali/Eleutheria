# Copy batch 02 — agent-drafted page sentences awaiting operator verbatim confirmation

<!-- Created by P34.18 (row 221), the next row needing new public sentences
     after batch-01 (B-2 "Batches + notice allowance", round 10,
     2026-10-01T04:32:16Z). Append-only: rows are never deleted or edited in
     place — a correction is a new row superseding the old id, and a status
     change is recorded in the confirmation log below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` · `confirmed`).
Only `confirmed` sentences may ship (B-2); the `identifier-changed` page is
served by the renamed-routes barrier only after its sentences are confirmed.
N-5 ("This identifier has changed." `4f628b89a266`) ships by sha256 under the
notice allowance (`data-notice`), not as a batch row.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| title | /sources/identifier-changed/ | Identifier changed | f977c1febe06483b2f7a34f749a0e46b5bcf2b0976f8747ccadb2d54fc9896d1 | pending |
| GN-02 | /sources/identifier-changed/ | Go to the sources and licences page | 7ec0a13a8fb2ec58f929e7381d906a36eb29ab699287a447c973ebe9e34c7750 | pending |

## Confirmation log

<!-- The operator's verbatim confirmation lands here at the copy-batch sitting:
     one line per sitting naming the rows confirmed, the operator's words
     verbatim, and a `date -u` stamp. Nothing is written until that sitting. -->
