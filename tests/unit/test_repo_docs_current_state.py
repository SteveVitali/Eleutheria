# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P33.7 human-facing docs refresh — guard the current-state claims that were stale.

Pins the honest Round-10 posture the refresh landed (deployed + public, but the
provisional release is staging-only, intake non-operational, evaluation deferred)
so a future edit cannot silently reintroduce the pre-launch "nothing is deployed /
no live fetch" framing — or, conversely, overstate the staged candidate as served.
The refresh report itself is asserted to exist.

"Must not contain a known-stale claim" guards are kept as written. "Must state the
current posture" checks are derived from the records the wording describes (the
DEFERRALS row, the committed intake gate, the governance directory), never pinned
to today's values, so a legitimate activation or a new policy document does not
turn them red (BM-TEST-01; SEED-03 / PKG-02 ED-11).
"""

import pathlib
import re
import tomllib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

_NUMBER_WORDS = {
    word: n
    for n, word in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve thirteen "
        "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split()
    )
}


def _read(rel: str) -> str:
    return (REPO_ROOT / rel).read_text(encoding="utf-8")


def _site_host() -> str:
    """The canonical host, derived from the astro config's `site:` field so a
    legitimate cutover never turns this test red (BM-TEST-01 — reference
    resolution, not a literal pin)."""
    match = re.search(
        r'^\s*site:\s*"https?://([^"/]+)', _read("web/astro.config.mjs"), re.M
    )
    assert match, "web/astro.config.mjs no longer declares its canonical site"
    return match.group(1)


def _deferral_lead(oid: str) -> str:
    """The leading status token of one DEFERRALS row (the register's own word)."""
    for line in _read("docs/tickets/DEFERRALS.md").splitlines():
        if line.startswith(f"| {oid} |"):
            cell = line.rstrip().rstrip("|").rsplit("|", 1)[-1]
            words = cell.replace("*", " ").split()
            return words[0].upper() if words else ""
    raise AssertionError(f"DEFERRALS.md has no {oid} row")


def test_refresh_report_exists() -> None:
    assert (REPO_ROOT / "docs/build/reports/DOCS_REFRESH_REPORT_R10.md").is_file()


def test_readme_states_deployed_public_surface() -> None:
    readme = _read("README.md")
    assert _site_host() in readme, "README no longer names the canonical host"
    for stale in (
        "not a running service",
        "nothing is deployed",
        "no source has been fetched live",
        "twelve fixture-tested connectors",
    ):
        assert stale not in readme, f"stale pre-launch claim reintroduced: {stale!r}"


def test_readme_round10_honest_bounds() -> None:
    """The README's bounds follow the records they describe: while production
    exposure is still owed (D-R10-PUBLISH-1 OPEN/PARTIAL) the README names that
    obligation and the staged-only posture; while the committed intake gate is
    off it says the receiver is not operating — and once the gate is on, it may
    no longer claim `operational=false`."""
    readme = _read("README.md")
    if _deferral_lead("D-R10-PUBLISH-1") in {"OPEN", "PARTIAL"}:
        assert "D-R10-PUBLISH-1" in readme
        assert "staging" in readme.lower()
    operational = tomllib.loads(_read("ops/config.toml"))["intake"]["operational"]
    assert isinstance(operational, bool)
    if operational:
        assert "operational=false" not in readme
    else:
        assert "operational=false" in readme or "receiver_not_operating" in readme


def test_changelog_current_limitations_are_honest() -> None:
    changelog = _read("CHANGELOG.md")
    assert "no source has been fetched live" not in changelog
    assert _site_host() in changelog, "CHANGELOG no longer names the canonical host"
    # The P22.3 relocation repaired: no live reference to the old pre-move path.
    assert "docs/build/PUBLICATION_CHECKLIST.md`" not in changelog
    assert "docs/build/FIRST_JURISDICTION_REPORT.md" not in changelog


def test_ops_readme_go_public_is_executed_not_deferred() -> None:
    ops = _read("ops/README.md")
    assert "are **not** ticked" not in ops
    assert "GO-PUBLIC EXECUTED" in ops or "executed" in ops
    assert "docs/build/FIRST_JURISDICTION_REPORT.md" not in ops
    assert "docs/build/reports/PUBLICATION_CHECKLIST.md" in ops


def test_web_readme_names_the_opt_in_islands() -> None:
    web = _read("web/README.md")
    for island in ("/map/", "/network/", "/search/"):
        assert island in web


def test_governance_readme_counts_all_documents() -> None:
    """The index's spelled-out count equals the governance documents actually
    present, and every one of them is linked from the index."""
    gov = _read("docs/governance/README.md")
    docs = sorted(
        p.name for p in (REPO_ROOT / "docs/governance").glob("*.md") if p.name != "README.md"
    )
    assert docs, "docs/governance/ holds no policy documents"
    counts = re.findall(r"\b([A-Z][a-z]+) documents\.", gov)
    assert counts, "docs/governance/README.md no longer states its document count"
    assert [_NUMBER_WORDS.get(c.lower()) for c in counts] == [len(docs)], (
        f"README states {counts} documents; docs/governance/ holds {len(docs)}"
    )
    unlinked = [name for name in docs if f"]({name})" not in gov]
    assert not unlinked, f"governance documents missing from the index: {unlinked}"


def test_docs_index_lists_evaluation_packet() -> None:
    assert "evaluation/" in _read("docs/README.md")
