# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The entity-identity guard: one entity per identity-bearing ``(scheme, value)``.

P31.3 / ADR-110 (closes D-P30.4-3, formerly ENTITY-RACE-01). Before this, the claim
sink resolved a subject by *check, then insert* on ``entity_identifier``. Two
concurrent sinks could both miss the check and both mint an entity. The guard is
the ``entity_identity_key`` side table (sqitch change ``entity_identity_key``).
Its primary key ``(scheme, value)`` is the uniqueness the database enforces:

0. **Read** the keys that already exist. This is one statement, and for a replay it
   is the only one.
1. **Claim the key** for every value that is still unkeyed, with
   ``ON CONFLICT DO NOTHING``. The keys go in one global ``(scheme, value)`` order,
   so two writers never deadlock on each other's keys. The key points at the
   earliest existing entity that already carries the identifier (a row an unguarded
   writer left behind). If there is none, it gets a fresh ``uuidv7()``. A concurrent
   writer's uncommitted key blocks this insert until that writer's transaction ends.
   Once it commits, this insert does nothing.
2. **Mint** an entity only for the keys this call won with a fresh id.
3. **Identify** the entity with its ``entity_identifier`` row (the read surface).
4. **Read back** the keys that were unkeyed. This is a new statement, so under READ
   COMMITTED it sees the keys concurrent writers committed while step 1 waited.

The entity FK on the key is ``DEFERRABLE INITIALLY DEFERRED``: the key is claimed
before its entity exists, inside one transaction. So a writer that loses a race
never leaves an orphan entity behind. **Call this inside a transaction** (the
sink's chunk transaction) at the default READ COMMITTED isolation.

Only identity-bearing schemes go through the guard: ``sig.connector.subject`` and,
since P31.5 (ADR-112), the partner-organisation schemes. Attribute-like schemes such as
``us.state`` or ``fr.insee`` are shared by many entities on purpose and are
**not** keyed (ADR-110).

Append-only: this module only ``INSERT``s and ``SELECT``s.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

#: The identifier scheme the claim sink keys connector subjects on.
SUBJECT_SCHEME = "sig.connector.subject"

#: The partner-organisation identity schemes (P31.5 / ADR-112). ``sig.org.name`` is
#: the normalized-name identifier (``resolution.normalize.normalize_org_name``); the
#: rest are external crosswalk ids that name exactly one organisation. FIPS is left
#: out on purpose: a place code is shared by every body in that place (the county
#: government and its sheriff), so it is an attribute scheme like ``us.state``.
PARTNER_NAME_SCHEME = "sig.org.name"
PARTNER_ORG_SCHEMES = frozenset(
    {
        PARTNER_NAME_SCHEME,
        "gleif.lei",
        "us.sam.uei",
        "dnb.duns",
        "us.dla.cage",
        "us.cgac.agency_code",
    }
)

#: The identity-bearing schemes the guard keys. The backfill in the sqitch changes
#: keys exactly these (``entity_identity_key`` the subjects, ``partner_org_identity_key``
#: the partner organisations). A new scheme joins by a code change here, plus a
#: backfill of its existing identifiers. The guard refuses any other scheme, so an
#: attribute scheme (``us.state``) can never be keyed by mistake.
GUARDED_SCHEMES = frozenset({SUBJECT_SCHEME} | PARTNER_ORG_SCHEMES)

Key = tuple[str, str]  # (scheme, value)


@dataclass(frozen=True)
class IdentityBatch:
    """What :func:`resolve_identity_batch` returned, keyed by ``(scheme, value)``."""

    entity_by_key: dict[Key, str]
    #: The keys this call minted a NEW entity for (it won the key with a fresh id).
    minted: frozenset[Key]
    #: The keys this call claimed for an entity that already existed (an identifier
    #: an unguarded writer left behind).
    adopted: frozenset[Key]


@dataclass(frozen=True)
class IdentityResolution:
    """What :func:`resolve_identities` returned for one ``(scheme, values)`` call."""

    entity_by_value: dict[str, str]
    minted: frozenset[str]
    adopted: frozenset[str]


# Every statement joins against unnest(...) rather than testing `= ANY(array)`. Under
# a generic (prepared) plan, `= ANY` over a parameter array is a linear search per
# row, and over entity_identifier that is minutes per chunk. A join can hash.
_READ_KEYS = (
    "SELECT k.scheme, k.value, k.entity_id FROM entity_identity_key k "
    "JOIN unnest(%s::text[], %s::text[]) AS w(scheme, value) "
    "  ON k.scheme = w.scheme AND k.value = w.value"
)

# Keys in (scheme, value) order, so two writers never wait on each other in a
# cycle. The legacy lookup adopts the earliest entity an unguarded writer already
# identified with the value (the same rule the backfill used).
_CLAIM_KEYS = (
    "INSERT INTO entity_identity_key (scheme, value, entity_id) "
    "SELECT w.scheme, w.value, COALESCE(legacy.entity_id, uuidv7()) "
    "  FROM unnest(%(schemes)s::text[], %(values)s::text[]) AS w(scheme, value) "
    "  LEFT JOIN ("
    "    SELECT DISTINCT ON (ei.scheme, ei.value) ei.scheme, ei.value, ei.entity_id "
    "      FROM entity_identifier ei "
    "      JOIN unnest(%(schemes)s::text[], %(values)s::text[]) AS u(scheme, value) "
    "        ON ei.scheme = u.scheme AND ei.value = u.value "
    "      JOIN entity e ON e.entity_id = ei.entity_id "
    "     ORDER BY ei.scheme, ei.value, e.created_at, ei.entity_id"
    "  ) AS legacy ON legacy.scheme = w.scheme AND legacy.value = w.value "
    " ORDER BY w.scheme, w.value "
    "ON CONFLICT (scheme, value) DO NOTHING "
    "RETURNING scheme, value, entity_id"
)

_MINT = (
    "INSERT INTO entity (entity_id, entity_type) "
    "SELECT m.id::uuid, m.entity_type FROM unnest(%s::text[], %s::text[]) AS m(id, entity_type) "
    " WHERE NOT EXISTS (SELECT 1 FROM entity e WHERE e.entity_id = m.id::uuid) "
    "RETURNING entity_id"
)

_IDENTIFY = (
    "INSERT INTO entity_identifier (entity_id, scheme, value) "
    "SELECT k.id::uuid, k.scheme, k.value "
    "  FROM unnest(%s::text[], %s::text[], %s::text[]) AS k(id, scheme, value) "
    "ON CONFLICT (entity_id, scheme, value) DO NOTHING"
)


def _read_keys(conn: Any, keys: list[Key]) -> dict[Key, str]:
    rows = conn.execute(_READ_KEYS, ([k[0] for k in keys], [k[1] for k in keys])).fetchall()
    return {(str(r[0]), str(r[1])): str(r[2]) for r in rows}


def resolve_identity_batch(conn: Any, refs: Iterable[tuple[str, str, str]]) -> IdentityBatch:
    """Resolve ``(scheme, value, entity_type)`` refs to entities, minting under the guard.

    One pass for every scheme, in one global ``(scheme, value)`` order. That order is
    what keeps two concurrent writers from deadlocking. Keys that already exist cost
    one round trip in total. Unkeyed values cost four more: claim, mint, identify and
    read back. ``conn`` is anything with psycopg's ``execute``. The caller owns the
    transaction, which must be at the default READ COMMITTED isolation. For a key
    seen twice, the first ``entity_type`` wins.
    """
    type_of: dict[Key, str] = {}
    for scheme, value, entity_type in refs:
        if not value:
            continue
        if scheme not in GUARDED_SCHEMES:
            raise ValueError(
                f"{scheme!r} is not an identity-bearing scheme the guard keys "
                f"(GUARDED_SCHEMES = {sorted(GUARDED_SCHEMES)}; ADR-110)"
            )
        type_of.setdefault((scheme, str(value)), entity_type)
    keys = sorted(type_of)
    if not keys:
        return IdentityBatch({}, frozenset(), frozenset())
    found = _read_keys(conn, keys)
    unkeyed = [k for k in keys if k not in found]
    minted: frozenset[Key] = frozenset()
    adopted: frozenset[Key] = frozenset()
    if unkeyed:
        claimed = conn.execute(
            _CLAIM_KEYS,
            {"schemes": [k[0] for k in unkeyed], "values": [k[1] for k in unkeyed]},
        ).fetchall()
        if claimed:
            won = {(str(r[0]), str(r[1])): str(r[2]) for r in claimed}
            new_ids = {
                str(r[0])
                for r in conn.execute(
                    _MINT, (list(won.values()), [type_of[k] for k in won])
                ).fetchall()
            }
            minted = frozenset(k for k, eid in won.items() if eid in new_ids)
            adopted = frozenset(won) - minted
            conn.execute(
                _IDENTIFY,
                (list(won.values()), [k[0] for k in won], [k[1] for k in won]),
            )
        # A new statement: under READ COMMITTED it sees the keys concurrent writers
        # committed while the claim waited on them.
        found.update(_read_keys(conn, unkeyed))
    missing = [k for k in keys if k not in found]
    if missing:  # pragma: no cover - the PK + the claim step make this unreachable
        raise RuntimeError(f"identity guard left {len(missing)} key(s) unkeyed: {missing[:3]}")
    return IdentityBatch(found, minted, adopted)


def resolve_identities(
    conn: Any, scheme: str, values: Iterable[str], *, entity_type: str
) -> IdentityResolution:
    """:func:`resolve_identity_batch` for one scheme, keyed by value."""
    batch = resolve_identity_batch(conn, ((scheme, str(v), entity_type) for v in values))
    return IdentityResolution(
        {k[1]: eid for k, eid in batch.entity_by_key.items()},
        frozenset(k[1] for k in batch.minted),
        frozenset(k[1] for k in batch.adopted),
    )


__all__ = [
    "GUARDED_SCHEMES",
    "PARTNER_NAME_SCHEME",
    "PARTNER_ORG_SCHEMES",
    "IdentityBatch",
    "IdentityResolution",
    "SUBJECT_SCHEME",
    "resolve_identities",
    "resolve_identity_batch",
]
