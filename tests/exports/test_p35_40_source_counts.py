# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.40 — source universe, lifecycle partition and counts
(SIG-TRANSP-002/026/027, K9 §3.1–3.3, F-431): one source is one registry row
(``sig.source-row/1``); ONE exporter function computes the six-state
lifecycle partition at the release's belief cut under the published
precedence; identifiers carrying data without a registry row are listed as
anomalies and never counted; every emitted count names its predicate; the
partition sum is asserted fail-closed; and every emitted number recomputes
from ``sources.json`` alone.

Every assertion runs over fixture registry rows + fixture view tuples — no
database, no secrets, no living values.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest
from exports.transparency import (
    COUNTS_SCHEMA,
    LIFECYCLE_STATES,
    SOURCE_RECORD_SCHEMA,
    TRANSPARENCY_COUNTS_PATH,
    TRANSPARENCY_SOURCES_PATH,
    emit_transparency_artifacts,
    recompute_counts,
)
from policy.transparency import TRANSPARENCY_SOURCE_VIEW_COLUMNS

AT = datetime(2026, 10, 20, 13, 0, tzinfo=UTC)

#: The contract's published precedence — written verbatim so a code change
#: that reorders the partition fails here, never silently.
PUBLISHED_PRECEDENCE = (
    "withdrawn",
    "published",
    "ingested_not_published",
    "permitted_not_ingested",
    "gated",
    "refused",
)


def _reg(
    sid: str,
    *,
    lane: str = "derived-only",
    ingestion_permitted: bool = False,
    compact_status: str = "no_response",
    reviewed: bool = True,
) -> dict[str, Any]:
    return {
        "name": f"Fixture {sid}",
        "source_kind": "government_portal",
        "homepage_url": "https://example.org",
        "custody_posture": "MIRROR",
        "compact_status": compact_status,
        "ingestion_permitted": ingestion_permitted,
        "cadence": "",
        "rights_reviewed_by": "licensing reviewer" if reviewed else "",
        "rights_reviewed_on": "2026-09-16" if reviewed else None,
        "rights": {
            "spdx": "CC0-1.0",
            "attribution": "© Fixture",
            "redistributable": True,
            "derivative_permitted": True,
            "terms_url": "https://example.org/terms",
        },
        "redistribution": {
            "lane": lane,
            "evidence": f"rights/{sid}.md",
            "evidence_uri": "",
            "decision_authority": "D-J3-1 [B-19]",
            "review_needed": False,
            "part_viii_class": "none-known",
            "packet_limited": False,
            "sig_labelled_cc0": False,
        },
    }


def _emit(
    registry: dict[str, dict[str, Any]],
    *,
    claims=(),
    executions=(),
    captures=(),
    site_source_ids=(),
    view_rows=(),
    cadence: dict[str, dict[str, str]] | None = None,
):
    from exports.transparency import (
        TRANSPARENCY_CAPTURE_VIEW_COLUMNS,
        TRANSPARENCY_RUN_VIEW_COLUMNS,
    )

    raw = {
        "transparency_runs": [
            tuple(r.get(c) for c in TRANSPARENCY_RUN_VIEW_COLUMNS) for r in executions
        ],
        "transparency_captures": [
            tuple(r.get(c) for c in TRANSPARENCY_CAPTURE_VIEW_COLUMNS) for r in captures
        ],
        "transparency_source_rights": [],
        "transparency_sources": [
            tuple(r.get(c) for c in TRANSPARENCY_SOURCE_VIEW_COLUMNS) for r in view_rows
        ],
        "transparency_predicates": [],
    }
    return emit_transparency_artifacts(
        raw,
        claims=claims,
        cadence_sources={} if cadence is None else cadence,
        source_registry=registry,
        site_source_ids=site_source_ids,
        at=AT,
    )


def _sources(arts: dict[str, bytes]) -> dict[str, dict[str, Any]]:
    doc = json.loads(arts[TRANSPARENCY_SOURCES_PATH])
    return {r["source_id"]: r for r in doc["sources"]}


def _counts(arts: dict[str, bytes]) -> dict[str, Any]:
    return json.loads(arts[TRANSPARENCY_COUNTS_PATH])


# --------------------------------------------------------------------------- #
# SIG-TRANSP-026 — a source is one registry row
# --------------------------------------------------------------------------- #


def test_sources_json_carries_the_source_row_schema():
    arts = _emit({"s1": _reg("s1", ingestion_permitted=True, lane="raw-ok")})
    doc = json.loads(arts[TRANSPARENCY_SOURCES_PATH])
    assert doc["schema"] == SOURCE_RECORD_SCHEMA == "sig.source-row/1"
    assert doc["sources"][0]["schema"] == "sig.source-row/1"


def test_one_row_per_registry_source_never_per_target():
    """Connectors/tenants/endpoints are attributes: N registry rows in →
    exactly N source rows out, whatever the run/capture fan-out names."""
    registry = {
        "legistar": _reg("legistar", ingestion_permitted=True, lane="raw-ok"),
        "primegov": _reg("primegov", ingestion_permitted=True, lane="link-only"),
        "osm_seed": _reg("osm_seed"),
    }
    # Captures/runs keyed to the same source_id do not multiply the row.
    executions = [
        {
            "report_id": f"r{i}",
            "run_id": f"run{i}",
            "source_id": "legistar",
            "completion_status": "ok",
            "claims_inserted": 2,
            "finished_at": AT,
        }
        for i in range(3)
    ]
    arts = _emit(registry, executions=executions)
    doc = json.loads(arts[TRANSPARENCY_SOURCES_PATH])
    assert sorted(r["source_id"] for r in doc["sources"]) == sorted(registry)
    counts = _counts(arts)
    assert counts["universe"]["count"] == len(registry)


# --------------------------------------------------------------------------- #
# SIG-TRANSP-027 — the lifecycle partition
# --------------------------------------------------------------------------- #


def test_emitted_precedence_is_the_published_order():
    arts = _emit({"s1": _reg("s1")})
    counts = _counts(arts)
    assert counts["schema"] == COUNTS_SCHEMA
    assert tuple(counts["precedence"]["order"]) == PUBLISHED_PRECEDENCE
    assert tuple(LIFECYCLE_STATES) == PUBLISHED_PRECEDENCE
    # Every lifecycle entry names its predicate and carries its id list.
    for state in PUBLISHED_PRECEDENCE:
        entry = counts["lifecycle"][state]
        assert entry["definition"].strip()
        assert isinstance(entry["ids"], list)
        assert entry["count"] == len(entry["ids"])


def test_precedence_first_match_published_beats_refused():
    """A refused-status row whose claims passed the gate is ``published`` —
    the published state precedes ``refused`` in the precedence order."""
    registry = {
        "r1": _reg("r1", compact_status="permission_declined", ingestion_permitted=True),
    }
    claims = [{"source_id": "r1", "predicate_id": "p", "observed_at": None}]
    arts = _emit(registry, claims=claims)
    row = _sources(arts)["r1"]
    assert row["lifecycle_state"] == "published"


def test_precedence_first_match_ingested_beats_gated():
    """Ingestion evidence on a permission-less row → ``ingested_not_published``
    (the state precedes ``gated``); the row still renders S-11 registry-only."""
    registry = {"g1": _reg("g1", ingestion_permitted=False)}
    executions = [
        {
            "report_id": "r",
            "run_id": "run",
            "source_id": "g1",
            "completion_status": "ok",
            "claims_inserted": 4,
            "finished_at": AT,
        }
    ]
    arts = _emit(registry, executions=executions)
    row = _sources(arts)["g1"]
    assert row["lifecycle_state"] == "ingested_not_published"


def test_precedence_first_match_permitted_beats_refused():
    """``permitted_not_ingested`` precedes ``refused``: a permitted row with
    no ingestion evidence lands permitted even when declined."""
    registry = {
        "x1": _reg("x1", ingestion_permitted=True, compact_status="permission_declined"),
    }
    arts = _emit(registry)
    assert _sources(arts)["x1"]["lifecycle_state"] == "permitted_not_ingested"


def test_partition_invariant_fails_closed_on_unnamed_state():
    """A source row escaping every named lifecycle state fails the export —
    the partition sum is asserted, never assumed."""
    arts = _emit({"s1": _reg("s1")})
    rows = json.loads(arts[TRANSPARENCY_SOURCES_PATH])["sources"]
    rows[0]["lifecycle_state"] = "made_up_state"
    from exports.transparency import source_counts

    with pytest.raises(AssertionError, match="partition invariant"):
        source_counts(rows, anomalies=[], at=AT)


def test_emitted_partition_sum_check_is_in_the_record():
    """The partition check lands IN the artifact (SIG-TRANSP-027): the
    released ``counts.json`` itself records observed == expected ==
    universe.count and ``holds: true`` — any consumer can verify the six
    states cover the registry exactly once."""
    arts = _emit({"s1": _reg("s1"), "s2": _reg("s2", ingestion_permitted=True)})
    counts = _counts(arts)
    ps = counts["partition_sum"]
    assert ps["holds"] is True
    assert ps["expected"] == counts["universe"]["count"] == 2
    assert (
        ps["observed"]
        == sum(counts["lifecycle"][s]["count"] for s in PUBLISHED_PRECEDENCE)
        == ps["expected"]
    )
    assert ps["definition"].strip()


def test_every_emitted_count_names_its_predicate():
    arts = _emit({"s1": _reg("s1", ingestion_permitted=True, lane="raw-ok")})
    counts = _counts(arts)
    assert counts["universe"]["definition"].strip()
    assert counts["precedence"]["definition"].strip()
    for state in PUBLISHED_PRECEDENCE:
        assert counts["lifecycle"][state]["definition"].strip()
    for name, entry in counts["attributes"].items():
        assert entry["definition"].strip(), f"attribute {name} carries no predicate"
        if name == "lanes":
            assert isinstance(entry["by_lane"], dict)
        else:
            assert isinstance(entry["count"], int)
    assert counts["anomalies"]["definition"].strip()


def test_recompute_check_recomputes_every_emitted_number():
    """The CI recompute check (K9 §3 acceptance): every number in the emitted
    ``counts.json`` re-derives from the emitted ``sources.json`` rows alone."""
    registry = {
        "pub": _reg("pub", lane="raw-ok", ingestion_permitted=True),
        "ing": _reg("ing", ingestion_permitted=True),
        "perm": _reg("perm", ingestion_permitted=True),
        "gate": _reg("gate"),
        "ref": _reg("ref", compact_status="permission_declined"),
    }
    claims = [{"source_id": "pub", "predicate_id": "p", "observed_at": None}]
    executions = [
        {
            "report_id": "r",
            "run_id": "run",
            "source_id": "ing",
            "completion_status": "ok",
            "claims_inserted": 1,
            "finished_at": AT,
        }
    ]
    arts = _emit(registry, claims=claims, executions=executions, site_source_ids={"pub"})
    sources_doc = json.loads(arts[TRANSPARENCY_SOURCES_PATH])
    counts = _counts(arts)
    recomputed = recompute_counts(sources_doc["sources"])
    assert recomputed["registered"] == counts["universe"]["count"]
    for st in PUBLISHED_PRECEDENCE:
        assert recomputed["partition"][st] == counts["lifecycle"][st]["ids"]
    attr = counts["attributes"]
    assert recomputed["rights_permitted"] == attr["rights_permitted"]["count"]
    assert attr["rights_not_permitted"]["count"] == (
        recomputed["registered"] - recomputed["rights_permitted"]
    )
    assert recomputed["scheduled"] == attr["scheduled"]["count"]
    assert recomputed["one_time_load"] == attr["one_time_load"]["count"]
    assert recomputed["run_records_present"] == attr["run_records_present"]["count"]
    assert recomputed["run_records_missing"] == attr["run_records_missing"]["count"]
    assert recomputed["site_records"] == attr["site_records"]["count"]
    assert attr["no_site_records"]["count"] == (
        recomputed["registered"] - recomputed["site_records"]
    )
    assert recomputed["open_issues"] == attr["open_issues"]["count"]
    assert recomputed["lanes"] == attr["lanes"]["by_lane"]


# --------------------------------------------------------------------------- #
# Anomalies — data-bearing identifiers with no registry row
# --------------------------------------------------------------------------- #


def test_named_anomaly_ids_listed_never_counted():
    """The K9 §3.1 ids — `okc_council_statement`, `okc-contract-c241032`,
    `osm`-class identifiers — carry claims/captures/runs but no registry
    row: they land in the anomaly box, never in any count."""
    registry = {"real": _reg("real", ingestion_permitted=True)}
    claims = [
        {"source_id": "okc_council_statement", "predicate_id": "p", "observed_at": None},
        {"source_id": "okc-contract-c241032", "predicate_id": "p", "observed_at": None},
        {"source_id": "osm", "predicate_id": "p", "observed_at": None},
    ]
    arts = _emit(registry, claims=claims, site_source_ids={"osm"})
    counts = _counts(arts)
    assert counts["universe"]["count"] == 1
    assert counts["anomalies"]["ids"] == [
        "okc-contract-c241032",
        "okc_council_statement",
        "osm",
    ]
    all_ids = [sid for st in PUBLISHED_PRECEDENCE for sid in counts["lifecycle"][st]["ids"]]
    for anomaly in counts["anomalies"]["ids"]:
        assert anomaly not in all_ids
    # No emitted row exists for an anomaly either — it is never a source.
    emitted_ids = sorted(
        r["source_id"] for r in json.loads(arts[TRANSPARENCY_SOURCES_PATH])["sources"]
    )
    assert emitted_ids == ["real"]


def test_anomalies_cover_run_and_capture_only_identifiers():
    """An identifier on a run or capture alone (no claims, no sites) is an
    anomaly too — the box covers every data-bearing channel."""
    registry = {"real": _reg("real", ingestion_permitted=True)}
    executions = [
        {
            "report_id": "r",
            "run_id": "run",
            "source_id": "ghost_run",
            "completion_status": "ok",
            "claims_inserted": 0,
            "finished_at": AT,
        }
    ]
    captures = [
        {
            "capture_id": "cap1",
            "source_id": "ghost_capture",
            "run_id": "run",
            "captured_at": AT,
        }
    ]
    arts = _emit(registry, executions=executions, captures=captures)
    counts = _counts(arts)
    assert sorted(counts["anomalies"]["ids"]) == ["ghost_capture", "ghost_run"]
    assert counts["universe"]["count"] == 1


def test_anomalies_cover_cadence_only_identifiers():
    """An identifier declared in ops/cadence.toml with no registry row is an
    anomaly too — a scheduled-but-unregistered id carries ops data (K9 §3.1)."""
    registry = {"real": _reg("real", ingestion_permitted=True)}
    arts = _emit(
        registry,
        cadence={"ghost_scheduled": {"cron": "0 0 * * *", "state": "enabled"}},
    )
    counts = _counts(arts)
    assert counts["anomalies"]["ids"] == ["ghost_scheduled"]
    assert counts["universe"]["count"] == 1


# --------------------------------------------------------------------------- #
# The state vocabulary — withdrawn and one_time_load per the definitions
# --------------------------------------------------------------------------- #


def test_withdrawn_named_never_implied():
    """``withdrawn`` carries its predicate and a defined (zero) count — a
    source-level withdrawal is a D-J3-5 gate decision nothing in the
    registry records yet; the state exists, it is never inferred."""
    arts = _emit({"s1": _reg("s1")})
    counts = _counts(arts)
    withdrawn = counts["lifecycle"]["withdrawn"]
    assert withdrawn["count"] == 0
    assert withdrawn["ids"] == []
    assert "withdrawal" in withdrawn["definition"]


def test_withdrawn_signal_wins_the_precedence():
    """If a registry row ever records a withdrawal (a ``withdrawn`` flag or
    ``[withdrawal]`` sub-table), the row lands ``withdrawn`` FIRST — ahead of
    ``published`` in the precedence order, even with published claims."""
    reg = _reg("w1", ingestion_permitted=True)
    reg["withdrawn"] = True
    registry = {"w1": reg}
    claims = [{"source_id": "w1", "predicate_id": "p", "observed_at": None}]
    arts = _emit(registry, claims=claims)
    row = _sources(arts)["w1"]
    assert row["lifecycle_state"] == "withdrawn"
    counts = _counts(arts)
    assert counts["lifecycle"]["withdrawn"]["ids"] == ["w1"]
    # The withdrawn row does not double-count into published.
    assert "w1" not in counts["lifecycle"]["published"]["ids"]


def test_one_time_load_counts_beside_not_scheduled():
    """``one_time_load`` is its own schedule attribute: a one-time seed is
    not ``scheduled`` and not ``not_scheduled``."""
    registry = {"seed": _reg("seed", ingestion_permitted=True)}
    arts = _emit(registry)
    counts = _counts(arts)
    # The fixture carries no cadence declaration → not_scheduled.
    assert counts["attributes"]["one_time_load"]["count"] == 0
    assert counts["attributes"]["not_scheduled"]["count"] == 1

    arts2 = emit_transparency_artifacts(
        {
            "transparency_runs": [],
            "transparency_captures": [],
            "transparency_source_rights": [],
            "transparency_sources": [],
            "transparency_predicates": [],
        },
        claims=[],
        cadence_sources={"seed": {"cron": "", "cadence": "one_time", "state": "enabled"}},
        source_registry=registry,
        at=AT,
    )
    counts2 = json.loads(arts2[TRANSPARENCY_COUNTS_PATH])
    assert counts2["attributes"]["one_time_load"]["count"] == 1
    assert counts2["attributes"]["scheduled"]["count"] == 0
    assert counts2["attributes"]["not_scheduled"]["count"] == 0
