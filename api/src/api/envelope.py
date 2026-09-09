# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Assemble the §37 response objects from the existing engines — never reinvent.

Every function here is pure and adapts one already-built value object into the
hand-written wire model:

* :func:`resolution_envelope` wraps the resolver's :class:`reconcile.resolve.Resolution`
  into the §37.1 envelope (SIG-API-002) — the value only ever leaves the API
  inside this envelope.
* :func:`coverage_statement` renders :class:`inference.coverage.CoverageRecord`
  objects into the per-response coverage statement (§32.2, SIG-API-003).
* :func:`license_statement` / :func:`attribution_for` compute the collection
  licence and upstream attribution from :class:`policy.rights.RightsRecord` rows
  via :mod:`policy.licensing` (§42.4, SIG-API-004).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from inference.coverage import CoverageRecord
from policy.licensing import (
    ExportGateClosed,
    LicenseIncompatibilityError,
    compute_export_license,
    downstream_obligations,
)
from policy.rights import RightsRecord
from reconcile.resolve import Resolution

from .models import (
    Attribution,
    CoverageStatement,
    LicenseStatement,
    MaterialFact,
    Rationale,
    ResolutionEnvelope,
)


class BareValueError(RuntimeError):
    """Raised if code ever tries to emit a material value outside an envelope.

    SIG-API-002 forbids returning a bare value; the API wraps every value in a
    :class:`ResolutionEnvelope` by construction, and this guard makes an
    accidental bare-value path fail loudly rather than leak.
    """


def resolution_envelope(resolution: Resolution) -> ResolutionEnvelope:
    """Adapt a resolver :class:`Resolution` into the §37.1 envelope (SIG-API-002)."""
    return ResolutionEnvelope(
        value=resolution.value,
        resolution_status=resolution.resolution_status,
        support=resolution.support,
        agreement=resolution.agreement,
        currency=resolution.currency,
        rationale=Rationale(code=resolution.rationale_code, text=resolution.rationale_text),
        supporting_claim_ids=list(resolution.supporting_claim_ids),
        dissenting_claim_ids=list(resolution.dissenting_claim_ids),
        as_of_world=resolution.as_of_world,
        as_of_belief=resolution.as_of_belief,
        ruleset_version=resolution.ruleset_version,
        contradiction_state=resolution.contradiction_state,
        winning_claim_id=resolution.winning_claim_id,
        considered_claim_ids=list(resolution.considered_claim_ids),
        resolver_version=resolution.resolver_version,
        input_digest=resolution.input_digest,
        unresolved_code=resolution.unresolved_code,
    )


def material_fact(resolution: Resolution) -> MaterialFact:
    """A (subject, predicate) material fact carrying its envelope (SIG-API-002)."""
    return MaterialFact(
        subject_id=resolution.subject_id,
        predicate_id=resolution.predicate_id,
        envelope=resolution_envelope(resolution),
    )


def coverage_statement(scope: str, records: Iterable[CoverageRecord]) -> CoverageStatement:
    """Render coverage records into the §32.2 statement (SIG-API-003).

    "Evaluated" is any record whose epistemic state is decided; "not evaluable"
    is a ``not_researched`` record — the explicit, explained gap §3.1 requires.
    """
    views = [r.public_view() for r in records]
    not_evaluable = sum(1 for r in views if r["absence_kind"] == "not_researched")
    evaluated = len(views) - not_evaluable
    return CoverageStatement(
        scope=scope,
        complete=not_evaluable == 0,
        evaluated=evaluated,
        not_evaluable=not_evaluable,
        records=views,
    )


def empty_coverage(scope: str) -> CoverageStatement:
    """A coverage statement for a resource with nothing left unevaluated."""
    return CoverageStatement(scope=scope, complete=True, evaluated=0, not_evaluable=0, records=[])


def attribution_for(rights: Iterable[RightsRecord]) -> list[Attribution]:
    """Upstream attribution for the constituent sources (SIG-API-004/CONTRIB-020)."""
    out: list[Attribution] = []
    for record in rights:
        ob = downstream_obligations(record)
        out.append(
            Attribution(
                source_id=ob["source_id"],
                attribution=ob["attribution"],
                license=ob["license"],
                attribution_required=ob["attribution_required"],
                share_alike=ob["share_alike"],
                terms_url=ob["terms_url"],
                upstream_license=ob["upstream_license"],
            )
        )
    return out


def license_statement(rights: Sequence[RightsRecord]) -> LicenseStatement:
    """Compute a collection's licence statement from constituent rights (§42.4).

    Reuses :func:`policy.licensing.compute_export_license`: when the constituents
    share a mergeable compartment there is a single SPDX; when they span
    mutually-incompatible regimes there is none, and the distinct effective
    licences are listed as compartments rather than silently merged (SIG-LIC-004a).
    """
    obligations = attribution_for(rights)
    if not rights:
        return LicenseStatement(
            effective_license=None, single_license=False, compartments=[], obligations=[]
        )
    try:
        effective = compute_export_license(rights)
        return LicenseStatement(
            effective_license=effective,
            single_license=True,
            compartments=[effective],
            obligations=obligations,
        )
    except LicenseIncompatibilityError:
        # Constituents span mutually-incompatible compartments: report both rather
        # than fabricate a single merged licence (SIG-LIC-004a).
        compartments = sorted({ob.license for ob in obligations})
        return LicenseStatement(
            effective_license=None,
            single_license=False,
            compartments=compartments,
            obligations=obligations,
        )
    except ExportGateClosed:
        # A source is UNDETERMINED or not redistributable: the collection has no
        # publishable licence at all. Report the gate is closed, never a licence
        # (SIG-LIC-004, fail closed).
        return LicenseStatement(
            effective_license=None,
            single_license=False,
            compartments=["EXPORT-GATE-CLOSED"],
            obligations=obligations,
        )
