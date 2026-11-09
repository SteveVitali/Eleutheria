# Copy batch 20 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P37.23 (row 447, R11-K13-GX-06b — entity pages B). Append-only,
     same convention as batch-01: rows are never deleted or edited in place; a
     status change is recorded in the confirmation log with a `date -u` stamp.
     Id prefix: EB-* = the entity hub's wave-B copy. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. Contract-verbatim strings (the ER disclosure, the
SIG-UI-080 withheld sentence) are record data, never batch sentences.

<!-- Supersession (append-only): batch-05 EN-01 ("Organisations, agencies and
     registry portals SIG records — every page cites the claims behind it.")
     is superseded by EB-01 — the contract-B record kinds publish entity
     pages beside the organisation-class kinds, so the lede names them. The
     superseded row remains in batch-05 unbound. -->

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| EB-01 | /entity/ | Organisations, agencies, portals and the procurement, funding, policy and event records SIG records — every page cites the claims behind it. | e23efe5d440dcf153b6d69bd32521c938c30c6aefb5818cb3a8495d5c8b7f970 | pending |

## Confirmation log

<!-- Operator confirmations append here, one line per row or batch-wide,
     dated with `date -u`. -->
