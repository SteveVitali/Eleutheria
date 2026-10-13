# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""B4 G1 R4 — stand-in/fixture packet chronology (P34.22b, ADR-146).

A stand-in is committed hand-authored bytes, never a capture. This test file is
the tree-level twin of ``test_no_future_date_literals.py``: where that guard
sweeps ISO literals for future dates, this one sweeps the *stand-in packets* —
the three committed builders and any committed ``*_dossier_packet.json``
artifact that declares a ``capture`` manifest — for the chronology rules:

* every capture stamp a record carries (``retrieved_*`` / ``observed_at`` /
  ``searched_at``, top-level or under ``evidence``) is bounded by its fixture's
  declared ``committed_at``;
* a ``capture_kind: stand-in`` record carries NO retrieval field;
* the packet's ``as_of`` never postdates its build;
* the manifest's declared commit times are the git truth, not typed values;
* the builders REFUSE a ``retrieved_at`` after a fixture commit and an
  ``as_of`` after the build — planted bad packets must fail, not drift.
"""

from __future__ import annotations

import copy
import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from exports.research_dossier import capture_chronology_violations, validate_packet
from support import REPO_ROOT

from ops import dossier_packet as okc
from ops import san_diego_dossier_packet as sd
from ops import tulsa_dossier_packet as tulsa

BUILDERS = (okc, tulsa, sd)

REPORTS = REPO_ROOT / "docs" / "build" / "reports"


def _git_committed(path: str) -> datetime:
    """The UTC committer time of the commit that last touched ``path``."""
    iso = subprocess.check_output(
        ["git", "-C", str(REPO_ROOT), "log", "-1", "--format=%cI", "--", path],
        text=True,
    ).strip()
    return datetime.fromisoformat(iso).astimezone(UTC)


@pytest.mark.parametrize("mod", BUILDERS, ids=lambda m: m.DOSSIER_ID)
def test_declared_fixture_commits_are_the_git_truth(mod) -> None:
    """Every manifest entry's committed_at equals the fixture's real commit."""
    packet = mod.build_packet()
    fixtures = packet["capture"]["fixtures"]
    assert fixtures, "a stand-in packet must declare its fixture manifest"
    for doc_id, fx in fixtures.items():
        declared = datetime.fromisoformat(fx["committed_at"])
        truth = _git_committed(str(fx["path"]))
        assert declared == truth, (
            f"{doc_id}: declared committed_at {declared.isoformat()} != git "
            f"{truth.isoformat()} for {fx['path']} — the manifest is git-derived, "
            "never typed"
        )


@pytest.mark.parametrize("mod", BUILDERS, ids=lambda m: m.DOSSIER_ID)
def test_built_packet_passes_capture_chronology(mod) -> None:
    packet = mod.build_packet()
    assert capture_chronology_violations(packet) == []
    assert validate_packet(packet) == []


@pytest.mark.parametrize("mod", BUILDERS, ids=lambda m: m.DOSSIER_ID)
def test_builder_refuses_retrieval_after_fixture_commit(mod) -> None:
    anchor = datetime.fromisoformat(mod.build_packet()["capture"]["anchor"])
    future = anchor + timedelta(days=30)
    with pytest.raises(ValueError, match="after the fixture"):
        mod.build_packet(retrieved_at=future)


@pytest.mark.parametrize("mod", BUILDERS, ids=lambda m: m.DOSSIER_ID)
def test_builder_refuses_as_of_after_the_build(mod) -> None:
    build = datetime.now(UTC)
    with pytest.raises(ValueError, match="after the build"):
        mod.build_packet(as_of=(build + timedelta(days=30)).date().isoformat())


@pytest.mark.parametrize("mod", BUILDERS, ids=lambda m: m.DOSSIER_ID)
def test_stand_in_records_carry_no_retrieval_date(mod) -> None:
    packet = mod.build_packet()
    stand_ins = [r for r in packet["records"] if r.get("capture_kind") == "stand-in"]
    assert stand_ins, "the packet must carry explicitly labelled stand-ins"
    for r in stand_ins:
        assert r.get("retrieved_at") is None and r.get("retrieved_date") is None
        ev = r.get("evidence") or {}
        assert ev.get("retrieved_at") is None and ev.get("retrieved_date") is None


def test_planted_retrieval_after_commit_fails() -> None:
    """A packet whose record postdates the fixture's commit is refused."""
    packet = okc.build_packet()
    planted = copy.deepcopy(packet)
    fixtures = planted["capture"]["fixtures"]
    doc, fx = next(iter(fixtures.items()))
    bound = datetime.fromisoformat(fx["committed_at"]) + timedelta(days=5)
    record = next(r for r in planted["records"] if r.get("document_id") == doc)
    record.setdefault("evidence", {})["retrieved_date"] = bound.date().isoformat()
    violations = capture_chronology_violations(planted)
    assert violations, "a planted late retrieval must violate"
    assert validate_packet(planted), "validate_packet surfaces the violation"


def test_planted_stand_in_with_retrieval_fails() -> None:
    """A stand-in record that carries a retrieval date is refused."""
    packet = okc.build_packet()
    planted = copy.deepcopy(packet)
    record = next(r for r in planted["records"] if r.get("capture_kind") == "stand-in")
    record["retrieved_date"] = "2001-01-01"  # even a PAST date is fabricated
    assert capture_chronology_violations(planted), (
        "a stand-in carrying any retrieval stamp must violate"
    )


def test_planted_future_as_of_fails() -> None:
    packet = okc.build_packet()
    planted = copy.deepcopy(packet)
    planted["as_of"] = {
        "world": "2999-01-01",  # future-ok: synthetic: planted future as_of
        "belief": "2999-01-01",  # future-ok: synthetic: planted future as_of
    }
    assert capture_chronology_violations(planted)


def test_planted_unbound_document_fails() -> None:
    """A record stamped against an undeclared document is refused."""
    packet = okc.build_packet()
    planted = copy.deepcopy(packet)
    record = dict(planted["records"][0])
    record["document_id"] = "undeclared-document"
    planted["records"] = [record] + list(planted["records"][1:])
    assert capture_chronology_violations(planted)


def test_scenario_as_of_is_not_a_capture_date() -> None:
    """The OKC scenario frame is a declared scenario, never a capture stamp —
    it may sit inside/after fixture dates without violating chronology."""
    packet = okc.build_packet()
    scenario = packet.get("scenario_as_of")
    assert scenario and scenario.get("world")
    # …and it never feeds the as-of pair, which stays the evidence anchor.
    anchor_day = datetime.fromisoformat(packet["capture"]["anchor"]).date().isoformat()
    assert packet["as_of"]["world"] == anchor_day


def _committed_packet_artifacts() -> list[Path]:
    """Committed generated dossier packets that declare a capture manifest."""
    if not REPORTS.is_dir():
        return []
    out: list[Path] = []
    for path in sorted(REPORTS.rglob("*_dossier_packet.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and (data.get("capture") or {}).get("fixtures"):
            out.append(path)
    return out


def test_committed_packet_artifacts_pass_chronology() -> None:
    """Every committed packet artifact that declares stand-in provenance is
    chronology-clean — supersession artifacts included (P34.22b)."""
    artifacts = _committed_packet_artifacts()
    assert artifacts, "expected at least one committed packet with a capture manifest"
    for path in artifacts:
        packet = json.loads(path.read_text(encoding="utf-8"))
        assert capture_chronology_violations(packet) == [], path


def test_web_research_dossier_fixture_is_a_declared_stand_in() -> None:
    """The web fixture carries the stand-in posture — no retrieval dates."""
    src = (REPO_ROOT / "web" / "src" / "lib" / "research-dossier-fixture.ts").read_text(
        encoding="utf-8"
    )
    assert 'capture_kind: "stand-in"' in src
    assert 'kind: "stand-in"' in src
    assert 'retrieved_date: "' not in src, (
        "a stand-in fixture never carries a retrieval date VALUE "
        "(a withheld ledger row's explicit null is fine)"
    )
