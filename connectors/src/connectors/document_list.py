# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `document_list` connector family (P37.52 / R11-ACQ-25, I8 §6.2).

An index-page -> PDF/HTML enumerator for public pages with no platform: the
four cooperative contract-document pages (Florida Buy / PAEC, WSIPC
RFP 24-01, NERIC's Gaggle service page, the NASPO ValuePoint portfolio), the
Illinois GATA CSFA award list, the Massachusetts capital-plan BWC line, the
Ohio OCJS BWC RFP (a digital-native PDF) and the Massachusetts EOPSS BWC
award announcement. It emits ``contract`` and ``grant_award`` records — an
award or contract fact is never a deployment.

The committed target inventory lives in ``data/document_list_targets.toml``
and the versioned vocabulary in ``data/document_list_vocab.toml`` (data, not
code — SIG-ENG-001 / SIG-INGEST-038). It serves the eight ACQ-25 registry
seats:

* ``procportal_fl_florida_buy_cooperative`` — the Florida Buy (PAEC) Gaggle
  contract page: its seven served contract documents enumerate as
  ``document_list_document`` pointers (contents never fetched — P8-2) and
  the reviewed cooperative contract mints ONE ``contract:`` record.
* ``procportal_wa_wsipc_rfp_24`` — the WSIPC RFP 24-01 page: the public
  notice, RFP, sample contract, addenda and publication affidavits enumerate
  as pointers (RB-07 — facts and citations only: no verbatim ``description``
  claim).
* ``procportal_ny_northeastern_regional`` — the NERIC Gaggle service-
  catalogue page: a service OFFERING, never an executed contract — the page
  record itself carries the declared vendor/title facts and its document
  links enumerate as pointers.
* ``procportal_us_naspo_valuepoint_portfolio`` — the NASPO ValuePoint
  Public-Safety/Video portfolio page (RB-07): the supplier master-agreement
  and participating-addenda links enumerate as pointers; the portfolio
  record mints ONE ``contract:`` row on the reviewed portfolio reference.
* ``camreg_ma_massachusetts_capital`` — the FY2025-2029 Capital Investment
  Plan line S027: the programme record mints on a ``funding_instrument:``
  subject and each served fiscal-year row mints a per-FY ``grant_award``
  allocation.
* ``grant_il_illinois_gata_csfa`` — the GATA CSFA 569-00-3496 AwardList:
  each served row mints one ``grant_award`` on a ``funding_instrument:``
  subject keyed on the award's own id; a person-shaped grantee is a recorded
  rejection, never a minted subject (the reviewed grantees are units of
  government).
* ``grant_oh_ohio_criminal_justice`` — the OCJS FY2026 BWC RFP, the family's
  one ``doclist_pdf`` target: the ``pdf_text`` layer-3 engine reads the text
  layer; the programme record carries the declared programme facts and the
  served award-window/statistic literals. The RFP serves no recipient list,
  so no award rows can mint by construction.
* ``grant_ma_massachusetts_law_enforcement`` — the EOPSS OGR final-round
  announcement: each listed recipient mints a ``grant_award``
  (organisation-shaped names only — a person-shaped entry is a recorded
  rejection); the programme record carries the served totals.

Every emitted claim is confined to the committed predicate allowlist
(SIG-INGEST-033); a served table whose header carries a forbidden person-
level token refuses the capture (:class:`ForbiddenFieldError`), and a
record the adapter cannot type honestly lands as a recorded
``document_list_rejected`` row — never a guessed claim. All eight sources
stay ``ingestion_permitted=false``; the operator's OP-26 Wave-D flips under
ING-GO-D are the only route to a live run (none performed or claimed here —
``live_verification=false``).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from html.parser import HTMLParser
from typing import Any
from urllib.parse import urljoin, urlsplit
from uuid import uuid4

from parsing.document import pdf_text_pages
from parsing.locator import Locator
from resolution.partner_identity import natural_person_signal

from ._data import load_table
from .stages import CaptureRef, Connector, ContentDrift, FetchResult, RunContext, register

CONNECTOR_NAME = "document_list"

#: The eight ACQ-25 registry seats this connector serves (closed set).
SOURCE_IDS = (
    "camreg_ma_massachusetts_capital",
    "grant_il_illinois_gata_csfa",
    "grant_ma_massachusetts_law_enforcement",
    "grant_oh_ohio_criminal_justice",
    "procportal_fl_florida_buy_cooperative",
    "procportal_ny_northeastern_regional",
    "procportal_us_naspo_valuepoint_portfolio",
    "procportal_wa_wsipc_rfp_24",
)

_TARGETS_TABLE = "document_list_targets"
_VOCAB_TABLE = "document_list_vocab"

TARGETS_SCHEMA = "sig.document-list-targets/1"
VOCAB_SCHEMA_ID = "sig.document-list-vocab/1"

#: The artifact genre every claim carries — the registered ``connector_run``
#: genre (a document-list capture is connector-run evidence, never dressed in
#: a camera-registry or document genre it is not).
_EVIDENCE_GENRE = "connector_run"

#: Subject families minted by this family (entity types declared in
#: ``db/src/db/data/subject_entity_types.toml``).
_KINDS = frozenset({"doclist_html", "doclist_pdf"})

_ADAPTERS = frozenset(
    {
        "contract_docs_page",
        "service_page",
        "award_table",
        "capital_line",
        "rfp_pdf",
        "release_awards",
    }
)

#: The entity/record kinds the emit stamps (normalize/load keep exactly these).
_EMIT_KINDS = frozenset(
    {
        "contract",
        "funding_instrument",
        "grant_award",
        "document_list_document",
        "document_list_rejected",
    }
)


# --- the versioned vocabulary (data, not code — §20) ---------------------------


@cache
def vocab() -> dict[str, Any]:
    """The committed ``sig.document-list-vocab/1`` table (fail-closed on drift)."""
    table = load_table(_VOCAB_TABLE)
    if table.get("schema") != VOCAB_SCHEMA_ID:
        raise ValueError(f"document list vocabulary must be {VOCAB_SCHEMA_ID!r}")
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
            f"the document_list connector may write only "
            f"{sorted(predicate_allowlist())} (SIG-INGEST-033); {predicate!r} is "
            "outside the allowlist — person-level data, deployments and guessed "
            "classes are never emitted."
        )
    return predicate


class ForbiddenFieldError(ValueError):
    """A served table carried a person-level column the screen refuses (Part VIII)."""


def assert_no_forbidden_columns(columns: Iterable[str], *, source_id: str) -> None:
    """Refuse a tabular payload carrying a forbidden person-level column NAME.

    The mechanical form of the family's Part VIII screen: a table header that
    names a person, plate, officer, judge, case subject or per-encounter field
    is refused before a single claim is built — the failing column names
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
            f"columns {offenders} — the document_list family emits "
            "organisation/programme-level records only (Part VIII / §0.7); the "
            "bytes are refused before any claim is built"
        )


# --- the committed target inventory (data, not code) ---------------------------


@dataclass(frozen=True)
class DocumentListTarget:
    """One committed document-list target — identifiers + reviewed declarations."""

    id: str
    source: str
    kind: str
    adapter: str
    url: str
    publisher: str
    jurisdiction: str
    title: str
    vendor: str
    facts_citations_only: bool
    link_re: str
    list_marker: str
    expect: tuple[str, ...]
    contract: tuple[tuple[str, str], ...]
    program: tuple[tuple[str, str], ...]
    columns: tuple[tuple[str, str], ...]
    evidence: str


@dataclass(frozen=True)
class DocumentListInventory:
    """The committed target set with its derivation provenance."""

    source_ref: str
    captured_on: str
    targets: tuple[DocumentListTarget, ...]

    def for_source(self, source_id: str) -> tuple[DocumentListTarget, ...]:
        return tuple(t for t in self.targets if t.source == source_id)


def _adapter_spec(adapter: str) -> Mapping[str, Any]:
    spec = (vocab().get("adapters") or {}).get(adapter)
    if not isinstance(spec, Mapping):
        raise ValueError(f"document list vocabulary names no adapter {adapter!r}")
    return spec


def _pairs(row: Mapping[str, Any], key: str) -> tuple[tuple[str, str], ...]:
    block = row.get(key) or {}
    if not isinstance(block, Mapping):
        raise ValueError(f"document list target {row.get('id')!r}: {key} must be a table")
    return tuple((str(k), str(v)) for k, v in block.items())


def load_inventory() -> DocumentListInventory:
    """Parse + validate the committed target table (fail-closed on drift).

    A malformed inventory — wrong schema, duplicate or unsorted ids, a row
    naming a source this family does not serve, an unknown kind/adapter, an
    undeclared host, a missing ``expect`` token — refuses the load rather than
    addressing outside the committed set.
    """
    table = load_table(_TARGETS_TABLE)
    if table.get("schema") != TARGETS_SCHEMA:
        raise ValueError(f"document list inventory schema must be {TARGETS_SCHEMA!r}")
    inv = table.get("inventory") or {}
    hosts = {str(h).lower() for h in (vocab().get("hosts") or [])}
    targets: list[DocumentListTarget] = []
    for i, row in enumerate(inv.get("targets") or []):
        if not isinstance(row, dict):
            raise ValueError(f"document list target {i} must be a table")
        tid = str(row.get("id") or "").strip()
        source = str(row.get("source") or "").strip()
        kind = str(row.get("kind") or "").strip()
        adapter = str(row.get("adapter") or "").strip()
        url = str(row.get("url") or "").strip()
        if not all((tid, source, kind, adapter, url)):
            raise ValueError(f"document list target {i} needs id/source/kind/adapter/url")
        if source not in SOURCE_IDS:
            raise ValueError(
                f"document list target {tid!r}: source {source!r} is not one of "
                f"{SOURCE_IDS} — this connector serves no other row"
            )
        if kind not in _KINDS:
            raise ValueError(
                f"document list target {tid!r}: kind {kind!r} is not a member of {sorted(_KINDS)}"
            )
        if adapter not in _ADAPTERS:
            raise ValueError(
                f"document list target {tid!r}: adapter {adapter!r} is not a member "
                f"of {sorted(_ADAPTERS)}"
            )
        spec = _adapter_spec(adapter)
        if str(spec.get("kind") or "") != kind:
            raise ValueError(
                f"document list target {tid!r}: adapter {adapter!r} reads kind "
                f"{spec.get('kind')!r}, not {kind!r}"
            )
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.username or parts.netloc.lower() not in hosts:
            raise ValueError(
                f"document list target {tid!r}: {url!r} is not an https URL on "
                "a committed host (fail-closed)"
            )
        expect = tuple(str(e) for e in (row.get("expect") or ()) if str(e).strip())
        if not expect:
            raise ValueError(
                f"document list target {tid!r}: an empty expect list leaves the "
                "page-identity check unenforceable (fail-closed)"
            )
        targets.append(
            DocumentListTarget(
                id=tid,
                source=source,
                kind=kind,
                adapter=adapter,
                url=url,
                publisher=str(row.get("publisher") or ""),
                jurisdiction=str(row.get("jurisdiction") or ""),
                title=str(row.get("title") or ""),
                vendor=str(row.get("vendor") or ""),
                facts_citations_only=bool(row.get("facts_citations_only") or False),
                link_re=str(row.get("link_re") or ""),
                list_marker=str(row.get("list_marker") or ""),
                expect=expect,
                contract=_pairs(row, "contract"),
                program=_pairs(row, "program"),
                columns=_pairs(row, "columns"),
                evidence=str(row.get("evidence") or ""),
            )
        )
    ids = [t.id for t in targets]
    if len(set(ids)) != len(ids):
        raise ValueError("document list inventory carries duplicate target ids")
    if ids != sorted(ids):
        raise ValueError("document list inventory is not id-sorted (deterministic order required)")
    declared = int(inv.get("target_count") or -1)
    if declared != len(targets):
        raise ValueError(
            f"document list inventory target_count={declared} but {len(targets)} rows committed"
        )
    return DocumentListInventory(
        source_ref=str(inv.get("source_ref") or ""),
        captured_on=str(inv.get("captured_on") or ""),
        targets=tuple(targets),
    )


def document_list_targets(source_id: str | None = None) -> list[dict[str, Any]]:
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


class _LinkScanner(HTMLParser):
    """Lift ``<a href>`` links (+ their text) off a page."""

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
    """``(absolute_url, link_text)`` pairs off an HTML page."""
    scanner = _LinkScanner()
    scanner.feed(data.decode("utf-8", errors="replace"))
    out: list[tuple[str, str]] = []
    for href, text in scanner.links:
        if href.startswith(("mailto:", "javascript:", "#")):
            continue
        out.append((urljoin(base_url, href), text))
    return out


class _TableParser(HTMLParser):
    """Collect ``<table>`` bodies as ``(header_cells, data_rows)``."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[tuple[list[str], list[list[str]]]] = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._cell_is_header = False
        self._cell: list[str] = []
        self._row: list[tuple[str, bool]] = []
        self._rows: list[list[tuple[str, bool]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "table":
            self._in_table = True
            self._rows = []
        elif tag == "tr" and self._in_table:
            self._in_row = True
            self._row = []
        elif tag in {"th", "td"} and self._in_row:
            self._in_cell = True
            self._cell_is_header = tag == "th"
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._in_cell:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"th", "td"} and self._in_cell:
            self._row.append((" ".join("".join(self._cell).split()), self._cell_is_header))
            self._in_cell = False
            self._cell = []
        elif tag == "tr" and self._in_row:
            if self._row:
                self._rows.append(self._row)
            self._in_row = False
        elif tag == "table" and self._in_table:
            header: list[str] = []
            body: list[list[str]] = []
            for r in self._rows:
                cells = [text for text, _h in r]
                if not header and all(h for _t, h in r):
                    header = cells
                elif header:
                    body.append(cells)
                elif not header:
                    # A table with no <th> row: first row is the header cells.
                    header = cells
            if header:
                self.tables.append((header, body))
            self._in_table = False


def _html_tables(data: bytes) -> list[tuple[list[str], list[list[str]]]]:
    """``(header, rows)`` per ``<table>`` in the captured HTML."""
    parser = _TableParser()
    parser.feed(data.decode("utf-8", errors="replace"))
    return parser.tables


class _ListItemScanner(HTMLParser):
    """Collect ``<li>`` item text (the release body's recipient list)."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[str] = []
        self._in_li = False
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "li":
            self._in_li = True
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._in_li:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "li" and self._in_li:
            item = " ".join("".join(self._text).split())
            if item:
                self.items.append(item)
            self._in_li = False
            self._text = []


def _list_items(data: bytes) -> list[str]:
    """The ``<li>`` item texts in document order."""
    scanner = _ListItemScanner()
    scanner.feed(data.decode("utf-8", errors="replace"))
    return scanner.items


def _slug(value: str) -> str:
    """A subject-key-safe slug: lowercased, ``:``-free, whitespace->``-``."""
    return re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower()).strip("-")


# --- per-adapter emits (pure) --------------------------------------------------


def _evidence(url: str, row_index: int) -> dict[str, Any]:
    return {
        "source_url": url,
        "extraction_method": "document_list",
        "locator": Locator.row(row_index).to_row(),
    }


def _stamp(row: dict[str, Any], *, source_id: str) -> dict[str, Any]:
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    return row


def _claim(
    subject_id: str,
    predicate: str,
    value: Any,
    raw_value: str,
    evidence: Mapping[str, Any],
    *,
    source_id: str,
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
    return _stamp(row, source_id=source_id)


def _rejection_row(
    *,
    source_id: str,
    target_id: str,
    reason: str,
    detail: str,
    feature_index: int,
    fields: Iterable[str],
) -> dict[str, Any]:
    """The recorded disposition for a record that failed closed — never a claim."""
    return _stamp(
        {
            "record_kind": "document_list_rejected",
            "subject_id": (
                f"document_list_document:{source_id}:{target_id}:rejected:{feature_index}"
            ),
            "predicate_id": assert_predicate_allowed("external_id"),
            "raw_value": reason,
            "rejection_reason": reason,
            "rejection_detail": detail,
            "feature_index": feature_index,
            "field_names_present": sorted(str(k) for k in fields),
            "target_id": target_id,
        },
        source_id=source_id,
    )


def _pointer_claims(
    *,
    source_id: str,
    publisher: str,
    jurisdiction: str,
    url: str,
    title: str,
    index: int,
) -> list[dict[str, Any]]:
    """One ``document_list_document`` pointer record — the link, never the content."""
    subject_id = f"document_list_document:{source_id}:{_slug(urlsplit(url).path or url)}"
    ev = _evidence(url, index)
    entity = _stamp(
        {
            "record_kind": "document_list_document",
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
    )
    rows = [entity]
    for predicate, value in (
        ("external_id", entity["external_id"]),
        ("document", url),
        ("title", title),
        ("published_by", publisher),
        ("jurisdiction", jurisdiction),
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
                )
            )
    return rows


def _page_fact_rows(
    *,
    source_id: str,
    target: DocumentListTarget,
    url: str,
) -> list[dict[str, Any]]:
    """The ``service_page`` seat's page record — a service offering's facts."""
    subject_id = f"document_list_document:{source_id}:{_slug(urlsplit(url).path or url)}"
    ev = _evidence(url, 0)
    entity = _stamp(
        {
            "record_kind": "document_list_document",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("document"),
            "external_id": urlsplit(url).path.rsplit("/", 1)[-1] or target.id,
            "raw_value": url,
            "title": target.title,
            "published_by_label": target.publisher,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
    )
    rows = [entity]
    for predicate, value, candidate in (
        ("external_id", entity["external_id"], None),
        ("document", url, None),
        ("title", target.title, None),
        ("vendor", target.vendor, {"scheme": "procurement.org_name", "value": target.vendor}),
        ("published_by", target.publisher, None),
        ("jurisdiction", target.jurisdiction, None),
        ("country", "US", None),
    ):
        if str(value or "").strip():
            rows.append(
                _claim(
                    subject_id,
                    predicate,
                    value,
                    str(value),
                    ev,
                    source_id=source_id,
                    candidate=candidate,
                )
            )
    return rows


def _contract_rows(
    *,
    source_id: str,
    target: DocumentListTarget,
    url: str,
) -> list[dict[str, Any]]:
    """One ``contract`` record for the target's declared cooperative contract.

    A contract emits only when the target declares its ``contract`` block —
    the reviewed reference is committed data, never a scraped guess. A
    person-shaped declared party label refuses the emit with a recorded
    rejection (fail-closed; the reviewed parties are organisations).
    """
    declared = dict(target.contract)
    ref = declared.get("ref", "").strip()
    if not ref:
        return [
            _rejection_row(
                source_id=source_id,
                target_id=target.id,
                reason="missing",
                detail="contract_docs_page target declares no contract ref",
                feature_index=0,
                fields=declared,
            )
        ]
    for party_key in ("vendor", "buyer"):
        label = declared.get(party_key, "").strip()
        if label and natural_person_signal(label) is not None:
            return [
                _rejection_row(
                    source_id=source_id,
                    target_id=target.id,
                    reason="person_shaped_party",
                    detail=f"declared {party_key} label is natural-person-shaped — never a subject",
                    feature_index=0,
                    fields=declared,
                )
            ]
    subject_id = f"contract:{source_id}:{_slug(ref)}"
    ev = _evidence(url, 0)
    entity = _stamp(
        {
            "record_kind": "contract",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("contract"),
            "external_id": ref,
            "raw_value": ref,
            "title": declared.get("title", ""),
            "vendor_label": declared.get("vendor", ""),
            "buyer_label": declared.get("buyer", ""),
            "published_by_label": target.publisher,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
    )
    rows: list[dict[str, Any]] = [entity]
    vendor = declared.get("vendor", "")
    buyer = declared.get("buyer", "")
    pairs: list[tuple[str, Any, Mapping[str, str] | None]] = [
        ("external_id", ref, None),
        ("title", declared.get("title", ""), None),
        ("vendor", vendor, {"scheme": "procurement.org_name", "value": vendor} if vendor else None),
        ("buyer", buyer, {"scheme": "procurement.org_name", "value": buyer} if buyer else None),
        ("contract_number", declared.get("contract_number", ""), None),
        ("products", declared.get("products", ""), None),
        ("document", url, None),
        ("published_by", target.publisher, None),
        ("jurisdiction", target.jurisdiction, None),
        ("country", "US", None),
    ]
    # RB-07 seats emit facts and citations only — never a verbatim description.
    if not target.facts_citations_only:
        pairs.append(("description", declared.get("description", ""), None))
    for predicate, value, candidate in pairs:
        if not str(value or "").strip():
            continue
        rows.append(
            _claim(
                subject_id,
                predicate,
                value,
                str(value),
                ev,
                source_id=source_id,
                candidate=candidate,
            )
        )
    return rows


def _program_rows(
    *,
    source_id: str,
    target: DocumentListTarget,
    url: str,
    record_kind: str = "funding_instrument",
) -> list[dict[str, Any]]:
    """One ``funding_instrument`` programme record on the declared programme."""
    declared = dict(target.program)
    ref = declared.get("ref", "").strip() or target.id
    subject_id = f"funding_instrument:{source_id}:{_slug(ref)}"
    ev = _evidence(url, 0)
    entity = _stamp(
        {
            "record_kind": record_kind,
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("funding_instrument"),
            "external_id": ref,
            "raw_value": ref,
            "title": declared.get("program_name", ""),
            "funder_label": declared.get("funder", ""),
            "published_by_label": target.publisher,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
    )
    rows: list[dict[str, Any]] = [entity]
    for predicate, value in (
        ("external_id", ref),
        ("funding_program_name", declared.get("program_name", "")),
        ("program_name", declared.get("program_name", "")),
        ("instrument_type", declared.get("instrument_type", "")),
        ("funder", declared.get("funder", "")),
        ("period", declared.get("period", "")),
        ("award_date", declared.get("award_date", "")),
        ("document", url),
        ("published_by", target.publisher),
        ("jurisdiction", target.jurisdiction),
        ("country", "US"),
    ):
        if str(value or "").strip():
            rows.append(
                _claim(
                    subject_id,
                    predicate,
                    value,
                    str(value),
                    ev,
                    source_id=source_id,
                )
            )
    if not target.facts_citations_only and declared.get("description_literal", "").strip():
        rows.append(
            _claim(
                subject_id,
                "description",
                declared["description_literal"],
                declared["description_literal"],
                ev,
                source_id=source_id,
            )
        )
    return rows


def _award_row(
    *,
    source_id: str,
    target: DocumentListTarget,
    url: str,
    award_id: str,
    recipient: str,
    index: int,
    amount_raw: str = "",
    amount_value: Any = "",
    start: str = "",
    end: str = "",
    extra_fields: Iterable[str] = (),
) -> list[dict[str, Any]]:
    """One ``grant_award`` record — organisation recipients only.

    A grant award asserts the funding fact (recipient, funder, programme,
    amount) — never a deployment. A person-shaped recipient name mints no
    subject and lands no claim anywhere: the recorded rejection carries the
    reason and the field names, never the name (Part VIII default-deny).
    """
    declared = dict(target.program)
    if not award_id or not recipient:
        return [
            _rejection_row(
                source_id=source_id,
                target_id=target.id,
                reason="missing",
                detail="award row carries no award id or recipient name",
                feature_index=index,
                fields=extra_fields,
            )
        ]
    if natural_person_signal(recipient) is not None:
        return [
            _rejection_row(
                source_id=source_id,
                target_id=target.id,
                reason="person_shaped_recipient",
                detail="grantee is natural-person-shaped — never a subject "
                "(grantees are units of government by review)",
                feature_index=index,
                fields=extra_fields,
            )
        ]
    subject_id = f"funding_instrument:{source_id}:{_slug(award_id)}"
    ev = _evidence(url, index)
    entity = _stamp(
        {
            "record_kind": "grant_award",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("funding_instrument"),
            "external_id": award_id,
            "raw_value": award_id,
            "recipient_label": recipient,
            "funder_label": declared.get("funder", ""),
            "published_by_label": target.publisher,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
    )
    rows: list[dict[str, Any]] = [entity]
    amount_num = re.sub(r"[^0-9.]", "", amount_raw)
    for predicate, value, candidate in (
        ("external_id", award_id, None),
        (
            "recipient",
            recipient,
            {"scheme": "procurement.org_name", "value": recipient},
        ),
        ("funder", declared.get("funder", ""), None),
        ("funding_program_name", declared.get("program_name", ""), None),
        ("instrument_type", declared.get("instrument_type", ""), None),
        ("funding_amount", amount_value if str(amount_value).strip() else (amount_num or ""), None),
        ("amount", amount_num or amount_raw, None),
        ("currency", "USD" if amount_num or amount_raw else "", None),
        ("start_date", start, None),
        ("end_date", end, None),
        ("award_date", declared.get("award_date", ""), None),
        ("period", declared.get("period", ""), None),
        ("document", url, None),
        ("published_by", target.publisher, None),
        ("jurisdiction", target.jurisdiction, None),
        ("country", "US", None),
    ):
        if not str(value or "").strip():
            continue
        rows.append(
            _claim(
                subject_id,
                predicate,
                value,
                str(value),
                ev,
                source_id=source_id,
                candidate=candidate,
            )
        )
    return rows


def _fy_label(cell_text: str) -> str | None:
    """``FY2026`` / ``FY 2026`` → the canonical ``FY2026`` label, else None."""
    m = re.fullmatch(r"(?i)fy\s*(\d{4})", cell_text.strip())
    return f"FY{m.group(1)}" if m else None


def _fy_rows(body: list[list[str]]) -> list[tuple[str, str]]:
    """``(fy_label, amount_literal)`` pairs out of a fiscal-year table body."""
    out: list[tuple[str, str]] = []
    for cells in body:
        if len(cells) < 2:
            continue
        label = _fy_label(cells[0])
        if label is None:
            continue
        amount = next((c for c in cells[1:] if re.search(r"[\d$]", c)), "")
        if amount:
            out.append((label, amount))
    return out


# --- the connector -------------------------------------------------------------


@register
class DocumentListConnector(Connector):
    """The `document_list` connector — index-page -> document enumeration.

    ``discover`` walks exactly the committed inventory (an uncommitted target
    list is refused loud); ``fetch`` egresses through the shared politeness
    layer only; ``parse``/``extract``/``normalize`` are pure functions of the
    captured bytes. Linked documents are enumerated as POINTER records —
    their contents are never fetched (P8-2 — documents are never re-hosted).
    """

    name = CONNECTOR_NAME
    version = "1.0.0"
    ingestion_mode = "html_scraping"
    incrementality = "re-issue detection via content-addressed capture digests"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — the committed inventory rows only."""
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        url = str(target["url"])
        parts = urlsplit(url)
        hosts = {str(h).lower() for h in (vocab().get("hosts") or [])}
        if parts.scheme != "https" or parts.netloc.lower() not in hosts:
            raise ContentDrift(
                ctx.source.id,
                "a committed target left the committed host set",
                details=f"{url!r} is not https on {sorted(hosts)} (fail-closed)",
            )
        return ctx.fetcher.fetch(url)

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes by the target's declared kind (pure).

        An HTML page missing its declared ``expect`` markers, a table adapter
        whose declared column literals are absent, or a PDF with no text
        layer is :class:`ContentDrift` — recorded loud, never a silent empty
        set.
        """
        data = ctx.captures.get(capture.digest)
        target = self._target_for(ctx, capture.source_uri)
        kind = str(target.get("kind") or "")
        tid = str(target.get("id") or "")
        inv = load_inventory()
        trow = next((t for t in inv.targets if t.id == tid), None)
        expect = tuple(trow.expect) if trow else ()
        if kind == "doclist_html":
            text = data.decode("utf-8", errors="replace")
            missing = [e for e in expect if e.lower() not in text.lower()]
            if missing:
                raise ContentDrift(
                    ctx.source.id,
                    "the page no longer carries its declared markers",
                    details=f"missing {missing} on {capture.source_uri}",
                )
            return {
                "kind": kind,
                "target": target,
                "trow": trow,
                "payload": {
                    "links": _index_links(data, str(capture.source_uri)),
                    "tables": _html_tables(data),
                    "items": _list_items(data),
                    "text": text,
                },
                "capture": capture,
            }
        if kind == "doclist_pdf":
            pages = pdf_text_pages(data)
            if not pages or not any(pages):
                raise ContentDrift(
                    ctx.source.id,
                    "the PDF capture carries no text layer — an image-only or "
                    "malformed document is evidence, never an extraction surface",
                    details=f"{len(data)} bytes on {capture.source_uri}",
                )
            text = "\n".join(pages)
            missing = [e for e in expect if e.lower() not in text.lower()]
            if missing:
                raise ContentDrift(
                    ctx.source.id,
                    "the PDF no longer carries its declared markers",
                    details=f"missing {missing} on {capture.source_uri}",
                )
            return {
                "kind": kind,
                "target": target,
                "trow": trow,
                "payload": {"pages": pages, "text": text},
                "capture": capture,
            }
        raise ContentDrift(
            ctx.source.id,
            f"a capture arrived from a target of undeclared kind {kind!r}",
            details=f"url {capture.source_uri}",
        )

    def _target_for(self, ctx: RunContext, url: str) -> Mapping[str, Any]:
        """Resolve the committed target behind a capture."""
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
            "a capture arrived whose URL matches no committed target",
            details=f"url {url}",
        )

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw claim rows from the parsed payload — adapter-dispatched (P2)."""
        target = parsed.get("trow")
        capture = parsed.get("capture")
        url = str(getattr(capture, "source_uri", "") or "")
        source_id = ctx.source.id
        payload = parsed.get("payload") or {}
        if not isinstance(target, DocumentListTarget):
            raise ContentDrift(
                source_id,
                "the parsed capture resolved no committed inventory row",
                details=f"url {url}",
            )
        adapter = target.adapter
        rows: list[Mapping[str, Any]] = []
        if adapter == "contract_docs_page":
            rows.extend(_contract_rows(source_id=source_id, target=target, url=url))
            rows.extend(
                self._pointers(source_id=source_id, target=target, links=payload.get("links") or [])
            )
            return rows
        if adapter == "service_page":
            rows.extend(_page_fact_rows(source_id=source_id, target=target, url=url))
            rows.extend(
                self._pointers(source_id=source_id, target=target, links=payload.get("links") or [])
            )
            return rows
        if adapter == "award_table":
            rows.extend(
                self._award_table_rows(
                    source_id=source_id,
                    target=target,
                    url=url,
                    tables=payload.get("tables") or [],
                )
            )
            return rows
        if adapter == "capital_line":
            rows.extend(_program_rows(source_id=source_id, target=target, url=url))
            rows.extend(
                self._capital_rows(
                    source_id=source_id, target=target, url=url, tables=payload.get("tables") or []
                )
            )
            return rows
        if adapter == "release_awards":
            rows.extend(_program_rows(source_id=source_id, target=target, url=url))
            rows.extend(
                self._release_recipient_rows(
                    source_id=source_id,
                    target=target,
                    url=url,
                    items=payload.get("items") or [],
                )
            )
            return rows
        if adapter == "rfp_pdf":
            rows.extend(_program_rows(source_id=source_id, target=target, url=url))
            rows.extend(
                self._rfp_stat_rows(
                    source_id=source_id,
                    target=target,
                    url=url,
                    text=str(payload.get("text") or ""),
                )
            )
            return rows
        raise ContentDrift(
            source_id,
            f"no adapter {adapter!r} is declared for this family's emit",
            details=f"target {target.id!r}",
        )

    def _pointers(
        self, *, source_id: str, target: DocumentListTarget, links: list[tuple[str, str]]
    ) -> list[dict[str, Any]]:
        """Enumerated document links → ``document_list_document`` pointers."""
        out: list[dict[str, Any]] = []
        for i, (link, text) in enumerate(links):
            if target.link_re and not re.search(target.link_re, link):
                continue
            out.extend(
                _pointer_claims(
                    source_id=source_id,
                    publisher=target.publisher,
                    jurisdiction=target.jurisdiction,
                    url=link,
                    title=text or urlsplit(link).path.rsplit("/", 1)[-1],
                    index=i,
                )
            )
        return out

    def _award_table_rows(
        self,
        *,
        source_id: str,
        target: DocumentListTarget,
        url: str,
        tables: list[tuple[list[str], list[list[str]]]],
    ) -> list[dict[str, Any]]:
        """The served award table → one ``grant_award`` per row (org-shaped)."""
        declared = dict(target.columns)
        if not declared:
            raise ContentDrift(
                source_id,
                "the award_table target declares no column map",
                details=f"target {target.id!r}",
            )
        table = next(
            (
                (header, body)
                for header, body in tables
                if all(literal in header for literal in declared.values())
            ),
            None,
        )
        if table is None:
            raise ContentDrift(
                source_id,
                "the served page carries no table with the declared column literals",
                details=f"declared {sorted(declared.values())} on {url}",
            )
        header, body = table
        assert_no_forbidden_columns(header, source_id=source_id)
        pos = {logical: header.index(literal) for logical, literal in declared.items()}
        if not body:
            raise ContentDrift(
                source_id,
                "the award table header is present but the body serves zero rows",
                details=f"url {url}",
            )
        rows: list[dict[str, Any]] = []
        for i, cells in enumerate(body):

            def cell(logical: str, cells: list[str] = cells) -> str:
                idx = pos.get(logical)
                return cells[idx] if idx is not None and idx < len(cells) else ""

            rows.extend(
                _award_row(
                    source_id=source_id,
                    target=target,
                    url=url,
                    award_id=cell("award_id"),
                    recipient=cell("grantee"),
                    amount_raw=cell("amount"),
                    start=cell("start_date"),
                    end=cell("end_date"),
                    index=i,
                    extra_fields=header,
                )
            )
        return rows

    def _capital_rows(
        self,
        *,
        source_id: str,
        target: DocumentListTarget,
        url: str,
        tables: list[tuple[list[str], list[list[str]]]],
    ) -> list[dict[str, Any]]:
        """Per-FY capital-plan rows → ``grant_award`` allocations (never recipients)."""
        for header, body in tables:
            pairs = _fy_rows(body)
            if not pairs:
                continue
            rows: list[dict[str, Any]] = []
            for i, (label, amount) in enumerate(pairs):
                rows.extend(
                    _award_row(
                        source_id=source_id,
                        target=target,
                        url=url,
                        award_id=f"{dict(target.program).get('ref', target.id)}:{label.lower()}",
                        recipient=dict(target.program).get("funder", ""),
                        amount_raw=amount,
                        index=i,
                        extra_fields=header,
                    )
                )
            return rows
        return []

    def _release_recipient_rows(
        self,
        *,
        source_id: str,
        target: DocumentListTarget,
        url: str,
        items: list[str],
    ) -> list[dict[str, Any]]:
        """The release body's ``<li>`` recipients → ``grant_award`` rows."""
        rows: list[dict[str, Any]] = []
        marker = (target.list_marker or "").lower()
        listed = [item for item in items if not marker or marker not in item.lower()]
        for i, name in enumerate(listed):
            rows.extend(
                _award_row(
                    source_id=source_id,
                    target=target,
                    url=url,
                    award_id=name,
                    recipient=name,
                    index=i,
                    extra_fields=items[:1],
                )
            )
        return rows

    def _rfp_stat_rows(
        self, *, source_id: str, target: DocumentListTarget, url: str, text: str
    ) -> list[dict[str, Any]]:
        """The RFP's served award-window/statistic literals → verbatim claims."""
        declared = dict(target.program)
        ref = declared.get("ref", target.id)
        subject_id = f"funding_instrument:{source_id}:{_slug(ref)}"
        ev = _evidence(url, 0)
        rows: list[dict[str, Any]] = []
        stat = re.search(r"(average award[^.\n]*(?:\$[\d,.]+)[^.\n]*)", text, flags=re.IGNORECASE)
        window = re.search(
            r"(\d{4}-\d{2}-\d{2})\s*(?:to|through|[-–—])\s*(\d{4}-\d{2}-\d{2})", text
        )
        if stat and not target.facts_citations_only:
            literal = " ".join(stat.group(1).split())
            rows.append(
                _claim(
                    subject_id,
                    "description",
                    literal,
                    literal,
                    ev,
                    source_id=source_id,
                )
            )
        if window:
            rows.append(
                _claim(
                    subject_id,
                    "period",
                    f"{window.group(1)}..{window.group(2)}",
                    window.group(0),
                    ev,
                    source_id=source_id,
                )
            )
        return rows

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """The emit is already typed; the allowlist was enforced per claim."""
        out: list[dict[str, Any]] = []
        for row in raw_claims:
            if row.get("record_kind") == "claim" or row.get("record_kind") in _EMIT_KINDS:
                out.append(dict(row))
        return out

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Stamp the generated ``claim_id`` + transaction time each L1 row needs."""
        out: list[dict[str, Any]] = []
        for row in linked:
            if row.get("record_kind") == "claim" or (
                row.get("predicate_id") in ("contract", "document", "funding_instrument")
                and row.get("record_kind") != "document_list_rejected"
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
    "DocumentListConnector",
    "DocumentListInventory",
    "DocumentListTarget",
    "ForbiddenFieldError",
    "PredicateNotAllowed",
    "assert_no_forbidden_columns",
    "assert_predicate_allowed",
    "document_list_targets",
    "forbidden_field_tokens",
    "forbidden_predicate_genres",
    "load_inventory",
    "predicate_allowlist",
    "vocab",
    "vocab_version",
]
