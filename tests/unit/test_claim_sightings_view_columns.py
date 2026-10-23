# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.44 (T2, DSRC-01) — the ``v_claim_sightings`` column-closure test.

The sqitch deploy script, the Python allow-list
(``policy.transparency.CLAIM_SIGHTING_VIEW_COLUMNS``), the export query's
explicit SELECT, and the sqitch verify script must name *exactly* the same
columns — a drift either drops a sighting field the ticket promised or
smuggles an unreviewed column (locator / excerpt / digest / OCFL id) past
the scrub boundary.
"""

from __future__ import annotations

import re
from pathlib import Path

from policy.transparency import CLAIM_SIGHTING_VIEW_COLUMNS, NEVER_EXPORTED_FIELDS

DB = Path(__file__).resolve().parents[2] / "db"
DEPLOY = DB / "deploy" / "claim_sightings.sql"
VERIFY = DB / "verify" / "claim_sightings.sql"
REVERT = DB / "revert" / "claim_sightings.sql"
VIEW = "v_claim_sightings"


def _strip_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def _split_top_level(select_list: str) -> list[str]:
    """Split a SELECT list on top-level commas — parens and quoted strings
    (``date_trunc('month', …)``) must not split an item."""
    items: list[str] = []
    depth = 0
    in_str = False
    current: list[str] = []
    for ch in select_list:
        if in_str:
            current.append(ch)
            if ch == "'":
                in_str = False
            continue
        if ch == "'":
            in_str = True
        elif ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            items.append("".join(current))
            current = []
            continue
        current.append(ch)
    if current:
        items.append("".join(current))
    return items


def _column_name(item: str) -> str:
    """The emitted column name of one SELECT item — the ``AS`` alias when
    present, else the unqualified, un-cast column (``c.claim_id::text`` →
    ``claim_id``)."""
    item = item.strip()
    m = re.search(r"\bAS\s+(\w+)\s*$", item, re.IGNORECASE)
    if m:
        return m.group(1)
    last = item.split()[-1]
    last = re.sub(r"::[\w\[\]]+", "", last)
    return last.split(".")[-1]


def _view_columns(sql: str) -> list[str]:
    """The outer SELECT list's explicit column names."""
    m = re.search(rf"CREATE (?:OR REPLACE )?VIEW {re.escape(VIEW)} AS(.*?);", sql, re.DOTALL)
    assert m is not None, f"deploy script does not define {VIEW}"
    body = m.group(1)
    sel_at = body.index("SELECT")
    from_at = body.index("FROM", sel_at)
    select_list = body[sel_at + len("SELECT") : from_at]
    return [_column_name(c) for c in _split_top_level(select_list)]


def _plan_lines() -> list[str]:
    return [
        line.strip()
        for line in (DB / "sqitch.plan").read_text().splitlines()
        if line.strip() and not line.strip().startswith(("#", "%"))
    ]


def test_view_columns_match_allow_list() -> None:
    assert _view_columns(_strip_comments(DEPLOY.read_text())) == list(CLAIM_SIGHTING_VIEW_COLUMNS)


def test_allow_list_carries_no_never_exported_field() -> None:
    assert not NEVER_EXPORTED_FIELDS.intersection(CLAIM_SIGHTING_VIEW_COLUMNS)


def test_deploy_is_explicit_columns_no_never_exported_no_star() -> None:
    sql = DEPLOY.read_text()
    assert not re.search(r"SELECT\s+\*", _strip_comments(sql), re.IGNORECASE)
    for field in NEVER_EXPORTED_FIELDS:
        for m in re.finditer(rf"\b{re.escape(field)}\b", sql):
            line_start = sql.rfind("\n", 0, m.start()) + 1
            line_end = sql.find("\n", m.end())
            line = sql[line_start : line_end if line_end != -1 else len(sql)]
            comment_at = line.find("--")
            assert comment_at != -1 and comment_at < m.start() - line_start, (
                f"never-exported {field!r} outside a comment: {line.strip()}"
            )
    # The raw claim_evidence columns the view must NOT expose.
    for field in ("locator", "excerpt", "weight_note", "extraction_id"):
        cols = _view_columns(_strip_comments(sql))
        assert field not in cols


def test_view_joins_establishes_only() -> None:
    """K5 §3.1 + the §16.5 evidence-role vocabulary: a ``contradicts`` (or
    ``corroborates``…) binding is evidence, never a sighting — the view's
    WHERE clause pins ``role = 'establishes'``."""
    sql = _strip_comments(DEPLOY.read_text())
    assert re.search(r"WHERE\s+ce\.role\s*=\s*'establishes'", sql)


def test_grant_boundary_sig_export_only() -> None:
    sql = DEPLOY.read_text()
    assert re.search(rf"GRANT SELECT ON {re.escape(VIEW)} TO sig_export", sql)
    assert "sig_read_public" not in sql


def test_revert_drops_the_view() -> None:
    sql = _strip_comments(REVERT.read_text())
    assert re.search(rf"DROP VIEW (?:IF EXISTS )?{re.escape(VIEW)}", sql)


def test_plan_entry_orders_after_dependencies() -> None:
    names = [line.split()[0] for line in _plan_lines()]
    assert "claim_sightings" in names
    idx = names.index("claim_sightings")
    assert names.index("claim_assertion_bindings") < idx
    assert names.index("access_control") < idx


def test_verify_script_selects_the_same_columns() -> None:
    sql = _strip_comments(VERIFY.read_text())
    m = re.search(r"SELECT\s+(.*?)\s+FROM v_claim_sightings", sql, re.DOTALL)
    assert m is not None, "verify script does not select from the view"
    selected = [c.strip() for c in m.group(1).split(",")]
    assert selected == list(CLAIM_SIGHTING_VIEW_COLUMNS)


def test_export_query_reads_the_view() -> None:
    """``EXPORT_QUERIES["claim_sightings"]`` must be the K5 §3.1 aggregate
    over ``v_claim_sightings`` — the declared relation is the row guard and
    the FROM names the view (the accumulator's read never re-derives the
    edge list from the raw tables)."""
    from exports.spine_export import EXPORT_QUERIES

    relation, sql = EXPORT_QUERIES["claim_sightings"]
    assert relation == VIEW
    assert re.search(r"FROM\s+v_claim_sightings\b", sql)


def test_export_query_aggregate_fields_match_the_constant() -> None:
    """The aggregate SELECT's output names must equal
    ``CLAIM_SIGHTINGS_COLUMNS`` — the accumulator's positional row
    contract."""
    from exports.dossier_sources import CLAIM_SIGHTINGS_COLUMNS
    from exports.spine_export import EXPORT_QUERIES

    _, sql = EXPORT_QUERIES["claim_sightings"]
    m = re.search(r"SELECT(.*?)FROM v_claim_sightings", sql, re.DOTALL)
    assert m is not None
    out_names = [_column_name(c) for c in _split_top_level(m.group(1))]
    assert out_names == list(CLAIM_SIGHTINGS_COLUMNS)


def test_export_query_carries_the_gates() -> None:
    """K5 §3.1 + DSRC-01: the sighting aggregate re-uses the shared
    publishable-claim gates — a missing token means the read drifts from
    the claims read's basis."""
    from exports.spine_export import EXPORT_QUERIES

    _, sql = EXPORT_QUERIES["claim_sightings"]
    for token in (
        "{EFFECTIVE}",  # the latest_decision CTE the rights gate consults
        "{PUB_CLAIM_GATE}",  # subject + object-entity + claim dispositions
        "{PUB_ARTIFACT_GATE}",  # a withheld artifact's sightings never count
        "{CAPTURE_SEAL_GATE}",  # a capture under a current seal loses its binding
        "{SIGHTING_BOUND}",  # the belief bound on bound_at
        "latest_decision",
        "redistributable = 'yes'",
        "sensitivity_tier = 0",
        "upper_inf(c.sys_period)",
        "GROUP BY 1,2,3,4",
    ):
        assert token in sql, f"claim_sightings query missing {token!r}"


def test_export_fields_carry_no_never_exported_name() -> None:
    from exports.dossier_sources import CLAIM_SIGHTINGS_COLUMNS

    assert not NEVER_EXPORTED_FIELDS.intersection(CLAIM_SIGHTINGS_COLUMNS)
