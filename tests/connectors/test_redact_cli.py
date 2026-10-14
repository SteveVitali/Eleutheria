# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The ``sig-connectors redact-*`` verbs (P36.15; SIG-PUB-015/016).

The operator-facing seam: propose a redaction (a review_item lands), a human
records the decision on the queue (fixture decisions here), and apply writes
the derivative OCFL object. Apply refuses (exit 3) with no recorded accept.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from connectors.capture_ocfl import OcflCaptureStore
from connectors.cli import main
from evidence.digest import multihash
from evidence.ocfl import OcflStore
from evidence.storage import LocalFileStore
from resolution.review_queue import ReviewQueue

PARENT = "Record: Officer Jane M. Doe signed. Total $1.2M."
DIGEST = multihash(PARENT.encode())


@pytest.fixture()
def env(tmp_path: Path) -> dict[str, object]:
    capdir = tmp_path / "caps"
    store = OcflCaptureStore(OcflStore(LocalFileStore(str(capdir))))
    store.put(PARENT.encode(), media_type="text/plain", source_uri="urn:x")
    return {"capdir": capdir, "queue": tmp_path / "queue.json"}


def _propose(env: dict[str, object]) -> int:
    return main(
        [
            "redact-propose",
            "--capture-dir",
            str(env["capdir"]),
            "--parent-capture-id",
            "cap-1",
            "--parent-digest",
            DIGEST,
            "--media-type",
            "text/plain",
            "--method",
            "text-layer-substitution",
            "--version",
            "1",
            "--text",
            "Jane M. Doe",
            "--queue-json",
            str(env["queue"]),
        ]
    )


def test_redact_propose_lands_a_review_item(env, capsys) -> None:
    assert _propose(env) == 0
    out = json.loads(capsys.readouterr().out.split("\nnext:")[0])
    assert out["inserted"] is True
    queue = ReviewQueue.from_dict(json.loads(Path(env["queue"]).read_text()))
    assert len(queue.pending()) == 1
    item = queue.pending()[0]
    assert item.kind == "redaction"
    assert "Jane M. Doe" not in json.dumps(item.to_row())


def test_redact_apply_refuses_without_a_review(env, capsys) -> None:
    assert _propose(env) == 0
    capsys.readouterr()
    item = ReviewQueue.from_dict(json.loads(Path(env["queue"]).read_text())).pending()[0]
    assert (
        main(
            [
                "redact-apply",
                "--capture-dir",
                str(env["capdir"]),
                "--item",
                item.item_id,
                "--queue-json",
                str(env["queue"]),
            ]
        )
        == 3
    )
    assert "REFUSED" in capsys.readouterr().err


def test_redact_apply_after_a_recorded_accept_writes_the_derivative(env, capsys) -> None:
    assert _propose(env) == 0
    capsys.readouterr()
    qpath = Path(env["queue"])
    queue = ReviewQueue.from_dict(json.loads(qpath.read_text()))
    item = queue.pending()[0]
    queue.decide(item.item_id, "accept", reviewer="records officer")
    qpath.write_text(json.dumps(queue.to_dict()))

    assert (
        main(
            [
                "redact-apply",
                "--capture-dir",
                str(env["capdir"]),
                "--item",
                item.item_id,
                "--queue-json",
                str(env["queue"]),
            ]
        )
        == 0
    )
    row = json.loads(capsys.readouterr().out)
    assert row["record"]["review"]["reviewer_role"] == "records officer"
    # The derivative object exists and omits the redacted text physically.
    store = OcflCaptureStore(OcflStore(LocalFileStore(str(env["capdir"]))))
    deriv_bytes = store.get(row["derivative_digest"])
    assert b"Jane M. Doe" not in deriv_bytes
    assert b"[redacted]" in deriv_bytes


def test_redact_propose_needs_a_queue(env, capsys) -> None:
    assert (
        main(
            [
                "redact-propose",
                "--capture-dir",
                str(env["capdir"]),
                "--parent-capture-id",
                "cap-1",
                "--parent-digest",
                DIGEST,
                "--media-type",
                "text/plain",
                "--method",
                "m",
                "--version",
                "1",
                "--text",
                "Jane",
            ]
        )
        == 2
    )
