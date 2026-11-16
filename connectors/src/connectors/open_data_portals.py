# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.69a — the international open-data portal connectors (ACQ-23a).

Three registered connectors over ONE committed vocabulary
(``open_data_portals_vocab``) and ONE committed inventory
(``open_data_portals_targets``, ``sig.open-data-portals-targets/1``):

* ``ckan_package_search`` — the CKAN Action API's ``package_search`` /
  ``package_show`` lanes. A ``package_search`` target fetches ONE declared
  bounded page (``?q=<query>&rows=<rows>``); a ``package_show`` target
  fetches the single named dataset record (``?id=<dataset_id>``). Each served
  package mints ONE ``open_data_dataset:`` subject carrying the dataset's own
  metadata (name, title, publisher organisation, licence id/title, declared
  jurisdiction + technology, ``metadata_modified`` as-of) and each declared
  resource mints ONE ``open_data_resource:`` pointer — the resource's URL and
  format, never its bytes (the resource contents are the file-reader lanes'
  business, and a pointer is never fetched content, P8-2). The search lane
  also emits ONE ``open_data_index:`` record carrying the served result
  count plus the declared truncation flag when the served total exceeds the
  declared page — never a fabricated "everything was enumerated" claim.

* ``opendatasoft_explore`` — the ODS v2 explore records API
  (``<portal_base>/api/explore/v2.1/catalog/datasets/<dataset_id>/records``).
  The camera-row lane of the family: each served record mints a
  ``traffic_camera:`` subject through the same ``CameraRegistryEntry`` emit
  ``dot_511`` uses (the parcel screen, the §19.4 tier transform, the
  PKG-07 declared-technology contract and the Part VIII denylist all ride
  the shared machinery — nothing is re-implemented here). A denied field
  NAME anywhere in the served row set fails the whole capture closed
  (F-330); a row missing its declared coordinate or a geometry drift fails
  the same way, never a redacted partial row.

* ``dataeuropa_hub_search`` — the data.europa.eu hub search API seat
  (I5-C348): ONE declared POST carrying the committed query body
  (``post_body`` is reviewed target data, exactly the USAspending pattern)
  enumerating matching catalogue datasets as ``open_data_dataset:`` records
  plus one ``open_data_index:`` count record — a family container seat:
  per-dataset publishers, never one guessed licence.

Every seat stays ``ingestion_permitted=false``; leg B (the first real wire)
is the operator's act under ING-GO-D (OP-26) — nothing here flips a row.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from functools import cache
from typing import Any
from urllib.parse import urlencode, urlsplit

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

_VOCAB_TABLE = "open_data_portals_vocab"
_TARGETS_TABLE = "open_data_portals_targets"
_SCHEMA = "sig.open-data-portals-vocab/1"
_TARGETS_SCHEMA = "sig.open-data-portals-targets/1"
_EVIDENCE_GENRE = "camera_registry"

CKAN_CONNECTOR = "ckan_package_search"
ODS_CONNECTOR = "opendatasoft_explore"
HUB_CONNECTOR = "dataeuropa_hub_search"
CONNECTOR_NAMES = frozenset({CKAN_CONNECTOR, ODS_CONNECTOR, HUB_CONNECTOR})

#: CKAN package fields that carry person-shaped contact metadata — never
#: read, never emitted; their NAMES are recorded on the dataset entity row
#: as ``excluded_fields`` so the dropped surface is legible (S5/F-330).
_PERSON_PACKAGE_KEYS = frozenset(
    {
        "author",
        "author_email",
        "maintainer",
        "maintainer_email",
        "creator_user_id",
        "contact_name",
        "contact_email",
        "contact_point",
    }
)


@cache
def vocab() -> dict[str, Any]:
    table = load_table(_VOCAB_TABLE)
    if str(table.get("schema") or "") != _SCHEMA:
        raise ValueError(f"open_data_portals vocabulary must be {_SCHEMA!r}")
    return table


def vocab_version() -> str:
    return str(vocab()["vocab_version"])


@cache
def predicate_allowlist() -> frozenset[str]:
    return frozenset(str(p) for p in vocab()["predicate_allowlist"])


def assert_predicate_allowed(predicate: str) -> str:
    if predicate not in predicate_allowlist():
        raise ValueError(
            f"predicate {predicate!r} is not in the open_data_portals allowlist "
            f"{sorted(predicate_allowlist())} (SIG-INGEST-033)"
        )
    return predicate


@cache
def target_table() -> list[dict[str, Any]]:
    table = load_table(_TARGETS_TABLE)
    if str(table.get("schema") or "") != _TARGETS_SCHEMA:
        raise ValueError(f"open_data_portals inventory must be {_TARGETS_SCHEMA!r}")
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


def targets_for(source_id: str, *, connector: str | None = None) -> list[dict[str, Any]]:
    out = [t for t in target_table() if str(t.get("source_id")) == source_id]
    if connector is not None:
        out = [t for t in out if str(t.get("connector")) == connector]
    return out


def portal_targets(source_id: str) -> list[dict[str, Any]]:
    """The expanded live targets for ``source_id`` — one bounded row per seat."""
    out: list[dict[str, Any]] = []
    for row in targets_for(source_id):
        kind = str(row.get("kind") or "")
        if kind == "package_search":
            url = f"{str(row['api_base']).rstrip('/')}/package_search?" + urlencode(
                {"q": str(row["query"]), "rows": str(int(row["rows"]))}
            )
        elif kind == "package_show":
            url = f"{str(row['api_base']).rstrip('/')}/package_show?" + urlencode(
                {"id": str(row["dataset_id"])}
            )
        elif kind == "ods_records":
            url = (
                f"{str(row['portal_base']).rstrip('/')}/api/explore/v2.1/catalog/"
                f"datasets/{str(row['dataset_id'])}/records?"
                + urlencode({"limit": str(int(row.get("limit") or 100))})
            )
        elif kind == "hub_search":
            url = str(row["search_url"])
        else:
            raise ValueError(f"open_data_portals target {row.get('id')!r} has kind {kind!r}")
        _assert_host(url, f"open_data_portals target {row.get('id')!r}")
        out.append(
            {
                "id": str(row["id"]),
                "url": url,
                "kind": str(row["kind"]),
                "target": dict(row),
                **({"post_body": dict(row["post_body"])} if "post_body" in row else {}),
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
        "extraction_method": "open_data_portal_json",
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


def _resource_pointer(
    *,
    source_id: str,
    license_spdx: str,
    dataset_subject: str,
    res: Mapping[str, Any],
    url: str,
    index: int,
) -> list[dict[str, Any]]:
    """One ``open_data_resource:`` pointer — the link, never the content."""
    res_id = str(res.get("id") or res.get("name") or f"resource-{index}").strip()
    res_url = str(res.get("url") or "").strip()
    if not res_url.startswith("https://"):
        return []
    fmt = str(res.get("format") or "").strip().lower()
    subject_id = f"open_data_resource:{source_id}:{_slug(res_id)}"
    ev = _evidence(url, index)
    entity = _stamp(
        {
            "record_kind": "open_data_resource",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("document"),
            "external_id": res_id,
            "raw_value": res_url,
            "resource_format": fmt,
            "dataset_subject": dataset_subject,
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
            "document",
            res_url,
            res_url,
            ev,
            source_id=source_id,
            license_spdx=license_spdx,
        )
    )
    name = str(res.get("name") or "").strip()
    if name:
        rows.append(
            _claim(
                subject_id,
                "title",
                name,
                name,
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    rows.append(
        _claim(
            subject_id,
            "external_id",
            res_id,
            res_id,
            ev,
            source_id=source_id,
            license_spdx=license_spdx,
        )
    )
    return rows


def _dataset_rows(
    *,
    source_id: str,
    license_spdx: str,
    pkg: Mapping[str, Any],
    target: Mapping[str, Any],
    url: str,
    index: int,
) -> list[dict[str, Any]]:
    """One ``open_data_dataset:`` subject + its resource pointer records."""
    name = str(pkg.get("name") or pkg.get("id") or "").strip()
    if not name:
        return []
    raw_title = pkg.get("title")
    if isinstance(raw_title, Mapping):
        # Localised title objects ({en: "…"}) — take the first served value.
        title = next((str(v) for v in raw_title.values() if str(v).strip()), "")
    else:
        title = str(raw_title or "")
    subject_id = f"open_data_dataset:{source_id}:{_slug(name)}"
    ev = _evidence(url, index)
    org = pkg.get("organization")
    publisher = (
        str(org.get("title") or org.get("name") or "").strip()
        if isinstance(org, Mapping)
        else str(target.get("publisher") or "").strip()
    )
    excluded = sorted(k for k in pkg if str(k) in _PERSON_PACKAGE_KEYS)
    license_id = str(pkg.get("license_id") or "").strip()
    license_title = str(pkg.get("license_title") or "").strip()
    resources = [r for r in (pkg.get("resources") or ()) if isinstance(r, Mapping)]
    entity = _stamp(
        {
            "record_kind": "open_data_dataset",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("portal_index"),
            "external_id": name,
            "raw_value": name,
            "title": title.strip(),
            "publisher_label": publisher,
            "dataset_license_id": license_id,
            "dataset_license_title": license_title,
            "resource_count": len(resources),
            "excluded_fields": excluded,
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
            name,
            name,
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
    if publisher:
        rows.append(
            _claim(
                subject_id,
                "published_by",
                publisher,
                publisher,
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    jurisdiction = str(target.get("jurisdiction") or "").strip()
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
    technology = str(target.get("technology") or "").strip()
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
    modified = str(pkg.get("metadata_modified") or pkg.get("revision_timestamp") or "").strip()
    if modified:
        rows.append(
            _claim(
                subject_id,
                "as_of",
                modified,
                modified,
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    for i, res in enumerate(resources):
        rows.extend(
            _resource_pointer(
                source_id=source_id,
                license_spdx=license_spdx,
                dataset_subject=subject_id,
                res=res,
                url=url,
                index=i,
            )
        )
    return rows


def _index_rows(
    *,
    source_id: str,
    license_spdx: str,
    target: Mapping[str, Any],
    url: str,
    count: int,
    returned: int,
) -> list[dict[str, Any]]:
    """The search lane's ``open_data_index:`` record — served total + truncation."""
    subject_id = f"open_data_index:{source_id}:{str(target.get('id'))}"
    ev = _evidence(url, 0)
    entity = _stamp(
        {
            "record_kind": "open_data_index",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("portal_index"),
            "external_id": str(target.get("id")),
            "raw_value": str(target.get("id")),
            "query": str(target.get("query") or target.get("search_url") or ""),
            "result_count": count,
            "returned_count": returned,
            "truncated": returned < count,
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
            entity["external_id"],
            entity["external_id"],
            ev,
            source_id=source_id,
            license_spdx=license_spdx,
        )
    )
    return rows


def _require_json(ctx: RunContext, capture: CaptureRef, kind: str) -> Any:
    data = ctx.captures.get(capture.digest)
    try:
        doc = json.loads(data)
    except (ValueError, TypeError) as exc:
        head = data[:64] if isinstance(data, (bytes, bytearray)) else str(data)[:64]
        raise ContentDrift(
            ctx.source.id,
            f"{kind} endpoint returned non-JSON content ({len(data)} bytes; starts {head!r})",
        ) from exc
    if not isinstance(doc, Mapping):
        raise ContentDrift(
            ctx.source.id, f"{kind} payload is not an object (got {type(doc).__name__})"
        )
    return doc


def _packages_from(
    doc: Mapping[str, Any], kind: str, ctx: RunContext
) -> tuple[list[Mapping[str, Any]], int]:
    """The served package list + the declared total (fail closed on drift)."""
    if kind in {"package_search", "package_show"}:
        if doc.get("success") is not True:
            raise ContentDrift(
                ctx.source.id, "the CKAN envelope's success flag is not true — an error envelope"
            )
        result = doc.get("result")
        if not isinstance(result, Mapping):
            raise ContentDrift(ctx.source.id, "the CKAN envelope carries no 'result' object")
        if kind == "package_show":
            return [result], 1
        results = result.get("results")
        if not isinstance(results, list):
            raise ContentDrift(
                ctx.source.id, "the CKAN package_search result carries no 'results' array"
            )
        try:
            count = int(str(result.get("count")))
        except (TypeError, ValueError):
            raise ContentDrift(
                ctx.source.id, "the CKAN package_search result lacks an integer 'count'"
            ) from None
        return [p for p in results if isinstance(p, Mapping)], count
    if kind == "hub_search":
        result = doc.get("result")
        if not isinstance(result, Mapping):
            raise ContentDrift(ctx.source.id, "the hub search payload carries no 'result' object")
        results = result.get("results")
        if not isinstance(results, list):
            raise ContentDrift(ctx.source.id, "the hub search result carries no 'results' array")
        raw_count = result.get("count")
        try:
            total = int(str(raw_count)) if raw_count is not None else len(results)
        except (TypeError, ValueError):
            raise ContentDrift(
                ctx.source.id, "the hub search result's 'count' is not an integer"
            ) from None
        return [p for p in results if isinstance(p, Mapping)], total
    raise ContentDrift(ctx.source.id, f"target kind {kind!r} has no package lane")


def _ods_camera_rows(
    *,
    ctx: RunContext,
    target: Mapping[str, Any],
    records: Sequence[Mapping[str, Any]],
    url: str,
) -> list[dict[str, Any]]:
    """The ODS record lane — ``traffic_camera:`` rows via the shared emit."""
    source_id = ctx.source.id
    license_spdx = str(target.get("license_spdx") or "")
    sensitivity_class = str(target.get("sensitivity_class") or vocab()["default_sensitivity_class"])
    sig = declared_parcel_signal()
    out: list[dict[str, Any]] = []
    for i, rec in enumerate(records):
        field_names = sorted(str(k) for k in rec)
        for name in field_names:
            term = denied_match(name)
            if term is not None:
                raise ContentDrift(
                    source_id,
                    f"the ODS record set publishes denied field {name!r} "
                    f"(denied {term!r}) — a Part VIII field the lane refuses "
                    "by name (F-330)",
                )
        point = rec.get("geo_point_2d")
        lat: float | None = None
        lon: float | None = None
        coord_source = "geo_point_2d"
        if isinstance(point, Mapping):
            try:
                lon = float(str(point.get("lon")))
                lat = float(str(point.get("lat")))
            except (TypeError, ValueError):
                lat = lon = None
        else:
            lat_field = str(target.get("lat_field") or "").strip()
            lon_field = str(target.get("lon_field") or "").strip()
            if lat_field and lon_field:
                coord_source = f"fields:{lat_field},{lon_field}"
                try:
                    lat = float(str(rec.get(lat_field)))
                    lon = float(str(rec.get(lon_field)))
                except (TypeError, ValueError):
                    lat = lon = None
        ref_field = str(target.get("ref_field") or "").strip()
        if ref_field:
            ref = str(rec.get(ref_field) or "").strip()
            if not ref:
                raise ContentDrift(
                    source_id,
                    f"declared ref_field {ref_field!r} is absent or empty on record {i}",
                )
        else:
            ref = f"r{i}"
        if lat is None or lon is None or not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ContentDrift(
                source_id,
                f"ODS record {i} ({ref!r}) carries no valid published coordinate "
                f"({coord_source}) — the lane never emits a guessed point",
            )
        verdict = screen_point(lat, lon, signal=sig)
        parcel_screen = verdict.value
        residential_flag = False
        cls_value = sensitivity_class
        if verdict is ParcelScreenVerdict.INTERSECTS:
            cls_value = demote_for_residential_parcel(SensitivityClass(cls_value), True).value
            lat = lon = None
            residential_flag = True
            tier = 3
            pub_lat = pub_lon = None
        else:
            pub_lat, pub_lon, tier = publishable_coordinate(lat, lon, cls_value)
            lat, lon = pub_lat, pub_lon
        entry = CameraRegistryEntry(
            camera_ref=ref,
            source_id=source_id,
            target_id=str(target.get("id")),
            state=str(target.get("state") or ""),
            agency=str(target.get("publisher") or ""),
            latitude=lat,
            longitude=lon,
            coordinate_source=coord_source,
            geo_tier=tier,
            sensitivity_class=cls_value,
            license_spdx=license_spdx,
            technology=str(target.get("technology") or ""),
            record_kind=declared_record_kind(target),
            name=(
                str(rec.get(str(target["name_field"]))).strip()
                if str(target.get("name_field") or "").strip()
                and str(rec.get(str(target["name_field"])) or "").strip()
                else None
            ),
            jurisdiction_scheme=str(target.get("jurisdiction_scheme") or "iso.3166_2"),
            extraction_method="opendatasoft_records_json",
            excluded_fields=tuple(n for n in field_names if n not in _ods_used_fields(target)),
            residential_parcel_flag=residential_flag,
            parcel_screen=parcel_screen,
            parcel_screen_signal=sig.stamp,
            axis_order="lon-lat",
        )
        retrieved = datetime.now(UTC).isoformat()
        out.extend(entry.claim_rows(url, retrieved, i))
    return out


def _ods_used_fields(target: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(
        f
        for f in (
            "geo_point_2d",
            str(target.get("ref_field") or ""),
            str(target.get("lat_field") or ""),
            str(target.get("lon_field") or ""),
            str(target.get("name_field") or ""),
        )
        if f
    )


def _ods_dataset_rows(
    *,
    source_id: str,
    target: Mapping[str, Any],
    url: str,
    total: int,
) -> list[dict[str, Any]]:
    """The ODS seat's declared dataset record — the catalogue-level anchor."""
    license_spdx = str(target.get("license_spdx") or "")
    subject_id = f"open_data_dataset:{source_id}:{_slug(str(target.get('dataset_id')))}"
    ev = _evidence(url, 0)
    entity = _stamp(
        {
            "record_kind": "open_data_dataset",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("portal_index"),
            "external_id": str(target.get("dataset_id")),
            "raw_value": str(target.get("dataset_id")),
            "title": str(target.get("title") or ""),
            "publisher_label": str(target.get("publisher") or ""),
            "dataset_license_id": str(target.get("dataset_license_id") or ""),
            "served_record_total": total,
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
            entity["external_id"],
            entity["external_id"],
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
    jurisdiction = str(target.get("jurisdiction") or "").strip()
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
    technology = str(target.get("technology") or "").strip()
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
    return rows


class _PortalConnector(Connector):
    """Shared eight-stage lane for the three open-data portal connectors."""

    connector_name = ""
    version = "1.0.0"
    ingestion_mode = "rest_api"
    incrementality = "re-issue detection via content-addressed capture digests"
    name = ""

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        targets = list(ctx.parameters.get("targets", []))
        if targets:
            return targets
        return [dict(t) for t in portal_targets(ctx.source.id)]

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """ONE polite request through the shared layer — the only egress.

        A ``post_body`` on the reviewed target makes the request a POST (the
        USAspending pattern: reviewed data, never content) — the hub-search
        seat's declared query body travels this way.
        """
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        body = target.get("post_body")
        if body is not None:
            return ctx.fetcher.fetch(
                str(target["url"]),
                headers={"Content-Type": "application/json"},
                body=json.dumps(body, sort_keys=True).encode("utf-8"),
            )
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        target = _resolve(ctx, capture.source_uri)
        spec = dict(target.get("target") or target)
        kind = str(spec.get("kind") or "")
        doc = _require_json(ctx, capture, kind or "portal")
        if kind == "ods_records":
            total = doc.get("total_count")
            results = doc.get("results")
            if not isinstance(results, list):
                raise ContentDrift(
                    ctx.source.id, "the ODS records payload lacks the 'results' array"
                )
            if not all(isinstance(r, Mapping) for r in results):
                raise ContentDrift(ctx.source.id, "an ODS result row is not an object")
            try:
                total_i = int(str(total)) if total is not None else len(results)
            except (TypeError, ValueError):
                raise ContentDrift(
                    ctx.source.id, "the ODS records payload's 'total_count' is not an integer"
                ) from None
            declared_bound = int(spec.get("limit") or 100)
            if len(results) > declared_bound:
                raise ContentDrift(
                    ctx.source.id,
                    f"the ODS records page carries {len(results)} rows over the "
                    f"declared bound {declared_bound}",
                )
            return {
                "kind": "ods_records",
                "payload": {"total_count": total_i, "results": list(results)},
                "capture": capture,
                "target": spec,
            }
        packages, count = _packages_from(doc, kind, ctx)
        return {
            "kind": kind,
            "payload": {"packages": packages, "count": count},
            "capture": capture,
            "target": spec,
        }

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        spec = dict(parsed.get("target") or {})
        kind = str(parsed.get("kind") or "")
        if kind == "ods_records":
            return [
                {
                    "record_kind": "ods_records_page",
                    "total_count": int(parsed["payload"]["total_count"]),
                    "results": list(parsed["payload"]["results"]),
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
                "record_kind": "portal_package_page",
                "packages": list(parsed["payload"]["packages"]),
                "count": int(parsed["payload"]["count"]),
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
            target = dict(raw.get("target") or {})
            url = str(raw.get("source_uri") or "")
            license_spdx = str(target.get("license_spdx") or "")
            if raw.get("record_kind") == "ods_records_page":
                out.extend(
                    _ods_dataset_rows(
                        source_id=ctx.source.id,
                        target=target,
                        url=url,
                        total=int(raw["total_count"]),
                    )
                )
                out.extend(
                    _ods_camera_rows(
                        ctx=ctx,
                        target=target,
                        records=list(raw.get("results") or ()),
                        url=url,
                    )
                )
                continue
            packages = list(raw.get("packages") or ())
            count = int(raw.get("count") or len(packages))
            if str(target.get("kind")) in {"package_search", "hub_search"}:
                out.extend(
                    _index_rows(
                        source_id=ctx.source.id,
                        license_spdx=license_spdx,
                        target=target,
                        url=url,
                        count=count,
                        returned=len(packages),
                    )
                )
            bound = int(target.get("rows") or target.get("limit") or len(packages))
            if len(packages) > bound:
                raise ContentDrift(
                    ctx.source.id,
                    f"the served page carries {len(packages)} packages over the "
                    f"declared bound {bound}",
                )
            for i, pkg in enumerate(packages):
                out.extend(
                    _dataset_rows(
                        source_id=ctx.source.id,
                        license_spdx=license_spdx,
                        pkg=pkg,
                        target=target,
                        url=url,
                        index=i,
                    )
                )
        return out


def _resolve(ctx: RunContext, source_uri: str) -> dict[str, Any]:
    """The run-time target a capture was fetched from (exact-URL match)."""
    for t in ctx.parameters.get("targets", []):
        if str(t.get("url")) == source_uri:
            return dict(t)
    for t in ctx.parameters.get("targets", []):
        spec = t.get("target") or {}
        base = str(spec.get("api_base") or spec.get("portal_base") or "\x00")
        if source_uri.startswith(base):
            return dict(t)
    rows = targets_for(ctx.source.id)
    return {"id": str(rows[0]["id"]), "target": dict(rows[0])} if rows else {}


@register
class CkanPackageSearchConnector(_PortalConnector):
    """CKAN ``package_search`` / ``package_show`` dataset+pointer lane."""

    name = CKAN_CONNECTOR


@register
class OpendatasoftExploreConnector(_PortalConnector):
    """ODS v2 explore records lane — camera rows via the shared emit."""

    name = ODS_CONNECTOR


@register
class DataeuropaHubSearchConnector(_PortalConnector):
    """data.europa.eu hub-search dataset-enumeration lane."""

    name = HUB_CONNECTOR


__all__ = [
    "CKAN_CONNECTOR",
    "CONNECTOR_NAMES",
    "CkanPackageSearchConnector",
    "DataeuropaHubSearchConnector",
    "HUB_CONNECTOR",
    "ODS_CONNECTOR",
    "OpendatasoftExploreConnector",
    "assert_predicate_allowed",
    "enumerated_rows",
    "portal_targets",
    "predicate_allowlist",
    "targets_for",
    "vocab",
    "vocab_version",
]
