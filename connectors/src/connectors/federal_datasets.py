# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `federal_datasets` connector family (P37.49 / R11-ACQ-21, I8 §6.2).

One fetch-and-parse helper — CSV, XLSX and JSON bodies plus an index-page link
enumerator — with small per-dataset adapters declared in
``data/federal_datasets_vocab.toml`` and the committed target inventory in
``data/federal_datasets_targets.toml`` (data, not code — SIG-ENG-001 /
SIG-INGEST-038). It serves the eight ACQ-21 registry seats:

* ``statrep_us_wiretap_summary_tables`` — the annual 18 U.S.C. §2519 Wiretap
  Report's data-table index (Wire 1–9 + appendices). The lane emits
  **document-pointer records only**: the report page enumerates its tables;
  the tables' per-jurisdiction aggregates ride a follow-up reviewed once the
  served table bodies are captured under the operator's first run. Judge and
  officer names are never read (§43.4 gate — the Wire 2 authorizations-by-
  judge table is a pointer, never an extraction surface).
* ``legis_us_federal_register_api`` and ``statrep_tx_south_padre_island_faa``
  — the Federal Register ``documents.json`` search, term-filtered (one term
  per committed query row; the API's Boolean OR is not relied on — the I6
  evidence recorded it returns 0). Each match is a
  ``federal_register_document`` record: document number, title, html URL,
  citation, publication date, issuing agencies — metadata only, never the
  document body.
* ``statrep_us_2024_federal_agency`` — the OMB consolidated Federal AI Use
  Case Inventory CSV (the ``ombegov`` GitHub publication). Each row is an
  ``ai_use_case`` record keyed agency × use-case id: name, topic area
  (verbatim), development stage (verbatim), the inventory's own literals —
  a guessed technology slug is never minted.
* ``statrep_us_dhs_ai_use`` — the DHS (S)AI Use-Case Inventory page, whose
  per-component inventory pages are enumerated as document pointers (the
  full spreadsheet sits behind the inventory-library link — pointers, never
  a guessed file URL).
* ``statrep_us_ice_287_participating`` — the ICE 287(g) landing page, whose
  dated ``participatingAgencies*.xlsx`` roster link resolves to a follow-on
  ``federal_xlsx`` child target (the filename changes each issue — link
  discovery, never a pinned stale name). Roster rows emit agency-registry
  records (name/state/county/type verbatim, signed date + MOA link as
  provenance) — a person-shaped agency name never mints a subject.
* ``statrep_us_ice_287_monthly`` — the same landing page's
  ``monthlyEncounter*`` / ``encounterReport*`` PDF links as pointers ONLY
  (S3): the encounter files' contents are never fetched, so no per-encounter
  or person-level row can exist by construction.
* ``camreg_us_nces_school_survey_on_crime`` — the NCES SSOCS public-use
  dataset page, whose wave-file links enumerate as document pointers (the
  public-use microdata are aggregate-only context, never a place-level
  deployment source).

Every emitted claim is confined to the committed predicate allowlist
(SIG-INGEST-033); a row whose declared columns carry a forbidden person-level
token refuses the capture (:class:`ContentDrift`-shaped
:class:`ForbiddenFieldError`), and a record the adapter cannot type honestly
lands as a recorded ``federal_record_rejected`` row — never a guessed claim.
All eight sources stay ``ingestion_permitted=false``; the operator's OP-26
Wave-D flip under ING-GO-D is the only route to a live run.
"""

from __future__ import annotations

import csv
import io
import json
import re
import zipfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit
from uuid import uuid4
from xml.etree import ElementTree

from parsing.locator import Locator
from resolution.partner_identity import natural_person_signal

from ._data import load_table
from .stages import CaptureRef, Connector, ContentDrift, FetchResult, RunContext, register

CONNECTOR_NAME = "federal_datasets"

#: The eight ACQ-21 registry seats this connector serves (closed set).
SOURCE_IDS = (
    "camreg_us_nces_school_survey_on_crime",
    "legis_us_federal_register_api",
    "statrep_tx_south_padre_island_faa",
    "statrep_us_2024_federal_agency",
    "statrep_us_dhs_ai_use",
    "statrep_us_ice_287_monthly",
    "statrep_us_ice_287_participating",
    "statrep_us_wiretap_summary_tables",
)

_TARGETS_TABLE = "federal_datasets_targets"
_VOCAB_TABLE = "federal_datasets_vocab"

TARGETS_SCHEMA = "sig.federal-dataset-targets/1"
VOCAB_SCHEMA_ID = "sig.federal-datasets-vocab/1"

#: The artifact genre every claim carries — the registered ``connector_run``
#: genre (vocab_artifact_genre; a federal-dataset capture is connector-run
#: evidence, never dressed in a camera-registry or document genre it is not).
_EVIDENCE_GENRE = "connector_run"

#: Subject families minted by this family (entity types declared in
#: ``db/src/db/data/subject_entity_types.toml``).
_KINDS = frozenset({"federal_index", "federal_json", "federal_csv", "federal_xlsx"})


# --- the versioned vocabulary (data, not code — §20) ---------------------------


@cache
def vocab() -> dict[str, Any]:
    """The committed ``sig.federal-datasets-vocab/1`` table (fail-closed on drift)."""
    table = load_table(_VOCAB_TABLE)
    if table.get("schema") != VOCAB_SCHEMA_ID:
        raise ValueError(f"federal datasets vocabulary must be {VOCAB_SCHEMA_ID!r}")
    return table


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab().get("vocab_version") or "unknown")


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (SIG-INGEST-033)."""
    return frozenset(str(p) for p in vocab().get("predicate_allowlist") or ())


def forbidden_predicate_genres() -> frozenset[str]:
    """Predicate GENRES the connector must never write (scope-creep guard)."""
    return frozenset(str(p) for p in vocab().get("forbidden_predicate_genres") or ())


def forbidden_field_tokens() -> tuple[str, ...]:
    """Column-name tokens marking a person-level field (Part VIII screen)."""
    return tuple(str(t) for t in vocab().get("forbidden_field_tokens") or ())


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowlisted, else raise :class:`PredicateNotAllowed`."""
    if predicate not in predicate_allowlist():
        raise PredicateNotAllowed(
            f"the federal_datasets connector may write only "
            f"{sorted(predicate_allowlist())} (SIG-INGEST-033); {predicate!r} is "
            "outside the allowlist — feed content, per-person data and guessed "
            "classes are never emitted."
        )
    return predicate


class ForbiddenFieldError(ValueError):
    """A served payload carried a person-level column the screen refuses (Part VIII)."""


def assert_no_forbidden_columns(columns: Iterable[str], *, source_id: str) -> None:
    """Refuse a tabular payload carrying a forbidden person-level column NAME.

    The mechanical form of the family's Part VIII screen: a CSV/XLSX header
    that names a person, plate, officer, judge, case subject or per-encounter
    field is refused before a single claim is built — the failing column names
    (schema vocabulary, never values) ride the exception for the record.
    """
    offenders = sorted(
        {
            name
            for name in columns
            for token in forbidden_field_tokens()
            if token in str(name).strip().lower()
        }
    )
    if offenders:
        raise ForbiddenFieldError(
            f"capture for source {source_id!r} carries forbidden person-level "
            f"columns {offenders} — the federal_datasets family emits "
            "agency/dataset-level records only (Part VIII / §0.7); the bytes "
            "are refused before any claim is built"
        )


# --- the committed target inventory (data, not code) ---------------------------


@dataclass(frozen=True)
class DatasetTarget:
    """One committed federal-dataset target — identifiers + provenance only."""

    id: str
    source: str
    kind: str
    adapter: str
    url: str
    expect: tuple[str, ...]
    license_spdx: str
    publisher: str
    link_re: str
    resolve_kind: str
    resolve_adapter: str
    evidence: str


@dataclass(frozen=True)
class DatasetInventory:
    """The committed target set with its derivation provenance."""

    source_ref: str
    captured_on: str
    targets: tuple[DatasetTarget, ...]

    def for_source(self, source_id: str) -> tuple[DatasetTarget, ...]:
        return tuple(t for t in self.targets if t.source == source_id)


def _adapter_spec(adapter: str) -> Mapping[str, Any]:
    spec = (vocab().get("adapters") or {}).get(adapter)
    if not isinstance(spec, Mapping):
        raise ValueError(f"federal datasets vocabulary names no adapter {adapter!r}")
    return spec


def load_inventory() -> DatasetInventory:
    """Parse + validate the committed target table (fail-closed on drift).

    A malformed inventory — wrong schema, duplicate or unsorted ids, a row
    naming a source this family does not serve, an unknown kind/adapter, an
    undeclared host, a missing ``expect`` token on an index row — refuses the
    load rather than addressing outside the committed set.
    """
    table = load_table(_TARGETS_TABLE)
    if table.get("schema") != TARGETS_SCHEMA:
        raise ValueError(f"federal datasets inventory schema must be {TARGETS_SCHEMA!r}")
    inv = table.get("inventory") or {}
    hosts = {str(h).lower() for h in (vocab().get("hosts") or [])}
    targets: list[DatasetTarget] = []
    for i, row in enumerate(inv.get("targets") or []):
        if not isinstance(row, dict):
            raise ValueError(f"federal datasets target {i} must be a table")
        tid = str(row.get("id") or "").strip()
        source = str(row.get("source") or "").strip()
        kind = str(row.get("kind") or "").strip()
        adapter = str(row.get("adapter") or "").strip()
        url = str(row.get("url") or "").strip()
        if not all((tid, source, kind, adapter, url)):
            raise ValueError(f"federal datasets target {i} needs id/source/kind/adapter/url")
        if source not in SOURCE_IDS:
            raise ValueError(
                f"federal datasets target {tid!r}: source {source!r} is not one of "
                f"{SOURCE_IDS} — this connector serves no other row"
            )
        if kind not in _KINDS:
            raise ValueError(
                f"federal datasets target {tid!r}: kind {kind!r} is not a member "
                f"of {sorted(_KINDS)}"
            )
        spec = _adapter_spec(adapter)
        if str(spec.get("kind") or "") != kind:
            raise ValueError(
                f"federal datasets target {tid!r}: adapter {adapter!r} reads kind "
                f"{spec.get('kind')!r}, not {kind!r}"
            )
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.username or parts.netloc.lower() not in hosts:
            raise ValueError(
                f"federal datasets target {tid!r}: {url!r} is not an https URL on "
                "a committed host (fail-closed)"
            )
        expect = tuple(str(e) for e in (row.get("expect") or ()) if str(e).strip())
        if kind == "federal_index" and not expect:
            raise ValueError(
                f"federal datasets target {tid!r}: an empty expect list leaves the "
                "index-identity check unenforceable (fail-closed)"
            )
        resolve_kind = str(row.get("resolve_kind") or "").strip()
        resolve_adapter = str(row.get("resolve_adapter") or "").strip()
        if (resolve_kind or resolve_adapter) and not (resolve_kind and resolve_adapter):
            raise ValueError(
                f"federal datasets target {tid!r}: resolve_kind/resolve_adapter "
                "are declared together or not at all"
            )
        if resolve_kind:
            rspec = _adapter_spec(resolve_adapter)
            if str(rspec.get("kind") or "") != resolve_kind:
                raise ValueError(
                    f"federal datasets target {tid!r}: resolve adapter "
                    f"{resolve_adapter!r} reads kind {rspec.get('kind')!r}, "
                    f"not {resolve_kind!r}"
                )
        targets.append(
            DatasetTarget(
                id=tid,
                source=source,
                kind=kind,
                adapter=adapter,
                url=url,
                expect=expect,
                license_spdx=str(row.get("license_spdx") or ""),
                publisher=str(row.get("publisher") or ""),
                link_re=str(row.get("link_re") or ""),
                resolve_kind=resolve_kind,
                resolve_adapter=resolve_adapter,
                evidence=str(row.get("evidence") or ""),
            )
        )
    ids = [t.id for t in targets]
    if len(set(ids)) != len(ids):
        raise ValueError("federal datasets inventory carries duplicate target ids")
    if ids != sorted(ids):
        raise ValueError(
            "federal datasets inventory is not id-sorted (deterministic order required)"
        )
    declared = int(inv.get("target_count") or -1)
    if declared != len(targets):
        raise ValueError(
            f"federal datasets inventory target_count={declared} but {len(targets)} rows committed"
        )
    return DatasetInventory(
        source_ref=str(inv.get("source_ref") or ""),
        captured_on=str(inv.get("captured_on") or ""),
        targets=tuple(targets),
    )


def federal_dataset_targets(source_id: str | None = None) -> list[dict[str, Any]]:
    """The ``{"id","url","kind"}`` targets ``live_targets.toml`` delegates to."""
    inv = load_inventory()
    rows = inv.targets if source_id is None else inv.for_source(source_id)
    return [
        {
            "id": t.id,
            "url": t.url,
            "kind": t.kind,
            "source": t.source,
            "adapter": t.adapter,
        }
        for t in rows
    ]


# --- the parse helpers (pure functions of captured bytes) ----------------------


def _csv_rows(data: bytes) -> list[dict[str, str]]:
    """Stream CSV bytes into row dicts (stdlib; utf-8-sig for BOMs)."""
    text = data.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [dict(r) for r in reader]


def _xlsx_rows(data: bytes) -> list[dict[str, str]]:
    """Stream the first worksheet of a stdlib-read XLSX into row dicts.

    Mirrors the P37.48 workbook lane's approach — inline strings, shared
    strings and numbers only; a workbook without a shared string table or a
    sheet that yields no header row is a parse-level drift the caller sees.
    """
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ElementTree.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("m:si", ns):
                shared.append("".join(t.text or "" for t in si.iter() if t.tag.endswith("}t")))
        sheet_name = next(
            (n for n in zf.namelist() if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", n)),
            None,
        )
        if sheet_name is None:
            raise ContentDrift(
                "federal_datasets",
                "the workbook carries no worksheet",
                details=f"members: {zf.namelist()[:8]}",
            )
        sheet = ElementTree.fromstring(zf.read(sheet_name))
    rows: list[list[str]] = []
    for row in sheet.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
        cells: dict[int, str] = {}
        for cell in row.iter("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
            ref = str(cell.get("r") or "A1")
            col = 0
            for ch in ref:
                if ch.isalpha():
                    col = col * 26 + (ord(ch.upper()) - ord("A") + 1)
                else:
                    break
            value = ""
            v = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
            inline = cell.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}is")
            if cell.get("t") == "s" and v is not None:
                idx = int(v.text or 0)
                value = shared[idx] if 0 <= idx < len(shared) else ""
            elif cell.get("t") == "inlineStr" and inline is not None:
                value = "".join(t.text or "" for t in inline.iter() if t.tag.endswith("}t"))
            elif v is not None and v.text is not None:
                value = v.text
            cells[col] = value
        if cells:
            width = max(cells)
            rows.append([cells.get(c, "") for c in range(1, width + 1)])
    if not rows:
        return []
    header = [str(h).strip() for h in rows[0]]
    return [
        {header[i]: row[i] for i in range(min(len(header), len(row))) if header[i]}
        for row in rows[1:]
    ]


class _LinkScanner(HTMLParser):
    """Lift ``<a href>`` links (+ their text) from an index page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            attr = {k.lower(): (v or "") for k, v in attrs}
            self._href = attr.get("href") or None
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join("".join(self._text).split())))
            self._href = None
            self._text = []


def _index_links(data: bytes, base_url: str) -> list[tuple[str, str]]:
    """``(absolute_url, link_text)`` pairs off an HTML index page."""
    scanner = _LinkScanner()
    scanner.feed(data.decode("utf-8", errors="replace"))
    out: list[tuple[str, str]] = []
    for href, text in scanner.links:
        if href.startswith(("mailto:", "javascript:", "#")):
            continue
        out.append((urljoin(base_url, href), text))
    return out


def _slug(value: str) -> str:
    """A subject-key-safe slug: lowercased, ``:``-free, whitespace→``-``."""
    return re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower()).strip("-")


# --- per-adapter emits (pure) --------------------------------------------------


def _evidence(url: str, row_index: int) -> dict[str, Any]:
    return {
        "source_url": url,
        "extraction_method": "federal_datasets",
        "locator": Locator.row(row_index).to_row(),
    }


def _stamp(row: dict[str, Any], *, source_id: str, license_spdx: str) -> dict[str, Any]:
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    if license_spdx:
        row.setdefault("license", license_spdx)
    return row


def _claim(
    subject_id: str,
    predicate: str,
    value: Any,
    raw_value: str,
    evidence: Mapping[str, Any],
    *,
    source_id: str,
    license_spdx: str,
    candidate: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "record_kind": "claim",
        "subject_id": subject_id,
        "predicate_id": assert_predicate_allowed(predicate),
        "raw_value": raw_value,
        "value": value,
        "evidence_genre": _EVIDENCE_GENRE,
        "evidence": dict(evidence),
    }
    if candidate is not None:
        row["candidate_identifier"] = dict(candidate)
    return _stamp(row, source_id=source_id, license_spdx=license_spdx)


def _rejection_row(
    *,
    source_id: str,
    license_spdx: str,
    target_id: str,
    reason: str,
    detail: str,
    feature_index: int,
    fields: Iterable[str],
) -> dict[str, Any]:
    """The recorded disposition for a record that failed closed — never a claim."""
    return _stamp(
        {
            "record_kind": "federal_record_rejected",
            "subject_id": f"federal_document:{source_id}:{target_id}:rejected:{feature_index}",
            "predicate_id": assert_predicate_allowed("external_id"),
            "raw_value": reason,
            "rejection_reason": reason,
            "rejection_detail": detail,
            "feature_index": feature_index,
            "field_names_present": sorted(str(k) for k in fields),
            "target_id": target_id,
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )


def _document_claims(
    *,
    source_id: str,
    license_spdx: str,
    publisher: str,
    url: str,
    title: str,
    index: int,
) -> list[dict[str, Any]]:
    """One ``federal_document`` pointer record — the link, never the content."""
    subject_id = f"federal_document:{source_id}:{_slug(urlsplit(url).path or url)}"
    ev = _evidence(url, index)
    entity = _stamp(
        {
            "record_kind": "federal_document",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("document"),
            "external_id": urlsplit(url).path.rsplit("/", 1)[-1] or url,
            "raw_value": url,
            "title": title,
            "published_by_label": publisher,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )
    rows = [entity]
    for predicate, value in (
        ("external_id", entity["external_id"]),
        ("document", url),
        ("title", title),
        ("published_by", publisher),
        ("country", "US"),
    ):
        if str(value).strip():
            rows.append(
                _claim(
                    subject_id,
                    predicate,
                    value,
                    str(value),
                    ev,
                    source_id=source_id,
                    license_spdx=license_spdx,
                )
            )
    return rows


def _fr_document_claims(
    *,
    source_id: str,
    license_spdx: str,
    publisher: str,
    doc: Mapping[str, Any],
    index: int,
    url: str,
) -> list[dict[str, Any]]:
    """One ``federal_register_document`` record — the API's own metadata."""
    number = str(doc.get("document_number") or "").strip()
    if not number:
        return [
            _rejection_row(
                source_id=source_id,
                license_spdx=license_spdx,
                target_id="federal_register_search",
                reason="missing",
                detail="documents.json result carries no document_number",
                feature_index=index,
                fields=doc,
            )
        ]
    subject_id = f"federal_register_document:{source_id}:{number}"
    ev = _evidence(url, index)
    agencies = (
        "; ".join(
            sorted(
                {
                    str(a.get("name") or "").strip()
                    for a in doc.get("agencies") or ()
                    if isinstance(a, Mapping) and str(a.get("name") or "").strip()
                }
            )
        )
        or publisher
    )
    entity = _stamp(
        {
            "record_kind": "federal_register_document",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("document"),
            "external_id": number,
            "raw_value": number,
            "title": str(doc.get("title") or "").strip(),
            "document_type": str(doc.get("type") or "").strip(),
            "publication_date": str(doc.get("publication_date") or "").strip(),
            "published_by_label": agencies,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )
    rows = [entity]
    for predicate, value in (
        ("external_id", number),
        ("title", entity["title"]),
        ("document", str(doc.get("html_url") or "").strip()),
        ("citation", str(doc.get("citation") or "").strip()),
        ("published_by", agencies),
        ("platform", "federalregister.gov"),
        ("country", "US"),
    ):
        if str(value).strip():
            rows.append(
                _claim(
                    subject_id,
                    predicate,
                    value,
                    str(value),
                    ev,
                    source_id=source_id,
                    license_spdx=license_spdx,
                )
            )
    return rows


def _ai_use_case_claims(
    *,
    source_id: str,
    license_spdx: str,
    publisher: str,
    spec: Mapping[str, Any],
    row: Mapping[str, Any],
    index: int,
    url: str,
) -> list[dict[str, Any]]:
    """One ``ai_use_case`` record — the inventory's own literals only."""
    fields = spec.get("fields") or {}
    ident = str(row.get(str(fields.get("id") or "")) or "").strip()
    agency = str(row.get(str(fields.get("agency") or "")) or "").strip()
    if not ident or not agency:
        return [
            _rejection_row(
                source_id=source_id,
                license_spdx=license_spdx,
                target_id=str(spec.get("target_id") or "ai_inventory"),
                reason="missing",
                detail="ai-inventory row carries no use-case id or agency",
                feature_index=index,
                fields=row,
            )
        ]
    subject_id = f"ai_use_case:{source_id}:{_slug(agency)}:{_slug(ident)}"
    ev = _evidence(url, index)
    name = str(row.get(str(fields.get("name") or "")) or "").strip()
    topic = str(row.get(str(fields.get("topic") or "")) or "").strip()
    stage = str(row.get(str(fields.get("stage") or "")) or "").strip()
    entity = _stamp(
        {
            "record_kind": "ai_use_case",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("external_id"),
            "external_id": ident,
            "raw_value": ident,
            "title": name,
            "agency": agency,
            "topic_area": topic,
            "dev_stage": stage,
            "published_by_label": agency,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )
    rows = [entity]
    for predicate, value in (
        ("external_id", ident),
        ("title", name),
        ("published_by", agency),
        ("technology_category", topic),
        ("in_use", stage),
        ("country", "US"),
    ):
        if str(value).strip():
            rows.append(
                _claim(
                    subject_id,
                    predicate,
                    value,
                    str(value),
                    ev,
                    source_id=source_id,
                    license_spdx=license_spdx,
                )
            )
    return rows


def _roster_claims(
    *,
    source_id: str,
    license_spdx: str,
    spec: Mapping[str, Any],
    row: Mapping[str, Any],
    index: int,
    url: str,
) -> list[dict[str, Any]]:
    """One ``agency_registry_entry`` record per 287(g) roster row.

    A person-shaped agency name never mints a subject (S7-shaped screen —
    the roster is agency-level by schema, the person-shape check is the
    fail-closed second gate); a dropped row is recorded, never emitted.
    """
    fields = spec.get("fields") or {}
    name = str(row.get(str(fields.get("agency") or "")) or "").strip()
    state = str(row.get(str(fields.get("state") or "")) or "").strip()
    if not name:
        return [
            _rejection_row(
                source_id=source_id,
                license_spdx=license_spdx,
                target_id=str(spec.get("target_id") or "ice_287g_roster"),
                reason="missing",
                detail="287(g) roster row carries no agency name",
                feature_index=index,
                fields=row,
            )
        ]
    if natural_person_signal(name) is not None:
        return [
            _rejection_row(
                source_id=source_id,
                license_spdx=license_spdx,
                target_id=str(spec.get("target_id") or "ice_287g_roster"),
                reason="person_shaped_agency",
                detail="agency key is natural-person-shaped — never a subject",
                feature_index=index,
                fields=row,
            )
        ]
    subject_id = f"agency_registry_entry:{source_id}:{_slug(state)}:{_slug(name)}"
    ev = _evidence(url, index)
    county = str(row.get(str(fields.get("county") or "")) or "").strip()
    agency_type = str(row.get(str(fields.get("type") or "")) or "").strip()
    entity = _stamp(
        {
            "record_kind": "agency_registry_entry",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("agency_registry_entry"),
            "external_id": f"{state}:{name}" if state else name,
            "raw_value": name,
            "agency_state": state,
            "agency_county": county,
            "agency_type": agency_type,
            "support_type": str(row.get(str(fields.get("support_type") or "")) or "").strip(),
            "signed_date": str(row.get(str(fields.get("signed") or "")) or "").strip(),
            "moa_url": urljoin(url, str(row.get(str(fields.get("moa") or "")) or "").strip())
            if str(row.get(str(fields.get("moa") or "")) or "").strip()
            else "",
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )
    rows = [entity]
    claim_pairs: list[tuple[str, Any, Mapping[str, str] | None]] = [
        ("agency_name", name, {"scheme": "agency_registry.agency_name", "value": name}),
        ("agency_state", state, {"scheme": "us.state_abbr", "value": state}),
        ("agency_county", county, None),
        ("agency_type", agency_type, None),
        ("external_id", entity["external_id"], None),
        ("country", "US", None),
    ]
    for predicate, value, candidate in claim_pairs:
        if str(value).strip():
            rows.append(
                _claim(
                    subject_id,
                    predicate,
                    value,
                    str(value),
                    ev,
                    source_id=source_id,
                    license_spdx=license_spdx,
                    candidate=candidate,
                )
            )
    return rows


# --- the connector -------------------------------------------------------------


@register
class FederalDatasetsConnector(Connector):
    """The `federal_datasets` connector — federal dataset files and search APIs.

    ``discover`` walks exactly the committed inventory (an uncommitted target
    list is refused loud); ``fetch`` egresses through the shared politeness
    layer only; ``parse``/``extract``/``normalize`` are pure functions of the
    captured bytes. The one bounded continuation pass resolves an index
    target's declared child link (the ICE 287(g) dated workbook) — never a
    recursive crawl.
    """

    name = CONNECTOR_NAME
    version = "1.0.0"
    ingestion_mode = "bulk_file_download"
    incrementality = "re-issue detection via content-addressed capture digests"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — the committed inventory rows only."""
        return list(ctx.parameters.get("targets", []))

    def discover_more(
        self, ctx: RunContext, captures: list[CaptureRef] | Any
    ) -> list[Mapping[str, Any]]:
        """Resolve an index target's declared child link (one bounded pass).

        The ICE 287(g) landing page names the current dated roster workbook;
        the resolved URL becomes a ``federal_xlsx`` child target whose bytes
        ``fetch()`` egresses for — link discovery because the filename
        changes each issue (I4-C280). A ``resolve`` row whose index carried
        no matching link records a drift finding rather than guessing a URL.
        """
        resolved: list[Mapping[str, Any]] = []
        # Two seats can share one landing URL (the ICE 287(g) index lanes) —
        # the source id disambiguates which committed row a capture resolves
        # under; a same-URL row for a different source is never consulted.
        by_url = {t.url: t for t in load_inventory().targets if t.source == ctx.source.id}
        for capture in captures:
            trow = by_url.get(str(capture.source_uri))
            if trow is None or not trow.resolve_kind:
                continue
            data = ctx.captures.get(capture.digest)
            links = _index_links(data, str(capture.source_uri))
            hits = [u for u, _t in links if re.search(trow.link_re, u)]
            if not hits:
                raise ContentDrift(
                    ctx.source.id,
                    "the index page carries no link matching the declared "
                    "resolve pattern — the roster filename moved",
                    details=f"pattern {trow.link_re!r} on {capture.source_uri}",
                )
            for url in sorted(set(hits)):
                child = {
                    "id": f"{trow.id}:{urlsplit(url).path.rsplit('/', 1)[-1]}",
                    "url": url,
                    "kind": trow.resolve_kind,
                    "adapter": trow.resolve_adapter,
                    "source": trow.source,
                    "license_spdx": trow.license_spdx,
                    "publisher": trow.publisher,
                    "resolved_from": str(capture.source_uri),
                }
                ctx.resolved_targets[url] = child
                resolved.append(child)
        return resolved

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        url = str(target["url"])
        parts = urlsplit(url)
        hosts = {str(h).lower() for h in (vocab().get("hosts") or [])}
        if parts.scheme != "https" or parts.netloc.lower() not in hosts:
            raise ContentDrift(
                ctx.source.id,
                "a resolved or committed target left the committed host set",
                details=f"{url!r} is not https on {sorted(hosts)} (fail-closed)",
            )
        return ctx.fetcher.fetch(url)

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes by the target's declared kind (pure).

        A non-JSON Federal Register payload, a CSV/XLSX that yields no rows,
        or an index page carrying no ``expect`` marker is
        :class:`ContentDrift` — recorded loud, never a silent empty set.
        """
        data = ctx.captures.get(capture.digest)
        target = self._target_for(ctx, capture.source_uri)
        kind = str(target.get("kind") or "")
        if kind == "federal_json":
            try:
                doc = json.loads(data)
            except (ValueError, TypeError) as exc:
                head = data[:64] if isinstance(data, (bytes, bytearray)) else str(data)[:64]
                raise ContentDrift(
                    ctx.source.id,
                    "the federal JSON endpoint returned non-JSON content",
                    details=f"{len(data)} bytes; starts {head!r} ({exc.__class__.__name__})",
                ) from exc
            if not isinstance(doc, Mapping) or not isinstance(doc.get("results"), list):
                raise ContentDrift(
                    ctx.source.id,
                    "the documents.json payload has no 'results' list",
                    details=(
                        "top-level keys: "
                        f"{sorted(doc) if isinstance(doc, Mapping) else type(doc).__name__}"
                    ),
                )
            return {"kind": kind, "target": target, "payload": doc, "capture": capture}
        if kind == "federal_index":
            text = data.decode("utf-8", errors="replace")
            missing = [e for e in target.get("expect") or () if e not in text]
            if missing:
                raise ContentDrift(
                    ctx.source.id,
                    "the index page no longer carries its declared markers",
                    details=f"missing {missing} on {capture.source_uri}",
                )
            links = _index_links(data, str(capture.source_uri))
            return {
                "kind": kind,
                "target": target,
                "payload": {"links": links},
                "capture": capture,
            }
        if kind == "federal_csv":
            rows = _csv_rows(data)
            if not rows:
                raise ContentDrift(
                    ctx.source.id,
                    "the CSV capture produced zero rows",
                    details=f"{len(data)} bytes on {capture.source_uri}",
                )
            return {
                "kind": kind,
                "target": target,
                "payload": {"rows": rows},
                "capture": capture,
            }
        if kind == "federal_xlsx":
            try:
                rows = _xlsx_rows(data)
            except zipfile.BadZipFile as exc:
                raise ContentDrift(
                    ctx.source.id,
                    "the XLSX capture is not a readable workbook",
                    details=f"{len(data)} bytes ({exc.__class__.__name__})",
                ) from exc
            if not rows:
                raise ContentDrift(
                    ctx.source.id,
                    "the XLSX capture produced zero rows",
                    details=f"{len(data)} bytes on {capture.source_uri}",
                )
            return {
                "kind": kind,
                "target": target,
                "payload": {"rows": rows},
                "capture": capture,
            }
        raise ContentDrift(
            ctx.source.id,
            f"a capture arrived from a target of undeclared kind {kind!r}",
            details=f"url {capture.source_uri}",
        )

    def _target_for(self, ctx: RunContext, url: str) -> Mapping[str, Any]:
        """Resolve the committed (or resolved-child) target behind a capture."""
        if url in ctx.resolved_targets:
            return ctx.resolved_targets[url]
        for target in ctx.parameters.get("targets", []) or []:
            if str(target.get("url")) == url:
                return target
        inv = load_inventory()
        for t in inv.targets:
            if t.url == url:
                return {
                    "id": t.id,
                    "url": t.url,
                    "kind": t.kind,
                    "adapter": t.adapter,
                    "source": t.source,
                }
        raise ContentDrift(
            ctx.source.id,
            "a capture arrived whose URL matches no committed or resolved target",
            details=f"url {url}",
        )

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw claim rows from the parsed payload — adapter-dispatched (P2)."""
        target = parsed.get("target") or {}
        capture = parsed.get("capture")
        url = str(getattr(capture, "source_uri", "") or target.get("url") or "")
        adapter = str(target.get("adapter") or "")
        spec = _adapter_spec(adapter)
        source_id = ctx.source.id
        inv = load_inventory()
        trow = next((t for t in inv.targets if t.id == target.get("id")), None)
        license_spdx = (
            str(target.get("license_spdx") or "")
            or (trow.license_spdx if trow else "")
            or str(spec.get("license_spdx") or "")
        )
        publisher = (
            str(target.get("publisher") or "")
            or (trow.publisher if trow else "")
            or str(spec.get("publisher") or "")
        )
        payload = parsed.get("payload") or {}
        rows: list[Mapping[str, Any]] = []
        if adapter == "fr_documents":
            for i, doc in enumerate(payload.get("results") or []):
                if not isinstance(doc, Mapping):
                    continue
                rows.extend(
                    _fr_document_claims(
                        source_id=source_id,
                        license_spdx=license_spdx,
                        publisher=publisher,
                        doc=doc,
                        index=i,
                        url=url,
                    )
                )
            return rows
        if adapter == "index_links":
            link_re = str(
                (trow.link_re if trow else "") or target.get("link_re") or spec.get("link_re") or ""
            )
            for i, (link, text) in enumerate(payload.get("links") or []):
                if link_re and not re.search(link_re, link):
                    continue
                rows.extend(
                    _document_claims(
                        source_id=source_id,
                        license_spdx=license_spdx,
                        publisher=publisher,
                        url=link,
                        title=text or urlsplit(link).path.rsplit("/", 1)[-1],
                        index=i,
                    )
                )
            return rows
        if adapter == "ai_inventory_csv":
            body = payload.get("rows") or []
            header = list(body[0]) if body else []
            assert_no_forbidden_columns(header, source_id=source_id)
            for i, row in enumerate(body):
                rows.extend(
                    _ai_use_case_claims(
                        source_id=source_id,
                        license_spdx=license_spdx,
                        publisher=publisher,
                        spec=spec,
                        row=row,
                        index=i,
                        url=url,
                    )
                )
            return rows
        if adapter == "ice_287g_roster_xlsx":
            body = payload.get("rows") or []
            header = list(body[0]) if body else []
            assert_no_forbidden_columns(header, source_id=source_id)
            for i, row in enumerate(body):
                rows.extend(
                    _roster_claims(
                        source_id=source_id,
                        license_spdx=license_spdx,
                        spec=spec,
                        row=row,
                        index=i,
                        url=url,
                    )
                )
            return rows
        raise ContentDrift(
            ctx.source.id,
            f"no adapter {adapter!r} is declared for this family's emit",
            details=f"target {target.get('id')!r}",
        )

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """The emit is already typed; the allowlist was enforced per claim."""
        out: list[dict[str, Any]] = []
        for row in raw_claims:
            if row.get("record_kind") == "claim" or row.get("record_kind") in (
                "federal_document",
                "federal_register_document",
                "ai_use_case",
                "agency_registry_entry",
                "federal_record_rejected",
            ):
                out.append(dict(row))
        return out

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Stamp the generated ``claim_id`` + transaction time each L1 row needs."""
        out: list[dict[str, Any]] = []
        for row in linked:
            if row.get("record_kind") == "claim" or (
                row.get("predicate_id") in ("document", "external_id", "agency_registry_entry")
                and row.get("record_kind") != "federal_record_rejected"
            ):
                out.append(
                    {
                        **row,
                        "claim_id": str(uuid4()),
                        "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                    }
                )
            else:
                out.append(dict(row))
        return out


__all__ = [
    "CONNECTOR_NAME",
    "SOURCE_IDS",
    "DatasetInventory",
    "DatasetTarget",
    "FederalDatasetsConnector",
    "ForbiddenFieldError",
    "PredicateNotAllowed",
    "assert_no_forbidden_columns",
    "assert_predicate_allowed",
    "federal_dataset_targets",
    "forbidden_field_tokens",
    "forbidden_predicate_genres",
    "load_inventory",
    "predicate_allowlist",
    "vocab",
    "vocab_version",
]
