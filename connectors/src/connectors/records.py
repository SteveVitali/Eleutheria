# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `records` connector — MuckRock, NextRequest, DocumentCloud (§23.5, P07.2).

A source adapter on the P04.1 eight-stage framework (:mod:`connectors.stages`)
for the public-records channel: it captures the **records requests** SIG cites as
provenance and the **documents they release**, writing :class:`RecordsRequest`
entities, :class:`EvidenceArtifactRow` rows, and released-document captures. It is
of deliberately different shape from ``osm``/``atlas`` — the sources are
rate-limited, auth-gated APIs, so the connector is a **targeted-lookup** client,
never a crawler.

This module owns five things §23.5 / §11.19 assign to P07.2, none of which the
framework provides:

* **The ``RecordsRequest`` runtime shape** (:class:`RecordsRequest`): the §11.19
  predicate surface — ``requesting_party``/``target_agency``/``request_text``/
  ``filed_date``/``response_date``/``response_status``/``statutory_basis``/
  ``platform``/``external_id``/``released_documents`` — validated against the
  frozen ``RecordsResponseStatus``/``RecordsPlatform`` vocabularies and rendered
  to append-only claim rows that preserve ``raw_value`` (P2). P09.1/P10.3 build on
  this shape and the coverage bridge below.
* **The ``no_responsive_records`` → ``CoverageRecord`` bridge** (SIG-ONTO-040): a
  ``response_status`` of ``no_responsive_records`` is a **positive finding**, not a
  discarded null — an agency stating on the record that it holds no ALPR contracts
  is evidence. It writes a coverage record in the ``NO_EVIDENCE_FOUND`` state
  (:mod:`db.absence`, the canonical §9.5 coverage model), which MUST name the
  sources searched (SIG-TIME-011).
* **MuckRock as api_v2 with a short-lived JWT** (:class:`MuckRockTokenCache`): the
  outline's ``api_v1`` reference is wrong. There is no unauthenticated read path;
  every data endpoint requires a Bearer JWT valid for five minutes. The cache
  refreshes on a TTL shorter than the token lifetime and on a 401, and the
  credential rides the single shared egress seam (SIG-INGEST-011) — this is
  authentication, never access-control circumvention (Rule 4 / SIG-INGEST-037).
* **The predicate allowlist as a hard schema gate** (SIG-INGEST-033): the
  connector may write only the ``RecordsRequest`` predicate surface plus the
  released-document capture link. A procurement value, a deployment, or a parsed
  document claim is refused at the ingest boundary — the ``D6`` admissibility
  filter (§10.5) enforced at ingestion.
* **Targeted-lookup discipline** (SIG-INGEST-036/037): rate-limited APIs are
  queried as targeted lookups for **known** requests/agencies/documents; no
  enumeration or crawl is ever attempted. ``discover()`` returns only explicitly
  supplied targets, and :func:`assert_targeted_lookup` refuses a listing/crawl
  target. This posture is a **legal** one — a deviation is an ADR with counsel,
  not an engineering judgement.

The layered parsing of the released documents is **not** done here: P07.1 owns the
parser, and this connector only *calls* it — :func:`parsing.classification.classify`
(and ``classify_archive`` for a mixed-format response bundle) records the
classification verdict and routes each document to a layer; the engines run in
P07.1. Rows are append-only and carry full provenance; the connector emits
**candidate** identifiers for the parties and never resolves entities itself
(SIG-INGEST-034).
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import Any, Protocol, runtime_checkable
from uuid import uuid4

from db.absence import AbsenceState, coverage_kind_for, render_absence
from evidence.digest import multihash
from parsing.classification import (
    ArchiveClassification,
    ClassificationVerdict,
    FileFormat,
    classify,
    classify_archive,
)

from ._data import load_table
from .net import ChallengeEncountered
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

_DETECTOR_VERSION = "connectors.records/1"


# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned `records` connector vocabulary (``data/records_vocab.toml``)."""
    return load_table("records_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def source_ids() -> Mapping[str, str]:
    """The registry source ids the connector runs against (§22.6 F)."""
    return dict(vocab()["sources"])


def response_statuses() -> frozenset[str]:
    """The RecordsRequest response-status vocabulary (§11.19, RecordsResponseStatus)."""
    return frozenset(vocab()["response_statuses"])


def platforms() -> frozenset[str]:
    """The RecordsRequest platform vocabulary (§11.19, RecordsPlatform)."""
    return frozenset(vocab()["platforms"])


def coverage_trigger_status() -> str:
    """The status that is a positive coverage finding (SIG-ONTO-040)."""
    return str(vocab()["coverage_trigger_status"])


# --- the predicate allowlist (SIG-INGEST-033) ---------------------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§23.5, §11.19, SIG-INGEST-033)."""
    return frozenset(vocab()["predicate_allowlist"])


def is_predicate_allowed(predicate: str) -> bool:
    """Whether ``predicate`` is in the connector's allowlist (SIG-INGEST-033)."""
    return predicate in predicate_allowlist()


def forbidden_predicate_genres() -> tuple[str, ...]:
    """The write-set §23.5 places out of scope for this connector (documented complement)."""
    return tuple(vocab()["forbidden_predicate_genres"])


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The records connector may write **only** the ``RecordsRequest`` predicate
    surface plus the released-document capture link (§23.5, §11.19): a procurement
    value, a deployment, a device count, or a parsed-document claim is refused here,
    at the ingestion boundary, rather than only at resolution (SIG-INGEST-033, the
    ``D6`` admissibility filter enforced at ingest).
    """
    if not is_predicate_allowed(predicate):
        raise PredicateNotAllowed(
            f"the records connector may write only {sorted(predicate_allowlist())} "
            f"(§23.5/§11.19, SIG-INGEST-033); {predicate!r} is outside the allowlist — "
            "procurement, deployment, and parsed-document claims are refused."
        )
    return predicate


# --- targeted-lookup discipline (SIG-INGEST-036/037) --------------------------


class CrawlAttempted(Exception):
    """Raised when a target would enumerate/crawl a rate-limited records API.

    Rule 5 of §26 (prefer the offered channel) plus the rate-limit rule mean these
    APIs are used as targeted lookups for **known** requests/agencies/documents
    only. Enumerating a listing endpoint is both prohibited and, at ~15 req/min,
    doomed — and it is a **legal** posture (SIG-INGEST-037): a deviation is an ADR
    with counsel, not an engineering judgement.
    """


def assert_targeted_lookup(target: Mapping[str, Any]) -> Mapping[str, Any]:
    """Return ``target`` if it is a targeted lookup, else raise :class:`CrawlAttempted`.

    A target is targeted iff it names a **specific** resource: a records request by
    ``external_id``, an agency by ``agency_id``, or a released document by ``url``
    (a concrete file). A target that asks to enumerate (``mode='crawl'`` /
    ``'enumerate'`` / ``'list'``, a ``page``/pagination cursor, or a bare listing
    endpoint with no specific id) is refused (SIG-INGEST-036/037).
    """
    mode = str(target.get("mode", "lookup")).lower()
    if mode in {"crawl", "enumerate", "list", "scrape"}:
        raise CrawlAttempted(
            f"target requests mode={mode!r}; the records APIs are targeted lookups only, "
            "never crawled (SIG-INGEST-036/037)."
        )
    if "page" in target or "cursor" in target or "offset" in target:
        raise CrawlAttempted(
            "target carries a pagination cursor; paging a records listing is enumeration, "
            "which the connector never performs (SIG-INGEST-036/037)."
        )
    has_specific = bool(
        target.get("external_id") or target.get("agency_id") or target.get("document_url")
    )
    url = str(target.get("url", ""))
    if not has_specific and _is_enumeration_url(url):
        raise CrawlAttempted(
            f"target url {url!r} is a bare listing endpoint with no specific id; the "
            "connector looks up known requests/agencies/documents only (SIG-INGEST-036/037)."
        )
    return target


def _is_enumeration_url(url: str) -> bool:
    """Whether a URL is a bare collection/listing endpoint (no specific resource).

    A MuckRock ``/api_v2/requests/`` (trailing the collection, nothing after) is a
    listing endpoint; ``/api_v2/requests/12345/`` names one request and is a lookup.
    A query that filters to a specific id (``?id=`` / ``?external_id=``) is a lookup.
    """
    if not url:
        return False
    base, _, query = url.partition("?")
    q = query.lower()
    if any(tok in q for tok in ("id=", "external_id=", "document=", "foia=")):
        return False
    collections = (
        "/api_v2/requests",
        "/api_v2/agencies",
        "/api_v2/communications",
        "/api_v2/files",
        "/api_v2/jurisdictions",
        "/api_v2/organizations",
        "/client/requests",
        "/api/documents/search",
    )
    tail = base.rstrip("/")
    return any(tail.endswith(c) for c in collections)


# --- MuckRock api_v2 endpoints (§23.5, F4.1) ----------------------------------


def muckrock_config() -> Mapping[str, Any]:
    """The MuckRock api_v2 endpoint + auth facts (``[muckrock]`` in the vocab)."""
    return vocab()["muckrock"]


class WrongMuckRockApiVersion(Exception):
    """Raised on any attempt to use the superseded MuckRock ``api_v1`` (§23.5, F4.1)."""


def muckrock_endpoint(name: str, resource_id: str | None = None) -> str:
    """Build a MuckRock **api_v2** endpoint URL (never api_v1, §23.5, F4.1).

    ``name`` is one of the nine api_v2 collections; ``resource_id`` (when given)
    targets one resource — the only shape the connector fetches, since it performs
    targeted lookups, not listings (SIG-INGEST-036).
    """
    cfg = muckrock_config()
    if name not in set(cfg["endpoints"]):
        raise ValueError(f"unknown MuckRock api_v2 endpoint {name!r}; one of {cfg['endpoints']}")
    base = f"{cfg['api_v2_base']}/{name}/"
    return f"{base}{resource_id}/" if resource_id is not None else base


def assert_muckrock_api_v2(url: str) -> str:
    """Return ``url`` if it is an api_v2 URL, else raise :class:`WrongMuckRockApiVersion`.

    The outline's ``api_v1`` reference is wrong and there is no v1 read path worth
    building against (§23.5, F4.1); a v1 URL is refused rather than silently fetched.
    """
    cfg = muckrock_config()
    if str(cfg["api_v1_base"]) in url or "/api_v1/" in url:
        raise WrongMuckRockApiVersion(
            f"{url!r} targets MuckRock api_v1; the connector uses api_v2 only — the "
            "outline's api_v1 reference is wrong (§23.5, F4.1)."
        )
    return url


def is_muckrock_source(source_id: str) -> bool:
    """Whether a registry source id is MuckRock (auth applies to it, §23.5)."""
    return source_id == source_ids().get("muckrock")


# --- the short-lived MuckRock JWT (§23.5, F4.3) -------------------------------


@runtime_checkable
class TokenSource(Protocol):
    """Mints a fresh MuckRock access token (the JWT).

    The concrete mint — a POST of username/password to
    ``accounts.muckrock.com/api/token/`` — is wired by the ops/live-run layer,
    exactly as :class:`connectors.net.Transport` injects the concrete HTTP client;
    here it is the seam :class:`MuckRockTokenCache` refreshes through, so the TTL /
    refresh-on-401 logic is deterministically testable without a real account.
    """

    def mint(self) -> str: ...


@dataclass(frozen=True)
class MuckRockToken:
    """One minted MuckRock access token and its five-minute lifetime (§23.5, F4.3)."""

    access: str
    issued_at: datetime
    ttl_seconds: int

    @property
    def expires_at(self) -> datetime:
        return self.issued_at + timedelta(seconds=self.ttl_seconds)

    def is_expired(self, now: datetime) -> bool:
        """Whether the token has passed its five-minute lifetime (F4.3)."""
        return now >= self.expires_at

    def needs_refresh(self, now: datetime, margin_seconds: int) -> bool:
        """Whether the token is within ``margin_seconds`` of expiry (refresh early)."""
        return now >= self.expires_at - timedelta(seconds=margin_seconds)


class MuckRockTokenCache:
    """A refreshing cache for the five-minute MuckRock JWT (§23.5, F4.3).

    A naive "fetch a token at job start" design fails: the token dies after five
    minutes and every data endpoint 401s thereafter (F4.3). This cache mints on
    first use, refreshes once the token is within the refresh margin of expiry
    (so the effective TTL is **shorter** than the token lifetime), and exposes
    :meth:`invalidate` for refresh-on-401. ``clock`` is injectable so the TTL
    behaviour is testable without real time.
    """

    def __init__(
        self,
        source: TokenSource,
        *,
        ttl_seconds: int | None = None,
        refresh_margin_seconds: int | None = None,
        clock: Any = None,
    ) -> None:
        cfg = muckrock_config()
        self._source = source
        self._ttl = int(ttl_seconds if ttl_seconds is not None else cfg["jwt_ttl_seconds"])
        self._margin = int(
            refresh_margin_seconds
            if refresh_margin_seconds is not None
            else cfg["refresh_margin_seconds"]
        )
        if self._margin >= self._ttl:
            raise ValueError(
                f"refresh margin {self._margin}s must be shorter than the token TTL "
                f"{self._ttl}s so a refreshed token is usable (§23.5, F4.3)"
            )
        self._clock = clock or (lambda: datetime.now(UTC))
        self._token: MuckRockToken | None = None
        self.mint_count = 0

    @property
    def effective_ttl_seconds(self) -> int:
        """The interval a cached token is actually reused for (< the 5-min lifetime)."""
        return self._ttl - self._margin

    def _mint(self) -> MuckRockToken:
        access = self._source.mint()
        self.mint_count += 1
        token = MuckRockToken(access=access, issued_at=self._clock(), ttl_seconds=self._ttl)
        self._token = token
        return token

    def token(self) -> MuckRockToken:
        """The current token, minting or refreshing it if stale/expired (F4.3)."""
        now = self._clock()
        if self._token is None or self._token.needs_refresh(now, self._margin):
            return self._mint()
        return self._token

    def invalidate(self) -> None:
        """Drop the cached token so the next call re-mints — the refresh-on-401 path."""
        self._token = None

    def authorization_header(self) -> dict[str, str]:
        """The ``Authorization: Bearer <jwt>`` header for a data-endpoint request.

        This is the credential that rides the shared egress seam (SIG-INGEST-011);
        supplying it is authentication, not circumvention (Rule 4 / SIG-INGEST-037).
        """
        return {"Authorization": f"Bearer {self.token().access}"}


# --- candidate identifiers for the parties (SIG-INGEST-034) -------------------


def agency_candidate(raw_agency: str, *, platform: str) -> dict[str, str]:
    """A **candidate** identifier for a records-request agency — never a resolution.

    The connector emits ``(scheme, value)`` and the identity layer (§14.6) resolves
    it (SIG-INGEST-034). A numeric MuckRock/NextRequest agency id routes to a
    platform-scoped scheme; a free-text agency name routes to the surrogate
    ``records.agency_name`` path that feeds P03.2's crosswalk.
    """
    value = raw_agency.strip()
    if value.isdigit():
        return {"scheme": f"{platform}.agency", "value": value}
    return {"scheme": "records.agency_name", "value": value}


# --- the RecordsRequest runtime shape (§11.19) --------------------------------


class InvalidRecordsRequest(Exception):
    """Raised when a RecordsRequest violates the §11.19 vocabulary contract."""


@dataclass(frozen=True)
class RecordsRequest:
    """The runtime shape of a §11.19 ``RecordsRequest`` — the entity SIG cites as provenance.

    Carries the §11.19 predicate surface. ``response_status`` and ``platform`` are
    validated against the frozen ``RecordsResponseStatus``/``RecordsPlatform``
    vocabularies; an out-of-vocabulary value is a hard error rather than a silent
    coercion (SIG-ONTO). ``released_documents`` holds the **EvidenceArtifact ids**
    of the released files (a repeatable ``entity_ref``, §11.19), computed from each
    file's stable source URI so the linkage holds before the bytes are captured.
    The connector emits **candidate** party identifiers, never resolutions
    (SIG-INGEST-034).
    """

    external_id: str
    platform: str
    source_id: str
    requesting_party: str | None = None
    target_agency: str | None = None
    request_text: str | None = None
    filed_date: str | None = None
    response_date: str | None = None
    response_status: str | None = None
    statutory_basis: str | None = None
    released_documents: tuple[str, ...] = ()
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not str(self.external_id).strip():
            raise InvalidRecordsRequest("a RecordsRequest requires an external_id (§11.19)")
        if self.platform not in platforms():
            raise InvalidRecordsRequest(
                f"platform {self.platform!r} is not in the RecordsPlatform vocabulary "
                f"{sorted(platforms())} (§11.19)"
            )
        if self.response_status is not None and self.response_status not in response_statuses():
            raise InvalidRecordsRequest(
                f"response_status {self.response_status!r} is not in the RecordsResponseStatus "
                f"vocabulary {sorted(response_statuses())} (§11.19)"
            )

    @property
    def subject_id(self) -> str:
        """The claim subject id for this request (platform + external id scoped)."""
        return f"records:{self.platform}:{self.external_id}"

    @property
    def is_no_responsive_records(self) -> bool:
        """Whether this request is the positive ``no_responsive_records`` finding (SIG-ONTO-040)."""
        return self.response_status == coverage_trigger_status()

    def predicate_values(self) -> dict[str, Any]:
        """The §11.19 predicate → value map for the set predicates (allowlisted keys only)."""
        candidates: dict[str, Any] = {
            "requesting_party": self.requesting_party,
            "target_agency": self.target_agency,
            "request_text": self.request_text,
            "filed_date": self.filed_date,
            "response_date": self.response_date,
            "response_status": self.response_status,
            "statutory_basis": self.statutory_basis,
            "external_id": self.external_id,
        }
        values = {k: v for k, v in candidates.items() if v is not None}
        if self.released_documents:
            values["released_documents"] = list(self.released_documents)
        return values

    def claim_rows(self) -> list[dict[str, Any]]:
        """The append-only claim rows for this request, confined to the allowlist (P2).

        One ``records_request`` entity row (carrying the whole predicate surface for
        provenance) plus one row per set §11.19 predicate. Every predicate id passes
        :func:`assert_predicate_allowed` (SIG-INGEST-033); ``raw_value`` is preserved
        beside every typed value (P2). Party predicates carry a **candidate**
        identifier, never a resolution (SIG-INGEST-034).
        """
        rows: list[dict[str, Any]] = [
            _stamp(
                {
                    "record_kind": "records_request",
                    "subject_id": self.subject_id,
                    "predicate_id": assert_predicate_allowed("records_request"),
                    "external_id": self.external_id,
                    "platform": self.platform,
                    "raw_value": self.external_id,
                    "predicate_surface": self.predicate_values(),
                    "released_documents": list(self.released_documents),
                },
                source_id=self.source_id,
            )
        ]
        for predicate, value in self.predicate_values().items():
            row: dict[str, Any] = {
                "record_kind": "claim",
                "subject_id": self.subject_id,
                "predicate_id": assert_predicate_allowed(predicate),
                "raw_value": _raw_value_of(value),
                "value": value,
            }
            if predicate in ("requesting_party", "target_agency") and isinstance(value, str):
                # SIG-INGEST-034: emit a candidate identifier, never resolve.
                row["candidate_identifier"] = agency_candidate(value, platform=self.platform)
            rows.append(_stamp(row, source_id=self.source_id))
        return rows


def _raw_value_of(value: Any) -> str:
    if isinstance(value, (list, tuple)):
        return ";".join(str(v) for v in value)
    return str(value)


# --- the no_responsive_records -> CoverageRecord bridge (SIG-ONTO-040) --------


def coverage_record_row(
    request: RecordsRequest,
    *,
    sources_searched: Sequence[str],
) -> dict[str, Any]:
    """The CoverageRecord a ``no_responsive_records`` request writes (SIG-ONTO-040).

    ``no_responsive_records`` is a **positive finding**: an agency stating on the
    record that it holds no responsive documents (e.g. no ALPR contracts) is
    evidence, not a null to discard. It is stored as a coverage record in the
    ``NO_EVIDENCE_FOUND`` state — reusing the canonical §9.5 coverage model
    (:mod:`db.absence`) so it feeds the negative-space surfaces P09.1 builds
    (`coverage_record.absence_kind = 'searched_not_found'`). The record MUST name
    the sources searched (SIG-TIME-011); an empty ``sources_searched`` is rejected.

    Raises :class:`ValueError` if called for a request that is not
    ``no_responsive_records`` — the bridge is only for the positive-finding case.
    """
    if not request.is_no_responsive_records:
        raise ValueError(
            f"coverage_record_row is only for {coverage_trigger_status()!r}; request "
            f"{request.external_id!r} has response_status={request.response_status!r}"
        )
    # render_absence enforces SIG-TIME-011 (NO_EVIDENCE_FOUND must name sources).
    rendering = render_absence(
        AbsenceState.NO_EVIDENCE_FOUND, sources_searched=list(sources_searched)
    )
    subject = request.target_agency or request.subject_id
    return _stamp(
        {
            "record_kind": "coverage_record",
            "subject_id": f"agency:{subject}",
            # The predicate the agency's on-record statement bears on: whether any
            # responsive records exist. absence_kind carries the §9.5 encoding.
            "predicate_id": assert_predicate_allowed("response_status"),
            "absence_kind": coverage_kind_for(AbsenceState.NO_EVIDENCE_FOUND),
            "absence_state": AbsenceState.NO_EVIDENCE_FOUND.value,
            "absence_label": rendering.label,
            "absence_detail": rendering.detail,
            "sources_searched": list(sources_searched),
            "coverage_period": request.response_date,
            "denominator_published": False,
            "raw_value": coverage_trigger_status(),
            "records_request_id": request.external_id,
            "records_request_subject": request.subject_id,
        },
        source_id=request.source_id,
    )


# --- released documents as EvidenceArtifact rows (§10.2, §23.5) ---------------


def evidence_artifact_id(source_uri: str) -> str:
    """The stable EvidenceArtifact id for a released document at ``source_uri``.

    Keyed on the **source URI** (the thing the source published), not the bytes, so
    a RecordsRequest can reference its released documents before they are captured
    and the linkage holds regardless of capture order (§10.2). Deterministic.
    """
    return f"records:artifact:{multihash(source_uri.encode('utf-8'))}"


@dataclass(frozen=True)
class EvidenceArtifactRow:
    """A released-document capture as an EvidenceArtifact row (§10.2, SIG-INGEST records).

    One artifact per released file: its stable id, the source that published it, a
    reference to the content-addressed capture, and the P07.1 classification verdict
    (the parser is *called*, not run here — the layer engines are P07.1). The
    ``records_request_id`` back-links the artifact to its request; the request's
    ``released_documents`` forward-links to :attr:`artifact_id` (§11.19).
    """

    artifact_id: str
    source_id: str
    source_uri: str
    capture_digest: str
    media_type: str
    byte_size: int
    records_request_id: str
    classification: Mapping[str, Any]
    integrity: str = "captured"

    def to_row(self) -> dict[str, Any]:
        return _stamp(
            {
                "record_kind": "evidence_artifact",
                "subject_id": self.artifact_id,
                "predicate_id": assert_predicate_allowed("released_documents"),
                "published_by": self.source_id,
                "source_uri": self.source_uri,
                "capture_digest": self.capture_digest,
                "media_type": self.media_type,
                "byte_size": self.byte_size,
                "integrity": self.integrity,
                "records_request_id": self.records_request_id,
                "classification": dict(self.classification),
                "raw_value": self.source_uri,
            },
            source_id=self.source_id,
        )


def classify_released_document(
    filename: str, data: bytes
) -> ClassificationVerdict | ArchiveClassification:
    """Call the P07.1 parser to classify one released document (§23.5 "calls the parser").

    A records response is routinely a **mixed-format ZIP** (scanned faxes, encrypted
    PDFs, multi-sheet XLSX); those are classified **per member** via
    :func:`parsing.classification.classify_archive`. Everything else is a single
    :func:`parsing.classification.classify`. This connector records the verdict and
    the routed layer; it does NOT run the layer engine (P07.1 owns that,
    SIG-PARSE-001/002).
    """
    verdict = classify(filename, data)
    if verdict.file_format is FileFormat.ZIP:
        return classify_archive(filename, data)
    return verdict


# --- the run record + per-capture quality report (§23.1, SIG-RECON-001 analogue)


@dataclass(frozen=True)
class CaptureQualityReport:
    """The quality report produced **per capture** (§23.5 AC).

    Alongside the ingest run record (:class:`evidence.ingest_run.IngestRun`, on
    ``ctx.run``), every capture carries this report: what was captured, its
    content-addressed digest and size, the P07.1 classification verdict, and how
    many records-request / released-document / coverage rows it yielded. It is the
    per-capture data-quality artifact the phase-gate data-quality checks read.
    """

    source_id: str
    capture_digest: str
    media_type: str
    byte_size: int
    capture_kind: str  # "records_request" | "released_document"
    connector_name: str
    connector_version: str
    vocab_version: str
    records_request_count: int = 0
    released_document_count: int = 0
    coverage_record_count: int = 0
    claim_count: int = 0
    classification: Mapping[str, Any] | None = None

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
            "records_request_count": self.records_request_count,
            "released_document_count": self.released_document_count,
            "coverage_record_count": self.coverage_record_count,
            "claim_count": self.claim_count,
            "classification": dict(self.classification) if self.classification else None,
        }


# --- the connector ------------------------------------------------------------


@register
class RecordsConnector(Connector):
    """The `records` connector: MuckRock/NextRequest/DocumentCloud (§23.5, P07.2).

    Runs on the P04.1 eight-stage framework as a **targeted-lookup** client (never a
    crawler, SIG-INGEST-036/037). ``discover`` returns only explicitly-supplied
    known targets; ``fetch`` egresses through the shared politeness layer, attaching
    a short-lived MuckRock JWT to api_v2 data endpoints (§23.5) and refreshing on a
    401; ``parse``/``extract``/``normalize`` are pure functions of the capture that
    build :class:`RecordsRequest` entities, write the ``no_responsive_records`` ->
    :func:`coverage_record_row` bridge (SIG-ONTO-040), capture each released document
    as an :class:`EvidenceArtifactRow` (calling the P07.1 parser to classify it), and
    emit a per-capture :class:`CaptureQualityReport`. Every claim is confined to the
    predicate allowlist (SIG-INGEST-033).
    """

    name = "records"
    version = "1.0.0"

    def __init__(self, *, token_cache: MuckRockTokenCache | None = None) -> None:
        self._token_cache = token_cache

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — known lookups only, never a crawl (SIG-INGEST-036).

        Targets come from ``ctx.parameters['targets']``; each is asserted to be a
        targeted lookup (:func:`assert_targeted_lookup`). The connector NEVER
        enumerates a listing endpoint itself.
        """
        targets = list(ctx.parameters.get("targets", []))
        for target in targets:
            assert_targeted_lookup(target)
        return targets

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one known target through the shared politeness layer only.

        Connectors hold no HTTP client of their own (SIG-INGEST-011). A MuckRock
        data endpoint (api_v2, refused if api_v1) carries the Bearer JWT; a 401
        (token expired mid-run) triggers exactly one refresh-and-retry (F4.3),
        after which a persistent 401 is a genuine challenge the framework records
        as a disappearance (SIG-INGEST-013) rather than something to defeat.
        """
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        assert_targeted_lookup(target)
        url = str(target["url"])
        if is_muckrock_source(ctx.source.id):
            assert_muckrock_api_v2(url)
        headers = self._authorization(ctx)
        if headers is None:
            return ctx.fetcher.fetch(url)
        try:
            return ctx.fetcher.fetch(url, headers=headers)
        except ChallengeEncountered:
            # A 401 on an authenticated endpoint most likely means the 5-minute JWT
            # expired; refresh once and retry (F4.3). This is not challenge-solving:
            # a second failure propagates to the disappearance layer unchanged.
            assert self._token_cache is not None
            self._token_cache.invalidate()
            return ctx.fetcher.fetch(url, headers=self._token_cache.authorization_header())

    def _authorization(self, ctx: RunContext) -> dict[str, str] | None:
        """The Authorization header for the source, or ``None`` when it needs no auth.

        MuckRock api_v2 requires a Bearer JWT on every data endpoint (§23.5, F4.2):
        a run against it without a configured token cache is a hard error, not a
        silent unauthenticated fetch (which would 401 anyway).
        """
        if not is_muckrock_source(ctx.source.id):
            return None
        cache = self._token_cache or ctx.parameters.get("muckrock_token_cache")
        if not isinstance(cache, MuckRockTokenCache):
            raise WrongMuckRockApiVersion(
                "MuckRock api_v2 data endpoints require a Bearer JWT (§23.5, F4.2); "
                "run the records connector with a MuckRockTokenCache configured."
            )
        self._token_cache = cache
        return cache.authorization_header()

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured bytes — a records-request JSON, or a released document.

        A JSON capture is the request/response payload; anything else is a released
        document, which is classified via the P07.1 parser (never parsed deeply
        here — P07.1 owns the engines). The capture's media type distinguishes them.
        """
        data = ctx.captures.get(capture.digest)
        if _is_json_media(capture.media_type):
            return {"kind": "records_request", "payload": json.loads(data), "capture": capture}
        filename = _filename_from_uri(capture.source_uri)
        verdict = classify_released_document(filename, data)
        return {
            "kind": "released_document",
            "capture": capture,
            "verdict": verdict.to_row(),
            "byte_size": len(data),
        }

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw records with locators, preserving raw values (P2).

        A request payload yields one raw record per request object (a single-id
        lookup returns one; a filtered lookup for a known id may wrap it in
        ``results`` — that is still a targeted lookup, not enumeration). A document
        capture yields one raw released-document record carrying its verdict.
        """
        if parsed["kind"] == "released_document":
            capture = parsed["capture"]
            return [
                {
                    "record_kind": "released_document",
                    "source_uri": capture.source_uri,
                    "capture_digest": capture.digest,
                    "media_type": capture.media_type,
                    "byte_size": parsed["byte_size"],
                    "verdict": parsed["verdict"],
                    "records_request_id": _request_id_hint(capture.source_uri),
                }
            ]
        payload = parsed["payload"]
        if isinstance(payload, Mapping) and "results" in payload:
            objects = payload["results"]
        else:
            objects = [payload]
        out: list[Mapping[str, Any]] = []
        for obj in objects:
            out.append({"record_kind": "records_request", "raw": dict(obj)})
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist.

        A request record becomes a :class:`RecordsRequest` and its claim rows, plus
        a CoverageRecord when it is ``no_responsive_records`` (SIG-ONTO-040); a
        released-document record becomes an :class:`EvidenceArtifactRow`. Every
        capture also emits one :class:`CaptureQualityReport` row.
        """
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            if raw["record_kind"] == "released_document":
                out.extend(self._normalize_document(ctx, raw))
            else:
                out.extend(self._normalize_request(ctx, raw))
        return out

    # -- normalization helpers --
    def _normalize_request(self, ctx: RunContext, raw: Mapping[str, Any]) -> list[dict[str, Any]]:
        request = self._build_request(ctx, raw["raw"])
        rows: list[dict[str, Any]] = list(request.claim_rows())
        coverage_count = 0
        if request.is_no_responsive_records:
            rows.append(
                coverage_record_row(
                    request,
                    sources_searched=self._sources_searched(ctx, request),
                )
            )
            coverage_count = 1
        claim_count = sum(1 for r in rows if r.get("record_kind") == "claim")
        report = CaptureQualityReport(
            source_id=ctx.source.id,
            capture_digest=_digest_of(raw["raw"]),
            media_type="application/json",
            byte_size=len(json.dumps(raw["raw"], sort_keys=True, default=str)),
            capture_kind="records_request",
            connector_name=self.name,
            connector_version=self.version,
            vocab_version=vocab_version(),
            records_request_count=1,
            released_document_count=len(request.released_documents),
            coverage_record_count=coverage_count,
            claim_count=claim_count,
        )
        rows.append(_stamp(report.to_row(), source_id=ctx.source.id))
        return rows

    def _normalize_document(self, ctx: RunContext, raw: Mapping[str, Any]) -> list[dict[str, Any]]:
        artifact = EvidenceArtifactRow(
            artifact_id=evidence_artifact_id(str(raw["source_uri"])),
            source_id=ctx.source.id,
            source_uri=str(raw["source_uri"]),
            capture_digest=str(raw["capture_digest"]),
            media_type=str(raw["media_type"]),
            byte_size=int(raw["byte_size"]),
            records_request_id=str(raw.get("records_request_id") or ""),
            classification=dict(raw["verdict"]),
        )
        report = CaptureQualityReport(
            source_id=ctx.source.id,
            capture_digest=str(raw["capture_digest"]),
            media_type=str(raw["media_type"]),
            byte_size=int(raw["byte_size"]),
            capture_kind="released_document",
            connector_name=self.name,
            connector_version=self.version,
            vocab_version=vocab_version(),
            released_document_count=1,
            classification=dict(raw["verdict"]),
        )
        return [artifact.to_row(), _stamp(report.to_row(), source_id=ctx.source.id)]

    def _build_request(self, ctx: RunContext, raw: Mapping[str, Any]) -> RecordsRequest:
        """Map a raw request object onto the §11.19 runtime shape.

        Field names follow the MuckRock api_v2 / NextRequest shapes but fall back
        across the common aliases; the released documents' source URIs are turned
        into stable EvidenceArtifact ids so the request links to them before they
        are captured (§11.19 ``released_documents``).
        """
        platform = str(raw.get("platform") or _platform_for_source(ctx.source.id))
        doc_urls = _released_document_urls(raw)
        return RecordsRequest(
            external_id=str(raw.get("external_id") or raw.get("id") or raw.get("request_id") or ""),
            platform=platform,
            source_id=ctx.source.id,
            requesting_party=_opt_str(raw.get("requesting_party") or raw.get("user")),
            target_agency=_opt_str(raw.get("target_agency") or raw.get("agency")),
            request_text=_opt_str(raw.get("request_text") or raw.get("title") or raw.get("text")),
            filed_date=_opt_str(raw.get("filed_date") or raw.get("date_submitted")),
            response_date=_opt_str(raw.get("response_date") or raw.get("datetime_done")),
            response_status=_opt_str(raw.get("response_status") or raw.get("status")),
            statutory_basis=_opt_str(raw.get("statutory_basis")),
            released_documents=tuple(evidence_artifact_id(u) for u in doc_urls),
            raw=dict(raw),
        )

    @staticmethod
    def _sources_searched(ctx: RunContext, request: RecordsRequest) -> list[str]:
        """The sources a ``no_responsive_records`` coverage record names (SIG-TIME-011).

        At minimum the platform the request was filed on and the source registry id;
        a caller may widen it via ``ctx.parameters['sources_searched']``.
        """
        extra = list(ctx.parameters.get("sources_searched", []))
        agency = request.target_agency or request.external_id
        named = [f"{request.platform}:{agency}", ctx.source.id]
        seen: list[str] = []
        for s in [*named, *extra]:
            if s and s not in seen:
                seen.append(s)
        return seen

    # -- link + load --
    # link() is inherited (identity): SIG-INGEST-034 — the connector emits candidate
    # identifiers and NEVER resolves entities itself; resolution is P03.2/P05.1.

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only).

        Adds the generated ``claim_id`` + transaction time (the two columns the
        reproducibility fingerprint excludes, SIG-INGEST-003) to the claim/entity
        rows. Coverage, evidence-artifact, and quality-report rows are records of
        their own kind and pass through unchanged.
        """
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


def _stamp(row: dict[str, Any], *, source_id: str) -> dict[str, Any]:
    """Stamp a row with its source id and the connector vocabulary version (§20).

    The records channel spans several REFERENCE-posture sources whose per-document
    rights vary; the export compartment is decided per source by the licence gate
    (SIG-LIC-009a), so — unlike osm/atlas — the connector does not pin a single
    compartment here. It records the source id and vocabulary version every row is
    interpretable against.
    """
    row.setdefault("source_id", source_id)
    row.setdefault("vocab_version", vocab_version())
    return row


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 claim/entity row needs.

    Mirrors the framework's load contract: ``claim_id`` and ``sys_period`` are the
    two non-deterministic columns the reproducibility fingerprint excludes
    (SIG-INGEST-003), so replay is byte-identical modulo exactly these. Only the
    claim/entity rows get an identity + transaction time; coverage records, evidence
    artifacts, and quality reports keep their own keys.
    """
    stamped_kinds = {"records_request", "claim"}
    out: list[dict[str, Any]] = []
    for claim in claims:
        if claim.get("record_kind") in stamped_kinds:
            out.append(
                {
                    **claim,
                    "claim_id": str(uuid4()),
                    "sys_period": f"[{datetime.now(UTC).isoformat()},)",
                }
            )
        else:
            out.append(dict(claim))
    return out


def _released_document_urls(raw: Mapping[str, Any]) -> list[str]:
    """The released documents' source URIs from a raw request object.

    Tolerates the common shapes: a ``released_documents``/``files``/``documents``
    list of URLs or of objects carrying a ``url``/``ffile``/``file`` field.
    """
    for key in ("released_documents", "files", "documents"):
        value = raw.get(key)
        if not value:
            continue
        urls: list[str] = []
        for item in value:
            if isinstance(item, str):
                urls.append(item)
            elif isinstance(item, Mapping):
                url = item.get("url") or item.get("ffile") or item.get("file") or item.get("href")
                if url:
                    urls.append(str(url))
        if urls:
            return urls
    return []


def _platform_for_source(source_id: str) -> str:
    """The RecordsPlatform for a registry source id (falls back to ``portal``)."""
    for platform, sid in source_ids().items():
        if sid == source_id and platform in platforms():
            return platform
    return "portal"


def _digest_of(payload: Any) -> str:
    return multihash(json.dumps(payload, sort_keys=True, default=str).encode("utf-8"))


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _is_json_media(media_type: str) -> bool:
    # Only a JSON content type is the request/response payload; everything else —
    # including text/plain — is a released document routed to the P07.1 parser.
    return "json" in media_type.lower()


def _filename_from_uri(uri: str) -> str:
    tail = uri.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return tail or "document"


def _request_id_hint(source_uri: str) -> str:
    """A best-effort request-id back-link for a standalone document capture.

    When a released document is fetched as its own target its request id may be
    carried in the target; absent that, the artifact still links forward from the
    request's ``released_documents`` by stable artifact id, so this is a hint only.
    """
    return ""


__all__ = [
    "CaptureQualityReport",
    "CrawlAttempted",
    "EvidenceArtifactRow",
    "InvalidRecordsRequest",
    "MuckRockToken",
    "MuckRockTokenCache",
    "PredicateNotAllowed",
    "RecordsConnector",
    "RecordsRequest",
    "TokenSource",
    "WrongMuckRockApiVersion",
    "agency_candidate",
    "assert_muckrock_api_v2",
    "assert_predicate_allowed",
    "assert_targeted_lookup",
    "classify_released_document",
    "coverage_record_row",
    "coverage_trigger_status",
    "evidence_artifact_id",
    "forbidden_predicate_genres",
    "is_muckrock_source",
    "is_predicate_allowed",
    "load_claims_for_l1",
    "muckrock_config",
    "muckrock_endpoint",
    "platforms",
    "predicate_allowlist",
    "response_statuses",
    "source_ids",
    "vocab",
    "vocab_version",
]
