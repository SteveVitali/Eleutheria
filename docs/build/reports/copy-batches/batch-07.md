# Copy batch 07 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.43 (row 386), the next row needing new public sentences
     after batch-06 (B-2 "Batches + notice allowance"; the status lane's
     `/status/` and `/status/sources/` wording is agent-drafted, pending
     verbatim confirmation). Append-only: rows are never deleted or edited in
     place — a correction is a new row superseding the old id, and a status
     change is recorded in the confirmation log below with a `date -u`
     stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. `{placeholder}` fields are injected DATA (status time,
release id, counts), not drafted copy.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| ST-12 | /status/ | The status lane | 8b3b0abca1152465e554fee0b2234884173ee44bdd34be5aba6b449b864edb5e | pending |
| ST-13 | /status/ | Status as of {statusTime} UTC — the lane updates every 6 hours and its values are not a citation; the published data is release {releaseId} (data as of {asOfWorld}). | 3319938e41a8701493138b6a68e0dd2083d1e933fcdf4d864512bcf67130708d | pending |
| ST-14 | /status/ | In the last 24 hours {runs24h} runs completed — {outcomes24h}; the last 7 days: {outcomes7d}. | e288a5a5c7769f68e220aa2416790f25c5c2cfd6486ec7aa2552f445c8443aca | pending |
| ST-15 | /status/ | Sources by freshness state: {freshnessStates}. | e2d5738b9cd16e22e205182c5ed0317682af264aa709379d5a8eef061bc8c585 | pending |
| ST-16 | /status/ | {listedCount} scheduled sources are listed on /status/sources/; {countOnly} gated, refused or withdrawn sources appear as counts only. | 011f9d18b815c9d2de55a075467bf915c204a7904d190b8ee5b28c7add6e541d | pending |
| ST-17 | /status/ | Scheduler drift: {drift}. | 9ad455215d6fb77a72da266d29fb5285b57fd0aecbc35c88aae23f026a4bacb8 | pending |
| ST-18 | /status/ | Robots disregarded under the recorded decision ({decisionRef}): {hosts} host(s), {events} fetch(es) — disclosed as host and count only. | c31de3c28538e3a81726969d46170803e0297f5470e66d58571fd32e9a685e84 | pending |
| ST-19 | /status/ | No status read is recorded in this build; the lane publishes a fresh copy every 6 hours once the status job runs. | 5dd3c0ced2d69ee51b642c79b165adbae4f24ffad953587b3beabe1715e558b0 | pending |
| SS-01 | /status/sources/ | No status read is recorded in this build; the lane publishes a fresh copy every 6 hours once the status job runs. | 5dd3c0ced2d69ee51b642c79b165adbae4f24ffad953587b3beabe1715e558b0 | pending |
| SS-02 | /status/sources/ | Status as of {statusTime} UTC — this page updates every 6 hours and is not a citation; the published data is release {releaseId} (data as of {asOfWorld}). Next-run values are shown to the day. | fd4e9ab67c76ddd279e97a57e5fa3057a43d6a685df73e23de9aa80da01afe91 | pending |
| SS-03 | /status/sources/ | Sources | caf85b0888d78f1f83771a07b25c3d30fa1210242f2fae6e5ae5d9a686602800 | pending |
| SS-04 | /status/sources/ | {listedCount} scheduled sources are listed below. | 1d1867f68379655de0c902a4d5e168030902912f2753d8d692b6647b6e8cd2fe | pending |
| SS-05 | /status/sources/ | {countOnly} sources appear as counts only — {gated} gated, {refused} refused and {withdrawn} withdrawn. | 7c96174bb392b7a6df7bfb129f7365c1dad068eb9703a170b8cf83624e2cf8f8 | pending |
| SS-06 | /status/sources/ | Runs and freshness | 43d851e08996289ccfbc303b8933f8189b6a8166dced9b42d2ca6c9a4f449788 | pending |
| SS-07 | /status/sources/ | Source | 0e570ca6fabe24f94e52c1833f3ffd25567022beb826fa16891f3322051bc221 | pending |
| SS-08 | /status/sources/ | Status | 920e413c7d411b61ef3e8c63b1cb6ad058d5f95f8b481dbafe60248387d8c355 | pending |
| SS-09 | /status/sources/ | Last run | 512a48218ba2179153629504206e7d54a7767e19ee2aa21574a7c614e5c92537 | pending |
| SS-10 | /status/sources/ | Next run (day) | a1c31836a716a1068c45160f64928118364876a47888359511dcadfc5bdd07f8 | pending |
| SS-11 | /status/sources/ | Freshness | cde4eb3cc3d18df704626386aafa37337773c3b69abd901e1c820ebb24f3727f | pending |
| SS-12 | /status/sources/ | Runs 7d | 8c52b2a8a560c19bbcdd0d360c1f0012f9933afbe73689ad1ab69b2e9cebed8b | pending |
| SS-13 | /status/sources/ | Errors | cb702378f31507efa79a2a2c6046050bc9f578f149c88e3c0a3d9532ab4b5300 | pending |
| SS-14 | /status/sources/ | Claims 7d | 572f5e01a910a2be07cf48cb3f3a3caf711333ada6e789e70d7f4e5cc5cdde46 | pending |
| SS-15 | /status/sources/ | The machine-readable heartbeat is state.json; the lane document is lane.json. | 336780dcc71bfcb5d10d65959e809a43024b6c2852ec99a261be3c934ef7541c | pending |
