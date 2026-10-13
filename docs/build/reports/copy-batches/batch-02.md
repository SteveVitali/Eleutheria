# Copy batch 02 — agent-drafted page sentences awaiting operator verbatim confirmation

<!-- Created by P34.18 (row 221), the next row needing new public sentences
     after batch-01 (B-2 "Batches + notice allowance", round 10,
     2026-10-01T04:32:16Z). Append-only: rows are never deleted or edited in
     place — a correction is a new row superseding the old id, and a status
     change is recorded in the confirmation log below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` · `confirmed`).
Only `confirmed` sentences may ship (B-2); the `identifier-changed` page is
served by the renamed-routes barrier only after its sentences are confirmed.
N-5 ("This identifier has changed." `4f628b89a266`) ships by sha256 under the
notice allowance (`data-notice`), not as a batch row.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| title | /sources/identifier-changed/ | Identifier changed | f977c1febe06483b2f7a34f749a0e46b5bcf2b0976f8747ccadb2d54fc9896d1 | pending |
| GN-02 | /sources/identifier-changed/ | Go to the sources and licences page | 7ec0a13a8fb2ec58f929e7381d906a36eb29ab699287a447c973ebe9e34c7750 | pending |
| EW-01 | /watch/ | No upcoming decisions are tracked yet. | 0e52fe83116017c217a7b786a50e65adab8fd337afe3c2a4e6dcbde1971b60ee | pending |
| EW-02 | /watch/ | The watch is not yet connected to SIG's procurement and agenda data, so no upcoming decision appears here. | 8dfb6b4032fb00491e6372a52acf10d3dc9fab8ca5f392b7a5d93e9eac59a0b1 | pending |
| EW-03 | /watch/ | SIG does hold some dated records (for example federal solicitations) that will appear here once it is. | 25e2564c322720f4933a615b5ddc57cee6161f43214af0a916be1d8bbc37509e | pending |
| EW-04 | /watch/ | Browse the dossiers | 728354c650a3e3c8a6078c271ef11bb18a8a609d731e28fc79056a0505846b10 | pending |
| EW-05 | /watch/ | The watch fills in with a release once the procurement and agenda feeds are connected. | 755e11fee6b3fc605bfc6367ebd0d9308ecd41187e1c7c8530d96f77bdfe2b82 | pending |
| EW-06 | /watch/ | No jurisdictions to subscribe to yet. | 6d920fbc2237951f70f773938e30a30b55112ee5f9032e43b2817ff6b409c869 | pending |
| EW-07 | /watch/ | A per-jurisdiction feed appears once the watch tracks a dated decision there; none are tracked yet. | 0c431a96a3e2c2f1add6612ddfa23ce8dde6306d4d154c436130304398a37498 | pending |
| EW-08 | /watch/ | The watch section above names the cause — the feeds come up with it. | dfd6e8f889a1e324df4f5fe8bdc73e0cf66bb25477eadaab64058b022dd761f6 | pending |
| EW-09 | /watch/ | Feeds appear with a release once decisions are tracked. | c3bcfb770f42a54309fcc59708fbcca08916959f1a13c34025a22446d13aeca0 | pending |
| EW-10 | /watch/ | No evidence ranked yet. | 7c78bba5de2a802a05b2e1444d2928e5ac2b1741ee1cc2695c1f023b102f49ca | pending |
| EW-11 | /watch/ | Nothing is ranked for an upcoming decision — the watch is not yet tracking one, and SIG's artifacts are not yet linked to stored documents. | 22696dc4f526b4ff4007547df717fda48e4e43b5aee56248859e714ab806a13c | pending |
| EW-12 | /watch/ | The published artifacts this release carries are listed on the evidence page. | a2c8a196bff4c9c066deca5ce7126bb117b63bd01808f1801a30f001753ec617 | pending |
| EW-13 | /watch/ | See the published artifacts | c218731646bf5997d1103c897dd4f00e85f037d0014aaee7b60f6979fdb8c57c | pending |
| EW-14 | /watch/ | Ranked evidence appears with a release once a dated decision is tracked. | 27be090e373374edc6726b3b77982e581919be1b6d287c916ceafd2b47763765 | pending |
| EW-15 | /watch/ | No citation list yet. | b56b8e10362f1310d001148dc6f7da43c3eec3c52ff184c7504d41720fdbdc31 | pending |
| EW-16 | /watch/ | The citation list is built from the ranked evidence; nothing is ranked yet. | 5d6c7b9b6f700658e3132e7a2b32b602f94255583d71f66ed47b06ab5e8bdf4a | pending |
| EW-17 | /watch/ | The list appears when evidence is ranked for a decision. | ee31a3e11285e22c41608f7aef4ffccfb089eaadd3bd45fc341b20f6b52b2e7f | pending |
| EW-18 | /evidence/ | No document views yet. | 65e6de2d3edd3ae90545b46e6f3b958076ed89a43f44b284076155252688c455 | pending |
| EW-19 | /evidence/ | SIG has not yet linked a claim to a stored document it can publish, so no full evidence view is available for this build. | 19ab9b0109678acc80d25367d9057c0741c8a0c3910974bf4b0855317d2427ca | pending |
| EW-20 | /evidence/ | The artifacts the release does carry are listed below, grouped by source. | d536185988310155f15ce7dd5926ff370753cac16076adb9781a6a1fdceeb58d | pending |
| EW-21 | /evidence/ | See the sources | a8e68bb5e20cff52dae3d7eb1daffef9ee7ab65b2c36274664f80ca17f5c97ed | pending |
| EW-22 | /evidence/ | Document views appear with a release once claims are bound to publishable documents. | e7b28a8e4badc4732e3a3ecabdf7e7a2ada87c3fae6bba364a459e1fb5ba7802 | pending |
| EW-23 | /evidence/ | Published artifacts | b961eeeb80ef706ae2ba2aafc36a319a10a4141b19437329f9b854a61dd5fc37 | pending |
| EW-24 | /evidence/ | The artifacts this release carries, grouped by source. A run record is a build-time record, not a stored document. | 5bc519de844f396dc950a0bb9e50fa31c9fa77c25ac632c30f3848b0d6810686 | pending |
| EW-25 | /evidence/ | run record — SIG did not store this document | 6527be81f1aaf9909e213a9c4dcbd1cd8c89070a9ee0dd5651f3ec8ffb987f5b | pending |
| EW-26 | /evidence/ | the source's own link (recorded as a claim) | a4c8ad96484190ab70a9c41a74dc65f00a131ecf23da3debb5caa79ef46604be | pending |
| EW-27 | /evidence/ | No published artifacts in this release — the list appears once the export carries them. | ca58e07ca68745ac8be8b54ff787adc8131cd292264a0afb1d374d1fa92ffe7e | pending |

## Confirmation log

<!-- The operator's verbatim confirmation lands here at the copy-batch sitting:
     one line per sitting naming the rows confirmed, the operator's words
     verbatim, and a `date -u` stamp. Nothing is written until that sitting. -->
