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

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from functools import cache
from typing import Any

from policy.rights import UNDETERMINED, RightsRecord, RightsReservation
from policy.transparency import (
    PART_VIII_CLASSES,
    PART_VIII_CLEAR_VALUES,
    REDISTRIBUTION_LANES,
)

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
    """The source's robots.txt posture **as declared at review time** (§10.3.1,
    §26) — registry metadata, never an enforcement claim (ADR-222).

    The field records what a review observed about the source's surface,
    not what the fetcher will do: under GL-GATE-08 (ADR-088, re-confirmed
    A-5 on every host — ADR-168) every host's robots verdict is probed,
    classified per RFC 9309 §2.3.1.4 and recorded, and a ``disallowed`` or
    ``unretrievable`` verdict does not gate the fetch — it is stamped
    ``robots_disregarded`` and disclosed publicly as host + count. No value
    of this field changes that behaviour:

    * ``honor`` — a crawlable surface whose robots.txt is probed and
      recorded; the historical label for "a robots policy governs this
      surface", kept verbatim so pre-P36.1b rows stay readable. It is a
      declaration of the surface's posture, not a promise the fetcher obeys
      the verdict — read "probe and record".
    * ``honor_with_exception`` — the same, where a recorded exception basis
      (e.g. an ADR-083 documented-API allow-list entry) covers part of the
      surface.
    * ``not_applicable`` — no robots-governed crawl surface (a documented
      API-mode row, or a non-fetch record source).

    The vocabulary is closed; a new value is an additive enum entry, never
    a retconned meaning. What still refuses — host opt-outs and affirmative
    rights reservations — is governed by §26 rule 7 / SIG-INGEST-046c, not
    by this field.
    """

    HONOR = "honor"
    HONOR_WITH_EXCEPTION = "honor_with_exception"
    NOT_APPLICABLE = "not_applicable"


#: Source reliability `R`, a property of the publisher (§10.4). Assigned per
#: source in the registry, never re-judged per claim (SIG-EPIS-014).
RELIABILITY_TIERS: frozenset[str] = frozenset({"R1", "R2", "R3", "R4", "R5", "R6"})

#: The §28.3 volatility classes a source row may declare (P35.20b / ED-43):
#: the same closed vocabulary as the predicate registry's
#: ``PredicateVolatility`` (ontology `sig_models`) — the source's class seeds
#: whether its staleness is evaluable at all (SIG-METRIC-006). A test pins this
#: tuple equal to the generated enum's members; the classes are never
#: re-derived silently from a name. A source with NO declared class is
#: ``not_evaluable`` on the freshness surface — the honest state, never a
#: guessed default (§3.1).
VOLATILITY_CLASSES: frozenset[str] = frozenset(
    {"IMMUTABLE", "GLACIAL", "SLOW", "MODERATE", "FAST", "VOLATILE"}
)


class LineageKind(StrEnum):
    """A source's declared lineage class (P35.25 / R11-L3-CP4, SIG-CONF-014).

    A **closed** vocabulary: ``primary`` (the source's records are its own
    collection, not a republish of another tracked dataset), ``mirror`` (a
    byte-faithful or row-faithful copy of an upstream), ``derived`` (reprocessed
    from upstream records), ``syndicated`` (a synthesis of several upstreams).
    ``undeclared`` is the honest default for a row carrying no ``[lineage]``
    block — never a claim of independence (§3.1; an absent declaration MUST
    NOT read as "independent").
    """

    PRIMARY = "primary"
    MIRROR = "mirror"
    DERIVED = "derived"
    SYNDICATED = "syndicated"
    UNDECLARED = "undeclared"


#: The independence-class token the resolver uses when no declared lineage
#: establishes one (SIG-CONF-014): undeclared claims collapse into this shared
#: pseudo-class so unclassified material NEVER counts as independent
#: corroboration — two undeclared voices agreeing stay ONE voice until the
#: registry says otherwise.
UNCLASSIFIED = "unclassified"


@dataclass(frozen=True)
class SourceRedistribution:
    """The ``[sources.<id>.redistribution]`` declaration (P35.35 / ADR-183).

    The registry of record's redistribution-lane verdict: the J4 pass's
    recorded lane, the evidence that produced it, the decision that ratified
    it, and the Part VIII signals ``derive_storage_tier`` reads. Additive: a
    row without the block parses to the undeclared default (``lane == ""`` —
    an honest absence, distinct from a *recorded* ``unknown`` verdict, which
    names why no positive lane could be evidenced). A declared lane is a
    recorded decision — it names its evidence, and a positive lane (anything
    but ``unknown``) names the decision authority that recorded it; the
    interim rights-record basis stays the fallback a lane-less row leaves,
    and never reaches ``public``.
    """

    #: The recorded lane — one of ``policy.transparency.REDISTRIBUTION_LANES``;
    #: ``""`` when the block is absent (undeclared, fail-closed).
    lane: str = ""
    #: The recorded basis text (verbatim from the lane pass's evidence column —
    #: the same field, not a new one).
    evidence: str = ""
    #: Where the recorded evidence lives (repo-relative path/URI).
    evidence_uri: str = ""
    #: The recorded decision that ratified the lane (e.g. ``D-J3-1 [B-19]``).
    decision_authority: str = ""
    #: The verdict itself flags thin evidence needing a fresh review pass.
    review_needed: bool = False
    #: The most restrictive recorded Part VIII class (``P8-1``…``P8-9``) or a
    #: recorded clear value (``clear``/``none-known``); ``""`` = unscreened.
    part_viii_class: str = ""
    #: R-10: the packet limits redistribution to aggregate granularity.
    packet_limited: bool = False
    #: R-11: a SIG-recorded CC0 label on SIG-authored material only.
    sig_labelled_cc0: bool = False

    def registry_version(self) -> str:
        """A content-derived version id for the DB mirror row's PK.

        The append-only ``source_redistribution`` projection keys rows on
        ``(source_id, registry_version)``: a lane declaration that changes
        lands a NEW row under a new version, never an UPDATE — the audit
        trail J4's lane history wants.
        """
        import hashlib

        canonical = "|".join(
            (
                self.lane,
                self.part_viii_class,
                self.evidence,
                self.evidence_uri,
                self.decision_authority,
                "1" if self.review_needed else "0",
                "1" if self.packet_limited else "0",
                "1" if self.sig_labelled_cc0 else "0",
            )
        )
        return f"sources.toml+{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"


@dataclass(frozen=True)
class SourceLineage:
    """The ``[sources.<id>.lineage]`` declaration (P35.25 / ADR-213).

    Additive registry metadata: a row without the block parses to the
    ``undeclared`` default. ``mirror_of``/``derived_from`` name OTHER REGISTRY
    source ids (validated at load); ``origin`` is the documentary free-text
    upstream when the upstream is not itself a registered source. A declared
    ``independence_class`` (``src:<source-id>`` or ``ext:<slug>``) overrides the
    resolved class — used to collapse several sources onto one upstream when
    that upstream is not registered under a stable id. Any non-undeclared
    ``kind`` requires ``evidence`` — a lineage declaration is a claim and
    names its basis.
    """

    kind: LineageKind = LineageKind.UNDECLARED
    #: Free-text upstream when it is not a registry source (e.g. a city's own
    #: GIS portal a camreg layer republishes).
    origin: str = ""
    #: The registry source this row mirrors (kind = mirror).
    mirror_of: str = ""
    #: The registry sources this row derives from (kind = derived/syndicated).
    derived_from: tuple[str, ...] = ()
    #: Explicit class override — ``src:<id>`` | ``ext:<slug>`` — when the
    #: resolved class would be wrong (e.g. two sources sharing one
    #: unregistered upstream declare the same ``ext:`` token).
    independence_class: str = ""
    #: The declared identifier namespace this source's upstream references
    #: live in (``data/id_namespaces.toml`` in ``db``, or ``src:<source-id>``
    #: for a source-private space). Two ``external_ref`` values compare only
    #: inside one namespace — a bare equal string across namespaces is never
    #: shared-upstream evidence (P35.25 NEW-1). Empty = undeclared.
    id_namespace: str = ""
    #: The §10.8 collection-method label (SIG-EPIS-028) — feeds method breadth.
    collection_method: str = ""
    #: The documentary basis for the declaration (required unless undeclared).
    evidence: str = ""


def resolve_independence_class(record: SourceRecord, records: Mapping[str, SourceRecord]) -> str:
    """The claim-level independence class a source's claims carry (§10.8).

    Declared rules, transitively resolved, never guessed:
    ``independence_class`` override → ``mirror_of``'s resolved class →
    ``derived_from`` resolving to a single distinct root → that root
    (multi-root derivations are ``unclassified``: a synthesis cannot honestly
    corroborate any single upstream) → declared kinds with no resolvable
    upstream are their own root ``src:<self>`` (the upstream is otherwise
    unrepresented in the graph — a lone voice, which can never corroborate
    itself anyway) → ``undeclared`` is ``unclassified``.
    """
    seen: set[str] = set()
    cur = record
    while True:
        lin = cur.lineage
        if lin.independence_class:
            return lin.independence_class
        if cur.id in seen:
            return UNCLASSIFIED  # a declared cycle is a defect — never a class
        seen.add(cur.id)
        if lin.kind == LineageKind.MIRROR and lin.mirror_of:
            upstream = records.get(lin.mirror_of)
            if upstream is None:
                return UNCLASSIFIED
            cur = upstream
            continue
        if lin.kind in (LineageKind.DERIVED, LineageKind.SYNDICATED) and lin.derived_from:
            roots = set()
            for up_id in lin.derived_from:
                up = records.get(up_id)
                if up is None:
                    roots.add(UNCLASSIFIED)
                    continue
                up_lin = up.lineage
                if up_lin.independence_class:
                    roots.add(up_lin.independence_class)
                elif up_lin.kind == LineageKind.UNDECLARED:
                    roots.add(UNCLASSIFIED)
                else:
                    roots.add(f"src:{up_id}")
            if len(roots) == 1:
                return roots.pop()
            return UNCLASSIFIED
        if lin.kind == LineageKind.UNDECLARED:
            return UNCLASSIFIED
        # Declared kind with no resolvable registry upstream — the source is
        # the upstream's only voice in the graph; it is its own root.
        return f"src:{cur.id}"


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
    #: The source's robots posture as declared at review time (ADR-222) —
    #: registry metadata, never an enforcement claim; under GL-GATE-08 every
    #: value means "probe + record" (:class:`RobotsPolicy`).
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
    #: P35.20b (ED-43, SIG-METRIC-006): the source's DECLARED §28.3 volatility
    #: class — the class its emit surface's dominant predicate volatility seeds.
    #: Empty when undeclared: staleness is then NOT evaluable for this source
    #: (the freshness surface reads ``not_evaluable``), never a guessed class.
    volatility_class: str = ""
    #: The recorded basis for the declared class (e.g. ``ADR-104(e)``'s
    #: recalibration from observed change rates). A declared class with no
    #: basis fails validation — a class is a claim and carries its evidence.
    volatility_basis: str = ""
    #: P35.25 (R11-L3-CP4, SIG-CONF-014): the declared lineage — origin /
    #: mirror_of / derived_from / independence_class — additive metadata, the
    #: ``undeclared`` default never reading as "independent". Lineage has NO
    #: effect on ``assert_loadable`` (the loader gate reads permission fields
    #: only — this is corroboration metadata, not an ingestion input).
    lineage: SourceLineage = SourceLineage()
    #: P35.35 (D-J3-1 [B-19], ADR-183): the recorded redistribution-lane
    #: verdict — the registry of record for the lane the capture-writer's
    #: ``storage_tier`` derivation and ``v_transparency_source`` read. An
    #: absent block is the undeclared default — ``lane == ""`` — which leaves
    #: the interim rights-record basis in charge (never ``public``). This is
    #: redistribution metadata, never an ingestion input: it has NO effect on
    #: ``assert_loadable`` and never flips ``ingestion_permitted``.
    redistribution: SourceRedistribution = SourceRedistribution()

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
        # P35.20b: a declared volatility class must be in the closed §28.3
        # vocabulary and carry its basis — never a guessed default (§3.1).
        if self.volatility_class:
            if self.volatility_class not in VOLATILITY_CLASSES:
                raise ValueError(
                    f"source {self.id!r} has volatility_class "
                    f"{self.volatility_class!r}; must be one of "
                    f"{sorted(VOLATILITY_CLASSES)} (§28.3, P35.20b)."
                )
            if not self.volatility_basis.strip():
                raise ValueError(
                    f"source {self.id!r} declares volatility_class "
                    f"{self.volatility_class!r} with no volatility_basis — a "
                    "class is a claim and names its evidence (P35.20b)."
                )
        elif self.volatility_basis.strip():
            raise ValueError(
                f"source {self.id!r} carries a volatility_basis but no "
                "volatility_class — a basis without a class is dangling (P35.20b)."
            )
        # P35.25: a lineage declaration is a claim — it names its evidence, and
        # its upstream references are registry ids, never free text the resolver
        # could silently misspell. `undeclared` needs nothing (it IS the honest
        # default); any declared kind with no documentary evidence fails closed.
        lin = self.lineage
        if lin.kind != LineageKind.UNDECLARED and not lin.evidence.strip():
            raise ValueError(
                f"source {self.id!r} declares lineage kind {lin.kind.value!r} "
                "with no lineage.evidence — a declaration names its documentary "
                "basis (P35.25, §3.1); leave the block absent for `undeclared`."
            )
        if lin.mirror_of == self.id or self.id in lin.derived_from:
            raise ValueError(
                f"source {self.id!r} names itself in mirror_of/derived_from — a "
                "source is never its own lineage (P35.25)."
            )
        if lin.kind == LineageKind.MIRROR and not (lin.mirror_of or lin.origin):
            raise ValueError(
                f"source {self.id!r} declares kind=mirror with neither "
                "mirror_of (a registry source) nor origin (a named upstream) — "
                "a mirror names what it copies (P35.25)."
            )
        if lin.independence_class and not (
            lin.independence_class == UNCLASSIFIED
            or lin.independence_class.startswith("src:")
            or lin.independence_class.startswith("ext:")
        ):
            raise ValueError(
                f"source {self.id!r} declares independence_class "
                f"{lin.independence_class!r}; the vocabulary is "
                "'src:<source-id>' | 'ext:<slug>' | 'unclassified' (P35.25)."
            )
        # A mirror_of/derived_from reference resolves only against registry
        # ids; the cross-source existence check runs in ``registry()`` once the
        # whole table is loaded (fail-closed: a dangling id raises at load).
        # P35.35: a redistribution declaration is a recorded verdict — it
        # names the closed-vocabulary lane, its evidence, and (for a positive
        # lane) the decision that ratified it. An absent block is the honest
        # undeclared default; a block naming an invented lane, an unevidenced
        # verdict, or a Part VIII class outside J4's vocabulary fails closed —
        # never silently "unknown" (a recorded unknown still names why).
        red = self.redistribution
        if red.lane:
            if red.lane not in REDISTRIBUTION_LANES:
                raise ValueError(
                    f"source {self.id!r} declares redistribution lane "
                    f"{red.lane!r}; the closed vocabulary is "
                    f"{sorted(REDISTRIBUTION_LANES)} (P35.35, J4 R-1…R-13)."
                )
            if not red.evidence.strip():
                raise ValueError(
                    f"source {self.id!r} declares redistribution lane "
                    f"{red.lane!r} with no redistribution.evidence — a lane is "
                    "a recorded verdict and names its basis (P35.35); leave "
                    "the block absent for the undeclared default."
                )
            if red.lane != "unknown" and not red.decision_authority.strip():
                raise ValueError(
                    f"source {self.id!r} declares positive redistribution "
                    f"lane {red.lane!r} with no decision_authority — a "
                    "positive lane records the decision that ratified it "
                    "(P35.35); only a recorded 'unknown' may stand on thin "
                    "evidence alone."
                )
        elif red != SourceRedistribution():
            raise ValueError(
                f"source {self.id!r} carries redistribution fields but no "
                "lane — a declaration without its verdict is dangling "
                "(P35.35)."
            )
        if red.part_viii_class and red.part_viii_class not in (
            PART_VIII_CLASSES | PART_VIII_CLEAR_VALUES
        ):
            raise ValueError(
                f"source {self.id!r} declares part_viii_class "
                f"{red.part_viii_class!r}; the vocabulary is "
                f"{sorted(PART_VIII_CLASSES | PART_VIII_CLEAR_VALUES)} "
                "(J4 §9, P35.35)."
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


def _lineage_from_row(source_id: str, row: dict[str, Any]) -> SourceLineage:
    """Parse the optional ``[sources.<id>.lineage]`` sub-table (P35.25).

    Absent block → the ``undeclared`` default (never "independent"). A present
    block must be a table; its fields validate on :class:`SourceLineage` and in
    :class:`SourceRecord`'s ``__post_init__``.
    """
    raw = row.get("lineage")
    if raw is None:
        return SourceLineage()
    if not isinstance(raw, dict):
        raise ValueError(
            f"source {source_id!r}: lineage must be a table "
            "{kind, origin, mirror_of, derived_from, independence_class, "
            "collection_method, evidence} (P35.25)"
        )
    derived = raw.get("derived_from") or ()
    if isinstance(derived, str):
        derived = (derived,)
    if not isinstance(derived, (list, tuple)):
        raise ValueError(
            f"source {source_id!r}: lineage.derived_from must be a list of "
            "registry source ids (P35.25)"
        )
    return SourceLineage(
        kind=LineageKind(str(raw.get("kind", LineageKind.UNDECLARED.value))),
        origin=str(raw.get("origin", "")),
        mirror_of=str(raw.get("mirror_of", "")),
        derived_from=tuple(str(u) for u in derived),
        independence_class=str(raw.get("independence_class", "")),
        id_namespace=str(raw.get("id_namespace", "")),
        collection_method=str(raw.get("collection_method", "")),
        evidence=str(raw.get("evidence", "")),
    )


def _redistribution_from_row(source_id: str, row: dict[str, Any]) -> SourceRedistribution:
    """Parse the optional ``[sources.<id>.redistribution]`` sub-table (P35.35).

    Absent block → the undeclared default (``lane == ""`` — the honest
    absence, not a recorded ``unknown``). A present block must be a table
    naming only the declared fields — an unknown key is a typo the load
    refuses rather than silently dropping (fail-closed, §3.1); the lane and
    Part VIII vocabularies validate on :class:`SourceRecord`.
    """
    raw = row.get("redistribution")
    if raw is None:
        return SourceRedistribution()
    if not isinstance(raw, dict):
        raise ValueError(
            f"source {source_id!r}: redistribution must be a table "
            "{lane, evidence, evidence_uri, decision_authority, review_needed, "
            "part_viii_class, packet_limited, sig_labelled_cc0} (P35.35)"
        )
    known = {
        "lane",
        "evidence",
        "evidence_uri",
        "decision_authority",
        "review_needed",
        "part_viii_class",
        "packet_limited",
        "sig_labelled_cc0",
    }
    extra = set(raw) - known
    if extra:
        raise ValueError(
            f"source {source_id!r}: redistribution block carries unknown "
            f"field(s) {sorted(extra)} — the declaration is closed-shape "
            "(P35.35); an unrecognised key never silently drops"
        )
    return SourceRedistribution(
        lane=str(raw.get("lane", "")).strip(),
        evidence=str(raw.get("evidence", "")),
        evidence_uri=str(raw.get("evidence_uri", "")),
        decision_authority=str(raw.get("decision_authority", "")),
        review_needed=bool(raw.get("review_needed", False)),
        part_viii_class=str(raw.get("part_viii_class", "")).strip(),
        packet_limited=bool(raw.get("packet_limited", False)),
        sig_labelled_cc0=bool(raw.get("sig_labelled_cc0", False)),
    )


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
        volatility_class=str(row.get("volatility_class", "")),
        volatility_basis=str(row.get("volatility_basis", "")),
        lineage=_lineage_from_row(source_id, row),
        redistribution=_redistribution_from_row(source_id, row),
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
    # P35.25: lineage upstream references are registry ids — a dangling
    # mirror_of/derived_from fails the whole load rather than resolving
    # "unclassified" for a typo'd declaration (fail-closed, §3.1).
    for record in records.values():
        upstreams = ([record.lineage.mirror_of] if record.lineage.mirror_of else []) + list(
            record.lineage.derived_from
        )
        for upstream in upstreams:
            if upstream not in records:
                raise ValueError(
                    f"source {record.id!r}: lineage upstream {upstream!r} is "
                    "not a registered source — register it or name the upstream "
                    "in lineage.origin instead (P35.25)"
                )
        ns = record.lineage.id_namespace
        if ns:
            # The namespace vocabulary is owned by db (the committed
            # id_namespaces.toml); a private space is `src:<source-id>`.
            # An undeclared token fails the load — never silently namespaced.
            from db.lineage import known_namespace  # db is a declared dep

            if not ns.startswith("src:") and not known_namespace(ns):
                raise ValueError(
                    f"source {record.id!r}: lineage.id_namespace {ns!r} is not "
                    "a declared namespace (db/data/id_namespaces.toml) — a "
                    "source-private space is 'src:<source-id>' (P35.25)"
                )
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
