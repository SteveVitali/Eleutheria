# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The France/Belgium (Technopolice) connectors — the first non-US adapter (§52 Phase 18, P18.2).

The France/Belgium evidence base **stress-tests** the international data model the
P18.1 adapter framework opened (§5.3): authorization is carried by **published
prefectural orders** rather than by contracts, and procurement by a **national
open-data dataset** rather than by thousands of municipal systems. Both must map
onto the existing entities — a :class:`LegalInstrument` and a
:class:`connectors.procurement.Contract` — or the failure to map is a §5.3 defect to
be found here, not in production. This module is the two connectors that make that
mapping concrete, and it exercises the framework with **no US-shaped assumption**:
it never reaches for a ``us.*`` term (the ``foia_request`` / ``us.foia`` / cooperative
US-vehicle vocabulary of the ``records``/``procurement`` connectors is refused).

Two source adapters on the P04.1 eight-stage framework (:mod:`connectors.stages`),
plus the runtime shapes they need:

* **The ``LegalInstrument`` runtime shape** (:class:`LegalInstrument`, §11.14): this
  ticket is its first consumer. A published **arrêté préfectoral** — the legally
  authoritative, dated, five-year-renewable authorization the US has no equivalent
  of (F9.18) — parses into a ``LegalInstrument`` whose ``instrument_type`` is in the
  ``prefectoral_order`` family (``fr.arrete_prefectoral is_a prefectoral_order``,
  SIG-ONTO-068). A US-shaped enum could not hold it; a national-namespace child under
  a shared abstract parent can.
* **The internationalized records-request vocabulary** (§13.8, SIG-ONTO-068): the
  ``france_belgium_records`` connector emits the ``AcquisitionMethod`` regime for the
  jurisdiction — ``fr.cada`` for France (Ma Dada / CADA), ``no_equivalent_available``
  for Belgium (whose national camera register sits behind a Belgian-eID wall and is
  not public — a *known-complete-unknown*, F9.31). It NEVER emits ``foia_request`` or
  a ``us.*`` records term (:func:`assert_not_us_records_method`).
* **National open-data procurement → ``Contract``** (§23.6, SIG-ONTO-032): the
  ``france_belgium_procurement`` connector maps a DECP (Données Essentielles de la
  Commande Publique) record 1:1 onto the country-neutral :class:`Contract` (F9.16).
  A marché riding an accord-cadre (framework agreement) is a piggyback and MUST set
  ``parent_cooperative_contract`` — the same SIG-ONTO-032 invariant the US
  cooperative-vehicle case turns on, reached here with no US vocabulary.

The layered parsing of a captured arrêté PDF is **not** done here: P07.1 owns the
parser. Rows are append-only and carry full provenance; the connectors emit
**candidate** identifiers for the parties and jurisdictions and never resolve
entities themselves (SIG-INGEST-034). The study of the already-executed
~12,000-camera OSM import — a precondition of any SIG-originated contribution at
scale (SIG-CONTRIB-016) — lives in :mod:`connectors.osm_import_study`.
"""

from __future__ import annotations

import csv
import io
import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import cache
from typing import Any

from evidence.digest import multihash
from parsing.classification import FileFormat, classify
from parsing.document import pdf_text_pages
from parsing.genre import classify_genre
from parsing.locator import Locator

from ._data import load_table
from .disappearance import note_disappearance
from .procurement import Contract, LifecycleTransition
from .stages import (
    CaptureRef,
    Connector,
    ContentDrift,
    FetchResult,
    RunContext,
    register,
)

# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `france_belgium` connector vocabulary (``data/france_belgium_vocab.toml``)."""
    return load_table("france_belgium_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def source_ids() -> Mapping[str, str]:
    """The registry source ids the connectors run against, by role key (§22.6 I)."""
    return dict(vocab()["sources"])


def legal_instrument_types() -> frozenset[str]:
    """The LegalInstrumentType vocabulary (§11.14), mirrored from the ontology enum."""
    return frozenset(vocab()["legal_instrument_types"])


def acquisition_methods() -> frozenset[str]:
    """The AcquisitionMethod vocabulary (§13.8), mirrored from the ontology enum."""
    return frozenset(vocab()["acquisition_methods"])


def prefectoral_order_family() -> frozenset[str]:
    """The prefectoral-order family: the abstract parent + its national children (§11.14)."""
    return frozenset(vocab()["prefectoral_order_family"])


def prefectoral_order_parent() -> str:
    """The shared abstract parent every prefectural order maps onto (``prefectoral_order``)."""
    return str(vocab()["prefectoral_order_parent"])


def forbidden_us_acquisition_methods() -> frozenset[str]:
    """The US records-request terms a non-US connector MUST NOT emit (§5.3, SIG-ONTO-068)."""
    return frozenset(vocab()["forbidden_us_acquisition_methods"])


def records_request_method_for(jurisdiction: str) -> str:
    """The internationalized records-request regime for a jurisdiction (§13.8).

    ``FR`` → ``fr.cada``; ``BE`` → ``no_equivalent_available`` (the national camera
    register is behind a Belgian-eID wall and not public, F9.31). Raises
    :class:`KeyError` for an unknown jurisdiction rather than guessing a regime.
    """
    return str(vocab()["records_request_methods"][jurisdiction])


def raa_index_spec() -> Mapping[str, Any]:
    """The reviewed RAA resource-index fan-out bounds (``[raa_index]``, P25.5)."""
    return vocab()["raa_index"]


def madada_feed_spec() -> Mapping[str, Any]:
    """The MaDada Atom safe-metadata contract (``[madada_feed]``, P25.5)."""
    return vocab()["madada_feed"]


# --- the internationalized records-request vocabulary (§13.8, SIG-ONTO-068) ---


class USRecordsMethodError(Exception):
    """Raised when the France/Belgium connector reaches for a US records-request term.

    The mechanical form of §5.3 / SIG-ONTO-068 for this connector: ``foia_request``
    is US-specific, and ``us.foia`` / ``us.state_public_records`` are the US children
    of the abstract ``records_request`` parent. A non-US connector emitting one of
    them is exactly the US-shaped assumption the international model prohibits.
    """


class InvalidAcquisitionMethod(Exception):
    """Raised when an acquisition method is not in the AcquisitionMethod vocabulary (§13.8)."""


def assert_not_us_records_method(method: str) -> str:
    """Return ``method`` unless it is a US records-request term, else raise (§5.3).

    Guards the "not ``foia_request``" acceptance criterion at the seam: the France
    (``fr.cada``) and Belgium (``no_equivalent_available``) regimes pass; the
    outline's ``foia_request`` and the ``us.*`` children are refused here.
    """
    if method in forbidden_us_acquisition_methods():
        raise USRecordsMethodError(
            f"the France/Belgium records connector may not emit {method!r}: it is a "
            "US-specific records-request term (§5.3, SIG-ONTO-068). France uses "
            "'fr.cada' and Belgium 'no_equivalent_available'."
        )
    return method


def assert_acquisition_method(method: str) -> str:
    """Return ``method`` if it is a valid, non-US AcquisitionMethod, else raise (§13.8)."""
    assert_not_us_records_method(method)
    if method not in acquisition_methods():
        raise InvalidAcquisitionMethod(
            f"acquisition method {method!r} is not in the AcquisitionMethod vocabulary "
            f"{sorted(acquisition_methods())} (§13.8)"
        )
    return method


def acquisition_method_claim(
    *,
    jurisdiction: str,
    subject_id: str,
    source_id: str,
    raw_value: str | None = None,
    known_complete_unknown: bool = False,
) -> dict[str, Any]:
    """Build one internationalized ``acquisition_method`` claim (§13.8, SIG-ONTO-068).

    The value is the jurisdiction's records-request regime — ``fr.cada`` or
    ``no_equivalent_available`` — validated to be a non-US AcquisitionMethod term.
    ``known_complete_unknown`` flags the Belgian case (F9.31): a complete
    authoritative register exists, is held by the police, and is not accessible — a
    state distinct from "no data" and from "no such data exists", which
    ``no_equivalent_available`` records rather than discards.
    """
    method = assert_acquisition_method(records_request_method_for(jurisdiction))
    return _stamp(
        {
            "record_kind": "claim",
            "subject_id": subject_id,
            "predicate_id": assert_legal_predicate_allowed("acquisition_method"),
            "value": method,
            "raw_value": raw_value if raw_value is not None else method,
            "jurisdiction": jurisdiction,
            "known_complete_unknown": known_complete_unknown,
        },
        source_id=source_id,
    )


# --- the predicate allowlist for the records connector (SIG-INGEST-033) -------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def legal_instrument_predicate_allowlist() -> frozenset[str]:
    """The predicates the records connector may write (§11.14, §13.8, SIG-INGEST-033)."""
    return frozenset(vocab()["legal_instrument_predicate_allowlist"])


def legal_instrument_forbidden_predicate_genres() -> tuple[str, ...]:
    """The write-set the records connector places out of scope (documented complement)."""
    return tuple(vocab()["legal_instrument_forbidden_predicate_genres"])


def assert_legal_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The ``france_belgium_records`` connector may write **only** the §11.14
    ``LegalInstrument`` predicate surface plus the ``acquisition_method`` coverage
    fact: a procurement value, a device count, or a deployment claim is refused here,
    at the ingest boundary (SIG-INGEST-033, the ``D6`` filter at ingest).
    """
    if predicate not in legal_instrument_predicate_allowlist():
        raise PredicateNotAllowed(
            f"the france_belgium records connector may write only "
            f"{sorted(legal_instrument_predicate_allowlist())} (§11.14/§13.8, "
            f"SIG-INGEST-033); {predicate!r} is outside the allowlist — procurement, "
            "device, and deployment claims are refused."
        )
    return predicate


def _is_json_media(media_type: str) -> bool:
    # Only a JSON content type is the records payload; everything else — a gazette
    # PDF, an HTML index page, an Atom feed — is an upstream document routed to the
    # P07.1 classifier.
    return "json" in media_type.lower()


def _filename_from_uri(uri: str) -> str:
    tail = uri.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return tail or "document"


def document_artifact_id(source_uri: str) -> str:
    """The stable EvidenceArtifact id for an upstream document at ``source_uri``.

    Keyed on the source URI, not the bytes, so the id is stable across
    re-captures and never depends on capture order (§10.2). Deterministic.
    """
    return f"france_belgium:artifact:{multihash(source_uri.encode('utf-8'))}"


def _document_artifact_row(source_id: str, record: Mapping[str, Any]) -> dict[str, Any]:
    """An upstream document capture as an EvidenceArtifact row (§10.2).

    For DERIVE-posture sources (``LicenseRef-DerivedFacts-Citations``,
    redistributable=false) the bytes are **never re-hosted**: the row carries
    provenance — source URI, content-addressed capture digest, media type, size —
    and the P07.1 classification verdict, which is recorded but not run to a layer
    engine here (SIG-PARSE-001/002).
    """
    source_uri = str(record["source_uri"])
    return _stamp(
        {
            "record_kind": "evidence_artifact",
            "subject_id": document_artifact_id(source_uri),
            "predicate_id": assert_legal_predicate_allowed("document"),
            "published_by": source_id,
            "source_uri": source_uri,
            "capture_digest": str(record["capture_digest"]),
            "media_type": str(record["media_type"]),
            "byte_size": int(record["byte_size"]),
            "integrity": "captured",
            "classification": dict(record["verdict"]),
            "raw_value": source_uri,
        },
        source_id=source_id,
    )


# --- the RAA resource-index adapter (P25.5, F9.18) -----------------------------
#
# The national RAA index CSV (data.gouv.fr, ODbL-1.0) is the discovery surface for
# the per-prefecture gazette PDFs: each row names a gazette document by title,
# URL, departement, and index-update date. The adapter parses the index STRICTLY —
# a changed header or non-CSV shape is ContentDrift, never an empty selection —
# and resolves a bounded subset of arrêté-titled rows into instrument_document
# targets. The LegalInstrument fields (title, departement, effective date sniffed
# from the title literal, CSI L252 five-year derived sunset) come from the index
# ROW; the fetched document is the evidence the claim cites.


@dataclass(frozen=True)
class RaaIndexEntry:
    """One row of the national RAA index CSV (``titre;url;departement;mise_a_jour``)."""

    row: int  # 1-based data-row number in the index — the claim locator
    titre: str
    url: str
    departement: str
    mise_a_jour: str


@dataclass(frozen=True)
class RaaIndex:
    """The parsed national RAA index: entries + the malformed-row accounting."""

    entries: tuple[RaaIndexEntry, ...]
    header: tuple[str, ...]
    malformed_count: int

    @property
    def entry_count(self) -> int:
        return len(self.entries)


def parse_raa_index(data: bytes, *, source_id: str) -> RaaIndex:
    """Parse the national RAA index CSV — STRICT shape validation (fail closed).

    The observed shape is semicolon-delimited UTF-8 with exactly the four columns
    ``titre;url;departement;mise_a_jour``. A capture whose header is missing or
    differs, or that is not parseable CSV text at all, is :class:`ContentDrift` —
    the upstream shape changed and the adapter refuses to guess (never silently
    zero rows). Rows missing a usable ``url``/``departement`` are counted
    ``malformed`` and skipped (heterogeneous data is expected), not drift.
    """
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContentDrift(
            source_id,
            "the RAA index is not decodable UTF-8 text",
            details=str(exc),
        ) from exc
    reader = csv.reader(io.StringIO(text), delimiter=";")
    try:
        header = next(reader)
    except StopIteration as exc:
        raise ContentDrift(source_id, "the RAA index capture is empty") from exc
    required = [str(c) for c in raa_index_spec()["required_columns"]]
    header_norm = [str(h).strip().lower() for h in header]
    if header_norm != required:
        raise ContentDrift(
            source_id,
            "the RAA index header no longer matches "
            f"{required!r} (got {header_norm!r}) — fail closed, never guess",
        )
    entries: list[RaaIndexEntry] = []
    malformed = 0
    for i, row in enumerate(reader, start=1):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != len(required):
            malformed += 1
            continue
        titre, url, departement, mise_a_jour = (cell.strip() for cell in row)
        if not url.startswith(("http://", "https://")) or not departement:
            malformed += 1
            continue
        entries.append(
            RaaIndexEntry(
                row=i, titre=titre, url=url, departement=departement, mise_a_jour=mise_a_jour
            )
        )
    return RaaIndex(entries=tuple(entries), header=tuple(header_norm), malformed_count=malformed)


_FRENCH_MONTHS = {
    "janvier": "01",
    "février": "02",
    "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "août": "08",
    "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "décembre": "12",
    "decembre": "12",
}

# Conservative date literals in RAA titres — "du 05 janvier 2026", "du 05/01/2026",
# "du 05012026", or an ISO "2026-01-05". Nothing else is read as a date.
_RE_DATE_WORDS = re.compile(
    r"\bdu\s+(\d{1,2})\s+([a-zA-ZéûôàùçÉÛÔÀÙÇ]+)\s+(\d{4})\b", re.IGNORECASE
)
_RE_DATE_ISO = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b")
_RE_DATE_SLASH = re.compile(r"\b(\d{1,2})[/.\-](\d{1,2})[/.\-](\d{4})\b")
_RE_DATE_COMPACT = re.compile(r"\b(\d{2})(\d{2})(20\d{2})\b")


def _sniff_raa_date(titre: str) -> str | None:
    """The arrêté date literal inside an RAA ``titre`` — ISO ``YYYY-MM-DD`` or ``None``.

    Only literal date strings in the title are used; the index ``mise_a_jour`` is
    the *resource update* date, never the instrument's effective date. An
    unparseable title yields ``None`` (no effective date, no derived sunset) —
    never a guessed date.
    """
    match = _RE_DATE_WORDS.search(titre)
    if match:
        day, month_name, year = match.groups()
        month = _FRENCH_MONTHS.get(month_name.lower())
        if month:
            return f"{year}-{month}-{int(day):02d}"
    match = _RE_DATE_ISO.search(titre)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    match = _RE_DATE_SLASH.search(titre)
    if match:
        day, month, year = match.groups()
        if 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
            return f"{year}-{int(month):02d}-{int(day):02d}"
    match = _RE_DATE_COMPACT.search(titre)
    if match:
        day, month, year = match.groups()
        if 1 <= int(day) <= 31 and 1 <= int(month) <= 12:
            return f"{year}-{int(month):02d}-{int(day):02d}"
    return None


def resolve_raa_targets(
    ctx: RunContext, index_capture: CaptureRef, spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Resolve the bounded per-prefecture ``instrument_document`` targets (P25.5).

    The bounds are reviewed DATA — the ``[raa_index]`` vocabulary defaults the
    live-target row may tighten but the adapter never crawls the full ~23k-row
    index: a departement allowlist, a conservative arrêté titre pattern,
    https-only document URLs, and a hard ``max_documents`` cap. Each resolved
    target carries the index row's fields (its provenance) and is registered on
    ``ctx.resolved_targets`` so the child's post-capture stages see them.
    """
    bounds = raa_index_spec()
    index = parse_raa_index(ctx.captures.get(index_capture.digest), source_id=ctx.source.id)
    departements = {str(d).strip() for d in spec.get("departements", []) or ()}
    title_re = re.compile(str(spec.get("title_pattern") or bounds["title_pattern"]), re.I)
    dept_re = re.compile(str(bounds["departement_pattern"]))
    doc_url_re = re.compile(str(spec.get("doc_url_pattern") or bounds["doc_url_pattern"]), re.I)
    require_https = bool(spec.get("require_https", bounds["require_https"]))
    max_documents = int(spec.get("max_documents", bounds["max_documents"]))
    out: list[dict[str, Any]] = []
    for entry in index.entries:
        if len(out) >= max_documents:
            break
        if departements and entry.departement not in departements:
            continue
        if not dept_re.match(entry.departement):
            continue
        if not title_re.search(entry.titre):
            continue
        if not doc_url_re.search(entry.url):
            continue
        if require_https and not entry.url.startswith("https://"):
            continue
        out.append(
            {
                "id": f"raa-arrete:{entry.departement}:{entry.row}",
                "url": entry.url,
                "kind": "instrument_document",
                "index_url": index_capture.source_uri,
                "index_row": entry.row,
                "titre": entry.titre,
                "departement": entry.departement,
                "mise_a_jour": entry.mise_a_jour,
            }
        )
    return out


# --- the DECP dataset-API indirection (P25.7) -----------------------------------
#
# The consolidated DECP files are *resources* of a data.gouv.fr dataset whose
# static URLs carry a regeneration timestamp — Etalab republishes and the pinned
# ``static.data.gouv.fr/resources/<dataset>/<timestamp>/<file>`` URL 404s. The
# live seed target is therefore the dataset document on the documented API v1
# (``www.data.gouv.fr /api/1/datasets/…``, allow-listed under ADR-083); the
# connector resolves the reviewed resource's CURRENT ``url`` from the captured
# index at run time. A regenerated resource resolves to its new timestamped URL;
# an absent/renamed resource is a recorded ``link_rotted`` disappearance — never
# a silent fallback to a stale URL.


@dataclass(frozen=True)
class DecpDatasetResource:
    """One resource row of the data.gouv.fr dataset-API document."""

    title: str
    url: str
    resource_id: str = ""
    last_modified: str = ""
    format: str = ""


@dataclass(frozen=True)
class DecpDataset:
    """The parsed dataset-API document: the dataset identity + its resource index."""

    dataset_id: str
    title: str
    resources: tuple[DecpDatasetResource, ...]


def parse_decp_dataset(data: bytes, *, source_id: str) -> DecpDataset:
    """Parse the data.gouv.fr dataset-API document — STRICT shape (fail closed).

    The documented shape is a JSON object carrying ``resources`` — a list of
    objects each with a non-empty ``title`` and an http(s) ``url``. A document
    that is not that shape (not JSON, no ``resources`` list, a resource missing
    its ``title``/``url``) is :class:`ContentDrift`: the API surface changed and
    the adapter refuses to guess which entry is the consolidated DECP file.
    """
    try:
        payload = json.loads(data)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ContentDrift(
            source_id,
            "the data.gouv.fr dataset-API document is not JSON",
            details=str(exc),
        ) from exc
    if not isinstance(payload, Mapping):
        raise ContentDrift(
            source_id,
            "the dataset-API document is not a JSON object — the API shape changed",
        )
    resources = payload.get("resources")
    if not isinstance(resources, list):
        raise ContentDrift(
            source_id,
            "the dataset-API document carries no `resources` list — the API shape "
            "changed; fail closed, never guess",
        )
    entries: list[DecpDatasetResource] = []
    for i, entry in enumerate(resources):
        if not isinstance(entry, Mapping):
            raise ContentDrift(
                source_id,
                f"dataset resource #{i} is not an object — the API shape changed",
            )
        title = str(entry.get("title") or "").strip()
        url = str(entry.get("url") or "").strip()
        if not title or not url.startswith(("http://", "https://")):
            raise ContentDrift(
                source_id,
                f"dataset resource #{i} lacks a title/url — the API shape changed; "
                "fail closed, never guess",
            )
        entries.append(
            DecpDatasetResource(
                title=title,
                url=url,
                resource_id=str(entry.get("id") or ""),
                last_modified=str(
                    entry.get("last_modified") or entry.get("last_modified_at") or ""
                ),
                format=str(entry.get("format") or ""),
            )
        )
    return DecpDataset(
        dataset_id=str(payload.get("id") or ""),
        title=str(payload.get("title") or ""),
        resources=tuple(entries),
    )


def resolve_decp_targets(
    ctx: RunContext, index_capture: CaptureRef, spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Resolve the reviewed DECP resource's CURRENT url from the dataset index (P25.7).

    The ``dataset_index`` target spec names the reviewed resource by
    ``resource_title``. Exactly one match resolves to a target carrying the
    dataset-API provenance (dataset url, resource id, last-modified stamp).
    **Zero** matches means the reviewed resource is gone from the dataset — a
    recorded ``link_rotted`` disappearance on ``ctx.resolved_disappearances``
    (the driver drains it onto the run report), never a fallback to a stale
    pinned URL. **More than one** match is :class:`ContentDrift` — an ambiguous
    selector fails loud rather than silently picking one.
    """
    title = str(spec.get("resource_title") or "").strip()
    if not title:
        raise ContentDrift(
            ctx.source.id,
            "a dataset_index target must name `resource_title` — the reviewed "
            "resource selector is data, not a guess",
        )
    dataset = parse_decp_dataset(ctx.captures.get(index_capture.digest), source_id=ctx.source.id)
    matches = [r for r in dataset.resources if r.title == title]
    if not matches:
        ctx.resolved_disappearances.append(
            note_disappearance(
                artifact_id=f"{spec.get('id') or 'decp-dataset'}:{title}",
                observed_at=index_capture.retrieved_at or datetime.now(UTC),
                failing_status="link_rotted",
            )
        )
        return []
    if len(matches) > 1:
        raise ContentDrift(
            ctx.source.id,
            f"the dataset-API document lists {len(matches)} resources titled "
            f"{title!r} — the selector is ambiguous; fail closed, never pick one",
        )
    resource = matches[0]
    return [
        {
            "id": f"{spec.get('id') or 'decp-dataset'}:{resource.title}",
            "url": resource.url,
            "kind": str(spec.get("resource_kind") or "contract"),
            "dataset_url": index_capture.source_uri,
            "dataset_id": dataset.dataset_id,
            "resource_title": resource.title,
            "resource_id": resource.resource_id,
            "resource_last_modified": resource.last_modified,
        }
    ]


# --- the MaDada Atom adapter (P25.5) --------------------------------------------
#
# The platform publishes an Atom feed of *successful* requests. An entry maps to
# ONE records-request context (fr.cada) carrying only safe metadata — the atom id,
# the timestamps, the request-event link. The user-authored <title>/<content> are
# request text: they are never parsed into a claim, never stored on a raw record,
# never emitted (the [madada_feed] contract names them `never_emit`).


@dataclass(frozen=True)
class AtomEntry:
    """The safe metadata of one MaDada feed entry — title/content never carried."""

    row: int  # 1-based entry ordinal in the feed — the claim locator
    atom_id: str
    link: str
    published: str
    updated: str


def parse_atom_feed(data: bytes, *, source_id: str) -> tuple[AtomEntry, ...]:
    """Parse a MaDada Atom feed — namespace-aware, STRICT shape (fail closed).

    The root must be an Atom ``<feed>``; every ``<entry>`` must carry an ``<id>``
    and a link. A capture that is not Atom, or an entry missing its identity/
    link, is :class:`ContentDrift` — the platform changed the feed shape and the
    adapter refuses to guess. ``<title>``/``<content>`` are deliberately never
    read into the returned entries: they are user-authored request text and the
    connector's contract is to never retain them.
    """
    ns = str(madada_feed_spec()["namespace"])
    try:
        root = ET.fromstring(data.decode("utf-8"))
    except (UnicodeDecodeError, ET.ParseError) as exc:
        raise ContentDrift(
            source_id, "the MaDada feed is not parseable XML", details=str(exc)
        ) from exc
    if root.tag != f"{{{ns}}}feed":
        raise ContentDrift(
            source_id,
            f"the MaDada feed root is {root.tag!r}, not the Atom {{{ns}}}feed — "
            "fail closed, never guess",
        )
    entries: list[AtomEntry] = []
    for i, entry in enumerate(root.findall(f"{{{ns}}}entry"), start=1):
        atom_id = entry.findtext(f"{{{ns}}}id")
        link_el = entry.find(f"{{{ns}}}link")
        link = link_el.get("href") if link_el is not None else None
        if not atom_id or not link:
            raise ContentDrift(
                source_id,
                f"feed entry #{i} is missing its atom id or link — the entry "
                "shape changed; fail closed",
            )
        entries.append(
            AtomEntry(
                row=i,
                atom_id=str(atom_id),
                link=str(link),
                published=str(entry.findtext(f"{{{ns}}}published") or ""),
                updated=str(entry.findtext(f"{{{ns}}}updated") or ""),
            )
        )
    return tuple(entries)


def _atom_entry_subject(entry: AtomEntry) -> str:
    """The records-request subject for one feed entry (the request-event id)."""
    match = re.search(r"request_event/(\d+)", entry.link) or re.search(
        r"InfoRequestEvent/(\d+)", entry.atom_id
    )
    if match:
        return f"madada:request_event/{match.group(1)}"
    return f"madada:request_event/{multihash(entry.link.encode('utf-8'))[:16]}"


# --- candidate identifiers for the parties (SIG-INGEST-034) -------------------


def org_candidate(raw_org: str, *, scheme: str = "fr.org_name") -> dict[str, str]:
    """A **candidate** identifier for a France/Belgium organization — never a resolution.

    A numeric id (a French SIREN/SIRET) routes to a scheme-scoped path; a free-text
    name routes to a surrogate ``<ns>.org_name`` path the identity layer (§14.6)
    resolves (SIG-INGEST-034).
    """
    value = raw_org.strip()
    if value.isdigit():
        return {"scheme": "fr.siret", "value": value}
    return {"scheme": scheme, "value": value}


def jurisdiction_candidate(raw_code: str, *, scheme: str = "fr.insee") -> dict[str, str]:
    """A **candidate** identifier for a France/Belgium jurisdiction (SIG-INGEST-034)."""
    return {"scheme": scheme, "value": str(raw_code).strip()}


# --- the LegalInstrument runtime shape (§11.14) -------------------------------


class InvalidLegalInstrument(Exception):
    """Raised when a LegalInstrument violates the §11.14 vocabulary contract."""


@dataclass(frozen=True)
class LegalInstrument:
    """The runtime shape of a §11.14 ``LegalInstrument`` — this ticket is its first consumer.

    Gives the international requirement somewhere to put an arrêté préfectoral, a CNIL
    decision, or a Belgian loi caméras. ``instrument_type`` is validated against the
    frozen ``LegalInstrumentType`` vocabulary; an out-of-vocabulary value is a hard
    error rather than a silent coercion (SIG-ONTO). A published prefectural order maps
    onto an instrument in the ``prefectoral_order`` family (:attr:`is_prefectoral_order`).
    The connector emits **candidate** party/jurisdiction identifiers, never resolutions
    (SIG-INGEST-034).
    """

    external_id: str
    source_id: str
    instrument_type: str
    enacting_body: str | None = None
    jurisdiction: str | None = None
    #: The candidate-identifier scheme the ``jurisdiction`` claim carries
    #: (SIG-INGEST-034): ``fr.insee`` for the France/Belgium paths; the statute-seed
    #: loader (P25.7) passes ``us.state`` — a candidate, never a resolution.
    jurisdiction_scheme: str = "fr.insee"
    citation: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None
    sunset_date: str | None = None
    constrains_technology: tuple[str, ...] = ()
    constrains_capability: tuple[str, ...] = ()
    requires_authorization_of: tuple[str, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.external_id).strip():
            raise InvalidLegalInstrument("a LegalInstrument requires an external_id (§11.14)")
        if self.instrument_type not in legal_instrument_types():
            raise InvalidLegalInstrument(
                f"instrument_type {self.instrument_type!r} is not in the LegalInstrumentType "
                f"vocabulary {sorted(legal_instrument_types())} (§11.14)"
            )

    @property
    def subject_id(self) -> str:
        """The claim subject id for this instrument (source + external id scoped)."""
        return f"legal_instrument:{self.source_id}:{self.external_id}"

    @property
    def is_prefectoral_order(self) -> bool:
        """Whether this instrument is a prefectural order (abstract parent or a child)."""
        return self.instrument_type in prefectoral_order_family()

    @property
    def abstract_instrument_type(self) -> str:
        """The shared abstract instrument type (``prefectoral_order`` for the family).

        Maps the concrete national child (``fr.arrete_prefectoral``) up to the shared
        abstract parent, so a cross-country query can ask for every prefectural order
        regardless of national namespace (SIG-ONTO-068). AC2's "maps onto
        ``instrument_type=prefectoral_order``" is exactly this.
        """
        if self.is_prefectoral_order:
            return prefectoral_order_parent()
        return self.instrument_type

    def predicate_values(self) -> dict[str, Any]:
        """The §11.14 predicate → value map for the set predicates (allowlisted keys only)."""
        candidates: dict[str, Any] = {
            "instrument_type": self.instrument_type,
            "enacting_body": self.enacting_body,
            "jurisdiction": self.jurisdiction,
            "citation": self.citation,
            "effective_from": self.effective_from,
            "effective_to": self.effective_to,
            "sunset_date": self.sunset_date,
            "external_id": self.external_id,
        }
        values = {k: v for k, v in candidates.items() if v is not None}
        if self.constrains_technology:
            values["constrains_technology"] = list(self.constrains_technology)
        if self.constrains_capability:
            values["constrains_capability"] = list(self.constrains_capability)
        if self.requires_authorization_of:
            values["requires_authorization_of"] = list(self.requires_authorization_of)
        return values

    def claim_rows(self) -> list[dict[str, Any]]:
        """The append-only claim rows for this instrument, confined to the allowlist (P2).

        One ``legal_instrument`` entity row (carrying the whole predicate surface for
        provenance) plus one row per set §11.14 predicate. Every predicate id passes
        :func:`assert_legal_predicate_allowed` (SIG-INGEST-033); ``raw_value`` is
        preserved beside every typed value (P2). ``enacting_body`` and ``jurisdiction``
        carry a **candidate** identifier, never a resolution (SIG-INGEST-034).
        """
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "legal_instrument",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_legal_predicate_allowed("legal_instrument"),
                    "external_id": self.external_id,
                    "raw_value": self.external_id,
                    "predicate_surface": self.predicate_values(),
                    "instrument_type": self.instrument_type,
                    "abstract_instrument_type": self.abstract_instrument_type,
                },
                source_id=self.source_id,
            )
        ]
        for predicate, value in self.predicate_values().items():
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": self.subject_id,
                "predicate_id": assert_legal_predicate_allowed(predicate),
                "raw_value": _raw_value_of(value),
                "value": value,
            }
            if predicate == "enacting_body" and isinstance(value, str):
                row["candidate_identifier"] = org_candidate(value)
            elif predicate == "jurisdiction" and isinstance(value, str):
                row["candidate_identifier"] = jurisdiction_candidate(
                    value, scheme=self.jurisdiction_scheme
                )
            if predicate == "sunset_date" and self.raw.get("sunset_date_derived"):
                # The five-year sunset is DERIVED from effective_from (CSI L252),
                # not read from the document — the claim says so explicitly.
                row["derived"] = True
                row["derivation"] = "csi_l252_five_year_validity"
            rows.append(_stamp(row, source_id=self.source_id))
        return rows


def prefectoral_order_from_raa(raw: Mapping[str, Any], *, source_id: str) -> LegalInstrument:
    """Build the arrêté préfectoral a RAA record parses into (§11.14, F9.18).

    A French prefectural authorization is granted for **five years and is renewable**
    (Code de la sécurité intérieure L252); when the arrêté carries an
    ``effective_from`` and no explicit expiry, the five-year ``sunset_date`` is
    derived and flagged as derived in ``raw`` so the §12 renewal-watch task can fire
    ("this authorization lapses in N years; is there a renewal?"). ``instrument_type``
    is ``fr.arrete_prefectoral`` — a national child of the abstract ``prefectoral_order``
    parent (SIG-ONTO-068), never a widened US enum.
    """
    v = vocab()
    effective_from = _opt_str(raw.get("effective_from") or raw.get("date"))
    sunset = _opt_str(raw.get("sunset_date") or raw.get("effective_to"))
    if sunset is None and effective_from is not None:
        sunset = _plus_years(effective_from, int(v["fr_prefectoral_order_validity_years"]))
    departement = _opt_str(raw.get("departement") or raw.get("commune") or raw.get("jurisdiction"))
    return LegalInstrument(
        external_id=str(raw.get("external_id") or raw.get("id") or raw.get("titre") or ""),
        source_id=source_id,
        instrument_type=str(v["fr_prefectoral_order_instrument_type"]),
        enacting_body=_opt_str(raw.get("enacting_body") or raw.get("prefecture")),
        jurisdiction=departement,
        citation=_opt_str(raw.get("citation")) or str(v["fr_prefectoral_order_citation"]),
        effective_from=effective_from,
        sunset_date=sunset,
        constrains_technology=tuple(str(t) for t in raw.get("constrains_technology", [])),
        requires_authorization_of=tuple(str(a) for a in raw.get("requires_authorization_of", [])),
        raw={**dict(raw), "sunset_date_derived": sunset is not None and not raw.get("sunset_date")},
    )


# --- national open-data procurement → Contract (§23.6, SIG-ONTO-032, F9.16) ---


def decp_procedure_channels() -> Mapping[str, str]:
    """The DECP ``procedure`` → AcquisitionChannel map (§11.11)."""
    return dict(vocab()["decp"]["procedure_channels"])


def decp_default_channel() -> str:
    """The AcquisitionChannel assumed when a DECP procedure maps to nothing specific."""
    return str(vocab()["decp_default_channel"])


def decp_framework_channel() -> str:
    """The channel a marché riding an accord-cadre carries (``cooperative_piggyback``)."""
    return str(vocab()["decp_framework_channel"])


def decp_currency() -> str:
    """The DECP currency (montant is in EUR)."""
    return str(vocab()["decp_currency"])


def decp_acquisition_channel(procedure: str | None, *, has_framework: bool) -> str:
    """The AcquisitionChannel for a DECP record (§11.11, SIG-ONTO-032).

    A marché with an ``idAccordCadre`` (framework agreement) is a piggyback on a
    master award and takes the framework channel regardless of ``procedure`` — the
    same shape as a US cooperative-vehicle piggyback, reached here through French
    open data with no US vocabulary. Otherwise the free-text French ``procedure``
    maps through :func:`decp_procedure_channels`, falling back to the default.
    """
    if has_framework:
        return decp_framework_channel()
    if procedure is None:
        return decp_default_channel()
    return decp_procedure_channels().get(procedure, decp_default_channel())


def contract_from_decp(raw: Mapping[str, Any], *, source_id: str) -> Contract:
    """Map one DECP record 1:1 onto the country-neutral §11.11 ``Contract`` (F9.16).

    Proves national open-data procurement maps onto ``Contract`` without loss (AC2):
    ``acheteur.id`` (SIRET) → buyer, ``titulaires[].titulaire.id`` → seller,
    ``montant`` → amount (EUR), ``dateNotification`` → signed/start date. ``end_date``
    is deliberately left unset — DECP gives ``dureeMois``, from which the end is
    **derivable, not stored** (F9.16). A marché carrying an ``idAccordCadre`` is a
    piggyback and MUST set ``parent_cooperative_contract`` (SIG-ONTO-032); the
    Contract's own ``__post_init__`` enforces that invariant.
    """
    acheteur = raw.get("acheteur") or {}
    buyer = _opt_str(acheteur.get("id") if isinstance(acheteur, Mapping) else acheteur)
    seller = _first_titulaire(raw.get("titulaires"))
    framework = _opt_str(raw.get("idAccordCadre"))
    procedure = _opt_str(raw.get("procedure"))
    channel = decp_acquisition_channel(procedure, has_framework=framework is not None)
    signed = _opt_str(raw.get("dateNotification"))
    products = tuple(p for p in (_opt_str(raw.get("objet")), _opt_str(raw.get("codeCPV"))) if p)
    lifecycle = (LifecycleTransition(state="contracted", date=signed),) if signed else ()
    return Contract(
        external_id=str(raw.get("id") or ""),
        source_id=source_id,
        buyer=buyer,
        seller=seller,
        amount=_opt_str(raw.get("montant")),
        currency=decp_currency() if raw.get("montant") is not None else None,
        signed_date=signed,
        start_date=signed,
        renewal_options=framework,
        products=products,
        acquisition_channel=channel,
        parent_cooperative_contract=framework if channel == decp_framework_channel() else None,
        lifecycle=lifecycle,
        raw=dict(raw),
    )


def _first_titulaire(titulaires: Any) -> str | None:
    """The first titulaire's SIRET/name from a DECP ``titulaires[]`` array (F9.16)."""
    if not isinstance(titulaires, Sequence) or isinstance(titulaires, (str, bytes)):
        return None
    for item in titulaires:
        holder = item.get("titulaire") if isinstance(item, Mapping) else None
        if isinstance(holder, Mapping):
            value = _opt_str(holder.get("id") or holder.get("denomination"))
            if value:
                return value
        elif isinstance(item, Mapping):
            value = _opt_str(item.get("id"))
            if value:
                return value
    return None


# --- the per-capture quality report (§23.1 universal rule) --------------------


@dataclass(frozen=True)
class CaptureQualityReport:
    """The quality report produced **per capture** (§23.1, phase-gate data quality)."""

    source_id: str
    capture_digest: str
    media_type: str
    byte_size: int
    capture_kind: str  # "prefectoral_order" | "records_request" | "contract"
    connector_name: str
    connector_version: str
    vocab_version: str
    legal_instrument_count: int = 0
    contract_count: int = 0
    acquisition_method_count: int = 0
    claim_count: int = 0

    def to_row(self) -> dict[str, Any]:
        return {
            "record_kind": "quality_report",
            "source_id": self.source_id,
            "capture_digest": self.capture_digest,
            "media_type": self.media_type,
            "byte_size": self.byte_size,
            "capture_kind": self.capture_kind,
            "connector_name": self.connector_name,
            "connector_version": self.connector_version,
            "vocab_version": self.vocab_version,
            "legal_instrument_count": self.legal_instrument_count,
            "contract_count": self.contract_count,
            "acquisition_method_count": self.acquisition_method_count,
            "claim_count": self.claim_count,
        }


# --- the records connector ----------------------------------------------------


@register
class FranceBelgiumRecordsConnector(Connector):
    """The `france_belgium_records` connector: prefectural orders + the CADA/no-regime vocabulary.

    Runs on the P04.1 eight-stage framework. ``discover``/``fetch`` acquire known
    targets through the shared politeness layer (SIG-INGEST-011); ``parse``/
    ``extract``/``normalize`` are pure functions of the capture that build
    :class:`LegalInstrument` entities from published arrêtés préfectoraux
    (``instrument_type`` in the ``prefectoral_order`` family) and emit the
    internationalized ``acquisition_method`` regime for the jurisdiction — ``fr.cada``
    for France, ``no_equivalent_available`` for Belgium — never ``foia_request``
    (SIG-ONTO-068). Every claim is confined to the predicate allowlist (SIG-INGEST-033);
    the connector emits candidate identifiers and never resolves entities (SIG-INGEST-034).
    """

    name = "france_belgium_records"
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — known lookups supplied on the run context."""
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only (SIG-INGEST-011)."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def discover_more(
        self, ctx: RunContext, captures: Sequence[CaptureRef]
    ) -> list[Mapping[str, Any]]:
        """Resolve bounded per-prefecture gazette PDFs from a captured RAA index (P25.5).

        A ``resource_index`` capture IS the discovery surface: its rows are
        filtered through the reviewed ``[raa_index]`` bounds (departement
        allowlist, arrêté titre pattern, https-only, ``max_documents`` cap) into
        ``instrument_document`` targets, each carrying its index row's fields.
        The pass is network-isolated — a pure function of captured bytes; only
        the driver's ``fetch()`` egresses for the resolved children.
        """
        out: list[Mapping[str, Any]] = []
        for capture in captures:
            spec = _configured_target(ctx, capture.source_uri)
            if not spec or str(spec.get("kind") or "") != "resource_index":
                continue
            for target in resolve_raa_targets(ctx, capture, spec):
                url = str(target["url"])
                if url not in ctx.resolved_targets:
                    ctx.resolved_targets[url] = target
                    out.append(target)
        return out

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes — a JSON payload, an index, a feed, or a document.

        A JSON capture is the arrêtés / records-request payload. A target whose
        configured kind is ``resource_index`` is parsed STRICTLY as the RAA index
        CSV (a changed header is ContentDrift); ``feed`` is the MaDada Atom feed
        (entry-shape drift is ContentDrift; request text is never read);
        ``instrument_document`` is a resolved gazette child — classified via
        P07.1, and a digital-native PDF gets a genre verdict from its own text.
        Anything else is an upstream document classified via the P07.1 parser —
        the derived-facts basis permits capturing provenance, never re-hosting
        the bytes.
        """
        data = ctx.captures.get(capture.digest)
        target = _configured_target(ctx, capture.source_uri)
        kind = str(target.get("kind") or "") if target else ""
        if kind == "resource_index":
            index = parse_raa_index(data, source_id=ctx.source.id)
            verdict = classify(_filename_from_uri(capture.source_uri), data)
            return {
                "kind": "resource_index",
                "capture": capture,
                "verdict": verdict.to_row(),
                "byte_size": len(data),
                "header": list(index.header),
                "entry_count": index.entry_count,
                "malformed_count": index.malformed_count,
            }
        if kind == "feed":
            entries = parse_atom_feed(data, source_id=ctx.source.id)
            verdict = classify(_filename_from_uri(capture.source_uri), data)
            return {
                "kind": "atom_feed",
                "capture": capture,
                "verdict": verdict.to_row(),
                "byte_size": len(data),
                "entries": [
                    {
                        "row": e.row,
                        "atom_id": e.atom_id,
                        "link": e.link,
                        "published": e.published,
                        "updated": e.updated,
                    }
                    for e in entries
                ],
            }
        if kind == "instrument_document":
            verdict = classify(_filename_from_uri(capture.source_uri), data)
            page_count = 0
            genre: dict[str, Any] | None = None
            if verdict.file_format is FileFormat.PDF and not verdict.encrypted:
                pages = pdf_text_pages(data)
                page_count = len(pages)
                if any(pages):
                    genre = classify_genre(
                        _filename_from_uri(capture.source_uri),
                        "\n".join(pages).encode("utf-8"),
                    ).to_row()
            return {
                "kind": "instrument_document",
                "capture": capture,
                "verdict": verdict.to_row(),
                "byte_size": len(data),
                "page_count": page_count,
                "genre": genre,
                "target": dict(ctx.resolved_targets.get(capture.source_uri) or target or {}),
            }
        if _is_json_media(capture.media_type):
            return {"payload": json.loads(data), "capture": capture}
        verdict = classify(_filename_from_uri(capture.source_uri), data)
        return {
            "kind": "document",
            "capture": capture,
            "verdict": verdict.to_row(),
            "byte_size": len(data),
        }

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw records with their kind, preserving raw values (P2).

        A document capture yields one evidence record carrying its provenance
        and P07.1 verdict. A ``resource_index`` capture additionally yields an
        index record (entry/malformed counts). An ``instrument_document``
        capture yields an evidence record and — only when the document itself
        supports it (an unencrypted PDF gazette) — a ``prefectoral_order`` raw
        record whose fields come from the resolved index row (with the derived
        CSI L252 sunset). An ``atom_feed`` capture yields an evidence record
        plus one records-request context per entry — safe metadata only, never
        request text. Otherwise the wrapping list key is authoritative —
        ``prefectoral_orders`` records are prefectural orders and
        ``records_requests`` records are records-request contexts, regardless of
        their inner fields. Only for a bare object/list is the kind inferred (an
        explicit ``record_kind``/``kind``, else a ``jurisdiction`` field marks a
        records-request context).
        """
        kind = parsed.get("kind")
        if kind in {"document", "resource_index", "instrument_document", "atom_feed"}:
            capture = parsed["capture"]
            evidence_document: dict[str, Any] = {
                "record_kind": "evidence_document",
                "source_uri": capture.source_uri,
                "capture_digest": capture.digest,
                "media_type": capture.media_type,
                "byte_size": parsed["byte_size"],
                "verdict": parsed["verdict"],
            }
            if kind == "resource_index":
                return [
                    evidence_document,
                    {
                        "record_kind": "resource_index",
                        "source_uri": capture.source_uri,
                        "capture_digest": capture.digest,
                        "media_type": capture.media_type,
                        "byte_size": parsed["byte_size"],
                        "header": parsed["header"],
                        "entry_count": parsed["entry_count"],
                        "malformed_count": parsed["malformed_count"],
                    },
                ]
            if kind == "instrument_document":
                out: list[Mapping[str, Any]] = [evidence_document]
                target = parsed.get("target") or {}
                verdict = parsed["verdict"]
                supports = verdict.get("file_format") == "pdf" and not verdict.get("encrypted")
                if supports and target.get("url"):
                    titre = str(target.get("titre") or "")
                    out.append(
                        {
                            "record_kind": "prefectoral_order",
                            "raw": {
                                "external_id": str(target["url"]),
                                "titre": titre,
                                "departement": str(target.get("departement") or ""),
                                "effective_from": _sniff_raa_date(titre),
                                "resource_updated_at": target.get("mise_a_jour"),
                                "index_url": target.get("index_url"),
                                "index_row": target.get("index_row"),
                                "document_url": str(target["url"]),
                                "document_genre": parsed.get("genre"),
                                "_media_type": capture.media_type,
                                "_evidence": {
                                    "source_url": str(target["url"]),
                                    "retrieved_date": _retrieved_date(capture),
                                    "extraction_method": "structured_import",
                                    # SIG-PARSE-003 rows are 0-based: the index
                                    # row ordinal minus the header.
                                    "locator": Locator.row(
                                        max(0, int(target.get("index_row") or 1) - 1)
                                    ).to_row(),
                                },
                            },
                        }
                    )
                return out
            # atom_feed: one records-request context per entry — the atom id,
            # timestamps, and event link ONLY; <title>/<content> are request
            # text and are never parsed into a record (the [madada_feed]
            # contract's never_emit list).
            out = [evidence_document]
            for entry in parsed.get("entries", []):
                out.append(
                    {
                        "record_kind": "records_request",
                        "raw": {
                            "jurisdiction": "FR",
                            "subject": _atom_entry_subject(
                                AtomEntry(
                                    row=int(entry["row"]),
                                    atom_id=str(entry["atom_id"]),
                                    link=str(entry["link"]),
                                    published=str(entry["published"]),
                                    updated=str(entry["updated"]),
                                )
                            ),
                            "request_url": str(entry["link"]),
                            "external_id": str(entry["atom_id"]),
                            "published": str(entry["published"]),
                            "updated": str(entry["updated"]),
                            "_media_type": capture.media_type,
                            "_evidence": {
                                "source_url": str(entry["link"]),
                                "retrieved_date": _retrieved_date(capture),
                                "extraction_method": "structured_import",
                                "locator": Locator.row(max(0, int(entry["row"]) - 1)).to_row(),
                            },
                        },
                    }
                )
            return out
        payload = parsed["payload"]
        out2: list[Mapping[str, Any]] = []
        if isinstance(payload, Mapping) and (
            "prefectoral_orders" in payload or "records_requests" in payload
        ):
            for obj in payload.get("prefectoral_orders", []) or []:
                out2.append({"record_kind": "prefectoral_order", "raw": dict(obj)})
            for obj in payload.get("records_requests", []) or []:
                out2.append({"record_kind": "records_request", "raw": dict(obj)})
            return out2
        for obj in _decp_or_list(payload, keys=()):
            kind2 = obj.get("record_kind") or obj.get("kind")
            if kind2 is None:
                kind2 = "records_request" if obj.get("jurisdiction") else "prefectoral_order"
            out2.append({"record_kind": str(kind2), "raw": dict(obj)})
        return out2

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist."""
        out: list[dict[str, Any]] = []
        artifact_count = 0
        for raw in raw_claims:
            if raw["record_kind"] == "evidence_document":
                out.append(_document_artifact_row(ctx.source.id, raw))
                artifact_count += 1
            elif raw["record_kind"] == "resource_index":
                # The captured index is an evidence artifact AND a quality datum:
                # entry/malformed counts record what the index yielded (P25.5).
                out.append(
                    _stamp(
                        {
                            "record_kind": "quality_report",
                            "source_id": ctx.source.id,
                            "capture_digest": str(raw["capture_digest"]),
                            "media_type": str(raw["media_type"]),
                            "byte_size": int(raw["byte_size"]),
                            "capture_kind": "resource_index",
                            "header": list(raw["header"]),
                            "entry_count": int(raw["entry_count"]),
                            "malformed_count": int(raw["malformed_count"]),
                            "connector_name": self.name,
                            "connector_version": self.version,
                            "vocab_version": vocab_version(),
                        },
                        source_id=ctx.source.id,
                    )
                )
            elif raw["record_kind"] == "records_request":
                out.extend(self._normalize_records_request(ctx, raw["raw"]))
            else:
                out.extend(self._normalize_prefectoral_order(ctx, raw["raw"]))
        if artifact_count:
            out.append(
                _stamp(
                    {
                        "record_kind": "quality_report",
                        "source_id": ctx.source.id,
                        "capture_digest": str(raw_claims[0].get("capture_digest", "")),
                        "media_type": str(raw_claims[0].get("media_type", "")),
                        "byte_size": int(raw_claims[0].get("byte_size", 0)),
                        "capture_kind": "document",
                        "connector_name": self.name,
                        "connector_version": self.version,
                        "vocab_version": vocab_version(),
                        "evidence_artifact_count": artifact_count,
                        "claim_count": len(raw_claims) - artifact_count,
                        "classification": raw_claims[0].get("verdict"),
                    },
                    source_id=ctx.source.id,
                )
            )
        return out

    def _normalize_prefectoral_order(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        instrument = prefectoral_order_from_raa(raw, source_id=ctx.source.id)
        rows: list[dict[str, Any]] = list(instrument.claim_rows())
        _merge_evidence(rows, raw)
        claim_count = sum(1 for r in rows if r.get("record_kind") == "claim")
        report = CaptureQualityReport(
            source_id=ctx.source.id,
            capture_digest=_digest_of(raw),
            media_type=str(raw.get("_media_type") or "application/json"),
            byte_size=len(json.dumps(raw, sort_keys=True, default=str)),
            capture_kind="prefectoral_order",
            connector_name=self.name,
            connector_version=self.version,
            vocab_version=vocab_version(),
            legal_instrument_count=1,
            claim_count=claim_count,
        )
        rows.append(_stamp(report.to_row(), source_id=ctx.source.id))
        return rows

    def _normalize_records_request(
        self, ctx: RunContext, raw: Mapping[str, Any]
    ) -> list[dict[str, Any]]:
        jurisdiction = str(raw["jurisdiction"])
        subject_id = str(
            raw.get("subject_id") or raw.get("subject") or f"jurisdiction:{jurisdiction}"
        )
        row = acquisition_method_claim(
            jurisdiction=jurisdiction,
            subject_id=subject_id,
            source_id=ctx.source.id,
            raw_value=_opt_str(raw.get("raw_value") or raw.get("request_url")),
            known_complete_unknown=bool(raw.get("known_complete_unknown")),
        )
        _merge_evidence([row], raw)
        report = CaptureQualityReport(
            source_id=ctx.source.id,
            capture_digest=_digest_of(raw),
            media_type="application/json",
            byte_size=len(json.dumps(raw, sort_keys=True, default=str)),
            capture_kind="records_request",
            connector_name=self.name,
            connector_version=self.version,
            vocab_version=vocab_version(),
            acquisition_method_count=1,
            claim_count=1,
        )
        return [row, _stamp(report.to_row(), source_id=ctx.source.id)]

    # link() inherited (identity): SIG-INGEST-034 — candidate identifiers only.

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only)."""
        return load_claims_for_l1(linked)


# --- the procurement connector ------------------------------------------------


@register
class FranceBelgiumProcurementConnector(Connector):
    """The `france_belgium_procurement` connector: DECP national open-data → Contract (§23.6).

    Runs on the P04.1 eight-stage framework. ``parse``/``extract``/``normalize`` are
    pure functions of the capture that map each DECP marché onto the country-neutral
    :class:`Contract` (F9.16), setting ``parent_cooperative_contract`` on a marché
    riding an accord-cadre (SIG-ONTO-032). Every claim is confined to the Contract
    predicate allowlist (enforced by :class:`Contract`); the connector emits candidate
    identifiers and never resolves entities (SIG-INGEST-034).
    """

    name = "france_belgium_procurement"
    version = "1.0.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def discover_more(
        self, ctx: RunContext, captures: Sequence[CaptureRef]
    ) -> list[Mapping[str, Any]]:
        """Resolve the reviewed DECP resource's current URL from the dataset index.

        A ``dataset_index`` capture IS the indirection (P25.7): the data.gouv.fr
        dataset-API document lists the current resource URLs, so the run
        resolves the reviewed resource's live URL at run time — a regenerated
        resource moves URL and still resolves; a removed/renamed one is a
        recorded disappearance on ``ctx.resolved_disappearances``, never a
        stale-URL fallback. The pass is network-isolated — a pure function of
        captured bytes; only the driver's ``fetch()`` egresses for the resolved
        resource.
        """
        out: list[Mapping[str, Any]] = []
        for capture in captures:
            spec = _configured_target(ctx, capture.source_uri)
            if not spec or str(spec.get("kind") or "") != "dataset_index":
                continue
            for target in resolve_decp_targets(ctx, capture, spec):
                url = str(target["url"])
                if url not in ctx.resolved_targets:
                    ctx.resolved_targets[url] = target
                    out.append(target)
        return out

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured DECP JSON payload — or the dataset-API index.

        A ``dataset_index`` capture is the data.gouv.fr dataset document (P25.7),
        parsed STRICTLY: a changed API shape is :class:`ContentDrift`, never a
        guessed resource. Any other capture is the consolidated DECP payload
        itself (the resolved resource's bytes).
        """
        data = ctx.captures.get(capture.digest)
        target = _configured_target(ctx, capture.source_uri)
        kind = str(target.get("kind") or "") if target else ""
        if kind == "dataset_index" and target is not None:
            dataset = parse_decp_dataset(data, source_id=ctx.source.id)
            verdict = classify(_filename_from_uri(capture.source_uri), data)
            return {
                "kind": "dataset_index",
                "capture": capture,
                "verdict": verdict.to_row(),
                "byte_size": len(data),
                "dataset_id": dataset.dataset_id,
                "dataset_title": dataset.title,
                "resource_title": str(target.get("resource_title") or ""),
                "resource_count": len(dataset.resources),
                "resources": [
                    {
                        "title": r.title,
                        "url": r.url,
                        "id": r.resource_id,
                        "last_modified": r.last_modified,
                        "format": r.format,
                    }
                    for r in dataset.resources
                ],
            }
        return {"payload": json.loads(data), "capture": capture}

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Pull the DECP marché records, preserving raw values (P2).

        A ``dataset_index`` capture yields one index record (the dataset identity,
        the reviewed ``resource_title`` selector, and the resource count) — the
        indirection's provenance. The resolved resource capture yields the
        marché records as before.
        """
        if parsed.get("kind") == "dataset_index":
            capture = parsed["capture"]
            return [
                {
                    "record_kind": "dataset_index",
                    "source_uri": capture.source_uri,
                    "capture_digest": capture.digest,
                    "media_type": capture.media_type,
                    "byte_size": parsed["byte_size"],
                    "dataset_id": parsed["dataset_id"],
                    "dataset_title": parsed["dataset_title"],
                    "resource_title": parsed["resource_title"],
                    "resource_count": parsed["resource_count"],
                }
            ]
        payload = parsed["payload"]
        return [{"record_kind": "contract", "raw": dict(obj)} for obj in _decp_marches(payload)]

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            if raw["record_kind"] == "dataset_index":
                # The captured dataset-API document is a quality datum: it
                # records the indirection's outcome — which dataset, which
                # resource selector, how many resources the index listed (P25.7).
                out.append(
                    _stamp(
                        {
                            "record_kind": "quality_report",
                            "source_id": ctx.source.id,
                            "capture_digest": str(raw["capture_digest"]),
                            "media_type": str(raw["media_type"]),
                            "byte_size": int(raw["byte_size"]),
                            "capture_kind": "dataset_index",
                            "dataset_id": str(raw["dataset_id"]),
                            "dataset_title": str(raw["dataset_title"]),
                            "resource_title": str(raw["resource_title"]),
                            "resource_count": int(raw["resource_count"]),
                            "connector_name": self.name,
                            "connector_version": self.version,
                            "vocab_version": vocab_version(),
                        },
                        source_id=ctx.source.id,
                    )
                )
                continue
            contract = contract_from_decp(raw["raw"], source_id=ctx.source.id)
            rows = list(contract.claim_rows())
            claim_count = sum(1 for r in rows if r.get("record_kind") == "claim")
            report = CaptureQualityReport(
                source_id=ctx.source.id,
                capture_digest=_digest_of(raw["raw"]),
                media_type="application/json",
                byte_size=len(json.dumps(raw["raw"], sort_keys=True, default=str)),
                capture_kind="contract",
                connector_name=self.name,
                connector_version=self.version,
                vocab_version=vocab_version(),
                contract_count=1,
                claim_count=claim_count,
            )
            out.extend(rows)
            out.append(_stamp(report.to_row(), source_id=ctx.source.id))
        return out

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


def _configured_target(ctx: RunContext, uri: str) -> Mapping[str, Any] | None:
    """The run-context target spec for a capture URI (configured or resolved, P25.5)."""
    resolved = ctx.resolved_targets.get(uri)
    if resolved is not None:
        return resolved
    for target in ctx.parameters.get("targets", []) or ():
        if str(target.get("url") or "") == uri:
            return target
    return None


def _retrieved_date(capture: CaptureRef) -> str:
    """The capture's retrieval date (ISO); the run date when not recorded."""
    if capture.retrieved_at is not None:
        return capture.retrieved_at.date().isoformat()
    return datetime.now(UTC).date().isoformat()


def _merge_evidence(rows: list[dict[str, Any]], raw: Mapping[str, Any]) -> None:
    """Attach the document evidence block a resolved record carries (P25.5).

    A ``prefectoral_order`` / ``records_request`` raw record built from a captured
    document carries ``_evidence`` (source URL + retrieval date + extraction
    method + locator): every emitted claim row gets it, so the live claim is
    evidence+timestamp complete (P1–P3). Records without the marker are untouched
    (the fixture path).
    """
    evidence = raw.get("_evidence")
    if not isinstance(evidence, Mapping):
        return
    observed_at = str(evidence.get("retrieved_date") or "")
    for row in rows:
        row["evidence"] = dict(evidence)
        row["observed_at"] = observed_at


def _stamp(row: dict[str, Any], *, source_id: str) -> dict[str, Any]:
    """Stamp a row with its source id and the connector vocabulary version (§20)."""
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    return row


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 entity/claim row needs.

    Mirrors the framework's load contract: ``claim_id`` and ``sys_period`` are the two
    non-deterministic columns the reproducibility fingerprint excludes (SIG-INGEST-003).
    Entity, claim, and contract rows get an identity + transaction time; quality
    reports keep their own keys.
    """
    stamped_kinds = {"legal_instrument", "contract", "funding_instrument", "claim"}
    out: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("record_kind") in stamped_kinds:
            out.append(
                {
                    **claim,
                    "claim_id": _new_claim_id(),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        else:
            out.append(dict(claim))
    return out


def _new_claim_id() -> str:
    from uuid import uuid4

    return str(uuid4())


def _decp_or_list(payload: Any, *, keys: Sequence[str]) -> list[Mapping[str, Any]]:
    """Flatten a payload into records: named-list keys, a ``results`` list, or a bare list/obj."""
    out: list[Mapping[str, Any]] = []
    if isinstance(payload, Mapping):
        matched = False
        for key in keys:
            value = payload.get(key)
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                out.extend(dict(o) for o in value)
                matched = True
        if matched:
            return out
        if isinstance(payload.get("results"), Sequence):
            return [dict(o) for o in payload["results"]]
        return [dict(payload)]
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes)):
        return [dict(o) for o in payload]
    return out


def _decp_marches(payload: Any) -> list[Mapping[str, Any]]:
    """The marché records from a DECP payload (``{"marches": {"marche": [...]}}``, F9.16)."""
    if isinstance(payload, Mapping) and "marches" in payload:
        marches = payload["marches"]
        if isinstance(marches, Mapping):
            marche = marches.get("marche", [])
            return [dict(o) for o in marche] if isinstance(marche, Sequence) else []
        if isinstance(marches, Sequence) and not isinstance(marches, (str, bytes)):
            return [dict(o) for o in marches]
    return _decp_or_list(payload, keys=("marche",))


def _raw_value_of(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    return str(value)


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _digest_of(payload: Any) -> str:
    return multihash(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def _plus_years(edtf_date: str, years: int) -> str:
    """Add ``years`` to an ISO/EDTF ``YYYY[-MM-DD]`` date, preserving month/day when present."""
    head = edtf_date.strip()[:10]
    parts = head.split("-")
    try:
        year = int(parts[0])
    except (ValueError, IndexError):
        return edtf_date
    new_year = year + years
    if len(parts) >= 3:
        return f"{new_year:04d}-{parts[1]}-{parts[2]}"
    if len(parts) == 2:
        return f"{new_year:04d}-{parts[1]}"
    return f"{new_year:04d}"


__all__ = [
    "AtomEntry",
    "CaptureQualityReport",
    "Contract",
    "DecpDataset",
    "DecpDatasetResource",
    "FranceBelgiumProcurementConnector",
    "FranceBelgiumRecordsConnector",
    "InvalidAcquisitionMethod",
    "InvalidLegalInstrument",
    "LegalInstrument",
    "PredicateNotAllowed",
    "RaaIndex",
    "RaaIndexEntry",
    "USRecordsMethodError",
    "acquisition_method_claim",
    "acquisition_methods",
    "assert_acquisition_method",
    "assert_legal_predicate_allowed",
    "assert_not_us_records_method",
    "contract_from_decp",
    "decp_acquisition_channel",
    "legal_instrument_predicate_allowlist",
    "legal_instrument_types",
    "load_claims_for_l1",
    "madada_feed_spec",
    "parse_atom_feed",
    "parse_decp_dataset",
    "parse_raa_index",
    "prefectoral_order_family",
    "prefectoral_order_from_raa",
    "raa_index_spec",
    "records_request_method_for",
    "resolve_decp_targets",
    "resolve_raa_targets",
    "source_ids",
    "vocab_version",
]
