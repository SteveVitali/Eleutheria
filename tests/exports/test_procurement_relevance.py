# SPDX-License-Identifier: Apache-2.0
"""P36.30 — ``sig.procurement-relevance/1`` through the export (K2 GX-04 / D-K2-5).

Fixture-level, never living records: entity rows and notice-fact rows are
fabricated ``raw`` tuples (the same shape ``fetch_export_raw`` produces) —
the same harness ``test_entity_slug_history.py`` drives.
"""

from __future__ import annotations

import json
import uuid
from datetime import date

from exports.manifest import BuildSpec
from exports.shaping import (
    ShapingClaim,
    build_shaped_dataset,
    parse_shaping_claims,
)
from exports.spine_export import build_spine_export
from policy.procurement_relevance import SCHEMA, UNCLASSIFIED_LABEL

RELEVANCE_PATH = "web/procurement_relevance.json"


def _eid() -> str:
    return str(uuid.uuid4())


def _claim(cid: str, sid: str, pred: str, *, value_text: str | None = None) -> ShapingClaim:
    return ShapingClaim(
        claim_id=cid,
        subject_id=sid,
        predicate_id=pred,
        value_kind="value",
        value_text=value_text,
        value_num=None,
        raw_value=value_text or "",
        observed_at=date(2026, 5, 1),
        sensitivity_tier=0,
        source_id="src_a",
        connector_name="camreg",
        effective_rights_id="rights-CC-BY-4.0",
        effective_spdx="CC-BY-4.0",
        effective_redistributable="yes",
        effective_derivative_permitted="yes",
        effective_attribution="© src_a",
        effective_terms_url="https://example/terms",
    )


def _site(subject: str) -> list[ShapingClaim]:
    return [
        _claim(f"{subject}-lat", subject, "camera_latitude", value_text="35.46"),
        _claim(f"{subject}-lon", subject, "camera_longitude", value_text="-97.51"),
        _claim(f"{subject}-jur", subject, "camera_jurisdiction", value_text="Oklahoma"),
    ]


def _rows(claims: list[ShapingClaim]) -> list[tuple]:
    return [
        (
            c.claim_id,
            c.subject_id,
            c.predicate_id,
            c.value_kind,
            c.value_text,
            c.value_num,
            c.raw_value,
            c.observed_at,
            c.sensitivity_tier,
            c.source_id,
            c.connector_name,
            c.occurrence_capture_id,
            c.occurrence_retrieved_at,
            c.occurrence_bound_at,
            c.effective_rights_id,
            c.effective_spdx,
            c.effective_redistributable,
            c.effective_derivative_permitted,
            c.effective_attribution,
            c.effective_terms_url,
        )
        for c in claims
    ]


def _ent(eid: str, etype: str | None, skey: str | None) -> tuple:
    """``(entity_id, type, subject_key, merged_into, canonical, review_req, status)``."""
    return (eid, etype, skey, None, None, False, None)


def _fact(sid: str, pred: str, val: str) -> tuple:
    """``notice_relevance_facts`` — (subject_id, predicate, value, source_id)."""
    return (sid, pred, val, "src_a")


def _export(claims: list[ShapingClaim], raw_over: dict):
    rows = _rows(claims)
    subjects = sorted({c.subject_id for c in claims})
    base_raw = {
        "shaping_claims": rows,
        "subject_entities": [(s, "deployment") for s in subjects],
        "source_stats": [],
        "source_runs": [],
        "sharing_edges": [],
        "spine_watermark": "claims=1",
    }
    dataset = build_shaped_dataset(
        base_raw,
        as_of="2026-09-22",
        generated_at="2026-09-22T00:00:00Z",
        spine_label="unit",
    )
    bs = BuildSpec(
        as_of_snapshot=date(2026, 9, 22),
        as_of_belief=date(2026, 9, 22),
        ruleset_version="ruleset/1",
        resolver_version="resolver/1",
    )
    return build_spine_export(
        dataset,
        raw_over,
        build_spec=bs,
        generated_at="2026-09-22T00:00:00Z",
        claims=parse_shaping_claims(rows),
        entity_types={s: "deployment" for s in subjects},
    )


def _doc(export) -> dict:
    return json.loads(export.web_artifacts[RELEVANCE_PATH].decode("utf-8"))


def _export_with_notices(entities: list[tuple], facts: list[tuple]) -> dict:
    raw = {
        "label_entities": entities,
        "label_entity_dispositions": [],
        "label_facts": [],
        "entity_labels": [],
        "notice_relevance_facts": facts,
    }
    return _doc(_export(_site(_eid()), raw))


# ---------------------------------------------------------------------------
# The emitted artifact — both ways of the rule (the ticket's AC)
# ---------------------------------------------------------------------------


def test_artifact_emitted_with_schema_rule_and_counts():
    doc = _export_with_notices([], [])
    assert doc["schema"] == SCHEMA == "sig.procurement-relevance/1"
    assert doc["rule"]["decision"] == (
        "D-K2-5 [B-22] = as recommended: exclude unclassified procurement"
    )
    assert doc["counts"] == {
        "notices": 0,
        "surveillance_related": 0,
        "not_classified": 0,
    }
    # The vocabulary evidence binds the doc to the reviewed bytes — a real
    # sha256, never a fabricated binding.
    assert len(doc["vocabulary"]["sha256"]) == 64
    assert doc["vocabulary"]["cpv_codes"] > 0
    assert doc["vocabulary"]["naics_codes"] == 0


def test_keyword_relevant_notice_verdict():
    notice = _eid()
    doc = _export_with_notices(
        [_ent(notice, None, f"procurement_notice:ted_eu:{notice[:8]}")],
        [_fact(notice, "matched_keyword", "alpr")],
    )
    row = doc["rows"][0]
    assert row["entity_id"] == notice
    assert row["kind"] == "notice"
    assert row["relevance"] == "surveillance_related"
    assert row["bases"] == ["matched_keyword"]
    assert row["matched"] == ["alpr"]
    assert row["buyer_label"] is None


def test_cpv_code_relevant_notice_verdict():
    notice = _eid()
    doc = _export_with_notices(
        [_ent(notice, None, f"procurement_notice:ted_eu:{notice[:8]}")],
        [_fact(notice, "products", "35120000")],
    )
    row = doc["rows"][0]
    assert row["relevance"] == "surveillance_related"
    assert row["bases"] == ["product_code"]
    assert row["matched"] == ["cpv:35120000"]


def test_unclassified_notice_emits_the_h13_buyer_label():
    """The D-K2-5 exclusion posture end-to-end: the unclassified notice is
    in the artifact (never silently dropped) and surfaces ONLY as the
    buyer-page row — the H-13 label verbatim."""
    notice = _eid()
    doc = _export_with_notices(
        [_ent(notice, None, f"procurement_notice:okc_portal:{notice[:8]}")],
        [_fact(notice, "products", "93500000")],  # an unreviewed CPV code
    )
    row = doc["rows"][0]
    assert row["relevance"] == "not_classified"
    assert row["bases"] == ["none"]
    assert row["matched"] == []
    assert row["buyer_label"] == "not classified as surveillance-related"
    assert row["buyer_label"] == UNCLASSIFIED_LABEL


def test_notice_with_no_claims_still_emits_a_typed_verdict():
    """A publishable notice entity with NO relevance facts is a typed
    ``not_classified`` row — honest absence, never a missing row."""
    notice = _eid()
    doc = _export_with_notices(
        [_ent(notice, None, f"procurement_notice:portal:{notice[:8]}")],
        [],
    )
    assert len(doc["rows"]) == 1
    assert doc["rows"][0]["relevance"] == "not_classified"
    assert doc["rows"][0]["buyer_label"] == UNCLASSIFIED_LABEL
    assert doc["counts"]["not_classified"] == 1


def test_non_notice_subjects_emit_no_rows():
    """Only the notice family classifies — orgs/sites stay out of the doc."""
    org = _eid()
    site = _eid()
    doc = _export_with_notices(
        [
            _ent(org, "organisation", f"organization:{org}"),
            _ent(site, "deployment", f"ops_deployment:{site}"),
        ],
        [_fact(org, "matched_keyword", "alpr")],
    )
    assert doc["rows"] == []


def test_withheld_label_state_emits_no_row():
    """A registry row whose label_state is withheld (the A-10 outcome —
    person-kind or disposition-denied subjects) never surfaces a verdict."""
    person = _eid()
    raw = {
        "label_entities": [_ent(person, "person", f"notice:{person}")],
        "label_entity_dispositions": [],
        "label_facts": [],
        "entity_labels": [],
        "notice_relevance_facts": [_fact(person, "matched_keyword", "alpr")],
    }
    doc = _doc(_export(_site(_eid()), raw))
    assert doc["rows"] == []
