# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The camera-site review surface's queue logic (P31.10, ADR-105/ADR-068).

Everything the PG-backed curation surface, the stratified campaign sampler, and
the offline JSONL path need that is *specific to camera-site review items*:

* **Family/stratum vocabulary.** The camera-site queue is two item-id families
  — ``er_match:camera_site:`` (proposals) and ``er_match:camera_site_disputed:``
  (adjudicator disagreements that are also proposals) — and the P31.3
  ``er_match:identity_duplicate:`` family is *excluded* from it. A review
  **stratum** is a predicate, not a partition: ``disputed`` (the disputed
  prefix or an ``active_learning:adjudicator_disagreement`` reason),
  ``soft-conflict`` (``reason`` ``soft_conflict:*``), or the match tier
  ``1g``/``3g``/``4g``/``5g``. A soft-conflicted 3g proposal is in *both* ``3g``
  and ``soft-conflict`` — tier-3 proposals on the real spine ARE the
  soft-conflicted ones, and the audit intent is that humans see every stratum.
* **Evidence.** :func:`read_observation` re-reads one subject's camera record
  off the spine (the same claim query shape as
  :func:`camera_sites_pg.read_camera_records`, per subject) and
  :func:`pair_evidence` assembles the two-observation view a reviewer weighs —
  coordinates are returned at spine precision here; the *curator's* §19.4
  reduction is applied by the caller (the curation app), which owns the tier.
* **Campaign sampler.** :func:`draw_sample` draws a stratified, seeded,
  reproducible sample of PENDING items; :func:`materialize_campaign` tags the
  draw append-only in ``review_campaign`` / ``review_campaign_item`` (+0 on a
  re-draw of the same design under the same id; a different design under a
  taken id is refused, never silently merged).
* **Offline path.** :func:`export_rows` serialises pending items to JSONL rows
  for a labelling session; :func:`import_decisions` writes the labels back
  through :meth:`PgReviewQueue.decide` — the same append-only decision path,
  so import never bypasses it. ``unsure``/empty labels write NOTHING (the item
  stays pending; the schema admits only ``accept``/``reject``).

Nothing here mutates an existing row or touches the claim spine's append-only
tables beyond ``review_*``: the only writes are ``INSERT ... ON CONFLICT
DO NOTHING`` into the two campaign tables.
"""

from __future__ import annotations

import json
import random
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from .review_queue import ACCEPT, REJECT, ReviewItem

__all__ = [
    "CAMERA_SITE_ITEM_PREFIX",
    "CAMERA_SITE_DISPUTED_PREFIX",
    "IDENTITY_DUPLICATE_PREFIX",
    "CAMERA_SITE_PREFIXES",
    "DEFAULT_STRATA",
    "DEFAULT_SAMPLE_SIZE",
    "is_camera_site_item",
    "stratum_for",
    "parse_strata",
    "pending_items",
    "read_observation",
    "pair_evidence",
    "draw_sample",
    "materialize_campaign",
    "export_rows",
    "import_decisions",
]

#: The proposal family P30.2b enqueues (``er_match:camera_site:{a}:{b}``).
CAMERA_SITE_ITEM_PREFIX = "er_match:camera_site:"
#: Disputed gold pairs that are ALSO proposals get their own id family so the
#: adjudicators' labels reach the reviewer (camera_sites_pg._active_learning_args).
CAMERA_SITE_DISPUTED_PREFIX = "er_match:camera_site_disputed:"
#: The P31.3 identity-triage family — a different queue, excluded from the
#: camera-site surface even though it shares the two tables.
IDENTITY_DUPLICATE_PREFIX = "er_match:identity_duplicate:"
#: Both camera-site families (the disputed prefix does not start with the plain
#: one — "camera_site_" vs "camera_site:" — so LIKE-prefix matching is disjoint).
CAMERA_SITE_PREFIXES = (CAMERA_SITE_ITEM_PREFIX, CAMERA_SITE_DISPUTED_PREFIX)

#: The stratum names the sampler knows (spec §6 Q11 design). Tiers 1g/3g are
#: auto-write tiers — included on purpose so humans AUDIT them.
DEFAULT_STRATA: tuple[str, ...] = ("1g", "3g", "4g", "5g", "soft-conflict", "disputed")

#: The §6 Q11 default design (~400 stratified pairs) — the Round-10 campaign
#: design, materializable but NOT a Round-9 deliverable anyone labels.
DEFAULT_SAMPLE_SIZE = 400

_DISPUTED_REASON = "active_learning:adjudicator_disagreement"


def is_camera_site_item(item_id: str) -> bool:
    """Whether ``item_id`` is a camera-site review proposal (either family)."""
    return item_id.startswith(CAMERA_SITE_PREFIXES)


def stratum_for(item_id: str, payload: Mapping[str, Any]) -> str:
    """The review stratum of a camera-site item (a predicate, not a partition).

    ``disputed`` covers both spellings of an adjudicator disagreement — the
    ``er_match:camera_site_disputed:`` id family and a plain ``camera_site:``
    item whose reason is ``active_learning:adjudicator_disagreement``. A
    ``soft_conflict:*`` reason is the ``soft-conflict`` bucket. Everything else
    falls to its match tier (``{tier}g``), or ``other`` when the proposal
    carries no tier (shouldn't happen for a camera-site proposal).
    """
    if item_id.startswith(CAMERA_SITE_DISPUTED_PREFIX):
        return "disputed"
    reason = str(payload.get("reason") or "")
    if reason == _DISPUTED_REASON:
        return "disputed"
    if reason.startswith("soft_conflict:"):
        return "soft-conflict"
    tier = payload.get("tier")
    if isinstance(tier, int):
        return f"{tier}g"
    return "other"


def _strata_case(alias: str = "ri") -> str:
    """The SQL CASE that mirrors :func:`stratum_for` for set-based filtering."""
    return (
        "CASE"
        f" WHEN {alias}.item_id LIKE %s THEN 'disputed'"  # camera_site_disputed:
        f" WHEN {alias}.payload->>'reason' = %s THEN 'disputed'"
        f" WHEN {alias}.payload->>'reason' LIKE %s THEN 'soft-conflict'"
        f" WHEN {alias}.payload->>'tier' ~ '^-?[0-9]+$'"
        f" THEN ({alias}.payload->>'tier') || 'g'"
        " ELSE 'other' END"
    )


def _strata_params() -> tuple[Any, ...]:
    return (CAMERA_SITE_DISPUTED_PREFIX + "%", _DISPUTED_REASON, "soft_conflict:%")


def parse_strata(spec: str | None) -> list[tuple[str, int | None]]:
    """Parse a ``--strata`` spec into ``(name, requested)`` pairs.

    ``spec`` is a comma list of ``name`` or ``name:count`` — e.g.
    ``"1g,3g,4g,5g,soft-conflict,disputed"`` or ``"4g:150,5g:150"``. A bare name
    gets ``requested=None`` (the ``--n`` share applies). ``all``/``auto`` expands
    to the default six; ``name:all`` draws the whole stratum.
    """
    if not spec or spec.strip().lower() in {"all", "auto"}:
        return [(s, None) for s in DEFAULT_STRATA]
    out: list[tuple[str, int | None]] = []
    for token in spec.split(","):
        token = token.strip()
        if not token:
            continue
        name, _, raw = token.partition(":")
        name = name.strip()
        if name not in DEFAULT_STRATA and name != "other":
            raise ValueError(
                f"unknown stratum {name!r} (known: {', '.join(DEFAULT_STRATA)}, other)"
            )
        if raw.strip().lower() in {"", "auto"}:
            out.append((name, None))
        elif raw.strip().lower() == "all":
            out.append((name, -1))  # -1 marks "the stratum's whole universe"
        else:
            try:
                count = int(raw)
            except ValueError as exc:
                raise ValueError(f"stratum {name!r} count {raw!r} is not a number") from exc
            if count < 0:
                raise ValueError(f"stratum {name!r} count must be >= 0")
            out.append((name, count))
    if not out:
        raise ValueError("an empty strata spec draws nothing")
    return out


_ITEM_COLS = (
    "item_id",
    "kind",
    "summary",
    "confidence",
    "overall_weight",
    "model_id",
    "prompt_version",
    "payload",
)


def _item_from_row(row: Sequence[Any]) -> ReviewItem:
    return ReviewItem.from_row(
        {
            "item_id": row[0],
            "kind": row[1],
            "summary": row[2],
            "confidence": row[3] or [],
            "overall_weight": row[4],
            "model_id": row[5],
            "prompt_version": row[6],
            "payload": row[7] or {},
        }
    )


def pending_items(
    conn: Any,
    *,
    prefixes: Sequence[str] | None = None,
    exclude_prefixes: Sequence[str] = (),
    tier: int | None = None,
    bucket: str | None = None,
    campaign: str | None = None,
    limit: int | None = None,
) -> tuple[ReviewItem, ...]:
    """Pending ``review_item`` rows (no ``review_decision``), filtered.

    ``prefixes``/``exclude_prefixes`` are literal ``item_id`` prefixes;
    ``tier`` matches the payload's integer ``tier``; ``bucket`` is a stratum
    name (:func:`stratum_for`'s SQL twin); ``campaign`` restricts to a drawn
    campaign's membership. Ordered by ``item_id`` (deterministic for the UI
    and for the seeded sampler).
    """
    where = ["rd.item_id IS NULL"]
    params: list[Any] = []
    if prefixes is not None:
        where.append("ri.item_id LIKE ANY(%s)")
        params.append([p + "%" if not p.endswith("%") else p for p in prefixes])
    for p in exclude_prefixes:
        where.append("ri.item_id NOT LIKE %s")
        params.append(p + "%" if not p.endswith("%") else p)
    if tier is not None:
        where.append("(ri.payload->>'tier') ~ '^-?[0-9]+$'")
        where.append("(ri.payload->>'tier')::int = %s")
        params.append(tier)
    if bucket is not None:
        where.append(f"({_strata_case('ri')}) = %s")
        params.extend(_strata_params())
        params.append(bucket)
    if campaign is not None:
        where.append(
            "EXISTS (SELECT 1 FROM review_campaign_item ci "
            "WHERE ci.campaign_id = %s AND ci.item_id = ri.item_id)"
        )
        params.append(campaign)
    sql = (
        f"SELECT {', '.join('ri.' + c for c in _ITEM_COLS)} FROM review_item ri "
        "LEFT JOIN review_decision rd ON rd.item_id = ri.item_id "
        f"WHERE {' AND '.join(where)} ORDER BY ri.item_id"
    )
    if limit is not None:
        sql += " LIMIT %s"
        params.append(limit)
    return tuple(_item_from_row(r) for r in conn.execute(sql, params).fetchall())


# --------------------------------------------------------------------------- #
# Evidence view — the two observations a reviewer weighs, re-read per subject  #
# --------------------------------------------------------------------------- #
def read_observation(conn: Any, subject_id: str) -> dict[str, Any] | None:
    """One subject's camera record at SPINE precision (the raw observation).

    The same per-subject claim query shape as
    :func:`camera_sites_pg.read_camera_records` — latest current tier-0 claim
    per predicate — so a record's fields are exactly what the resolver weighed.
    Coordinate reduction to the curator's §19.4 tier is the CALLER's job (the
    curation app owns the contributor tier); this returns the raw values.
    Returns ``None`` when the subject carries no camera claims.
    """
    from .camera_sites_pg import _RECORDS_SQL

    sql = _RECORDS_SQL.replace(
        "WHERE c.sensitivity_tier = 0",
        "WHERE c.subject_id = %s AND c.sensitivity_tier = 0",
    )
    # _RECORDS_SQL is DISTINCT ON (subject_id, predicate_id) — keep it, with a
    # subject predicate added so one record is read, not the whole spine.
    rows = conn.execute(
        sql,
        (
            subject_id,
            [
                "camera_latitude",
                "camera_longitude",
                "camera_external_ref",
                "camera_name",
                "camera_roadway",
                "camera_direction",
                "camera_operator",
                "camera_jurisdiction",
                "camera_type",
            ],
        ),
    ).fetchall()
    rec: dict[str, Any] = {"claims": [], "sources": {}}
    for _subject, predicate, value, claim_id, source_id in rows:
        rec[predicate] = value
        rec["sources"][predicate] = source_id
        if predicate in {"camera_latitude", "camera_longitude", "camera_external_ref"}:
            rec["claims"].append(claim_id)
    if "camera_latitude" not in rec and "camera_longitude" not in rec:
        return None

    def _f(v: Any) -> float | None:
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        return f if f == f and abs(f) != float("inf") else None

    sources = rec["sources"]
    return {
        "subject_id": subject_id,
        "source_id": str(
            sources.get("camera_latitude")
            or sources.get("camera_longitude")
            or next((s for s in sources.values() if s), "")
        ),
        "latitude": _f(rec.get("camera_latitude")),
        "longitude": _f(rec.get("camera_longitude")),
        "external_ref": rec.get("camera_external_ref"),
        "name": rec.get("camera_name"),
        "roadway": rec.get("camera_roadway"),
        "direction": rec.get("camera_direction"),
        "operator": rec.get("camera_operator"),
        "jurisdiction": rec.get("camera_jurisdiction"),
        "camera_type": rec.get("camera_type"),
        "claim_ids": sorted(rec["claims"]),
    }


def pair_evidence(conn: Any, item: ReviewItem) -> dict[str, Any] | None:
    """The two-observation evidence view for a camera-site review item.

    Returns ``None`` for non-camera-site items. For ``camera_site:`` proposals
    the payload already carries the matcher evidence (tier, tier_label, rule,
    distance_m, sources, soft_conflicts, one-to-one flags); for
    ``camera_site_disputed:`` items it carries the adjudicators' labels and the
    records snapshot. Both sides' observations are re-read off the spine
    (:func:`read_observation`) — the CURRENT claims, spine precision.
    """
    if not is_camera_site_item(item.item_id):
        return None
    payload = dict(item.payload)
    left = payload.get("left")
    right = payload.get("right")
    view: dict[str, Any] = {
        "left_subject": left,
        "right_subject": right,
        "stratum": stratum_for(item.item_id, payload),
        "tier": payload.get("tier"),
        "tier_label": payload.get("tier_label"),
        "reason": payload.get("reason"),
        "score": item.overall_weight,
        "left_observation": read_observation(conn, str(left)) if left else None,
        "right_observation": read_observation(conn, str(right)) if right else None,
    }
    ev = payload.get("evidence")
    if isinstance(ev, Mapping):
        view["distance_m"] = ev.get("distance_m")
        view["rule"] = ev.get("rule")
        view["soft_conflicts"] = list(ev.get("soft_conflicts") or [])
        view["match_evidence"] = dict(ev)
    snap = payload.get("snapshot")
    if isinstance(snap, Mapping):
        view["distance_m"] = snap.get("distance_m", view.get("distance_m"))
        view["snapshot"] = dict(snap)
    labels = payload.get("labels")
    if isinstance(labels, Mapping):
        view["adjudicator_labels"] = dict(labels)
    return view


# --------------------------------------------------------------------------- #
# The stratified, seeded campaign sampler (design §6 Q11 — Round-10 design)    #
# --------------------------------------------------------------------------- #
def draw_sample(
    conn: Any,
    strata: Sequence[tuple[str, int | None]],
    *,
    n: int = DEFAULT_SAMPLE_SIZE,
    seed: str = "0",
) -> dict[str, list[str]]:
    """Draw a stratified, seeded, reproducible sample of pending camera-site items.

    Strata are predicates (an item may qualify for several); each stratum's
    candidate set is all PENDING camera-site items satisfying it. Seeding is
    per-stratum (``Random(f"{seed}:{stratum}")`` over the sorted ids) so adding
    or removing a stratum never perturbs another stratum's draw.

    ``n`` is the UNIQUE-item target: an equal first-pass share per stratum,
    then a deterministic second pass that tops up, in spec order, strata with
    undrawn candidates until the union reaches ``n`` or every stratum is
    exhausted (the count is honest — small strata simply draw their universe).
    ``name:all`` draws that stratum's whole universe.

    Returns ``{stratum: [item_id, ...]}`` (the drawn ids per stratum; the union
    is the sample, and the FIRST stratum in spec order that drew an item is its
    campaign label).
    """
    pending = pending_items(conn, prefixes=CAMERA_SITE_PREFIXES)
    by_stratum: dict[str, list[str]] = {}
    for name, _req in strata:
        by_stratum[name] = sorted(
            it.item_id for it in pending if stratum_for(it.item_id, it.payload) == name
        )
    order = [name for name, _req in strata]

    # First pass: explicit per-stratum counts, else an equal share of n.
    share = max(1, n // max(1, len(order)))
    quotas: dict[str, int] = {}
    for name, req in strata:
        quotas[name] = len(by_stratum[name]) if req == -1 else (req if req is not None else share)

    drawn: dict[str, list[str]] = {}
    shuffled: dict[str, list[str]] = {}
    for name in order:
        ids = list(by_stratum[name])
        rng = random.Random(f"{seed}:{name}")
        rng.shuffle(ids)
        shuffled[name] = ids
        drawn[name] = ids[: min(quotas[name], len(ids))]

    # Second pass: top up, in spec order, the strata with undrawn headroom
    # until the union reaches n (a small stratum simply contributes its all).
    union = set().union(*drawn.values()) if drawn else set()
    deficit = n - len(union)
    for name in order:
        while deficit > 0 and len(drawn[name]) < len(shuffled[name]):
            candidate = shuffled[name][len(drawn[name])]
            drawn[name].append(candidate)
            union.add(candidate)
            deficit = n - len(union)
    return drawn


def materialize_campaign(
    conn: Any,
    *,
    campaign_id: str,
    purpose: str,
    design: Mapping[str, Any],
    created_by: str,
    drawn: Mapping[str, Sequence[str]],
) -> dict[str, Any]:
    """Tag a drawn sample as an append-only campaign (+0 on a re-draw).

    Inserts the ``review_campaign`` row (``ON CONFLICT DO NOTHING``) and one
    ``review_campaign_item`` row per (campaign, drawn item) — each item's
    stratum is the FIRST stratum in spec order that drew it. When the id is
    already taken by a DIFFERENT design, refuses (ValueError) rather than
    mixing two draws under one label. Returns a JSON-able summary.
    """
    if not created_by:
        raise ValueError("a campaign MUST record the tool/engineering actor that drew it")
    # First stratum (spec order) that drew an item owns its campaign label.
    item_stratum: dict[str, str] = {}
    for stratum, ids in drawn.items():
        for item_id in ids:
            item_stratum.setdefault(item_id, stratum)
    with conn.transaction():
        row = conn.execute(
            "INSERT INTO review_campaign(campaign_id, purpose, design, created_by) "
            "VALUES (%s, %s, %s::jsonb, %s) ON CONFLICT (campaign_id) DO NOTHING "
            "RETURNING campaign_id",
            (campaign_id, purpose, json.dumps(dict(design), sort_keys=True), created_by),
        ).fetchone()
        if row is None:
            existing = conn.execute(
                "SELECT design FROM review_campaign WHERE campaign_id = %s", (campaign_id,)
            ).fetchone()
            assert existing is not None
            prior = existing[0] if isinstance(existing[0], dict) else json.loads(existing[0])
            if prior.get("design_digest") != design.get("design_digest"):
                raise ValueError(
                    f"campaign {campaign_id!r} already exists with a different design "
                    "(append-only — pick a new campaign id for a new draw)"
                )
        inserted = 0
        for item_id, stratum in sorted(item_stratum.items()):
            if conn.execute(
                "INSERT INTO review_campaign_item(campaign_id, item_id, stratum) "
                "VALUES (%s, %s, %s) ON CONFLICT (campaign_id, item_id) DO NOTHING "
                "RETURNING item_id",
                (campaign_id, item_id, stratum),
            ).fetchone():
                inserted += 1
    return {
        "campaign_id": campaign_id,
        "campaign_inserted": row is not None,
        "items": len(item_stratum),
        "items_inserted": inserted,
        "items_skipped_existing": len(item_stratum) - inserted,
    }


# --------------------------------------------------------------------------- #
# The offline JSONL path — export pending items, import labelled decisions    #
# --------------------------------------------------------------------------- #
def export_rows(
    conn: Any,
    *,
    campaign: str | None = None,
    prefixes: Sequence[str] | None = None,
    tier: int | None = None,
    bucket: str | None = None,
) -> list[dict[str, Any]]:
    """Pending items as JSONL-ready labelling rows (decision left blank).

    Each row carries everything a labeller needs offline: the item id, its
    summary, stratum, the payload (matcher evidence / adjudicator labels), and
    a blank ``decision``/``rationale`` to fill — ``accept`` | ``reject`` |
    ``unsure`` (unsure writes nothing on import).
    """
    items = pending_items(conn, prefixes=prefixes, tier=tier, bucket=bucket, campaign=campaign)
    rows = []
    for it in items:
        rows.append(
            {
                "item_id": it.item_id,
                "kind": it.kind,
                "summary": it.summary,
                "stratum": (
                    stratum_for(it.item_id, it.payload) if is_camera_site_item(it.item_id) else None
                ),
                "overall_weight": it.overall_weight,
                "confidence": [f.to_row() for f in it.confidence],
                "payload": dict(it.payload),
                "decision": None,
                "rationale": None,
            }
        )
    return rows


def import_decisions(
    queue: Any,
    rows: Iterable[Mapping[str, Any]],
    *,
    reviewer: str,
) -> dict[str, Any]:
    """Write labelled decisions back through the append-only ``decide`` path.

    ``rows`` are the export format with ``decision`` filled: ``accept`` /
    ``reject`` append one ``review_decision`` each via ``queue.decide`` (the
    ONLY write path — import never bypasses it); ``unsure``/``defer``/empty
    write NOTHING (the item stays pending — the schema admits no third state).
    Any other value fails loudly. Returns ``{appended, skipped, errors}``.
    """
    if not reviewer:
        raise ValueError("a review decision MUST record the human reviewer (SIG-IDENT-026)")
    appended = 0
    skipped = 0
    errors: list[str] = []
    for i, row in enumerate(rows):
        item_id = str(row.get("item_id") or "").strip()
        decision = str(row.get("decision") or "").strip().lower()
        rationale = row.get("rationale")
        rationale = str(rationale).strip() if rationale else None
        if not item_id:
            errors.append(f"line {i + 1}: missing item_id")
            continue
        if decision in {"", "unsure", "defer", "deferred", "skip"}:
            skipped += 1  # "unsure" persists nothing — the item stays pending.
            continue
        if decision == "match":
            decision = ACCEPT
        elif decision in {"no-match", "no_match"}:
            decision = REJECT
        if decision not in {ACCEPT, REJECT}:
            errors.append(f"line {i + 1} ({item_id}): invalid decision {decision!r}")
            continue
        try:
            queue.decide(item_id, decision, reviewer=reviewer, rationale=rationale or None)
        except ValueError as exc:
            errors.append(f"line {i + 1} ({item_id}): {exc}")
            continue
        appended += 1
    return {"appended": appended, "skipped": skipped, "errors": errors}
