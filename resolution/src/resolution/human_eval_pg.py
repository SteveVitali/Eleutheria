# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""PG writers/readers for the P32.9 human-evaluation schema (ADR-128).

Every function takes an open psycopg connection and an explicit ``role`` and
runs under ``SET ROLE`` — the schema's grant/RLS matrix is the enforcement,
this module just speaks the correct role + GUC:

* preparation (``sig_eval_admin``): preregister campaign + manifest + samples,
  build packets, draw assignments, record attestation events;
* labeling (``sig_eval_reviewer`` under ``sig.eval_reviewer`` GUC): append a
  first-pass label — the RLS ``WITH CHECK`` refuses any reviewer id that is
  not the session's own, and the packet digest is re-checked against the
  current packet row so a stale packet cannot be labeled;
* sealing authority (``sig_eval_custodian``): record adjudications and the
  authorized unsealing decision (``human_eval_release``).

Operational ``sig_materialize`` has deliberately NO access to the eval tables
(it may read only ``human_eval_label_operational``, which is empty until an
explicit operational-scope release) — the sealed-label isolation is proven by
the tests, not by convention here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from .camera_sites_pg import set_role
from .human_eval import (
    label_watermark,
    manifest_digest,
    membership_digest,
    packet_digest,
)

__all__ = [
    "frame_from_review_items",
    "read_campaign",
    "read_samples",
    "eval_units_from_campaign",
    "run_shadow_evaluation",
    "preregister_campaign",
    "write_manifest",
    "write_samples",
    "write_packets",
    "assign_reviewers",
    "record_attestation",
    "record_label",
    "record_adjudication",
    "record_release",
    "campaign_status",
    "export_workbook",
    "verify_manifest",
    "campaign_watermark",
]

_ADMIN = "sig_eval_admin"
_REVIEWER = "sig_eval_reviewer"
_CUSTODIAN = "sig_eval_custodian"

_INSERT_CAMPAIGN = (
    "INSERT INTO human_eval_campaign"
    "(campaign_id, purpose, protocol_digest, frame_snapshot, ruleset_digest,"
    " seed, design, created_by) "
    "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT (campaign_id) DO NOTHING"
)
_INSERT_MANIFEST = (
    "INSERT INTO human_eval_manifest"
    "(campaign_id, manifest_digest, membership_digest, sample_count,"
    " denominators, created_by) "
    "VALUES (%s,%s,%s,%s,%s::jsonb,%s) ON CONFLICT (campaign_id) DO NOTHING"
)
_INSERT_SAMPLE = (
    "INSERT INTO human_eval_sample"
    "(campaign_id, sample_id, pair_id, left_ref, right_ref, packet_digest,"
    " partition, estimand, stratum_id, dependency_group_id,"
    " source_lineage_ids, selection_probability, weight, draw_order,"
    " reference_basis) "
    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) "
    "ON CONFLICT (campaign_id, sample_id) DO NOTHING"
)
_INSERT_PACKET = (
    "INSERT INTO human_eval_packet(campaign_id, sample_id, packet_digest, payload) "
    "VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT (campaign_id, sample_id) DO NOTHING"
)
_INSERT_ASSIGNMENT = (
    "INSERT INTO human_eval_assignment"
    "(campaign_id, sample_id, reviewer_id, pass_no, assigned_by) "
    "VALUES (%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING"
)
_INSERT_ATTESTATION = (
    "INSERT INTO human_eval_attestation"
    "(campaign_id, reviewer_id, kind, detail, recorded_by) "
    "VALUES (%s,%s,%s,%s::jsonb,%s) RETURNING attestation_id"
)
_INSERT_LABEL = (
    "INSERT INTO human_eval_label"
    "(campaign_id, sample_id, reviewer_id, label_round, label, reason_codes,"
    " evidence_refs, rubric_version, packet_digest, attestation_id,"
    " supersedes_label_id, label_digest) "
    "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s) RETURNING label_id"
)
_INSERT_ADJUDICATION = (
    "INSERT INTO human_eval_adjudication"
    "(campaign_id, sample_id, adjudicator_id, phase, label, reason,"
    " evidence_refs, supersedes_adjudication_id) "
    "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s) RETURNING adjudication_id"
)
_INSERT_RELEASE = (
    "INSERT INTO human_eval_release"
    "(campaign_id, scope, authorized_by, detail) "
    "VALUES (%s,%s,%s,%s::jsonb) ON CONFLICT (campaign_id, scope) DO NOTHING"
    " RETURNING release_id"
)


def _connect(conn: Any, role: str | None) -> None:
    if role:
        set_role(conn, role)


def frame_from_review_items(
    conn: Any,
    *,
    prefixes: Sequence[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Build a camera-site evaluation frame from PENDING operational items.

    Reads the P31.10 review surface read-only: every pending camera-site
    proposal becomes one frame pair whose dependency attributes are derived
    from the spine — ``source_lineage_ids`` = the union of both sides' claim
    source ids (copied/republished observations sharing an upstream record
    can never cross the split), ``entity_neighborhood`` = the ~1 km cell the
    pair occupies (the component proxy — pairs sharing a subject entity are
    grouped regardless, via the subject keys), ``republisher_family`` /
    ``mirror_group_id`` stay empty when the spine carries no recorded family
    (an honest unknown, never a fabricated grouping).
    """
    from .camera_site_review import (
        CAMERA_SITE_PREFIXES,
        pending_items,
        read_observation,
        stratum_for,
    )

    rows: list[dict[str, Any]] = []
    for it in pending_items(conn, prefixes=list(prefixes or CAMERA_SITE_PREFIXES), limit=limit):
        left = str(it.payload.get("left") or "")
        right = str(it.payload.get("right") or "")
        left_obs = read_observation(conn, left)
        right_obs = read_observation(conn, right)
        obs = [o for o in (left_obs, right_obs) if o]
        lineage = sorted({str(o.get("source_id")) for o in obs if o.get("source_id")})
        lats = [o["latitude"] for o in obs if o.get("latitude") is not None]
        lons = [o["longitude"] for o in obs if o.get("longitude") is not None]
        nbr = ""
        if lats and lons:
            mid_lat = (min(lats) + max(lats)) / 2
            mid_lon = (min(lons) + max(lons)) / 2
            nbr = f"geo:{mid_lat:.2f}:{mid_lon:.2f}"
        rows.append(
            {
                "pair_id": it.item_id,
                "left_ref": left,
                "right_ref": right,
                "stratum_id": stratum_for(it.item_id, it.payload),
                "estimand": "auto_positive_precision",
                "reference_basis": "physical_identity",
                "entity_neighborhood": nbr,
                "source_lineage_ids": lineage,
                "republisher_family": "",
                "mirror_group_id": "",
            }
        )
    return rows


def preregister_campaign(
    conn: Any,
    *,
    campaign_id: str,
    purpose: str,
    protocol_digest: str,
    frame_snapshot: str,
    ruleset_digest: str,
    seed: str,
    design: Mapping[str, Any],
    created_by: str,
    role: str | None = _ADMIN,
) -> dict[str, Any]:
    """Insert the immutable campaign row. Refuses a different design under a
    taken id (ON CONFLICT DO NOTHING + post-check) — the design is frozen at
    preregistration, a changed design means a NEW campaign."""
    _connect(conn, role)
    with conn.transaction():
        conn.execute(
            _INSERT_CAMPAIGN,
            (
                campaign_id,
                purpose,
                protocol_digest,
                frame_snapshot,
                ruleset_digest,
                seed,
                json.dumps(design, sort_keys=True),
                created_by,
            ),
        )
    row = conn.execute(
        "SELECT purpose, design FROM human_eval_campaign WHERE campaign_id = %s",
        (campaign_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"campaign {campaign_id!r} insert did not persist")
    if row[0] != purpose or row[1] != dict(design):
        raise ValueError(
            f"campaign id {campaign_id!r} is already taken by a different design "
            "— a changed design needs a NEW campaign id (preregistration is immutable)"
        )
    return {"campaign_id": campaign_id, "inserted": True}


def write_samples(
    conn: Any,
    sample_rows: Sequence[Mapping[str, Any]],
    *,
    role: str | None = _ADMIN,
) -> int:
    """Append the drawn sample rows (idempotent under the PK)."""
    _connect(conn, role)
    n = 0
    with conn.transaction():
        for r in sample_rows:
            conn.execute(
                _INSERT_SAMPLE,
                (
                    r["campaign_id"],
                    r["sample_id"],
                    r["pair_id"],
                    r["left_ref"],
                    r["right_ref"],
                    r.get("packet_digest"),
                    r["partition"],
                    r["estimand"],
                    r["stratum_id"],
                    r["dependency_group_id"],
                    list(r.get("source_lineage_ids") or []),
                    r["selection_probability"],
                    r.get("weight"),
                    r["draw_order"],
                    r["reference_basis"],
                ),
            )
            n += 1
    return n


def write_manifest(
    conn: Any,
    *,
    campaign_id: str,
    sample_rows: Sequence[Mapping[str, Any]],
    denominators: Mapping[str, Any],
    created_by: str,
    role: str | None = _ADMIN,
) -> dict[str, Any]:
    """Record the manifest row: digest over campaign + membership + the
    persisted denominators (the population each selection_probability drew
    against). One row per campaign — ON CONFLICT DO NOTHING + equality check
    makes re-materializing the same draw idempotent."""
    _connect(conn, role)
    campaign = _read_campaign(conn, campaign_id)
    m_digest = manifest_digest(campaign, sample_rows)
    mem_digest = membership_digest(sample_rows)
    with conn.transaction():
        conn.execute(
            _INSERT_MANIFEST,
            (
                campaign_id,
                m_digest,
                mem_digest,
                len(sample_rows),
                json.dumps(denominators, sort_keys=True),
                created_by,
            ),
        )
    existing = conn.execute(
        "SELECT manifest_digest, membership_digest, sample_count "
        "FROM human_eval_manifest WHERE campaign_id = %s",
        (campaign_id,),
    ).fetchone()
    if existing is None or existing[0] != m_digest:
        raise ValueError(
            f"manifest for {campaign_id!r} does not match this draw "
            f"(stored={existing[0] if existing else None}, computed={m_digest}) — "
            "a different sample under the same id is refused"
        )
    return {
        "campaign_id": campaign_id,
        "manifest_digest": m_digest,
        "membership_digest": mem_digest,
        "sample_count": len(sample_rows),
    }


def _read_campaign(conn: Any, campaign_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT campaign_id, purpose, design, seed FROM human_eval_campaign WHERE campaign_id = %s",
        (campaign_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"no such human-eval campaign {campaign_id!r}")
    return {"campaign_id": row[0], "purpose": row[1], "design": row[2], "seed": row[3]}


def read_campaign(conn: Any, campaign_id: str, *, role: str | None = _ADMIN) -> dict[str, Any]:
    """The campaign row (design + seed) under the given role."""
    _connect(conn, role)
    return _read_campaign(conn, campaign_id)


def read_samples(conn: Any, campaign_id: str, *, role: str | None = _ADMIN) -> list[dict[str, Any]]:
    """The campaign's sample rows under the given role (admin/custodian)."""
    _connect(conn, role)
    return _read_samples(conn, campaign_id)


def _read_samples(conn: Any, campaign_id: str) -> list[dict[str, Any]]:
    cols = (
        "sample_id, pair_id, left_ref, right_ref, partition, estimand,"
        " stratum_id, dependency_group_id, source_lineage_ids,"
        " selection_probability, weight, draw_order, reference_basis,"
        " packet_digest"
    )
    rows = conn.execute(
        f"SELECT {cols} FROM human_eval_sample WHERE campaign_id = %s ORDER BY draw_order",
        (campaign_id,),
    ).fetchall()
    out = []
    for r in rows:
        out.append(
            {
                "sample_id": r[0],
                "pair_id": r[1],
                "left_ref": r[2],
                "right_ref": r[3],
                "partition": r[4],
                "estimand": r[5],
                "stratum_id": r[6],
                "dependency_group_id": r[7],
                "source_lineage_ids": list(r[8] or []),
                "selection_probability": r[9],
                "weight": r[10],
                "draw_order": r[11],
                "reference_basis": r[12],
                "packet_digest": r[13],
            }
        )
    return out


def verify_manifest(
    conn: Any,
    campaign_id: str,
    *,
    role: str | None = _ADMIN,
) -> dict[str, Any]:
    """Recompute the manifest digest over live rows; report match/mismatch.

    ``verified=False`` means a sample/design/manifest field changed after
    preregistration (or the manifest was never written) — the campaign must be
    treated as tampered, never silently accepted.
    """
    _connect(conn, role)
    campaign = _read_campaign(conn, campaign_id)
    samples = _read_samples(conn, campaign_id)
    stored = conn.execute(
        "SELECT manifest_digest, membership_digest, sample_count, denominators "
        "FROM human_eval_manifest WHERE campaign_id = %s",
        (campaign_id,),
    ).fetchone()
    computed = manifest_digest(campaign, samples)
    computed_membership = membership_digest(samples)
    ok = (
        stored is not None
        and stored[0] == computed
        and stored[1] == computed_membership
        and stored[2] == len(samples)
    )
    return {
        "campaign_id": campaign_id,
        "verified": bool(ok),
        "computed_manifest_digest": computed,
        "computed_membership_digest": computed_membership,
        "stored_manifest_digest": stored[0] if stored else None,
        "denominators": stored[3] if stored else None,
    }


def write_packets(
    conn: Any,
    packets: Sequence[Mapping[str, Any]],
    *,
    role: str | None = _ADMIN,
) -> int:
    """Persist blinded packets (the reviewer-facing payloads).

    ``packets`` rows carry ``campaign_id``, ``sample_id`` and the blinded
    ``payload``; the digest is computed and stored on the packet row here.
    The packet table is the authority a label's ``packet_digest`` is checked
    against — sample rows are immutable, so a packet payload can never be
    silently replaced either (the PK + conflict-noop keeps re-runs +0).
    """
    _connect(conn, role)
    n = 0
    with conn.transaction():
        for p in packets:
            digest = packet_digest(p["payload"])
            conn.execute(
                _INSERT_PACKET,
                (
                    p["campaign_id"],
                    p["sample_id"],
                    digest,
                    json.dumps(p["payload"], sort_keys=True),
                ),
            )
            n += 1
    return n


def assign_reviewers(
    conn: Any,
    *,
    campaign_id: str,
    reviewer_id: str,
    sample_ids: Sequence[str],
    pass_no: int,
    assigned_by: str,
    role: str | None = _ADMIN,
) -> int:
    """Append reviewer × sample × pass assignments (idempotent)."""
    if pass_no not in (1, 2):
        raise ValueError("pass_no must be 1 or 2 (two independent first passes)")
    _connect(conn, role)
    n = 0
    with conn.transaction():
        for sid in sample_ids:
            conn.execute(
                _INSERT_ASSIGNMENT,
                (campaign_id, sid, reviewer_id, pass_no, assigned_by),
            )
            n += 1
    return n


def record_attestation(
    conn: Any,
    *,
    campaign_id: str | None,
    reviewer_id: str,
    kind: str,
    detail: Mapping[str, Any],
    recorded_by: str,
    role: str | None = _ADMIN,
) -> str:
    """Append a human-attestation event; return its attestation_id."""
    _connect(conn, role)
    row = conn.execute(
        _INSERT_ATTESTATION,
        (campaign_id, reviewer_id, kind, json.dumps(detail, sort_keys=True), recorded_by),
    ).fetchone()
    return str(row[0])


def _require_attestation(conn: Any, attestation_id: str, reviewer_id: str) -> None:
    row = conn.execute(
        "SELECT reviewer_id, kind FROM human_eval_attestation WHERE attestation_id = %s",
        (attestation_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"no such attestation {attestation_id!r}")
    if row[0] != reviewer_id:
        raise ValueError(
            f"attestation {attestation_id!r} belongs to reviewer {row[0]!r}, not {reviewer_id!r}"
        )
    if row[1] != "human_identity":
        raise ValueError(
            f"attestation {attestation_id!r} is kind {row[1]!r}; a label requires "
            "a 'human_identity' attestation (agents cannot impersonate reviewers)"
        )


def record_label(
    conn: Any,
    *,
    campaign_id: str,
    sample_id: str,
    reviewer_id: str,
    round: str,
    label: str,
    reason_codes: Sequence[str],
    evidence_refs: Sequence[Mapping[str, Any]],
    rubric_version: str,
    packet_digest: str,
    attestation_id: str,
    label_digest: str,
    supersedes_label_id: str | None = None,
    role: str | None = _REVIEWER,
) -> str:
    """Append one independent reference label as the reviewer role.

    Runs under ``sig_eval_reviewer`` with the ``sig.eval_reviewer`` GUC set to
    this reviewer: the label table's RLS ``WITH CHECK`` refuses the insert if
    the row's ``reviewer_id`` is anyone else's, so one reviewer can never
    write (or overwrite) another's label. The packet digest is verified
    against the current packet — labeling a superseded/stale packet version
    is refused. ``supersedes_label_id`` links an append-only correction; the
    superseded row stays.
    """
    from .human_eval import REFERENCE_LABELS

    if label not in REFERENCE_LABELS:
        raise ValueError(f"label must be one of {REFERENCE_LABELS}, got {label!r}")
    _connect(conn, role)
    with conn.transaction():
        conn.execute("SELECT set_config('sig.eval_reviewer', %s, true)", (reviewer_id,))
        _require_attestation(conn, attestation_id, reviewer_id)
        pkt = conn.execute(
            "SELECT packet_digest FROM human_eval_packet WHERE campaign_id = %s AND sample_id = %s",
            (campaign_id, sample_id),
        ).fetchone()
        if pkt is None:
            raise ValueError(
                f"no packet visible for {campaign_id}/{sample_id} under this "
                "session — a reviewer can label only packets the campaign "
                "assigned to them (packet RLS enforces the assignment)"
            )
        if pkt[0] != packet_digest:
            raise ValueError(
                f"packet digest mismatch for {sample_id}: labeling against "
                f"{packet_digest} but the current packet is {pkt[0]} — a stale packet "
                "cannot be labeled"
            )
        row = conn.execute(
            _INSERT_LABEL,
            (
                campaign_id,
                sample_id,
                reviewer_id,
                round,
                label,
                list(reason_codes),
                json.dumps(list(evidence_refs), sort_keys=True),
                rubric_version,
                packet_digest,
                attestation_id,
                supersedes_label_id,
                label_digest,
            ),
        ).fetchone()
    return str(row[0])


def record_adjudication(
    conn: Any,
    *,
    campaign_id: str,
    sample_id: str,
    adjudicator_id: str,
    phase: str,
    label: str,
    reason: str,
    evidence_refs: Sequence[Mapping[str, Any]],
    supersedes_adjudication_id: str | None = None,
    role: str | None = _CUSTODIAN,
) -> str:
    """Append an adjudication under the sealing-authority role."""
    _connect(conn, role)
    row = conn.execute(
        _INSERT_ADJUDICATION,
        (
            campaign_id,
            sample_id,
            adjudicator_id,
            phase,
            label,
            reason,
            json.dumps(list(evidence_refs), sort_keys=True),
            supersedes_adjudication_id,
        ),
    ).fetchone()
    return str(row[0])


def record_release(
    conn: Any,
    *,
    campaign_id: str,
    scope: str,
    authorized_by: str,
    detail: Mapping[str, Any],
    role: str | None = _CUSTODIAN,
) -> str | None:
    """Record the authorized unsealing decision (one row per campaign+scope).

    Until this row exists, sealed_final labels/adjudications are invisible to
    every model-development and operational surface. ``scope`` names the
    permitted use ('final' evaluation readout, 'operational' promotion to
    clustering, 'development_only').
    """
    _connect(conn, role)
    row = conn.execute(
        _INSERT_RELEASE,
        (campaign_id, scope, authorized_by, json.dumps(detail, sort_keys=True)),
    ).fetchone()
    return str(row[0]) if row else None


def campaign_status(conn: Any, campaign_id: str, *, role: str | None = _ADMIN) -> dict[str, Any]:
    """Counts by partition + the released label/adjudication counts.

    Under ``sig_eval_admin`` the counts come from the *released* views —
    sealed_final rows do not exist for the model-development surface until an
    authorized release. Under the custodian the raw counts include them.
    """
    _connect(conn, role)
    parts = dict(
        conn.execute(
            "SELECT partition, count(*) FROM human_eval_sample "
            "WHERE campaign_id = %s GROUP BY partition",
            (campaign_id,),
        ).fetchall()
    )
    label_view = "human_eval_label" if role == _CUSTODIAN else "human_eval_label_released"
    adj_view = (
        "human_eval_adjudication" if role == _CUSTODIAN else "human_eval_adjudication_released"
    )
    labels = conn.execute(
        f"SELECT count(*) FROM {label_view} WHERE campaign_id = %s", (campaign_id,)
    ).fetchone()[0]
    adj = conn.execute(
        f"SELECT count(*) FROM {adj_view} WHERE campaign_id = %s", (campaign_id,)
    ).fetchone()[0]
    released = False
    if role == _CUSTODIAN:
        released = bool(
            conn.execute(
                "SELECT count(*) FROM human_eval_release WHERE campaign_id = %s",
                (campaign_id,),
            ).fetchone()[0]
        )
    from .human_eval import campaign_state

    return {
        "campaign_id": campaign_id,
        "state": campaign_state(label_count=labels, adjudication_count=adj, released=released),
        "samples_by_partition": parts,
        "labels_visible_to_role": labels,
        "adjudications_visible_to_role": adj,
        "release_recorded": released if role == _CUSTODIAN else None,
    }


def export_workbook(
    conn: Any,
    *,
    campaign_id: str,
    reviewer_id: str,
    pass_no: int = 1,
    role: str | None = _ADMIN,
) -> list[dict[str, Any]]:
    """The blinded labeling workbook for ONE reviewer (JSON-able rows).

    Emits only that reviewer's assigned samples and only the blinded packet
    payload — never the sample table's stratum/partition/probability fields,
    never another reviewer's labels, never model artifacts. Each row carries
    the packet digest the label must cite.
    """
    from .human_eval import assert_blinded

    _connect(conn, role)
    rows = conn.execute(
        "SELECT a.sample_id, p.packet_digest, p.payload "
        "FROM human_eval_assignment a "
        "JOIN human_eval_packet p ON p.campaign_id = a.campaign_id "
        "  AND p.sample_id = a.sample_id "
        "WHERE a.campaign_id = %s AND a.reviewer_id = %s AND a.pass_no = %s "
        "ORDER BY a.sample_id",
        (campaign_id, reviewer_id, pass_no),
    ).fetchall()
    out = []
    for sid, digest, payload in rows:
        assert_blinded(payload)
        out.append(
            {
                "sample_id": sid,
                "packet_digest": digest,
                "packet": payload,
                "label": None,
                "reason_codes": [],
                "evidence_refs": [],
                "rubric_version": None,
            }
        )
    return out


def campaign_watermark(conn: Any, campaign_id: str, *, role: str | None = _CUSTODIAN) -> str:
    """The chained label watermark over the campaign's labels in append order."""
    _connect(conn, role)
    rows = conn.execute(
        "SELECT label_digest FROM human_eval_label WHERE campaign_id = %s ORDER BY label_seq",
        (campaign_id,),
    ).fetchall()
    return label_watermark([{"label_digest": r[0]} for r in rows])


# ---------------------------------------------------------------------------
# P32.10 — evaluation materialization + the shadow gate readout (SIG-EVAL-003/4)
# ---------------------------------------------------------------------------
def _current_labels(
    conn: Any, campaign_id: str
) -> dict[str, dict[tuple[str, str], dict[str, Any]]]:
    """The chain-tip label per (sample, reviewer, round), read through the
    RELEASED view — sealed_final labels are absent until an authorized
    release row exists; absence is the seal, not a lookup."""
    rows = conn.execute(
        "SELECT sample_id, reviewer_id, label_round, label, packet_digest,"
        " label_seq FROM human_eval_label_released WHERE campaign_id = %s",
        (campaign_id,),
    ).fetchall()
    current: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    for sid, reviewer, rnd, label, pkt, seq in rows:
        per_sample = current.setdefault(sid, {})
        key = (str(reviewer), str(rnd))
        if key not in per_sample or per_sample[key]["label_seq"] < seq:
            per_sample[key] = {"label": label, "packet_digest": pkt, "label_seq": seq}
    return current


def _current_adjudications(conn: Any, campaign_id: str) -> dict[str, dict[str, Any]]:
    """The chain-tip adjudication per sample (released view; the superseded
    rows stay but only the highest seq is current)."""
    rows = conn.execute(
        "SELECT sample_id, label, adjudication_seq FROM human_eval_adjudication_released "
        "WHERE campaign_id = %s",
        (campaign_id,),
    ).fetchall()
    current: dict[str, dict[str, Any]] = {}
    for sid, label, seq in rows:
        if sid not in current or current[sid]["seq"] < seq:
            current[sid] = {"label": label, "seq": seq}
    return current


def _release_scopes(conn: Any, campaign_id: str) -> tuple[str, ...] | None:
    """The recorded release scopes, or ``None`` when the role cannot read the
    release table (unknown is handled by the evaluator, never assumed)."""
    try:
        rows = conn.execute(
            "SELECT scope FROM human_eval_release WHERE campaign_id = %s",
            (campaign_id,),
        ).fetchall()
    except Exception:
        return None
    return tuple(sorted(str(r[0]) for r in rows))


def eval_units_from_campaign(
    conn: Any,
    campaign_id: str,
    *,
    tier_of_pair: Mapping[str, int] | None = None,
    scope_of_pair: Mapping[str, str] | None = None,
    role: str | None = _ADMIN,
) -> dict[str, Any]:
    """Materialize :class:`resolution.evaluator.EvalUnit` rows for a campaign.

    The outcome per sample is resolved from the *released* label and
    adjudication surfaces ONLY — a sealed_final unit whose labels are still
    sealed materializes ``sealed=True, outcome='missing'`` and stays in every
    strict denominator:

    * the current adjudication wins when one exists
      (``unresolved`` stays ``unresolved``);
    * else the two independent labels per ``human_eval.consensus``: two equal
      definite judgments give the label; any disagreement, any
      ``insufficient_evidence``, or a single in-flight label gives
      ``unresolved`` (it proceeds to adjudication — never guessed);
    * else ``missing``.

    ``packet_ok`` is False when the label's recorded ``packet_digest`` differs
    from the sample's current packet digest — a stale-packet label can never
    certify. ``tier_of_pair``/``scope_of_pair`` map the frozen candidate's
    auto-tier (and hypothesis scope) onto ``pair_id``; pairs absent from the
    map keep ``tier=None`` (reported in the estimand rows, matched to no gate).
    """
    from .evaluator import EvalUnit
    from .human_eval import consensus

    _connect(conn, role)
    samples = _read_samples(conn, campaign_id)
    labels = _current_labels(conn, campaign_id)
    adjudications = _current_adjudications(conn, campaign_id)
    scopes = _release_scopes(conn, campaign_id)
    pkt_rows = conn.execute(
        "SELECT sample_id, packet_digest FROM human_eval_packet WHERE campaign_id = %s",
        (campaign_id,),
    ).fetchall()
    packet_digests = {str(r[0]): str(r[1]) for r in pkt_rows}

    units: list[EvalUnit] = []
    for s in samples:
        sid = str(s["sample_id"])
        sealed_final = s["partition"] == "sealed_final"
        adj = adjudications.get(sid)
        current = labels.get(sid, {})
        outcome = "missing"
        packet_ok = True
        if adj is not None:
            outcome = (
                "insufficient_evidence"
                if adj["label"] == "insufficient_evidence"
                else str(adj["label"])
            )
        elif current:
            cons = consensus([v["label"] for v in current.values()])
            # Two equal definite judgments give the label; an in-flight
            # single label, a disagreement, or any insufficient_evidence is
            # unresolved until adjudication — never guessed.
            outcome = cons if cons in ("same", "different") else "unresolved"
            pkt = packet_digests.get(sid)
            if pkt and any(v["packet_digest"] != pkt for v in current.values()):
                packet_ok = False
        sealed = sealed_final and outcome == "missing"
        pair_id = str(s["pair_id"])
        units.append(
            EvalUnit(
                sample_id=sid,
                estimand=str(s["estimand"]),
                stratum_id=str(s["stratum_id"]),
                partition=str(s["partition"]),
                dependency_group_id=str(s["dependency_group_id"]),
                outcome=outcome,
                reference_provenance="human",
                tier=(tier_of_pair or {}).get(pair_id),
                scope=(scope_of_pair or {}).get(pair_id, "snapshot"),
                weight=float(s["weight"]) if s.get("weight") is not None else None,
                selection_probability=float(s["selection_probability"]),
                sealed=sealed,
                packet_ok=packet_ok,
            )
        )
    return {
        "campaign_id": campaign_id,
        "units": units,
        "release_scopes": scopes,
    }


def run_shadow_evaluation(
    conn: Any,
    campaign_id: str,
    *,
    design: Any,
    tier_of_pair: Mapping[str, int] | None = None,
    scope_of_pair: Mapping[str, str] | None = None,
    historical: Sequence[Any] = (),
    role: str | None = _ADMIN,
) -> Any:
    """Materialize the campaign's released-label units and run the shadow
    evaluation — the report-only confidence gate (P32.10).

    ``design`` is the preregistered :class:`SamplingDesign` (it MUST match the
    campaign's frozen design digests — the caller constructs it from the
    preregistration record). ``manifest_verified`` is recomputed live here;
    contamination/candidate-digest checks are caller inputs the offline
    runner wires when the frozen artifacts are present. Nothing is applied:
    the returned :class:`EvaluationReport` carries recommendations only.
    """
    from .evaluator import evaluate

    mat = eval_units_from_campaign(
        conn, campaign_id, tier_of_pair=tier_of_pair, scope_of_pair=scope_of_pair, role=role
    )
    verification = verify_manifest(conn, campaign_id, role=role)
    return evaluate(
        units=mat["units"],
        design=design,
        manifest_verified=bool(verification["verified"]),
        release_scopes=mat["release_scopes"] or (),
        historical=tuple(historical),
        notes=(
            f"manifest digest: {verification['computed_manifest_digest']}",
            f"campaign {campaign_id} materialized from released views only",
        ),
    )
