# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Contribution back to the ecosystem: the human-mediated OSM suggestion workflow (§35.2).

Contribution back is a **funded architectural commitment**, not a stretch goal (P5),
and it has one non-negotiable shape: SIG proposes, a human decides. This module owns
that posture and its two compliance surfaces, as pure, tested Python ahead of
persistence (the established `tasks`/`policy.governance` pattern).

* **No direct automated OSM writes (SIG-CONTRIB-014).** There is *no* code path that
  writes to OSM. :func:`write_to_osm` exists only to refuse, and an
  :class:`AppliedEdit` cannot record SIG as the applier — the "suggestion, never a
  write" posture is structural, not a convention.
* **Human-mediated suggestion workflow (SIG-CONTRIB-015/015a).** A
  :class:`CooperativeChallenge` (a MapRoulette *cooperative* challenge,
  ``cooperativeType='tags'``) proposes a specific :class:`TagChange` — "this node has
  no ``operator``; SIG's evidence suggests ``operator=X``; decide." A mapper reviews
  each :class:`TagSuggestion` individually and applies it **in their own account**
  (:func:`apply_by_mapper`), which is exactly what keeps SIG outside the Automated
  Edits Code's scope (ADR-055 / SIG-CONTRIB-016b) and reduces the mapper's cost to
  ~one decision per device (SIG-CONTRIB-017a).
* **The changeset hashtag (SIG-CONTRIB-016e).** :data:`CHANGESET_HASHTAG` is declared
  and required on every SIG-originated edit. It is also the measurement instrument for
  the §7 leverage metric — :class:`LeverageLedger` reads *accepted* upstream changesets
  bearing the hashtag, which makes the contribution stream publicly auditable by third
  parties (including SIG's critics), the property that makes the metric credible.
* **The contribution-path licence gate (SIG-CONTRIB-016f).** :func:`build_suggestion`
  applies ``policy.licensing.assert_contribution_permitted`` *before rendering* a
  suggestion: a task built on a source whose terms do not permit deriving an OSM edit
  is blocked, never surfaced (publishing it would make SIG the proximate cause of a
  licence breach — §42.3a).
* **Per-project correction channels (SIG-CONTRIB-018).** :data:`PROJECT_CHANNELS` names
  each downstream project's *own* stated submission channel and correction format,
  rather than inventing one.
* **The Organised Editing disclosure (SIG-CONTRIB-016d/016g).**
  :func:`organised_editing_activity` loads the activity page's disclosures from data and
  asserts every field the OSM Organised Editing Guidelines require is present — including
  the hashtag, every non-standard tool and data source with usage conditions, and metrics
  stated as task outcomes, not contributor rankings.
"""

from __future__ import annotations

import tomllib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import cache
from pathlib import Path
from typing import Any, NoReturn

from policy.licensing import assert_contribution_permitted
from policy.rights import RightsRecord

from ._data import load_table

__all__ = [
    "CHANGESET_HASHTAG",
    "contribution_registered",
    "ops_config_path",
    "CooperativeType",
    "MapperDecision",
    "AutomatedOsmWriteError",
    "MissingChangesetHashtagError",
    "TagChange",
    "CooperativeChallenge",
    "TagSuggestion",
    "AppliedEdit",
    "build_suggestion",
    "apply_by_mapper",
    "cooperative_task_payload",
    "write_to_osm",
    "carries_hashtag",
    "UpstreamChangeset",
    "LeverageLedger",
    "ContributionChannel",
    "PROJECT_CHANNELS",
    "channel_for",
    "ToolDisclosure",
    "DataSourceDisclosure",
    "OrganisedEditingActivity",
    "organised_editing_activity",
    "MAPROULETTE_FIELD_CROSSWALK",
]


#: The declared changeset hashtag, required on every SIG-originated OSM edit
#: (SIG-CONTRIB-016e). It doubles as the §7 leverage-metric instrument and the
#: token by which SIG's contribution stream is third-party-auditable. Changing it
#: is a spec amendment, not an edit (SIG-ENG-003), because the metric and the
#: Organised Editing disclosure both key on it.
CHANGESET_HASHTAG = "#sig_operator_attribution"


def ops_config_path() -> Path:
    """The repo's ``ops/config.toml`` path (P21.5, ADR-067).

    The contribution-back live gate reads its ``registered`` flag from operations
    config, next to the object-store / egress budget, so an operator flips one file
    to turn the challenge push from a refusal into a real (still human-mediated)
    push once the Organised Editing activity is genuinely registered (HG-08).
    """
    return Path(__file__).resolve().parents[3] / "ops" / "config.toml"


def contribution_registered(config_path: str | Path | None = None) -> bool:
    """Whether the SIG Organised Editing activity is registered (``ops/config.toml``).

    Reads ``[tasks.contribution] registered`` and **fails closed** (``False``) when
    the file or the key is absent — an unregistered activity may not push a
    MapRoulette challenge (SIG-CONTRIB-016d, RISK-P16-14). The registration itself
    is an off-repo, human decision (HG-08): the flag records that it happened, it
    does not perform it.
    """
    path = Path(config_path) if config_path is not None else ops_config_path()
    if not path.exists():
        return False
    with path.open("rb") as fh:
        doc = tomllib.load(fh)
    section = doc.get("tasks", {})
    if isinstance(section, dict):
        contribution = section.get("contribution", {})
        if isinstance(contribution, dict):
            return bool(contribution.get("registered", False))
    return False


#: How the MapRoulette cooperative-challenge object model maps onto SIG's
#: requirements (SIG-CONTRIB-015a, SC-15). Documentation, asserted by a test so it
#: does not drift from the fields this module actually uses.
MAPROULETTE_FIELD_CROSSWALK: dict[str, str] = {
    "changeset_hashtag": "checkinComment",
    "originating_tool": "checkinSource",
    "evidence_to_mapper": "instruction",
    "leverage_metric": "completionMetrics",
    "task_retirement": "isArchived",
    "cooperative_capability": "cooperativeType",
}


class CooperativeType(StrEnum):
    """The MapRoulette ``cooperativeType`` (SIG-CONTRIB-015a).

    ``TAGS`` is the decisive capability: a cooperative challenge proposes a specific
    tag change the mapper accepts, rejects, or edits — rather than sending them to
    edit freehand. That individual review is what keeps SIG outside the Automated
    Edits Code's scope (SIG-CONTRIB-016b).
    """

    TAGS = "tags"


class MapperDecision(StrEnum):
    """What a human mapper decided about a suggestion, in their own account (§35.2).

    A suggestion is a proposal; the mapper exercises judgment. ``EDITED`` captures
    the case where they applied a *different* value than SIG proposed — proof the
    review is real and not a rubber stamp.
    """

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"


#: The decisions that result in an actual upstream edit (and so must carry the
#: hashtag on their changeset). A rejection writes nothing.
_APPLYING_DECISIONS: frozenset[MapperDecision] = frozenset(
    {MapperDecision.ACCEPTED, MapperDecision.EDITED}
)


class AutomatedOsmWriteError(RuntimeError):
    """Raised on any attempt at a direct automated write to OSM (SIG-CONTRIB-014)."""


class MissingChangesetHashtagError(ValueError):
    """Raised when a SIG-originated edit/suggestion lacks the changeset hashtag (016e)."""


def carries_hashtag(comment: str, *, hashtag: str = CHANGESET_HASHTAG) -> bool:
    """Whether a changeset comment carries the required hashtag (SIG-CONTRIB-016e)."""
    return hashtag in comment


def _require_hashtag(comment: str, *, what: str) -> None:
    if not carries_hashtag(comment):
        raise MissingChangesetHashtagError(
            f"{what} MUST carry the changeset hashtag {CHANGESET_HASHTAG!r} "
            "(SIG-CONTRIB-016e); it is required on every SIG-originated edit and is how "
            "the §7 leverage metric reads accepted contributions"
        )


@dataclass(frozen=True)
class TagChange:
    """A single proposed OSM tag change — the payload of a cooperative suggestion.

    Names the element and the exact tag SIG proposes (e.g. ``operator=Springfield PD``
    on a node with no ``operator``). ``current_value`` is ``None`` when the tag is
    absent — the orphaned-device case (§33.2 #5) that is the highest-value
    contribution SIG can make upstream (SIG-CONTRIB-017).
    """

    element_type: str
    element_id: int
    tag_key: str
    proposed_value: str
    current_value: str | None = None

    def __post_init__(self) -> None:
        if self.element_type not in {"node", "way", "relation"}:
            raise ValueError(
                f"OSM element_type must be node/way/relation, got {self.element_type!r}"
            )
        if not self.tag_key or not self.proposed_value:
            raise ValueError("a TagChange MUST name a tag_key and a proposed_value")


@dataclass(frozen=True)
class CooperativeChallenge:
    """A MapRoulette cooperative challenge — the verified human-mediated mechanism (015a).

    Carries the fields SIG's requirements map onto (see
    :data:`MAPROULETTE_FIELD_CROSSWALK`). ``checkin_comment`` MUST carry the changeset
    hashtag (SIG-CONTRIB-016e); ``cooperative_type`` is ``TAGS`` because the specific
    tag-change review is what keeps SIG compliant (SIG-CONTRIB-016b). It proposes; it
    does not write — a challenge holds :class:`TagSuggestion`s a mapper works one by one.
    """

    challenge_id: str
    name: str
    instruction: str
    checkin_comment: str
    checkin_source: str = "SIG"
    cooperative_type: CooperativeType = CooperativeType.TAGS
    enabled: bool = True
    is_archived: bool = False

    def __post_init__(self) -> None:
        if not self.challenge_id:
            raise ValueError("a CooperativeChallenge MUST carry a challenge_id")
        if self.cooperative_type is not CooperativeType.TAGS:
            raise ValueError(
                "SIG's contribution challenges MUST be cooperativeType=tags so each change "
                "is individually reviewed (SIG-CONTRIB-015a/016b)"
            )
        _require_hashtag(self.checkin_comment, what="a CooperativeChallenge checkin_comment")


@dataclass(frozen=True)
class TagSuggestion:
    """One proposed tag change surfaced to a mapper — a suggestion, never a write.

    Built by :func:`build_suggestion`, which applies the contribution-path licence
    gate first (SIG-CONTRIB-016f). ``instruction`` and ``evidence_ref`` surface the
    supporting evidence (a contract, a record) to the mapper so the decision is one
    reviewable unit (SIG-CONTRIB-017a). ``checkin_comment`` carries the hashtag.
    """

    suggestion_id: str
    change: TagChange
    instruction: str
    evidence_ref: str
    source_id: str
    checkin_comment: str

    def __post_init__(self) -> None:
        if not self.suggestion_id:
            raise ValueError("a TagSuggestion MUST carry a suggestion_id")
        if not self.evidence_ref:
            raise ValueError(
                "a TagSuggestion MUST surface its supporting evidence to the mapper "
                "(SIG-CONTRIB-015/017a)"
            )
        _require_hashtag(self.checkin_comment, what="a TagSuggestion checkin_comment")


@dataclass(frozen=True)
class AppliedEdit:
    """The record of a human mapper applying (or rejecting) a suggestion (SIG-CONTRIB-015).

    A mapper reviews a :class:`TagSuggestion` and acts **in their own account**, with
    their own judgment. ``mapper_account`` is that person's account; there is no field
    by which SIG could be the applier — the suggestion-not-write posture is structural
    (SIG-CONTRIB-014). An applying decision (accepted/edited) MUST carry the hashtag on
    its changeset; a rejection writes nothing and needs none.
    """

    suggestion_id: str
    mapper_account: str
    decision: MapperDecision
    changeset_comment: str = ""
    changeset_id: str | None = None
    applied_value: str | None = None

    def __post_init__(self) -> None:
        if not self.mapper_account:
            raise ValueError(
                "an AppliedEdit MUST name the mapper's own account (SIG-CONTRIB-015); "
                "SIG never applies an edit itself (SIG-CONTRIB-014)"
            )
        if self.mapper_account.strip().upper() == "SIG":
            raise AutomatedOsmWriteError(
                "SIG MUST NOT be the account that applies an OSM edit (SIG-CONTRIB-014); "
                "a human mapper applies each change in their own account"
            )
        if self.decision in _APPLYING_DECISIONS:
            _require_hashtag(self.changeset_comment, what="an applied edit's changeset")

    @property
    def wrote_upstream(self) -> bool:
        """Whether this decision resulted in an actual upstream edit."""
        return self.decision in _APPLYING_DECISIONS


def build_suggestion(
    *,
    suggestion_id: str,
    change: TagChange,
    instruction: str,
    evidence_ref: str,
    rights: RightsRecord,
    checkin_comment: str | None = None,
    registry: Mapping[str, Any] | None = None,
) -> TagSuggestion:
    """Build a contribution suggestion, applying the licence gate first (016f).

    The task builder MUST check, *before rendering*, that the source's terms permit
    deriving an OSM edit — so this calls
    :func:`policy.licensing.assert_contribution_permitted` on ``rights`` and lets its
    :class:`policy.licensing.ContributionGateClosed` propagate: a task built on an
    incompatible source is never constructed. ``checkin_comment`` defaults to a
    hashtag-bearing comment naming the proposed tag.
    """
    assert_contribution_permitted(rights, registry=registry)
    comment = checkin_comment or (
        f"{change.tag_key}={change.proposed_value} from public records {CHANGESET_HASHTAG}"
    )
    return TagSuggestion(
        suggestion_id=suggestion_id,
        change=change,
        instruction=instruction,
        evidence_ref=evidence_ref,
        source_id=rights.source_id,
        checkin_comment=comment,
    )


def apply_by_mapper(
    suggestion: TagSuggestion,
    *,
    mapper_account: str,
    decision: MapperDecision,
    changeset_id: str | None = None,
    applied_value: str | None = None,
) -> AppliedEdit:
    """Record a human mapper applying `suggestion` in their own account (SIG-CONTRIB-015).

    This is the *only* way a suggestion becomes an upstream edit: a person decides.
    The changeset comment is inherited from the suggestion (carrying the hashtag) for
    an applying decision; a rejection writes nothing.
    """
    comment = suggestion.checkin_comment if decision in _APPLYING_DECISIONS else ""
    return AppliedEdit(
        suggestion_id=suggestion.suggestion_id,
        mapper_account=mapper_account,
        decision=decision,
        changeset_comment=comment,
        changeset_id=changeset_id,
        applied_value=applied_value,
    )


def cooperative_task_payload(suggestion: TagSuggestion) -> dict[str, Any]:
    """Render a suggestion as a MapRoulette cooperative-challenge task payload.

    This is the OSM/DeFlock per-project **correction export format** (SIG-CONTRIB-018):
    a cooperative ``tags`` operation proposing the specific change, with SIG's evidence
    in the ``instruction`` and the changeset hashtag in ``checkinComment``. It is a
    *proposal* a mapper accepts, rejects, or edits — never an applied write
    (SIG-CONTRIB-014/015). It uses OSM's own stated channel (MapRoulette), not an
    invented one (SIG-CONTRIB-018).
    """
    change = suggestion.change
    return {
        "cooperativeType": CooperativeType.TAGS.value,
        "checkinComment": suggestion.checkin_comment,
        "checkinSource": "SIG",
        "instruction": suggestion.instruction,
        "operations": [
            {
                "operationType": "modifyElement",
                "element": {"type": change.element_type, "id": change.element_id},
                "set": {change.tag_key: change.proposed_value},
            }
        ],
        "evidence_ref": suggestion.evidence_ref,
    }


def write_to_osm(*_args: object, **_kwargs: object) -> NoReturn:
    """Always refuse: SIG performs NO direct automated writes to OSM (SIG-CONTRIB-014).

    There is deliberately no implementation. Contribution back goes through the
    human-mediated suggestion workflow (:func:`build_suggestion` →
    :func:`apply_by_mapper`); a mapper applies every change in their own account.
    """
    raise AutomatedOsmWriteError(
        "SIG MUST NOT perform direct automated writes to OSM (SIG-CONTRIB-014); "
        "build a suggestion and let a human mapper apply it in their own account "
        "(SIG-CONTRIB-015)"
    )


# --------------------------------------------------------------------------- #
# The §7 leverage metric (SIG-CONTRIB-016e; §7 / §32.6 SIG-METRIC-011)          #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class UpstreamChangeset:
    """An observed upstream OSM changeset — the public signal the metric reads.

    A third party could reconstruct the same count from OSM's public changeset feed
    by filtering on the hashtag, which is precisely the auditability the metric needs
    (SIG-CONTRIB-016e). ``accepted`` records whether the change survived upstream
    (was not reverted).
    """

    changeset_id: str
    comment: str
    accepted: bool = True


class LeverageLedger:
    """The §7 leverage metric: SIG-originated operator-attribution suggestions accepted upstream.

    "Count of SIG-originated operator-attribution suggestions accepted upstream"
    (§7) is otherwise unmeasurable except by inferring SIG's influence from tag-count
    deltas. The ledger measures it directly by reading *accepted* changesets that carry
    :data:`CHANGESET_HASHTAG` (SIG-CONTRIB-016e) — a changeset without the hashtag is
    not counted, and a reverted (``accepted=False``) one is not either.
    """

    def __init__(self, *, hashtag: str = CHANGESET_HASHTAG) -> None:
        self._hashtag = hashtag
        self._changesets: dict[str, UpstreamChangeset] = {}

    @property
    def hashtag(self) -> str:
        """The changeset hashtag this ledger keys its metric on (SIG-CONTRIB-016e)."""
        return self._hashtag

    def record(self, changeset: UpstreamChangeset) -> None:
        """Observe an upstream changeset (idempotent by ``changeset_id``)."""
        self._changesets[changeset.changeset_id] = changeset

    def record_all(self, changesets: Iterable[UpstreamChangeset]) -> None:
        for changeset in changesets:
            self.record(changeset)

    def accepted_operator_attributions(self) -> int:
        """The §7 metric: how many hashtag-bearing changesets were accepted upstream."""
        return sum(
            1
            for cs in self._changesets.values()
            if cs.accepted and carries_hashtag(cs.comment, hashtag=self._hashtag)
        )

    def attributed_changeset_ids(self) -> frozenset[str]:
        """Every observed changeset carrying the hashtag (accepted or later reverted)."""
        return frozenset(
            cs.changeset_id
            for cs in self._changesets.values()
            if carries_hashtag(cs.comment, hashtag=self._hashtag)
        )


# --------------------------------------------------------------------------- #
# Per-project correction channels (SIG-CONTRIB-018)                            #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ContributionChannel:
    """A downstream project's OWN stated correction/submission channel (SIG-CONTRIB-018).

    SIG maintains a per-project correction export format and uses each project's own
    stated channel rather than inventing one.
    """

    project: str
    mechanism: str
    submission_url: str
    export_format: str
    notes: str = ""


#: The per-project correction channels (SIG-CONTRIB-018). OSM (and DeFlock, which
#: routes device observations to OSM, SIG-CONTRIB-004) go through the MapRoulette
#: cooperative challenge; EFF's Atlas uses its own correction channel (§35.3, N8).
PROJECT_CHANNELS: dict[str, ContributionChannel] = {
    "openstreetmap": ContributionChannel(
        project="openstreetmap",
        mechanism="maproulette_cooperative_challenge",
        submission_url="https://maproulette.org/",
        export_format="maproulette_cooperative_tags",
        notes="Human mapper applies each tag change in their own account (SIG-CONTRIB-015).",
    ),
    "deflock": ContributionChannel(
        project="deflock",
        mechanism="maproulette_cooperative_challenge",
        submission_url="https://maproulette.org/",
        export_format="maproulette_cooperative_tags",
        notes="Device observations route to OSM/DeFlock upstream (SIG-CONTRIB-004, N7).",
    ),
    "atlas": ContributionChannel(
        project="atlas",
        mechanism="atlas_correction_submission",
        submission_url="https://atlasofsurveillance.org/",
        export_format="atlas_deployment_correction",
        notes="Deployment corrections via the Atlas's own submission channel (§35.3, N8).",
    ),
}


class UnknownProjectError(KeyError):
    """Raised when a correction is requested for a project SIG has no channel for."""


def channel_for(project: str) -> ContributionChannel:
    """The correction channel for `project`, or raise (SIG-CONTRIB-018)."""
    try:
        return PROJECT_CHANNELS[project]
    except KeyError:
        raise UnknownProjectError(
            f"no correction channel for project {project!r}; SIG uses each project's own "
            "stated submission channel and does not invent one (SIG-CONTRIB-018)"
        ) from None


# --------------------------------------------------------------------------- #
# The Organised Editing activity disclosure (SIG-CONTRIB-016d/016g; SIG-LIC-007) #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class ToolDisclosure:
    """A non-standard tool used, with its usage conditions and a link (SIG-CONTRIB-016d)."""

    name: str
    usage_conditions: str
    url: str


@dataclass(frozen=True)
class DataSourceDisclosure:
    """A data source feeding a contribution, with its licence and conditions (016d/LIC-007c)."""

    name: str
    license: str
    usage_conditions: str
    url: str


@dataclass(frozen=True)
class OrganisedEditingActivity:
    """The published + registered Organised Editing activity page's disclosures (016d/016g).

    Escaping the Automated Edits Code does not escape the Organised Editing Guidelines
    (SIG-CONTRIB-016d): a SIG-run challenge directing volunteers at the backlog is
    squarely in scope. This value object carries every disclosure the guidelines
    require, loaded from data, so :func:`organised_editing_activity` can assert nothing
    is missing. ``metrics`` is stated as task **outcomes**, not contributor rankings
    (SIG-CONTRIB-016g; §33.6). ``account_holder`` / ``maproulette_api_docs`` discharge
    SIG-CONTRIB-015b.
    """

    version: str
    coordinating_org: str
    contact: str
    hashtag: str
    goal: str
    timeframe: str
    tools: tuple[ToolDisclosure, ...]
    data_sources: tuple[DataSourceDisclosure, ...]
    participating_accounts: tuple[str, ...]
    metrics: str
    account_holder: str
    maproulette_api_docs: str
    attribution_expectation: str
    registered: bool
    activity_page: str
    activity_page_wiki: str

    def __post_init__(self) -> None:
        missing = [
            name
            for name in (
                "coordinating_org",
                "contact",
                "hashtag",
                "goal",
                "timeframe",
                "metrics",
                "account_holder",
                "maproulette_api_docs",
                "attribution_expectation",
                "activity_page",
                "activity_page_wiki",
            )
            if not str(getattr(self, name)).strip()
        ]
        if missing:
            raise ValueError(
                f"the Organised Editing activity disclosure is missing required fields "
                f"{missing} (SIG-CONTRIB-016d)"
            )
        if self.hashtag != CHANGESET_HASHTAG:
            raise ValueError(
                f"the activity hashtag {self.hashtag!r} MUST equal the declared changeset "
                f"hashtag {CHANGESET_HASHTAG!r} (SIG-CONTRIB-016e)"
            )
        if not self.tools:
            raise ValueError("the disclosure MUST list every non-standard tool (SIG-CONTRIB-016d)")
        if not self.data_sources:
            raise ValueError(
                "the disclosure MUST list every data source and its usage conditions "
                "(SIG-CONTRIB-016d; SIG-LIC-007c)"
            )
        if not self.registered:
            raise ValueError(
                "the activity page MUST be registered in the Organised Editing activities "
                "list (SIG-CONTRIB-016d)"
            )
        # SIG-CONTRIB-016g: metrics are task outcomes, not contributor rankings.
        lowered = self.metrics.lower()
        if "ranking" in lowered or "leaderboard" in lowered:
            if "no " not in lowered and "not " not in lowered:
                raise ValueError(
                    "the metrics disclosure MUST state task outcomes, not contributor "
                    "rankings (SIG-CONTRIB-016g; §33.6)"
                )

    def discloses_data_source_conditions(self) -> bool:
        """Whether every data source carries a licence and usage conditions (016d/LIC-007c)."""
        return all(
            bool(ds.license.strip()) and bool(ds.usage_conditions.strip())
            for ds in self.data_sources
        )


def _tools(rows: list[dict[str, Any]]) -> tuple[ToolDisclosure, ...]:
    return tuple(
        ToolDisclosure(
            name=str(r["name"]),
            usage_conditions=str(r["usage_conditions"]),
            url=str(r.get("url", "")),
        )
        for r in rows
    )


def _data_sources(rows: list[dict[str, Any]]) -> tuple[DataSourceDisclosure, ...]:
    return tuple(
        DataSourceDisclosure(
            name=str(r["name"]),
            license=str(r["license"]),
            usage_conditions=str(r["usage_conditions"]),
            url=str(r.get("url", "")),
        )
        for r in rows
    )


@cache
def organised_editing_activity() -> OrganisedEditingActivity:
    """The seeded Organised Editing activity disclosure (SIG-CONTRIB-016d/016e/016g).

    Loads ``data/organised_editing.toml`` and constructs the value object, whose
    ``__post_init__`` refuses a disclosure missing any required field — so an
    incomplete activity page cannot be shipped silently.
    """
    data = load_table("organised_editing")
    activity = data["activity"]
    return OrganisedEditingActivity(
        version=str(activity["version"]),
        coordinating_org=str(activity["coordinating_org"]),
        contact=str(activity["contact"]),
        hashtag=str(activity["hashtag"]),
        goal=str(activity["goal"]),
        timeframe=str(activity["timeframe"]),
        tools=_tools(activity["tools"]),
        data_sources=_data_sources(activity["data_sources"]),
        participating_accounts=tuple(str(a) for a in activity["participating_accounts"]),
        metrics=str(activity["metrics"]),
        account_holder=str(activity["account_holder"]),
        maproulette_api_docs=str(activity["maproulette_api_docs"]),
        attribution_expectation=str(activity["attribution_expectation"]),
        registered=bool(activity["registered"]),
        activity_page=str(activity["activity_page"]),
        activity_page_wiki=str(activity["activity_page_wiki"]),
    )
