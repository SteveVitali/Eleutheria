from resolution.probabilistic import ProbabilisticMatcher

recs = [
    {"unique_id": "a1", "normalized_name": "travis county sheriff office", "name_first_token": "travis", "state": "TX", "organization_class": "us.le.sheriff"},
    {"unique_id": "a2", "normalized_name": "travis county so", "name_first_token": "travis", "state": "TX", "organization_class": "us.le.sheriff"},
    {"unique_id": "b1", "normalized_name": "los angeles police department", "name_first_token": "los", "state": "CA", "organization_class": "us.le.municipal_police"},
    {"unique_id": "b2", "normalized_name": "los angeles police dept", "name_first_token": "los", "state": "CA", "organization_class": "us.le.municipal_police"},
    {"unique_id": "c1", "normalized_name": "harris county sheriff office", "name_first_token": "harris", "state": "TX", "organization_class": "us.le.sheriff"},
]
m = ProbabilisticMatcher.from_data()
for res in m.match(recs):
    print(f"{res.left}-{res.right} tier={res.match_tier} w={res.match_weight:.2f} p={res.match_probability:.3f}")
    for c in res.decomposition:
        print(f"    {c.column}: gamma={c.gamma} bf={c.bayes_factor:.3f} [{c.label}]")
