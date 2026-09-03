# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The `atlas` connector — agency adoption from the EFF Atlas of Surveillance (§23.3, P04.3).

The second real source adapter on the P04.1 eight-stage framework
(:mod:`connectors.stages`), of deliberately different shape from ``osm``. It
ingests the EFF Atlas of Surveillance agency-adoption feed and writes a single
predicate — ``deployment_exists`` — at **family-level** technology granularity,
landing in the CC-BY-4.0 SIG graph compartment (§42.2). The Atlas is a
MIRROR-posture CC-BY source with a third-party caveat (SC-09).

This module owns five things §23.3 assigns to P04.3, none of which the framework
provides:

* **Atlas category → SIG technology family** (data, in ``data/atlas_vocab.toml``):
  seeded from the authoritative external crosswalk (``eff_atlas`` in
  ``ontology/vocab/crosswalks.yaml``) and rolled to its family level, carrying the
  SKOS mapping relation + ``lossy`` flag as provenance (SIG-STORE-040). A category
  outside the vocabulary is recorded as an unmapped category + a research task,
  never guessed.
* **Agency-id keying with surrogate routing** (SIG-INGEST-034): the connector keys
  on the Atlas agency identifier and emits a *candidate* identifier — an ORI-shaped
  value routes to the canonical ``us.fbi.ori`` scheme, everything else routes to
  the ``atlas.agency_name`` **surrogate path** that feeds P03.2's crosswalk. The
  connector NEVER resolves entities itself.
* **A predicate allowlist enforced as a hard schema gate** (SIG-INGEST-033): the
  only claim predicate is ``deployment_exists``. Device counts, coordinates,
  configuration and current status are refused — writing one is a schema error.
* **Evidence-genre preservation** (§23.3, OL-2D-AT-02): the Atlas's methodology is
  nine distinct evidence genres. Where the upstream records which component
  produced a row the connector carries it; where it does not, the connector records
  the **granularity loss** rather than assign a tier by guess.
* **Category retirement, not a world change** (SIG-ONTO-059): a row tagged with a
  retired Atlas category (the March-2024 Ring/Neighbors retirement) is recorded as
  a **category retirement** — a vocabulary event — never a ``deployment_exists`` and
  never the world event of a deployment ending. Every row carries the Atlas
  vocabulary version, so a later disappearance is read against the taxonomy that
  produced it, never as a program ending.

Rows are append-only and carry full provenance (Atlas attribution, vocabulary
version, agency candidate identifier, upstream links); the connector never marks a
row authoritative or "current", so later evidence supersedes or temporally
qualifies an Atlas row through the resolver (P08.x), never by overwrite.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import Any
from uuid import uuid4

from resolution.ori import is_valid_ori

from ._data import load_table
from .stages import CaptureRef, Connector, FetchResult, RunContext, register

#: The registry source this connector runs against (§22.6 D; MIRROR + CC-BY-4.0).
ATLAS_SOURCE_ID = "eff_atlas_of_surveillance"

#: The export compartment Atlas-derived claims land in: the CC-BY-4.0 SIG graph
#: (policy/data/licenses.toml → compartments.sig_graph, §42.2).
CC_BY_LICENSE = "CC-BY-4.0"
SIG_GRAPH_COMPARTMENT = "sig_graph"

#: The single claim predicate this connector may write, at family granularity
#: (§23.3). Enforced by :func:`assert_predicate_allowed` (SIG-INGEST-033).
DEPLOYMENT_EXISTS_PREDICATE = "deployment_exists"

#: The predicate a *category retirement* is recorded under — a **vocabulary event**
#: (SIG-ONTO-059), kept strictly distinct from the world event below.
CATEGORY_RETIRED_PREDICATE = "atlas_category_retired"
#: The predicate a *world* change (a deployment ending) would use. The Atlas
#: connector NEVER emits it from a category retirement; it exists only to name the
#: distinction the spec draws (SIG-ONTO-059).
DEPLOYMENT_ENDED_PREDICATE = "deployment_ended"

#: The candidate-identifier schemes the connector routes an agency id onto
#: (SIG-INGEST-034, §11 identifier systems).
ORI_SCHEME = "us.fbi.ori"
ATLAS_AGENCY_SCHEME = "atlas.agency_name"

#: Research-task type for an Atlas category outside the versioned vocabulary —
#: mirrors the osm connector's unmapped-tag task shape (SIG-INGEST-045 analogue).
UNMAPPED_CATEGORY_TASK_TYPE = "unmapped_atlas_category"

_DETECTOR_VERSION = "connectors.atlas/1"


# --- the versioned vocabulary (data, not code — §20, SIG-ENG-001) -------------


@cache
def vocab() -> dict[str, Any]:
    """The versioned Atlas category→claim vocabulary (``data/atlas_vocab.toml``)."""
    return load_table("atlas_vocab")


def vocab_version() -> str:
    """The connector vocabulary version stamped onto every run (§20)."""
    return str(vocab()["vocab_version"])


def atlas_version() -> str:
    """The observed **Atlas** taxonomy version, recorded on every row (SIG-ONTO-059)."""
    return str(vocab()["atlas_version"])


def _columns() -> Mapping[str, Any]:
    return vocab()["columns"]


# --- the predicate allowlist (SIG-INGEST-033) ---------------------------------


class PredicateNotAllowed(Exception):
    """A schema error: the connector tried to write outside its predicate allowlist."""


def predicate_allowlist() -> frozenset[str]:
    """The predicates this connector may write (§23.3, SIG-INGEST-033)."""
    return frozenset(vocab()["predicate_allowlist"])


def is_predicate_allowed(predicate: str) -> bool:
    """Whether ``predicate`` is in the connector's allowlist (SIG-INGEST-033)."""
    return predicate in predicate_allowlist()


def forbidden_predicate_genres() -> tuple[str, ...]:
    """The write-set §23.3 explicitly places out of scope for this connector.

    Device counts, coordinates, configuration and current status: named here so
    the out-of-scope set is data, not prose. The allowlist above is authoritative
    (anything outside it is refused); this is the documented complement.
    """
    return tuple(vocab()["forbidden_predicate_genres"])


def assert_predicate_allowed(predicate: str) -> str:
    """Return ``predicate`` if allowed, else raise :class:`PredicateNotAllowed`.

    The Atlas connector may write **only** ``deployment_exists`` (§23.3): device
    counts, coordinates, configuration and current status are refused here, at the
    ingestion boundary, rather than only at resolution (SIG-INGEST-033, the ``D6``
    admissibility filter enforced at ingest).
    """
    if not is_predicate_allowed(predicate):
        raise PredicateNotAllowed(
            f"the atlas connector may write only {sorted(predicate_allowlist())} "
            f"(§23.3, SIG-INGEST-033); {predicate!r} is outside the allowlist — "
            "device counts, coordinates, configuration and current status are refused."
        )
    return predicate


# --- agency-id keying + surrogate routing (SIG-INGEST-034) --------------------


@dataclass(frozen=True)
class AgencyIdentity:
    """A **candidate** identifier for an Atlas agency — never a resolution (SIG-INGEST-034).

    The connector keys on the Atlas agency identifier and emits this; the identity
    layer (§14.6) resolves it. An ORI-shaped value routes to the canonical
    ``us.fbi.ori`` scheme; everything else — the common case, since the Atlas keys
    on agency *names* — routes to the ``atlas.agency_name`` **surrogate path** that
    feeds P03.2's crosswalk. ``route`` records which path was taken.
    """

    scheme: str
    value: str
    route: str  # "canonical" | "surrogate"

    def as_identifier(self) -> dict[str, str]:
        """The ``(scheme, value)`` candidate identifier payload (SIG-IDENT-006)."""
        return {"scheme": self.scheme, "value": self.value}


def agency_identity(agency_id: str) -> AgencyIdentity:
    """Route one Atlas agency identifier to a candidate identifier (SIG-INGEST-034).

    An ORI-shaped value (``^[A-Z0-9]{9}$``, validated by :func:`resolution.ori.
    is_valid_ori` — pattern, never position) is a canonical ``us.fbi.ori``
    candidate; any other value routes to the ``atlas.agency_name`` surrogate path.
    The connector never resolves or mints identity here — it only emits the
    candidate and records the route.
    """
    value = agency_id.strip()
    if is_valid_ori(value):
        return AgencyIdentity(scheme=ORI_SCHEME, value=value, route="canonical")
    return AgencyIdentity(scheme=ATLAS_AGENCY_SCHEME, value=value, route="surrogate")


# --- Atlas category → SIG technology family (§23.3) ---------------------------


def category_mapping(category: str) -> Mapping[str, Any] | None:
    """The family-level mapping for an Atlas category, or ``None`` if unmapped."""
    return vocab()["categories"].get(category.strip())


def is_retired_category(category: str) -> bool:
    """Whether an Atlas category has been retired from the upstream taxonomy (SIG-ONTO-059)."""
    return category.strip() in vocab()["retired"]


def retired_categories() -> Mapping[str, Any]:
    """The retired-category ledger (category → retirement metadata, SIG-ONTO-059)."""
    return vocab()["retired"]


# --- evidence-genre preservation (§23.3, OL-2D-AT-02) -------------------------


@cache
def _genre_by_alias() -> dict[str, str]:
    """Reverse map: lowercased upstream component label → canonical genre."""
    out: dict[str, str] = {}
    for genre, spec in vocab()["evidence_genres"].items():
        out[genre.lower()] = genre
        for alias in spec.get("aliases", []):
            out[str(alias).strip().lower()] = genre
    return out


def evidence_genres() -> frozenset[str]:
    """The nine methodology components the Atlas's evidence-genre model names (§23.3)."""
    return frozenset(vocab()["evidence_genres"])


def normalize_evidence_genre(raw: str) -> str | None:
    """Map an upstream component label onto one of the nine genres, or ``None``.

    ``None`` means the upstream label was not recognised — the connector records a
    granularity loss rather than assign a tier by guess (§23.3).
    """
    return _genre_by_alias().get(raw.strip().lower())


def _genre_column(header: Iterable[str]) -> str | None:
    """The feed's evidence-genre column, if it records one at all (§23.3)."""
    present = set(header)
    for name in vocab()["evidence_genre_columns"]:
        if name in present:
            return str(name)
    return None


# --- CSV parsing + canary -----------------------------------------------------


def parse_csv(data: bytes) -> dict[str, Any]:
    """Parse the Atlas adoption CSV into a header + list of row dicts.

    Kept as a pure function of the captured bytes (SIG-INGEST-002): the connector
    reads the archived capture back and calls this, never the network.
    """
    text = data.decode("utf-8-sig")  # tolerate a UTF-8 BOM on the upstream export
    reader = csv.DictReader(io.StringIO(text))
    header = list(reader.fieldnames or [])
    rows = [dict(row) for row in reader]
    return {"header": header, "rows": rows}


def canary_findings(parsed: Mapping[str, Any]) -> list[str]:
    """Structural-drift findings for an Atlas response (SIG-PARSE-008 canary).

    Committed fixtures (SIG-PARSE-007) pin known inputs and pass forever; they
    cannot catch an upstream that quietly changes shape. The canary is the
    complement: it runs against a *live* response on a cadence and alerts when the
    structure the parser depends on drifts. This is that check's deterministic
    core — the schema assertions — so the nightly job is a thin fetch-and-call
    wrapper. An **empty** list means no drift.

    Checks: the agency and category columns are present in the header; every row
    carries a non-empty agency and category. It deliberately does NOT assert
    category *values* — a new Atlas category is handled as an unmapped category +
    research task, not treated as drift (mirrors the osm canary).
    """
    findings: list[str] = []
    header = parsed.get("header")
    if not isinstance(header, list):
        return ["missing CSV header"]
    cols = _columns()
    agency_col = str(cols["agency_column"])
    category_col = str(cols["category_column"])
    for required in (agency_col, category_col):
        if required not in header:
            findings.append(f"missing required column {required!r}")
    if findings:
        return findings
    for i, row in enumerate(parsed.get("rows", [])):
        if not str(row.get(agency_col, "")).strip():
            findings.append(f"row[{i}] has an empty {agency_col!r}")
        if not str(row.get(category_col, "")).strip():
            findings.append(f"row[{i}] has an empty {category_col!r}")
    return findings


# --- category retirement as a vocabulary event (SIG-ONTO-059) -----------------


def category_retirement_record(
    category: str,
    observed_at: datetime | None = None,
    *,
    attribution: str = "",
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """One category-retirement row — a vocabulary event, never a world change.

    A retired Atlas category (SIG-ONTO-059) is recorded under
    :data:`CATEGORY_RETIRED_PREDICATE` with ``event_class='vocabulary_event'`` and
    the Atlas **version** at which it retired, so a disappearance is read as
    "category retired", not as the world event of a deployment ending
    (:data:`DEPLOYMENT_ENDED_PREDICATE`, which is never emitted here). The
    retirement is keyed on the vocabulary version, not wall-clock time;
    ``observed_at`` is optional and included only when a caller supplies it, so a
    connector run emitting it inside the pure ``normalize`` stage stays idempotent
    (SIG-INGEST-003).
    """
    meta = retired_categories()[category.strip()]
    row: dict[str, Any] = {
        "record_kind": "vocabulary_event",
        "predicate_id": CATEGORY_RETIRED_PREDICATE,
        "event_class": "vocabulary_event",
        "retired_category": category.strip(),
        "raw_value": category.strip(),
        "retired_at_atlas_version": str(meta.get("retired_at", "")),
        "removed_data_points": meta.get("removed_data_points"),
        "note": str(meta.get("note", "")),
        "atlas_version": atlas_version(),
        "context": dict(context) if context else None,
    }
    if observed_at is not None:
        row["observed_at"] = observed_at
    return _stamp(row, attribution=attribution)


def unmapped_category_task(subject_id: str, category: str) -> dict[str, Any]:
    """A research task for an Atlas category outside the versioned vocabulary (§23.3)."""
    return {
        "task_type": UNMAPPED_CATEGORY_TASK_TYPE,
        "subject_id": subject_id,
        "atlas_category": category.strip(),
        "priority": 0.5,
        "closing_condition": (
            "the category is added to the versioned atlas_vocab (a §20 migration) "
            "OR confirmed out of scope and annotated"
        ),
        "detector_version": _DETECTOR_VERSION,
        "status": "generated",
    }


# --- the connector ------------------------------------------------------------


@register
class AtlasConnector(Connector):
    """The `atlas` connector: agency adoption from the EFF Atlas of Surveillance (§23.3).

    Runs on the P04.1 eight-stage framework. ``discover``/``fetch`` acquire the
    bulk adoption feed through the shared politeness layer; ``parse``/``extract``/
    ``normalize`` are pure functions of the capture that map each Atlas category to
    a SIG technology family, key on the Atlas agency identifier (routing non-ORI
    values to the surrogate path), preserve the producing evidence genre or record
    its loss, and record a retired category as a retirement rather than a world
    change. Every claim is confined to ``deployment_exists`` by the predicate
    allowlist and stamped into the CC-BY-4.0 SIG graph compartment.
    """

    name = "atlas"
    version = "1.0.0"

    # -- acquisition --
    def discover(self, ctx: RunContext) -> list[Mapping[str, Any]]:
        """Enumerate fetch targets (identifiers, not content).

        Targets come from ``ctx.parameters['targets']`` — each a bulk adoption-feed
        export (the Atlas is a MIRROR-posture CC-BY dataset, §22.6 D).
        """
        return list(ctx.parameters.get("targets", []))

    def fetch(self, ctx: RunContext, target: Mapping[str, Any]) -> FetchResult:
        """Obtain bytes for one target through the shared politeness layer only.

        Connectors hold no HTTP client of their own; the shared fetcher carries the
        descriptive UA and enforces robots + rate limits (SIG-INGEST-011).
        """
        assert ctx.fetcher is not None, "connectors fetch only through the shared layer"
        return ctx.fetcher.fetch(str(target["url"]))

    # -- interpretation (pure functions of the capture) --
    def parse(self, ctx: RunContext, capture: CaptureRef) -> Any:
        """Structure the captured Atlas CSV (header + row dicts)."""
        return parse_csv(ctx.captures.get(capture.digest))

    def extract(self, ctx: RunContext, parsed: Any) -> list[Mapping[str, Any]]:
        """Raw adoption records with locators, preserving raw values (P2).

        Each record keeps the raw agency + category strings, the row's upstream
        attribution (links/summary) and descriptive context, and — if the feed
        records one at all — the raw producing methodology component. No typing or
        mapping happens here; that is :meth:`normalize`.
        """
        cols = _columns()
        header = list(parsed.get("header", []))
        genre_col = _genre_column(header)
        agency_col = str(cols["agency_column"])
        category_col = str(cols["category_column"])
        out: list[Mapping[str, Any]] = []
        for row in parsed.get("rows", []):
            agency = str(row.get(agency_col, "")).strip()
            category = str(row.get(category_col, "")).strip()
            if not agency or not category:
                continue
            out.append(
                {
                    "record_kind": "atlas_row",
                    "agency": agency,
                    "category": category,
                    "attribution_links": [
                        {"column": c, "value": str(row[c]).strip()}
                        for c in cols["attribution_columns"]
                        if str(row.get(c, "")).strip()
                    ],
                    "context": {
                        c: str(row[c]).strip()
                        for c in cols["context_columns"]
                        if str(row.get(c, "")).strip()
                    },
                    # None => the feed does not record the component at all (loss);
                    # "" => recorded but blank (also a loss). Distinct from a value.
                    "raw_evidence_component": (
                        str(row.get(genre_col, "")).strip() if genre_col is not None else None
                    ),
                    "feed_records_component": genre_col is not None,
                }
            )
        return out

    def normalize(
        self, ctx: RunContext, raw_claims: list[Mapping[str, Any]]
    ) -> list[dict[str, Any]]:
        """Typed rows beside preserved raw values (P2), confined to the allowlist.

        Maps each category to a SIG technology family and emits one
        ``deployment_exists`` claim at family granularity; keys on the Atlas agency
        identifier and routes non-ORI values to the surrogate path; carries the
        producing evidence genre or records the granularity loss; records a retired
        category as a retirement (never a deployment); files a research task for an
        unmapped category. Every row is stamped with the Atlas vocabulary version
        and into the CC-BY-4.0 SIG graph compartment.
        """
        attribution = _attribution(ctx)
        out: list[dict[str, Any]] = []
        for raw in raw_claims:
            category = str(raw["category"])
            if is_retired_category(category):
                out.append(
                    category_retirement_record(
                        category,
                        attribution=attribution,
                        context={"agency": raw["agency"], **raw.get("context", {})},
                    )
                )
                continue
            mapping = category_mapping(category)
            if mapping is None:
                out.append(self._unmapped_row(raw, attribution))
                continue
            out.append(self._deployment_row(raw, mapping, attribution))
        return out

    # -- normalization helpers --
    def _deployment_row(
        self, raw: Mapping[str, Any], mapping: Mapping[str, Any], attribution: str
    ) -> dict[str, Any]:
        agency = str(raw["agency"])
        category = str(raw["category"])
        identity = agency_identity(agency)
        genre, loss = self._resolve_genre(raw)
        row: dict[str, Any] = {
            "record_kind": "claim",
            "subject_id": f"atlas:{agency}:{mapping['family']}",
            # SIG-INGEST-033: hard gate — the ONLY claim predicate the atlas
            # connector writes. Raises PredicateNotAllowed on anything else.
            "predicate_id": assert_predicate_allowed(DEPLOYMENT_EXISTS_PREDICATE),
            "value": True,
            "raw_value": category,  # P2: the raw Atlas category is always preserved
            "technology_family": str(mapping["family"]),
            "granularity": "family",  # §23.3: family-level technology granularity
            "sig_technology_concept": mapping.get("sig_concept"),
            "crosswalk_relation": mapping.get("relation"),
            "crosswalk_lossy": bool(mapping.get("lossy", False)),
            "agency_identifier": identity.as_identifier(),
            "identity_route": identity.route,
            "evidence_genre": genre,
            "evidence_genre_granularity_loss": loss,
            "atlas_version": atlas_version(),
            "raw_agency": agency,
            "raw_context": raw.get("context", {}),
            "attribution_links": list(raw.get("attribution_links", [])),
        }
        if raw.get("raw_evidence_component"):
            # Recorded upstream but unrecognised (loss) — keep it for provenance.
            row["raw_evidence_component"] = raw["raw_evidence_component"]
        return _stamp(row, attribution=attribution)

    def _unmapped_row(self, raw: Mapping[str, Any], attribution: str) -> dict[str, Any]:
        agency = str(raw["agency"])
        category = str(raw["category"])
        subject_id = f"atlas:{agency}"
        return _stamp(
            {
                "record_kind": "unmapped_category",
                "subject_id": subject_id,
                "raw_value": category,
                "raw_agency": agency,
                "atlas_version": atlas_version(),
                "agency_identifier": agency_identity(agency).as_identifier(),
                "research_task": unmapped_category_task(subject_id, category),
            },
            attribution=attribution,
        )

    @staticmethod
    def _resolve_genre(raw: Mapping[str, Any]) -> tuple[str | None, bool]:
        """The carried genre and whether it is a granularity loss (§23.3).

        Returns ``(genre, False)`` when the upstream records a recognised component,
        else ``(None, True)`` — the feed did not record a component, or recorded one
        the connector does not recognise; either way a tier is NOT guessed.
        """
        component = raw.get("raw_evidence_component")
        if not component:
            return None, True
        genre = normalize_evidence_genre(str(component))
        if genre is None:
            return None, True
        return genre, False

    # -- link + load --
    # link() is inherited (identity): SIG-INGEST-034 — the connector emits candidate
    # identifiers and NEVER resolves entities itself; resolution is the identity
    # layer's job (P03.2/P05.1).

    def load(self, ctx: RunContext, linked: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Produce the L1 rows; the driver asserts them (live only).

        Adds the generated ``claim_id`` + transaction time (the two columns the
        reproducibility fingerprint excludes, SIG-INGEST-003). Every row is already
        stamped into the CC-BY-4.0 SIG graph compartment in :meth:`normalize`.
        """
        return load_claims_for_l1(linked)


# --- module-private helpers ---------------------------------------------------


def _stamp(row: dict[str, Any], *, attribution: str = "") -> dict[str, Any]:
    """Stamp a row with source attribution + the CC-BY-4.0 compartment (§42.2).

    Preserving the Atlas's own source attribution on every row is an AC of §23.3;
    the CC-BY-4.0 / ``sig_graph`` stamp keeps Atlas-derived claims in the SIG graph
    compartment the export gate governs (SIG-LIC-010).
    """
    row.setdefault("source_id", ATLAS_SOURCE_ID)
    row["source_attribution"] = attribution
    row["license"] = CC_BY_LICENSE
    row["compartment"] = SIG_GRAPH_COMPARTMENT
    return row


def _attribution(ctx: RunContext) -> str:
    """The Atlas's required attribution string, from the source's rights record."""
    try:
        return ctx.source.rights.attribution
    except AttributeError:  # pragma: no cover - defensive; ctx.source is a SourceRecord
        return ""


def load_claims_for_l1(claims: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Add the generated ``claim_id`` + transaction time each L1 row needs.

    Mirrors the framework's load contract: ``claim_id`` and ``sys_period`` are the
    two non-deterministic columns the reproducibility fingerprint excludes
    (SIG-INGEST-003), so replay is byte-identical modulo exactly these.
    """
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
    "ATLAS_AGENCY_SCHEME",
    "ATLAS_SOURCE_ID",
    "CATEGORY_RETIRED_PREDICATE",
    "CC_BY_LICENSE",
    "DEPLOYMENT_ENDED_PREDICATE",
    "DEPLOYMENT_EXISTS_PREDICATE",
    "ORI_SCHEME",
    "SIG_GRAPH_COMPARTMENT",
    "UNMAPPED_CATEGORY_TASK_TYPE",
    "AgencyIdentity",
    "AtlasConnector",
    "PredicateNotAllowed",
    "agency_identity",
    "assert_predicate_allowed",
    "atlas_version",
    "canary_findings",
    "category_mapping",
    "category_retirement_record",
    "evidence_genres",
    "forbidden_predicate_genres",
    "is_predicate_allowed",
    "is_retired_category",
    "load_claims_for_l1",
    "normalize_evidence_genre",
    "parse_csv",
    "predicate_allowlist",
    "retired_categories",
    "unmapped_category_task",
    "vocab",
    "vocab_version",
]
