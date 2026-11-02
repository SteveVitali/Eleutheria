# Copy batch 05 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.42a (row 383), the next row needing new public sentences
     after batch-04 (B-2 "Batches + notice allowance"; the GX-06a entity
     surfaces' wording is agent-drafted, pending verbatim confirmation).
     Append-only: rows are never deleted or edited in place — a correction
     is a new row superseding the old id, and a status change is recorded
     in the confirmation log below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. Contract-verbatim strings (the ER disclosure, the
SIG-UI-080 withheld sentence) are record data, never batch sentences.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| EN-01 | /entity/ | Organisations, agencies and registry portals SIG records — every page cites the claims behind it. | c9e768e9ed57616a75d592ac4dec653863df4421facd7c18decaf387a5f742b1 | pending |
| EN-02 | /entity/ | Each count below carries SIG's entity-resolution disclosure: | 3ef8b8fe39f51c3f537b2a19f1924961abd53fb910dceb7bbe229af24f531a5d | pending |
| EN-03 | /entity/ | keyed entities in this release, counted with the entity-resolution disclosure beside each type. | 0e2b606bd4647d605ef73119138d6c41a8d17d4ef49368c75789252bbac6c0f1 | pending |
| EN-04 | /entity/ | await the registry auto-allow review — typed "not yet reviewed" rows, keyed no page and shown no name until the review matches them. | 27c777b2b11c80c2846547e3428423d18727d030c3d9d52fefbfb6dd5ad41ede | pending |
| EN-05 | /entity/ | The A–Z lists carry only keyed, published entities; the typed not-yet-reviewed rows beside them name a review state, never a name. | 18d2760d099456fa71ba79af506509d26cfbbf98dc556e47f1750e97fbd9922b | pending |
| EN-06 | /entity/<type>/ | recorded — keyed no page and shown no name until the registry auto-allow review matches | eaa0e328cbf92eac28613b08915b4eb719e7e6a1280dc2598376903ccfb045b3 | pending |
| EN-07 | /entity/<type>/<key>/ | Per-compartment statement and relationship exports land with the contract-B release; the JSON twin above is this entity's complete record today. | a2e2258526947ecc8d1b2c9cfe04fd542ebdfff67f04bba9990330dd32f069bc | pending |
| EN-10 | /entity/ | No entities published yet | 9d99011224d3610fd6a429d9057efee9224a58c11a520f6d455dd2c6f57041de | pending |
| EN-11 | /entity/ | No entity has passed the label registry's publication rules in this release. Absence here means none published, not that none exist. | bacec93d941020039e16715d9ae9d7e735e023133be1432a1834f6aa838fd293 | pending |
| EN-12 | /entity/ | The sources page lists what this release collected even before entities are keyed. | c23ce671d78a18a560a569fe6d590ab82bc001953c0f157f1bb553ff46a0b2b5 | pending |
| EN-13 | /entity/ | See the sources | a8e68bb5e20cff52dae3d7eb1daffef9ee7ab65b2c36274664f80ca17f5c97ed | pending |
| EN-14 | /entity/ | An entity type appears here once a release keys and pages it. | 172c590f9191840c2895f8c7e34696067cb63a083bfae926183bce18543f86eb | pending |
| EN-15 | /entity/<type>/ | published yet | 3715c60f3c906159a2f8855419ef6f068376986feb345d186af4dcf6f00b20e9 | pending |
| EN-16 | /entity/<type>/ | This release keys no published entity of this type — a publication state, not a finding that none exist. | c36d930cf09133d73e0be987994c62535c8f6fc20e7134421fe5b8bde4df6216 | pending |
| EN-17 | /entity/<type>/ | Other published entity types are listed on the hub. | 6814aa8d4316e94bb97b97c4c119c52652770aae1f863d354853c45ae33eae84 | pending |
| EN-18 | /entity/<type>/ | Back to the entity hub | b2d8406d9e203a5c1fad84600f47a8a07a3919a884a2bea7de09b3507de87c40 | pending |
| EN-19 | /entity/<type>/ | Rows appear here once a release keys entities of this type. | d0095ac792bb0536ef4cf1229e94b61976e4fe2fbe554d641093d75fe2ee1f8f | pending |
| EN-20 | /entity/<type>/<key>/ | Recorded, not yet published as a page | 1ff424b2719c54fe03ebf8e7f29b3d811088d0ca90625745c0a6ab0b133acec2 | pending |
| EN-21 | /entity/<type>/<key>/ | The label registry keys this entity but its page record did not ship in this build — a publication gap, not a finding about the entity. | 218bf50f1f0dc663c015dab0606e1884270aec5766cd48a8b219fef62dabbdb8 | pending |
| EN-22 | /entity/<type>/<key>/ | The type's A–Z list carries every entity this release pages. | ba6f7ba478dae471f37269998b3aeb334af6f9772a60170928e92f505a4f09ec | pending |
| EN-23 | /entity/<type>/<key>/ | Back to the entity hub | b2d8406d9e203a5c1fad84600f47a8a07a3919a884a2bea7de09b3507de87c40 | pending |
| EN-24 | /entity/<type>/<key>/ | The page appears with the release that emits its record. | 75f9df266c745da15bcec814c233fe1d274d26d8950735a4b36f7bb0b95ac1bd | pending |
| EN-25 | /entity/<type>/<key>/ | No claims published for this entity | 1579123bb11631b35d7927c027f059de8c04992711049c651c69429eeb4b4276 | pending |
| EN-26 | /entity/<type>/<key>/ | This release publishes no resolved claims about this entity — a reviewed state, not a finding. | 54c9ce7fe7d53143798ceffd4548381d34bc9ecb431d3f24f9da63a4746e4925 | pending |
| EN-27 | /entity/<type>/<key>/ | The relationships below are the recorded edges when they exist. | b7357119dba6917ebb549b6d8d96d1da37171f989b685f228277214952a4e3a6 | pending |
| EN-28 | /entity/<type>/<key>/ | Back to | cd9182ceab27df65eb2cbc52096c257a3ec235bf4512d7c56ad66d53380d5207 | pending |
| EN-29 | /entity/<type>/<key>/ | Claims appear with a release that publishes them. | ffb7fb2112a103cc999d93f4d23020d6789b3772e886a54df6b8b59e784c5a95 | pending |
| EN-30 | /entity/<type>/<key>/ | No relationships recorded | bfe0e79f1360f673dd7aed9c5b346eb46e9d5c94d3b853bcdc7ecba7e7d1f126 | pending |
| EN-31 | /entity/<type>/<key>/ | SIG has recorded no relationships for this entity in this release — an evidenced absence in the record, not in the world. | 489e4a8a0ff7df5fde00b7663024e3fd375ebc5fa206e0e87a344a72cd2de46c | pending |
| EN-32 | /entity/<type>/<key>/ | The claim groups above carry what SIG does record. | 945142e84ce783b4924aa763862e3637b7aec14dd5031489c2265a074082258f | pending |
| EN-33 | /entity/<type>/<key>/ | Back to the entity hub | b2d8406d9e203a5c1fad84600f47a8a07a3919a884a2bea7de09b3507de87c40 | pending |
| EN-34 | /entity/<type>/<key>/ | Relationship rows appear with a release that evidences them. | 46e736c938cfc67ea324f74e9be0b12e3a165a959c46831287a582c37ec01013 | pending |
| EN-35 | /entity/<type>/<key>/ | Not shipped in this record wave | f7cb9e05f13855128a644019c43252f2993c9232cb09925ef3c0dd781f4c17ff | pending |
| EN-36 | /entity/<type>/<key>/ | Contradiction records, the dated timeline and the related-pages block are contract-B sections — this release's entity record carries them as typed empty slots. | 13bcd965bb7cf676166ad228b379950c4d0e80876efc60939fb3cac801469bf8 | pending |
| EN-37 | /entity/<type>/<key>/ | The relationships table and claim groups above carry this contract's facts. | 383aa71689c44de82d3b03a06125137dbb4258f96802213ddf0f6e9f3d9b3758 | pending |
| EN-38 | /entity/<type>/<key>/ | Read the JSON twin | d614b36e3b03ebf93723eddbd7f6a2c3115b959e332caf85c34697cb8a6342d7 | pending |
| EN-39 | /entity/<type>/<key>/ | These sections fill with the contract-B release. | b74dbc55e885bd30c897e9714e03fd92e6bdfaed3131d36af5e1e5b7af1115d5 | pending |

## Confirmation log

<!-- The operator's verbatim confirmation lands here at the copy-batch sitting:
     one line per sitting naming the rows confirmed, the operator's words
     verbatim, and a `date -u` stamp. Nothing is written until that sitting. -->
