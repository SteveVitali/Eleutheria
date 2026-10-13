# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.21a — source-scoped rights + the append-only attribution backfill.

AC coverage (E2-12 / ADR-194, F-387):

- ``PgClaimSink._rights_id`` keys on (source, spdx, attribution, terms) — two
  sources sharing a licence but not an attribution mint distinct
  ``rights_record``s; identical tuples dedupe (replay-safe).
- a source's claims recorded under a RESOLVED record carrying another source's
  attribution gain a NEW corrected ``rights_record`` + ``rights_decision``
  rows — never an UPDATE; the co-recorded source's claims are untouched;
- a correction that would change a resolved record's licence is REFUSED,
  loudly, before any write;
- declared identifier normalisations (``OGL-3.0`` → ``OGL-UK-3.0``) correct the
  licence id while keeping redistributability;
- the apply is idempotent — a second run reuses, never duplicates, rows;
- ``empty_attribution_count`` reports the pre/post defect count.
"""

from __future__ import annotations

from datetime import date

import pytest
from conftest import insert_claim, seed_claim_prerequisites
from db.claim_sink import PgClaimSink
from db.rights_corrections import (
    AttributionCorrection,
    AttributionCorrectionError,
    apply_correction,
    apply_corrections,
    empty_attribution_count,
    plan_corrections,
    validate_correction,
)


def _corr(**over: object) -> AttributionCorrection:
    defaults: dict[str, object] = {
        "source_id": "fixture_src",
        "spdx": "CC-BY-4.0",
        "attribution": "Fixture City Council open data",
        "redistributable": "yes",
        "derivative_permitted": "yes",
        "terms_url": "https://fixture.gov/terms",
        "reviewed_by": "licensing reviewer",
        "reviewed_on": date(2026, 10, 3),
        "basis": "E2-12 / ADR-194 attribution correction (P34.21a): F-387",
        "retrieval_date": date(2026, 9, 18),
        "review_packet": "docs/build/reports/rights/fixture_src.md",
    }
    defaults.update(over)
    return AttributionCorrection(**defaults)  # type: ignore[arg-type]


def _seed_shared_record(
    conn: object,
    *,
    source_ids: tuple[str, ...] = ("fixture_src", "other_src"),
    spdx: str = "CC-BY-4.0",
    attribution: str | None = "DeFlock community map",
    terms_url: str | None = "https://deflock.example/terms",
    claims_per_source: int = 2,
) -> dict[str, object]:
    """The F-387 shape: sources' claims SHARE one resolved record that carries
    another source's attribution (or none)."""
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO rights_record(spdx_expression,attribution_text,redistributable,"
        "derivative_permitted,terms_url,retrieval_date) "
        "VALUES(%s,%s,'yes','yes',%s,'2026-01-01') RETURNING rights_id",
        (spdx, attribution, terms_url),
    )
    shared_id = str(cur.fetchone()[0])
    out: dict[str, object] = {"shared_id": shared_id, "claims": {}}
    for source_id in source_ids:
        prereqs = seed_claim_prerequisites(conn)
        prereqs["rights_id"] = shared_id
        cur.execute(
            "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
            "reliability_justification,rights_id,custody_posture,compact_status,robots_policy) "
            "VALUES(%s,'Fixture','portal','R2','fixture',%s,'MIRROR','no_response','obey')",
            (source_id, shared_id),
        )
        cur.execute(
            "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
            "acquisition_method,primary_or_secondary,rights_id,capture_status) "
            "VALUES(%s,%s,'webpage','crawl','primary',%s,'captured') RETURNING artifact_id",
            (source_id, f"urn:sig:{source_id}:page", shared_id),
        )
        artifact_id = cur.fetchone()[0]
        cur.execute(
            "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
            "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,capture_method,"
            "capture_tool_version) VALUES(%s,%s,10,'text/html',now(),%s,'o','v1','x','v') "
            "RETURNING capture_id",
            (artifact_id, f"d-{source_id}", prereqs["run_id"]),
        )
        capture_id = cur.fetchone()[0]
        ids = []
        for _ in range(claims_per_source):
            cid = insert_claim(conn, prereqs)
            cur.execute(
                "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
                (cid, capture_id),
            )
            ids.append(str(cid))
        out["claims"][source_id] = ids  # type: ignore[index]
    return out


def _effective(conn: object, claim_id: str) -> tuple[str, str | None, str | None]:
    """(spdx, attribution, terms_url) through the ADR-095 effective rule."""
    row = conn.execute(
        "SELECT rr.spdx_expression, rr.attribution_text, rr.terms_url FROM claim c"
        " LEFT JOIN (SELECT DISTINCT ON (ce.claim_id) ce.claim_id, ea.source_id"
        "   FROM claim_evidence ce"
        "   JOIN evidence_capture ec ON ce.capture_id = ec.capture_id"
        "   JOIN evidence_artifact ea ON ec.artifact_id = ea.artifact_id"
        "   WHERE ce.role = 'establishes' ORDER BY ce.claim_id, ea.source_id) cs"
        "   ON cs.claim_id = c.claim_id"
        " LEFT JOIN (SELECT DISTINCT ON (rd.source_id, rd.prior_rights_id)"
        "          rd.source_id, rd.prior_rights_id, rd.rights_id"
        "    FROM rights_decision rd"
        "   ORDER BY rd.source_id, rd.prior_rights_id, rd.decided_at DESC, rd.decision_id DESC"
        " ) ld ON ld.source_id = cs.source_id AND ld.prior_rights_id = c.rights_id"
        " JOIN rights_record rr ON rr.rights_id = COALESCE(ld.rights_id, c.rights_id)"
        " WHERE c.claim_id = %s",
        (claim_id,),
    ).fetchone()
    assert row is not None
    return str(row[0]), row[1], row[2]


# --------------------------------------------------------------------------- #
# The sink: per-source rights resolution (F-387 at the write seam)             #
# --------------------------------------------------------------------------- #


def test_sink_rights_record_keyed_per_source_attribution(conn: object) -> None:
    """Two sources sharing a licence but differing in attribution/terms mint
    DISTINCT rights_records — the pre-P34.21a SPDX key collapsed them."""
    sink = PgClaimSink(conn, connector_name="fixture")
    a = sink._rights_id("src_a", "CC-BY-4.0", "Council A open data", "https://a/terms")
    b = sink._rights_id("src_b", "CC-BY-4.0", "Council B open data", "https://b/terms")
    assert a != b  # same licence, different source+attribution → different record
    # An identical tuple dedupes onto the first record (replay-safe).
    assert sink._rights_id("src_a", "CC-BY-4.0", "Council A open data", "https://a/terms") == a
    # A third source whose (spdx, attribution, terms) genuinely agrees shares it —
    # the key scopes the lookup; the record itself stays source-agnostic.
    assert sink._rights_id("src_c", "CC-BY-4.0", "Council A open data", "https://a/terms") == a
    n = conn.execute("SELECT count(*) FROM rights_record").fetchone()[0]
    assert int(n) == 2
    rows = conn.execute(
        "SELECT attribution_text, terms_url FROM rights_record ORDER BY attribution_text"
    ).fetchall()
    assert {r[0] for r in rows} == {"Council A open data", "Council B open data"}
    assert {r[1] for r in rows} == {"https://a/terms", "https://b/terms"}


def test_sink_resolver_fills_absent_claim_fields(conn: object) -> None:
    """A claim that asserted no attribution records the source's own reviewed
    credit through the resolver — claim fields still win when present."""
    resolver = lambda sid: (  # noqa: E731 - a fixture lambda
        {
            "spdx": "CC-BY-4.0",
            "attribution": "Registry credit for " + sid,
            "terms_url": "https://reg/terms",
            "redistributable": "yes",
            "derivative_permitted": "yes",
        }
        if sid == "src_reg"
        else None
    )
    sink = PgClaimSink(conn, connector_name="fixture", rights_resolver=resolver)
    rid = sink._rights_id("src_reg", "", None, None)
    row = conn.execute(
        "SELECT spdx_expression, attribution_text, terms_url FROM rights_record "
        "WHERE rights_id = %s",
        (rid,),
    ).fetchone()
    assert row == ("CC-BY-4.0", "Registry credit for src_reg", "https://reg/terms")
    # Claim-carried fields win over the registry (assertion-time provenance).
    rid2 = sink._rights_id("src_reg", "MIT", "Claim credit", "https://claim/terms")
    row2 = conn.execute(
        "SELECT spdx_expression, attribution_text, terms_url FROM rights_record "
        "WHERE rights_id = %s",
        (rid2,),
    ).fetchone()
    assert row2 == ("MIT", "Claim credit", "https://claim/terms")
    assert rid2 != rid


def test_sink_unknown_source_resolves_nothing(conn: object) -> None:
    sink = PgClaimSink(
        conn,
        connector_name="fixture",
        rights_resolver=lambda sid: None,
    )
    rid = sink._rights_id("unknown_src", "", None, None)
    row = conn.execute(
        "SELECT spdx_expression, redistributable FROM rights_record WHERE rights_id = %s",
        (rid,),
    ).fetchone()
    assert row == ("UNDETERMINED", "UNDETERMINED")  # honestly undecided, never 'no'


# --------------------------------------------------------------------------- #
# The backfill: corrections over resolved priors                                #
# --------------------------------------------------------------------------- #


def test_correction_repairs_shared_record_attribution(conn: object) -> None:
    """fixture_src's claims sat on the shared record's 'DeFlock' credit; the
    correction lands a new record + decision and the effective view flips —
    while other_src's claims stay exactly where they were."""
    seed = _seed_shared_record(conn)
    report = apply_correction(conn, _corr())
    assert report["decisions_inserted"] == 1
    assert report["claims_affected"] == 2
    for cid in seed["claims"]["fixture_src"]:
        assert _effective(conn, cid) == (
            "CC-BY-4.0",
            "Fixture City Council open data",
            "https://fixture.gov/terms",
        )
    # other_src shares the same recorded record but no decision — untouched.
    for cid in seed["claims"]["other_src"]:
        assert _effective(conn, cid) == (
            "CC-BY-4.0",
            "DeFlock community map",
            "https://deflock.example/terms",
        )
    # The recorded rights_id is assertion-time provenance — never rewritten.
    recorded = conn.execute(
        "SELECT DISTINCT rights_id FROM claim WHERE claim_id = ANY(%s)",
        (seed["claims"]["fixture_src"],),
    ).fetchall()
    assert {str(r[0]) for r in recorded} == {seed["shared_id"]}
    # The decision names the role, basis, and terms — the audit trail.
    dec = conn.execute(
        "SELECT reviewer, basis, terms_url FROM rights_decision WHERE source_id = 'fixture_src'"
    ).fetchone()
    assert dec[0] == "licensing reviewer"
    assert "E2-12" in dec[1] and "ADR-194" in dec[1]
    assert dec[2] == "https://fixture.gov/terms"


def test_correction_refuses_a_licence_change(conn: object) -> None:
    """A correction that would change a resolved record's spdx is NOT an
    attribution correction — refused loudly, and nothing is written."""
    _seed_shared_record(conn)
    corr = _corr(spdx="ODbL-1.0")  # prior carries CC-BY-4.0 — a licence change
    plan = plan_corrections(conn, [corr])
    assert plan["refused"]
    assert any("licence change" in r for r in plan["refused"])
    with pytest.raises(AttributionCorrectionError, match="relicense"):
        apply_correction(conn, corr)
    assert conn.execute("SELECT count(*) FROM rights_decision").fetchone()[0] == 0


def test_correction_refuses_a_redistributability_change(conn: object) -> None:
    """Correcting attribution may never soften or harden a resolved record's
    redistributability — the correction keeps the prior's (ADR-194)."""
    _seed_shared_record(conn)
    corr = _corr(redistributable="no")
    with pytest.raises(AttributionCorrectionError):
        apply_correction(conn, corr)
    assert conn.execute("SELECT count(*) FROM rights_decision").fetchone()[0] == 0


def test_declared_identifier_normalisation_corrects_the_id(conn: object) -> None:
    """OGL-3.0 → OGL-UK-3.0 declared in spdx_aliases: the same licence text
    under its canonical id — recorded, not a silent relabel."""
    _seed_shared_record(conn, spdx="OGL-3.0", attribution="Sheffield City Council")
    corr = _corr(
        spdx="OGL-UK-3.0",
        attribution="Sheffield City Council (OGL v3.0)",
        spdx_aliases=("OGL-3.0",),
    )
    report = apply_correction(conn, corr)
    assert report["decisions_inserted"] == 1
    row = conn.execute(
        "SELECT rr.spdx_expression FROM rights_decision rd"
        " JOIN rights_record rr ON rr.rights_id = rd.rights_id"
        " WHERE rd.source_id = 'fixture_src'"
    ).fetchone()
    assert str(row[0]) == "OGL-UK-3.0"


def test_undeclared_identifier_difference_is_refused(conn: object) -> None:
    """The same id difference without a declared alias is a licence change."""
    _seed_shared_record(conn, spdx="OGL-3.0", attribution="Sheffield")
    with pytest.raises(AttributionCorrectionError, match="relicense"):
        apply_correction(conn, _corr(spdx="OGL-UK-3.0"))


def test_apply_is_idempotent(conn: object) -> None:
    _seed_shared_record(conn)
    first = apply_correction(conn, _corr())
    second = apply_correction(conn, _corr())
    assert first["decisions"][0]["inserted"] is True
    assert second["decisions"][0]["inserted"] is False
    assert first["rights_id"] == second["rights_id"]
    n = conn.execute("SELECT count(*) FROM rights_decision").fetchone()[0]
    assert int(n) == 1


def test_plan_is_read_only_and_reports_counts(conn: object) -> None:
    _seed_shared_record(conn)
    plan = plan_corrections(conn, [_corr()])
    src = plan["sources"][0]
    assert src["decisions_would_write"] == 1
    assert src["claims_affected"] == 2
    assert src["priors"][0]["kind"] == "correct"
    assert conn.execute("SELECT count(*) FROM rights_decision").fetchone()[0] == 0


def test_empty_attribution_count_reports_the_defect_and_the_fix(conn: object) -> None:
    _seed_shared_record(conn, source_ids=("fixture_src",), attribution=None)
    assert empty_attribution_count(conn, ["fixture_src"]) == 2
    apply_correction(conn, _corr())
    assert empty_attribution_count(conn, ["fixture_src"]) == 0


def test_correction_on_a_noop_record_writes_no_decision(conn: object) -> None:
    """A source whose record already carries the corrected signature is a no-op."""
    _seed_shared_record(
        conn,
        source_ids=("fixture_src",),
        attribution="Fixture City Council open data",
        terms_url="https://fixture.gov/terms",
    )
    report = apply_correction(conn, _corr())
    assert report["decisions_inserted"] == 0
    assert conn.execute("SELECT count(*) FROM rights_decision").fetchone()[0] == 0


def test_validation_is_fail_closed(conn: object) -> None:
    assert validate_correction(_corr(redistributable="UNDETERMINED"))
    assert validate_correction(_corr(attribution="", terms_url=""))
    assert validate_correction(_corr(reviewed_by=""))
    assert validate_correction(_corr(basis="no citation"))
    assert not validate_correction(_corr())


def test_batch_apply_aborts_wholes_on_any_refusal(conn: object) -> None:
    """A refused row anywhere aborts the run before the first write — the
    transaction the caller holds rolls back whole (never a partial apply)."""
    _seed_shared_record(conn, source_ids=("fixture_src", "src_b"))
    with pytest.raises(AttributionCorrectionError):
        apply_corrections(
            conn,
            [_corr(), _corr(source_id="src_b", spdx="ODbL-1.0")],
        )
    # The good row was refused WITH the bad one — no partial apply reached
    # the decision table (the caller's rollback erases the rest).
    assert conn.execute("SELECT count(*) FROM rights_decision").fetchone()[0] == 0
