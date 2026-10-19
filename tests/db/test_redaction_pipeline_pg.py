# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The redaction pipeline over the real spine (P36.15 staging leg, Docker).

Runs the production path end to end against the deployed schema: an OCFL
capture store over a tmp root, the *real* ``review_item``/``review_decision``
tables through :class:`resolution.review_pg.PgReviewQueue`, and the public read
surface through the *real* ``PgReadStore.capture`` SQL — bound to the test's
rolled-back connection through a one-connection pool stub so nothing commits.

The recorded decisions here are synthetic fixture decisions (a role label + a
DB-stamped time) — they stand in for the human act; nothing claims a real
redaction was decided.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from conftest import insert_claim, seed_claim_prerequisites
from connectors.capture_ocfl import OcflCaptureStore
from connectors.redaction_pipeline import (
    enqueue_proposal,
    propose_redaction,
    run_redaction,
)
from evidence.ocfl import OcflStore
from evidence.redaction import RedactionReviewRequired, extract_text
from evidence.storage import LocalFileStore
from resolution.review_pg import PgReviewQueue

PARENT_TEXT = (
    "Minutes: the contract is approved. Signed by Officer Jane M. Doe. Effective 2026-09-01."
)


class _OneConnPool:
    """Hands ``PgReadStore._pooled`` the test's rolled-back connection."""

    timeout = 5.0

    def __init__(self, conn: Any) -> None:
        self._conn = conn

    def connection(self, timeout: float | None = None) -> Any:
        @contextmanager
        def _cm() -> Iterator[Any]:
            yield self._conn

        return _cm()

    def check(self) -> None:  # pool-health hook the retry path calls
        return None

    def get_stats(self) -> dict[str, int]:
        return {}


def _read_store_over(conn: Any) -> Any:
    """A real ``PgReadStore`` whose pool is the test's rolled-back conn."""
    from api.store_pg import PgReadStore

    store = PgReadStore.__new__(PgReadStore)
    store._dsn = "test"
    store._ruleset = None
    store._as_of = None
    store._role = None
    store._search_timeout_ms = 0
    store._connect_kwargs = {}
    store._pool = _OneConnPool(conn)
    store._local = threading.local()
    store._annotation_lock = threading.Lock()
    store._annotation_cache = None
    store._last_annotation_view = None
    store._shaping_cache = None
    return store


def _seed_capture_chain(conn: Any, tmp_path: Any) -> dict[str, Any]:
    """Artifact + parent capture + bound claim excerpt, all fixture-synthetic."""
    prereqs = seed_claim_prerequisites(conn)
    claim_id = insert_claim(conn, prereqs, value_text="36", value_num=36)

    store = OcflCaptureStore(OcflStore(LocalFileStore(str(tmp_path))))
    ref = store.put(PARENT_TEXT.encode(), media_type="text/plain", source_uri="urn:p36-15:minutes")

    cur = conn.cursor()
    cur.execute(
        "INSERT INTO source_registry"
        "(source_id,name,source_kind,default_reliability,"
        " reliability_justification,rights_id,custody_posture,compact_status,"
        " ingestion_permitted,robots_policy) "
        "VALUES('p36-15-source','p36-15 fixture','records','R1','fixture',"
        "       %s,'MIRROR','in_scope',false,'fixture')",
        (prereqs["rights_id"],),
    )
    cur.execute(
        "INSERT INTO evidence_artifact"
        "(source_id,stable_locator,artifact_type,acquisition_method,"
        " primary_or_secondary,rights_id,capture_status) "
        "VALUES('p36-15-source','urn:p36-15:minutes','minutes','fixture',"
        "       'primary',%s,'captured') RETURNING artifact_id",
        (prereqs["rights_id"],),
    )
    artifact_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO evidence_capture"
        "(artifact_id,content_digest,byte_size,media_type,retrieved_at,"
        " retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        " capture_method,capture_tool_version) "
        "VALUES(%s,%s,%s,'text/plain',now(),%s,%s,%s,'public','fixture','0') "
        "RETURNING capture_id",
        (
            artifact_id,
            ref.digest,
            len(PARENT_TEXT.encode()),
            prereqs["run_id"],
            ref.ocfl_object_id,
            ref.ocfl_version,
        ),
    )
    capture_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role,excerpt) "
        "VALUES(%s,%s,'establishes',%s)",
        (claim_id, capture_id, "Signed by Officer Jane M. Doe."),
    )
    return {
        "store": store,
        "queue": PgReviewQueue(conn),
        "artifact_id": str(artifact_id),
        "capture_id": str(capture_id),
        "claim_id": str(claim_id),
        "ref": ref,
        "run_id": prereqs["run_id"],
    }


def test_reviewed_redaction_round_trips_through_the_spine(conn: Any, tmp_path: Any) -> None:
    """Propose → recorded accept → apply → derivative row → public read."""
    env = _seed_capture_chain(conn, tmp_path)
    queue: PgReviewQueue = env["queue"]

    item = propose_redaction(
        parent_capture_id=env["capture_id"],
        parent_digest=env["ref"].digest,
        parent_bytes=env["store"].get(env["ref"].digest),
        media_type="text/plain",
        literals=["Jane M. Doe"],
        method="text-layer-substitution",
        version="1",
    )
    enqueue_proposal(queue, item)
    # The append-only human review — a synthetic fixture decision (a ROLE,
    # never a personal name); decided_at is stamped by the database.
    queue.decide(item.item_id, "accept", reviewer="records officer")

    result = run_redaction(env["store"], queue, item_id=item.item_id)
    deriv = result.capture_ref

    # The derivative row lands on the spine — a NEW capture row, parent-linked,
    # redaction_* recorded; the parent row is never edited.
    conn.execute(
        "INSERT INTO evidence_capture"
        "(artifact_id,content_digest,byte_size,media_type,retrieved_at,"
        " retrieved_by_run_id,ocfl_object_id,ocfl_version,storage_tier,"
        " capture_method,capture_tool_version,redaction_applied,"
        " redaction_method,redaction_version,parent_capture_id) "
        "VALUES(%s,%s,%s,'text/plain',now(),%s,%s,%s,'public','fixture','0',"
        "       true,%s,%s,%s)",
        (
            env["artifact_id"],
            deriv.digest,
            deriv.byte_size,
            env["run_id"],
            deriv.ocfl_object_id,
            deriv.ocfl_version,
            "text-layer-substitution",
            "1",
            env["capture_id"],
        ),
    )
    deriv_id = conn.execute(
        "SELECT capture_id FROM evidence_capture WHERE parent_capture_id = %s",
        (env["capture_id"],),
    ).fetchone()[0]
    conn.execute(
        "INSERT INTO claim_evidence(claim_id,capture_id,role,excerpt) "
        "VALUES(%s,%s,'establishes',%s)",
        (env["claim_id"], deriv_id, "Signed by Officer [redacted]."),
    )

    # The review record is real rows on the curation mechanism — append-only.
    decisions = queue.decisions(item.item_id)
    assert len(decisions) == 1 and decisions[0].reviewer == "records officer"

    # The public read surface resolves the derivative metadata through the
    # spine — and P35.31's served-tier floor (F-400) then labels the rep
    # honestly: this fixture's rights record cannot evidence a lane, so the
    # recorded 'public' row is TIGHTENED to sealed at read (derived_at_read,
    # never a silent 'public' upgrade). The positive "the derivative's excerpt
    # is served" contract is pinned on the public-representation unit and API
    # honesty tests; here the raw excerpt is nowhere in the served rep.
    read = _read_store_over(conn)
    meta = read.capture(env["artifact_id"], env["capture_id"])
    assert meta is not None
    assert meta.derivative is not None
    assert meta.derivative.content_digest == deriv.digest
    assert meta.excerpt == "Signed by Officer Jane M. Doe."
    assert meta.tier_basis == "derived_at_read" and meta.recorded_tier == "public"
    from evidence.tiers import public_representation

    rep = public_representation(meta)
    assert rep["tier"] == "sealed" and rep["tier_basis"] == "derived_at_read"
    assert rep["recorded_tier"] == "public"
    assert "excerpt" not in rep and "Jane M. Doe" not in str(rep)

    # The derivative's bytes physically omit the redacted span.
    deriv_bytes = env["store"].get(deriv.digest)
    assert b"Jane M. Doe" not in deriv_bytes
    assert "Jane M. Doe" not in extract_text(deriv_bytes, "text/plain")
    assert env["store"].get(env["ref"].digest) == PARENT_TEXT.encode()


def test_apply_over_pg_refuses_without_a_recorded_review(conn: Any, tmp_path: Any) -> None:
    env = _seed_capture_chain(conn, tmp_path)
    item = propose_redaction(
        parent_capture_id=env["capture_id"],
        parent_digest=env["ref"].digest,
        parent_bytes=env["store"].get(env["ref"].digest),
        media_type="text/plain",
        literals=["Jane M. Doe"],
        method="text-layer-substitution",
        version="1",
    )
    enqueue_proposal(env["queue"], item)
    with pytest.raises(RedactionReviewRequired):
        run_redaction(env["store"], env["queue"], item_id=item.item_id)
