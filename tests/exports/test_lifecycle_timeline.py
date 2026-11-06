# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.

"""P37.9 (R11-DATA-05) — lifecycle into the dossier timeline.

The §29.4 reconciler's events feed the dossier ``timeline`` section on both
emission paths (the pre-placement flat dossiers and the keyed ``sig.dossier/2``
set): the section is non-empty wherever a dossier's member subjects carry
lifecycle evidence (the acceptance shape, F2a NEW-1); event-log transitions
decide (SIG-RECON-039), indeterminate windows stay marked (SIG-RECON-040), and
the two owned SIG-ONTO-065 soft-constraint flags surface as rows.
"""

from __future__ import annotations

import importlib.util as _ilu
import json

import pytest
from placement_fixtures import build_placement_env
from test_spine_export import _build, _build24, _fixture_claims, _site

from exports import lifecycle_timeline

_needs_duckdb = pytest.mark.skipif(
    _ilu.find_spec("duckdb") is None,
    reason="duckdb is required for the placement engine",
)


def _lc_claims() -> list[tuple]:
    """Lifecycle claim rows in the ``lifecycle_claims`` query's column order:
    subject_id, predicate_id, value_json::text, claim_id, observed_edtf,
    valid_edtf."""
    return [
        (
            "A",
            "lifecycle_transition",
            json.dumps({"state": "contracted", "date": "2025-04-03"}),
            "lc-1",
            None,
            None,
        ),
        (
            "A",
            "lifecycle_transition",
            json.dumps({"state": "canceled", "date": "2026-02"}),
            "lc-2",
            None,
            None,
        ),
        (
            "A",
            "deployment_lifecycle_transition",
            json.dumps({"state": "active", "date": "2025-06"}),
            "lc-3",
            None,
            None,
        ),
    ]


def _section(doc: dict, section_id: str) -> dict:
    return next(s for s in doc["sections"] if s["section_id"] == section_id)


def test_timeline_section_is_non_empty_where_events_exist() -> None:
    """The acceptance shape: a dossier whose subjects carry lifecycle claims
    emits a populated ``timeline`` section — the pre-placement flat path."""
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"lifecycle_claims": _lc_claims()},
    )
    dossier = json.loads(export.web_artifacts["web/dossiers.json"].decode())[0]
    timeline = _section(dossier, "timeline")
    assert timeline.get("rows"), "events exist — the section must be non-empty"
    by_claim = {r["claim_id"]: r for r in timeline["rows"] if r.get("claim_id")}
    # The audit event-log row is marked event_log; the procurement rows inferred.
    assert by_claim["lc-3"]["evidence_kind"] == "event_log"
    assert by_claim["lc-3"]["lifecycle_track"] == "operational"
    assert by_claim["lc-1"]["evidence_kind"] == "inferred"
    assert by_claim["lc-1"]["lifecycle_track"] == "procurement"
    assert by_claim["lc-1"]["value"] == "procurement: contracted"


def test_timeline_marks_unordered_windows_and_decides_nothing() -> None:
    """RECON-040: two overlapping fuzzy windows never invent an order — every
    member row carries ``unordered_within_window`` and no ``decides_current_state``."""
    claims = [
        (
            "A",
            "lifecycle_transition",
            json.dumps({"state": "contracted", "date": "2025"}),
            "lc-1",
            None,
            None,
        ),
        (
            "A",
            "lifecycle_transition",
            json.dumps({"state": "canceled", "date": "2025-06"}),
            "lc-2",
            None,
            None,
        ),
    ]
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"lifecycle_claims": claims},
    )
    dossier = json.loads(export.web_artifacts["web/dossiers.json"].decode())[0]
    rows = _section(dossier, "timeline")["rows"]
    assert len(rows) == 2
    assert all(r["unordered_within_window"] is True for r in rows)
    assert all("decides_current_state" not in r for r in rows)


def test_event_log_decides_and_the_row_says_so() -> None:
    """RECON-039: one event-log transition among inferred ones decides the
    window's state — the deciding row is marked, the window still recorded
    unordered."""
    claims = [
        (
            "A",
            "deployment_lifecycle_transition",
            json.dumps({"state": "active", "date": "2025"}),
            "lc-1",
            None,
            None,
        ),
        (
            "A",
            "deployment_lifecycle_transition",
            json.dumps({"state": "active", "date": "2025"}),
            "lc-1b",
            None,
            None,
        ),
    ]
    claims[1] = (
        "A",
        "deployment_lifecycle_transition",
        json.dumps({"state": "suspended", "date": "2025-06"}),
        "lc-2",
        None,
        None,
    )
    # lc-1 is event-log; lc-2 inferred would need lifecycle_transition but its
    # states are procurement — instead mix tracks: one log + one log → indeterminate.
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"lifecycle_claims": claims},
    )
    dossier = json.loads(export.web_artifacts["web/dossiers.json"].decode())[0]
    rows = _section(dossier, "timeline")["rows"]
    assert all(r["unordered_within_window"] is True for r in rows)

    # One log + one inferred on the same track → the log decides.
    mixed = [
        (
            "A",
            "deployment_lifecycle_transition",
            json.dumps({"state": "active", "date": "2025"}),
            "lc-1",
            None,
            None,
        ),
        (
            "A",
            "lifecycle_transition",
            json.dumps({"state": "active", "date": "2025-06", "track": "operational"}),
            "lc-2",
            None,
            None,
        ),
    ]
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"lifecycle_claims": mixed},
    )
    dossier = json.loads(export.web_artifacts["web/dossiers.json"].decode())[0]
    rows = _section(dossier, "timeline")["rows"]
    deciding = [r for r in rows if r.get("decides_current_state")]
    assert [r["claim_id"] for r in deciding] == ["lc-1"]
    assert all(r["unordered_within_window"] is True for r in rows)


def test_undated_transitions_are_listed_never_ordered() -> None:
    claims = [
        (
            "A",
            "lifecycle_transition",
            json.dumps({"state": "contracted", "date": "2025-01"}),
            "lc-1",
            None,
            None,
        ),
        (
            "A",
            "deployment_lifecycle_transition",
            json.dumps({"state": "active", "date": None}),
            "lc-2",
            None,
            None,
        ),
    ]
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"lifecycle_claims": claims},
    )
    dossier = json.loads(export.web_artifacts["web/dossiers.json"].decode())[0]
    rows = _section(dossier, "timeline")["rows"]
    undated = [r for r in rows if r.get("date_kind") == "undated"]
    assert [r["claim_id"] for r in undated] == ["lc-2"]
    # The undated event did not glue the dated one into an unordered window.
    assert all("unordered_within_window" not in r for r in rows)


def test_soft_constraint_flag_rows_surface() -> None:
    """ONTO-065: removed∧active flags a data-error row; canceled∧active a
    wind-down row — flagged, never rejected."""
    claims = [
        (
            "A",
            "deployment_lifecycle_transition",
            json.dumps({"state": "removed", "date": "2025-01"}),
            "lc-1",
            None,
            None,
        ),
        (
            "A",
            "deployment_lifecycle_transition",
            json.dumps({"state": "active", "date": "2025-02"}),
            "lc-2",
            None,
            None,
        ),
    ]
    export = _build(
        _site("A", "35.46", "-97.51", "Oklahoma"),
        raw_over={"lifecycle_claims": claims},
    )
    dossier = json.loads(export.web_artifacts["web/dossiers.json"].decode())[0]
    rows = _section(dossier, "timeline")["rows"]
    flags = [r for r in rows if r.get("soft_constraint")]
    assert [f["soft_constraint"] for f in flags] == ["physical_removed_operational_active"]
    assert flags[0]["disposition"] == "data_error"


def test_no_lifecycle_claims_means_an_empty_timeline() -> None:
    """Honest absence: no lifecycle evidence → the section emits no rows."""
    export = _build(_site("A", "35.46", "-97.51", "Oklahoma"))
    dossier = json.loads(export.web_artifacts["web/dossiers.json"].decode())[0]
    assert "rows" not in _section(dossier, "timeline")


@_needs_duckdb
def test_keyed_dossier_timeline_populates_on_placed_members(tmp_path) -> None:
    """The keyed ``sig.dossier/2`` path: A's lifecycle events land on every
    dossier its chain places it under (the placed leg's membership)."""
    env = build_placement_env(tmp_path / "lifecycle_keyed")
    from exports.placement import PlacementEngine

    engine = PlacementEngine(env.pack_dir, env.registry_path, spec_path=env.spec_path)
    export = _build24(
        _fixture_claims(),
        placement=engine,
        raw_over={"lifecycle_claims": _lc_claims()},
    )
    docs = {}
    for path, data in export.web_artifacts.items():
        if path.startswith("web/dossiers/") and path.endswith(".json") and "index" not in path:
            doc = json.loads(data.decode())
            docs[doc["slug_path"]] = doc
    # A places at the Verdin place leaf → the chain ancestors all show the
    # timeline (the member record's events count on each dossier it belongs to).
    for slug_path in ("usa", "usa/ca", "usa/ca/verdin-county-06037"):
        rows = _section(docs[slug_path], "timeline")["rows"]
        assert rows, f"{slug_path}: member lifecycle events must populate the section"
        assert {r["claim_id"] for r in rows if r.get("claim_id")} == {"lc-1", "lc-2", "lc-3"}
    # And the wind-down flag rides along (canceled ∧ active — soft constraint).
    assert any(
        r.get("soft_constraint") == "procurement_canceled_operational_active"
        for r in _section(docs["usa/ca"], "timeline")["rows"]
    )
    # A subject with no placement produces no rows anywhere — never guessed.
    assert all(r["subject_id"] == "A" for r in _section(docs["usa"], "timeline")["rows"])


def test_dossier_timeline_rows_unit_shape() -> None:
    """The surface adapter: per-track rows, decided/unordered marks, flag rows."""
    events = lifecycle_timeline.events_by_subject(_lc_claims())
    rows, rec = lifecycle_timeline.subject_timeline_rows("A", events["A"], as_of_edtf="2026-09-22")
    tracks = {r.get("lifecycle_track") for r in rows if r.get("lifecycle_track")}
    assert tracks == {"procurement", "operational"}
    assert any(r.get("soft_constraint") == "procurement_canceled_operational_active" for r in rows)
    # The reconciliation behind the rows: proc canceled ∧ op active decided.
    assert rec.current_states()["procurement"] == "canceled"
    assert rec.current_states()["operational"] == "active"
    # Unattributed subjects emit nothing.
    assert lifecycle_timeline.dossier_timeline_rows({"B"}, events) == []
