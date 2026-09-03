# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `osm` connector — physical assets from OpenStreetMap (§23.2, P04.2).

The first real source adapter on the P04.1 eight-stage framework
(:mod:`connectors.stages`). It ingests ``man_made=surveillance`` elements —
**nodes, ways and relations** — from OpenStreetMap, consuming the full §23.2
surveillance-tag vocabulary, and lands them in the physically separate
**ODbL-licensed** asset layer under the REFERENCE custody posture (§42.3, ADR-011).

This module owns four things the spec assigns to P04.2 (§23.2 Notes):

* **The SIG-INGEST-045 versioned tag→claim vocabulary** (data, in
  ``data/osm_tag_vocab.toml``): the allowlisted keys, the ``;``-split
  multi-value rule, the ``surveillance:type`` → device-kind map, and the
  ``camera:type`` → mobility map. A surveillance-bearing key *outside* the
  allowlist is recorded as an unmapped value **and** a research task (REQ-R1-02),
  never silently dropped.
* **The ``(osm_type, osm_id, version)`` reference key** (SIG-INGEST-045b/045f): a
  bare element id is not a stable reference across time — the same id denoted a
  freeway feature for fifteen years and a surveillance device thereafter — and
  node/way/relation id-spaces overlap, so the type is part of the key.
* **``first_observed`` walked from element history** (SIG-INGEST-045a/045c): the
  version where surveillance tags *first appeared*, never the element's creation
  timestamp — a repurposed 2009 road node dates from its retag, not its import.
* **Mapper-identity discard** (SIG-INGEST-045e, a Part VIII safety invariant):
  OSM ``user``/``uid`` are dropped at ingest and never stored or exposed;
  ``changeset`` is retained as the provenance anchor.

Deletion is detected by **snapshot diffing** (:func:`snapshot_diff`,
SIG-INGEST-045g): Overpass never reports deletions, so a device removed from OSM
is only seen by diffing successive snapshots — and a *deletion from OSM* (a
mapping event) is kept strictly distinct from a *removal from the street* (a
world event), which the connector never infers from an OSM deletion.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from ._data import load_table
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

#: The registry source this connector runs against (§22.6; REFERENCE + ODbL-1.0).
OSM_SOURCE_ID = "osm_overpass"
#: The registry source for per-element history walks (SIG-INGEST-045c, Q19).
OSM_HISTORY_SOURCE_ID = "osm_element_history"

#: The export compartment OSM-derived assets land in — physically separate from
#: the CC-BY-4.0 SIG graph (§42.3, ADR-011, SIG-LIC-006).
ODBL_LICENSE = "ODbL-1.0"
ODBL_COMPARTMENT = "osm_physical"

#: OSM's three element types; their id-spaces are independent and overlap, which
#: is why the type is part of every key (SIG-INGEST-045f).
ELEMENT_TYPES: frozenset[str] = frozenset({"node", "way", "relation"})

#: Predicate for the "this OSM element was deleted from OSM" mapping event — kept
#: strictly distinct from a street-removal world event (SIG-INGEST-045g).
DELETED_FROM_OSM_PREDICATE = "osm_element_deleted"
#: The predicate a *world* removal would use. The OSM connector NEVER emits it
#: from a snapshot diff; it exists only to name the distinction the spec draws.
REMOVED_FROM_STREET_PREDICATE = "physical_removed_from_street"

#: Research-task type for a surveillance-bearing tag outside the allowlist
#: (REQ-R1-02, SIG-INGEST-045) — mirrors evidence.disappearance's task shape.
UNMAPPED_TAG_TASK_TYPE = "unmapped_surveillance_tag"
_DETECTOR_VERSION = "connectors.osm/1"


# --- the versioned vocabulary (data, not code — SIG-INGEST-045, §20) ----------


@cache
def vocab() -> dict[str, Any]:
    """The versioned SIG-INGEST-045 tag→claim vocabulary (``data/osm_tag_vocab.toml``)."""
    return load_table("osm_tag_vocab")


def vocab_version() -> str:
    """The vocabulary version stamped onto every run (§20; versioned migrations)."""
    return str(vocab()["version"])


def _allowlisted_keys() -> Mapping[str, Any]:
    return vocab()["keys"]


def is_surveillance_bearing_key(key: str) -> bool:
    """Whether a tag key carries surveillance meaning (§23.2).

    Used to decide what an *unallowlisted* key is: a key that looks like
    surveillance metadata but is not in the vocabulary is recorded as an unmapped
    value + a research task (REQ-R1-02), rather than ignored.
    """
    v = vocab()
    if key in _allowlisted_keys():
        return True
    if key == v["selection_key"]:
        return False  # the selection predicate itself is not a claim-bearing key
    return key.startswith("surveillance") or key.startswith("camera:")


def is_surveillance_element(tags: Mapping[str, str]) -> bool:
    """Whether an element is an in-scope surveillance asset (the §23.2 predicate)."""
    v = vocab()
    return tags.get(v["selection_key"]) == v["selection_value"]


# --- pure tag handling --------------------------------------------------------


def split_multivalue(value: str) -> tuple[str, ...]:
    """Split a ``;`` multi-value into an **unordered set**, rendered sorted (§23.2).

    OSM packs multiple values into one string with ``;`` (e.g.
    ``surveillance:type=ALPR;camera``). The spec requires these be treated as an
    unordered set; we dedupe, strip, drop empties, and sort so the result is
    order-independent and content-addresses stably (SIG-INGEST-003).
    """
    parts = {p.strip() for p in value.split(";")}
    return tuple(sorted(p for p in parts if p))


def strip_mapper_identity(element: Mapping[str, Any]) -> dict[str, Any]:
    """Drop OSM ``user``/``uid`` at ingest; retain everything else (SIG-INGEST-045e).

    A queryable table of which mapper recorded which police camera is a targeting
    surface and MUST NOT be built. ``changeset`` is deliberately kept — it is the
    provenance anchor and is not person-identifying on its face.
    """
    discard = set(vocab()["mapper_identity_keys"])
    return {k: v for k, v in element.items() if k not in discard}


def _normalize_lookup(table_name: str, raw: str) -> str | None:
    return vocab()[table_name].get(raw.strip().lower())


def map_surveillance_type(raw: str) -> str | None:
    """Map one ``surveillance:type`` value to a device kind, or ``None`` if unmapped."""
    return _normalize_lookup("surveillance_type", raw)


def map_mobility(camera_type: str) -> str:
    """Infer mobility from ``camera:type`` (§23.2); unknown values stay ``unknown``."""
    return _normalize_lookup("mobility", camera_type) or "unknown"


# --- keying (SIG-INGEST-045b / 045f) ------------------------------------------


@dataclass(frozen=True, order=True)
class ElementRef:
    """The stable, id-space-scoped reference to an OSM element (SIG-INGEST-045f).

    ``(osm_type, osm_id)`` — never ``osm_id`` alone, because node, way and
    relation id-spaces are independent and overlap.
    """

    osm_type: str
    osm_id: int

    def __post_init__(self) -> None:
        if self.osm_type not in ELEMENT_TYPES:
            raise ValueError(f"osm_type {self.osm_type!r} not one of {sorted(ELEMENT_TYPES)}")

    @property
    def subject_id(self) -> str:
        """The claim subject id for this element (id-space scoped)."""
        return f"osm:{self.osm_type}/{self.osm_id}"


@dataclass(frozen=True, order=True)
class ElementVersionRef:
    """The reference that is unambiguous *across time* (SIG-INGEST-045b).

    ``(osm_type, osm_id, version)``: the same id denoted a freeway feature for
    fifteen years and a surveillance device thereafter, so only the version pins
    which meaning is referenced — and preserving it is what makes a later OSM edit
    detectable (REQ-R1-01, §23.2).
    """

    osm_type: str
    osm_id: int
    version: int

    @property
    def ref(self) -> ElementRef:
        return ElementRef(self.osm_type, self.osm_id)


def element_version_ref(element: Mapping[str, Any]) -> ElementVersionRef:
    """Build the ``(osm_type, osm_id, version)`` reference from a raw element."""
    return ElementVersionRef(
        osm_type=str(element["type"]),
        osm_id=int(element["id"]),
        version=int(element["version"]),
    )


# --- first_observed from element history (SIG-INGEST-045a / 045c) -------------


@dataclass(frozen=True)
class HistoryVersion:
    """One version of an element from ``/api/0.6/<type>/<id>/history.json``."""

    version: int
    timestamp: datetime
    tags: Mapping[str, str]


def _parse_timestamp(value: str) -> datetime:
    # OSM timestamps are ISO-8601 with a trailing 'Z'.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def history_versions(history_doc: Mapping[str, Any]) -> list[HistoryVersion]:
    """Extract the per-version tag sets from an element-history document."""
    out: list[HistoryVersion] = []
    for el in history_doc.get("elements", []):
        out.append(
            HistoryVersion(
                version=int(el["version"]),
                timestamp=_parse_timestamp(str(el["timestamp"])),
                tags=dict(el.get("tags", {})),
            )
        )
    return sorted(out, key=lambda v: v.version)


def first_observed_from_history(versions: Iterable[HistoryVersion]) -> HistoryVersion | None:
    """The earliest version at which surveillance tags **first appeared** (SIG-INGEST-045a).

    Walks the history in version order and returns the first version whose tags
    carry the surveillance selection predicate. This is deliberately NOT the
    element's creation timestamp: a repurposed 2009 road node dates from its
    2024 retag, not its freeway import — reading the creation date would date the
    device to before its vendor existed and systematically corrupt the temporal
    layer (SC-17.3). Returns ``None`` if no version ever carried surveillance tags.
    """
    for v in sorted(versions, key=lambda x: x.version):
        if is_surveillance_element(v.tags):
            return v
    return None


# --- deletion via snapshot diffing (SIG-INGEST-045g) --------------------------


@dataclass(frozen=True)
class SnapshotDiff:
    """The delta between two OSM snapshots of the surveillance layer (SIG-INGEST-045g).

    ``deleted_from_osm`` is a set of **mapping events**, NOT street removals:
    Overpass never reports deletions, so a purely incremental connector would
    never see a device disappear; but an element vanishing from OSM means a mapper
    removed the *record*, which is a different claim (different predicate) from the
    device being removed from the street. Conflating them would let a mapper's
    cleanup read as a decommissioning, so the connector keeps them distinct and
    never emits a world-removal from a diff.
    """

    added: frozenset[ElementRef] = frozenset()
    persisted: frozenset[ElementRef] = frozenset()
    deleted_from_osm: frozenset[ElementRef] = frozenset()

    def deletion_events(self, observed_at: datetime) -> list[dict[str, Any]]:
        """One mapping-event row per element that vanished from OSM (never a world event)."""
        return [
            {
                "subject_id": ref.subject_id,
                "osm_type": ref.osm_type,
                "osm_id": ref.osm_id,
                "predicate_id": DELETED_FROM_OSM_PREDICATE,
                "event_class": "mapping_event",
                "raw_value": "deleted_from_osm",
                "observed_at": observed_at,
                "source_id": OSM_SOURCE_ID,
                "license": ODBL_LICENSE,
                "compartment": ODBL_COMPARTMENT,
            }
            for ref in sorted(self.deleted_from_osm)
        ]


def snapshot_diff(previous: Iterable[ElementRef], current: Iterable[ElementRef]) -> SnapshotDiff:
    """Diff two surveillance-layer snapshots by element reference (SIG-INGEST-045g)."""
    prev = set(previous)
    cur = set(current)
    return SnapshotDiff(
        added=frozenset(cur - prev),
        persisted=frozenset(cur & prev),
        deleted_from_osm=frozenset(prev - cur),
    )


# --- Overpass etiquette (SIG-INGEST-045d / 045h / 045i / 045j) ----------------

#: Published Overpass quotas that MUST be respected (SIG-INGEST-045h).
OVERPASS_MAX_REQUESTS_PER_DAY = 10_000
OVERPASS_MAX_BYTES_PER_DAY = 1_000_000_000  # 1 GB/day
OVERPASS_DEFAULT_TIMEOUT = 180
OVERPASS_DEFAULT_MAXSIZE = 512 * 1024 * 1024  # 512 MiB


class BulkStitchingForbidden(Exception):
    """Raised on an attempt to stitch bounding boxes to scrape the whole world (SIG-INGEST-045i)."""


def build_overpass_query(
    *,
    bbox: tuple[float, float, float, float] | None = None,
    timeout: int = OVERPASS_DEFAULT_TIMEOUT,
    maxsize: int = OVERPASS_DEFAULT_MAXSIZE,
) -> str:
    """Build an Overpass QL query for the surveillance layer, respecting etiquette.

    * Selects ``man_made=surveillance`` across node/way/relation (§23.2).
    * Carries ``[timeout:…][maxsize:…]`` (SIG-INGEST-045h).
    * **Never puts a space in a tag-value filter** — a space trips the public
      instance's request filter (SIG-INGEST-045d); any further value filtering is
      done client-side in :meth:`OSMConnector.normalize`.
    * Requires a bbox: an unbounded worldwide query is bulk-stitching and both
      prohibited and doomed in practice (SIG-INGEST-045i) — use a PBF dump for
      bulk (:func:`acquisition_mode`).
    """
    if bbox is None:
        raise BulkStitchingForbidden(
            "an unbounded Overpass query stitches the whole world (SIG-INGEST-045i); "
            "use a PBF dump for bulk and tiled Overpass for increments."
        )
    s, w, n, e = bbox
    area = f"({s},{w},{n},{e})"
    v = vocab()
    sel = f'["{v["selection_key"]}"="{v["selection_value"]}"]'  # no spaces (SIG-INGEST-045d)
    body = "".join(f"{kind}{sel}{area};" for kind in ("node", "way", "relation"))
    return f"[out:json][timeout:{timeout}][maxsize:{maxsize}];({body});out tags center meta;"


def acquisition_mode(*, bulk: bool) -> str:
    """PBF + tag filtering for bulk; tiled Overpass for increments (SIG-INGEST-045i)."""
    return "pbf_tag_filter" if bulk else "overpass_tiled"


def overpass_status_action(status: int) -> str:
    """Map an Overpass HTTP status onto the etiquette-correct action (SIG-INGEST-045h).

    ``429`` is slot exhaustion → **back off in time** (poll ``/api/status`` rather
    than model quota locally, because one DNS name fronts independently
    rate-limited servers). ``504`` means the query was too large → **shrink it**;
    retrying a 504 unchanged is useless and rude. ``200`` is fine.
    """
    if status == 429:
        return "back_off"
    if status == 504:
        return "shrink"
    if 200 <= status < 300:
        return "ok"
    return "record_disappearance"


def assert_own_or_public_instance(host: str, permitted_self_hosted: Iterable[str] = ()) -> None:
    """Refuse another project's self-hosted Overpass without permission (SIG-INGEST-045j)."""
    public = {"overpass-api.de", "overpass.kumi.systems", "lz4.overpass-api.de"}
    allowed = public | set(permitted_self_hosted)
    if host not in allowed:
        raise PermissionError(
            f"{host!r} is not a public Overpass instance and SIG has no explicit "
            "permission to use it (SIG-INGEST-045j)."
        )


# --- unmapped surveillance tags → research tasks (REQ-R1-02) ------------------


def unmapped_tag_task(subject_id: str, key: str, raw_value: str) -> dict[str, Any]:
    """A research task for a surveillance-bearing key outside the allowlist (SIG-INGEST-045)."""
    return {
        "task_type": UNMAPPED_TAG_TASK_TYPE,
        "subject_id": subject_id,
        "osm_key": key,
        "raw_value": raw_value,
        "priority": 0.5,
        "closing_condition": (
            "the key is added to the versioned osm_tag_vocab (a §20 migration) "
            "OR confirmed out of scope and annotated"
        ),
        "detector_version": _DETECTOR_VERSION,
        "status": "generated",
    }


# --- geometry descriptor ------------------------------------------------------


def geometry_descriptor(element: Mapping[str, Any]) -> dict[str, Any] | None:
    """A lightweight geometry descriptor (§23.2; SIG-GEO-003 — never assume a point).

    Nodes carry ``lat``/``lon``; ways/relations carry a ``center`` (from
    ``out center``) or ``bounds``. Full PostGIS geometry lives in the DB layer;
    the connector only records what the capture provides, preserving the element
    type so a non-point element is never coerced to a point.
    """
    et = element.get("type")
    if et == "node" and "lat" in element and "lon" in element:
        return {"kind": "point", "lat": float(element["lat"]), "lon": float(element["lon"])}
    center = element.get("center")
    if isinstance(center, Mapping) and "lat" in center and "lon" in center:
        return {"kind": "center", "lat": float(center["lat"]), "lon": float(center["lon"])}
    bounds = element.get("bounds")
    if isinstance(bounds, Mapping):
        return {"kind": "bounds", "bounds": dict(bounds)}
    return None


# --- the ODbL physical-asset row (the separate table, §42.3) ------------------


def physical_asset_rows(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Project normalized claims onto ODbL ``physical_asset``-shaped rows (§42.3).

    This is the physically separate, ODbL-licensed asset layer the OSM output
    lands in (SIG-LIC-006, ADR-011): one row per ``(osm_type, osm_id)`` element,
    carrying the version (so a later edit is detectable), geometry descriptor,
    inferred mobility, and the history-walked ``first_observed`` — and stamped
    ``ODbL-1.0`` / ``osm_physical`` so the export gate keeps it out of the CC-BY
    graph. Rows are keyed and sorted by element ref for determinism.
    """
    by_ref: dict[ElementRef, dict[str, Any]] = {}
    for claim in claims:
        if claim.get("record_kind") != "asset":
            continue
        ref = ElementRef(str(claim["osm_type"]), int(claim["osm_id"]))
        by_ref[ref] = {
            "osm_element_type": ref.osm_type,
            "osm_element_id": ref.osm_id,
            "osm_version": int(claim["osm_version"]),
            "asset_technology": claim.get("asset_technology"),
            "mobility": claim.get("mobility", "unknown"),
            "geometry": claim.get("geometry"),
            "first_observed": claim.get("first_observed"),
            "last_observed": claim.get("last_observed"),
            "changeset": claim.get("changeset"),
            "source_id": OSM_SOURCE_ID,
            "license": ODBL_LICENSE,
            "compartment": ODBL_COMPARTMENT,
        }
    return [by_ref[ref] for ref in sorted(by_ref)]


# --- the connector ------------------------------------------------------------


@register
class OSMConnector(Connector):
    """The `osm` connector: surveillance physical assets from OpenStreetMap (§23.2).

    Runs on the P04.1 eight-stage framework. ``discover``/``fetch`` acquire an
    Overpass snapshot (or a per-element history document) through the shared
    politeness layer — which stamps the descriptive, contact-carrying UA the
    public instance requires (SIG-INGEST-045d); ``parse``/``extract``/``normalize``
    are pure functions of the capture that apply the versioned vocabulary, split
    multi-values, discard mapper identity, and key on ``(osm_type, osm_id,
    version)``. Output is stamped into the ODbL compartment.
    """

    name = "osm"
    version = "1.0.0"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets (identifiers, not content).

        Targets come from ``ctx.parameters['targets']`` — each an Overpass tile
        query (``kind='overpass'``) or a per-element history document
        (``kind='history'``, for elements under active reconciliation,
        SIG-INGEST-045c). The connector never enumerates the whole world itself
        (SIG-INGEST-045i).
        """
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only.

        Connectors hold no HTTP client of their own; the shared fetcher carries
        the descriptive UA (SIG-INGEST-045d) and enforces robots + rate limits.
        """
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
        """Structure the captured OSM JSON (Overpass snapshot or element history)."""
        return json.loads(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:
        """Raw records with locators, preserving raw values and discarding mapper identity.

        Handles both document shapes: an element-history document (all elements
        share one ``(type, id)`` with distinct versions) yields a ``first_observed``
        record (SIG-INGEST-045a); an Overpass snapshot yields one raw asset record
        per surveillance element. OSM ``user``/``uid`` are dropped here, at ingest
        (SIG-INGEST-045e); ``changeset`` is kept.
        """
        elements = list(parsed.get("elements", []))
        if _is_history_document(elements):
            return _extract_history(elements)
        out: list[Mapping[str, Any]] = []
        for el in elements:
            tags = el.get("tags", {})
            if not is_surveillance_element(tags):
                continue
            clean = strip_mapper_identity(el)
            out.append(
                {
                    "record_kind": "asset",
                    "osm_type": str(clean["type"]),
                    "osm_id": int(clean["id"]),
                    "osm_version": int(clean["version"]),
                    "changeset": clean.get("changeset"),
                    "raw_tags": dict(tags),
                    "geometry": geometry_descriptor(clean),
                }
            )
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed values beside preserved raw values, per the versioned vocabulary (P2).

        Splits ``;`` multi-values into unordered sets, maps ``surveillance:type``
        to a device kind and ``camera:type`` to mobility, cross-normalizes the
        four surveillance keys, keys every output on ``(osm_type, osm_id,
        version)``, and records any surveillance-bearing key outside the allowlist
        as an unmapped value + a research task (REQ-R1-02). Every output row is
        stamped into the ODbL compartment (§42.3).
        """
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            if raw.get("record_kind") == "first_observed":
                out.append(self._normalize_first_observed(raw))
                continue
            out.extend(self._normalize_asset(raw))
        return out

    # -- normalization helpers --
    def _normalize_first_observed(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        return _stamp(
            {
                "record_kind": "claim",
                "subject_id": raw["subject_id"],
                "osm_type": raw["osm_type"],
                "osm_id": raw["osm_id"],
                "osm_version": raw["osm_version"],
                "predicate_id": "first_observed",
                "raw_value": raw["raw_value"],
                "value_time": raw["first_observed"],
            }
        )

    def _normalize_asset(self, raw: Mapping[str, Any]) -> list[dict[str, Any]]:
        ref = ElementRef(str(raw["osm_type"]), int(raw["osm_id"]))
        tags: Mapping[str, str] = raw["raw_tags"]
        allow = _allowlisted_keys()
        multivalue = set(vocab()["multivalue_keys"])
        rows: list[dict[str, Any]] = []
        asset_technology: str | None = None
        mobility = "unknown"

        for key, value in sorted(tags.items()):
            if key == vocab()["selection_key"]:
                continue
            if key not in allow:
                if is_surveillance_bearing_key(key):
                    rows.append(self._unmapped_row(ref, raw, key, value))
                continue
            values = split_multivalue(value) if key in multivalue else (value,)
            if key == "surveillance:type":
                asset_technology = self._first_mapped_type(values) or asset_technology
            if key == "camera:type":
                mobility = self._first_mobility(values)
            rows.append(self._claim_row(ref, raw, key, value, values))

        # The asset row itself — the ODbL physical_asset projection input. Carries
        # the version (edit detection), geometry, inferred mobility, and a
        # first_observed placeholder (None => resolved later from history, NEVER the
        # creation timestamp — SIG-INGEST-045a).
        rows.append(
            _stamp(
                {
                    "record_kind": "asset",
                    "subject_id": ref.subject_id,
                    "osm_type": ref.osm_type,
                    "osm_id": ref.osm_id,
                    "osm_version": int(raw["osm_version"]),
                    "changeset": raw.get("changeset"),
                    "asset_technology": asset_technology,
                    "mobility": mobility,
                    "geometry": raw.get("geometry"),
                    "first_observed": None,
                    "last_observed": None,
                }
            )
        )
        return rows

    def _claim_row(
        self,
        ref: ElementRef,
        raw: Mapping[str, Any],
        key: str,
        raw_value: str,
        values: tuple[str, ...],
    ) -> dict[str, Any]:
        predicate = _allowlisted_keys()[key]["predicate"]
        row: dict[str, Any] = {
            "record_kind": "claim",
            "subject_id": ref.subject_id,
            "osm_type": ref.osm_type,
            "osm_id": ref.osm_id,
            "osm_version": int(raw["osm_version"]),
            "predicate_id": predicate,
            "osm_key": key,
            "raw_value": raw_value,  # P2: the raw value is always preserved
        }
        if key not in vocab()["raw_value_only_keys"]:
            row["value_set"] = list(values)
            if key == "surveillance:type":
                mapped = [map_surveillance_type(x) for x in values]
                row["value_set_normalized"] = [m for m in mapped if m is not None]
                unmapped = [x for x, m in zip(values, mapped, strict=True) if m is None]
                if unmapped:
                    row["unmapped_values"] = unmapped
                    row["research_task"] = unmapped_tag_task(
                        ref.subject_id, key, ";".join(unmapped)
                    )
        return _stamp(row)

    def _unmapped_row(
        self, ref: ElementRef, raw: Mapping[str, Any], key: str, value: str
    ) -> dict[str, Any]:
        return _stamp(
            {
                "record_kind": "claim",
                "subject_id": ref.subject_id,
                "osm_type": ref.osm_type,
                "osm_id": ref.osm_id,
                "osm_version": int(raw["osm_version"]),
                "predicate_id": "unmapped_surveillance_tag",
                "osm_key": key,
                "raw_value": value,
                "research_task": unmapped_tag_task(ref.subject_id, key, value),
            }
        )

    @staticmethod
    def _first_mapped_type(values: tuple[str, ...]) -> str | None:
        for v in values:
            mapped = map_surveillance_type(v)
            if mapped is not None:
                return mapped
        return None

    @staticmethod
    def _first_mobility(values: tuple[str, ...]) -> str:
        for v in values:
            m = map_mobility(v)
            if m != "unknown":
                return m
        return "unknown"

    def resolve_first_observed(self, versions: Iterable[HistoryVersion]) -> datetime | None:
        """The history-walked ``first_observed`` for an element (SIG-INGEST-045a)."""
        hv = first_observed_from_history(versions)
        return hv.timestamp if hv is not None else None

    # -- load --
    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the ODbL L1 claim rows; the driver asserts them (live only).

        Adds the generated ``claim_id`` + transaction time (the two columns the
        reproducibility fingerprint excludes, SIG-INGEST-003). Every row is already
        stamped ``ODbL-1.0`` / ``osm_physical`` in :meth:`normalize`, so the export
        gate keeps the OSM layer out of the CC-BY graph (§42.3).
        """
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


def _stamp(row: dict[str, Any]) -> dict[str, Any]:
    """Stamp a row into the ODbL compartment (§42.3, SIG-LIC-006)."""
    row.setdefault("source_id", OSM_SOURCE_ID)
    row["license"] = ODBL_LICENSE
    row["compartment"] = ODBL_COMPARTMENT
    return row


def _is_history_document(elements: list[Mapping[str, Any]]) -> bool:
    """Whether a parsed document is a single element's version history.

    A history document is every version of ONE element, so all elements share the
    same ``(type, id)`` and carry distinct versions; an Overpass snapshot mixes
    many elements. Requires at least two versions to be unambiguous.
    """
    if len(elements) < 2:
        return False
    refs = {(str(e.get("type")), e.get("id")) for e in elements}
    versions = {e.get("version") for e in elements}
    return len(refs) == 1 and len(versions) == len(elements)


def _extract_history(elements: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    hv = first_observed_from_history(
        [
            HistoryVersion(
                version=int(e["version"]),
                timestamp=_parse_timestamp(str(e["timestamp"])),
                tags=dict(e.get("tags", {})),
            )
            for e in elements
        ]
    )
    if hv is None:
        return []
    first = elements[0]
    ref = ElementRef(str(first["type"]), int(first["id"]))
    return [
        {
            "record_kind": "first_observed",
            "subject_id": ref.subject_id,
            "osm_type": ref.osm_type,
            "osm_id": ref.osm_id,
            "osm_version": hv.version,
            "first_observed": hv.timestamp,
            "raw_value": hv.timestamp.isoformat(),
        }
    ]


def canary_findings(parsed: Mapping[str, Any]) -> list[str]:
    """Structural-drift findings for an OSM response (SIG-PARSE-008 canary).

    Committed fixtures (SIG-PARSE-007) pin known inputs and keep passing forever;
    they cannot catch an upstream that quietly changes shape. The canary is the
    complement: it runs against a *live* response on a cadence and alerts when the
    structure the parser depends on drifts. This function is that check's
    deterministic core — the schema assertions — so the nightly job is a thin
    fetch-and-call wrapper. An **empty** list means no drift; each string names a
    structural expectation the response violated.

    Checks: a top-level ``elements`` list is present; every element carries
    ``type``/``id``/``version`` (the reference key, SIG-INGEST-045b); every
    surveillance element carries a ``tags`` map. It deliberately does NOT assert
    tag *values* — new device kinds are handled as unmapped values + research
    tasks (REQ-R1-02), not treated as drift.
    """
    findings: list[str] = []
    elements = parsed.get("elements")
    if not isinstance(elements, list):
        return ["missing top-level 'elements' list"]
    for i, el in enumerate(elements):
        if not isinstance(el, Mapping):
            findings.append(f"element[{i}] is not an object")
            continue
        for key in ("type", "id", "version"):
            if key not in el:
                findings.append(f"element[{i}] ({el.get('type')}/{el.get('id')}) missing {key!r}")
        if el.get("type") not in ELEMENT_TYPES:
            findings.append(f"element[{i}] has unknown type {el.get('type')!r}")
        tags = el.get("tags", {})
        if is_surveillance_element(tags if isinstance(tags, Mapping) else {}) and not isinstance(
            tags, Mapping
        ):
            findings.append(f"element[{i}] surveillance element has non-map tags")
    return findings


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 claim needs.

    Mirrors the framework's load contract: ``claim_id`` and ``sys_period`` are the
    two non-deterministic columns the reproducibility fingerprint excludes
    (SIG-INGEST-003), so replay is byte-identical modulo exactly these.
    """
    out: list[dict[str, Any]] = []
    for claim in claims:
        out.append(
            {
                **claim,
                "claim_id": str(uuid4()),
                "sys_period": f"[{datetime.now(UTC).isoformat()},)",
            }
        )
    return out


__all__ = [
    "DELETED_FROM_OSM_PREDICATE",
    "ODBL_COMPARTMENT",
    "ODBL_LICENSE",
    "OSM_HISTORY_SOURCE_ID",
    "OSM_SOURCE_ID",
    "REMOVED_FROM_STREET_PREDICATE",
    "BulkStitchingForbidden",
    "ElementRef",
    "ElementVersionRef",
    "HistoryVersion",
    "OSMConnector",
    "SnapshotDiff",
    "acquisition_mode",
    "assert_own_or_public_instance",
    "build_overpass_query",
    "canary_findings",
    "element_version_ref",
    "first_observed_from_history",
    "geometry_descriptor",
    "history_versions",
    "is_surveillance_bearing_key",
    "is_surveillance_element",
    "load_claims_for_l1",
    "map_mobility",
    "map_surveillance_type",
    "overpass_status_action",
    "physical_asset_rows",
    "snapshot_diff",
    "split_multivalue",
    "strip_mapper_identity",
    "unmapped_tag_task",
    "vocab",
    "vocab_version",
]
