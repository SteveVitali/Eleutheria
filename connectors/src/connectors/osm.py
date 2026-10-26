# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `osm` connector — physical assets from OpenStreetMap (§23.2, P04.2).

The first real source adapter on the P04.1 eight-stage framework
(:mod:`connectors.stages`). It ingests ``man_made=surveillance`` elements —
**nodes, ways and relations** — from OpenStreetMap, consuming the full §23.2
surveillance-tag vocabulary, and lands them in the physically separate
**ODbL-licensed** asset layer under the REFERENCE custody posture (§42.3, ADR-011).

P37.1 (ACQ-17, I8 §4.3) widens the connector from the §23.2 tag layer into a
**camera-site origin**: every element carrying ``surveillance:type`` or
``highway=speed_camera`` — not only ``man_made=surveillance`` — emits the
camera-site predicate family (``camera_external_ref``/coordinates/
``camera_jurisdiction``/``camera_operator``/``technology``) onto its
``osm:<type>/<id>`` subject, so the element joins the camera-site ER pool.
The widened queries request ``out body center qt;`` — never ``out meta`` — so
OSM ``user``/``uid`` are never *requested*, the capture-side half of
SIG-INGEST-045e (F-406 / D-R11-OSMUID-1 / D-P34.49-2); edit detection moves
from ``osm_version`` onto the content-digest snapshot diff
(:func:`element_content_digest` / :func:`snapshot_content_diff`), with
``osm_element_history`` kept as the version-history channel. National and
global collection runs as two tiled passes (discovery ``out count;`` per
declared area, then ``out body center qt;`` per non-empty area, reconciled
against the discovery counts as ContentDrift — SIG-ENG-042). Elements whose
``source``/``survey`` provenance names Wi-Fi/BLE/RF detection keep only
3-decimal coarsened coordinates until the SIG-PUB-011–014 residential
screen lands.

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
  OSM ``user``/``uid`` are never requested (``out body``, P37.1), are refused
  at the capture writer if a nonconforming endpoint sends them anyway, and are
  dropped again at extract for the history channel — never stored or exposed;
  ``changeset`` is retained as the provenance anchor.

Deletion is detected by **snapshot diffing** (:func:`snapshot_diff`,
SIG-INGEST-045g): Overpass never reports deletions, so a device removed from OSM
is only seen by diffing successive snapshots — and a *deletion from OSM* (a
mapping event) is kept strictly distinct from a *removal from the street* (a
world event), which the connector never infers from an OSM deletion.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from urllib.parse import urlencode
from uuid import uuid4

from policy.parcel_screen import (
    ParcelScreenVerdict,
    ResidentialParcelSignal,
    declared_parcel_signal,
    screen_geometry_descriptor,
)
from policy.sensitivity import SensitivityClass, demote_for_residential_parcel, geo_tier_for
from resolution.partner_identity import natural_person_signal, partner_ref_rows

from ._data import load_table
from .stages import (
    CaptureRef,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    content_digest,
    register,
)

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


def is_camera_site_element(tags: Mapping[str, str]) -> bool:
    """Whether an element is a camera-site element (P37.1 / ACQ-17, I8 §4.3).

    The camera-site family is additive to ``man_made=surveillance``: an element
    carrying any ``camera_site.presence_keys`` key (``surveillance:type`` — the
    ~154k ALPR nodes ride it) or matching a ``value_keys`` pair
    (``highway=speed_camera``, AP-W-024) emits the camera-site predicate
    family. The selection is DATA (``osm_tag_vocab.toml``), never a literal.
    """
    cs = vocab()["camera_site"]
    for key in cs["presence_keys"]:
        if key in tags:
            return True
    for key, value in cs["value_keys"].items():
        if tags.get(key) == value:
            return True
    return False


def element_in_scope(tags: Mapping[str, str]) -> bool:
    """Whether an element is in the widened collection scope (P37.1)."""
    return is_surveillance_element(tags) or is_camera_site_element(tags)


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


@cache
def _rf_patterns() -> tuple[re.Pattern[str], ...]:
    return tuple(re.compile(str(p), re.IGNORECASE) for p in vocab()["rf_source"]["patterns"])


def rf_derived_source(tags: Mapping[str, str]) -> str | None:
    """The RF-detection provenance a provenance tag declares, else ``None``.

    P37.1 / ACQ-17: an element whose ``source``/``survey`` provenance names
    Wi-Fi wardriving, Bluetooth/BLE scanning, or generic RF detection keeps
    only coarsened coordinates until the SIG-PUB-011–014 residential screen
    lands — RF-derived positions were observed where a *signal* was heard, not
    where a device was surveyed. Returns the declaring tag's value (the
    evidence), never a guess.
    """
    table = vocab()["rf_source"]
    for key in table["keys"]:
        value = tags.get(key)
        if not value:
            continue
        text = str(value)
        if any(p.search(text) for p in _rf_patterns()):
            return text
    return None


def coarsened_geometry(geom: Mapping[str, Any] | None, decimals: int) -> dict[str, Any] | None:
    """Round a geometry descriptor's coordinates to ``decimals`` places.

    Covers point/center ``lat``/``lon`` and the four ``bounds`` edges — an
    RF-derived element may never emit a precise descriptor of any shape.
    """
    if geom is None:
        return None
    out = dict(geom)
    for key in ("lat", "lon"):
        if key in out:
            out[key] = round(float(out[key]), decimals)
    bounds = out.get("bounds")
    if isinstance(bounds, Mapping):
        out["bounds"] = {
            k: round(float(v), decimals) if isinstance(v, int | float) else v
            for k, v in bounds.items()
        }
    return out


def camera_site_technologies(tags: Mapping[str, str], mobility: str) -> tuple[str, ...]:
    """The P35.15b technology slugs a camera-site element declares (ACQ-17).

    ``highway=speed_camera`` declares the P36.3 ATE subtype ``ate-speed``;
    every ``surveillance:type`` value maps through the device kind + the
    element's inferred mobility onto ``ontology/vocab/technology.yaml`` slugs
    (``alpr-fixed``, ``alpr-mobile``, …). A kind whose mobility the table
    cannot specialise emits NOTHING — honest absence, never a guessed slug —
    and a retired slug is never emitted.
    """
    cs = vocab()["camera_site"]
    table = vocab()["camera_site_technology"]
    out: list[str] = []
    for key, value in cs["value_keys"].items():
        if key == "highway" and tags.get(key) == value:
            out.append(str(cs["speed_camera_technology"]))
    kinds_table = table["kinds"]
    for raw_value in split_multivalue(str(tags.get("surveillance:type") or "")):
        kind = map_surveillance_type(raw_value)
        if kind is None:
            continue  # unmapped value — the research-task machinery owns it
        spec = kinds_table.get(kind)
        if spec is None:
            continue  # a kind with no declared slug mapping emits no claim
        slug: str | None = None
        mobility_map = spec.get("mobility") or {}
        if mobility in mobility_map:
            slug = str(mobility_map[mobility])
        elif spec.get("any_mobility") or mobility in ("fixed", "unknown"):
            slug = spec.get("default")
        if slug:
            out.append(str(slug))
    return tuple(dict.fromkeys(out))


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


def element_content_digest(element: Mapping[str, Any]) -> str:
    """Content-address one element's *content* for edit detection (P37.1 / ACQ-17).

    Under ``out body`` an element no longer carries ``version`` — the version
    counter stays on the ``osm_element_history`` channel — so edit detection
    moves onto the digest of the fields an edit actually changes: tags, the
    element's own coordinates/center/bounds, and the member lists (a way's
    ``nodes``, a relation's ``members``) whose change *is* a geometry edit.
    Acquisition metadata (timestamp/changeset/user/uid) is deliberately
    excluded: it is never the device's state (and ``user``/``uid`` is never
    in scope at all, SIG-INGEST-045e).
    """
    return content_digest(
        {
            "type": element.get("type"),
            "id": element.get("id"),
            "tags": element.get("tags") or {},
            "lat": element.get("lat"),
            "lon": element.get("lon"),
            "center": element.get("center"),
            "bounds": element.get("bounds"),
            "nodes": element.get("nodes"),
            "members": element.get("members"),
        }
    )


@dataclass(frozen=True)
class ContentSnapshotDiff(SnapshotDiff):
    """A snapshot diff that also reports *edited* elements (P37.1 / ACQ-17).

    :meth:`snapshot_diff` compares element references; this compares element
    *content digests*, so a re-tagged or re-sited element — still present under
    ``out body``, version unseen — surfaces as ``edited`` rather than silently
    re-persisting. ``persisted`` holds only content-identical elements.
    """

    edited: frozenset[ElementRef] = frozenset()


def snapshot_content_diff(
    previous: Mapping[ElementRef, str], current: Mapping[ElementRef, str]
) -> ContentSnapshotDiff:
    """Diff two snapshots of ``{ElementRef: element_content_digest}`` (P37.1)."""
    prev, cur = set(previous), set(current)
    changed = frozenset(r for r in prev & cur if previous[r] != current[r])
    return ContentSnapshotDiff(
        added=frozenset(cur - prev),
        persisted=frozenset(prev & cur) - changed,
        edited=changed,
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


def _tag_selectors() -> tuple[str, ...]:
    """The widened tag filters every query selects (P37.1 / ACQ-17).

    ``man_made=surveillance`` (the §23.2 asset layer) **plus** the camera-site
    selectors: ``["surveillance:type"]`` presence and each ``value_keys`` pair
    (``highway=speed_camera``). **Never a space in a filter** — a space trips
    the public instance's request filter (SIG-INGEST-045d); value filtering
    beyond the selectors happens client-side in :meth:`OSMConnector.normalize`.
    """
    v = vocab()
    sels = [f'["{v["selection_key"]}"="{v["selection_value"]}"]']
    for key in v["camera_site"]["presence_keys"]:
        sels.append(f'["{key}"]')
    for key, value in v["camera_site"]["value_keys"].items():
        sels.append(f'["{key}"="{value}"]')
    return tuple(sels)


def _select_union(region: str) -> str:
    """The union of every selector over node/way/relation inside ``region``.

    ``region`` is a parenthesised bbox literal ``(S,W,N,E)`` or an area
    reference ``(area.a)``.
    """
    return "".join(
        f"{kind}{sel}{region};" for sel in _tag_selectors() for kind in ("node", "way", "relation")
    )


def build_overpass_query(
    *,
    bbox: tuple[float, float, float, float] | None = None,
    timeout: int = OVERPASS_DEFAULT_TIMEOUT,
    maxsize: int = OVERPASS_DEFAULT_MAXSIZE,
) -> str:
    """Build an Overpass QL query for the surveillance layer, respecting etiquette.

    * Selects the widened scope (``man_made=surveillance`` + ``surveillance:type``
      presence + ``highway=speed_camera``) across node/way/relation
      (§23.2, P37.1 / ACQ-17).
    * Prints ``out body center qt;`` — the body verbosity carries tags and
      geometry (``center`` for ways/relations, ``qt`` a stable quadtile order)
      while requesting **no meta**, so ``user``/``uid`` are never asked for
      (SIG-INGEST-045e, the capture-side half of F-406). ``version``/
      ``timestamp``/``changeset`` no longer arrive either: edit detection is
      the content-digest diff (:func:`snapshot_content_diff`) and the version
      counter stays on the ``osm_element_history`` channel.
    * Carries ``[timeout:…][maxsize:…]`` (SIG-INGEST-045h).
    * **Never puts a space in a tag-value filter** — a space trips the public
      instance's request filter (SIG-INGEST-045d); any further value filtering is
      done client-side in :meth:`OSMConnector.normalize`.
    * Requires a bbox: an unbounded worldwide query is bulk-stitching and both
      prohibited and doomed in practice (SIG-INGEST-045i) — use a PBF dump for
      bulk (:func:`acquisition_mode`) and the declared area tiling
      (:func:`tile_discovery_targets`) for increments.
    """
    if bbox is None:
        raise BulkStitchingForbidden(
            "an unbounded Overpass query stitches the whole world (SIG-INGEST-045i); "
            "use a PBF dump for bulk and tiled Overpass for increments."
        )
    s, w, n, e = bbox
    body = _select_union(f"({s},{w},{n},{e})")
    return f"[out:json][timeout:{timeout}][maxsize:{maxsize}];({body});out body center qt;"


# --- the national/global area tiling (P37.1 / ACQ-17, I8 §4.3 item 3) ---------


@cache
def area_tiles() -> dict[str, Any]:
    """The declared collection tiling (``data/osm_area_tiles.toml``, data not code)."""
    return load_table("osm_area_tiles")


def us_state_area_selector(code: str) -> str:
    """The Overpass area filter for a US state/DC (ISO3166-2)."""
    return f'area["ISO3166-2"="{code}"]'


def country_area_selector(code: str) -> str:
    """The Overpass area filter for a country (ISO3166-1 alpha-2)."""
    return f'area["ISO3166-1"="{code}"]'


def declared_areas() -> list[dict[str, str]]:
    """The discovery order: the 51 US state/DC areas first, then every declared
    ISO country. The US has no country tile — its state areas are the coverage —
    so no element is ever fetched twice (SIG-INGEST-045i)."""
    tiles = area_tiles()
    out = [{"tile": code, "selector": us_state_area_selector(code)} for code in tiles["us_states"]]
    out += [
        {"tile": str(code).upper(), "selector": country_area_selector(str(code))}
        for code in tiles["countries"]
    ]
    return out


def build_area_count_query(
    selectors: Sequence[str],
    *,
    timeout: int,
    maxsize: int = OVERPASS_DEFAULT_MAXSIZE,
) -> str:
    """One chained ``out count;`` request over a chunk of area selectors.

    Each selector becomes ``<sel>->.aN;(<selection union>(area.aN);)->.cN;.cN
    out count;`` so the response's count elements align positionally with
    ``selectors`` — the discovery census every fetch tile reconciles against.
    """
    parts: list[str] = []
    for i, sel in enumerate(selectors):
        parts.append(f"{sel}->.a{i};({_select_union(f'(area.a{i})')})->.c{i};.c{i} out count;")
    return f"[out:json][timeout:{timeout}][maxsize:{maxsize}];{''.join(parts)}"


def build_area_fetch_query(
    selector: str,
    *,
    timeout: int,
    maxsize: int = OVERPASS_DEFAULT_MAXSIZE,
) -> str:
    """One ``out body center qt;`` fetch query for a single declared area."""
    return (
        f"[out:json][timeout:{timeout}][maxsize:{maxsize}];"
        f"{selector}->.a;({_select_union('(area.a)')});out body center qt;"
    )


def tile_discovery_targets(endpoint: str) -> list[dict[str, Any]]:
    """The ``out count;`` discovery targets — one per chunk of declared areas.

    Each target carries ``kind="overpass_tile_count"``, the ``tile_ids`` its
    positional counts map onto, the interpreter URL, and the reviewed pacing
    (``rate_limit_per_min`` from ``params.pace_seconds`` — the ~30s spacing the
    public instance expects, enforced by the shared fetcher's per-host delay).
    The fetch tiles themselves are resolved network-isolated by
    :meth:`OSMConnector.discover_more` once the counts are captured.
    """
    params = area_tiles()["params"]
    areas = declared_areas()
    chunk = max(1, int(params["areas_per_count"]))
    targets: list[dict[str, Any]] = []
    for i in range(0, len(areas), chunk):
        part = areas[i : i + chunk]
        query = build_area_count_query(
            [a["selector"] for a in part],
            timeout=int(params["count_timeout"]),
        )
        targets.append(
            {
                "id": f"{OSM_SOURCE_ID}:tile-count:{i // chunk}",
                "kind": "overpass_tile_count",
                "tile_ids": [a["tile"] for a in part],
                "url": f"{endpoint}?{urlencode({'data': query})}",
                "endpoint": endpoint,
                "rate_limit_per_min": max(1, int(60 // int(params["pace_seconds"]))),
                "pace_seconds": int(params["pace_seconds"]),
            }
        )
    return targets


def tile_fetch_target(
    tile: str, selector: str, expected_count: int, endpoint: str
) -> dict[str, Any]:
    """The resolved ``out body center qt;`` fetch target for one non-empty area.

    ``expected_count`` is the tile's discovery count; the post-capture stages
    reconcile the emitted element count against it and a mismatch beyond the
    declared tolerance is recorded ContentDrift (:func:`tile_count_drift`).
    """
    params = area_tiles()["params"]
    query = build_area_fetch_query(selector, timeout=int(params["fetch_timeout"]))
    return {
        "id": f"{OSM_SOURCE_ID}:tile:{tile}",
        "kind": "overpass",
        "tile": tile,
        "expected_count": int(expected_count),
        "url": f"{endpoint}?{urlencode({'data': query})}",
        "rate_limit_per_min": max(1, int(60 // int(params["pace_seconds"]))),
        "pace_seconds": int(params["pace_seconds"]),
    }


def parse_count_elements(parsed: Mapping[str, Any]) -> list[int]:
    """The per-statement totals of an ``out count;`` response, in order."""
    out: list[int] = []
    for el in parsed.get("elements", []):
        if el.get("type") == "count":
            tags = el.get("tags") or {}
            out.append(int(tags.get("total") or 0))
    return out


def tile_count_drift(expected: int, actual: int) -> int | None:
    """The element-count delta when it exceeds the declared tolerance, else ``None``.

    Elements can be mapped or deleted between the discovery and fetch passes, so
    small deltas are ordinary OSM movement, not drift: the tile reconciles
    unless ``|actual - expected| > max(count_tolerance_floor, expected *
    count_tolerance_pct)`` (SIG-ENG-042 — the counts reconcile or the run
    records the drift; never a vacuous success).
    """
    params = area_tiles()["params"]
    bound = max(
        int(params["count_tolerance_floor"]),
        int(float(params["count_tolerance_pct"]) * expected),
    )
    delta = abs(int(actual) - int(expected))
    return delta if delta > bound else None


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
        flagged = bool(claim.get("residential_parcel_flag"))
        version = claim.get("osm_version")
        by_ref[ref] = {
            "osm_element_type": ref.osm_type,
            "osm_element_id": ref.osm_id,
            # Version-optional (P37.1): `out body` yields None — the row keeps
            # the honest absent rather than minting a version it never saw.
            "osm_version": int(version) if version is not None else None,
            "asset_technology": claim.get("asset_technology"),
            "mobility": claim.get("mobility", "unknown"),
            # P35.66 (SIG-PUB-005/013): a parcel-intersecting asset is demoted
            # to C3 — this ODbL projection is the publish surface, so the
            # device point is withheld here (program-level facts only). The
            # raw geometry stays on the asset record (canonical evidence);
            # the verdict + flag ride the row so the demotion is recorded.
            "geometry": None if flagged else claim.get("geometry"),
            "first_observed": claim.get("first_observed"),
            "last_observed": claim.get("last_observed"),
            "changeset": claim.get("changeset"),
            "sensitivity_class": claim.get("sensitivity_class"),
            "residential_parcel_flag": flagged,
            "parcel_screen": claim.get("parcel_screen"),
            "parcel_screen_signal": claim.get("parcel_screen_signal"),
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

    def __init__(self, *, parcel_signal: ResidentialParcelSignal | None = None) -> None:
        # P35.66 (SIG-PUB-005/013): the declared residential-parcel signal the
        # asset emit screen consults — ``None`` resolves the committed
        # ``policy/data/residential_parcels.toml``; tests inject a fixture
        # layer. The connector never fabricates a verdict.
        self._parcel_signal = parcel_signal

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

    # -- capture (the mapper-identity refusal, SIG-INGEST-045e / F-406) --
    def capture(self, ctx: RunContext, fetched: FetchResult) -> CaptureRef:
        """Store the bytes — but refuse an Overpass response carrying ``user``/``uid``.

        P37.1 / ACQ-17 (D-R11-OSMUID-1, D-P34.49-2): the widened queries print
        ``out body`` so mapper identity is never *requested*; a response that
        still carries it is a nonconforming endpoint — recorded ContentDrift,
        and the screened bytes never reach the capture store (the defence the
        post-capture :func:`strip_mapper_identity` could never provide, since
        the raw capture sealed them first). Scoped to ``osm_overpass`` Overpass
        responses: the ``osm_element_history`` channel legitimately carries
        meta-shaped documents.
        """
        if (
            ctx.source.id == OSM_SOURCE_ID
            and _is_overpass_request(fetched.url)
            and _carries_mapper_identity(fetched.body)
        ):
            raise ContentDrift(
                ctx.source.id,
                "Overpass response carries user/uid under an `out body` query — "
                "mapper identity the request never asked for (SIG-INGEST-045e)",
                details=(
                    "the capture writer refuses to seal mapper-identity fields; "
                    "the endpoint is nonconforming"
                ),
            )
        return super().capture(ctx, fetched)

    def discover_more(
        self, ctx: RunContext, captures: Sequence[CaptureRef]
    ) -> list[Mapping[str, Any]]:
        """Resolve per-area fetch tiles from captured ``out count;`` responses.

        The national/global collection runs two passes inside one run (P37.1 /
        ACQ-17, SIG-INGEST-045i): discovery captures the per-area census, then
        every non-empty area resolves to one ``out body center qt;`` fetch
        target carrying its ``expected_count`` — the drift bound the fetch
        reconciles against. Pure: reads stored capture bytes and
        ``ctx.parameters``/``ctx.resolved_targets`` only (network-isolated by
        the driver), and returns the bounded follow-on list the continuation
        pass fetches.
        """
        by_url: dict[str, Mapping[str, Any]] = {}
        for t in ctx.parameters.get("targets", []) or []:
            if str(t.get("kind")) == "overpass_tile_count":
                by_url[str(t.get("url", ""))] = t
        area_by_tile = {a["tile"]: a["selector"] for a in declared_areas()}
        targets: list[Mapping[str, Any]] = []
        for cap in captures:
            count_target = by_url.get(cap.source_uri)
            if count_target is None:
                continue
            try:
                doc = json.loads(ctx.captures.get(cap.digest))
            except (ValueError, TypeError):
                continue  # a non-JSON count body is ContentDrift in parse()
            counts = parse_count_elements(doc)
            for tile, expected in zip(
                [str(x) for x in count_target.get("tile_ids") or []], counts, strict=False
            ):
                if expected <= 0:
                    continue  # an empty area resolves to no fetch tile
                selector = area_by_tile.get(tile)
                if selector is None:
                    continue
                target = tile_fetch_target(
                    tile,
                    selector,
                    expected,
                    str(count_target.get("endpoint") or _overpass_endpoint()),
                )
                ctx.resolved_targets[str(target["url"])] = target
                targets.append(target)
        return targets

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
        """Structure the captured OSM JSON (Overpass snapshot or element history).

        A live Overpass endpoint can return non-JSON (an HTML error/WAF page, a 429/
        504 body); rather than crash with an opaque ``JSONDecodeError``, surface it as
        :class:`ContentDrift` (fail loud, recorded — P25.3 / ADR-082), so the live
        runner writes a ``content_drift`` fetch record with 0 claims.

        The target the capture was fetched under is bound onto the parsed
        document (``_target``) so :meth:`extract` can reconcile a tile fetch
        against its discovery ``expected_count`` — context only, never content.
        """
        data = ctx.captures.get(capture.digest)
        try:
            doc = json.loads(data)
        except (ValueError, TypeError) as exc:
            head = data[:64] if isinstance(data, (bytes, bytearray)) else str(data)[:64]
            raise ContentDrift(
                ctx.source.id,
                "Overpass returned non-JSON content (HTML error / WAF page / rate-limit body)",
                details=f"{len(data)} bytes; starts {head!r} ({exc.__class__.__name__})",
            ) from exc
        if isinstance(doc, dict):
            target = ctx.resolved_targets.get(capture.source_uri) or _seed_target(
                ctx, capture.source_uri
            )
            if target is not None:
                doc = dict(doc)
                doc["_target"] = dict(target)
        return doc

    def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:
        """Raw records with locators, preserving raw values and discarding mapper identity.

        Handles three document shapes: an element-history document (all elements
        share one ``(type, id)`` with distinct versions) yields a ``first_observed``
        record (SIG-INGEST-045a); an ``out count;`` discovery document yields the
        per-tile census rows; an Overpass snapshot yields one raw asset record per
        in-scope element (the widened ``element_in_scope`` selection, P37.1).
        Under ``out body`` an element carries no ``version`` — the key stays
        ``None`` and edit detection is the content-digest diff (REQ-R1-01's
        preserved reference becomes content-addressed rather than versioned).
        A tile fetch reconciles its element count against the discovery
        ``expected_count`` — beyond the tolerance, recorded :class:`ContentDrift`.
        OSM ``user``/``uid`` are dropped here as defence-in-depth for the
        meta-shaped history channel (SIG-INGEST-045e); ``changeset`` is kept.
        """
        elements = list(parsed.get("elements", []))
        if _is_history_document(elements):
            return _extract_history(elements)
        if _is_count_document(elements):
            return _extract_tile_counts(elements, parsed.get("_target"))
        target = parsed.get("_target") if isinstance(parsed, Mapping) else None
        expected = (target or {}).get("expected_count")
        if expected is not None:
            drift = tile_count_drift(int(expected), len(elements))
            if drift is not None:
                raise ContentDrift(
                    ctx.source.id,
                    f"tile {(target or {}).get('tile') or (target or {}).get('id')}: "
                    f"discovery count {expected}, fetched {len(elements)} elements "
                    f"(Δ{drift}) — the discovery census and the fetch disagree",
                    details="SIG-ENG-042: tile counts reconcile or the run drifts",
                )
        out: list[Mapping[str, Any]] = []
        for el in elements:
            tags = el.get("tags", {})
            if not element_in_scope(tags):
                continue
            clean = strip_mapper_identity(el)
            version = clean.get("version")
            out.append(
                {
                    "record_kind": "asset",
                    "osm_type": str(clean["type"]),
                    "osm_id": int(clean["id"]),
                    # Version-optional (P37.1): `out body` carries no version —
                    # the (type,id,version) version-history channel is
                    # osm_element_history; edit detection is content-addressed.
                    "osm_version": int(version) if version is not None else None,
                    "changeset": clean.get("changeset"),
                    # P35.26 / SIG-ONTO-030: the upstream change date for this
                    # version — the tag claims' honest `observed_at` (never the
                    # fetch timestamp: an unchanged element re-fetched keeps its
                    # real last-modified date). None under `out body`.
                    "element_timestamp": clean.get("timestamp"),
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
            if raw.get("record_kind") == "tile_count":
                # The discovery census: a non-claim run-record row — the audit
                # surface every fetch tile's expected_count reconciles against.
                out.append(_stamp(dict(raw)))
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

        # SIG-ONTO-028: operator absence is a first-class, countable state — an
        # element with no `operator`/`operator:wikidata` tag earns an explicit
        # `operator_absent: true` claim, so the ~116,800-device backlog is
        # countable on the spine rather than implicit in a missing tag.
        if "operator" not in tags and "operator:wikidata" not in tags:
            rows.append(
                _stamp(
                    {
                        "record_kind": "claim",
                        "subject_id": ref.subject_id,
                        "osm_type": ref.osm_type,
                        "osm_id": ref.osm_id,
                        "osm_version": raw.get("osm_version"),
                        "predicate_id": "operator_absent",
                        "value": True,
                        "raw_value": None,  # P2: the absence is the fact
                        "observed_at": raw.get("element_timestamp"),
                    }
                )
            )

        # P35.26 / SIG-TRUST-003: the dataset publisher is recorded provenance —
        # a `published_by` claim (PUBLISHER role — literal, never an operational
        # entity-ref), so every OSM subject's publisher reads as PUBLISHER, and
        # a publishing-only source can never mint an operator edge.
        rows.append(
            _stamp(
                {
                    "record_kind": "claim",
                    "subject_id": ref.subject_id,
                    "osm_type": ref.osm_type,
                    "osm_id": ref.osm_id,
                    "osm_version": raw.get("osm_version"),
                    "predicate_id": "published_by",
                    "value": vocab()["publisher_label"],
                    "raw_value": vocab()["publisher_label"],
                    "observed_at": raw.get("element_timestamp"),
                }
            )
        )

        # P37.1 / ACQ-17 (SIG-PUB-011–014 stand-in): an element whose
        # provenance names Wi-Fi/BLE/RF detection keeps only 3-decimal
        # coarsened geometry on every derived surface — the asset row and the
        # camera-site coordinate claims; the precise bytes stay in the sealed
        # capture only.
        rf_source = rf_derived_source(tags)
        geometry = raw.get("geometry")
        if rf_source is not None:
            geometry = coarsened_geometry(geometry, int(vocab()["rf_source"]["decimals"]))

        # P35.66 (SIG-PUB-005/013): the residential-parcel screen runs on the
        # asset's device point (``point``/``center`` descriptors); every other
        # shape records ``unscreened`` — the declared check is point-in-parcel
        # and a bounds polygon asserting "no intersection" would claim a screen
        # that never ran. An ``intersects`` verdict demotes the record to C3
        # and stamps the flag; the geometry itself stays on the asset row
        # (canonical evidence) — the ODbL projection
        # (:func:`physical_asset_rows`) withholds it, so the publish surface
        # emits program-level facts only.
        sig = self._parcel_signal or declared_parcel_signal()
        verdict = screen_geometry_descriptor(geometry, signal=sig)
        asset_flagged = verdict is ParcelScreenVerdict.INTERSECTS
        asset_class = demote_for_residential_parcel(
            SensitivityClass.C1,  # SIG-PUB-006: roadside hardware defaults C1
            asset_flagged,
        )

        # The asset row itself — the ODbL physical_asset projection input. Carries
        # the version (edit detection — optional under `out body`), geometry,
        # inferred mobility, and a first_observed placeholder (None => resolved
        # later from history, NEVER the creation timestamp — SIG-INGEST-045a).
        rows.append(
            _stamp(
                {
                    "record_kind": "asset",
                    "subject_id": ref.subject_id,
                    "osm_type": ref.osm_type,
                    "osm_id": ref.osm_id,
                    "osm_version": raw.get("osm_version"),
                    "changeset": raw.get("changeset"),
                    "asset_technology": asset_technology,
                    "mobility": mobility,
                    "geometry": geometry,
                    "first_observed": None,
                    "last_observed": None,
                    "sensitivity_class": asset_class.value,
                    "geo_tier": geo_tier_for(asset_class),
                    "residential_parcel_flag": asset_flagged,
                    "parcel_screen": verdict.value,
                    "parcel_screen_signal": sig.stamp,
                    "rf_derived_source": rf_source,
                }
            )
        )

        # P37.1 / ACQ-17 (I8 §4.3): the camera-site claim family — the OSM
        # element as a camera-site ORIGIN record (external ref + namespace,
        # coarsened coordinates, unresolved jurisdiction, org-only operator,
        # technology) so it enters the camera-site ER pool.
        if is_camera_site_element(tags):
            rows.extend(self._camera_site_rows(ref, raw, tags, geometry, mobility))
        return rows

    def _camera_site_rows(
        self,
        ref: ElementRef,
        raw: Mapping[str, Any],
        tags: Mapping[str, str],
        geometry: Mapping[str, Any] | None,
        mobility: str,
    ) -> list[dict[str, Any]]:
        """The camera-site predicate family for one element (P37.1 / ACQ-17).

        Emitted on the element's own ``osm:<type>/<id>`` subject — the origin
        record the camera-site ER pool reads:

        * ``camera_external_ref`` (+ ``external_id``) in the declared
          ``osm.element`` namespace — the shared upstream id space a
          republisher's OSM ref joins under (P35.25 tier-1g, never a bare
          string coincidence).
        * ``camera_latitude``/``camera_longitude`` — the node point or the
          way/relation ``center``; already coarsened by the caller when the
          element is RF-derived (``coordinate_coarsened`` records the fact).
          ``camera_coordinate_source`` records ``osm`` — the honest "the point
          is the element's own geometry" source.
        * ``camera_jurisdiction`` = ``unresolved`` — OSM carries no reliable
          jurisdiction tag; honest absence over a guessed one.
        * ``camera_operator`` — only from an ``operator`` tag that carries NO
          affirmative natural-person signal (organisation-only; a person-shaped
          tag is suppressed and never minted). ``link()`` twins it into an
          organisation entity-ref via ``partner_ref_rows`` scoped to the
          source, exactly as dot_511 does.
        * ``technology`` — the P35.15b slugs
          (:func:`camera_site_technologies`); multi-cardinality, one claim
          per slug.
        """
        subject = ref.subject_id
        observed = raw.get("element_timestamp")
        version = raw.get("osm_version")
        rows: list[dict[str, Any]] = []

        def _claim(predicate: str, value: Any, **extra: Any) -> dict[str, Any]:
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": subject,
                "osm_type": ref.osm_type,
                "osm_id": ref.osm_id,
                "osm_version": version,
                "predicate_id": predicate,
                "value": value,
                "raw_value": value,
                "observed_at": observed,
            }
            row.update(extra)
            return _stamp(row)

        element_ref_value = f"{ref.osm_type}/{ref.osm_id}"
        rows.append(
            _claim(
                "camera_external_ref",
                subject,
                candidate_identifier={"scheme": "osm.element", "value": element_ref_value},
                id_namespace="osm.element",
            )
        )
        rows.append(_claim("external_id", subject))

        if isinstance(geometry, Mapping) and geometry.get("kind") in ("point", "center"):
            rf_source = rf_derived_source(tags)
            for predicate, key in (("camera_latitude", "lat"), ("camera_longitude", "lon")):
                extra: dict[str, Any] = {}
                if rf_source is not None:
                    extra["coordinate_coarsened"] = {
                        "decimals": int(vocab()["rf_source"]["decimals"]),
                        "basis": "rf_derived_source",
                        "source_value": rf_source,
                    }
                rows.append(_claim(predicate, float(geometry[key]), **extra))
            rows.append(_claim("camera_coordinate_source", "osm"))

        rows.append(
            _claim(
                "camera_jurisdiction",
                "unresolved",
                candidate_identifier={"scheme": "sig.unresolved", "value": "unresolved"},
            )
        )

        operator = str(tags.get("operator") or "").strip()
        if operator and natural_person_signal(operator) is None:
            # Organisation-only (P37.1): a person-shaped tag is suppressed
            # entirely — never a claim, never a mint; the verbatim tag stays
            # on the operator_stated claim for the record.
            rows.append(_claim("camera_operator", operator))

        for slug in camera_site_technologies(tags, mobility):
            rows.append(_claim("technology", slug))
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
            "osm_version": raw.get("osm_version"),
            "predicate_id": predicate,
            "osm_key": key,
            "raw_value": raw_value,  # P2: the raw value is always preserved
            # P35.26 / SIG-ONTO-030: the upstream change date of this element
            # version — the honest observation time of the tag state.
            "observed_at": raw.get("element_timestamp"),
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
                "osm_version": raw.get("osm_version"),
                "predicate_id": "unmapped_surveillance_tag",
                "osm_key": key,
                "raw_value": value,
                "observed_at": raw.get("element_timestamp"),
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

    # -- link --
    def link(self, ctx: RunContext, normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Twin authoritative ``camera_operator`` claims into organisation entity-refs.

        The same ``partner_ref_rows`` seam dot_511 uses (P35.26 / ADR-112): an
        evidenced OSM ``operator`` tag mints a scoped-name organisation ref
        anchored to the source — never a person (the emission half already
        suppresses person-shaped tags; the mint machinery additionally refuses
        ambiguous names). ``operator_stated``/``published_by`` mint nothing.
        """
        return partner_ref_rows(normalized, predicates={"camera_operator"}, scope=ctx.source.id)

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


def _overpass_endpoint() -> str:
    """The configured interpreter endpoint (lazy — live_targets imports osm too)."""
    import os

    from .live_targets import DEFAULT_OVERPASS_ENDPOINT

    return os.environ.get("SIG_OVERPASS_ENDPOINT", "").strip() or DEFAULT_OVERPASS_ENDPOINT


def _is_overpass_request(url: str) -> bool:
    """Whether a fetched URL is an Overpass interpreter request.

    The capture-side mapper-identity refusal (SIG-INGEST-045e) applies to the
    Overpass channel — an ``/api/interpreter`` URL or any request carrying the
    ``data=`` query parameter — and never to the ``osm_element_history``
    channel, whose API-0.6 responses legitimately carry meta fields.
    """
    return "interpreter" in url or "data=" in url


def _carries_mapper_identity(body: bytes | str) -> bool:
    """Whether a response body contains ``user``/``uid`` on any element."""
    try:
        doc = json.loads(body)
    except (ValueError, TypeError):
        return False  # a non-JSON body is ContentDrift in parse(), not identity
    discard = set(vocab()["mapper_identity_keys"])
    elements = doc.get("elements") if isinstance(doc, Mapping) else None
    if not isinstance(elements, list):
        return False
    return any(isinstance(el, Mapping) and discard & set(el) for el in elements)


def _seed_target(ctx: RunContext, source_uri: str) -> Mapping[str, Any] | None:
    """The configured seed target a capture was fetched under, by URL."""
    for t in ctx.parameters.get("targets", []) or []:
        if str(t.get("url", "")) == source_uri:
            return t
    return None


def _is_count_document(elements: list[Mapping[str, Any]]) -> bool:
    """Whether a parsed document is an ``out count;`` discovery response."""
    return bool(elements) and all(el.get("type") == "count" for el in elements)


def _extract_tile_counts(
    elements: list[Mapping[str, Any]], target: Mapping[str, Any] | None
) -> list[Mapping[str, Any]]:
    """One ``tile_count`` raw record per count element — the discovery census.

    Counts align positionally with the target's ``tile_ids`` (the query
    emits one ``out count;`` per area statement, in order); a target carrying
    no ids falls back to the positional index so the record is never lost.
    """
    tile_ids = [str(x) for x in (target or {}).get("tile_ids") or []]
    out: list[Mapping[str, Any]] = []
    for i, el in enumerate(elements):
        counts = el.get("tags") or {}
        out.append(
            {
                "record_kind": "tile_count",
                "tile_id": tile_ids[i] if i < len(tile_ids) else f"#{i}",
                "count_total": int(counts.get("total") or 0),
                "count_nodes": int(counts.get("nodes") or 0),
                "count_ways": int(counts.get("ways") or 0),
                "count_relations": int(counts.get("relations") or 0),
            }
        )
    return out


def _stamp(row: dict[str, Any]) -> dict[str, Any]:
    """Stamp a row into the ODbL compartment (§42.3, SIG-LIC-006)."""
    row.setdefault("source_id", OSM_SOURCE_ID)
    row["license"] = ODBL_LICENSE
    row["compartment"] = ODBL_COMPARTMENT
    if row.get("record_kind") == "claim":
        # P35.14a: the closed artifact genre for OSM claims is `osm_node_set`
        # (D2), never the connector_run (D3) fallback.
        row.setdefault("evidence_genre", "osm_node_set")
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
    ``type``/``id`` — ``version`` is NOT required since P37.1 (``out body``
    carries no meta; the reference key's version half lives on the
    ``osm_element_history`` channel, and an Overpass element keeps its own
    ``type``/``id``); ``count`` elements are the discovery-census shape; every
    in-scope element carries a ``tags`` map. It deliberately does NOT assert
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
        if el.get("type") == "count":
            continue  # an `out count;` discovery row — the tiling census
        for key in ("type", "id"):
            if key not in el:
                findings.append(f"element[{i}] ({el.get('type')}/{el.get('id')}) missing {key!r}")
        if el.get("type") not in ELEMENT_TYPES:
            findings.append(f"element[{i}] has unknown type {el.get('type')!r}")
        tags = el.get("tags", {})
        if element_in_scope(tags if isinstance(tags, Mapping) else {}) and not isinstance(
            tags, Mapping
        ):
            findings.append(f"element[{i}] in-scope element has non-map tags")
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
    "ContentSnapshotDiff",
    "ElementRef",
    "ElementVersionRef",
    "HistoryVersion",
    "OSMConnector",
    "SnapshotDiff",
    "acquisition_mode",
    "area_tiles",
    "assert_own_or_public_instance",
    "build_area_count_query",
    "build_area_fetch_query",
    "build_overpass_query",
    "camera_site_technologies",
    "canary_findings",
    "coarsened_geometry",
    "country_area_selector",
    "declared_areas",
    "element_content_digest",
    "element_in_scope",
    "element_version_ref",
    "first_observed_from_history",
    "geometry_descriptor",
    "history_versions",
    "is_camera_site_element",
    "is_surveillance_bearing_key",
    "is_surveillance_element",
    "load_claims_for_l1",
    "map_mobility",
    "map_surveillance_type",
    "overpass_status_action",
    "parse_count_elements",
    "physical_asset_rows",
    "rf_derived_source",
    "snapshot_content_diff",
    "snapshot_diff",
    "split_multivalue",
    "strip_mapper_identity",
    "tile_count_drift",
    "tile_discovery_targets",
    "tile_fetch_target",
    "unmapped_tag_task",
    "us_state_area_selector",
    "vocab",
    "vocab_version",
]
