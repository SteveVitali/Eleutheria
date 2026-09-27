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

from ._data import load_table
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


def _arcgis_pages(row: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Expand one ArcGIS layer row into its deterministic ``/query`` pages.

    ``page_size`` on the row is the reviewed per-layer page bound — pinned
    when the layer's own ``maxRecordCount`` is below the 1,000 default
    (P26.16: camreg_portland_or serves 200 rows/page, so a 1,000-row request
    returns ``exceededTransferLimit`` on every page).
    """
    layer_url = str(row["layer_url"]).rstrip("/")
    observed = int(row.get("observed_count") or 0)
    oid_field = str(row.get("object_id_field") or "OBJECTID")
    page_size = min(_ARCGIS_PAGE_SIZE, max(1, int(row.get("page_size") or _ARCGIS_PAGE_SIZE)))
    pages = max(1, -(-observed // page_size))
    out: list[dict[str, Any]] = []
    for page in range(pages):
        params = {
            **_ARCGIS_QUERY_PARAMS,
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
    out: list[dict[str, Any]] = []
    for page in range(pages):
        params = {
            "$select": "*,:id",
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
    expanders = {"arcgis_query": _arcgis_pages, "socrata_rows": _socrata_pages}
    out: list[dict[str, Any]] = []
    for row in target_table().get("targets", []):
        if str(row.get("source_id")) != source_id:
            continue
        kind = str(row.get("kind") or "arcgis_query")
        expand = expanders.get(kind)
        if expand is None:
            raise ValueError(
                f"registry target {row.get('id')!r} declares unknown kind {kind!r} "
                f"(known: {sorted(expanders)}) — the connector never fetches an "
                "unrecognised platform."
            )
        for page in expand(row):
            out.append(
                {
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
                }
            )
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
    agency: str
    latitude: float
    longitude: float
    coordinate_source: str
    geo_tier: int
    sensitivity_class: str
    license_spdx: str
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

    def __post_init__(self) -> None:
        if not str(self.camera_ref).strip():
            raise ValueError("a CameraRegistryEntry requires a camera_ref (the registry key)")

    @property
    def subject_id(self) -> str:
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

        One ``traffic_camera`` entity row (carrying the whole predicate surface
        plus the excluded-field NAMES — never their values) plus one claim row
        per set predicate. The coordinate claims carry the published
        (tier-applied) coordinate and the sensitivity facts that produced it;
        the state is a ``us.state_abbr`` jurisdiction candidate and the camera
        ref a ``dot511.camera_ref`` candidate identifier — never resolutions
        (SIG-INGEST-034).
        """
        ev = self.evidence(source_url, retrieved_date, feature_index)
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "traffic_camera",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_predicate_allowed("traffic_camera"),
                    "external_id": self.camera_ref,
                    "raw_value": self.camera_ref,
                    "state": self.state,
                    "agency": self.agency,
                    "target_id": self.target_id,
                    "latitude": self.latitude,
                    "longitude": self.longitude,
                    "coordinate_source": self.coordinate_source,
                    "geo_tier": self.geo_tier,
                    "sensitivity_class": self.sensitivity_class,
                    "excluded_fields": list(self.excluded_fields),
                    "evidence_genre": "camera_registry",
                    "evidence": ev,
                },
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
        rows.append(
            self._claim(
                "camera_jurisdiction",
                self.state,
                self.state,
                ev,
                candidate={"scheme": self.jurisdiction_scheme, "value": self.state},
            )
        )
        rows.append(self._claim("camera_operator", self.agency, self.agency, ev))
        rows.append(self._claim("camera_latitude", self.latitude, str(self.latitude), ev))
        rows.append(self._claim("camera_longitude", self.longitude, str(self.longitude), ev))
        rows.append(
            self._claim(
                "camera_coordinate_source", self.coordinate_source, self.coordinate_source, ev
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
        return rows


# --- the connector ------------------------------------------------------------


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
    # link() is inherited (identity): SIG-INGEST-034 — candidate identifiers only.

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
    ref_pair = _first_field(fields, vocab()["id_fields"])
    if ref_pair is None:
        raise CoordinateRejected(
            "missing", "no camera identity field matched the id_fields aliases"
        )
    lat, lon, coord_source = extract_coordinate(fields, raw.get("geometry"))
    sensitivity_class = str(target.get("sensitivity_class") or vocab()["default_sensitivity_class"])
    plat, plon, tier = publishable_coordinate(lat, lon, sensitivity_class)

    def _s(aliases_key: str) -> str | None:
        pair = _first_field(fields, vocab()[aliases_key])
        if pair is None:
            return None
        text = str(pair[1]).strip()
        return text or None

    return CameraRegistryEntry(
        camera_ref=str(ref_pair[1]),
        source_id=source_id,
        target_id=str(target.get("id") or "unknown_target"),
        state=str(target.get("state") or ""),
        agency=str(target.get("agency") or ""),
        latitude=plat,
        longitude=plon,
        coordinate_source=coord_source,
        geo_tier=tier,
        sensitivity_class=sensitivity_class,
        license_spdx=str(target.get("license_spdx") or ""),
        name=_s("name_fields"),
        roadway=_s("roadway_fields"),
        county=_s("county_fields"),
        status=_s("status_fields"),
        direction=_s("direction_fields"),
        excluded_fields=tuple(raw.get("excluded_fields") or ()),
        jurisdiction_scheme=str(target.get("jurisdiction_scheme") or "us.state_abbr"),
        extraction_method=_EXTRACTION_METHODS.get(
            str(target.get("kind") or "arcgis_query"), "arcgis_feature_json"
        ),
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
    stamped_kinds = {"traffic_camera", "claim"}
    out: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("record_kind") in stamped_kinds:
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
            elif not all(isinstance(geometry.get(k), (int, float)) for k in ("x", "y")):
                findings.append(f"features[{i}] geometry lacks numeric x/y")
    return findings


__all__ = [
    "CameraRegistryEntry",
    "CoordinateRejected",
    "Dot511Connector",
    "PredicateNotAllowed",
    "assert_predicate_allowed",
    "canary_findings",
    "enumerated_outcomes",
    "extract_coordinate",
    "is_media_field",
    "load_claims_for_l1",
    "partition_fields",
    "predicate_allowlist",
    "publishable_coordinate",
    "registry_targets",
    "vocab",
    "vocab_version",
]
