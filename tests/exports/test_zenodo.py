# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Zenodo quarterly-release deposit (§38.2, SIG-EXPORT-002)."""

from __future__ import annotations

import json
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
    digests = json.loads(payload[Z.DIGESTS_PATH])
    # the excluded evidence STILL has its digest recorded, so the citation pins it.
    assert "sig_graph/captures.jsonl" in digests


def test_deposition_records_the_excluded_evidence() -> None:
    manifest, by_path, evidence = _manifest()
    dep = Z.deposit_release(manifest, by_path, Z.FakeZenodoTransport(), evidence_artifacts=evidence)
    assert dep.excluded_evidence == ("sig_graph/captures.jsonl",)


# --- the real Zenodo REST transport: request shapes (HG-07: no live account) ---


def test_zenodo_metadata_matches_the_deposit_api_shape() -> None:
    md = Z.DepositMetadata(
        title="SIG dataset release sig-2026",
        version="sig-2026",
        concept_id="sig",
        licenses=("CC-BY-4.0", "ODbL-1.0"),
    )
    body = Z.zenodo_metadata(md)
    # The Zenodo deposition metadata block (real API fields).
    assert body["upload_type"] == "dataset"
    assert body["title"] == "SIG dataset release sig-2026"
    assert body["version"] == "sig-2026"
    assert body["creators"] == [{"name": "The SIG project"}]
    # Compartment-aware licence (SIG-LIC-004, §42): CC-BY is the primary Zenodo licence,
    # and BOTH compartment licences are spelled out for the reader.
    assert body["license"] == "cc-by-4.0"
    assert "ODbL-1.0" in body["description"] and "CC-BY-4.0" in body["description"]


def test_http_transport_drives_the_real_deposit_flow() -> None:
    import httpx

    calls: list[tuple[str, str]] = []
    uploaded: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        # The token rides as a query param on every call (Zenodo access_token).
        assert request.url.params.get("access_token") == "tok"
        if request.method == "POST" and request.url.path == "/api/deposit/depositions":
            return httpx.Response(
                201,
                json={
                    "id": 42,
                    "links": {"bucket": "https://sandbox.zenodo.org/api/files/bkt"},
                },
            )
        if request.method == "PUT" and request.url.path == "/api/deposit/depositions/42":
            body = json.loads(request.content)
            assert body["metadata"]["upload_type"] == "dataset"  # real metadata shape
            return httpx.Response(200, json={"id": 42})
        if request.method == "PUT" and "/api/files/bkt/" in request.url.path:
            name = request.url.path.split("/api/files/bkt/", 1)[1]
            uploaded[name] = request.content
            return httpx.Response(201, json={"key": name})
        if request.url.path.endswith("/actions/publish"):
            return httpx.Response(
                202,
                json={"doi": "10.5072/zenodo.999", "conceptdoi": "10.5072/zenodo.100"},
            )
        raise AssertionError(f"unexpected request {request.method} {request.url}")

    transport = Z.ZenodoHttpTransport(
        token="tok", sandbox=True, transport=httpx.MockTransport(handler)
    )
    md = Z.DepositMetadata("t", "v", "sig", ("CC-BY-4.0",))
    concept, version = transport.deposit(
        concept_id="sig", version="v", files={"manifest.json": b"{}"}, metadata=md
    )
    # Sandbox mints 10.5072 test DOIs (RISK-P21-08: NOT the production 10.5281 prefix).
    assert concept == "10.5072/zenodo.100"
    assert version == "10.5072/zenodo.999"
    # The flow ran in order: create → metadata → upload → publish.
    assert calls[0] == ("POST", "/api/deposit/depositions")
    assert ("POST", "/api/deposit/depositions/42/actions/publish") in calls
    assert uploaded == {"manifest.json": b"{}"}


def test_deposit_export_dir_reads_a_built_release(tmp_path) -> None:
    manifest, by_path, _ = _manifest()
    (tmp_path / "sig_graph").mkdir()
    (tmp_path / "manifest.json").write_bytes(manifest.to_bytes())
    (tmp_path / "sig_graph" / "claims.csv").write_bytes(b"claims")
    (tmp_path / "sig_graph" / "captures.jsonl").write_bytes(b"a lot of evidence bytes" * 100)
    transport = Z.FakeZenodoTransport()
    dep = Z.deposit_export_dir(str(tmp_path), transport, extra_files={"CITATION.cff": b"cff"})
    assert "CITATION.cff" in dep.files
    assert Z.MANIFEST_PATH in dep.files and Z.DIGESTS_PATH in dep.files
    assert dep.concept_doi != dep.version_doi


def test_sandbox_prefix_is_distinct_from_production() -> None:
    # RISK-P21-08: a sandbox DOI must never be mistaken for a production concept DOI.
    fake_sandbox = Z.FakeZenodoTransport(prefix=Z.ZENODO_SANDBOX_PREFIX)
    c, _ = fake_sandbox.deposit(concept_id="sig", version="v", files={}, metadata=None)  # type: ignore[arg-type]
    assert c.startswith("10.5072/zenodo.")


def test_deposits_ledger_is_append_only() -> None:
    from datetime import date

    from exports.deposits import DepositRecord, append_record

    dep = Z.Deposition("10.5072/zenodo.1", "10.5072/zenodo.2", ("manifest.json",))
    rec = DepositRecord("sig-2026", "sandbox-dry-run", dep, date(2026, 9, 9))
    first = append_record(None, rec)
    assert "| sandbox-dry-run |" in first
    assert "10.5072/zenodo.1" in first
    # A second record keeps the first verbatim and adds a row (never rewrites history).
    rec2 = DepositRecord("sig-2027", "sandbox", dep, date(2027, 1, 1))
    second = append_record(first, rec2)
    assert first.rstrip("\n") in second
    assert second.count("| sig-20") == 2
