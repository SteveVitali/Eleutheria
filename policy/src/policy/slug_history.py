# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Entity URL keys and slug history — ``sig.slug-history/1`` (K2 §3.3/§6.5,
ticket P36.29, R11-K13-GX-03).

Same identifier module family as :mod:`policy.labels` (SIG-UI-067 — ONE module
owns slugs, hashes and history): this file holds the *history* half — the
append-only record of every entity URL key ever issued and the redirect
semantics the single redirect generator (JUR-05, P36.35) consumes. It reads
``labels``' primitives; nothing here re-derives a slug, a hash or a label.

The record (K2 §6.5)::

    {hash, uuid, url_type, slug, from_pub, to_pub, status, target}

* ``hash`` — the issued Crockford-base32 hash of the entity's canonical UUID
  text, **authoritative and frozen**: an issued hash is never reissued to a
  different entity and never rewritten; a collision inside the registry
  extends the *new* key by one character (:func:`freeze_hashes`).
* ``uuid`` — the canonical entity identity (ENT-6); ``/id/<type>/<uuid>``
  always resolves through it.
* ``url_type`` / ``slug`` — the ``/entity/<type>/<name-slug>--<hash>/``
  segments; the slug is cosmetic. ``slug`` is ``None`` where the key was
  never issued by a release this history can see (a merged or withdrawn
  entity recorded before its first bound prior registry) — recorded, never
  fabricated.
* ``from_pub`` / ``to_pub`` — the publication ids that issued and retired
  the key (``None`` = still live / unknown, honest absence).
* ``status`` — the closed vocabulary ``current | renamed | merged | split |
  withdrawn``; ``target`` is the successor URL (``renamed``/``merged``), the
  successor URL list (``split``) or ``None``.

Append-only law: the emitted row LIST is strictly additive — prior rows
carry forward verbatim, a key's retirement appends a terminal row for the
same key, and a terminal row never re-opens. Resolution reads the terminal
row when one exists for a key.

Redirect semantics (K2 §3.3, the one vocabulary JUR-05's generator and the
web stubs both implement — :func:`resolve_request` is the reference):

* ``/entity/<type>/<anything>--<hash>/`` — hash authoritative: a live key
  with a wrong slug 301s to the canonical URL; a retired key answers its
  terminal status.
* rename / merge / re-type → **301** to the target URL.
* split → **300** with the successor URL list (the choice page is JUR-05's).
* withdrawal → **410** (the tombstone page is JUR-05's). The K2
  ``withdrawn`` status is the *lifecycle* tombstone — an entity that left
  the public surface with no recorded transition. A **publication**
  withdrawal (P34.19, F-337) is stronger: the entity's id may not appear
  in any public artifact, so its rows are scrubbed from the emitted
  document entirely rather than tombstoned.
* ``/id/<type>/<uuid>`` → **302** to the current URL while the entity is
  live (the key can still move), else the terminal status: ``merged`` 301,
  ``split`` 300, ``withdrawn`` 410; a ``renamed`` row with no live row
  resolves through its own target.
* An unknown hash or uuid answers ``None`` — the honest 404, never a guess.

SIG-UI-112 binds here too: ``person`` entities carry no label, page, node,
slug or URL (``labels.py`` withholds them), so no history row may ever be
emitted for one — :func:`merge_history` filters them and
:func:`resolve_request` treats the ``person`` url_type as absent.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from typing import Any

from .labels import HASH_LEN, EntityLabel, entity_hash, entity_url

#: The emitted document's schema id (K2 §6.5).
ENTITY_SLUG_HISTORY_SCHEMA = "sig.slug-history/1"

#: The closed status vocabulary (K2 §3.3/§6.5).
HISTORY_STATUSES: tuple[str, ...] = (
    "current",
    "renamed",
    "merged",
    "split",
    "withdrawn",
)

#: Statuses that retire a key — the terminal rows resolution reads.
TERMINAL_STATUSES: frozenset[str] = frozenset({"renamed", "merged", "split", "withdrawn"})

#: HTTP semantics per status (K2 §3.3). ``current`` resolves at the URL layer
#: by exact match (serve) or canonical 301; at the ``/id/`` layer by 302.
STATUS_HTTP: dict[str, int] = {
    "renamed": 301,
    "merged": 301,
    "split": 300,
    "withdrawn": 410,
}

_ENTITY_URL_RE = re.compile(r"^/entity/([a-z0-9-]+)/([^/]+?)/?$")
_ID_URL_RE = re.compile(r"^/id/([a-z0-9-]+)/([^/]+?)/?$")
_KEY_RE = re.compile(r"^(.+?)--([0-9a-z]{4,})$")


@dataclass(frozen=True)
class SlugHistoryRow:
    """One issued entity URL key and its resolution (``sig.slug-history/1``)."""

    hash: str
    uuid: str
    url_type: str | None
    slug: str | None
    status: str
    target: str | tuple[str, ...] | None = None
    from_pub: str | None = None
    to_pub: str | None = None
    note: str | None = None

    def row(self) -> dict[str, Any]:
        """The emitted ``sig.slug-history/1`` object."""
        out: dict[str, Any] = {
            "hash": self.hash,
            "uuid": self.uuid,
            "url_type": self.url_type,
            "slug": self.slug,
            "status": self.status,
            "target": list(self.target) if isinstance(self.target, tuple) else self.target,
            "from_pub": self.from_pub,
            "to_pub": self.to_pub,
        }
        if self.note is not None:
            out["note"] = self.note
        return out


@dataclass(frozen=True)
class RedirectDecision:
    """One resolved request outcome — the seam JUR-05's generator and the
    static stubs consume. ``status`` is the HTTP semantics (200 = serve,
    300 choice page, 301 permanent, 302 the live ``/id/`` redirect, 410
    tombstone, 404 honest absence). ``target`` is the URL to send;
    ``targets`` carries the split choices."""

    status: int
    target: str | None = None
    targets: tuple[str, ...] | None = None
    reason: str | None = None


def _as_row(obj: SlugHistoryRow | Mapping[str, Any]) -> dict[str, Any]:
    """Normalise a dataclass or emitted dict to the emitted dict shape."""
    if isinstance(obj, SlugHistoryRow):
        return obj.row()
    return dict(obj)


def issued_hashes(rows: Sequence[Mapping[str, Any]]) -> set[str]:
    """Every hash the history has issued — the frozen set new keys must not
    collide into (K2 §3.3: a hash is never reissued)."""
    return {str(r["hash"]) for r in rows if r.get("hash")}


def freeze_hashes(
    labels: Mapping[str, EntityLabel],
    prior_rows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, EntityLabel]:
    """Apply the K2 §3.3 collision-extension rule to a label registry.

    A new key whose 7-char hash collides with an already-issued hash (any
    prior history row) or with another label in this registry extends by one
    base32 character until it is unique — the extension appends, never
    rewrites, and an already-issued hash is never reassigned. Deterministic:
    entities are assigned in sorted ``entity_id`` order, first-come keeps
    the 7-char form. Returns ``entity_id → EntityLabel`` with ``hash`` and
    ``url`` replaced on the extended rows; input rows pass through frozen.
    """
    # A hash is frozen *for its uuid*: reusing your own issued hash is the
    # permanence contract, not a collision. Extension applies only when the
    # hash was issued to a DIFFERENT entity (or a sibling in this registry).
    hash_uuids: dict[str, set[str]] = {}
    for r in prior_rows:
        if r.get("hash") and r.get("uuid"):
            hash_uuids.setdefault(str(r["hash"]), set()).add(str(r["uuid"]))
    taken: set[str] = set()  # this registry's assignments
    out: dict[str, EntityLabel] = {}
    for eid in sorted(labels):
        label = labels[eid]
        if label.slug is None or label.url is None or label.url_type is None:
            out[eid] = label
            continue
        hash_value = label.hash or entity_hash(eid)
        length = HASH_LEN
        while (hash_value in hash_uuids and hash_uuids[hash_value] != {eid}) or (
            hash_value in taken
        ):
            length += 1
            hash_value = entity_hash(eid, length=length)
        taken.add(hash_value)
        if hash_value != label.hash:
            label = replace(
                label,
                hash=hash_value,
                url=entity_url(label.url_type, label.slug, hash_value),
            )
        out[eid] = label
    return out


def check_unique_labels(labels: Mapping[str, EntityLabel]) -> None:
    """SIG-UI-111 fail-closed assertion: within ``kind`` no two emitted rows
    share a full display label. ``resolve_disambiguators`` guarantees the
    invariant; this check makes a regression a build failure, never a
    silently-shipped duplicate."""
    seen: dict[tuple[str, str], str] = {}
    for eid, label in labels.items():
        if label.label is None:
            continue
        key = (label.kind, label.label.casefold())
        other = seen.get(key)
        if other is not None:
            raise ValueError(
                "SIG-UI-111: duplicate display label "
                f"{label.label!r} within kind {label.kind!r} "
                f"(entities {other} and {eid})"
            )
        seen[key] = eid


def _label_key_url(label: EntityLabel) -> str | None:
    return label.url


def merge_history(
    prior_rows: Sequence[Mapping[str, Any] | SlugHistoryRow],
    labels: Mapping[str, EntityLabel],
    *,
    publication: str,
    url_types: Mapping[str, str] | None = None,
    merged_into: Mapping[str, str] | None = None,
    withdrawn: set[str] | frozenset[str] | Sequence[str] | None = None,
    split_into: Mapping[str, Sequence[str]] | None = None,
) -> list[SlugHistoryRow]:
    """The append-only history merge — one release's diff.

    ``prior_rows`` are the previous release's emitted ``sig.slug-history/1``
    rows (empty for a first bound release); ``labels`` is this release's
    ``entity_id → EntityLabel`` registry. ``url_types`` maps an entity id to
    its URL type segment for entities that carry no current label (the
    merged/withdrawn tombstones); ``merged_into`` maps a retired entity id
    to its survivor's id; ``withdrawn`` is the **publication-withdrawal**
    list (P34.19): those entities are scrubbed from the emitted document
    entirely — every prior row naming one is dropped and nothing is
    appended, because a withdrawn entity's id may not appear in any public
    artifact (F-337 — a scrub, not a 410 tombstone); ``split_into`` maps a
    retired id to its successor ids (300 — no spine record mints these
    yet, the seam is here for the first recorded split).

    Rules:

    * every prior row carries forward verbatim — except a publication-
      withdrawn entity's rows, which leave the document entirely;
    * a prior ``current`` row whose entity keeps the same URL stays;
      a URL change appends a ``renamed`` terminal row for the old key
      plus a ``current`` row for the new key (the hash — the entity's
      identity — never changes on rename);
    * a prior ``current`` row whose entity leaves the registry appends
      ``merged`` (survivor recorded), ``split`` (successors recorded) or
      ``withdrawn`` — an unexplained absence is the honest 410, never a
      dangling ``current``;
    * entities newly recorded ``merged_into``/``split_into`` with no prior
      row emit their terminal row now (``slug: None`` where no prior key
      is visible) so ``/id/<type>/<uuid>`` resolves truthfully;
    * ``person`` entities and label rows without a URL emit nothing —
      no label, no slug, no history (SIG-UI-112 / A-10);
    * rows sort by ``(uuid, hash, from_pub or "", status)`` for byte-stable
      output; append-only is verifiable — every prior row reappears
      verbatim in the result.
    """
    merged_into = dict(merged_into or {})
    withdrawn_set = {str(w) for w in (withdrawn or ())}
    split_into = {str(k): tuple(str(s) for s in v) for k, v in (split_into or {}).items()}
    url_types = dict(url_types or {})

    # Publication withdrawal scrubs: a withdrawn entity's rows leave the
    # emitted document entirely — its id may not appear in any public
    # artifact (F-337), which rules out even a 410 tombstone.
    prior = [r for r in (_as_row(r) for r in prior_rows) if str(r.get("uuid")) not in withdrawn_set]
    out: list[dict[str, Any]] = [dict(r) for r in prior]

    # Live labelled keys: uuid → label. A recorded terminal entity —
    # merged, split or withdrawn — can never hold a live key, whatever a
    # stale registry row says (the record, not the row, governs).
    live: dict[str, EntityLabel] = {
        eid: lbl
        for eid, lbl in labels.items()
        if lbl.url is not None
        and lbl.kind != "person"
        and eid not in withdrawn_set
        and eid not in merged_into
        and eid not in split_into
    }

    # Prior current rows by uuid — each entity's last live key.
    prior_current: dict[str, dict[str, Any]] = {}
    prior_terminal_uuids: set[str] = set()
    for r in prior:
        if r.get("status") == "current":
            prior_current[str(r.get("uuid"))] = r
        elif r.get("status") in TERMINAL_STATUSES:
            prior_terminal_uuids.add(str(r.get("uuid")))

    # Dedupe key includes slug + status: a `renamed`/`merged`/`withdrawn`
    # terminal row shares (uuid, hash) with the prior `current` row it
    # retires, and a rename's NEW `current` row shares (uuid, hash, status)
    # with the old one — only an identical (uuid, hash, slug, status) tuple
    # is a real duplicate.
    emitted_keys: set[tuple[str, str, str, str]] = {
        (str(r.get("uuid")), str(r.get("hash")), str(r.get("slug")), str(r.get("status")))
        for r in out
        if r.get("hash")
    }
    new_rows: list[dict[str, Any]] = []

    def _append(row: dict[str, Any]) -> None:
        key = (
            str(row.get("uuid")),
            str(row.get("hash")),
            str(row.get("slug")),
            str(row.get("status")),
        )
        if key in emitted_keys:
            return
        emitted_keys.add(key)
        new_rows.append(row)

    def _target_for(entity_id: str, url_type: str | None) -> str:
        """A successor's URL — its canonical page URL when labelled, else the
        permanent ``/id/`` address (always resolves; never a dead target)."""
        lbl = live.get(entity_id)
        if lbl is not None and lbl.url:
            return lbl.url
        kind_type = url_types.get(entity_id)
        return f"/id/{kind_type or 'entity'}/{entity_id}/"

    # 1. Transitions for every prior `current` row.
    for uuid, row in prior_current.items():
        old_url = f"/entity/{row.get('url_type')}/{row.get('slug')}--{row.get('hash')}/"
        lbl = live.get(uuid)
        if lbl is not None:
            if lbl.url == old_url:
                continue  # still current, verbatim carry
            # renamed / re-typed: the hash is the same identity; the old key
            # retires 301 to the new canonical URL.
            _append(
                SlugHistoryRow(
                    hash=str(row.get("hash")),
                    uuid=uuid,
                    url_type=row.get("url_type"),
                    slug=row.get("slug"),
                    status="renamed",
                    target=lbl.url,
                    from_pub=row.get("from_pub"),
                    to_pub=publication,
                ).row()
            )
            _append(
                SlugHistoryRow(
                    hash=str(lbl.hash or entity_hash(uuid)),
                    uuid=uuid,
                    url_type=lbl.url_type,
                    slug=lbl.slug,
                    status="current",
                    from_pub=publication,
                ).row()
            )
            continue
        # The entity left the label registry — a terminal row for its key.
        # A publication-withdrawn successor can never be named: its id may
        # not appear in a public artifact, so the merge/split falls back to
        # the honest 410 rather than leaking the successor's id.
        survivor = merged_into.get(uuid)
        if survivor in withdrawn_set:
            survivor = None
        successors = tuple(s for s in split_into.get(uuid, ()) if s not in withdrawn_set)
        if survivor is not None:
            _append(
                SlugHistoryRow(
                    hash=str(row.get("hash")),
                    uuid=uuid,
                    url_type=row.get("url_type"),
                    slug=row.get("slug"),
                    status="merged",
                    target=_target_for(survivor, url_types.get(survivor)),
                    from_pub=row.get("from_pub"),
                    to_pub=publication,
                ).row()
            )
        elif successors:
            _append(
                SlugHistoryRow(
                    hash=str(row.get("hash")),
                    uuid=uuid,
                    url_type=row.get("url_type"),
                    slug=row.get("slug"),
                    status="split",
                    target=tuple(_target_for(s, url_types.get(s)) for s in successors),
                    from_pub=row.get("from_pub"),
                    to_pub=publication,
                ).row()
            )
        else:
            _append(
                SlugHistoryRow(
                    hash=str(row.get("hash")),
                    uuid=uuid,
                    url_type=row.get("url_type"),
                    slug=row.get("slug"),
                    status="withdrawn",
                    target=None,
                    from_pub=row.get("from_pub"),
                    to_pub=publication,
                    note="no longer published",
                ).row()
            )

    # 2. `current` rows for every live key not already current.
    for eid in sorted(live):
        lbl = live[eid]
        prev = prior_current.get(eid)
        prev_url = (
            f"/entity/{prev.get('url_type')}/{prev.get('slug')}--{prev.get('hash')}/"
            if prev is not None
            else None
        )
        if prev is not None and lbl.url == prev_url:
            continue  # already carried
        _append(
            SlugHistoryRow(
                hash=str(lbl.hash or entity_hash(eid)),
                uuid=eid,
                url_type=lbl.url_type,
                slug=lbl.slug,
                status="current",
                from_pub=publication,
            ).row()
        )

    # 3. Terminal rows for recorded merge/split entities that have no prior
    #    row at all — recorded now so `/id/` resolves truthfully. A
    #    publication-withdrawn entity emits nothing (the scrub reaches its
    #    id); a person entity emits nothing, ever (SIG-UI-112).
    for eid in sorted(set(merged_into) | set(split_into)):
        if (
            eid in withdrawn_set
            or eid in prior_current
            or eid in prior_terminal_uuids
            or eid in live
            or url_types.get(eid) == "person"
        ):
            continue
        hash_value = entity_hash(eid)
        url_type = url_types.get(eid)
        if eid in merged_into and merged_into[eid] not in withdrawn_set:
            _append(
                SlugHistoryRow(
                    hash=hash_value,
                    uuid=eid,
                    url_type=url_type,
                    slug=None,
                    status="merged",
                    target=_target_for(merged_into[eid], url_types.get(merged_into[eid])),
                    to_pub=publication,
                    note="merged before this history bound a prior release",
                ).row()
            )
        elif eid in split_into:
            successors = tuple(s for s in split_into[eid] if s not in withdrawn_set)
            if not successors:
                continue  # every successor scrubbed — nothing nameable
            _append(
                SlugHistoryRow(
                    hash=hash_value,
                    uuid=eid,
                    url_type=url_type,
                    slug=None,
                    status="split",
                    target=tuple(_target_for(s, url_types.get(s)) for s in successors),
                    to_pub=publication,
                    note="split recorded before this history bound a prior release",
                ).row()
            )
        # A merged-into-withdrawn entity falls through unemitted too — the
        # merge's successor can never be named publicly.

    out.extend(new_rows)
    out.sort(
        key=lambda r: (
            str(r.get("uuid") or ""),
            str(r.get("hash") or ""),
            str(r.get("from_pub") or ""),
            str(r.get("status") or ""),
        )
    )
    return [
        SlugHistoryRow(
            hash=str(r["hash"]),
            uuid=str(r["uuid"]),
            url_type=r.get("url_type"),
            slug=r.get("slug"),
            status=str(r["status"]),
            target=(tuple(r["target"]) if isinstance(r.get("target"), list) else r.get("target")),
            from_pub=r.get("from_pub"),
            to_pub=r.get("to_pub"),
            note=r.get("note"),
        )
        for r in out
    ]


def history_doc(
    rows: Sequence[SlugHistoryRow | Mapping[str, Any]],
    *,
    publication: str | None,
    generated_at: str,
) -> dict[str, Any]:
    """The emitted ``sig.slug-history/1`` document for
    ``web/entity_slug_history.json`` — the single registry the JUR-05
    redirect generator consumes (K2 §6.5)."""
    emitted = [_as_row(r) for r in rows]
    for r in emitted:
        if r.get("status") not in HISTORY_STATUSES:
            raise ValueError(f"sig.slug-history/1 row with bad status: {r!r}")
    # One key may retire at most once — two terminal rows for one key is a
    # corrupt registry, never something the resolver should guess over.
    terminal: set[tuple[str, str]] = set()
    retired_keys: set[tuple[str, str, str, str]] = set()
    for r in emitted:
        if r.get("status") in TERMINAL_STATUSES:
            key = (str(r.get("uuid")), str(r.get("hash")))
            if key in terminal:
                raise ValueError(
                    f"sig.slug-history/1: key retired twice (uuid {key[0]}, hash {key[1]})"
                )
            terminal.add(key)
            retired_keys.add(_key_tuple(r))
    # An entity holds at most one LIVE key — a verbatim-carried `current`
    # row retired by a terminal row is history, not a second live key.
    live_uuids: set[str] = set()
    for r in emitted:
        if r.get("status") == "current" and _key_tuple(r) not in retired_keys:
            uuid = str(r.get("uuid"))
            if uuid in live_uuids:
                raise ValueError(f"sig.slug-history/1: entity has two live keys (uuid {uuid})")
            live_uuids.add(uuid)
        if r.get("url_type") == "person":
            raise ValueError(
                "sig.slug-history/1: a person row can never be emitted "
                f"(uuid {r.get('uuid')}) — SIG-UI-112"
            )
    return {
        "schema": ENTITY_SLUG_HISTORY_SCHEMA,
        "publication": publication,
        "generated_at": generated_at,
        "rows": emitted,
    }


def _terminal_row(candidates: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    for r in reversed(candidates):
        if r.get("status") in TERMINAL_STATUSES:
            return r
    return None


def _key_tuple(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """The issued-key identity — a terminal row retires exactly the
    ``current`` row whose (uuid, hash, url_type, slug) it names."""
    return (
        str(row.get("uuid")),
        str(row.get("hash")),
        str(row.get("url_type")),
        str(row.get("slug")),
    )


def _live_currents(
    emitted: Sequence[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    """The genuinely-live ``current`` rows. A verbatim-carried ``current``
    row is *stale* when a terminal row names the same key — append-only
    history keeps both, so liveness is ``current`` minus retired, never the
    row's status alone."""
    retired = {_key_tuple(r) for r in emitted if r.get("status") in TERMINAL_STATUSES}
    return [r for r in emitted if r.get("status") == "current" and _key_tuple(r) not in retired]


def _terminal_decision(row: Mapping[str, Any]) -> RedirectDecision:
    status = str(row.get("status"))
    target = row.get("target")
    if status == "split":
        targets = tuple(str(t) for t in (target or ()))
        return RedirectDecision(status=300, targets=targets, reason="split")
    if status == "withdrawn":
        return RedirectDecision(status=410, reason="withdrawn")
    return RedirectDecision(
        status=STATUS_HTTP[status],
        target=str(target) if target else None,
        reason=status,
    )


def resolve_request(
    rows: Sequence[SlugHistoryRow | Mapping[str, Any]],
    path: str,
) -> RedirectDecision | None:
    """Resolve a request path against the history — the redirect semantics
    K2 §3.3 binds (the reference implementation JUR-05's generator and the
    web stubs mirror).

    ``/entity/<type>/<slug>--<hash>/`` and ``/id/<type>/<uuid>`` resolve;
    anything else answers ``None`` (never a guess). ``None`` is also the
    answer for an unknown hash/uuid — the honest 404.
    """
    emitted = [_as_row(r) for r in rows]
    live_rows = _live_currents(emitted)
    m = _ID_URL_RE.match(path)
    if m:
        url_type, uuid = m.group(1), m.group(2)
        cands = [r for r in emitted if str(r.get("uuid")) == uuid]
        if not cands:
            return None
        live = next(
            (
                r
                for r in live_rows
                if str(r.get("uuid")) == uuid and (r.get("url_type") in (None, url_type))
            ),
            None,
        )
        if live is not None:
            slug, h = live.get("slug"), live.get("hash")
            lt = live.get("url_type") or url_type
            if slug and h:
                return RedirectDecision(
                    status=302, target=f"/entity/{lt}/{slug}--{h}/", reason="id"
                )
            return None  # a live row without a key is malformed — honest 404
        term = _terminal_row(cands)
        if term is None:
            return None
        decision = _terminal_decision(term)
        if decision.status == 301 and decision.target is None:
            return None
        # a `renamed` row resolves `/id/` through its target (302 — the
        # entity is still live under the successor key).
        if term.get("status") == "renamed" and decision.target:
            return RedirectDecision(status=302, target=decision.target, reason="id")
        return decision
    m = _ENTITY_URL_RE.match(path)
    if not m:
        return None
    url_type, key = m.group(1), m.group(2)
    km = _KEY_RE.match(key)
    if not km:
        return None
    _, hash_value = km.group(1), km.group(2)
    cands = [r for r in emitted if str(r.get("hash")) == hash_value]
    if not cands:
        return None
    live = next((r for r in live_rows if str(r.get("hash")) == hash_value), None)
    if live is not None:
        if not live.get("slug") or not live.get("url_type"):
            return None  # a live row without a key is malformed — honest 404
        canonical = f"/entity/{live['url_type']}/{live['slug']}--{live['hash']}/"
        if path.rstrip("/") + "/" == canonical:
            return RedirectDecision(status=200, target=canonical, reason="current")
        # hash authoritative: the slug (or a stale url_type) is cosmetic — 301.
        return RedirectDecision(status=301, target=canonical, reason="canonical")
    term = _terminal_row(cands)
    if term is not None:
        return _terminal_decision(term)
    return None
