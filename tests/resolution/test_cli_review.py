# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The review-queue curation CLI (SIG-ENG-013): `review enqueue` scores records and
enqueues the PROPOSED proposals, `review list`/`show` surface the confidence explanation
inline (SIG-IDENT-025), and `review decide` records a human accept/reject that persists
across invocations (SIG-IDENT-026)."""

from __future__ import annotations

import json

import pytest
from resolution.cli import main

_RECORDS = [
    {
        "unique_id": "b1",
        "normalized_name": "los angeles police department",
        "name_first_token": "los",
        "state": "CA",
        "organization_class": "us.le.municipal_police",
    },
    {
        "unique_id": "b2",
        "normalized_name": "los angeles police dept",
        "name_first_token": "los",
        "state": "CA",
        "organization_class": "us.le.municipal_police",
    },
]


def _records_file(tmp_path) -> str:
    path = tmp_path / "records.json"
    path.write_text(json.dumps(_RECORDS), encoding="utf-8")
    return str(path)


def test_enqueue_list_and_decide_flow(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    queue = str(tmp_path / "queue.json")
    records = _records_file(tmp_path)

    assert main(["review", "enqueue", queue, records]) == 0
    enqueue_out = capsys.readouterr().out
    assert "enqueued" in enqueue_out

    assert main(["review", "list", queue]) == 0
    list_out = capsys.readouterr().out
    assert "er_match:b1~b2" in list_out
    # the per-comparison confidence explanation is surfaced inline (SIG-IDENT-025)
    assert "overall match weight" in list_out
    assert "normalized_name" in list_out

    assert main(["review", "decide", queue, "er_match:b1~b2", "accept", "--reviewer", "alice"]) == 0
    decide_out = capsys.readouterr().out
    assert "accept by alice" in decide_out

    # the decision persisted: the item is no longer pending
    assert main(["review", "list", queue]) == 0
    assert "no pending proposals" in capsys.readouterr().out


def test_decide_on_a_missing_item_reports_and_exits_nonzero(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    queue = str(tmp_path / "queue.json")
    main(["review", "enqueue", queue, _records_file(tmp_path)])
    capsys.readouterr()
    code = main(["review", "decide", queue, "er_match:nope~nope", "reject", "--reviewer", "bob"])
    assert code == 2
    assert "no pending review item" in capsys.readouterr().out
