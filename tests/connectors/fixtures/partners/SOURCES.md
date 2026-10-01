# P31.5 partner fixtures (SYNTHETIC)

Committed by P31.5 (DEEPEN.1, ADR-112) to prove the partner entity-ref claims over the real
connector stages and a real PostgreSQL spine (`tests/partner_fixtures.py`,
`tests/connectors/test_partner_refs_shadow.py`, `tests/db/test_partner_entity_refs.py`).

- `contracts.json` — a generic procurement `results[]` payload (the §11.11 Contract path).
- `usaspending_awards.json` — a USAspending `spending_by_award` page (the P26.14 notice path).
- `atlas_issue_records.csv` — an Atlas issue-record CSV (the §11.17 accountability-event path).

Every id, amount, vendor, story URL and person-shaped name is **invented test data, not
evidence**. The public-body names (the Washington State Department of Transportation, the
King County composite) are real so the fixtures join the committed
`tests/connectors/fixtures/dot_511/wa_wsdot.json` camera fixture, whose operator is that
department. The person-shaped and sole-proprietor names are deliberately fictitious and pin
the never-a-person rule: they must stay text only. None of these files is ever fetched live
or loaded to a hosted spine.

`text_claim_digests.json` is the golden content digest of every record the connectors emit
over these fixtures (plus `ted_eu_search_page1.json`, `france/decp_marches.json`,
`dot_511/wa_wsdot.json`) computed at the P31.5 base commit `34406ff`, before the partner
entity-ref claims existed: the shadow diff test asserts the post-P31.5 text records are
exactly these.
