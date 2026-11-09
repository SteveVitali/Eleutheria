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
def san_diego() -> lp.Family:
    return lp.family("san-diego")


@pytest.fixture()
def pilot() -> lp.Family:
    return lp.family("acq-pilot")


@pytest.fixture()
def okc_packet(okc: lp.Family) -> dict[str, Any]:
    return lp.load_pass_packet(okc)


@pytest.fixture()
def sd_packet(san_diego: lp.Family) -> dict[str, Any]:
    return lp.load_pass_packet(san_diego)


@pytest.fixture()
def pilot_packet(pilot: lp.Family) -> dict[str, Any]:
    return lp.load_pass_packet(pilot)


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


# --------------------------------------------------------------------------- #
# P37.16b — the last two families (san-diego dossier + the acquisition pilot)   #
# --------------------------------------------------------------------------- #


def test_screen_clears_san_diego_disclosed(san_diego: lp.Family) -> None:
    screen = lp.screen_family(san_diego)
    assert screen["verdict"] == "clear", screen["held_reason"]
    assert screen["screener"] == "agent"
    assert screen["disclosure"] == "cleared by agent screen, no human review"
    assert screen["controls_verified"]
    assert screen["members"] == ["SRC-003", "SRC-004", "SRC-005"]
    # S9's Ubicquia signature-block lane resolves to a mechanical enforcement.
    assert all(lane["enforced"] for lane in screen["lanes"])
    assert len(screen["targets"]) == 9


def test_screen_clears_both_pilot_sub_families(pilot: lp.Family) -> None:
    assert pilot.all_screen_families == ("oklahoma-state", "california-state-auditor")
    for name in pilot.all_screen_families:
        screen = lp.screen_family(pilot, screen_family_name=name)
        assert screen["verdict"] == "clear", (name, screen["held_reason"])
        assert screen["family"] == name
        assert screen["targets"]  # scoped to the sub-family's targets
        assert all(lane["enforced"] for lane in screen["lanes"])
    okc_screen = lp.screen_family(pilot, screen_family_name="oklahoma-state")
    ca_screen = lp.screen_family(pilot, screen_family_name="california-state-auditor")
    assert {t["doc_id"] for t in okc_screen["targets"]} == {
        "src-007-target-1",
        "src-007-target-2",
        "src-006-target-1",
        "src-006-target-2",
    }
    assert {t["doc_id"] for t in ca_screen["targets"]} == {
        "src-011-target-1",
        "src-011-target-2",
    }


def test_pilot_clear_records_are_per_screen_and_disclosed(pilot: lp.Family, tmp_path: Path) -> None:
    paths = lp.write_clears(pilot, out_dir=tmp_path, screened_on="2026-11-08")
    assert sorted(p.name for p in paths) == [
        "PART_VIII_CLEAR.california-state-auditor.json",
        "PART_VIII_CLEAR.oklahoma-state.json",
    ]
    recs = {
        json.loads(p.read_text(encoding="utf-8"))["family"]: json.loads(
            p.read_text(encoding="utf-8")
        )
        for p in paths
    }
    for _name, rec in recs.items():
        assert rec["schema"] == "sig.part-viii-clear/1"
        assert rec["status"] == "clear"
        assert rec["deferral"] == "D-P32.21-1"
        assert rec["disclosure"] == "cleared by agent screen, no human review"
    assert recs["oklahoma-state"]["candidates"] == ["SRC-006", "SRC-007"]
    assert recs["california-state-auditor"]["candidates"] == ["SRC-011"]


def test_pilot_packet_shape_and_source_resolution(
    pilot: lp.Family, pilot_packet: dict[str, Any]
) -> None:
    assert pilot_packet["schema"] == lp.ACQ_PILOT_PASS_SCHEMA
    rows = {t["doc_id"]: t for t in lp.packet_targets(pilot, pilot_packet)}
    # E4-B6 — each candidate rides its gated same_source registry row; the
    # OSCN statute URL rides the green ok_statute row's recorded basis (E4-B5).
    assert rows["src-006-target-1"]["source_id"] == "ok_omes_contracts"
    assert rows["src-006-target-2"]["source_id"] == "ok_omes_contracts"
    assert rows["src-007-target-1"]["source_id"] == "ok_dac_uved"
    assert rows["src-007-target-2"]["source_id"] == "ok_statute"
    assert rows["src-011-target-1"]["source_id"] == "ca_state_auditor"
    assert rows["src-011-target-2"]["source_id"] == "ca_state_auditor"
    assert lp.family_sources(pilot, pilot_packet) == [
        "ok_dac_uved",
        "ok_statute",
        "ok_omes_contracts",
        "ca_state_auditor",
    ]


def test_hg03_lines_pilot_and_san_diego(
    san_diego: lp.Family,
    sd_packet: dict[str, Any],
    pilot: lp.Family,
    pilot_packet: dict[str, Any],
) -> None:
    sd = lp.hg03_lines(san_diego, sd_packet)
    assert sd["applied"] is False
    assert sd["lines"]["dossier_san_diego"]["status"] == "pending"
    p = lp.hg03_lines(pilot, pilot_packet)
    assert p["applied"] is False
    # The green source's recorded basis reads applied — nothing re-asks it.
    assert p["lines"]["ok_statute"]["status"] == "applied"
    for sid in ("ok_dac_uved", "ok_omes_contracts", "ca_state_auditor"):
        assert p["lines"][sid]["status"] == "pending"


def test_part_viii_state_records_all_six_new_clears(san_diego: lp.Family, pilot: lp.Family) -> None:
    sd = lp.part_viii_state(san_diego)
    assert sd["cleared"] is True
    assert set(sd["candidates"]) == {"SRC-003", "SRC-004", "SRC-005"}
    p = lp.part_viii_state(pilot)
    assert p["cleared"] is True
    assert set(p["candidates"]) == {"SRC-006", "SRC-007", "SRC-011"}


def test_no_go_means_prepared_not_executed_for_the_last_two(
    san_diego: lp.Family,
    sd_packet: dict[str, Any],
    pilot: lp.Family,
    pilot_packet: dict[str, Any],
    tmp_path: Path,
) -> None:
    for fam, pkt, name in (
        (san_diego, sd_packet, "san-diego"),
        (pilot, pilot_packet, "acq-pilot"),
    ):
        dest = tmp_path / name
        record, code = lp.run_pass(
            fam,
            out_dir=dest,
            packet=pkt,
            evaluated_at="2026-11-08T00:00:00Z",
        )
        assert code == lp.QUEUED == 42
        assert record["status"] == "prepared_not_executed"
        assert record["deferral"] == fam.deferral
        assert any("verbatim go" in r for r in record["paused_reasons"])
        assert any("hg03" in r for r in record["paused_reasons"])
        written = json.loads((dest / "LIVE_PASS_RESULT.json").read_text(encoding="utf-8"))
        assert written["status"] == "prepared_not_executed"


def test_pilot_targets_record_not_attempted_rows(
    pilot: lp.Family, pilot_packet: dict[str, Any], tmp_path: Path
) -> None:
    record, _ = lp.run_pass(
        pilot, out_dir=tmp_path, packet=pilot_packet, evaluated_at="2026-11-08T00:00:00Z"
    )
    assert len(record["targets"]) == 6
    assert {t["doc_id"] for t in record["targets"]} == {
        "src-006-target-1",
        "src-006-target-2",
        "src-007-target-1",
        "src-007-target-2",
        "src-011-target-1",
        "src-011-target-2",
    }
    assert all(t["outcome"] == "not_attempted" for t in record["targets"])


# --- honest outcomes on the new shapes ----------------------------------------


def test_metadata_only_preflight_never_fetches(
    san_diego: lp.Family, sd_packet: dict[str, Any]
) -> None:
    """SRC-027's workbook path is rejected permanently (E4-B3) — the
    metadata_only_preflight target never fetches, even on a green gate."""
    fetcher = _StaticFetcher({})
    outcomes, _ = lp.execute(
        san_diego,
        sd_packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_refused,
        source_resolver=_permitted_source,
    )
    meta = next(o for o in outcomes if o["doc_id"] == "sd-network-audit-links")
    assert meta["outcome"] == "metadata_only"
    assert "E4-B3" in meta["detail"]
    assert fetcher.calls == []  # zero egress — every other target is gated too


def test_pilot_non_green_sources_never_fetch(
    pilot: lp.Family, pilot_packet: dict[str, Any]
) -> None:
    fetcher = _StaticFetcher({})
    outcomes, emitted = lp.execute(
        pilot,
        pilot_packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_refused,
        source_resolver=_permitted_source,
    )
    assert fetcher.calls == []
    assert all(o["outcome"] == "not_attempted" for o in outcomes)
    assert emitted == {}


def test_excluded_candidate_never_fetches(pilot: lp.Family) -> None:
    """A target naming an excluded candidate is refused before the gate."""
    packet = {
        "schema": lp.ACQ_PILOT_PASS_SCHEMA,
        "families": [
            {
                "family": "oklahoma-state",
                "candidate_ids": ["SRC-008"],
                "excluded_candidate_ids": ["SRC-008"],
                "registered_source": "ok_dac_uved",
                "document_cap": 10,
                "targets": [
                    {
                        "candidate_id": "SRC-008",
                        "doc_id": "src-008-target-1",
                        "kind": "document_capture",
                        "url": "https://example.gov/excluded",
                    }
                ],
            }
        ],
    }
    fetcher = _StaticFetcher({})
    outcomes, _ = lp.execute(
        pilot,
        packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
    )
    assert outcomes[0]["outcome"] == "not_attempted"
    assert "excluded" in outcomes[0]["detail"]
    assert fetcher.calls == []


def test_packet_integrity_fails_closed(
    pilot: lp.Family, pilot_packet: dict[str, Any], tmp_path: Path
) -> None:
    assert lp.packet_integrity(pilot, pilot_packet)["ok"] is True
    over = {
        "schema": lp.ACQ_PILOT_PASS_SCHEMA,
        "families": [
            {
                "family": "oklahoma-state",
                "candidate_ids": ["SRC-007"],
                "excluded_candidate_ids": ["SRC-007"],
                "registered_source": "ok_dac_uved",
                "document_cap": 1,
                "targets": [
                    {
                        "candidate_id": "SRC-007",
                        "doc_id": "a",
                        "kind": "document_capture",
                        "url": "https://example.gov/a",
                    },
                    {
                        "candidate_id": "SRC-007",
                        "doc_id": "b",
                        "kind": "document_capture",
                        "url": "https://example.gov/b",
                    },
                ],
            }
        ],
    }
    integrity = lp.packet_integrity(pilot, over)
    assert integrity["ok"] is False
    assert any("document_cap" in p for p in integrity["problems"])
    assert any("excluded" in p for p in integrity["problems"])
    record, code = lp.run_pass(
        pilot,
        operator_go="go",
        out_dir=tmp_path,
        packet=over,
        gate=_green,
        entries=_fake_entries(),
        evaluated_at="2026-11-08T00:00:00Z",
    )
    assert code == lp.QUEUED
    assert any("packet_integrity" in r for r in record["paused_reasons"])


def test_byte_bound_exception_still_caps(san_diego: lp.Family, sd_packet) -> None:
    """E4-B4's per-target exception is not an approved method — the adapter
    bound still caps the ~16 MB PAB recommendation (``too_large``, honest)."""
    pab = next(t for t in sd_packet["targets"] if t["doc_id"] == "sd-pab-recommendation-2025")
    assert "byte_bound_exception" in pab
    bound = lp._byte_cap(san_diego, pab)
    assert bound == 1048576
    target = {
        "doc_id": "sd-pab-recommendation-2025",
        "url": "https://www.sandiego.gov/sites/default/files/pab-final-recommendation-alpr-2025.pdf",
        "kind": "document_page",
        "byte_bound_exception": pab["byte_bound_exception"],
    }
    packet = {"schema": lp.DOSSIER_PASS_SCHEMA, "targets": [target]}
    fetcher = _StaticFetcher({target["url"]: (b"x" * (bound + 64), "application/pdf", 200)})
    outcomes, _ = lp.execute(
        san_diego,
        packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
    )
    assert outcomes[0]["outcome"] == "too_large"
    assert outcomes[0]["byte_size"] == bound + 64


def test_unreachable_retries_within_the_declared_budget(pilot: lp.Family) -> None:
    """A transport-level failure retries up to the packet's declared bounded
    budget — a refusal or a 4xx is still recorded, never retried."""
    import httpx

    url = "https://oklahoma.gov/dac/about/staff/about-the-uved-program.html"
    packet = {
        "schema": lp.ACQ_PILOT_PASS_SCHEMA,
        "families": [
            {
                "family": "oklahoma-state",
                "candidate_ids": ["SRC-007"],
                "registered_source": "ok_dac_uved",
                "document_cap": 10,
                "retry_budget_per_target": 2,
                "targets": [
                    {
                        "candidate_id": "SRC-007",
                        "doc_id": "src-007-target-1",
                        "kind": "document_capture",
                        "url": url,
                    }
                ],
            }
        ],
    }

    class _Flaky:
        def __init__(self) -> None:
            self.calls = 0

        def fetch(self, u: str, **_kw: Any) -> Any:
            from connectors.stages import FetchResult

            self.calls += 1
            if self.calls < 3:
                raise httpx.ConnectError("refused")
            return FetchResult(
                url=u,
                status=200,
                body=b"<html>uved</html>",
                media_type="text/html",
                retrieved_at=datetime.now(UTC),
            )

    flaky = _Flaky()
    outcomes, _ = lp.execute(
        pilot,
        packet,
        fetcher=flaky,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
    )
    assert outcomes[0]["outcome"] == "captured"
    assert outcomes[0]["attempts"] == 3  # 1 + retry_budget 2
    assert outcomes[0]["elapsed_seconds"] >= 0

    class _Down:
        def __init__(self) -> None:
            self.calls = 0

        def fetch(self, u: str, **_kw: Any) -> Any:
            self.calls += 1
            raise httpx.ConnectError("refused")

    down = _Down()
    outcomes, _ = lp.execute(
        pilot,
        packet,
        fetcher=down,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
    )
    assert outcomes[0]["outcome"] == "unreachable"
    assert outcomes[0]["attempts"] == 3
    assert down.calls == 3


def test_san_diego_executed_pass_rebuilds_packet(
    san_diego: lp.Family, sd_packet: dict[str, Any], tmp_path: Path
) -> None:
    """The four registered docs replay through the dossier_documents connector
    over real (fixture-served) bytes; leads go fetch-only; the metadata-only
    target is never fetched."""
    dossier = Path("tests/connectors/fixtures/dossier")
    bodies: dict[str, Any] = {
        "https://www.sandiego.gov/sites/default/files/sdpd-annual-surveillance-report-2025.pdf": (
            (dossier / "sd_asr_2025_vigilant.pdf").read_bytes(),
            "application/pdf",
            200,
        ),
        "https://www.sandiego.gov/sites/default/files/cosd-public-safety-agreement-ubicquia.pdf": (
            (dossier / "sd_ubicquia_agreement_2023.pdf").read_bytes(),
            "application/pdf",
            200,
        ),
        "https://www.sandiego.gov/police/data-transparency/technology": (
            (dossier / "sd_technology_index.html").read_bytes(),
            "text/html",
            200,
        ),
        "https://www.sandiego.gov/pab/reports": (
            (dossier / "sd_pab_index.html").read_bytes(),
            "text/html",
            200,
        ),
        "https://www.sandiego.gov/police/data-transparency/technology?tech=alpr": (
            b"<html>alpr program</html>",
            "text/html",
            200,
        ),
        "https://www.sandiego.gov/sites/default/files/alpr-use-policy.pdf": (
            b"%PDF-1.4 policy",
            "application/pdf",
            200,
        ),
        "https://www.sandiego.gov/sites/default/files/pab-final-recommendation-alpr-2025.pdf": (
            b"%PDF-1.4 rec",
            "application/pdf",
            200,
        ),
        "https://www.sandiego.gov/city-clerk/officialdocs/council-documents": (
            b"<html>clerk</html>",
            "text/html",
            200,
        ),
    }
    fetcher = _StaticFetcher(bodies)
    record, code = lp.run_pass(
        san_diego,
        operator_go="operator's verbatim go",
        out_dir=tmp_path,
        packet=sd_packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
        go_recorded_by="operator (in-ticket verbatim)",
        evaluated_at="2026-11-07T01:00:00Z",
    )
    assert code == 0
    assert record["status"] == "executed"
    assert record["rebuilt_packet"]["records"] > 0
    by_doc = {t["doc_id"]: t for t in record["targets"]}
    assert by_doc["sd-asr-2025-vigilant"]["outcome"] == "captured"
    assert by_doc["sd-asr-2025-vigilant"]["capture_digest"]
    assert by_doc["sd-alpr-program-page"]["outcome"] == "captured"
    assert by_doc["sd-network-audit-links"]["outcome"] == "metadata_only"
    assert by_doc["sd-network-audit-links"].get("capture_digest") is None
    # The metadata-only URL was fetched once — for the ALPR program lead only.
    assert (
        fetcher.calls.count(
            "https://www.sandiego.gov/police/data-transparency/technology?tech=alpr"
        )
        == 1
    )
    assert all("elapsed_seconds" in t for t in record["targets"])


def test_pilot_executed_run_emits_funnel_overlay(
    pilot: lp.Family, pilot_packet: dict[str, Any], tmp_path: Path
) -> None:
    """An executed pilot pass records the honest outcome set + the measured
    funnel overlay — no dossier packet, no stand-ins to retire."""
    # The statute page carries the reviewed clause map's literals verbatim —
    # the ok_statute connector slices § 7-606.1 out of real page text.
    statute_page = (
        "<html><body><p>Oklahoma Statutes</p><p>§ 7-606.1 (OSCN 2026)</p>"
        "<p>shall not be used by any individual or agency for purposes other "
        "than enforcement of the Compulsory Insurance Law or as otherwise "
        "permitted by law</p><p>shall not be implemented until such time "
        "that the Insurance Department verifies that the following "
        "conditions have been met</p></body></html>"
    ).encode()
    bodies: dict[str, Any] = {
        "https://oklahoma.gov/dac/about/staff/about-the-uved-program.html": (
            b"<html>uved program</html>",
            "text/html",
            200,
        ),
        "https://www.oscn.net/applications/oscn/DeliverDocument.asp?CiteID=478582": (
            statute_page,
            "text/html",
            200,
        ),
        (
            "https://oklahoma.gov/omes/divisions/central-purchasing/"
            "agency-resources/statewide-contracts.html"
        ): (
            b"<html>contracts</html>",
            "text/html",
            200,
        ),
        "https://oklahoma.gov/omes/services/purchasing/solicitations/0900000569.html": (
            b"<html>solicitation</html>",
            "text/html",
            200,
        ),
        "https://information.auditor.ca.gov/reports/2019-118/index.html": (
            b"<html>audit</html>",
            "text/html",
            200,
        ),
        "https://information.auditor.ca.gov/reports/2019-118/surveys.html": (
            b"<html>surveys</html>",
            "text/html",
            200,
        ),
    }
    fetcher = _StaticFetcher(bodies)
    record, code = lp.run_pass(
        pilot,
        operator_go="operator's verbatim go",
        out_dir=tmp_path,
        packet=pilot_packet,
        fetcher=fetcher,
        captures=_captures(),
        gate=_green,
        source_resolver=_permitted_source,
        go_recorded_by="operator (in-ticket verbatim)",
        evaluated_at="2026-11-07T01:00:00Z",
    )
    assert code == 0
    assert record["status"] == "executed"
    assert "rebuilt_packet" not in record  # no dossier packet for the pilot
    overlay = record["funnel_overlay"]
    assert set(overlay["sub_families"]) == {"oklahoma-state", "california-state-auditor"}
    assert overlay["sub_families"]["oklahoma-state"]["capture"]["attempted"] == 4
    assert overlay["sub_families"]["california-state-auditor"]["capture"]["attempted"] == 2
    assert overlay["sub_families"]["oklahoma-state"]["capture"]["captured"] == 4
    assert overlay["sub_families"]["california-state-auditor"]["capture"]["captured"] == 2
    assert overlay["basis"].startswith("real captures")
    by_doc = {t["doc_id"]: t for t in record["targets"]}
    assert by_doc["src-007-target-2"]["outcome"] == "captured"
    # The statute doc rode the ok_statute connector — claims emitted over
    # live bytes; fetch-only leads mint nothing.
    assert by_doc["src-007-target-2"].get("emitted_records", 0) > 0
    assert "emitted_records" not in by_doc["src-007-target-1"]
    assert by_doc["src-006-target-1"]["candidate_id"] == "SRC-006"
    assert by_doc["src-011-target-1"]["sub_family"] == "california-state-auditor"
