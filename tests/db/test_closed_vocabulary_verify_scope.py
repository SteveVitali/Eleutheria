# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""OPS-SPINE-SCHEMA-DEPLOY regression: `closed_vocabulary` on a pre-existing
spine.

The change's own verify asserted *every* `vocab_predicate` row carries the
full registry metadata — true only on a fresh spine. Production `sig-pg`
carried 133 runtime-registered rows the pre-P35.14a sink auto-registration
minted with P19.4 defaults and `skos_concept_iri IS NULL`, so the assert
divided by zero and `sqitch deploy --verify` failed 19 changes in (the same
fresh-vs-existing verify class as D-P34.24b-1). The `@r11-vocab-verify-scope`
rework scopes the metadata assert to the rows the registry seeds actually
wrote — `skos_concept_iri IS NOT NULL` is written only by ontology-registry
seeds, so a pre-existing NULL-iri row `ON CONFLICT DO NOTHING` keeps is
outside the assert by design.

This test replays the production shape on a throwaway container: deploy up
to (not including) `closed_vocabulary`, insert the runtime-registration
shape — one registry id the change's `ON CONFLICT` must keep verbatim
(`deployed`, also one of the verify's six measured predicates) and one
never-registered id — then `deploy --verify` to the tip and a standalone
`sqitch verify`. Finally it plants a registry-IRI row with a *malformed* IRI
and proves the scoped assert still bites (`sqitch verify` fails): the fix
narrows scope, never to a tautology.
"""

from __future__ import annotations

import pytest
from conftest import (
    PG_DB,
    PG_PASSWORD,
    PG_USER,
    _docker_reachable,
    _require_or_skip,
    create_plan_database,
    pg_container,
    run_sqitch,
)

# The P19.4-era runtime auto-registration shape (db/src/db/claim_sink.py
# pre-P35.14a): datatype/definition carried, object_type 'literal',
# MODERATE/365/authoritative_source_wins defaults — and never a
# skos_concept_iri.
_RUNTIME_ROW_SQL = (
    "INSERT INTO vocab_predicate"
    "(predicate_id,vocab_version,value_datatype,object_type,definition,"
    " volatility_class,half_life_days,resolution_strategy) "
    "VALUES(%s,'1.0.0',%s,'literal',%s,'MODERATE',365,"
    "'authoritative_source_wins')"
)


def _connect(host: str, port: int):
    import psycopg

    return psycopg.connect(
        host=host,
        port=port,
        user=PG_USER,
        password=PG_PASSWORD,
        dbname=PG_DB,
        autocommit=True,
    )


def test_closed_vocabulary_verify_on_a_pre_existing_spine() -> None:
    if not _docker_reachable():
        _require_or_skip("the Docker daemon is not reachable")
    import docker.errors

    with pg_container() as (network, host, port):
        create_plan_database(host, port, PG_DB)
        # Stop just before closed_vocabulary: `er_rerun_login` is the last
        # plan change before the @r11-verify-membership rework boundary, and
        # everything closed_vocabulary needs (vocab_predicate itself,
        # claim_assertion_bindings, seed_vocab) is deployed by then.
        run_sqitch(network, "deploy", "--verify", "--to-change", "er_rerun_login")

        with _connect(host, port) as conn:
            # The runtime registry carries the strategy row itself before
            # minting predicates — the conftest fixture mirrors this.
            conn.execute(
                "INSERT INTO vocab_resolution_strategy(strategy_id,definition) "
                "VALUES('authoritative_source_wins','fixture') "
                "ON CONFLICT DO NOTHING"
            )
            # A registry id the change's ON CONFLICT DO NOTHING must keep
            # verbatim — the production case (runtime claims preceded the
            # closed vocabulary, so registry predicates auto-registered
            # NULL-iri before the seed ever ran).
            conn.execute(_RUNTIME_ROW_SQL, ("deployed", "boolean", "runtime fixture"))
            # A never-registered id — the bulk of sig-pg's 133 NULL rows.
            conn.execute(_RUNTIME_ROW_SQL, ("sig.test.runtime_pred", "string", "runtime fixture"))

        # The defect: this deploy --verify divided by zero at
        # closed_vocabulary on exactly this spine shape.
        run_sqitch(network, "deploy", "--verify")
        run_sqitch(network, "verify")

        with _connect(host, port) as conn:
            # Pre-existing rows keep their values verbatim — the NULL iri is
            # honest runtime state, never fabricated by the change.
            assert (
                conn.execute(
                    "SELECT count(*) FROM vocab_predicate WHERE skos_concept_iri IS NULL"
                ).fetchone()[0]
                == 2
            )
            row = conn.execute(
                "SELECT skos_concept_iri, definition FROM vocab_predicate"
                " WHERE predicate_id = 'deployed'"
            ).fetchone()
            assert row is not None and row[0] is None and row[1] == "runtime fixture"
            # The projection the change did write carries the canonical IRI.
            assert conn.execute(
                "SELECT skos_concept_iri FROM vocab_predicate"
                " WHERE predicate_id = 'camera_latitude'"
            ).fetchone()[0] == (
                "https://ontology.sig-project.org/vocab/predicate/1.0.0/camera_latitude"
            )

            # …and the assert still bites: a registry-IRI row whose IRI is
            # malformed is exactly the missing-metadata seed defect the
            # scoped assert exists to catch — `sqitch verify` must fail on
            # closed_vocabulary, never wave it through.
            conn.execute(
                "INSERT INTO vocab_predicate"
                "(predicate_id,vocab_version,value_datatype,object_type,"
                " definition,skos_concept_iri,volatility_class,half_life_days,"
                " resolution_strategy) "
                "VALUES('sig.test.bad_iri','1.0.0','string','literal','fixture',"
                "'https://ontology.sig-project.org/vocab/predicate/1.0.0/WRONG',"
                "'MODERATE',365,'authoritative_source_wins')"
            )
        with pytest.raises(docker.errors.ContainerError) as err:
            run_sqitch(network, "verify")
        assert b"closed_vocabulary" in err.value.stderr, err.value.stderr
