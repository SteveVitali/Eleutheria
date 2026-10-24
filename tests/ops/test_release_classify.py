# SPDX-License-Identifier: Apache-2.0
"""P35.60 (REL-06 / SIG-REL-012 / SIG-CONF-010) — the §7.3 release
classifier, the standing-go record checks, the §7.4 readout generator and
the pending-readout notice.

The catalog AC verbatim: the classifier returns Class S on an unevaluable
check and on a ratchet-regression input; every §7.1 bound breach and §7.2
named trigger returns Class S; an in-bounds diff returns Class R; an
expired/void/out-of-scope standing go is refused; the readout carries the
required wordings verbatim, labelled agent-drafted, signature slot empty.

The green fixture is the real one — the same built v2 release +
S-mode suite ``test_release_verify`` runs (V14's deltas consumed verbatim,
never re-derived); planted defects mutate the *emitted* result doc or the
*declared* metadata the classifier reads.

Nothing here is a live/hosted leg — ``live_verification=false``; the
``--apply`` writes land in a ``LocalDirStore`` fixture registry only.
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "ops" / "src"))
sys.path.insert(0, str(REPO / "tests" / "ops"))

from test_release_verify import (  # noqa: E402
    AS_OF_WORLD,
    COMMIT,
    T0,
    _build_candidate,
    _ctx,
)

from ops import alerts  # noqa: E402
from ops import release_classify as rcls  # noqa: E402
from ops import release_conf as rc  # noqa: E402
from ops import release_pipeline as rp  # noqa: E402
from ops import release_verify as rv  # noqa: E402

NOW = T0


# --------------------------------------------------------------------------- #
# Fixture plumbing                                                            #
# --------------------------------------------------------------------------- #


def _classified_fixture(
    tmp_path: Path, *, mutate: Any = None, pre_cut: bool = True
) -> tuple[Path, str, rp.LocalDirStore, dict[str, Any]]:
    """``(work_dir, pub, store, suite_doc)`` — the real green posture: a
    scheduled cut journaled *before* the candidate's first event, the prior
    release recorded as Class-S-signed (gen-1 pointer + its signed_readout
    approval), and the real S-mode suite run over the tree origin."""
    root = tmp_path / "relroot"
    if pre_cut:
        rp.emit_event(
            rp.LocalDirStore(root),
            "cut",
            None,
            {
                "outcome": "recorded",
                "t0": T0.isoformat(),
                "as_of": AS_OF_WORLD,
                "replay": None,
                "emergency": None,
            },
            now=T0,
        )
    work_dir, pub, store = _build_candidate(tmp_path)
    old_pub = str(json.loads(store.read("registry/conf/1/latest.json")).get("publication_id") or "")
    # the prior release was signed under Class S — the generation pointer
    # says so and its approval record resolves to a signed readout.
    gen_doc = json.loads(store.read("registry/conf/1/latest.json"))
    approval_obj = "registry/approvals/prior-readout.json"
    gen_doc["class"] = "S"
    gen_doc["approval_ref"] = {"object": approval_obj, "kind": "signed_readout"}
    (root / "registry" / "conf" / "1" / "latest.json").write_bytes(json.dumps(gen_doc).encode())
    (root / "registry" / "approvals").mkdir(parents=True, exist_ok=True)
    (root / "registry" / "approvals" / "prior-readout.json").write_bytes(
        json.dumps(
            {
                "schema": "sig.promotion-approval/1",
                "kind": "signed_readout",
                "publication_id": old_pub,
                "signature": "sig:operator-verbatim-decision",
                "ref": "readout for " + old_pub,
                "approved_at": "2026-10-01T12:00:00Z",
            }
        ).encode()
    )
    suite = rv.run_suite(_ctx(work_dir, pub, store))
    if mutate is not None:
        mutate(suite)
    return work_dir, pub, store, suite


def _suite_file(tmp_path: Path, suite: dict[str, Any]) -> Path:
    out = tmp_path / "results"
    out.mkdir(exist_ok=True)
    f = out / "suite-S-fixture.json"
    f.write_text(json.dumps(suite), encoding="utf-8")
    return out


def _classify(store: rp.LocalDirStore, pub: str, suite: dict[str, Any]) -> dict[str, Any]:
    return rcls.classify(store, pub, suites=[suite], now=NOW)


def _v14(suite: dict[str, Any]) -> dict[str, Any]:
    return {r["check"]: r for r in suite["results"]}["V14"]


def _seed_go(
    store: rp.LocalDirStore, name: str = "go.json", *, root: Path | None = None, **over: Any
) -> str:
    rec = {
        "schema": "sig.promotion-approval/1",
        "kind": "standing_go",
        "class": "class_r",
        "ref": "B-9 (GATE-P, 2026-10-01T04:35:53Z)",
        "approved_at": "2026-10-01T04:35:53Z",
        "expires_at": "2026-12-31T00:00:00Z",
    }
    rec.update(over)
    base = (root or Path(store.root)) / "registry" / "approvals"
    base.mkdir(parents=True, exist_ok=True)
    (base / name).write_bytes(json.dumps(rec).encode())
    return f"registry/approvals/{name}"


# --------------------------------------------------------------------------- #
# The green path — an in-bounds diff classifies R                             #
# --------------------------------------------------------------------------- #


def test_in_bounds_diff_classifies_class_r(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    assert suite["verdict"] == "pass", json.dumps(suite["counts"])
    record = _classify(store, pub, suite)
    assert record["schema"] == rcls.CLASSIFICATION_SCHEMA
    assert record["class"] == "class_r", json.dumps(
        [r for r in record["checks"] if r["verdict"] != "r"], indent=1
    )
    assert not record["triggers"] and not record["unevaluable"]
    # every check landed a row — the ledger is complete, never silent
    assert len(record["checks"]) >= 10
    # the emitted deltas are consumed verbatim (V14 measured; the
    # classifier read the row, never re-derived it)
    deltas = record["evidence"]["v14_deltas"]
    assert deltas == _v14(suite)["evidence"]["deltas"]
    assert deltas["records"]["total"]["previous"] == deltas["records"]["total"]["current"]


def test_verb_classify_apply_journals_and_records(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    results = _suite_file(tmp_path, suite)
    notices: list[alerts.Alert] = []
    out = rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=results,
        notice_hook=notices.append,
    )
    assert out["class"] == "class_r" and out["applied"] is True
    assert out["event"].startswith("registry/events/")
    rec_obj = json.loads(store.read(out["classification_object"]))
    assert rec_obj["schema"] == rcls.CLASSIFICATION_SCHEMA
    assert rec_obj["class"] == "class_r"
    # the journal the promote verb folds
    assert rc.journal_class(store, pub) == "class_r"
    # B-9's promised mail — the classified notice carries the diff+checks
    assert len(notices) == 1 and notices[0].kind == rcls.NOTICE_KIND_R
    assert notices[0].detail["publication_id"] == pub
    assert notices[0].detail["v14_diff"]["total"]["current"] == 2
    # Class R drafts no readout
    assert not store.list(rcls.READOUTS_PREFIX)


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    out = rp.verb_classify(
        store, apply_=False, publication_id=pub, results=_suite_file(tmp_path, suite)
    )
    assert out["dry_run"] is True and out["class"] == "class_r"
    assert store.list(rcls.CLASSIFICATIONS_PREFIX) == []
    assert store.list(rcls.READOUTS_PREFIX) == []
    # dry-run never locks the registry
    assert store.read("registry/LOCK") is None


# --------------------------------------------------------------------------- #
# Fail-closed: anything unevaluable is Class S                                #
# --------------------------------------------------------------------------- #


def test_no_results_is_fail_closed_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    out = rp.verb_classify(store, apply_=False, publication_id=pub, results=None)
    assert out["class"] == "class_s" and out["failclosed"] is True
    assert "suite-input" in out["unevaluable"]


def test_unreadable_results_file_fails_closed(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    bad = tmp_path / "results-bad"
    bad.mkdir()
    (bad / "suite-S-broken.json").write_bytes(b"{not json")
    docs, unreadable = rcls.load_suite_documents(bad)
    assert docs == [] and unreadable
    record = rcls.classify(store, pub, suites=docs, unreadable_inputs=unreadable)
    assert record["class"] == "class_s" and record["unevaluable"]


def test_a_failed_check_row_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _v14(suite)["status"] = "fail"
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "check-not-green:V14" in record["triggers"]


def test_a_skipped_check_row_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    {r["check"]: r for r in suite["results"]}["V5"]["status"] = "skip"
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "check-not-green:V5" in record["triggers"]


def test_a_waiver_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    suite["waivers"] = [{"check": "V11", "readout": "r.md"}]
    suite["verdict"] = "waived"
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "waiver-present" in record["triggers"]


def test_missing_result_row_is_unevaluable(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    suite["results"] = [r for r in suite["results"] if r["check"] != "V14"]
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "suite-input" in record["unevaluable"]


def test_missing_descriptor_fails_closed(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    (tmp_path / "relroot" / "staged" / "releases" / pub / "descriptor.json").unlink()
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "environment" in record["unevaluable"] or "signed-code" in record["unevaluable"]


def test_absent_cut_event_is_unevaluable(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path, pre_cut=False)
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "cut-provenance" in record["unevaluable"]


# --------------------------------------------------------------------------- #
# The §7.2/§7.3 named triggers — each returns Class S by name                 #
# --------------------------------------------------------------------------- #


def _delta(suite: dict[str, Any]) -> dict[str, Any]:
    return _v14(suite)["evidence"]["deltas"]


def test_ratchet_regression_is_class_s(tmp_path: Path) -> None:
    """The catalog AC — a V15 ratchet signal is Class S verbatim (ADR-154)."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    v15 = {r["check"]: r for r in suite["results"]}["V15"]
    v15["status"] = "fail"
    v15["evidence"] = {
        "gate": {"verdict": "fail", "ratchet_regressions": [{"id": "GQ-1"}]},
        "class_s_signal": True,
    }
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "ratchet-regression" in record["triggers"]


def test_first_release_no_baseline_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["baseline"] = None
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "first-release" in record["triggers"]


def test_total_records_bounds_breach_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["records"]["total"] = {"previous": 100, "current": 120}
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "total-records-bounds" in record["triggers"]


def test_compartment_bounds_breach_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["records"]["per_compartment"] = {
        "sig_graph": {"previous": 100, "current": 40, "pct": -60.0}
    }
    _delta(suite)["records"]["total"] = {"previous": 100, "current": 40}
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "compartment-bounds:sig_graph" in record["triggers"]


def test_new_compartment_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["records"]["per_compartment"]["osm_physical"] = {
        "previous": 0,
        "current": 5,
        "pct": 100.0,
    }
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "new-compartment:osm_physical" in record["triggers"]


def test_new_source_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["sources"]["added"] = ["new_source_9"]
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "new-source" in record["triggers"]


def test_source_removed_without_a_recorded_withdrawal_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["sources"]["removed"] = ["src_a"]
    # a present withdrawal registry with no covering entry → the named
    # trigger; an absent registry is instead unevaluable (fail closed)
    (tmp_path / "relroot" / "registry" / "withdrawals.json").write_text(
        json.dumps({"schema": "sig.withdrawal-registry/1", "entries": []})
    )
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "source-withdrawal-unrecorded" in record["triggers"]


def test_source_removed_with_absent_registry_is_unevaluable(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["sources"]["removed"] = ["src_a"]
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "sources-withdrawn" in record["unevaluable"]


def test_source_removed_through_a_recorded_withdrawal_stays_r(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["sources"]["removed"] = ["src_a"]
    # 'fewer only through recorded withdrawals' — the registry names it
    (tmp_path / "relroot" / "registry" / "withdrawals.json").write_text(
        json.dumps(
            {
                "schema": "sig.withdrawal-registry/1",
                "entries": [
                    {
                        "target_kind": "entity",
                        "target_id": "src_a",
                        "disposition": "withdraw",
                        "reason_category": "rights_withdrawal",
                        "authority": "ord-9",
                        "decided_at": T0.isoformat(),
                    }
                ],
            }
        )
    )
    record = _classify(store, pub, suite)
    assert "source-withdrawal-unrecorded" not in record["triggers"]
    assert record["class"] == "class_r", json.dumps(
        [r for r in record["checks"] if r["verdict"] != "r"], indent=1
    )


def test_licence_change_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["licences"]["added"] = ["ODbL-1.0"]
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "licence-change" in record["triggers"]


def test_template_fingerprint_change_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["template_fingerprint"]["changed"] = True
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "template-fingerprint-change" in record["triggers"]


def test_template_fingerprint_unavailable_is_fail_closed(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["template_fingerprint"] = {"state": "unavailable", "owner": "test"}
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "template-fingerprint" in record["unevaluable"]


def test_version_change_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["version_schema"]["current"]["ruleset_version"] = "p28/2.0.0"
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "version-change:ruleset_version" in record["triggers"]


def test_part_viii_screen_change_is_class_s(tmp_path: Path) -> None:
    """A policy_version delta is the Part VIII screen change B-9 voids on
    — read from the descriptors' versions blocks (declared metadata)."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    baseline = str(_delta(suite)["baseline"]["publication_id"])
    d_path = tmp_path / "relroot" / "staged" / "releases" / baseline / "descriptor.json"
    doc = json.loads(d_path.read_bytes())
    doc["versions"]["policy_version"] = "publication-eligibility/0"
    d_path.write_bytes(json.dumps(doc).encode())
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "part-viii-screen-change" in record["triggers"]


def test_v14_failure_lines_are_named_triggers(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _v14(suite)["evidence"]["failures"] = ["source src_a: 2 → 0 records (dropped)"]
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "v14-anomaly" in record["triggers"]


def test_allowlist_change_is_class_s(tmp_path: Path) -> None:
    """The declared allow-list digest differs (release.json metadata)."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    baseline = str(_delta(suite)["baseline"]["publication_id"])
    rel_path = tmp_path / "relroot" / "staged" / "releases" / baseline / "release.json"
    doc = json.loads(rel_path.read_bytes())
    doc["routes_sha256"] = "f" * 64
    rel_path.write_bytes(json.dumps(doc).encode())
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "allowlist-change" in record["triggers"]


def test_new_public_surface_is_class_s(tmp_path: Path) -> None:
    """A non-record route appearing in the candidate manifest is §7.2's
    'new public surface' — record-namespace churn is not."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    man_path = tmp_path / "relroot" / "staged" / "releases" / pub / "integrity_manifest.json"
    man = json.loads(man_path.read_bytes())
    man["artifacts"].append(
        {
            "path": f"r/{pub}/dashboard/index.html",
            "media_type": "text/html",
            "compartment": "web",
            "license": "CC-BY-4.0",
            "sha256": "0" * 64,
            "byte_size": 10,
        }
    )
    man_path.write_bytes(json.dumps(man).encode())
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "new-public-surface" in record["triggers"]


def test_record_routes_churn_is_not_a_surface_change(tmp_path: Path) -> None:
    """New record pages under c/<comp>/ are data refresh, not a new surface."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    man_path = tmp_path / "relroot" / "staged" / "releases" / pub / "integrity_manifest.json"
    man = json.loads(man_path.read_bytes())
    man["artifacts"].append(
        {
            "path": f"r/{pub}/c/sig_graph/entity/camera/ent-new/index.html",
            "media_type": "text/html",
            "compartment": "sig_graph",
            "license": "CC-BY-4.0",
            "sha256": "1" * 64,
            "byte_size": 10,
        }
    )
    man_path.write_bytes(json.dumps(man).encode())
    record = _classify(store, pub, suite)
    assert "new-public-surface" not in record["triggers"]
    assert record["class"] == "class_r"


def test_disclosure_change_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    baseline = str(_delta(suite)["baseline"]["publication_id"])
    d_path = tmp_path / "relroot" / "staged" / "releases" / baseline / "descriptor.json"
    doc = json.loads(d_path.read_bytes())
    doc["disclosures"] = [{"id": "new-disclosure", "text": "new text"}]
    d_path.write_bytes(json.dumps(doc).encode())
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "disclosure-change" in record["triggers"]


def test_evaluation_status_change_is_class_s(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    baseline = str(_delta(suite)["baseline"]["publication_id"])
    d_path = tmp_path / "relroot" / "staged" / "releases" / baseline / "descriptor.json"
    doc = json.loads(d_path.read_bytes())
    doc["evaluation"]["status"] = "certified"
    d_path.write_bytes(json.dumps(doc).encode())
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "evaluation-status-change" in record["triggers"]


def test_replay_cut_is_class_s(tmp_path: Path) -> None:
    root = tmp_path / "relroot"
    rp.emit_event(
        rp.LocalDirStore(root),
        "cut",
        None,
        {
            "outcome": "recorded",
            "t0": T0.isoformat(),
            "as_of": AS_OF_WORLD,
            "replay": "2026-10-15T00:00:00Z",
            "emergency": None,
        },
        now=T0,
    )
    work_dir, pub, store = _build_candidate(tmp_path)
    gen_doc = json.loads(store.read("registry/conf/1/latest.json"))
    gen_doc["class"] = "S"
    gen_doc["approval_ref"] = {
        "object": "registry/approvals/prior-readout.json",
        "kind": "signed_readout",
    }
    (root / "registry" / "conf" / "1" / "latest.json").write_bytes(json.dumps(gen_doc).encode())
    (root / "registry" / "approvals").mkdir(parents=True, exist_ok=True)
    old_pub = str(gen_doc["publication_id"])
    (root / "registry" / "approvals" / "prior-readout.json").write_bytes(
        json.dumps(
            {
                "schema": "sig.promotion-approval/1",
                "kind": "signed_readout",
                "publication_id": old_pub,
                "signature": "sig:x",
            }
        ).encode()
    )
    suite = rv.run_suite(_ctx(work_dir, pub, store))
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "replay-or-emergency-cut" in record["triggers"]


def test_no_signed_code_baseline_is_class_s(tmp_path: Path) -> None:
    """No Class-S generation exists → nothing the operator signed to match."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    gen_doc = json.loads(store.read("registry/conf/1/latest.json"))
    gen_doc["class"] = "R"  # the only generation was never S-signed
    (tmp_path / "relroot" / "registry" / "conf" / "1" / "latest.json").write_bytes(
        json.dumps(gen_doc).encode()
    )
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s"
    assert "no-signed-code-baseline" in record["triggers"]


def test_code_change_is_class_s(tmp_path: Path) -> None:
    """The signed baseline's code.commit differs → any code change is S."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    baseline = str(_delta(suite)["baseline"]["publication_id"])
    d_path = tmp_path / "relroot" / "staged" / "releases" / baseline / "descriptor.json"
    doc = json.loads(d_path.read_bytes())
    doc["code"]["commit"] = "f" * 40
    d_path.write_bytes(json.dumps(doc).encode())
    record = _classify(store, pub, suite)
    assert record["class"] == "class_s" and "code-change" in record["triggers"]


# --------------------------------------------------------------------------- #
# The standing go — validated, never implied (§7.3 / B-9)                     #
# --------------------------------------------------------------------------- #


def test_standing_go_absent_is_not_valid(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    st = rcls.evaluate_standing_go(store, "go.json", pub, now=NOW)
    assert st["status"] == "absent"


def test_standing_go_valid_records_status(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store)
    st = rcls.evaluate_standing_go(store, "go.json", pub, now=NOW, classified_at=NOW)
    assert st["status"] == "valid" and st["expires_at"]


def test_standing_go_expired_before_classify_is_refused(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store, expires_at="2026-10-01T00:00:00Z")
    st = rcls.evaluate_standing_go(store, "go.json", pub, now=NOW, classified_at=NOW)
    assert st["status"] == "expired"


def test_standing_go_expired_after_classify_is_honoured_in_flight(tmp_path: Path) -> None:
    """§7.3 in-flight: expired at promote-time but valid at classify-time."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store, expires_at="2026-10-20T00:00:00Z")  # after T0, before NOW
    later = NOW + timedelta(days=10)
    st = rcls.evaluate_standing_go(store, "go.json", pub, now=later, classified_at=NOW)
    assert st["status"] == "expired-in-flight-honoured"
    assert st.get("honoured_in_flight") is True


def test_standing_go_revoked_is_refused(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store, revoked=True)
    st = rcls.evaluate_standing_go(store, "go.json", pub, now=NOW)
    assert st["status"] == "revoked"


def test_standing_go_void_record_is_refused(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store)
    rcls.record_go_void(store, "go.json", pub, ["ratchet-regression"], now=NOW)
    st = rcls.evaluate_standing_go(store, "go.json", pub, now=NOW)
    assert st["status"] == "voided" and "ratchet-regression" in st["detail"]


def test_record_go_void_is_append_only_and_once(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store)
    # no voiding trigger → nothing written
    assert rcls.record_go_void(store, "go.json", pub, ["licence-change"], now=NOW) is None
    assert store.read("registry/approvals/go.json.voided") is None
    # a voiding trigger appends the marker — once, never edited
    obj = rcls.record_go_void(store, "go.json", pub, ["new-source"], now=NOW)
    assert obj == "registry/approvals/go.json.voided"
    assert rcls.record_go_void(store, "go.json", pub, ["ratchet-regression"], now=NOW) is None
    doc = json.loads(store.read(obj))
    assert doc["schema"] == rcls.GO_VOID_SCHEMA and doc["go"] == "go.json"
    # and the go record itself is untouched
    assert json.loads(store.read("registry/approvals/go.json"))["kind"] == "standing_go"


def test_standing_go_out_of_scope_pub_is_refused(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store, publication_id="p-" + "9" * 64)
    st = rcls.evaluate_standing_go(store, "go.json", pub, now=NOW)
    assert st["status"] == "out-of-scope"


def test_standing_go_out_of_scope_commit_is_refused(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store, scope={"code_commit": "f" * 40})
    st = rcls.evaluate_standing_go(store, "go.json", pub, now=NOW, candidate_commit=COMMIT)
    assert st["status"] == "out-of-scope"


def test_standing_go_wrong_kind_is_refused(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store, kind="signed_readout")
    st = rcls.evaluate_standing_go(store, "go.json", pub, now=NOW)
    assert st["status"] == "wrong-kind"


def test_verb_classify_records_go_void_on_voiding_trigger(tmp_path: Path) -> None:
    """On --apply, a voiding trigger appends the go's .voided marker."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store)
    _delta(suite)["sources"]["added"] = ["brand_new_source"]
    notices: list[alerts.Alert] = []
    out = rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=_suite_file(tmp_path, suite),
        go="go.json",
        notice_hook=notices.append,
    )
    assert out["class"] == "class_s"
    assert out["go_voided"] == "registry/approvals/go.json.voided"
    assert out["standing_go"]["status"] == "valid"  # status BEFORE the void landed
    # a second classify now reports the go voided
    again = rcls.classify(store, pub, suites=[suite], go="go.json", now=NOW + timedelta(minutes=1))
    assert again["standing_go"]["status"] == "voided"


# --------------------------------------------------------------------------- #
# promote integration — the journal's class + the approval record gate       #
# --------------------------------------------------------------------------- #


def _promote_pub(store: rp.LocalDirStore, pub: str, **kw: Any) -> dict[str, Any]:
    kw.setdefault("api_image", "registry.local/sig-api@sha256:" + "a" * 64)
    kw.setdefault("web_image", "registry.local/sig-web@sha256:" + "b" * 64)
    kw.setdefault("project", "sig-fixture")
    kw.setdefault("region", "us-central1")
    kw.setdefault("now", NOW)
    return rc.verb_promote(store, apply_=True, publication_id=pub, **kw)


def test_class_r_promote_under_a_valid_standing_go(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store)
    notices: list[alerts.Alert] = []
    rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=_suite_file(tmp_path, suite),
        go="go.json",
        notice_hook=notices.append,
        now=NOW,
    )
    out = _promote_pub(store, pub, approval="go.json")
    assert out["applied"] is True
    latest = json.loads(store.read("registry/conf/2/latest.json"))
    assert latest["class"] == "R" and latest["publication_id"] == pub
    assert latest["approval_ref"]["kind"] == "standing_go"


def test_class_r_promote_refuses_an_expired_go(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store, expires_at="2026-10-01T00:00:00Z")  # expired before classify
    rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=_suite_file(tmp_path, suite),
        notice_hook=lambda a: None,
        now=NOW,
    )
    with pytest.raises(rp.PipelineError) as exc:
        _promote_pub(store, pub, approval="go.json")
    assert exc.value.code == "approval-refused"
    assert "expired" in str(exc.value)


def test_class_r_promote_refuses_a_voided_go(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store)
    rcls.record_go_void(store, "go.json", pub, ["new-source"], now=NOW)
    rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=_suite_file(tmp_path, suite),
        notice_hook=lambda a: None,
        now=NOW,
    )
    with pytest.raises(rp.PipelineError) as exc:
        _promote_pub(store, pub, approval="go.json")
    assert exc.value.code == "approval-refused"
    assert "void" in str(exc.value)


def test_class_r_promote_refuses_an_absent_go(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=_suite_file(tmp_path, suite),
        notice_hook=lambda a: None,
        now=NOW,
    )
    with pytest.raises(rp.PipelineError) as exc:
        _promote_pub(store, pub, approval="missing.json")
    assert exc.value.code == "approval-absent"


def test_in_flight_expired_go_promotes_once(tmp_path: Path) -> None:
    """Expired-after-classify honoured: the approval ref records it."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store, expires_at="2026-10-20T00:00:00Z")
    rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=_suite_file(tmp_path, suite),
        notice_hook=lambda a: None,
        now=NOW,
    )
    later = NOW + timedelta(days=10)
    out = _promote_pub(store, pub, approval="go.json", now=later)
    latest = json.loads(store.read("registry/conf/2/latest.json"))
    assert out["applied"] is True and latest["class"] == "R"
    assert latest["approval_ref"].get("honoured_in_flight") is True


def test_class_s_promote_needs_a_signed_readout(tmp_path: Path) -> None:
    """A standing go never authorises Class S; an agent never signs — the
    readout draft stays unsigned and promote refuses it verbatim."""
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _seed_go(store)
    _delta(suite)["sources"]["added"] = ["new_source_9"]  # → class_s
    rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=_suite_file(tmp_path, suite),
        notice_hook=lambda a: None,
        now=NOW,
    )
    assert rc.journal_class(store, pub) == "class_s"
    # the standing go is wrong-kind for Class S
    with pytest.raises(rp.PipelineError) as exc:
        _promote_pub(store, pub, approval="go.json")
    assert "signed_readout" in str(exc.value)
    # and the drafted readout itself can never be the approval — it is
    # unsigned by construction and names no signature
    draft = json.loads(store.read(f"{rcls.READOUTS_PREFIX}{pub}.json"))
    assert draft["signature"] is None


# --------------------------------------------------------------------------- #
# The Class-S readout — §7.4, verbatim wording, agent-drafted                 #
# --------------------------------------------------------------------------- #


def _class_s_record(tmp_path: Path) -> tuple[str, rp.LocalDirStore, dict[str, Any]]:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    _delta(suite)["sources"]["added"] = ["new_source_9"]
    return pub, store, _classify(store, pub, suite)


def test_readout_carries_the_required_wording_verbatim(tmp_path: Path) -> None:
    pub, store, record = _class_s_record(tmp_path)
    doc, md = rcls.draft_readout(record)
    assert doc["schema"] == rcls.READOUT_SCHEMA
    for sentence in (rcls.WORDING_MAINTAINER, rcls.WORDING_NO_HUMAN, rcls.WORDING_MEM9):
        assert sentence in md
        assert sentence in doc["required_wording"]
    assert "single maintainer, no second reviewer" in md
    assert "no human check performed" in md
    # both basis options are SIG-CONF-010's verbatim wording
    assert rcls.BASIS_REVIEWED in md and rcls.BASIS_CHECKS_ONLY in md


def test_readout_is_agent_drafted_and_unsigned(tmp_path: Path) -> None:
    pub, store, record = _class_s_record(tmp_path)
    doc, md = rcls.draft_readout(record)
    assert doc["agent_drafted"] is True
    assert doc["signature"] is None and doc["signed_at"] is None
    assert doc["basis"] is None
    assert "agent-drafted" in md
    assert "an agent never signs" in md or "never signs" in md


def test_readout_carries_diff_and_verify_summary(tmp_path: Path) -> None:
    pub, store, record = _class_s_record(tmp_path)
    doc, md = rcls.draft_readout(record)
    assert doc["publication_id"] == pub
    assert (
        doc["template_fingerprint"]
        == record["evidence"]["v14_deltas"]["template_fingerprint"]["current"]
    )
    assert doc["diff_summary"] == record["evidence"]["v14_deltas"]
    assert doc["verify_summary"] == record["evidence"]["suites"]
    assert "| check | verdict | detail |" in md


def test_verb_classify_writes_the_readout_pair_and_notice(tmp_path: Path) -> None:
    pub, store, record = _class_s_record(tmp_path)
    notices: list[alerts.Alert] = []
    out = rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=_suite_file(tmp_path, record_to_suite(store, pub, record)),
        notice_hook=notices.append,
        now=NOW,
    )
    assert out["class"] == "class_s" and out["applied"] is True
    assert out["readout"]["json"] == f"{rcls.READOUTS_PREFIX}{pub}.json"
    md = store.read(out["readout"]["md"]).decode()
    assert "single maintainer, no second reviewer" in md
    assert notices and notices[0].kind == rcls.NOTICE_KIND_S
    assert notices[0].detail["readout"]["json"].endswith(f"{pub}.json")
    # the event names the readout + notice for the promote audit trail
    ev = rc.journal_classification(store, pub)
    assert ev["class"] == "class_s" and ev["readout"]["json"]
    assert ev["notice"]["kind"] == rcls.NOTICE_KIND_S


def record_to_suite(store: rp.LocalDirStore, pub: str, record: dict[str, Any]) -> dict[str, Any]:
    """Re-emit the minimal suite doc a classification record consumed —
    the suite rows stay as the record's evidence expects (the record's own
    evidence block is the honest reconstruction surface for a re-run)."""
    deltas = record["evidence"]["v14_deltas"]
    suite = {
        "schema": rv.RESULT_SCHEMA,
        "mode": "S",
        "publication_id": pub,
        "origin": "tree:test",
        "origin_kind": "tree",
        "checks": list(rv.CHECKS_S),
        "results": [
            {
                "check": cid,
                "mode": "S",
                "status": "pass",
                "detail": "re-emitted",
                "evidence": {"deltas": deltas} if cid == "V14" else {},
                "duration": 0.0,
            }
            for cid in rv.CHECKS_S
        ],
        "counts": {"pass": len(rv.CHECKS_S), "fail": 0, "skip": 0},
        "verdict": "pass",
        "promotion_blocked": False,
        "waivers": [],
        "waivers_ignored": [],
        "uncovered": [],
    }
    return suite


# --------------------------------------------------------------------------- #
# The notice path — recorded through the landed seam, no address in a file    #
# --------------------------------------------------------------------------- #


def test_notice_records_through_the_alert_ledger(tmp_path: Path) -> None:
    pub, store, record = _class_s_record(tmp_path)
    ledger = alerts.AlertLedger(tmp_path / "alerts.jsonl")
    rcls.notify_classification(
        record,
        {"json": f"registry/readouts/{pub}.json"},
        ledger=ledger,
        notifiers=[],
    )
    rows = ledger.read()
    assert len(rows) == 1 and rows[0]["kind"] == rcls.NOTICE_KIND_S
    assert rows[0]["detail"]["publication_id"] == pub
    # the env-configured destination is env-only — nothing names an address
    assert "email" not in json.dumps(rows[0]).lower()


def test_notice_payload_scrubs_secret_values(tmp_path: Path) -> None:
    pub, store, record = _class_s_record(tmp_path)
    import os

    os.environ["SIG_ALERT_WEBHOOK_URL"] = "https://hooks.example.test/t0ken-secret"
    try:
        alert = rcls.notify_classification(
            record,
            None,
            ledger=alerts.AlertLedger(tmp_path / "alerts.jsonl"),
            notifiers=[],
        )
        assert "t0ken-secret" not in json.dumps(alert.as_json())
    finally:
        del os.environ["SIG_ALERT_WEBHOOK_URL"]


# --------------------------------------------------------------------------- #
# The template fingerprint — deterministic, stamped, compared                 #
# --------------------------------------------------------------------------- #


def test_template_fingerprint_is_deterministic() -> None:
    from exports.release_fingerprint import template_fingerprint

    assert template_fingerprint() == template_fingerprint()
    assert len(template_fingerprint()) == 64


def test_build_stamps_the_template_fingerprint(tmp_path: Path) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    rel = json.loads((work_dir / f"releases/{pub}/release.json").read_bytes())
    assert isinstance(rel.get("template_fingerprint"), str)
    assert len(rel["template_fingerprint"]) == 64
    # V14 consumed it — the emitted delta compares prev vs current
    deltas = _delta(suite)
    assert deltas["template_fingerprint"]["changed"] is False
    assert deltas["template_fingerprint"]["current"] == rel["template_fingerprint"]


# --------------------------------------------------------------------------- #
# The no-readout set — §7.3: each records its pre-authorisation id           #
# --------------------------------------------------------------------------- #


def test_rollback_still_requires_its_recorded_authority(tmp_path: Path) -> None:
    """The no-readout set is untouched: rollback/clear-latest/withdraw keep
    requiring their operator go / pre-authorisation id (never a readout)."""
    from ops import release_reversal as rr

    store = rp.LocalDirStore(tmp_path / "relroot")
    target = "p-" + "0" * 64
    # a minimal promoted-set fixture so the verb reaches the authority check:
    # conf/1 lists the target as promoted and latest.json points elsewhere
    (tmp_path / "relroot" / "registry" / "conf" / "1").mkdir(parents=True)
    (tmp_path / "relroot" / "registry" / "conf" / "1" / "promoted.map").write_text(f"{target} 1;\n")
    (tmp_path / "relroot" / "registry" / "conf" / "1" / "latest.json").write_text(
        json.dumps({"schema": "sig.latest-pointer/2", "publication_id": "p-" + "1" * 64})
    )
    (tmp_path / "relroot" / "staged" / "v" / target).mkdir(parents=True)
    (tmp_path / "relroot" / "staged" / "v" / target / "index.json").write_text("{}")
    with pytest.raises(rp.PipelineError) as exc:
        rr.verb_rollback(store, apply_=True, to=target, reason="t", go=None)
    assert exc.value.code == "go-required"


# --------------------------------------------------------------------------- #
# Verb-level S classification still fail-closed through the journal           #
# --------------------------------------------------------------------------- #


def test_classify_apply_writes_classification_event_only_when_applied(
    tmp_path: Path,
) -> None:
    work_dir, pub, store, suite = _classified_fixture(tmp_path)
    out = rp.verb_classify(
        store,
        apply_=True,
        publication_id=pub,
        results=_suite_file(tmp_path, suite),
        notice_hook=lambda a: None,
        now=NOW,
    )
    ev = rc.journal_classification(store, pub)
    assert ev is not None and ev["class"] == "class_r"
    assert ev["classification_object"] == out["classification_object"]
    assert ev["verb"] == "classified"
