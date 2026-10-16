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


# --- the declared aggregate transport (P36.6 / ACQ-10, I8 NEW-7) --------------

#: The aggregate target kinds this connector expands (I8 NEW-7): the count
#: lanes whose published rows are enforcement aggregates — a camera × month or
#: site × quarter count of warnings/violations — never a per-violation, plate
#: or citation row. ``socrata_aggregate`` issues a bounded SoQL
#: ``$select … $group … $where`` query (or reads a dataset the publisher
#: already aggregates, ``count_function="verbatim"``);
#: ``arcgis_outstatistics`` issues a bounded ``outStatistics`` +
#: ``groupByFieldsForStatistics`` query.
_AGGREGATE_KINDS = frozenset({"socrata_aggregate", "arcgis_outstatistics"})

#: The closed vocabulary for an aggregate target's ``aggregate_period_kind`` —
#: how the published period column reads. ``"month"`` truncates a published
#: datetime column server-side (``date_trunc_ym(<field>)``); ``"verbatim"``
#: carries the publisher's own period label (``YEAR_MONTH``, ``quarter_name``).
_PERIOD_KINDS = frozenset({"month", "verbatim"})

#: The closed vocabulary for ``aggregate_count_function``. ``"sum"`` asks the
#: platform to total the published per-row measure (``sum(<field>)`` /
#: ``statisticType=sum``); ``"verbatim"`` reads a dataset already published as
#: an aggregate — the published total IS the count, no server-side grouping.
#: ArcGIS ``outStatistics`` requires a statistic function, so ``"verbatim"``
#: is only legal on ``socrata_aggregate``.
_COUNT_FUNCTIONS = frozenset({"sum", "verbatim"})

#: Declared field names land verbatim inside the SoQL ``$select``/``$group``
#: and ArcGIS ``outStatistics`` query text — a bare column identifier only,
#: never an expression or quoted literal smuggled through the registry row.
_FIELD_NAME_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class AggregateSpecNotDeclared(Exception):
    """A registry defect: a malformed aggregate-target declaration.

    Deliberately NOT a per-record rejection: an aggregate target without a
    complete, well-formed ``aggregate_*`` declaration is a broken registry
    row — the run fails loudly rather than inventing a group/period/measure
    surface the publisher never declared (P36.6).
    """


@dataclass(frozen=True)
class AggregateSpec:
    """The validated aggregate declaration carried by an aggregate target row.

    ``subject_field`` names the published key the aggregate subject resolves
    on (a camera/site/enforcement-space code); ``period_field`` +
    ``period_kind`` name the published period column and how it reads;
    ``count_field`` + ``count_function`` name the published measure column
    and the platform function that totals it; ``measure`` is the claim's
    declared unit (``"violations"``); ``discriminator_field`` names an
    optional published column that disambiguates concurrent count series on
    the same subject × period (DC's ``ENFORCEMENT_TYPE`` — its published
    value rides the claim's ``series`` field so the red-light, speed and
    other series on one space-month never collide).
    """

    subject_field: str
    period_field: str
    period_kind: str
    count_field: str
    count_function: str
    measure: str
    discriminator_field: str | None


def _aggregate_field(row: Mapping[str, Any], key: str, target_id: Any) -> str:
    """One validated bare-identifier field name from an aggregate declaration."""
    value = str(row.get(key) or "").strip()
    if not _FIELD_NAME_RE.fullmatch(value):
        raise AggregateSpecNotDeclared(
            f"registry target {target_id!r} declares {key}={value!r} — an "
            "aggregate declaration field must be a bare published column "
            "identifier, never an expression (the query text is committed "
            "registry data, fail closed)"
        )
    return value


def assert_target_aggregate(row: Mapping[str, Any]) -> AggregateSpec | None:
    """The target row's validated :class:`AggregateSpec`, or ``None``.

    Non-aggregate kinds return ``None``. An aggregate kind without a complete
    declaration — or whose period/count vocabulary is outside the closed
    members — is a registry defect (fail closed), never a guessed grouping.
    """
    kind = str(row.get("kind") or "").strip()
    if kind not in _AGGREGATE_KINDS:
        return None
    target_id = row.get("id")
    period_kind = str(row.get("aggregate_period_kind") or "").strip()
    if period_kind not in _PERIOD_KINDS:
        raise AggregateSpecNotDeclared(
            f"registry target {target_id!r} declares aggregate_period_kind="
            f"{period_kind!r}, which is not a member ({sorted(_PERIOD_KINDS)})"
        )
    count_function = str(row.get("aggregate_count_function") or "").strip()
    if count_function not in _COUNT_FUNCTIONS:
        raise AggregateSpecNotDeclared(
            f"registry target {target_id!r} declares aggregate_count_function="
            f"{count_function!r}, which is not a member ({sorted(_COUNT_FUNCTIONS)})"
        )
    if kind == "arcgis_outstatistics" and count_function == "verbatim":
        raise AggregateSpecNotDeclared(
            f"registry target {target_id!r}: 'verbatim' has no ArcGIS "
            "statisticType — a pre-aggregated ArcGIS table aggregates via "
            "'sum' (or registers as an arcgis_query lane)"
        )
    if kind == "arcgis_outstatistics" and period_kind != "verbatim":
        raise AggregateSpecNotDeclared(
            f"registry target {target_id!r}: ArcGIS "
            "groupByFieldsForStatistics groups verbatim columns only — the "
            "period expression is the column itself"
        )
    measure = str(row.get("aggregate_measure") or "").strip()
    if not measure:
        raise AggregateSpecNotDeclared(
            f"registry target {target_id!r} declares no 'aggregate_measure' — "
            "the count's unit must be declared, never implied"
        )
    discriminator = str(row.get("aggregate_discriminator_field") or "").strip()
    return AggregateSpec(
        subject_field=_aggregate_field(row, "aggregate_subject_field", target_id),
        period_field=_aggregate_field(row, "aggregate_period_field", target_id),
        period_kind=period_kind,
        count_field=_aggregate_field(row, "aggregate_count_field", target_id),
        count_function=count_function,
        measure=measure,
        discriminator_field=(
            _aggregate_field(row, "aggregate_discriminator_field", target_id)
            if discriminator
            else None
        ),
    )


def target_aggregate_violations() -> list[str]:
    """``sig-connectors validate`` rules for the aggregate declarations (P36.6)."""
    violations: list[str] = []
    for row in target_table().get("targets", []):
        label = f"target {row.get('id')!r} (source {row.get('source_id')!r})"
        try:
            assert_target_aggregate(row)
        except AggregateSpecNotDeclared as exc:
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


def _socrata_aggregate_pages(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expand one ``socrata_aggregate`` row into deterministic grouped pages.

    The reviewed SoQL shape (I8 NEW-7)::

        $select=<subject> AS subject, <period expr> AS period,
                <count expr> AS count[, <disc> AS discriminator]
        &$group=<subject>,<period expr>[,<disc>]
        &$where=<window>
        &$order=<subject>,<period expr>[,<disc>]
        &$limit=5000&$offset=<n>

    ``period_kind="month"`` wraps the period column in ``date_trunc_ym(…)``;
    ``"verbatim"`` selects the published period label itself.
    ``count_function="verbatim"`` names a dataset the publisher already
    aggregates (a site × quarter table): no ``$group`` is emitted — the
    published row IS the group row — and its column selects verbatim as
    ``count``. Output columns are aliased to the canonical
    ``subject``/``period``/``count``/``discriminator`` names so the emit path
    never guesses field names; the group/order clauses carry the underlying
    expressions.
    """
    spec = assert_target_aggregate(row)
    assert spec is not None  # aggregate kind ⇒ validated spec
    resource_url = str(row["layer_url"]).rstrip("/")
    observed = int(row.get("observed_count") or 0)
    pages = max(1, -(-observed // _SOCRATA_PAGE_SIZE))
    period_expr = (
        f"date_trunc_ym({spec.period_field})" if spec.period_kind == "month" else spec.period_field
    )
    count_expr = (
        f"{spec.count_function}({spec.count_field})"
        if spec.count_function != "verbatim"
        else spec.count_field
    )
    select_parts = [
        f"{spec.subject_field} AS subject",
        f"{period_expr} AS period",
        f"{count_expr} AS count",
    ]
    order_parts = [spec.subject_field, period_expr]
    if spec.discriminator_field is not None:
        select_parts.append(f"{spec.discriminator_field} AS discriminator")
        order_parts.append(spec.discriminator_field)
    params: dict[str, Any] = {"$select": ",".join(select_parts)}
    if spec.count_function != "verbatim":
        params["$group"] = ",".join(order_parts)
    where = str(row.get("where") or "").strip()
    if where:
        # The first-window bound (2023-10 onward, ≈ 36 months) is committed
        # target data, reviewed like the arcgis `where` allowlist (P36.4).
        params["$where"] = where
    params["$order"] = ",".join(order_parts)
    out: list[dict[str, Any]] = []
    for page in range(pages):
        page_params = {
            **params,
            "$limit": _SOCRATA_PAGE_SIZE,
            "$offset": page * _SOCRATA_PAGE_SIZE,
        }
        out.append(
            {
                "url": f"{resource_url}?{urlencode(page_params)}",
                "page": page,
                "page_count": pages,
            }
        )
    return out


def _arcgis_outstatistics_pages(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expand one ``arcgis_outstatistics`` row into deterministic grouped pages.

    The reviewed query shape (I8 NEW-7): ``groupByFieldsForStatistics`` names
    the subject + period (+ discriminator) columns verbatim,
    ``outStatistics`` carries one ``sum`` statistic aliased ``count``, and the
    response's ``features[].attributes`` are group rows — never geometry,
    never a per-violation row. Pages are ``resultOffset`` /
    ``resultRecordCount`` over the group columns so a >1,000-group table is
    captured whole; ``exceededTransferLimit`` on the last planned page fails
    loud in ``parse``, same as the feature layers.
    """
    spec = assert_target_aggregate(row)
    assert spec is not None
    layer_url = str(row["layer_url"]).rstrip("/")
    observed = int(row.get("observed_count") or 0)
    page_size = min(_ARCGIS_PAGE_SIZE, max(1, int(row.get("page_size") or _ARCGIS_PAGE_SIZE)))
    pages = max(1, -(-observed // page_size))
    group_fields = [spec.subject_field, spec.period_field]
    if spec.discriminator_field is not None:
        group_fields.append(spec.discriminator_field)
    out_statistics = json.dumps(
        [
            {
                "statisticType": spec.count_function,
                "onStatisticField": spec.count_field,
                "outStatisticFieldName": "count",
            }
        ],
        separators=(",", ":"),
    )
    params_base = {
        "where": str(row.get("where") or "1=1").strip() or "1=1",
        "groupByFieldsForStatistics": ",".join(group_fields),
        "outStatistics": out_statistics,
        "returnGeometry": "false",
        "orderByFields": ",".join(group_fields),
        "f": "json",
    }
    out: list[dict[str, Any]] = []
    for page in range(pages):
        params = {
            **params_base,
            "resultRecordCount": page_size,
            "resultOffset": page * page_size,
        }
        out.append(
            {"url": f"{layer_url}/query?{urlencode(params)}", "page": page, "page_count": pages}
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
    expanders = {
        "arcgis_query": _arcgis_pages,
        "socrata_rows": _socrata_pages,
        # P36.6 (ACQ-10, I8 NEW-7): the aggregate count lanes — grouped SoQL
        # and ArcGIS outStatistics queries emitting enforcement_count rows.
        "socrata_aggregate": _socrata_aggregate_pages,
        "arcgis_outstatistics": _arcgis_outstatistics_pages,
    }
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
        if rpm is None and kind in ("arcgis_query", "arcgis_outstatistics"):
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
        # P36.6 (ACQ-10): the aggregate declaration + the declared field
        # bindings (camera_ref_field / deployment_date_field) are validated
        # at expansion — a broken declaration is a registry defect, never a
        # guessed emit.
        aggregate = assert_target_aggregate(row)
        declared_fields = {
            key: str(row.get(key)).strip()
            for key in ("camera_ref_field", "deployment_date_field")
            if str(row.get(key) or "").strip()
        }
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
            if aggregate is not None:
                target["aggregate"] = {
                    "subject_field": aggregate.subject_field,
                    "period_field": aggregate.period_field,
                    "period_kind": aggregate.period_kind,
                    "count_field": aggregate.count_field,
                    "count_function": aggregate.count_function,
                    "measure": aggregate.measure,
                    "discriminator_field": aggregate.discriminator_field,
                }
            for key, value in declared_fields.items():
                target[key] = value
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


def socrata_line_geometry_probe(fields: Mapping[str, Any]) -> dict[str, Any] | None:
    """Surface ANY dict-valued geometry column on a ``line`` target (P36.6).

    A ``geometry_kind="line"`` route/programme register (MTA's ABLE routes)
    declares NO path geometry — the published surface is a tabular register.
    ``socrata_point_geometry`` would silently drop a ``LineString``/``Polygon``
    under a declared column (it only surfaces ``Point`` shapes), so a line
    target probes for the raw dict itself: surfacing it as the record's
    ``geometry`` makes :func:`_entry_from_raw` fail closed
    (``unsupported_geometry``) instead of asserting "no geometry" against a
    capture that DID carry a path. ``None`` means the capture is the expected
    geometry-free register row.
    """
    for name in vocab()["point_fields"]:
        value = fields.get(name)
        if isinstance(value, Mapping):
            return dict(value)
    return None


def socrata_area_geometry(fields: Mapping[str, Any]) -> dict[str, Any] | None:
    """The ``{"rings": …}`` geometry from a Socrata polygon column (P36.6).

    An area/zone Socrata dataset — Howard County's school-zone layer
    (``the_geom``) — carries a GeoJSON ``Polygon``/``MultiPolygon`` column
    instead of a point. This converts it to the ArcGIS ``rings`` convention
    :func:`area_geometry` consumes: each polygon's exterior ring is wound so
    its signed area is negative (ArcGIS's exterior convention) and each hole
    positive, so the shared WKT/centroid path applies unchanged. Returns
    ``None`` when no declared point-field column carries polygon coordinates —
    the record then fails closed inside ``area_geometry`` as ``missing``.
    """
    for name in vocab()["point_fields"]:
        value = fields.get(name)
        if not isinstance(value, Mapping):
            continue
        geo_type = str(value.get("type") or "").lower()
        coords = value.get("coordinates")
        if not isinstance(coords, list):
            continue
        if geo_type == "polygon":
            polygons = [coords]
        elif geo_type == "multipolygon":
            polygons = coords
        else:
            continue
        rings: list[Any] = []
        for polygon in polygons:
            if not isinstance(polygon, list):
                continue
            for i, ring in enumerate(polygon):
                checked = _checked_ring(ring, len(rings))
                if i == 0:
                    # Exterior ring — ArcGIS's convention winds it so the
                    # signed area is negative (Y-up lon/lat).
                    rings.append(
                        checked if _ring_signed_area(checked) < 0 else list(reversed(checked))
                    )
                else:
                    # Hole ring — positive signed area.
                    rings.append(
                        checked if _ring_signed_area(checked) > 0 else list(reversed(checked))
                    )
        if rings:
            return {"rings": rings}
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
    #: P36.6 (ACQ-10): the published deployment-date column's value when the
    #: target declares ``deployment_date_field`` (MTA's ``implementation_date``
    #: — the route's enforced-since date). Emits verbatim under
    #: ``installation_date``; ``None`` on every undeclared record.
    installation_date: str | None = None

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
        if self.geometry_kind == "area" and (
            self.geometry_wkt is None
            or self.centroid_latitude is None
            or self.centroid_longitude is None
        ):
            raise ValueError(
                "an area CameraRegistryEntry requires geometry_wkt + a derived centroid"
            )
        # P36.6 (ACQ-10): a ``line`` record — a published route/programme
        # register row — legitimately carries NO geometry (the publisher
        # ships no path column): it asserts the shape kind only. The
        # contract is symmetric: a line entry must be all-geometry-free
        # (the emit path mints no WKT this ticket) or fully-formed — a
        # WKT without its derived centroid is the half-formed surface this
        # check exists to refuse.
        if self.geometry_kind == "line" and (
            (self.geometry_wkt is None)
            != (self.centroid_latitude is None and self.centroid_longitude is None)
        ):
            raise ValueError(
                "a line CameraRegistryEntry is geometry-free (route/programme "
                "record) or carries wkt + a derived centroid — never half-formed"
            )
        if self.geometry_kind == "line" and self.ring_count != 0:
            raise ValueError("a geometry-free line CameraRegistryEntry carries no ring count")
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
            # emit: a programme area is not a point. P36.6 (ACQ-10): a
            # geometry-free ``line`` record (a route/programme register row
            # that publishes no path) asserts its ``geometry_kind`` only —
            # no ``fixed_asset_location`` claim mints a null geometry.
            rows.append(self._claim("geometry_kind", self.geometry_kind, self.geometry_kind, ev))
            if self.geometry_wkt is not None:
                rows.append(
                    self._claim(
                        "fixed_asset_location",
                        self.geometry_wkt,
                        str(self.geometry_wkt),
                        ev,
                    )
                )
        if self.installation_date is not None:
            # P36.6 (ACQ-10): the declared deployment-date column emits
            # verbatim under `installation_date` — the route/programme's
            # enforced-since date (MTA `implementation_date`).
            rows.append(
                self._claim(
                    "installation_date",
                    self.installation_date,
                    str(self.installation_date),
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
        if kind in ("socrata_rows", "socrata_aggregate"):
            # P36.6 (ACQ-10): a socrata_aggregate capture is the same /resource
            # JSON row array — the rows just carry the grouped subject/period/
            # count aliases the committed $select produces.
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
        target_kind = str(target.get("kind") or "")
        is_aggregate = target_kind in _AGGREGATE_KINDS
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
                if is_aggregate:
                    # P36.6 (ACQ-10): the row is a grouped subject × period
                    # count record — never geometry, never a per-violation row.
                    out.append(
                        {
                            "record_kind": "enforcement_aggregate",
                            "feature_index": index,
                            "fields": dict(fields),
                            "excluded_fields": excluded,
                            "geometry": None,
                            "source_uri": capture.source_uri,
                            "retrieved_at": retrieved.isoformat(),
                            "target": dict(target),
                        }
                    )
                    continue
                out.append(
                    {
                        "record_kind": "camera_feature",
                        "feature_index": index,
                        "fields": dict(fields),
                        "excluded_fields": excluded,
                        # P36.6 (ACQ-10): an area-declared Socrata target
                        # resolves its polygon column (GeoJSON) into the
                        # rings shape area_geometry consumes; a line-declared
                        # target probes for ANY geometry-bearing column — a
                        # capture carrying a path must reach _entry_from_raw
                        # as non-None so the record fails closed rather than
                        # silently asserting "no geometry".
                        "geometry": (
                            socrata_area_geometry(fields)
                            if str(target.get("geometry_kind") or "").strip() == "area"
                            else socrata_line_geometry_probe(fields)
                            if str(target.get("geometry_kind") or "").strip() == "line"
                            else socrata_point_geometry(fields)
                        ),
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
                    # P36.6 (ACQ-10): an outStatistics feature's attributes are
                    # one group row (subject + period + count) — never a
                    # geometry, never a per-violation row.
                    "record_kind": ("enforcement_aggregate" if is_aggregate else "camera_feature"),
                    "feature_index": index,
                    "fields": dict(fields),
                    "excluded_fields": excluded,
                    "geometry": (
                        None
                        if is_aggregate
                        else dict(geometry)
                        if isinstance(geometry, Mapping)
                        else None
                    ),
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
            target: Mapping[str, Any] = raw.get("target") or {}
            if raw.get("record_kind") == "enforcement_aggregate":
                # P36.6 (ACQ-10): a site-period aggregate row emits its
                # subject identity + the enforcement_count claim; a row
                # missing its subject/period/count fails closed, recorded.
                try:
                    rows = _aggregate_claim_rows(ctx.source.id, raw, target)
                except (CoordinateRejected, ValueError) as exc:
                    rejected += 1
                    reason = (
                        exc.reason if isinstance(exc, CoordinateRejected) else "no_registry_key"
                    )
                    out.append(_rejection_row(ctx.source.id, raw, target, reason, str(exc)))
                    continue
                emitted += 1
                out.extend(rows)
                continue
            if raw.get("record_kind") != "camera_feature":
                continue
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
#: P36.6 (ACQ-10): the aggregate kinds share their row-kind's wire shape — a
#: grouped SoQL response is still a Socrata JSON row array, an outStatistics
#: response still ArcGIS feature attributes.
_EXTRACTION_METHODS = {
    "arcgis_query": "arcgis_feature_json",
    "socrata_rows": "socrata_rows_json",
    "socrata_aggregate": "socrata_rows_json",
    "arcgis_outstatistics": "arcgis_feature_json",
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
    # P36.6 (ACQ-10): a target may pin the published subject key explicitly
    # (``camera_ref_field`` — MTA's route key, DC's ENFORCEMENT_SPACE_CODE)
    # when the dataset's meaningful key sits outside the generic alias walk.
    # An absent declared column fails closed, never a silent alias fallback.
    ref_field = str(target.get("camera_ref_field") or "").strip()
    ref_pair: tuple[str, Any] | None
    if ref_field:
        if fields.get(ref_field) in (None, "") or isinstance(fields.get(ref_field), Mapping):
            raise CoordinateRejected(
                "missing", f"declared camera_ref_field {ref_field!r} is absent or empty"
            )
        ref_pair = (ref_field, fields[ref_field])
    else:
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
    elif geometry_kind == "line":
        # P36.6 (ACQ-10): a route/programme record declares shape ``line`` —
        # an enforced corridor (MTA's bus-lane ATE routes), not a device
        # point or a bounded zone. The published dataset is a tabular
        # programme register (``program``/``route``/``implementation_date``)
        # that carries NO path geometry, so the record asserts the shape
        # only: ``geometry_wkt``/centroid stay ``None`` and no
        # ``fixed_asset_location`` claim emits. A capture that DOES carry a
        # path fails closed — the polyline→WKT emit path is not this
        # ticket's, and silently dropping it would assert "no geometry"
        # against published evidence.
        if raw.get("geometry") is not None:
            raise CoordinateRejected(
                "unsupported_geometry",
                "a line record carrying published path geometry has no emit "
                "path this ticket — the polyline WKT serialiser does not "
                "exist yet",
            )
        coord_source = "none"
        tier = 0
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

    # P36.6 (ACQ-10): the declared deployment-date column (MTA's
    # `implementation_date`) emits verbatim under `installation_date`; an
    # absent or non-scalar declared column emits nothing (the fact is "not
    # asserted", never fabricated).
    dep_field = str(target.get("deployment_date_field") or "").strip()
    installation_date: str | None = None
    if dep_field:
        dep_value = fields.get(dep_field)
        if dep_value is not None and not isinstance(dep_value, (Mapping, list, tuple)):
            installation_date = str(dep_value).strip() or None

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
        installation_date=installation_date,
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


def _aggregate_claim_rows(
    source_id: str, raw: Mapping[str, Any], target: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """The entity + claim rows for one site-period aggregate record (P36.6).

    The subject is the published site key (``aggregate_subject_field`` —
    DC's ``ENFORCEMENT_SPACE_CODE``, Montgomery's ``site_number``, Chicago's
    ``camera_id``) minted under the same ``traffic_camera:`` subject scheme
    the site layers use, so the count series joins the location record at
    ER. The ``enforcement_count`` claim carries ``{period, count, measure}``
    — a ``series`` field when the target declares a discriminator column
    (DC's ``ENFORCEMENT_TYPE`` splits one space-month into per-type series).
    A row with no subject key, no period label, or a non-numeric count fails
    closed — an aggregate record never invents the window or the total.
    """
    fields: Mapping[str, Any] = raw["fields"]
    if not str(target.get("id") or "").strip():
        raise CoordinateRejected(
            "unmatched_target",
            "the capture's source URI matches no configured registry target",
        )
    # The expanded target carries the spec already validated at expansion
    # under its "aggregate" member — a record arriving from a target whose
    # spec is absent or malformed is a defect, never a guessed grouping.
    spec_map = target.get("aggregate")
    if not isinstance(spec_map, Mapping):
        raise CoordinateRejected(
            "unsupported_geometry",
            "an enforcement_aggregate record arrived from a non-aggregate target",
        )
    try:
        spec = AggregateSpec(
            subject_field=str(spec_map["subject_field"]),
            period_field=str(spec_map["period_field"]),
            period_kind=str(spec_map["period_kind"]),
            count_field=str(spec_map["count_field"]),
            count_function=str(spec_map["count_function"]),
            measure=str(spec_map["measure"]),
            discriminator_field=(
                str(spec_map["discriminator_field"])
                if spec_map.get("discriminator_field")
                else None
            ),
        )
    except KeyError as exc:
        raise CoordinateRejected(
            "unmatched_target",
            f"the target's aggregate spec is missing a member: {exc}",
        ) from exc
    kind = str(target.get("kind") or "")
    if kind == "arcgis_outstatistics":
        # outStatistics attributes keep the PUBLISHED group-column names; the
        # count lands under its declared outStatisticFieldName "count".
        subject = fields.get(spec.subject_field)
        period = fields.get(spec.period_field)
        count = fields.get("count")
        series = fields.get(spec.discriminator_field) if spec.discriminator_field else None
    else:
        # socrata_aggregate rows carry the canonical $select aliases.
        subject = fields.get("subject")
        period = fields.get("period")
        count = fields.get("count")
        series = fields.get("discriminator")
    subject_text = str(subject or "").strip()
    if not subject_text:
        raise CoordinateRejected(
            "missing", "aggregate row carries no subject key (group column empty)"
        )
    period_text = str(period or "").strip()
    if not period_text:
        raise CoordinateRejected(
            "missing", "aggregate row carries no period label (group column empty)"
        )
    try:
        count_int = int(float(str(count)))
    except (TypeError, ValueError):
        raise CoordinateRejected(
            "malformed", f"aggregate count {count!r} is not a number"
        ) from None
    series_text = str(series).strip() if series is not None else ""
    technology = assert_target_technology(target)
    record_kind = declared_record_kind(target)
    target_id = str(target.get("id") or "unknown_target")
    state = str(target.get("state") or "")
    agency = str(target.get("agency") or "")
    license_spdx = str(target.get("license_spdx") or "")
    subject_id = f"traffic_camera:{source_id}:{target_id}:{subject_text}"
    evidence = {
        "source_url": str(raw["source_uri"]),
        "extraction_method": _EXTRACTION_METHODS.get(kind, "arcgis_feature_json"),
        "locator": Locator.row(int(raw["feature_index"])).to_row(),
    }

    def _claim(
        predicate: str,
        value: Any,
        raw_value: str,
        candidate: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        row: dict[str, Any] = {
            "record_kind": "claim",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed(predicate),
            "raw_value": raw_value,
            "value": value,
            "evidence_genre": "camera_registry",
            "evidence": dict(evidence),
        }
        if candidate is not None:
            row["candidate_identifier"] = dict(candidate)
        return _stamp(row, source_id=source_id, license_spdx=license_spdx)

    rows: list[dict[str, Any]] = [
        _stamp(
            {
                "record_kind": record_kind,
                "subject_id": subject_id,
                "predicate_id": assert_predicate_allowed("traffic_camera"),
                "external_id": subject_text,
                "raw_value": subject_text,
                "state": state,
                "agency": agency,
                "target_id": target_id,
                "technology": technology,
                "aggregate_measure": spec.measure,
                "excluded_fields": list(raw.get("excluded_fields") or ()),
                "evidence_genre": "camera_registry",
                "evidence": evidence,
            },
            source_id=source_id,
            license_spdx=license_spdx,
        ),
        _claim(
            "camera_external_ref",
            subject_text,
            subject_text,
            candidate={"scheme": "dot511.camera_ref", "value": subject_text},
        ),
        _claim("external_id", subject_text, subject_text),
        _claim("technology", technology, technology),
        _claim(
            "camera_jurisdiction",
            state,
            state,
            candidate={
                "scheme": str(target.get("jurisdiction_scheme") or "us.state_abbr"),
                "value": state,
            },
        ),
        _claim("camera_registry_publisher", agency, agency),
    ]
    operator = str(target.get("operator") or "").strip()
    if operator:
        op = _claim("camera_operator", operator, operator)
        jurisdiction_scheme = str(target.get("jurisdiction_scheme") or "us.state_abbr")
        if state and jurisdiction_scheme != "sig.unresolved":
            op["partner_jurisdiction"] = f"{jurisdiction_scheme}:{state}"
        rows.append(op)
    count_claim = _claim("enforcement_count", count_int, str(count_int))
    count_claim["period"] = period_text
    count_claim["measure"] = spec.measure
    if series_text:
        count_claim["series"] = series_text
    rows.append(count_claim)
    return rows


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
    "AggregateSpec",
    "AggregateSpecNotDeclared",
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
    "assert_target_aggregate",
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
    "socrata_area_geometry",
    "target_aggregate_violations",
    "target_geometry_violations",
    "target_status_violations",
    "target_technology_violations",
    "technology_slugs",
    "vocab",
    "vocab_version",
]
