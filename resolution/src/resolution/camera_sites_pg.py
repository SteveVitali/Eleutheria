# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The PostgreSQL seam for camera-site entity resolution (P30.2b, ADR-105).

* :func:`read_camera_records` reads the observation-level camera records off the
  spine (tier-0, current claims; one record per ``traffic_camera`` subject).
* :func:`materialize_camera_sites` runs one ER pass
  (:func:`resolution.camera_sites.resolve_camera_sites`) and WRITES it append-only:
  every recorded decision is a ``camera_site_match`` row (``INSERT ... ON CONFLICT
  (input_digest) DO NOTHING`` — a re-run over an unchanged spine is +0), every
  PROPOSED merge is enqueued once as a ``review_item`` (stable per pair, so a re-run
  never floods the queue), and the ``camera_site_run`` record is written LAST as the
  completion marker. Writes are batched, one transaction per ``batch_size`` rows (the
  P30.2a lesson: the hosted write path is latency-bound), and a failed batch rolls back
  whole — re-running completes it. Nothing here UPDATEs or DELETEs.
* :func:`read_resolved_site_runs` is the read seam the export uses: the latest
  COMPLETED run's auto-written same-device edges plus its M / N and eval summary.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Sequence
from dataclasses import replace
from typing import Any

from .camera_sites import (
    CameraGoldPair,
    CameraGoldSet,
    CameraRecord,
    CameraSiteResult,
    CameraSiteRules,
    HumanItem,
    HumanVote,
    SiteDecision,
    decision_digest,
    load_camera_gold,
    resolve_camera_sites,
)
from .eval_loop import read_auto_write_threshold

__all__ = [
    "CAMERA_PREDICATES",
    "read_camera_records",
    "read_human_verdicts",
    "materialize_camera_sites",
    "materialize_camera_sites_from_dsn",
    "read_resolved_site_runs",
    "review_item_id",
    "set_role",
]

#: The camera-registry predicates a record is assembled from (ADR-104 registry rows).
CAMERA_PREDICATES = (
    "camera_latitude",
    "camera_longitude",
    "camera_external_ref",
    "camera_name",
    "camera_roadway",
    "camera_direction",
    "camera_operator",
    "camera_jurisdiction",
    "camera_type",
)

_FIELD = {
    "camera_external_ref": "external_ref",
    "camera_name": "name",
    "camera_roadway": "roadway",
    "camera_direction": "direction",
    "camera_operator": "operator",
    "camera_jurisdiction": "jurisdiction",
    "camera_type": "camera_type",
}

#: The claims a decision cites as its evidence (coordinates + the upstream reference).
_EVIDENCE_PREDICATES = frozenset({"camera_latitude", "camera_longitude", "camera_external_ref"})

_RECORDS_SQL = (
    "SELECT DISTINCT ON (c.subject_id, c.predicate_id) "
    "       c.subject_id::text, c.predicate_id, c.value_text, c.claim_id::text, ea.source_id "
    "  FROM claim c "
    "  LEFT JOIN LATERAL ("
    "     SELECT ea.source_id FROM claim_evidence ce "
    "       JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
    "       JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id "
    "      WHERE ce.claim_id = c.claim_id "
    "      ORDER BY ec.retrieved_at, ea.source_id LIMIT 1) ea ON true "
    " WHERE c.sensitivity_tier = 0 AND upper_inf(c.sys_period) "
    "   AND c.predicate_id = ANY(%s) "
    " ORDER BY c.subject_id, c.predicate_id, c.claim_id DESC"
)

# P31.11 duplicate-target lineage (ADR-R9-HUMANER): which connector TARGET a
# record's subject was minted under (the sig.connector.subject identifier is
# `traffic_camera:<source>:<target>:<ref>`) and which captured contents its
# claims cite (evidence_capture.content_digest) — the two evidences
# infer_duplicate_targets consumes.
_TARGETS_SQL = (
    "SELECT ei.entity_id::text, ei.value "
    "  FROM entity_identifier ei "
    " WHERE ei.scheme = 'sig.connector.subject' "
    "   AND ei.value LIKE 'traffic_camera:%%' "
    "   AND ei.entity_id = ANY(%s::uuid[])"
)
_DIGESTS_SQL = (
    "SELECT DISTINCT c.subject_id::text, ec.content_digest "
    "  FROM claim c "
    "  JOIN claim_evidence ce ON ce.claim_id = c.claim_id "
    "  JOIN evidence_capture ec ON ec.capture_id = ce.capture_id "
    " WHERE c.sensitivity_tier = 0 AND upper_inf(c.sys_period) "
    "   AND c.predicate_id = ANY(%s)"
)

# The append-only review surface the run consumes: camera-site items bind a pair
# (payload.left/right); review_decision rows are the votes (decided_at is
# DB-stamped — ordering only, never trusted to be unique).
_REVIEW_ITEMS_SQL = (
    "SELECT item_id, payload->>'left', payload->>'right', "
    "       payload->>'tier', payload->>'tier_label' "
    "  FROM review_item "
    r" WHERE item_id LIKE 'er_match:camera\_site%%' ESCAPE '\' "
    " ORDER BY item_id"
)
_REVIEW_VOTES_SQL = (
    "SELECT d.item_id, d.decision, d.reviewer, d.decided_at, d.decision_id::text "
    "  FROM review_decision d "
    "  JOIN review_item i ON i.item_id = d.item_id "
    r" WHERE i.item_id LIKE 'er_match:camera\_site%%' ESCAPE '\' "
    " ORDER BY d.decided_at, d.decision_id"
)


def set_role(conn: Any, role: str) -> None:
    """``SET ROLE`` with the role name quoted as an identifier (never interpolated raw)."""
    from psycopg import sql

    conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(role)))


def _float(value: Any) -> float | None:
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f and abs(f) != float("inf") else None


def read_camera_records(conn: Any) -> list[CameraRecord]:
    """The observation-level camera records on the spine (one per camera subject).

    A record is a subject carrying a ``camera_latitude`` or ``camera_longitude`` claim —
    exactly the M the resolved-site metric is denominated in. Each attribute is the
    subject's latest current tier-0 claim for that predicate (claim ids are uuidv7, so
    the latest is the most recent capture of that ONE record); both coordinate axes
    therefore come from the same record — never from two sources. The record's source
    is the source of its coordinate evidence.

    P31.11: each record also carries its target-level lineage evidence — the
    connector ``target`` its subject was minted under (parsed out of the
    ``sig.connector.subject`` identifier) and the ``content_digest``s of the
    captures its claims cite — what :func:`infer_duplicate_targets` consumes.
    """
    rows = conn.execute(_RECORDS_SQL, (list(CAMERA_PREDICATES),)).fetchall()
    by_subject: dict[str, dict[str, Any]] = {}
    for subject, predicate, value, claim_id, source_id in rows:
        rec = by_subject.setdefault(subject, {"claims": [], "sources": {}})
        rec[predicate] = value
        rec["sources"][predicate] = source_id
        if predicate in _EVIDENCE_PREDICATES:
            rec["claims"].append(claim_id)
    for subject, digest in conn.execute(_DIGESTS_SQL, (list(CAMERA_PREDICATES),)).fetchall():
        tgt = by_subject.get(subject)
        if tgt is not None:
            tgt.setdefault("digests", set()).add(digest)
    out: list[CameraRecord] = []
    for subject in sorted(by_subject):
        rec = by_subject[subject]
        if "camera_latitude" not in rec and "camera_longitude" not in rec:
            continue  # not an observation-level camera record (no coordinate claim)
        sources = rec["sources"]
        source = (
            sources.get("camera_latitude")
            or sources.get("camera_longitude")
            or next((s for s in sources.values() if s), None)
        )
        out.append(
            CameraRecord(
                subject_id=subject,
                source_id=str(source or ""),
                latitude=_float(rec.get("camera_latitude")),
                longitude=_float(rec.get("camera_longitude")),
                claim_ids=tuple(sorted(rec["claims"])),
                capture_digests=tuple(sorted(rec.get("digests") or ())),
                **{field: rec.get(pred) for pred, field in _FIELD.items()},
            )
        )
    # Target ids: parse the third segment of each record's sig.connector.subject
    # identifier (traffic_camera:<source>:<target>:<ref>) — the subject string,
    # not a trusted field, is the lineage anchor.
    by_id = {r.subject_id: r for r in out}
    targets: dict[str, str] = {}
    for entity, value in conn.execute(_TARGETS_SQL, (list(by_id),)).fetchall():
        parts = str(value).split(":", 3)
        if entity in by_id and len(parts) >= 4 and parts[0] == "traffic_camera":
            targets[entity] = parts[2]
    if targets:
        out = [replace(r, target_id=targets.get(r.subject_id)) for r in out]
    return out


def read_human_verdicts(
    conn: Any,
) -> tuple[list[HumanItem], list[HumanVote]]:
    """The camera-site review surface the run consumes (P31.11 / ADR-R9-HUMANER).

    Items: every ``er_match:camera_site*`` review item (proposals, gold-disputed
    items, routed-back conflicts) that binds a pair via ``payload.left``/``right``.
    Votes: every append-only ``review_decision`` row on those items, oldest first.
    Empty when nothing has been decided — the zero-decision case is the rule,
    not an exception.
    """
    items: list[HumanItem] = []
    for item_id, left, right, tier, tier_label in conn.execute(_REVIEW_ITEMS_SQL).fetchall():
        if not left or not right:
            continue  # an item that binds no pair is never invented into one
        try:
            t = int(tier) if tier is not None else None
        except (TypeError, ValueError):
            t = None
        items.append(
            HumanItem(
                item_id=str(item_id),
                left=str(left),
                right=str(right),
                tier=t,
                tier_label=str(tier_label) if tier_label else None,
            )
        )
    votes: list[HumanVote] = []
    for item_id, decision, reviewer, decided_at, decision_id in conn.execute(
        _REVIEW_VOTES_SQL
    ).fetchall():
        votes.append(
            HumanVote(
                item_id=str(item_id),
                decision=str(decision),
                reviewer=str(reviewer),
                # uuidv7 decision_id orders within a decided_at tick; appended so
                # the fold's ordering is deterministic even on a timestamp tie.
                decided_at=f"{decided_at.isoformat()}#{decision_id}",
            )
        )
    return items, votes


def review_item_id(d: SiteDecision) -> str:
    """The stable review-queue id of a proposed same-device merge (one per pair)."""
    return f"er_match:camera_site:{d.left}:{d.right}"


def _decision_row(result: CameraSiteResult, d: SiteDecision) -> tuple[Any, ...]:
    a = d.assessment
    ev = dict(a.evidence)
    if d.verdict is not None:
        # The human audit trail travels inside match_evidence: which review items
        # decided the pair and what each folded to (SIG-IDENT-025/026).
        ev = {
            **ev,
            "human_items": [[iid, iv] for iid, iv in d.verdict.items],
            "decided_at": d.verdict.decided_at,
        }
    return (
        result.run_key,
        a.left,
        a.right,
        a.tier,
        a.tier_label,
        d.relation,
        d.disposition,
        d.reason,
        d.decided_by,
        json.dumps(ev, sort_keys=True),
        list(a.evidence_claims),
        result.rules_version,
        result.resolver_version,
        decision_digest(result.run_key, d),
    )


_INSERT_MATCH = (
    "INSERT INTO camera_site_match(run_key, left_entity, right_entity, match_tier, tier_label, "
    " relation_type, disposition, disposition_reason, decided_by, match_evidence, "
    " evidence_claims, ruleset_version, resolver_version, input_digest) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::uuid[], %s, %s, %s) "
    "ON CONFLICT (input_digest) DO NOTHING RETURNING match_id"
)

_INSERT_REVIEW = (
    "INSERT INTO review_item(item_id, kind, summary, confidence, overall_weight, payload) "
    "VALUES (%s, 'er_match', %s, %s::jsonb, NULL, %s::jsonb) "
    "ON CONFLICT (item_id) DO NOTHING RETURNING item_id"
)


def _review_args(result: CameraSiteResult, d: SiteDecision) -> tuple[Any, ...]:
    a = d.assessment
    ev = dict(a.evidence)
    summary = (
        f"Same camera? {ev['sources'][0]} vs {ev['sources'][1]}, {ev['distance_m']} m apart "
        f"({a.tier_label}; proposed: {d.reason})"
    )
    confidence = [
        {"name": "distance_m", "weight": 0.0, "detail": f"{ev['distance_m']} m"},
        {
            "name": "shared_upstream_ref",
            "weight": 0.0,
            "detail": str(ev["shared_upstream_ref"] or "none"),
        },
        {
            "name": "one_to_one",
            "weight": 0.0,
            "detail": (
                f"unique within co-location radius: {ev['unique_within_colocation']}; "
                f"mutual nearest: {ev['mutual_nearest']}"
            ),
        },
    ]
    payload = {
        "left": a.left,
        "right": a.right,
        "tier": a.tier,
        "tier_label": a.tier_label,
        "reason": d.reason,
        "evidence": ev,
        "evidence_claims": list(a.evidence_claims),
        "run_key": result.run_key,
        "rules_version": result.rules_version,
    }
    return (
        review_item_id(d),
        summary,
        json.dumps(confidence),
        json.dumps(payload, sort_keys=True),
    )


def _conflict_review_args(result: CameraSiteResult, d: SiteDecision) -> tuple[Any, ...]:
    """A human-conflicted pair routed BACK to review (P31.11): two curators
    disagreed, so the pair is proposed again under its own ``camera_site_conflict``
    item id — a clean adjudication there supersedes the conflicted proposal's
    verdict in the next run's fold (latest decided item governs)."""
    a = d.assessment
    ev = dict(a.evidence)
    payload = {
        "left": a.left,
        "right": a.right,
        "tier": a.tier,
        "tier_label": a.tier_label,
        "reason": "human_conflict",
        "evidence": ev,
        "evidence_claims": list(a.evidence_claims),
        "human_items": [[iid, iv] for iid, iv in (d.verdict.items if d.verdict else ())],
        "run_key": result.run_key,
        "rules_version": result.rules_version,
    }
    summary = (
        f"Same camera? reviewers disagree — adjudicate "
        f"({ev.get('sources', ['?', '?'])[0]} vs {ev.get('sources', ['?', '?'])[1]}, "
        f"{ev.get('distance_m', '?')} m apart; {a.tier_label})"
    )
    return (
        f"er_match:camera_site_conflict:{a.left}:{a.right}",
        summary,
        json.dumps([]),
        json.dumps(payload, sort_keys=True),
    )


def _active_learning_args(
    gold: CameraGoldSet, gp: CameraGoldPair, *, also_proposed: bool
) -> tuple[Any, ...]:
    """A disputed gold pair's review item. When the pair is ALSO a proposal this run, it
    gets its own ``…camera_site_disputed:`` id so the adjudicators' labels reach the
    reviewer instead of colliding (``ON CONFLICT DO NOTHING``) with the proposal item."""
    left, right = sorted((gp.left, gp.right))
    labels = {a.adjudicator: a.label.value for a in gp.adjudications}
    payload = {
        "left": left,
        "right": right,
        "reason": "active_learning:adjudicator_disagreement",
        "gold_set_version": gold.version,
        "gold_pair_id": gp.pair_id,
        "labels": labels,
        "snapshot": dict(gp.snapshot),
    }
    summary = (
        f"Same camera? adjudicators disagree ({gold.verifier}: {labels.get(gold.verifier)}; "
        f"{gold.llm}: {labels.get(gold.llm)}) — gold pair {gp.pair_id}"
    )
    prefix = "er_match:camera_site_disputed" if also_proposed else "er_match:camera_site"
    return (
        f"{prefix}:{left}:{right}",
        summary,
        json.dumps([]),
        json.dumps(payload, sort_keys=True),
    )


def materialize_camera_sites(
    conn: Any,
    *,
    role: str | None = None,
    gold: CameraGoldSet | None = None,
    threshold: float | None = None,
    records: Sequence[CameraRecord] | None = None,
    rules: CameraSiteRules | None = None,
    batch_size: int = 1_000,
    progress: Callable[[str, int, int], None] | None = None,
) -> dict[str, Any]:
    """Run one camera-site ER pass over the spine and materialize it (append-only).

    ``gold`` defaults to the committed camera gold set; ``threshold`` to the published
    auto-write floor. Returns a JSON-able summary: the run's M / N / dedup ratio / eval
    fields plus ``inserted`` / ``skipped_existing`` counts (+0 on an unchanged re-run).
    """
    if role:
        set_role(conn, role)
    the_gold = gold if gold is not None else load_camera_gold()
    floor = threshold if threshold is not None else read_auto_write_threshold()
    recs = list(records) if records is not None else read_camera_records(conn)
    human_items, human_votes = read_human_verdicts(conn)
    if progress is not None:
        progress("read", len(recs), 0)
    result = resolve_camera_sites(
        recs,
        gold=the_gold,
        threshold=floor,
        rules=rules,
        human_items=human_items,
        human_votes=human_votes,
    )
    if progress is not None:
        progress("resolved", len(result.decisions), 0)

    inserted = skipped = enqueued = 0
    decisions = list(result.decisions)
    for start in range(0, len(decisions), batch_size):
        batch = decisions[start : start + batch_size]
        with conn.transaction():
            for d in batch:
                if conn.execute(_INSERT_MATCH, _decision_row(result, d)).fetchone():
                    inserted += 1
                else:
                    skipped += 1
                if d.disposition == "proposed":
                    # A human conflict is routed back under its own
                    # camera_site_conflict item (the plain proposal id is the
                    # already-decided item); every other proposal is the
                    # ordinary per-pair item.
                    args = (
                        _conflict_review_args(result, d)
                        if d.reason == "human_conflict"
                        else _review_args(result, d)
                    )
                    if conn.execute(_INSERT_REVIEW, args).fetchone():
                        enqueued += 1
        if progress is not None:
            progress("written", start + len(batch), inserted)

    # Active learning (ADR-099 §3, design §2.4): the gold pairs the verifier and the LLM
    # adjudicator DISAGREE on are routed to the human queue — whatever this run decided for
    # them — so review spends its labels where they buy the most (one stable item per pair).
    active = 0
    if the_gold is not None:
        present = {r.subject_id for r in recs}
        disputed = set(the_gold.disputed())
        proposed = {(d.left, d.right) for d in decisions if d.disposition == "proposed"}
        with conn.transaction():
            for gp in the_gold.pairs:
                if gp.pair_id not in disputed or gp.left not in present or gp.right not in present:
                    continue
                also_proposed = tuple(sorted((gp.left, gp.right))) in proposed
                args = _active_learning_args(the_gold, gp, also_proposed=also_proposed)
                if conn.execute(_INSERT_REVIEW, args).fetchone():
                    active += 1

    summary = result.summary()
    with conn.transaction():
        run_inserted = (
            conn.execute(
                "INSERT INTO camera_site_run(run_key, ruleset_version, resolver_version, "
                " gold_set_version, auto_write_tiers, observation_count, cluster_count, summary) "
                "VALUES (%s, %s, %s, %s, %s::smallint[], %s, %s, %s::jsonb) "
                "ON CONFLICT (run_key) DO NOTHING RETURNING run_key",
                (
                    result.run_key,
                    result.rules_version,
                    result.resolver_version,
                    result.gold_version,
                    sorted(result.auto_write_tiers),
                    result.observation_count,
                    result.cluster_count,
                    json.dumps(summary, sort_keys=True, default=str),
                ),
            ).fetchone()
            is not None
        )
    return {
        **summary,
        "inserted": inserted,
        "skipped_existing": skipped,
        "review_items_enqueued": enqueued,
        "active_learning_enqueued": active,
        "run_record_inserted": run_inserted,
    }


def materialize_camera_sites_from_dsn(dsn: str, **kwargs: Any) -> dict[str, Any]:
    """Open an autocommit connection from ``dsn`` and materialize (CLI convenience)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        return materialize_camera_sites(conn, **kwargs)
    finally:
        conn.close()


def read_resolved_site_runs(conn: Any, *, role: str | None = None) -> list[dict[str, Any]]:
    """The latest COMPLETED camera-site ER run, as the export's read seam (ADR-105).

    Returns ``[]`` when no run has completed (the surface then keeps its observation-level
    framing — never a fabricated resolved-site count), else a one-element list:
    ``{run_key, observation_count, cluster_count, auto_write_tiers, summary,
    auto_write_edges, human_accept_edges, resolved_edges, proposed_count,
    cannot_link_count, refused_count}``. P31.11: resolved sites are formed by BOTH
    ``auto_write`` edges AND valid ``human_accept`` edges (``resolved_edges`` is the
    union); ``proposed`` merges await review, ``human_reject``/``cannot_link`` pairs
    are recorded never to cluster, and ``refused`` accept attempts are counted —
    none of those form sites.
    """
    if role:
        set_role(conn, role)
    run = conn.execute(
        "SELECT run_key, observation_count, cluster_count, auto_write_tiers, summary "
        "  FROM camera_site_run ORDER BY completed_at DESC, run_key DESC LIMIT 1"
    ).fetchone()
    if run is None:
        return []
    rows = conn.execute(
        "SELECT left_entity::text, right_entity::text, disposition FROM camera_site_match "
        " WHERE run_key = %s AND disposition IN ('auto_write', 'human_accept', 'proposed', "
        "                                      'human_reject', 'refused') "
        " ORDER BY left_entity, right_entity",
        (run[0],),
    ).fetchall()
    auto_edges = [(str(a), str(b)) for a, b, disp in rows if disp == "auto_write"]
    human_edges = [(str(a), str(b)) for a, b, disp in rows if disp == "human_accept"]
    proposed_count = sum(1 for _a, _b, disp in rows if disp == "proposed")
    cannot_link_count = sum(1 for _a, _b, disp in rows if disp == "human_reject")
    refused_count = sum(1 for _a, _b, disp in rows if disp == "refused")
    summary = run[4] if isinstance(run[4], dict) else json.loads(run[4] or "{}")
    return [
        {
            "run_key": run[0],
            "observation_count": int(run[1]),
            "cluster_count": int(run[2]),
            "auto_write_tiers": [int(t) for t in (run[3] or [])],
            "summary": summary,
            "auto_write_edges": auto_edges,
            "human_accept_edges": human_edges,
            "resolved_edges": sorted(set(auto_edges) | set(human_edges)),
            "proposed_count": proposed_count,
            "cannot_link_count": cannot_link_count,
            "refused_count": refused_count,
        }
    ]
