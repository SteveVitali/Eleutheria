# ADR-124 flagged-organisation census (sig.org-census/1)

P34.26 / ADR-159 (G2-ADR124 + D-K2-1 [A-10], "auto-allow + absence
only"): every `publication_review_required` organisation on the read
spine (`sig-pg (read-only sig_read_public)`), read-only. Screened labels and literal party
values are **never** in this report — ids + scheme:value pairs only
(K2 §3.4; the screen result is a count, not a name). K2 NEW-1's
"969 flagged" and "50 reviews unlock 96.5 %" are re-measured by
this report, never pinned.

```json
{
  "definitions": {
    "adr159_outcome": "auto_allow_eligible | already allowed | recorded deny | not yet reviewed",
    "degree": "distinct claim subjects whose claims reference the org via object_entity (the K2 organisation-edge measure \u2014 NEW-1 re-measured, never pinned)",
    "edge_share": "degree / the flagged-org graph's distinct (subject, org) pairs (the denominator this report prints)",
    "identifiers": "external entity_identifier scheme:value pairs held; label-bearing schemes (*.name, sig.curator.handle, \u2026) are counted in label_identifier_count, never listed",
    "materialized_degree": "live incident edges over relationship + entity_role + organization_relation (open sys_period where bitemporal)",
    "person_name_screen": "policy.intake.screen_part_viii + the partner_identity never-a-person rule over cached_canonical_name + literal party claim values \u2014 result only, screened text never recorded",
    "registry_match": "an entity_identifier in an ADR-159 registry scheme whose asserting claim reaches an ingestion_permitted source (tier-0 match record)"
  },
  "disposition_registry_present": false,
  "edge_denominator": 43662,
  "flagged_total": 1559,
  "generated_at": "2026-10-04T16:01:18Z",
  "obligation": "D-R11-ADR124-1",
  "outcome_counts": {
    "not yet reviewed": 1559
  },
  "person_screen_flagged": 5,
  "policy_version": "publication-eligibility/1",
  "record_type": "sig.org-census/1",
  "registry_match_counts": {},
  "rule": "ADR-159 registry auto-allow (G2-ADR124 + D-K2-1 [A-10])",
  "spine": "sig-pg (read-only sig_read_public)",
  "top50_edge_share": 0.9259997251614677
}
```

## Summary

- flagged organisations: **1559**
- flagged-org edge denominator (distinct subject,org pairs): **43662**
- top-50 degree share: **92.6%**
- `auto_allow_eligible`: **0**
- `already allowed`: **0**
- `recorded deny`: **0**
- `not yet reviewed`: **1559**
- person-name screen flags: **5** (labels/values screened, never recorded)

## Registry matches (permitted-source asserted)

- census_of_governments (`us.census.geoid`): **0**
- sam_uei (`us.sam.uei`): **0**
- wikidata_qid (`wikidata.qid`): **0**

## Columns (CENSUS.csv)

| column | meaning |
|---|---|
| entity_id | the flagged organisation's id |
| organization_type | its §11.2 namespaced type |
| status | active/inactive/withdrawn/suppressed |
| degree | distinct claim subjects referencing the org via `claim.object_entity` (K2's organisation-edge measure) |
| materialized_degree | live incident edges over `relationship` + `entity_role` + `organization_relation` |
| edge_share | degree / the report's distinct-pair denominator |
| identifiers | external `entity_identifier` `scheme:value` pairs held — label-bearing schemes (`*.name`, `sig.curator.handle`, …) are never written; their count is the next column |
| label_identifier_count | how many label-scheme identifiers the org holds (the withheld name's count — the name itself is never in this report) |
| registry_match | `registry:scheme:value` whose asserting claim reaches an `ingestion_permitted` source, else empty |
| person_name_screen | `pass` | `flag_part_viii` | `flag_person_name` — never the screened string |
| screened_literal_party_count | how many literal party values the screen ran over (a count, not the values) |
| current_disposition | the effective entity disposition (`none`/`allow`/`withhold`/`restrict`/`withdraw`) |
| adr159_outcome | the typed ADR-159 state — `auto_allow_eligible` (the verb would record an allow), `already allowed`, `recorded deny`, or `not yet reviewed` — never absent, never an implicit allow |
| obligation | `D-R11-ADR124-1` — the owed ADR-124 allow row |

## Files

- `CENSUS.csv` — one row per flagged organisation (the columns above)
- `census.json` — the `sig.org-census/1` machine record
- `allow-list.json` — the `sig.disposition-list/1` over the `auto_allow_eligible` rows; **P34.46 applies it under its in-ticket go with the Round-10 schema** — P34.26 applies nothing
