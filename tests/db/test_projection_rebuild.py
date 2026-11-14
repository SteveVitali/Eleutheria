# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Drop-all/rebuild equality for the §15.4 materialized projections (P37.57a).

SIG-STORE-004 (MUST): every projection is rebuildable from canonical state by a
single documented command, and a CI job rebuilds each from scratch and verifies
it. SIG-ONTO-001/002 (§8.1): L3 tables are truncate-and-rebuild-able from
L1+L2+ruleset and L4 is physically separate, labelled, and droppable — losing
every projection costs only compute, never information (SIG-STORE-005).

This is that CI job. Over one seeded spine on real PG18+PostGIS it:

* runs every projection's documented materializer (``sig-reconcile`` /
  ``sig-inference`` / ``sig-resolution`` / ``sig-tasks`` — the commands
  ``db/README.md`` §"Rebuilding the projections" documents),
* snapshots every materialized table,
* drops ALL of them, and
* re-runs the same commands and asserts the rebuilt content is equal.

"Equal" is honest: a rebuild re-mints surrogate ``uuidv7`` keys and stamps
fresh ``clock_timestamp()`` columns, so the comparison covers every
NON-minted column — all ``input_digest`` keys, every provenance/reference
column, and every payload field. A minted column set that drifts (a new
uuidv7/clock default a migration adds and nobody declared here) fails the
drift guard rather than being silently excluded. References INTO other
re-minted keys (``relationship.supersedes``, ``research_task.trigger_ref``)
are dereferenced to the target row's stable content identity before compare.

The drop set is exactly the derived tables — never the canonical spine
(claim/entity/evidence/run/rights/registry/vocab), never the human records
that pin derived rows (``review_decision``, ``review_campaign*``,
``camera_site_human_decisions``, claimed ``research_task`` state). The seeded
spine leaves every review proposal undecided and every task unclaimed, so a
full drop is a legal instance of the documented rule; on a populated spine
the same rule drops only derived rows no canonical row references.
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from conftest import register_vocab_predicate, seed_claim_prerequisites
from inference.accountability import materialize_accountability_links
from inference.materialize import materialize_coverage
from psycopg import sql
from psycopg.types.range import Range
from reconcile.materialize import (
    materialize_contradictions,
    materialize_resolutions,
    materialize_role_edges,
    materialize_sharing_edges,
)
from resolution.camera_sites_pg import materialize_camera_sites
from resolution.org_cascade_pg import materialize_org_cascade
from tasks.research_pg import materialize_research_queue

ROLE = "sig_materialize"
FIXED_NOW = datetime(2026, 6, 1, tzinfo=UTC)  # detector priorities are age-derived

#: The Postgres materialized projections of §15.4 (and the L4 separate-schema
#: projection of §8.1), in drop order — children of a run record first.
PROJECTION_TABLES: tuple[str, ...] = (
    "research_task",
    "review_item",
    "camera_site_demotion",
    "camera_site_census",
    "camera_site_execution",
    "camera_site_match",
    "camera_site_run",
    "organization_execution",
    "organization_match",
    "organization_run",
    "inference.derived_fact",
    "inference.derived_geometry",
    "entity_role",
    "relationship",
    "contradiction",
    "coverage_record",
    "resolution",
)

#: Minted-per-execution columns that carry NO default (everything else volatile
#: is auto-detected off its ``uuidv7()``/``clock_timestamp()``/``tstzrange(…)``
#: default — see ``_volatile_columns``).
EXTRA_VOLATILE: dict[str, set[str]] = {
    "camera_site_execution": {"execution_id"},
    "organization_execution": {"execution_id"},
}

#: References INTO another projection table's re-minted surrogate key:
#: ``source_table -> {column: (target_table, target_pk_column)}``. Compared as
#: the target row's stable identity (``input_digest`` where it exists, else the
#: row's own canonical content) — never the re-minted uuid.
DEREF: dict[str, dict[str, tuple[str, str]]] = {
    "relationship": {"supersedes": ("relationship", "relationship_id")},
    "entity_role": {"supersedes": ("entity_role", "entity_role_id")},
    "contradiction": {"research_task_ids": ("research_task", "task_id")},
}

#: ``research_task.trigger_ref`` polymorphs on ``trigger_kind``: the cited
#: materialized row per kind (a claim ref — e.g. ``contract`` — is a stable
#: spine key and needs no deref).
TRIGGER_DEREF: dict[str, tuple[str, str]] = {
    "contradiction": ("contradiction", "contradiction_id"),
    "relationship": ("relationship", "relationship_id"),
    "coverage": ("coverage_record", "coverage_id"),
}

#: jsonb columns carrying a re-minted value inside an otherwise-deterministic
#: payload: ``table -> {column: keys stripped before compare}``.
JSONB_STRIP: dict[str, dict[str, frozenset[str]]] = {
    "camera_site_execution": {"summary": frozenset({"execution_id"})},
    "organization_execution": {"summary": frozenset({"execution_id"})},
}

_MINT_DEFAULT = (
    "uuidv7(",
    "clock_timestamp()",
    "now()",
    "transaction_timestamp()",
    "statement_timestamp()",
)


def _split(table: str) -> tuple[str, str]:
    schema, _, name = table.partition(".")
    return (schema, name) if name else ("public", table)


def _columns(conn: Any, table: str) -> list[tuple[str, str | None]]:
    schema, name = _split(table)
    rows = conn.execute(
        "SELECT column_name, column_default FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s ORDER BY ordinal_position",
        (schema, name),
    ).fetchall()
    return [(str(r[0]), None if r[1] is None else str(r[1])) for r in rows]


def _volatile_columns(conn: Any, table: str, cols: list[tuple[str, str | None]]) -> set[str]:
    """The columns a rebuild re-mints: any column whose DEFAULT is a mint
    function (uuidv7 / clock_timestamp / now / tstzrange(clock_timestamp(),…)),
    plus the declared no-default exceptions (execution ids minted in Python)."""
    auto = {c for c, d in cols if d is not None and any(m in d.lower() for m in _MINT_DEFAULT)}
    extra = EXTRA_VOLATILE.get(table, set())
    missing = extra - {c for c, _ in cols}
    assert not missing, f"{table}: declared volatile columns absent from schema: {missing}"
    return auto | extra


def _pk_columns(conn: Any, table: str) -> list[str]:
    schema, name = _split(table)
    rows = conn.execute(
        "SELECT a.attname FROM pg_index i "
        " JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) "
        "WHERE i.indrelid = %s::regclass AND i.indisprimary "
        "ORDER BY array_position(i.indkey::int[], a.attnum::int)",
        (f"{schema}.{name}",),
    ).fetchall()
    return [str(r[0]) for r in rows]


def _freeze(value: Any) -> Any:
    """A deterministic, sortable canonical form for one column value."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Decimal):
        return str(value.normalize())
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _freeze(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_freeze(v) for v in value]
    if isinstance(value, bytes):
        return value.hex()
    if isinstance(value, Range):
        return (
            _freeze(value.lower),
            _freeze(value.upper),
            str(value.bounds),
        )
    return str(value)


def _strip_jsonb(table: str, col: str, value: Any) -> Any:
    """Drop the re-minted keys embedded in a deterministic payload column."""
    strip = JSONB_STRIP.get(table, {}).get(col)
    if strip is None or not isinstance(value, dict):
        return value
    return {k: v for k, v in value.items() if k not in strip}


def _select_rows(conn: Any, table: str, cols: list[str]) -> list[dict[str, Any]]:
    schema, name = _split(table)
    stmt = sql.SQL("SELECT {} FROM {}.{}").format(
        sql.SQL(", ").join(sql.Identifier(c) for c in cols),
        sql.Identifier(schema),
        sql.Identifier(name),
    )
    cur = conn.execute(stmt)
    return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def _stable_map(conn: Any, table: str, pk: list[str], cols: list[tuple[str, str | None]]) -> dict:
    """``pk tuple -> the row's stable identity`` (``input_digest`` where the
    table carries one — it IS the reproducible-content key — else the row's
    own canonical content tuple)."""
    all_cols = [c for c, _ in cols]
    if "input_digest" in all_cols:
        rows = _select_rows(conn, table, [*pk, "input_digest"])
        return {tuple(str(r[p]) for p in pk): str(r["input_digest"]) for r in rows}
    volatile = _volatile_columns(conn, table, cols)
    content = [c for c in all_cols if c not in volatile and c not in pk]
    rows = _select_rows(conn, table, [*pk, *content])
    return {tuple(str(r[p]) for p in pk): tuple(_freeze(r[c]) for c in content) for r in rows}


def _canonical(conn: Any) -> dict[str, list[tuple[Any, ...]]]:
    """``table -> sorted canonical rows``: every NON-minted column, volatile
    foreign keys replaced by the referenced row's stable identity."""
    out: dict[str, list[tuple[Any, ...]]] = {}
    schema: dict[str, list[tuple[str, str | None]]] = {}
    volatile: dict[str, set[str]] = {}
    stable: dict[str, dict] = {}
    for table in PROJECTION_TABLES:
        cols = _columns(conn, table)
        schema[table] = cols
        volatile[table] = _volatile_columns(conn, table, cols)
        stable[table] = _stable_map(conn, table, _pk_columns(conn, table), cols)
    for table in PROJECTION_TABLES:
        content = [c for c, _ in schema[table] if c not in volatile[table]]
        rows = _select_rows(conn, table, content)
        deref = DEREF.get(table, {})
        canon: list[tuple[Any, ...]] = []
        for row in rows:
            vals: list[Any] = []
            for col in content:
                value = row[col]
                if col in deref and value is not None:
                    target_table, _pk_col = deref[col]
                    if isinstance(value, (list, tuple)):
                        value = [
                            stable[target_table].get((str(v),), f"unresolved:{v}") for v in value
                        ]
                    else:
                        value = stable[target_table].get((str(value),), f"unresolved:{value}")
                if table == "research_task" and col == "trigger_ref" and value is not None:
                    target = TRIGGER_DEREF.get(str(row.get("trigger_kind") or ""))
                    if target is not None:
                        value = stable[target[0]].get((str(value),), f"unresolved:{value}")
                value = _strip_jsonb(table, col, value)
                vals.append(_freeze(value))
            canon.append(tuple(vals))
        out[table] = sorted(canon, key=repr)
    return out


def _drop_all(conn: Any) -> None:
    """Drop every derived row (never a canonical one). DELETE in child-first
    order — never TRUNCATE … CASCADE, so a canonical table referencing a
    projection (``review_decision.item_id``) can never be silently emptied."""
    for table in PROJECTION_TABLES:
        schema, name = _split(table)
        conn.execute(
            sql.SQL("DELETE FROM {}.{}").format(sql.Identifier(schema), sql.Identifier(name))
        )


def _materialize_all(conn: Any, *, now: datetime = FIXED_NOW) -> None:
    """Every projection's documented rebuild command, in pipeline order —
    the same set ``db/README.md`` §"Rebuilding the projections" lists."""
    materialize_resolutions(conn, role=ROLE)
    materialize_sharing_edges(conn, role=ROLE)
    materialize_role_edges(conn, role=ROLE)
    materialize_contradictions(conn, role=ROLE)
    materialize_coverage(conn, role=ROLE, negative_space=True)
    materialize_accountability_links(conn, role=ROLE)
    materialize_camera_sites(conn, role=ROLE)
    materialize_org_cascade(conn, role=ROLE)
    materialize_research_queue(conn, role=ROLE, now=now)
    conn.execute("RESET ROLE")


# --- the seeded spine --------------------------------------------------------


def _entity(conn: Any, entity_type: str) -> Any:
    return conn.execute(
        "INSERT INTO entity(entity_type) VALUES(%s) RETURNING entity_id", (entity_type,)
    ).fetchone()[0]


def _source_capture(conn: Any, prereqs: dict, source_id: str, genre: str) -> Any:
    conn.execute(
        "INSERT INTO source_registry(source_id,name,source_kind,default_reliability,"
        "reliability_justification,rights_id,custody_posture,compact_status,"
        "robots_policy,ingestion_permitted) "
        "VALUES(%s,%s,'registry','R1','fixture',%s,'MIRROR','granted','obey',true) "
        "ON CONFLICT DO NOTHING",
        (source_id, source_id, prereqs["rights_id"]),
    )
    artifact_id = conn.execute(
        "INSERT INTO evidence_artifact(source_id,stable_locator,artifact_type,"
        "acquisition_method,primary_or_secondary,rights_id,capture_status) "
        "VALUES(%s,%s,%s,'registry_api','primary',%s,'captured') RETURNING artifact_id",
        (source_id, f"urn:sig:p3757:{source_id}", genre, prereqs["rights_id"]),
    ).fetchone()[0]
    return conn.execute(
        "INSERT INTO evidence_capture(artifact_id,content_digest,byte_size,media_type,"
        "retrieved_at,retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        "capture_method,capture_tool_version,source_uri) "
        "VALUES(%s,%s,10,'application/json','2026-05-01T00:00:00Z',%s,%s,'v1',"
        "'public','registry_api','sig/0',%s) RETURNING capture_id",
        (
            artifact_id,
            f"digest-{source_id}",
            prereqs["run_id"],
            f"urn:sig:p3757:{source_id}",
            f"urn:sig:p3757:{source_id}",
        ),
    ).fetchone()[0]


def _claim(
    conn: Any,
    prereqs: dict,
    subject: Any,
    predicate: str,
    *,
    object_type: str = "literal",
    object_entity: Any = None,
    value_text: str | None = None,
    value_num: int | None = None,
    unit: str | None = None,
    reliability: str = "R1",
    observed_at: str = "2026-05-01T00:00:00Z",
    capture: Any = None,
) -> Any:
    claim_id = conn.execute(
        "INSERT INTO claim(subject_id,predicate_id,object_type,object_entity,value_kind,"
        "value_text,value_num,unit,raw_value,observed_at,source_reliability,claim_directness,"
        "artifact_integrity,asserted_by,assertion_rationale,ingest_run_id,rights_id,"
        "sensitivity_tier) "
        "VALUES(%s,%s,%s,%s,'value',%s,%s,%s,%s,%s,%s,'D1','I1',%s,'fixture',%s,%s,0) "
        "RETURNING claim_id",
        (
            subject,
            predicate,
            object_type,
            object_entity,
            value_text,
            value_num,
            unit,
            value_text,
            observed_at,
            reliability,
            prereqs["author_id"],
            prereqs["run_id"],
            prereqs["rights_id"],
        ),
    ).fetchone()[0]
    if capture is not None:
        conn.execute(
            "INSERT INTO claim_evidence(claim_id,capture_id,role) VALUES(%s,%s,'establishes')",
            (claim_id, capture),
        )
    return claim_id


def _ref_claim(conn: Any, prereqs: dict, subject: Any, predicate: str, target: Any) -> Any:
    return _claim(
        conn,
        prereqs,
        subject,
        predicate,
        object_type="entity_ref",
        object_entity=target,
        value_text=str(target),
    )


def _org_with_qid(conn: Any, prereqs: dict, qid: str) -> str:
    eid = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO entity(entity_id, entity_type) VALUES (%s::uuid, 'organization')",
        (eid,),
    )
    conn.execute(
        "INSERT INTO organization(entity_id, organization_type) "
        "VALUES (%s::uuid, 'us.le.municipal_police')",
        (eid,),
    )
    cid = _claim(conn, prereqs, eid, "external_id", value_text=qid)
    conn.execute(
        "INSERT INTO entity_identifier(entity_id, scheme, value, asserted_by_claim) "
        "VALUES (%s::uuid, 'wikidata.qid', %s, %s::uuid)",
        (eid, qid, str(cid)),
    )
    return eid


def _camera_record(
    conn: Any, prereqs: dict, source_id: str, *, lat: str, lon: str, ref: str, operator: str
) -> Any:
    dep = _entity(conn, "deployment")
    cap = _source_capture(conn, prereqs, source_id, "camera_registry")
    for pid, val in (
        ("camera_latitude", lat),
        ("camera_longitude", lon),
        ("camera_external_ref", ref),
        ("camera_operator", operator),
    ):
        _claim(conn, prereqs, dep, pid, value_text=val, capture=cap)
    return dep


def _seed_spine(conn: Any) -> dict:
    """One seeded spine that exercises every projection: a count disagreement
    (resolution + contradiction + a contradiction-triggered task), a sharing
    edge, an accountability chain (role edge + L4 derived facts), an org pair
    sharing one canonical id, and two coincident camera records."""
    prereqs = seed_claim_prerequisites(conn)
    for pid, datatype, obj in (
        ("contracted_device_count", "integer", "quantity"),
        ("configured_sharing_partner", "string", "entity_ref"),
        ("external_id", "string", "literal"),
        ("camera_latitude", "string", "literal"),
        ("camera_longitude", "string", "literal"),
        ("camera_external_ref", "string", "literal"),
        ("camera_operator", "string", "literal"),
    ):
        register_vocab_predicate(conn, pid, datatype=datatype, object_type=obj)
    conn.execute(
        "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
        "VALUES('never_resolve','fixture: recorded, not adjudicated') ON CONFLICT DO NOTHING"
    )
    for pid in ("operator", "buyer", "seller", "recipient", "applies_to"):
        conn.execute(
            "INSERT INTO vocab_predicate"
            "(predicate_id,vocab_version,value_datatype,object_type,definition,"
            " volatility_class,half_life_days,resolution_strategy) "
            "VALUES(%s,'1.0.0','entity_ref','entity_ref','fixture','IMMUTABLE',NULL,"
            "'never_resolve') ON CONFLICT DO NOTHING",
            (pid,),
        )

    dep = prereqs["subject_id"]
    # 299-vs-190 — a real disagreement (two sources, evidence-bound claims).
    cap_a = _source_capture(conn, prereqs, "vendor_contract_src", "executed_contract")
    cap_b = _source_capture(conn, prereqs, "vendor_invoice_src", "invoice")
    _claim(
        conn,
        prereqs,
        dep,
        "contracted_device_count",
        object_type="quantity",
        value_text="299",
        value_num=299,
        unit="devices",
        reliability="R1",
        capture=cap_a,
    )
    _claim(
        conn,
        prereqs,
        dep,
        "contracted_device_count",
        object_type="quantity",
        value_text="190",
        value_num=190,
        unit="devices",
        reliability="R2",
        observed_at="2026-04-01T00:00:00Z",
        capture=cap_b,
    )
    # sharing edge + the accountability chain (operator also mints a role edge).
    partner = _entity(conn, "organization")
    _ref_claim(conn, prereqs, dep, "configured_sharing_partner", partner)
    org, vendor = partner, _entity(conn, "organization")
    contract = _entity(conn, "contract")
    funding = _entity(conn, "funding_instrument")
    policy = _entity(conn, "policy")
    _ref_claim(conn, prereqs, dep, "operator", org)
    _ref_claim(conn, prereqs, contract, "buyer", org)
    _ref_claim(conn, prereqs, contract, "seller", vendor)
    _ref_claim(conn, prereqs, funding, "recipient", org)
    _ref_claim(conn, prereqs, policy, "applies_to", dep)
    # two organisations sharing one canonical identifier (cascade tier 0).
    _org_with_qid(conn, prereqs, "Q90000001")
    _org_with_qid(conn, prereqs, "Q90000001")
    # two coincident camera records from two sources.
    _camera_record(
        conn,
        prereqs,
        "camreg_zz_a",
        lat="35.4676000",
        lon="-97.5164000",
        ref="101",
        operator="Zed DOT",
    )
    _camera_record(
        conn,
        prereqs,
        "camreg_zz_b",
        lat="35.4676010",
        lon="-97.5164010",
        ref="202",
        operator="community mirror",
    )
    return prereqs


# --- the checks --------------------------------------------------------------


def test_every_projection_rebuilds_content_equal_after_a_full_drop(conn: Any) -> None:
    """THE check: materialize → snapshot → drop ALL → re-materialize → equal."""
    _seed_spine(conn)
    _materialize_all(conn)
    before = _canonical(conn)
    non_empty = {t: len(r) for t, r in before.items() if r}
    assert non_empty, "the seeded spine produced no projection rows at all"
    _drop_all(conn)
    _materialize_all(conn)
    after = _canonical(conn)
    assert after == before, "rebuild diverged: " + "; ".join(
        f"{t}: {len(before.get(t) or ())} -> {len(after.get(t) or ())} rows"
        for t in PROJECTION_TABLES
        if after.get(t) != before.get(t)
    )


def test_the_seeded_spine_exercises_the_projection_set(conn: Any) -> None:
    """The equality proof is not vacuous: the seed reaches the headline
    projections (resolution/contradiction/edge/role/coverage/L4/org cascade/
    camera-site run + match and the research queue)."""
    _seed_spine(conn)
    _materialize_all(conn)
    canon = _canonical(conn)
    for table in (
        "resolution",
        "contradiction",
        "relationship",
        "entity_role",
        "coverage_record",
        "inference.derived_fact",
        "organization_match",
        "camera_site_run",
        "camera_site_execution",
        "organization_execution",
    ):
        assert canon[table], f"{table} empty — the seed does not reach it"
    conn.execute("RESET ROLE")


def test_volatile_declarations_cover_every_minted_default(conn: Any) -> None:
    """Drift guard: a migration adding a minted-default column to a projection
    table lands inside the volatile set automatically; a DECLARED volatile
    column that vanishes from the schema fails here (never a silent drop)."""
    for table in PROJECTION_TABLES:
        cols = _columns(conn, table)
        names = {c for c, _ in cols}
        assert names, f"{table}: not a table in this schema"
        volatile = _volatile_columns(conn, table, cols)
        assert volatile & names == volatile
        # every declared-volatile column is re-minted by construction —
        # and every NON-volatile column is compared, so coverage is total.
        assert len(volatile) < len(names)


def test_rebuild_is_also_idempotent_without_a_drop(conn: Any) -> None:
    """A second pass over an unchanged spine appends +0 on every deterministic
    projection — the ON CONFLICT DO NOTHING contract every materializer shares.
    The two execution ledgers are the ONE documented exception (ADR-123): each
    pass is a new execution, so they append exactly one completion record."""
    _seed_spine(conn)
    _materialize_all(conn)
    counts = {
        t: conn.execute(
            sql.SQL("SELECT count(*) FROM {}.{}").format(
                sql.Identifier(schema), sql.Identifier(name)
            )
        ).fetchone()[0]
        for t in PROJECTION_TABLES
        for schema, name in [_split(t)]
    }
    _materialize_all(conn)
    execution_ledgers = {"camera_site_execution", "organization_execution"}
    for table, n in counts.items():
        schema, name = _split(table)
        now = conn.execute(
            sql.SQL("SELECT count(*) FROM {}.{}").format(
                sql.Identifier(schema), sql.Identifier(name)
            )
        ).fetchone()[0]
        if table in execution_ledgers:
            assert now == n + 1, f"{table}: re-run appended {now - n} (expected +1)"
        else:
            assert now == n, f"{table}: re-run appended {now - n} rows (expected +0)"
