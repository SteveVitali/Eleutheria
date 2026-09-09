# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Stage-5 pathway coverage (§46, P21.9, deliverable 4, RISK-P17-03 retirement).

The proof that Phase 17's pathways are now **ingested**, not merely expressible: every
pathway in the P17 conformance suite (the three ``tests/ontology/generalization/
test_stage5_*.py`` graphs) must have **at least one claim produced by a connector fixture**.
This is the mechanical retirement of RISK-P17-03 ("populated pathways are instance graphs in
the conformance suite, not rows persisted to the claim spine"): if a pathway had no
connector-produced claim, this test fails.

The coverage table is rendered into ``docs/build/STAGE5_CONNECTORS.md``; this test also
asserts that committed report is consistent with the live coverage (no stale doc).
"""

from __future__ import annotations

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from connectors.net import FetchResult, PoliteFetcher, RobotsResult
from connectors.pipeline import run
from connectors.registry import CompactStatus, CustodyPosture, get
from connectors.stages import InMemoryCaptureStore, InMemoryClaimSink, RunContext
from evidence.ingest_run import IngestRun

from connectors import pathways as pw

_FIX = Path(__file__).parent / "fixtures" / "pathways"
_REPORT = Path("docs/build/reports/STAGE5_CONNECTORS.md")
_FAMILIES = ("rtcc_federation", "fr_css_forensics", "acoustic_drone_location")

# The canonical roster of P17 conformance-suite pathways, one per fixture graph in
# tests/ontology/generalization/test_stage5_*.py. Kept explicit here (not derived) so a
# drift between the ontology conformance suite and the connector coverage is a failed test.
_CONFORMANCE_SUITE_PATHWAYS = {
    "private_camera_federation",
    "rtcc_hub",
    "broker_chain",
    "face_recognition",
    "css_and_forensics",
    "federal_authorization",
    "gunshot_detection",
    "drones",
    "commercial_location",
}


class _StaticTransport:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text="User-agent: *\nAllow: /\n")

    def request(self, url: str, *, user_agent: str) -> FetchResult:
        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type="application/json",
            retrieved_at=datetime(2026, 8, 20, tzinfo=UTC),
        )


def _run_family(family: str) -> list[dict[str, Any]]:
    source_id = pw.pathway_family_source(family)
    transport = _StaticTransport((_FIX / f"{family}.json").read_bytes())
    fetcher = PoliteFetcher(
        connector_name="pathways", connector_version="1.0.0", transport=transport
    )
    source = dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        custody_posture=CustodyPosture.REFERENCE,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )
    ctx = RunContext(
        source=source,
        run=IngestRun("pathways", "1.0.0", "deadbeef", "r1", "v1", ()),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [{"id": "t1", "url": f"https://{source_id}/x", "kind": "bulk"}]},
    )
    return run(pw.PathwaysConnector(), ctx).claims


def _coverage() -> dict[str, list[dict[str, Any]]]:
    by_pathway: dict[str, list[dict[str, Any]]] = {}
    for family in _FAMILIES:
        for claim in _run_family(family):
            by_pathway.setdefault(claim["conformance_pathway"], []).append(claim)
    return by_pathway


# --- the coverage proof (deliverable 4) ---------------------------------------


def test_vocab_roster_matches_the_conformance_suite() -> None:
    # The connector's declared roster must equal the P17 conformance-suite pathways.
    assert pw.all_conformance_pathways() == _CONFORMANCE_SUITE_PATHWAYS


def test_every_p17_pathway_has_at_least_one_connector_produced_claim() -> None:
    # RISK-P17-03 retirement: every conformance-suite pathway is now ingested.
    coverage = _coverage()
    for pathway in sorted(_CONFORMANCE_SUITE_PATHWAYS):
        assert coverage.get(pathway), f"P17 pathway {pathway!r} has no connector-produced claim"


def test_no_deployment_claim_from_a_procurement_genre_document() -> None:
    for claims in _coverage().values():
        for c in claims:
            if c["document_genre"] == "procurement_record":
                assert c["claim_type"] != "deployment"


def test_stage5_connectors_report_is_present_and_consistent() -> None:
    # The rendered coverage table must exist and mark every pathway MET (no stale doc).
    assert _REPORT.exists(), "docs/build/STAGE5_CONNECTORS.md is missing"
    text = _REPORT.read_text()
    coverage = _coverage()
    for pathway in sorted(_CONFORMANCE_SUITE_PATHWAYS):
        assert pathway in text, f"{pathway} missing from STAGE5_CONNECTORS.md"
        assert coverage.get(pathway)  # live coverage backs the doc's MET row


if __name__ == "__main__":  # render the committed coverage table
    coverage = _coverage()
    lines = [
        "# Stage-5 connector coverage — P17 pathways (P21.9, §46)",
        "",
        "Auto-derivable via `python -m tests.connectors.test_pathway_coverage`. Every P17",
        "conformance-suite pathway has >=1 claim produced by a `pathways` connector fixture",
        "(the mechanical retirement of RISK-P17-03). All runs are fixture replay — no live",
        "fetch (HG-03/HG-04 per source pending); a `run --mode live` refuses (exit 3).",
        "",
        "| P17 pathway | family | claims | claim types | verdict |",
        "|---|---|---|---|---|",
    ]
    fam_of = {p: fam for fam, ps in pw.conformance_pathways().items() for p in ps}
    for pathway in sorted(_CONFORMANCE_SUITE_PATHWAYS):
        claims = coverage.get(pathway, [])
        types = ", ".join(sorted({c["claim_type"] for c in claims})) or "—"
        verdict = "MET" if claims else "MISSING"
        lines.append(f"| {pathway} | {fam_of[pathway]} | {len(claims)} | {types} | {verdict} |")
    print("\n".join(lines))
