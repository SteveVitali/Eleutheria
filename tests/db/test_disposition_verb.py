# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.26 — the ``sig-ops disposition`` verb + flagged-org census (fixture spine).

ADR-124 + ADR-159 (G2-ADR124 + D-K2-1 [A-10], SIG-TRUST-006 / SIG-ONTO-013 /
SIG-PUB-002 / SIG-STORE-011, F-452):

* ``record --allow`` inserts ONLY ``allow`` rows through
  ``db.dispositions.record_disposition`` — INSERT-only, one transaction — and
  fails closed with a typed refusal for every candidate that is not a tier
  0–1 registry match asserted by an ``ingestion_permitted`` source with a
  clean person-name screen;
* a recorded allow is immediately visible to the SAME gate the API serves
  (``entity_eligible_sql`` + ``organization_publication_decision``), and a
  flagged org without one is the typed ``pending_publication_review``
  absence — through ``PgReadStore`` itself (deliverable 3);
* ``run_census`` over the fixture spine classifies every flagged org —
  ``auto_allow_eligible`` only where ``--apply`` would record — and the
  emitted artifacts carry ids + counts, never a screened label;
* the census is read-only by construction: it runs identically under
  ``TRANSACTION READ ONLY``.
"""

from __future__ import annotations

import json
from typing import Any

import psycopg
from conftest import insert_claim, seed_claim_prerequisites
from db.dispositions import entity_eligible_sql, record_disposition
from policy.eligibility import (
    Disposition,
    ReasonCategory,
    TargetKind,
    new_disposition,
)

from ops import dispositions as disp

_OGRI = "us.fbi.ori"


def _entity(conn: Any, entity_type: str = "organization") -> Any:
    return conn.execute(
        "INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (entity_type,)
    ).fetchone()[0]


def _org(
    conn: Any,
    entity_id: Any,
    *,
    review: bool = True,
    status: str = "active",
    label: str = "Fixture Police Department",
) -> None:
    conn.execute(
        "INSERT INTO organization(entity_id, organization_type, status,"
        " publication_review_required, cached_canonical_name)"
        " VALUES(%s, 'us.le.municipal_police', %s, %s, %s)",
        (entity_id, status, review, label),
    )


def _permitted_source_claim(
    conn: Any,
    prereqs: dict[str, Any],
    *,
    source_id: str = "fixture_census_registry",
    permitted: bool = True,
) -> Any:
    """A claim bound through claim_evidence to a capture of an
    ``ingestion_permitted`` source — the ADR-159 item-6 provenance chain."""
    conn.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,robots_policy,"
        "ingestion_permitted) VALUES(%s,%s,'registry','R2','fixture',%s,'MIRROR','granted',"
        "'obey',%s) ON CONFLICT DO NOTHING",
        (source_id, source_id, prereqs["rights_id"], permitted),
    )
    artifact = conn.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,'registry','registry_api','primary',%s,'captured') "
        "RETURNING artifact_id",
        (source_id, f"urn:sig:p34_26:{source_id}", prereqs["rights_id"]),
    ).fetchone()[0]
    capture = conn.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) "
        "VALUES(%s,%s,10,'application/json','2026-01-01',%s,%s,'v1','public',"
        "'registry_api','sig/0',%s) RETURNING capture_id",
        (
            artifact,
            f"digest-{source_id}",
            prereqs["run_id"],
            f"urn:{source_id}",
            f"urn:{source_id}",
        ),
    ).fetchone()[0]
    claim_id = insert_claim(conn, prereqs)
    conn.execute(
        "INSERT INTO claim_evidence(claim_id, capture_id, role) VALUES(%s, %s, 'establishes')",
        (claim_id, capture),
    )
    return claim_id


def _identifier(
    conn: Any, entity_id: Any, scheme: str, value: str, asserted_by: Any = None
) -> None:
    conn.execute(
        "INSERT INTO entity_identifier(entity_id, scheme, value, asserted_by_claim)"
        " VALUES(%s, %s, %s, %s)",
        (entity_id, scheme, value, asserted_by),
    )


def _entry(
    entity_id: Any,
    registry: str = "wikidata_qid",
    value: str = "Q12345",
    *,
    registry_name: str | None = None,
) -> dict[str, Any]:
    return {
        "entity_id": str(entity_id),
        "registry": registry,
        "identifier": {"scheme": disp.REGISTRIES[registry]["scheme"], "value": value},
        "match_tier": 0,
        **({"registry_name": registry_name} if registry_name else {}),
    }


def _list_of(*entries: dict[str, Any]) -> disp.DispositionList:
    return disp.load_disposition_list(
        {
            "record_type": disp.DISPOSITION_LIST_SCHEMA,
            "list_id": "fixture-list",
            "policy_version": "publication-eligibility/1",
            "entries": list(entries),
        }
    )


def _deny(conn: Any, entity_id: Any) -> None:
    record_disposition(
        conn,
        new_disposition(
            target_kind=TargetKind.ENTITY,
            target_id=str(entity_id),
            disposition=Disposition.WITHHOLD,
            reason_category=ReasonCategory.REVIEW_DENIED,
            authority="reviewer:fixture",
        ),
    )


# --------------------------------------------------------------------------- #
# verify → apply — the allow path
# --------------------------------------------------------------------------- #


def test_apply_records_allow_and_lifts_the_flag(conn: Any) -> None:
    prereqs = seed_claim_prerequisites(conn)
    org = _entity(conn)
    _org(conn, org)
    claim_id = _permitted_source_claim(conn, prereqs)
    _identifier(conn, org, "wikidata.qid", "Q12345", claim_id)

    lst = _list_of(_entry(org))
    verdicts = disp.plan_allows(conn, lst.entries)
    assert [v.verdict for v in verdicts] == [disp.VERDICT_RECORD]

    eligible = f"SELECT {entity_eligible_sql('%s')}"  # noqa: S608
    thrice = (str(org),) * 3
    assert conn.execute(eligible, thrice).fetchone()[0] is False  # flagged, withheld

    applied = disp.apply_allows(
        conn, verdicts, authority="ADR-159:wikidata_qid", decided_by="registry-auto-allow"
    )
    assert applied[0].disposition_id is not None

    row = conn.execute(
        "SELECT disposition, reason_category, authority, decided_by,"
        " evidence_claim_id::text, policy_version FROM publication_disposition"
        " WHERE target_id = %s",
        (str(org),),
    ).fetchone()
    assert row[0] == "allow"
    assert row[1] == "pending_publication_review"
    assert row[2] == "ADR-159:wikidata_qid"
    assert row[3] == "registry-auto-allow"
    assert row[4] == str(claim_id)  # the match's asserting claim is the evidence
    assert row[5] == "publication-eligibility/1"
    assert conn.execute(eligible, thrice).fetchone()[0] is True  # the flag lifts


def test_reapply_is_idempotent_already_allowed(conn: Any) -> None:
    prereqs = seed_claim_prerequisites(conn)
    org = _entity(conn)
    _org(conn, org)
    _identifier(conn, org, "us.sam.uei", "UEIFIXTURE1", _permitted_source_claim(conn, prereqs))
    lst = _list_of(_entry(org, registry="sam_uei", value="UEIFIXTURE1"))
    applied = disp.apply_allows(
        conn,
        disp.plan_allows(conn, lst.entries),
        authority="ADR-159:sam_uei",
        decided_by="registry-auto-allow",
    )
    assert applied[0].verdict == disp.VERDICT_RECORD
    # a second run of the same list records NOTHING (append-only + no dup)
    again = disp.plan_allows(conn, lst.entries)
    assert again[0].verdict == disp.VERDICT_ALREADY_ALLOWED
    applied2 = disp.apply_allows(
        conn, again, authority="ADR-159:sam_uei", decided_by="registry-auto-allow"
    )
    assert all(v.disposition_id is None for v in applied2)
    n = conn.execute(
        "SELECT count(*) FROM publication_disposition WHERE target_id = %s",
        (str(org),),
    ).fetchone()[0]
    assert n == 1


def test_refusal_matrix(conn: Any) -> None:
    """Every non-match candidate fails closed with its typed refusal — and a
    refusal is NEVER written."""
    prereqs = seed_claim_prerequisites(conn)
    cases: list[tuple[Any, dict[str, Any], str]] = []

    # unmatched organisation — no identifier at all (SIG-ONTO-013: a
    # vendor-network-listing-only org keeps its flag)
    org_no_id = _entity(conn)
    _org(conn, org_no_id)
    cases.append((org_no_id, _entry(org_no_id), disp.REFUSAL_NO_MATCH))

    # unpermitted provenance — the identifier is asserted by a source whose
    # ingestion_permitted is false (ADR-159 item 6)
    org_bad_src = _entity(conn)
    _org(conn, org_bad_src)
    bad_claim = _permitted_source_claim(conn, prereqs, source_id="unpermitted_src", permitted=False)
    _identifier(conn, org_bad_src, "wikidata.qid", "Q9", bad_claim)
    cases.append((org_bad_src, _entry(org_bad_src, value="Q9"), disp.REFUSAL_PROVENANCE))

    # unasserted identifier — no provenance at all
    org_null = _entity(conn)
    _org(conn, org_null)
    _identifier(conn, org_null, "wikidata.qid", "Q8", None)
    cases.append((org_null, _entry(org_null, value="Q8"), disp.REFUSAL_PROVENANCE))

    # person-shaped label — the never-a-person rule outranks a registry match
    org_person = _entity(conn)
    _org(conn, org_person, label="John Smith")
    p_claim = _permitted_source_claim(conn, prereqs, source_id="p_src")
    _identifier(conn, org_person, "wikidata.qid", "Q7", p_claim)
    cases.append((org_person, _entry(org_person, value="Q7"), disp.REFUSAL_SCREEN))

    # person-shaped literal party value on a claim (K2 §3.4)
    org_lit = _entity(conn)
    _org(conn, org_lit)
    l_claim = _permitted_source_claim(conn, prereqs, source_id="l_src")
    _identifier(conn, org_lit, "wikidata.qid", "Q6", l_claim)
    conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
        "value_text,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,"
        "rights_id,sensitivity_tier,object_entity) "
        "VALUES(%s,%s,'entity_ref','value','Doe, Jane','x','2026-05-01','R1','D1','I1',"
        "%s,'fixture',%s,%s,0,%s)",
        (
            prereqs["subject_id"],
            prereqs["predicate_id"],
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
            org_lit,
        ),
    )
    cases.append((org_lit, _entry(org_lit, value="Q6"), disp.REFUSAL_SCREEN))

    # a person entity — refused always (ADR-163)
    person = _entity(conn, "person")
    cases.append((person, _entry(person), disp.REFUSAL_PERSON))

    # withdrawn / suppressed orgs — the status gate
    org_w = _entity(conn)
    _org(conn, org_w, status="withdrawn")
    w_claim = _permitted_source_claim(conn, prereqs, source_id="w_src")
    _identifier(conn, org_w, "wikidata.qid", "Q5", w_claim)
    cases.append((org_w, _entry(org_w, value="Q5"), disp.REFUSAL_STATUS))

    # a recorded deny — the auto rule never overrides a recorded decision
    org_d = _entity(conn)
    _org(conn, org_d)
    d_claim = _permitted_source_claim(conn, prereqs, source_id="d_src")
    _identifier(conn, org_d, "wikidata.qid", "Q4", d_claim)
    _deny(conn, org_d)
    cases.append((org_d, _entry(org_d, value="Q4"), disp.REFUSAL_DENY))

    # not an organisation at all
    dep = _entity(conn, "deployment")
    cases.append((dep, _entry(dep), disp.REFUSAL_NOT_ORG))

    # missing entity
    missing = "99999999-9999-4999-8999-999999999999"
    cases.append((missing, _entry(missing), disp.REFUSAL_TARGET_MISSING))

    before = conn.execute("SELECT count(*) FROM publication_disposition").fetchone()[0]
    entries = [e for _t, e, _v in cases]
    verdicts = disp.plan_allows(conn, _list_of(*entries).entries)
    by_id = {v.entry.entity_id: v for v in verdicts}
    for target, _e, expected in cases:
        got = by_id[str(target)].verdict
        assert got == expected, f"{target}: {got} != {expected}"
    disp.apply_allows(conn, verdicts, authority="ADR-159:x", decided_by="registry-auto-allow")
    after = conn.execute("SELECT count(*) FROM publication_disposition").fetchone()[0]
    assert after == before  # a refusal is never written


def test_apply_is_atomic_one_transaction(conn: Any) -> None:
    """The list is one decision batch: insert, verify-all-land."""
    prereqs = seed_claim_prerequisites(conn)
    orgs = []
    for i in range(2):
        org = _entity(conn)
        _org(conn, org)
        c = _permitted_source_claim(conn, prereqs, source_id=f"multi_src_{i}")
        _identifier(conn, org, "us.census.geoid", f"GEOID{i}", c)
        orgs.append(org)
    lst = _list_of(
        *[
            _entry(o, registry="census_of_governments", value=f"GEOID{i}")
            for i, o in enumerate(orgs)
        ]
    )
    verdicts = disp.plan_allows(conn, lst.entries)
    disp.apply_allows(conn, verdicts, authority="ADR-159:cog", decided_by="registry-auto-allow")
    n = conn.execute(
        "SELECT count(*) FROM publication_disposition WHERE disposition = 'allow'"
        " AND authority = 'ADR-159:cog'"
    ).fetchone()[0]
    assert n == 2


# --------------------------------------------------------------------------- #
# deliverable 3 — the API gate sees the recorded allow / the typed absence
# --------------------------------------------------------------------------- #


def test_api_gate_serves_typed_absence_then_visible(
    conn: Any, sig_database: dict[str, object]
) -> None:
    """Through ``PgReadStore`` (the real API path): a flagged org with no
    disposition answers the ``pending_publication_review`` tombstone; after
    ``apply_allows`` records the allow the same route is visible."""
    from api.store_pg import PgReadStore

    prereqs = seed_claim_prerequisites(conn)
    org = _entity(conn)
    _org(conn, org)
    claim_id = _permitted_source_claim(conn, prereqs)
    _identifier(conn, org, "wikidata.qid", "Q55", claim_id)
    conn.commit()  # the store reads on its own pooled connection

    dsn = (
        f"postgresql://{sig_database['user']}:{sig_database['password']}@"
        f"{sig_database['host']}:{sig_database['port']}/{sig_database['dbname']}"
    )
    store = PgReadStore(dsn, pool_min=1, pool_max=2)
    try:
        record = store.entity("organization", str(org))
        assert record is not None
        assert record.publication is not None
        assert record.publication.permitted is False
        assert record.publication.reason_category.value == "pending_publication_review"
        assert record.label is None  # the label is never served under the flag

        lst = _list_of(_entry(org, value="Q55"))
        with psycopg.connect(dsn, autocommit=False) as w:
            disp.apply_allows(
                w,
                disp.plan_allows(w, lst.entries),
                authority="ADR-159:wikidata_qid",
                decided_by="registry-auto-allow",
            )
            w.commit()

        record2 = store.entity("organization", str(org))
        assert record2 is not None
        assert record2.publication is None  # permitted — the allow lifts the flag
        assert record2.label == "Fixture Police Department"
    finally:
        store.close()
        # leave the spine as found (committed rows outlive the conn rollback)
        with psycopg.connect(dsn, autocommit=True) as c:
            c.execute(
                "TRUNCATE publication_disposition, entity_identifier, organization,"
                " entity, claim_evidence, claim, evidence_capture, evidence_artifact,"
                " source_registry, ingest_run, rights_record CASCADE"
            )


# --------------------------------------------------------------------------- #
# The census — every flagged org classified, read-only, ids + counts only
# --------------------------------------------------------------------------- #


def test_census_classifies_every_flagged_org(conn: Any) -> None:
    prereqs = seed_claim_prerequisites(conn)
    # eligible: flagged + permitted wikidata match + clean screen
    eligible = _entity(conn)
    _org(conn, eligible)
    c1 = _permitted_source_claim(conn, prereqs, source_id="cen_a")
    _identifier(conn, eligible, "wikidata.qid", "Q1", c1)
    _identifier(conn, eligible, _OGRI, "ORI001", None)  # a non-registry id too
    # edges: two distinct subjects reference it
    for _ in range(2):
        subj = _entity(conn, "deployment")
        conn.execute(
            "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
            "value_text,raw_value,observed_at,source_reliability,claim_directness,"
            "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,"
            "rights_id,sensitivity_tier,object_entity) "
            "VALUES(%s,%s,'entity_ref','value',NULL,'x','2026-05-01','R1','D1','I1',"
            "%s,'fixture',%s,%s,0,%s)",
            (
                subj,
                prereqs["predicate_id"],
                prereqs["author_id"],
                prereqs["run_id"],
                prereqs["rights_id"],
                eligible,
            ),
        )
    # unpermitted match -> not yet reviewed
    unperm = _entity(conn)
    _org(conn, unperm)
    c2 = _permitted_source_claim(conn, prereqs, source_id="cen_b", permitted=False)
    _identifier(conn, unperm, "wikidata.qid", "Q2", c2)
    # no identifiers at all -> not yet reviewed (SIG-ONTO-013 vendor-listing org)
    bare = _entity(conn)
    _org(conn, bare)
    # person-shaped label with a permitted match -> still not auto-allowed
    shaped = _entity(conn)
    _org(conn, shaped, label="John Smith")
    c4 = _permitted_source_claim(conn, prereqs, source_id="cen_d")
    _identifier(conn, shaped, "wikidata.qid", "Q4", c4)
    # a recorded deny -> recorded deny (never relabelled "not yet reviewed")
    denied = _entity(conn)
    _org(conn, denied)
    _deny(conn, denied)
    # a non-flagged org is simply not in the census
    unflagged = _entity(conn)
    _org(conn, unflagged, review=False)

    result = disp.run_census(conn)
    by_id = {r.entity_id: r for r in result.rows}
    assert set(by_id) == {
        str(eligible),
        str(unperm),
        str(bare),
        str(shaped),
        str(denied),
    }
    assert result.flagged_total == 5

    r_el = by_id[str(eligible)]
    assert r_el.adr159_outcome == disp.OUTCOME_AUTO_ALLOW
    assert r_el.registry_match == ("wikidata_qid", "wikidata.qid", "Q1")
    assert r_el.degree == 2
    assert r_el.person_name_screen == disp.SCREEN_PASS
    assert (_OGRI, "ORI001") in r_el.identifiers
    assert r_el.current_disposition == "none"

    assert by_id[str(unperm)].adr159_outcome == disp.OUTCOME_NOT_REVIEWED
    assert by_id[str(unperm)].registry_match is None  # unpermitted provenance
    assert by_id[str(unperm)].identifiers  # the identifier is still reported
    assert by_id[str(bare)].adr159_outcome == disp.OUTCOME_NOT_REVIEWED
    assert by_id[str(bare)].identifiers == []
    assert by_id[str(shaped)].adr159_outcome == disp.OUTCOME_NOT_REVIEWED
    assert by_id[str(shaped)].person_name_screen == disp.SCREEN_FLAG_PERSON_NAME
    assert by_id[str(shaped)].registry_match is not None  # match recorded, screen wins
    assert by_id[str(denied)].adr159_outcome == disp.OUTCOME_RECORDED_DENY
    assert by_id[str(denied)].current_disposition == "withhold"


def test_census_runs_under_transaction_read_only(conn: Any) -> None:
    """The live leg's exact posture: the census is all SELECTs — it succeeds
    inside a READ ONLY transaction where any write would abort."""
    prereqs = seed_claim_prerequisites(conn)
    org = _entity(conn)
    _org(conn, org)
    _identifier(conn, org, "wikidata.qid", "Q1", _permitted_source_claim(conn, prereqs))
    conn.execute("SET TRANSACTION READ ONLY")
    result = disp.run_census(conn)
    assert result.flagged_total == 1
    assert result.rows[0].adr159_outcome == disp.OUTCOME_AUTO_ALLOW


def test_census_artifacts_carry_no_screened_text(conn: Any, tmp_path: Any) -> None:
    prereqs = seed_claim_prerequisites(conn)
    org = _entity(conn)
    _org(conn, org, label="Fixture Police Department")
    _identifier(conn, org, "wikidata.qid", "Q1", _permitted_source_claim(conn, prereqs))
    conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,value_kind,"
        "value_text,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,"
        "rights_id,sensitivity_tier,object_entity) "
        "VALUES(%s,%s,'entity_ref','value','Literal Partner Solutions','x','2026-05-01',"
        "'R1','D1','I1',%s,'fixture',%s,%s,0,%s)",
        (
            prereqs["subject_id"],
            prereqs["predicate_id"],
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
            org,
        ),
    )
    # a label-bearing identifier — the hosted case (sig.org.name is the
    # withheld label) — is counted, never listed in the artifacts
    _identifier(conn, org, "sig.org.name", "fixture police department")
    result = disp.run_census(conn)
    paths = disp.write_census(
        result, tmp_path, spine_name="fixture", generated_at="2026-01-01T00:00:00Z"
    )
    whole = "".join(p.read_text(encoding="utf-8") for p in paths.values())
    # the label and literal party value are screened inputs — never output
    assert "Fixture Police Department" not in whole
    assert "fixture police department" not in whole
    assert "Literal Partner Solutions" not in whole
    row = result.rows[0]
    assert row.screened_literal_party_count == 1
    assert row.label_identifier_count == 1
    assert ("sig.org.name", "fixture police department") not in row.identifiers
    assert row.identifiers == [("wikidata.qid", "Q1")]
    allow = json.loads(paths["allow-list.json"].read_text(encoding="utf-8"))
    assert [e["entity_id"] for e in allow["entries"]] == [str(org)]
