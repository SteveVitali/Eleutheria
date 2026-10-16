# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `dot_511` connector — camera-location registries (P26.7/P26.9, SOURCES.7/.8).

State DOT and 511 traveler-info systems (P26.7), and municipal, transit-agency,
and non-US national/provincial operators (P26.9), publish their traffic-camera
inventory as authoritative operator-published location registries — the closest
thing to a ground-truth camera census and the physical-layer complement to the
crowdsourced OSM ``man_made=surveillance`` layer (§23.2). The registries ship in
two platforms: public ArcGIS REST feature layers
(``…/FeatureServer|MapServer/<n>/query``) and Socrata ``/resource/<id>.json``
datasets; keyed JSON APIs and unlicensed frontend payloads are enumerated,
never wired (``data/dot_511_targets.toml`` for state tiers,
``data/camera_registry_targets.toml`` for municipal/transit/international
tiers — one merged registry at read time).

This connector ingests **registry rows only**. Every row is an infrastructure
fact — a camera exists at an operator-published coordinate on a roadway — and
**no person data exists in these feeds by construction**. The Part VIII
boundary is structural: feed-content fields (snapshot/image/video/HLS URLs,
file paths, stream references) are matched by the vocabulary's media blocklist,
recorded by NAME on the entity's ``excluded_fields``, and never fetched,
emitted, or carried as values (P26.7 out-of-scope: "we ingest the camera
*registry*, never the feed content").

Rules this adapter upholds:

* **Coordinates are policy-checked at claim time** (§43.3, SIG-PUB-004): every
  emitted coordinate is parsed, range-checked, and passed through
  :func:`policy.sensitivity.apply_tier` at the target's sensitivity class
  (default C1 — publicly visible hardware on public right-of-way, operator-
  published). A malformed, missing, or out-of-range coordinate fails the record
  closed: it lands as a ``camera_record_rejected`` row (recorded, never silent),
  never as a claim. A capture that yields no parseable camera records at all is
  :class:`ContentDrift` — fail loud, never a silent empty run.
* **Schema-driven field aliases** (``data/dot_511_vocab.toml``, versioned): each
  state's layer names the same facts differently (``latitude`` vs ``Latitude``
  vs ``x``/``y`` vs geometry-only); the first present alias wins and the matched
  field name rides the claim for provenance. Unknown fields are ignored; media
  fields are blocklisted by name.
* **Per-source rights granularity**: each state is its own source row
  (``dot_511_<st>``) because terms differ per publisher; the loader gate and the
  live gate apply per state (SIG-INGEST-028). Targets whose rights are
  unresolved keep their source gated — the connector never reaches them.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from parsing.locator import Locator
from policy.sensitivity import SensitivityClass, apply_tier, geo_tier_for
from resolution.partner_identity import partner_ref_rows

from ._data import load_table
from .api_allowlist import api_allow_entry
from .field_denylist import assert_target_fields_clean
from .stages import (
    CaptureRef,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    register,
)

# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `dot_511` vocabulary (``data/dot_511_vocab.toml``)."""
    return load_table("dot_511_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


@cache
def target_table() -> dict[str, Any]:
    """The sourced enumeration registry — merged DOT + municipal tiers (P26.9).

    ``data/dot_511_targets.toml`` (P26.7, state DOT/511 registries) and
    ``data/camera_registry_targets.toml`` (P26.9, municipal/transit/non-US
    registries) are one logical registry kept in two files so each tier's
    enumeration history stays reviewable; every reader sees the union of
    ``targets`` and ``enumerated`` rows.
    """
    merged: dict[str, Any] = {"targets": [], "enumerated": []}
    for name in ("dot_511_targets", "camera_registry_targets"):
        table = load_table(name)
        merged["targets"].extend(table.get("targets", []))
        merged["enumerated"].extend(table.get("enumerated", []))
    return merged


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (SIG-INGEST-033)."""
    return frozenset(vocab()["predicate_allowlist"])


# --- the declared technology vocabulary (PKG-07 / P35.15a) -------------------


@cache
def _technology_vocab() -> dict[str, Any]:
    """The committed technology vocabulary (``ontology/vocab/technology.yaml``)."""
    from ontology.generate import load_vocab

    return load_vocab("technology")


@cache
def technology_slugs() -> frozenset[str]:
    """Every ACTIVE technology slug in the registry (retired slugs never emit)."""
    out: set[str] = set()
    for domain in _technology_vocab()["domains"]:
        for family in domain.get("families", ()):
            for tech in family.get("technologies", ()):
                if str(tech.get("status") or "active") != "retired":
                    out.add(str(tech["slug"]))
    return frozenset(out)


@cache
def _technology_domains() -> dict[str, str]:
    """Technology slug -> its domain slug (``surveillance-video``, …)."""
    out: dict[str, str] = {}
    for domain in _technology_vocab()["domains"]:
        for family in domain.get("families", ()):
            for tech in family.get("technologies", ()):
                if str(tech.get("status") or "active") != "retired":
                    out[str(tech["slug"])] = str(domain["slug"])
    return out


#: The record-kind values an emitted camera-registry entity row may carry
#: besides a technology slug itself: ``traffic_camera`` stays legal ONLY for a
#: target that literally declares it — the pre-P35.15a blanket typing is the
#: F-329/FM-04 defect; an ALPR/ATE/UAS target may never carry it.
_TRAFFIC_CAMERA_KIND = "traffic_camera"


def declared_record_kind(target: Mapping[str, Any]) -> str:
    """The entity row's ``record_kind`` — the subject subtype the target declares.

    Defaults to the target's ``technology`` slug; a target may pin
    ``record_kind = "traffic_camera"`` only when its technology is a
    fixed/PTZ camera (the ``surveillance-video`` domain) — an ALPR or drone
    layer wearing the traffic-camera kind is exactly the F-329 mistyping.
    """
    technology = str(target.get("technology") or "").strip()
    declared = str(target.get("record_kind") or "").strip()
    if not declared:
        return technology
    if declared == _TRAFFIC_CAMERA_KIND:
        if _technology_domains().get(technology) == "surveillance-video":
            return declared
        raise TechnologyNotDeclared(
            f"target {target.get('id')!r} declares record_kind='traffic_camera' with "
            f"technology={technology!r} — the legacy traffic-camera kind is legal only "
            "for a fixed/PTZ camera target (F-329)."
        )
    if declared == technology:
        return declared
    raise TechnologyNotDeclared(
        f"target {target.get('id')!r} declares record_kind={declared!r} — the "
        "subject subtype must be the declared technology slug or the explicit "
        f"{_TRAFFIC_CAMERA_KIND!r} escape."
    )


class TechnologyNotDeclared(Exception):
    """A registry defect: the target carries no usable technology declaration.

    Deliberately NOT a per-record rejection: a camera-registry target without a
    validated ``technology`` slug is a broken registry row, and the run must
    fail loudly rather than re-emit the legacy ``traffic_camera`` blanket
    (PKG-07 / P35.15a).
    """


def assert_target_technology(target: Mapping[str, Any]) -> str:
    """The target's validated technology slug, or :class:`TechnologyNotDeclared`."""
    slug = str(target.get("technology") or "").strip()
    if not slug:
        raise TechnologyNotDeclared(
            f"registry target {target.get('id')!r} carries no 'technology' slug — "
            "PKG-07 requires every camera-registry target to declare a member of "
            "ontology/vocab/technology.yaml (no silent traffic_camera default)."
        )
    if slug not in technology_slugs():
        raise TechnologyNotDeclared(
            f"registry target {target.get('id')!r} declares technology={slug!r}, "
            "which is not an active member of ontology/vocab/technology.yaml — "
            "register it via the ontology or re-point to a member slug."
        )
    return slug


def target_technology_violations() -> list[str]:
    """``sig-connectors validate`` rules for the per-target technology slug."""
    violations: list[str] = []
    for row in target_table().get("targets", []):
        tech = str(row.get("technology") or "").strip()
        label = f"target {row.get('id')!r} (source {row.get('source_id')!r})"
        if not tech:
            violations.append(f"{label}: missing 'technology' slug (PKG-07)")
            continue
        if tech not in technology_slugs():
            violations.append(
                f"{label}: technology={tech!r} is not an active member of "
                "ontology/vocab/technology.yaml"
            )
            continue
        try:
            declared_record_kind(row)
        except TechnologyNotDeclared as exc:
            violations.append(f"{label}: {exc}")
    return violations


def declared_technologies() -> dict[tuple[str, str], str]:
    """``(source_id, target_id)`` -> declared technology slug, for subject-keyed
    seams (the camera-site ER record builder) that must resolve a subject's own
    target declaration without importing the connector at build time."""
    out: dict[tuple[str, str], str] = {}
    for row in target_table().get("targets", []):
        tech = str(row.get("technology") or "").strip()
        if tech:
            out[(str(row.get("source_id") or ""), str(row.get("id") or ""))] = tech
    return out


# --- the declared geometry kind (P36.3 enum / P36.4 ACQ-08, SIG-GEO-003) ------


@cache
def geometry_kinds() -> frozenset[str]:
    """Every ``GeometryKind`` member of the ontology enum (P36.3, SIG-GEO-003).

    Read from the authored schema (``ontology/schema/common.yaml``) — the same
    source ``make gen`` consumes — so a registry row can never declare a shape
    the closed vocabulary does not know. Members: ``point`` | ``line`` |
    ``area``.
    """
    import yaml
    from ontology.generate import schema_path

    with (schema_path().parent / "common.yaml").open("rb") as fh:
        data = yaml.safe_load(fh)
    return frozenset(str(k) for k in data["enums"]["GeometryKind"]["permissible_values"])


class GeometryKindNotDeclared(Exception):
    """A registry defect: the target declares an unknown ``geometry_kind``.

    Deliberately NOT a per-record rejection: a camera-registry target whose
    declared shape is not a ``GeometryKind`` member is a broken registry row —
    the run fails loudly rather than silently point-flattening an area or
    line record (SIG-GEO-003).
    """


def assert_target_geometry_kind(target: Mapping[str, Any]) -> str:
    """The target's declared ``geometry_kind`` (default ``point``), validated."""
    kind = str(target.get("geometry_kind") or "point").strip()
    if kind not in geometry_kinds():
        raise GeometryKindNotDeclared(
            f"registry target {target.get('id')!r} declares "
            f"geometry_kind={kind!r}, which is not a GeometryKind member "
            f"({sorted(geometry_kinds())}) — register the member in "
            "ontology/schema/common.yaml or re-point to a member."
        )
    return kind


def target_geometry_violations() -> list[str]:
    """``sig-connectors validate`` rules for the per-target geometry kind."""
    violations: list[str] = []
    for row in target_table().get("targets", []):
        label = f"target {row.get('id')!r} (source {row.get('source_id')!r})"
        try:
            assert_target_geometry_kind(row)
        except GeometryKindNotDeclared as exc:
            violations.append(f"{label}: {exc}")
    return violations


# --- the declared status disposition (P36.5 / ACQ-09) -------------------------


#: The closed vocabulary for a target's ``status_disposition`` — how the
#: layer's published status column is allowed to affect lifecycle claims.
#: ``"removal"`` is the only member: the target is a removal ledger whose
#: rows bound the device's presence (removal → ``valid_to``, never a
#: deletion — I8 §5.2, I9a NEW-2).
_STATUS_DISPOSITIONS = frozenset({"removal"})


class StatusDispositionNotDeclared(Exception):
    """A registry defect: an unknown status disposition or a missing removal
    vocabulary.

    Deliberately NOT a per-record rejection: a target that mis-declares how
    its published status column maps to lifecycle claims is a broken registry
    row — the run must fail loudly rather than mint (or silently drop)
    ``valid_to`` bounds on unverified status semantics (P36.5; the S5 guard —
    a published status value is a permit-compliance fact, verbatim, until
    verified).
    """


def assert_target_status_disposition(target: Mapping[str, Any]) -> str | None:
    """The target's declared ``status_disposition`` (``None`` when undeclared).

    ``"removal"`` marks a removal-ledger target; with it the row MUST also
    carry a non-empty ``removal_status_values`` — the declared vocabulary of
    published status values that record a removal. A removal row's
    ``valid_to`` is stamped only on a member value: a status the registry
    does not declare never mints an end bound, and the verbatim published
    value still rides ``camera_status`` either way (S5 guard).
    """
    disposition = str(target.get("status_disposition") or "").strip()
    if not disposition:
        return None
    if disposition not in _STATUS_DISPOSITIONS:
        raise StatusDispositionNotDeclared(
            f"registry target {target.get('id')!r} declares "
            f"status_disposition={disposition!r}, which is not a member "
            f"({sorted(_STATUS_DISPOSITIONS)}) — register the member in "
            "dot_511.py or re-point the row."
        )
    if not _row_removal_status_values(target):
        raise StatusDispositionNotDeclared(
            f"registry target {target.get('id')!r} declares "
            "status_disposition='removal' but carries no "
            "'removal_status_values' — the declared removal-value vocabulary "
            "is required so a valid_to bound is never minted on an "
            "unverifiable status match."
        )
    return disposition


def _row_removal_status_values(target: Mapping[str, Any]) -> frozenset[str]:
    """The target's declared removal-value vocabulary, lower-cased for matching."""
    value = target.get("removal_status_values")
    if isinstance(value, str):
        return frozenset(v.strip().lower() for v in value.split(",") if v.strip())
    if isinstance(value, (list, tuple)):
        return frozenset(str(v).strip().lower() for v in value if str(v).strip())
    return frozenset()


# --- the declared coordinate precision (P36.5 / ACQ-09) -----------------------


#: The closed vocabulary for a target's ``coordinate_precision`` — the
#: publisher's own declared precision caveat. ``"approximate"`` is the only
#: member (Milford's layer description: "approximate locations, not GPS
#: data" — the caveat must travel with the record, §19.1/P4).
_COORD_PRECISIONS = frozenset({"approximate"})


class CoordinatePrecisionNotDeclared(Exception):
    """A registry defect: a ``coordinate_precision`` outside the closed set.

    Deliberately NOT a per-record rejection: an unknown precision label is a
    broken registry row — precision caveats must be declared vocabulary, never
    invented per record (P4 — uncertainty before false precision).
    """


def assert_target_coordinate_precision(target: Mapping[str, Any]) -> str | None:
    """The target's declared ``coordinate_precision`` (``None`` when undeclared)."""
    precision = str(target.get("coordinate_precision") or "").strip()
    if not precision:
        return None
    if precision not in _COORD_PRECISIONS:
        raise CoordinatePrecisionNotDeclared(
            f"registry target {target.get('id')!r} declares "
            f"coordinate_precision={precision!r}, which is not a member "
            f"({sorted(_COORD_PRECISIONS)}) — register the member in "
            "dot_511.py or re-point the row."
        )
    return precision


def target_status_violations() -> list[str]:
    """``sig-connectors validate`` rules for the declared status/coordinate
    semantics (P36.5): status dispositions, removal vocabularies, and the
    declared coordinate precision are validated fail-closed."""
    violations: list[str] = []
    for row in target_table().get("targets", []):
        label = f"target {row.get('id')!r} (source {row.get('source_id')!r})"
        try:
            assert_target_status_disposition(row)
        except StatusDispositionNotDeclared as exc:
            violations.append(f"{label}: {exc}")
        try:
            assert_target_coordinate_precision(row)
        except CoordinatePrecisionNotDeclared as exc:
            violations.append(f"{label}: {exc}")
    return violations


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`."""
    if predicate not in predicate_allowlist():
        raise PredicateNotAllowed(
            f"the dot_511 connector may write only {sorted(predicate_allowlist())} "
            f"(SIG-INGEST-033); {predicate!r} is outside the allowlist — feed content, "
            "person data, and deployment inferences are refused by construction."
        )
    return predicate


# --- the target registry ------------------------------------------------------

#: The ArcGIS REST query a registry target resolves to: all attribute fields,
#: point geometry in WGS84 (outSR=4326 so ``x`` is longitude, ``y`` latitude).
_ARCGIS_QUERY_PARAMS = {
    "where": "1=1",
    "outFields": "*",
    "outSR": "4326",
    "returnGeometry": "true",
    "f": "json",
}

#: The reviewed ArcGIS REST request budget (I8 NEW-3, api_allowlist.toml
#: `services*.arcgis.com` rows): applied to every ``arcgis_query`` target
#: unless the row or the host's allowlist entry names a stricter one.
_ARCGIS_REVIEWED_RPM = 10

#: ArcGIS page size: ArcGIS Online hosted layers cap a ``query`` response at the
#: service's ``maxRecordCount`` (1,000 on every hosted layer probed 2026-09-17 —
#: the capture carries ``exceededTransferLimit: true``). Registry rows therefore
#: expand into deterministic **page targets** (``resultOffset`` /
#: ``resultRecordCount`` over a stable ``orderByFields``) so a >1,000-camera
#: layer is captured whole — each page its own raw capture. If a layer grows
#: past its planned pages, the last page still returns
#: ``exceededTransferLimit`` and ``parse`` fails loud (ContentDrift) rather than
#: silently truncating the registry.
_ARCGIS_PAGE_SIZE = 1000

#: Socrata page size: the SoQL ``$limit`` cap is 50,000 but a 5,000-row page
#: keeps each capture modest and every enumerated municipal dataset is <2,000
#: rows. A page that returns exactly the page size on the LAST planned page is
#: treated like ArcGIS's ``exceededTransferLimit`` — the registry may have
#: outgrown its planned pages, so ``parse`` fails loud rather than silently
#: truncating.
_SOCRATA_PAGE_SIZE = 5000


def _row_out_fields(row: Mapping[str, Any]) -> list[str]:
    """The reviewed ``out_fields`` capture allowlist on a target row (P35.6 / P8-5).

    ``out_fields`` names the literal layer fields a new camera target may
    capture — it replaces the ``outFields=*`` wildcard so a raw capture holds
    only allowlisted attribute columns (Part VIII P8-5). The value may be a
    TOML array or a comma string; order is preserved.
    """
    value = row.get("out_fields")
    if isinstance(value, str):
        return [f.strip() for f in value.split(",") if f.strip()]
    if isinstance(value, (list, tuple)):
        return [str(f) for f in value]
    return []


def _arcgis_pages(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expand one ArcGIS layer row into its deterministic ``/query`` pages.

    ``page_size`` on the row is the reviewed per-layer page bound — pinned
    when the layer's own ``maxRecordCount`` is below the 1,000 default
    (P26.16: camreg_portland_or serves 200 rows/page, so a 1,000-row request
    returns ``exceededTransferLimit`` on every page).

    ``out_fields`` (P35.6 / P8-5) replaces ``outFields=*`` with the reviewed
    allowlist so the raw capture holds only those fields; the object-id field
    is always appended (paging breaks without it). A denied field inside the
    allowlist is a registration refusal — the F-330 denylist check runs before
    this expansion, so a row that reaches here is clean.
    """
    layer_url = str(row["layer_url"]).rstrip("/")
    observed = int(row.get("observed_count") or 0)
    oid_field = str(row.get("object_id_field") or "OBJECTID")
    page_size = min(_ARCGIS_PAGE_SIZE, max(1, int(row.get("page_size") or _ARCGIS_PAGE_SIZE)))
    pages = max(1, -(-observed // page_size))
    params_base = dict(_ARCGIS_QUERY_PARAMS)
    # P36.4 (ACQ-08): a reviewed server-side attribute filter narrows the
    # capture at the service — Vermont's ITS DeviceList serves every ITS
    # device class, so ``where = "DeviceType='CCTV'"`` fetches only the
    # camera rows and the raw capture never carries the non-camera devices.
    where = str(row.get("where") or "").strip()
    if where:
        params_base["where"] = where
    out_fields = _row_out_fields(row)
    if out_fields:
        names = list(out_fields)
        if oid_field not in names:
            names.append(oid_field)
        params_base["outFields"] = ",".join(names)
    out: list[dict[str, Any]] = []
    for page in range(pages):
        params = {
            **params_base,
            "orderByFields": oid_field,
            "resultRecordCount": page_size,
            "resultOffset": page * page_size,
        }
        out.append(
            {"url": f"{layer_url}/query?{urlencode(params)}", "page": page, "page_count": pages}
        )
    return out


def _socrata_pages(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expand one Socrata dataset row into deterministic ``$limit/$offset`` pages.

    ``$select=*,:id`` keeps the publisher's columns AND the Socrata ``:id``
    row-id (the fallback registry key when a dataset has no id column);
    ``$order=:id`` makes page offsets stable within a run.
    """
    resource_url = str(row["layer_url"]).rstrip("/")
    observed = int(row.get("observed_count") or 0)
    pages = max(1, -(-observed // _SOCRATA_PAGE_SIZE))
    out_fields = _row_out_fields(row)
    select = ",".join([*out_fields, ":id"]) if out_fields else "*,:id"
    out: list[dict[str, Any]] = []
    for page in range(pages):
        params = {
            "$select": select,
            "$order": ":id",
            "$limit": _SOCRATA_PAGE_SIZE,
            "$offset": page * _SOCRATA_PAGE_SIZE,
        }
        out.append(
            {"url": f"{resource_url}?{urlencode(params)}", "page": page, "page_count": pages}
        )
    return out


def registry_targets(source_id: str) -> list[dict[str, Any]]:
    """The live fetch targets for one camera-registry source (identifiers, not content).

    Reads the verified ``[[targets]]`` rows of the merged registry
    (``dot_511_targets.toml`` + ``camera_registry_targets.toml``) — the same
    registry that preserves the enumerated non-target outcomes — and expands
    each row into the deterministic platform URLs. A source whose rows are all
    ``[[enumerated]]`` (keyed, refused, unreachable) has no live targets; the
    live runner refuses it rather than inventing one.

    Paging: an ``arcgis_query`` row yields ``ceil(observed_count / 1000)``
    page targets ordered by the layer's object-id field; a ``socrata_rows``
    row yields ``ceil(observed_count / 5000)`` pages ordered by ``:id`` (min 1
    either way). All pages of one layer share the registry row's ``id`` — a
    camera's subject key is page-independent.
    """
    return expand_registry_rows(
        (
            row
            for row in target_table().get("targets", [])
            if str(row.get("source_id")) == source_id
        ),
        source_id=source_id,
    )


def expand_registry_rows(
    rows: Iterable[Mapping[str, Any]], *, source_id: str = ""
) -> list[dict[str, Any]]:
    """Expand registry ``[[targets]]`` rows into fetch targets (P35.6 seam).

    The expansion logic of :func:`registry_targets`, factored so the
    F-330 denylist, the ``out_fields`` allowlist and the api_allowlist rate
    budget can be exercised on arbitrary rows (the ACQ-01 generator and its
    tests) without touching the committed registry files.
    """
    expanders = {"arcgis_query": _arcgis_pages, "socrata_rows": _socrata_pages}
    out: list[dict[str, Any]] = []
    for row in rows:
        if source_id and str(row.get("source_id")) != source_id:
            continue
        kind = str(row.get("kind") or "arcgis_query")
        # F-330 (P35.6): a target whose declared layer schema or out_fields
        # allowlist carries a Part VIII denied field is refused here too — the
        # registration-time denylist (validate/generator) is the primary gate,
        # but a dirty row must never reach the fetch path.
        assert_target_fields_clean(row)
        expand = expanders.get(kind)
        if expand is None:
            raise ValueError(
                f"registry target {row.get('id')!r} declares unknown kind {kind!r} "
                f"(known: {sorted(expanders)}) — the connector never fetches an "
                "unrecognised platform."
            )
        # P35.6 (I8 NEW-3): apply the host's reviewed api_allowlist request
        # budget — the 10/min ArcGIS services*.arcgis.com rows — as the
        # per-target rate limit; an explicit ``rate_limit_per_min`` on the row
        # (a stricter reviewed budget) always wins.
        rpm = row.get("rate_limit_per_min")
        if rpm is None:
            entry = api_allow_entry(str(row["layer_url"]))
            rpm = entry.rate_limit_per_min if entry is not None else None
        if rpm is None and kind == "arcgis_query":
            # An ArcGIS layer on a host the allowlist does not name still runs
            # at the reviewed 10/min ArcGIS budget (I8 NEW-3), never unbounded.
            rpm = _ARCGIS_REVIEWED_RPM
        # P35.15a (PKG-07): a target without a declared technology slug never
        # expands — the emit path must never mint the legacy `traffic_camera`
        # blanket typing (F-329).
        technology = assert_target_technology(row)
        # P36.4 (ACQ-08, SIG-GEO-003): the declared geometry kind is validated
        # at expansion — a row naming a shape the ontology does not know is a
        # broken registry row, never a silently point-flattened emit.
        geometry_kind = assert_target_geometry_kind(row)
        # P36.5 (ACQ-09): the declared status disposition + coordinate
        # precision are validated at expansion — a removal target without its
        # declared removal-value vocabulary or a non-member precision is a
        # broken registry row, never a silently un-bounded (or falsely
        # bounded) emit.
        status_disposition = assert_target_status_disposition(row)
        coordinate_precision = assert_target_coordinate_precision(row)
        where = str(row.get("where") or "").strip()
        for page in expand(row):
            target = {
                "id": str(row["id"]),
                "url": page["url"],
                "kind": kind,
                "state": str(row["state"]),
                "agency": str(row["agency"]),
                "jurisdiction_scheme": str(row.get("jurisdiction_scheme") or "us.state_abbr"),
                "layer_url": str(row["layer_url"]).rstrip("/"),
                "page": page["page"],
                "page_count": page["page_count"],
                "license_spdx": str(row.get("license_spdx", "")),
                "sensitivity_class": str(
                    row.get("sensitivity_class") or vocab()["default_sensitivity_class"]
                ),
                "enum_source": str(row.get("enum_source", "")),
                "technology": technology,
                "record_kind": declared_record_kind(row),
                "geometry_kind": geometry_kind,
            }
            if status_disposition:
                target["status_disposition"] = status_disposition
                target["removal_status_values"] = sorted(_row_removal_status_values(row))
            if coordinate_precision:
                target["coordinate_precision"] = coordinate_precision
            if where:
                target["where"] = where
            if rpm is not None:
                target["rate_limit_per_min"] = int(rpm)
            out_fields = _row_out_fields(row)
            if out_fields:
                target["out_fields"] = out_fields
            out.append(target)
    return out


def registry_row(source_id: str, target_id: str = "") -> dict[str, Any]:
    """The registry metadata row for a ``(source_id, target_id)`` pair.

    With ``target_id`` empty and the source owning exactly one target row, that
    row is returned — the fixture-replay path supplies a synthetic target whose
    metadata still resolves from the registry.
    """
    rows = [
        dict(r) for r in target_table().get("targets", []) if str(r.get("source_id")) == source_id
    ]
    if target_id:
        for row in rows:
            if str(row.get("id")) == target_id:
                return row
        return {}
    if len(rows) == 1:
        return rows[0]
    return {}


def enumerated_outcomes() -> list[dict[str, Any]]:
    """The recorded non-target discovery outcomes (keyed/refused/unreachable)."""
    return [dict(r) for r in target_table().get("enumerated", [])]


# --- media-field blocklist ----------------------------------------------------


@cache
def _media_names() -> frozenset[str]:
    return frozenset(str(n).lower() for n in vocab()["media_field_names"])


@cache
def _media_patterns() -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(p) for p in (str(x).lower() for x in vocab()["media_field_patterns"]))


def is_media_field(field_name: str) -> bool:
    """Whether a field carries/points at feed CONTENT — never ingested (Part VIII).

    A field is media-bearing when its name is in the explicit blocklist or
    matches a blocklist pattern (``url``, ``image``, ``video``, ``snapshot``,
    ``hls``, ``stream``, ``thumb``, ``fileloc``). Only the field NAME is ever
    recorded; the value is dropped at extraction.
    """
    name = field_name.lower()
    if name in _media_names():
        return True
    return any(p.search(name) for p in _media_patterns())


def partition_fields(attributes: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Split attributes into (registry fields, excluded media-field names)."""
    fields: dict[str, Any] = {}
    excluded: list[str] = []
    for key, value in attributes.items():
        if is_media_field(key):
            excluded.append(key)
        else:
            fields[key] = value
    return fields, sorted(excluded)


# --- coordinate validation (§43.3 / SIG-PUB-004 — fail closed) ----------------


class CoordinateRejected(ValueError):
    """A camera coordinate failed the policy check — the record fails closed.

    Carries the machine-stable ``reason`` recorded on the rejection row:
    ``missing`` (no coordinate anywhere), ``malformed`` (unparseable),
    ``out_of_range`` (lat∉[-90,90] / lon∉[-180,180]), ``tier_forbids_geometry``
    (the sensitivity tier publishes no geometry).
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail
        super().__init__(f"camera coordinate rejected: {reason} ({detail})" if detail else reason)


def _first_field(fields: Mapping[str, Any], aliases: Iterable[str]) -> tuple[str, Any] | None:
    """The first present, non-empty aliased field, as ``(name, value)``.

    Non-scalar values are skipped (P26.9): a GeoJSON dict under a text-aliased
    name — Socrata's ``location`` point object — is geometry, never a name or
    id string, and stays available to :func:`socrata_point_geometry`.
    """
    for name in aliases:
        if name in fields and fields[name] not in (None, ""):
            value = fields[name]
            if isinstance(value, (Mapping, list, tuple)):
                continue
            return (name, value)
    return None


def socrata_point_geometry(fields: Mapping[str, Any]) -> dict[str, Any] | None:
    """The ``{"x": lon, "y": lat}`` geometry from a Socrata point-object field (P26.9).

    Socrata rows carry GeoJSON-ish point columns (``the_geom``, ``location``,
    ``geolocation``, ``geometry_point``, ``geo_location`` — the vocab's
    ``point_fields``) instead of an ArcGIS ``geometry`` member. The first
    dict-valued candidate with either GeoJSON ``{"type": "Point",
    "coordinates": [lon, lat]}`` shape or ``latitude``/``longitude`` keys wins;
    coordinates are returned in the same ``x``=longitude / ``y``=latitude shape
    the ArcGIS geometry path produces so downstream validation is identical.
    """
    for name in vocab()["point_fields"]:
        value = fields.get(name)
        if not isinstance(value, Mapping):
            continue
        coords = value.get("coordinates")
        if (
            str(value.get("type")).lower() == "point"
            and isinstance(coords, (list, tuple))
            and len(coords) >= 2
        ):
            return {"x": coords[0], "y": coords[1]}
        if value.get("latitude") is not None and value.get("longitude") is not None:
            return {"x": value["longitude"], "y": value["latitude"]}
    return None


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _matching_fields(fields: Mapping[str, Any], aliases: Iterable[str]) -> list[tuple[str, Any]]:
    """Every present, non-empty, scalar aliased field, in alias order.

    The plural counterpart of :func:`_first_field` — coordinate extraction
    walks ALL matching pairs so a present-but-unusable pair (DMS text,
    projected values, publisher-swapped columns — observed live P26.16)
    falls through to the next pair instead of hard-rejecting a record whose
    operator-published point geometry is valid.
    """
    out: list[tuple[str, Any]] = []
    for name in aliases:
        if name in fields and fields[name] not in (None, ""):
            value = fields[name]
            if isinstance(value, (Mapping, list, tuple)):
                continue
            out.append((name, value))
    return out


def extract_coordinate(
    fields: Mapping[str, Any], geometry: Mapping[str, Any] | None
) -> tuple[float, float, str]:
    """The operator-published ``(lat, lon, coord_source)`` for one feature.

    Explicit latitude/longitude attribute fields are preferred — a published
    attribute is stronger provenance than derived geometry — tried in alias
    order until a pair parses numeric and in-range. The ArcGIS point geometry
    (``outSR=4326``: ``x``=longitude, ``y``=latitude) is the fallback when no
    attribute pair yields a usable coordinate — geometry-only layers (WSDOT,
    KC/WSDOT, UDOT) and layers whose aliased columns are unusable (P26.16:
    DMS-text ``LATITUDE``/``LONGITUDE``, projected ``x``/``y`` attributes,
    publisher-swapped columns) still carry their real point in geometry.
    A record with no usable coordinate anywhere raises
    :class:`CoordinateRejected` — fail closed.
    """
    lat_pairs = _matching_fields(fields, vocab()["lat_fields"])
    lon_pairs = _matching_fields(fields, vocab()["lon_fields"])
    saw_numeric = False
    for lat_pair in lat_pairs:
        for lon_pair in lon_pairs:
            lat = _as_float(lat_pair[1])
            lon = _as_float(lon_pair[1])
            if lat is None or lon is None:
                continue
            saw_numeric = True
            if -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0:
                return (lat, lon, f"fields:{lat_pair[0]}/{lon_pair[0]}")
    if geometry is not None and geometry.get("x") is not None and geometry.get("y") is not None:
        lat = _as_float(geometry.get("y"))
        lon = _as_float(geometry.get("x"))
        if lat is None or lon is None:
            raise CoordinateRejected("malformed", "geometry: values are not numeric")
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise CoordinateRejected(
                "out_of_range", f"geometry: lat={lat} lon={lon} outside valid ranges"
            )
        return (lat, lon, "geometry")
    if lat_pairs and lon_pairs:
        raise CoordinateRejected(
            "out_of_range" if saw_numeric else "malformed",
            "every aliased lat/lon field pair failed validation and no point geometry is present",
        )
    raise CoordinateRejected("missing", "no lat/lon field pair and no point geometry")


def publishable_coordinate(
    lat: float, lon: float, sensitivity_class: str
) -> tuple[float, float, int]:
    """The coordinate a claim may carry after the §43.3/§19.4 tier transform.

    ``geo_tier_for`` resolves the class's publication tier and
    :func:`policy.sensitivity.apply_tier` applies it (C1/C2-operator-published →
    tier 0 exact). A tier-3 class returns ``None`` — jurisdiction only — and the
    record fails closed with ``tier_forbids_geometry``. The DOT registries are
    operator-published hardware on public right-of-way, so the reviewed default
    is C1; a target may pin a stricter class in ``dot_511_targets.toml``.
    """
    try:
        cls = SensitivityClass(sensitivity_class)
    except ValueError as exc:
        raise CoordinateRejected(
            "invalid_sensitivity_class",
            f"target pins unknown sensitivity class {sensitivity_class!r}",
        ) from exc
    tier = geo_tier_for(cls)
    published = apply_tier(lat, lon, tier)
    if published is None:
        raise CoordinateRejected(
            "tier_forbids_geometry",
            f"sensitivity class {cls.value} publishes no geometry (tier {tier})",
        )
    return (published[0], published[1], tier)


# --- area geometry (P36.4 / SIG-GEO-003 — fail closed) -------------------------


def _checked_ring(ring: Any, index: int) -> list[tuple[float, float]]:
    """One ArcGIS polygon ring as validated ``(lon, lat)`` pairs.

    A ring must be a list of ≥4 positions, each a numeric in-range ``[x, y]``
    (outSR=4326: x = longitude, y = latitude), closed first==last. Any other
    shape is :class:`CoordinateRejected` — a malformed area record is recorded
    on a rejection row, never emitted.
    """
    if not isinstance(ring, (list, tuple)) or len(ring) < 4:
        raise CoordinateRejected(
            "malformed", f"rings[{index}] is not a closed ring of at least 4 positions"
        )
    points: list[tuple[float, float]] = []
    for j, pos in enumerate(ring):
        if not isinstance(pos, (list, tuple)) or len(pos) < 2:
            raise CoordinateRejected("malformed", f"rings[{index}][{j}] is not an [x, y] position")
        x = _as_float(pos[0])
        y = _as_float(pos[1])
        if x is None or y is None:
            raise CoordinateRejected("malformed", f"rings[{index}][{j}]: values are not numeric")
        if not (-180.0 <= x <= 180.0 and -90.0 <= y <= 90.0):
            raise CoordinateRejected(
                "out_of_range", f"rings[{index}][{j}]: x={x} y={y} outside valid ranges"
            )
        points.append((x, y))
    if points[0] != points[-1]:
        raise CoordinateRejected(
            "malformed", f"rings[{index}] is not closed (first != last position)"
        )
    return points


def _ring_signed_area(ring: list[tuple[float, float]]) -> float:
    """The shoelace signed area of a closed ring (Y-up: >0 counter-clockwise)."""
    area = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        area += x1 * y2 - x2 * y1
    return area / 2.0


def _ring_centroid(ring: list[tuple[float, float]]) -> tuple[float, float]:
    """The shoelace centroid ``(x, y)`` of a closed ring.

    A degenerate (zero-area) ring falls back to the vertex mean — still
    deterministic, and the ring would already have failed closed when it
    produced a malformed polygon.
    """
    a = 0.0
    cx = 0.0
    cy = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i]
        x2, y2 = ring[i + 1]
        cross = x1 * y2 - x2 * y1
        a += cross
        cx += (x1 + x2) * cross
        cy += (y1 + y2) * cross
    a *= 0.5
    if abs(a) < 1e-15:
        xs = [p[0] for p in ring[:-1]]
        ys = [p[1] for p in ring[:-1]]
        return (sum(xs) / len(xs), sum(ys) / len(ys))
    return (cx / (6 * a), cy / (6 * a))


def _fmt_wkt(value: float) -> str:
    """Deterministic WKT ordinate formatting (shortest round-trip repr)."""
    return repr(float(value))


def _ring_wkt(ring: list[tuple[float, float]]) -> str:
    return "(" + ", ".join(f"{_fmt_wkt(x)} {_fmt_wkt(y)}" for x, y in ring) + ")"


def area_geometry(geometry: Any) -> tuple[str, float, float, int]:
    """The ``(wkt, centroid_lat, centroid_lon, ring_count)`` of an ArcGIS polygon.

    For a ``geometry_kind = "area"`` target the feature's ``geometry.rings``
    carries the published polygon (outSR=4326). ArcGIS ring orientation
    distinguishes parts: exterior rings wind clockwise (negative signed area),
    interior rings (holes) counter-clockwise and group under the most recent
    exterior. One exterior yields ``POLYGON``; several yield ``MULTIPOLYGON``.
    The centroid is DERIVED — the shoelace centroid of the largest-area
    exterior ring, recorded on the entity row for positioning; the record
    never mints a device-point coordinate claim.

    Fail closed (a malformed/unsupported shape is recorded on a rejection row,
    never emitted): no geometry → ``missing``; a point ``x``/``y`` geometry on
    an area target → ``unsupported_geometry`` (schema drift); non-numeric,
    out-of-range, unclosed or degenerate rings → ``malformed``/
    ``out_of_range``.
    """
    if not isinstance(geometry, Mapping):
        raise CoordinateRejected("missing", "area target feature carries no geometry")
    if "x" in geometry or "y" in geometry:
        raise CoordinateRejected(
            "unsupported_geometry",
            "an area-target feature carried point geometry (x/y) — schema drift",
        )
    rings = geometry.get("rings")
    if not isinstance(rings, list) or not rings:
        raise CoordinateRejected("missing", "area target feature carries no 'rings'")
    checked = [_checked_ring(ring, i) for i, ring in enumerate(rings)]
    polygons: list[list[Any]] = []  # each [exterior_ring, [hole_ring, …]]
    for ring in checked:
        if _ring_signed_area(ring) < 0:
            polygons.append([ring, []])
        else:
            if not polygons:
                raise CoordinateRejected(
                    "malformed", "first ring is not an exterior (clockwise) ring"
                )
            polygons[-1][1].append(ring)
    if not polygons:
        raise CoordinateRejected("malformed", "no exterior (clockwise) ring present")
    if len(polygons) == 1:
        exterior, holes = polygons[0]
        wkt = "POLYGON(" + ", ".join([_ring_wkt(exterior), *map(_ring_wkt, holes)]) + ")"
    else:
        members = []
        for exterior, holes in polygons:
            members.append("(" + ", ".join([_ring_wkt(exterior), *map(_ring_wkt, holes)]) + ")")
        wkt = "MULTIPOLYGON(" + ", ".join(members) + ")"
    largest = max(polygons, key=lambda p: abs(_ring_signed_area(p[0])))
    cx, cy = _ring_centroid(largest[0])
    return (wkt, cy, cx, len(checked))


# --- the camera-registry entry -------------------------------------------------


@dataclass(frozen=True)
class CameraRegistryEntry:
    """One registry-keyed traffic-camera row (P26.7).

    ``camera_ref`` is required — it is the subject key the claim spine appends
    under (per-source + per-layer scoped, so the same ArcGIS OBJECTID in two
    layers never collides). ``latitude``/``longitude`` are the **published**
    (post-tier) coordinates; ``coordinate_source`` records which field names or
    geometry produced them.
    """

    camera_ref: str
    source_id: str
    target_id: str
    state: str
    #: The registry's PUBLISHER label (the target row's ``agency`` — who
    #: publishes this camera layer). Provenance only: it becomes a
    #: ``camera_registry_publisher`` claim, never a ``camera_operator`` claim —
    #: a publisher is not an evidenced camera operator (P32.3 / SIG-TRUST-003,
    #: ADR-122). The OSM contributor label is the canonical case.
    agency: str
    #: The published (post-tier) device-point coordinates. ``None`` on a
    #: non-point record (P36.4): an area record carries ``geometry_wkt`` +
    #: a derived centroid instead, and never mints ``camera_latitude`` /
    #: ``camera_longitude`` claims (SIG-GEO-003).
    latitude: float | None
    longitude: float | None
    coordinate_source: str
    geo_tier: int
    sensitivity_class: str
    license_spdx: str
    #: P35.15a / PKG-07 (F-329, F-523): the registry target's declared
    #: ``technology`` slug — an active member of ontology/vocab/technology.yaml.
    #: Emitted as the ``technology`` claim AND as the subject record's subtype
    #: (``record_kind``); never inferred from a name substring.
    technology: str
    #: The entity row's ``record_kind`` — the declared subject subtype, i.e. the
    #: technology slug by default; ``"traffic_camera"`` only when the target
    #: literally declares it (see :func:`declared_record_kind`).
    record_kind: str
    #: An authoritative operator label — set only when the registry evidence
    #: itself names the camera operator (the target's ``operator`` field or a
    #: feature ``operator_fields`` value). Only this mints ``camera_operator``.
    operator: str | None = None
    name: str | None = None
    roadway: str | None = None
    county: str | None = None
    status: str | None = None
    direction: str | None = None
    excluded_fields: tuple[str, ...] = ()
    #: The candidate-identifier scheme the ``camera_jurisdiction`` claim carries
    #: (P26.9): ``us.state_abbr`` for US admin-1 codes, ``iso.3166_2`` for
    #: ISO 3166-2 subdivision codes (CA-ON, AU-ACT, GB-ENG), ``iso.3166_1_alpha2``
    #: for country-level publishers (NZ, HK).
    jurisdiction_scheme: str = "us.state_abbr"
    #: The evidence extraction method stamped per platform (P26.9):
    #: ``arcgis_feature_json`` or ``socrata_rows_json``.
    extraction_method: str = "arcgis_feature_json"
    #: P36.4 (ACQ-08, SIG-GEO-003): the record's declared ``GeometryKind``
    #: member — ``point`` for every existing device-point target; ``area``
    #: for a programme-area record (Seattle SPD CCTV pilot areas), whose
    #: publisher's geometry is a polygon, never a device point.
    geometry_kind: str = "point"
    #: For a non-point record: the publisher's geometry serialised as WKT
    #: (``POLYGON``/``MULTIPOLYGON``, lon-lat axis order, outSR=4326 source).
    geometry_wkt: str | None = None
    #: For an area record: the DERIVED label position — the shoelace centroid
    #: of the largest exterior ring, post-tier. Recorded on the entity row as
    #: ``centroid_*`` fields; never a published device coordinate.
    centroid_latitude: float | None = None
    centroid_longitude: float | None = None
    #: The number of rings the published polygon carried (transparency for
    #: multi-ring / hole handling).
    ring_count: int = 0
    #: P36.5 (ACQ-09, P4): the target's declared coordinate-precision caveat —
    #: ``None`` or a ``_COORD_PRECISIONS`` member (``"approximate"`` for
    #: Milford's published "approximate locations, not GPS data" rows).
    #: Stamped on the entity + the coordinate claims so the publisher's own
    #: caveat travels with the record.
    coordinate_precision: str | None = None
    #: P36.5 (ACQ-09, I9a NEW-2): a removal-ledger row's end bound — the
    #: published removal date under ``valid_to_kind="exact"``, or
    #: ``(None, "unknown")`` when the publisher flags the device removed
    #: without a date. Stamped on the entity + every claim row a removal row
    #: emits; left ``None`` on every other record (absence is the spine's
    #: "not asserted" — the device is never silently bounded, and the append
    #: never deletes the paired inventory rows).
    valid_to: str | None = None
    valid_to_kind: str | None = None

    def __post_init__(self) -> None:
        if not str(self.camera_ref).strip():
            raise ValueError("a CameraRegistryEntry requires a camera_ref (the registry key)")
        # PKG-07: an entry never emits without its validated declared
        # technology — the slug membership is asserted at target expansion and
        # re-asserted here so a hand-built entry cannot smuggle a non-member
        # value into the claim surface.
        assert_target_technology({"id": self.target_id, "technology": self.technology})
        if not str(self.record_kind).strip():
            raise ValueError("a CameraRegistryEntry requires a record_kind (the subtype)")
        # SIG-GEO-003 (P36.4): the declared shape is a GeometryKind member and
        # the record carries the geometry its kind requires — a point record
        # must have a published coordinate; an area record must have its WKT
        # and a derived centroid. A hand-built entry that violates the shape
        # contract fails closed here, never a half-formed claim surface.
        if self.geometry_kind not in geometry_kinds():
            raise GeometryKindNotDeclared(
                f"entry for {self.target_id!r} declares geometry_kind={self.geometry_kind!r}"
            )
        if self.geometry_kind == "point" and (self.latitude is None or self.longitude is None):
            raise ValueError("a point CameraRegistryEntry requires published coordinates")
        if self.geometry_kind != "point" and (
            self.geometry_wkt is None
            or self.centroid_latitude is None
            or self.centroid_longitude is None
        ):
            raise ValueError(
                "a non-point CameraRegistryEntry requires geometry_wkt + a derived centroid"
            )
        # P36.5: the declared coordinate-precision caveat is a member of the
        # closed set — a hand-built entry cannot smuggle an invented label.
        if self.coordinate_precision is not None:
            assert_target_coordinate_precision(
                {"id": self.target_id, "coordinate_precision": self.coordinate_precision}
            )
        # P36.5 (I9a NEW-2): a removal bound asserts a kind only the emit path
        # mints — ``"exact"`` (a published date) or ``"unknown"`` (a removal
        # flag with no date). Any other temporal vocabulary is a registry
        # defect, never a silently re-labeled bound; an ``exact`` bound without
        # its date is a contradiction the row must not assert.
        if self.valid_to_kind is not None:
            if self.valid_to_kind not in ("exact", "unknown"):
                raise ValueError(
                    f"valid_to_kind={self.valid_to_kind!r} is not an emitted member "
                    "('exact'/'unknown')"
                )
            if self.valid_to_kind == "exact" and not self.valid_to:
                raise ValueError("an 'exact' valid_to bound requires the published date")

    @property
    def subject_id(self) -> str:
        # The ``traffic_camera:`` scheme is the subject's IDENTITY anchor under
        # ``sig.connector.subject`` — ~232k existing subjects minted under it
        # stay the identity root for their (source, target, ref). P35.15a does
        # NOT re-scheme it: minting ``<technology>:…`` keys would fork every
        # existing subject into a second current row the next ingest (the
        # same-source constraint means the twin could never merge — append-only
        # makes the fork permanent). The declared-subtype correction rides the
        # ``technology`` claim + the entity row's ``record_kind``; P35.15b's
        # backfill writes technology claims onto these existing subjects.
        return f"traffic_camera:{self.source_id}:{self.target_id}:{self.camera_ref}"

    def evidence(self, source_url: str, retrieved_date: str, feature_index: int) -> dict[str, Any]:
        """The evidence dict every claim carries — capture URL + row locator.

        ``retrieved_date`` is deliberately NOT in the claim dict: it is the
        capture's per-run retrieval timestamp, and a volatile value inside the
        claim makes ``content_digest`` churn — a re-run over an unchanged
        registry would mint duplicate claim rows (the same defect class P26.6
        fixed by removing ``capture_digest`` from agenda claim evidence). The
        retrieval timestamp is already durable on ``evidence_capture.
        retrieved_at`` and the run row's fetch record. The parameter stays in
        the signature because the raw ``camera_feature`` record keeps the
        timestamp for provenance — it just never reaches claim identity.
        """
        _ = retrieved_date
        return {
            "source_url": source_url,
            "extraction_method": self.extraction_method,
            "locator": Locator.row(feature_index).to_row(),
        }

    def _claim(
        self,
        predicate: str,
        value: Any,
        raw_value: str,
        evidence: Mapping[str, Any],
        *,
        candidate: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "record_kind": "claim",
            "subject_id": self.subject_id,
            "predicate_id": assert_predicate_allowed(predicate),
            "raw_value": raw_value,
            "value": value,
            "evidence_genre": "camera_registry",
            "evidence": dict(evidence),
        }
        if candidate is not None:
            row["candidate_identifier"] = dict(candidate)
        return _stamp(row, source_id=self.source_id, license_spdx=self.license_spdx)

    def claim_rows(
        self, source_url: str, retrieved_date: str, feature_index: int
    ) -> list[dict[str, Any]]:
        """The append-only claim rows for this entry, confined to the allowlist (P2).

        One camera-registry entity row (``predicate_id="traffic_camera"``, the
        registry-record assertion) whose ``record_kind`` is the subject's
        declared subtype — the target's technology slug, or ``traffic_camera``
        only when the target literally declares it — carrying the whole
        predicate surface plus the excluded-field NAMES (never their values);
        plus one claim row per set predicate, including the ``technology``
        claim (P35.15a / PKG-07). The coordinate claims carry the published
        (tier-applied) coordinate and the sensitivity facts that produced it;
        the state is a ``us.state_abbr`` jurisdiction candidate and the camera
        ref a ``dot511.camera_ref`` candidate identifier — never resolutions
        (SIG-INGEST-034).
        """
        ev = self.evidence(source_url, retrieved_date, feature_index)
        entity: dict[str, Any] = {
            # PKG-07 (F-329/F-523): the record kind is the subject's
            # declared subtype — an ALPR target's rows read ``alpr-*``,
            # ``traffic_camera`` survives only on a target that
            # literally declares it.
            "record_kind": self.record_kind,
            "subject_id": self.subject_id,
            "predicate_id": assert_predicate_allowed("traffic_camera"),
            "external_id": self.camera_ref,
            "raw_value": self.camera_ref,
            "state": self.state,
            "agency": self.agency,
            "target_id": self.target_id,
            "technology": self.technology,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "coordinate_source": self.coordinate_source,
            "geo_tier": self.geo_tier,
            "sensitivity_class": self.sensitivity_class,
            "excluded_fields": list(self.excluded_fields),
            "evidence_genre": "camera_registry",
            "evidence": ev,
        }
        if self.geometry_kind != "point":
            # SIG-GEO-003 (P36.4): the declared shape, the published polygon
            # and the derived centroid ride the entity row — a point record
            # stays byte-identical to its pre-P36.4 emit (the default shape
            # needs no restatement); ``latitude``/``longitude`` stay ``None``
            # because a programme area is not a device point.
            entity["geometry_kind"] = self.geometry_kind
            entity["geometry_wkt"] = self.geometry_wkt
            entity["centroid_latitude"] = self.centroid_latitude
            entity["centroid_longitude"] = self.centroid_longitude
            entity["ring_count"] = self.ring_count
        if self.coordinate_precision:
            # P36.5 (P4): the publisher's declared precision caveat rides the
            # entity row so it travels with the record.
            entity["coordinate_precision"] = self.coordinate_precision
        rows: list[dict[str, Any]] = [
            _stamp(
                entity,
                source_id=self.source_id,
                license_spdx=self.license_spdx,
            )
        ]
        rows.append(
            self._claim(
                "camera_external_ref",
                self.camera_ref,
                self.camera_ref,
                ev,
                candidate={"scheme": "dot511.camera_ref", "value": self.camera_ref},
            )
        )
        rows.append(self._claim("external_id", self.camera_ref, self.camera_ref, ev))
        # PKG-07 (P35.15a): the declared technology rides the claim surface —
        # value and raw are the registry slug verbatim (the slug IS the raw
        # declaration; the target row is its evidence via source_url+locator).
        rows.append(self._claim("technology", self.technology, self.technology, ev))
        rows.append(
            self._claim(
                "camera_jurisdiction",
                self.state,
                self.state,
                ev,
                candidate={"scheme": self.jurisdiction_scheme, "value": self.state},
            )
        )
        # P32.3 (SIG-TRUST-003/004): the registry's ``agency`` label is
        # PUBLISHER provenance, not operator evidence — it lands as
        # ``camera_registry_publisher`` and never mints an operator
        # relationship or an organisation entity-ref (an OSM/community
        # publisher label is not an evidenced camera operator). Only an
        # authoritative operator field — the target's ``operator`` key or a
        # feature operator alias — mints ``camera_operator``, which the
        # ``link()`` stage then twins into an organisation entity-ref.
        rows.append(self._claim("camera_registry_publisher", self.agency, self.agency, ev))
        if self.operator:
            op = self._claim("camera_operator", self.operator, self.operator, ev)
            if self.state and self.jurisdiction_scheme != "sig.unresolved":
                # The evidenced jurisdiction anchoring the operator's
                # scoped-name identity (SIG-TRUST-004).
                op["partner_jurisdiction"] = f"{self.jurisdiction_scheme}:{self.state}"
            rows.append(op)
        if self.geometry_kind == "point":
            rows.append(self._claim("camera_latitude", self.latitude, str(self.latitude), ev))
            rows.append(self._claim("camera_longitude", self.longitude, str(self.longitude), ev))
            rows.append(
                self._claim(
                    "camera_coordinate_source",
                    self.coordinate_source,
                    self.coordinate_source,
                    ev,
                )
            )
        else:
            # SIG-GEO-003 (P36.4): a non-point registry record declares its
            # shape — the published polygon is a ``fixed_asset_location``
            # geometry-wkt claim and the kind rides ``geometry_kind``. No
            # ``camera_latitude``/``camera_longitude`` device-point claims
            # emit: a programme area is not a point.
            rows.append(self._claim("geometry_kind", self.geometry_kind, self.geometry_kind, ev))
            rows.append(
                self._claim(
                    "fixed_asset_location",
                    self.geometry_wkt,
                    str(self.geometry_wkt),
                    ev,
                )
            )
        for predicate, value in (
            ("camera_name", self.name),
            ("camera_roadway", self.roadway),
            ("camera_county", self.county),
            ("camera_status", self.status),
            ("camera_direction", self.direction),
        ):
            if value is not None:
                rows.append(self._claim(predicate, value, str(value), ev))
        if self.coordinate_precision:
            # P36.5 (P4): the publisher's declared precision caveat rides the
            # coordinate claims too — an "approximate" coordinate can never be
            # re-asserted downstream as an exact device point.
            for row in rows:
                if row.get("predicate_id") in (
                    "camera_latitude",
                    "camera_longitude",
                    "camera_coordinate_source",
                ):
                    row["coordinate_precision"] = self.coordinate_precision
        if self.valid_to_kind is not None:
            # P36.5 (I9a NEW-2): a removal-ledger row bounds EVERY claim it
            # emits — the entity record and the coordinate/status/name claims
            # share one ``valid_to`` bound so the device is never half-removed.
            # The append never deletes: the paired inventory layer's rows stay
            # open until (and if) they publish their own bound.
            for row in rows:
                row["valid_to"] = self.valid_to
                row["valid_to_kind"] = self.valid_to_kind
        return rows


# --- the connector ------------------------------------------------------------


#: The operator predicate whose text claims gain an entity-ref claim (P31.5).
_PARTNER_PREDICATES = frozenset({"camera_operator"})


@register
class Dot511Connector(Connector):
    """The `dot_511` connector: state DOT/511 traffic-camera location registries.

    ``discover`` returns the per-state ArcGIS ``query`` targets resolved from the
    registry (identifiers, not content); ``fetch`` egresses through the shared
    politeness layer only; ``parse``/``extract``/``normalize`` are pure functions
    of the captured bytes. Registry rows only — image/video/stream fields are
    blocklisted by name and never fetched or emitted (Part VIII).
    """

    name = "dot_511"
    version = "1.0.0"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — the reviewed registry rows only."""
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured ArcGIS query JSON (pure, network-isolated).

        An ArcGIS error envelope (``{"error": {…}}``), a non-JSON body (an HTML
        error/WAF page), or a document with no ``features`` list is
        :class:`ContentDrift` — recorded loud, never an opaque crash or a silent
        empty result (P25.1 / ADR-082).
        """
        data = ctx.captures.get(capture.digest)
        target = _resolve_target(ctx, capture.source_uri)
        kind = str(target.get("kind") or "arcgis_query")
        if kind == "socrata_rows":
            return self._parse_socrata(ctx, capture, data, target)
        try:
            doc = json.loads(data)
        except (ValueError, TypeError) as exc:
            head = data[:64] if isinstance(data, (bytes, bytearray)) else str(data)[:64]
            raise ContentDrift(
                ctx.source.id,
                "ArcGIS query returned non-JSON content (HTML error / WAF page)",
                details=f"{len(data)} bytes; starts {head!r} ({exc.__class__.__name__})",
            ) from exc
        if not isinstance(doc, Mapping):
            raise ContentDrift(
                ctx.source.id,
                "ArcGIS query payload is not an object",
                details=f"got {type(doc).__name__}",
            )
        if isinstance(doc.get("error"), Mapping):
            err = doc["error"]
            raise ContentDrift(
                ctx.source.id,
                "ArcGIS query returned an error envelope",
                details=f"code={err.get('code')} message={str(err.get('message'))[:120]!r}",
            )
        if not isinstance(doc.get("features"), list):
            raise ContentDrift(
                ctx.source.id,
                "ArcGIS query payload has no 'features' list",
                details=f"top-level keys: {sorted(doc)}",
            )
        if doc.get("exceededTransferLimit") is True:
            # The flag means "more rows exist beyond this page". On any page
            # before the last planned one that is *expected*; on the last
            # planned page it means the registry outgrew its planned range —
            # fail loud rather than emit a silently truncated registry.
            target = _resolve_target(ctx, capture.source_uri)
            page = int(target.get("page") or 0)
            page_count = int(target.get("page_count") or 1)
            if page >= page_count - 1:
                raise ContentDrift(
                    ctx.source.id,
                    "ArcGIS query page hit the transfer limit — "
                    "the registry outgrew its planned pages",
                    details=(
                        f"page {page + 1}/{page_count} returned "
                        "exceededTransferLimit=true; more rows exist beyond the "
                        "planned resultOffset range — bump the target's "
                        "observed_count in data/dot_511_targets.toml (never emit "
                        "a silently truncated registry)"
                    ),
                )
        return {"kind": "arcgis_feature_query", "payload": doc, "capture": capture}

    def _parse_socrata(
        self, ctx: RunContext, capture: CaptureRef, data: bytes, target: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Structure a captured Socrata ``/resource`` row array (pure, P26.9).

        A Socrata error envelope (``{"code": "…", "error": true}``), a non-JSON
        body, a non-array payload, or a page that returns exactly the page size
        on the LAST planned page (the registry may have outgrown its planned
        pages — the Socrata analogue of ``exceededTransferLimit``) is
        :class:`ContentDrift` — recorded loud, never silently truncated.
        """
        try:
            doc = json.loads(data)
        except (ValueError, TypeError) as exc:
            head = data[:64] if isinstance(data, (bytes, bytearray)) else str(data)[:64]
            raise ContentDrift(
                ctx.source.id,
                "Socrata resource returned non-JSON content (HTML error / WAF page)",
                details=f"{len(data)} bytes; starts {head!r} ({exc.__class__.__name__})",
            ) from exc
        if isinstance(doc, Mapping):
            raise ContentDrift(
                ctx.source.id,
                "Socrata resource returned an error envelope",
                details=(
                    f"code={doc.get('code')!r} message={str(doc.get('message'))[:120]!r} "
                    f"(top-level keys: {sorted(doc)})"
                ),
            )
        if not isinstance(doc, list):
            raise ContentDrift(
                ctx.source.id,
                "Socrata resource payload is not a row array",
                details=f"got {type(doc).__name__}",
            )
        page = int(target.get("page") or 0)
        page_count = int(target.get("page_count") or 1)
        if len(doc) == _SOCRATA_PAGE_SIZE and page >= page_count - 1:
            raise ContentDrift(
                ctx.source.id,
                "Socrata page filled its $limit — the registry may have outgrown its planned pages",
                details=(
                    f"page {page + 1}/{page_count} returned {_SOCRATA_PAGE_SIZE} rows; "
                    "bump the target's observed_count in "
                    "data/camera_registry_targets.toml (never emit a silently "
                    "truncated registry)"
                ),
            )
        return {"kind": "socrata_rows", "payload": {"rows": doc}, "capture": capture}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw camera records with row locators, media fields excluded by name (P2).

        Each feature yields one raw record carrying its attribute map minus the
        media blocklist (names recorded, values dropped), its point geometry,
        the target's registry context (state/agency/licence/sensitivity class),
        and the capture's retrieval timestamp for evidence. A non-object feature
        is drift.
        """
        doc = parsed["payload"]
        capture: CaptureRef = parsed["capture"]
        target = _resolve_target(ctx, capture.source_uri)
        retrieved = capture.retrieved_at or datetime.now(UTC)
        out: list[Mapping[str, Any]] = []
        if parsed.get("kind") == "socrata_rows":
            rows = doc["rows"]
            for index, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    raise ContentDrift(
                        ctx.source.id,
                        "a Socrata row is not an object",
                        details=f"rows[{index}] is {type(row).__name__}",
                    )
                fields, excluded = partition_fields(row)
                out.append(
                    {
                        "record_kind": "camera_feature",
                        "feature_index": index,
                        "fields": dict(fields),
                        "excluded_fields": excluded,
                        "geometry": socrata_point_geometry(fields),
                        "source_uri": capture.source_uri,
                        "retrieved_at": retrieved.isoformat(),
                        "target": dict(target),
                    }
                )
            return out
        for index, feature in enumerate(doc["features"]):
            if not isinstance(feature, Mapping):
                raise ContentDrift(
                    ctx.source.id,
                    "an ArcGIS feature is not an object",
                    details=f"features[{index}] is {type(feature).__name__}",
                )
            attributes = feature.get("attributes")
            if not isinstance(attributes, Mapping):
                raise ContentDrift(
                    ctx.source.id,
                    "an ArcGIS feature carries no 'attributes' map",
                    details=f"features[{index}] keys: {sorted(feature)}",
                )
            fields, excluded = partition_fields(attributes)
            geometry = feature.get("geometry")
            out.append(
                {
                    "record_kind": "camera_feature",
                    "feature_index": index,
                    "fields": dict(fields),
                    "excluded_fields": excluded,
                    "geometry": dict(geometry) if isinstance(geometry, Mapping) else None,
                    "source_uri": capture.source_uri,
                    "retrieved_at": retrieved.isoformat(),
                    "target": dict(target),
                }
            )
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist.

        Coordinates are extracted, range-checked, and tier-applied here — a
        record that fails the coordinate policy lands as a
        ``camera_record_rejected`` row (recorded, never a claim). A capture
        whose features ALL fail is :class:`ContentDrift` — a 100%-rejection
        feed is a schema change, not an empty registry.
        """
        out: list[dict[str, Any]] = []
        emitted = 0
        rejected = 0
        for raw in raw_claims:
            if raw.get("record_kind") != "camera_feature":
                continue
            target: Mapping[str, Any] = raw.get("target") or {}
            try:
                entry = _entry_from_raw(ctx.source.id, raw, target)
            except (CoordinateRejected, ValueError) as exc:
                rejected += 1
                reason = exc.reason if isinstance(exc, CoordinateRejected) else "no_registry_key"
                out.append(_rejection_row(ctx.source.id, raw, target, reason, str(exc)))
                continue
            emitted += 1
            out.extend(
                entry.claim_rows(
                    str(raw["source_uri"]), str(raw["retrieved_at"]), int(raw["feature_index"])
                )
            )
        if raw_claims and emitted == 0 and rejected > 0:
            raise ContentDrift(
                ctx.source.id,
                "every camera record failed the coordinate/identity policy",
                details=f"{rejected} rejected, 0 emitted — the layer schema likely drifted",
            )
        return out

    # -- link + load --
    # SIG-INGEST-034: candidate identifiers only; the identity layer decides whether
    # the registry's operator stands as an organisation (P31.5 / ADR-112).

    def link(self, ctx: RunContext, normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Append the ``camera_operator`` entity-ref claims (P31.5 / ADR-112,
        role-repaired by P32.3 / ADR-122).

        Only an authoritative ``camera_operator`` claim twins an organisation
        entity-ref — the registry PUBLISHER label (``camera_registry_publisher``)
        is provenance and mints nothing (a community-map publisher is not an
        evidenced camera operator). Each mint carries the claim's evidenced
        jurisdiction (``partner_jurisdiction``, e.g. ``us.state_abbr:OK``) so the
        operator's scoped-name identity stays inside its jurisdiction
        (SIG-TRUST-004); a composite operator ("King County / WSDOT") names two
        parties and stays text only.
        """
        return partner_ref_rows(normalized, predicates=_PARTNER_PREDICATES, scope=ctx.source.id)

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only, SIG-INGEST-003)."""
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------

#: The evidence extraction method each platform kind stamps on claims (P26.9).
_EXTRACTION_METHODS = {
    "arcgis_query": "arcgis_feature_json",
    "socrata_rows": "socrata_rows_json",
}


def _resolve_target(ctx: RunContext, source_uri: str) -> dict[str, Any]:
    """The registry metadata for the target a capture was fetched from.

    A run-time target (``ctx.parameters['targets']``) matches by exact URL or
    ``layer_url`` prefix; the registry row supplies defaults for any field the
    run-time row omits (state/agency/licence/sensitivity). A fixture replay
    supplies a synthetic single target — resolved by falling back to the
    source's single registry row when no URL match exists. An unmatched target
    returns ``{}`` and the record fails closed as ``unmatched_target``.
    """
    targets = list(ctx.parameters.get("targets", []))
    matched: Mapping[str, Any] = {}
    for t in targets:
        if str(t.get("url")) == source_uri or (
            str(t.get("layer_url")) and source_uri.startswith(str(t["layer_url"]))
        ):
            matched = t
            break
    registry = registry_row(ctx.source.id, str(matched.get("id") or ""))
    if not registry and not matched:
        registry = registry_row(ctx.source.id)
    merged = {**registry, **dict(matched)}
    return merged


def _entry_from_raw(
    source_id: str, raw: Mapping[str, Any], target: Mapping[str, Any]
) -> CameraRegistryEntry:
    """Map one raw feature onto :class:`CameraRegistryEntry` via the field aliases."""
    fields: Mapping[str, Any] = raw["fields"]
    if not str(target.get("id") or "").strip():
        raise CoordinateRejected(
            "unmatched_target",
            "the capture's source URI matches no configured registry target",
        )
    # PKG-07 (P35.15a): the declared technology + record kind come from the
    # matched registry row — a target without a member slug fails the RUN
    # (TechnologyNotDeclared is deliberately not a per-record rejection: a
    # broken registry row is a config defect, never a silently untyped row).
    technology = assert_target_technology(target)
    record_kind = declared_record_kind(target)
    geometry_kind = assert_target_geometry_kind(target)
    ref_pair = _first_field(fields, vocab()["id_fields"])
    if ref_pair is None:
        raise CoordinateRejected(
            "missing", "no camera identity field matched the id_fields aliases"
        )
    sensitivity_class = str(target.get("sensitivity_class") or vocab()["default_sensitivity_class"])
    # SIG-GEO-003 (P36.4): the record's declared shape picks the geometry path.
    # A point record resolves its operator-published coordinate as before; an
    # area record serialises the published polygon rings to WKT + a derived
    # centroid and never mints a device-point coordinate.
    lat: float | None = None
    lon: float | None = None
    centroid_lat: float | None = None
    centroid_lon: float | None = None
    geometry_wkt: str | None = None
    ring_count = 0
    if geometry_kind == "area":
        geometry_wkt, centroid_raw_lat, centroid_raw_lon, ring_count = area_geometry(
            raw.get("geometry")
        )
        centroid_lat, centroid_lon, tier = publishable_coordinate(
            centroid_raw_lat, centroid_raw_lon, sensitivity_class
        )
        coord_source = "geometry:rings"
    elif geometry_kind == "point":
        lat, lon, coord_source = extract_coordinate(fields, raw.get("geometry"))
        lat, lon, tier = publishable_coordinate(lat, lon, sensitivity_class)
    else:
        raise CoordinateRejected(
            "unsupported_geometry",
            f"target declares geometry_kind {geometry_kind!r}, which has no emit path",
        )

    def _s(aliases_key: str) -> str | None:
        pair = _first_field(fields, vocab()[aliases_key])
        if pair is None:
            return None
        text = str(pair[1]).strip()
        return text or None

    operator = str(target.get("operator") or "").strip() or _s("operator_fields")
    status = _s("status_fields")

    # P36.5 (ACQ-09): the target's declared status disposition decides how the
    # published status column reads. A "removal" target is a removal ledger —
    # a row whose published status is a declared removal value bounds the
    # device: the layer's published date emits ``valid_to`` with
    # ``valid_to_kind="exact"``; a removal flag with no published date emits
    # ``valid_to_kind="unknown"`` (an ended-when-unknown bound, never a
    # fabricated date — P4). A non-removal status value emits no bound at
    # all, and the verbatim published status still rides ``camera_status``
    # either way (the S5 guard — published values stay published).
    valid_to: str | None = None
    valid_to_kind: str | None = None
    if assert_target_status_disposition(target) == "removal":
        if status is not None and status.strip().lower() in _row_removal_status_values(target):
            removal_date = _first_field(fields, vocab()["removal_date_fields"])
            if removal_date is not None:
                valid_to = str(removal_date[1]).strip()
                valid_to_kind = "exact"
            else:
                valid_to = None
                valid_to_kind = "unknown"

    return CameraRegistryEntry(
        camera_ref=str(ref_pair[1]),
        source_id=source_id,
        target_id=str(target.get("id") or "unknown_target"),
        state=str(target.get("state") or ""),
        agency=str(target.get("agency") or ""),
        technology=technology,
        record_kind=record_kind,
        operator=operator,
        latitude=lat,
        longitude=lon,
        coordinate_source=coord_source,
        geo_tier=tier,
        sensitivity_class=sensitivity_class,
        license_spdx=str(target.get("license_spdx") or ""),
        name=_s("name_fields"),
        roadway=_s("roadway_fields"),
        county=_s("county_fields"),
        status=status,
        direction=_s("direction_fields"),
        coordinate_precision=assert_target_coordinate_precision(target),
        valid_to=valid_to,
        valid_to_kind=valid_to_kind,
        excluded_fields=tuple(raw.get("excluded_fields") or ()),
        jurisdiction_scheme=str(target.get("jurisdiction_scheme") or "us.state_abbr"),
        extraction_method=_EXTRACTION_METHODS.get(
            str(target.get("kind") or "arcgis_query"), "arcgis_feature_json"
        ),
        geometry_kind=geometry_kind,
        geometry_wkt=geometry_wkt,
        centroid_latitude=centroid_lat,
        centroid_longitude=centroid_lon,
        ring_count=ring_count,
    )


def _rejection_row(
    source_id: str,
    raw: Mapping[str, Any],
    target: Mapping[str, Any],
    reason: str,
    detail: str,
) -> dict[str, Any]:
    """The recorded disposition for a record that failed closed — never a claim."""
    fields: Mapping[str, Any] = raw.get("fields") or {}
    return _stamp(
        {
            "record_kind": "camera_record_rejected",
            "subject_id": (
                f"traffic_camera:{source_id}:"
                f"{target.get('id') or 'unknown'}:rejected:{raw.get('feature_index')}"
            ),
            "predicate_id": assert_predicate_allowed("traffic_camera"),
            "raw_value": reason,
            "rejection_reason": reason,
            "rejection_detail": detail,
            "feature_index": raw.get("feature_index"),
            "field_names_present": sorted(str(k) for k in fields),
            "target_id": str(target.get("id") or ""),
            "state": str(target.get("state") or ""),
        },
        source_id=source_id,
        license_spdx=str(target.get("license_spdx") or ""),
    )


def _stamp(row: dict[str, Any], *, source_id: str, license_spdx: str) -> dict[str, Any]:
    """Stamp a row with its source id, licence, and the connector vocab version."""
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    if license_spdx:
        row.setdefault("license", license_spdx)
    return row


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 row needs.

    ``claim_id`` and ``sys_period`` are the two non-deterministic columns the
    reproducibility fingerprint excludes (SIG-INGEST-003). Entity and claim rows
    get an identity; rejection rows keep their own keys.
    """
    out: list[dict[str, Any]] = []
    for claim in claims:
        # Entity rows are the registry-record assertions (predicate
        # ``traffic_camera``); their record_kind is the declared subtype
        # (P35.15a — any technology slug or an explicit ``traffic_camera``).
        # Rejection rows share the predicate but keep their own keys.
        is_entity_row = (
            claim.get("predicate_id") == "traffic_camera"
            and claim.get("record_kind") != "camera_record_rejected"
        )
        if claim.get("record_kind") == "claim" or is_entity_row:
            out.append(
                {
                    **claim,
                    "claim_id": str(uuid4()),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        else:
            out.append(dict(claim))
    return out


def canary_findings(parsed: Mapping[str, Any]) -> list[str]:
    """Structural-drift findings for an ArcGIS feature query (SIG-PARSE-008 canary).

    An empty list means no drift. Checks the shape the parser depends on: a
    ``features`` list of objects each carrying an ``attributes`` map; point
    geometry, when present, carries numeric ``x``/``y``. Field *names* are not
    asserted — the alias vocabulary handles naming drift as data.
    """
    payload = parsed.get("payload", parsed)
    findings: list[str] = []
    features = payload.get("features")
    if not isinstance(features, list):
        return ["missing top-level 'features' list"]
    for i, feature in enumerate(features):
        if not isinstance(feature, Mapping):
            findings.append(f"features[{i}] is not an object")
            continue
        if not isinstance(feature.get("attributes"), Mapping):
            findings.append(f"features[{i}] has no 'attributes' map")
        geometry = feature.get("geometry")
        if geometry is not None:
            if not isinstance(geometry, Mapping):
                findings.append(f"features[{i}] geometry is not an object")
            elif "rings" in geometry:
                # P36.4: a polygon (area) layer carries `rings`, not x/y —
                # programme-area records are valid shapes, not point drift.
                rings = geometry["rings"]
                if not isinstance(rings, list) or not all(isinstance(r, list) for r in rings):
                    findings.append(f"features[{i}] geometry 'rings' is not a list of rings")
            elif not all(isinstance(geometry.get(k), (int, float)) for k in ("x", "y")):
                findings.append(f"features[{i}] geometry lacks numeric x/y")
    return findings


__all__ = [
    "CameraRegistryEntry",
    "CoordinatePrecisionNotDeclared",
    "CoordinateRejected",
    "Dot511Connector",
    "GeometryKindNotDeclared",
    "PredicateNotAllowed",
    "StatusDispositionNotDeclared",
    "TechnologyNotDeclared",
    "area_geometry",
    "assert_predicate_allowed",
    "assert_target_coordinate_precision",
    "assert_target_geometry_kind",
    "assert_target_status_disposition",
    "assert_target_technology",
    "canary_findings",
    "declared_record_kind",
    "declared_technologies",
    "enumerated_outcomes",
    "extract_coordinate",
    "geometry_kinds",
    "is_media_field",
    "load_claims_for_l1",
    "partition_fields",
    "predicate_allowlist",
    "publishable_coordinate",
    "registry_targets",
    "target_geometry_violations",
    "target_status_violations",
    "target_technology_violations",
    "technology_slugs",
    "vocab",
    "vocab_version",
]
