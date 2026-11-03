# Copy batch 14 — agent-drafted public sentences awaiting operator verbatim confirmation

<!-- Created by P36.55 (row 398, dossier template v2), the row needing new
     public sentences after batch-13 (B-2 "Batches + notice allowance"): the
     Figure-1 typed empty states + caption chrome, the locator statuses, the
     Explore bar labels, the 'Next decisions' block, the 'Other public
     resources' block and the network-slot empty states. Agent-drafted,
     pending verbatim confirmation. Append-only: rows are never deleted
     or edited in place — a correction is a new row superseding the old
     id, and a status change is recorded in the confirmation log below
     with a `date -u` stamp. -->

## Convention

Identical to `batch-01.md`: one row per drafted public sentence — **page**,
exact **text** as it renders, **sha256** (UTF-8, no trailing newline,
`printf '%s' '<text>' | shasum -a 256`), **status** (`pending` ·
`confirmed`). Only `confirmed` sentences may ship (B-2); the publish
gate scans every `batch-*.md`, so a pending row refuses the republish
rather than reading as untracked. The `data-copy` attribute binds each
rendered element to its row ids. `{placeholder}` fields are injected
DATA (dates, counts, source names), not drafted copy.

## Rows

| id | page | text | sha256 | status |
|---|---|---|---|---|
| MF-01 | /dossier/&lt;path&gt;/ | No figure artifact in this build | 191e4613d4a76ae9ffb55c48d5a4c8d970bbf23432433ecd952baab22e861df7 | pending |
| MF-02 | /dossier/&lt;path&gt;/ | This release emitted no dossier-visuals input for this page — a publication gap, not a finding that nothing is recorded here. | c7203add97e423aac3e87700c89c09777c05f85f67bd34bc3d1a1cbdac28dc3a | pending |
| MF-03 | /dossier/&lt;path&gt;/ | The places table, sites list and every section below carry the same recorded facts — the map is never the only carrier. | d37cebec912b19e8dc2d60e781f9a0bdd25997d5cb538dd322bdc388fe8098d8 | pending |
| MF-05 | /dossier/&lt;path&gt;/ | The figure appears with a release that emits its verified inputs. | 8711d9a757ad3e84e18fb36bc9340ba1f1570220347c9c78330ec85891b37a1f | pending |
| MF-06 | /dossier/&lt;path&gt;/ | Figure 1 | 0565fceba715022c0e85824b201086ecd54eb9eb38df8778c3686ed57b2148e0 | pending |
| MF-07 | /dossier/&lt;path&gt;/ | Drawn compartments: {compartments}. | 4d24e5528fb4b6c4ac1969cca08cd10f2a38f7ca2dff44c8e63917ef268ade7b | pending |
| MF-08 | /dossier/&lt;path&gt;/ | {reason} — {records_total} published records still carry their facts below. | d184e175417e7e1214d4dfe2d4711a7423c8bf597829dbbd021d5b23f45cc4e9 | pending |
| MF-09 | /dossier/&lt;path&gt;/ | The published records for this place carry no draw-able point — the figure would have nothing honest to show. | b7b17395f9a480fc64e7d532573cb6bdf9942c2d1573cf60e7320413239c6e9f | pending |
| MF-10 | /dossier/&lt;path&gt;/ | No verified outline for this jurisdiction | 215d14ad8c4a81dacb234cbd6e987a231d2befc46b0479490a76ec414a3165da | pending |
| MF-11 | /dossier/&lt;path&gt;/ | No located records to draw | 3f2fc0a1aea39699548e52cc57d3195fa941c40a448281e3f0b47d8b880b5170 | pending |
| LC-01 | /dossier/&lt;path&gt;/ | No locator in this build | 6c78e1683c707e6705abcd7d759511ea2108d5376e2bd3c4e89f1aac1df140ad | pending |
| LC-02 | /dossier/&lt;path&gt;/ | No parent context — this dossier is a top-level jurisdiction | 7548f7d55d341de552b4a2fbf69ae3a8bc3a7570b04027e13e5e7808f4c2120d | pending |
| LC-03 | /dossier/&lt;path&gt;/ | No parent boundary geometry in this release | 9d9ba702387863dd0408a3b85e1a2b626e8a25d2d42b71020197c51407b6d2e7 | pending |
| LC-04 | /dossier/&lt;path&gt;/ | The parent-context symbol sheet is not in this build | 7462a531ef3cba2b4375e63ba431975621b5ebd08f0e2fc085505ffad5d011d6 | pending |
| EB-01 | /dossier/&lt;path&gt;/ | Explore on the map → | 0d0f57b2895f138416339ea11af25b2cd385497c9293d89d5ec06e5836c46b17 | pending |
| EB-02 | /dossier/&lt;path&gt;/ | See connections → | 78c2615a2bd49b81b50cc792b6fa5050fa4f3ebaf8dc2511965f98e342f291a4 | pending |
| ND-01 | /dossier/&lt;path&gt;/ | SIG is not tracking a dated upcoming decision for {name}. That is a gap in what SIG has recorded — not a finding that no decision is pending. | d51e1064ca8fff9f3515a1871a4f5e55816c9c263c5cbd3e8a6073f34734f68f | pending |
| ND-02 | /dossier/&lt;path&gt;/ | Watch upcoming decisions → | 26c1fe812ca7e9a9fb246499847ce48164f3f74f22ad8e4371f75b1530896cc5 | pending |
| OR-01 | /dossier/&lt;path&gt;/ | Other public resources | d346235ec4dc0e84f25978b514c7fabf740bcd69321dabcfd5ddc6ba8334b9b9 | pending |
| OR-02 | /dossier/&lt;path&gt;/ | Public resources a reader may also find useful — SIG does not endorse them, and this list never carries avoidance routing or plate lookups. | f77d09eaeff6c3234a7bd1ea9780154c7aaa55130324f4b8cfe0a4b1fcee603c | pending |
| NF-01 | /dossier/&lt;path&gt;/ | No dossier network figure is emitted in this release — the edge model that makes one honest is not landed yet (VIZ-01b's content). | bd73c1d0392ec12431dba59dc22e2a3995ec00c1aa8ac9705f5d26b23443c6ff | pending |
| NF-02 | /dossier/&lt;path&gt;/ | The rows and figures on this page carry the recorded facts the figure would summarise. | 6ac0fb3221861ec91d93b4c726dd39e192c1b59e0b55055515cff1bbaeaf8c85 | pending |
| NF-03 | /dossier/&lt;path&gt;/ | See the published network | a1848217b715ab6c51f7d31edb8bb6d9fdd83408db0363ca69b21ee77f680781 | pending |
| NF-04 | /dossier/&lt;path&gt;/ | The figure appears with a release that emits its evidenced edges. | 989948da1f53e95d7c32b7653f12f71f64a1401eb788161023cc507a6244d7c2 | pending |

## Confirmation log

<!-- one line per status change, `date -u` stamped; empty until the
     operator confirms a row verbatim. -->
