# Copy batch 27 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P37.41 (row 465, R11-K13-UX10-4 — the per-source changelog:
     the /sources/<id>/changelog/ log page, the source page's changelog
     section and the page-B entry). Append-only, same convention as
     batch-01: rows are never deleted or edited in place; a status change
     is recorded in the confirmation log with a `date -u` stamp. Id
     prefixes: SCL-* = the changelog surface's drafted copy; PB-09 = a new
     page-B list row on /sources/<id>/. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. `{name}`/`{label}` name the slot the source's own fields
fill — the row records the template the element fills. Furniture —
headings, link labels, table captions — is navigational chrome, never a
row.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| SCL-01 | /sources/<id>/ | Changelog | ead07c84baac57a9542f388a07a2a5209456ce790b04251bc9bd7d179ea85cb1 | pending |
| SCL-02 | /sources/<id>/ | No changelog events are recorded for this source yet — the log is generated from the rights record, run records, release diffs, issues and corrections, each dated by its own record's clock. | 56c5cfa6c784de478330cda38b2ffa4097480135c401ae7fe2e374bb3c8bc873 | pending |
| SCL-03 | /sources/<id>/ | The full append-only log is the changelog page (index.json). | 9b74e64a37f7b81701a6aa81077024942f19169d72cf3e780058645598548101 | pending |
| SCL-10 | /sources/<id>/changelog/ | Changelog — {name} | c375346e064f2c2c5c76fa79fb623d0e81d4d1781832c43ff9c3a9b005eac570 | pending |
| SCL-11 | /sources/<id>/changelog/ | The append-only log of recorded change for this source — generated from the rights record, run records, release diffs, issues and corrections. Every date comes from the record's own clock (the basis column), never from version-control dates. | 439bcfebb2c9ed15525614faba36be505213dfc6ae02957e2a8225273bdd03a0 | pending |
| SCL-12 | /sources/<id>/changelog/ | History before {label}: rights decisions and run records only. | f30ff5ad45a00d48d9163fc111f55a83057f8ec8416a2cd8bb874c4a671e2edf | pending |
| SCL-13 | /sources/<id>/changelog/ | No changelog events are recorded yet | 351d7670a2f2f1047d3feaf80ddf212714646a0c6b1a864ccda1f93795f91e66 | pending |
| SCL-14 | /sources/<id>/changelog/ | This source's artifacts record no rights decision, run, release diff, issue or correction event to date. | 87288c7114bd2391b446f923ff9d96b8c074b26dbaba9ab8e5f63a3666042cbc | pending |
| SCL-15 | /sources/<id>/changelog/ | The source page carries everything this release does record. | ff0132570cef5c0f7d13410ae40dae3d7fcca460b69ca041d0a35ae162f56015 | pending |
| SCL-16 | /sources/<id>/changelog/ | Back to the source page | d9787d24d0c7954a085b5214f2ae44d55a1834a32de7217e2c868c727f314ea2 | pending |
| SCL-17 | /sources/<id>/changelog/ | Each recorded decision, run, release diff, issue or correction appends an event. | f60c050f01d4fba2a72ffa110f27ef24a8dd7d51f7bad970d0d1ee384ddc2339 | pending |
| SCL-18 | /sources/<id>/changelog/ | Date | 99c40ab405926cb5ad1def9cff4d7ce624f8f8abfff4e85f655347fcb949d08e | pending |
| SCL-19 | /sources/<id>/changelog/ | Event | 4e1f49a9c8ae8a158434e647c0c410352d718984a4fcd144d26cca3c394caa02 | pending |
| SCL-20 | /sources/<id>/changelog/ | Dated by | 93979349175ce6ea5f7431b0eb7e9602cace08af3bf25670f4a31b1aa66a4c5e | pending |
| SCL-22 | /sources/<id>/changelog/ | The machine twin is index.json; the release's cross-source diff lives on /changes/ and the source change feed. | 647306a3a96a56a25352283b3db497072da912beac9dd89394f8b0e7a5608dce | pending |
| SCL-23 | /sources/<id>/changelog/ | Every event is dated by the record's own clock — the basis column names which one; no date comes from version control. | e7da7a298773f277fdb0fe5f74f1a00b57ecdeb276933b17333e460576654a12 | pending |
| SCL-24 | /sources/<id>/changelog/ | Summaries render from a closed code vocabulary; the machine twin carries the same events. | 60e2e1fba47e67e2c9ee75738231808d3a78f42c1386a36d0308c590aa60bd4d | pending |
| PB-09 | /sources/<id>/ | Changelog | ead07c84baac57a9542f388a07a2a5209456ce790b04251bc9bd7d179ea85cb1 | pending |

## Confirmation log

<!-- Operator confirmations append here, one line per row or batch-wide,
     dated with `date -u`. -->
