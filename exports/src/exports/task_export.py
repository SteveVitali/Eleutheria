# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Task export v2 (P36.58 / R11-K13-RQ-01; K11 §3–§5, UXR-A11).

The research queue's v2 record shape. On top of the catalog-true base card
(`_research_queue`) this module adds what the recorded row and the shared
registries already know:

* **identity** — ``task_id`` plus the K11 §3 handle ``T-<place>-<code>-<slug>-<hash>``
  and a per-type title (SIG-RQ-001); codes and title templates come from the
  committed ``tasks/data/task_codes.toml`` registry, never invented text;
* **the gap named** — ``predicate_ids`` resolved from the task's recorded
  trigger (the materialized coverage/contradiction the detector cites), plus
  the trigger's own detail — never a fabricated predicate (SIG-RQ-005);
* **real labels** — the subject's public label/url from the ONE label
  derivation (P35.29 ``label_registry``), or the typed ``<kind> #<hash4>``
  fallback — never a raw UUID (SIG-RQ-003, L-2);
* **jurisdiction attribution** — K11 §4.3's order: the recorded jurisdiction
  resolved to a registry key → the subject's own resolved place → the dossier
  placement leaf → the agenda/procurement tenant's registered jurisdiction →
  the honest ``unplaced`` bucket, each basis named on the card;
* **lanes (SIG-RQ-006 / D-K11-1)** — per-object field gaps route through the
  committed ``gap_routing.toml`` table: OSM-mappable predicates aggregate into
  ``M-`` campaigns by (place, predicate); registry-only fields stay out of the
  queue surface entirely (coverage metrics carry them) and their count is
  named in ``queue_meta`` — never silently dropped;
* **shards** — ``web/tasks/<lane>/<place>.jsonl.gz`` per lane and place, each
  part ≤ ``SHARD_MAX_BYTES`` (SIG-RQ-010), byte-deterministic (mtime=0 gzip);
* **``web/task_handles_history.json``** — the handle-history artifact the
  redirect generator (P36.35/JUR-05) reads: every ``/task/<uuid>/`` id-alias
  plus the (empty-first-release) rename history.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from inference.peer_classes import load_peer_classes
from policy.labels import EntityLabel, entity_hash, hash4
from tasks.routing import TaskCodes

from . import dossier_keys, downloads
from .jurisdictions import jurisdiction_slug
from .watch import _tenant_for, _tenant_jurisdictions

#: The v2 card schema id — additive over the P34.12 card (new optional fields).
CARD_SCHEMA = "sig.queue-card/2"
#: The campaign row schema id (SIG-RQ-006 aggregated field gaps).
CAMPAIGN_SCHEMA = "sig.queue-campaign/1"
#: The handle-history artifact schema (the `*_handles_history.json` family the
#: JUR-05 redirect generator scans — ``web/src/lib/data.ts#getHandleHistories``).
HANDLES_HISTORY_SCHEMA = "sig.handles-history/1"
#: The queue_meta envelope v2 (P36.58 — lanes, facets, the shard index).
QUEUE_META_SCHEMA = "sig/analytics-queue-meta/2"

#: SIG-RQ-010 — no single queue file larger than 25 MB.
SHARD_MAX_BYTES = 25 * 1024 * 1024
#: K11 §3 — the handle is ≤ 64 chars; the hash is 4 chars extended to 5…8 on a
#: collision within the release.
HANDLE_MAX = 64
HASH_MIN, HASH_MAX = 4, 8
SLUG_MAX = 24

_UNPLACED = dossier_keys.UNPLACED

#: The closed lane vocabulary (mirrors ``tasks.routing.LANES``).
LANES: tuple[str, ...] = ("research", "campaign", "metric")

#: Trailing LSAD designations the place segment drops for municipality-level
#: leaves only (K11 §3 — counties keep "county").
_LSAD_DROP: frozenset[str] = frozenset(
    {"city", "town", "village", "cdp", "borough", "municipality"}
)

#: Org-suffix abbreviations (K11 §3 — token-pair replacements applied before
#: the 24-char cut; ``sheriff's office`` folds to ``sheriff s office``).
_ORG_ABBREVIATIONS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("police", "department"), "pd"),
    (("sheriff", "s", "office"), "so"),
    (("sheriffs", "office"), "so"),
    (("sheriff", "office"), "so"),
    (("department", "of"), "dept"),
    (("county",), "co"),
)

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE
)


def _tokens(text: str) -> list[str]:
    """ASCII-folded ``[a-z0-9]+`` tokens (K11 §3's slug alphabet)."""
    folded = unicodedata.normalize("NFKD", str(text))
    ascii_text = folded.encode("ascii", "ignore").decode("ascii")
    return _TOKEN_RE.findall(ascii_text.lower())


@dataclass
class QueueBuild:
    """Everything the v2 queue emit produces for one export snapshot."""

    cards: list[dict[str, Any]] = field(default_factory=list)  # research lane
    campaigns: list[dict[str, Any]] = field(default_factory=list)
    metric_members: int = 0  # per-object field gaps held to coverage metrics
    shards: dict[str, bytes] = field(default_factory=dict)  # path → jsonl.gz
    handles_history: dict[str, Any] = field(default_factory=dict)
    summary: dict[str, Any] = field(default_factory=dict)  # queue_meta v2 fields


# --------------------------------------------------------------------------- #
# Handle pieces (K11 §3)
# --------------------------------------------------------------------------- #


def place_segment(jkey: str | None, keyed: dossier_keys.KeyedRegistry | None) -> str:
    """The handle's ``<place>`` — the K4 display-slug path joined with "-".

    GEOID suffixes drop (``acworth-30136`` → ``acworth``); a municipality-level
    leaf drops a *trailing* LSAD designation (``city/town/village/cdp``) only
    when the registry name does not itself end with that word — "Oklahoma City"
    keeps its name, "Acworth city" becomes ``acworth``; counties keep
    ``county`` (K11 §3 verbatim). Unplaced/unkeyed resolves to ``unplaced``.
    """
    if not jkey or keyed is None:
        return _UNPLACED
    info = keyed.keys.get(jkey)
    if info is None:
        return _UNPLACED
    parts: list[str] = []
    for seg in info.slug_path.split("/"):
        # ``name-<geoid>`` → ``name`` (the canonical code tail is numeric for
        # census-keyed leaves; admin-1 segments carry letters and pass through).
        m = re.match(r"^(.+)-\d+$", seg)
        parts.append(m.group(1) if m else seg)
    if info.level == "municipality" and len(parts) > 1:
        name_tokens = _tokens(info.name)
        leaf = parts[-1].split("-")
        if leaf and leaf[-1] in _LSAD_DROP and (not name_tokens or name_tokens[-1] != leaf[-1]):
            leaf = leaf[:-1]
            parts[-1] = "-".join(leaf)
    return "-".join(p for p in parts if p) or _UNPLACED


def handle_slug(label: str, place_segment_: str) -> str | None:
    """The handle's ``<slug>`` — the subject label per K11 §3.

    ASCII-fold → tokens → drop tokens equal to the place's last component →
    org-suffix abbreviations → join with "-" → cut at ``SLUG_MAX`` on a token
    boundary. ``None`` when nothing survives (the handle omits the segment).
    """
    tokens = _tokens(label)
    if not tokens:
        return None
    place_tail = place_segment_.rsplit("-", 1)[-1]
    tokens = [t for t in tokens if t != place_tail]
    out: list[str] = []
    i = 0
    while i < len(tokens):
        replaced = False
        for words, abbrev in _ORG_ABBREVIATIONS:
            n = len(words)
            if tuple(tokens[i : i + n]) == words:
                out.append(abbrev)
                i += n
                replaced = True
                break
        if not replaced:
            out.append(tokens[i])
            i += 1
    slug = "-".join(out)
    if len(slug) > SLUG_MAX:
        cut = slug[:SLUG_MAX]
        slug = cut[: cut.rfind("-")] if "-" in cut else cut
    return slug or None


def mint_handle(
    kind: str,
    place_seg: str,
    code: str,
    slug: str | None,
    object_id: str,
    *,
    hash_len: int = HASH_MIN,
) -> str:
    """``<kind>-<place>-<code>-<slug>-<hash>`` — the §3 grammar, ≤ 64 chars.

    ``slug`` is omitted when empty (``T-usa-ok-retention-q1c4``); the hash is
    Crockford base32 of sha256(canonical id text) — collision extension is the
    caller's pass (:func:`resolve_handle_hashes`)."""
    digest = entity_hash(str(object_id), length=hash_len)
    parts = [kind, place_seg, code] + ([slug] if slug else []) + [digest]
    return "-".join(parts)


def resolve_handle_hashes(entries: list[dict[str, Any]], *, key: str = "handle") -> None:
    """Extend colliding handles' hashes in place (4 → 5…8), deterministic.

    ``entries`` carry ``key`` plus ``_object_id`` — the canonical id the hash
    derives from (task_id / campaign group key). A group that cannot separate
    at ``HASH_MAX`` keeps the longest form and is still unique by object id —
    an over-collision is a registry defect a test can never silently miss
    (the emitted set is asserted unique at build end)."""
    for length in range(HASH_MIN, HASH_MAX + 1):
        groups: dict[str, list[dict[str, Any]]] = {}
        for e in entries:
            handle = mint_handle(
                e["_kind"],
                e["_place"],
                e["_code"],
                e.get("_slug"),
                e["_object_id"],
                hash_len=length,
            )
            e[key] = handle
            groups.setdefault(handle, []).append(e)
        collisions = [g for g in groups.values() if len(g) > 1]
        if not collisions:
            return
        if length == HASH_MAX:
            break
        # keep only the collided entries for the next length (non-collided are frozen)
        entries = [e for g in collisions for e in g]
    seen: set[str] = set()
    for e in entries:
        seen.add(e[key])


def _type_code(task_type: str, codes: TaskCodes) -> str:
    """The handle's one-token code — the registry's, or the type's own first
    token for a legacy/uncatalogued type ([a-z]{2,10} enforced by truncation)."""
    entry = codes.by_type.get(task_type)
    if entry is not None:
        return entry.code
    tokens = [t for t in _tokens(task_type) if t.isalpha()]
    return ("".join(tokens))[:10] or "task"


# --------------------------------------------------------------------------- #
# Labels, triggers, attribution
# --------------------------------------------------------------------------- #


def _subject_label(
    subject_id: str, labels: Mapping[str, EntityLabel]
) -> tuple[str, str | None, str | None]:
    """``(label, url, subject_key)`` — the ONE derivation's row, else the typed
    fallback (``Record #<hash4>`` — L-2: never a raw UUID or a bare id)."""
    row = labels.get(subject_id)
    if row is not None:
        if row.label:
            return row.label, row.url, row.subject_key
        if row.descriptor:
            return row.descriptor, row.url, row.subject_key
    if subject_id:
        return f"Record #{hash4(subject_id)}", None, subject_id if ":" in subject_id else None
    return "Record", None, None


def _trigger_lookup(raw: Mapping[str, Any]) -> dict[tuple[str, str], Mapping[str, Any]]:
    """``(kind, ref) → materialized row`` for trigger detail + predicate.

    P37.32 (K7 WX-06): a ``contract`` trigger resolves against the
    ``watch_claims`` read — the ref is the firing ``end_date`` claim id the
    ``contract_expiring`` detector cited, and the row is that claim itself.
    """
    out: dict[tuple[str, str], Mapping[str, Any]] = {}
    for r in raw.get("materialized_coverage") or ():
        if isinstance(r, Mapping) and r.get("coverage_id"):
            out[("coverage", str(r["coverage_id"]))] = r
    for r in raw.get("materialized_contradictions") or ():
        if isinstance(r, Mapping) and r.get("contradiction_id"):
            out[("contradiction", str(r["contradiction_id"]))] = r
    for r in raw.get("materialized_edges") or ():
        if isinstance(r, Mapping) and r.get("relationship_id"):
            out[("relationship", str(r["relationship_id"]))] = r
    # Contract claims — ``watch_claims`` rows keyed by claim_id, positional or
    # mapping shaped (the read emits tuples; fixtures may carry dicts).
    for r in raw.get("watch_claims") or ():
        try:
            if isinstance(r, Mapping):
                row = r
            else:
                row = dict(zip(watch_claim_columns(), r, strict=False))
            cid = row.get("claim_id")
            if not cid:
                continue
            out[("contract", str(cid))] = {
                "claim_id": str(cid),
                "subject_key": row.get("subject_key"),
                "predicate_id": row.get("predicate_id"),
                "end_date": row.get("value_text") or row.get("raw_value"),
                "observed_at": row.get("observed_at"),
                "source_id": row.get("source_id"),
            }
        except (TypeError, AttributeError):
            continue
    return out


def watch_claim_columns() -> tuple[str, ...]:
    """The ``watch_claims`` column order (``exports.watch.WATCH_CLAIMS_COLUMNS``),
    looked up lazily so the shared constant stays the single authority."""
    from .watch import WATCH_CLAIMS_COLUMNS

    return WATCH_CLAIMS_COLUMNS


def _trigger_detail(
    kind: str, ref: str, lookup: Mapping[tuple[str, str], Mapping[str, Any]]
) -> dict[str, Any]:
    """The trigger's own recorded detail, by kind — coverage names its
    predicate + absence kind + search state; a contradiction its type +
    severity; a relationship edge its access kind + observation dates; a
    contract trigger (P37.32) the firing ``end_date`` claim — the recorded
    end the task asks about."""
    row = lookup.get((kind, ref))
    if row is None:
        return {"resolves": False}
    if kind == "contract":
        out = {
            "resolves": True,
            "predicate_id": row.get("predicate_id"),
            "end_date": row.get("end_date"),
            "subject_key": row.get("subject_key"),
            "observed_at": row.get("observed_at"),
            "source_id": row.get("source_id"),
        }
    elif kind == "coverage":
        out = {
            "resolves": True,
            "predicate_id": row.get("predicate_id"),
            "absence_kind": row.get("absence_kind"),
            "searched_at": row.get("searched_at"),
            "subject_class": row.get("subject_class"),
        }
        searched = [str(s) for s in (row.get("sources_searched") or ()) if s]
        if searched:
            out["sources_searched"] = searched
    elif kind == "contradiction":
        out = {
            "resolves": True,
            "predicate_id": row.get("predicate_id"),
            "contradiction_type": row.get("contradiction_type"),
            "severity": row.get("severity"),
            "status": row.get("status"),
        }
    else:  # relationship
        out = {
            "resolves": True,
            "access_kind": row.get("access_kind"),
            "edge_type": row.get("edge_type"),
            "observed_at": row.get("observed_at"),
            "valid_from": row.get("valid_from"),
            "valid_to": row.get("valid_to"),
            "to_entity": row.get("to_entity"),
        }
    return {k: v for k, v in out.items() if v not in (None, "")}


def _jkey_of(
    value: str,
    labels: Mapping[str, EntityLabel],
    keyed: dossier_keys.KeyedRegistry | None,
    slug_map: Mapping[str, str],
) -> str | None:
    """Resolve a recorded jurisdiction value to a canonical registry key — by
    the registry itself, the label row's place key, the ``jurisdiction:<key>``
    subject form, or the legacy-slug map. ``None`` is honest non-resolution."""
    if not value:
        return None
    if keyed is not None:
        if value in keyed.keys:
            return value
        if value.startswith("jurisdiction:"):
            tail = value.split(":", 1)[1]
            tail = tail.replace("iso.3166-1:", "iso3166-1:").replace("iso.3166-2:", "iso3166-2:")
            if tail in keyed.keys:
                return tail
        row = labels.get(value)
        if row is not None and row.place_jkey in keyed.keys:
            return str(row.place_jkey)
    mapped = slug_map.get(value)
    if mapped and (keyed is None or mapped in keyed.keys):
        return mapped
    return None


def _tenant_jkey(
    subject_key: str | None,
    keyed: dossier_keys.KeyedRegistry | None,
) -> tuple[str | None, str | None]:
    """§4.3 step 3 — the agenda/procurement tenant's registered jurisdiction,
    resolved to a registry key by exact name match (ambiguous → None)."""
    tenant = _tenant_for(subject_key) if subject_key else None
    if not tenant or keyed is None:
        return None, tenant
    name = _tenant_jurisdictions().get(tenant)
    if not name:
        return None, tenant
    folded = {info.name.casefold(): jkey for jkey, info in keyed.keys.items()}
    return folded.get(name.casefold()), tenant


def _place_of(
    jkey: str | None,
    recorded: str,
    keyed: dossier_keys.KeyedRegistry | None,
) -> dict[str, Any]:
    """The card's ``place`` object — the canonical slug + display name, or the
    honest ``unplaced`` bucket (never a guessed path)."""
    if jkey and keyed is not None and jkey in keyed.keys:
        info = keyed.keys[jkey]
        return {"key": jkey, "slug": info.slug_path, "name": keyed.display_name(jkey)}
    if jkey:
        return {"key": jkey, "slug": jurisdiction_slug(jkey), "name": jkey}
    if recorded:
        return {"key": None, "slug": jurisdiction_slug(recorded), "name": recorded}
    return {"key": None, "slug": _UNPLACED, "name": "Not yet placed"}


def _title(
    task_type: str,
    subject_label: str,
    trigger_date: str | None,
    codes: TaskCodes,
) -> str:
    """The per-type title — the registry template rendered, or the honest
    ``<type label>: <subject>`` form (never a placeholder literal)."""
    entry = codes.by_type.get(task_type)
    label = entry.label if entry is not None else task_type.replace("_", " ")
    if entry is None:
        return f"{label}: {subject_label}"
    text = entry.title
    if "{date}" in text:
        if not trigger_date:
            return f"{label}: {subject_label}"
        text = text.replace("{date}", trigger_date[:10])
    return text.replace("{subject}", subject_label)


# --------------------------------------------------------------------------- #
# The build
# --------------------------------------------------------------------------- #


def _peer_entity_types() -> frozenset[str]:
    """The §32.1 peer-class entity types — a coverage row whose subject_class
    is one of these is a per-object (field-gap) row, never a place aggregate."""
    return frozenset(pc.entity_type for pc in load_peer_classes())


def _campaign_slug(predicate: str) -> str:
    """The campaign code — the field name itself (K11 §3's campaign row)."""
    tokens = [t for t in _tokens(predicate) if t.isalpha()]
    return ("_".join(tokens))[:24] or "field"


def build_queue(
    cards: Sequence[Mapping[str, Any]],
    raw: Mapping[str, Any],
    *,
    label_registry: Mapping[str, EntityLabel],
    keyed: dossier_keys.KeyedRegistry | None,
    slug_map: Mapping[str, str],
    leaf_by_subject: Mapping[str, str],
    routing: Mapping[str, Any],
    codes: TaskCodes,
    generated_at: str,
    watch_items_by_subject: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> QueueBuild:
    """Enrich the base cards into the v2 queue + shards + meta (pure).

    ``cards`` are the catalog-true ``_research_queue`` rows (already
    ``_rekey_queue_cards``-processed when the caller keys dossiers); ``raw``
    supplies the materialized trigger rows; ``leaf_by_subject`` is the dossier
    accumulation's ``subject → leaf jkey`` map (empty pre-placement).
    ``watch_items_by_subject`` (P37.32 / K7 WX-06) maps a watch item's subject
    key to the emitted ``sig.watch-item/1`` rows about it — the task ↔ item
    link (K7 §5.8): a card whose subject has a watch item links the item's own
    emitted handle, never a re-derived one.
    """
    lookup = _trigger_lookup(raw)
    peer_types = _peer_entity_types()
    out = QueueBuild()
    _card_coverage_refs: set[str] = set()  # coverage ids a card member already counts

    # -- pass 1: enrich + lane ------------------------------------------------ #
    field_gap_members: list[dict[str, Any]] = []  # (card, coverage row, route)
    for card_in in cards:
        card = dict(card_in)
        subject_id = str(card.get("subject_id") or "")

        # trigger detail + predicate (SIG-RQ-005 — the gap named, or the honest
        # "no resolvable trigger" absence for legacy/hand-inserted rows).
        trig = card.get("trigger") or {}
        kind, ref = str(trig.get("kind") or ""), str(trig.get("ref") or "")
        detail: dict[str, Any] = {}
        predicate_ids: list[str] = []
        trigger_row: Mapping[str, Any] | None = None
        if kind and ref:
            detail = _trigger_detail(kind, ref, lookup)
            trigger_row = lookup.get((kind, ref))
            pred = detail.get("predicate_id")
            if pred:
                predicate_ids = [str(pred)]
            card["trigger"] = {"kind": kind, "ref": ref, "detail": detail}
        # P37.35: the row's recorded predicate_ids win (SIG-RQ-005 — the set
        # the task seeks); the trigger-resolved predicate is the fallback.
        stored = card.get("predicate_ids")
        card["predicate_ids"] = [str(p) for p in stored] if stored else predicate_ids

        # recorded state + provenance the detail page's History block reads.
        card["status"] = str(card.get("status") or "generated")
        if card.get("disposition"):
            card["disposition"] = str(card["disposition"])
        else:
            card.pop("disposition", None)
        if card.get("generated_at"):
            card["generated_at"] = str(card["generated_at"])
        else:
            card.pop("generated_at", None)
        card["detector_version"] = str(card.get("detector_version") or "")

        # real label + the K2 page link (SIG-RQ-003; L-2 fallback never a UUID).
        label, url, subject_key = _subject_label(subject_id, label_registry)
        card["subject_label"] = label
        if url:
            card["subject_url"] = url

        # P37.32 (K7 WX-06 / §5.8): the task ↔ item link — the emitted watch
        # item(s) on the SAME subject (the renewal-terms task pairs with the
        # contract_expiry item; any other subject-matched item links the same
        # way). The emitted handle is authoritative — never re-derived.
        if watch_items_by_subject and subject_key:
            wi = [
                {
                    "handle": str(w.get("handle") or ""),
                    "kind": str(w.get("kind") or ""),
                    "title": str(w.get("title") or ""),
                }
                for w in watch_items_by_subject.get(subject_key) or ()
                if w.get("handle")
            ]
            if wi:
                card["watch_items"] = wi

        # jurisdiction attribution (K11 §4.3 order, basis named).
        recorded_jur = str(card.get("jurisdiction") or "")
        jkey, basis = _jkey_of(recorded_jur, label_registry, keyed, slug_map), None
        if jkey:
            basis = "task_jurisdiction"
        elif (row := label_registry.get(subject_id)) is not None and row.place_jkey:
            jkey, basis = str(row.place_jkey), "subject_place"
        elif leaf_by_subject.get(subject_id):
            jkey, basis = leaf_by_subject[subject_id], "dossier_placement"
        else:
            t_jkey, _tenant = _tenant_jkey(subject_key, keyed)
            if t_jkey:
                jkey, basis = t_jkey, "tenant"
        if jkey:
            card["jurisdiction"] = jkey
            card["place_basis"] = basis
        else:
            card["place_basis"] = "recorded" if recorded_jur else _UNPLACED
        card["place"] = _place_of(jkey, recorded_jur, keyed)

        # P37.35 (RQ-02): a closed/invalidated or superseded row is not open
        # work — it leaves every public lane (the row stays on the spine for
        # history; the campaign/metric gap it named still aggregates below
        # from the materialized coverage rows themselves).
        if card["status"] in ("closed", "invalidated") or card.get("disposition") == "superseded":
            continue

        # lane (SIG-RQ-006 / D-K11-1): a per-object coverage field gap follows
        # the routing table — OSM-mappable predicates aggregate into campaigns;
        # registry-only fields stay in coverage metrics, not the queue.
        lane = "research"
        if (
            kind == "coverage"
            and trigger_row is not None
            and str(trigger_row.get("subject_class") or "") in peer_types
            and trigger_row.get("subject_id")
        ):
            pred = str(trigger_row.get("predicate_id") or "")
            routed = routing.get(pred)
            if routed is not None and routed.lane in ("campaign", "metric"):
                lane = routed.lane
                field_gap_members.append({"card": card, "coverage": trigger_row, "route": routed})
                _card_coverage_refs.add(str(trigger_row.get("coverage_id") or ref))
        card["lane"] = lane
        if lane == "metric":
            out.metric_members += 1
            continue
        if lane == "research":
            out.cards.append(card)

    # -- pass 2: campaign aggregation (SIG-RQ-006) ----------------------------- #
    groups: dict[tuple[str | None, str, str], list[dict[str, Any]]] = {}
    for member in field_gap_members:
        if member["card"]["lane"] != "campaign":
            continue
        card = member["card"]
        pred = str(member["coverage"].get("predicate_id") or "")
        sclass = str(member["coverage"].get("subject_class") or "")
        place_key = (card.get("place") or {}).get("key")
        groups.setdefault((place_key, pred, sclass), []).append(member)

    # P37.35 (RQ-02): campaigns aggregate from the materialized coverage rows
    # themselves — the per-object gap set, independent of which research_task
    # rows were minted (the superseded per-camera rows stay history). A subject
    # already carried by a card member is never double-counted.
    for cov in raw.get("materialized_coverage") or ():
        if not isinstance(cov, Mapping):
            continue
        if str(cov.get("absence_kind") or "") not in ("not_researched", "searched_not_found"):
            continue
        sclass = str(cov.get("subject_class") or "")
        subj = str(cov.get("subject_id") or "")
        if sclass not in peer_types or not subj:
            continue
        if str(cov.get("coverage_id") or "") in _card_coverage_refs:
            continue  # a card member already counts this gap — never double
        pred = str(cov.get("predicate_id") or "")
        routed = routing.get(pred)
        if routed is None or routed.lane != "campaign":
            if routed is not None and routed.lane == "metric":
                out.metric_members += 1
            continue
        jur = str(cov.get("jurisdiction_id") or "")
        jkey = _jkey_of(jur, label_registry, keyed, slug_map)
        if not jkey:
            row = label_registry.get(subj)
            if row is not None and row.place_jkey:
                jkey = str(row.place_jkey)
            else:
                jkey = leaf_by_subject.get(subj)
        label, url, _sk = _subject_label(subj, label_registry)
        groups.setdefault((jkey, pred, sclass), []).append(
            {
                "coverage": cov,
                "card": {
                    "lane": "campaign",
                    "subject_id": subj,
                    "subject_label": label,
                    **({"subject_url": url} if url else {}),
                    "coverage_id": str(cov.get("coverage_id") or ""),
                },
            }
        )
    for members in groups.values():
        seen_subj: set[str] = set()
        deduped: list[dict[str, Any]] = []
        for m in members:
            s = str(m["card"].get("subject_id") or "")
            if s and s not in seen_subj:
                seen_subj.add(s)
                deduped.append(m)
        members[:] = deduped

    campaign_entries: list[dict[str, Any]] = []
    for (place_key, pred, sclass), members in sorted(
        groups.items(), key=lambda kv: (str(kv[0][0]), kv[0][1], kv[0][2])
    ):
        members_cards = [m["card"] for m in members]
        group_key = f"{place_key or _UNPLACED}|{pred}|{sclass}"
        place = _place_of(place_key, "", keyed)
        campaign_entries.append(
            {
                "_kind": "M",
                "_place": place_segment(place_key, keyed),
                "_code": _campaign_slug(pred),
                "_slug": None,
                "_object_id": f"campaign:{group_key}",
                "schema": CAMPAIGN_SCHEMA,
                "kind": "campaign",
                "predicate_id": pred,
                "subject_class": sclass,
                "place": place,
                "member_count": len(members_cards),
                "members": [
                    {
                        "task_id": str(c.get("task_id") or ""),
                        "subject_id": str(c.get("subject_id") or ""),
                        "subject_label": str(c.get("subject_label") or ""),
                        **({"subject_url": c["subject_url"]} if c.get("subject_url") else {}),
                    }
                    for c in sorted(members_cards, key=lambda c: str(c.get("subject_id") or ""))
                ],
                "contribution": {
                    "kind": "osm-field-gap",
                    "note": "a field-level mapping gap on individual records, aggregated",
                },
            }
        )
    resolve_handle_hashes(campaign_entries)
    for e in campaign_entries:
        for k in ("_kind", "_place", "_code", "_slug", "_object_id"):
            e.pop(k, None)
        out.campaigns.append(e)

    # -- pass 3: handles + titles for the research lane (SIG-RQ-001) ------------ #
    entries = []
    for card in out.cards:
        place_seg = (
            place_segment(card["place"]["key"], keyed)
            if card["place"].get("key")
            else (
                card["place"]["slug"].replace("/", "-")
                if card["place"]["slug"] != _UNPLACED
                else _UNPLACED
            )
        )
        slug = handle_slug(str(card["subject_label"]), place_seg)
        entries.append(
            {
                "_kind": "T",
                "_place": place_seg,
                "_code": _type_code(str(card["task_type"]), codes),
                "_slug": slug,
                "_object_id": f"task:{card['task_id'] or card['subject_id']}",
                "_card": card,
            }
        )
    resolve_handle_hashes(entries)
    for e in entries:
        card = e["_card"]
        card["handle"] = e["handle"]
        trig_detail = (card.get("trigger") or {}).get("detail") or {}
        date = (
            trig_detail.get("end_date")
            or trig_detail.get("searched_at")
            or trig_detail.get("observed_at")
            or trig_detail.get("valid_from")
            or card.get("generated_at")
        )
        card["title"] = _title(
            str(card["task_type"]), str(card["subject_label"]), str(date) if date else None, codes
        )
        for k in ("_kind", "_place", "_code", "_slug", "_object_id", "_card"):
            e.pop(k, None)

    # -- pass 4: lane/place shards --------------------------------------------- #
    def _jsonl_gz(rows: Sequence[Mapping[str, Any]]) -> bytes:
        body = "".join(
            downloads.json.dumps(r, sort_keys=True, separators=(",", ":")) + "\n" for r in rows
        )
        return downloads._gzip(body.encode("utf-8"))

    def _emit_shards(
        lane: str, rows_by_place: dict[str, list[dict[str, Any]]]
    ) -> list[dict[str, Any]]:
        index: list[dict[str, Any]] = []
        for slug, rows in sorted(rows_by_place.items()):
            parts = [rows]
            data = _jsonl_gz(rows)
            if len(data) > SHARD_MAX_BYTES:
                # Split deterministically by row count until every part fits
                # (SIG-RQ-010 — never a single oversized queue file).
                n = len(rows)
                cut = max(1, n - 1)
                while len(data) > SHARD_MAX_BYTES and cut > 0:
                    parts = [rows[i : i + cut] for i in range(0, n, cut)]
                    data = _jsonl_gz(parts[-1])
                    cut = cut // 2
            for i, part in enumerate(parts):
                path = (
                    f"web/tasks/{lane}/{slug}.jsonl.gz"
                    if len(parts) == 1
                    else f"web/tasks/{lane}/{slug}-part-{i + 1:04d}.jsonl.gz"
                )
                blob = _jsonl_gz(part)
                out.shards[path] = blob
                index.append(
                    {
                        "path": path,
                        "lane": lane,
                        "place_slug": slug,
                        "rows": len(part),
                        "bytes": len(blob),
                    }
                )
        return index

    research_by_place: dict[str, list[dict[str, Any]]] = {}
    for card in out.cards:
        slug = str((card.get("place") or {}).get("slug") or _UNPLACED)
        research_by_place.setdefault(slug, []).append(card)
    campaign_by_place: dict[str, list[dict[str, Any]]] = {}
    for camp in out.campaigns:
        slug = str((camp.get("place") or {}).get("slug") or _UNPLACED)
        campaign_by_place.setdefault(slug, []).append(camp)
    shard_index = _emit_shards("research", research_by_place) + _emit_shards(
        "campaign", campaign_by_place
    )

    # -- pass 5: handles_history + queue_meta summary -------------------------- #
    out.handles_history = {
        "schema": HANDLES_HISTORY_SCHEMA,
        "family": "task",
        "generated_at": generated_at,
        "note": (
            "First handled release: no earlier task handles exist to rename. Rows are "
            "id-aliases — /task/<uuid>/ 301s to the current handle (K11 §3)."
        ),
        "rows": [
            {
                "old": f"/task/{card['task_id']}/",
                "target": f"/task/{card['handle']}/",
                "kind": "id-alias",
                "note": "canonical task id → public handle",
            }
            for card in out.cards
            if card.get("task_id") and card.get("handle")
        ],
    }

    by_type: dict[str, int] = {}
    by_assignee: dict[str, int] = {}
    by_place: dict[str, dict[str, Any]] = {}
    for card in out.cards:
        by_type[str(card["task_type"])] = by_type.get(str(card["task_type"]), 0) + 1
        a = str(card.get("assignee_class") or "")
        by_assignee[a] = by_assignee.get(a, 0) + 1
        p = card.get("place") or {}
        place_row = by_place.setdefault(
            str(p.get("slug") or _UNPLACED),
            {"slug": p.get("slug") or _UNPLACED, "name": p.get("name"), "tasks": 0},
        )
        place_row["tasks"] += 1
    out.summary = {
        "card_schema": CARD_SCHEMA,
        "handle_grammar": "k11-handle/1",
        "lanes": {
            "research": len(out.cards),
            "campaigns": len(out.campaigns),
            "campaign_members": sum(c["member_count"] for c in out.campaigns),
            "metric_only_members": out.metric_members,
            "curation": {
                "exported": False,
                "note": "curation-lane work happens in the loopback curation app (D-K11-5)",
            },
        },
        "tasks_by_type": dict(sorted(by_type.items())),
        "tasks_by_assignee": dict(sorted(by_assignee.items())),
        "tasks_by_place": sorted(
            by_place.values(), key=lambda r: (-int(r["tasks"]), str(r["slug"]))
        ),
        "shards": shard_index,
    }
    return out


__all__ = [
    "CAMPAIGN_SCHEMA",
    "CARD_SCHEMA",
    "HANDLES_HISTORY_SCHEMA",
    "HASH_MAX",
    "HASH_MIN",
    "HANDLE_MAX",
    "LANES",
    "QUEUE_META_SCHEMA",
    "SHARD_MAX_BYTES",
    "QueueBuild",
    "build_queue",
    "handle_slug",
    "mint_handle",
    "place_segment",
    "resolve_handle_hashes",
]
