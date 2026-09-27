# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P32.13 / ADR-132 (SIG-FIND-001/002) — immutable release namespaces and
specific public record routes: two-stage identity, deterministic build,
atomic validation/activation, rollback, the withdrawal barrier before origin,
legacy-selector resolution, and the measured-build seam."""

from __future__ import annotations

import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest
from exports.manifest import canonical_json
from exports.release import (
    INTEGRITY_SCHEMA,
    PUBLICATION_RE,
    ReleaseError,
    ReleaseRegistry,
    activate,
    apply_withdrawals,
    build_release,
    measure_build,
    resolve_selector,
    rollback,
    route_access,
    validate_release,
)
from policy.eligibility import (
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)

REVISION = "deadbeef" * 8  # 64-char test revision


def _rights(source: str, spdx: str) -> dict:
    return {
        "attribution": f"© {source}",
        "attribution_required": True,
        "license": spdx,
        "share_alike": spdx.startswith("ODbL"),
        "source_id": source,
        "terms_url": "https://example/terms",
        "upstream_license": None,
    }


def _site_row(i: int, source: str, spdx: str, juris: str = "OK") -> dict:
    return {
        "_rights": _rights(source, spdx),
        "claim_ids": [f"claim-{source}-{i}-a", f"claim-{source}-{i}-b"],
        "entity_id": f"ent-{source}-{i}",
        "entity_type": "deployment",
        "geometry": {"coordinates": [-97.5 + i * 0.01, 35.46], "type": "Point"},
        "jurisdiction": juris,
        "label": f"Site {source} {i}",
        "n_observation_claims": 2,
        "n_sources": 1,
        "point_status": "resolved",
        "precision": "full_precision",
        "rights_id": "r1",
        "source_id": source,
        "spdx": spdx,
        "tier": 0,
    }


def _claim_row(cid: str, ent: str, source: str, artifact: str | None) -> dict:
    return {
        "claim_id": cid,
        "entity_id": ent,
        "predicate_id": "camera_latitude",
        "observed_at": "2026-05-01",
        "source_id": source,
        "evidence": (
            [{"capture_id": f"cap-{cid}", "artifact_id": artifact, "role": "establishes"}]
            if artifact
            else []
        ),
    }


def _write_export(root: Path, *, n_records: int = 3, two_compartments: bool = True) -> Path:
    """A minimal but real-shaped export directory: two licence compartments,
    record_claims, evidence + dossiers + manifest."""
    comp_a = "sig_graph"
    comp_b = "osm_physical" if two_compartments else "sig_graph"
    lic = {comp_a: "CC-BY-4.0", "osm_physical": "ODbL-1.0"}
    src = {comp_a: "src_a", "osm_physical": "src_osm"}

    (root / comp_a).mkdir(parents=True, exist_ok=True)
    (root / "web").mkdir(parents=True, exist_ok=True)
    if two_compartments:
        (root / comp_b).mkdir(parents=True, exist_ok=True)

    artifacts = []
    for comp in {comp_a, comp_b} if two_compartments else {comp_a}:
        s, spdx, lic_id = src[comp], lic[comp], lic[comp]
        rows = [_site_row(i, s, spdx) for i in range(n_records)]
        (root / comp / "sites.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
        )
        claims = [
            _claim_row(f"claim-{s}-{i}-a", f"ent-{s}-{i}", s, f"art-{comp}")
            for i in range(n_records)
        ] + [_claim_row(f"claim-{s}-{i}-b", f"ent-{s}-{i}", s, None) for i in range(n_records)]
        (root / comp / "record_claims.jsonl").write_text(
            "".join(json.dumps(r) + "\n" for r in claims), encoding="utf-8"
        )
        for p in ("sites.jsonl", "record_claims.jsonl"):
            artifacts.append(
                {
                    "path": f"{comp}/{p}",
                    "compartment": comp,
                    "license": lic_id,
                    "sha256": "x",
                    "byte_size": 1,
                    "media_type": "application/json",
                }
            )

    evidence = {
        "artifacts": [
            {
                "artifact_id": "art-sig_graph",
                "artifact_type": "registry_table",
                "as_of": "2026-09-27",
                "capture_status": "captured",
                "currency": "",
                "directness": "primary",
                "permalink": "sig:connector:test:sig",
                "source": "src_a",
                "subject_id": "",
                "title": "sig registry page",
                "touches_open_contradiction": False,
                "answers_open_task": False,
            },
            *(
                [
                    {
                        "artifact_id": "art-osm_physical",
                        "artifact_type": "dump",
                        "as_of": "2026-09-27",
                        "capture_status": "captured",
                        "currency": "",
                        "directness": "primary",
                        "permalink": "sig:connector:test:osm",
                        "source": "src_osm",
                        "subject_id": "",
                        "title": "osm dump",
                        "touches_open_contradiction": False,
                        "answers_open_task": False,
                    }
                ]
                if two_compartments
                else []
            ),
        ],
        "claim_views": [],
    }
    (root / "web" / "evidence.json").write_text(json.dumps(evidence), encoding="utf-8")
    (root / "web" / "dossiers.json").write_text(
        json.dumps(
            [
                {
                    "asOf": {
                        "as_of_world": "2026-09-27",
                        "as_of_belief": "2026-09-27",
                        "belief_pinned": False,
                    },
                    "jurisdiction": "OK",
                    "rulesetVersion": "p27.3/1.0.0",
                    "sections": [
                        {"section_id": "at_a_glance"},
                        {
                            "rows": [{"label": "Sites", "value": "N"}],
                            "section_id": "what_is_deployed",
                        },
                    ],
                    "gaps": [{"kind": "NOT_RESEARCHED", "label": "Data-sharing partners"}],
                }
            ]
        ),
        encoding="utf-8",
    )
    manifest = {
        "artifacts": artifacts,
        "concept_id": "c1",
        "content_key": "k1",
        "release_id": "sig-2026-09-27-test",
        "reproducibility_inputs": {
            "as_of_belief": "2026-09-27",
            "as_of_snapshot": "2026-09-27",
            "resolver_version": "0.0.0",
            "ruleset_version": "p27.3/1.0.0",
        },
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def _build(tmp_path: Path, export: Path, name: str = "rel"):
    return build_release(export, tmp_path / name, renderer_revision=REVISION)


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        p.relative_to(root).as_posix(): p.read_bytes()
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _disposition(kind: TargetKind, tid: str, disp: Disposition, seq: int = 0):
    return new_disposition(
        target_kind=kind,
        target_id=tid,
        disposition=disp,
        reason_category=ReasonCategory.SAFETY_WITHDRAWAL,
        authority="test-authority",
        decided_at=datetime(2026, 9, 27, tzinfo=UTC),
        seq=seq,
    )


# --------------------------------------------------------------------------- #
# AC1 — identical inputs ⇒ identical namespace AND bytes                      #
# --------------------------------------------------------------------------- #


def test_publication_id_shape(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    assert PUBLICATION_RE.match(build.publication_id)


def test_build_is_deterministic(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    a = build_release(export, tmp_path / "a", renderer_revision=REVISION)
    b = build_release(export, tmp_path / "b", renderer_revision=REVISION)
    assert a.publication_id == b.publication_id
    assert a.manifest_sha256 == b.manifest_sha256
    assert _tree_bytes(tmp_path / "a") == _tree_bytes(tmp_path / "b")


def test_descriptor_inputs_change_publication_id(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    base = _build(tmp_path, export, name="base")
    # renderer change → new namespace
    alt = build_release(export, tmp_path / "alt", renderer_revision="cafe" * 16)
    assert alt.publication_id != base.publication_id
    # projection input change (a site label) → new namespace
    rows = list((export / "sig_graph" / "sites.jsonl").open())
    row = json.loads(rows[0])
    row["label"] = "renamed"
    rows[0] = json.dumps(row) + "\n"
    (export / "sig_graph" / "sites.jsonl").write_text("".join(rows))
    changed = build_release(export, tmp_path / "changed", renderer_revision=REVISION)
    assert changed.publication_id != base.publication_id
    # policy/temporal input change → new namespace
    m = json.loads((export / "manifest.json").read_text())
    m["reproducibility_inputs"]["as_of_belief"] = "2026-09-26"
    (export / "manifest.json").write_text(json.dumps(m))
    cut = build_release(export, tmp_path / "cut", renderer_revision=REVISION)
    assert cut.publication_id != base.publication_id


# --------------------------------------------------------------------------- #
# AC2/AC3 — same namespace different bytes refused; acyclic digest            #
# --------------------------------------------------------------------------- #


def test_integrity_manifest_is_external_and_acyclic(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    integrity = json.loads(
        (build.out_dir / f"releases/{build.publication_id}/integrity_manifest.json").read_text()
    )
    assert integrity["schema"] == INTEGRITY_SCHEMA
    assert integrity["publication_id"] == build.publication_id
    # the digest never appears inside a covered artifact (the acyclic rule)
    covered = {a["path"] for a in integrity["artifacts"]}
    assert f"releases/{build.publication_id}/integrity_manifest.json" not in covered
    assert f"releases/{build.publication_id}/catalog_entry.json" not in covered
    digest_text = build.manifest_sha256.encode()
    for a in integrity["artifacts"]:
        data = (build.out_dir / a["path"]).read_bytes()
        assert digest_text not in data, f"final digest embedded in {a['path']}"


def test_reactivation_with_different_bytes_refused(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    registry = tmp_path / "registry"
    activate(registry, build.out_dir)

    # A second directory with the SAME namespace but different final bytes:
    # rebuild identical inputs, then rewrite one artifact + recompute the
    # integrity manifest so validation passes — activation must still refuse.
    tampered = tmp_path / "tampered"
    shutil.copytree(build.out_dir, tampered)
    pub = build.publication_id
    rec = tampered / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0.json"
    doc = json.loads(rec.read_text())
    doc["label"]["text"] = "tampered label"
    rec.write_bytes(canonical_json(doc))
    im_path = tampered / f"releases/{pub}/integrity_manifest.json"
    integrity = json.loads(im_path.read_text())
    import hashlib

    for a in integrity["artifacts"]:
        if a["path"] == f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0.json":
            data = rec.read_bytes()
            a["sha256"] = hashlib.sha256(data).hexdigest()
            a["byte_size"] = len(data)
    im_path.write_bytes(canonical_json(integrity))
    ce_path = tampered / f"releases/{pub}/catalog_entry.json"
    ce = json.loads(ce_path.read_text())
    ce["manifest_sha256"] = hashlib.sha256(im_path.read_bytes()).hexdigest()
    ce_path.write_bytes(canonical_json(ce))

    assert validate_release(tampered).state == "complete"
    with pytest.raises(ReleaseError, match="different bytes under the same namespace"):
        activate(registry, tampered)


def test_reactivation_with_identical_bytes_is_idempotent(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    registry = tmp_path / "registry"
    first = activate(registry, build.out_dir)
    second = activate(registry, build.out_dir)
    assert first["manifest_sha256"] == second["manifest_sha256"]
    cat = ReleaseRegistry(registry).catalog()
    assert len(cat["publications"]) == 1


# --------------------------------------------------------------------------- #
# AC4 — a cited record beyond the old 500-slice resolves exact content        #
# --------------------------------------------------------------------------- #


def test_record_beyond_500_slice_resolves(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export", n_records=1200, two_compartments=False)
    build = _build(tmp_path, export)
    pub = build.publication_id
    # record #1000 — far beyond the old 500-row cap — resolves to exact bytes
    eid = "ent-src_a-999"
    rec_json = build.out_dir / f"r/{pub}/c/sig_graph/entity/deployment/{eid}.json"
    rec_html = build.out_dir / f"r/{pub}/c/sig_graph/entity/deployment/{eid}/index.html"
    assert rec_json.exists() and rec_html.exists()
    doc = json.loads(rec_json.read_text())
    assert doc["entity_id"] == eid
    assert doc["publication_id"] == pub
    assert doc["record_key"] == f"sig_graph:deployment:{eid}"
    html = rec_html.read_text()
    assert "Site src_a 999" in html and "<script" not in html
    # offline/no-JS completeness: every record route exists in the tree
    index = list((build.out_dir / f"r/{pub}/c/sig_graph").glob("entity/deployment/*.json"))
    assert len(index) == 1200
    # and a rebuild resolves the SAME bytes
    other = build_release(export, tmp_path / "again", renderer_revision=REVISION)
    assert (
        other.out_dir / rec_json.relative_to(build.out_dir)
    ).read_bytes() == rec_json.read_bytes()


def test_record_states_missing_label_and_point_honestly(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export", two_compartments=False)
    row = json.loads((export / "sig_graph" / "sites.jsonl").read_text().splitlines()[0])
    row["label"] = None
    row["geometry"] = None
    row["point_status"] = "unresolved"
    lines = (export / "sig_graph" / "sites.jsonl").read_text().splitlines()
    lines[0] = json.dumps(row)
    (export / "sig_graph" / "sites.jsonl").write_text("\n".join(lines) + "\n")
    build = _build(tmp_path, export)
    pub = build.publication_id
    rec = build.out_dir / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0.json"
    doc = json.loads(rec.read_text())
    assert doc["label"]["basis"] == "unlabelled"
    assert doc["location"]["kind"] == "unreported"
    html = (
        build.out_dir / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/index.html"
    ).read_text()
    assert "not reported" in html or "Unnamed" in html


# --------------------------------------------------------------------------- #
# AC5 — invalid/unmatched legacy selectors never masquerade                   #
# --------------------------------------------------------------------------- #


def _activated_registry(tmp_path: Path) -> tuple[Path, str]:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    registry = tmp_path / "registry"
    activate(registry, build.out_dir)
    return registry, build.publication_id


def test_resolve_selector_variants(tmp_path: Path) -> None:
    registry, pub = _activated_registry(tmp_path)
    # exact triple → redirect to the real release
    out = resolve_selector(
        registry,
        as_of_world="2026-09-27",
        as_of_belief="2026-09-27",
        ruleset="p27.3/1.0.0",
    )
    assert out["status"] == "redirect" and out["publication_id"] == pub
    # an ISO instant normalises to the same date
    out2 = resolve_selector(
        registry, as_of_world="2026-09-27T15:22:10Z", as_of_belief=None, ruleset=None
    )
    assert out2["status"] == "redirect"
    # record path maps into the release namespace
    out3 = resolve_selector(
        registry,
        as_of_world="2026-09-27",
        as_of_belief=None,
        ruleset=None,
        path="/entity/deployment/ent-src_a-0/",
    )
    assert out3["status"] == "redirect"
    assert out3["href"].startswith(f"/r/{pub}/c/sig_graph/entity/deployment/")
    # a record absent from that release → honest unavailable (no masquerade)
    out4 = resolve_selector(
        registry,
        as_of_world="2026-09-27",
        as_of_belief=None,
        ruleset=None,
        path="/entity/deployment/ent-nowhere/",
    )
    assert out4["status"] == "unavailable"
    # selectors no release covers → unavailable, never current content
    out5 = resolve_selector(registry, as_of_world="1999-01-01", as_of_belief=None, ruleset=None)
    assert out5["status"] == "unavailable"
    # unknown ruleset → unavailable, never "unchanged page labeled historical"
    out6 = resolve_selector(registry, as_of_world=None, as_of_belief=None, ruleset="ruleset/9.9.9")
    assert out6["status"] == "unavailable"
    # malformed → invalid
    out7 = resolve_selector(
        registry, as_of_world="definitely not a date", as_of_belief=None, ruleset=None
    )
    assert out7["status"] == "invalid"
    # no selectors → current convenience (never a citation)
    out8 = resolve_selector(registry, as_of_world=None, as_of_belief=None, ruleset=None)
    assert out8["status"] == "current" and out8["publication_id"] == pub


def test_resolve_ambiguous_when_two_releases_share_the_triple(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    registry = tmp_path / "registry"
    a = _build(tmp_path, export, name="a")
    activate(registry, a.out_dir)
    b = build_release(export, tmp_path / "b", renderer_revision="f00d" * 16)
    activate(registry, b.out_dir)
    out = resolve_selector(
        registry,
        as_of_world="2026-09-27",
        as_of_belief="2026-09-27",
        ruleset="p27.3/1.0.0",
    )
    assert out["status"] == "ambiguous"
    assert sorted(out["candidates"]) == sorted([a.publication_id, b.publication_id])


# --------------------------------------------------------------------------- #
# AC6 — incomplete compartment/index fails staging                             #
# --------------------------------------------------------------------------- #


def test_validate_and_activate_fail_on_missing_record(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    pub = build.publication_id
    victim = build.out_dir / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0.json"
    victim.unlink()
    report = validate_release(build.out_dir)
    assert report.state == "incomplete"
    assert any("missing artifact" in f or "missing file" in f for f in report.failures)
    with pytest.raises(ReleaseError, match="failed validation"):
        activate(tmp_path / "registry", build.out_dir)
    assert not (tmp_path / "registry" / "latest.json").exists()


def test_validate_fails_on_undeclared_artifact(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    pub = build.publication_id
    extra = build.out_dir / f"r/{pub}/c/sig_graph/entity/deployment/sneaky.json"
    extra.write_bytes(b"{}")
    report = validate_release(build.out_dir)
    assert report.state == "incomplete"
    assert any("undeclared artifact" in f for f in report.failures)


def test_validate_fails_on_index_digest_mismatch(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    pub = build.publication_id
    idx = build.out_dir / f"r/{pub}/c/sig_graph/records.index.jsonl"
    idx.write_bytes(b'{"record_key":"x"}\n')
    report = validate_release(build.out_dir)
    assert report.state == "incomplete"


# --------------------------------------------------------------------------- #
# AC7/AC8 — rollback + tombstones + barrier before origin                      #
# --------------------------------------------------------------------------- #


def test_rollback_repoints_latest_and_overlay(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    registry = tmp_path / "registry"
    a = _build(tmp_path, export, name="a")
    activate(registry, a.out_dir)
    b = build_release(export, tmp_path / "b", renderer_revision="f00d" * 16)
    activate(registry, b.out_dir)
    latest = json.loads((registry / "latest.json").read_text())
    assert latest["publication_id"] == b.publication_id
    out = rollback(registry, a.publication_id)
    latest = json.loads((registry / "latest.json").read_text())
    assert latest["publication_id"] == a.publication_id
    assert latest.get("rolled_back") is True
    stub = registry / "staged/entity/deployment/ent-src_a-0/index.html"
    assert f"/r/{a.publication_id}/" in stub.read_text()
    assert out["latest"] == a.publication_id


def test_rollback_refuses_unknown_release(tmp_path: Path) -> None:
    registry, _pub = _activated_registry(tmp_path)
    with pytest.raises(ReleaseError, match="not activated"):
        rollback(registry, "p-" + "0" * 64)


def test_withdrawal_tombstones_deterministic(tmp_path: Path) -> None:
    registry, pub = _activated_registry(tmp_path)
    staged = registry / "staged"
    rec = _disposition(TargetKind.ENTITY, "ent-src_a-1", Disposition.WITHDRAW)
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([rec])
    first = apply_withdrawals(staged, reg.withdrawals())
    html = (staged / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-1/index.html").read_text()
    assert "withdrawn" in html
    assert "safety_withdrawal" in html
    assert "test-authority" in html
    assert "2026-09-27" in html
    assert "rationale" not in html  # privileged fields never publish
    tomb = json.loads(
        (staged / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-1.json").read_text()
    )
    assert tomb["schema"] == "sig.tombstone/1"
    assert tomb["permitted"] is False
    assert tomb["reason_category"] == "safety_withdrawal"
    conf = (staged / "conf" / "withdrawn_routes.conf").read_text()
    assert f"location = /r/{pub}/c/sig_graph/entity/deployment/ent-src_a-1/" in conf
    assert conf.index("location =") >= 0
    # deterministic: same registry + same tree → identical result
    second = apply_withdrawals(staged, reg.withdrawals())
    assert second == first


def test_claim_withdrawal_denies_records_carrying_it(tmp_path: Path) -> None:
    registry, pub = _activated_registry(tmp_path)
    staged = registry / "staged"
    rec = _disposition(TargetKind.CLAIM, "claim-src_a-0-a", Disposition.WITHHOLD)
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([rec])
    apply_withdrawals(staged, reg.withdrawals())
    tomb = json.loads(
        (staged / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0.json").read_text()
    )
    assert tomb["schema"] == "sig.tombstone/1"
    assert (
        "Record withdrawn"
        in (staged / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/index.html").read_text()
    )


def test_artifact_withdrawal_denies_evidence_page(tmp_path: Path) -> None:
    registry, pub = _activated_registry(tmp_path)
    staged = registry / "staged"
    rec = _disposition(TargetKind.ARTIFACT, "art-sig_graph", Disposition.WITHDRAW)
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([rec])
    apply_withdrawals(staged, reg.withdrawals())
    assert (
        "Record withdrawn"
        in (staged / f"r/{pub}/c/sig_graph/evidence/art-sig_graph/index.html").read_text()
    )


def test_release_withdrawal_denies_the_whole_namespace(tmp_path: Path) -> None:
    registry, pub = _activated_registry(tmp_path)
    staged = registry / "staged"
    rec = _disposition(TargetKind.RELEASE_ARTIFACT, pub, Disposition.WITHDRAW)
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([rec])
    out = apply_withdrawals(staged, reg.withdrawals())
    assert out["denied"] > 0
    html = (staged / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/index.html").read_text()
    assert "Record withdrawn" in html
    # and the release landing is denied too
    assert (staged / f"releases/{pub}/index.html").exists()


def test_withdrawal_denies_under_rollback(tmp_path: Path) -> None:
    """A withhold recorded while R2 is latest still denies under an R1 rollback
    (ADR-124's access-time rule carried into the file layer)."""
    export = _write_export(tmp_path / "export")
    registry = tmp_path / "registry"
    a = _build(tmp_path, export, name="a")
    activate(registry, a.out_dir)
    b = build_release(export, tmp_path / "b", renderer_revision="f00d" * 16)
    activate(registry, b.out_dir)
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([_disposition(TargetKind.ENTITY, "ent-src_a-0", Disposition.WITHHOLD)])
    rollback(registry, a.publication_id)
    staged = registry / "staged"
    # the SAME record is denied under BOTH releases — the barrier is
    # current-disposition, not release-time
    assert (
        "Record withdrawn"
        in (
            staged / f"r/{a.publication_id}/c/sig_graph/entity/deployment/ent-src_a-0/index.html"
        ).read_text()
    )
    assert (
        "Record withdrawn"
        in (
            staged / f"r/{b.publication_id}/c/sig_graph/entity/deployment/ent-src_a-0/index.html"
        ).read_text()
    )


def test_route_access_check(tmp_path: Path) -> None:
    registry, pub = _activated_registry(tmp_path)
    route = f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/"
    out = route_access(registry, route)
    assert out["permitted"] is True
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([_disposition(TargetKind.ENTITY, "ent-src_a-0", Disposition.WITHDRAW)])
    out = route_access(registry, route)
    assert out["permitted"] is False
    assert out["tombstone"]["reason_category"] == "safety_withdrawal"
    assert out["tombstone"]["policy_version"] == "publication-eligibility/1"


def test_route_access_denies_routes_under_a_withdrawn_release(tmp_path: Path) -> None:
    """The namespace deny dominates: a route whose own target has no
    disposition is still denied under a withdrawn release (ADR-132)."""
    registry, pub = _activated_registry(tmp_path)
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([_disposition(TargetKind.RELEASE_ARTIFACT, pub, Disposition.WITHDRAW)])
    apply_withdrawals(registry / "staged", reg.withdrawals())
    for route in (
        f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/",
        f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0.json",
        f"releases/{pub}/",
    ):
        out = route_access(registry, route)
        assert out["permitted"] is False, route
        assert out["tombstone"]["reason_category"] == "safety_withdrawal"


def test_route_access_denies_record_carrying_a_denied_claim(tmp_path: Path) -> None:
    """A claim-level withhold denies every record route asserting it — the
    serving check sees the same denial the deny map encodes (ADR-132)."""
    registry, pub = _activated_registry(tmp_path)
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([_disposition(TargetKind.CLAIM, "claim-src_a-0-a", Disposition.WITHHOLD)])
    apply_withdrawals(registry / "staged", reg.withdrawals())
    out = route_access(registry, f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/")
    assert out["permitted"] is False
    # a record NOT carrying the claim stays permitted
    other = route_access(registry, f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-1/")
    assert other["permitted"] is True


def test_rollback_to_a_withdrawn_release_is_refused(tmp_path: Path) -> None:
    """Latest must never retarget every convenience URL at a wholly-denied
    namespace — rollback to a release under a current deny is refused."""
    registry, pub = _activated_registry(tmp_path)
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([_disposition(TargetKind.RELEASE_ARTIFACT, pub, Disposition.WITHDRAW)])
    apply_withdrawals(registry / "staged", reg.withdrawals())
    with pytest.raises(ReleaseError, match="denied namespace|disposition"):
        rollback(registry, pub)
    # the earlier namespace stays reachable at its own routes — as tombstones
    latest = json.loads((registry / "latest.json").read_text())
    assert latest["publication_id"] == pub  # unchanged — still the only release


def test_withdraw_allow_lifts_a_denial(tmp_path: Path) -> None:
    registry, pub = _activated_registry(tmp_path)
    staged = registry / "staged"
    reg = ReleaseRegistry(registry)
    reg.save_withdrawals([_disposition(TargetKind.ENTITY, "ent-src_a-0", Disposition.WITHHOLD)])
    apply_withdrawals(staged, reg.withdrawals())
    out = route_access(registry, f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/")
    assert out["permitted"] is False
    # a later allow supersedes for access decisions (append-only override)
    reg.save_withdrawals(
        reg.withdrawals()
        + [_disposition(TargetKind.ENTITY, "ent-src_a-0", Disposition.ALLOW, seq=1)]
    )
    out = route_access(registry, f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/")
    assert out["permitted"] is True


# --------------------------------------------------------------------------- #
# Compartment + namespace coverage                                             #
# --------------------------------------------------------------------------- #


def test_routes_are_release_and_compartment_specific(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    pub = build.publication_id
    assert (build.out_dir / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0.json").exists()
    assert (build.out_dir / f"r/{pub}/c/osm_physical/entity/deployment/ent-src_osm-0.json").exists()
    sig_doc = json.loads(
        (
            build.out_dir
            / "r"
            / pub
            / "c"
            / "sig_graph"
            / "entity"
            / "deployment"
            / "ent-src_a-0.json"
        ).read_text()
    )
    osm_doc = json.loads(
        (
            build.out_dir
            / "r"
            / pub
            / "c"
            / "osm_physical"
            / "entity"
            / "deployment"
            / "ent-src_osm-0.json"
        ).read_text()
    )
    assert sig_doc["license"] == "CC-BY-4.0"
    assert osm_doc["license"] == "ODbL-1.0"
    assert sig_doc["record_key"].startswith("sig_graph:")
    assert osm_doc["record_key"].startswith("osm_physical:")
    # the ODbL record's claim anchors point at the ODbL slice only
    anchors = {a["claim_id"] for a in osm_doc["claim_anchors"]}
    assert all(cid.startswith("claim-src_osm-") for cid in anchors)
    # evidence anchors resolve under the same compartment route
    ev = build.out_dir / f"r/{pub}/c/osm_physical/evidence/art-osm_physical/index.html"
    assert ev.exists()


def test_evidence_and_dossier_pages_emitted(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    pub = build.publication_id
    ev = build.out_dir / f"r/{pub}/c/sig_graph/evidence/art-sig_graph/index.html"
    assert "sig:connector:test:sig" in ev.read_text()
    dos = build.out_dir / f"r/{pub}/dossier/OK/index.html"
    assert "Data-sharing partners" in dos.read_text()
    land = build.out_dir / f"releases/{pub}/index.html"
    assert "sig_graph" in land.read_text()


def test_record_html_has_no_scripts_and_links_latest_as_convenience(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export", two_compartments=False)
    build = _build(tmp_path, export)
    pub = build.publication_id
    html = (
        build.out_dir / f"r/{pub}/c/sig_graph/entity/deployment/ent-src_a-0/index.html"
    ).read_text()
    assert "<script" not in html
    assert "never cite" in html or "convenience" in html
    assert "/entity/deployment/ent-src_a-0/" in html
    assert f"/r/{pub}/" in html


def test_measure_build_reports_cost(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    report = measure_build(export, tmp_path / "measured", renderer_revision=REVISION)
    assert report["records"] == 6
    assert report["files"] > 0 and report["bytes"] > 0
    assert report["wall_seconds"] >= 0 and report["peak_rss_bytes"] > 0
    assert (tmp_path / "measured" / "release" / "generation_measurement.json").exists()


# --------------------------------------------------------------------------- #
# Activation staging shape                                                     #
# --------------------------------------------------------------------------- #


def test_activation_stages_public_tree_and_overlay(tmp_path: Path) -> None:
    registry, pub = _activated_registry(tmp_path)
    staged = registry / "staged"
    assert (staged / f"r/{pub}/c/sig_graph/records.index.jsonl").exists()
    assert (staged / f"releases/{pub}/catalog_entry.json").exists()
    assert (staged / "releases/index.html").exists()
    assert (staged / "releases/catalog.json").exists()
    assert (staged / "entity/deployment/ent-src_a-0/index.html").exists()
    stub = (staged / "entity/deployment/ent-src_a-0/index.html").read_text()
    assert "convenience" in stub and (
        "never an immutable citation" in stub.lower() or "never cite" in stub
    )
    latest = json.loads((registry / "latest.json").read_text())
    assert latest["publication_id"] == pub
    compat = json.loads((registry / "compat_index.json").read_text())
    assert compat["entries"][0]["publication_id"] == pub
    act = json.loads((registry / f"activations/{pub}.json").read_text())
    assert act["activated_at"]  # real UTC instant lives in the receipt only


def test_activation_stamps_now_in_receipt_not_artifacts(tmp_path: Path) -> None:
    export = _write_export(tmp_path / "export")
    build = _build(tmp_path, export)
    registry = tmp_path / "registry"
    now = datetime(2026, 9, 28, 3, 4, 5, tzinfo=UTC)
    activate(registry, build.out_dir, now=now)
    act = json.loads((registry / f"activations/{build.publication_id}.json").read_text())
    assert act["activated_at"].startswith("2026-09-28")
    # nothing inside the hashed tree mentions the wall clock
    for art in (build.out_dir / "r").rglob("*.html"):
        assert "2026-09-28" not in art.read_text()


def test_cli_verbs(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    from exports.cli import main

    export = _write_export(tmp_path / "export")
    out = tmp_path / "rel"
    assert (
        main(
            [
                "release",
                "build",
                "--export-dir",
                str(export),
                "--out",
                str(out),
                "--renderer-revision",
                REVISION,
            ]
        )
        == 0
    )
    assert main(["release", "validate", "--release", str(out)]) == 0
    registry = tmp_path / "registry"
    assert main(["release", "activate", "--registry", str(registry), "--release", str(out)]) == 0
    assert (
        main(
            [
                "release",
                "resolve",
                "--registry",
                str(registry),
                "--as-of-world",
                "bogus",
            ]
        )
        == 2
    )
