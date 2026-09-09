# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Zenodo quarterly-release deposit (§38.2, SIG-EXPORT-002)."""

from __future__ import annotations

from datetime import date

from exports.manifest import Artifact, BuildSpec, Manifest

from exports import zenodo as Z


def _manifest(**kw: object) -> tuple[Manifest, dict[str, bytes], tuple[Artifact, ...]]:
    spec = BuildSpec(date(2026, 6, 30), date(2026, 6, 30), "ruleset/1", "resolver/1", **kw)  # type: ignore[arg-type]
    graph = Artifact.of(
        name="claims.csv",
        path="sig_graph/claims.csv",
        media_type="text/csv",
        compartment="sig_graph",
        license="CC-BY-4.0",
        data=b"claims",
    )
    evid = Artifact.of(
        name="captures.jsonl",
        path="sig_graph/captures.jsonl",
        media_type="application/x-ndjson",
        compartment="sig_graph",
        license="CC-BY-4.0",
        data=b"a lot of evidence bytes" * 100,
    )
    manifest = Manifest(spec, (graph, evid))
    by_path = {
        "sig_graph/claims.csv": b"claims",
        "sig_graph/captures.jsonl": b"a lot of evidence bytes" * 100,
    }
    return manifest, by_path, (evid,)


def test_deposit_carries_concept_and_version_doi() -> None:
    manifest, by_path, evidence = _manifest()
    dep = Z.deposit_release(manifest, by_path, Z.FakeZenodoTransport(), evidence_artifacts=evidence)
    assert dep.concept_doi.startswith("10.5281/zenodo.")
    assert dep.version_doi.startswith("10.5281/zenodo.")
    assert dep.concept_doi != dep.version_doi


def test_concept_doi_is_stable_across_versions_version_doi_is_not() -> None:
    # The whole point of the split (§38.2): cite the dataset once, pin a run forever.
    m1, by_path, evidence = _manifest()
    transport = Z.FakeZenodoTransport()
    d1 = Z.deposit_release(m1, by_path, transport, evidence_artifacts=evidence)
    # A later release of the SAME dataset (a new quarter / ruleset): a new version DOI,
    # but the same concept DOI, because the dataset slug is unchanged.
    spec2 = BuildSpec(date(2026, 9, 30), date(2026, 9, 30), "ruleset/2", "resolver/1")
    m2 = Manifest(spec2, m1.artifacts)
    d2 = Z.deposit_release(m2, by_path, transport, evidence_artifacts=evidence)
    assert d1.concept_doi == d2.concept_doi
    assert d1.version_doi != d2.version_doi


def test_evidence_bytes_are_excluded_but_digest_manifest_is_deposited() -> None:
    # §38.2: evidence bytes excluded by size; the manifest of digests is deposited.
    manifest, by_path, evidence = _manifest()
    payload = Z.deposit_payload(
        manifest, by_path, evidence_paths=frozenset(a.path for a in evidence)
    )
    assert "sig_graph/captures.jsonl" not in payload  # evidence bytes excluded
    assert "sig_graph/claims.csv" in payload  # non-evidence bytes kept
    assert Z.MANIFEST_PATH in payload and Z.DIGESTS_PATH in payload
    import json

    digests = json.loads(payload[Z.DIGESTS_PATH])
    # the excluded evidence STILL has its digest recorded, so the citation pins it.
    assert "sig_graph/captures.jsonl" in digests


def test_deposition_records_the_excluded_evidence() -> None:
    manifest, by_path, evidence = _manifest()
    dep = Z.deposit_release(manifest, by_path, Z.FakeZenodoTransport(), evidence_artifacts=evidence)
    assert dep.excluded_evidence == ("sig_graph/captures.jsonl",)
