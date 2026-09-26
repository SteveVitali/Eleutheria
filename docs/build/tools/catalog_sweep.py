#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P26.13 (SOURCES.12) — open-data-catalog surveillance-dataset sweep.

Enumerates surveillance-relevant datasets across three public catalog
discovery APIs, writes the committed enumeration artifact under
``docs/build/reports/``, then (``qualify``) probes each candidate's metadata
to classify it as camera-registry-shaped (point features with camera fields
— the ``dot_511``/``socrata_rows`` connector path) vs a non-target, recording
the verbatim licence metadata and the observed row count for each row.

Catalogs queried (the ticket's set):

* **Socrata catalog** — ``api.us.socrata.com/api/catalog/v1`` (``q`` full-text
  + ``limit``/``offset`` pagination; ``metadata.domain`` names the portal).
* **ArcGIS Hub search** — ``hub.arcgis.com/api/search/v1/collections/all/items``
  (``q`` + ``startindex`` pagination; item ``properties`` carry
  ``licenseInfo``/``accessInformation`` verbatim).
* **CKAN** — ``ckan.publishing.service.gov.uk/api/3/action/package_search``
  (data.gov.uk's CKAN API; ``license_id``/``license_title`` + resource URLs).

Keyword set (the ticket's, verbatim): camera, cctv, traffic camera, alpr,
license plate, surveillance, public safety camera.

Usage::

    python3 docs/build/tools/catalog_sweep.py enumerate [--date YYYY-MM-DD]
    python3 docs/build/tools/catalog_sweep.py qualify [--date YYYY-MM-DD]
    python3 docs/build/tools/catalog_sweep.py review [--date YYYY-MM-DD]
    python3 docs/build/tools/catalog_sweep.py retry [--date YYYY-MM-DD] [--apply]

``enumerate`` writes ``docs/build/reports/catalog_sweep_<date>.json`` (every
candidate dataset: id/portal/title/licence/endpoint + the schema hints needed
for qualification). ``qualify`` re-reads that artifact, probes each
candidate's live metadata, and writes
``docs/build/reports/catalog_sweep_<date>_qualified.json`` adding ``shape``
(camera_registry|non_target|error), ``licence_verbatim``, ``spdx`` (resolved
or None), ``observed_count``, and ``blocker`` rows. ``review`` is the offline
second pass over the qualified artifact: the schema/title heuristics
over-admit (public-health "surveillance" tables carry a geolocation column;
enforcement-violation and ALPR-read datasets are point-shaped but are not
registries), so each camera_registry row is re-checked against the
title-level non-registry patterns below, Socrata dict-form licences are
re-parsed, hand-verified licence resolutions are applied, and every override
is recorded in ``review_decisions``. All artifacts are append-only records —
re-run writes a new dated file, never edits one.
"""

from __future__ import annotations

import ast
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[3]
REPORTS = REPO / "docs" / "build" / "reports"

#: The ticket's keyword set, verbatim.
KEYWORDS = [
    "camera",
    "cctv",
    "traffic camera",
    "alpr",
    "license plate",
    "surveillance",
    "public safety camera",
]

UA = "sig-catalog-sweep/1.0 (https://github.com/SteveVitali/Eleutheria; registry-enumeration)"

# ArcGIS item types that can back a camera registry (feature/map services).
_ARCGIS_DATA_TYPES = {"Feature Service", "Feature Layer", "Map Service"}

#: Camera-registry content signals on a dataset title/description/fields.
#: A candidate must match one of these AND carry point geometry to qualify.
_CONTENT_TERMS = (
    "camera",
    "cctv",
    "alpr",
    "license plate",
    "licence plate",
    "speed cam",
    "red light",
    "red-light",
    "traffic safety",
    "photo radar",
    "photo enforcement",
    "automated enforcement",
    "surveillance",
    "webcam",
    "jamcam",
)

#: Aggregate/non-registry title signals — documents, stats, dashboards.
_NON_REGISTRY_TERMS = (
    "annual report",
    "budget",
    "collision",
    "complaint",
    "crime",
    "dashboard",
    "district data",
    "election",
    "enforcement actions",
    "foia",
    "incident",
    "injur",
    "offense",
    "permit",
    "policy",
    "request",
    "salary",
    "shotspotter",
    "stats",
    "stop data",
    "survey",
    "use of force",
    "vehicle crash",
    "911",
)

#: Socrata datatype names that prove a point/lat-lon registry shape.
_SOCRATA_POINT_TYPES = {"point", "location", "multipoint", "line", "polygon"}

#: Verbatim licence strings → SPDX. Conservative: only strings that are
#: unambiguous open-data grants resolve; everything else stays gated
#: (GL-GATE-06 flips only clear-licence rows).
_LICENCE_MAP = [
    # (lowercase substring, spdx) — first match wins, most specific first.
    ("public domain", "CC0-1.0"),
    ("cc0", "CC0-1.0"),
    ("cc-zero", "CC0-1.0"),
    ("pddl", "PDDL-1.0"),
    ("open data commons public domain", "PDDL-1.0"),
    ("open government licence - canada", "OGL-Canada-2.0"),
    ("open government license - canada", "OGL-Canada-2.0"),
    ("open government licence - city of ottawa", "LicenseRef-Ottawa-ODL-2.0"),
    ("open government licence", "OGL-3.0"),
    ("open government license", "OGL-3.0"),
    ("uk-ogl", "OGL-3.0"),
    ("ogl", None),  # bare "OGL" is ambiguous — gated
    ("creative commons attribution 4.0", "CC-BY-4.0"),
    ("creative commons attribution 3.0", "CC-BY-3.0"),
    ("cc-by-4.0", "CC-BY-4.0"),
    ("cc-by-3.0", "CC-BY-3.0"),
    ("cc by 4.0", "CC-BY-4.0"),
    ("cc by 3.0", "CC-BY-3.0"),
    ("cc-by-sa-4.0", "CC-BY-SA-4.0"),
    ("cc-by-sa-2.0", "CC-BY-SA-2.0"),
    ("licence ouverte", "LicenceOuverte-2.0"),
    ("odbl", "ODbL-1.0"),
    ("open database license", "ODbL-1.0"),
]

#: CKAN licence ids → SPDX (data.gov.uk / ODL registry ids).
_CKAN_LICENCE_MAP = {
    "uk-ogl": "OGL-3.0",
    "OGL-UK-3.0": "OGL-3.0",
    "ogl": "OGL-3.0",
    "cc-by": "CC-BY-4.0",
    "cc-by-4.0": "CC-BY-4.0",
    "cc-by-3.0": "CC-BY-3.0",
    "cc-zero": "CC0-1.0",
    "CC0": "CC0-1.0",
    "odc-pddl": "PDDL-1.0",
    "odc-by": "ODC-BY-1.0",
    "odc-odbl": "ODbL-1.0",
    "other-pd": "CC0-1.0",
    "other-open": None,  # ambiguous — gated
    "other-nc": None,
    "notspecified": None,
    "": None,
}


def _get(url: str, *, timeout: float = 30.0, delay: float = 0.25) -> bytes:
    """GET ``url`` with the tool UA + a politeness delay; return the body."""
    time.sleep(delay)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (public APIs)
        return resp.read()


def _get_json(url: str, **kw: Any) -> Any:
    return json.loads(_get(url, **kw))


# --- enumeration -------------------------------------------------------------


def _socrata_rows(now: str) -> list[dict[str, Any]]:
    """Socrata catalog rows for the keyword set (type=dataset only)."""
    seen: dict[str, dict[str, Any]] = {}
    for kw in KEYWORDS:
        offset = 0
        while True:
            q = urllib.parse.urlencode({"q": kw, "limit": 100, "offset": offset})
            doc = _get_json(f"https://api.us.socrata.com/api/catalog/v1?{q}")
            results = doc.get("results") or []
            for r in results:
                res = r.get("resource") or {}
                if str(res.get("type")) != "dataset":
                    continue
                meta = r.get("metadata") or {}
                domain = str(meta.get("domain") or "")
                ds_id = str(res.get("id") or "")
                if not domain or not ds_id:
                    continue
                key = f"{domain}:{ds_id}"
                row = seen.setdefault(
                    key,
                    {
                        "catalog": "socrata",
                        "portal": domain,
                        "id": ds_id,
                        "title": str(res.get("name") or ""),
                        "licence": str(meta.get("license") or ""),
                        "endpoint": f"https://{domain}/resource/{ds_id}.json",
                        "permalink": str(r.get("permalink") or ""),
                        "attribution": str(res.get("attribution") or ""),
                        "download_count": int(res.get("download_count") or 0),
                        "columns_field_name": list(res.get("columns_field_name") or []),
                        "columns_datatype": [str(x) for x in (res.get("columns_datatype") or [])],
                        "keywords": [],
                    },
                )
                if kw not in row["keywords"]:
                    row["keywords"].append(kw)
            total = int(doc.get("resultSetSize") or 0)
            offset += len(results)
            if offset >= total or not results:
                break
    return sorted(seen.values(), key=lambda r: (r["portal"], r["id"]))


def _arcgis_rows(now: str) -> list[dict[str, Any]]:
    """ArcGIS Hub search rows for the keyword set (service items only)."""
    seen: dict[str, dict[str, Any]] = {}
    for kw in KEYWORDS:
        startindex = 1
        while True:
            q = urllib.parse.urlencode({"q": kw, "limit": 100, "startindex": startindex})
            doc = _get_json(f"https://hub.arcgis.com/api/search/v1/collections/all/items?{q}")
            features = doc.get("features") or []
            for f in features:
                props = f.get("properties") or {}
                if str(props.get("type")) not in _ARCGIS_DATA_TYPES:
                    continue
                item_id = str(props.get("id") or "")
                if not item_id:
                    continue
                url = str(props.get("url") or "")
                host = urllib.parse.urlsplit(url).netloc or "arcgis.com"
                row = seen.setdefault(
                    item_id,
                    {
                        "catalog": "arcgis_hub",
                        "portal": host,
                        "id": item_id,
                        "title": str(props.get("title") or ""),
                        "licence": str(
                            props.get("licenseInfo")
                            or props.get("license")
                            or props.get("accessInformation")
                            or ""
                        ),
                        "endpoint": url,
                        "permalink": f"https://www.arcgis.com/home/item.html?id={item_id}",
                        "attribution": str(props.get("accessInformation") or ""),
                        "owner": str(props.get("owner") or ""),
                        "org_id": str(props.get("orgId") or ""),
                        "item_type": str(props.get("type") or ""),
                        "keywords": [],
                    },
                )
                if kw not in row["keywords"]:
                    row["keywords"].append(kw)
            matched = int(doc.get("numberMatched") or 0)
            returned = int(doc.get("numberReturned") or len(features))
            startindex += returned
            if startindex > matched or returned <= 0 or startindex > 500:
                break
    return sorted(seen.values(), key=lambda r: (r["portal"], r["id"]))


def _ckan_rows(now: str) -> list[dict[str, Any]]:
    """data.gov.uk CKAN package_search rows for the keyword set."""
    host = "ckan.publishing.service.gov.uk"
    seen: dict[str, dict[str, Any]] = {}
    for kw in KEYWORDS:
        start = 0
        while True:
            q = urllib.parse.urlencode({"q": kw, "rows": 100, "start": start})
            doc = _get_json(f"https://{host}/api/3/action/package_search?{q}")
            result = doc.get("result") or {}
            results = result.get("results") or []
            for pkg in results:
                name = str(pkg.get("name") or "")
                if not name:
                    continue
                resources = [
                    {
                        "url": str(r.get("url") or ""),
                        "format": str(r.get("format") or ""),
                        "name": str(r.get("name") or ""),
                    }
                    for r in (pkg.get("resources") or [])
                ]
                row = seen.setdefault(
                    name,
                    {
                        "catalog": "ckan_data_gov_uk",
                        "portal": host,
                        "id": name,
                        "title": str(pkg.get("title") or ""),
                        "licence": str(pkg.get("license_id") or pkg.get("license_title") or ""),
                        "licence_title": str(pkg.get("license_title") or ""),
                        "endpoint": f"https://{host}/dataset/{name}",
                        "permalink": str(pkg.get("url") or ""),
                        "attribution": str((pkg.get("organization") or {}).get("title") or ""),
                        "resources": resources,
                        "keywords": [],
                    },
                )
                if kw not in row["keywords"]:
                    row["keywords"].append(kw)
            count = int(result.get("count") or 0)
            start += len(results)
            if start >= count or not results:
                break
    return sorted(seen.values(), key=lambda r: r["id"])


def cmd_enumerate(date: str) -> int:
    """Query all three catalogs and write the enumeration artifact."""
    now = datetime.now(UTC).isoformat()
    print("enumerating socrata catalog …", file=sys.stderr)
    socrata = _socrata_rows(now)
    print(f"  {len(socrata)} datasets", file=sys.stderr)
    print("enumerating arcgis hub …", file=sys.stderr)
    arcgis = _arcgis_rows(now)
    print(f"  {len(arcgis)} service items", file=sys.stderr)
    print("enumerating ckan data.gov.uk …", file=sys.stderr)
    ckan = _ckan_rows(now)
    print(f"  {len(ckan)} packages", file=sys.stderr)

    artifact = {
        "artifact": "catalog_sweep",
        "ticket": "P26.13 / SOURCES.12",
        "retrieved_at": now,
        "catalogs": {
            "socrata": "https://api.us.socrata.com/api/catalog/v1",
            "arcgis_hub": "https://hub.arcgis.com/api/search/v1/collections/all/items",
            "ckan_data_gov_uk": "https://ckan.publishing.service.gov.uk/api/3/action/package_search",
        },
        "keywords": list(KEYWORDS),
        "counts": {
            "socrata": len(socrata),
            "arcgis_hub": len(arcgis),
            "ckan_data_gov_uk": len(ckan),
            "total": len(socrata) + len(arcgis) + len(ckan),
        },
        "datasets": socrata + arcgis + ckan,
    }
    path = REPORTS / f"catalog_sweep_{date}.json"
    path.write_text(json.dumps(artifact, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(artifact['datasets'])} datasets)", file=sys.stderr)
    return 0


# --- qualification ------------------------------------------------------------


def _licence_to_spdx(licence: str, licence_title: str = "", catalog: str = "") -> str | None:
    """Resolve a verbatim licence string to SPDX, or None (ambiguous → gated)."""
    if catalog == "ckan_data_gov_uk":
        lid = licence.strip()
        if lid in _CKAN_LICENCE_MAP:
            return _CKAN_LICENCE_MAP[lid]
        for cand in (lid, licence_title):
            low = cand.lower()
            for needle, spdx in _LICENCE_MAP:
                if needle in low:
                    return spdx
        return None
    low = licence.lower().strip()
    if not low:
        return None
    for needle, spdx in _LICENCE_MAP:
        if needle in low:
            return spdx
    return None


def _content_signal(row: dict[str, Any]) -> bool:
    """Whether the TITLE describes camera-registry content.

    Only the dataset title is tested — the matched search keywords always
    contain a camera term by construction, so they can never discriminate.
    """
    hay = str(row.get("title") or "").lower()
    return any(t in hay for t in _CONTENT_TERMS)


def _non_registry(row: dict[str, Any]) -> str:
    """A non-registry reason if the title reads as documents/stats."""
    title = str(row.get("title") or "").lower()
    for t in _NON_REGISTRY_TERMS:
        if t in title:
            return f"non_registry_title:{t.strip()}"
    return ""


def _socrata_shape(row: dict[str, Any]) -> tuple[str, str]:
    """Classify a Socrata candidate from its catalog column schema."""
    types = {str(t).lower() for t in row.get("columns_datatype") or []}
    if not _content_signal(row):
        return ("non_target", "content: no camera/surveillance signal in title/keywords")
    if not types & {"point", "location"}:
        return ("non_target", "shape: no Point/Location column (not a point registry)")
    return ("camera_registry", "")


def _socrata_probe(row: dict[str, Any]) -> dict[str, Any]:
    """Live count + licence confirmation for a Socrata candidate."""
    domain, ds_id = row["portal"], row["id"]
    out: dict[str, Any] = {}
    try:
        count_doc = _get_json(
            f"https://{domain}/resource/{ds_id}.json?$select=count(*)",
        )
        out["observed_count"] = int(count_doc[0].get("count") or 0)
    except Exception as exc:  # noqa: BLE001 — probe failures are recorded
        out["probe_error"] = f"count: {type(exc).__name__} {exc}"
        out["observed_count"] = 0
    try:
        views = _get_json(f"https://{domain}/api/views/{ds_id}.json")
        out["licence_verbatim"] = str(views.get("license") or row.get("licence") or "")
        out["attribution_verbatim"] = str(views.get("attribution") or row.get("attribution") or "")
    except Exception as exc:  # noqa: BLE001
        out["licence_verbatim"] = str(row.get("licence") or "")
        out.setdefault("probe_error", f"views: {type(exc).__name__} {exc}")
    return out


def _arcgis_layers(service_url: str) -> list[dict[str, Any]]:
    """The published layer stubs of an ArcGIS Feature/Map service root."""
    root = service_url.rstrip("/")
    doc = _get_json(f"{root}?f=json")
    return list(doc.get("layers") or [])


def _arcgis_layer_meta(layer_url: str) -> dict[str, Any]:
    """Layer metadata: geometry type, fields, oid field."""
    return _get_json(f"{layer_url.rstrip('/')}?f=json")


def _arcgis_count(layer_url: str) -> int:
    q = urllib.parse.urlencode({"where": "1=1", "returnCountOnly": "true", "f": "json"})
    doc = _get_json(f"{layer_url.rstrip('/')}/query?{q}")
    if isinstance(doc, dict) and isinstance(doc.get("count"), int):
        return int(doc["count"])
    raise ValueError(f"unexpected count payload: {str(doc)[:120]}")


def _arcgis_item(item_id: str) -> dict[str, Any]:
    """The ArcGIS Online item record (licence text, owner)."""
    q = urllib.parse.urlencode({"f": "json"})
    return _get_json(f"https://www.arcgis.com/sharing/rest/content/items/{item_id}?{q}")


def _pick_camera_layer(layers: list[dict[str, Any]], title: str) -> dict[str, Any] | None:
    """The camera-named layer of a service, else the single layer, else None."""
    if len(layers) == 1:
        return layers[0]
    cam = [
        layer
        for layer in layers
        if any(
            t in str(layer.get("name") or "").lower()
            for t in ("camera", "cctv", "alpr", "red light", "speed")
        )
    ]
    return cam[0] if cam else None


def _arcgis_probe(row: dict[str, Any]) -> dict[str, Any]:
    """Layer resolution + count + licence for an ArcGIS Hub candidate."""
    out: dict[str, Any] = {}
    url = str(row.get("endpoint") or "").rstrip("/")
    if not url:
        out["probe_error"] = "no service url"
        return out
    try:
        if url.endswith("/query"):
            url = url[: -len("/query")]
        if url.split("/")[-1].isdigit():
            layer_url = url
        else:
            layers = _arcgis_layers(url)
            pick = _pick_camera_layer(layers, str(row.get("title") or ""))
            if pick is None:
                out["probe_error"] = f"no camera-named layer among {len(layers)} service layers"
                return out
            layer_url = f"{url}/{pick['id']}"
            out["picked_layer"] = str(pick.get("name") or "")
        meta = _arcgis_layer_meta(layer_url)
        out["layer_url"] = layer_url
        out["geometry_type"] = str(meta.get("geometryType") or "")
        out["layer_name"] = str(meta.get("name") or "")
        fields = [str(f.get("name")) for f in (meta.get("fields") or [])]
        out["observed_fields"] = fields
        oid = str(meta.get("objectIdField") or "")
        out["object_id_field"] = oid or next(
            (f for f in fields if f.lower() in ("objectid", "fid", "esri_oid", "oid", "object_id")),
            "",
        )
        try:
            out["observed_count"] = _arcgis_count(layer_url)
        except Exception as exc:  # noqa: BLE001
            out["probe_error"] = f"count: {type(exc).__name__} {exc}"
            out["observed_count"] = 0
    except Exception as exc:  # noqa: BLE001
        out["probe_error"] = f"service: {type(exc).__name__} {exc}"
        return out
    try:
        item = _arcgis_item(row["id"])
        out["licence_verbatim"] = str(
            item.get("licenseInfo") or item.get("accessInformation") or row.get("licence") or ""
        )[:4000]
        out["item_owner"] = str(item.get("owner") or row.get("owner") or "")
    except Exception as exc:  # noqa: BLE001
        out["licence_verbatim"] = str(row.get("licence") or "")[:4000]
        out.setdefault("probe_error", f"item: {type(exc).__name__} {exc}")
    return out


def _ckan_probe(row: dict[str, Any]) -> dict[str, Any]:
    """Resolve a CKAN package's resources to a fetchable endpoint."""
    out: dict[str, Any] = {}
    arc = [
        r
        for r in (row.get("resources") or [])
        if "/FeatureServer" in r.get("url", "") or "/MapServer" in r.get("url", "")
    ]
    soc = [
        r
        for r in (row.get("resources") or [])
        if "/resource/" in r.get("url", "") and r.get("url", "").endswith(".json")
    ]
    out["licence_verbatim"] = str(row.get("licence_title") or row.get("licence") or "")
    if arc:
        out["resource_kind"] = "arcgis_query"
        out["resolved_url"] = arc[0]["url"]
        try:
            meta = _arcgis_layer_meta(arc[0]["url"].rstrip("/").rsplit("/query", 1)[0])
            layer_url = arc[0]["url"].rstrip("/").rsplit("/query", 1)[0]
            if not layer_url.split("/")[-1].isdigit():
                layers = _arcgis_layers(layer_url)
                pick = _pick_camera_layer(layers, str(row.get("title") or ""))
                if pick is None:
                    out["probe_error"] = "no camera-named layer"
                    return out
                layer_url = f"{layer_url}/{pick['id']}"
                meta = _arcgis_layer_meta(layer_url)
            out["layer_url"] = layer_url
            out["geometry_type"] = str(meta.get("geometryType") or "")
            out["observed_fields"] = [str(f.get("name")) for f in (meta.get("fields") or [])]
            out["object_id_field"] = str(meta.get("objectIdField") or "OBJECTID")
            try:
                out["observed_count"] = _arcgis_count(layer_url)
            except Exception as exc:  # noqa: BLE001
                out["probe_error"] = f"count: {type(exc).__name__} {exc}"
        except Exception as exc:  # noqa: BLE001
            out["probe_error"] = f"arcgis: {type(exc).__name__} {exc}"
        return out
    if soc:
        out["resource_kind"] = "socrata_rows"
        out["resolved_url"] = soc[0]["url"]
        return out
    out["resource_kind"] = "unsupported"
    out["probe_error"] = (
        "no ArcGIS REST or Socrata /resource endpoint among "
        f"{len(row.get('resources') or [])} resources "
        f"({sorted({(r.get('format') or '?') for r in (row.get('resources') or [])})})"
    )
    return out


def cmd_qualify(date: str) -> int:
    """Probe every enumerated dataset: shape, count, verbatim licence."""
    src = REPORTS / f"catalog_sweep_{date}.json"
    artifact = json.loads(src.read_text(encoding="utf-8"))
    rows = artifact["datasets"]
    now = datetime.now(UTC).isoformat()
    qualified: list[dict[str, Any]] = []
    for i, row in enumerate(rows):
        out = dict(row)
        catalog = str(row.get("catalog"))
        if catalog == "socrata":
            shape, reason = _socrata_shape(row)
            if shape == "camera_registry":
                out.update(_socrata_probe(row))
                out["resource_kind"] = "socrata_rows"
            else:
                out["blocker"] = reason
            out["shape"] = shape
        elif catalog == "arcgis_hub":
            if not _content_signal(row):
                out["shape"] = "non_target"
                out["blocker"] = "content: no camera/surveillance signal in title/keywords"
            else:
                out.update(_arcgis_probe(row))
                geom = str(out.get("geometry_type") or "")
                if out.get("probe_error") and not out.get("layer_url"):
                    out["shape"] = "error"
                    out["blocker"] = str(out["probe_error"])
                elif geom != "esriGeometryPoint":
                    out["shape"] = "non_target"
                    out["blocker"] = f"shape: geometry {geom or 'unknown'} is not point"
                else:
                    out["shape"] = "camera_registry"
                    out["resource_kind"] = "arcgis_query"
        elif catalog == "ckan_data_gov_uk":
            if not _content_signal(row):
                out["shape"] = "non_target"
                out["blocker"] = "content: no camera/surveillance signal in title/keywords"
            else:
                out.update(_ckan_probe(row))
                kind = str(out.get("resource_kind") or "")
                if kind == "arcgis_query":
                    if out.get("probe_error") and not out.get("layer_url"):
                        out["shape"] = "error"
                        out["blocker"] = str(out["probe_error"])
                    elif str(out.get("geometry_type")) != "esriGeometryPoint":
                        out["shape"] = "non_target"
                        out["blocker"] = "shape: not a point layer"
                    else:
                        out["shape"] = "camera_registry"
                elif kind == "socrata_rows":
                    out["shape"] = "camera_registry"
                else:
                    out["shape"] = "non_target"
                    out["blocker"] = str(out.get("probe_error") or "unsupported resource kind")
        else:
            out["shape"] = "error"
            out["blocker"] = f"unknown catalog {catalog!r}"
        non_reg = _non_registry(row)
        if out["shape"] == "camera_registry" and non_reg:
            out["shape"] = "non_target"
            out["blocker"] = non_reg
        licence_text = str(out.get("licence_verbatim") or out.get("licence") or "")
        out["licence_verbatim"] = licence_text[:4000]
        out["spdx"] = _licence_to_spdx(
            str(row.get("licence") or ""),
            str(row.get("licence_title") or ""),
            catalog=catalog,
        )
        if out["spdx"] is None and licence_text and catalog != "ckan_data_gov_uk":
            out["spdx"] = _licence_to_spdx(licence_text)
        qualified.append(out)
        if (i + 1) % 25 == 0:
            print(f"  qualified {i + 1}/{len(rows)}", file=sys.stderr)

    counts: dict[str, int] = {}
    for row in qualified:
        key = f"{row['shape']}"
        counts[key] = counts.get(key, 0) + 1
    out_doc = {
        "artifact": "catalog_sweep_qualified",
        "ticket": "P26.13 / SOURCES.12",
        "retrieved_at": now,
        "source_artifact": src.name,
        "counts": {
            **counts,
            "clear_licence_registries": sum(
                1 for r in qualified if r["shape"] == "camera_registry" and r.get("spdx")
            ),
            "gated_licence_registries": sum(
                1 for r in qualified if r["shape"] == "camera_registry" and not r.get("spdx")
            ),
        },
        "datasets": qualified,
    }
    dest = REPORTS / f"catalog_sweep_{date}_qualified.json"
    dest.write_text(json.dumps(out_doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {dest}: {out_doc['counts']}", file=sys.stderr)
    return 0


# --- review pass --------------------------------------------------------------
# The qualify heuristics are deliberately permissive (a point shape + a camera
# word in the title admits a row). The review pass re-checks every admitted
# row against title-level non-registry patterns below, re-parses Socrata
# dict-form licence metadata, and applies hand-verified licence resolutions.
# Every override lands in `review_decisions` — nothing is silently dropped.


#: Title-level non-registry content the shape probe over-admits. Each row is
#: (compiled pattern, honest blocker reason recorded on the row).
_REVIEW_NON_REGISTRY: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"behavioral risk|risk behavior|health surveillance|eye health|"
            r"vision and eye|youth risk|syndromic|overdose|covid|mosquito|"
            r"tick surveillance|\bwnv\b|\beee\b|immuniz|vaccin|clinic|"
            r"hospitaliz|medicaid|medicare|nutrition|aging trends|"
            r"medical insurance|positives|fatalities"
        ),
        "health/epidemiological surveillance dataset — not a camera registry",
    ),
    (
        re.compile(r"violation|citation|ticket|speed data"),
        "enforcement-violation records — person-adjacent event data, not a registry",
    ),
    (
        re.compile(
            r"license plate reader data|licence plate reader data|alpr data|"
            r"plate reads|all license plate|all licence plate|"
            r"plate collection|license plate survey|lpr success"
        ),
        "ALPR read/plate records — Part VIII plate data, never ingested",
    ),
    (
        re.compile(r"surveillance images|images posted"),
        "imagery/feed dataset — media content is never ingested",
    ),
    (
        re.compile(
            r"_form\b|collection_form|registration_form|survey\b|fieldwork|"
            r"stakehold|survey123"
        ),
        "collection form/survey artifact — not a registry",
    ),
    (
        re.compile(
            r"viewshed|coverage|density|totals|summary|dashboard|maintenance|"
            r"wishlist|inspection|sewer|salon|shelter|study ?area|patrouille|"
            r"reseau|profondeur|camera_?counts|parking services"
        ),
        "aggregate/administrative/coverage layer — not a camera registry",
    ),
]

#: Extra licence-text patterns the review pass applies over the FULL
#: licence_verbatim (the qualify map is deliberately narrower).
_REVIEW_LICENCE_MAP = [
    ("open-government-licence", "OGL-3.0"),  # nationalarchives URL form
    ("nationalarchives.gov.uk/doc/open-government", "OGL-3.0"),
    ("licenses/by-sa/2.0", "CC-BY-SA-2.0"),
    ("licenses/by-sa/4.0", "CC-BY-SA-4.0"),
    ("licenses/by/4.0", "CC-BY-4.0"),
    ("licenses/by/3.0", "CC-BY-3.0"),
    ("licenses/by-nc", None),  # non-commercial — restrictive, stays gated
    ("attribution | share alike 4.0", "CC-BY-SA-4.0"),
    ("attribution | sharealike 4.0", "CC-BY-SA-4.0"),
    ("creative commons attribution 4.0", "CC-BY-4.0"),
    ("creativecommons.org/licenses/by/4.0", "CC-BY-4.0"),
    ("creativecommons.org/licenses/by-sa/2.0", "CC-BY-SA-2.0"),
    ("creativecommons.org/licenses/by-sa/4.0", "CC-BY-SA-4.0"),
    ("open database license", "ODbL-1.0"),
    ("opendatacommons.org/licenses/odbl", "ODbL-1.0"),
    ("open government licence - city of ottawa", "LicenseRef-Ottawa-ODL-2.0"),
]

#: Hand-verified licence resolutions (evidence recorded in the rights packet /
#: run ledger): dataset catalog ids whose licence was confirmed verbatim
#: outside the metadata the probe captured.
_REVIEW_SPDX_OVERRIDES: dict[str, tuple[str, str]] = {
    # Region of Peel "Red Light Cameras" — the item names the Open Data
    # Licence for The Regional Municipality of Peel v1.0; the grant text
    # ("copy, publish, redistribute, adapt, and use our data for personal or
    # commercial purposes") verified 2026-09-18 via the Wayback capture of
    # data.peelregion.ca/pages/license.
    "36dbfcb33aa2453c8de55e0a34ccfc6a": (
        "LicenseRef-Peel-ODL-1.0",
        "named Peel ODL v1.0 + verbatim permissive grant via Wayback capture",
    ),
    # City of St. Albert "Photo Enforcement Mobile Locations" — licence text
    # verified 2026-09-18 via the Hub page item data
    # (content/items/454c9ce8b2bd444e833210d9cdfb636e/data): Open Data
    # Licence – City of St. Albert v1.0 (Alberta-OGL adapted; worldwide,
    # royalty-free, perpetual, commercial use + attribution).
    "6f2ca1b545844065b719483d562d553e": (
        "LicenseRef-StAlbert-ODL-1.0",
        "named St. Albert ODL v1.0 + verbatim grant via Hub page item data",
    ),
}


def _review_spdx(row: dict[str, Any]) -> tuple[str | None, str]:
    """Re-resolve a row's SPDX from every licence signal it carries."""
    licence = str(row.get("licence") or "")
    licence_verbatim = str(row.get("licence_verbatim") or "")
    # Socrata licence metadata is a dict literal ({'name': ..., 'termsLink': ...})
    # — the qualify map tested the repr, not the name. Re-parse it here.
    name = ""
    if licence.startswith("{"):
        try:
            parsed = ast.literal_eval(licence)
            if isinstance(parsed, dict):
                name = str(parsed.get("name") or "")
        except (ValueError, SyntaxError):
            name = ""
    override = _REVIEW_SPDX_OVERRIDES.get(str(row.get("id") or ""))
    if override is not None:
        return (override[0], f"manual override: {override[1]}")
    for cand in (name, licence_verbatim, licence):
        low = cand.lower()
        if not low or low in ("none", "null"):
            continue
        for needle, spdx in _REVIEW_LICENCE_MAP:
            if needle in low:
                return (spdx, f"licence map hit: {needle!r}")
        spdx = _licence_to_spdx(
            licence if cand is licence else cand,
            str(row.get("licence_title") or ""),
            catalog=str(row.get("catalog") or ""),
        )
        if spdx is not None:
            return (spdx, "qualify map hit on re-parse")
    return (None, "")


def cmd_review(date: str) -> int:
    """Offline second pass over the qualified artifact — no network."""
    src = REPORTS / f"catalog_sweep_{date}_qualified.json"
    artifact = json.loads(src.read_text(encoding="utf-8"))
    now = datetime.now(UTC).isoformat()
    decisions: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    for row in artifact["datasets"]:
        out = dict(row)
        shape_from = str(out.get("shape") or "")
        spdx_from = out.get("spdx")
        if shape_from == "camera_registry":
            title = str(out.get("title") or "").lower()
            for pat, reason in _REVIEW_NON_REGISTRY:
                if pat.search(title):
                    out["shape"] = "non_target"
                    out["blocker"] = f"review: {reason}"
                    decisions.append(
                        {
                            "id": out.get("id"),
                            "catalog": out.get("catalog"),
                            "title": out.get("title"),
                            "shape_from": shape_from,
                            "shape_to": "non_target",
                            "reason": reason,
                        }
                    )
                    break
        spdx_to, how = _review_spdx(out)
        if spdx_to != spdx_from:
            decisions.append(
                {
                    "id": out.get("id"),
                    "catalog": out.get("catalog"),
                    "title": out.get("title"),
                    "spdx_from": spdx_from,
                    "spdx_to": spdx_to,
                    "reason": how,
                }
            )
            out["spdx"] = spdx_to
        rows.append(out)

    counts: dict[str, int] = {}
    for row in rows:
        counts[row["shape"]] = counts.get(row["shape"], 0) + 1
    out_doc = {
        "artifact": "catalog_sweep_reviewed",
        "ticket": "P26.13 / SOURCES.12",
        "reviewed_at": now,
        "source_artifact": src.name,
        "counts": {
            **counts,
            "clear_licence_registries": sum(
                1 for r in rows if r["shape"] == "camera_registry" and r.get("spdx")
            ),
            "gated_licence_registries": sum(
                1 for r in rows if r["shape"] == "camera_registry" and not r.get("spdx")
            ),
        },
        "review_decisions": decisions,
        "datasets": rows,
    }
    dest = REPORTS / f"catalog_sweep_{date}_reviewed.json"
    dest.write_text(json.dumps(out_doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(
        f"wrote {dest}: {out_doc['counts']} | {len(decisions)} review decisions",
        file=sys.stderr,
    )
    return 0


# --- probe-error retry (P31.13 / BREADTH.2, D-SOURCES.12-1) --------------------
# The 2026-09-18 sweep left 68 `error` rows (transport failures + vanished
# endpoints). The retry pass re-probes each error row ONCE, records the outcome
# in a dated artifact, and (--apply) registers the rows that now resolve to a
# camera-registry shape as `camreg_*` sources with `ingestion_permitted=false`
# — no rights basis exists for these rows (67/68 carried spdx=null and
# GL-GATE-07 covered only the 257 gated rows), so nothing is wired or fetched
# for ingestion; each registration is queued for a reviewer (HG-03). A
# persistent DNS/SSL/503 is `unreachable`; a vanished endpoint is `link_rotted`.

SOURCES_TOML = REPO / "connectors/src/connectors/data/sources.toml"
DISPOSITIONS_TOML = REPO / "connectors/src/connectors/data/live_dispositions.toml"

#: Transport-level error signatures → `unreachable` (the endpoint never spoke).
_UNREACHABLE_MARKERS = (
    "URLError",
    "HTTPError",
    "TimeoutError",
    "timeout",
    "nodename nor servname",
    "SSL",
    "RemoteDisconnected",
    "ConnectionError",
    "Service Unavailable",
)


def _slug(text: str, limit: int = 28) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return slug[:limit].strip("_") or "row"


def _retry_source_id(row: dict[str, Any]) -> str:
    """A deterministic registry id for a retry success — traceable to the row."""
    basis = (
        row.get("owner")
        or (str(row.get("id") or "") if row.get("catalog") == "ckan_data_gov_uk" else "")
        or row.get("portal")
        or row.get("title")
        or "catalog"
    )
    return f"camreg_{_slug(str(basis))}_{str(row.get('id') or 'x')[:6].lower()}"


def _classify_retry(row: dict[str, Any], probe: dict[str, Any]) -> str:
    """The retry outcome for a re-probed error row (same rules as qualify+review)."""
    err = str(probe.get("probe_error") or "")
    layer_url = str(probe.get("layer_url") or "")
    # A live service with no layers at all is a vanished endpoint; a live
    # service with layers but no camera-named one is a live non-target.
    if "no camera-named layer among 0" in err:
        return "link_rotted"
    if "no camera-named layer" in err:
        return "non_target"
    if err and not layer_url:
        if "404" in err or "410" in err:
            return "link_rotted"
        if any(m in err for m in _UNREACHABLE_MARKERS):
            return "unreachable"
        return "error"
    kind = str(probe.get("resource_kind") or "")
    if row.get("catalog") == "ckan_data_gov_uk" and kind not in ("arcgis_query", "socrata_rows"):
        return "non_target" if not err else "error"
    if kind == "arcgis_query" or row.get("catalog") == "arcgis_hub":
        if str(probe.get("geometry_type") or "") != "esriGeometryPoint":
            return "non_target"
    non_reg = _non_registry(row)
    if non_reg:
        return "non_target"
    title = str(row.get("title") or "").lower()
    if any(pat.search(title) for pat, _ in _REVIEW_NON_REGISTRY):
        return "non_target"
    if probe.get("observed_count") in (None, 0):
        # The layer resolves but the count probe failed — a partial success
        # still worth registering for review (shape + content are established).
        return "camera_registry"
    return "camera_registry"


def _registry_row_block(source_id: str, row: dict[str, Any], date: str) -> str:
    """The sources.toml block for a retry success — fail-closed pending HG-03."""
    title = str(row.get("title") or "").replace('"', "'")
    spdx = row.get("spdx") or "UNDETERMINED"
    licence = str(row.get("licence_verbatim") or row.get("licence") or "")[:400].replace('"', "'")
    permalink = str(row.get("permalink") or row.get("endpoint") or "")
    kind = str(row.get("resource_kind") or "arcgis_query")
    access = (
        "rest_api (socrata /resource rows — registry rows only)"
        if kind == "socrata_rows"
        else "rest_api (arcgis feature layer query — registry rows only)"
    )
    count = row.get("observed_count")
    count_txt = f"; {count} rows observed" if count else ""
    prior = str(row.get("prior_blocker") or "")[:120].replace('"', "'")
    return (
        f"\n[sources.{source_id}]\n"
        f'name = "{title} (catalog retry {date})"\n'
        f'source_kind = "government_portal"\n'
        f'homepage_url = "{permalink}"\n'
        f'default_tier = "R1"\n'
        f'custody_posture = "MIRROR"\n'
        f'compact_status = "not_contacted"\n'
        f'robots_policy = "honor"\n'
        f'access_method = "{access}"\n'
        f'auth_model = "none"\n'
        f"verified = true\n"
        f"last_verified = {date}\n"
        f"ingestion_permitted = false\n"
        f'notes = "P31.13 catalog probe-error retry {date}: prior probe error '
        f"({prior}) resolved — point camera-registry layer observed{count_txt}. "
        f"Licence evidence: '{licence[:200]}' -> spdx {spdx}. NO rights basis — "
        f'queued for rights review (HG-03); NOT wired, never fetched for ingestion."\n'
        f"[sources.{source_id}.rights]\n"
        f'spdx = "{spdx}"\n'
        f"redistributable = false\n"
        f"derivative_permitted = false\n"
        f'terms_url = "{permalink}"\n'
        f"retrieval_date = {date}\n"
    )


def _disposition_row_block(source_id: str, row: dict[str, Any]) -> str:
    """The live_dispositions.toml block — promote for the camera-registry path."""
    title = str(row.get("title") or "").replace('"', "'")[:80]
    return (
        f"\n[sources.{source_id}]\n"
        f'disposition = "promote"\n'
        f'class_ticket = "P25.3"\n'
        f'note = "P31.13 catalog retry success: {title} — camera-registry-shaped; '
        f'candidate for the dot_511 path. Pending rights review (HG-03)."\n'
    )


def cmd_retry(date: str, *, apply: bool = False) -> int:
    """Re-probe every `error` row of the reviewed artifact once (P31.13)."""
    reviewed = sorted(REPORTS.glob("catalog_sweep_*_reviewed.json"))[-1]
    artifact = json.loads(reviewed.read_text(encoding="utf-8"))
    errors = [r for r in artifact["datasets"] if r.get("shape") == "error"]
    print(f"retrying {len(errors)} probe-error rows from {reviewed.name}", file=sys.stderr)
    now = datetime.now(UTC).isoformat()
    results: list[dict[str, Any]] = []
    for i, row in enumerate(errors):
        out = {
            "id": row.get("id"),
            "catalog": row.get("catalog"),
            "portal": row.get("portal"),
            "title": row.get("title"),
            "endpoint": row.get("endpoint"),
            "permalink": row.get("permalink"),
            "owner": row.get("owner"),
            "prior_blocker": row.get("blocker"),
        }
        catalog = str(row.get("catalog") or "")
        if catalog == "arcgis_hub":
            probe = _arcgis_probe(row)
        elif catalog == "ckan_data_gov_uk":
            probe = _ckan_probe(row)
        elif catalog == "socrata":
            probe = _socrata_probe(row)
        else:
            probe = {"probe_error": f"unknown catalog {catalog!r}"}
        out.update(probe)
        outcome = _classify_retry(row, probe)
        out["retry_outcome"] = outcome
        spdx, how = _review_spdx({**row, **probe})
        out["spdx"] = spdx
        if how:
            out["spdx_basis"] = how
        if outcome == "camera_registry":
            out["registered_source_id"] = _retry_source_id(row)
        results.append(out)
        print(
            f"  [{i + 1}/{len(errors)}] {row.get('id')} -> {outcome}",
            file=sys.stderr,
        )

    counts: dict[str, int] = {}
    for r in results:
        counts[r["retry_outcome"]] = counts.get(r["retry_outcome"], 0) + 1
    out_doc = {
        "artifact": "catalog_sweep_retry",
        "ticket": "P31.13 / BREADTH.2 (D-SOURCES.12-1 engineering remainder)",
        "retried_at": now,
        "source_artifact": reviewed.name,
        "counts": {**counts, "retried": len(results)},
        "rights_note": (
            "No retry-success row carries a rights basis (GL-GATE-07 covered only "
            "the 257 gated rows). Successes are registered ingestion_permitted=false "
            "and queued for a reviewer (HG-03); nothing is wired or fetched."
        ),
        "results": results,
    }
    dest = REPORTS / f"catalog_sweep_{date}_retry.json"
    dest.write_text(json.dumps(out_doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {dest}: {out_doc['counts']}", file=sys.stderr)

    if apply:
        successes = [r for r in results if r["retry_outcome"] == "camera_registry"]
        if successes:
            existing = SOURCES_TOML.read_text(encoding="utf-8")
            disp_text = DISPOSITIONS_TOML.read_text(encoding="utf-8")
            for r in successes:
                sid = r["registered_source_id"]
                if f"[sources.{sid}]" in existing:
                    r["registration"] = "already_registered"
                    continue
                existing += _registry_row_block(sid, r, date)
                disp_text += _disposition_row_block(sid, r)
                r["registration"] = "registered_unpermitted"
                print(f"  registered {sid} (ingestion_permitted=false)", file=sys.stderr)
            SOURCES_TOML.write_text(existing, encoding="utf-8")
            DISPOSITIONS_TOML.write_text(disp_text, encoding="utf-8")
            # Record the registration outcome back into the artifact.
            dest.write_text(json.dumps(out_doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


def main(argv: list[str]) -> int:
    cmd = argv[1] if len(argv) > 1 else ""
    date = datetime.now(UTC).strftime("%Y-%m-%d")
    if "--date" in argv:
        date = argv[argv.index("--date") + 1]
    if cmd == "enumerate":
        return cmd_enumerate(date)
    if cmd == "qualify":
        return cmd_qualify(date)
    if cmd == "review":
        return cmd_review(date)
    if cmd == "retry":
        return cmd_retry(date, apply="--apply" in argv)
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
