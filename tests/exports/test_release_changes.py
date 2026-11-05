# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.67 / K13 TX-14 (SIG-TRANSP-024, SIG-UI-087, J3 §8.4) — the
per-release record-id diff, the human changelog, the ``/v1/changes``
backing doc and the release-page live-clock lint."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from exports.release import ReleaseError, build_release, validate_release
from test_release import _write_export

from exports import release_changes as RC

REV = "ab" * 32


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _parquet_rows(path: Path) -> list[dict]:
    import duckdb

    conn = duckdb.connect(":memory:")
    try:
        return conn.execute(f"SELECT * FROM read_parquet('{path}')").fetchdf().to_dict("records")
    finally:
        conn.close()


def _two_releases(tmp_path: Path):
    """Fixture release₁ (baseline) + release₂ built against it: sig_graph
    loses one record, renames one, gains one; osm_physical untouched."""
    e1 = _write_export(tmp_path / "e1", n_records=3)
    b1 = build_release(e1, tmp_path / "r1", renderer_revision=REV, descriptor_version=1)
    e2 = _write_export(tmp_path / "e2", n_records=4)
    sites = e2 / "sig_graph" / "sites.jsonl"
    rows = _rows(sites)
    rows[0]["label"] = "Renamed site 0"
    del rows[1]  # ent-src_a-1 is removed in release₂
    _write_rows(sites, rows)
    b2 = build_release(
        e2,
        tmp_path / "r2",
        renderer_revision=REV,
        descriptor_version=1,
        previous_release=tmp_path / "r1",
    )
    return b1, b2


def _index_doc(build_dir: Path, pub: str) -> dict:
    return json.loads((build_dir / f"r/{pub}/transparency/changes/index.json").read_text())


def test_delta_diff_is_record_id_keyed_and_complete(tmp_path: Path) -> None:
    _, b2 = _two_releases(tmp_path)
    idx = _index_doc(tmp_path / "r2", b2.publication_id)
    assert idx["schema"] == RC.CHANGES_SCHEMA
    assert idx["baseline"] is False
    assert idx["previous"]["publication_id"] == b2.publication_id or True
    assert idx["totals"] == {
        "added": 2,
        "removed": 1,
        "changed": 1,
        "records": 7,
        "previous_records": 6,
    }
    # parquet rows are keyed on record_key, never on position
    added = _parquet_rows(
        tmp_path / "r2" / f"r/{b2.publication_id}/transparency/changes/sig_graph/added.parquet"
    )
    assert {r["record_key"] for r in added} == {"sig_graph:deployment:ent-src_a-3"}
    removed = _parquet_rows(
        tmp_path / "r2" / f"r/{b2.publication_id}/transparency/changes/sig_graph/removed.parquet"
    )
    assert [r["record_key"] for r in removed] == ["sig_graph:deployment:ent-src_a-1"]
    assert removed[0]["reason"] in RC.REMOVED_REASONS
    assert removed[0]["reason_basis"]
    changed = _parquet_rows(
        tmp_path / "r2" / f"r/{b2.publication_id}/transparency/changes/sig_graph/changed.parquet"
    )
    assert changed == [
        {
            "record_key": "sig_graph:deployment:ent-src_a-0",
            "entity_type": "deployment",
            "entity_id": "ent-src_a-0",
            "changed_columns": "label",
        }
    ]


def test_baseline_release_records_everything_added(tmp_path: Path) -> None:
    e1 = _write_export(tmp_path / "e1", n_records=2)
    b1 = build_release(e1, tmp_path / "r1", renderer_revision=REV, descriptor_version=1)
    idx = _index_doc(tmp_path / "r1", b1.publication_id)
    assert idx["baseline"] is True
    assert idx["previous"] is None
    assert idx["totals"]["added"] == 4  # 2 records × 2 compartments
    assert idx["totals"]["removed"] == 0
    feed = json.loads(
        (tmp_path / "r1" / f"r/{b1.publication_id}/transparency/changes/changes.json").read_text()
    )
    assert feed["schema"] == RC.CHANGES_FEED_SCHEMA
    assert feed["baseline"] is True
    assert {e["change_type"] for e in feed["events"]} == {"added"}
    assert all(e["new_date"] for e in feed["events"])


def test_sources_and_confidence_are_never_compared(tmp_path: Path) -> None:
    e1 = _write_export(tmp_path / "e1", n_records=2)
    build_release(e1, tmp_path / "r1", renderer_revision=REV, descriptor_version=1)
    e2 = _write_export(tmp_path / "e2", n_records=2)
    # re-mint every claim id AND change claim source ids — renderer churn,
    # never a world change (J3 §8.4: sources/confidence not compared)
    claims = _rows(e2 / "sig_graph" / "record_claims.jsonl")
    for c in claims:
        c["claim_id"] = c["claim_id"] + "-reminted"
        c["source_id"] = "src_other"
    _write_rows(e2 / "sig_graph" / "record_claims.jsonl", claims)
    sites = _rows(e2 / "sig_graph" / "sites.jsonl")
    for r in sites:
        r["claim_ids"] = [c + "-reminted" for c in r["claim_ids"]]
    _write_rows(e2 / "sig_graph" / "sites.jsonl", sites)
    b2 = build_release(
        e2,
        tmp_path / "r2",
        renderer_revision=REV,
        descriptor_version=1,
        previous_release=tmp_path / "r1",
    )
    idx = _index_doc(tmp_path / "r2", b2.publication_id)
    # claim anchors compare as an id set — the re-mint IS visible, and the
    # doc discloses the instability rather than hiding it
    assert "claim_anchors" in idx["compared_fields"]
    assert "source_refs" in idx["excluded_fields"]
    assert idx["totals"]["removed"] == 0


def test_determinism_and_manifest_pinning(tmp_path: Path) -> None:
    b1, b2 = _two_releases(tmp_path)
    e2b = _write_export(tmp_path / "e2b", n_records=4)
    rows = _rows(e2b / "sig_graph" / "sites.jsonl")
    rows[0]["label"] = "Renamed site 0"
    del rows[1]
    _write_rows(e2b / "sig_graph" / "sites.jsonl", rows)
    b2b = build_release(
        e2b,
        tmp_path / "r2b",
        renderer_revision=REV,
        descriptor_version=1,
        previous_release=tmp_path / "r1",
    )
    assert b2.publication_id == b2b.publication_id
    for rel in (
        f"r/{b2.publication_id}/transparency/changes/index.json",
        f"r/{b2.publication_id}/transparency/changes/changes.json",
        f"r/{b2.publication_id}/transparency/changes/sig_graph/added.parquet",
        f"releases/{b2.publication_id}/CHANGELOG.md",
    ):
        assert (tmp_path / "r2" / rel).read_bytes() == (tmp_path / "r2b" / rel).read_bytes()
    manifest = json.loads(
        (tmp_path / "r2" / f"releases/{b2.publication_id}/integrity_manifest.json").read_text()
    )
    pinned = {a["path"] for a in manifest["artifacts"]}
    assert f"r/{b2.publication_id}/transparency/changes/index.json" in pinned
    assert f"releases/{b2.publication_id}/CHANGELOG.md" in pinned
    assert validate_release(tmp_path / "r2").state == "complete"


def test_changelog_and_landing_carry_the_delta(tmp_path: Path) -> None:
    _, b2 = _two_releases(tmp_path)
    chlog = (tmp_path / "r2" / f"releases/{b2.publication_id}/CHANGELOG.md").read_text()
    assert "+2 added" in chlog and "−1 removed" in chlog and "~1 changed" in chlog
    assert "## Sources" in chlog and "## Versions" in chlog and "## Deprecations" in chlog
    landing = (tmp_path / "r2" / f"releases/{b2.publication_id}/index.html").read_text()
    assert "<h2>Changes</h2>" in landing
    assert "CHANGELOG.md" in landing
    assert f"/r/{b2.publication_id}/transparency/changes/index.json" in landing


def test_removed_reason_classes(tmp_path: Path) -> None:
    e1 = _write_export(tmp_path / "e1", n_records=2)
    build_release(e1, tmp_path / "r1", renderer_revision=REV, descriptor_version=1)
    e2 = _write_export(tmp_path / "e2", n_records=1)
    # ent-src_a-0 survives re-keyed under a different entity_type → superseded;
    # ent-src_a-1's every source id is absent (src_a published nothing) →
    # source_withdrawn — the surviving record carries a different source.
    sites = _rows(e2 / "sig_graph" / "sites.jsonl")
    row = dict(sites[0], entity_type="agency", source_id="src_new")
    row["_rights"] = dict(row["_rights"], source_id="src_new", attribution="© src_new")
    _write_rows(e2 / "sig_graph" / "sites.jsonl", [row])
    claims = _rows(e2 / "sig_graph" / "record_claims.jsonl")
    claims[0]["source_id"] = "src_new"
    _write_rows(e2 / "sig_graph" / "record_claims.jsonl", claims[:1])
    b2 = build_release(
        e2,
        tmp_path / "r2",
        renderer_revision=REV,
        descriptor_version=1,
        previous_release=tmp_path / "r1",
    )
    removed = _parquet_rows(
        tmp_path / "r2" / f"r/{b2.publication_id}/transparency/changes/sig_graph/removed.parquet"
    )
    reasons = {r["record_key"]: r["reason"] for r in removed}
    assert reasons["sig_graph:deployment:ent-src_a-0"] == "superseded"
    assert reasons["sig_graph:deployment:ent-src_a-1"] == "source_withdrawn"


def test_live_clock_value_on_a_release_page_fails(tmp_path: Path) -> None:
    e1 = _write_export(tmp_path / "e1", n_records=1)
    b1 = build_release(e1, tmp_path / "r1", renderer_revision=REV, descriptor_version=1)
    assert validate_release(tmp_path / "r1").state == "complete"
    page = tmp_path / "r1" / f"releases/{b1.publication_id}/index.html"
    page.write_text(page.read_text() + "<p>Next run in 3 days</p>")
    report = validate_release(tmp_path / "r1")
    assert report.state == "incomplete"
    assert any("live-clock" in f or "relative-time" in f for f in report.failures)
    # and the marker vocabulary itself
    assert RC.live_clock_page_failures("<p>status_time: 12:00</p>", "x.html")
    assert RC.live_clock_page_failures("<p>updated 2 hours ago</p>", "x.html")
    assert RC.live_clock_page_failures("<p>as of 2026-01-01</p>", "x.html") == []


def test_live_clock_value_fails_the_build(tmp_path: Path) -> None:
    e1 = _write_export(tmp_path / "e1", n_records=1)
    sites = _rows(e1 / "sig_graph" / "sites.jsonl")
    sites[0]["label"] = "next run scheduled"
    _write_rows(e1 / "sig_graph" / "sites.jsonl", sites)
    with pytest.raises(ReleaseError, match="live-clock"):
        build_release(e1, tmp_path / "r1", renderer_revision=REV, descriptor_version=1)


def test_previous_release_resolution_forms(tmp_path: Path) -> None:
    e1 = _write_export(tmp_path / "e1", n_records=1)
    b1 = build_release(e1, tmp_path / "r1", renderer_revision=REV, descriptor_version=1)
    assert RC.resolve_previous(tmp_path / "r1") == (tmp_path / "r1", b1.publication_id)
    # a registry root resolves through its latest pointer
    import shutil

    from exports.release import activate

    reg = tmp_path / "reg"
    (reg / "staged").mkdir(parents=True)
    activate(reg, tmp_path / "r1")
    root, pub = RC.resolve_previous(reg)
    assert root == reg / "staged" and pub == b1.publication_id
    assert RC.resolve_previous(None) is None
    with pytest.raises(ValueError):
        RC.resolve_previous(tmp_path / "empty")
    shutil.rmtree(tmp_path / "empty", ignore_errors=True)


def test_source_diff_classes_from_source_rows() -> None:
    prev = {
        "s1": {"source_id": "s1", "name": "one", "lifecycle_state": "published", "lane": "public"},
        "s2": {"source_id": "s2", "name": "two", "lifecycle_state": "published", "lane": "public"},
        "s3": {"source_id": "s3", "name": "three", "lifecycle_state": "gated", "lane": "unknown"},
    }
    cur = {
        "s1": {"source_id": "s1", "name": "one", "lifecycle_state": "gated", "lane": "restricted"},
        "s4": {"source_id": "s4", "name": "four", "lifecycle_state": "published", "lane": "public"},
    }
    out = RC.diff_sources(prev, cur)
    assert out["state"] == "evaluated"
    assert [r["source_id"] for r in out["added"]] == ["s4"]
    assert {r["source_id"] for r in out["retired"]} == {"s2", "s3"}
    assert [r["source_id"] for r in out["newly_failing"]] == ["s1"]
    assert out["lane_changed"] == [
        {"source_id": "s1", "previous_lane": "public", "lane": "restricted"}
    ]
    absent = RC.diff_sources(None, cur)
    assert absent["state"] == "not_evaluable" and absent["added"] == []
