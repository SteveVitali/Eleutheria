# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The source-lineage declarations artifact generator (P35.25 / R11-L3-CP4;
SIG-CONF-014, ADR-213 — design CP-4).

``sig-connectors source-lineage-list`` emits the committed declaration list
``sig-db lineage-rematerialize`` consumes: one row per registry source carrying
the source's DECLARED lineage signature — kind, upstream references
(``mirror_of`` / ``derived_from`` / ``origin``), the resolved
``independence_class``, the declared ``id_namespace``, and the documentary
``evidence`` the declaration names. The artifact is generated from
``sources.toml`` (the ``[lineage]`` blocks are the authoritative input),
written under ``docs/build/reports/lineage/`` and COMMITTED; a reviewer may
edit rows, and ``load_declarations`` fail-closed-validates whatever it reads —
the artifact is the control surface, not the registry.

``registry_version`` is the content digest of the sorted declaration rows: a
declaration change mints a new version, so ``source_lineage`` gains a new
``(source_id, registry_version)`` row — the append-only versioning the table's
primary key encodes. A source with no ``[lineage]`` block still appears,
declared as the honest ``undeclared``/``unclassified`` state — the rematerialize
leg records that explicitly rather than leaving the lineage unknown.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from .registry import resolve_independence_class
from .registry import sources as _registry_sources

#: The schema id the committed declarations artifact carries.
DECLARATIONS_SCHEMA = "sig.source-lineage/1"

#: The canonical output path — committed under the lineage-reports tree.
DEFAULT_OUTPUT = Path("docs/build/reports/lineage/p35_25_declarations.json")


def declarations_list() -> dict[str, Any]:
    """The artifact document: one declaration row per registered source.

    Determinism: rows are emitted in registry ``source_id`` order and the
    ``registry_version`` is a content digest of exactly those rows — the same
    registry always mints the same version.
    """
    records = _registry_sources()
    by_id = {r.id: r for r in records}
    rows: list[dict[str, Any]] = []
    for rec in records:
        lin = rec.lineage
        rows.append(
            {
                "source_id": rec.id,
                "kind": lin.kind.value,
                "origin": lin.origin,
                "mirror_of": lin.mirror_of,
                "derived_from": list(lin.derived_from),
                # The RESOLVED claim-level class (transitive mirror/derived
                # resolution) — what claim_lineage.independence_class stamps.
                "independence_class": resolve_independence_class(rec, by_id),
                "id_namespace": lin.id_namespace or "undeclared",
                "collection_method": lin.collection_method,
                "evidence": lin.evidence,
            }
        )
    version = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:16]
    return {
        "schema": DECLARATIONS_SCHEMA,
        "generated_from": "connectors/src/connectors/data/sources.toml",
        "registry_version": f"sources.toml+{version}",
        "note": (
            "Declared lineage + independence classes for `sig-db "
            "lineage-rematerialize` (P35.25 / SIG-CONF-014). Generated from the "
            "registry's [lineage] blocks; a reviewer may edit rows before "
            "commit. `undeclared`/`unclassified` rows are recorded explicitly "
            "— absent lineage is the honest unknown state, never 'independent'."
        ),
        "sources": rows,
        "totals": {
            "sources": len(rows),
            "declared": sum(1 for r in rows if r["kind"] != "undeclared"),
            "unclassified": sum(1 for r in rows if r["independence_class"] == "unclassified"),
        },
    }


def write_declarations_list(out_path: Path | None = None, *, today: date | None = None) -> Path:
    """Serialise the artifact to ``out_path`` (canonical JSON, committed)."""
    doc = declarations_list()
    doc["generated_on"] = (today or date.today()).isoformat()
    path = out_path or DEFAULT_OUTPUT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


__all__ = [
    "DECLARATIONS_SCHEMA",
    "DEFAULT_OUTPUT",
    "declarations_list",
    "write_declarations_list",
]
