# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The second-jurisdiction connector run wiring (P24.6 / JURIS.2 / GL-JURIS-01).

The France sources route through the P18.2 `france_belgium` connectors — data
rows in `CONNECTOR_FOR_SOURCE`, not a per-jurisdiction hack. All four are flipped
(operator + counsel determinations 2026-09-15): replay/shadow run over the
committed fixtures under network isolation; `decp_fr` is live (real DECP file),
`raa_prefectures`/`madada` carry document-capture targets (the RAA index CSV /
the MaDada Atom feed — P25.5), and `declarationcamera_be` alone still refuses
live on NoLiveTargets (the register sits behind Belgian eID).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from connectors.runner import CONNECTOR_FOR_SOURCE, RunMode, run_source

FIXTURES = Path(__file__).parent / "fixtures" / "france"

FRANCE_SOURCES = ("raa_prefectures", "madada", "decp_fr", "declarationcamera_be")


def test_france_sources_are_mapped_to_the_p18_connectors() -> None:
    # The adapter exercise needs no per-jurisdiction hack: the four France/Belgium
    # source ids resolve to the two registered france_belgium connectors.
    assert CONNECTOR_FOR_SOURCE["raa_prefectures"] == "france_belgium_records"
    assert CONNECTOR_FOR_SOURCE["madada"] == "france_belgium_records"
    assert CONNECTOR_FOR_SOURCE["declarationcamera_be"] == "france_belgium_records"
    assert CONNECTOR_FOR_SOURCE["decp_fr"] == "france_belgium_procurement"


def test_committed_france_fixtures_exist() -> None:
    for name in ("raa_prefectures.json", "madada_records.json", "decp_marches.json"):
        assert (FIXTURES / name).exists(), name


def test_raa_shadow_run_emits_the_prefectoral_instrument() -> None:
    report = run_source(
        "raa_prefectures",
        mode=RunMode.SHADOW,
        fixture=FIXTURES / "raa_prefectures.json",
        kind="records",
        media_type="application/json",
    )
    assert report.connector == "france_belgium_records"
    predicates = {c.get("predicate_id") for c in report.claims}
    assert "instrument_type" in predicates
    inst = next(c for c in report.claims if c.get("predicate_id") == "instrument_type")
    assert inst["value"] == "fr.arrete_prefectoral"
    # The five-year renewable sunset is derived (CSI L252), not stored.
    sunset = next(c for c in report.claims if c.get("predicate_id") == "sunset_date")
    assert sunset["value"] == "2031-02-01"
    assert report.diff is not None and report.diff.changed_count == 0


def test_madada_shadow_run_now_passes_the_gate() -> None:
    # Counsel approved madada (HG-02, 2026-09-15) — DERIVE custody +
    # public_terms_only + the derived-facts licence — so a shadow run over the
    # committed fixture now passes the loader gate (it was refused before the
    # counsel flip). Live still refuses on NoLiveTargets (adapter owed).
    report = run_source(
        "madada",
        mode=RunMode.SHADOW,
        fixture=FIXTURES / "madada_records.json",
        kind="records",
        media_type="application/json",
    )
    assert report.claims


def test_document_capture_yields_artifact_not_claims() -> None:
    # A live upstream document (non-JSON — a gazette PDF, an index page, a MaDada
    # Atom feed) is captured as an EvidenceArtifact row carrying provenance + the
    # P07.1 verdict; no instrument claim is fabricated from an unparsed document.
    report = run_source(
        "raa_prefectures",
        mode=RunMode.SHADOW,
        fixture=FIXTURES / "sample_document.pdf",
        kind="records",
        media_type="application/pdf",
    )
    kinds = [row["record_kind"] for row in report.claims]
    assert "evidence_artifact" in kinds
    assert "quality_report" in kinds
    assert "claim" not in kinds
    artifact = next(r for r in report.claims if r["record_kind"] == "evidence_artifact")
    assert artifact["predicate_id"] == "document"
    assert artifact["published_by"] == "raa_prefectures"
    assert artifact["classification"]["file_format"] == "pdf"


def test_madada_fixture_normalizes_to_fr_cada_not_foia() -> None:
    # The connector itself is correct over the fixture — only the source's gate
    # blocks the run. (The regime claim is what the seed carries into the spine.)
    import dataclasses

    from connectors.registry import get
    from connectors.stages import (
        InMemoryCaptureStore,
        InMemoryClaimSink,
        RunContext,
        registered_connectors,
    )
    from evidence.ingest_run import IngestRun

    connector = registered_connectors()["france_belgium_records"]()
    payload = json.loads((FIXTURES / "madada_records.json").read_text())
    ctx = RunContext(
        source=dataclasses.replace(get("madada"), ingestion_permitted=True),
        run=IngestRun(
            connector_name="france_belgium",
            connector_version="1.0.0",
            code_commit="deadbeef",
            ruleset_version="r1",
            vocab_version="v1",
            input_digests=(),
        ),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
    )
    rows = connector.normalize(
        ctx,
        [{"record_kind": "records_request", "raw": r} for r in payload["records_requests"]],
    )
    acq = next(r for r in rows if r.get("predicate_id") == "acquisition_method")
    assert acq["value"] == "fr.cada"
    values = {str(r.get("value")) for r in rows}
    assert "foia_request" not in values
    assert not any(v.startswith("us.") for v in values)


def test_decp_shadow_run_maps_marches_onto_contracts() -> None:
    report = run_source(
        "decp_fr",
        mode=RunMode.SHADOW,
        fixture=FIXTURES / "decp_marches.json",
        kind="bulk_csv",
        media_type="application/json",
    )
    contracts = [c for c in report.claims if c.get("record_kind") == "contract"]
    assert len(contracts) == 2
    # The accord-cadre marché is a cooperative piggyback (SIG-ONTO-032) with its
    # parent set — the invariant reached with no US vocabulary.
    piggyback = next(c for c in contracts if c.get("idAccordCadre") or "accord" in json.dumps(c))
    assert piggyback.get("parent_cooperative_contract") == "accord-cadre-2024-089"
    assert piggyback.get("acquisition_channel") == "cooperative_piggyback"
    assert report.diff is not None and report.diff.changed_count == 0


def test_france_document_targets_registered_but_declarationcamera_stays_gated() -> None:
    # Counsel approved all four France/Belgium sources (HG-02, 2026-09-15).
    # With the document-capture path landed (P25.5), raa_prefectures carries the
    # national RAA index CSV and madada the platform's own Atom feed — both
    # captured as EvidenceArtifacts. declarationcamera_be stays targetless: the
    # register sits behind Belgian eID — no anonymous path exists to register.
    from connectors.live_targets import NoLiveTargets, live_targets

    assert live_targets("raa_prefectures")
    assert live_targets("madada")
    with pytest.raises(NoLiveTargets):
        run_source("declarationcamera_be", mode=RunMode.LIVE)


def test_all_france_sources_are_flipped_on_the_counsel_basis() -> None:
    # Counsel approved ingestion for the whole cohort (HG-02, 2026-09-15):
    # raa_prefectures (ODbL-1.0) + decp_fr (LicenceOuverte-2.0, ADR-084) on their
    # confirmed licences; madada + declarationcamera_be on the derived-facts
    # basis (LicenseRef-DerivedFacts-Citations — request metadata / register
    # facts only, never user-authored request text; redistributable=false).
    from connectors.registry import get

    for source_id in FRANCE_SOURCES:
        assert get(source_id).ingestion_permitted is True, source_id
    # The P24.6 rights packets are linked from the France source rows (Belgium's
    # eID-gated register is out of the France slice — its packet is HG-04 work).
    for source_id in ("raa_prefectures", "decp_fr", "madada"):
        assert get(source_id).review_packet.startswith("docs/build/reports/rights/")


def test_run_france_script_exists_and_is_france_shaped() -> None:
    script = Path(__file__).resolve().parents[2] / "docs" / "build" / "tools" / "run_france.sh"
    assert script.exists()
    text = script.read_text()
    assert 'JURISDICTION="france"' in text
    assert '--jurisdiction "$JURISDICTION"' in text
    assert "acceptance.live_api_france" in text
    assert "--mode live" not in text.replace("re-run with --mode live", "")
    # Templated from run_okc.sh: the same eight stages, in order.
    for stage in ("1/8", "2/8", "3/8", "4/8", "5/8", "6/8", "7/8", "8/8"):
        assert stage in text
    # France-shaped, not a copy: its own sources + reports dir.
    assert "raa_prefectures" in text and "decp_fr" in text and "madada" in text
    assert "reports/france" in text
