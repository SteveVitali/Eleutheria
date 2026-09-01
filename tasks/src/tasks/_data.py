# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Load the tasks package's data tables.

The per-jurisdiction records-law reference table and the versioned request
templates are **data, not code** (SIG-ENG-001): each jurisdiction row and each
template is a TOML entry reviewed on its own, so amending a statute citation or
adding a template version is a data change, never a code change. Changes after
this ticket are VERSIONED (§20) — bump the table's `*_version` and add the change,
never silently rewrite a landed row. This module is the single cached reader those
tables load through, mirroring ``connectors._data.load_table`` /
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
    resource = files("tasks").joinpath("data", f"{name}.toml")
    with resource.open("rb") as fh:
        return tomllib.load(fh)
