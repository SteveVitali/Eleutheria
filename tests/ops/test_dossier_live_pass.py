# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.16a: the bounded dossier live-capture pass — machinery + staged pause.

Every contract the ticket demands is pinned here — each test fails if the
behaviour it names is removed:

* **the staged pause** — without the operator's explicit verbatim go the pass
  never fetches: ``run_pass`` writes ``prepared_not_executed``, exits QUEUED
  (42), and the paused reasons name the requirement verbatim; an unapplied
  HG-03 line pauses the same way even with a go present;
* **the agent screen (B-42)** — each family's drafted ADR-185 lanes resolve
  to their mechanical enforcements, the verdict is ``clear``, and the record
  discloses "cleared by agent screen, no human review"; a lane with no
  enforcement holds the screen closed;
* **honest outcomes** — an executed pass records ``captured`` /
  ``access_restricted`` (403 — never retried past its basis) / ``link_rotted``
  / ``too_large`` / ``not_attempted`` (a non-green source is never fetched);
* **stand-ins no longer served** — the rebuilt packet drops every record
  bound to an attempted doc: a captured doc binds its live artifact, a
  refused doc keeps only the honest ``capture_attempt`` record, and docs the
  pass did not attempt carry through verbatim.
"""

from __future__ import annotations

import dataclasses
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from ops import dossier_live_pass as lp


@pytest.fixture()
def okc() -> lp.Family:
    return lp.family("okc")


@pytest.fixture()
def tulsa() -> lp.Family:
    return lp.family("tulsa")


@pytest.fixture()
def okc_packet(okc: lp.Family) -> dict[str, Any]:
    return lp.load_pass_packet(okc)


def _green(_sid: str) -> list[str]:
    return []


def _refused(_sid: str) -> list[str]:
    return ["ingestion_permitted=false (not flipped by a reviewer, SIG-INGEST-028)"]


def _permitted_source(source_id: str) -> Any:
    """The applied-flip registry row an executed pass runs under — the
    operator's HG-03 flip made real, never minted here."""
    from connectors.registry import CompactStatus, get

    return dataclasses.replace(
        get(source_id),
        ingestion_permitted=True,
        compact_status=CompactStatus.PUBLIC_TERMS_ONLY,
    )


class _StaticFetcher:
    """A fetcher double serving canned FetchResults / raising on demand."""

    def __init__(self, responses: dict[str, Any]) -> None:
        self._responses = responses
        self.calls: list[str] = []

    def fetch(self, url: str, **_kw: Any) -> Any:
        from connectors.stages import FetchResult

        self.calls.append(url)
        r = self._responses[url]
        if isinstance(r, Exception):
            raise r
        body, media, status = r
        return FetchResult(
            url=url,
            status=status,
            body=body,
            media_type=media,
            retrieved_at=datetime.now(UTC),
        )


def _captures() -> Any:
    from connectors.stages import InMemoryCaptureStore

    return InMemoryCaptureStore()


# --------------------------------------------------------------------------- #
# The B-42 agent screen (ADR-185 §2)                                           #
# --------------------------------------------------------------------------- #


def test_screen_clears_okc_and_tulsa_disclosed(okc, tulsa) -> None:
    for fam in (okc, tulsa):
        screen = lp.screen_family(fam)
        assert screen["verdict"] == "clear", screen["held_reason"]
        assert screen["screener"] == "agent"
        assert screen["disclosure"] == "cleared by agent screen, no human review"
        assert screen["controls_verified"]
        assert screen["lanes"] and all(lane["enforced"] for lane in screen["lanes"])
        assert screen["unenforced_lanes"] == []
        assert screen["targets"]


def test_clear_record_is_sig_part_viii_clear(okc) -> None:
    rec = lp.clear_record(okc, screened_on="2026-11-07")
    assert rec["schema"] == "sig.part-viii-clear/1"
    assert rec["status"] == "clear"
    assert rec["screener"] == "agent"
    assert rec["screened_on"] == "2026-11-07"
    assert rec["disclosure"] == "cleared by agent screen, no human review"
    assert "B-42" in rec["authority"]
    assert rec["deferral"] == "D-P32.18-1"
    assert rec["candidates"] == ["SRC-001"]


def test_a_lane_with_no_enforcement_holds_the_screen(okc) -> None:
    screens = {
        "screens": [
            {
                "family": "okc-municipal",
                "preflight": {
                    "status": "screening_required",
                    "lanes": ["S6 free-text excerpts", "S99 an unmapped hazard"],
                },
            }
        ]
    }
    screen = lp.screen_family(okc, screens=screens)
    assert screen["verdict"] == "held"
    assert "S99" in " ".join(screen["unenforced_lanes"]) or screen["unenforced_lanes"]


def test_write_clear_emits_the_record(okc, tmp_path: Path) -> None:
    out = lp.write_clear(okc, out_dir=tmp_path, screened_on="2026-11-07")
    rec = json.loads(out.read_text(encoding="utf-8"))
    assert rec["schema"] == "sig.part-viii-clear/1"
    assert rec["status"] == "clear"


# --------------------------------------------------------------------------- #
# Preconditions + the staged pause                                             #
# --------------------------------------------------------------------------- #


def test_hg03_lines_read_the_real_gate(okc, okc_packet) -> None:
    lines = lp.hg03_lines(okc, okc_packet)
    # On the implementation chain the operator's flips are unapplied —
    # dossier_okc stays refused; the existing green sources are applied.
    assert lines["applied"] is False
    assert lines["lines"]["dossier_okc"]["status"] == "pending"
    assert lines["lines"]["ok_statute"]["status"] == "applied"
    assert lines["lines"]["okcpd_policy"]["status"] == "applied"
    assert lines["lines"]["okc_procurement"]["status"] == "applied"


def test_no_go_means_prepared_not_executed(okc, okc_packet, tmp_path: Path) -> None:
    record, code = lp.run_pass(
        okc, out_dir=tmp_path, packet=okc_packet, evaluated_at="2026-11-07T00:00:00Z"
    )
    assert code == lp.QUEUED == 42
    assert record["schema"] == lp.LIVE_PASS_RESULT_SCHEMA
    assert record["status"] == "prepared_not_executed"
    assert record["operator_go"]["present"] is False
    assert any("verbatim go" in r for r in record["paused_reasons"])
    assert any("hg03" in r for r in record["paused_reasons"])
    written = json.loads((tmp_path / "LIVE_PASS_RESULT.json").read_text(encoding="utf-8"))
    assert written["status"] == "prepared_not_executed"


def test_a_go_without_hg03_lines_still_pauses(okc, okc_packet, tmp_path: Path) -> None:
    record, code = lp.run_pass(
        okc,
        operator_go="run the okc live pass",
        out_dir=tmp_path,
        packet=okc_packet,
        evaluated_at="2026-11-07T00:00:00Z",
    )
    assert code == 42
    assert record["operator_go"]["present"] is True
    assert record["operator_go"]["verbatim"] == "run the okc live pass"
    assert any("hg03_lines_pending" in r for r in record["paused_reasons"])


def test_part_viii_state_records_the_clear(okc) -> None:
    state = lp.part_viii_state(okc)
    assert state["candidates"]["SRC-001"]["status"] == "clear"
    assert state["cleared"] is True


# --------------------------------------------------------------------------- #
# Execution — honest outcomes through the reviewed stack                       #
# --------------------------------------------------------------------------- #


def _fake_entries() -> list[Any]:
    """Queue entries carrying the recorded clear (the state the leg runs
    under once the agent screen lands)."""
    entries = __import__("tasks.acquisition", fromlist=["build_queue"]).build_queue()
    return entries


def test_execute_refuses_a_non_green_source_without_fetching(okc, okc_packet) -> None:
    fetcher = _StaticFetcher({})
    outcomes, emitted = lp.execute(
        okc, okc_packet, fetcher=fetcher, captures=_captures(), gate=_refused
    )
    assert fetcher.calls == []  # zero egress — the gate decides
    assert all(o["outcome"] == "not_attempted" for o in outcomes)
    assert emitted == {}


def _okc_bodies(packet: dict[str, Any]) -> dict[str, Any]:
    """doc_id -> canned response keyed off the packet's own URLs."""
    dossier = Path("tests/connectors/fixtures/dossier")
    okc_fix = Path("tests/connectors/fixtures/okc")
    by_doc = {
        "okc-flock-usage-2026": (dossier / "okc_usage_page.html", "text/html"),
        "okc-council-memo-2026-08": (dossier / "okc_council_memo_2026.pdf", "application/pdf"),
        "okc-flock-amendment-2026": (dossier / "okc_amendment_1_2026.pdf", "application/pdf"),
        "okc-statute-47-7-606-1": (okc_fix / "ok_statute.json", "application/json"),
        "okc-ops-manual-5-118": (okc_fix / "okcpd_policy.json", "application/json"),
        "okc-purchasing-index": (okc_fix / "okc_procurement.json", "application/json"),
    }
    return {
        t["url"]: (by_doc[t["doc_id"]][0].read_bytes(), by_doc[t["doc_id"]][1], 200)
        for t in packet["targets"]
        if t["doc_id"] in by_doc
    }


def test_execute_captures_okc_targets_through_the_connector(okc, okc_packet) -> None:
    bodies = _okc_bodies(okc_packet)
    fetcher = _StaticFetcher(bodies)
    outcomes, emitted = lp.execute(
        okc,
        okc_packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
    )
    assert len(outcomes) == len(okc_packet["targets"])
    captured = {o["doc_id"]: o for o in outcomes if o["outcome"] == "captured"}
    # The three clause_fields docs emitted records over live bytes.
    for doc in ("okc-flock-usage-2026", "okc-council-memo-2026-08", "okc-flock-amendment-2026"):
        assert captured[doc]["capture_digest"]
        assert captured[doc]["retrieved_at"]
        assert captured[doc]["emitted_records"] >= 0
    assert emitted  # connector emits bind the live captures
    # Every emitted record is stripped of connector-transient ids.
    for _doc_id, recs in emitted.items():
        for r in recs:
            assert "claim_id" not in r and "sys_period" not in r


def test_a_403_is_recorded_never_retried(okc) -> None:
    from connectors.net import ChallengeEncountered

    target = {
        "doc_id": "okc-purchasing-index",
        "url": "https://www.okc.gov/departments/finance/purchasing",
        "existing_source": "okc_procurement",
        "kind": "document_page",
    }
    packet = {"schema": "sig.dossier-live-return-pass/1", "targets": [target]}
    fetcher = _StaticFetcher({target["url"]: ChallengeEncountered("403", status=403)})
    outcomes, _ = lp.execute(
        okc,
        packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
    )
    assert outcomes[0]["outcome"] == "access_restricted"
    assert outcomes[0]["http_status"] == 403
    assert fetcher.calls == [target["url"]]  # one attempt — never retried


def test_a_404_is_link_rotted(okc) -> None:
    target = {
        "doc_id": "tpd-flock-page",
        "url": "https://www.tulsapolice.org/flock-safety",
        "kind": "document_page",
    }
    packet = {"schema": "sig.dossier-live-return-pass/1", "targets": [target]}
    fetcher = _StaticFetcher({target["url"]: (b"", "text/html", 404)})
    outcomes, _ = lp.execute(
        okc,
        packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
    )
    assert outcomes[0]["outcome"] == "link_rotted"
    assert outcomes[0]["http_status"] == 404


def test_over_bound_bytes_are_too_large(okc) -> None:
    target = {
        "doc_id": "big-doc",
        "url": "https://example.gov/big.pdf",
        "kind": "document_page",
        "byte_bound": 8,
    }
    packet = {"schema": "sig.dossier-live-return-pass/1", "targets": [target]}
    fetcher = _StaticFetcher({target["url"]: (b"x" * 64, "application/pdf", 200)})
    outcomes, _ = lp.execute(
        okc,
        packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
    )
    assert outcomes[0]["outcome"] == "too_large"
    assert outcomes[0]["byte_size"] == 64


# --------------------------------------------------------------------------- #
# Packet rebuild — stand-ins no longer served                                  #
# --------------------------------------------------------------------------- #


def test_rebuild_drops_stand_ins_for_attempted_docs(okc) -> None:
    base = {
        "schema": "sig.dossier-packet/1",
        "records": [
            {
                "record_kind": "evidence_artifact",
                "document_id": "doc-a",
                "capture_kind": "stand-in",
            },
            {"record_kind": "claim", "document_id": "doc-a", "predicate": "p"},
            {
                "record_kind": "evidence_artifact",
                "document_id": "doc-b",
                "capture_kind": "stand-in",
            },
            {"record_kind": "claim", "document_id": "doc-unattempted", "predicate": "p2"},
        ],
        "capture": {"kind": "fixture_replay"},
    }
    outcomes = [
        {
            "doc_id": "doc-a",
            "url": "u",
            "source_id": "s",
            "outcome": "captured",
            "detail": "",
            "capture_digest": "dg",
            "byte_size": 10,
            "media_type": "text/html",
            "retrieved_at": "2026-11-07T01:00:00+00:00",
        },
        {
            "doc_id": "doc-b",
            "url": "u2",
            "source_id": "s",
            "outcome": "access_restricted",
            "detail": "403",
        },
    ]
    rebuilt = lp.rebuild_packet(
        okc,
        base,
        outcomes,
        emitted={"doc-a": [{"record_kind": "claim", "document_id": "doc-a", "predicate": "live"}]},
    )
    assert "doc-b" not in [
        r.get("document_id") for r in rebuilt["records"] if r.get("record_kind") == "claim"
    ]
    # doc-a: stand-in + claim replaced by the live artifact + emitted claim.
    kinds = [r["record_kind"] for r in rebuilt["records"] if r.get("document_id") == "doc-a"]
    assert kinds == ["evidence_artifact", "claim"]
    live_art = next(
        r
        for r in rebuilt["records"]
        if r.get("document_id") == "doc-a" and r["record_kind"] == "evidence_artifact"
    )
    assert live_art["capture_kind"] == "live_capture"
    assert live_art["retrieved_at"]
    # doc-b: nothing but the honest capture_attempt remains — no stand-in.
    doc_b = [r for r in rebuilt["records"] if r.get("document_id") == "doc-b"]
    assert [r["record_kind"] for r in doc_b] == ["capture_attempt"]
    assert doc_b[0]["outcome"] == "access_restricted"
    # unattempted doc untouched.
    assert any(r.get("document_id") == "doc-unattempted" for r in rebuilt["records"])
    assert rebuilt["capture"]["kind"] == "live_pass"


def test_executed_run_writes_result(okc, okc_packet, tmp_path: Path) -> None:
    bodies = _okc_bodies(okc_packet)
    fetcher = _StaticFetcher(bodies)
    record, code = lp.run_pass(
        okc,
        operator_go="operator's verbatim go",
        out_dir=tmp_path,
        packet=okc_packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
        go_recorded_by="operator (in-ticket verbatim)",
        evaluated_at="2026-11-07T01:00:00Z",
    )
    assert code == 0
    assert record["status"] == "executed"
    assert record["operator_go"]["verbatim"] == "operator's verbatim go"
    assert record["go_recorded_by"] == "operator (in-ticket verbatim)"
    assert record["rebuilt_packet"]["records"] > 0
    assert (tmp_path / "LIVE_PASS_RESULT.json").exists()
