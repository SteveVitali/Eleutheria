# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The standalone-download renderer (K6 §5.1, P36.19's dedicated policy).

An inline figure draws its meaning from the page stylesheet (``var(--sig-*)``
on the kit's classes). A *downloaded* figure cannot see the page — the
dedicated SVG response policy (P36.19: ``default-src 'none'``,
``style-src 'unsafe-inline'``, sandboxed, ``nosniff``) lets it carry exactly
one ``<style>`` block. This module produces that document: the same figure
bytes plus a style block whose values are the *same* ``--sig-*`` literals —
resolved through the lexicon's declared bindings and the token mirror, so a
standalone figure reads identically on- and off-page, in light and dark.

The emitted file still passes the full safety contract apart from the one
permitted ``<style>`` element — no scripts, no events, no external fetches,
no ``data-*`` (SIG-UI-134).
"""

from __future__ import annotations

from .lexicon import Lexicon, load_lexicon
from .model import FigureKitError
from .serialize import assert_svg_safe
from .tokens import sig_token_value

_XML_DECL = '<?xml version="1.0" encoding="UTF-8"?>\n'

#: The figure classes' style rules — the mirror of the ``/* P36.27 */`` block
#: in ``web/src/styles/epistemic.css``. Colours come from ``--fig-*`` custom
#: properties defined per document so the same rules serve light and dark.
_RULES = """.sig-fig{max-width:100%;height:auto;background:var(--fig-bg)}
.sig-fig-outline{fill:none;stroke:var(--fig-ink);stroke-width:1.4}
.sig-fig-provisional{stroke:var(--fig-provisional);stroke-dasharray:5 3}
.sig-fig-child{fill:var(--fig-surface-2);stroke:var(--fig-rule-strong);stroke-width:.8}
.sig-fig-child-uncovered{fill:url(#fig-hatch)}
.sig-fig-child-pending{stroke-dasharray:3 3}
.sig-fig-hatch-line{stroke:var(--fig-absence);stroke-width:1}
.sig-fig-area{fill:var(--fig-data-fill);stroke:var(--fig-data);stroke-width:1}
.sig-fig-point{fill:var(--fig-data);stroke:var(--fig-bg);stroke-width:1}
.sig-fig-src-single.sig-fig-area,.sig-fig-src-single.sig-fig-point{fill:none;stroke:var(--fig-data);stroke-width:1.4}
.sig-fig-contested{fill:none;stroke:var(--fig-contested);stroke-width:1.4}
.sig-fig-locator-inset{stroke:var(--fig-ink);stroke-dasharray:2 2;fill:none}
.sig-fig-node{fill:var(--fig-data);stroke:var(--fig-bg);stroke-width:1}
.sig-fig-centre{fill:var(--fig-ink)}
.sig-fig-node-group{fill:none;stroke:var(--fig-data);stroke-width:1.4}
.sig-fig-node-label{fill:var(--fig-ink);font-size:var(--fig-font-xs)}
.sig-fig-edge{fill:none;stroke:var(--fig-ink);stroke-width:1.4}
.sig-fig-edge-muted{stroke:var(--fig-ink-muted)}
.sig-fig-edge-acc-declared{stroke-dasharray:5 3}
.sig-fig-sector{fill:none;stroke:var(--fig-rule-strong);stroke-width:.8}
.sig-fig-axis{fill:none;stroke:var(--fig-rule-strong);stroke-width:1}
.sig-fig-axis-label{fill:var(--fig-ink-muted);font-size:var(--fig-font-xs)}
.sig-fig-bar{fill:var(--fig-data)}
.sig-fig-mark{fill:var(--fig-data);stroke:var(--fig-bg);stroke-width:1}
.sig-fig-mark-label{fill:var(--fig-ink);font-size:var(--fig-font-xs)}
.sig-fig-legend{fill:var(--fig-ink-muted);font-size:var(--fig-font-xs)}
.sig-fig-series-0{fill:var(--fig-series-0)}
.sig-fig-series-1{fill:var(--fig-series-1)}
.sig-fig-series-2{fill:var(--fig-series-2)}
.sig-fig-series-3{fill:var(--fig-series-3)}
.sig-fig-series-4{fill:var(--fig-series-4)}
.sig-fig-series-5{fill:var(--fig-series-5)}
.sig-fig-series-6{fill:var(--fig-series-6)}
.sig-fig-series-7{fill:var(--fig-series-7)}
.sig-fig-series-8{fill:var(--fig-series-8)}
"""


def _vars(lexicon: Lexicon, *, dark: bool) -> str:
    """The ``--fig-*`` bindings for one colour scheme — every value resolved
    through the lexicon's declared token names (``legend.dataHue.token``
    etc.), never a hard-coded palette."""
    pairs = {
        "fig-bg": "sig-bg",
        "fig-surface-2": "sig-surface-2",
        "fig-rule-strong": "sig-rule-strong",
        "fig-ink": "sig-ink",
        "fig-ink-muted": "sig-ink-muted",
        "fig-data": lexicon.data_hue_token,
        "fig-data-fill": "sig-data-seq-400",
        "fig-contested": lexicon.mark_token(lexicon.contested_token),
        "fig-provisional": lexicon.mark_token(lexicon.provisional_token),
        "fig-absence": "sig-epi-absence-ink",
        # The stacked-series ramp — interleaved steps of the sequential blue
        # ramp for local contrast + the neutral 'other' (K5's 8+1 ceiling).
        "fig-series-0": "sig-data-seq-400",
        "fig-series-1": "sig-data-seq-200",
        "fig-series-2": "sig-data-seq-600",
        "fig-series-3": "sig-data-seq-300",
        "fig-series-4": "sig-data-seq-700",
        "fig-series-5": "sig-data-seq-100",
        "fig-series-6": "sig-data-seq-500",
        "fig-series-7": "sig-data-1",
        "fig-series-8": "sig-rule-strong",
    }
    body = ";".join(f"--{k}:{sig_token_value(v, dark=dark)}" for k, v in pairs.items())
    # --fig-font-xs mirrors --sig-step--2 (0.8125rem = 13px): a literal
    # because a downloaded SVG resolves rem against its own root anyway.
    return f".sig-fig{{{body};--fig-font-xs:13px}}"


def standalone_document(svg: str, lexicon: Lexicon | None = None) -> str:
    """Wrap an emitted figure in the standalone download document.

    Deterministic: the ``<style>`` block is generated entirely from the
    lexicon + token mirror, inserted directly after the ``<svg …>`` opening
    tag, before ``<title>``/``<desc>``.
    """
    lex = lexicon or load_lexicon()
    if not svg.startswith("<svg"):
        raise FigureKitError("standalone_document expects emitted figure bytes")
    insert_at = svg.index(">") + 1
    style = (
        "<style>"
        + _vars(lex, dark=False)
        + "@media (prefers-color-scheme:dark){"
        + _vars(lex, dark=True)
        + "}"
        + _RULES
        + "</style>"
    )
    doc = _XML_DECL + svg[:insert_at] + style + svg[insert_at:]
    return assert_svg_safe(doc, allow_style_block=True)


__all__ = ["standalone_document"]
