# Copy batch 25 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P37.39 (row 463, R11-K13-QB-01 — quality basis, copies and
     possible duplicates on UX surfaces: the /disagreements/ co-located
     kind's copy). Append-only, same convention as batch-01: rows are never
     deleted or edited in place; a status change is recorded in the
     confirmation log with a `date -u` stamp. Id prefix: QB-* = the
     quality-basis surface's drafted copy. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. `{slot}` names vary per render — the row records the
template the element fills. Furniture — headings, link labels, table
captions — is navigational chrome, never a row.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| QB-05 | /disagreements/place/*/ | Co-located candidates are not evaluable for this place — {not_evaluable}. | aae96c869a7a41e53595ed2ea61beea57e620a1f347bc5286c377ec7459488c1 | pending |
| QB-06 | /disagreements/place/*/ | No cross-source co-located candidates are recorded for this place — records stay as listed, never merged. | 8108393f04b2517b06614e35f3c0bf8ec6e11e84991c6edcadb2798e6949bdda | pending |
| QB-07 | /disagreements/place/*/ | {count} possible duplicate pairs recorded — candidates for the same installation across sources; they are shown, never merged. | 196105b493db852aea0ee8ebc3ae0175c038f1558114e5b62d83ff37bc73fcbf | pending |
| QB-08 | /disagreements/ | No cross-source co-located candidates are recorded in this release — or the run that lists them has not completed. | e9fcb7e85161645b797809866046ac6e34dcaf84d9f5911a0b2ed8251070bffb | pending |

## Confirmation log

<!-- Operator confirmations append here, one line per row or batch-wide,
     dated with `date -u`. -->
