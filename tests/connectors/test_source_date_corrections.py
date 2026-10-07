# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.22b / ADR-146 (table row 2) — the additive ``sources.toml`` date
corrections and their readers.

The Round-3 session wrote the chain date ``2026-09-10`` on 2026-09-13 (commit
``e1cedcad``, ``runs/P21.5.md:23``); the 21 misdated lines — fifteen date
fields on six sources plus the six ``FLIPPED`` notes that quote the same chain
date — are corrected **additively**: the recorded values and every FLIPPED
note stay byte-identical, and each affected source declares
``[[sources.<id>.date_corrections]]`` entries a reader prefers when it shows
the date. ``ingestion_permitted`` is untouched (HG-03), GL-GATE-03's authority
stays 2026-09-09.
"""

from __future__ import annotations

from datetime import date

import pytest
from connectors.corrections import corrections_list
from connectors.registry import (
    DateCorrection,
    SourceRecord,
    get,
)

#: (source_id, field) — the fifteen recorded date fields the Round-3 chain
#: date mis-stamped (register: docs/build/reports/memory-repair/
#: date_corrections.csv; the six `notes` lines it also lists carry no
#: machine-readable date and stay byte-identical).
CORRECTED: dict[str, tuple[str, ...]] = {
    "osm_overpass": ("last_verified", "rights_reviewed_on"),
    "deflock_repo": ("rights_reviewed_on",),
    "okc_procurement": ("last_verified", "rights_reviewed_on", "rights.retrieval_date"),
    "okc_council": ("last_verified", "rights_reviewed_on", "rights.retrieval_date"),
    "okcpd_policy": ("last_verified", "rights_reviewed_on", "rights.retrieval_date"),
    "ok_statute": ("last_verified", "rights_reviewed_on", "rights.retrieval_date"),
}

RECORDED = date(2026, 9, 10)
TRUE = date(2026, 9, 13)


def test_every_affected_source_carries_its_corrections() -> None:
    for source_id, fields in CORRECTED.items():
        rec = get(source_id)
        declared = {c.field for c in rec.date_corrections}
        assert declared == set(fields), (
            f"{source_id}: corrections {sorted(declared)} != {sorted(fields)}"
        )
        for c in rec.date_corrections:
            assert c.recorded == RECORDED
            assert c.true == TRUE
            # the correction names its evidence commit and decision record
            assert c.evidence == "e1cedcad"
            assert c.adr == "ADR-146"


def test_recorded_values_are_untouched_and_effective_shows_true() -> None:
    """ADR-146 D2: the recorded fields still read 2026-09-10 — the correction
    is additive, never a rewrite — while ``effective_date`` returns the true
    date a reader should show."""
    for source_id, fields in CORRECTED.items():
        rec = get(source_id)
        for field in fields:
            assert rec.recorded_date(field) == RECORDED, (source_id, field)
            assert rec.effective_date(field) == TRUE, (source_id, field)


def test_uncorrected_fields_read_the_recorded_value() -> None:
    """Fields with no correction resolve to their recorded value verbatim —
    e.g. osm_overpass's rights.retrieval_date was never chain-dated."""
    rec = get("osm_overpass")
    assert rec.effective_date("rights.retrieval_date") == date(2026, 8, 20)
    assert get("deflock_repo").effective_date("last_verified") == date(2026, 8, 20)


def test_no_ingestion_permitted_changed() -> None:
    """Nothing was re-flipped: the six corrected sources keep exactly the
    ingestion posture the GL-GATE-03 decision recorded."""
    for source_id in CORRECTED:
        assert get(source_id).ingestion_permitted is True
    # …and the correction mechanism never manufactures a flip — a source
    # without one stays whatever it was (spot-check a gated source).
    assert get("bidnet_direct").ingestion_permitted is False
    assert get("bidnet_direct").date_corrections == ()


def test_correction_for_lookup() -> None:
    rec = get("okc_procurement")
    c = rec.correction_for("last_verified")
    assert isinstance(c, DateCorrection) and c.true == TRUE
    assert rec.correction_for("rights.retrieval_date") is not None


def test_a_correction_naming_a_wrong_recorded_value_fails_closed() -> None:
    """A correction that mis-states the recorded value is a defect, refused at
    record construction — corrections never invent the value they correct."""
    from datetime import date as d

    base = get("okc_procurement")
    with pytest.raises(ValueError, match="records"):
        SourceRecord(
            id=base.id,
            name=base.name,
            source_kind=base.source_kind,
            homepage_url=base.homepage_url,
            default_tier=base.default_tier,
            custody_posture=base.custody_posture,
            compact_status=base.compact_status,
            robots_policy=base.robots_policy,
            rights=base.rights,
            date_corrections=(
                DateCorrection(
                    field="last_verified",
                    recorded=d(2026, 9, 9),  # not what the row records
                    true=TRUE,
                    evidence="e1cedcad",
                    adr="ADR-146",
                ),
            ),
        )


def test_malformed_correction_entry_fails_closed() -> None:
    from connectors.registry import _date_corrections_from_row

    with pytest.raises(ValueError):
        _date_corrections_from_row("x", {"date_corrections": [{"field": "last_verified"}]})
    with pytest.raises(ValueError):
        _date_corrections_from_row(
            "x",
            {
                "date_corrections": [
                    {
                        "field": "last_verified",
                        "recorded": "2026-09-10",  # a string, not a TOML date
                        "true": TRUE,
                        "evidence": "e1cedcad",
                        "adr": "ADR-146",
                    }
                ]
            },
        )


def test_corrections_artifact_echoes_the_date_corrections() -> None:
    """The attribution-corrections artifact shows the effective dates and
    echoes each correction's provenance — the correction is never silent."""
    doc = corrections_list()
    by_id = {r["source_id"]: r for r in doc["corrections"]}
    for source_id in CORRECTED:
        row = by_id[source_id]
        assert row["reviewed_on"] == TRUE.isoformat(), source_id
        echoes = {c["field"]: c for c in row.get("date_corrections", ())}
        assert set(echoes) == set(CORRECTED[source_id]), source_id
        for _field, c in echoes.items():
            assert c["recorded"] == RECORDED.isoformat()
            assert c["true"] == TRUE.isoformat()
            assert c["evidence"] == "e1cedcad" and c["adr"] == "ADR-146"
    # retrieval_date shows the effective date where one exists
    assert by_id["okc_procurement"]["retrieval_date"] == TRUE.isoformat()
    # a source with no corrections echoes none and shows the recorded dates
    clean = next(r for r in doc["corrections"] if "date_corrections" not in r)
    assert clean["reviewed_on"]


def test_echoed_artifact_still_loads_fail_closed() -> None:
    """The new ``date_corrections`` echo key is additive — the spine writer's
    loader still validates the artifact (unknown keys are ignored)."""
    import json
    import tempfile
    from pathlib import Path

    from connectors.corrections import write_corrections_list
    from db.rights_corrections import load_corrections

    with tempfile.TemporaryDirectory() as tmp:
        out = write_corrections_list(Path(tmp) / "corrections.json")
        rows = load_corrections(out)
        doc = json.loads(out.read_text(encoding="utf-8"))
    assert rows
    echoed = [r for r in doc["corrections"] if r.get("date_corrections")]
    assert len(echoed) == len(CORRECTED)
