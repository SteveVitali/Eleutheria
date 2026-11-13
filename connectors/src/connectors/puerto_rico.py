# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `puerto_rico` connector family (P37.51 / R11-ACQ-24, I8 §6.2).

The Puerto Rico territorial surfaces — the legislature's SUTRA measures
system and the OCPR Consulta del Registro de Contratos — behind one
``html_scraping`` connector with small per-surface adapters declared in
``data/puerto_rico_vocab.toml`` and the committed target inventory in
``data/puerto_rico_targets.toml`` (data, not code — SIG-ENG-001 /
SIG-INGEST-038). It serves the eight ACQ-24 registry seats:

* ``legis_pr_sistema_nico_de`` — the SUTRA channel seat (I5-C227): four
  committed GET title-phrase queries, one bounded first page each. Each
  result item is a ``sutra_measure`` record keyed on the platform's own
  numeric medida id; author names are dropped before any claim (Part VIII
  person-naming default-deny — the count rides the entity row as
  provenance). A ``sutra_search_page`` outcome row records the served
  totals and the honest ``truncated`` flag.
* ``legis_pr_rc0787_resoluci_de`` … ``legis_pr_pc0489_ley_del`` — the six
  measure seats: each committed ``/medidas/<id>`` detail page emits one
  ``sutra_measure`` record (type/number, cuatrienio, filing date, title,
  events verbatim, ``/SutraFilesGen/`` links as pointers — contents never
  fetched). A pending measure is proposed law — ``legislative_bill``
  surface, never asserted as in force.
* ``procportal_pr_consulta_del_registro`` — the OCPR contract registry
  (I5-C226, AP-T2-021 S7-flagged): the fiscal-year bulk index enumerates as
  ``ocpr_document`` pointers (FY contents never fetched; the served
  2023-2024 link's recorded 404 is an honest live outcome) and a populated
  ``#tblContracts`` results table parses to ``contract`` records on the
  registry's own column literals. The POST + ``__RequestVerificationToken``
  search form is NEVER submitted (the I5 R3 bound). The Contratista cell
  runs the S7 screen: a non-organisation-shaped contractor name is dropped
  before any claim — the contract still mints, the person datum never
  lands (recorded on ``contractor_screen`` + the outcome's drop count).

Every emitted claim is confined to the committed predicate allowlist
(SIG-INGEST-033); a served table carrying a forbidden person-level column
refuses the capture before any claim is built. All eight sources stay
``ingestion_permitted=false``; the operator's OP-26 Wave-D flip under
ING-GO-D (HG-03 RB-08 `a` territorial public records — GL-GATE-07 reaches
territories; the OCPR row additionally S7 `a`) is the only route to a
live run.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit
from uuid import uuid4

from parsing.locator import Locator
from resolution.partner_identity import PartnerIdentity, partner_identity

from ._data import load_table
from .stages import CaptureRef, Connector, ContentDrift, FetchResult, RunContext, register

CONNECTOR_NAME = "puerto_rico"

#: The eight ACQ-24 registry seats this connector serves (closed set).
SOURCE_IDS = (
    "legis_pr_pc0489_ley_del",
    "legis_pr_pc0560_plan_de",
    "legis_pr_rc0740_investigaci_sobre",
    "legis_pr_rc0787_resoluci_de",
    "legis_pr_rcs0198_resoluci_conjunta",
    "legis_pr_rs0604_resoluci_del",
    "legis_pr_sistema_nico_de",
    "procportal_pr_consulta_del_registro",
)

_TARGETS_TABLE = "puerto_rico_targets"
_VOCAB_TABLE = "puerto_rico_vocab"

TARGETS_SCHEMA = "sig.puerto-rico-targets/1"
VOCAB_SCHEMA_ID = "sig.puerto-rico-vocab/1"

#: The artifact genre every claim carries — the registered ``connector_run``
#: genre (a SUTRA/OCPR capture is connector-run evidence, never dressed in a
#: camera-registry or document genre it is not).
_EVIDENCE_GENRE = "connector_run"

#: Subject kinds minted by this family (entity types declared in
#: ``db/src/db/data/subject_entity_types.toml``; ``contract:`` reuses the
#: §11.11 prefix already mapped there).
_KINDS = frozenset({"sutra_index", "sutra_detail", "ocpr_index"})

#: The served literals an OCPR results table's identity-critical columns
#: MUST carry — a table missing the contract number, the contractor cell or
#: the granting entity cannot honestly type a contract record.
_REQUIRED_OCPR_COLUMNS = ("contract_number", "contractor", "entity")

_MEDIDA_HREF = re.compile(r"^/medidas/(\d+)$")
_MEDIDA_NUMBER = re.compile(r"^[A-Z]{2,4}\d{3,5}$")
_PAGE_TOTALS = re.compile(r"(\d+)\s*al\s*(\d+)\s*de\s*(\d+)\s*records", re.I)
_EMPTY_MARKER = "No se encontró información"
_DOC_LINK = re.compile(r"/SutraFilesGen/")
_FY_LINK = re.compile(r"downloadfrequentsearchfiscalyeardocument\?q=([0-9]{4}-[0-9]{4})")
_US_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")


# --- the versioned vocabulary (data, not code — §20) ---------------------------


@cache
def vocab() -> dict[str, Any]:
    """The committed ``sig.puerto-rico-vocab/1`` table (fail-closed on drift)."""
    table = load_table(_VOCAB_TABLE)
    if table.get("schema") != VOCAB_SCHEMA_ID:
        raise ValueError(f"puerto rico vocabulary must be {VOCAB_SCHEMA_ID!r}")
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
            f"the puerto_rico connector may write only "
            f"{sorted(predicate_allowlist())} (SIG-INGEST-033); {predicate!r} is "
            "outside the allowlist — person names, per-record natural persons and "
            "guessed classes are never emitted."
        )
    return predicate


class ForbiddenFieldError(ValueError):
    """A served payload carried a person-level column the screen refuses (Part VIII)."""


def assert_no_forbidden_columns(columns: Iterable[str], *, source_id: str) -> None:
    """Refuse a tabular payload carrying a forbidden person-level column NAME.

    The mechanical form of the family's Part VIII screen: an OCPR results
    table header that names a person, plate, officer, judge or per-record
    field is refused before a single claim is built — the failing column
    names (schema vocabulary, never values) ride the exception for the
    record.
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
            f"columns {offenders} — the puerto_rico family emits "
            "agency/measure-level records only (Part VIII / §0.7); the bytes "
            "are refused before any claim is built"
        )


# --- the committed target inventory (data, not code) ---------------------------


@dataclass(frozen=True)
class PuertoRicoTarget:
    """One committed territorial target — identifiers + provenance only."""

    id: str
    source: str
    kind: str
    adapter: str
    url: str
    expect: tuple[str, ...]
    license_spdx: str
    publisher: str
    evidence: str


@dataclass(frozen=True)
class PuertoRicoInventory:
    """The committed target set with its derivation provenance."""

    source_ref: str
    captured_on: str
    targets: tuple[PuertoRicoTarget, ...]

    def for_source(self, source_id: str) -> tuple[PuertoRicoTarget, ...]:
        return tuple(t for t in self.targets if t.source == source_id)


def _adapter_spec(adapter: str) -> Mapping[str, Any]:
    spec = (vocab().get("adapters") or {}).get(adapter)
    if not isinstance(spec, Mapping):
        raise ValueError(f"puerto rico vocabulary names no adapter {adapter!r}")
    return spec


def load_inventory() -> PuertoRicoInventory:
    """Parse + validate the committed target table (fail-closed on drift).

    A malformed inventory — wrong schema, duplicate or unsorted ids, a row
    naming a source this family does not serve, an unknown kind/adapter, an
    undeclared host, a missing ``expect`` token — refuses the load rather
    than addressing outside the committed set.
    """
    table = load_table(_TARGETS_TABLE)
    if table.get("schema") != TARGETS_SCHEMA:
        raise ValueError(f"puerto rico inventory schema must be {TARGETS_SCHEMA!r}")
    inv = table.get("inventory") or {}
    hosts = {str(h).lower() for h in (vocab().get("hosts") or [])}
    targets: list[PuertoRicoTarget] = []
    for i, row in enumerate(inv.get("targets") or []):
        if not isinstance(row, dict):
            raise ValueError(f"puerto rico target {i} must be a table")
        tid = str(row.get("id") or "").strip()
        source = str(row.get("source") or "").strip()
        kind = str(row.get("kind") or "").strip()
        adapter = str(row.get("adapter") or "").strip()
        url = str(row.get("url") or "").strip()
        if not all((tid, source, kind, adapter, url)):
            raise ValueError(f"puerto rico target {i} needs id/source/kind/adapter/url")
        if source not in SOURCE_IDS:
            raise ValueError(
                f"puerto rico target {tid!r}: source {source!r} is not one of "
                f"{SOURCE_IDS} — this connector serves no other row"
            )
        if kind not in _KINDS:
            raise ValueError(
                f"puerto rico target {tid!r}: kind {kind!r} is not a member of {sorted(_KINDS)}"
            )
        spec = _adapter_spec(adapter)
        if str(spec.get("kind") or "") != kind:
            raise ValueError(
                f"puerto rico target {tid!r}: adapter {adapter!r} reads kind "
                f"{spec.get('kind')!r}, not {kind!r}"
            )
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.username or parts.netloc.lower() not in hosts:
            raise ValueError(
                f"puerto rico target {tid!r}: {url!r} is not an https URL on "
                "a committed host (fail-closed)"
            )
        expect = tuple(str(e) for e in (row.get("expect") or ()) if str(e).strip())
        if not expect:
            raise ValueError(
                f"puerto rico target {tid!r}: an empty expect list leaves the "
                "page-identity check unenforceable (fail-closed)"
            )
        targets.append(
            PuertoRicoTarget(
                id=tid,
                source=source,
                kind=kind,
                adapter=adapter,
                url=url,
                expect=expect,
                license_spdx=str(row.get("license_spdx") or ""),
                publisher=str(row.get("publisher") or ""),
                evidence=str(row.get("evidence") or ""),
            )
        )
    ids = [t.id for t in targets]
    if len(set(ids)) != len(ids):
        raise ValueError("puerto rico inventory carries duplicate target ids")
    if ids != sorted(ids):
        raise ValueError("puerto rico inventory is not id-sorted (deterministic order required)")
    declared = int(inv.get("target_count") or -1)
    if declared != len(targets):
        raise ValueError(
            f"puerto rico inventory target_count={declared} but {len(targets)} rows committed"
        )
    return PuertoRicoInventory(
        source_ref=str(inv.get("source_ref") or ""),
        captured_on=str(inv.get("captured_on") or ""),
        targets=tuple(targets),
    )


def puerto_rico_targets(source_id: str | None = None) -> list[dict[str, Any]]:
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


# --- helpers (pure) ------------------------------------------------------------


def _iso_date(raw: str) -> str | None:
    """MM/DD/YYYY (the SUTRA/OCPR served format) → ISO 8601, else None."""
    m = _US_DATE.match(raw.strip())
    if not m:
        return None
    mm, dd, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return datetime(yyyy, mm, dd).date().isoformat()
    except ValueError:
        return None


def _slug(value: str) -> str:
    """A subject-key-safe slug: lowercased, ``:``-free, whitespace→``-``."""
    return re.sub(r"[^a-z0-9._-]+", "-", value.strip().lower()).strip("-")


def _evidence(url: str, row_index: int) -> dict[str, Any]:
    return {
        "source_url": url,
        "extraction_method": "puerto_rico",
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
            "record_kind": "puerto_rico_record_rejected",
            "subject_id": f"ocpr_document:{source_id}:{target_id}:rejected:{feature_index}",
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


# --- the SUTRA search-index parser (stdlib, data not regex) --------------------


class _SutraIndexParser(HTMLParser):
    """One measure item per ``<a href="/medidas/<id>">`` result anchor.

    The served page is a Next.js RSC page whose results render inside a
    ``<ul class="list-none">`` list (deferred segments included). Each item
    carries ``Medida: <number>``, ``Radicada <date>``, optional
    ``Autor(es):``/``Co-Autor(es):`` name spans, a ``Título:`` block and a
    progress strip whose completed steps render ``font-bold text-white``.
    """

    _FIELDS = {
        "radicada": "filed",
        "autor(es):": "authors",
        "co-autor(es):": "coauthors",
        "título:": "title",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict[str, Any]] = []
        self.current: dict[str, Any] | None = None
        self.nav_text: list[str] = []
        self.empty_marker = False
        self._in_nav = False
        self._in_strong = False
        self._strong_text: list[str] = []
        self._field: str | None = None
        self._expect_number = False
        self._in_step = False
        self._in_title_strong = False

    # -- tag events --
    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "a":
            m = _MEDIDA_HREF.match(a.get("href") or "")
            if m and self.current is None:
                self.current = {
                    "medida_id": m.group(1),
                    "detail_path": a["href"],
                    "steps": [],
                    "filed": "",
                    "authors": [],
                    "coauthors": [],
                    "title": [],
                    "number": "",
                }
        elif tag == "nav" and "page navigation" in a.get("aria-label", "").lower():
            self._in_nav = True
        elif tag == "strong" and self.current is not None:
            self._in_strong = True
            self._strong_text = []
        elif tag == "span" and self.current is not None:
            cls = a.get("class") or ""
            if "font-bold" in cls and "text-white" in cls:
                self._in_step = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "strong" and self._in_strong:
            label = "".join(self._strong_text).strip().lower()
            self._field = self._FIELDS.get(label)
            self._in_strong = False
        elif tag == "p":
            self._field = None
        elif tag == "span" and self._in_step:
            self._in_step = False
        elif tag == "nav" and self._in_nav:
            self._in_nav = False
        elif tag == "a" and self.current is not None:
            self.items.append(self.current)
            self.current = None
            self._field = None

    def handle_data(self, data: str) -> None:
        if self._in_nav:
            self.nav_text.append(data)
            return
        if self.current is None:
            return
        text = data.strip()
        if not text:
            return
        if self._in_strong:
            self._strong_text.append(text)
            return
        if text == "Medida:" or text.rstrip(":").lower() == "medida":
            self._expect_number = True
            return
        if self._in_step:
            self.current["steps"].append(text)
            return
        if self._expect_number:
            if _MEDIDA_NUMBER.match(text):
                self.current["number"] = text
                self._expect_number = False
            return
        if self._field == "filed":
            self.current["filed"] = text
        elif self._field == "title":
            self.current["title"].append(text)
        elif self._field in ("authors", "coauthors"):
            self.current[self._field].append(text)

    def totals(self) -> tuple[int | None, int | None, int | None]:
        """``(from, to, total)`` from the page-navigation marker, if served."""
        text = " ".join("".join(self.nav_text).split())
        if _EMPTY_MARKER in text:
            self.empty_marker = True
            return None, None, 0
        m = _PAGE_TOTALS.search(text)
        if not m:
            return None, None, None
        return int(m.group(1)), int(m.group(2)), int(m.group(3))


class _SutraDetailParser(HTMLParser):
    """The measure detail page's own literals.

    ``<h1>`` carries ``<type> (<number>)`` (e.g. ``Resolución de la Cámara
    (RC0787)``); ``<strong>LABEL:</strong>`` + the next ``<span>`` carry
    Cuatrienio/Fecha de Radicación/Título; the ``role="list"`` events list
    holds one ``<li>`` per event (``text-sutra-primary`` name, ``Fecha:``
    strong + date, optional ``/SutraFilesGen/`` document links); the tab
    labels carry the ``Autores (N)`` count — names never parsed.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.h1_text: list[str] = []
        self.fields: dict[str, str] = {}
        self.events: list[dict[str, Any]] = []
        self.documents: list[tuple[str, str]] = []
        self.author_count: int | None = None
        self._in_h1 = False
        self._in_strong = False
        self._strong_text: list[str] = []
        self._await_label: str | None = None
        self._await_depth = 0
        self._await_text: list[str] = []
        self._in_events = False
        self._li: dict[str, Any] | None = None
        self._in_event_name = False
        self._event_field: str | None = None
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "h1":
            self._in_h1 = True
        elif tag == "strong":
            self._in_strong = True
            self._strong_text = []
        elif tag == "ul" and a.get("role") == "list":
            self._in_events = True
        elif tag == "li" and self._in_events:
            self._li = {"name": [], "date": "", "detail": [], "docs": []}
        elif (
            tag == "span"
            and self._li is not None
            and "text-sutra-primary" in (a.get("class") or "")
        ):
            self._in_event_name = True
        elif tag == "span" and self._await_label is not None:
            self._await_depth += 1
            self._await_text = []
        elif tag == "a":
            self._href = a.get("href")
            self._link_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "h1":
            self._in_h1 = False
        elif tag == "strong":
            label = "".join(self._strong_text).strip()
            self._in_strong = False
            if label.endswith(":"):
                if self._li is not None and label.lower().startswith("fecha"):
                    self._event_field = "date"
                else:
                    self._await_label = label
        elif tag == "span" and self._await_label is not None and self._await_depth > 0:
            self._await_depth -= 1
            if self._await_depth <= 0:
                value = " ".join("".join(self._await_text).split())
                if value:
                    self.fields[self._await_label] = value
                self._await_label = None
                self._await_depth = 0
                self._await_text = []
        elif tag == "span" and self._in_event_name:
            self._in_event_name = False
        elif tag == "a" and self._href is not None:
            text = " ".join("".join(self._link_text).split())
            if _DOC_LINK.search(self._href):
                self.documents.append((self._href, text))
                if self._li is not None:
                    self._li["docs"].append(self._href)
            self._href = None
            self._link_text = []
        elif tag == "li" and self._li is not None:
            self.events.append(self._li)
            self._li = None
            self._event_field = None
        elif tag == "ul" and self._in_events:
            self._in_events = False
        elif tag in ("option", "button"):
            pass

    def handle_data(self, data: str) -> None:
        if self._in_h1:
            self.h1_text.append(data)
        if self._in_strong:
            self._strong_text.append(data)
            return
        text = data.strip()
        if not text:
            return
        if self._href is not None:
            self._link_text.append(text)
        if self._await_label is not None:
            self._await_text.append(text)
            return
        if self._in_event_name and self._li is not None:
            self._li["name"].append(text)
            return
        if self._li is not None:
            if text == "Fecha:" or text.rstrip(":").lower() == "fecha":
                self._event_field = "date"
                return
            if self._event_field == "date" and not self._li["date"]:
                self._li["date"] = text
                self._event_field = None
            elif self._li["name"] and not self._li["docs"] and self._href is None:
                self._li["detail"].append(text)
        m = re.search(r"Autores\s*\((\d+)\)", text)
        if m and self.author_count is None:
            self.author_count = int(m.group(1))

    def header(self) -> tuple[str, str]:
        """``(measure_type, number)`` from the h1's ``<type> (<number>)`` text."""
        text = " ".join("".join(self.h1_text).split())
        m = re.search(r"\(([A-Z]{2,4}\d{3,5})\)", text)
        number = m.group(1) if m else ""
        mtype = text[: m.start()].strip() if m else text
        return mtype, number


class _OcprIndexParser(HTMLParser):
    """The OCPR landing page: the FY bulk links + the served results table.

    ``#tblContracts``'s ``<th>`` row carries the registry's column literals;
    a populated ``<tbody>`` yields one row dict per contract keyed on those
    literals (the table ships empty server-side today — pointers only then).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fy_links: list[tuple[str, str]] = []
        self.last_updated = ""
        self.form_posted = False
        self.columns: list[str] = []
        self.rows: list[dict[str, Any]] = []
        self._in_fy_link = False
        self._fy_text: list[str] = []
        self._href: str | None = None
        self._link_text: list[str] = []
        self._in_table = False
        self._in_th = False
        self._th_text: list[str] = []
        self._in_tbody = False
        self._row: dict[int, list[str]] | None = None
        self._row_links: dict[int, str] = {}
        self._cell: int | None = None
        self._cell_text: list[str] = []
        self._updated_next = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "form":
            if (a.get("method") or "").lower() == "post":
                self.form_posted = True
        elif tag == "a":
            self._href = a.get("href")
            self._link_text = []
        elif tag == "table" and a.get("id") == "tblContracts":
            self._in_table = True
        elif tag == "th" and self._in_table:
            self._in_th = True
            self._th_text = []
        elif tag == "tbody" and self._in_table:
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._row = {}
            self._row_links = {}
        elif tag == "td" and self._row is not None:
            self._cell = len(self._row)
            self._cell_text = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            m = _FY_LINK.search(self._href)
            if m:
                self.fy_links.append((m.group(1), self._href))
            elif self._cell is not None:
                self._row_links[self._cell] = self._href
            self._href = None
            self._link_text = []
        elif tag == "th" and self._in_th:
            self.columns.append(" ".join("".join(self._th_text).split()))
            self._in_th = False
        elif tag == "td" and self._cell is not None and self._row is not None:
            self._row[self._cell] = self._cell_text
            self._cell = None
            self._cell_text = []
        elif tag == "tr" and self._row is not None:
            self.rows.append({"cells": self._row, "links": self._row_links})
            self._row = None
            self._row_links = {}
        elif tag == "tbody" and self._in_tbody:
            self._in_tbody = False
        elif tag == "table" and self._in_table:
            self._in_table = False
        elif tag == "p" and self._updated_next:
            self._updated_next = False

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if self._in_th:
            self._th_text.append(data)
            return
        if self._href is not None:
            self._link_text.append(data)
        if self._cell is not None:
            self._cell_text.append(data)
        if not text:
            return
        if "actualizaci" in text.lower() and "ltima" in text.lower():
            self._updated_next = True
            self.last_updated = " ".join(text.split())


# --- per-adapter emits (pure) --------------------------------------------------


def _measure_rows(
    *,
    source_id: str,
    license_spdx: str,
    publisher: str,
    url: str,
    medida_id: str,
    number: str,
    measure_type: str,
    session: str,
    filed_raw: str,
    title: str,
    status: str,
    status_date: str,
    author_count: int | None,
    detail_url: str,
    documents: list[tuple[str, str]],
    events: list[dict[str, Any]],
    index: int,
    phrase: str | None = None,
) -> list[dict[str, Any]]:
    """One ``sutra_measure`` record + its measure-surface claims."""
    subject_id = f"sutra_measure:{medida_id}"
    ev = _evidence(url, index)
    filed_iso = _iso_date(filed_raw) if filed_raw else None
    entity = _stamp(
        {
            "record_kind": "sutra_measure",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("legislative_bill"),
            "external_id": medida_id,
            "measure_number": number,
            "measure_type": measure_type,
            "raw_value": number or medida_id,
            "bill_identifier": number,
            "bill_title": title,
            "legislative_session": session,
            "filed_date_raw": filed_raw,
            "filed_date": filed_iso,
            "latest_action": status,
            "latest_action_date": status_date,
            "author_count": author_count,
            "authors_redacted": True,
            "record_url": detail_url,
            "document_urls": [d for d, _t in documents],
            "events": [
                {
                    "name": " ".join(e["name"]),
                    "date": e.get("date") or "",
                    "detail": " ".join(e.get("detail") or []),
                    "document_urls": list(e.get("docs") or []),
                }
                for e in events
            ],
            "published_by_label": publisher,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )
    rows: list[dict[str, Any]] = [entity]
    pairs: list[tuple[str, Any]] = [
        ("external_id", medida_id),
        ("bill_external_id", medida_id),
        ("bill_identifier", number),
        ("bill_title", title),
        ("bill_session", session),
        ("bill_jurisdiction", "US-PR"),
        ("bill_status", status),
        ("bill_status_date", status_date),
        ("filed_date", filed_iso or filed_raw),
        ("published_by", publisher),
        ("platform", "sutra.oslpr.org"),
        ("country", "US"),
    ]
    for predicate, value in pairs:
        if str(value or "").strip():
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
    for doc_url, _text in documents:
        rows.append(
            _claim(
                subject_id,
                "document",
                urljoin(url, doc_url),
                doc_url,
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    if phrase:
        rows.append(
            _claim(
                subject_id,
                "bill_matched_keyword",
                phrase,
                phrase,
                ev,
                source_id=source_id,
                license_spdx=license_spdx,
            )
        )
    return rows


def _ocpr_document_rows(
    *,
    source_id: str,
    license_spdx: str,
    publisher: str,
    url: str,
    fiscal_year: str,
    link: str,
    index: int,
) -> list[dict[str, Any]]:
    """One ``ocpr_document`` pointer record — the link, never the content."""
    subject_id = f"ocpr_document:{source_id}:{fiscal_year}"
    ev = _evidence(url, index)
    full = urljoin(url, link)
    title = f"Contratos Otorgados por Año Fiscal {fiscal_year}"
    entity = _stamp(
        {
            "record_kind": "ocpr_document",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("external_id"),
            "external_id": fiscal_year,
            "raw_value": link,
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
        ("external_id", fiscal_year),
        ("document", full),
        ("title", title),
        ("published_by", publisher),
        ("platform", "consultacontratos.ocpr.gov.pr"),
        ("country", "US"),
    ):
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


def _ocpr_contract_rows(
    *,
    source_id: str,
    license_spdx: str,
    publisher: str,
    url: str,
    target_id: str,
    row: Mapping[str, Any],
    columns: list[str],
    fields: Mapping[str, str],
    index: int,
) -> list[dict[str, Any]]:
    """One ``contract`` record per served results row — the S7 screen applies.

    ``Contratista`` is a party field only when it is affirmatively
    organisation-shaped (an org marker the identity layer accepts). A
    natural-person-shaped — or merely non-org-shaped — contractor name is
    DROPPED: it mints no subject, lands no ``seller`` claim and never
    appears on the entity row (S7 / Part VIII default-deny). The contract
    itself still emits — the served record is real public data; the person
    name is the dropped datum, recorded as a screen outcome, never the
    name.
    """
    cells: Mapping[int, list[str]] = row.get("cells") or {}
    links: Mapping[int, str] = row.get("links") or {}
    # Resolve each declared field to its served cell index by literal.
    idx: dict[str, int] = {}
    for logical, literal in fields.items():
        for i, name in enumerate(columns):
            if name == literal:
                idx[logical] = i
    missing = [c for c in _REQUIRED_OCPR_COLUMNS if c not in idx]

    def cell(logical: str) -> str:
        i = idx.get(logical)
        if i is None:
            return ""
        return " ".join("".join(cells.get(i) or []).split())

    number = cell("contract_number")
    contractor = cell("contractor")
    entity = cell("entity")
    if not number or missing:
        return [
            _rejection_row(
                source_id=source_id,
                license_spdx=license_spdx,
                target_id=target_id,
                reason="missing",
                detail=(
                    f"results row carries no contract number, or the served columns lack {missing}"
                ),
                feature_index=index,
                fields=columns,
            )
        ]
    # The S7 screen: only an affirmatively organisation-shaped contractor
    # emits a `seller` claim. Any refusal shape — natural-person-shaped,
    # sole-proprietor, single-word, generic — drops the name wholesale
    # (the contract still mints; the person datum never lands).
    org = partner_identity(contractor) if contractor else None
    contractor_screen = "org" if isinstance(org, PartnerIdentity) else "dropped"
    subject_id = f"contract:{source_id}:{_slug(number)}"
    ev = _evidence(url, index)
    granted = cell("granted")
    valid_from = cell("valid_from")
    valid_to = cell("valid_to")
    amount_raw = cell("amount")
    amount_num = re.sub(r"[^0-9.]", "", amount_raw) or ""
    doc_link = links.get(idx.get("document", -1), "")
    entity_row = _stamp(
        {
            "record_kind": "contract",
            "subject_id": subject_id,
            "predicate_id": assert_predicate_allowed("contract"),
            "external_id": number,
            "raw_value": number,
            "contract_number": number,
            "buyer_label": entity,
            "seller_label": contractor if contractor_screen == "org" else "",
            "contractor_screen": contractor_screen,
            "service_category": cell("service"),
            "cancelled_raw": cell("cancelled"),
            "granted_raw": granted,
            "validity_raw": f"{valid_from} – {valid_to}".strip(" –"),
            "published_by_label": publisher,
            "evidence_genre": _EVIDENCE_GENRE,
            "evidence": ev,
        },
        source_id=source_id,
        license_spdx=license_spdx,
    )
    rows: list[dict[str, Any]] = [entity_row]
    pairs: list[tuple[str, Any, Mapping[str, str] | None]] = [
        ("external_id", number, None),
        ("buyer", entity, {"scheme": "procurement.org_name", "value": entity} if entity else None),
        (
            "seller",
            contractor if contractor_screen == "org" else "",
            {"scheme": "procurement.org_name", "value": contractor}
            if contractor_screen == "org"
            else None,
        ),
        ("signed_date", _iso_date(granted) or granted, None),
        ("start_date", _iso_date(valid_from) or valid_from, None),
        ("end_date", _iso_date(valid_to) or valid_to, None),
        ("amount", amount_num or amount_raw, None),
        ("currency", "USD", None),
        ("description", cell("service"), None),
        ("document", urljoin(url, doc_link) if doc_link else "", None),
        ("published_by", publisher, None),
        ("country", "US", None),
    ]
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
                license_spdx=license_spdx,
                candidate=candidate,
            )
        )
    return rows


# --- the connector -------------------------------------------------------------


@register
class PuertoRicoConnector(Connector):
    """The `puerto_rico` connector — SUTRA measures + the OCPR registry.

    ``discover`` walks exactly the committed inventory (an uncommitted target
    list is refused loud); ``fetch`` egresses through the shared politeness
    layer only, on the committed host set; ``parse``/``extract``/``normalize``
    are pure functions of the captured bytes (a marked page that violates its
    contract is :class:`ContentDrift`, never a silent empty set).
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

        A page missing its declared markers, a search page carrying neither
        measure items nor the served empty marker, or a results table whose
        header lacks the contract-identity columns is :class:`ContentDrift`
        — recorded loud, never a silent empty set.
        """
        data = ctx.captures.get(capture.digest)
        target = self._target_for(ctx, capture.source_uri)
        kind = str(target.get("kind") or "")
        text = data.decode("utf-8", errors="replace")
        missing = [e for e in target.get("expect") or () if e not in text]
        if missing:
            raise ContentDrift(
                ctx.source.id,
                "the page no longer carries its declared markers",
                details=f"missing {missing} on {capture.source_uri}",
            )
        if kind == "sutra_index":
            parser = _SutraIndexParser()
            parser.feed(text)
            frm, to, total = parser.totals()
            if not parser.items and not parser.empty_marker:
                raise ContentDrift(
                    ctx.source.id,
                    "the SUTRA search page carries neither measure items nor "
                    "the served empty marker",
                    details=f"url {capture.source_uri}",
                )
            return {
                "kind": kind,
                "target": target,
                "payload": {
                    "items": parser.items,
                    "page_from": frm,
                    "page_to": to,
                    "total": total,
                    "empty": parser.empty_marker,
                },
                "capture": capture,
            }
        if kind == "sutra_detail":
            detail = _SutraDetailParser()
            detail.feed(text)
            mtype, number = detail.header()
            if not number:
                raise ContentDrift(
                    ctx.source.id,
                    "the SUTRA detail page carries no measure number in its h1",
                    details=f"url {capture.source_uri}",
                )
            return {
                "kind": kind,
                "target": target,
                "payload": {
                    "measure_type": mtype,
                    "number": number,
                    "fields": detail.fields,
                    "events": detail.events,
                    "documents": detail.documents,
                    "author_count": detail.author_count,
                },
                "capture": capture,
            }
        if kind == "ocpr_index":
            ocpr = _OcprIndexParser()
            ocpr.feed(text)
            if not ocpr.fy_links and not ocpr.rows:
                raise ContentDrift(
                    ctx.source.id,
                    "the OCPR page carries neither the fiscal-year index nor a results table",
                    details=f"url {capture.source_uri}",
                )
            if ocpr.rows:
                assert_no_forbidden_columns(ocpr.columns, source_id=ctx.source.id)
            return {
                "kind": kind,
                "target": target,
                "payload": {
                    "fy_links": ocpr.fy_links,
                    "columns": ocpr.columns,
                    "rows": ocpr.rows,
                    "last_updated": ocpr.last_updated,
                    "form_posted": ocpr.form_posted,
                },
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
                    "expect": list(t.expect),
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
        if adapter == "sutra_search":
            phrase = parse_qs(urlsplit(url).query).get("frase_titulo", [None])[0]
            for i, item in enumerate(payload.get("items") or []):
                steps = [s for s in item.get("steps") or []]
                rows.extend(
                    _measure_rows(
                        source_id=source_id,
                        license_spdx=license_spdx,
                        publisher=publisher,
                        url=url,
                        medida_id=str(item.get("medida_id") or ""),
                        number=str(item.get("number") or ""),
                        measure_type="",
                        session="",
                        filed_raw=str(item.get("filed") or ""),
                        title=" ".join(item.get("title") or []),
                        status=steps[-1] if steps else "",
                        status_date="",
                        author_count=len(item.get("authors") or [])
                        + len(item.get("coauthors") or []),
                        detail_url=urljoin(url, str(item.get("detail_path") or "")),
                        documents=[],
                        events=[],
                        index=i,
                        phrase=phrase,
                    )
                )
            rows.append(
                _stamp(
                    {
                        "record_kind": "sutra_search_page",
                        "url": url,
                        "phrase": phrase,
                        "outcome": "empty"
                        if payload.get("empty")
                        else ("matched" if payload.get("items") else "empty"),
                        "page_from": payload.get("page_from"),
                        "page_to": payload.get("page_to"),
                        "total_records": payload.get("total"),
                        "returned_count": len(payload.get("items") or []),
                        "truncated": bool(
                            isinstance(payload.get("total"), int)
                            and int(payload["total"]) > len(payload.get("items") or [])
                        ),
                    },
                    source_id=source_id,
                    license_spdx=license_spdx,
                )
            )
            return rows
        if adapter == "sutra_measure_page":
            fields = payload.get("fields") or {}
            medida_id = urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1]
            events = payload.get("events") or []
            latest = events[-1] if events else {}
            rows.extend(
                _measure_rows(
                    source_id=source_id,
                    license_spdx=license_spdx,
                    publisher=publisher,
                    url=url,
                    medida_id=medida_id,
                    number=str(payload.get("number") or ""),
                    measure_type=str(payload.get("measure_type") or ""),
                    session=str(fields.get("Cuatrienio:") or ""),
                    filed_raw=str(fields.get("Fecha de Radicación:") or ""),
                    title=str(fields.get("Título:") or ""),
                    status=" ".join(latest.get("name") or []),
                    status_date=str(latest.get("date") or ""),
                    author_count=payload.get("author_count"),
                    detail_url=url,
                    documents=list(payload.get("documents") or []),
                    events=list(events),
                    index=0,
                )
            )
            return rows
        if adapter == "ocpr_registry_index":
            for i, (fy, link) in enumerate(payload.get("fy_links") or []):
                rows.extend(
                    _ocpr_document_rows(
                        source_id=source_id,
                        license_spdx=license_spdx,
                        publisher=publisher,
                        url=url,
                        fiscal_year=fy,
                        link=link,
                        index=i,
                    )
                )
            fields = spec.get("fields") or {}
            served_columns = list(payload.get("columns") or [])
            dropped = 0
            for i, row in enumerate(payload.get("rows") or []):
                emitted = _ocpr_contract_rows(
                    source_id=source_id,
                    license_spdx=license_spdx,
                    publisher=publisher,
                    url=url,
                    target_id=str(target.get("id") or ""),
                    row=row,
                    columns=served_columns,
                    fields=fields,
                    index=i,
                )
                dropped += sum(
                    1
                    for r in emitted
                    if r.get("record_kind") == "contract"
                    and r.get("contractor_screen") == "dropped"
                )
                rows.extend(emitted)
            rows.append(
                _stamp(
                    {
                        "record_kind": "ocpr_index",
                        "url": url,
                        "fy_links": len(payload.get("fy_links") or []),
                        "results_rows": len(payload.get("rows") or []),
                        "contracts_emitted": sum(
                            1 for r in rows if r.get("record_kind") == "contract"
                        ),
                        "contractor_names_dropped": dropped,
                        "last_updated_literal": payload.get("last_updated") or "",
                        "search_form_post": bool(payload.get("form_posted")),
                        "search_form_submitted": False,
                    },
                    source_id=source_id,
                    license_spdx=license_spdx,
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
                "sutra_measure",
                "ocpr_document",
                "contract",
                "puerto_rico_record_rejected",
                "sutra_search_page",
                "ocpr_index",
            ):
                out.append(dict(row))
        return out

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Stamp the generated ``claim_id`` + transaction time each L1 row needs."""
        out: list[dict[str, Any]] = []
        for row in linked:
            if row.get("record_kind") == "claim" or (
                row.get("predicate_id") in ("legislative_bill", "contract", "external_id")
                and row.get("record_kind") != "puerto_rico_record_rejected"
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
    "ForbiddenFieldError",
    "PredicateNotAllowed",
    "PuertoRicoConnector",
    "PuertoRicoInventory",
    "PuertoRicoTarget",
    "assert_no_forbidden_columns",
    "assert_predicate_allowed",
    "forbidden_field_tokens",
    "forbidden_predicate_genres",
    "load_inventory",
    "predicate_allowlist",
    "puerto_rico_targets",
    "vocab",
    "vocab_version",
]
