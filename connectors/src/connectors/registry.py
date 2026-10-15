# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The seeded source registry (§22, SIG-INGEST-023/024/026/027/038).

Every source SIG may ever ingest from has a registry row here, seeded from the
canonical spec's verified access matrix (§22.2), the outline's named sources
(OL-21), and the sources research added (§22.3/§22.6). A registry described in
prose is not executable (SIG-ENG-001); this module makes it data.

Three invariants are load-bearing and enforced here rather than left to prose:

* **``ingestion_permitted`` defaults to false** (SIG-INGEST-028). It is a hard
  runtime gate — a connector refuses to run when it is false — not a note. The
  gate itself lives in :mod:`connectors.loader`.
* **``redistributable`` is separately reviewed** and MUST NOT be derived from the
  licence string (SIG-INGEST-024 / SIG-LIC-003). The rights record is built from
  the policy package's :class:`~policy.rights.RightsRecord`, which requires the
  field explicitly; a source whose rights are unresolved is ``UNDETERMINED``
  (SIG-LIC-001/004) and fails the export gate closed.
* **``compact_status`` is a closed vocabulary in which ``no_response`` is a real,
  recorded state** (SIG-INGEST-027), not the absence of one.

The rights review (which SPDX expression, whether redistributable) is a per-source
research task; where the spec has not resolved it, the row carries ``UNDETERMINED``
rather than a guess (SIG-LIC-004).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from functools import cache
from typing import Any

from policy.rights import UNDETERMINED, RightsRecord, RightsReservation

from ._data import load_table


class SourceKind(StrEnum):
    """The genre of a source (§10.3.1)."""

    UPSTREAM_PROJECT = "upstream_project"
    VENDOR_SITE = "vendor_site"
    GOVERNMENT_PORTAL = "government_portal"
    #: Municipal surveillance-ordinance (CCOPS) disclosures — their own source
    #: class, distinct from civil-society datasets and vendor portals
    #: (SIG-INGEST-049, P24.7): licence public record, format pdf, document pipeline.
    GOVERNMENT_MANDATED_DISCLOSURE = "government_mandated_disclosure"
    RECORDS_CHANNEL = "records_channel"
    NEWS_PUBLISHER = "news_publisher"
    COURT_SYSTEM = "court_system"
    ACADEMIC = "academic"
    COMMUNITY = "community"
    CONTRIBUTOR = "contributor"
    COMMERCIAL = "commercial"


class CustodyPosture(StrEnum):
    """How SIG holds a source's content (§8.4)."""

    MIRROR = "MIRROR"
    DERIVE = "DERIVE"
    REFERENCE = "REFERENCE"
    LINK = "LINK"


class CompactStatus(StrEnum):
    """Outreach / permission state for a source (SIG-INGEST-027).

    A **closed** vocabulary. ``NO_RESPONSE`` is a recorded state, not an absence
    of one — the distinction the federation compact turns on.
    """

    NOT_CONTACTED = "not_contacted"
    CONTACTED_AWAITING_RESPONSE = "contacted_awaiting_response"
    NO_RESPONSE = "no_response"
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_GRANTED_CONDITIONAL = "permission_granted_conditional"
    PERMISSION_DECLINED = "permission_declined"
    PUBLIC_TERMS_ONLY = "public_terms_only"
    PARTNERSHIP_ACTIVE = "partnership_active"


class RobotsPolicy(StrEnum):
    """The robots.txt posture a connector MUST honour (§10.3.1, §26)."""

    HONOR = "honor"
    HONOR_WITH_EXCEPTION = "honor_with_exception"
    NOT_APPLICABLE = "not_applicable"


#: Source reliability `R`, a property of the publisher (§10.4). Assigned per
#: source in the registry, never re-judged per claim (SIG-EPIS-014).
RELIABILITY_TIERS: frozenset[str] = frozenset({"R1", "R2", "R3", "R4", "R5", "R6"})


@dataclass(frozen=True)
class DateCorrection:
    """An additive correction to a recorded registry date (P34.22b / ADR-146).

    The recorded ``sources.toml`` value is never rewritten (ADR-146 D2: no
    committed artifact is edited to fix a date); the correction sits beside it
    and a reader prefers :meth:`SourceRecord.effective_date` — which returns
    the ``true`` date — when it shows the date. ``field`` names the corrected
    field: ``"last_verified"``, ``"rights_reviewed_on"`` or
    ``"rights.retrieval_date"`` (a dotted name addresses the nested rights
    block). ``evidence`` names the commit whose committer time evidences the
    true date; ``adr`` names the correcting decision record.
    """

    field: str
    recorded: date
    true: date
    evidence: str
    adr: str

    def __post_init__(self) -> None:
        if not self.field:
            raise ValueError("a date correction requires a field")
        if not self.evidence:
            raise ValueError(f"date correction for {self.field!r} requires evidence")
        if not self.adr:
            raise ValueError(f"date correction for {self.field!r} requires an adr")


#: The registry fields a ``[[sources.<id>.date_corrections]]`` entry may
#: correct — the three date fields the rights-record surfaces carry.
CORRECTABLE_DATE_FIELDS: frozenset[str] = frozenset(
    {"last_verified", "rights_reviewed_on", "rights.retrieval_date"}
)


@dataclass(frozen=True)
class SourceRecord:
    """A single source registry row (§10.3.1, SIG-INGEST-023).

    Carries, at minimum, the SIG-INGEST-023 fields: identity, custody posture, a
    rights record with an SPDX expression and a separately-reviewed
    ``redistributable`` boolean, ``default_tier`` + source reliability ``R``,
    access method, auth model, rate limits, observed cadence, ``compact_status``,
    ``ingestion_permitted``, contact channel, and a last-verified date.
    """

    id: str
    name: str
    source_kind: SourceKind
    homepage_url: str
    #: Source reliability R (§10.4); the source's default evidence tier.
    default_tier: str
    custody_posture: CustodyPosture
    compact_status: CompactStatus
    robots_policy: RobotsPolicy
    rights: RightsRecord
    #: Hard gate — a connector refuses to run when false (SIG-INGEST-028).
    ingestion_permitted: bool = False
    #: Novel-source flag: defaults R5 with the flag set (SIG-EPIS-015).
    reliability_provisional: bool = False
    access_method: str = ""
    auth_model: str = "none"
    rate_limits: str = ""
    cadence: str = ""
    contact: str = ""
    last_verified: date | None = None
    #: Whether the lead research pass actually reached the URL (§22.6 "Verified").
    verified: bool = False
    notes: str = ""
    #: Rights-review metadata (P21.1, SIG-LIC-001/009, SIG-INGEST-028/038). All
    #: optional (additive/back-compat): an unreviewed row carries none. A flip to
    #: ``ingestion_permitted = true`` is invalid without them — enforced by
    #: :func:`review_metadata_violations`, not by prose.
    #: Reviewer ROLE (never a personal name — Part VIII §0.7), e.g. "licensing reviewer".
    rights_reviewed_by: str = ""
    #: Date the rights review was recorded.
    rights_reviewed_on: date | None = None
    #: Path (repo-relative) to the source's rights-review packet under docs/build/rights/.
    review_packet: str = ""
    #: Additive date corrections (P34.22b / ADR-146): the recorded fields above
    #: are never rewritten; a reader showing one prefers ``effective_date``.
    date_corrections: tuple[DateCorrection, ...] = ()

    def correction_for(self, field: str) -> DateCorrection | None:
        """The declared correction for ``field``, or None."""
        return next((c for c in self.date_corrections if c.field == field), None)

    def recorded_date(self, field: str) -> date | None:
        """The field's recorded value — what the registry row literally says."""
        if field == "last_verified":
            return self.last_verified
        if field == "rights_reviewed_on":
            return self.rights_reviewed_on
        if field == "rights.retrieval_date":
            return self.rights.retrieval_date
        raise KeyError(f"source {self.id!r}: unknown date field {field!r}")

    def effective_date(self, field: str) -> date | None:
        """The date a reader shows: the corrected ``true`` date when a
        correction exists (ADR-146), else the recorded value."""
        correction = self.correction_for(field)
        if correction is not None:
            return correction.true
        return self.recorded_date(field)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("source record requires an id")
        if not self.name:
            raise ValueError(f"source {self.id!r} requires a name")
        if self.default_tier not in RELIABILITY_TIERS:
            raise ValueError(
                f"source {self.id!r} has default_tier {self.default_tier!r}; "
                f"must be one of {sorted(RELIABILITY_TIERS)} (§10.4)."
            )
        if self.rights.source_id != self.id:
            raise ValueError(
                f"source {self.id!r} carries a rights record for "
                f"{self.rights.source_id!r}; they must match (SIG-LIC-001)."
            )
        seen: set[str] = set()
        for correction in self.date_corrections:
            if correction.field in seen:
                raise ValueError(
                    f"source {self.id!r}: duplicate date correction for "
                    f"{correction.field!r} — corrections are additive but "
                    "never ambiguous"
                )
            seen.add(correction.field)
            if correction.field not in CORRECTABLE_DATE_FIELDS:
                raise ValueError(
                    f"source {self.id!r}: date correction names uncorrectable "
                    f"field {correction.field!r} (correctable: "
                    f"{sorted(CORRECTABLE_DATE_FIELDS)})"
                )
            if correction.recorded != self.recorded_date(correction.field):
                raise ValueError(
                    f"source {self.id!r}: date correction for "
                    f"{correction.field!r} records {correction.recorded}, but "
                    f"the row carries {self.recorded_date(correction.field)} — "
                    "a correction names the recorded value it corrects "
                    "(ADR-146), never invents one"
                )


def _rights_from_row(source_id: str, row: dict[str, Any]) -> RightsRecord:
    """Build the source's rights record (§42.1), defaulting to UNDETERMINED.

    ``redistributable`` is required per row and is **never** inferred from the
    SPDX string (SIG-INGEST-024 / SIG-LIC-003): an unresolved source is
    ``UNDETERMINED`` + ``redistributable = false``, which fails the export gate
    closed (SIG-LIC-004).
    """
    r: dict[str, Any] = dict(row.get("rights", {}))
    spdx = str(r.get("spdx", UNDETERMINED))
    retrieval = r.get("retrieval_date")
    return RightsRecord(
        source_id=source_id,
        spdx=spdx,
        attribution=str(r.get("attribution", "")),
        redistributable=bool(r.get("redistributable", False)),
        derivative_permitted=bool(r.get("derivative_permitted", False)),
        terms_url=str(r.get("terms_url", "")),
        retrieval_date=retrieval if isinstance(retrieval, date) else date(2026, 8, 20),
        ai_training_permitted=bool(r.get("ai_training_permitted", False)),
        upstream_license=r.get("upstream_license"),
        # P34.19 (F-403, ADR-183): express-terms disclosure fields, optional.
        captured_terms_verbatim=str(r.get("captured_terms_verbatim", "")),
        captured_terms_evidence=str(r.get("captured_terms_evidence", "")),
        publication_basis=str(r.get("publication_basis", "")),
        # P36.1a (SIG-INGEST-046c): the recorded refusal state, additive — a
        # ``[sources.<id>.rights.reservation]`` sub-table lands only when an
        # affirmative machine-readable reservation was observed and recorded;
        # it is never UNDETERMINED and never edits a landed fact.
        reservation=_reservation_from_row(source_id, r.get("reservation")),
    )


def _reservation_from_row(source_id: str, row: Any) -> RightsReservation | None:
    """Parse the optional ``rights.reservation`` sub-table (SIG-INGEST-046c).

    Fail-closed: a present but malformed reservation — wrong shape, a missing
    kind/verbatim/observed_on/evidence — raises rather than silently dropping
    a refusal (the defining standard, §3.1).
    """
    if row is None:
        return None
    if not isinstance(row, dict):
        raise ValueError(
            f"source {source_id!r}: rights.reservation must be a table "
            "{kind, verbatim, observed_on, evidence} (SIG-INGEST-046c)"
        )
    observed_on = row.get("observed_on")
    if not isinstance(observed_on, date):
        raise ValueError(
            f"source {source_id!r}: rights.reservation.observed_on must be a TOML date"
        )
    return RightsReservation(
        kind=str(row.get("kind", "")),
        verbatim=str(row.get("verbatim", "")),
        observed_on=observed_on,
        evidence=str(row.get("evidence", "")),
    )


def _date_corrections_from_row(source_id: str, row: dict[str, Any]) -> tuple[DateCorrection, ...]:
    """Parse the optional ``date_corrections`` array (P34.22b / ADR-146).

    Fail-closed: a malformed entry — wrong shape, a non-date value, a missing
    evidence/adr field — raises rather than silently dropping a correction.
    The ``recorded`` value's fidelity to the row is checked by
    :class:`SourceRecord`'s own validation.
    """
    out: list[DateCorrection] = []
    for i, entry in enumerate(row.get("date_corrections") or ()):
        if not isinstance(entry, dict):
            raise ValueError(f"source {source_id!r}: date_corrections[{i}] is not a table")
        try:
            field = str(entry["field"])
            recorded = entry["recorded"]
            true = entry["true"]
            evidence = str(entry["evidence"])
            adr = str(entry["adr"])
        except KeyError as exc:
            raise ValueError(
                f"source {source_id!r}: date_corrections[{i}] lacks {exc} — "
                "an entry is {field, recorded, true, evidence, adr}"
            ) from exc
        if not isinstance(recorded, date) or not isinstance(true, date):
            raise ValueError(
                f"source {source_id!r}: date_corrections[{i}] recorded/true must be TOML dates"
            )
        out.append(
            DateCorrection(field=field, recorded=recorded, true=true, evidence=evidence, adr=adr)
        )
    return tuple(out)


def _record_from_row(source_id: str, row: dict[str, Any]) -> SourceRecord:
    last_verified = row.get("last_verified")
    return SourceRecord(
        id=source_id,
        name=str(row["name"]),
        source_kind=SourceKind(row["source_kind"]),
        homepage_url=str(row.get("homepage_url", "")),
        default_tier=str(row.get("default_tier", "R5")),
        custody_posture=CustodyPosture(row.get("custody_posture", "LINK")),
        compact_status=CompactStatus(row.get("compact_status", "not_contacted")),
        robots_policy=RobotsPolicy(row.get("robots_policy", "honor")),
        rights=_rights_from_row(source_id, row),
        ingestion_permitted=bool(row.get("ingestion_permitted", False)),
        reliability_provisional=bool(row.get("reliability_provisional", False)),
        access_method=str(row.get("access_method", "")),
        auth_model=str(row.get("auth_model", "none")),
        rate_limits=str(row.get("rate_limits", "")),
        cadence=str(row.get("cadence", "")),
        contact=str(row.get("contact", "")),
        last_verified=last_verified if isinstance(last_verified, date) else None,
        verified=bool(row.get("verified", False)),
        notes=str(row.get("notes", "")),
        rights_reviewed_by=str(row.get("rights_reviewed_by", "")),
        rights_reviewed_on=(
            reviewed_on if isinstance(reviewed_on := row.get("rights_reviewed_on"), date) else None
        ),
        review_packet=str(row.get("review_packet", "")),
        date_corrections=_date_corrections_from_row(source_id, row),
    )


@cache
def registry() -> dict[str, SourceRecord]:
    """The full seeded source registry, keyed by source id (SIG-INGEST-038)."""
    table = load_table("sources")
    records: dict[str, SourceRecord] = {}
    for source_id, row in table.get("sources", {}).items():
        if source_id in records:
            raise ValueError(f"duplicate source id in registry: {source_id!r}")
        records[source_id] = _record_from_row(source_id, row)
    return records


def sources() -> list[SourceRecord]:
    """Every registered source, ordered by id."""
    return [registry()[k] for k in sorted(registry())]


def get(source_id: str) -> SourceRecord:
    """Return one source by id, or raise :class:`KeyError`."""
    return registry()[source_id]


def rights_records() -> list[RightsRecord]:
    """The rights record of every registered source (SIG-LIC-001)."""
    return [s.rights for s in sources()]
