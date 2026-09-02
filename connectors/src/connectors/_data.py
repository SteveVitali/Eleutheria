# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Load the connectors package's data tables.

The source registry is **data, not code** (SIG-ENG-001, SIG-INGEST-038): every
source is a TOML row, not a Python literal, so seeding a new source is a data
change reviewed on its own and never a schema/code change. This module is the
single cached reader those tables are loaded through, mirroring
``policy._data.load_table``.
"""

from __future__ import annotations

import tomllib
from functools import cache
from importlib.resources import files
from typing import Any


@cache
def load_table(name: str) -> dict[str, Any]:
    """Return the parsed TOML data table `<name>.toml` shipped with the package."""
    resource = files("connectors").joinpath("data", f"{name}.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)
