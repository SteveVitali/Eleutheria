import json
from datetime import date, datetime

from reconcile.resolve import RESOLVE, RESOLVER_VERSION, Claim
from reconcile.ruleset import load_ruleset

rs = load_ruleset()

# Two independent sources agreeing on 38 active devices; one older dissenting
# council-minutes figure of 40 — a real, multi-claim, RESOLVED decision.
claims = [
    Claim(
        claim_id="claim:portal-2026-07",
        subject_id="dep:okc",
        predicate_id="active_device_count",
        value=38,
        reliability="R2",
        integrity="I1",
        genre="portal_snapshot",
        observed_at=date(2026, 7, 1),
        source_id="src:okc-portal",
        count_basis="active",
        structured_exact=True,
    ),
    Claim(
        claim_id="claim:minutes-2026-06",
        subject_id="dep:okc",
        predicate_id="active_device_count",
        value=38,
        reliability="R2",
        integrity="I1",
        genre="council_minutes",
        observed_at=date(2026, 6, 15),
        source_id="src:okc-council",
        count_basis="active",
    ),
    Claim(
        claim_id="claim:news-2026-05",
        subject_id="dep:okc",
        predicate_id="active_device_count",
        value=40,
        reliability="R4",
        integrity="I1",
        genre="news_article",
        observed_at=date(2026, 5, 1),
        source_id="src:local-news",
        count_basis="active",
    ),
]

r = RESOLVE(
    "dep:okc",
    "active_device_count",
    claims,
    as_of_world=date(2026, 9, 1),
    as_of_belief=date(2026, 9, 1),
    ruleset=rs,
    computed_at=datetime(2026, 1, 1),
)
print("status", r.resolution_status, "value", r.value, "code", r.unresolved_code)
print("digest", r.input_digest)
print("ruleset", r.ruleset_version, "resolver", RESOLVER_VERSION)


def claim_dict(c: Claim) -> dict:
    return {
        "claim_id": c.claim_id,
        "subject_id": c.subject_id,
        "predicate_id": c.predicate_id,
        "value": c.value,
        "reliability": c.reliability,
        "integrity": c.integrity,
        "genre": c.genre,
        "observed_at": c.observed_at.isoformat(),
        "source_id": c.source_id,
        "count_basis": c.count_basis,
        "structured_exact": c.structured_exact,
    }


sample = {
    "_note": "L3 byte-identical rebuild sample (SIG-RECON-020). Regenerate with "
    "make gen or the P08.3 generator when the ruleset/resolver version changes.",
    "subject_id": "dep:okc",
    "predicate_id": "active_device_count",
    "as_of_world": "2026-09-01",
    "as_of_belief": "2026-09-01",
    "ruleset_version": r.ruleset_version,
    "resolver_version": RESOLVER_VERSION,
    "claims": [claim_dict(c) for c in claims],
    "expected_input_digest": r.input_digest,
    "expected_decision_key": json.loads(json.dumps(list(r.decision_key()))),
}
print(json.dumps(sample, indent=2))
