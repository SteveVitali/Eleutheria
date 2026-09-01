# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Curated source indexes held **as indexes**, never normalized into claims (§10.9).

**SIG-EPIS-030 (MUST).** SIG MUST be able to hold a curated source index *as an
index*, without normalizing its entries into claims (OL-2E-AL-02). A well-maintained
bibliography of reporting is valuable on its own terms, and forcing premature
normalization would both destroy that value and manufacture low-quality claims.

This module is the **general form** of the behaviour the P13.1 ``accountability``
connector's Abuse Library handling relies on: a :class:`CuratedSourceIndex` is a
list of :class:`CuratedIndexEntry` references retained *as an index*. It carries an
explicit guard — :meth:`CuratedSourceIndex.as_claims` raises — so the "held as an
index, not normalized into facts" invariant is a mechanical property, not a
convention. Its entries surface as ``index_only`` records (:meth:`index_records`),
never as event/attribute claims.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

#: The default source class for a bibliography entry. A curated index of reporting
#: is advocacy analysis until a source is typed more precisely (OL-2E-AL-03).
DEFAULT_SOURCE_CLASS = "advocacy_analysis"


class IndexNormalizationRefused(NotImplementedError):
    """Raised when something tries to normalize a curated index into claims.

    Holding the index *as an index* is the point (SIG-EPIS-030); materializing its
    entries into claims would destroy the index's value and manufacture low-quality
    claims (§10.9, OL-2E-AL-02).
    """


@dataclass(frozen=True)
class CuratedIndexEntry:
    """One entry in a curated source index: a reference to reporting, never a claim.

    ``source_ref`` is the citation/URL the entry points at; ``indexes`` is the
    subject the entry is *about* (e.g. an incident id), retained so the index can
    be joined without being flattened into a claim about that subject.
    """

    source_ref: str
    source_class: str = DEFAULT_SOURCE_CLASS
    indexes: str = ""
    stable_locator: str = ""
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.source_ref).strip():
            raise ValueError("a curated index entry requires a source_ref (§10.9)")


@dataclass(frozen=True)
class CuratedSourceIndex:
    """A curated bibliography held **as an index** (§10.9, SIG-EPIS-030).

    Its entries are retained as index references and MUST NOT be normalized into
    claims. :attr:`held_as_index` is always true and :meth:`as_claims` always
    raises: the index is a first-class object that stays an index.
    """

    index_id: str
    entries: tuple[CuratedIndexEntry, ...] = ()

    #: Always true: a curated index is held as an index, never as normalized claims.
    held_as_index: bool = field(default=True, init=False)

    def __len__(self) -> int:
        return len(self.entries)

    def __iter__(self) -> Iterator[CuratedIndexEntry]:
        return iter(self.entries)

    def __bool__(self) -> bool:
        return bool(self.entries)

    def as_claims(self) -> Any:
        """The guard: a curated index is never materialized into claims (SIG-EPIS-030)."""
        raise IndexNormalizationRefused(
            "a curated source index is held as an index, not normalized into claims "
            "(SIG-EPIS-030, §10.9, OL-2E-AL-02)"
        )

    def index_records(self) -> tuple[dict[str, Any], ...]:
        """The index as ``index_only`` records — references, never claim rows.

        Each record carries ``index_only=True`` so any downstream consumer (a store,
        a render surface) treats it as a bibliography entry, not a fact about its
        subject.
        """
        return tuple(
            {
                "record_kind": "index_entry",
                "index_only": True,
                "index_id": self.index_id,
                "indexes": entry.indexes,
                "source_ref": entry.source_ref,
                "source_class": entry.source_class,
                "stable_locator": entry.stable_locator,
                "raw_value": entry.source_ref,
            }
            for entry in self.entries
        )

    @classmethod
    def from_raw(
        cls,
        index_id: str,
        raws: Sequence[Mapping[str, Any]],
        *,
        ref_keys: Sequence[str],
        subject_keys: Sequence[str] = (),
        class_key: str | None = None,
        default_class: str = DEFAULT_SOURCE_CLASS,
        allowed_classes: frozenset[str] | None = None,
    ) -> CuratedSourceIndex:
        """Build an index from raw entry mappings, keeping each as a reference.

        ``ref_keys`` / ``subject_keys`` are tried in order for the source reference
        and the indexed subject; a per-entry ``class_key`` sets the source class
        (validated against ``allowed_classes`` when given, else falling back to
        ``default_class``). Entries with no resolvable reference are skipped rather
        than invented into a claim.
        """
        entries: list[CuratedIndexEntry] = []
        for raw in raws:
            ref = _first(raw, ref_keys) or _first(raw, subject_keys)
            if not ref:
                continue
            cls_value = _first(raw, (class_key,)) if class_key else ""
            source_class = cls_value if cls_value else default_class
            if allowed_classes is not None and source_class not in allowed_classes:
                source_class = default_class
            entries.append(
                CuratedIndexEntry(
                    source_ref=ref,
                    source_class=source_class,
                    indexes=_first(raw, subject_keys),
                    raw=dict(raw),
                )
            )
        return cls(index_id=index_id, entries=tuple(entries))


def _first(raw: Mapping[str, Any], keys: Sequence[str]) -> str:
    """The first non-empty value in ``raw`` among ``keys`` (stringified), else ``""``."""
    for key in keys:
        if not key:
            continue
        value = raw.get(key)
        if value not in (None, ""):
            return str(value)
    return ""


__all__ = [
    "DEFAULT_SOURCE_CLASS",
    "CuratedIndexEntry",
    "CuratedSourceIndex",
    "IndexNormalizationRefused",
]
