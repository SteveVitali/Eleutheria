# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The operator-only claim purge seam (P37.71; ADR-181/WV-06 + ADR-189/WV-11).

``sig_purge_claims`` — created by the ``operator_purge`` sqitch change — is the
ONE database function that may delete claim rows, the sole exception to
SIG-STORE-011. This module is only the caller: it validates the recorded
inputs and hands the call to the function. The actual enforcement is in the
database:

* EXECUTE is granted to the ``sig_purge_operator`` role and nothing else; the
  role is NOLOGIN and membership is never granted by a migration or an agent —
  the operator provisions a login member (Secret Manager credential only) at
  first use.
* The function itself re-checks membership, refuses an unnamed material set or
  an unnamed go, refuses a claim any recorded decision references, and writes
  the tombstone + audit rows in the same transaction as the delete.

Nothing here runs the function without the operator's in-ticket go naming the
material — the ``authority_ref`` argument carries that go's reference verbatim
and an empty one is refused. There is no agent path.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

# The closed tombstone/audit category vocabulary — mirrors the CHECK constraint
# in db/deploy/operator_purge.sql and DELETION_CATEGORIES in
# ops/src/ops/operator_deletion.py; a test asserts the three stay equal.
PURGE_CATEGORIES = (
    "categorically_excluded",  # SIG-PUB-002 material SIG must not hold at all
    "privacy_harm",
    "legal_demand",
    "security_concern",
    "copyright_claim",
    "rights_withdrawal",
)

PURGE_FUNCTION = "sig_purge_claims"


class PurgeError(Exception):
    """A refused or failed purge call — never retried silently."""


def _claim_ids(claim_ids: Iterable[str]) -> list[str]:
    """Validate the named material: a non-empty set of uuid-shaped ids."""
    ids: list[str] = []
    for raw in claim_ids:
        try:
            ids.append(str(uuid.UUID(str(raw))))
        except (ValueError, AttributeError) as exc:
            raise PurgeError(f"not a claim uuid: {raw!r}") from exc
    if not ids:
        raise PurgeError("no claim ids named — the go names the material")
    return ids


def purge_claims(
    dsn: str,
    claim_ids: Iterable[str],
    *,
    category: str,
    authority_ref: str,
    decision_entry_id: str | None = None,
    connect: Any = None,
) -> dict[str, Any]:
    """Invoke ``sig_purge_claims`` over ``dsn`` and return the audit record.

    ``authority_ref`` is the in-ticket go naming the material (required, and
    the function refuses an empty one). ``connect`` is injectable for tests;
    the real path uses psycopg. Returns the tombstone + audit ids and the
    recorded detail; raises ``PurgeError`` on a refused call.
    """
    ids = _claim_ids(claim_ids)
    if category not in PURGE_CATEGORIES:
        raise PurgeError(f"category {category!r} is not in the closed vocabulary")
    if not authority_ref or not authority_ref.strip():
        raise PurgeError("the in-ticket go must be named (authority_ref)")
    if connect is None:
        import psycopg

        connect = psycopg.connect
    try:
        with connect(dsn) as conn:
            row = conn.execute(
                "SELECT sig_purge_claims(%s::uuid[], %s, %s, %s)",
                (ids, category, authority_ref, decision_entry_id),
            ).fetchone()
            tombstone_id = row[0]
            audit = conn.execute(
                "SELECT audit_id, executed_by, executed_role, detail "
                "FROM purge_audit WHERE tombstone_id = %s",
                (tombstone_id,),
            ).fetchone()
            conn.commit()
    except PurgeError:
        raise
    except Exception as exc:  # noqa: BLE001 - the function's refusals surface here
        raise PurgeError(str(exc)) from exc
    return {
        "tombstone_id": str(tombstone_id),
        "audit_id": str(audit[0]),
        "executed_by": audit[1],
        "executed_role": audit[2],
        "detail": audit[3],
    }
