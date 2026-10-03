# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.21b (E2-12 / ADR-194) — the export's ``web/attribution_corrections.json``.

The dated correction record is honest and data-driven: it exists only when
this export's effective rights resolve through rights_decisions whose recorded
basis carries the ADR-194 attribution-correction marker; each corrected source
carries the newest decision's ``decided_at`` + ``basis`` and the count of rows
the export carries under it. A pre-backfill (or fixture) export emits no
artifact — the /sources/ note is absent, never fabricated. The shaping parser
keeps pre-P34.21b row shapes: absent trailing columns mean "no decision".
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime

from exports.manifest import BuildSpec
from exports.shaping import (
    ShapingClaim,
    build_shaped_dataset,
    parse_shaping_claims,
)
from exports.spine_export import (
    _attribution_corrections_payload,
    build_spine_export,
)

CORRECTION_BASIS = (
    "ADR-194 attribution correction: earlier rows credited the wrong holder "
    "(E2-12); the recorded terms + attribution stand under the new rights."
)


def _claim(
    cid: str,
    sid: str,
    pred: str,
    *,
    value_text: str | None = None,
    source_id: str = "src_a",
    decided_at: datetime | None = None,
    basis: str | None = None,
) -> ShapingClaim:
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
        source_id=source_id,
        connector_name="camreg",
        effective_rights_id="rights-1",
        effective_spdx="ODbL-1.0",
        effective_redistributable="yes",
        effective_derivative_permitted="yes",
        effective_attribution=f"© {source_id}",
        effective_terms_url="https://example/terms",
        effective_decision_decided_at=decided_at,
        effective_decision_basis=basis,
    )


def _site(subject: str, **kw) -> list[ShapingClaim]:
    return [
        _claim(f"{subject}-lat", subject, "camera_latitude", value_text="35.0", **kw),
        _claim(f"{subject}-lon", subject, "camera_longitude", value_text="-97.0", **kw),
        _claim(f"{subject}-jur", subject, "camera_jurisdiction", value_text="X", **kw),
    ]


def _build(claims: list[ShapingClaim]):
    rows = [
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
    subjects = sorted({c.subject_id for c in claims})
    dataset = build_shaped_dataset(
        {
            "shaping_claims": rows,
            "subject_entities": [(s, "deployment") for s in subjects],
            "source_stats": [],
            "source_runs": [],
            "sharing_edges": [],
            "spine_watermark": "claims=1",
        },
        as_of="2026-09-27",
        generated_at="2026-09-27T00:00:00Z",
        spine_label="unit",
    )
    return build_spine_export(
        dataset,
        {},
        build_spec=BuildSpec(
            as_of_snapshot=date(2026, 9, 27),
            as_of_belief=date(2026, 9, 27),
            ruleset_version="ruleset/1",
            resolver_version="resolver/1",
        ),
        generated_at="2026-09-27T00:00:00Z",
        claims=claims,
        entity_types={s: "deployment" for s in subjects},
    )


# --- the payload builder --------------------------------------------------------


def test_no_correction_means_honest_absence() -> None:
    claims = _site("A")
    assert (
        _attribution_corrections_payload(
            claims, as_of="2026-09-27", generated_at="2026-09-27T00:00:00Z"
        )
        is None
    )


def test_non_correction_decision_is_not_a_correction() -> None:
    claims = _site(
        "A",
        decided_at=datetime(2026, 9, 1, tzinfo=UTC),
        basis="P27.2 source-scoped resolution (no attribution change)",
    )
    assert (
        _attribution_corrections_payload(
            claims, as_of="2026-09-27", generated_at="2026-09-27T00:00:00Z"
        )
        is None
    )


def test_payload_names_corrected_source_stamp_basis_and_rows() -> None:
    d1 = datetime(2026, 9, 20, 12, 0, tzinfo=UTC)
    d2 = datetime(2026, 9, 25, 8, 30, tzinfo=UTC)
    claims = (
        _site("A", decided_at=d1, basis=CORRECTION_BASIS)
        + _site("B", source_id="src_b", decided_at=d2, basis=CORRECTION_BASIS)
        + _site("C", source_id="src_c")  # uncorrected source — excluded
    )
    payload = _attribution_corrections_payload(
        claims, as_of="2026-09-27", generated_at="2026-09-27T00:00:00Z"
    )
    assert payload is not None
    assert payload["schema"] == "sig.attribution-corrections/1"
    assert payload["as_of"] == "2026-09-27"
    rows = {c["source_id"]: c for c in payload["corrections"]}
    assert set(rows) == {"src_a", "src_b"}  # src_c uncorrected → absent
    assert rows["src_a"]["decided_at"] == d1.isoformat()
    assert rows["src_b"]["decided_at"] == d2.isoformat()
    assert rows["src_a"]["basis"] == CORRECTION_BASIS
    assert rows["src_a"]["affected_rows"] == 3  # this export carries 3 claims


def test_newest_decision_wins_the_stamp() -> None:
    older = datetime(2026, 9, 20, tzinfo=UTC)
    newer = datetime(2026, 9, 26, tzinfo=UTC)
    claims = [
        _claim("c1", "A", "camera_latitude", decided_at=older, basis=CORRECTION_BASIS),
        _claim("c2", "A", "camera_longitude", decided_at=newer, basis=CORRECTION_BASIS),
    ]
    payload = _attribution_corrections_payload(
        claims, as_of="2026-09-27", generated_at="2026-09-27T00:00:00Z"
    )
    assert payload is not None
    (row,) = payload["corrections"]
    assert row["decided_at"] == newer.isoformat()
    assert row["affected_rows"] == 2


def test_correction_without_decided_at_is_excluded() -> None:
    claims = _site("A", basis=CORRECTION_BASIS)  # basis but no stamp — malformed input
    assert (
        _attribution_corrections_payload(
            claims, as_of="2026-09-27", generated_at="2026-09-27T00:00:00Z"
        )
        is None
    )


# --- the parse layer --------------------------------------------------------------


def test_parse_reads_trailing_decision_columns() -> None:
    claim = _claim(
        "c1",
        "A",
        "camera_latitude",
        decided_at=datetime(2026, 9, 25, tzinfo=UTC),
        basis=CORRECTION_BASIS,
    )
    row20 = (
        claim.claim_id,
        claim.subject_id,
        claim.predicate_id,
        claim.value_kind,
        claim.value_text,
        claim.value_num,
        claim.raw_value,
        claim.observed_at,
        claim.sensitivity_tier,
        claim.source_id,
        claim.connector_name,
        claim.occurrence_capture_id,
        claim.occurrence_retrieved_at,
        claim.occurrence_bound_at,
        claim.effective_rights_id,
        claim.effective_spdx,
        claim.effective_redistributable,
        claim.effective_derivative_permitted,
        claim.effective_attribution,
        claim.effective_terms_url,
    )
    stamp = datetime(2026, 9, 25, 10, 0, tzinfo=UTC)
    (parsed,) = parse_shaping_claims([(*row20, True, stamp, CORRECTION_BASIS)])
    assert parsed.effective_decision_decided_at == stamp
    assert parsed.effective_decision_basis == CORRECTION_BASIS


def test_parse_pre_p34_21b_row_shape_defaults_to_no_decision() -> None:
    claim = _claim("c1", "A", "camera_latitude")
    row20 = (
        claim.claim_id,
        claim.subject_id,
        claim.predicate_id,
        claim.value_kind,
        claim.value_text,
        claim.value_num,
        claim.raw_value,
        claim.observed_at,
        claim.sensitivity_tier,
        claim.source_id,
        claim.connector_name,
        claim.occurrence_capture_id,
        claim.occurrence_retrieved_at,
        claim.occurrence_bound_at,
        claim.effective_rights_id,
        claim.effective_spdx,
        claim.effective_redistributable,
        claim.effective_derivative_permitted,
        claim.effective_attribution,
        claim.effective_terms_url,
    )
    (parsed,) = parse_shaping_claims([row20])
    assert parsed.effective_decision_decided_at is None
    assert parsed.effective_decision_basis is None


# --- end to end over build_spine_export -------------------------------------------


def test_export_emits_the_correction_artifact_only_when_carried() -> None:
    corrected = _site(
        "A",
        decided_at=datetime(2026, 9, 25, tzinfo=UTC),
        basis=CORRECTION_BASIS,
    ) + _site("B", source_id="src_b")
    export = _build(corrected)
    assert "web/attribution_corrections.json" in export.web_artifacts
    doc = json.loads(export.web_artifacts["web/attribution_corrections.json"].decode())
    assert doc["schema"] == "sig.attribution-corrections/1"
    assert [c["source_id"] for c in doc["corrections"]] == ["src_a"]

    clean = _build(_site("C") + _site("D", source_id="src_d"))
    assert "web/attribution_corrections.json" not in clean.web_artifacts
