# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.79 / R11-K13-SRCH-00 — the held-out search relevance set (D-K3-7 [B-28] = b).

A **separate agent context** (this row) authors the >= 40-query held-out set
that SIG-SRCH-013's measured-relevance acceptance (SRCH-07, P36.71) judges the
search stack against. The set is labelled ``agent-authored held-out set; not
independent`` wherever it or its metric appears (SIG-CONF-012 — an estimand
label, never a claim of real-world precision).

The seal (B-28 = b; ADR-228):

* The set's **bytes are never committed** — only their sha256 lands in the
  repo (the ``sig.held-out-relevance-descriptor/1`` under
  ``docs/build/reports/p36.79-held-out-relevance/``). The bytes live as ONE
  restricted-bucket object written by the named OM-14 mutation
  (``ops/gcp/held-out-seal.sh``); bucket versioning + the committed digest is
  the restore point.
* **Deterministic re-derivation** — a resumed ``live_verification=true`` run
  re-derives byte-identical bytes: the generator reads its subject pool from
  committed registries **at a pinned commit** (``git show PIN:path``) and every
  slot's query surface is rendered by a closed-vocabulary transform. No wall
  clock, no environment, no ordering luck enters the bytes.
* **No read path in the repo.** Tuning contexts (P36.31, P36.32, P36.38…40)
  see the descriptor's digest only; the acceptance row reads the sealed
  object. The emit machinery lives here in the ops seal lane — a module under
  the production-mutation surface, never under ``exports``/``web``/``api``
  where benchmark readers live. ``tests/ops/test_held_out_relevance.py``
  fails if any emitted query text lands in a committed file or any module
  outside the seal surface imports this one.
* The recipe is the **committed generation method** (the contract's words):
  slot selectors are opaque registry positions + closed transforms, so the
  authored act — category mix, subject selection, surface form, judgement —
  is recorded and auditable while the rendered queries stay out of the tree.

Subject pool: the committed source registry and acquisition target registries
at ``PIN_COMMIT`` — names a release reader could plausibly type because they
are what SIG actually holds (or, for the honest rows, deliberately does not).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

#: The D-K3-7 [B-28] = b label — carried verbatim wherever the set or its
#: metric is emitted (SIG-CONF-012; the metric is estimand-labelled, never
#: presented as real-world precision).
HELD_OUT_LABEL = "agent-authored held-out set; not independent"

SET_SCHEMA = "sig.held-out-relevance-set/1"
DESCRIPTOR_SCHEMA = "sig.held-out-relevance-descriptor/1"
SEAL_SCHEMA = "sig.held-out-relevance-seal/1"

SET_ID = "sig.held-out.search-relevance/2026-10"
TICKET = "P36.79"
CATALOG_ID = "R11-K13-SRCH-00"
DECISION = (
    "D-K3-7 [B-28] = b (answered 2026-10-01T04:41:11Z): a separate agent "
    "context writes the >= 40-query held-out set, labelled 'agent-authored "
    "held-out set; not independent', before and never visible to the "
    "contexts that tune search (P36.31, P36.32, P36.38-P36.40)"
)
READER = "R11-K13-SRCH-07 (P36.71 — the search acceptance row)"
READER_RULE = (
    "readers: the acceptance row R11-K13-SRCH-07 (P36.71) only; tuning "
    "contexts (P36.31, P36.32, P36.38…P36.40) read the committed "
    "sig.held-out-relevance-descriptor/1 — the digest — and never this set"
)

#: The restricted-bucket object the OM-14 mutation writes (the ONE named
#: production mutation of the row; bucket versioning + the committed digest
#: is the restore point).
OBJECT_PREFIX = "search/held-out/"
OBJECT_NAME = "sig.held-out-relevance-set-1.json"

#: The commit the subject pool is read from — the orchestrator's P36.79
#: dispatch boundary (the branch base). Pinned forever, so a resumed run on
#: a much later tip re-derives identical bytes.
PIN_COMMIT = "80d71cf153c5ef45780bae6966f89ee81d3a9233"

SOURCES_TOML = "connectors/src/connectors/data/sources.toml"
CAMREG_TOML = "connectors/src/connectors/data/camera_registry_targets.toml"
DOT511_TOML = "connectors/src/connectors/data/dot_511_targets.toml"
PINNED_INPUTS = (SOURCES_TOML, CAMREG_TOML, DOT511_TOML)

REPO_ROOT = Path(__file__).resolve().parents[3]

# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------

#: Subject pool tables: (path, toml-section) — ``sources`` is the registry
#: table of ``[sources.<key>]`` rows; ``targets`` is ``[[targets]]``.
_TABLES = {
    "sources": (SOURCES_TOML, "sources"),
    "camreg": (CAMREG_TOML, "targets"),
    "dot511": (DOT511_TOML, "targets"),
}

#: US state / subdivision codes → display names (generic gazetteer data,
#: never set content). Covers every ``state`` code a slot selects.
_ADMIN1_NAMES = {
    "DC": "District of Columbia",
    "IA": "Iowa",
    "ID": "Idaho",
    "KY": "Kentucky",
    "LA": "Louisiana",
    "MD": "Maryland",
    "MO": "Missouri",
    "NV": "Nevada",
    "OR": "Oregon",
    "UT": "Utah",
    "WA": "Washington",
    "WV": "West Virginia",
    "US-MD": "Maryland",
    "US-NV": "Nevada",
    "US-WV": "West Virginia",
    "US-ID": "Idaho",
    "AU-ACT": "Australian Capital Territory",
    "AU-QLD": "Queensland",
    "CA-AB": "Alberta",
    "CA-BC": "British Columbia",
    "CA-MB": "Manitoba",
    "CA-ON": "Ontario",
    "GB-ENG": "England",
    "GB-SCT": "Scotland",
    "CO-MET": "Meta",
    "IE-DL": "Donegal",
    "NZ": "New Zealand",
}

#: ``technology`` registry keys → the search phrase a reader would type
#: (generic vocabulary mapping, never the judgement). Only keys a slot
#: selects need an entry.
_TECH_PHRASES = {
    "alpr-fixed": "ALPR cameras",
    "ate-red-light": "red light camera",
    "ate-speed": "speed camera",
    "ate-unspecified": "automated enforcement camera",
    "camera-trailer-unspecified": "mobile camera trailer",
    "fixed-camera-cctv": "CCTV camera",
    "private-camera-integration-live-feeds": "private camera integration",
    "uas-general": "police drone flights",
}

#: Alias/acronym expansions a reader expects the alias card to show. Generic
#: vocabulary (the reviewable expansion + its source is what SRCH-007/D05
#: shows) — only acronyms a slot selects need an entry.
_ACRONYM_EXPANSIONS = {
    "ALPR": "automatic license plate reader",
    "CCTV": "closed-circuit television",
    "DHS": "Department of Homeland Security",
    "FOIA": "Freedom of Information Act",
    "LPR": "license plate reader",
    "RTCC": "real-time crime center",
    "UAS": "unmanned aircraft system",
}

#: Query surface forms — the closed vocabulary that renders a slot's query
#: text from its resolved registry row. No surface renders a literal the
#: recipe carries: the emitted query text never appears in this file.
_SURFACES = {
    "city",  # agency/name → the city it names
    "admin1",  # row.state → the admin-1 display name
    "code",  # row.state → the bare code a reader may type
    "initials",  # name → its ALL-CAPS initials ("New York City" → NYC)
    "agency",  # the full agency string
    "agency_first",  # agency before " / " or " ("
    "source_name",  # the source row's name
    "source_id",  # the source registry key itself (identifier lookup)
    "source_domain",  # homepage_url / url host
    "target_id",  # the target row's id (identifier lookup)
    "id_phrase",  # an id's tokens title-cased ("…_green_light_…" → words)
    "acronym",  # first ALLCAPS token (>=3 chars) in the resolved name
    "tech",  # row.technology → _TECH_PHRASES
    "pick",  # word ``pick`` of the resolved name/id tokens, title-cased
    "pick_suffix",  # pick + " " + a fixed benign suffix word
    "pick_phrase",  # ``suffix`` id tokens from ``pick``, title-cased
    "acronym_pick",  # the ``pick``-th ALLCAPS token (>=3 chars) in the name
    "typo_drop",  # deterministic misspelling (one interior vowel dropped)
    "typo_swap",  # deterministic misspelling (adjacent letters swapped)
    "gibberish",  # derived nonsense token — never a real subject
    "badge_query",  # "officer <derived> badge <NNNN>" — honest (Part VIII)
    "plate_query",  # "<derived> plate" — honest (plates never resolve)
}

_KINDS = {
    "place-city",
    "place-admin1",
    "place-code",
    "place-initials",
    "acronym",
    "technology",
    "org-vendor",
    "org-agency",
    "record-label",
    "source-name",
    "source-domain",
    "identifier",
    "typo",
    "negative",
    "honest-gated",
    "honest-contract",
    "honest-person",
}

_JUDGEMENTS = {"top3", "honest"}

_EXPECTED_TYPES = {"place", "source", "organization", "technology", "alias", "none"}

#: The benign suffix vocabulary ``pick_suffix`` draws on (generic search
#: words — never a subject).
_SUFFIX_WORDS = ("cameras", "cctv", "contract", "policy", "alpr")


@dataclass(frozen=True)
class Slot:
    """One authored slot: an opaque selector + a closed surface + a judgement.

    ``table``/``index`` select the registry row at PIN_COMMIT; ``surface``
    renders the query text; ``pick`` (word index) and ``suffix``
    (_SUFFIX_WORDS index) parameterise the pick surfaces. ``expect`` /
    ``expect_ref`` name the expected result type and what it must match —
    ``"subject"`` resolves to the slot's own subject at emit time.
    """

    id: str
    kind: str
    table: str
    index: int
    surface: str
    judgement: str
    expect: str  # _EXPECTED_TYPES member
    expect_of: str  # "subject" | "resolved" | "" (none)
    pick: int = 0
    suffix: int = -1
    note: str = ""


# ---------------------------------------------------------------------------
# The authored recipe — >= 40 slots. Selectors are opaque registry positions
# at PIN_COMMIT; the rendered query text never appears in this file.
# ---------------------------------------------------------------------------

_SLOTS: tuple[Slot, ...] = (
    # --- places: city names a reader types (agency → city) ----------------
    Slot("H01", "place-city", "camreg", 3, "city", "top3", "place", "subject"),
    Slot("H02", "place-city", "camreg", 8, "city", "top3", "place", "subject"),
    Slot("H03", "place-city", "camreg", 12, "city", "top3", "place", "subject"),
    Slot("H04", "place-city", "camreg", 26, "city", "top3", "place", "subject"),
    Slot("H05", "place-city", "camreg", 28, "city", "top3", "place", "subject"),
    Slot("H06", "place-city", "camreg", 36, "city", "top3", "place", "subject"),
    Slot("H07", "place-city", "camreg", 163, "city", "top3", "place", "subject"),
    Slot("H08", "place-city", "camreg", 181, "city", "top3", "place", "subject"),
    Slot("H09", "place-city", "camreg", 255, "city", "top3", "place", "subject"),
    # --- places: admin-1 names a reader types ------------------------------
    Slot("H10", "place-admin1", "dot511", 2, "admin1", "top3", "place", "subject"),
    Slot("H11", "place-admin1", "dot511", 3, "admin1", "top3", "place", "subject"),
    Slot("H12", "place-admin1", "dot511", 11, "admin1", "top3", "place", "subject"),
    Slot("H13", "place-admin1", "dot511", 17, "admin1", "top3", "place", "subject"),
    Slot("H14", "place-admin1", "dot511", 22, "admin1", "top3", "place", "subject"),
    # --- places: codes + initials ------------------------------------------
    Slot("H15", "place-code", "camreg", 36, "code", "top3", "place", "subject"),
    Slot("H16", "place-code", "camreg", 11, "code", "top3", "place", "subject"),
    Slot("H17", "place-initials", "camreg", 190, "initials", "top3", "place", "subject"),
    # --- acronyms (the alias card / expansion is the expected item) --------
    Slot("H18", "acronym", "sources", 28, "acronym_pick", "top3", "alias", "resolved", pick=1),
    Slot("H19", "acronym", "sources", 501, "acronym", "top3", "alias", "resolved"),
    Slot("H20", "acronym", "sources", 48, "acronym", "top3", "alias", "resolved"),
    Slot("H21", "acronym", "camreg", 272, "acronym", "top3", "alias", "resolved"),
    # --- technologies ------------------------------------------------------
    Slot("H22", "technology", "camreg", 24, "tech", "top3", "technology", "subject"),
    Slot("H23", "technology", "camreg", 275, "tech", "top3", "technology", "subject"),
    Slot("H24", "technology", "camreg", 21, "tech", "top3", "technology", "subject"),
    Slot("H25", "technology", "camreg", 260, "tech", "top3", "technology", "subject"),
    # --- organisations: vendors --------------------------------------------
    Slot("H26", "org-vendor", "sources", 19, "pick", "top3", "organization", "resolved", pick=0),
    Slot("H27", "org-vendor", "sources", 523, "pick", "top3", "organization", "resolved", pick=3),
    Slot("H28", "org-vendor", "sources", 522, "pick", "top3", "organization", "resolved", pick=2),
    Slot("H29", "org-vendor", "sources", 568, "pick", "top3", "organization", "resolved", pick=5),
    # --- organisations: agencies -------------------------------------------
    Slot("H30", "org-agency", "camreg", 18, "agency_first", "top3", "organization", "subject"),
    Slot("H31", "org-agency", "camreg", 241, "agency_first", "top3", "organization", "subject"),
    Slot("H32", "org-agency", "camreg", 262, "agency_first", "top3", "organization", "subject"),
    Slot("H33", "org-agency", "camreg", 263, "agency_first", "top3", "organization", "subject"),
    Slot("H34", "org-agency", "dot511", 0, "agency", "top3", "organization", "subject"),
    # --- sources: names + domains + ids ------------------------------------
    Slot("H35", "source-name", "sources", 17, "source_name", "top3", "source", "subject"),
    Slot("H36", "source-name", "sources", 27, "source_name", "top3", "source", "subject"),
    Slot("H37", "source-name", "sources", 558, "source_name", "top3", "source", "subject"),
    Slot("H38", "source-name", "sources", 33, "source_name", "top3", "source", "subject"),
    Slot("H39", "source-domain", "sources", 8, "source_domain", "top3", "source", "subject"),
    Slot("H40", "source-domain", "sources", 23, "source_domain", "top3", "source", "subject"),
    Slot("H41", "source-domain", "camreg", 0, "source_domain", "top3", "source", "subject"),
    # --- identifiers --------------------------------------------------------
    Slot("H42", "identifier", "sources", 195, "source_id", "top3", "source", "subject"),
    Slot("H43", "identifier", "camreg", 188, "target_id", "top3", "source", "subject"),
    # --- programme / record-flavoured phrases -------------------------------
    Slot(
        "H44",
        "record-label",
        "camreg",
        260,
        "pick_phrase",
        "top3",
        "place",
        "subject",
        pick=0,
        suffix=3,
    ),
    Slot("H45", "org-agency", "dot511", 6, "agency", "top3", "organization", "subject"),
    # --- typos (suggestion leg; expected = the corrected subject) ----------
    Slot("H46", "typo", "camreg", 12, "typo_drop", "top3", "place", "subject"),
    Slot("H47", "typo", "camreg", 163, "typo_swap", "top3", "place", "subject"),
    Slot("H48", "typo", "camreg", 28, "typo_drop", "top3", "place", "subject"),
    # --- the honest set: the release cannot answer, never mislead ----------
    Slot(
        "H49",
        "negative",
        "sources",
        0,
        "gibberish",
        "honest",
        "none",
        "",
        note="nonsense token — must not match anything",
    ),
    Slot(
        "H50",
        "negative",
        "sources",
        1,
        "gibberish",
        "honest",
        "none",
        "",
        note="nonsense token — must not match anything",
    ),
    Slot(
        "H51",
        "honest-gated",
        "sources",
        533,
        "pick_suffix",
        "honest",
        "none",
        "",
        pick=5,
        suffix=1,
        note="gated source — never ingested; the release honestly cannot answer",
    ),
    Slot(
        "H52",
        "honest-gated",
        "sources",
        543,
        "source_name",
        "honest",
        "none",
        "",
        note="gated non-English dataset — never ingested; no misleading top hit",
    ),
    Slot(
        "H53",
        "honest-contract",
        "sources",
        58,
        "pick_suffix",
        "honest",
        "none",
        "",
        pick=0,
        suffix=2,
        note="no contract documents published — the honest answer is not a record hit",
    ),
    Slot(
        "H54",
        "honest-person",
        "sources",
        0,
        "badge_query",
        "honest",
        "none",
        "",
        note="Part VIII — officer/badge queries never resolve to a person",
    ),
    Slot(
        "H55",
        "honest-person",
        "sources",
        1,
        "plate_query",
        "honest",
        "none",
        "",
        note="Part VIII — plate lookups never resolve to record data",
    ),
)


# ---------------------------------------------------------------------------
# Pinned-input loading (deterministic: git show PIN:path, digest-pinned)
# ---------------------------------------------------------------------------


class SealError(RuntimeError):
    """A fail-closed seal/generation error — never a guessed row."""


def _git_show_pinned(path: str) -> bytes:
    """Read ``path`` at PIN_COMMIT via ``git show`` — the immutable input."""
    try:
        out = subprocess.run(
            ["git", "show", f"{PIN_COMMIT}:{path}"],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - git absent
        raise SealError(f"git unavailable — cannot read pinned input {path}") from exc
    if out.returncode != 0:
        raise SealError(
            f"pinned input {path} unreadable at {PIN_COMMIT[:12]}: "
            f"{out.stderr.decode('utf-8', 'replace').strip()[:200]}"
        )
    return out.stdout


def _load_table(name: str) -> list[tuple[str, dict[str, Any]]]:
    """Load one subject table at the pin → ordered (key, row) pairs."""
    path, section = _TABLES[name]
    doc = tomllib.loads(_git_show_pinned(path).decode("utf-8"))
    rows = doc.get(section)
    if not isinstance(rows, (list, dict)):
        raise SealError(f"{name}: section {section} missing in {path}")
    if isinstance(rows, dict):  # the sources registry: key → row
        return [(k, v) for k, v in rows.items() if isinstance(v, dict)]
    return [(str(r.get("id") or r.get("source_id") or f"row{i}"), r) for i, r in enumerate(rows)]


def _table_row(slot: Slot) -> tuple[str, dict[str, Any]]:
    rows = _load_table(slot.table)
    if not (0 <= slot.index < len(rows)):
        raise SealError(f"{slot.id}: {slot.table}[{slot.index}] out of range ({len(rows)})")
    return rows[slot.index]


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[\s_/()—-]+", text) if t and t[0].isalnum()]


_CITY_STOP = {
    "Transportation",
    "Department",
    "Public",
    "Works",
    "Police",
    "Traffic",
    "Management",
    "Safety",
    "Services",
    "GIS",
    "Division",
    "Bureau",
    "County",
    "Commission",
    "District",
    "Agency",
}


def _city_from_agency(agency: str) -> str:
    """Deterministic city extraction over the used agency shapes."""
    a = agency.strip()
    m = re.match(r"^(?:City and County of|City of|Town of|Regional Municipality of)\s+(.+)$", a)
    if m:
        run = m.group(1).split(",")[0].split("(")[0].split("/")[0].strip()
        words = [w for w in run.split() if w and w[0].isupper() and w not in _CITY_STOP]
        if words:
            return " ".join(dict.fromkeys(words))
    for pat in (
        r"^([^(/,]+?) City Council\b",
        r"^([^(/,]+?) Borough Council\b",
        r"^([^(/,]+?) County Council\b",
        r"^Alcaldía de ([^(/,]+?),",
        r"^([^(/,]+?) City \(",
        r"^(District of Columbia)\b",
        r"^([^(/,]+?) County[,\s]",
        r"^([^(/,]+?) (?:Police Department|Sheriff|Department of)\b",
    ):
        m = re.match(pat, a)
        if m:
            return m.group(1).strip()
    raise SealError(f"city surface: no pattern for agency {agency!r}")


def _stable_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:12], 16)


def _render(slot: Slot, key: str, row: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Render a slot's query text + resolved expectation.

    Returns (query, expected). ``expected`` is ``{"type": …}`` plus the
    resolved ``match``/``ref`` the acceptance harness checks against —
    resolved at emit time so the recipe stays opaque.
    """
    agency = str(row.get("agency") or "")
    name = str(row.get("name") or "")
    state = str(row.get("state") or "")
    tech = str(row.get("technology") or "")
    url = str(row.get("homepage_url") or row.get("url") or "")
    subject = key  # the registry key or row id

    def expect_place() -> dict[str, Any]:
        ref = state or subject
        return {"type": "place", "match": _PLACE_MATCH.get(slot.id, ref), "of": subject}

    def expect_none() -> dict[str, Any]:
        return {"type": "none"}

    surface = slot.surface
    if surface == "city":
        query = _city_from_agency(agency)
        exp = expect_place()
        exp["match"] = query
    elif surface == "admin1":
        if state not in _ADMIN1_NAMES:
            raise SealError(f"{slot.id}: state {state!r} has no admin-1 name")
        query = _ADMIN1_NAMES[state]
        exp = {"type": "place", "match": query, "of": subject}
    elif surface == "code":
        query = state
        exp = {"type": "place", "match": _ADMIN1_NAMES.get(state, state), "of": subject}
    elif surface == "initials":
        words = [w for w in re.split(r"\s+", agency.split("(")[0].strip()) if w]
        if len(words) < 2:
            raise SealError(f"{slot.id}: initials surface needs a multiword agency {agency!r}")
        query = "".join(w[0].upper() for w in words)
        exp = {"type": "place", "match": agency.split("(")[0].strip(), "of": subject}
    elif surface == "agency":
        query = agency
        exp = {"type": "organization", "match": agency, "of": subject}
    elif surface == "agency_first":
        query = re.split(r"\s+[/(]", agency, maxsplit=1)[0].strip()
        exp = {"type": "organization", "match": query, "of": subject}
    elif surface == "source_name":
        query = name
        exp = {"type": "source", "id": subject}
    elif surface == "source_id":
        query = subject
        exp = {"type": "source", "id": subject}
    elif surface == "target_id":
        query = key
        exp = {"type": "source", "id": str(row.get("source_id") or subject)}
    elif surface == "source_domain":
        host = re.sub(r"^https?://", "", url).split("/")[0]
        if not host or "." not in host:
            raise SealError(f"{slot.id}: no host in {url!r}")
        query = host
        exp = {"type": "source", "id": str(row.get("source_id") or subject)}
    elif surface == "id_phrase":
        query = " ".join(t.capitalize() for t in _tokens(key) if t.lower() not in _ID_STOP)
        exp = {"type": "place", "match": query, "of": subject}
    elif surface == "acronym":
        toks = _tokens(name or key)
        acr = next((t for t in toks if t.isupper() and len(t) >= 3), None)
        if acr is None and tech in _TECH_ACRONYMS:
            acr = _TECH_ACRONYMS[tech]
        if acr is None or acr not in _ACRONYM_EXPANSIONS:
            raise SealError(f"{slot.id}: no known acronym in {name or key!r}")
        query = acr
        exp = {"type": "alias", "expansion": _ACRONYM_EXPANSIONS[acr], "of": subject}
    elif surface == "tech":
        if tech not in _TECH_PHRASES:
            raise SealError(f"{slot.id}: technology {tech!r} has no phrase")
        query = _TECH_PHRASES[tech]
        exp = {"type": "technology", "id": tech, "of": subject}
    elif surface == "pick":
        toks = _tokens(name or key)
        if not (0 <= slot.pick < len(toks)):
            raise SealError(f"{slot.id}: pick {slot.pick} out of {len(toks)} tokens")
        tok = toks[slot.pick]
        query = tok.capitalize() if tok.islower() else tok
        exp = {"type": "organization", "match": query, "of": subject}
    elif surface == "pick_suffix":
        toks = _tokens(name or key)
        if not (0 <= slot.pick < len(toks)) or not (0 <= slot.suffix < len(_SUFFIX_WORDS)):
            raise SealError(f"{slot.id}: pick/suffix out of range")
        tok = toks[slot.pick]
        query = f"{tok.capitalize() if tok.islower() else tok} {_SUFFIX_WORDS[slot.suffix]}"
        exp = expect_none()
    elif surface == "pick_phrase":
        toks = _tokens(key)
        if not (0 <= slot.pick < len(toks)) or not (0 < slot.suffix <= len(toks) - slot.pick):
            raise SealError(
                f"{slot.id}: pick_phrase {slot.pick}+{slot.suffix} out of {len(toks)} tokens"
            )
        query = " ".join(t.capitalize() for t in toks[slot.pick : slot.pick + slot.suffix])
        exp = {"type": "place", "match": _city_from_agency(agency), "of": subject}
    elif surface == "acronym_pick":
        toks = [t for t in _tokens(name or key) if t.isupper() and len(t) >= 3]
        if not (0 <= slot.pick < len(toks)) or toks[slot.pick] not in _ACRONYM_EXPANSIONS:
            raise SealError(f"{slot.id}: acronym_pick {slot.pick} unresolved")
        query = toks[slot.pick]
        exp = {"type": "alias", "expansion": _ACRONYM_EXPANSIONS[query], "of": subject}
    elif surface in ("typo_drop", "typo_swap"):
        base = _city_from_agency(agency)
        query = _misspell(slot, base)
        exp = {"type": "place", "match": base, "of": subject, "expects_suggestion": True}
    elif surface == "gibberish":
        h = hashlib.sha256(f"held-out:{slot.id}".encode()).hexdigest()
        query = f"zx{h[:2]}-{h[2:8]}"
        exp = expect_none()
    elif surface == "badge_query":
        n = int(hashlib.sha256(f"badge:{slot.id}".encode()).hexdigest()[:8], 16)
        query = f"officer badge {n % 10000:04d} camera list"
        exp = expect_none()
    elif surface == "plate_query":
        n = int(hashlib.sha256(f"plate:{slot.id}".encode()).hexdigest()[:8], 16)
        query = f"{n % 1000:03d}XYZ plate reader hits"
        exp = expect_none()
    else:
        raise SealError(f"{slot.id}: unknown surface {surface!r}")

    if slot.expect == "none":
        exp = expect_none()
    elif slot.expect in {"place", "organization", "source", "technology", "alias"}:
        exp["type"] = slot.expect if exp.get("type") != "none" else exp["type"]
        if slot.expect == "source" and "id" not in exp:
            exp["id"] = subject
    if slot.judgement == "honest":
        exp = expect_none()
    return query, exp


_ID_STOP = {
    "camreg",
    "gb",
    "au",
    "us",
    "eng",
    "sct",
    "nir",
    "on",
    "ab",
    "mb",
    "bc",
    "nsw",
    "vic",
    "qld",
    "tas",
    "wa",
    "tx",
    "ca",
    "il",
    "fl",
    "ga",
    "co",
    "nc",
    "tn",
    "va",
    "ct",
    "al",
    "ny",
    "md",
    "nv",
    "in",
    "of",
    "the",
    "and",
    "a",
    "an",
    "as",
    "at",
    "by",
    "for",
    "or",
    "to",
    "via",
}

_TECH_ACRONYMS = {"uas-general": "UAS", "alpr-fixed": "ALPR"}

#: Slots whose ``place`` match differs from the rendered query (alt forms):
#: e.g. an initials query expects the expanded name, not the initials.
_PLACE_MATCH: dict[str, str] = {}


def _misspell(slot: Slot, base: str) -> str:
    """Deterministic misspelling — interior position chosen by the slot id."""
    letters = [i for i, c in enumerate(base) if c.isalpha() and 0 < i < len(base) - 1]
    if not letters:
        raise SealError(f"{slot.id}: cannot misspell {base!r}")
    pos = letters[_stable_int(slot.id) % len(letters)]
    if slot.surface == "typo_swap" and pos + 1 < len(base):
        return base[:pos] + base[pos + 1] + base[pos] + base[pos + 2 :]
    return base[:pos] + base[pos + 1 :]


# ---------------------------------------------------------------------------
# The emitted artifact
# ---------------------------------------------------------------------------


def build_set() -> dict[str, Any]:
    """Build the ``sig.held-out-relevance-set/1`` document — deterministic."""
    seen: set[str] = set()
    queries: list[dict[str, Any]] = []
    for slot in _SLOTS:
        key, row = _table_row(slot)
        query, expected = _render(slot, key, row)
        query = " ".join(query.split()).strip()
        if not query:
            raise SealError(f"{slot.id}: empty query")
        if query.lower() in seen:
            raise SealError(f"{slot.id}: duplicate query {query!r}")
        seen.add(query.lower())
        entry: dict[str, Any] = {
            "id": slot.id,
            "kind": slot.kind,
            "query": query,
            "judgement": slot.judgement,
            "answerable": slot.judgement == "top3",
            "expected": expected,
            "selector": {"table": slot.table, "index": slot.index, "of": key},
        }
        if slot.note:
            entry["note"] = slot.note
        queries.append(entry)
    top3 = sum(1 for q in queries if q["judgement"] == "top3")
    return {
        "schema": SET_SCHEMA,
        "record_type": SET_SCHEMA,
        "set_id": SET_ID,
        "label": HELD_OUT_LABEL,
        "decision": DECISION,
        "authored_by": {
            "context": f"{TICKET} implement-spec worker — a separate agent context (B-28 = b)",
            "ticket": TICKET,
            "manifest_row": 371,
            "catalog": CATALOG_ID,
        },
        "metric": {
            "estimand_label": HELD_OUT_LABEL,
            "cite": (
                "SIG-CONF-012 — the metric is estimand-labelled wherever it "
                "appears; never presented as real-world precision"
            ),
            "targets": (
                "SIG-SRCH-013 — held-out top-3 success >= 80% on answerable "
                "queries; 0 misleading top hits on the honest set; zero-result "
                "rate reported"
            ),
        },
        "access": {
            "reader": READER,
            "rule": READER_RULE,
            "seal": "restricted-bucket object; only its sha256 is committed",
        },
        "generation": {
            "method": "ops.held_out_relevance build_set()",
            "pin_commit": PIN_COMMIT,
            "inputs": [
                {"path": p, "sha256": hashlib.sha256(_git_show_pinned(p)).hexdigest()}
                for p in PINNED_INPUTS
            ],
        },
        "counts": {
            "queries": len(queries),
            "top3": top3,
            "honest": len(queries) - top3,
        },
        "queries": queries,
    }


def canonical_bytes(doc: dict[str, Any]) -> bytes:
    return (
        json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


def emit_bytes() -> bytes:
    return canonical_bytes(build_set())


def set_sha256() -> str:
    return hashlib.sha256(emit_bytes()).hexdigest()


def object_uri(project: str) -> str:
    return f"gs://{project}-sig-restricted/{OBJECT_PREFIX}{OBJECT_NAME}"


def descriptor(project: str = "<project>") -> dict[str, Any]:
    """The committed ``sig.held-out-relevance-descriptor/1`` — digest only.

    This is the ONLY artefact tuning contexts read: it carries the label, the
    object locator, the reader rule and the digest — never a set row.
    """
    blob = emit_bytes()
    return {
        "schema": DESCRIPTOR_SCHEMA,
        "record_type": DESCRIPTOR_SCHEMA,
        "set_id": SET_ID,
        "label": HELD_OUT_LABEL,
        "metric_label": HELD_OUT_LABEL,
        "sha256": hashlib.sha256(blob).hexdigest(),
        "bytes": len(blob),
        "object": object_uri(project),
        "status": "prepared_not_executed",
        "sealed_at": None,
        "reader": READER,
        "rule": READER_RULE,
        "generation": build_set()["generation"],
    }


def verify_object(blob: bytes, expect_sha256: str) -> bool:
    """The acceptance check: candidate object bytes == the committed digest."""
    return hashlib.sha256(blob).hexdigest() == expect_sha256


def packet(
    *,
    status: str = "prepared_not_executed",
    planned_at: str,
    author: str | None = None,
    window: str = "any time outside 03:00-10:00Z",
    rerun: str,
    project: str = "<project>",
) -> dict[str, Any]:
    """The committed ``sig.held-out-relevance-seal/1`` packet (OM-19)."""
    doc = build_set()
    blob = canonical_bytes(doc)
    return {
        "schema": SEAL_SCHEMA,
        "record_type": SEAL_SCHEMA,
        "set_id": SET_ID,
        "label": HELD_OUT_LABEL,
        "status": status,
        "planned_at": planned_at,
        "sha256": hashlib.sha256(blob).hexdigest(),
        "bytes": len(blob),
        "counts": doc["counts"],
        "object": object_uri(project),
        "authority": (
            "GATE-G5 §4 (2026-10-25T18:40Z, LEDGER GATE DECISIONS): "
            '"pre-authorise the 13 named 11C OM-20 rows: P35.2, P35.23, '
            "P36.13, P36.33, P36.43, P36.44, P36.46, P36.68, P36.75, P36.76, "
            'P36.77, P36.78, P36.79" — P36.79 named verbatim; expires GATE-G6'
        ),
        "mutation": (
            "one restricted-bucket object write (the sealed set); restore "
            "point = bucket versioning + this committed digest"
        ),
        "window": window,
        "author_env": "SIG_HELDOUT_AUTHOR (the recorded operator id, OM-20 scope discipline)",
        "queue": {
            "reason": (
                "hosted env absent at this row — no ADC, SIG_GCP_PROJECT unset; "
                "the write stays armed, never fabricated"
            ),
            "rerun": rerun,
            "env_required": [
                "SIG_GCP_PROJECT",
                "ADC (gcloud auth application-default)",
                "SIG_HELDOUT_AUTHOR",
                "gcloud storage on PATH",
            ],
        },
        "access": {"reader": READER, "rule": READER_RULE},
        "generation": doc["generation"],
        "notes": [
            (
                "the set's bytes are committed only as this sha256 — a resumed run "
                "re-derives deterministically from PIN_COMMIT inputs"
            ),
            (
                "no fixture, reader or export in the repo carries a set row — the "
                "seal boundary is asserted by tests/ops/test_held_out_relevance.py"
            ),
            "the metric is estimand-labelled wherever it appears (SIG-CONF-012)",
        ],
    }


def census() -> dict[str, int]:
    """The slot census — counts only, never content (the packet's summary)."""
    out: dict[str, int] = {}
    for s in _SLOTS:
        out[s.kind] = out.get(s.kind, 0) + 1
    return dict(sorted(out.items()))


# ---------------------------------------------------------------------------
# CLI — `sig-ops held-out …` (the seal lane; ops only)
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="sig-ops held-out",
        description=(
            "the P36.79 held-out search relevance set — emit/digest/descriptor/"
            "check/verify. The bytes are the sealed object; the repo carries "
            "the digest only (B-28 = b)."
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_emit = sub.add_parser("emit", help="write the canonical set bytes")
    p_emit.add_argument(
        "--out", required=True, help="output path (a gitignored/uncommitted location)"
    )
    sub.add_parser("digest", help="print the set's sha256")
    p_desc = sub.add_parser("descriptor", help="print the committed descriptor JSON")
    p_desc.add_argument("--project", default="<project>")
    sub.add_parser("check", help="resolve every slot + print the census (offline)")
    p_ver = sub.add_parser("verify", help="verify a candidate object against a digest")
    p_ver.add_argument("path")
    p_ver.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)

    if args.cmd == "emit":
        blob = emit_bytes()
        Path(args.out).write_bytes(blob)
        print(f"emit ok — {len(blob)} B sha256:{hashlib.sha256(blob).hexdigest()} -> {args.out}")
        return 0
    if args.cmd == "digest":
        print(set_sha256())
        return 0
    if args.cmd == "descriptor":
        print(json.dumps(descriptor(args.project), indent=2, sort_keys=True))
        return 0
    if args.cmd == "check":
        doc = build_set()
        c = census()
        print(
            f"held-out check ok — {doc['counts']['queries']} queries "
            f"({doc['counts']['top3']} top3 / {doc['counts']['honest']} honest), "
            f"{len(c)} kinds, pin {PIN_COMMIT[:12]}"
        )
        for k, n in c.items():
            print(f"  {k}: {n}")
        return 0
    if args.cmd == "verify":
        blob = Path(args.path).read_bytes()
        if verify_object(blob, args.sha256):
            print(f"verify ok — sha256:{args.sha256} matches {args.path}")
            return 0
        print(
            f"verify REFUSED — {args.path} sha256:{hashlib.sha256(blob).hexdigest()} "
            f"!= {args.sha256}",
            file=sys.stderr,
        )
        return 4
    return 64


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
