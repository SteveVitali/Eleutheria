# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Dry-run impact report for legacy ``sig.org.name`` partner keys (P32.3 / ADR-122).

Before P32.3 every name-only partner minted a *global* ``sig.org.name`` entity:
two records that normalised to the same name silently unioned, even across
jurisdictions. ADR-122 replaces that with scope-qualified ``sig.org.name_scoped``
keys. Nothing may be re-keyed in place — the claim spine is append-only and the
identity guard's keys are immutable recorded decisions — so the repair path is a
**recorded disposition** per legacy key, decided by a human, not a code path.

This module produces the dry-run evidence that review needs. For every existing
``sig.org.name`` identifier it reports:

* the organisation entity it keys and its label;
* the observed claim provenance behind it — the sources and predicates that
  asserted the name;
* the ``sig.org.name_scoped`` keys it *would* have minted under P32.3 — one
  ``src:<source>|<name>`` per asserting source (jurisdiction-scoped keys are
  reported when a ``partner_jurisdiction`` row-level context was recorded, which
  pre-P32.3 data never carries);
* the **split count** — how many unmerged candidates the one global entity
  decomposes into. A split count > 1 is exactly the cross-source auto-union
  SIG-TRUST-004 forbids going forward.

Read-only by construction: :func:`name_scope_report` runs SELECTs and returns a
plain dict; the ``partner-name-audit`` CLI prints it as JSON. No row is written.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

from db.identity_guard import PARTNER_NAME_SCHEME

from .partner_identity import scoped_name_key

__all__ = [
    "LegacyNameImpact",
    "name_scope_report",
    "proposed_scoped_keys",
]

#: The provenance query: for every legacy sig.org.name identifier, each source
#: that asserted it (through an entity-ref claim's evidence set) and each
#: predicate that carried the name.
_REPORT_SQL = """
SELECT ei.value AS name_key,
       e.entity_id::text,
       o.cached_canonical_name AS label,
       ea.source_id,
       c.predicate_id
  FROM entity_identifier ei
  JOIN entity e ON e.entity_id = ei.entity_id
  LEFT JOIN organization o ON o.entity_id = e.entity_id
  JOIN claim c ON c.object_entity = e.entity_id AND c.object_type = 'entity_ref'
  JOIN claim_evidence ce ON ce.claim_id = c.claim_id
  JOIN evidence_capture ec ON ec.capture_id = ce.capture_id
  JOIN evidence_artifact ea ON ea.artifact_id = ec.artifact_id
 WHERE ei.scheme = %s
 ORDER BY ei.value, ea.source_id, c.predicate_id
"""


def proposed_scoped_keys(normalized: str, sources: Iterable[str]) -> list[str]:
    """The ``sig.org.name_scoped`` keys a legacy global name would split into.

    One ``src:<source>|<name>`` key per distinct asserting source — the
    deterministic dry-run scope. A single source collapses to one key (the
    pre-P32.3 union was harmless inside one source); several sources split the
    global entity into that many unmerged candidates.
    """
    keys: list[str] = []
    seen: set[str] = set()
    for source in sorted({str(s) for s in sources if str(s).strip()}):
        key, _ = scoped_name_key(normalized, scope=source)
        if key not in seen:
            seen.add(key)
            keys.append(key)
    return keys


@dataclass(frozen=True)
class LegacyNameImpact:
    """The dry-run disposition evidence for one legacy ``sig.org.name`` key."""

    name_key: str
    entity_id: str
    label: str | None
    sources: tuple[str, ...] = field(default_factory=tuple)
    predicates: tuple[str, ...] = field(default_factory=tuple)
    proposed_keys: tuple[str, ...] = field(default_factory=tuple)

    @property
    def split_count(self) -> int:
        """How many unmerged scoped candidates this global entity becomes."""
        return max(len(self.proposed_keys), 1)

    def as_dict(self) -> dict[str, Any]:
        return {
            "name_key": self.name_key,
            "entity_id": self.entity_id,
            "label": self.label,
            "sources": list(self.sources),
            "predicates": list(self.predicates),
            "proposed_scoped_keys": list(self.proposed_keys),
            "split_count": self.split_count,
        }


def _impacts_from_rows(rows: Iterable[Mapping[str, Any]]) -> list[LegacyNameImpact]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row["name_key"])
        g = grouped.setdefault(
            key,
            {
                "entity_id": str(row["entity_id"]),
                "label": row.get("label"),
                "sources": set(),
                "predicates": set(),
            },
        )
        if row.get("source_id"):
            g["sources"].add(str(row["source_id"]))
        if row.get("predicate_id"):
            g["predicates"].add(str(row["predicate_id"]))
    out: list[LegacyNameImpact] = []
    for key in sorted(grouped):
        g = grouped[key]
        sources = tuple(sorted(g["sources"]))
        out.append(
            LegacyNameImpact(
                name_key=key,
                entity_id=g["entity_id"],
                label=g["label"],
                sources=sources,
                predicates=tuple(sorted(g["predicates"])),
                proposed_keys=tuple(proposed_scoped_keys(key, sources)),
            )
        )
    return out


def name_scope_report(conn: Any) -> dict[str, Any]:
    """The dry-run impact report for every legacy ``sig.org.name`` key.

    ``conn`` is a psycopg connection. Runs one SELECT and returns
    ``{"scheme": …, "legacy_keys": N, "split_keys": M, "impacts": […]}`` —
    ``split_keys`` counts how many global keys decompose into more than one
    scoped candidate (the auto-union exposure P32.3 removes going forward).
    """
    with conn.cursor() as cur:
        cur.execute(_REPORT_SQL, (PARTNER_NAME_SCHEME,))
        rows = [
            {
                "name_key": r[0],
                "entity_id": r[1],
                "label": r[2],
                "source_id": r[3],
                "predicate_id": r[4],
            }
            for r in cur.fetchall()
        ]
    impacts = _impacts_from_rows(rows)
    return {
        "scheme": PARTNER_NAME_SCHEME,
        "dry_run": True,
        "legacy_keys": len(impacts),
        "split_keys": sum(1 for i in impacts if i.split_count > 1),
        "impacts": [i.as_dict() for i in impacts],
    }
