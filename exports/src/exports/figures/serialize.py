# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The CSP-safe, byte-deterministic SVG serializer (P36.27, ADR-157; K6 §5.1).

One emitter for every figure the kit produces. Its contract is the output
half of the ticket:

* **byte-deterministic** — attributes serialise in declaration order,
  numbers through one formatter, children in insertion order, a trailing
  newline. Same input → same bytes, always.
* **CSP-safe** — the emitted document contains no ``<script>``, no ``on*``
  handler attributes, no ``javascript:``/``data:``/external references, no
  inline ``style=`` attributes, no ``data-*``/per-area numerals
  (SIG-UI-134). ``assert_svg_safe`` re-checks the finished bytes — defence in
  depth, not a substitute for never emitting them.
* **link-safe** — the only ``href`` values permitted are fragment references
  (``#…``) and root-relative paths (``/…``): a figure may drill down into the
  release, never out of it.
* **P36.19-compatible** — ``<style>`` blocks are emitted *only* by
  ``standalone.py`` (the dedicated download document the response policy
  serves sandboxed with ``style-src 'unsafe-inline'``); inline figures carry
  classes the page stylesheet owns.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from xml.sax.saxutils import escape, quoteattr

from .model import FigureKitError


class SvgError(FigureKitError):
    """The serializer refused an emission that would break the figure
    contract — fail-closed (SIG-ENG-042)."""


#: Tags the kit may emit — a closed vocabulary. Anything else is a bug.
_ALLOWED_TAGS = frozenset(
    {
        "svg",
        "defs",
        "pattern",
        "g",
        "path",
        "rect",
        "circle",
        "line",
        "polyline",
        "polygon",
        "text",
        "title",
        "desc",
        "a",
        "style",
    }
)

#: Attributes banned outright — the CSP/parity contract.
_BANNED_ATTRS = re.compile(r"^(on\w*|style|data-.*)$", re.I)

_SAFE_HREF = re.compile(r"^(#[A-Za-z0-9_-]+|/[A-Za-z0-9_./~-]*)$")


@dataclass
class El:
    """A deterministic element: tag, ordered attributes, ordered children."""

    tag: str
    attrs: list[tuple[str, str]] = field(default_factory=list)
    children: list[El | str] = field(default_factory=list)

    def attr(self, name: str, value: object) -> El:
        if _BANNED_ATTRS.match(name):
            raise SvgError(f"attribute {name!r} is banned in figure SVG")
        if name == "href" or name == "xlink:href":
            v = str(value)
            if not _SAFE_HREF.match(v):
                raise SvgError(f"href {v!r} is not a fragment or root-relative path")
        self.attrs.append((name, str(value)))
        return self

    def add(self, child: El | str) -> El:
        self.children.append(child)
        return self

    def render(self) -> str:
        return "".join(_render(self))


def _render(el: El) -> list[str]:
    if el.tag not in _ALLOWED_TAGS:
        raise SvgError(f"tag <{el.tag}> is not in the figure vocabulary")
    out = [f"<{el.tag}"]
    for name, value in el.attrs:
        out.append(f" {name}={quoteattr(value)}")
    if not el.children:
        out.append("/>")
        return out
    out.append(">")
    for child in el.children:
        if isinstance(child, El):
            out.extend(_render(child))
        else:
            out.append(escape(str(child)))
    out.append(f"</{el.tag}>")
    return out


def svg_root(
    viewbox: tuple[float, float],
    classes: tuple[str, ...],
    title_id: str,
    desc_id: str,
    *,
    extra: tuple[tuple[str, str], ...] = (),
) -> El:
    """The root ``<svg>`` for a figure — ``role="img"`` + ``aria-labelledby``
    into the emitted ``<title>``/``<desc>`` pair (SIG-UI-131)."""
    w, h = viewbox
    root = El("svg")
    root.attr("xmlns", "http://www.w3.org/2000/svg")
    root.attr("viewBox", f"0 0 {w:g} {h:g}")
    root.attr("class", " ".join(classes))
    root.attr("role", "img")
    root.attr("aria-labelledby", f"{title_id} {desc_id}")
    for name, value in extra:
        root.attr(name, value)
    return root


_FORBIDDEN_PATTERNS = (
    re.compile(r"<\s*script\b", re.I),
    re.compile(r"\bon\w+\s*=", re.I),
    re.compile(r"javascript\s*:", re.I),
    re.compile(r"<\s*foreignObject\b", re.I),
    # External or data references through any URL-bearing attribute.
    re.compile(r"\b(?:href|src|xlink:href)\s*=\s*['\"]\s*(?:https?:|//|data:)", re.I),
    # External fetches inside a style block (fragment url(#…) is fine).
    re.compile(r"@import\b|<\s*link\b|url\s*\(\s*['\"]?(?:https?:|//|data:)", re.I),
    re.compile(r"\bstyle\s*=", re.I),
    # No data-* attributes inside figure SVG — per-area numerals or ids would
    # leak the record layer (SIG-UI-134); figure metadata lives on the page
    # wrapper (check:figures), never in emitted bytes.
    re.compile(r"\bdata-[a-z0-9-]+\s*=", re.I),
)


def assert_svg_safe(svg: str, *, allow_style_block: bool) -> str:
    """Re-check finished figure bytes against the CSP/parity contract —
    fail-closed. ``allow_style_block`` is ``True`` only for the standalone
    download document (its dedicated policy permits the embedded style);
    inline figures must never carry a ``<style>`` element either."""
    if not allow_style_block and re.search(r"<\s*style\b", svg, re.I):
        raise SvgError("inline figure emitted a <style> block")
    for pattern in _FORBIDDEN_PATTERNS:
        m = pattern.search(svg)
        if m:
            raise SvgError(f"figure SVG violates the safety contract: {m.group(0)!r}")
    return svg


def document(el: El) -> str:
    """Render an element tree to a complete byte-stable document."""
    return el.render() + "\n"


__all__ = ["El", "SvgError", "assert_svg_safe", "document", "svg_root"]
