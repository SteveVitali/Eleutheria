# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P37.69a — the committed open-data FILE readers (ACQ-23a file lane).

Three registered connectors over ONE committed vocabulary
(``open_data_files_vocab``) and ONE committed inventory
(``open_data_files_targets``, ``sig.open-data-files-targets/1``):

* ``csv_file`` — a committed CSV register URL (Barnet's community-safety and
  traffic-enforcement camera CSVs). The served sheet's FIRST row is the
  header; every declared field name must appear verbatim (a renamed or
  missing column is ``ContentDrift``, never a guessed position), and ANY
  field name hitting the shared Part VIII denylist fails the whole capture
  closed — the lane never silently drops a column and mints the rest
  (F-330). Each data row mints a ``traffic_camera:`` subject through the
  same ``CameraRegistryEntry`` emit ``dot_511`` uses — the parcel screen,
  the §19.4 tier transform, the declared-axis-order stamp, the recorded
  geometry-defect lane and the PKG-07 declared-technology contract all ride
  the shared machinery.
* ``geojson_file`` — a committed ``FeatureCollection`` (Trafford's CCTV
  GeoJSON). Every feature must be a ``Point`` (an area or linestring member
  is drift — the lane's contract is device points); the properties dict is
  header-screened the same way and each declared field is asserted present.
* ``xlsx_file`` — a committed ``.xlsx`` workbook (Madrid's videovigilancia
  export, Korosten's data.gov.ua XLSX). The reader is a deliberately small
  stdlib-only implementation (``zipfile`` + ``ElementTree`` — the OOXML
  sheet-1 text surface, never a general spreadsheet engine): it resolves
  the declared sheet by name through ``workbook.xml`` + the rels part,
  expands ``sharedStrings.xml`` string refs, and treats the first row as
  the header under the same deny/marker contract. An unreadable zip, a
  missing declared sheet or a non-tabular layout is ``ContentDrift``.

Each file lane also mints ONE ``open_data_dataset:`` record carrying the
seat's declared catalogue metadata (title, publisher, licence id,
jurisdiction, technology, served row count) — the dataset-page facts live
on the portal lane or the dossier seat; here the record is the file's own
provenance anchor, its values declared target data, never guessed from the
file.

Target rows may pin ``expected_markers`` — literal strings the served
content must contain (the reviewed sheet banner or a known column header);
an absent marker is ``ContentDrift`` like every other reviewed-literal
contract. ``[[enumerated]]`` rows record the seats whose concrete file URL
is NOT yet committed (the candidate's dataset landing page is evidenced
but its resource URL is not) — they are registry records, never targets.

Every seat stays ``ingestion_permitted=false``; leg B (the first real wire)
is the operator's act under ING-GO-D (OP-26).
"""

from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from functools import cache
from typing import Any
from xml.etree import ElementTree

from policy.parcel_screen import ParcelScreenVerdict, declared_parcel_signal, screen_point
from policy.sensitivity import SensitivityClass, demote_for_residential_parcel

from ._data import load_table
from .dot_511 import (
    CameraRegistryEntry,
    declared_record_kind,
    publishable_coordinate,
)
from .field_denylist import denied_match
from .open_data_portals import _dataset_rows, assert_predicate_allowed
from .stages import CaptureRef, Connector, ContentDrift, FetchResult, RunContext, register

_VOCAB_TABLE = "open_data_files_vocab"
_TARGETS_TABLE = "open_data_files_targets"
_SCHEMA = "sig.open-data-files-vocab/1"
_TARGETS_SCHEMA = "sig.open-data-files-targets/1"

CSV_CONNECTOR = "csv_file"
GEOJSON_CONNECTOR = "geojson_file"
XLSX_CONNECTOR = "xlsx_file"
CONNECTOR_NAMES = frozenset({CSV_CONNECTOR, GEOJSON_CONNECTOR, XLSX_CONNECTOR})

#: The reader's hard caps — a served file past the declared bound is drift,
#: never a silently truncated ingest.
_MAX_ROWS = 5_000
_MAX_BYTES = 8 * 1024 * 1024
_XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
_XLSX_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"


@cache
def vocab() -> dict[str, Any]:
    table = load_table(_VOCAB_TABLE)
    if str(table.get("schema") or "") != _SCHEMA:
        raise ValueError(f"open_data_files vocabulary must be {_SCHEMA!r}")
    return table


def vocab_version() -> str:
    return str(vocab()["vocab_version"])


@cache
def file_targets(source_id: str, *, connector: str | None = None) -> list[dict[str, Any]]:
    table = load_table(_TARGETS_TABLE)
    if str(table.get("schema") or "") != _TARGETS_SCHEMA:
        raise ValueError(f"open_data_files inventory must be {_TARGETS_SCHEMA!r}")
    out = [dict(t) for t in table.get("targets", ()) if str(t.get("source_id")) == source_id]
    if connector is not None:
        out = [t for t in out if str(t.get("connector")) == connector]
    return out


@cache
def _all_targets() -> list[dict[str, Any]]:
    table = load_table(_TARGETS_TABLE)
    return [dict(t) for t in table.get("targets", ())]


@cache
def enumerated_rows() -> list[dict[str, Any]]:
    table = load_table(_TARGETS_TABLE)
    return [dict(t) for t in table.get("enumerated", ())]


def expanded_targets(source_id: str) -> list[dict[str, Any]]:
    """The expanded live targets — the committed file URL is the leg-A URL."""
    from urllib.parse import urlsplit

    hosts = frozenset(str(h) for h in vocab()["hosts"])
    out: list[dict[str, Any]] = []
    for row in file_targets(source_id):
        url = str(row["url"])
        if urlsplit(url).netloc.lower() not in hosts:
            raise ValueError(
                f"open_data_files target {row.get('id')!r} expands to host "
                f"{urlsplit(url).netloc.lower()!r}, off the committed host set "
                f"{sorted(hosts)} — a review error, never allowed"
            )
        out.append(
            {
                "id": str(row["id"]),
                "url": url,
                "kind": str(row["kind"]),
                "target": dict(row),
            }
        )
    return out


def _check_markers(source_id: str, target: Mapping[str, Any], text: str) -> None:
    """Every declared ``expected_markers`` literal must appear verbatim."""
    for marker in target.get("expected_markers", ()) or ():
        if str(marker) not in text:
            raise ContentDrift(
                source_id,
                f"reviewed marker {str(marker)!r} is absent from the served "
                f"file ({target.get('id')!r}) — a drifted capture, never a "
                "partially accepted sheet",
            )


def _screen_header(source_id: str, target: Mapping[str, Any], header: Sequence[str]) -> None:
    """The Part VIII header screen + the declared-field presence check."""
    names = [str(h).strip() for h in header]
    for name in names:
        term = denied_match(name)
        if term is not None:
            raise ContentDrift(
                source_id,
                f"the served file's header carries denied field {name!r} "
                f"(denied {term!r}) — a Part VIII field the lane refuses by "
                "name (F-330); the sheet is not partially accepted",
            )
    for field in target.get("declared_fields", ()) or ():
        if str(field) not in names:
            raise ContentDrift(
                source_id,
                f"declared field {str(field)!r} is absent from the served "
                f"header {names} — a renamed or dropped column is drift, "
                "never a guessed position",
            )


def _used_fields(target: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(
        f
        for f in (
            str(target.get("ref_field") or ""),
            str(target.get("lat_field") or ""),
            str(target.get("lon_field") or ""),
            str(target.get("name_field") or ""),
            str(target.get("status_field") or ""),
        )
        if f
    )


def _camera_rows(
    *,
    ctx: RunContext,
    target: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    url: str,
    coordinate_source: str,
    extraction_method: str,
    axis_order: str,
) -> list[dict[str, Any]]:
    """Row dicts → ``traffic_camera:`` claim sets via the shared emit."""
    source_id = ctx.source.id
    max_rows = int(target.get("max_rows") or _MAX_ROWS)
    if len(rows) > max_rows:
        raise ContentDrift(
            source_id,
            f"the served file carries {len(rows)} data rows over the declared bound {max_rows}",
        )
    sig = declared_parcel_signal()
    license_spdx = str(target.get("license_spdx") or "")
    sensitivity_class = str(target.get("sensitivity_class") or vocab()["default_sensitivity_class"])
    used = _used_fields(target)
    lat_field = str(target.get("lat_field") or "")
    lon_field = str(target.get("lon_field") or "")
    out: list[dict[str, Any]] = []
    retrieved = datetime.now(UTC).isoformat()
    for i, row in enumerate(rows):
        ref_field = str(target.get("ref_field") or "").strip()
        ref = str(row.get(ref_field) or "").strip() if ref_field else ""
        if not ref:
            if ref_field:
                raise ContentDrift(
                    source_id,
                    f"declared ref_field {ref_field!r} is empty on row {i}",
                )
            ref = f"r{i}"
        # Named-column reads — ``lat_field``/``lon_field`` are declared by
        # NAME, so the pair's published axis order is the stamp, not the read
        # order (the GeoJSON lane's array pair is always [lon, lat]).
        raw_lat, raw_lon = row.get(lat_field), row.get(lon_field)
        try:
            lat = float(str(raw_lat))
            lon = float(str(raw_lon))
        except (TypeError, ValueError):
            raise ContentDrift(
                source_id,
                f"row {i} ({ref!r}) carries no valid published coordinate — "
                "the lane never emits a guessed point",
            ) from None
        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            raise ContentDrift(
                source_id,
                f"row {i} ({ref!r}) published coordinate ({lat},{lon}) is out "
                "of range — drift, not a corrected pair",
            )
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
        name_field = str(target.get("name_field") or "").strip()
        status_field = str(target.get("status_field") or "").strip()
        entry = CameraRegistryEntry(
            camera_ref=ref,
            source_id=source_id,
            target_id=str(target.get("id")),
            state=str(target.get("state") or ""),
            agency=str(target.get("publisher") or ""),
            latitude=pub_lat,
            longitude=pub_lon,
            coordinate_source=coordinate_source,
            geo_tier=tier,
            sensitivity_class=cls_value,
            license_spdx=license_spdx,
            technology=str(target.get("technology") or ""),
            record_kind=declared_record_kind(target),
            name=(str(row.get(name_field)).strip() or None)
            if name_field and str(row.get(name_field) or "").strip()
            else None,
            status=(str(row.get(status_field)).strip() or None)
            if status_field and str(row.get(status_field) or "").strip()
            else None,
            jurisdiction_scheme=str(target.get("jurisdiction_scheme") or "iso.3166_2"),
            extraction_method=extraction_method,
            excluded_fields=tuple(sorted(n for n in row if n not in used)),
            residential_parcel_flag=residential_flag,
            parcel_screen=verdict.value,
            parcel_screen_signal=sig.stamp,
            axis_order=axis_order,
        )
        out.extend(entry.claim_rows(url, retrieved, i))
    return out


def _dataset_for_file(
    *,
    ctx: RunContext,
    target: Mapping[str, Any],
    url: str,
    row_count: int,
    fmt: str,
) -> list[dict[str, Any]]:
    """The file's own ``open_data_dataset:`` provenance anchor."""
    pkg = {
        "name": str(target.get("dataset_name") or target.get("id")),
        "title": str(target.get("title") or ""),
        "organization": {"title": str(target.get("publisher") or "")},
        "license_id": str(target.get("dataset_license_id") or ""),
        "license_title": str(target.get("dataset_license_title") or ""),
        "resources": [
            {
                "id": str(target.get("id")),
                "url": url,
                "format": fmt,
                "name": str(target.get("title") or ""),
            }
        ],
        "metadata_modified": str(target.get("dataset_modified") or ""),
    }
    rows = _dataset_rows(
        source_id=ctx.source.id,
        license_spdx=str(target.get("license_spdx") or ""),
        pkg=pkg,
        target=target,
        url=url,
        index=0,
    )
    for row in rows:
        if row.get("record_kind") == "open_data_dataset":
            row["served_row_count"] = row_count
    return rows


# --- the xlsx lane's minimal OOXML reader (stdlib only) ------------------------


def _xlsx_shared_strings(zf: zipfile.ZipFile) -> list[str]:
    try:
        raw = zf.read("xl/sharedStrings.xml")
    except KeyError:
        return []
    root = ElementTree.fromstring(raw)
    out: list[str] = []
    for si in root.findall(f"{_XLSX_NS}si"):
        out.append("".join(t.text or "" for t in si.iter(f"{_XLSX_NS}t")))
    return out


def _xlsx_sheet_path(zf: zipfile.ZipFile, sheet_name: str) -> str:
    """Resolve the declared sheet name → its sheet XML member path."""
    workbook = ElementTree.fromstring(zf.read("xl/workbook.xml"))
    rels = ElementTree.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
    rel_targets = {
        str(r.get("Id")): str(r.get("Target")) for r in rels.findall(f"{_XLSX_REL_NS}Relationship")
    }
    rns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    for sheet in workbook.iter(f"{_XLSX_NS}sheet"):
        if str(sheet.get("name")) == sheet_name:
            target = rel_targets.get(str(sheet.get(rns)))
            if not target:
                break
            return (
                "xl/" + target.lstrip("/") if not target.startswith("xl/") else target.lstrip("/")
            )
    raise ContentDrift(
        "xlsx",
        f"the declared sheet {sheet_name!r} is absent from the workbook — "
        "a renamed sheet is drift, never a guessed first sheet",
    )


def _xlsx_rows(source_id: str, data: bytes, target: Mapping[str, Any]) -> list[list[str]]:
    """The declared sheet's rows as string lists (sharedStrings expanded)."""
    if len(data) > _MAX_BYTES:
        raise ContentDrift(
            source_id, f"the served xlsx is {len(data)} bytes, over the {_MAX_BYTES} bound"
        )
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except zipfile.BadZipFile as exc:
        raise ContentDrift(
            source_id, "the served file is not a readable xlsx zip envelope"
        ) from exc
    with zf:
        shared = _xlsx_shared_strings(zf)
        sheet_name = str(target.get("sheet_name") or "Sheet1")
        try:
            path = _xlsx_sheet_path(zf, sheet_name)
        except ContentDrift as exc:
            raise ContentDrift(source_id, str(exc)) from exc
        try:
            sheet = ElementTree.fromstring(zf.read(path))
        except KeyError as exc:
            raise ContentDrift(
                source_id, f"the declared sheet member {path!r} is absent from the zip"
            ) from exc
        out: list[list[str]] = []
        for row in sheet.iter(f"{_XLSX_NS}row"):
            cells: list[str] = []
            for cell in row.findall(f"{_XLSX_NS}c"):
                cell_type = str(cell.get("t") or "")
                value = cell.find(f"{_XLSX_NS}v")
                inline = cell.find(f"{_XLSX_NS}is")
                if cell_type == "s" and value is not None:
                    try:
                        cells.append(shared[int(str(value.text))])
                    except (ValueError, IndexError):
                        raise ContentDrift(
                            source_id, "an xlsx shared-string index is out of range"
                        ) from None
                elif cell_type == "inlineStr" and inline is not None:
                    cells.append("".join(t.text or "" for t in inline.iter(f"{_XLSX_NS}t")))
                elif value is not None:
                    cells.append(str(value.text or ""))
                else:
                    cells.append("")
            out.append(cells)
    return out


class _FileConnector(Connector):
    """Shared eight-stage lane for the three committed-file readers."""

    connector_name = ""
    version = "1.0.0"
    ingestion_mode = "bulk_file_download"
    incrementality = "re-issue detection via content-addressed capture digests"
    name = ""

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        targets = list(ctx.parameters.get("targets", []))
        if targets:
            return targets
        return [dict(t) for t in expanded_targets(ctx.source.id)]

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """ONE polite GET on the committed file URL — the only egress."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        target = _resolve(ctx, capture.source_uri)
        spec = dict(target.get("target") or target)
        kind = str(spec.get("kind") or "")
        data = ctx.captures.get(capture.digest)
        if len(data) > _MAX_BYTES:
            raise ContentDrift(
                ctx.source.id,
                f"the served file is {len(data)} bytes, over the {_MAX_BYTES} bound",
            )
        if kind == "csv":
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ContentDrift(ctx.source.id, "the served CSV is not valid UTF-8") from exc
            _check_markers(ctx.source.id, spec, text)
            try:
                table = list(csv.reader(io.StringIO(text)))
            except csv.Error as exc:
                raise ContentDrift(
                    ctx.source.id, "the served CSV does not parse as a table"
                ) from exc
            if not table:
                raise ContentDrift(ctx.source.id, "the served CSV is empty")
            _screen_header(ctx.source.id, spec, table[0])
            header = [str(h).strip() for h in table[0]]
            rows = [
                {header[j]: str(cell) for j, cell in enumerate(r) if j < len(header)}
                for r in table[1:]
                if any(str(c).strip() for c in r)
            ]
            return {
                "kind": "csv",
                "payload": {"rows": rows},
                "capture": capture,
                "target": spec,
            }
        if kind == "geojson":
            try:
                doc = json.loads(data)
            except (ValueError, TypeError) as exc:
                raise ContentDrift(ctx.source.id, "the served file is not valid JSON") from exc
            if not isinstance(doc, Mapping) or doc.get("type") != "FeatureCollection":
                raise ContentDrift(
                    ctx.source.id,
                    "the served GeoJSON is not a FeatureCollection — the lane's "
                    "contract is the published device-point collection",
                )
            features = doc.get("features")
            if not isinstance(features, list):
                raise ContentDrift(
                    ctx.source.id, "the FeatureCollection carries no 'features' array"
                )
            geo_rows: list[dict[str, Any]] = []
            for i, feat in enumerate(features):
                if not isinstance(feat, Mapping) or feat.get("type") != "Feature":
                    raise ContentDrift(ctx.source.id, f"GeoJSON member {i} is not a Feature")
                geom = feat.get("geometry")
                if not isinstance(geom, Mapping) or geom.get("type") != "Point":
                    raise ContentDrift(
                        ctx.source.id,
                        f"GeoJSON feature {i} geometry is not a Point — an area "
                        "or line member is drift for the device-point lane",
                    )
                coords = geom.get("coordinates")
                if not (
                    isinstance(coords, Sequence)
                    and not isinstance(coords, str)
                    and len(coords) >= 2
                ):
                    raise ContentDrift(
                        ctx.source.id, f"GeoJSON feature {i} carries no [lon,lat] pair"
                    )
                props = feat.get("properties")
                props = dict(props) if isinstance(props, Mapping) else {}
                try:
                    lon = float(str(coords[0]))
                    lat = float(str(coords[1]))
                except (TypeError, ValueError):
                    raise ContentDrift(
                        ctx.source.id, f"GeoJSON feature {i} has non-numeric coordinates"
                    ) from None
                props["__lon"] = str(lon)
                props["__lat"] = str(lat)
                geo_rows.append(props)
            _check_markers(ctx.source.id, spec, data.decode("utf-8", "replace"))
            _screen_header(ctx.source.id, spec, sorted({k for r in geo_rows for k in r}))
            return {
                "kind": "geojson",
                "payload": {"rows": geo_rows},
                "capture": capture,
                "target": spec,
            }
        if kind == "xlsx":
            table = _xlsx_rows(ctx.source.id, data, spec)
            if not table:
                raise ContentDrift(ctx.source.id, "the declared xlsx sheet is empty")
            text = "\n".join("|".join(r) for r in table)
            _check_markers(ctx.source.id, spec, text)
            _screen_header(ctx.source.id, spec, table[0])
            xlsx_header = [str(h).strip() for h in table[0]]
            sheet_rows = [
                {xlsx_header[j]: str(cell) for j, cell in enumerate(r) if j < len(xlsx_header)}
                for r in table[1:]
                if any(str(c).strip() for c in r)
            ]
            return {
                "kind": "xlsx",
                "payload": {"rows": sheet_rows},
                "capture": capture,
                "target": spec,
            }
        raise ContentDrift(
            ctx.source.id, f"open_data_files target kind {kind!r} is not a reader kind"
        )

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        return [
            {
                "record_kind": "file_table",
                "rows": list(parsed["payload"]["rows"]),
                "kind": str(parsed.get("kind") or ""),
                "source_uri": parsed["capture"].source_uri,
                "retrieved_at": (
                    parsed["capture"].retrieved_at.isoformat()
                    if parsed["capture"].retrieved_at is not None
                    else datetime.now(UTC).isoformat()
                ),
                "target": dict(parsed.get("target") or {}),
            }
        ]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            target = dict(raw.get("target") or {})
            url = str(raw.get("source_uri") or "")
            kind = str(raw.get("kind") or "")
            rows = list(raw.get("rows") or ())
            assert_predicate_allowed("portal_index")
            out.extend(
                _dataset_for_file(
                    ctx=ctx,
                    target=target,
                    url=url,
                    row_count=len(rows),
                    fmt={"csv": "csv", "geojson": "geojson", "xlsx": "xlsx"}.get(kind, kind),
                )
            )
            if kind == "geojson":
                out.extend(
                    _camera_rows(
                        ctx=ctx,
                        target={**target, "lat_field": "__lat", "lon_field": "__lon"},
                        rows=rows,
                        url=url,
                        coordinate_source="geometry.coordinates",
                        extraction_method="geojson_file",
                        axis_order="lon-lat",
                    )
                )
            else:
                out.extend(
                    _camera_rows(
                        ctx=ctx,
                        target=target,
                        rows=rows,
                        url=url,
                        coordinate_source=(
                            f"fields:{target.get('lat_field')},{target.get('lon_field')}"
                        ),
                        extraction_method=f"{kind}_file",
                        axis_order=str(target.get("axis_order") or "lon-lat"),
                    )
                )
        return out


def _resolve(ctx: RunContext, source_uri: str) -> dict[str, Any]:
    for t in ctx.parameters.get("targets", []):
        if str(t.get("url")) == source_uri:
            return dict(t)
    rows = _all_targets()
    for row in rows:
        if str(row.get("source_id")) == ctx.source.id and str(row.get("url")) == source_uri:
            return {"id": str(row["id"]), "target": dict(row)}
    same_source = [r for r in rows if str(r.get("source_id")) == ctx.source.id]
    return {"id": str(same_source[0]["id"]), "target": dict(same_source[0])} if same_source else {}


@register
class CsvFileConnector(_FileConnector):
    """The committed CSV register reader."""

    name = CSV_CONNECTOR


@register
class GeojsonFileConnector(_FileConnector):
    """The committed GeoJSON FeatureCollection reader."""

    name = GEOJSON_CONNECTOR


@register
class XlsxFileConnector(_FileConnector):
    """The committed XLSX workbook reader (declared sheet, stdlib OOXML)."""

    name = XLSX_CONNECTOR


__all__ = [
    "CONNECTOR_NAMES",
    "CSV_CONNECTOR",
    "CsvFileConnector",
    "GEOJSON_CONNECTOR",
    "GeojsonFileConnector",
    "XLSX_CONNECTOR",
    "XlsxFileConnector",
    "enumerated_rows",
    "expanded_targets",
    "file_targets",
    "vocab",
    "vocab_version",
]
