# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""The shared-lexicon reader for the figure kit (P36.17's ``sig.lexicon/1``).

The kit reads ``web/src/lib/lexicon.json`` as **plain JSON** — the file is the
one machine-readable meaning table for the whole public surface, so the
figure vocabulary is the lexicon's, never a figure-private set (SIG-UI-131,
K13 C-07). Fail-closed on any key the kit relies on that the lexicon does not
declare — a meaning the shared file does not encode cannot be drawn.

The vocabulary the kit consumes:

* ``legend.dataHue``      — the one data hue binding (point/area ink)
* ``legend.fill``         — hollow = exactly one source; filled = corroborated
                            (2+ independent lineages — the interim legend line)
* ``legend.contested``    — the ``≠`` mark; raspberry means contested only
* ``legend.provisional``  — the amber dashed state; amber means provisional only
* ``legend.absence``      — the hatch texture; hatch means absence only
* ``legend.entityKind``   — shape carries kind, never epistemic state
* ``legend.linePattern``  — dashed/double/solid mean *access kind* only, so the
                            figure kit never uses line pattern for anything else

Token *names* in the lexicon resolve to literal values through
``tokens.py`` — the Python mirror of ``web/src/lib/design-tokens.ts``, whose
drift the unit suite pins byte-equal against ``tokens.css`` (one vocabulary,
no forked palettes).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .model import FigureKitError

LEXICON_SCHEMA = "sig.lexicon/1"

#: The figure-kit's own class vocabulary — every class the serializer emits.
#: These are the *structure* classes; colour/state comes from the shared
#: ``epistemic.css`` figure classes and tokens on-page, and from the embedded
#: style block in standalone files (K14 §4.7).
FIGURE_CLASSES = (
    "sig-fig",
    "sig-fig-geo",
    "sig-fig-layer",
    "sig-fig-outline",
    "sig-fig-outline-state",
    "sig-fig-provisional",
    "sig-fig-child",
    "sig-fig-child-uncovered",
    "sig-fig-child-pending",
    "sig-fig-hatch-line",
    "sig-fig-area",
    "sig-fig-point",
    "sig-fig-src-single",
    "sig-fig-src-corroborated",
    "sig-fig-contested",
    "sig-fig-locator",
    "sig-fig-locator-inset",
    "sig-fig-sprite",
    "sig-fig-sprite-cell",
    "sig-fig-caption",
    "sig-fig-legend",
)


@dataclass(frozen=True)
class Lexicon:
    """The slice of ``sig.lexicon/1`` the figure kit consumes — bound names
    and the exact interim labels, never re-worded."""

    data_hue_token: str
    contested_token: str
    provisional_token: str
    absence_token: str
    fill_encodings: dict[str, Any]
    line_pattern: dict[str, Any]
    entity_kind: dict[str, Any]
    labels: dict[str, str]

    def check_class(self, cls: str) -> str:
        """Fail-closed class gate — only the shared vocabulary may emit."""
        if cls not in FIGURE_CLASSES:
            raise FigureKitError(f"figure class {cls!r} not in the kit vocabulary")
        return cls

    def corroboration_class(self, n_sources: int) -> str:
        """The interim lineages rule (``fill.encodings``): one source → the
        hollow state; two or more → the filled/corroborated state."""
        return "sig-fig-src-single" if n_sources <= 1 else "sig-fig-src-corroborated"

    def mark_token(self, family: str) -> str:
        """Resolve a lexicon ``*-ink`` family name to the mark token — the
        ``-ink`` name binds the colour *family*; marks/edges take ``-mark``,
        labels take ``-text`` (the tokens.css convention)."""
        if family.endswith("-ink"):
            return family[: -len("-ink")] + "-mark"
        return family

    def text_token(self, family: str) -> str:
        if family.endswith("-ink"):
            return family[: -len("-ink")] + "-text"
        return family


def _find_repo_file(rel: str, repo_root: Path | None) -> Path:
    candidates = []
    if repo_root is not None:
        candidates.append(repo_root / rel)
    here = Path(__file__).resolve()
    for up in range(len(here.parents)):
        candidates.append(here.parents[up] / rel)
    for c in candidates:
        if c.is_file():
            return c
    raise FigureKitError(
        f"{rel} not found — the figure kit reads the shared lexicon; run from "
        "a checkout that has it (or pass the path explicitly)"
    )


def load_lexicon(path: Path | str | None = None, repo_root: Path | None = None) -> Lexicon:
    """Load the shared lexicon and bind the figure vocabulary — fail-closed."""
    rel = "web/src/lib/lexicon.json"
    p = Path(path) if path is not None else _find_repo_file(rel, repo_root)
    try:
        doc = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise FigureKitError(f"{p}: unreadable lexicon — {e}") from e
    if not isinstance(doc, dict) or doc.get("schema") != LEXICON_SCHEMA:
        raise FigureKitError(f"{p}: not a {LEXICON_SCHEMA} document")

    def _get(*keys: str) -> Any:
        node: Any = doc
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                raise FigureKitError(f"{p}: lexicon missing {'/'.join(keys)}")
            node = node[k]
        return node

    try:
        legend = _get("legend")
        data_hue = _get("legend", "dataHue", "token")
        fill = _get("legend", "fill", "encodings")
        contested_tokens = _get("legend", "contested", "tokens")
        provisional_tokens = _get("legend", "provisional", "tokens")
        line_pattern = _get("legend", "linePattern")
        entity_kind = _get("legend", "entityKind")
        labels = {
            "singleSource": str(
                fill["singleSource"]["interimLegendLine"]
                if "interimLegendLine" in fill["singleSource"]
                else fill["singleSource"]["label"]
            ),
            "corroborated": str(
                fill["corroborated"].get("interimLegendLine", fill["corroborated"]["label"])
            ),
            "contested": str(legend["contested"]["plain"]),
        }
    except (KeyError, IndexError, TypeError) as e:
        raise FigureKitError(f"{p}: lexicon shape incomplete for figures — {e}") from e

    return Lexicon(
        data_hue_token=str(data_hue),
        contested_token=str(contested_tokens[0]),
        provisional_token=str(provisional_tokens[0]),
        absence_token="sig-epi-absence-ink",
        fill_encodings=fill,
        line_pattern=line_pattern,
        entity_kind=entity_kind,
        labels=labels,
    )


__all__ = ["FIGURE_CLASSES", "LEXICON_SCHEMA", "Lexicon", "load_lexicon"]
