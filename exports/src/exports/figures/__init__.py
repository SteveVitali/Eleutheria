# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``exports.figures`` — the static figure kit, geography half (FIG-01a).

P36.27 / ADR-157: one Python package for every build-time map figure —
dossier at-a-glance maps, locators, index sprites, the no-JS overview.
One projection, one simplifier, one binning rule (``static-12px@1``), one
CSP-safe deterministic serializer, one lexicon vocabulary. The
graph/chart/legend half lands with P36.28 (FIG-01b).
"""

from .binning import (
    RULE_NAME,
    BinPlan,
    plan_binning,
)
from .lexicon import Lexicon, load_lexicon
from .locator import (
    SPRITE_SCHEMA,
    SpriteEntry,
    build_index_sprite,
    build_locator,
)
from .map_figure import build_map_figure
from .model import (
    FigureKitError,
    FigureSizeError,
    FigureSpec,
    MapFigureResult,
    RecordInput,
    load_spec,
    spec_from_dict,
)
from .serialize import SvgError, assert_svg_safe
from .standalone import standalone_document
from .tokens import sig_token_value

__all__ = [
    "RULE_NAME",
    "SPRITE_SCHEMA",
    "BinPlan",
    "FigureKitError",
    "FigureSizeError",
    "FigureSpec",
    "Lexicon",
    "MapFigureResult",
    "RecordInput",
    "SpriteEntry",
    "SvgError",
    "assert_svg_safe",
    "build_index_sprite",
    "build_locator",
    "build_map_figure",
    "load_lexicon",
    "load_spec",
    "plan_binning",
    "sig_token_value",
    "spec_from_dict",
    "standalone_document",
]
