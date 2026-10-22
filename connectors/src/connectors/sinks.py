# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The claim-sink factory the connector runner selects a write target through (§16).

A connector run threads a :class:`connectors.stages.ClaimSink` on its
:class:`~connectors.stages.RunContext`; ``load()`` asserts the run's claims into
it on a live run only (never on replay/shadow). Two sinks exist:

* the in-memory default (``InMemoryClaimSink``) — the test/replay target, and
* the PostgreSQL spine (``db.claim_sink.PgClaimSink``) — the production target
  wired in P19.4, selected with ``--sink pg --dsn …``.

The ``connectors`` package must not depend on the psycopg driver directly (that
belongs to the ``db`` package, which owns the physical store); this factory keeps
that boundary by delegating connection-opening to
:meth:`db.claim_sink.PgClaimSink.from_dsn`. ``import connectors`` therefore never
pulls in psycopg unless a PG sink is actually requested at runtime.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any

from .stages import ClaimSink, InMemoryClaimSink

#: The sink kinds the runner accepts (``--sink``).
SINK_KINDS = ("memory", "pg")

#: Env var the ops/CLI composition roots read for the PG sink's per-transaction
#: claim commit size (P26.18 / SOURCES.17). The chunk size is operator config,
#: not code: hosted jobs set it on the job env; unset ⇒ the ``db.claim_sink``
#: module default (ordinary sources commit in a single chunk, unchanged).
ENV_COMMIT_CHUNK_SIZE = "SIG_COMMIT_CHUNK_SIZE"


def _registry_rights(source_id: str) -> Mapping[str, Any] | None:
    """The source's registry rights tuple, normalized to the spine vocabulary.

    P34.21a / ADR-194: the ``rights_resolver`` wired onto the live
    :class:`db.claim_sink.PgClaimSink` so a claim that omits rights fields
    records the source's *own* reviewed (spdx, attribution, terms) — never an
    empty or cross-source record (F-387). Claim-carried fields always win; this
    only fills the gaps. An unregistered source resolves ``None`` and the claim
    stands on its own fields (the loader gate has already decided it may run).
    """
    from .registry import get

    try:
        record = get(source_id)
    except KeyError:
        return None
    rights = record.rights
    # A recorded rights review (role + date) distinguishes "reviewed, not
    # publishable" ('no') from "not yet reviewed" (UNDETERMINED) — the
    # registry's `redistributable = false` default conflates the two. An
    # unreviewed source keeps the honest undecided marker so a decision can
    # lift it later; stamping 'no' would record a review that never happened.
    reviewed = bool(record.rights_reviewed_by and record.rights_reviewed_on)
    if rights.spdx == "UNDETERMINED":
        redistributable = "UNDETERMINED"
    elif rights.redistributable:
        redistributable = "yes"
    else:
        redistributable = "no" if reviewed else "UNDETERMINED"
    if rights.spdx == "UNDETERMINED":
        derivative = "UNDETERMINED"
    elif rights.derivative_permitted:
        derivative = "yes"
    else:
        derivative = "no" if reviewed else "UNDETERMINED"
    return {
        "spdx": rights.spdx,
        "attribution": rights.attribution,
        "terms_url": rights.terms_url,
        "redistributable": redistributable,
        "derivative_permitted": derivative,
    }


def _registry_lane(source_id: str) -> Mapping[str, Any] | None:
    """The source's redistribution-lane evidence (P35.31 + row 313 / F-400).

    The capture writer's ``storage_tier`` derivation consumes the recorded
    ``[redistribution]`` lane where the registry row declares one (row 313's
    fields — ``lane``, ``part_viii_class``, ``packet_limited``,
    ``sig_labelled_cc0``, and the verdict's evidence/decision fields the
    ``source_redistribution`` mirror stores); the interim basis — the rights
    record fields ``policy.transparency.interim_lane`` reads — remains the
    fallback for an undeclared block, and never reaches ``public``. A
    declined compact is the recorded refusal R-1 names; an unregistered
    source resolves ``None`` — the writer then derives ``sealed``, never
    ``public`` by default.
    """
    from .registry import CompactStatus, get

    try:
        record = get(source_id)
    except KeyError:
        return None
    rights = record.rights
    # Same normalization as ``_registry_rights``: the registry's
    # ``redistributable = false`` default conflates "reviewed, not
    # publishable" with "not yet reviewed" — an unreviewed source keeps the
    # honest undecided marker so the lane derives ``unknown``, never a
    # recorded refusal.
    reviewed = bool(record.rights_reviewed_by and record.rights_reviewed_on)
    if rights.spdx == "UNDETERMINED":
        redistributable = "UNDETERMINED"
    elif rights.redistributable:
        redistributable = "yes"
    else:
        redistributable = "no" if reviewed else "UNDETERMINED"
    fields: dict[str, Any] = {
        "custody_posture": record.custody_posture.value,
        "spdx": rights.spdx,
        "redistributable": redistributable,
        "derivative_permitted": rights.derivative_permitted,
        "reviewed": reviewed,
        "refused": record.compact_status == CompactStatus.PERMISSION_DECLINED,
    }
    red = record.redistribution
    if red.lane:
        # The recorded verdict wins over the interim basis: it names the
        # closed-vocabulary lane plus the Part VIII class and packet flags
        # the interim basis could never carry — the raw-ok + P8-clear →
        # public path is ONLY reachable through these recorded fields.
        fields.update(
            {
                "lane": red.lane,
                "part_viii_class": red.part_viii_class,
                "packet_limited": red.packet_limited,
                "sig_labelled_cc0": red.sig_labelled_cc0,
                "lane_evidence": red.evidence,
                "lane_evidence_uri": red.evidence_uri,
                "lane_decision_authority": red.decision_authority,
                "lane_review_needed": red.review_needed,
                "redistribution_version": red.registry_version(),
                "lane_basis": "registry:[redistribution]",
            }
        )
    return fields


def _registry_lineage(source_id: str) -> Any:
    """The source's resolved claim-lineage record (P35.25 / SIG-CONF-014).

    The registry's declared ``[lineage]`` block resolves to the claim's
    ``id_namespace``/``lineage_kind``/``independence_class``; an unregistered
    or undeclared source resolves to the honest defaults (undeclared kind,
    unclassified class — never a guess). ``db.lineage.ClaimLineage`` is the
    row shape; basis names where the values came from.
    """
    from db.lineage import UNCLASSIFIED, UNDECLARED, ClaimLineage, namespace_version

    from .registry import get, registry, resolve_independence_class

    try:
        record = get(source_id)
    except KeyError:
        return ClaimLineage(source_id=source_id)
    lin = record.lineage
    basis = f"registry:sources.toml+{namespace_version()}"
    return ClaimLineage(
        source_id=source_id,
        id_namespace=lin.id_namespace or UNDECLARED,
        lineage_kind=lin.kind.value,
        independence_class=resolve_independence_class(record, registry())
        if lin.kind.value != "undeclared"
        else UNCLASSIFIED,
        basis=basis,
    )


def resolve_commit_chunk_size(
    explicit: int | None = None, env: Mapping[str, str] | None = None
) -> int | None:
    """Resolve the commit chunk size: explicit flag wins, else ``$SIG_COMMIT_CHUNK_SIZE``.

    Returns ``None`` when neither is set, so the sink applies its own default
    (``db.claim_sink.DEFAULT_COMMIT_CHUNK_SIZE``) — the connector layer never
    hard-codes a size. A non-numeric or non-positive env value raises
    ``ValueError`` so a misconfigured job fails loud rather than silently
    ingesting under a wrong bound.
    """
    if explicit is not None:
        return explicit
    raw = (os.environ if env is None else env).get(ENV_COMMIT_CHUNK_SIZE, "").strip()
    if not raw:
        return None
    value = int(raw)
    if value < 1:
        raise ValueError(f"{ENV_COMMIT_CHUNK_SIZE} must be a positive integer (got {raw!r})")
    return value


def make_claim_sink(kind: str = "memory", *, dsn: str | None = None, **kwargs: Any) -> ClaimSink:
    """Build the selected :class:`ClaimSink`.

    ``kind='memory'`` returns an :class:`InMemoryClaimSink` (the default, unchanged
    behaviour). ``kind='pg'`` requires a ``dsn`` and returns a ``PgClaimSink`` bound
    to that database; the psycopg import lives behind this branch so the in-memory
    path has no driver dependency.

    The PG sink is built with the production ``object_resolver``
    (:func:`db.claim_sink.record_object_ref`, P31.5 / ADR-112): an entity-ref claim
    record that a connector's ``link()`` stage emitted is written with its
    ``object_entity``; every other record stays a literal. It also gets the
    production ``on_duplicates`` hook (:func:`db.claim_sink.record_resightings`,
    P31.7 / ADR-R9-RESIGHT): every live re-assertion of a stored claim appends the
    re-sighting's ``claim_evidence`` link to the execution's capture. A caller may
    still pass its own ``object_resolver`` / ``on_duplicates``. (The asserting
    ``replay_ingest`` path builds its ``PgClaimSink`` directly, deliberately
    without the hook — a replay re-reads stored bytes, so it is not a sighting.)
    """
    if kind == "memory":
        return InMemoryClaimSink()
    if kind == "pg":
        if not dsn:
            raise ValueError("the 'pg' claim sink requires a --dsn connection string")
        from db.claim_sink import (  # psycopg stays in `db`
            PgClaimSink,
            record_object_ref,
            record_resightings,
        )

        kwargs.setdefault("object_resolver", record_object_ref)
        kwargs.setdefault("on_duplicates", record_resightings)
        # P34.21a / ADR-194: the live sink resolves rights per SOURCE from the
        # registry (a claim's own fields still win). A caller may pass its own
        # ``rights_resolver``; replay sinks are built directly in runner.py and
        # deliberately carry none — a replay re-records what was asserted.
        kwargs.setdefault("rights_resolver", _registry_rights)
        # P35.25 / SIG-CONF-014: the live sink also resolves declared lineage
        # per source (claim_lineage rows); undeclared stays undeclared — never
        # a guessed class.
        kwargs.setdefault("lineage_resolver", _registry_lineage)
        # P35.31 / NEW-2 (F-400): the live sink derives each capture's
        # ``storage_tier`` from the source's redistribution lane + Part VIII
        # class (interim basis: the registry's rights record). An unknown
        # source derives ``sealed`` — never the old 'public' constant.
        kwargs.setdefault("lane_resolver", _registry_lane)
        return PgClaimSink.from_dsn(dsn, **kwargs)
    raise ValueError(f"unknown claim-sink kind {kind!r}; expected one of {SINK_KINDS}")


__all__ = [
    "ENV_COMMIT_CHUNK_SIZE",
    "SINK_KINDS",
    "make_claim_sink",
    "resolve_commit_chunk_size",
]
