# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.69b — the OGC WFS family connector (ACQ-23b).

ONE registered connector (``ogc_wfs``) over ONE committed vocabulary
(``ogc_wfs_vocab``, ``sig.ogc-wfs-vocab/1``) and ONE committed inventory
(``ogc_wfs_targets``, ``sig.ogc-wfs-targets/1``) serving the four ACQ-23b
seats (I5-C312 Runnymede, I5-C315 South Kesteven, I5-C321 Clackmannanshire,
I5-C322 Ipswich — the last stays ``[[enumerated]]``, D-P37.69b-1):

* ``wfs_capabilities`` — ONE declared ``GetCapabilities`` document on the
  committed ``service_url``. It mints ONE ``ogc_service:`` record carrying
  the served facts — the declared service version, the served feature-type
  names, the upstream ``updateSequence`` when published — plus the seat's
  declared catalogue metadata (publisher, licence, jurisdiction,
  technology). ``expected_typenames`` pins names the document MUST serve;
  ``feature_type_selector`` (``"sole"`` or a literal name) turns the
  captured document into the discovery surface for a bounded
  ``wfs_get_feature`` follow-on inside the same run (``discover_more`` —
  the SERVED document names the feature type, never a guessed one; SKDC's
  statmap seat records no typename, so only this lane can wire it).

* ``wfs_get_feature`` — ONE declared bounded ``GetFeature`` page
  (``typenames=<t>&count=<n>``, WFS 2.0). Each member feature must carry a
  ``gml:Point`` whose ``srsName`` sits in the vocabulary's committed
  CRS→axis-order map (P35.16/F-322 — an unmapped CRS is drift, never a
  guessed order); the ``gml:pos`` pair reads under that order. Every
  property local-name is Part VIII header-screened (``denied_match`` —
  F-330), and each member mints a ``traffic_camera:`` subject through the
  same ``CameraRegistryEntry`` emit ``dot_511`` uses — the parcel screen,
  the §19.4 tier transform, the declared-axis-order stamp and the PKG-07
  declared-technology contract all ride the shared machinery. The lane also
  mints ONE ``open_data_index:`` count record per page
  (``numberMatched``/``numberReturned`` — the served counts, never a
  fabricated census).

An ``ExceptionReport``/``ows:ExceptionReport`` response, a non-XML payload,
a missing declared typename, an out-of-bound member count, a non-point
geometry or an absent ``pos`` pair is ``ContentDrift`` — the lane never
emits a guessed or partial record.

Every seat stays ``ingestion_permitted=false``; leg B (the first real wire)
is the operator's act under ING-GO-D (OP-26) — nothing here flips a row.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from functools import cache
from typing import Any
from urllib.parse import urlencode, urlsplit
from xml.etree import ElementTree

from parsing.locator import Locator
from policy.parcel_screen import ParcelScreenVerdict, declared_parcel_signal, screen_point
from policy.sensitivity import SensitivityClass, demote_for_residential_parcel

from ._data import load_table
from .dot_511 import (
    CameraRegistryEntry,
    declared_record_kind,
    publishable_coordinate,
)
from .field_denylist import denied_match
from .stages import CaptureRef, Connector, ContentDrift, FetchResult, RunContext, register

_VOCAB_TABLE = "ogc_wfs_vocab"
_TARGETS_TABLE = "ogc_wfs_targets"
_SCHEMA = "sig.ogc-wfs-vocab/1"
_TARGETS_SCHEMA = "sig.ogc-wfs-targets/1"
_EVIDENCE_GENRE = "camera_registry"

CONNECTOR_NAME = "ogc_wfs"
CONNECTOR_NAMES = frozenset({CONNECTOR_NAME})

#: The declared WFS service-version member — the family ships the 2.0
#: request shape (``typenames`` + ``count``); a different declared version
#: fails at expansion, never silently re-parameterised.
_WFS_VERSION = "2.0.0"
#: The reader's hard caps — a served page past the declared bound is drift,
#: never a silently truncated ingest.
_MAX_MEMBERS = 5_000
_MAX_BYTES = 16 * 1024 * 1024
_DEFAULT_COUNT = 500
_MAX_RESOLVE = 4

_GML_ID = "{http://www.opengis.net/gml/3.2}id"


@cache
def vocab() -> dict[str, Any]:
    table = load_table(_VOCAB_TABLE)
    if str(table.get("schema") or "") != _SCHEMA:
        raise ValueError(f"ogc_wfs vocabulary must be {_SCHEMA!r}")
    return table


def vocab_version() -> str:
    return str(vocab()["vocab_version"])


@cache
def predicate_allowlist() -> frozenset[str]:
    return frozenset(str(p) for p in vocab()["predicate_allowlist"])


def assert_predicate_allowed(predicate: str) -> str:
    if predicate not in predicate_allowlist():
        raise ValueError(
            f"predicate {predicate!r} is not in the ogc_wfs allowlist "
            f"{sorted(predicate_allowlist())} (SIG-INGEST-033)"
        )
    return predicate


@cache
def srs_axis_orders() -> dict[str, str]:
    return {str(k): str(v) for k, v in dict(vocab()["srs_axis_orders"]).items()}


@cache
def target_table() -> list[dict[str, Any]]:
    table = load_table(_TARGETS_TABLE)
    if str(table.get("schema") or "") != _TARGETS_SCHEMA:
        raise ValueError(f"ogc_wfs inventory must be {_TARGETS_SCHEMA!r}")
    return [dict(t) for t in table.get("targets", ())]


@cache
def enumerated_rows() -> list[dict[str, Any]]:
    table = load_table(_TARGETS_TABLE)
    return [dict(t) for t in table.get("enumerated", ())]


@cache
def committed_hosts() -> frozenset[str]:
    return frozenset(str(h) for h in vocab()["hosts"])


def _assert_host(url: str, owner: str) -> None:
    """The expanded URL must sit on the committed host set — never egress off it."""
    host = urlsplit(url).netloc.lower()
    if host not in committed_hosts():
        raise ValueError(
            f"{owner} expands to host {host!r}, off the committed host set "
            f"{sorted(committed_hosts())} — a review error, never allowed"
        )


def _declared_version(spec: Mapping[str, Any], owner: str) -> str:
    version = str(spec.get("wfs_version") or _WFS_VERSION)
    if version != _WFS_VERSION:
        raise ValueError(
            f"{owner} declares wfs_version {version!r} — the family ships the "
            f"{_WFS_VERSION} request shape only"
        )
    return version


def capabilities_url(spec: Mapping[str, Any]) -> str:
    """The ONE GetCapabilities request URL a committed row expands to."""
    service_url = str(spec["service_url"]).split("?", 1)[0]
    query = urlencode(
        {
            "service": "WFS",
            "request": "GetCapabilities",
            "version": _declared_version(spec, spec.get("id", "target")),
        }
    )
    url = f"{service_url}?{query}"
    _assert_host(url, f"ogc_wfs target {spec.get('id')!r}")
    return url


def get_feature_url(spec: Mapping[str, Any]) -> str:
    """The ONE bounded GetFeature request URL — WFS 2.0 ``typenames``+``count``."""
    service_url = str(spec["service_url"]).split("?", 1)[0]
    typename = str(spec.get("typename") or "").strip()
    if not typename:
        raise ValueError(
            f"ogc_wfs target {spec.get('id')!r} declares kind 'wfs_get_feature' "
            "with no typename — a feature page is never guessed"
        )
    count = int(spec.get("count") or _DEFAULT_COUNT)
    if count < 1 or count > _MAX_MEMBERS:
        raise ValueError(
            f"ogc_wfs target {spec.get('id')!r} declares count {count} — "
            f"outside the reviewed bound 1..{_MAX_MEMBERS}"
        )
    query = urlencode(
        {
            "service": "WFS",
            "version": _declared_version(spec, spec.get("id", "target")),
            "request": "GetFeature",
            "typenames": typename,
            "count": str(count),
        }
    )
    url = f"{service_url}?{query}"
    _assert_host(url, f"ogc_wfs target {spec.get('id')!r}")
    return url


def targets_for(source_id: str, *, connector: str | None = None) -> list[dict[str, Any]]:
    out = [t for t in target_table() if str(t.get("source_id")) == source_id]
    if connector is not None:
        out = [t for t in out if str(t.get("connector")) == connector]
    return out


def expanded_targets(source_id: str) -> list[dict[str, Any]]:
    """The expanded live targets for ``source_id`` — one bounded row per seat."""
    out: list[dict[str, Any]] = []
    for row in targets_for(source_id):
        kind = str(row.get("kind") or "")
        if kind == "wfs_capabilities":
            url = capabilities_url(row)
        elif kind == "wfs_get_feature":
            url = get_feature_url(row)
        else:
            raise ValueError(f"ogc_wfs target {row.get('id')!r} has kind {kind!r}")
        out.append(
            {
                "id": str(row["id"]),
                "url": url,
                "kind": str(row["kind"]),
                "target": dict(row),
            }
        )
    return out


def _stamp(row: dict[str, Any], *, source_id: str, license_spdx: str) -> dict[str, Any]:
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    if license_spdx:
        row.setdefault("license", license_spdx)
    return row


def _evidence(url: str, index: int) -> dict[str, Any]:
    return {
        "source_url": url,
        "extraction_method": "ogc_wfs_gml",
        "locator": Locator.row(index).to_row(),
    }


def _claim(
    subject_id: str,
    predicate: str,
    value: Any,
    raw_value: str,
    evidence: Mapping[str, Any],
    *,
    source_id: str,
    license_spdx: str,
) -> dict[str, Any]:
    return _stamp(
        {
            "record_kind": "claim",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed(predicate),
            "raw_value": raw_value,
            "value": value,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": dict(evidence),
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )


def _slug(text: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "-" for ch in text.strip())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-") or "unnamed"


# --- the GML/WFS payload readers (pure functions of the capture bytes) ---------


def _localname(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _root(source_id: str, data: bytes, kind: str) -> Any:
    if len(data) > _MAX_BYTES:
        raise ContentDrift(
            source_id,
            f"the served {kind} document is {len(data)} bytes, over the {_MAX_BYTES} bound",
        )
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContentDrift(source_id, f"the served {kind} document is not valid UTF-8") from exc
    try:
        root = ElementTree.fromstring(text)
    except ElementTree.ParseError as exc:
        raise ContentDrift(source_id, f"the served {kind} document does not parse as XML") from exc
    name = _localname(str(root.tag))
    if name == "ExceptionReport":
        detail = " ".join(
            (el.text or "").strip()
            for el in root.iter()
            if _localname(str(el.tag)) == "ExceptionText"
        )[:300]
        raise ContentDrift(
            source_id,
            f"the {kind} endpoint returned an OGC ExceptionReport "
            + (f"({detail!r})" if detail else ""),
        )
    return root


def _check_markers(source_id: str, spec: Mapping[str, Any], data: bytes) -> None:
    for marker in spec.get("expected_markers", ()) or ():
        if str(marker).encode() not in data:
            raise ContentDrift(
                source_id,
                f"reviewed marker {str(marker)!r} is absent from the served "
                f"document ({spec.get('id')!r}) — a drifted capture, never a "
                "partially accepted page",
            )


def _capabilities_facts(source_id: str, data: bytes) -> dict[str, Any]:
    """The served service facts — version + feature-type names (fail closed)."""
    root = _root(source_id, data, "GetCapabilities")
    if _localname(str(root.tag)) != "WFS_Capabilities":
        raise ContentDrift(
            source_id,
            f"the GetCapabilities payload's root is {_localname(str(root.tag))!r}, "
            "not WFS_Capabilities — a drifted service document",
        )
    served: list[str] = []
    for el in root.iter():
        if _localname(str(el.tag)) != "FeatureType":
            continue
        name_el = next(
            (c for c in list(el) if _localname(str(c.tag)) == "Name"),
            None,
        )
        if name_el is None or not str(name_el.text or "").strip():
            raise ContentDrift(
                source_id, "a served FeatureType carries no Name — a shapeless service listing"
            )
        served.append(str(name_el.text).strip())
    if not served:
        raise ContentDrift(
            source_id, "the capabilities document serves zero feature types — nothing to name"
        )
    return {
        "served_version": str(root.get("version") or ""),
        "update_sequence": str(root.get("updateSequence") or ""),
        "served_typenames": sorted(set(served)),
    }


def _resolve_selector(source_id: str, spec: Mapping[str, Any], served: list[str]) -> list[str]:
    """The feature types a ``feature_type_selector`` resolves to (fail closed)."""
    selector = str(spec.get("feature_type_selector") or "").strip()
    if not selector:
        return []
    if selector == "sole":
        if len(served) != 1:
            raise ContentDrift(
                source_id,
                f"feature_type_selector 'sole' met {len(served)} served feature types "
                f"{served} — the INSPIRE service is not single-type; never a guessed name",
            )
        return list(served)
    if selector not in served:
        raise ContentDrift(
            source_id,
            f"declared feature_type_selector {selector!r} is not among the served "
            f"feature types {served} — a renamed layer is drift",
        )
    return [selector]


def _member_rows(source_id: str, root: Any, spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Each ``wfs:member``/``gml:featureMember`` → a flat row dict (fail closed)."""
    members = [el for el in root.iter() if _localname(str(el.tag)) in {"member", "featureMember"}]
    bound = int(spec.get("count") or _DEFAULT_COUNT)
    if len(members) > bound or len(members) > _MAX_MEMBERS:
        raise ContentDrift(
            source_id,
            f"the GetFeature page carries {len(members)} members over the declared "
            f"bound {bound} — a drifted page, never silently truncated",
        )
    ref_field = str(spec.get("ref_field") or "").strip()
    name_field = str(spec.get("name_field") or "").strip()
    orders = srs_axis_orders()
    allowed_srs = {str(s) for s in (spec.get("expected_srs") or orders.keys())}
    rows: list[dict[str, Any]] = []
    for i, member in enumerate(members):
        feature = next((c for c in list(member) if isinstance(c.tag, str)), None)
        if feature is None:
            raise ContentDrift(source_id, f"member {i} carries no feature element")
        props: dict[str, str] = {}
        prop_names: list[str] = []
        geom_prop = ""
        point: Any | None = None
        for child in list(feature):
            cname = _localname(str(child.tag))
            for el in child.iter():
                if _localname(str(el.tag)) == "Point" and point is None:
                    point = el
                    geom_prop = cname
            if cname not in prop_names:
                prop_names.append(cname)
            text = (child.text or "").strip()
            if text and cname not in props:
                props[cname] = text
        for name in prop_names:
            term = denied_match(name)
            if term is not None:
                raise ContentDrift(
                    source_id,
                    f"the served feature {i} publishes denied field {name!r} "
                    f"(denied {term!r}) — a Part VIII field the lane refuses "
                    "by name (F-330)",
                )
        if point is None:
            raise ContentDrift(
                source_id,
                f"feature {i} carries no gml:Point — the lane's contract is "
                "device points, never a guessed geometry",
            )
        srs = str(point.get("srsName") or "").strip()
        if not srs:
            for el in member.iter():
                if str(el.get("srsName") or "").strip():
                    srs = str(el.get("srsName")).strip()
                    break
        if srs not in allowed_srs:
            raise ContentDrift(
                source_id,
                f"feature {i} publishes srsName {srs!r} off the declared set "
                f"{sorted(allowed_srs)} — a CRS drift, never a guessed order",
            )
        axis_order = orders.get(srs)
        if axis_order is None:
            raise ContentDrift(
                source_id,
                f"feature {i} srsName {srs!r} is unmapped in the vocabulary "
                "CRS→axis table — a review error, never a guessed order",
            )
        pos_el = next(
            (c for c in list(point) if _localname(str(c.tag)) == "pos"),
            None,
        )
        coords_el = (
            next((c for c in list(point) if _localname(str(c.tag)) == "coordinates"), None)
            if pos_el is None
            else None
        )
        coord_source = "gml:pos"
        raw_pair = ""
        if pos_el is not None:
            raw_pair = (pos_el.text or "").strip()
        elif coords_el is not None:
            coord_source = "gml:coordinates"
            raw_pair = (coords_el.text or "").strip()
        if not raw_pair:
            raise ContentDrift(
                source_id, f"feature {i} carries an empty gml Point — no published coordinate"
            )
        parts = re.split(r"[\s,]+", raw_pair)
        parts = [p for p in parts if p]
        if len(parts) != 2:
            raise ContentDrift(
                source_id,
                f"feature {i} coordinate pair {raw_pair!r} is not a 2-ord pair — "
                "a drifted geometry, never a guessed split",
            )
        try:
            a, b = float(parts[0]), float(parts[1])
        except ValueError:
            raise ContentDrift(
                source_id, f"feature {i} coordinate pair {raw_pair!r} is not numeric"
            ) from None
        lat, lon = (a, b) if axis_order == "lat-lon" else (b, a)
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ContentDrift(
                source_id,
                f"feature {i} published coordinate ({lat},{lon}) is out of range — "
                "drift, not a corrected pair",
            )
        ref = ""
        if ref_field:
            ref = str(props.get(ref_field) or "").strip()
            if not ref:
                raise ContentDrift(
                    source_id,
                    f"declared ref_field {ref_field!r} is absent or empty on feature {i}",
                )
        else:
            ref = str(
                feature.get(_GML_ID)
                or feature.get("{http://www.opengis.net/gml}id")
                or feature.get("fid")
                or feature.get("id")
                or ""
            ).strip()
        if not ref:
            ref = f"f{i}"
        name = ""
        if name_field:
            name = str(props.get(name_field) or "").strip()
        used = {n for n in (ref_field, name_field, geom_prop) if n}
        rows.append(
            {
                "ref": ref,
                "name": name,
                "lat": lat,
                "lon": lon,
                "coord_source": f"{geom_prop or 'gml:Point'}:{coord_source}",
                "srs_name": srs,
                "axis_order": axis_order,
                "prop_names": prop_names,
                "excluded_fields": sorted(n for n in prop_names if n not in used),
            }
        )
    return rows


def _collection_counts(source_id: str, root: Any, members: int) -> dict[str, Any]:
    """The served page counts — ``numberMatched``/``numberReturned`` honest facts."""
    raw_matched = str(root.get("numberMatched") or "").strip()
    raw_returned = str(root.get("numberReturned") or "").strip()
    matched: int | None = None
    if raw_matched and raw_matched.lower() != "unknown":
        try:
            matched = int(raw_matched)
        except ValueError:
            raise ContentDrift(
                source_id,
                f"the FeatureCollection's numberMatched {raw_matched!r} is not an integer",
            ) from None
    returned = members
    if raw_returned:
        try:
            declared_returned = int(raw_returned)
        except ValueError:
            raise ContentDrift(
                source_id,
                f"the FeatureCollection's numberReturned {raw_returned!r} is not an integer",
            ) from None
        if declared_returned != members:
            raise ContentDrift(
                source_id,
                f"numberReturned {declared_returned} disagrees with the "
                f"{members} served members — a drifted envelope",
            )
    return {
        "number_matched": matched,
        "number_returned": returned,
        "count_source": "numberMatched" if matched is not None else "memberCount",
    }


# --- emit --------------------------------------------------------------------


def _service_rows(
    *,
    source_id: str,
    spec: Mapping[str, Any],
    url: str,
    facts: Mapping[str, Any],
    resolved: Sequence[str],
) -> list[dict[str, Any]]:
    """One ``ogc_service:`` record — the capabilities document's served facts."""
    license_spdx = str(spec.get("license_spdx") or "")
    service_id = str(spec.get("service_id") or spec.get("id") or "service").strip()
    subject_id = f"ogc_service:{source_id}:{_slug(service_id)}"
    ev = _evidence(url, 0)
    entity = _stamp(
        {
            "record_kind": "ogc_service",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("portal_index"),
            "external_id": service_id,
            "raw_value": service_id,
            "title": str(spec.get("title") or ""),
            "publisher_label": str(spec.get("publisher") or ""),
            "dataset_license_id": str(spec.get("dataset_license_id") or ""),
            "wfs_version": str(facts.get("served_version") or ""),
            "update_sequence": str(facts.get("update_sequence") or ""),
            "served_feature_types": list(facts.get("served_typenames") or []),
            "served_type_count": len(facts.get("served_typenames") or []),
            "resolved_typenames": list(resolved),
            "excluded_fields": [],
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )
    rows: list[dict[str, Any]] = [entity]
    rows.append(
        _claim(
            subject_id,
            "external_id",
            service_id,
            service_id,
            ev,
            source_id=source_id,
            license_spdx=license_spdx,
        )
    )
    if entity["title"]:
        rows.append(
            _claim(
                subject_id,
                "title",
                entity["title"],
                entity["title"],
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    if entity["publisher_label"]:
        rows.append(
            _claim(
                subject_id,
                "published_by",
                entity["publisher_label"],
                entity["publisher_label"],
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    jurisdiction = str(spec.get("jurisdiction") or "").strip()
    if jurisdiction:
        rows.append(
            _claim(
                subject_id,
                "jurisdiction",
                jurisdiction,
                jurisdiction,
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    technology = str(spec.get("technology") or "").strip()
    if technology:
        rows.append(
            _claim(
                subject_id,
                "technology",
                technology,
                technology,
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    as_of = str(facts.get("update_sequence") or spec.get("dataset_modified") or "").strip()
    if as_of:
        rows.append(
            _claim(
                subject_id,
                "as_of",
                as_of,
                as_of,
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    return rows


def _index_rows(
    *,
    source_id: str,
    spec: Mapping[str, Any],
    url: str,
    counts: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """The feature page's ``open_data_index:`` record — served + returned counts."""
    license_spdx = str(spec.get("license_spdx") or "")
    target_id = str(spec.get("id") or "")
    subject_id = f"open_data_index:{source_id}:{target_id}"
    ev = _evidence(url, 0)
    matched = counts.get("number_matched")
    returned = int(counts.get("number_returned") or 0)
    entity = _stamp(
        {
            "record_kind": "open_data_index",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("portal_index"),
            "external_id": target_id,
            "raw_value": target_id,
            "query": str(spec.get("typename") or ""),
            "result_count": int(matched) if matched is not None else returned,
            "returned_count": returned,
            "truncated": bool(matched is not None and returned < int(matched)),
            "count_source": str(counts.get("count_source") or ""),
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )
    rows = [entity]
    rows.append(
        _claim(
            subject_id,
            "external_id",
            target_id,
            target_id,
            ev,
            source_id=source_id,
            license_spdx=license_spdx,
        )
    )
    return rows


def _camera_rows(
    *,
    ctx: RunContext,
    spec: Mapping[str, Any],
    members: Sequence[Mapping[str, Any]],
    url: str,
) -> list[dict[str, Any]]:
    """Member row dicts → ``traffic_camera:`` claim sets via the shared emit."""
    source_id = ctx.source.id
    sig = declared_parcel_signal()
    license_spdx = str(spec.get("license_spdx") or "")
    sensitivity_class = str(spec.get("sensitivity_class") or vocab()["default_sensitivity_class"])
    out: list[dict[str, Any]] = []
    retrieved = datetime.now(UTC).isoformat()
    for i, member in enumerate(members):
        lat = float(member["lat"])
        lon = float(member["lon"])
        verdict = screen_point(lat, lon, signal=sig)
        residential_flag = False
        cls_value = sensitivity_class
        if verdict is ParcelScreenVerdict.INTERSECTS:
            cls_value = demote_for_residential_parcel(SensitivityClass(cls_value), True).value
            residential_flag = True
            tier = 3
            pub_lat = pub_lon = None
        else:
            pub_lat, pub_lon, tier = publishable_coordinate(lat, lon, cls_value)
        entry = CameraRegistryEntry(
            camera_ref=str(member["ref"]),
            source_id=source_id,
            target_id=str(spec.get("id")),
            state=str(spec.get("state") or ""),
            agency=str(spec.get("publisher") or ""),
            latitude=pub_lat,
            longitude=pub_lon,
            coordinate_source=str(member["coord_source"]),
            geo_tier=tier,
            sensitivity_class=cls_value,
            license_spdx=license_spdx,
            technology=str(spec.get("technology") or ""),
            record_kind=declared_record_kind(spec),
            name=str(member["name"]).strip() or None,
            jurisdiction_scheme=str(spec.get("jurisdiction_scheme") or "iso.3166_2"),
            extraction_method="ogc_wfs_getfeature_gml",
            excluded_fields=tuple(member["excluded_fields"]),
            residential_parcel_flag=residential_flag,
            parcel_screen=verdict.value,
            parcel_screen_signal=sig.stamp,
            axis_order=str(member["axis_order"]),
        )
        out.extend(entry.claim_rows(url, retrieved, i))
    return out


def _resolve(ctx: RunContext, source_uri: str) -> dict[str, Any]:
    """The run-time target a capture was fetched from (exact-URL match)."""
    for t in ctx.parameters.get("targets", []):
        if str(t.get("url")) == source_uri:
            return dict(t)
    resolved = ctx.resolved_targets.get(source_uri)
    if resolved is not None:
        return dict(resolved)
    for t in ctx.parameters.get("targets", []):
        spec = t.get("target") or {}
        base = str(spec.get("service_url") or "\x00").split("?", 1)[0]
        if base != "\x00" and source_uri.startswith(base):
            return dict(t)
    rows = targets_for(ctx.source.id)
    return {"id": str(rows[0]["id"]), "target": dict(rows[0])} if rows else {}


@register
class OgcWfsConnector(Connector):
    """The OGC WFS family's eight-stage lane (ACQ-23b)."""

    name = CONNECTOR_NAME
    version = "1.0.0"
    ingestion_mode = "rest_api"
    incrementality = "re-issue detection via content-addressed capture digests"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        targets = list(ctx.parameters.get("targets", []))
        if targets:
            return targets
        return [dict(t) for t in expanded_targets(ctx.source.id)]

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """ONE polite GET on the expanded request URL — the only egress."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def discover_more(
        self, ctx: RunContext, captures: Sequence[CaptureRef]
    ) -> list[Mapping[str, Any]]:
        """Resolve GetFeature follow-ons from captured capabilities (one pass).

        A capabilities capture whose committed row declares
        ``feature_type_selector`` is the discovery surface for its feature
        page: the SERVED document names the feature type (``"sole"`` asserts
        a single-type service; a literal name asserts membership), and the
        resolved child inherits the seat's reviewed declarations — never a
        guessed typename.
        """
        resolved: list[Mapping[str, Any]] = []
        for capture in captures:
            target = _resolve(ctx, str(capture.source_uri))
            spec = dict(target.get("target") or target)
            if str(spec.get("kind") or "") != "wfs_capabilities":
                continue
            selector = str(spec.get("feature_type_selector") or "").strip()
            if not selector:
                continue
            data = ctx.captures.get(capture.digest)
            facts = _capabilities_facts(ctx.source.id, data)
            names = _resolve_selector(ctx.source.id, spec, list(facts["served_typenames"]))
            bound = int(spec.get("max_resolve") or _MAX_RESOLVE)
            if len(names) > bound:
                raise ContentDrift(
                    ctx.source.id,
                    f"the selector resolved {len(names)} feature types over the "
                    f"declared bound {bound}",
                )
            for typename in names:
                child_spec = {
                    **{k: v for k, v in spec.items() if k != "kind"},
                    "kind": "wfs_get_feature",
                    "typename": typename,
                    "count": int(spec.get("getfeature_count") or _DEFAULT_COUNT),
                    "resolved_from": str(capture.source_uri),
                }
                child = {
                    "id": f"{spec.get('id')}:{typename}",
                    "url": get_feature_url(child_spec),
                    "kind": "wfs_get_feature",
                    "target": child_spec,
                }
                ctx.resolved_targets[str(child["url"])] = child
                resolved.append(child)
        return resolved

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        target = _resolve(ctx, capture.source_uri)
        spec = dict(target.get("target") or target)
        kind = str(spec.get("kind") or "")
        data = ctx.captures.get(capture.digest)
        _check_markers(ctx.source.id, spec, data)
        if kind == "wfs_capabilities":
            facts = _capabilities_facts(ctx.source.id, data)
            resolved = _resolve_selector(ctx.source.id, spec, list(facts["served_typenames"]))
            expected = [str(n) for n in (spec.get("expected_typenames") or ())]
            missing = [n for n in expected if n not in facts["served_typenames"]]
            if missing:
                raise ContentDrift(
                    ctx.source.id,
                    f"declared expected_typenames {missing} are not among the "
                    f"served feature types {facts['served_typenames']} — a "
                    "renamed layer is drift, never a silent pass",
                )
            return {
                "kind": "wfs_capabilities",
                "payload": {**facts, "resolved_typenames": resolved},
                "capture": capture,
                "target": spec,
            }
        if kind == "wfs_get_feature":
            root = _root(ctx.source.id, data, "GetFeature")
            if _localname(str(root.tag)) != "FeatureCollection":
                raise ContentDrift(
                    ctx.source.id,
                    f"the GetFeature payload's root is {_localname(str(root.tag))!r}, "
                    "not FeatureCollection — a drifted service document",
                )
            members = _member_rows(ctx.source.id, root, spec)
            counts = _collection_counts(ctx.source.id, root, len(members))
            return {
                "kind": "wfs_get_feature",
                "payload": {"members": members, "counts": counts},
                "capture": capture,
                "target": spec,
            }
        raise ContentDrift(
            ctx.source.id, f"a capture arrived from a target of undeclared kind {kind!r}"
        )

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        spec = dict(parsed.get("target") or {})
        kind = str(parsed.get("kind") or "")
        if kind == "wfs_capabilities":
            return [
                {
                    "record_kind": "wfs_capabilities_document",
                    "served_version": str(parsed["payload"]["served_version"]),
                    "update_sequence": str(parsed["payload"]["update_sequence"]),
                    "served_typenames": list(parsed["payload"]["served_typenames"]),
                    "resolved_typenames": list(parsed["payload"]["resolved_typenames"]),
                    "source_uri": parsed["capture"].source_uri,
                    "retrieved_at": (
                        parsed["capture"].retrieved_at.isoformat()
                        if parsed["capture"].retrieved_at is not None
                        else datetime.now(UTC).isoformat()
                    ),
                    "target": spec,
                }
            ]
        return [
            {
                "record_kind": "wfs_feature_page",
                "members": list(parsed["payload"]["members"]),
                "counts": dict(parsed["payload"]["counts"]),
                "source_uri": parsed["capture"].source_uri,
                "retrieved_at": (
                    parsed["capture"].retrieved_at.isoformat()
                    if parsed["capture"].retrieved_at is not None
                    else datetime.now(UTC).isoformat()
                ),
                "target": spec,
            }
        ]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            spec = dict(raw.get("target") or {})
            url = str(raw.get("source_uri") or "")
            if raw.get("record_kind") == "wfs_capabilities_document":
                out.extend(
                    _service_rows(
                        source_id=ctx.source.id,
                        spec=spec,
                        url=url,
                        facts={
                            "served_version": raw["served_version"],
                            "update_sequence": raw["update_sequence"],
                            "served_typenames": raw["served_typenames"],
                        },
                        resolved=list(raw.get("resolved_typenames") or ()),
                    )
                )
                continue
            out.extend(
                _index_rows(
                    source_id=ctx.source.id,
                    spec=spec,
                    url=url,
                    counts=dict(raw.get("counts") or {}),
                )
            )
            out.extend(
                _camera_rows(
                    ctx=ctx,
                    spec=spec,
                    members=list(raw.get("members") or ()),
                    url=url,
                )
            )
        return out


__all__ = [
    "CONNECTOR_NAME",
    "CONNECTOR_NAMES",
    "OgcWfsConnector",
    "assert_predicate_allowed",
    "capabilities_url",
    "enumerated_rows",
    "expanded_targets",
    "get_feature_url",
    "predicate_allowlist",
    "srs_axis_orders",
    "targets_for",
    "vocab",
    "vocab_version",
]
