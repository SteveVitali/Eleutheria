# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The durable intake stores over PostgreSQL (P32.16 / ADR-135, SIG-FIND-006).

Two role-scoped wrappers over the `intake` sqitch change — the same
least-privilege shape the rest of the spine uses (``SET ROLE`` on connect):

* :class:`PgIntakeReceiverStore` (``SET ROLE sig_intake_receiver``) — the public
  receiver's only data path. It can INSERT report/receipt/contact/event rows
  (the writer-guard trigger restricts it to the ``received`` event), read the
  coarse ``intake.report_public`` projection for dedupe and status, and compare
  one receipt's token digest. It holds **no** claim-spine, review-decision or
  disposition privilege — the schema grants make a stolen receiver credential
  unable to write canonical state by construction.
* :class:`PgIntakeReviewerStore` (``SET ROLE sig_intake_reviewer``) — the
  loopback curation surface's queue/detail/event path: SELECT the quarantined
  payloads + audit log, append reviewer events, and run the two SECURITY
  DEFINER maintenance functions (redact / expunge). It cannot update or delete
  intake rows directly and holds no canonical write either.

Every write runs in a real transaction; ``insert_report`` is the
submit-side commit — the 201/history-keeping contract is "success only after
durable commit" (S4 §8).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any, Protocol, overload

import psycopg
from psycopg import sql
from psycopg.rows import dict_row

__all__ = [
    "RECEIVER_ROLE",
    "REVIEWER_ROLE",
    "RECEIVER_ACTOR",
    "PgIntakeReceiverStore",
    "PgIntakeReviewerStore",
    "IntakeReceiverStore",
    "IntakeReviewerStore",
]

RECEIVER_ROLE = "sig_intake_receiver"
REVIEWER_ROLE = "sig_intake_reviewer"
#: The fixed actor value the writer-guard requires on a ``received`` event.
RECEIVER_ACTOR = "sig-intake-receiver"

_LIFECYCLE_EVENTS = (
    "received",
    "triaged",
    "assigned",
    "review_requested",
    "disposition_proposed",
    "disposition_approved",
    "applied",
    "published",
    "closed",
)


class IntakeReceiverStore(Protocol):
    """The public receiver's data contract (PG + the in-memory test double)."""

    def insert_report(
        self,
        *,
        report_id: str,
        receipt_id: str,
        idempotency_key: str,
        category: str,
        description: str,
        publication_id: str | None,
        record_key: str | None,
        claim_ids: list[str],
        evidence_urls: list[str],
        contact: str | None,
        token_digest: bytes,
    ) -> None:
        """Persist one accepted report + receipt + received event (one transaction)."""
        ...

    def find_by_idempotency(self, idempotency_key: str) -> dict[str, Any] | None:
        """The prior receipt for a dedupe key, else ``None`` (projection only)."""
        ...

    def public_status(self, receipt_id: str) -> dict[str, Any] | None:
        """The coarse public projection row for a receipt id, else ``None``."""
        ...

    def receipt_token_digest(self, report_id: str) -> bytes | None:
        """The stored status-token digest for constant-time comparison."""
        ...

    def close(self) -> None: ...


class IntakeReviewerStore(Protocol):
    """The private reviewer's data contract over the same schema."""

    def queue(self, *, limit: int = 200, include_closed: bool = False) -> list[dict[str, Any]]: ...
    def detail(self, receipt_id: str) -> dict[str, Any] | None: ...
    def record_event(
        self, receipt_id: str, event: str, actor: str, detail: dict[str, Any]
    ) -> int: ...
    def redact(self, receipt_id: str, fields: list[str], actor: str) -> None: ...
    def expunge(self, receipt_id: str) -> None: ...
    def expunge_due(
        self,
        *,
        after_disposition_days: int,
        ceiling_days: int,
        now: datetime,
        dry_run: bool = False,
    ) -> dict[str, Any]: ...
    def close(self) -> None: ...


def _dsn_connect(dsn: str, role: str) -> psycopg.Connection[dict[str, Any]]:
    conn = psycopg.connect(dsn, autocommit=True, row_factory=dict_row)
    conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))
    return conn


@overload
def _row(row: None) -> None: ...
@overload
def _row(row: dict[str, Any]) -> dict[str, Any]: ...
def _row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Serialise one psycopg dict row to JSON-safe values.

    ``uuid.UUID`` values become strings and datetimes ISO-8601 — psycopg
    returns both natively, and a route that passed them through verbatim
    500s on JSON serialisation (C4 NEW-8). List values (``claim_ids``,
    ``evidence_urls``) get the same treatment element-wise.
    """
    if row is None:
        return None
    out = dict(row)
    for key, value in out.items():
        if isinstance(value, uuid.UUID):
            out[key] = str(value)
        elif isinstance(value, datetime):
            out[key] = value.isoformat()
        elif isinstance(value, list):
            out[key] = [str(v) if isinstance(v, uuid.UUID) else v for v in value]
    return out


class PgIntakeReceiverStore:
    """The public receiver's least-privilege store (``SET ROLE sig_intake_receiver``)."""

    def __init__(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        self._conn = conn

    @classmethod
    def from_dsn(cls, dsn: str) -> PgIntakeReceiverStore:
        return cls(_dsn_connect(dsn, RECEIVER_ROLE))

    # -- writes -------------------------------------------------------------- #
    def insert_report(
        self,
        *,
        report_id: str,
        receipt_id: str,
        idempotency_key: str,
        category: str,
        description: str,
        publication_id: str | None,
        record_key: str | None,
        claim_ids: list[str],
        evidence_urls: list[str],
        contact: str | None,
        token_digest: bytes,
    ) -> None:
        """One durable transaction: report + receipt + (contact) + received event."""
        with self._conn.transaction():
            self._conn.execute(
                "INSERT INTO intake.report "
                "(report_id, receipt_id, idempotency_key, category, publication_id,"
                " record_key, claim_ids, description, evidence_urls)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb)",
                (
                    report_id,
                    receipt_id,
                    idempotency_key,
                    category,
                    publication_id,
                    record_key,
                    json.dumps(claim_ids),
                    description,
                    json.dumps(evidence_urls),
                ),
            )
            self._conn.execute(
                "INSERT INTO intake.receipt (report_id, token_digest) VALUES (%s,%s)",
                (report_id, token_digest),
            )
            if contact is not None:
                self._conn.execute(
                    "INSERT INTO intake.reporter_contact (report_id, contact) VALUES (%s,%s)",
                    (report_id, contact),
                )
            self._conn.execute(
                "INSERT INTO intake.event (report_id, event, actor, detail)"
                " VALUES (%s,'received',%s,'{}'::jsonb)",
                (report_id, RECEIVER_ACTOR),
            )

    # -- reads --------------------------------------------------------------- #
    def find_by_idempotency(self, idempotency_key: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT receipt_id, category, received_at, state, public_response"
            " FROM intake.report_public WHERE idempotency_key = %s",
            (idempotency_key,),
        ).fetchone()
        return _row(row)

    def public_status(self, receipt_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT report_id, receipt_id, category, received_at,"
            " lifecycle_event, state, public_response, outcome,"
            " correction_ref, publication_id, tombstone"
            " FROM intake.report_public WHERE receipt_id = %s",
            (receipt_id,),
        ).fetchone()
        return _row(row)

    def receipt_token_digest(self, report_id: str) -> bytes | None:
        row = self._conn.execute(
            "SELECT token_digest FROM intake.receipt WHERE report_id = %s",
            (report_id,),
        ).fetchone()
        if row is None:
            return None
        return bytes(row["token_digest"])

    def close(self) -> None:
        self._conn.close()


class PgIntakeReviewerStore:
    """The private reviewer's store (``SET ROLE sig_intake_reviewer``)."""

    def __init__(self, conn: psycopg.Connection[dict[str, Any]]) -> None:
        self._conn = conn

    @classmethod
    def from_dsn(cls, dsn: str) -> PgIntakeReviewerStore:
        return cls(_dsn_connect(dsn, REVIEWER_ROLE))

    def _report_id_for(self, receipt_id: str) -> str | None:
        row = self._conn.execute(
            "SELECT report_id FROM intake.report WHERE receipt_id = %s", (receipt_id,)
        ).fetchone()
        return None if row is None else str(row["report_id"])

    def queue(self, *, limit: int = 200, include_closed: bool = False) -> list[dict[str, Any]]:
        """The pending queue: undecided reports oldest-first + the latest event.

        ``include_closed=True`` returns the bounded most-recent history instead —
        the dashboard needs both views; the queue is never unbounded. "Pending"
        is computed in SQL: no lifecycle event has reached a terminal decision.
        """
        terminal = ("disposition_approved", "applied", "published", "closed")
        if include_closed:
            rows = self._conn.execute(
                "SELECT r.receipt_id, r.category, r.received_at,"
                " COALESCE(le.event,'received') AS lifecycle_event"
                " FROM intake.report r"
                " LEFT JOIN LATERAL ("
                "   SELECT e.event FROM intake.event e"
                "   WHERE e.report_id = r.report_id AND e.event = ANY(%s)"
                "   ORDER BY e.event_seq DESC LIMIT 1"
                " ) le ON true"
                " ORDER BY r.received_at DESC LIMIT %s",
                (list(_LIFECYCLE_EVENTS), int(limit)),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT r.receipt_id, r.category, r.received_at,"
                " COALESCE(le.event,'received') AS lifecycle_event"
                " FROM intake.report r"
                " LEFT JOIN LATERAL ("
                "   SELECT e.event FROM intake.event e"
                "   WHERE e.report_id = r.report_id AND e.event = ANY(%s)"
                "   ORDER BY e.event_seq DESC LIMIT 1"
                " ) le ON true"
                " WHERE COALESCE(le.event,'received') <> ALL(%s)"
                " ORDER BY r.received_at ASC LIMIT %s",
                (list(_LIFECYCLE_EVENTS), list(terminal), int(limit)),
            ).fetchall()
        return [_row(dict(r)) for r in rows]

    def detail(self, receipt_id: str) -> dict[str, Any] | None:
        """Full restricted view: payload + contact + the append-only event log."""
        report = self._conn.execute(
            "SELECT report_id, receipt_id, idempotency_key, category, publication_id,"
            " record_key, claim_ids, description, evidence_urls, received_at, expunged_at"
            " FROM intake.report WHERE receipt_id = %s",
            (receipt_id,),
        ).fetchone()
        if report is None:
            return None
        report = _row(report)
        contact = self._conn.execute(
            "SELECT contact FROM intake.reporter_contact WHERE report_id = %s",
            (report["report_id"],),
        ).fetchone()
        events = self._conn.execute(
            "SELECT event_seq, event, actor, at, detail FROM intake.event"
            " WHERE report_id = %s ORDER BY event_seq",
            (report["report_id"],),
        ).fetchall()
        report["contact"] = None if contact is None else contact["contact"]
        report["events"] = [_row(dict(e)) for e in events]
        report["lifecycle_event"] = next(
            (e["event"] for e in reversed(report["events"]) if e["event"] in _LIFECYCLE_EVENTS),
            "received",
        )
        return report

    def record_event(self, receipt_id: str, event: str, actor: str, detail: dict[str, Any]) -> int:
        """Append one reviewer event; returns the event_seq. The writer guard +
        transition table (checked app-side) keep this fail-closed."""
        report_id = self._report_id_for(receipt_id)
        if report_id is None:
            raise KeyError(f"unknown receipt {receipt_id!r}")
        row = self._conn.execute(
            "INSERT INTO intake.event (report_id, event, actor, detail)"
            " VALUES (%s,%s,%s,%s::jsonb) RETURNING event_seq",
            (report_id, event, actor, json.dumps(detail)),
        ).fetchone()
        if row is None:  # pragma: no cover - RETURNING always yields a row
            raise RuntimeError("event insert returned no row")
        return int(row["event_seq"])

    def redact(self, receipt_id: str, fields: list[str], actor: str) -> None:
        """Irreversible moderator redaction via the SECURITY DEFINER function."""
        report_id = self._report_id_for(receipt_id)
        if report_id is None:
            raise KeyError(f"unknown receipt {receipt_id!r}")
        self._conn.execute(
            "SELECT intake.redact_report(%s::uuid, %s::text[], %s)",
            (report_id, fields, actor),
        )

    def expunge(self, receipt_id: str) -> None:
        """Retention expunge of one report via the SECURITY DEFINER function."""
        report_id = self._report_id_for(receipt_id)
        if report_id is None:
            raise KeyError(f"unknown receipt {receipt_id!r}")
        self._conn.execute("SELECT intake.expunge_report(%s::uuid)", (report_id,))

    def expunge_due(
        self,
        *,
        after_disposition_days: int,
        ceiling_days: int,
        now: datetime,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """The retention sweep (S4 §8): expunge payloads whose final
        disposition/closure is older than ``after_disposition_days``, and
        report (never silently expunge) undecided reports older than the
        ``ceiling_days`` review/reminder ceiling. Reports carrying a
        ``legal_hold`` event are skipped and listed — extension is an
        authorized reviewer act, recorded on the event log. ``dry_run``
        reports the same decision set without writing."""
        rows = self._conn.execute(
            "SELECT r.report_id, r.receipt_id, r.received_at, r.expunged_at,"
            " COALESCE(le.event,'received') AS lifecycle_event, le.at AS lifecycle_at,"
            " EXISTS (SELECT 1 FROM intake.event h WHERE h.report_id = r.report_id"
            "         AND COALESCE((h.detail->>'legal_hold')::boolean,false)) AS held"
            " FROM intake.report r"
            " LEFT JOIN LATERAL ("
            "   SELECT e.event, e.at FROM intake.event e"
            "   WHERE e.report_id = r.report_id AND e.event = ANY(%s)"
            "   ORDER BY e.event_seq DESC LIMIT 1"
            " ) le ON true",
            (list(_LIFECYCLE_EVENTS),),
        ).fetchall()
        from datetime import timedelta

        expunge_cut = now - timedelta(days=after_disposition_days)
        ceiling_cut = now - timedelta(days=ceiling_days)
        expunged: list[str] = []
        review_overdue: list[str] = []
        held: list[str] = []
        for r in rows:
            rid = str(r["report_id"])
            if r["expunged_at"] is not None:
                continue
            decided = r["lifecycle_event"] in {
                "disposition_approved",
                "applied",
                "published",
                "closed",
            }
            due = decided and r["lifecycle_at"] is not None and r["lifecycle_at"] < expunge_cut
            overdue = not decided and r["received_at"] < ceiling_cut
            if r["held"]:
                held.append(r["receipt_id"])
                continue
            if due:
                if not dry_run:
                    self._conn.execute("SELECT intake.expunge_report(%s::uuid)", (rid,))
                expunged.append(r["receipt_id"])
            elif overdue:
                review_overdue.append(r["receipt_id"])
        return {
            "expunged": expunged,
            "review_overdue": review_overdue,
            "legal_hold_skipped": held,
        }

    def close(self) -> None:
        self._conn.close()
