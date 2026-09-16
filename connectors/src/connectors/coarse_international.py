# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Coarse international datasets, ingested at explicit coarse granularity (§22.7, §52).

Some international sources are inherently coarse: country-level surveillance
indices (Carnegie's AI Global Surveillance Index), global facial-recognition maps
(the Facial Recognition World Map), and vendor-level international datasets (ASPI's
Mapping China's Tech Giants). SIG-ENG-036 / SIG-INGEST-042 bind their ingestion:
each MUST enter the graph as a claim carrying its **explicit coarse granularity**
and MUST NEVER be disaggregated to agency level by inference — a country-level
index attached to a specific agency would manufacture precision the source never
had (P4, SIG-ONTO-021).

This module is the claim-shaping layer that enforces that. It does not fetch —
these sources are registered LINK-posture and ``ingestion_permitted = false`` until
their rights are reviewed (§22.7) — it owns the **claim shape and the
anti-disaggregation guard** every coarse-international connector must route through:

* :func:`coarse_claim` stamps each row with the dataset's declared granularity and
  a subject at that granularity (a country/region Jurisdiction, or a vendor
  Organization), never an agency.
* :func:`assert_not_disaggregated` is the hard gate: offering an agency-level
  subject for a coarse dataset raises :class:`DisaggregationError`, so the P4
  violation is caught at the seam rather than silently persisted.
"""

from __future__ import annotations

import csv
import io
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from evidence.digest import multihash
from parsing.classification import classify
from parsing.document import html_script_srcs, utf8_text
from parsing.locator import Locator

from ._data import load_table
from .stages import CaptureRef, Connector, ContentDrift, FetchResult, RunContext, register

#: The coarse granularities a country/vendor-level international dataset may claim.
#: `agency`/`device` are deliberately absent — that is the level SIG-INGEST-042
#: forbids inferring.
COARSE_GRANULARITIES = frozenset({"country", "region", "vendor"})

#: Subject kinds that represent an agency-level (or finer) disaggregation. Attaching
#: a coarse dataset's claim to one of these is the inference SIG-ENG-036 prohibits.
DISAGGREGATED_SUBJECT_KINDS = frozenset(
    {"agency", "organization", "deployment", "device", "physical_asset"}
)

#: Subject kinds a coarse claim MAY carry, by granularity. ``vendor`` denotes an
#: Organization bearing the **vendor role** (§12.4) — "vendor" is a role, never an
#: entity subtype (SIG-ONTO-012) — kept distinct from the bare ``organization``
#: subject kind, which is banned precisely because it is the ambiguous agency-level
#: pin SIG-INGEST-042 forbids.
_SUBJECT_KIND_FOR_GRANULARITY = {
    "country": "jurisdiction",
    "region": "jurisdiction",
    "vendor": "vendor",
}


class DisaggregationError(Exception):
    """Raised when a coarse dataset is disaggregated toward agency level (SIG-INGEST-042).

    The mechanical form of SIG-ENG-036: a country-/vendor-level claim MUST NOT be
    pinned to a specific agency, deployment, or device by inference. Raised naming
    the dataset and subject so the P4 defect is auditable.
    """


class CoarseGranularityError(Exception):
    """Raised when a dataset declares a granularity that is not coarse."""


@dataclass(frozen=True)
class CoarseDataset:
    """A registered coarse international dataset (§22.7, SIG-INGEST-042)."""

    #: The source-registry id this dataset is seeded under.
    source_id: str
    #: Human-readable dataset name.
    name: str
    #: The dataset's explicit coarse granularity — one of :data:`COARSE_GRANULARITIES`.
    granularity: str

    def __post_init__(self) -> None:
        if self.granularity not in COARSE_GRANULARITIES:
            raise CoarseGranularityError(
                f"dataset {self.source_id!r} declares granularity {self.granularity!r}; "
                f"coarse international datasets are one of {sorted(COARSE_GRANULARITIES)} "
                "(SIG-INGEST-042)."
            )


#: The three coarse international datasets named for Stage 6 (§22.7, OL-5.3-01).
#: Country-level indices and a global FR map are `country`; the ASPI vendor study
#: is `vendor`. Each is registered in the source registry (data/sources.toml).
DATASETS: dict[str, CoarseDataset] = {
    "carnegie_ai_gsi": CoarseDataset(
        source_id="carnegie_ai_gsi",
        name="AI Global Surveillance Index (Carnegie)",
        granularity="country",
    ),
    "facial_recognition_world_map": CoarseDataset(
        source_id="facial_recognition_world_map",
        name="Facial Recognition World Map",
        granularity="country",
    ),
    "aspi_mapping_chinas_tech_giants": CoarseDataset(
        source_id="aspi_mapping_chinas_tech_giants",
        name="Mapping China's Tech Giants (ASPI)",
        granularity="vendor",
    ),
}


def assert_not_disaggregated(dataset: CoarseDataset, subject_kind: str) -> None:
    """Reject an agency-level subject for a coarse dataset (SIG-ENG-036/INGEST-042).

    A coarse dataset's claim subject must sit at its own granularity — a
    country/region :class:`Jurisdiction` or a vendor :class:`Organization` — never
    an agency, deployment, or device. Anything in :data:`DISAGGREGATED_SUBJECT_KINDS`
    raises :class:`DisaggregationError`.
    """
    if subject_kind in DISAGGREGATED_SUBJECT_KINDS:
        raise DisaggregationError(
            f"dataset {dataset.source_id!r} is {dataset.granularity}-level; attaching its "
            f"claim to a {subject_kind!r} subject would disaggregate it to agency level by "
            "inference (SIG-ENG-036 / SIG-INGEST-042, P4)."
        )
    expected = _SUBJECT_KIND_FOR_GRANULARITY[dataset.granularity]
    if subject_kind != expected:
        raise DisaggregationError(
            f"dataset {dataset.source_id!r} is {dataset.granularity}-level; its claim "
            f"subject must be a {expected!r}, not {subject_kind!r} (SIG-INGEST-042)."
        )


def coarse_claim(
    dataset: CoarseDataset,
    *,
    subject_kind: str,
    subject_id: str,
    predicate: str,
    value: Any,
    raw_value: str,
    attribution: str,
) -> dict[str, Any]:
    """Build one coarse-granularity claim row (SIG-INGEST-042).

    Routes through :func:`assert_not_disaggregated` so the granularity guard cannot
    be bypassed, then stamps the row with the dataset's ``granularity``, the raw
    upstream value (P2), and a ``disaggregation_prohibited`` marker that travels with
    the claim so no downstream step re-pins it to an agency.
    """
    assert_not_disaggregated(dataset, subject_kind)
    return {
        "record_kind": "claim",
        "source_id": dataset.source_id,
        "subject_kind": subject_kind,
        "subject_id": subject_id,
        "predicate_id": predicate,
        "value": value,
        "raw_value": raw_value,  # P2: the coarse source value is preserved verbatim
        "granularity": dataset.granularity,  # SIG-INGEST-042: explicit, never inferred finer
        "disaggregation_prohibited": True,
        "source_attribution": attribution,
    }


# --- the REFERENCE-capture path (§47, P18.1, P21.8) ---------------------------
#
# The three datasets were flipped on counsel approval (HG-02, 2026-09-15): DERIVE
# custody on the derived-facts basis — coarse country/vendor-level facts only,
# never the upstream page/dataset bytes. This connector is the capture path: it
# drives the extractor above through the eight-stage framework, so
# ``run --mode live`` on a flipped source ingests it — and ``run --mode live``
# on an un-flipped source REFUSES at the loader gate (exit 3). Over committed
# fixtures it runs in replay/shadow with no network (SIG-INGEST-018/019).


def parse_coarse(data: bytes) -> dict[str, Any]:
    """Parse a coarse-international dataset capture (pure function of the bytes)."""
    payload = json.loads(data.decode("utf-8"))
    if "rows" not in payload:
        raise ValueError("a coarse-international capture must carry a 'rows' list (§22.7)")
    return payload


def _is_json_media(media_type: str) -> bool:
    # Only a JSON content type is the curated dataset payload; everything else —
    # including text/html — is an upstream document routed to the P07.1 classifier.
    return "json" in media_type.lower()


def _filename_from_uri(uri: str) -> str:
    tail = uri.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return tail or "document"


def document_artifact_id(source_uri: str) -> str:
    """The stable EvidenceArtifact id for an upstream document at ``source_uri``.

    Keyed on the source URI, not the bytes, so the id is stable across
    re-captures and never depends on capture order (§10.2). Deterministic.
    """
    return f"coarse:artifact:{multihash(source_uri.encode('utf-8'))}"


def _document_artifact_row(source_id: str, record: Mapping[str, Any]) -> dict[str, Any]:
    """An upstream document capture as an EvidenceArtifact row (§10.2).

    The coarse sources are DERIVE-posture (``LicenseRef-DerivedFacts-Citations``,
    redistributable=false): the bytes are **never re-hosted** — the row carries
    provenance (source URI, content-addressed capture digest, media type, size)
    plus the P07.1 classification verdict, recorded but not run to a layer engine
    (SIG-PARSE-001/002). The SIG-INGEST-042 anti-disaggregation guard is moot for a
    provenance row: it asserts no granularity claim at all.
    """
    source_uri = str(record["source_uri"])
    return {
        "record_kind": "evidence_artifact",
        "subject_id": document_artifact_id(source_uri),
        "predicate_id": "document",
        "published_by": source_id,
        "source_uri": source_uri,
        "capture_digest": str(record["capture_digest"]),
        "media_type": str(record["media_type"]),
        "byte_size": int(record["byte_size"]),
        "integrity": "captured",
        "classification": dict(record["verdict"]),
        "raw_value": source_uri,
    }


# --- the versioned vocabulary + the curated-adapter surface (P25.4) -----------
#
# ``data/coarse_international_vocab.toml`` (SIG-ENG-001 — data, not code) carries
# the predicate allowlist, the aggregate-only forbidden-column tokens, and the
# per-source adapter spec: where each flipped source's real data surface lives
# (the Carnegie page's embedded JS dataset array; the FRWM page's linked Google
# Sheet) and the strict shape it is parsed under. A changed upstream shape is
# :class:`ContentDrift` — recorded loud, never a silent empty set.


@cache
def vocab() -> dict[str, Any]:
    """The versioned `coarse_international` vocabulary (`coarse_international_vocab.toml`)."""
    return load_table("coarse_international_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def adapter_spec(source_id: str) -> Mapping[str, Any] | None:
    """The reviewed adapter spec for ``source_id`` (``[adapters.<id>]``), if any."""
    return vocab().get("adapters", {}).get(source_id)


def coarse_predicate_allowlist() -> frozenset[str]:
    """The predicate surface this connector may write (typed claims only)."""
    return frozenset(vocab()["coarse_predicate_allowlist"])


def forbidden_column_tokens() -> tuple[str, ...]:
    """The column/field-name tokens that mark a non-aggregate axis (RISK-P0-08)."""
    return tuple(vocab()["forbidden_column_tokens"])


class CoarsePredicateNotAllowed(Exception):
    """Raised when a coarse row carries a predicate outside the allowlist (§10.5 D6)."""


class CoarseNonAggregateError(Exception):
    """Raised when a live coarse data surface carries a per-search/per-person field.

    The coarse datasets are country/vendor aggregates ONLY (SIG-INGEST-042,
    Part VIII): a column or field whose name carries a forbidden token (a
    per-search/per-plate/per-person or per-device axis) is refused whole, naming
    the offender so the defect is auditable.
    """


def assert_coarse_predicate(predicate: str) -> str:
    """Return ``predicate`` if on the coarse allowlist, else raise (typed claims only)."""
    if predicate not in coarse_predicate_allowlist():
        raise CoarsePredicateNotAllowed(
            f"the coarse_international connector may write only "
            f"{sorted(coarse_predicate_allowlist())} (SIG-INGEST-042); "
            f"{predicate!r} is outside the allowlist."
        )
    return predicate


def assert_coarse_aggregate_fields(names: Sequence[str]) -> None:
    """Reject any field/column name carrying a per-search/per-person token.

    The hard mechanical form of the aggregate-only rule for the coarse sources:
    a live data surface that grew a per-search, per-plate, per-person, or
    per-device column is refused before a single claim is built (RISK-P0-08).
    """
    for name in names:
        # Normalize separators so a "Search subject name" / "search-subject-name"
        # column cannot dodge the "subject_name" token on punctuation alone.
        lowered = re.sub(r"[\s\-]+", "_", str(name).strip().lower())
        for token in forbidden_column_tokens():
            if token in lowered:
                raise CoarseNonAggregateError(
                    f"coarse dataset field {name!r} matches the forbidden non-aggregate "
                    f"token {token!r}; the connector ingests country/vendor AGGREGATE "
                    "rows ONLY — per-search/per-person/per-device columns are never "
                    "stored (SIG-INGEST-042, §18.1, RISK-P0-08)."
                )


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


def _evidence(capture: CaptureRef, locator: Mapping[str, Any]) -> dict[str, Any]:
    """The evidence block every adapter-emitted claim carries (P1–P3, §3.1)."""
    return {
        "source_url": capture.source_uri,
        "retrieved_date": _retrieved_date(capture),
        "extraction_method": "structured_import",
        "locator": dict(locator),
    }


# --- adapter 1: the embedded-dataset page (carnegie_ai_gsi) --------------------
#
# The AI Global Surveillance Index feature page is a Next.js client-rendered
# interactive: the dataset lives inside one of the page's ``<script src>`` chunk
# files as a minified array of per-country objects — ``{arrayItem:!0,chinese:!0,
# city:!1,country:"Algeria",description:"...",facial:!0,id:"DZ",inactiveMapData:
# {…},mapData:{…},policing:!0,us:!1}``. The page is the discovery surface
# (``discover_more`` resolves its chunk links into bounded ``dataset_chunk``
# targets); the chunk carrying ``entry_marker`` is the data surface. The parser
# is STRICT: the marker is unique to the dataset array, every entry must match
# the full field shape, and the per-entry ids must be internally consistent — a
# partial or malformed extraction is ContentDrift, never garbage.


def _js_unescape(text: str) -> str:
    """Unescape a JS string literal's body (``\\"`` ``\\'`` ``\\n`` ``\\uXXXX`` ``\\\\``)."""

    def _rep(m: re.Match[str]) -> str:
        esc = m.group(1)
        if esc == "u":
            return m.group(0)  # \\uXXXX handled below
        return {'"': '"', "'": "'", "\\": "\\", "n": "\n", "r": "\r", "t": "\t"}.get(esc, esc)

    out = re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)
    return re.sub(r"\\(.)", _rep, out)


@dataclass(frozen=True)
class EmbeddedEntry:
    """One country entry of the embedded dataset array (the strict-parse result)."""

    byte_start: int  # absolute offset into the capture bytes — the claim locator
    byte_end: int
    country: str
    iso2: str
    flags: Mapping[str, bool]
    companies: tuple[str, ...]
    #: The verbatim ``…Companies: <strong>…</strong>`` inner literal (P2) —
    #: pre-split, pre-``N/A``-stripped; travels into supplier raw_values.
    companies_raw: str


#: The strict per-entry shape of the embedded dataset array (observed 2026-09-15:
#: all 75 entries share this exact field order — a different order or shape is
#: ContentDrift). ``(?:[^"\\]|\\.)*`` matches a JS string body with escapes.
_EMBEDDED_ENTRY_RE = re.compile(
    rb"\{arrayItem:!0,"
    rb"chinese:(?P<chinese>!0|!1),"
    rb"city:(?P<city>!0|!1),"
    rb'country:"(?P<country>(?:[^"\\]|\\.)*)",'
    rb'description:"(?P<description>(?:[^"\\]|\\.)*)",'
    rb"facial:(?P<facial>!0|!1),"
    rb'id:"(?P<id>[A-Z]{2})",'
    rb'inactiveMapData:\{id:"(?P<inactive_id>[A-Z]{2})",settings:\{fill:[a-zA-Z$_0-9]+\}\},'
    rb'mapData:\{id:"(?P<map_id>[A-Z]{2})",settings:\{fill:[a-zA-Z$_0-9]+\}\},'
    rb"policing:(?P<policing>!0|!1),"
    rb"us:(?P<us>!0|!1)\}"
)

#: The per-entry description's supplier list — ``…Companies: <strong>A, B</strong>``.
_COMPANIES_RE = re.compile(r"Companies: <strong>([^<]+)</strong>")


def parse_embedded_dataset(
    data: bytes, *, source_id: str, spec: Mapping[str, Any]
) -> tuple[EmbeddedEntry, ...] | None:
    """Parse a JS chunk for the embedded dataset array — STRICT (fail closed).

    Returns ``None`` when the chunk carries no ``entry_marker`` at all — a
    library/UI chunk, not the data surface (zero claims, no error). When the
    marker IS present every entry must match the full field shape and the three
    per-entry ids must agree; a malformed entry, an inconsistent id, or fewer
    than ``min_entries`` entries is :class:`ContentDrift` — the upstream shape
    changed and the adapter refuses to guess.
    """
    marker = str(spec["entry_marker"]).encode("utf-8")
    starts = [m.start() for m in re.finditer(re.escape(marker), data)]
    if not starts:
        return None
    entries: list[EmbeddedEntry] = []
    flag_fields = list(spec["flag_predicates"].keys())
    for i, start in enumerate(starts):
        match = _EMBEDDED_ENTRY_RE.match(data, start)
        if match is None:
            raise ContentDrift(
                source_id,
                f"embedded dataset entry #{i} no longer matches the strict entry shape — "
                "fail closed, never guess",
                details=data[start : start + 120].decode("utf-8", errors="replace"),
            )
        nxt = match.end()
        expected_next = b",{" if i + 1 < len(starts) else b"]"
        if data[nxt : nxt + len(expected_next)] != expected_next:
            raise ContentDrift(
                source_id,
                "the embedded dataset array is not terminated/contiguous as expected — "
                "the upstream shape changed",
            )
        g = match.groupdict()
        if not (g["id"] == g["inactive_id"] == g["map_id"]):
            raise ContentDrift(
                source_id,
                "an embedded dataset entry's three ids disagree — the shape changed",
                details=g["id"].decode(),
            )
        description = _js_unescape(g["description"].decode("utf-8", errors="replace"))
        companies_m = _COMPANIES_RE.search(description)
        if companies_m is None:
            raise ContentDrift(
                source_id,
                f"entry {g['id'].decode()!r} lost its '…Companies: <strong>' field — "
                "the description shape changed",
            )
        companies_raw = companies_m.group(1).strip()
        companies = tuple(
            name.strip()
            for name in companies_raw.split(",")
            if name.strip() and name.strip() != "N/A"  # N/A is a non-value, not a company
        )
        entries.append(
            EmbeddedEntry(
                byte_start=start,
                byte_end=match.end(),
                country=_js_unescape(g["country"].decode("utf-8", errors="replace")),
                iso2=g["id"].decode(),
                flags={f: g[f] == b"!0" for f in flag_fields},
                companies=companies,
                companies_raw=companies_raw,
            )
        )
    if len(entries) < int(spec["min_entries"]):
        raise ContentDrift(
            source_id,
            f"the embedded dataset yielded {len(entries)} entries (< min_entries "
            f"{spec['min_entries']}) — a partial extraction is drift, not an answer",
        )
    return tuple(entries)


def resolve_dataset_chunks(
    ctx: RunContext, page_capture: CaptureRef, spec: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Resolve the bounded ``dataset_chunk`` targets off a captured index page (P25.4).

    The page's ``<script src>`` list is the discovery surface: chunk links under
    the reviewed path (``script_src_contains`` + suffix + same-host, bounded by
    ``max_chunks``) become fetch targets carrying the page URL as provenance.
    A page that no longer carries any matching chunk link is :class:`ContentDrift`
    — the discovery surface changed and the adapter fails loud.
    """
    from urllib.parse import urlparse

    data = ctx.captures.get(page_capture.digest)
    srcs = html_script_srcs(data, page_capture.source_uri)
    contains = str(spec["script_src_contains"])
    suffix = str(spec["script_src_suffix"])
    host = urlparse(page_capture.source_uri).hostname
    chunks = [s for s in srcs if contains in s and s.split("?", 1)[0].endswith(suffix)]
    if spec.get("same_host", True):
        chunks = [s for s in chunks if urlparse(s).hostname == host]
    if not chunks:
        raise ContentDrift(
            ctx.source.id,
            "the index page no longer carries any matching <script src> chunk link — "
            "the embedded-dataset discovery surface changed",
        )
    max_chunks = int(spec["max_chunks"])
    if len(chunks) > max_chunks:
        # A page that grew past the reviewed bound is a shape change: silently
        # truncating could cut the data chunk out of the run — fail loud instead.
        raise ContentDrift(
            ctx.source.id,
            f"the index page carries {len(chunks)} chunk links (> max_chunks "
            f"{max_chunks}) — the discovery surface grew past the reviewed bound",
        )
    out: list[dict[str, Any]] = []
    for ordinal, url in enumerate(chunks[:max_chunks]):
        out.append(
            {
                "id": f"{ctx.source.id}:chunk:{ordinal}",
                "url": url,
                "kind": "dataset_chunk",
                "index_url": page_capture.source_uri,
                "index_ordinal": ordinal,
            }
        )
    return out


# --- adapter 2: the linked-sheet dataset (facial_recognition_world_map) --------
#
# The FRWM map page carries no per-country table — it links the compiled Google
# Sheet (``page_link_literal``). The six per-continent sheets are fetched as
# gviz CSV seed targets (``dataset_csv``) and parsed STRICTLY: the header must
# equal ``expected_header``, every country name must map through the reviewed
# ``countries`` table, and every status literal through ``status_map`` — a
# changed header, an unmapped literal, or an unmapped country is ContentDrift.
# Upstream's own duplicate (Egypt, on two sheets with disagreeing statuses)
# emits both rows — contradictions stay visible, never silently reconciled (P3).


@dataclass(frozen=True)
class SheetRow:
    """One parsed row of an FRWM sheet CSV (country + status + citations)."""

    row: int  # 0-based data-row ordinal in the sheet — the claim locator
    country: str
    status: str
    source1: str
    source2: str


def parse_dataset_csv(
    data: bytes, *, source_id: str, spec: Mapping[str, Any]
) -> tuple[tuple[str, ...], tuple[SheetRow, ...]]:
    """Parse one gviz ``out:csv`` sheet STRICTLY — header + rows (fail closed)."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ContentDrift(
            source_id, "the sheet capture is not decodable UTF-8 text", details=str(exc)
        ) from exc
    try:
        rows = list(csv.reader(io.StringIO(text)))
    except csv.Error as exc:
        raise ContentDrift(
            source_id, "the sheet capture is not parseable CSV", details=str(exc)
        ) from exc
    if not rows:
        raise ContentDrift(source_id, "the sheet capture is empty")
    header = tuple(str(c).strip() for c in rows[0])
    expected = tuple(str(c) for c in spec["expected_header"])
    if header != expected:
        raise ContentDrift(
            source_id,
            f"the sheet header no longer matches {list(expected)!r} (got "
            f"{list(header)!r}) — fail closed, never guess",
        )
    assert_coarse_aggregate_fields(header)  # the aggregate-only gate on live data
    status_map = spec["status_map"]
    countries = spec["countries"]
    out: list[SheetRow] = []
    for i, row in enumerate(rows[1:]):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != len(expected):
            raise ContentDrift(
                source_id,
                f"sheet row {i + 1} has {len(row)} fields, expected {len(expected)} — "
                "the shape changed",
            )
        country, status, source1, source2, _notes = (cell.strip() for cell in row)
        if country not in countries:
            raise ContentDrift(
                source_id,
                f"sheet row {i + 1} carries unmapped country {country!r} — the "
                "reviewed countries table does not cover it (never guess an ISO code)",
            )
        if status not in status_map:
            raise ContentDrift(
                source_id,
                f"sheet row {i + 1} carries unmapped status {status!r} — the "
                "reviewed status enum does not cover it",
            )
        out.append(
            SheetRow(row=i, country=country, status=status, source1=source1, source2=source2)
        )
    if not out:
        raise ContentDrift(source_id, "the sheet capture yielded zero data rows")
    return header, tuple(out)


# --- the connector ------------------------------------------------------------


@register
class CoarseInternationalConnector(Connector):
    """The `coarse_international` connector — country/vendor-level datasets (§22.7, §47).

    The REFERENCE-capture path for the three coarse international datasets (Carnegie
    AI GSI, Facial Recognition World Map, ASPI Mapping China's Tech Giants). It runs
    on the P04.1 eight-stage framework and routes every row through
    :func:`coarse_claim`, so the **anti-disaggregation guard** (SIG-ENG-036 /
    SIG-INGEST-042) cannot be bypassed: a country/vendor claim can never be pinned
    to an agency. The datasets stay LINK-posture until a packet + flip permits a
    live run, so a live run against an un-flipped source is refused at the loader
    gate (exit 3); replay/shadow run over committed fixtures with no network.
    """

    name = "coarse_international"
    version = "1.1.0"

    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    def discover_more(
        self, ctx: RunContext, captures: Sequence[CaptureRef]
    ) -> list[Mapping[str, Any]]:
        """Resolve bounded ``dataset_chunk`` targets off an embedded-dataset page (P25.4).

        An ``embedded_dataset_page`` capture IS the discovery surface for the JS
        chunk carrying the embedded dataset array: its ``<script src>`` links are
        filtered through the reviewed spec (path + suffix + same-host, bounded by
        ``max_chunks``) and each becomes a fetch target, registered on
        ``ctx.resolved_targets`` so the chunk's post-capture stages see the page
        provenance. Network-isolated — a pure function of captured bytes; only
        the driver's ``fetch()`` egresses for the resolved children.
        """
        spec = adapter_spec(ctx.source.id)
        if not spec or str(spec.get("kind") or "") != "embedded_dataset_page":
            return []
        out: list[Mapping[str, Any]] = []
        for capture in captures:
            target = _configured_target(ctx, capture.source_uri)
            if not target or str(target.get("kind") or "") != "document":
                continue
            for child in resolve_dataset_chunks(ctx, capture, spec):
                url = str(child["url"])
                if url not in ctx.resolved_targets:
                    ctx.resolved_targets[url] = child
                    out.append(child)
        return out

    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes — a dataset surface, a curated payload, or a document.

        Dispatch is on the configured/resolved target kind first (a reviewed
        adapter surface): ``dataset_chunk`` is a JS chunk — strict-parsed for the
        embedded dataset array when it carries the marker (``embedded_dataset``),
        a plain asset otherwise (``js_asset``, zero claims); ``dataset_csv`` is a
        sheet CSV parsed strictly (header/country/status drift is ContentDrift).
        A JSON capture is the curated ``rows`` payload. A ``document`` capture of
        a ``sheet_dataset`` source must still carry its dataset link literal —
        else the page shape drifted. Anything else is an upstream document
        classified via the P07.1 parser — provenance only, never re-hosted.
        """
        data = ctx.captures.get(capture.digest)
        target = _configured_target(ctx, capture.source_uri)
        kind = str(target.get("kind") or "") if target else ""
        spec = adapter_spec(ctx.source.id)
        if kind == "dataset_chunk":
            if spec is None:
                raise ContentDrift(
                    ctx.source.id,
                    "a dataset_chunk target has no adapter spec in the vocabulary — "
                    "the reviewed surface is missing (fail closed)",
                )
            entries = parse_embedded_dataset(data, source_id=ctx.source.id, spec=spec)
            if entries is None:
                return {"kind": "js_asset", "capture": capture, "byte_size": len(data)}
            return {
                "kind": "embedded_dataset",
                "capture": capture,
                "byte_size": len(data),
                "target": dict(target or {}),
                "entries": [
                    {
                        "byte_start": e.byte_start,
                        "byte_end": e.byte_end,
                        "country": e.country,
                        "iso2": e.iso2,
                        "flags": dict(e.flags),
                        "companies": list(e.companies),
                        "companies_raw": e.companies_raw,
                    }
                    for e in entries
                ],
            }
        if kind == "dataset_csv":
            if spec is None:
                raise ContentDrift(
                    ctx.source.id,
                    "a dataset_csv target has no adapter spec in the vocabulary — "
                    "the reviewed surface is missing (fail closed)",
                )
            sheet_name = str((target or {}).get("sheet") or "")
            declared = {str(v) for v in spec.get("sheets", {}).values()}
            if declared and sheet_name not in declared:
                raise ContentDrift(
                    ctx.source.id,
                    f"a dataset_csv target names sheet {sheet_name!r} outside the "
                    f"declared sheet set {sorted(declared)!r} — fail closed",
                )
            header, rows = parse_dataset_csv(data, source_id=ctx.source.id, spec=spec)
            return {
                "kind": "dataset_csv",
                "capture": capture,
                "byte_size": len(data),
                "target": dict(target or {}),
                "sheet": sheet_name,
                "header": list(header),
                "rows": [
                    {
                        "row": r.row,
                        "country": r.country,
                        "status": r.status,
                        "source1": r.source1,
                        "source2": r.source2,
                    }
                    for r in rows
                ],
            }
        if _is_json_media(capture.media_type):
            return parse_coarse(data)
        # document path — for a sheet_dataset source the page must still carry
        # its dataset link literal (the page<->dataset binding); a page that
        # dropped it is drift, not a successful capture.
        if spec and str(spec.get("kind") or "") == "sheet_dataset":
            literal = str(spec["page_link_literal"])
            if literal not in utf8_text(data):
                raise ContentDrift(
                    ctx.source.id,
                    f"the index page no longer carries its dataset link {literal!r} — "
                    "the page<->dataset binding changed",
                )
        verdict = classify(_filename_from_uri(capture.source_uri), data)
        return {
            "kind": "document",
            "capture": capture,
            "verdict": verdict.to_row(),
            "byte_size": len(data),
        }

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        if parsed.get("kind") == "document":
            capture = parsed["capture"]
            return [
                {
                    "record_kind": "evidence_document",
                    "source_uri": capture.source_uri,
                    "capture_digest": capture.digest,
                    "media_type": capture.media_type,
                    "byte_size": parsed["byte_size"],
                    "verdict": parsed["verdict"],
                }
            ]
        if parsed.get("kind") == "js_asset":
            # A non-data JS chunk is a static asset — not evidence of any claim.
            return []
        if parsed.get("kind") == "embedded_dataset":
            return self._extract_embedded_dataset(ctx, parsed)
        if parsed.get("kind") == "dataset_csv":
            return self._extract_dataset_csv(ctx, parsed)
        dataset_id = str(parsed.get("dataset") or ctx.source.id)
        return [{"dataset_id": dataset_id, "row": dict(row)} for row in parsed.get("rows", [])]

    def _extract_embedded_dataset(
        self, ctx: RunContext, parsed: Mapping[str, Any]
    ) -> list[Mapping[str, Any]]:
        """Flatten one embedded dataset entry set into curated rows (P25.4).

        Each country entry emits: the membership claim, one typed bool claim per
        upstream flag, and one supplier claim per company upstream names — every
        row carrying its byte-range locator + retrieval evidence (P1–P3) and the
        verbatim raw value (P2). Country-level only (SIG-INGEST-042).
        """
        spec = adapter_spec(ctx.source.id) or {}
        flag_predicates: Mapping[str, str] = spec.get("flag_predicates", {})
        membership_predicate = str(spec.get("membership_predicate", "uses_ai_surveillance"))
        supplier_predicate = str(spec.get("supplier_predicate", "ai_surveillance_supplier"))
        capture = parsed["capture"]
        dataset_id = str(parsed.get("dataset") or ctx.source.id)
        out: list[Mapping[str, Any]] = [
            {
                "record_kind": "dataset_capture",
                "capture_kind": "embedded_dataset",
                "source_uri": capture.source_uri,
                "capture_digest": capture.digest,
                "media_type": capture.media_type,
                "byte_size": parsed["byte_size"],
                "index_url": str(parsed.get("target", {}).get("index_url") or ""),
                "entry_count": len(parsed["entries"]),
            }
        ]
        for entry in parsed["entries"]:
            subject_id = f"jurisdiction:iso.3166-1:{entry['iso2']}"
            country = str(entry["country"])
            evidence = _evidence(
                capture, Locator.byte_range(entry["byte_start"], entry["byte_end"]).to_row()
            )
            rows: list[dict[str, Any]] = [
                {
                    "subject_id": subject_id,
                    "predicate": membership_predicate,
                    "value": True,
                    "raw_value": f"{country} — indexed as an AI-surveillance adopter",
                },
            ]
            for flag, predicate in flag_predicates.items():
                rows.append(
                    {
                        "subject_id": subject_id,
                        "predicate": str(predicate),
                        "value": bool(entry["flags"][flag]),
                        "raw_value": f"{country} — {flag}={entry['flags'][flag]}",
                    }
                )
            for company in entry["companies"]:
                rows.append(
                    {
                        "subject_id": subject_id,
                        "predicate": supplier_predicate,
                        "value": company,
                        "raw_value": f"{country} — Relevant Companies: {entry['companies_raw']}",
                    }
                )
            for row in rows:
                row["_evidence"] = evidence
                out.append({"dataset_id": dataset_id, "row": row})
        return out

    def _extract_dataset_csv(
        self, ctx: RunContext, parsed: Mapping[str, Any]
    ) -> list[Mapping[str, Any]]:
        """Flatten one sheet CSV into curated status rows (P25.4).

        Each row emits one typed ``facial_recognition_status`` claim — the mapped
        enum value beside the verbatim ``Country — status`` literal (P2), the
        row's source URLs carried as citations, and the cell locator + retrieval
        evidence every live claim needs (P1–P3). Country-level only.
        """
        spec = adapter_spec(ctx.source.id) or {}
        status_map: Mapping[str, str] = spec.get("status_map", {})
        countries: Mapping[str, str] = spec.get("countries", {})
        status_predicate = str(spec.get("status_predicate", "facial_recognition_status"))
        capture = parsed["capture"]
        dataset_id = str(parsed.get("dataset") or ctx.source.id)
        sheet = str(parsed.get("sheet") or "")
        out: list[Mapping[str, Any]] = [
            {
                "record_kind": "dataset_capture",
                "capture_kind": "dataset_csv",
                "source_uri": capture.source_uri,
                "capture_digest": capture.digest,
                "media_type": capture.media_type,
                "byte_size": parsed["byte_size"],
                "sheet": sheet,
                "header": list(parsed["header"]),
                "row_count": len(parsed["rows"]),
            }
        ]
        for r in parsed["rows"]:
            citations = [u for u in (r["source1"], r["source2"]) if u]
            out.append(
                {
                    "dataset_id": dataset_id,
                    "row": {
                        "subject_id": f"jurisdiction:{countries[r['country']]}",
                        "predicate": status_predicate,
                        "value": status_map[r["status"]],
                        "raw_value": f"{r['country']} — {r['status']}",
                        "source_citations": citations,
                        "_evidence": _evidence(
                            capture,
                            Locator.cell(r["row"], 1, sheet=sheet or None).to_row(),
                        ),
                    },
                }
            )
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        artifact_count = 0
        dataset_capture: Mapping[str, Any] | None = None
        claim_count = 0
        for raw in raw_claims:
            if raw.get("record_kind") == "evidence_document":
                out.append(_document_artifact_row(ctx.source.id, raw))
                artifact_count += 1
                continue
            if raw.get("record_kind") == "dataset_capture":
                dataset_capture = raw
                continue
            dataset = DATASETS[str(raw["dataset_id"])]
            subject_kind = _SUBJECT_KIND_FOR_GRANULARITY[dataset.granularity]
            row = dict(raw["row"])
            evidence = row.pop("_evidence", None)
            assert_coarse_aggregate_fields(list(row.keys()))
            assert_coarse_predicate(str(row["predicate"]))
            claim = coarse_claim(
                dataset,
                subject_kind=subject_kind,
                subject_id=str(row.pop("subject_id")),
                predicate=str(row.pop("predicate")),
                value=row.pop("value", None),
                raw_value=str(row.pop("raw_value")),
                attribution=str(row.pop("attribution", dataset.name)),
            )
            # Extra reviewed row fields (e.g. source_citations) pass through;
            # the evidence block stamps every live claim (P1–P3, §3.1).
            claim.update(row)
            if isinstance(evidence, Mapping):
                claim["evidence"] = dict(evidence)
                claim["observed_at"] = str(evidence.get("retrieved_date") or "")
            claim["vocab_version"] = vocab_version()
            out.append(claim)
            claim_count += 1
        if artifact_count:
            out.append(
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
                }
            )
        if dataset_capture is not None:
            out.append(
                {
                    "record_kind": "quality_report",
                    "source_id": ctx.source.id,
                    "capture_digest": str(dataset_capture.get("capture_digest", "")),
                    "media_type": str(dataset_capture.get("media_type", "")),
                    "byte_size": int(dataset_capture.get("byte_size", 0)),
                    "capture_kind": str(dataset_capture.get("capture_kind", "")),
                    "source_uri": str(dataset_capture.get("source_uri", "")),
                    "index_url": str(dataset_capture.get("index_url", "")),
                    "sheet": str(dataset_capture.get("sheet", "")),
                    "entry_count": int(
                        dataset_capture.get("entry_count", dataset_capture.get("row_count", 0))
                    ),
                    "connector_name": self.name,
                    "connector_version": self.version,
                    "vocab_version": vocab_version(),
                    "claim_count": claim_count,
                }
            )
        return out

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for claim in linked:
            out.append(
                {
                    **claim,
                    "claim_id": str(uuid4()),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        return out


__all__ = [
    "COARSE_GRANULARITIES",
    "DATASETS",
    "DISAGGREGATED_SUBJECT_KINDS",
    "CoarseDataset",
    "CoarseGranularityError",
    "CoarseInternationalConnector",
    "CoarseNonAggregateError",
    "CoarsePredicateNotAllowed",
    "DisaggregationError",
    "EmbeddedEntry",
    "SheetRow",
    "adapter_spec",
    "assert_coarse_aggregate_fields",
    "assert_coarse_predicate",
    "assert_not_disaggregated",
    "coarse_claim",
    "coarse_predicate_allowlist",
    "forbidden_column_tokens",
    "parse_coarse",
    "parse_dataset_csv",
    "parse_embedded_dataset",
    "resolve_dataset_chunks",
    "vocab",
    "vocab_version",
]
