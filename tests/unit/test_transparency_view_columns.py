# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.33 — the view-column closure test (J3 §3.3 items 1–2 + S-12).

The sqitch deploy script and the Python allow-lists must name *exactly* the
same columns: a drift either drops a transparency field the ticket promised
or — worse — smuggles an unreviewed column past the scrub boundary. This
test parses the outer SELECT list of each ``v_transparency_*`` view and
asserts closure against ``policy.transparency.TRANSPARENCY_*_VIEW_COLUMNS``,
and that no never-exported field name appears in the deploy script.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from policy.transparency import (
    NEVER_EXPORTED_FIELDS,
    TRANSPARENCY_CAPTURE_VIEW_COLUMNS,
    TRANSPARENCY_RUN_VIEW_COLUMNS,
)

DEPLOY = Path(__file__).resolve().parents[2] / "db" / "deploy" / "transparency_views.sql"


def _split_top_level(select_list: str) -> list[str]:
    """Split a SELECT list on commas at paren depth 0 (CASE/COALESCE args
    nest inside parens — they must not split)."""
    items, depth, buf = [], 0, []
    for ch in select_list:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            items.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        items.append("".join(buf))
    return items


def _column_name(expr: str) -> str:
    expr = expr.strip().rstrip(",")
    m = re.search(r"\bAS\s+(\w+)\s*(?:--[^\n]*)?$", expr, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"(?:\w+)\.(\w+)$", expr)
    if m:
        return m.group(1)
    return expr


def _view_columns(sql: str, view: str, from_marker: str) -> list[str]:
    """The outer SELECT list's output names — the SELECT nearest before the
    outer FROM (the CTE selects sit earlier in the same statement)."""
    start = sql.index(f"CREATE VIEW {view} AS")
    end = sql.index("GRANT SELECT ON", start)
    body = sql[start:end]
    from_at = body.index(from_marker)
    # Last SELECT keyword before the outer FROM.
    sel_at = body.rindex("SELECT", 0, from_at)
    select_list = body[sel_at + len("SELECT") : from_at]
    return [_column_name(i) for i in _split_top_level(select_list)]


def _strip_comments(sql: str) -> str:
    return "\n".join(line.split("--", 1)[0] for line in sql.splitlines())


def test_no_select_star_and_no_never_exported_names():
    sql = DEPLOY.read_text()
    assert not re.search(r"SELECT\s+\*", _strip_comments(sql), re.IGNORECASE)
    for field in NEVER_EXPORTED_FIELDS:
        # Word-boundary match — a never-exported column name may only appear
        # inside a comment (naming the rule), never in the view's SQL.
        for m in re.finditer(rf"\b{re.escape(field)}\b", sql):
            line_start = sql.rfind("\n", 0, m.start()) + 1
            line = sql[line_start : sql.find("\n", m.end())]
            comment_at = line.find("--")
            in_comment = comment_at != -1 and comment_at < m.start() - line_start
            stripped = line.lstrip()
            assert in_comment or stripped.startswith("--"), (
                f"never-exported {field!r} outside a comment: {stripped}"
            )


def test_run_view_columns_match_allow_list():
    sql = DEPLOY.read_text()
    cols = _view_columns(sql, "v_transparency_run", "FROM ingest_run_report rr")
    assert cols == list(TRANSPARENCY_RUN_VIEW_COLUMNS)


def test_capture_view_columns_match_allow_list():
    sql = DEPLOY.read_text()
    cols = _view_columns(sql, "v_transparency_capture", "FROM ingest_run_capture irc")
    assert cols == list(TRANSPARENCY_CAPTURE_VIEW_COLUMNS)


def test_allow_lists_carry_no_never_exported_field():
    for cols in (TRANSPARENCY_RUN_VIEW_COLUMNS, TRANSPARENCY_CAPTURE_VIEW_COLUMNS):
        assert not NEVER_EXPORTED_FIELDS.intersection(cols)


def test_export_queries_select_the_allow_list_verbatim():
    """TRANSPARENCY_QUERIES must select exactly the allow-listed columns from
    the views — a hand-typed drift either fails at the DB or silently drops
    a column the scrub relies on."""
    from exports.transparency import TRANSPARENCY_QUERIES

    for key, columns, view in (
        ("transparency_runs", TRANSPARENCY_RUN_VIEW_COLUMNS, "v_transparency_run"),
        ("transparency_captures", TRANSPARENCY_CAPTURE_VIEW_COLUMNS, "v_transparency_capture"),
    ):
        relation, sql = TRANSPARENCY_QUERIES[key]
        assert relation == view
        m = re.match(r"SELECT (.*) FROM", sql)
        assert m is not None
        selected = [c.strip() for c in m.group(1).split(",")]
        assert selected == list(columns)


def test_verify_script_selects_the_same_columns():
    """The sqitch verify script's explicit-column selects must match the
    allow-lists — a drift means the deploy check and the runtime contract
    test different surfaces."""
    verify = _strip_comments((DEPLOY.parents[1] / "verify" / "transparency_views.sql").read_text())
    for view, cols in (
        ("v_transparency_run", TRANSPARENCY_RUN_VIEW_COLUMNS),
        ("v_transparency_capture", TRANSPARENCY_CAPTURE_VIEW_COLUMNS),
    ):
        stmt = next(
            (
                s
                for s in verify.split(";")
                if re.search(rf"\bFROM {view}\b", s) and "WHERE FALSE" in s
            ),
            None,
        )
        assert stmt is not None, view
        m = re.search(r"SELECT\s+(.*?)\s+FROM", stmt, re.S)
        assert m is not None, view
        selected = [c.strip() for c in m.group(1).split(",")]
        assert selected == list(cols)


@pytest.mark.parametrize("view", ["v_transparency_run", "v_transparency_capture"])
def test_grant_targets_sig_export(view):
    sql = DEPLOY.read_text()
    assert f"GRANT SELECT ON {view} TO sig_export" in sql
    assert "sig_read_public" not in sql
