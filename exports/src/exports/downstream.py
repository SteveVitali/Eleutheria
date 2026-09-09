# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The six downstream application classes as validated design targets (§38.4).

The export portfolio MUST be validated against **six named downstream application
classes** (SIG-EXPORT-010, OL-15.7-01): for each, SIG must be able to *name the specific
artifact that serves it*, and a class with no serving artifact is an export-design
defect — not an aspiration. This module encodes the six classes and their required
serving capabilities as data, and :func:`validate` reports any unserved class.

Where two classes' needs conflict — route/privacy applications want the device layer
*alone* while researchers want it *joined* — SIG serves them as **separate artifacts**
rather than one compromise artifact (SIG-EXPORT-011); this is the same separation the
ODbL/CC-BY licence split (§42.3) forces, so the two constraints agree.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationClass:
    """One §38.4 downstream class: the capabilities its serving artifact must provide."""

    key: str
    label: str
    required_capabilities: frozenset[str]
    serving_artifact: str


#: The six classes of §38.4. `required_capabilities` are matched against the set a
#: release + the surrounding surfaces (the P14.1 API, the procurement feed) provide;
#: ALL must be present for the class to be served.
DOWNSTREAM_CLASSES: tuple[ApplicationClass, ...] = (
    ApplicationClass(
        "academic",
        "Academic analysis",
        frozenset({"parquet", "crosswalk", "zenodo_doi"}),
        "Parquet + the crosswalk export + Zenodo DOIs",
    ),
    ApplicationClass(
        "newsroom",
        "Newsroom tools",
        frozenset({"json_api", "evidence_links", "belief_pinned_permalinks"}),
        "JSON API + per-claim evidence links + belief-pinned permalinks",
    ),
    ApplicationClass(
        "local_dashboard",
        "Local dashboards",
        frozenset({"jurisdiction_slice"}),
        "Per-jurisdiction JSON/CSV slices",
    ),
    ApplicationClass(
        "route_privacy",
        "Route / privacy applications",
        frozenset({"pmtiles", "geojson", "odbl_asset_layer"}),
        "PMTiles + GeoJSON of the ODbL asset layer",
    ),
    ApplicationClass(
        "policy_tracker",
        "Policy trackers",
        frozenset({"procurement_feed", "ical_rss"}),
        "The procurement/renewal feed + iCal/RSS",
    ),
    ApplicationClass(
        "visualization",
        "Visualizations",
        frozenset({"edge_list", "crosswalk"}),
        "The edge list + entity crosswalk",
    ),
)


@dataclass(frozen=True)
class ClassCoverage:
    """Whether one application class is served, and what it is missing if not."""

    application_class: ApplicationClass
    served: bool
    missing: frozenset[str]


def validate(available_capabilities: Iterable[str]) -> list[ClassCoverage]:
    """For each of the six classes, whether the available capabilities serve it (SIG-EXPORT-010)."""
    available = set(available_capabilities)
    out: list[ClassCoverage] = []
    for klass in DOWNSTREAM_CLASSES:
        missing = klass.required_capabilities - available
        out.append(ClassCoverage(klass, not missing, frozenset(missing)))
    return out


def defects(available_capabilities: Iterable[str]) -> list[ClassCoverage]:
    """The application classes with no serving artifact — export-design defects (SIG-EXPORT-010)."""
    return [c for c in validate(available_capabilities) if not c.served]


class DownstreamDesignDefect(Exception):
    """Raised when a §38.4 application class has no serving artifact."""


def assert_all_served(available_capabilities: Iterable[str]) -> None:
    """Fail loudly if any of the six classes is unserved (SIG-EXPORT-010)."""
    unserved = defects(available_capabilities)
    if unserved:
        detail = "; ".join(
            f"{c.application_class.label} missing {sorted(c.missing)}" for c in unserved
        )
        raise DownstreamDesignDefect(
            f"export portfolio does not serve {len(unserved)} downstream class(es): {detail} "
            "(SIG-EXPORT-010)."
        )


def assert_separate_serving_artifacts(
    route_privacy_paths: Iterable[str], researcher_paths: Iterable[str]
) -> None:
    """Assert the route/privacy and researcher artifacts are disjoint (SIG-EXPORT-011).

    The device-layer-alone artifact (route/privacy) and the joined graph artifact
    (researcher) must be *different files*, never one compromise artifact — which the
    ODbL/CC-BY compartment split already guarantees, but is asserted here so a future
    regression that merged them is caught.
    """
    overlap = set(route_privacy_paths) & set(researcher_paths)
    if overlap:
        raise DownstreamDesignDefect(
            f"route/privacy and researcher classes share artifact(s) {sorted(overlap)}; "
            "they must be served as separate artifacts (SIG-EXPORT-011)."
        )


__all__ = [
    "ApplicationClass",
    "DOWNSTREAM_CLASSES",
    "ClassCoverage",
    "validate",
    "defects",
    "DownstreamDesignDefect",
    "assert_all_served",
    "assert_separate_serving_artifacts",
]
