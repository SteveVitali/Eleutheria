# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.16 public-repo honesty guard (F-189, G2 0c; ADR-163/164/165/167/180/182).

Invariant: the public repository presents no editorial board, no counsel
review and no counsel document as existing.

- The source registry's ``rights_reviewed_by`` values never name "counsel";
  the five entries re-recorded under ADR-167 carry the fixed vocabulary
  ``the operator's own determination (no counsel)`` verbatim.
- ``docs/governance/**`` makes no board/counsel claim outside correction
  context: struck-through text (``~~…~~``), verbatim operator quotes
  (blockquotes) and the appended ``## Corrections`` section are the
  correction itself, not claims. Landed ADR bodies, build history and
  planning notes are excluded by the contract (never edited), as are the
  dated records inside ``docs/build/``.
- The correction is in place, not a deletion: the struck statements still
  carry ``~~…~~`` with a dated pointer, the ``## Corrections`` section
  states the posture only in the operator's adopted sentences (quoted
  verbatim), the 2026-09-15 legal-home text is untouched, and no
  "who runs SIG" section exists (C-5, "Omit until I write it").
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GOV_DIR = REPO_ROOT / "docs" / "governance"
GOV_DOC = GOV_DIR / "governance-and-code-of-conduct.md"
SOURCES = REPO_ROOT / "connectors/src/connectors/data/sources.toml"
CHECKLIST = REPO_ROOT / "docs/build/reports/PUBLICATION_CHECKLIST.md"
BATCH = REPO_ROOT / "docs/build/reports/copy-batches/batch-01.md"

FIXED_VOCABULARY = "the operator's own determination (no counsel)"  # ADR-167 decision 2

# The five registry entries re-recorded by P34.16 (their recorded 2026-09-15
# determinations; the date and every other field are untouched).
RECORRECTED_SOURCES = (
    "madada",
    "declarationcamera_be",
    "carnegie_ai_gsi",
    "facial_recognition_world_map",
    "aspi_mapping_chinas_tech_giants",
)

# Operator sentences adopted by selection and quoted verbatim in the
# governance doc's Corrections section (RATIFICATION_LOG, agent-drafted and
# operator-adopted; the quotes are frozen record text, not living state).
ADOPTED_SENTENCES = (
    # WV-02 (A-23, round 9, 2026-10-01T04:28:49Z; ADR-164)
    "I waive SIG-GOV-015's editorial board: I hold interim single-maintainer "
    "editorial authority, and every naming/sensitivity decision goes in a public "
    "decision log.",
    # WV-03 (A-23, round 9; ADR-163)
    "I waive the second-reviewer role (SIG-PUB-008 / HG-11) for Round-11 "
    "releases; each readout states 'single maintainer, no second reviewer'.",
    # WV-01 (A-23, round 9; ADR-165)
    "I waive SIG-GOV-012/013 for now: SIG's legal home is me as an individual, "
    "disclosed on the site, revisited at announcement, a first legal demand, "
    "funding, or a second maintainer.",
    # WV-07 (A-23, round 9; ADR-182)
    "I waive the counsel-review clauses of SIG-LIC-009 and SIG-INGEST-037; "
    "rights decisions rest on my recorded determinations, labelled as such.",
    # C-3 (round 19, 2026-10-01T04:54:19Z; ADR-167)
    "The 'counsel' determinations of 2026-09-16 and 09-24 were my own; there "
    "was no counsel. My 09-28 message 'let's defer all the human review steps "
    "and proceed' was my decision to defer the human review legs.",
    # WV-05 (A-23 part 2, round 9; ADR-180)
    "I waive one-click, unidentified intake (SIG-GOV-001/002) for Round 11: "
    "corrections come by e-mail, and the site says plainly that senders disclose "
    "their address.",
)

# A surviving line may mention counsel only as an enumerated honest context —
# disclosure of absence, the corrected record, a conditional future, or the
# hostile-reader dossier's role-play of the *documented organisation's*
# counsel (never SIG's). Anything else is a counsel claim presented as
# current and fails.
ALLOWED_COUNSEL = re.compile(
    r"("
    r"no counsel"  # disclosure ("there is/was no counsel")
    r"|in place of (engaging )?counsel"  # operator-adopted drafts instead
    r"|real counsel"  # "supersedeable by real counsel", "Real counsel review may supersede"
    r"|may supersede|supersedes|supersedeable"  # a filed opinion would supersede
    r"|ever engaged|engaging counsel|engage counsel"  # conditional future only
    r"|pending-counsel labels"  # describing the labels the determinations replaced
    r"|waiv"  # the waiver is cited (waived/waive/waiver), not claimed
    r"|documented organi[sz]ation'?s counsel|documented org'?s counsel"  # role-play subject
    r"|vendor counsel|counsel stance|counsel objects"  # hostile-reader role-play
    r")",
    re.IGNORECASE,
)

# A surviving line may mention a board only as an enumerated context: a
# section-label citation of the waived requirement (the
# `## The editorial board (SIG-GOV-015)` heading), or the README index row
# that lists what the governance document covers ("…editorial board, capture
# resistance…") — every body claim is struck.
ALLOWED_BOARD = re.compile(r"(^#{1,6}\s.*\bSIG-GOV-015\b|editorial board,\s*capture)")

WORD = {
    "counsel": re.compile(r"\bcounsel\b", re.IGNORECASE),
    "board": re.compile(r"\bboard\b", re.IGNORECASE),
}

STRUCK = re.compile(r"~~.*?~~", re.DOTALL)
CORRECTIONS_SECTION = re.compile(r"(?ms)^## Corrections\b.*?(?=^## |\Z)")
BLOCKQUOTE = re.compile(r"^\s*>")


def _claim_surface(path: Path) -> list[tuple[int, str]]:
    """Lines a board/counsel claim could still be presented on: the file minus
    the appended ``## Corrections`` section, minus every ``~~…~~`` span, minus
    blockquote (verbatim-quote) lines. Returns ``(line_number, text)``."""
    text = path.read_text(encoding="utf-8")
    text = CORRECTIONS_SECTION.sub("", text)
    text = STRUCK.sub("", text)
    return [
        (n, line) for n, line in enumerate(text.splitlines(), start=1) if not BLOCKQUOTE.match(line)
    ]


def _registry() -> dict[str, dict]:
    return tomllib.loads(SOURCES.read_text(encoding="utf-8"))["sources"]


def test_no_counsel_reviewer_value_in_the_registry() -> None:
    """ADR-167 decision 2 / H-8: no ``rights_reviewed_by`` value names counsel —
    every past "counsel" determination is the operator's own (no counsel)."""
    # The fixed vocabulary's "(no counsel)" parenthetical is the disclosure of
    # absence, not a counsel claim; it is the only value permitted to name the
    # word at all.
    offenders = {
        name: entry["rights_reviewed_by"]
        for name, entry in _registry().items()
        if "counsel" in str(entry.get("rights_reviewed_by", "")).lower()
        and entry["rights_reviewed_by"] != FIXED_VOCABULARY
    }
    assert not offenders, f"counsel reviewer values remain in sources.toml: {offenders}"


def test_the_five_entries_carry_the_fixed_vocabulary_and_nothing_else_changed() -> None:
    """Exactly the five ADR-167 entries read the fixed vocabulary verbatim; the
    recorded 2026-09-15 determination date and the ingest posture are the
    untouched rest of each entry."""
    sources = _registry()
    fixed = [
        name
        for name, entry in sources.items()
        if entry.get("rights_reviewed_by") == FIXED_VOCABULARY
    ]
    assert sorted(fixed) == sorted(RECORRECTED_SOURCES), (
        f"expected exactly the five ADR-167 entries on the fixed vocabulary, got {fixed}"
    )
    for name in RECORRECTED_SOURCES:
        entry = sources[name]
        assert entry["rights_reviewed_by"] == FIXED_VOCABULARY
        assert str(entry["rights_reviewed_on"]) == "2026-09-15", (
            f"{name}: the recorded determination date changed — only the reviewer "
            "value is re-recorded (no date, no ingestion_permitted flip)"
        )
        assert entry["ingestion_permitted"] is True, (
            f"{name}: ingestion_permitted changed — this row flips nothing"
        )


def test_no_board_or_counsel_claim_in_governance_docs() -> None:
    """No ``docs/governance/**`` file presents a board, a counsel review or a
    counsel document as current outside struck, quoted or correction context."""
    offenders: list[str] = []
    for path in sorted(GOV_DIR.rglob("*.md")):
        rel = path.relative_to(REPO_ROOT)
        for lineno, line in _claim_surface(path):
            if WORD["counsel"].search(line) and not ALLOWED_COUNSEL.search(line):
                offenders.append(f"{rel}:{lineno}: counsel claim: {line.strip()}")
            if WORD["board"].search(line) and not ALLOWED_BOARD.search(line):
                offenders.append(f"{rel}:{lineno}: board claim: {line.strip()}")
    assert not offenders, (
        "governance text still presents a board/counsel as current:\n" + "\n".join(offenders)
    )


def test_false_statements_are_struck_in_place_not_deleted() -> None:
    """The F-189/G2-0c statements survive as ``~~…~~`` with a dated pointer —
    an in-place strike, never a silent deletion."""
    text = GOV_DOC.read_text(encoding="utf-8")
    for fragment in (
        "editorial board exists, distinct from the technical maintainers",
        "not a public launch",
        "a counsel opinion (HG-02)",
        "HG-02 counsel confirms the publication posture",
        "board's two-reviewer concurrence",
        "served\n  `/corrections` and `/dispute` mechanisms",
    ):
        m = re.search(r"~~[^~]*" + re.escape(fragment) + r"[^~]*~~", text)
        assert m, f"the false statement is missing or no longer struck: {fragment!r}"
    # Every strike carries its dated pointer: consecutive `~~…~~` spans are
    # one struck statement (the gap is punctuation), so the pointer follows
    # each contiguous strike group.
    spans = list(re.finditer(r"~~.*?~~", text, re.DOTALL))
    assert spans, "no struck text — the correction must strike in place"
    for i, m in enumerate(spans):
        if i and m.start() - spans[i - 1].end() > 8:
            group_end = spans[i - 1].end()
            window = text[group_end : group_end + 300]
            assert re.search(r"\(struck\s+2026-10-03\s+—\s+see\s+Corrections", window), (
                f"struck statement ending at byte {group_end} lacks its dated pointer"
            )
    group_end = spans[-1].end()
    window = text[group_end : group_end + 300]
    assert re.search(r"\(struck\s+2026-10-03\s+—\s+see\s+Corrections", window), (
        f"struck statement ending at byte {group_end} lacks its dated pointer"
    )


def test_corrections_section_quotes_only_the_operators_adopted_sentences() -> None:
    """The appended section is dated, points at the four named ADRs and states
    the posture only in the operator's adopted sentences, verbatim."""
    text = GOV_DOC.read_text(encoding="utf-8")
    m = CORRECTIONS_SECTION.search(text)
    assert m, "the governance doc carries no appended ## Corrections section"
    section = m.group(0)
    assert "Appended 2026-10-03" in section, "the Corrections section is not dated"
    for adr in ("ADR-163", "ADR-164", "ADR-165", "ADR-167"):
        assert adr in section, f"the Corrections section does not point to {adr}"
    flat = " ".join(" ".join(re.sub(r"^\s*> ?", "", line).split()) for line in section.splitlines())
    for sentence in ADOPTED_SENTENCES:
        assert sentence in flat, f"adopted sentence not quoted verbatim: {sentence[:60]}…"


def test_no_who_runs_sig_section_and_legal_home_text_untouched() -> None:
    """C-5 ("Omit until I write it"): no name or description of the operator
    beyond the adopted WV-01 sentence, no "who runs SIG" section, and the
    2026-09-15 legal-home paragraph is neither extended nor rewritten."""
    text = GOV_DOC.read_text(encoding="utf-8")
    assert not re.search(r"(?i)^#{1,6}.*who runs sig", text, re.MULTILINE), (
        "a 'who runs SIG' section exists — C-5 says omit it until the operator writes it"
    )
    assert (
        "**The legal home of SIG (Surveillance Infrastructure Graph) is Steven Vitali, an\n"
        "individual maintainer, operating the project in a personal capacity (2026-09-15).**"
        in text
    ), "the 2026-09-15 legal-home text was rewritten"


def test_checklist_correction_is_appended_not_rewritten() -> None:
    """PUBLICATION_CHECKLIST keeps its body and gains the dated ADR-167
    correction naming the counsel claims it corrects."""
    text = CHECKLIST.read_text(encoding="utf-8")
    assert "## 2026-10-03 — correction (P34.16; ADR-167, ADR-182" in text
    assert FIXED_VOCABULARY in text
    # The dated records stay: the GO-PUBLIC EXECUTED section is history.
    assert "2026-09-16 — GO-PUBLIC EXECUTED" in text


def _rendered(text: str) -> str:
    """The sentence as it renders — ``markup contributes no text`` (batch-01
    convention): drop backticks, asterisks (``**``/``~~``/italics) and collapse
    whitespace so a line-wrapped doc sentence equals its pinned batch text."""
    return re.sub(r"\s+", " ", re.sub(r"[`*]", "", text)).strip()


def test_corrections_section_states_posture_only_in_adopted_sentences() -> None:
    """Outside the italic header and the verbatim blockquotes, the section is
    correction apparatus only — bold labels, lead-ins that end `:` before a
    quote, and `—` pointer fragments. No unconfirmed declarative sentence."""
    text = GOV_DOC.read_text(encoding="utf-8")
    m = CORRECTIONS_SECTION.search(text)
    assert m, "the governance doc carries no appended ## Corrections section"
    section = m.group(0)
    body = section.split("\n- ", 1)
    assert len(body) == 2, "the Corrections section has no itemised entries"
    items = ("\n- " + body[1]).split("\n- ")
    for item in items:
        if not item.strip():
            continue
        lines = item.splitlines()
        has_quote = any(line.lstrip().startswith(">") for line in lines)
        apparatus = " ".join(
            line.strip() for line in lines if line.strip() and not line.lstrip().startswith(">")
        )
        apparatus = re.sub(r"^- ", "", apparatus).strip()
        label = re.match(r"^\*\*.+?\*\*", apparatus)
        assert label, f"item lacks its bold label: {apparatus[:60]}"
        rest = apparatus[label.end() :].strip()
        if has_quote:
            frags = [f.strip() for f in re.split(r"(?=: )|(?=\s—\s)", rest) if f.strip()]
            for frag in frags:
                assert frag.endswith(":") or frag.startswith(("—", "(")), (
                    f"declarative text outside a quote is not apparatus: {frag[:80]}"
                )
        else:
            assert rest.startswith("—"), (
                f"an item with no quote must be a pointer fragment: {rest[:80]}"
            )


def test_agent_drafted_further_sentences_are_pending_batch_rows() -> None:
    """B-2: every further agent-drafted sentence is a pending GC-* batch-01
    row pinned verbatim — held OUT of the doc until the operator confirms it
    verbatim ("confirmed or absent"); an agent never confirms. GC-05/GC-06
    carry ADR-167's recorded sha256s."""
    batch = BATCH.read_text(encoding="utf-8")
    doc_rows = [
        line
        for line in batch.splitlines()
        if line.startswith("| GC-") and "governance-and-code-of-conduct.md" in line
    ]
    assert doc_rows, "batch-01 carries no GC-* pending rows for the governance doc"
    doc_text = _rendered(GOV_DOC.read_text(encoding="utf-8"))
    adr_pinned = {
        "| GC-05 |": "f62f9e984c0d6d7b7a6f5065cef480d666a8da59b2a73e15c762dbf347333b4f",
        "| GC-06 |": "c7e4f78bcd07b99b9a656c2bc4e6e56a19be7fd86b5d2329b2447414348a6e02",
    }
    import hashlib

    for row in doc_rows:
        assert row.rstrip().endswith("| pending |"), (
            f"a GC-* row is not pending — an agent never confirms: {row[:80]}"
        )
        cells = [c.strip() for c in row.split("|")]
        candidate = cells[3] if len(cells) >= 5 else ""
        pinned = cells[4] if len(cells) >= 6 else ""
        assert candidate and pinned, f"malformed GC-* row: {row[:80]}"
        assert hashlib.sha256(candidate.encode("utf-8")).hexdigest() == pinned, (
            f"GC-* row's sha256 does not verify: {cells[1]}"
        )
        assert _rendered(candidate) not in doc_text, (
            f"unconfirmed candidate text shipped in the doc: {candidate[:60]}"
        )
    for prefix, sha in adr_pinned.items():
        row = next((r for r in doc_rows if r.startswith(prefix)), None)
        assert row, f"{prefix.strip()} missing from batch-01"
        assert sha in row, f"{prefix.strip()} does not carry ADR-167's recorded sha256 {sha[:12]}…"
