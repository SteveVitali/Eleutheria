# Copy batch 22 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P37.29 (row 453, R11-K13-VIZ-04 — in-place map activation on
     dossiers). Append-only, same convention as batch-01: rows are never
     deleted or edited in place; a status change is recorded in the
     confirmation log with a `date -u` stamp.
     Id prefix: SA-* = the <sig-activate> surface's drafted copy. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. Furniture — "Open full map", "Cite this view", "Close
interactive map", the embed heading — is navigational chrome, never a row
(the batch-16 precedent).

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| SA-01 | /dossier/<path>/ | Explore on the interactive map | e133ac6650f241980671880165523a5d1c023966b1dde37c73e245d36e925a1b | pending |
| SA-02 | /dossier/<path>/ | The interactive map could not load; the figure and the places table show the same records. | a634933fd3b26dcc7fbf16f377c88d9b7d7c46c7ef5b219d50f9f7f9630782e3 | pending |

## Confirmation log

<!-- Operator confirmations append here, one line per row or batch-wide,
     dated with `date -u`. -->
