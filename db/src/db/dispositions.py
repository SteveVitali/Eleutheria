# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The publication-disposition registry over the spine (P32.5 / ADR-124, SIG-TRUST-006).

One append-only table (``publication_disposition``, sqitch ``publication_dispositions``)
records every publication decision — ``allow``/``withhold``/``restrict``/``withdraw`` —
with its policy version, authority, safe reason category, decision instant and optional
evidence/correction linkage. The spine itself is never rewritten: a correction or a
withdrawal is a NEW row, and the *effective* disposition is the latest one at access
time — so a withhold recorded in release R2 still denies the data under a rollback to
R1 on every origin/cache/archive path.

Two carriers of ONE rule (the same discipline as ADR-123's temporal contract):

* **SQL** — ``sig.effective_disposition`` plus the shared boolean fragments
  :func:`entity_eligible_sql` / :func:`claim_eligible_sql`, inlined into the API and
  export queries so a public consumer cannot forget to apply the selector.
* **Pure** — :func:`policy.eligibility.latest_disposition` over
  :class:`policy.eligibility.DispositionRecord`, kept identical by fixture/PG parity
  tests (``tests/db/test_publication_dispositions.py``).

Write path: :func:`record_disposition` — INSERT-only; the table's immutability
trigger and privilege set admit no UPDATE/DELETE route. The decision instant is
stamped by the database (``DEFAULT clock_timestamp()`` — P32.10a single clock
authority): the writer omits ``decided_at`` so the host clock can never
future-date a fresh row against the server clock the fragments evaluate; an
explicit value is accepted only as a documented replay/migration input.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from policy.eligibility import (
    Disposition,
    DispositionRecord,
    ReasonCategory,
    TargetKind,
    latest_disposition,
    new_disposition,
)

__all__ = [
    "DISPOSITION_TABLE",
    "TargetKind",
    "artifact_eligible_sql",
    "claim_eligible_sql",
    "dispositions_for",
    "effective_dispositions",
    "eligible_claim_ids",
    "eligible_entity_ids",
    "entity_eligible_sql",
    "latest_disposition",
    "new_disposition",
    "record_disposition",
]

DISPOSITION_TABLE = "publication_disposition"


#: The current-access-time effective disposition as a scalar SQL expression —
#: ``NULL`` when nothing is recorded. ``decided_at <= clock_timestamp()`` is the
#: rollback rule: public access always applies the LATEST recorded disposition,
#: never the disposition set that was current when an artifact was built.
def _latest_scalar(kind: str, id_expr: str) -> str:
    return (
        f"(SELECT d.disposition::text FROM {DISPOSITION_TABLE} d"
        f" WHERE d.target_kind = '{kind}' AND d.target_id = ({id_expr})::text"
        "   AND d.decided_at <= clock_timestamp()"
        " ORDER BY d.decided_at DESC, d.disposition_seq DESC LIMIT 1)"
    )


def entity_eligible_sql(id_expr: str) -> str:
    """SQL boolean — "this entity may be publicly represented (labelled/listed)".

    Mirrors :func:`policy.eligibility.organization_publication_decision`:
    a current deny disposition wins; a ``withdrawn``/``suppressed`` organisation
    status denies; ``publication_review_required`` withholds unless the latest
    disposition is a recorded ``allow``.
    """
    latest = _latest_scalar("entity", id_expr)
    return (
        f"(COALESCE({latest}, 'allow') NOT IN ('withhold','restrict','withdraw')"
        f" AND NOT EXISTS ("
        f"   SELECT 1 FROM organization o WHERE o.entity_id = {id_expr}"
        f"     AND (o.status IN ('withdrawn','suppressed')"
        f"          OR (o.publication_review_required"
        f"              AND COALESCE({latest}, '') <> 'allow'))))"
    )


def artifact_eligible_sql(id_expr: str) -> str:
    """SQL boolean — "this evidence artifact / capture / published object may
    be publicly represented" (current policy) — the inline twin of
    :func:`policy.eligibility.access_decision` (P32.5/ADR-124).

    Used by the P32.13 evidence-binding export so a ``withhold``/``withdraw``
    recorded on an artifact drops its public bindings the same way it drops
    the artifact route — one rule, three carriers (SQL fragment, pure
    selector, file registry), never a second definition.
    """
    latest = _latest_scalar("artifact", id_expr)
    return f"(COALESCE({latest}, 'allow') NOT IN ('withhold','restrict','withdraw'))"


def claim_eligible_sql(claim_alias: str = "c") -> str:
    """SQL boolean — "this claim may be publicly represented" (current policy).

    Mirrors :func:`policy.eligibility.claim_publication_decision`: no current
    denying claim-level disposition, the claim's subject entity is eligible
    (``claim.subject_id`` is ``uuid REFERENCES entity`` on this spine), and the
    claim's ``object_entity`` — the partner-organisation seam — is eligible too.
    """
    c = claim_alias
    return (
        f"(COALESCE({_latest_scalar('claim', f'{c}.claim_id')}, 'allow')"
        "   NOT IN ('withhold','restrict','withdraw')"
        f" AND {entity_eligible_sql(f'{c}.subject_id')}"
        f" AND ({c}.object_entity IS NULL OR {entity_eligible_sql(f'{c}.object_entity')}))"
    )


def _record_from_row(row: Any) -> DispositionRecord:
    """A row from the PRIVILEGED (full-column) select — decided_by + rationale."""
    (
        did,
        kind,
        tid,
        disp,
        reason,
        authority,
        decided_at,
        decided_by,
        rationale,
        ev,
        sup,
        pv,
        seq,
    ) = row
    return DispositionRecord(
        target_kind=TargetKind(str(kind)),
        target_id=str(tid),
        disposition=Disposition(str(disp)),
        reason_category=ReasonCategory(str(reason)),
        authority=str(authority),
        decided_at=decided_at,
        policy_version=str(pv),
        decided_by=None if decided_by is None else str(decided_by),
        rationale=rationale,
        evidence_claim_id=None if ev is None else str(ev),
        supersedes=None if sup is None else str(sup),
        seq=int(seq),
    )


def _record_from_safe_row(row: Any) -> DispositionRecord:
    """A row from the PUBLIC-SAFE column set — decided_by/rationale stay None
    (the migration grants exactly these columns to ``sig_read_public``)."""
    (did, kind, tid, disp, reason, authority, decided_at, ev, sup, pv, seq) = row
    return DispositionRecord(
        target_kind=TargetKind(str(kind)),
        target_id=str(tid),
        disposition=Disposition(str(disp)),
        reason_category=ReasonCategory(str(reason)),
        authority=str(authority),
        decided_at=decided_at,
        policy_version=str(pv),
        evidence_claim_id=None if ev is None else str(ev),
        supersedes=None if sup is None else str(sup),
        seq=int(seq),
    )


_SELECT_COLS = (
    "disposition_id, target_kind, target_id, disposition, reason_category, authority,"
    " decided_at, decided_by, rationale, evidence_claim_id, supersedes, policy_version,"
    " disposition_seq"
)

#: Exactly the columns the migration grants ``sig_read_public``/``sig_export`` —
#: access decisions never need ``decided_by``/``rationale`` (the tombstone states
#: reason_category + authority only, SIG-TRUST-006).
_SAFE_COLS = (
    "disposition_id, target_kind, target_id, disposition, reason_category, authority,"
    " decided_at, evidence_claim_id, supersedes, policy_version, disposition_seq"
)


def dispositions_for(
    cur: Any, target_kind: str | TargetKind, target_ids: list[str] | tuple[str, ...]
) -> list[DispositionRecord]:
    """Every recorded disposition for the targets (history, oldest→newest).

    Selects the FULL column set — ``decided_by``/``rationale`` are granted to the
    elevated review roles only, so this helper is for the authorized-review /
    internal path; public readers go through :func:`effective_dispositions`.
    """
    if not target_ids:
        return []
    kind = target_kind.value if isinstance(target_kind, TargetKind) else target_kind
    rows = cur.execute(
        f"SELECT {_SELECT_COLS} FROM {DISPOSITION_TABLE}"
        " WHERE target_kind = %s AND target_id = ANY(%s)"
        " ORDER BY decided_at, disposition_seq",
        (kind, list(target_ids)),
    ).fetchall()
    return [_record_from_row(r) for r in rows]


def effective_dispositions(
    cur: Any,
    target_kind: str | TargetKind,
    target_ids: list[str] | tuple[str, ...],
    at: datetime | None = None,
) -> dict[str, DispositionRecord]:
    """The latest disposition per target at ``at`` (``None`` = current access time)
    — the batch form of ``sig.effective_disposition`` / ``latest_disposition``.

    Reads the PUBLIC-SAFE column set only, so it works under ``sig_read_public``
    (an access decision needs disposition + reason_category + authority + the
    ordering columns — never the privileged rationale)."""
    if not target_ids:
        return {}
    kind = target_kind.value if isinstance(target_kind, TargetKind) else target_kind
    rows = cur.execute(
        f"SELECT {_SAFE_COLS} FROM {DISPOSITION_TABLE}"
        " WHERE target_kind = %s AND target_id = ANY(%s)"
        # Carrier parity (P32.10a): the SQL twin bounds
        # `decided_at <= COALESCE(p_at, clock_timestamp())`; the batch read does
        # the same so a future-dated replay row is recorded history
        # (dispositions_for shows it) but never the CURRENT effective
        # disposition on either carrier.
        " AND decided_at <= COALESCE(%s::timestamptz, clock_timestamp())"
        " ORDER BY decided_at, disposition_seq",
        (kind, list(target_ids), at),
    ).fetchall()
    by_target: dict[str, list[DispositionRecord]] = {}
    for r in rows:
        rec = _record_from_safe_row(r)
        by_target.setdefault(rec.target_id, []).append(rec)
    out: dict[str, DispositionRecord] = {}
    for tid in target_ids:
        eff = latest_disposition(by_target.get(str(tid), []), at)
        if eff is not None:
            out[str(tid)] = eff
    return out


def _uuid_only(ids: list[str] | tuple[str, ...]) -> list[str]:
    """Entity/claim targets are uuids on this spine; non-uuid references (a
    raw subject string in a hand-written row) are not entity-gated."""
    out: list[str] = []
    for i in ids:
        s = str(i).strip().lower()
        if len(s) == 36 and s.count("-") == 4:
            out.append(s)
    return out


def eligible_entity_ids(cur: Any, entity_ids: list[str] | tuple[str, ...]) -> set[str]:
    """The subset of entity ids publicly eligible under the CURRENT policy — the
    same :func:`entity_eligible_sql` fragment the query paths inline."""
    ids = _uuid_only(entity_ids)
    if not ids:
        return set()
    rows = cur.execute(
        f"SELECT e.entity_id::text FROM entity e"
        f" WHERE e.entity_id = ANY(%s::uuid[]) AND {entity_eligible_sql('e.entity_id')}",
        (ids,),
    ).fetchall()
    return {str(r[0]) for r in rows}


def eligible_claim_ids(cur: Any, claim_ids: list[str] | tuple[str, ...]) -> set[str]:
    """The subset of claim ids publicly eligible under the CURRENT policy — the
    same :func:`claim_eligible_sql` fragment the claim queries inline."""
    ids = _uuid_only(claim_ids)
    if not ids:
        return set()
    rows = cur.execute(
        f"SELECT c.claim_id::text FROM claim c"
        f" WHERE c.claim_id = ANY(%s::uuid[]) AND {claim_eligible_sql('c')}",
        (ids,),
    ).fetchall()
    return {str(r[0]) for r in rows}


def record_disposition(conn: Any, record: DispositionRecord) -> str:
    """Append ONE disposition row (INSERT-only — the immutable-registry write path).

    ``record`` must come from :func:`policy.eligibility.new_disposition` (validated
    by the same rule the SQL CHECK enforces). Returns the new ``disposition_id``.
    A re-issued disposition is a NEW row (``supersedes`` links the old id); no
    UPDATE/DELETE path exists — enforced by trigger AND by privilege.

    Single clock authority (P32.10a): when ``record.decided_at is None`` the
    ``decided_at`` column is omitted from the INSERT so the database stamps it
    (``DEFAULT clock_timestamp()``) — the writer's host clock can never
    future-date a fresh row against the server clock the eligibility fragments
    evaluate. An explicit ``decided_at`` is written only as a documented
    replay/migration input that re-records already-decided history.
    """
    base_cols = (
        "disposition_id, target_kind, target_id, disposition, reason_category,"
        " authority, decided_by, rationale, evidence_claim_id, supersedes,"
        " policy_version"
    )
    base_vals = (
        record.target_kind.value,
        record.target_id,
        record.disposition.value,
        record.reason_category.value,
        record.authority,
        record.decided_by,
        record.rationale,
        record.evidence_claim_id,
        record.supersedes,
        record.policy_version,
    )
    cols = base_cols
    vals: tuple[Any, ...] = base_vals
    if record.decided_at is not None:
        # Replay/migration only: an explicit recorded-history instant. Normal
        # writes omit the column so DEFAULT clock_timestamp() stamps it.
        cols = f"{base_cols}, decided_at"
        vals = (*base_vals, record.decided_at)
    row = conn.execute(
        f"INSERT INTO {DISPOSITION_TABLE} ({cols}) "
        f"VALUES (gen_random_uuid(), {', '.join(['%s'] * len(vals))}) "
        "RETURNING disposition_id::text",
        vals,
    ).fetchone()
    assert row is not None
    return str(row[0])
