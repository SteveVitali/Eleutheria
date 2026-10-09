# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.17 honesty-wave scans (the TS-10 successor — QW-5 covers
"permalink"/"reproducible" in `test_p34_11_claim_words.py`).

The public prose sweep: the visible text of every public page/component/layout
must never again carry the claims republish #1 removes — the "one-click" and
"anonymous" dispute promises (WV-05), "human-verified" holdout claims (R1.4),
"editorial board"/process-counsel wording (R1.5 — the pinned *disclosure*
"cleared by counsel" is the honest negation and is exempted), requirement ids
and gate names in copy (C4 NEW-20), or the fabricated review's "Releasable"
record (ADR-179).

Beyond prose: the pinned notice strings render where the wave places them, the
new public routes are registered, and the withdrawn routes stay denied.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WEB = REPO_ROOT / "web"

PUBLIC_DIRS = ["web/src/pages", "web/src/components", "web/src/layouts"]

# Forbidden claims in rendered prose, everywhere on the public surface.
FORBIDDEN_PROSE = [
    (re.compile(r"\bone[- ]click\b", re.I), "WV-05: no 'one-click' intake promise"),
    (re.compile(r"\banonymous(ly)?\b", re.I), "WV-05: e-mail senders disclose their address"),
    (re.compile(r"\bhuman[- ]verif", re.I), "R1.4: no 'human-verified' holdout claim"),
    (re.compile(r"\bpartially (human[- ])?review", re.I), "R1.4: no partial-human-review claim"),
    (re.compile(r"\beditorial board\b", re.I), "R1.5: no editorial board exists"),
    (re.compile(r"\bReleasable\b"), "ADR-179: the fabricated review status is gone"),
    (re.compile(r"\bReviewer [AB]\b"), "ADR-179: the fabricated reviewers are gone"),
    (re.compile(r"\bno account required\b", re.I), "WV-05: no account-anonymity promise"),
]

# C4 NEW-20 (no requirement ids or gate names in copy) — scoped to the files
# the wave authored or rewrote. Untouched pages carry pinned citations like
# "(SIG-METRIC-008)" that predate the wave and are copy-batch #1's business,
# not this wave's.
NO_IDS_PROSE = [
    (re.compile(r"\bSIG-[A-Z]+-\d+\b"), "C4 NEW-20: no requirement ids in copy"),
    (re.compile(r"\bHG-\d+\b"), "C4 NEW-20: no gate names in copy"),
]
WAVE_FILES = [
    "web/src/pages/dispute.astro",
    "web/src/pages/corrections.astro",
    "web/src/pages/editorial-standards.astro",
    "web/src/pages/style-guide.astro",
    "web/src/pages/methodology.astro",
    "web/src/pages/status.astro",
    "web/src/pages/sources.astro",
    "web/src/pages/terms.astro",
    "web/src/pages/data-collection.astro",
    "web/src/pages/index.astro",
    "web/src/layouts/BaseLayout.astro",
    "web/src/components/DisputeLink.astro",
]

# The honest disclosure that legitimately names "counsel" (GC-05's pinned text
# — the basis label states no counsel reviewed the publication).
COUNSEL_DISCLOSURE = "cleared by counsel"


def _strip_expressions(src: str) -> str:
    """Remove balanced ``{ ... }`` JSX expression spans (identifiers are not
    copy), honouring strings and comments inside them — the P34.11 helper's
    semantics."""
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        if src[i] == "{":
            depth = 1
            i += 1
            while i < n and depth:
                c = src[i]
                if c == "{":
                    depth += 1
                    i += 1
                elif c == "}":
                    depth -= 1
                    i += 1
                elif c in "\"'`":
                    quote = c
                    i += 1
                    while i < n and src[i] != quote:
                        i += 2 if src[i] == "\\" else 1
                    i += 1
                elif src[i : i + 2] == "//":
                    while i < n and src[i] != "\n":
                        i += 1
                elif src[i : i + 2] == "/*":
                    i += 2
                    while i < n and src[i : i + 2] != "*/":
                        i += 1
                    i += 2
                else:
                    i += 1
        else:
            out.append(src[i])
            i += 1
    return "".join(out)


def _visible_text(path: Path) -> str:
    src = path.read_text(encoding="utf-8")
    parts = src.split("---", 2)
    template = parts[2] if len(parts) == 3 else src
    template = _strip_expressions(template)
    template = re.sub(r"<!--.*?-->", " ", template, flags=re.S)
    template = re.sub(r"<[^>]*>", " ", template)
    return template


def _public_astro() -> list[Path]:
    files: list[Path] = []
    for base in PUBLIC_DIRS:
        for path in (REPO_ROOT / base).rglob("*.astro"):
            if "internal" in path.parts:
                continue
            files.append(path)
    return sorted(files)


def test_no_forbidden_claim_in_public_prose() -> None:
    offenders: list[str] = []
    for path in _public_astro():
        text = _visible_text(path)
        for pat, why in FORBIDDEN_PROSE:
            for m in pat.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                offenders.append(f"{path.relative_to(REPO_ROOT)}:{line}: {m.group(0)!r} — {why}")
    assert offenders == [], "forbidden claims in rendered public prose:\n" + "\n".join(offenders)


def test_no_requirement_ids_or_gate_names_in_wave_copy() -> None:
    offenders: list[str] = []
    for rel in WAVE_FILES:
        path = REPO_ROOT / rel
        text = _visible_text(path)
        for pat, why in NO_IDS_PROSE:
            for m in pat.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                offenders.append(f"{rel}:{line}: {m.group(0)!r} — {why}")
    assert offenders == [], "internal ids in wave copy:\n" + "\n".join(offenders)


def test_counsel_appears_only_as_the_honest_disclosure() -> None:
    offenders: list[str] = []
    for path in _public_astro():
        text = _visible_text(path)
        scrubbed = text.replace(COUNSEL_DISCLOSURE, "")
        for m in re.finditer(r"\bcounsel\b", scrubbed, re.I):
            line = text.count("\n", 0, m.start()) + 1
            offenders.append(
                f"{path.relative_to(REPO_ROOT)}:{line}: 'counsel' outside the pinned disclosure"
            )
    assert offenders == [], (
        "R1.5: 'counsel' may only appear in the pinned no-counsel disclosure:\n"
        + "\n".join(offenders)
    )


def test_dispute_page_states_email_intake_truthfully() -> None:
    text = _visible_text(WEB / "src/pages/dispute.astro")
    assert "e-mail" in text
    assert "promises no response time" in text
    assert "privacy-harm and safety reports first" in text
    assert "Not operating yet." in text  # N-2 verbatim
    template = (WEB / "src/pages/dispute.astro").read_text()
    assert "data-intake-email" in template or "INTAKE_EMAIL_MARKER" in template


def test_notice_strings_render_verbatim_where_pinned() -> None:
    # Some notices sit inside JSX conditionals (N-1 under `review === null`,
    # N-4 under `creditUnderCorrection`), so this checks the raw template —
    # the `data-notice` marker is asserted alongside the literal text.
    expectations = {
        "web/src/pages/editorial-standards.astro": ("N-1", "Not yet performed."),
        "web/src/pages/410.astro": (
            "N-6",
            "This page has been removed while a correction is made.",
        ),
        "web/src/pages/status.astro": (
            "N-7",
            "The API's dossier and terms responses are known to be wrong and are being corrected.",
        ),
        "web/src/pages/terms.astro": (
            "N-7",
            "The API's dossier and terms responses are known to be wrong and are being corrected.",
        ),
        "web/src/pages/sources.astro": (
            "N-4",
            "Attribution for this source is being corrected; see the source's own terms.",
        ),
        "web/src/pages/dispute.astro": ("N-2", "Not operating yet."),
    }
    for rel, (nid, notice) in expectations.items():
        template = (REPO_ROOT / rel).read_text(encoding="utf-8")
        assert f'data-notice="{nid}"' in template, f"{rel}: data-notice={nid} marker missing"
        assert notice in template, f"{rel}: notice string missing — {notice!r}"


def test_new_routes_registered_and_withdrawn_routes_denied() -> None:
    allowlist = (REPO_ROOT / "ops/public_routes.toml").read_text(encoding="utf-8")
    assert '"sources"' in allowlist and '"status"' in allowlist
    denied = re.findall(r'path = "(/[^"]+/)"', allowlist)
    assert "/visual-language/" in denied
    for dead in ("/curate/", "/task/new/", "/releases/", "/research-dossier/", "/intake/"):
        assert dead in denied, f"{dead} must stay denied"
    # The e2e registry covers the new pages.
    registry = (WEB / "tests/e2e/pages.ts").read_text(encoding="utf-8")
    assert '"/sources/"' in registry and '"/status/"' in registry


def test_public_pages_carry_no_internal_route_links() -> None:
    """No public page links to the withdrawn surfaces (the P34.11 test covers
    the older set; /visual-language/ joins it here)."""
    withdrawn = re.compile(
        r'href="(?:/(?:contribution-back|visual-language|research-dossier'
        r"|releases|curate|intake)/?)"
    )
    offenders: list[str] = []
    for path in _public_astro():
        if withdrawn.search(path.read_text(encoding="utf-8")):
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert offenders == [], f"withdrawn-route links remain: {offenders}"


def test_publish_gate_refuses_unconfirmed_copy_and_unset_intake() -> None:
    """The republish-#1 gate exists in the one publish path (B-2 in code)."""
    src = (REPO_ROOT / "ops/src/ops/publish.py").read_text(encoding="utf-8")
    assert "check_publishable_copy" in src
    assert "data-copy" in src and "confirmed" in src
    assert 'data-intake-email="unset"' in src
