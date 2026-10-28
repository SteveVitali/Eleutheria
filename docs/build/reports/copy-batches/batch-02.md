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
| SL-20 | /sources/ | Corrected {correctedOn}: earlier downloads credited some rows to the wrong source. | 4ce52f1626dfcf196483636d14ac3ca22d28ce9fad870ddc599be2d0c9dd83f9 | pending |
| TB-01 | object/sig-public | The download set published on 2026-09-27 is not served publicly: earlier downloads credited some rows to the wrong source; a corrected export replaces it. | a4137447e87bddb512a863a0e15f85dbbbff45c076e8c3c3746f8b8cb4ffb42d | pending |
| RD-01 | /research-dossier/[slug]/ | This dossier rests on non-live evidence — {detail} — nothing on this page is a live capture; every fact names how its bytes were obtained. | 16005b822537c34942e70ccd969c4b00923ba53d74047ea6d0acb74e442c7864 | pending |
| RD-02 | /research-dossier/[slug]/ | Research dossier — {reviewLabel} — an evidence-complete twelve-question portfolio, distinct from the inventory overview. As-of world {world}, belief {belief}. | cc46b1a3772a36c8947c4787aada2726ac85ad215a18262f032a50987d720994 | pending |
| RD-03 | /research-dossier/[slug]/ | Licence {licence} · permalink {permalink} · as-of world {world}, belief {belief} | f8ecc1a7d3e3f8592aaf3b01aa0e19a22659d8cbd9b769c75c8cfa652f489994 | pending |
| RD-04 | /research-dossier/ | A research dossier exists only when a packet was authored for it — absence here means none is published, not that the questions have no answers. | 59fd0815e8902fc6f96fe8e8e702df0c7032dab0ccc807ab7147d485b9d41830 | pending |
<!-- P35.25 (R11-L3-CP4, SIG-CONF-014): ST-11 is the drafted S6 A-20
     lineage-basis disclosure — the /status/ sentence staged for the
     ticket's queued, not-yet-run L2 live leg (the OM-20 pre-authorised
     registry declarations + claim-lineage rematerialize — also queued).
     It is drafted + pending like every batch row, and its
     confirmation belongs to the same sitting that runs the legs — the notice
     describes the post-rematerialize basis, so it must not ship early. -->
| ST-11 | /status/ | Corroboration counts and identifier matching now require declared lineage; records with no declared lineage are unclassified, never independent voices. | c751850d6b030f04c86b887026d5e42fc97e0d4341668d31b5c3afec02f17573 | pending |

<!-- P35.40 (TX-11, SIG-TRANSP-002/026/027): the /sources/ "How SIG counts a
     source" block — the authored sentences are pinned; the numerals are
     {Figure}-bound data (manifest-listed transparency/counts.json pointers)
     and the per-state predicate text is emitted {entry.definition} data, so
     neither is drafted copy. SC-02 pins the {fmtInt(…)} placeholder verbatim
     like every template row. Added 2026-10-20, pending. -->
| SC-01 | /sources/ | How SIG counts a source | b0db02ead2abed547c4e77d78421b04b7e68aa16f9ff511e6d702d7225f96e03 | pending |
| SC-02 | /sources/ | A source is exactly one row in SIG's source registry — {fmtInt(sourceCounts.universe.count)} registry rows in this release. Connectors, capture hosts, mirrors, and tenants are attributes of a row, never sources of their own, and the counts recompute from the emitted rows in the source-rows artifact. | eb527a84df9741694a721d69dc7ab09db51c58dfe6e8d2118973b3e5ed2129ae | pending |
| SC-03 | /sources/ | The lifecycle partition | f93188b0511d6851235c414f6272d0854b995132e081be4da8fc0dab0225d4ca | pending |
| SC-04 | /sources/ | Every registry row lands in exactly one state; the first matching state in precedence order wins, so the six states are a partition — they sum to the universe exactly once. | dd8a78a7e4c8d69cd40a630e0a7d70b4b4be9d819b562714ef08bbbada64e50b | pending |
| SC-05 | /sources/ | Counted alongside the lifecycle | 14daac46ed92d0c5ab6d8ac01d731f19dc897d4f15912a09f9a0bb0435b109bd | pending |
| SC-06 | /sources/ | These predicates count the same registry rows again — each is an independent named attribute, so they do not sum to the universe. | 86c8204460e72e9594a04978edd90d589cab35edf5982b10c8292771a7efd811 | pending |
| SC-07 | /sources/ | Identifiers that are not sources | 143f1b15498acbe5247bc870d4ba0fe11885ed8fc781af5e011c40d80f1bbd57 | pending |
| SC-08 | /sources/ | These identifiers carry data in this release but have no row in the source registry. They are anomalies — listed here and never counted as sources anywhere on this site: | e83a9d2af96243c47794fd324a0cc1c3877e6e43b47ca4725bcacad6ee281a39 | pending |
| SC-09 | /sources/ | The licence table below lists the sources SIG publishes rows from; the lifecycle partition above covers every registry row, including those SIG is gated from or has refused to collect. | 18372b1a9f5d8d43dfdf4118cd9a3d9f3859453afdfceaed5146ff0b45819ec6 | pending |


<!-- P36.22 (UXK14-3a, SIG-UI-086/151): the five-part typed empty-state
     expansion — every `EmptySurface` now names a real cause and carries
     the nearby/change sentences the pattern requires — plus the
     sig.error-page/1 five-part error-page sentences (404 nearby/change +
     the search/status recovery labels per page, 403/410 the same, and
     the new /500/ set). The state/missing/action sentences carried over
     from the P34-era copy are bound only where they were already tracked
     (the EW-* rows and NF-01/02, FB-01/02, GN-01 reuse); CK-* binds only
     the sentences THIS row drafted. `lib/empty.ts` page cells mark
     dormant surfaces (no page renders them today — the sentence lives
     in the copy table until a surface mounts it). Added 2026-10-28,
     pending like every batch row — an agent never confirms copy (B-2). -->
| CK-01 | / | The sources page lists what this release has collected even before a dossier is ready. | 6a431ca0daeb0ccc077ff4ad939e765de89e9025570e14758947737a0d372aeb | pending |
| CK-02 | / | See the sources | a8e68bb5e20cff52dae3d7eb1daffef9ee7ab65b2c36274664f80ca17f5c97ed | pending |
| CK-03 | / | A jurisdiction's dossier appears here once a release publishes it to a releasable standard. | 7fa06cd82f7602358daa61f612e9c66933e1974a5be2610ecf14e95fbd8ad73d | pending |
| CK-04 | lib/empty.ts | The sources page lists what this release carries even before counted quantities are published. | aa95d8438cc15a99c8c516e0d61668d578744c9a804ca031ab34b5a711c8ee36 | pending |
| CK-05 | lib/empty.ts | See the sources | a8e68bb5e20cff52dae3d7eb1daffef9ee7ab65b2c36274664f80ca17f5c97ed | pending |
| CK-06 | lib/empty.ts | Counted quantities appear here once a release publishes them. | 324335bd546a270b9d39692de1a10b4b73917ad9ed10531f70a76b3e3d997866 | pending |
| CK-07 | /dossier/ | The map's located records cover places that have no published dossier yet. | 6e60b6bc4a0b4b4695a68eb4b2dea6c5c0321db0233b6c7bf1295681b9e5f22e | pending |
| CK-08 | /dossier/ | See the sources | a8e68bb5e20cff52dae3d7eb1daffef9ee7ab65b2c36274664f80ca17f5c97ed | pending |
| CK-09 | /dossier/ | A dossier joins this index when a release publishes it. | 31382387f27029b1d01dc1ec60e689ce871e8b2cc598bbea436c6f285579e46a | pending |
| CK-10 | /map/ | Records without a published point are listed below the map when they exist. | 9bf41a8942d8ab119b59989e83b83b5e9870f6935e426c5f6c0aae7796799eba | pending |
| CK-11 | /map/ | Located assets appear on the map as releases publish them. | fc47cd470e8c7e12f5cfc8e25e3b9d3715515299a9a30da9d88f483c42eb3a36 | pending |
| CK-12 | /map/ | The located-records table below lists what is published for this view. | 1aecea1464c8faea8f118c285ba29987a39d9033878c721f5f93371d14cd9c9f | pending |
| CK-13 | /map/ | Browse the dossiers | 728354c650a3e3c8a6078c271ef11bb18a8a609d731e28fc79056a0505846b10 | pending |
| CK-14 | /map/ | Density bins appear with a release once they are computed and published. | 19bb044b3c4388daabf0620c6978ba0675dd14d082b362deddcfd81aa43d220e | pending |
| CK-15 | /map/ | Located records appear on the map above when the view has them. | b42f229c63db5e0a658abe89c283dc5d66017a09db5fe013fd234ed0528f0a94 | pending |
| CK-16 | /map/ | This list fills with a release when records carry a withheld or unknown point. | 78465f70da8100a0fc6a5c8614bea000cfdd53c42620be9d72fa2d0e66989977 | pending |
| CK-17 | /network/ | The dossiers name the sharing partners SIG has recorded. | 12212d957c2fecbc97abcfc606fa36f62500a00d7d9cd2629a5ac6f3fb88d55a | pending |
| CK-18 | /network/ | Browse the dossiers | 728354c650a3e3c8a6078c271ef11bb18a8a609d731e28fc79056a0505846b10 | pending |
| CK-19 | /network/ | Sharing and access edges appear here once a release publishes them. | 7e73b8665214a01a85b16e37ad9a99e0e2c855b842666fa9d57343defe021b30 | pending |
| CK-20 | lib/empty.ts | The network view lists the sharing edges that are published. | feb8152943ffbe77ff454069fc4417f59d4daf5456c4435e6704dd8140db2c4b | pending |
| CK-21 | lib/empty.ts | See the methodology | 1d55a493700889628ce86ba0629231a40e60c4442785bbd48d477990e011ef96 | pending |
| CK-22 | lib/empty.ts | Network statistics appear once the resolution review that makes one honest passes its gate. | 5db7e449b41cc07a82e463e352599e89e4a49ff32301aac2373c522673686e16 | pending |
| CK-23 | /network/ | Other access kinds may already have recorded edges for this view. | b87bd3c364e847812f13b0969b95e103554fb8c72bf2e85daab1add62e9a2ec6 | pending |
| CK-24 | /network/ | Edges of this kind appear with a release once SIG evidences them. | ec693a92271ca09db1cc4d5e335d956fae5d301389a3d1fc674884d230c70ccf | pending |
| CK-25 | /network/ | Published access edges are listed for each view above. | de70b0252f70255485ddf78e45de774d76105dccfb77d75824511c3278daad88 | pending |
| CK-26 | /network/ | A closed path appears with a release once the reachability work lands. | 39cd779e2fcb5c65bf871fe2a929ff450d4d67d57ed8ab3abdad7d648f695921 | pending |
| CK-27 | /data-freshness/ | The sources page lists every registry source this release covers. | 1aba0bfe2f93a5aae98d83b7bf0dde36b5a3e8814638e3b02b6aa314b1eb0714 | pending |
| CK-28 | /data-freshness/ | See the sources | a8e68bb5e20cff52dae3d7eb1daffef9ee7ab65b2c36274664f80ca17f5c97ed | pending |
| CK-29 | /data-freshness/ | Freshness rows appear once registry sources carry a freshness record in a release. | 929db135d6709ea5555ae5ff4b11b08ccad57c0969620468e01639278982c46e | pending |
| CK-30 | /coverage-metrics/ | The dossier index lists what is published for each jurisdiction. | 51c1fb54f11522197aae601452691ade5774179684ef2222148fe5e0ac0a478e | pending |
| CK-31 | /coverage-metrics/ | Browse the dossiers | 728354c650a3e3c8a6078c271ef11bb18a8a609d731e28fc79056a0505846b10 | pending |
| CK-32 | /coverage-metrics/ | Counted quantities appear with a release once they are published. | 9eb22211b49fb7c669ccfacf44065e9809d0c0750670f092392cb23fa2d4e9a4 | pending |
| CK-33 | /corrections/ | The methodology names how a correction is recorded when one is needed. | e2178471cd622d4fb44657c359fa2b88ee264c224de8b405b83608c1ed3ec0b9 | pending |
| CK-34 | /corrections/ | Each recorded correction lands here as a new entry with a release. | 278b83257b62f84f77cbd400a8a1999874f9ce9ff9a89cf4712f0139495466ea | pending |
| CK-35 | /research-queue/ | Every dossier names what SIG does not know yet. | d4c8421040080c6c3aeef06ecfb094cd8737083387dc34dfc3586753791e57f4 | pending |
| CK-36 | /research-queue/ | A gap opens a task here as review finds it, with a release. | 01bae6c8516315252c10223f4f29de0ce3403029bc83b07c02bace06ba069101 | pending |
| CK-37 | /research-queue/ | The queue's open tasks are listed below. | 25576438c1f8cf5aa93f8462ce519edd4e0bd4b2578d44cf62c4882562c24eb6 | pending |
| CK-38 | /research-queue/ | The filter appears once tasks are scoped to a place. | 4c2ea481b7dc582898f18724bfd1a21edfeeef5d4472190bb1a566d8039731f9 | pending |
| CK-39 | lib/empty.ts | The dossier index keeps the inventory overviews. | e0ebad534473ef023dc97fe49b5668772b3df3fc0c1f0336546b1c800cdb9fc7 | pending |
| CK-40 | lib/empty.ts | A reviewed research dossier appears here once it passes review in a release. | 47971e686fb436fd4f3b8cc589bb49315e8c7e04f0f94f850504a7ad46e1aaa6 | pending |
| CK-41 | lib/empty.ts | The research queue lists the gaps SIG has turned into tasks. | 3f95307e6967a17360860a7c491c02d1c00b8883176819dcbfba93341580a83c | pending |
| CK-42 | lib/empty.ts | Open gaps appear here as review finds them, with a release. | 04f1a24360fbf7bac9d624a137d2eb2b32ed9afea1abfe529ef512be8bf81274 | pending |
| CK-43 | /404.html | The record is served whole from the home page; the search page finds a place or a source by name. | 0aa905f05d7e0d1092c9bde6f7b122683af82bb8c9654378dd0711341cdafad3 | pending |
| CK-44 | /404.html | A renamed page redirects or names its new identifier; an address that never existed stays a not-found state. | 9f46f3457f8b0f7806e6848750d37c91617ff8f70c9fab93d05af2557519571d | pending |
| CK-45 | /404.html | Search the record | e0b6d274a54d93fe188086b48ec6ff72d7cda6eba12ce125fc68a87551a7845e | pending |
| CK-46 | /404.html | Check the status page | 1b735dab904d4711198029b2ccfed779997a4ac37cc58362c43655a8df834b16 | pending |
| CK-47 | /403/ | The public record is served whole from the home page. | 99320d885400167c07b336146de20f876e74fe801487590a41205fd3e60fd5a4 | pending |
| CK-48 | /403/ | Access states change only with a publication decision in a later release, never at request time. | 277b436b21035fc1012bf2ee98d1ccbd254f7cbea616f7f79bad9b167c74c30e | pending |
| CK-49 | /403/ | Search the record | e0b6d274a54d93fe188086b48ec6ff72d7cda6eba12ce125fc68a87551a7845e | pending |
| CK-50 | /403/ | Check the status page | 1b735dab904d4711198029b2ccfed779997a4ac37cc58362c43655a8df834b16 | pending |
| CK-51 | /410/ | The corrections log names recorded corrections; the home page serves the record meanwhile. | 8d950bad56d46fed61a2c61ba08473b990fb6d438124b68ad3b62797d41bb108 | pending |
| CK-52 | /410/ | The page returns, or stays removed with a named reason, in a later release. | 6c3248f822c3910790c47e8b54afd3c339c71b2703558fde503752036f76fc43 | pending |
| CK-53 | /410/ | Search the record | e0b6d274a54d93fe188086b48ec6ff72d7cda6eba12ce125fc68a87551a7845e | pending |
| CK-54 | /410/ | Check the status page | 1b735dab904d4711198029b2ccfed779997a4ac37cc58362c43655a8df834b16 | pending |
| CK-55 | /500/ | Go to the home page | adceddedfd5962e31a232a284d14ee514b150e8baed9faeb7c9ca217623de072 | pending |
| CK-56 | /500/ | The page could not be served from the published record. | 6dadea658a4be7a62d389c98750112edaa0ade9095ead323229bf426f53f7e7f | pending |
| CK-57 | /500/ | The home page and the record index are served from the same published tree. | 134bea66047ce24a18a3db4b32b42df1e519fff14e97adcf76a2bacc54f11eae | pending |
| CK-58 | /500/ | The status page records any known serving fault; try the address again later. | 2a1d8f2a337c04a194e9707470661b73bd4d5a997e5b5fa9001d9a8918f38716 | pending |
| CK-59 | /500/ | Search the record | e0b6d274a54d93fe188086b48ec6ff72d7cda6eba12ce125fc68a87551a7845e | pending |
| CK-60 | /500/ | Check the status page | 1b735dab904d4711198029b2ccfed779997a4ac37cc58362c43655a8df834b16 | pending |

## Confirmation log

<!-- The operator's verbatim confirmation lands here at the copy-batch sitting:
     one line per sitting naming the rows confirmed, the operator's words
     verbatim, and a `date -u` stamp. Nothing is written until that sitting. -->
