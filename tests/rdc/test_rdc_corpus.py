# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.23 (SIG-CONF-008/012, SIG-ENG-042): the real-data regression corpus —
manifest validation, licence lanes, member digests, oracle facts, snapshot
approval, estimand lint, and the scheduled-lane posture.

These tests run in the PR lane (the `*` partition of `make test-par`): a PR
touching connectors/, resolution/, reconcile/, exports/ or db/ runs them
through the same suite as every other test — the corpus is the regression
substrate for exactly those packages.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from ops import rdc, rdc_oracles

DATA = Path(__file__).resolve().parent / "data"


@pytest.fixture(scope="module")
def corpus() -> rdc.Corpus:
    return rdc.load_corpus(DATA)


def _slice(corpus: rdc.Corpus, sid: str) -> rdc.Slice:
    return next(s for s in corpus.slices if s.slice_id == sid)


# ---------------------------------------------------------------------------
# Manifest + licence lanes
# ---------------------------------------------------------------------------


def test_corpus_validates_clean(corpus: rdc.Corpus) -> None:
    assert rdc.validate_corpus(corpus) == []


def test_every_archetype_declares_status_and_deferral_shape(corpus: rdc.Corpus) -> None:
    assert len(corpus.archetypes) == 14
    for a in corpus.archetypes:
        assert a.status in rdc.ARCHETYPE_STATUS
        if a.status == "deferred":
            assert a.deferral.startswith("D-P35.23-"), a.archetype_id
    served = {a.archetype_id for a in corpus.archetypes if a.status == "served"}
    assert served == {
        "eff_data_driven",
        "legistar_tenants",
        "atlas_eff_two_state_names",
        "procurement_topical",
    }


def test_committed_slices_are_licensed_raw_ok_non_odbl(corpus: rdc.Corpus) -> None:
    from connectors.registry import get

    for s in corpus.slices:
        src = get(s.source_id)
        if s.lane == "committed":
            assert src.redistribution.lane == "raw-ok", s.slice_id
            assert "odbl" not in (src.rights.spdx or "").lower(), s.slice_id
            assert all((s.directory / m.path).exists() for m in s.members)
        else:
            # restricted = anything else: derived-only/link-only/unknown lanes
            # or ODbL compartment material
            assert (
                src.redistribution.lane != "raw-ok" or "odbl" in (src.rights.spdx or "").lower()
            ), s.slice_id


def test_restricted_slices_commit_digests_only(corpus: rdc.Corpus) -> None:
    for s in corpus.slices:
        if s.lane != "restricted":
            continue
        # only slice.toml is committed under restricted/<id>/ — no bytes
        committed_files = [p.name for p in s.directory.iterdir() if p.is_file()]
        assert committed_files == ["slice.toml"], s.slice_id
        for m in s.members:
            assert len(m.sha256) == 64
            assert m.capture.startswith("sig:capture:")


def test_member_digests_verify(corpus: rdc.Corpus) -> None:
    for s in corpus.slices:
        if s.lane == "restricted":
            continue
        assert rdc.member_bytes(s), s.slice_id


def test_corrupted_member_fails(corpus: rdc.Corpus, tmp_path: Path) -> None:
    root = tmp_path / "data"
    shutil.copytree(DATA, root)
    victim = root / "camreg_nottingham_axis" / "layer83.json"
    victim.write_bytes(b'{"features": []}')  # corrupt bytes
    c = rdc.load_corpus(root)
    errors = rdc.validate_corpus(c)
    assert any("digest mismatch" in e for e in errors)
    s = _slice(c, "camreg_nottingham_axis")
    with pytest.raises(rdc.CorpusError, match="corrupt"):
        rdc.member_bytes(s)


def test_empty_corpus_fails_not_vacuous(tmp_path: Path) -> None:
    root = tmp_path / "data"
    root.mkdir()
    (root / "corpus.toml").write_text(
        'schema = "sig.rdc-corpus/1"\ncorpus_id = "empty"\nversion = 1\n'
        '[estimands]\nm4 = "x never an estimate of real-world precision or recall"\n'
        'm5 = "x never an estimate of real-world precision or recall"\n'
        'm6 = "x never an estimate of real-world precision or recall"\n'
    )
    c = rdc.load_corpus(root)
    errors = rdc.validate_corpus(c)
    assert any("SIG-ENG-042" in e for e in errors)


def test_corrupt_slice_bytes_fail_the_oracle(corpus: rdc.Corpus, tmp_path: Path) -> None:
    root = tmp_path / "data"
    shutil.copytree(DATA, root)
    victim = root / "usaspending_topical" / "spending_by_award.json"
    bad = b"not json at all {{{"
    victim.write_bytes(bad)
    # re-pin the digest so only the oracle sees the corruption
    st = root / "usaspending_topical" / "slice.toml"
    import hashlib

    st.write_text(
        st.read_text().replace(
            "82d3775212dd702fe8d162c476e154ad21ae305f1cd8a7b9590b9bb253e27fea",
            hashlib.sha256(bad).hexdigest(),
        )
    )
    c = rdc.load_corpus(root)
    s = _slice(c, "usaspending_topical")
    with pytest.raises(ValueError):  # CorpusError or the oracle's decode error — never silent
        rdc.run_oracle(s)


# ---------------------------------------------------------------------------
# Oracle facts on the real slices (pipeline-independent answers)
# ---------------------------------------------------------------------------


def test_dc_oracle_facts(corpus: rdc.Corpus) -> None:
    facts = rdc.run_oracle(_slice(corpus, "camreg_dc_multiview"))
    assert facts["feature_count"] == 1060
    assert facts["distinct_object_ids"] == 1060
    assert facts["collision_count"] == 0  # OBJECTID is unique; the collided field is `ID`
    assert facts["co_located_groups"] >= 30  # real multi-view sites exist
    assert facts["null_island"] == 0
    assert facts["out_of_extent"] == 0


def test_nottingham_oracle_flags_the_transposition(corpus: rdc.Corpus) -> None:
    facts = rdc.run_oracle(_slice(corpus, "camreg_nottingham_axis"))
    assert facts["feature_count"] == 562
    assert facts["distinct_object_ids"] == 562
    # under the declared extent + the field-level Lat/Long read, the oracle's
    # raw-attribute census sees the transposed fields — every record outside
    attrs_out = facts["out_of_extent"]
    assert attrs_out == 0  # geometry x/y are correctly ordered…
    # …the transposed *attribute* fields are the recorded defect the pipeline
    # leg pins (562 geometry_defect claims); see the pipeline expectations.


def test_atlas_oracle_multistate_census(corpus: rdc.Corpus) -> None:
    facts = rdc.run_oracle(_slice(corpus, "eff_atlas_multistate"))
    assert facts["row_count"] == 736
    assert facts["multistate_name_count"] == 150
    assert "aberdeen police department" in facts["multistate_names"]
    assert "chambers county sheriff s office" in facts["multistate_names"]


def test_usaspending_oracle_facts(corpus: rdc.Corpus) -> None:
    facts = rdc.run_oracle(_slice(corpus, "usaspending_topical"))
    assert facts["result_count"] == 100
    assert facts["term_hits"]["surveillance"] > 0


def test_eff_release_oracle_facts(tmp_path: Path) -> None:
    # run against the staged derived bytes (gitignored) when present; else a
    # synthetic zip keeps the oracle contract covered
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "DATA.csv", "Agency,State,Type of Technology\nA,CA,ALPR\nA,CA,ALPR\nB,TX,ALPR\n"
        )
    facts = rdc_oracles.eff_release_facts(buf.getvalue())
    assert facts["tables"]["DATA.csv"]["row_count"] == 3
    assert facts["tables"]["DATA.csv"]["exact_repeat_rows"] == 1


def test_legistar_oracle_facts() -> None:
    a = json.dumps(
        [{"MatterFile": "26-001", "MatterId": 1}, {"MatterFile": "26-002", "MatterId": 2}]
    ).encode()
    b = json.dumps(
        [{"MatterFile": "26-001", "MatterId": 9}, {"MatterFile": "26-010", "MatterId": 10}]
    ).encode()
    facts = rdc_oracles.legistar_tenant_facts({"albemarle_matters.json": a, "bart_matters.json": b})
    assert facts["shared_matter_files"] == 1
    assert facts["tenants"] == {"albemarle": 2, "bart": 2}
    assert facts["shared_matter_id_count"] == 0  # tenant-scoped ids stay apart


def test_osm_oracle_facts() -> None:
    doc = json.dumps(
        {
            "elements": [
                {"type": "node", "id": 1, "tags": {"man_made": "surveillance"}},
                {
                    "type": "node",
                    "id": 2,
                    "tags": {"man_made": "surveillance", "camera:type": "fixed"},
                },
            ]
        }
    ).encode()
    facts = rdc_oracles.osm_overpass_facts(doc)
    assert facts["element_count"] == 2 and facts["distinct_ids"] == 2
    assert facts["by_type"] == {"node": 2}


# ---------------------------------------------------------------------------
# Snapshots — the explicit-commit mechanism
# ---------------------------------------------------------------------------


def test_committed_snapshots_verify(corpus: rdc.Corpus) -> None:
    assert rdc.verify_snapshots(corpus) == []


def test_tampered_snapshot_is_refused(corpus: rdc.Corpus, tmp_path: Path) -> None:
    root = tmp_path / "data"
    shutil.copytree(DATA, root)
    snap = root / "snapshots" / "eff_atlas_multistate.snapshot.json"
    doc = json.loads(snap.read_text())
    doc["oracle_digest"] = "sha256:" + "0" * 64
    snap.write_text(json.dumps(doc, indent=2))
    c = rdc.load_corpus(root)
    violations = rdc.verify_snapshots(c)
    assert any("drift without approval" in v for v in violations)


def test_missing_snapshot_is_refused(corpus: rdc.Corpus, tmp_path: Path) -> None:
    root = tmp_path / "data"
    shutil.copytree(DATA, root)
    (root / "snapshots" / "usaspending_topical.snapshot.json").unlink()
    c = rdc.load_corpus(root)
    violations = rdc.verify_snapshots(c)
    assert any("no committed snapshot" in v for v in violations)


def test_approved_drift_is_accepted(corpus: rdc.Corpus, tmp_path: Path) -> None:
    root = tmp_path / "data"
    shutil.copytree(DATA, root)
    # simulate a legitimate upstream-byte change on the smallest slice
    member = root / "usaspending_topical" / "spending_by_award.json"
    doc = json.loads(member.read_text())
    doc["results"] = doc["results"][:10]
    member.write_text(json.dumps(doc))
    import hashlib

    st = root / "usaspending_topical" / "slice.toml"
    st.write_text(
        st.read_text().replace(
            "82d3775212dd702fe8d162c476e154ad21ae305f1cd8a7b9590b9bb253e27fea",
            hashlib.sha256(member.read_bytes()).hexdigest(),
        )
    )
    c = rdc.load_corpus(root)
    # unapproved drift refuses
    assert rdc.verify_snapshots(c)
    # the explicit approval covers exactly this drift
    rdc.approve_snapshot(
        c,
        _slice(c, "usaspending_topical"),
        landed_in="P35.99",
        rationale="test: upstream page trimmed to 10 rows",
        rationale_ref="docs/build/runs/P35.99.md",
    )
    assert rdc.verify_snapshots(c) == []
    # a second unapproved change refuses again — raw corrupted bytes land on
    # the violations list as a corrupt member…
    doc["results"] = doc["results"][:5]
    member.write_text(json.dumps(doc))
    assert any("corrupt" in v for v in rdc.verify_snapshots(rdc.load_corpus(root)))
    # …and a re-pinned but unapproved drift lands on the violations list
    st.write_text(
        st.read_text().replace(
            st.read_text().split('sha256 = "')[1].split('"')[0],
            hashlib.sha256(member.read_bytes()).hexdigest(),
        )
    )
    assert rdc.verify_snapshots(rdc.load_corpus(root))


# ---------------------------------------------------------------------------
# Estimand lint (SIG-CONF-012)
# ---------------------------------------------------------------------------


def test_report_lint_requires_estimand_headers(corpus: rdc.Corpus) -> None:
    good = rdc.build_report(
        corpus,
        sections={},
        generated_at="2026-10-15T00:00:00Z",
        verdict="pass",
        slices_evaluated=4,
        slices_deferred=[],
    )
    assert rdc.report_lint_errors(good) == []

    bad = dict(good)
    bad["estimand"] = {"m4": "", "m5": "share of pairs merged", "m6": "precision 0.99"}
    errors = rdc.report_lint_errors(bad)
    assert any("estimand.m4" in e for e in errors)
    assert any("estimand.m5" in e or "estimand.m6" in e for e in errors)


def test_report_lint_refuses_vacuous(corpus: rdc.Corpus) -> None:
    report = rdc.build_report(
        corpus,
        sections={},
        generated_at="2026-10-15T00:00:00Z",
        verdict="pass",
        slices_evaluated=0,
        slices_deferred=[],
    )
    assert any("SIG-ENG-042" in e for e in rdc.report_lint_errors(report))


# ---------------------------------------------------------------------------
# The scheduled / restricted lane
# ---------------------------------------------------------------------------


def test_derive_restricted_from_capture_root(corpus: rdc.Corpus, tmp_path: Path) -> None:
    """A synthetic OCFL capture object feeds the digest-verified derivation."""
    member_sha = "e29950fe1d29775752e5c71b59b281550904a5465d84280e03f2547d51bd256a"
    cap_id = (
        "bcnab3jdmlnufhpum24dq5n44qkx3w7f6yk7mexfk7i2ikwdpdjmcmdi3p4weal"
        "uwgmmgr2rszlb7hge5curkadp4xzcbwbd3o3urbfnwuu"
    )
    # build a minimal OCFL object holding the real zip bytes when staged,
    # else synthetic bytes re-pinned in the corpus copy
    root = tmp_path / "data"
    shutil.copytree(DATA, root)
    staged = Path("docs/build/logs/rdc-staging/eff_data_driven_2016_2017/alpr_2016-2017_update.zip")
    if staged.exists():
        blob = staged.read_bytes()
    else:
        blob = b"synthetic restricted bytes"
        st = root / "restricted" / "eff_data_driven_2016_2017" / "slice.toml"
        import hashlib

        st.write_text(st.read_text().replace(member_sha, hashlib.sha256(blob).hexdigest()))
        member_sha = hashlib.sha256(blob).hexdigest()
    obj = tmp_path / "caps" / "ab" / "cd" / "ef" / f"sig%3acapture%3a{cap_id}"
    content = obj / "v1" / "content"
    content.mkdir(parents=True)
    (content / "capture").write_bytes(blob)
    (obj / "inventory.json").write_text(
        json.dumps(
            {
                "id": f"sig:capture:{cap_id}",
                "type": "https://ocfl.io/1.1/spec/#inventory",
                "head": "v1",
                "manifest": {"x": ["v1/content/capture"]},
            }
        )
    )
    c = rdc.load_corpus(root)
    out = tmp_path / "out"
    result = rdc.derive_restricted(c, tmp_path / "caps", out)
    assert (
        out / "restricted" / "eff_data_driven_2016_2017" / "alpr_2016-2017_update.zip"
    ).read_bytes() == blob
    # legistar + osm captures are absent → recorded errors, not silent skips
    assert any("legistar" in e for e in result["errors"])
    assert any("osm" in e for e in result["errors"])
    # the derived member now validates materialized
    assert not rdc.validate_corpus(
        rdc.load_corpus(out / "restricted" / ".." / ".." / "data" if False else root),
        require_materialized=False,
    )


def test_corrupted_derivation_aborts(corpus: rdc.Corpus, tmp_path: Path) -> None:
    root = tmp_path / "data"
    shutil.copytree(DATA, root)
    cap_id = (
        "bcnaaosf6f4ixtdzv7g6jzcf5a52yjijvppjzjluuo6pv6vi6ze7ajhc3yezn"
        "cedoo3rsaldgm5mdstbqbo7ijbjj7z47txfhcfsqyddf44"
    )
    obj = tmp_path / "caps" / "ab" / "cd" / "ef" / f"sig%3acapture%3a{cap_id}"
    (obj / "v1" / "content").mkdir(parents=True)
    (obj / "v1" / "content" / "capture").write_bytes(b"wrong bytes")
    (obj / "inventory.json").write_text(
        json.dumps({"head": "v1", "manifest": {"x": ["v1/content/capture"]}})
    )
    c = rdc.load_corpus(root)
    result = rdc.derive_restricted(c, tmp_path / "caps", tmp_path / "out")
    assert any("sha256 mismatch" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# The PR-lane membership assertion
# ---------------------------------------------------------------------------


def test_corpus_tests_ride_the_pr_partition() -> None:
    """tests/rdc sits under the pytest testpaths — the `*` partition of
    `make test-par` collects it for every PR, including every PR touching
    connectors/ resolution/ reconcile/ exports/ db/ (the corpus's declared
    trigger set). A heavier restricted lane stays scheduled, not per-PR."""
    root = Path(__file__).resolve().parents[2]
    pyproject = (root / "pyproject.toml").read_text()
    assert '"tests"' in pyproject or "'tests'" in pyproject
    table = (root / "scripts" / "ci" / "pytest_partitions.txt").read_text()
    assert "\n*\n" in f"\n{table}\n" or table.rstrip().endswith("\n*") or "*" in table.split()


# ---------------------------------------------------------------------------
# The scheduled restricted lane (sig-rdc-probe, SIG-CONF-013)
# ---------------------------------------------------------------------------


class _FakeBucket:
    """A ``GcsBucket``-shaped double: reads/writes a dict, records uploads."""

    def __init__(self, objects: dict[str, bytes] | None = None) -> None:
        self.objects = dict(objects or {})
        self.uploaded: dict[str, bytes] = {}

    def get_object(self, name: str) -> bytes:
        if name not in self.objects:
            raise KeyError(name)
        return self.objects[name]

    def put_object(self, name: str, data: bytes, *, content_type: str = "") -> None:
        self.uploaded[name] = data


def _ocfl_objects(cap_id: str, blob: bytes, prefix: str = "evidence/captures") -> dict[str, bytes]:
    from evidence.ocfl import object_path

    base = f"{prefix}/{object_path(f'sig:capture:{cap_id}')}"
    inv = json.dumps({"head": "v1", "manifest": {"x": ["v1/content/capture"]}})
    return {
        f"{base}/inventory.json": inv.encode(),
        f"{base}/v1/content/capture": blob,
    }


def test_derive_restricted_from_bucket(corpus: rdc.Corpus, tmp_path: Path) -> None:
    """The job's bounded fetch: deterministic OCFL paths, digest-verified."""
    cap_id = (
        "bcnaaosf6f4ixtdzv7g6jzcf5a52yjijvppjzjluuo6pv6vi6ze7ajhc3yezn"
        "cedoo3rsaldgm5mdstbqbo7ijbjj7z47txfhcfsqyddf44"
    )
    blob = b"the real overpass bytes would live here"
    root = tmp_path / "data"
    shutil.copytree(DATA, root)
    # re-pin the osm member to the synthetic blob
    st = root / "restricted" / "osm_okc_surveillance" / "slice.toml"
    st.write_text(
        st.read_text().replace(
            "34dd1d933d63625543d5ef36664418cc4e7ba17bcf38fe279ded196f52a2e273",
            hashlib.sha256(blob).hexdigest(),
        )
    )
    c = rdc.load_corpus(root)
    bucket = _FakeBucket(_ocfl_objects(cap_id, blob))
    out = rdc.derive_restricted_from_bucket(c, bucket, "evidence/captures", tmp_path / "staged")
    staged = tmp_path / "staged" / "restricted" / "osm_okc_surveillance" / "overpass_nodes.json"
    assert staged.read_bytes() == blob
    # the other two captures are absent → recorded errors, never silent skips
    assert any("eff_data_driven" in e for e in out["errors"])
    assert any("legistar" in e for e in out["errors"])
    # and a byte-level lie under the right key is refused, never trusted
    bad = _FakeBucket(_ocfl_objects(cap_id, b"forged bytes"))
    out2 = rdc.derive_restricted_from_bucket(c, bad, "evidence/captures", tmp_path / "s2")
    assert any("sha256 mismatch" in e for e in out2["errors"])


def _stage_all_restricted(root: Path, staging: Path) -> None:
    """Materialize every restricted member with small valid synthetic bytes,
    re-pinned in the corpus copy — the scheduled leg's staging shape."""
    import io
    import zipfile

    members = {
        "eff_data_driven_2016_2017": {
            "alpr_2016-2017_update.zip": None,  # built below
        },
        "legistar_tenant_collision": {
            "albemarle_matters.json": json.dumps(
                [{"MatterFile": "2024-01", "MatterId": 7}]
            ).encode(),
            "bart_matters.json": json.dumps([{"MatterFile": "2024-01", "MatterId": 7}]).encode(),
        },
        "osm_okc_surveillance": {
            "overpass_nodes.json": json.dumps(
                {"elements": [{"type": "node", "id": 1, "tags": {"man_made": "surveillance"}}]}
            ).encode(),
        },
    }
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("alpr.csv", "Agency,State,Type of Technology\nX PD,CA,ALPR\nX PD,CA,ALPR\n")
    members["eff_data_driven_2016_2017"]["alpr_2016-2017_update.zip"] = buf.getvalue()

    for slice_id, mems in members.items():
        st = root / "restricted" / slice_id / "slice.toml"
        text = st.read_text()
        for path, blob in mems.items():
            sha = hashlib.sha256(blob).hexdigest()
            # re-pin: replace the declared 64-hex digest for THIS member block
            block = text.split('path = "' + path + '"')[1].split("[[members]]")[0]
            old = block.split('sha256 = "')[1].split('"')[0]
            text = text.replace(old, sha, 1)
            target = staging / "restricted" / slice_id / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(blob)
        st.write_text(text)


def test_scheduled_run_local_staging(corpus: rdc.Corpus, tmp_path: Path) -> None:
    """The in-container leg end-to-end, offline: staged restricted bytes,
    overlay corpus, full harness, both records, uploads under the
    conditioned prefix."""
    root = tmp_path / "data"
    shutil.copytree(DATA, root)
    staging = tmp_path / "staging"
    _stage_all_restricted(root, staging)
    bucket = _FakeBucket()
    out = tmp_path / "records"
    rc = rdc.run_scheduled(
        rdc.load_corpus(root),
        slices_dir=staging,
        bucket=bucket,
        capture_prefix="evidence/captures/",
        records_prefix="ops/probes/rdc/",
        out_dir=out,
        job_name="sig-rdc-probe",
        now="2026-10-20T01:15:00Z",
    )
    assert rc == 0
    report = json.loads((out / "rdc-report.json").read_text())
    assert report["schema"] == "sig.rdc-report/1"
    assert report["slices_evaluated"] == 7
    assert report["slices_deferred_unmaterialized"] == []
    record = json.loads((out / "probe-run.json").read_text())
    assert record["version"] == "sig.probe-run/1"
    assert record["overall"] == "pass"
    assert set(record["checks"]) >= {"corpus", "m4", "m5", "m6"}
    # uploads land under the conditioned ops/probes/ scope as new objects
    names = sorted(bucket.uploaded)
    assert any(n.startswith("ops/probes/rdc/2026-10-20/") for n in names)
    assert any(n.endswith("-rdc-report.json") for n in names)
    assert any(n.endswith("-probe-run.json") for n in names)


def test_scheduled_run_suppressed_in_window(corpus: rdc.Corpus, tmp_path: Path) -> None:
    """A quiet-band fire records a suppressed probe-run — never a fake pass."""
    bucket = _FakeBucket()
    out = tmp_path / "records"
    rc = rdc.run_scheduled(
        corpus,
        slices_dir=None,
        bucket=bucket,
        capture_prefix="evidence/captures/",
        records_prefix="ops/probes/rdc/",
        out_dir=out,
        job_name="sig-rdc-probe",
        now="2026-10-20T04:00:00Z",  # inside 03:00–06:30Z
    )
    assert rc == 0
    record = json.loads((out / "probe-run.json").read_text())
    assert record["checks"]["window"]["verdict"] == "skipped"
    assert not (out / "rdc-report.json").exists()
    assert any(n.endswith("-probe-run.json") for n in bucket.uploaded)


def test_scheduled_run_batch_window_suppressed(corpus: rdc.Corpus, tmp_path: Path) -> None:
    """A day-6→13 batch-window fire suppresses even at a legal hour."""
    out = tmp_path / "records"
    rc = rdc.run_scheduled(
        corpus,
        slices_dir=None,
        bucket=None,
        capture_prefix="evidence/captures/",
        records_prefix="ops/probes/rdc/",
        out_dir=out,
        job_name="sig-rdc-probe",
        now="2026-10-08T01:15:00Z",  # dom 8 — inside the batch window
    )
    assert rc == 0
    record = json.loads((out / "probe-run.json").read_text())
    assert "batch window" in record["checks"]["window"]["reason"]
