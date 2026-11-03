# Copy batch 13 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.53 (row 396, per-dossier downloads), the row needing new
     public sentences after batch-12 (B-2 "Batches + notice allowance",
     D-K5-1 = B-22 "as recommended"): the /dossier/<path>/downloads/ page
     wording — the lede, the no-slices line, the recipe note and the API
     equivalent — plus the explorer's "All downloads for this dossier →"
     link. Agent-drafted, pending verbatim confirmation.
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
| DD-01 | /dossier/&lt;path&gt;/downloads/ | Downloads for the {name} dossier — one file set per licence compartment (a file never mixes licences). {materialised} Every bundle's ATTRIBUTION.txt · LICENCE.txt states the captured terms and the operator-accepted basis verbatim (no withdrawal — a bad bundle is corrected by a new release, never retracted silently). Served from {mirror} as content-hash keys ({posture}). | 0e9f86c73466e52b66883ab659ea6bfcf9e475ca042023aa4287f788ec335907 | pending |
| DD-02 | /dossier/&lt;path&gt;/downloads/ | No materialised slices for this dossier in this release — {reason}. | a4fe8e4a07991231c5467c67dae78313363c2dd7baac1129818796c609094075 | pending |
| DD-03 | /dossier/&lt;path&gt;/downloads/ | {note} | 75f3a7fcbce8d5c3e8f5b3a70516c71563128d0ae93689b973cc0cfe45a5bfe3 | pending |
| DD-04 | /dossier/&lt;path&gt;/downloads/ | API equivalent — {endpoint} on the read API (see API & JSON twins) — {note} | 4b262434488486a111df6ce1e8f3aa12a827d35f1f843bf91712b7cd6de078ac | pending |
| DD-05 | /dossier/&lt;path&gt;/sources/ | All downloads for this dossier → | d8b2054187518e70032a8500dfe040eda3751dbc6aeb3f2968ca97ab754569d1 | pending |

## Confirmation log

<!-- one line per status change, `date -u` stamped; empty until the
     operator confirms a row verbatim. -->
