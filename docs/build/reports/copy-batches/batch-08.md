# Copy batch 08 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.47 (row 390), the next row needing new public sentences
     after batch-07 (B-2 "Batches + notice allowance", D-K10-1 = OD-07 a:
     the `/sources/<id>/` page-A wording — headings, absence states,
     disclosure texts and conduct notes — is agent-drafted, pending
     verbatim confirmation). Append-only: rows are never deleted or
     edited in place — a correction is a new row superseding the old
     id, and a status change is recorded in the confirmation log
     below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish
gate scans every `batch-*.md`, so a pending row refuses the republish
rather than reading as untracked. The `data-copy` attribute binds each
rendered element to its row ids. `{placeholder}` fields are injected
DATA (dates, counts, hosts, licence ids), not drafted copy. The
`/sources/<id>/` column names the page family.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| SP-01 | /sources/<id>/ | {lifecycle} — flags: {flags} | 0a8579b21915160cad45f413237d95ba268a3dc9fb51c1dfb6d008ec35656e7f | pending |
| SP-02 | /sources/<id>/ | runs since this release → | 7227584efac039aa0d3da969333b535c33164718114a433fcad10bda511c2284 | pending |
| SP-03 | /sources/<id>/ | SIG holds data from this source, but no record of the run that loaded it exists. | 89fae7b1a647aa81170c36ab313a3fc2d57786439ea922ceb686d0f2757b0ff8 | pending |
| SP-04 | /sources/<id>/ | At a glance | 46b396c85919af7dd3a4ea3a2792a437365a5fce2a4ae023a4d0526954813676 | pending |
| SP-05 | /sources/<id>/ | Publisher | 21378545892f1fe2b0f70fd49b619f6c4b326f2748a03d23d9b0220053222d9c | pending |
| SP-06 | /sources/<id>/ | Lifecycle state | 6ebd3627521308c3deef3b44ff393662171516b381a4c6c613de3833f1037f33 | pending |
| SP-07 | /sources/<id>/ | Raw-bytes lane | 3994e7d03c309a418b8212f9c4bcad9d785da1805ca6d45a8fedc9142eeedcc5 | pending |
| SP-08 | /sources/<id>/ | Published claims | 117fa97eac8845c007d74e0778f93440c51567f3c558441a115e1d650c640436 | pending |
| SP-09 | /sources/<id>/ | Last successful run | 81120703372a9ee7b9cc86d997b99d389594ee7799a8851afa1802a045b1f009 | pending |
| SP-10 | /sources/<id>/ | Last upstream change | c6d6d33af53484497896289ea768403568bd8647d31b0ac825e365b73f8cd46d | pending |
| SP-11 | /sources/<id>/ | Last change in SIG's records | 7a054a597de68f2231141bf17685085a47ee519ec554b6a0d9792c05a3b4ff4e | pending |
| SP-12 | /sources/<id>/ | Dossier contribution | d54fe82818a65bc972d7d09ce3ef340678c02495e059c9c1e9868442a22dd626 | pending |
| SP-13 | /sources/<id>/ | About this source | 6d86dc29409c936251040d9187582ffdb4887eaf01cdf5d6b89be01355d32b8a | pending |
| SP-14 | /sources/<id>/ | description pending review | 338bb20043bbff8a485603f8592321b80399a425289693ba52c5c92d7686fe8c | pending |
| SP-15 | /sources/<id>/ | Technology classes | 4bd43e59da699a4adebfe9b1715bab283afc6b1312fa2c424e9aac5cf8afcd70 | pending |
| SP-16 | /sources/<id>/ | Declared geography | cee3dea4ad22a04766cd4646b8c4e07d3c32f86d1879623abb3eda6ecf4bf251 | pending |
| SP-17 | /sources/<id>/ | Volatility across this source's published claims: {volatility}. | ceae3cd415a4a98ac5ca637564f5b7f5626dfe3c9d5188ba7636d14de3cb1c36 | pending |
| SP-18 | /sources/<id>/ | Ground truth (upstream) | d3c26f8cb21ae1b45de0d620a1cb97d25b929b7a79b4093b98898e506b8fe54f | pending |
| SP-19 | /sources/<id>/ | No upstream link is recorded | 4d290a929010eee596d1665e09c66b9c43a60b60eac814d8a343031a6b9883fa | pending |
| SP-20 | /sources/<id>/ | SIG has not recorded a homepage or terms URL for this source — an evidenced absence, not a broken link. | ea249d6cfdeb9700ef27f0190abbf8fabfeb9dc3b3f7d914a3eb15e59140ba96 | pending |
| SP-21 | /sources/<id>/ | The rights record below says on what basis SIG publishes from this source. | 2f48569e650e2bb01870d43c5ee71efde277d8bbd8620cf6e4b01a51cc02a81c | pending |
| SP-22 | /sources/<id>/ | Back to the sources table | 95fe080952f66c117fb769a630b553ac512ced9b04636591cb3002eaea85daef | pending |
| SP-23 | /sources/<id>/ | An upstream link appears here when the registry records one (S-6 checked before it publishes). | a785ceec669733d47cbe064aa14b3b462b9cc8b278504e4c4c8d2e039ce3a592 | pending |
| SP-24 | /sources/<id>/ | Upstream page — {scrubbed_url} (path withheld: the full URL is not publishable for this lane) | e6977d345f10cebcda5cd7d87f86bc68bb93434cb26892aae2d1a7a4eb4f2992 | pending |
| SP-25 | /sources/<id>/ | Terms page — {scrubbed_url} (path withheld) | 4450d2ef89b047543b9d68fc140b2cddf7abab78f01179c466820ec56a62a5cc | pending |
| SP-26 | /sources/<id>/ | — terms not captured by SIG | 6c63095c2edb0265a165bbe840e0113c409dd230a9bcdd4da7fa5143539c49ed | pending |
| SP-27 | /sources/<id>/ | Targets | 27445f6ab61d9a5cea1584df4a98277b77e1d091fb67c143d4d40116468dcdec | pending |
| SP-28 | /sources/<id>/ | This release's artifacts enumerate no per-target rows for this source — the section lists target endpoints, tenants or slices once the targets artifact ships. | 7702fdc73b94391cadb19a00be501e9c5478e4315abf67086c429f87221558d9 | pending |
| SP-29 | /sources/<id>/ | Target | 978354db0c00fc78c3a5524f462a73bc425df3fb2767e51a5f46352ae26ae6f9 | pending |
| SP-30 | /sources/<id>/ | Host | 4a823118b9ba8baa2f47489c0716f52755368e3e3c2c26d60736ccfa1bb21b5e | pending |
| SP-31 | /sources/<id>/ | Declared jurisdiction | 0882b2433abd5ecbc51e025fa0d5e42f3e177a5abd550b5e93480468c2fc5bf8 | pending |
| SP-32 | /sources/<id>/ | Observed at enumeration | 4d13410e7ea090ed15cb0e602e4e014888c69a4485c165c44744cb0150f45513 | pending |
| SP-33 | /sources/<id>/ | Last capture | 62d93f7efa4cc19844ac62f050a9a88dfa53f24d6a7e814e8d50dc7d5e4ce070 | pending |
| SP-34 | /sources/<id>/ | State | a3b50c476732c7409d297c3d7d0e23569fee5e08318553ae76041ab5fe60582e | pending |
| SP-35 | /sources/<id>/ | Licence and redistribution | 5e0ce65eeca8bdf402460dcc2550c45d08e0a7b7830c5da40a6f9bc8aa304b12 | pending |
| SP-36 | /sources/<id>/ | Upstream licence (as declared) | bcc68a07a5e06f77810e291d6212d61f5ff13a51ac9007edc281295ef695b107 | pending |
| SP-37 | /sources/<id>/ | SIG's publication basis | 0c71d630c50f984f8bfe97ecb1cbc3a609b7cac70abefd151370a499a3f03770 | pending |
| SP-38 | /sources/<id>/ | {lane} — {basis}; recorded under {authority}. SIG publishes facts, not a licence from the publisher. | f0b69c40bc21850f6253bdabb33be1fb7916c3cd7dea9658b0679228d4fdf6d5 | pending |
| SP-39 | /sources/<id>/ | Derivative redistribution | e827bd01743c2ef13b6c2d6b85a77ca4e340a83a9c9f4cc5ea62c15274abdf58 | pending |
| SP-40 | /sources/<id>/ | Required attribution | c5ece9907982d94e3e13d1688d07ae788010071cf0a4061c5aa759318f983d2c | pending |
| SP-41 | /sources/<id>/ | Part VIII class | 0bfdf83e860f9e248c5cec3d30519d9a3a3899b3f27a3210e0ac8627c94aed37 | pending |
| SP-42 | /sources/<id>/ | Attribution for this source is being corrected; see the source's own terms. | 6ee2dd66e2885e1050f919bab90b9a34c2958ec8b7bf7f2f80a7b90070ea5532 | pending |
| SP-43 | /sources/<id>/ | Rights review record | 0ba24595b9601b9f4134cf7b463463079df09622973971c0ba2cbc4723ac6c99 | pending |
| SP-44 | /sources/<id>/ | Decision basis | 388fb0ebbd5ef738a34d30b89b7188500957bbc6e0120c60667f9d4ad9268856 | pending |
| SP-45 | /sources/<id>/ | Reviewer | d29f46772c4aaacbbc35c3da380dcc9dfa2df19fa3992bdf6e725a2e09abd53b | pending |
| SP-46 | /sources/<id>/ | Decided | 30ba702eee51c2a58e8237ce27c7d2caa308ce1341c50226149c40b1ea79d5df | pending |
| SP-47 | /sources/<id>/ | Terms reviewed | 413330266fa064b626c4a70bf17586e9e69a730cb9e95faf826905d9f9511e88 | pending |
| SP-48 | /sources/<id>/ | Approved for ingestion on {decided_at} under a standing instruction from SIG's operator (GL-GATE-07) to "err on the side of approving" sources awaiting rights review. A maintainer applied it under delegation. No per-source legal review and no counsel opinion is recorded for this source. SIG publishes facts from it on its own basis, which is not a licence from the publisher. | 94916beb20719ab7a82dcb88e63078d59afe878be129724f75bcc413425cf46e | pending |
| SP-49 | /sources/<id>/ | This approval went beyond the rule as recorded. A fresh decision is pending. | 338546182b43d4e8605208cb0315db5482b759c70dbf8b2be955a0c4f601d795 | pending |
| SP-50 | /sources/<id>/ | The publisher's captured terms say: "{excerpt}". SIG has not yet withdrawn this source's data pending a new rights review. | a4aaa54f36c22d802fbb88abd60c4cbe370c39aba6095549f6368496bb5db242 | pending |
| SP-51 | /sources/<id>/ | Reviewer recorded as counsel. This was reported by SIG's operator; no written counsel opinion is on file. | 808fb77d63e522b79081bf60a76014093be342390f4847a15471d1d9474a8c73 | pending |
| SP-52 | /sources/<id>/ | Approved on {decided_at} after review of the publisher's licence ({spdx}). | 23c044e11cc9aa5a319becab5f46567e854a070c29c2889a4e2f707893e2121b | pending |
| SP-53 | /sources/<id>/ | The registry records this approval; no rights-decision row is on the published record for this source. | 78b8cfc7c2171d33f01b5dc7f4d6a3c338ef555de7d65a20b686236bff3989fb | pending |
| SP-54 | /sources/<id>/ | The publisher's captured terms conflict with what SIG publishes; a new rights review is pending. | da1fef149b169b9ff3548a1bdd632333be1dd70da3cbc5d6e1cbf66bc1770300 | pending |
| SP-55 | /sources/<id>/ | Collection conduct (observed) | bb7d66aaef2104a0ac61ae9a269fff62d322fc835ffe2a332af226cf39dd4d3b | pending |
| SP-56 | /sources/<id>/ | These rows come from SIG's own run records — never from the registry's declared crawling posture. | fa63427eb22d3ab365e84ea9e5b3b8e2526a47112b9be7c039e4173d1296f973 | pending |
| SP-57 | /sources/<id>/ | SIG holds data from this source, but no record of the run that loaded it exists. | 89fae7b1a647aa81170c36ab313a3fc2d57786439ea922ceb686d0f2757b0ff8 | pending |
| SP-58 | /sources/<id>/ | No executions are recorded for this source in this release. | 3b1d7f2f7844ca778679734ddbaa51e461e0d0794f1f27c76a36e57e39993f12 | pending |
| SP-59 | /sources/<id>/ | SIG fetched {count} page(s) on {host} that the site's robots.txt disallows, under SIG's crawler policy {decision_ref}. | 0bab249da170e8de23daadd881f87444c62204e70191049ae4476aa9b2f1b5ba | pending |
| SP-60 | /sources/<id>/ | Registry record only | 7b2b99079bca4792d1be3e6034d76b5bbedad5eb7d191078475ed62d40668169 | pending |
| SP-61 | /sources/<id>/ | This page carries the registry record for this source — SIG publishes no runs, captures or records from it. | 17c24ed0cdab758f7ba9af973bea4f4c50caf35165cf3caf1d523d96d2786ba7 | pending |
| SP-62 | /sources/<id>/ | Status | 920e413c7d411b61ef3e8c63b1cb6ad058d5f95f8b481dbafe60248387d8c355 | pending |
| SP-63 | /sources/<id>/ | Reason class | 1e2025b4195759178db8e47f91c2c0827c64565fdd04504b67b2d347c7c2906f | pending |
| SP-64 | /sources/<id>/ | Publisher | 21378545892f1fe2b0f70fd49b619f6c4b326f2748a03d23d9b0220053222d9c | pending |
| SP-65 | /sources/<id>/ | Upstream host | 149a09de3df8ceeb03f5589f328389f440d1b7a16b1e8984171177968706d921 | pending |
| SP-66 | /sources/<id>/ | Lane | 559263857b40b5a9bfe31255fdd369afa4226581ea9f5140fdf8baf18645f8e6 | pending |
| SP-67 | /sources/<id>/ | Not yet approved: waiting for a rights review. | 96000fbbe93fe9330504e9cc1f6be22f524d45a4209772536b9f0ac3729c18c3 | pending |
| SP-68 | /sources/<id>/ | When a rights decision lands, this page gains the full source record; the status page lists this source only as a count (D-J3-11). | 30e00fb7f8ca78d657d3e957748fd747a91f9b0444139bd18c0604e6fd0fc9df | pending |
| SP-69 | /sources/<id>/ | SIG's registry states that SIG honours robots.txt for this source; the run records above show otherwise. A registry correction is pending. | 6a926b7cce734ed083c58047ceda7a132cbc45db6942652e5ce6998f15384adf | pending |
| SP-70 | /sources/<id>/ | a recorded quota stopped {count} execution(s) early | 4acba1aa355b786d19436221e75314ce33ae2b20c534dc4df8b8c31fffea3b1f | pending |
| SP-71 | /sources/<id>/ | a recorded byte/time budget stopped {count} execution(s) early | 37094077f2679fe701a14654cd20b8c0197584e5a7aac70b1a87deaaa04353d9 | pending |
| SP-72 | /sources/<id>/ | Crawler identity: {identity} | a0eb0bd18cf160e4b981b3b978e67a4ec311e53469ad0454b395d9518d0821fd | pending |
| SP-73 | /sources/<id>/ | Cadence and freshness | d34776aeb547269a2468c42da0e7f45e1bc352060095905cad4d093d38e053b2 | pending |
| SP-74 | /sources/<id>/ | Declared cadence | 6e0b9f953d9a2b3a884e10af4b4bc1d712d803ca3ecfe294f2f3044d9365163d | pending |
| SP-75 | /sources/<id>/ | Observed cadence | 2b22eb1426d1d79ccaae2dae66d605b7537aa2725df6ff8bff587868589c5e98 | pending |
| SP-76 | /sources/<id>/ | Freshness verdict | ce630fa4f84bbb0e37aee2c65abe56009a8444de7e3922e1a60057bbb7f25587 | pending |
| SP-77 | /sources/<id>/ | Staleness | 0c4be2488706ef09a26c21ef876a6f1b126d99c694b4ad1cb5a215e89a3eae39 | pending |
| SP-78 | /sources/<id>/ | Recorded runs over time — one marker per execution (the conduct table above is this figure's text equivalent). | 95f73a2300b49ddc0a99fc4084f0ea2f78e27c3d5938a8518cb9b479a50a5f70 | pending |
| SP-79 | /sources/<id>/ | No drawn runs strip in this build — this build carries no static figure artifact for this source (a publication state, not a finding); the conduct rows above carry the same recorded facts. | 20c2c0edfc18237fcb6126faace67bf7fbffbc0074363d5f8cbc33f0df243724 | pending |
| SP-80 | /sources/<id>/ | Runs since this release and the current verdict — live on the status lane: a different clock, never a citation. | 064e4c344f2f5b55c6f04c0daf774ded52795f6208931a9ff16092660b3cc5bf | pending |
| SP-81 | /sources/<id>/ | SIG decided not to ingest this source; the refusal class is recorded above. | b2123ea10e8043fde0c9794b3b47567a005184ce3ea3c110dc666c0802065c64 | pending |
