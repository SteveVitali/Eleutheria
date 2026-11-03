# SPDX-License-Identifier: Apache-2.0
"""P36.58 (R11-K13-RQ-01): the gap-routing + task-code tables (SIG-RQ-005/001/003).

The routing matrix test K11 §8 names: every §32.1 peer-class ``tracked``
predicate has an explicit route (never a substring guess), every routed task
type exists in the §33.2 catalog or is declared catalog-pending, and the
subject-grain copy test — no subject-grain task type's closing-condition text
speaks of "the jurisdiction".
"""

from __future__ import annotations

from inference.peer_classes import load_peer_classes
from tasks.catalog import CATALOG_SIZE, catalog
from tasks.research_pg import CLOSING_CONDITION_TEXT
from tasks.routing import (
    LANES,
    PENDING_CATALOG_TYPES,
    load_gap_routing,
    load_task_codes,
)


def test_every_tracked_predicate_has_an_explicit_route() -> None:
    routes = load_gap_routing()
    tracked = {p for pc in load_peer_classes() for p in pc.tracked}
    missing = sorted(p for p in tracked if p not in routes)
    assert not missing, f"tracked predicates with no explicit route: {missing}"


def test_routing_table_names_only_known_predicates() -> None:
    routes = load_gap_routing()
    tracked = {p for pc in load_peer_classes() for p in pc.tracked}
    extra = sorted(p for p in routes if p not in tracked)
    assert not extra, f"routes naming predicates no peer class tracks: {extra}"


def test_lanes_are_the_closed_vocabulary() -> None:
    for pred, route in load_gap_routing().items():
        assert route.lane in LANES, f"{pred}: lane {route.lane!r}"
        assert route.grain in ("subject", "jurisdiction"), f"{pred}: grain {route.grain!r}"


def test_routed_task_types_are_catalog_or_declared_pending() -> None:
    known = set(catalog().slugs()) | set(PENDING_CATALOG_TYPES)
    for pred, route in load_gap_routing().items():
        if route.route is not None:
            assert route.route in known, f"{pred}: route {route.route!r} not catalog/pending"
            # a pending-type route is always declared pending, never a drifted slug
        assert route.template is None or route.lane == "research"


def test_task_codes_cover_the_catalog() -> None:
    codes = load_task_codes()
    slugs = catalog().slugs()
    assert len(slugs) == CATALOG_SIZE
    missing = sorted(s for s in slugs if s not in codes.by_type)
    assert not missing, f"catalog types with no handle code: {missing}"
    pendings = {t for t, e in codes.by_type.items() if e.catalog_pending}
    assert pendings == set(PENDING_CATALOG_TYPES)


def test_handle_codes_are_unique_mnemonics() -> None:
    codes = load_task_codes()
    seen: dict[str, str] = {}
    for tt, e in codes.by_type.items():
        assert e.code.isalpha() and e.code.islower() and 2 <= len(e.code) <= 10
        assert e.code not in seen, f"code {e.code!r} claimed by {seen[e.code]!r} and {tt!r}"
        seen[e.code] = tt


def test_titles_name_the_subject() -> None:
    for tt, e in load_task_codes().by_type.items():
        assert "{subject}" in e.title, f"{tt}: title template has no {{subject}}"


def test_subject_grain_closing_text_never_says_jurisdiction() -> None:
    """K11 §8's copy test: a task whose routing grain is ``subject`` must not
    close on "the jurisdiction" (RC-6 — a per-camera gap is not a place gap)."""
    routes = load_gap_routing()
    subject_grain_types = {r.route for r in routes.values() if r.route and r.grain == "subject"}
    subject_grain_types.add("coverage_hole")  # minted per-object by the detector
    for closing_type, text in CLOSING_CONDITION_TEXT.items():
        if closing_type in subject_grain_types:
            assert "jurisdiction" not in text.lower(), (
                f"{closing_type}: subject-grain closing text names 'jurisdiction' — {text!r}"
            )


def test_osm_field_predicates_route_to_campaigns_and_registry_to_metrics() -> None:
    """D-K11-1 as answered: OSM-mappable fields aggregate to campaigns;
    DOT-registry-only fields stay coverage metrics."""
    routes = load_gap_routing()
    for pred in ("brand", "operator_stated", "camera_mount", "surveillance_zone"):
        assert routes[pred].lane == "campaign", f"{pred} should be a mapping campaign"
    for pred in ("camera_operator", "camera_name", "camera_latitude", "camera_status"):
        assert routes[pred].lane == "metric", f"{pred} should stay a coverage metric"


def test_named_research_routes() -> None:
    """K11 §4.1's explicit rows: retention/sharing route to the pending types,
    contract predicates to missing_contract."""
    routes = load_gap_routing()
    assert routes["configured_retention_days"].route == "retention_unknown"
    assert routes["configured_sharing_partner"].route == "sharing_unknown"
    assert routes["configured_retention_days"].template == "surveillance_policy"
    assert routes["seller"].route == "missing_contract"
    assert routes["seller"].template == "alpr_contract"
