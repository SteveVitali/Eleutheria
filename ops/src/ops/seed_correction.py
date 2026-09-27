# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The authored seed-correction packet for the OKC count claims (P32.18 / S2).

SIG-DOS-003 requires the pre-P32.3 seeded flagship interpretation to be
*corrected, not rewritten*: the spine the early slice wrote holds ambiguous rows
(``claimed_device_count=299`` carrying a ``news_article`` genre,
``claimed_device_count=190`` asserted as a *source claim* when the source only
ever said "businesses own around 100 within city limits", and every count
missing its §29.3 ``count_scope`` universe). P32.3 repaired the *seed fixture*
(ops/seed.py); this module carries the additive **correction packet** that a
reviewed run applies to a spine still holding the legacy rows — the only write
against the claim spine this module performs is the §16.6 transaction-time
belief closure (``sys_period`` upper bound) on each superseded row plus the
append-only insert of each corrected claim with ``revises_claim`` +
``correction_reason``. The old rows are never deleted or mutated.

Packet contract ``sig.seed-correction-packet/1``:

* ``corrections[]`` — one entry per superseded interpretation:
  ``target_record`` (the exact legacy record shape — the spine row is located
  by ``db.claim_sink.content_digest``, never by a guessed id),
  ``replacement_records`` (the corrected connector-shaped records: same
  subject/predicate lineage with the declared ``count_scope`` /
  ``count_scope_detail`` universe and ``evidence_origin=seed_fixture``),
  and ``correction_reason`` (required by the ``claim_correction_reasoned``
  CHECK — §16.6 / SIG-STORE-020).
* ``derived_labels[]`` — the labelled derived sums the packet *authorizes
  readers to compute* (the "~190" city-limits roll-up). A derived sum is L4 /
  never an observation (``reconcile.count_scope.derive_approximate_sum``); the
  packet records it so the dossier can cite the label while no claim ever
  asserts 190 as a source figure.
* ``non_corrections[]`` — rows the review deliberately left alone (the ODbL
  OSM compartment row keeps its own licence compartment).
* ``review.status`` — ``not_run`` on this build: no independent reviewer
  exists (D-R10-HUMAN-1), and the machinery never fabricates one.
* ``status`` — ``prepared``: the packet is authored and reviewable; ``apply``
  reports its own per-correction outcomes, never mutating the packet.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping, Sequence
from typing import Any

from db.claim_sink import SUBJECT_SCHEME, PgClaimSink, content_digest
from reconcile.count_scope import ORIGIN_SEED_FIXTURE, CountScope, derive_approximate_sum

PACKET_SCHEMA = "sig.seed-correction-packet/1"
REPORT_SCHEMA = "sig.seed-correction-report/1"
PACKET_ID = "okc-seed-count-scopes"
PACKET_VERSION = "seed-correction/1"

_DEPLOYMENT = "sig:deployment:okc-okcpd-flock"
_OKC_JURISDICTION = "us.state_abbr:OK"
_APPLY_CONNECTOR = "okc-seed-correction"
_APPLY_COMMIT = "p32.18-seed-correction"

# --------------------------------------------------------------------------- #
# The legacy (pre-P32.3) seed records — the correction targets, verbatim from
# ops.seed._OKC_CLAIMS as shipped by P21.4 (commit parent of 6b97033). The
# spine locates each row by ``content_digest(record)``; ANY drift between the
# recorded target and the stored row fails closed (review fails closed, §3.1).
# --------------------------------------------------------------------------- #

_LEGACY_CLAIMS: tuple[dict[str, Any], ...] = (
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "claimed_device_count",
        "value": 299,
        "raw_value": "299",
        "observed_at": "2026-08-20",
        "source_id": "deflock",
        "spdx": "CC-BY-4.0",
        "attribution": "DeFlock community map",
        "evidence_genre": "news_article",
    },
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "claimed_device_count",
        "value": 190,
        "raw_value": "businesses own around 100 within city limits",
        "observed_at": "2026-08-18",
        "source_id": "bacy",
        "spdx": "CC-BY-4.0",
        "attribution": "OKCPD Chief Bacy, city council 2026-08-18",
        "evidence_genre": "news_article",
    },
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "active_device_count",
        "value": 90,
        "raw_value": "OKCPD has 90 cameras",
        "observed_at": "2026-08-18",
        "source_id": "bacy",
        "spdx": "CC-BY-4.0",
        "attribution": "OKCPD Chief Bacy, city council 2026-08-18",
        "evidence_genre": "official_statement",
    },
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "contracted_device_count",
        "value": 90,
        "raw_value": "90 cameras",
        "observed_at": "2023-01-01",
        "source_id": "okc-contract-c241032",
        "spdx": "CC-BY-4.0",
        "attribution": "OKC Master Agreement C241032",
        "evidence_genre": "contract",
    },
    {
        "subject_id": _DEPLOYMENT,
        "predicate_id": "mapped_device_count",
        "value": 31,
        "raw_value": "31",
        "observed_at": "2026-08-20",
        "source_id": "osm",
        "spdx": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors, ODbL 1.0 (share-alike)",
        "evidence_genre": "community_map",
    },
)


def _scope_qualifiers(scope: str, detail: str | None = None) -> list[dict[str, Any]]:
    qualifiers: list[dict[str, Any]] = [
        {"qualifier_id": "count_scope", "value": scope, "jurisdiction": _OKC_JURISDICTION},
        {"qualifier_id": "evidence_origin", "value": ORIGIN_SEED_FIXTURE},
    ]
    if detail:
        qualifiers.append({"qualifier_id": "count_scope_detail", "value": detail})
    return qualifiers


def _replacement(
    target: Mapping[str, Any],
    *,
    value: Any = None,
    raw_value: str | None = None,
    genre: str | None = None,
    scope: str,
    detail: str | None = None,
    rationale: str,
    directness: str | None = None,
) -> dict[str, Any]:
    """The corrected record: the legacy lineage preserved verbatim except the
    fields the correction owns — the scope universe, the fixture-origin label,
    and (only where the correction says so) the value/genre/directness."""
    record = copy.deepcopy(dict(target))
    record["qualifiers"] = _scope_qualifiers(scope, detail)
    record["assertion_rationale"] = rationale
    if value is not None:
        record["value"] = value
    if raw_value is not None:
        record["raw_value"] = raw_value
    if genre is not None:
        record["evidence_genre"] = genre
    if directness is not None:
        record["claim_directness"] = directness
    return record


#: The legacy record indexes (into _LEGACY_CLAIMS) each correction targets.
_DEFLOCK_299, _BACY_190, _ACTIVE_90, _CONTRACT_90, _OSM_31 = range(5)


def _derived_city_sum() -> Any:
    """The real roll-up — `reconcile.count_scope.derive_approximate_sum` over
    the two disjoint city-limits claims (never a hand-typed integer)."""
    agency = type(
        "Input",
        (),
        {
            "scope": CountScope("city_limits", _OKC_JURISDICTION, "agency_operated"),
            "value": 90,
            "count_basis": "active",
        },
    )()
    private = type(
        "Input",
        (),
        {
            "scope": CountScope("city_limits", _OKC_JURISDICTION, "privately_owned"),
            "value": 100,
            "count_basis": "claimed",
        },
    )()
    return derive_approximate_sum(
        _DEPLOYMENT,
        [agency, private],
        basis="derived_total",
        assumptions=(
            "the two inputs are disjoint city-limits populations — the agency's "
            "operated readers and privately-owned cameras are not double-counted",
            "the ~100 private figure is an approximate journalism statement, so "
            "the sum is approximate, never a measured total",
        ),
        note=(
            "'~190' is a DERIVED approximate city-limits total — 90 agency-"
            "operated + ~100 privately-owned, same scope, same period. It is L4, "
            "never an observation, and never a claim value."
        ),
    )


def correction_packet() -> dict[str, Any]:
    """The reviewed ``sig.seed-correction-packet/1`` artifact (deterministic)."""
    t = _LEGACY_CLAIMS
    corrections = [
        {
            "correction_id": "deflock-299-metro-scope",
            "target_record": t[_DEFLOCK_299],
            "replacement_records": [
                _replacement(
                    t[_DEFLOCK_299],
                    genre="community_map",
                    scope="metro",
                    rationale=(
                        "the DeFlock figure is a community-map observation over the OKC "
                        "METRO — neither a city-limits count nor a news article; the "
                        "correction relabels genre and declares the metro count universe"
                    ),
                )
            ],
            "correction_reason": "scope_unlabelled_genre_misclassified",
            "note": (
                "299 answers 'how many devices across the metro', not 'how many city "
                "readers' — it stays visible as a different-scope count, never a "
                "contradiction of the city figures."
            ),
        },
        {
            "correction_id": "bacy-190-derived-not-sourced",
            "target_record": t[_BACY_190],
            "replacement_records": [
                _replacement(
                    t[_BACY_190],
                    value=100,
                    scope="city_limits",
                    detail="privately_owned",
                    directness="D6",
                    rationale=(
                        "the source asserted 'businesses own around 100 within city "
                        "limits' — ~100 PRIVATELY-OWNED cameras; the 190 the legacy row "
                        "recorded is a derived sum (90 + ~100), never a sourced figure. "
                        "The correction asserts the sourced literal and labels it "
                        "journalism (D6), city-limits scope, private ownership."
                    ),
                )
            ],
            "correction_reason": "derived_sum_recorded_as_source_claim",
            "note": (
                "190 was never an observation; the correction keeps the sourced ~100 "
                "and the packet's derived_labels record the ~190 roll-up explicitly."
            ),
        },
        {
            "correction_id": "bacy-90-active-scope",
            "target_record": t[_ACTIVE_90],
            "replacement_records": [
                _replacement(
                    t[_ACTIVE_90],
                    scope="city_limits",
                    detail="agency_operated",
                    directness="D6",
                    rationale=(
                        "the agency's 90 is an ACTIVE count over city-limits, "
                        "agency-operated readers — declared so it never collapses "
                        "with the city-owned 90 or the metro 299"
                    ),
                )
            ],
            "correction_reason": "scope_unlabelled",
            "note": "90 active ≠ 90 owned ≠ 90 contracted — separate predicates kept separate.",
        },
        {
            "correction_id": "contract-90-scope",
            "target_record": t[_CONTRACT_90],
            "replacement_records": [
                _replacement(
                    t[_CONTRACT_90],
                    scope="city_limits",
                    detail="agency_operated",
                    rationale=(
                        "the contracted unit count declares its universe: contracted "
                        "units are not active sensors and not owned hardware"
                    ),
                )
            ],
            "correction_reason": "scope_unlabelled",
            "note": "",
        },
        {
            "correction_id": "osm-31-metro-scope",
            "target_record": t[_OSM_31],
            "replacement_records": [
                _replacement(
                    t[_OSM_31],
                    scope="metro",
                    rationale=(
                        "the OSM-derived mapped count is a METRO observation; its ODbL "
                        "licence compartment and attribution are preserved verbatim"
                    ),
                )
            ],
            "correction_reason": "scope_unlabelled",
            "note": "ODbL compartment unchanged — the licence boundary is not a count fix.",
        },
    ]
    derived = _derived_city_sum()
    return {
        "schema": PACKET_SCHEMA,
        "packet_id": PACKET_ID,
        "version": PACKET_VERSION,
        "subject": {"deployment": _DEPLOYMENT, "jurisdiction": _OKC_JURISDICTION},
        "status": "prepared",
        "review": {
            "status": "not_run",
            "note": (
                "no independent reviewer exists on this build — D-R10-HUMAN-1 "
                "remains OPEN; nothing here fabricates one"
            ),
        },
        "corrections": corrections,
        "derived_labels": [
            {
                "label_id": "okc-city-limits-total",
                "question": "q3",
                "kind": "derived_approximate_sum",
                "view": derived.as_view(),
                "input_scope_detail": ["agency_operated", "privately_owned"],
                "note": (
                    "the labelled roll-up a reader may compute; never asserted as a "
                    "claim — the spine holds only the two sourced inputs"
                ),
            }
        ],
        "non_corrections": [
            {
                "record": t[_OSM_31],
                "note": (
                    "the ODbL OSM row is corrected ONLY in scope labelling (see "
                    "osm-31-metro-scope); its licence compartment is never moved"
                ),
            }
        ],
        "notes": [
            "additive §16.6 corrections only: each target's belief window closes and a "
            "corrected claim with revises_claim + correction_reason is appended",
            "no target row is deleted or mutated in place; a query before the "
            "correction still returns the legacy values",
            "299 (metro, community map) is never a same-scope contradiction of the "
            "city figures; ~190 is a labelled derived sum, never a claim",
        ],
    }


# --------------------------------------------------------------------------- #
# The apply path — additive §16.6 corrections against a live spine.
# --------------------------------------------------------------------------- #


def _target_digests(corrections: Sequence[Mapping[str, Any]]) -> list[str]:
    return [content_digest(dict(c["target_record"])) for c in corrections]


def _apply_one(conn: Any, sink: PgClaimSink, correction: Mapping[str, Any]) -> dict[str, Any]:
    """Apply one correction entry; idempotent and crash-safe per stage.

    Stage 1 resolves the legacy row by its content digest. Stage 2 closes its
    belief window (the only allowed spine UPDATE — §16.6). Stage 3 appends the
    corrected claims through the ordinary sink path carrying ``revises_claim``
    + ``correction_reason``. Every stage checks before acting so a re-run after
    a mid-way stop converges to the same final state.
    """
    cid = str(correction["correction_id"])
    digest = content_digest(dict(correction["target_record"]))
    rows = conn.execute(
        "SELECT claim_id::text, upper_inf(sys_period) AS open FROM claim WHERE content_digest=%s",
        (digest,),
    ).fetchall()
    replacements = [dict(r) for r in correction["replacement_records"]]
    reason = str(correction["correction_reason"])
    if not rows:
        # No legacy row: either the spine was seeded post-P32.3 (already
        # scope-labelled, nothing to revise) or the slice was never seeded.
        # Do not invent a target — record and skip.
        return {
            "correction_id": cid,
            "outcome": "no_target",
            "target_digest": digest,
        }
    if len(rows) > 1:
        return {
            "correction_id": cid,
            "outcome": "error",
            "detail": f"ambiguous target: {len(rows)} rows match digest {digest[:12]}…",
        }
    claim_id = str(rows[0][0])
    still_open = bool(rows[0][1])
    if still_open:
        # §16.6: close the prior CURRENT belief interval — the only UPDATE the
        # append-only spine permits. The row itself is never deleted.
        conn.execute(
            "UPDATE claim SET sys_period = tstzrange(lower(sys_period), clock_timestamp(), '[)') "
            "WHERE claim_id=%s::uuid AND upper_inf(sys_period)",
            (claim_id,),
        )
    stamped = [{**r, "revises_claim": claim_id, "correction_reason": reason} for r in replacements]
    before = sink.report.inserted
    sink.assert_claims(stamped)
    landed = sink.report.inserted - before
    ids = conn.execute(
        "SELECT claim_id::text FROM claim WHERE revises_claim=%s::uuid", (claim_id,)
    ).fetchall()
    return {
        "correction_id": cid,
        "outcome": "applied" if still_open else "already_applied",
        "target_digest": digest,
        "target_claim_id": claim_id,
        "belief_closed": still_open,
        "replacement_inserted": landed,
        "replacement_claim_ids": [str(r[0]) for r in ids],
    }


def apply_packet(
    dsn: str,
    packet: Mapping[str, Any] | None = None,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Apply ``packet`` against the spine at ``dsn``; return the report.

    ``dry_run`` resolves targets and reports what WOULD change — no writes.
    The packet itself is never mutated: apply state lives in the returned
    ``sig.seed-correction-report/1``.
    """
    import psycopg

    pkt = packet if packet is not None else correction_packet()
    if str(pkt.get("schema")) != PACKET_SCHEMA:
        raise ValueError(f"not a {PACKET_SCHEMA} packet: {pkt.get('schema')!r}")
    corrections = list(pkt.get("corrections") or ())
    report: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "packet_id": pkt.get("packet_id"),
        "dry_run": dry_run,
        "review": dict(pkt.get("review") or {"status": "not_run"}),
        "corrections": [],
        "derived_labels": list(pkt.get("derived_labels") or []),
    }
    if dry_run:
        with psycopg.connect(dsn, autocommit=True) as conn:
            for c in corrections:
                digest = content_digest(dict(c["target_record"]))
                row = conn.execute(
                    "SELECT count(*) AS n, count(*) FILTER (WHERE upper_inf(sys_period)) AS open "
                    "FROM claim WHERE content_digest=%s",
                    (digest,),
                ).fetchone()
                n, open_n = (int(row[0]), int(row[1])) if row else (0, 0)
                report["corrections"].append(
                    {
                        "correction_id": c["correction_id"],
                        "outcome": "would_apply" if open_n else "no_current_target",
                        "target_digest": digest,
                        "matching_rows": n,
                    }
                )
        return report

    with psycopg.connect(dsn, autocommit=True) as conn:
        # The sink binds THIS connection so each correction — §16.6 belief
        # closure + the append-only replacement insert — is ONE transaction
        # (the sink's chunk transaction nests as a savepoint). A mid-apply
        # crash can never leave a closed claim without its replacement.
        sink = PgClaimSink(
            conn,
            connector_name=_APPLY_CONNECTOR,
            connector_version="1.0.0",
            code_commit=_APPLY_COMMIT,
        )
        sink.register_vocabulary(
            (
                ("count_scope", "string"),
                ("count_scope_detail", "string"),
                ("evidence_origin", "string"),
            )
        )
        for c in corrections:
            try:
                with conn.transaction():
                    report["corrections"].append(_apply_one(conn, sink, c))
            except Exception as exc:  # rolled back above; record, never hide
                report["corrections"].append(
                    {
                        "correction_id": str(c.get("correction_id")),
                        "outcome": "error",
                        "detail": f"{type(exc).__name__}: {exc}",
                    }
                )
                # The sink's caches may hold ids the rollback undid — a fresh
                # sink over the same connection cannot reuse them.
                sink = PgClaimSink(
                    conn,
                    connector_name=_APPLY_CONNECTOR,
                    connector_version="1.0.0",
                    code_commit=_APPLY_COMMIT,
                )
    report["sink"] = {
        "inserted": sink.report.inserted,
        "duplicates": sink.report.duplicates,
        "quarantined": sink.report.quarantined,
    }
    return report


def render_packet_json(packet: Mapping[str, Any]) -> bytes:
    """Deterministic packet JSON (indented + sorted — committed-artifact form)."""
    return (json.dumps(packet, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


__all__ = [
    "PACKET_SCHEMA",
    "REPORT_SCHEMA",
    "PACKET_ID",
    "apply_packet",
    "correction_packet",
    "render_packet_json",
    "SUBJECT_SCHEME",
]
