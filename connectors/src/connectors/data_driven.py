# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `data_driven` connector — EFF/MuckRock Data Driven releases (§23.9, P21.8).

The first-class ingestion of EFF/MuckRock's **Data Driven** releases — the only
substantial public evidence base for pre-Flock, non-Flock ALPR network behaviour
(SIG-INGEST-043). A source adapter on the P04.1 eight-stage framework
(:mod:`connectors.stages`), of deliberately different shape from ``atlas``: the
unit of ingestion is a **versioned release manifest**, and every claim it writes
is a **per-agency aggregate** that is historical, not current.

This module owns the things §23.9 assigns to P21.8, none of which the framework
provides:

* **The release-version model** (:class:`ReleaseManifest`, SIG-INGEST-043b): each
  release is a versioned artifact addressed by a content digest and stamped with
  its retrieval date. The connector targets the **file artifacts directly**; the
  article URL is recorded as *context*, never as the source (the outline's article
  URL is a dead end with no data links). Every claim carries the release version +
  digest + retrieval date, so a **versioned re-ingest yields a new dated claim
  set and never overwrites the prior one** (SIG-INGEST-043d / SIG-INGEST-017).
* **Per-agency aggregate rows ONLY** (:func:`assert_aggregate_only`,
  SIG-INGEST-043, RISK-P0-08, RISK-P21-15): a per-search, per-plate, per-person,
  or per-edge sharing-list column is **refused at the ingest boundary** — it would
  enable the de-pseudonymisation join §43.2a forbids and manufacture the
  unexplained edge the defining standard forbids. This is a hard schema gate.
* **Sharing DEGREE, never the edge list** (SIG-INGEST-043c): all 463 source-
  document links resolve to a host that blocks automated access, so SIG obtains
  how many partners an agency had (``sharing_partner_degree``) but never who they
  were. Degree supports "this agency shared with 851 others"; it does not support
  drawing any specific edge.
* **Per-column retention windows in incommensurable units** (SIG-INGEST-043d): the
  corpus carries vendor-specific retention-window columns in different units (a
  30-day column beside another vendor's figures). The connector preserves the
  **window definition per column** and never normalizes the values together —
  direct, dated evidence for the incommensurable-counts problem (§29.1).
* **Agency crosswalk through the P03.2 cascade** (:meth:`DataDrivenConnector.link`,
  SIG-INGEST-043c/§14.6): each agency aggregate is resolved against known SIG
  identities via :func:`resolution.cascade.resolve`; a match is labelled with its
  cascade **tier** (defining standard §3.1 — a match names why it fired). The
  connector emits **candidate** identifiers and never mints identity itself.
* **Records-request linkage** (:func:`records_request_link`, SIG-INGEST-044): where
  a release documents the public-records request that produced an agency's data,
  the aggregate is linked back to that :class:`~connectors.records.RecordsRequest`
  (the entity SIG cites as provenance) — the release is the *result* of a request.

Every claim from this source is **historical** and carries ``observed_at``,
subject to normal currency decay (§28.3): a `configured_sharing_partner_set`
(FAST, 4-month half-life) figure is `C4 HISTORICAL` and cannot answer a
present-tense question. The connector NEVER writes a current-state claim
(SIG-INGEST-043). Rows are append-only and carry full provenance.
"""

from __future__ import annotations

import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from evidence.digest import multihash
from resolution.cascade import Candidate, CascadeContext, MatchResult, resolve
from resolution.identity import Identifier
from resolution.ori import is_valid_ori

from ._data import load_table
from .records import RecordsRequest
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

#: The registry source this connector runs against (§22.6 D; MIRROR candidate,
#: rights UNDETERMINED until reviewed — SIG-INGEST-028).
DATA_DRIVEN_SOURCE_ID = "eff_data_driven"

#: The candidate-identifier schemes an agency id routes onto (SIG-INGEST-034).
ORI_SCHEME = "us.fbi.ori"
DATA_DRIVEN_AGENCY_SCHEME = "data_driven.agency_name"

#: The organisation class the connector keys agency aggregates as, so the P03.2
#: cascade compares like with like (a law-enforcement agency).
AGENCY_CLASS = "law_enforcement_agency"

_DETECTOR_VERSION = "connectors.data_driven/1"


# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned Data Driven connector vocabulary (``data/data_driven_vocab.toml``)."""
    return load_table("data_driven_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def source_id() -> str:
    """The registry source id the connector runs against (§22.6 D)."""
    return str(vocab()["source_id"])


def temporal_class() -> str:
    """The temporal class every claim carries — always ``historical`` (SIG-INGEST-043)."""
    return str(vocab()["temporal_class"])


# --- the predicate allowlist (SIG-INGEST-033) ---------------------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§23.9, SIG-INGEST-033)."""
    return frozenset(vocab()["predicate_allowlist"])


def is_predicate_allowed(predicate: str) -> bool:
    """Whether ``predicate`` is in the connector's allowlist (SIG-INGEST-033)."""
    return predicate in predicate_allowlist()


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`."""
    if not is_predicate_allowed(predicate):
        raise PredicateNotAllowed(
            f"the data_driven connector may write only {sorted(predicate_allowlist())} "
            f"(§23.9, SIG-INGEST-033); {predicate!r} is outside the allowlist — "
            "per-search, per-plate, per-person and per-edge rows are refused."
        )
    return predicate


# --- the aggregate-only guard (SIG-INGEST-043, RISK-P0-08, RISK-P21-15) --------


class PerSearchColumnError(Exception):
    """Raised when a Data Driven release carries a non-aggregate (per-search/edge) column.

    Data Driven is per-agency AGGREGATE rows ONLY (§23.9, §18.1). A per-search,
    per-plate, per-person/officer, or per-edge sharing-list column would enable the
    de-pseudonymisation join §43.2a forbids and manufacture an unexplained network
    edge — so it is refused at the ingest boundary, naming the offending column so
    the P0 defect is auditable (RISK-P0-08, RISK-P21-15).
    """


def forbidden_column_tokens() -> tuple[str, ...]:
    """The column-name tokens that mark a non-aggregate row (§23.9, RISK-P21-15)."""
    return tuple(vocab()["forbidden_column_tokens"])


def _offending_token(name: str) -> str | None:
    lowered = str(name).strip().lower()
    for token in forbidden_column_tokens():
        if token in lowered:
            return token
    return None


def assert_aggregate_only(columns: Iterable[str]) -> None:
    """Reject any per-search / per-person / per-edge column (SIG-INGEST-043, RISK-P21-15).

    The hard mechanical form of the Part VIII §0.7 guarantee: Data Driven is
    ingested as per-agency aggregates ONLY. Any column whose name carries a
    forbidden token (a per-search/per-plate/per-person or a sharing-edge/partner
    list) raises :class:`PerSearchColumnError` before a single claim is built.
    """
    for name in columns:
        token = _offending_token(name)
        if token is not None:
            raise PerSearchColumnError(
                f"Data Driven column {name!r} matches the forbidden non-aggregate token "
                f"{token!r}; the connector ingests per-agency AGGREGATE rows ONLY — "
                "per-search/per-plate/per-person and per-edge sharing lists are never stored "
                "(§23.9, §18.1, RISK-P0-08, RISK-P21-15)."
            )


# --- agency-id keying + surrogate routing (SIG-INGEST-034) --------------------


@dataclass(frozen=True)
class AgencyIdentity:
    """A **candidate** identifier for a Data Driven agency — never a resolution.

    An ORI-shaped value routes to the canonical ``us.fbi.ori`` scheme; everything
    else routes to the ``data_driven.agency_name`` surrogate path that feeds
    P03.2's crosswalk. ``route`` records which path was taken (SIG-INGEST-034).
    """

    scheme: str
    value: str
    route: str  # "canonical" | "surrogate"

    def as_identifier(self) -> dict[str, str]:
        return {"scheme": self.scheme, "value": self.value}


def agency_identity(agency_id: str) -> AgencyIdentity:
    """Route one Data Driven agency identifier to a candidate identifier (SIG-INGEST-034)."""
    value = agency_id.strip()
    if is_valid_ori(value):
        return AgencyIdentity(scheme=ORI_SCHEME, value=value, route="canonical")
    return AgencyIdentity(scheme=DATA_DRIVEN_AGENCY_SCHEME, value=value, route="surrogate")


# --- the release manifest (SIG-INGEST-043b provenance) ------------------------


class InvalidRelease(Exception):
    """Raised when a Data Driven release manifest violates the §23.9 contract."""


@dataclass(frozen=True)
class ReleaseManifest:
    """One versioned Data Driven release — the unit of ingestion (§23.9, SIG-INGEST-043b).

    Each release is addressed by a **content digest** and stamped with its
    **retrieval date**; the connector targets the file artifacts directly and
    records the article URL as *context* (a dead end with no data links, 043b).
    A hard limitation is recorded with every ingest: all source-document links
    resolve to a host that blocks automated access, so SIG obtains sharing degree
    but never the edge list (043c).
    """

    release_id: str
    version: str
    retrieved_date: str
    observed_at: str
    data_file_urls: tuple[str, ...]
    article_url: str = ""
    source_documents_block_automation: bool = True
    source_document_link_count: int = 0
    retention_window_columns: Mapping[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if not str(self.version).strip():
            raise InvalidRelease("a Data Driven release requires a version (SIG-INGEST-043b)")
        if not self.data_file_urls:
            raise InvalidRelease(
                "a Data Driven release must target the file artifacts directly; the "
                "article URL is a dead end with no data links (SIG-INGEST-043b)."
            )

    @property
    def digest(self) -> str:
        """The content digest that addresses this release version (SIG-INGEST-043b)."""
        payload = {
            "release_id": self.release_id,
            "version": self.version,
            "data_file_urls": list(self.data_file_urls),
        }
        return multihash(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8"))

    def provenance(self) -> dict[str, Any]:
        """The per-release provenance stamped onto every claim (P1–P3, SIG-INGEST-043b)."""
        return {
            "release_id": self.release_id,
            "release_version": self.version,
            "release_digest": self.digest,
            "retrieved_date": self.retrieved_date,
            "observed_at": self.observed_at,  # historical (SIG-INGEST-043/044)
            "temporal_class": temporal_class(),
            "article_url_is_context_only": True,  # SIG-INGEST-043b
            "source_documents_block_automation": self.source_documents_block_automation,
            "source_document_link_count": self.source_document_link_count,
        }


def parse_release(data: bytes) -> dict[str, Any]:
    """Parse a Data Driven release manifest JSON (pure function of the capture)."""
    payload = json.loads(data.decode("utf-8"))
    if "release" not in payload:
        raise InvalidRelease("a Data Driven capture must carry a 'release' object (§23.9)")
    return payload


def _manifest_from(release: Mapping[str, Any]) -> ReleaseManifest:
    return ReleaseManifest(
        release_id=str(release.get("release_id", DATA_DRIVEN_SOURCE_ID)),
        version=str(release["version"]),
        retrieved_date=str(release["retrieved_date"]),
        observed_at=str(release.get("observed_at", release["version"])),
        data_file_urls=tuple(str(u) for u in release.get("data_file_urls", [])),
        article_url=str(release.get("article_url", "")),
        source_documents_block_automation=bool(
            release.get("source_documents_block_automation", True)
        ),
        source_document_link_count=int(release.get("source_document_link_count", 0)),
        retention_window_columns=dict(release.get("retention_window_columns", {})),
    )


# --- records-request linkage (SIG-INGEST-044) ---------------------------------


def records_request_link(
    agency_subject_id: str,
    request: Mapping[str, Any],
) -> dict[str, Any]:
    """Link an agency aggregate to the records request that produced it (SIG-INGEST-044).

    The Data Driven release is the *result* of MuckRock public-records requests, so
    where a release documents the request behind an agency's data the aggregate is
    linked back to the :class:`~connectors.records.RecordsRequest` (the §11.19
    entity SIG cites as provenance) by its stable subject id — the seam into
    ``tasks.records_request`` / the records channel. No request text or party is
    fabricated here; only the linkage the release itself documents.
    """
    rr = RecordsRequest(
        external_id=str(request["external_id"]),
        platform=str(request.get("platform", "muckrock")),
        source_id=DATA_DRIVEN_SOURCE_ID,
        target_agency=request.get("target_agency"),
    )
    return {
        "record_kind": "records_request_link",
        "subject_id": agency_subject_id,
        "records_request_subject": rr.subject_id,
        "records_request_external_id": rr.external_id,
        "records_request_platform": rr.platform,
        "target_agency": rr.target_agency,
        "raw_value": rr.external_id,
    }


# --- the per-agency aggregate (SIG-INGEST-043/043a/043c/043d) ------------------


@dataclass(frozen=True)
class AgencyAggregate:
    """One agency's per-agency AGGREGATE row (§23.9, SIG-INGEST-043a). Never per-search."""

    agency_id: str
    agency_name: str
    state: str | None
    vendor: str | None
    detections: int | None
    hits: int | None
    sharing_partner_degree: int | None
    pooled_lookup_participant: bool
    retention: Mapping[str, Any] | None
    records_request: Mapping[str, Any] | None

    @property
    def subject_id(self) -> str:
        return f"data_driven:agency:{self.agency_id}"

    @property
    def non_hit_proportion(self) -> float | None:
        """1 − hits/detections — the corpus's key structural number (SIG-INGEST-043a)."""
        if self.detections in (None, 0) or self.hits is None:
            return None
        return 1.0 - (self.hits / self.detections)


def _aggregate_from(row: Mapping[str, Any]) -> AgencyAggregate:
    return AgencyAggregate(
        agency_id=str(row.get("agency_id") or row.get("agency_name") or ""),
        agency_name=str(row.get("agency_name", "")),
        state=(str(row["state"]) if row.get("state") else None),
        vendor=(str(row["vendor"]) if row.get("vendor") else None),
        detections=(int(row["detections"]) if row.get("detections") is not None else None),
        hits=(int(row["hits"]) if row.get("hits") is not None else None),
        sharing_partner_degree=(
            int(row["sharing_partner_degree"])
            if row.get("sharing_partner_degree") is not None
            else None
        ),
        pooled_lookup_participant=bool(row.get("pooled_lookup_participant", False)),
        retention=(dict(row["retention"]) if row.get("retention") else None),
        records_request=(dict(row["records_request"]) if row.get("records_request") else None),
    )


# --- the connector ------------------------------------------------------------


@register
class DataDrivenConnector(Connector):
    """The `data_driven` connector: EFF/MuckRock Data Driven releases (§23.9, P21.8).

    Runs on the P04.1 eight-stage framework. ``discover``/``fetch`` acquire a
    versioned release manifest through the shared politeness layer;
    ``parse``/``extract``/``normalize`` are pure functions of the capture that
    build per-agency AGGREGATE claims (never per-search), preserve each vendor's
    retention window per column, record sharing DEGREE (never the edge list), and
    stamp every claim with the release version + digest + retrieval date so a
    versioned re-ingest appends new dated claims and never overwrites. ``link``
    crosswalks each agency to a known SIG identity through the P03.2 cascade,
    labelling a match with its tier. Every claim is confined to the predicate
    allowlist and is historical (SIG-INGEST-043/044).
    """

    name = "data_driven"
    version = "1.0.0"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets — the release file artifacts (SIG-INGEST-043b)."""
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain the release manifest bytes through the shared politeness layer only."""
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> dict[str, Any]:
        """Structure the captured release manifest JSON."""
        return parse_release(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        """Raw per-agency aggregate records with the release provenance, preserving raw values.

        The aggregate-only guard runs HERE, at the ingest boundary: a per-search /
        per-person / per-edge column refuses the whole release before any claim is
        built (SIG-INGEST-043, RISK-P21-15).
        """
        release = parsed["release"]
        manifest = _manifest_from(release)
        agencies = list(release.get("agencies", []))
        # SIG-INGEST-043 / RISK-P21-15: reject any non-aggregate column across the
        # release's declared column set AND every agency row's own keys.
        declared_columns = list(release.get("columns", []))
        observed_columns: set[str] = set(declared_columns)
        for row in agencies:
            observed_columns.update(row.keys())
        assert_aggregate_only(sorted(observed_columns))
        out: list[Mapping[str, Any]] = []
        for row in agencies:
            out.append(
                {
                    "record_kind": "data_driven_agency",
                    "raw": dict(row),
                    "provenance": manifest.provenance(),
                    "retention_window_columns": dict(manifest.retention_window_columns or {}),
                }
            )
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed per-agency aggregate claim rows beside preserved raw values (P2)."""
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            out.extend(self._agency_rows(raw))
        return out

    # -- normalization helpers --
    def _agency_rows(self, raw: Mapping[str, Any]) -> list[dict[str, Any]]:
        agg = _aggregate_from(raw["raw"])
        prov = dict(raw["provenance"])
        retention_columns = dict(raw.get("retention_window_columns", {}))
        identity = agency_identity(agg.agency_id)
        base = {
            "source_id": DATA_DRIVEN_SOURCE_ID,
            "subject_id": agg.subject_id,
            "subject_kind": "agency",
            "granularity": "agency_aggregate",  # §23.9: per-agency aggregate ONLY
            "agency_identifier": identity.as_identifier(),
            "identity_route": identity.route,
            "raw_agency": agg.agency_name,
            "vendor": agg.vendor,
            "state": agg.state,
            **prov,
        }
        rows: list[dict[str, Any]] = []

        # deployment_exists — a non-Flock vendor deployment (historical).
        if agg.vendor:
            rows.append(self._claim(base, "deployment_exists", value=True, raw_value=agg.vendor))
        # aggregate scan/hit-rate observations (SIG-INGEST-043a).
        if agg.detections is not None:
            rows.append(
                self._claim(
                    base,
                    "scan_volume_observed",
                    value=agg.detections,
                    raw_value=str(agg.detections),
                )
            )
        if agg.hits is not None:
            rows.append(
                self._claim(base, "hit_volume_observed", value=agg.hits, raw_value=str(agg.hits))
            )
        non_hit = agg.non_hit_proportion
        if non_hit is not None:
            rows.append(
                self._claim(
                    base,
                    "non_hit_proportion_observed",
                    value=non_hit,
                    raw_value=f"{agg.detections} detections / {agg.hits} hits",
                )
            )
        # SIG-INGEST-043c: sharing DEGREE only — never an edge list.
        if agg.sharing_partner_degree is not None:
            row = self._claim(
                base,
                "sharing_partner_degree",
                value=agg.sharing_partner_degree,
                raw_value=str(agg.sharing_partner_degree),
            )
            row["degree_only_no_edge_list"] = True  # SIG-INGEST-043c
            rows.append(row)
        # configured_access to a vendor-operated pooled lookup service.
        if agg.pooled_lookup_participant:
            rows.append(
                self._claim(
                    base,
                    "pooled_lookup_participation",
                    value=True,
                    raw_value="pooled_lookup_participant",
                )
            )
        # SIG-INGEST-043d: per-column retention window, preserved with its unit,
        # NEVER normalized across vendors' incommensurable units.
        if agg.retention:
            column = str(agg.retention.get("column", ""))
            window_def = retention_columns.get(column, {})
            row = self._claim(
                base,
                "retention_window_observed",
                value=agg.retention.get("value"),
                raw_value=f"{agg.retention.get('value')} {agg.retention.get('unit')}",
            )
            row["retention_column"] = column
            row["retention_unit"] = agg.retention.get("unit")
            row["retention_window_definition"] = dict(window_def)
            row["incommensurable_units_preserved"] = True  # SIG-INGEST-043d
            rows.append(row)
        # SIG-INGEST-044: link the aggregate to the records request that produced it.
        if agg.records_request:
            link = records_request_link(agg.subject_id, agg.records_request)
            link.update(
                {
                    k: base[k]
                    for k in ("source_id", "release_version", "release_digest", "retrieved_date")
                }
            )
            rows.append(link)
        return rows

    @staticmethod
    def _claim(
        base: Mapping[str, Any], predicate: str, *, value: Any, raw_value: str
    ) -> dict[str, Any]:
        return {
            "record_kind": "claim",
            **base,
            "predicate_id": assert_predicate_allowed(predicate),
            "value": value,
            "raw_value": raw_value,
        }

    # -- link (crosswalk through the P03.2 cascade, SIG-INGEST-043c/§14.6) --
    def link(self, ctx: RunContext, normalized: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Crosswalk each agency to a known SIG identity through the P03.2 cascade.

        Known SIG identities are supplied on ``ctx.parameters['sig_identities']``
        (the seam the composed stack fills from the identity layer). For each
        agency the connector builds a :class:`resolution.cascade.Candidate` and
        runs :func:`resolution.cascade.resolve`; the first deterministic tier that
        fires stamps ``resolved_entity_id`` + ``match_tier`` + ``tier_label`` +
        ``match_evidence`` onto every row for that agency (defining standard §3.1 —
        a match names why it fired). With no known identities the stage is identity
        (the connector never mints identity itself, SIG-INGEST-034).
        """
        identities = _candidates_from(ctx.parameters.get("sig_identities", []))
        if not identities:
            return normalized
        cascade_ctx = CascadeContext.from_data()
        # Resolve one match per distinct agency subject, then stamp all its rows.
        resolved: dict[str, MatchResult] = {}
        for row in normalized:
            subject = str(row.get("subject_id", ""))
            if not subject or subject in resolved:
                continue
            candidate = _agency_candidate(row)
            if candidate is None:
                continue
            match = _first_match(candidate, identities, cascade_ctx)
            if match is not None:
                resolved[subject] = match
        for row in normalized:
            match = resolved.get(str(row.get("subject_id", "")))
            if match is not None:
                row["resolved_entity_id"] = match.right
                row["match_tier"] = match.match_tier
                row["tier_label"] = match.tier_label
                row["match_evidence"] = match.match_evidence
        return normalized

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only)."""
        return load_claims_for_l1(linked)


# --- crosswalk helpers --------------------------------------------------------


def _agency_candidate(row: Mapping[str, Any]) -> Candidate | None:
    """Build a resolution Candidate for an agency claim row (P03.2)."""
    name = str(row.get("raw_agency", "")).strip()
    if not name:
        return None
    ident = row.get("agency_identifier") or {}
    identifiers: frozenset[Identifier] = frozenset()
    scheme = str(ident.get("scheme", ""))
    value = str(ident.get("value", ""))
    if scheme == ORI_SCHEME and value:
        identifiers = frozenset({Identifier(scheme=ORI_SCHEME, value=value)})
    return Candidate(
        entity_id=str(row.get("subject_id")),
        organization_class=AGENCY_CLASS,
        name=name,
        state=(str(row["state"]) if row.get("state") else None),
        identifiers=identifiers,
    )


def _candidates_from(specs: Iterable[Mapping[str, Any]]) -> list[Candidate]:
    """Build known-SIG-identity Candidates from parameter specs (the crosswalk seam)."""
    out: list[Candidate] = []
    for spec in specs:
        identifiers = frozenset(
            Identifier(scheme=str(i["scheme"]), value=str(i["value"]))
            for i in spec.get("identifiers", [])
        )
        out.append(
            Candidate(
                entity_id=str(spec["entity_id"]),
                organization_class=str(spec.get("organization_class", AGENCY_CLASS)),
                name=str(spec.get("name", "")),
                state=(str(spec["state"]) if spec.get("state") else None),
                identifiers=identifiers,
            )
        )
    return out


def _first_match(
    candidate: Candidate, identities: Sequence[Candidate], ctx: CascadeContext
) -> MatchResult | None:
    for known in identities:
        if known.entity_id == candidate.entity_id:
            continue
        match = resolve(candidate, known, context=ctx)
        if match is not None:
            return match
    return None


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 row needs (SIG-INGEST-003)."""
    out: list[dict[str, Any]] = []
    for claim in claims:
        out.append(
            {
                **claim,
                "claim_id": str(uuid4()),
                "sys_period": f"[{datetime.now(UTC).isoformat()},)",
            }
        )
    return out


__all__ = [
    "AGENCY_CLASS",
    "DATA_DRIVEN_AGENCY_SCHEME",
    "DATA_DRIVEN_SOURCE_ID",
    "ORI_SCHEME",
    "AgencyAggregate",
    "AgencyIdentity",
    "DataDrivenConnector",
    "InvalidRelease",
    "PerSearchColumnError",
    "PredicateNotAllowed",
    "ReleaseManifest",
    "agency_identity",
    "assert_aggregate_only",
    "assert_predicate_allowed",
    "forbidden_column_tokens",
    "is_predicate_allowed",
    "load_claims_for_l1",
    "parse_release",
    "predicate_allowlist",
    "records_request_link",
    "source_id",
    "temporal_class",
    "vocab",
    "vocab_version",
]
