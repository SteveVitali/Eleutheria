#!/usr/bin/env python3
"""Generate the 27 P21.1 rights-review packets + _TEMPLATE.md (scratch, gitignored).

Packets lay out FACTS (quoted terms + retrieval date) separately from JUDGEMENT
(the reviewer decision line). No packet asserts a legal conclusion. Verbatim terms
that were actually fetched by the agent this pass carry the retrieval date; where a
terms page was not fetched, the packet says so honestly and records the terms_url
for the reviewer to fetch (defining standard §3.1 — no synthetic certainty).
"""

from __future__ import annotations

import pathlib

RIGHTS = pathlib.Path(__file__).resolve().parents[3] / "docs/build/rights"
RETRIEVAL = "2026-09-09"

# --- Verbatim terms actually fetched by the agent (retrieval 2026-09-09) -------

OSM_VERBATIM = f"""> Fetched from https://www.openstreetmap.org/copyright on {RETRIEVAL} (terms page,
> not source content — permitted research):
>
> "OpenStreetMap is *open* data, licensed under the Open Data Commons Open Database
> License (ODbL) by the OpenStreetMap Foundation (OSMF). In summary: You are free to
> copy, distribute, transmit and adapt our data, as long as you credit OpenStreetMap
> and its contributors. If you alter or build upon our data, you may distribute the
> result only under the same license. The full legal code at Open Data Commons
> explains your rights and responsibilities."
>
> "Where you use OpenStreetMap data, you are required to do the following two things:
> Provide credit to OpenStreetMap by displaying our attribution notice. Make clear
> that the data is available under the Open Database License."
>
> "Although OpenStreetMap is open data, we cannot provide a free-of-charge map API or
> map tiles for third-parties. See our API Usage Policy, Tile Usage Policy and
> Nominatim Usage Policy." (§26 crawler-conduct / etiquette applies.)"""

USASPENDING_VERBATIM = f"""> Fetched from https://api.usaspending.gov/ on {RETRIEVAL} (API landing page,
> not award content — permitted research):
>
> "The USAspending API (Application Programming Interface) allows the public to access
> comprehensive U.S. government spending data."
>
> "The U.S. Department of the Treasury is building a suite of open-source tools to help
> federal agencies comply with the DATA Act and to deliver the resulting standardized
> federal spending information back to agencies and to the public."
>
> USAspending is a work of the U.S. federal government published under the DATA Act
> (Pub. L. 113-101). U.S. Government works are not subject to domestic copyright
> protection (17 U.S.C. §105); the data are in the public domain. This packet records
> that fact; the SPDX expression is a reviewer decision (see Decision)."""

DEFLOCK_REPO_VERBATIM = f"""> Fetched from https://github.com/FoggedLens/deflock on {RETRIEVAL} (repo landing,
> not content — permitted research): the repository files navigation shows a "README"
> and an "**MIT license**" badge, and the README states the map "Uses OpenStreetMap
> data to populate a map with crowdsourced locations of ALPRs". The LICENSE file is
> linked at the repo root (terms_url below). MIT license canonical text:
>
> "Permission is hereby granted, free of charge, to any person obtaining a copy of
> this software and associated documentation files (the \\"Software\\"), to deal in the
> Software without restriction, including without limitation the rights to use, copy,
> modify, merge, publish, distribute, sublicense, and/or sell copies of the Software
> ... THE SOFTWARE IS PROVIDED \\"AS IS\\", WITHOUT WARRANTY OF ANY KIND."
>
> NOTE: the DeFlock *device data* is contributed to OpenStreetMap and travels under
> ODbL-1.0 (SIG-LIC-009a silently-travelling share-alike), not MIT — MIT covers the
> DeFlock *code* only."""

MIT_CANONICAL = """> MIT License canonical text (SPDX: MIT), applied to this repository's LICENSE file
> (terms_url below; not fetched verbatim this pass — reviewer to confirm the exact
> copyright line):
>
> "Permission is hereby granted, free of charge, to any person obtaining a copy of this
> software ... to deal in the Software without restriction ... THE SOFTWARE IS PROVIDED
> \\"AS IS\\", WITHOUT WARRANTY OF ANY KIND."""

AGPL_CANONICAL = """> GNU Affero General Public License v3.0 canonical text (SPDX: AGPL-3.0), applied to
> this repository's LICENSE file (terms_url below; not fetched verbatim this pass):
>
> "This is free software: you are free to change and redistribute it ... if you modify
> the Program, your modified version must prominently offer all users interacting with
> it remotely through a computer network ... an opportunity to receive the Corresponding
> Source of your version."
>
> HAZARD (SIG-INGEST-048b): AGPL-3.0 code MUST NOT be linked into SIG's Apache-2.0
> codebase; its methods may be studied freely. derivative_permitted=false records the
> linking hazard (not a data restriction)."""

CCBYSA_CANONICAL = """> Creative Commons Attribution-ShareAlike 4.0 International (SPDX: CC-BY-SA-4.0)
> canonical deed (not fetched verbatim from the source this pass — homepage is a
> JavaScript app that returned no static terms text; SPDX recorded in the registry
> under SIG-INGEST-030):
>
> "You are free to: Share — copy and redistribute the material in any medium or format;
> Adapt — remix, transform, and build upon the material for any purpose, even
> commercially. Under the following terms: Attribution ... ShareAlike — If you remix,
> transform, or build upon the material, you must distribute your contributions under
> the same license as the original."""

CCBY_CANONICAL = """> Creative Commons Attribution 4.0 International (SPDX: CC-BY-4.0) canonical deed
> (terms_url below records the source's own copyright statement; not fetched verbatim
> this pass — reviewer to confirm the source page still asserts CC BY 4.0):
>
> "You are free to: Share ... Adapt ... for any purpose, even commercially. Under the
> following terms: Attribution — You must give appropriate credit ... No additional
> restrictions."""

CC0_CANONICAL = """> Creative Commons CC0 1.0 Universal / public-domain dedication (SPDX: CC0-1.0)
> canonical deed (terms_url below records the source's own data-terms statement; not
> fetched verbatim this pass — reviewer to confirm the source page still asserts CC0 /
> public domain):
>
> "The person who associated a work with this deed has dedicated the work to the public
> domain by waiving all of his or her rights to the work worldwide under copyright law
> ... You can copy, modify, distribute and perform the work, even for commercial
> purposes, all without asking permission."""


def undetermined_terms(note: str) -> str:
    return (
        f"> UNDETERMINED — no resolved rights block in the registry (SIG-LIC-004; fails the\n"
        f"> export gate closed). {note}\n>\n"
        f"> Terms were NOT fetched verbatim for this source this pass; the terms_url is\n"
        f"> recorded for the reviewer to fetch and quote before any flip. This packet makes\n"
        f"> no assertion about the licence (defining standard §3.1 — no synthetic certainty)."
    )


# --- Per-source packet data ----------------------------------------------------
# fields: id, name, homepage, terms_url, robots, spdx, redist, deriv, verbatim,
#         redist_analysis, deriv_analysis, odbl, custody_rec, counsel

OSM_ODBL_IDS = {
    "osm_surveillance_tagging": "OSM surveillance tagging (Tag:man_made=surveillance)",
    "osm_copyright": "OSM copyright / licence",
    "osmf_licence_guidelines": "OSMF Licence Community Guidelines",
    "osm_taginfo": "OSM taginfo API",
    "osm_overpass": "OSM Overpass API",
    "osm_replication": "OSM replication diffs",
    "osm_element_history": "OSM element history",
    "osm_automated_edits_coc": "OSM Automated Edits code of conduct",
    "sous_surveillance_osm_import": "sous-surveillance.net → OSM import",
}

PACKETS: list[dict] = []


def add(**kw) -> None:
    PACKETS.append(kw)


# --- The nine OSM/ODbL packets ---
_OSM_TERMS = {
    "osm_copyright": "https://www.openstreetmap.org/copyright",
    "osmf_licence_guidelines": "https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines",
    "osm_taginfo": "https://www.openstreetmap.org/copyright",
    "osm_overpass": "https://www.openstreetmap.org/copyright",
    "osm_replication": "https://www.openstreetmap.org/copyright",
    "osm_element_history": "https://www.openstreetmap.org/copyright",
    "osm_automated_edits_coc": "https://www.openstreetmap.org/copyright",
    "osm_surveillance_tagging": "https://www.openstreetmap.org/copyright",
    "sous_surveillance_osm_import": "https://www.openstreetmap.org/copyright",
}
_OSM_HOME = {
    "osm_surveillance_tagging": "https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance",
    "osm_copyright": "https://www.openstreetmap.org/copyright",
    "osmf_licence_guidelines": "https://wiki.osmfoundation.org/wiki/Licence/Community_Guidelines",
    "osm_taginfo": "https://taginfo.openstreetmap.org/api/4/",
    "osm_overpass": "https://overpass-api.de/api/interpreter",
    "osm_replication": "https://planet.openstreetmap.org/replication/",
    "osm_element_history": "https://api.openstreetmap.org/api/0.6/node/<id>/history.json",
    "osm_automated_edits_coc": "https://wiki.openstreetmap.org/wiki/Automated_Edits_code_of_conduct",
    "sous_surveillance_osm_import": "https://wiki.openstreetmap.org/wiki/Import/sous-surveillance",
}
for sid, name in OSM_ODBL_IDS.items():
    add(
        id=sid, name=name, homepage=_OSM_HOME[sid], terms_url=_OSM_TERMS[sid],
        robots="honor (OSM/OSMF API + tile usage policies apply; §26 etiquette).",
        spdx="ODbL-1.0", redist="true", deriv="true", verbatim=OSM_VERBATIM,
        redist_analysis="Redistributable under ODbL-1.0 with the two required credit/licence-notice conditions. redistributable=true is separately reviewed (SIG-LIC-003), not derived from the SPDX string.",
        deriv_analysis="Derivatives permitted; a derived database inherits the ODbL share-alike obligation (SIG-LIC-009a). derivative_permitted=true.",
        odbl="OSM-derived ⇒ ODbL compartment (RISK-P0-01/02). The share-alike/attribution and §4.4(b) sui-generis questions are for counsel (HG-02); until dispositioned the OSM-derived layer is export/link-only.",
        custody_rec="REFERENCE (fetch + hold derived facts); never the canonical editing DB (N7).",
        counsel="YES — ODbL §4.4(b) sui-generis + share-alike travel (RISK-P0-01/02, HG-02).",
    )

# --- DeFlock repo (MIT) ---
add(
    id="deflock_repo", name="DeFlock — canonical repo (FoggedLens/deflock)",
    homepage="https://github.com/FoggedLens/deflock",
    terms_url="https://github.com/FoggedLens/deflock/blob/main/LICENSE",
    robots="honor (GitHub); repo landing fetched, not cloned.",
    spdx="MIT", redist="true", deriv="true", verbatim=DEFLOCK_REPO_VERBATIM,
    redist_analysis="MIT code is redistributable with the copyright + permission notice retained. redistributable=true (SIG-LIC-003).",
    deriv_analysis="Derivatives permitted under MIT. BUT the DeFlock device *data* travels under OSM's ODbL (SIG-LIC-009a) — MIT covers the code only.",
    odbl="Device data is OSM-derived ⇒ ODbL compartment for the data path (RISK-P0-01/02). Code path is MIT.",
    custody_rec="REFERENCE (code studied; device data reconciled via osm_overpass under ODbL).",
    counsel="PARTIAL — code is clean MIT; the data path inherits the ODbL/HG-02 question.",
)

# --- DeFlock app repo (AGPL) ---
add(
    id="deflock_app_repo", name="DeFlock — app repo (FoggedLens/deflock-app)",
    homepage="https://github.com/FoggedLens/deflock-app",
    terms_url="https://github.com/FoggedLens/deflock-app/blob/main/LICENSE",
    robots="honor (GitHub).",
    spdx="AGPL-3.0", redist="true", deriv="false", verbatim=AGPL_CANONICAL,
    redist_analysis="AGPL-3.0 is redistributable under its copyleft terms. redistributable=true.",
    deriv_analysis="derivative_permitted=false in the registry records the SIG-INGEST-048b LINKING hazard: AGPL code MUST NOT be linked into SIG's Apache-2.0 codebase. Methods may be studied; code may not be linked/derived-into SIG.",
    odbl="Not OSM-derived. No ODbL implication; the hazard is the AGPL network-copyleft/linking rule.",
    custody_rec="REFERENCE (study only; never link into SIG's build).",
    counsel="YES — AGPL-3.0 linking/network-copyleft disposition (SIG-INGEST-048b).",
)

# --- Eyes on Flock (CC-BY-SA-4.0) ---
add(
    id="eyes_on_flock", name="Eyes on Flock",
    homepage="https://eyesonflock.com/", terms_url="https://eyesonflock.com/",
    robots="honor (Allow: / ; public unauthenticated key-free JSON API GET /api/v1/data; do not poll faster than upstream refresh, SIG-INGEST-030c).",
    spdx="CC-BY-SA-4.0", redist="true", deriv="true", verbatim=CCBYSA_CANONICAL,
    redist_analysis="Redistributable under CC-BY-SA-4.0 with attribution + share-alike. redistributable=true. NOTE: eyesonflock.com is a JS app; no static terms text was returned this pass — the CC-BY-SA-4.0 posture is the registry-recorded Stage-0 outcome (SIG-INGEST-030, confirmed usable public terms).",
    deriv_analysis="Derivatives permitted; the CC-BY-SA-4.0 share-alike obligation travels (SIG-LIC-009a). derivative_permitted=true.",
    odbl="Not OSM-derived; CC-BY-SA-4.0 compartment is separate from and incompatible with ODbL (SIG-LIC-004a) — must not be merged with the OSM compartment in one export.",
    custody_rec="MIRROR (portal temporal layer / archival succession, §22.5) — subject to the Stage-0 partnership + succession outreach (HG-04, SIG-CONTRIB-013).",
    counsel="PARTIAL — public CC-BY-SA terms usable today; partnership/succession is Stage-0 outreach, not counsel.",
)

# --- Atlas of Surveillance (CC-BY-4.0) ---
add(
    id="eff_atlas_of_surveillance", name="EFF Atlas of Surveillance",
    homepage="https://www.atlasofsurveillance.org/", terms_url="https://www.eff.org/copyright",
    robots="honor.",
    spdx="CC-BY-4.0", redist="true", deriv="true", verbatim=CCBY_CANONICAL,
    redist_analysis="Redistributable under CC-BY-4.0 with attribution to EFF / Atlas of Surveillance. redistributable=true; preserve source attribution and allow supersession (§23.3).",
    deriv_analysis="Derivatives permitted with attribution. derivative_permitted=true.",
    odbl="Not OSM-derived. CC-BY-4.0 folds into neither ODbL nor CC-BY-SA (SIG-LIC-004a) — its own compartment.",
    custody_rec="MIRROR (primary deployment seed; supersession allowed).",
    counsel="NO — standard CC-BY-4.0 with attribution.",
)

# --- GLEIF (CC0) ---
add(
    id="gleif", name="GLEIF LEI golden copy",
    homepage="https://www.gleif.org/en/lei-data/gleif-golden-copy",
    terms_url="https://www.gleif.org/en/about/governance/data-terms-of-use", robots="honor.",
    spdx="CC0-1.0", redist="true", deriv="true", verbatim=CC0_CANONICAL,
    redist_analysis="CC0 public-domain dedication ⇒ freely redistributable. redistributable=true.",
    deriv_analysis="No restriction on derivatives under CC0. derivative_permitted=true.",
    odbl="Not OSM-derived; CC0 relicensable into any compartment (including ODbL/CC-BY).",
    custody_rec="MIRROR (reference entity registry).",
    counsel="NO — CC0.",
)

# --- Wikidata (CC0) ---
add(
    id="wikidata_sparql", name="Wikidata SPARQL",
    homepage="https://query.wikidata.org/sparql",
    terms_url="https://www.wikidata.org/wiki/Wikidata:Licensing", robots="honor (WDQS query-limit etiquette; §26).",
    spdx="CC0-1.0", redist="true", deriv="true", verbatim=CC0_CANONICAL,
    redist_analysis="Wikidata statements are CC0. redistributable=true.",
    deriv_analysis="No derivative restriction under CC0. derivative_permitted=true.",
    odbl="Not OSM-derived; CC0 relicensable into any compartment.",
    custody_rec="REFERENCE (SPARQL federation).",
    counsel="NO — CC0.",
)

# --- Flock Finder (MIT) ---
add(
    id="flock_finder", name="Flock Finder",
    homepage="https://github.com/simeononsecurity/flock-finder",
    terms_url="https://github.com/simeononsecurity/flock-finder/blob/main/LICENSE",
    robots="honor (GitHub).",
    spdx="MIT", redist="true", deriv="true", verbatim=MIT_CANONICAL,
    redist_analysis="MIT code redistributable with notice retained. redistributable=true.",
    deriv_analysis="Derivatives permitted under MIT. derivative_permitted=true.",
    odbl="Not OSM-derived (RF-derived candidate discovery). No ODbL implication.",
    custody_rec="REFERENCE — LEAD GENERATION ONLY; never promoted to confirmed without §43.5.",
    counsel="NO — MIT code; the epistemic (lead-only) constraint is a modelling rule, not a rights one.",
)

# --- agency_audit_export (CC0 public record) ---
add(
    id="agency_audit_export", name="Agency Flock audit exports (public records)",
    homepage="https://eleutheria.example/records/agency-audit-export",
    terms_url="https://eleutheria.example/records/agency-audit-export",
    robots="not_applicable (obtained as public records, not crawled).",
    spdx="CC0-1.0", redist="true", deriv="true",
    verbatim=undetermined_terms(
        "This row models an agency's OWN Flock audit CSVs obtained as public records "
        "(not the derived HIBF bulk exports; SIG-INGEST-046a). The registry records "
        "CC0-1.0 as the posture for government-produced public records, but the "
        "records-release terms are agency-specific and were not fetched this pass."
    ),
    redist_analysis="Government public records; CC0-1.0 posture recorded. redistributable=true, but audit CSVs carry PII-minimisation obligations (aggregates-only, §43.6) that are a DATA-HANDLING rule, separate from the rights posture.",
    deriv_analysis="Derivatives permitted for the public-record data; structural aggregates only (N4/N9).",
    odbl="Not OSM-derived. No ODbL implication.",
    custody_rec="MIRROR (structural aggregates only; never re-host plate-level detail).",
    counsel="YES — public-records PII handling + the N4/N9 no-plate-level-search boundary.",
)

# --- raa_prefectures (ODbL via data.gouv.fr) ---
add(
    id="raa_prefectures", name="Recueils des actes administratifs des préfectures",
    homepage="https://www.data.gouv.fr/fr/datasets/recueils-des-actes-administratifs-des-prefectures/",
    terms_url="https://www.data.gouv.fr/fr/datasets/recueils-des-actes-administratifs-des-prefectures/",
    robots="honor.",
    spdx="ODbL-1.0", redist="true", deriv="true",
    verbatim=undetermined_terms(
        "The registry records ODbL-1.0 for this data.gouv.fr dataset (Licence Ouverte / "
        "ODbL are the two data.gouv.fr licences). The dataset page terms were not fetched "
        "verbatim this pass; the reviewer should confirm ODbL vs Licence Ouverte before a flip."
    ),
    redist_analysis="If ODbL-1.0: redistributable with attribution + share-alike. redistributable=true recorded; confirm the exact data.gouv.fr licence on fetch.",
    deriv_analysis="Derivatives permitted under ODbL with share-alike travel (SIG-LIC-009a).",
    odbl="ODbL compartment if ODbL — same RISK-P0-01/02 / HG-02 counsel questions as OSM. Prefectural arrêté PDFs (P21.8) are a separate extraction path.",
    custody_rec="REFERENCE (France/Belgium path; ingestion_permitted=false by design until P21.8).",
    counsel="YES — ODbL disposition (HG-02) + FR data.gouv.fr licence confirmation.",
)

# --- usaspending (UNDETERMINED, public-domain facts) ---
add(
    id="usaspending", name="USAspending",
    homepage="https://api.usaspending.gov/", terms_url="https://api.usaspending.gov/docs/",
    robots="honor (public REST API; api.data.gov-style etiquette; §26).",
    spdx="CC0-1.0 candidate (US-PD)", redist="true", deriv="true", verbatim=USASPENDING_VERBATIM,
    redist_analysis="U.S. Government works are not subject to domestic copyright (17 U.S.C. §105) ⇒ public domain ⇒ freely redistributable. This packet records the FACT; the registry row is still UNDETERMINED (no rights block) — adding the block is the reviewer's flip decision (see Decision).",
    deriv_analysis="No copyright ⇒ no derivative restriction. A reviewer flip would set derivative_permitted=true.",
    odbl="Not OSM-derived. CC0/US-PD relicensable into any compartment.",
    custody_rec="REFERENCE (prime + sub-awards; federal_award_id tracing). The one source ever fetched live (P07.3, LD-X08) — that trace ran outside the loader gate; a flip closes that gap.",
    counsel="LOW — U.S. federal public-domain works; reviewer confirms the SPDX expression (CC0-1.0 vs US-PD) per licenses.toml (CC0-1.0 is the accepted expression).",
)

# --- deflock (upstream field observation, UNDETERMINED) ---
add(
    id="deflock", name="DeFlock (upstream field observation)",
    homepage="https://deflock.org/", terms_url="https://deflock.org/",
    robots="honor (canonical host deflock.org; NOT deflock.me — 403 Cloudflare).",
    spdx="UNDETERMINED", redist="false", deriv="false",
    verbatim=undetermined_terms(
        "DeFlock the PROJECT (as distinct from its MIT code repo deflock_repo and AGPL "
        "app repo deflock_app_repo). Its device observations are contributed upstream to "
        "OpenStreetMap and travel under ODbL (SIG-LIC-009a); the deflock.org site itself "
        "has no separately-stated data licence. compact_status=not_contacted — Stage-0 "
        "outreach is outstanding (HG-04)."
    ),
    redist_analysis="UNDETERMINED ⇒ redistributable=false (fails export gate closed, SIG-LIC-004). Device data reconciled via OSM under ODbL, not re-hosted from deflock.org.",
    deriv_analysis="UNDETERMINED ⇒ derivative_permitted=false until reviewed. Do not fork DeFlock (SIG-CHART-015.1); link and reconcile.",
    odbl="Device data is OSM-derived ⇒ ODbL compartment (RISK-P0-01/02).",
    custody_rec="REFERENCE (link + reconcile via osm_overpass; do not compete, do not fork).",
    counsel="YES — ODbL data path (HG-02) + Stage-0 outreach outcome (HG-04).",
)

# --- civicclerk (portal software, UNDETERMINED) ---
add(
    id="civicclerk", name="CivicClerk agenda platform",
    homepage="https://<tenant>.api.civicclerk.com/v1/Events",
    terms_url="https://www.civicclerk.com/",
    robots="honor (per-tenant portal; the OKC tenant is oklahomacityok, agenda_tenants.toml).",
    spdx="UNDETERMINED", redist="false", deriv="false",
    verbatim=undetermined_terms(
        "CivicClerk is the vendor agenda/meeting platform; okc_council flows through its "
        "oklahomacityok tenant. The PUBLISHED RECORDS (agendas/minutes/video) are government "
        "public records; the CivicClerk PLATFORM terms of service govern automated access and "
        "were not fetched this pass. The reviewer must separate the public-record rights "
        "(government) from the vendor ToS (access-method constraint)."
    ),
    redist_analysis="Government public records are redistributable; the vendor platform ToS may constrain the ACCESS METHOD (rate/robots), not the record rights. redistributable=false until reviewed.",
    deriv_analysis="Public-record derivatives permitted; confirm the vendor ToS does not forbid bulk automated extraction.",
    odbl="Not OSM-derived. No ODbL implication.",
    custody_rec="REFERENCE (fetch published agendas/minutes for the tenant jurisdiction).",
    counsel="PARTIAL — public-record rights are clear; the vendor ToS automated-access clause needs a read.",
)

# --- Six OKC UNDETERMINED rows ---
OKC = [
    ("okc_procurement", "City of Oklahoma City — procurement / contracts",
     "https://www.okc.gov/departments/finance/purchasing",
     "https://www.okc.gov/", "REFERENCE", "R1 executed contracts / procurement records",
     "Municipal executed contracts (Flock Master Agreement C241032) are government public records; obtained via procurement portal or open records request."),
    ("okc_council", "Oklahoma City Council — agendas & minutes (CivicClerk)",
     "https://oklahomacityok.portal.civicclerk.com/",
     "https://oklahomacityok.portal.civicclerk.com/", "REFERENCE", "R2 municipal governance records",
     "Council agendas/minutes are government public records, served via the CivicClerk tenant oklahomacityok (see the civicclerk packet for the vendor-ToS access question)."),
    ("okcpd_policy", "OKCPD — policy (Operations Manual)",
     "https://www.okc.gov/departments/police",
     "https://www.okc.gov/", "REFERENCE", "R2 agency policy",
     "OKCPD Operations Manual §5-118 (ALPR policy) — agency policy document, government public record."),
    ("ok_statute", "Oklahoma statutes (47 O.S. §7-606.1 et seq.)",
     "https://www.oscn.net/applications/oscn/index.asp?ftdb=STOKST47",
     "https://www.oscn.net/", "REFERENCE", "R1 statutory / legal regime",
     "Oklahoma statutory text (OSCN). Statutes/edicts of government are not copyrightable in the U.S. (public domain); OSCN's site terms govern access method only."),
    ("journalrecord", "The Journal Record (Oklahoma City)",
     "https://journalrecord.com/", "https://journalrecord.com/terms-of-service/", "LINK",
     "R2 investigative journalism (paywalled)",
     "Copyrighted newspaper content behind a paywall. LINK posture: link to the article, quote only the minimum evidentiary fact, never re-host the article body."),
    ("oklahoman", "The Oklahoman (oklahoman.com)",
     "https://www.oklahoman.com/", "https://cm.oklahoman.com/terms-of-service/", "LINK",
     "R4 investigative journalism (Gannett / USA TODAY Network)",
     "Copyrighted newspaper content (Gannett). LINK posture: link to the article, never re-host; Gannett ToS forbids bulk extraction / re-publication."),
]
for sid, name, home, terms, custody, tier_desc, note in OKC:
    is_news = custody == "LINK"
    add(
        id=sid, name=name, homepage=home, terms_url=terms,
        robots="honor (terms not fetched verbatim this pass).",
        spdx="UNDETERMINED", redist="false", deriv="false",
        verbatim=undetermined_terms(f"{tier_desc}. {note}"),
        redist_analysis=(
            "Government public record ⇒ redistributable in principle, but the row is "
            "UNDETERMINED (redistributable=false, fails export gate closed) until a reviewer "
            "fetches the portal terms and records the posture."
            if not is_news else
            "Copyrighted third-party content; NOT redistributable (LINK posture). redistributable=false — SIG links out and stores only the stable locator + minimal evidentiary quote."
        ),
        deriv_analysis=(
            "Derivatives of the underlying facts (not the prose) are permitted for government records; confirm on review."
            if not is_news else
            "No derivative/redistribution of the article body; LINK only. derivative_permitted=false."
        ),
        odbl="Not OSM-derived. No ODbL implication.",
        custody_rec=(
            f"{custody} (fetch + hold the government record)." if not is_news
            else f"{custody} — link-only; a content-fetching connector MUST NOT run against it (§8.4)."
        ),
        counsel=(
            "PARTIAL — public-record rights are clear; confirm portal access terms."
            if not is_news else
            "YES — third-party copyright / newspaper ToS; LINK posture keeps SIG clear but confirm quote length is de-minimis."
        ),
    )


TEMPLATE = """# Rights-review packet — TEMPLATE (SIG-LIC-001, P21.1)

> Copy this file to `docs/build/rights/<source_id>.md`. A packet lays out **facts**
> (quoted terms + retrieval date) separately from **judgement** (the reviewer decision
> line). It asserts **no** legal conclusion (defining standard §3.1 — no synthetic
> certainty about rights). Reading a terms/robots page is permitted research, **not**
> ingestion; do not fetch source *content*. Contact channels are organisational
> addresses only — **no personal names** (Part VIII §0.7).

- **Source id:** `<source_id>`
- **Homepage:** <url>
- **Terms URL(s) fetched:** <url> — retrieved <YYYY-MM-DD> (or: "not fetched this pass")
- **robots.txt:** <honor / honor_with_exception / not_applicable> — <summary>

## Terms (verbatim)

> Paste the verbatim quoted terms text with its retrieval date, OR state honestly that
> the terms page was not fetched and record the terms_url for the reviewer.

## SPDX candidate

`<SPDX expression or UNDETERMINED>` (accepted expressions per `policy/data/licenses.toml`).

## redistributable analysis

<separately-reviewed; never derived from the SPDX string — SIG-LIC-003>

## derivative_permitted analysis

<including any SIG-INGEST-048b linking hazard>

## ODbL compartment implications

<if OSM-derived: RISK-P0-01/02, HG-02; else "not OSM-derived">

## Custody posture recommendation

<MIRROR / DERIVE / REFERENCE / LINK — §8.4>

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: ____   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

<YES/NO/PARTIAL — SIG-LIC-009: a recorded reviewer role is not a legal opinion>
"""


def render(p: dict) -> str:
    return f"""# Rights-review packet — `{p["id"]}` ({p["name"]})

> Facts (quoted terms + retrieval date) are separated from judgement (the Decision
> line). This packet asserts no legal conclusion (defining standard §3.1). Reading the
> terms page is permitted research, not ingestion; no source *content* was fetched.

- **Source id:** `{p["id"]}`
- **Homepage:** {p["homepage"]}
- **Terms URL(s):** {p["terms_url"]}
- **robots.txt:** {p["robots"]}

## Terms (verbatim)

{p["verbatim"]}

## SPDX candidate

`{p["spdx"]}`  (accepted expressions per `policy/data/licenses.toml`)

## redistributable analysis

{p["redist_analysis"]}  → registry `redistributable = {p["redist"]}`.

## derivative_permitted analysis

{p["deriv_analysis"]}  → registry `derivative_permitted = {p["deriv"]}`.

## ODbL compartment implications

{p["odbl"]}

## Custody posture recommendation

{p["custody_rec"]}

## Decision

- [ ] permit ingestion — reviewer: ____ date: ____
- SPDX to record: `{p["spdx"]}`   rights_reviewed_by (role, never a name): ____   rights_reviewed_on: ____

## Counsel-needed flag

**{p["counsel"]}**
"""


def main() -> None:
    RIGHTS.mkdir(parents=True, exist_ok=True)
    (RIGHTS / "_TEMPLATE.md").write_text(TEMPLATE, encoding="utf-8")
    seen = set()
    for p in PACKETS:
        assert p["id"] not in seen, f"duplicate packet id {p['id']}"
        seen.add(p["id"])
        (RIGHTS / f"{p['id']}.md").write_text(render(p), encoding="utf-8")
    print(f"wrote {len(PACKETS)} packets + _TEMPLATE.md to {RIGHTS}")
    assert len(PACKETS) == 27, f"expected 27 packets, got {len(PACKETS)}"


if __name__ == "__main__":
    main()
