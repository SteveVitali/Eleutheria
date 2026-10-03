# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""P34.11 / QW-5 claim-word scan for the public .astro surface.

Until real ``/s/`` pins exist (D-J3-6/P36.66b), no public page may call a link a
"permalink" or claim a citation stays "reproducible". The check sweeps the
VISIBLE text of every public page, component and layout — frontmatter code,
``//`` and ``<!-- -->`` comments, ``{...}`` expressions and tag attributes are
all stripped first, so identifiers (``data-testid="permalink"``,
``beliefPinnedPermalink``) are exempt while rendered prose is not.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

CLAIM_WORDS = re.compile(r"\bpermalink|reproducible\b", re.IGNORECASE)

PUBLIC_DIRS = ["web/src/pages", "web/src/components", "web/src/layouts"]


def _strip_expressions(src: str) -> str:
    """Remove balanced ``{ ... }`` JSX expression spans, honouring strings and
    comments inside them, so only literal markup text remains."""
    out: list[str] = []
    i, n = 0, len(src)
    while i < n:
        ch = src[i]
        if ch == "{":
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
                elif c == "/" and i + 1 < n and src[i + 1] == "/":
                    while i < n and src[i] != "\n":
                        i += 1
                elif c == "/" and i + 1 < n and src[i + 1] == "*":
                    i += 2
                    while i + 1 < n and not (src[i] == "*" and src[i + 1] == "/"):
                        i += 1
                    i += 2
                else:
                    i += 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _visible_text(path: Path) -> str:
    src = path.read_text(encoding="utf-8")
    # Frontmatter is code, not copy.
    parts = src.split("---", 2)
    template = parts[2] if len(parts) == 3 else src
    template = _strip_expressions(template)
    template = re.sub(r"<!--.*?-->", " ", template, flags=re.S)
    # Tags (and their attributes) are markup, not copy.
    template = re.sub(r"<[^>]*>", " ", template)
    return template


def _public_astro_files() -> list[Path]:
    files: list[Path] = []
    for base in PUBLIC_DIRS:
        for path in (REPO_ROOT / base).rglob("*.astro"):
            if "internal" in path.parts:
                continue
            files.append(path)
    return sorted(files)


def test_no_public_prose_claims_permalink_or_reproducible() -> None:
    offenders: list[str] = []
    for path in _public_astro_files():
        text = _visible_text(path)
        for m in CLAIM_WORDS.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{line}: {m.group(0)!r}")
    assert offenders == [], (
        "QW-5: 'permalink'/'reproducible' in rendered public text — "
        "a link records the as-of pair, it is not a pin:\n" + "\n".join(offenders)
    )


def test_every_public_page_scanned_is_real() -> None:
    # Guard: the scan must actually cover the public surface, not silently glob
    # nothing if the tree moves.
    files = _public_astro_files()
    assert len(files) >= 30
    names = {p.name for p in files}
    assert "index.astro" in names and "BaseLayout.astro" in names
