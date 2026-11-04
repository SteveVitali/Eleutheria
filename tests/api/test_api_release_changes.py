# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.67 / K13 TX-14 (SIG-TRANSP-024): ``/v1/changes`` is backed by the
release's own record-id diff — the manifest-pinned
``sig.release-changes-feed/1`` doc at
``r/<pub>/transparency/changes/changes.json`` — through the same verified,
withdrawal-checked serving path as the api slice."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from api.release_serving import ReleaseServingError, ReleaseServingStore
from exports.release import activate, build_release
from starlette.testclient import TestClient

from api import create_app

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "exports"))
from test_release import _write_export  # noqa: E402

REV = "cd" * 32


def _registry_with_two_releases(tmp_path: Path) -> tuple[Path, str, str]:
    e1 = _write_export(tmp_path / "e1", n_records=3)
    b1 = build_release(e1, tmp_path / "r1", renderer_revision=REV, descriptor_version=1)
    e2 = _write_export(tmp_path / "e2", n_records=4)
    rows = [
        json.loads(line) for line in (e2 / "sig_graph" / "sites.jsonl").read_text().splitlines()
    ]
    rows[0]["label"] = "Renamed site 0"
    del rows[1]
    (e2 / "sig_graph" / "sites.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    b2 = build_release(
        e2,
        tmp_path / "r2",
        renderer_revision=REV,
        descriptor_version=1,
        previous_release=tmp_path / "r1",
    )
    reg = tmp_path / "registry"
    (reg / "staged").mkdir(parents=True)
    activate(reg, tmp_path / "r1")
    activate(reg, tmp_path / "r2")
    return reg, b1.publication_id, b2.publication_id


@pytest.fixture
def serving(tmp_path: Path) -> tuple[ReleaseServingStore, str, str]:
    reg, p1, p2 = _registry_with_two_releases(tmp_path)
    return ReleaseServingStore(reg), p1, p2


def test_changes_document_serves_the_release_diff(serving) -> None:
    store, _p1, p2 = serving
    payload, ident = store.changes_document(None)
    assert ident.publication_id == p2
    assert payload["schema"] == "sig.release-changes-feed/1"
    assert payload["baseline"] is False
    assert payload["release"]["publication_id"] == p2
    kinds = {e["change_type"] for e in payload["events"]}
    assert kinds == {"added", "removed", "changed"}
    assert all(e["new_date"] for e in payload["events"])


def test_changes_document_release_param_selects_any_promoted(serving) -> None:
    store, p1, _p2 = serving
    payload, ident = store.changes_document(p1)
    assert ident.publication_id == p1
    assert payload["baseline"] is True  # the first release is the baseline
    assert payload["previous"] is None


def test_changes_document_refuses_unknown_and_absent(serving, tmp_path: Path) -> None:
    store, p1, _p2 = serving
    with pytest.raises(ReleaseServingError) as err:
        store.changes_document("p-" + "0" * 64)
    assert err.value.code == "unknown_publication"
    # a release that predates the changes doc answers the typed absence —
    # never a fabricated diff
    rel = f"r/{p1}/transparency/changes/changes.json"
    (store.staged / rel).unlink()
    with pytest.raises(ReleaseServingError) as err2:
        store.changes_document(p1, absent_status=503, absent_code="release_artifact_absent")
    assert err2.value.status == 503


def test_v1_changes_route_serves_the_release(serving, store) -> None:
    serving_store, _p1, p2 = serving
    client = TestClient(create_app(store, release_serving=serving_store))
    body = client.get("/v1/changes").json()
    assert body["schema"] == "sig.release-changes-feed/1"
    assert body["release"]["publication_id"] == p2
    # the since filter applies to the release doc's events unchanged
    all_events = client.get("/v1/changes", params={"since": "2020-01-01"}).json()["events"]
    none_events = client.get("/v1/changes", params={"since": "2999-01-01"}).json()["events"]  # future-ok: synthetic: a far-future since cursor yields no events
    assert len(all_events) == len(body["events"]) and none_events == []
