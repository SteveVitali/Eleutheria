# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Vendor-portal slug parsing as a **hypothesis generator** (SIG-IDENT-015).

A vendor portal slug (a Flock/Fusus network subdomain, a path segment) is a weak
hint at an organisation's name, never an identity. This module parses it by a
documented, **versioned grammar** — never ad-hoc splitting — and returns a
:class:`SlugHypothesis` explicitly marked ``is_hypothesis=True`` so no caller can
mistake it for an identity assertion. Vendor-internal test tenants (``test``,
``demo``, a documented denylist) are excluded outright: they never become
candidate real bodies.

The output is a *name hypothesis* the cascade may use to search for candidates; it
is never a match on its own and never auto-writes.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any

__all__ = ["SlugHypothesis", "SLUG_GRAMMAR_VERSION", "parse_slug", "is_denied_slug"]

# The grammar: lowercase, split on the documented separators, drop empties.
_SEPARATORS = re.compile(r"[-_./ ]+")


@cache
def _grammar() -> dict[str, Any]:
    resource = files("resolution").joinpath("data", "slug_grammar.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)


SLUG_GRAMMAR_VERSION = str(_grammar()["version"])


@dataclass(frozen=True)
class SlugHypothesis:
    """A parsed slug: a NAME HYPOTHESIS, never an identity assertion (SIG-IDENT-015)."""

    raw: str
    tokens: tuple[str, ...]
    name_hypothesis: str
    grammar_version: str
    #: Always True — a parsed slug is a hypothesis to search on, never a match.
    is_hypothesis: bool = True


def _tokens(slug: str) -> list[str]:
    return [t for t in _SEPARATORS.split(slug.strip().lower()) if t]


def is_denied_slug(slug: str) -> bool:
    """Whether the slug is a vendor-internal test tenant (denylisted, SIG-IDENT-015)."""
    grammar = _grammar()
    tokens = _tokens(slug)
    if not tokens:
        return True
    exact = set(grammar.get("denylist_exact", []))
    if any(tok in exact for tok in tokens):
        return True
    lowered = slug.strip().lower()
    return any(marker in lowered for marker in grammar.get("denylist_contains", []))


def parse_slug(slug: str) -> SlugHypothesis | None:
    """Parse a vendor-portal slug into a name hypothesis, or ``None`` if denied.

    Returns ``None`` for an empty slug or a denylisted vendor-internal test tenant
    (SIG-IDENT-015). Otherwise returns a :class:`SlugHypothesis` whose
    ``name_hypothesis`` is the tokens title-cased and space-joined — a *guess* to
    feed the candidate search, explicitly flagged as a hypothesis.
    """
    if is_denied_slug(slug):
        return None
    tokens = _tokens(slug)
    return SlugHypothesis(
        raw=slug,
        tokens=tuple(tokens),
        name_hypothesis=" ".join(tokens),
        grammar_version=SLUG_GRAMMAR_VERSION,
    )
