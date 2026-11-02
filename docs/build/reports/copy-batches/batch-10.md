# Copy batch 10 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.49 (row 392), the next row needing new public sentences
     after batch-09 (B-2 "Batches + notice allowance", D-J3-12 = OD-07 a:
     the `/status/issues/` issues log and the `/sources/<id>/` known-issues
     section's wording — headings, the log summary, absence states — is
     agent-drafted, pending verbatim confirmation). Append-only: rows are
     never deleted or edited in place — a correction is a new row
     superseding the old id, and a status change is recorded in the
     confirmation log below with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish
gate scans every `batch-*.md`, so a pending row refuses the republish
rather than reading as untracked. The `data-copy` attribute binds each
rendered element to its row ids. `{placeholder}` fields are injected
DATA (dates, counts, hosts, licence ids), not drafted copy. The
`/status/issues/` and `/sources/<id>/` columns name the page families.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| IL-01 | /status/issues/ | Issues as of {status_time} UTC — this page is not a citation; the published data is release {releaseId} (data as of {asOfWorld}). | 759001e95be7c8caa080e0c45461d6ad99c668f53e3eb72f97fee8e07af36a3a | pending |
| IL-02 | /status/issues/ | The log is append-only: a resolved issue gains a closed date, it is never removed. Auto-detected entries come from recorded runs; curated entries are the committed known-issues registry. | f318756c062c3b751e055bc606b0e9b0890a1aa276bc246588936b905ed1ccd4 | pending |
| IL-03 | /status/issues/ | No issues are recorded in this build. | 142da010c7e23f4807f4f91ef348c2b8f90e4a1bf7872936bcac4489668abd2a | pending |
| IL-04 | /status/issues/ | The log | c7181c729f1e528cd9d771a19b73bcdfbfd7f82300e4c3ce28cd99a7c941c2b6 | pending |
| IL-05 | /status/issues/ | {openCount} open and {closedCount} closed entries across {curatedCount} curated known issues. | 8288d188a29755ed78bb9730fe9f91e8cb77b959fbf64bd8f4f4f7d03debae16 | pending |
| IL-06 | /status/issues/ | Class | 4f3a9bd003974a5ed8c9ad65d4aeda3b8a0db6fd903e36e83a3a950624b09bbd | pending |
| IL-07 | /status/issues/ | Kind | f5387f9bb6ed70315a77fdcb9335facc27a9bf241f35955bd2755c55e0c016c7 | pending |
| IL-08 | /status/issues/ | Opened | b19fb8d1b395b333251f40be2909ca37a0b0a007b3c4c4b34b726be71f715daa | pending |
| IL-09 | /status/issues/ | Last seen | 21fd79c7de52e1cf63f8cf11f8a0eac6965506e09ba6e406e1f6bf40a3b5ed52 | pending |
| IL-10 | /status/issues/ | Closed | c21ead0614e7e1b70edb3759e1d19ca1e12e6036980d10bfb73052fb1a018efa | pending |
| IL-11 | /status/issues/ | Count | 37bac4952becf21ac5838d3c9ba82811bc421c857571e89634dcbe346681d54c | pending |
| IL-12 | /status/issues/ | Issue | 48dc76dfa23ae03fea1372c5ed6c0e1bd62eaeca7bba6d804eb0afa87972f031 | pending |
| IL-13 | /status/issues/ | The machine-readable log is issues.jsonl; curated entries are recorded in the committed known_issues.toml. | 3ea1f7b37aaae1efa55dc2b149dce09bd1f1199991afda9062ff1214600a9df6 | pending |
| IL-14 | /status/issues/ | Pages: | 0f36bbc96bf26dbbc00740973db0e3b1d509ab24e0fe64ae9e90bea494b6f1c1 | pending |
| IL-15 | /status/issues/ | first | a7937b64b8caa58f03721bb6bacf5c78cb235febe0e70b1b84cd99541461a08e | pending |
| IL-16 | /status/issues/ | ‹ previous | a02ed4a2b620f9f3276fb50f9ffa1f0aa9f5bfa171549ba6dbf1cbcc5618f436 | pending |
| IL-17 | /status/issues/ | Page {page} of {pages} — sources {first}–{last} of {total} | 7ef86e26d87cc55ba953deb6b7985106864cfa8744426590dc8c49024f978dc1 | pending |
| IL-18 | /status/issues/ | next › | 93d4f7f677800a6cce5425c8657605e40ebb454a76c20c5656e801a17bb730ac | pending |
| IL-19 | /status/issues/ | last | 3547cb112ac4489af2310c0626cdba6f3097a2ad5a3b42ddd3b59c76c7a079a3 | pending |
| KI-01 | /sources/<id>/ | Known issues | 9e06846ba2df2bb2fb6494c1576cc9a2c882691c389d5d66ebb53f91d820a2fe | pending |
| KI-02 | /sources/<id>/ | No issues are recorded for this source. | 71790056d1777c185652099f723e793ebea6ac17a88b784cedf146f7ef5b5162 | pending |
| KI-03 | /sources/<id>/ | Class | 4f3a9bd003974a5ed8c9ad65d4aeda3b8a0db6fd903e36e83a3a950624b09bbd | pending |
| KI-04 | /sources/<id>/ | Kind | f5387f9bb6ed70315a77fdcb9335facc27a9bf241f35955bd2755c55e0c016c7 | pending |
| KI-05 | /sources/<id>/ | Opened | b19fb8d1b395b333251f40be2909ca37a0b0a007b3c4c4b34b726be71f715daa | pending |
| KI-06 | /sources/<id>/ | Closed | c21ead0614e7e1b70edb3759e1d19ca1e12e6036980d10bfb73052fb1a018efa | pending |
| KI-07 | /sources/<id>/ | Issue | 48dc76dfa23ae03fea1372c5ed6c0e1bd62eaeca7bba6d804eb0afa87972f031 | pending |
| KI-08 | /sources/<id>/ | The full append-only log is /status/issues/. | 81ddafe59e0a26283d8f1d5c9cb41dcc36ec4ac75c1f3e04c6d5007b2346d24d | pending |

## Confirmation log

<!-- one line per status change, `date -u` stamped; empty until the
     operator confirms a row verbatim. -->
