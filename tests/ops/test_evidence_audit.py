# SPDX-License-Identifier: Apache-2.0
"""The P32.6 evidence-audit suite (SIG-TRUST-007).

Every test asserts a contract the ticket names — denominators, the five
evidence states, the three semantic forms, the anti-inflation rule, the dry
fixtures (recoverable / digest-mismatched / missing / restricted), and the
prohibition on deriving replayability from ``source_id``.
"""

from __future__ import annotations

import json

import pytest
from evidence.digest import multihash
from ops.evidence_audit import (
    DEFAULT_ROLL_BOUNDARY,
    NULL_PROBE,
    Adjudication,
    CaptureRecord,
    CaptureVerdict,
    ClaimBinding,
    ClaimUnit,
    EvidenceGrade,
    FixtureCaptureProbe,
    OccurrenceConfidence,
    run_audit,
    stratum_of,
    units_from_rows,
    verify_capture,
    verify_digest,
)

SEED = "p32-6-test-seed"
POST = "2026-10-01T00:00:00Z"
PRE = "2026-09-20T00:00:00Z"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _bytes(text: str) -> bytes:
    return text.encode("utf-8")


def _mark(digest: str, run: str = "run-1", obj: str | None = None, ver: str | None = "v1") -> dict:
    return {
        "run_id": run,
        "target_key": "t1",
        "state": "flushed",
        "capture_digest": digest,
        "source_uri": "https://example.test/page",
        "media_type": "text/plain",
        "byte_size": 10,
        "retrieved_at": POST,
        "records": 1,
        "ocfl_object_id": obj,
        "ocfl_version": ver,
        "recorded_at": POST,
    }


def _capture(**kw) -> CaptureRecord:
    base = dict(
        capture_id="cap-1",
        classification="actual",
        content_digest=None,
        byte_size=None,
        media_type="text/plain",
        ocfl_object_id=None,
        ocfl_version=None,
        storage_tier="public",
        retrieved_at=POST,
        retrieved_by_run_id="run-1",
        source_uri="https://example.test/page",
        artifact_stable_locator="https://example.test/page",
        artifact_type="document",
        artifact_source_id="atlas_registry",
        marks=(),
    )
    base.update(kw)
    return CaptureRecord(**base)


def _binding(capture: CaptureRecord | None, **kw) -> ClaimBinding:
    base = dict(
        role="establishes",
        binding_status="actual_capture",
        locator={"kind": "byte_range", "start": 0, "end": 4},
        extraction_id="ex-1",
        extraction_config_digest="cfg-1",
        extractor_version="parser/1.2.3",
        bound_at=POST,
        capture=capture,
    )
    base.update(kw)
    return ClaimBinding(**base)


def _unit(cid: str, bindings=(), **kw) -> ClaimUnit:
    base = dict(
        claim_id=cid,
        predicate_id="camera_location",
        subject_id="ent-1",
        source_id="atlas_registry",
        connector_name="atlas_registry",
        run_started_at=POST,
        rights_spdx="CC-BY-4.0",
        compartment="cc_by",
        bindings=tuple(bindings),
        publication_eligible=True,
    )
    base.update(kw)
    return ClaimUnit(**base)


def _probe(*pairs: tuple[str, str]) -> FixtureCaptureProbe:
    """``(object_id, text)`` → a probe with each object at v1."""
    return FixtureCaptureProbe({oid: {"v1": _bytes(text)} for oid, text in pairs})


def _actual_capture_with_bytes(
    text: str, *, run: str = "run-1", retrieved: str = POST
) -> CaptureRecord:
    """A fully-wired actual capture: real digest, OCFL ids, agreeing mark."""
    digest = multihash(_bytes(text))
    obj = f"sig:capture:{digest}"
    return _capture(
        content_digest=digest,
        byte_size=len(_bytes(text)),
        ocfl_object_id=obj,
        ocfl_version="v1",
        retrieved_at=retrieved,
        retrieved_by_run_id=run,
        marks=(_mark(digest, run=run, obj=obj, ver="v1"),),
    )


def _audit(units, probe=NULL_PROBE, **kw) -> object:
    return run_audit(
        list(units),
        probe,
        seed=kw.pop("seed", SEED),
        sample_size=kw.pop("sample_size", 100),
        boundary=kw.pop("boundary", DEFAULT_ROLL_BOUNDARY),
        **kw,
    )


def _result(report, cid: str) -> dict:
    return next(u for u in report.units if u["claim_id"] == cid)


# ---------------------------------------------------------------------------
# Digest + probe verification
# ---------------------------------------------------------------------------


def test_verify_digest_matches_multihash_and_sha256_hex():
    data = _bytes("record")
    assert verify_digest(multihash(data), data) == "multihash-sha256-b32"
    import hashlib

    assert verify_digest(hashlib.sha256(data).hexdigest(), data) == "sha256-hex"
    assert verify_digest(multihash(data), b"other") is None


def test_recoverable_fixture_grades_exact_replayable():
    cap = _actual_capture_with_bytes("operator: Acme")
    b = _binding(cap, locator={"kind": "byte_range", "start": 0, "end": 4})
    unit = _unit("c-ok", [b], raw_value="oper")
    report = _audit([unit], _probe((cap.ocfl_object_id, "operator: Acme")))
    row = _result(report, "c-ok")
    assert row["grade"] == EvidenceGrade.EXACT_REPLAYABLE
    assert row["occurrence_confidence"] == OccurrenceConfidence.EXACT
    assert row["adjudication"] == Adjudication.ESTABLISHED
    assert row["capture_checks"][0]["verdict"] == CaptureVerdict.VERIFIED
    assert row["capture_checks"][0]["matched_algorithm"] == "multihash-sha256-b32"


def test_digest_mismatch_fixture_is_a_finding_never_adopted():
    cap = _actual_capture_with_bytes("operator: Acme")
    b = _binding(cap)
    unit = _unit("c-mism", [b], raw_value="oper")
    # The probe holds DIFFERENT bytes at the recorded object.
    report = _audit([unit], _probe((cap.ocfl_object_id, "tampered bytes")))
    row = _result(report, "c-mism")
    assert row["grade"] == EvidenceGrade.UNRECOVERABLE
    assert "digest_mismatch" in row["flags"]
    assert row["capture_checks"][0]["verdict"] == CaptureVerdict.DIGEST_MISMATCH
    assert row["adjudication"] == Adjudication.UNRESOLVED
    assert any(f["kind"] == "digest_mismatch" for f in report.findings)


def test_missing_fixture_reported_explicitly():
    cap = _actual_capture_with_bytes("operator: Acme")
    unit = _unit("c-miss", [_binding(cap)])
    report = _audit([unit], _probe())  # the object is absent
    row = _result(report, "c-miss")
    assert row["capture_checks"][0]["verdict"] == CaptureVerdict.MISSING
    assert row["grade"] == EvidenceGrade.UNRECOVERABLE
    assert row["occurrence_confidence"] == OccurrenceConfidence.EXACT  # occurrence still attested
    assert any(f["kind"] == "missing_bytes" for f in report.findings)


def test_restricted_fixture_is_distinct_from_loss():
    cap = _actual_capture_with_bytes("sealed bytes", retrieved=POST)
    cap = _capture(
        **{**cap.__dict__, "storage_tier": "restricted"}  # type: ignore[arg-type]
    )
    unit = _unit("c-restr", [_binding(cap)])
    report = _audit([unit], _probe((cap.ocfl_object_id, "sealed bytes")))
    row = _result(report, "c-restr")
    assert row["grade"] == EvidenceGrade.RESTRICTED_NOT_PUBLIC
    assert row["capture_checks"][0]["restricted_access"] is True
    # verified but restricted — NEVER 'missing', NEVER public-replayable
    assert row["capture_checks"][0]["verdict"] == CaptureVerdict.VERIFIED


def test_restricted_unreadable_reports_restricted_not_missing():
    digest = multihash(_bytes("sealed"))
    cap = _capture(
        content_digest=digest,
        byte_size=6,
        ocfl_object_id=f"sig:capture:{digest}",
        ocfl_version="v1",
        storage_tier="sealed",
        marks=(_mark(digest, obj=f"sig:capture:{digest}"),),
    )
    unit = _unit("c-sealed", [_binding(cap)])
    report = _audit([unit], _probe())  # privileged reader absent → unreadable
    row = _result(report, "c-sealed")
    assert row["grade"] == EvidenceGrade.RESTRICTED_NOT_PUBLIC
    assert "restricted_unverified" in row["flags"]
    assert not any(f["kind"] == "missing_bytes" for f in report.findings)


def test_no_probe_reports_unverified_never_missing():
    cap = _actual_capture_with_bytes("x")
    unit = _unit("c-noprobe", [_binding(cap)])
    report = _audit([unit], NULL_PROBE)
    row = _result(report, "c-noprobe")
    assert row["capture_checks"][0]["verdict"] == CaptureVerdict.UNVERIFIED
    assert not any(f["kind"] == "missing_bytes" for f in report.findings)


# ---------------------------------------------------------------------------
# The axes are independent
# ---------------------------------------------------------------------------


def test_verified_bytes_without_marks_is_bounded_not_exact():
    cap = _capture(
        classification="actual",
        content_digest=multihash(_bytes("b")),
        byte_size=1,
        ocfl_object_id=None,
        ocfl_version=None,
        marks=(),  # pre-P31.4: no marks
    )
    unit = _unit("c-nomark", [_binding(cap)])
    # derive object id from the digest (pre-P32.2 rows lack ocfl ids)
    probe = _probe((f"sig:capture:{cap.content_digest}", "b"))
    report = _audit([unit], probe)
    row = _result(report, "c-nomark")
    assert row["occurrence_confidence"] == OccurrenceConfidence.BOUNDED
    assert row["grade"] == EvidenceGrade.EXACT_REPLAYABLE  # bytes+locator+extractor prove replay


def test_verified_bytes_no_locator_is_document_locatable():
    cap = _actual_capture_with_bytes("b")
    unit = _unit("c-noloc", [_binding(cap, locator=None)])
    probe = _probe((cap.ocfl_object_id, "b"))
    row = _result(_audit([unit], probe), "c-noloc")
    assert row["grade"] == EvidenceGrade.DOCUMENT_LOCATABLE
    assert "no_exact_locator" in row["flags"]


def test_verified_bytes_no_extractor_is_document_locatable():
    cap = _actual_capture_with_bytes("b")
    unit = _unit(
        "c-noext",
        [
            _binding(
                cap,
                locator={"kind": "byte_range", "start": 0, "end": 1},
                extractor_version=None,
                extraction_id=None,
                extraction_method=None,
            )
        ],
    )
    probe = _probe((cap.ocfl_object_id, "b"))
    row = _result(_audit([unit], probe), "c-noext")
    assert row["grade"] == EvidenceGrade.DOCUMENT_LOCATABLE
    assert "no_extractor_identity" in row["flags"]


def test_synthetic_only_is_source_attributed():
    cap = _capture(
        classification="synthetic",
        content_digest="0" * 64,
        byte_size=0,
        artifact_stable_locator="sig:connector:atlas_registry",
    )
    unit = _unit("c-synth", [_binding(cap, binding_status="legacy_synthetic")])
    row = _result(_audit([unit]), "c-synth")
    assert row["grade"] == EvidenceGrade.SOURCE_ATTRIBUTED_ONLY
    assert row["occurrence_confidence"] == OccurrenceConfidence.BOUNDED


def test_no_evidence_link_is_unrecoverable():
    unit = _unit("c-none", [])
    row = _result(_audit([unit]), "c-none")
    assert row["grade"] == EvidenceGrade.UNRECOVERABLE


def test_dangling_capture_reference_is_ambiguous():
    b = _binding(None)
    b = ClaimBinding(
        role="establishes",
        binding_status="actual_capture",
        locator=None,
        dangling_capture_id="cap-gone",
    )
    unit = _unit("c-dangle", [b])
    row = _result(_audit([unit]), "c-dangle")
    assert "dangling_capture" in row["flags"]
    assert "ambiguous_lineage" in row["flags"]


def test_contested_marks_make_occurrence_ambiguous():
    cap = _capture(
        classification="actual",
        content_digest="d1",
        byte_size=5,
        ocfl_object_id=None,
        ocfl_version=None,
        retrieved_by_run_id="run-1",
        marks=(
            _mark("d1", run="run-2", obj="objA", ver="v1"),
            _mark("d1", run="run-3", obj="objB", ver="v2"),
        ),
    )
    unit = _unit("c-contest", [_binding(cap)])
    # probe can verify bytes at the derived object — occurrence still ambiguous
    probe = _probe(("sig:capture:d1", "bytes"))
    row = _result(_audit([unit], probe), "c-contest")
    assert row["occurrence_confidence"] == OccurrenceConfidence.UNKNOWN
    assert "ambiguous_lineage" in row["flags"]


# ---------------------------------------------------------------------------
# Roles + epochs
# ---------------------------------------------------------------------------


def test_operational_predicate_with_only_synthetic_support_flags_unsupported():
    cap = _capture(classification="synthetic", content_digest="0" * 64, byte_size=0)
    unit = _unit(
        "c-role",
        [_binding(cap, binding_status="legacy_synthetic")],
        predicate_id="camera_operator",
        object_entity="ent-acme",
    )
    row = _result(_audit([unit]), "c-role")
    assert "unsupported_role_mapping" in row["flags"]


def test_publisher_predicate_never_needs_role_support():
    cap = _capture(classification="synthetic", content_digest="0" * 64, byte_size=0)
    unit = _unit(
        "c-pub",
        [_binding(cap, binding_status="legacy_synthetic")],
        predicate_id="camera_registry_publisher",
        object_entity=None,
    )
    row = _result(_audit([unit]), "c-pub")
    assert "unsupported_role_mapping" not in row["flags"]


def test_operational_predicate_with_verified_support_is_not_flagged():
    cap = _actual_capture_with_bytes("oper")
    unit = _unit(
        "c-role-ok",
        [_binding(cap)],
        predicate_id="camera_operator",
        object_entity="ent-acme",
    )
    probe = _probe((cap.ocfl_object_id, "oper"))
    row = _result(_audit([unit], probe), "c-role-ok")
    assert "unsupported_role_mapping" not in row["flags"]


def test_epoch_stratification():
    pre = _unit("c-pre", [_binding(_actual_capture_with_bytes("a", retrieved=PRE))])
    post = _unit("c-post", [_binding(_actual_capture_with_bytes("b", retrieved=POST))])
    undated = _unit("c-undated", [_binding(_capture(retrieved_at=None))])
    assert stratum_of(pre, DEFAULT_ROLL_BOUNDARY).capture_epoch == "pre_roll"
    assert stratum_of(post, DEFAULT_ROLL_BOUNDARY).capture_epoch == "post_roll"
    assert stratum_of(undated, DEFAULT_ROLL_BOUNDARY).capture_epoch == "undated"


def test_no_replayability_from_source_id_alone():
    """A real source_id + a synthetic capture ⇒ never exact_replayable."""
    cap = _capture(classification="synthetic", content_digest="0" * 64, byte_size=0)
    unit = _unit("c-src", [_binding(cap, binding_status="legacy_synthetic")])
    report = _audit([unit], NULL_PROBE)
    assert _result(report, "c-src")["grade"] != EvidenceGrade.EXACT_REPLAYABLE
    assert report.metrics["verified_capture_availability"]["numerator"] == 0
    assert report.metrics["replay_success"]["numerator"] == 0


# ---------------------------------------------------------------------------
# Census + sampling + determinism
# ---------------------------------------------------------------------------


def _population(n: int = 60) -> list[ClaimUnit]:
    """A mixed population across families/epochs/roles/compartments."""
    units = []
    roles = ["camera_location", "camera_operator", "camera_registry_publisher", "height"]
    for i in range(n):
        text = f"value-{i}"
        cap = _actual_capture_with_bytes(text, retrieved=PRE if i % 2 else POST, run=f"run-{i % 3}")
        units.append(
            _unit(
                f"c-{i:03d}",
                [_binding(cap, locator={"kind": "byte_range", "start": 0, "end": 5})],
                predicate_id=roles[i % len(roles)],
                object_entity="e" if roles[i % len(roles)] == "camera_operator" else None,
                connector_name="atlas_registry" if i % 3 else "osm_overpass",
                rights_spdx="ODbL-1.0" if i % 3 == 0 else "CC-BY-4.0",
                compartment="odbl" if i % 3 == 0 else "cc_by",
                raw_value="value",
            )
        )
    return units


def _population_probe(units) -> FixtureCaptureProbe:
    objs = {}
    for i, u in enumerate(units):
        for b in u.bindings:
            if b.capture and b.capture.ocfl_object_id:
                objs[b.capture.ocfl_object_id] = {"v1": _bytes(f"value-{i}")}
    return FixtureCaptureProbe(objs)


def test_census_denominators_reconcile_to_population():
    units = _population()
    report = _audit(units, _population_probe(units))
    c = report.census
    assert c["claims"] == len(units)
    assert c["reconciles"] is True
    for axis in ("by_source_family", "by_capture_epoch", "by_predicate_role", "by_compartment"):
        assert sum(c[axis].values()) == len(units)
    assert sum(s["universe"] for s in report.strata) == len(units)


def test_reproducible_sampling_frame():
    units = _population()
    probe = _population_probe(units)
    r1 = _audit(units, probe, sample_size=20)
    r2 = _audit(units, probe, sample_size=20)
    assert r1.dumps() == r2.dumps()
    r3 = _audit(units, probe, sample_size=20, seed="other-seed")
    ids1 = {u["claim_id"] for u in r1.units if u["in_sample"]}
    ids3 = {u["claim_id"] for u in r3.units if u["in_sample"]}
    assert ids1 != ids3 or len(ids1) == len(units)


def test_sample_weights_recorded():
    units = _population(30)
    report = _audit(units, _population_probe(units), sample_size=10)
    sampled = [u for u in report.units if u["in_sample"]]
    assert sampled and all(u["sample_weight"] for u in sampled)
    for s in report.strata:
        assert s["universe"] >= s["drawn"]


def test_targeted_set_reported_separately_unweighted():
    units = _population(30)
    targeted = {units[0].claim_id}
    report = _audit(units, _population_probe(units), sample_size=5, targeted_ids=targeted)
    targeted_rows = report.adjudication["targeted_set"]
    assert targeted_rows[0]["claim_id"] == units[0].claim_id
    u0 = _result(report, units[0].claim_id)
    assert u0["in_sample"] is True and u0["in_targeted_set"] is True
    assert u0["sample_weight"] is None  # targeted rows carry no weight


# ---------------------------------------------------------------------------
# Semantic trio + anti-inflation
# ---------------------------------------------------------------------------


def test_semantic_trio_three_forms():
    cap_ok = _actual_capture_with_bytes("oper")
    cap_bad = _actual_capture_with_bytes("zzz-not-the-value")
    cap_synth = _capture(classification="synthetic", content_digest="0" * 64, byte_size=0)
    units = [
        _unit("c-e", [_binding(cap_ok)], raw_value="oper"),
        _unit("c-n", [_binding(cap_bad)], raw_value="oper"),
        _unit("c-u", [_binding(cap_synth, binding_status="legacy_synthetic")]),
    ]
    probe = _probe((cap_ok.ocfl_object_id, "oper"), (cap_bad.ocfl_object_id, "zzz-not-the-value"))
    report = _audit(units, probe)
    adj = report.adjudication
    assert adj["sampled_eligible"] == 3
    assert adj["established"] == 1
    assert adj["adjudicated"] == 2  # established + replay_disagreement
    assert adj["unresolved"] == 1
    assert adj["support_all"] == pytest.approx(1 / 3)
    assert adj["conditional_fidelity"] == pytest.approx(1 / 2)
    assert adj["adjudication_yield"] == pytest.approx(2 / 3)


def test_missing_evidence_cannot_inflate_fidelity():
    """The anti-inflation rule: evidence loss stays in the fidelity denominator."""
    cap_ok = _actual_capture_with_bytes("oper")
    cap_lose = _actual_capture_with_bytes("zzzz")
    units = [
        _unit("c-e", [_binding(cap_ok)], raw_value="oper"),
        _unit("c-lost", [_binding(cap_lose)], raw_value="zzzz"),
    ]
    # Full bytes → both adjudicated → fidelity 1.0
    full = _probe((cap_ok.ocfl_object_id, "oper"), (cap_lose.ocfl_object_id, "zzzz"))
    r_full = _audit(units, full)
    assert r_full.adjudication["conditional_fidelity"] == pytest.approx(1.0)
    # Bytes vanish for c-lost → unresolved/evidence_unavailable → fidelity drops,
    # never rises; yield drops; support_all drops.
    sparse = _probe((cap_ok.ocfl_object_id, "oper"))
    r_lost = _audit(units, sparse)
    adj = r_lost.adjudication
    assert adj["unresolved_evidence_unavailable"] == 1
    assert adj["conditional_fidelity"] == pytest.approx(1 / 2)
    assert adj["conditional_fidelity"] < r_full.adjudication["conditional_fidelity"]
    assert adj["adjudication_yield"] == pytest.approx(1 / 2)
    assert adj["support_all"] == pytest.approx(1 / 2)


def test_replay_disagreement_is_not_established():
    cap = _actual_capture_with_bytes("totally-different")
    unit = _unit("c-dis", [_binding(cap)], raw_value="oper")
    probe = _probe((cap.ocfl_object_id, "totally-different"))
    row = _result(_audit([unit], probe), "c-dis")
    assert row["adjudication"] == Adjudication.NOT_ESTABLISHED
    assert "replay_disagreement" in row["flags"]


def test_replay_success_denominator_is_replayable_units():
    cap_ok = _actual_capture_with_bytes("oper")
    cap_synth = _capture(classification="synthetic", content_digest="0" * 64, byte_size=0)
    units = [
        _unit("c-e", [_binding(cap_ok)], raw_value="oper"),
        _unit("c-s", [_binding(cap_synth, binding_status="legacy_synthetic")]),
    ]
    probe = _probe((cap_ok.ocfl_object_id, "oper"))
    report = _audit(units, probe)
    rs = report.metrics["replay_success"]
    assert rs["denominator"] == 1  # only the replayable unit
    assert rs["numerator"] == 1


def test_adjudicator_verdicts_flow_into_the_trio():
    cap = _actual_capture_with_bytes("z")  # page locator — not mechanical
    unit = _unit("c-adj", [_binding(cap, locator={"kind": "page", "page": 2})])
    probe = _probe((cap.ocfl_object_id, "z"))
    report = _audit([unit], probe, adjudications={"c-adj": "established"})
    row = _result(report, "c-adj")
    assert row["adjudication"] == Adjudication.ESTABLISHED
    assert row["adjudication_basis"] == "adjudicator-supplied"


# ---------------------------------------------------------------------------
# Byte budget + loader row round-trip
# ---------------------------------------------------------------------------


def test_byte_budget_exhaustion_reports_unverified():
    caps = [_actual_capture_with_bytes(f"b{i}", run=f"run-{i}") for i in range(3)]
    units = [_unit(f"c-{i}", [_binding(caps[i])]) for i in range(3)]
    probe = _probe(*[(c.ocfl_object_id, f"b{i}") for i, c in enumerate(caps)])
    report = _audit(units, probe, byte_budget=3)  # tiny: exhausts after ~3 bytes
    assert report.input["byte_budget_exhausted"] is True
    verdicts = {u["capture_checks"][0]["verdict"] for u in report.units}
    assert CaptureVerdict.UNVERIFIED in verdicts


def test_units_from_rows_groups_and_dedups():
    row_base = {
        "claim_id": "c-1",
        "predicate_id": "camera_location",
        "subject_id": "e",
        "object_entity": None,
        "object_type": None,
        "value_kind": "value",
        "value_text": "v",
        "raw_value": "v",
        "observed_at": POST,
        "claim_digest": "d",
        "claim_extraction_id": None,
        "ingest_run_id": "r",
        "sensitivity_tier": 0,
        "review_status": "unreviewed",
        "capture_id": "cap-1",
        "binding_extraction_id": "ex",
        "role": "establishes",
        "locator": {"kind": "byte_range", "start": 0, "end": 1},
        "extraction_config_digest": "cfg",
        "extractor_version": "x/1",
        "binding_status": "actual_capture",
        "bound_at": POST,
        "capture_classification": "actual",
        "capture_digest": multihash(_bytes("z")),
        "byte_size": 1,
        "media_type": "text/plain",
        "ocfl_object_id": "sig:capture:x",
        "ocfl_version": "v1",
        "storage_tier": "public",
        "retrieved_at": POST,
        "retrieved_by_run_id": "run-1",
        "capture_source_uri": "u",
        "artifact_id": "a",
        "source_id": "src",
        "artifact_url": "u",
        "stable_locator": "u",
        "artifact_type": "document",
        "acquisition_method": "http",
        "capture_status": "captured",
        "connector_name": "atlas_registry",
        "connector_version": "1",
        "code_commit": "abc",
        "is_replay": False,
        "run_started_at": POST,
        "spdx_expression": "CC-BY-4.0",
        "redistributable": "yes",
        "derivative_permitted": "yes",
        "rights_retrieval_date": "2026-01-01",
        "extraction_extractor_name": "parser",
        "extraction_extractor_version": "x/1",
        "extraction_method": "structured",
    }
    marks = {row_base["capture_digest"]: [_mark(row_base["capture_digest"], obj="sig:capture:x")]}
    units = units_from_rows([row_base, dict(row_base)], marks, {"c-1"})
    assert len(units) == 1
    assert len(units[0].bindings) == 1
    assert units[0].bindings[0].capture.marks
    assert units[0].publication_eligible is True


def test_report_is_json_serializable_and_digest_stable():
    cap = _actual_capture_with_bytes("v")
    report = _audit([_unit("c-1", [_binding(cap)])], _probe((cap.ocfl_object_id, "v")))
    s = report.dumps()
    assert json.loads(s)["audit_version"] == "evidence-audit/1"
    assert report.digest()


def test_findings_cover_each_failure_kind():
    cap_m = _actual_capture_with_bytes("x")
    cap_d = _actual_capture_with_bytes("y", run="r2")
    cap_s = _capture(classification="synthetic", content_digest="0" * 64, byte_size=0)
    units = [
        _unit("c-miss", [_binding(cap_m)]),
        _unit("c-mism", [_binding(cap_d)]),
        _unit(
            "c-role",
            [_binding(cap_s, binding_status="legacy_synthetic")],
            predicate_id="camera_operator",
            object_entity="e",
        ),
    ]
    probe = _probe((cap_d.ocfl_object_id, "different"))
    report = _audit(units, probe)
    kinds = {f["kind"] for f in report.findings}
    assert {"missing_bytes", "digest_mismatch", "unsupported_role_mapping"} <= kinds


def test_byte_size_and_mark_attested_pinned_version():
    """The audit reads the PINNED version, not head — v1 bytes verify even when
    v2 (a later re-fetch) carries different bytes."""
    cap = _actual_capture_with_bytes("old")
    objs = {cap.ocfl_object_id: {"v1": _bytes("old"), "v2": _bytes("new")}}
    probe = FixtureCaptureProbe(objs)
    check = verify_capture(cap, probe)
    assert check.verdict == CaptureVerdict.VERIFIED
    assert check.version == "v1"
