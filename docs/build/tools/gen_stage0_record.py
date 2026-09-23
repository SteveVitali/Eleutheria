#!/usr/bin/env python3
"""Generate docs/build/STAGE0_OUTREACH_RECORD.md (P21.1, scratch generator).

One row per federation-compact project (the 19 from spec §6 / §35.1). The gate
HG-04 is SKIP this run: NO outreach was performed, so every row's `date_sent` is
`—` and every outcome is the registry-recorded compact posture — `not_contacted`
or `public_terms_only`, plus the pre-existing `no_response` for FlockReporter (a
recorded state from SIG-INGEST-039b, NOT new outreach). Contact channels are
ORGANISATIONAL public addresses only — no personal names (Part VIII §0.7).
"""

from __future__ import annotations

import pathlib

from connectors.registry import get, registry

ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/build/STAGE0_OUTREACH_RECORD.md"

# Outcome ranking so a project's row surfaces the most-progressed recorded state
# among its governed sources (a "contacted" state surfaces over not_contacted).
RANK = {
    "not_contacted": 0,
    "permission_declined": 1,
    "no_response": 2,
    "contacted_awaiting_response": 3,
    "public_terms_only": 4,
    "permission_granted": 5,
    "permission_granted_conditional": 5,
    "partnership_active": 6,
}

# The 19 federation-compact projects (spec §6 table, lines 656-676; "all nineteen
# federation-compact projects", spec §52 line ~6731). Each maps to a public
# organisational contact channel (never a personal name) and the sources.toml ids
# it governs.
PROJECTS: list[tuple[str, str, list[str]]] = [
    ("OpenStreetMap / OSMF", "https://osmfoundation.org/wiki/Contact (OSMF, public)",
     ["osm_surveillance_tagging", "osm_copyright", "osmf_licence_guidelines", "osm_taginfo",
      "osm_overpass", "osm_replication", "osm_element_history", "osm_automated_edits_coc",
      "sous_surveillance_osm_import"]),
    ("DeFlock (FoggedLens)", "https://github.com/FoggedLens/deflock/issues (project issue tracker, public)",
     ["deflock", "deflock_repo", "deflock_app_repo"]),
    ("Eyes on Flock", "contact@eyesonflock.com (organisational address, registry-recorded)",
     ["eyes_on_flock", "eyes_on_flock_description"]),
    ("Have I Been Flocked", "https://haveibeenflocked.com/about (project contact page, public)",
     ["have_i_been_flocked", "hibf_methodology", "hibf_audit_log_guide"]),
    ("ALPR Watch", "https://alprwatch.org/ (project site, public)",
     ["alpr_watch", "alpr_watch_foia_method", "alpr_watch_code", "alpr_watch_dashboard"]),
    ("EFF — Atlas of Surveillance", "https://www.eff.org/about/contact (EFF, public)",
     ["eff_atlas_of_surveillance", "atlas_methodology", "atlas_about", "atlas_data_library",
      "eff_copyright", "eff_street_level_surveillance"]),
    ("EFF — Data Driven", "https://www.eff.org/about/contact (EFF, public)",
     ["eff_data_driven"]),
    ("ALPR Accountability Atlas", "https://alpratlas.org/ (project site, public)",
     ["alpr_accountability_atlas"]),
    ("ALPR Abuse Library / Kansas Watch", "https://library.kansas.watch/ (project site, public)",
     ["alpr_abuse_library"]),
    ("MuckRock", "info@muckrock.com (organisational address, public)",
     ["muckrock"]),
    ("DocumentCloud", "https://www.documentcloud.org/help/ (project contact page, public)",
     ["documentcloud"]),
    ("Drivers Against Flock", "https://driversagainstflock.org/ (project site, public)",
     ["drivers_against_flock"]),
    ("Flock Finder", "https://github.com/simeononsecurity/flock-finder/issues (issue tracker, public)",
     ["flock_finder"]),
    ("Flock-You", "https://github.com/rjmoggach/flock-you (project repo, public)",
     ["flock_you"]),
    ("FlockReporter", "flockreporter.org (DNS ceased 2026-07-28 .. 2026-08-20; SIG-INGEST-039b)",
     ["flockreporter"]),
    ("Local DeFlock / Eyes Off groups", "per-group public sites (connectors/.../data/local_groups.toml)",
     ["eyes_off_cedar_rapids", "eyes_off_eugene"]),
    ("Technopolice / La Quadrature du Net", "https://www.laquadrature.net/en/contact/ (LQDN, public)",
     ["technopolice", "technopolice_forum", "technocarte_update", "la_quadrature_du_net"]),
    ("Surveillance under Surveillance", "https://sunders.uber.space/ (project site, public)",
     ["surveillance_under_surveillance"]),
    ("PanoptiCity", "https://panopticity.fr/ (project site, public)",
     ["panopticity"]),
]


def outcome_for(ids: list[str]) -> str:
    reg = registry()
    present = [get(i).compact_status.value for i in ids if i in reg]
    if not present:
        return "not_contacted"
    return max(present, key=lambda s: RANK[s])


def main() -> None:
    reg = registry()
    lines: list[str] = []
    lines.append("# STAGE0_OUTREACH_RECORD — federation-compact Stage-0 outreach (P21.1, SIG-CONTRIB-012/012a/013)")
    lines.append("")
    lines.append(
        "One row per **federation-compact project** — the 19 of spec §6 (the compact table) / §35.1 "
        "(\"all nineteen federation-compact projects\", §52). Stage-0 outreach MUST be attempted and its "
        "outcome recorded **before** any connector is written for a project (SIG-CONTRIB-012, "
        "SIG-CHART-033); the outcome vocabulary is the closed `compact_status` enum (SIG-INGEST-027)."
    )
    lines.append("")
    lines.append("## Gate status — HG-04 = SKIP (no outreach performed this run)")
    lines.append("")
    lines.append(
        "**No Stage-0 outreach has been performed by this ticket.** This file is the RECORD FORMAT "
        "(template), seeded from the registry's current `compact_status`. Every `date_sent` is `—` and "
        "every `outcome` is the registry-recorded posture: `not_contacted` or `public_terms_only` "
        "(public terms suffice for lawful use today), plus the pre-existing `no_response` for "
        "**FlockReporter** — a state already recorded in the registry (the directory's DNS ceased "
        "between 2026-07-28 and 2026-08-20, SIG-INGEST-039b), NOT new outreach invented here. No "
        "`permission_granted` / `partnership_active` / `permission_declined` is asserted anywhere, "
        "because none was obtained (defining standard §3.1 — no synthetic certainty; append-only "
        "P1–P3 — a real outreach event is added as a new dated row, never by rewriting this seed). "
        "Contact channels are ORGANISATIONAL public addresses only — no personal names (Part VIII §0.7)."
    )
    lines.append("")
    lines.append("The archival-succession offer (SIG-CONTRIB-013, RISK-P0-17/20) and, where a project has "
                 "publicly asked for help (SIG-CONTRIB-012a), the opening offer, are carried in the "
                 "outreach letter template: `docs/governance/stage0-outreach-letter.md`.")
    lines.append("")
    lines.append("## Record")
    lines.append("")
    lines.append("| # | project | contact channel (public org address only) | date_sent | outcome | governs (sources.toml ids) |")
    lines.append("|---|---|---|---|---|---|")
    for i, (name, contact, ids) in enumerate(PROJECTS, start=1):
        outcome = outcome_for(ids)
        gov = ", ".join(f"`{x}`" for x in ids)
        # Flag ids that are not in the source registry (local-group projects live in
        # local_groups.toml) so the row is honest about where the id lives.
        missing = [x for x in ids if x not in reg]
        note = ""
        if missing:
            note = "  _(+ local_groups.toml)_" if name.startswith("Local") else \
                   f"  _(not in sources.toml: {', '.join(missing)})_"
        lines.append(f"| {i} | {name} | {contact} | — | {outcome} | {gov}{note} |")
    lines.append("")
    lines.append("_19 project rows. Regenerate: `python .agents/scratch/tools/gen_stage0_record.py`. "
                 "Consistency test: `tests/connectors/test_stage0_outreach.py`._")
    lines.append("")
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {OUT} ({len(PROJECTS)} project rows)")
    assert len(PROJECTS) == 19


if __name__ == "__main__":
    main()
