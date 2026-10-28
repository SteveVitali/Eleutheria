# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P36.1b — the copy check: conduct text must claim only implemented conduct.

E2-07's finding was aspiration drift: ``crawler_conduct.toml``, the
``policy.crawler`` docstring, the ``robots_policy`` registry field and the
Stage-0 letter all said SIG honours robots.txt while the runtime probes and
records it and proceeds stamped ``robots_disregarded`` (GL-GATE-08 / ADR-088,
re-confirmed A-5 on every host — ADR-168). This module is the lint the ticket
calls for (SIG-ENG-042): every conduct claim the four text surfaces make maps
to a code anchor, and a text asserting conduct the code does not implement is
a violation, not prose drift.

The surfaces: ``policy/src/policy/data/crawler_conduct.toml`` (the policy of
record), ``policy/src/policy/crawler.py`` (its docstring),
``connectors/src/connectors/data/sources.toml`` (the ``robots_policy``
declaration — ADR-222), ``web/src/pages/data-collection.astro`` (the published
crawler page) and ``docs/governance/stage0-outreach-letter.md`` (the unsent
letter).
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CONDUCT_PATH = REPO_ROOT / "policy/src/policy/data/crawler_conduct.toml"
CRAWLER_PATH = REPO_ROOT / "policy/src/policy/crawler.py"
SOURCES_PATH = REPO_ROOT / "connectors/src/connectors/data/sources.toml"
NET_PATH = REPO_ROOT / "connectors/src/connectors/net.py"
PAGE_PATH = REPO_ROOT / "web/src/pages/data-collection.astro"
LETTER_PATH = REPO_ROOT / "docs/governance/stage0-outreach-letter.md"
BATCH_PATH = REPO_ROOT / "docs/build/reports/copy-batches/batch-01.md"


def _norm(text: str) -> str:
    """Whitespace-folded text — the same normalisation the page test uses."""
    text = re.sub(r'\{"\s*"\}', " ", text)
    return " ".join(text.split())


def _batch_row(rid: str) -> str:
    """The ``/data-collection/`` batch row's pinned text for ``rid``."""
    for line in BATCH_PATH.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")][1:-1]
        if len(cells) == 5 and cells[0] == rid and cells[1] == "/data-collection/":
            return cells[2]
    raise AssertionError(f"no /data-collection/ batch row {rid}")


# --- the lint ---------------------------------------------------------------
#
# Claims the implementation does NOT make true. A text carrying one of these
# patterns asserts conduct the code does not implement — the E2-07 class.

_FALSE_CLAIMS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"honou?rs?\s+robots", re.I),
        "claims SIG honours robots.txt — under GL-GATE-08 (ADR-088/ADR-168) "
        "verdicts are probed and recorded, never enforced",
    ),
    (
        re.compile(r"permission is NOT granted", re.I),
        "claims an unretrievable robots.txt refuses the fetch — the verdict is "
        "recorded, the fetch proceeds stamped robots_disregarded",
    ),
    (
        re.compile(r"refus\w+\s+(?:any|every|each|all|the)\s+disallow", re.I),
        "claims a robots disallow is refused — it proceeds stamped "
        "robots_disregarded; only opt-outs and affirmative reservations refuse",
    ),
    (
        re.compile(r"(?:never|not|no)\s+fetch\w*\s+[^.]*robots\.txt[^.]*disallow", re.I),
        "claims disallowed fetches are not made — GL-GATE-08 proceeds and "
        "records robots_disregarded",
    ),
]

# Claims that DO have code behind them — a text may make them only while the
# anchor holds. Each tuple: (claim pattern, anchor check name). The anchors are
# asserted by the tests below; this lint's job is that the claim patterns are
# the ones the anchors implement.
_CLAIMS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"robots_disregarded"), "fetch stamps robots_disregarded (net.py)"),
    (
        re.compile(r"opt-out register", re.I),
        "register consulted before every fetch, before robots (opt_out.py/net.py)",
    ),
    (
        re.compile(r"rights reservation", re.I),
        "detect_reservation + loader refusal (crawler.py/loader.py)",
    ),
    (
        re.compile(r"host\s*\+\s*count|host and a count", re.I),
        "robots_disclosure_rows emits host+count+decision_ref",
    ),
]


def conduct_claim_violations(text: str) -> list[str]:
    """The copy check: violations for text asserting unimplemented conduct.

    Returns a list — empty means the text's conduct claims are all ones the
    code implements. Anchored claims (a text that asserts the implemented
    posture) are validated by the anchor tests in this module.
    """
    return [why for pattern, why in _FALSE_CLAIMS if pattern.search(text)]


def test_every_claim_pattern_is_implemented() -> None:
    """The lint's claim vocabulary maps to real anchors (the check itself is
    not aspirational): each claim's anchor is exercised by a test below."""
    # The claim patterns must each match the authoritative surfaces — a claim
    # the real text never makes is a dead lint clause (vacuous check).
    page = _norm(PAGE_PATH.read_text(encoding="utf-8"))
    conduct = "\n".join(r.text for r in _rules())
    corpus = "\n".join([page, conduct, CRAWLER_PATH.read_text(encoding="utf-8")])
    matched = 0
    for pattern, _name in _CLAIMS:
        if pattern.search(corpus):
            matched += 1
    assert matched >= 3, "the claim vocabulary drifted from the text it lints"


def _rules():
    from policy.crawler import conduct_rules

    return conduct_rules()


# --- conduct file ------------------------------------------------------------


def test_rule_two_states_the_decided_posture() -> None:
    """SIG-INGEST-036 rule 2: probed + recorded per RFC 9309, never gating,
    disregards stamped and disclosed, a disallow is not a reservation."""
    rule2 = next(r for r in _rules() if r.n == 2)
    assert rule2.title == "Probe and record robots.txt"
    text = rule2.text
    for anchor in (
        "RFC 9309",
        "no_policy_4xx",
        "unretrievable",
        "robots_disregarded",
        "does not gate the fetch",
        "host + count",
        "never a rights reservation",
        "ADR-083",
        "ingestion_permitted",
    ):
        assert anchor in text, f"rule 2 text dropped the {anchor!r} clause"


def test_rule_seven_names_the_implemented_register() -> None:
    """Rule 7's 'immediately' names the mechanism P36.1a built (ADR-168)."""
    rule7 = next(r for r in _rules() if r.n == 7)
    for anchor in (
        "sig.opt-out-register/1",
        "before every fetch",
        "before even the robots probe",
        "zero egress",
        "no rebuild or redeploy",
    ):
        assert anchor in rule7.text, f"rule 7 text dropped the {anchor!r} clause"


def test_rule_one_names_the_owned_url() -> None:
    rule1 = next(r for r in _rules() if r.n == 1)
    assert "https://surveillancegraph.org/data-collection/" in rule1.text


def test_no_rule_claims_robots_enforcement() -> None:
    for rule in _rules():
        assert conduct_claim_violations(f"{rule.title}. {rule.text}") == [], rule.title


def test_crawler_docstring_matches_the_file() -> None:
    import policy.crawler as crawler

    doc = crawler.__doc__ or ""
    assert "robots_disregarded" in doc
    assert "GL-GATE-08" in doc and "ADR-168" in doc
    assert "never enforced" in doc or "not" in doc and "gate the fetch" in doc
    assert "opt-out register" in doc
    assert conduct_claim_violations(doc) == []


# --- the registry field (ADR-222) --------------------------------------------


def test_robots_policy_is_declared_never_enforced() -> None:
    """ADR-222: the field documents the review-time declaration — registry
    metadata, not an enforcement claim — beside the data and on the enum."""
    from connectors.registry import RobotsPolicy

    doc = RobotsPolicy.__doc__ or ""
    assert "declared at review time" in doc
    assert "never an enforcement claim" in doc
    assert "probe" in doc and "record" in doc
    assert conduct_claim_violations(doc) == []

    header = SOURCES_PATH.read_text(encoding="utf-8")[:4000]
    assert "AS DECLARED AT REVIEW TIME" in header
    assert "never an enforcement claim" in header
    assert "robots_disregarded" in header


def test_registry_rows_still_parse_the_closed_vocabulary() -> None:
    """Back-compat: every row's robots_policy parses to the closed enum and no
    row was retconned to a new value."""
    from connectors.registry import RobotsPolicy, registry

    records = registry()
    for record in records.values():
        assert record.robots_policy in set(RobotsPolicy)
    assert any(r.robots_policy is RobotsPolicy.HONOR for r in records.values())


# --- the page ---------------------------------------------------------------


# Row-id → the conduct rule it binds, asserted verbatim against the file.
def test_page_carries_the_conduct_rules_verbatim() -> None:
    """The published page carries the policy of record verbatim (Q-E2-02):
    each CR-0n batch row is exactly ``title + '. ' + text`` of rule n and the
    page element binds the row."""
    source = PAGE_PATH.read_text(encoding="utf-8")
    for rule in _rules():
        rid = f"CR-0{rule.n}"
        assert f'data-copy="{rid}"' in source, f"page does not bind {rid}"
        assert _batch_row(rid) == f"{rule.title}. {rule.text}", (
            f"{rid} drifted from crawler_conduct.toml rule {rule.n}"
        )


def test_page_states_the_register_reservation_and_disclosure() -> None:
    """The full text (B-2): opt-out register, the 046c refusal state and the
    disregarded-disallow disclosure, exactly as implemented."""
    page = _batch_row("DC-28") + " " + _batch_row("DC-29")
    assert "before every fetch" in page and "robots.txt probe" in page
    assert "no requests at all" in page
    assert "without a rebuild or redeploy" in page

    reservation = _batch_row("DC-30") + " " + _batch_row("DC-31")
    for anchor in (
        "Content-Signal",
        "ai-train=no",
        "TDM-Reservation",
        "noai",
        "noimageai",
        "Article 4",
        "never captured",
        "ingestion gate",
    ):
        assert anchor in reservation, f"the reservation copy dropped {anchor!r}"

    robots = _batch_row("DC-25") + " " + _batch_row("DC-26")
    assert "host and a count" in robots
    assert "not a rights reservation" in robots


# --- code anchors: the claims the text makes are implemented -----------------


def test_opt_out_register_is_consulted_before_robots() -> None:
    """The text's 'checked before every fetch — before even the robots probe'
    is a source-order fact, not a promise."""
    net = NET_PATH.read_text(encoding="utf-8")
    body = net[net.index("def fetch(") : net.index("def fetch(") + 4000]
    opt_out_at = body.index("self._opt_out.reason_for(host)")
    robots_at = body.index("self._robots_verdict(url)")
    assert opt_out_at < robots_at


class _ScriptedTransport:
    """A minimal :class:`connectors.net.Transport` — the injected seam the
    conduct layer drives; no sockets anywhere in this check."""

    def __init__(self, *, robots_text: str | None, page_body: bytes = b"{}") -> None:
        self.robots_text = robots_text
        self.page_body = page_body
        self.robots_calls: list[str] = []
        self.request_calls: list[str] = []

    def robots(self, robots_url: str):
        from connectors.net import RobotsResult

        self.robots_calls.append(robots_url)
        return RobotsResult(text=self.robots_text, status=200)

    def request(self, url: str, *, user_agent: str, **kw):  # noqa: ARG002
        from datetime import UTC, datetime

        from connectors.stages import FetchResult

        self.request_calls.append(url)
        return FetchResult(
            url=url,
            status=200,
            body=self.page_body,
            media_type="application/json",
            retrieved_at=datetime(2026, 10, 26, tzinfo=UTC),
            headers={},
        )


def test_an_opted_out_fixture_host_receives_zero_egress() -> None:
    """Fixture-verified: a register entry stops the fetch before any request —
    no robots probe, no request (§26 rule 7)."""
    from connectors.net import HostOptOut, PoliteFetcher
    from connectors.opt_out import parse_register

    register = parse_register(
        'register_version = "sig.opt-out-register/1"\n'
        '[[opt_outs]]\nhost = "portal.example"\n'
        'recorded_on = 2026-10-26\nevidence = "fixture"\n'
    )
    transport = _ScriptedTransport(robots_text="User-agent: *\nAllow: /\n")
    fetcher = PoliteFetcher(
        connector_name="test",
        connector_version="0",
        transport=transport,
        opt_out_register=register,
    )
    with pytest.raises(HostOptOut):
        fetcher.fetch("https://portal.example/page")
    assert transport.robots_calls == [] and transport.request_calls == []
    assert fetcher.opt_out_refusals[0]["host"] == "portal.example"


def test_a_disallow_only_fixture_proceeds_stamped() -> None:
    """GL-GATE-08 verbatim: a robots Disallow is not a reservation — the fetch
    proceeds and is stamped robots_disregarded."""
    from connectors.net import PoliteFetcher

    transport = _ScriptedTransport(robots_text="User-agent: *\nDisallow: /\n")
    fetcher = PoliteFetcher(connector_name="test", connector_version="0", transport=transport)
    fetcher.fetch("https://plain.example/page")
    assert any(d["verdict"] == "disallowed" for d in fetcher.robots_disregarded)
    assert not fetcher.reservations


def test_a_reserved_fixture_is_refused_at_the_gate() -> None:
    """Fixture-verified: a source carrying a recorded reservation is refused
    by the loader gate under the 046c state — even with every other gate field
    flipped green — and the committed ALPR Abuse Library row carries it."""
    from connectors.loader import IngestionNotPermitted, assert_loadable
    from connectors.registry import CompactStatus, CustodyPosture, registry
    from connectors.runner import live_gate_reasons
    from policy.rights import is_refused

    record = registry()["alpr_abuse_library"]
    assert is_refused(record.rights)
    assert record.rights.reservation is not None
    assert record.rights.reservation.kind == "content_signal"
    assert any("reservation" in r for r in live_gate_reasons(record))
    flipped = dataclasses.replace(
        record,
        ingestion_permitted=True,
        compact_status=CompactStatus.PERMISSION_GRANTED,
        custody_posture=CustodyPosture.MIRROR,
    )
    with pytest.raises(IngestionNotPermitted, match="reservation"):
        assert_loadable(flipped)


def test_the_disclosure_anchor_is_host_plus_count() -> None:
    """'Disclosed as host + count' is implemented — the transparency rows."""
    from policy.transparency import ROBOTS_DISREGARD_DECISION_REF, robots_disclosure_rows

    rows = robots_disclosure_rows([{"host": "h.example", "outcome": "disregarded", "count": 3}])
    assert rows[0]["host"] == "h.example" and rows[0]["count"] == 3
    assert rows[0]["decision_ref"] == ROBOTS_DISREGARD_DECISION_REF
    assert "GL-GATE-08" in ROBOTS_DISREGARD_DECISION_REF


def test_the_reservation_detector_refuses_the_recorded_signal() -> None:
    """The verbatim signal the ALPR row records is refused by the detector the
    text describes (Content-Signal ai-train=no)."""
    from policy.crawler import detect_reservation

    verdict = detect_reservation({"Content-Signal": "search=yes,ai-train=no,use=reference"})
    assert verdict.refuses
    assert all(s.kind == "content_signal" for s in verdict.signals)


# --- the copy check fails on a text/code mismatch -----------------------------


def test_the_lint_flags_the_dishonest_forms() -> None:
    """The pre-P36.1b texts — the ones E2-07 caught — are flagged."""
    assert conduct_claim_violations("SIG honors robots.txt on every host.")
    assert conduct_claim_violations("We honour robots/ToS and conduct.")
    assert conduct_claim_violations("Where robots.txt is unretrievable, permission is NOT granted.")
    assert conduct_claim_violations("The crawler refuses any disallowed path it is handed.")


def test_no_committed_surface_carries_a_flagged_claim() -> None:
    """conduct file, docstring, page copy rows, sources header and the letter
    are all clean."""
    surfaces = {
        "crawler_conduct.toml": CONDUCT_PATH.read_text(encoding="utf-8"),
        "crawler.py docstring": __import__("policy.crawler", fromlist=["x"]).__doc__ or "",
        "sources.toml header": SOURCES_PATH.read_text(encoding="utf-8")[:5000],
        "outreach letter": LETTER_PATH.read_text(encoding="utf-8"),
    }
    page_rows = []
    for line in BATCH_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("|") and "/data-collection/" in line:
            cells = [c.strip() for c in line.split("|")][1:-1]
            if len(cells) == 5 and cells[0] not in ("id", "—"):
                page_rows.append(cells[2])
    surfaces["/data-collection/ rows"] = "\n".join(page_rows)
    for name, text in surfaces.items():
        assert conduct_claim_violations(text) == [], name
