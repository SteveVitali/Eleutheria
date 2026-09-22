# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The authenticated curation service (§34, §28.5, §30, §33.4, §36; ADR-068).

This is the write-side counterpart to the public read API (`api.app`): the surface
reviewers use to work the ER review queue and contradiction/task dispositions, and
the surface an L0 contributor submits through. It is deliberately a **separate
FastAPI app** from the public read API and is mounted **only when
``SIG_CURATION_ENABLED=1``** — the public API process never carries these routes
(Part VIII §0.7: the curation service is authenticated and is not public). In the
runtime composition it runs as the second ``api-curation`` host process /
``docker-compose`` service bound to a non-public interface.

Four load-bearing invariants, each pinned by ``tests/api/test_curation.py``:

* **Disabled by default (RISK-P21-10).** :func:`create_curation_app` builds an app
  with **no** ``/v1/curation/*`` routes unless curation is enabled, so a stray
  deployment of the public process can never expose the write surface — the routes
  are simply absent (404), not merely guarded.
* **Authenticated + tier-gated (§36.1, SIG-CONTRIB-001).** Every route requires a
  bearer token that maps to a P16.1 pseudonymous :class:`~tasks.contributor.Contributor`
  (no token → 401); each route asserts the contributor tier holds the write scope it
  needs (insufficient → 403). No per-person data beyond the pseudonymous handle is
  read or stored (Part VIII §0.7).
* **Append-only, human-attributed writes (P1–P3, defining standard §3.1).** Every
  write is exactly one new row appended to the :class:`CurationLog` (never a
  mutation), carrying the **human actor id** (the contributor handle) and a
  timestamp. Repeating a decision appends another row — a decision *history*, never
  an edit. The queue's *pending* set is computed on read (proposals minus those with
  a decision row), the same semantics as P19.5's ``PgReviewQueue`` ``LEFT JOIN
  review_decision`` — P21.2 shipped compute-on-read, so this is the JSONL queue path,
  not a new persistence repo.
* **Machine suggestions never auto-apply (§34 SIG-LLM-001..007, §3.1).** A proposal
  MAY carry a model-suggested decision with its confidence class and provenance; it
  is surfaced as a *labelled suggestion* only. There is no code path that writes a
  decision without an explicit human decision + actor id — :meth:`CurationLog.append`
  refuses an empty actor.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request
from resolution.review_queue import ReviewItem, ReviewQueue
from starlette.responses import JSONResponse, RedirectResponse, Response
from starlette.routing import Route
from tasks.contributor import Contributor, ContributorTier, WriteScope, may_write
from tasks.onboarding import OnboardingTimingAggregate
from tasks.poisoning import (
    AnomalyDetector,
    ClaimSource,
    ContributionSignal,
    visual_weight,
)
from tasks.submission import (
    OSM_ROUTED_KINDS,
    SubmissionKind,
    is_sig_capturable,
    route_device_observation,
    submit,
)
from tasks.vocabulary import Disposition

from . import __version__
from .prohibitions import assert_no_prohibited_routes, route_paths

__all__ = [
    "CURATION_ENABLED_ENV",
    "CurationLog",
    "CurationRecord",
    "curation_enabled",
    "create_curation_app",
    "build_curation_router",
    "authenticated_contributor",
    "CURATION_KEYS",
]

#: The env var that mounts the curation surface. Unset / anything but ``"1"`` keeps
#: every ``/v1/curation/*`` route absent (RISK-P21-10, disabled-by-default).
CURATION_ENABLED_ENV = "SIG_CURATION_ENABLED"


def curation_enabled(env: Mapping[str, str] | None = None) -> bool:
    """Whether the curation surface is enabled (``SIG_CURATION_ENABLED=1``)."""
    import os

    source = os.environ if env is None else env
    return source.get(CURATION_ENABLED_ENV) == "1"


# --------------------------------------------------------------------------- #
# Authentication: bearer token -> a P16.1 pseudonymous contributor (SIG-CONTRIB-006)
# --------------------------------------------------------------------------- #
#: A tiny demo token registry mapping bearer tokens to pseudonymous contributors.
#: Production wires this to the real tier-token store (P16.1); the mapping shape —
#: token -> (pseudonymous handle, tier) — is what the service depends on. No
#: real-name field exists anywhere (SIG-CONTRIB-006, Part VIII §0.7).
CURATION_KEYS: dict[str, Contributor] = {
    "anon-demo-key": Contributor(handle="anon-1", tier=ContributorTier.ANONYMOUS),
    "registered-demo-key": Contributor(handle="registered-1", tier=ContributorTier.REGISTERED),
    "reviewer-demo-key": Contributor(handle="reviewer-1", tier=ContributorTier.TRUSTED_REVIEWER),
    "curator-demo-key": Contributor(handle="curator-1", tier=ContributorTier.CURATOR),
    "maintainer-demo-key": Contributor(handle="maintainer-1", tier=ContributorTier.MAINTAINER),
}


def authenticated_contributor(
    authorization: str | None = Header(default=None),
) -> Contributor:
    """Resolve the bearer token to a contributor; 401 if missing/unknown (§36.1).

    The curation surface is authenticated — unlike the public read API there is no
    anonymous fall-through. A missing, malformed, or unknown token is refused with
    401 so no route runs without an attributable human actor.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="curation requires a bearer token (§36.1)")
    token = authorization[7:].strip()
    contributor = CURATION_KEYS.get(token)
    if contributor is None:
        raise HTTPException(status_code=401, detail="unknown curation token (§36.1)")
    return contributor


def _require_scope(contributor: Contributor, scope: WriteScope) -> None:
    """Assert ``contributor``'s tier holds ``scope`` (§34.1); 403 otherwise."""
    if not may_write(contributor.tier, scope):
        raise HTTPException(
            status_code=403,
            detail=(
                f"tier {contributor.tier.value!r} may not {scope.value} "
                "(insufficient contributor tier, §34.1)"
            ),
        )


# --------------------------------------------------------------------------- #
# The append-only curation log (P1-P3, §3.1) — the JSONL queue path            #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class CurationRecord:
    """One append-only curation action — a decision, disposition, submission, revert.

    Every field the audit trail needs is here: the ``action`` kind, the ``target_id``
    it acts on, the **human actor id** (a pseudonymous contributor handle, never a
    legal name — SIG-CONTRIB-006), the UTC ``at`` timestamp, and an action-specific
    ``payload``. It is immutable; a correction is a *new* record, never an edit.
    """

    action: str
    target_id: str
    actor: str
    at: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def to_row(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "target_id": self.target_id,
            "actor": self.actor,
            "at": self.at,
            "payload": dict(self.payload),
        }


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


class CurationLog:
    """An append-only log of curation actions (P1-P3, the audit trail per action).

    Every write appends exactly one :class:`CurationRecord`; nothing is ever mutated
    or removed. Deciding the same item twice appends a second row (a history), which
    is how a reversal stays an attributable new assertion rather than an edit. This
    is the JSONL queue path P21.2 (shrunk) left in place: an in-memory list that
    serialises to JSONL, not a new persistence repo.
    """

    def __init__(self) -> None:
        self._records: list[CurationRecord] = []

    def append(
        self,
        action: str,
        target_id: str,
        *,
        actor: str,
        payload: Mapping[str, Any] | None = None,
    ) -> CurationRecord:
        """Append one action row. Refuses an empty human actor id (§3.1, SIG-LLM-002).

        The empty-actor refusal is the structural guarantee that no write path — not
        a machine suggestion, not a default — can create a curation row without a
        human being attributable for it.
        """
        if not actor:
            raise ValueError(
                "a curation write MUST carry a human actor id — no decision is "
                "writable without one (§3.1, SIG-LLM-002)"
            )
        record = CurationRecord(
            action=action,
            target_id=target_id,
            actor=actor,
            at=_now_iso(),
            payload=dict(payload or {}),
        )
        self._records.append(record)
        return record

    def records(
        self, *, action: str | None = None, target_id: str | None = None
    ) -> tuple[CurationRecord, ...]:
        """Every appended record, optionally filtered by action/target (append order)."""
        return tuple(
            r
            for r in self._records
            if (action is None or r.action == action)
            and (target_id is None or r.target_id == target_id)
        )

    def decided_item_ids(self) -> frozenset[str]:
        """The review-queue item ids that carry at least one decision (compute-on-read)."""
        return frozenset(r.target_id for r in self._records if r.action == "review_decision")

    def latest_disposition(self, kind: str, target_id: str) -> CurationRecord | None:
        """The most recent disposition row for ``target_id`` (compute-on-read, §30/§33.4)."""
        matches = [r for r in self._records if r.action == kind and r.target_id == target_id]
        return matches[-1] if matches else None

    def to_rows(self) -> list[dict[str, Any]]:
        return [r.to_row() for r in self._records]


# --------------------------------------------------------------------------- #
# The router                                                                   #
# --------------------------------------------------------------------------- #
_DECIDE_TO_REVIEW = {"match": "accept", "no-match": "reject", "no_match": "reject"}
_ER_DECISIONS = frozenset({"match", "no-match", "no_match", "defer"})


async def _read_params(request: Request) -> dict[str, str]:
    """Parse the request body as JSON or urlencoded form (no-JS forms send the latter).

    HTML ``<form method="post">`` sends ``application/x-www-form-urlencoded``; API
    clients may send JSON. Both are supported without a multipart dependency, so the
    curation forms work with **no client JavaScript** (progressive enhancement).
    """
    ctype = request.headers.get("content-type", "")
    if "application/json" in ctype:
        data = await request.json()
        if not isinstance(data, dict):
            raise HTTPException(status_code=400, detail="expected a JSON object")
        return {str(k): "" if v is None else str(v) for k, v in data.items()}
    from urllib.parse import parse_qs

    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {k: v[-1] for k, v in parsed.items()}


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "")


def _ok(request: Request, body: dict[str, Any], *, redirect: str | None) -> Response:
    """Return a JSON body, or a 303 redirect for a no-JS HTML form submission."""
    if redirect and _wants_html(request):
        return RedirectResponse(url=redirect, status_code=303)
    return JSONResponse(body)


def _item_to_row(item: ReviewItem, decided: bool) -> dict[str, Any]:
    """A review-queue item as JSON, with any machine suggestion clearly labelled."""
    row: dict[str, Any] = {
        "item_id": item.item_id,
        "kind": item.kind,
        "summary": item.summary,
        "overall_weight": item.overall_weight,
        "confidence": [f.to_row() for f in item.confidence],
        "decided": decided,
    }
    # A model-assisted item's suggestion is surfaced as a LABELLED suggestion with
    # its provenance — never a pre-applied decision (SIG-LLM-001/002).
    if item.model_assisted:
        suggested = item.payload.get("suggested_decision")
        row["suggestion"] = {
            "suggested_decision": suggested,
            "confidence_class": item.payload.get("confidence_class"),
            "model_id": item.model_id,
            "prompt_version": item.prompt_version,
            "auto_applied": False,
            "note": "machine suggestion — a human must decide (SIG-LLM-001/002)",
        }
    return row


def build_curation_router() -> APIRouter:
    """Assemble the authenticated ``/v1/curation`` router (§34, ADR-068)."""
    router = APIRouter(prefix="/v1/curation")

    def _queue(request: Request) -> ReviewQueue:
        return request.app.state.review_queue

    def _log(request: Request) -> CurationLog:
        return request.app.state.curation_log

    # --- review queue: list (filter by tier) ---------------------------------
    @router.get("/review-queue")
    def review_queue_list(
        request: Request,
        tier: str | None = None,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> Response:
        _require_scope(contributor, WriteScope.VERIFY_SUBMISSIONS)
        queue = _queue(request)
        log = _log(request)
        decided = log.decided_item_ids()
        # RISK-P21-11 (reviewer fatigue): order by |overall_weight| descending so the
        # highest-impact / most-decisive proposals surface first, then by id.
        items = sorted(
            queue.pending(),
            key=lambda it: (
                -(abs(it.overall_weight) if it.overall_weight is not None else 0.0),
                it.item_id,
            ),
        )
        rows = [
            _item_to_row(it, it.item_id in decided) for it in items if it.item_id not in decided
        ]
        if tier:
            wanted = f"tier {tier}"
            rows = [r for r in rows if wanted in str(r["summary"]).lower()]
        return JSONResponse({"pending": rows, "count": len(rows)})

    @router.get("/review-queue/{item_id}")
    def review_queue_item(
        request: Request,
        item_id: str,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> Response:
        _require_scope(contributor, WriteScope.VERIFY_SUBMISSIONS)
        queue = _queue(request)
        log = _log(request)
        item = queue.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="no such review item")
        row = _item_to_row(item, item.item_id in log.decided_item_ids())
        row["history"] = [
            r.to_row() for r in log.records(action="review_decision", target_id=item_id)
        ]
        return JSONResponse(row)

    # --- review queue: decide (match / no-match / defer) ---------------------
    @router.post("/review-queue/{item_id}/decide")
    async def review_queue_decide(
        request: Request,
        item_id: str,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> Response:
        _require_scope(contributor, WriteScope.VERIFY_SUBMISSIONS)
        queue = _queue(request)
        log = _log(request)
        item = queue.get(item_id)
        if item is None:
            raise HTTPException(status_code=404, detail="no such review item")
        params = await _read_params(request)
        decision = (params.get("decision") or "").strip().lower()
        if decision not in _ER_DECISIONS:
            raise HTTPException(
                status_code=400,
                detail=f"decision must be one of {sorted(_ER_DECISIONS)} (a human choice)",
            )
        reason = (params.get("reason") or params.get("rationale") or "").strip()
        # A model-assisted proposal's decision MUST log the model/prompt that
        # proposed it (SIG-IDENT-026); the suggestion itself never auto-applies.
        payload: dict[str, Any] = {"decision": decision, "reason": reason}
        if item.model_assisted:
            payload["model_id"] = item.model_id
            payload["prompt_version"] = item.prompt_version
        if decision == "defer":
            payload["deferred"] = True
        # Exactly one append-only row, attributed to the human contributor handle.
        record = log.append("review_decision", item_id, actor=contributor.handle, payload=payload)
        return _ok(
            request,
            {"recorded": record.to_row(), "review_decision": _DECIDE_TO_REVIEW.get(decision)},
            redirect="/curate/",
        )

    # --- contradiction disposition (compute-on-read; both claims shown in UI) -
    @router.post("/contradiction/{contradiction_id}/disposition")
    async def contradiction_disposition(
        request: Request,
        contradiction_id: str,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> Response:
        _require_scope(contributor, WriteScope.RESOLUTION_OVERRIDE)
        params = await _read_params(request)
        disposition = (params.get("disposition") or "").strip()
        reason = (params.get("reason") or "").strip()
        if not disposition:
            raise HTTPException(status_code=400, detail="a contradiction disposition is required")
        if not reason:
            # Defining standard §3.1: a decision carries a reason.
            raise HTTPException(status_code=400, detail="a disposition MUST carry a reason (§3.1)")
        record = _log(request).append(
            "contradiction_disposition",
            contradiction_id,
            actor=contributor.handle,
            payload={"disposition": disposition, "reason": reason},
        )
        return _ok(request, {"recorded": record.to_row()}, redirect="/curate/contradictions/")

    # --- task disposition ----------------------------------------------------
    @router.post("/task/{task_id}/disposition")
    async def task_disposition(
        request: Request,
        task_id: str,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> Response:
        _require_scope(contributor, WriteScope.TASK_DISPOSITION)
        params = await _read_params(request)
        disposition = (params.get("disposition") or "").strip()
        reason = (params.get("reason") or "").strip()
        valid = {d.value for d in Disposition}
        if disposition not in valid:
            raise HTTPException(
                status_code=400, detail=f"task disposition must be one of {sorted(valid)}"
            )
        payload: dict[str, Any] = {"disposition": disposition, "reason": reason}
        # The negative-result→data disposition needs its sources searched (SIG-TASK-009).
        if disposition == Disposition.RESOLVED_NO_EVIDENCE_EXISTS.value:
            sources = (params.get("sources_searched") or "").strip()
            if not sources:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "resolved_no_evidence_exists MUST name the sources searched (SIG-TASK-009)"
                    ),
                )
            payload["sources_searched"] = [s.strip() for s in sources.split(",") if s.strip()]
        record = _log(request).append(
            "task_disposition", task_id, actor=contributor.handle, payload=payload
        )
        return _ok(request, {"recorded": record.to_row()}, redirect="/curate/tasks/")

    # --- L0 submission (evidence URL + claim + as-of; refuses without evidence) -
    @router.post("/submission")
    async def submission(
        request: Request,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> Response:
        _require_scope(contributor, WriteScope.QUEUE_SUBMISSION)
        params = await _read_params(request)
        kind_raw = (params.get("kind") or "").strip()
        evidence_url = (params.get("evidence_url") or params.get("evidence_ref") or "").strip()
        claim = (params.get("claim") or "").strip()
        as_of = (params.get("as_of") or "").strip()
        # Parse the opt-in, aggregate-only onboarding timing BEFORE any append, so a
        # malformed value is rejected without leaving a submission row (SIG-CONTRIB-003).
        opted_in = (params.get("timing_opt_in") or "").strip().lower() in {
            "1",
            "true",
            "on",
            "yes",
        }
        elapsed_minutes: float | None = None
        if opted_in and (raw := (params.get("elapsed_minutes") or "").strip()):
            try:
                elapsed_minutes = float(raw)
            except ValueError as exc:
                raise HTTPException(
                    status_code=400, detail="elapsed_minutes must be a number"
                ) from exc
            if elapsed_minutes < 0:
                raise HTTPException(status_code=400, detail="elapsed_minutes must be >= 0")
        if not evidence_url:
            # The L0 form refuses without evidence — a contribution is a piece of
            # evidence (SIG-CONTRIB-002); no evidence, no submission.
            raise HTTPException(status_code=422, detail="a submission MUST carry an evidence URL")
        try:
            kind = SubmissionKind(kind_raw)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"unknown submission kind {kind_raw!r}"
            ) from exc
        # Anti-poisoning: device observations are refused and routed to OSM/DeFlock
        # (SIG-CONTRIB-004) — SIG captures the things OSM does not hold.
        if kind in OSM_ROUTED_KINDS or not is_sig_capturable(kind):
            referral = route_device_observation()
            raise HTTPException(
                status_code=422,
                detail={
                    "refused": "device observations are routed to OSM/DeFlock, not captured",
                    "target": referral.target,
                    "reason": referral.reason,
                },
            )
        receipt = submit(submission_id=f"sub:{_now_iso()}", kind=kind, evidence_ref=evidence_url)
        # Anti-poisoning routing runs server-side (SIG-CONTRIB-010): bursts /
        # coordinated-similar / contested-resolving are flagged to review, NEVER
        # rejected. The verdict is recorded on the append-only row.
        detector = AnomalyDetector()
        signal = ContributionSignal(
            handle=contributor.handle,
            subject_id=claim or evidence_url,
            predicate_id=kind.value,
            content_fingerprint=claim or evidence_url,
            submitted_at=datetime.now(UTC),
            resolves_contested=(params.get("resolves_contested") == "1"),
        )
        verdict = detector.assess([signal])[0]
        record = _log(request).append(
            "submission",
            receipt.submission_id,
            actor=contributor.handle,
            payload={
                "kind": kind.value,
                "evidence_url": evidence_url,
                "claim": claim,
                "as_of": as_of,
                "entry_level": receipt.entry_level.value,
                "produces_l1_claim": receipt.produces_l1_claim,
                "routing": verdict.decision.value,
                "routed_to_review": verdict.routed_to_review,
                "review_reasons": [r.value for r in verdict.reasons],
                # An unverified community submission renders BELOW a records-derived
                # claim (SIG-CONTRIB-011c) — the presentation weight travels with it.
                "visual_weight": visual_weight(ClaimSource.UNVERIFIED_COMMUNITY),
            },
        )
        # Opt-in, AGGREGATE-ONLY onboarding timing (SIG-CONTRIB-003, Part VIII §0.7).
        # The measurement (validated above) is folded into the aggregate histogram
        # ONLY — it is NEVER written to the append-only submission row above (that
        # would be a per-user timing row). No identity, no handle, no per-user row.
        if elapsed_minutes is not None:
            request.app.state.onboarding_timing.record(elapsed_minutes)
        return _ok(request, {"recorded": record.to_row()}, redirect="/curate/submit/")

    # --- onboarding timing (opt-in, AGGREGATE-ONLY: count + median, no per-user rows)
    @router.get("/onboarding-timing")
    def onboarding_timing(
        request: Request,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> Response:
        """The opt-in onboarding-timing **aggregate** (SIG-CONTRIB-003, Part VIII §0.7).

        Returns only a count + median (the two numbers the ≤10-minute study gate
        re-checks). There is deliberately no endpoint that returns any per-user
        timing — none is stored.
        """
        aggregate: OnboardingTimingAggregate = request.app.state.onboarding_timing
        return JSONResponse(aggregate.to_record())

    # --- revert (a new assertion, never a deletion; requires a reason) -------
    @router.post("/revert")
    async def revert(
        request: Request,
        contributor: Contributor = Depends(authenticated_contributor),
    ) -> Response:
        _require_scope(contributor, WriteScope.HUMAN_ASSERTION)
        params = await _read_params(request)
        contribution_id = (params.get("contribution_id") or "").strip()
        reason = (params.get("reason") or "").strip()
        if not contribution_id:
            raise HTTPException(status_code=400, detail="a revert MUST name a contribution")
        if not reason:
            # SIG-CONTRIB-009: a revert MUST record a reason.
            raise HTTPException(
                status_code=400, detail="a revert MUST record a reason (SIG-CONTRIB-009)"
            )
        record = _log(request).append(
            "revert",
            contribution_id,
            actor=contributor.handle,
            payload={"reason": reason, "kind": "new_assertion_not_deletion"},
        )
        return _ok(request, {"recorded": record.to_row()}, redirect="/curate/revert/")

    return router


def _seed_demo_queue() -> ReviewQueue:
    """A small demo review queue so ``sig-api serve-curation`` has something to work.

    One deterministic tier-5 ER match plus one model-assisted extraction carrying a
    labelled machine suggestion (SIG-LLM-001) — enough to drive the UI end to end.
    """
    from resolution.review_queue import ConfidenceFactor

    queue = ReviewQueue()
    queue.enqueue(
        ReviewItem(
            item_id="er_match:agency:okcpd~agency:okc-pd",
            kind="er_match",
            summary="tier 5: agency:okcpd ~ agency:okc-pd (weight +12.40, p=0.998)",
            confidence=(
                ConfidenceFactor(name="name", weight=8.2, detail="exact token overlap"),
                ConfidenceFactor(name="jurisdiction", weight=4.2, detail="same city"),
            ),
            overall_weight=12.4,
            payload={
                "left": {"label": "Oklahoma City Police Department", "jurisdiction": "OKC"},
                "right": {"label": "OKC PD", "jurisdiction": "Oklahoma City"},
            },
        )
    )
    queue.enqueue(
        ReviewItem(
            item_id="model_extraction:gpt-x:12:48",
            kind="model_extraction",
            summary="agency:okcpd operates_alpr 'Flock Safety' [R6/PROPOSED]",
            overall_weight=None,
            model_id="gpt-x",
            prompt_version="p-2026-07",
            payload={
                "suggested_decision": "match",
                "confidence_class": "medium",
                "span": "operates Flock Safety cameras",
            },
        )
    )
    return queue


def create_curation_app(
    *,
    review_queue: ReviewQueue | None = None,
    curation_log: CurationLog | None = None,
    enabled: bool | None = None,
) -> FastAPI:
    """Build the curation app (ADR-068); routes are absent unless enabled (RISK-P21-10).

    When ``enabled`` is false (the default, from ``SIG_CURATION_ENABLED``), the app
    carries **no** ``/v1/curation/*`` routes — the write surface is structurally
    absent, not merely guarded — so the public API process (which never sets the
    flag) can never expose it.
    """
    is_enabled = curation_enabled() if enabled is None else enabled
    app = FastAPI(
        title="SIG curation service (authenticated, non-public)",
        version=__version__,
        description=(
            "The authenticated §34 curation surface (ADR-068). Mounted only when "
            "SIG_CURATION_ENABLED=1; never on the public API process (Part VIII §0.7)."
        ),
    )
    app.state.enabled = is_enabled

    @app.get("/")
    def root() -> dict[str, object]:
        return {
            "service": "SIG curation service",
            "enabled": is_enabled,
            "public": False,
            "note": (
                "authenticated, non-public curation surface (ADR-068); "
                "routes present only when SIG_CURATION_ENABLED=1"
            ),
        }

    if is_enabled:
        app.state.review_queue = review_queue if review_queue is not None else _seed_demo_queue()
        app.state.curation_log = curation_log if curation_log is not None else CurationLog()
        # Opt-in, AGGREGATE-ONLY onboarding timing (SIG-CONTRIB-003, Part VIII §0.7):
        # a count + median only — never a per-user row (see the /submission hook).
        app.state.onboarding_timing = OnboardingTimingAggregate()
        app.include_router(build_curation_router())

    # Defence in depth: the curation surface still may never mount a Part VIII
    # prohibited path (SIG-API-012) — assert it structurally at construction.
    paths = route_paths([r for r in app.routes if isinstance(r, Route)])
    assert_no_prohibited_routes(paths)
    return app
