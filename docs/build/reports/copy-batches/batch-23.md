# Copy batch 23 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P37.34 (row 458, R11-K13-WX-04b — watch feeds v2: the
     /watch/feeds/ directory's new feed-set sentences + the place/item
     subscribe lines). Append-only, same convention as batch-01: rows are
     never deleted or edited in place; a status change is recorded in the
     confirmation log with a `date -u` stamp.
     Id prefix: WF-* = the watch feeds surface's drafted copy. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. Furniture — link labels ("iCal", "RSS", "JSON Feed"),
the "Subscribe to …" lead-in and the how-to list items carried over from
the pre-batch page — is navigational chrome, never a row (the batch-16
precedent).

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| WF-01 | /watch/feeds/ | Every feed exists even when it lists zero items — subscribe now and items appear as SIG records them. | 22df19152beb4b0b110f8b0cd285673452bf936c482077e946cdf47b7a48559d | pending |
| WF-02 | /watch/feeds/ | All upcoming decisions | 7219771b4d7b5cabbe53e673a027357070185aff72fff4dfaa631da61555710c | pending |
| WF-03 | /watch/feeds/ | An item page's "add to calendar" link downloads a one-event calendar for that decision alone. | bad9ecf4f207734ff2dbb1b935ca26a3f316f8ca553524624908248f309630c9 | pending |
| WF-04 | /watch/feeds/ | These older per-jurisdiction feeds cover contract renewal decisions only, keyed on each contract's derived decision date; the scoped feeds above carry every decision kind. | a595e1cf0100bdc26d2e9c7acd8a9a140355e684c6d3aa0a49a84dba107ef7d3 | pending |

## Confirmation log

<!-- Operator confirmations append here, one line per row or batch-wide,
     dated with `date -u`. -->
