# SPDX-License-Identifier: Apache-2.0
"""P35.58 (REL-04b / SIG-REL-007) — verification suite B: V6–V10, V14, V15, P1.

Suite A (P35.56, ``test_release_verify.py``) landed V1–V5 + V11–V13. This
file covers the suite-B checks over the SAME real-built-release fixture
(a defect planted per check, the honest tree staying green) plus the
post-promote auto-rollback path through ``release_conf.verb_promote``:

* V6 number truth — a planted ``data-figure-value``/pointer/artifact
  defect fails; a figure whose artifact is not manifest-listed fails.
* V7 API parity — ``api_parity_check`` is the verdict owner (hosted, never
  re-implemented); the served legs compare the API's answers byte-equal
  as canonical JSON; an absent API fetcher is a recorded skip that blocks.
* V8 attribution — empty attribution under an attribution-required
  licence, a licence-less compartment, an attribution-less map page, a
  bare-identifier or handle-shaped source render all fail.
* V9 jurisdiction-coordinate sanity — null-island / out-of-range points,
  the ``covers`` oracle's axis-swap leg, out-of-boundary survivors
  rendered without a disclosed conflict, dossier-rollup recompute lies.
* V10 withdrawal barrier — the current disposition set re-derives to the
  served ``withdrawn.conf``; every alias answers 410 with that route's
  own ``sig.tombstone/1`` body under the recorded ``X-SIG-Conf-Gen``.
* V14 diff sanity — the §7.3 drift bounds (−5 %/+50 % per compartment,
  a dropped source) are failures; the deltas emit as evidence.
* V15 quality gate — ``exports.quality.run_release_gate`` is the hosted
  hook: enforce failures / not-evaluable enforce checks / ratchet
  regressions fail, the last surfacing the Class-S signal.
* P1 — latest.json ↔ release.json parity, the 35-day freshness bound,
  served==recorded conf generation, and the cadence declarations.
* auto-rollback — a failed post-promote check journals ``failed``,
  invokes ``verb_rollback``/``verb_clear_latest`` under the standing
  D-G3-8/B-9 authority (a NEW immutable generation — history is never
  rewritten), fires the recorded alert, and appends the incident note.

Everything here is a fixture/tree answer — ``origin_kind == "tree"`` rows
are fixture evidence, never a hosted/public leg (``live_verification=
false``; the real legs are later release rows').
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ops" / "src"))
sys.path.insert(0, str(REPO / "tests" / "ops"))

from test_release_verify import (  # noqa: E402
    T0,
    _ApiFixture,
    _build_candidate,
    _ctx,
    _quality_report,
)

from ops import release_conf as rc  # noqa: E402
from ops import release_pipeline as rp  # noqa: E402
from ops import release_reversal as rr  # noqa: E402
from ops import release_verify as rv  # noqa: E402
from ops import scheduled as S  # noqa: E402

_NOW = T0


def _seed_entity_deny(
    tmp_path: Path,
    work_dir: Path,
    store: rp.LocalDirStore,
    *,
    gen_n: int = 1,
    write_served_conf: bool = True,
) -> bytes:
    """Seed a real entity-level withdrawal and (optionally) write the
    re-derived barrier into the served generation — the exact bytes
    ``apply_withdrawals`` emits, including the ``staged/conf/tombstone/``
    bodies the deny lines name."""
    relroot = work_dir.parent / "relroot"
    (relroot / "registry" / "withdrawals.json").write_text(
        json.dumps(
            {
                "schema": "sig.withdrawal-registry/1",
                "entries": [
                    {
                        "target_kind": "entity",
                        "target_id": "ent-1",
                        "disposition": "withdraw",
                        "reason_category": "safety_withdrawal",
                        "authority": "ord-1",
                        "decided_at": T0.isoformat(),
                        "seq": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    # the barrier derives against the generation's own serving pub (the
    # same ``active_pub`` check_v10 will use)
    served_pub = str(
        json.loads(store.read(f"registry/conf/{gen_n}/latest.json")).get("publication_id") or ""
    )
    work = tmp_path / "v10-view"
    work.mkdir()
    conf = rr.derive_withdrawal_barrier(store, work, active_pub=served_pub)
    if write_served_conf:
        (relroot / "registry" / "conf" / str(gen_n) / "withdrawn.conf").write_bytes(conf)
    for p in (work / "registry-view" / "staged" / "conf" / "tombstone").rglob("*"):
        if p.is_file():
            dst = relroot / "staged" / "conf" / "tombstone" / p.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(p.read_bytes())
    return conf


def _record_json(work_dir: Path, pub: str, eid: str = "ent-1") -> Path:
    return work_dir / "r" / pub / "c" / "sig_graph" / "entity" / "camera" / f"{eid}.json"


# --------------------------------------------------------------------------- #
# V6 — number truth (the J3 §5.4 figure contract)                              #
# --------------------------------------------------------------------------- #


def test_v6_fails_on_a_recomputed_value_mismatch(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    page = work_dir / "v" / pub / "index.html"
    page.write_text(page.read_text().replace('data-figure-value="2"', 'data-figure-value="7"'))
    row = rv.check_v6(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("!= recomputed" in f for f in row["evidence"]["failures"])


def test_v6_fails_on_an_unmanifested_artifact(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    page = work_dir / "v" / pub / "index.html"
    page.write_text(page.read_text().replace("web/coverage.json", "web/made_up.json"))
    row = rv.check_v6(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("not manifest-listed" in f for f in row["evidence"]["failures"])


def test_v6_fails_on_a_missing_artifact(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    (work_dir / "v" / pub / "artifact" / "web" / "coverage.json").unlink()
    row = rv.check_v6(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("not in v/" in f for f in row["evidence"]["failures"])


def test_v6_fails_on_a_pointer_miss(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    page = work_dir / "s" / pub / "index.html"
    page.write_text(
        page.read_text().replace('data-pointer="/totals/sites"', 'data-pointer="/totals/nope"')
    )
    row = rv.check_v6(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("misses" in f for f in row["evidence"]["failures"])


def test_v6_fails_on_a_stale_artifact_as_of(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    art = work_dir / "v" / pub / "artifact" / "web" / "coverage.json"
    doc = json.loads(art.read_text())
    doc["as_of_world"] = "2026-09-01T00:00:00Z"  # older than the release's as_of
    art.write_text(json.dumps(doc))
    row = rv.check_v6(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("as-of" in f for f in row["evidence"]["failures"])


# --------------------------------------------------------------------------- #
# V7 — API parity (release_publish_verify.api_parity_check owns the verdict)   #
# --------------------------------------------------------------------------- #


def test_v7_passes_over_the_fixture_api(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    row = rv.check_v7(_ctx(work_dir, pub, store))
    assert row["status"] == "pass", json.dumps(row["evidence"], indent=1)[:2000]


def test_v7_skips_without_an_api_fetcher(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    row = rv.check_v7(_ctx(work_dir, pub, store, api_fetcher=None))
    assert row["status"] == "skip"
    suite = rv.run_suite(_ctx(work_dir, pub, store, api_fetcher=None))
    assert suite["verdict"] == "blocked" and "V7" in suite["uncovered"]


def test_v7_fails_when_the_api_names_another_release(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    api = _ApiFixture(work_dir, pub, named_pub="p-" + "9" * 64)
    row = rv.check_v7(_ctx(work_dir, pub, store, api_fetcher=api))
    assert row["status"] == "fail"
    assert any("names release" in f for f in row["evidence"]["failures"])


def test_v7_fails_on_a_live_spine_route_missing_its_basis(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    api = _ApiFixture(work_dir, pub, terms_basis="release")
    row = rv.check_v7(_ctx(work_dir, pub, store, api_fetcher=api))
    assert row["status"] == "fail"
    assert any("live-spine" in f for f in row["evidence"]["failures"])


def test_v7_fails_on_a_served_slice_mismatch(tmp_path: Path) -> None:
    """A declared slice document the API answers with DIFFERENT bytes — the
    canonical-JSON compare catches it."""
    work_dir, pub, store = _build_candidate(tmp_path)
    api_dir = work_dir / "r" / pub / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "coverage.json").write_text(json.dumps({"totals": {"sites": 2}}))
    (api_dir / "index.json").write_text(
        json.dumps(
            {
                "schema": "sig.api-slice/1",
                "publication_id": pub,
                "documents": [
                    {
                        "route": "/v1/release/coverage",
                        "path": f"r/{pub}/api/coverage.json",
                    }
                ],
            }
        )
    )
    api = _ApiFixture(work_dir, pub, tampered=frozenset({"/v1/release/coverage"}))
    row = rv.check_v7(_ctx(work_dir, pub, store, api_fetcher=api))
    assert row["status"] == "fail"
    assert any("canonical" in f for f in row["evidence"]["failures"])


def test_v7_fails_when_the_api_slice_route_404s(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    api_dir = work_dir / "r" / pub / "api"
    api_dir.mkdir(parents=True)
    (api_dir / "coverage.json").write_text(json.dumps({"totals": {"sites": 2}}))
    (api_dir / "index.json").write_text(
        json.dumps(
            {
                "schema": "sig.api-slice/1",
                "publication_id": pub,
                "documents": [
                    {"route": "/v1/release/coverage", "path": f"r/{pub}/api/coverage.json"}
                ],
            }
        )
    )
    api = _ApiFixture(work_dir, pub, missing=frozenset({"/v1/release/coverage"}))
    row = rv.check_v7(_ctx(work_dir, pub, store, api_fetcher=api))
    assert row["status"] == "fail"
    assert any("HTTP 404" in f for f in row["evidence"]["failures"])


# --------------------------------------------------------------------------- #
# V8 — attribution sanity                                                     #
# --------------------------------------------------------------------------- #


def test_v8_fails_on_an_empty_required_attribution(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    idx = work_dir / "r" / pub / "c" / "sig_graph" / "records.index.jsonl"
    idx.write_text(
        idx.read_text()
        + json.dumps(
            {
                "record_key": "sig_graph:camera:ent-1",
                "_rights": {
                    "source_id": "src_a",
                    "attribution_required": True,
                    "attribution": "   ",
                },
            }
        )
        + "\n"
    )
    row = rv.check_v8(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("attribution" in f for f in row["evidence"]["failures"])


def test_v8_fails_on_a_record_source_without_attribution(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    rec = _record_json(work_dir, pub)
    doc = json.loads(rec.read_bytes())
    doc["source_refs"] = [{"source_id": "src_a", "attribution": ""}]
    rec.write_text(json.dumps(doc))
    row = rv.check_v8(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("carries no attribution" in f for f in row["evidence"]["failures"])


def test_v8_fails_on_a_licence_less_compartment(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    ctx = _ctx(work_dir, pub, store)
    ctx.fetcher.overrides["/LICENCES.json"] = json.dumps(
        {"schema": "sig.licences-index/1", "compartments": [{"compartment": "sig_graph"}]}
    ).encode()
    row = rv.check_v8(ctx)
    assert row["status"] == "fail"
    assert any("no licence" in f for f in row["evidence"]["failures"])


def test_v8_fails_when_a_map_page_carries_no_attribution(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    for ns in ("v", "s"):
        page = work_dir / ns / pub / "map" / "index.html"
        page.write_text(
            page.read_text().replace(
                '<p class="map-attribution">Map data © Ohio DOT and contributors</p>', ""
            )
        )
    row = rv.check_v8(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("no attribution element" in f for f in row["evidence"]["failures"])
    assert any("omits 'Ohio DOT'" in f for f in row["evidence"]["failures"])


def test_v8_fails_on_a_source_rendered_as_a_bare_id(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    src = work_dir / "v" / pub / "artifact" / "web" / "sources.json"
    doc = json.loads(src.read_text())
    doc["sources"][0]["name"] = "src_a"  # the source's own id — never a render
    src.write_text(json.dumps(doc))
    row = rv.check_v8(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("bare id" in f for f in row["evidence"]["failures"])


def test_v8_fails_on_a_handle_shaped_source_render(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    for ns in ("v", "s"):
        src = work_dir / ns / pub / "artifact" / "web" / "sources.json"
        doc = json.loads(src.read_text())
        doc["sources"][0]["name"] = "@OhioDOT"  # a personal/social handle
        src.write_text(json.dumps(doc))
    row = rv.check_v8(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("handle-shaped" in f for f in row["evidence"]["failures"])


# --------------------------------------------------------------------------- #
# V9 — jurisdiction-coordinate sanity                                         #
# --------------------------------------------------------------------------- #


def _plant_point(work_dir: Path, pub: str, lat: float, lon: float, eid: str = "ent-1") -> Path:
    rec = _record_json(work_dir, pub, eid)
    doc = json.loads(rec.read_bytes())
    doc["location"] = {"kind": "point", "lat": lat, "lon": lon}
    rec.write_text(json.dumps(doc))
    return rec


def test_v9_fails_on_a_null_island_point(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    _plant_point(work_dir, pub, 0.0, 0.0)
    row = rv.check_v9(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("null-island" in f for f in row["evidence"]["failures"])


def test_v9_fails_on_an_out_of_range_point(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    _plant_point(work_dir, pub, 95.0, -97.5)
    row = rv.check_v9(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("out-of-range" in f for f in row["evidence"]["failures"])


def test_v9_catches_an_axis_swap(tmp_path: Path) -> None:
    """The mark43 regression class: the shipped pair is outside the claimed
    jurisdiction but the SWAPPED pair is inside it — only the injected
    boundary oracle sees that."""
    work_dir, pub, store = _build_candidate(tmp_path)
    _plant_point(work_dir, pub, 40.0, -97.5)
    # the oracle answers "inside" only for the swapped coordinate order
    covers = lambda _claim, lat, lon: (lat, lon) == (-97.5, 40.0)  # noqa: E731
    row = rv.check_v9(_ctx(work_dir, pub, store, covers=covers))
    assert row["status"] == "fail"
    assert any("axis swap" in f for f in row["evidence"]["failures"])


def test_v9_skips_when_points_exist_without_an_oracle(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    _plant_point(work_dir, pub, 35.5, -97.5)
    row = rv.check_v9(_ctx(work_dir, pub, store, covers=None))
    assert row["status"] == "skip"
    assert any("no covers oracle" in s for s in row["evidence"]["skipped_legs"])


def test_v9_fails_on_an_undisclosed_out_of_boundary_point(tmp_path: Path) -> None:
    """A point outside its claimed jurisdiction that still renders on the
    site without a disclosed-conflict marking fails — the withheld or
    disclosed renderings are the only permitted answers."""
    work_dir, pub, store = _build_candidate(tmp_path)
    _plant_point(work_dir, pub, 40.0, -97.5)
    covers = lambda _claim, _lat, _lon: False  # noqa: E731 — nothing is inside
    row = rv.check_v9(_ctx(work_dir, pub, store, covers=covers))
    assert row["status"] == "fail"
    assert any("disclosed-conflict" in f for f in row["evidence"]["failures"])


def test_v9_fails_when_a_dossier_rollup_lies(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    d = work_dir / "v" / pub / "artifact" / "web" / "dossiers" / "unplaced.json"
    doc = json.loads(d.read_text())
    doc["rollup"]["records"] = 5  # recomputes to 2
    d.write_text(json.dumps(doc))
    row = rv.check_v9(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("rollup.records" in f for f in row["evidence"]["failures"])


# --------------------------------------------------------------------------- #
# V10 — the withdrawal barrier                                                #
# --------------------------------------------------------------------------- #


def test_v10_green_over_a_seeded_deny(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    conf = _seed_entity_deny(tmp_path, work_dir, store)
    assert b"location =" in conf
    row = rv.check_v10(_ctx(work_dir, pub, store))
    assert row["status"] == "pass", json.dumps(row["evidence"], indent=1)[:3000]
    assert row["evidence"]["expected_aliases"] == row["evidence"]["served_aliases"] > 0
    assert row["evidence"]["probed"], "the deny aliases must actually be probed"


def test_v10_fails_when_the_served_generation_lacks_the_deny(tmp_path: Path) -> None:
    """The registry carries a disposition but conf gen 1's withdrawn.conf
    was never re-derived — every missing alias is a failure."""
    work_dir, pub, store = _build_candidate(tmp_path)
    _seed_entity_deny(tmp_path, work_dir, store, write_served_conf=False)
    row = rv.check_v10(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("not denied by the served generation" in f for f in row["evidence"]["failures"])


def test_v10_fails_when_the_tombstone_body_is_wrong(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    conf = _seed_entity_deny(tmp_path, work_dir, store)
    # clobber one tombstone body — the 410 still answers, with the wrong body
    tomb = next((work_dir.parent / "relroot" / "staged" / "conf" / "tombstone").rglob("*"))
    tomb.write_bytes(b"<html>generic 410</html>")
    assert b"location =" in conf
    row = rv.check_v10(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("own sig.tombstone/1 body" in f for f in row["evidence"]["failures"])


def test_v10_fails_when_the_conf_gen_header_lies(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    _seed_entity_deny(tmp_path, work_dir, store)
    ctx = _ctx(work_dir, pub, store)
    ctx.fetcher.conf_gen_header = "9"  # the origin claims a generation the registry never wrote
    row = rv.check_v10(ctx)
    assert row["status"] == "fail"
    assert any("X-SIG-Conf-Gen" in f for f in row["evidence"]["failures"])


def test_v10_p_mode_probes_new_since_last_release(tmp_path: Path) -> None:
    """P mode: every alias new since the prior generation plus a bounded
    sample of the rest — the new-deny lands in gen 2's conf."""
    work_dir, pub, store = _build_candidate(tmp_path, promoted=True)
    conf = _seed_entity_deny(tmp_path, work_dir, store, gen_n=2)
    ctx = _ctx(work_dir, pub, store, mode="P")
    row = rv.check_v10(ctx)
    assert row["status"] == "pass", json.dumps(row["evidence"], indent=1)[:3000]
    sample = row["evidence"].get("p_sample") or {}
    assert sample.get("new", 0) > 0 and sample.get("new") == len(row["evidence"]["probed"])
    assert b"location =" in conf


# --------------------------------------------------------------------------- #
# V14 — diff sanity (the §7.3 drift bounds)                                   #
# --------------------------------------------------------------------------- #


def test_v14_green_against_the_staged_prior_release(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    row = rv.check_v14(_ctx(work_dir, pub, store))
    assert row["status"] == "pass", json.dumps(row["evidence"], indent=1)[:3000]
    deltas = row["evidence"]["deltas"]
    assert deltas["baseline"]["publication_id"] != pub
    assert deltas["records"]["total"]["current"] == deltas["records"]["total"]["previous"] == 2


def test_v14_fails_on_a_compartment_record_breach(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    cat = work_dir / "releases" / pub / "catalog_entry.json"
    doc = json.loads(cat.read_bytes())
    doc["compartments"][0]["record_count"] = 10  # 2 → 10: +400 %, past §7.3's +50 %
    cat.write_text(json.dumps(doc))
    row = rv.check_v14(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("sig_graph" in f for f in row["evidence"]["failures"])
    assert any("total records" in f for f in row["evidence"]["failures"])


def test_v14_fails_on_a_dropped_source(tmp_path: Path) -> None:
    """A source that carried records last release and carries none now is
    the §7.3 flag — seed source_refs onto the PRIOR release's records."""
    work_dir, pub, store = _build_candidate(tmp_path)
    staged = work_dir.parent / "relroot" / "staged"
    old_pub = str(json.loads(store.read("registry/latest.json"))["publication_id"])
    rec_dir = staged / "r" / old_pub / "c" / "sig_graph" / "entity" / "camera"
    for rec_path in rec_dir.glob("*.json"):
        doc = json.loads(rec_path.read_bytes())
        doc["source_refs"] = (doc.get("source_refs") or []) + [{"source_id": "src_dropped"}]
        rec_path.write_text(json.dumps(doc))
    row = rv.check_v14(_ctx(work_dir, pub, store))
    assert row["status"] == "fail"
    assert any("dropped" in f or "loses" in f for f in row["evidence"]["failures"])


def test_v14_records_a_first_release_skip(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    ctx = _ctx(work_dir, pub, store)
    ctx.store = None
    ctx.previous_pub = None
    ctx.previous_dir = None
    row = rv.check_v14(ctx)
    assert row["status"] == "skip"
    assert "baseline absent" in row["detail"] or row["evidence"]["skipped_legs"]


# --------------------------------------------------------------------------- #
# V15 — the quality gate hook (exports.quality.run_release_gate owns it)      #
# --------------------------------------------------------------------------- #


def test_v15_green_on_a_clean_report(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    row = rv.check_v15(_ctx(work_dir, pub, store))
    assert row["status"] == "pass", json.dumps(row["evidence"], indent=1)


def test_v15_fails_on_an_enforce_failure(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    report = _quality_report()
    report["checks"][0]["outcome"] = "fail"
    row = rv.check_v15(_ctx(work_dir, pub, store, quality_report=report))
    assert row["status"] == "fail"
    assert row["evidence"]["gate"]["enforce_failures"] == ["q.coverage"]


def test_v15_fails_on_a_not_evaluable_enforce_check(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    report = _quality_report()
    report["checks"][0]["outcome"] = "not_evaluable"
    row = rv.check_v15(_ctx(work_dir, pub, store, quality_report=report))
    assert row["status"] == "fail"
    assert row["evidence"]["gate"]["not_evaluable_enforce"] == ["q.coverage"]


def test_v15_ratchet_regression_fails_and_surfaces_class_s(tmp_path: Path) -> None:
    """The ratchet→Class-S surface: a regression fails the gate AND the
    report's own class_s_trigger rides the evidence verbatim."""
    work_dir, pub, store = _build_candidate(tmp_path)
    report = _quality_report()
    report["checks"][0]["regression"] = True
    report["summary"]["class_s_trigger"] = True
    row = rv.check_v15(_ctx(work_dir, pub, store, quality_report=report))
    assert row["status"] == "fail"
    assert row["evidence"]["gate"]["ratchet_regressions"] == ["q.coverage"]
    assert row["evidence"]["class_s_signal"] is True
    assert "Class S" in row["detail"]


def test_v15_skips_on_an_absent_report_and_the_skip_blocks(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    row = rv.check_v15(_ctx(work_dir, pub, store, quality_report=None))
    assert row["status"] == "skip"
    suite = rv.run_suite(_ctx(work_dir, pub, store, quality_report=None))
    assert suite["verdict"] == "blocked" and "V15" in suite["uncovered"]


def test_v15_report_from_a_path(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path)
    rp_path = tmp_path / "q.json"
    rp_path.write_text(json.dumps(_quality_report()))
    row = rv.check_v15(_ctx(work_dir, pub, store, quality_report=rp_path))
    assert row["status"] == "pass"


# --------------------------------------------------------------------------- #
# P1 — the hosted probes (P-mode row)                                         #
# --------------------------------------------------------------------------- #


def test_p1_green_over_the_promoted_tree(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path, promoted=True)
    row = rv.check_p1(_ctx(work_dir, pub, store, mode="P"))
    assert row["status"] == "pass", json.dumps(row["evidence"], indent=1)[:3000]


def test_p1_fails_on_a_pointer_mismatch(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path, promoted=True)
    ctx = _ctx(work_dir, pub, store, mode="P")
    ctx.fetcher.overrides["/release.json"] = json.dumps(
        {"schema": "sig.site-release/1", "publication_id": "p-" + "9" * 64}
    ).encode()
    row = rv.check_p1(ctx)
    assert row["status"] == "fail"
    assert any("/release.json names" in f for f in row["evidence"]["failures"])


def test_p1_fails_on_a_stale_release(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path, promoted=True)
    # stale BEFORE ctx construction — the served override reads
    # conf/2/releases/latest.json (the activation-overlay object)
    gen = work_dir.parent / "relroot" / "registry" / "conf" / "2" / "releases" / "latest.json"
    doc = json.loads(gen.read_text())
    doc["activated_at"] = "2026-01-01T00:00:00Z"  # > 35 days before T0
    gen.write_text(json.dumps(doc))
    row = rv.check_p1(_ctx(work_dir, pub, store, mode="P"))
    assert row["status"] == "fail"
    assert any("exceeds" in f for f in row["evidence"]["failures"])


def test_p1_fails_on_a_conf_gen_mismatch(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path, promoted=True)
    ctx = _ctx(work_dir, pub, store, mode="P")
    ctx.fetcher.conf_gen_header = "9"
    row = rv.check_p1(ctx)
    assert row["status"] == "fail"
    assert any("conf-gen 9" in f for f in row["evidence"]["failures"])


def test_p1_fails_when_cadence_lacks_the_release_targets(tmp_path: Path) -> None:
    work_dir, pub, store = _build_candidate(tmp_path, promoted=True)
    bare = tmp_path / "cadence.toml"
    bare.write_text('[probes]\ntargets = []\n[runs]\nsink = "gs://x"\n')
    row = rv.check_p1(_ctx(work_dir, pub, store, mode="P", cadence_path=bare))
    assert row["status"] == "fail"
    assert any("probe target" in f for f in row["evidence"]["failures"])


# --------------------------------------------------------------------------- #
# The scheduled probe kinds — P1's cadence surface (scheduled.py)             #
# --------------------------------------------------------------------------- #


def test_cadence_toml_declares_the_p1_targets() -> None:
    cfg = S.load_cadence(REPO / "ops" / "cadence.toml")
    kinds = {t.kind for t in cfg.probe_targets}
    for want in S.RELEASE_PROBE_KINDS:
        assert want in kinds, f"cadence.toml declares no {want} probe"
    age = next(t for t in cfg.probe_targets if t.kind == "sig-release-age")
    assert age.max_age_days == S.RELEASE_AGE_MAX_DAYS == 35
    assert any(t.name.startswith("absent-api-release") for t in cfg.probe_targets)


def test_probe_hosted_dispatches_the_release_kinds() -> None:
    """probe_hosted routes the sig-release-* kinds to check_release (the
    injected fixture seam) and carries the declared trigger severity."""
    calls: list[tuple[str, str]] = []

    def fake_release(kind: str, url: str) -> tuple[bool, str]:
        calls.append((kind, url))
        return False, f"{kind} red"

    specs = {t.name: t for t in S.load_cadence(REPO / "ops" / "cadence.toml").probe_targets}
    targets = [
        (n, k, "https://web.example")
        for n, k in (
            ("sig-release-pointer", "sig-release-pointer"),
            ("sig-release-age", "sig-release-age"),
            ("sig-conf-gen", "sig-conf-gen"),
        )
    ]
    rows = S.probe_hosted(targets, check_release_fn=fake_release, specs=specs)
    assert [r.service for r in rows] == [t[0] for t in targets]
    assert all(not r.ok for r in rows)
    assert {k for k, _u in calls} == set(S.RELEASE_PROBE_KINDS)
    # the declared trigger severity rides the spec
    assert specs["sig-release-age"].trigger == "alarm"
    assert specs["sig-conf-gen"].trigger == "critical"


def test_check_release_pointer_parity() -> None:
    """check_release's three kinds over a canned HTTP layer."""
    answers: dict[str, tuple[int, dict[str, str], bytes]] = {
        "https://web/releases/latest.json": (
            200,
            {},
            json.dumps({"publication_id": "p-" + "a" * 64, "conf_gen": 3}).encode(),
        ),
        "https://web/release.json": (
            200,
            {},
            json.dumps({"publication_id": "p-" + "a" * 64}).encode(),
        ),
        "https://web/": (200, {"X-SIG-Conf-Gen": "3"}, b"<html>ok</html>"),
    }

    def fake_get(url: str, *, timeout: float = 15.0) -> tuple[int, dict[str, str], bytes]:
        return answers.get(url, (404, {}, b""))

    orig = S._http_get
    S._http_get = fake_get
    try:
        ok, detail = S.check_release("sig-release-pointer", "https://web")
        assert ok, detail
        ok, detail = S.check_release("sig-conf-gen", "https://web")
        assert ok, detail
        # pointer mismatch fails
        answers["https://web/release.json"] = (
            200,
            {},
            json.dumps({"publication_id": "p-" + "b" * 64}).encode(),
        )
        ok, detail = S.check_release("sig-release-pointer", "https://web")
        assert not ok and "names" in detail
        # a served conf-gen ahead of the record fails (RR-7's alarm class)
        answers["https://web/"] = (200, {"X-SIG-Conf-Gen": "4"}, b"")
        ok, detail = S.check_release("sig-conf-gen", "https://web")
        assert not ok and "conf-gen" in detail
    finally:
        S._http_get = orig


def test_check_release_age_bound() -> None:
    fresh = datetime.now(UTC).isoformat()
    stale = "2020-01-01T00:00:00+00:00"
    body = {"value": None}

    def fake_get(url: str, *, timeout: float = 15.0) -> tuple[int, dict[str, str], bytes]:
        return 200, {}, json.dumps({"activated_at": body["value"]}).encode()

    orig = S._http_get
    S._http_get = fake_get
    try:
        body["value"] = fresh
        ok, detail = S.check_release("sig-release-age", "https://web/releases/latest.json")
        assert ok, detail
        body["value"] = stale
        ok, detail = S.check_release("sig-release-age", "https://web/releases/latest.json")
        assert not ok and "age" in detail
        body["value"] = None
        ok, detail = S.check_release("sig-release-age", "https://web/releases/latest.json")
        assert not ok
    finally:
        S._http_get = orig


# --------------------------------------------------------------------------- #
# The auto-rollback (REL-04b): failed post-check → rollback → alert → note    #
# --------------------------------------------------------------------------- #

_PUB_A = "p-" + "a" * 64
_PUB_B = "p-" + "b" * 64
_EID = "ent-1"


def _arb_store(tmp_path: Path) -> rp.LocalDirStore:
    return rp.LocalDirStore(tmp_path)


def _arb_put(store: rp.Store, name: str, doc: dict[str, Any]) -> None:
    store.insert(name, json.dumps(doc, sort_keys=True).encode(), content_type="application/json")


def _arb_seed_pub(store: rp.Store, pub: str, label: str) -> None:
    """A staged release namespace set + descriptor/catalog-entry — the same
    shape test_release_reversal's _seed_pub poses."""
    _arb_put(
        store,
        f"staged/releases/{pub}/catalog_entry.json",
        {
            "schema": "sig.catalog-entry/1",
            "publication_id": pub,
            "data_release_id": label,
            "label": label,
            "compartments": [{"compartment": "sig_graph", "record_count": 2}],
            "compat": {"as_of_world": "2026-10-20"},
        },
    )
    _arb_put(
        store,
        f"staged/releases/{pub}/descriptor.json",
        {"schema": "sig.release-descriptor/2", "label": label, "code": {"commit": "0" * 40}},
    )
    _arb_put(
        store,
        f"staged/releases/{pub}/release.json",
        {"schema": "sig.site-release/1", "data_release_id": label},
    )
    for ns in ("r", "v", "s"):
        store.insert(f"staged/{ns}/{pub}/index.html", f"<html>{ns}:{pub[:10]}</html>".encode())
    # one entity route so the barrier has something to scope
    store.insert(
        f"staged/r/{pub}/c/sig_graph/entity/camera/{_EID}/index.html",
        f"<html>{_EID}</html>".encode(),
    )
    store.insert(
        f"staged/r/{pub}/c/sig_graph/entity/camera/{_EID}.json",
        json.dumps({"entity_id": _EID, "entity_type": "camera"}).encode(),
    )


def _arb_seed_registry(store: rp.Store, pub: str, label: str) -> None:
    """One prior generation: pub promoted + latest, withdrawals/labels
    registries present (the rollback machinery's inputs)."""
    _arb_put(
        store,
        "registry/catalog.json",
        {
            "schema": "sig.publication-catalog/1",
            "publications": [
                {
                    "publication_id": pub,
                    "data_release_id": label,
                    "label": label,
                    "compartments": [{"compartment": "sig_graph"}],
                    "manifest_sha256": "0" * 64,
                    "descriptor_sha256": "1" * 64,
                    "compat": {"as_of_world": "2026-10-20"},
                }
            ],
        },
    )
    _arb_put(
        store,
        "registry/withdrawals.json",
        {"schema": "sig.withdrawal-registry/1", "entries": []},
    )
    _arb_put(
        store,
        "registry/labels.json",
        {
            "schema": "sig.label-map/1",
            "labels": [{"publication_id": pub, "label": label}],
        },
    )
    latest = {
        "schema": rc.LATEST_SCHEMA_V2,
        "publication_id": pub,
        "label": label,
        "activated_at": _NOW.isoformat(),
        "conf_gen": 1,
        "previous": None,
        "rolled_back": False,
        "withdrawals_sha256": rr.withdrawals_sha256(store),
    }
    for name, body in {
        "promoted.map": rc.render_promoted_map({pub}, gen=1),
        "latest.json": json.dumps(latest, sort_keys=True).encode(),
        "withdrawn.conf": rr._deny_map_bytes(Path("/nonexistent")),
        "selectors.conf": rc._empty_selectors(1),
        "labels.conf": rc.render_labels_conf({}, gen=1),
        "releases/index.html": b"<html>releases</html>",
        "releases/catalog.json": b"{}",
        "releases/latest.json": json.dumps(latest, sort_keys=True).encode(),
    }.items():
        store.insert(f"registry/conf/1/{name}", body)


def _arb_seed_promotable(store: rp.Store, pub: str) -> None:
    """The journal records promote needs: verified + classified."""
    rp.emit_event(store, "verified", pub, {"outcome": "recorded"}, now=_NOW)
    rp.emit_event(
        store,
        "classified",
        pub,
        {"outcome": "recorded", "class": "class_r"},
        now=_NOW,
    )
    _arb_put(
        store,
        "registry/approvals/go.json",
        {
            "schema": "sig.promotion-approval/1",
            "kind": "standing_go",
            "class": "class_r",
            "ref": "GATE-G4 §4",
            "approved_at": "2026-10-09T17:32:00Z",
        },
    )
    _arb_put(
        store,
        "registry/authorities/d-g3-8",
        {
            "schema": rr.AUTHORITY_SCHEMA,
            "kind": "go",
            "ref": "D-G3-8/B-9",
            "issued_at": "2026-10-23T00:00:00Z",
        },
    )


def _arb_promote(root: Path, pub: str, **kw: Any) -> dict[str, Any]:
    kw.setdefault("approval", "go.json")
    kw.setdefault("api_image", "gcr.io/sig/sig-api@sha256:" + "1" * 64)
    kw.setdefault("web_image", "gcr.io/sig/sig-web@sha256:" + "2" * 64)
    kw.setdefault("project", "sig-fixture")
    kw.setdefault("region", "us-central1")
    kw.setdefault("now", _NOW)
    kw.setdefault("alert_hook", lambda alert: "captured")
    kw.setdefault("apply_", True)
    return rc.verb_promote(_arb_store(root), publication_id=pub, **kw)


def _failing_checks(_store: rp.Store, *, gen: int, pub: str) -> list[dict[str, Any]]:
    return [{"id": "p1.release-pointer", "status": "fail", "detail": "the check says no"}]


def _conf_doc(root: Path, gen: int, name: str) -> dict[str, Any]:
    return json.loads((root / "registry" / "conf" / str(gen) / name).read_bytes())


def test_failed_post_check_rolls_back_to_the_prior_latest(tmp_path: Path) -> None:
    """The REL-04b acceptance path end-to-end over the fixture registry:
    failed post-check → failed event → verb_rollback under the standing
    authority → conf/<gen+1> names the prior latest → alert + incident."""
    store = _arb_store(tmp_path)
    _arb_seed_pub(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_pub(store, _PUB_B, "sig-2026-10-02.1")
    _arb_seed_registry(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_promotable(store, _PUB_B)
    gen2_before = (tmp_path / "registry" / "conf" / "1").stat().st_mtime_ns
    fired: list[Any] = []

    with pytest.raises(rp.PipelineError) as exc:
        _arb_promote(
            tmp_path,
            _PUB_B,
            post_checks=_failing_checks,
            alert_hook=lambda a: fired.append(a) or "recorded",
        )
    assert exc.value.code == "post-check-failed"

    # a NEW generation, naming the prior latest — history is never edited
    assert (tmp_path / "registry" / "conf" / "3" / "latest.json").is_file()
    latest3 = _conf_doc(tmp_path, 3, "latest.json")
    assert latest3["publication_id"] == _PUB_A
    assert latest3.get("rolled_back") is True
    # conf/2 — the failed promotion's generation — still names PUB_B and is
    # byte-intact (append-only: a failed promote is a fact, never erased)
    latest2 = _conf_doc(tmp_path, 2, "latest.json")
    assert latest2["publication_id"] == _PUB_B
    assert (tmp_path / "registry" / "conf" / "1").stat().st_mtime_ns == gen2_before

    # the journal: failed → rolled-back (+ rolled-back-from on PUB_B) → incident
    verbs = [e["verb"] for e in rp.list_events(_arb_store(tmp_path))]
    assert "failed" in verbs and "rolled-back" in verbs and "incident" in verbs
    rb = next(e for e in rp.list_events(_arb_store(tmp_path)) if e["verb"] == "rolled-back")
    assert rb.get("detail", rb).get("conf_gen") == 3 or "conf_gen" in str(rb)

    # the alert fired through the injected seam — recorded verbatim
    assert fired and fired[0].kind == "release-auto-rollback"
    assert fired[0].severity == "critical"

    # the incident note is an append-only registry/incidents/ object
    incidents = sorted((tmp_path / "registry" / "incidents").glob("*.json"))
    assert incidents
    note = json.loads(incidents[-1].read_bytes())
    assert note["schema"] == "sig.release-incident/1"
    assert note["publication_id"] == _PUB_B
    assert note["restored_publication_id"] == _PUB_A
    assert note["failed_checks"][0]["id"] == "p1.release-pointer"
    assert note["authority_decision"] == "D-G3-8/B-9"
    assert note["rollback"]["outcome"] == "rolled-back"
    assert note["rollback"]["conf_gen"] == 3


def test_failed_post_check_without_a_prior_release_clears_latest(tmp_path: Path) -> None:
    """First-release promote whose post-check fails: there is no prior
    publication to roll to — the verb clear-latest path takes the latest
    pointer down and the barrier still serves (§8.2)."""
    store = _arb_store(tmp_path)
    _arb_seed_pub(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_promotable(store, _PUB_A)
    # no prior generation — registry shell only
    _arb_put(
        store,
        "registry/withdrawals.json",
        {"schema": "sig.withdrawal-registry/1", "entries": []},
    )
    _arb_put(
        store,
        "registry/catalog.json",
        {"schema": "sig.publication-catalog/1", "publications": []},
    )
    _arb_put(store, "registry/labels.json", {"schema": "sig.label-map/1", "labels": []})

    with pytest.raises(rp.PipelineError) as exc:
        _arb_promote(tmp_path, _PUB_A, post_checks=_failing_checks)
    assert exc.value.code == "post-check-failed"
    latest2 = _conf_doc(tmp_path, 2, "latest.json")
    # the cleared pointer — the archive-only sentinel, never pub A
    assert latest2["publication_id"] in (None, "", "none")
    incidents = sorted((tmp_path / "registry" / "incidents").glob("*.json"))
    assert incidents
    note = json.loads(incidents[-1].read_bytes())
    assert note["rollback"]["outcome"] in ("cleared-latest", "cleared")


def test_failed_post_check_over_a_floor_serve_restores_the_floor(tmp_path: Path) -> None:
    """The prior serving generation can be a legacy-floor serve — its
    latest.json carries ``publication_id: None`` + ``legacy_floor`` (§8.5).
    A failed promote on top must roll back ``to`` the floor label
    (``verb_rollback`` resolves ``legacy-<date>``), never clear-latest into
    an archive-only posture the operator did not choose."""
    store = _arb_store(tmp_path)
    floor = "legacy-20261001"
    # the imported floor: registry/floor.json + the staged v/ tree
    _arb_put(
        store,
        "registry/floor.json",
        {
            "schema": "sig.legacy-floor/1",
            "floors": [
                {
                    "label": floor,
                    "namespace": f"v/{floor}",
                    "imported_at": _NOW.isoformat(),
                    "source": "fixture",
                    "objects": 1,
                    "bytes": 24,
                }
            ],
        },
    )
    store.insert(f"staged/v/{floor}/index.html", b"<html>floor</html>")
    # a floor-serving generation: publication_id None, legacy_floor the label
    _arb_put(
        store,
        "registry/catalog.json",
        {"schema": "sig.publication-catalog/1", "publications": []},
    )
    _arb_put(
        store,
        "registry/withdrawals.json",
        {"schema": "sig.withdrawal-registry/1", "entries": []},
    )
    _arb_put(store, "registry/labels.json", {"schema": "sig.label-map/1", "labels": []})
    latest = {
        "schema": rc.LATEST_SCHEMA_V2,
        "publication_id": None,
        "label": floor,
        "legacy_floor": floor,
        "activated_at": _NOW.isoformat(),
        "conf_gen": 1,
        "previous": None,
        "rolled_back": True,
        "withdrawals_sha256": rr.withdrawals_sha256(store),
    }
    for name, body in {
        "promoted.map": rc.render_promoted_map(set(), gen=1),
        "latest.json": json.dumps(latest, sort_keys=True).encode(),
        "withdrawn.conf": rr._deny_map_bytes(Path("/nonexistent")),
        "selectors.conf": rc._empty_selectors(1),
        "labels.conf": rc.render_labels_conf({}, gen=1),
        "releases/index.html": b"<html>releases</html>",
        "releases/catalog.json": b"{}",
        "releases/latest.json": json.dumps(latest, sort_keys=True).encode(),
    }.items():
        store.insert(f"registry/conf/1/{name}", body)
    _arb_seed_pub(store, _PUB_B, "sig-2026-10-02.1")
    _arb_seed_promotable(store, _PUB_B)

    with pytest.raises(rp.PipelineError) as exc:
        _arb_promote(tmp_path, _PUB_B, post_checks=_failing_checks)
    assert exc.value.code == "post-check-failed"
    detail = exc.value.detail or {}
    assert detail["auto_rollback"]["outcome"] == "rolled-back"
    assert detail["auto_rollback"]["target"] == floor
    latest3 = _conf_doc(tmp_path, 3, "latest.json")
    assert latest3["publication_id"] is None
    assert latest3["legacy_floor"] == floor
    incidents = sorted((tmp_path / "registry" / "incidents").glob("*.json"))
    note = json.loads(incidents[-1].read_bytes())
    assert note["restored_publication_id"] == floor


def test_failed_post_check_with_a_refused_rollback_is_still_recorded(tmp_path: Path) -> None:
    """No authority record → the rollback refuses honestly; the refusal is
    recorded in the incident note and the promote still raises
    post-check-failed — the operator sees BOTH facts."""
    store = _arb_store(tmp_path)
    _arb_seed_pub(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_pub(store, _PUB_B, "sig-2026-10-02.1")
    _arb_seed_registry(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_promotable(store, _PUB_B)
    # remove the standing authority — the rollback must refuse
    (tmp_path / "registry" / "authorities" / "d-g3-8").unlink()

    with pytest.raises(rp.PipelineError) as exc:
        _arb_promote(tmp_path, _PUB_B, post_checks=_failing_checks)
    assert exc.value.code == "post-check-failed"
    detail = exc.value.detail or {}
    assert detail["auto_rollback"]["outcome"] == "refused"
    assert "authority-absent" in detail["auto_rollback"]["error"]
    incidents = sorted((tmp_path / "registry" / "incidents").glob("*.json"))
    assert incidents
    note = json.loads(incidents[-1].read_bytes())
    assert note["rollback"]["outcome"] == "refused"


def test_resumed_promote_failure_rolls_back_to_the_prior_release(tmp_path: Path) -> None:
    """A crashed promote (generation written, checks never ran, no events)
    resumes — and when the resumed checks fail the rollback must restore
    the PREVIOUS release, not refuse `same-latest` on the failed pub: the
    failed generation's own latest.json records `previous` for exactly
    this."""
    store = _arb_store(tmp_path)
    _arb_seed_pub(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_pub(store, _PUB_B, "sig-2026-10-02.1")
    _arb_seed_registry(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_promotable(store, _PUB_B)

    def crash_checks(_s: rp.Store, *, gen: int, pub: str) -> list[dict[str, Any]]:
        raise RuntimeError("simulated crash after the generation write")

    with pytest.raises(RuntimeError):
        _arb_promote(tmp_path, _PUB_B, post_checks=crash_checks)
    # the half-finished generation is the current one now
    assert _conf_doc(tmp_path, 2, "latest.json")["publication_id"] == _PUB_B

    # a real crash leaves the promote lock held — the operator breaks it
    # (recorded into the fresh lock) and the resume completes the verb
    with pytest.raises(rp.PipelineError) as exc:
        _arb_promote(
            tmp_path,
            _PUB_B,
            post_checks=_failing_checks,
            break_lock="operator break after the crash",
        )
    assert exc.value.code == "post-check-failed"
    latest3 = _conf_doc(tmp_path, 3, "latest.json")
    assert latest3["publication_id"] == _PUB_A  # restored, not a same-latest refusal
    detail = exc.value.detail or {}
    assert detail["auto_rollback"]["outcome"] == "rolled-back"
    incidents = sorted((tmp_path / "registry" / "incidents").glob("*.json"))
    note = json.loads(incidents[-1].read_bytes())
    assert note["restored_publication_id"] == _PUB_A


def test_dry_run_never_touches_the_rollback_path(tmp_path: Path) -> None:
    store = _arb_store(tmp_path)
    _arb_seed_pub(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_pub(store, _PUB_B, "sig-2026-10-02.1")
    _arb_seed_registry(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_promotable(store, _PUB_B)
    out = _arb_promote(tmp_path, _PUB_B, apply_=False, post_checks=_failing_checks)
    assert out["dry_run"] is True and out["applied"] is False
    assert not (tmp_path / "registry" / "incidents").exists()
    assert not (tmp_path / "registry" / "conf" / "2").exists()


def test_auto_rollback_disabled_keeps_the_old_posture(tmp_path: Path) -> None:
    """auto_rollback=False — the pre-P35.58 journal-and-refuse shape; the
    alert + incident note still record what the operator must see."""
    store = _arb_store(tmp_path)
    _arb_seed_pub(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_pub(store, _PUB_B, "sig-2026-10-02.1")
    _arb_seed_registry(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_promotable(store, _PUB_B)
    with pytest.raises(rp.PipelineError) as exc:
        _arb_promote(tmp_path, _PUB_B, post_checks=_failing_checks, auto_rollback=False)
    assert exc.value.code == "post-check-failed"
    assert not (tmp_path / "registry" / "conf" / "3").exists()
    assert "auto-rollback: disabled" in str(exc.value)
    incidents = sorted((tmp_path / "registry" / "incidents").glob("*.json"))
    assert incidents  # the note is still append-only evidence


def test_injected_rollback_runner_is_recorded_verbatim(tmp_path: Path) -> None:
    """The test seam: an injected runner's return rides the incident note
    verbatim — the machinery never pretends it ran the real verb."""
    store = _arb_store(tmp_path)
    _arb_seed_pub(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_pub(store, _PUB_B, "sig-2026-10-02.1")
    _arb_seed_registry(store, _PUB_A, "sig-2026-10-01.1")
    _arb_seed_promotable(store, _PUB_B)
    seen: dict[str, Any] = {}

    def runner(store: rp.Store, *, to: str, reason: str, go: str) -> dict[str, Any]:
        seen["to"] = to
        seen["reason"] = reason
        seen["go"] = go
        return {"outcome": "rolled-back", "conf_gen": 3}

    with pytest.raises(rp.PipelineError) as exc:
        _arb_promote(tmp_path, _PUB_B, post_checks=_failing_checks, rollback_runner=runner)
    assert exc.value.code == "post-check-failed"
    assert seen["to"] == _PUB_A and seen["go"] == "d-g3-8"
    detail = exc.value.detail or {}
    assert detail["auto_rollback"]["runner"] == "injected"
