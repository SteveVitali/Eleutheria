# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""GQ-10 file evaluator (P35.47 / SIG-CONF-005): the release-dir scan measures
the dossier inflation ratio against lineage roots off the emitted dossier
accounting — never a second derivation — and the sites rows supply the
one-row-per-record / interval-published / multi-view accounting."""

from __future__ import annotations

import json

from ops.quality import EvalContext, eval_gq10


def _write(tmp_path, rel: str, obj) -> None:
    path = tmp_path / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(obj, str):
        path.write_text(obj, encoding="utf-8")
    else:
        path.write_text(json.dumps(obj), encoding="utf-8")


def _dossier_doc(published: int, roots: int) -> dict:
    measured = (published / roots) if roots else None
    return {
        "schema": "sig.dossier/2",
        "rollup": {
            "records": published,
            "count_interval": {"records": published + 1, "lower": roots - 1, "upper": roots},
            "dossier_inflation_vs_lineage_roots": {
                "published_rows": published,
                "lineage_roots": roots,
                "measured": measured,
                "ratchet_target": "<= 1.02",
            },
        },
    }


def _site_row(entity: str, **extra) -> dict:
    row = {
        "entity_id": entity,
        "label": f"Site {entity}",
        "jurisdiction": "Oklahoma",
        "tier": 0,
        "lat": 35.4,
        "lon": -97.5,
        "precision": "exact",
        "site_id": entity,
        "copies": [],
        "possible_duplicates": [],
        "multi_view": [],
        "n_independent_lineages": 1,
    }
    row.update(extra)
    return row


def test_gq10_measures_the_worst_dossier_ratio(tmp_path) -> None:
    _write(tmp_path, "web/dossiers/oklahoma.json", _dossier_doc(published=10, roots=10))
    _write(tmp_path, "web/dossiers/oklahoma/tulsa.json", _dossier_doc(published=5, roots=4))
    _write(
        tmp_path,
        "apache/sites.jsonl",
        "\n".join(
            json.dumps(r)
            for r in [
                _site_row("a", copies=[{"record": "b"}]),
                _site_row("c", multi_view=[{"record": "d"}]),
                _site_row("e", possible_duplicates=[{"record": "f"}]),
            ]
        ),
    )
    m = eval_gq10(EvalContext(scan_dir=tmp_path))
    assert m.offered == 2 and m.evaluated == 2
    # The worst dossier (1.25) is the measured value — never averaged away.
    assert m.measured == 1.25
    assert "tulsa" in m.detail["worst_dossier"]
    assert m.detail["rows_with_copies"] == 1
    assert m.detail["rows_with_multi_view"] == 1
    assert m.detail["rows_with_possible_duplicates"] == 1
    assert m.detail["site_rows"] == 3


def test_gq10_not_evaluable_without_scan_dir() -> None:
    m = eval_gq10(EvalContext())
    assert m.not_evaluable_reason is not None
    assert m.measured is None


def test_gq10_not_evaluable_on_empty_dir(tmp_path) -> None:
    m = eval_gq10(EvalContext(scan_dir=tmp_path))
    assert m.not_evaluable_reason is not None


def test_gq10_honest_when_no_interval_evaluated(tmp_path) -> None:
    _write(
        tmp_path,
        "web/dossiers/oklahoma.json",
        {
            "schema": "sig.dossier/2",
            "rollup": {
                "dossier_inflation_vs_lineage_roots": {
                    "published_rows": 2,
                    "not_evaluable": "no completed camera-site ER run",
                }
            },
        },
    )
    m = eval_gq10(EvalContext(scan_dir=tmp_path))
    assert m.measured is None
    assert m.not_evaluable_reason is not None
