# Copy batch 21 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P37.24 (row 448, R11-K13-GX-08a — overview builder A and
     /graphs/**). Append-only, same convention as batch-01: rows are never
     deleted or edited in place; a status change is recorded in the
     confirmation log with a `date -u` stamp.
     Id prefix: GO-* = the /graphs/ overview surface's drafted copy. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. Contract-verbatim strings (the ER disclosure, the artifact's
`position_note`, the typed absence tokens) are record data, never batch
sentences; `{place}`/`{title}`/`{ovId}` pin template placeholders for
injected DATA (the batch-01 precedent). Furniture — nav labels, pagination,
table headers — is navigational, never a row (the batch-16 precedent).

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| GO-01 | /graphs/ | Static overview graphs — each answers one question over the release's recorded relationships. Node positions carry no geographic meaning. | a84060851efe3f95fbb03aaa16945866ef6055a29901278449bcc0cf08256c7c | pending |
| GO-02 | /graphs/ | No overview graphs in this release | 6c08aec191e04595e31603dd178854263a19ae1b0fc3b66c790021453cd6a73f | pending |
| GO-03 | /graphs/ | This release emits no sig.graph-overview/1 artifacts — an honest absence, never a hidden one. The entity pages carry the same evidence. | 7f8f2bb4d44b6106f684723e88a365e93837a78395645d005cd4dd620ff99137 | pending |
| GO-04 | /graphs/<overview>/ | Scoped to {place} — whole {title} overview. | c7fa72ee157d0b14063aa4d15465a368b21e8d3f7cea358bdc6ba1abbc8056a0 | pending |
| GO-05 | /graphs/<overview>/ | Downloads — per licence compartment: | 71d332850a5cc5844e69bc29599e5dd46511f223dd401650b7363c2ae37807a9 | pending |
| GO-06 | /graphs/<overview>/ | Drill down by place: | d86b9821771acfd9d9983779ce79c473a955e7c570fc55d48fcd33e28b1e071b | pending |
| GO-07 | /graphs/<overview>/ | Overview not in this release | cba23a3a442197567d8549b8cf1d0e63956ff88f684489fc06b6179dd8b2a555 | pending |
| GO-08 | /graphs/<overview>/ | This release emits no {ovId} overview — an honest absence, never a hidden one. The emitted overviews are listed on the hub. | a92a7e3d4423f49270c08af0e9cafde2b96a49f52a775d4e8affcc1d26b19e31 | pending |

## Confirmation log

<!-- Operator confirmations append here, one line per row or batch-wide,
     dated with `date -u`. -->
