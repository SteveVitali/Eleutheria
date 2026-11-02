# SPDX-License-Identifier: Apache-2.0
"""The ``sig.entity-page/1`` record contract — ticket P36.41 (K2 §4.2/§6.2,
R11-K13-GX-05a, contract A).

The typed record shape every entity page renders from. Contract A covers the
E1 page kinds — organisations, agencies and registry portals — plus their
relationship rows and degree-only facts; contract B (P37.22, GX-05b) extends
the kind set and fills the 05b sections (notices/contracts/grants/bills/
instruments/events, timeline, contradictions, related). The 05b sections are
emitted here as typed empty values so the consumer's section list is stable
across both halves.

The laws the contract carries (K2 §7 honesty rules + §56.11 owner ids):

* A-10 (D-K2-1 = b + c, ADR-159 — the operator's word, never re-decided):
  an organisation matched by the registry auto-allow ADR gets an entity page
  (a keyed twin); every other organisation is typed ``not_yet_reviewed`` —
  a typed state, never a silent absence and never an improvised label.
  ``withheld`` entities and ``person`` entities emit nothing at all.
* H-2 / SIG-UI-115 — every relationship row carries the relation in words,
  direction, access kind, date + date kind (or ``undated``), the four
  epistemic fields as four separate fields (SIG-UI-004), the source names
  and the supporting claim ids.
* H-3 / SIG-UI-088 / SIG-UI-116 — historical and undated relationships are
  marked (``historical`` / ``date_kind == "undated"``), never present-tense.
* H-4 / SIG-UI-117 — degree-only facts are node attributes (``access.
  degree_only``), never drawn as edges and never emitted as relation items.
* SIG-UI-080 — where the publication gate withholds a counterparty (a
  withheld or unregistered partner entity), the twin sets
  ``withheld_notice`` to the mandated sentence and drops the row whole;
  no Part VIII withholding is named or counted.
* SIG-UI-053/108/110 — no raw identifier is a label; counterparties render
  the shared ``sig.entity-label/1`` label or a typed review state; every
  label carries its basis.
* SIG-EXPORT-014 — the exporter emits the twin per licence compartment the
  entity's facts license to (``web/entity/<url_type>/<key>/index.<comp>.json``),
  schema-registered so the release descriptor lists it.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from policy.labels import EntityLabel, sanitize_label
from policy.licensing import compute_export_license, export_refusal_reason
from policy.rights import RightsRecord
from resolution.partner_identity import natural_person_signal

from . import compartments as C

#: The emitted document schema (K2 §6.2, contract A).
ENTITY_PAGE_SCHEMA = "sig.entity-page/1"

#: Contract A's page kinds (GX-05a): organisations, agencies and registry
#: portals. Contract B (P37.22) appends the E2/E3 kinds; ``other``/``site``/
#: ``jurisdiction`` kinds are never entity-page kinds (sites are T0 records).
PAGE_KINDS: tuple[str, ...] = ("org", "agency", "portal")

#: The typed review states A-10 produces (labels' ``label_state`` vocabulary —
#: ADR-159). ``not_yet_reviewed`` is visible; ``withheld`` is absence.
REVIEW_NOT_YET_REVIEWED = "not_yet_reviewed"
REVIEW_WITHHELD = "withheld"

#: SIG-UI-080's mandated sentence, verbatim — where the publication gate
#: withholds organisations or relationships. Emitted whole, never re-worded.
WITHHELD_RELATIONSHIPS_NOTICE = "some relationships are not shown pending publication review"

#: The H-8 / SIG-UI-070 entity-resolution disclosure, verbatim — every entity
#: count and the page's count-bearing sections carry it (K2 §7 H-8).
ER_DISCLOSURE = (
    "SIG has not merged organisations across sources; one agency can appear more than once"
)

#: K2 §4.2 row 5 — relationship groups over 50 rows show the first 50 plus
#: the grouped counts and the "all N" posture (``more``).
ITEMS_PER_RELATION = 50
#: K2 §6.2 — each relation item carries at most 3 supporting claim ids.
CLAIM_IDS_PER_ITEM = 3

#: The epoch-zero placeholder a pre-P35.26 write stamped for "no recorded
#: date" — rendered ``undated``, never a real-looking date (SIG-TIME-012).
_EPOCH_DATE = "1970-01-01"

#: valid-to bound kinds meaning the edge's valid time has ENDED (the same
#: vocabulary ``spine_export``'s network edges mark historical on).
_ENDED_TO_KINDS: frozenset[str] = frozenset({"exact", "before", "after"})

#: ``reconcile.weight.currency`` C-codes → the web's currency words.
_CURRENCY_WORDS = {"C1": "CURRENT", "C2": "AGING", "C3": "STALE", "C4": "HISTORICAL"}

#: The degree-count predicate family (SIG-INGEST-043c / K2 §7 H-4) — a
#: source-stated partner COUNT, an attribute, never an edge. Mirrors
#: ``exports.shaping.SHARING_DEGREE_PREDICATES`` without the import cycle.
DEGREE_PREDICATES: frozenset[str] = frozenset({"sharing_partner_degree"})

#: The §12.2 access kinds — relation groups keep them strictly separate
#: (SIG-UI-024 / SIG-ONTO-042); a non-access entity-ref group carries
#: ``access_kind: null``.
ACCESS_KINDS: frozenset[str] = frozenset({"configured_access", "observed_use", "declared_policy"})

#: Page-state vocabulary — the A-10 decision surface.
PAGE_STATE_PUBLISHED = "published"
PAGE_STATE_NOT_YET_REVIEWED = "not_yet_reviewed"
PAGE_STATE_WITHHELD = "withheld"
#: Labelled, allowed, but not a contract-A page kind (contract B's scope —
#: a keyed entity with no twin here is a typed absence, never a broken page).
PAGE_STATE_UNPAGED = "unpaged"


def page_state(label: EntityLabel) -> str:
    """The A-10 page state for one ``sig.entity-label/1`` row.

    ``published`` — the registry auto-allow ADR matched (a keyed label in a
    contract-A kind); ``not_yet_reviewed`` — every other organisation (the
    typed state, never silent); ``withheld`` — no page, no node, ever;
    ``unpaged`` — an allowed label outside contract A's kind set (sibling
    scope, typed).
    """
    state = label.label_state
    if state == REVIEW_WITHHELD or label.kind == "person":
        return PAGE_STATE_WITHHELD
    if state == REVIEW_NOT_YET_REVIEWED:
        return PAGE_STATE_NOT_YET_REVIEWED
    if label.kind not in PAGE_KINDS:
        return PAGE_STATE_UNPAGED
    if not (label.slug and label.hash and label.url_type and label.url):
        # An allowed organisation with no issued key is the review-state
        # shape — the absence is typed, never a broken URL.
        return PAGE_STATE_NOT_YET_REVIEWED
    return PAGE_STATE_PUBLISHED


def review_record(label: EntityLabel) -> dict[str, Any]:
    """The typed ``not_yet_reviewed`` record for an un-keyed organisation.

    Carries no label, slug, hash, URL or entity id — the state IS the record
    (A-10 c + SIG-UI-108): a surface renders "Organisation · not yet
    reviewed", never an improvised name and never a raw identifier.
    """
    return {
        "schema": ENTITY_PAGE_SCHEMA,
        "review_state": REVIEW_NOT_YET_REVIEWED,
        "kind": label.kind,
        "descriptor": label.descriptor,
        "er_disclosure": ER_DISCLOSURE,
    }


# ---------------------------------------------------------------------------
# Claim rows — the ``entity_page_claims`` export seam's row shape.
# ---------------------------------------------------------------------------

#: ``(subject_id, predicate_id, value, claim_id, object_entity, observed_at,
#: source_id, spdx, attribution, redistributable, derivative_permitted,
#: terms_url, rights_id)`` — one row per publishable claim × bound source.
CLAIM_ROW_LEN = 13


@dataclass(frozen=True)
class PageClaim:
    """One publishable claim riding an entity page's twin."""

    subject_id: str
    predicate_id: str
    value: str | None
    claim_id: str
    object_entity: str | None
    observed_at: str | None
    source_id: str | None
    rights_id: str


def page_claims(rows: Sequence[Sequence[Any]]) -> dict[str, list[PageClaim]]:
    """Index ``entity_page_claims`` rows by subject id (deduped per claim)."""
    out: dict[str, dict[str, PageClaim]] = {}
    for row in rows:
        try:
            sid, pred = str(row[0]), str(row[1])
            val = None if row[2] is None else str(row[2])
            cid = str(row[3])
            obj = None if row[4] is None else str(row[4])
            obs = _norm_iso_date(row[5])
            src = None if row[6] is None else str(row[6])
            rid = str(row[12])
        except (TypeError, IndexError):
            continue
        claim = PageClaim(
            subject_id=sid,
            predicate_id=pred,
            value=val,
            claim_id=cid,
            object_entity=obj,
            observed_at=obs,
            source_id=src,
            rights_id=rid,
        )
        by_id = out.setdefault(sid, {})
        existing = by_id.get(cid)
        # A claim bound to a second source repeats as a row pair; the first
        # rights row stands (rights are per claim, not per source row).
        if existing is None or (existing.source_id is None and src is not None):
            by_id[cid] = claim
    return {sid: list(by_id.values()) for sid, by_id in out.items()}


def claim_source_map(rows: Sequence[Sequence[Any]]) -> dict[str, set[str]]:
    """``claim_id → bound source ids`` — sources accumulate across row pairs."""
    out: dict[str, set[str]] = {}
    for row in rows:
        try:
            cid, src = str(row[3]), row[6]
        except (TypeError, IndexError):
            continue
        if src:
            out.setdefault(cid, set()).add(str(src))
    return out


def claim_rights(rows: Sequence[Sequence[Any]], *, retrieval: date) -> dict[str, RightsRecord]:
    """``rights_id → RightsRecord`` over the entity-page claim rows."""
    out: dict[str, RightsRecord] = {}
    for row in rows:
        try:
            src, spdx, attr = str(row[6]), str(row[7]), str(row[8])
            redist, deriv, terms, rid = str(row[9]), str(row[10]), str(row[11]), str(row[12])
        except (TypeError, IndexError):
            continue
        out.setdefault(
            rid,
            RightsRecord(
                source_id=src,
                spdx=spdx,
                attribution=attr,
                redistributable=redist == "yes",
                derivative_permitted=deriv == "yes",
                terms_url=terms,
                retrieval_date=retrieval,
            ),
        )
    return out


def _norm_iso_date(value: Any) -> str | None:
    """An ISO ``YYYY-MM-DD`` date, or ``None`` for absence/epoch placeholder."""
    if value is None:
        return None
    d = value.date() if isinstance(value, datetime) else value
    text = d.isoformat() if isinstance(d, date) else str(value)[:10]
    return None if text == _EPOCH_DATE else text


def _currency_word(
    predicate_ids: Sequence[str], observed: str | None, as_of: date | None
) -> str | None:
    """The worst currency class across the item's predicates (§28.3-derived).

    ``UNDATED`` when no evidenced date exists; ``None`` when no predicate
    resolves or no as_of pins the snapshot — honest absence, never a guess.
    """
    if observed is None:
        return "UNDATED"
    if as_of is None:
        return None
    from reconcile.weight import currency, predicate_meta

    observed_d = date.fromisoformat(observed)
    classes: list[str] = []
    for pid in sorted(set(predicate_ids)):
        try:
            meta = predicate_meta(pid)
        except KeyError:
            continue
        classes.append(
            currency(
                volatility_class=str(meta.get("volatility_class", "")),
                half_life=str(meta.get("half_life", "")),
                observed_at=observed_d,
                as_of=as_of,
            )
        )
    if not classes:
        return None
    return _CURRENCY_WORDS[max(classes)]


def _support_word(claim_ids: Sequence[str], lineage: Mapping[str, str]) -> str:
    """The §10.7 support floor from declared independence classes — the same
    derivation the network edges carry (derived, never a constant)."""
    classes = {
        lineage.get(cid, "")
        for cid in claim_ids
        if lineage.get(cid) not in (None, "", "unclassified")
    }
    if len(classes) >= 2:
        return "STRONGLY_SUPPORTED"
    if claim_ids:
        return "WEAKLY_SUPPORTED"
    return "UNSUPPORTED"


def _resolution_fields(
    resolutions: Mapping[tuple[str, str], Mapping[str, Any]],
    subject_id: str,
    predicate_id: str,
) -> tuple[str | None, str | None]:
    """``(status, agreement)`` off the materialized envelope — ``None`` pair
    when no envelope was written (the typed absence, never a guessed one)."""
    env = resolutions.get((subject_id, predicate_id))
    if env is None:
        return None, None
    state = str(env.get("contradiction_state") or "")
    if env.get("resolved"):
        return "resolved", state or None
    if state in ("resolved_conflict", "unresolved_conflict"):
        return state, state
    return "unresolved", state or None


def _predicate_words(predicate_ids: Sequence[str], fallback: str = "") -> str:
    """The relation in words — unslugged predicate ids, never raw slot names."""
    words = sorted({p.replace("_", " ") for p in predicate_ids if p})
    return "; ".join(words) if words else fallback.replace("_", " ")


# ---------------------------------------------------------------------------
# Twin sections (contract A populates claims / relations / degree_only; the
# 05b sections emit as typed empty values so the record shape is stable).
# ---------------------------------------------------------------------------


def claim_groups(
    subject_id: str,
    claims: Sequence[PageClaim],
    *,
    resolutions: Mapping[tuple[str, str], Mapping[str, Any]],
    lineage: Mapping[str, str],
    source_names: Mapping[str, str],
    claim_sources: Mapping[str, set[str]],
    as_of: date | None,
) -> list[dict[str, Any]]:
    """ "What SIG records" — the subject's scalar claims grouped by predicate
    (K2 §4.2 row 4). Entity-ref claims (``object_entity`` set) are
    relationship inputs, not record facts; degree predicates are node
    attributes — both are filtered here, never double-counted."""
    by_pred: dict[str, list[PageClaim]] = {}
    for c in claims:
        if c.subject_id != subject_id or c.object_entity is not None:
            continue
        if c.predicate_id in DEGREE_PREDICATES:
            continue
        by_pred.setdefault(c.predicate_id, []).append(c)
    groups: list[dict[str, Any]] = []
    for pred, rows in sorted(by_pred.items()):
        claim_ids = sorted({c.claim_id for c in rows if c.claim_id})
        source_ids = sorted(
            {sid for cid in claim_ids for sid in claim_sources.get(cid, ())}
            | {c.source_id for c in rows if c.source_id}
        )
        values = sorted({v for v in (c.value for c in rows) if v not in (None, "")})
        observed_dates = sorted({d for d in (c.observed_at for c in rows) if d})
        observed = observed_dates[0] if observed_dates else None
        status, agreement = _resolution_fields(resolutions, subject_id, pred)
        groups.append(
            {
                "predicate": pred,
                "relation": _predicate_words([pred]),
                "envelope": {
                    "status": status,
                    "support": _support_word(claim_ids, lineage),
                    "agreement": agreement,
                    "currency": _currency_word([pred], observed, as_of),
                    "rationale": None,
                },
                "values": values,
                "observed_at": observed,
                "date_kind": "observed" if observed else "undated",
                "sources": [{"id": sid, "name": source_names.get(sid)} for sid in source_ids],
                "claim_ids": claim_ids,
            }
        )
    return groups


def _counterparty(
    entity_id: str,
    labels: Mapping[str, EntityLabel],
) -> tuple[dict[str, Any] | None, bool]:
    """``(counterparty, withheld)`` — the shared label or a typed state.

    A withheld/person partner or an entity the registry never published
    returns ``(None, True)`` — the row drops whole and the twin's
    ``withheld_notice`` carries SIG-UI-080's sentence (never a raw id,
    never a count). A not-yet-reviewed partner keeps its typed state.
    """
    lbl = labels.get(entity_id)
    if lbl is None:
        return None, True
    if lbl.label_state == REVIEW_WITHHELD or lbl.kind == "person":
        return None, True
    if lbl.label_state == REVIEW_NOT_YET_REVIEWED:
        return {
            "entity_id": entity_id,
            "kind": lbl.kind,
            "review_state": REVIEW_NOT_YET_REVIEWED,
            "label": None,
            "url": None,
        }, False
    # A counterparty outside contract A's page kinds carries its key for the
    # record/crosswalk seams but no entity-page URL (``unpaged`` — its own
    # page is a sibling scope; the consumer links its record or list row).
    url = lbl.url if lbl.kind in PAGE_KINDS else None
    return {
        "entity_id": entity_id,
        "kind": lbl.kind,
        "label": lbl.label,
        "label_basis": lbl.label_basis,
        "url": url,
        "key": f"{lbl.slug}--{lbl.hash}" if (lbl.slug and lbl.hash) else None,
    }, False


def _literal_counterparty(text: str) -> dict[str, Any] | None:
    """The display label for a source-stated literal partner, or ``None``
    (person-shaped or unlabelable text never surfaces — Part VIII, K2 §3.4)."""
    if natural_person_signal(text):
        return None
    label = sanitize_label(text)
    if not label:
        return None
    return {"label": label, "literal": True, "url": None}


def relation_groups(
    subject_id: str,
    claims: Sequence[PageClaim],
    *,
    edge_rows: Sequence[Mapping[str, Any]],
    labels: Mapping[str, EntityLabel],
    resolutions: Mapping[tuple[str, str], Mapping[str, Any]],
    lineage: Mapping[str, str],
    source_names: Mapping[str, str],
    claim_sources: Mapping[str, set[str]],
    as_of: date | None,
) -> tuple[list[dict[str, Any]], bool]:
    """ "Relationships" — one group per (relation, direction, access_kind)
    (K2 §4.2 row 5, H-2 fields; SIG-UI-115).

    Edges come from two seams joined on ``claim_id``: the entity-ref claims
    (outbound where the page entity is the subject, inbound where it is the
    object) and the materialized ``relationship`` rows (access-kind edges
    carrying the reconciled direction + valid bounds). Literal partners keep
    their stated text screened through the person screen; withheld or
    unregistered counterparties drop whole and return ``withheld=True``.
    """
    claim_by_id = {c.claim_id: c for c in claims}
    # Bucket key → {"relation","direction","access_kind","items":{cp→item}}.
    groups: dict[tuple[str, str, str | None], dict[str, Any]] = {}
    withheld = False

    def bucket(relation: str, direction: str, access_kind: str | None) -> dict[str, Any]:
        key = (relation, direction, access_kind)
        if key not in groups:
            groups[key] = {
                "relation": relation,
                "direction": direction,
                "access_kind": access_kind,
                "items": {},
            }
        return groups[key]

    def put(
        *,
        relation_predicates: Sequence[str],
        direction: str,
        access_kind: str | None,
        counterparty: dict[str, Any],
        claim_ids: Sequence[str],
        subjects: Sequence[str],
        observed: str | None,
        valid_to: str | None,
        valid_to_kind: str | None,
    ) -> None:
        relation = _predicate_words(relation_predicates, access_kind or "related")
        grp = bucket(relation, direction, access_kind)
        cp_key = str(
            counterparty.get("entity_id")
            or counterparty.get("key")
            or counterparty.get("label")
            or "unstated"
        )
        item = grp["items"].setdefault(
            cp_key,
            {
                "counterparty": counterparty,
                "claim_ids": [],
                "subjects": set(),
                "observed": [],
                "valid_to": valid_to,
                "valid_to_kind": valid_to_kind or "unknown",
                "predicates": set(),
            },
        )
        item["claim_ids"] = sorted(set(item["claim_ids"]) | set(claim_ids))
        item["subjects"].update(subjects)
        if observed:
            item["observed"].append(observed)
        item["predicates"].update(relation_predicates)
        if valid_to and (item["valid_to"] is None or valid_to < item["valid_to"]):
            item["valid_to"] = valid_to

    # --- entity-ref claims (both directions) ---------------------------------
    for c in claims:
        if c.predicate_id in DEGREE_PREDICATES:
            continue
        if c.object_entity == subject_id:
            # inbound: the row's SUBJECT is the counterparty.
            cp, drop = _counterparty(c.subject_id, labels)
            if drop:
                withheld = True
                continue
            assert cp is not None
            put(
                relation_predicates=[c.predicate_id],
                direction="inbound",
                access_kind=None,
                counterparty=cp,
                claim_ids=[c.claim_id],
                subjects=[c.subject_id],
                observed=c.observed_at,
                valid_to=None,
                valid_to_kind=None,
            )
        elif c.subject_id == subject_id and c.object_entity is not None:
            cp, drop = _counterparty(c.object_entity, labels)
            if drop:
                withheld = True
                continue
            assert cp is not None
            put(
                relation_predicates=[c.predicate_id],
                direction="outbound",
                access_kind=None,
                counterparty=cp,
                claim_ids=[c.claim_id],
                subjects=[c.subject_id],
                observed=c.observed_at,
                valid_to=None,
                valid_to_kind=None,
            )

    # --- materialized access edges -------------------------------------------
    for e in edge_rows or ():
        try:
            src, dst = str(e["from_entity"]), str(e["to_entity"])
            kind = str(e.get("access_kind") or "")
        except (KeyError, TypeError):
            continue
        if src != subject_id and dst != subject_id:
            continue
        direction = "outbound" if src == subject_id else "inbound"
        partner = dst if direction == "outbound" else src
        access_kind = kind if kind in ACCESS_KINDS else kind or None
        cp, drop = _counterparty(partner, labels)
        if drop:
            withheld = True
            continue
        assert cp is not None
        evidence = str(e.get("evidence_claim") or "")
        ev_claim = claim_by_id.get(evidence)
        predicates = sorted(
            {
                p
                for p in [
                    ev_claim.predicate_id if ev_claim else None,
                    str(e.get("edge_type") or ""),
                ]
                if p
            }
        )
        put(
            relation_predicates=predicates,
            direction=direction,
            access_kind=access_kind,
            counterparty=cp,
            claim_ids=[evidence] if evidence else [],
            subjects=[src],
            observed=_norm_iso_date(e.get("observed_at") or e.get("valid_from")),
            valid_to=_norm_iso_date(e.get("valid_to")),
            valid_to_kind=str(e.get("valid_to_kind") or "") or None,
        )

    # --- literal-partner claims (stated text, never an entity ref) -----------
    for c in claims:
        if c.subject_id != subject_id or c.object_entity is not None:
            continue
        if c.predicate_id in DEGREE_PREDICATES or not _is_access_predicate(c.predicate_id):
            continue
        text = c.value
        if text in (None, ""):
            continue
        cp = _literal_counterparty(str(text))
        if cp is None:
            withheld = True
            continue
        put(
            relation_predicates=[c.predicate_id],
            direction="outbound",
            access_kind=_access_kind_for(c.predicate_id),
            counterparty=cp,
            claim_ids=[c.claim_id],
            subjects=[c.subject_id],
            observed=c.observed_at,
            valid_to=None,
            valid_to_kind=None,
        )

    out: list[dict[str, Any]] = []
    for grp in groups.values():
        items: list[dict[str, Any]] = []
        for raw_item in grp["items"].values():
            claim_ids = sorted(raw_item["claim_ids"])[:CLAIM_IDS_PER_ITEM]
            observed_dates = sorted({d for d in raw_item["observed"] if d})
            observed = observed_dates[0] if observed_dates else None
            predicates = sorted(raw_item["predicates"])
            currency = _currency_word(predicates, observed, as_of)
            valid_to = raw_item["valid_to"]
            ended = valid_to is not None or raw_item["valid_to_kind"] in _ENDED_TO_KINDS
            status, agreement = _resolution_fields(
                resolutions,
                sorted(raw_item["subjects"])[0] if raw_item["subjects"] else subject_id,
                predicates[0] if predicates else "",
            )
            items.append(
                {
                    "counterparty": raw_item["counterparty"],
                    "relation": grp["relation"],
                    "role": predicates[0] if predicates else None,
                    "date": observed,
                    "date_kind": "observed" if observed else "undated",
                    "currency": currency,
                    "status": status,
                    "support": _support_word(claim_ids, lineage),
                    "agreement": agreement,
                    "sources": [
                        {"id": sid, "name": source_names.get(sid)}
                        for sid in sorted(
                            {s for cid in claim_ids for s in claim_sources.get(cid, ())}
                        )
                    ],
                    "claim_ids": claim_ids,
                    "historical": ended or currency == "HISTORICAL",
                }
            )
        items.sort(
            key=lambda i: (
                str(i["counterparty"].get("label") or ""),
                str(i["counterparty"].get("entity_id") or ""),
            )
        )
        out.append(
            {
                "relation": grp["relation"],
                "direction": grp["direction"],
                "access_kind": grp["access_kind"],
                "count": len(items),
                "items": items[:ITEMS_PER_RELATION],
                "more": max(0, len(items) - ITEMS_PER_RELATION),
                "claim_ids": sorted({cid for it in items for cid in it["claim_ids"]}),
            }
        )
    out.sort(key=lambda g: (g["relation"], g["direction"], g["access_kind"] or ""))
    return out, withheld


def _is_access_predicate(predicate_id: str) -> bool:
    """Sharing/access vocabulary — the literal-partner relation candidates."""
    p = predicate_id.lower()
    return "sharing" in p or "access" in p or p.endswith("_edge")


def _access_kind_for(predicate_id: str) -> str | None:
    """The §12.2 access kind a sharing predicate classifies to, or ``None`` —
    the same hint map ``reconcile.materialize`` owns (never coerced)."""
    p = predicate_id.lower()
    for hint, kind in (
        ("configured", "configured_access"),
        ("sharing_partner", "configured_access"),
        ("observed", "observed_use"),
        ("_use", "observed_use"),
        ("seen", "observed_use"),
        ("declared", "declared_policy"),
        ("policy", "declared_policy"),
        ("mou", "declared_policy"),
        ("agreement", "declared_policy"),
    ):
        if hint in p:
            return kind
    return None


def degree_only_facts(
    subject_id: str,
    claims: Sequence[PageClaim],
    *,
    source_names: Mapping[str, str],
    claim_sources: Mapping[str, set[str]],
    as_of: date | None,
) -> list[dict[str, Any]]:
    """The degree-only facts — source-stated partner COUNTS carried as node
    attributes ("Shared with N — partners not named", SIG-INGEST-043c / H-4 /
    SIG-UI-117). Never a relation item, never an edge."""
    rows = [c for c in claims if c.subject_id == subject_id and c.predicate_id in DEGREE_PREDICATES]
    if not rows:
        return []
    counts = sorted({int(c.value) for c in rows if c.value and str(c.value).strip().isdigit()})
    claim_ids = sorted({c.claim_id for c in rows if c.claim_id})
    observed_dates = sorted({d for d in (c.observed_at for c in rows) if d})
    observed = observed_dates[0] if observed_dates else None
    source_ids = sorted(
        {sid for cid in claim_ids for sid in claim_sources.get(cid, ())}
        | {c.source_id for c in rows if c.source_id}
    )
    predicates = sorted({c.predicate_id for c in rows})
    currency = _currency_word(predicates, observed, as_of)
    return [
        {
            "predicate": "; ".join(predicates),
            "counts": counts,
            "claim_ids": claim_ids,
            "observed_at": observed,
            "date_kind": "observed" if observed else "undated",
            "currency": currency,
            "historical": currency == "HISTORICAL",
            "sources": [{"id": sid, "name": source_names.get(sid)} for sid in source_ids],
        }
    ]


def summary_lines(relations: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """ "Summary" — one mechanical count sentence per relationship group, the
    K2 §4.2 row-2 shape: every number carries its group and claim pointers
    (a ``<Figure>`` input), never a fabricated narrative."""
    out: list[dict[str, Any]] = []
    for grp in relations:
        count = int(grp.get("count") or 0)
        if count <= 0:
            continue
        out.append(
            {
                "text": (
                    f"{count} recorded "
                    f"{'outbound' if grp['direction'] == 'outbound' else 'inbound'} "
                    f"relationship{'' if count == 1 else 's'} — "
                    f"{grp['relation']}"
                ),
                "value": count,
                "relation": grp["relation"],
                "direction": grp["direction"],
                "claim_ids": list(grp.get("claim_ids") or []),
            }
        )
    return out


# ---------------------------------------------------------------------------
# The twin + the per-compartment artifact map.
# ---------------------------------------------------------------------------


def build_twin(
    label: EntityLabel,
    *,
    publication: str,
    generated_at: str,
    compartment: str,
    entity_type: str | None,
    identifiers: Sequence[tuple[str, str]] = (),
    claims: Sequence[Mapping[str, Any]] = (),
    relations: Sequence[Mapping[str, Any]] = (),
    degree_only: Sequence[Mapping[str, Any]] = (),
    withheld_relationships: bool = False,
) -> dict[str, Any]:
    """One ``sig.entity-page/1`` twin (K2 §6.2, contract A).

    ``compartment`` is the file's licence compartment — the caller emits one
    filtered twin per compartment the entity's facts license to, so an ODbL
    claim never lands in a CC-BY file (ADR-106, SIG-EXPORT-014).
    """
    key = f"{label.slug}--{label.hash}"
    record_url = (
        f"/r/{publication}/c/{compartment}/entity/{entity_type}/{label.entity_id}/"
        if entity_type
        else None
    )
    return {
        "schema": ENTITY_PAGE_SCHEMA,
        "review_state": PAGE_STATE_PUBLISHED,
        "key": key,
        "entity_id": label.entity_id,
        "sig_id": label.sig_id,
        "kind": label.kind,
        "url_type": label.url_type,
        "url": label.url,
        "label": label.label,
        "descriptor": label.descriptor,
        "label_basis": label.label_basis,
        "label_source_id": label.label_source_id,
        "place_jkey": label.place_jkey,
        "disambiguator": label.disambiguator,
        "publication": publication,
        "generated_at": generated_at,
        "compartment": compartment,
        "identifiers": [
            {"scheme": scheme, "value": value} for scheme, value in sorted(set(identifiers))
        ],
        "summary": summary_lines(relations),
        "claims": list(claims),
        "relations": list(relations),
        "access": {
            # GX-07 (P37.21) computes the closures; contract A emits the
            # typed-empty slot so the record shape is stable across waves.
            "closures": [],
            "degree_only": list(degree_only),
        },
        # Contract-B sections (P37.22) — typed empty under contract A.
        "contradictions": [],
        "timeline": [],
        "related": {},
        "downloads": [],
        "cite": {
            "publication": publication,
            "url": label.url,
            "record_url": record_url,
            "sig_id": label.sig_id,
        },
        "withheld_notice": WITHHELD_RELATIONSHIPS_NOTICE if withheld_relationships else None,
        "er_disclosure": ER_DISCLOSURE,
    }


def _claim_compartment(
    claim: PageClaim,
    rights: Mapping[str, RightsRecord],
    *,
    registry: Mapping[str, Any] | None,
    default_compartment: str,
) -> str:
    """The licence compartment one claim's rights file under."""
    rec = rights.get(claim.rights_id)
    if rec is None or export_refusal_reason(rec, registry) is not None:
        return default_compartment
    try:
        licence = compute_export_license([rec], registry)
        comp = C.compartment_for_license(licence, None, registry)
    except Exception:  # noqa: BLE001 — a licence failure files to the default compartment
        return default_compartment
    return str(comp) if comp else default_compartment


def entity_page_artifacts(
    registry: Mapping[str, EntityLabel],
    *,
    claim_rows: Sequence[Sequence[Any]],
    edge_rows: Sequence[Mapping[str, Any]],
    identifiers: Mapping[str, Sequence[tuple[str, str]]],
    entity_types: Mapping[str, str],
    resolutions: Mapping[tuple[str, str], Mapping[str, Any]],
    lineage: Mapping[str, str],
    source_names: Mapping[str, str],
    entity_comps: Mapping[str, set[str]],
    default_compartment: str,
    publication: str,
    generated_at: str,
    as_of: date | None,
    retrieval: date,
    registry_license: Mapping[str, Any] | None = None,
) -> dict[str, tuple[dict[str, Any], str]]:
    """``path → (twin doc, compartment)`` for every published contract-A page.

    Per-compartment filing (SIG-EXPORT-014 / ADR-106): the entity files under
    every compartment its twin inputs (label facts + page claims) license to;
    each emitted twin carries only the claims / relation items / degree facts
    whose backing evidence licenses to that file's compartment — an ODbL
    claim never lands in a CC-BY twin.

    A ``withheld`` entity emits nothing; a ``not_yet_reviewed`` organisation
    emits nothing either — its typed state rides ``labels/<comp>.jsonl`` and
    :func:`review_record` for the index surfaces (no key, no URL, never a
    broken page); an ``unpaged`` kind emits nothing under contract A.
    """
    by_subject = page_claims(claim_rows)
    sources_of = claim_source_map(claim_rows)
    rights = claim_rights(claim_rows, retrieval=retrieval)
    # claim_id → compartment, so relation items file beside their evidence.
    claim_comp: dict[str, str] = {}
    for row_claims in by_subject.values():
        for c in row_claims:
            claim_comp[c.claim_id] = _claim_compartment(
                c, rights, registry=registry_license, default_compartment=default_compartment
            )

    artifacts: dict[str, tuple[dict[str, Any], str]] = {}
    for eid, label in sorted(registry.items()):
        if page_state(label) != PAGE_STATE_PUBLISHED:
            continue
        own = by_subject.get(eid, [])
        # inbound claims: every publishable claim whose object is this entity.
        inbound = [c for cs in by_subject.values() for c in cs if c.object_entity == eid]
        groups = claim_groups(
            eid,
            own,
            resolutions=resolutions,
            lineage=lineage,
            source_names=source_names,
            claim_sources=sources_of,
            as_of=as_of,
        )
        rel, withheld = relation_groups(
            eid,
            [*own, *inbound],
            edge_rows=edge_rows,
            labels=registry,
            resolutions=resolutions,
            lineage=lineage,
            source_names=source_names,
            claim_sources=sources_of,
            as_of=as_of,
        )
        degree = degree_only_facts(
            eid, own, source_names=source_names, claim_sources=sources_of, as_of=as_of
        )
        comps = set(entity_comps.get(eid) or {default_compartment})
        for c in own:
            comps.add(claim_comp.get(c.claim_id, default_compartment))
        for comp in sorted(comps):
            comp_claims = [
                g
                for g in groups
                if {claim_comp.get(cid, default_compartment) for cid in g["claim_ids"]} <= {comp}
            ]
            comp_rel = [
                {
                    **g,
                    "items": [
                        it
                        for it in g["items"]
                        if {claim_comp.get(cid, default_compartment) for cid in it["claim_ids"]}
                        <= {comp}
                    ],
                }
                for g in rel
            ]
            comp_rel = [g for g in comp_rel if g["items"]]
            comp_degree = [
                d
                for d in degree
                if {claim_comp.get(cid, default_compartment) for cid in d["claim_ids"]} <= {comp}
            ]
            doc = build_twin(
                label,
                publication=publication,
                generated_at=generated_at,
                compartment=comp,
                entity_type=entity_types.get(eid),
                identifiers=identifiers.get(eid, ()),
                claims=comp_claims,
                relations=comp_rel,
                degree_only=comp_degree,
                withheld_relationships=withheld,
            )
            path = f"web/entity/{label.url_type}/{label.slug}--{label.hash}/index.{comp}.json"
            artifacts[path] = (doc, comp)
    return artifacts


__all__ = [
    "ACCESS_KINDS",
    "CLAIM_IDS_PER_ITEM",
    "CLAIM_ROW_LEN",
    "DEGREE_PREDICATES",
    "ENTITY_PAGE_SCHEMA",
    "ER_DISCLOSURE",
    "ITEMS_PER_RELATION",
    "PAGE_KINDS",
    "PAGE_STATE_NOT_YET_REVIEWED",
    "PAGE_STATE_PUBLISHED",
    "PAGE_STATE_UNPAGED",
    "PAGE_STATE_WITHHELD",
    "REVIEW_NOT_YET_REVIEWED",
    "REVIEW_WITHHELD",
    "WITHHELD_RELATIONSHIPS_NOTICE",
    "PageClaim",
    "build_twin",
    "claim_groups",
    "claim_rights",
    "claim_source_map",
    "degree_only_facts",
    "entity_page_artifacts",
    "page_claims",
    "page_state",
    "relation_groups",
    "review_record",
    "summary_lines",
]
