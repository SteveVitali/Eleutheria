# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The organisation cascade materializer — tiers 0–1 auto-link, tier 2
'possibly the same' (P37.46b, R11-CONF-13 13b; design CP-10; SIG-CONF-004,
SIG-IDENT-020/025, ADR-L3-B §4).

P37.46a's crosswalk intake asserts registry identifiers onto organisation
entities (``entity_identifier`` rows with ``asserted_by_claim`` provenance).
This module is the 13b half — the production materializer that reads those
assertions off the spine and records the cascade's match records append-only:

* :func:`read_org_candidates` assembles each organisation entity's cascade
  surface: its lane identifiers (with the asserting claims), its name / state /
  class, and whether the entity is an ``org_crosswalk_entry`` — an upstream
  registry's own multi-scheme assertion (the established crosswalk tier 1
  consumes).
* :func:`plan_org_cascade` is the pure decision pass. **Tier 0** auto-links
  every pair sharing an exact authoritative identifier (ORI9, GEOID, LEI, UEI,
  QID — the committed ``tier0_schemes``, with the ORI validity + civil-ORI
  rules of :mod:`resolution.cascade`). **Tier 1** auto-links a pair an
  ``org_crosswalk_entry`` bridges — entity A shares one identifier with the
  crosswalk row and entity B another — the established registry crosswalk.
  **Tier 2** (normalized name + state + class, minus the committed collision
  exclusion) records ``possibly_same`` and is **surfaced, never linked**
  (SIG-CONF-004 / ADR-L3-B §4: a name-based match is published as "possibly
  the same"; it auto-links only once a registry-generated collision list
  exists). Every decision carries ``match_tier`` + ``match_evidence`` +
  ``evidence_claims`` (SIG-IDENT-025).
* :func:`materialize_org_cascade` writes the run append-only:
  ``organization_match`` rows ``INSERT … ON CONFLICT (input_digest) DO
  NOTHING`` (+0 on a digest-identical re-run), then the ``organization_run``
  record LAST as the completion marker plus one ``organization_execution``
  row per execution (ADR-123 latest-execution semantics). Nothing UPDATEs or
  DELETEs.
* :func:`read_org_cascade_runs` is the read seam: the latest COMPLETED
  execution's run plus its recorded links, for the identity report and any
  later export surface.
"""

from __future__ import annotations

import hashlib
import json
import uuid as _uuid
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from .camera_sites_pg import set_role
from .cascade import CascadeContext
from .normalize import NORMALIZE_RULESET_VERSION, normalize_org_name
from .ori import is_civil_ori, is_valid_ori

__all__ = [
    "AUTO_LINK_TIERS",
    "CROSSWALK_SUBJECT_PREFIX",
    "ORG_CASCADE_RESOLVER_VERSION",
    "ORG_CASCADE_RULESET_VERSION",
    "REPORT_SCHEMA",
    "OrgCascadeResult",
    "OrgDecision",
    "OrgIdentifier",
    "OrgRecord",
    "materialize_org_cascade",
    "materialize_org_cascade_from_dsn",
    "org_decision_digest",
    "org_run_key",
    "plan_org_cascade",
    "read_org_candidates",
    "read_org_cascade_runs",
    "set_role",
]

#: The committed run-record schema (``organization_run.summary.record_type``).
REPORT_SCHEMA = "sig.org-cascade-run/1"
#: Resolver/ruleset versions stamped on every row — a ruleset change mints new
#: run keys, never a silent re-link (SIG-RECON-002).
ORG_CASCADE_RESOLVER_VERSION = "org-cascade/1"
ORG_CASCADE_RULESET_VERSION = "org-cascade-rules/1"
#: The tiers that may auto-link (ADR-L3-B §4): 0 = exact shared authoritative
#: identifier, 1 = established registry crosswalk. Tier 2 stays surfaced.
AUTO_LINK_TIERS = (0, 1)
#: The minted-subject prefix marking an org_crosswalk_entry entity.
CROSSWALK_SUBJECT_PREFIX = "org_crosswalk_entry:"


@dataclass(frozen=True)
class OrgIdentifier:
    """One asserted identifier with its provenance claim (entity_identifier row)."""

    scheme: str
    value: str
    claim_id: str | None = None


@dataclass(frozen=True)
class OrgRecord:
    """One organisation entity's cascade surface (the deterministic fields only).

    ``identifiers`` carries every tier-0-scheme ``entity_identifier`` row with
    its ``asserted_by_claim``; ``attribute_claims`` the claim ids the name /
    state surface was read from (tier-2 evidence). ``is_crosswalk_entry``
    marks an entity minted from an ``org_crosswalk_entry`` subject — the
    upstream-established crosswalk tier 1 bridges through.
    """

    entity_id: str
    organization_class: str = "us.org"
    name: str | None = None
    state: str | None = None
    identifiers: tuple[OrgIdentifier, ...] = ()
    is_crosswalk_entry: bool = False
    attribute_claims: tuple[str, ...] = ()

    @property
    def normalized_name(self) -> str:
        return normalize_org_name(self.name) if self.name else ""


@dataclass(frozen=True)
class OrgDecision:
    """One recorded match decision (SIG-IDENT-020/025).

    ``relation`` is the emitted link vocabulary: ``same_as`` for tiers 0–1
    (disposition ``auto_link``), ``possibly_same`` for tier 2 (disposition
    ``surfaced`` — recorded for display, never clustered into an identity).
    """

    left: str
    right: str
    tier: int
    tier_label: str
    relation: str
    disposition: str
    reason: str | None
    evidence: dict[str, Any]
    evidence_claims: tuple[str, ...] = ()

    @property
    def pair(self) -> tuple[str, str]:
        return (self.left, self.right)


@dataclass(frozen=True)
class OrgCascadeResult:
    """The output of one organisation cascade run (pure; persisted by
    :func:`materialize_org_cascade`)."""

    ruleset_version: str
    resolver_version: str
    run_key: str
    organization_count: int
    decisions: tuple[OrgDecision, ...]
    clusters: dict[str, str]
    crosswalk_entries: int = 0
    collision_excluded_pairs: int = 0

    def summary(self) -> dict[str, Any]:
        by_tier: dict[str, dict[str, int]] = {}
        for d in self.decisions:
            slot = by_tier.setdefault(d.tier_label, {"auto_link": 0, "surfaced": 0})
            slot[d.disposition] = slot.get(d.disposition, 0) + 1
        sizes: dict[int, int] = {}
        members: dict[str, int] = {}
        for c in self.clusters.values():
            members[c] = members.get(c, 0) + 1
        for n in members.values():
            sizes[n] = sizes.get(n, 0) + 1
        links = sum(1 for d in self.decisions if d.relation == "same_as")
        return {
            "record_type": REPORT_SCHEMA,
            "run_key": self.run_key,
            "ruleset_version": self.ruleset_version,
            "resolver_version": self.resolver_version,
            "auto_link_tiers": list(AUTO_LINK_TIERS),
            "organizations": self.organization_count,
            "crosswalk_entries": self.crosswalk_entries,
            "same_as_pairs": links,
            "possibly_same_pairs": len(self.decisions) - links,
            "resolved_organizations": len(set(self.clusters.values())),
            "cluster_size_histogram": {str(k): v for k, v in sorted(sizes.items())},
            "collision_excluded_pairs": self.collision_excluded_pairs,
            "by_tier": {k: by_tier[k] for k in sorted(by_tier)},
        }


# --------------------------------------------------------------------------- #
# The pure decision pass                                                       #
# --------------------------------------------------------------------------- #


def _usable_identifier(scheme: str, value: str) -> bool:
    """Whether ``(scheme, value)`` is a tier-0-usable authoritative identifier.

    Mirrors :func:`resolution.cascade._tier0`: an ORI is usable only when it is
    a valid ORI9 that is not a civil/applicant ORI (SIG-IDENT-003 — a civil ORI
    never auto-links by itself); every other scheme passes through.
    """
    if scheme != "us.fbi.ori":
        return True
    return is_valid_ori(value) and not is_civil_ori(value)


def _union_find(edges: Iterable[tuple[str, str]], nodes: Iterable[str]) -> dict[str, str]:
    parent: dict[str, str] = {n: n for n in nodes}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        root = x
        while parent[root] != root:
            root = parent[root]
        while parent[x] != root:
            parent[x], x = root, parent[x]
        return root

    for a, b in edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            lo, hi = sorted((ra, rb))
            parent[hi] = lo
    return {n: find(n) for n in parent}


def _pair(a: str, b: str) -> tuple[str, str]:
    return (a, b) if a < b else (b, a)


def plan_org_cascade(
    records: Sequence[OrgRecord],
    *,
    context: CascadeContext | None = None,
) -> OrgCascadeResult:
    """The deterministic organisation cascade over ``records`` (pure).

    Deterministic tiers run over the authoritative-identifier index
    (``context.tier0_schemes``, ORI-usable only): tier 0 for every pair sharing
    an identifier, tier 1 for every pair a crosswalk-entry entity bridges.
    Tier 2 then surfaces the remaining same-name+state+class pairs as
    ``possibly_same`` — never linked — minus the committed collision exclusion.
    Returns the full :class:`OrgCascadeResult`; the caller persists it.
    """
    ctx = context if context is not None else CascadeContext.from_data()
    recs = sorted(records, key=lambda r: r.entity_id)
    by_entity = {r.entity_id: r for r in recs}
    decided: dict[tuple[str, str], OrgDecision] = {}

    # The authoritative-identifier index: (scheme, value) -> entities, plus the
    # asserting claim per (entity, scheme, value) — the match record's
    # evidence_claims provenance (SIG-IDENT-025).
    id_index: dict[tuple[str, str], set[str]] = {}
    claim_index: dict[tuple[str, str, str], str] = {}
    usable_ids: dict[str, set[tuple[str, str]]] = {}
    for r in recs:
        mine = usable_ids.setdefault(r.entity_id, set())
        for i in r.identifiers:
            if i.scheme not in ctx.tier0_schemes or not _usable_identifier(i.scheme, i.value):
                continue
            key = (i.scheme, i.value)
            id_index.setdefault(key, set()).add(r.entity_id)
            mine.add(key)
            if i.claim_id:
                claim_index[(r.entity_id, i.scheme, i.value)] = i.claim_id

    def _claims_for(*args: tuple[str, str, str]) -> tuple[str, ...]:
        return tuple(sorted(claim_index[a] for a in args if a in claim_index))

    # Tier 0 — an exact shared authoritative identifier (SIG-CONF-004).
    shared: dict[tuple[str, str], list[tuple[str, str]]] = {}
    for (scheme, value), entities in sorted(id_index.items()):
        ents = sorted(entities)
        for x in range(len(ents)):
            for y in range(x + 1, len(ents)):
                shared.setdefault(_pair(ents[x], ents[y]), []).append((scheme, value))
    for (a, b), ids in sorted(shared.items()):
        decided[(a, b)] = OrgDecision(
            left=a,
            right=b,
            tier=0,
            tier_label="0",
            relation="same_as",
            disposition="auto_link",
            reason=None,
            evidence={
                "rule": "exact_shared_canonical_identifier",
                "shared_identifiers": [{"scheme": s, "value": v} for s, v in ids],
            },
            evidence_claims=_claims_for(*((e, s, v) for e in (a, b) for s, v in ids)),
        )

    # Tier 1 — the established registry crosswalk: a crosswalk-entry entity
    # whose upstream row asserts identifiers both sides share. The pair is
    # recorded with the bridging entry as its evidence, never re-derived.
    for c in recs:
        if not c.is_crosswalk_entry:
            continue
        c_ids = usable_ids.get(c.entity_id, set())
        partners = sorted({e for key in c_ids for e in id_index.get(key, ())} - {c.entity_id})
        for x in range(len(partners)):
            for y in range(x + 1, len(partners)):
                a, b = partners[x], partners[y]
                if (a, b) in decided:
                    continue
                via = sorted(
                    (c_ids & usable_ids.get(a, set())) | (c_ids & usable_ids.get(b, set()))
                )
                decided[(a, b)] = OrgDecision(
                    left=a,
                    right=b,
                    tier=1,
                    tier_label="1",
                    relation="same_as",
                    disposition="auto_link",
                    reason=None,
                    evidence={
                        "rule": "established_upstream_crosswalk",
                        "crosswalk_entity": c.entity_id,
                        "crosswalk_identifiers": [{"scheme": s, "value": v} for s, v in via],
                    },
                    evidence_claims=_claims_for(
                        *((e, s, v) for e in (a, b, c.entity_id) for s, v in via)
                    ),
                )

    # Tier 2 — normalized name + state + class, minus the committed collision
    # exclusion: surfaced as 'possibly the same', NEVER auto-linked
    # (SIG-CONF-004 / ADR-L3-B §4). A pair already linked at tier 0/1 keeps the
    # stronger record only.
    by_name: dict[tuple[str, str, str], list[str]] = {}
    for r in recs:
        name = r.normalized_name
        if not name or r.state is None:
            continue
        by_name.setdefault((name, r.state, r.organization_class), []).append(r.entity_id)
    collision = 0
    for (name, state, org_class), ents in sorted(by_name.items()):
        for x in range(len(ents)):
            for y in range(x + 1, len(ents)):
                a, b = ents[x], ents[y]
                if (a, b) in decided:
                    continue
                if name in ctx.name_collisions:
                    collision += 1
                    continue
                attr_claims = tuple(
                    sorted(set(by_entity[a].attribute_claims) | set(by_entity[b].attribute_claims))
                )
                decided[(a, b)] = OrgDecision(
                    left=a,
                    right=b,
                    tier=2,
                    tier_label="2",
                    relation="possibly_same",
                    disposition="surfaced",
                    reason="name_match_possibly_same",
                    evidence={
                        "rule": "normalized_name_state_class",
                        "normalized_name": name,
                        "state": state,
                        "organization_class": org_class,
                        "normalize_ruleset_version": NORMALIZE_RULESET_VERSION,
                        "surface": (
                            "possibly the same — a name-based match is "
                            "surfaced, never auto-linked (SIG-CONF-004 / "
                            "ADR-L3-B §4)"
                        ),
                    },
                    evidence_claims=attr_claims,
                )

    decisions = tuple(decided[k] for k in sorted(decided))
    same_as_edges = [(d.left, d.right) for d in decisions if d.relation == "same_as"]
    clusters = _union_find(same_as_edges, [r.entity_id for r in recs])
    return OrgCascadeResult(
        ruleset_version=ORG_CASCADE_RULESET_VERSION,
        resolver_version=ORG_CASCADE_RESOLVER_VERSION,
        run_key=org_run_key(recs, context=ctx),
        organization_count=len(recs),
        decisions=decisions,
        clusters=clusters,
        crosswalk_entries=sum(1 for r in recs if r.is_crosswalk_entry),
        collision_excluded_pairs=collision,
    )


def _freeze(v: Any) -> Any:
    if isinstance(v, (set, frozenset)):
        frozen = [_freeze(x) for x in v]
        return sorted(frozen, key=lambda e: json.dumps(e, sort_keys=True, default=str))
    if isinstance(v, dict):
        return {str(k): _freeze(v[k]) for k in sorted(v, key=str)}
    if isinstance(v, (list, tuple)):
        return [_freeze(x) for x in v]
    return v


def org_run_key(records: Sequence[OrgRecord], *, context: CascadeContext) -> str:
    """The run identity: every input a decision depends on.

    Digests the resolver + ruleset versions, the cascade context (tier-0
    schemes, the collision exclusion, the normalize ruleset), and every
    record's full surface — entity id, class, name, state, crosswalk flag and
    every identifier with its asserting claim. Two runs over the same inputs
    share a key (the re-run is +0); ANY change a decision could depend on
    mints a new key, and readers take the latest COMPLETED execution's run
    whole — never a union of stale and fresh edges.
    """
    h = hashlib.sha256()
    h.update(
        json.dumps(
            {
                "resolver": ORG_CASCADE_RESOLVER_VERSION,
                "ruleset": ORG_CASCADE_RULESET_VERSION,
                "auto": sorted(AUTO_LINK_TIERS),
                "tier0_schemes": sorted(context.tier0_schemes),
                "name_collisions": sorted(context.name_collisions),
                "normalize_ruleset": NORMALIZE_RULESET_VERSION,
            },
            sort_keys=True,
        ).encode()
    )
    for r in sorted(records, key=lambda r: r.entity_id):
        h.update(
            json.dumps(
                _freeze(
                    {
                        "entity": r.entity_id,
                        "class": r.organization_class,
                        "name": r.name,
                        "state": r.state,
                        "crosswalk": r.is_crosswalk_entry,
                        "ids": [
                            {"scheme": i.scheme, "value": i.value, "claim": i.claim_id}
                            for i in r.identifiers
                        ],
                        "attribute_claims": list(r.attribute_claims),
                    }
                ),
                sort_keys=True,
                default=str,
            ).encode()
        )
        h.update(b"\n")
    return "orgcascade:" + h.hexdigest()[:40]


def org_decision_digest(key: str, d: OrgDecision) -> str:
    """The idempotency digest of one match row (a digest-identical re-run = +0)."""
    payload = {
        "run_key": key,
        "left": d.left,
        "right": d.right,
        "tier": d.tier,
        "relation": d.relation,
        "disposition": d.disposition,
        "reason": d.reason,
        "claims": list(d.evidence_claims),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


# --------------------------------------------------------------------------- #
# The spine read                                                              #
# --------------------------------------------------------------------------- #

_ORGS_SQL = (
    "SELECT e.entity_id::text, o.organization_type, o.cached_canonical_name "
    "FROM entity e LEFT JOIN organization o ON o.entity_id = e.entity_id "
    "WHERE e.entity_type = 'organization'"
)
_IDS_SQL = (
    "SELECT ei.entity_id::text, ei.scheme, ei.value, ei.asserted_by_claim::text "
    "FROM entity_identifier ei "
    "JOIN entity e ON e.entity_id = ei.entity_id AND e.entity_type = 'organization' "
    "WHERE ei.scheme = ANY(%s::text[])"
)
_XWALK_SQL = (
    "SELECT ei.entity_id::text FROM entity_identifier ei "
    "JOIN entity e ON e.entity_id = ei.entity_id AND e.entity_type = 'organization' "
    "WHERE ei.scheme = 'sig.connector.subject' "
    "  AND ei.value LIKE 'org_crosswalk_entry:%'"
)
#: The name / jurisdiction surface: the latest *current* claim per subject per
#: predicate (a claim id is never a timestamp — order by the assertion's own
#: sys_period lower bound, claim_id as the exact-tie breaker).
_NAME_SQL = (
    "SELECT DISTINCT ON (c.subject_id) c.subject_id::text, "
    "       COALESCE(c.value_text, c.value_json->>'value'), c.claim_id::text "
    "FROM claim c WHERE c.predicate_id = 'organization_legal_name' "
    "  AND upper_inf(c.sys_period) "
    "ORDER BY c.subject_id, lower(c.sys_period) DESC, c.claim_id"
)
_STATE_SQL = (
    "SELECT DISTINCT ON (c.subject_id) c.subject_id::text, "
    "       COALESCE(c.value_text, c.value_json->>'value'), c.claim_id::text "
    "FROM claim c WHERE c.predicate_id = 'organization_jurisdiction' "
    "  AND upper_inf(c.sys_period) "
    "ORDER BY c.subject_id, lower(c.sys_period) DESC, c.claim_id"
)


def read_org_candidates(conn: Any, *, context: CascadeContext | None = None) -> list[OrgRecord]:
    """Assemble each organisation entity's cascade surface off the spine.

    Identifiers come from ``entity_identifier`` restricted to the cascade's
    tier-0 schemes (provenance: ``asserted_by_claim``); the crosswalk-entry
    flag from the ``sig.connector.subject`` minted id; the name prefers the
    cached canonical name and falls back to the latest current
    ``organization_legal_name`` claim; the state is the latest current
    ``organization_jurisdiction`` claim. Entities with no organization
    projection row keep the ``us.org`` class default — the cascade never
    invents a class.
    """
    ctx = context if context is not None else CascadeContext.from_data()
    recs: dict[str, dict[str, Any]] = {}
    for eid, otype, cname in conn.execute(_ORGS_SQL).fetchall():
        recs[str(eid)] = {
            "class": str(otype) if otype else "us.org",
            "name": cname if cname else None,
            "state": None,
            "attr": [],
        }
    xwalk = {str(r[0]) for r in conn.execute(_XWALK_SQL).fetchall()}
    idents: dict[str, list[OrgIdentifier]] = {}
    for eid, scheme, value, cid in conn.execute(_IDS_SQL, (sorted(ctx.tier0_schemes),)).fetchall():
        idents.setdefault(str(eid), []).append(
            OrgIdentifier(str(scheme), str(value), None if cid is None else str(cid))
        )
    for eid, value, cid in conn.execute(_NAME_SQL).fetchall():
        tgt = recs.get(str(eid))
        if tgt is None:
            continue
        if tgt["name"] is None and value:
            tgt["name"] = str(value)
        if cid:
            tgt["attr"].append(str(cid))
    for eid, value, cid in conn.execute(_STATE_SQL).fetchall():
        tgt = recs.get(str(eid))
        if tgt is None:
            continue
        if value:
            tgt["state"] = str(value)
        if cid:
            tgt["attr"].append(str(cid))
    return [
        OrgRecord(
            entity_id=eid,
            organization_class=recs[eid]["class"],
            name=recs[eid]["name"],
            state=recs[eid]["state"],
            identifiers=tuple(sorted(idents.get(eid, []), key=lambda i: (i.scheme, i.value))),
            is_crosswalk_entry=eid in xwalk,
            attribute_claims=tuple(sorted(set(recs[eid]["attr"]))),
        )
        for eid in sorted(recs)
    ]


# --------------------------------------------------------------------------- #
# The append-only write                                                        #
# --------------------------------------------------------------------------- #

_INSERT_MATCH = (
    "INSERT INTO organization_match(run_key, left_entity, right_entity, "
    " relation_type, match_tier, tier_label, disposition, disposition_reason, "
    " match_evidence, evidence_claims, ruleset_version, resolver_version, "
    " input_digest, decided_by) "
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::uuid[], %s, %s, %s, %s) "
    "ON CONFLICT (input_digest) DO NOTHING RETURNING match_id"
)


def _decision_row(result: OrgCascadeResult, d: OrgDecision) -> tuple[Any, ...]:
    return (
        result.run_key,
        d.left,
        d.right,
        d.relation,
        d.tier,
        d.tier_label,
        d.disposition,
        d.reason,
        json.dumps(d.evidence, sort_keys=True),
        [c for c in d.evidence_claims if c],
        result.ruleset_version,
        result.resolver_version,
        org_decision_digest(result.run_key, d),
        "auto",
    )


def materialize_org_cascade(
    conn: Any,
    *,
    role: str | None = None,
    records: Sequence[OrgRecord] | None = None,
    context: CascadeContext | None = None,
    execution_id: str | None = None,
    batch_size: int = 1_000,
    progress: Callable[[str, int, int], None] | None = None,
) -> dict[str, Any]:
    """Run one organisation cascade pass over the spine and materialize it.

    Append-only: every recorded decision is an ``organization_match`` row
    (``ON CONFLICT (input_digest) DO NOTHING`` — a re-run over an unchanged
    spine is +0), the ``organization_run`` record lands LAST as the completion
    marker, and one ``organization_execution`` row is appended per execution
    (retrying the same ``execution_id`` is +0). Writes are batched, one
    transaction per ``batch_size`` rows; nothing UPDATEs or DELETEs.

    Returns a JSON-able summary: M, the same_as / possibly_same counts, the
    resolved-organisation count, plus ``inserted`` / ``skipped_existing``.
    """
    if role:
        set_role(conn, role)
    recs = list(records) if records is not None else read_org_candidates(conn)
    result = plan_org_cascade(recs, context=context)
    if progress is not None:
        progress("resolved", len(result.decisions), 0)

    inserted = skipped = 0
    decisions = list(result.decisions)
    for start in range(0, len(decisions), batch_size):
        batch = decisions[start : start + batch_size]
        with conn.transaction():
            for d in batch:
                if conn.execute(_INSERT_MATCH, _decision_row(result, d)).fetchone():
                    inserted += 1
                else:
                    skipped += 1
        if progress is not None:
            progress("written", start + len(batch), inserted)

    summary = result.summary()
    execution = execution_id or str(_uuid.uuid4())
    with conn.transaction():
        run_inserted = (
            conn.execute(
                "INSERT INTO organization_run(run_key, ruleset_version, resolver_version, "
                " auto_link_tiers, organization_count, link_count, possibly_same_count, "
                " summary) "
                "VALUES (%s, %s, %s, %s::smallint[], %s, %s, %s, %s::jsonb) "
                "ON CONFLICT (run_key) DO NOTHING RETURNING run_key",
                (
                    result.run_key,
                    result.ruleset_version,
                    result.resolver_version,
                    sorted(AUTO_LINK_TIERS),
                    result.organization_count,
                    summary["same_as_pairs"],
                    summary["possibly_same_pairs"],
                    json.dumps(summary, sort_keys=True, default=str),
                ),
            ).fetchone()
            is not None
        )
        execution_appended = (
            conn.execute(
                "INSERT INTO organization_execution(execution_id, run_key, input_count, summary) "
                "VALUES (%s, %s, %s, %s::jsonb) "
                "ON CONFLICT (execution_id) DO NOTHING RETURNING execution_id",
                (
                    execution,
                    result.run_key,
                    result.organization_count,
                    json.dumps({**summary, "execution_id": execution}, sort_keys=True, default=str),
                ),
            ).fetchone()
            is not None
        )
    return {
        **summary,
        "inserted": inserted,
        "skipped_existing": skipped,
        "run_record_inserted": run_inserted,
        "execution_id": execution,
        "execution_appended": execution_appended,
    }


def materialize_org_cascade_from_dsn(dsn: str, **kwargs: Any) -> dict[str, Any]:
    """Open an autocommit connection from ``dsn`` and materialize (CLI convenience)."""
    import psycopg  # available via the sig-db dependency (driver stays in `db`)

    conn = psycopg.connect(dsn, autocommit=True)
    try:
        return materialize_org_cascade(conn, **kwargs)
    finally:
        conn.close()


def read_org_cascade_runs(conn: Any, *, role: str | None = None) -> list[dict[str, Any]]:
    """The latest COMPLETED organisation cascade run, as the read seam.

    Returns ``[]`` when no run has completed (the surface keeps its
    un-materialized framing — never a fabricated link count), else a
    one-element list: ``{run_key, ruleset_version, resolver_version,
    auto_link_tiers, organization_count, link_count, possibly_same_count,
    summary, links}`` where ``links`` carries each recorded pair's
    ``{left, right, relation_type, tier, disposition, evidence}`` row.
    Selection follows the LATEST completed execution (ADR-123): an A→B→A
    reversion re-executed under an old key still surfaces as the latest.
    """
    if role:
        set_role(conn, role)
    present = conn.execute(
        "SELECT to_regclass('public.organization_run') IS NOT NULL "
        "   AND to_regclass('public.organization_match') IS NOT NULL "
        "   AND to_regclass('public.organization_execution') IS NOT NULL"
    ).fetchone()[0]
    if not present:
        return []
    row = conn.execute(
        "SELECT run_key FROM organization_execution "
        " ORDER BY completed_at DESC, execution_id DESC LIMIT 1"
    ).fetchone()
    if row is None:
        row = conn.execute(
            "SELECT run_key FROM organization_run ORDER BY completed_at DESC, run_key DESC LIMIT 1"
        ).fetchone()
    if row is None:
        return []
    run_key = str(row[0])
    run = conn.execute(
        "SELECT run_key, ruleset_version, resolver_version, auto_link_tiers, "
        " organization_count, link_count, possibly_same_count, summary "
        "FROM organization_run WHERE run_key = %s",
        (run_key,),
    ).fetchone()
    if run is None:
        return []
    links = [
        {
            "left": str(le),
            "right": str(re_),
            "relation_type": str(rel),
            "tier": int(tier),
            "disposition": str(disp),
            "evidence": ev,
        }
        for le, re_, rel, tier, disp, ev in conn.execute(
            "SELECT left_entity::text, right_entity::text, relation_type, match_tier, "
            " disposition, match_evidence FROM organization_match "
            "WHERE run_key = %s ORDER BY left_entity, right_entity",
            (run_key,),
        ).fetchall()
    ]
    return [
        {
            "run_key": str(run[0]),
            "ruleset_version": str(run[1]),
            "resolver_version": str(run[2]),
            "auto_link_tiers": [int(t) for t in run[3]],
            "organization_count": int(run[4]),
            "link_count": int(run[5]),
            "possibly_same_count": int(run[6]),
            "summary": run[7],
            "links": links,
        }
    ]
