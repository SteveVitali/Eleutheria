# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The search-result export bundle (P37.43 / K3 SRCH-08 — "CSV/JSON
download of a result set (≤ 10,000 rows), per licence group with licence
files (J3 TX download conventions)").

``GET /v1/releases/{pub or latest}/search/export?format=csv|json`` answers
a deterministic ``application/zip`` bundle over the same verified
``sig.search-results/2`` engine the results page renders — Datasette's
"download these results" (K12a [Q087]) under SIG's licence-compartment
rules:

* **Per licence group, never a mixed-compartment file** — each licence
  compartment with exported rows gets one folder:
  ``<compartment>/results.csv`` (or ``results.json`` under
  ``sig.search-export-records/1``), ``<compartment>/LICENCE.txt`` and
  ``<compartment>/ATTRIBUTION.txt``. A compartment's rows never share a
  file with another compartment's rows, and every exported row carries
  its licence (the compartment licence column + the group licence files).
* **J3 download conventions** — the bundle's ``SHA256SUMS`` checksums
  every member in GNU format; ``manifest.json`` (``sig.search-export/1``)
  records the release, the query, the scope (access-time denials counted,
  DR-C4-09 carried), the ≤ 10,000-row cap and the honest ``truncated``
  flags; ``ATTRIBUTION.txt`` names every source the exported rows cite
  and points at the release's own downloads for the captured terms
  verbatim (they are never re-typed here — ``/releases/<pub>/data/`` and
  the compartment ``ATTRIBUTION.txt`` carry them).
* **Deterministic** — identical index bytes + identical query → identical
  zip bytes (sorted members, fixed timestamps, no clock values in the
  manifest; ``data as of`` is the release's own ``as_of_world``).

The row set comes from ``SearchEngineV2.export_records``: the same
match-quality order the page walks, the same access-time denial barrier
evaluated per candidate, collapsed acronym word-hits withheld, and at
most ``EXPORT_ROW_CAP`` rows total.
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from collections.abc import Mapping, Sequence
from typing import Any

from policy.licensing import license_url as _license_url

from .downloads import licence_txt
from .manifest import PUBLICATION_BASIS, canonical_json, sha256_hex

#: The bundle manifest schema.
SEARCH_EXPORT_SCHEMA = "sig.search-export/1"
#: The per-group JSON rows document schema.
SEARCH_EXPORT_ROWS_SCHEMA = "sig.search-export-records/1"

#: Fixed zip member timestamp — immutable bytes for an immutable request.
_ZIP_DATE = (1980, 1, 1, 0, 0, 0)

MANIFEST_FILE = "manifest.json"
SHA256SUMS_FILE = "SHA256SUMS"
README_FILE = "README.txt"

#: The CSV column order for one group's ``results.csv`` — the record-card
#: fields the engine emits, compartment + licence explicit on every row.
CSV_COLUMNS: tuple[str, ...] = (
    "record_key",
    "entity_id",
    "entity_type",
    "name",
    "name_derived",
    "name_basis",
    "jurisdiction",
    "place",
    "sources",
    "source_names",
    "technology",
    "matched",
    "tier",
    "score",
    "compartment",
    "license",
    "href",
)

_EXPORT_FORMATS = ("csv", "json")


class SearchExportError(RuntimeError):
    """A search-export contract violation — always loud, never partial."""


def _csv_cell(value: Any) -> str:
    if value is None:
        return ""
    s = str(value)
    if isinstance(value, bool):
        s = "true" if value else "false"
    return f'"{s.replace(chr(34), chr(34) * 2)}"' if any(c in s for c in '",\n\r') else s


def _row_cells(row: Mapping[str, Any]) -> list[str]:
    return [
        _csv_cell(row.get("record_key")),
        _csv_cell(row.get("entity_id")),
        _csv_cell(row.get("entity_type")),
        _csv_cell(row.get("name")),
        _csv_cell(row.get("name_derived")),
        _csv_cell(row.get("name_basis")),
        _csv_cell(row.get("jurisdiction")),
        _csv_cell(row.get("place")),
        _csv_cell(";".join(str(s) for s in row.get("sources") or [])),
        _csv_cell(";".join(str(s) for s in row.get("source_names") or [])),
        _csv_cell(row.get("technology")),
        _csv_cell(row.get("matched")),
        _csv_cell(row.get("tier")),
        _csv_cell(row.get("score")),
        _csv_cell(row.get("compartment")),
        _csv_cell(row.get("license")),
        _csv_cell(row.get("href")),
    ]


def _group_rows_csv(
    group: Mapping[str, Any],
    *,
    release: Mapping[str, Any],
    query: Mapping[str, Any],
) -> bytes:
    """One group's ``results.csv`` — the ADR-224 ``#``-comment licence
    provenance preamble (the rows are never read decontextualised from
    their licence) + the header + every exported row in emitted order."""
    comp = str(group["compartment"])
    license_id = str(group["license"])
    q_line = json.dumps(
        {
            "q": query.get("q"),
            "types": query.get("types"),
            "filters": query.get("filters"),
        },
        sort_keys=True,
    )
    lines = [
        f"# SIG search result export — licence group {comp}",
        f"# release: {release.get('label') or ''} {release.get('publication_id') or ''}".rstrip(),
        f"# data as of: {release.get('as_of_world') or 'not recorded'}",
        f"# query: {q_line}",
        f"# licence: {license_id}",
        f"# compartment: {comp} — every row in this file is this licence "
        "group; no other group's rows appear here",
        f"# rows: {group.get('exported')} exported of {group.get('total')} matching"
        + (" — TRUNCATED at the export cap" if group.get("truncated") else ""),
        "# licence files: LICENCE.txt and ATTRIBUTION.txt beside this "
        "file state the terms and the credit a re-user must carry",
    ]
    lines.append(",".join(CSV_COLUMNS))
    for row in group.get("rows") or []:
        r = dict(row)
        r["compartment"] = comp
        r["license"] = license_id
        lines.append(",".join(_row_cells(r)))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _group_rows_json(
    group: Mapping[str, Any],
    *,
    release: Mapping[str, Any],
    query: Mapping[str, Any],
) -> bytes:
    """One group's ``results.json`` — the ``sig.search-export-records/1``
    envelope carrying licence + compartment on the document and on every
    row."""
    comp = str(group["compartment"])
    license_id = str(group["license"])
    rows = []
    for row in group.get("rows") or []:
        r = dict(row)
        r["compartment"] = comp
        r["license"] = license_id
        rows.append(r)
    return canonical_json(
        {
            "schema": SEARCH_EXPORT_ROWS_SCHEMA,
            "release": dict(release),
            "query": {
                "q": query.get("q"),
                "types": query.get("types"),
                "filters": query.get("filters") or {},
            },
            "compartment": comp,
            "license": license_id,
            "matching": int(group.get("total") or 0),
            "exported": int(group.get("exported") or 0),
            "truncated": bool(group.get("truncated")),
            "licence_files": ["LICENCE.txt", "ATTRIBUTION.txt"],
            "rows": rows,
        }
    )


def _group_attribution_txt(
    group: Mapping[str, Any],
    *,
    release: Mapping[str, Any],
) -> bytes:
    """One group's ``ATTRIBUTION.txt`` — every source the EXPORTED rows
    cite, with its registry name and exported row count, under the group
    licence. The captured terms verbatim and the operator-accepted basis
    are never re-typed: the pointer names the release's own downloads."""
    comp = str(group["compartment"])
    license_id = str(group["license"])
    license_url = _license_url(license_id)
    per_source: dict[str, dict[str, Any]] = {}
    for row in group.get("rows") or []:
        ids = [str(s) for s in row.get("sources") or []]
        names = [str(n) for n in row.get("source_names") or []]
        if not ids and row.get("source_id"):
            ids = [str(row["source_id"])]
        for i, sid in enumerate(ids or [""]):
            if not sid:
                continue
            rec = per_source.setdefault(
                sid,
                {
                    "name": names[i] if i < len(names) else sid,
                    "rows": 0,
                },
            )
            rec["rows"] += 1
    lines = [
        f"# ATTRIBUTION — search result export · licence group {comp}",
        "",
        f"Licence: {license_id}",
        "Licence URL: "
        + (str(license_url) if license_url else "project LicenseRef — see per-source terms below"),
        "",
        f"Publication basis: {PUBLICATION_BASIS}",
        "",
        "This file names every source the exported rows of this licence "
        "group cite. It is a download-time summary — the release's own "
        "per-compartment ATTRIBUTION.txt (the downloads centre, "
        f"/releases/{release.get('publication_id')}/data/) states each "
        "source's effective attribution, terms URL and any captured terms "
        "verbatim plus the operator-accepted basis; those statements "
        "govern and are never re-typed here.",
        "",
        "## Sources cited by the exported rows",
    ]
    if not per_source:
        lines += ["", "(no rows exported for this group — no sources to name)"]
    for sid in sorted(per_source):
        rec = per_source[sid]
        lines += ["", f"- {rec['name']} ({sid})", f"  rows exported: {rec['rows']}"]
    lines += [
        "",
        "Changes made by SIG: source records were normalised, "
        "licence-sliced and re-serialised; upstream bytes are not "
        "republished here.",
        "",
    ]
    return ("\n".join(lines)).encode("utf-8")


def _readme(result: Mapping[str, Any], *, fmt: str) -> bytes:
    release = result.get("release") or {}
    scope = result.get("scope") or {}
    export = result.get("export") or {}
    lines = [
        "SIG search result export",
        "=========================",
        "",
        f"Release: {release.get('label') or ''} {release.get('publication_id') or ''}".rstrip(),
        f"Data as of: {release.get('as_of_world') or 'not recorded'}",
        f"Format: {fmt} (one results.{fmt} per licence group)",
        f"Rows exported: {export.get('exported_records')} "
        f"(cap {export.get('row_cap')}; truncated: {str(bool(export.get('truncated'))).lower()})",
        f"Licence groups searched: {scope.get('groups_searched')} "
        f"· records searched: {scope.get('records_searched')}",
        "",
        "Layout: one folder per licence group, each holding results.{fmt}, "
        "LICENCE.txt and ATTRIBUTION.txt. A licence group's rows never "
        "share a file with another group's rows. manifest.json describes "
        "the bundle; SHA256SUMS checksums every member.",
        "",
        "Records only: typed catalog results (places, sources, "
        "technologies, documents) are links in the results page, not "
        "exportable record rows. Cite the release URL for durability.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def _manifest(
    result: Mapping[str, Any], *, fmt: str, files: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    export = result.get("export") or {}
    scope = result.get("scope") or {}
    query = result.get("query") or {}
    groups: list[dict[str, Any]] = []
    for g in export.get("groups") or []:
        gfiles = [f["path"] for f in files if f["path"].startswith(f"{g['compartment']}/")]
        groups.append(
            {
                "compartment": g["compartment"],
                "license": g["license"],
                "matching": int(g.get("total") or 0),
                "exported": int(g.get("exported") or 0),
                "truncated": bool(g.get("truncated")),
                "collapsed_reason": g.get("collapsed_reason"),
                "files": sorted(gfiles),
            }
        )
    return {
        "schema": SEARCH_EXPORT_SCHEMA,
        "release": dict(result.get("release") or {}),
        "query": {
            "q": query.get("q"),
            "normalized": query.get("normalized"),
            "types": query.get("types"),
            "filters": query.get("filters") or {},
            "suggestion": query.get("suggestion"),
        },
        "scope": {
            "records_indexed": scope.get("records_indexed"),
            "records_searched": scope.get("records_searched"),
            "groups_searched": scope.get("groups_searched"),
            "excluded_records_by_reason": scope.get("excluded_records_by_reason") or {},
        },
        "export": {
            "format": fmt,
            "row_cap": export.get("row_cap"),
            "exported_records": export.get("exported_records"),
            "truncated": bool(export.get("truncated")),
        },
        "groups": groups,
        "note": (
            "One folder per licence group — results rows ship only beside "
            "that group's LICENCE.txt and ATTRIBUTION.txt, never in a "
            "mixed-compartment file. Typed catalog results are not "
            "exportable rows; the results page links them."
        ),
    }


def _filename(result: Mapping[str, Any], *, fmt: str) -> str:
    pub = str((result.get("release") or {}).get("publication_id") or "unknown")
    query = result.get("query") or {}
    qh = hashlib.sha256(
        canonical_json(
            {
                "q": query.get("q"),
                "t": query.get("types"),
                "f": query.get("filters"),
                "s": query.get("suggestion"),
            }
        )
    ).hexdigest()[:8]
    return f"sig-search-export-{pub[:12]}-{qh}-{fmt}.zip"


def search_export_zip(result: Mapping[str, Any], *, fmt: str, requested: str) -> tuple[bytes, str]:
    """The deterministic ``application/zip`` bundle for one export payload
    → ``(bytes, filename)``. ``fmt`` is ``csv`` or ``json``; the payload is
    the engine's ``export_records`` result (a served
    ``sig.search-results/2`` payload carrying the ``export`` block).
    """
    if fmt not in _EXPORT_FORMATS:
        raise SearchExportError(f"export format must be one of {_EXPORT_FORMATS}; got {fmt!r}")
    release = dict(result.get("release") or {})
    query = dict(result.get("query") or {})
    export = result.get("export") or {}
    files: list[dict[str, Any]] = []

    # Per licence group — each folder is single-compartment by
    # construction (a group key names exactly one compartment). A group
    # with no exported rows emits no folder (the manifest still records
    # its matching total) — J3's no-empty-bundle rule.
    for group in export.get("groups") or []:
        if not group.get("rows"):
            continue
        comp = str(group["compartment"])
        license_id = str(group["license"])
        rows_name = f"results.{fmt}"
        rows_bytes = (
            _group_rows_csv(group, release=release, query=query)
            if fmt == "csv"
            else _group_rows_json(group, release=release, query=query)
        )
        members = {
            f"{comp}/{rows_name}": rows_bytes,
            f"{comp}/LICENCE.txt": licence_txt(
                license_id, _license_url(license_id), compartment=comp
            ),
            f"{comp}/ATTRIBUTION.txt": _group_attribution_txt(group, release=release),
        }
        for path in sorted(members):
            data = members[path]
            files.append(
                {"path": path, "bytes": len(data), "sha256": sha256_hex(data), "data": data}
            )

    manifest = _manifest(result, fmt=fmt, files=files)
    manifest_bytes = canonical_json(manifest)
    readme_bytes = _readme(result, fmt=fmt)
    ordered = [(MANIFEST_FILE, manifest_bytes), (README_FILE, readme_bytes)] + [
        (f["path"], f["data"]) for f in files
    ]
    sums = "".join(f"{sha256_hex(data)}  {path}\n" for path, data in ordered).encode("utf-8")
    ordered.append((SHA256SUMS_FILE, sums))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, data in ordered:
            info = zipfile.ZipInfo(path, date_time=_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            zf.writestr(info, data)
    return buf.getvalue(), _filename(result, fmt=fmt)


__all__ = [
    "CSV_COLUMNS",
    "MANIFEST_FILE",
    "README_FILE",
    "SEARCH_EXPORT_ROWS_SCHEMA",
    "SEARCH_EXPORT_SCHEMA",
    "SHA256SUMS_FILE",
    "SearchExportError",
    "search_export_zip",
]
