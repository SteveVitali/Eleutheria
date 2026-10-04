# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.26 — the ``sig-ops disposition`` verb + flagged-org census (pure layer).

ADR-124 + ADR-159 (G2-ADR124 + D-K2-1 [A-10], SIG-TRUST-006 / SIG-ONTO-013 /
SIG-PUB-002 / SIG-STORE-011): the allow verb is dry-run by default, verifies
every ``sig.disposition-list/1`` entry against the spine, and fails closed
with typed refusals; the census emits ids + counts only — a screened label
or literal party value can never reach a committed artifact.
"""

from __future__ import annotations

import json
import re
from typing import Any

import pytest

from ops import cli as ops_cli
from ops import dispositions as disp

_E1 = "11111111-1111-4111-8111-111111111111"
_E2 = "22222222-2222-4222-8222-222222222222"
_E3 = "33333333-3333-4333-8333-333333333333"


def _list_doc(*entries: dict[str, Any], **kw: Any) -> dict[str, Any]:
    return {
        "record_type": disp.DISPOSITION_LIST_SCHEMA,
        "list_id": "test-list",
        "policy_version": "publication-eligibility/1",
        **kw,
        "entries": list(entries),
    }


def _entry(entity_id: str = _E1, registry: str = "wikidata_qid", **kw: Any) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "registry": registry,
        "identifier": {"scheme": disp.REGISTRIES[registry]["scheme"], "value": "Q1"},
        "match_tier": 0,
        **kw,
    }


# --------------------------------------------------------------------------- #
# sig.disposition-list/1 validation
# --------------------------------------------------------------------------- #


def test_load_list_accepts_a_valid_document() -> None:
    lst = disp.load_disposition_list(_list_doc(_entry()))
    assert lst.list_id == "test-list"
    assert lst.policy_version == "publication-eligibility/1"
    assert len(lst.entries) == 1
    e = lst.entries[0]
    assert e.entity_id == _E1 and e.registry == "wikidata_qid"
    assert e.scheme == "wikidata.qid" and e.value == "Q1" and e.match_tier == 0


def test_load_list_sorts_entries_by_entity_id() -> None:
    lst = disp.load_disposition_list(_list_doc(_entry(_E3), _entry(_E1), _entry(_E2)))
    assert [e.entity_id for e in lst.entries] == [_E1, _E2, _E3]


def test_load_list_rejects_wrong_record_type() -> None:
    doc = _list_doc(_entry())
    doc["record_type"] = "sig.something-else/1"
    with pytest.raises(disp.DispositionListError):
        disp.load_disposition_list(doc)


def test_load_list_rejects_unknown_registry() -> None:
    e = {
        "entity_id": _E1,
        "registry": "openstates",
        "identifier": {"scheme": "us.census.geoid", "value": "401234"},
        "match_tier": 0,
    }
    with pytest.raises(disp.DispositionListError, match="registry"):
        disp.load_disposition_list(_list_doc(e))


def test_load_list_rejects_scheme_registry_mismatch() -> None:
    e = _entry(registry="sam_uei")
    e["identifier"] = {"scheme": "wikidata.qid", "value": "Q1"}
    with pytest.raises(disp.DispositionListError, match="scheme"):
        disp.load_disposition_list(_list_doc(e))


def test_load_list_rejects_tier_above_1() -> None:
    """ADR-159 (a): only tier 0–1 match records justify an auto-allow."""
    with pytest.raises(disp.DispositionListError, match="tier"):
        disp.load_disposition_list(_list_doc(_entry(match_tier=2)))


def test_load_list_rejects_bad_entity_id() -> None:
    with pytest.raises(disp.DispositionListError, match="uuid"):
        disp.load_disposition_list(_list_doc(_entry(entity_id="not-a-uuid")))


def test_load_list_rejects_duplicate_identifier_entries() -> None:
    with pytest.raises(disp.DispositionListError, match="duplicate"):
        disp.load_disposition_list(_list_doc(_entry(), _entry()))


def test_load_list_rejects_wrong_policy_version() -> None:
    with pytest.raises(disp.DispositionListError, match="policy_version"):
        disp.load_disposition_list(_list_doc(_entry(), policy_version="publication-eligibility/2"))


# --------------------------------------------------------------------------- #
# --authority / --decided-by validation
# --------------------------------------------------------------------------- #


def test_authority_is_required() -> None:
    with pytest.raises(disp.DispositionListError, match="authority"):
        disp.validate_actor_fields(authority="", decided_by="registry-auto-allow")


def test_decided_by_must_be_a_role_token_never_a_name() -> None:
    for bad in ("Jane Smith", "jane.smith@example.com", "SMITH", "Jane Smith, reviewer"):
        with pytest.raises(disp.DispositionListError, match="decided-by"):
            disp.validate_actor_fields(authority="ADR-159", decided_by=bad)
    for good in ("registry-auto-allow", "adr-159:wikidata_qid", "sig_materialize"):
        disp.validate_actor_fields(authority="ADR-159", decided_by=good)


# --------------------------------------------------------------------------- #
# The person-name screen (K2 §3.4 / ADR-159 (d))
# --------------------------------------------------------------------------- #


def test_screen_flags_person_shaped_names() -> None:
    """The never-a-person rule: two words, no organisation marker -> a name."""
    assert disp.screen_name("John Smith") == disp.SCREEN_FLAG_PERSON_NAME
    assert disp.screen_name("Sheriff Doe") == disp.SCREEN_FLAG_PERSON_NAME


def test_screen_flags_part_viii_identifier_shapes() -> None:
    assert disp.screen_name("Call 555-123-4567 Dept") == disp.SCREEN_FLAG_PART_VIII
    assert disp.screen_name("Unit 123-45-6789") == disp.SCREEN_FLAG_PART_VIII


def test_screen_passes_organisation_names() -> None:
    assert disp.screen_name("Acme Police Department") is None
    assert disp.screen_name("OpenStreetMap Foundation") is None
    assert disp.screen_name("") is None


# --------------------------------------------------------------------------- #
# verify_entry — the fail-closed verdict chain (stub connection)
# --------------------------------------------------------------------------- #


class _StubConn:
    """Answers the module's exact SQL constants with canned rows."""

    def __init__(self, answers: dict[str, list[Any]]) -> None:
        self.answers = answers
        self.queries: list[str] = []

    def execute(self, query: str, params: tuple = ()) -> _StubConn:
        self.queries.append(query)
        rows = self.answers.get(query, [])
        key = (query, params[0] if params else None)
        if key in self.answers:
            rows = self.answers[key]
        self._result = iter(rows)
        return self

    def fetchone(self) -> Any:
        return next(self._result, None)

    def fetchall(self) -> list[Any]:
        return list(self._result)


def _org_stub(
    *,
    entity_type: str = "organization",
    status: str = "active",
    is_person: bool = False,
    effective: tuple | None = None,
    match_claim: str | None = "cc000000-0000-4000-8000-0000000000aa",
    permitted: bool = True,
    label: str = "Test Police Department",
    literal: list | None = None,
) -> _StubConn:
    answers: dict[Any, list[Any]] = {
        disp.REGISTRY_PRESENT_SQL: [(True,)],
        disp._ORG_ROW_SQL: [(entity_type, "us.le.municipal_police", status, True, is_person)],
        disp._EFFECTIVE_ONE_SQL: [effective] if effective else [],
        disp._MATCH_ROW_SQL: [(match_claim,)] if match_claim != "NONE" else [],
        disp._PERMITTED_CLAIM_SQL: [("pp000000-0000-4000-8000-0000000000bb",)] if permitted else [],
        disp._LABEL_SQL: [(label,)],
        disp._LITERAL_PARTIES_ONE_SQL: [(v,) for v in (literal or [])],
    }
    return _StubConn(answers)


def test_verify_entry_records_a_clean_registry_match() -> None:
    conn = _org_stub()
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.VERDICT_RECORD
    assert v.evidence_claim_id == "cc000000-0000-4000-8000-0000000000aa"


def test_verify_entry_refuses_a_person_entity() -> None:
    conn = _org_stub(entity_type="person", is_person=True)
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.REFUSAL_PERSON


def test_verify_entry_refuses_a_denied_org() -> None:
    conn = _org_stub(effective=("withhold", "dd000000-0000-4000-8000-0000000000cc"))
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.REFUSAL_DENY
    # the deny check runs BEFORE the match check — an auto rule never overrides
    assert disp._MATCH_ROW_SQL not in conn.queries


def test_verify_entry_refuses_unmatched_identifier() -> None:
    conn = _org_stub(match_claim="NONE")
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.REFUSAL_NO_MATCH


def test_verify_entry_refuses_unpermitted_provenance() -> None:
    conn = _org_stub(permitted=False)
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.REFUSAL_PROVENANCE


def test_verify_entry_refuses_null_asserting_claim() -> None:
    conn = _org_stub(match_claim=None)
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.REFUSAL_PROVENANCE


def test_verify_entry_refuses_a_withdrawn_org() -> None:
    conn = _org_stub(status="withdrawn")
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.REFUSAL_STATUS


def test_verify_entry_refuses_person_shaped_label() -> None:
    conn = _org_stub(label="John Smith")
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.REFUSAL_SCREEN


def test_verify_entry_screens_literal_party_values() -> None:
    """K2 §3.4: the screen runs over literal party values on the claims too."""
    conn = _org_stub(literal=["Doe, Jane"])
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.REFUSAL_SCREEN


def test_verify_entry_screens_the_registry_name() -> None:
    conn = _org_stub()
    entry = disp.load_disposition_list(_list_doc(_entry(registry_name="John Smith"))).entries[0]
    v = disp.verify_entry(conn, entry)
    assert v.verdict == disp.REFUSAL_SCREEN


def test_verify_entry_skips_an_already_allowed_org() -> None:
    conn = _org_stub(effective=("allow", "dd000000-0000-4000-8000-0000000000cc"))
    v = disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    assert v.verdict == disp.VERDICT_ALREADY_ALLOWED


def test_verify_entry_is_read_only() -> None:
    """The verification surface issues SELECT statements only."""
    conn = _org_stub()
    disp.verify_entry(conn, disp.load_disposition_list(_list_doc(_entry())).entries[0])
    for q in conn.queries:
        assert re.match(r"^\s*SELECT", q, re.IGNORECASE), q


# --------------------------------------------------------------------------- #
# build_plan — the emitted record
# --------------------------------------------------------------------------- #


def test_build_plan_is_deterministic_and_id_keyed() -> None:
    lst = disp.load_disposition_list(_list_doc(_entry(_E2), _entry(_E1)))
    conn = _org_stub()
    verdicts = disp.plan_allows(conn, lst.entries)
    plan = disp.build_plan(lst, verdicts, mode="dry-run", authority="ADR-159:x", decided_by="r-a-a")
    assert plan["record_type"] == disp.DISPOSITION_PLAN_SCHEMA
    assert plan["mode"] == "dry-run"
    assert [r["entity_id"] for r in plan["entries"]] == [_E1, _E2]
    assert plan["summary"]["total"] == 2
    assert plan["summary"]["record"] == 2
    assert plan["obligation"] == "D-R11-ADR124-1"
    # a screened label/registry name never leaks into the plan
    assert "John Smith" not in json.dumps(plan)


# --------------------------------------------------------------------------- #
# write_census — the committed artifacts carry ids + counts only
# --------------------------------------------------------------------------- #


def _census_result() -> disp.CensusResult:
    rows = [
        disp.CensusRow(
            entity_id=_E1,
            organization_type="us.le.municipal_police",
            status="active",
            degree=3,
            materialized_degree=1,
            edge_share=0.75,
            identifiers=[("wikidata.qid", "Q1"), ("us.fbi.ori", "OK001")],
            registry_match=("wikidata_qid", "wikidata.qid", "Q1"),
            match_claim_id="cc000000-0000-4000-8000-0000000000aa",
            person_name_screen=disp.SCREEN_PASS,
            screened_literal_party_count=2,
            current_disposition="none",
            adr159_outcome=disp.OUTCOME_AUTO_ALLOW,
        ),
        disp.CensusRow(
            entity_id=_E2,
            organization_type="us.le.municipal_police",
            status="active",
            degree=1,
            materialized_degree=0,
            edge_share=0.25,
            identifiers=[],
            registry_match=None,
            person_name_screen=disp.SCREEN_PASS,
            screened_literal_party_count=0,
            current_disposition="none",
            adr159_outcome=disp.OUTCOME_NOT_REVIEWED,
        ),
    ]
    return disp.CensusResult(
        rows=rows,
        flagged_total=2,
        edge_denominator=4,
        counts={disp.OUTCOME_AUTO_ALLOW: 1, disp.OUTCOME_NOT_REVIEWED: 1},
        registry_match_counts={"wikidata_qid": 1},
        top50_edge_share=1.0,
        person_screen_flagged=0,
    )


def test_write_census_emits_ids_only_artifacts(tmp_path) -> None:
    paths = disp.write_census(
        _census_result(), tmp_path, spine_name="fixture", generated_at="2026-01-01T00:00:00Z"
    )
    assert set(paths) == {"CENSUS.md", "CENSUS.csv", "census.json", "allow-list.json"}
    for path in paths.values():
        text = path.read_text(encoding="utf-8")
        # no screened label or literal party value may reach a committed file
        for screened in ("John Smith", "Doe, Jane", "Test Police Department"):
            assert screened not in text
    csv_lines = (tmp_path / "CENSUS.csv").read_text(encoding="utf-8").splitlines()
    assert csv_lines[0].split(",") == list(disp.CENSUS_COLUMNS)
    assert len(csv_lines) == 3  # header + 2 flagged orgs
    assert _E1 in csv_lines[1] and _E2 in csv_lines[2]
    assert "D-R11-ADR124-1" in csv_lines[1]
    allow = json.loads((tmp_path / "allow-list.json").read_text(encoding="utf-8"))
    assert allow["record_type"] == disp.DISPOSITION_LIST_SCHEMA
    # only the eligible row is in the allow list
    assert [e["entity_id"] for e in allow["entries"]] == [_E1]
    record = json.loads((tmp_path / "census.json").read_text(encoding="utf-8"))
    assert record["record_type"] == disp.CENSUS_SCHEMA
    assert record["flagged_total"] == 2
    assert record["outcome_counts"]["auto_allow_eligible"] == 1


def test_census_sql_is_read_only() -> None:
    """Every census statement is a SELECT — the live leg carries zero writes."""
    for name in dir(disp):
        if name.endswith("_SQL"):
            sql = getattr(disp, name)
            assert re.match(r"^\s*SELECT", sql), name
            assert not re.search(
                r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|GRANT)\b",
                sql,
            ), name


# --------------------------------------------------------------------------- #
# CLI wiring — parser + refusal exits (no spine needed)
# --------------------------------------------------------------------------- #


def test_cli_record_requires_allow_flag() -> None:
    assert (
        ops_cli.main(
            [
                "disposition",
                "record",
                "--from",
                "x.json",
                "--authority",
                "a",
                "--decided-by",
                "r-a-a",
            ]
        )
        == 2
    )


def test_cli_record_requires_from() -> None:
    assert (
        ops_cli.main(
            [
                "disposition",
                "record",
                "--allow",
                "--authority",
                "a",
                "--decided-by",
                "r-a-a",
            ]
        )
        == 2
    )


def test_cli_record_requires_authority() -> None:
    assert (
        ops_cli.main(
            [
                "disposition",
                "record",
                "--allow",
                "--from",
                "x.json",
                "--decided-by",
                "r-a-a",
            ]
        )
        == 2
    )


def test_cli_record_refuses_a_named_decider() -> None:
    assert (
        ops_cli.main(
            [
                "disposition",
                "record",
                "--allow",
                "--from",
                "x.json",
                "--authority",
                "a",
                "--decided-by",
                "Jane Smith",
            ]
        )
        == 2
    )


def test_cli_record_requires_dsn_env(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SIG_DISPOSITION_DSN", raising=False)
    lst = tmp_path / "l.json"
    lst.write_text(json.dumps(_list_doc(_entry())), encoding="utf-8")
    rc = ops_cli.main(
        [
            "disposition",
            "record",
            "--allow",
            "--from",
            str(lst),
            "--authority",
            "ADR-159:x",
            "--decided-by",
            "r-a-a",
        ]
    )
    assert rc == 2


def test_cli_dry_run_is_the_default(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without --apply the verb verifies and prints a plan — it never writes."""
    calls: dict[str, Any] = {}

    class _FakeCtx:
        def __enter__(self):
            return _org_stub()

        def __exit__(self, *exc):
            return None

    monkeypatch.setenv("SIG_DISPOSITION_DSN", "postgresql://example/sig")
    monkeypatch.setattr(disp, "_connect", lambda dsn: _FakeCtx())
    calls["apply"] = 0
    real = disp.apply_allows

    def _spy(*a, **kw):
        calls["apply"] += 1
        return real(*a, **kw)

    monkeypatch.setattr(disp, "apply_allows", _spy)
    lst = tmp_path / "l.json"
    lst.write_text(json.dumps(_list_doc(_entry())), encoding="utf-8")
    rc = ops_cli.main(
        [
            "disposition",
            "record",
            "--allow",
            "--from",
            str(lst),
            "--authority",
            "ADR-159:x",
            "--decided-by",
            "r-a-a",
        ]
    )
    assert rc == 0
    assert calls["apply"] == 0  # dry-run: apply_allows is never reached


def test_cli_census_requires_out_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SIG_DISPOSITION_DSN", "postgresql://example/sig")
    assert ops_cli.main(["disposition", "census"]) == 2
