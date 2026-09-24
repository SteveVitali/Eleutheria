# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The second-jurisdiction connector run wiring (P24.6 / JURIS.2 / GL-JURIS-01).

The France sources route through the P18.2 `france_belgium` connectors — data
rows in `CONNECTOR_FOR_SOURCE`, not a per-jurisdiction hack. Every source stays
`ingestion_permitted=false` (HG-03): replay/shadow run over the committed
fixtures under network isolation; a live run is refused before any socket opens.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from connectors.runner import CONNECTOR_FOR_SOURCE, LiveGateRefused, RunMode, run_source

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


def test_madada_shadow_run_is_refused_at_the_compact_gate() -> None:
    # `madada` is compact_status=not_contacted + custody LINK — the loader gate
    # refuses even a fixture/shadow run (SIG-INGEST-014/027). That refusal is the
    # honest evidence run_france.sh records; the fr.cada claim still reaches the
    # spine via the seed.
    from connectors.loader import IngestionNotPermitted

    with pytest.raises(IngestionNotPermitted, match="compact_status"):
        run_source(
            "madada",
            mode=RunMode.SHADOW,
            fixture=FIXTURES / "madada_records.json",
            kind="records",
            media_type="application/json",
        )


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


@pytest.mark.parametrize("source_id", FRANCE_SOURCES)
def test_live_run_refuses_every_france_source(source_id: str) -> None:
    # No France source is flipped (HG-03): a live run is refused before any
    # socket opens — the gate exercised in the second jurisdiction, exit 3 at CLI.
    with pytest.raises(LiveGateRefused):
        run_source(source_id, mode=RunMode.LIVE)


def test_no_france_source_is_flipped() -> None:
    # The registry posture this ticket must not change (HG-03 is an operator gate).
    from connectors.registry import get

    for source_id in FRANCE_SOURCES:
        record = get(source_id)
        assert record.ingestion_permitted is False, source_id
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
