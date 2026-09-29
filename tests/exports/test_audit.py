# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Unit tests for the read-only public-surface audit (P27.1, LAUNCH.1).

These exercise the pure assembler + serialisers over synthetic query rows (no database), plus a
fake-connection round-trip of :func:`run_audit`. The Docker-gated seeded-spine end-to-end lives in
``tests/db/test_audit_spine.py``.
"""

from __future__ import annotations

import json

from exports.audit import (
    AUDIT_SCHEMA_VERSION,
    MODELING_TABLES,
    QUERIES,
    Fraction,
    build_spine_audit,
    redact_dsn,
    run_audit,
)


def _raw() -> dict[str, object]:
    """A representative raw result map mirroring the P27 pre-audit baseline shape."""
    return {
        "claim_total": 1_059_533,
        "claim_current_total": 1_059_533,
        "entity_total": 92_169,
        "source_total": 210,
        "source_permitted": 210,
        "entity_by_type": [("deployment", 92_165), ("organization", 4)],
        "sensitivity_by_tier": [(0, 1_059_533)],
        "licence_mix": [
            ("LicenseRef-PublicRecord-FactualCompilation", "yes", "yes", 372_869),
            (None, "UNDETERMINED", "UNDETERMINED", 256_172),
            ("CC0-1.0", "yes", "yes", 82_539),
            ("ODbL-1.0", "yes", "yes", 5_929),
        ],
        "redistributable_split": [("yes", 803_361), ("UNDETERMINED", 256_172)],
        "undetermined_by_connector": [
            ("procurement", 204_918),
            ("dot_511", 34_650),
            ("france_belgium_procurement", 14_462),
        ],
        "claims_by_connector": [("dot_511", 814_066), ("procurement", 204_918)],
        "geolocated_entities": 75_479,
        "geo_claims": [("camera_latitude", 93_305), ("camera_longitude", 93_305)],
        "value_geom_populated": 0,
        "jurisdiction_spread": [("FL", 12_953), ("GA", 7_049), (None, 16_859)],
        "observed_at_coverage": (113_000, "2020-01-01T00:00:00Z", "2026-09-20T00:00:00Z"),
        "modeling_tables": {t: 0 for t in MODELING_TABLES},
    }


def _audit():
    return build_spine_audit(
        _raw(),
        as_of="2026-09-22T12:00:00Z",
        generated_at="2026-09-22T12:00:00Z",
        spine_label="postgresql://sig@127.0.0.1:5433/sig",
        note="OSM land in flight",
    )


def test_totals_and_denominators() -> None:
    a = _audit()
    assert a.total_claims == 1_059_533
    assert a.total_entities == 92_169
    assert a.total_sources == 210
    # Publishable = sum of redistributable='yes' licence rows, with the total denominator.
    assert a.publishable.numerator == 372_869 + 82_539 + 5_929
    assert a.publishable.denominator == 1_059_533
    assert a.undetermined.numerator == 256_172
    assert a.geolocated.numerator == 75_479
    assert a.geolocated.denominator == 92_169


def test_never_a_bare_total_every_headline_carries_a_denominator() -> None:
    # §32 / SIG-METRIC-008: a headline count without a named denominator is forbidden.
    a = _audit()
    for frac in (a.publishable, a.undetermined, a.geolocated):
        rendered = frac.render()
        assert " of " in rendered and frac.label, rendered
        assert "%" in rendered


def test_fraction_zero_denominator_is_safe() -> None:
    assert Fraction(0, 0, "x").pct == 0.0
    assert Fraction(5, 0, "x").pct == 0.0


def test_markdown_reports_every_required_section() -> None:
    md = _audit().to_markdown()
    # AC2: licence mix, UNDETERMINED-by-connector, geolocated, jurisdiction, modeling gap + queries.
    assert "Licence mix" in md
    assert "UNDETERMINED rights by connector" in md
    assert "camera_latitude" in md
    assert "jurisdiction" in md.lower()
    assert "Modeling-table population" in md
    assert "Exact queries" in md
    # PROVISIONAL honesty + the re-audit obligation are stated up front.
    assert "PROVISIONAL" in md
    assert "re-audit" in md.lower()
    # Aggregate-only coordinates (Part VIII) — the report names the constraint.
    assert "aggregate" in md.lower()
    # Every query appears verbatim in the queries block.
    for query in QUERIES.values():
        assert query in md


def test_markdown_undetermined_by_connector_values() -> None:
    md = _audit().to_markdown()
    assert "procurement" in md
    assert "204,918" in md  # thousands-formatted


def test_json_is_deterministic_and_sorted() -> None:
    a = _audit()
    s1 = a.to_json_str()
    s2 = build_spine_audit(
        _raw(),
        as_of="2026-09-22T12:00:00Z",
        generated_at="2026-09-22T12:00:00Z",
        spine_label="postgresql://sig@127.0.0.1:5433/sig",
        note="OSM land in flight",
    ).to_json_str()
    assert s1 == s2  # deterministic bytes over the same inputs
    doc = json.loads(s1)
    assert doc["schema_version"] == AUDIT_SCHEMA_VERSION
    assert doc["totals"]["claims"] == 1_059_533
    assert doc["publishable"]["numerator"] == 372_869 + 82_539 + 5_929
    assert doc["undetermined"]["numerator"] == 256_172


def test_named_counts_are_resorted_deterministically() -> None:
    # Even if the raw rows arrive unsorted, the assembler re-sorts (count desc, name asc).
    raw = _raw()
    raw["undetermined_by_connector"] = [
        ("dot_511", 34_650),
        ("procurement", 204_918),
        ("france_belgium_procurement", 14_462),
    ]
    a = build_spine_audit(
        raw,
        as_of="x",
        generated_at="x",
        spine_label="s",
    )
    assert [n.name for n in a.undetermined_by_connector] == [
        "procurement",
        "dot_511",
        "france_belgium_procurement",
    ]


def test_null_jurisdiction_rendered_as_placeholder() -> None:
    a = _audit()
    names = [n.name for n in a.jurisdiction_spread]
    assert "(null)" in names  # the unresolved bucket is surfaced, not dropped


def test_modeling_tables_report_empty_state() -> None:
    a = _audit()
    assert all(m.empty for m in a.modeling_tables)
    assert {m.table for m in a.modeling_tables} == set(MODELING_TABLES)


def test_redact_dsn_strips_password_and_query() -> None:
    assert redact_dsn("postgresql://sig:secret@127.0.0.1:5433/sig?sslmode=disable") == (
        "postgresql://sig@127.0.0.1:5433/sig"
    )
    assert redact_dsn("postgresql://sig@host/db") == "postgresql://sig@host/db"
    assert "secret" not in redact_dsn("postgres://u:secret@h:1/d")


# --------------------------------------------------------------------------- #
# run_audit over a fake connection: proves the executor issues SET TRANSACTION #
# READ ONLY, runs only SELECTs, and assembles the same shape.                  #
# --------------------------------------------------------------------------- #


class _FakeCursor:
    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses
        self._last: object = None
        self.executed: list[str] = []

    def execute(self, query: str, params: object = None) -> None:
        self.executed.append(query)
        self._last = self._responses.get(query)

    def fetchone(self):
        val = self._last
        if val is None:
            return None
        if isinstance(val, list):
            return val[0] if val else None
        return val

    def fetchall(self):
        val = self._last
        if val is None:
            return []
        return list(val) if isinstance(val, list) else [val]


class _FakeConn:
    def __init__(self, responses: dict[str, object]) -> None:
        self._cur = _FakeCursor(responses)

    def cursor(self) -> _FakeCursor:
        return self._cur


def test_run_audit_is_read_only_and_only_selects() -> None:
    responses: dict[str, object] = {
        "SET default_transaction_read_only = on": None,
        QUERIES["claim_total"]: (1_059_533,),
        QUERIES["claim_current_total"]: (1_059_533,),
        QUERIES["entity_total"]: (92_169,),
        QUERIES["source_total"]: (210,),
        QUERIES["source_permitted"]: (210,),
        QUERIES["entity_by_type"]: [("deployment", 92_165)],
        QUERIES["sensitivity_by_tier"]: [(0, 1_059_533)],
        QUERIES["licence_mix"]: [("CC0-1.0", "yes", "yes", 1_059_533)],
        QUERIES["redistributable_split"]: [("yes", 1_059_533)],
        QUERIES["undetermined_by_connector"]: [],
        QUERIES["claims_by_connector"]: [("dot_511", 1_059_533)],
        QUERIES["geolocated_entities"]: (75_479,),
        QUERIES["geo_claims"]: [("camera_latitude", 93_305)],
        QUERIES["value_geom_populated"]: (0,),
        QUERIES["jurisdiction_spread"]: [("FL", 12_953)],
        QUERIES["observed_at_coverage"]: (113_000, "2020-01-01T00:00:00Z", "2026-09-20T00:00:00Z"),
    }
    for table in MODELING_TABLES:
        responses[f"SELECT count(*) FROM {table}"] = (0,)

    conn = _FakeConn(responses)
    audit = run_audit(conn, as_of="2026-09-22", note="test", spine_label="fake")

    # The first statement puts the session read-only (fail-closed).
    assert conn._cur.executed[0] == "SET default_transaction_read_only = on"
    # Every statement issued is a read (the read-only SET or a SELECT) — never a write.
    for stmt in conn._cur.executed:
        upper = stmt.strip().upper()
        assert upper.startswith("SELECT") or upper == "SET DEFAULT_TRANSACTION_READ_ONLY = ON", stmt
        for forbidden in ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE"):
            assert forbidden not in upper, stmt
    assert audit.total_claims == 1_059_533
    assert audit.publishable.numerator == 1_059_533


def test_query_set_covers_the_ticket_deliverables() -> None:
    # The ticket names each of these; guard against a query being dropped.
    for key in (
        "claim_total",
        "entity_total",
        "source_total",
        "licence_mix",
        "undetermined_by_connector",
        "geolocated_entities",
        "jurisdiction_spread",
        "value_geom_populated",
    ):
        assert key in QUERIES


# --------------------------------------------------------------------------- #
# P27.2 / ADR-095: the effective (post-decision) rights view                    #
# --------------------------------------------------------------------------- #


def _raw_with_decisions() -> dict[str, object]:
    raw = _raw()
    raw["effective_licence_mix"] = [
        ("LicenseRef-PublicRecord-FactualCompilation", "yes", "yes", 372_869),
        ("CC0-1.0", "yes", "yes", 300_000),
        ("CC-BY-4.0", "yes", "yes", 150_000),
        ("LicenceOuverte-2.0", "yes", "yes", 14_462),
        ("ODbL-1.0", "yes", "yes", 5_929),
        ("LicenseRef-MuckRock-API-ToS", "no", "no", 6),
        (None, "UNDETERMINED", "UNDETERMINED", 200),
    ]
    raw["effective_redistributable_split"] = [
        ("yes", 843_260),
        ("no", 6),
        ("UNDETERMINED", 200),
    ]
    raw["effective_undetermined_by_connector"] = [("procurement", 200)]
    raw["rights_decisions"] = [
        ("ted_eu", "CC-BY-4.0", "yes", "maintainer (delegated)", "2026-09-22T18:00:00Z", "p", "r"),
        (
            "muckrock",
            "LicenseRef-MuckRock-API-ToS",
            "no",
            "maintainer (delegated)",
            "2026-09-22T18:00:00Z",
            "p",
            "r",
        ),
    ]
    return raw


def _audit_effective():
    return build_spine_audit(
        _raw_with_decisions(),
        as_of="2026-09-22T18:00:00Z",
        generated_at="2026-09-22T18:00:00Z",
        spine_label="postgresql://sig@127.0.0.1:5433/sig",
        note="post-decision",
    )


def test_effective_fractions_carry_denominators() -> None:
    a = _audit_effective()
    assert a.publishable_effective is not None
    assert a.publishable_effective.numerator == 372_869 + 300_000 + 150_000 + 14_462 + 5_929
    assert a.publishable_effective.denominator == 1_059_533
    assert a.undetermined_effective is not None
    assert a.undetermined_effective.numerator == 200
    assert a.undetermined_effective.denominator == 1_059_533
    # Recorded (as-asserted) fractions are untouched — the two views never conflate.
    assert a.undetermined.numerator == 256_172


def test_effective_markdown_section_and_decision_trail() -> None:
    md = _audit_effective().to_markdown()
    assert "Effective rights" in md
    assert "post-decision" in md
    assert "LicenceOuverte-2.0" in md
    assert "ted_eu" in md and "maintainer (delegated)" in md  # the decision trail is verbatim
    assert "rights_decision" in md  # the mechanism is named


def test_no_decision_table_reports_not_measured() -> None:
    """A pre-P27.2 spine has no effective view — fields are None, never fake zeros."""
    a = _audit()  # _raw() carries no effective_* keys
    assert a.effective_licence_mix is None
    assert a.publishable_effective is None
    doc = json.loads(a.to_json_str())
    assert doc["effective_licence_mix"] is None
    assert doc["publishable_effective"] is None
    md = a.to_markdown()
    assert "Effective rights" not in md
