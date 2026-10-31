# Copy batch 04 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.35 (row 376), the next row needing new public sentences
     after batch-03 (B-2 "Batches + notice allowance", D-K4-8 / OD-07:
     the JUR-05 corrections-log wording is agent-drafted, pending verbatim
     confirmation). Append-only: rows are never deleted or edited in place. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The migration entries' ids are carried in the
rendered correction block's `data-copy` attribute (`data-copy="MG-01 MG-02"`
on the `li`, in order: what_changed's drafted half, corrected_value).

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| MG-01 | /corrections/ | Dossier pages that each combined two places now answer with a split page naming both; each place has its own dossier. | 744a4e25d4329d82af4afed5d32cdedc81016853fc9462427af73a97e3c3b1b5 | pending |
| MG-02 | /corrections/ | a split page naming both places, each with its own dossier | eb0675ee04cacda7abe57be8dc82b71f3e3e57c80991d3e4081ed9440b762d44 | pending |
| MG-03 | /corrections/ | Records shown under one country's dossier were found to be located in another; the old pages now explain where the records actually sit. | 65a411f802b09063cb737c8baa214209ceb94a6cc21cfbb91892284173c6ad15 | pending |
| MG-04 | /corrections/ | a correction page naming where the records are now | bbfaf8ca7d077b4d8bbaf4736b8ec04ee18ad64e8ec734b9654c8bcf356ab84d | pending |
| MG-05 | /corrections/ | The 'unresolved' bucket is now the 'Not yet placed' data-quality report; records are never guessed into a jurisdiction. | 4fdd5d328782a6a67527a763f350eeec035c160d4ed043f95747da8287617384 | pending |
| MG-06 | /corrections/ | the 'Not yet placed' data-quality report | c2b6a9584f4655ba9e1c80d2b19fdf919fe7ef1c5a0abfd41c5176500caf55af | pending |
| SL-MAP-04 | /map/ | Static overview | 88af70b02214bc088f2e0bb0b2382e62c84e7f3f0c342b658f3e01d0e892338a | pending |
| SL-MAP-05 | /map/ | A build-time static rendition of the located records, binned so no single point implies more precision than SIG published. The places table below is its tabular equivalent (SIG-UI-037). | 10f757af79697bf56d93762cb3e15e8806323a0c45bdc17101cb2a0268ba18a9 | pending |
| SL-MAP-06 | /map/ | This export does not emit the drawn overview figure — the places table below carries the same counts (SIG-ENG-042: an honest absence, never a fabricated map). | 3aa1615b97537fe241427f65a8699b73efc06ae174e6bfb2ab733e5c29402a1c | pending |
| SL-MAP-07 | /map/ | If search cannot be reached, the first letter of a place's name finds it in the A–Z directory. | 5e7d6be4de898d968406c6eace6982fbd8d5d5b15dc11d70857d7499038c636c | pending |
| SL-MAP-08 | /map/ | Every jurisdiction SIG has located records in, with its own full site list — a paginated page per place, the interim per-record link target. | 5403595de1b89b4d19873d47c58718e5ae432e211aa1687ae8e5f0afbca2c972 | pending |
| SL-MAP-01 | /map/ | Every published record placed in {name}, grouped by licence compartment — the interim per-record link target (each row answers #{key}). Coordinates print only at the published precision. | c0c6a0f4046a8da3fa56d12711678094a805af5b1c424de5055c6ad82ae6b682 | pending |
| SL-MAP-03 | /map/ | Licence: {licence} | 478e20af399b5e3bfbe4391dbcae571323eb1be23c732a859985f47bb1ffe12d | pending |
