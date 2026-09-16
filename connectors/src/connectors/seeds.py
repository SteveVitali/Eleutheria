# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 The SIG project. Code is Apache-2.0; data and documentation
# carry per-artifact licences — see LICENSE and docs/2_canonical_design_spec.md §42.
"""Committed one-time seed assets (P25.7 / D-CCOPS.1-1, SIG-INGEST-049f).

A seed is **reviewed committed data, never a feed**: the asset ships inside the
``connectors`` package and is served to the eight-stage pipeline over the static
transport — the same loader gate and claim spine every source rides
(:func:`connectors.runner.run_seed`), with the run-time in-memory permit flip the
fixture path documents (SIG-INGEST-028). The registry row stays
``ingestion_permitted=false``; no network is ever opened for a seed.

The seed table is **data, not code** (SIG-ENG-001): registering a new seed is a
row in ``data/seeds.toml`` plus a packaged asset — never a code change.
"""

from __future__ import annotations

from collections.abc import Mapping
from importlib.resources import files
from pathlib import Path
from typing import Any

from ._data import load_table


class SeedNotRegistered(Exception):
    """The source has no committed seed asset registered in ``seeds.toml``."""


def seed_spec(source_id: str) -> Mapping[str, Any] | None:
    """The ``seeds.toml`` row for ``source_id`` — ``None`` when none is registered."""
    spec = load_table("seeds").get(source_id)
    return spec if isinstance(spec, Mapping) else None


def seed_asset_path(source_id: str) -> Path:
    """The packaged seed asset's path — the fixture the seed pipeline runs over."""
    spec = seed_spec(source_id)
    if spec is None:
        raise SeedNotRegistered(
            f"source {source_id!r} has no committed seed asset registered in "
            "seeds.toml; a seed load is only ever a reviewed packaged asset, "
            "never a network fetch (SIG-INGEST-049f)."
        )
    asset = str(spec.get("asset") or "")
    if not asset:
        raise SeedNotRegistered(
            f"source {source_id!r} has a seeds.toml row with no `asset` — the "
            "packaged seed file is required data."
        )
    # The package ships as a plain src-layout directory in this workspace, so the
    # traversable is a real filesystem path; read_bytes() works either way.
    return Path(str(files("connectors").joinpath("data", asset)))


__all__ = ["SeedNotRegistered", "seed_asset_path", "seed_spec"]
