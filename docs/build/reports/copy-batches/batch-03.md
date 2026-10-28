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

## Confirmation log

<!-- The operator's verbatim confirmation lands here at the copy-batch sitting:
     one line per sitting naming the rows confirmed, the operator's words
     verbatim, and a `date -u` stamp. Nothing is written until that sitting. -->
