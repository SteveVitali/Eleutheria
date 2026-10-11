# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.11 / R11-ACQ-07 — the ADR-185 S8 tribal screened lane.

The two IND-TRIBAL members (plan AP-T2-201 cand I5-C225; plan AP-T2-210 cand
I9b-C095) land under the operator's B-37 answer "TR facts+cite":

* ``camreg_tribal_all_leaders_directory`` — the BIA Tribal Leaders Directory.
  The screened lane captures the layer's own ArcGIS REST **metadata page**
  (a bounded citation document: stated name + the verbatim BIA use
  disclaimer). The 601-row ``arcgis_query`` is a recorded *non-target*
  outcome (``[[enumerated]] status = "screened_lane"``) — no row is ever
  fetched; leader name/phone/email fields stay unread.
* ``legis_tribal_tohono_oodham_notice`` — the single Tohono O'odham
  Legislative Branch public-hearing notice on the Border Patrol LGDS +
  Automated Surveillance Tower proposals. Institutional facts only — the
  chairperson the notice names is deliberately not a configured field and
  the shared Part VIII person-name guard would refuse one anyway.

These tests pin the lane's invariants: gated registry rows, screened
predicate allowlists, facts+citations only over committed stand-in fixtures,
and the recorded non-target enumeration — never a rights decision, a live
fetch or an ingestion_permitted flip (HG-03/OP-26 remains the operator's).
"""

from __future__ import annotations

import copy
import dataclasses
import re
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from connectors.dossier_documents import (
    DOSSIER_DOCUMENTS as CONNECTOR,
)
from connectors.dossier_documents import (
    DOSSIER_SOURCES,
    adapter_config,
    check_crosswalk,
    predicate_allowlist,
)
from connectors.live_targets import live_targets
from connectors.loader import IngestionNotPermitted, assert_loadable
from connectors.net import PoliteFetcher, RateLimiter, RobotsResult
from connectors.pipeline import run
from connectors.registry import get
from connectors.runner import CONNECTOR_FOR_SOURCE
from connectors.stages import (
    FetchResult,
    InMemoryCaptureStore,
    InMemoryClaimSink,
    RunContext,
    get_connector,
)
from evidence.ingest_run import IngestRun

_FIX = Path(__file__).resolve().parent / "fixtures" / "dossier"
_REPO = Path(__file__).resolve().parents[2]
_RETRIEVED = datetime(2026, 10, 19, 15, 0, 0, tzinfo=UTC)
_ALLOW_ALL = "User-agent: *\nAllow: /\n"

TRIBAL_SOURCES = (
    "camreg_tribal_all_leaders_directory",
    "legis_tribal_tohono_oodham_notice",
)

#: doc_id -> (fixture file, media type) — the committed stand-ins.
FIXTURE_FOR_DOC: dict[str, tuple[str, str]] = {
    "bia-tld-layer-metadata": ("bia_tribal_leadership_layer.html", "text/html"),
    "tolc-lgds-ast-hearing-notice-2025-11-19": (
        "tolc_lgds_ast_hearing_notice.pdf",
        "application/pdf",
    ),
}

#: The predicates the lane may emit — facts + citations only (B-37). Person-
#: name, registrant, row-level and device predicates are absent by
#: construction, not convention.
SCREENED_ALLOWLISTS: dict[str, frozenset[str]] = {
    "camreg_tribal_all_leaders_directory": frozenset(
        {"title", "document", "use_restriction", "disclosure_field_state"}
    ),
    "legis_tribal_tohono_oodham_notice": frozenset(
        {
            "title",
            "document",
            "technology",
            "enacting_body",
            "posted_date",
            "disclosure_field_state",
        }
    ),
}

#: Predicates that would read as a person/row/device fact — never allowed.
FORBIDDEN_PREDICATES = {
    "camera_operator",
    "fixed_asset_location",
    "deployment_exists",
    "claimed_device_count",
    "active_device_count",
    "installed_device_count",
}


class _MapTransport:
    """URL-keyed canned responses — no real network (SIG-INGEST-011)."""

    def __init__(self) -> None:
        self.responses: dict[str, tuple[bytes, str]] = {}
        self.requested: list[str] = []

    def add_url(self, url: str, body: bytes, media: str) -> None:
        self.responses[url] = (body, media)

    def robots(self, robots_url: str) -> RobotsResult:
        return RobotsResult(text=_ALLOW_ALL, status=200)

    def request(
        self, url: str, *, user_agent: str, headers: Any = None, body: bytes | None = None
    ) -> FetchResult:
        self.requested.append(url)
        if url in self.responses:
            resp_body, media = self.responses[url]
            return FetchResult(
                url=url,
                status=200,
                body=resp_body,
                media_type=media,
                retrieved_at=_RETRIEVED,
            )
        return FetchResult(
            url=url,
            status=404,
            body=b"",
            media_type="text/plain",
            retrieved_at=_RETRIEVED,
        )


def _ctx(source_id: str, targets: list[dict[str, Any]]) -> RunContext:
    source = dataclasses.replace(get(source_id), ingestion_permitted=True)
    transport = _MapTransport()
    for target in targets:
        doc_id = str(target.get("doc_id") or target.get("id"))
        name, media = FIXTURE_FOR_DOC[doc_id]
        transport.add_url(str(target["url"]), (_FIX / name).read_bytes(), media)
    fetcher = PoliteFetcher(
        connector_name=CONNECTOR,
        connector_version="1.0.0",
        transport=transport,
        rate_limiter=RateLimiter(sleep=lambda s: None),
    )
    return RunContext(
        source=source,
        run=IngestRun(
            connector_name=CONNECTOR,
            connector_version="1.0.0",
            code_commit="deadbeef",
            ruleset_version="r1",
            vocab_version="v1",
            input_digests=(),
        ),
        fetcher=fetcher,
        captures=InMemoryCaptureStore(),
        claim_sink=InMemoryClaimSink(),
        parameters={"targets": targets},
    )


def _run_source(source_id: str):
    targets = copy.deepcopy(list(live_targets(source_id)))
    return run(get_connector(CONNECTOR)(), _ctx(source_id, targets))


def _claims(report) -> list[Mapping[str, Any]]:
    return [c for c in report.claims if c.get("record_kind") == "claim"]


def _clean(report) -> None:
    """The run recorded no disappearance, refusal or drift disposition."""
    assert not report.disappearances
    assert not report.refusals
    assert not report.drifted


# --- registration + gate posture ----------------------------------------------


def test_tribal_sources_registered_and_routed() -> None:
    """Both screened-lane sources are registry rows routed through
    ``dossier_documents`` — and both joined DOSSIER_SOURCES (the frozen
    crosswalk review applies to their field maps)."""
    for source_id in TRIBAL_SOURCES:
        assert source_id in DOSSIER_SOURCES
        assert CONNECTOR_FOR_SOURCE[source_id] == "dossier_documents"
        record = get(source_id)
        assert record.ingestion_permitted is False
        assert record.rights.spdx.strip().upper() == "UNDETERMINED"
        assert record.rights.redistributable is False
        with pytest.raises(IngestionNotPermitted):
            assert_loadable(record)


def test_screened_allowlists_are_facts_and_citations_only() -> None:
    """The adapter allowlists carry ONLY fact/citation predicates — no person,
    registrant, row-level or device predicate is admitted by construction."""
    for source_id, expected in SCREENED_ALLOWLISTS.items():
        allow = predicate_allowlist(source_id)
        assert allow == expected, f"{source_id}: {sorted(allow)}"
        assert not (allow & FORBIDDEN_PREDICATES)
        assert adapter_config(source_id)["jurisdiction"].startswith("US-TRIBAL:")


def test_crosswalk_still_clean_with_tribal_targets() -> None:
    assert check_crosswalk() == []


# --- the recorded non-target outcome -------------------------------------------


def test_bia_row_query_is_a_recorded_non_target() -> None:
    """The 601-row arcgis_query is enumerated ``screened_lane`` — never a
    ``[[targets]]`` row and never expanded into a fetch target."""
    from connectors.dot_511 import enumerated_outcomes, registry_targets

    rows = {r["id"]: r for r in enumerated_outcomes()}
    row = rows["r11_bia_tribal_leaders_directory"]
    assert row["status"] == "screened_lane"
    assert "TribalLeadership_Directory" in row["url"]
    # The source's own live targets are the dossier clause_fields rows — the
    # camera-registry expander yields nothing (no [[targets]] row names it).
    assert registry_targets("camreg_tribal_all_leaders_directory") == []
    urls = [str(t["url"]) for t in live_targets("camreg_tribal_all_leaders_directory")]
    assert urls and all("/query" not in u for u in urls)


# --- the screened lane over committed stand-ins --------------------------------


def test_bia_layer_metadata_facts_and_citations() -> None:
    report = _run_source("camreg_tribal_all_leaders_directory")
    _clean(report)
    claims = _claims(report)
    assert claims, "the screened lane must emit its facts + citations"
    emitted = {str(c["predicate_id"]) for c in claims}
    assert emitted <= SCREENED_ALLOWLISTS["camreg_tribal_all_leaders_directory"]
    # The two facts: the directory's stated name + the BIA use disclaimer —
    # each verbatim against the captured bytes.
    titles = [c for c in claims if c["predicate_id"] == "title"]
    assert any("Tribal Leaders" in str(c["value"]) for c in titles)
    restrictions = [c for c in claims if c["predicate_id"] == "use_restriction"]
    assert any("navigation" in str(c["raw_value"]) for c in restrictions), (
        "the BIA use-disclaimer literal is the verbatim evidence"
    )


def test_tolc_notice_facts_and_citations() -> None:
    report = _run_source("legis_tribal_tohono_oodham_notice")
    _clean(report)
    claims = _claims(report)
    assert claims
    emitted = {str(c["predicate_id"]) for c in claims}
    assert emitted <= SCREENED_ALLOWLISTS["legis_tribal_tohono_oodham_notice"]
    techs = {str(c["value"]) for c in claims if c["predicate_id"] == "technology"}
    assert techs == {
        "Linear Ground Detection System (LGDS)",
        "Automated Surveillance Tower",
    }
    bodies = {str(c["value"]) for c in claims if c["predicate_id"] == "enacting_body"}
    assert any("Domestic Affairs Committee" in b for b in bodies)


def test_no_person_name_ever_emitted() -> None:
    """S8 lane: nothing that reads as a person name or a per-person fact can
    leave the pipe — the field maps carry no such field, and the shared Part
    VIII guard runs on every claim's raw value."""
    person_patterns = re.compile(
        r"(chairperson|first_name|last_name|contact|phone|email|badge)", re.I
    )
    for source_id in TRIBAL_SOURCES:
        report = _run_source(source_id)
        _clean(report)
        for claim in _claims(report):
            blob = f"{claim.get('value')} {claim.get('raw_value')}"
            assert not person_patterns.search(blob), (source_id, claim["predicate_id"])


def test_targets_stay_bounded() -> None:
    """Each screened source captures exactly ONE bounded document."""
    assert len(live_targets("camreg_tribal_all_leaders_directory")) == 1
    assert len(live_targets("legis_tribal_tohono_oodham_notice")) == 1


# --- schedule of record ---------------------------------------------------------


def test_tribal_cadence_rows_declared_ahead_of_any_flip() -> None:
    """Cadence coverage exists BEFORE a wave-open flip can happen: each
    screened source carries a `[[sources]]` row whose first scheduled fire
    lands after the Wave-A window (day-24 crons, created --paused under R6)."""
    doc = tomllib.loads((_REPO / "ops" / "cadence.toml").read_text())
    rows = {s["id"]: s for s in doc.get("sources", [])}
    for source_id, cron in (
        ("camreg_tribal_all_leaders_directory", "41 7 24 * *"),
        ("legis_tribal_tohono_oodham_notice", "43 7 24 * *"),
    ):
        assert source_id in rows, f"{source_id} has no cadence row"
        assert rows[source_id]["cron"] == cron
        assert rows[source_id]["cadence"] == "monthly"
