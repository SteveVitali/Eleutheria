# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The Python mirror of ``web/src/lib/design-tokens.ts`` (SIG-UI-146).

``web/src/styles/tokens.css`` is the single source of truth for every colour
value; non-CSS consumers take the *same* literals from a mirror table. The TS
mirror resolves lexicon-bound names for the browser islands; this mirror does
the same for the standalone figure renderer — which must inline literal
values because a downloaded SVG carries its own ``<style>`` block under the
dedicated response policy (P36.19, SIG-UI-144) and cannot see the page's
custom properties.

``tests/exports/test_figure_kit.py`` pins every entry byte-equal to the
``tokens.css`` declaration it names (the same drift rule
``web/tests/unit/design-tokens.test.ts`` enforces on the TS side) — a forked
palette fails the build.
"""

from __future__ import annotations

from .model import FigureKitError

#: ``--sig-*`` name → light literal, for every token the figure kit's
#: standalone style block needs. Keys are the full token names (leading
#: ``sig-`` included, as the lexicon binds them).
SIG_TOKEN_VALUES_LIGHT: dict[str, str] = {
    "sig-bg": "hsl(240deg 14.3% 98.6%)",
    "sig-surface": "hsl(0deg 0% 100%)",
    "sig-surface-2": "hsl(216deg 23.8% 95.9%)",
    "sig-rule": "hsl(218.2deg 15.1% 85.7%)",
    "sig-rule-strong": "hsl(219.1deg 9.8% 53.9%)",
    "sig-ink": "hsl(218.2deg 20% 10.8%)",
    "sig-ink-muted": "hsl(220deg 10.3% 39.8%)",
    "sig-link": "hsl(213.1deg 71.9% 39%)",
    "sig-epi-disagree-mark": "hsl(337.3deg 59.2% 49%)",
    "sig-epi-disagree-text": "hsl(336.6deg 61.5% 40.8%)",
    "sig-epi-provisional-mark": "hsl(38.9deg 100% 36.3%)",
    "sig-epi-provisional-text": "hsl(36.1deg 100% 27.1%)",
    "sig-epi-absence-ink": "hsl(220deg 11.8% 40%)",
    "sig-data-1": "hsl(212.8deg 67.7% 50.2%)",
    "sig-data-seq-400": "hsl(213deg 82% 56.5%)",
    "sig-data-seq-700": "hsl(214deg 78% 23.5%)",
}

#: The ``prefers-color-scheme: dark`` rebinds — same names, the dark literals
#: a standalone figure must carry (K14 §4.7: dark mode must work everywhere,
#: including downloaded SVGs).
SIG_TOKEN_VALUES_DARK: dict[str, str] = {
    "sig-bg": "hsl(217.5deg 16% 9.8%)",
    "sig-surface": "hsl(220deg 17.1% 13.7%)",
    "sig-surface-2": "hsl(218.6deg 15.9% 17.3%)",
    "sig-rule": "hsl(220deg 14.8% 23.9%)",
    "sig-rule-strong": "hsl(220deg 10.1% 46.7%)",
    "sig-ink": "hsl(222.9deg 17.9% 92.4%)",
    "sig-ink-muted": "hsl(220deg 12.9% 68%)",
    "sig-link": "hsl(212.6deg 76.6% 73.1%)",
    "sig-epi-disagree-mark": "hsl(337.7deg 68.8% 61%)",
    "sig-epi-disagree-text": "hsl(339.1deg 84.1% 75.3%)",
    "sig-epi-provisional-mark": "hsl(42.7deg 88.7% 38.2%)",
    "sig-epi-provisional-text": "hsl(40.1deg 84.8% 66.5%)",
    "sig-epi-absence-ink": "hsl(220deg 15.4% 65.7%)",
    "sig-data-1": "hsl(212.8deg 76.8% 56.1%)",
    "sig-data-seq-400": "hsl(213deg 82% 56.5%)",
    "sig-data-seq-700": "hsl(213deg 85% 89.4%)",
}


def sig_token_value(name: str, dark: bool = False) -> str:
    """Resolve a ``--sig-*`` token name to its literal — fail-closed, exactly
    like the TS ``sigTokenValue``: a name the mirror does not carry is a
    build-time error, never a silent default."""
    key = name if name.startswith("sig-") else f"sig-{name}"
    table = SIG_TOKEN_VALUES_DARK if dark else SIG_TOKEN_VALUES_LIGHT
    value = table.get(key, SIG_TOKEN_VALUES_LIGHT.get(key))
    if value is None:
        raise FigureKitError(
            f"token {name!r} is not in the figure-kit token mirror — the "
            "lexicon may only bind tokens mirrored in figures/tokens.py"
        )
    return value


__all__ = ["SIG_TOKEN_VALUES_DARK", "SIG_TOKEN_VALUES_LIGHT", "sig_token_value"]
