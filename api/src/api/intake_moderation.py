# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The private intake-moderation routes on the loopback curation app (P32.16 /
ADR-135, §55.5 SIG-FIND-006).

The reviewer half of the anonymous correction receiver: mounted on
``create_curation_app`` ONLY when an intake reviewer store is supplied — the
loopback-authenticated curation process is the required delivery target (S4
§8: "a dashboard queue is the required delivery target"), and these routes are
structurally absent everywhere else.

* ``GET /v1/curation/intake`` — the durable pending queue (policy priority
  then oldest-first), bounded; survives restarts by construction (the queue is
  a query over `intake.report` + `intake.event`).
* ``GET /v1/curation/intake/{receipt_id}`` — the restricted payload detail +
  append-only event log (the only surface that may show raw narrative/contact).
* ``POST /v1/curation/intake/{receipt_id}/events`` — append a reviewer event.
  Transitions are fail-closed over the data-table state machine
  (:func:`policy.intake.legal_transition`); dispositions need outcome + reason
  (SIG-GOV-004); ``disposition_approved`` additionally requires the curator
  scope (proposal vs. approval separation); ``redacted`` runs the irreversible
  field-level redaction; ``applied``/``published`` are unreachable — the
  DB writer guard refuses them for every current role (P32.16a owns them).

Nothing here writes a claim, a review_decision, or a publication disposition:
a *reviewed* report is not an *applied* correction (SIG-FIND-008 is P32.16a).
"""

from __future__ import annotations

from typing import Any

from db.intake import IntakeReviewerStore
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from policy.governance import intake_categories
from tasks.contributor import Contributor, WriteScope

from policy import intake as pint

from .curation import _require_scope, authenticated_contributor

__all__ = ["build_intake_moderation_router"]


def _category_meta() -> dict[str, dict[str, Any]]:
    return {str(c["id"]): c for c in intake_categories()}


def build_intake_moderation_router(store: IntakeReviewerStore) -> APIRouter:
    """Assemble ``/v1/curation/intake/*`` over the reviewer store (fail closed)."""
    router = APIRouter(prefix="/v1/curation/intake")

    @router.get("")
    def intake_queue(
        all: bool = False,
        limit: int = 200,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> JSONResponse:
        """The pending moderation queue — priority order, bounded, durable."""
        _require_scope(contributor, WriteScope.VERIFY_SUBMISSIONS)
        if limit < 1 or limit > 500:
            raise HTTPException(status_code=400, detail="limit must be 1–500")
        meta = _category_meta()
        rows = store.queue(limit=limit, include_closed=all)
        for row in rows:
            cat = meta.get(row["category"], {})
            row["priority"] = cat.get("priority")
            row["sla_hours"] = cat.get("sla_hours")
            row["state"] = pint.public_state(row["lifecycle_event"])
        # Priority first (privacy_harm/security_concern = 1), then oldest.
        rows.sort(key=lambda r: (r["priority"] or 99, r["received_at"]))
        return JSONResponse(
            {"pending": rows, "count": len(rows), "include_closed": all, "limit": limit}
        )

    @router.get("/{receipt_id}")
    def intake_detail(
        receipt_id: str,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> JSONResponse:
        """The restricted payload + full audit log — reviewer eyes only."""
        _require_scope(contributor, WriteScope.VERIFY_SUBMISSIONS)
        row = store.detail(receipt_id)
        if row is None:
            raise HTTPException(status_code=404, detail="unknown receipt")
        meta = _category_meta()
        row["priority"] = meta.get(row["category"], {}).get("priority")
        row["sla_hours"] = meta.get(row["category"], {}).get("sla_hours")
        row["state"] = pint.public_state(row["lifecycle_event"])
        return JSONResponse(row)

    @router.post("/{receipt_id}/events")
    async def append_event(
        request: Request,
        receipt_id: str,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> JSONResponse:
        """Append one reviewer event — transitions and detail are fail-closed."""
        try:
            body = await request.json()
        except Exception:
            raise HTTPException(status_code=422, detail="a JSON body is required") from None
        if not isinstance(body, dict):
            raise HTTPException(status_code=422, detail="a JSON object is required")
        event = str(body.get("event") or "")
        detail = body.get("detail") or {}
        if not isinstance(detail, dict):
            raise HTTPException(status_code=422, detail="detail must be an object")

        if event not in pint.moderation_events():
            raise HTTPException(
                status_code=422,
                detail=(
                    f"event must be one of {sorted(pint.moderation_events())}; "
                    "received belongs to the receiver, applied/published are "
                    "reserved for the P32.16a bridge, expunged to retention"
                ),
            )
        # Two-key approval: ANY reviewer may triage/propose/redact; approving a
        # disposition takes the curator scope (HUMAN_ASSERTION) — the same
        # split the §34.1 tier ladder gives decide-vs-verify.
        if event == "disposition_approved":
            _require_scope(contributor, WriteScope.HUMAN_ASSERTION)
        else:
            _require_scope(contributor, WriteScope.VERIFY_SUBMISSIONS)

        row = store.detail(receipt_id)
        if row is None:
            raise HTTPException(status_code=404, detail="unknown receipt")
        current = row["lifecycle_event"]
        if not pint.legal_transition(current, event):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{event!r} does not follow {current!r} — the intake "
                    "transition table is fail-closed"
                ),
            )
        # disposition_approved must name the proposal it approves and the
        # proposal must be the current event — approval is never of thin air.
        if event == "disposition_approved":
            if current != "disposition_proposed":
                raise HTTPException(
                    status_code=409,
                    detail="a disposition_approved must follow a live proposal",
                )
            proposed_seq = next(
                e["event_seq"]
                for e in reversed(row["events"])
                if e["event"] == "disposition_proposed"
            )
            if detail.get("approves_seq") not in (None, proposed_seq):
                raise HTTPException(
                    status_code=409,
                    detail="approves_seq must name the current disposition_proposed",
                )
            detail.setdefault("approves_seq", proposed_seq)
        try:
            clean = pint.validate_moderation_detail(event, detail)
        except pint.IntakeFieldError as exc:
            raise HTTPException(status_code=422, detail={"fields": exc.fields}) from exc

        actor = contributor.handle
        try:
            if event == "redacted":
                store.redact(receipt_id, list(clean["fields"]), actor)
                fresh = store.detail(receipt_id)
                seq = fresh["events"][-1]["event_seq"] if fresh else None
            else:
                seq = store.record_event(receipt_id, event, actor, clean)
        except KeyError:
            raise HTTPException(status_code=404, detail="unknown receipt") from None
        return JSONResponse(
            {"receipt_id": receipt_id, "event": event, "event_seq": seq, "actor": actor},
            status_code=201,
        )

    return router
