# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.75 (R11-ACQ-30) — the Flock share-list §43.2a screen + org-level claim builder.

D-K2-4 + OD-24 [A-22] = yes / b (verbatim): the Eyes on Flock mirror's
``organizations_shared_with`` / ``organizations_received_from`` share lists —
the 474,184 I3 edges — plus P36.74's served-portal lists become
**organisation-level** ``configured_access`` claims, after the
§43.2a/Part VIII screen: **no operator ids, no search reasons, no audit
rows**. GATE-G5 §3 (2026-10-25T18:40Z) approved "the Flock share-list §43.2a
screen" lane; the write itself is the OM-20 named mutation (the GATE-G5 §4
list names P36.75 verbatim).

Three pure pieces, exercised over committed fixtures:

* **The screen** — :func:`screen_share_fieldset`. Whole-fieldset (A-22): one
  deny-class hit ANYWHERE on the portal record refuses the portal's whole
  share fieldset — never a field-level drop. The vocabulary is committed
  data (``data/flock_share_screen.toml``, ``sig.flock-share-screen/1``):
  operator-id / search-reason / audit-row classes, the F-330 person-material
  denylist delegated (never forked), the unreviewed-record-row catch-all,
  and the organisation-slug entry shape every share-list value must match.
  Verdicts are **counts only** — a hit names its class, never the material.

* **The claim builder** — :func:`build_share_claims`. Screened portals feed
  P08.2's §29.3 machinery exactly as the connectors do
  (``sharing_observations`` → ``reconcile_sharing`` → the same
  ``configured_sharing_partner`` rows + the P31.6 partner ``object_ref``), so
  a claim the builder emits digests identically to the connector-emitted one
  — the hosted write dedupes to +0 against claims the mirror already
  landed. Claims carry ``access_kind='configured_access'`` at organisation
  level only: subjects/objects are ``flock_portal:<slug>`` platform
  identities — never a person, never an operator, never an audit row
  (SIG-ENG-042: a claim outside the organisation level fails).

* **The GX-08b feed** — :func:`build_share_feed`. The screened edge set
  projected into the deterministic ``sig.flock-share-feed/1`` document the
  state × state Flock-sharing overview (P37.25, A-11) consumes: per-state
  cells, the slug→state placement the claims themselves don't carry (the
  aggregator's ``state`` field is context, never a claim), and the honest
  unplaced list.

The hosted append-only write (plan/apply over the claim spine) lives in
``db.flock_share_write`` — the same split P35.15b used: ``db`` owns the
spine-write machinery, connectors owns the emit path. This module never
touches a socket, a DSN or a clock.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Any

from evidence.claim_identity import claim_digest
from evidence.digest import multihash
from reconcile.sharing import ReconciledEdge, reconcile_sharing

from . import field_denylist, flock_portal
from ._data import load_table
from .flock_portal import EYES_ON_FLOCK_SOURCE_ID, sharing_observations_for_portal

PROBE_SOURCE_ID = "flock_transparency_portals"
SCREEN_TABLE = "flock_share_screen"
SCREEN_SCHEMA = "sig.flock-share-screen/1"
FEED_SCHEMA = "sig.flock-share-feed/1"
BUILDER = "flock-share-lists/1"

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])")


def _tokens(name: str) -> list[str]:
    """Normalise a field name to lowercase snake tokens — the F-330 rule."""
    return [t for t in _TOKEN_SPLIT.split(_CAMEL.sub("_", name).lower()) if t]


def screen_vocab() -> dict[str, Any]:
    """The committed ``sig.flock-share-screen/1`` table — fail closed on drift."""
    table = load_table(SCREEN_TABLE)
    if table.get("schema") != SCREEN_SCHEMA:
        raise ValueError(f"{SCREEN_TABLE}.toml schema must be {SCREEN_SCHEMA!r}")
    if not table.get("classes"):
        raise ValueError(f"{SCREEN_TABLE}.toml carries no [[classes]]")
    return table


def _exempt() -> frozenset[str]:
    return frozenset(str(f) for f in screen_vocab().get("exempt_fields", ()))


def _known_unmapped() -> frozenset[str]:
    return frozenset(str(f) for f in screen_vocab().get("known_unmapped_fields", ()))


def _share_fields() -> tuple[str, ...]:
    return tuple(str(f) for f in screen_vocab().get("share_fields", ()))


def _entry_re() -> re.Pattern[str]:
    pattern = str(screen_vocab().get("entry_pattern") or "")
    if not pattern:
        raise ValueError(f"{SCREEN_TABLE}.toml carries no entry_pattern")
    return re.compile(pattern)


def _list_fields() -> tuple[str, ...]:
    """The two directional share-list fields (subset of ``share_fields``)."""
    keep = {"organizations_shared_with", "organizations_received_from"}
    return tuple(f for f in _share_fields() if f in keep)


@dataclass(frozen=True)
class ScreenClass:
    """One deny class from the vocabulary table."""

    class_id: str
    tokens: frozenset[str]
    sequences: tuple[tuple[str, ...], ...]
    value_kinds: frozenset[str]
    field_denylist: bool = False
    match_unreviewed: bool = False


def _classes() -> tuple[ScreenClass, ...]:
    out: list[ScreenClass] = []
    for row in screen_vocab().get("classes", ()):
        out.append(
            ScreenClass(
                class_id=str(row["class_id"]),
                tokens=frozenset(str(t) for t in row.get("tokens", ())),
                sequences=tuple(tuple(str(t) for t in seq) for seq in row.get("sequences", ())),
                value_kinds=frozenset(str(k) for k in row.get("value_kinds", ("any",))),
                field_denylist=bool(row.get("field_denylist", False)),
                match_unreviewed=bool(row.get("match_unreviewed", False)),
            )
        )
    return tuple(out)


def _value_kind(value: Any) -> str:
    if isinstance(value, Mapping):
        return "dict"
    if isinstance(value, (list, tuple)):
        return "list"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    return "null"


def _material(cls: ScreenClass, value: Any) -> bool:
    """Whether ``value`` can carry material under ``cls``'s declared kinds."""
    kind = _value_kind(value)
    if "any" not in cls.value_kinds and kind not in cls.value_kinds:
        return False
    if kind == "string":
        return bool(value.strip())
    if kind in ("list", "dict"):
        return bool(value)
    return value is not None


def _name_hit(cls: ScreenClass, name: str) -> bool:
    """The class's name check only (value-kind tested separately)."""
    if cls.field_denylist:
        return field_denylist.denied_match(name) is not None
    toks = _tokens(name)
    if not toks:
        return False
    if any(t in cls.tokens for t in toks):
        return True
    for seq in cls.sequences:
        n = len(seq)
        if n and any(tuple(toks[i : i + n]) == seq for i in range(len(toks) - n + 1)):
            return True
    return False


def _walk(record: Mapping[str, Any]) -> Iterator[tuple[str, Any]]:
    """Every (name, value) in the record — top level plus nested mappings."""
    for key, value in record.items():
        name = str(key)
        yield name, value
        if isinstance(value, Mapping):
            yield from _walk(value)
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, Mapping):
                    yield from _walk(item)


@dataclass(frozen=True)
class ScreenVerdict:
    """The §43.2a verdict for one portal record — counts only, never material."""

    refused: bool
    #: class_id -> hit count (a hit names its class, never the field value).
    hits: Mapping[str, int]
    #: Unreviewed scalar fields tolerated (counted, never read by the builder).
    tolerated: tuple[str, ...]


def screen_share_fieldset(record: Mapping[str, Any]) -> ScreenVerdict:
    """The §43.2a/Part VIII whole-fieldset screen (D-K2-4 + OD-24 [A-22]).

    One deny-class hit ANYWHERE on the portal record refuses the WHOLE share
    fieldset — both directional lists and the slug/state the edges key on —
    so a portal carrying prohibited material contributes zero edges. Deny
    hits name their class only; the field value is never recorded.
    """
    exempt = _exempt()
    known = _known_unmapped()
    classes = _classes()
    deny_classes = [c for c in classes if not c.match_unreviewed]
    unreviewed = next((c for c in classes if c.match_unreviewed), None)
    hits: dict[str, int] = {}
    tolerated: list[str] = []
    for name, value in _walk(record):
        if name in exempt or name in known:
            continue
        named = [c for c in deny_classes if _name_hit(c, name)]
        hit = next((c for c in named if _material(c, value)), None)
        if hit is not None:
            hits[hit.class_id] = hits.get(hit.class_id, 0) + 1
            continue
        if named:
            # A deny-named field with only config-kind values is tolerated.
            tolerated.append(name)
            continue
        if unreviewed is not None and _material(unreviewed, value):
            hits[unreviewed.class_id] = hits.get(unreviewed.class_id, 0) + 1
        else:
            tolerated.append(name)
    # Every share-list entry MUST be an organisation-platform slug — a
    # free-text/person/id entry refuses the whole fieldset.
    pattern = _entry_re()
    for field_name in _list_fields():
        entries = record.get(field_name)
        if not isinstance(entries, (list, tuple)):
            continue
        for entry in entries:
            if not isinstance(entry, str) or not pattern.match(entry):
                hits["P8-NON-SLUG-ENTRY"] = hits.get("P8-NON-SLUG-ENTRY", 0) + 1
    return ScreenVerdict(refused=bool(hits), hits=hits, tolerated=tuple(sorted(tolerated)))


# --- inputs -------------------------------------------------------------------


def snapshot_portals(doc: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """The portal records of an aggregator mirror snapshot — fail closed."""
    portals = doc.get("portals")
    if not isinstance(portals, list):
        raise ValueError("aggregator snapshot carries no `portals` list")
    if not all(isinstance(p, Mapping) for p in portals):
        raise ValueError("aggregator snapshot `portals` carries a non-object row")
    return [dict(p) for p in portals]


def page_record_portal(doc: Mapping[str, Any]) -> Mapping[str, Any]:
    """The mirror-schema portal object of one ``sig.flock-portal-page/1`` record."""
    from .flock_portal_probe import PAGE_SCHEMA

    if doc.get("schema") != PAGE_SCHEMA:
        raise ValueError(f"portal extraction must be a {PAGE_SCHEMA} record")
    portal = doc.get("portal")
    if not isinstance(portal, Mapping) or not portal:
        raise ValueError(f"{PAGE_SCHEMA} record carries no `portal` object")
    return dict(portal)


# --- the claim builder ---------------------------------------------------------


#: The claim fields a ``configured_sharing_partner`` row may carry — the
#: organisation-level contract every emitted claim is audited against (the
#: catalog AC verbatim: 0 person-level or audit-row fields).
CLAIM_FIELDS: frozenset[str] = frozenset(
    {
        "record_kind",
        "subject_id",
        "predicate_id",
        "value",
        "raw_value",
        "object_ref",
        "from_org",
        "to_org",
        "access_kind",
        "valid_from_kind",
        "corroborated",
        "observations_count",
        "source_id",
        "source_attribution",
        "license",
        "compartment",
        "ai_training_permitted",
        "evidence_genre",
    }
)


@dataclass
class ShareBuild:
    """What :func:`build_share_claims` produces for one evidence unit."""

    claims: list[dict[str, Any]]
    edges: tuple[ReconciledEdge, ...]
    screened_portals: int
    #: Per refused portal: its slug and the class-hit counts (never material).
    refused: list[dict[str, Any]]
    tolerated_fields: list[str]
    feed: dict[str, Any]
    claim_set_digest: str = ""


def _claim_set_digest(claims: Iterable[Mapping[str, Any]]) -> str:
    """Order-independent digest of the claim set's UNSEALED identity digests.

    ``claim_digest`` here is the pre-binding identity — the sink seals each
    claim's extraction-binding versions at write (SIG-INGEST-004); the set
    digest pins WHAT the screened set is, and the written row's stored
    ``content_digest`` derives from it deterministically.
    """
    digests = sorted(claim_digest(dict(c)) for c in claims)
    return hashlib.sha256("\n".join(digests).encode("utf-8")).hexdigest()


def build_share_claims(
    portals: Iterable[Mapping[str, Any]],
    *,
    source_id: str = EYES_ON_FLOCK_SOURCE_ID,
    attribution: str = "",
) -> ShareBuild:
    """Screen every portal, then build org-level ``configured_access`` claims.

    Refused portals contribute ZERO observations (whole-fieldset, A-22). The
    clean set reconciles through P08.2's §29.3 machinery — the same path the
    connectors emit through — and every edge lands as a
    ``configured_sharing_partner`` claim with the partner's portal
    ``object_ref``, stamped into the CC-BY-SA-4.0 ``portal`` compartment.
    """
    screened = 0
    refused: list[dict[str, Any]] = []
    tolerated: set[str] = set()
    observations = []
    org_states: dict[str, str] = {}
    for portal in portals:
        screened += 1
        slug = str(portal.get(str(flock_portal._identity()["slug_field"]), "")).strip()
        verdict = screen_share_fieldset(portal)
        tolerated.update(verdict.tolerated)
        if verdict.refused:
            refused.append({"slug": slug or "<missing>", "classes": dict(verdict.hits)})
            continue
        observed_at = flock_portal.portal_snapshot_date(portal)
        if slug and observed_at is not None:
            observations.extend(sharing_observations_for_portal(portal, slug, observed_at))
        state = str(portal.get("state") or "").strip()
        if slug and state:
            org_states[slug] = state
    reconciliation = reconcile_sharing(observations)
    claims: list[dict[str, Any]] = []
    for row in flock_portal._sharing_edge_rows(reconciliation, attribution=attribution):
        claim = dict(row)
        to_org = str(claim.get("to_org") or "").strip()
        if to_org:
            claim["object_ref"] = flock_portal._portal_partner_ref(to_org)
        claim["source_id"] = source_id
        claims.append(claim)
    claims.sort(key=lambda c: (str(c.get("subject_id")), str(c.get("value"))))
    feed = build_share_feed(
        reconciliation.edges,
        org_states=org_states,
        screened_portals=screened,
        refused=refused,
        source_id=source_id,
    )
    return ShareBuild(
        claims=claims,
        edges=reconciliation.edges,
        screened_portals=screened,
        refused=refused,
        tolerated_fields=sorted(tolerated),
        feed=feed,
        claim_set_digest=_claim_set_digest(claims),
    )


def build_share_feed(
    edges: Iterable[ReconciledEdge],
    *,
    org_states: Mapping[str, str],
    screened_portals: int,
    refused: list[dict[str, Any]],
    source_id: str,
) -> dict[str, Any]:
    """The ``sig.flock-share-feed/1`` document GX-08b (P37.25, A-11) consumes.

    Deterministic: cells sorted by (from_state, to_state), the slug→state
    placement the claims deliberately do not carry (``state`` is aggregator
    context, never a claim), and the honest unplaced list — an endpoint whose
    portal never carried ``state``.
    """
    edge_list = sorted(edges, key=lambda e: (e.from_org, e.to_org))
    cells: dict[tuple[str, str], int] = {}
    unplaced: set[str] = set()
    for edge in edge_list:
        frm = org_states.get(edge.from_org)
        to = org_states.get(edge.to_org)
        if frm is None:
            unplaced.add(edge.from_org)
        if to is None:
            unplaced.add(edge.to_org)
        if frm is None or to is None:
            continue
        cells[(frm, to)] = cells.get((frm, to), 0) + 1
    doc: dict[str, Any] = {
        "schema": FEED_SCHEMA,
        "builder": BUILDER,
        "source_id": source_id,
        "access_kind": "configured_access",
        "screened_portals": screened_portals,
        "refused_portals": len(refused),
        "refusal_classes": {
            cls: sum(r["classes"].get(cls, 0) for r in refused)
            for cls in sorted({c for r in refused for c in r["classes"]})
        },
        "edges": len(edge_list),
        "org_states": dict(sorted(org_states.items())),
        "unplaced_orgs": sorted(unplaced),
        "cells": [
            {"from_state": frm, "to_state": to, "edges": n}
            for (frm, to), n in sorted(cells.items())
        ],
    }
    doc["digest"] = multihash(
        json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    )
    return doc


__all__ = [
    "BUILDER",
    "CLAIM_FIELDS",
    "FEED_SCHEMA",
    "PROBE_SOURCE_ID",
    "SCREEN_SCHEMA",
    "ShareBuild",
    "ScreenVerdict",
    "build_share_claims",
    "build_share_feed",
    "page_record_portal",
    "screen_share_fieldset",
    "screen_vocab",
    "snapshot_portals",
]
