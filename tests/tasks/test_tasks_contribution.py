# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Contribution back to the ecosystem: the human-mediated OSM suggestion workflow
(§35.2, SIG-CONTRIB-014/015/015a/015b/016d/016e/016f/016g/018).

AC1 (014/015): no unattended write path; a suggestion requires a human application
step. AC4 (016e): the changeset hashtag is declared, required on SIG edits, and
wired to the §7 leverage metric. AC5 (016f): the contribution-path licence gate
blocks a task built on a deliberately-incompatible source. AC3 (016d): the
Organised Editing activity page is published + registered and discloses tools and
data sources with their usage conditions.
"""

from __future__ import annotations

from datetime import date

import pytest
from policy.licensing import ContributionGateClosed
from policy.rights import RightsRecord

from tasks import contribution as C


def _rights(source_id: str, spdx: str, **kw: object) -> RightsRecord:
    defaults: dict[str, object] = dict(
        attribution="attr",
        redistributable=True,
        derivative_permitted=True,
        terms_url="https://example/terms",
        retrieval_date=date(2026, 1, 1),
    )
    defaults.update(kw)
    return RightsRecord(source_id=source_id, spdx=spdx, **defaults)  # type: ignore[arg-type]


def _change() -> C.TagChange:
    return C.TagChange(
        element_type="node",
        element_id=123,
        tag_key="operator",
        proposed_value="Springfield Police Department",
        current_value=None,
    )


def _suggestion() -> C.TagSuggestion:
    return C.build_suggestion(
        suggestion_id="s1",
        change=_change(),
        instruction="SIG evidence: a 2025 procurement contract names the operator.",
        evidence_ref="evidence://contract/abc",
        rights=_rights("osm_overpass", "ODbL-1.0"),
    )


# --- AC1 / SIG-CONTRIB-014: no direct automated OSM writes exist ---------------


def test_no_automated_osm_write_path_exists() -> None:
    with pytest.raises(C.AutomatedOsmWriteError):
        C.write_to_osm(_change())


def test_sig_can_never_be_the_account_that_applies_an_edit() -> None:
    # SIG-CONTRIB-014: an AppliedEdit naming SIG as the applier is unrepresentable.
    with pytest.raises(C.AutomatedOsmWriteError):
        C.AppliedEdit(
            suggestion_id="s1",
            mapper_account="SIG",
            decision=C.MapperDecision.ACCEPTED,
            changeset_comment=f"operator=X {C.CHANGESET_HASHTAG}",
        )


# --- AC1 / SIG-CONTRIB-015: contribution requires a human application step ------


def test_suggestion_becomes_an_edit_only_when_a_human_mapper_applies_it() -> None:
    suggestion = _suggestion()
    applied = C.apply_by_mapper(
        suggestion,
        mapper_account="jane_mapper",
        decision=C.MapperDecision.ACCEPTED,
        changeset_id="cs42",
    )
    assert applied.mapper_account == "jane_mapper"
    assert applied.wrote_upstream is True
    # The human's changeset inherits the hashtag (SIG-CONTRIB-016e).
    assert C.carries_hashtag(applied.changeset_comment)


def test_mapper_can_reject_a_suggestion_and_nothing_is_written() -> None:
    applied = C.apply_by_mapper(
        _suggestion(), mapper_account="jane_mapper", decision=C.MapperDecision.REJECTED
    )
    assert applied.wrote_upstream is False
    assert applied.changeset_comment == ""


def test_mapper_can_edit_to_a_different_value_exercising_judgment() -> None:
    applied = C.apply_by_mapper(
        _suggestion(),
        mapper_account="jane_mapper",
        decision=C.MapperDecision.EDITED,
        applied_value="Springfield PD",
    )
    assert applied.wrote_upstream is True
    assert applied.applied_value == "Springfield PD"


def test_cooperative_challenge_is_tags_typed_and_carries_the_hashtag() -> None:
    challenge = C.CooperativeChallenge(
        challenge_id="ch1",
        name="SIG operator attribution",
        instruction="Decide whether SIG's evidence supports the operator tag.",
        checkin_comment=f"operator attribution {C.CHANGESET_HASHTAG}",
    )
    assert challenge.cooperative_type is C.CooperativeType.TAGS
    with pytest.raises(ValueError):
        C.CooperativeChallenge(
            challenge_id="ch2",
            name="bad",
            instruction="x",
            checkin_comment="no hashtag here",
        )


# --- AC4 / SIG-CONTRIB-016e: the hashtag is required on every SIG edit ----------


def test_declared_hashtag_is_required_on_a_sig_suggestion() -> None:
    assert C.CHANGESET_HASHTAG.startswith("#")
    # A suggestion the builder produces always carries the hashtag.
    assert C.carries_hashtag(_suggestion().checkin_comment)
    # And an applying edit without it is refused (SIG-CONTRIB-016e).
    with pytest.raises(C.MissingChangesetHashtagError):
        C.AppliedEdit(
            suggestion_id="s1",
            mapper_account="jane_mapper",
            decision=C.MapperDecision.ACCEPTED,
            changeset_comment="operator=X (forgot the hashtag)",
        )


# --- AC4 / SIG-CONTRIB-016e + §7: the leverage metric reads accepted edits ------


def test_leverage_metric_reads_accepted_edits_from_the_hashtag() -> None:
    ledger = C.LeverageLedger()
    ledger.record_all(
        [
            C.UpstreamChangeset("cs1", f"operator=A {C.CHANGESET_HASHTAG}", accepted=True),
            C.UpstreamChangeset("cs2", f"operator=B {C.CHANGESET_HASHTAG}", accepted=True),
            # No hashtag → not a SIG-originated contribution, not counted.
            C.UpstreamChangeset("cs3", "operator=C some other edit", accepted=True),
            # Hashtag but reverted upstream → not an accepted contribution.
            C.UpstreamChangeset("cs4", f"operator=D {C.CHANGESET_HASHTAG}", accepted=False),
        ]
    )
    assert ledger.accepted_operator_attributions() == 2
    assert ledger.attributed_changeset_ids() == frozenset({"cs1", "cs2", "cs4"})


def test_a_task_originated_suggestion_flows_into_the_metric_when_accepted() -> None:
    # End-to-end: a suggestion the task builder produced, applied by a mapper,
    # shows up in the §7 metric because the mapper's changeset carries the hashtag.
    applied = C.apply_by_mapper(
        _suggestion(),
        mapper_account="jane_mapper",
        decision=C.MapperDecision.ACCEPTED,
        changeset_id="cs99",
    )
    ledger = C.LeverageLedger()
    ledger.record(
        C.UpstreamChangeset(
            applied.changeset_id or "cs99", applied.changeset_comment, accepted=True
        )
    )
    assert ledger.accepted_operator_attributions() == 1


# --- AC5 / SIG-CONTRIB-016f: the contribution-path licence gate blocks a task ---


def test_licence_gate_blocks_a_task_on_an_incompatible_source() -> None:
    # A CC-BY-SA-4.0 source is not relicensable to OSM's ODbL-1.0; the builder MUST
    # refuse to render a suggestion from it (SIG-CONTRIB-016f). No task is produced.
    with pytest.raises(ContributionGateClosed):
        C.build_suggestion(
            suggestion_id="s2",
            change=_change(),
            instruction="x",
            evidence_ref="evidence://portal/xyz",
            rights=_rights("portal", "CC-BY-SA-4.0"),
        )


def test_licence_gate_blocks_a_no_derivatives_source() -> None:
    with pytest.raises(ContributionGateClosed):
        C.build_suggestion(
            suggestion_id="s3",
            change=_change(),
            instruction="x",
            evidence_ref="evidence://feed/1",
            rights=_rights("proprietary", "CC-BY-4.0", derivative_permitted=False),
        )


def test_licence_gate_permits_a_compatible_source() -> None:
    suggestion = C.build_suggestion(
        suggestion_id="s4",
        change=_change(),
        instruction="x",
        evidence_ref="evidence://record/1",
        rights=_rights("gov_record", "CC0-1.0"),
    )
    assert suggestion.source_id == "gov_record"


# --- SIG-CONTRIB-018: per-project correction channels ---------------------------


def test_per_project_channels_use_each_projects_own_channel() -> None:
    osm = C.channel_for("openstreetmap")
    assert osm.mechanism == "maproulette_cooperative_challenge"
    atlas = C.channel_for("atlas")
    assert atlas.mechanism == "atlas_correction_submission"
    assert atlas.export_format != osm.export_format
    with pytest.raises(C.UnknownProjectError):
        C.channel_for("nonexistent_project")


def test_osm_correction_export_format_is_a_cooperative_proposal() -> None:
    # SIG-CONTRIB-018/015a: the OSM per-project correction export format is a
    # MapRoulette cooperative-tags proposal, carrying the hashtag and the evidence.
    payload = C.cooperative_task_payload(_suggestion())
    assert payload["cooperativeType"] == "tags"
    assert C.carries_hashtag(payload["checkinComment"])
    assert payload["operations"][0]["set"] == {"operator": "Springfield Police Department"}
    assert payload["operations"][0]["element"] == {"type": "node", "id": 123}
    assert payload["evidence_ref"] == "evidence://contract/abc"


# --- AC3 / SIG-CONTRIB-016d/016g/015b: the Organised Editing disclosure ---------


def test_activity_page_discloses_tools_and_data_sources_with_conditions() -> None:
    activity = C.organised_editing_activity()
    assert activity.registered is True
    assert activity.hashtag == C.CHANGESET_HASHTAG
    assert activity.coordinating_org and activity.contact
    assert activity.tools, "must disclose non-standard tools (SIG-CONTRIB-016d)"
    assert activity.data_sources, "must disclose data sources (SIG-CONTRIB-016d)"
    assert activity.discloses_data_source_conditions()
    # SIG-CONTRIB-015b: account holder + located MapRoulette API docs disclosed.
    assert activity.account_holder
    assert activity.maproulette_api_docs
    # SIG-CONTRIB-016g: metrics are task outcomes, not contributor rankings.
    assert "outcome" in activity.metrics.lower()


def test_activity_disclosure_refuses_a_mismatched_hashtag() -> None:
    with pytest.raises(ValueError):
        C.OrganisedEditingActivity(
            version="v1",
            coordinating_org="SIG",
            contact="c@example",
            hashtag="#wrong_hashtag",
            goal="g",
            timeframe="t",
            tools=(C.ToolDisclosure("t", "c", "u"),),
            data_sources=(C.DataSourceDisclosure("d", "CC0-1.0", "c", "u"),),
            participating_accounts=("acct",),
            metrics="task outcomes",
            account_holder="h",
            maproulette_api_docs="u",
            attribution_expectation="a",
            registered=True,
            activity_page="p",
            activity_page_wiki="w",
        )


def test_activity_disclosure_refuses_contributor_rankings_as_metrics() -> None:
    with pytest.raises(ValueError):
        C.OrganisedEditingActivity(
            version="v1",
            coordinating_org="SIG",
            contact="c@example",
            hashtag=C.CHANGESET_HASHTAG,
            goal="g",
            timeframe="t",
            tools=(C.ToolDisclosure("t", "c", "u"),),
            data_sources=(C.DataSourceDisclosure("d", "CC0-1.0", "c", "u"),),
            participating_accounts=("acct",),
            metrics="a contributor leaderboard ranking mappers by edit volume",
            account_holder="h",
            maproulette_api_docs="u",
            attribution_expectation="a",
            registered=True,
            activity_page="p",
            activity_page_wiki="w",
        )


def test_maproulette_crosswalk_is_documented() -> None:
    # SIG-CONTRIB-015a: the hashtag maps to checkinComment; the cooperative
    # capability is cooperativeType.
    assert C.MAPROULETTE_FIELD_CROSSWALK["changeset_hashtag"] == "checkinComment"
    assert C.MAPROULETTE_FIELD_CROSSWALK["cooperative_capability"] == "cooperativeType"
