# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Publication policy: exclusions, de-pseudonymisation, jurisdiction (§43).

Three enforceable rules beyond the officer test and the coordinate matrix:

* **Categorical exclusions (SIG-PUB-002/003).** Certain data MUST NOT be stored
  in any tier at any sensitivity level. No balancing test applies.
* **SIG must never become the de-pseudonymisation join (§43.2a).** Operator/user
  identifiers in third-party audit data are hashed with a *held-back salt* at
  ingest; raw values are never stored in a publishable tier or republished,
  regardless of prior publication (SIG-PUB-003a). SIG MUST NOT expose any surface
  joinable on an operator identifier or permitting per-operator aggregation
  (SIG-PUB-003b).
* **Jurisdiction-conditional publication (SIG-PUB-017).** A single global rule is
  not available; the engine evaluates both the data subject's jurisdiction and
  the record's origin.
"""

from __future__ import annotations

import hashlib

from ._data import load_table


class CategoricallyExcluded(Exception):
    """Raised when categorically excluded data is offered for storage (SIG-PUB-002)."""


class DePseudonymisationError(Exception):
    """Raised when a surface would enable the de-pseudonymisation join (§43.2a)."""


def excluded_kinds() -> frozenset[str]:
    """The categorically excluded data kinds (§43.2), loaded from data."""
    return frozenset(row["kind"] for row in load_table("exclusions")["excluded"])


def is_categorically_excluded(kind: str) -> bool:
    """Whether ``kind`` may never be stored, in any tier (SIG-PUB-002/003)."""
    return kind in excluded_kinds()


def assert_storable(kind: str) -> None:
    """Raise :class:`CategoricallyExcluded` if ``kind`` is categorically excluded."""
    if is_categorically_excluded(kind):
        raise CategoricallyExcluded(
            f"{kind!r} is categorically excluded (§43.2, SIG-PUB-002); no balancing "
            "test applies and it MUST NOT be stored in any tier."
        )


def hash_operator_identifier(raw: str, salt: str) -> str:
    """Hash an operator/user identifier with a held-back salt at ingest (SIG-PUB-003a).

    The raw value MUST NEVER be stored in a publishable tier or republished —
    regardless of the fact that a third party has already published it
    (SIG-PUB-003c). Callers store only this digest.
    """
    if not salt:
        raise ValueError("a held-back salt is required (SIG-PUB-003a); refusing empty salt")
    return hashlib.sha256(f"{salt}:{raw}".encode()).hexdigest()


def assert_no_operator_join(
    *, joinable_on_operator_id: bool, per_operator_aggregation: bool
) -> None:
    """Reject a surface that would enable the de-pseudonymisation join (SIG-PUB-003b).

    SIG is uniquely positioned to be the thing that makes the join work —
    reconciling identities across projects is exactly what SIG is for — and this
    is the one place that capability MUST be withheld. A publishable table
    joinable on an operator identifier, or an API permitting per-operator
    aggregation, is forbidden.
    """
    if joinable_on_operator_id:
        raise DePseudonymisationError(
            "a table joinable on an operator identifier is forbidden (SIG-PUB-003b)."
        )
    if per_operator_aggregation:
        raise DePseudonymisationError(
            "an API permitting per-operator aggregation is forbidden (SIG-PUB-003b)."
        )


def _jurisdiction_allows_employee_names(code: str) -> bool:
    table = load_table("jurisdictions")
    entry = table["jurisdictions"].get(code)
    if entry is None:
        return bool(table["defaults"]["public_employee_names_publishable"])
    return bool(entry["public_employee_names_publishable"])


def publication_permitted(
    subject_jurisdiction: str,
    record_origin_jurisdiction: str,
    *,
    is_public_employee_name: bool,
) -> bool:
    """Jurisdiction-conditional publication of a public-employee name (SIG-PUB-017).

    Both the data subject's jurisdiction and the record's origin jurisdiction
    must permit publication; unknown jurisdictions default to the conservative
    (no-publish) posture. Non-employee-name material is not gated by this rule.
    """
    if not is_public_employee_name:
        return True
    return _jurisdiction_allows_employee_names(
        subject_jurisdiction
    ) and _jurisdiction_allows_employee_names(record_origin_jurisdiction)
