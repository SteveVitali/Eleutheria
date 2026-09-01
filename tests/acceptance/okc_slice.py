# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The P06.1 vertical slice: Oklahoma City (OKCPD Flock ALPR) carried from
evidence to a rendered dossier.

This module assembles the slice graph from the committed evidence fixtures
(``fixtures/okc_sources.json``), runs the minimal count reconciliation
(``reconcile``), builds the §39.2 dossier (``exports.dossier``), and exposes the
J-1 traversal (§2.2, Appendix D). It is slice-scoped fixture/assembly code for the
acceptance query; the production graph→dossier assembly is P15.2.

Every material fact resolves to a *document at a locator*: each fixture artifact's
bytes are content-addressed (a real ``capture_digest``), its ``url`` is the
``stable_locator``, and each claim's ``locator`` pins the supporting text span.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from evidence.digest import multihash
from exports.dossier import (
    DocumentRef as UiDoc,
)
from exports.dossier import (
    Dossier,
    Figure,
    Gap,
    Reconciliation,
    ReconClaim,
    Row,
    Section,
)
from reconcile.counts import reconcile_as_single_count, reconcile_counts
from reconcile.model import (
    POLICY_CONFIGURATION_DIVERGENCE,
    Contradiction,
    CountClaim,
    CountReconciliation,
    CountResolution,
    Evidence,
)

AS_OF = date(2026, 9, 1)
JURISDICTION = "Oklahoma City, Oklahoma"
AGENCY = "Oklahoma City Police Department (OKCPD)"
DEPLOYMENT_ID = "sig:deployment:okc-okcpd-flock"
PERMALINK = "https://sig-project.org/dossier/okc-okcpd-flock?as_of=2026-09-01"

_FIXTURE = Path(__file__).parent / "fixtures" / "okc_sources.json"


# --- evidence layer -----------------------------------------------------------


@dataclass(frozen=True)
class Artifact:
    artifact_id: str
    source_id: str
    source_family: str
    genre: str
    reliability: str
    artifact_type: str
    url: str
    retrieved_at: str
    title: str
    text: str
    capture_digest: str


def _load_artifacts() -> dict[str, Artifact]:
    raw = json.loads(_FIXTURE.read_text())
    out: dict[str, Artifact] = {}
    for a in raw["artifacts"]:
        # Content-address the artifact's canonical bytes: a real capture digest so
        # the evidence genuinely resolves to a stored document (§17, §D.4).
        digest = multihash(json.dumps(a, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        out[a["artifact_id"]] = Artifact(capture_digest=digest, **a)
    return out


class SliceEvidence:
    """Builds document-at-locator evidence from the committed artifacts."""

    def __init__(self) -> None:
        self.artifacts = _load_artifacts()

    def for_quote(self, artifact_id: str, quote: str) -> Evidence:
        art = self.artifacts[artifact_id]
        start = art.text.find(quote)
        if start < 0:
            raise AssertionError(
                f"quote {quote!r} not found in artifact {artifact_id!r} — "
                "the locator must pin a real span in the captured document"
            )
        return Evidence(
            source_id=art.source_id,
            source_family=art.source_family,
            artifact_type=art.artifact_type,
            stable_locator=art.url,
            capture_digest=art.capture_digest,
            locator={"quote": quote, "text_span": [start, start + len(quote)]},
            excerpt=quote,
        )

    def genre(self, artifact_id: str) -> str:
        return self.artifacts[artifact_id].genre

    def reliability(self, artifact_id: str) -> str:
        return self.artifacts[artifact_id].reliability


# --- the slice graph ----------------------------------------------------------


@dataclass(frozen=True)
class Fact:
    """A single non-count material fact in the graph, with its evidence."""

    key: str
    label: str
    value: object | None
    evidence: Evidence | None = None
    status: str = "known"  # known | not_researched | searched_not_found
    note: str = ""


@dataclass(frozen=True)
class PhysicalAsset:
    asset_id: str
    label: str
    operator: str | None  # None => unknown operator (§29.2 attribution gap)
    evidence: Evidence


@dataclass
class SliceGraph:
    jurisdiction: str
    agency: str
    deployment_id: str
    reconciliation: CountReconciliation
    count_claims: list[CountClaim]
    facts: dict[str, list[Fact]]  # keyed by dossier section id
    assets: list[PhysicalAsset]
    contradictions: list[Contradiction]
    conflation: Contradiction  # the deliberate PREDICATE_CONFLATION demonstration
    evidence: SliceEvidence


def build_slice() -> SliceGraph:
    ev = SliceEvidence()

    # --- count claims (§29.1): six distinct predicates -----------------------
    def cc(
        basis: str,
        value: int,
        artifact_id: str,
        observed: date,
        *,
        genre: str | None = None,
        structured_exact: bool = False,
        scope: str | None = None,
        quote: str | None = None,
    ) -> CountClaim:
        return CountClaim(
            count_basis=basis,
            value=value,
            reliability=ev.reliability(artifact_id),
            integrity="I1",
            observed_at=observed,
            genre=genre or ev.genre(artifact_id),
            evidence=ev.for_quote(artifact_id, quote if quote is not None else str(value)),
            structured_exact=structured_exact,
            scope_note=scope,
        )

    count_claims = [
        cc("contracted", 90, "okc-contract-c241032", date(2023, 1, 1), quote="90 cameras"),
        cc(
            "active",
            90,
            "okc-bacy-count-2026-08-18",
            date(2026, 8, 18),
            quote="OKCPD has 90 cameras",
        ),
        cc(
            "mapped",
            299,
            "okc-deflock-map",
            date(2026, 8, 20),
            structured_exact=True,
            scope="metro",
            quote="299",
        ),
        # within-predicate disagreement (AC6): DeFlock ~299 vs Chief Bacy ~190.
        cc(
            "claimed",
            299,
            "okc-deflock-map",
            date(2026, 8, 20),
            genre="news_article",
            scope="metro",
            quote="299",
        ),
        cc(
            "claimed",
            190,
            "okc-bacy-count-2026-08-18",
            date(2026, 8, 18),
            genre="news_article",
            scope="city limits",
            quote="businesses own around 100 within city limits",
        ),
    ]
    reconciliation = reconcile_counts(DEPLOYMENT_ID, count_claims, as_of=AS_OF)

    # the deliberate conflation §29.1 forbids: contracted 90 vs mapped 299 as ONE count
    conflation = reconcile_as_single_count(
        DEPLOYMENT_ID,
        [c for c in count_claims if c.count_basis in ("contracted", "mapped")],
    )
    assert conflation is not None, "the deliberate conflation MUST fire PREDICATE_CONFLATION"

    # --- contradictions (rendered without collapse) --------------------------
    contradictions: list[Contradiction] = list(reconciliation.contradictions)
    # policy_configuration_divergence: Ops Manual §5-118 vs 109-agency sharing.
    contradictions.append(
        Contradiction(
            contradiction_type=POLICY_CONFIGURATION_DIVERGENCE,
            subject_id=DEPLOYMENT_ID,
            predicate_id="configured_sharing_partner_set",
            claim_values=(
                "policy: will not be shared as part of a law enforcement information database",
                "configured: 109 local agencies can pull OKC data",
            ),
            note=(
                "OKCPD Operations Manual §5-118 states ALPR data will not be shared as part of a "
                "law enforcement information database, while the configured Flock network let 109 "
                "local agencies pull OKC data (pre-renewal). Both observations retained."
            ),
            severity="blocking",
            evidence=(
                ev.for_quote(
                    "okc-ops-manual-5-118",
                    "will not be shared as part of a law enforcement information database",
                ),
                ev.for_quote("okc-sharing-109-agencies", "109 local agencies can already pull"),
            ),
        )
    )

    # --- non-count facts, keyed by dossier section ---------------------------
    facts: dict[str, list[Fact]] = {
        "cost_and_expiry": [
            Fact(
                "contract_value",
                "Annual contract value",
                "$270,000",
                ev.for_quote("okc-contract-c241032", "$270,000 a year"),
            ),
            Fact(
                "expiry",
                "Contract term ends",
                "2027-06-30",
                ev.for_quote("okc-council-2026-08-18", "through 2027-06-30"),
            ),
            Fact(
                "next_decision_date",
                "Next decision date",
                "2027-06-30",
                ev.for_quote("okc-council-2026-08-18", "returns to the council before another"),
                note="Renewed one year; returns to council before the next renewal.",
            ),
        ],
        "who_else_can_see": [
            Fact(
                "configured_sharing",
                "Configured access (agencies that can pull data)",
                109,
                ev.for_quote("okc-sharing-109-agencies", "109 local agencies can already pull"),
            ),
            Fact(
                "national_network",
                "National sharing network",
                "5,000+ agencies",
                ev.for_quote(
                    "okc-sharing-109-agencies", "more than 5,000 agencies and 100,000 cameras"
                ),
            ),
        ],
        "configuration_and_retention": [
            Fact(
                "configured_retention_days",
                "Configured retention (post-renewal)",
                7,
                ev.for_quote(
                    "okc-council-2026-08-18", "reducing the data retention period from 30 to 7 days"
                ),
            ),
            Fact(
                "prior_retention_days",
                "Prior configured retention",
                30,
                ev.for_quote("okc-council-2026-08-18", "from 30 to 7 days"),
            ),
            Fact(
                "federal_sharing_control",
                "Federal-sharing control",
                "City, not Flock (2026-08-18 amendment)",
                ev.for_quote(
                    "okc-council-2026-08-18", "sole power to share data with federal agencies"
                ),
            ),
        ],
        "usage": [
            Fact(
                "observed_searches",
                "Observed network searches (OKC-specific)",
                None,
                status="not_researched",
                note="Configured national lookup was enabled; OKC-specific observed searches "
                "are not yet researched (§12.2 configured access vs observed use).",
            ),
        ],
        "policy": [
            Fact(
                "sharing_policy",
                "Agency sharing policy (Ops Manual §5-118)",
                "Data will not be shared as part of a law enforcement information database",
                ev.for_quote(
                    "okc-ops-manual-5-118",
                    "will not be shared as part of a law enforcement information database",
                ),
            ),
            Fact(
                "legal_regime",
                "Applicable statute",
                "47 O.S. §7-606.1 (limits ALPR to insurance enforcement)",
                ev.for_quote("okc-statute-47-7-606-1", "47 O.S. §7-606.1"),
            ),
        ],
        "accountability_events": [
            Fact(
                "renewal_vote",
                "Council renewal vote (2026-08-18)",
                "Renewed 5–3, after public comment (not a consent agenda)",
                ev.for_quote("okc-council-2026-08-18", "5 to 3"),
            ),
            Fact(
                "related_litigation",
                "Related litigation",
                "Flock platform under federal constitutional challenge (vendor-level)",
                ev.for_quote("okc-litigation-flock", "under federal constitutional challenge"),
            ),
        ],
        "timeline": [
            Fact(
                "program_start",
                "Program start",
                "2023",
                ev.for_quote("okc-contract-c241032", "since 2023"),
            ),
            Fact(
                "renewal",
                "Contract renewed (lifecycle transition)",
                "2026-08-18",
                ev.for_quote("okc-council-2026-08-18", "August 18, 2026"),
            ),
        ],
    }

    # replacement / adjacent vendor (J-1's last hop)
    facts.setdefault("what_is_deployed", []).append(
        Fact(
            "replacement_vendor",
            "Adjacent / replacement vendor",
            "Fusus (Axon) RTCC",
            ev.for_quote(
                "okc-replacement-fusus-axon", "Fusus, the Axon-owned real-time crime center"
            ),
        )
    )

    # --- physical assets, incl. one with no operator (§29.2) -----------------
    assets = [
        PhysicalAsset(
            "sig:asset:okc-pole-1",
            "Mapped ALPR pole (OKCPD-operated)",
            AGENCY,
            ev.for_quote("okc-deflock-map", "The community map shows 299"),
        ),
        PhysicalAsset(
            "sig:asset:okc-pole-2",
            "Mapped ALPR pole (operator unknown)",
            None,
            ev.for_quote("okc-deflock-map", "many mapped devices have no confirmed operator"),
        ),
    ]

    return SliceGraph(
        jurisdiction=JURISDICTION,
        agency=AGENCY,
        deployment_id=DEPLOYMENT_ID,
        reconciliation=reconciliation,
        count_claims=count_claims,
        facts=facts,
        assets=assets,
        contradictions=contradictions,
        conflation=conflation,
        evidence=ev,
    )


# --- J-1 traversal (§2.2, Appendix D) ----------------------------------------


@dataclass(frozen=True)
class Hop:
    name: str
    node: str
    evidence: tuple[Evidence, ...] = ()


def j1_traversal(graph: SliceGraph) -> list[Hop]:
    """The journalist's traversal, in the order §2.2 specifies:
    city → police agency → deployment → contract → counts → sharing → searches →
    retention → policy → litigation → replacement vendor."""
    rec = graph.reconciliation

    def fact(section: str, key: str) -> Fact:
        return next(f for f in graph.facts.get(section, []) if f.key == key)

    def fact_ev(section: str, key: str) -> tuple[Evidence, ...]:
        f = fact(section, key)
        return (f.evidence,) if f.evidence else ()

    contracted = rec.resolutions["contracted"]
    return [
        Hop("city", graph.jurisdiction),
        Hop("police_agency", graph.agency),
        Hop("deployment", graph.deployment_id),
        Hop("contract", "Master Agreement C241032", (graph.count_claims[0].evidence,)),
        Hop(
            "contracted_cameras",
            f"{contracted.value} contracted",
            (contracted.winning_claim.evidence,) if contracted.winning_claim else (),
        ),
        Hop(
            "mapped_devices",
            f"{rec.resolutions['mapped'].value} mapped (lower bound)",
            (rec.resolutions["mapped"].winning_claim.evidence,)
            if rec.resolutions["mapped"].winning_claim
            else (),
        ),
        Hop(
            "sharing_relationships",
            "109 local agencies (configured access)",
            fact_ev("who_else_can_see", "configured_sharing"),
        ),
        Hop("network_searches", "observed use: not researched", ()),
        Hop(
            "retention_settings",
            "7 days (post-renewal); prior 30",
            fact_ev("configuration_and_retention", "configured_retention_days"),
        ),
        Hop("policy", "Ops Manual §5-118", fact_ev("policy", "sharing_policy")),
        Hop(
            "related_litigation",
            "Flock under federal constitutional challenge",
            fact_ev("accountability_events", "related_litigation"),
        ),
        Hop(
            "replacement_vendor", "Fusus (Axon)", fact_ev("what_is_deployed", "replacement_vendor")
        ),
    ]


# --- dossier assembly (§39.2) -------------------------------------------------


def _ui_doc(e: Evidence) -> UiDoc:
    return UiDoc(
        source_family=e.source_family,
        stable_locator=e.stable_locator,
        locator=e.locator,
        capture_digest=e.capture_digest,
        excerpt=e.excerpt,
    )


def _count_figure(res: CountResolution) -> Figure:
    win = res.winning_claim
    winning = ReconClaim(
        value=res.value,
        source_family=win.evidence.source_family,
        reliability=win.reliability,
        weight=res.weight,
        observed_at=win.observed_at,
        document=_ui_doc(win.evidence),
    )
    competing = tuple(
        ReconClaim(
            value=c.value,
            source_family=c.evidence.source_family,
            reliability=c.reliability,
            weight=None,
            observed_at=c.observed_at,
            document=_ui_doc(c.evidence),
        )
        for c in res.dissenting
    )
    label = res.count_basis.capitalize() + " device count"
    return Figure(
        key=res.predicate_id,
        label=label,
        value=res.value,
        unit="cameras",
        lower_bound=res.lower_bound,
        reconciliation=Reconciliation(
            rule=f"{res.count_basis}: W{res.weight}",
            winning=winning,
            competing=competing,
            note=res.rationale,
        ),
    )


def _rows(facts: list[Fact]) -> tuple[Row, ...]:
    out = []
    for f in facts:
        out.append(
            Row(
                label=f.label,
                value=f.value,
                status=f.status,
                document=_ui_doc(f.evidence) if f.evidence else None,
                note=f.note,
            )
        )
    return tuple(out)


def build_dossier(graph: SliceGraph) -> Dossier:
    rec = graph.reconciliation

    # Count figures live in "what is deployed"; each is expandable (SIG-UI-014).
    deployed_figures = tuple(
        _count_figure(rec.resolutions[b])
        for b in ("contracted", "active", "installed", "mapped", "claimed", "invoiced")
        if b in rec.resolutions
    )

    # "What we don't know" (SIG-UI-011): the unresearched predicates + facts.
    gaps = [
        Gap("installed_device_count", "not_researched", "No field inventory of installed devices."),
        Gap(
            "invoiced_device_count",
            "not_researched",
            "No invoice obtained; billed quantity unknown.",
        ),
        Gap(
            "observed network searches (OKC-specific)",
            "not_researched",
            "Configured access is known; observed use is not.",
        ),
    ]
    unresearched = len(gaps)

    where_rows = tuple(
        Row(
            label=a.label,
            value=(a.operator if a.operator is not None else None),
            status="known" if a.operator is not None else "not_researched",
            document=_ui_doc(a.evidence),
            note="operator unknown (§29.2)" if a.operator is None else "",
        )
        for a in graph.assets
    )

    at_a_glance = (
        Row("Jurisdiction", graph.jurisdiction),
        Row("Agency", graph.agency),
        Row("Vendor", "Flock Safety"),
        Row(
            "Contract", "Master Agreement C241032", document=_ui_doc(graph.count_claims[0].evidence)
        ),
    )

    how_we_know = tuple(
        Row(f"Source family: {fam}", "cited", document=None)
        for fam in sorted({a.source_family for a in graph.evidence.artifacts.values()})
    )

    contradiction_rows = tuple(
        Row(
            label=f"Contradiction: {c.contradiction_type}",
            value=c.note,
            document=_ui_doc(c.evidence[0]) if c.evidence else None,
        )
        for c in graph.contradictions
    )

    sections = (
        Section("at_a_glance", rows=at_a_glance),
        Section(
            "what_is_deployed",
            figures=deployed_figures,
            rows=_rows(graph.facts.get("what_is_deployed", [])),
        ),
        Section("cost_and_expiry", rows=_rows(graph.facts.get("cost_and_expiry", []))),
        Section("who_else_can_see", rows=_rows(graph.facts.get("who_else_can_see", []))),
        Section(
            "configuration_and_retention",
            rows=_rows(graph.facts.get("configuration_and_retention", [])),
        ),
        Section("usage", rows=_rows(graph.facts.get("usage", []))),
        Section("where_the_hardware_is", rows=where_rows),
        Section("policy", rows=_rows(graph.facts.get("policy", []))),
        Section(
            "accountability_events",
            rows=_rows(graph.facts.get("accountability_events", [])) + contradiction_rows,
        ),
        Section("timeline", rows=_rows(graph.facts.get("timeline", []))),
        Section(
            "what_we_dont_know",
            rows=tuple(Row(g.label, None, status=g.status, note=g.note) for g in gaps),
        ),
        Section("how_we_know_this", rows=how_we_know),
    )

    dossier = Dossier(
        subject_label=f"{graph.agency} — Flock ALPR deployment",
        jurisdiction=graph.jurisdiction,
        as_of=AS_OF,
        permalink=PERMALINK,
        sections=sections,
        gaps=tuple(gaps),
        unresearched_field_count=unresearched,
        source_families=tuple(sorted({a.source_family for a in graph.evidence.artifacts.values()})),
    )
    dossier.validate()
    return dossier


def material_facts(graph: SliceGraph) -> list[tuple[str, Evidence]]:
    """Every material fact in the slice, paired with the evidence that supports it
    (used to assert each resolves to a document at a locator — AC2)."""
    out: list[tuple[str, Evidence]] = []
    for res in graph.reconciliation.resolutions.values():
        if res.winning_claim is not None:
            out.append((f"{res.predicate_id}={res.value}", res.winning_claim.evidence))
    for section_facts in graph.facts.values():
        for f in section_facts:
            if f.evidence is not None:
                out.append((f"{f.key}={f.value}", f.evidence))
    for a in graph.assets:
        out.append((a.asset_id, a.evidence))
    for c in graph.contradictions:
        for e in c.evidence:
            out.append((f"contradiction:{c.contradiction_type}", e))
    return out
