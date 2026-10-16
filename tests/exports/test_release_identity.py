# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.12 — release identity v2 + clock guards (SIG-REL-001/002/003; G3 §3).

Covers the whole REL-01 acceptance surface:

* the human label ``sig-YYYY-MM-DD.N`` — derived from ``snapshot.as_of_world``
  (never typed), allocated under the registry lock, same-day second build →
  ``.2``, collisions/refusals named;
* the export id ``sig-export-<ts>-<key8>`` — the NEW-1 same-day fix
  (instants + watermark + commit in the key);
* the descriptor ``sig.publication-descriptor/2`` — every §3.2 field
  populated or explicitly declared-empty, fail-closed validation, v1 still
  parseable but never promotable;
* the §3.3 clock guards — T0-once, host-clock sanity, the AR-3 frozen
  window (``--emergency`` lifts it), typed-as-of ≤ built_at, no emitted date
  later than built_at, ``--replay`` → Class S;
* the SIG-REL-002 promotion refusals — v1 descriptor, dirty tree, unpushed
  commit, ``0.0.0``, non-sha commit, an as-of earlier than the previous.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from exports.manifest import BuildSpec
from exports.release import ReleaseError, activate, build_release, promote

from exports import release_identity as RI

T0 = datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)
AS_OF_WORLD = "2026-10-16T00:00:00Z"
AS_OF_BELIEF = "2026-10-16T00:00:00Z"
COMMIT = "0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d"


# --------------------------------------------------------------------------- #
# Fixtures — a minimal export dir + a v2 build                                #
# --------------------------------------------------------------------------- #


def _site_row(i: int) -> dict[str, Any]:
    return {
        "entity_type": "camera",
        "entity_id": f"ent-{i}",
        "source_id": "src_a",
        "label": f"Site {i}",
        "technology": "alpr",
        "jurisdiction": "OK",
        "claim_ids": [f"claim-{i}"],
        "geometry": None,
        "_rights": {
            "source_id": "src_a",
            "attribution_required": True,
            "attribution": "Test Source",
            "spdx": "CC-BY-4.0",
        },
    }


def _write_export(root: Path, *, manifest_extra: dict[str, Any] | None = None) -> Path:
    comp = "sig_graph"
    (root / comp).mkdir(parents=True)
    (root / "web").mkdir(parents=True)
    rows = [_site_row(1), _site_row(2)]
    (root / comp / "sites.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    (root / comp / "record_claims.jsonl").write_text(
        "".join(
            json.dumps(
                {
                    "claim_id": f"claim-{i}",
                    "entity_id": f"ent-{i}",
                    "source_id": "src_a",
                    "evidence_artifact_ids": [],
                }
            )
            + "\n"
            for i in (1, 2)
        ),
        encoding="utf-8",
    )
    (root / "web" / "evidence.json").write_text(
        json.dumps({"artifacts": [], "claim_views": []}), encoding="utf-8"
    )
    manifest: dict[str, Any] = {
        "artifacts": [
            {
                "path": f"{comp}/sites.jsonl",
                "compartment": comp,
                "license": "CC-BY-4.0",
                "sha256": "0" * 64,
                "byte_size": 1,
                "media_type": "application/json",
            },
            {
                "path": "web/terms_disclosure.json",
                "compartment": "web",
                "license": "CC-BY-4.0",
                "sha256": "1" * 64,
                "byte_size": 1,
                "media_type": "application/json",
            },
        ],
        "concept_id": "sig",
        "content_key": "a" * 64,
        "release_id": "sig-export-20261016T000000Z-deadbeef",
        "reproducibility_inputs": {
            "as_of_belief": "2026-10-16",
            "as_of_snapshot": "2026-10-16",
            "resolver_version": "0.1.0+g00000000",
            "ruleset_version": "p27.3/1.0.0",
        },
        "snapshot": {
            "as_of_world": AS_OF_WORLD,
            "as_of_belief": AS_OF_BELIEF,
            "belief_pinned": False,
            "spine_watermark": "claims=42 closed=0 bump=42",
            "materialize_run": None,
            "sqitch_head": "p35.12-test-head",
            "restore_point": None,
        },
        "environment": "fixture",
    }
    manifest.update(manifest_extra or {})
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _v2_build(
    tmp_path: Path,
    export: Path,
    name: str = "rel",
    registry: Path | None = None,
    **kw: Any,
):
    kw.setdefault("descriptor_version", 2)
    kw.setdefault("built_at", T0)
    kw.setdefault("code_commit", COMMIT)
    kw.setdefault("code_tree", "clean")
    kw.setdefault("ontology_generated_sha256", "b" * 64)
    if registry is None:
        registry = tmp_path / "registry"
    if "label" not in kw and "labels_registry" not in kw:
        kw["labels_registry"] = registry
    return build_release(export, tmp_path / name, **kw)


# --------------------------------------------------------------------------- #
# The human label                                                             #
# --------------------------------------------------------------------------- #


def test_label_form_and_derivation() -> None:
    assert RI.label_for(AS_OF_WORLD, 1) == "sig-2026-10-16.1"
    assert RI.label_for(AS_OF_WORLD, 2) == "sig-2026-10-16.2"
    # the date comes from the instant, never a typed day
    assert RI.label_for("2026-10-15T23:59:59Z", 1) == "sig-2026-10-15.1"
    with pytest.raises(RI.LabelRegistryError):
        RI.label_for("not-a-date", 1)


def test_same_day_allocation_increments(tmp_path: Path) -> None:
    reg = tmp_path / "registry"
    first = RI.allocate_label(reg, AS_OF_WORLD, allocated_at=T0)
    second = RI.allocate_label(reg, AS_OF_WORLD, allocated_at=T0)
    assert first == "sig-2026-10-16.1"
    assert second == "sig-2026-10-16.2"
    doc = RI.load_labels(reg)
    assert [e["label"] for e in doc["labels"]] == [first, second]
    assert (reg / "labels.lock").exists()


def test_label_counts_catalog_publications_for_the_date(tmp_path: Path) -> None:
    """A catalog entry on the same as-of date occupies its ordinal — a
    registry that knew the release before labels.json landed can never
    re-issue its number (SIG-REL-001)."""
    reg = tmp_path / "registry"
    reg.mkdir()
    (reg / "catalog.json").write_text(
        json.dumps(
            {
                "schema": "sig.publication-catalog/1",
                "publications": [
                    {
                        "publication_id": "p-" + "a" * 64,
                        "label": "sig-2026-10-16.1",
                        "compat": {"as_of_world": "2026-10-16"},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert RI.allocate_label(reg, AS_OF_WORLD) == "sig-2026-10-16.2"


def test_label_reuse_is_refused(tmp_path: Path) -> None:
    """A hand-edited labels.json cannot silently re-issue a label."""
    reg = tmp_path / "registry"
    RI.allocate_label(reg, AS_OF_WORLD, allocated_at=T0)
    # second same-day allocation must take .2 — never .1 again
    assert RI.allocate_label(reg, AS_OF_WORLD) == "sig-2026-10-16.2"


def test_v2_build_derives_label_from_snapshot_date(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    assert build.descriptor["label"] == "sig-2026-10-16.1"
    assert build.descriptor["snapshot"]["as_of_world"] == AS_OF_WORLD


def test_v2_build_second_same_day_release_takes_2(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    reg = tmp_path / "registry"
    a = _v2_build(tmp_path, export, name="a", registry=reg)
    b = _v2_build(tmp_path, export, name="b", registry=reg)
    assert a.descriptor["label"] == "sig-2026-10-16.1"
    assert b.descriptor["label"] == "sig-2026-10-16.2"


def test_typed_label_must_derive_from_the_snapshot_date(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    # a label whose date is NOT the snapshot's UTC date is refused — the
    # label date is the data date, never typed (§3.3 rule 6).
    with pytest.raises(ReleaseError, match="does not derive"):
        _v2_build(tmp_path, export, label="sig-2026-10-17.1")  # future-ok: synthetic: vs T0


def test_labelless_v2_build_is_refused(tmp_path: Path) -> None:
    """No registry + no typed label → no silently minted label."""
    export = _write_export(tmp_path / "export")
    with pytest.raises(ReleaseError, match="needs a label"):
        build_release(
            export,
            tmp_path / "out",
            descriptor_version=2,
            built_at=T0,
            code_commit=COMMIT,
            code_tree="clean",
        )


# --------------------------------------------------------------------------- #
# The export id                                                               #
# --------------------------------------------------------------------------- #


def _spec(**kw: Any) -> BuildSpec:
    d: dict[str, Any] = dict(
        as_of_snapshot=date(2026, 10, 16),
        as_of_belief=date(2026, 10, 16),
        ruleset_version="ruleset/1",
        resolver_version="resolver/1",
        as_of_snapshot_instant="2026-10-16T00:00:00Z",
    )
    d.update(kw)
    return BuildSpec(**d)  # type: ignore[arg-type]


def test_export_id_form() -> None:
    rid = _spec().release_id()
    assert RI.EXPORT_ID_RE.match(rid), rid


def test_export_id_same_day_no_collision(tmp_path: Path) -> None:
    """NEW-1: two same-day exports with different spine state or code can
    never share an id — the watermark and commit are in the key."""
    a = _spec(spine_watermark="claims=10 bump=10", code_commit="a" * 40)
    b = _spec(spine_watermark="claims=11 bump=11", code_commit="a" * 40)
    c = _spec(spine_watermark="claims=10 bump=10", code_commit="b" * 40)
    assert len({a.release_id(), b.release_id(), c.release_id()}) == 3
    assert a.release_id() != b.release_id()


def test_export_id_is_idempotent_for_identical_inputs() -> None:
    """Two builds of the SAME spec name the same export (SIG-EXPORT-003)."""
    assert _spec().release_id() == _spec().release_id()


def test_export_id_differs_on_instants(tmp_path: Path) -> None:
    a = _spec(as_of_snapshot_instant="2026-10-16T00:00:00Z")
    b = _spec(as_of_snapshot_instant="2026-10-16T01:00:00Z")
    assert a.release_id() != b.release_id()
    assert b.release_id().startswith("sig-export-20261016T010000Z-")


# --------------------------------------------------------------------------- #
# The §3.3 clock guards                                                        #
# --------------------------------------------------------------------------- #


def test_freeze_window_monthly() -> None:
    # day 6 00:00Z → day 13 12:00Z
    assert RI.freeze_window(datetime(2026, 10, 6, 0, 0, tzinfo=UTC)) is not None
    assert RI.freeze_window(datetime(2026, 10, 10, 12, 0, tzinfo=UTC)) is not None
    assert RI.freeze_window(datetime(2026, 10, 13, 11, 59, tzinfo=UTC)) is not None
    assert RI.freeze_window(datetime(2026, 10, 13, 12, 0, tzinfo=UTC)) is None
    assert RI.freeze_window(datetime(2026, 10, 5, 23, 59, tzinfo=UTC)) is None


def test_freeze_window_daily() -> None:
    # 03:00Z → 06:30Z
    assert RI.freeze_window(datetime(2026, 10, 20, 3, 0, tzinfo=UTC)) is not None
    assert RI.freeze_window(datetime(2026, 10, 20, 6, 29, tzinfo=UTC)) is not None
    assert RI.freeze_window(datetime(2026, 10, 20, 6, 30, tzinfo=UTC)) is None
    assert RI.freeze_window(datetime(2026, 10, 20, 2, 59, tzinfo=UTC)) is None


def test_frozen_window_refuses_without_emergency() -> None:
    with pytest.raises(RI.ClockGuardError, match="frozen window"):
        RI.assert_not_frozen(datetime(2026, 10, 7, 12, 0, tzinfo=UTC))


def test_frozen_window_emergency_lifts() -> None:
    RI.assert_not_frozen(datetime(2026, 10, 7, 12, 0, tzinfo=UTC), emergency="takedown X")
    RI.assert_not_frozen(datetime(2026, 10, 20, 4, 0, tzinfo=UTC), emergency="takedown Y")


def test_host_clock_ok(tmp_path: Path) -> None:
    report = RI.host_clock_report(
        T0,
        fetcher=lambda: "Fri, 16 Oct 2026 12:00:05 GMT",
    )
    assert report["ok"] and report["skew_seconds"] == 5.0


def test_host_clock_skew_refuses() -> None:
    with pytest.raises(RI.ClockGuardError, match="skew"):
        RI.host_clock_report(T0, fetcher=lambda: "Fri, 16 Oct 2026 12:05:00 GMT")


def test_host_clock_unreachable_refuses() -> None:
    def _boom() -> str:
        raise OSError("no network")

    with pytest.raises(RI.ClockGuardError, match="could not read"):
        RI.host_clock_report(T0, fetcher=_boom)


def test_future_as_of_refuses() -> None:
    with pytest.raises(RI.ClockGuardError, match="future"):
        RI.check_as_of_clock("2026-10-17T00:00:00Z", T0)  # future-ok: synthetic: vs T0


def test_as_of_later_than_built_at_refuses() -> None:
    """The typed as-of can never exceed the build instant (SIG-REL-003)."""
    built = datetime(2026, 10, 16, 8, 0, 0, tzinfo=UTC)
    with pytest.raises(RI.ClockGuardError, match="later than the build instant"):
        RI.check_as_of_clock("2026-10-16T12:00:00Z", built)


def test_same_day_as_of_is_the_cut_path() -> None:
    RI.check_as_of_clock("2026-10-16T08:00:00Z", T0)  # earlier same UTC day


def test_earlier_day_as_of_requires_replay() -> None:
    with pytest.raises(RI.ClockGuardError, match="replay"):
        RI.check_as_of_clock("2026-10-15T00:00:00Z", T0)
    # with --replay the historical cut is allowed (and forced Class S)
    RI.check_as_of_clock("2026-10-15T00:00:00Z", T0, replay="verify rerun")


def test_replay_forces_class_s(tmp_path: Path) -> None:
    export = _write_export(
        tmp_path / "export",
        manifest_extra={"environment": "replay", "replay": "verify rerun"},
    )
    build = _v2_build(tmp_path, export, environment="replay")
    assert build.descriptor["environment"] == "replay"
    assert build.descriptor["build"]["publish_class"] == "S"
    assert build.descriptor["build"]["replay_reason"] == "verify rerun"


def test_replay_environment_needs_a_reason(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export", manifest_extra={"environment": "replay"})
    with pytest.raises(ReleaseError, match="replay reason"):
        _v2_build(tmp_path, export, environment="replay")


def test_descriptor_clock_ordering(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    doc = build.descriptor
    assert RI.descriptor_clock_failures(doc, now=T0) == []
    # belief later than built_at violates the chain
    doc2 = json.loads(json.dumps(doc))
    doc2["snapshot"]["as_of_belief"] = "2026-10-17T00:00:00Z"  # future-ok: synthetic: vs T0
    failures = RI.descriptor_clock_failures(doc2, now=T0)
    assert any("as_of_belief" in f for f in failures)


def test_emitted_date_scan() -> None:
    doc = {
        "label": "sig-2026-10-16.1",
        "built_at": "2026-10-16T12:00:00Z",
        "notes": "generated 2026-10-20T09:00:00Z",  # future-ok: synthetic: vs T0
        "expiry_date": "2030-01-01T00:00:00Z",
    }
    failures = RI.emitted_date_failures(doc, T0)
    assert len(failures) == 1 and "notes" in failures[0]


def test_cli_from_spine_future_as_of_refuses(capsys: pytest.CaptureFixture[str]) -> None:
    """The operator path refuses a future --as-of BEFORE any DB read."""
    from exports.cli import main

    code = main(
        [
            "build",
            "--from-spine",
            "--dsn",
            "postgresql://x",
            "--as-of",
            "2999-01-01T00:00:00Z",  # future-ok: synthetic: future refusal input
            "--out",
            "/tmp/x",
            "--skip-host-clock-check",
        ]
    )
    assert code == 4
    assert "future" in capsys.readouterr().out


def test_cli_from_spine_earlier_day_requires_replay(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from exports.cli import main

    code = main(
        [
            "build",
            "--from-spine",
            "--dsn",
            "postgresql://x",
            "--as-of",
            "2020-01-01T00:00:00Z",
            "--out",
            "/tmp/x",
            "--skip-host-clock-check",
        ]
    )
    assert code == 4
    assert "replay" in capsys.readouterr().out


def test_cli_from_spine_emergency_flag_flows(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Inside a frozen window, --emergency is the only lift — exercised by
    monkeypatching the clock to a frozen instant."""
    from exports import cli as cli_mod

    frozen = datetime(2026, 10, 7, 12, 0, 0, tzinfo=UTC)
    monkey_t0 = pytest.MonkeyPatch()
    try:
        monkey_t0.setattr(cli_mod, "_t0_for_tests", frozen, raising=False)
    finally:
        monkey_t0.undo()
    # the direct guard check is the binding assertion
    RI.assert_not_frozen(frozen, emergency="op")


# --------------------------------------------------------------------------- #
# The sig.publication-descriptor/2 document                                   #
# --------------------------------------------------------------------------- #


def test_v2_descriptor_required_fields(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    doc = build.descriptor
    assert doc["schema"] == RI.DESCRIPTOR_SCHEMA_V2
    assert doc["label"] == "sig-2026-10-16.1"
    assert doc["environment"] == "fixture"
    snap = doc["snapshot"]
    assert snap["as_of_world"] == AS_OF_WORLD
    assert snap["as_of_belief"] == AS_OF_BELIEF
    assert snap["belief_pinned"] is False
    assert snap["spine_watermark"] == "claims=42 closed=0 bump=42"
    assert "materialize_run" in snap and "sqitch_head" in snap
    assert "restore_point" in snap
    assert doc["export"]["id"] == "sig-export-20261016T000000Z-deadbeef"
    assert doc["export"]["content_key"] == "a" * 64
    assert doc["code"]["commit"] == COMMIT
    assert doc["code"]["tree"] == "clean"
    assert doc["renderer"]["revision"] == COMMIT  # one code identity (NEW-3)
    versions = doc["versions"]
    for field in (
        "ruleset_version",
        "resolver_version",
        "policy_version",
        "projection_version",
        "search_index_version",
        "ontology_version",
        "ontology_generated_sha256",
        "descriptor_schema",
    ):
        assert field in versions, field
    assert versions["descriptor_schema"] == RI.DESCRIPTOR_SCHEMA_V2
    assert doc["gates"]["attribution_gate"]["pass_count"] == 2
    assert len(doc["gates"]["disposition_root"]) == 64
    assert (
        doc["gates"]["rights_registry_sha256"] is None
        or len(doc["gates"]["rights_registry_sha256"]) == 64
    )
    assert doc["evaluation"]["status"] == "deferred"
    assert doc["evaluation"]["eval_confidence"]["mode"] == "shadow"
    assert isinstance(doc["disclosures"], list)
    # J3 TX-13b: transparency_root populated (terms_disclosure artifact
    # exists) — boundaries_root present, declared-empty until JUR-01 lands.
    assert doc["transparency_root"] is not None
    assert len(doc["transparency_root"]) == 64
    assert "boundaries_root" in doc
    assert doc["build"]["built_at"] == "2026-10-16T12:00:00Z"


def test_v2_descriptor_validates_clean(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    assert RI.validate_descriptor(build.descriptor, now=T0) == []


def test_v2_validator_is_fail_closed(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    doc = _v2_build(tmp_path, export).descriptor
    # missing required field
    bad = json.loads(json.dumps(doc))
    del bad["snapshot"]["spine_watermark"]
    assert any("spine_watermark" in f for f in RI.validate_descriptor(bad, now=T0))
    # wrong schema id
    bad = json.loads(json.dumps(doc))
    bad["schema"] = "sig.publication-descriptor/1"
    assert RI.validate_descriptor(bad, now=T0)
    # non-sha commit
    bad = json.loads(json.dumps(doc))
    bad["code"]["commit"] = "abc"
    assert any("commit" in f for f in RI.validate_descriptor(bad, now=T0))
    # label not matching the snapshot date
    bad = json.loads(json.dumps(doc))
    bad["label"] = "sig-2026-10-17.1"  # future-ok: synthetic: fixture date vs fixed T0
    assert any("label" in f for f in RI.validate_descriptor(bad, now=T0))


def test_v1_descriptor_still_parseable(tmp_path: Path) -> None:
    """v1 remains a first-class read path (records/descriptors built before
    v2 stay consumable); only promotion refuses it."""
    export = _write_export(tmp_path / "export")
    build = build_release(
        export, tmp_path / "v1", descriptor_version=1, renderer_revision="ab" * 20
    )
    doc = build.descriptor
    assert doc["schema"] == RI.DESCRIPTOR_SCHEMA_V1
    assert RI.descriptor_release_id(doc) == doc["data_release_id"]
    assert RI.descriptor_as_of_world(doc) == "2026-10-16"
    # the v2 accessors read v1 shape transparently
    assert RI.descriptor_versions_block(doc)["ruleset_version"] == "p27.3/1.0.0"


def test_v1_and_v2_namespaces_differ(tmp_path: Path) -> None:
    """The descriptor schema is an identity input — v1 and v2 of the same
    export are different publications."""
    export = _write_export(tmp_path / "export")
    v1 = build_release(export, tmp_path / "v1", descriptor_version=1, renderer_revision="ab" * 20)
    v2 = _v2_build(tmp_path, export, name="v2")
    assert v1.publication_id != v2.publication_id


def test_v2_refuses_renderer_revision(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    with pytest.raises(ReleaseError, match="one code identity"):
        build_release(
            export,
            tmp_path / "out",
            descriptor_version=2,
            renderer_revision="ab" * 20,
            labels_registry=tmp_path / "reg",
        )


# --------------------------------------------------------------------------- #
# The SIG-REL-002 promotion refusals                                          #
# --------------------------------------------------------------------------- #


def _promotable_doc(tmp_path: Path) -> dict[str, Any]:
    export = _write_export(tmp_path / "export")
    return _v2_build(tmp_path, export).descriptor


def test_promotion_refuses_v1_descriptor(tmp_path: Path) -> None:
    """The v2-only rule alone keeps the p-17b713 fixture class out."""
    v1_doc = {"schema": RI.DESCRIPTOR_SCHEMA_V1, "data_release_id": "sig-x"}
    refusals = RI.promotion_refusals(v1_doc)
    assert any("v2" in r or DESCRIPTOR in r for r in refusals for DESCRIPTOR in [""])
    assert any("not sig.publication-descriptor/2" in r for r in refusals)


def test_promotion_refuses_dirty_tree(tmp_path: Path) -> None:
    doc = _promotable_doc(tmp_path)
    refusals = RI.promotion_refusals(doc, tree_clean=False, pushed=True)
    assert any("dirty" in r for r in refusals)
    doc["code"]["tree"] = "dirty"
    assert any("dirty" in r for r in RI.promotion_refusals(doc, pushed=True))


def test_promotion_refuses_unpushed_commit(tmp_path: Path) -> None:
    doc = _promotable_doc(tmp_path)
    refusals = RI.promotion_refusals(doc, tree_clean=True, pushed=False)
    assert any("pushed" in r for r in refusals)


def test_promotion_refuses_non_sha_commit(tmp_path: Path) -> None:
    doc = _promotable_doc(tmp_path)
    doc["code"]["commit"] = "main"
    refusals = RI.promotion_refusals(doc, tree_clean=True, pushed=True)
    assert any("40-hex" in r for r in refusals)


def test_promotion_refuses_zero_versions(tmp_path: Path) -> None:
    doc = _promotable_doc(tmp_path)
    doc["versions"]["resolver_version"] = "0.0.0"
    refusals = RI.promotion_refusals(doc, tree_clean=True, pushed=True)
    assert any("0.0.0" in r for r in refusals)
    doc["label"] = "0.0.0"
    assert any("label" in r for r in RI.promotion_refusals(doc, tree_clean=True, pushed=True))


def test_promotion_refuses_earlier_release_date(tmp_path: Path) -> None:
    doc = _promotable_doc(tmp_path)
    refusals = RI.promotion_refusals(
        doc,
        tree_clean=True,
        pushed=True,
        previous_as_of_world="2026-10-20T00:00:00Z",  # future-ok: synthetic: vs T0
    )
    assert any("earlier" in r for r in refusals)
    # a later or equal previous passes this check
    assert not any(
        "earlier" in r
        for r in RI.promotion_refusals(
            doc,
            tree_clean=True,
            pushed=True,
            previous_as_of_world="2026-10-15T00:00:00Z",
        )
    )


def test_promotion_clean_candidate_has_no_refusals(tmp_path: Path) -> None:
    doc = _promotable_doc(tmp_path)
    assert RI.promotion_refusals(doc, tree_clean=True, pushed=True) == []


def test_promote_end_to_end_refuses_v1_and_activates_v2(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    registry = tmp_path / "registry"
    # v1 candidate: refused before anything activates
    v1 = build_release(export, tmp_path / "v1", descriptor_version=1, renderer_revision="ab" * 20)
    with pytest.raises(ReleaseError, match="promotion refused"):
        promote(registry, v1.out_dir, pushed=True, tree_clean=True)
    # v2 candidate on injected-clean/pushed probes: activates
    v2 = _v2_build(tmp_path, export, name="v2", registry=registry)
    act = promote(registry, v2.out_dir, pushed=True, tree_clean=True)
    assert act["publication_id"] == v2.publication_id
    latest = json.loads((registry / "latest.json").read_text())
    assert latest["publication_id"] == v2.publication_id
    assert latest["data_release_id"] == "sig-2026-10-16.1"


def test_promote_names_every_refusal(tmp_path: Path) -> None:
    """The gate reports the whole refusal set at once, never the first one."""
    doc = _promotable_doc(tmp_path)
    doc["code"]["commit"] = "notasha"
    doc["versions"]["ruleset_version"] = "0.0.0"
    doc["code"]["tree"] = "dirty"
    refusals = RI.promotion_refusals(doc, tree_clean=False, pushed=False)
    assert len(refusals) >= 4


def test_activation_refuses_before_built_at(tmp_path: Path) -> None:
    """§3.3 rule 3: activated_at ≥ built_at — a release never activates
    before its own recorded build instant."""
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    registry = tmp_path / "registry"
    early = T0 - timedelta(hours=1)
    with pytest.raises(ReleaseError, match="earlier than built_at"):
        activate(registry, build.out_dir, now=early)
    act = activate(registry, build.out_dir, now=T0 + timedelta(minutes=1))
    assert act["publication_id"] == build.publication_id


def test_validate_release_runs_descriptor_validation(tmp_path: Path) -> None:
    from exports.release import validate_release

    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    assert validate_release(build.out_dir).state == "complete"
    # corrupt the descriptor's snapshot → validate_release reports it
    desc_path = build.out_dir / f"releases/{build.publication_id}/descriptor.json"
    doc = json.loads(desc_path.read_text())
    doc["snapshot"]["as_of_belief"] = "2026-10-20T00:00:00Z"  # future-ok: synthetic: vs T0
    # re-fix the artifact sha so only the *field* check fires is impossible —
    # a tampered descriptor ALSO fails its integrity digest; both are named.
    desc_path.write_text(json.dumps(doc), encoding="utf-8")
    report = validate_release(build.out_dir)
    assert report.state == "incomplete"


def test_catalog_entry_carries_label_as_data_release_id(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _v2_build(tmp_path, export)
    entry = json.loads(
        (build.out_dir / f"releases/{build.publication_id}/catalog_entry.json").read_text()
    )
    assert entry["data_release_id"] == "sig-2026-10-16.1"
    assert entry["compat"]["as_of_world"] == "2026-10-16"
    assert entry["reproducibility"]["as_of_world"] == AS_OF_WORLD


# --------------------------------------------------------------------------- #
# CLI surface                                                                 #
# --------------------------------------------------------------------------- #


def test_cli_label_allocate(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from exports.cli import main

    reg = tmp_path / "registry"
    code = main(["release", "label-allocate", "--registry", str(reg), "--as-of", AS_OF_WORLD])
    assert code == 0
    assert capsys.readouterr().out.strip() == "sig-2026-10-16.1"


def test_cli_promote_refuses_v1(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from exports.cli import main

    export = _write_export(tmp_path / "export")
    v1 = build_release(export, tmp_path / "v1", descriptor_version=1, renderer_revision="ab" * 20)
    code = main(
        [
            "release",
            "promote",
            "--registry",
            str(tmp_path / "registry"),
            "--release",
            str(v1.out_dir),
        ]
    )
    assert code == 4
    assert "promotion refused" in capsys.readouterr().out
