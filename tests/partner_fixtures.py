# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P31.5 partner fixture set: real connector stages over committed fixtures.

Runs each connector's post-capture stages (parse → extract → normalize → link → load)
over one committed fixture capture with a FIXED retrieval time, network-isolated and
non-asserting (:func:`connectors.replay.replay`), so the emitted records are
byte-reproducible. Shared by the shadow-diff test
(``tests/connectors/test_partner_refs_shadow.py``) and the real-PG materializer proof
(``tests/db/test_partner_entity_refs.py``). The fixtures are listed in
``tests/connectors/fixtures/partners/SOURCES.md``.

This module deliberately uses only APIs that existed before P31.5, so the golden
digests (``fixtures/partners/text_claim_digests.json``) were produced by running it
unchanged at the base commit.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from connectors.accountability import AccountabilityConnector
from connectors.dot_511 import Dot511Connector
from connectors.france_belgium import FranceBelgiumProcurementConnector
from connectors.live_targets import live_targets
from connectors.procurement import ProcurementConnector
from connectors.registry import get
from connectors.replay import replay
from connectors.stages import Connector, InMemoryCaptureStore, InMemoryClaimSink, RunContext
from evidence.ingest_run import IngestRun

FIXTURES = Path(__file__).parent / "connectors" / "fixtures"
PARTNERS = FIXTURES / "partners"
GOLDEN = PARTNERS / "text_claim_digests.json"
RETRIEVED = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)

_TED_ENDPOINT = "https://api.ted.europa.eu/v3/notices/search"
_USASPENDING_URI = "https://api.usaspending.gov/api/v2/search/spending_by_award/"


@dataclasses.dataclass(frozen=True)
class FixtureRun:
    """One committed fixture capture replayed through one connector."""

    key: str
    connector: Callable[[], Connector]
    source_id: str
    path: Path
    media_type: str
    source_uri: str
    targets: tuple[Mapping[str, Any], ...] = ()


def _wa_target() -> Mapping[str, Any]:
    targets = [
        t
        for t in live_targets("dot_511_wa")
        if t["id"] == "wa_wsdot_travel_cameras" and t.get("page", 0) == 0
    ]
    assert len(targets) == 1
    return targets[0]


def fixture_runs() -> list[FixtureRun]:
    wa = _wa_target()
    decp_uri = "https://www.data.gouv.fr/fixtures/decp_marches.json"
    return [
        FixtureRun(
            "procurement_contracts",
            ProcurementConnector,
            "govspend",
            PARTNERS / "contracts.json",
            "application/json",
            "https://govspend.example.invalid/contracts.json",
        ),
        FixtureRun(
            "usaspending_awards",
            ProcurementConnector,
            "usaspending",
            PARTNERS / "usaspending_awards.json",
            "application/json",
            _USASPENDING_URI,
        ),
        FixtureRun(
            "ted_eu",
            ProcurementConnector,
            "ted_eu",
            FIXTURES / "ted_eu_search_page1.json",
            "application/json",
            _TED_ENDPOINT,
        ),
        FixtureRun(
            "decp_fr",
            FranceBelgiumProcurementConnector,
            "decp_fr",
            FIXTURES / "france" / "decp_marches.json",
            "application/json",
            decp_uri,
            ({"id": "t1", "url": decp_uri, "kind": "bulk_csv"},),
        ),
        FixtureRun(
            "dot_511_wa",
            Dot511Connector,
            "dot_511_wa",
            FIXTURES / "dot_511" / "wa_wsdot.json",
            "application/json",
            str(wa["url"]),
            (wa,),
        ),
        FixtureRun(
            "atlas_issue_records",
            AccountabilityConnector,
            "alpr_accountability_atlas",
            PARTNERS / "atlas_issue_records.csv",
            "text/csv",
            "https://alpratlas.org/issue_records.csv",
        ),
    ]


def run_fixture(run: FixtureRun) -> list[dict[str, Any]]:
    """Replay one fixture capture through its connector; returns the loaded records."""
    connector = run.connector()
    source = dataclasses.replace(get(run.source_id), ingestion_permitted=True)
    ctx = RunContext(
        source=source,
        run=IngestRun(
            connector.name, getattr(connector, "version", "1.0.0"), "fixture", "r1", "v1", ()
        ),
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": [dict(t) for t in run.targets]},
    )
    capture = ctx.captures.put(
        run.path.read_bytes(),
        media_type=run.media_type,
        source_uri=run.source_uri,
        retrieved_at=RETRIEVED,
    )
    return [dict(r) for r in replay(connector, ctx, [capture])]


def fixture_records() -> dict[str, list[dict[str, Any]]]:
    """Every fixture run's loaded records, keyed by run."""
    return {run.key: run_fixture(run) for run in fixture_runs()}


#: The accountability vocabulary version stamped on records at the P31.5 base
#: commit (34406ff) the golden digests were computed under. A §20 vocabulary
#: migration bumps the version `_stamp` writes onto every record — same claim
#: content under a new provenance stamp, and in production a new append-only
#: claim row on the next run — so a digest comparison against the base-commit
#: golden must normalize the stamp back (P31.12 bumped it to 2026.09.26.1).
GOLDEN_ACCOUNTABILITY_VOCAB = "2026.09.18.2"


def golden_digest(run_key: str, record: Mapping[str, Any]) -> str:
    """`content_digest` comparable to the base-commit golden for ``run_key``.

    Records from the accountability connector carry its vocabulary version; the
    golden pins the base-commit stamp, so the field is normalized before
    digesting. Every other run's records digest exactly as stored.
    """
    from db.claim_sink import content_digest

    runs = {r.key: r for r in fixture_runs()}
    if runs[run_key].connector is AccountabilityConnector and "vocab_version" in record:
        record = {**record, "vocab_version": GOLDEN_ACCOUNTABILITY_VOCAB}
    return content_digest(record)
