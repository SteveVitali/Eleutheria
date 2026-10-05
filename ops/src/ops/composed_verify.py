# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The composed Round-10 verification runner (P33.2 — ``sig.composed-verification/1``).

Drives the integrated evidence-first path through ONE composed fixture over a real
PostgreSQL+PostGIS spine (deployed by sqitch — the same harness as ``tests/db``):

  capture → claim → temporal/role resolution → eligible release →
  search/record → correction (receiver → reviewer → application bridge)

Every leg consumes the shared machinery its owner ticket landed — nothing here
re-implements a contract:

* **capture→claim** — the real ``connectors.pipeline.run`` (eight stages, the
  fail-closed ingestion gate on an in-memory-permitted source — never a rights
  flip on disk) asserting through the production sink wiring
  (``make_claim_sink('pg')`` = ``record_object_ref`` + ``record_resightings``),
  plus the committed composed-fixture document asserted with a real
  ``CaptureRef`` so every fixture claim carries an ``actual_capture`` binding
  (SIG-TRUST-002) with its row locator.
* **temporal/role** — ``db.occurrences`` (latest eligible occurrence, dated and
  retrieval-fallback observations, latest-per-lineage) checked *against the SQL
  twin* ``sig.eligible_occurrence`` deployed by the sqitch plan — the
  cross-stream parity proof; and ``db.organization_roles`` (PUBLISHER never
  mints; OPERATOR/VENDOR mint distinct partner entities).
* **eligible release** — ``ops.release_candidate.run_candidate_materialization``
  (the shared materializers, idempotent +0 re-run), ``run_spine_export`` (one
  read-only REPEATABLE READ snapshot), ``build_release`` → ``validate_release``
  → ``activate``: eligibility (a withheld entity + an UNDETERMINED-rights
  subject excluded loudly) and licence compartments (CC-BY in ``sig_graph``,
  ODbL in ``osm_physical``) preserved.
* **search/record** — the released FTS5 index (``check_index_contract`` +
  ``search``), the bound record bytes, and the serving barrier
  (``route_access``/``resolve_selector``) over the activated registry.
* **correction** — ``run_intake_journey`` targeting a claim THIS release
  published (``target_claim_id``): the P32.16→P32.16a receiver→reviewer→bridge
  chain, §16.6 close+revises, exactly-once apply, publish linkage, and the live
  receiver-role refusal — while ``ops/config.toml [intake] operational=false``
  stays the honest production state.

Offline only (``live_verification=false``): no hosted probe, no production
publication, no network fetch — the connector transport serves committed fixture
bytes. Emits ``COMPOSED_VERIFICATION.json`` + ``COMPOSED_VERIFICATION.md``.
"""

from __future__ import annotations

import dataclasses
import json
import shutil
import sqlite3
import subprocess
import tomllib
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from exports.manifest import canonical_json, sha256_hex

PROOF_SCHEMA = "sig.composed-verification/1"
PROOF_JSON = "COMPOSED_VERIFICATION.json"
PROOF_MD = "COMPOSED_VERIFICATION.md"

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_PATH = REPO_ROOT / "docs" / "build" / "fixtures" / "p33-2_composed_fixture.json"
ATLAS_FIXTURE = REPO_ROOT / "tests" / "connectors" / "fixtures" / "atlas" / "adoption_feed.csv"
CONFIG_PATH = REPO_ROOT / "ops" / "config.toml"

#: Occurrence times are relative to the run's clock — the spine's
#: ``claim_observed_not_future`` invariant refuses future-dated assertions, and
#: a re-sighting MUST post-date the first capture while staying in the past.
_CAPTURE_AGE_DAYS = 7
_RESIGHTING_AGE_DAYS = 1

#: The fixture subject the release publishes and the correction leg disputes.
RELEASED_SUBJECT = "fx-dep-released"
WITHHELD_SUBJECT = "fx-dep-withheld"
ODBL_SUBJECT = "fx-dep-odbl"
UNDETERMINED_SUBJECT = "fx-dep-undetermined"
COUNT_PREDICATE = "contracted_camera_count"
UNDATED_PREDICATE = "camera_presence"


class ComposedVerificationError(RuntimeError):
    """A leg failed hard enough that later legs cannot run honestly."""


class _StaticTransport:
    """Serves one document's bytes for any URL — no real network (SIG-INGEST-011).

    Byte-for-byte the e2e seam's helper (``tests/e2e/test_composed_stack.py``);
    kept local so the runner has no test-module dependency.
    """

    def __init__(self, body: bytes, media_type: str) -> None:
        self._body = body
        self._media_type = media_type

    def robots(self, robots_url: str) -> Any:
        from connectors.net import RobotsResult

        return RobotsResult(text="User-agent: *\nAllow: /\n")

    def request(
        self,
        url: str,
        *,
        user_agent: str,
        headers: Mapping[str, str] | None = None,
        body: bytes | None = None,
    ) -> Any:
        from connectors.net import FetchResult

        return FetchResult(
            url=url,
            status=200,
            body=self._body,
            media_type=self._media_type,
            retrieved_at=datetime.now(UTC) - timedelta(days=_CAPTURE_AGE_DAYS),
        )


def _git_head() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=10,
        )
        head = out.stdout.strip()
        return head if out.returncode == 0 and head else "unknown"
    except Exception:
        return "unknown"


def _capture_ref(body: bytes, *, retrieved_at: datetime, source_uri: str) -> Any:
    """A real ``CaptureRef`` over the fixture bytes (SIG-TRUST-002)."""
    from connectors.stages import CaptureRef
    from evidence.digest import multihash

    return CaptureRef(
        digest=multihash(body),
        media_type="application/json",
        source_uri=source_uri,
        byte_size=len(body),
        retrieved_at=retrieved_at,
        ocfl_object_id="sig:p33.2-composed-fixture",
        ocfl_version="v1",
    )


def _fixture_records(doc: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The fixture rows adapted into connector-shaped claim records.

    ``record_kind``/``subject_id``/``predicate_id``/``value``/``raw_value``/
    ``observed_at``/``license`` ride straight through ``assertion_from_record``;
    the ``locator`` pins each claim to its row index in THIS document so the
    binding classifies ``actual_capture`` rather than the (honest but weaker)
    ``document_only`` fallback.
    """
    out: list[dict[str, Any]] = []
    for i, row in enumerate(doc.get("rows") or []):
        rec: dict[str, Any] = {"record_kind": "claim"}
        for key in (
            "subject_id",
            "predicate_id",
            "object_type",
            "object_ref",
            "value",
            "raw_value",
            "unit",
            "observed_at",
            "source_reliability",
            "license",
        ):
            if key in row:
                rec[key] = row[key]
        rec["locator"] = {"kind": "row", "row": i}
        rec["extraction_method"] = "deterministic"
        out.append(rec)
    return out


def _subject_entity_id(conn: Any, subject: str) -> str:
    row = conn.execute(
        "SELECT entity_id::text FROM entity_identifier "
        "WHERE scheme = 'sig.connector.subject' AND value = %s",
        (subject,),
    ).fetchone()
    if row is None:
        raise ComposedVerificationError(f"fixture subject {subject!r} has no entity")
    return str(row[0] if not hasattr(row, "keys") else row["entity_id"])


def _claim_ids(conn: Any, subject_entity: str, predicate: str) -> list[str]:
    return [
        str(r["claim_id"])
        for r in conn.execute(
            "SELECT claim_id::text AS claim_id FROM claim "
            "WHERE subject_id = %s::uuid AND predicate_id = %s ORDER BY observed_at, claim_id",
            (subject_entity, predicate),
        ).fetchall()
    ]


def _markdown(proof: Mapping[str, Any]) -> str:
    lines = [
        "# Composed Round-10 verification — P33.2",
        "",
        f"* **schema:** `{PROOF_SCHEMA}`",
        f"* **code revision:** `{proof['code_commit']}`",
        f"* **dsn:** `{proof['dsn']}`",
        f"* **generated_at:** {proof['generated_at']}",
        "* **live_verification:** false (offline fixture + local Docker only)",
        f"* **intake receiver operational (ops/config.toml):** "
        f"`{proof['environment']['intake_operational']}` — the honest production state",
        f"* **verdict:** **{proof['verdict'].upper()}**",
        "",
        "## Inputs",
        "",
        f"* fixture: `{proof['inputs']['fixture']['path']}` "
        f"(sha256 `{proof['inputs']['fixture']['sha256']}`)",
        f"* connector fixture: `{proof['inputs']['connector_fixture']['path']}` "
        f"(sha256 `{proof['inputs']['connector_fixture']['sha256']}`)",
        "",
        "## Legs",
        "",
    ]
    for leg in proof["legs"]:
        marks = "".join(
            f"  - [{'x' if c['ok'] else ' '}] **{c['check']}** — {c['detail']}\n"
            for c in leg["checks"]
        )
        lines.append(f"### {leg['leg']}\n\n{marks}")
    rel = proof.get("release") or {}
    lines += [
        "## Release identity",
        "",
        f"* publication_id: `{rel.get('publication_id')}`",
        f"* manifest_sha256: `{rel.get('manifest_sha256')}`",
        f"* compartments: `{json.dumps(rel.get('compartments'))}`",
        "",
        "Generated by `sig-ops composed-verify` / `ops.composed_verify.run_composed_verification`.",
    ]
    return "\n".join(lines) + "\n"


def run_composed_verification(
    dsn: str,
    *,
    out_dir: Path | str,
    renderer_revision: str = "p33.2",
    code_commit: str | None = None,
) -> dict[str, Any]:
    """Execute the composed path over ``dsn`` and write the proof to ``out_dir``.

    ``dsn`` must name a TEST spine (a freshly sqitch-deployed PG18+PostGIS —
    the ``tests/db``/``tests/e2e`` container or a scratch compose database).
    The function mutates the fixture database (asserts + materializes + a
    canonical correction) and writes the export/release/registry trees +
    the proof under ``out_dir``. Returns the ``sig.composed-verification/1``
    document; ``verdict`` is ``pass`` only when every check holds.
    """
    import psycopg
    from psycopg.rows import dict_row, tuple_row

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # A rerun on the same out_dir must not stack staged trees — stale
    # manifests/dossiers would double-count against activation validation.
    for stale in ("export", "release", "registry"):
        shutil.rmtree(out_dir / stale, ignore_errors=True)
    commit = code_commit or _git_head()
    legs: list[dict[str, Any]] = []

    def check(leg: str, name: str, ok: bool, detail: str) -> None:
        if not legs or legs[-1]["leg"] != leg:
            legs.append({"leg": leg, "checks": []})
        legs[-1]["checks"].append({"check": name, "ok": bool(ok), "detail": detail})

    fixture_bytes = FIXTURE_PATH.read_bytes()
    fixture_doc = json.loads(fixture_bytes)
    atlas_bytes = ATLAS_FIXTURE.read_bytes()
    run_now = datetime.now(UTC)
    first_capture_at = run_now - timedelta(days=_CAPTURE_AGE_DAYS)
    resighting_at = run_now - timedelta(days=_RESIGHTING_AGE_DAYS)
    export_as_of = run_now.date().isoformat()

    # -- environment posture (recorded, never implied) ----------------------- #
    cfg = tomllib.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    intake_cfg = cfg.get("intake") or {}
    intake_operational = bool(intake_cfg.get("operational"))

    conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    # Shared ops machinery (run_completion / rematerialize) indexes result
    # rows positionally — it owns its own tuple-row connection.
    tconn = psycopg.connect(dsn, autocommit=True)
    state: dict[str, Any] = {}
    try:
        # =====================================================================
        # Leg A — capture → claim
        # =====================================================================
        leg = "A.capture_to_claim"

        # A1 — the REAL connector pipeline over a committed fixture, asserting
        # through the production sink wiring (object refs + re-sightings).
        from connectors.atlas import ATLAS_SOURCE_ID, AtlasConnector
        from connectors.net import PoliteFetcher
        from connectors.pipeline import run as run_connector
        from connectors.registry import get as get_source
        from connectors.sinks import make_claim_sink
        from connectors.stages import InMemoryCaptureStore, RunContext
        from db.claim_sink import PgClaimSink
        from evidence.ingest_run import IngestRun

        connector = AtlasConnector()
        transport = _StaticTransport(atlas_bytes, "text/csv")
        fetcher = PoliteFetcher(
            connector_name=connector.name, connector_version="1.0.0", transport=transport
        )
        # In-memory-only permission — the registry row on disk stays
        # ingestion_permitted=false; no rights flip is performed (SIG-INGEST-028).
        source = dataclasses.replace(get_source(ATLAS_SOURCE_ID), ingestion_permitted=True)
        sink = make_claim_sink(
            "pg",
            dsn=dsn,
            connector_name=connector.name,
            connector_version="1.0.0",
            code_commit=commit,
        )
        assert isinstance(sink, PgClaimSink)
        ctx = RunContext(
            source=source,
            run=IngestRun(connector.name, "1.0.0", commit, "r1", "v1", ()),
            fetcher=fetcher,
            captures=InMemoryCaptureStore(),
            claim_sink=sink,
            parameters={
                "targets": [{"id": "t1", "url": "https://atlas.test/feed", "kind": "bulk_csv"}]
            },
        )
        report = run_connector(connector, ctx)
        check(
            leg,
            "connector_pipeline_asserted",
            report.claim_count > 0 and sink.report.inserted > 0,
            f"atlas over committed fixture: claim_count={report.claim_count} "
            f"inserted={sink.report.inserted} through PgClaimSink "
            f"(asserted={report.asserted}, captures={len(report.captures)})",
        )
        capture = report.captures[0]
        bound_rows = conn.execute(
            "SELECT ce.binding_status, count(*) AS n FROM claim_evidence ce "
            "JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
            "WHERE ec.content_digest = %s GROUP BY ce.binding_status",
            (capture.digest,),
        ).fetchall()
        bound_by_status = {str(r["binding_status"]): int(r["n"]) for r in bound_rows}
        bound = sum(bound_by_status.values())
        check(
            leg,
            "capture_bound_claims",
            bound >= sink.report.inserted
            and set(bound_by_status) <= {"actual_capture", "document_only"},
            f"{bound} claim_evidence rows bind the {sink.report.inserted} inserted "
            f"claims ({report.claim_count} records, {report.claim_count - sink.report.inserted} "
            "in-batch duplicates) to the pipeline capture "
            f"digest {capture.digest[:24]}… — classification "
            f"{bound_by_status} (atlas rows carry no typed locator → the "
            "binding is honestly document_only, SIG-TRUST-002)",
        )

        # A2 — the committed composed-fixture document asserted with a real
        # CaptureRef; every row locates into the document.
        fx_sink = make_claim_sink(
            "pg",
            dsn=dsn,
            connector_name="composed-fixture",
            connector_version="1.0.0",
            code_commit=commit,
        )
        assert isinstance(fx_sink, PgClaimSink)
        records = _fixture_records(fixture_doc)
        fx_capture = _capture_ref(
            fixture_bytes,
            retrieved_at=first_capture_at,
            source_uri="sig:fixture:p33.2-composed",
        )
        fx_sink.assert_claims(records, capture=fx_capture)
        fixture_claims = [
            str(r["claim_id"])
            for r in conn.execute(
                "SELECT claim_id::text AS claim_id FROM claim c JOIN ingest_run r "
                "ON c.ingest_run_id = r.run_id "
                "WHERE r.connector_name = 'composed-fixture' ORDER BY c.claim_id",
            ).fetchall()
        ]
        check(
            leg,
            "fixture_claims_asserted",
            fx_sink.report.inserted == len(records) and len(fixture_claims) == len(records),
            f"{fx_sink.report.inserted}/{len(records)} fixture claims inserted "
            f"(duplicates={fx_sink.report.duplicates})",
        )
        loc_row = conn.execute(
            "SELECT count(*) AS n FROM claim_evidence ce JOIN claim c "
            "ON c.claim_id = ce.claim_id JOIN ingest_run r "
            "ON c.ingest_run_id = r.run_id "
            "WHERE r.connector_name = 'composed-fixture' "
            "AND ce.binding_status = 'actual_capture' AND ce.locator IS NOT NULL",
        ).fetchone()
        loc_rows = int((loc_row or {"n": 0})["n"])
        check(
            leg,
            "fixture_locator_bindings",
            loc_rows == len(records),
            f"{loc_rows}/{len(records)} fixture bindings are actual_capture with "
            "a typed row locator into the fixture document",
        )
        # Idempotency + the re-sighting occurrence: re-assert the whole fixture
        # against a SECOND capture — +0 claims, new establishing bindings.
        fx_sink2 = make_claim_sink(
            "pg",
            dsn=dsn,
            connector_name="composed-fixture",
            connector_version="1.0.0",
            code_commit=commit,
        )
        assert isinstance(fx_sink2, PgClaimSink)
        fx_capture2 = _capture_ref(
            fixture_bytes,
            retrieved_at=resighting_at,
            source_uri="sig:fixture:p33.2-composed",
        )
        fx_sink2.assert_claims(records, capture=fx_capture2)
        links_row = conn.execute(
            "SELECT count(*) AS n FROM claim_evidence ce JOIN claim c "
            "ON c.claim_id = ce.claim_id JOIN ingest_run r "
            "ON c.ingest_run_id = r.run_id WHERE r.connector_name = 'composed-fixture'",
        ).fetchone()
        links = int((links_row or {"n": 0})["n"])
        check(
            leg,
            "resighting_append_only",
            fx_sink2.report.inserted == 0 and links == 2 * len(records),
            f"re-assert against a later capture: inserted={fx_sink2.report.inserted} "
            f"(+0), claim_evidence links={links} (2×{len(records)} — every claim now "
            "carries two establishing occurrences, append-only)",
        )

        # =====================================================================
        # Leg B — temporal + role resolution (pure model vs the SQL twin)
        # =====================================================================
        leg = "B.temporal_role_resolution"
        from db.occurrences import row_bindings, select_observation, select_occurrence
        from db.organization_roles import (
            OrganizationRole,
            mints_entity_ref,
            role_for_predicate,
        )

        released_entity = _subject_entity_id(conn, RELEASED_SUBJECT)
        withheld_entity = _subject_entity_id(conn, WITHHELD_SUBJECT)
        count_ids = _claim_ids(conn, released_entity, COUNT_PREDICATE)
        state["released_entity"] = released_entity
        state["withheld_entity"] = withheld_entity
        state["count_claim_ids"] = count_ids

        bindings = row_bindings(conn.cursor(row_factory=tuple_row), count_ids)
        # The later-dated count (v30) carries two occurrences after the
        # re-sighting; latest eligible occurrence = the second capture.
        latest_claim = count_ids[-1]
        occ_pure = select_occurrence(bindings[latest_claim])
        occ_sql = conn.execute(
            "SELECT capture_id::text FROM eligible_occurrence(%s::uuid, clock_timestamp())",
            (latest_claim,),
        ).fetchone()
        check(
            leg,
            "occurrence_selection_parity",
            occ_pure is not None
            and occ_sql is not None
            and str(occ_pure.capture_id) == str(occ_sql["capture_id"]),
            f"latest eligible occurrence for the restated count: pure model "
            f"{occ_pure.capture_id if occ_pure else None} == "
            f"eligible_occurrence {occ_sql['capture_id'] if occ_sql else None} "
            f"(the re-sighting capture retrieved {resighting_at.date()} "
            f"wins over the first {first_capture_at.date()})",
        )
        # Belief-time: before the re-sighting's bound_at, the first capture won.
        bound_ats = sorted(b.bound_at for b in bindings[latest_claim] if b.bound_at is not None)
        belief_mid = None
        if len(bound_ats) >= 2:
            delta = bound_ats[-1] - bound_ats[0]
            belief_mid = bound_ats[0] + delta / 2
        occ_early = (
            select_occurrence(bindings[latest_claim], belief=belief_mid) if belief_mid else None
        )
        occ_early_sql = (
            conn.execute(
                "SELECT capture_id::text FROM eligible_occurrence(%s::uuid, %s)",
                (latest_claim, belief_mid),
            ).fetchone()
            if belief_mid
            else None
        )
        check(
            leg,
            "belief_time_parity",
            belief_mid is not None
            and occ_early is not None
            and occ_early_sql is not None
            and str(occ_early.capture_id) == str(occ_early_sql["capture_id"])
            and str(occ_early.capture_id) != str(occ_pure.capture_id if occ_pure else ""),
            f"belief as-of {belief_mid}: both twins select the FIRST capture "
            f"{occ_early.capture_id if occ_early else None} (the later binding "
            "is not yet known — sys/belief time respected)",
        )
        # Dated claim keeps its own instant; undated claim falls back to the
        # latest occurrence retrieved_at.
        obs_dated = select_observation(
            observed_at=datetime(2026, 6, 1, tzinfo=UTC), bindings=bindings[latest_claim]
        )
        undated_ids = _claim_ids(conn, released_entity, UNDATED_PREDICATE)
        undated_bindings = row_bindings(conn.cursor(row_factory=tuple_row), undated_ids)
        obs_undated = select_observation(
            observed_at=None, bindings=undated_bindings[undated_ids[0]]
        )
        check(
            leg,
            "observation_bases",
            obs_dated.basis == "claim"
            and obs_undated.basis == "capture_retrieved_at_latest"
            and obs_undated.observed_at == resighting_at.date(),
            f"dated count → basis=claim ({obs_dated.observed_at}); undated "
            f"{UNDATED_PREDICATE} → basis=capture_retrieved_at_latest "
            f"({obs_undated.observed_at}) — no fabricated dates",
        )
        # Role taxonomy: publisher stays literal; operator/vendor mint distinct
        # partner entities.
        role_rows = conn.execute(
            "SELECT predicate_id, object_entity::text AS object_entity FROM claim "
            "WHERE subject_id = %s::uuid AND predicate_id = ANY(%s)",
            (
                released_entity,
                ["camera_registry_publisher", "camera_operator", "vendor"],
            ),
        ).fetchall()
        roles = {r["predicate_id"]: r["object_entity"] for r in role_rows}
        check(
            leg,
            "role_separation",
            role_for_predicate("camera_registry_publisher") == OrganizationRole.PUBLISHER
            and not mints_entity_ref("camera_registry_publisher")
            and roles.get("camera_registry_publisher") is None
            and roles.get("camera_operator") is not None
            and roles.get("vendor") is not None
            and roles.get("camera_operator") != roles.get("vendor"),
            f"camera_registry_publisher → PUBLISHER (object_entity NULL — "
            f"provenance mints nothing); camera_operator → "
            f"{str(roles.get('camera_operator'))[:8]}…, vendor → "
            f"{str(roles.get('vendor'))[:8]}… (distinct partner orgs, "
            "SIG-TRUST-003)",
        )

        # =====================================================================
        # Leg C — eligibility → materialize → export → release → activate
        # =====================================================================
        leg = "C.eligible_release"
        from db.dispositions import record_disposition
        from exports.release import activate, build_release, validate_release
        from exports.spine_export import run_spine_export
        from policy.eligibility import (
            Disposition,
            ReasonCategory,
            TargetKind,
            new_disposition,
        )

        from ops.release_candidate import run_candidate_materialization

        disp_id = record_disposition(
            conn,
            new_disposition(
                target_kind=TargetKind.ENTITY,
                target_id=withheld_entity,
                disposition=Disposition.WITHHOLD,
                reason_category=ReasonCategory.REVIEW_DENIED,
                authority="p33.2-composed-verification",
                decided_by="p33.2-fixture",
                rationale="composed fixture — withheld subject must not release",
            ),
        )
        check(
            leg,
            "withhold_recorded",
            bool(disp_id),
            f"entity-level WITHHOLD disposition {str(disp_id)}… recorded on "
            f"{withheld_entity[:8]}… ({WITHHELD_SUBJECT})",
        )

        # The UNDETERMINED-rights subject reaches the licence gate loudly: a
        # recorded rights_decision (P27.2/ADR-095, insert-only) lifts the
        # fixture source's redistribution posture to 'yes' while the licence
        # itself stays spdx='UNDETERMINED' — review could not determine the
        # upstream licence. Publishable claims reach slicing; the export
        # gate then refuses the slice by name in exclusions.json instead of
        # the claim silently failing the publishable test (SIG-LIC-004).
        from db.rights_decisions import RightsResolution, apply_resolution

        resolution = apply_resolution(
            tconn,
            RightsResolution(
                source_id="composed-fixture",
                spdx="UNDETERMINED",
                attribution="",
                redistributable="yes",
                derivative_permitted="yes",
                terms_url="sig:fixture:p33.2-undetermined-review",
                retrieval_date=run_now.date(),
                reviewed_by="p33.2-composed-verification",
                reviewed_on=run_now.date(),
                basis=(
                    "composed fixture: review could not determine the upstream "
                    "licence — redistribution recorded, licence unresolved, "
                    "export gate fails closed"
                ),
            ),
        )
        check(
            leg,
            "undetermined_decision_recorded",
            int(resolution["claims_lifted"]) > 0,
            f"rights_decision lifts {resolution['claims_lifted']} UNDETERMINED "
            "claims to redistributable (licence still UNDETERMINED) — "
            f"decision(s): {[d['decision_id'][:8] for d in resolution['decisions']]}",
        )

        mat = run_candidate_materialization(
            tconn,
            identity_digest=sha256_hex(fixture_bytes),
            snapshot_digest=sha256_hex(atlas_bytes),
            code_commit=commit,
        )
        check(
            leg,
            "materialization_idempotent",
            mat["plus_zero"] is True,
            f"rematerialize pass-1 +{mat['inserted_pass_one']}, rerun "
            f"+{mat['inserted_rerun']} (shared materializers, stable +0)",
        )

        # run_spine_export indexes result rows positionally — tuple rows.
        export_conn = psycopg.connect(dsn, autocommit=False)
        try:
            export = run_spine_export(
                export_conn,
                as_of=export_as_of,
                note="P33.2 composed Round-10 verification fixture",
                spine_label="p33.2 composed fixture spine",
            )
        finally:
            export_conn.rollback()
            export_conn.close()
        export_dir = export.write_to(out_dir / "export")
        sites_rows = [
            json.loads(line)
            for line in (export_dir / "sig_graph" / "sites.jsonl").read_text().splitlines()
            if line.strip()
        ]
        odbl_rows = []
        odbl_sites = export_dir / "osm_physical" / "sites.jsonl"
        if odbl_sites.exists():
            odbl_rows = [
                json.loads(line) for line in odbl_sites.read_text().splitlines() if line.strip()
            ]
        site_entities = {str(r.get("entity_id") or r.get("subject_id")) for r in sites_rows}
        odbl_entities = {str(r.get("entity_id") or r.get("subject_id")) for r in odbl_rows}
        odbl_entity = _subject_entity_id(conn, ODBL_SUBJECT)
        undetermined_entity = _subject_entity_id(conn, UNDETERMINED_SUBJECT)
        check(
            leg,
            "eligible_subjects_released",
            released_entity in site_entities and odbl_entity in odbl_entities,
            f"{RELEASED_SUBJECT} → sig_graph sites ({len(sites_rows)} rows); "
            f"{ODBL_SUBJECT} → osm_physical sites ({len(odbl_rows)} rows) — "
            "licence compartments preserved",
        )
        exclusions = export.exclusions
        refused_slices = [e for e in exclusions.get("refused") or [] if isinstance(e, Mapping)]
        undetermined_refused = [
            e
            for e in refused_slices
            if e.get("reason") == "UNDETERMINED" and e.get("spdx") == "UNDETERMINED"
        ]
        check(
            leg,
            "licence_gate_exclusion",
            withheld_entity not in site_entities
            and undetermined_entity not in site_entities
            and undetermined_entity not in odbl_entities
            and any(e.get("source_id") == "composed-fixture" for e in undetermined_refused),
            f"withheld entity {withheld_entity[:8]}… absent; UNDETERMINED-rights "
            f"subject {undetermined_entity[:8]}… absent and its refused slice "
            f"named in exclusions.json ({undetermined_refused}) — loud "
            "exclusion, never silent drop",
        )

        release_dir = out_dir / "release"
        build = build_release(export_dir, release_dir, renderer_revision=renderer_revision)
        vreport = validate_release(release_dir)
        registry_dir = out_dir / "registry"
        activation = activate(registry_dir, release_dir)
        pub = activation["publication_id"]
        latest = json.loads((registry_dir / "latest.json").read_text())
        check(
            leg,
            "release_activated",
            vreport.state == "complete" and latest["publication_id"] == pub,
            f"validate_release state={vreport.state} "
            f"({vreport.artifacts_checked} artifacts); activated "
            f"{pub[:24]}…; latest.json points at it",
        )
        state.update(
            {
                "export_dir": export_dir,
                "release_dir": release_dir,
                "registry_dir": registry_dir,
                "publication_id": pub,
                "build": build,
                "activation": activation,
            }
        )

        # =====================================================================
        # Leg D — search + record over the activated release
        # =====================================================================
        leg = "D.search_record"
        from exports.release import resolve_selector, route_access
        from exports.search_index import (
            INDEX_FILE,
            check_index_contract,
            parse_params,
            search,
        )

        staged = registry_dir / "staged"
        comp_dir = staged / "r" / pub / "c" / "sig_graph"
        idx_path = comp_dir / INDEX_FILE
        sconn = sqlite3.connect(f"file:{idx_path}?mode=ro", uri=True)
        try:
            meta = check_index_contract(sconn)
            hits = search(
                sconn,
                meta,
                parse_params(
                    q="P33.2 Composed Fixture",
                    kind=None,
                    jurisdiction=None,
                    source=None,
                    location=None,
                    technology=None,
                    limit=None,
                    cursor=None,
                ),
            )
        finally:
            sconn.close()
        hit_keys = [r["record_key"] for r in hits.get("results") or []]
        index_rows = [
            json.loads(line)
            for line in (comp_dir / "records.index.jsonl").read_text().splitlines()
            if line.strip()
        ]
        released_row = next(
            (r for r in index_rows if str(r.get("entity_id")) == released_entity), None
        )
        check(
            leg,
            "search_index_finds_record",
            released_row is not None and released_row["record_key"] in hit_keys,
            f"FTS5 index (contract-pinned) returns the released record "
            f"{released_row['record_key'] if released_row else None} for "
            f"q='P33.2 Composed Fixture' ({len(hit_keys)} hits)",
        )
        record_json = comp_dir / "entity" / "deployment" / f"{released_entity}.json"
        record = json.loads(record_json.read_text()) if record_json.exists() else {}
        anchors = [
            str(a.get("claim_id"))
            for a in (record.get("claim_anchors") or [])
            if isinstance(a, Mapping)
        ]
        bound_anchor = None
        if anchors:
            bound_anchor = conn.execute(
                "SELECT c.claim_id::text AS claim_id, ce.capture_id::text AS capture_id,"
                " ec.content_digest AS digest FROM claim c JOIN claim_evidence ce "
                "ON ce.claim_id = c.claim_id JOIN evidence_capture ec "
                "ON ec.capture_id = ce.capture_id "
                "WHERE c.claim_id = ANY(%s::uuid[]) LIMIT 1",
                (anchors,),
            ).fetchone()
        check(
            leg,
            "record_to_capture_trace",
            record_json.exists()
            and bool(anchors)
            and bound_anchor is not None
            and str(bound_anchor["digest"]) == fx_capture.digest,
            f"published record r/{pub[:16]}…/entity/deployment/{released_entity[:8]}… "
            f"→ {len(anchors)} claim anchors → claim_evidence → capture digest "
            f"{bound_anchor['digest'][:24] if bound_anchor else None}… == the "
            "fixture document multihash (record→claim→evidence→input bytes)",
        )
        route = f"r/{pub}/c/sig_graph/entity/deployment/{released_entity}/"
        access = route_access(registry_dir, route)
        selector = resolve_selector(registry_dir, as_of_world=None, as_of_belief=None, ruleset=None)
        check(
            leg,
            "serving_barrier",
            access.get("permitted") is True and selector.get("publication_id") == pub,
            f"route_access({route[:48]}…) permitted; current selector resolves {pub[:24]}…",
        )
        state["record_key"] = released_row["record_key"] if released_row else None
        state["anchors"] = anchors

        # =====================================================================
        # Leg E — correction: receiver → reviewer → application bridge
        # =====================================================================
        leg = "E.correction"
        from ops.journey_verify import run_intake_journey

        # The disputed claim is the CURRENT (latest, re-sighted) count claim
        # this release carries — the bridge refuses to revise superseded
        # history, so the correction targets the live assertion the public
        # record cites, not the first sighting the re-sighting closed.
        correction_target = count_ids[-1]
        proof_intake = run_intake_journey(
            dsn,
            publication_id=pub,
            record_key_value=str(state["record_key"]),
            # unique-per-run key — the journey derives report_id/receipt_id
            # from it (uuid5), so a rerun on the same DSN never collides;
            # the intake CHECK admits [A-Za-z0-9_-] only, no dots.
            report_key=f"p33-2-composed-{int(run_now.timestamp())}",
            target_claim_id=correction_target,
        )
        steps_ok = all(s["ok"] for s in proof_intake["steps"])
        check(
            leg,
            "intake_journey",
            steps_ok,
            "; ".join(f"{s['step']}={'ok' if s['ok'] else 'FAIL'}" for s in proof_intake["steps"]),
        )
        corr = conn.execute(
            "SELECT claim_id::text AS claim_id, value_num, value_text,"
            " revises_claim::text AS revises, correction_reason, sys_period FROM claim "
            "WHERE revises_claim = %s::uuid",
            (correction_target,),
        ).fetchone()
        prior = conn.execute(
            "SELECT NOT upper_inf(sys_period) AS closed FROM claim WHERE claim_id = %s::uuid",
            (correction_target,),
        ).fetchone()
        check(
            leg,
            "append_only_correction",
            corr is not None
            and corr["revises"] == correction_target
            and prior is not None
            and prior["closed"] is True
            and corr["value_text"] == "225",
            f"§16.6 close+revises: corrected claim {corr['claim_id'][:8] if corr else None}… "
            f"(value_text='225', correction_reason={corr['correction_reason'] if corr else None}) "
            f"revises {correction_target[:8]}…; prior sys_period closed="
            f"{prior['closed'] if prior else None} — no UPDATE anywhere",
        )
        state["correction"] = proof_intake
        state["corrected_claim_id"] = corr["claim_id"] if corr else None
    finally:
        conn.close()
        tconn.close()

    # =========================================================================
    # Assemble the proof
    # =========================================================================
    verdict = "pass" if all(c["ok"] for leg in legs for c in leg["checks"]) else "fail"
    built = state.get("build")
    comp_meta = {}
    if built is not None:
        for m in built.report.get("compartments") or []:
            comp_meta[str(m["compartment"])] = {
                "license": m.get("license"),
                "record_count": m.get("record_count"),
                "search_index_sha256": m.get("search_index_sha256"),
            }
    proof: dict[str, Any] = {
        "schema": PROOF_SCHEMA,
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "code_commit": commit,
        "renderer_revision": renderer_revision,
        "dsn": _dsn_label(dsn),
        "environment": {
            "live_verification": False,
            "docker_required": True,
            "intake_operational": intake_operational,
            "intake_staffed": intake_cfg.get("staffed"),
            "note": (
                "offline fixture verification — no hosted probe, no production "
                "publication, no live obligation discharged"
            ),
        },
        "inputs": {
            "fixture": {
                "path": str(FIXTURE_PATH.relative_to(REPO_ROOT)),
                "sha256": sha256_hex(fixture_bytes),
                "capture_digest": None,
            },
            "connector_fixture": {
                "path": str(ATLAS_FIXTURE.relative_to(REPO_ROOT)),
                "sha256": sha256_hex(atlas_bytes),
            },
        },
        "legs": legs,
        "release": {
            "publication_id": state.get("publication_id"),
            "manifest_sha256": (state.get("activation") or {}).get("manifest_sha256"),
            "compartments": comp_meta,
            "record_key": state.get("record_key"),
        },
        "correction": state.get("correction"),
        "verdict": verdict,
    }
    try:
        proof["inputs"]["fixture"]["capture_digest"] = fx_capture.digest
    except UnboundLocalError:
        pass
    (out_dir / PROOF_JSON).write_bytes(canonical_json(proof) + b"\n")
    (out_dir / PROOF_MD).write_text(_markdown(proof))
    return proof


def _dsn_label(dsn: str) -> str:
    """A non-secret DSN label for the proof — host/db name only, never creds."""
    tail = dsn.rsplit("/", 1)[-1]
    host = dsn.rsplit("@", 1)[-1].split("/")[0]
    return f"{host}/{tail.split('?')[0]}"


__all__ = [
    "PROOF_SCHEMA",
    "ComposedVerificationError",
    "run_composed_verification",
]
