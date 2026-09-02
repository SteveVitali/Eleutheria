# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Load the policy package's data tables.

The policy contract keeps its tables — licence compartments, the sensitivity
matrix, the threat model, categorical exclusions, crawler rules — as **data,
not code** (SIG-LIC-004a is the sharpest instance: adding a source under a new
share-alike licence must be a data row, never a schema change). This module is
the single, cached reader those tables are loaded through.
"""

from __future__ import annotations

import tomllib
from functools import cache
from importlib.resources import files
from typing import Any


@cache
def load_table(name: str) -> dict[str, Any]:
    """Return the parsed TOML data table `<name>.toml` shipped with the package."""
    resource = files("policy").joinpath("data", f"{name}.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)
