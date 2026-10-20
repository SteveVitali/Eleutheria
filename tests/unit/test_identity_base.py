# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P35.38b (manifest row 317, R11-SAFE-06; ADR-217) — the identity-base invariants.

Two legs, both repo checks:

1. **No new retired-domain literal.** ``sig-project.org`` (unregistered, B-6)
   and ``sig.example`` (the older placeholder) may exist only inside declared
   regions — append-only history (deployed DB changes, landed ADRs, frozen
   tickets, build memory, the research corpus), the sentinel registry that
   detects them, the compat mechanism itself, test needles, and the two
   deferral-scoped files. A literal anywhere else — shipped code, config,
   generated artifacts, new docs — fails.

2. **One declared emitter per minted base.** Each IRI namespace the system
   mints is a single declared constant in a single file; a second hard-coded
   emitter file fails (the "one declared base per surface" rule).
"""

from __future__ import annotations

import json
import subprocess

import pytest
from support import REPO_ROOT

RETIRED_DOMAINS: tuple[str, ...] = ("sig-project.org", "sig.example")

# --- leg 1: the declared regions where a retired-domain literal is history ---


def _history_region(path: str) -> bool:
    """Append-only / non-shipped regions where an old literal is a record, not a
    minted base: deployed sqitch changes + the plan (D-P35.38b-1), landed ADR
    bodies, frozen ticket contracts + the DEFERRALS register, the risk register,
    the research corpus, committed build memory (except the live tooling under
    ``docs/build/tools/``), and the test trees (needles and pins)."""
    return (
        path.startswith(("db/deploy/", "db/revert/", "db/verify/", "db/refactor/"))
        or path == "db/sqitch.plan"
        or path.startswith("docs/adr/")
        or path.startswith("docs/tickets/")
        or path.startswith("docs/research/")
        or path == "docs/risk_register.md"
        or (path.startswith("docs/build/") and not path.startswith("docs/build/tools/"))
        or path.startswith("tests/")
        or path.startswith("web/tests/")
    )


#: Files inside scanned territory that legitimately carry a retired literal —
#: each with its reason. Adding an entry needs the same declaration.
_EXEMPT_FILES: frozenset[str] = frozenset(
    {
        "ops/sentinels.toml",  # the sentinel registry — detects the literal
        "docs/build/tools/record_policy/tail_probe_sweep.toml",  # probe-sweep sentinel list
        "docs/governance/iri-base-alias-map.json",  # the compat mechanism itself
        "docs/governance/iri-base-compat-note.md",
        # D-P35.38b-2 — the published OSM organised-editing disclosure; repointing
        # it needs a provisioned contact address + real target routes + the
        # external OSM-wiki page edit (recorded debt, not a hidden literal):
        "tasks/src/tasks/data/organised_editing.toml",
        "docs/governance/organised-editing-activity.md",
        "tests/unit/test_identity_base.py",  # this guard's own needles
        # record artifacts that quote the ADR/contract text verbatim — they name
        # the retired base inside a decision description, never mint it:
        "CHANGELOG.md",  # the per-ticket changelog entry cites the ADR-217 summary
        # generated spec — Appendix F mirrors spec_src/99a_appF_adr.md, which
        # itself sits in the docs/research history region:
        "docs/2_canonical_design_spec.md",
    }
)


def _grep_files(needle: str, *pathspecs: str) -> set[str]:
    out = subprocess.run(
        ["git", "grep", "-lF", needle, "--", *pathspecs],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return {line for line in out.stdout.splitlines() if line}


@pytest.mark.parametrize("domain", RETIRED_DOMAINS)
def test_no_retired_domain_literal_outside_declared_regions(domain: str) -> None:
    hits = {p for p in _grep_files(domain) if p not in _EXEMPT_FILES and not _history_region(p)}
    assert hits == set(), (
        f"`{domain}` literal found outside the declared history/exempt regions "
        f"(ADR-217 — retired bases are never minted anew; add the file to "
        f"_EXEMPT_FILES only with a recorded reason): {sorted(hits)}"
    )


# --- leg 2: one declared emitter per minted namespace -------------------------

#: Each minted IRI prefix → the exact file set that may carry it inside scanned
#: territory (the declared constant + the ontology's declared source data).
_MINTED_PREFIX_EMITTERS: dict[str, frozenset[str]] = {
    "https://surveillancegraph.org/prov/": frozenset(
        {"exports/src/exports/provo.py"}  # ``SIG`` — the one declared constant
    ),
    "https://surveillancegraph.org/ns/": frozenset(
        {"exports/src/exports/formats.py"}  # ``SIG_NS`` — the @context pair
    ),
    "https://surveillancegraph.org/id/": frozenset(
        {"api/src/api/dereference.py"}  # the /id/ dereference base
    ),
    "https://ontology.surveillancegraph.org/": frozenset(
        {
            "ontology/src/ontology/generate.py",  # ``BASE`` — everything derives
            "docs/build/tools/build_predicates.py",  # the registry builder's BASE
            # the LinkML schema ids + ``sig:`` prefix are declared data, not a
            # second constant — generate.py is the only code that mints:
            "ontology/src/ontology/schema/common.yaml",
            "ontology/src/ontology/schema/edges.yaml",
            "ontology/src/ontology/schema/entities.yaml",
            "ontology/src/ontology/schema/sig.yaml",
            "ontology/vocab/predicates.yaml",  # per-row skos_concept_iri values
        }
    ),
}


@pytest.mark.parametrize(
    ("prefix", "emitters"),
    sorted(_MINTED_PREFIX_EMITTERS.items()),
    ids=[p.rsplit("/", 2)[-2] for p in sorted(_MINTED_PREFIX_EMITTERS)],
)
def test_one_declared_emitter_per_minted_namespace(prefix: str, emitters: frozenset[str]) -> None:
    """A minted namespace lives in exactly its declared file set (plus derived /
    exempt regions) — a second hard-coded emitter is a second base."""
    hits = _grep_files(prefix)
    scanned_hits = {
        p
        for p in hits
        if p not in _EXEMPT_FILES
        and not _history_region(p)
        and not p.startswith("ontology/generated/")  # derived from the emitters
    }
    assert scanned_hits == emitters, (
        f"`{prefix}` must be minted by exactly {sorted(emitters)} inside scanned "
        f"territory; found {sorted(scanned_hits)}"
    )
    # The declared emitters must actually carry it — a silently-drifted base
    # (an empty hit set) fails the same check from the other side.
    missing = emitters - hits
    assert missing == set(), f"declared emitter(s) lost `{prefix}`: {sorted(missing)}"


# --- the compat mechanism's own integrity -------------------------------------


def test_alias_map_is_machine_readable_append_only_and_covers_every_family() -> None:
    path = REPO_ROOT / "docs/governance/iri-base-alias-map.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["schema"] == "sig.iri-alias-map/1"
    assert data["policy"]["append_only"] is True
    assert data["policy"]["mint_base"] == "https://surveillancegraph.org"

    aliases = data["aliases"]
    families = [a["family"] for a in aliases]
    assert len(families) == len(set(families)), "alias families must be unique"
    # The family set the cutover enumerated — a new family is an append, and
    # this set growing is fine; shrinking or renaming means a rewrite.
    assert {
        "ontology-schema",
        "vocab-technology",
        "vocab-capability",
        "vocab-predicate",
        "vocab-enum-schemes",
        "vocab-crosswalk",
        "prov-lineage",
        "jsonld-context",
        "api-id-namespace",
        "ocfl-user-address",
        "watch-feed-uid",
        "crawler-contact-url",
    } <= set(families)

    for alias in aliases:
        old = str(alias["old_base"])
        new = str(alias["new_base"])
        assert any(d in old for d in RETIRED_DOMAINS), (
            f"{alias['family']}: old_base must sit on a retired domain: {old}"
        )
        assert "surveillancegraph.org" in new, (
            f"{alias['family']}: new_base must sit on the owned domain: {new}"
        )
        assert alias["match"] in {"prefix", "exact", "suffix"}
        assert alias["surfaces"] and alias["note"]


def test_compat_note_is_published_and_linked() -> None:
    note = REPO_ROOT / "docs/governance/iri-base-compat-note.md"
    text = note.read_text(encoding="utf-8")
    assert "sig-project.org" in text  # names the retired base plainly
    assert "surveillancegraph.org" in text
    assert "iri-base-alias-map.json" in text
    # not an HTTP-redirect claim — the note must say so:
    assert "redirect" in text.lower()
    readme = (REPO_ROOT / "docs/governance/README.md").read_text(encoding="utf-8")
    assert "iri-base-compat-note.md" in readme


def test_adr_217_records_the_decision() -> None:
    adr = next(REPO_ROOT.glob("docs/adr/ADR-217-*.md"), None)
    assert adr is not None, "ADR-217 (the identity-base ADR) must exist"
    text = adr.read_text(encoding="utf-8")
    assert "## Revisit trigger" in text
    assert "ADR-168" in text  # the E2 decision chain it builds on
    assert "surveillancegraph.org" in text
