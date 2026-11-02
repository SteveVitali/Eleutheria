# Copy batch 09 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.48 (row 391), the sources table (UX9-3): the `/sources/`
     view family wording — titles, view names, column headers, facet/sort
     chrome, download and status-lane footer lines — is agent-drafted,
     pending verbatim confirmation (B-2, D-K10-1 = OD-07 a). The `/sources/<table>/`
     page value names the whole table family (the three views, their sort
     routes and the facet routes); `/status/sources/` reuses the shared
     headers. Append-only: rows are never deleted or edited in place — a
     correction is a new row superseding the old id, and a status change is
     recorded in the confirmation log below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish
gate scans every `batch-*.md`, so a pending row refuses the republish
rather than reading as untracked. The `data-copy` attribute binds each
rendered element to its row ids. `{placeholder}` fields are injected
DATA (dates, counts, hosts, licence ids), not drafted copy.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| title | /sources/ | Sources | caf85b0888d78f1f83771a07b25c3d30fa1210242f2fae6e5ae5d9a686602800 | pending |
| ST-02 | /sources/<table>/ | The sources table | 09e90d09cac2902cd7e7cc6379cfce36bc4298806a02cdfb8ae43a3db9f8d82d | pending |
| ST-03 | /sources/<table>/ | One row per source-registry row — values are as of this release; the current read is on the status lane. Every column is a value or a named absence, and sort links are pre-rendered pages — the ordering is in the HTML. | 3f9af1291f78c2561d139cc5fa329d05a8f1aab65aa4bfb1e30666aea1fcd516 | pending |
| ST-04 | /sources/<table>/ | View: | 1d016dda38423ba271aea0d5c5ef331722775d34c6de6fe5471751f689268a6c | pending |
| ST-05 | /sources/<table>/ | Overview | d4b1ea5708dd532930a85188b45aff6f0a3ed458500c7577e0127a538eb0d100 | pending |
| ST-06 | /sources/<table>/ | Runs & freshness | 5a4e969126748c17a706723d4a4ae363781d9e85e724e120c994da84c430cacb | pending |
| ST-07 | /sources/<table>/ | Rights & downloads | 47d57f067724fa592cc30eac36856275287042ea652d838d232bb61254ed07a4 | pending |
| ST-08 | /sources/<table>/ | Sort by: | 27ab0062ef43bf402763716a5aaf89d2f716e8d62bfbcca1dc9fbb8849add18d | pending |
| ST-09 | /sources/<table>/ | A–Z: | 0137a8c5c96da0bf4c37dd1d38983ee176653b12f62128254831ef0059b1088d | pending |
| ST-10 | /sources/<table>/ | Filter by one dimension | 92a5dacd564282adefd083149439ec31c3f1cbd62c807f650d2060c8c96c07dd | pending |
| ST-11 | /sources/<table>/ | Source | 0e570ca6fabe24f94e52c1833f3ffd25567022beb826fa16891f3322051bc221 | pending |
| ST-12 | /sources/<table>/ | Publisher | 21378545892f1fe2b0f70fd49b619f6c4b326f2748a03d23d9b0220053222d9c | pending |
| ST-13 | /sources/<table>/ | Class | 4f3a9bd003974a5ed8c9ad65d4aeda3b8a0db6fd903e36e83a3a950624b09bbd | pending |
| ST-14 | /sources/<table>/ | Geography | f3c73803dfc63c7d51184159d333c19641b4a798aa45ca790dc5f60520e30a94 | pending |
| ST-15 | /sources/<table>/ | Status | 920e413c7d411b61ef3e8c63b1cb6ad058d5f95f8b481dbafe60248387d8c355 | pending |
| ST-16 | /sources/<table>/ | Freshness | cde4eb3cc3d18df704626386aafa37337773c3b69abd901e1c820ebb24f3727f | pending |
| ST-17 | /sources/<table>/ | Published claims | 117fa97eac8845c007d74e0778f93440c51567f3c558441a115e1d650c640436 | pending |
| ST-18 | /sources/<table>/ | Download | d6eafe82359100423c93c5ce53c352c1b51ca1e699215fcec3f5c5dd9bf12d24 | pending |
| ST-19 | /sources/<table>/ | Last successful run | 81120703372a9ee7b9cc86d997b99d389594ee7799a8851afa1802a045b1f009 | pending |
| ST-20 | /sources/<table>/ | Last upstream change | c6d6d33af53484497896289ea768403568bd8647d31b0ac825e365b73f8cd46d | pending |
| ST-21 | /sources/<table>/ | Last change in SIG's records | 7a054a597de68f2231141bf17685085a47ee519ec554b6a0d9792c05a3b4ff4e | pending |
| ST-22 | /sources/<table>/ | Cadence | 316d43c021472bb1e64fe9fdcb409b0097adb3acc6d0254c6b22853787330a0b | pending |
| ST-23 | /sources/<table>/ | Runs | 848f54e89660cea4357644039ac5d7146f76c8e85df5c04076e08feb7e7547f0 | pending |
| ST-24 | /sources/<table>/ | Errors | cb702378f31507efa79a2a2c6046050bc9f578f149c88e3c0a3d9532ab4b5300 | pending |
| ST-25 | /sources/<table>/ | Licence | f3ec8e880a46c8a6fb105396ee5400124f828934a9dd68c668f796cf6d47b1c8 | pending |
| ST-26 | /sources/<table>/ | Redistribution | 29aa6c37f0425e3769f4b40be7d76487cc092f731a5f31770342d8969af85780 | pending |
| ST-27 | /sources/<table>/ | Ground truth | 1b07da8e9939c0064e202e538333886a93d1f414e14457aca43601bcb05f11a0 | pending |
| ST-28 | /sources/<table>/ | Download this table: CSV · JSON · Table Schema — the API serves the same rows. | 4e9a4590976505257826db74cc28fd754674eeefe6e204db5f4c4bec9fb553c7 | pending |
| ST-29 | /sources/<table>/ | Runs since this release and the current verdict are on the status lane — updated on a six-hour cadence, not a citation. | 607b18444315dac0d65c82d5a85ca60b766f17eaa35b23bdadff412e0363d941 | pending |
| ST-30 | /sources/<table>/ | Sources where {dim} is {value} | 7330a40da408ff9c2c5dc485cf7073ed5082d1971509889c4ba90babf799722f | pending |
| title | /sources/runs/ | Sources — runs and freshness | 6fa5a2ae2d96dac6ced55671abcb6880a7f672998d761aac9029612f899adc1c | pending |
| title | /sources/rights/ | Sources — rights and downloads | 299fe49e568c87eae981a8a072afb0a13182e0ba9067bbee71658cefd16db68f | pending |
| ST-33 | /sources/<table>/ | One-dimension filter — the full menu is below. No facet combination is pre-rendered; the CSV carries every row for multi-dimension work. | 88e18a871ff6ba814ac92beff25ea454b1a06965537351c214a8f6ecf60906af | pending |
| ST-34 | /sources/<table>/ | Pages: | 0f36bbc96bf26dbbc00740973db0e3b1d509ab24e0fe64ae9e90bea494b6f1c1 | pending |
| ST-35 | /sources/<table>/ | first | a7937b64b8caa58f03721bb6bacf5c78cb235febe0e70b1b84cd99541461a08e | pending |
| ST-36 | /sources/<table>/ | ‹ previous | a02ed4a2b620f9f3276fb50f9ffa1f0aa9f5bfa171549ba6dbf1cbcc5618f436 | pending |
| ST-37 | /sources/<table>/ | next › | 93d4f7f677800a6cce5425c8657605e40ebb454a76c20c5656e801a17bb730ac | pending |
| ST-38 | /sources/<table>/ | last | 3547cb112ac4489af2310c0626cdba6f3097a2ad5a3b42ddd3b59c76c7a079a3 | pending |
| ST-39 | /sources/<table>/ | Page {page} of {pages} — rows {start}–{end} of {total} rows | ba84cb051806f3004f11f71bfb223606b41905573e3a668deecaeac5b8b51d03 | pending |

<!-- P36.48 supersession notes (append-only): batch-01 SL-01 ("Sources and
     licences") is superseded by ST-01 ("Sources") — the `/sources/` title
     follows D-K9-3's rename; the sentence remains in batch-01 unbound.
     batch-07 SS-09 ("Last run") → ST-19, SS-12 ("Runs 7d") → ST-23 and
     SS-14 ("Claims 7d") — the status table adopted the shared row
     component's Runs & freshness columns (K9 C-12); the superseded rows
     remain in batch-07 unbound. -->

## Confirmation log

<!-- Operator confirmations append here, one line per row or batch-wide,
     dated with `date -u`. -->
