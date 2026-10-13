# SPDX-License-Identifier: Apache-2.0
"""Offline unit tests for the P32.23a release-candidate pipeline (SIG-TRUST-010,
ADR-142).

These cover the DB-free seams: the pinned candidate identity, the shadow-gate
invariant, the deferred-evaluation disclosure rules (no optimistic count, no
prior-preview figure), the publication-pointer guard, the rollback packet, and
the live return-pass. The full end-to-end over a real spine is Docker-gated in
``tests/db/test_release_candidate.py``.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ops import release_candidate as rc

P32_22 = (
    Path(__file__).resolve().parents[2] / "docs" / "build" / "reports" / "p32.22-bounded-recovery"
)
SNAPSHOT_PATH = P32_22 / "REPAIRED_SNAPSHOT.json"
SHADOW_PATH = P32_22 / "PROVISIONAL_VS_SHADOW.json"


def _snapshot() -> dict:
    return json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))


def _shadow() -> dict:
    return json.loads(SHADOW_PATH.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# The pinned identity — deferred evaluation under the provisional policy.
# ---------------------------------------------------------------------------


def test_identity_pins_ruleset_snapshot_and_deferred_evaluation() -> None:
    identity = rc.candidate_identity(
        snapshot=_snapshot(), shadow_report=_shadow(), code_commit="deadbeef"
    )
    assert identity["identity_version"] == rc.IDENTITY_VERSION
    assert identity["ruleset_version"] == rc.PROVISIONAL_RULESET
    snap = identity["frozen_snapshot"]
    assert snap["snapshot_digest"] == _snapshot()["snapshot_digest"]
    assert snap["status"] == "frozen_unpublished"
    ev = identity["evaluation"]
    assert ev["status"] == "deferred"
    assert ev["decision"] is None and ev["decision_ref"] is None
    assert ev["basis"] == "provisional-policy"
    assert "HUMAN-H4" in ev["deferred_by"] and "a33cd6ec" in ev["deferred_by"]
    assert ev["policy_id"] == "eval-confidence/1"
    assert ev["mode"] == "shadow"
    assert ev["applied"] == []
    assert ev["p32_10_confidence_policy"] != "activated"
    assert identity["published"] is False
    # determinism: same inputs → same identity digest
    again = rc.candidate_identity(
        snapshot=_snapshot(), shadow_report=_shadow(), code_commit="deadbeef"
    )
    assert again["identity_digest"] == identity["identity_digest"]


def test_identity_digest_changes_with_any_input() -> None:
    a = rc.candidate_identity(snapshot=_snapshot(), shadow_report=_shadow())
    snap = _snapshot()
    snap["snapshot_digest"] = "sha256:changed"
    b = rc.candidate_identity(snapshot=snap, shadow_report=_shadow())
    assert a["identity_digest"] != b["identity_digest"]


def test_identity_refuses_an_activated_shadow_gate() -> None:
    shadow = _shadow()
    shadow["shadow_evaluator"]["mode"] = "active"
    with pytest.raises(rc.CandidateError) as exc:
        rc.candidate_identity(snapshot=_snapshot(), shadow_report=shadow)
    assert exc.value.code == "activated_policy"


def test_identity_refuses_a_non_empty_applied_set() -> None:
    shadow = _shadow()
    shadow["shadow_evaluator"]["applied"] = ["camera-site-auto-write"]
    with pytest.raises(rc.CandidateError) as exc:
        rc.candidate_identity(snapshot=_snapshot(), shadow_report=shadow)
    assert exc.value.code == "activated_policy"


def test_snapshot_without_digest_is_refused() -> None:
    with pytest.raises(rc.CandidateError) as exc:
        rc.candidate_identity(snapshot={"snapshot_version": "sig.repaired-snapshot/1"})
    assert exc.value.code == "bad_snapshot"


# ---------------------------------------------------------------------------
# Changed-input verification — the reassessment stop.
# ---------------------------------------------------------------------------


def test_frame_check_refuses_a_snapshot_with_no_population() -> None:
    with pytest.raises(rc.CandidateError) as exc:
        rc.verify_population_frame(None, {"population_frame": {}})
    assert exc.value.code == "bad_snapshot"


def test_frame_check_refuses_missing_claims_with_fake_conn() -> None:
    """A conn-shaped fake that returns no rows — the recorded population is
    absent from the spine, which must stop the build as changed_input."""

    class _Cur:
        description = ()

        def fetchall(self):
            return []

        def fetchone(self):
            # every watermark query takes positional fields; a wide-enough
            # zero row satisfies them all
            return [0, None, 0, 0, 0, 0]

    class _Conn:
        def execute(self, *_a, **_kw):
            return _Cur()

        def cursor(self):
            return _Cur()

    snap = _snapshot()
    with pytest.raises(rc.CandidateError) as exc:
        rc.verify_population_frame(_Conn(), snap)
    assert exc.value.code == "changed_input"
    assert "absent" in str(exc.value)
    assert len(exc.value.detail["claims_missing"]) == 16


# ---------------------------------------------------------------------------
# The deferred-evaluation disclosure: only THIS build's coverage may quote a
# resolved-sites figure, and never an unqualified population total.
# ---------------------------------------------------------------------------


def _export_dir(tmp_path: Path, coverage: dict | None = None) -> Path:
    d = tmp_path / "export"
    (d / "web").mkdir(parents=True)
    (d / "exclusions.json").write_text(
        json.dumps(
            {
                "schema": "p27.4/exclusions/1.0.0",
                "refused": [{"compartment": "ud", "source": "muckrock", "rows": 2}],
                "totals": {"refused_slices": 1, "refused_rows": 2},
                "generated_at": "2026-10-19T00:00:00Z",  # future-ok: synthetic: fixture
                "note": "test",
            }
        ),
        encoding="utf-8",
    )
    if coverage is not None:
        (d / "web" / "coverage.json").write_text(json.dumps(coverage), encoding="utf-8")
    return d


def test_resolved_sites_figure_reads_only_this_build(tmp_path: Path) -> None:
    cov = {
        "metrics": [
            {
                "id": "resolved_sites",
                "value": "5 resolved sites (from 7 observation-level records)",
                "denominator": "7 observation-level sites",
                "is_population_total": False,
            }
        ]
    }
    d = _export_dir(tmp_path, cov)
    fig = rc.resolved_sites_figure(d)
    assert fig is not None
    assert fig["value"].startswith("5 resolved sites")
    assert fig["denominator"] == "7 observation-level sites"
    assert fig["provisional"] is True
    assert fig["source"].endswith("coverage.json only")


def test_resolved_sites_figure_is_none_without_the_metric(tmp_path: Path) -> None:
    d = _export_dir(tmp_path, {"metrics": [{"id": "records", "value": "3"}]})
    assert rc.resolved_sites_figure(d) is None
    d2 = _export_dir(tmp_path / "b", None)
    assert rc.resolved_sites_figure(d2) is None


def test_resolved_sites_figure_refuses_a_population_total(tmp_path: Path) -> None:
    """The optimistic-count failure mode: an unqualified resolved total is the
    previously-optimistic number the deferred evaluation must NOT reuse."""
    cov = {
        "metrics": [
            {
                "id": "resolved_sites",
                "value": "223,901 resolved sites",
                "is_population_total": True,
            }
        ]
    }
    d = _export_dir(tmp_path, cov)
    with pytest.raises(rc.CandidateError) as exc:
        rc.resolved_sites_figure(d)
    assert exc.value.code == "optimistic_count"


def test_disclosure_is_provisional_and_quotes_no_prior_count(tmp_path: Path) -> None:
    identity = rc.candidate_identity(snapshot=_snapshot(), shadow_report=_shadow())
    apply_report = {
        "report_version": "recovery-apply-report/1",
        "counts": {"applied": 4, "skipped": 0, "failed": 0},
        "results": [
            {
                "action_digest": "d1",
                "outcome": "applied",
                "disposition_id": "disp-1",
            }
        ],
        "rerun": {"plus_zero": True},
    }
    materialization = {"plus_zero": True}
    d = _export_dir(tmp_path, {"metrics": []})
    disclosure = rc.build_disclosure(
        identity=identity,
        export_dir=d,
        apply_report=apply_report,
        materialization=materialization,
        build_report={"records": 0},
    )
    assert disclosure["disclosure_version"] == rc.DISCLOSURE_VERSION
    assert disclosure["status"] == "provisional_review_only"
    assert disclosure["published"] is False
    assert disclosure["prior_preview_counts_reused"] is False
    assert disclosure["resolved_sites"] is None
    ev = disclosure["evaluation"]
    assert ev["status"] == "deferred" and ev["applied"] == []
    assert ev["p32_10_confidence_policy_activated"] is False
    su = disclosure["suppression_disclosure"]
    assert su["dispositions_recorded"] == 1
    assert su["export_refused_totals"]["refused_slices"] == 1
    # the deferral is disclosed verbatim, not paraphrased away
    assert "no final evaluation decision" in disclosure["evaluation_disclosure"].lower()
    assert "PROVISIONAL" in disclosure["evaluation_disclosure"]


# ---------------------------------------------------------------------------
# The publication pointer — read-only, drift is a hard failure.
# ---------------------------------------------------------------------------


def test_read_publication_pointer(tmp_path: Path) -> None:
    assert rc.read_publication_pointer(None) is None
    assert rc.read_publication_pointer(tmp_path) is None
    latest = {"schema": "sig.publication-pointer/1", "publication_id": "sig-pub-x"}
    (tmp_path / "latest.json").write_text(json.dumps(latest), encoding="utf-8")
    assert rc.read_publication_pointer(tmp_path) == latest


def test_read_publication_pointer_refuses_corrupt(tmp_path: Path) -> None:
    (tmp_path / "latest.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(rc.CandidateError):
        rc.read_publication_pointer(tmp_path)


def _fake_build_release_moves_pointer(tmp_path: Path):
    """A build_release stand-in that flips latest.json — the mutation the
    candidate must detect and refuse."""

    def _fake(export_dir, release_dir, *, renderer_revision, page_size=1000):
        (tmp_path / "latest.json").write_text(
            json.dumps({"publication_id": "sig-pub-mutated"}), encoding="utf-8"
        )
        return SimpleNamespace(
            publication_id="sig-pub-fake",
            descriptor={"schema": "sig.publication-descriptor/1"},
            manifest_sha256="x" * 64,
            out_dir=Path(release_dir),
            report={},
        )

    return _fake


def test_staging_refuses_when_the_pointer_moves(tmp_path: Path, monkeypatch) -> None:
    import exports.release as rel

    monkeypatch.setattr(rel, "build_release", _fake_build_release_moves_pointer(tmp_path))
    monkeypatch.setattr(rel, "validate_release", lambda _d: SimpleNamespace(state="complete"))
    with pytest.raises(rc.CandidateError) as exc:
        rc.stage_candidate_release(
            tmp_path / "export",
            tmp_path / "rel",
            renderer_revision="x",
            registry_dir=tmp_path,
        )
    assert exc.value.code == "pointer_mutation"


def test_staging_records_pointer_unchanged(tmp_path: Path, monkeypatch) -> None:
    import exports.release as rel

    latest = {"schema": "sig.publication-pointer/1", "publication_id": "sig-pub-prior"}
    (tmp_path / "latest.json").write_text(json.dumps(latest), encoding="utf-8")

    def _no_touch(export_dir, release_dir, *, renderer_revision, page_size=1000):
        return SimpleNamespace(
            publication_id="sig-pub-cand",
            descriptor={"schema": "sig.publication-descriptor/1"},
            manifest_sha256="y" * 64,
            out_dir=Path(release_dir),
            report={},
        )

    monkeypatch.setattr(rel, "build_release", _no_touch)
    monkeypatch.setattr(rel, "validate_release", lambda _d: SimpleNamespace(state="complete"))
    staged = rc.stage_candidate_release(
        tmp_path / "export",
        tmp_path / "rel",
        renderer_revision="x",
        registry_dir=tmp_path,
    )
    assert staged["activated"] is False
    assert staged["pointer_unchanged"] is True
    assert staged["pointer_before"] == latest == staged["pointer_after"]


# ---------------------------------------------------------------------------
# The rollback packet + return-pass + manifest roll-up.
# ---------------------------------------------------------------------------


def _staged(publication_id: str = "sig-pub-abc") -> dict:
    build = SimpleNamespace(
        publication_id=publication_id,
        descriptor={
            "schema": "sig.publication-descriptor/1",
            "data_release_id": "sig-2026-10-19-12345678",  # future-ok: synthetic: fixture
            "ruleset_version": rc.PROVISIONAL_RULESET,
        },
        manifest_sha256="m" * 64,
        out_dir=Path("/tmp/rel"),
        report={"records": 3, "compartments": [{"compartment": "portal"}]},
    )
    return {
        "build": build,
        "validation": SimpleNamespace(state="complete"),
        "pointer_before": None,
        "pointer_after": None,
        "pointer_unchanged": True,
        "activated": False,
    }


def test_rollback_packet_records_pointer_reversal_without_mutation() -> None:
    identity = rc.candidate_identity(snapshot=_snapshot(), shadow_report=_shadow())
    pkt = rc.build_rollback_packet(
        identity=identity,
        publication_id="sig-pub-abc",
        release_manifest_sha256="m" * 64,
        descriptor_sha256="d" * 64,
        disclosure_digest="s" * 64,
        pointer_before=None,
        materialization={"plus_zero": True},
    )
    assert pkt["rollback_version"] == rc.ROLLBACK_VERSION
    assert pkt["status"] == "prepared_not_needed"
    assert pkt["candidate"]["published"] is False
    assert pkt["pointer_unchanged"] is True
    assert "never deleted" in pkt["reversal_plan"]["mechanism"] or "untouched" in json.dumps(
        pkt["reversal_plan"]
    )
    # no prior pointer → reversal removes the pointer entirely
    assert "removes" in pkt["reversal_plan"]["if_no_prior_pointer"]


def test_rollback_packet_names_the_prior_pointer_when_one_exists() -> None:
    identity = rc.candidate_identity(snapshot=_snapshot(), shadow_report=_shadow())
    prior = {"publication_id": "sig-pub-prior", "manifest_sha256": "p" * 64}
    pkt = rc.build_rollback_packet(
        identity=identity,
        publication_id="sig-pub-abc",
        release_manifest_sha256="m" * 64,
        descriptor_sha256="d" * 64,
        disclosure_digest="s" * 64,
        pointer_before=prior,
        materialization={"plus_zero": True},
    )
    assert "sig-pub-prior" in pkt["reversal_plan"]["if_no_prior_pointer"]


def test_return_pass_keeps_the_live_stage_open() -> None:
    pkt = rc.build_candidate_return_pass(identity_digest="i" * 64, snapshot_digest="s" * 64)
    assert pkt["status"] == "prepared_not_executed"
    assert any("D-R10-LIVE-1" in d for d in pkt["prerequisite_open_deferrals"])
    assert any("release-candidate" in c["command"] for c in pkt["commands"])
    assert any("unpublished" in r or "stays OPEN" in r for r in pkt["explicit_reservations"])


def test_manifest_rolls_up_one_consistent_identity(tmp_path: Path) -> None:
    identity = rc.candidate_identity(
        snapshot=_snapshot(), shadow_report=_shadow(), code_commit="deadbeef"
    )
    staged = _staged()
    staged["export_manifest_sha256"] = "e" * 64
    disclosure = rc.build_disclosure(
        identity=identity, export_dir=_export_dir(tmp_path, {"metrics": []})
    )
    rollback = rc.build_rollback_packet(
        identity=identity,
        publication_id="sig-pub-abc",
        release_manifest_sha256="m" * 64,
        descriptor_sha256="d" * 64,
        disclosure_digest="s" * 64,
        pointer_before=None,
        materialization={"plus_zero": True},
    )
    ret = rc.build_candidate_return_pass(
        identity_digest=identity["identity_digest"],
        snapshot_digest=identity["frozen_snapshot"]["snapshot_digest"],
    )
    manifest = rc.build_candidate_manifest(
        identity=identity,
        snapshot=_snapshot(),
        frame_check={"population_digest_matches": True},
        materialization={"plus_zero": True, "dependency_order": ["resolution"]},
        staged=staged,
        disclosure=disclosure,
        rollback=rollback,
        return_pass=ret,
        dossier_packet_digests={"0": "p" * 64},
        apply_report={"report_version": "recovery-apply-report/1"},
        plan_digest="sha256:plan",
        audit_digest="sha256:audit",
    )
    cand = manifest["candidate"]
    assert cand["identity_digest"] == identity["identity_digest"]
    assert cand["evaluation_status"] == "deferred"
    assert cand["published"] is False
    # cross-artifact agreement: the descriptor's ruleset IS the identity's
    assert manifest["release"]["descriptor"]["ruleset_version"] == cand["ruleset_version"]
    assert manifest["release"]["activated"] is False
    assert manifest["release"]["unpublished_by_construction"] is True
    assert manifest["publication_pointer"]["unchanged"] is True
    # every deferral row has a disposition — nothing silently left dangling
    ids = {d["id"] for d in manifest["deferral_dispositions"]}
    assert {"D-R10-HUMAN-1", "D-R6.1-EVAL", "D-R10-LIVE-1", "D-R10-PUBLISH-1"} <= ids


def test_write_candidate_packet_emits_all_artifacts(tmp_path: Path) -> None:
    identity = rc.candidate_identity(snapshot=_snapshot(), shadow_report=_shadow())
    staged = _staged()
    disclosure = rc.build_disclosure(
        identity=identity, export_dir=_export_dir(tmp_path, {"metrics": []})
    )
    rollback = rc.build_rollback_packet(
        identity=identity,
        publication_id="p",
        release_manifest_sha256="m",
        descriptor_sha256="d",
        disclosure_digest="s",
        pointer_before=None,
        materialization=None,
    )
    ret = rc.build_candidate_return_pass(identity_digest="i", snapshot_digest="s")
    manifest = rc.build_candidate_manifest(
        identity=identity,
        snapshot=_snapshot(),
        frame_check={},
        materialization={},
        staged=staged,
        disclosure=disclosure,
        rollback=rollback,
        return_pass=ret,
    )
    rc.write_candidate_packet(
        tmp_path / "packet",
        manifest=manifest,
        disclosure=disclosure,
        rollback=rollback,
        materialization={},
        return_pass=ret,
    )
    for name in (
        "CANDIDATE_MANIFEST.json",
        "DISCLOSURE.json",
        "ROLLBACK_PACKET.json",
        "MATERIALIZATION.json",
        "LIVE_RETURN_PASS.json",
        "CANDIDATE_MANIFEST.md",
        "DISCLOSURE.md",
        "ROLLBACK_PACKET.md",
    ):
        assert (tmp_path / "packet" / name).exists(), name
    # the markdown renders the deferral, not just the happy path
    md = (tmp_path / "packet" / "CANDIDATE_MANIFEST.md").read_text(encoding="utf-8")
    assert "Unpublished" in md
    assert "no final" in md
    assert "provisional" in md.lower()


# ---------------------------------------------------------------------------
# The CLI verb is wired and refuses cleanly.
# ---------------------------------------------------------------------------


def test_cli_requires_snapshot(tmp_path: Path) -> None:
    from ops.cli import main

    with pytest.raises(SystemExit):  # argparse: --snapshot is required
        main(["release-candidate", "--out", str(tmp_path)])


def test_cli_refuses_cleanly_on_changed_input(tmp_path: Path, monkeypatch) -> None:
    """The CLI surfaces a CandidateError as exit 3 with the refusal code —
    never a traceback on the reassessment stop."""
    from ops import cli

    snap = tmp_path / "snapshot.json"
    snap.write_text(json.dumps(_snapshot()), encoding="utf-8")

    class _Conn:
        def rollback(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(
        cli,
        "_cloudsql_dsn_from_parts",
        lambda: "postgresql://example/never-used",
    )

    def _boom(*_a: object, **_kw: object) -> None:
        raise rc.CandidateError("changed_input", "population drifted")

    import psycopg

    monkeypatch.setattr(psycopg, "connect", lambda *_a, **_kw: _Conn())
    monkeypatch.setattr(rc, "run_candidate", _boom)
    assert cli.main(["release-candidate", "--snapshot", str(snap), "--out", str(tmp_path)]) == 3
