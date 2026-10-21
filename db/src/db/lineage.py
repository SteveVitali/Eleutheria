# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Declared lineage / namespace vocabulary + the claim-level lineage record
(P35.25 / R11-L3-CP4, SIG-CONF-014; design CP-4).

Two honest states anchor everything here:

* ``undeclared`` — a claim/source carrying NO lineage or namespace
  declaration. It is a recorded state, never a guess and never "independent".
* ``unclassified`` — the resolved independence class undeclared material
  carries. Corroboration counts only DISTINCT declared classes; every
  unclassified claim shares the one pseudo-class, so two undeclared voices
  agreeing are ONE voice, and an undeclared voice can never corroborate a
  declared one.

``data/id_namespaces.toml`` is the single committed vocabulary of shared
upstream identifier spaces (the ``osm.element`` / ``deflock.node`` / ``dot_511``
family). A source's own private space is ``src:<source-id>`` — declared in
``sources.toml``, needing no row here, and equal only within that source.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any

_VOCAB_RESOURCE = "id_namespaces.toml"

#: The independence-class token for material whose lineage is undeclared or
#: unresolvable (SIG-CONF-014, CP-4). Shared by every undeclared claim — one
#: pseudo-class, so undeclared content can never read as independent voices.
UNCLASSIFIED = "unclassified"

#: The ``id_namespace``/``lineage_kind`` token for an absent declaration.
#: Recorded explicitly (never NULL) so lineage-completeness verification is a
#: plain NOT NULL scan — "every claim has an id_namespace or the explicit
#: `undeclared` marker" (the ticket's L3 leg).
UNDECLARED = "undeclared"

#: A source-private identifier space: ``src:<source-id>``. Two refs under
#: different ``src:`` namespaces can never be the same upstream identifier.
SELF_NAMESPACE_PREFIX = "src:"


@cache
def _doc() -> dict[str, Any]:
    data = files(__package__).joinpath("data", _VOCAB_RESOURCE).read_bytes()
    return tomllib.loads(data.decode("utf-8"))


def namespace_version() -> str:
    """The declared vocabulary version, stamped on lineage rows/reports."""
    version = str(_doc().get("version") or "").strip()
    if not version:
        raise ValueError(f"{_VOCAB_RESOURCE}: missing version")
    return version


@cache
def namespaces() -> frozenset[str]:
    """Every declared shared identifier namespace (the vocabulary)."""
    out = {str(row["id"]).strip() for row in _doc().get("namespace", [])}
    out.discard("")
    if not out:
        raise ValueError(f"{_VOCAB_RESOURCE}: no [[namespace]] rows")
    return frozenset(out)


def known_namespace(token: str) -> bool:
    """Whether ``token`` is a declared shared namespace (``src:`` privates are
    checked by shape at their own layer — a private space needs no row here)."""
    return token in namespaces()


def valid_namespace_token(token: str) -> bool:
    """Whether ``token`` may be recorded as a claim/source ``id_namespace``:
    a declared shared namespace, a ``src:<source-id>`` private space, or the
    explicit ``undeclared`` marker."""
    if token == UNDECLARED:
        return True
    if token.startswith(SELF_NAMESPACE_PREFIX):
        return (
            len(token) > len(SELF_NAMESPACE_PREFIX)
            and ":" not in token[len(SELF_NAMESPACE_PREFIX) :]
        )
    return known_namespace(token)


@dataclass(frozen=True)
class ClaimLineage:
    """The lineage triple a ``claim_lineage`` row records for one claim.

    * ``source_id`` — the registry source the claim was minted from.
    * ``id_namespace`` — the declared namespace the subject/upstream refs live
      in (``undeclared`` when nothing is declared).
    * ``lineage_kind`` — the source's declared lineage kind (``undeclared`` by
      default; never inferred).
    * ``independence_class`` — the resolved corroboration class
      (``unclassified`` when undeclared/unresolvable).
    * ``basis`` — where the row's values came from: ``registry:<version>``
      (emit-time resolution), ``rematerialize:<run>`` (the append-only
      backfill), or ``undeclared`` (no declaration exists).
    """

    source_id: str
    id_namespace: str = UNDECLARED
    lineage_kind: str = UNDECLARED
    independence_class: str = UNCLASSIFIED
    basis: str = UNDECLARED


__all__ = [
    "ClaimLineage",
    "SELF_NAMESPACE_PREFIX",
    "UNCLASSIFIED",
    "UNDECLARED",
    "known_namespace",
    "namespace_version",
    "namespaces",
    "valid_namespace_token",
]
