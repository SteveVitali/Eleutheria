# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""``exports.figures`` — the static figure kit (FIG-01a + FIG-01b).

P36.27 / ADR-157: one Python package for every build-time figure —
dossier at-a-glance maps, locators, index sprites, the no-JS overview.
P36.28 extends the same package (same serializer, same lexicon, same
token mirror, same standalone wrapper) with the graph/chart/legend half:
the deterministic bipartite dossier network figure (SIG-UI-125/DV03),
the radial entity ego (K2), the K14 chart kinds (bar, stacked-bar,
strip, timeline), the generated legend and the wide/narrow + table-twin
contract. One projection, one CSP-safe deterministic serializer, one
lexicon vocabulary — and no third-party layout dependency (the GPL
igraph wheel is never imported).
"""

from .binning import (
    RULE_NAME,
    BinPlan,
    plan_binning,
)
from .chart import (
    CHART_KINDS,
    INPUT_SCHEMA_CHART,
    RESULT_SCHEMA_CHART,
    ChartSpec,
    build_chart,
    chart_spec_from_dict,
    load_chart_spec,
)
from .graph_model import (
    INPUT_SCHEMA_GRAPH,
    RESULT_SCHEMA_GRAPH,
    GraphFigureSpec,
    StaticFigureResult,
    graph_spec_from_dict,
    load_graph_spec,
)
from .legend import LegendEntry, build_legend_entries
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
from .network_figure import build_ego_figure, build_network_figure
from .serialize import SvgError, assert_svg_safe
from .standalone import standalone_document
from .tokens import sig_token_value

__all__ = [
    "CHART_KINDS",
    "INPUT_SCHEMA_CHART",
    "INPUT_SCHEMA_GRAPH",
    "RESULT_SCHEMA_CHART",
    "RESULT_SCHEMA_GRAPH",
    "RULE_NAME",
    "SPRITE_SCHEMA",
    "BinPlan",
    "ChartSpec",
    "FigureKitError",
    "FigureSizeError",
    "FigureSpec",
    "GraphFigureSpec",
    "LegendEntry",
    "Lexicon",
    "MapFigureResult",
    "RecordInput",
    "SpriteEntry",
    "StaticFigureResult",
    "SvgError",
    "assert_svg_safe",
    "build_chart",
    "build_ego_figure",
    "build_index_sprite",
    "build_legend_entries",
    "build_locator",
    "build_map_figure",
    "build_network_figure",
    "chart_spec_from_dict",
    "graph_spec_from_dict",
    "load_chart_spec",
    "load_graph_spec",
    "load_lexicon",
    "load_spec",
    "plan_binning",
    "sig_token_value",
    "spec_from_dict",
    "standalone_document",
]
