# Description batch 25 — agent-drafted source descriptions awaiting operator verbatim confirmation

<!-- P36.45 (R11-K13-UX10-1; D-J3-12 / OD-07 a — 'batches of ~25 confirmed verbatim; description pending review until then'). Append-only: a status change is recorded in the confirmation log below with a `date -u` stamp; rows are never deleted. -->

## Convention

One row per agent-drafted per-source description — the **source** id,
the exact **text** as it will render, its **sha256** (UTF-8, no trailing
newline), and a **status** (`pending` · `confirmed`). Only `confirmed`
descriptions may land on the registry `description` field — the
publish-matrix lint fails a declared description whose sha256 matches
no confirmed row here. An unconfirmed source publishes
`description_pending_review`.

## Rows

| id | source | text | sha256 | status |
|---|---|---|---|---|
| D25-01 | wikidata_sparql | `Wikidata SPARQL` — an upstream project source. | a71fa24b5fb56b95ee15d49f0df019dcb71ee0ae73e850787bfa2a2856cc2b72 | pending |
| D25-02 | wired_shotspotter_leak | `WIRED ShotSpotter sensor leak` — a news publisher source. | 9885eee4e10afb4992e55cccbe69b43a81a2230e77ba965d01fb850b6f74a96f | pending |

## Confirmation log

(none yet)
