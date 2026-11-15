# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The task-surface data tables (P36.58 / R11-K13-RQ-01).

Two committed, versioned registries (SIG-ENG-001 — data, not code):

* ``task_codes.toml`` — the K11 §3 handle-code registry: per-type mnemonic
  (``T-<place>-<code>-<slug>-<hash>``), the plain-language type label and the
  title template the export renders (SIG-RQ-001/003).
* ``gap_routing.toml`` — the explicit predicate → presentation-lane table
  (SIG-RQ-005): every §32.1 peer-class ``tracked`` predicate routes to
  ``research`` | ``campaign`` | ``metric`` (D-K11-1, answered
  "as recommended"), replacing the retired substring match as the routing
  authority. The detector rewiring itself is RQ-02 (P37.35); the export
  presents lanes from this table today.

Both load through :mod:`tasks._data` with closed-vocabulary validation at
load — a bad row fails loudly, never silently.
"""

from __future__ import annotations

from dataclasses import dataclass

from ._data import load_table

__all__ = [
    "LANES",
    "PENDING_CATALOG_TYPES",
    "GapRoute",
    "TaskCode",
    "TaskCodes",
    "load_gap_routing",
    "load_task_codes",
]

#: The closed lane vocabulary (D-K11-1): research | campaign | metric.
LANES: tuple[str, ...] = ("research", "campaign", "metric")

#: The closed subject-grain vocabulary (SIG-RQ-005 — the closing condition
#: must match its subject grain).
GRAINS: tuple[str, ...] = ("subject", "jurisdiction")

#: Task types the routing table may name before the catalog registers them.
#: P37.35 (RQ-02) landed `retention_unknown`/`sharing_unknown` as §33.2 rows
#: 35/36 — none is pending today; the mechanism stands for the next
#: catalog-pending type. Any other unregistered ``route`` value fails the load.
PENDING_CATALOG_TYPES: frozenset[str] = frozenset()


@dataclass(frozen=True)
class TaskCode:
    """One ``task_codes.toml`` row: handle code + plain label + title template."""

    task_type: str
    code: str
    label: str
    title: str
    catalog_pending: bool


@dataclass(frozen=True)
class TaskCodes:
    """The parsed code registry keyed by task type."""

    version: str
    by_type: dict[str, TaskCode]


@dataclass(frozen=True)
class GapRoute:
    """One ``gap_routing.toml`` row: the lane a coverage predicate presents on."""

    predicate: str
    lane: str
    route: str | None  # the task type the table asserts (may be catalog-pending)
    template: str | None  # the §36 request-template family, when records-obtainable
    grain: str


def load_task_codes() -> TaskCodes:
    """The handle-code registry — validated, fail-closed.

    Codes are ``[a-z]{2,10}`` and unique; a ``catalog_pending`` flag is the only
    way a row may name a type the §33.2 catalog does not register.
    """
    raw = load_table("task_codes")
    version = str(raw.get("version") or "")
    if not version:
        raise ValueError("task_codes.toml must declare a 'version'")
    by_type: dict[str, TaskCode] = {}
    codes: dict[str, str] = {}
    for i, entry in enumerate(raw.get("type") or ()):
        tt = str(entry.get("task_type") or "")
        code = str(entry.get("code") or "")
        label = str(entry.get("label") or "")
        title = str(entry.get("title") or "")
        pending = bool(entry.get("catalog_pending"))
        if not tt:
            raise ValueError(f"task_codes.toml row #{i} has no task_type")
        if tt in by_type:
            raise ValueError(f"task_codes.toml repeats task_type {tt!r}")
        if not code.isalpha() or not code.islower() or not (2 <= len(code) <= 10):
            raise ValueError(
                f"task_codes.toml row {tt!r}: code {code!r} is not [a-z]{{2,10}} (K11 §3)"
            )
        if code in codes:
            raise ValueError(
                f"task_codes.toml: code {code!r} is claimed by both {codes[code]!r} and {tt!r}"
            )
        if not label:
            raise ValueError(f"task_codes.toml row {tt!r} has no plain-language label")
        if "{subject}" not in title:
            raise ValueError(
                f"task_codes.toml row {tt!r}: the title template must name {{subject}}"
            )
        codes[code] = tt
        by_type[tt] = TaskCode(
            task_type=tt, code=code, label=label, title=title, catalog_pending=pending
        )
    return TaskCodes(version=version, by_type=by_type)


def load_gap_routing() -> dict[str, GapRoute]:
    """The predicate → lane routing table — validated, fail-closed.

    ``lane`` is closed (``research`` | ``campaign`` | ``metric``), ``grain`` is
    closed (``subject`` | ``jurisdiction``), and a ``route`` must name a §33.2
    catalog slug or one of the declared catalog-pending types.
    """
    from .catalog import catalog

    known = set(catalog().slugs()) | set(PENDING_CATALOG_TYPES)
    raw = load_table("gap_routing")
    version = str(raw.get("version") or "")
    if not version:
        raise ValueError("gap_routing.toml must declare a 'version'")
    routes: dict[str, GapRoute] = {}
    for i, entry in enumerate(raw.get("route") or ()):
        pred = str(entry.get("predicate") or "")
        lane = str(entry.get("lane") or "")
        route = entry.get("route")
        template = entry.get("template")
        grain = str(entry.get("grain") or "subject")
        if not pred:
            raise ValueError(f"gap_routing.toml row #{i} has no predicate")
        if pred in routes:
            raise ValueError(f"gap_routing.toml repeats predicate {pred!r}")
        if lane not in LANES:
            raise ValueError(f"gap_routing.toml row {pred!r}: unknown lane {lane!r}")
        if grain not in GRAINS:
            raise ValueError(f"gap_routing.toml row {pred!r}: unknown grain {grain!r}")
        if route is not None and str(route) not in known:
            raise ValueError(
                f"gap_routing.toml row {pred!r}: route {route!r} names neither a §33.2 "
                "catalog type nor a declared catalog-pending type"
            )
        if lane != "research" and (route is not None or template is not None):
            raise ValueError(
                f"gap_routing.toml row {pred!r}: only research lanes name a route/template"
            )
        routes[pred] = GapRoute(
            predicate=pred,
            lane=lane,
            route=None if route is None else str(route),
            template=None if template is None else str(template),
            grain=grain,
        )
    return routes
