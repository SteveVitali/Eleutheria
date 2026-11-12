# Copy batch 26 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P37.40 (row 464, R11-K13-CHG-01 — the /changes/ page and
     change feeds: the two-class copy and the empty/typed-absence states).
     Append-only, same convention as batch-01: rows are never deleted or
     edited in place; a status change is recorded in the confirmation log
     with a `date -u` stamp. Id prefix: CHG-* = the changes surface's
     drafted copy. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish gate
scans every `batch-*.md`, so a pending row refuses the republish rather than
reading as untracked. The `data-copy` attribute binds each rendered element
to its row ids. `{slot}` names vary per render — the row records the
template the element fills. Furniture — headings, link labels, table
captions — is navigational chrome, never a row.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| CHG-01 | /changes/ | This page diffs the latest release against the previous activated release and keeps two kinds of change apart: what SIG's records now say differently, and what the sources report changed in the world. Dates are the releases' own world and belief dates — never version-control dates. | 45f72a16f6db1fecb2503446f0e0686a2b0f0d5df94b2e931182006ccae0ed87 | pending |
| CHG-02 | /changes/ | No release diff is bound to this build | c8385f2a42f5ee7885d23bbb277939aa3fbaed5aa0cbcb216c40dd6b757f8a64 | pending |
| CHG-03 | /changes/ | The changes view reads the release's own diff files (transparency/changes/) — a release bound to this build carries none, so no change is asserted. | 58aea01bd0bb947517c0cb86d6f06e18350170aefce13c401992119f592edc7f | pending |
| CHG-04 | /changes/ | The release catalog and each source page still show what this build knows. | b8bbf4a11c973571922949cfcbae31f883b59e78dbe4c03e8ab0f50c98138a58 | pending |
| CHG-05 | /changes/ | Browse the sources | e5ca6e0ce0af27478334e04ed8d15d706456cd8f066690f85565249e39d51b79 | pending |
| CHG-06 | /changes/ | The next activated release carrying a diff turns this page on. | 9fee54610ecfc457884f77d1464cff7dc297cdeb28a218a030b83b740bdc2f0a | pending |
| CHG-07 | /changes/ | From {previous} to {current}. | 373615020a4ab718fc412026bb6482d79ab46adf5b4bde5db85141b0016624b6 | pending |
| CHG-08 | /changes/ | What the sources report changed on their own side — a source that stopped publishing, left the universe, or withdrew a record's footing — dated by the releases' world dates. | 2b37068a6db983bd8d35301877387703afb464102f44ba9d39a2ed6a293a3ca7 | pending |
| CHG-09 | /changes/ | No world-side change is recorded between these two releases. | 5e84c933e33e4d8f48a8da833e4655bfdf25e108fd972913cdbc2e70122206c5 | pending |
| CHG-10 | /changes/ | What SIG's published records now say differently — records added, removed or whose compared fields changed — dated by release activation (belief time). A record-level change reflects SIG's records; it may be SIG learning, re-resolution or claim re-minting, never automatically a change in the world. | f846a542cf25f2e8cabde2d1279bfed97a226fdd704a74a3a4bd1d54b2ba4525 | pending |
| CHG-11 | /changes/ | No record-side change is recorded between these two releases. | 3331eac0a80796857820075bf61e47322eca3959a7a5d1b40dc0595392fb6ac0 | pending |
| CHG-12 | /changes/ | The feed document is capped at {shown} of {total} events — the full record-level diff is the release's parquet set. | 034f587a3a964a4d0212364334c5817792b18d88eee903e099a3af5919a85542 | pending |
| CHG-13 | /changes/ | Every change also rides an Atom feed: one for the whole release diff, one per place (a place feed covers its descendants), and one per source. Feeds exist even when they list zero entries — subscribe early and items arrive with the next release. | d8cc2b7d4feeaafa071d9f33f2c77fcfbd9c34bd6f7cf2ecdd69aa5dfb17a1ed | pending |
| CHG-14 | /changes/feeds/ | Subscriptions are pull feeds: add one to a feed reader and it fetches updates at each release — SIG keeps no email list and no accounts. Every feed exists even when it lists zero entries, so a reader can subscribe before the first change lands. | e7e873bebf604d3f5e0fcaea38cd8f1ef67d83030c7d572c8eebc73dfe6c51c8 | pending |
| CHG-15 | /changes/ | The source-lifecycle diff was not evaluable for this release — no source-side change is asserted either way. | c484f988e2a265afb186a946a91d06656211f2025ca2f124774b6b31d20705f1 | pending |

## Confirmation log

<!-- Operator confirmations append here, one line per row or batch-wide,
     dated with `date -u`. -->
