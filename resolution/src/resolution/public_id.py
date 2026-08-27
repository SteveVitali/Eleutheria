# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Public ``sig:`` identifier minting and the stability contract (SIG-IDENT-031/032).

SIG mints persistent public identifiers of the form ``sig:<type>:<uuidv7>``,
dereferenceable at ``https://<host>/id/<type>/<uuid>`` with content negotiation
(HTML, JSON-LD, RDF). The one guarantee everything downstream depends on: **a
``sig:`` identifier is NEVER silently reassigned to a different real-world entity**
(SIG-IDENT-032). When a cluster splits or merges:

* surviving identifiers are **preserved**, and
* the change is recorded as an explicit, **dated merge/split event** with
  ``redirects_to`` (merge) or ``split_into`` (split) pointers, and the retired
  identifier becomes a **tombstone** — never a live pointer to a new entity.

:class:`PublicIdRegistry` enforces that: a merged-away id resolves (redirects) to
its survivor; a split source resolves to an *ambiguous* set its readers must
disambiguate; neither is ever recycled as a live id for something else.
"""

from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import date

__all__ = [
    "uuid7",
    "PublicIdentifier",
    "mint",
    "parse",
    "dereference_url",
    "negotiate",
    "Tombstone",
    "MergeSplitEvent",
    "Resolution",
    "PublicIdRegistry",
]

_VERSION = 7
_VARIANT_RFC4122 = 0b10


def uuid7(
    *,
    timestamp_ms: int | None = None,
    rand_a: int | None = None,
    rand_b: int | None = None,
) -> uuid.UUID:
    """Generate a UUIDv7 (RFC 9562): 48-bit ms timestamp + version/variant + random.

    ``timestamp_ms``/``rand_a``/``rand_b`` are injectable so tests can mint a fixed,
    reproducible id; in production they default to the wall clock and CSPRNG. The
    time-ordered prefix makes minted ids k-sortable, matching the DB's native
    ``uuidv7()`` used for the same rows.
    """
    ts = (time.time_ns() // 1_000_000 if timestamp_ms is None else timestamp_ms) & ((1 << 48) - 1)
    a = (secrets.randbits(12) if rand_a is None else rand_a) & ((1 << 12) - 1)
    b = (secrets.randbits(62) if rand_b is None else rand_b) & ((1 << 62) - 1)
    value = (ts << 80) | (_VERSION << 76) | (a << 64) | (_VARIANT_RFC4122 << 62) | b
    return uuid.UUID(int=value)


@dataclass(frozen=True)
class PublicIdentifier:
    """A parsed ``sig:<type>:<uuidv7>`` identifier."""

    entity_type: str
    uuid: uuid.UUID

    def __str__(self) -> str:
        return f"sig:{self.entity_type}:{self.uuid}"


def mint(entity_type: str, *, value: uuid.UUID | None = None) -> PublicIdentifier:
    """Mint a new ``sig:<type>:<uuidv7>`` identifier (SIG-IDENT-031).

    ``value`` may be supplied (a reproducible uuid7 in tests); otherwise a fresh
    uuid7 is generated. The minted uuid MUST be version 7.
    """
    if not entity_type or ":" in entity_type:
        raise ValueError(f"invalid sig identifier type {entity_type!r} (SIG-IDENT-031)")
    u = value if value is not None else uuid7()
    if u.version != 7:
        raise ValueError("a sig public identifier MUST use a UUIDv7 (SIG-IDENT-031)")
    return PublicIdentifier(entity_type=entity_type, uuid=u)


def parse(identifier: str) -> PublicIdentifier:
    """Parse a ``sig:<type>:<uuid>`` string back into a :class:`PublicIdentifier`."""
    parts = identifier.split(":")
    if len(parts) != 3 or parts[0] != "sig":
        raise ValueError(f"not a sig identifier: {identifier!r} (SIG-IDENT-031)")
    return PublicIdentifier(entity_type=parts[1], uuid=uuid.UUID(parts[2]))


def dereference_url(identifier: PublicIdentifier | str, *, host: str) -> str:
    """The dereferenceable URL for an identifier (SIG-IDENT-031).

    ``sig:organization:<uuid>`` → ``https://<host>/id/organization/<uuid>``.
    """
    pid = identifier if isinstance(identifier, PublicIdentifier) else parse(identifier)
    return f"https://{host}/id/{pid.entity_type}/{pid.uuid}"


# The content-negotiation table: an Accept media type → representation (§14.8).
_NEGOTIATION: tuple[tuple[str, str], ...] = (
    ("text/html", "html"),
    ("application/ld+json", "json-ld"),
    ("application/json", "json-ld"),
    ("text/turtle", "rdf"),
    ("application/rdf+xml", "rdf"),
    ("application/n-triples", "rdf"),
)


def negotiate(accept: str | None) -> str:
    """Pick a representation for an ``Accept`` header (SIG-IDENT-031 content neg).

    Recognises HTML, JSON-LD, and RDF media types; defaults to ``html`` for a
    missing/``*/*`` header (the human-browser default).
    """
    if not accept:
        return "html"
    wanted = {part.split(";")[0].strip().lower() for part in accept.split(",")}
    if "*/*" in wanted and len(wanted) == 1:
        return "html"
    for media_type, representation in _NEGOTIATION:
        if media_type in wanted:
            return representation
    return "html"


# --- The stability contract (SIG-IDENT-032) ----------------------------------


@dataclass(frozen=True)
class Tombstone:
    """A retired identifier: never a live pointer to a new entity (SIG-IDENT-032).

    ``redirects_to`` is set for a merge (single survivor); ``split_into`` for a
    split (the set of successors the reader must disambiguate). Exactly one is
    populated.
    """

    identifier: str
    reason: str  # "merged" | "split"
    dated: date
    redirects_to: str | None = None
    split_into: tuple[str, ...] = ()


@dataclass(frozen=True)
class MergeSplitEvent:
    """A dated cluster-change event recorded when identifiers change (SIG-IDENT-032)."""

    event_type: str  # "merge" | "split"
    dated: date
    sources: tuple[str, ...]
    results: tuple[str, ...]


@dataclass(frozen=True)
class Resolution:
    """The outcome of resolving a public identifier.

    ``status`` is ``active`` (live), ``redirect`` (a merged-away id → its survivor
    in ``target``), or ``split`` (a split source → the ambiguous ``targets`` set).
    """

    status: str
    target: str | None = None
    targets: tuple[str, ...] = ()


@dataclass
class PublicIdRegistry:
    """Mints, tombstones, and resolves ``sig:`` identifiers with stability.

    Holds the set of live identifiers, the tombstones, and the ordered event log.
    Merges and splits go through here so the stability invariant is enforced in one
    place: no live identifier is ever silently repointed at a different entity.
    """

    live: set[str] = field(default_factory=set)
    tombstones: dict[str, Tombstone] = field(default_factory=dict)
    events: list[MergeSplitEvent] = field(default_factory=list)

    def register(self, identifier: PublicIdentifier | str) -> str:
        """Record a freshly minted identifier as live."""
        key = str(identifier)
        if key in self.tombstones:
            raise ValueError(f"{key} is tombstoned and MUST NOT be reused (SIG-IDENT-032)")
        self.live.add(key)
        return key

    def merge(
        self,
        *,
        sources: tuple[str, ...],
        survivor: str,
        dated: date,
    ) -> MergeSplitEvent:
        """Merge ``sources`` into ``survivor``; the survivor's id is preserved.

        Every non-survivor source is tombstoned with ``redirects_to = survivor``, so
        a citation of a merged-away id still resolves. The survivor id is never
        changed (SIG-IDENT-032).
        """
        if survivor not in sources:
            raise ValueError("the survivor MUST be one of the merge sources (SIG-IDENT-032)")
        if len(sources) < 2:
            raise ValueError("a merge needs at least two sources (SIG-IDENT-032)")
        for src in sources:
            if src == survivor:
                continue
            self.live.discard(src)
            self.tombstones[src] = Tombstone(
                identifier=src, reason="merged", dated=dated, redirects_to=survivor
            )
        self.live.add(survivor)
        event = MergeSplitEvent(
            event_type="merge", dated=dated, sources=tuple(sources), results=(survivor,)
        )
        self.events.append(event)
        return event

    def split(
        self,
        *,
        source: str,
        into: tuple[str, ...],
        dated: date,
    ) -> MergeSplitEvent:
        """Split ``source`` into ``into`` successors.

        ``source`` is tombstoned with ``split_into = into`` — it is NOT reassigned
        to any single successor (that would be a silent reassignment). Each
        successor id is registered live. Readers of the old id get an *ambiguous*
        resolution they must disambiguate (SIG-IDENT-032).
        """
        if len(into) < 2:
            raise ValueError("a split needs at least two successors (SIG-IDENT-032)")
        if source in into:
            raise ValueError(
                "a split source MUST NOT be reused as one of its successors "
                "(no silent reassignment, SIG-IDENT-032)"
            )
        self.live.discard(source)
        for child in into:
            self.live.add(child)
        self.tombstones[source] = Tombstone(
            identifier=source, reason="split", dated=dated, split_into=tuple(into)
        )
        event = MergeSplitEvent(
            event_type="split", dated=dated, sources=(source,), results=tuple(into)
        )
        self.events.append(event)
        return event

    def is_tombstone(self, identifier: str) -> bool:
        return identifier in self.tombstones

    def resolve(self, identifier: str) -> Resolution:
        """Resolve an identifier to its current status (SIG-IDENT-032).

        A live id resolves ``active``; a merged-away id follows ``redirects_to``
        transitively to the surviving id (``redirect``); a split source resolves to
        the ambiguous successor set (``split``). An unknown id raises.
        """
        if identifier in self.live:
            return Resolution(status="active", target=identifier)
        tomb = self.tombstones.get(identifier)
        if tomb is None:
            raise KeyError(f"unknown sig identifier {identifier!r}")
        if tomb.reason == "merged":
            target = tomb.redirects_to
            assert target is not None
            # Follow a chain of merges to the ultimate survivor.
            seen = {identifier}
            while target in self.tombstones and self.tombstones[target].reason == "merged":
                if target in seen:
                    break
                seen.add(target)
                target = self.tombstones[target].redirects_to  # type: ignore[assignment]
            return Resolution(status="redirect", target=target)
        return Resolution(status="split", targets=tomb.split_into)
