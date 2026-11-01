# Copy batch 06 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.42b (row 384), the next row needing new public sentences
     after batch-05 (B-2 "Batches + notice allowance"; the entity-figure
     companion surfaces' wording is agent-drafted, pending verbatim
     confirmation). Append-only: rows are never deleted or edited in place —
     a correction is a new row superseding the old id, and a status change is
     recorded in the confirmation log below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. Contract-verbatim strings (the ER disclosure, the
SIG-UI-080 withheld sentence) are record data, never batch sentences.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| EF-01 | /entity/<type>/<key>/ | No drawn figure in this record wave — This build carries no static figure artifact for this entity — a publication state, not a finding about the entity. The tables on this page carry the same recorded facts. The drawn figure appears with a release that emits it. | 2b39a7545771c44d58eb9056c275e06fe5c08b5aa599b62f1595d012c3098ecd | pending |
| EF-02 | /entity/<type>/<key>/ | An interactive explorer view ships with the explore-surface wave; the figure and tables carry the same facts today. | 3fce5307181bdebd7f2eb042f3b8ce7596052d0a7377c074bfb4e5764e5c0a75 | pending |
| EF-03 | /entity/<type>/<key>/print/ | Print or save this page as a PDF (your browser's Print dialog → “Save as PDF”). Back to the entity page. | 9c1b706ca9742630df363f51448693a2d8136b1e459172acf842f0eecf8cf42a | pending |
