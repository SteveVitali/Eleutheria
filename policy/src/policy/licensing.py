# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The N-compartment export licence model and its gates (§42.2/42.4).

The export architecture is an **N-compartment model keyed on the rights record**
(SIG-LIC-004a), not a fixed two-way split. Each mutually-incompatible licence
regime is its own separable compartment, and the set of compartments is **data,
not code** (``policy/data/licenses.toml``): adding a source under a new
share-alike licence is a data row, never a schema or code change.

Three gates are enforced here:

* **Export gate (SIG-LIC-004).** ``UNDETERMINED`` rights, or a source not marked
  ``redistributable``, fail the export gate *closed*.
* **Compatibility gate (SIG-LIC-004a/010).** An export licence is *computed* from
  constituent rights; the build fails on incompatibility. ODbL-1.0 and
  CC-BY-SA-4.0 are not mergeable with each other, and neither may be folded into
  a CC-BY-4.0 export. A deliberate cross-compartment merge raises.
* **Training gate (SIG-LIC-004c).** Content whose rights do not permit AI
  training MUST NOT be routed through a model-training pipeline, enforced at the
  data layer.

Silently-travelling share-alike (SIG-LIC-009a): where a record's provenance is a
share-alike upstream, the *stricter* upstream regime governs, not the declared
permissive one.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from ._data import load_table
from .rights import RightsRecord, is_undetermined


class ExportGateClosed(Exception):
    """Raised when unresolved or non-redistributable rights reach the export gate."""


class LicenseIncompatibilityError(Exception):
    """Raised when constituent rights cannot be combined into any export licence."""


class TrainingNotPermitted(Exception):
    """Raised when ai-train=no content is routed toward a training pipeline."""


def _registry(registry: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return registry if registry is not None else load_table("licenses")


def effective_license(record: RightsRecord, registry: Mapping[str, Any] | None = None) -> str:
    """The licence that actually governs export placement for ``record``.

    Normally the declared ``spdx``. But a silently-travelling share-alike
    obligation does not disappear because an intermediary failed to pass it on
    (SIG-LIC-009a): if the record names a share-alike ``upstream_license``, that
    stricter regime governs. And where the upstream provenance cannot be resolved —
    an ``upstream_license`` that is not in the compartment registry — the spec says
    default to the **stricter** regime, not the declared permissive one; returning the
    unknown upstream makes :func:`compute_export_license` fail the build closed rather
    than silently laundering an obligation SIG cannot vouch for.
    """
    reg = _registry(registry)["licenses"]
    upstream = record.upstream_license
    if upstream:
        facts = reg.get(upstream)
        if facts is None or facts.get("share_alike"):
            return upstream
    return record.spdx


def assert_export_permitted(records: Iterable[RightsRecord]) -> None:
    """Fail closed on any source that may not be published (SIG-LIC-004)."""
    for record in records:
        if is_undetermined(record):
            raise ExportGateClosed(
                f"source {record.source_id!r} has UNDETERMINED rights; the export "
                "gate fails closed (SIG-LIC-004)."
            )
        if not record.redistributable:
            raise ExportGateClosed(
                f"source {record.source_id!r} is not marked redistributable "
                "(SIG-LIC-003); the export gate fails closed."
            )


def compute_export_license(
    records: Iterable[RightsRecord],
    registry: Mapping[str, Any] | None = None,
) -> str:
    """Compute the single SPDX licence a set of rights may be exported under.

    Returns the licence, or raises :class:`LicenseIncompatibilityError` if the
    records span mutually-incompatible regimes (SIG-LIC-004a/010). This is the
    per-compartment compatibility gate; the CI test suite drives a deliberate
    cross-compartment merge through it and asserts the build fails.
    """
    records = list(records)
    assert_export_permitted(records)
    reg = _registry(registry)["licenses"]

    if not records:
        raise LicenseIncompatibilityError("cannot compute an export licence for zero sources")

    candidate: set[str] | None = None
    for record in records:
        spdx = effective_license(record, registry)
        if spdx not in reg:
            raise LicenseIncompatibilityError(
                f"source {record.source_id!r} declares licence {spdx!r}, which is not "
                "in the compartment registry (licenses.toml)."
            )
        allowed = set(reg[spdx]["relicensable_to"])
        candidate = allowed if candidate is None else (candidate & allowed)

    assert candidate is not None
    if not candidate:
        licences = sorted({effective_license(r, registry) for r in records})
        raise LicenseIncompatibilityError(
            f"licences {licences} are mutually incompatible and cannot be merged "
            "into one export compartment (SIG-LIC-004a)."
        )
    # Deterministic choice: the most-constraining common target (share-alike
    # first, then lexical) so an export never silently loosens obligations.
    return _most_constraining(candidate, reg)


def _most_constraining(candidates: set[str], reg: Mapping[str, Any]) -> str:
    return sorted(candidates, key=lambda spdx: (not reg[spdx].get("share_alike", False), spdx))[0]


def most_permissive_license(
    records: Iterable[RightsRecord],
    registry: Mapping[str, Any] | None = None,
) -> str:
    """The *least*-constraining licence a set of rights may all be published under.

    The mirror of :func:`compute_export_license`: same relicensable-set intersection
    and same fail-closed / incompatibility behaviour, but it returns the most permissive
    common target rather than the strictest. The crosswalk (SIG-IDENT-033) is published
    under the most permissive licence its constituents allow (SIG-EXPORT-007), so its
    reuse is maximised — but it still cannot escape the licence math: incompatible
    constituents raise exactly as the ordinary gate does.
    """
    records = list(records)
    assert_export_permitted(records)
    reg = _registry(registry)["licenses"]

    if not records:
        raise LicenseIncompatibilityError("cannot compute an export licence for zero sources")

    candidate: set[str] | None = None
    for record in records:
        spdx = effective_license(record, registry)
        if spdx not in reg:
            raise LicenseIncompatibilityError(
                f"source {record.source_id!r} declares licence {spdx!r}, which is not "
                "in the compartment registry (licenses.toml)."
            )
        allowed = set(reg[spdx]["relicensable_to"])
        candidate = allowed if candidate is None else (candidate & allowed)

    assert candidate is not None
    if not candidate:
        licences = sorted({effective_license(r, registry) for r in records})
        raise LicenseIncompatibilityError(
            f"licences {licences} are mutually incompatible and cannot be merged "
            "into one export compartment (SIG-LIC-004a)."
        )
    # Reuse-maximising order: the fewest obligations first — not share-alike before
    # share-alike, then no-attribution before attribution — then lexical for determinism.
    return sorted(
        candidate,
        key=lambda spdx: (
            reg[spdx].get("share_alike", False),
            reg[spdx].get("attribution_required", True),
            spdx,
        ),
    )[0]


def assert_training_allowed(record: RightsRecord) -> None:
    """Gate a source toward a model-training pipeline (SIG-LIC-004c).

    Enforced at the data layer: content whose rights record does not carry the
    ``ai_training_permitted`` grant MUST NOT enter a training pipeline,
    regardless of how permissive its licence string is. This does not restrict
    §25 model-*assisted extraction* (inference over a document, not training).
    """
    if not record.ai_training_permitted:
        raise TrainingNotPermitted(
            f"source {record.source_id!r} is not marked ai_training_permitted "
            "(SIG-LIC-004b/004c); it MUST NOT be routed to a training pipeline."
        )


def compartments() -> dict[str, dict[str, Any]]:
    """The declared export compartments (SIG-LIC-005), loaded from data."""
    return load_table("licenses")["compartments"]


def downstream_obligations(
    record: RightsRecord, registry: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """The attribution/provenance obligations to pass downstream, per row (SIG-LIC-011).

    A downstream consumer must be able to comply without re-deriving the chain,
    so each exported row carries its licence, whether attribution is required,
    the attribution string, whether the obligation is share-alike, and the
    provenance (including any stricter upstream regime, SIG-LIC-009a).
    """
    reg = _registry(registry)["licenses"]
    governing = effective_license(record, registry)
    facts = reg.get(governing, {})
    return {
        "source_id": record.source_id,
        "license": governing,
        "attribution_required": bool(facts.get("attribution_required", True)),
        "attribution": record.attribution,
        "share_alike": bool(facts.get("share_alike", False)),
        "terms_url": record.terms_url,
        "upstream_license": record.upstream_license,
    }
